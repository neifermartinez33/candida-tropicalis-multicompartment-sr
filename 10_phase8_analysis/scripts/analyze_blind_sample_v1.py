#!/usr/bin/env python3
"""analyze_blind_sample_v1.py (2026-10-24)

Blind sample of round 2 (workbook B08, decision D2 point 5): compares the decision of the blind reading
with the earlier decision (r2_b08_key.csv) and writes the arbitration workbook for the third reviewer.

Reports, by stratum and in total:
  - proportion of reversed decisions, with exact Clopper-Pearson CI;
  - Cohen's kappa between the earlier decision and that of the blind reading (INCLUDE versus EXCLUDE), with a
    95 % CI by the asymptotic standard error of Fleiss, Cohen and Everitt;
  - the contingency table with the counts per cell;
  - extrapolation to the total of the stratum (expected number of wrong decisions = proportion x size of the
    stratum), declared as an estimate.
Usage, from the project root, when workbook B08 is complete:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/analyze_blind_sample_v1.py
Outputs (never overwritten), in 08_phase6_data_extraction/verification/round2_2026-10-24:
  r2_b08_agreement_<date-time>.csv and .json
  r2_b08b_arbitration.xlsx (discrepancies; arbiter_decision INCLUDE or EXCLUDE, ec_code, arbiter). It is read by
  build_analysis_dataset_v3.py.
"""
import json
import math
import os
import sys
from datetime import datetime

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

D = "08_phase6_data_extraction/verification/round2_2026-10-24"
BOOK, KEY, ARB = f"{D}/r2_b08_sample_blind.xlsx", f"{D}/r2_b08_key.csv", f"{D}/r2_b08b_arbitration.xlsx"
FONT = Font(name="Calibri", size=11, color="000000")


def lpmf(k, n, p):
    if p <= 0:
        return 0.0 if k == 0 else -math.inf
    if p >= 1:
        return 0.0 if k == n else -math.inf
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p)


def cdf(k, n, p):
    return sum(math.exp(lpmf(i, n, p)) for i in range(k + 1))


def exact_ci(k, n, a=0.05):
    if n == 0:
        return (math.nan, math.nan)

    def solve(f):
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) else (lo, mid)
        return (lo + hi) / 2
    return (0.0 if k == 0 else solve(lambda p: 1 - cdf(k - 1, n, p) < a / 2),
            1.0 if k == n else solve(lambda p: cdf(k, n, p) > a / 2))


def kappa(a, b):
    """Cohen's kappa for two categories and its 95 % CI (asymptotic standard error, Fleiss et al. 1969)."""
    cats = ["INCLUDE", "EXCLUDE"]
    n = len(a)
    if n == 0:
        return math.nan, math.nan, math.nan, {}
    t = {(i, j): sum(1 for x, y in zip(a, b) if x == i and y == j) for i in cats for j in cats}
    p = {k: v / n for k, v in t.items()}
    pr = {i: sum(p[(i, j)] for j in cats) for i in cats}
    pc = {j: sum(p[(i, j)] for i in cats) for j in cats}
    po = sum(p[(i, i)] for i in cats)
    pe = sum(pr[i] * pc[i] for i in cats)
    if pe == 1:
        return math.nan, math.nan, math.nan, t
    k = (po - pe) / (1 - pe)
    s1 = sum(p[(i, i)] * (1 - (pr[i] + pc[i]) * (1 - k)) ** 2 for i in cats)
    s2 = (1 - k) ** 2 * sum(p[(i, j)] * (pc[i] + pr[j]) ** 2 for i in cats for j in cats if i != j)
    s3 = (k - pe * (1 - k)) ** 2
    se = math.sqrt(max(s1 + s2 - s3, 0) / n) / (1 - pe)
    return k, k - 1.96 * se, k + 1.96 * se, t


def main():
    for f in (BOOK, KEY):
        if not os.path.exists(f):
            sys.exit(f"Missing {f}")
    b = pd.read_excel(BOOK, sheet_name="sample", dtype=object)
    k = pd.read_csv(KEY, dtype=str)
    m = b.merge(k, on=["sample_id", "study_id"], how="left", validate="one_to_one")
    m["blind"] = m.decision.astype(str).str.strip().str.upper()
    missing = m[~m.blind.isin(["INCLUDE", "EXCLUDE"])]
    if len(missing):
        sys.exit(f"Missing: {len(missing)} decisions in {BOOK} (for example {', '.join(missing.sample_id.head(5))})")
    m["prior"] = m.stratum.str.startswith("EXCLUDE").map({True: "EXCLUDE", False: "INCLUDE"})
    m["reversed"] = m.blind != m.prior
    rows = []
    for grp, g in list(m.groupby("stratum")) + [("TOTAL exclusions", m[m.prior == "EXCLUDE"]),
                                                ("TOTAL inclusions", m[m.prior == "INCLUDE"]), ("TOTAL", m)]:
        x, n = int(g.reversed.sum()), len(g)
        lo, hi = exact_ci(x, n)
        size = int(g.n_stratum.astype(int).iloc[0]) if not grp.startswith("TOTAL") else \
            int(g.drop_duplicates("stratum").n_stratum.astype(int).sum())
        rows.append({"stratum": grp, "sampled": n, "reversed": x, "prop_reversed": x / n if n else math.nan,
                     "ci_lower": lo, "ci_upper": hi, "stratum_size": size,
                     "expected_errors_in_stratum": round(x / n * size, 1) if n else math.nan})
    kp, klo, khi, tab = kappa(list(m.prior), list(m.blind))
    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    f_csv, f_json = f"{D}/r2_b08_agreement_{stamp}.csv", f"{D}/r2_b08_agreement_{stamp}.json"
    if os.path.exists(ARB):
        sys.exit(f"Already exists {ARB}: not overwritten (if it has to be redone, rename the earlier one)")
    pd.DataFrame(rows).to_csv(f_csv, index=False)
    json.dump({"script": os.path.basename(__file__), "run_time": datetime.now().astimezone().isoformat(timespec="seconds"),
               "kappa": kp, "kappa_ci": [klo, khi], "contingency_prior_by_blind": {f"{i}|{j}": v for (i, j), v in tab.items()},
               "observed_agreement": float((m.prior == m.blind).mean()), "n": len(m)},
              open(f_json, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    dis = m[m.reversed][["sample_id", "study_id", "title", "year", "pdf_file", "stratum", "ft_decision", "ft_reason",
                         "blind", "ec_code", "compartments", "n_tropicalis", "has_ast", "comment"]].rename(
        columns={"blind": "blind_decision", "ec_code": "blind_ec_code", "comment": "blind_comment"})
    for c in ("arbiter_decision", "ec_code", "arbiter", "date", "arbiter_comment"):
        dis[c] = None
    wb = Workbook()
    ws = wb.active
    ws.title = "instructions"
    for line in ["Arbitration of the blind sample (B08)",
                 "One row per report in which the blind reading does not match the earlier decision.",
                 "arbiter_decision: INCLUDE or EXCLUDE, with the application rule of the protocol; ec_code if EXCLUDE. The "
                 "arbiter's decision is final and is used by build_analysis_dataset_v3.py."]:
        ws.append([line])
    ws.column_dimensions["A"].width = 120
    sh = wb.create_sheet("arbitration")
    sh.append(list(dis.columns))
    for rec in dis.astype(object).where(dis.notna(), None).itertuples(index=False):
        sh.append(list(rec))
    for w in (ws, sh):
        for row in w.iter_rows():
            for c in row:
                c.font = FONT
                c.alignment = Alignment(wrap_text=True, vertical="top")
    for j, col in enumerate(dis.columns, start=1):
        sh.column_dimensions[get_column_letter(j)].width = 40 if col in ("title", "blind_comment") else 15
    for col, vals in (("arbiter_decision", ["INCLUDE", "EXCLUDE"]),
                      ("ec_code", [f"EC{i}" for i in (1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13)])):
        L = get_column_letter(list(dis.columns).index(col) + 1)
        dv = DataValidation(type="list", formula1='"' + ",".join(vals) + '"', allow_blank=True)
        sh.add_data_validation(dv)
        dv.add(f"{L}2:{L}{len(dis) + 1}")
    wb.save(ARB)
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"kappa {kp:.3f} (IC 95 % {klo:.3f} a {khi:.3f}); observed agreement {(m.prior == m.blind).mean():.3f}")
    print(f"Discrepancies for the third reviewer: {len(dis)} -> {ARB}")


if __name__ == "__main__":
    main()
