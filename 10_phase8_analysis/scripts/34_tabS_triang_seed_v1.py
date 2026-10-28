"""Supplementary Tables S13 (triangulation with repository data) and S14 (seed-set check).

Reads the newest outputs of 32_triang_analysis_v1.py and 33_seed_set_check_v1.py and writes, for each table,
a CSV with the main block and an XLSX with one sheet per block.
Usage: python 34_tabS_triang_seed_v1.py   (from the project root)
"""
import csv, glob, os, datetime
import openpyxl
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_log  # noqa: E402
from openpyxl.styles import Font, Alignment

OUT = "12_documents/supplementary/tables"
RES = "10_phase8_analysis/results"
NAMES = {"C1": "C1 Human host", "C2": "C2 Animal host", "C3": "C3 Agroecosystem", "C4": "C4 Healthcare environment",
         "C5": "C5 Natural environment (broad reading)", "C6": "C6 Anthropogenic matrix", "not_allocated": "Not allocated"}

def newest(p):
    f = sorted(glob.glob(os.path.join(RES, p)))
    assert f, p
    return f[-1]

def rd(p):
    return list(csv.reader(open(p, encoding="utf-8")))

def num(x):
    try:
        return int(x)
    except ValueError:
        try:
            return float(x)
        except ValueError:
            return x

def book(path, sheets):
    wb = openpyxl.Workbook(); wb.remove(wb.active)
    for title, rows in sheets:
        ws = wb.create_sheet(title[:31])
        for r in rows:
            ws.append([num(x) for x in r])
        for c in ws[1]:
            c.font = Font(bold=True)
        for col in ws.columns:
            w = min(70, max(len(str(c.value or "")) for c in col) + 2)
            ws.column_dimensions[col[0].column_letter].width = w
            for c in col:
                c.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(path)

def main():
    st = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S")
    dist = rd(newest("triangulation/triang_distribution_v1_*.csv"))
    res = rd(newest("triangulation/triang_resistance_pubmlst_v1_*.csv"))
    dic = rd(newest("triangulation/triang_ncbi_source_dictionary_v1_*.csv"))
    h = ["Repository", "Compartment", "Isolates, n", "Isolates, % of allocated", "Submissions, n",
         "Submissions, % of allocated", "Isolates in the largest submission, n", "Largest submission, % of the compartment"]
    d = [h] + [[r[0], NAMES[r[1]]] + r[2:] for r in dist[1:]]
    rh = ["Repository", "Compartment", "Agent", "Resistance criterion", "Subset", "Resistant, n", "Classified, n",
          "Unclassifiable MIC, n", "Senders, n", "Resistant, %", "95% CI lower", "95% CI upper"]
    rr = [rh] + [[r[0], NAMES[r[1]]] + r[2:] for r in res[1:]]
    dh = ["Isolation source", "Host", "Environment", "Sample type", "Title (only when no source field)", "Assignment",
          "Rule", "BioSamples, n"]
    dd = [dh] + [r[:5] + [NAMES.get(r[5], "Excluded: laboratory-derived sample" if r[5] == "excluded_laboratory" else r[5])]
                 + r[6:] for r in dic[1:]]
    p13 = os.path.join(OUT, f"tabS13_repository_triangulation_v1_{st}")
    with open(p13 + ".csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(d + [[]] + rr)
    book(p13 + ".xlsx", [("Distribution", d), ("PubMLST resistance", rr), ("NCBI source dictionary", dd)])
    seed_src = rd(newest("seed_set/seed_set_by_source_v1_*.csv"))
    seed = rd(newest("seed_set/seed_set_recovery_v1_*.csv"))
    sh = [["Source", "Seed studies recovered, n", "Seed studies, n", "Recovered, %"]] + seed_src[1:]
    p14 = os.path.join(OUT, f"tabS14_seed_set_check_v1_{st}")
    with open(p14 + ".csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(sh)
    book(p14 + ".xlsx", [("By source", sh), ("Seed studies", seed)])
    ins = [newest(p) for p in ("triangulation/triang_distribution_v1_*.csv", "triangulation/triang_resistance_pubmlst_v1_*.csv",
                               "triangulation/triang_ncbi_source_dictionary_v1_*.csv", "seed_set/seed_set_by_source_v1_*.csv",
                               "seed_set/seed_set_recovery_v1_*.csv")]
    print(run_log.write(__file__, ins, [p13 + ".csv", p13 + ".xlsx", p14 + ".csv", p14 + ".xlsx"]))
    print(p13, p14, sep="\n")

if __name__ == "__main__":
    main()
