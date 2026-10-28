#!/usr/bin/env Rscript
# 12_ma_metareg_v1.R (2026-10-24)
# Exploratory meta-regression of heterogeneity (protocol, section 9; decision D1 of 2026-10-24), rules
# 10_phase8_analysis/analysis_rules_v4_2026-10-24.md, AR21.
#   - Only strata pooled in the main analysis (ma_results_v3) with at least 10 collections with data on the
#     covariate (10 per covariate).
#   - One covariate at a time, among the registered ones that do not belong to a hypothesis deferred to the second
#     report: susceptibility method, WHO region, overall risk-of-bias judgement, species identification
#     method and editorial status. Compartment (H2), clade (H1), period and criterion version
#     (H4) are not touched here.
#   - Levels with fewer than 3 collections are grouped into "others"; if a single level remains, the covariate is not
#     fitted in that stratum.
#   - Model: one-level binomial-normal GLMM with the covariate as a fixed effect, 7-node quadrature, on
#     the same main collections; the coefficient per level against the reference (logit) is reported,
#     with the likelihood-ratio test against the model without covariate and the relative reduction of tau2.
#     It is exploratory: there is no correction for multiplicity and the total number of tests is reported.
# Usage, from the project root:
#   conda run --no-capture-output -n ctrop_ma Rscript 10_phase8_analysis/scripts/12_ma_metareg_v1.R [--provisional] [--check]

if (!dir.exists("10_phase8_analysis")) stop("Run from the project root")
suppressPackageStartupMessages({ library(lme4); library(jsonlite) })
RULES <- "10_phase8_analysis/analysis_rules_v4_2026-10-24.md"
RES <- "10_phase8_analysis/results"
ROB_DIR <- "09_phase7_risk_of_bias/results"
MIN_COL <- 10; MIN_LEVEL <- 3
KEY <- c("compartment", "agent", "outcome", "regime_stratum")
args <- commandArgs(trailingOnly = TRUE)
CHECK <- "--check" %in% args; PROV <- "--provisional" %in% args; TAG <- if (PROV) "_PROVISIONAL" else ""
newest <- function(dir, pat) {
  f <- sort(Sys.glob(file.path(dir, pat))); f <- f[grepl("_PROVISIONAL\\.csv$", f) == PROV]
  if (!length(f)) stop("There is no ", pat, if (PROV) " PROVISIONAL" else " FINAL")
  f[length(f)]
}
f_res <- newest(RES, "ma_results_v3_*.csv")
f_rob <- newest(ROB_DIR, "rob_assessment_v2_*.csv")
if (!file.exists(RULES)) stop("Missing ", RULES)
# the input is the one that 06_ma_marginal_v3.R used for that ma_results_v3 (its log), not the most recent one
lg <- file.path(RES, "logs", sub("^ma_results_v3_(.*)\\.csv$", "06_ma_marginal_v3_\\1.json", basename(f_res)))
if (!file.exists(lg)) stop("The log is missing for ", basename(f_res), ": ", lg)
f_in <- grep("ma_input_v2_", names(fromJSON(lg)$inputs), value = TRUE)
if (length(f_in) != 1 || !file.exists(f_in)) stop("The log of ", basename(f_res), " does not identify its ma_input_v2")
x <- read.csv(f_in, stringsAsFactors = FALSE, na.strings = "")
res <- read.csv(f_res, stringsAsFactors = FALSE, na.strings = c("", "NA"))
rob <- read.csv(f_rob, stringsAsFactors = FALSE, na.strings = c("", "NA"))[, c("study_id", "overall_judgement", "editorial_status")]
x$main <- as.logical(x$main)
key_of <- function(d) do.call(paste, c(unname(as.list(d[KEY])), list(sep = " | ")))
x$stratum <- key_of(x); res$stratum <- key_of(res)
d <- x[x$main & x$stratum %in% res$stratum[res$status == "pooled"], ]
n0 <- nrow(d); d <- merge(d, rob, by = "study_id", all.x = TRUE, sort = FALSE)
if (nrow(d) != n0) stop("The join with the risk of bias changed the number of rows")
without_rob <- unique(d$study_id[is.na(d$overall_judgement)])
if (length(without_rob)) stop("Main reports without a risk-of-bias judgement: ", paste(head(without_rob, 5), collapse = ", "),
                          ". Run derive_rob_judgement_v2.py on the same dataset.")
d$events <- as.integer(round(d$events)); d$n_tested <- as.integer(round(d$n_tested))

METHOD_GROUP <- c("1" = "reference broth microdilution", "2" = "commercial microdilution or automated",
                  "3" = "gradient diffusion", "4" = "disk diffusion", "5" = "other")
COVS <- list(
  method = function(z) unname(METHOD_GROUP[as.character(z$method_rank)]),
  who_region = function(z) z$who_region,
  rob_high = function(z) ifelse(is.na(z$overall_judgement), NA, ifelse(z$overall_judgement == "High", "high", "low or moderate")),
  # not_specified is missing data, not phenotypic: those collections leave this model
  species_id = function(z) ifelse(z$species_id_v3 %in% c("molecular", "MALDI_TOF"), "molecular or MALDI-TOF",
                                  ifelse(z$species_id_v3 %in% c("biochemical", "automated", "chromogenic", "conventional"),
                                         "phenotypic", NA)),
  editorial = function(z) ifelse(is.na(z$editorial_status), NA, ifelse(z$editorial_status == "peer_reviewed",
                                                                     "peer reviewed", "preprint or grey"))
)
out <- list(); n_tests <- 0
for (s in sort(unique(d$stratum))) {
  g0 <- d[d$stratum == s, ]
  for (cv in names(COVS)) {
    g <- g0; g$cov <- COVS[[cv]](g); g <- g[!is.na(g$cov), ]
    row <- data.frame(stratum = s, covariate = cv, k = nrow(g), levels = NA_character_, status = NA_character_,
                      lrt_chisq = NA_real_, lrt_df = NA_real_, lrt_p = NA_real_, tau2_null = NA_real_,
                      tau2_cov = NA_real_, tau2_reduction = NA_real_, coefficients = NA_character_,
                      stringsAsFactors = FALSE)
    if (nrow(g) < MIN_COL) { row$status <- "fewer_than_10_collections"; out[[length(out) + 1]] <- row; next }
    OTHER <- "other levels (fewer than 3 collections each)"
    tb <- table(g$cov); small <- names(tb)[tb < MIN_LEVEL]
    if (length(small)) g$cov[g$cov %in% small] <- OTHER
    tb <- table(g$cov)
    if (OTHER %in% names(tb) && tb[[OTHER]] < MIN_LEVEL) { g <- g[g$cov != OTHER, ]; tb <- table(g$cov) }
    row$k <- nrow(g)
    if (length(tb) < 2 || nrow(g) < MIN_COL) {
      row$status <- "single_usable_level"; row$levels <- paste(names(tb), tb, sep = ": ", collapse = "; ")
      out[[length(out) + 1]] <- row; next
    }
    ref <- names(tb)[which.max(tb)]
    g$cov <- relevel(factor(g$cov), ref = ref)
    row$levels <- paste(names(tb), tb, sep = ": ", collapse = "; ")
    if (CHECK && length(out) > 3) { row$status <- "not_fitted_in_check"; out[[length(out) + 1]] <- row; next }
    m0 <- try(suppressMessages(suppressWarnings(glmer(cbind(events, n_tested - events) ~ 1 + (1 | collection_id),
                                                      data = g, family = binomial, nAGQ = 7L))), silent = TRUE)
    m1 <- try(suppressMessages(suppressWarnings(glmer(cbind(events, n_tested - events) ~ cov + (1 | collection_id),
                                                      data = g, family = binomial, nAGQ = 7L))), silent = TRUE)
    if (inherits(m0, "try-error") || inherits(m1, "try-error")) {
      row$status <- "no_fit"; out[[length(out) + 1]] <- row; next
    }
    n_tests <- n_tests + 1
    ll0 <- as.numeric(logLik(m0)); ll1 <- as.numeric(logLik(m1)); df <- length(fixef(m1)) - 1
    row$lrt_chisq <- 2 * (ll1 - ll0); row$lrt_df <- df; row$lrt_p <- pchisq(row$lrt_chisq, df, lower.tail = FALSE)
    row$tau2_null <- as.numeric(VarCorr(m0)[[1]])[1]; row$tau2_cov <- as.numeric(VarCorr(m1)[[1]])[1]
    row$tau2_reduction <- if (row$tau2_null > 0) (row$tau2_null - row$tau2_cov) / row$tau2_null else NA_real_
    fe <- fixef(m1); se <- sqrt(diag(as.matrix(vcov(m1))))
    nm <- setdiff(names(fe), "(Intercept)")
    row$coefficients <- paste(sprintf("%s: %.3f (%.3f to %.3f)", sub("^cov", "", nm), fe[nm], fe[nm] - 1.96 * se[nm],
                                      fe[nm] + 1.96 * se[nm]), collapse = "; ")
    row$status <- "fitted"
    out[[length(out) + 1]] <- row
  }
}
tab <- do.call(rbind, out)
cat(sprintf("Strata pooled: %d; tests fitted: %d\n", length(unique(d$stratum)), n_tests))
print(table(tab$covariate, tab$status))
if (!CHECK) {
  stamp <- paste0(format(Sys.time(), "%Y-%m-%dT%H%M%S"), TAG)
  f_out <- file.path(RES, paste0("ma_metareg_v1_", stamp, ".csv"))
  if (file.exists(f_out)) stop("Already exists ", f_out)
  write.csv(tab, f_out, row.names = FALSE)
  log_dir <- file.path(RES, "logs"); dir.create(log_dir, recursive = TRUE, showWarnings = FALSE)
  ins <- c(RULES, f_in, f_res, f_rob)
  write_json(list(script = "12_ma_metareg_v1.R", mode = if (PROV) "PROVISIONAL" else "FINAL",
                  run_time = format(Sys.time(), "%Y-%m-%d %H:%M:%S %z"), r_version = R.version.string,
                  lme4 = as.character(packageVersion("lme4")),
                  inputs = setNames(as.list(unname(tools::md5sum(ins))), ins),
                  outputs = setNames(list(unname(tools::md5sum(f_out))), basename(f_out)),
                  min_collections = MIN_COL, min_level = MIN_LEVEL, tests = n_tests,
                  note = "exploratory; no correction for multiplicity; covariates of deferred hypotheses excluded (D1)"),
             file.path(log_dir, paste0("12_ma_metareg_v1_", stamp, ".json")), auto_unbox = TRUE, pretty = TRUE, na = "null")
  cat("Output:", f_out, "\n")
}
