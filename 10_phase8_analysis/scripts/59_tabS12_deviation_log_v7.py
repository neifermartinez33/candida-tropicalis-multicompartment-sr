#!/usr/bin/env python3
"""59_tabS12_deviation_log_v7.py (2026-10-30)

Table S12 v7: the log of v5 with entry 27 pointed to Table S17 and entry 28 added. The script reads the v5
workbook and its CSV mirror and writes v7 with the same format.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/59_tabS12_deviation_log_v7.py
Outputs (never overwritten): 12_documents/supplementary/tables/tabS12_deviation_log_v7_<date-time>.xlsx and .csv;
log in 10_phase8_analysis/results/logs/.
"""
import csv
import glob
import os
import sys
from copy import copy
from datetime import datetime

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_log  # noqa: E402

DIR = "12_documents/supplementary/tables"
OLD_2 = "Full-text screening and data extraction by a language model with targeted human verification, instead of duplicate human reading"
NEW_2 = "Full-text screening and data extraction performed with a language model as a tool, with targeted human verification; the protocol registered duplicate human reading"
OLD_27 = "1000 simulations per model and scenario; 45_qba_missed_reports_v2.R)"
NEW_27 = "1000 simulations per model and scenario; 45_qba_missed_reports_v2.R); results in Table S17"
NEW = [
    ["28", "Correction of the derivation of RB5 and RB6: the 36 reports that entered after the row verification had no method or standard at report level and "
           "were rated as not declaring them; both are now read from their verified rows. RB5 changed in 35 reports and RB6 in 18, and the overall judgement of "
           "10 reports moved from high to moderate (7) or low (3); SA9, the meta-regression on risk of bias and Tables S4, S8, S10 and S16 were recomputed",
     "Coding error found on 30 October 2026, after the results had been seen; the rules of Section 2.9 did not change. The pooled estimates of the main analysis "
     "do not depend on risk of bias and did not change", "Yes", ""],
]


def newest(pattern):
    hits = sorted(glob.glob(os.path.join(DIR, pattern)))
    if not hits:
        sys.exit(f"missing input: {pattern}")
    return hits[-1]


def main():
    src_x = newest("tabS12_deviation_log_v5_*.xlsx")
    src_c = newest("tabS12_deviation_log_v5_*.csv")
    st = datetime.now().astimezone().strftime("%Y-%m-%dT%H%M%S")
    out_x = f"{DIR}/tabS12_deviation_log_v7_{st}.xlsx"
    out_c = f"{DIR}/tabS12_deviation_log_v7_{st}.csv"
    if os.path.exists(out_x) or os.path.exists(out_c):
        sys.exit("output exists")

    wb = openpyxl.load_workbook(src_x)
    ws = wb.worksheets[0]
    last = max(r for r in range(1, ws.max_row + 1) if str(ws.cell(row=r, column=1).value) == "27")
    if OLD_27 not in ws.cell(row=last, column=2).value:
        sys.exit("entry 27 differs")
    ws.cell(row=last, column=2).value = ws.cell(row=last, column=2).value.replace(OLD_27, NEW_27)
    for r in range(1, ws.max_row + 1):
        if ws.cell(row=r, column=2).value == OLD_2:
            ws.cell(row=r, column=2).value = NEW_2
    tail = ws.max_row - last
    ws.insert_rows(last + 1, amount=len(NEW))
    for i, row in enumerate(NEW, start=1):
        for c, v in enumerate(row, start=1):
            cell = ws.cell(row=last + i, column=c, value=v)
            ref = ws.cell(row=last, column=c)
            cell.font, cell.alignment, cell.border, cell.fill = copy(ref.font), copy(ref.alignment), copy(ref.border), copy(ref.fill)
    wb.save(out_x)

    with open(src_c, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    rows = [[c.replace(OLD_27, NEW_27).replace(OLD_2, NEW_2) for c in r] for r in rows] + NEW
    with open(out_c, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)
    log = run_log.write(__file__, [src_x, src_c], [out_x, out_c], entries=len(rows) - 1, tail_rows=tail)
    print(f"written {out_x} and {out_c}; entries {len(rows) - 1}; rows after the last entry {tail}; log {log}")


if __name__ == "__main__":
    main()
