#!/usr/bin/env python3
"""49_tabS12_deviation_log_v5.py (2026-10-30)

Table S12 v5: the deviation log of v4 with entries 25 to 27 added, for the decisions of round 4 (team decisions D4
and D5 of 2026-10-30). The script reads the v4 workbook and its CSV mirror, appends the rows and writes v5 with the
same format.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/49_tabS12_deviation_log_v5.py
Outputs (never overwritten): 12_documents/supplementary/tables/tabS12_deviation_log_v5_<date-time>.xlsx and .csv;
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
NEW = [
    ["25", "Re-reading of the 808 full-text exclusions outside the blind sample that contained terms specific to "
           "susceptibility testing or could not be read as text; 57 became inclusions (8 eligible for the "
           "meta-analysis) and 14 were recorded as not retrieved",
     "To establish how many eligible reports had been excluded, after the blind sample had shown that exclusions "
     "were reversed. The dataset was rebuilt after the analysis of 28 October 2026", "Yes", "8"],
    ["26", "Susceptibility rows of the 7 reports added at the arbitration of the blind sample extracted and verified "
           "(reverses the decision of 29 October 2026 not to extract them); three of them contribute to pooled strata",
     "The dataset had to be rebuilt for entry 25, and leaving 7 comparable reports out could not be justified. "
     "ARTEMIS 2005-2007 (R04084) is a new collection; SENTRY 1997 (O17938) belongs to an existing one", "Yes", "8"],
    ["27", "Bias analysis of the 1045 full-text exclusions not re-read (rate 3 of 469 from the blind sample; "
           "1000 simulations per model and scenario; 45_qba_missed_reports_v2.R)",
     "Not prespecified; bounds the effect of the exclusions that no reviewer re-read", "Yes", ""],
]


def newest(pattern):
    hits = sorted(glob.glob(os.path.join(DIR, pattern)))
    if not hits:
        sys.exit(f"missing input: {pattern}")
    return hits[-1]


def main():
    src_x = newest("tabS12_deviation_log_v4_*.xlsx")
    src_c = newest("tabS12_deviation_log_v4_*.csv")
    st = datetime.now().astimezone().strftime("%Y-%m-%dT%H%M%S")
    out_x = f"{DIR}/tabS12_deviation_log_v5_{st}.xlsx"
    out_c = f"{DIR}/tabS12_deviation_log_v5_{st}.csv"
    if os.path.exists(out_x) or os.path.exists(out_c):
        sys.exit("output exists")

    wb = openpyxl.load_workbook(src_x)
    ws = wb.worksheets[0]
    last = max(r for r in range(1, ws.max_row + 1) if str(ws.cell(row=r, column=1).value) == "24")
    tail = [[ws.cell(row=r, column=c).value for c in range(1, 6)] for r in range(last + 1, ws.max_row + 1)]
    ws.insert_rows(last + 1, amount=len(NEW))
    for i, row in enumerate(NEW, start=1):
        for c, v in enumerate(row, start=1):
            cell = ws.cell(row=last + i, column=c, value=v)
            ref = ws.cell(row=last, column=c)
            cell.font, cell.alignment, cell.border, cell.fill = copy(ref.font), copy(ref.alignment), copy(ref.border), copy(ref.fill)
    wb.save(out_x)

    with open(src_c, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    rows.extend(NEW)
    with open(out_c, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)
    log = run_log.write(__file__, [src_x, src_c], [out_x, out_c], entries=len(rows) - 1, tail_rows=len(tail))
    print(f"written {out_x} and {out_c}; entries {len(rows) - 1}; rows after the last entry {len(tail)}; log {log}")


if __name__ == "__main__":
    main()
