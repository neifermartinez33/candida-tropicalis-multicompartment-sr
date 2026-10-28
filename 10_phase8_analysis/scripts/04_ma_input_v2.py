#!/usr/bin/env python3
"""04_ma_input_v2.py (2026-10-24)

Input table of the meta-analysis (SQ2) with the rules 10_phase8_analysis/analysis_rules_v4_2026-10-24.md,
on analysis dataset v3. Changes from v1, all in rules v4:
  - regime of each row by verification_rules_v1 (Rule 1 for all agents, criterion that separates
    method and breakpoint, breakpoints and markers by clause of the agent); there is no longer a no_version filter;
  - Rule 4 of the protocol: the resistance row without a declared version and without MIC is left out;
  - D4: the resistance row enters only if the version that the study applied had a clinical breakpoint
    for C. tropicalis and that agent (applicability matrix with sources); it replaces AR8;
  - AR20: rows that do not measure prevalence, out of the main analysis (they return in SX3);
  - C5 in strict reading in the main analysis; C5 rows of broad reading only in SA1;
  - collections: AR1 plus the pairs that round 2 declared the same collection (B03);
  - AR10 v4: if the rows of a report in a stratum are disjoint subsets (different sources or periods)
    and none is the total, they are summed instead of choosing one.
It computes no pooled estimate: that is done by the R scripts.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/04_ma_input_v2.py --provisional
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/04_ma_input_v2.py
Without an option it takes the most recent FINAL v3 dataset and stops if any main row of a stratum that meets
AR12 is not verified; --provisional takes the most recent PROVISIONAL v3 and marks it in every output.
Outputs (never overwritten), in 10_phase8_analysis/results:
  ma_input_v2_<date-time>[_PROVISIONAL].csv     one row per report, stratum and selection variant
  ma_strata_v2_<...>.csv, ec12_collections_v2_<...>.csv, ar10_sums_v2_<...>.csv,
  verification_coverage_v2_<...>.csv and logs/04_ma_input_v2_<...>.json
"""
import glob
import json
import os
import platform
import re
import sys
import unicodedata
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verification_rules_v1 as V  # noqa: E402

RULES = "10_phase8_analysis/analysis_rules_v4_2026-10-24.md"
DECISIONS = "10_phase8_analysis/team_decisions_2026-10-24.md"
MATRIX = "10_phase8_analysis/applicability/cbp_applicability_v1_2026-10-24.csv"
T = "10_phase8_analysis/data/tidy_tables_v0_2026-10-20"
OUT, LOG_DIR = "10_phase8_analysis/results", "10_phase8_analysis/results/logs"
METHOD_RANK = {"broth_microdilution_CLSI_or_unspecified": 1, "broth_microdilution_EUCAST": 1,
               "broth_macrodilution": 1, "commercial_microdilution_SYO": 2, "commercial_automated_VITEK2": 2,
               "commercial_ATB_FUNGUS": 2, "commercial_other": 2, "gradient_diffusion": 3,
               "disk_diffusion": 4}  # other method: 5
DROP_METHODS = {"biofilm_susceptibility_not_resistance", "not_reported"}  # AR9
STRATUM = ["compartment", "agent", "outcome", "regime_stratum"]
MIN_K, MIN_G = 5, 2  # AR12


def md5(path):
    import hashlib
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(text):
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


# ------------------------------------------------------------------------------- applicability (D4)
APPLICABLE = {"YES", "NO", "NS_only", "IE", "UNVERIFIED"}
M44_KEYS = {"M44-A", "M44-A2", "M44-S3", "M44 3rd ed"}
ECV_DOCS = {"M59", "M57S"}
M60_FAMILY = {"M60", "M27 4th ed", "M60 2nd ed", "M27M44S"}
EDEF_YEAR = {"7.1": 2008, "7.2": 2012, "7.3": 2015, "7.3.1": 2017, "7.3.2": 2020, "7.4": 2023}


def load_matrix(path):
    if not os.path.exists(path):
        sys.exit(f"The applicability matrix is missing {path} (decision D4)")
    mx = pd.read_csv(path, dtype=str, keep_default_na=False)
    need = {"standard", "scope", "key", "agent", "applicable", "valid_from", "valid_to", "regime", "method_scope", "source"}
    if need - set(mx.columns):
        sys.exit(f"The matrix does not carry the columns {sorted(need - set(mx.columns))}")
    bad = mx[~mx.applicable.isin(APPLICABLE)]
    if len(bad):
        sys.exit(f"Values of 'applicable' not admitted in the matrix: {sorted(set(bad.applicable))}")
    if (mx.source.str.strip() == "").any():
        sys.exit("There are matrix rows without a source: D4 requires the source of every cell")
    for c in ("valid_from", "valid_to"):
        mx[c] = pd.to_numeric(mx[c], errors="coerce")
    return mx


def eucast_version_of(row):
    """Version of the EUCAST table declared in the row (extracted document or string), or None."""
    for txt in (row.get("interp_documents"), row.get("interp_raw")):
        m = re.search(r"EUCAST(?: BP)?[^;/]{0,12}\bv(?:ersion)? ?(\d+(?:\.\d+)?)|EUCAST (\d+\.\d+)\b", str(txt or ""), re.I)
        if m:
            v = m.group(1) or m.group(2)
            return v if "." in v else v + ".0"
    return None


def edef_year(row):
    ys = [EDEF_YEAR[m] for m in re.findall(r"E\.? ?Def ?(7\.\d(?:\.\d)?)", f"{row.get('interp_documents') or ''} {row.get('interp_raw') or ''}", re.I)
          if m in EDEF_YEAR]
    return max(ys) if ys else None


def window_value(cands, y0, y1, nearest_last):
    """Applicability value of the cells in force between y0 and y1; all must agree."""
    win = cands[(cands.valid_from <= y1 + 0.999) & (cands.valid_to >= y0)]
    if not len(win):
        if not len(cands):
            return "MISSING", "no cells"
        win = cands.sort_values("valid_from").iloc[[-1 if nearest_last else 0]]
    vals = set(win.applicable)
    keys = ",".join(win.key)
    if len(vals) == 1:
        return vals.pop(), keys
    return "AMBIGUOUS", f"the cells in force ({keys}) difieren"


def applicability(row, mx):
    """(decision, detail) of D4 for a resistance row. It enters only with YES."""
    agent, regime = row["agent"], row["regime"]
    m = mx[mx.agent == agent]
    if not len(m):
        return "MISSING", f"agent {agent} without cells in the matrix"
    y1 = row.get("year")
    y0 = row.get("period_end") if pd.notna(row.get("period_end")) else y1
    if regime in ("CLSI_SS", "CLSI_pre2012"):
        c = m[m.standard == "CLSI"]
        docs = set(V.clsi_documents(V.agent_text(row.get("interp_raw"), agent))) | \
            {d.strip() for d in str(row.get("interp_documents") or "").split(";") if d.strip()}
        docs -= {"M44 unversioned"}
        disk = row.get("method") == "disk_diffusion"
        if disk:
            have = c[(c.scope == "document") & c.key.isin(docs & M44_KEYS)]
            if not len(have) and docs & M60_FAMILY:
                have = c[c.key == "M60_disk"]
        else:
            have = c[(c.scope == "document") & c.key.isin(docs - M44_KEYS - ECV_DOCS)]
        if len(have):
            r = have.sort_values("valid_from").iloc[-1]
            return r.applicable, f"CLSI {r.key}"
        if docs & ECV_DOCS and not (docs - ECV_DOCS):
            return "NO", "only an ECV document"
        pool = c[(c.regime == regime) & (c.method_scope == ("disk" if disk else "broth")) & ~c.key.isin(ECV_DOCS | {"M60_disk"})]
        if row.get("regime_basis") == "declared_cutoff":
            # the declared breakpoints match those of a document of the regime (Rule 1)
            return ("YES", "declared breakpoints, published in the regime") if (pool.applicable == "YES").any() else \
                ("NO", "declared breakpoints without a document of the regime with a breakpoint")
        if row.get("regime_basis") == "year_in_string":
            ys = [int(y) for y in V.YEAR.findall(str(row.get("interp_raw") or ""))]
            if ys:
                y0 = y1 = max(ys)
        if pd.isna(y1) or pd.isna(y0):
            return "UNVERIFIED", "CLSI without document or year to bound the version"
        v, k = window_value(pool, float(y0), float(max(y0, y1)), nearest_last=(regime == "CLSI_pre2012"))
        return v, f"CLSI {regime}, by years: {k}"
    if regime == "EUCAST":
        c = m[(m.standard == "EUCAST") & (m.scope == "version")]
        v = eucast_version_of(row)
        if v is not None:
            mv = c[c.key == v]
            if len(mv):
                return mv.iloc[0].applicable, f"EUCAST v{v}"
        if row.get("regime_basis") == "eucast_year_in_string":
            ys = [int(y) for y in V.YEAR.findall(str(row.get("interp_raw") or ""))]
            if ys:
                y0 = y1 = max(ys)
        ed = edef_year(row)
        if ed is not None and pd.notna(y0):
            y0 = max(float(y0), ed)
        if pd.isna(y1) or pd.isna(y0):
            return "MISSING", "EUCAST without version or years"
        val, k = window_value(c, float(y0), float(max(y0, y1)), nearest_last=True)
        return val, f"EUCAST by years ({k})"
    return "MISSING", f"regimen {regime}"


# ------------------------------------------------------------------------------------- rows
def nwt_regime(row):
    """Source of the ECV of a non-wild-type row (AR5), as in v1."""
    st = str(row["interp_standard"])
    clsi, eucast = "CLSI" in st, "EUCAST" in st
    if row["agent"] == "caspofungin":
        return None, "no_ecv_for_agent"
    if clsi and eucast:
        return None, "mixed_standard"
    if clsi or eucast:
        return ("ECV_CLSI" if clsi else "ECV_EUCAST"), ""
    return None, "ecv_source_not_identifiable"


def long_table(ast, studies, mx, excluded):
    a = ast.merge(studies[["study_id", "year", "c5_definition_v3", "species_id_v3", "country_iso3", "who_region",
                           "study_label", "entry_route"]], on="study_id", how="left")
    a = a.rename(columns={"period_start": "row_period_start", "period_end": "row_period_end"})
    sp = studies.set_index("study_id")
    a["period_start"] = a.study_id.map(sp["period_start"])
    a["period_end"] = a.study_id.map(sp["period_end"])
    dropped = a["method"].isin(DROP_METHODS)
    excluded["AR9 biofilm or undeclared method"] = int((dropped & ((a.eligible_r_cbp_v3 == "YES") |
                                                                         (a.eligible_nwt_ecv_v3 == "YES"))).sum())
    a = a[~dropped]
    parts = []
    # resistance by clinical breakpoint
    r = a[a.eligible_r_cbp_v3 == "YES"].copy()
    r["regime"] = r.regime_v3
    r["exclusion"] = ""
    r.loc[r.regime.isna(), "exclusion"] = "R: " + r.loc[r.regime.isna(), "regime_basis"].astype(str)
    r.loc[(r.exclusion == "") & (r.rule4_excluded == "YES"), "exclusion"] = "R: Rule 4 (no version and no MIC)"
    app = [applicability(x, mx) if e == "" else ("", "") for x, e in zip(r.to_dict("records"), r.exclusion)]
    r["d4"] = [p[0] for p in app]
    r["d4_detail"] = [p[1] for p in app]
    missing = r[r.d4.isin(["MISSING"])]
    if len(missing):
        f = os.path.join(OUT, f"d4_missing_cells_{datetime.now().strftime('%Y-%m-%dT%H%M%S')}.csv")
        missing.groupby(["agent", "regime", "d4_detail"]).size().reset_index(name="rows").to_csv(f, index=False)
        sys.exit(f"The applicability matrix does not cover {len(missing)} rows; cells missing in {f}")
    sel = (r.exclusion == "") & (r.d4 != "YES")
    r.loc[sel, "exclusion"] = "R: D4 " + r.loc[sel, "d4"] + " (" + r.loc[sel, "d4_detail"] + ")"
    r["outcome"], r["events"] = "R", r.n_R
    parts.append(r)
    # non-wild-type by ECV
    n = a[a.eligible_nwt_ecv_v3 == "YES"].copy()
    res = [nwt_regime(x) for x in n.to_dict("records")]
    n["regime"] = [x[0] for x in res]
    n["exclusion"] = ["" if x[0] else f"NWT: {x[1]}" for x in res]
    n["d4"], n["d4_detail"] = "", ""
    n["outcome"], n["events"] = "NWT", n.n_NWT
    parts.append(n)
    x = pd.concat(parts, ignore_index=True)
    for reason, k in x.loc[x.exclusion != "", "exclusion"].value_counts().items():
        excluded[reason] = int(k)
    x = x[x.exclusion == ""].copy()
    flc = (x.agent == "fluconazole") & x.regime.isin(["CLSI_SS", "EUCAST"]) & (x.outcome == "R")
    x["regime_stratum"] = x.regime.where(~flc, "CLSI_SS+EUCAST")  # AR7
    x["method_rank"] = x.method.map(METHOD_RANK).fillna(5).astype(int)
    x["crit_pref"] = ((x.regime == "EUCAST") != (x.method == "broth_microdilution_EUCAST")).astype(int)
    x["c5_reading"] = x.c5_definition_v3.where(x.compartment == "C5")
    x["c5_broad"] = (x.compartment == "C5") & (x.c5_definition_v3 != "strict")
    x["ar20"] = x.ar20_excluded.eq("YES")
    return x


def disjoint(g):
    """The rows of a report in a stratum are disjoint subsets without a total (AR10 v4)."""
    if len(g) < 2:
        return False
    src = g.source_raw.fillna("").astype(str).str.strip().str.lower()
    distinct_src = src.ne("").all() and src.nunique() == len(g)
    per = list(zip(g.row_period_start, g.row_period_end))
    have_per = all(pd.notna(p[0]) for p in per)
    no_overlap = have_per and all(not V.periods_overlap(per[i][0], per[i][1], per[j][0], per[j][1])
                                  for i in range(len(per)) for j in range(i + 1, len(per)))
    if not (distinct_src or no_overlap):
        return False
    n = sorted(g.n_tested.astype(float), reverse=True)
    return n[0] < sum(n[1:])          # no row is the total of the others


def select_rows(x, exclude_ar20, sums):
    """AR10 v4: one row per report and stratum. Same order as v1 (method, criterion, most isolates,
    lowest row_id); if the rows of the best method are disjoint subsets without a total, they are summed."""
    d = x[~x.ar20] if exclude_ar20 else x
    out = []
    for key, g in d.groupby(["study_id"] + STRATUM, sort=False):
        g = g.sort_values(["method_rank", "crit_pref", "n_tested", "row_id"], ascending=[True, True, False, True])
        best = g[(g.method_rank == g.method_rank.iloc[0]) & (g.crit_pref == g.crit_pref.iloc[0])]
        if disjoint(best):
            r = best.iloc[0].copy()
            r["events"], r["n_tested"] = int(best.events.sum()), int(best.n_tested.sum())
            r["row_id"] = "+".join(best.row_id.astype(str))
            r["ar10_summed"] = True
            r["verified"] = "YES" if (best.verified == "YES").all() else "NO"
            out.append(r)
            sums.append({"variant": "main" if exclude_ar20 else "all", "study_id": key[0],
                         **dict(zip(STRATUM, key[1:])), "rows": r["row_id"], "events": r["events"],
                         "n_tested": r["n_tested"], "sources": " | ".join(best.source_raw.fillna("").astype(str))})
        else:
            r = g.iloc[0].copy()
            r["ar10_summed"] = False
            out.append(r)
    return pd.DataFrame(out)


def collections(studies, cand, merges):
    """AR1 plus the round-2 merges (B03), by transitive closure."""
    parent = {r: r for r in studies.study_id}

    def find(v):
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    def union(a, b):
        if a in parent and b in parent:
            ra, rb = find(a), find(b)
            parent[max(ra, rb)] = min(ra, rb)

    cand = cand[cand.report_id.isin(parent)].dropna(subset=["period_start"])
    for _, g in cand.groupby("candidate_group"):
        iv = [(r, s, e if pd.notna(e) else s) for r, s, e in zip(g.report_id, g.period_start, g.period_end)]
        for i in range(len(iv)):
            for j in range(i + 1, len(iv)):
                if iv[i][1] <= iv[j][2] and iv[j][1] <= iv[i][2]:
                    union(iv[i][0], iv[j][0])
    for a, b in zip(merges.report_a, merges.report_b):
        union(a, b)
    return {r: "COL_" + find(r) for r in parent}


def research_groups(studies, cand, reports):
    """AR13, as in v1."""
    first_group = cand.groupby("report_id").candidate_group.min()
    inst = reports.set_index("report_id")["programme_institution_raw"]
    out = {}
    for r in studies.study_id:
        if r in first_group.index:
            out[r] = f"CG{int(first_group[r])}"
        elif r in inst.index and pd.notna(inst[r]) and norm(str(inst[r]).split(";")[0]):
            out[r] = "INST:" + norm(str(inst[r]).split(";")[0])
        else:
            out[r] = "REP:" + r
    return out


def mark_main(x, mask):
    """AR2: in each stratum, one report per collection, the one with most isolates tested (ties: most
    recent, lowest study_id). Only among the rows of mask."""
    x = x.copy()
    x["main"] = False
    d = x[mask].sort_values(["n_tested", "year", "study_id"], ascending=[False, False, True])
    keep = d[~d.duplicated(["collection_id"] + STRATUM, keep="first")].index
    x.loc[keep, "main"] = True
    return x


def strata_summary(x):
    rows = []
    for key, g in x.groupby(STRATUM, sort=True):
        m = g[g.main]
        if not len(m):
            continue
        n = m.n_tested.sum()
        rows.append(dict(zip(STRATUM, key), k_collections=len(m), research_groups=m.research_group.nunique(),
                         events=int(m.events.sum()), isolates=int(n),
                         largest_collection_pct=round(100 * m.n_tested.max() / n, 1) if n else None,
                         flagged_main_rows=int(m.regime_flag.fillna("").str.contains(
                             "|".join(V.SX1_FLAGS)).sum()),
                         unverified_main_rows=int((m.verified != "YES").sum()),
                         k_reports_all=int(g.study_id.nunique()),
                         meets_minimum=bool(len(m) >= MIN_K and m.research_group.nunique() >= MIN_G)))
    return pd.DataFrame(rows)


def newest_dataset(provisional):
    pat = "10_phase8_analysis/data/analysis_dataset_v3_*"
    ds = sorted(d for d in glob.glob(pat) if os.path.isdir(d) and d.endswith("_PROVISIONAL") == provisional)
    if not ds:
        sys.exit(f"There is no v3 dataset {'PROVISIONAL' if provisional else 'FINAL'}: run first "
                 "build_analysis_dataset_v3.py" + (" --provisional" if provisional else ""))
    return ds[-1]


def main():
    provisional = "--provisional" in sys.argv[1:]
    global MATRIX
    over = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--matrix=")]
    if over:
        MATRIX = over[0]
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    D = newest_dataset(provisional)
    IN = {"rules": RULES, "decisions": DECISIONS, "matrix": MATRIX, "studies": f"{D}/studies.csv",
          "ast": f"{D}/ast.csv", "merges": f"{D}/collection_merges.csv",
          "candidates": f"{T}/collection_candidates.csv", "reports": f"{T}/reports.csv"}
    for k, p in IN.items():
        if not os.path.exists(p):
            sys.exit(f"Missing input {k}: {p}")
    studies = pd.read_csv(IN["studies"], low_memory=False)
    ast = pd.read_csv(IN["ast"], low_memory=False)
    merges = pd.read_csv(IN["merges"])
    cand = pd.read_csv(IN["candidates"])
    reports = pd.read_csv(IN["reports"], low_memory=False)[["report_id", "programme_institution_raw"]]
    # (2026-10-27) round 3 (reference-list check): its reports carry their institution in their own tidy tables
    r3 = "10_phase8_analysis/data/tidy_tables_r3_reference_check_v1_2026-10-27/reports.csv"
    if os.path.exists(r3):
        IN["reports_r3"] = r3
        reports = pd.concat([reports, pd.read_csv(r3)[["report_id", "programme_institution_raw"]]], ignore_index=True)
    mx = load_matrix(MATRIX)
    excluded, sums = {}, []
    x = long_table(ast, studies, mx, excluded)
    x["regime_flag"] = x.regime_flag_v3.fillna("")
    sel_main = select_rows(x, exclude_ar20=True, sums=sums)
    sel_all = select_rows(x, exclude_ar20=False, sums=sums)
    sel_main["sel_main"], sel_all["sel_all"] = True, True
    keycols = ["study_id"] + STRATUM
    y = sel_all.merge(sel_main[keycols + ["row_id", "sel_main"]].rename(columns={"row_id": "row_id_main"}),
                      on=keycols, how="outer")
    # rows that are only in the main selection (should not happen) or with a different chosen row
    only_main = y.row_id.isna()
    if only_main.any():
        sys.exit("A main row does not appear in the complete selection: do not continue, report it")
    diff = y.sel_main.fillna(False) & (y.row_id != y.row_id_main)
    if diff.any():
        # the report has a preferred AR20 row in the complete selection and another in the main one:
        # both are kept, each marked with its variant
        extra = sel_main.merge(y.loc[diff, keycols], on=keycols)
        extra["sel_all"] = False
        y.loc[diff, "sel_main"] = False
        y = pd.concat([y, extra], ignore_index=True)
    y["sel_main"] = y.sel_main.fillna(False).astype(bool)
    y["sel_all"] = y.sel_all.fillna(False).astype(bool)
    col = collections(studies, cand, merges)
    rg = research_groups(studies, cand, reports)
    y["collection_id"], y["research_group"] = y.study_id.map(col), y.study_id.map(rg)
    y = mark_main(y, y.sel_main & ~y.c5_broad.astype(bool))
    strata = strata_summary(y)
    met = strata[strata.meets_minimum]
    cover = y[y.main].merge(met[STRATUM], on=STRATUM)
    cover = cover[cover.verified != "YES"][["row_id", "study_id", "study_label"] + STRATUM + ["events", "n_tested"]]

    sizes = pd.Series(col).value_counts()
    multi = sorted(sizes[sizes > 1].index)
    members = pd.DataFrame({"report_id": list(col), "collection_id": list(col.values())})
    trace = members[members.collection_id.isin(multi)].merge(
        studies[["study_id", "study_label", "year", "period_start", "period_end", "n_tropicalis"]],
        left_on="report_id", right_on="study_id", how="left").drop(columns="study_id")
    trace["research_group"] = trace.report_id.map(rg)
    trace["merged_by_round2"] = trace.report_id.isin(set(merges.report_a) | set(merges.report_b))

    tag = "_PROVISIONAL" if provisional else ""
    if not provisional and len(cover):
        f = os.path.join(OUT, f"verification_coverage_v2_{datetime.now().strftime('%Y-%m-%dT%H%M%S')}.csv")
        cover.to_csv(f, index=False)
        sys.exit(f"{len(cover)} main rows of strata that meet AR12 are not verified (list in {f}). "
                 "Verify them in B02 (priority 4) and build the v3 dataset again.")
    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S") + tag
    os.makedirs(LOG_DIR, exist_ok=True)
    f = {n: os.path.join(OUT, f"{n}_v2_{stamp}.csv") for n in
         ("ma_input", "ma_strata", "ec12_collections", "ar10_sums", "verification_coverage")}
    for p in f.values():
        if os.path.exists(p):
            sys.exit(f"Already exists {p}: not overwritten")
    keep = ["row_id", "study_id", "study_label", "collection_id", "research_group", "main", "sel_main", "sel_all",
            "compartment", "agent", "agent_class", "outcome", "regime", "regime_stratum", "regime_flag", "regime_basis",
            "d4_detail", "events", "n_tested", "method", "method_rank", "interp_standard", "interp_documents", "bp_type",
            "year", "period_start", "period_end", "country_iso3", "who_region", "species_id_v3", "ar20", "ar20_reason",
            "c5_reading", "c5_broad", "ar10_summed", "verified", "entry_route"]
    y = y.sort_values(STRATUM + ["main", "study_id"], ascending=[True] * 4 + [False, True])
    y[keep].to_csv(f["ma_input"], index=False)
    strata.to_csv(f["ma_strata"], index=False)
    trace.sort_values(["collection_id", "report_id"]).to_csv(f["ec12_collections"], index=False)
    pd.DataFrame(sums).to_csv(f["ar10_sums"], index=False)
    cover.to_csv(f["verification_coverage"], index=False)
    log = {"script": os.path.basename(__file__), "mode": "PROVISIONAL" if provisional else "FINAL",
           "run_time": datetime.now().astimezone().isoformat(timespec="seconds"),
           "python": platform.python_version(), "pandas": pd.__version__,
           "inputs": {k: {"path": p, "md5": md5(p)} for k, p in IN.items()},
           "outputs": {os.path.basename(p): md5(p) for p in f.values()},
           "excluded_rows_by_reason": excluded,
           "rows": len(y), "rows_sel_main": int(y.sel_main.sum()), "rows_sel_all": int(y.sel_all.sum()),
           "main_rows": int(y.main.sum()), "ar10_sums": len(sums),
           "collections_with_2plus_reports": len(multi), "reports_in_them": int(len(trace)),
           "round2_merges": len(merges), "strata": len(strata), "strata_meeting_minimum": len(met),
           "strata_meeting_minimum_by_compartment": met.compartment.value_counts().sort_index().to_dict(),
           "unverified_main_rows_in_AR12_strata": len(cover)}
    with open(os.path.join(LOG_DIR, f"04_ma_input_v2_{stamp}.json"), "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False, default=str)
    print("Dataset:", D)
    print("Rules:", RULES, "MD5", log["inputs"]["rules"]["md5"])
    print("Rows excluded by reason:")
    for k, v in sorted(excluded.items(), key=lambda kv: -kv[1]):
        print(f"  {v:5d}  {k}")
    print(f"Rows selected: main {log['rows_sel_main']}, complete {log['rows_sel_all']}; main (AR2) {log['main_rows']}")
    print(f"AR10 v4 sums: {len(sums)}; collection merges of round 2: {len(merges)}")
    print(f"Strata: {len(strata)}; meet AR12: {len(met)}", log["strata_meeting_minimum_by_compartment"])
    print(f"Unverified main rows in strata that meet AR12: {len(cover)}")
    for k, p in f.items():
        print(f"{k}: {p}")


if __name__ == "__main__":
    main()
