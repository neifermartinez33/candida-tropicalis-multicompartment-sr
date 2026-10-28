# Team decisions, 2026-10-26

*Candida tropicalis* review, PROSPERO CRD420261486387. It complements `team_decisions_2026-10-24.md`, which is not modified.

They are taken upon return of the round 2 workbooks and before the FINAL run. All are made after seeing data and are declared in the table of deviations in Methods. Each one cites the files where the trace is kept.

## E1. Doubtful reports that leave the meta-analysis

R01131, O04837, O06082 and R09590 move from `ENTERS_REVIEW_AND_MA` to `ENTERS_REVIEW` (they enter SQ1, not the meta-analysis). O04837 and O06082 contributed unverified susceptibility rows and rows from samples selected by phenotype (panel enriched with resistant isolates; isolates chosen for their resistance); R01131 uses author breakpoints and R09590 has no extracted rows. Trace: comment on each row in `07_phase5_full_text_screening/doubtful_review_2026-10-20/full_text_doubtful_review_2026-10-20.xlsx`.

## E2. PDF of another work found during row verification (B02)

R00374 and O09663 are recorded as not retrieved (`ec_if_not = NOT_RETRIEVED`), not as excluded by criterion. The PRISMA counts them in a separate line of not retrieved reports. Code: `build_analysis_dataset_v3.py`, `01_prisma_counts_v3.py`, `20_fig01_prisma_v4.R`.

## E3. Duplicate record of the same publication

R09497 is the same article as O13298 (Momani, EMHJ 2000), which already enters. It is counted as a duplicate record in the PRISMA, with the reviewer's decision in the note. Code: `dataset_v3_core.extra_reports`, `build_analysis_dataset_v3.py`, `01_prisma_counts_v3.py`.

## E4. Inclusion with the correct text when the assigned PDF is another work

The inclusion of O17437 in SQ1 is respected (Tu et al. 2019; n = 22; C1; Taiwan). General rule: if the assigned PDF is of another work and the reviewer includes it in B09 after reading the correct text, the data in the B09 columns replace those of the extraction; in the FINAL run they are mandatory. Trace: comment and columns of O17437 in `r2_b09_extraction_exclusions.xlsx`.

## E5. Inclusions from the arbitration of the blind sample

The arbiter's 41 inclusions of reports excluded at full text enter SQ1 with the data from the confirmed blind reading (compartment, n), from screening (country, identification, period, design) and from the record (author, year). The four countries that appear only in the reviewers' comments are in `08_phase6_data_extraction/verification/round2_2026-10-24/b08_arbitration_country_from_comments_2026-10-26.csv`, with their quote. O09669 (retracted publication) remains excluded for that reason.

## E6. No new reading of the remaining exclusions (D2)

The blind sample reversed 7.9 % of the decisions (95 % CI 6.2-10.0; kappa 0.84) and 10 % of the exclusions, mainly because of rule I1 of 2026-10-24 (studies without susceptibility testing enter SQ1). The non-sampled exclusions are not re-read: it was estimated that re-reading the 734 candidates would add about 160 reports without moving any SQ1 proportion by more than 0.1 points. It is declared as a limitation, with the reversal rate and that estimate. The workbook and its generator are archived (`../candida_multicompartment_archivo_2026-10-24/MANIFIESTO_retiro_B14_2026-10-26.csv`).

## E7. B10 corrections in the extraction and in the regimen rule

The 49 corrections in `extraction_corrections_b10_2026-10-25.csv` are applied (MIC and criterion; B02 takes precedence). The regimen rule (`verification_rules_v1.py`) reads, only when the string gives neither document nor year, the itraconazole breakpoints (prior to 2012) and the fluconazole and voriconazole disk zone diameters; a declared EUCAST breakpoint is no longer treated as an undeclared version (Rule 4). Checked against all rows: no row with a regimen changes it; 9 rows gain a regimen (8 from B10 and R04910, with the same defect). The zone diameters of R04444, R04445, R04680 and R04681 were transferred to `criterion_v` from the quote or Table 1 transcribed by the reviewers.

## E8. Author breakpoints

An author breakpoint is not the standard's CBP (AR6), even if the string names a CLSI document as the method: the row leaves the resistance analysis with the reason `author_breakpoint`. It counts only if the declared threshold is the one published by CLSI for that agent (R02773, fluconazole ≥64; R01680 and R05681, itraconazole R ≥1, which are classified as CLSI prior to 2012 and are flagged for SX1). 50 rows lose their regimen, of which 6 were in the main analysis; the effect measured before deciding, with the main model, was −0.02, +0.08 and +0.18 percentage points in the three affected strata (C1, CLSI prior to 2012: fluconazole, itraconazole, voriconazole). The decision was not taken on the basis of its effect.

## E9. Data corrected by the reviewers in the B09 comments

The B09 instructions asked for the data of the SQ1 inclusions to be corrected in `comment`, and no script read that column. The values written by the reviewers were transcribed, without a new decision: n of *C. tropicalis* (88 reports), compartment (8), country (7) and allocation by compartment (3), each with the literal fragment of the comment, in `08_phase6_data_extraction/verification/round2_2026-10-24/b09_comment_transcription_2026-10-26.csv`. The allocation of O09106 and O09416 is in `isolate_groups_multicompartment_v3_2026-10-26.xlsx`; where the report already appeared in an allocation workbook (O01397, O18219, R08459), that workbook prevails, and it matches the comment. The meta-analysis input does not change (byte-for-byte identical): only Table 2, Figure 2 and the list of included reports change.

### Correction of the implementation of E8 (2026-10-26, night)

The first implementation only recognised the singular form ('of the author'). It was extended to all the forms with which the extraction records a breakpoint defined by the authors ('of the authors', "authors' own", "authors' categories", 'defined by the authors', 'adapted by the authors', 'author (S≤4 …)'). The annotation that the authors applied a standard with a version ('R according to EUCAST v11.0 (authors)', 'CLSI M100 (according to authors)') does not count as an author criterion. 44 resistance rows change; 42 leave the resistance analysis and 11 of them were in the main analysis; R04412 (itraconazole R ≥1, equal to the CLSI breakpoint prior to 2012), also from the main analysis, changes basis but is retained. The FINAL chain was run again (2026-10-26, 16:57-18:08): four strata of C1, CLSI prior to 2012, change (fluconazole 18.23 % to 18.02 %; itraconazole 19.95 % to 18.66 %; voriconazole 18.65 % to 17.87 %; flucytosine 6.82 % to 6.98 %); the PRISMA counts do not change.
