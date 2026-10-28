#!/usr/bin/env python3
"""make_isolate_groups_multicompartment_v1.py

Sheet for the team to allocate by compartment the isolates of the reports that
sample two or more compartments (analysis_dataset_v1). One row per report and
sampled compartment. It is the first stretch of the isolate_groups table of the data
dictionary (same column names). Table 2 and Figure 2 count a report in a
compartment only if it contributed at least one verified isolate in this sheet.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/make_isolate_groups_multicompartment_v1.py
Outputs (if there is already a v1 sheet in the folder it does not generate another, so as not to overwrite what was filled in):
  08_phase6_data_extraction/verification/isolate_groups_multicompartment_v1_<date>.xlsx
  10_phase8_analysis/results/logs/make_isolate_groups_multicompartment_v1_<date-time>.json
"""
import glob, hashlib, json, os, platform, sys
from datetime import datetime

import pandas as pd
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

D = "10_phase8_analysis/data/analysis_dataset_v2_2026-10-23"
IN = {"studies": f"{D}/studies.csv", "ast": f"{D}/ast.csv",
      "reports": "10_phase8_analysis/data/tidy_tables_v0_2026-10-20/reports.csv",
      "lookup": "10_phase8_analysis/data/lookups/compartments_v1.csv"}
OUT_DIR = "08_phase6_data_extraction/verification"
LOG_DIR = "10_phase8_analysis/results/logs"
CONTEXT = ["group_id", "report_id", "study_label", "year", "doi", "pdf_file", "pdf_status", "title",
           "compartments_sampled", "compartment", "compartment_name", "n_tropicalis_report",
           "ast_max_n_tested", "sources_extracted"]
FILL = ["n_isolates", "verification_status", "location_in_report", "compartment_corrected",
        "agronomic_management", "verified_by", "verified_date", "note"]
CHECK = ["sum_report", "matches_total"]
LISTS = {"verification_status": ["pending", "verified", "not_separable", "not_verifiable"],
         "compartment_corrected": ["C1", "C2", "C3", "C4", "C5", "C6"],
         "agronomic_management": ["documented_present", "documented_absent", "not_evaluated"]}
WIDE = {"title": 40, "sources_extracted": 70, "pdf_file": 30, "location_in_report": 18, "note": 40}
INSTRUCTIONS = [
    "Allocation of isolates by compartment: reports that sample two or more compartments",
    "Purpose. n_tropicalis_report is the total of the report. Table 2 and Figure 2 count a "
    "report in a compartment only if it contributed at least one verified C. tropicalis isolate in that "
    "compartment. While any of its rows is not verified, the report appears as 'Not allocated'.",
    "What to fill in on each row, reading the full text (results and tables, not the abstract):",
    "n_isolates: C. tropicalis isolates recovered from that compartment; 0 if it was sampled and nothing was "
    "isolated. Each isolate is counted only once.",
    "verification_status: verified (n_isolates read from the article); not_separable (the article does not give the "
    "number for this compartment: n_isolates stays empty); not_verifiable (the PDF could not be reviewed); "
    "pending (not reviewed).",
    "location_in_report: table, figure or page the number comes from.",
    "compartment_corrected: only if the article shows that the stratum belongs to another compartment "
    "according to Table 1 of the protocol; explain it in note.",
    "agronomic_management: only in C3 and C5 rows: documented_present, documented_absent or not_evaluated. "
    "It is the C3/C5 discriminant and defines the strict reading of C5.",
    "verified_by: reviewer identifier. verified_date: YYYY-MM-DD.",
    "Context columns (not edited). sources_extracted is the text of the extraction, "
    "not verified. ast_max_n_tested is the largest n tested in the susceptibility rows of that "
    "compartment: it is a hint, not the number of isolates.",
    "sum_report and matches_total compare the sum of n_isolates of the report with its total (if they do not "
    "update, Ctrl+Shift+F9). A difference is not always an error (for example, reference "
    "isolates included in the total): explain it in note.",
    "If a compartment is missing, add a row with the same report_id and group_id = report_id_Cx.",
    "Save with the same file name, without changing columns or sheets, and without leaving copies in this "
    "folder. The Table 2 script reads this file and records its MD5.",
]


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_rows():
    s = pd.read_csv(IN["studies"])
    ast = pd.read_csv(IN["ast"], low_memory=False)
    rep = pd.read_csv(IN["reports"], low_memory=False)[["report_id", "pdf_file", "pdf_status", "sources_raw"]]
    names = pd.read_csv(IN["lookup"]).set_index("code")["name"]
    multi = s[s["n_compartments"] > 1]
    rows = multi.assign(compartment=multi["compartments"].str.split(";")).explode("compartment")
    hint = ast.groupby(["study_id", "compartment"])["n_tested"].max()
    rows["ast_max_n_tested"] = [hint.get((i, c)) for i, c in zip(rows["study_id"], rows["compartment"])]
    rows = rows.merge(rep, left_on="study_id", right_on="report_id", how="left")
    out = pd.DataFrame({
        "group_id": rows["study_id"] + "_" + rows["compartment"], "report_id": rows["study_id"],
        "study_label": rows["study_label"], "year": rows["year"], "doi": rows["doi"],
        "pdf_file": rows["pdf_file"], "pdf_status": rows["pdf_status"], "title": rows["title"],
        "compartments_sampled": rows["compartments"], "compartment": rows["compartment"],
        "compartment_name": rows["compartment"].map(names), "n_tropicalis_report": rows["n_tropicalis"],
        "ast_max_n_tested": rows["ast_max_n_tested"], "sources_extracted": rows["sources_raw"]})
    return out.sort_values(["study_label", "compartment"]).reset_index(drop=True), multi


def check_formulas(L, r):
    """Formulas of spreadsheet row r: sum of n_isolates of the report and its comparison with the total."""
    b, st, n = L["report_id"], L["verification_status"], L["n_isolates"]
    same = f"{b}:{b},{b}{r},{st}:{st},"
    match = (f'=IF(COUNTIFS({same}"pending")+COUNTIFS({same}"not_verifiable")>0,"incomplete",'
             f'IF(COUNTIFS({same}"not_separable")>0,"not separable",'
             f'IF({L["sum_report"]}{r}={L["n_tropicalis_report"]}{r},"yes","no")))')
    return f"=SUMIF({b}:{b},{b}{r},{n}:{n})", match


def write_book(path, out):
    wb = xlsxwriter.Workbook(path)
    bold = wb.add_format({"bold": True, "font_color": "black", "text_wrap": True, "valign": "top"})
    txt = wb.add_format({"font_color": "black", "valign": "top"})
    wrap = wb.add_format({"font_color": "black", "valign": "top", "text_wrap": True})
    plain, ital = wb.add_format({"font_color": "black"}), wb.add_format({"italic": True, "font_color": "black"})
    wi = wb.add_worksheet("Instructions")
    wi.set_column(0, 0, 120)
    for i, line in enumerate(INSTRUCTIONS):
        bits = line.split("C. tropicalis")  # species name in italics
        if len(bits) == 1:
            wi.write(i, 0, line, bold if i == 0 else wrap)
            continue
        frags = []
        for k, b in enumerate(bits):
            frags += [plain, b] if b else []
            frags += [ital, "C. tropicalis"] if k < len(bits) - 1 else []
        wi.write_rich_string(i, 0, *frags, wrap)
    ws = wb.add_worksheet("allocation")
    cols = CONTEXT + FILL + CHECK
    L = {c: xl_col_to_name(j) for j, c in enumerate(cols)}
    for j, c in enumerate(cols):
        ws.write(0, j, c, bold)
        ws.set_column(j, j, WIDE.get(c, 14))
    for i, rec in enumerate(out.to_dict("records"), start=1):
        for c in CONTEXT:
            v = rec[c]
            if pd.isna(v):
                continue
            v = int(v) if isinstance(v, float) else v
            ws.write(i, cols.index(c), v, wrap if c in WIDE else txt)
        ws.write(i, cols.index("verification_status"), "pending", txt)
        f_sum, f_match = check_formulas(L, i + 1)
        # cached values = state of a blank form, shown until the sheet recalculates
        ws.write_formula(i, cols.index("sum_report"), f_sum, txt, 0)
        ws.write_formula(i, cols.index("matches_total"), f_match, txt, "incomplete")
    last = len(out) + 200  # room for rows the team adds
    for c, values in LISTS.items():
        ws.data_validation(1, cols.index(c), last, cols.index(c), {"validate": "list", "source": values})
    ws.data_validation(1, cols.index("n_isolates"), last, cols.index("n_isolates"),
                       {"validate": "integer", "criteria": ">=", "value": 0})
    ws.freeze_panes(1, 3)
    ws.autofilter(0, 0, len(out), len(cols) - 1)
    wb.close()


def main():
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    for k, p in IN.items():
        if not os.path.exists(p):
            sys.exit(f"Missing input {k}: {p}")
    prev = glob.glob(os.path.join(OUT_DIR, "isolate_groups_multicompartment_v1_*.xlsx"))
    if prev:
        sys.exit(f"Already exists {prev[0]}: no other sheet is generated so as not to overwrite what was filled in")
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    out, multi = build_rows()
    now = datetime.now()
    path = os.path.join(OUT_DIR, f"isolate_groups_multicompartment_v1_{now:%Y-%m-%d}.xlsx")
    write_book(path, out)
    log = {"script": os.path.basename(__file__),
           "run_time": now.astimezone().isoformat(timespec="seconds"),
           "python": platform.python_version(), "pandas": pd.__version__,
           "xlsxwriter": xlsxwriter.__version__,
           "inputs": {k: {"path": p, "md5": md5(p)} for k, p in IN.items()},
           "outputs": {os.path.basename(path): md5(path)},
           "reports": int(multi["study_id"].nunique()), "rows": len(out),
           "rows_by_compartment": out["compartment"].value_counts().sort_index().to_dict()}
    log_path = os.path.join(LOG_DIR, f"make_isolate_groups_multicompartment_v1_{now:%Y-%m-%dT%H%M%S}.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=1, ensure_ascii=False)
    print(f"Reports with two or more compartments: {log['reports']}; rows: {log['rows']}")
    print("Rows by compartment:", log["rows_by_compartment"])
    print(f"Planilla: {path}\nLog: {log_path}")


if __name__ == "__main__":
    main()
