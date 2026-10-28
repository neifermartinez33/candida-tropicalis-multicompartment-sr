#!/usr/bin/env python3
"""make_label_book_v1.py (2026-10-24)

Workbook B13 of round 2: report labels ("Author Year") malformed in the extraction and missing publication
years. The label is cosmetic (Tables S6 and S8, Table 2), but it appears in the article. It proposes
the label from the first author and the year of the screening record (RIS); the reviewer confirms or corrects
against the PDF. The year is listed for information: dataset v3 does not apply it, because the regime of some
rows depends on the year and is computed earlier (see team_decisions_2026-10-24.md, pending P3).

Usage, from the project root, after a run of build_analysis_dataset_v3.py (any mode):
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/make_label_book_v1.py
Output (not overwritten): 08_phase6_data_extraction/verification/round2_2026-10-24/r2_b13_labels.xlsx
"""
import glob
import os
import re
import sys
import unicodedata

import pandas as pd

R2 = "08_phase6_data_extraction/verification/round2_2026-10-24"
OUT = f"{R2}/r2_b13_labels.xlsx"
RIS = "06_phase4_title_abstract_screening/import/screening_reviewer_1_reviewer_2_n22203_seed1310202643.ris"
R_MAP = "07_phase5_full_text_screening/r_stream_screen_id_map_2026-10-24.csv"
def plain_au(au):
    return re.sub(r",\s*null$", "", (au or "").strip())


def latin(ch):
    return unicodedata.category(ch).startswith("L") and unicodedata.name(ch, "").startswith("LATIN")


def reason(label, au0):
    """Reason why the label is not usable for the article, or '' if it is."""
    s = str(label)
    if s in ("", "nan") or not re.search(r"\d{4}[a-z]?$", s):
        return "no_year"
    name = re.sub(r"\s+\d{4}[a-z]?$", "", s).strip()
    if any(unicodedata.category(c).startswith("L") and not latin(c) for c in name):
        return "non_latin_script"
    if not latin(name[0]) or re.fullmatch(r"([A-Z]\.?\s*)+", name):
        return "not_a_name"
    if re.search(r"^ER\s|\s-\s|…|\.\.\.|[A-Za-zÀ-ÿ]\d|\*|Dr\.", name):
        return "record_residue"
    if re.search(r"Department|Universi|Hospital|Cent(er|re)\b|Institut", name):
        return "institution"
    if re.match(r"^([A-Z]{1,2}\.?\s+)+[A-ZÀ-Ý]", name):
        return "leading_initials"
    if re.search(r"(\s[A-Z]{1,3})+$|\sJr\.?$", name):
        return "trailing_initials"
    if len(re.findall(r"[a-zß-ÿ]", name)) == 0 and len(name) > 3:
        return "all_caps"
    if re.search(r"\s{2,}", name):
        return "given_names"
    a = plain_au(au0)
    if a and "," not in a and len(a.split()) >= 3 and name == re.sub(r"\s+", " ", a):
        return "given_names"
    return ""


def tcase(x):
    return re.sub(r"[^\s-]+", lambda m: m.group(0)[:1] + m.group(0)[1:].lower(), " ".join(x.split()))


def proposal(label, why, year):
    """Only the unambiguous mechanical fixes; the rest is decided by the reviewer."""
    if year is None or why in ("no_year", "non_latin_script", "not_a_name", "record_residue", "institution", "given_names"):
        return ""
    name = re.sub(r"\s+\d{4}[a-z]?$", "", str(label)).strip()
    if why == "leading_initials":
        name = re.sub(r"^([A-Z]{1,2}\.?\s+)+", "", name)
    if why == "trailing_initials":
        name = re.sub(r"(\s[A-Z]{1,3})+$|\sJr\.?$", "", name).strip()
    if not re.search(r"[a-zß-ÿ]", name):
        name = tcase(name)
    if len(re.sub(r"[^A-Za-zÀ-ÿ]", "", name)) < 2 or re.fullmatch(r"([A-Z]\.?\s*)+", name):
        return ""
    suf = re.search(r"\d{4}([a-z]?)$", str(label))
    return f"{name} {int(float(year))}{suf.group(1) if suf else ''}"


def main():
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    if os.path.exists(OUT):
        sys.exit(f"Already exists {OUT}: not overwritten")
    ds = sorted(glob.glob("10_phase8_analysis/data/analysis_dataset_v3_*"))
    if not ds:
        sys.exit("A v3 dataset is missing: run build_analysis_dataset_v3.py first")
    st = pd.read_csv(f"{ds[-1]}/studies.csv", low_memory=False)
    rmap = pd.read_csv(R_MAP)
    r2s = dict(zip(rmap.R_id, rmap.screen_id))
    st["screen_id"] = [i if i.startswith("O") else r2s.get(i, "") for i in st.study_id]
    want, recs, cur, sid = set(st.screen_id), {}, {"AU": [], "Y1": ""}, None
    with open(RIS, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            if ln.startswith("ER  -"):
                if sid in want:
                    recs[sid] = cur
                cur, sid = {"AU": [], "Y1": ""}, None
            elif ln.startswith("AU  - "):
                cur["AU"].append(ln[6:].strip())
            elif ln.startswith("Y1  - ") and not cur["Y1"]:
                cur["Y1"] = ln[6:].strip()[:4]
            elif ln.startswith("N1  - SCREEN_ID "):
                sid = ln[16:].strip()
    au0 = {r["study_id"]: (recs.get(r["screen_id"], {"AU": []})["AU"] or [""])[0] for r in st.to_dict("records")}
    st["why"] = [reason(lab, au0[i]) for lab, i in zip(st.study_label, st.study_id)]
    sel = st[(st.why != "") | st.year.isna()].copy()
    rows = []
    for r in sel.sort_values("study_id").to_dict("records"):
        rec = recs.get(r["screen_id"], {"AU": [], "Y1": ""})
        y = r["year"] if pd.notna(r["year"]) else (rec["Y1"] or None)
        prop = proposal(r["study_label"], r["why"] or "no_year", y)
        rows.append({"study_id": r["study_id"], "study_label_extracted": r["study_label"], "year_extracted": r["year"],
                     "reason": r["why"] or "no_year", "record_first_authors": "; ".join(rec["AU"][:3]), "record_year": rec["Y1"], "title": r["title"],
                     "study_label_proposal": prop, "decision_study_label": None, "year_from_pdf": None,
                     "page_or_source": None, "reviewer": None, "date": None, "comment": None})
    df = pd.DataFrame(rows)
    instr = pd.DataFrame({"instruction": [
        "One row per report with a malformed label or without publication year.",
        "decision_study_label: 'Surname Year' of the first author, as it will be cited (without initials; compound surname if cited that way). "
        "Empty = in provisional mode the proposal is used, or the extracted label if there is no proposal; in the FINAL run "
        "the decision is mandatory (if the extracted label is correct, copy it).",
        "Rows can be added with other reports whose label is wrong (only study_id and decision_study_label).",
        "Mechanical reasons (trailing_initials, all_caps, leading_initials): if the proposals are correct, it is enough to copy the "
        "column study_label_proposal into decision_study_label after reviewing them. The other reasons (given_names, "
        "non_latin_script, no_year, record_residue, not_a_name, institution) are resolved with the PDF or the record.",
        "year_from_pdf: the publication year if missing; it is recorded but dataset v3 does not apply it (pending P3).",
        "The letter that distinguishes two reports of the same author and year (a, b, ...) is added by the build script."]})
    with pd.ExcelWriter(OUT, engine="xlsxwriter") as xw:
        instr.to_excel(xw, sheet_name="instructions", index=False)
        df.to_excel(xw, sheet_name="reports", index=False)
        ws = xw.sheets["reports"]
        for j, w in enumerate([10, 30, 8, 16, 40, 8, 50, 22, 22, 10, 16, 10, 10, 20]):
            ws.set_column(j, j, w)
    print(f"{OUT}: {len(df)} reports; reasons {df.reason.value_counts().to_dict()}; with a mechanical proposal: "
          f"{int((df.study_label_proposal != '').sum())}")


if __name__ == "__main__":
    main()
