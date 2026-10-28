#!/usr/bin/env python3
"""make_rob_calibration_books.py

Calibration workbooks CAL-RB1 for the extraction of the risk-of-bias fields that the
dictionary marks 'not extracted' (manual rob_manual_v2_2026-10-21.md, section 7, step 1).
One workbook per reviewer, same row order, draw with a fixed seed. Reviewers work
blinded: the workbooks are identical except for the reviewer's name.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 09_phase7_risk_of_bias/make_rob_calibration_books.py
Outputs (never overwritten):
  09_phase7_risk_of_bias/rob_cal1_<reviewer>_<date-time>.xlsx
  09_phase7_risk_of_bias/rob_cal1_sample_<date-time>.csv
  09_phase7_risk_of_bias/logs/make_rob_calibration_books_<date-time>.json
"""
import csv, hashlib, json, os, platform, random, re, sys
from datetime import datetime

import openpyxl
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

STUDIES = "10_phase8_analysis/data/analysis_dataset_v1_2026-10-20/studies.csv"
PDFLIST = "07_phase5_full_text_screening/pdf_md5_n5939_2026-10-20.txt"
MANUAL = "09_phase7_risk_of_bias/rob_manual_v2_2026-10-21.md"
OUT_DIR = "09_phase7_risk_of_bias"
LOG_DIR = os.path.join(OUT_DIR, "logs")

SEED = 21102026          # seed of the draw; recorded in the log and in the CSV of the sample
N_CAL = 200              # size of the calibration, manual v2 section 7
REVIEWERS = ["reviewer_1", "reviewer_2"]
PDF_ROOT = "~/EXTENCIONES/ARTICULO_COMPLETO/articulos_pdf"

DEDUP = ["by_patient", "by_host_or_site", "by_sampling_point",
         "declared_unspecified", "repeated_included", "not_declared",
         "single_sampling", "not_retrievable"]
EDITORIAL = ["peer_reviewed", "preprint", "grey"]
C5DEF = ["strict", "broad", "not_applicable"]
AGRO = ["documented_present", "documented_absent", "not_evaluated"]
YESNO = ["YES", "NO"]

# (header, width, validation list or None, to_be_filled)
COLS = [
    ("n", 5, None, False),
    ("report_id", 11, None, False),
    ("study_label", 30, None, False),
    ("year", 7, None, False),
    ("journal", 26, None, False),
    ("doi", 24, None, False),
    ("country", 16, None, False),
    ("compartments", 13, None, False),
    ("design", 17, None, False),
    ("pdf_file", 42, None, False),
    ("dedup_rule", 23, DEDUP, True),
    ("dedup_quote", 52, None, True),
    ("dedup_page", 11, None, True),
    ("methods_read", 13, YESNO, True),
    ("editorial_status", 16, EDITORIAL, True),
    ("site_applies", 11, None, False),
    ("c5_definition", 15, C5DEF, True),
    ("agronomic_management", 20, AGRO, True),
    ("agro_quote", 44, None, True),
    ("agro_page", 11, None, True),
    ("comments", 40, None, True),
]

INSTRUCTIONS = [
    "CAL-RB1. Calibration of the extraction of risk-of-bias fields",
    "",
    "Full manual: 09_phase7_risk_of_bias/rob_manual_v2_2026-10-21.md. This sheet summarises; the manual prevails.",
    "",
    "1. Work alone, without consulting the other reviewer. Both workbooks carry the same rows in the same order.",
    "2. Open the PDF named in the column pdf_file, in " + PDF_ROOT,
    "3. dedup_rule: look in Methods (design, setting, isolates, collection), then in the first",
    "   sentence of Results that gives the numbers, then in the footnote of the first table.",
    "4. Every value other than not_declared requires a literal quote and page. Without a quote the value is not recorded.",
    "5. not_declared requires having read the whole Methods section: set methods_read = YES.",
    "6. Doubt is not forced: not_retrievable exists and is used.",
    "",
    "The five traps. None counts as a declared deduplication:",
    "  a. 'Consecutive isolates' is consecutive in time, not one per unit. It is the most frequent error.",
    "  b. 'Repeated samples' in the case definition requires repetition, it does not remove it.",
    "  c. 'Unique isolates' without saying unique with respect to what: if it is not known, not_retrievable.",
    "  d. Rule declared for identification but not for susceptibility: not_retrievable.",
    "  e. Multicentre study where one centre applies the rule and nothing is said of the rest: not_retrievable.",
    "",
    "repeated_included also applies when the report gives n isolates and n patients, they differ,",
    "and there is no deduplication rule. The quote is that sentence with the numbers.",
    "",
    "site_applies = NO: leave c5_definition, agronomic_management, agro_quote and agro_page empty.",
    "site_applies = YES: strict can only be marked if agronomic_management is documented_absent.",
    "",
    "editorial_status is resolved with the bibliographic record and does not require opening the PDF.",
]


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_studies():
    with open(STUDIES, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    elig = [r for r in rows if (r.get("eligible_ma") or "").strip() == "YES"]
    if not elig:
        sys.exit("There are no studies with eligible_ma = YES")
    return elig


def load_pdfs():
    pdfs = {}
    with open(PDFLIST, encoding="utf-8", errors="replace") as f:
        for ln in f:
            parts = ln.rstrip("\n").split("  ", 1)
            if len(parts) != 2:
                continue
            m = re.search(r"_([OR]\d{4,6})_", parts[1])
            if m:
                pdfs.setdefault(m.group(1), parts[1])
    return pdfs


def book(path, reviewer, sample, stamp):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Instructions"
    ws.column_dimensions["A"].width = 110
    ws["A1"] = f"Reviewer: {reviewer}    Seed: {SEED}    Generated: {stamp}"
    ws["A1"].font = Font(bold=True)
    for i, line in enumerate(INSTRUCTIONS, start=3):
        ws.cell(i, 1, line).alignment = Alignment(wrap_text=False)

    vs = wb.create_sheet("Values")
    for j, (name, vals) in enumerate([("dedup_rule", DEDUP), ("methods_read", YESNO),
                                      ("editorial_status", EDITORIAL), ("c5_definition", C5DEF),
                                      ("agronomic_management", AGRO)], start=1):
        vs.cell(1, j, name).font = Font(bold=True)
        for i, v in enumerate(vals, start=2):
            vs.cell(i, j, v)
        vs.column_dimensions[get_column_letter(j)].width = 24
    val_col = {"dedup_rule": 1, "methods_read": 2, "editorial_status": 3,
               "c5_definition": 4, "agronomic_management": 5}
    vals_of = {"dedup_rule": DEDUP, "methods_read": YESNO, "editorial_status": EDITORIAL,
               "c5_definition": C5DEF, "agronomic_management": AGRO}

    ex = wb.create_sheet("Extraction")
    for j, (name, width, _, _) in enumerate(COLS, start=1):
        c = ex.cell(1, j, name)
        c.font = Font(bold=True)
        c.alignment = Alignment(vertical="top")
        ex.column_dimensions[get_column_letter(j)].width = width
    for i, r in enumerate(sample, start=2):
        for j, (name, _, _, _) in enumerate(COLS, start=1):
            v = r.get(name, "")
            ex.cell(i, j, v).alignment = Alignment(vertical="top", wrap_text=(name.endswith("quote")))
    last = len(sample) + 1
    for name, vcol in val_col.items():
        j = [k for k, (n, _, _, _) in enumerate(COLS, start=1) if n == name][0]
        L = get_column_letter(vcol)
        src = f"Values!${L}$2:${L}${1 + len(vals_of[name])}"
        dv = DataValidation(type="list", formula1=src, allow_blank=True, showDropDown=False)
        dv.error = f"Value outside the allowed list for {name}"
        dv.errorTitle = "Value not allowed"
        ex.add_data_validation(dv)
        dv.add(f"{get_column_letter(j)}2:{get_column_letter(j)}{last}")
    ex.freeze_panes = "C2"
    wb.save(path)


def main():
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    for f in (STUDIES, PDFLIST, MANUAL):
        if not os.path.exists(f):
            sys.exit(f"Missing {f}")

    studies = load_studies()
    pdfs = load_pdfs()
    faltan = [r["study_id"] for r in studies if r["study_id"] not in pdfs]
    if faltan:
        sys.exit(f"{len(faltan)} eligible without a PDF in the listing, e.g. {faltan[:5]}")

    studies.sort(key=lambda r: r["study_id"])          # stable order before drawing
    by_id = {r["study_id"]: r for r in studies}

    # Stratified sample. The reports that sample C3 or C5 are 11 in 1,104, so a
    # simple draw would bring none and the calibration would not exercise c5_definition or
    # agronomic_management. All 11 enter and the rest are drawn.
    def site(r):
        c = r.get("compartments") or ""
        return "C3" in c or "C5" in c
    site_fields = [r["study_id"] for r in studies if site(r)]
    rest = [r["study_id"] for r in studies if not site(r)]
    if len(site_fields) > N_CAL:
        sys.exit(f"Hay {len(site_fields)} reports of C3 or C5, more than the calibration size")
    rnd = random.Random(SEED)
    sample_ids = site_fields + rnd.sample(rest, N_CAL - len(site_fields))
    rnd.shuffle(sample_ids)                            # the reading order is also drawn

    sample = []
    for n, sid in enumerate(sample_ids, start=1):
        r = by_id[sid]
        comp = r.get("compartments") or ""
        sample.append({
            "n": n, "report_id": sid, "study_label": r.get("study_label") or "",
            "year": r.get("year") or "", "journal": r.get("journal") or "",
            "doi": r.get("doi") or "", "country": r.get("country") or "",
            "compartments": comp, "design": r.get("design") or "",
            "pdf_file": pdfs[sid],
            "site_applies": "YES" if ("C3" in comp or "C5" in comp) else "NO",
        })

    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    paths = [os.path.join(OUT_DIR, f"rob_cal1_{rev}_{stamp}.xlsx") for rev in REVIEWERS]
    key = os.path.join(OUT_DIR, f"rob_cal1_sample_{stamp}.csv")
    for p in paths + [key]:
        if os.path.exists(p):
            sys.exit(f"Already exists {p}: not overwritten")

    for rev, p in zip(REVIEWERS, paths):
        book(p, rev, sample, stamp)
    with open(key, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n", "report_id", "site_applies", "pdf_file"])
        for r in sample:
            w.writerow([r["n"], r["report_id"], r["site_applies"], r["pdf_file"]])

    order = hashlib.md5(",".join(sample_ids).encode()).hexdigest()
    log = {"script": os.path.basename(__file__),
           "run_time": datetime.now().astimezone().isoformat(timespec="seconds"),
           "python": platform.python_version(), "openpyxl": openpyxl.__version__,
           "seed": SEED, "n_calibration": N_CAL, "reviewers": REVIEWERS,
           "eligible_total": len(studies), "order_md5": order,
           "site_fields_apply": sum(1 for r in sample if r["site_applies"] == "YES"),
           "inputs": {p: md5(p) for p in (STUDIES, PDFLIST, MANUAL)},
           "outputs": {os.path.basename(p): md5(p) for p in paths + [key]}}
    log_path = os.path.join(LOG_DIR, f"make_rob_calibration_books_{stamp}.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=1, ensure_ascii=False)

    print(f"CAL-RB1: {N_CAL} reports drawn with seed {SEED}, "
          f"{log['site_fields_apply']} with site fields")
    print("Row order (md5):", order)
    for p in paths:
        print("Workbook:", p)
    print("Sample:", key)
    print("Log:", log_path)


if __name__ == "__main__":
    main()
