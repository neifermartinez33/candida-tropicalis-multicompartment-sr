#!/usr/bin/env python3
"""42_tabS12_deviation_log_v4.py (2026-10-29)

Table S12 v4: the deviation log of v3 with entry 22 rewritten, because the team decided on 2026-10-29 to rate
the certainty of the evidence with GRADE (Table S16) instead of leaving it pending. Nothing else changes: the
script reads the v3 workbook and its CSV mirror, replaces the three text cells of that entry and writes v4 with
the same format. The previous version is archived with its MD5 outside the deposit.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/42_tabS12_deviation_log_v4.py
Outputs (never overwritten): 12_documents/supplementary/tables/tabS12_deviation_log_v4_<date-time>.xlsx and .csv;
log in 10_phase8_analysis/results/logs/42_tabS12_deviation_log_v4_<date-time>.json.
"""
import csv
import glob
import os
import sys
from datetime import datetime

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_log  # noqa: E402

DIR = "12_documents/supplementary/tables"
ENTRY = "22"
OLD_START = "GRADE certainty and summary of findings table not produced"
NEW = {
    "Deviation or analysis decision":
        "Certainty of the evidence rated with GRADE adapted to single proportions estimated from observational "
        "data, stratum by stratum (Table S16); the numeric thresholds that operationalise each domain were "
        "agreed by the team on 29 October 2026, after the results had been seen; no summary of findings table "
        "was produced because the review estimates no effect measure",
    "Reason":
        "The protocol applies GRADE but fixes no numeric thresholds; those used are reported with the rating of "
        "every stratum in Table S16, so that any rating can be recomputed or re-rated with other thresholds",
    "After data": "Yes",
    "Row of Table A1": "7",
}


def newest(pattern):
    hits = sorted(glob.glob(os.path.join(DIR, pattern)))
    if not hits:
        sys.exit(f"missing input: {pattern}")
    return hits[-1]


def main():
    src_x = newest("tabS12_deviation_log_v3_*.xlsx")
    src_c = newest("tabS12_deviation_log_v3_*.csv")
    stamp = datetime.now().astimezone()
    st = stamp.strftime("%Y-%m-%dT%H%M%S")
    out_x = f"{DIR}/tabS12_deviation_log_v4_{st}.xlsx"
    out_c = f"{DIR}/tabS12_deviation_log_v4_{st}.csv"
    if os.path.exists(out_x) or os.path.exists(out_c):
        sys.exit("output exists")

    wb = openpyxl.load_workbook(src_x)
    ws = wb.worksheets[0]
    head = [c.value for c in ws[1]]
    target = [r for r in range(2, ws.max_row + 1) if str(ws.cell(row=r, column=1).value) == ENTRY]
    if len(target) != 1:
        sys.exit(f"entry {ENTRY} found {len(target)} times in {src_x}")
    r = target[0]
    if not str(ws.cell(row=r, column=2).value or "").startswith(OLD_START):
        sys.exit(f"entry {ENTRY} of {src_x} is not the GRADE entry: {ws.cell(row=r, column=2).value!r}")
    for col, name in enumerate(head, start=1):
        if name in NEW:
            ws.cell(row=r, column=col).value = NEW[name]
    wb.save(out_x)

    with open(src_c, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    hit = [i for i, row in enumerate(rows) if row and row[0] == ENTRY]
    if len(hit) != 1:
        sys.exit(f"entry {ENTRY} found {len(hit)} times in {src_c}")
    i = hit[0]
    for col, name in enumerate(rows[0]):
        if name.lstrip("﻿") in NEW:
            rows[i][col] = NEW[name.lstrip("﻿")]
    with open(out_c, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)

    log = run_log.write(__file__, [src_x, src_c], [out_x, out_c], entry=int(ENTRY), entries=len(rows) - 1)
    print(f"written {out_x} and {out_c}; entries {len(rows) - 1}; log {log}")
    print(" | ".join(rows[i])[:400])


if __name__ == "__main__":
    main()
