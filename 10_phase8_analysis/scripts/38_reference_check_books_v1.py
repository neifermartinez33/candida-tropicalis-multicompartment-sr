"""Round 3 (reference-list check): verification workbooks for the review team.

B14 (data):  sheet reports  one row per candidate report (screening and extraction proposal; decision to confirm);
             sheet rows     one row per resistance row of the reports proposed for inclusion (values to confirm or
                            correct, with the *_v columns as in B11);
             sheet pairs    proposed same-collection pairs with included reports (as in B03).
B12 (risk of bias of the new reports, as round 2): dedup rule (RB8), editorial status, agronomic management.
Proposals come from the model output of round 3 (screening, extraction) and from the reading of the full texts
recorded in PROPOSALS below; nothing is decided here. In FINAL mode the dataset builder requires every decision.
Usage: python 38_reference_check_books_v1.py   (from the project root)
"""
import glob, os, re, sys, datetime
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_log  # noqa: E402

V3 = "08_phase6_data_extraction/verification/round3_reference_check_2026-10-27"
R3 = "09_phase7_risk_of_bias/round3_reference_check_2026-10-27"
TIDY = "10_phase8_analysis/data/tidy_tables_r3_reference_check_v1_2026-10-27"
REG = "07_phase5_full_text_screening/reference_check_2026-10-27"
# same-collection proposals (report_b is an included report of the main review)
PAIRS = [("B002", "R00651", "YES", "same programme (Australian Candidaemia Study), same period 2001-2004"),
         ("B012", "R02080", "YES", "same hospital (Virgen del Rocío, Seville) and same period 2004-2009"),
         ("B005", "O02775", "NO", "multinational cohort; only its Spanish arm (Gregorio Marañón) may overlap the "
                                   "Marañón candidaemia series: partial overlap, not the same collection"),
         ("B015", "R01591", "NO", "Nîmes and Montpellier also in GEMSUD 2008; collection period of B015 not stated"),
         ("B001", "O15899", "NO", "8 Australian hospitals 2014-2016; Queensland series 2000-2019 may share isolates "
                                   "of one state only")]
# RB8 dedup rule, with the verbatim sentence and the PDF page that support it (rob_rules, section 3)
DEDUP = {"B001": ("by_patient", "Episodes of recurrent candidaemia (occurring more than 30 days after the initial episode) within the study period were excluded.", "2"),
         "B002": ("by_patient", "For patients with >1 episode of candidemia, the second episode was defined as a new case if it occurred >30 days after the previous episode.", "2"),
         "B003": ("by_patient", "Any blood cultures positive for a Candida species within 30 days of the initial positive culture from the same patient were considered part of the same case, or episode", "5"),
         "B006": ("by_patient", "If the same species was detected two times or more in the same patient, only the first time was included in the analysis.", "2"),
         "B004": ("not_declared", "", ""), "B005": ("not_declared", "", ""), "B007": ("not_declared", "", ""),
         "B010": ("not_declared", "", ""), "B012": ("not_declared", "", ""), "B015": ("not_declared", "", ""),
         "B017": ("not_declared", "", ""), "B023": ("not_declared", "", "")}

# (2026-10-28) editorial proposal with the mechanical rule of round 2 (make_rob_books_round2_v1.py); the first
# version proposed peer_reviewed for every report, which missed the MMWR surveillance summary of B003 (a report)
PREPRINT = re.compile(r"rxiv|research square|preprint|ssrn|preprints\.org|authorea|scielo preprints", re.I)
GREY = re.compile(r"tesis|thesis|disertaci|dissertation|monograf|trabajo de grado|congres|congress|abstract|resumen de|"
                  r"meeting|symposium|simposio|jornada|informe t[eé]cnico|report", re.I)


def editorial(text):
    return "preprint" if PREPRINT.search(text) else ("grey" if GREY.search(text) else "peer_reviewed")


def newest(p):
    f = sorted(glob.glob(p))
    assert f, p
    return f[-1]

def main():
    stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S")
    reg = pd.read_csv(newest(f"{REG}/reference_check_candidates_v1_*.csv"))
    scr_f = newest(f"{REG}/full_text_screening_r3_v1_*.xlsx")
    scr = pd.read_excel(scr_f, sheet_name="All").set_index("ID")
    rep = pd.read_csv(f"{TIDY}/reports.csv").set_index("report_id")
    ast = pd.read_csv(f"{TIDY}/ast.csv")
    st3 = pd.read_csv(newest("10_phase8_analysis/data/analysis_dataset_v3_2*/studies.csv"), low_memory=False).set_index("study_id")
    reports = []
    for _, g in reg.iterrows():
        rid = g.report_id
        s = scr.loc[rid] if rid in scr.index else None
        e = rep.loc[rid] if rid in rep.index else None
        ext_dec = e.extraction_decision if e is not None else ""
        proposal = ("NOT_RETRIEVED" if g.retrieval_status != "retrieved" else
                    "INCLUDE_MA" if e is not None and ext_dec == "INCLUDE" and e.extraction_ma == "YES" else
                    "INCLUDE_SQ1" if e is not None and ext_dec == "INCLUDE" else "EXCLUDE")
        reports.append({"report_id": rid, "title": g.title, "first_author": g.first_author, "year": g.year,
                        "doi": g.doi, "pdf_file": g.pdf_file, "retrieval_status": g.retrieval_status,
                        "screening_decision": "" if s is None else s.Decision,
                        "screening_reason": "" if s is None else s["Main reason"],
                        "extraction_decision": ext_dec, "change_reason": "" if e is None else e.extraction_change_reason,
                        "n_tropicalis_total": None if e is None else e.n_tropicalis_total,
                        "compartments": None if e is None else e.compartments_raw,
                        "country": None if e is None else e.country_raw,
                        "period": None if e is None else f"{e.period_start}-{e.period_end}",
                        "proposal": proposal, "decision": "", "ec": "", "reviewer": "", "date": "", "comment": ""})
    rows = ast[ast.report_id.isin([r["report_id"] for r in reports if r["proposal"].startswith("INCLUDE")])]
    rws = pd.DataFrame({"row_id": "R3_" + rows.ast_row_id.astype(str), "report_id": rows.report_id,
                        "compartment": rows.compartment, "period_raw": rows.period_raw, "agent_raw": rows.agent_raw,
                        "agent": rows.agent_std, "method_raw": rows.method_raw, "criterion_raw": rows.interp_raw,
                        "n_tested": rows.n_tested, "n_S": rows.n_S, "n_SDD_I": rows.n_SDD_I, "n_R": rows.n_R,
                        "n_NWT": rows.n_NWT, "mic_range": rows.mic_range, "note": rows.note_raw,
                        "row_action": "", "n_tested_v": "", "n_S_v": "", "n_SDD_I_v": "", "n_R_v": "", "n_NWT_v": "",
                        "criterion_v": "", "page_or_table": "", "reviewer": "", "date": "", "comment": ""})
    pairs = []
    for i, (a, b, prop, why) in enumerate(PAIRS, 1):
        sb = st3.loc[b]
        pairs.append({"pair_id": f"R3P{i:02d}", "report_a": a, "label_a": f"{rep.at[a, 'study_label']}" if a in rep.index else a,
                      "period_a": f"{rep.at[a, 'period_start']}-{rep.at[a, 'period_end']}" if a in rep.index else "",
                      "n_a": rep.at[a, "n_tropicalis_total"] if a in rep.index else None,
                      "institution_a": rep.at[a, "programme_institution_raw"] if a in rep.index else "",
                      "report_b": b, "label_b": sb.study_label, "period_b": f"{sb.period_start}-{sb.period_end}",
                      "n_b": sb.n_tropicalis, "institution_b": sb.programme_institution_raw,
                      "proposal": prop, "reason": why, "decision": "", "reviewer": "", "date": "", "comment": ""})
    instr = pd.DataFrame({"Round 3, workbook B14: reports found by checking the reference lists of four previous reviews": [
        "reports: write INCLUDE_MA, INCLUDE_SQ1, EXCLUDE or NOT_RETRIEVED in decision (and the EC code when excluding).",
        "rows: write CONFIRM, CORRECT or DELETE in row_action; when correcting, fill only the *_v columns that change and "
        "page_or_table.",
        "pairs: write YES (same collection) or NO in decision.",
        "Proposals were written by the language model (screening and extraction with the frozen phase 5 and 6 "
        "instructions) and by the reading of the full texts; no proposal enters the FINAL dataset without a decision."]})
    os.makedirs(V3, exist_ok=True); os.makedirs(R3, exist_ok=True)
    p14 = f"{V3}/r3_b14_reference_check_{stamp}.xlsx"
    with pd.ExcelWriter(p14) as w:
        instr.to_excel(w, sheet_name="instructions", index=False)
        pd.DataFrame(reports).to_excel(w, sheet_name="reports", index=False)
        rws.to_excel(w, sheet_name="rows", index=False)
        pd.DataFrame(pairs).to_excel(w, sheet_name="pairs", index=False)
    rob = []
    for r in reports:
        if not r["proposal"].startswith("INCLUDE"):
            continue
        rid = r["report_id"]; e = rep.loc[rid]
        rule, quote, page = DEDUP[rid]
        rob.append({"report_id": rid, "study_label": e.study_label, "year": e.year, "journal": e.journal, "doi": e.doi,
                    "country": e.country_raw, "compartments": e.compartments_raw, "design": e.design_raw,
                    "pdf_file": r["pdf_file"], "entry_route": "reference_check_2026_10_27", "site_applies": "",
                    "dedup_rule": rule, "dedup_quote": quote, "dedup_page": page, "methods_read": "YES",
                    "editorial_status": "", "editorial_proposal": editorial(f"{e.journal} {e.title}"), "agronomic_management": "not_applicable",
                    "agro_quote": "", "agro_page": "", "reviewer": "", "verifier": "", "agrees": "",
                    "dedup_rule_final": "", "comments": ""})
    p12 = f"{R3}/r3_b12_rob_reference_check_{stamp}.xlsx"
    with pd.ExcelWriter(p12) as w:
        pd.DataFrame({"Round 3, workbook B12: risk of bias of the reports of the reference-list check": [
            "Confirm dedup_rule (RB8) in dedup_rule_final and editorial_status; the other criteria are derived from the "
            "verified extraction, as in round 2."]}).to_excel(w, sheet_name="instructions", index=False)
        pd.DataFrame(rob).to_excel(w, sheet_name="reports", index=False)
    print(run_log.write(__file__, [newest(f"{REG}/reference_check_candidates_v1_*.csv"), scr_f, f"{TIDY}/reports.csv",
                                   f"{TIDY}/ast.csv"], [p14, p12], reports=len(reports), rows=len(rws), pairs=len(pairs),
                        rob_reports=len(rob)))
    print(p14, p12, sep="\n")

if __name__ == "__main__":
    main()
