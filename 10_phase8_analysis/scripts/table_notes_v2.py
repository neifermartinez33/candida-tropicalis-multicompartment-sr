"""table_notes_v2.py (2026-10-24)

Footnotes and common utilities of Tables 3 and 4 in their version 2 (rules
analysis_rules_v4_2026-10-24.md). They correct the v1 notes that the audit of 2026-10-24 found
inaccurate: the CI of the median is not Hartung-Knapp but t with k-1 degrees of freedom on the standard
error of the GLMM (what meta calls "HK" in a GLMM); the prediction interval is that of Higgins,
Thompson and Spiegelhalter with t on k-2 (meta: "HTS"), not Hartung-Knapp-Sidik-Jonkman; and the exact
binomial interval of the non-pooled strata goes in the table, not "in the text". The format is still that
of table_helpers.py.
"""
import csv
import glob
import json
import math
import os
import sys

import table_helpers as T

RES = "10_phase8_analysis/results"
KEY = ("compartment", "agent", "outcome", "regime_stratum")
NOT_POOLED = {"not_pooled_boundary_AR18a": "6", "not_pooled_tau2_AR18b": "7", "not_pooled_no_profile_AR18c": "7",
              "below_minimum": "8"}
FLAG = "9"


def mode():
    return "--provisional" in sys.argv[1:]


def newest(pat, provisional):
    f = sorted(x for x in glob.glob(os.path.join(RES, pat)) if x.endswith("_PROVISIONAL.csv") == provisional)
    if not f:
        sys.exit(f"There is no {pat}" + (" PROVISIONAL" if provisional else " FINAL"))
    return f[-1]


def inputs(provisional):
    """ma_results_v3 and the strata summary of the same input (checked through the R log)."""
    f_res = newest("ma_results_v3_*.csv", provisional)
    stamp = os.path.basename(f_res)[len("ma_results_v3_"):-4]
    lg = os.path.join(RES, "logs", f"06_ma_marginal_v3_{stamp}.json")
    if not os.path.exists(lg):
        sys.exit(f"The log is missing for {f_res}")
    ins = json.load(open(lg, encoding="utf-8"))["inputs"]
    f_st = [p for p in ins if os.path.basename(p).startswith("ma_strata_v2_")]
    if len(f_st) != 1 or not os.path.exists(f_st[0]):
        sys.exit("The log of ma_results_v3 does not identify its ma_strata_v2")
    return f_res, f_st[0]


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def key_of(r):
    return tuple(r[k] for k in KEY)


def _logpmf(k, n, p):
    if p <= 0:
        return 0.0 if k == 0 else float("-inf")
    if p >= 1:
        return 0.0 if k == n else float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p)


def _cdf(k, n, p):
    return sum(math.exp(_logpmf(i, n, p)) for i in range(0, k + 1))


def exact_ci(k, n, a=0.05):
    """Exact Clopper-Pearson binomial CI, by bisection (without scipy)."""
    def solve(f, lo=0.0, hi=1.0):
        for _ in range(80):
            mid = (lo + hi) / 2
            if f(mid):
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else solve(lambda p: 1 - _cdf(k - 1, n, p) < a / 2)
    upper = 1.0 if k == n else solve(lambda p: _cdf(k, n, p) > a / 2)
    return lower, upper


def crude_exact(r):
    """Crude proportion; with an exact binomial CI when the stratum is not pooled."""
    return T.pct_ci(r["p_crude"], r["exact_lower"], r["exact_upper"])


def model_cells(r):
    if r["status"] != "pooled":
        return [T.DASH] * 4
    return [T.pct_ci(r["p_marginal"], r["marg_lower"], r["marg_upper"]),
            T.pct_ci(r["p_median"], r["med_lower"], r["med_upper"]),
            T.pct_range(r["pi_lower"], r["pi_upper"]),
            T.tau_ci(r["tau2"], r["tau2_lower"], r["tau2_upper"])]


def footnotes(provisional, extra):
    notes = [
        ("1", "Pooled mean: population-averaged proportion of the binomial-normal generalised linear mixed model with a "
              "random intercept per independent collection (adaptive Gauss-Hermite quadrature, 7 points), obtained by "
              "integrating the random effect; 95% CI by parametric bootstrap percentile with 999 replicates."),
        ("2", "Median: pooled logit back-transformed, the median of the modelled distribution of true proportions; 95% CI "
              "from the model standard error with *t* on *k* " + T.EN + " 1 degrees of freedom. It falls below the mean "
              "when heterogeneity is large."),
        ("3", "Crude: total events divided by total isolates tested; it weights collections by size, whereas the model "
              "weights collections equally. For strata that are not pooled, the exact binomial 95% CI of the total is "
              "given in parentheses."),
        ("4", "Prediction interval of Higgins, Thompson and Spiegelhalter, *t* on *k* " + T.EN + " 2 degrees of freedom. It "
              "is the quantity interpreted for consistency, not " + T.I2 + "."),
        ("5", "*k*: independent collections after resolving overlapping reports; in parentheses, distinct research "
              "groups. A stratum is pooled only with at least 5 collections from at least 2 groups."),
        ("6", "No event in any collection, or every isolate resistant: the model has no maximum likelihood estimate and "
              "the stratum is not pooled."),
        ("7", "Between-collection variance " + T.TAU2 + " not identified: the upper limit of its profile likelihood "
              "interval exceeds 25, or the profile could not be obtained. Not pooled."),
        ("8", "Below the minimum condition: fewer than 5 independent collections or fewer than 2 research groups. Not "
              "pooled; described from its collections."),
        (FLAG, "Stratum includes collections whose criterion version was inferred (from the publication year or from the "
               "declared breakpoints) or whose pre-2012 CLSI document was cited in a report published in 2013 or later; "
               "sensitivity analysis SX1 removes them."),
        ("10", "Interpretive criteria: CLSI species-specific, breakpoints of M27-S4 and later documents; CLSI pre-2012, "
               "M27-A to M27-S3 and M44-A to M44-S3; the two are never pooled. CLSI species-specific and EUCAST are "
               "pooled only for fluconazole, where the resistance threshold coincides at 8 mg/L. A resistance row enters "
               "only when the document or version applied published a clinical breakpoint for *C. tropicalis* and that "
               "agent; for the CLSI pre-2012 echinocandin criterion, which had only a susceptible category, no "
               "resistance stratum is formed."),
        ("11", "Excluded before pooling: categories without a declared criterion version and without MIC data (protocol "
               "rule 4), and rows that do not estimate prevalence (phenotype-selected samples, inferred denominators, "
               "compiled datasets), which sensitivity analysis SX3 re-includes."),
        ("12", "Heterogeneity test and " + T.I2 + " are reported in the supplementary material: the package computes "
               "them from the inverse-variance formulation, not from the mixed model."),
    ]
    notes += extra
    if provisional:
        notes.append(("P", "PROVISIONAL: round-2 verification decisions pending; not for the manuscript."))
    return notes
