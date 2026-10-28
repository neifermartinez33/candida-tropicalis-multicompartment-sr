#!/usr/bin/env python3
"""Analysis dataset v1 (2026-10-20): included studies only, deduplicated, numeric and coded fields only.

Inclusion: extraction decision INCLUDE. Removed: truncated PDF; PDF of another work
(per extraction notes, or one of the three shared files that are not articles);
country inferred from affiliation (EC3); duplicate records of the same PDF (one kept:
most AST rows, then most molecular+genotype rows, then lowest corpus number).
Rows kept only if quantifiable: compartment C1-C6, single named agent, denominator > 0,
counts consistent with the denominator. No free text.

Usage: python3 build_analysis_dataset_v1.py TIDY_V0_DIR EXTRACTION_XLSX OUT_DIR
"""
import os, re, sys, json
import numpy as np, pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

T, XLSX, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
rep = pd.read_csv(f"{T}/reports.csv", low_memory=False)
ast = pd.read_csv(f"{T}/ast.csv", low_memory=False)
mol = pd.read_csv(f"{T}/molecular.csv", low_memory=False)
gen = pd.read_csv(f"{T}/genotypes.csv", low_memory=False)
c4 = pd.read_excel(XLSX, sheet_name="Clade 4")
COMP = ["C1", "C2", "C3", "C4", "C5", "C6"]
NON_ARTICLE_PDF_GROUPS = [7, 18, 27]
log = []

# ------------------------------------------------------------------ studies
s = rep[rep.extraction_decision == "INCLUDE"].copy(); log.append(("Included in the extraction", len(s)))
s = s[s.pdf_status != "truncated"]; log.append(("Without truncated PDF", len(s)))
s = s[~(s.pdf_status.eq("wrong_document_per_notes") | s.pdf_identical_group.isin(NON_ARTICLE_PDF_GROUPS))]
log.append(("Without PDF of another work", len(s)))
s = s[s.country_inferred_flag != True]; log.append(("Without country inferred from the affiliation (EC3)", len(s)))
bad_title = s.title.isna() | s.title.astype(str).str.contains(r"REMOVED|Data Sheet|^nan$", case=False)
s["_score"] = s.n_rows_ast.fillna(0) * 1000 + s.n_rows_molecular.fillna(0) + s.n_rows_genotype.fillna(0) - bad_title * 1e6
drop = set()
for g, d in s[s.pdf_identical_group.notna()].groupby("pdf_identical_group"):
    if len(d) > 1:
        best = d.sort_values(["_score", "corpus_n"], ascending=[False, True]).report_id.iloc[0]
        drop |= set(d.report_id) - {best}
s = s[~s.report_id.isin(drop)]; log.append(("Without duplicate records of the same PDF", len(s)))
ids = set(s.report_id)

def cat(text, rules, default):
    t = str(text).lower() if pd.notna(text) else ""
    for pat, val in rules:
        if re.search(pat, t):
            return val
    return default

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

def split_comp(x):
    if pd.isna(x): return []
    return sorted({c.strip() for c in str(x).split(";") if c.strip() in COMP})

comps = s.compartments_raw.map(split_comp)
single_iso = s.country_iso3.where(~s.multinational.astype(bool), "MULTI")
studies = pd.DataFrame({
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

# ---------------------------------------------------------------------- AST
def mic(x):
    if pd.isna(x): return (np.nan, None)
    t = str(x).replace(",", ".").replace(" ", "")
    n = re.findall(r"\d+(?:\.\d+)?", t)
    if not n: return (np.nan, None)
    q = "<=" if re.match(r"^(<|≤)", t) else (">=" if re.match(r"^(>|≥)", t) else "=")
    return (float(n[0]), q)

def mic_range(x):
    if pd.isna(x): return (np.nan, np.nan)
    n = re.findall(r"\d+(?:\.\d+)?", str(x).replace(",", "."))
    return (float(n[0]), float(n[-1])) if n else (np.nan, np.nan)

a = ast[ast.report_id.isin(ids) & ast.compartment.isin(COMP) & ast.per_agent.astype(bool)].copy()
a = a[~a.agent_class.isin(["antiseptic", "experimental", "aggregated", "unclear", "unmapped"])]
n0 = len(a)
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
res = res.drop_duplicates().reset_index(drop=True)
res.insert(0, "row_id", [f"R{i+1:05d}" for i in range(len(res))])

# ---------------------------------------------------------------- molecular
m = mol[mol.report_id.isin(ids) & mol.compartment.isin(COMP) & ~mol.is_gene_presence_only.astype(bool)].copy()
m.loc[m.n_with.isna() & m.is_absence_statement.astype(bool), "n_with"] = 0
m = m[m.n_examined.notna() & (m.n_examined > 0) & m.n_with.notna() & (m.n_with <= m.n_examined)]
mech = m.mechanism_raw.map({"mutation": "mutation", "overexpression": "overexpression", "other": "other"})
det = np.where(m.aa_substitutions.notna(), m.aa_substitutions.astype(str).str.replace("; ", "+"),
               np.where(mech.eq("overexpression"), "overexpression", np.where(m.is_absence_statement.astype(bool), "none_detected", "other")))
METHOD_MOL = [(r"wgs|genom|whole|illumina|nanopore", "WGS"), (r"sanger|sequenc", "sequencing"),
              (r"qpcr|rt-?pcr|real-?time|expression", "qPCR"), (r"pcr", "PCR"), (r"maldi|spectrom|mass", "mass_spectrometry")]
molecular = pd.DataFrame({
    "study_id": m.report_id, "compartment": m.compartment, "gene": m.gene_std, "mechanism": mech, "determinant": det,
    "combination": np.where(m.is_combination.astype(bool), "YES", "NO"),
    "n_examined": m.n_examined.astype("Int64"), "n_with": m.n_with.astype("Int64"),
    "n_R_with": m.n_R_with.astype("Int64"), "n_S_with": m.n_S_with.astype("Int64"),
    "method": m.method_raw.map(lambda x: cat(x, METHOD_MOL, "other")),
}).drop_duplicates().reset_index(drop=True)
molecular.insert(0, "row_id", [f"M{i+1:04d}" for i in range(len(molecular))])

# ---------------------------------------------------------------- genotypes
g = gen[gen.report_id.isin(ids) & gen.compartment.isin(COMP)].copy()
g = g[g.n_typed.notna() | g.n_isolates.notna()]
dsts = g.dst_list.fillna("").map(lambda x: [d for d in str(x).split("; ") if d])
genotypes = pd.DataFrame({
    "study_id": g.report_id, "compartment": g.compartment, "scheme": g.scheme,
    "dst": [int(d[0]) if len(d) == 1 else pd.NA for d in dsts], "n_dst_listed": dsts.map(len),
    "n_typed": g.n_typed.astype("Int64"), "n_isolates": g.n_isolates.astype("Int64"), "n_azole_R": g.n_azole_R.astype("Int64"),
    "clade4": np.where(g.clade4_reported.astype(bool), "YES", "NO"),
}).drop_duplicates().reset_index(drop=True)
genotypes.insert(0, "row_id", [f"G{i+1:04d}" for i in range(len(genotypes))])

cc = c4[c4.ID.isin(ids)].copy()
cc["n_clade4"] = pd.to_numeric(cc["n clade 4 isolates"], errors="coerce")
cc = cc[cc.n_clade4.notna()]
clade4 = pd.DataFrame({"study_id": cc.ID, "n_clade4": cc.n_clade4.astype("Int64"),
                       "n_azole_R": pd.to_numeric(cc["n R azoles"], errors="coerce").astype("Int64"),
                       "compartments": cc.Compartments.map(split_comp).map(";".join).replace("", np.nan)})

# ---------------------------------------------------------- study-level flags
def one_or_multiple(x):
    u = sorted(set(v for v in x if pd.notna(v)))
    return u[0] if len(u) == 1 else ("multiple" if u else np.nan)
studies["ast_method"] = studies.study_id.map(res.groupby("study_id").method.agg(one_or_multiple))
studies["interp_standard"] = studies.study_id.map(res.groupby("study_id").interp_standard.agg(one_or_multiple))
studies["flc_regime"] = studies.study_id.map(res[res.agent == "fluconazole"].groupby("study_id").flc_regime.agg(one_or_multiple))
for col, df in [("has_ast", res), ("has_molecular", molecular), ("has_genotype", genotypes)]:
    studies[col] = np.where(studies.study_id.isin(df.study_id), "YES", "NO")
studies["clade4"] = np.where(studies.study_id.isin(set(genotypes[genotypes.clade4 == "YES"].study_id) | set(clade4.study_id)), "YES", "NO")
studies["eligible_ma"] = np.where(studies.study_id.isin(set(res[(res.eligible_r_cbp == "YES") | (res.eligible_nwt_ecv == "YES")].study_id)), "YES", "NO")

# ------------------------------------------------------------------- write
tables = {"studies": studies, "ast": res, "molecular": molecular, "genotypes": genotypes, "clade4": clade4}
for k, v in tables.items():
    v.to_csv(f"{OUT}/{k}.csv", index=False)
readme = [("Step", "Studies")] + log + [
    ("Susceptibility rows", len(res)), ("Molecular rows", len(molecular)), ("Genotype rows", len(genotypes)),
    ("Studies eligible for meta-analysis (eligible_ma = YES)", int((studies.eligible_ma == "YES").sum())),
    ("eligible_r_cbp = YES", "n_R and CLSI or EUCAST clinical breakpoint with an identifiable document or version"),
    ("eligible_nwt_ecv = YES", "n_NWT with an epidemiological cut-off value"),
    ("MIC units", "mg/L; empty when the method gives zone diameters in mm"),
    ("Pending", "Overlapping collections (EC12) unresolved: a collection may appear in more than one study"),
]
wb = Workbook(); wb.remove(wb.active)
ws = wb.create_sheet("readme")
for r in readme: ws.append(list(r))
ws.column_dimensions["A"].width = 55; ws.column_dimensions["B"].width = 95
for k, v in tables.items():
    ws = wb.create_sheet(k)
    ws.append(list(v.columns))
    for c in ws[1]: c.font = Font(bold=True, color="000000")
    for row in v.astype(object).where(v.notna(), None).itertuples(index=False):
        ws.append(list(row))
    ws.freeze_panes = "A2"
wb.save(f"{OUT}.xlsx")
json.dump({"log": log, "rows": {k: len(v) for k, v in tables.items()}, "dropped_duplicates": sorted(drop)},
          open(f"{OUT}/build_log.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps({"log": log, "rows": {k: len(v) for k, v in tables.items()}, "ast_rows_before_row_filters": n0,
                  "eligible_ma": int((studies.eligible_ma == "YES").sum()),
                  "comp": studies.compartments.value_counts().head(8).to_dict()}, ensure_ascii=False))
