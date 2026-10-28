#!/usr/bin/env Rscript
# 06_ma_marginal_v3.R (2026-10-24)
# Estimates by stratum (SQ2) with the rules 10_phase8_analysis/analysis_rules_v4_2026-10-24.md on
# ma_input_v2 (analysis dataset v3). Same model as v2 (AR14 to AR18): one-level binomial-normal GLMM,
# 7-node quadrature; population mean with CI by parametric percentile bootstrap of 999
# replicates; median with a t CI with k-1 degrees of freedom on the model standard error (what
# meta calls "HK" in a GLMM); Higgins, Thompson and Spiegelhalter prediction interval with t on k-2;
# tau2 by maximum likelihood with CI by profile likelihood.
# Changes from v2:
#   - the seed of each stratum comes from its key and not from its position in the list, so that a stratum
#     gives the same bootstrap even if the set of strata changes;
#   - reads ma_input_v2 and its strata summary, of the same stamp; in provisional mode it says so in every output;
#   - the strata that are not pooled keep the exact binomial interval of the total, which now goes to the
#     table and not only to the text.
# Usage, from the project root:
#   conda run --no-capture-output -n ctrop_ma Rscript 10_phase8_analysis/scripts/06_ma_marginal_v3.R [--provisional]
# Outputs: 10_phase8_analysis/results/ma_results_v3_<date-time>[_PROVISIONAL].csv and its log in results/logs.

if (!dir.exists("10_phase8_analysis")) stop("Run from the project root")
suppressPackageStartupMessages({
  library(meta); library(metafor); library(lme4); library(jsonlite)
})

RULES <- "10_phase8_analysis/analysis_rules_v4_2026-10-24.md"
RES <- "10_phase8_analysis/results"
TAU2_MAX <- 25; BOOT_R <- 999; SEED <- 20261024; NODES <- 4096
PROFILE_SECONDS <- 180; BOOT_SECONDS <- 900
KEY <- c("compartment", "agent", "outcome", "regime_stratum")
ZQ <- qnorm((seq_len(NODES) - 0.5) / NODES)
PROV <- "--provisional" %in% commandArgs(trailingOnly = TRUE)
TAG <- if (PROV) "_PROVISIONAL" else ""

newest <- function(pat) {
  f <- sort(Sys.glob(file.path(RES, pat)))
  f <- f[grepl("_PROVISIONAL\\.csv$", f) == PROV]
  if (!length(f)) stop("There is no ", pat, if (PROV) " PROVISIONAL" else " FINAL",
                       ": run 04_ma_input_v2.py first", if (PROV) " --provisional" else "")
  f[length(f)]
}
# seed per stratum: deterministic function of the key
seed_of <- function(s) SEED + sum(utf8ToInt(s) * seq_along(utf8ToInt(s))) %% 100000L

f_in <- newest("ma_input_v2_*.csv")
stamp_in <- sub("^ma_input_v2_(.*)\\.csv$", "\\1", basename(f_in))
f_st <- file.path(RES, paste0("ma_strata_v2_", stamp_in, ".csv"))
for (f in c(RULES, f_st)) if (!file.exists(f)) stop("Missing ", f)

x <- read.csv(f_in, stringsAsFactors = FALSE, na.strings = "")
st <- read.csv(f_st, stringsAsFactors = FALSE, na.strings = "")
x$main <- as.logical(x$main)
st$meets_minimum <- as.logical(st$meets_minimum)
key_of <- function(d) do.call(paste, c(unname(as.list(d[KEY])), list(sep = " | ")))
x$stratum <- key_of(x); st$stratum <- key_of(st)
d <- x[x$main & x$stratum %in% st$stratum[st$meets_minimum], ]
d$events <- as.integer(round(d$events)); d$n_tested <- as.integer(round(d$n_tested))
stopifnot(!anyNA(d$events), !anyNA(d$n_tested), all(d$n_tested > 0), all(d$events >= 0),
          all(d$events <= d$n_tested), !any(duplicated(paste(d$stratum, d$collection_id))))
ag <- aggregate(cbind(events, n_tested) ~ stratum, data = d, FUN = sum)
ag$k <- as.integer(table(d$stratum)[ag$stratum])
chk <- merge(ag, st[st$meets_minimum, ], by = "stratum")
if (nrow(chk) != sum(st$meets_minimum) || !all(chk$events.x == chk$events.y) ||
    !all(chk$n_tested == chk$isolates) || !all(chk$k == chk$k_collections))
  stop("The input does not match the strata summary: do not continue, report it")

num <- function(o, f) { v <- o[[f]]; if (is.null(v) || !length(v)) NA_real_ else as.numeric(v)[1] }
marginal <- function(mu, tau2) {
  if (!is.finite(mu) || !is.finite(tau2)) return(NA_real_)
  if (tau2 <= 0) return(plogis(mu))
  mean(plogis(mu + sqrt(tau2) * ZQ))
}
boot_stat <- function(fit) marginal(as.numeric(fixef(fit))[1], as.numeric(VarCorr(fit)[[1]])[1])
budget <- function(expr, seconds, msg) {
  tryCatch({ setTimeLimit(elapsed = seconds, transient = FALSE); expr },
           error = function(e) structure(NA_real_, err = paste(msg, conditionMessage(e))),
           finally = setTimeLimit(elapsed = Inf, transient = FALSE))
}
FIELDS <- c("p_marginal", "marg_lower", "marg_upper", "p_median", "med_lower", "med_upper",
            "pi_lower", "pi_upper", "tau2", "tau2_lower", "tau2_upper", "I2", "Q", "df_Q",
            "pval_Q", "exact_lower", "exact_upper", "glmm_max_diff", "boot_used")
blank <- as.data.frame(setNames(rep(list(NA_real_), length(FIELDS)), FIELDS))

rows <- list()
ord <- st[st$meets_minimum, ]
ord <- ord[order(ord$k_collections, ord$stratum), ]
t0 <- Sys.time()
cat(sprintf("Input %s%s\nStrata that meet AR12: %d. tau2 threshold = %g, %d replicates.\n",
            basename(f_in), if (PROV) "  [PROVISIONAL]" else "", nrow(ord), TAU2_MAX, BOOT_R))
for (i in seq_len(nrow(ord))) {
  s <- ord[i, ]; g <- d[d$stratum == s$stratum, ]
  ev <- sum(g$events); nn <- sum(g$n_tested); pc <- g$events / g$n_tested
  ex <- binom.test(ev, nn)$conf.int
  base <- cbind(s[KEY], data.frame(k_collections = s$k_collections, research_groups = s$research_groups,
                                   k_reports_all = s$k_reports_all, flagged_main_rows = s$flagged_main_rows,
                                   unverified_main_rows = s$unverified_main_rows,
                                   events = ev, isolates = nn, p_crude = ev / nn,
                                   p_col_min = min(pc), p_col_max = max(pc),
                                   largest_collection_pct = s$largest_collection_pct,
                                   collections_zero = sum(g$events == 0),
                                   collections_full = sum(g$events == g$n_tested)))
  s0 <- Sys.time(); notes <- character(0)
  r <- cbind(base, blank, status = NA_character_, seed = seed_of(s$stratum), seconds = 0, note = "")
  r$exact_lower <- ex[1]; r$exact_upper <- ex[2]
  if (ev == 0 || ev == nn) {
    r$status <- "not_pooled_boundary_AR18a"
    cat(sprintf("%3d/%3d %-44s k=%3d  %d/%d  boundary (AR18a)\n", i, nrow(ord), s$stratum, s$k_collections, ev, nn))
  } else {
    m <- withCallingHandlers(
      metaprop(event = events, n = n_tested, studlab = collection_id, data = g, method = "GLMM", sm = "PLOGIT",
               common = FALSE, random = TRUE, method.random.ci = "HK", method.predict = "HTS", prediction = TRUE),
      warning = function(w) { notes <<- c(notes, conditionMessage(w)); invokeRestart("muffleWarning") })
    gl <- suppressMessages(suppressWarnings(
      glmer(cbind(events, n_tested - events) ~ 1 + (1 | collection_id), data = g, family = binomial, nAGQ = 7)))
    mu <- as.numeric(fixef(gl))[1]; t2 <- as.numeric(VarCorr(gl)[[1]])[1]
    dif <- max(abs(mu - num(m, "TE.random")), abs(t2 - num(m, "tau2")))
    if (!is.finite(dif) || dif > 1e-4) notes <- c(notes, sprintf("meta and lme4 differ by %.3g", dif))
    pr <- budget(suppressMessages(suppressWarnings(confint(gl, parm = "theta_", method = "profile", quiet = TRUE))),
                 PROFILE_SECONDS, "tau2 profile not obtained:")
    if (is.matrix(pr)) {
      t2_lo <- as.numeric(pr[1, 1])^2; t2_hi <- as.numeric(pr[1, 2])^2
    } else {
      t2_lo <- NA_real_; t2_hi <- NA_real_; notes <- c(notes, attr(pr, "err"))
    }
    pooled <- is.finite(t2_hi) && t2_hi <= TAU2_MAX
    r$status <- if (pooled) "pooled" else if (is.finite(t2_hi)) "not_pooled_tau2_AR18b" else "not_pooled_no_profile_AR18c"
    r$p_marginal <- marginal(mu, t2)
    r$p_median <- plogis(num(m, "TE.random"))
    r$med_lower <- plogis(num(m, "lower.random")); r$med_upper <- plogis(num(m, "upper.random"))
    r$pi_lower <- plogis(num(m, "lower.predict")); r$pi_upper <- plogis(num(m, "upper.predict"))
    r$tau2 <- t2; r$tau2_lower <- t2_lo; r$tau2_upper <- t2_hi
    r$I2 <- num(m, "I2"); r$Q <- num(m, "Q"); r$df_Q <- num(m, "df.Q"); r$pval_Q <- num(m, "pval.Q")
    r$glmm_max_diff <- dif
    if (pooled) {
      bb <- budget(suppressMessages(suppressWarnings(
              bootMer(gl, FUN = boot_stat, nsim = BOOT_R, type = "parametric", use.u = FALSE,
                      seed = seed_of(s$stratum)))), BOOT_SECONDS, "bootstrap not obtained:")
      if (inherits(bb, "boot")) {
        tt <- as.numeric(bb$t); tt <- tt[is.finite(tt)]; r$boot_used <- length(tt)
        if (length(tt) >= 100) {
          q <- quantile(tt, c(0.025, 0.975), names = FALSE); r$marg_lower <- q[1]; r$marg_upper <- q[2]
        } else notes <- c(notes, sprintf("only %d usable replicates: no CI", length(tt)))
      } else notes <- c(notes, attr(bb, "err"))
      cat(sprintf("%3d/%3d %-44s k=%3d  mean %.4f [%.4f-%.4f]  median %.4f  crude %.4f\n", i, nrow(ord),
                  s$stratum, s$k_collections, r$p_marginal, r$marg_lower, r$marg_upper, r$p_median, r$p_crude))
    } else {
      cat(sprintf("%3d/%3d %-44s k=%3d  tau2=%.2f CI up to %.3g  not pooled\n", i, nrow(ord),
                  s$stratum, s$k_collections, t2, t2_hi))
    }
  }
  r$note <- paste(unique(notes[nzchar(notes)]), collapse = " / ")
  r$seconds <- round(as.numeric(difftime(Sys.time(), s0, units = "secs")), 1)
  rows[[i]] <- r
}
res <- do.call(rbind, rows)
res <- res[order(res$compartment, res$outcome, res$agent, res$regime_stratum), ]
np <- sum(res$status == "pooled")
stamp <- paste0(format(Sys.time(), "%Y-%m-%dT%H%M%S"), TAG)
f_out <- file.path(RES, paste0("ma_results_v3_", stamp, ".csv"))
if (file.exists(f_out)) stop("Already exists ", f_out, ": not overwritten")
write.csv(res, f_out, row.names = FALSE)
log_dir <- file.path(RES, "logs"); dir.create(log_dir, recursive = TRUE, showWarnings = FALSE)
ins <- c(RULES, f_in, f_st); pk <- c("meta", "metafor", "lme4", "jsonlite")
sel <- nzchar(res$note); lab <- key_of(res)
write_json(list(script = "06_ma_marginal_v3.R", mode = if (PROV) "PROVISIONAL" else "FINAL",
                run_time = format(Sys.time(), "%Y-%m-%d %H:%M:%S %z"), r_version = R.version.string,
                packages = setNames(lapply(pk, function(p) as.character(packageVersion(p))), pk),
                inputs = setNames(as.list(unname(tools::md5sum(ins))), ins),
                outputs = setNames(list(unname(tools::md5sum(f_out))), basename(f_out)),
                model = list(method = "GLMM", sm = "PLOGIT", nAGQ = 7,
                             principal = "population mean, integrating the random effect",
                             marginal_nodes = NODES, boot_type = "parametric percentile", boot_r = BOOT_R,
                             seed = "SEED + function of the stratum key", seed_base = SEED,
                             median_ci = "t with k-1 df on the model standard error (meta: HK)",
                             prediction = "Higgins-Thompson-Spiegelhalter, t with k-2 df (meta: HTS)",
                             tau2 = "ML", tau2_ci = "profile likelihood, lme4", tau2_max = TAU2_MAX),
                strata = nrow(res), n_pooled = np,
                not_pooled = as.list(table(res$status[res$status != "pooled"])),
                n_unverified_main_rows = sum(res$unverified_main_rows, na.rm = TRUE),
                without_marginal_ci = sum(res$status == "pooled" & is.na(res$marg_lower)),
                glmm_max_diff = max(res$glmm_max_diff, na.rm = TRUE),
                total_seconds = round(as.numeric(difftime(Sys.time(), t0, units = "secs")), 1),
                notes = as.list(setNames(res$note[sel], lab[sel]))),
           file.path(log_dir, paste0("06_ma_marginal_v3_", stamp, ".json")), auto_unbox = TRUE, pretty = TRUE, na = "null")
cat(sprintf("\nStrata: %d; pooled: %d; not pooled: %d; without CI of the mean: %d\n", nrow(res), np,
            nrow(res) - np, sum(res$status == "pooled" & is.na(res$marg_lower))))
cat(sprintf("Maximum discrepancy meta/lme4: %.3g\nTime: %.0f s\nOutput: %s\n",
            max(res$glmm_max_diff, na.rm = TRUE), as.numeric(difftime(Sys.time(), t0, units = "secs")), f_out))
