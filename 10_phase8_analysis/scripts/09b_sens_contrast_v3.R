#!/usr/bin/env Rscript
# 09b_sens_contrast_v3.R (2026-10-24)
# Sensitivity analyses that are CONTRASTS between two levels of a factor (AR19), rules
# 10_phase8_analysis/analysis_rules_v4_2026-10-24.md, on ma_input_v2.
#
# Changes from v2:
#   1. Unpaired contrasts (SA4, SA7, SA8): the model with its own variances per level has a separable
#      likelihood, so it is fitted as two one-level GLMMs, one per level, with 7-node quadrature (v2
#      used the joint model with Laplace, the only approximation that lme4 admits with two terms). The
#      logit contrast is mu_a - mu_b with standard error the square root of the sum of the squares, which is that of the
#      joint model because the covariance between levels is zero. The difference in marginal means carries a CI
#      from two independent parametric bootstraps, one per level.
#   2. Estimability: each level must meet AR12 and AR18 separately (ceiling of the profiled tau2 CI <= 25).
#   3. SA7 compares CLSI regimes (field regime), so that for fluconazole the CLSI rows of the combined stratum
#      CLSI_SS+EUCAST enter; v2 looked for CLSI_SS in regime_stratum and fluconazole was left out. In SA4 and SA7
#      AR2 is recomputed within each regime.
#   4. SA5 (paired) pairs each non-wild-type row with the resistance row of the same standard (CLSI ECV with
#      CLSI CBP, EUCAST ECV with EUCAST CBP), one per collection and outcome; shared-intercept model
#      with 7-node quadrature; AR18 on the shared variance.
#   6. SA8: collections with unspecified species identification are left out (v2 counted them as
#      phenotypic).
#   5. Seeds by cell key; CSV per analysis with the MD5 of the input in the name.
#   7. (2026-10-24, afternoon) In the unpaired ones the collections present in both levels are counted
#      (k_shared): AR19 assumes each collection in a single level; if there are shared ones, the covariance between
#      levels is not zero and the CI of the contrast is conservative. It is declared in the note of the cell; the
#      estimator is not changed (team decision pending).
#
# Usage, from the project root:
#   conda run --no-capture-output -n ctrop_ma Rscript 10_phase8_analysis/scripts/09b_sens_contrast_v3.R --check [--provisional]
#   conda run --no-capture-output -n ctrop_ma Rscript 10_phase8_analysis/scripts/09b_sens_contrast_v3.R [--provisional] [--only=SA7]

if (!dir.exists("10_phase8_analysis")) stop("Run from the project root")
suppressPackageStartupMessages({ library(lme4); library(jsonlite) })

RULES <- "10_phase8_analysis/analysis_rules_v4_2026-10-24.md"
RES <- "10_phase8_analysis/results"
SENS <- file.path(RES, "sensitivity")
BOOT_R <- 999; SEED <- 20261026; NODES <- 4096; TAU2_MAX <- 25
MIN_K <- 5; MIN_G <- 2
PROFILE_SECONDS <- 180; BOOT_SECONDS <- 900
ZQ <- qnorm((seq_len(NODES) - 0.5) / NODES)
KEY <- c("compartment", "agent", "outcome", "regime_stratum")

args <- commandArgs(trailingOnly = TRUE)
CHECK <- "--check" %in% args
PROV <- "--provisional" %in% args
TAG <- if (PROV) "_PROVISIONAL" else ""
ONLY <- sub("^--only=", "", grep("^--only=", args, value = TRUE))
ONLY <- if (length(ONLY)) trimws(strsplit(ONLY[1], ",")[[1]]) else character(0)

newest <- function(pat) {
  f <- sort(Sys.glob(file.path(RES, pat)))
  f <- f[grepl("_PROVISIONAL\\.csv$", f) == PROV]
  if (!length(f)) stop("There is no ", pat, if (PROV) " PROVISIONAL" else " FINAL")
  f[length(f)]
}
seed_of <- function(s) SEED + sum(utf8ToInt(s) * seq_along(utf8ToInt(s))) %% 100000L
f_in <- newest("ma_input_v2_*.csv")
if (!file.exists(RULES)) stop("Missing ", RULES)
md5_in <- substr(unname(tools::md5sum(f_in)), 1, 8)
x <- read.csv(f_in, stringsAsFactors = FALSE, na.strings = "")
for (cc in c("main", "sel_main", "sel_all", "c5_broad", "ar20")) x[[cc]] <- as.logical(x[[cc]])
x$events <- as.integer(round(x$events)); x$n_tested <- as.integer(round(x$n_tested))
stopifnot(!anyNA(x$events), !anyNA(x$n_tested), all(x$n_tested > 0), all(x$events >= 0), all(x$events <= x$n_tested))
# not_specified is missing data: those collections do not enter SA8 (v2 counted them as phenotypic)
x$idmol <- ifelse(x$species_id_v3 %in% c("molecular", "MALDI_TOF"), "molecular",
                  ifelse(x$species_id_v3 %in% c("biochemical", "automated", "chromogenic", "conventional"),
                         "phenotypic", NA_character_))
x$standard <- ifelse(x$regime %in% c("CLSI_SS", "CLSI_pre2012", "ECV_CLSI"), "CLSI",
                     ifelse(x$regime %in% c("EUCAST", "ECV_EUCAST"), "EUCAST", NA_character_))
base <- x[x$sel_main & !x$c5_broad, ]
principal <- x[x$main, ]

# AR2 within the groups indicated
ar2_by <- function(d, cols) {
  d <- d[order(-d$n_tested, -d$year, d$study_id), ]
  d[!duplicated(do.call(paste, c(unname(as.list(d[c(cols, "collection_id")])), list(sep = "|")))), ]
}

ANALYSES <- list(
  SA4_R = list(label = "Species-specific CLSI versus EUCAST, clinical resistance", paired = FALSE,
               level_pair = c("CLSI_SS", "EUCAST"), cell = c("compartment", "agent"),
               data_ = function() { d <- ar2_by(base[base$outcome == "R", ], c("compartment", "agent", "regime"))
                                    d$level <- d$regime; d }),
  SA4_NWT = list(label = "CLSI ECV versus EUCAST ECV, non-wild type", paired = FALSE,
                 level_pair = c("ECV_CLSI", "ECV_EUCAST"), cell = c("compartment", "agent"),
                 data_ = function() { d <- principal[principal$outcome == "NWT", ]; d$level <- d$regime_stratum; d }),
  SA7 = list(label = "Species-specific CLSI versus CLSI before 2012", paired = FALSE,
             level_pair = c("CLSI_SS", "CLSI_pre2012"), cell = c("compartment", "agent"),
             data_ = function() { d <- ar2_by(base[base$outcome == "R", ], c("compartment", "agent", "regime"))
                                  d$level <- d$regime; d }),
  SA8 = list(label = "Molecular versus phenotypic identification", paired = FALSE,
             level_pair = c("molecular", "phenotypic"), cell = KEY,
             data_ = function() { d <- principal; d$level <- d$idmol; d }),
  SA5 = list(label = "Non-wild type by ECV versus clinical resistance, paired within the collection", paired = TRUE,
             level_pair = c("NWT", "R"), cell = c("compartment", "agent", "standard"),
             data_ = function() {
               d <- base[!is.na(base$standard), ]
               d <- ar2_by(d, c("compartment", "agent", "standard", "outcome"))
               d$level <- d$outcome
               cn <- tapply(d$level, paste(d$compartment, d$agent, d$standard, d$collection_id),
                            function(v) length(unique(v)))
               d[cn[paste(d$compartment, d$agent, d$standard, d$collection_id)] == 2, ]
             })
)
if (length(ONLY)) {
  missing <- setdiff(ONLY, names(ANALYSES))
  if (length(missing)) stop("Unknown analysis: ", paste(missing, collapse = ", "))
  ANALYSES <- ANALYSES[ONLY]
}

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
FIELDS <- c("k_a", "k_b", "groups_a", "groups_b", "ev_a", "n_a", "ev_b", "n_b", "crude_a", "crude_b",
            "logit_a", "logit_b", "se_a", "se_b", "logit_contrast", "se_logit", "logit_lo", "logit_hi", "p_value",
            "marg_a", "marg_b", "diff_marg", "diff_lo", "diff_hi", "tau2_a", "tau2_b", "tau2_hi_a", "tau2_hi_b",
            "boot_used_a", "boot_used_b", "k_pairs", "k_shared")
empty <- as.data.frame(setNames(rep(list(NA_real_), length(FIELDS)), FIELDS))

# one level: one-level GLMM, 7-node quadrature, tau2 profile and bootstrap of the marginal mean
level_fit <- function(dd, seed) {
  gl <- try(suppressMessages(suppressWarnings(
    glmer(cbind(events, n_tested - events) ~ 1 + (1 | collection_id), data = dd, family = binomial, nAGQ = 7L))),
    silent = TRUE)
  if (inherits(gl, "try-error")) return(list(ok = FALSE, note = "the GLMM of the level was not fitted"))
  mu <- as.numeric(fixef(gl))[1]; se <- sqrt(as.numeric(vcov(gl))[1]); t2 <- as.numeric(VarCorr(gl)[[1]])[1]
  out <- list(ok = is.finite(mu) && is.finite(se) && is.finite(t2), mu = mu, se = se, t2 = t2, t2_hi = NA_real_,
              boot = NULL, note = "")
  if (CHECK || !out$ok) return(out)
  pr <- budget(suppressMessages(suppressWarnings(confint(gl, parm = "theta_", method = "profile", quiet = TRUE))),
               PROFILE_SECONDS, "profile not obtained:")
  out$t2_hi <- if (is.matrix(pr)) as.numeric(pr[1, 2])^2 else NA_real_
  if (!is.matrix(pr)) out$note <- attr(pr, "err")
  if (is.finite(out$t2_hi) && out$t2_hi <= TAU2_MAX) {
    bstat <- function(f) marginal(as.numeric(fixef(f))[1], as.numeric(VarCorr(f)[[1]])[1])
    bb <- budget(suppressMessages(suppressWarnings(
            bootMer(gl, FUN = bstat, nsim = BOOT_R, type = "parametric", use.u = FALSE, seed = seed))),
          BOOT_SECONDS, "bootstrap not obtained:")
    if (inherits(bb, "boot")) out$boot <- as.numeric(bb$t) else out$note <- paste(out$note, attr(bb, "err"))
  }
  out
}

ajusta <- function(g, la, lb, paired, seed) {
  notes <- character(0); out <- as.list(empty)
  a <- g[g$level == la, ]; b <- g[g$level == lb, ]
  out$k_a <- length(unique(a$collection_id)); out$k_b <- length(unique(b$collection_id))
  out$groups_a <- length(unique(a$research_group)); out$groups_b <- length(unique(b$research_group))
  out$ev_a <- sum(a$events); out$n_a <- sum(a$n_tested); out$ev_b <- sum(b$events); out$n_b <- sum(b$n_tested)
  out$crude_a <- out$ev_a / out$n_a; out$crude_b <- out$ev_b / out$n_b
  if (paired) out$k_pairs <- length(intersect(a$collection_id, b$collection_id))
  if (!paired) {
    out$k_shared <- length(intersect(a$collection_id, b$collection_id))
    if (out$k_shared > 0)
      notes <- c(notes, sprintf("%d collections in both levels: non-zero covariance ignored, conservative CI of the contrast",
                                out$k_shared))
  }
  if (out$k_a < MIN_K || out$k_b < MIN_K || out$groups_a < MIN_G || out$groups_b < MIN_G)
    return(list(v = out, status = "level_below_AR12", notes = notes, model = ""))
  lim <- c(if (out$ev_a == 0) "level a without events", if (out$ev_b == 0) "level b without events",
           if (out$ev_a == out$n_a) "level a saturated", if (out$ev_b == out$n_b) "level b saturated")
  if (length(lim)) return(list(v = out, status = "boundary_no_estimator", notes = paste(lim, collapse = ", "), model = ""))
  if (!paired) {
    fa <- level_fit(a, seed); fb <- level_fit(b, seed + 1L)
    if (!fa$ok || !fb$ok) return(list(v = out, status = "no_fit", notes = c(fa$note, fb$note), model = ""))
    out$logit_a <- fa$mu; out$logit_b <- fb$mu; out$se_a <- fa$se; out$se_b <- fb$se
    out$tau2_a <- fa$t2; out$tau2_b <- fb$t2; out$tau2_hi_a <- fa$t2_hi; out$tau2_hi_b <- fb$t2_hi
    out$logit_contrast <- fa$mu - fb$mu; out$se_logit <- sqrt(fa$se^2 + fb$se^2)
    out$marg_a <- marginal(fa$mu, fa$t2); out$marg_b <- marginal(fb$mu, fb$t2); out$diff_marg <- out$marg_a - out$marg_b
    model <- "two one-level GLMMs (own variances per level), nAGQ 7"
    if (!CHECK) {
      if (!(is.finite(fa$t2_hi) && fa$t2_hi <= TAU2_MAX && is.finite(fb$t2_hi) && fb$t2_hi <= TAU2_MAX)) {
        status <- "level_not_poolable_AR18"
        notes <- c(notes, sprintf("tau2 ceiling: a %.3g, b %.3g", fa$t2_hi, fb$t2_hi))
      } else status <- "estimated"
      if (!is.null(fa$boot) && !is.null(fb$boot)) {
        dd <- fa$boot - fb$boot; dd <- dd[is.finite(dd)]
        out$boot_used_a <- sum(is.finite(fa$boot)); out$boot_used_b <- sum(is.finite(fb$boot))
        if (length(dd) >= 100) {
          q <- quantile(dd, c(0.025, 0.975), names = FALSE); out$diff_lo <- q[1]; out$diff_hi <- q[2]
        } else notes <- c(notes, "insufficient bootstrap: no CI of the difference")
      }
      notes <- c(notes, fa$note, fb$note)
    } else status <- "check_only"
  } else {
    g$level <- factor(g$level, levels = c(la, lb))
    fit <- try(suppressMessages(suppressWarnings(
      glmer(cbind(events, n_tested - events) ~ 0 + level + (1 | collection_id), data = g, family = binomial, nAGQ = 7L))),
      silent = TRUE)
    if (inherits(fit, "try-error")) return(list(v = out, status = "no_fit", notes = "the paired model was not fitted", model = ""))
    fe <- fixef(fit); V <- as.matrix(vcov(fit)); t2 <- as.numeric(VarCorr(fit)[[1]])[1]
    ia <- which(names(fe) == paste0("level", la)); ib <- which(names(fe) == paste0("level", lb))
    cc <- rep(0, length(fe)); cc[ia] <- 1; cc[ib] <- -1
    out$logit_a <- unname(fe[ia]); out$logit_b <- unname(fe[ib]); out$tau2_a <- t2; out$tau2_b <- t2
    out$logit_contrast <- as.numeric(cc %*% fe); out$se_logit <- sqrt(as.numeric(t(cc) %*% V %*% cc))
    out$marg_a <- marginal(out$logit_a, t2); out$marg_b <- marginal(out$logit_b, t2); out$diff_marg <- out$marg_a - out$marg_b
    model <- "intercept shared by collection, within-collection contrast, nAGQ 7"
    status <- if (CHECK) "check_only" else "estimated"
    if (!CHECK) {
      # AR18 on the shared variance: ceiling of the profiled tau2 CI <= 25
      pr <- budget(suppressMessages(suppressWarnings(confint(fit, parm = "theta_", method = "profile", quiet = TRUE))),
                   PROFILE_SECONDS, "profile not obtained:")
      t2_hi <- if (is.matrix(pr)) as.numeric(pr[1, 2])^2 else NA_real_
      out$tau2_hi_a <- t2_hi; out$tau2_hi_b <- t2_hi
      if (!(is.finite(t2_hi) && t2_hi <= TAU2_MAX)) {
        status <- "level_not_poolable_AR18"
        notes <- c(notes, if (is.matrix(pr)) sprintf("tau2 ceiling %.3g", t2_hi) else attr(pr, "err"))
      }
    }
    if (!CHECK && status == "estimated") {
      bstat <- function(f) {
        e <- fixef(f); t <- as.numeric(VarCorr(f)[[1]])[1]
        marginal(e[[paste0("level", la)]], t) - marginal(e[[paste0("level", lb)]], t)
      }
      bb <- budget(suppressMessages(suppressWarnings(
              bootMer(fit, FUN = bstat, nsim = BOOT_R, type = "parametric", use.u = FALSE, seed = seed))),
            BOOT_SECONDS, "bootstrap not obtained:")
      if (inherits(bb, "boot")) {
        tt <- as.numeric(bb$t); tt <- tt[is.finite(tt)]; out$boot_used_a <- length(tt)
        if (length(tt) >= 100) {
          q <- quantile(tt, c(0.025, 0.975), names = FALSE); out$diff_lo <- q[1]; out$diff_hi <- q[2]
        }
      } else notes <- c(notes, attr(bb, "err"))
    }
  }
  out$logit_lo <- out$logit_contrast - 1.96 * out$se_logit
  out$logit_hi <- out$logit_contrast + 1.96 * out$se_logit
  out$p_value <- 2 * pnorm(-abs(out$logit_contrast / out$se_logit))
  list(v = out, status = status, notes = notes, model = model)
}

dir.create(SENS, recursive = TRUE, showWarnings = FALSE)
t0 <- Sys.time(); done_list <- list()
cat(sprintf("Input %s%s\nContrasts: %s%s\n", basename(f_in), if (PROV) " [PROVISIONAL]" else "",
            paste(names(ANALYSES), collapse = ", "), if (CHECK) "   [--check]" else ""))
for (nm in names(ANALYSES)) {
  a <- ANALYSES[[nm]]
  f_out <- file.path(SENS, paste0("contrast_", nm, "_v3_", md5_in, TAG, ".csv"))
  if (!CHECK && file.exists(f_out)) {
    cat("  ", nm, "already computed on this same input, reused\n")
    done_list[[nm]] <- read.csv(f_out, stringsAsFactors = FALSE, na.strings = c("", "NA")); next
  }
  d <- a$data_()
  d <- d[d$level %in% a$level_pair, ]
  d$cell <- do.call(paste, c(unname(as.list(d[a$cell])), list(sep = " | ")))
  cells <- sort(unique(d$cell))
  if (CHECK) cells <- head(cells, 1)
  cat(sprintf("\n%s  %s\n  rows %d, candidate cells %d\n", nm, a$label, nrow(d), length(cells)))
  rows <- list()
  for (i in seq_along(cells)) {
    g <- d[d$cell == cells[i], ]; s0 <- Sys.time()
    r <- try(ajusta(g, a$level_pair[1], a$level_pair[2], a$paired, seed_of(paste(nm, cells[i]))), silent = TRUE)
    if (inherits(r, "try-error"))
      r <- list(v = as.list(empty), status = "fit_error", model = "", notes = paste("failure:", conditionMessage(attr(r, "condition"))))
    b0 <- g[1, , drop = FALSE]
    rows[[i]] <- cbind(
      data.frame(analysis = nm, label = a$label, level_a = a$level_pair[1], level_b = a$level_pair[2],
                 paired = a$paired, cell = cells[i], compartment = b0$compartment, agent = b0$agent,
                 outcome = if ("outcome" %in% a$cell) b0$outcome else NA_character_,
                 regime_stratum = if ("regime_stratum" %in% a$cell) b0$regime_stratum else NA_character_,
                 stringsAsFactors = FALSE),
      as.data.frame(r$v),
      data.frame(model = r$model, status = r$status, seed = seed_of(paste(nm, cells[i])),
                 seconds = round(as.numeric(difftime(Sys.time(), s0, units = "secs")), 1),
                 note = paste(unique(r$notes[nzchar(r$notes)]), collapse = " / "), stringsAsFactors = FALSE))
    cat(sprintf("  %3d/%3d %-40s k %3d/%3d  %-26s contrast %s\n", i, length(cells), cells[i],
                as.integer(rows[[i]]$k_a), as.integer(rows[[i]]$k_b), r$status,
                if (is.finite(rows[[i]]$logit_contrast)) sprintf("%+.3f", rows[[i]]$logit_contrast) else "NA"))
  }
  res <- if (length(rows)) do.call(rbind, rows) else
    data.frame(analysis = nm, label = a$label, status = "no_cells", stringsAsFactors = FALSE)
  if (!CHECK) write.csv(res, f_out, row.names = FALSE)
  done_list[[nm]] <- res
}
all_rows <- do.call(rbind, lapply(done_list, function(h) {
  for (cc in setdiff(unique(unlist(lapply(done_list, names))), names(h))) h[[cc]] <- NA
  h[, sort(names(h))]
}))
all_rows <- all_rows[order(all_rows$analysis, all_rows$compartment, all_rows$agent), ]
stamp <- paste0(format(Sys.time(), "%Y-%m-%dT%H%M%S"), TAG)
if (!CHECK) {
  f_all <- file.path(RES, paste0("ma_sensitivity_contrast_v3_", stamp, ".csv"))
  if (file.exists(f_all)) stop("Already exists ", f_all)
  write.csv(all_rows, f_all, row.names = FALSE)
  log_dir <- file.path(RES, "logs"); dir.create(log_dir, recursive = TRUE, showWarnings = FALSE)
  pk <- c("lme4", "jsonlite")
  write_json(list(script = "09b_sens_contrast_v3.R", mode = if (PROV) "PROVISIONAL" else "FINAL",
                  run_time = format(Sys.time(), "%Y-%m-%d %H:%M:%S %z"), r_version = R.version.string,
                  packages = setNames(lapply(pk, function(p) as.character(packageVersion(p))), pk),
                  inputs = setNames(as.list(unname(tools::md5sum(c(RULES, f_in)))), c(RULES, f_in)),
                  outputs = setNames(list(unname(tools::md5sum(f_all))), basename(f_all)),
                  rule = "AR19: logit contrast and difference in marginal means, always both",
                  unpaired = "two one-level GLMMs, nAGQ 7; SE of the contrast by sum in quadrature; CI of the difference by two independent bootstraps",
                  paired = "shared intercept, nAGQ 7", estimability = "AR12 and AR18 in each level",
                  boot_r = BOOT_R, seed_base = SEED, min_k = MIN_K, min_groups = MIN_G, tau2_max = TAU2_MAX,
                  cells = as.list(sapply(done_list, nrow)), statuses = as.list(table(all_rows$status)),
                  total_seconds = round(as.numeric(difftime(Sys.time(), t0, units = "secs")), 1)),
             file.path(log_dir, paste0("09b_sens_contrast_v3_", stamp, ".json")), auto_unbox = TRUE, pretty = TRUE, na = "null")
  cat("\nOutput:", f_all, "\n")
} else cat("\n--check finished: inputs and formulas validated. Nothing was written.\n")
cat(sprintf("Rows: %d. Time: %.0f s\n", nrow(all_rows), as.numeric(difftime(Sys.time(), t0, units = "secs"))))
