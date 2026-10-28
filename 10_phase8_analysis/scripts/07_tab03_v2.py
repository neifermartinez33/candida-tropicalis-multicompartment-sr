#!/usr/bin/env python3
"""07_tab03_v2.py (2026-10-24)

Table 3 (Results, SQ2): non-wild type by ECV and resistance by clinical breakpoint in C1, by
agent and criterion, with the figures of 06_ma_marginal_v3.R (rules v4). Changes from v1: corrected
notes (table_notes_v2), exact CI in the non-pooled strata, inferred-version flag according to SX1,
note on D4, Rule 4 and AR20, and provisional mode.
Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/07_tab03_v2.py [--provisional]
Outputs (never overwritten): 12_documents/tables/tab03_c1_resistance_v2_<date-time>[_PROVISIONAL].xlsx,
its CSV mirror in results and the log.
"""
import csv
import json
import os
import platform
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table_helpers as T  # noqa: E402
import table_notes_v2 as N  # noqa: E402

OUT_DIR, LOG_DIR = "12_documents/tables", os.path.join(N.RES, "logs")
RULES = "10_phase8_analysis/analysis_rules_v4_2026-10-24.md"
CRIT_ORDER = {"ECV_CLSI": 0, "ECV_EUCAST": 1, "CLSI_SS": 0, "CLSI_SS+EUCAST": 1, "CLSI_pre2012": 2, "EUCAST": 3}
HEADERS = ["Antifungal agent", "Interpretive criterion", "Collections, *k* (groups)", "Events/isolates tested",
           "Crude, %", "Pooled mean, % (95% CI)", "Median, % (95% CI)", "95% prediction interval, %",
           T.TAU2 + " (95% CI)", "Largest collection, %"]
WIDTHS = [15, 24, 11, 14, 14, 19, 19, 15, 17, 11]
CAPTION = ["Proportion of ", ("i", "Candida tropicalis"), " isolates from compartment C1, the human host, that were "
           "non-wild-type by epidemiological cut-off value or resistant by clinical breakpoint, by antifungal agent and "
           "interpretive criterion."]


def rows_of(recs):
    out = []
    for r in recs:
        marker = N.NOT_POOLED.get(r["status"])
        agent = r["agent"][0].upper() + r["agent"][1:]
        crit = T.CRITERION[r["regime_stratum"]]
        out.append([(agent, marker) if marker else agent,
                    (crit, N.FLAG) if int(float(r["flagged_main_rows"] or 0)) else crit,
                    f"{int(float(r['k_collections']))} ({int(float(r['research_groups']))})",
                    f"{int(float(r['events'])):,}/{int(float(r['isolates'])):,}",
                    N.crude_exact(r)] + N.model_cells(r) + [T.pct(float(r["largest_collection_pct"]) / 100)])
    return out


def main():
    prov = N.mode()
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    f_res, f_st = N.inputs(prov)
    for f in (RULES, f_res, f_st):
        if not os.path.exists(f):
            sys.exit(f"Missing {f}")
    res, st = N.read(f_res), N.read(f_st)
    met = {N.key_of(r) for r in st if r["meets_minimum"] == "True"}
    if met != {N.key_of(r) for r in res}:
        sys.exit("The results CSV does not carry the same strata that meet AR12")
    c1 = [r for r in res if r["compartment"] == "C1"]
    blocks = []
    for oc in ("NWT", "R"):
        sel = sorted([r for r in c1 if r["outcome"] == oc], key=lambda r: (r["agent"], CRIT_ORDER[r["regime_stratum"]]))
        if sel:
            blocks.append((T.OUTCOME[oc], rows_of(sel)))
    below = [r for r in st if r["compartment"] == "C1" and r["meets_minimum"] != "True"]
    extra = [("13", f"A further {len(below)} C1 strata did not reach the minimum condition and are described in the "
                    f"supplementary material: {sum(int(float(r['events'])) for r in below):,} events in "
                    f"{sum(int(float(r['isolates'])) for r in below):,} isolates tested.")]
    notes = N.footnotes(prov, extra)
    cap = ([("i", "[PROVISIONAL] ")] if prov else []) + CAPTION
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S") + ("_PROVISIONAL" if prov else "")
    xlsx = os.path.join(OUT_DIR, f"tab03_c1_resistance_v2_{stamp}.xlsx")
    mirror = os.path.join(N.RES, f"tab03_c1_resistance_v2_{stamp}.csv")
    for f in (xlsx, mirror):
        if os.path.exists(f):
            sys.exit(f"Already exists {f}: not overwritten")
    T.write_table(xlsx, "Table 3", 3, cap, HEADERS, WIDTHS, blocks, notes)
    with open(mirror, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["block"] + [T.plain(h) for h in HEADERS])
        for lab, rws in blocks:
            for cells in rws:
                w.writerow([lab] + [c[0] if isinstance(c, tuple) else c for c in cells])
    n_rows = sum(len(r) for _, r in blocks)
    pooled = sum(1 for r in c1 if r["status"] == "pooled")
    log = {"script": os.path.basename(__file__), "mode": "PROVISIONAL" if prov else "FINAL",
           "run_time": datetime.now().astimezone().isoformat(timespec="seconds"), "python": platform.python_version(),
           "inputs": {p: T.md5(p) for p in (RULES, f_res, f_st)},
           "outputs": {os.path.basename(p): T.md5(p) for p in (xlsx, mirror)},
           "c1_strata_in_table": n_rows, "c1_pooled": pooled, "c1_below_minimum": len(below)}
    with open(os.path.join(LOG_DIR, f"07_tab03_v2_{stamp}.json"), "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False)
    print(f"Table 3: {n_rows} C1 strata ({pooled} pooled), {len(below)} below AR12 in the footnote\nWorkbook: {xlsx}")


if __name__ == "__main__":
    main()
