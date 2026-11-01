"""Workbook B15: human re-reading of the full-text exclusions that were not in the blind sample (B08)
and whose full text reports antifungal susceptibility data.

Filter: a term specific to susceptibility testing anywhere in the full text (MIC, CLSI, NCCLS, EUCAST,
M27/M44/M59/M60, Etest, Sensititre, YeastOne, ATB Fungus, Vitek AST, disk diffusion, breakpoint, ECV,
ECOFF, SDD and their Chinese equivalents), or a text layer too short to be screened (< 2000 characters).
The sensitivity of the filter is measured on the reports eligible for the meta-analysis of the final dataset.

Outputs (07_phase5_full_text_screening/rescreen_ast_2026-10-29/):
  r4_b15_ast_exclusions_rescreen.xlsx   workbook for the reviewer, without the model's decision
  r4_b15_key.csv                         model's reason, evidence and notes (not shown to the reviewer)
  pdfs/                                  copies of the PDFs to be read
  make_rescreen_ast_book_v1_<ts>.json    log with counts, filter sensitivity and MD5 checksums

Usage: python3 make_rescreen_ast_book_v1.py   (from the project root)
"""
import hashlib, json, os, re, shutil, subprocess, sys
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

PDF_DIR = os.path.expanduser("~/EXTENCIONES/ARTICULO_COMPLETO/articulos_pdf")
FT = "07_phase5_full_text_screening/full_text_screening.xlsx"
B08_KEY = "08_phase6_data_extraction/verification/round2_2026-10-24/r2_b08_key.csv"
DATASET = "10_phase8_analysis/data/analysis_dataset_v3_2026-10-28T193035/studies.csv"
OUT = "07_phase5_full_text_screening/rescreen_ast_2026-10-29"

AST_SPECIFIC = (r"\bMICs?\b|minimum inhibitory|minimal inhibitory|\bCLSI\b|\bNCCLS\b|\bEUCAST\b|\bM27\b|\bM44\b|\bM60\b|\bM59\b"
                r"|E-?test|Sensititre|Vitek[ -]?2?\s*AST|AST-YS|ATB Fungus|YeastOne|disk diffusion|disc diffusion"
                r"|breakpoints?|\bECVs?\b|ECOFF|epidemiological cut|susceptible dose|\bSDD\b|药敏|耐药|最低抑菌")
TROP = r"tropicalis"
MIN_CHARS = 2000
DECISIONS = ["EXCLUSION_CONFIRMED", "INCLUDE_SQ1", "INCLUDE_MA", "NOT_RETRIEVED"]
EC_CODES = [f"EC{i}" for i in range(1, 14) if i != 5]  # EC5 is a classification rule towards C6, not an exclusion


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def text_of(pdf):
    r = subprocess.run(["pdftotext", "-q", "-layout", os.path.join(PDF_DIR, pdf), "-"], capture_output=True)
    return re.sub(r"\s+", " ", ILLEGAL_CHARACTERS_RE.sub(" ", r.stdout.decode("utf-8", errors="ignore")))


def screen(flat):
    """Specific susceptibility terms found and up to three quotes, those closest to a mention of the species first."""
    hits = list(re.finditer(AST_SPECIFIC, flat, re.I))
    trop = [m.start() for m in re.finditer(TROP, flat, re.I)]
    dist = lambda m: min((abs(m.start() - t) for t in trop), default=10 ** 9)
    quotes, used = [], []
    for m in sorted(hits, key=dist):
        if any(abs(m.start() - u) < 400 for u in used):
            continue
        used.append(m.start())
        quotes.append(flat[max(0, m.start() - 200): m.end() + 200])
        if len(quotes) == 3:
            break
    return sorted({m.group(0).lower() for m in hits}), quotes


def main():
    ts = datetime.now().astimezone().strftime("%Y-%m-%dT%H%M%S")
    ft = pd.read_excel(FT, sheet_name="All", dtype=str)
    key08 = pd.read_csv(B08_KEY, dtype=str)
    excl = ft[(ft.Decision == "EXCLUDE") & ~ft.ID.isin(key08.study_id)].copy()

    # filter on the unsampled exclusions
    rows = []
    for _, r in excl.iterrows():
        flat = text_of(r["PDF file"])
        terms, quotes = screen(flat)
        rows.append(dict(study_id=r.ID, chars=len(flat), terms=terms, quotes=quotes,
                         unreadable=len(flat) < MIN_CHARS))
    f = pd.DataFrame(rows).set_index("study_id")
    f["selected"] = f.unreadable | (f.terms.str.len() > 0)

    # sensitivity on the reports eligible for the meta-analysis
    st = pd.read_csv(DATASET, dtype=str)
    st["nonhuman"] = st.compartments.fillna("").str.contains("C[2-6]")
    val = st[st.eligible_ma_v3 == "YES"].dropna(subset=["pdf_file"])
    val = val[val.pdf_file.apply(lambda p: os.path.exists(os.path.join(PDF_DIR, p)))]
    caught = val.pdf_file.apply(lambda p: (lambda t: len(t) < MIN_CHARS or bool(re.search(AST_SPECIFIC, t, re.I)))(text_of(p)))
    missed = sorted(val.study_id[~caught])

    # workbook
    sel = excl[excl.ID.isin(f.index[f.selected])].sort_values("ID")
    os.makedirs(os.path.join(OUT, "pdfs"), exist_ok=True)
    for p in sel["PDF file"]:
        dst = os.path.join(OUT, "pdfs", p)
        if not os.path.exists(dst):
            shutil.copy2(os.path.join(PDF_DIR, p), dst)

    wb = Workbook()
    ins = wb.active
    ins.title = "instructions"
    for line in [
        "Round 4, workbook B15: full-text exclusions with susceptibility data",
        f"Workbook B15. {len(sel)} reports that the language model excluded at full-text screening, that were not part of the blind sample (B08), and whose full text contains a term specific to antifungal susceptibility testing (MIC, CLSI, EUCAST, breakpoint, Etest, ECV and similar) or could not be read as text.",
        "Fill the yellow columns of the sheet reports. Read each report in the folder pdfs/ (link in column pdf_file) applying the frozen screening manual and the inclusion rules in force (including rule I1: a study with isolates assignable to a compartment enters the distribution analysis even without susceptibility testing). The model's decision and reasons are not shown, so that the reading is independent.",
        "The quotes are only aids to find the susceptibility data; they were selected automatically and may refer to other species. pdf_text_layer NO means the PDF is scanned and has no text to search: read it directly.",
        "has_ast_tropicalis: YES if the report gives susceptibility results for C. tropicalis isolates (MIC, categories or counts), NO otherwise.",
        "decision: EXCLUSION_CONFIRMED (with ec_code), INCLUDE_SQ1 (enters the distribution analysis only), INCLUDE_MA (has rows that could enter the meta-analysis), NOT_RETRIEVED (the PDF is another work, truncated or unreadable).",
        "For INCLUDE_SQ1 and INCLUDE_MA fill compartments, n_tropicalis and country; for INCLUDE_MA describe in comment the agents, method, interpretive criterion and page or table of the data.",
        "reviewer: your reviewer code; date: date of the reading (YYYY-MM-DD).",
    ]:
        ins.append([line])
    ins.column_dimensions["A"].width = 160
    for c in ins["A"]:
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ins["A1"].font = Font(bold=True)

    ws = wb.create_sheet("reports", 0)
    wb.active = 0
    # columns to fill come right after the identifiers; reading aids and the record follow
    fill = ["has_ast_tropicalis", "decision", "ec_code", "compartments", "n_tropicalis", "country",
            "reviewer", "date", "comment"]
    cols = ["study_id", "pdf_file"] + fill + ["pdf_text_layer", "susceptibility_terms", "quote_1", "quote_2", "quote_3",
                                              "title", "year", "journal", "doi"]
    ws.append(cols)
    for _, r in sel.iterrows():
        g = f.loc[r.ID]
        q = list(g.quotes) + [""] * 3
        ws.append([r.ID, r["PDF file"]] + [None] * len(fill)
                  + ["NO (scanned, read the PDF)" if g.unreadable else "YES", "; ".join(g.terms), q[0], q[1], q[2],
                     r.Title, r.Year, r.Journal, r.DOI])
    head = PatternFill("solid", fgColor="DDEBF7")
    todo = PatternFill("solid", fgColor="FFF2CC")
    widths = dict(study_id=10, pdf_file=28, has_ast_tropicalis=12, decision=24, ec_code=10, compartments=14,
                  n_tropicalis=12, country=14, reviewer=12, date=12, comment=45, pdf_text_layer=14,
                  susceptibility_terms=22, quote_1=55, quote_2=55, quote_3=55, title=50, year=7, journal=25, doi=24)
    wrap = Alignment(wrap_text=True, vertical="top")
    for j, name in enumerate(cols, 1):
        letter = ws.cell(1, j).column_letter
        ws.column_dimensions[letter].width = widths[name]
        h = ws.cell(1, j)
        h.font = Font(bold=True)
        h.fill = todo if name in fill else head
        h.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        for i in range(2, ws.max_row + 1):
            c = ws.cell(i, j)
            c.alignment = wrap  # wrapped text never spills over the cells to fill
            if name in fill:
                c.fill = todo
    for i in range(2, ws.max_row + 1):
        ws.row_dimensions[i].height = 90
        c = ws.cell(i, 2)
        c.hyperlink = f"pdfs/{c.value}"
        c.font = Font(color="0563C1", underline="single")
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = ws.dimensions
    n = ws.max_row
    letter = {name: ws.cell(1, j).column_letter for j, name in enumerate(cols, 1)}
    for name, values in (("has_ast_tropicalis", ["YES", "NO"]), ("decision", DECISIONS), ("ec_code", EC_CODES)):
        dv = DataValidation(type="list", formula1='"' + ",".join(values) + '"', allow_blank=True)
        dv.add(f"{letter[name]}2:{letter[name]}{n}")
        ws.add_data_validation(dv)
    book = os.path.join(OUT, "r4_b15_ast_exclusions_rescreen.xlsx")
    wb.save(book)

    key = sel[["ID", "Main reason", "Exclusions", "Evidence", "Notes"]].rename(
        columns={"ID": "study_id", "Main reason": "model_reason", "Exclusions": "model_exclusions",
                 "Evidence": "model_evidence", "Notes": "model_notes"})
    key_path = os.path.join(OUT, "r4_b15_key.csv")
    key.to_csv(key_path, index=False)

    log = dict(
        script="make_rescreen_ast_book_v1.py", run_time=ts,
        unsampled_exclusions=len(excl), unreadable=int(f.unreadable.sum()),
        with_specific_terms=int((f.terms.str.len() > 0).sum()), selected=int(f.selected.sum()),
        selected_by_model_reason=sel["Main reason"].str.extract(r"(EC\d+)")[0].fillna("other").value_counts().to_dict(),
        filter_sensitivity=dict(reports_eligible_ma_with_pdf=len(val), caught=int(caught.sum()),
                                sensitivity=round(float(caught.mean()), 4), missed=missed,
                                nonhuman_caught=int(caught[val.nonhuman].sum()), nonhuman=int(val.nonhuman.sum())),
        inputs={p: md5(p) for p in (FT, B08_KEY, DATASET)},
        outputs={os.path.basename(p): md5(p) for p in (book, key_path)},
        pdfs_copied=len(sel),
    )
    with open(os.path.join(OUT, f"make_rescreen_ast_book_v1_{ts}.json"), "w") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in log.items() if k not in ("inputs", "outputs")}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
