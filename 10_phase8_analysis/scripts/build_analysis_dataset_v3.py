#!/usr/bin/env python3
"""build_analysis_dataset_v3.py (2026-10-24)

Analysis dataset v3 = exact reconstruction of analysis_dataset_v2 + mechanical layer of 2026-10-24
(verification_rules_v1) + human decisions of round 2 (workbooks r2_b02 to r2_b11 and the doubtful-reports
workbook of 2026-10-20). Team decisions: 10_phase8_analysis/team_decisions_2026-10-24.md.

Round 3 (2026-10-27): reports found by checking the reference lists of four previous reviews enter through the
verification workbook r3_b14 (decisions per report, per AST row and same-collection pairs), with their extraction
in tidy_tables_r3_reference_check_v1_2026-10-27; they go through the same functions as the round-2 extra reports.

Modes:
  no option       FINAL. If a mandatory decision is missing, it stops and writes the list of pending ones.
  --provisional   Where the decision is missing it uses the proposal in the workbook. The output folder and every
                  file carry PROVISIONAL; no figure of that run goes to the article.
  --check         Reads everything, reports and writes nothing.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/build_analysis_dataset_v3.py --provisional
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/build_analysis_dataset_v3.py
Outputs (never overwritten), in 10_phase8_analysis/data/analysis_dataset_v3_<date-time>[_PROVISIONAL]/:
  studies.csv, ast.csv, molecular.csv, genotypes.csv, clade4.csv   tables, with the v2 columns and the new ones
  collection_merges.csv     pairs that round 2 declared the same collection (read by 04_ma_input_v2.py)
  report_decisions.csv      one row per report with its entry or exit route (read by PRISMA v3)
  changes_log.csv           every change applied: workbook, key, field, old and new value, reviewer
  pending.csv               decisions that were missing (in provisional mode, those taken from the proposal)
  build_log.json            MD5 of inputs and outputs, counts per step
"""
import glob
import os
import re
import sys
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dataset_v3_core as C  # noqa: E402
import dictionaries as Dct  # noqa: E402
import verification_rules_v1 as V  # noqa: E402

R2 = "08_phase6_data_extraction/verification/round2_2026-10-24"
BOOK = {k: f"{R2}/r2_{k}.xlsx" for k in ("b02_rows", "b03_collection_pairs", "b04_ar20_rows", "b05_species_id",
                                         "b07_allocation_c5", "b09_extraction_exclusions", "b11_new_ast_rows")}
B08_ARB = f"{R2}/r2_b08b_arbitration.xlsx"      # written by analyze_blind_sample_v1.py; optional
# (2026-10-26) arbiter inclusions of reports excluded at full text, which have no extraction
B08_BLIND = f"{R2}/r2_b08_sample_blind.xlsx"
B08_COUNTRY = f"{R2}/b08_arbitration_country_from_comments_2026-10-26.csv"
# (2026-10-26) extraction corrections confirmed in the B10 review: MIC and criterion, with quote and page
B10_FIX = f"{R2}/extraction_corrections_b10_2026-10-25.csv"
# (2026-10-26) data that the reviewers corrected in the B09 comment (n, compartment, country), transcribed with
# the literal fragment; the allocation by compartment of the multicompartment reports is in isolate_groups_..._v3
B09_TRANS = f"{R2}/b09_comment_transcription_2026-10-26.csv"
ALLOC_BOOKS = "08_phase6_data_extraction/verification/isolate_groups_multicompartment_v*.xlsx"
B10_MIC = {"mic50": "mic50_mg_l", "mic90": "mic90_mg_l", "mic_min": "mic_min_mg_l", "mic_max": "mic_max_mg_l"}
FT_SHEET = "07_phase5_full_text_screening/full_text_screening.xlsx"
RIS = "06_phase4_title_abstract_screening/import/screening_reviewer_1_reviewer_2_n22203_seed1310202643.ris"
R_MAP = "07_phase5_full_text_screening/r_stream_screen_id_map_2026-10-24.csv"
DUB = "07_phase5_full_text_screening/doubtful_review_2026-10-20/full_text_doubtful_review_2026-10-20.xlsx"
DECISIONS = "10_phase8_analysis/team_decisions_2026-10-24.md"
R3_BOOK = "08_phase6_data_extraction/verification/round3_reference_check_2026-10-27/r3_b14_reference_check_*.xlsx"
R3_TIDY = "10_phase8_analysis/data/tidy_tables_r3_reference_check_v1_2026-10-27"
R3_XLSX = "08_phase6_data_extraction/reference_check_2026-10-27/data_extraction_r3_v1_2026-10-27T192604.xlsx"
R3_ROUTE = "reference_check_2026_10_27"
R3_OK = {"INCLUDE_MA", "INCLUDE_SQ1", "EXCLUDE", "NOT_RETRIEVED"}
OUT_BASE = "10_phase8_analysis/data"
EC_RE = re.compile(r"\bEC(1[0-3]|[1-9])\b", re.I)
DUB_OK = {"ENTERS_REVIEW_AND_MA", "ENTERS_REVIEW", "REMAINS_EXCLUDED", "NOT_RETRIEVED", "NOT_DETERMINABLE"}
DUB_SYN = {"INCLUDE": "ENTERS_REVIEW", "INCLUDE_MA": "ENTERS_REVIEW_AND_MA", "EXCLUDE": "REMAINS_EXCLUDED"}
NUM_V = {"n_tested_v": "n_tested", "n_S_v": "n_S", "n_SDD_I_v": "n_SDD_I", "n_R_v": "n_R", "n_NWT_v": "n_NWT"}


class Ledger:
    """Changes applied and pending decisions."""

    def __init__(self, provisional):
        self.provisional = provisional
        self.changes, self.pending = [], []

    def change(self, book, key, field, old, new, decision, reviewer=None, date=None, used_proposal=False):
        self.changes.append({"book": book, "key": key, "field": field, "old": old, "new": new, "decision": decision,
                             "reviewer": reviewer, "date": date, "from_proposal": "YES" if used_proposal else "NO"})

    def need(self, book, key, what, proposal):
        self.pending.append({"book": book, "key": key, "missing": what, "proposal_used": proposal if self.provisional else ""})


def txt(v):
    return "" if V.is_blank(v) else str(v).strip()


def read_book(path, sheet):
    if not os.path.exists(path):
        sys.exit(f"The workbook is missing {path}. Run make_verification_books_v1.py first.")
    return pd.read_excel(path, sheet_name=sheet, dtype=object)


def decide(row, col, proposal, ledger, book, key, what, allowed=None):
    """Reviewer's decision or, in provisional mode, the proposal. Returns (value, from_proposal)."""
    v = txt(row.get(col))
    if v:
        if allowed and v not in allowed:
            sys.exit(f"{book}, {key}: value not admitted in {col}: {v!r}. Admitted: {sorted(allowed)}")
        return v, False
    ledger.need(book, key, what, proposal)
    return (proposal, True) if ledger.provisional else (None, True)


# ------------------------------------------------------------------------------------- reports
def doubtful_decisions(ledger):
    d = pd.read_excel(DUB, sheet_name="Review", dtype=object)
    out = {}
    for r in d.to_dict("records"):
        v = txt(r.get("decision_final")).upper()
        v = DUB_SYN.get(v, v)
        used = False
        if not v:
            ledger.need("doubtful_2026-10-20", r["ID"], "decision_final", r["proposed_verdict"])
            if not ledger.provisional:
                continue
            v, used = r["proposed_verdict"], True
        if v not in DUB_OK:
            sys.exit(f"Doubtful-reports workbook, {r['ID']}: decision_final not admitted: {v!r}")
        ec = EC_RE.search(txt(r.get("reviewers_comment")) or txt(r.get("exclusion_code")))
        out[r["ID"]] = {"decision": v, "ec": ("EC" + ec.group(1)) if ec else "", "from_proposal": used,
                        "reviewer": txt(r.get("decision_reviewer_1")) + "/" + txt(r.get("decision_reviewer_2"))}
    return out


def b09_decisions(ledger):
    b = read_book(BOOK["b09_extraction_exclusions"], "reports")
    allowed = {"INCLUDE_SQ1", "INCLUDE_MA", "NOT_RETRIEVED"} | {f"EXCLUDE_EC{i}" for i in range(1, 14)}
    out = {}
    for r in b.to_dict("records"):
        prop = r["proposal"] if r["proposal"] != "REVIEW" else "EXCLUDE_UNREVIEWED"
        v, used = decide(r, "decision", prop, ledger, "B09", r["study_id"], "decision", allowed)
        if v is None:
            continue
        out[r["study_id"]] = {"decision": v, "from_proposal": used, "reviewer": txt(r.get("reviewer")),
                              "date": txt(r.get("date")),
                              "data": {k: txt(r.get(k)) for k in B09_DATA}}
    return out


# (2026-10-26) Data columns of B09. If the PDF assigned to the report is another work and the reviewer includes it after reading
# the correct text, these values replace those of the extraction (which was done on the wrong PDF).
B09_DATA = ["study_label", "year", "n_tropicalis_total", "compartments", "country", "period_start", "period_end",
            "design", "identification_method"]
B09_REQUIRED = ["study_label", "year", "n_tropicalis_total", "compartments", "country"]


def b09_transcription(e500):
    """Corrections from the B09 comment for the inclusions: n, compartment and country. If the report is already in an
    allocation workbook, that workbook prevails on the compartment."""
    if not os.path.exists(B09_TRANS):
        return {}
    tr = pd.read_csv(B09_TRANS, dtype=str)
    in_books = set()
    for f in glob.glob(ALLOC_BOOKS):
        in_books |= set(pd.read_excel(f, sheet_name="allocation", dtype=object).report_id.astype(str))
    ov = {}
    for r in tr.to_dict("records"):
        k = r["study_id"]
        if k not in e500 or not e500[k]["decision"].startswith("INCLUDE"):
            continue
        d = {}
        if txt(r.get("n_tropicalis_total_v")):
            d["n_tropicalis_total"] = float(r["n_tropicalis_total_v"])
        if txt(r.get("compartments_v")) and k not in in_books:
            d["compartments_raw"] = r["compartments_v"]
        if txt(r.get("country_v")):
            iso, reg, multi, _, _ = Dct.map_country(r["country_v"])
            if not iso and not multi:
                sys.exit(f"Transcription B09, {k}: unrecognized country: {r['country_v']!r}")
            d.update(country_raw=r["country_v"], country_iso3=";".join(iso) if iso else None, who_region=reg,
                     multinational=bool(multi), country_inferred_flag=False)
        if d:
            ov[k] = d
    return ov


def b09_overrides(e500, rep, ledger):
    """Extraction fields that are replaced by those of B09 in reports with the PDF of another work."""
    wrong = set(rep.report_id[rep.pdf_status.eq("wrong_document_per_notes")])
    ov = {}
    for k, v in e500.items():
        if not v["decision"].startswith("INCLUDE") or k not in wrong:
            continue
        d = v["data"]
        missing = [c for c in B09_REQUIRED if not d[c]]
        if missing:
            if not ledger.provisional:
                sys.exit(f"B09, {k}: the assigned PDF is another work; to include it, fill in {missing} with the correct text")
            continue
        iso, reg, multi, inferred, _ = Dct.map_country(d["country"])
        if not iso:
            sys.exit(f"B09, {k}: unrecognized country: {d['country']!r}")
        ov[k] = {"study_label": d["study_label"], "year": float(d["year"]), "country_raw": d["country"],
                 "country_iso3": ";".join(iso), "who_region": reg, "multinational": multi, "country_inferred_flag": False,
                 "compartments_raw": d["compartments"], "n_tropicalis_total": float(d["n_tropicalis_total"]),
                 "period_start": float(d["period_start"]) if d["period_start"] else None,
                 "period_end": float(d["period_end"]) if d["period_end"] else None,
                 "design_raw": d["design"] or None, "species_id_raw": d["identification_method"] or None,
                 "pdf_status": "correct_text_read_in_round2"}
    return ov


def first_authors(ids):
    """First author of the screening record (RIS) for each report; R is translated to its SCREEN_ID."""
    rmap = pd.read_csv(R_MAP)
    r2s = dict(zip(rmap.R_id, rmap.screen_id))
    sid = {i: (i if i.startswith("O") else r2s.get(i, "")) for i in ids}
    want, out, au, cur = set(sid.values()), {}, [], None
    with open(RIS, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            if ln.startswith("ER  -"):
                if cur in want and au:
                    out[cur] = au[0]
                au, cur = [], None
            elif ln.startswith("AU  - "):
                au.append(ln[6:].strip())
            elif ln.startswith("N1  - SCREEN_ID "):
                cur = ln[16:].strip()
    return {i: out.get(s, "") for i, s in sid.items()}


def arbitration_new_reports(ids, rep, ledger):
    """Report rows for the arbiter inclusions that have no extraction (excluded at full text).
    Compartment and n: blind reading of B08, confirmed by the arbiter. Country, identification, period and design:
    full-text screening sheet; the country that appears only in the reviewers' comment comes from B08_COUNTRY.
    Label: surname of the first author of the record and year."""
    new = sorted(set(ids) - set(rep.report_id))
    if not new:
        return {}
    b = pd.read_excel(B08_BLIND, sheet_name="sample", dtype=object).set_index("study_id")
    ft = pd.read_excel(FT_SHEET, sheet_name="All", dtype=object).set_index("ID")
    extra_c = pd.read_csv(B08_COUNTRY, dtype=str).set_index("study_id")["country"].to_dict() if os.path.exists(B08_COUNTRY) else {}
    au = first_authors(new)
    ov = {}
    for k in new:
        r, f = b.loc[k], ft.loc[k] if k in ft.index else pd.Series(dtype=object)
        country = txt(f.get("Country")) or txt(extra_c.get(k))
        comp = txt(r.get("compartments")); n = pd.to_numeric(r.get("n_tropicalis"), errors="coerce")
        year = pd.to_numeric(r.get("year"), errors="coerce")
        surname = au[k].split(",")[0].strip()
        missing = [c for c, v in (("country", country), ("compartments", comp), ("n_tropicalis", n), ("year", year),
                                ("first author", surname)) if v in ("", None) or (isinstance(v, float) and pd.isna(v))]
        if missing:
            if not ledger.provisional:
                sys.exit(f"Arbitration B08, {k}: inclusion without {missing}")
            continue
        iso, reg, multi, _, _ = Dct.map_country(country)
        if not iso and not multi:
            sys.exit(f"Arbitration B08, {k}: unrecognized country: {country!r}")
        yrs = re.findall(r"(?:19|20)\d{2}", txt(f.get("Period")))
        ov[k] = {"study_label": f"{surname} {int(year)}", "year": float(year), "title": txt(r.get("title")) or None,
                 "journal": txt(r.get("journal")) or None, "doi": txt(r.get("DOI")) or None,
                 "pdf_file": txt(r.get("pdf_file")) or None, "country_raw": country,
                 "country_iso3": ";".join(iso) if iso else None, "who_region": reg, "multinational": bool(multi),
                 "country_inferred_flag": False, "compartments_raw": comp, "n_tropicalis_total": float(n),
                 "period_start": float(yrs[0]) if yrs else None, "period_end": float(yrs[-1]) if yrs else None,
                 "design_raw": txt(f.get("Study type")) or None, "species_id_raw": txt(f.get("Identification")) or None,
                 "pdf_status": "read_in_round2_blind_sample", "extraction_decision": "INCLUDE",
                 "n_rows_ast": 0, "n_rows_molecular": 0, "n_rows_genotype": 0}
    return ov


def b08_arbitration():
    """Reversals confirmed by the third reviewer in the blind sample (if the workbook already exists)."""
    if not os.path.exists(B08_ARB):
        return {}, "not arbitrated: the workbook r2_b08b_arbitration.xlsx does not exist yet"
    b = pd.read_excel(B08_ARB, sheet_name="arbitration", dtype=object)
    out = {}
    for r in b.to_dict("records"):
        v = txt(r.get("arbiter_decision")).upper()
        if v in ("INCLUDE", "EXCLUDE"):
            out[r["study_id"]] = {"decision": v, "ec": txt(r.get("ec_code")), "reviewer": txt(r.get("arbiter"))}
    return out, f"{len(out)} arbitration decisions read"


# ------------------------------------------------------------------------------------ rows
def b02_decisions(ledger):
    reps = read_book(BOOK["b02_rows"], "reports")
    rows = read_book(BOOK["b02_rows"], "rows")
    rep_dec, row_dec = {}, {}
    for r in reps.to_dict("records"):
        need = int(r["priority"]) <= 3
        v = txt(r.get("report_eligible"))
        if not v:
            if need:
                ledger.need("B02", r["study_id"], "report_eligible", "YES")
            v = "YES"
        elif v not in ("YES", "NO"):
            sys.exit(f"B02, report {r['study_id']}: report_eligible not admitted: {v!r}")
        # (2026-10-26) a NO carries its EC code or NOT_RETRIEVED (PDF of another work); empty is not admitted in FINAL
        ec_b02 = txt(r.get("ec_if_not")).upper()
        if v == "NO" and not re.fullmatch(r"EC\d{1,2}|NOT_RETRIEVED", ec_b02) and not ledger.provisional:
            sys.exit(f"B02, report {r['study_id']}: report_eligible NO without ec_if_not (ECn or NOT_RETRIEVED)")
        rep_dec[r["study_id"]] = {"eligible": v, "ec": txt(r.get("ec_if_not")), "reviewer": txt(r.get("reviewer")),
                                  "date": txt(r.get("date")), "reviewed": bool(txt(r.get("report_eligible")))}
    for r in rows.to_dict("records"):
        need = int(r["priority"]) <= 3
        a = txt(r.get("row_action"))
        if a and a not in ("OK", "CORRECT", "EXCLUDE_ROW"):
            sys.exit(f"B02, row {r['row_id']}: row_action not admitted: {a!r}")
        if not a and need:
            ledger.need("B02", r["row_id"], "row_action", "OK")
        vals = {k: r.get(k) for k in list(NUM_V) + ["compartment_v", "criterion_v"] if txt(r.get(k))}
        if a == "CORRECT" and not vals:
            sys.exit(f"B02, row {r['row_id']}: CORRECT without any *_v value")
        if a in ("CORRECT", "EXCLUDE_ROW") and not txt(r.get("page_or_table")):
            sys.exit(f"B02, row {r['row_id']}: {a} without page_or_table (principle 3: no trace, no change)")
        row_dec[r["row_id"]] = {"action": a or ("OK" if ledger.provisional or not need else ""), "values": vals,
                                "reviewed": bool(a), "reviewer": txt(r.get("reviewer")), "date": txt(r.get("date")),
                                "page": txt(r.get("page_or_table"))}
    return rep_dec, row_dec


def b03_merges(ledger):
    b = read_book(BOOK["b03_collection_pairs"], "pairs")
    out = []
    for r in b.to_dict("records"):
        prop = r["proposal"] if r["proposal"] in ("YES", "PARTIAL") else "NO"
        v, used = decide(r, "decision", prop, ledger, "B03", r["pair_id"], "decision", {"YES", "PARTIAL", "NO"})
        if v in ("YES", "PARTIAL"):
            out.append({"pair_id": r["pair_id"], "report_a": r["report_a"], "report_b": r["report_b"], "decision": v,
                        "from_proposal": "YES" if used else "NO", "reviewer": txt(r.get("reviewer"))})
    return pd.DataFrame(out, columns=["pair_id", "report_a", "report_b", "decision", "from_proposal", "reviewer"])


def b04_ar20(ledger):
    b = read_book(BOOK["b04_ar20_rows"], "rows")
    out = {}
    for r in b.to_dict("records"):
        prop = "EXCLUDE_AR20" if r["proposal"] in ("phenotype_selected", "inferred_denominator", "compiled_dataset") else "KEEP"
        v, used = decide(r, "decision", prop, ledger, "B04", r["row_id"], "decision", {"EXCLUDE_AR20", "KEEP"})
        reason = txt(r.get("reason_ar20")) or (r["proposal"] if used else "")
        if v == "EXCLUDE_AR20":
            if not reason:
                sys.exit(f"B04, row {r['row_id']}: EXCLUDE_AR20 without reason_ar20")
            out[r["row_id"]] = {"reason": reason, "from_proposal": used, "reviewer": txt(r.get("reviewer"))}
    return out


def b05_species(ledger):
    b = read_book(BOOK["b05_species_id"], "reports")
    allowed = {"molecular", "MALDI_TOF", "automated", "biochemical", "chromogenic", "conventional", "not_specified"}
    out = {}
    for r in b.to_dict("records"):
        v, used = decide(r, "decision_species_id", r["species_id_proposal"], ledger, "B05", r["study_id"],
                         "decision_species_id", allowed)
        if v:
            out[r["study_id"]] = {"species_id": v, "from_proposal": used, "reviewer": txt(r.get("reviewer"))}
    return out


def b13_labels(ledger):
    """Workbook B13 (optional): corrected report labels. Only the label; the year is not applied here."""
    f = f"{R2}/r2_b13_labels.xlsx"
    if not os.path.exists(f):
        return {}
    out = {}
    for r in read_book(f, "reports").to_dict("records"):
        prop = txt(r.get("study_label_proposal")) or txt(r.get("study_label_extracted"))
        v, used = decide(r, "decision_study_label", prop, ledger, "B13", r["study_id"], "decision_study_label")
        if v:
            out[r["study_id"]] = {"label": v, "from_proposal": used, "reviewer": txt(r.get("reviewer"))}
    return out


def b07_decisions(ledger):
    al = read_book(BOOK["b07_allocation_c5"], "allocation")
    c5 = read_book(BOOK["b07_allocation_c5"], "c5")
    alloc = {}
    if "row_id" in al.columns:
        for r in al.to_dict("records"):
            v, used = decide(r, "decision", "EXCLUDE_ROW", ledger, "B07", r["row_id"], "decision",
                             {"REASSIGN", "CORRECT_N", "EXCLUDE_ROW"})
            if v == "REASSIGN" and not txt(r.get("compartment_v")):
                sys.exit(f"B07, row {r['row_id']}: REASSIGN without compartment_v")
            if v == "CORRECT_N" and not txt(r.get("n_tested_v")):
                sys.exit(f"B07, row {r['row_id']}: CORRECT_N without n_tested_v")
            if v:
                alloc[r["row_id"]] = {"decision": v, "compartment_v": txt(r.get("compartment_v")),
                                      "n_tested_v": txt(r.get("n_tested_v")), "from_proposal": used,
                                      "reviewer": txt(r.get("reviewer"))}
    agro = {}
    for r in c5.to_dict("records"):
        prop = txt(r.get("proposal_agronomic")) or "not_evaluated"
        v, used = decide(r, "decision_agronomic", prop, ledger, "B07", r["report_id"], "decision_agronomic",
                         {"documented_absent", "documented_present", "not_evaluated"})
        if v:
            agro[r["report_id"]] = {"agronomic": v, "from_proposal": used, "reviewer": txt(r.get("reviewer"))}
    return alloc, agro


def b11_rows(ledger, dub_ma_ids):
    b = read_book(BOOK["b11_new_ast_rows"], "rows")
    out = []
    for r in b.to_dict("records"):
        if r["report_id"] not in dub_ma_ids:
            continue       # the report did not enter the meta-analysis in the doubtful-reports workbook
        v, used = decide(r, "row_action", "CONFIRM", ledger, "B11", r["new_row_id"], "row_action",
                         {"CONFIRM", "CORRECT", "DISCARD"})
        if v in (None, "DISCARD"):
            continue
        if v == "CORRECT" and not any(txt(r.get(k)) for k in ("n_tested_v", "n_events_v", "compartment_v",
                                                               "criterion_v", "method_v")):
            sys.exit(f"B11, row {r['new_row_id']}: CORRECT without *_v values")
        if not used and not txt(r.get("page_or_table")):
            sys.exit(f"B11, row {r['new_row_id']}: page_or_table is missing")
        g = lambda k, d: txt(r.get(k)) or d  # noqa: E731
        out.append({"row_id": r["new_row_id"], "study_id": r["report_id"], "compartment": g("compartment_v", r["compartment"]),
                    "agent": r["agent"], "outcome": r["outcome"], "n_tested": int(float(g("n_tested_v", r["n_tested"]))),
                    "n_events": int(float(g("n_events_v", r["n_events"]))), "interp_raw": g("criterion_v", r["criterion_raw"]),
                    "method": g("method_v", r["method"]), "from_proposal": used, "reviewer": txt(r.get("reviewer")),
                    "page": g("page_or_table", r.get("location"))})
    return out


# ------------------------------------------------------------------------------- build
def r3_decisions(ledger):
    """Round 3: decisions per report, per AST row and per same-collection pair (workbook r3_b14)."""
    f = sorted(glob.glob(R3_BOOK))
    if not f:
        return None
    path = f[-1]
    rep_d, row_d, pairs = {}, {}, []
    for r in read_book(path, "reports").to_dict("records"):
        v, used = decide(r, "decision", r["proposal"], ledger, "R3_B14", r["report_id"], "decision", R3_OK)
        if v is None:
            continue
        ec = txt(r.get("ec")) or (EC_RE.search(txt(r.get("screening_reason"))).group(0)
                                  if EC_RE.search(txt(r.get("screening_reason"))) else "")
        rep_d[r["report_id"]] = {"decision": v, "ec": ec if v == "EXCLUDE" else "", "from_proposal": used,
                                 "reviewer": txt(r.get("reviewer"))}
    for r in read_book(path, "rows").to_dict("records"):
        v, used = decide(r, "row_action", "CONFIRM", ledger, "R3_B14", r["row_id"], "row_action",
                         {"CONFIRM", "CORRECT", "DELETE"})
        if v is None:
            continue
        vals = {k: r[k] for k in ("n_tested_v", "n_S_v", "n_SDD_I_v", "n_R_v", "n_NWT_v", "criterion_v")
                if not V.is_blank(r.get(k))}
        row_d[r["row_id"]] = {"action": v, "values": vals, "from_proposal": used, "reviewer": txt(r.get("reviewer")),
                              "date": txt(r.get("date"))}
    for r in read_book(path, "pairs").to_dict("records"):
        v, used = decide(r, "decision", r["proposal"], ledger, "R3_B14", r["pair_id"], "decision", {"YES", "NO"})
        if v == "YES":
            pairs.append({"pair_id": r["pair_id"], "report_a": r["report_a"], "report_b": r["report_b"], "decision": v,
                          "from_proposal": "YES" if used else "NO", "reviewer": txt(r.get("reviewer"))})
    return {"path": path, "reports": rep_d, "rows": row_d, "pairs": pairs}


def std_of(raw):
    k = V.norm_text(raw)
    c, e = bool(re.search(r"\b(clsi|nccls)\b", k)), bool(re.search(r"\beucast\b", k))
    return "CLSI+EUCAST" if (c and e) else ("CLSI" if c else ("EUCAST" if e else None))


def b11_to_ast(rows, studies):
    """B11 rows with the columns of the ast table."""
    if not rows:
        return pd.DataFrame()
    d = pd.DataFrame(rows)
    yr = studies.set_index("study_id")["year"]
    # Agent class from the extraction dictionary (corrected on 2026-10-24: it was empty before and
    # Figure 3 showed an "NA" class)
    class_of = {a: c for a, c, _ in Dct.AGENT_EXACT.values()}
    cls = d.agent.map(class_of)
    if cls.isna().any():
        sys.exit(f"B11: agents without a class in dictionaries.AGENT_EXACT: {sorted(d.agent[cls.isna()].unique())}")
    out = pd.DataFrame({
        "row_id": d.row_id, "study_id": d.study_id, "compartment": d.compartment, "period_start": pd.NA, "period_end": pd.NA,
        "agent": d.agent, "agent_class": cls, "method": d.method, "interp_standard": d.interp_raw.map(std_of),
        "interp_documents": None, "bp_type": np.where(d.outcome == "NWT", "ECV", "CBP"), "flc_regime": None,
        "version_inferred": "NO", "n_tested": d.n_tested.astype("Int64"), "n_S": pd.NA, "n_SDD_I": pd.NA,
        "n_R": np.where(d.outcome == "R", d.n_events, np.nan), "n_NWT": np.where(d.outcome == "NWT", d.n_events, np.nan),
        "mic50_mg_l": np.nan, "mic90_mg_l": np.nan, "mic_min_mg_l": np.nan, "mic_max_mg_l": np.nan, "mic_gm_mg_l": np.nan,
        "interp_raw": d.interp_raw, "note_raw": "B11 " + d.page.astype(str), "source_raw": None,
        "ast_row_id": None, "origin": "B11"})
    out["n_R"] = out.n_R.astype("Int64")
    out["n_NWT"] = out.n_NWT.astype("Int64")
    out["year_tmp"] = out.study_id.map(yr)
    return out


def main():
    args = sys.argv[1:]
    provisional, check = "--provisional" in args, "--check" in args
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    L = Ledger(provisional or check)
    counts = {}

    # 1. reconstruction of v2 and mechanical layer
    t = C.load_tidy()
    tb = C.apply_ec2(C.rebuild_v1(t))
    bad = C.check_against_v2(tb)
    if bad:
        sys.exit("The reconstruction does not reproduce analysis_dataset_v2: " + " | ".join(bad))
    m = C.mechanical(tb, t["rep"])
    st, a = m["studies"].copy(), m["ast"].copy()
    a["origin"] = "analysis_v2"
    st["entry_route"] = "analysis_v2"
    counts["v2 reports"], counts["v2 ast rows"] = len(st), len(a)

    # 2. decisions
    dub = doubtful_decisions(L)
    e500 = b09_decisions(L)
    arb, arb_note = b08_arbitration()
    rep_dec, row_dec = b02_decisions(L)
    merges = b03_merges(L)
    ar20 = b04_ar20(L)
    species = b05_species(L)
    labels = b13_labels(L)
    alloc, agro = b07_decisions(L)
    dub_ma = {k for k, v in dub.items() if v["decision"] == "ENTERS_REVIEW_AND_MA"}
    new_rows = b11_rows(L, dub_ma)
    r3 = r3_decisions(L)

    pend = pd.DataFrame(L.pending, columns=["book", "key", "missing", "proposal_used"])
    counts["pending decisions"] = pend.groupby("book").size().to_dict()
    if not (provisional or check) and len(pend):
        f = os.path.join(OUT_BASE, f"pending_v3_{datetime.now().strftime('%Y-%m-%dT%H%M%S')}.csv")
        pend.to_csv(f, index=False)
        sys.exit(f"Missing: {len(pend)} mandatory decisions (by workbook: {counts['pending decisions']}). "
                 f"List in {f}. For a working run, use --provisional.")

    # 3. reports that enter through round 2
    in_dub = {k for k, v in dub.items() if v["decision"] in ("ENTERS_REVIEW", "ENTERS_REVIEW_AND_MA")}
    in_500 = {k for k, v in e500.items() if v["decision"] in ("INCLUDE_SQ1", "INCLUDE_MA")}
    in_arb = {k for k, v in arb.items() if v["decision"] == "INCLUDE"} - set(st.study_id)
    extra_ids = (in_dub | in_500 | in_arb) - set(st.study_id)
    ov = b09_overrides(e500, t["rep"], L)
    for k, d in b09_transcription(e500).items():
        ov.setdefault(k, {}).update({c: v for c, v in d.items() if c not in ov.get(k, {})})
    counts["B09 inclusions with transcribed comment data"] = len(b09_transcription(e500))
    ov_arb = arbitration_new_reports(in_arb, t["rep"], L)
    ov.update(ov_arb)
    counts["arbitration inclusions without extraction (data from B08 and from screening)"] = len(ov_arb)
    x = C.extra_reports(t, extra_ids, overrides=ov)
    counts["reports with B09 data (assigned PDF of another work)"] = sorted(ov)
    xm = C.mechanical(x, x["_rep"]) if len(x["studies"]) else None
    route = {**{k: "doubtful_2026_10_20" for k in in_dub}, **{k: "extraction_exclusion_review" for k in in_500},
             **{k: "blind_sample_arbitration" for k in in_arb}}
    counts["extra reports requested"] = len(extra_ids)
    counts["extra reports that pass the v1 filter"] = 0 if xm is None else len(xm["studies"])
    counts["extra reports discarded by the v1 filter"] = sorted(x["_dropped"])
    if xm is not None:
        xs, xa = xm["studies"].copy(), xm["ast"].copy()
        xs["entry_route"] = xs.study_id.map(route)
        # doubtful reports: what the extraction does not carry is taken from the reading of 2026-10-20, which the reviewers
        # confirm when deciding in the doubtful-reports workbook (compartment, n of C. tropicalis)
        dw = pd.read_excel(DUB, sheet_name="Review", dtype=object).set_index("ID")
        for i, rr in xs.iterrows():
            sid = rr.study_id
            if route.get(sid) != "doubtful_2026_10_20" or sid not in dw.index:
                continue
            comp = txt(dw.at[sid, "compartment"])
            if V.is_blank(rr.compartments) and comp in C.COMP:
                xs.at[i, "compartments"], xs.at[i, "n_compartments"] = comp, 1
                L.change("doubtful_2026-10-20", sid, "compartments", None, comp, "reading of 2026-10-20",
                         used_proposal=dub[sid]["from_proposal"])
            country = txt(dw.at[sid, "country"])
            if V.is_blank(rr.country) and country:
                iso, reg, multi, _inf, _rule = Dct.map_country(re.sub(r"\s*\([^)]*\)", "", country).strip())
                if iso:
                    xs.at[i, "country"] = country
                    xs.at[i, "country_iso3"] = iso[0] if len(iso) == 1 and not multi else "MULTI"
                    xs.at[i, "who_region"] = reg if not multi else "MULTI"
                    L.change("doubtful_2026-10-20", sid, "country_iso3", rr.country_iso3, xs.at[i, "country_iso3"],
                             "reading of 2026-10-20", used_proposal=dub[sid]["from_proposal"])
            nt = V.safe_int(dw.at[sid, "n_tropicalis"])
            if pd.isna(rr.n_tropicalis) and nt is not None:
                xs.at[i, "n_tropicalis"] = nt
                L.change("doubtful_2026-10-20", sid, "n_tropicalis", None, nt, "reading of 2026-10-20",
                         used_proposal=dub[sid]["from_proposal"])
        ma_ok = dub_ma | {k for k, v in e500.items() if v["decision"] == "INCLUDE_MA"}
        xa = xa[xa.study_id.isin(ma_ok)].copy()      # only the reports that enter the meta-analysis contribute rows
        xa["origin"] = "round2_tidy"
        st = pd.concat([st, xs], ignore_index=True)
        a = pd.concat([a, xa], ignore_index=True)
        for sid in xs.study_id:
            L.change("ronda2", sid, "report", "excluded_or_doubtful", "included", route.get(sid),
                     used_proposal=dub.get(sid, e500.get(sid, {})).get("from_proposal", False))
    nb = b11_to_ast(new_rows, st)
    if len(nb):
        nb = nb[nb.study_id.isin(set(st.study_id))].drop(columns=["year_tmp"])
        a = pd.concat([a, nb], ignore_index=True)
        for r in new_rows:
            L.change("B11", r["row_id"], "row", None, "added", "CONFIRM/CORRECT", r["reviewer"],
                     used_proposal=r["from_proposal"])
    counts["B11 rows added"] = int(len(nb))

    # 3 bis. round 3: reports of the reference-list check, through the same functions as the round-2 extra reports
    xm3 = None
    if r3 is not None:
        ids3 = {k for k, v in r3["reports"].items() if v["decision"] in ("INCLUDE_MA", "INCLUDE_SQ1")}
        t3 = C.load_tidy(R3_TIDY, R3_XLSX)
        x3 = C.extra_reports(t3, ids3, prefix="R3_")
        xm3 = C.mechanical(x3, x3["_rep"]) if len(x3["studies"]) else None
        counts["round 3 reports entering"] = 0 if xm3 is None else len(xm3["studies"])
        counts["round 3 reports discarded by the v1 filter"] = sorted(x3["_dropped"])
        if xm3 is not None:
            xs3, xa3 = xm3["studies"].copy(), xm3["ast"].copy()
            xs3["entry_route"] = R3_ROUTE
            ma3 = {k for k, v in r3["reports"].items() if v["decision"] == "INCLUDE_MA"}
            xa3 = xa3[xa3.study_id.isin(ma3)].copy()
            xa3["origin"] = "round3_tidy"
            xa3 = xa3.set_index("row_id", drop=False)
            gone = set()
            for rid, d in r3["rows"].items():
                if rid not in xa3.index:
                    continue
                if d["action"] == "DELETE":
                    gone.add(rid)
                    L.change("R3_B14", rid, "row", "kept", "excluded", "DELETE", d["reviewer"], d["date"], d["from_proposal"])
                elif d["action"] == "CORRECT":
                    for k, v in d["values"].items():
                        col = NUM_V.get(k) or "interp_raw"
                        old = xa3.at[rid, col]
                        new = int(float(v)) if k in NUM_V else str(v).strip()
                        xa3.at[rid, col] = new
                        if k == "criterion_v":
                            xa3.at[rid, "interp_standard"] = std_of(new) or xa3.at[rid, "interp_standard"]
                        L.change("R3_B14", rid, col, old, new, "CORRECT", d["reviewer"], d["date"], d["from_proposal"])
            xa3 = xa3[~xa3.index.isin(gone)].reset_index(drop=True)
            # a label already used by a report of the review gets the next free letter
            for i, lab in xs3.study_label.items():
                new, k = lab, 0
                while (st.study_label == new).any() or (xs3.drop(index=i).study_label == new).any():
                    new = lab + "abcdefghijklmnopqrstuvwxyz"[k]; k += 1
                if new != lab:
                    L.change("R3_B14", xs3.at[i, "study_id"], "study_label", lab, new, "label already in use")
                    xs3.at[i, "study_label"] = new
            st = pd.concat([st, xs3], ignore_index=True)
            a = pd.concat([a, xa3], ignore_index=True)
            for sid in xs3.study_id:
                L.change("ronda3", sid, "report", "not_in_corpus", "included", R3_ROUTE,
                         used_proposal=r3["reports"][sid]["from_proposal"])
        if r3["pairs"]:
            merges = pd.concat([merges, pd.DataFrame(r3["pairs"])], ignore_index=True)
        counts["round 3 same-collection pairs"] = len(r3["pairs"])

    # 4. reports that leave
    out_b02 = {k for k, v in rep_dec.items() if v["eligible"] == "NO"}
    out_arb = {k for k, v in arb.items() if v["decision"] == "EXCLUDE"}
    leaving = (out_b02 | out_arb) & set(st.study_id)
    for sid in sorted(leaving):
        ec = rep_dec.get(sid, {}).get("ec") or arb.get(sid, {}).get("ec")
        L.change("B02" if sid in out_b02 else "B08", sid, "report", "included", "excluded", ec)
    st = st[~st.study_id.isin(leaving)].copy()
    a = a[~a.study_id.isin(leaving)].copy()
    counts["reports that leave (B02 or arbitration)"] = len(leaving)

    # 5. changes per row: B02 and B07
    a = a.set_index("row_id", drop=False)
    drop_rows = set()
    for rid, d in row_dec.items():
        if rid not in a.index or d["action"] in ("", "OK"):
            continue
        if d["action"] == "EXCLUDE_ROW":
            drop_rows.add(rid)
            L.change("B02", rid, "row", "kept", "excluded", "EXCLUDE_ROW", d["reviewer"], d["date"])
            continue
        for k, v in d["values"].items():
            col = NUM_V.get(k) or {"compartment_v": "compartment", "criterion_v": "interp_raw"}[k]
            old = a.at[rid, col]
            new = int(float(v)) if k in NUM_V else str(v).strip()
            a.at[rid, col] = new
            if k == "criterion_v":
                a.at[rid, "interp_standard"] = std_of(new) or a.at[rid, "interp_standard"]
            L.change("B02", rid, col, old, new, "CORRECT", d["reviewer"], d["date"])
    for rid, d in alloc.items():
        if rid not in a.index:
            continue
        if d["decision"] == "EXCLUDE_ROW":
            drop_rows.add(rid)
        elif d["decision"] == "REASSIGN":
            old = a.at[rid, "compartment"]; a.at[rid, "compartment"] = d["compartment_v"]
            L.change("B07", rid, "compartment", old, d["compartment_v"], "REASSIGN", d["reviewer"], used_proposal=d["from_proposal"])
            continue
        elif d["decision"] == "CORRECT_N":
            old = a.at[rid, "n_tested"]; a.at[rid, "n_tested"] = int(float(d["n_tested_v"]))
            L.change("B07", rid, "n_tested", old, d["n_tested_v"], "CORRECT_N", d["reviewer"], used_proposal=d["from_proposal"])
            continue
        L.change("B07", rid, "row", "kept", "excluded", d["decision"], d["reviewer"], used_proposal=d["from_proposal"])
    a = a[~a.index.isin(drop_rows)].reset_index(drop=True)
    for c in ("n_tested", "n_S", "n_SDD_I", "n_R", "n_NWT"):
        a[c] = pd.to_numeric(a[c], errors="coerce").astype("Int64")
    counts["rows excluded by B02 or B07"] = len(drop_rows)

    # 5 bis. B10 corrections (2026-10-26): MIC that the extraction did not take, and criterion; B02 takes priority
    if os.path.exists(B10_FIX):
        fx = pd.read_csv(B10_FIX, dtype=str)
        a = a.set_index("row_id", drop=False)
        b02_crit = {rid for rid, d in row_dec.items() if "criterion_v" in d["values"]}
        n_mic = n_crit = 0
        for r in fx.to_dict("records"):
            rid = r["row_id"]
            if rid not in a.index:
                continue
            for k, col in B10_MIC.items():
                v = txt(r.get(k))
                num = re.search(r"\d+(?:[.,]\d+)?", v)        # '>256' is recorded as 256 (the limit tested)
                if num and pd.isna(a.at[rid, col]):
                    a.at[rid, col] = float(num.group(0).replace(",", "."))
                    L.change("B10", rid, col, None, v, "record MIC (B10)")
                    n_mic += 1
            cv = txt(r.get("criterion_v"))
            if cv and rid not in b02_crit:
                old = a.at[rid, "interp_raw"]; a.at[rid, "interp_raw"] = cv
                a.at[rid, "interp_standard"] = std_of(cv) or a.at[rid, "interp_standard"]
                L.change("B10", rid, "interp_raw", old, cv, "criterion (B10)")
                n_crit += 1
        a = a.reset_index(drop=True)
        counts["B10 corrections applied"] = {"cim": n_mic, "criterion": n_crit}

    # 6. rules on the rows already corrected
    a = C.apply_row_rules(a, st)
    a["ar20_excluded"] = np.where(a.row_id.isin(ar20), "YES", "NO")
    a["ar20_reason"] = a.row_id.map({k: v["reason"] for k, v in ar20.items()})
    for rid, v in ar20.items():
        L.change("B04", rid, "ar20_excluded", "NO", "YES", v["reason"], v["reviewer"], used_proposal=v["from_proposal"])
    rev = {k for k, v in row_dec.items() if v["reviewed"]} | {r["row_id"] for r in new_rows if not r["from_proposal"]}
    if r3 is not None:
        rev |= {k for k, v in r3["rows"].items() if not v["from_proposal"]}
    a["verified"] = np.where(a.row_id.isin(rev), "YES", "NO")

    # 7. reports: species, exposure, C5, verification condition
    st["species_id_v3"] = st.species_id_proposal
    for sid, v in species.items():
        if sid in set(st.study_id):
            old = st.loc[st.study_id == sid, "species_id_v3"].iloc[0]
            st.loc[st.study_id == sid, "species_id_v3"] = v["species_id"]
            L.change("B05", sid, "species_id_v3", old, v["species_id"], "decision", v["reviewer"], used_proposal=v["from_proposal"])
    # corrected labels (B13); a letter distinguishes two reports of the same author and year
    for sid, v in labels.items():
        if sid in set(st.study_id):
            old = st.loc[st.study_id == sid, "study_label"].iloc[0]
            new, k = v["label"], 0
            while (st.study_label == new).any() and old != new:
                new = v["label"] + "abcdefghijklmnopqrstuvwxyz"[k]
                k += 1
            if new != old:
                st.loc[st.study_id == sid, "study_label"] = new
                L.change("B13", sid, "study_label", old, new, "decision", v["reviewer"], used_proposal=v["from_proposal"])
    st["agronomic_management_v3"] = st.study_id.map({k: v["agronomic"] for k, v in agro.items()})
    has_c5 = st.compartments.fillna("").str.contains("C5")
    st["c5_definition_v3"] = np.where(~has_c5, "not_applicable",
                                      np.where(st.agronomic_management_v3.eq("documented_absent"), "strict", "broad"))
    r3_rev = set() if r3 is None else {k for k, v in r3["reports"].items() if not v["from_proposal"]}
    st["report_verified"] = np.where(st.study_id.isin({k for k, v in rep_dec.items() if v["reviewed"]} | r3_rev),
                                     "YES", "NO")
    st["sq1_only"] = np.where(st.study_id.isin(set(a.study_id)), "NO", "YES")
    ok = a[(a.eligible_r_cbp_v3 == "YES") | (a.eligible_nwt_ecv_v3 == "YES")].study_id
    st["eligible_ma_v3"] = np.where(st.study_id.isin(set(ok)), "YES", "NO")
    counts["v3 reports"], counts["v3 ast rows"] = len(st), len(a)
    counts["reports by route"] = st.entry_route.value_counts().to_dict()
    counts["reports eligible for MA"] = int((st.eligible_ma_v3 == "YES").sum())
    counts["eligible R rows"] = int((a.eligible_r_cbp_v3 == "YES").sum())
    counts["eligible NWT rows"] = int((a.eligible_nwt_ecv_v3 == "YES").sum())
    counts["Rule 4 rows"] = int((a.rule4_excluded == "YES").sum())
    counts["AR20 rows"] = int((a.ar20_excluded == "YES").sum())
    counts["verified rows"] = int((a.verified == "YES").sum())
    counts["merged pairs (B03)"] = len(merges)
    counts["B08 arbitration"] = arb_note

    # other tables, for the reports that remain
    keep = set(st.study_id)
    tabs = {}
    for k in ("molecular", "genotypes", "clade4"):
        parts = [m[k]] + ([xm[k]] if xm is not None else []) + ([xm3[k]] if xm3 is not None else [])
        tabs[k] = pd.concat(parts, ignore_index=True)
        tabs[k] = tabs[k][tabs[k].study_id.isin(keep)]

    # decisions per report (for PRISMA v3)
    rd = []
    for k, v in dub.items():
        rd.append({"report_id": k, "source": "doubtful_2026_10_20", "decision": v["decision"], "ec": v["ec"],
                   "in_v3": "YES" if k in keep else "NO", "from_proposal": "YES" if v["from_proposal"] else "NO"})
    for k, v in e500.items():
        rd.append({"report_id": k, "source": "extraction_exclusion_review", "decision": v["decision"],
                   "ec": v["decision"].replace("EXCLUDE_", "") if v["decision"].startswith("EXCLUDE_EC") else "",
                   "in_v3": "YES" if k in keep else "NO", "from_proposal": "YES" if v["from_proposal"] else "NO"})
    for k in sorted(leaving):
        ec_k = rep_dec.get(k, {}).get("ec") or arb.get(k, {}).get("ec")
        nr = k in out_b02 and str(ec_k).strip().upper() == "NOT_RETRIEVED"   # PDF of another work: not retrieved
        rd.append({"report_id": k, "source": "B02" if k in out_b02 else "B08",
                   "decision": "NOT_RETRIEVED" if nr else "EXCLUDED", "ec": "" if nr else ec_k,
                   "in_v3": "NO", "from_proposal": "NO"})
    # (2026-10-26) report that enters by human decision but shares a PDF with another that already enters: duplicate
    for r in rd:
        if r["report_id"] in x.get("_dup_of", {}) and r["in_v3"] == "NO":
            r["note"] = f"reviewer decision {r['decision']}; same publication as {x['_dup_of'][r['report_id']]}"
            r["decision"], r["ec"] = "DUPLICATE_REPORT", ""
    if r3 is not None:
        for k, v in r3["reports"].items():
            dec = {"INCLUDE_MA": "INCLUDED", "INCLUDE_SQ1": "INCLUDED", "EXCLUDE": "EXCLUDED"}.get(v["decision"], v["decision"])
            rd.append({"report_id": k, "source": R3_ROUTE, "decision": dec, "ec": v["ec"],
                       "in_v3": "YES" if k in keep else "NO", "from_proposal": "YES" if v["from_proposal"] else "NO"})
    rd = pd.DataFrame(rd)
    counts["reports of the extraction flow discarded by the v1 filter"] = len(x["_dropped"])

    for kk, vv in counts.items():
        print(f"{kk}: {vv}")
    if check:
        print("\n--check: nothing was written.")
        return

    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    tag = "_PROVISIONAL" if provisional else ""
    out = os.path.join(OUT_BASE, f"analysis_dataset_v3_{stamp}{tag}")
    if os.path.exists(out):
        sys.exit(f"Already exists {out}")
    os.makedirs(out)
    files = {"studies.csv": st, "ast.csv": a, "molecular.csv": tabs["molecular"], "genotypes.csv": tabs["genotypes"],
             "clade4.csv": tabs["clade4"], "collection_merges.csv": merges, "report_decisions.csv": rd,
             "changes_log.csv": pd.DataFrame(L.changes), "pending.csv": pend}
    for n, df in files.items():
        df.to_csv(os.path.join(out, n), index=False)
    inputs = [C.XLSX, C.EC2_DEC, DUB, DECISIONS] + [f"{C.TIDY}/{f}" for f in ("reports.csv", "ast.csv", "molecular.csv", "genotypes.csv")] \
        + [p for p in BOOK.values()] + ([B08_ARB] if os.path.exists(B08_ARB) else []) \
        + ([r3["path"], R3_XLSX] + [f"{R3_TIDY}/{f}" for f in ("reports.csv", "ast.csv")] if r3 is not None else [])
    log = {"script": os.path.basename(__file__), "mode": "PROVISIONAL" if provisional else "FINAL",
           "run_time": datetime.now().astimezone().isoformat(timespec="seconds"),
           "python": sys.version.split()[0], "pandas": pd.__version__,
           "inputs": {p: C.md5(p) for p in inputs}, "outputs": {n: C.md5(os.path.join(out, n)) for n in files},
           "check_against_v2": "identical", "counts": counts}
    C.write_json(os.path.join(out, "build_log.json"), log)
    print(f"\nDataset v3{' PROVISIONAL' if provisional else ''}: {out}")


if __name__ == "__main__":
    main()
