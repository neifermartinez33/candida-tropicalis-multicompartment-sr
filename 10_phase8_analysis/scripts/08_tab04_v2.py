#!/usr/bin/env python3
"""08_tab04_v2.py (2026-10-24)

Table 4 (Results, SQ2): non-human compartments, C2 to C6, both outcomes (non-wild type by ECV and
resistance by clinical breakpoint), every stratum with at least two independent collections,
pooled where possible (AR12 and AR18) and described where not. Changes from v1: includes the primary
outcome if any non-clinical stratum has it (v1 stopped), notes computed from the data (v1 had
a fixed figure), corrected notes (table_notes_v2), exact CI in the non-pooled ones and provisional mode. The
reading of C5 is the strict one (main); the broad one goes in SA1.
Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/08_tab04_v2.py [--provisional]
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
LOOKUP = "10_phase8_analysis/data/lookups/compartments_v1.csv"
MIN_K = 2
CRIT_ORDER = {"ECV_CLSI": 0, "ECV_EUCAST": 1, "CLSI_SS": 2, "CLSI_SS+EUCAST": 3, "CLSI_pre2012": 4, "EUCAST": 5}
HEADERS = ["Compartment", "Outcome", "Antifungal agent", "Interpretive criterion", "Collections, *k* (groups)",
           "Events/isolates tested", "Crude, %", "Pooled mean, % (95% CI)", "Median, % (95% CI)",
           "95% prediction interval, %", T.TAU2 + " (95% CI)", "Largest collection, %"]
WIDTHS = [12, 10, 15, 22, 11, 13, 14, 18, 18, 14, 16, 10]
CAPTION = ["Proportion of ", ("i", "Candida tropicalis"), " isolates that were non-wild-type by epidemiological cut-off "
           "value or resistant by clinical breakpoint in the non-human compartments C2 to C6, by compartment, outcome, "
           "antifungal agent and interpretive criterion. Strata with at least two independent collections."]
OUT_SHORT = {"NWT": "Non-wild-type", "R": "Resistant"}


def main():
    prov = N.mode()
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    f_res, f_st = N.inputs(prov)
    for f in (RULES, f_res, f_st, LOOKUP):
        if not os.path.exists(f):
            sys.exit(f"Missing {f}")
    res = {N.key_of(r): r for r in N.read(f_res)}
    st = N.read(f_st)
    name = {r["code"]: r["short_label"] for r in N.read(LOOKUP)}
    non = [r for r in st if r["compartment"] != "C1"]
    shown = sorted([r for r in non if int(float(r["k_collections"])) >= MIN_K],
                   key=lambda r: (r["compartment"], r["outcome"] != "NWT", r["agent"], CRIT_ORDER[r["regime_stratum"]]))
    rest = [r for r in non if int(float(r["k_collections"])) < MIN_K]
    blocks = []
    for code in sorted({r["compartment"] for r in shown}):
        rows = []
        for r in (x for x in shown if x["compartment"] == code):
            m = res.get(N.key_of(r))
            status = m["status"] if m else "below_minimum"
            marker = N.NOT_POOLED.get(status)
            crit = T.CRITERION[r["regime_stratum"]]
            ev, n = int(float(r["events"])), int(float(r["isolates"]))
            if m:
                crude = N.crude_exact(m)
                model = N.model_cells(m)
            else:
                lo, hi = N.exact_ci(ev, n)
                crude = T.pct_ci(ev / n, lo, hi)
                model = [T.DASH] * 4
            rows.append([(r["compartment"], marker) if marker else r["compartment"], OUT_SHORT[r["outcome"]],
                         r["agent"][0].upper() + r["agent"][1:],
                         (crit, N.FLAG) if int(float(r["flagged_main_rows"] or 0)) else crit,
                         f"{int(float(r['k_collections']))} ({int(float(r['research_groups']))})",
                         f"{ev:,}/{n:,}", crude] + model + [T.pct(float(r["largest_collection_pct"]) / 100)])
        blocks.append((f"{code} {name.get(code, code)}", rows))
    by_comp = {}
    for r in rest:
        c = by_comp.setdefault(r["compartment"], [0, 0, 0])
        c[0] += 1
        c[1] += int(float(r["events"]))
        c[2] += int(float(r["isolates"]))
    remainder = "; ".join(f"{c} {v[0]} strata, {v[1]:,}/{v[2]:,}" for c, v in sorted(by_comp.items())) or "none"
    nwt_shown = sum(1 for r in shown if r["outcome"] == "NWT")
    extra = [("13", f"Strata with a single collection, not shown: {remainder} (events/isolates tested); listed in the "
                    f"supplementary material. Non-wild-type strata shown: {nwt_shown}."),
             ("14", "Compartment C5 in its strict reading (documented absence of agronomic management); the broad reading "
                    "is sensitivity analysis SA1.")]
    notes = N.footnotes(prov, extra)
    cap = ([("i", "[PROVISIONAL] ")] if prov else []) + CAPTION
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S") + ("_PROVISIONAL" if prov else "")
    xlsx = os.path.join(OUT_DIR, f"tab04_nonhuman_v2_{stamp}.xlsx")
    mirror = os.path.join(N.RES, f"tab04_nonhuman_v2_{stamp}.csv")
    for f in (xlsx, mirror):
        if os.path.exists(f):
            sys.exit(f"Already exists {f}: not overwritten")
    T.write_table(xlsx, "Table 4", 4, cap, HEADERS, WIDTHS, blocks, notes)
    with open(mirror, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["block"] + [T.plain(h) for h in HEADERS])
        for lab, rws in blocks:
            for cells in rws:
                w.writerow([lab] + [c[0] if isinstance(c, tuple) else c for c in cells])
    pooled = sum(1 for r in shown if res.get(N.key_of(r), {}).get("status") == "pooled")
    log = {"script": os.path.basename(__file__), "mode": "PROVISIONAL" if prov else "FINAL",
           "run_time": datetime.now().astimezone().isoformat(timespec="seconds"), "python": platform.python_version(),
           "inputs": {p: T.md5(p) for p in (RULES, f_res, f_st, LOOKUP)},
           "outputs": {os.path.basename(p): T.md5(p) for p in (xlsx, mirror)},
           "strata_shown": len(shown), "pooled": pooled, "nwt_shown": nwt_shown, "single_collection": len(rest)}
    with open(os.path.join(LOG_DIR, f"08_tab04_v2_{stamp}.json"), "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False)
    print(f"Table 4: {len(shown)} strata ({pooled} pooled; NWT {nwt_shown}), {len(rest)} of a single collection in the footnote\nWorkbook: {xlsx}")


if __name__ == "__main__":
    main()
