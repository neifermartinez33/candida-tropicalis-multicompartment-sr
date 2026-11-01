#!/usr/bin/env python3
"""58_tabS15_human_model_agreement_v5.py (2026-10-30)

Table S15 v5: the rows of v3 with two changes, read from the CSV of v3. The row of the model runs says which run was used
and what happened to the reports on which the runs differed (05_phase3_model_validation/reproducibility_2026-10-29), the row of RB8 separates the reports read by two reviewers from those coded by one reviewer with a verifier.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/58_tabS15_human_model_agreement_v5.py
Outputs (never overwritten): 12_documents/supplementary/tables/tabS15_human_model_agreement_v5_<date-time>.csv and .xlsx.
"""
import glob
import os
import sys
from datetime import datetime

import pandas as pd
from openpyxl.styles import Alignment

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_log  # noqa: E402

OUT_DIR = "12_documents/supplementary/tables"
RUNS = ("The first run gave every decision used in the review; the two further runs added no decision or datum. Of the 33 reports on which the runs differed, 19 went "
        "through a human decision or verification, among them the 2 that contributed to a pooled stratum and the 4 exclusions that both further runs proposed to include, "
        "which the reviewers included; the other 14 contributed to no pooled stratum (10 inclusions in the distribution analysis only and 4 exclusions not re-read, for "
        "which no run proposed inclusion). ")
RB8_ROLE = "No model (the other criteria were derived from the verified extraction)"
RB8_TASK = ("Two reviewers read the full text of 199 reports in calibration and 902 in the full pass, with a verbatim quote for every value other than not declared; "
            "disagreements arbitrated. One reviewer with a verifier coded the reports added during verification, by the reference-list check and in the last round")


def main():
    src = sorted(glob.glob(f"{OUT_DIR}/tabS15_human_model_agreement_v3_*.csv"))[-1]
    t = pd.read_csv(src, dtype=str, encoding="utf-8")
    r = t.index[t.stage == "Run-to-run reproducibility of the model"]
    b = t.index[t.stage == "Risk of bias: handling of repeated isolates (RB8)"]
    if len(r) != 1 or len(b) != 1:
        sys.exit("rows not found")
    t.loc[r, "outcome"] = RUNS + t.loc[r[0], "outcome"]
    for old, new in (("read 5939 full texts and proposed a decision per criterion", "read 5939 full texts, applied the criteria and recorded a decision per criterion"),
                     ("proposed the rows of the 15 reports", "extracted the rows of the 15 reports")):
        hits = t.model_role.str.contains(old, regex=False)
        if hits.sum() != 1:
            sys.exit(f"not found: {old}")
        t.loc[hits, "model_role"] = t.loc[hits, "model_role"].str.replace(old, new, regex=False)
    t.loc[b, "model_role"] = RB8_ROLE
    t.loc[b, "human_task"] = RB8_TASK
    t.loc[b, "human_decisions"] = str(2 * (199 + 902 + 13))
    now = datetime.now().astimezone()
    base = f"{OUT_DIR}/tabS15_human_model_agreement_v5_{now.strftime('%Y-%m-%dT%H%M%S')}"
    if os.path.exists(base + ".csv"):
        sys.exit("output exists")
    t.to_csv(base + ".csv", index=False, encoding="utf-8")
    total = int(t.human_decisions.astype(int).sum())
    with pd.ExcelWriter(base + ".xlsx", engine="openpyxl") as xw:
        t.to_excel(xw, index=False, sheet_name="Table S15")
        ws = xw.sheets["Table S15"]
        for col, w in zip("ABCDEFGHI", (5, 28, 14, 45, 12, 55, 70, 55, 50)):
            ws.column_dimensions[col].width = w
        for row in ws.iter_rows():
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        pd.DataFrame({"note": [
            "Table S15. Work done with the language model and human decisions by stage of the review, with the agreement between them where both exist. "
            f"Human decisions counted in this table: {total:,} (each record decided by two readers counts twice).",
            "Agreement statistics are those computed by the chain scripts named in the source column; kappa values carry their 95% confidence interval.",
            f"Built by 58_tabS15_human_model_agreement_v5.py on {now.isoformat(timespec='seconds')}."]}).to_excel(xw, index=False, sheet_name="Notes", header=False)
    log = run_log.write(__file__, [src], [base + ".csv", base + ".xlsx"], human_decisions_total=total, rows=len(t))
    print(f"written {base}.csv/.xlsx; human decisions {total:,}; log {log}")


if __name__ == "__main__":
    main()
