#!/usr/bin/env python3
"""Write the three Excel workbooks of 2026-10-20 from the v0 build and the
review of the doubtful articles.

  pdf_integrity_issues_2026-10-20.xlsx      files to re-retrieve or merge
  full_text_doubtful_review_2026-10-20.xlsx proposals for the two reviewers
  tidy_tables_v0_2026-10-20.xlsx            the organized tables, dictionaries and data dictionary

Format: black text, bold header without fill, frozen header row.
"""
import argparse, glob, json, os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter

BOLD = Font(bold=True, color="000000")
NORMAL = Font(color="000000")
WRAP = Alignment(wrap_text=True, vertical="top")

def write_sheet(wb, name, df, widths=None, wrap_cols=()):
    ws = wb.create_sheet(title=name[:31])
    cols = list(df.columns)
    ws.append(cols)
    for c in ws[1]:
        c.font = BOLD
        c.alignment = Alignment(wrap_text=True, vertical="top")
    for row in df.itertuples(index=False):
        ws.append([None if (isinstance(v, float) and pd.isna(v)) else v for v in row])
    for j, col in enumerate(cols, start=1):
        w = (widths or {}).get(col)
        if w is None:
            s = df[col].astype(str).str.len()
            w = int(min(60, max(10, (s.quantile(0.9) if len(s) else 10), len(str(col)) + 2)))
        ws.column_dimensions[get_column_letter(j)].width = w
        if col in wrap_cols:
            for cell in ws.iter_cols(min_col=j, max_col=j, min_row=2):
                for c in cell:
                    c.alignment = WRAP
    ws.freeze_panes = "A2"
    return ws

def write_text_sheet(wb, name, lines, width=120):
    ws = wb.create_sheet(title=name[:31])
    for i, l in enumerate(lines, start=1):
        c = ws.cell(row=i, column=1, value=l)
        c.font = BOLD if i == 1 else NORMAL
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = width
    return ws

def integrity(out_dir, tidy_dir, screening=None, groups=None):
    rep = pd.read_csv(os.path.join(tidy_dir, "reports.csv"), low_memory=False)
    keep = ["report_id", "corpus_n", "title", "year", "doi", "pdf_file", "extraction_decision", "extraction_ma",
            "n_rows_ast", "pdf_identical_group", "pdf_identical_with", "pdf_identical_title_similarity"]
    wb = Workbook(); wb.remove(wb.active)
    write_text_sheet(wb, "Instructions", [
        "Integrity problems of the PDFs of full-text screening (2026-10-20)",
        "An eligibility decision or an extracted figure is only valid if it was taken on the correct and complete full text.",
        "Sheet 'Identical PDFs': files identical byte for byte (MD5) assigned to more than one record. If the titles are the same work, one record is kept and the other is marked as duplicate (it is not counted twice in the extraction). If the titles are different works, the PDF corresponds at most to one of them: which one is verified and the text of the others is retrieved.",
        "Sheet 'Truncated PDFs': incomplete downloads (exact size of 64 or 256 KiB). They are downloaded again.",
        "Sheet 'Wrong PDF (notes)': the extraction itself recorded that the text corresponds to another document.",
        "Sheet 'Tables not captured (notes)': the extraction says that a table or part of the text could not be read in the conversion. The datum may be in the PDF.",
        "A text that cannot be retrieved is counted as 'not retrieved' in PRISMA (protocol, section 7), not as excluded by a criterion.",
        "Columns to fill in: action, owner, date, result.",
    ])
    def add_action(df, default):
        df = df.copy()
        df["proposed_action"] = default
        for c in ["action", "owner", "date", "result"]:
            df[c] = None
        return df
    if screening and groups:
        scr = pd.read_excel(screening, sheet_name="All")
        g = pd.read_csv(groups)
        allr = scr.merge(g[["ID", "grp"]], on="ID", how="inner")
        allr = allr.merge(rep[["report_id", "extraction_decision", "extraction_ma", "n_rows_ast"]], left_on="ID", right_on="report_id", how="left")
        import re as _re
        def _tok(t):
            t = _re.sub(r"[^\w\s]", " ", str(t or "").lower()); return set(w for w in t.split() if len(w) > 2)
        sims = []
        for _, r in allr.iterrows():
            others = allr[(allr.grp == r.grp) & (allr.ID != r.ID)]
            a = _tok(r["Title"])
            sims.append(round(max((len(a & _tok(o)) / len(a | _tok(o)) if (a and _tok(o)) else 0.0) for o in others["Title"]), 2))
        allr["pdf_identical_title_similarity"] = sims
        allr["pdf_identical_with"] = allr.apply(lambda r: "; ".join(allr[(allr.grp == r.grp) & (allr.ID != r.ID)].ID), axis=1)
        ident = pd.DataFrame({"pdf_identical_group": allr.grp, "report_id": allr.ID, "corpus_n": allr["No."], "title": allr["Title"],
                              "year": allr["Year"], "doi": allr["DOI"], "pdf_file": allr["PDF file"],
                              "ft_screening_decision": allr["Decision"], "extraction_decision": allr.extraction_decision,
                              "extraction_ma": allr.extraction_ma, "n_rows_ast": allr.n_rows_ast,
                              "pdf_identical_with": allr.pdf_identical_with,
                              "pdf_identical_title_similarity": allr.pdf_identical_title_similarity}).sort_values(["pdf_identical_group", "corpus_n"])
    else:
        ident = rep[rep.pdf_identical_group.notna()].sort_values(["pdf_identical_group", "corpus_n"])[keep]
    ident = ident.copy()
    ident["proposed_action"] = ident.pdf_identical_title_similarity.map(
        lambda s: "same work: keep one record and mark the other as duplicate" if (s or 0) >= 0.5
        else "verify which record the PDF corresponds to and retrieve the text of the others")
    for c in ["action", "owner", "date", "result"]:
        ident[c] = None
    write_sheet(wb, "Identical PDFs", ident, wrap_cols=("title", "pdf_identical_with"))
    write_sheet(wb, "Truncated PDFs", add_action(rep[rep.pdf_status == "truncated"][keep[:8]], "download again"), wrap_cols=("title",))
    wr = rep[rep.pdf_status == "wrong_document_per_notes"][keep[:8] + ["extraction_notes"]]
    write_sheet(wb, "Wrong PDF (notes)", add_action(wr, "retrieve the correct PDF"), wrap_cols=("title", "extraction_notes"))
    tm = rep[rep.pdf_status.isin(["tables_or_text_not_captured_per_notes", "partial_text_per_notes"])][keep[:8] + ["pdf_status", "extraction_notes"]]
    write_sheet(wb, "Tables not captured (notes)", add_action(tm, "read the table in the PDF and complete the extraction"), wrap_cols=("title", "extraction_notes"))
    p = os.path.join(out_dir, "pdf_integrity_issues_2026-10-20.xlsx")
    wb.save(p); return p

def doubtful(out_dir, review_dir, batches_dir):
    rows = []
    for f in sorted(glob.glob(os.path.join(review_dir, "*.jsonl"))):
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    ctx = {}
    for f in sorted(glob.glob(os.path.join(batches_dir, "*.json"))):
        for r in json.load(open(f, encoding="utf-8")):
            ctx[r["ID"]] = r
    out = []
    seen = set()
    for r in rows:
        if r["ID"] in seen:
            continue
        seen.add(r["ID"])
        c = ctx.get(r["ID"], {})
        ex = c.get("extraction", {})
        crit = r.get("criteria") or {}
        ma = r.get("ma_data") or []
        ma_txt = "; ".join(f"{d.get('antifungico')}: {d.get('n_R')}/{d.get('n_tested')} R ({d.get('category')}; {d.get('location')})" for d in ma)
        out.append({
            "N": c.get("N"), "ID": r["ID"], "title": c.get("title"), "year": c.get("year"), "pdf": os.path.basename(c.get("pdf") or ""),
            "original_doubt": " | ".join(x for x in [ex.get("change_reason"), ex.get("comments")] if x),
            "proposed_verdict": r.get("verdict"), "exclusion_code": r.get("exclusion_code"),
            "pdf_matches": r.get("pdf_matches"), "pdf_is_of": r.get("pdf_is_of"),
            **{k: crit.get(k) for k in ["IC1", "IC2", "IC3", "IC4", "IC5", "IC6", "IC7", "IC8"]},
            "compartment": r.get("compartment"), "source": r.get("source"), "country": r.get("country"), "period": r.get("period"),
            "n_tropicalis": r.get("n_tropicalis"), "identification_method": r.get("identification_method"),
            "susceptibility_method": r.get("susceptibility_method"), "interpretive_criterion": r.get("interpretive_criterion"),
            "meta_analysis_data": ma_txt or None, "molecular_or_genotype": r.get("molecular_or_genotype"),
            "resolves_the_doubt": r.get("resolves_the_doubt"), "evidence": " || ".join(r.get("evidence") or []),
            "confidence": r.get("confidence"), "note": r.get("note"),
            "decision_reviewer_1": None, "decision_reviewer_2": None, "decision_final": None, "reviewers_comment": None,
        })
    df = pd.DataFrame(out).sort_values("N")
    order = {"ENTERS_REVIEW_AND_MA": 0, "ENTERS_REVIEW": 1, "NOT_RETRIEVED": 2, "NOT_DETERMINABLE": 3, "REMAINS_EXCLUDED": 4}
    df["_o"] = df.proposed_verdict.map(order).fillna(9)
    df = df.sort_values(["_o", "N"]).drop(columns="_o")
    wb = Workbook(); wb.remove(wb.active)
    summ = df.proposed_verdict.value_counts().rename_axis("proposed_verdict").reset_index(name="articles")
    write_text_sheet(wb, "Instructions", [
        "Review of the articles with final decision DOUBTFUL at extraction (2026-10-20)",
        f"Articles reviewed: {len(df)} of 316. Each row is a proposal with its evidence; the decision belongs to the reviewers.",
        "The PDF was read (extracted text, OCR and, where tables were missing, the image of the page) and the criteria IC1 to IC8 and EC1 to EC13 of the protocol were applied with the rules of the manual.",
        "ENTERS_REVIEW_AND_MA: meets the general rule and IC4 with denominators per antifungal, and IC8. The figures of 'meta_analysis_data' give table and page so that they can be verified.",
        "ENTERS_REVIEW: meets the general rule (IC1, IC2, IC5, IC6, IC7 and IC3 or IC4) but not the requirements of the meta-analysis.",
        "NOT_RETRIEVED: the PDF does not correspond to the record, is truncated or is partial. It is not an exclusion by criterion: it goes to the not-retrieved box of PRISMA if the correct text is not obtained.",
        "NOT_DETERMINABLE: correct PDF but illegible in the necessary part.",
        "REMAINS_EXCLUDED: fails a criterion; the EC code is given.",
        "Columns to fill in: decision_reviewer_1, decision_reviewer_2, decision_final, reviewers_comment.",
    ])
    write_sheet(wb, "Summary", summ)
    write_sheet(wb, "Review", df, wrap_cols=("title", "original_doubt", "resolves_the_doubt", "evidence", "meta_analysis_data", "note", "source", "molecular_or_genotype"),
                widths={"title": 45, "original_doubt": 50, "resolves_the_doubt": 50, "evidence": 60, "meta_analysis_data": 50, "note": 40})
    p = os.path.join(out_dir, "full_text_doubtful_review_2026-10-20.xlsx")
    wb.save(p)
    df.to_csv(os.path.join(out_dir, "full_text_doubtful_review_2026-10-20.csv"), index=False)
    return p, df

def tidy_workbook(out_dir, tidy_dir, data_dict_path):
    wb = Workbook(); wb.remove(wb.active)
    write_text_sheet(wb, "README", [
        "Ordered tables v0 of the C. tropicalis review (2026-10-20), generated by build_tidy_tables_v0.py",
        "Origin: full_text_screening.xlsx and data_extraction_tropicalis.xlsx (extraction, without human verification). No figure of these tables is verified: verification_status = pending.",
        "Structure: reports (one row per record), ast (one row per stratum x antifungal x method x criterion), mic_summary, molecular, genotypes, dynamics_raw (sheet Dynamics unchanged, with its row type), collection_candidates (EC12 candidates) and dictionaries.",
        "The 'raw' variables keep the text of the extraction. The normalised variables (agent_std, method_cat, interp_*, flc_regime, country_iso3, gene_std, aa_substitutions, scheme, clade4_reported) are proposals by rule and must be reviewed in the dictionaries.",
        "The analysis datasets are built later, only with verified rows and with an assigned collection; they are not built here.",
        "The sheet data_dictionary describes the target structure (v1) and indicates what remains to be extracted.",
    ])
    for name in ["reports", "ast", "mic_summary", "molecular", "genotypes", "dynamics_raw", "collection_candidates"]:
        df = pd.read_csv(os.path.join(tidy_dir, f"{name}.csv"), low_memory=False)
        write_sheet(wb, name, df)
    for f in sorted(glob.glob(os.path.join(tidy_dir, "dictionaries", "*.csv"))):
        df = pd.read_csv(f)
        write_sheet(wb, os.path.basename(f)[:-4], df)
    write_sheet(wb, "data_dictionary", pd.read_csv(data_dict_path), wrap_cols=("definition", "allowed_values_or_format", "source_in_current_matrices"),
                widths={"definition": 60, "allowed_values_or_format": 45, "source_in_current_matrices": 40})
    p = os.path.join(out_dir, "tidy_tables_v0_2026-10-20.xlsx")
    wb.save(p); return p

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tidy", required=True)
    ap.add_argument("--review", required=True)
    ap.add_argument("--batches", required=True)
    ap.add_argument("--data-dict", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="all")
    ap.add_argument("--screening", default=None)
    ap.add_argument("--groups", default=None)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.only in ("all", "integrity"):
        print(integrity(a.out, a.tidy, a.screening, a.groups))
    if a.only in ("all", "doubtful"):
        p, df = doubtful(a.out, a.review, a.batches); print(p, len(df))
    if a.only in ("all", "tidy"):
        print(tidy_workbook(a.out, a.tidy, a.data_dict))
