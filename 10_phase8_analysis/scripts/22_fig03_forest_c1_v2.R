#!/usr/bin/env Rscript
# 22_fig03_forest_c1_v2.R (2026-10-24)
# v2: reads ma_results_v3 and the ma_input_v2 of the same run (through the log of 06_ma_marginal_v3.R), thousands
# separator in k (events/isolates), and with --provisional reads the PROVISIONAL run and labels it in the figure.
# Figure 3 (Results, SQ2): forest plot of C1, the human host, by antifungal agent and
# interpretive regime, in the style of Figure 2 of Hsu et al. (2025). Each independent
# collection is a point with area proportional to the isolates tested; where the stratum is
# pooled, the population mean is drawn with its 95 % CI and, in a thin line, the prediction
# interval (rules v2, AR15 and AR17). The strata that are not pooled show their collections
# and carry no estimate, as in Tables 3 and 4. On the right, k with events and isolates, and
# the mean with its CI. Text in English, Palatino-type font, 1200 dpi, PDF, SVG, PNG and TIFF.
# Usage, from the project root:
#   FONTCONFIG_FILE=/etc/fonts/fonts.conf conda run --no-capture-output -n ctrop_ma Rscript 10_phase8_analysis/scripts/22_fig03_forest_c1_v2.R [--provisional]

if (!dir.exists("10_phase8_analysis")) stop("Run from the project root")
suppressPackageStartupMessages({
  library(ggplot2)
  library(jsonlite)
})
source("10_phase8_analysis/scripts/fig_helpers.R")
font <- fig_font()

RES <- "10_phase8_analysis/results"
RULES <- "10_phase8_analysis/analysis_rules_v4_2026-10-24.md"
PROV <- "--provisional" %in% commandArgs(trailingOnly = TRUE)
TAG <- if (PROV) "_PROVISIONAL" else ""
SEED <- 20261021
ORD <- c("ECV_CLSI", "ECV_EUCAST", "CLSI_SS", "CLSI_SS+EUCAST", "CLSI_pre2012", "EUCAST")
LAB <- c("CLSI ECV", "EUCAST ECV", "CLSI SS", "CLSI SS or EUCAST", "CLSI pre-2012", "EUCAST")
EN <- intToUtf8(8211)   # en dash of the interval; the source stays in ASCII
EM <- intToUtf8(8212)   # em dash: stratum without estimate

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
res <- res[res$compartment == "C1", ]
inp <- inp[inp$compartment == "C1" & as.logical(inp$main), ]
if (nrow(res) == 0) stop("There are no C1 strata in the results")

res$rank <- match(res$regime_stratum, ORD)
res$crit <- LAB[res$rank]
res$agent_lab <- paste0(toupper(substring(res$agent, 1, 1)), substring(res$agent, 2))
res <- res[order(res$outcome != "NWT", res$agent, res$rank), ]
res$key <- paste(res$agent, res$outcome, res$regime_stratum)
inp$key <- paste(inp$agent, inp$outcome, inp$regime_stratum)
inp <- inp[inp$key %in% res$key, ]
inp$p <- inp$events / inp$n_tested

# drawing rows: header, group label and one row per stratum, from top to bottom
blocks <- list(c("NWT", "Non-wild-type by ECV"), c("R", "Resistant by clinical breakpoint"))
lines <- list(list(kind = "head"))
for (b in blocks) {
  if (!any(res$outcome == b[1])) next
  lines[[length(lines) + 1]] <- list(kind = "group", text = b[2])
  for (i in which(res$outcome == b[1])) lines[[length(lines) + 1]] <- list(kind = "row", i = i)
}
n_lines <- length(lines)
y_of <- function(k) n_lines - k + 1          # the first line stays on top
kind <- vapply(lines, function(l) l$kind, character(1))

rows <- data.frame(y = y_of(which(kind == "row")),
                   i = vapply(lines[kind == "row"], function(l) as.numeric(l$i), numeric(1)))
d <- cbind(rows, res[rows$i, ])
d$label <- paste0(d$agent_lab, ", ", d$crit)
big <- function(v) { x <- as.integer(v); ifelse(abs(x) >= 1e4, formatC(x, big.mark = ",", format = "d"), formatC(x, format = "d")) }  # MDPI: thousands separator only from five digits (2026-10-27)
d$k_txt <- sprintf("%s (%s/%s)", big(d$k_collections), big(d$events), big(d$isolates))
d$est_txt <- ifelse(d$status == "pooled",
                    sprintf("%.1f (%.1f%s%.1f)", 100 * d$p_marginal, 100 * d$marg_lower, EN,
                            100 * d$marg_upper), EM)
pool <- d[d$status == "pooled", ]
pts <- merge(inp, d[, c("key", "y")], by = "key")

grp <- data.frame(y = y_of(which(kind == "group")),
                  text = vapply(lines[kind == "group"], function(l) l$text, character(1)))
y_head <- y_of(which(kind == "head"))

X_LAB <- -0.75   # position of the text columns, in x-axis units
X_K <- 1.05
X_EST <- 1.52
XLIM <- c(X_LAB, 1.97)
head_df <- data.frame(x = c(X_LAB, X_EST), y = y_head,
                      label = c("Agent and interpretive criterion", "Mean, % (95% CI)"))
# the k of the header is a variable: in italics, composed with plotmath
k_head <- data.frame(x = X_K, y = y_head, label = 'bolditalic(k)~bold("(events/isolates)")')
acl <- unique(inp[, c("agent", "agent_class")])
d$agent_class <- acl$agent_class[match(d$agent, acl$agent)]
cls <- sort(unique(d$agent_class))
pal <- setNames(scales::hue_pal()(length(cls)), cls)

p <- ggplot() +
  geom_hline(yintercept = y_head - 0.5, linewidth = 0.4) +
  geom_point(data = pts, aes(x = p, y = y, size = n_tested, colour = agent_class),
             alpha = 0.35, shape = 16,
             position = position_jitter(height = 0.17, width = 0, seed = SEED)) +
  geom_segment(data = pool, aes(x = pi_lower, xend = pi_upper, y = y, yend = y),
               linewidth = 0.35, colour = "grey30") +
  geom_segment(data = pool, aes(x = marg_lower, xend = marg_upper, y = y, yend = y),
               linewidth = 0.9, colour = "black") +
  geom_point(data = pool, aes(x = p_marginal, y = y), shape = 23, size = 2.1, stroke = 0.4,
             fill = "black", colour = "black") +
  geom_text(data = d, aes(x = X_LAB, y = y, label = label), hjust = 0, size = 9,
            size.unit = "pt", family = font) +
  geom_text(data = d, aes(x = X_K, y = y, label = k_txt), hjust = 0, size = 9,
            size.unit = "pt", family = font) +
  geom_text(data = d, aes(x = X_EST, y = y, label = est_txt), hjust = 0, size = 9,
            size.unit = "pt", family = font) +
  geom_text(data = grp, aes(x = X_LAB, y = y, label = text), hjust = 0, size = 9.5,
            size.unit = "pt", family = font, fontface = "italic") +
  geom_text(data = head_df, aes(x = x, y = y, label = label), hjust = 0, size = 9,
            size.unit = "pt", family = font, fontface = "bold") +
  geom_text(data = k_head, aes(x = x, y = y, label = label), parse = TRUE, hjust = 0, size = 9,
            size.unit = "pt", family = font, fontface = "bold") +
  scale_colour_manual(values = pal, name = "Antifungal class",
                      guide = guide_legend(override.aes = list(alpha = 0.8, size = 2.2))) +
  scale_size_area(max_size = 3.1, name = "Isolates tested", breaks = c(10, 100, 1000)) +
  scale_x_continuous(breaks = seq(0, 1, 0.25), labels = function(v) sprintf("%.0f", 100 * v),
                     expand = c(0, 0)) +
  scale_y_continuous(expand = expansion(add = c(0.6, 0.9))) +
  coord_cartesian(xlim = XLIM, ylim = c(0.5, n_lines + 0.5), clip = "off") +
  labs(x = "Proportion of isolates, %", y = NULL, title = if (PROV) "PROVISIONAL: not for the manuscript" else NULL) +
  theme_classic(base_size = 10, base_family = font) +
  theme(text = element_text(family = font, colour = "black"),
        axis.text.y = element_blank(), axis.ticks.y = element_blank(),
        axis.line.y = element_blank(),
        axis.text.x = element_text(colour = "black", size = 9),
        axis.title.x = element_text(face = "bold", size = 10),
        axis.line.x = element_line(linewidth = 0.4),
        legend.position = "bottom", legend.box = "vertical", legend.box.just = "left",
        legend.title = element_text(face = "bold", size = 9),
        legend.text = element_text(size = 9),
        plot.margin = margin(4, 4, 4, 4))

W <- 7.5
H <- 0.21 * n_lines + 1.72   # +0.27 in: the legend goes from one row to two
outs <- save_figure(function() print(p), paste0("fig03_forest_c1_v2", TAG), W, H, font)

stamp <- sub(paste0("^fig03_forest_c1_v2", TAG, "_(.*)\\.pdf$"), "\\1", basename(outs[1]))
vals <- d[, c("agent", "outcome", "regime_stratum", "status", "k_collections", "events",
              "isolates", "p_marginal", "marg_lower", "marg_upper", "pi_lower", "pi_upper")]
vals_csv <- file.path(RES, paste0("fig03_forest_c1_v2", TAG, "_", stamp, ".csv"))
write.csv(vals, vals_csv, row.names = FALSE)
ins <- c(RULES, f_res, f_in, "10_phase8_analysis/scripts/fig_helpers.R")
log_path <- file.path(RES, "logs", paste0("22_fig03_forest_c1_v2", TAG, "_", stamp, ".json"))
dir.create(dirname(log_path), recursive = TRUE, showWarnings = FALSE)
write_json(list(script = "22_fig03_forest_c1_v2.R", mode = if (PROV) "PROVISIONAL" else "FINAL",
                run_time = format(Sys.time(), "%Y-%m-%d %H:%M:%S %z"),
                r_version = R.version.string, ggplot2 = as.character(packageVersion("ggplot2")),
                inputs = setNames(as.list(unname(tools::md5sum(ins))), ins),
                outputs = setNames(as.list(unname(tools::md5sum(c(outs, vals_csv)))),
                                   basename(c(outs, vals_csv))),
                font = font, width_in = W, height_in = H, dpi = 1200, jitter_seed = SEED,
                strata = nrow(d), pooled = sum(d$status == "pooled"),
                collections_drawn = nrow(pts)),
           log_path, auto_unbox = TRUE, pretty = TRUE)
cat(sprintf("Figure 3: %d C1 strata (%d pooled), %d collections drawn\n",
            nrow(d), sum(d$status == "pooled"), nrow(pts)))
cat(sprintf("Font: %s | size: %.2f x %.2f in | 1200 dpi\n", font, W, H))
cat("Outputs:", c(outs, vals_csv, log_path), sep = "\n  ")
cat("\n")
