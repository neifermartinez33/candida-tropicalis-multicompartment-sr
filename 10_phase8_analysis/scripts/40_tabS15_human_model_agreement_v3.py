#!/usr/bin/env python3
"""40_tabS15_human_model_agreement_v3.py (2026-10-30)

v3 adds the re-reading of the exclusions (workbook B15), the two further runs of the model and the rows of workbook
B16; explains the difference between the full texts read and the reports assessed, and counts the reports of the
blind sample that contribute to a pooled stratum. v2 added one row: the study-level extraction of the model (compartments and number of C. tropicalis isolates)
compared with the values that the blind readers of the 20% sample recorded independently, in the reports that
both included. The other rows are unchanged from v1.

Table S15: human decisions and language-model proposals by stage of the review, with the agreement between the
model's proposal and the human decision wherever both exist. This script decides nothing: it counts the
decisions recorded in the deposited workbooks and reads the agreement statistics already computed by the chain.

Stages and sources
  deduplication                03_phase1_deduplication (adjudicated pairs and audits; Section 2.4)
  calibration, title/abstract  04_phase2_calibration/results, 06_phase4_title_abstract_screening/rayyan_exports
  full-text screening          07_phase5_full_text_screening/full_text_screening.xlsx (model proposals),
                               08_phase6_data_extraction/verification/round2_2026-10-24/r2_b08_* (blind sample)
  doubtful reports             07_phase5_full_text_screening/doubtful_review_2026-10-20
  extraction exclusions        round2_2026-10-24/r2_b09_extraction_exclusions.xlsx
  row verification             round2_2026-10-24/r2_b02_rows.xlsx, r2_b11_new_ast_rows.xlsx
  other verification books     round2_2026-10-24/r2_b03, b04, b05, b07 (proposal versus decision)
  risk of bias (RB8)           09_phase7_risk_of_bias (two human readers; Section 2.9)
Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/40_tabS15_human_model_agreement_v3.py
Outputs (never overwritten): 12_documents/supplementary/tables/tabS15_human_model_agreement_v3_<date-time>.xlsx and .csv;
log in 10_phase8_analysis/results/logs/40_tabS15_human_model_agreement_v3_<date-time>.json.
"""
import json
import math
import os
import re
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_log  # noqa: E402

R2 = "08_phase6_data_extraction/verification/round2_2026-10-24"
FT = "07_phase5_full_text_screening/full_text_screening.xlsx"
DOUBT = "07_phase5_full_text_screening/doubtful_review_2026-10-20/full_text_doubtful_review_2026-10-20.xlsx"
TA = "06_phase4_title_abstract_screening/rayyan_exports/screening_agreement_two_readers_20261028_223035.txt"
CAL = "04_phase2_calibration/results/calibration_kappa_CAL1_20261016_150217.txt"
MA_INPUT = sorted(f for f in os.listdir("10_phase8_analysis/results") if f.startswith("ma_input_v2_"))[-1]
MA_INPUT = "10_phase8_analysis/results/" + MA_INPUT
EXTRACTION = "08_phase6_data_extraction/data_extraction_tropicalis.xlsx"
MA_RESULTS = "10_phase8_analysis/results/" + sorted(f for f in os.listdir("10_phase8_analysis/results") if f.startswith("ma_results_v3_") and "PROVISIONAL" not in f)[-1]
PRISMA = "10_phase8_analysis/results/" + sorted(f for f in os.listdir("10_phase8_analysis/results") if f.startswith("prisma_counts_v3_") and f.endswith(".csv") and "PROVISIONAL" not in f)[-1]
B15 = "07_phase5_full_text_screening/rescreen_ast_2026-10-29/r4_b15_ast_exclusions_rescreen_v2.xlsx"
B16 = "08_phase6_data_extraction/verification/round4_2026-10-30/r4_b16_new_rows_v2.xlsx"
OUT_DIR = "12_documents/supplementary/tables"
INPUTS = [FT, DOUBT, TA, CAL, MA_INPUT, EXTRACTION, MA_RESULTS, PRISMA, B15, B16] + [f"{R2}/{b}" for b in (
    "r2_b08_agreement_2026-10-26T112820.json", "r2_b08_key.csv", "r2_b08_sample_blind.xlsx", "r2_b08b_arbitration.xlsx", "r2_b09_extraction_exclusions.xlsx",
    "r2_b02_rows.xlsx", "r2_b11_new_ast_rows.xlsx", "r2_b03_collection_pairs.xlsx", "r2_b04_ar20_rows.xlsx",
    "r2_b05_species_id.xlsx", "r2_b07_allocation_c5.xlsx")]

# Figures taken from the manuscript text that were verified against the phase files earlier in the chain; each carries
# its source so that it can be rechecked. They are not computed here because their inputs are not tabular.
DEDUP = dict(pairs_read=5236, audit_merged=200, audit_not_merged=1000, source="03_phase1_deduplication/adjudication; Section 2.4")
RB8 = dict(cal_n=199, cal_kappa="0.921 (0.878–0.964)", full_n=902, full_kappa="0.859 (0.833–0.885)",
           source="09_phase7_risk_of_bias/compute_rob_agreement.py outputs; Section 2.9")


def pct(k, n):
    return f"{100 * k / n:.1f}%"


def kappa_line(path, label):
    t = open(path, encoding="utf-8").read()
    m = re.search(r"kappa: ([0-9]\.[0-9]+)\. 95 ?% CI: ([0-9]\.[0-9]+) to ([0-9]\.[0-9]+)", t)
    if not m:
        sys.exit(f"kappa not found in {path} ({label})")
    return f"{float(m.group(1)):.3f} ({float(m.group(2)):.3f}–{float(m.group(3)):.3f})"


rows = []

# 1. Deduplication
rows.append(dict(stage="Deduplication", unit="Candidate pairs", model_role="Claude Sonnet 5 classified every candidate pair, independently of a deterministic algorithm",
                 human_decisions=DEDUP["pairs_read"], human_task="Two blinded reviewers adjudicated the pairs on which the two procedures disagreed, the pairs the model could not decide and the pairs between the algorithm thresholds",
                 agreement="Audits: no false merge in 200 merged pairs; no duplicate in 1000 pairs not proposed for merging",
                 outcome="Final merges as adjudicated", source=DEDUP["source"]))

# 2. Calibration and title/abstract screening (human only)
rows.append(dict(stage="Calibration of the screening manual", unit="Records", model_role="No model",
                 human_decisions=400, human_task="Two reviewers, 200 random records each, blinded",
                 agreement=f"Cohen's kappa {kappa_line(CAL, 'calibration')}", outcome="Manual frozen before screening",
                 source=CAL))
ta = open(TA, encoding="utf-8").read()
m = re.search(r"Observed agreement: ([0-9.]+) \((\d+) of (\d+)\)", ta)
rows.append(dict(stage="Title and abstract screening", unit="Records", model_role="No model (the safety net registered in the protocol was not used)",
                 human_decisions=2 * int(m.group(3)), human_task=f"Two reviewers screened all {int(m.group(3)):,} records independently and blinded in Rayyan; discrepancies resolved by consensus or a third reviewer",
                 agreement=f"Observed agreement {float(m.group(1)) * 100:.1f}% ({int(m.group(2)):,} of {int(m.group(3)):,}); Cohen's kappa {kappa_line(TA, 'title/abstract')}",
                 outcome="2096 discrepancies resolved", source=TA))

# 3. Full-text screening: model proposals and the blind sample
summ = pd.read_excel(FT, sheet_name="Summary", header=None)
sv = dict(zip(summ[0].astype(str), summ[1]))
n_ft = int(sv["Articles screened"])
props = f"INCLUDE {int(sv['INCLUDE'])}, EXCLUDE {int(sv['EXCLUDE'])}, DOUBTFUL {int(sv['DOUBTFUL'])}"
ag = json.load(open(f"{R2}/r2_b08_agreement_2026-10-26T112820.json"))
arb = pd.read_excel(f"{R2}/r2_b08b_arbitration.xlsx", sheet_name="arbitration", dtype=str)
key = pd.read_csv(f"{R2}/r2_b08_key.csv", dtype=str)
n_exc = int(key.stratum.str.startswith("EXCLUDE").sum())
n_inc = int(key.stratum.str.startswith("INCLUDED").sum())
changed = arb[arb.ft_decision != arb.arbiter_decision]
upheld = arb[arb.ft_decision == arb.arbiter_decision]
exc_to_inc = changed[(changed.ft_decision == "EXCLUDE") & (changed.arbiter_decision == "INCLUDE")]
inc_to_exc = changed[(changed.ft_decision == "INCLUDE") & (changed.arbiter_decision == "EXCLUDE")]
dbt_to_exc = changed[changed.ft_decision == "DOUBTFUL"]
STRATUM = ["compartment", "agent", "outcome", "regime_stratum"]
ma = pd.read_csv(MA_INPUT, low_memory=False)
ma = ma[ma["main"] == True].merge(pd.read_csv(MA_RESULTS).query("status == 'pooled'")[STRATUM], on=STRATUM)  # noqa: E712
pooled_reports = set(ma.study_id)
added_in_ma = len(set(exc_to_inc.study_id) & pooled_reports)
pr = pd.read_csv(PRISMA).query("box != 'other_methods'").set_index("item")["n"]
n_assessed = int(pr["assessed"])
later_nr = sum(int(pr[i]) for i in ("doubtful_not_retrieved", "extraction_not_retrieved", "verification_not_retrieved", "wrong_or_truncated", "rescreen_not_retrieved"))
assert n_ft - later_nr == n_assessed, (n_ft, later_nr, n_assessed)
no_ast = int((exc_to_inc.has_ast == "NO").sum())
assert ag["n"] == 822 and len(arb) == 65 and len(changed) == 57, (ag["n"], len(arb), len(changed))
rows.append(dict(stage="Full-text screening", unit="Reports", model_role=f"Claude Opus 5.5 read {n_ft} full texts and proposed a decision per criterion with verbatim evidence ({props}); {later_nr} of them were later recorded as not retrieved (doubtful reports, extraction, verification, wrong or truncated PDF, re-reading), which leaves {n_assessed} reports assessed",
                 human_decisions=ag["n"] + len(arb), human_task=f"Stratified random sample of 20% of the decisions ({ag['n']}: {n_exc} exclusions, {n_inc} inclusions not contributing to a pooled estimate) re-read by reviewers blinded to the previous decision; the {len(arb)} disagreements arbitrated by a third reviewer",
                 agreement=f"Blind reader versus model: observed agreement {ag['observed_agreement'] * 100:.1f}%, Cohen's kappa {ag['kappa']:.2f} ({ag['kappa_ci'][0]:.2f}–{ag['kappa_ci'][1]:.2f}); after arbitration {len(upheld)} model decisions upheld and {len(changed)} changed ({pct(len(changed), ag['n'])})",
                 outcome=f"{len(exc_to_inc)} of {n_exc} sampled exclusions ({pct(len(exc_to_inc), n_exc)}) became inclusions ({no_ast} without susceptibility testing) and entered the distribution analysis; {len(inc_to_exc)} of {n_inc} sampled inclusions ({pct(len(inc_to_exc), n_inc)}) and {len(dbt_to_exc)} report that the model had left as doubtful and the reviewers had included became exclusions; {added_in_ma} of the added reports contributed to a pooled stratum",
                 source=f"{FT}; {R2}/r2_b08_key.csv; r2_b08_agreement_2026-10-26T112820.json; r2_b08b_arbitration.xlsx"))

# 3 bis. Study-level extraction: model versus the blind readers (independent), reports included by both
def wilson(k, n, z=1.96):
    p = k / n
    den = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / den, (c + h) / den


blind = pd.read_excel(f"{R2}/r2_b08_sample_blind.xlsx", sheet_name="sample", dtype=str).merge(
    key[["study_id", "ft_decision"]], on="study_id")
both = blind[(blind.ft_decision == "INCLUDE") & blind.decision.str.upper().str.startswith("INCLU")]
ext = pd.read_excel(EXTRACTION, sheet_name="Studies", dtype=str).drop_duplicates("ID").set_index("ID")
both = both[both.study_id.isin(ext.index)]
comps = lambda v: frozenset(re.findall(r"C[1-6]", str(v if isinstance(v, str) else "")))  # noqa: E731
def count(v):
    m = re.search(r"\d+", str(v if isinstance(v, str) else "").replace(",", ""))
    return int(m.group(0)) if m else None
pairs = [(comps(ext.loc[r.study_id, "compartments"]), comps(r.compartments),
          count(ext.loc[r.study_id, "n_tropicalis_total"]), count(r.n_tropicalis)) for r in both.itertuples()]
pc = [(a, b) for a, b, _, _ in pairs if a and b]
pn = [(a, b) for _, _, a, b in pairs if a is not None and b is not None]
kc = sum(a == b for a, b in pc)
kn = sum(a == b for a, b in pn)
k10 = sum(abs(a - b) <= 0.10 * max(a, b) for a, b in pn)
lc, uc = wilson(kc, len(pc))
ln_, un = wilson(kn, len(pn))
rows.append(dict(stage="Data extraction: compartments and number of isolates", unit="Reports",
                 model_role="Claude Opus 5.5 extracted, for every included report, the compartments of recovery and the number of C. tropicalis isolates",
                 human_decisions=len(both), human_task=f"The blind readers of the 20% sample recorded both fields independently, without seeing the model's extraction; compared in the {len(both)} reports that the model and the blind reader both included",
                 agreement=f"Same compartments in {kc} of {len(pc)} ({pct(kc, len(pc))}; 95% CI {100 * lc:.1f}–{100 * uc:.1f}); same number of isolates in {kn} of {len(pn)} ({pct(kn, len(pn))}; 95% CI {100 * ln_:.1f}–{100 * un:.1f}), within 10% in {k10} ({pct(k10, len(pn))})",
                 outcome="Discrepant values resolved at arbitration or in the row verification",
                 source=f"{EXTRACTION} (sheet Studies); {R2}/r2_b08_sample_blind.xlsx; r2_b08_key.csv"))

# 4. Doubtful reports
d = pd.read_excel(DOUBT, sheet_name="Review", dtype=str)
cat = lambda s: s.fillna("").str.replace(r"^reviewer_\d: ", "", regex=True).str.split().str[0]
r1, r2, fin, prop = cat(d.decision_reviewer_1), cat(d.decision_reviewer_2), cat(d.decision_final), cat(d.proposed_verdict)
n_d = len(d)
agree_rr = int((r1 == r2).sum())
agree_pf = int((prop == fin).sum())
fin_counts = fin.value_counts().to_dict()
rows.append(dict(stage="Doubtful reports after extraction", unit="Reports", model_role=f"Claude Opus 5.5 proposed a verdict with evidence for the {n_d} reports left as doubtful",
                 human_decisions=2 * n_d, human_task="The two registered reviewers decided every report independently; disagreements resolved by consensus",
                 agreement=f"Reviewer 1 versus reviewer 2: {agree_rr} of {n_d} ({pct(agree_rr, n_d)}) same category; model proposal versus final decision: {agree_pf} of {n_d} ({pct(agree_pf, n_d)}) same verdict category",
                 outcome="; ".join(f"{k.replace('_', ' ').lower()} {v}" for k, v in fin_counts.items()),
                 source=DOUBT))

# 5. Reports excluded at extraction
b9 = pd.read_excel(f"{R2}/r2_b09_extraction_exclusions.xlsx", sheet_name="reports", dtype=str)
n9 = len(b9)
dec = b9.decision.str.replace(r"^EXCLUDE_.*", "EXCLUDE", regex=True)
prop9 = b9.proposal.str.replace(r"^EXCLUDE_.*", "EXCLUDE", regex=True)
with_prop = prop9 != "REVIEW"
agree9 = int(((prop9 == dec) & with_prop).sum())
rows.append(dict(stage="Reports excluded by the model during extraction", unit="Reports", model_role=f"Claude Opus 5.5 excluded {n9} reports during extraction; for {int(with_prop.sum())} of them a second reading proposed a verdict, {int((~with_prop).sum())} were left for review without proposal",
                 human_decisions=n9, human_task="Reviewers decided every report",
                 agreement=f"Second-reading proposal versus decision: {agree9} of {int(with_prop.sum())} ({pct(agree9, int(with_prop.sum()))}) same category",
                 outcome="; ".join(f"{k} {v}" for k, v in dec.value_counts().to_dict().items()).replace("INCLUDE_SQ1", "admitted to the distribution analysis").replace("INCLUDE_MA", "admitted to the meta-analysis").replace("NOT_RETRIEVED", "recorded as not retrieved").replace("EXCLUDE", "remained excluded"),
                 source=f"{R2}/r2_b09_extraction_exclusions.xlsx"))

# 6. Row verification
b2 = pd.read_excel(f"{R2}/r2_b02_rows.xlsx", sheet_name="rows", dtype=str)
b2r = pd.read_excel(f"{R2}/r2_b02_rows.xlsx", sheet_name="reports", dtype=str)
act = b2.row_action.value_counts().to_dict()
fields = {c[:-2]: int(b2.loc[b2.row_action == "CORRECT", c].notna().sum()) for c in b2.columns if c.endswith("_v")}
fields = dict(sorted(fields.items(), key=lambda kv: -kv[1]))
b11 = pd.read_excel(f"{R2}/r2_b11_new_ast_rows.xlsx", sheet_name="rows", dtype=str)
a11 = b11.row_action.value_counts().to_dict()
rows.append(dict(stage="Data extraction: susceptibility rows", unit="Rows", model_role="Claude Opus 5.5 extracted every row from the full text with notes on ambiguities and calculations",
                 human_decisions=len(b2) + len(b11), human_task=f"Every row of every report eligible for the meta-analysis checked against the PDF ({len(b2)} rows of {len(b2r)} reports); {len(b11)} rows added by the reviewers were checked by a second reviewer",
                 agreement=f"Model row versus PDF: {act['OK']} confirmed ({pct(act['OK'], len(b2))}), {act['CORRECT']} corrected ({pct(act['CORRECT'], len(b2))}), {act['EXCLUDE_ROW']} removed ({pct(act['EXCLUDE_ROW'], len(b2))}); fields corrected: " + ", ".join(f"{k} {v}" for k, v in fields.items()) + f"; added rows: {a11.get('CONFIRM', 0)} confirmed, {a11.get('CORRECT', 0)} corrected, {a11.get('DISCARD', 0)} discarded",
                 outcome=f"{int((b2r.report_eligible == 'YES').sum())} reports eligible for the meta-analysis, {int((b2r.report_eligible == 'NO').sum())} not eligible",
                 source=f"{R2}/r2_b02_rows.xlsx; r2_b11_new_ast_rows.xlsx"))

# 7. Other verification workbooks with a proposal and a decision
b3 = pd.read_excel(f"{R2}/r2_b03_collection_pairs.xlsx", sheet_name="pairs", dtype=str)
b4 = pd.read_excel(f"{R2}/r2_b04_ar20_rows.xlsx", sheet_name="rows", dtype=str)
b5 = pd.read_excel(f"{R2}/r2_b05_species_id.xlsx", sheet_name="reports", dtype=str)
b7a = pd.read_excel(f"{R2}/r2_b07_allocation_c5.xlsx", sheet_name="allocation", dtype=str)
b7c = pd.read_excel(f"{R2}/r2_b07_allocation_c5.xlsx", sheet_name="c5", dtype=str)
b3d, b4d, b5d = b3.decision.value_counts().to_dict(), b4.decision.value_counts().to_dict(), b5.decision_species_id.value_counts().to_dict()
b5_agree = int((b5.species_id_proposal == b5.decision_species_id).sum())
rows.append(dict(stage="Collections, rows not estimating a prevalence, species identification, allocation and agronomic management", unit="Pairs, rows and reports",
                 model_role="Model-generated proposals (candidate pairs of reports describing the same collection; rows suspected of not estimating a prevalence; species identification method; allocation of isolates and documentation of agronomic management in natural matrices)",
                 human_decisions=len(b3) + len(b4) + len(b5) + len(b7a) + len(b7c),
                 human_task=f"Reviewers decided {len(b3)} candidate pairs, {len(b4)} flagged rows, {len(b5)} identification methods, {len(b7a)} allocations and {len(b7c)} natural-matrix reports",
                 agreement=f"Pairs: proposal was definite (YES) for {int((b3.proposal == 'YES').sum())}, PARTIAL for {int((b3.proposal == 'PARTIAL').sum())} and left for review for {int((b3.proposal == 'REVIEW').sum())}; identification: proposal confirmed in {b5_agree} of {len(b5)} ({pct(b5_agree, len(b5))}); flagged rows: {b4d.get('EXCLUDE_AR20', 0)} excluded and {b4d.get('KEEP', 0)} kept",
                 outcome=f"Pairs: same collection {b3d.get('YES', 0)}, partial overlap {b3d.get('PARTIAL', 0)}, different {b3d.get('NO', 0)}; allocation rows removed or reassigned {len(b7a)}",
                 source=f"{R2}/r2_b03_collection_pairs.xlsx; r2_b04_ar20_rows.xlsx; r2_b05_species_id.xlsx; r2_b07_allocation_c5.xlsx"))

# 7 bis. Round 4: re-reading of the exclusions and rows of the added reports
b15 = pd.read_excel(B15, sheet_name="reports", dtype=str)
d15 = b15.decision.value_counts().to_dict()
inc15 = set(b15[b15.decision.isin(["INCLUDE_MA", "INCLUDE_SQ1"])].study_id)
rows.append(dict(stage="Re-reading of the full-text exclusions", unit="Reports",
                 model_role="Claude Opus 5.5 answered specific questions from the reviewers and edited the wording of comments; it decided nothing",
                 human_decisions=len(b15), human_task=f"The {len(b15)} exclusions outside the blind sample that contained terms specific to susceptibility testing or could not be read as text were read jointly by two reviewers, to establish how many eligible reports had been excluded",
                 agreement="Not applicable: joint reading, no agreement statistic",
                 outcome=f"{d15['EXCLUSION_CONFIRMED']} confirmed; {len(inc15)} included ({d15['INCLUDE_MA']} eligible for the meta-analysis, {len(inc15 & pooled_reports)} contributing to a pooled stratum); {d15['NOT_RETRIEVED']} recorded as not retrieved",
                 source=B15))
b16r = pd.read_excel(B16, sheet_name="rows", dtype=str)
b16p = pd.read_excel(B16, sheet_name="reports", dtype=str)
rows.append(dict(stage="Data extraction: rows of the reports added in the last round", unit="Rows",
                 model_role="Claude Opus 5.5 proposed the rows of the 15 reports from the full text (8 of the re-reading and 7 of the arbitration of the blind sample)",
                 human_decisions=len(b16r), human_task=f"Reviewers checked {len(b16r)} rows of {len(b16p)} reports against the PDF and decided the collections and the rows that do not estimate a prevalence",
                 agreement=f"{int((b16r.row_action == 'CONFIRM').sum())} of {len(b16r)} rows confirmed",
                 outcome="3 reports excluded from the main analysis because their isolates were selected for resistance", source=B16))

# 7 ter. Reproducibility of the model (no human decision)
rows.append(dict(stage="Run-to-run reproducibility of the model", unit="Reports",
                 model_role="Two further independent runs of Claude Opus 5.5 with the same instructions on 200 full-text decisions and 50 extracted reports",
                 human_decisions=0, human_task="None: this measures repeatability, not accuracy",
                 agreement="Screening decision between pairs of runs 85.5-92.0% (Cohen's kappa 0.75-0.86; Fleiss' kappa across the three runs 0.80); same decision in all three runs for 83.5% of the reports",
                 outcome="Number of isolates and compartments reproduced in all 50 re-extracted reports; all counts in 167 of 201 and 171 of 209 rows common to the runs",
                 source="05_phase3_model_validation/reproducibility_2026-10-29"))

# 8. Risk of bias, RB8
rows.append(dict(stage="Risk of bias: handling of repeated isolates (RB8)", unit="Reports", model_role="No model (the other criteria were derived from the verified extraction)",
                 human_decisions=2 * (RB8["cal_n"] + RB8["full_n"] + 13), human_task=f"Two reviewers read the full text of {RB8['cal_n']} reports in calibration and {RB8['full_n']} in the full pass, with a verbatim quote for every value other than not declared, and the 13 reports added in the last round; disagreements arbitrated",
                 agreement=f"Cohen's kappa {RB8['cal_kappa']} in calibration and {RB8['full_kappa']} in the full pass",
                 outcome="Overall judgement per report in Table S8", source=RB8["source"]))

tab = pd.DataFrame(rows)
tab.insert(0, "no", range(1, len(tab) + 1))
total = int(tab.human_decisions.sum())
now = datetime.now().astimezone()
stamp = now.strftime("%Y-%m-%dT%H%M%S")
base = f"{OUT_DIR}/tabS15_human_model_agreement_v3_{stamp}"
if os.path.exists(base + ".csv"):
    sys.exit("output exists")
tab.to_csv(base + ".csv", index=False, encoding="utf-8")
with pd.ExcelWriter(base + ".xlsx", engine="openpyxl") as xw:
    tab.to_excel(xw, index=False, sheet_name="Table S15")
    ws = xw.sheets["Table S15"]
    for col, w in zip("ABCDEFGHI", (5, 28, 14, 45, 12, 55, 70, 55, 50)):
        ws.column_dimensions[col].width = w
    from openpyxl.styles import Alignment
    for row in ws.iter_rows():
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    note = pd.DataFrame({"note": [
        "Table S15. Human decisions and language-model proposals by stage of the review, with the agreement between the proposal and the human decision where both exist.",
        f"Human decisions counted in this table: {total:,} (each record decided by two readers counts twice).",
        "Agreement statistics are those computed by the chain scripts named in the source column; kappa values carry their 95% confidence interval.",
        f"Built by 40_tabS15_human_model_agreement_v3.py on {now.isoformat(timespec='seconds')}."]})
    note.to_excel(xw, index=False, sheet_name="Notes", header=False)
log = run_log.write(__file__, INPUTS, [base + ".csv", base + ".xlsx"], human_decisions_total=total, rows=len(tab))
print(f"written {base}.csv/.xlsx; human decisions {total:,}; log {log}")
