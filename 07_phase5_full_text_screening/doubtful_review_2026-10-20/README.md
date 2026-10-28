# Review of the doubtful full-text records, 2026-10-20

Scope: the 316 records with `decision_final = DOUBTFUL` in
`08_phase6_data_extraction/data_extraction_tropicalis.xlsx` (sheet Studies).
The 580 records marked DOUBTFUL at full-text screening had already been re-decided
by the extraction (245 still doubtful, 298 excluded, 37 included); the extraction
added 71 included records that it turned to doubtful. 245 + 71 = 316.

Nothing here is a decision. Each line is a proposal with its evidence (quote,
page, table) for the two registered reviewers, who decide in
`full_text_doubtful_review_2026-10-20.xlsx` (columns `decision_reviewer_1`,
`decision_reviewer_2`, `decision_final`).

## Procedure

- Reader: language model (configured identifier `claude-opus-5-5`; the serving
  model may differ), nine independent sessions, one per input batch. Batch 05 was
  split at record R05488; records R05533 to O12214 were read in batch 05b.
- Instruction: `instructions_frozen_2026-10-20.md`,
  SHA-256 `414197ed3dca1abc3adea85a575f3ff7fe523be910f2565048f187854921258f`.
  It quotes the registered IC1-IC8, EC1-EC13, the compartments and the
  application rules of the frozen screening manual.
- Text: pdftotext of each PDF; tesseract OCR (English model) for the 23 scanned
  files; page images read directly where tables were missing from the text.
- Inputs (record context, previous decisions and notes) and raw outputs (one JSON line per record, as
  written by the reader) are kept unaltered, in their original Spanish, in the project archive; they are not
  part of this deposit. `10_phase8_analysis/scripts/make_workbooks.py` (mode `doubtful`) built the review
  workbook from them. The instruction file in this folder is an English translation of the frozen instruction.
- No second reading was run on these proposals; the two reviewers' decision is
  the verification.

## Verdicts

| Verdict | Records | Meaning |
|---|---|---|
| ENTERS_REVIEW_AND_MA | 43 | General rule met, IC4 with per-agent denominators and IC8 |
| ENTERS_REVIEW | 107 | General rule met (IC1, IC2, IC5, IC6, IC7 and IC3 or IC4) |
| NOT_RETRIEVED | 108 | PDF of another work (81) or partial (27); counts as not retrieved, not as excluded |
| REMAINS_EXCLUDED | 58 | EC2 22, EC3 14, EC7 8, EC1 4, EC12 4, EC4 2, EC13 2, EC2 and EC3 2 |
| NOT_DETERMINABLE | 0 | |
