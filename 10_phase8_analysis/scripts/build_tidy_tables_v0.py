#!/usr/bin/env python3
"""Build the tidy (long, relational) tables of the C. tropicalis review from the
matrices, v0, 2026-10-20.

Inputs (never modified):
  07_phase5_full_text_screening/full_text_screening.xlsx
  08_phase6_data_extraction/data_extraction_tropicalis.xlsx
  pdf integrity lists (identical-hash groups and truncated files)

Outputs (CSV, UTF-8, one table per file, plus one .xlsx with all of them):
  reports, ast, mic_summary, molecular, genotypes, collection_candidates,
  dictionaries (agent, method, interpretive criterion, country), build_log.json

Nothing produced here is a verified datum. Every row carries the extraction
flags and a verification_status column that starts as 'pending'. The analysis
sets are built later and only from rows a human has verified (protocol rule:
no figure enters the meta-analysis unless a human has seen it in the source).

Usage:
  python3 build_tidy_tables_v0.py --screening PATH --extraction PATH \
      --pdf-groups PATH --truncated PATH [--doubtful-review PATH] --out DIR
"""
import argparse, hashlib, json, os, re, sys
from datetime import date
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dictionaries as D

def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def nn(x):
    return None if (x is None or (isinstance(x, float) and np.isnan(x))) else x

def norm_title(t):
    t = str(t or "").lower()
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"[^\w\s]", " ", t)
    return set(w for w in t.split() if len(w) > 2)

def jaccard(a, b):
    return len(a & b) / len(a | b) if (a and b) else 0.0

def period_from_text(p):
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return (None, None)
    yrs = [int(y) for y in re.findall(r"(?<!\d)(19[5-9]\d|20[0-3]\d)(?!\d)", str(p))]
    if not yrs:
        return (None, None)
    return (min(yrs), max(yrs))

WRONG_PDF = r"does not correspond|corresponds to another|another article|another document|wrong pdf|mistaken pdf|downloaded full text corresponds|is not the article|writing manual|style manual|statute|bylaws"
TABLES_MISSING = r"not in the text|not extracted|absent in the text|absent from the text|not legible|illegible|unreadable|scanned"
PARTIAL_TEXT = r"only contains|contains only|only available|only the first|only the diagram|only the annex|only the appendix|review report"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screening", required=True)
    ap.add_argument("--extraction", required=True)
    ap.add_argument("--pdf-groups", required=True)
    ap.add_argument("--truncated", required=True)
    ap.add_argument("--doubtful-review", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    scr = pd.read_excel(a.screening, sheet_name="All")
    ec12 = pd.read_excel(a.screening, sheet_name="Possible duplicates EC12")
    X = pd.read_excel(a.extraction, sheet_name=None)
    est, res, mol, gen = X["Studies"], X["Resistance"], X["Molecular"], X["Genotype"]
    grp = pd.read_csv(a.pdf_groups)
    trunc = set(pd.read_csv(a.truncated)["ID"])

    # ------------------------------------------------------------------ reports
    s = scr.set_index("ID")
    rep = est.copy()
    rep = rep.merge(scr[["ID", "Decision", "Meta-analysis", "Main reason", "Exclusions",
                         "Programme/institution", "Identification", "Notes"]], on="ID", how="left")
    # unique study labels: "Author Year", suffixed a, b, c when repeated
    lab = rep["Study"].astype(str)
    cnt = lab.groupby(lab).cumcount()
    tot = lab.map(lab.value_counts())
    rep["study_label"] = np.where(tot > 1, lab + cnt.map(lambda i: "abcdefghijklmnopqrstuvwxyz"[i] if i < 26 else str(i)), lab)

    # pdf integrity
    g_by_id = dict(zip(grp.ID, grp.grp))
    members = grp.groupby("grp")["ID"].apply(list).to_dict()
    titles = dict(zip(scr.ID, scr["Title"]))
    def shared(i):
        gid = g_by_id.get(i)
        if gid is None:
            return (None, None, None)
        others = [o for o in members[gid] if o != i]
        sim = max(jaccard(norm_title(titles.get(i)), norm_title(titles.get(o))) for o in others)
        return (int(gid), "; ".join(others), round(sim, 2))
    sh = rep["ID"].map(shared)
    rep["pdf_identical_group"] = [x[0] for x in sh]
    rep["pdf_identical_with"] = [x[1] for x in sh]
    rep["pdf_identical_title_similarity"] = [x[2] for x in sh]
    notes = (rep["change_reason"].fillna("") + " || " + rep["comments"].fillna("")).str.lower()
    rep["pdf_truncated"] = rep["ID"].isin(trunc)
    rep["pdf_wrong_per_notes"] = notes.str.contains(WRONG_PDF, regex=True)
    rep["tables_missing_per_notes"] = notes.str.contains(TABLES_MISSING, regex=True)
    rep["partial_text_per_notes"] = notes.str.contains(PARTIAL_TEXT, regex=True)
    def pdf_status(r):
        if r.pdf_truncated: return "truncated"
        if r.pdf_wrong_per_notes: return "wrong_document_per_notes"
        if pd.notna(r.pdf_identical_group):
            return "identical_pdf_similar_titles" if (r.pdf_identical_title_similarity or 0) >= 0.5 else "identical_pdf_different_titles"
        if r.partial_text_per_notes: return "partial_text_per_notes"
        if r.tables_missing_per_notes: return "tables_or_text_not_captured_per_notes"
        return "no_flag"
    rep["pdf_status"] = rep.apply(pdf_status, axis=1)

    # geography
    cm = rep["country"].map(D.map_country)
    rep["country_iso3"] = [";".join(x[0]) if x[0] else None for x in cm]
    rep["who_region"] = [x[1] for x in cm]
    rep["multinational"] = [x[2] for x in cm]
    rep["country_inferred_flag"] = [x[3] for x in cm]
    rep["country_rule"] = [x[4] for x in cm]

    # doubtful review (optional)
    if a.doubtful_review and os.path.exists(a.doubtful_review):
        dv = pd.read_csv(a.doubtful_review)
        if "proposed_verdict" in dv.columns and "verdict" not in dv.columns:
            dv = dv.rename(columns={"proposed_verdict": "verdict"})
        keep = [c for c in ["ID", "verdict", "exclusion_code", "pdf_matches", "pdf_corresponde", "pdf_is_of", "confidence"] if c in dv.columns]
        rep = rep.merge(dv[keep].rename(columns={"verdict": "doubtful_review_verdict", "exclusion_code": "doubtful_review_ec",
                                                  "pdf_matches": "doubtful_review_pdf_matches", "pdf_corresponde": "doubtful_review_pdf_matches",  # column renamed on 2026-10-28
                                                  "pdf_is_of": "doubtful_review_pdf_is",
                                                  "confidence": "doubtful_review_confidence"}), on="ID", how="left")

    reports = pd.DataFrame({
        "report_id": rep["ID"], "corpus_n": rep["No."], "study_label": rep["study_label"],
        "title": rep["Title"], "year": rep["Publication year"], "journal": rep["Journal"], "doi": rep["DOI"],
        "pdf_file": rep["PDF file"], "pdf_status": rep["pdf_status"],
        "pdf_identical_group": rep["pdf_identical_group"], "pdf_identical_with": rep["pdf_identical_with"],
        "pdf_identical_title_similarity": rep["pdf_identical_title_similarity"],
        "ft_screening_decision": rep["Decision"], "ft_screening_ma": rep["Meta-analysis"],
        "ft_screening_reason": rep["Main reason"], "ft_screening_ec": rep["Exclusions"],
        "extraction_decision": rep["decision_final"], "extraction_change_reason": rep["change_reason"],
        "extraction_ma": rep["meta_analysis_eligible"], "extraction_ic8": rep["ic8"], "extraction_confidence": rep["confidence"],
        "design_raw": rep["design"], "setting_raw": rep["environment"], "programme_institution_raw": rep["Programme/institution"],
        "multicentre_raw": rep["multicentrico"], "n_centres": rep["n_centres"],
        "country_raw": rep["country"], "country_iso3": rep["country_iso3"], "who_region": rep["who_region"],
        "multinational": rep["multinational"], "country_inferred_flag": rep["country_inferred_flag"],
        "region_city_raw": rep["region_city"], "period_start": rep["period_start"], "period_end": rep["period_end"],
        "compartments_raw": rep["compartments"], "sources_raw": rep["source_details"], "population_raw": rep["population"],
        "infection_type_raw": rep["infection_type"], "n_tropicalis_total": rep["n_tropicalis_total"],
        "n_candida_total": rep["n_candida_total"], "species_id_raw": rep["identification_method"],
        "ast_method_raw": rep["susceptibility_method"], "interp_document_raw": rep["standard_document"],
        "interp_version_raw": rep["standard_version"], "breakpoint_type_raw": rep["breakpoint_type"],
        "azole_exposure_raw": rep["azole_exposure"], "agricultural_azoles_tested_raw": rep["agricultural_fungicides_tested"],
        "clade4_mentioned": rep["clado4"], "n_rows_ast": rep["resistance_rows"], "n_rows_molecular": rep["molecular_rows"],
        "n_rows_genotype": rep["genotype_rows"], "extraction_notes": rep["comments"],
    })
    for c in ["doubtful_review_verdict", "doubtful_review_ec", "doubtful_review_pdf_matches", "doubtful_review_pdf_is", "doubtful_review_confidence"]:
        if c in rep.columns:
            reports[c] = rep[c]
    # fields to be completed by humans (empty in v0)
    for c in ["decision_human", "decision_human_reason", "collection_id", "research_group_id", "editorial_status",
              "species_id_category", "molecular_confirmation_prop", "dedup_rule_declared",
              "azole_exposure_clinical_documented", "azole_exposure_agricultural_documented",
              "verification_status", "verified_by", "verified_date"]:
        reports[c] = "pending" if c == "verification_status" else None
    reports.to_csv(os.path.join(a.out, "reports.csv"), index=False)

    # ---------------------------------------------------------------------- ast
    yr = dict(zip(est.ID, est["Publication year"]))
    dec = dict(zip(est.ID, est["decision_final"]))
    pst = dict(zip(reports.report_id, reports.pdf_status))
    rows = []
    for i, r in res.reset_index(drop=True).iterrows():
        agent_std, agent_class, per_agent, agent_rule = D.map_agent(nn(r["antifungico"]))
        ip = D.parse_interpretive(nn(r["standard"]), nn(yr.get(r["ID"])))
        p0, p1 = period_from_text(nn(r["period"]))
        if p0 is None:
            p0, p1 = nn(r["Period start"]), nn(r["Period end"])
        n, sS, sI, sR, nwt = (nn(r[c]) for c in ["n_tested", "n_S", "n_SDD_I", "n_R", "n_NWT"])
        cats = [v for v in (sS, sI, sR) if v is not None]
        if n is None:
            chk = "no_denominator"
        elif len(cats) == 3:
            chk = "sum_ok" if sum(cats) == n else ("sum_gt_n" if sum(cats) > n else "sum_lt_n")
        elif len(cats) == 0:
            chk = "no_categories"
        else:
            chk = "partial_categories"
        rows.append({
            "ast_row_id": f"A{i+1:05d}", "report_id": r["ID"], "compartment": nn(r["compartment"]),
            "source_raw": nn(r["source"]), "period_raw": nn(r["period"]), "period_start": p0, "period_end": p1,
            "agent_raw": nn(r["antifungico"]), "agent_std": agent_std, "agent_class": agent_class, "per_agent": per_agent,
            "method_raw": nn(r["method"]), "method_cat": D.map_method(nn(r["method"])),
            "interp_raw": nn(r["standard"]), **ip,
            "n_tested": n, "n_S": sS, "n_SDD_I": sI, "n_R": sR, "n_NWT": nwt, "category_check": chk,
            "mic_range": nn(r["mic_range"]), "mic50": nn(r["cmi50"]), "mic90": nn(r["cmi90"]), "mic_gm": nn(r["cmi_mg"]),
            "unit": nn(r["unit"]), "note_raw": nn(r["note"]),
            "extraction_decision": dec.get(r["ID"]), "extraction_ma_row": nn(r["Eligible for MA"]), "pdf_status": pst.get(r["ID"]),
        })
    ast = pd.DataFrame(rows)
    comp_ok = ast["compartment"].isin(["C1", "C2", "C3", "C4", "C5", "C6"])
    pdf_ok = ast["pdf_status"].isin(["no_flag", "tables_or_text_not_captured_per_notes"])
    base = (ast.extraction_decision == "INCLUDE") & comp_ok & ast.per_agent & ast.n_tested.notna() & (ast.n_tested > 0) & pdf_ok \
        & (ast.unit.fillna("").str.contains("mm") == False)
    ast["candidate_secondary_cbp"] = base & ast.n_R.notna() & ast.bp_type.fillna("").str.contains("CBP") \
        & ast.interp_standard.isin(["CLSI", "EUCAST"])
    ast["candidate_primary_ecv"] = base & ast.n_NWT.notna() & ast.bp_type.fillna("").str.contains("ECV")
    ast["mic_only"] = ast[["n_S", "n_SDD_I", "n_R", "n_NWT"]].isna().all(axis=1) & ast[["mic_range", "mic50", "mic90", "mic_gm"]].notna().any(axis=1)
    for c in ["n_tested_verified", "n_R_verified", "n_NWT_verified", "location_in_report", "verification_status", "verified_by", "verified_date"]:
        ast[c] = "pending" if c == "verification_status" else None
    ast.to_csv(os.path.join(a.out, "ast.csv"), index=False)
    ast.loc[ast[["mic_range", "mic50", "mic90", "mic_gm"]].notna().any(axis=1),
            ["ast_row_id", "report_id", "compartment", "agent_std", "method_cat", "n_tested", "mic_range", "mic50", "mic90", "mic_gm", "unit"]
            ].to_csv(os.path.join(a.out, "mic_summary.csv"), index=False)

    # ---------------------------------------------------------------- molecular
    mrows = []
    for i, r in mol.reset_index(drop=True).iterrows():
        pdx = D.parse_determinants(nn(r["gen"]), nn(r["alteration"]))
        mrows.append({"mol_row_id": f"M{i+1:04d}", "report_id": r["ID"], "compartment": nn(r["compartment"]),
                      "gene_raw": nn(r["gen"]), **pdx, "alteration_raw": nn(r["alteration"]),
                      "mechanism_raw": nn(r["type"]), "n_examined": nn(r["n_examined"]), "n_with": nn(r["n_with_alteration"]),
                      "n_R_with": nn(r["n_resistant_with_alteration"]), "n_S_with": nn(r["n_susceptible_with_alteration"]),
                      "method_raw": nn(r["method"]), "note_raw": nn(r["note"]),
                      "extraction_decision": dec.get(r["ID"]), "extraction_ma_row": nn(r["Eligible for MA"]),
                      "selection_of_examined": None, "verification_status": "pending"})
    pd.DataFrame(mrows).to_csv(os.path.join(a.out, "molecular.csv"), index=False)

    # ---------------------------------------------------------------- genotypes
    grows = []
    for i, r in gen.reset_index(drop=True).iterrows():
        m = str(r["method"]).lower()
        scheme = ("MLST" if "mlst" in m else "microsatellite_STR" if re.search(r"microsat|mmt|\bstr\b|mlmt", m)
                  else "WGS" if re.search(r"wgs|genoma|whole", m) else "other" )
        t = f"{r['type']} {r['reported_clade']}"
        dst = re.findall(r"DST\s?(\d+)", t)
        clade4 = bool(re.search(r"clad[eo] ?4\b|clade iv|\bazr\b", t, re.I)) and not re.search(r"non-?clade 4|not clade 4|no clade 4", t, re.I)
        grows.append({"geno_row_id": f"G{i+1:04d}", "report_id": r["ID"], "compartment": nn(r["compartment"]),
                      "method_raw": nn(r["method"]), "scheme": scheme, "n_typed": nn(r["n_tipificados"]),
                      "type_raw": nn(r["type"]), "dst_list": "; ".join(dst) or None, "n_isolates": nn(r["n_isolates"]),
                      "n_azole_R": nn(r["n_azole_resistant"]), "lineage_label_reported": nn(r["reported_clade"]),
                      "clade4_reported": clade4, "note_raw": nn(r["note"]),
                      "extraction_decision": dec.get(r["ID"]), "verification_status": "pending"})
    pd.DataFrame(grows).to_csv(os.path.join(a.out, "genotypes.csv"), index=False)

    # ------------------------------------------------------------- dynamics (raw)
    dyn = X["Dynamics"].copy()
    dyn["row_type"] = np.where(dyn["antifungico"].astype(str).str.contains("prevalencia", case=False),
                               "species_prevalence_not_an_outcome", "resistance_by_period_to_merge_into_ast")
    dyn["agent_std"] = [D.map_agent(nn(v))[0] for v in dyn["antifungico"]]
    dyn["extraction_decision"] = dyn["ID"].map(dec)
    dyn = dyn.rename(columns={"ID": "report_id", "compartment": "compartment", "antifungico": "agent_raw",
                              "period": "period_raw", "n_tested": "n_tested", "description": "description_raw"})
    dyn[["report_id", "compartment", "row_type", "agent_raw", "agent_std", "period_raw", "n_tested", "n_R",
         "description_raw", "extraction_decision"]].to_csv(os.path.join(a.out, "dynamics_raw.csv"), index=False)

    # ----------------------------------------------------- collection candidates
    n2id = dict(zip(scr["No."], scr["ID"]))
    cc = ec12.copy()
    cc["report_id"] = cc["No."].map(n2id)
    # (2026-10-27) an empty candidate sheet (round 3) gives empty columns instead of failing on unpacking
    pe = cc["Period"].map(period_from_text).tolist()
    cc["period_start"] = [x[0] for x in pe]
    cc["period_end"] = [x[1] for x in pe]
    def overlap_flag(g):
        g = g.dropna(subset=["period_start"])
        if len(g) < 2: return "insufficient_period_data"
        iv = sorted(zip(g.period_start, g.period_end))
        return "periods_overlap" if any(iv[k+1][0] <= iv[k][1] for k in range(len(iv)-1)) else "periods_disjoint"
    ov = cc.groupby("Group").apply(overlap_flag, include_groups=False).to_dict()
    cc["group_period_overlap"] = cc["Group"].map(ov)
    cc = cc.rename(columns={"Group": "candidate_group", "Country": "country_raw", "Programme/institution (normalised)": "institution_key",
                            "Title": "title", "Year": "year", "Period": "period_raw", "N isolates": "n_isolates",
                            "Programme/institution": "institution_raw"})
    cc["decision_same_collection"] = None
    cc[["candidate_group", "report_id", "country_raw", "institution_key", "institution_raw", "title", "year", "period_raw",
        "period_start", "period_end", "n_isolates", "group_period_overlap", "decision_same_collection"]
       ].to_csv(os.path.join(a.out, "collection_candidates.csv"), index=False)

    # -------------------------------------------------------------- dictionaries
    dd = os.path.join(a.out, "dictionaries"); os.makedirs(dd, exist_ok=True)
    ag = res["antifungico"].dropna().astype(str).value_counts().rename_axis("agent_raw").reset_index(name="n_rows").sort_values(["n_rows", "agent_raw"], ascending=[False, True], ignore_index=True)
    ag[["agent_std", "agent_class", "per_agent", "rule"]] = ag["agent_raw"].apply(lambda x: pd.Series(D.map_agent(x)))
    ag.to_csv(os.path.join(dd, "dict_agent.csv"), index=False)
    me = res["method"].fillna("").astype(str).value_counts().rename_axis("method_raw").reset_index(name="n_rows").sort_values(["n_rows", "method_raw"], ascending=[False, True], ignore_index=True)
    me["method_cat"] = me["method_raw"].map(D.map_method)
    me.to_csv(os.path.join(dd, "dict_method.csv"), index=False)
    it = res["standard"].fillna("").astype(str).value_counts().rename_axis("interp_raw").reset_index(name="n_rows").sort_values(["n_rows", "interp_raw"], ascending=[False, True], ignore_index=True)
    parsed = it["interp_raw"].apply(lambda x: pd.Series(D.parse_interpretive(x or None)))
    pd.concat([it, parsed], axis=1).to_csv(os.path.join(dd, "dict_interpretive.csv"), index=False)
    co = est["country"].dropna().astype(str).value_counts().rename_axis("country_raw").reset_index(name="n_reports").sort_values(["n_reports", "country_raw"], ascending=[False, True], ignore_index=True)
    cmap = co["country_raw"].map(D.map_country)
    co["iso3"] = [";".join(x[0]) for x in cmap]; co["who_region"] = [x[1] for x in cmap]
    co["multinational"] = [x[2] for x in cmap]; co["inferred_flag"] = [x[3] for x in cmap]; co["rule"] = [x[4] for x in cmap]
    co.to_csv(os.path.join(dd, "dict_country.csv"), index=False)

    # ----------------------------------------------------------------- build log
    log = {"built": str(date.today()), "script": os.path.basename(__file__), "version": "v0",
           "inputs": {os.path.basename(p): md5(p) for p in [a.screening, a.extraction, a.pdf_groups, a.truncated, a.doubtful_review] if p and os.path.exists(p)},
           "counts": {"reports": len(reports), "ast_rows": len(ast), "molecular_rows": len(mrows), "genotype_rows": len(grows),
                      "collection_candidate_rows": len(cc)}}
    json.dump(log, open(os.path.join(a.out, "build_log.json"), "w"), indent=1)
    print(json.dumps(log, indent=1))

if __name__ == "__main__":
    main()
