#!/usr/bin/env python3
"""derive_rob_judgement_v2.py (2026-10-24)

Risk-of-bias judgement per report with the rules 09_phase7_risk_of_bias/rob_rules_v3_2026-10-24.md
on analysis dataset v3. Changes from v1 (all in rules v3):
  - RB4 uses species_id_v3 (corrected identification: negations and partial molecular confirmation, B05);
  - RB6 reads the basis of the version of each row (verification_rules_v1): version declared by document,
    written year or revised-CBP marker; inferred from the publication year or from the declared breakpoints,
    or EUCAST without version; and the branch that v1 did not have written (standard or document absent with no
    inferred version) is now written with the same MIC criterion;
  - RB9 uses agronomic_management_v3 (B07) when it exists; otherwise the phase 7 consensus;
  - RB8 comes from the phase 7 consensus or, for the new reports, from workbook B12 (dedup_rule_final if
    it exists, otherwise dedup_rule); in --provisional a report without RB8 is set to not_retrievable (Unclear) and
    one without editorial status to peer_reviewed, and the output is marked PROVISIONAL;
  - the judgement is per report; the R scripts join it by study_id.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 09_phase7_risk_of_bias/derive_rob_judgement_v2.py --provisional
  conda run --no-capture-output -n ctrop_ma python -B 09_phase7_risk_of_bias/derive_rob_judgement_v2.py
Outputs (never overwritten): 09_phase7_risk_of_bias/results/rob_assessment_v2_<date-time>[_PROVISIONAL].csv
and logs/derive_rob_judgement_v2_<...>.json
"""
import glob
import json
import os
import sys
from collections import Counter
from datetime import datetime

import pandas as pd

sys.path.insert(0, "10_phase8_analysis/scripts")
import verification_rules_v1 as V  # noqa: E402

CONSENSUS = "09_phase7_risk_of_bias/rob_consensus_2026-10-22.xlsx"
SHEETS = ("Consensus_cal1_200", "Consensus_pass_904")
B12_GLOB = "09_phase7_risk_of_bias/round2_2026-10-24/r2_b12_rob_new_reports_*.xlsx"
# (2026-10-27) round 3 (reference-list check): the newest workbook of its folder
B12_R3_GLOB = "09_phase7_risk_of_bias/round3_reference_check_2026-10-27/r3_b12_rob_reference_check_*.xlsx"
RULES_DOC = "09_phase7_risk_of_bias/rob_rules_v3_2026-10-24.md"
OUT_DIR, LOG_DIR = "09_phase7_risk_of_bias/results", "09_phase7_risk_of_bias/logs"
SI, DU, NO, NA = "Yes", "Unclear", "No", "Not applicable"
CRIT = ["RB1", "RB2", "RB3", "RB4", "RB5", "RB6", "RB7", "RB8", "RB9"]
RB8_MAP = {"by_patient": SI, "by_host_or_site": SI, "by_sampling_point": SI,
            "declared_unspecified": SI, "repeated_included": NO, "not_declared": NO,
            "single_sampling": NA, "not_retrievable": DU}
RB1_SI, RB1_NO = {"cross_sectional", "surveillance"}, {"case_report", "case_series"}
RB4_SI, RB4_DU = {"molecular", "MALDI_TOF"}, {"automated", "chromogenic", "biochemical", "conventional"}
DECLARED = {"document", "year_in_string", "revised_marker", "eucast_document", "eucast_year_in_string"}
INFERRED = {"publication_year", "declared_cutoff", "eucast_unversioned"}


def md5(p):
    import hashlib
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def txt(v):
    return "" if V.is_blank(v) else str(v).strip()


def newest_dataset(provisional):
    ds = sorted(d for d in glob.glob("10_phase8_analysis/data/analysis_dataset_v3_*")
                if os.path.isdir(d) and d.endswith("_PROVISIONAL") == provisional)
    if not ds:
        sys.exit("There is no v3 dataset" + (" PROVISIONAL" if provisional else " FINAL"))
    return ds[-1]


def rob_sources(provisional):
    cons = pd.concat([pd.read_excel(CONSENSUS, sheet_name=h).assign(_sheet=h) for h in SHEETS])
    if cons.report_id.duplicated().any():
        sys.exit("A report appears twice in the phase 7 consensus")
    out = {r["report_id"]: {"dedup_rule": txt(r.get("dedup_rule")), "methods_read": txt(r.get("methods_read")),
                            "editorial_status": txt(r.get("editorial_status")),
                            "agronomic_management": txt(r.get("agronomic_management")), "source": r["_sheet"]}
           for r in cons.to_dict("records")}
    books = sorted(glob.glob(B12_GLOB)) + sorted(glob.glob(B12_R3_GLOB))[-1:]
    for f in books:
        b = pd.read_excel(f, sheet_name="reports", dtype=object)
        for r in b.to_dict("records"):
            if r["report_id"] in out:
                sys.exit(f"{r['report_id']} is in phase 7 and in {f}")
            if txt(r.get("agrees")) == "NO" and not txt(r.get("dedup_rule_final")):
                sys.exit(f"{f}, {r['report_id']}: agrees NO without dedup_rule_final from the third reviewer")
            dd = txt(r.get("dedup_rule_final")) or txt(r.get("dedup_rule"))
            if dd and dd not in RB8_MAP:
                sys.exit(f"{f}, {r['report_id']}: dedup_rule not admitted: {dd!r}")
            if dd and dd != "not_declared" and not (txt(r.get("dedup_quote")) and txt(r.get("dedup_page"))):
                sys.exit(f"{f}, {r['report_id']}: dedup_rule {dd} without quote and page (section 3 of the rules)")
            out[r["report_id"]] = {"dedup_rule": dd, "methods_read": txt(r.get("methods_read")),
                                   "editorial_status": txt(r.get("editorial_status")),
                                   "editorial_proposal": txt(r.get("editorial_proposal")),
                                   "agronomic_management": txt(r.get("agronomic_management")),
                                   "source": os.path.basename(f)}
    return out, books


def judge(vals):
    """Section 5 of the rules, unchanged since v2."""
    nos = [k for k, v in vals.items() if v == NO]
    dud = [k for k, v in vals.items() if v == DU]
    if vals.get("RB8") == NO or vals.get("RB4") == NO:
        return "High", "No in " + "/".join(k for k in ("RB4", "RB8") if vals.get(k) == NO)
    rest = [k for k in nos if k not in ("RB4", "RB8")]
    if len(rest) >= 2:
        return "High", "two or more No among the rest: " + ",".join(rest)
    if len(nos) == 1:
        return "Moderate", "one No: " + nos[0]
    if len(dud) >= 3:
        return "Moderate", "three or more Unclear: " + ",".join(dud)
    return "Low", "no No or Unclear" if not dud else f"no No, {len(dud)} Unclear: " + ",".join(dud)


def main():
    provisional = "--provisional" in sys.argv[1:]
    check = "--check" in sys.argv[1:]
    if not os.path.isdir("09_phase7_risk_of_bias"):
        sys.exit("Run from the project root")
    for p in (CONSENSUS, RULES_DOC):
        if not os.path.exists(p):
            sys.exit(f"Missing {p}")
    D = newest_dataset(provisional)
    st = pd.read_csv(f"{D}/studies.csv", low_memory=False)
    a = pd.read_csv(f"{D}/ast.csv", low_memory=False)
    src, books = rob_sources(provisional)
    elig = st[st.eligible_ma_v3 == "YES"]
    missing = [s for s in elig.study_id if s not in src or not src[s]["dedup_rule"]]
    if missing and not provisional:
        sys.exit(f"{len(missing)} eligible reports without RB8 (phase 7 or B12): {missing[:8]}... "
                 "Run make_rob_books_round2_v1.py and fill in the workbook; or use --provisional.")
    rows_by = {k: g for k, g in a.groupby("study_id")}
    out, ramas = [], Counter()
    for s in elig.to_dict("records"):
        sid = s["study_id"]
        g = rows_by.get(sid, a.iloc[0:0])
        c = src.get(sid, {})
        prov = []
        # RB1
        d = txt(s.get("design"))
        rb1 = SI if d in RB1_SI else (NO if d in RB1_NO else DU)
        # RB2
        falt = [k for k in ("country_iso3", "period_start", "period_end", "compartments", "design") if not txt(s.get(k))]
        rb2 = SI if not falt else (DU if len(falt) == 1 else NO)
        # RB3 and RB7
        nt = pd.to_numeric(s.get("n_tropicalis"), errors="coerce")
        maxn = pd.to_numeric(g.n_tested, errors="coerce").max() if len(g) else 0
        if pd.isna(nt) or nt <= 0:
            rb3, rb7 = DU, DU
        else:
            cob = (maxn or 0) / nt
            rb3 = SI if cob >= 0.90 else (DU if cob >= 0.50 else NO)
            rb7 = NO if (pd.to_numeric(g.n_tested, errors="coerce") > nt).any() else SI
        # RB4
        sp = txt(s.get("species_id_v3"))
        rb4 = SI if sp in RB4_SI else (DU if sp in RB4_DU else (NO if sp == "not_specified" else DU))
        # RB5
        met, standard = txt(s.get("ast_method")), txt(s.get("interp_standard"))
        # standard document: the one extracted or the one that the v3 parser identifies in the string
        doc = g.interp_documents.notna().any() or g.regime_basis.isin(["document", "eucast_document"]).any()
        if not met or met == "not_reported" or standard == "not_reported":
            rb5 = NO
        else:
            rb5 = SI if doc else DU
        # RB6 (rules v3, section 2)
        basis = set(g.regime_basis.dropna())
        flags = "|".join(g.regime_flag_v3.fillna("").astype(str))
        inferred = bool(basis & INFERRED) or "inferred_from" in flags
        marked = "pre2012_doc_published_2013plus" in flags
        mic = (g.has_mic == "YES").any()
        declared_all = bool(basis) and basis <= (DECLARED | {"not_clsi_or_eucast", "mixed_standard"}) and \
            bool(basis & DECLARED)
        if standard and standard != "not_reported" and declared_all and not inferred and not marked:
            rb6 = SI
        else:
            rb6 = DU if mic else NO
            if not (inferred or marked):
                ramas["standard_or_document_absent_no_inference"] += 1
        # RB8
        dd = c.get("dedup_rule", "")
        if not dd:
            dd, _ = "not_retrievable", prov.append("RB8 not coded: not_retrievable")
        rb8 = RB8_MAP[dd]
        # RB9
        comps = [x.strip() for x in txt(s.get("compartments")).split(";") if x.strip()]
        if not any(x != "C1" for x in comps):
            rb9 = NA
        else:
            agro = txt(s.get("agronomic_management_v3")) or c.get("agronomic_management", "")
            rb9 = SI if agro in ("documented_present", "documented_absent") else DU
        ed = c.get("editorial_status") or ""
        if not ed:
            ed = c.get("editorial_proposal") or "peer_reviewed"
            prov.append(f"editorial status not coded: {ed}")
        vals = dict(zip(CRIT, (rb1, rb2, rb3, rb4, rb5, rb6, rb7, rb8, rb9)))
        jg, reason = judge(vals)
        out.append({"study_id": sid, "study_label": s.get("study_label"), "year": s.get("year"),
                    "entry_route": s.get("entry_route"), "compartments": s.get("compartments"), **vals,
                    "overall_judgement": jg, "judgement_reason": reason, "rob_alto": "YES" if jg == "High" else "NO",
                    "dedup_rule": dd, "editorial_status": ed, "rb8_source": c.get("source", ""),
                    "provisional": "; ".join(prov)})
    res = pd.DataFrame(out)
    print(f"Dataset: {D}\nReports eligible for MA: {len(elig)}; without coded RB8: {len(missing)}")
    print("Overall judgement:", res.overall_judgement.value_counts().to_dict())
    for k in CRIT:
        print(f"  {k}", res[k].value_counts().to_dict())
    if ramas:
        print("RB6 by the branch written in rules v3:", dict(ramas))
    if check:
        print("--check: nothing was written.")
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S") + ("_PROVISIONAL" if provisional else "")
    f = os.path.join(OUT_DIR, f"rob_assessment_v2_{stamp}.csv")
    if os.path.exists(f):
        sys.exit(f"Already exists {f}")
    res.to_csv(f, index=False)
    log = {"script": os.path.basename(__file__), "mode": "PROVISIONAL" if provisional else "FINAL",
           "run_time": datetime.now().astimezone().isoformat(timespec="seconds"), "dataset": D,
           "inputs": {p: md5(p) for p in [CONSENSUS, RULES_DOC, f"{D}/studies.csv", f"{D}/ast.csv"] + books},
           "outputs": {os.path.basename(f): md5(f)}, "reports": len(res), "without_rb8": len(missing),
           "judgement": res.overall_judgement.value_counts().to_dict(), "rb6_written_branch": dict(ramas),
           "by_criterion": {k: res[k].value_counts().to_dict() for k in CRIT}}
    with open(os.path.join(LOG_DIR, f"derive_rob_judgement_v2_{stamp}.json"), "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False, default=str)
    print("Output:", f)


if __name__ == "__main__":
    main()
