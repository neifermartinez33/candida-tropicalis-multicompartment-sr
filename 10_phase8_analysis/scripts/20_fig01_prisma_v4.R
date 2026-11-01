#!/usr/bin/env Rscript
# 20_fig01_prisma_v4.R (2026-10-24)
# v4: reads prisma_counts_v3. All the assessed reports come from the databases (the "R" flow of
# full-text screening are database records included at title and abstract; audit of 2026-10-24,
# finding C1), so the diagram is the "databases and registers" one of PRISMA 2020, without a branch for other
# methods. The not retrieved are broken down; the included box separates the reports that only contribute to the
# distribution by compartment. With --provisional it reads the PROVISIONAL table and labels it in the band.
# (2026-10-27) Round 3 added reports found by checking the reference lists of four previous reviews: when the
# table has an "other_methods" box, the diagram adds the PRISMA 2020 column "Identification of studies via other
# methods" (citation searching), whose included reports join the included box.
# Figure 1. PRISMA 2020 flow diagram in the style of Figure 1 of the reference
# article (Hsu et al., 2025): amber top band, light-blue phase bars, white boxes
# with black border, black text and black arrows. Text in English and a
# Palatino-type font. All figures come from the most recent prisma_counts table;
# whatever has no source is labelled "pending".
# Usage, from the project root:
#   FONTCONFIG_FILE=/etc/fonts/fonts.conf conda run --no-capture-output -n ctrop_ma Rscript 10_phase8_analysis/scripts/20_fig01_prisma_v4.R [--provisional]

if (!dir.exists("10_phase8_analysis")) stop("Run from the project root")

suppressPackageStartupMessages({
  library(grid)
  library(ragg)
  library(systemfonts)
  library(jsonlite)
})

candidates <- c("Palatino Linotype", "TeX Gyre Pagella", "P052", "URW Palladio L")
font <- candidates[candidates %in% unique(system_fonts()$family)][1]
if (is.na(font)) stop("R sees no Palatino-type font")

PROV <- "--provisional" %in% commandArgs(trailingOnly = TRUE)
files <- sort(Sys.glob("10_phase8_analysis/results/prisma_counts_v3_*.csv"))
files <- files[grepl("_PROVISIONAL\\.csv$", files) == PROV]
if (length(files) == 0) stop("There is no prisma_counts_v3 table", if (PROV) " PROVISIONAL" else " FINAL",
                             ": run 01_prisma_counts_v3.py first")
src <- files[length(files)]
tab <- read.csv(src, stringsAsFactors = FALSE)
# (2026-10-30) --es: labels in Spanish and non-breaking space as thousands separator, for the Spanish manuscript
ES <- "--es" %in% commandArgs(trailingOnly = TRUE)
L <- function(en, es) if (ES) es else en
ES_LAB <- c(
  "Identical copies consolidated" = "Copias id\u00e9nticas consolidadas", "Duplicate records removed" = "Registros duplicados eliminados",
  "Full text not obtained" = "Texto completo no obtenido", "Full text was another work or truncated" = "Texto completo de otra obra o truncado",
  "Doubtful reports without the correct full text" = "Informes dudosos sin el texto completo correcto",
  "Extraction-stage reports without the correct full text" = "Informes de la extracci\u00f3n sin el texto completo correcto",
  "Reports whose full text was another work, found at row verification" = "Informes cuyo texto completo era otra obra, hallados al verificar las filas",
  "Excluded reports whose full text was another work, found at the re-reading" = "Informes excluidos cuyo texto completo era otra obra, hallados en la relectura",
  "Identification method not reported" = "M\u00e9todo de identificaci\u00f3n no informado",
  "Country of origin not identifiable" = "Pa\u00eds de origen no identificable",
  "Not the target species, not disaggregable, or no isolate" = "Otra especie, datos no separables o sin aislados",
  "Denominators not recoverable" = "Denominadores no recuperables", "Reference strains only" = "Solo cepas de referencia",
  "Review, editorial or abstract without data" = "Revisi\u00f3n, editorial o resumen sin datos",
  "Activity of new compounds only" = "Solo actividad de compuestos nuevos",
  "Source not assignable to a compartment" = "Fuente no asignable a un compartimento",
  "Overlapping collection reported elsewhere" = "Colecci\u00f3n solapada informada en otro lugar",
  "Industrial or biotechnological use" = "Uso industrial o biotecnol\u00f3gico",
  "Duplicate record of the same publication" = "Registro duplicado de la misma publicaci\u00f3n",
  "Testing method and criterion not reported" = "M\u00e9todo de prueba y criterio no informados",
  "In silico only" = "Solo in silico", "Retracted publication" = "Publicaci\u00f3n retractada")
if (ES) {
  use <- tab$box %in% c("excluded", "removed") | startsWith(tab$item, "excluded_") |
    tab$item %in% c("not_obtained", "wrong_or_truncated", "doubtful_not_retrieved", "extraction_not_retrieved",
                    "verification_not_retrieved", "rescreen_not_retrieved")
  if (!all(tab$label[use] %in% names(ES_LAB))) stop("Label without translation: ", paste(setdiff(tab$label[use], names(ES_LAB)), collapse = "; "))
  tab$label[use] <- ES_LAB[tab$label[use]]
}

fmt <- function(x) ifelse(abs(x) >= 1e4, formatC(x, big.mark = if (ES) intToUtf8(160) else ",", format = "d"), formatC(x, format = "d"))  # MDPI: thousands separator only from five digits (2026-10-27)
num <- function(item) {
  v <- tab$n[tab$item == item & tab$box != "other_methods"]   # the other-methods column repeats some item names
  if (length(v) != 1 || is.na(v)) "pending" else fmt(v)
}
nline <- function(item) sprintf("%s (n = %s)", tab$label[tab$item == item], num(item))

# ---- text of each box
s <- tab[startsWith(tab$item, "source:"), ]
s <- s[order(-s$n), ]
s_top <- head(s, 8)
s_rest <- s[-(1:8), ]
id_l <- c(sprintf(L("Records identified from %d sources", "Registros identificados de %d fuentes"), nrow(s)), sprintf("(n = %s):", num("total")),
          sprintf("%s (n = %s)", s_top$label, fmt(s_top$n)),
          sprintf(L("Other %d sources (n = %s)", "Otras %d fuentes (n = %s)"), nrow(s_rest), fmt(sum(s_rest$n))))
id_r <- c(L("Records removed before screening:", "Registros eliminados antes del cribado:"), nline("identical_copies"), nline("duplicates"))
s1_l <- c(L("Records screened", "Registros cribados"), sprintf("(n = %s)", num("screened")))
s1_r <- c(L("Records excluded", "Registros excluidos"), sprintf("(n = %s)", num("ta_excluded")))
s2_l <- c(L("Reports sought for retrieval", "Informes buscados"), sprintf("(n = %s)", num("sought")))
s2_r <- c(sprintf(L("Reports not retrieved (n = %s):", "Informes no recuperados (n = %s):"), num("not_retrieved")),
          nline("not_obtained"), nline("wrong_or_truncated"), nline("doubtful_not_retrieved"),
          nline("extraction_not_retrieved"),
          if (any(tab$item == "verification_not_retrieved" & tab$n > 0)) nline("verification_not_retrieved"),
          if (any(tab$item == "rescreen_not_retrieved" & tab$n > 0)) nline("rescreen_not_retrieved"))
s3_l <- c(L("Reports assessed for eligibility", "Informes evaluados para elegibilidad"), sprintf("(n = %s)", num("assessed")))
e <- tab[tab$box == "excluded", ]
e <- e[order(-e$n), ]
s3_r <- c(sprintf(L("Reports excluded (n = %s):", "Informes excluidos (n = %s):"), fmt(sum(e$n))), sprintf("%s (n = %s)", e$label, fmt(e$n)))
in_l <- c(L("Studies included in review", "Estudios incluidos en la revisi\u00f3n"), sprintf("(n = %s)", num("studies")),
          L("Reports of included studies", "Informes de los estudios incluidos"), sprintf("(n = %s)", num("reports")),
          L("Reports with compartment data only", "Informes solo con datos de compartimento"), sprintf("(n = %s)", num("reports_sq1_only")),
          L("Collections in a pooled estimate", "Colecciones en una estimaci\u00f3n agrupada"), sprintf("(n = %s)", num("meta_analysis")))
rows <- list(list(l = id_l, r = id_r), list(l = s1_l, r = s1_r), list(l = s2_l, r = s2_r),
             list(l = s3_l, r = s3_r), list(l = in_l, r = NULL))
# (2026-10-27) identification via other methods (reference lists of previous reviews), PRISMA 2020 template
OTHER <- any(tab$box == "other_methods")
if (OTHER) {
  oex <- tab[tab$box == "other_methods" & startsWith(tab$item, "excluded_"), ]
  oex <- oex[order(-oex$n), ]
  rows[[1]]$o <- c(L("Records identified from:", "Registros identificados de:"), sprintf(L("Citation searching (n = %s)", "B\u00fasqueda de citas (n = %s)"), fmt(tab$n[tab$box == "other_methods" & tab$item == "identified"])))
  rows[[3]]$o <- c(sprintf(L("Reports sought for retrieval (n = %s)", "Informes buscados (n = %s)"), fmt(tab$n[tab$box == "other_methods" & tab$item == "sought"])),
                   sprintf(L("Reports not retrieved (n = %s)", "Informes no recuperados (n = %s)"), fmt(tab$n[tab$box == "other_methods" & tab$item == "not_retrieved"])))
  rows[[4]]$o <- c(sprintf(L("Reports assessed for eligibility (n = %s)", "Informes evaluados para elegibilidad (n = %s)"), fmt(tab$n[tab$box == "other_methods" & tab$item == "assessed"])),
                   sprintf(L("Reports excluded (n = %s):", "Informes excluidos (n = %s):"), fmt(sum(oex$n))), sprintf("%s (n = %s)", oex$label, fmt(oex$n)))
}

# ---- geometry, in inches
W <- if (OTHER) 9.4 else 7; pad <- 0.09; gap <- 0.25; banner_h <- 0.42; lineh <- 1.15
xbar <- c(0.08, 0.46); xl <- c(0.62, 3.10); xr <- c(3.45, 6.92); xo <- c(7.12, 9.32)

# largest font size (9 pt down to 7 pt) at which every line fits its box, measured on the PDF device
measure <- function(lines, fs) {
  max(vapply(lines, function(t) convertWidth(grobWidth(textGrob(t, gp = gpar(fontfamily = font,
    fontface = "plain", fontsize = fs))), "inches", valueOnly = TRUE), numeric(1)))
}
tmp <- tempfile(fileext = ".pdf")
cairo_pdf(tmp, width = W, height = 10, family = font)
fs <- 10
repeat {
  ok_l <- all(vapply(rows, function(rw) measure(rw$l, fs) <= diff(xl) - 2 * pad, logical(1)))
  ok_r <- all(vapply(rows, function(rw) is.null(rw$r) || measure(rw$r, fs) <= diff(xr) - 2 * pad, logical(1)))
  ok_o <- all(vapply(rows, function(rw) is.null(rw$o) || measure(rw$o, fs) <= diff(xo) - 2 * pad, logical(1)))
  if ((ok_l && ok_r && ok_o) || fs <= 8) break
  fs <- fs - 0.25
}
# a line that still does not fit at the smallest size is wrapped at a word boundary, keeping "(n = x)" whole
wrap <- function(lines, maxw) {
  unlist(lapply(lines, function(t) {
    if (measure(t, fs) <= maxw) return(t)
    w <- regmatches(t, gregexpr("\\(n = [^)]*\\):?|\\S+", t))[[1]]
    out <- character(0); cur <- ""
    for (x in w) {
      nxt <- if (cur == "") x else paste(cur, x)
      if (cur != "" && measure(nxt, fs) > maxw) { out <- c(out, cur); cur <- x } else cur <- nxt
    }
    c(out, cur)
  }))
}
rows <- lapply(rows, function(rw) list(l = wrap(rw$l, diff(xl) - 2 * pad),
                                       r = if (is.null(rw$r)) NULL else wrap(rw$r, diff(xr) - 2 * pad),
                                       o = if (is.null(rw$o)) NULL else wrap(rw$o, diff(xo) - 2 * pad)))
invisible(dev.off())
unlink(tmp)

lh <- fs * lineh * 1.2 / 72  # R: line height = 1.2 x size x lineheight
bh <- function(lines) if (is.null(lines)) 0 else length(lines) * lh + 2 * pad
row_h <- vapply(rows, function(rw) max(bh(rw$l), bh(rw$r), bh(rw$o)), numeric(1))
H <- 0.08 + banner_h + gap + sum(row_h) + gap * (length(rows) - 1) + 0.08
ytop <- H - 0.08 - banner_h - gap - c(0, cumsum(row_h + gap))[seq_along(rows)]
yc <- ytop - row_h / 2

# the n of the sample sizes is in italics, being a variable; the rest in roman
as_label <- function(t) {
  k <- regexpr("n = ", t, fixed = TRUE)
  if (k < 0) return(t)
  pre <- substr(t, 1, k - 1)
  post <- paste0(" = ", substr(t, k + 4, nchar(t)))
  if (nchar(pre) == 0) bquote(italic(n) * .(post)) else bquote(.(pre) * italic(n) * .(post))
}

draw <- function() {
  grid.newpage()
  pushViewport(viewport(xscale = c(0, W), yscale = c(0, H)))
  txt <- function(lines, x, y, size, just = c("left", "top"), rot = 0, face = "plain") {
    g <- gpar(fontfamily = font, fontface = face, fontsize = size, lineheight = lineh, col = "black")
    for (i in seq_along(lines))
      grid.text(as_label(lines[i]), x = x, y = y - (i - 1) * lh, just = just, rot = rot,
                default.units = "native", gp = g)
  }
  box <- function(lines, xx, y) {
    h <- bh(lines)
    grid.rect(x = xx[1], y = y - h / 2, width = diff(xx), height = h, just = c("left", "bottom"),
              default.units = "native", gp = gpar(fill = "white", col = "black", lwd = 1.4))
    txt(lines, xx[1] + pad, y + h / 2 - pad, fs)
  }
  arr <- function(x0, y0, x1, y1)
    grid.segments(x0, y0, x1, y1, default.units = "native",
                  arrow = arrow(angle = 20, length = unit(0.09, "inches"), type = "closed"),
                  gp = gpar(col = "black", fill = "black", lwd = 1.2))
  wb <- if (OTHER) xr[2] - 0.08 else W - 0.16
  grid.roundrect(x = 0.08, y = H - 0.08 - banner_h, width = wb, height = banner_h,
                 just = c("left", "bottom"), default.units = "native", r = unit(0.08, "inches"),
                 gp = gpar(fill = "#FFC000", col = "#BF8F00", lwd = 1.4))
  txt(paste0(L("Identification of studies via databases and registers", "Identificaci\u00f3n de estudios mediante bases de datos y registros"), if (PROV) " [PROVISIONAL]" else ""),
      0.08 + wb / 2, H - 0.08 - banner_h / 2, fs + 2, just = "centre", face = "bold")
  if (OTHER) {
    grid.roundrect(x = xo[1], y = H - 0.08 - banner_h, width = diff(xo), height = banner_h,
                   just = c("left", "bottom"), default.units = "native", r = unit(0.08, "inches"),
                   gp = gpar(fill = "#D9D9D9", col = "#7F7F7F", lwd = 1.4))
    txt(L(c("Identification of studies", "via other methods"), c("Identificaci\u00f3n de estudios", "por otros m\u00e9todos")), mean(xo), H - 0.08 - banner_h / 2 + lh / 2, fs + 1,
        just = "centre", face = "bold")
  }
  phases <- list(Identification = 1, Screening = 2:4, Included = 5)
  for (nm in names(phases)) {
    i <- phases[[nm]]
    y1 <- ytop[min(i)]
    y0 <- ytop[max(i)] - row_h[max(i)]
    grid.roundrect(x = xbar[1], y = y0, width = diff(xbar), height = y1 - y0, just = c("left", "bottom"),
                   default.units = "native", r = unit(0.08, "inches"),
                   gp = gpar(fill = "#9DC3E6", col = "black", lwd = 1.4))
    txt(L(nm, c(Identification = "Identificaci\u00f3n", Screening = "Cribado", Included = "Inclusi\u00f3n")[[nm]]), mean(xbar), (y0 + y1) / 2, fs + 1, just = "centre", rot = 90, face = "bold")
  }
  for (i in seq_along(rows)) {
    box(rows[[i]]$l, xl, yc[i])
    if (!is.null(rows[[i]]$r)) {
      box(rows[[i]]$r, xr, yc[i])
      arr(xl[2], yc[i], xr[1], yc[i])
    }
    if (i < length(rows))
      arr(mean(xl), yc[i] - bh(rows[[i]]$l) / 2, mean(xl), yc[i + 1] + bh(rows[[i + 1]]$l) / 2)
    if (!is.null(rows[[i]]$o)) box(rows[[i]]$o, xo, yc[i])
  }
  if (OTHER) {
    oi <- which(!vapply(rows, function(rw) is.null(rw$o), logical(1)))
    for (k in seq_len(length(oi) - 1))
      arr(mean(xo), yc[oi[k]] - bh(rows[[oi[k]]]$o) / 2, mean(xo), yc[oi[k + 1]] + bh(rows[[oi[k + 1]]]$o) / 2)
    last <- oi[length(oi)]; n <- length(rows)
    grid.segments(mean(xo), yc[last] - bh(rows[[last]]$o) / 2, mean(xo), yc[n], default.units = "native",
                  gp = gpar(col = "black", lwd = 1.2))
    arr(mean(xo), yc[n], xl[2], yc[n])
  }
  popViewport()
}

source("10_phase8_analysis/scripts/fig_helpers.R")
outs <- save_figure(draw, paste0("fig01_prisma_v4", if (PROV) "_PROVISIONAL" else "", if (ES) "_es" else ""), W, H, font)

log_dir <- "10_phase8_analysis/results/logs"
dir.create(log_dir, recursive = TRUE, showWarnings = FALSE)
stamp <- format(Sys.time(), "%Y-%m-%dT%H%M%S")
write_json(list(script = "20_fig01_prisma_v4.R", mode = if (PROV) "PROVISIONAL" else "FINAL", run_time = format(Sys.time(), "%Y-%m-%d %H:%M:%S %z"),
                r_version = R.version.string, input = setNames(list(unname(tools::md5sum(src))), basename(src)),
                outputs = setNames(as.list(unname(tools::md5sum(outs))), basename(outs)),
                font = font, fontsize = fs, width_in = W, height_in = H, dpi = 1200,
                pending = tab$item[tab$status != "final"]),
           file.path(log_dir, paste0("20_fig01_prisma_v4", if (ES) "_es" else "", "_", stamp, ".json")), auto_unbox = TRUE, pretty = TRUE)

cat("Table used:", src, "\n")
cat(sprintf("Font: %s %.2f pt | size: %.2f x %.2f in | 1200 dpi\n", font, fs, W, H))
cat("Pending or provisional boxes:", paste(tab$label[tab$status != "final"], collapse = "; "), "\n")
cat("Files:\n")
cat(paste0("  ", normalizePath(outs), "\n"), sep = "")
