#!/usr/bin/env python3
"""make_isolate_groups_multicompartment_v2.py (2026-10-24)

Allocation sheet by compartment for the reports that sample two or more compartments and that
entered dataset v3 through round 2 (doubtful and excluded at extraction), and which are therefore not in
isolate_groups_multicompartment_v1_2026-10-21.xlsx. Same columns, same instructions and same formulas
as v1 (imported from make_isolate_groups_multicompartment_v1.py, which is not touched).

Usage, from the project root (after build_analysis_dataset_v3.py):
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/make_isolate_groups_multicompartment_v2.py [--provisional]
If there are already sheets, it only lists the reports they lack, in a new sheet with date and time.
Output: 08_phase6_data_extraction/verification/isolate_groups_multicompartment_v2_<date-time>.xlsx and its log.
"""
import glob
import json
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_isolate_groups_multicompartment_v1 as M1  # noqa: E402

OUT_DIR = "08_phase6_data_extraction/verification"


def newest_dataset(provisional):
    ds = sorted(d for d in glob.glob("10_phase8_analysis/data/analysis_dataset_v3_*")
                if os.path.isdir(d) and d.endswith("_PROVISIONAL") == provisional)
    if not ds:
        sys.exit("There is no v3 dataset" + (" PROVISIONAL" if provisional else " FINAL"))
    return ds[-1]


def build_rows():
    """As M1.build_rows, but dataset v3 already carries pdf_file: the one in reports.csv is taken."""
    s = pd.read_csv(M1.IN["studies"], low_memory=False)
    s = s.drop(columns=[c for c in ("pdf_file", "pdf_status", "sources_raw") if c in s.columns])
    ast = pd.read_csv(M1.IN["ast"], low_memory=False)
    rep = pd.read_csv(M1.IN["reports"], low_memory=False)[["report_id", "pdf_file", "pdf_status", "sources_raw"]]
    names = pd.read_csv(M1.IN["lookup"]).set_index("code")["name"]
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


def main():
    provisional = "--provisional" in sys.argv[1:]
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    D = newest_dataset(provisional)
    M1.IN.update({"studies": f"{D}/studies.csv", "ast": f"{D}/ast.csv"})
    done = set()
    books = sorted(glob.glob(os.path.join(OUT_DIR, "isolate_groups_multicompartment_v*.xlsx")))
    for f in books:
        done |= set(pd.read_excel(f, sheet_name="allocation").report_id.dropna())
    out, multi = build_rows()
    out = out[~out.report_id.isin(done)].reset_index(drop=True)
    print(f"Dataset {D}\nMulticompartment reports: {multi.study_id.nunique()}; already in sheets: "
          f"{multi.study_id.isin(done).sum()}; new: {out.report_id.nunique()}")
    if not len(out):
        print("Nothing to do.")
        return
    now = datetime.now()
    path = os.path.join(OUT_DIR, f"isolate_groups_multicompartment_v2_{now:%Y-%m-%dT%H%M%S}.xlsx")
    if os.path.exists(path):
        sys.exit(f"Already exists {path}")
    M1.write_book(path, out)
    log = {"script": os.path.basename(__file__), "run_time": now.astimezone().isoformat(timespec="seconds"),
           "dataset": D, "previous_books": [os.path.basename(b) for b in books],
           "inputs": {k: {"path": p, "md5": M1.md5(p)} for k, p in M1.IN.items()},
           "outputs": {os.path.basename(path): M1.md5(path)}, "reports": int(out.report_id.nunique()), "rows": len(out)}
    os.makedirs(M1.LOG_DIR, exist_ok=True)
    with open(os.path.join(M1.LOG_DIR, f"make_isolate_groups_multicompartment_v2_{now:%Y-%m-%dT%H%M%S}.json"),
              "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False)
    print(f"Planilla: {path} ({log['reports']} reports, {log['rows']} rows)")


if __name__ == "__main__":
    main()
