# Phase 0 records not incorporated into the corpus: deduplication

Date: 2026-10-13. Phase 1, deduplication for the *Candida tropicalis* review.

## What they are

335 exported records that did not reach the imported corpus (rule C4 of the standard): 316 from the LILACS file non_clinical_matrices.ris, which was never imported, and 19 patents from the VIP file. They are identified with the same key as in the reconciliation (valid DOI or normalised title plus year). The Wanfang .txt file is the same VIP sweep in another format and is not used.

## Procedure

- Stable identifier for each record: p0nc-<source>-<position in the source file>.
- Normalisation, blocking keys and scoring identical to those of the main workflow (scripts 01, 02 and 05, thresholds from work/thresholds.json).
- Candidate pairs against the corpus and among the 335 records themselves.
- This segment has no model. For that reason all candidate pairs are read in duplicate, blind and independently, with no exception by score zone. No merge occurs without human judgement (principle P1).
- Rule RC-1 is applied to the 4 pairs it covers.
- Closure with 07_audit_close.py, prefix not_incorporated_queue; consensus with 09 if there are discrepancies.

## Blocking result

- 150 of the 335 records have at least one candidate pair; the other 185 share no key and enter the corpus as unique records.
- 294 candidate pairs: 200 against the corpus and 94 among the not-incorporated records themselves.
- By algorithm zone, as description only: 121 above the upper threshold, 2 in the intermediate zone and 171 below the lower threshold. The reviewers do not see this information.

## Files (sha256)

- 02_phase0_raw_corpus/not_incorporated/not_incorporated_n335_2026-10-13.ris: 2fab99098a162aa6dcc354e56efb2992c393aafcc07ceaebe39d39ce1a441731
- 02_phase0_raw_corpus/not_incorporated/not_incorporated_n335_2026-10-13.csv: 50c7b28fabc6f2068b97978d7309b66c9f1900a9e8a0a8ac942024dac5dee5ba
- work/not_incorporated_pairs.csv: 6fc4c4f3971f38badf0d010f5a8691d1f6c165aae69009227146b1ecb88d9247
- work/not_incorporated_queue_blind.csv: 4f3e12a4d928f56ba93dd4ce483cb4bfd8f98269e7934ecf4a615f353c5b3cf6
- work/not_incorporated_queue_key.csv: 6e2fdf4daec2671709355685fea1255a41a7c1fabef06ee79ae92d7a725cd9c3
- work/adjudication_rules_not_incorporated.csv: 3936a1378cced804c2a311a1c2223a5aa7ab7d5600f8a828f18b0371919b5aa3
- algorithm/11_not_incorporated.py: 60025fc90ebd61d47fc4955fb9bccc28610e25fb96e4b006674bb7c879be2db1
- algorithm/07_audit_close.py: 490e6cab7122250117f76338adaa45c6542dfe177c1659e1ce4124b8000de2af

## Closure of the queue

- Two complete and independent readings, 294 pairs each. Raw agreement 0.9966; Cohen's kappa 0.9930; one discrepancy.
- N0273 (p0nc-VIP-0091 versus rayyan-690626055, patent): reviewer_2 SAME_WORK, reviewer_1 UNDECIDABLE. Consensus SAME_WORK, validated by the two reviewers and communicated by reviewer_2. script recorded it in work/not_incorporated_queue_consensus.xlsx at their request, at 12:22 Colombia time. Both records have the same publication number (118957127); the VIP record has no year in PY or in Y1.
- RC-1 covered 4 pairs (N0054, N0071, N0087, N0102) and did not change any judgement: the two reviewers had already judged them DIFFERENT_WORKS.
- Key opened at 12:22 Colombia time. Result: 123 SAME_WORK, 171 DIFFERENT_WORKS, 0 UNDECIDABLE.
- The 07 table that cross-tabulates human judgement and model comes out as zeros by construction, because the model was not run in this segment. It is not interpreted.
- Cross-tabulation with the algorithm decision, descriptive only: DUPLICATE 117 SAME_WORK and 4 DIFFERENT_WORKS; DOUBTFUL 2 SAME_WORK; DIFFERENT 4 SAME_WORK and 167 DIFFERENT_WORKS.

## Grouping

- Union of the 123 SAME_WORK pairs. No DIFFERENT_WORKS pair ends up within the same group: there are no chaining conflicts.
- Five groups contain two corpus records. In all five, those two records already form an L1 pair of the main workflow (Q077581 to Q077585, same patent number); the union does not create new merges within the corpus.
- LILACS, 316 records: no SAME_WORK pair with the corpus. 113 records form 48 internal groups (65 internal duplicates). Unique works: 251 (185 without a candidate pair, 18 with only DIFFERENT_WORKS pairs, 48 group representatives).
- VIP, 19 records: all 19 are SAME_WORK with 19 corpus records (29 pairs).

## Finding: the 19 VIP records were not not-incorporated records

- In VIP_VIP-1_chinese_159_2026-09-11.ris those 19 records have no year in PY or in Y1; the date is only in DA. Rayyan took the year from DA and wrote it into Y1. The reconciliation key takes the year from PY or Y1, so the exported record was left as a title without a year and the corpus record as a title with a year. The absence is an artefact of the key.
- Their 19 counterparts are corpus records between rayyan-690626038 and rayyan-690626115, with the same title and the year from DA. They are exactly the 19 corpus records without a key counterpart in any export, and they are part of the residual of 81.
- Rerun of the reconciliation in memory, without writing files, taking the year from DA when PY and Y1 are missing: 51,030 exported − 316 absent − 3,132 consolidated copies + 62 residual = 47,644. Only the VIP file changes (from 19 to 0 absent).
- The blind human adjudication reached the same conclusion by another route: the 19 are SAME_WORK with their counterparts.
- It is a correction made after seeing the data and is declared as such.

## Pending decision

- PRISMA accounting: R4 remains at 316 (LILACS only); the 19 VIP records neither enter the corpus as new records nor are counted as removed duplicates; the residual to be explained falls from 81 to 62.
- Dated correction in candida-tropicalis/reglas-conteo-prisma-y-conciliacion.md, which states that 19 VIP records did not reach the corpus, and in the reconciliation procedure of the standard (year from DA when PY and Y1 are missing), which is inherited by the *Acinetobacter baumannii* review.
- Reporting of this segment separately from the metrics of section 5.8: the model was not run and its records are selected for not matching the corpus by key.

## Closure files (sha256)

- work/not_incorporated_queue_reviewer_2.xlsx: c49b651d56edfa8e0f2d84eb73100745c6978f7df7b06044872cb4d4e28cba31
- work/not_incorporated_queue_reviewer_1.xlsx: 3a0201167f9eaf99f7ac1e594a5d7eb2a61c6ea5eaf10d17aae9def2079390ae
- work/not_incorporated_queue_discrepancies.csv: cda47e1e77b46dc0f41fb8af49d9d53317e6a595a3401f72b4f6a298ddbc9d93
- work/not_incorporated_queue_consensus.xlsx: b030d7525cc90ced0a0ad0a804b20553ae377c38214f0dc90127aaf0e9b13564
- work/not_incorporated_queue_result.txt: c0fb18c36c632d945aa3402ee3294329c889ba3265c0e5b3572de1dc7abeba2b

## Subsequent decisions (2026-10-13)

- reviewer_2 approved the reclassification of the 19 VIP records and the dated correction of the counting rules document. They were applied with reconciliation v2 and script 12; see decision_corpus_definition_2026-10-13.md.
- The reporting of this segment separately from the metrics of section 5.8 remains pending.

- Resolved on 2026-10-13 (16:38, Colombia time), with reviewer_2's approval of the pending items: this segment is reported separately from the metrics of section 5.8, descriptively only. See adjudication/metrics_plan_phase1_2026-10-13.md.
