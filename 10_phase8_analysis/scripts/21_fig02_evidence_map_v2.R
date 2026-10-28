#!/usr/bin/env Rscript
# 21_fig02_evidence_map_v2.R (2026-10-24)
# v2: the unit is the independent collection, not the report (audit of 2026-10-24): it reads the
# collection-compartment allocation written by 03_tab02_characteristics_v2.py and the v3 dataset of that same run,
# so that the figure and Table 2 count the same way. With --provisional it reads the PROVISIONAL run and labels it.
# Figure 2 (Results 3.2, SQ1): evidence map. (A) collections by recovery
# compartment, with their isolates; (B) collections by compartment and WHO region, with the
# zeros visible. It checks that the allocation matches the log of that same run,
# so that the figure and Table 2 count the same way. Style of the reference article (Hsu et al.,
# 2025): default ggplot palette by group (A) and the gradient of its Figure 3, with grey
# for zero (B). Text in English, Palatino-type font, 1200 dpi, PDF, SVG, PNG and TIFF.
# Usage, from the project root:
#   FONTCONFIG_FILE=/etc/fonts/fonts.conf conda run --no-capture-output -n ctrop_ma Rscript 10_phase8_analysis/scripts/21_fig02_evidence_map_v2.R [--provisional]

if (!dir.exists("10_phase8_analysis")) stop("Run from the project root")
suppressPackageStartupMessages({
  library(ggplot2)
  library(grid)
  library(jsonlite)
})
source("10_phase8_analysis/scripts/fig_helpers.R")
font <- fig_font()

res <- "10_phase8_analysis/results"
PROV <- "--provisional" %in% commandArgs(trailingOnly = TRUE)
TAG <- if (PROV) "_PROVISIONAL" else ""
files <- sort(Sys.glob(file.path(res, "collection_compartment_v2_*.csv")))
files <- files[grepl("_PROVISIONAL\\.csv$", files) == PROV]
if (length(files) == 0) stop("There is no allocation: run 03_tab02_characteristics_v2.py first", if (PROV) " --provisional" else "")
src <- files[length(files)]
t2_log <- file.path(res, "logs", sub("^collection_compartment_v2_", "03_tab02_characteristics_v2_",
                                     sub("\\.csv$", ".json", basename(src))))
if (!file.exists(t2_log)) stop("Missing ", t2_log)
studies_csv <- fromJSON(t2_log)$inputs$studies$path
lookup_csv <- "10_phase8_analysis/data/lookups/compartments_v1.csv"
for (f in c(t2_log, studies_csv, lookup_csv)) if (!file.exists(f)) stop("Missing ", f)
asg <- read.csv(src, stringsAsFactors = FALSE, na.strings = "")
st <- read.csv(studies_csv, stringsAsFactors = FALSE, na.strings = "")
lk <- read.csv(lookup_csv, stringsAsFactors = FALSE)

rows <- c(lk$code, "not_allocated")
row_lab <- c(paste(lk$code, lk$short_label), "Not allocated")
reg <- c("AFR", "AMR", "EMR", "EUR", "SEAR", "WPR", "MULTI")
reg_lab <- c("African", "Americas", "Eastern\nMediterranean", "European", "South-East\nAsia",
             "Western\nPacific", "Multi-\nnational")
comp_col <- setNames(c("#F8766D", "#B79F00", "#00BA38", "#00BFC4", "#619CFF", "#F564E3", "grey60"),
                     row_lab)  # ggplot2 default hue palette, as in the reference figures
map_pal <- c("#27CEC6", "#54EC95", "#7AF964", "#B4F53F", "#DED937", "#F7B336", "#F78121",
             "#E45310", "#C82600")  # colour bar of Figure 3 of the reference article
fmt <- function(x) ifelse(abs(x) >= 1e4, formatC(x, big.mark = ",", format = "d"), formatC(x, format = "d"))  # MDPI: thousands separator only from five digits (2026-10-27)

# same counts as Table 2: stop if the assignment and the Table 2 log of that run disagree
n_rows <- vapply(rows, function(r) as.numeric(sum(asg$column == r)), numeric(1))
chk <- fromJSON(t2_log)$collections_by_column
# one row per collection: its representative report (the one Table 2 uses)
rep_ids <- unique(asg$report_id)
st <- st[st$study_id %in% rep_ids, ]
if (!all(n_rows == unlist(chk[rows])) || nrow(st) != chk$ALL) {
  stop("The allocation does not match the log of Table 2")
}
if (!all(c(asg$who_region, st$who_region) %in% reg)) stop("There are regions outside the list")

# ---- panel A: reports and isolates by compartment
a <- data.frame(row = rows, reports = n_rows,
                isolates = vapply(rows, function(r) sum(asg$isolates[asg$column == r], na.rm = TRUE),
                                  numeric(1)))
a$label <- sprintf("%s (%s)", fmt(a$reports), fmt(a$isolates))   # collections (isolates)
a$row <- factor(a$row, levels = rev(rows), labels = rev(row_lab))

# ---- panel B: reports and isolates by compartment and WHO region; last row, all reports
by_region <- function(region, isolates, r) {
  do.call(rbind, lapply(reg, function(g) {
    data.frame(row = r, region = g, reports = sum(region == g),
               isolates = sum(isolates[region == g], na.rm = TRUE))
  }))
}
b <- do.call(rbind, c(lapply(rows, function(r) {
  d <- asg[asg$column == r, ]
  by_region(d$who_region, d$isolates, r)
}), list(by_region(st$who_region, st$n_tropicalis, "ALL"))))   # ALL: all collections
b$fill <- ifelse(b$reports > 0, b$reports, NA)
b$label <- ifelse(b$reports > 0, sprintf("%s\n(%s)", fmt(b$reports), fmt(b$isolates)), "0")
b$text_col <- ifelse(!is.na(b$fill) & b$fill >= 500, "white", "black")
b$row_code <- b$row
b$region_code <- b$region
b$row <- factor(b$row, levels = rev(c(rows, "ALL")), labels = rev(c(row_lab, "All collections")))
b$region <- factor(b$region, levels = reg, labels = reg_lab)

base <- theme(text = element_text(family = font, colour = "black"),
              plot.title = element_text(face = "bold", size = 11),
              plot.subtitle = element_text(size = 9),
              plot.title.position = "plot",
              plot.tag = element_text(face = "bold", size = 14),
              axis.text = element_text(face = "bold", colour = "black", size = 9),
              axis.ticks.y = element_blank(),
              axis.ticks.length.y = unit(0, "pt"))

pA <- ggplot(a, aes(x = reports, y = row)) +
  geom_col(aes(fill = row), width = 0.7, colour = "black", linewidth = 0.3) +
  geom_text(aes(label = label), hjust = 0, nudge_x = max(a$reports) * 0.012, size = 9,
            size.unit = "pt", family = font, fontface = "bold") +
  scale_fill_manual(values = comp_col, guide = "none") +
  scale_x_continuous(labels = fmt, expand = expansion(mult = c(0, 0.38))) +
  labs(x = expression(bold("Collections, ") * bolditalic(n)), y = NULL, tag = "A",
       title = paste0("Independent collections by compartment of recovery", if (PROV) " [PROVISIONAL]" else ""),
       subtitle = "Bar labels: collections (isolates of the representative report)") +
  theme_classic(base_size = 10, base_family = font) + base +
  theme(axis.title.x = element_text(face = "bold", size = 10),
        axis.line = element_line(linewidth = 0.4))

brk <- c(1, 10, 100, 1000)
brk <- brk[brk <= max(b$reports)]  # colour bar breaks inside the data range
pB <- ggplot(b, aes(x = region, y = row)) +
  geom_tile(aes(fill = fill), colour = "white", linewidth = 0.8) +
  geom_text(aes(label = label, colour = text_col), size = 8, size.unit = "pt", family = font,
            fontface = "bold", lineheight = 0.85) +
  geom_hline(yintercept = 1.5, linewidth = 0.5) +
  scale_colour_identity() +
  scale_fill_gradientn(colours = map_pal, transform = "log10", limits = c(1, max(b$reports)),
                       breaks = brk, labels = fmt,
                       na.value = "grey85", name = expression(bold("Collections, ") * bolditalic(n))) +
  scale_x_discrete(position = "top", expand = c(0, 0)) +
  scale_y_discrete(expand = c(0, 0)) +
  guides(fill = guide_colourbar(theme = theme(legend.key.width = unit(2.2, "in"),
                                              legend.key.height = unit(0.12, "in")))) +
  labs(x = NULL, y = NULL, tag = "B", title = "Collections by compartment and WHO region",
       subtitle = "Cells: collections (isolates); grey: none") +
  theme_minimal(base_size = 10, base_family = font) + base +
  theme(panel.grid = element_blank(), axis.ticks = element_blank(),
        axis.text.x.top = element_text(size = 8.5, lineheight = 0.9, vjust = 0),
        legend.position = "bottom", legend.title.position = "left",
        legend.title = element_text(face = "bold", size = 9), legend.text = element_text(size = 9))

hA <- 2.4   # panel heights, in inches
hB <- 4.45
W <- 7
H <- hA + hB
draw <- function() {
  grid.newpage()
  pushViewport(viewport(layout = grid.layout(2, 1, heights = unit(c(hA, hB), "in"))))
  print(pA, vp = viewport(layout.pos.row = 1, layout.pos.col = 1))
  print(pB, vp = viewport(layout.pos.row = 2, layout.pos.col = 1))
  popViewport()
}
outs <- save_figure(draw, paste0("fig02_evidence_map_v2", TAG), W, H, font)

# numbers drawn in the figure, as a table; then the log
stamp <- sub(paste0("^fig02_evidence_map_v2", TAG, "_(.*)\\.pdf$"), "\\1", basename(outs[1]))
vals_csv <- file.path(res, paste0("fig02_evidence_map_v2", TAG, "_", stamp, ".csv"))
vals <- rbind(data.frame(panel = "A", row = rows, region = "all", reports = a$reports,
                         isolates = a$isolates),
              data.frame(panel = "B", row = b$row_code, region = b$region_code, reports = b$reports,
                         isolates = b$isolates))
write.csv(vals, vals_csv, row.names = FALSE)
ins <- c(src, t2_log, studies_csv, lookup_csv, "10_phase8_analysis/scripts/fig_helpers.R")
log_path <- file.path(res, "logs", paste0("21_fig02_evidence_map_v2", TAG, "_", stamp, ".json"))
write_json(list(script = "21_fig02_evidence_map_v2.R", mode = if (PROV) "PROVISIONAL" else "FINAL",
                run_time = format(Sys.time(), "%Y-%m-%d %H:%M:%S %z"),
                r_version = R.version.string, ggplot2 = as.character(packageVersion("ggplot2")),
                inputs = setNames(as.list(unname(tools::md5sum(ins))), ins),
                outputs = setNames(as.list(unname(tools::md5sum(c(outs, vals_csv)))),
                                   basename(c(outs, vals_csv))),
                font = font, width_in = W, height_in = H, dpi = 1200,
                collections_by_row = setNames(as.list(unname(a$reports)), rows)),
           log_path, auto_unbox = TRUE, pretty = TRUE)
cat("Allocation used:", src, "\n")
cat(sprintf("Font: %s | size: %.2f x %.2f in | 1200 dpi\n", font, W, H))
cat("Outputs:", c(outs, vals_csv, log_path), sep = "\n  ")
cat("\n")
