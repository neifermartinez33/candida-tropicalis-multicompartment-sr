#!/usr/bin/env python3
"""03_tab02_characteristics_v1.py

Table 2 of the manuscript (Results 3.2, SQ1): characteristics of the included reports by
recovery compartment. Unit: the report (analysis_dataset_v1). The independent
collections (EC12) are not yet resolved: the table is provisional.

Counting rule. A single-compartment report counts in that compartment with its
n_tropicalis. A report that samples two or more counts in each compartment where it contributed at
least one isolate, according to the sheet isolate_groups_multicompartment_v1, only when all its
rows are 'verified'. If any row is pending or 'not_separable', it goes to 'Not allocated'
with its total.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/03_tab02_characteristics_v1.py
Outputs (never overwritten):
  12_documents/tables/tab02_characteristics_v1_<date-time>.xlsx
  10_phase8_analysis/results/tab02_characteristics_v1_<date-time>.csv  (cells of the table)
  10_phase8_analysis/results/report_compartment_v1_<date-time>.csv     (allocation; used by Figure 2)
  10_phase8_analysis/results/logs/03_tab02_characteristics_v1_<date-time>.json
"""
import glob, hashlib, json, os, platform, sys, textwrap
from datetime import datetime

import pandas as pd
import xlsxwriter

D = "10_phase8_analysis/data/analysis_dataset_v2_2026-10-23"
IN = {k: f"{D}/{k}.csv" for k in ("studies", "ast", "molecular", "genotypes")}
IN["lookup"] = "10_phase8_analysis/data/lookups/compartments_v1.csv"
ALLOC = "08_phase6_data_extraction/verification/isolate_groups_multicompartment_v1_*.xlsx"
OUT_TAB, OUT_RES = "12_documents/tables", "10_phase8_analysis/results"
LOG_DIR = "10_phase8_analysis/results/logs"
FONT = "Palatino Linotype"
DASH = chr(8211)  # en dash for ranges
COMPS = ["C1", "C2", "C3", "C4", "C5", "C6"]
COLS = COMPS + ["not_allocated", "ALL"]  # a code NA would be read as missing by pandas and R
REGIONS = [("AFR", "African Region"), ("AMR", "Region of the Americas"),
           ("EMR", "Eastern Mediterranean Region"), ("EUR", "European Region"),
           ("SEAR", "South-East Asia Region"), ("WPR", "Western Pacific Region"), ("MULTI", "Multinational")]
DESIGN = [("Cross-sectional", ["cross_sectional"]), ("Surveillance", ["surveillance"]),
          ("Cohort", ["cohort"]), ("Case" + DASH + "control", ["case_control"]),
          ("Case series or case report", ["case_series", "case_report"]),
          ("Laboratory evaluation", ["laboratory_evaluation"]),
          ("Other", ["retrospective", "prospective", "trial", "other"])]
SPECIES_ID = [("Molecular", "molecular"), ("MALDI-TOF MS", "MALDI_TOF"), ("Automated system", "automated"),
              ("Biochemical panel", "biochemical"), ("Chromogenic medium", "chromogenic"),
              ("Conventional phenotypic", "conventional"), ("Not classifiable", "not_specified")]
DATA = [("Antifungal susceptibility", "ast"), ("Molecular resistance determinants", "mol"),
        ("Genotyping", "gen"), ("Clade 4 assignment", "clade4"),
        ("Prior azole exposure documented", "azole"), ("Agricultural azoles tested", "agri"),
        ("Eligible for meta-analysis (provisional)", "elig")]


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def num(x):
    """Thousands separator; one decimal only when the value is not whole."""
    return f"{x:,.0f}" if float(x).is_integer() else f"{x:,.1f}"


def npct(k, n):
    return "0" if k == 0 else f"{k:,} ({100 * k / n:.1f})"


def load_allocation():
    files = sorted(glob.glob(ALLOC))
    if len(files) > 1:
        sys.exit("There is more than one allocation sheet: " + ", ".join(files))
    if not files:
        cols = ["report_id", "compartment", "compartment_corrected", "n_isolates", "verification_status"]
        return pd.DataFrame(columns=cols), None
    al = pd.read_excel(files[0], sheet_name="allocation")
    al["verification_status"] = al["verification_status"].fillna("pending").astype(str).str.strip().str.lower()
    al["n_isolates"] = pd.to_numeric(al["n_isolates"], errors="coerce")
    return al, files[0]


def assign(s, al):
    """One row per report and Table 2 column: C1-C6, or not_allocated while its isolates are not."""
    one = s[s["n_compartments"] == 1]
    parts = [pd.DataFrame({"report_id": one["study_id"], "column": one["compartments"],
                           "comp_src": one["compartments"], "isolates": one["n_tropicalis"],
                           "status": "single"})]
    multi = s.loc[s["n_compartments"] > 1, ["study_id", "n_tropicalis"]]
    for rid, total in multi.itertuples(index=False):
        g = al[al["report_id"] == rid]
        g = g.assign(column=g["compartment_corrected"].fillna(g["compartment"]))
        done = len(g) > 0 and g["verification_status"].eq("verified").all() and g["n_isolates"].notna().all()
        pos = g[g["n_isolates"] >= 1]
        if done and not len(pos):
            print(f"Warning: {rid} is verified without isolates in any compartment; it remains pending")
        if done and len(pos):
            agg = pos.groupby("column").agg(isolates=("n_isolates", "sum"),
                                             comp_src=("compartment", lambda x: ";".join(sorted(set(x)))))
            parts.append(agg.reset_index().assign(report_id=rid, status="allocated"))
        else:
            state = "not_separable" if g["verification_status"].eq("not_separable").any() else "pending"
            parts.append(pd.DataFrame({"report_id": [rid], "column": ["not_allocated"], "comp_src": [None],
                                       "isolates": [total], "status": [state]}))
    return pd.concat(parts, ignore_index=True)


def add_flags(frame, s, ast, mol, gen):
    """Report attributes plus data flags: per compartment where row tables allow it, else per report."""
    def pairs(df):
        return set(zip(df["study_id"], df["compartment"]))

    elig = ast[(ast["eligible_r_cbp"] == "YES") | (ast["eligible_nwt_ecv"] == "YES")]
    out = frame.join(s.set_index("study_id"), on="report_id")
    for key, pset, report_flag in [("ast", pairs(ast), "has_ast"), ("mol", pairs(mol), "has_molecular"),
                                   ("gen", pairs(gen), "has_genotype"), ("elig", pairs(elig), "eligible_ma")]:
        out["f_" + key] = [any((r, c) in pset for c in str(cs).split(";")) if col in COMPS else flag == "YES"
                           for r, col, cs, flag in zip(out["report_id"], out["column"], out["comp_src"],
                                                       out[report_flag])]
    out["f_clade4"] = out["clade4"].eq("YES")
    out["f_azole"] = out["azole_exposure_documented"].eq("YES")
    out["f_agri"] = out["agricultural_azoles_tested"].eq("YES")
    return out


def summarise(df):
    """Cells of one Table 2 column."""
    n, iso = len(df), df["isolates"].dropna()
    tot, yr = iso.sum(), df["year"].dropna()
    c = {"reports": f"{n:,}", "isolates": num(tot),
         "iso_median": f"{num(iso.median())} ({num(iso.quantile(0.25))}{DASH}{num(iso.quantile(0.75))})"
         if len(iso) else DASH,
         "largest": f"{100 * iso.max() / tot:.1f}" if tot else DASH,
         "countries": f"{df.loc[df['country_iso3'] != 'MULTI', 'country_iso3'].nunique():,}",
         "year": f"{yr.median():g} ({yr.min():.0f}{DASH}{yr.max():.0f})" if len(yr) else DASH,
         "period": npct(int(df["period_start"].notna().sum()), n)}
    for code, _ in REGIONS:
        c["region:" + code] = npct(int((df["who_region"] == code).sum()), n)
    for label, codes in DESIGN:
        c["design:" + label] = npct(int(df["design"].isin(codes).sum()), n)
    for _, code in SPECIES_ID:
        c["sid:" + code] = npct(int((df["species_id"] == code).sum()), n)
    for _, key in DATA:
        c[key] = npct(int(df["f_" + key].sum()), n)
    return c


def row_spec():
    """(label, cell key or None for a section heading, footnote, indented)."""
    rows = [("Reports, n", "reports", None, False), ("Isolates, n", "isolates", "2", False),
            ("Isolates per report, median (IQR)", "iso_median", None, False),
            ("Largest report, % of isolates", "largest", "3", False),
            ("Countries, n", "countries", None, False), ("WHO region, n (%)", None, None, False)]
    rows += [(lab, "region:" + code, "4" if code == "MULTI" else None, True) for code, lab in REGIONS]
    rows += [("Publication year, median (range)", "year", None, False),
             ("Collection period reported, n (%)", "period", None, False),
             ("Study design, n (%)", None, None, False)]
    rows += [(lab, "design:" + lab, "5" if lab == "Other" else None, True) for lab, _ in DESIGN]
    rows += [("Species identification, n (%)", None, "6", False)]
    rows += [(lab, "sid:" + code, None, True) for lab, code in SPECIES_ID]
    rows += [("Data reported, n (%)", None, "7", False)]
    rows += [(lab, key, "8" if key == "elig" else None, True) for lab, key in DATA]
    return rows


def footnotes(st, missing):
    return [
        ("1", "Reports that sample two or more compartments and whose isolates are not yet allocated by "
              f"compartment (verification pending, n = {st.get('pending', 0)}) or cannot be separated in the "
              f"source (n = {st.get('not_separable', 0)}). Once allocated, a report is counted in each "
              "compartment that contributed at least one isolate, so compartment columns are not additive."),
        ("2", "Sum of isolates as reported. Collections published in more than one report are not yet "
              "merged, so the same isolates may be counted more than once. Number of isolates not reported "
              f"in {missing} reports."),
        ("3", "Share of the column's isolates contributed by the report with most isolates."),
        ("4", "Reports sampling more than one country; their countries are not counted in Countries, n."),
        ("5", "Retrospective, prospective, trial or design not classifiable from the report."),
        ("6", "Highest-resolution method declared: molecular > MALDI-TOF MS > automated system > biochemical "
              "panel > chromogenic medium > conventional phenotypic. Not classifiable: generic phenotypic "
              "description, method cited from a previous publication, or no method stated."),
        ("7", "Susceptibility, molecular determinants, genotyping and eligibility refer to the isolates "
              "of the column's compartment; clade 4, prior azole exposure and agricultural azoles tested "
              "are recorded per report."),
        ("8", "Denominators per antifungal agent and a declared interpretive criterion or MIC data, as judged "
              "at extraction; risk of bias not yet assessed."),
        ("", "Provisional version: analysis_dataset_v1, reports rather than independent collections; "
             "numbers not yet verified against the full texts. IQR, interquartile range; MALDI-TOF MS, "
             "matrix-assisted laser desorption/ionisation time-of-flight mass spectrometry; WHO, World "
             "Health Organization."),
    ]


def write_xlsx(path, header, rows, cells, notes):
    wb = xlsxwriter.Workbook(path)
    ws = wb.add_worksheet("Table 2")
    base = {"font_name": FONT, "font_color": "black", "valign": "top"}

    def fmt(**k):
        return wb.add_format({**base, **k})

    ncol, widths = 1 + len(COLS), [36] + [14.5] * len(COLS)
    for j, w in enumerate(widths):
        ws.set_column(j, j, w)
    cap, cap_b = fmt(font_size=9, text_wrap=True), fmt(font_size=9, bold=True)
    ws.merge_range(0, 0, 0, ncol - 1, "", cap)
    ws.write_rich_string(0, 0, cap_b, "Table 2. ", cap,
                         "Characteristics of the included reports by compartment of recovery.", cap)
    head = {"font_size": 10, "bold": True, "top": 2, "bottom": 1, "text_wrap": True}
    ws.write(1, 0, "Characteristic", fmt(**head))
    for j, col in enumerate(COLS, 1):
        if col == "not_allocated":
            ws.write_rich_string(1, j, fmt(font_size=10, bold=True), "Not allocated",
                                 fmt(font_size=10, bold=True, font_script=1), "1",
                                 fmt(**head, align="center"))
        else:
            ws.write(1, j, header[col], fmt(**head, align="center"))
    ws.set_row(1, 40)
    for i, (label, key, note, indent) in enumerate(rows):
        r, edge = 2 + i, ({"bottom": 2} if i == len(rows) - 1 else {})
        lab = fmt(font_size=10, italic=key is None, indent=int(indent), **edge)
        if note:
            ws.write_rich_string(r, 0, fmt(font_size=10, italic=key is None), label,
                                 fmt(font_size=10, font_script=1), note, lab)
        else:
            ws.write(r, 0, label, lab)
        val = fmt(font_size=10, align="center", **edge)
        for j, col in enumerate(COLS, 1):
            ws.write(r, j, cells[col][key] if key else "", val)
    total_w, small = sum(widths), fmt(font_size=9, text_wrap=True)
    for k, (n, text) in enumerate(notes):
        r = 2 + len(rows) + k
        ws.merge_range(r, 0, r, ncol - 1, "", small)
        if n:
            ws.write_rich_string(r, 0, fmt(font_size=9, font_script=1), n, small, " " + text, small)
        else:
            ws.write(r, 0, text, small)
        ws.set_row(r, 13 * max(1, len(textwrap.wrap(text, int(total_w * 1.4)))))
    ws.hide_gridlines(2)
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    wb.close()


def main():
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    for k, p in IN.items():
        if not os.path.exists(p):
            sys.exit(f"Missing input {k}: {p}")
    s = pd.read_csv(IN["studies"])
    ast, mol, gen = (pd.read_csv(IN[k], low_memory=False) for k in ("ast", "molecular", "genotypes"))
    names = pd.read_csv(IN["lookup"]).set_index("code")["short_label"]
    al, al_path = load_allocation()
    unknown = sorted(set(al["report_id"].dropna()) - set(s.loc[s["n_compartments"] > 1, "study_id"]))
    if unknown:
        print("Warning: report_id of the sheet that are not multicompartment reports:", ", ".join(unknown))
    asg = assign(s, al)
    if asg["report_id"].nunique() != len(s):
        sys.exit("The allocation does not cover all the reports")
    every = pd.DataFrame({"report_id": s["study_id"], "column": "ALL", "comp_src": s["compartments"],
                          "isolates": s["n_tropicalis"], "status": "all"})
    frame = add_flags(pd.concat([asg, every], ignore_index=True), s, ast, mol, gen)
    cells = {col: summarise(frame[frame["column"] == col]) for col in COLS}
    header = {c: f"{c}\n{names[c]}" for c in COMPS}
    header["ALL"] = "All reports"
    status = asg.loc[asg["column"] == "not_allocated", "status"].value_counts().to_dict()
    rows, notes = row_spec(), footnotes(status, int(s["n_tropicalis"].isna().sum()))

    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    f_xlsx = os.path.join(OUT_TAB, f"tab02_characteristics_v1_{stamp}.xlsx")
    f_csv = os.path.join(OUT_RES, f"tab02_characteristics_v1_{stamp}.csv")
    f_asg = os.path.join(OUT_RES, f"report_compartment_v1_{stamp}.csv")
    for d in (OUT_TAB, OUT_RES, LOG_DIR):
        os.makedirs(d, exist_ok=True)
    for f in (f_xlsx, f_csv, f_asg):
        if os.path.exists(f):
            sys.exit(f"Already exists {f}: not overwritten")
    write_xlsx(f_xlsx, header, rows, cells, notes)
    plain = [{"characteristic": lab, **{(header.get(c, "Not allocated").replace("\n", " ")):
                                        (cells[c][key] if key else "") for c in COLS}}
             for lab, key, _, _ in rows]
    pd.DataFrame(plain).to_csv(f_csv, index=False)
    keep = ["report_id", "study_label", "column", "comp_src", "status", "isolates", "who_region",
            "country_iso3", "year"]
    frame.loc[frame["column"] != "ALL", keep].to_csv(f_asg, index=False)

    log = {"script": os.path.basename(__file__),
           "run_time": datetime.now().astimezone().isoformat(timespec="seconds"),
           "python": platform.python_version(), "pandas": pd.__version__,
           "xlsxwriter": xlsxwriter.__version__,
           "inputs": {k: {"path": p, "md5": md5(p)} for k, p in IN.items()},
           "allocation": {"path": al_path, "md5": md5(al_path) if al_path else None},
           "outputs": {os.path.basename(f): md5(f) for f in (f_xlsx, f_csv, f_asg)},
           "reports_by_column": {c: int((frame["column"] == c).sum()) for c in COLS},
           "status_counts": asg["status"].value_counts().to_dict()}
    log_path = os.path.join(LOG_DIR, f"03_tab02_characteristics_v1_{stamp}.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=1, ensure_ascii=False)
    print("Allocation sheet:", al_path or "does not exist (the multicompartment reports go to Not allocated)")
    print("Reports per column:", log["reports_by_column"])
    print("Status of the allocation:", log["status_counts"])
    print(f"Table: {f_xlsx}\nCells: {f_csv}\nAllocation: {f_asg}\nLog: {log_path}")


if __name__ == "__main__":
    main()
