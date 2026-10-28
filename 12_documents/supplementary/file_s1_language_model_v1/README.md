# File S1. Language-model components of the review

Models, versions, instructions and outputs of every step in which a language model took part.
No model output entered the analysis without the human verification described in Sections 2.4
and 2.5 of the manuscript. The instructions were written in Spanish; this folder holds English
translations, and the SHA-256 of each Spanish original identifies the exact text that was used.
The originals, the raw model responses and the free-text reasons of the deduplication decisions
are kept outside the deposit by the review team.

| Step | Model | Interface | Dates (UTC) | Instruction in this folder | SHA-256 of the original |
|---|---|---|---|---|---|
| Deduplication: classification of 77,603 candidate pairs | Claude Sonnet 5 (`claude-sonnet-5`), Anthropic | Claude Code 2.1.284, non-interactive mode (`claude -p --model claude-sonnet-5`), instruction as appended system prompt, output constrained by a JSON schema, batches of 40 pairs | 2026-09-28 to 2026-09-30 | `deduplication/pair_adjudication_instruction_EN.txt`, `deduplication/pair_schema_EN.json` | `88161539025c39d3cb5781811348038640ebe62e8133f92b5a05bf269b70518c` (instruction), `3710ec8003108ce3c2b7cea9d72739bfa0cd97432bd60902b058b9fa3448f80d` (schema) |
| Full-text screening | Claude Opus 5.5 (`claude-opus-5-5`), Anthropic | Claude Code sessions, one batch of reports per session | 2026-10-19 | `full_text/full_text_screening_instruction_EN.md` | `22bb72d4bcf14fb477008d00cbf1c124973cfab59926f2b31446fff4e7f2dd5c` |
| Data extraction | Claude Opus 5.5 (`claude-opus-5-5`), Anthropic | Claude Code sessions, one batch of reports per session | 2026-10-19 to 2026-10-20 | `full_text/data_extraction_instruction_EN.md` | `a87f47fed9302e25e0dee9db67a24442a2caf0cfd981d2e5da5cfcd1767f9dca` |
| Full-text screening and data extraction of the 16 retrieved reports of the reference-list check (round 3) | Claude Opus 5.5 (`claude-opus-5-5`), Anthropic | Claude Code subagents, one for screening and one for extraction | 2026-10-27 | the two instructions above, unchanged (only the file locations differed) | `22bb72d4bcf14fb477008d00cbf1c124973cfab59926f2b31446fff4e7f2dd5c` (screening), `a87f47fed9302e25e0dee9db67a24442a2caf0cfd981d2e5da5cfcd1767f9dca` (extraction) |
| Proposals on the 316 doubtful reports | Claude Opus 5.5 (`claude-opus-5-5`), Anthropic | nine independent sessions | 2026-10-20 | `07_phase5_full_text_screening/doubtful_review_2026-10-20/instructions_frozen_2026-10-20.md` (in the project) | `414197ed3dca1abc3adea85a575f3ff7fe523be910f2565048f187854921258f` |

Before the deduplication run, Claude Sonnet 5 and Claude Opus 5.5 were both run on a development
set of 300 pairs labelled by one reviewer; the production run used Claude Sonnet 5. The model
identifier recorded for each production decision is the one returned by the service.

## Deduplication files

- `pair_adjudication_instruction_EN.txt`: the instruction, with the response labels of the original
  in brackets.
- `pair_schema_EN.json`: the output schema, with field names and labels in English.
- `model_decisions_n77603.csv`: one row per candidate pair with the model decision (`SAME_WORK`,
  `DIFFERENT_WORKS`, `UNDECIDABLE`), the field that supported it, the batch, the model identifier
  that answered and the time. The free-text reason written by the model is in Spanish and is not
  part of the deposit.
- `run_manifest_EN.json`: model requested, Claude Code version, SHA-256 of the instruction, schema
  and input pairs, batch size and start time.
- `runs_EN.log`: the five runs, with the pairs pending at the start of each.

Decision counts: 52,650 `SAME_WORK`, 24,664 `DIFFERENT_WORKS` and 289 `UNDECIDABLE`. Every pair on which the
model and the deterministic algorithm disagreed, every `UNDECIDABLE` pair and every pair in the zone
between the algorithm thresholds was read by two blinded reviewers; pairs on which both agreed were
audited by random samples (200 merged pairs and 1000 non-merged pairs).

## Full-text files

- `full_text_screening_instruction_EN.md` and `data_extraction_instruction_EN.md`: the instructions,
  with the field names of the model output kept as in the original and their meaning in brackets.
  The resulting screening and extraction records are `07_phase5_full_text_screening/full_text_screening.xlsx`
  and `08_phase6_data_extraction/data_extraction_tropicalis.xlsx`.
