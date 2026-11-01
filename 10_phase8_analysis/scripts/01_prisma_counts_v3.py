#!/usr/bin/env python3
"""01_prisma_counts_v3.py (2026-10-24)

Figures of the PRISMA 2020 diagram, computed from the source files of each phase and from analysis
dataset v3. Every figure of Figure 1 comes from this table; a box without a source stays 'pending' and
is never estimated. Changes from v2 (audit of 2026-10-24, finding C1):
  - the 'R' flow of full-text screening are database records included at title and
    abstract (1,733 by DOI and title or by title; 3 ambiguous ones decided by workbook B06): there are no 'other
    methods' and the right branch of the diagram disappears;
  - not retrieved = sought - full texts obtained + texts that were not the work (PDF of another work
    or truncated, doubtful NOT_RETRIEVED and NOT_DETERMINABLE, excluded at extraction NOT_RETRIEVED);
  - the 316 doubtful and the 500 excluded at extraction are counted by their round-2 decision, with
    their EC code, and not as a block;
  - with a PROVISIONAL v3 dataset, the missing decisions appear as a box of their own and the table is
    marked PROVISIONAL.

  - also writes the per-report list of the excluded reports with their reason and of the not retrieved, taken from
    the same sources as the figures and checked against them (supplementary material, PRISMA 16b).

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/01_prisma_counts_v3.py [--provisional]
Outputs (never overwritten), in 10_phase8_analysis/results:
  prisma_counts_v3_<date-time>[_PROVISIONAL].csv (read by the figure), .xlsx and logs/01_prisma_counts_v3_<...>.json
  prisma_excluded_reports_v3_<date-time>[_PROVISIONAL].csv   one report per row: code, reason and phase
  prisma_not_retrieved_v3_<date-time>[_PROVISIONAL].csv      one record per row: SCREEN_ID and cause
"""
import glob
import hashlib
import json
import os
import platform
import re
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dataset_v3_core as C  # noqa: E402

RIS_FIELDS = "06_phase4_title_abstract_screening/import/screening_record_fields_n22203_2026-10-28.csv"  # extract of the screening RIS used when the RIS is absent (2026-10-28)
IN = {
    "by_file": "02_phase0_raw_corpus/reconciliation/reconciliation_by_file_v2_2026-10-13.csv",
    "chain": "03_phase1_deduplication/results/corpus_definition_report_2026-10-13.txt",
    "ft": "07_phase5_full_text_screening/full_text_screening.xlsx",
    "ex": "08_phase6_data_extraction/data_extraction_tropicalis.xlsx",
    "build_v2": "10_phase8_analysis/data/analysis_dataset_v2_2026-10-23/build_log.json",
    "ec2": "07_phase5_full_text_screening/ec2_decisions_2026-10-23.csv",
    "ris": "06_phase4_title_abstract_screening/import/screening_reviewer_1_reviewer_2_n22203_seed1310202643.ris",
    "cal1": "04_phase2_calibration/results/calibration_CAL1_final_decisions.csv",
    "r_map": "07_phase5_full_text_screening/r_stream_screen_id_map_2026-10-24.csv",
    "b06": "08_phase6_data_extraction/verification/round2_2026-10-24/r2_b06_r_stream_ambiguous.xlsx",
}
RAYYAN_DIR = "06_phase4_title_abstract_screening/rayyan_exports"
OUT_DIR = "10_phase8_analysis/results"
SOURCE_NAMES = {
    "LENS": "Lens.org", "SCOPUS": "Scopus", "PUBMED": "PubMed", "LILACS": "LILACS/BVS",
    "AGRIS": "AGRIS", "CNKI": "CNKI", "DIMENSIONS": "Dimensions", "SCIENCE_DIRECT": "ScienceDirect",
    "Sstage": "J-STAGE", "Google_scholar": "Google Scholar", "Researchsquare": "Research Square",
    "Redalyc": "Redalyc", "VIP": "VIP", "SCIELO": "SciELO", "African_Journals_Online": "African Journals Online",
    "AIRITI": "Airiti Library", "SSRN": "SSRN", "KoreaMed": "KoreaMed",
    "bioRxiv_and_medRxiv": "bioRxiv/medRxiv", "Preprinorg": "Preprints.org",
}
EXCLUSION_LABELS = {
    "EC1": "Not the target species, not disaggregable, or no isolate",
    "EC2": "Identification method not reported",
    "EC3": "Country of origin not identifiable",
    "EC4": "Source not assignable to a compartment",
    "EC6": "Testing method and criterion not reported",
    "EC7": "Denominators not recoverable",
    "EC8": "Reference strains only",
    "EC9": "Activity of new compounds only",
    "EC10": "Industrial or biotechnological use",
    "EC11": "In silico only",
    "EC12": "Overlapping collection reported elsewhere",
    "EC13": "Review, editorial or abstract without data",
    "RETRACTED": "Retracted publication",
    "DUPLICATE_REPORT": "Duplicate record of the same publication",
    "PENDING": "Decision pending (provisional count)",
}
FREE_TEXT_CODES = {
    "Study of an identification method without an assignable source or susceptibility": "EC4",
    "Retracted article; unreliable data (IC7)": "RETRACTED",
}
rows = []


def add(box, item, label, n, source, rule, status="final"):
    rows.append({"box": box, "item": item, "label": label, "n": n, "status": status, "source": source, "rule": rule})


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def chain_number(text, label):
    m = re.search(re.escape(label) + r"\s+(\d+)", text)
    if not m:
        sys.exit(f"Cannot find '{label}' in {IN['chain']}")
    return int(m.group(1))


def newest(pat, provisional=None):
    f = sorted(glob.glob(pat))
    if provisional is not None:
        f = [x for x in f if x.rstrip("/").endswith("_PROVISIONAL") == provisional
             or x.endswith("_PROVISIONAL.csv") == provisional]
    return f[-1] if f else None


def main():
    provisional = "--provisional" in sys.argv[1:]
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    if not os.path.exists(IN["ris"]):   # (2026-10-30) the RIS is not in the public repository: its extract stands in, also in the log
        IN["ris"] = RIS_FIELDS
    for k, p in IN.items():
        if not os.path.exists(p):
            sys.exit(f"Missing input {k}: {p}")
    D = newest("10_phase8_analysis/data/analysis_dataset_v3_*", provisional)
    if not D:
        sys.exit("There is no v3 dataset" + (" PROVISIONAL" if provisional else " FINAL"))
    IN_V3 = {"studies": f"{D}/studies.csv", "report_decisions": f"{D}/report_decisions.csv",
             "build_v3": f"{D}/build_log.json"}
    checks = {}

    # 1. Identification by source and chain to the screening corpus (as in v2)
    bf = pd.read_csv(IN["by_file"])
    bf = bf[bf["in_chain"] == "yes"]
    by_source = bf.groupby("source")["parsed"].sum().sort_values(ascending=False)
    for src, n in by_source.items():
        add("identification", f"source:{src}", SOURCE_NAMES.get(src, src), int(n), IN["by_file"],
            "R1, R2: records in the files of the chain")
    identified = int(by_source.sum())
    txt = open(IN["chain"], encoding="utf-8").read()
    c_ident = chain_number(txt, "records identified (R1, R2)")
    c_r3 = chain_number(txt, "identical copies consolidated (R3)")
    c_resid = chain_number(txt, "corpus records without a counterpart (residual)")
    c_dup = chain_number(txt, "duplicates removed in phase 1")
    c_scr = chain_number(txt, "records for screening")
    identical = c_r3 - c_resid
    add("identification", "total", "Databases", identified, IN["by_file"], "sum of the sources")
    add("removed", "identical_copies", "Identical copies consolidated", identical, IN["chain"],
        "R3 minus the explained residual (harmonised reading)")
    add("removed", "duplicates", "Duplicate records removed", c_dup, IN["chain"], "phase 1 deduplication")
    add("screening", "screened", "Records screened", c_scr, IN["chain"], "title and abstract")
    checks["sources_equal_chain"] = identified == c_ident
    checks["identified_minus_removed_equals_screened"] = identified - identical - c_dup == c_scr

    # 2. Title and abstract
    # (2026-10-30) customizations_log.csv, added on 2026-10-29, is the audit log of the labels, not the export of decisions
    exports = sorted(f for f in os.listdir(RAYYAN_DIR) if f.lower().endswith(".csv") and f != "customizations_log.csv")
    if len(exports) != 1:
        sys.exit(f"Expected a single CSV in {RAYYAN_DIR}, found {len(exports)}")
    f_ray = os.path.join(RAYYAN_DIR, exports[0])
    ray = pd.read_csv(f_ray, encoding="utf-8-sig")
    ray = ray[ray["key"] == "included"].sort_values("article_id")
    if IN["ris"].endswith(".ris"):
        screen_ids = [ln[16:].strip() for ln in open(IN["ris"], encoding="utf-8", errors="replace")
                      if ln.startswith("N1  - SCREEN_ID ")]
    else:  # (2026-10-28) the RIS is not in the public repository; same identifiers, same order
        screen_ids = pd.read_csv(RIS_FIELDS, dtype=str, keep_default_na=False).screen_id.tolist()
    if len(screen_ids) != len(ray) or not ray["article_id"].is_unique:
        sys.exit("The RIS and the Rayyan export do not match one to one")
    decision = dict(zip(screen_ids, ray["value"].astype(int)))
    cal = pd.read_csv(IN["cal1"], encoding="utf-8-sig")
    cal_inc = set(cal.loc[cal["decision_final"] == "Include", "work"])
    cal_exc = int((cal["decision_final"] == "Exclude").sum())
    sought = {o for o, v in decision.items() if v == 1} | cal_inc
    ta_excluded = sum(1 for v in decision.values() if v == -1) + cal_exc
    add("screening", "ta_excluded", "Records excluded", ta_excluded, f_ray, "Rayyan consensus plus the calibration round")
    add("retrieval", "sought", "Reports sought for retrieval", len(sought), f_ray, "title and abstract inclusions")
    checks["screened_equals_excluded_plus_sought"] = c_scr == ta_excluded + len(sought)

    # 3. Full texts obtained: flow O (SCREEN_ID) and flow R (paired with its record)
    ft = pd.read_excel(IN["ft"], sheet_name="All")
    o_ids = set(ft.ID[ft.ID.astype(str).str.startswith("O")])
    rmap = pd.read_csv(IN["r_map"])
    amb = pd.read_excel(IN["b06"], sheet_name="reports", dtype=object)
    pend_amb = 0
    r_to_screen = dict(zip(rmap.R_id, rmap.screen_id))
    for r in amb.to_dict("records"):
        v = str(r.get("decision_screen_id") or "").strip()
        if v and v != "nan":
            r_to_screen[r["R_id"]] = v
        else:
            pend_amb += 1
    r_ids = set(ft.ID[ft.ID.astype(str).str.startswith("R")])
    unmatched = r_ids - set(r_to_screen)
    obtained = o_ids | {r_to_screen[r] for r in r_ids if r in r_to_screen}
    checks["obtained_are_all_ta_inclusions"] = obtained <= sought
    checks["no_record_assessed_twice"] = len(obtained) == len(o_ids) + len(r_ids) - len(unmatched)
    if pend_amb and not provisional:
        sys.exit(f"Missing: {pend_amb} decisions of workbook B06 (ambiguous R flow)")
    # in provisional mode, each ambiguous R counts as a different record obtained
    n_obtained = len(obtained) + len(unmatched)
    not_obtained = len(sought) - n_obtained
    add("retrieval", "not_obtained", "Full text not obtained", not_obtained, IN["ft"],
        "sought minus records with a full text (R stream matched to its record)",
        "provisional" if pend_amb else "final")

    # 4. Construction: v2 (truncated, another work, inferred country, duplicates) and EC2 triage
    steps = dict((k, v) for k, v in json.load(open(IN["build_v2"], encoding="utf-8"))["log"])
    truncated = steps["Included in the extraction"] - steps["Without truncated PDF"]
    wrong_doc = steps["Without truncated PDF"] - steps["Without PDF of another work"]
    ec3_build = steps["Without PDF of another work"] - steps["Without country inferred from the affiliation (EC3)"]
    dup_reports = steps["Without country inferred from the affiliation (EC3)"] - steps["Without duplicate records of the same PDF"]
    tri = pd.read_csv(IN["ec2"], encoding="utf-8-sig")
    tri_ids = set(tri.loc[tri["group"].isin(["B_refers_to_other_source", "D_generic_no_method"]), "study_id"])
    n_tri = len(tri_ids)
    # the same steps, report by report, with the filters of the construction (dataset_v3_core)
    rep0 = pd.read_csv(os.path.join(C.TIDY, "reports.csv"), low_memory=False)
    s0 = rep0[rep0.extraction_decision == "INCLUDE"]
    s1 = s0[s0.pdf_status != "truncated"]
    s2 = s1[~(s1.pdf_status.eq("wrong_document_per_notes") | s1.pdf_identical_group.isin(C.NON_ARTICLE_PDF_GROUPS))]
    s3 = s2[s2.country_inferred_flag != True]  # noqa: E712
    _, _, dup_ids = C.select_reports(rep0)
    ids_wrong = set(s0.report_id) - set(s2.report_id)
    ids_ec3 = set(s2.report_id) - set(s3.report_id)
    v2log = json.load(open(IN["build_v2"], encoding="utf-8"))
    checks["build_steps_reproduced"] = (len(s0), len(s1), len(s2), len(s3)) == (
        steps["Included in the extraction"], steps["Without truncated PDF"], steps["Without PDF of another work"],
        steps["Without country inferred from the affiliation (EC3)"])
    checks["duplicates_reproduced"] = (set(dup_ids) == set(v2log["dropped_duplicates"])
                                       and len(dup_ids) == steps["Without country inferred from the affiliation (EC3)"]
                                       - steps["Without duplicate records of the same PDF"] - n_tri)
    checks["ec2_triage_reproduced"] = tri_ids == set(v2log["ec2_triage_2026-10-23"]["excluded"])

    # 5. Round-2 decisions (doubtful, excluded at extraction, B02, arbitration)
    rd = pd.read_csv(IN_V3["report_decisions"])
    dub = rd[rd.source == "doubtful_2026_10_20"]
    e5 = rd[rd.source == "extraction_exclusion_review"]
    dub_nr = int(dub.decision.isin(["NOT_RETRIEVED", "NOT_DETERMINABLE"]).sum())
    e5_nr = int((e5.decision == "NOT_RETRIEVED").sum())
    b02 = rd[rd.source == "B02"]
    b02_nr = int((b02.decision == "NOT_RETRIEVED").sum())   # (2026-10-26) PDF of another work found in B02
    r4 = rd[rd.source == "rescreen_b15_2026_10_29"]     # (2026-10-30) round 4: re-reading of the exclusions (workbook B15)
    r4_nr = int((r4.decision == "NOT_RETRIEVED").sum())
    not_retrieved = not_obtained + truncated + wrong_doc + dub_nr + e5_nr + b02_nr + r4_nr
    add("retrieval", "wrong_or_truncated", "Full text was another work or truncated", truncated + wrong_doc,
        IN["build_v2"], "PDF of another work or truncated, among extraction inclusions")
    add("retrieval", "doubtful_not_retrieved", "Doubtful reports without the correct full text", dub_nr,
        IN_V3["report_decisions"], "doubtful review: NOT_RETRIEVED or NOT_DETERMINABLE")
    add("retrieval", "extraction_not_retrieved", "Extraction-stage reports without the correct full text", e5_nr,
        IN_V3["report_decisions"], "B09: NOT_RETRIEVED")
    add("retrieval", "verification_not_retrieved", "Reports whose full text was another work, found at row verification",
        b02_nr, IN_V3["report_decisions"], "B02: NOT_RETRIEVED")
    add("retrieval", "rescreen_not_retrieved", "Excluded reports whose full text was another work, found at the re-reading",
        r4_nr, IN_V3["report_decisions"], "B15: NOT_RETRIEVED")
    add("retrieval", "not_retrieved", "Reports not retrieved", not_retrieved, IN["ft"], "sum of the lines above")
    to_screen = lambda i: i if str(i).startswith("O") else r_to_screen.get(i, "")  # noqa: E731
    nr = ([{"id": i, "screen_id": i, "cause": "not_obtained"} for i in sorted(sought - obtained)]
          + [{"id": i, "screen_id": to_screen(i), "cause": "wrong_or_truncated"} for i in sorted(ids_wrong)]
          + [{"id": i, "screen_id": to_screen(i), "cause": "doubtful_not_retrieved"}
             for i in sorted(dub.report_id[dub.decision.isin(["NOT_RETRIEVED", "NOT_DETERMINABLE"])])]
          + [{"id": i, "screen_id": to_screen(i), "cause": "extraction_not_retrieved"}
             for i in sorted(e5.report_id[e5.decision == "NOT_RETRIEVED"])]
          + [{"id": i, "screen_id": to_screen(i), "cause": "verification_not_retrieved"}
             for i in sorted(b02.report_id[b02.decision == "NOT_RETRIEVED"])]
          + [{"id": i, "screen_id": to_screen(i), "cause": "rescreen_not_retrieved"}
             for i in sorted(r4.report_id[r4.decision == "NOT_RETRIEVED"])])
    nr = pd.DataFrame(nr)
    # in provisional mode, sought - obtained also carries the candidate records of the undecided ambiguous R
    checks["not_retrieved_list_matches"] = (len(nr) == not_retrieved + (len(unmatched) if provisional else 0)
                                            and not nr.id.duplicated().any())
    nr["status"] = "final"
    if provisional and unmatched:
        cand = set(amb.loc[amb.R_id.isin(unmatched), "screen_id_candidates"].astype(str).str.split(r"[;, ]+").explode())
        nr.loc[nr.id.isin(cand), "status"] = "provisional_ambiguous_R"
    assessed = len(sought) - not_retrieved
    add("eligibility", "assessed", "Reports assessed for eligibility", assessed, IN["ft"], "sought minus not retrieved")

    reasons = ft.loc[ft["Decision"] == "EXCLUDE", ["ID", "Main reason"]].copy()
    reasons["code"] = reasons["Main reason"].astype(str).str.strip().str.extract(r"^(EC\d{1,2})", expand=False)
    reasons["code"] = reasons.code.fillna(reasons["Main reason"].astype(str).str.strip().map(FREE_TEXT_CODES))
    if reasons.code.isna().any():
        sys.exit("Reasons without code: " + "; ".join(sorted(set(reasons.loc[reasons.code.isna(), "Main reason"]))))
    arb = rd[rd.source == "B08"]          # exits by arbitration (entries by arbitration do not subtract here)
    counts = reasons.code.value_counts().to_dict()
    st = pd.read_csv(IN_V3["studies"], low_memory=False)
    revived = set(st.study_id[st.entry_route.isin(["blind_sample_arbitration", "rescreen_b15_2026_10_29"])])
    revived |= set(r4.report_id[r4.decision == "NOT_RETRIEVED"])
    # the confirmed exclusions of B15 keep the report and take the code that the reviewers recorded
    r4_ec = r4[r4.decision == "EXCLUSION_CONFIRMED"].set_index("report_id").ec.dropna().to_dict()
    new_code = reasons.ID.map(r4_ec)
    reasons["code"] = new_code.fillna(reasons.code)
    counts = reasons.code.value_counts().to_dict()
    for sid in revived & set(reasons.ID):
        c = reasons.loc[reasons.ID == sid, "code"].iloc[0]
        counts[c] -= 1
    counts["EC3"] = counts.get("EC3", 0) + ec3_build
    counts["EC2"] = counts.get("EC2", 0) + n_tri
    counts["DUPLICATE_REPORT"] = dup_reports - n_tri
    dup_r2 = sorted(rd.report_id[rd.decision == "DUPLICATE_REPORT"])   # (2026-10-26) round 2, same PDF as another included report
    counts["DUPLICATE_REPORT"] += len(dup_r2)
    for part in (dub[dub.decision == "REMAINS_EXCLUDED"], e5[e5.decision.str.startswith("EXCLUDE_EC")],
                 b02[b02.decision == "EXCLUDED"], arb):
        for ec in part.ec.fillna(""):
            m = re.search(r"EC\d{1,2}", str(ec))
            k = m.group(0) if m else "PENDING"
            counts[k] = counts.get(k, 0) + 1
    n_pend = int((e5.decision == "EXCLUDE_UNREVIEWED").sum())
    if n_pend:
        counts["PENDING"] = counts.get("PENDING", 0) + n_pend
    for k, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        if n:
            add("excluded", k, EXCLUSION_LABELS.get(k, k), int(n), IN["ft"] + " + ronda 2", "single main reason per report",
                "provisional" if k == "PENDING" else "final")
    excluded = sum(counts.values())
    ex = [{"report_id": i, "code": c, "stage": "full_text_screening"}
          for i, c in zip(reasons.ID, reasons.code) if i not in revived]
    ex += [{"report_id": i, "code": "EC3", "stage": "extraction_country_inferred_from_affiliation"} for i in sorted(ids_ec3)]
    ex += [{"report_id": i, "code": "EC2", "stage": "species_identification_triage_2026_10_23"} for i in sorted(tri_ids)]
    ex += [{"report_id": i, "code": "DUPLICATE_REPORT", "stage": "same_pdf_as_another_report"} for i in sorted(dup_ids)]
    ex += [{"report_id": i, "code": "DUPLICATE_REPORT", "stage": "round2_same_pdf_as_included_report"} for i in dup_r2]
    for part, stage in ((dub[dub.decision == "REMAINS_EXCLUDED"], "round2_doubtful_review"),
                        (e5[e5.decision.str.startswith("EXCLUDE_EC")], "round2_extraction_exclusion_review"),
                        (b02[b02.decision == "EXCLUDED"], "round2_row_verification_B02"), (arb, "round2_blind_sample_arbitration")):
        for i, e in zip(part.report_id, part.ec.fillna("")):
            m = re.search(r"EC\d{1,2}", str(e))
            ex.append({"report_id": i, "code": m.group(0) if m else "PENDING", "stage": stage})
    ex += [{"report_id": i, "code": "PENDING", "stage": "round2_extraction_exclusion_review_pending"}
           for i in sorted(e5.report_id[e5.decision == "EXCLUDE_UNREVIEWED"])]
    ex = pd.DataFrame(ex)
    ex["label"] = ex.code.map(EXCLUSION_LABELS).fillna(ex.code)
    ex["screen_id"] = ex.report_id.map(lambda i: i if str(i).startswith("O") else r_to_screen.get(i, ""))
    ex["status"] = ex.code.map(lambda c: "provisional" if c == "PENDING" else "final")
    checks["excluded_list_matches_counts"] = (ex.code.value_counts().to_dict() == {k: v for k, v in counts.items() if v}
                                              and not ex.report_id.duplicated().any())

    # (2026-10-27) identification via other methods: reference lists of four previous reviews (round 3)
    r3 = rd[rd.source == "reference_check_2026_10_27"]
    r3_included = int((r3.in_v3 == "YES").sum())
    f_cand = sorted(glob.glob("07_phase5_full_text_screening/reference_check_2026-10-27/reference_check_candidates_v1_*.csv"))
    if len(r3):
        cand = pd.read_csv(f_cand[-1])
        r3_nr = int((r3.decision == "NOT_RETRIEVED").sum())
        add("other_methods", "identified", "Records identified from citation searching", len(cand), f_cand[-1],
            "references of four previous reviews not retrieved by the search, primary studies on title or open text")
        add("other_methods", "sought", "Reports sought for retrieval", len(cand), f_cand[-1], "all candidates")
        add("other_methods", "not_retrieved", "Reports not retrieved", r3_nr, IN_V3["report_decisions"], "no open or free full text")
        add("other_methods", "assessed", "Reports assessed for eligibility", len(cand) - r3_nr, IN_V3["report_decisions"],
            "sought minus not retrieved")
        r3_ex = r3[r3.decision == "EXCLUDED"]
        for code, n in r3_ex.ec.fillna("PENDING").value_counts().items():
            add("other_methods", f"excluded_{code}", EXCLUSION_LABELS.get(code, code), int(n), IN_V3["report_decisions"],
                "single main reason per report")
        add("other_methods", "included", "Reports of included studies", r3_included, IN_V3["report_decisions"],
            "included reports found by citation searching (counted in the included totals)")
        checks["other_methods_balance"] = len(cand) - r3_nr - len(r3_ex) == r3_included
    included_reports = len(st)
    add("included", "reports", "Reports of included studies", included_reports, IN_V3["studies"], "analysis dataset v3")
    add("included", "reports_sq1_only", "Reports contributing to the compartment distribution only",
        int((st.sq1_only == "YES").sum()), IN_V3["studies"], "no susceptibility rows (SQ1)")
    f_ec12 = newest(os.path.join(OUT_DIR, "ec12_collections_v2_*.csv"), provisional)
    if f_ec12:
        stamp4 = os.path.basename(f_ec12)[len("ec12_collections_v2_"):-4]
        lg = os.path.join(OUT_DIR, "logs", f"04_ma_input_v2_{stamp4}.json")
        if not os.path.exists(lg) or json.load(open(lg, encoding="utf-8"))["inputs"]["studies"]["path"] != IN_V3["studies"]:
            sys.exit(f"{f_ec12} was not built with {D}: run 04_ma_input_v2.py on that dataset first")
        ec12 = pd.read_csv(f_ec12)
        ec12 = ec12[ec12.report_id.isin(set(st.study_id))]
        collections = included_reports - len(ec12) + ec12.collection_id.nunique()
        add("included", "studies", "Studies included (independent collections)", collections, f_ec12,
            "reports of the same collection counted once (AR1 and round-2 merges)")
    else:
        add("included", "studies", "Studies included (independent collections)", None, "", "", "pending")
    f_res = newest(os.path.join(OUT_DIR, "ma_results_v3_*.csv"), provisional)
    f_mi = newest(os.path.join(OUT_DIR, "ma_input_v2_*.csv"), provisional)
    if f_res and f_mi:
        res, mi = pd.read_csv(f_res), pd.read_csv(f_mi, low_memory=False)
        keys = ["compartment", "agent", "outcome", "regime_stratum"]
        pooled = res.loc[res["status"] == "pooled", keys]
        in_ma = mi[mi["main"].astype(str) == "True"].merge(pooled, on=keys)
        add("included", "meta_analysis", "Collections contributing to a pooled estimate",
            in_ma.collection_id.nunique(), f_res, "strata pooled under AR12 and AR18")
    else:
        add("included", "meta_analysis", "Collections contributing to a pooled estimate", None, "",
            "needs ma_results_v3 (06_ma_marginal_v3.R)", "pending")
    checks["assessed_minus_excluded_equals_included"] = assessed - excluded == included_reports - r3_included
    # in provisional mode, the only unpaired R admitted are the ambiguous ones that B06 has not decided yet
    checks["every_r_report_matched"] = not unmatched or (provisional and len(unmatched) <= pend_amb)
    if not all(checks.values()):
        for k, v in checks.items():
            print(f"  {'OK   ' if v else 'FAIL'} {k}")
        sys.exit("The chain does not reconcile: the table is not written")

    tab = pd.DataFrame(rows)
    tab["n"] = tab["n"].astype("Int64")
    os.makedirs(os.path.join(OUT_DIR, "logs"), exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S") + ("_PROVISIONAL" if provisional else "")
    f_csv = os.path.join(OUT_DIR, f"prisma_counts_v3_{stamp}.csv")
    f_xlsx = os.path.join(OUT_DIR, f"prisma_counts_v3_{stamp}.xlsx")
    f_ex = os.path.join(OUT_DIR, f"prisma_excluded_reports_v3_{stamp}.csv")
    f_nr = os.path.join(OUT_DIR, f"prisma_not_retrieved_v3_{stamp}.csv")
    for f in (f_csv, f_xlsx, f_ex, f_nr):
        if os.path.exists(f):
            sys.exit(f"Already exists {f}: not overwritten")
    tab.to_csv(f_csv, index=False)
    tab.to_excel(f_xlsx, index=False, sheet_name="prisma_counts")
    ex[["report_id", "screen_id", "code", "label", "stage", "status"]].to_csv(f_ex, index=False)
    nr[["id", "screen_id", "cause", "status"]].to_csv(f_nr, index=False)
    log = {"script": os.path.basename(__file__), "mode": "PROVISIONAL" if provisional else "FINAL",
           "run_time": datetime.now().astimezone().isoformat(timespec="seconds"),
           "python": platform.python_version(), "pandas": pd.__version__,
           "inputs": {k: {"path": p, "md5": md5(p)} for k, p in {**IN, **IN_V3}.items()},
           "outputs": {os.path.basename(f): md5(f) for f in (f_csv, f_xlsx, f_ex, f_nr)},
           "tidy_reports": {"path": os.path.join(C.TIDY, "reports.csv"), "md5": md5(os.path.join(C.TIDY, "reports.csv"))},
           "checks": checks, "pending_items": tab.loc[tab["status"] != "final", "item"].tolist(),
           "b06_pending": pend_amb}
    with open(os.path.join(OUT_DIR, "logs", f"01_prisma_counts_v3_{stamp}.json"), "w", encoding="utf-8") as f:
        json.dump(log, f, indent=1, ensure_ascii=False, default=str)
    show = tab[~tab["item"].str.startswith("source:")][["box", "label", "n", "status"]]
    print("Dataset:", D)
    print(show.to_string(index=False))
    print("\nClosure checks:")
    for k, v in checks.items():
        print(f"  {'OK   ' if v else 'FAIL'} {k}")
    print(f"\nTable: {f_csv}\nWorkbook: {f_xlsx}\nExcluded by report: {f_ex} ({len(ex)})\n"
          f"Not retrieved by record: {f_nr} ({len(nr)})")


if __name__ == "__main__":
    main()
