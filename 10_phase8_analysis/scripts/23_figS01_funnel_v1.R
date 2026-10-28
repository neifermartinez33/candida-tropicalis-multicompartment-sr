#!/usr/bin/env Rscript
# 23_figS01_funnel_v1.R (2026-10-27)
# Figure S1 (reporting bias, exploratory): funnel plots of the pooled strata, as the registered protocol
# states ("Funnel plots are of limited validity for proportions and are used only exploratorily").
# One panel per pooled stratum with at least 10 independent collections, any compartment. Each collection
# is a point: its proportion on x and its isolates tested on y (log scale), the sample-size funnel
# recommended for proportions (Hunter et al. 2014), because the standard error of a proportion depends on
# the proportion itself. The dashed line is the population mean of the main analysis (AR15) and the curves
# are the 95 % binomial limits around it, p +/- 1.96 sqrt(p (1 - p) / n). No asymmetry test is run: the
# protocol states that funnel plot asymmetry is not a valid test for proportions. The figure is
# descriptive and changes no estimate. Text in English, Palatino-type font, 1200 dpi, PDF, SVG, PNG and TIFF.
# Usage, from the project root:
#   FONTCONFIG_FILE=/etc/fonts/fonts.conf conda run --no-capture-output -n ctrop_ma Rscript 10_phase8_analysis/scripts/23_figS01_funnel_v1.R [--provisional]

if (!dir.exists("10_phase8_analysis")) stop("Run from the project root")
suppressPackageStartupMessages({
  library(ggplot2)
  library(jsonlite)
})
source("10_phase8_analysis/scripts/fig_helpers.R")
font <- fig_font()

RES <- "10_phase8_analysis/results"
OUT <- "12_documents/supplementary/figures"
RULES <- "10_phase8_analysis/analysis_rules_v4_2026-10-24.md"
PROV <- "--provisional" %in% commandArgs(trailingOnly = TRUE)
TAG <- if (PROV) "_PROVISIONAL" else ""
K_MIN <- 10
ORD <- c("ECV_CLSI", "ECV_EUCAST", "CLSI_SS", "CLSI_SS+EUCAST", "CLSI_pre2012", "EUCAST")
LAB <- c("CLSI ECV", "EUCAST ECV", "CLSI SS", "CLSI SS or EUCAST", "CLSI pre-2012", "EUCAST")
CMP <- c(C1 = "human host", C2 = "animal host", C3 = "agroecosystem", C4 = "healthcare environment",
         C5 = "natural environment", C6 = "anthropogenic matrix")

newest <- function(pat) {
  f <- sort(Sys.glob(file.path(RES, pat)))
  f <- f[grepl("_PROVISIONAL\\.csv$", f) == PROV]
  if (length(f) == 0) stop("There is no ", pat, if (PROV) " PROVISIONAL" else " FINAL")
  f[length(f)]
}
f_res <- newest("ma_results_v3_*.csv")
lg <- file.path(RES, "logs", sub("^ma_results_v3_(.*)\\.csv$", "06_ma_marginal_v3_\\1.json", basename(f_res)))
if (!file.exists(lg)) stop("The log is missing for ", f_res)
f_in <- grep("ma_input_v2_", names(fromJSON(lg)$inputs), value = TRUE)
if (length(f_in) != 1 || !file.exists(f_in)) stop("The log of ma_results_v3 does not identify its ma_input_v2")
if (!file.exists(RULES)) stop("Missing ", RULES)
res <- read.csv(f_res, stringsAsFactors = FALSE, na.strings = c("", "NA"))
inp <- read.csv(f_in, stringsAsFactors = FALSE, na.strings = c("", "NA"))
res <- res[res$status == "pooled" & res$k_collections >= K_MIN, ]
if (nrow(res) == 0) stop("No pooled stratum has ", K_MIN, " or more collections")
inp <- inp[as.logical(inp$main), ]

res$rank <- match(res$regime_stratum, ORD)
res <- res[order(res$compartment, res$outcome != "NWT", res$agent, res$rank), ]
res$key <- paste(res$compartment, res$agent, res$outcome, res$regime_stratum)
agent_lab <- paste0(toupper(substring(res$agent, 1, 1)), substring(res$agent, 2))
res$panel <- sprintf("%s, %s\n%s %s, %s, k = %d", agent_lab, LAB[res$rank], res$compartment,
                     CMP[res$compartment], ifelse(res$outcome == "NWT", "NWT", "R"), res$k_collections)
res$panel <- factor(res$panel, levels = res$panel)
inp$key <- paste(inp$compartment, inp$agent, inp$outcome, inp$regime_stratum)
pts <- merge(inp[inp$key %in% res$key, c("key", "collection_id", "events", "n_tested")],
             res[, c("key", "panel", "p_marginal")], by = "key")
pts$p <- pts$events / pts$n_tested
chk <- table(pts$key)[res$key]
if (any(chk != res$k_collections)) stop("The collections drawn do not match k_collections of ma_results_v3")

# 95 % binomial limits around the pooled mean, on a grid of n from the smallest to the largest collection
lim <- do.call(rbind, lapply(seq_len(nrow(res)), function(i) {
  n <- exp(seq(log(1), log(max(pts$n_tested) * 1.1), length.out = 200))
  p0 <- res$p_marginal[i]; se <- sqrt(p0 * (1 - p0) / n)
  rbind(data.frame(panel = res$panel[i], n = n, x = p0 - 1.96 * se, side = "lo"),
        data.frame(panel = res$panel[i], n = n, x = p0 + 1.96 * se, side = "hi"))
}))
lim <- lim[lim$x >= 0 & lim$x <= 1, ]  # each curve stops where it leaves 0 to 100 %

p <- ggplot() +
  geom_path(data = lim, aes(x = x, y = n, group = side), linewidth = 0.3, colour = "grey45") +
  geom_vline(data = res, aes(xintercept = p_marginal), linewidth = 0.35, linetype = "dashed") +
  geom_point(data = pts, aes(x = p, y = n_tested), shape = 16, size = 1.1, alpha = 0.55) +
  facet_wrap(~panel, ncol = 4) +
  scale_x_continuous(breaks = seq(0, 1, 0.25), labels = function(v) sprintf("%.0f", 100 * v),
                     expand = expansion(add = 0.02)) +
  scale_y_log10(breaks = c(1, 10, 100, 1000, 10000), labels = function(x) ifelse(abs(x) >= 1e4, formatC(x, big.mark = ",", format = "d"), formatC(x, format = "d"))) +
  coord_cartesian(xlim = c(0, 1), ylim = c(1, max(pts$n_tested) * 1.1)) +
  labs(x = "Proportion of isolates, %", y = "Isolates tested in the collection (log scale)",
       title = if (PROV) "PROVISIONAL: not for the manuscript" else NULL) +
  theme_classic(base_size = 9, base_family = font) +
  theme(text = element_text(family = font, colour = "black"),
        axis.text = element_text(colour = "black", size = 7.5),
        axis.title = element_text(face = "bold", size = 9.5),
        strip.background = element_blank(),
        strip.text = element_text(size = 7.5, hjust = 0, lineheight = 1.05),
        panel.spacing = unit(0.45, "lines"),
        plot.margin = margin(4, 8, 4, 4))

W <- 7.5
H <- 1.75 * ceiling(nrow(res) / 4) + 0.6
outs <- save_figure(function() print(p), paste0("fig_s01_funnel_v1", TAG), W, H, font, out_dir = OUT)

stamp <- sub(paste0("^fig_s01_funnel_v1", TAG, "_(.*)\\.pdf$"), "\\1", basename(outs[1]))
vals <- res[, c("compartment", "agent", "outcome", "regime_stratum", "k_collections", "isolates", "p_marginal")]
vals_csv <- file.path(RES, paste0("fig_s01_funnel_v1", TAG, "_", stamp, ".csv"))
write.csv(vals, vals_csv, row.names = FALSE)
ins <- c(RULES, f_res, f_in, "10_phase8_analysis/scripts/fig_helpers.R")
log_path <- file.path(RES, "logs", paste0("23_figS01_funnel_v1", TAG, "_", stamp, ".json"))
dir.create(dirname(log_path), recursive = TRUE, showWarnings = FALSE)
write_json(list(script = "23_figS01_funnel_v1.R", mode = if (PROV) "PROVISIONAL" else "FINAL",
                run_time = format(Sys.time(), "%Y-%m-%d %H:%M:%S %z"),
                r_version = R.version.string, ggplot2 = as.character(packageVersion("ggplot2")),
                inputs = setNames(as.list(unname(tools::md5sum(ins))), ins),
                outputs = setNames(as.list(unname(tools::md5sum(c(outs, vals_csv)))),
                                   basename(c(outs, vals_csv))),
                font = font, width_in = W, height_in = H, dpi = 1200, k_min = K_MIN,
                strata = nrow(res), collections_drawn = nrow(pts)),
           log_path, auto_unbox = TRUE, pretty = TRUE)
cat(sprintf("Figure S1: %d pooled strata with k >= %d, %d collections drawn\n", nrow(res), K_MIN, nrow(pts)))
cat(sprintf("Font: %s | size: %.2f x %.2f in | 1200 dpi\n", font, W, H))
cat("Outputs:", c(outs, vals_csv, log_path), sep = "\n  ")
cat("\n")
