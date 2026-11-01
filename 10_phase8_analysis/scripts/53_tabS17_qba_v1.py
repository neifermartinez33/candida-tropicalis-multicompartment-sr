#!/usr/bin/env python3
"""53_tabS17_qba_v1.py (2026-10-30)

Table S17: results of the quantitative bias analysis of the full-text exclusions that no reviewer re-read
(45_qba_missed_reports_v2.R), by pooled stratum, rate model and scenario. It reads the results and changes nothing.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/53_tabS17_qba_v1.py
Outputs (never overwritten): 12_documents/supplementary/tables/tabS17_qba_v1_<date-time>.xlsx and its CSV mirror;
log in 10_phase8_analysis/results/logs/.
"""
import glob
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_log  # noqa: E402
import table_helpers as T  # noqa: E402

RES = "10_phase8_analysis/results"
OUT_DIR = "12_documents/supplementary/tables"
COMPARTMENT = {"C1": "C1, human host", "C2": "C2, animal host", "C6": "C6, anthropogenic matrices"}
OUT_SHORT = {"NWT": "Non-wild-type", "R": "Resistant"}
MODEL = {"empirical": "Observed rate", "pessimistic": "Pessimistic rate"}


def shift(r):
    a, b, c = [f"{r[k]:.1f}".replace("-0.0", "0.0") for k in ("change_pp_median", "change_pp_p2.5", "change_pp_p97.5")]
    return f"{a} ({b} to {c})".replace("-", chr(8722))


def main():
    src = sorted(glob.glob(f"{RES}/qba_missed_reports_v2_*[0-9].csv"))[-1]
    q = pd.read_csv(src)
    if q.failed_fits.sum():
        sys.exit("failed fits in the bias analysis")
    k = q.stratum.str.split(" | ", regex=False, expand=True)
    q["compartment"], q["agent"], q["outcome"], q["regime"] = k[0], k[1], k[2], k[3]
    rows = []
    for (comp, ag, out, reg, model), g in q.groupby(["compartment", "agent", "outcome", "regime", "rate_model"], sort=True):
        s = g.set_index("scenario")
        e = s.loc["exchangeable"]
        rows.append(dict(compartment=comp, agent=ag, outcome=out, regime=reg, rate_model=model, pooled_mean_pct=f"{e['p_marginal_pct']:.1f}",
                         missed_reports_median=int(e["missed_reports_median"]), missed_reports_p95=int(e["missed_reports_p95"]),
                         share_simulations_stratum_changed_pct=f"{100 * e['share_sims_stratum_changed']:.1f}",
                         as_observed=shift(s.loc["exchangeable"]), percentile_90=shift(s.loc["high"]), percentile_10=shift(s.loc["low"])))
    tab = pd.DataFrame(rows)
    headers = ["Compartment", "Agent", "Outcome and interpretive criterion", "Pooled mean, %", "Rate model", "Reports added, median (95th percentile)",
               "Simulations that changed the stratum, %", "Reports as observed", "Reports at the 90th percentile", "Reports at the 10th percentile"]
    widths = [14, 13, 22, 8, 12, 11, 12, 15, 15, 15]
    blocks = []
    for comp in ("C1", "C2", "C6"):
        body = [[COMPARTMENT[comp], r.agent[0].upper() + r.agent[1:], f"{OUT_SHORT[r.outcome]}, {T.CRITERION.get(r.regime, r.regime)}", r.pooled_mean_pct,
                 MODEL[r.rate_model], f"{r.missed_reports_median} ({r.missed_reports_p95})", r.share_simulations_stratum_changed_pct,
                 r.as_observed, r.percentile_90, r.percentile_10] for r in tab[tab.compartment == comp].itertuples()]
        blocks.append((COMPARTMENT[comp], body))
    cap = ["Quantitative bias analysis of the 1045 full-text exclusions that no reviewer re-read, by pooled stratum of ", ("i", "Candida tropicalis"),
           " collections. Change in the population mean, in percentage points: median (2.5th to 97.5th percentile) of 1000 simulations per rate model "
           "and scenario. The analysis was not prespecified"]
    notes = [
        ("1", "Observed rate: Beta(3.5, 466.5), from the 3 of the 469 sampled exclusions that became reports contributing to a pooled stratum. Pessimistic rate: "
              "Beta(41.5, 428.5) multiplied by Beta(1219.5, 2073.5), that is, the 41 of 469 exclusions reversed in the blind sample multiplied by the share of the "
              "included reports eligible for the meta-analysis. The 808 re-read exclusions are left out of the rate because they were selected for susceptibility data."),
        ("2", "In each simulation a binomial number of reports was drawn from the 1045, each one being a report eligible for the meta-analysis drawn at random, with "
              "all its main rows, entering as a new independent collection, and the main model was refitted in the strata that received rows. In the last two columns "
              "the events of the added reports were set to the 90th or the 10th percentile of the collection proportions of the stratum."),
        ("3", "CLSI, Clinical and Laboratory Standards Institute; ECV, epidemiological cut-off value; EUCAST, European Committee on Antimicrobial Susceptibility Testing."),
    ]
    st = datetime.now().astimezone().strftime("%Y-%m-%dT%H%M%S")
    base = f"{OUT_DIR}/tabS17_qba_v1_{st}"
    if os.path.exists(base + ".xlsx"):
        sys.exit("output exists")
    T.write_table(base + ".xlsx", "Table S17", "S17", cap, headers, widths, blocks, notes)
    tab.to_csv(base + ".csv", index=False, encoding="utf-8")
    log = run_log.write(__file__, [src], [base + ".xlsx", base + ".csv"], rows=len(tab))
    print(f"written {base}.xlsx/.csv; {len(tab)} rows; log {log}")


if __name__ == "__main__":
    main()
