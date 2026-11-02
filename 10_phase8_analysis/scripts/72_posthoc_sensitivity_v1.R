#!/usr/bin/env Rscript
# 72_posthoc_sensitivity_v1.R (2026-11-02)
# Analyses that were not prespecified, added after the results had been seen. Same model and thresholds as
# 06_ma_marginal_v3.R (AR12, AR14 to AR18): one-level binomial-normal GLMM, 7-node quadrature, population mean with a parametric
# percentile bootstrap of 999 replicates, tau2 by maximum likelihood with a profile interval.
#   SX4 without case reports and case series; SX5 without laboratory evaluations; SX6 without collections of fewer than 5 isolates;
#   SX7 all three; SX8 without the largest collection (human host);
#   SX9 ECV outcomes with the reference method of each ECV and by test method, resistance with reference broth microdilution only;
#   SX10 non-human strata with one collection per laboratory, the one with most isolates tested;
#   SX11 non-human strata leaving out one collection at a time;
#   REG human host, fluconazole and voriconazole with current breakpoints, by WHO region, with a likelihood-ratio test.
# Each subset reapplies AR12 and AR18.
# Usage, from the project root:
#   conda run --no-capture-output -n ctrop_ma Rscript 10_phase8_analysis/scripts/72_posthoc_sensitivity_v1.R
# Outputs: results/ma_posthoc_v1_<date-time>.csv, ma_posthoc_lrt_v1_<date-time>.csv and a log in results/logs.
if (!dir.exists("10_phase8_analysis")) stop("Run from the project root")
suppressPackageStartupMessages({library(lme4); library(parallel); library(jsonlite)})
RES <- "10_phase8_analysis/results"; TAU2_MAX <- 25; BOOT_R <- 999; SEED <- 20261024; NODES <- 4096
ZQ <- qnorm((seq_len(NODES) - 0.5) / NODES)
newest <- function(p) {f <- sort(Sys.glob(file.path(RES, p))); f <- f[!grepl("PROVISIONAL", f)]; f[length(f)]}
seed_of <- function(s) SEED + sum(utf8ToInt(s) * seq_along(utf8ToInt(s))) %% 100000L
f_in <- newest("ma_input_v2_*.csv"); f_res <- newest("ma_results_v3_*.csv")
DS <- "10_phase8_analysis/data/analysis_dataset_v3_2026-10-30T133231/studies.csv"
LAB <- "10_phase8_analysis/data/lookups/lab_coding_v1.csv"
x <- read.csv(f_in, stringsAsFactors = FALSE, na.strings = ""); x <- x[as.logical(x$main), ]
s <- read.csv(DS, stringsAsFactors = FALSE, na.strings = "")
x$design <- s$design[match(x$study_id, s$study_id)]
lb <- read.csv(LAB, stringsAsFactors = FALSE)
x$laboratory <- lb$laboratory[match(x$study_id, lb$study_id)]
base <- read.csv(f_res, stringsAsFactors = FALSE)
marg <- function(f) {m <- as.numeric(fixef(f))[1]; t <- as.numeric(VarCorr(f)[[1]])[1]; if (t <= 0) plogis(m) else mean(plogis(m + sqrt(t) * ZQ))}
BMD <- c("broth_microdilution_CLSI_or_unspecified", "broth_microdilution_EUCAST")
stratum <- function(b) x[x$compartment == b$compartment & x$agent == b$agent & x$outcome == b$outcome & x$regime_stratum == b$regime_stratum, ]
fit <- function(g, analysis, key, level = "", grp = "research_group", boot = TRUE) {
  e <- as.integer(round(g$events)); n <- as.integer(round(g$n_tested)); k <- length(e); G <- length(unique(g[[grp]]))
  r <- data.frame(analysis = analysis, stratum = key, level = level, k = k, groups = G, events = sum(e), isolates = sum(n),
                  status = NA_character_, p_marginal = NA_real_, marg_lower = NA_real_, marg_upper = NA_real_, p_median = NA_real_,
                  tau2 = NA_real_, tau2_lower = NA_real_, tau2_upper = NA_real_, stringsAsFactors = FALSE)
  if (k < 5 || G < 2) {r$status <- "below_minimum_AR12"; return(r)}
  if (sum(e) == 0 || sum(e) == sum(n)) {r$status <- "not_pooled_boundary_AR18a"; return(r)}
  u <- seq_along(e)
  f <- suppressMessages(suppressWarnings(glmer(cbind(e, n - e) ~ 1 + (1 | u), family = binomial, nAGQ = 7)))
  pr <- tryCatch(suppressMessages(suppressWarnings(confint(f, parm = "theta_", method = "profile", quiet = TRUE))), error = function(e) NULL)
  r$p_marginal <- marg(f); r$p_median <- plogis(as.numeric(fixef(f))[1]); r$tau2 <- as.numeric(VarCorr(f)[[1]])[1]
  if (is.matrix(pr)) {r$tau2_lower <- pr[1, 1]^2; r$tau2_upper <- pr[1, 2]^2}
  r$status <- if (is.na(r$tau2_upper)) "not_pooled_no_profile_AR18c" else if (r$tau2_upper > TAU2_MAX) "not_pooled_tau2_AR18b" else "pooled"
  if (r$status == "pooled" && boot) {
    b <- suppressMessages(suppressWarnings(bootMer(f, marg, nsim = BOOT_R, type = "parametric", use.u = FALSE, seed = seed_of(paste(key, analysis, level)))))
    tt <- as.numeric(b$t); tt <- tt[is.finite(tt)]; q <- quantile(tt, c(.025, .975), names = FALSE); r$marg_lower <- q[1]; r$marg_upper <- q[2]
  }
  r
}
tasks <- list()
add <- function(...) tasks[[length(tasks) + 1]] <<- list(...)
c1 <- base[base$compartment == "C1" & base$status == "pooled", ]
for (i in seq_len(nrow(c1))) {
  b <- c1[i, ]; key <- paste(b$compartment, b$agent, b$outcome, b$regime_stratum, sep = " | "); g <- stratum(b)
  cr <- g$design %in% c("case_report", "case_series"); le <- g$design == "laboratory_evaluation"; sm <- g$n_tested < 5
  add(g[!cr, ], "SX4", key); add(g[!le, ], "SX5", key); add(g[!sm, ], "SX6", key); add(g[!(cr | le | sm), ], "SX7", key)
  add(g[-which.max(g$n_tested), ], "SX8", key)
  if (b$outcome == "R") add(g[g$method %in% BMD, ], "SX9", key, "reference broth microdilution")
}
ec <- x[x$compartment == "C1" & x$outcome == "NWT", ]
for (key0 in unique(paste(ec$agent, ec$regime_stratum, sep = "|"))) {
  p <- strsplit(key0, "|", fixed = TRUE)[[1]]; g <- ec[ec$agent == p[1] & ec$regime_stratum == p[2], ]
  if (sum(base$compartment == "C1" & base$agent == p[1] & base$outcome == "NWT" & base$regime_stratum == p[2]) == 0) next
  key <- paste("C1", p[1], "NWT", p[2], sep = " | ")
  own <- if (p[2] == "ECV_EUCAST") "broth_microdilution_EUCAST" else "broth_microdilution_CLSI_or_unspecified"
  add(g[g$method == own, ], "SX9", key, "method of the ECV")
  for (m in c("commercial_microdilution_SYO", "commercial_ATB_FUNGUS", "gradient_diffusion", "commercial_automated_VITEK2"))
    if (any(g$method == m)) add(g[g$method == m, ], "SX9", key, m)
}
nh <- base[base$compartment != "C1", ]
for (i in seq_len(nrow(nh))) {
  b <- nh[i, ]; key <- paste(b$compartment, b$agent, b$outcome, b$regime_stratum, sep = " | "); g <- stratum(b)
  o <- do.call(rbind, lapply(split(g, g$laboratory), function(z) z[order(-z$n_tested, z$collection_id)[1], ]))
  add(o, "SX10", key, "one collection per laboratory", "laboratory")
  if (b$status == "pooled") for (j in seq_len(nrow(g))) add(g[-j, ], "SX11", key, g$collection_id[j], "research_group", FALSE)
}
for (pp in list(c("fluconazole", "CLSI_SS+EUCAST"), c("voriconazole", "CLSI_SS"))) {
  g <- x[x$compartment == "C1" & x$outcome == "R" & x$agent == pp[1] & x$regime_stratum == pp[2], ]
  key <- paste("C1", pp[1], "R", pp[2], sep = " | ")
  for (r in c("AFR", "AMR", "EMR", "EUR", "SEAR", "WPR")) add(g[g$who_region == r, ], "REG", key, r)
}
cat(length(tasks), "tasks\n")
res <- mclapply(tasks, function(t) tryCatch(do.call(fit, unname(t)), error = function(e) {cat("ERROR", conditionMessage(e), "\n"); NULL}),
                mc.cores = max(1, detectCores() - 1), mc.preschedule = FALSE)
stopifnot(!any(sapply(res, is.null)))
out <- do.call(rbind, res)
lrt <- list()
for (pp in list(c("fluconazole", "CLSI_SS+EUCAST"), c("voriconazole", "CLSI_SS"))) {
  g0 <- x[x$compartment == "C1" & x$outcome == "R" & x$agent == pp[1] & x$regime_stratum == pp[2], ]
  for (mult in c(TRUE, FALSE)) {
    g <- if (mult) g0 else g0[g0$who_region != "MULTI", ]; g <- g[!is.na(g$who_region), ]
    e <- as.integer(round(g$events)); n <- as.integer(round(g$n_tested)); u <- seq_along(e); mm <- model.matrix(~ factor(g$who_region))
    f0 <- suppressMessages(suppressWarnings(glmer(cbind(e, n - e) ~ 1 + (1 | u), family = binomial, nAGQ = 7)))
    f1 <- suppressMessages(suppressWarnings(glmer(cbind(e, n - e) ~ mm - 1 + (1 | u), family = binomial, nAGQ = 7)))
    t0 <- as.numeric(VarCorr(f0)[[1]]); t1 <- as.numeric(VarCorr(f1)[[1]]); ch <- as.numeric(2 * (logLik(f1) - logLik(f0))); df <- ncol(mm) - 1
    lrt[[length(lrt) + 1]] <- data.frame(agent = pp[1], with_multinational = mult, k = nrow(g), chisq = ch, df = df, p = pchisq(ch, df, lower.tail = FALSE), tau2_null = t0, tau2_region = t1, reduction = 1 - t1 / t0)
  }
}
stamp <- format(Sys.time(), "%Y-%m-%dT%H%M%S")
f1 <- file.path(RES, paste0("ma_posthoc_v1_", stamp, ".csv")); f2 <- file.path(RES, paste0("ma_posthoc_lrt_v1_", stamp, ".csv"))
write.csv(out, f1, row.names = FALSE); write.csv(do.call(rbind, lrt), f2, row.names = FALSE)
ins <- c(f_in, f_res, DS, LAB)
write_json(list(script = "72_posthoc_sensitivity_v1.R", run_time = format(Sys.time(), "%Y-%m-%d %H:%M:%S %z"), r_version = R.version.string,
                lme4 = as.character(packageVersion("lme4")), seed_base = SEED, boot_r = BOOT_R,
                inputs = setNames(as.list(unname(tools::md5sum(ins))), ins),
                outputs = setNames(as.list(unname(tools::md5sum(c(f1, f2)))), basename(c(f1, f2)))),
           file.path(RES, "logs", paste0("72_posthoc_sensitivity_v1_", stamp, ".json")), auto_unbox = TRUE, pretty = TRUE)
cat("done", f1, nrow(out), "\n")
