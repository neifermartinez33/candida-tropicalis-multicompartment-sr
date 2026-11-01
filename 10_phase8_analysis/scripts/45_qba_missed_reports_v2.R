#!/usr/bin/env Rscript
# 45_qba_missed_reports_v2.R (2026-10-30)
# v2: after round 4 (workbooks B15, B16) the exclusions not re-read fall to 1045 and the rates are updated.
# Quantitative bias analysis of the full-text exclusions that no reviewer re-read: how many eligible
# reports may remain among them, and how much they could move the pooled estimates.
#
# Bias parameters
#   N_UNREAD   full-text exclusions not re-read by a reviewer (default 1045: not in the blind sample B08 nor in workbook B15).
#   Rate of missed reports that would contribute to a pooled stratum, two models:
#     empirical    p ~ Beta(0.5 + 3, 0.5 + 466): 3 of the 469 sampled exclusions (O13199, O13212, R04084) became
#                  reports contributing to a pooled stratum (B08, decision D4). Workbook B15 is left out of the
#                  rate because it was selected for susceptibility data, so it does not represent the unread;
#     pessimistic  p = r * q, r ~ Beta(0.5 + 41, 0.5 + 428): exclusions reversed in B08, and
#                  q ~ Beta(0.5 + 1219, 0.5 + 2073): share of the included reports eligible for the
#                  meta-analysis; it assumes that reversed exclusions are as often eligible as included reports.
#   Missed reports M ~ Binomial(N_UNREAD, p). Each missed report is a report eligible for the
#   meta-analysis drawn at random, with all its main rows, entering as a new independent collection.
#   Three scenarios for the proportions of the missed reports:
#     exchangeable   rows as observed;
#     high           events set to the 90th percentile of the collection proportions of the stratum;
#     low            events set to the 10th percentile.
# Each simulation refits the main model (binomial-normal GLMM, random intercept per collection,
# 7-node quadrature) in the strata that receive rows, and records the population mean.
#
# Usage, from the project root:
#   conda run --no-capture-output -n ctrop_ma Rscript 10_phase8_analysis/scripts/45_qba_missed_reports_v2.R [N_UNREAD] [N_SIM]
# Outputs: 10_phase8_analysis/results/qba_missed_reports_v2_<date-time>.csv (one row per stratum, rate
# model and scenario) and qba_missed_reports_v2_<date-time>_sims.csv, with the log in results/logs.

if (!dir.exists("10_phase8_analysis")) stop("Run from the project root")
suppressPackageStartupMessages({ library(lme4); library(jsonlite); library(parallel) })

RES <- "10_phase8_analysis/results"
SEED <- 20261029; NODES <- 4096
ZQ <- qnorm((seq_len(NODES) - 0.5) / NODES)
KEY <- c("compartment", "agent", "outcome", "regime_stratum")
args <- commandArgs(trailingOnly = TRUE)
N_UNREAD <- if (length(args) >= 1) as.integer(args[1]) else 1045L
N_SIM <- if (length(args) >= 2) as.integer(args[2]) else 1000L
CORES <- max(1L, detectCores() - 1L)

newest <- function(pat) { f <- sort(Sys.glob(file.path(RES, pat))); f <- f[!grepl("PROVISIONAL", f)]; f[length(f)] }
f_in <- newest("ma_input_v2_*.csv"); f_res <- newest("ma_results_v3_*.csv")
x <- read.csv(f_in, stringsAsFactors = FALSE, na.strings = "")
r <- read.csv(f_res, stringsAsFactors = FALSE, na.strings = c("", "NA"))
key_of <- function(d) do.call(paste, c(unname(as.list(d[KEY])), list(sep = " | ")))
x$stratum <- key_of(x); r$stratum <- key_of(r)
pooled <- r$stratum[r$status == "pooled"]
d <- x[as.logical(x$main) & x$stratum %in% pooled, c("stratum", "study_id", "collection_id", "events", "n_tested")]
d$events <- as.integer(round(d$events)); d$n_tested <- as.integer(round(d$n_tested))

marginal <- function(fit) {
  mu <- as.numeric(fixef(fit))[1]; tau2 <- as.numeric(VarCorr(fit)[[1]])[1]
  if (tau2 <= 0) plogis(mu) else mean(plogis(mu + sqrt(tau2) * ZQ))
}
fit_p <- function(g) {
  f <- tryCatch(suppressMessages(suppressWarnings(
    glmer(cbind(events, n_tested - events) ~ 1 + (1 | collection_id), data = g, family = binomial, nAGQ = 7))),
    error = function(e) NULL)
  if (is.null(f)) NA_real_ else marginal(f)
}
base <- sapply(pooled, function(s) fit_p(d[d$stratum == s, ]))
chk <- max(abs(base - r$p_marginal[match(pooled, r$stratum)]), na.rm = TRUE)
if (chk > 1e-4) stop("The refit does not reproduce ma_results_v3 (max difference ", signif(chk, 3), ")")

templates <- split(d[, c("stratum", "events", "n_tested")], d$study_id)
props <- tapply(d$events / d$n_tested, d$stratum, identity)
q90 <- sapply(props, quantile, 0.9, names = FALSE); q10 <- sapply(props, quantile, 0.1, names = FALSE)

draw_rate <- function(model) switch(model,
  empirical = rbeta(1, 3.5, 466.5),
  pessimistic = rbeta(1, 41.5, 428.5) * rbeta(1, 1219.5, 2073.5))

one_sim <- function(i, model, scenario) {
  set.seed(SEED + 7919L * i + switch(model, empirical = 0L, pessimistic = 1L) * 104729L)
  m <- rbinom(1, N_UNREAD, draw_rate(model))
  out <- setNames(rep(0, length(pooled)), pooled)
  if (m == 0) return(c(m = 0, out))
  add <- do.call(rbind, lapply(seq_len(m), function(j) {
    t <- templates[[sample.int(length(templates), 1)]]
    t$collection_id <- paste0("SIM_", j)
    t
  }))
  if (scenario != "exchangeable") {
    q <- if (scenario == "high") q90[add$stratum] else q10[add$stratum]
    add$events <- as.integer(round(add$n_tested * q))
  }
  for (s in unique(add$stratum)) {
    g <- rbind(d[d$stratum == s, c("collection_id", "events", "n_tested")], add[add$stratum == s, c("collection_id", "events", "n_tested")])
    out[s] <- 100 * (fit_p(g) - base[s])
  }
  c(m = m, out)
}

ts <- format(Sys.time(), "%Y-%m-%dT%H%M%S")
sims <- list(); summ <- list()
for (model in c("empirical", "pessimistic")) for (scenario in c("exchangeable", "high", "low")) {
  t0 <- Sys.time()
  res <- do.call(rbind, mclapply(seq_len(N_SIM), one_sim, model = model, scenario = scenario, mc.cores = CORES))
  sims[[paste(model, scenario)]] <- data.frame(rate_model = model, scenario = scenario, sim = seq_len(N_SIM), res, check.names = FALSE)
  for (s in pooled) {
    v <- res[, s]
    summ[[length(summ) + 1]] <- data.frame(
      stratum = s, rate_model = model, scenario = scenario, p_marginal_pct = round(100 * base[s], 2),
      missed_reports_median = median(res[, "m"]), missed_reports_p95 = unname(quantile(res[, "m"], 0.95)),
      share_sims_stratum_changed = round(mean(v != 0), 3),
      change_pp_median = round(median(v, na.rm = TRUE), 3),
      change_pp_p2.5 = round(unname(quantile(v, 0.025, na.rm = TRUE)), 3),
      change_pp_p97.5 = round(unname(quantile(v, 0.975, na.rm = TRUE)), 3),
      change_pp_max_abs = round(max(abs(v), na.rm = TRUE), 3),
      failed_fits = sum(is.na(v)))
  }
  cat(sprintf("%s / %s: %d simulations, %.1f min\n", model, scenario, N_SIM, as.numeric(difftime(Sys.time(), t0, units = "mins"))))
}
summary_df <- do.call(rbind, summ)
f_out <- file.path(RES, paste0("qba_missed_reports_v2_", ts, ".csv"))
f_sims <- file.path(RES, paste0("qba_missed_reports_v2_", ts, "_sims.csv"))
write.csv(summary_df, f_out, row.names = FALSE)
write.csv(do.call(rbind, sims), f_sims, row.names = FALSE)

overall <- aggregate(cbind(change_pp_p97.5, change_pp_max_abs) ~ rate_model + scenario, data = transform(summary_df, change_pp_p97.5 = pmax(abs(change_pp_p97.5), abs(change_pp_p2.5))), FUN = max)
md5 <- function(f) unname(tools::md5sum(f))
log <- list(script = "45_qba_missed_reports_v2.R", run_time = ts, n_unread = N_UNREAD, n_sim = N_SIM, seed = SEED,
            strata = length(pooled), refit_max_difference = chk,
            largest_change_by_model_and_scenario = overall,
            inputs = setNames(as.list(md5(c(f_in, f_res))), c(f_in, f_res)),
            outputs = setNames(as.list(md5(c(f_out, f_sims))), basename(c(f_out, f_sims))))
dir.create(file.path(RES, "logs"), showWarnings = FALSE)
writeLines(toJSON(log, auto_unbox = TRUE, pretty = TRUE, digits = NA), file.path(RES, "logs", paste0("45_qba_missed_reports_v2_", ts, ".json")))
print(overall)
cat(f_out, "\n")
