#!/usr/bin/env python3
"""make_rob_books_round2_v1.py (2026-10-24)

Workbook B12 of round 2: RB8 (deduplication rule), methods_read, editorial status and site
fields for the reports eligible for the meta-analysis in dataset v3 that did not go through phase 7
(they are not in rob_consensus_2026-10-22.xlsx). They are, above all, reports that enter through the corrections
of 2026-10-24 (rows that the no_version filter left out, criterion separated from the method) and doubtful ones that the
review proposed for the meta-analysis.

Same vocabulary and same rules as the manual rob_manual_v2_2026-10-21.md (section 3 of
rob_rules_v2): every value other than not_declared requires a literal quote and page. One reviewer codes and
the second verifies (column agrees); discrepancies go to the third reviewer. It is declared as a
deviation: phase 7 was done with two blinded reviewers and consensus.

Usage, from the project root (after build_analysis_dataset_v3.py):
  conda run --no-capture-output -n ctrop_ma python -B 09_phase7_risk_of_bias/make_rob_books_round2_v1.py --provisional
  conda run --no-capture-output -n ctrop_ma python -B 09_phase7_risk_of_bias/make_rob_books_round2_v1.py
Takes the most recent v3 dataset (PROVISIONAL with --provisional). If B12 workbooks already exist, it only lists the
reports they lack, in a new workbook with its date and time: it never overwrites.
Output: 09_phase7_risk_of_bias/round2_2026-10-24/r2_b12_rob_new_reports_<date-time>.xlsx and its log.
"""
import glob
import json
import os
import re
import sys
from datetime import datetime

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

CONSENSUS = "09_phase7_risk_of_bias/rob_consensus_2026-10-22.xlsx"
SHEETS = ("Consensus_cal1_200", "Consensus_pass_904")
OUT = "09_phase7_risk_of_bias/round2_2026-10-24"
DEDUP = ["by_patient", "by_host_or_site", "by_sampling_point", "declared_unspecified",
         "repeated_included", "not_declared", "single_sampling", "not_retrievable"]
FONT = Font(name="Calibri", size=11, color="000000")
PREPRINT = re.compile(r"rxiv|research square|preprint|ssrn|preprints\.org|authorea|scielo preprints", re.I)
GREY = re.compile(r"tesis|thesis|disertaci|dissertation|monograf|trabajo de grado|congres|congress|abstract|resumen de|"
                  r"meeting|symposium|simposio|jornada|informe t[eé]cnico|report", re.I)


def md5(p):
    import hashlib
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def newest_dataset(provisional):
    ds = sorted(d for d in glob.glob("10_phase8_analysis/data/analysis_dataset_v3_*")
                if os.path.isdir(d) and d.endswith("_PROVISIONAL") == provisional)
    if not ds:
        sys.exit("There is no v3 dataset" + (" PROVISIONAL" if provisional else " FINAL"))
    return ds[-1]


def main():
    provisional = "--provisional" in sys.argv[1:]
    if not os.path.isdir("09_phase7_risk_of_bias"):
        sys.exit("Run from the project root")
    D = newest_dataset(provisional)
    st = pd.read_csv(f"{D}/studies.csv", low_memory=False)
    cons = pd.concat([pd.read_excel(CONSENSUS, sheet_name=h) for h in SHEETS])
    done = set(cons.report_id)
    for f in sorted(glob.glob(f"{OUT}/r2_b12_rob_new_reports_*.xlsx")):
        done |= set(pd.read_excel(f, sheet_name="reports").report_id)
    elig = st[(st.eligible_ma_v3 == "YES") & ~st.study_id.isin(done)].copy()
    print(f"Dataset {D}\nEligible for MA: {int((st.eligible_ma_v3 == 'YES').sum())}; "
          f"without risk-of-bias assessment: {len(elig)}")
    if not len(elig):
        print("Nothing to do.")
        return
    j = elig.journal.fillna("").astype(str) + " " + elig.title.fillna("").astype(str)
    elig["editorial_proposal"] = ["preprint" if PREPRINT.search(x) else ("grey" if GREY.search(x) else "peer_reviewed")
                                for x in j]
    elig["site_applies"] = elig.compartments.fillna("").str.contains("C3|C5").map({True: "YES", False: "NO"})
    book = pd.DataFrame({
        "report_id": elig.study_id, "study_label": elig.study_label, "year": elig.year, "journal": elig.journal, "doi": elig.doi,
        "country": elig.country, "compartments": elig.compartments, "design": elig.design, "pdf_file": elig.pdf_file,
        "entry_route": elig.entry_route, "site_applies": elig.site_applies, "dedup_rule": None, "dedup_quote": None,
        "dedup_page": None, "methods_read": None, "editorial_status": None,
        "editorial_proposal": elig.editorial_proposal, "agronomic_management": None, "agro_quote": None,
        "agro_page": None, "reviewer": None, "verifier": None, "agrees": None, "dedup_rule_final": None,
        "comments": None}).sort_values("report_id")
    instr = ["Workbook B12. Risk of bias of the reports eligible for the meta-analysis that did not go through phase 7.",
             "Same manual as phase 7 (rob_manual_v2_2026-10-21.md): dedup_rule with one of the eight values; every value "
             "other than not_declared requires a literal quote (dedup_quote) and page (dedup_page). methods_read: YES when "
             "the whole methods section was read.",
             "editorial_status: peer_reviewed, preprint or grey (theses, conference abstracts, reports). editorial_proposal "
             "is only a suggestion from the journal.",
             "Only if site_applies is YES (the report samples C3 or C5): agronomic_management documented_present, "
             "documented_absent or not_evaluated, with agro_quote and agro_page.",
             "One reviewer codes (reviewer) and the second verifies (verifier, agrees YES or NO). If agrees is NO, the "
             "third reviewer writes dedup_rule_final. Without dedup_rule (or dedup_rule_final) the report has no RB8."]
    wb = Workbook()
    ws = wb.active
    ws.title = "instructions"
    for line in ["Round 2, workbook B12: risk of bias of new reports"] + instr:
        ws.append([line])
    ws.column_dimensions["A"].width = 140
    for row in ws.iter_rows():
        for c in row:
            c.font = FONT
            c.alignment = Alignment(wrap_text=True, vertical="top")
    sh = wb.create_sheet("reports")
    sh.append(list(book.columns))
    for rec in book.astype(object).where(book.notna(), None).itertuples(index=False):
        sh.append(list(rec))
    for row in sh.iter_rows():
        for c in row:
            c.font = FONT
            c.alignment = Alignment(vertical="top", wrap_text=True)
    for jx, col in enumerate(book.columns, start=1):
        sh.column_dimensions[get_column_letter(jx)].width = {"journal": 30, "pdf_file": 35, "dedup_quote": 45,
                                                             "agro_quote": 45, "comments": 40}.get(col, 14)
    sh.freeze_panes = "B2"
    n = len(book) + 1
    for col, vals in (("dedup_rule", DEDUP), ("dedup_rule_final", DEDUP), ("methods_read", ["YES", "NO"]),
                      ("editorial_status", ["peer_reviewed", "preprint", "grey"]), ("agrees", ["YES", "NO"]),
                      ("agronomic_management", ["documented_present", "documented_absent", "not_evaluated"])):
        L = get_column_letter(list(book.columns).index(col) + 1)
        dv = DataValidation(type="list", formula1='"' + ",".join(vals) + '"', allow_blank=True)
        sh.add_data_validation(dv)
        dv.add(f"{L}2:{L}{n}")
    os.makedirs(OUT, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    f = os.path.join(OUT, f"r2_b12_rob_new_reports_{stamp}.xlsx")
    if os.path.exists(f):
        sys.exit(f"Already exists {f}")
    wb.save(f)
    log = {"script": os.path.basename(__file__), "run_time": datetime.now().astimezone().isoformat(timespec="seconds"),
           "dataset": D, "inputs": {CONSENSUS: md5(CONSENSUS), f"{D}/studies.csv": md5(f"{D}/studies.csv")},
           "output": {os.path.basename(f): md5(f)}, "reports": len(book),
           "by_entry_route": book.entry_route.value_counts().to_dict(),
           "site_applies": int((book.site_applies == "YES").sum())}
    with open(os.path.join(OUT, f"make_rob_books_round2_v1_{stamp}.json"), "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False, default=str)
    print(f"Workbook: {f} ({len(book)} reports; by route {log['by_entry_route']})")


if __name__ == "__main__":
    main()
