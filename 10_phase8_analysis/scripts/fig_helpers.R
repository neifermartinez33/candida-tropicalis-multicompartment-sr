# fig_helpers.R
# Output standard of the manuscript figures, common to all figure scripts:
#   vector PDF (cairo, embedded fonts), SVG (cairo), PNG and TIFF at 1200 dpi (ragg;
#   TIFF with LZW compression). Palatino-type font; figure text in English.
# It is loaded with source("10_phase8_analysis/scripts/fig_helpers.R") from each figure script,
# which is run with FONTCONFIG_FILE=/etc/fonts/fonts.conf to see the system fonts.

fig_font <- function() {
  candidates <- c("Palatino Linotype", "TeX Gyre Pagella", "P052", "URW Palladio L")
  font <- candidates[candidates %in% unique(systemfonts::system_fonts()$family)][1]
  if (is.na(font)) stop("R sees no Palatino-type font")
  font
}

# draw: function without arguments that draws the figure; name: prefix of the file (figNN_name_vK)
save_figure <- function(draw, name, width, height, font, out_dir = "12_documents/figures", dpi = 1200) {
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
  base <- file.path(out_dir, paste0(name, "_", format(Sys.time(), "%Y-%m-%dT%H%M%S")))
  f <- paste0(base, c(".pdf", ".svg", ".png", ".tif"))
  if (any(file.exists(f))) stop("An output with that name already exists: it is not overwritten")
  grDevices::cairo_pdf(f[1], width = width, height = height, family = font)
  draw()
  invisible(grDevices::dev.off())
  grDevices::svg(f[2], width = width, height = height, family = font)
  draw()
  invisible(grDevices::dev.off())
  ragg::agg_png(f[3], width = width, height = height, units = "in", res = dpi)
  draw()
  invisible(grDevices::dev.off())
  ragg::agg_tiff(f[4], width = width, height = height, units = "in", res = dpi, compression = "lzw")
  draw()
  invisible(grDevices::dev.off())
  f
}
