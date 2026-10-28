#!/usr/bin/env python3
"""make_verification_books_v1.py (2026-10-24)

Workbooks of round 2 of human verification (decision D2 of team_decisions_2026-10-24.md). Each
workbook carries a proposal and its evidence; the decision is the reviewer's and is written in the empty
columns. build_analysis_dataset_v3.py reads these workbooks: if a decision is missing, it stops (or uses the
proposal in --provisional mode, which marks every output as PROVISIONAL).

The doubtful reports (316) have no new workbook: they are decided in the workbook already prepared,
07_phase5_full_text_screening/doubtful_review_2026-10-20/full_text_doubtful_review_2026-10-20.xlsx
(columns decision_reviewer_1, decision_reviewer_2, decision_final, reviewers_comment).

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/make_verification_books_v1.py --check
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/make_verification_books_v1.py
Outputs (never overwritten):
  08_phase6_data_extraction/verification/round2_2026-10-24/r2_b02 ... r2_b10 (.xlsx) and r2_b08_key.csv
  07_phase5_full_text_screening/r_stream_screen_id_map_2026-10-24.csv
  08_phase6_data_extraction/verification/round2_2026-10-24/make_verification_books_v1_<date-time>.json
"""
import math
import os
import re
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dataset_v3_core as C  # noqa: E402
import verification_rules_v1 as V  # noqa: E402

OUT = "08_phase6_data_extraction/verification/round2_2026-10-24"
R_MAP = "07_phase5_full_text_screening/r_stream_screen_id_map_2026-10-24.csv"
FT = "07_phase5_full_text_screening/full_text_screening.xlsx"
RIS = "06_phase4_title_abstract_screening/import/screening_reviewer_1_reviewer_2_n22203_seed1310202643.ris"
RAYYAN = "06_phase4_title_abstract_screening/rayyan_exports/decisions_final_postresolucion_n22203_2026-10-22.csv"
CAL_SAMPLE = "04_phase2_calibration/calibration_sample_200_seed13102026.csv"
CAL_DEC = "04_phase2_calibration/results/calibration_CAL1_final_decisions.csv"
# reference run that defines the universe to verify (none of its figures is used)
MA_INPUT = "10_phase8_analysis/results/ma_input_v1_2026-10-23T114123.csv"
MA_RESULTS = "10_phase8_analysis/results/ma_results_v2_2026-10-23T120806.csv"
ALLOC = "08_phase6_data_extraction/verification/isolate_groups_multicompartment_v1_2026-10-21.xlsx"
ROB_CONS = "09_phase7_risk_of_bias/rob_consensus_2026-10-22.xlsx"
CAND = "10_phase8_analysis/data/tidy_tables_v0_2026-10-20/collection_candidates.csv"
DUB = "07_phase5_full_text_screening/doubtful_review_2026-10-20/full_text_doubtful_review_2026-10-20.xlsx"
SEED = 20261024
SAMPLE_FRACTION = 0.20
KEY = ["compartment", "agent", "outcome", "regime_stratum"]
FONT = Font(name="Calibri", size=11, color="000000")
EC_LIST = ["EC1", "EC2", "EC3", "EC4", "EC6", "EC7", "EC8", "EC9", "EC10", "EC11", "EC12", "EC13"]


# ------------------------------------------------------------------------------------ writing
def write_book(path, title, instructions, sheets):
    """sheets: list of (name, DataFrame, {column: list of admitted values or None}, {col: width})."""
    wb = Workbook()
    ws = wb.active
    ws.title = "instructions"
    ws.append([title])
    for line in instructions:
        ws.append([line])
    for row in ws.iter_rows():
        for c in row:
            c.font = FONT
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 140
    for name, df, choices, widths in sheets:
        sh = wb.create_sheet(name)
        sh.append(list(df.columns))
        for rec in df.astype(object).where(df.notna(), None).itertuples(index=False):
            sh.append(list(rec))
        for row in sh.iter_rows():
            for c in row:
                c.font = FONT
                c.alignment = Alignment(vertical="top", wrap_text=True)
        for j, col in enumerate(df.columns, start=1):
            w = widths.get(col)
            if w is None:
                lens = df[col].map(lambda v: 0 if v is None or (isinstance(v, float) and v != v) else len(str(v)))
                q = float(lens.quantile(0.9)) if len(lens) else 0.0
                w = min(45, max(9, len(col) + 2, int(q) if q == q else 0))
            sh.column_dimensions[get_column_letter(j)].width = w
        sh.freeze_panes = "B2"
        for col, allowed in (choices or {}).items():
            if col not in df.columns or not allowed:
                continue
            j = list(df.columns).index(col) + 1
            dv = DataValidation(type="list", formula1='"' + ",".join(allowed) + '"', allow_blank=True)
            dv.error = "Value outside the list"
            sh.add_data_validation(dv)
            letter = get_column_letter(j)
            dv.add(f"{letter}2:{letter}{max(2, len(df) + 1)}")
    wb.save(path)
    return path


def blank_cols(df, cols):
    for c in cols:
        df[c] = None
    return df


# ------------------------------------------------------------------------------------- fuentes
def load_ft():
    ft = pd.read_excel(FT, sheet_name="All")
    return ft.rename(columns={"Title": "title", "Year": "year", "Journal": "journal",
                              "PDF file": "pdf_file", "Decision": "ft_decision",
                              "Main reason": "ft_reason", "Evidence": "ft_evidence"})


def parse_ris(path):
    recs, cur = [], {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            tag, val = ln[:2], ln[6:].strip()
            if ln.startswith("ER  -"):
                recs.append(cur); cur = {}
            elif ln[2:6] == "  - ":
                if tag == "N1" and val.startswith("SCREEN_ID "):
                    cur["screen_id"] = val.split()[1]
                elif tag in ("TI", "DO", "Y1", "T2", "AN"):
                    cur.setdefault(tag, val)
                elif tag == "AU":
                    cur.setdefault("AU", val)
    return pd.DataFrame(recs)


def norm_title(t):
    import unicodedata
    t = unicodedata.normalize("NFKC", str(t)).lower()
    return re.sub(r"[\W_]+", " ", t).strip()


def norm_doi(d):
    d = str(d).lower().strip()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d if d.startswith("10.") else ""


def ta_inclusions():
    ids = [ln[16:].strip() for ln in open(RIS, encoding="utf-8", errors="replace")
           if ln.startswith("N1  - SCREEN_ID ")]
    ray = pd.read_csv(RAYYAN, encoding="utf-8-sig")
    ray = ray[ray["key"] == "included"].sort_values("article_id")
    if len(ray) != len(ids):
        sys.exit("The RIS and the Rayyan export do not have the same number of records")
    dec = dict(zip(ids, ray["value"].astype(int)))
    cal = pd.read_csv(CAL_DEC, encoding="utf-8-sig")
    inc = {o for o, v in dec.items() if v == 1} | set(cal.loc[cal["decision_final"] == "Include", "work"])
    return inc


def r_stream_map(ft):
    """Pairs each 'R' report of full-text screening with its record in the screening corpus:
    DOI and title (same DOI and title similarity >= 0.9) or exact normalised title. Only among
    title and abstract inclusions."""
    import difflib
    inc = ta_inclusions()
    ris = parse_ris(RIS)
    cal = pd.read_csv(CAL_SAMPLE, encoding="utf-8-sig")
    tcol = next((c for c in cal.columns if c.lower() in ("title", "title", "title", "ti")), None)
    dcol = next((c for c in cal.columns if c.lower() in ("doi", "do")), None)
    idcol = next((c for c in cal.columns if c.lower() in ("work", "screen_id", "id")), None)
    extra = pd.DataFrame({"screen_id": cal[idcol], "TI": cal[tcol] if tcol else "",
                          "DO": cal[dcol] if dcol else ""}) if idcol else pd.DataFrame()
    corpus = pd.concat([ris, extra], ignore_index=True)
    corpus = corpus[corpus.screen_id.isin(inc)].copy()
    corpus["nt"] = corpus.TI.map(norm_title)
    corpus["nd"] = corpus.DO.fillna("").map(norm_doi)
    by_doi = corpus[corpus.nd != ""].groupby("nd").screen_id.apply(list).to_dict()
    by_title = corpus.groupby("nt").screen_id.apply(list).to_dict()
    tit = dict(zip(corpus.screen_id, corpus.nt))
    r = ft[ft.ID.astype(str).str.startswith("R")].copy()
    out = []
    for rec in r.itertuples(index=False):
        nt, nd = norm_title(rec.title), norm_doi(rec.DOI) if isinstance(rec.DOI, str) else ""
        cands, how = [], ""
        if nd and nd in by_doi:
            c = [s for s in by_doi[nd] if difflib.SequenceMatcher(None, nt, tit[s]).ratio() >= 0.9]
            if c:
                cands, how = c, "doi+title"
        if not cands and nt in by_title:
            cands, how = by_title[nt], "title"
        out.append({"R_id": rec.ID, "title": rec.title, "year": rec.year, "DOI": rec.DOI,
                    "match_method": how or "none", "k_candidates": len(cands),
                    "screen_id_candidates": ";".join(sorted(set(cands)))})
    return pd.DataFrame(out), corpus


# -------------------------------------------------------------------------------------- workbooks
def book_rows(m, t, ft, pooled_reports, flags, used, dub=None, dub_text=None):
    """B02: rows of the reports eligible for the meta-analysis, by priority. dub: (mechanical) tables
    of the doubtful reports proposed for the meta-analysis, which enter with priority 1
    because their rows only count if the reviewers confirm the inclusion in the doubtful-reports workbook."""
    parts = []
    for tb, is_dub in ((m, False), (dub, True)):
        if tb is None:
            continue
        st, a = tb["studies"], tb["ast"]
        elig = set(st.loc[st.eligible_ma_v3 == "YES", "study_id"])
        a = a[a.study_id.isin(elig) & ((a.eligible_r_cbp_v3 == "YES") | (a.eligible_nwt_ecv_v3 == "YES"))].copy()
        a = a.merge(st[["study_id", "study_label", "year", "n_tropicalis", "extraction_confidence", "pdf_file",
                        "compartments", "country", "period_start", "period_end", "design", "species_id_raw"]]
                    .rename(columns={"period_start": "study_period_start", "period_end": "study_period_end"}),
                    on="study_id", how="left")
        a["doubtful"] = is_dub
        parts.append(a)
    a = pd.concat(parts, ignore_index=True)
    rep = t["rep"].set_index("report_id")
    ev = ft.set_index("ID")["ft_evidence"]
    a["ft_evidence"] = a.study_id.map(ev)
    a["reader_text_doubtful"] = a.study_id.map(dub_text or {})
    a["flags"] = a.row_id.map(flags).fillna("")
    a.loc[a.doubtful, "flags"] = "doubtful report proposed for MA; " + a.loc[a.doubtful, "flags"]
    over = (a.n_tropicalis.notna() & (a.n_tested > a.n_tropicalis))
    a.loc[over, "flags"] = a.loc[over, "flags"] + "; n_tested > n_tropicalis"
    a["flags"] = a["flags"].str.strip("; ")
    a["used_2026_10_23"] = np.where(a.row_id.isin(used), "YES", "NO")
    pooled = a.study_id.isin(pooled_reports) | a.doubtful
    flagged = a.groupby("study_id")["flags"].transform(lambda s: (s != "").any())
    conf = a.extraction_confidence.fillna("")
    a["priority"] = np.select([pooled & (flagged | conf.eq("low")), pooled & conf.eq("medium"), pooled],
                              [1, 2, 3], 4)
    cols = ["priority", "study_id", "study_label", "year", "pdf_file", "extraction_confidence", "row_id",
            "used_2026_10_23", "compartment", "agent", "method", "interp_raw", "regime_v3", "regime_basis",
            "n_tested", "n_S", "n_SDD_I", "n_R", "n_NWT", "mic50_mg_l", "mic90_mg_l", "mic_range_raw", "unit_raw",
            "note_raw", "flags", "ft_evidence", "reader_text_doubtful"]
    out = a.sort_values(["priority", "study_id", "agent", "row_id"])[cols]
    out = blank_cols(out, ["row_action", "n_tested_v", "n_S_v", "n_SDD_I_v", "n_R_v", "n_NWT_v",
                           "compartment_v", "criterion_v", "page_or_table", "reviewer", "date", "comment"])
    reps = (a.groupby("study_id").agg(priority=("priority", "min"), study_label=("study_label", "first"),
                                      year=("year", "first"), pdf_file=("pdf_file", "first"),
                                      doubtful=("doubtful", "first"),
                                      n_rows=("row_id", "size"), confidence=("extraction_confidence", "first"),
                                      flags=("flags", lambda s: "; ".join(sorted({x for v in s for x in v.split("; ") if x}))),
                                      n_tropicalis=("n_tropicalis", "first"), compartments=("compartments", "first"),
                                      country=("country", "first"), period_start=("study_period_start", "first"),
                                      period_end=("study_period_end", "first"), design=("design", "first"),
                                      species_id_raw=("species_id_raw", "first"))
            .reset_index().sort_values(["priority", "study_id"]))
    reps["doubtful"] = np.where(reps.doubtful, "YES", "NO")
    reps = blank_cols(reps, ["report_eligible", "ec_if_not", "reviewer", "date", "comment"])
    return out, reps


AGENT_ES = {"fluconazol": "fluconazole", "voriconazol": "voriconazole", "itraconazol": "itraconazole",
            "posaconazol": "posaconazole", "isavuconazol": "isavuconazole", "ketoconazol": "ketoconazole",
            "miconazol": "miconazole", "clotrimazol": "clotrimazole", "econazol": "econazole",
            "anfotericina b": "amphotericin B", "anfotericina": "amphotericin B", "nistatina": "nystatin",
            "caspofungina": "caspofungin", "micafungina": "micafungin", "anidulafungina": "anidulafungin",
            "rezafungina": "rezafungin", "flucitosina": "flucytosine", "5-flucitosina": "flucytosine",
            "5-fluorocitosina": "flucytosine", "terbinafina": "terbinafine"}
METHODS = ["broth_microdilution_CLSI_or_unspecified", "broth_microdilution_EUCAST", "broth_macrodilution",
           "commercial_microdilution_SYO", "commercial_automated_VITEK2", "commercial_ATB_FUNGUS", "commercial_other",
           "gradient_diffusion", "disk_diffusion", "agar_dilution", "other"]


def split_top(text, sep=";"):
    """Splits by sep outside parentheses."""
    out, depth, cur = [], 0, []
    for ch in str(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == sep and depth == 0:
            out.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return [x.strip() for x in out if x.strip()]


def guess_method(raw):
    k = V.norm_text(raw)
    for pat, m in [(r"e-?test|gradient|mic ?test|liofilchem", "gradient_diffusion"),
                   (r"disco|disk|difusi", "disk_diffusion"), (r"vitek", "commercial_automated_VITEK2"),
                   (r"sensititre|yeastone|yo-?\d", "commercial_microdilution_SYO"), (r"\batb\b", "commercial_ATB_FUNGUS"),
                   (r"e\.? ?def|eucast", "broth_microdilution_EUCAST"), (r"macrodiluci|macrodilution", "broth_macrodilution"),
                   (r"microdiluci|microdilution|m27|nccls|clsi", "broth_microdilution_CLSI_or_unspecified")]:
        if re.search(pat, k):
            return m
    return "other"


def book_new_rows(dub):
    """B11: susceptibility rows of the doubtful reports proposed for the meta-analysis that have no
    rows in the tidy tables. They are prefilled with what the doubtful review of 2026-10-20 read
    (text 'meta_analysis_data', which gives table and page); the reviewer confirms or corrects."""
    rows = []
    for r in dub.itertuples(index=False):
        for item in split_top(r.meta_analysis_data):
            mm = re.match(r"\s*([^:]+):\s*(\d+)\s*/\s*(\d+)\s*([A-Za-z]+)?\s*(\((.*)\))?\s*$", item, flags=re.S)
            if not mm:
                rows.append({"report_id": r.ID, "reader_text": item, "parse": "not_read"})
                continue
            ag_raw, ev, n, _lab, _p, inner = mm.groups()
            inner = inner or ""
            parts = split_top(inner)
            crit = parts[0] if parts else ""
            loc = "; ".join(parts[1:])
            outcome = "NWT" if re.search(r"non-?wild|not wild|non-?wt|\becv\b", inner, re.I) else "R"
            rows.append({"report_id": r.ID, "study_label": None, "title": r.title, "year": r.year,
                         "pdf_file": r.pdf, "compartment": r.compartment, "agent_raw": ag_raw.strip(),
                         "agent": AGENT_ES.get(ag_raw.strip().lower(), ag_raw.strip()), "outcome": outcome,
                         "n_tested": int(n), "n_events": int(ev), "criterion_raw": crit, "location": loc,
                         "method_raw": r.susceptibility_method, "method": guess_method(r.susceptibility_method),
                         "reader_text": item, "parse": "ok"})
    out = pd.DataFrame(rows)
    out.insert(0, "new_row_id", [f"N{i+1:04d}" for i in range(len(out))])
    return blank_cols(out, ["row_action", "n_tested_v", "n_events_v", "compartment_v", "criterion_v", "method_v",
                            "page_or_table", "reviewer", "date", "comment"])


def per(a0, a1):
    f = lambda v: "" if v is None or v != v else str(int(v))  # noqa: E731
    return f"{f(a0)}-{f(a1)}"


def book_pairs(m, t, ma):
    """B03: pairs of meta-analysis reports that could be the same collection. Candidates:
    same country (or one multinational within the same programme), overlapping periods and, in addition,
    same programme, same institution (Jaccard >= 0.6 between distinctive words) or the same
    figures in a stratum with at least 10 isolates tested."""
    st = m["studies"]
    rep = t["rep"].set_index("report_id")
    elig = st[st.eligible_ma_v3 == "YES"].copy()
    col = ma.groupby("study_id").collection_id.first()
    # reports that enter through the layer of 2026-10-24 have no collection in the run of 2026-10-23
    elig["collection_id"] = elig.study_id.map(col).fillna(elig.study_id)
    for c in ("period_start", "period_end", "n_tropicalis"):
        elig[c] = pd.to_numeric(elig[c], errors="coerce").astype(float)
    inst = elig.study_id.map(rep["programme_institution_raw"]).fillna("")
    elig["inst"] = inst
    elig["programmes"] = (inst + " " + elig.title.fillna("") + " " +
                          elig.study_id.map(rep["extraction_notes"]).fillna("")).map(V.programmes_of)
    a3 = m["ast"]
    a3 = a3[(a3.eligible_r_cbp_v3 == "YES") & a3.n_R.notna()]
    cells = {}
    for r in a3.itertuples(index=False):
        if r.n_tested >= V.MIN_N_IDENTICAL:
            cells.setdefault(r.study_id, {}).setdefault((r.compartment, r.agent), set()).add((int(r.n_R), int(r.n_tested)))
    rows = []
    e = elig.to_dict("records")
    for i in range(len(e)):
        for j in range(i + 1, len(e)):
            a, b = e[i], e[j]
            if a["collection_id"] == b["collection_id"]:
                continue
            prog = a["programmes"] & b["programmes"]
            same_country = a["country_iso3"] == b["country_iso3"]
            if not same_country and not (prog and "MULTI" in (a["country_iso3"], b["country_iso3"])):
                continue
            if not V.periods_overlap(a["period_start"], a["period_end"], b["period_start"], b["period_end"]):
                continue
            jac = V.inst_jaccard(a["inst"], b["inst"])
            ca, cb = cells.get(a["study_id"], {}), cells.get(b["study_id"], {})
            ident = [k for k in sorted(set(ca) & set(cb)) if ca[k] & cb[k]]
            if not prog and jac < V.SAME_INST and not ident:
                continue
            ex = "; ".join(f"{k[0]} {k[1]}: " + ", ".join(f"{x}/{y}" for x, y in sorted(ca[k] & cb[k])) for k in ident[:3])
            p = {"programme": ";".join(sorted(prog)), "jaccard": jac, "n_a": a["n_tropicalis"], "n_b": b["n_tropicalis"],
                 "identical_counts": len(ident), "identical_example": ex,
                 "same_period": (a["period_start"], a["period_end"]) == (b["period_start"], b["period_end"]),
                 "nested": V.nested(a["period_start"], a["period_end"], b["period_start"], b["period_end"])}
            prop, why = V.pair_proposal(p)
            rows.append({"pair_id": None, "report_a": a["study_id"], "label_a": a["study_label"],
                         "period_a": per(a["period_start"], a["period_end"]), "n_a": a["n_tropicalis"],
                         "institution_a": a["inst"], "collection_a": a["collection_id"],
                         "report_b": b["study_id"], "label_b": b["study_label"],
                         "period_b": per(b["period_start"], b["period_end"]), "n_b": b["n_tropicalis"],
                         "institution_b": b["inst"], "collection_b": b["collection_id"],
                         "country_a": a["country_iso3"], "country_b": b["country_iso3"], "programme": p["programme"],
                         "jaccard_institution": jac, "identical_counts": len(ident), "identical_example": ex,
                         "proposal": prop, "reason": why})
    out = pd.DataFrame(rows)
    order = {"YES": 0, "PARTIAL": 1, "REVIEW": 2}
    out = out.sort_values(["proposal", "country_a", "label_a"], key=lambda c: c.map(order) if c.name == "proposal" else c)
    out = out.reset_index(drop=True)
    out["pair_id"] = [f"P{i+1:03d}" for i in range(len(out))]
    return blank_cols(out, ["decision", "reviewer", "date", "comment"])


def book_ar20(m, t):
    a = m["ast"]
    rep = t["rep"].set_index("report_id")
    st = m["studies"].set_index("study_id")
    a = a[(a.eligible_r_cbp_v3 == "YES") | (a.eligible_nwt_ecv_v3 == "YES")].copy()
    rn = a.study_id.map(rep["extraction_notes"]).fillna("")
    props = [V.d3_proposal(n, r) for n, r in zip(a.note_raw, rn)]
    a["proposal"] = [p[0] for p in props]
    a["evidence_phrase"] = [p[1] for p in props]
    a = a[a.proposal != ""].copy()
    a["study_label"] = a.study_id.map(st["study_label"])
    a["pdf_file"] = a.study_id.map(st["pdf_file"])
    a["report_note"] = a.study_id.map(rep["extraction_notes"])
    cols = ["row_id", "study_id", "study_label", "pdf_file", "compartment", "agent", "n_tested", "n_R", "n_NWT",
            "note_raw", "report_note", "proposal", "evidence_phrase"]
    out = a.sort_values(["proposal", "study_id", "agent"])[cols]
    return blank_cols(out, ["decision", "reason_ar20", "reviewer", "date", "comment"])


def book_species(m):
    st = m["studies"]
    s = st[st.species_id_issue != ""].copy()
    cols = ["study_id", "study_label", "year", "eligible_ma", "pdf_file", "species_id_raw", "species_id",
            "species_id_proposal", "species_id_issue"]
    out = s.sort_values(["eligible_ma", "study_id"], ascending=[False, True])[cols]
    return blank_cols(out, ["decision_species_id", "reviewer", "date", "comment"])


def book_allocation_c5(m):
    al = pd.read_excel(ALLOC, sheet_name="allocation")
    al["n_isolates"] = pd.to_numeric(al["n_isolates"], errors="coerce")
    al["comp"] = al["compartment_corrected"].fillna(al["compartment"])
    ver = al[al.verification_status.astype(str).str.lower().eq("verified")]
    iso = ver.groupby(["report_id", "comp"]).n_isolates.sum()
    a = m["ast"]
    rows = []
    for r in a[a.study_id.isin(set(ver.report_id))].itertuples(index=False):
        have = iso.get((r.study_id, r.compartment), 0)
        if r.n_tested > have:
            rows.append({"row_id": r.row_id, "study_id": r.study_id, "compartment": r.compartment, "agent": r.agent,
                         "n_tested": r.n_tested, "verified_isolates_in_compartment": have,
                         "verified_allocation": "; ".join(f"{c}: {int(n)}" for (rid, c), n in iso.items() if rid == r.study_id)})
    alloc = pd.DataFrame(rows)
    if len(alloc):
        alloc["proposal"] = np.where(alloc.verified_isolates_in_compartment == 0, "EXCLUDE_ROW_OR_REASSIGN", "CORRECT_N")
        alloc = blank_cols(alloc, ["decision", "compartment_v", "n_tested_v", "reviewer", "date", "comment"])
    cons = pd.concat([pd.read_excel(ROB_CONS, sheet_name=s) for s in ("Consensus_cal1_200", "Consensus_pass_904")])
    cons = cons[["report_id", "c5_definition", "agronomic_management", "agro_quote", "agro_page"]]
    c5_rep = set(m["studies"].loc[m["studies"].compartments.fillna("").str.contains("C5"), "study_id"])
    c5 = cons[cons.report_id.isin(c5_rep)].copy()
    agro_al = al[al["comp"] == "C5"].groupby("report_id").agronomic_management.first()
    c5["agronomic_allocation_2026_10_23"] = c5.report_id.map(agro_al)
    c5["study_label"] = c5.report_id.map(m["studies"].set_index("study_id")["study_label"])
    c5["conflict"] = (c5.agronomic_allocation_2026_10_23.notna() &
                      (c5.agronomic_allocation_2026_10_23 != c5.agronomic_management))
    c5["proposal_agronomic"] = np.where(c5.agro_quote.notna(), c5.agronomic_management, c5.agronomic_allocation_2026_10_23)
    c5 = c5.rename(columns={"agronomic_management": "agronomic_rob_consensus_2026_10_22"})
    c5 = blank_cols(c5, ["decision_agronomic", "reviewer", "date", "comment"])
    return alloc, c5


def book_sample(ft, m, pooled_reports):
    rng = np.random.default_rng(SEED)
    ex = ft[ft.ft_decision == "EXCLUDE"].copy()
    ex["stratum"] = "EXCLUDE " + ex.ft_reason.astype(str).str.extract(r"^(EC\d{1,2})", expand=False).fillna("other")
    inc = m["studies"][~m["studies"].study_id.isin(pooled_reports)][["study_id", "eligible_ma_v3"]].copy()
    inc["stratum"] = "INCLUDED not pooled, eligible MA " + inc.eligible_ma_v3
    inc = inc.merge(ft, left_on="study_id", right_on="ID", how="left")
    pool = pd.concat([ex.assign(study_id=ex.ID), inc], ignore_index=True)
    pick = []
    for s, g in pool.groupby("stratum", sort=True):
        k = math.ceil(SAMPLE_FRACTION * len(g))
        idx = rng.choice(len(g), size=k, replace=False)
        pick.append(g.iloc[sorted(idx)].assign(n_stratum=len(g), k_stratum=k))
    smp = pd.concat(pick, ignore_index=True)
    smp = smp.sample(frac=1, random_state=SEED).reset_index(drop=True)   # the order does not reveal the stratum
    smp["sample_id"] = [f"S{i+1:04d}" for i in range(len(smp))]
    key = smp[["sample_id", "study_id", "stratum", "n_stratum", "k_stratum", "ft_decision", "ft_reason"]]
    cols = ["sample_id", "study_id", "title", "year", "journal", "DOI", "pdf_file"]
    book = blank_cols(smp[cols].copy(), ["reader", "decision", "ec_code", "compartments", "n_tropicalis",
                                         "has_ast", "date", "comment"])
    return book, key


def book_500(t, ft):
    ex = pd.read_excel(C.XLSX, sheet_name="Studies")
    mm = ft[["ID", "ft_decision", "pdf_file"]].merge(ex, on="ID", how="left")
    e = mm[(mm.ft_decision != "EXCLUDE") & (mm.decision_final == "EXCLUDE")].copy()
    props = [V.exclusion500_proposal(mo, n, c, p, sp) for mo, n, c, p, sp in
             zip(e.change_reason, e.n_tropicalis_total, e.compartments, e.country, e.identification_method)]
    e["proposal"] = [p[0] for p in props]
    e["reason"] = [p[1] for p in props]
    cols = ["ID", "Study", "Publication year", "pdf_file", "change_reason", "comments", "n_tropicalis_total",
            "compartments", "country", "period_start", "period_end", "design", "identification_method",
            "proposal", "reason"]
    out = e[cols].rename(columns={"ID": "study_id", "Study": "study_label", "Publication year": "year"})
    out = out.sort_values(["proposal", "study_id"])
    return blank_cols(out, ["decision", "reviewer", "date", "comment"])


def mechanical_listing(m, ma):
    a = m["ast"]
    old = ma[ma.outcome == "R"][["row_id", "regime", "regime_flag"]].drop_duplicates("row_id")
    x = a.merge(old, on="row_id", how="left")
    x["change"] = ""
    x.loc[x.regime.notna() & (x.regime_v3.fillna("excluded") != x.regime), "change"] = "different regime"
    x.loc[(x.eligible_r_cbp == "NO") & (x.eligible_r_cbp_v3 == "YES"), "change"] += "; now eligible (without the no_version filter)"
    x.loc[x.rule4_excluded == "YES", "change"] += "; Rule 4: version not declared and without MIC"
    x["change"] = x.change.str.strip("; ")
    x = x[x.change != ""]
    cols = ["row_id", "study_id", "compartment", "agent", "interp_raw", "regime", "regime_v3", "regime_basis",
            "regime_flag_v3", "has_mic", "rule4_excluded", "change"]
    return blank_cols(x[cols].sort_values(["change", "study_id"]), ["comment"])


INSTR = {
    "b02": ["Workbook B02. Verification of the figures against the PDF, row by row.",
            "Priority: 1 report in a pooled stratum with some flag or low confidence; 2 medium confidence; 3 high; 4 report eligible for meta-analysis that is not in a pooled stratum today. The minimum verification (D2) covers priorities 1 to 3.",
            "Sheet reports: one line per report. report_eligible: YES if the report meets the application rule of the protocol (IC1, IC2, IC5, IC6, IC7 and IC3 or IC4); NO and the code in ec_if_not otherwise.",
            "Sheet rows: row_action OK if the figures match the PDF; CORRECT if any does not, writing ONLY the correct figures in the *_v columns; EXCLUDE_ROW if the row should not exist (another species, another compartment without separable data, data of another work).",
            "compartment_v: only if the compartment of the row is wrong. criterion_v: the criterion as the report declares it, if the extraction misread it.",
            "page_or_table: page and table where the figure is. Without that trace a change is not recorded (principle 3 of the group standard).",
            "The column flags explains why a row is prioritised: AR20 proposal, figure reconstructed from a percentage, categories computed by the extractor, n_tested greater than n_tropicalis, doubtful report proposed for the meta-analysis.",
            "used_2026_10_23: YES if the row entered some stratum of the run of 2026-10-23. NO rows are also reviewed (they may enter with the rules of 2026-10-24), but they are usually those without a breakpoint for the agent.",
            "Doubtful reports (doubtful YES): their rows only count if in the doubtful-reports workbook (07_phase5_full_text_screening/doubtful_review_2026-10-20/) the final decision is ENTERS_REVIEW_AND_MA. reader_text_doubtful carries what the doubtful review read, for comparison.",
            "No figure is changed outside the *_v columns. Empty decision cells block the construction of dataset v3."],
    "b03": ["Workbook B03. Pairs of reports that could be the same collection of isolates (EC12, AR1).",
            "decision: YES if the two reports describe, totally or partially, the same isolates (same programme or institution, overlapping periods); PARTIAL if one collection contains the other; NO if they are different collections.",
            "YES and PARTIAL merge the two collections and AR2 chooses in each stratum the report with most isolates tested. NO keeps them separate.",
            "proposal and reason are the automatic proposal: same figures in a stratum, same n of isolates, same institution or programme with nested periods. Different institutions with similar names carry the proposal NO."],
    "b04": ["Workbook B04. Rows that may not measure prevalence (rule AR20, decision D3).",
            "decision EXCLUDE_AR20 if the row is: a sample selected by phenotype (isolates included for being resistant, non-susceptible or for a mutation); an inferred denominator (the report does not give the number tested per agent nor says that all the isolates were tested); or a dataset compiled from public databases or from the literature. State the reason in reason_ar20.",
            "decision KEEP if the note was misread (for example, isolates selected at random, or the text says that all were tested).",
            "The rows excluded by AR20 leave the main analysis and return in the sensitivity analysis SX3."],
    "b05": ["Workbook B05. Species identification method of the reports classified 'molecular' whose text denies molecular confirmation or limits it to other species, to doubtful cases or to part of the isolates.",
            "decision_species_id: the category of the method with which C. tropicalis was identified in that report: molecular, MALDI_TOF, automated, biochemical, chromogenic, conventional or not_specified.",
            "It affects RB4 (risk of bias) and SA8."],
    "b06": ["Workbook B06. Reports of the 'R' flow of full-text screening with more than one candidate record in the screening corpus.",
            "decision_screen_id: the SCREEN_ID that corresponds to the PDF (check title, authors, year and journal)."],
    "b07": ["Workbook B07. Allocation by compartment and agronomic management of C5.",
            "Sheet allocation: AST rows whose n_tested exceeds the isolates that the verified allocation workbook (2026-10-23) gives to that compartment. decision: REASSIGN (write compartment_v), CORRECT_N (write n_tested_v) or EXCLUDE_ROW.",
            "Sheet c5: reports with rows in C5. The risk-of-bias consensus (2026-10-22) and the allocation workbook (2026-10-23) disagree. decision_agronomic: documented_absent, documented_present or not_evaluated, with the quote of the report in comment. The strict reading of C5, which is the main analysis, admits only documented_absent."],
    "b08": ["Workbook B08. Stratified random sample (seed 20261024) of 20 % of the full-text exclusions and 20 % of the included reports that do not contribute to pooled strata.",
            "It is read BLIND: the workbook does not show the earlier decision. Do not open r2_b08_key.csv, which is for the analysis.",
            "decision: INCLUDE or EXCLUDE, applying the rule of the protocol: a study enters the review if it meets IC1, IC2, IC5, IC6 and IC7 and at least IC3 or IC4. A study without susceptibility testing with C. tropicalis isolates assignable to a compartment ENTERS (it contributes to SQ1).",
            "ec_code: the exclusion criterion. If INCLUDE: compartments, n_tropicalis and has_ast (YES or NO).",
            "With this, the proportion of reversed decisions is reported with its exact CI, and the kappa between the earlier decision and that of this reading. Discrepancies go to the third reviewer."],
    "b09": ["Workbook B09. The 500 reports that the extraction excluded after screening ('No extractable data').",
            "Most were excluded because they carry no susceptibility testing. By the application rule of the protocol (IC3 or IC4) and by the rules of 2026-10-20 for the doubtful reports, a study with C. tropicalis isolates assignable to a compartment enters the review and contributes to SQ1 even if it has no AST.",
            "decision: INCLUDE_SQ1 (enters the review, without susceptibility data), INCLUDE_MA (has susceptibility data that the extraction did not take: they are extracted separately), NOT_RETRIEVED (the available text does not correspond or is illegible) or EXCLUDE_ECx with its code.",
            "For INCLUDE_SQ1, n_tropicalis_total, compartments, country and identification method are checked in the PDF; if any is wrong, it is corrected in comment."],
    "b11": ["Workbook B11. Susceptibility rows of the doubtful reports that the review of 2026-10-20 proposed for the meta-analysis (ENTERS_REVIEW_AND_MA) and that have no rows in the extraction tables.",
            "Each row comes from what that review read (column reader_text, with table and page). It only counts if in the doubtful-reports workbook the final decision is ENTERS_REVIEW_AND_MA.",
            "row_action: CONFIRM if n_tested, n_events, the criterion and the compartment match the PDF; CORRECT writing only what changes in the *_v columns; DISCARD if the row should not enter (another species, aggregated data, a category that is not resistance).",
            "outcome R: resistance by clinical breakpoint, n_events is the number of resistant isolates. outcome NWT: non-wild type by ECV. If the report counts the non-susceptible as resistant, it is noted in comment.",
            "method_v: the susceptibility method, from the list, if the proposed one is wrong. page_or_table: mandatory."],
    "b10": ["Workbook B10. Mechanical changes of the layer of 2026-10-24, without human decision: regime from the declared breakpoints or the written year (Rule 1), M44 without version, eligibility without the no_version filter (AR6) and Rule 4 (version not declared and without MIC).",
            "For review only: if a change is wrong, note it in comment and the rule is corrected, not the row."],
}


def main():
    check = "--check" in sys.argv[1:]
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    t = C.load_tidy()
    tb = C.apply_ec2(C.rebuild_v1(t))
    bad = C.check_against_v2(tb)
    if bad:
        sys.exit("The reconstruction does not reproduce analysis_dataset_v2: " + " | ".join(bad))
    m = C.mechanical(tb, t["rep"])
    ft = load_ft()
    dubwb = pd.read_excel(DUB, sheet_name="Review")
    dub_ma = dubwb[dubwb.proposed_verdict == "ENTERS_REVIEW_AND_MA"]
    xd = C.extra_reports(t, set(dub_ma.ID))
    xdm = C.mechanical(xd, t["rep"])
    dub_text = dict(zip(dub_ma.ID, dub_ma.meta_analysis_data))
    ma = pd.read_csv(MA_INPUT)
    res = pd.read_csv(MA_RESULTS)
    pooled = res.loc[res.status == "pooled", KEY]
    mp = ma[ma["main"].astype(str) == "True"].merge(pooled, on=KEY)
    pooled_reports = set(mp.study_id)

    # flags per row for B02
    rep = t["rep"].set_index("report_id")
    flags = {}
    for r in pd.concat([m["ast"], xdm["ast"]], ignore_index=True).itertuples(index=False):
        f = []
        p, _ = V.d3_proposal(r.note_raw, rep["extraction_notes"].get(r.study_id, ""))
        if p:
            f.append(f"AR20 proposal: {p}")
        nt = V.norm_text(r.note_raw)
        if re.search(r"calculated( of| from| as)? %|reconstructed|from (a )?percentage|of percentage", nt):
            f.append("reconstructed from a percentage")
        if re.search(r"calculated by the extractor|deduced from the range|deducted from the range|applied by the extractor|(deduced|deducted|calculated) categories|categories (deduced|deducted|calculated)", nt):
            f.append("categories calculated by the extractor")
        if r.rule4_excluded == "YES":
            f.append("Rule 4")
        if f:
            flags[r.row_id] = "; ".join(f)

    rows, reps = book_rows(m, t, ft, pooled_reports, flags, set(ma.row_id), xdm, dub_text)
    new = book_new_rows(dub_ma[~dub_ma.ID.isin(set(rows.study_id))])
    pairs = book_pairs(m, t, ma)
    ar20 = book_ar20(m, t)
    species = book_species(m)
    alloc, c5 = book_allocation_c5(m)
    smp, key = book_sample(ft, m, pooled_reports)
    e500 = book_500(t, ft)
    mech = mechanical_listing(m, ma)
    rmap, _ = r_stream_map(ft)
    amb = rmap[rmap.k_candidates != 1].copy()
    amb = blank_cols(amb, ["decision_screen_id", "reviewer", "date", "comment"])

    summary = {
        "B02 rows": len(rows), "B02 reports": len(reps),
        "B02 reports by priority": reps.priority.value_counts().sort_index().to_dict(),
        "B03 pares": len(pairs), "B03 proposals": pairs.proposal.value_counts().to_dict(),
        "B04 AR20 rows": len(ar20), "B04 proposals": ar20.proposal.value_counts().to_dict(),
        "B05 reports": len(species), "B07 allocation rows": len(alloc), "B07 C5 reports": len(c5),
        "B07 C5 in conflict": int(c5.conflict.sum()) if len(c5) else 0,
        "B08 sample": len(smp), "B08 by stratum": key.groupby("stratum").size().to_dict(),
        "B09 reports": len(e500), "B09 proposals": e500.proposal.value_counts().to_dict(),
        "B10 mechanical changes": len(mech),
        "B02 doubtful reports proposed for MA with tidy rows": int((reps.doubtful == "YES").sum()),
        "B11 new rows": len(new), "B11 reports": int(new.report_id.nunique()) if len(new) else 0,
        "B11 not read": int((new.parse != "ok").sum()) if len(new) else 0,
        "R flow": rmap.match_method.value_counts().to_dict(),
        "R flow ambiguous": int((rmap.k_candidates > 1).sum()), "R flow unpaired": int((rmap.k_candidates == 0).sum()),
    }
    for k, v in summary.items():
        print(f"{k}: {v}")
    if check:
        print("\n--check: nothing was written.")
        return

    p = lambda n: os.path.join(OUT, n)  # noqa: E731
    names = ["r2_b02_rows.xlsx", "r2_b03_collection_pairs.xlsx", "r2_b04_ar20_rows.xlsx", "r2_b05_species_id.xlsx",
             "r2_b06_r_stream_ambiguous.xlsx", "r2_b07_allocation_c5.xlsx", "r2_b08_sample_blind.xlsx",
             "r2_b09_extraction_exclusions.xlsx", "r2_b10_mechanical_changes.xlsx", "r2_b11_new_ast_rows.xlsx",
             "r2_b08_key.csv"]
    exist = [f for f in [p(n) for n in names] + [R_MAP] if os.path.exists(f)]
    if exist:
        sys.exit("They already exist, nothing is overwritten: " + ", ".join(exist))
    os.makedirs(OUT, exist_ok=True)
    outs = [
        write_book(p("r2_b02_rows.xlsx"), "Round 2, workbook B02: figures by row", INSTR["b02"],
                   [("reports", reps, {"report_eligible": ["YES", "NO"], "ec_if_not": EC_LIST}, {"flags": 50}),
                    ("rows", rows, {"row_action": ["OK", "CORRECT", "EXCLUDE_ROW"],
                                     "compartment_v": C.COMP}, {"interp_raw": 40, "note_raw": 50, "ft_evidence": 50, "flags": 40})]),
        write_book(p("r2_b03_collection_pairs.xlsx"), "Round 2, workbook B03: pairs of collections", INSTR["b03"],
                   [("pairs", pairs, {"decision": ["YES", "PARTIAL", "NO"]}, {})]),
        write_book(p("r2_b04_ar20_rows.xlsx"), "Round 2, workbook B04: rows that do not measure prevalence", INSTR["b04"],
                   [("rows", ar20, {"decision": ["EXCLUDE_AR20", "KEEP"],
                                     "reason_ar20": ["phenotype_selected", "inferred_denominator", "compiled_dataset"]},
                     {"note_raw": 60, "report_note": 50})]),
        write_book(p("r2_b05_species_id.xlsx"), "Round 2, workbook B05: species identification", INSTR["b05"],
                   [("reports", species, {"decision_species_id": ["molecular", "MALDI_TOF", "automated", "biochemical",
                                                                   "chromogenic", "conventional", "not_specified"]},
                     {"species_id_raw": 70})]),
        write_book(p("r2_b06_r_stream_ambiguous.xlsx"), "Round 2, workbook B06: ambiguous R flow", INSTR["b06"],
                   [("reports", amb, {}, {"title": 60})]),
        write_book(p("r2_b07_allocation_c5.xlsx"), "Round 2, workbook B07: allocation and C5", INSTR["b07"],
                   [("allocation", alloc if len(alloc) else pd.DataFrame({"no_rows": []}),
                     {"decision": ["REASSIGN", "CORRECT_N", "EXCLUDE_ROW"], "compartment_v": C.COMP}, {}),
                    ("c5", c5, {"decision_agronomic": ["documented_absent", "documented_present", "not_evaluated"]},
                     {"agro_quote": 50})]),
        write_book(p("r2_b08_sample_blind.xlsx"), "Round 2, workbook B08: blind sample", INSTR["b08"],
                   [("sample", smp, {"decision": ["INCLUDE", "EXCLUDE"], "ec_code": EC_LIST, "has_ast": ["YES", "NO"]},
                     {"title": 60})]),
        write_book(p("r2_b09_extraction_exclusions.xlsx"), "Round 2, workbook B09: excluded at extraction", INSTR["b09"],
                   [("reports", e500, {"decision": ["INCLUDE_SQ1", "INCLUDE_MA", "NOT_RETRIEVED"] + [f"EXCLUDE_{e}" for e in EC_LIST]},
                     {"change_reason": 60, "comments": 50})]),
        write_book(p("r2_b10_mechanical_changes.xlsx"), "Round 2, workbook B10: mechanical changes (review only)", INSTR["b10"],
                   [("changes", mech, {}, {"interp_raw": 50})]),
        write_book(p("r2_b11_new_ast_rows.xlsx"), "Round 2, workbook B11: new rows of doubtful reports", INSTR["b11"],
                   [("rows", new, {"row_action": ["CONFIRM", "CORRECT", "DISCARD"], "compartment_v": C.COMP,
                                    "method_v": METHODS}, {"reader_text": 60, "criterion_raw": 40, "location": 40})]),
    ]
    f_key = p("r2_b08_key.csv")
    key.to_csv(f_key, index=False)
    rmap[rmap.k_candidates == 1].assign(screen_id=lambda d: d.screen_id_candidates).to_csv(R_MAP, index=False)
    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    log = {"script": os.path.basename(__file__), "run_time": datetime.now().astimezone().isoformat(timespec="seconds"),
           "decisions": "10_phase8_analysis/team_decisions_2026-10-24.md",
           "inputs": {f: C.md5(f) for f in (FT, RIS, RAYYAN, MA_INPUT, MA_RESULTS, ALLOC, ROB_CONS, C.XLSX, C.EC2_DEC, DUB,
                                             "10_phase8_analysis/team_decisions_2026-10-24.md")},
           "outputs": {os.path.basename(f): C.md5(f) for f in outs + [f_key, R_MAP]},
           "seed": SEED, "sample_fraction": SAMPLE_FRACTION, "summary": summary}
    C.write_json(p(f"make_verification_books_v1_{stamp}.json"), log)
    print("\nWorkbooks in", OUT)


if __name__ == "__main__":
    main()
