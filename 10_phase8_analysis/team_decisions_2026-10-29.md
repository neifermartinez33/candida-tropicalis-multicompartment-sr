# Team decisions, 29 October 2026

Taken while answering the second round of criticisms of manuscript v2, after the final analysis run of
28 October 2026. No decision here changes the analysis dataset or any pooled estimate.

## D1. Certainty of the evidence: GRADE is rated, with the thresholds of the draft (closes P6 of 2026-10-24)

The team approves the thresholds that `35_grade_draft_v1.py` had proposed on 27 October 2026 and they are
applied without change. The protocol applies GRADE adapted to single proportions estimated from observational
data but fixes no numeric threshold, so these were agreed today, after the results had been seen, and are
reported in full with the rating of every stratum so that any rating can be recomputed or re-rated.

| Domain | Rule |
|---|---|
| Risk of bias | Serious (one level) if more than 50% of the isolates of the stratum come from collections whose index report is at high risk of bias |
| Inconsistency | Serious (one level) if the 95% prediction interval spans more than 50 percentage points; very serious (two levels) if it spans more than 75 |
| Imprecision | Serious (one level) if the width of the 95% CI of the population mean exceeds the estimate itself, or if fewer than 300 isolates contribute |
| Indirectness | Serious (one level) for the non-human compartments, which pool heterogeneous hosts or matrices; not serious for the human host |
| Publication bias | Not downgraded: conventional funnel asymmetry is not valid for proportions; non-retrieval is examined instead (Table S11) |

Starting level: high, as for prevalence questions. Result over the 27 pooled strata of the final run: high 2
(caspofungin and micafungin resistance in the human host, CLSI species-specific), moderate 8, low 6 (including
fluconazole resistance in the human host under current breakpoints) and very low 11 (including all four
non-human strata). Inconsistency lowered the rating in 18 strata, imprecision in 15, risk of bias in 10 and
indirectness in 4.

Written to `12_documents/supplementary/tables/tabS16_grade_v1_*` by `41_tabS16_grade_v1.py`, with its log. No
summary of findings table is produced, because the review estimates no effect measure. Declared as a decision
taken after the data had been seen in Table A1, row 7, and in entry 22 of Table S12, rewritten as v4 by
`42_tabS12_deviation_log_v4.py`.

## D2. The susceptibility rows of the reports added by the B08 arbitration are not extracted

Of the 41 reports that the arbitration of the blind sample added (decision of 2026-10-26), 27 report no
susceptibility testing, 6 report it without a method, criterion or MIC from which a row could be built, 1 had
been selected for its resistance (AR20) and 7 report susceptibility by species. The rows of those 7 are not
extracted, for two reasons:

- Two of them belong to multinational surveillance programmes, ARTEMIS and SENTRY, whose collections already
  contribute to the pooled strata (`COL_O02615`, `COL_O02333`, `COL_O10502`, `COL_O13692`, `COL_R06762`).
  Only one report per collection and stratum contributes, the one with the most isolates tested, so extracting
  them would change which report represents a collection, not add collections.
- The other five contribute between 1 and 7 isolates each.

Declared in Section 3.1 of the manuscript and in the Limitations, with these numbers. The alternative, to
extract the two multinational reports and re-decide the collection overlap (AR1, AR2, workbook B03), was
considered and rejected as disproportionate to its effect on the estimates.

## D3. Client version of every language-model step

Recorded from the session transcripts of each date and written into File S1 and Sections 2.4 and 2.5 of the
manuscript: Claude Code 2.1.284 for the deduplication (28 to 30 September 2026), 2.1.302 for the full-text
screening, the data extraction and the proposals on the doubtful reports (19 and 20 October 2026), and 2.1.310
for round 3 of the reference-list check (27 October 2026).
