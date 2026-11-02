#!/usr/bin/env python3
"""71_lab_coding_freeze_v1.py (2026-11-02)

Freezes the laboratory coding of the non-human collections from the review sheet of script 70: team_laboratory when filled,
proposed_laboratory otherwise.

Usage, from the project root:
  python3 10_phase8_analysis/scripts/71_lab_coding_freeze_v1.py
Output: 10_phase8_analysis/data/lookups/lab_coding_v1.csv
"""
import csv
import glob

from openpyxl import load_workbook

OUT = "10_phase8_analysis/data/lookups/lab_coding_v1.csv"
src = sorted(glob.glob("10_phase8_analysis/results/lab_recoding_review_v1_*.xlsx"))[-1]
ws = load_workbook(src, read_only=True)["Collections"]
it = ws.iter_rows(values_only=True)
h = list(next(it))
rows = [dict(zip(h, r)) for r in it if r[1]]
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["study_id", "report", "laboratory"])
    for r in rows:
        w.writerow([r["study_id"], r["report"], r["team_laboratory"] or r["proposed_laboratory"]])
print(src, len(rows), len({(r["team_laboratory"] or r["proposed_laboratory"]) for r in rows}))
