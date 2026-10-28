"""dataset_v3_core.py (2026-10-24)

Common core of make_verification_books_v1.py and build_analysis_dataset_v3.py.

1. rebuild_v1() rebuilds in memory analysis dataset v1 with the EXACT logic of
   build_analysis_dataset_v1.py (same rows, same order, same row_id), but keeps the
   trace that v1 discarded: the identifier of the row in the tidy tables (ast_row_id), the criterion
   string as extracted (interp_raw) and the extractor's note (note_raw).
2. apply_ec2() applies the EC2 triage of 2026-10-23 exactly as apply_ec2_triage_v1.py.
3. check_against_v2() checks cell by cell that 1 + 2 reproduces analysis_dataset_v2_2026-10-23.
   If it does not, nothing that follows is reliable and the script stops.
4. mechanical() applies the mechanical rules fixed on 2026-10-24 (verification_rules_v1).
5. extra_reports() builds, with the same logic, the rows of the reports that enter through a
   round-2 decision (doubtful and excluded at extraction). Their rows carry row_id 'X' +
   ast_row_id, so that the row_id of v1 and v2 do not change.
"""
import json
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verification_rules_v1 as V  # noqa: E402

TIDY = "10_phase8_analysis/data/tidy_tables_v0_2026-10-20"
XLSX = "08_phase6_data_extraction/data_extraction_tropicalis.xlsx"
V2 = "10_phase8_analysis/data/analysis_dataset_v2_2026-10-23"
EC2_DEC = "07_phase5_full_text_screening/ec2_decisions_2026-10-23.csv"
COMP = ["C1", "C2", "C3", "C4", "C5", "C6"]
NON_ARTICLE_PDF_GROUPS = [7, 18, 27]
TRACE = ["ast_row_id", "interp_raw", "note_raw", "source_raw"]

DESIGN = [(r"case report|clinical case\b|single case\b|case report", "case_report"), (r"case series", "case_series"),
          (r"surveillance", "surveillance"), (r"cases? and controls|case-control|case control", "case_control"),
          (r"cohort", "cohort"), (r"cross-sectional|transversal|cross", "cross_sectional"),
          (r"experimental|in vitro|evaluation|method comparison|diagnostic|validation", "laboratory_evaluation"),
          (r"retrospectiv", "retrospective"), (r"prospectiv", "prospective"), (r"trial", "trial")]
SPECIES_ID = [(r"pcr|sequenc|\bits\b|d1/d2|d1-d2|lsu|wgs|genom|rflp|molecular", "molecular"), (r"maldi", "MALDI_TOF"),
              (r"vitek|microscan|phoenix|autoscan", "automated"),
              (r"api|id ?32|32 ?c id|auxacolor|rapid ?yeast|uni-?yeast|biochem|as+[iy]milation|fermentation|z[iy]mogram|aux[ao]nogram", "biochemical"),
              (r"chrom|hicrome|candida ?id", "chromogenic"),
              (r"germ tube|germinal tube|chlamydosp|corn ?meal|cornmeal|morphology|morphologic\b|conventional|dalmau", "conventional")]
METHOD_MOL = [(r"wgs|genom|whole|illumina|nanopore", "WGS"), (r"sanger|sequenc", "sequencing"),
              (r"qpcr|rt-?pcr|real-?time|expression", "qPCR"), (r"pcr", "PCR"), (r"maldi|spectrom|mass", "mass_spectrometry")]


def cat(text, rules, default):
    t = str(text).lower() if pd.notna(text) else ""
    for pat, val in rules:
        if re.search(pat, t):
            return val
    return default


def split_comp(x):
    if pd.isna(x):
        return []
    return sorted({c.strip() for c in str(x).split(";") if c.strip() in COMP})


def mic(x):
    if pd.isna(x):
        return (np.nan, None)
    t = str(x).replace(",", ".").replace(" ", "")
    n = re.findall(r"\d+(?:\.\d+)?", t)
    if not n:
        return (np.nan, None)
    q = "<=" if re.match(r"^(<|≤)", t) else (">=" if re.match(r"^(>|≥)", t) else "=")
    return (float(n[0]), q)


def mic_range(x):
    if pd.isna(x):
        return (np.nan, np.nan)
    n = re.findall(r"\d+(?:\.\d+)?", str(x).replace(",", "."))
    return (float(n[0]), float(n[-1])) if n else (np.nan, np.nan)


def _read_tidy(tidy, name):
    """(2026-10-27) a table without rows (round 3: no molecular or genotype data) is written without a header;
    it is read as an empty table with the columns of the main tidy tables."""
    p = f"{tidy}/{name}"
    if os.path.getsize(p) <= 2:
        return pd.read_csv(f"{TIDY}/{name}", nrows=0)
    return pd.read_csv(p, low_memory=False)


def load_tidy(tidy=TIDY, xlsx=XLSX):
    return {"rep": _read_tidy(tidy, "reports.csv"),
            "ast": _read_tidy(tidy, "ast.csv"),
            "mol": _read_tidy(tidy, "molecular.csv"),
            "gen": _read_tidy(tidy, "genotypes.csv"),
            "c4": pd.read_excel(xlsx, sheet_name="Clade 4")}


# ------------------------------------------------------------------------------------- studies
def select_reports(rep, ids_in=None, skip_country=False):
    """Report filter of v1. With ids_in, it starts from those reports instead of the INCLUDE ones.
    skip_country: does not apply the filter of the country inferred from the affiliation, because for a report that
    enters by a human round-2 decision the reviewer already checked the country (IC6) in the PDF."""
    log = []
    s = rep[rep.extraction_decision == "INCLUDE"].copy() if ids_in is None else rep[rep.report_id.isin(ids_in)].copy()
    log.append(("Included in the extraction", len(s)))
    s = s[s.pdf_status != "truncated"]; log.append(("Without truncated PDF", len(s)))
    s = s[~(s.pdf_status.eq("wrong_document_per_notes") | s.pdf_identical_group.isin(NON_ARTICLE_PDF_GROUPS))]
    log.append(("Without PDF of another work", len(s)))
    if not skip_country:
        s = s[s.country_inferred_flag != True]  # noqa: E712
    log.append(("Without country inferred from the affiliation (EC3)", len(s)))
    bad_title = s.title.isna() | s.title.astype(str).str.contains(r"REMOVED|Data Sheet|^nan$", case=False)
    s["_score"] = s.n_rows_ast.fillna(0) * 1000 + s.n_rows_molecular.fillna(0) + s.n_rows_genotype.fillna(0) - bad_title * 1e6
    drop = set()
    for g, d in s[s.pdf_identical_group.notna()].groupby("pdf_identical_group"):
        if len(d) > 1:
            best = d.sort_values(["_score", "corpus_n"], ascending=[False, True]).report_id.iloc[0]
            drop |= set(d.report_id) - {best}
    s = s[~s.report_id.isin(drop)]; log.append(("Without duplicate records of the same PDF", len(s)))
    return s, log, drop


def studies_frame(s):
    comps = s.compartments_raw.map(split_comp)
    single_iso = s.country_iso3.where(~s.multinational.astype(bool), "MULTI")
    return pd.DataFrame({
        "study_id": s.report_id, "corpus_n": s.corpus_n, "study_label": s.study_label,
        "year": pd.to_numeric(s.year, errors="coerce").astype("Int64"), "title": s.title, "journal": s.journal, "doi": s.doi,
        "country": s.country_raw.where(~s.multinational.astype(bool), "multinacional"),
        "country_iso3": single_iso.where(single_iso.notna() & ~single_iso.astype(str).str.contains(";"), "MULTI"),
        "who_region": s.who_region.where(~s.multinational.astype(bool), "MULTI"),
        "period_start": pd.to_numeric(s.period_start, errors="coerce").astype("Int64"),
        "period_end": pd.to_numeric(s.period_end, errors="coerce").astype("Int64"),
        "compartments": comps.map(";".join).replace("", np.nan), "n_compartments": comps.map(len),
        "n_tropicalis": pd.to_numeric(s.n_tropicalis_total, errors="coerce").astype("Int64"),
        "n_candida": pd.to_numeric(s.n_candida_total, errors="coerce").astype("Int64"),
        "multicentre": s.multicentre_raw.where(s.multicentre_raw.isin(["YES", "NO"])),
        "n_centres": pd.to_numeric(s.n_centres, errors="coerce").astype("Int64"),
        "design": s.design_raw.map(lambda x: cat(x, DESIGN, "other")),
        "species_id": s.species_id_raw.map(lambda x: cat(x, SPECIES_ID, "not_specified")),
        "azole_exposure_documented": s.azole_exposure_raw.map(lambda x: "NO" if (pd.isna(x) or str(x).strip().lower().startswith("not recorded")) else "YES"),
        "agricultural_azoles_tested": np.where(s.agricultural_azoles_tested_raw.notna(), "YES", "NO"),
    })


# ----------------------------------------------------------------------------------------- AST
def ast_frame(ast, ids):
    a = ast[ast.report_id.isin(ids) & ast.compartment.isin(COMP) & ast.per_agent.astype(bool)].copy()
    a = a[~a.agent_class.isin(["antiseptic", "experimental", "aggregated", "unclear", "unmapped"])]
    a = a[a.n_tested.notna() & (a.n_tested > 0)]
    cats3 = a[["n_S", "n_SDD_I", "n_R"]]
    ok = ~((a.n_R > a.n_tested) | (a.n_NWT > a.n_tested) | (cats3.notna().all(axis=1) & (cats3.sum(axis=1) > a.n_tested)))
    a = a[ok]
    has_value = a[["n_S", "n_SDD_I", "n_R", "n_NWT", "mic50", "mic90", "mic_gm"]].notna().any(axis=1)
    a = a[has_value]
    mm = a.unit.fillna("").str.contains("mm")
    m50 = a.mic50.map(mic); m90 = a.mic90.map(mic); rg = a.mic_range.map(mic_range)
    res = pd.DataFrame({
        "study_id": a.report_id, "compartment": a.compartment,
        "period_start": pd.to_numeric(a.period_start, errors="coerce").astype("Int64"),
        "period_end": pd.to_numeric(a.period_end, errors="coerce").astype("Int64"),
        "agent": a.agent_std, "agent_class": a.agent_class, "method": a.method_cat,
        "interp_standard": a.interp_standard, "interp_documents": a.interp_documents, "bp_type": a.bp_type,
        "flc_regime": a.flc_regime.where(a.agent_std == "fluconazole"),
        "version_inferred": np.where(a.version_inferred.astype(bool), "YES", "NO"),
        "n_tested": a.n_tested.astype("Int64"), "n_S": a.n_S.astype("Int64"), "n_SDD_I": a.n_SDD_I.astype("Int64"),
        "n_R": a.n_R.astype("Int64"), "n_NWT": a.n_NWT.astype("Int64"),
        "mic50_mg_l": [np.nan if b else v[0] for v, b in zip(m50, mm)], "mic50_qualifier": [None if b else v[1] for v, b in zip(m50, mm)],
        "mic90_mg_l": [np.nan if b else v[0] for v, b in zip(m90, mm)], "mic90_qualifier": [None if b else v[1] for v, b in zip(m90, mm)],
        "mic_min_mg_l": [np.nan if b else v[0] for v, b in zip(rg, mm)], "mic_max_mg_l": [np.nan if b else v[1] for v, b in zip(rg, mm)],
        "mic_gm_mg_l": a.mic_gm.where(~mm),
    })
    std_ok = res.interp_standard.fillna("").str.contains("CLSI|EUCAST")
    no_version = (a.flc_regime.eq("CLSI_version_not_stated") & a.interp_documents.isna()).values
    res["eligible_r_cbp"] = np.where(res.n_R.notna() & res.bp_type.fillna("").str.contains("CBP") & std_ok & ~no_version, "YES", "NO")
    res["eligible_nwt_ecv"] = np.where(res.n_NWT.notna() & res.bp_type.fillna("").str.contains("ECV"), "YES", "NO")
    v1cols = list(res.columns)
    for c in TRACE:
        res[c] = a[c].values
    res["mic_range_raw"] = a.mic_range.values
    res["unit_raw"] = a.unit.values
    # v1 did drop_duplicates() on its columns: the first row of each group is kept
    res = res.drop_duplicates(subset=v1cols).reset_index(drop=True)
    return res, v1cols


def molecular_frame(mol, ids):
    m = mol[mol.report_id.isin(ids) & mol.compartment.isin(COMP) & ~mol.is_gene_presence_only.astype(bool)].copy()
    m.loc[m.n_with.isna() & m.is_absence_statement.astype(bool), "n_with"] = 0
    m = m[m.n_examined.notna() & (m.n_examined > 0) & m.n_with.notna() & (m.n_with <= m.n_examined)]
    mech = m.mechanism_raw.map({"mutation": "mutation", "overexpression": "overexpression", "other": "other"})
    det = np.where(m.aa_substitutions.notna(), m.aa_substitutions.astype(str).str.replace("; ", "+"),
                   np.where(mech.eq("overexpression"), "overexpression", np.where(m.is_absence_statement.astype(bool), "none_detected", "other")))
    return pd.DataFrame({
        "study_id": m.report_id, "compartment": m.compartment, "gene": m.gene_std, "mechanism": mech, "determinant": det,
        "combination": np.where(m.is_combination.astype(bool), "YES", "NO"),
        "n_examined": m.n_examined.astype("Int64"), "n_with": m.n_with.astype("Int64"),
        "n_R_with": m.n_R_with.astype("Int64"), "n_S_with": m.n_S_with.astype("Int64"),
        "method": m.method_raw.map(lambda x: cat(x, METHOD_MOL, "other")),
    }).drop_duplicates().reset_index(drop=True)


def genotypes_frame(gen, ids):
    g = gen[gen.report_id.isin(ids) & gen.compartment.isin(COMP)].copy()
    g = g[g.n_typed.notna() | g.n_isolates.notna()]
    dsts = g.dst_list.fillna("").map(lambda x: [d for d in str(x).split("; ") if d])
    return pd.DataFrame({
        "study_id": g.report_id, "compartment": g.compartment, "scheme": g.scheme,
        "dst": [int(d[0]) if len(d) == 1 else pd.NA for d in dsts], "n_dst_listed": dsts.map(len),
        "n_typed": g.n_typed.astype("Int64"), "n_isolates": g.n_isolates.astype("Int64"), "n_azole_R": g.n_azole_R.astype("Int64"),
        "clade4": np.where(g.clade4_reported.astype(bool), "YES", "NO"),
    }).drop_duplicates().reset_index(drop=True)


def clade4_frame(c4, ids):
    cc = c4[c4.ID.isin(ids)].copy()
    cc["n_clade4"] = pd.to_numeric(cc["n clade 4 isolates"], errors="coerce")
    cc = cc[cc.n_clade4.notna()]
    return pd.DataFrame({"study_id": cc.ID, "n_clade4": cc.n_clade4.astype("Int64"),
                         "n_azole_R": pd.to_numeric(cc["n R azoles"], errors="coerce").astype("Int64"),
                         "compartments": cc.Compartments.map(split_comp).map(";".join).replace("", np.nan)})


def study_flags(studies, res, molecular, genotypes, clade4):
    def one_or_multiple(x):
        u = sorted(set(v for v in x if pd.notna(v)))
        return u[0] if len(u) == 1 else ("multiple" if u else np.nan)
    studies = studies.copy()
    studies["ast_method"] = studies.study_id.map(res.groupby("study_id").method.agg(one_or_multiple))
    studies["interp_standard"] = studies.study_id.map(res.groupby("study_id").interp_standard.agg(one_or_multiple))
    studies["flc_regime"] = studies.study_id.map(res[res.agent == "fluconazole"].groupby("study_id").flc_regime.agg(one_or_multiple))
    for col, df in [("has_ast", res), ("has_molecular", molecular), ("has_genotype", genotypes)]:
        studies[col] = np.where(studies.study_id.isin(df.study_id), "YES", "NO")
    studies["clade4"] = np.where(studies.study_id.isin(set(genotypes[genotypes.clade4 == "YES"].study_id) | set(clade4.study_id)), "YES", "NO")
    studies["eligible_ma"] = np.where(studies.study_id.isin(set(res[(res.eligible_r_cbp == "YES") | (res.eligible_nwt_ecv == "YES")].study_id)), "YES", "NO")
    return studies


def rebuild_v1(t):
    """Dataset v1 in memory, with trace. Returns a dict of tables and the log of steps."""
    s, log, drop = select_reports(t["rep"])
    ids = set(s.report_id)
    studies = studies_frame(s)
    res, v1cols = ast_frame(t["ast"], ids)
    res.insert(0, "row_id", [f"R{i+1:05d}" for i in range(len(res))])
    molecular = molecular_frame(t["mol"], ids)
    molecular.insert(0, "row_id", [f"M{i+1:04d}" for i in range(len(molecular))])
    genotypes = genotypes_frame(t["gen"], ids)
    genotypes.insert(0, "row_id", [f"G{i+1:04d}" for i in range(len(genotypes))])
    clade4 = clade4_frame(t["c4"], ids)
    studies = study_flags(studies, res, molecular, genotypes, clade4)
    return {"studies": studies, "ast": res, "molecular": molecular, "genotypes": genotypes,
            "clade4": clade4, "_log": log, "_drop": sorted(drop), "_v1cols": ["row_id"] + v1cols}


def apply_ec2(tb, dec_path=EC2_DEC):
    """As apply_ec2_triage_v1.py: excludes B and D, recodes A."""
    dec = pd.read_csv(dec_path, encoding="utf-8-sig", dtype=str)
    outside = set(dec.loc[dec.group.isin(["B_refers_to_other_source", "D_generic_no_method"]), "study_id"])
    recode = dict(zip(dec.loc[dec.group == "A_declared_recode", "study_id"],
                      dec.loc[dec.group == "A_declared_recode", "species_id_proposed"]))
    out = {}
    for k in ("studies", "ast", "molecular", "genotypes", "clade4"):
        out[k] = tb[k][~tb[k].study_id.isin(outside)].reset_index(drop=True)
    st = out["studies"]
    st.loc[st.study_id.isin(recode), "species_id"] = st.loc[st.study_id.isin(recode), "study_id"].map(recode)
    for k in ("_log", "_drop", "_v1cols"):
        out[k] = tb[k]
    out["_ec2_excluded"] = sorted(outside)
    out["_ec2_recoded"] = recode
    return out


def _as_text(df):
    return df.astype(object).where(df.notna(), "").astype(str)


def check_against_v2(tb, v2=V2):
    """Cell by cell against dataset v2 on disk. Returns a list of discrepancies (empty if it reconciles)."""
    bad = []
    for k in ("studies", "ast", "molecular", "genotypes", "clade4"):
        disk = pd.read_csv(os.path.join(v2, f"{k}.csv"), dtype=str, keep_default_na=False)
        mem = tb[k][tb["_v1cols"]] if k == "ast" else tb[k]
        tmp = pd.read_csv(pd.io.common.StringIO(mem.to_csv(index=False)), dtype=str, keep_default_na=False)
        if list(tmp.columns) != list(disk.columns):
            bad.append(f"{k}: different columns")
            continue
        if len(tmp) != len(disk):
            bad.append(f"{k}: {len(tmp)} rows in memory versus {len(disk)} on disk")
            continue
        diff = (tmp.values != disk.values)
        if diff.any():
            r, c = np.argwhere(diff)[0]
            bad.append(f"{k}: {int(diff.sum())} different cells; first in row {r}, column {tmp.columns[c]}")
    return bad


# ------------------------------------------------------------------------------ mechanical layer
EUCAST_VER = re.compile(r"EUCAST BP v\s*\d+(?:\.\d+)?|E\.Def", re.I)
EUCAST_VER_RAW = re.compile(r"E\.? ?Def|E\.? ?Dis|EUCAST[^;/]{0,12}\bv(?:ersion)? ?\d|EUCAST \d+(?:\.\d+)+", re.I)


def apply_row_rules(a, studies):
    """Mechanical rules per row (2026-10-24): regime (Rule 1, corrected AR6), basis of the version,
    MIC present, Rule 4 and v3 eligibility. Used by mechanical() and by build_analysis_dataset_v3.py,
    which applies it again after the human corrections."""
    a = a.copy()
    yr = studies.set_index("study_id")["year"].astype("Float64")
    pub = a.study_id.map(yr)
    out = [V.row_regime(ag, st_, raw, (None if pd.isna(y) else float(y)))
           for ag, st_, raw, y in zip(a.agent, a.interp_standard, a.interp_raw, pub)]
    a["regime_v3"] = [o[0] for o in out]
    a["regime_basis"] = [o[1] for o in out]
    a["regime_flag_v3"] = [o[2] for o in out]
    # EUCAST: version by document (BP vX or E.Def, in the extracted documents or in the string) or by
    # year written in the string; otherwise, without version (Rule 4)
    eu = a.regime_basis.eq("eucast")
    raw = a.interp_raw.fillna("").astype(str)
    has_doc = a.interp_documents.fillna("").astype(str).str.contains(EUCAST_VER) | raw.str.contains(EUCAST_VER_RAW)
    has_year = raw.str.contains(V.YEAR)
    a.loc[eu & has_doc, "regime_basis"] = "eucast_document"
    a.loc[eu & ~has_doc & has_year, "regime_basis"] = "eucast_year_in_string"
    # (2026-10-26, B10) a declared breakpoint ('S <=1 mg/L') declares the criterion: it is not Rule 4; the version comes from the years
    has_cut = raw.str.contains(r"\b[sr]\s*(?:≤|<=|=<|<|>|≥|>=|=>)\s*\d", case=False)
    a.loc[eu & ~has_doc & ~has_year & has_cut, "regime_basis"] = "eucast_declared_cutoff"
    a.loc[eu & ~has_doc & ~has_year & ~has_cut, "regime_basis"] = "eucast_unversioned"
    a["eucast_version"] = a.interp_documents.fillna("").astype(str).str.extract(r"EUCAST BP v\s*(\d+(?:\.\d+)?)", expand=False)
    a["has_mic"] = np.where([V.has_mic(r) for r in a.to_dict("records")], "YES", "NO")
    a["rule4_excluded"] = np.where([V.rule4_excluded(b, m == "YES", pd.notna(r))
                                    for b, m, r in zip(a.regime_basis, a.has_mic, a.n_R)], "YES", "NO")
    std_ok = a.interp_standard.fillna("").astype(str).str.contains("CLSI|EUCAST")
    bp = a.bp_type.fillna("").astype(str)
    valid = ~((a.n_R > a.n_tested).fillna(False) | (a.n_NWT > a.n_tested).fillna(False)).astype(bool)
    a["eligible_r_cbp_v3"] = np.where(a.n_R.notna() & bp.str.contains("CBP") & std_ok & valid, "YES", "NO")
    a["eligible_nwt_ecv_v3"] = np.where(a.n_NWT.notna() & bp.str.contains("ECV") & valid, "YES", "NO")
    return a


def mechanical(tb, rep):
    """New columns of the mechanical layer (rules fixed on 2026-10-24). It deletes nothing."""
    tb = dict(tb)
    tb["ast"] = apply_row_rules(tb["ast"], tb["studies"])
    a = tb["ast"]
    # reports
    st = tb["studies"].copy()
    r = rep.set_index("report_id")
    st["species_id_raw"] = st.study_id.map(r["species_id_raw"])
    prop = st.species_id_raw.map(V.species_proposal)
    st["species_id_proposal"] = [p[0] for p in prop]
    st["species_id_issue"] = [p[1] for p in prop]
    # the EC2 triage already recoded some 'not_specified': that human decision prevails
    st.loc[st.species_id_issue.eq("") , "species_id_proposal"] = st.loc[st.species_id_issue.eq(""), "species_id"]
    st["azole_exposure_status"] = st.study_id.map(r["azole_exposure_raw"]).map(V.azole_exposure_3)
    st["extraction_confidence"] = st.study_id.map(r["extraction_confidence"])
    st["pdf_file"] = st.study_id.map(r["pdf_file"])
    st["programme_institution_raw"] = st.study_id.map(r["programme_institution_raw"])
    ok = a[(a.eligible_r_cbp_v3 == "YES") | (a.eligible_nwt_ecv_v3 == "YES")].study_id
    st["eligible_ma_v3"] = np.where(st.study_id.isin(set(ok)), "YES", "NO")
    tb["studies"] = st
    return tb


def extra_reports(t, ids, prefix="X", overrides=None):
    """Tables of the reports that enter by a round-2 decision, with the logic of v1.
    Their AST rows carry row_id = prefix + ast_row_id.
    overrides: {report_id: {column: value}} with the data that the reviewer read in the correct text when the assigned
    PDF was another work (B09); they are applied before the filter, which therefore no longer discards it because of the PDF."""
    rep_in = t["rep"]
    if overrides:
        rep_in = rep_in.copy()
        new = [k for k in overrides if k not in set(rep_in.report_id)]   # reports without extraction (B08 arbitration)
        if new:
            rep_in = pd.concat([rep_in, pd.DataFrame({"report_id": new})], ignore_index=True)
        for k, cols in overrides.items():
            m = rep_in.report_id == k
            for c, v in cols.items():
                if c not in rep_in.columns:
                    raise KeyError(f"unknown column in overrides: {c}")
                rep_in[c] = rep_in[c].astype(object)
                rep_in.loc[m, c] = v
    s, log, drop = select_reports(rep_in, ids_in=ids, skip_country=True)
    keep = set(s.report_id)
    studies = studies_frame(s)
    res, _ = ast_frame(t["ast"], keep)
    res.insert(0, "row_id", prefix + res["ast_row_id"].astype(str))
    molecular = molecular_frame(t["mol"], keep)
    molecular.insert(0, "row_id", [f"{prefix}M{i+1:04d}" for i in range(len(molecular))])
    genotypes = genotypes_frame(t["gen"], keep)
    genotypes.insert(0, "row_id", [f"{prefix}G{i+1:04d}" for i in range(len(genotypes))])
    clade4 = clade4_frame(t["c4"], keep)
    studies = study_flags(studies, res, molecular, genotypes, clade4)
    # (2026-10-26) discarded for sharing a PDF with another report that enters: duplicate record of the same publication
    rep = rep_in.set_index("report_id")
    dup_of = {}
    for i in sorted(set(drop) & set(ids)):
        g = rep.at[i, "pdf_identical_group"]
        kept = sorted(set(rep.index[rep.pdf_identical_group == g]) & keep)
        if kept: dup_of[i] = kept[0]
    return {"studies": studies, "ast": res, "molecular": molecular, "genotypes": genotypes,
            "clade4": clade4, "_log": log, "_dropped": sorted(set(ids) - keep), "_dup_of": dup_of, "_rep": rep_in}


def md5(path):
    import hashlib
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, default=str)
