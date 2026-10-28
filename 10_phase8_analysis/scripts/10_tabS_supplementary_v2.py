#!/usr/bin/env python3
"""10_tabS_supplementary_v2.py (2026-10-24)

v2: reads ma_results_v3 and the ma_strata_v2 and ma_input_v2 of the same run (through the log of
06_ma_marginal_v3.R); the names of the compartments come from the lookup table of the project
(v1 carried names from another scheme: "C2, hospital and urban wastewater", "C4, food and food
industry"..., which are not the compartments of this review); the notes that v1 had fixed are
computed from the data; the row flag is that of SX1 (rules v4); --provisional mode.

Tables of the supplementary material, in the same style as Tables 3 and 4 (table_helpers):

  S1  Heterogeneity of the strata that meet the minimum condition (AR12): Q, I2 and tau2.
      AR17 sends Q and I2 to the supplement with the warning that `meta` computes them with the
      inverse-variance formulation and not with the GLMM, so they are not the statistic of the
      fitted model, and the prediction interval is what is interpreted.
  S2  Inventory of the 102 strata: k, groups, reports, events, isolates, crude proportion,
      contribution of the largest collection, rows flagged by AR6 and whether it meets AR12.
  S3  Non-clinical compartments (C2 to C6): the same inventory plus the range per collection and the
      exact binomial interval of the total, which is what AR18 requires to report when there is no pooling.

The sensitivity table is S4 and is built separately, when the 09a and 09b run finishes.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/10_tabS_supplementary_v2.py --check [--provisional]
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/10_tabS_supplementary_v2.py [--provisional]

Outputs (never overwritten):
  12_documents/supplementary/tables/tabS0{1,2,3}_*_v2_<date-time>[_PROVISIONAL].xlsx   and their CSV mirror
  10_phase8_analysis/results/logs/tabS_supplementary_v2_<date-time>.json
"""
import csv, glob, json, os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from table_helpers import (CRITERION, DASH, EN, I2, OUTCOME, TAU2, md5, miss, pct, pct_ci,
                           pct_range, plain, tau_ci, write_table)

import table_notes_v2 as N  # noqa: E402

LOOKUP = "10_phase8_analysis/data/lookups/compartments_v1.csv"
OUT_DIR = "12_documents/supplementary/tables"
LOG_DIR = "10_phase8_analysis/results/logs"

SP = ("i", "C. tropicalis")
STATUS = {"pooled": "Pooled",
          "not_pooled_boundary_AR18a": "Not pooled: all collections at the boundary",
          "not_pooled_tau2_AR18b": "Not pooled: upper limit of the profile interval for "
                                    + plain(TAU2) + " above 25",
          "not_pooled_no_profile_AR18c": "Not pooled: profile interval for " + plain(TAU2)
                                          + " not obtained"}
with open(LOOKUP, encoding="utf-8-sig", newline="") as _f:
    COMPART = {r["code"]: f"{r['code']} {r['short_label']}" for r in csv.DictReader(_f)}


def last_(pattern):
    f = sorted(glob.glob(pattern))
    if not f:
        sys.exit(f"There is no {pattern}")
    return f[-1]


def leer(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def ent(v):
    return DASH if miss(v) else f"{int(float(v)):,}".replace(",", chr(8201))


def dec(v, d=2):
    return DASH if miss(v) else f"{float(v):.{d}f}"


def si_no(v):
    return "Yes" if str(v).strip() in ("True", "TRUE", "YES", "1") else "No"


def crit(r):
    return CRITERION.get(r["regime_stratum"], r["regime_stratum"])


def order(r):
    o = {"NWT": 0, "R": 1}
    return (r["compartment"], r["agent"], o.get(r["outcome"], 9), r["regime_stratum"])


def mirror(path, headers, rows):
    """CSV mirror of the table, without italics marks: it is what is cited and read again."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([plain(h) for h in headers])
        for row in rows:
            w.writerow([plain(c[0] if isinstance(c, tuple) else c) for c in row])


def table_s1(res, p_xlsx, p_csv):
    ok = sorted([r for r in res], key=order)
    headers = ["Compartment", "Agent", "Outcome and interpretive criterion",
               ["k", " collections"], ["Q", ""], ["df", ""], ["P", " value"], I2 + ", %",
               TAU2 + " (95% CI)", "Model status"]
    headers[3] = [("i", "k"), " collections"]
    headers[4] = [("i", "Q")]
    headers[5] = [("i", "df")]
    headers[6] = [("i", "P"), " value"]
    widths = [12, 15, 30, 9, 9, 6, 8, 8, 17, 30]
    rows = []
    for r in ok:
        rows.append([
            COMPART.get(r["compartment"], r["compartment"]), r["agent"],
            f"{OUTCOME.get(r['outcome'], r['outcome'])}, {crit(r)}",
            ent(r["k_collections"]), dec(r["Q"], 1), ent(r["df_Q"]),
            DASH if miss(r["pval_Q"]) else (f"{float(r['pval_Q']):.3f}"
                                            if float(r["pval_Q"]) >= 0.001 else "<0.001"),
            pct(r["I2"], 1), tau_ci(r["tau2"], r["tau2_lower"], r["tau2_upper"]),
            STATUS.get(r["status"], r["status"])])
    caption = ["Heterogeneity statistics for the ", ("i", "k"),
               " collections of each stratum that meets the minimum condition, ",
               SP, ", pooled proportions of antifungal resistance"]
    notes = [
        ("1", [("i", "Q"), " and ", ("i", "I"), chr(178),
               " are computed with the inverse-variance formulation and are therefore not "
               "statistics of the fitted binomial-normal generalised linear mixed model. They are "
               "reported for comparability with the published literature. The quantity estimated "
               "by the model is ", ("i", chr(964)), chr(178),
               ", and the prediction interval derived from it is what the text interprets."]),
        ("2", [("i", chr(964)), chr(178), " is estimated by maximum likelihood on the logit scale, "
               "with a 95 % confidence interval from the profile likelihood."]),
        ("3", "A stratum meets the minimum condition with at least five independent collections "
              "from at least two research groups. Strata below it are listed in Table S2."),
        ("4", "CI, confidence interval; CLSI, Clinical and Laboratory Standards Institute; "
              "ECV, epidemiological cut-off value; EUCAST, European Committee on Antimicrobial "
              "Susceptibility Testing."),
    ]
    write_table(p_xlsx, "Table S1", "S1", caption, headers, widths, [(None, rows)], notes)
    mirror(p_csv, headers, rows)
    return len(rows)


def table_s2(stt, res, p_xlsx, p_csv):
    est = {(r["compartment"], r["agent"], r["outcome"], r["regime_stratum"]): r for r in res}
    headers = ["Compartment", "Agent", "Outcome and interpretive criterion",
               [("i", "k"), " collections"], "Research groups", "Reports",
               "Events/isolates", "Crude proportion, %", "Largest collection, %",
               "Rows flagged (SX1)", "Meets minimum condition", "Model status"]
    widths = [12, 15, 28, 9, 9, 8, 13, 10, 10, 9, 10, 26]
    rows = []
    for r in sorted(stt, key=order):
        k = (r["compartment"], r["agent"], r["outcome"], r["regime_stratum"])
        e = est.get(k)
        rows.append([
            COMPART.get(r["compartment"], r["compartment"]), r["agent"],
            f"{OUTCOME.get(r['outcome'], r['outcome'])}, {crit(r)}",
            ent(r["k_collections"]), ent(r["research_groups"]), ent(r["k_reports_all"]),
            f"{ent(r['events'])}/{ent(r['isolates'])}",
            pct(float(r["events"]) / float(r["isolates"])) if float(r["isolates"] or 0) else DASH,
            dec(r["largest_collection_pct"], 1), ent(r["flagged_main_rows"]),
            si_no(r["meets_minimum"]),
            STATUS.get(e["status"], e["status"]) if e
            else "Below minimum condition (AR12): not estimated"])
    caption = ["Full inventory of the strata defined by compartment, agent, outcome and "
               "interpretive criterion, ", SP]
    notes = [
        ("1", "A stratum meets the minimum condition with at least five independent collections "
              "from at least two research groups (AR12). Strata below it are not estimated and "
              "are described in the text."),
        ("2", "A collection is the set of reports from the same institution or programme and "
              "country whose collection periods overlap (AR1), plus the pairs that the round-2 "
              "verification declared to be the same collection. Within a stratum only the report "
              "with the largest number of isolates tested against the agent enters (AR2)."),
        ("3", "Rows flagged are those whose criterion version was inferred (from the publication year or "
              "from the declared breakpoints) or whose pre-2012 CLSI document was cited in a report published "
              "in 2013 or later. Sensitivity analysis SX1 excludes them."),
        ("4", "Research groups are approximated by the declared institution (AR13)."),
    ]
    write_table(p_xlsx, "Table S2", "S2", caption, headers, widths, [(None, rows)], notes)
    mirror(p_csv, headers, rows)
    return len(rows)


def table_s3(stt, res, ma, p_xlsx, p_csv):
    est = {(r["compartment"], r["agent"], r["outcome"], r["regime_stratum"]): r for r in res}
    nc = [r for r in stt if r["compartment"] != "C1"]
    headers = ["Compartment", "Agent", "Outcome and interpretive criterion",
               [("i", "k"), " collections"], "Research groups", "Events/isolates",
               "Crude proportion, %", "Range across collections, %",
               "Exact binomial 95% CI of the total, %", "Model status"]
    widths = [26, 15, 28, 9, 9, 13, 10, 12, 13, 24]
    blocks = []
    for c in sorted({r["compartment"] for r in nc}):
        rows = []
        for r in sorted([x for x in nc if x["compartment"] == c], key=order):
            k = (r["compartment"], r["agent"], r["outcome"], r["regime_stratum"])
            e = est.get(k)
            lo, hi = exact(ma, k)
            rows.append([
                COMPART.get(c, c), r["agent"],
                f"{OUTCOME.get(r['outcome'], r['outcome'])}, {crit(r)}",
                ent(r["k_collections"]), ent(r["research_groups"]),
                f"{ent(r['events'])}/{ent(r['isolates'])}",
                pct(float(r["events"]) / float(r["isolates"]))
                if float(r["isolates"] or 0) else DASH,
                range_(ma, k),
                pct_range(lo, hi) if lo is not None else DASH,
                STATUS.get(e["status"], e["status"]) if e
                else "Below minimum condition (AR12): not estimated"])
        blocks.append((COMPART.get(c, c), rows))
    caption = ["Strata of the non-clinical compartments C2 to C6, ", SP,
               ", with the quantities reported when a stratum is not pooled"]
    nwt2 = sum(1 for r in nc if r["outcome"] == "NWT" and int(float(r["k_collections"])) >= 2)
    notes = [
        ("1", f"Non-clinical strata of the primary outcome (non-wild-type by epidemiological cut-off value) "
              f"with at least two independent collections: {nwt2}."),
        ("2", "When a stratum is not pooled, AR18 requires reporting the number of collections, "
              "research groups, events and isolates, the crude proportion, the range across "
              "collections and the exact binomial interval of the total, which is what this table "
              "gives. The exact interval treats the total as a single sample and therefore "
              "ignores clustering by collection; it is a descriptive bound, not an estimate of "
              "the population proportion."),
        ("3", "CI, confidence interval."),
    ]
    write_table(p_xlsx, "Table S3", "S3", caption, headers, widths, blocks, notes)
    mirror(p_csv, headers, [f for _, fs in blocks for f in fs])
    return sum(len(fs) for _, fs in blocks)


def rows_of(ma, k):
    c, a, o, reg = k
    return [r for r in ma if r["compartment"] == c and r["agent"] == a and r["outcome"] == o
            and r["regime_stratum"] == reg and r["main"] == "True"]


def range_(ma, k):
    f = rows_of(ma, k)
    if not f:
        return DASH
    ps = [float(x["events"]) / float(x["n_tested"]) for x in f if float(x["n_tested"] or 0)]
    return DASH if not ps else pct_range(min(ps), max(ps))


def exact(ma, k):
    """Clopper-Pearson on the total of the stratum, without dependencies: bisection on the
    cumulative binomial computed with the regularised incomplete beta by continued
    fraction. It is the interval that AR18 requires to report when there is no pooling."""
    f = rows_of(ma, k)
    if not f:
        return None, None
    x = int(sum(float(r["events"]) for r in f))
    n = int(sum(float(r["n_tested"]) for r in f))
    if n == 0:
        return None, None
    return cp_lo(x, n), cp_hi(x, n)


def betainc(a, b, x):
    """I_x(a,b) by Lentz's continued fraction, as in Numerical Recipes."""
    import math
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lb = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
          + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return math.exp(lb) * betacf(a, b, x) / a
    return 1 - math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                        + b * math.log(1 - x) + a * math.log(x)) * betacf(b, a, 1 - x) / b


def betacf(a, b, x, itmax=200, eps=3e-16, fpmin=1e-300):
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1 / d
        de = d * c
        h *= de
        if abs(de - 1) < eps:
            break
    return h


def _root(f, lo=0.0, hi=1.0, it=120):
    """Bisection on f increasing in p: the regularised incomplete beta is."""
    for _ in range(it):
        mid = (lo + hi) / 2
        if f(mid) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def cp_lo(x, n, alpha=0.05):
    """Lower Clopper-Pearson limit: alpha/2 quantile of Beta(x, n-x+1)."""
    if x == 0:
        return 0.0
    return _root(lambda p: betainc(x, n - x + 1, p) - alpha / 2)


def cp_hi(x, n, alpha=0.05):
    """Upper Clopper-Pearson limit: 1-alpha/2 quantile of Beta(x+1, n-x)."""
    if x == n:
        return 1.0
    return _root(lambda p: betainc(x + 1, n - x, p) - (1 - alpha / 2))


def main():
    check = "--check" in sys.argv[1:]
    prov = N.mode()
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    p_res, p_str = N.inputs(prov)
    p_ma = p_str.replace("ma_strata_v2_", "ma_input_v2_")
    if not os.path.exists(p_ma):
        sys.exit(f"Missing {p_ma}")
    res, stt, ma = leer(p_res), leer(p_str), leer(p_ma)
    print(f"ma_results {os.path.basename(p_res)}: {len(res)} strata estimated")
    print(f"ma_strata  {os.path.basename(p_str)}: {len(stt)} strata in total")
    nmin = sum(1 for r in stt if si_no(r["meets_minimum"]) == "Yes")
    print(f"  meet the minimum condition AR12: {nmin}")
    print(f"  non-clinical (C2 to C6): {sum(1 for r in stt if r['compartment'] != 'C1')}")
    faltan = [(r['compartment'], r['agent'], r['outcome'], r['regime_stratum']) for r in stt
              if si_no(r["meets_minimum"]) == "Yes"
              and (r["compartment"], r["agent"], r["outcome"], r["regime_stratum"])
              not in {(x["compartment"], x["agent"], x["outcome"], x["regime_stratum"])
                      for x in res}]
    if faltan:
        sys.exit(f"Strata that meet AR12 and are not in ma_results: {faltan[:5]}")
    # check of the exact interval against a known case: 1 of 10, Clopper-Pearson
    lo, hi = cp_lo(1, 10), cp_hi(1, 10)
    if not (abs(lo - 0.00252858) < 1e-6 and abs(hi - 0.44501612) < 1e-6):
        sys.exit(f"The exact interval does not reproduce the test case 1/10: {lo:.8f}, {hi:.8f}")
    print(f"  exact interval, test case 1/10: {100 * lo:.4f} a {100 * hi:.4f} %  ok")
    if check:
        print("\n--check: nothing was written.")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S") + ("_PROVISIONAL" if prov else "")
    outputs, counts_ = {}, {}
    plan = [("tabS01_heterogeneity", lambda a, b: table_s1(res, a, b)),
            ("tabS02_strata_inventory", lambda a, b: table_s2(stt, res, a, b)),
            ("tabS03_nonclinical_strata", lambda a, b: table_s3(stt, res, ma, a, b))]
    for name, fn in plan:
        px = os.path.join(OUT_DIR, f"{name}_v2_{stamp}.xlsx")
        pc = os.path.join(OUT_DIR, f"{name}_v2_{stamp}.csv")
        for p in (px, pc):
            if os.path.exists(p):
                sys.exit(f"Already exists {p}")
        counts_[name] = fn(px, pc)
        outputs[px] = md5(px)
        outputs[pc] = md5(pc)
        print(f"  {name}: {counts_[name]} rows")
    log = {"script": os.path.basename(__file__), "mode": "PROVISIONAL" if prov else "FINAL",
           "run_time": datetime.now().astimezone().isoformat(timespec="seconds"),
           "inputs": {p: md5(p) for p in (p_res, p_str, p_ma)},
           "rows_per_table": counts_, "md5_outputs": outputs}
    p_log = os.path.join(LOG_DIR, f"tabS_supplementary_v2_{stamp}.json")
    with open(p_log, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=1, ensure_ascii=False)
    print(f"\n{OUT_DIR}\n{p_log}")


if __name__ == "__main__":
    main()
