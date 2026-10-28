# Title and abstract screening (phase 4): adopted design, allocation and preparation

*Candida tropicalis* review. Written on 13 October 2026 at 17:55, Colombia time, before running the allocation. No record has been screened.

## Team decisions (13 October 2026)

- Design: independent, blind double human reading of all works, which is the registered design. Neither of the two registered alternatives for excess volume is activated.
- Readers: the four authors, in rotating pairs.
- Language model: a non-deciding reader, with two uses: safety net and measurement of its performance.
- Arbiter: an author who does not belong to the block's pair. The registered rule ("no one arbitrates in a phase in which they were a primary assessor") is now applied per record: no one arbitrates a record they read or of which they are an author. This is declared in the amendment.
- Calibration works: their consensus decision is retained. They do not enter the general screening, the general kappa or the model metrics, because the manual is written with them.
- This design replaces the parallel design of section 8 of the Methodological Approach v4, which is not applied. Phase 3 (model admission) is not applied either: the model decides nothing, so there is nothing to admit. Its performance is measured on the full corpus.

## Frame

- The 22,403 works of the phase 1 corpus minus the 200 of the calibration: 22,203 works.
- If the calibration needs a second round, its 200 works are drawn from among the 22,203, with a seed declared before drawing, and are removed from their blocks without reallocating the others.

## Readers, pairs and blocks

| Code | Reader |
|---|---|
| reviewer_3 | reviewer_3 |
| reviewer_1 | reviewer_1 |
| reviewer_2 | reviewer_2 |
| reviewer_4 | reviewer_4 |

| Block | Reading pair | Authors outside the pair |
|---|---|---|
| B1 | reviewer_3, reviewer_1 | reviewer_2, reviewer_4 |
| B2 | reviewer_3, reviewer_2 | reviewer_1, reviewer_4 |
| B3 | reviewer_3, reviewer_4 | reviewer_1, reviewer_2 |
| B4 | reviewer_1, reviewer_2 | reviewer_3, reviewer_4 |
| B5 | reviewer_1, reviewer_4 | reviewer_3, reviewer_2 |
| B6 | reviewer_2, reviewer_4 | reviewer_3, reviewer_1 |

Each reader belongs to three pairs and reads half of the frame.

## Allocation

- Allocation seed: 1310202641, with the Python 3 random generator. A single generator, in this order: blocks that carry one extra work, allocation of the team-authored works, permutation of the rest, order within each block, arbiters.
- Sizes: 22,203 = 6 × 3,700 + 3. Three blocks, chosen by the seed, carry 3,701 works.
- Team-authored works (conflict-of-interest rule of the protocol): they are identified before allocation by searching for the four authors in the authors field; the list is kept in allocation/team_authored_records.csv. Each one is allocated to a block whose pair does not include any of its authors.
- The rest is allocated by simple random sampling until the sizes are complete.
- Order within each block: random. The import files follow that order.
- Arbiter of each block: one of the two authors outside the pair. Among the combinations in which each author arbitrates one or two blocks, the seed chooses one.

## Decision rules

1. Each reader marks include, exclude or "maybe" in Rayyan, in blind mode, applying the frozen manual. "Maybe" counts as inclusion.
2. If both include, the work goes to full text. If both exclude, it is excluded.
3. If they disagree: consensus of the pair and, if the disagreement persists, the block's arbiter decides. No one consults the model's label at this step.
4. Safety net: once the human decision for a block is closed, the model's output for that block is opened. Every work that the human decision excluded and the model included is read by the block's arbiter, unless they have already decided it as arbiter. Their decision is final.
5. What the human decision includes goes to full text, whatever the model says.
6. Team-authored works: if their pair does not reach consensus, or if the net flags them, they go directly to full text, because the authors outside the pair are authors of those works and cannot arbitrate them.

## Model

- Input: the 22,203 works of the frame, in random order with seed 1310202642 (rule G6), with the fields the readers see in Rayyan: titles, abstracts, keywords, journal, year, authors, language and DOI.
- Instruction: the frozen manual, with no separate instruction (G3). The model identifier and the client version are fixed and recorded here before the run (G1, G2).
- Timing: after the manual is frozen and before the human decision for any block is closed. The SHA-256 hash of the raw output is recorded here before it is opened for the net.
- If the model cannot be run on the whole frame with the fixed identifier, screening proceeds as registered, without the net, and this is declared (G7).

## Measurement

- Reference standard: the final human decision, after consensus and arbiter and before the net.
- Reported: sensitivity, specificity and positive predictive value of the model, with exact 95% Clopper-Pearson intervals; kappa between the model and the human decision; works that the net brought to full text and how many remain included at the end.
- Human agreement: Cohen's kappa of each pair on the initial independent decisions of its block.
- The calibration works are excluded from all these figures.
- Declared limitation: the reference is human judgement, not the truth. What readers and model both exclude remains unverified.

## Rayyan

- One new review per block, with blind mode activated before the readers enter. The arbiter is added when the pair closes its reading.
- Before importing, check that automatic duplicate resolution is disabled. Duplicate suggestions are not resolved: deduplication was closed in phase 1 and residual overlap is handled at full text (EC12).
- Do not use Rayyan's relevance sorting or prediction. Work proceeds in import order.
- Each record keeps its AN (record identifier) and carries a "SCREEN_ID" note with the work identifier. After import, the block is exported and check_rayyan_block.py is run: the block must contain exactly its works, with no missing, surplus or repeated ones. No one screens until the check closes.
- No block is imported before the manual is frozen.

## Allocation result

Run on 13 October 2026 at 17:50, Colombia time, with allocate_screening_blocks.py. Before that there were two trial runs without writing (--dry); the seed is fixed and the definitive run gave the same allocation.

Time clarification: this plan was written at 17:47 (file modification time), not at 17:55 as stated in the header. The header is not corrected, in order to preserve the hash with which the allocation was run: 2b11781e031957e7336a1b3be6dbc9519413cf3280fee3e3c3dc4ed2ba95b99a. This section was added afterwards.

- Frame: 22,203 works. Blocks with one extra work: B1, B4 and B5.
- Team-authored works: 9, all by reviewer_3 and reviewer_4 (8 by strict match, 1 loose match treated as team-authored). None is in the calibration. All 9 go to B4 (reviewer_1 and reviewer_2) and have no arbiter (rule 6).

| Block | Reading pair | Arbiter | Works | Import file |
|---|---|---|---|---|
| B1 | reviewer_3, reviewer_1 | reviewer_4 | 3,701 | import/B1_reviewer_3_reviewer_1_n3701.ris |
| B2 | reviewer_3, reviewer_2 | reviewer_4 | 3,700 | import/B2_reviewer_3_reviewer_2_n3700.ris |
| B3 | reviewer_3, reviewer_4 | reviewer_2 | 3,700 | import/B3_reviewer_3_reviewer_4_n3700.ris |
| B4 | reviewer_1, reviewer_2 | reviewer_3 | 3,701 | import/B4_reviewer_1_reviewer_2_n3701.ris |
| B5 | reviewer_1, reviewer_4 | reviewer_3 | 3,701 | import/B5_reviewer_1_reviewer_4_n3701.ris |
| B6 | reviewer_2, reviewer_4 | reviewer_1 | 3,700 | import/B6_reviewer_2_reviewer_4_n3700.ris |

- Works per reader: reviewer_3 11,101, reviewer_1 11,103, reviewer_2 11,101, reviewer_4 11,101.
- Balance between blocks: with abstract, 90.8 to 91.8%; title in Chinese, Japanese or Korean script, 1.1 to 1.7%; with DOI, 74.6 to 76.5%; median publication year, 2016 in all six.
- Works without a title: 16 (from 1 to 6 per block); 3 of them also have no abstract. Works without an abstract: 1,921. The manual must state how they are handled; proposal for the calibration: if title and abstract are not enough to decide, the work goes to full text.

## Verification

- verify_allocation.py rereads the corpus, the allocation and the generated files without reusing the allocation code. Result in allocation/verification_2026-10-13.txt: 0 failures. It checks that the 22,203 works are unique and, together with the calibration, add up to the 22,403 of the corpus; that each block file has the number of records in its name, in allocation order, with content identical to the corpus except for the SCREEN_ID note; that no team work is read or arbitrated by one of its authors; that no arbiter reads the block they arbitrate; that the model input has the same 22,203 works in their order; and that the manifest matches.
- check_rayyan_block.py was tested with the import files themselves (it closes by SCREEN_ID in the six blocks and in the calibration), with a file without the SCREEN_ID note (it closes by AN) and with CSV exports simulated for the test, one of them with two missing records and one repeated record (it does not close and names them). The test files were not saved in the project.

## Files (sha256)

| File | sha256 |
|---|---|
| allocation/team_authored_records.csv | 877441fb1d9ffd16feb87c22ace924198e33b35b42de669dd90228e841c8dec5 |
| allocation/screening_allocation_seed1310202641.csv | bc888a8f5222455e9fe0101c32c5bb8ddd4e959f137861de7b12ba629f8336f9 |
| allocation/block_pairs_and_arbiters_seed1310202641.csv | 0afb624c82e3444e5dbc8d7d3ecce8375b94ff74837765cd902fd2ec6bbc09c2 |
| allocation/allocation_report_2026-10-13.txt | f3332b8f90d87180d11f17ddf0a682b4a44efaf41d83ed66663aa08ed4534175 |
| allocation/verification_2026-10-13.txt | cc543aa9979e4bd5df2e29f85832219628b9565b2b0bd480f7a2207592bfe883 |
| model/model_input_n22203_seed1310202642.jsonl | 879c79a7c80d76a3f48d66599a2058f9afdfe4e3bc81a7d228be4290a16e8512 |
| import/B1_reviewer_3_reviewer_1_n3701.ris | 079b3f2b9b2ed6533976a954f2bbe0f3cf2345fc2f80ca1897828abc35c8e9f6 |
| import/B2_reviewer_3_reviewer_2_n3700.ris | f4c310a0aedf5975090c2e6ae0e2a470950aada36721a53d8bfb84c9456c74b6 |
| import/B3_reviewer_3_reviewer_4_n3700.ris | 28f32aa36d15b3bbc660759f573646678c3a25b84088ee9ae4c3f5d7ca4c0f11 |
| import/B4_reviewer_1_reviewer_2_n3701.ris | 3f8dfafb6239e16397ae0de1e12582ddbf21c76834d04e352b2b40c9688ad36c |
| import/B5_reviewer_1_reviewer_4_n3701.ris | 4e95a711d8690a9199a66349ca5f90e245f803c648cdcbc8b6336adfb4aa696a |
| import/B6_reviewer_2_reviewer_4_n3700.ris | f85ac11847b63f270aff3074474dc9650352597db31235de623b7bba9b0ae0e4 |
| ../04_phase2_calibration/calibration_sample_200_seed13102026_import.ris | f7ce11d921a67233f3fb06e9eb28f825dceab9f235ebb3f500e820cfe3530efa |
| search_team_authored.py | dc75c2c85b98729561d153fc396c3f16b36d5a7a0d4d08a42314867cc5860cf5 |
| allocate_screening_blocks.py | 0dfb35189a638efc5fae53248fc28caf0df82e57f3ef4449c52236ee7c6beef7 |
| check_rayyan_block.py | 0a6ddc7ea3688d85e5b7bf73a23e3ff6cb40e19b1d177cdef22fe8bfc8785608 |
| verify_allocation.py | 3f7d5436829523d576dd04a982e97cc6500a423106fc6f1c311e6b53f37ffd4f |
| ../04_phase2_calibration/make_calibration_import.py | 4b92f11113c1e67b47a5d0457490bb71576a123135970484cd1fd8c835075837 |

The hashes of the allocation outputs are also in manifest_2026-10-13.txt.

## Start-up order

1. Calibration with the four readers (addendum of 13 October in 04_phase2_calibration/calibration_plan_2026-10-13.md). File: 04_phase2_calibration/calibration_sample_200_seed13102026_import.ris, in a new Rayyan review with blind mode. Beforehand, import 3 or 4 test records, export them and run check_rayyan_block.py CAL1: the report states whether SCREEN_ID, AN or neither survives.
2. Kappa per pair; second round if any pair falls below 0.60. If there is a second round, its 200 works are removed from their blocks by filtering the existing allocation, without drawing again, and the import files of the affected blocks are regenerated before importing. That script is written only if needed: rerunning allocate_screening_blocks.py with a different frame would change the allocation of all works.
3. Freeze the manual with a hash.
4. Fix the model identifier and the client version; run the model on model/model_input_n22203_seed1310202642.jsonl; record the hash of the raw output here.
5. Import each block into its own Rayyan review (blind mode, automatic duplicate resolution disabled), export and run check_rayyan_block.py. Only a block whose check says CLOSES is screened.

## Operational clarifications for Rayyan (13 October 2026, 18:06, Colombia time)

Written after reviewing Rayyan's official help and before any import. They do not change any decision rule: they set how the rules are executed on the platform.

- Identifier: Rayyan replaces the AN with its own identifier on import and keeps the original notes, to which it adds its own data. The identifier that counts is the SCREEN_ID note. If the calibration check does not find it, no screening is done and files with the identifier in the title are generated.
- "Maybe": Rayyan does not flag "exclude + maybe" as a conflict and does not count "maybe" towards the majority. So that its conflict list matches rule 3, the readers use only Include or Exclude, and Include in case of doubt. If someone marks "maybe", the decision is computed outside Rayyan and counts as inclusion (rule 1).
- Relevance ratings: "Compute Ratings" is trained on the decisions of the whole team even when blind mode is active. No one uses it or sorts by relevance in any review of this phase.
- Duplicates: detection runs only if someone clicks "Detect Duplicates", and "Auto Resolve" deletes irreversibly. No one clicks either of them.
- Roles: the readers enter with the free Reviewer role, which decides but does not export or change blind mode. Only the owner of each review imports, exports and changes blind mode.
- Independent decisions: with blind mode active, the export only brings the decisions of the person exporting. When all readers of a review finish, the owner turns off blind mode and exports immediately, before any discussion. That export is the source of the kappa; the change log included in the export also preserves the history with date and time.
- Conflicts: the "Majority" method is set in each block, so that the arbiter's vote resolves the tie within Rayyan. The final decision is computed outside Rayyan with the rules of this plan.
- Free plan limits according to Rayyan's pricing page: 3 active reviews per account and 2 free reviewers per account (the help clarifies that this last limit is per account, not per review). Ownership proposal with free accounts, pending confirmation by the team: each owner has at most two active reviews at a time and two different invitees.

| Review | Owner | Readers | Arbiter |
|---|---|---|---|
| C1, calibration | reviewer_3 | reviewer_3, reviewer_1, reviewer_2 | consensus of the four |
| C2, calibration | reviewer_4 | reviewer_4 | consensus of the four |
| B1 | reviewer_4 | reviewer_3, reviewer_1 | reviewer_4 |
| B2 | reviewer_2 | reviewer_3, reviewer_2 | reviewer_4 |
| B3 | reviewer_2 | reviewer_3, reviewer_4 | reviewer_2 |
| B4 | reviewer_3 | reviewer_1, reviewer_2 | reviewer_3 |
| B5 | reviewer_4 | reviewer_1, reviewer_4 | reviewer_3 |
| B6 | reviewer_1 | reviewer_2, reviewer_4 | reviewer_1 |

- C1 and C2 have the same file of 200 works; they are split only because of the invitee limit. They are archived (not deleted) when the calibration closes.
- In C1, B2 and B5 the owner also reads: they do not turn off blind mode until the other readers of that review finish. In the blocks where the owner is the arbiter, the owner does not vote before the conflict stage.
- Alternative: a single account with the Advanced plan (9 active reviews and 10 free reviewers according to the pricing page) owning all reviews, or an institutional licence if the university has one.
- Exports: they are saved in rayyan_exports/ of the corresponding phase (04_phase2_calibration or 06_phase4_title_abstract_screening). If Rayyan delivers a .zip, it is kept as is and the check is run on the articles file it contains.

## Correction of 13 October 2026, 18:22, Colombia time: a single Rayyan account

The team reports that only the account of reviewer_2 has a paid licence, so all reviews are created in it. The ownership table with free accounts in the previous section is void; the rest of the operational clarifications remain in force.

- Owner of all reviews: reviewer_2. The other authors enter with the Reviewer role in the reviews where they read or arbitrate; the arbiter is invited when the pair finishes.
- Calibration in a single review (C) with the four readers; it is no longer split into C1 and C2.
- Active reviews: the calibration and six blocks. If the licence has a limit of 3 active reviews (Rayyan's help indicates this for the Free and Essential plans), the calibration is archived before the blocks and these are worked in two balanced batches: first B1, B3 and B6; then B2, B4 and B5. Each reader has one or two blocks per batch and three in total.
- Owner who also reads: reviewer_2 reads in C, B2, B4 and B6 and is the only one who can turn off blind mode. In those reviews they do not turn it off until the other readers finish. This is declared as a limitation, because Rayyan's help does not document a log of blind mode changes.
- reviewer_2 does not vote in B1 or B5; in B3 they vote only as arbiter, on ties, after the pair finishes.
- Proposal pending confirmation by the team: since reviewer_2 reads three blocks and operates the scripts, the raw output of the model is not opened until the human decision for all six blocks is closed. Its hash is recorded beforehand. This replaces the block-by-block opening of rule 4.

## Design change, recorded on 14 October 2026 at 10:11, Colombia time: two readers

Team decision communicated on the evening of 13 October, before any import into Rayyan and before anyone had screened a single work. Screening is done by reviewer_1 (reviewer_1) and reviewer_2 (reviewer_2), the two reviewers of the registered protocol. Reason: availability. Both can dedicate up to 12 hours a day; the senior researchers, reviewer_3 (reviewer_3) and reviewer_4 (reviewer_4), arbitrate and audit. The allocation into six blocks with rotating pairs is void; its files are moved unmodified to _superseded/four_readers_2026-10-13/.

- Readers: reviewer_1 and reviewer_2 read the 22,203 works of the frame, each independently and blind, in the same random order.
- Arbiter: each work is assigned an arbiter in advance, reviewer_3 or reviewer_4, by a seeded draw and in equal halves. The arbiter resolves the ties that the pair does not resolve by consensus and reads the safety-net works that correspond to them (rules 3 and 4). Neither of the two screens in this phase, so the registered arbitration rule is met as it stands.
- Team-authored works: all 9 are by reviewer_3 and reviewer_4. They have no arbiter; if the pair does not reach consensus or the net flags them, they go to full text (rule 6).
- Calibration: done by reviewer_1 and reviewer_2 on the 200 works, as registered, with Cohen's kappa; second round if it falls below 0.60.
- Seed for the reading order and the arbiters: 1310202643, a single generator and in this order: permutation of the frame; then, draw of the half of the non-team-authored works that reviewer_3 arbitrates; the rest is arbitrated by reviewer_4.
- Model input: unchanged (seed 1310202642). The new script reproduces it and checks that it is byte-for-byte identical.
- Rayyan: two reviews in the account of reviewer_2, calibration (C) and screening (S). reviewer_1 enters as Reviewer; the arbiters are invited to S when the pair finishes its reading. The safety net is read in separate reviews, one per arbiter, when the model output is opened.
- The model output is not opened until the human decision for the whole corpus is closed.
- The declared limitation remains in force: reviewer_2 is the owner of the reviews and also a reader.
- New files: prepare_two_reader_screening.py, check_rayyan_import.py (replaces check_rayyan_block.py) and verify_two_reader_import.py.

## Result of the two-reader preparation (14 October 2026, 10:11, Colombia time)

- Run with prepare_two_reader_screening.py, after a trial run without writing (--dry). Plan applied with the design change section already written: sha256 3fdbaa74769bc39abdbe5e443cf8be8f56f094df583eac1ad506137fb434aba1.
- Frame: 22,203 works. reviewer_1 and reviewer_2 read all of them, in the same order.
- Arbiters: reviewer_3, 11,097 works; reviewer_4, 11,097; without arbiter, the 9 team-authored works.
- The model input is reproduced byte for byte: it does not change.
- verify_two_reader_import.py: 0 failures (allocation/verification_two_readers_2026-10-14.txt).
- check_rayyan_import.py was tested with the screening file (it closes by SCREEN_ID), with the calibration (it closes), with the file without the SCREEN_ID note (it closes by AN) and with a CSV export simulated for the test with three missing records and one repeated record (it does not close and names them). Before using it, it was corrected so that two checks in the same second do not collide on the report name; the hash below is that of the final version. The test files were not saved in the project.
- The dated outputs carry 2026-10-14, the run date.
- The import file is 56 MB, below the 100 MB per-file limit indicated by Rayyan's help.

| File | sha256 |
|---|---|
| import/screening_reviewer_1_reviewer_2_n22203_seed1310202643.ris | 87920e46541bdfe2b3a67968e71d935065bb1c71675b95caa48d1893e792436e |
| allocation/two_reader_order_and_arbiters_seed1310202643.csv | eb23db26861b999faf5469d14e3c48e689c11ab300e5c38b2e5bee9685ef3430 |
| allocation/two_reader_report_2026-10-14.txt | 7681e94b6e82caa8dd1ab91bc35e0192438eca99c8a533efd082751fb1375238 |
| allocation/verification_two_readers_2026-10-14.txt | 11efc15e79de7ccec63d335ac16e2b38aa6adad0943c29f67a8a828f4034583f |
| allocation/team_authored_records.csv | 877441fb1d9ffd16feb87c22ace924198e33b35b42de669dd90228e841c8dec5 |
| model/model_input_n22203_seed1310202642.jsonl | 879c79a7c80d76a3f48d66599a2058f9afdfe4e3bc81a7d228be4290a16e8512 |
| ../04_phase2_calibration/calibration_sample_200_seed13102026_import.ris | f7ce11d921a67233f3fb06e9eb28f825dceab9f235ebb3f500e820cfe3530efa |
| prepare_two_reader_screening.py | 9988946eb7905e51e209e653703835dae52e3fb1e10df54edbb7d5efe6265c4f |
| verify_two_reader_import.py | 2743590396b0c42c9bdfffe9fbc1ef33afd59ea53602cb9926217414123086cc |
| check_rayyan_import.py | 3e93c19469e777ed7fa387d66d693c847693a2b0c4c78b131936b21ce0d82cd1 |
| search_team_authored.py | dc75c2c85b98729561d153fc396c3f16b36d5a7a0d4d08a42314867cc5860cf5 |

## Two-reader start-up order (replaces the previous one)

1. Amendment 1: review by the four authors and submission to PROSPERO before starting the calibration, with the review stage updated.
2. Calibration in Rayyan (review C): import the calibration file, CAL1 check, invite reviewer_1, screening by both, export of independent decisions.
3. Cohen's kappa; second round if it falls below 0.60; manual frozen with a hash; consensus on the 200 works.
4. Amendment planned by the team for after the calibration (EC4), before the general screening.
5. Backup of the project outside biocompu (rule G8) before running the model.
6. Model run with fixed identifier and version; the hash of the raw output is recorded here and the output remains unopened.
7. Screening in Rayyan (review S): import the screening file, S check, invite reviewer_1, screening by both.
8. Closure: immediate export of the independent decisions; consensus; ties go to reviewer_3 or reviewer_4 according to the table; final export.
9. Safety net: the model output is opened and each arbiter reads their works in a separate review; flagged team works go to full text.
10. Phase report: kappa, decisions, model performance and contribution of the net.

## Start of the general screening (16 October 2026)

- Frozen manual: 04_phase2_calibration/screening_manual_v1.md (sha256 5191baa5795c60191789301dcc133b6abe94032f73eefea3cbd9d7b458512595). It is the instruction for the two readers and for the model.
- CAL1 calibration: kappa 0.878 (details in the calibration plan). Team decision: there will be no more amendments; item 4 of the two-reader start-up order (EC4 amendment) is void.
- Review S in the account of reviewer_2: import import/screening_reviewer_1_reviewer_2_n22203_seed1310202643.ris, export and run the S check before anyone screens; blind mode active; reviewer_1 enters with the Reviewer role.
- Rules arising from the calibration: no test marks in the real review (if it is necessary to demonstrate the use of Rayyan, this is done in a separate review); each reader exports their decisions with blind mode active when they finish; no one comments on works until both exports are available.
- Model: the identifier and the execution route are still to be fixed. It has to run before the human decision is closed, with the backup outside biocompu done beforehand (G8), and the hash of its output is recorded here before it is opened.
- The calibration review is archived in Rayyan, without being deleted.
