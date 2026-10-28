#!/usr/bin/env python3
"""13_tabS_lists_v1.py (2026-10-24)

Lists of the supplementary material that were missing (audit of 2026-10-24, "Material missing for submission"),
in the style of the other tables. All come from files already produced by the chain; this script
decides nothing, it only formats and checks that the sources are from the same run.

  S6   Included reports: collection, entry route, contribution to the meta-analysis, risk-of-bias judgement.
  S7   Reports assessed at full text and excluded, with their main reason and the phase (PRISMA 16b).
  S8   Risk of bias per report, RB1 to RB9 and overall judgement (PRISMA 18).
  S9   Applicability matrix of clinical breakpoints by document or version and agent (D4).
  S10  Exploratory meta-regression (AR21), if the output of 12_ma_metareg_v1.R exists.
  S11  Records not retrieved versus assessed, by publication period, record type and language.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/13_tabS_lists_v1.py [--provisional] [--check]
Outputs (never overwritten): 12_documents/supplementary/tables/tabS06..S11_*_v1_<date-time>[_PROVISIONAL].xlsx and
their CSV mirror; log in 10_phase8_analysis/results/logs/tabS_lists_v1_<date-time>.json.
"""
import csv
import glob
import json
import os
import platform
import re
import sys
from collections import Counter
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dataset_v3_core as C  # noqa: E402
import table_helpers as T  # noqa: E402
import table_notes_v2 as N  # noqa: E402

OUT_DIR = "12_documents/supplementary/tables"
LOG_DIR = os.path.join(N.RES, "logs")
RULES = "10_phase8_analysis/analysis_rules_v4_2026-10-24.md"
FT = "07_phase5_full_text_screening/full_text_screening.xlsx"
RIS = "06_phase4_title_abstract_screening/import/screening_reviewer_1_reviewer_2_n22203_seed1310202643.ris"
R_MAP = "07_phase5_full_text_screening/r_stream_screen_id_map_2026-10-24.csv"
B06 = "08_phase6_data_extraction/verification/round2_2026-10-24/r2_b06_r_stream_ambiguous.xlsx"
MATRIX = "10_phase8_analysis/applicability/cbp_applicability_v1_2026-10-24.csv"
SP = ("i", "C. tropicalis")
ABBR = ("CLSI, Clinical and Laboratory Standards Institute; EUCAST, European Committee on Antimicrobial Susceptibility "
        "Testing; WHO, World Health Organization.")

R3_CAND = "07_phase5_full_text_screening/reference_check_2026-10-27/reference_check_candidates_v1_*.csv"
ENTRY = {"analysis_v2": "Full-text screening", "doubtful_2026_10_20": "Doubtful report, round-2 review",
         "extraction_exclusion_review": "Extraction-stage exclusion, round-2 review",
         "blind_sample_arbitration": "Blind-sample arbitration",
         "reference_check_2026_10_27": "Reference-list check, round 3"}
STAGE = {"full_text_screening": "Full-text screening",
         "extraction_country_inferred_from_affiliation": "Extraction: country only inferable from affiliation",
         "species_identification_triage_2026_10_23": "Extraction: species identification triage",
         "same_pdf_as_another_report": "Extraction: same document as another report",
         "round2_doubtful_review": "Round 2: doubtful reports",
         "round2_extraction_exclusion_review": "Round 2: extraction-stage exclusions",
         "round2_extraction_exclusion_review_pending": "Round 2: extraction-stage exclusions, pending",
         "round2_row_verification_B02": "Round 2: verification of meta-analysis rows",
         "round2_blind_sample_arbitration": "Round 2: blind-sample arbitration"}
RB_VAL = {"Yes": "Yes", "No": "No", "Unclear": "Unclear", "Not applicable": "Not applicable"}
JUDGEMENT = {"High": "High", "Moderate": "Moderate", "Low": "Low"}
RB_HEAD = [("RB1", "sampling frame and method"), ("RB2", "subjects and setting described"),
           ("RB3", "coverage of the identified sample"), ("RB4", "species identification"),
           ("RB5", "testing method with a standard"), ("RB6", "criterion with document and version"),
           ("RB7", "denominator per agent"), ("RB8", "declared deduplication"),
           ("RB9", "sampling-site documentation")]
APPLIC = {"YES": "Published", "NO": "None", "NS_only": "Susceptible category only", "IE": "Insufficient evidence",
          "UNVERIFIED": "Not verified"}
METHOD = {"broth": "Broth dilution", "disk": "Disk diffusion", "any": "Any"}
MR_STATUS = {"fitted": "Fitted", "fewer_than_10_collections": "Fewer than 10 collections with data",
             "single_usable_level": "Fewer than two levels with at least 3 collections",
             "no_fit": "Model did not converge", "not_fitted_in_check": "Not fitted (check run)"}
COVARIATE = {"method": "Susceptibility testing method", "who_region": "WHO region",
             "rob_high": "Overall risk of bias of the index report", "species_id": "Species identification method",
             "editorial": "Editorial status"}


def newest(pat, prov, required=True):
    f = sorted(x for x in glob.glob(pat) if x.endswith("_PROVISIONAL.csv") == prov or x.rstrip("/").endswith("_PROVISIONAL") == prov)
    if not f:
        if required:
            sys.exit(f"There is no {pat}" + (" PROVISIONAL" if prov else " FINAL"))
        return None
    return f[-1]


def write(path_x, path_c, sheet, number, caption, headers, widths, blocks, notes):
    for p in (path_x, path_c):
        if os.path.exists(p):
            sys.exit(f"Already exists {p}: not overwritten")
    T.write_table(path_x, sheet, number, caption, headers, widths, blocks, notes)
    with open(path_c, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["block"] + [T.plain(h) for h in headers])
        for lab, rows in blocks:
            for r in rows:
                w.writerow([lab or ""] + [T.plain(c[0] if isinstance(c, tuple) else c) for c in r])
    return sum(len(r) for _, r in blocks)


def txt(v):
    return "" if T.miss(v) else str(v).strip()


def year(v):
    try:
        return str(int(float(v)))
    except (TypeError, ValueError):
        return T.DASH


def cap(prov, parts):
    return ([("i", "[PROVISIONAL] ")] if prov else []) + parts


def prov_note(prov):
    return [("P", "PROVISIONAL: round-2 verification decisions pending; not for the manuscript.")] if prov else []


# --------------------------------------------------------------------------------------------- S6

def s6(st, mi, pooled, ec12, rob, prov):
    main = mi[mi["main"].astype(str) == "True"]
    key = main[["compartment", "agent", "outcome", "regime_stratum"]].astype(str).agg(" | ".join, axis=1)
    main = main.assign(_k=key)
    in_pooled = main[main._k.isin(pooled)].groupby("study_id")._k.nunique()
    in_main = main.groupby("study_id")._k.nunique()
    coll = dict(zip(ec12.report_id, ec12.collection_id))
    jg = dict(zip(rob.study_id, rob.overall_judgement))
    rows = []
    for r in st.sort_values(["study_label", "study_id"]).to_dict("records"):
        sid = r["study_id"]
        rows.append([sid, txt(r["study_label"]), year(r["year"]), txt(r["country_iso3"]) or T.DASH,
                     txt(r["who_region"]) or T.DASH, txt(r["compartments"]).replace(";", ", ") or T.DASH,
                     ENTRY.get(r["entry_route"], r["entry_route"]),
                     "Distribution only" if r["sq1_only"] == "YES" else "Distribution and susceptibility",
                     coll.get(sid, "COL_" + sid), f"{int(in_main.get(sid, 0))}", f"{int(in_pooled.get(sid, 0))}",
                     JUDGEMENT.get(jg.get(sid), T.DASH)])
    headers = ["Report ID", "Report", "Year", "Country", "WHO region", "Compartments", "Entry", "Contribution",
               "Collection", "Strata as index report", "Pooled strata as index report", "Overall risk of bias"]
    widths = [9, 20, 6, 8, 8, 12, 22, 16, 13, 9, 9, 10]
    n_multi = ec12.collection_id.nunique()
    notes = [
        ("1", f"Collection: reports of the same collection share an identifier (rule AR1 plus the round-2 merges; "
              f"{len(ec12)} reports in {n_multi} multi-report collections); every other report is its own collection."),
        ("2", "Index report: within each stratum one report per collection enters the analysis, the one with most isolates "
              "tested against the agent (AR2). Pooled strata are those meeting the minimum condition and the "
              "non-pooling rule."),
        ("3", "Risk of bias was assessed for the reports eligible for the meta-analysis (RB1 to RB9, Table S8); a dash "
              "means the report contributes only to the compartment distribution."),
        ("4", "Country as ISO 3166-1 alpha-3 code; MULTI, multinational collection. " + ABBR),
    ] + prov_note(prov)
    caption = cap(prov, ["Reports of the included studies of ", SP, ", with their collection, route of entry and "
                         "contribution to the synthesis."])
    return headers, widths, [(None, rows)], notes, caption


# --------------------------------------------------------------------------------------------- S7

def s7(ex, info, prov, r3=None):
    rows = []
    order = ex.code.value_counts().index.tolist()
    blocks = []
    for code in order:
        sub = ex[ex.code == code].sort_values("report_id")
        rows = []
        for r in sub.to_dict("records"):
            i = info.get(r["report_id"], {})
            rows.append([r["report_id"], txt(i.get("title")) or T.DASH, year(i.get("year")), txt(i.get("doi")) or T.DASH,
                         STAGE.get(r["stage"], r["stage"])])
        blocks.append((f"{code}. {sub.label.iloc[0]} ({len(sub):,})", rows))
    # (2026-10-28) reports of the reference-list check (other methods column of Figure 1): excluded and not retrieved
    if r3 is not None and len(r3):
        lab = dict(zip(ex.code, ex.label))
        for dec, title in (("EXCLUDED", "Reference-list check, round 3: excluded"),
                           ("NOT_RETRIEVED", "Reference-list check, round 3: not retrieved (no open or free full text)")):
            sub = r3[r3.decision == dec].sort_values("report_id")
            if len(sub):
                blocks.append((f"{title} ({len(sub):,})",
                               [[r["report_id"], txt(r["title"]) or T.DASH, year(r["year"]), txt(r["doi"]) or T.DASH,
                                 f"{r['ec']}. {lab.get(r['ec'], '')}" if dec == "EXCLUDED" else "Not retrieved"]
                                for r in sub.to_dict("records")]))
    headers = ["Report ID", "Title", "Year", "DOI", "Stage"]
    widths = [9, 70, 6, 26, 30]
    notes = [
        ("1", "One main reason per report, the first criterion that the report fails in the order of the protocol. The "
              "counts per reason are those of the PRISMA flow diagram (Figure 1), computed from the same files."),
        ("2", "Round 2: second verification of 24 October 2026 on the doubtful reports, the reports excluded at data "
              "extraction and a blind sample of excluded reports (deviations declared in the Methods)."),
    ] + ([("3", "Reference-list check: reports cited by four previous reviews and not found by the search (other methods "
                 "column of Figure 1); they are not counted in the blocks above.")] if r3 is not None and len(r3) else []) + prov_note(prov)
    caption = cap(prov, ["Reports of ", SP, " assessed in full text and excluded, by main reason."])
    return headers, widths, blocks, notes, caption


# --------------------------------------------------------------------------------------------- S8

def reason_en(s):
    s = txt(s)
    rules = [(r"^No in (.*)$", r"No in \1"), (r"^two or more No among the rest: (.*)$", r"Two or more No among the others: \1"),
             (r"^one No: (.*)$", r"One No: \1"), (r"^three or more Unclear: (.*)$", r"Three or more Unclear: \1"),
             (r"^no No or Unclear$", "No No and no Unclear"), (r"^no No, (\d+) Unclear: (.*)$", r"No No; \1 Unclear: \2")]
    for a, b in rules:
        if re.match(a, s):
            return re.sub(a, b, s)
    return s or T.DASH


def s8(rob, prov):
    rows = []
    for r in rob.sort_values(["study_label", "study_id"]).to_dict("records"):
        rows.append([r["study_id"], txt(r["study_label"]), year(r["year"]), txt(r["compartments"]).replace(";", ", ")]
                    + [RB_VAL.get(txt(r[k]), txt(r[k]) or T.DASH) for k, _ in RB_HEAD]
                    + [JUDGEMENT.get(r["overall_judgement"], r["overall_judgement"]), reason_en(r["judgement_reason"])])
    headers = ["Report ID", "Report", "Year", "Compartments"] + [f"{k}, {v}" for k, v in RB_HEAD] + ["Overall", "Basis"]
    widths = [9, 18, 6, 10] + [10] * 9 + [9, 24]
    n_prov = int(rob.provisional.notna().sum()) if "provisional" in rob.columns else 0
    notes = [
        ("1", "Criteria adapted from the Joanna Briggs Institute checklist for prevalence studies and the six "
              "microbiological surveillance domains of the protocol; three pairs that rest on the same field are "
              "collapsed (RB1, RB4, RB5) and JBI items 3, 8 and 9 are not assessed (risk-of-bias rules, sections 1 and 4)."),
        ("2", "Overall: High with No in RB8 or RB4, or two or more No among the other criteria; Moderate with one No or "
              "three or more Unclear; Low otherwise. RB9 applies only to compartments C2 to C6."),
        ("3", "RB8 was extracted by two reviewers reading the full text; the other criteria are derived from the extraction "
              "form. The judgement is carried to the collection through the index report of each stratum."),
    ] + ([("4", f"{n_prov} reports assessed in round 2 carry provisional values (RB8 or editorial status not yet coded).")]
         if n_prov else []) + prov_note(prov)
    caption = cap(prov, ["Risk of bias by report, ", SP, " reports eligible for the meta-analysis."])
    return headers, widths, [(None, rows)], notes, caption


# --------------------------------------------------------------------------------------------- S9

def yr(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return T.DASH
    return f"{x:.2f}".rstrip("0").rstrip(".") if x % 1 else str(int(x))


def s9(mx, prov):
    blocks = []
    for (std, scope), g in mx.groupby(["standard", "scope"], sort=False):
        rows = []
        for r in g.to_dict("records"):
            src = re.split(r"\s*\|\s*", txt(r["source"]))
            rows.append([txt(r["key"]), txt(r["agent"])[:1].upper() + txt(r["agent"])[1:], METHOD.get(r["method_scope"], r["method_scope"]),
                         f"{yr(r['valid_from'])}{T.EN}{yr(r['valid_to'])}", APPLIC.get(r["applicable"], r["applicable"]),
                         txt(r["note"]) or T.DASH, "; ".join(x for x in src[1:] if x) or T.DASH])
        blocks.append((f"{std}, by {'document' if scope == 'document' else 'version'}", rows))
    headers = ["Document or version", "Agent", "Method", "In force", "Clinical breakpoint for C. tropicalis", "Note", "Source"]
    widths = [14, 14, 11, 11, 16, 50, 40]
    notes = [
        ("1", "A row for resistance by clinical breakpoint enters the analysis only when the document or version applied "
              "published a clinical breakpoint for C. tropicalis and that agent (Published); Susceptible category only "
              "admits no resistance stratum; None, Insufficient evidence and Not verified leave the row out of the "
              "resistance outcome (decision D4 of 24 October 2026, applied before the analyses were re-run)."),
        ("2", "In force: years of validity, with decimals for EUCAST versions dated within a year. Rows without a "
              "declared version are placed by the year in which the breakpoints were applied (rules v4, rule 1)."),
        ("3", "Not verified: the value could not be confirmed in a primary or secondary source; those rows are counted "
              "and reported as unverified, never assumed."),
        ("4", ABBR),
    ] + prov_note(prov)
    caption = cap(prov, ["Applicability of clinical breakpoints for ", SP, " by interpretive document or version and agent."])
    return headers, widths, blocks, notes, caption


# -------------------------------------------------------------------------------------------- S10

def s10(mr, prov):
    rows = []
    for r in mr.sort_values(["stratum", "covariate"]).to_dict("records"):
        p = T.DASH
        if not T.miss(r.get("lrt_p")):
            x = float(r["lrt_p"])
            p = f"{x:.3f}" if x >= 0.001 else "<0.001"
        chi = T.DASH if T.miss(r.get("lrt_chisq")) else f"{float(r['lrt_chisq']):.2f} ({int(float(r['lrt_df']))})"
        red = T.DASH if T.miss(r.get("tau2_reduction")) else f"{100 * float(r['tau2_reduction']):.0f}"
        t2 = (T.DASH if T.miss(r.get("tau2_null")) else
              f"{float(r['tau2_null']):.2f} to {float(r['tau2_cov']):.2f}")
        c_, a_, o_, rs_ = (txt(r["stratum"]).split(" | ") + ["", "", "", ""])[:4]
        lab_ = f"{c_}, {a_}, {'non-wild-type' if o_ == 'NWT' else 'resistant'}, {T.CRITERION.get(rs_, rs_)}"
        rows.append([lab_, COVARIATE.get(r["covariate"], r["covariate"]),
                     f"{int(float(r['k']))}" if not T.miss(r.get("k")) else T.DASH, txt(r.get("levels")) or T.DASH,
                     chi, p, t2, red, txt(r.get("coefficients")) or T.DASH, MR_STATUS.get(r["status"], r["status"])])
    n_fit = int((mr.status == "fitted").sum())
    headers = ["Stratum", "Covariate", "*k*", "Levels (collections)", "Likelihood ratio chi-square (df)",
               "*P*", T.TAU2 + ", without to with covariate", T.TAU2 + " reduction, %", "Coefficients, logit (95% CI)", "Status"]
    widths = [30, 20, 6, 30, 12, 7, 14, 9, 40, 22]
    notes = [
        ("1", "Exploratory meta-regression (rule AR21): one covariate at a time, in pooled strata with at least 10 "
              "collections with data on the covariate; levels with fewer than 3 collections are grouped as other levels. "
              "Binomial-normal generalised linear mixed model with the covariate as fixed effect (adaptive Gauss-Hermite "
              "quadrature, 7 points); coefficients against the most frequent level."),
        ("2", f"{n_fit} models fitted; no correction for multiplicity. Compartment, clade, period and criterion version "
              "are not used here: they belong to hypotheses deferred to the second report (decision D1)."),
        ("3", "Associations between collections, not effects: the covariates are confounded with country, period and "
              "laboratory. " + ABBR),
    ] + prov_note(prov)
    caption = cap(prov, ["Exploratory meta-regression of the between-collection heterogeneity, ", SP, "."])
    return headers, widths, [(None, rows)], notes, caption


# -------------------------------------------------------------------------------------------- S11

RIS_FIELDS = "06_phase4_title_abstract_screening/import/screening_record_fields_n22203_2026-10-28.csv"


def ris_fields(path):
    if not os.path.exists(path):  # (2026-10-28) the RIS is not in the public repository: same fields from its extract
        f = pd.read_csv(RIS_FIELDS, dtype=str, keep_default_na=False)
        return {r["screen_id"]: {t: r[t] for t in ("TY", "Y1", "LA") if r[t]} for r in f.to_dict("records")}
    out, cur, sid = {}, {}, None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            tag = ln[:2]
            if ln.startswith("ER  -"):
                if sid:
                    out[sid] = cur
                cur, sid = {}, None
            elif ln[2:6] == "  - ":
                v = ln[6:].strip()
                if tag == "N1" and v.startswith("SCREEN_ID "):
                    sid = v[10:].strip()
                elif tag in ("TY", "Y1", "LA") and tag not in cur:
                    cur[tag] = v
    return out


def band(y):
    try:
        y = int(str(y)[:4])
    except (TypeError, ValueError):
        return "Not recorded"
    if y < 2000:
        return "Before 2000"
    if y < 2010:
        return "2000" + T.EN + "2009"
    if y < 2015:
        return "2010" + T.EN + "2014"
    if y < 2020:
        return "2015" + T.EN + "2019"
    return "2020" + T.EN + "2026"


def kind(t):
    t = (t or "").upper()
    return {"JOUR": "Journal article", "THES": "Thesis", "CONF": "Conference", "CPAPER": "Conference",
            "ABST": "Conference", "CHAP": "Book or chapter", "BOOK": "Book or chapter"}.get(t, "Other" if t else "Not recorded")


def lang(v):
    v = (v or "").strip().lower()
    if not v:
        return "Not recorded"
    for pat, lab in ((r"^(en|eng)", "English"), (r"^(es|spa)", "Spanish"), (r"^(pt|por)", "Portuguese"),
                     (r"^(zh|chi|chn|中)", "Chinese"), (r"^(ja|jpn|jap)", "Japanese")):
        if re.match(pat, v):
            return lab
    return "Other"


def s11(nr, ft_ids, to_screen, ris, sought_n, prov):
    nr_scr = set(nr.screen_id.dropna().astype(str)) - {""}
    lost_after = set(nr.loc[nr.cause != "not_obtained", "screen_id"].dropna().astype(str))
    assessed = {to_screen(i) for i in ft_ids} - lost_after - {""}
    groups = {"Not retrieved": nr_scr, "Assessed": assessed}
    blocks = []
    for lab, fn, field in (("Publication period", band, "Y1"), ("Record type", kind, "TY"), ("Language of the record", lang, "LA")):
        rows = []
        cnt = {g: Counter(fn(ris.get(i, {}).get(field)) for i in ids) for g, ids in groups.items()}
        order_y = ["Before 2000", "2000" + T.EN + "2009", "2010" + T.EN + "2014", "2015" + T.EN + "2019",
                   "2020" + T.EN + "2026", "Not recorded"]
        cats = sorted(set(cnt["Not retrieved"]) | set(cnt["Assessed"]),
                      key=lambda c: (order_y.index(c),) if field == "Y1" else
                      (c == "Not recorded", -cnt["Not retrieved"].get(c, 0) - cnt["Assessed"].get(c, 0)))
        for c in cats:
            a, b = cnt["Not retrieved"].get(c, 0), cnt["Assessed"].get(c, 0)
            rows.append([c, f"{a:,}", T.pct(a / len(nr_scr)) if nr_scr else T.DASH, f"{b:,}",
                         T.pct(b / len(assessed)) if assessed else T.DASH,
                         T.pct(a / (a + b)) if a + b else T.DASH])
        blocks.append((lab, rows))
    headers = ["Category", "Not retrieved, *n*", "Not retrieved, %", "Assessed, *n*", "Assessed, %",
               "Not retrieved within the category, %"]
    widths = [22, 12, 11, 12, 11, 14]
    notes = [
        ("1", f"Records sought for retrieval after title and abstract screening, by whether a correct full text was "
              f"assessed ({len(assessed):,}) or not ({len(nr_scr):,}); not retrieved includes full texts that were another "
              f"work or truncated. Percentages by column within each characteristic, and by row in the last column. "
              f"Records sought according to the PRISMA count: {sought_n:,}."),
        ("2", "Characteristics as recorded in the bibliographic record used for screening; the language field was empty "
              "in most records, so the language rows describe only the records that carry it."),
        ("3", "The research group discarded contact with authors and interlibrary loan as retrieval routes; the "
              "proportion not retrieved is a limitation declared in the Discussion."),
    ] + prov_note(prov)
    caption = cap(prov, ["Records of ", SP, " reports sought for retrieval: not retrieved versus assessed, by publication "
                         "period, record type and language."])
    return headers, widths, blocks, notes, caption, len(assessed), len(nr_scr)


def main():
    prov = N.mode()
    check = "--check" in sys.argv[1:]
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    for p in (RULES, FT, RIS, R_MAP, B06, MATRIX):
        if not os.path.exists(p):
            sys.exit(f"Missing {p}")
    D = newest("10_phase8_analysis/data/analysis_dataset_v3_*", prov)
    f_res, f_st = N.inputs(prov)
    lg06 = json.load(open(os.path.join(LOG_DIR, f"06_ma_marginal_v3_{os.path.basename(f_res)[len('ma_results_v3_'):-4]}.json"),
                          encoding="utf-8"))
    f_in = [p for p in lg06["inputs"] if os.path.basename(p).startswith("ma_input_v2_")][0]
    f_ec12 = f_in.replace("ma_input_v2_", "ec12_collections_v2_")
    lg04 = json.load(open(os.path.join(LOG_DIR, "04_ma_input_v2_" + os.path.basename(f_in)[len("ma_input_v2_"):-4] + ".json"),
                          encoding="utf-8"))
    if lg04["inputs"]["studies"]["path"] != f"{D}/studies.csv":
        sys.exit(f"{f_in} was not built with {D}")
    f_rob = newest("09_phase7_risk_of_bias/results/rob_assessment_v2_*.csv", prov)
    f_ex = newest(os.path.join(N.RES, "prisma_excluded_reports_v3_*.csv"), prov)
    f_nr = f_ex.replace("prisma_excluded_reports_v3_", "prisma_not_retrieved_v3_")
    f_pc = f_ex.replace("prisma_excluded_reports_v3_", "prisma_counts_v3_")
    lgp = json.load(open(os.path.join(LOG_DIR, "01_prisma_counts_v3_" + os.path.basename(f_ex)[len("prisma_excluded_reports_v3_"):-4]
                                      + ".json"), encoding="utf-8"))
    if lgp["inputs"]["studies"]["path"] != f"{D}/studies.csv":
        sys.exit(f"{f_ex} was not built with {D}: run 01_prisma_counts_v3.py on that dataset")
    f_mr = newest(os.path.join(N.RES, "ma_metareg_v1_*.csv"), prov, required=False)

    st = pd.read_csv(f"{D}/studies.csv", low_memory=False)
    mi = pd.read_csv(f_in, low_memory=False)
    res = pd.read_csv(f_res)
    pooled = set(res.loc[res.status == "pooled", ["compartment", "agent", "outcome", "regime_stratum"]]
                 .astype(str).agg(" | ".join, axis=1))
    ec12 = pd.read_csv(f_ec12)
    rob = pd.read_csv(f_rob)
    main_ids = set(mi.loc[mi["main"].astype(str) == "True", "study_id"])
    falt = main_ids - set(rob.study_id)
    if falt:
        sys.exit(f"{len(falt)} main reports without a risk-of-bias judgement in {f_rob}")
    ex = pd.read_csv(f_ex)
    nr = pd.read_csv(f_nr, dtype=str)
    pc = pd.read_csv(f_pc)
    sought_n = int(pc.loc[pc.item == "sought", "n"].iloc[0])
    excl_n = int(pc.loc[pc.box == "excluded", "n"].sum())
    if excl_n != len(ex):
        sys.exit(f"The list of excluded reports ({len(ex)}) does not match PRISMA ({excl_n})")
    ft = pd.read_excel(FT, sheet_name="All")
    rep = pd.read_csv(os.path.join(C.TIDY, "reports.csv"), low_memory=False)
    info = {r["report_id"]: {"title": r.get("title"), "year": r.get("year"), "doi": r.get("doi")} for r in rep.to_dict("records")}
    for r in ft.to_dict("records"):
        info[r["ID"]] = {"title": r["Title"], "year": r["Year"], "doi": r["DOI"]}
    rmap = pd.read_csv(R_MAP)
    r_to_screen = dict(zip(rmap.R_id, rmap.screen_id))
    amb = pd.read_excel(B06, sheet_name="reports", dtype=object)
    for r in amb.to_dict("records"):
        v = txt(r.get("decision_screen_id"))
        if v:
            r_to_screen[r["R_id"]] = v
    to_screen = lambda i: i if str(i).startswith("O") else r_to_screen.get(i, "")  # noqa: E731
    mx = pd.read_csv(MATRIX)
    mr = pd.read_csv(f_mr) if f_mr else None
    print(f"Dataset {D}\nInput {os.path.basename(f_in)} | results {os.path.basename(f_res)} | risk of bias "
          f"{os.path.basename(f_rob)}\nPRISMA {os.path.basename(f_pc)} | metarregresion {os.path.basename(f_mr) if f_mr else 'NONE'}")
    if check:
        print("--check: inputs aligned; nothing was written.")
        return
    print("Reading the screening RIS...")
    ris = ris_fields(RIS)

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S") + ("_PROVISIONAL" if prov else "")
    outs, counts = {}, {}

    def out(name, number, sheet, spec):
        headers, widths, blocks, notes, caption = spec[:5]
        px = os.path.join(OUT_DIR, f"{name}_v1_{stamp}.xlsx")
        pcs = os.path.join(OUT_DIR, f"{name}_v1_{stamp}.csv")
        n = write(px, pcs, sheet, number, caption, headers, widths, blocks, notes)
        outs[px], outs[pcs], counts[name] = T.md5(px), T.md5(pcs), n
        print(f"  {name}: {n} rows")

    out("tabS06_included_reports", "S6", "Table S6", s6(st, mi, pooled, ec12, rob, prov))
    rd = pd.read_csv(f"{D}/report_decisions.csv", dtype=str)
    r3 = rd[rd.source == "reference_check_2026_10_27"]
    cand = pd.read_csv(sorted(glob.glob(R3_CAND))[-1], dtype=str).set_index("report_id")
    r3 = r3.assign(title=r3.report_id.map(cand.title), year=r3.report_id.map(cand.year), doi=r3.report_id.map(cand.doi))
    out("tabS07_excluded_reports", "S7", "Table S7", s7(ex, info, prov, r3))
    out("tabS08_risk_of_bias", "S8", "Table S8", s8(rob, prov))
    out("tabS09_cbp_applicability", "S9", "Table S9", s9(mx, prov))
    if mr is not None:
        out("tabS10_metaregression", "S10", "Table S10", s10(mr, prov))
    else:
        print("  tabS10: there is no output of 12_ma_metareg_v1.R; it is not written")
    spec11 = s11(nr, ft.ID.tolist(), to_screen, ris, sought_n, prov)
    out("tabS11_not_retrieved", "S11", "Table S11", spec11)
    n_ass, n_nr = spec11[5], spec11[6]
    if n_ass + n_nr != sought_n and not prov:
        sys.exit(f"S11: assessed + not retrieved = {n_ass + n_nr}, PRISMA sought = {sought_n}")
    ins = [RULES, f"{D}/studies.csv", f_in, f_res, f_ec12, f_rob, f_ex, f_nr, f_pc, FT, R_MAP, B06, MATRIX, RIS] + ([f_mr] if f_mr else [])
    log = {"script": os.path.basename(__file__), "mode": "PROVISIONAL" if prov else "FINAL",
           "run_time": datetime.now().astimezone().isoformat(timespec="seconds"), "python": platform.python_version(),
           "inputs": {p: T.md5(p) for p in ins}, "outputs": {os.path.basename(k): v for k, v in outs.items()},
           "rows": counts, "s11": {"assessed": n_ass, "not_retrieved": n_nr, "sought_prisma": sought_n}}
    p_log = os.path.join(LOG_DIR, f"tabS_lists_v1_{stamp}.json")
    with open(p_log, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False)
    print(f"S11: assessed {n_ass:,} + not retrieved {n_nr:,} = {n_ass + n_nr:,} (PRISMA, sought: {sought_n:,})\n{OUT_DIR}\n{p_log}")


if __name__ == "__main__":
    main()
