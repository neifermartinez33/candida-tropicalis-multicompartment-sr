#!/usr/bin/env python3
"""40_tabS15_human_model_agreement_v1.py (2026-10-29)

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
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/40_tabS15_human_model_agreement_v1.py
Outputs (never overwritten): 12_documents/supplementary/tables/tabS15_human_model_agreement_v1_<date-time>.xlsx and .csv;
log in 10_phase8_analysis/results/logs/40_tabS15_human_model_agreement_v1_<date-time>.json.
"""
import json
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
OUT_DIR = "12_documents/supplementary/tables"
INPUTS = [FT, DOUBT, TA, CAL, MA_INPUT] + [f"{R2}/{b}" for b in (
    "r2_b08_agreement_2026-10-26T112820.json", "r2_b08_key.csv", "r2_b08b_arbitration.xlsx", "r2_b09_extraction_exclusions.xlsx",
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
ma = pd.read_csv(MA_INPUT, dtype=str, usecols=["study_id"])
added_in_ma = int(ma.study_id.isin(set(exc_to_inc.study_id)).sum())
no_ast = int((exc_to_inc.has_ast == "NO").sum())
assert ag["n"] == 822 and len(arb) == 65 and len(changed) == 57, (ag["n"], len(arb), len(changed))
rows.append(dict(stage="Full-text screening", unit="Reports", model_role=f"Claude Opus 5.5 read {n_ft} full texts and proposed a decision per criterion with verbatim evidence ({props})",
                 human_decisions=ag["n"] + len(arb), human_task=f"Stratified random sample of 20% of the decisions ({ag['n']}: {n_exc} exclusions, {n_inc} inclusions not contributing to a pooled estimate) re-read by reviewers blinded to the previous decision; the {len(arb)} disagreements arbitrated by a third reviewer",
                 agreement=f"Blind reader versus model: observed agreement {ag['observed_agreement'] * 100:.1f}%, Cohen's kappa {ag['kappa']:.2f} ({ag['kappa_ci'][0]:.2f}–{ag['kappa_ci'][1]:.2f}); after arbitration {len(upheld)} model decisions upheld and {len(changed)} changed ({pct(len(changed), ag['n'])})",
                 outcome=f"{len(exc_to_inc)} of {n_exc} sampled exclusions ({pct(len(exc_to_inc), n_exc)}) became inclusions ({no_ast} without susceptibility testing) and entered the distribution analysis; {len(inc_to_exc)} of {n_inc} sampled inclusions ({pct(len(inc_to_exc), n_inc)}) and {len(dbt_to_exc)} report that had been doubtful became exclusions; {added_in_ma} of the added reports contributed to a pooled stratum",
                 source=f"{FT}; {R2}/r2_b08_key.csv; r2_b08_agreement_2026-10-26T112820.json; r2_b08b_arbitration.xlsx"))

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

# 8. Risk of bias, RB8
rows.append(dict(stage="Risk of bias: handling of repeated isolates (RB8)", unit="Reports", model_role="No model (the other criteria were derived from the verified extraction)",
                 human_decisions=2 * (RB8["cal_n"] + RB8["full_n"]), human_task=f"Two reviewers read the full text of {RB8['cal_n']} reports in calibration and {RB8['full_n']} in the full pass, with a verbatim quote for every value other than not declared; disagreements arbitrated",
                 agreement=f"Cohen's kappa {RB8['cal_kappa']} in calibration and {RB8['full_kappa']} in the full pass",
                 outcome="Overall judgement per report in Table S8", source=RB8["source"]))

tab = pd.DataFrame(rows)
tab.insert(0, "no", range(1, len(tab) + 1))
total = int(tab.human_decisions.sum())
now = datetime.now().astimezone()
stamp = now.strftime("%Y-%m-%dT%H%M%S")
base = f"{OUT_DIR}/tabS15_human_model_agreement_v1_{stamp}"
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
        f"Built by 40_tabS15_human_model_agreement_v1.py on {now.isoformat(timespec='seconds')}."]})
    note.to_excel(xw, index=False, sheet_name="Notes", header=False)
log = run_log.write(__file__, INPUTS, [base + ".csv", base + ".xlsx"], human_decisions_total=total, rows=len(tab))
print(f"written {base}.csv/.xlsx; human decisions {total:,}; log {log}")
