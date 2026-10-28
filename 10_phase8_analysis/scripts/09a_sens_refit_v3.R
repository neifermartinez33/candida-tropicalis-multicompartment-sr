#!/usr/bin/env Rscript
# 09a_sens_refit_v3.R (2026-10-24)
# Sensitivity analyses of the refit family, rules 10_phase8_analysis/analysis_rules_v4_2026-10-24.md,
# on ma_input_v2. Each analysis changes the subset of rows or the estimator and reapplies AR12 and AR18. The
# contrasts between levels of a factor are in 09b_sens_contrast_v3.R (AR19).
#
# Changes from v2:
#   1. AR2 is recomputed within each subset that removes rows (SX1, SX2, SX3, SA1, SA2): if the main
#      report of a collection leaves, the next report of the same collection enters, instead of losing the
#      collection. SA9 follows its registered rule (rob_rules, section 6): the collection whose main
#      report is at high risk leaves.
#   2. The strata of each analysis are those that meet AR12 in that subset, not only those of the main analysis:
#      SA1 and SX3 can create strata that the main analysis does not have.
#   3. SA1 is run: the main analysis uses the strict reading of C5 and SA1 the broad one (registered hierarchy).
#   4. SX3, new and declared: brings back the rows that AR20 removes from the main analysis.
#   5. SA11 compares the nested model (collections within country, Laplace, the only approximation that lme4 admits with two
#      levels) with the one-level model fitted with the same approximation, so that the difference does not mix
#      the structure with the approximation. Each multinational collection is its own country group.
#   6. SA10a, SA10b and SA11 carry the status of the stratum in the main analysis: a stratum not pooled there is reported
#      as such even if the alternative estimator gives a number.
#   7. The seeds come from the key of the stratum and of the analysis; the CSVs per analysis carry the MD5 of the
#      input in the name, so a result computed on another input is never reused.
#   8. The strata of the main analysis that do not reach AR12 in a subset appear as rows with status
#      below_AR12_in_subset (v2 omitted them and the loss was not visible).
#   9. (2026-10-27) SA11: a stratum whose summed variance exceeds TAU2_MAX at its point estimate is not pooled
#      (amphotericin B, CLSI ECV, had a Laplace marginal mean outside its own bootstrap CI).
#
# Usage, from the project root:
#   conda run --no-capture-output -n ctrop_ma Rscript 10_phase8_analysis/scripts/09a_sens_refit_v3.R --check [--provisional]
#   conda run --no-capture-output -n ctrop_ma Rscript 10_phase8_analysis/scripts/09a_sens_refit_v3.R [--provisional] [--only=SA1,SX3]
# --check: inputs, joins and formulas on one stratum per analysis, without bootstrap or profile, in seconds.

if (!dir.exists("10_phase8_analysis")) stop("Run from the project root")
suppressPackageStartupMessages({ library(meta); library(metafor); library(lme4); library(jsonlite) })

RULES <- "10_phase8_analysis/analysis_rules_v4_2026-10-24.md"
RES <- "10_phase8_analysis/results"
SENS <- file.path(RES, "sensitivity")
ROB_DIR <- "09_phase7_risk_of_bias/results"
TAU2_MAX <- 25; BOOT_R <- 999; SEED <- 20261025; NODES <- 4096
MIN_K <- 5; MIN_G <- 2
PROFILE_SECONDS <- 180; BOOT_SECONDS <- 900
KEY <- c("compartment", "agent", "outcome", "regime_stratum")
SX1_FLAGS <- "pre2012_doc_published_2013plus|inferred_from_year|inferred_from_cutoffs"
ZQ <- qnorm((seq_len(NODES) - 0.5) / NODES)

args <- commandArgs(trailingOnly = TRUE)
CHECK <- "--check" %in% args
PROV <- "--provisional" %in% args
TAG <- if (PROV) "_PROVISIONAL" else ""
ONLY <- sub("^--only=", "", grep("^--only=", args, value = TRUE))
ONLY <- if (length(ONLY)) trimws(strsplit(ONLY[1], ",")[[1]]) else character(0)

newest <- function(dir, pat) {
  f <- sort(Sys.glob(file.path(dir, pat)))
  f <- f[grepl("_PROVISIONAL\\.csv$", f) == PROV]
  if (!length(f)) stop("There is no ", pat, if (PROV) " PROVISIONAL" else " FINAL", " in ", dir)
  f[length(f)]
}
seed_of <- function(s) SEED + sum(utf8ToInt(s) * seq_along(utf8ToInt(s))) %% 100000L

f_in <- newest(RES, "ma_input_v2_*.csv")
stamp_in <- sub("^ma_input_v2_(.*)\\.csv$", "\\1", basename(f_in))
f_st <- file.path(RES, paste0("ma_strata_v2_", stamp_in, ".csv"))
f_main <- newest(RES, "ma_results_v3_*.csv")
for (f in c(RULES, f_st, f_main)) if (!file.exists(f)) stop("Missing ", f)
md5_in <- substr(unname(tools::md5sum(f_in)), 1, 8)

x <- read.csv(f_in, stringsAsFactors = FALSE, na.strings = "")
st <- read.csv(f_st, stringsAsFactors = FALSE, na.strings = "")
mainres <- read.csv(f_main, stringsAsFactors = FALSE, na.strings = c("", "NA"))
for (cc in c("main", "sel_main", "sel_all", "c5_broad", "ar20")) x[[cc]] <- as.logical(x[[cc]])
key_of <- function(d) do.call(paste, c(unname(as.list(d[KEY])), list(sep = " | ")))
x$stratum <- key_of(x); mainres$stratum <- key_of(mainres)
x$events <- as.integer(round(x$events)); x$n_tested <- as.integer(round(x$n_tested))
stopifnot(!anyNA(x$events), !anyNA(x$n_tested), all(x$n_tested > 0), all(x$events >= 0),
          all(x$events <= x$n_tested))
# country group for SA11: each multinational collection is its own group
x$country_group <- ifelse(is.na(x$country_iso3) | x$country_iso3 == "MULTI",
                          paste0("MULTI_", x$collection_id), x$country_iso3)

# --- phase 7: judgement per report (SA9) and editorial status (SA2) --------------------------------------------
f_rob <- tryCatch(newest(ROB_DIR, "rob_assessment_v2_*.csv"), error = function(e) NA_character_)
x$overall_judgement <- NA_character_; x$editorial_status <- NA_character_
if (!is.na(f_rob)) {
  rb <- read.csv(f_rob, stringsAsFactors = FALSE, na.strings = c("", "NA"))
  rb <- unique(rb[, c("study_id", "overall_judgement", "editorial_status")])
  if (any(duplicated(rb$study_id))) stop("The risk-of-bias judgement carries a report twice")
  n0 <- nrow(x); x$overall_judgement <- NULL; x$editorial_status <- NULL
  x <- merge(x, rb, by = "study_id", all.x = TRUE, sort = FALSE)
  if (nrow(x) != n0) stop("The join with the risk-of-bias judgement changed the number of rows")
  x$stratum <- key_of(x)
  falt <- unique(x$study_id[x$main & is.na(x$overall_judgement)])
  cat(sprintf("Phase 7: %s | main reports without judgement: %d\n", basename(f_rob), length(falt)))
  if (length(falt)) stop("There are main reports without a risk-of-bias judgement: ", paste(head(falt, 5), collapse = ", "),
                         ". Run derive_rob_judgement_v2.py on the same dataset.")
}

# AR2 within a subset: one report per collection and stratum, the one with most isolates tested
ar2 <- function(d) {
  d <- d[order(-d$n_tested, -d$year, d$study_id), ]
  d[!duplicated(paste(d$stratum, d$collection_id)), ]
}
base <- x[x$sel_main & !x$c5_broad, ]          # candidate rows of the main analysis (without AR20, strict C5)
principal <- x[x$main, ]
if (!isTRUE(all.equal(sort(paste(ar2(base)$stratum, ar2(base)$row_id)),
                      sort(paste(principal$stratum, principal$row_id)))))
  stop("AR2 recomputed on the rows of the main analysis does not reproduce the main flag of ma_input: do not continue, report it")

ANALYSES <- list(
  SA3 = list(label = "Each report as an independent unit",
             subset = function() base, unit = "study_id", est = "glmm"),
  SX1 = list(label = "Without rows with an inferred version or an earlier document in a recent publication",
             subset = function() ar2(base[is.na(base$regime_flag) | !grepl(SX1_FLAGS, base$regime_flag), ]),
             unit = "collection_id", est = "glmm"),
  SX2 = list(label = "Without assumed breakpoint type",
             subset = function() ar2(base[is.na(base$bp_type) | base$bp_type != "CBP_assumed", ]),
             unit = "collection_id", est = "glmm"),
  SX3 = list(label = "With the rows that AR20 removes (selected samples, inferred denominator, compiled datasets)",
             subset = function() ar2(x[x$sel_all & !x$c5_broad, ]), unit = "collection_id", est = "glmm"),
  SA1 = list(label = "C5 in broad reading",
             subset = function() { d <- ar2(x[x$sel_main, ]); d[d$compartment == "C5", ] },
             unit = "collection_id", est = "glmm"),
  SA9 = list(label = "Without collections whose main report is at high risk",
             subset = function() {
               if (all(is.na(x$overall_judgement))) stop("SA9 requires rob_assessment_v2 (derive_rob_judgement_v2.py)")
               principal[!(principal$overall_judgement %in% "High"), ]
             }, unit = "collection_id", est = "glmm"),
  SA2 = list(label = "Without preprints",
             subset = function() {
               if (all(is.na(x$editorial_status))) stop("SA2 requires rob_assessment_v2 (derive_rob_judgement_v2.py)")
               ar2(base[is.na(base$editorial_status) | base$editorial_status != "preprint", ])
             }, unit = "collection_id", est = "glmm"),
  SA10a = list(label = "Inverse-variance logit with continuity correction",
               subset = function() principal, unit = "collection_id", est = "iv"),
  SA10b = list(label = "Freeman-Tukey double arcsine",
               subset = function() principal, unit = "collection_id", est = "pft"),
  SA11 = list(label = "Collections nested within country",
              subset = function() principal, unit = "collection_id", est = "glmm_country")
)
if (length(ONLY)) {
  missing <- setdiff(ONLY, names(ANALYSES))
  if (length(missing)) stop("Unknown analysis: ", paste(missing, collapse = ", "))
  ANALYSES <- ANALYSES[ONLY]
}

num <- function(o, f) { v <- o[[f]]; if (is.null(v) || !length(v)) NA_real_ else as.numeric(v)[1] }
marginal <- function(mu, tau2) {
  if (!is.finite(mu) || !is.finite(tau2)) return(NA_real_)
  if (tau2 <= 0) return(plogis(mu))
  mean(plogis(mu + sqrt(tau2) * ZQ))
}
budget <- function(expr, seconds, msg) {
  tryCatch({ setTimeLimit(elapsed = seconds, transient = FALSE); expr },
           error = function(e) structure(NA_real_, err = paste(msg, conditionMessage(e))),
           finally = setTimeLimit(elapsed = Inf, transient = FALSE))
}
FIELDS <- c("p_point", "p_lower", "p_upper", "p_median", "med_lower", "med_upper", "pi_lower", "pi_upper",
            "tau2", "tau2_lower", "tau2_upper", "boot_used", "p_ref_laplace", "tau2_ref_laplace")
blank <- as.data.frame(setNames(rep(list(NA_real_), length(FIELDS)), FIELDS))

ajusta <- function(g, est, seed) {
  notes <- character(0); out <- as.list(blank); status <- "pooled"
  ev <- sum(g$events); nn <- sum(g$n_tested)
  if (ev == 0 || ev == nn) return(list(v = out, status = "not_pooled_boundary_AR18a", notes = notes))
  if (est %in% c("iv", "pft")) {
    cl <- list(event = quote(events), n = quote(n_tested), studlab = quote(unit), data = g,
               method = "Inverse", sm = if (est == "iv") "PLOGIT" else "PFT", common = FALSE, random = TRUE,
               method.random.ci = "HK", method.predict = "HTS", prediction = TRUE, method.tau = "DL")
    if (est == "iv") cl$incr <- 0.5
    m <- withCallingHandlers(do.call(metaprop, cl),
      warning = function(w) { notes <<- c(notes, conditionMessage(w)); invokeRestart("muffleWarning") })
    bt <- if (est == "iv") plogis else function(z) metafor::transf.ipft.hm(z, targs = list(ni = g$n_tested))
    out$p_point <- bt(num(m, "TE.random"))
    out$p_lower <- bt(num(m, "lower.random")); out$p_upper <- bt(num(m, "upper.random"))
    out$p_median <- out$p_point; out$med_lower <- out$p_lower; out$med_upper <- out$p_upper
    out$pi_lower <- bt(num(m, "lower.predict")); out$pi_upper <- bt(num(m, "upper.predict"))
    out$tau2 <- if (est == "iv") num(m, "tau2") else NA_real_
    if (est == "pft") notes <- c(notes, "tau2 on the arcsine scale, not comparable with that of the GLMM")
    return(list(v = out, status = "estimated_alternative_estimator", notes = notes))
  }
  f1 <- cbind(events, n_tested - events) ~ 1 + (1 | unit)
  f2 <- cbind(events, n_tested - events) ~ 1 + (1 | country_group / unit)
  gl <- try(suppressMessages(suppressWarnings(
    glmer(if (est == "glmm_country") f2 else f1, data = g, family = binomial,
          nAGQ = if (est == "glmm_country") 1L else 7L))), silent = TRUE)
  if (inherits(gl, "try-error")) return(list(v = out, status = "no_fit", notes = "the GLMM was not fitted"))
  mu <- as.numeric(fixef(gl))[1]
  t2 <- sum(as.numeric(unlist(lapply(VarCorr(gl), function(z) z[1]))))
  m <- withCallingHandlers(
    metaprop(event = events, n = n_tested, studlab = unit, data = g, method = "GLMM", sm = "PLOGIT",
             common = FALSE, random = TRUE, method.random.ci = "HK", method.predict = "HTS", prediction = TRUE),
    warning = function(w) { notes <<- c(notes, conditionMessage(w)); invokeRestart("muffleWarning") })
  out$p_median <- plogis(num(m, "TE.random"))
  out$med_lower <- plogis(num(m, "lower.random")); out$med_upper <- plogis(num(m, "upper.random"))
  out$pi_lower <- plogis(num(m, "lower.predict")); out$pi_upper <- plogis(num(m, "upper.predict"))
  out$tau2 <- t2; out$p_point <- marginal(mu, t2)
  if (est == "glmm_country") {
    # reference: the one-level model with the same Laplace approximation
    ref <- try(suppressMessages(suppressWarnings(glmer(f1, data = g, family = binomial, nAGQ = 1L))), silent = TRUE)
    if (!inherits(ref, "try-error")) {
      t2r <- as.numeric(VarCorr(ref)[[1]])[1]
      out$tau2_ref_laplace <- t2r
      out$p_ref_laplace <- marginal(as.numeric(fixef(ref))[1], t2r)
    } else notes <- c(notes, "the one-level reference model was not fitted")
    notes <- c(notes, "AR18 is not reapplied: its criterion is defined on the variance of a single level")
    # 2026-10-27: a summed variance whose point estimate already exceeds TAU2_MAX implies an upper limit above it,
    # so the stratum is not pooled (the Laplace marginal mean is unreliable there and its bootstrap CI excluded it)
    status <- if (is.finite(t2) && t2 > TAU2_MAX) "not_pooled_tau2_AR18b" else "pooled"
  }
  if (CHECK) return(list(v = out, status = "check_only", notes = notes))
  if (est == "glmm") {
    pr <- budget(suppressMessages(suppressWarnings(confint(gl, parm = "theta_", method = "profile", quiet = TRUE))),
                 PROFILE_SECONDS, "tau2 profile not obtained:")
    if (is.matrix(pr)) {
      out$tau2_lower <- as.numeric(pr[1, 1])^2; out$tau2_upper <- as.numeric(pr[1, 2])^2
    } else notes <- c(notes, attr(pr, "err"))
    status <- if (is.finite(out$tau2_upper) && out$tau2_upper <= TAU2_MAX) "pooled" else
      if (is.finite(out$tau2_upper)) "not_pooled_tau2_AR18b" else "not_pooled_no_profile_AR18c"
  }
  if (status == "pooled") {
    bstat <- function(fit) marginal(as.numeric(fixef(fit))[1], sum(as.numeric(unlist(lapply(VarCorr(fit), function(z) z[1])))))
    bb <- budget(suppressMessages(suppressWarnings(
            bootMer(gl, FUN = bstat, nsim = BOOT_R, type = "parametric", use.u = FALSE, seed = seed))),
          BOOT_SECONDS, "bootstrap not obtained:")
    if (inherits(bb, "boot")) {
      tt <- as.numeric(bb$t); tt <- tt[is.finite(tt)]; out$boot_used <- length(tt)
      if (length(tt) >= 100) {
        q <- quantile(tt, c(0.025, 0.975), names = FALSE); out$p_lower <- q[1]; out$p_upper <- q[2]
      } else notes <- c(notes, sprintf("only %d usable replicates: no CI", length(tt)))
    } else notes <- c(notes, attr(bb, "err"))
  }
  list(v = out, status = status, notes = notes)
}

dir.create(SENS, recursive = TRUE, showWarnings = FALSE)
t0 <- Sys.time(); done_list <- list()
mstat <- setNames(mainres$status, mainres$stratum)
cat(sprintf("Input %s%s\nAnalyses: %s%s\n", basename(f_in), if (PROV) " [PROVISIONAL]" else "",
            paste(names(ANALYSES), collapse = ", "), if (CHECK) "   [--check]" else ""))
for (nm in names(ANALYSES)) {
  a <- ANALYSES[[nm]]
  f_out <- file.path(SENS, paste0("sens_", nm, "_v3_", md5_in, TAG, ".csv"))
  if (!CHECK && file.exists(f_out)) {
    cat("  ", nm, "already computed on this same input, reused\n")
    done_list[[nm]] <- read.csv(f_out, stringsAsFactors = FALSE, na.strings = c("", "NA")); next
  }
  d <- a$subset()
  d$unit <- d[[a$unit]]
  if (any(duplicated(paste(d$stratum, d$unit)))) stop(nm, ": there are repeated units in a stratum")
  ku <- tapply(d$unit, d$stratum, function(v) length(unique(v)))
  gr <- tapply(d$research_group, d$stratum, function(v) length(unique(v)))[names(ku)]
  eligible <- names(ku)[ku >= MIN_K & gr >= MIN_G]
  if (a$est %in% c("iv", "pft", "glmm_country")) eligible <- intersect(eligible, names(mstat))
  if (CHECK) eligible <- head(eligible[order(ku[eligible])], 1)
  cat(sprintf("\n%s  %s\n  rows %d, strata that meet AR12 in this subset: %d\n", nm, a$label,
              nrow(d), length(eligible)))
  rows <- list()
  for (i in seq_along(eligible)) {
    s <- eligible[i]; g <- d[d$stratum == s, ]; s0 <- Sys.time()
    r <- try(ajusta(g, a$est, seed_of(paste(nm, s))), silent = TRUE)
    if (inherits(r, "try-error"))
      r <- list(v = as.list(blank), status = "fit_error", notes = paste("failure:", conditionMessage(attr(r, "condition"))))
    ms <- if (s %in% names(mstat)) mstat[[s]] else "not_estimable_in_main"
    if (a$est %in% c("iv", "pft", "glmm_country") && ms != "pooled")
      r$notes <- c(r$notes, paste("stratum", ms, "in the main analysis"))
    base_k <- g[1, KEY]; rownames(base_k) <- NULL
    rows[[i]] <- cbind(data.frame(analysis = nm, label = a$label, estimator = a$est, unit = a$unit,
                                   stringsAsFactors = FALSE), base_k,
                        data.frame(k_units = length(unique(g$unit)), research_groups = length(unique(g$research_group)),
                                   events = sum(g$events), isolates = sum(g$n_tested),
                                   p_crude = sum(g$events) / sum(g$n_tested)),
                        as.data.frame(r$v),
                        data.frame(status = r$status, main_status = ms, seed = seed_of(paste(nm, s)),
                                   seconds = round(as.numeric(difftime(Sys.time(), s0, units = "secs")), 1),
                                   note = paste(unique(r$notes[nzchar(r$notes)]), collapse = " / "),
                                   stringsAsFactors = FALSE))
    cat(sprintf("  %3d/%3d %-44s k=%3d  %-28s p=%.4f\n", i, length(eligible), s, rows[[i]]$k_units,
                r$status, rows[[i]]$p_point))
  }
  # strata of the main analysis that do not reach AR12 in this subset: they are reported, they do not disappear
  rel <- names(mstat)
  if (nm == "SA1") rel <- rel[startsWith(rel, "C5 | ")]
  below_min <- if (CHECK) character(0) else setdiff(rel, eligible)
  for (s in below_min) {
    g <- d[d$stratum == s, ]
    kk <- strsplit(s, " | ", fixed = TRUE)[[1]]
    rows[[length(rows) + 1]] <- cbind(
      data.frame(analysis = nm, label = a$label, estimator = a$est, unit = a$unit,
                 compartment = kk[1], agent = kk[2], outcome = kk[3], regime_stratum = kk[4],
                 k_units = length(unique(g$unit)), research_groups = length(unique(g$research_group)),
                 events = sum(g$events), isolates = sum(g$n_tested),
                 p_crude = if (nrow(g)) sum(g$events) / sum(g$n_tested) else NA_real_, stringsAsFactors = FALSE),
      blank,
      data.frame(status = "below_AR12_in_subset", main_status = mstat[[s]], seed = NA_real_,
                 seconds = 0, note = "", stringsAsFactors = FALSE))
  }
  if (length(below_min)) cat(sprintf("  strata of the main analysis below AR12 in this subset: %d\n", length(below_min)))
  res <- if (length(rows)) do.call(rbind, rows) else NULL
  if (is.null(res)) {
    cat("  no strata that meet AR12: the analysis has no object with these data\n")
    res <- data.frame(analysis = nm, label = a$label, estimator = a$est, unit = a$unit,
                      status = "no_strata_meeting_AR12", stringsAsFactors = FALSE)
  }
  if (!CHECK) write.csv(res, f_out, row.names = FALSE)
  done_list[[nm]] <- res
}

all_rows <- do.call(rbind, lapply(done_list, function(h) {
  for (cc in setdiff(unique(unlist(lapply(done_list, names))), names(h))) h[[cc]] <- NA
  h[, sort(names(h))]
}))
all_rows$stratum <- ifelse(is.na(all_rows$compartment), NA_character_, key_of(all_rows))
mr <- mainres[, c("stratum", "p_marginal", "p_median", "tau2", "k_collections")]
names(mr) <- c("stratum", "main_p", "main_median", "main_tau2", "main_k")
all_rows <- merge(all_rows, mr, by = "stratum", all.x = TRUE, sort = FALSE)
all_rows$delta_p <- all_rows$p_point - all_rows$main_p              # AR19: never alone
all_rows$delta_median <- all_rows$p_median - all_rows$main_median
all_rows$delta_tau2 <- all_rows$tau2 - all_rows$main_tau2
all_rows$delta_p_vs_laplace <- all_rows$p_point - all_rows$p_ref_laplace   # SA11 against its one-level reference
all_rows <- all_rows[order(all_rows$analysis, all_rows$compartment, all_rows$outcome, all_rows$agent, all_rows$regime_stratum), ]
stamp <- paste0(format(Sys.time(), "%Y-%m-%dT%H%M%S"), TAG)
if (!CHECK) {
  f_all <- file.path(RES, paste0("ma_sensitivity_refit_v3_", stamp, ".csv"))
  if (file.exists(f_all)) stop("Already exists ", f_all)
  write.csv(all_rows, f_all, row.names = FALSE)
  log_dir <- file.path(RES, "logs"); dir.create(log_dir, recursive = TRUE, showWarnings = FALSE)
  ins <- c(RULES, f_in, f_st, f_main, if (!is.na(f_rob)) f_rob)
  pk <- c("meta", "metafor", "lme4", "jsonlite")
  write_json(list(script = "09a_sens_refit_v3.R", mode = if (PROV) "PROVISIONAL" else "FINAL",
                  run_time = format(Sys.time(), "%Y-%m-%d %H:%M:%S %z"), r_version = R.version.string,
                  packages = setNames(lapply(pk, function(p) as.character(packageVersion(p))), pk),
                  inputs = setNames(as.list(unname(tools::md5sum(ins))), ins),
                  outputs = setNames(list(unname(tools::md5sum(f_all))), basename(f_all)),
                  analyses = as.list(sapply(done_list, nrow)), tau2_max = TAU2_MAX, boot_r = BOOT_R,
                  seed = "SEED + function of the analysis key and of the stratum", seed_base = SEED,
                  tau2_inverse_variance = "DL (DerSimonian-Laird), because REML did not converge",
                  sa11 = "nested with Laplace against one level with Laplace; groups MULTI_<collection>",
                  min_k = MIN_K, min_groups = MIN_G,
                  statuses = as.list(table(all_rows$status)),
                  total_seconds = round(as.numeric(difftime(Sys.time(), t0, units = "secs")), 1)),
             file.path(log_dir, paste0("09a_sens_refit_v3_", stamp, ".json")), auto_unbox = TRUE, pretty = TRUE, na = "null")
  cat("\nOutput:", f_all, "\n")
} else cat("\n--check finished: inputs, joins and formulas validated. Nothing was written.\n")
cat(sprintf("Rows: %d. Time: %.0f s\n", nrow(all_rows), as.numeric(difftime(Sys.time(), t0, units = "secs"))))
