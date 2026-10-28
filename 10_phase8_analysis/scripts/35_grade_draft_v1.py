"""DRAFT GRADE certainty and summary of findings for the pooled strata, for decision by the review team.

The protocol applies GRADE as adapted to single-proportion estimates from observational studies: study limitations
from the aggregate risk-of-bias judgement, inconsistency from the width of the prediction interval (not I2),
imprecision from the CI width relative to the proportion and from the number of isolates and collections,
indirectness from the correspondence with the review framework, and publication bias with the caution stated for
proportions. The protocol does not fix numeric thresholds; the thresholds below are PROPOSALS of this draft and are
written in the output so the team can change them before any judgement enters the manuscript.

Proposed rules (starting level high, as for proportions estimated from cross-sectional data):
  risk of bias    serious if more than 50% of the isolates come from collections whose index report is at high risk
  inconsistency   serious if the 95% prediction interval spans more than 50 percentage points; very serious if > 75
  imprecision     serious if the CI width exceeds the estimate itself or fewer than 300 isolates contribute
  indirectness    serious for non-human compartments (heterogeneous hosts or matrices pooled within one compartment);
                  not serious for the human host
  publication     not downgraded: funnel asymmetry is not valid for proportions (Section 2.9); non-retrieval bias is
                  discussed instead
Usage: python 35_grade_draft_v1.py   (from the project root)
"""
import glob, os, datetime
import sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_log  # noqa: E402

RES = "10_phase8_analysis/results"
LEVELS = ["very low", "low", "moderate", "high"]
RULES = {"rob_high_share": 0.50, "pi_serious": 50, "pi_very": 75, "min_isolates": 300}

def newest(p):
    return sorted(glob.glob(os.path.join(RES, p)))[-1]

def main():
    st = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S")
    res = pd.read_csv(newest("ma_results_v3_*.csv"))
    pooled = res[res["status"] == "pooled"].copy()
    x = pd.read_csv(newest("ma_input_v2_*.csv"))
    rob = pd.read_csv(sorted(glob.glob("09_phase7_risk_of_bias/results/rob_assessment_v2_*.csv"))[-1])
    rob = rob[["study_id", "overall_judgement"]].drop_duplicates()
    x = x[x["main"] == True].merge(rob, on="study_id", how="left")
    key = ["compartment", "agent", "outcome", "regime_stratum"]
    rows = []
    for _, r in pooled.iterrows():
        g = x
        for k in key:
            g = g[g[k] == r[k]]
        n = g["n_tested"].sum()
        high = g.loc[g["overall_judgement"].astype(str).str.lower().str.startswith("high"), "n_tested"].sum()
        share = high / n if n else float("nan")
        p, lo, hi = 100 * r["p_marginal"], 100 * r["marg_lower"], 100 * r["marg_upper"]
        piw = 100 * (r["pi_upper"] - r["pi_lower"])
        d_rob = 1 if share > RULES["rob_high_share"] else 0
        d_inc = 2 if piw > RULES["pi_very"] else (1 if piw > RULES["pi_serious"] else 0)
        d_imp = 1 if ((hi - lo) > p or r["isolates"] < RULES["min_isolates"]) else 0
        d_ind = 0 if r["compartment"] == "C1" else 1
        level = LEVELS[max(0, 3 - d_rob - d_inc - d_imp - d_ind)]
        reasons = [s for s, d in (("risk of bias", d_rob), ("inconsistency", d_inc), ("imprecision", d_imp),
                                  ("indirectness", d_ind)) if d]
        rows.append({"compartment": r["compartment"], "agent": r["agent"], "outcome": r["outcome"],
                     "regime": r["regime_stratum"], "collections": int(r["k_collections"]), "isolates": int(r["isolates"]),
                     "estimate_pct": round(p, 1), "ci": f"{lo:.1f}–{hi:.1f}",
                     "pi": f"{100 * r['pi_lower']:.1f}–{100 * r['pi_upper']:.1f}",
                     "isolates_high_rob_pct": round(100 * share, 1), "pi_width_points": round(piw, 1),
                     "down_rob": d_rob, "down_inconsistency": d_inc, "down_imprecision": d_imp, "down_indirectness": d_ind,
                     "down_publication": 0, "proposed_certainty": level,
                     "reasons": "; ".join(reasons) if reasons else "none"})
    out = pd.DataFrame(rows).sort_values(["compartment", "outcome", "agent", "regime"])
    os.makedirs(os.path.join(RES, "grade_draft"), exist_ok=True)
    p = os.path.join(RES, "grade_draft", f"grade_draft_v1_{st}.csv")
    out.to_csv(p, index=False)
    with open(p.replace(".csv", "_rules.txt"), "w") as f:
        f.write(__doc__ + "\nThresholds used: " + repr(RULES) + "\n")
    print(run_log.write(__file__, [newest("ma_results_v3_*.csv"), newest("ma_input_v2_*.csv"),
                                   sorted(glob.glob("09_phase7_risk_of_bias/results/rob_assessment_v2_*.csv"))[-1]],
                        [p, p.replace(".csv", "_rules.txt")], mode="DRAFT", thresholds=RULES))
    print(p)
    print(out[["compartment", "agent", "outcome", "regime", "estimate_pct", "isolates_high_rob_pct", "pi_width_points",
               "proposed_certainty", "reasons"]].to_string(index=False))

if __name__ == "__main__":
    main()
