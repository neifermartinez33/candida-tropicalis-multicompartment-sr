# Candida tropicalis — multicompartment distribution and antifungal resistome

Systematic review and meta-analysis of proportions.
PROSPERO **CRD420261486387**, registered 2026-09-13. Data and code deposit: https://doi.org/10.5281/zenodo.23748222. Searches executed 2026-09-07 to 2026-09-12.
GIIM, Universidad de Córdoba (Montería, Colombia). First review of the series;
*Acinetobacter baumannii* follows with the same skeleton as a sibling folder.

## Status, 2026-10-30

FINAL run of the analysis chain after round 4 (re-reading of the full-text exclusions, rows of the reports added at the
arbitration, correction of RB5 and RB6). Current dataset `10_phase8_analysis/data/analysis_dataset_v3_2026-10-30T133231`,
meta-analysis input `10_phase8_analysis/results/ma_input_v2_2026-10-30T133242.csv`.

| PRISMA quantity | n |
|---|---|
| Records screened | 22,403 |
| Reports assessed for eligibility (search) | 5,757 |
| Reports not retrieved (search) | 4,141 |
| Reports excluded after assessment (search) | 2,477 |
| Reports identified from the reference lists of four previous reviews | 23 (7 not retrieved, 4 excluded, 12 included) |
| Reports of included studies | 3,292 |
| Studies included (independent collections) | 3,056 |
| Collections contributing to a pooled estimate | 894 |

- Reproducibility check on 2026-10-30: the chain was run from a clean copy holding only the files of this folder, without the
  RIS file, from `build_analysis_dataset_v3.py` to the manuscripts. Datasets, results, tables, Figure 3 and the Word text came
  out identical to the deposited ones; the sensitivity refits differ by at most 1e-13.
- Manuscripts: `12_documents/manuscript/v4_2026-10-30/plantilla/`, on the journal template.
- Corrections after the FINAL run: RB5 and RB6 read from the verified rows for 36 reports, Table 2 with the corrected species
  identification, Table S13 with a Summary sheet, Table S14 without the Wanfang_Data row, and Table S17 added. This is release 1.1.0.
  Release 1.1.1 adds changes_log.csv, clade4.csv and pending.csv of the final dataset, which were missing from 1.1.0, and removes a phase 1 decision record.
- Manuscript drafts and the scripts that edit them are not in the repository; the scripts of the analysis chain, tables and
  figures are.
- Superseded outputs, provisional runs, record exports and copies of full texts (1,660 files) moved out of the project to the
  project archive, same relative paths, with a manifest (path, MD5, reason). Nothing was deleted.

## Status, 2026-10-28

FINAL run of the analysis chain with the reference-list check (round 3) completed. Current dataset
`10_phase8_analysis/data/analysis_dataset_v3_2026-10-28T153554`, meta-analysis input
`10_phase8_analysis/results/ma_input_v2_2026-10-28T153606.csv`; every result, table and figure log cites them, and the
13 PRISMA checks pass.

| PRISMA quantity | n |
|---|---|
| Records screened | 22,403 |
| Reports assessed for eligibility (search) | 5,771 |
| Reports not retrieved (search) | 4,127 |
| Reports identified from the reference lists of four previous reviews | 23 (7 not retrieved, 4 excluded, 12 included) |
| Reports of included studies | 3,235 |
| Studies included (independent collections) | 3,000 |
| Collections contributing to a pooled estimate | 888 |

- Round 3 (reference-list check, 2026-10-27/28): candidates B001-B023, screened and extracted with the frozen phase 5
  and 6 instructions, verified by the team (workbooks `r3_b14` and `r3_b12`). Effect on the estimates: 8 human-host
  strata change by at most 0.09 percentage points; no conclusion changes.
- The review is published as two articles (D1). The first article (distribution and phenotypic resistance) is complete;
  the second (resistome, clade 4, MIC distributions, temporal trends) is in preparation.
- Remaining Spanish residue in the tidy tables (clade, phylogeny) was translated on 2026-10-28 and the chain rerun;
  all tables and figures are identical.

## What this repository contains

By decision of the review team (2026-10-28) the repository holds:

| Content | Where |
|---|---|
| Scripts of every phase (Python, R, shell) and the computing environment | folder of each phase; analysis chain in `10_phase8_analysis/scripts/`; `10_phase8_analysis/env/` |
| Search strategies (PRISMA-S document with the literal strings, yields and dates of every source) and the PRISMA-S log | `01_search/strategies/`, `01_search/prisma_s_log.csv` |
| Screening decisions (identifiers and decisions only) and calibration | `02_phase0_raw_corpus/`, `03_phase1_deduplication/`, `04_phase2_calibration/`, `06_phase4_title_abstract_screening/`, `07_phase5_full_text_screening/` |
| Analysis matrices: extraction matrix, verification workbooks, tidy tables, analysis datasets, applicability of breakpoints | `08_phase6_data_extraction/`, `10_phase8_analysis/data/`, `10_phase8_analysis/applicability/` |
| Risk of bias: manual, rules, workbooks and assessment | `09_phase7_risk_of_bias/` |
| Pre-specified analysis rules, team decisions and the runbook of the analysis chain | `10_phase8_analysis/analysis_rules_v4_2026-10-24.md`, `team_decisions_2026-10-*.md`, `runbook_v4_2026-10-24.md` |
| Model results and run logs (MD5 of every input and output) | `10_phase8_analysis/results/`, `09_phase7_risk_of_bias/logs/` |
| Tables, figures and supplementary material of the first article | `12_documents/tables/`, `12_documents/figures/`, `12_documents/supplementary/` |

Not included: the record exports of the searched databases (RIS and similar files), because they contain third-party records and abstracts whose terms of use do not allow redistribution; also three calibration files that quote abstracts, the full texts of the reports and the manuscript drafts. Reviewers are identified only as `reviewer_1`, `reviewer_2` and `reviewer_3`.

Reproducibility: the analysis chain (runbook steps 4 to 6) runs from the files in the repository. The screening RIS
file is not included; the three scripts that read it (`build_analysis_dataset_v3.py`, `01_prisma_counts_v3.py`,
`13_tabS_lists_v1.py`) use instead `06_phase4_title_abstract_screening/import/screening_record_fields_n22203_2026-10-28.csv`
(screening identifier, first author, record type, year and language of each record), which gives identical results.
The seed-set check (`33_seed_set_check_v1.py`) searches the titles of the raw corpus and needs the RIS exports, which
are available from the authors on request within the terms of use of the databases.

Licences: code under the MIT License; data, tables, figures and documents under CC BY 4.0 (see `LICENSE`). Cite as in
`CITATION.cff`. The status notes below describe the whole project and may cite files that are not in the repository.

## Status, 2026-10-26

FINAL run of analysis chain v4 completed and validated. The deposited outputs come from the English rerun of 2026-10-27 (dataset `10_phase8_analysis/data/analysis_dataset_v3_2026-10-27T024914`, meta-analysis input `10_phase8_analysis/results/ma_input_v2_2026-10-27T024925.csv`), which reproduces the FINAL run of 2026-10-26 exactly (see "Language of the deposit" below). Every result, table and figure log cites that dataset and input, and all 145 input and output MD5 recorded in the 17 logs of the run match the files on disk.

| PRISMA quantity | n |
|---|---|
| Records screened | 22,403 |
| Reports assessed for eligibility | 5,771 |
| Reports not retrieved | 4,127 |
| Reports of included studies | 3,223 |
| Studies included (independent collections) | 2,991 |
| Collections contributing to a pooled estimate | 881 |

- Outputs for the manuscript, one version each: `12_documents/tables/` (Tables 1-4), `12_documents/figures/` (Figures 1-3), `12_documents/supplementary/tables/` (Tables S1-S11), `12_documents/supplementary/figures/` (Figure S1, exploratory funnel plots stated in the registered protocol, added on 2026-10-27). Figures at 1200 dpi (PNG, TIFF) and as vector PDF and SVG. Numbers in the text are copied from the CSV next to each table or from `10_phase8_analysis/results/`.
- Validation on 2026-10-26: main GLMM against an independent exact-integration fit (k, events, isolates and exact CIs identical; pooled means within 0.26 percentage points, the 7-node quadrature); SA3, SX1, SA10a, SA10b and the SA4/SA7 contrasts recomputed independently (identical); Tables 3, 4, S1 and Figures 2 and 3 agree with their sources.
- Post-data decisions taken on 2026-10-26, to be declared in the deviations table of Methods: `10_phase8_analysis/team_decisions_2026-10-26.md` (E1-E9), in addition to `team_decisions_2026-10-24.md`.
- E8 (author-defined breakpoints) as implemented in this run: 44 resistance rows change regime basis, 11 of them leave the main analysis; four C1 CLSI pre-2012 strata change (fluconazole 18.23 % to 18.02 %, itraconazole 19.95 % to 18.66 %, voriconazole 18.65 % to 17.87 %, flucytosine 6.82 % to 6.98 %). PRISMA counts are unchanged.
- All round-2 verification books are filled and in place. Blind-sample agreement (B08): 7.9 % of decisions reversed (95 % CI 6.2-10.0), kappa 0.84; the remaining full-text exclusions were not re-read (E6, declared as a limitation).
- Superseded runs and working material are kept outside the deposit in the project archive, with manifests (path, MD5, reason).
- Language of the deposit: the project was run in Spanish and translated into English for deposit on 2026-10-26 and 2026-10-27 (scripts, data values, column and sheet names, documents and logs; English number formats). The translated chain was rerun end to end and reproduces the Spanish run exactly: same pooled estimates, confidence intervals, PRISMA counts and table values. The Spanish-language originals are kept in the project archive. Bibliographic records (RIS exports and the corpus derived from them) are third-party metadata and are left unaltered.

## Status, 2026-10-24

Analysis chain v4 (`10_phase8_analysis/runbook_v4_2026-10-24.md`) executed end to end in `--provisional` mode. Rules:
`10_phase8_analysis/analysis_rules_v4_2026-10-24.md`, `09_phase7_risk_of_bias/rob_rules_v3_2026-10-24.md`,
`10_phase8_analysis/team_decisions_2026-10-24.md`.

- Current outputs are marked `_PROVISIONAL` and do not go to the manuscript: where a round-2 human decision is
  missing, the mechanical proposal is used.
- Pending before the FINAL run (P1): the round-2 verification books, to be filled in and returned to
  `08_phase6_data_extraction/verification/round2_2026-10-24/`, `09_phase7_risk_of_bias/round2_2026-10-24/` and the
  other paths of their manifest. Then run steps 4 to 6 of the runbook without `--provisional`.
- The 2026-10-23 results (rules v3) were superseded: Table 2 and Figure 2 used the earlier allocation workbook, and the
  sensitivity, regime and applicability errors are corrected in v4.
- Validation on 2026-10-24: the 23-10 chain reproduced its data steps exactly. For v4, the main GLMM was checked
  against an independent exact-integration fit (max. difference 0.14 percentage points, the 7-node quadrature).
  SA3, SX1, SA10a, SA10b and the SA4/SA7 contrasts were recomputed independently and agree. Tables 3, 4 and S1 and
  Figure 3 agree with `ma_results_v3`, and Figure 2 agrees with the allocation and Table 2.
- Superseded and working material (2,488 files: earlier runs, dedup work sheets and model runs, old script and rules
  versions, the former `99_archive/`) moved out of the project to the project archive, same relative paths, with a
  manifest (path, MD5, reason). Nothing was deleted.

## Status, 2026-10-13

Phase 1 (deduplication) complete. No screening decision has been made yet.

| Quantity | n |
|---|---|
| Records identified (exports in the chain, rules R1 and R2) | 51,030 |
| Identical copies consolidated (R3) | 3,132 |
| Exported but not imported (R4), recovered for deduplication | 316 |
| Corpus records with no key counterpart in the exports (explained below) | 62 |
| Raw corpus imported into Rayyan | 47,644 |
| Records entering deduplication | 47,960 |
| Duplicates removed in phase 1 | 25,557 |
| Records for screening | 22,403 |

- Deduplication was performed outside Rayyan: a deterministic algorithm and a language model, with layered human adjudication. Decisions and their dates are in `03_phase1_deduplication/adjudication/`.
- The 62 residual records have counterparts in the exports under a different key (57 with the DOI only in the export, 5 with a different year). Harmonised reading of the chain: 51,030 − 316 − 3,070 = 47,644.
- Screening corpus: `03_phase1_deduplication/results/screening_corpus_phase1_n22403_2026-10-13.ris`.
- Phase 1 metrics and the audit of Rayyan's historical deduplication: `03_phase1_deduplication/results/phase1_metrics_report_2026-10-13.txt`.
- Phase 2: calibration sample of 200 records drawn with seed 13102026, in `04_phase2_calibration/`. The two registered reviewers (reviewer_1 and reviewer_2) calibrate; import file `calibration_sample_200_seed13102026_import.ris`.
- Screening design, final on 2026-10-14: the two registered reviewers read every record, independently and blinded; unresolved discrepancies go to a third party (reviewer_3 or reviewer_4) assigned at random per record; a language model reads all records as a non-deciding safety net and its performance is measured. Plan: `06_phase4_title_abstract_screening/screening_plan_2026-10-13.md`. The four-reader allocation of 2026-10-13 was superseded before any import and is kept in `06_phase4_title_abstract_screening/_superseded/`.
- Screening prepared: one Rayyan import file with the 22,203 records outside calibration, in random order (seed 1310202643): `06_phase4_title_abstract_screening/import/screening_reviewer_1_reviewer_2_n22203_seed1310202643.ris`. Order and arbiter table in `06_phase4_title_abstract_screening/allocation/`, model input in `06_phase4_title_abstract_screening/model/`, import check `06_phase4_title_abstract_screening/check_rayyan_import.py`. Nothing is imported for screening before the manual is frozen.
- Phase 3 (model admission) does not apply under the adopted design: the model decides nothing.
- PROSPERO amendment 1: draft in `00_protocol_and_registration/amendments/`, section 4 revised to the two-reviewer design; previous drafts in `amendments/_superseded/`. Pending team review and submission.

The section below is kept as the record of 2026-09-28.

## Status — 2026-09-28

Phase 0 complete. No screening decision has been made yet by any reviewer.

| Quantity | n |
|---|---|
| Records in the source exports (57 files, 21 sources) | 51,189 |
| Records imported into Rayyan | 47,644 |
| Removed by Rayyan auto-resolver | 24,620 |
| Remaining in the screening review | 23,024 |
| Raw corpus reconstructed and verified | 47,644 |

Verification performed on the two Rayyan exports: the two sets of Rayyan identifiers are
disjoint (intersection = 0), their union is 47,644, and their sum matches the import count.
The raw corpus was therefore reconstructed from inside the platform, without re-importing
anything and without modifying the existing review. Checksums in
`02_phase0_raw_corpus/checksums.txt`.

Coverage check against the source exports: of the 43,681 DOI-bearing records in the 57 export
files, 43,377 (99.3%) have their DOI present in the reconstructed raw corpus. The 304 absent
are almost all LILACS (255) and LENS (49). Scopus is an exact match: 14,500 records in the
export and 14,500 Scopus EIDs in the corpus.

**Open discrepancy.** The source exports hold 51,189 records and Rayyan imported 47,644, a gap
of 3,545. Part of it is a duplicated search: `VIP_VIP-1_chinese_159_2026-09-11` appears twice,
as `.ris` under `VIP/` and as `.txt` under `Wanfang_Data/`, same 159 records in two formats.
The remainder is unexplained and must be resolved before the PRISMA flow diagram is written:
the candidates are records dropped by Rayyan at import and records with no DOI, which the
coverage check above cannot match.

Note: `customizations_log.csv` is empty in both exports (header row only). Rayyan does not
log auto-resolver deletions, so per-pass attribution of the deduplication is not recoverable.
Deduplication is therefore performed outside Rayyan, on the raw corpus, and Rayyan's output
is audited rather than reproduced.

## Layout

| Folder | Contents |
|---|---|
| `00_protocol_and_registration` | Registered protocol, PROSPERO record, `amendments/` |
| `01_search` | `strategies/` (exact query, filters and date per source), `exports/` (the 52 source files, one subfolder per source), `prisma_s_log.csv` |
| `02_phase0_raw_corpus` | Rayyan exports, reconstructed raw corpus, checksums |
| `03_phase1_deduplication` | `algorithm/`, `model/`, `pairs/`, `adjudication/`, `results/` |
| `04_phase2_calibration` | Calibration sample, blind decisions, kappa, frozen screening manual |
| `05_phase3_model_validation` | Run-to-run reproducibility of the language model: samples, instructions sent, outputs and agreement |
| `06_phase4_title_abstract_screening` | Human and model decisions, overlap sample, recovery layer |
| `07_phase5_full_text_screening` | Full texts, dual decisions, exclusion codes |
| `08_phase6_data_extraction` | Extraction form, double extraction, resolved dataset |
| `09_phase7_risk_of_bias` | JBI appraisal, GRADE |
| `10_phase8_analysis` | `data/`, `scripts/`, `results/` |
| `11_phase9_deposit` | List of files kept out of the repository; Zenodo package |
| `12_documents` | `methodology/`, `manuscript/`, `figures/` |
| Project archive (not deposited) | Superseded versions, earlier runs, working material and the Spanish-language originals, with manifests. Nothing is deleted |

## Naming rules

- Lowercase, `snake_case`, English, no spaces and no accents.
- ISO dates at the end: `_2026-09-28`.
- Record counts in the filename where they identify the file: `screening_corpus_n23024_2026-09-28.ris`.
- Versions `_v1`, `_v2`. Never `final`, `definitive` or `last`.
- Source export files keep their original names; provenance for any renamed file is recorded
  in the `checksums.txt` of its folder.
- Nothing is deleted. Superseded material moves out of the project to the dated archive folder next to it, with a manifest.

## Next steps as of 2026-09-28

Historical record; items 1 and 2 were resolved in phase 1 (rules R1 to R4, Status 2026-10-13) and item 3 was completed.

1. Resolve the 3,545-record discrepancy between the source exports and the Rayyan import.
2. Decide whether the duplicated VIP / Wanfang_Data search counts once or twice in PRISMA.
3. Phase 1: blocking, own algorithm, model, layered human adjudication, and measurement of
   the Rayyan auto-resolver's false positives — the figure that decides whether the existing
   review is patched or rebuilt.