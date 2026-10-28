#!/usr/bin/env bash
# Rebuild the v0 tidy tables and their workbook from the project root.
# Inputs are never modified. Outputs go to 10_phase8_analysis/data/.
# The data dictionary used by the workbook step (data_dictionary_v1_target_2026-10-20.csv) is kept in the project archive.
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=10_phase8_analysis/data/tidy_tables_v0_2026-10-20
python3 10_phase8_analysis/scripts/build_tidy_tables_v0.py \
  --screening 07_phase5_full_text_screening/full_text_screening.xlsx \
  --extraction 08_phase6_data_extraction/data_extraction_tropicalis.xlsx \
  --pdf-groups 07_phase5_full_text_screening/pdf_identical_groups_2026-10-20.csv \
  --truncated 07_phase5_full_text_screening/pdf_truncated_2026-10-20.csv \
  --doubtful-review 07_phase5_full_text_screening/doubtful_review_2026-10-20/full_text_doubtful_review_2026-10-20.csv \
  --out "$OUT"
python3 10_phase8_analysis/scripts/make_workbooks.py --only tidy \
  --tidy "$OUT" --review none --batches none \
  --data-dict 10_phase8_analysis/data/data_dictionary_v1_target_2026-10-20.csv \
  --out 10_phase8_analysis/data
