#!/usr/bin/env python3
"""03_tab02_characteristics_v2.py (2026-10-24)

Table 2 of the manuscript (Results, SQ1): characteristics of the included studies by recovery
compartment, on analysis dataset v3. Changes from v1 (audit of 2026-10-24):
  - the unit is the independent collection (AR1 and the round-2 merges, from the ec12_collections_v2 of the
    same dataset); each collection is described by its representative report (the one with most
    C. tropicalis isolates; ties broken by the most recent and the lowest identifier), so isolates are no longer
    counted twice; the reports row also gives all the reports, including the secondary ones;
  - the data flags (susceptibility, molecular, genotype, eligible for the meta-analysis) hold for the collection
    if any of its reports has them in that compartment;
  - corrected species identification (species_id_v3), azole exposure on three levels, eligibility for the
    meta-analysis with rules v4;
  - the allocation of the multicompartment reports reads all the isolate_groups_multicompartment sheets
    (v1 and v2); a report cannot be in two.
Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/03_tab02_characteristics_v2.py [--provisional]
Outputs (never overwritten):
  12_documents/tables/tab02_characteristics_v2_<date-time>[_PROVISIONAL].xlsx
  10_phase8_analysis/results/tab02_characteristics_v2_<...>.csv, collection_compartment_v2_<...>.csv (used by
  Figure 2) and logs/03_tab02_characteristics_v2_<...>.json
"""
import glob
import json
import os
import platform
import sys
from datetime import datetime

import pandas as pd
import xlsxwriter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib  # noqa: E402

T1 = importlib.import_module("03_tab02_characteristics_v1")  # formatting functions of v1, unchanged

ALLOC = "08_phase6_data_extraction/verification/isolate_groups_multicompartment_v*.xlsx"
LOOKUP = "10_phase8_analysis/data/lookups/compartments_v1.csv"
OUT_TAB, OUT_RES, LOG_DIR = "12_documents/tables", "10_phase8_analysis/results", "10_phase8_analysis/results/logs"
COMPS, COLS = T1.COMPS, T1.COLS
DATA = [("Antifungal susceptibility", "ast"), ("Molecular resistance determinants", "mol"),
        ("Genotyping", "gen"), ("Clade 4 assignment", "clade4"),
        ("Prior azole exposure documented (present or absent)", "azole"), ("Agricultural azoles tested", "agri"),
        ("Eligible for meta-analysis", "elig")]


def newest(pat, provisional):
    f = sorted(x for x in glob.glob(pat) if x.rstrip("/").endswith(("_PROVISIONAL", "_PROVISIONAL.csv")) == provisional)
    return f[-1] if f else None


def load_allocation():
    files = sorted(glob.glob(ALLOC))
    parts = []
    for f in files:
        al = pd.read_excel(f, sheet_name="allocation")
        al["verification_status"] = al["verification_status"].fillna("pending").astype(str).str.strip().str.lower()
        al["n_isolates"] = pd.to_numeric(al["n_isolates"], errors="coerce")
        al["_book"] = os.path.basename(f)
        parts.append(al)
    al = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
        columns=["report_id", "compartment", "compartment_corrected", "n_isolates", "verification_status", "_book"])
    twice = al.groupby("report_id")["_book"].nunique()
    if (twice > 1).any():
        sys.exit("Reports allocated in two sheets: " + ", ".join(twice[twice > 1].index))
    return al, files


def main():
    provisional = "--provisional" in sys.argv[1:]
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    D = newest("10_phase8_analysis/data/analysis_dataset_v3_*", provisional)
    if not D:
        sys.exit("There is no v3 dataset" + (" PROVISIONAL" if provisional else " FINAL"))
    f_ec12 = newest(os.path.join(OUT_RES, "ec12_collections_v2_*.csv"), provisional)
    if not f_ec12:
        sys.exit("ec12_collections_v2 is missing: run 04_ma_input_v2.py first")
    stamp4 = os.path.basename(f_ec12)[len("ec12_collections_v2_"):-4]
    lg = json.load(open(os.path.join(LOG_DIR, f"04_ma_input_v2_{stamp4}.json"), encoding="utf-8"))
    if lg["inputs"]["studies"]["path"] != f"{D}/studies.csv":
        sys.exit(f"{f_ec12} was not built with {D}: run 04_ma_input_v2.py on that dataset first")
    IN = {k: f"{D}/{k}.csv" for k in ("studies", "ast", "molecular", "genotypes")}
    IN["lookup"], IN["ec12"] = LOOKUP, f_ec12
    s = pd.read_csv(IN["studies"], low_memory=False)
    ast, mol, gen = (pd.read_csv(IN[k], low_memory=False) for k in ("ast", "molecular", "genotypes"))
    names = pd.read_csv(LOOKUP).set_index("code")["short_label"]
    ec = pd.read_csv(f_ec12)
    col_of = dict(zip(ec.report_id, ec.collection_id))
    s["collection_id"] = s.study_id.map(col_of).fillna("COL_" + s.study_id)
    # representative report of each collection
    s["_n"] = pd.to_numeric(s.n_tropicalis, errors="coerce").fillna(-1)
    rep = (s.sort_values(["_n", "year", "study_id"], ascending=[False, False, True])
           .drop_duplicates("collection_id"))
    s["species_id"] = s.species_id_v3
    s["azole_exposure_documented"] = s.azole_exposure_status.ne("not_documented").map({True: "YES", False: "NO"})
    s["eligible_ma"] = s.eligible_ma_v3
    al, books = load_allocation()
    r = rep.copy()
    zero = r[r.n_compartments.fillna(0) == 0]
    asg = T1.assign(r[r.n_compartments.fillna(0) > 0], al)
    if len(zero):
        asg = pd.concat([asg, pd.DataFrame({"report_id": zero.study_id, "column": "not_allocated", "comp_src": None,
                                            "isolates": zero.n_tropicalis, "status": "no_compartment"})],
                        ignore_index=True)
    if asg.report_id.nunique() != len(r):
        sys.exit("The allocation does not cover all the representative reports")
    every = pd.DataFrame({"report_id": r.study_id, "column": "ALL", "comp_src": r.compartments,
                          "isolates": r.n_tropicalis, "status": "all"})
    frame = pd.concat([asg, every], ignore_index=True)
    # data flags per collection: any report of the collection, in the compartment of the column
    rep_col = dict(zip(s.study_id, s.collection_id))
    ast_v = ast.assign(eligible_r_cbp=ast.eligible_r_cbp_v3, eligible_nwt_ecv=ast.eligible_nwt_ecv_v3)
    for df in (ast_v, mol, gen):
        df["collection_id"] = df.study_id.map(rep_col)
    elig = ast_v[(ast_v.eligible_r_cbp == "YES") | (ast_v.eligible_nwt_ecv == "YES")]
    pairs = {k: set(zip(df.collection_id, df.compartment)) for k, df in
             (("ast", ast_v), ("mol", mol), ("gen", gen), ("elig", elig))}
    anyrep = {k: set(df.collection_id) for k, df in (("ast", ast_v), ("mol", mol), ("gen", gen), ("elig", elig))}
    frame = frame.join(r.set_index("study_id"), on="report_id")
    for key in ("ast", "mol", "gen", "elig"):
        frame["f_" + key] = [any((c, x) in pairs[key] for x in str(cs).split(";")) if col in COMPS else c in anyrep[key]
                             for c, col, cs in zip(frame.collection_id, frame.column, frame.comp_src)]
    cl4 = set(s.collection_id[s.clade4 == "YES"])
    az = set(s.collection_id[s.azole_exposure_documented == "YES"])
    ag = set(s.collection_id[s.agricultural_azoles_tested == "YES"])
    frame["f_clade4"] = frame.collection_id.isin(cl4)
    frame["f_azole"] = frame.collection_id.isin(az)
    frame["f_agri"] = frame.collection_id.isin(ag)
    T1.DATA = DATA
    cells = {}
    for c in COLS:
        sub = frame[frame.column == c]
        cc = T1.summarise(sub)
        # reports: all those of the collections of the column
        cc["reports_all"] = f"{int(s.collection_id.isin(set(sub.collection_id)).sum()):,}"
        cells[c] = cc
    header = {c: f"{c}\n{names[c]}" for c in COMPS}
    header["ALL"] = "All collections"
    status = asg.loc[asg.column == "not_allocated", "status"].value_counts().to_dict()
    rows = T1.row_spec()
    rows[0] = ("Collections (independent studies), n", "reports", None, False)
    rows.insert(1, ("Reports, n", "reports_all", "9", False))
    rows = [(lab.replace("Isolates per report", "Isolates per collection").replace("Largest report", "Largest collection"),
             k, n, i) for lab, k, n, i in rows]
    notes = T1.footnotes(status, int(r.n_tropicalis.isna().sum()))
    notes = [(n, t) for n, t in notes if n not in ("2", "8", "")]
    notes.insert(1, ("2", "Isolates of the representative report of each collection (the report with most "
                          "C. tropicalis isolates), so isolates published in more than one report are counted once. "
                          f"Number of isolates not reported in {int(r.n_tropicalis.isna().sum())} collections."))
    notes.append(("8", "Denominators per antifungal agent and a declared interpretive criterion, or MIC data "
                       "(analysis rules v4)."))
    notes.append(("9", "All reports of the collections in the column, including secondary reports of the same "
                       "collection (rule AR1 and the round-2 decisions on overlapping collections)."))
    notes.append(("", "IQR, interquartile range; MALDI-TOF MS, matrix-assisted laser desorption/ionisation time-of-flight "
                      "mass spectrometry; WHO, World Health Organization."
                      + (" PROVISIONAL: decisions of the round-2 verification pending; not for the manuscript."
                         if provisional else "")))
    notes = sorted(notes, key=lambda t: (t[0] == "", int(t[0]) if t[0] else 0))
    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S") + ("_PROVISIONAL" if provisional else "")
    f_xlsx = os.path.join(OUT_TAB, f"tab02_characteristics_v2_{stamp}.xlsx")
    f_csv = os.path.join(OUT_RES, f"tab02_characteristics_v2_{stamp}.csv")
    f_asg = os.path.join(OUT_RES, f"collection_compartment_v2_{stamp}.csv")
    for d in (OUT_TAB, OUT_RES, LOG_DIR):
        os.makedirs(d, exist_ok=True)
    for f in (f_xlsx, f_csv, f_asg):
        if os.path.exists(f):
            sys.exit(f"Already exists {f}: not overwritten")
    T1.write_xlsx(f_xlsx, header, rows, cells, notes)
    if provisional:
        import openpyxl
        wb = openpyxl.load_workbook(f_xlsx)
        ws = wb.active
        ws["A1"].value = "[PROVISIONAL] " + str(ws["A1"].value or "")
        wb.save(f_xlsx)
    plain = [{"characteristic": lab, **{header.get(c, "Not allocated").replace("\n", " "): (cells[c][k] if k else "")
                                        for c in COLS}} for lab, k, _, _ in rows]
    pd.DataFrame(plain).to_csv(f_csv, index=False)
    keep = ["collection_id", "report_id", "study_label", "column", "comp_src", "status", "isolates", "who_region",
            "country_iso3", "year"]
    frame.loc[frame.column != "ALL", keep].to_csv(f_asg, index=False)
    log = {"script": os.path.basename(__file__), "mode": "PROVISIONAL" if provisional else "FINAL",
           "run_time": datetime.now().astimezone().isoformat(timespec="seconds"),
           "python": platform.python_version(), "pandas": pd.__version__, "xlsxwriter": xlsxwriter.__version__,
           "inputs": {k: {"path": p, "md5": T1.md5(p)} for k, p in IN.items()},
           "allocation": {os.path.basename(f): T1.md5(f) for f in books},
           "outputs": {os.path.basename(f): T1.md5(f) for f in (f_xlsx, f_csv, f_asg)},
           "collections": int(len(r)), "reports": int(len(s)),
           "collections_by_column": {c: int((frame.column == c).sum()) for c in COLS},
           "status_counts": asg.status.value_counts().to_dict()}
    with open(os.path.join(LOG_DIR, f"03_tab02_characteristics_v2_{stamp}.json"), "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False, default=str)
    print("Dataset:", D)
    print(f"Collections: {len(r)}; reports: {len(s)}")
    print("Collections per column:", log["collections_by_column"])
    print("Status of the allocation:", log["status_counts"])
    print(f"Table: {f_xlsx}\nCells: {f_csv}\nAllocation: {f_asg}")


if __name__ == "__main__":
    main()
