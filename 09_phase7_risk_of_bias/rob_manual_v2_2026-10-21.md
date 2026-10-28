# Extraction manual: risk of bias domains not extracted (phase 7)

Review: *Multicompartment distribution and dynamics of the antifungal resistome of Candida tropicalis, with emphasis on the azole-resistant clade 4*. PROSPERO CRD420261486387.
Version 2, frozen on 2026-10-21. It supersedes `rob_manual_v1_2026-10-21.md`, which is not deleted.

What changes with respect to v1, and why. The three corrections concern the sampling design and reporting, not the criteria: none of them changes what is extracted or how it is scored, and all three were made before a single report was extracted.

1. **Calibration increases from 80 to 200 reports.** The full pass is also in duplicate, so the calibration reports are not extra reading: they are the first reports of the pass, with a pause to calculate agreement. Enlarging it costs no additional work. And with 80 no decision can be made: if `not_declared` dominates the field, with an observed agreement of 90 % and an expected agreement of 70 % the kappa is 0.67 with an interval of 0.45 to 0.89, which does not allow judging against the 0.60 threshold. With 200 the same case gives 0.53 to 0.81. In addition, 200 is the team's precedent: this is how screening was calibrated in CAL1.
2. **The calibration sample is stratified, not simple random.** Only 11 of the 1,104 eligible reports sample C3 or C5. A simple draw would bring none of them, and the calibration would not exercise `c5_definition` or `agronomic_management`. All 11 are included, plus 189 drawn from the rest.
3. **Observed agreement is reported alongside kappa, not kappa alone.** With a dominant category, kappa underestimates agreement and on its own is misleading in both directions.

This manual does not change the registered criteria or the assessment rules. It sets how the four fields that the data dictionary marks `not extracted`, on which RB8, SA1, SA2 and the C3 versus C5 discriminant depend, are extracted by reading the full text. Scoring and the overall judgement are in `rob_rules_v2_2026-10-21.md` and are not touched here: the reviewer extracts facts, not quality judgements.

It is the single instruction for the two registered reviewers, reviewer_1 and reviewer_2, and for the two arbiters, reviewer_3 and reviewer_4.

## 1. What is extracted

| Field | On which reports | What for |
| --- | --- | --- |
| `dedup_rule` | The 1,104 eligible | RB8 and SA9 |
| `editorial_status` | The 1,104 eligible | SA2, with and without preprints |
| `c5_definition` | Only those sampling C3 or C5 | SA1 |
| `agronomic_management` | Only those sampling C3 or C5 | C3 versus C5 discriminant, and RB9 |

`editorial_status` is resolved from the bibliographic record and does not require opening the PDF. The other three do.

## 2. General rule

1. **What the report says is extracted, not what the reviewer infers.** If the report does not say it, the value is the one corresponding to not saying it, and that is a data point, not a failure.
2. **Every value other than `not_declared` requires a literal quote and its page.** Without a quote the value is not recorded. The quote is what allows arbitration and auditing to take seconds instead of a re-reading.
3. **`not_declared` requires having read the complete Methods section**, not just having searched for a word. The “Methods read” checkbox is ticked so that this can be recorded.
4. Doubt is not resolved in favour of either side: the value `not_retrievable` exists and is used.
5. For languages the reviewer does not master, machine translation is used, as in screening.
6. The two reviewers work **blind and separately**, in different workbooks with the same row order. No one consults the other during the pass.

## 3. `dedup_rule`: decision sequence

### Step 1. Where to look, in this order

1. **Methods**, in the subsections on design, setting, isolates or strains, sample collection and microbiological methods.
2. **The first sentence of Results that gives the numbers**: if it says “161 isolates from 127 patients”, there is repetition even if Methods says nothing.
3. **The footnote of the first table** and that of the susceptibility table.
4. In environmental studies, the subsections on sampling and site description.

### Step 2. What counts as declared

Any sentence that sets the unit from which one isolate is retained:

- Clinical: “one isolate per patient”, “only the first isolate from each patient”, “duplicate isolates were excluded”, “non-duplicate isolates”, “one strain per patient”. Value `by_patient`.
- Host, device or anatomical site: “one isolate per animal”, “one per catheter”, “one per anatomical site”. Value `by_host_or_site`.
- Environmental: “one isolate per sample”, “one colony per plate”, “one per sampling point”. Value `by_sampling_point`.
- It says that duplicates were removed without saying by which criterion, or it sets the unit at the episode and not at the patient: value `declared_unspecified`, with the literal quote. “One isolate per episode” is not equivalent to one per patient, because a patient may have several episodes; it is recorded here and the arbiter decides whether the report also says that there was one episode per patient.
- If the report relies on the rule of a surveillance network or programme and cites it, it counts equally, with the quote of that sentence.

### Step 3. Known traps

These five produce the errors that matter. None of them counts as declared.

1. **“Consecutive isolates” is not deduplication.** It means consecutive in time, which is the opposite of selecting one per unit. It is the most frequent error in this field.
2. **“Repeated samples” referring to the case definition is not deduplication.** For example, a candiduria defined as a high count in two repeated samples requires repetition; it does not eliminate it.
3. **“Unique isolates” without saying unique with respect to what.** If it only means distinct strains by typing, it is not deduplication by patient. If it cannot be known, it is `not_retrievable`.
4. **Deduplication declared only for identification and not for susceptibility.** What matters is the denominator against the antifungal. If the rule is declared for one step and the susceptibility denominator is another number, it is `not_retrievable` and the discrepancy is noted.
5. **A multicentre study in which the rule is applied by one centre and nothing is said about the rest.** It is `not_retrievable`.

### Step 4. The three values that are not “declared”

- **`repeated_included`.** The report says that it retained repeated isolates from the same unit; **or** it reports the number of isolates and the number of patients, the two numbers differ and there is no deduplication rule. The report's own numbers are the declaration: the quote is that sentence. This is the case of O00631, with 161 isolates from 127 patients.
- **`single_sampling`.** Designs in which repetition cannot occur: a single sampling per site, an animal sampled once, an outbreak isolate. It is **not** used for a cross-sectional study of 200 patients, where repetition can occur even if it is not mentioned.
- **`not_declared`.** The complete Methods section and the first sentence of Results with the numbers were read, and there is nothing. It is a legitimate and frequent value; it is not a reviewer failure.

## 4. `editorial_status`

Three values: `peer_reviewed`, `preprint`, `grey`. It is resolved from the bibliographic record.

- `preprint`: bioRxiv, medRxiv, Research Square, SSRN, Authorea, Preprints.org and equivalents, or a version declared as a preprint by the document itself.
- `grey`: theses, technical reports, institutional documents, conference abstracts published outside a journal.
- `peer_reviewed`: the rest, including journals without an impact factor and regional journals.

A preprint that was later published in a journal and was cited by the journal version is `peer_reviewed`.

## 5. `c5_definition` and `agronomic_management`

Only for reports sampling C3, agroecosystem, or C5, natural environment. There are **eleven** among the 1,104 eligible, and all eleven enter the calibration through the stratification of section 7. This means that when the calibration closes, these two fields are complete for the whole corpus, and the full pass no longer includes them. The `site_applies` column of the workbook states which reports they apply to; this does not have to be decided.

- **`agronomic_management`**: `documented_present` if the report documents agronomic management at the site, understood as fungicide use, cultivation, fertilisation or agricultural intervention; `documented_absent` if it expressly documents that there is none; `not_evaluated` if it does not address it. Most will be `not_evaluated`, and that is also a data point.
- **`c5_definition`**: `strict` if the site has documented absence of agronomic management, that is, `agronomic_management` equal to `documented_absent`; `broad` if the site is natural but management is not documented; `not_applicable` if the report does not sample C5.

The rule links the two fields: `strict` cannot be marked without `documented_absent`. The workbook validates this.

## 6. What is always recorded

For each report and each field other than `not_declared`: the value, the **literal quote** as it appears in the text, without translating or summarising, and the **page** of the PDF. For `dedup_rule` equal to `not_declared`, the “Methods read” checkbox ticked.

The 180 extraction notes that already mention repetition of isolates **are not given to the reviewers during the pass**, because they would anchor the decision. They are used afterwards, in arbitration, as a consistency check: if the extractor's note says that there were repeats and both reviewers marked a declared rule, that row goes to the arbiter even if there is no discrepancy between them.

## 7. Procedure

1. **Calibration, CAL-RB1.** 200 reports: the 11 sampling C3 or C5 and 189 drawn from the rest with seed 21102026. The two reviewers blind, in the same order. At closure three things are reported, not one: the **observed agreement**, **Cohen's kappa with its 95 % CI** in two forms —on the eight values and on the collapse to Yes, No, Not applicable and Unclear, because with eight categories and rare cells the kappa is unstable and the collapse is what enters the scoring— and the **contingency table with the counts per cell**, which is what allows one to see whether disagreement is concentrated in a specific trap.
   **If the collapsed kappa falls below 0.60**, the discrepancies are discussed, the manual moves to the next version with the rules that were needed, and calibration is repeated on 200 new reports. It is not repeated more than twice: if the second one does not reach it either, the problem is the field and not the reviewers, and what to do with RB8 is decided before spending the rest of the hours.
2. **Full pass.** The remaining 904 reports, the two reviewers, blind, in the same random order with seed. The 200 calibration reports enter the corpus with their consensus decision and are left out of the overall kappa. The full pass includes only `dedup_rule` and `editorial_status`: the site fields were closed in the calibration (section 5).
3. **Arbitration.** The two arbiters resolve the discrepancies, with the reports split into halves by a seeded draw, as in the registered screening. They also resolve the rows flagged by the consistency check of section 6.
4. **Closure.** Consensus file with one row per report, observed agreement and overall kappa with its 95 % CI, and count of discrepancies by type.

Realistic volume: 1,104 reports per reviewer, of which 200 in the calibration and 904 in the pass. At three to four minutes per report, between 55 and 75 hours of work each. It is advisable to spread it over full working days and not short sessions, because the error in this field grows with fatigue: trap 1, confusing consecutive with deduplicated, is the one that appears most at the end of the day.

## 8. What this manual does not do

It does not assess quality. The reviewer does not decide whether a study is at high risk: they record what the report says. The overall judgement is applied afterwards by a deterministic rule that is already frozen and that no reviewer needs to know in order to extract. That separation is what allows the extraction to validate itself.
