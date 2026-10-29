#!/usr/bin/env python3
"""41_tabS16_grade_v1.py (2026-10-29)

Table S16: certainty of the evidence (GRADE) for every pooled stratum, with the thresholds that the review
team approved on 2026-10-29. It supersedes the draft written by 35_grade_draft_v1.py, whose thresholds were a
proposal; the thresholds are unchanged from that draft and are recorded here, in the table footnotes and in the
deviation log (Table S12), because they were fixed after the data had been seen.

GRADE adapted to single proportions estimated from observational data: the starting level is high, as for
prevalence questions, and each domain is operationalised with a rule that can be recomputed from the deposited
results.
  risk of bias    serious (1 level) if more than 50% of the isolates of the stratum come from collections whose
                  index report is at high risk of bias
  inconsistency   serious (1) if the 95% prediction interval spans more than 50 percentage points; very serious
                  (2) if it spans more than 75
  imprecision     serious (1) if the width of the 95% confidence interval of the population mean exceeds the
                  estimate itself, or if fewer than 300 isolates contribute
  indirectness    serious (1) for the non-human compartments, which pool heterogeneous hosts or matrices within
                  one compartment; not serious for the human host
  publication     not downgraded: conventional funnel asymmetry tests are not valid for proportions
                  (Section 2.9); non-retrieval is examined instead (Table S11)
Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/41_tabS16_grade_v1.py
Outputs (never overwritten): 12_documents/supplementary/tables/tabS16_grade_v1_<date-time>.xlsx and its CSV
mirror; log in 10_phase8_analysis/results/logs/41_tabS16_grade_v1_<date-time>.json.
"""
import csv
import glob
import os
import sys
from collections import Counter
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_log  # noqa: E402
import table_helpers as T  # noqa: E402

RES = "10_phase8_analysis/results"
OUT_DIR = "12_documents/supplementary/tables"
RULES = {"rob_high_share": 0.50, "pi_serious": 50, "pi_very": 75, "min_isolates": 300}
LEVELS = ["Very low", "Low", "Moderate", "High"]
COMPARTMENT = {"C1": "C1, human host", "C2": "C2, animal host", "C6": "C6, anthropogenic matrices"}
OUT_SHORT = {"NWT": "Non-wild-type", "R": "Resistant"}
STEP = {0: "Not serious", 1: "Serious", 2: "Very serious"}


def newest(pattern, folder=RES):
    hits = sorted(glob.glob(os.path.join(folder, pattern)))
    if not hits:
        sys.exit(f"missing input: {pattern}")
    return hits[-1]


def main():
    stamp = datetime.now().astimezone()
    res_p = newest("ma_results_v3_*.csv")
    inp_p = newest("ma_input_v2_*.csv")
    rob_p = newest("rob_assessment_v2_*.csv", "09_phase7_risk_of_bias/results")
    res = pd.read_csv(res_p)
    pooled = res[res["status"] == "pooled"].copy()
    x = pd.read_csv(inp_p, low_memory=False)
    rob = pd.read_csv(rob_p)[["study_id", "overall_judgement"]].drop_duplicates()
    x = x[x["main"] == True].merge(rob, on="study_id", how="left")  # noqa: E712
    key = ["compartment", "agent", "outcome", "regime_stratum"]
    rows, counts = [], Counter()
    for _, r in pooled.iterrows():
        g = x
        for k in key:
            g = g[g[k] == r[k]]
        n = g["n_tested"].sum()
        high = g.loc[g["overall_judgement"].astype(str).str.lower().str.startswith("high"), "n_tested"].sum()
        share = float(high) / float(n) if n else float("nan")
        p, lo, hi = 100 * r["p_marginal"], 100 * r["marg_lower"], 100 * r["marg_upper"]
        pi_width = 100 * (r["pi_upper"] - r["pi_lower"])
        d_rob = 1 if share > RULES["rob_high_share"] else 0
        d_inc = 2 if pi_width > RULES["pi_very"] else (1 if pi_width > RULES["pi_serious"] else 0)
        d_imp = 1 if ((hi - lo) > p or r["isolates"] < RULES["min_isolates"]) else 0
        d_ind = 0 if r["compartment"] == "C1" else 1
        level = LEVELS[max(0, 3 - d_rob - d_inc - d_imp - d_ind)]
        counts[level] += 1
        counts["strata"] += 1
        rows.append({
            "compartment": r["compartment"], "agent": r["agent"], "outcome": r["outcome"],
            "regime": r["regime_stratum"], "k": int(r["k_collections"]), "groups": int(r["research_groups"]),
            "isolates": int(r["isolates"]), "estimate": T.pct_ci(r["p_marginal"], r["marg_lower"], r["marg_upper"]),
            "pi": T.pct_range(r["pi_lower"], r["pi_upper"]), "rob_share": T.pct(share),
            "pi_width": f"{pi_width:.1f}", "d_rob": d_rob, "d_inc": d_inc, "d_imp": d_imp, "d_ind": d_ind,
            "certainty": level})
    tab = pd.DataFrame(rows).sort_values(["compartment", "outcome", "agent", "regime"])

    headers = ["Compartment", "Agent", "Outcome and interpretive criterion", "Collections (groups)", "Isolates",
               "Population mean, % (95% CI)", "95% prediction interval, %", "Risk of bias", "Inconsistency",
               "Imprecision", "Indirectness", "Publication bias", "Certainty"]
    widths = [14, 13, 21, 9, 8, 15, 13, 13, 13, 11, 11, 11, 9]
    blocks = []
    for comp in ("C1", "C2", "C6"):
        part = tab[tab.compartment == comp]
        if not len(part):
            continue
        body = []
        for _, r in part.iterrows():
            body.append([
                COMPARTMENT.get(comp, comp), r["agent"][0].upper() + r["agent"][1:],
                f"{OUT_SHORT.get(r['outcome'], r['outcome'])}, {T.CRITERION.get(r['regime'], r['regime'])}",
                f"{r['k']} ({r['groups']})", f"{r['isolates']:,}".replace(",", chr(8239)), r["estimate"], r["pi"],
                (STEP[r["d_rob"]], "1") if r["d_rob"] else (STEP[r["d_rob"]], "1"),
                (STEP[r["d_inc"]], "2"), (STEP[r["d_imp"]], "3"), (STEP[r["d_ind"]], "4"),
                ("Not downgraded", "5"), r["certainty"]])
        blocks.append((COMPARTMENT.get(comp, comp), body))
    cap = ["Certainty of the evidence of every pooled stratum of ", ("i", "Candida tropicalis"),
           " collections, rated with GRADE adapted to single proportions estimated from observational data. "
           "The starting level is high and each domain is operationalised with a rule that can be recomputed "
           "from the deposited results; the rules were fixed after the data had been seen and are declared in "
           "Table S12"]
    notes = [
        ("1", f"Serious when more than {100 * RULES['rob_high_share']:.0f}% of the isolates of the stratum come "
              "from collections whose index report is at high risk of bias (Table S8). The share is given in the "
              "CSV mirror of this table."),
        ("2", f"Serious when the 95% prediction interval spans more than {RULES['pi_serious']} percentage points, "
              f"very serious when it spans more than {RULES['pi_very']}. The prediction interval is preferred to "
              "*I*², which is not informative for proportions (Section 2.7)."),
        ("3", "Serious when the width of the 95% confidence interval of the population mean exceeds the estimate "
              f"itself, or when fewer than {RULES['min_isolates']} isolates contribute to the stratum."),
        ("4", "Serious for the non-human compartments, which pool heterogeneous hosts or matrices within one "
              "compartment, and not serious for the human host."),
        ("5", "Not downgraded in any stratum: conventional funnel asymmetry tests are not valid for meta-analyses "
              "of proportions (Section 2.9), so reporting bias was examined by comparing the reports that could "
              "not be retrieved with those assessed (Table S11) and by excluding preprints (Table S4)."),
        ("6", "CI, confidence interval; CLSI, Clinical and Laboratory Standards Institute; ECV, epidemiological "
              "cut-off value; EUCAST, European Committee on Antimicrobial Susceptibility Testing; GRADE, Grading "
              "of Recommendations, Assessment, Development and Evaluations."),
    ]
    st = stamp.strftime("%Y-%m-%dT%H%M%S")
    base = f"{OUT_DIR}/tabS16_grade_v1_{st}"
    if os.path.exists(base + ".xlsx"):
        sys.exit("output exists")
    T.write_table(base + ".xlsx", "Table S16", "S16", cap, headers, widths, blocks, notes)
    with open(base + ".csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["compartment", "agent", "outcome", "regime", "collections", "research_groups", "isolates",
                    "population_mean_pct_ci", "prediction_interval_pct", "isolates_from_high_rob_pct",
                    "pi_width_points", "downgrade_risk_of_bias", "downgrade_inconsistency",
                    "downgrade_imprecision", "downgrade_indirectness", "downgrade_publication_bias", "certainty"])
        for _, r in tab.iterrows():
            w.writerow([r["compartment"], r["agent"], r["outcome"], r["regime"], r["k"], r["groups"], r["isolates"],
                        T.plain(r["estimate"]), T.plain(r["pi"]), r["rob_share"], r["pi_width"], r["d_rob"],
                        r["d_inc"], r["d_imp"], r["d_ind"], 0, r["certainty"]])
    log = run_log.write(__file__, [res_p, inp_p, rob_p], [base + ".xlsx", base + ".csv"],
                        thresholds=RULES, strata=int(counts["strata"]),
                        certainty={k: int(counts[k]) for k in LEVELS[::-1]})
    print(f"written {base}.xlsx/.csv; log {log}")
    print({k: counts[k] for k in LEVELS[::-1]}, "strata", counts["strata"])
    print(tab[["compartment", "agent", "outcome", "regime", "estimate", "pi", "rob_share", "pi_width",
               "d_rob", "d_inc", "d_imp", "d_ind", "certainty"]].to_string(index=False))


if __name__ == "__main__":
    main()
