# Team decisions, 2026-10-24

*Candida tropicalis* review, PROSPERO CRD420261486387.

They are taken after seeing the results of the 2026-10-23 run and the 2026-10-24 audit (`candida-tropicalis/auditoria-preredaccion-2026-10-24.md`), and before any re-run. All are declared in Methods as decisions made after seeing the data. The MD5 of this file is recorded in the log of each script that reads it. Any change goes to a new, dated file, with its reason.

## D1. Scope of the first article

It covers SQ1 (distribution of isolates by compartment) and the phenotypic part of SQ2: proportion of non-wild-type by ECV (primary) and of resistance by clinical breakpoint (secondary), by compartment, agent and interpretive regimen, with their sensitivity analyses and the exploratory meta-regression of heterogeneity described below.

The following are left for a second report, declared today and before analysing them: the frequency of molecular determinants of SQ2, the MIC distributions, SQ3 to SQ7 and hypotheses H1 to H5.

The meta-regression of the first article uses only the registered covariates that do not belong to a postponed hypothesis: susceptibility method, region, overall risk of bias judgement, species identification method and editorial status. Compartment (H2), clade (H1), period and criterion version (H4) move to the second report. One covariate is run at a time, only in strata with at least ten collections per covariate, and it is declared exploratory (protocol §9).

Declared risk: selective outcome reporting. It is mitigated by fixing the postponement today, before analysing those outcomes, and by citing this file in the article.

## D2. Human verification

Minimal, with pre-filled proposals. The automated process proposes and the reviewer decides (principle P1 of the group's standard). The following are verified:

1. The 316 doubtful reports, in the workbook already prepared (`07_phase5_full_text_screening/doubtful_review_2026-10-20/`). The 108 without the correct text become not retrieved unless the correct PDF is obtained.
2. All rows of the reports contributing to pooled strata, against the PDF.
3. The pairs of reports that are candidates to be the same collection.
4. The rows that are candidates for not measuring prevalence (D3), species identification, the allocation by compartment and the agronomic management of C5, and the four ambiguous matches of the R flow.
5. A stratified random sample, with a fixed seed, of 20 % of the full-text exclusions and 20 % of the inclusions that do not contribute to pooled strata, read blind to the previous decision. The 20 % is anchored in the protocol's alternative of screening by one reviewer (§7). The proportion of reversed decisions with its exact CI and the kappa are reported.
6. The 500 reports excluded at extraction, whose reason is coded.

This is done by the two registered reviewers, with additional readers from the group if needed; discrepancies go to the assigned third reviewer. It is declared as a deviation: the protocol requires full text in duplicate without exception.

## D3. Rows that do not measure prevalence

New rule AR20. They leave the main analysis, with their reason:

- samples selected by phenotype, that is, isolates included in the study because they are resistant, non-susceptible or carriers of a mutation;
- rows whose denominator is not reported and was inferred;
- sets compiled from public databases or from the literature, which are not a sampled collection.

A new sensitivity analysis, SX3, reincorporates them. Partial coverage, case-control designs and case reports are not excluded: they already have their registered route (RB1, RB3 and SA9).

Reason: those rows do not measure the registered outcome, the proportion among the isolates recovered from a compartment. The rule is set after seeing results and is declared as such.

## C5. Hierarchy of the reference group

The registered hierarchy, which the protocol sets as non-modifiable, is restored: the strict reading is the main analysis and the broad one goes to SA1. Deviation 5 of rules v2 and v3 is withdrawn. If strict C5 does not reach AR12, it is reported stratum by stratum, without a pooled estimate, as the protocol provides.

## D4. Applicability of the breakpoint by version

A resistance row enters a stratum only if the document or version applied by the study published a clinical breakpoint applicable to *C. tropicalis* for that agent. It is decided with two matrices by version, CLSI and EUCAST, completed with their source before re-running. It applies Table 5 of the protocol version by version; it is not a new rule.

## D5. Model by country

The main analysis remains single-level, with 7-node quadrature; the model with collection nested in country remains as SA11. It is declared as a deviation from the protocol's conditional multilevel model (§9). Choosing it stratum by stratum in view of SA11 would be a post-data decision.

## D6. Amendment in PROSPERO

The deviations are declared in the manuscript, with the table of date, content and reason required by the protocol (§1). It remains to be decided whether an amendment is also submitted with the submission (deviation 15 of the risk of bias rules) or not (decision of 2026-10-16). It does not block the writing.

## Implementation decisions (2026-10-24, afternoon)

They were taken by whoever prepared the code when writing the v4 rules, as a reasonable default and before re-running. They are written down so that the team can see them and can revert them in a new file.

- **I1. EC6 and EC7** are read as criteria on the susceptibility data: a report without those data is not excluded by them and enters SQ1 (B09, `INCLUDE_SQ1`).
- **I2. Method and criterion.** When a string names CLSI and EUCAST, the standard that gives the agent's breakpoints counts; if it cannot be separated, the row is removed.
- **I3. AR10** sums disjoint subsets of the same report when there is no total row.
- **I4. D4 by default:** the `UNVERIFIED` cells of the matrix are left out and counted; CLSI itraconazole prior to 2012 is coded with CBP (mucosal) pending P4.
- **I5. Doubtful reports that enter:** country, compartment and *n* of *C. tropicalis* absent from the extraction are taken from the 2026-10-20 reading, which the reviewer confirms when deciding the report.
- **I6. Provisional mode:** empty decision → mechanical proposal; B09 `REVIEW` → excluded unreviewed (PENDING box of the PRISMA); B03 without decision → different collections; B06 without decision → different records; empty RB8 → `not_retrievable`. The FINAL run stops with the list of what is missing.
- **I7. Unspecified identification** is missing data in SA8 and in the meta-regression (not phenotypic).
- **I8. SA5** applies AR18 to the common variance of the paired model.
- **I9.** The strata of the main analysis that do not reach AR12 in a sensitivity subset are reported with that status.
- **I10. Report labels** ("Author Year") malformed in the extraction (initials, capitals, full names, remnants of the record, non-Latin alphabets): workbook B13; the build applies the decided label and adds the letter if it coincides with another.

## Team pending items

| ID | What | Where |
| --- | --- | --- |
| P1 | Fill in the round 2 workbooks: B02 rows (5,098 rows, 1,214 reports, by priority), B03 collection pairs (384), B04 AR20 rows (136), B05 identification (141), B06 ambiguous R flow (3), B07 allocation and C5 (6 rows, 5 C5 reports), B08 blind sample (822) and its arbitration, B09 exclusions from the extraction (500; 151 without proposal), B10 mechanical changes (695, review), B11 new rows (106 in 28 reports), B12 risk of bias of new reports (150), B13 labels, doubtful reports (316) and multicompartment allocation v2 | `08_phase6_data_extraction/verification/round2_2026-10-24/`, `09_phase7_risk_of_bias/round2_2026-10-24/` |
| P2 | B06: R03187 and R05729 share candidates; if they are the same record, the PRISMA figures shift by one unit | B06 |
| P3 | Publication years missing in 5 reports (R03278 and O16063 are in the main analysis; their rows do not depend on the year). Correct them in the extraction source for the next rebuild of the tidy tables; B13 records them | B13 |
| P4 | CLSI itraconazole prior to 2012: its CBP is only for mucosal candidiasis (Rex et al. 1997). Keep it (with a note) or remove it from the matrix | D4 matrix |
| P5 | `UNVERIFIED` cells of the matrix (M60 and M44 3rd ed. zones for the species, among others): obtain the document or leave them out | `breakpoint_history_notes_2026-10-24.md` |
| P6 | GRADE: confirm before grading the anchors proposed on 2026-10-23 (limitations by the proportion of collections at High; inconsistency by *τ*² and the prediction interval, not by *I*²; indirectness by compartment and applicability of the criterion; imprecision not graded; publication bias not assessed) | findings of 2026-10-23, §12 |
| P7 | D6: submit the amendment in PROSPERO or not | — |
| P8 | The R scripts of v4 have never been run: first run in `--check` and `--provisional`, and return any error | runbook |
