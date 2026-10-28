#!/usr/bin/env python3
"""02_tab01_compartments_v1.py

Table 1 of the manuscript (Methods): recovery compartments C1-C6 and the azole
exposure regime that defines each one. It is a transcription of the registered protocol
(PROSPERO CRD420261486387; full protocol, section 3 and its Table 1): it uses no study
data. The names come from 10_phase8_analysis/data/lookups/compartments_v1.csv, the
same names table used by Table 2 and the figures.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/02_tab01_compartments_v1.py
Outputs (never overwritten):
  12_documents/tables/tab01_compartments_v1_<date-time>.xlsx
  10_phase8_analysis/results/logs/02_tab01_compartments_v1_<date-time>.json
"""
import csv, hashlib, json, os, platform, sys, textwrap
from datetime import datetime

import xlsxwriter

LOOKUP = "10_phase8_analysis/data/lookups/compartments_v1.csv"
OUT_DIR = "12_documents/tables"
LOG_DIR = "10_phase8_analysis/results/logs"
FONT = "Palatino Linotype"
WIDTHS = [7, 30, 50, 50]  # column widths, in characters

# Protocol, section 3, Table 1: matrices and azole exposure regimen of each compartment
SOURCES = {
    "C1": "Invasive and non-invasive clinical samples; cutaneous and mucosal colonisation; "
          "carriage in occupationally exposed healthy populations",
    "C2": "Domestic, production, wild and captive animals",
    "C3": "Agricultural soil; fruit and fruit surfaces; cultivated vegetation; irrigation water",
    "C4": "Surfaces, furniture, equipment and devices in healthcare settings",
    "C5": "Wild soil; sediment; fresh and marine water; uncultivated vegetation; hypersaline matrices",
    "C6": "Urban and hospital wastewater; beaches and coastal waters receiving discharge; "
          "periurban soil with effluent; sludge",
}
REGIMEN = {
    "C1": "Clinical azoles",
    "C2": "Veterinary azoles and indirect environmental exposure",
    "C3": "Agricultural azole fungicides",
    "C4": "Clinical azoles and disinfectants",
    "C5": "No direct regimen. Reference group, admissible only with documented absence of "
          "agronomic management",
    "C6": "Documented anthropogenic input without attributable azole regimen. Descriptive: takes "
          "no part in between-compartment contrasts and cannot form the reference group",
}
# footnote number attached to the compartment name or to the regimen of each row
NAME_NOTE = {"C1": "1", "C3": "2", "C4": "1", "C5": "2", "C6": "4"}
REGIMEN_NOTE = {"C5": "3"}
FOOTNOTES = [
    ("1", "C1 and C4 are distinguished by the purpose for which the sample was cultured: a catheter "
          "tip processed to diagnose infection is C1; the same device swabbed during a surface "
          "survey is C4."),
    ("2", "C3 and C5 are distinguished by documented agronomic management of the sampled matrix "
          "(declared, reported or verifiable fungicide use at the sampling site or in its production "
          "unit), not by distance; distance is recorded only as a secondary, continuous indicator."),
    ("3", "Strict reading, which governs the primary analysis: only matrices with documented absence "
          "of agronomic management. Broad reading, used only in sensitivity analysis SA1: also "
          "natural matrices whose management was not evaluated."),
    ("4", "A matrix with documented anthropogenic input is classified as C6 even in the absence of "
          "agronomic management in its surroundings."),
]
CAPTION = ("Compartments of recovery of ", "Candida tropicalis",
           " isolates and the azole exposure regimen that characterises each compartment, as "
           "defined in the registered protocol.")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def lines(text, width, chars=1.25):
    """Lines a text wraps to in a column of the given width; chars = characters per width unit
    (about 1.25 at 10 pt and 1.4 at 9 pt). Only used to set row heights."""
    return max(1, len(textwrap.wrap(text, int(width * chars))))


def main():
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    with open(LOOKUP, encoding="utf-8", newline="") as f:
        comp = list(csv.DictReader(f))
    codes = [r["code"] for r in comp]
    if codes != ["C1", "C2", "C3", "C4", "C5", "C6"]:
        sys.exit(f"The compartments table does not carry C1-C6 in order: {codes}")
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    out = os.path.join(OUT_DIR, f"tab01_compartments_v1_{stamp}.xlsx")
    if os.path.exists(out):
        sys.exit(f"Already exists {out}: not overwritten")

    wb = xlsxwriter.Workbook(out)
    ws = wb.add_worksheet("Table 1")
    base = {"font_name": FONT, "font_color": "black", "text_wrap": True, "valign": "top"}

    def fmt(**k):
        return wb.add_format({**base, **k})

    cap, cap_b, cap_i = fmt(font_size=9), fmt(font_size=9, bold=True), fmt(font_size=9, italic=True)
    head = fmt(font_size=10, bold=True, top=2, bottom=1)
    txt, sup = fmt(font_size=10), fmt(font_size=10, font_script=1)
    note, note_sup = fmt(font_size=9), fmt(font_size=9, font_script=1)
    for j, w in enumerate(WIDTHS):
        ws.set_column(j, j, w)
    total_w = sum(WIDTHS)

    ws.merge_range(0, 0, 0, 3, "", cap)
    ws.write_rich_string(0, 0, cap_b, "Table 1. ", cap, CAPTION[0], cap_i, CAPTION[1],
                         cap, CAPTION[2], cap)
    ws.set_row(0, 13 * lines("Table 1. " + "".join(CAPTION), total_w, 1.4))
    for j, h in enumerate(["Code", "Compartment", "Sources included", "Azole exposure regimen"]):
        ws.write(1, j, h, head)
    for i, r in enumerate(comp):
        c, row = r["code"], 2 + i
        cell = fmt(font_size=10, bottom=2) if c == "C6" else fmt(font_size=10)
        ws.write(row, 0, c, cell)
        cells = [(r["name"], NAME_NOTE), (SOURCES[c], {}), (REGIMEN[c], REGIMEN_NOTE)]
        for j, (text, notes) in enumerate(cells, 1):
            if c in notes:
                ws.write_rich_string(row, j, txt, text, sup, notes[c], cell)
            else:
                ws.write(row, j, text, cell)
        need = max(lines(t, w) for t, w in zip([r["name"], SOURCES[c], REGIMEN[c]], WIDTHS[1:]))
        ws.set_row(row, 14 * need + 2)
    for k, (n, text) in enumerate(FOOTNOTES):
        row = 2 + len(comp) + k
        ws.merge_range(row, 0, row, 3, "", note)
        ws.write_rich_string(row, 0, note_sup, n, note, " " + text, note)
        ws.set_row(row, 13 * lines(text, total_w, 1.4))
    ws.hide_gridlines(2)
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    wb.close()

    log = {"script": os.path.basename(__file__),
           "run_time": datetime.now().astimezone().isoformat(timespec="seconds"),
           "python": platform.python_version(), "xlsxwriter": xlsxwriter.__version__,
           "source": "registered protocol, section 3 and Table 1 (PROSPERO CRD420261486387)",
           "inputs": {LOOKUP: md5(LOOKUP)}, "outputs": {os.path.basename(out): md5(out)},
           "rows": len(comp), "footnotes": len(FOOTNOTES)}
    log_path = os.path.join(LOG_DIR, f"02_tab01_compartments_v1_{stamp}.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=1, ensure_ascii=False)
    print(f"Table 1: {len(comp)} compartimentos, {len(FOOTNOTES)} footnotes")
    print(f"Workbook: {out}\nLog: {log_path}")


if __name__ == "__main__":
    main()
