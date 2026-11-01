#!/usr/bin/env python3
"""68_tabS13_S14_v2.py (2026-10-31)

Tables S13 and S14 v2 from their v1 files. Table S13 adds a Summary sheet with the repository figures cited in Section 3.2,
read from the triangulation log; Table S14 drops the Wanfang_Data row, whose folder held a copy of the VIP export.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/68_tabS13_S14_v2.py [--check]
With --check it only compares the cells with the v2 files in the folder. Outputs: tabS13_repository_triangulation_v2_<date-time>
and tabS14_seed_set_check_v2_<date-time>, .xlsx and .csv.
"""
import csv
import glob
import os
import re
import sys
import tempfile
from datetime import datetime

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_log  # noqa: E402

T = "12_documents/supplementary/tables/"
LOG = "10_phase8_analysis/results/triangulation/triang_log_v1_2026-10-27T182709.txt"


def summary():
    t = open(LOG, encoding="utf-8").read()
    p = re.search(r"PubMLST: (\d+) isolates, (\d+) countries, years (\d+)-(\d+), (\d+) senders", t)
    asia = int(re.search(r"'Asia': (\d+)", t).group(1))
    allocated = sum(int(x) for x in re.search(r"anat_source \{(.*?)\}", t).group(1).replace("None: 455", "").split(": ")[1:] and re.findall(r": (\d+)", re.search(r"anat_source \{(.*?)\}", t).group(1).replace("None: 455", "")))
    n = re.search(r"NCBI: (\d+) BioSamples, (\d+) laboratory-derived excluded, (\d+) remaining, (\d+) isolates after collapsing by BioProject and strain, (\d+) submissions", t)
    china = int(re.search(r"\('China', (\d+)\)", t).group(1))
    iso = int(n.group(4))
    return [["Repository", "Quantity", "Value"],
            ["PubMLST", "Isolates", int(p.group(1))], ["PubMLST", "Submitters", int(p.group(5))], ["PubMLST", "Countries", int(p.group(2))],
            ["PubMLST", "Isolates from Asia, n", asia], ["PubMLST", "Isolates from Asia, %", round(100 * asia / int(p.group(1)), 1)],
            ["PubMLST", "Isolates with the anatomical source recorded", allocated],
            ["NCBI BioSample", "BioSamples", int(n.group(1))], ["NCBI BioSample", "Laboratory-derived samples excluded", int(n.group(2))],
            ["NCBI BioSample", "Isolates after collapsing by BioProject and strain", iso], ["NCBI BioSample", "Submissions", int(n.group(5))],
            ["NCBI BioSample", "Isolates from China, n", china], ["NCBI BioSample", "Isolates from China, %", round(100 * china / iso, 1)]]


def build(folder, st):
    s13 = sorted(glob.glob(T + "tabS13_repository_triangulation_v1_*.xlsx"))[-1]
    wb = openpyxl.load_workbook(s13)
    ws = wb.create_sheet("Summary", 0)
    rows = summary()
    for r in rows:
        ws.append(r)
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 18, 54
    out13 = f"{folder}tabS13_repository_triangulation_v2_{st}"
    wb.save(out13 + ".xlsx")
    with open(out13 + ".csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerows(rows)
        w.writerow([])
        w.writerows(csv.reader(open(s13.replace(".xlsx", ".csv"), encoding="utf-8-sig", newline="")))
    s14 = sorted(glob.glob(T + "tabS14_seed_set_check_v1_*.xlsx"))[-1]
    wb = openpyxl.load_workbook(s14)
    ws = wb.worksheets[0]
    hit = [r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=1).value == "Wanfang_Data"]
    if len(hit) != 1:
        sys.exit("Wanfang row of Table S14")
    ws.delete_rows(hit[0])
    out14 = f"{folder}tabS14_seed_set_check_v2_{st}"
    wb.save(out14 + ".xlsx")
    c = list(csv.reader(open(s14.replace(".xlsx", ".csv"), encoding="utf-8-sig", newline="")))
    with open(out14 + ".csv", "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows([r for r in c if not (r and r[0] == "Wanfang_Data")])
    return s13, s14, out13, out14


def cells(p):
    wb = openpyxl.load_workbook(p, data_only=True)
    return [[[c for c in r] for r in ws.iter_rows(values_only=True)] for ws in wb]


def main():
    st = datetime.now().astimezone().strftime("%Y-%m-%dT%H%M%S")
    if "--check" in sys.argv:
        tmp = tempfile.mkdtemp() + "/"
        _, _, a, b = build(tmp, st)
        for new, pat in ((a, "tabS13_repository_triangulation_v2_*.xlsx"), (b, "tabS14_seed_set_check_v2_*.xlsx")):
            cur = sorted(glob.glob(T + pat))[-1]
            print(os.path.basename(cur), "same cells:", cells(new + ".xlsx") == cells(cur), "csv same:", open(new + ".csv", "rb").read() == open(cur.replace(".xlsx", ".csv"), "rb").read())
        return
    s13, s14, a, b = build(T, st)
    print(run_log.write(__file__, [s13, s14, LOG], [a + ".xlsx", a + ".csv", b + ".xlsx", b + ".csv"]))


if __name__ == "__main__":
    main()
