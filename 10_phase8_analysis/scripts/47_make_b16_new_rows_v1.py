"""Workbook B16: proposed rows of the reports that the re-reading of workbook B15 added to the
meta-analysis (decision INCLUDE_MA), for verification against the PDF.

The rows follow the columns of workbook B11. Counts are written only when the report states them or when
they follow from its MICs and the criterion it declares (column parse says which). Rows with MICs and no
count have outcome MIC_only: they go to the MIC distributions of the second article, not to the pooled
strata. The seven reports of team decision D4 (2026-10-30) are added in a later version, once their PDFs
are available.

Outputs (08_phase6_data_extraction/verification/round4_2026-10-30/):
  r4_b16_new_rows.xlsx                  sheets instructions, reports, rows, molecular, genotypes
  47_make_b16_new_rows_v1_<ts>.json     log with counts and MD5 checksums

Usage: python3 47_make_b16_new_rows_v1.py   (from the project root)
"""
import datetime
import hashlib
import json
import os
import sys

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

B15 = "07_phase5_full_text_screening/rescreen_ast_2026-10-29/r4_b15_ast_exclusions_rescreen_v2.xlsx"
OUT_DIR = "08_phase6_data_extraction/verification/round4_2026-10-30"
OUT = f"{OUT_DIR}/r4_b16_new_rows.xlsx"

SYO = "commercial_microdilution_SYO"
BMD = "broth_microdilution_CLSI_or_unspecified"
EU = "broth_microdilution_EUCAST"

# report_id: label, source, period, identification, setting, ar20_check, flags for the reviewer
REPORTS = {
    "O06294": ("Grosset 2016", "blood (2 isolates), heart valve (1)", None, "ID32C", "CHU de Poitiers, France; case report",
               "phenotype_selected?",
               "One patient: 3 consecutive isolates with the same MLST profile, so the isolates are not independent. "
               "The report is a case of acquired resistance. Decide whether AR20 applies. The text says the day 32 "
               "isolate was resistant to azoles, but in Table 1 its fluconazole MIC is 1 and its posaconazole MIC "
               "0.125; only voriconazole (8) agrees."),
    "O10550": ("Oliveira Carvalho 2013", "blood (all 6)", None, "ITS amplification", "Sao Paulo, Brazil",
               "phenotype_selected?",
               "Isolates chosen as fluconazole resistant and susceptible for an ERG11 study: decide whether AR20 "
               "applies. Workbook B15 says different infected sites; the 6 C. tropicalis of Table 1 are all from "
               "blood. Declared cut-offs (S <=4, I 16-32, R >=64) under the EUCAST method match neither EUCAST "
               "(R >4) nor CLSI pre-2012 (S <=8): decide the regime. MIC 8 falls in no declared category."),
    "O10851": ("Sui 2026", "oral mucosa", None, "ITS sequencing", "Sanya General Hospital, China",
               "phenotype_selected?",
               "Three clinical strains used to test an essential oil, one of them chosen as drug resistant: decide "
               "whether AR20 applies. ATCC 750 is not counted. Method document M27 4th ed.; the R threshold (>64) "
               "is the one stated in the text, not that of a species-specific CLSI document."),
    "O14051": ("Contreras-Martinez 2024", "blood culture, tracheal aspirate (not separated)", None, "Vitek 2 YST",
               "Salud Social S.A.S., Sincelejo, Colombia", "",
               "No criterion and no category per isolate, so no count: all rows are MIC_only and the report adds "
               "nothing to the pooled strata. Workbook B15 records the DOI of Molecules; the PDF is the preprint."),
    "R02565": ("Caballero-Trejo 2014", "neonatal colonisation (1 tested); hands of healthcare workers (2, not tested)",
               "2008-2009", "API 20C AUX", "NICU, Hospital de Pediatria CMN Siglo XXI, Mexico City", "",
               "Workbook B15 gives n = 3, but Cuadro III covers strains from neonates and lists 1 C. tropicalis: "
               "n_tested is 1 here. Confirm that the 2 isolates from hands were not tested. Cuadro III also gives "
               "voriconazole and caspofungin, which the B15 comment omits."),
    "R03631": ("Choudhury 2018", "blood", "2014-2016", "MALDI-TOF Bruker", "Tan Tock Seng Hospital, Singapore", "",
               "Counts follow from the MIC distribution and the revised CLSI species-specific breakpoints the report "
               "declares; the report gives no categories for C. tropicalis. Each distribution sums to 27. Tables 1 "
               "and 2 give 4 azoles and 2 echinocandins; the B15 comment also lists amphotericin B, flucytosine and "
               "caspofungin, which are not in the tables. Read the MIC columns against the PDF image."),
    "R04929": ("Gill 2023", "skin lesions", None, "microscopy and biochemical tests",
               "Armed Forces hospitals, India (3 centres)", "",
               "No category for the species, so all rows are MIC_only and the report adds nothing to the pooled "
               "strata. Anidulafungin and caspofungin values come without counts. Methods cite M27-A3, Table 4 CLSI "
               "2017. Table 3 repeats C. tropicalis (5) in three clinical types; Table 4 gives 5 in total."),
    "R07987": ("Miranda-Cadena 2021", "oral candidiasis", None, "chromogenic agar, API ID 32C, PCR",
               "Dental Clinic UPV/EHU, Bilbao, Spain", "",
               "The range of fluconazole (0.5 - >64) gives the 2 values, and the geometric mean 5.7 agrees. The text "
               "does not name a C. tropicalis among the fluconazole-resistant isolates, so 1/2 follows from the MIC "
               "and EUCAST v10.0 (R >4), not from a statement of the report."),
}

# report, agent, outcome, n_tested, n_events, criterion, method, location marker, reader text, parse
ROWS = [
    ("O06294", "fluconazole", "MIC_only", 3, None, "EUCAST method; no breakpoint document named", EU, "Table 1",
     "MICs 1, 0.5, 0.5 mg/L", "text and table disagree"),
    ("O06294", "voriconazole", "R", 3, 1, "EUCAST method; no breakpoint document named", EU, "Table 1",
     "MICs 8, 0.06, 0.06 mg/L; text: day 32 isolate resistant to azoles", "category stated in the text"),
    ("O06294", "posaconazole", "MIC_only", 3, None, "EUCAST method; no breakpoint document named", EU, "Table 1",
     "MICs 0.125, 0.06, 0.03 mg/L", "text and table disagree"),
    ("O06294", "caspofungin", "R", 3, 2, "EUCAST method; no breakpoint document named", EU, "Table 1",
     "MICs 0.03, 4, 4 mg/L; text: resistant to the three echinocandins", "category stated in the text"),
    ("O06294", "micafungin", "R", 3, 2, "EUCAST method; no breakpoint document named", EU, "Table 1",
     "MICs 0.03, 0.5, 0.5 mg/L; text: resistant to the three echinocandins", "category stated in the text"),
    ("O06294", "anidulafungin", "R", 3, 2, "EUCAST method; no breakpoint document named", EU, "Table 1",
     "MICs 0.03, 0.5, 0.5 mg/L; text: resistant to the three echinocandins", "category stated in the text"),
    ("O06294", "flucytosine", "MIC_only", 3, None, "EUCAST method; no breakpoint document named", EU, "Table 1",
     "MICs 0.124, 0.124, 0.124 mg/L", "no category"),
    ("O06294", "amphotericin B", "MIC_only", 3, None, "EUCAST method; no breakpoint document named", EU, "Table 1",
     "MICs 0.125, 0.06, 0.06 mg/L", "no category"),
    ("O10550", "fluconazole", "R", 6, 1, "EUCAST method; S <=4, I 16-32, R >=64 mg/L as stated", EU, "Table 1",
     "MICs 0.5, 2, 8, 64, 0.5, 16 mg/L", "calculated from individual MICs and the declared cut-off"),
    ("O10851", "fluconazole", "R", 3, 1, "CLSI M27 4th ed.; >64 mg/L stated as resistant", BMD, "Table 1",
     "MICs 1, 2, 256 mg/L; text: strain 56 is drug resistant", "category stated in the text"),
    ("O14051", "fluconazole", "MIC_only", 7, None, "not stated", BMD, "Table 1",
     "Individual MIC90: 75.4, 8.0, 66.8, 358.3, 529.3, 428.5, 410.0", "no category"),
    ("O14051", "amphotericin B", "MIC_only", 7, None, "not stated", BMD, "Table 1",
     "Individual MIC90: 2.0, 2.1, 1.7, 2.4, 1.6, 2.5, 2.0", "no category"),
    ("O14051", "caspofungin", "MIC_only", 7, None, "not stated", BMD, "Table 1",
     "Individual MIC90: 0.5, 0.5, 0.7, 0.5, 0.5, 0.5, 0.6", "no category"),
    ("R02565", "fluconazole", "R", 1, 0, "NCCLS M27-A2; S <=8, SDD 16-32, R >=64", BMD, "Cuadro III",
     "Otras (13), which include 1 C. tropicalis: 0% resistant; all strains of other species susceptible",
     "category stated in the text"),
    ("R02565", "itraconazole", "R", 1, 0, "NCCLS M27-A2; S <=0.125, SDD 0.25-0.5, R >=1", BMD, "Cuadro III",
     "Otras (13), which include 1 C. tropicalis: 0% resistant", "category stated in the text"),
    ("R02565", "amphotericin B", "R", 1, 0, "S <=1, R >=2", BMD, "Cuadro III",
     "Otras (13), which include 1 C. tropicalis: 0% resistant", "category stated in the text"),
    ("R02565", "voriconazole", "R", 1, 0, "S <=2, R >=4", BMD, "Cuadro III",
     "Otras (13), which include 1 C. tropicalis: 0% resistant", "category stated in the text"),
    ("R02565", "caspofungin", "R", 1, 0, "no cut-off stated", BMD, "Cuadro III",
     "Otras (13), which include 1 C. tropicalis: 0% resistant", "category stated in the text"),
    ("R03631", "fluconazole", "R", 27, 4, "revised CLSI species-specific breakpoints; R >=8", SYO, "Table 1",
     "MIC 1: 7, 2: 15, 4: 1, 8: 1, 32: 1, 64: 1, 128: 1", "calculated from the MIC distribution"),
    ("R03631", "voriconazole", "R", 27, 3, "revised CLSI species-specific breakpoints; R >=1", SYO, "Table 1",
     "MIC 0.06: 4, 0.12: 8, 0.25: 11, 0.5: 1, 2: 2, 8: 1", "calculated from the MIC distribution"),
    ("R03631", "anidulafungin", "R", 27, 0, "revised CLSI species-specific breakpoints; R >=1", SYO, "Table 2",
     "MIC 0.015: 3, 0.03: 7, 0.06: 13, 0.12: 4", "calculated from the MIC distribution"),
    ("R03631", "micafungin", "R", 27, 0, "revised CLSI species-specific breakpoints; R >=1", SYO, "Table 2",
     "MIC 0.008: 1, 0.015: 8, 0.03: 17, 0.06: 1", "calculated from the MIC distribution"),
    ("R03631", "posaconazole", "MIC_only", 27, None, "no breakpoint for the agent", SYO, "Table 1",
     "MIC 0.06: 2, 0.12: 11, 0.25: 7, 0.5: 6, 8: 1", "no category"),
    ("R03631", "itraconazole", "MIC_only", 27, None, "no breakpoint for the agent", SYO, "Table 1",
     "MIC 0.06: 1, 0.12: 7, 0.25: 15, 0.5: 3, 16: 1", "no category"),
    ("R04929", "amphotericin B", "MIC_only", 5, None, "CLSI M27-A3", BMD, "Table 4", "MIC 0.25", "no category"),
    ("R04929", "itraconazole", "MIC_only", 5, None, "CLSI M27-A3", BMD, "Table 4", "MIC 0.125 (4); 0.5 (1)", "no category"),
    ("R04929", "voriconazole", "MIC_only", 5, None, "CLSI M27-A3", BMD, "Table 4", "MIC 0.0313 (1); 0.125 (4)", "no category"),
    ("R04929", "posaconazole", "MIC_only", 5, None, "CLSI M27-A3", BMD, "Table 4", "MIC 0.0313 (1); 0.5 (4)", "no category"),
    ("R04929", "anidulafungin", "MIC_only", 5, None, "CLSI M27-A3", BMD, "Table 4", "MIC 0.0625; 0.125 (no counts)", "no category"),
    ("R04929", "caspofungin", "MIC_only", 5, None, "CLSI M27-A3", BMD, "Table 4", "MIC 0.125; 0.25 (no counts)", "no category"),
    ("R07987", "fluconazole", "R", 2, 1, "EUCAST v10.0 (2020) species-specific; R >4", EU, "Table 1",
     "MIC GM 5.7, range 0.5 - >64", "calculated from the MIC range and the declared criterion"),
    ("R07987", "anidulafungin", "R", 2, 0, "EUCAST v10.0 (2020) species-specific; R >0.06", EU, "Table 1",
     "MIC GM 0.02, range 0.016-0.03", "calculated from the MIC range and the declared criterion"),
    ("R07987", "isavuconazole", "MIC_only", 2, None, "no EUCAST breakpoint, as stated", EU, "Table 1",
     "MIC 0.016", "no category"),
]

# report, gene, alteration, n_examined, n_with_alteration, method, location marker
MOLECULAR = [
    ("O06294", "FKS1", "S645P (HS1)", 3, 2, "sequencing", "Table 1"),
    ("O10550", "ERG11", "Y221Y/F", 6, 2, "sequencing", "Table 1"),
    ("O10550", "ERG11", "K344K/T", 6, 4, "sequencing", "Table 1"),
    ("O10550", "ERG11", "V362V/M", 6, 2, "sequencing", "Table 1"),
    ("O10550", "ERG11", "R371R/S", 6, 1, "sequencing", "Table 1"),
]
# report, method, n_typed, type, n_isolates, location marker
GENOTYPES = [
    ("O06294", "MLST", 3, "same allelic profile in the three isolates (MDR1 1, XYR1 1, SAPT2 3, SAPT4 1, ZWF1a 1, ICL1 1)", 3, "Table 3"),
]

ROW_COLS = ["new_row_id", "report_id", "study_label", "title", "year", "pdf_file", "compartment", "agent_raw", "agent",
            "outcome", "n_tested", "n_events", "criterion_raw", "location", "method_raw", "method", "reader_text",
            "parse", "row_action", "n_tested_v", "n_events_v", "compartment_v", "criterion_v", "method_v",
            "page_or_table", "reviewer", "date", "comment"]
REPORT_COLS = ["report_id", "study_label", "title", "year", "journal", "doi", "pdf_file", "country", "setting", "compartments",
               "n_tropicalis_b15", "source", "period", "species_id", "ar20_check", "to_check", "n_rows", "n_rows_R",
               "reviewer", "date", "ar20_decision", "comment"]
INSTRUCTIONS = [
    "Round 4, workbook B16: new rows of the reports added to the meta-analysis by the re-reading of workbook B15",
    "Each row is a proposal read from the PDF (columns location and reader_text). Column parse says whether the "
    "count is stated by the report or calculated from its MICs and declared criterion.",
    "row_action: CONFIRM if n_tested, n_events, the criterion and the compartment match the PDF; CORRECT writing only "
    "what changes in the *_v columns, and page_or_table; DISCARD if the row should not enter.",
    "outcome R: resistance by clinical breakpoint, n_events is the number of resistant isolates. outcome MIC_only: "
    "MICs without a count; these rows do not enter the pooled strata.",
    "Sheet reports: column to_check lists what needs a decision; write ar20_decision (YES or NO) where ar20_check is filled.",
]


def md5(p):
    with open(p, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def write_sheet(wb, name, cols, rows):
    ws = wb.create_sheet(name)
    ws.append(cols)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="DDE6EE")
    for r in rows:
        ws.append([r.get(c) for c in cols])
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(vertical="top", wrap_text=len(str(c.value or "")) > 40)
    ws.freeze_panes = "C2"
    for i, col in enumerate(cols, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 45 if col in (
            "reader_text", "to_check", "criterion_raw", "title", "comment") else 15


def main():
    src = openpyxl.load_workbook(B15, read_only=True)["reports"]
    it = src.iter_rows(values_only=True)
    head = next(it)
    book = {r[0]: dict(zip(head, r)) for r in it}
    ma = sorted(k for k, v in book.items() if v["decision"] == "INCLUDE_MA")
    if ma != sorted(REPORTS):
        sys.exit(f"INCLUDE_MA of B15 does not match the reports of this script: {ma}")

    rows, nid = [], 0
    for rep, agent, outcome, n, ev, crit, meth, loc, text, parse in ROWS:
        nid += 1
        b = book[rep]
        rows.append({"new_row_id": f"M{nid:04d}", "report_id": rep, "study_label": REPORTS[rep][0], "title": b["title"],
                     "year": b["year"], "pdf_file": b["pdf_file"], "compartment": "C1", "agent_raw": agent, "agent": agent,
                     "outcome": outcome, "n_tested": n, "n_events": ev, "criterion_raw": crit, "location": loc,
                     "method_raw": meth, "method": meth, "reader_text": text, "parse": parse})
    if any(r["n_events"] is not None and not 0 <= r["n_events"] <= r["n_tested"] for r in rows):
        sys.exit("A count exceeds its denominator")
    if any((r["outcome"] == "R") != (r["n_events"] is not None) for r in rows):
        sys.exit("outcome R and n_events do not agree")

    reports = []
    for rep, (label, source, period, sid, setting, ar20, flag) in REPORTS.items():
        b = book[rep]
        own = [r for r in rows if r["report_id"] == rep]
        reports.append({"report_id": rep, "study_label": label, "title": b["title"], "year": b["year"], "journal": b["journal"],
                        "doi": b["doi"], "pdf_file": b["pdf_file"], "country": b["country"], "setting": setting,
                        "compartments": b["compartments"], "n_tropicalis_b15": b["n_tropicalis"], "source": source,
                        "period": period, "species_id": sid, "ar20_check": ar20, "to_check": flag, "n_rows": len(own),
                        "n_rows_R": sum(r["outcome"] == "R" for r in own)})

    os.makedirs(OUT_DIR, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "instructions"
    for line in INSTRUCTIONS:
        ws.append([line])
    ws["A1"].font = Font(bold=True)
    ws.column_dimensions["A"].width = 130
    for row in ws.iter_rows():
        row[0].alignment = Alignment(wrap_text=True, vertical="top")
    write_sheet(wb, "reports", REPORT_COLS, reports)
    write_sheet(wb, "rows", ROW_COLS, rows)
    write_sheet(wb, "molecular", ["report_id", "gene", "alteration", "n_examined", "n_with_alteration", "method", "location",
                                  "row_action", "reviewer", "date", "comment"],
                [dict(zip(["report_id", "gene", "alteration", "n_examined", "n_with_alteration", "method", "location"], m))
                 for m in MOLECULAR])
    write_sheet(wb, "genotypes", ["report_id", "method", "n_typed", "type", "n_isolates", "location", "row_action", "reviewer",
                                  "date", "comment"],
                [dict(zip(["report_id", "method", "n_typed", "type", "n_isolates", "location"], g)) for g in GENOTYPES])
    wb.save(OUT)

    now = datetime.datetime.now()
    log = {"script": os.path.basename(__file__), "run_time": now.isoformat(timespec="seconds"),
           "proposed_by": {"model": "claude-opus-5-5", "client": "Claude Code 2.1.314", "date": now.date().isoformat(),
                           "instruction": "12_documents/supplementary/file_s1_language_model_v1/full_text/data_extraction_instruction_EN.md"},
           "inputs": {B15: md5(B15)}, "outputs": {OUT: md5(OUT)},
           "counts": {"reports": len(reports), "rows": len(rows), "rows_R": sum(r["outcome"] == "R" for r in rows),
                      "rows_MIC_only": sum(r["outcome"] == "MIC_only" for r in rows), "molecular": len(MOLECULAR),
                      "genotypes": len(GENOTYPES)},
           "verified": False}
    with open(f"{OUT_DIR}/47_make_b16_new_rows_v1_{now:%Y-%m-%dT%H%M%S}.json", "w") as f:
        json.dump(log, f, indent=1, ensure_ascii=False)
    print(json.dumps(log["counts"]))
    print({r["report_id"]: (r["n_rows"], r["n_rows_R"]) for r in reports})


if __name__ == "__main__":
    main()
