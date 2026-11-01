"""Workbook B16, version 2: adds the rows of the seven reports of team decision D4 (2026-10-30) to the rows of
47_make_b16_new_rows_v1.py and records the row check requested by the team.

Every number of reader_text is searched in the text layer of the PDF of the report; O13199 has its tables in an
image and was read from it. Column reviewer holds the identifier of the language model, because that is who made
this check: a person has to confirm the rows before the text of the manuscript can call them verified by the
reviewers. Workbook r4_b16_new_rows.xlsx is kept unchanged.

Outputs (08_phase6_data_extraction/verification/round4_2026-10-30/):
  r4_b16_new_rows_v2.xlsx               sheets instructions, reports, rows, molecular, genotypes
  48_b16_add_d4_and_check_v1_<ts>.json  log with counts, unmatched numbers and MD5 checksums

Usage: python3 48_b16_add_d4_and_check_v1.py   (from the project root)
"""
import datetime
import glob
import importlib.util
import json
import os
import re
import subprocess
import sys

import openpyxl
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("b16", os.path.join(HERE, "47_make_b16_new_rows_v1.py"))
b16 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b16)

STUDIES = "10_phase8_analysis/data/analysis_dataset_v3_2026-10-28T193035/studies.csv"
B08B = "08_phase6_data_extraction/verification/round2_2026-10-24/r2_b08b_arbitration.xlsx"
PDF_DIRS = ["08_phase6_data_extraction/verification/round4_2026-10-30/pdfs",
            "07_phase5_full_text_screening/rescreen_ast_2026-10-29/pdfs"]
OUT = f"{b16.OUT_DIR}/r4_b16_new_rows_v2.xlsx"
CHECKER = "claude-opus-5-5"

GD = "gradient_diffusion"
DD = "disk_diffusion"

# report_id: source, period, identification, setting, ar20_check, to_check
D4_REPORTS = {
    "R04084": ("blood and other sterile sites", "2005-2007", "CHROMagar, Vitek, API or molecular",
               "ARTEMIS DISK, 47 centres, global", "",
               "Rows use the reference laboratory microdilution (Ref.-BMD), first in the method order of AR10; "
               "participant disk results (fluconazole R 4.6%, voriconazole R 5.6%) are not used. Counts calculated from "
               "percentages of 412. Period 2005-2007 does not overlap COL_O02615 (1992-2001): proposed as a new "
               "collection. O15877 (2005-2011, n = 3) overlaps in period and has to be decided in B03."),
    "O17938": ("blood", "1997", "Vitek, API, CHROMagar", "SENTRY Europe, 20 centres in 13 countries", "",
               "Counts follow from the MIC ranges and the NCCLS cut-offs. Period 1997 lies inside COL_O02615: proposed "
               "as part of that collection (PARTIAL in B03), so it would be secondary (10 against 354 isolates)."),
    "O13199": ("urine", None, "CHROMagar and MALDI-TOF", "AIIMS, New Delhi, India", "",
               "Table 2 is an image. Isolates tested were chosen at random; the columns of Table 2 add up to 17, the "
               "text says 18. All isolates are stated to be susceptible."),
    "R08533": ("blood", "2007-2016", "ID32C, MALDI-TOF, ITS", "Helsinki and Uusimaa, Finland", "",
               "3 persistent and 3 non-persistent cases summed. CLSI breakpoints until the end of 2010 and EUCAST "
               "afterwards, not separable by isolate: expected to fall as mixed_standard at the build."),
    "O13212": ("clinical samples, not specified", None, "Dalmau method and MALDI-TOF", "Ege University Hospital, Izmir, Turkey", "",
               "No category per isolate: the count applies R >4 to the individual MICs under the declared EUCAST criteria."),
    "O06680": ("urine, blood, other", None, "as in the report", "India", "",
               "Disk diffusion, CLSI. ATCC 66029 is not counted. Amphotericin B has no M44 breakpoint: expected to leave at "
               "the applicability step."),
    "R06784": ("blood", "2024", "MALDI-TOF", "First Affiliated Hospital of Guangzhou Medical University, China", "",
               "Method and document are not named: expected to leave at AR9. The report gives one result for its 3 Candida."),
}

D4_ROWS = [
    ("R04084", "fluconazole", "R", 412, 0, "CLSI M27-S3; S <=8, SDD 16-32, R >=64", b16.BMD, "Table 3",
     "Ref.-BMD: S 98.3, SDD 1.7, R 0.0 %", "calculated from percentages"),
    ("R04084", "voriconazole", "R", 412, 0, "CLSI M27-S3; S <=1, SDD 2, R >=4", b16.BMD, "Table 3",
     "Ref.-BMD: S 100.0, SDD 0.0, R 0.0 %", "calculated from percentages"),
    ("O17938", "fluconazole", "R", 10, 0, "NCCLS M27-A; S <=8, R >=64", b16.BMD, "TABLE 4",
     "range 0.25-2.0, MIC50 1.0, MIC90 2.0", "calculated from the MIC range and the declared criterion"),
    ("O17938", "itraconazole", "R", 10, 0, "NCCLS M27-A; S <=0.12, R >=1.0", b16.BMD, "TABLE 4",
     "range 0.06-0.5, MIC50 0.25, MIC90 0.5", "calculated from the MIC range and the declared criterion"),
    ("O17938", "voriconazole", "MIC_only", 10, None, "no criterion", b16.BMD, "TABLE 4",
     "range 0.015-0.25, MIC50 0.06, MIC90 0.12", "no category"),
    ("O17938", "posaconazole", "MIC_only", 10, None, "no criterion", b16.BMD, "TABLE 4",
     "Sch 56592: range 0.015-0.25, MIC50 0.12, MIC90 0.25", "no category"),
    ("O17938", "caspofungin", "MIC_only", 10, None, "no criterion", b16.BMD, "TABLE 4",
     "MK-0991: range 0.25-2.0, MIC50 0.5, MIC90 1.0", "no category"),
    ("O17938", "ravuconazole", "MIC_only", 10, None, "no criterion", b16.BMD, "TABLE 4",
     "BMS-207147: range 0.015-0.25, MIC50 0.12, MIC90 0.25", "no category"),
]
for agent, ward, icu in [("amphotericin B", "0.5", "0.25-0.5"), ("fluconazole", "0.125-0.2", "0.25"),
                         ("caspofungin", "0.125-0.25", "0.015-0.125"), ("micafungin", "0.015", "0.015"),
                         ("voriconazole", "0.03", "0.03"), ("itraconazole", "0.03", "0.03")]:
    D4_ROWS.append(("O13199", agent, "R", 7, 0, "CLSI M27-A3/M27-S4", b16.BMD, "Table 2",
                    f"Ward (3) {ward}; ICU (4) {icu}; all isolates susceptible", "category stated in the text"))
D4_ROWS += [
    ("R08533", "fluconazole", "R", 6, 0, "CLSI until 2010, EUCAST from 2011", GD, "Table 1",
     "C tropicalis 0/3 and 0/3", "stated by the report; subsets summed"),
    ("O13212", "fluconazole", "R", 4, 0, "EUCAST E.Def 7.3.1; R >4", b16.EU, "Table 2",
     "Individual MICs 1, 0.5, 4, 0.5", "calculated from individual MICs and the declared criterion"),
    ("O06680", "fluconazole", "R", 3, 1, "CLSI; disk 25 ug", DD, "Table 4", "R 1, S-DD 0, S 2", "stated by the report"),
    ("O06680", "voriconazole", "R", 3, 0, "CLSI; disk 1 ug", DD, "Table 4", "R 0, S-DD 0, S 3", "stated by the report"),
    ("O06680", "amphotericin B", "R", 3, 0, "CLSI; disk 100 units", DD, "Table 4", "R 0, S-DD 3, S 0", "stated by the report"),
    ("R06784", "fluconazole", "R", 1, 0, "CLSI, document not named", "not_reported", "minimum inhibitory concentration",
     "susceptible, MIC <=1 mg/L", "stated by the report"),
]

# AR20 of the reports with ar20_check, with the reason written in the comment
AR20 = {"O06294": ("YES", "Case report chosen for acquired resistance; 3 serial isolates of one patient."),
        "O10550": ("YES", "Isolates chosen as fluconazole resistant and susceptible for the ERG11 study."),
        "O10851": ("YES", "Strains chosen for an activity study, one for being drug resistant.")}


def pdf_text(rep):
    for d in PDF_DIRS:
        hit = glob.glob(f"{d}/*_{rep}_*.pdf")
        if hit:
            out = subprocess.run(["pdftotext", "-layout", hit[0], "-"], capture_output=True, text=True).stdout
            return out.replace(",", ".")
    sys.exit(f"No PDF for {rep}")


def unmatched(rep, text):
    """Numbers of reader_text that are not in the PDF text."""
    src = pdf_text(rep)
    nums = re.findall(r"(?<![A-Za-z\d-])\d+(?:\.\d+)?", re.sub(r"(BMD|Sch|BMS|MK|MIC)[\w-]*", " ", text))
    return [n for n in nums if not re.search(rf"(?<![\d.]){re.escape(n)}(?![\d])", src)]


def main():
    st = pd.read_csv(STUDIES, dtype=str).set_index("study_id")
    arb = pd.read_excel(B08B, sheet_name="arbitration", dtype=str).set_index("study_id")

    wb0 = openpyxl.load_workbook(b16.OUT)
    def sheet(n):
        ws = wb0[n]
        h = [c.value for c in ws[1]]
        return [dict(zip(h, [c.value for c in r])) for r in ws.iter_rows(min_row=2)]
    rows, reports, mol, gen = sheet("rows"), sheet("reports"), sheet("molecular"), sheet("genotypes")

    nid = len(rows)
    for rep, agent, outcome, n, ev, crit, meth, loc, text, parse in D4_ROWS:
        nid += 1
        s = st.loc[rep]
        rows.append({"new_row_id": f"M{nid:04d}", "report_id": rep, "study_label": s.study_label, "title": s.title,
                     "year": s.year, "pdf_file": arb.loc[rep, "pdf_file"], "compartment": "C1", "agent_raw": agent,
                     "agent": agent, "outcome": outcome, "n_tested": n, "n_events": ev, "criterion_raw": crit,
                     "location": loc, "method_raw": meth, "method": meth, "reader_text": text, "parse": parse})
    for rep, (source, period, sid, setting, ar20, flag) in D4_REPORTS.items():
        s = st.loc[rep]
        own = [r for r in rows if r["report_id"] == rep]
        reports.append({"report_id": rep, "study_label": s.study_label, "title": s.title, "year": s.year, "journal": s.journal,
                        "doi": s.doi, "pdf_file": arb.loc[rep, "pdf_file"], "country": s.country, "setting": setting,
                        "compartments": "C1", "n_tropicalis_b15": s.n_tropicalis, "source": source, "period": period,
                        "species_id": sid, "ar20_check": ar20, "to_check": flag, "n_rows": len(own),
                        "n_rows_R": sum(r["outcome"] == "R" for r in own)})

    today = datetime.date.today().isoformat()
    misses = {}
    for r in rows:
        r.update({"row_action": "CONFIRM", "reviewer": CHECKER, "date": today,
                  "page_or_table": r["location"]})
        if r["report_id"] != "O13199":
            m = unmatched(r["report_id"], r["reader_text"])
            if m:
                misses[r["new_row_id"]] = m
    for r in reports:
        r.update({"reviewer": CHECKER, "date": today})
        if r["report_id"] in AR20:
            r["ar20_decision"], r["comment"] = AR20[r["report_id"]]
        else:
            r["ar20_decision"] = "NO"
    for r in mol + gen:
        r.update({"row_action": "CONFIRM", "reviewer": CHECKER, "date": today})

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "instructions"
    for line in b16.INSTRUCTIONS + [
            "Version 2: adds the 7 reports of team decision D4. Rows and AR20 were checked by the identifier in column "
            "reviewer; a person has to confirm them before they count as verified by the reviewers."]:
        ws.append([line])
    ws.column_dimensions["A"].width = 130
    b16.write_sheet(wb, "reports", b16.REPORT_COLS, reports)
    b16.write_sheet(wb, "rows", b16.ROW_COLS, rows)
    b16.write_sheet(wb, "molecular", list(mol[0]), mol)
    b16.write_sheet(wb, "genotypes", list(gen[0]), gen)
    wb.save(OUT)

    now = datetime.datetime.now()
    log = {"script": os.path.basename(__file__), "run_time": now.isoformat(timespec="seconds"), "checked_by": CHECKER,
           "verified_by_reviewers": False, "inputs": {b16.OUT: b16.md5(b16.OUT), STUDIES: b16.md5(STUDIES), B08B: b16.md5(B08B)},
           "outputs": {OUT: b16.md5(OUT)},
           "counts": {"reports": len(reports), "rows": len(rows), "rows_R": sum(r["outcome"] == "R" for r in rows),
                      "rows_R_with_events": sum(r["outcome"] == "R" and r["n_events"] > 0 for r in rows),
                      "ar20_yes": sorted(AR20)},
           "numbers_not_found_in_pdf_text": misses}
    with open(f"{b16.OUT_DIR}/48_b16_add_d4_and_check_v1_{now:%Y-%m-%dT%H%M%S}.json", "w") as f:
        json.dump(log, f, indent=1, ensure_ascii=False)
    print(json.dumps(log["counts"]))
    print("not found:", json.dumps(misses))


if __name__ == "__main__":
    main()
