#!/usr/bin/env python3
"""11_tabS_sensitivity_v2.py (2026-10-24)

Tables S4 and S5 of the supplementary material with the outputs of 09a_sens_refit_v3.R and 09b_sens_contrast_v3.R
(rules analysis_rules_v4_2026-10-24.md), in the style of Tables 3 and 4.

  S4  Refit family: SA1, SA2, SA3, SA9, SA10a, SA10b, SA11, SX1, SX2 and SX3. One row per analysis and
      stratum, with the comparator that corresponds to each estimator and the difference in percentage points.
  S5  Contrast family (AR19): SA4_R, SA4_NWT, SA5, SA7 and SA8. Logit contrast and difference in population
      means, always both.

Changes from v1:
  1. Correct comparator by estimator. SA10a and SA10b return the back-transformed pooled value, which is
     a median-type quantity: it is compared with the median of the main analysis (v1 subtracted it from the population
     mean). SA11 is compared with the one-level model fitted with the same Laplace approximation.
     The others (GLMM) compare population mean with population mean.
  2. The strata of the main analysis that do not reach AR12 in a subset appear with that status.
  3. In S5, a contrast is only reported with status "estimated": if a level does not meet AR18 there are no figures.
  4. Checks that the two R outputs were computed on the same input as ma_results_v3 (R logs).
  5. --provisional mode.
SA10b: the Freeman-Tukey back-transformation returns exactly zero when the pooled value falls
below the floor of the inverse at the harmonic mean of the n; it is not an estimate of zero (Schwarzer et al.,
Res Synth Methods 2019;10:476-483). Those cells appear as not estimable under the transformation.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/11_tabS_sensitivity_v2.py --check [--provisional]
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/11_tabS_sensitivity_v2.py [--provisional]
Outputs (never overwritten):
  12_documents/supplementary/tables/tabS04_sensitivity_refit_v2_<date-time>[_PROVISIONAL].xlsx and .csv
  12_documents/supplementary/tables/tabS05_sensitivity_contrast_v2_<date-time>[_PROVISIONAL].xlsx and .csv
  10_phase8_analysis/results/logs/tabS_sensitivity_v2_<date-time>.json
"""
import csv
import json
import os
import platform
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table_helpers as T  # noqa: E402
import table_notes_v2 as N  # noqa: E402

OUT_DIR = "12_documents/supplementary/tables"
LOG_DIR = os.path.join(N.RES, "logs")
RULES = "10_phase8_analysis/analysis_rules_v4_2026-10-24.md"
SP = ("i", "C. tropicalis")

ORDER_S4 = ["SA1", "SA2", "SA3", "SA9", "SA10a", "SA10b", "SA11", "SX1", "SX2", "SX3"]
ETIQ = {
    "SA1": "Compartment C5 in its broad reading",
    "SA2": "Preprints excluded",
    "SA3": "Each report as an independent unit",
    "SA9": "Collections whose index report is at high risk of bias excluded",
    "SA10a": "Logit transformation, inverse variance, continuity correction of 0.5",
    "SA10b": "Freeman-Tukey double arcsine transformation, inverse variance",
    "SA11": "Collections nested within country",
    "SX1": "Rows with an inferred criterion version excluded (not prespecified)",
    "SX2": "Rows with an assumed breakpoint type excluded (not prespecified)",
    "SX3": "Rows that do not estimate prevalence re-included (not prespecified)",
    "SA4_R": "CLSI species-specific versus EUCAST, resistance by clinical breakpoint",
    "SA4_NWT": "CLSI versus EUCAST epidemiological cut-off value, non-wild-type",
    "SA5": "Non-wild-type by ECV versus resistance by clinical breakpoint, paired within collection",
    "SA7": "CLSI species-specific versus CLSI pre-2012, resistance by clinical breakpoint",
    "SA8": "Molecular or MALDI-TOF versus phenotypic species identification",
}
ORDER_S5 = ["SA4_R", "SA4_NWT", "SA7", "SA8", "SA5"]
LEVEL = {"CLSI_SS": "CLSI species-specific", "EUCAST": "EUCAST", "ECV_CLSI": "CLSI ECV",
         "ECV_EUCAST": "EUCAST ECV", "CLSI_pre2012": "CLSI pre-2012", "molecular": "Molecular or MALDI-TOF",
         "phenotypic": "Phenotypic", "NWT": "Non-wild-type (ECV)", "R": "Resistant (clinical breakpoint)"}
OUT_SHORT = {"NWT": "Non-wild-type", "R": "Resistant"}
STATUS_S4 = {
    "pooled": "Pooled",
    "estimated_alternative_estimator": "Estimated",
    "not_pooled_boundary_AR18a": "Not pooled: no event, or every isolate an event",
    "not_pooled_tau2_AR18b": "Not pooled: " + T.plain(T.TAU2) + " not identified",
    "not_pooled_no_profile_AR18c": "Not pooled: profile interval for " + T.plain(T.TAU2) + " not obtained",
    "below_AR12_in_subset": "Below the minimum condition in this subset",
    "no_fit": "Model did not converge",
    "fit_error": "Fit failed",
    "no_strata_meeting_AR12": "No stratum meets the minimum condition",
}
MAIN_STATUS = {"not_pooled_boundary_AR18a": "no event or every isolate an event",
               "not_pooled_tau2_AR18b": T.plain(T.TAU2) + " not identified",
               "not_pooled_no_profile_AR18c": "profile for " + T.plain(T.TAU2) + " not obtained",
               "not_estimable_in_main": "stratum not formed"}
STATUS_S5 = {
    "estimated": "Estimated",
    "level_not_poolable_AR18": "Not estimable: " + T.plain(T.TAU2) + " not identified in a level",
    "level_below_AR12": "Not estimable: a level below the minimum condition",
    "boundary_no_estimator": "Not estimable: a level with no event or every isolate an event",
    "no_fit": "Model did not converge",
    "fit_error": "Fit failed",
    "no_cells": "No cell with both levels",
}
POOLED_LIKE = {"pooled", "estimated_alternative_estimator"}


def num(v):
    if T.miss(v):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def ent(v):
    x = num(v)
    return T.DASH if x is None else f"{int(round(x)):,}"


def pval(v):
    x = num(v)
    if x is None:
        return T.DASH
    return f"{x:.3f}" if x >= 0.001 else "<0.001"


def newest(pat, prov):
    return N.newest(pat, prov)


LOG_OF = {"ma_sensitivity_refit_v3": "09a_sens_refit_v3", "ma_sensitivity_contrast_v3": "09b_sens_contrast_v3"}


def r_log(prefix, out_path):
    stamp = os.path.basename(out_path)[len(prefix) + 1:-4]
    lg = os.path.join(LOG_DIR, f"{LOG_OF[prefix]}_{stamp}.json")
    if not os.path.exists(lg):
        sys.exit(f"The log is missing for {out_path}: {lg}")
    return json.load(open(lg, encoding="utf-8"))


def same_input(f_res, f_refit, f_contr):
    """The two R outputs must come from the same input as the ma_results_v3 of the tables."""
    stamp = os.path.basename(f_res)[len("ma_results_v3_"):-4]
    lg06 = json.load(open(os.path.join(LOG_DIR, f"06_ma_marginal_v3_{stamp}.json"), encoding="utf-8"))
    f_in = [p for p in lg06["inputs"] if os.path.basename(p).startswith("ma_input_v2_")]
    if len(f_in) != 1:
        sys.exit("The log of ma_results_v3 does not identify its ma_input_v2")
    f_in = f_in[0]
    problems = []
    if f_refit:
        ins = r_log("ma_sensitivity_refit_v3", f_refit)["inputs"]
        if f_in not in ins:
            problems.append(f"{os.path.basename(f_refit)} was not computed on {os.path.basename(f_in)}")
        if f_res not in ins:
            problems.append(f"{os.path.basename(f_refit)} was not compared with {os.path.basename(f_res)}")
    if f_contr:
        ins = r_log("ma_sensitivity_contrast_v3", f_contr)["inputs"]
        if f_in not in ins:
            problems.append(f"{os.path.basename(f_contr)} was not computed on {os.path.basename(f_in)}")
    if problems:
        sys.exit("Misaligned inputs:\n  " + "\n  ".join(problems) + "\nRun 09a and 09b again after 06.")
    return f_in


# ---------------------------------------------------------------------------------------------- S4

def comparator(a, r):
    """(comparator value, difference) according to the estimator of the analysis."""
    if a in ("SA10a", "SA10b"):
        return num(r.get("main_median")), num(r.get("delta_median"))
    if a == "SA11":
        return num(r.get("p_ref_laplace")), num(r.get("delta_p_vs_laplace"))
    return num(r.get("main_p")), num(r.get("delta_p"))


def table_s4(refit, prov, p_xlsx, p_csv):
    headers = ["Compartment", "Agent", "Outcome and interpretive criterion", "*k* units (groups)",
               "Estimate, % (95% CI)", "Comparator, %", "Difference, percentage points", T.TAU2, "Status"]
    widths = [11, 14, 26, 10, 18, 11, 12, 8, 34]
    blocks, count_ = [], Counter()
    names = [a for a in ORDER_S4 if a in {r["analysis"] for r in refit}]
    names += sorted({r["analysis"] for r in refit} - set(names))
    for a in names:
        rows = []
        rs = sorted([r for r in refit if r["analysis"] == a],
                    key=lambda r: (r.get("compartment") or "", r.get("outcome") or "", r.get("agent") or "",
                                   r.get("regime_stratum") or ""))
        for r in rs:
            if r["status"] == "no_strata_meeting_AR12" or T.miss(r.get("compartment")):
                rows.append([T.DASH] * 8 + [STATUS_S4.get(r["status"], r["status"])])
                count_["no_strata"] += 1
                continue
            pt, lo, hi = num(r["p_point"]), num(r["p_lower"]), num(r["p_upper"])
            est = STATUS_S4.get(r["status"], r["status"])
            ms = r.get("main_status") or ""
            comp, diff = comparator(a, r)
            flag = None
            zero_ft = a == "SA10b" and pt is not None and pt == 0.0
            if zero_ft:
                pt = lo = hi = None
                est = "Not estimable under this transformation"
                flag = "1"
                count_["SA10b_zero"] += 1
            if r["status"] in POOLED_LIKE and ms != "pooled":
                est += f"; not pooled in the main analysis ({MAIN_STATUS.get(ms, ms)})"
                flag = flag or "4"
                count_["not_pooled_in_main"] += 1
            if r["status"] not in POOLED_LIKE:   # not pooled, below AR12 or not fitted: no figure
                pt = lo = hi = None
            est_txt = T.pct_ci(pt, lo, hi, 2) if pt is not None else T.DASH
            ok_diff = r["status"] in POOLED_LIKE and ms == "pooled" and not zero_ft and diff is not None
            tau = T.DASH if a == "SA10b" else T.tau_ci(r.get("tau2"), r.get("tau2_lower"), r.get("tau2_upper"))
            rows.append([
                r["compartment"], r["agent"][0].upper() + r["agent"][1:],
                f"{OUT_SHORT.get(r['outcome'], r['outcome'])}, {T.CRITERION.get(r['regime_stratum'], r['regime_stratum'])}",
                f"{ent(r['k_units'])} ({ent(r['research_groups'])})",
                (est_txt, flag) if flag else est_txt,
                T.pct(comp, 2) if (comp is not None and ms == "pooled" and pt is not None) else T.DASH,
                (("0.00" if abs(100 * diff) < 0.005 else f"{100 * diff:+.2f}") if ok_diff else T.DASH),
                tau, est])
            count_[a] += 1
        blocks.append((f"{a}. {ETIQ.get(a, a)}", rows))
    cap = ([("i", "[PROVISIONAL] ")] if prov else []) + [
        "Sensitivity analyses of the refitting family, one row per analysis and stratum, ", SP,
        ". Each analysis changes one decision and re-applies the minimum condition and the non-pooling rule"]
    notes = [
        ("1", "The inverse of the Freeman-Tukey double arcsine transformation returns exactly zero when the pooled value "
              "on the transformed scale falls below the floor of the back-transformation evaluated at the harmonic mean "
              "of the sample sizes; there is no valid inverse there, so the cell is reported as not estimable and never "
              "as 0.00 % (Schwarzer et al., Research Synthesis Methods 2019;10:476-483)."),
        ("2", "Comparator. For the generalised linear mixed model analyses, the population-averaged mean of the main "
              "analysis. For SA10a and SA10b, whose back-transformed pooled value is a median-type quantity, the median "
              "of the main analysis. For SA11, the single-level model refitted with the same Laplace approximation, so "
              "that the difference isolates the nesting from the approximation. The difference is given only when both "
              "the analysis and the main analysis pool the stratum."),
        ("3", "Subsets that remove rows (SA2, SX1, SX2, SX3 and SA1) recompute the choice of one report per collection "
              "and stratum, so a collection whose index report leaves is represented by its next report. SA9 removes "
              "the collections whose index report is at high risk of bias, as registered."),
        ("4", "Stratum not pooled in the main analysis. The estimate of the alternative estimator is shown for "
              "transparency; the inverse-variance path has no profile likelihood for " + T.plain(T.TAU2) +
              " and the nested model splits it across two levels, so the non-pooling rule cannot be re-applied, and "
              "their willingness to pool does not show that the between-collection variance is identified."),
        ("5", T.plain(T.TAU2) + ": between-collection variance on the logit scale, with its profile likelihood 95% "
              "interval where computed; for SA11, the sum of the between-country and between-collection variances; "
              "for SA10b it is on the arcsine scale and not shown."),
        ("6", "SX1, SX2 and SX3 were not prespecified and are declared as deviations. CI, confidence interval; CLSI, "
              "Clinical and Laboratory Standards Institute; ECV, epidemiological cut-off value; EUCAST, European "
              "Committee on Antimicrobial Susceptibility Testing."),
    ]
    if prov:
        notes.append(("P", "PROVISIONAL: round-2 verification decisions pending; not for the manuscript."))
    T.write_table(p_xlsx, "Table S4", "S4", cap, headers, widths, blocks, notes)
    with open(p_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["block"] + [T.plain(h) for h in headers])
        for lab, rows in blocks:
            for row in rows:
                w.writerow([lab] + [T.plain(c[0] if isinstance(c, tuple) else c) for c in row])
    return sum(len(f) for _, f in blocks), count_


# ---------------------------------------------------------------------------------------------- S5

def cell_txt(r):
    parts = r["cell"].split(" | ")
    if r["analysis"] == "SA8" and len(parts) == 4:
        c, ag, oc, rs = parts
        return f"{c} | {ag} | {OUT_SHORT.get(oc, oc)}, {T.CRITERION.get(rs, rs)}"
    return " | ".join(parts)


def table_s5(contr, prov, p_xlsx, p_csv):
    headers = ["Cell", "Level A", "Level B", "*k* A / B", "Crude A / B, %", "Logit contrast, A " + T.EN + " B (95% CI)",
               "*P*", "Difference of population means, A " + T.EN + " B, percentage points (95% CI)",
               T.TAU2 + " A / B", "Status"]
    widths = [30, 16, 16, 9, 13, 19, 7, 21, 11, 30]
    blocks, count_, omitted = [], Counter(), Counter()
    names = [a for a in ORDER_S5 if a in {r["analysis"] for r in contr}]
    names += sorted({r["analysis"] for r in contr} - set(names))
    for a in names:
        rows = []
        for r in sorted([x for x in contr if x["analysis"] == a], key=lambda x: x.get("cell") or ""):
            if r["status"] == "no_cells":
                rows.append([T.DASH] * 9 + [STATUS_S5["no_cells"]])
                continue
            ka, kb = num(r["k_a"]) or 0, num(r["k_b"]) or 0
            if ka < 1 or kb < 1:
                omitted[a] += 1
                continue
            est = r["status"] == "estimated"
            c, lo, hi = num(r["logit_contrast"]), num(r["logit_lo"]), num(r["logit_hi"])
            dm, dlo, dhi = num(r["diff_marg"]), num(r["diff_lo"]), num(r["diff_hi"])
            logit = T.DASH
            if est and c is not None:
                logit = f"{c:+.3f} ({lo:+.3f} to {hi:+.3f})" if lo is not None else f"{c:+.3f}"
            dif = T.DASH
            if est and dm is not None:
                dif = f"{100 * dm:+.2f} ({100 * dlo:+.2f} to {100 * dhi:+.2f})" if dlo is not None else f"{100 * dm:+.2f}"
            ca, cb = num(r["crude_a"]), num(r["crude_b"])
            kk = f"{ent(ka)} / {ent(kb)}"
            if a == "SA5" and num(r.get("k_pairs")) is not None:
                kk = f"{ent(r['k_pairs'])} pairs"
            ksh = num(r.get("k_shared"))
            if a != "SA5" and ksh:
                kk += f" ({ent(ksh)} in both)"
                count_["shared_cells"] += 1
                count_["shared_cells_estimated"] += int(est)
            ta, tb = num(r.get("tau2_a")), num(r.get("tau2_b"))
            tau = T.DASH
            if est and ta is not None:
                tau = f"{ta:.2f}" if a == "SA5" else f"{ta:.2f} / {tb:.2f}"
            rows.append([cell_txt(r), LEVEL.get(r["level_a"], r["level_a"]), LEVEL.get(r["level_b"], r["level_b"]),
                          kk, f"{T.pct(ca, 1)} / {T.pct(cb, 1)}", logit, pval(r["p_value"]) if est else T.DASH, dif, tau,
                          "Not estimable: shared " + T.plain(T.TAU2) + " not identified"
                          if (a == "SA5" and r["status"] == "level_not_poolable_AR18") else
                          STATUS_S5.get(r["status"], r["status"])])
            count_[a] += 1
            count_["estimated"] += int(est)
        blocks.append((f"{a}. {ETIQ.get(a, a)}", rows))
    cap = ([("i", "[PROVISIONAL] ")] if prov else []) + [
        "Contrasts between two levels of a factor, ", SP, ". Rule AR19 requires both quantities under distinct names: "
        "the contrast on the logit scale, which is the effect of the factor with the heterogeneity held apart, and the "
        "difference of population-averaged means from the same fits, which also carries the difference in "
        "heterogeneity"]
    om = "; ".join(f"{k} {v}" for k, v in sorted(omitted.items())) or "none"
    if count_["shared_cells"]:
        indep = (f"Rule AR19 assumes each collection belongs to one level; in {count_['shared_cells']} cells "
                 f"({count_['shared_cells_estimated']} estimated) some collections report both levels (column *k*, "
                 "\"in both\"). Their positive covariance is ignored, so for those cells the intervals below are "
                 "conservative. Each level is fitted")
    else:
        indep = "Each collection belongs to one level and each level is fitted"
    notes = [
        ("1", "A contrast is estimated only when each level meets the minimum condition (at least 5 collections from at "
              "least 2 research groups) and the non-pooling rule on its own; otherwise the cell is listed with its status "
              "and without figures. Cells where one level has no collection are not listed (" + om + ")."),
        ("2", "Unpaired contrasts (SA4, SA7, SA8): " + indep + " with its "
              "own binomial-normal model (adaptive Gauss-Hermite quadrature, 7 points); with independent levels this "
              "equals the joint model with level-specific variances. The standard error of the "
              "logit contrast is the root of the summed squared standard errors; the interval for the difference of "
              "population means comes from two independent parametric bootstraps of 999 replicates."),
        ("3", "Paired contrast (SA5): the same collections contribute to both levels, with one random intercept per "
              "collection shared by the two outcomes; the contrast is within collection, " + T.plain(T.TAU2) + " is "
              "shared and the non-pooling rule is applied to it; the interval for the difference comes from a parametric "
              "bootstrap of the paired model. *k*: collections with both outcomes."),
        ("4", "SA8 leaves out collections whose species identification method was not specified. SA7 compares the CLSI "
              "regimes row by row, so for fluconazole it includes the CLSI rows of the combined CLSI and EUCAST stratum."),
        ("5", "No contrast is obtained by subtracting rows of Tables 3 or 4. Wald 95% CI and *P* for the logit contrast; "
              "exploratory, without correction for multiplicity. CI, confidence interval; CLSI, Clinical and Laboratory "
              "Standards Institute; ECV, epidemiological cut-off value; EUCAST, European Committee on Antimicrobial "
              "Susceptibility Testing; MALDI-TOF, matrix-assisted laser desorption ionisation time-of-flight mass "
              "spectrometry."),
    ]
    if prov:
        notes.append(("P", "PROVISIONAL: round-2 verification decisions pending; not for the manuscript."))
    T.write_table(p_xlsx, "Table S5", "S5", cap, headers, widths, blocks, notes)
    with open(p_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["block"] + [T.plain(h) for h in headers])
        for lab, rows in blocks:
            for row in rows:
                w.writerow([lab] + [T.plain(c[0] if isinstance(c, tuple) else c) for c in row])
    return sum(len(f) for _, f in blocks), count_, omitted


def main():
    check = "--check" in sys.argv[1:]
    prov = N.mode()
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    if not os.path.exists(RULES):
        sys.exit(f"Missing {RULES}")
    f_res, _ = N.inputs(prov)
    f_refit = newest("ma_sensitivity_refit_v3_*.csv", prov)
    f_contr = newest("ma_sensitivity_contrast_v3_*.csv", prov)
    f_in = same_input(f_res, f_refit, f_contr)
    refit, contr = N.read(f_refit), N.read(f_contr)
    print(f"Input {os.path.basename(f_in)}\nRefit: {os.path.basename(f_refit)}  {len(refit)} rows, analyses "
          f"{', '.join(sorted({r['analysis'] for r in refit}))}")
    print(f"  statuses: {dict(Counter(r['status'] for r in refit))}")
    print(f"Contrasts: {os.path.basename(f_contr)}  {len(contr)} rows; statuses {dict(Counter(r['status'] for r in contr))}")
    falt = [r for r in contr if r["status"] == "estimated" and num(r.get("diff_marg")) is None]
    if falt:
        sys.exit(f"{len(falt)} contrasts estimated without a difference in population means: AR19 requires both quantities")
    if check:
        print("\n--check: nothing was written.")
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S") + ("_PROVISIONAL" if prov else "")
    p4x = os.path.join(OUT_DIR, f"tabS04_sensitivity_refit_v2_{stamp}.xlsx")
    p4c = os.path.join(OUT_DIR, f"tabS04_sensitivity_refit_v2_{stamp}.csv")
    p5x = os.path.join(OUT_DIR, f"tabS05_sensitivity_contrast_v2_{stamp}.xlsx")
    p5c = os.path.join(OUT_DIR, f"tabS05_sensitivity_contrast_v2_{stamp}.csv")
    for p in (p4x, p4c, p5x, p5c):
        if os.path.exists(p):
            sys.exit(f"Already exists {p}: not overwritten")
    n4, c4 = table_s4(refit, prov, p4x, p4c)
    n5, c5, om = table_s5(contr, prov, p5x, p5c)
    log = {"script": os.path.basename(__file__), "mode": "PROVISIONAL" if prov else "FINAL",
           "run_time": datetime.now().astimezone().isoformat(timespec="seconds"), "python": platform.python_version(),
           "inputs": {p: T.md5(p) for p in (RULES, f_res, f_in, f_refit, f_contr)},
           "outputs": {os.path.basename(p): T.md5(p) for p in (p4x, p4c, p5x, p5c)},
           "rows": {"tabS04": n4, "tabS05": n5}, "s4_counts": dict(c4), "s5_counts": dict(c5),
           "s5_cells_with_one_level_not_listed": dict(om)}
    p_log = os.path.join(LOG_DIR, f"tabS_sensitivity_v2_{stamp}.json")
    with open(p_log, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False)
    print(f"  tabS04: {n4} rows ({c4.get('SA10b_zero', 0)} SA10b not estimable; "
          f"{c4.get('not_pooled_in_main', 0)} not pooled in the main analysis)\n  tabS05: {n5} rows "
          f"({c5.get('estimated', 0)} contrasts estimated)\n{OUT_DIR}\n{p_log}")


if __name__ == "__main__":
    main()
