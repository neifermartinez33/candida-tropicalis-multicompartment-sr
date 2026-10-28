# Definition of the screening corpus: status as of 2026-10-13

Phase 1, deduplication for the *Candida tropicalis* review.

## Decision applied: the 19 VIP records are not not-incorporated records

- Decided by reviewer_2 on 2026-10-13, after seeing the finding documented in decision_not_incorporated_2026-10-13.md. It is a correction made after seeing the data and is declared as such.
- Reconciliation v2 (02_phase0_raw_corpus/reconciliation/reconcile_sources_v2.py). Only change from v1: the year of the RIS key is taken from PY, from Y1 or, if both are missing, from DA. Chain: 51,030 exported − 316 absent − 3,132 consolidated copies + 62 residual = 47,644. The v1 outputs remain intact.
- Script 12 takes the R4 records from the v2 list of absent records. The 316 from LILACS are included. The 19 VIP patents are not included, and their 34 pairs from the not-incorporated queue are excluded (29 with the corpus and 5 among themselves, all SAME_WORK).
- The .txt file attributed to Wanfang Data still has 19 absent records in v2: in that format the same patents do not carry the year field (%D) and the date is in %8. It does not enter the chain (rule R2).

## Rules applied by script 12

Application of section 5.7 of the Methodological Approach v4: screening corpus equal to raw corpus minus confirmed merges.

- L1 merges, because the two audits met their criterion. A human judgement in L1 only confirms: 23 L1 pairs of the development set labelled UNDECIDABLE keep the L1 merge.
- L2 does not merge.
- L3 and L4 are decided by human judgement. The 3,442 pairs of the queue, by agreement plus consensus. The 5 L3 and L4 pairs of the development set, by their human label: 2 SAME_WORK, 1 DIFFERENT_WORKS and 2 UNDECIDABLE.
- RC-1 prevails over all of the above: 1,560 pairs (1,556 from the main workflow and 4 from the not-incorporated queue).
- Each queue is rebuilt with the same logic as 07 and checked against its result.txt. All five match.

## Provisional result

- 47,960 records (47,644 from the raw corpus and 316 recovered through R4) and 77,863 pairs with a decision.
- The union of the SAME_WORK pairs gives 22,365 groups and 25,595 duplicates removed. The figure is provisional: resolving the conflicts can only increase the number of groups.

## Finding: chaining conflicts

- 34 groups (212 records) contain 117 pairs that were not merged: 86 DIFFERENT_WORKS by human judgement, 25 DIFFERENT_WORKS from L2 without human reading and 6 UNDECIDABLE (5 from the queue and 1 from the development set).
- Mechanism: a record with sparse metadata, without pages or without DOI, is joined by L1 to two related works that a human separated. Examples: conference abstract and article, article and thesis, the same communication at two conferences, a translated title.
- Within the 34 groups there are 399 L1 pairs and 60 SAME_WORK pairs confirmed by humans. In 18 groups, a pair separated by human judgement is joined only by L1 links: if the human judgement is correct, each of those groups contains at least one false L1 merge.
- Script 12 writes work/chain_conflicts.csv (117 pairs, with the merge path that joins each one) and stops without writing the corpus.

## Pending decision

- Procedure for partitioning the 34 groups.
- Whether the L1 escalation rule (a false positive in the audit returns the whole layer to human reading) applies to false merges found outside the sample. By its wording it is defined on the sample of 200 pairs, which yielded zero.
- Rule for choosing the representative record of each group in the screening corpus. Section 5.7 does not set it.
- Reporting of the not-incorporated segment separately from the metrics of section 5.8, pending since decision_not_incorporated_2026-10-13.md.

## Files (sha256)

- 02_phase0_raw_corpus/reconciliation/reconcile_sources_v2.py: e821bf2f1c7a19793235c4cf819ec40a7d8fb8db9c199831ff485997da9cca72
- 02_phase0_raw_corpus/reconciliation/reconciliation_by_file_v2_2026-10-13.csv: a2a459d65007ad9a854b554e4092bee09c16131a30c6fe2c09ce34fd00fa5696
- 02_phase0_raw_corpus/reconciliation/reconciliation_absent_v2_2026-10-13.csv: d23a90068e04a3592971832c5c3af75308556c443c6766334b7bd896d01e4ea6
- 02_phase0_raw_corpus/reconciliation/reconciliation_residual_v2_2026-10-13.csv: b38e82277d60580fb25be428610a90fab9c017f9347d00ae48f1ed5ea6ded9b0
- 02_phase0_raw_corpus/reconciliation/reconciliation_summary_v2_2026-10-13.txt: b21231d04e60f25a63c188dfa1c14dbffca527677d3e0aba6706fe0ef31a9989
- 03_phase1_deduplication/algorithm/12_define_corpus.py: b3fc98c7a21e01ef48fb57ed0f0422533654316cc443b8c11c2463c8c1fe92b8
- 03_phase1_deduplication/work/chain_conflicts.csv: 0778ad7a6a868d3a06e2edbd315edf3626260240c57baf1981625552cb4fd25f

## Decisions of 2026-10-13, 12:48 Colombia time

Taken by reviewer_2 after seeing the chaining conflicts. They were made after seeing the data and are declared as such.

- **Partition of the 34 groups.** Reading by group, double and independent, by reviewer_2 and reviewer_1. Each reviewer assigns each record of the group to a work (A, B, C...) in accordance with the pair adjudication manual. Agreement is measured on the pairs implied by the two partitions and discrepancies are resolved by consensus. Within those groups, the final partition replaces the union of pairs.
- **L1 escalation.** It is not applied. The rule is defined on the random audit of 200 pairs, which yielded zero false merges. The false L1 merges that appeared through chaining are corrected with the partition and reported with their number and mechanism.
- **Representative record of each group in the screening corpus.** It is chosen by completeness, in this order: has an abstract; has a valid DOI; greatest number of filled bibliographic fields among authors, journal, year, volume, issue and page; lowest identifier. The rule does not change any count.

## Implementation (2026-10-13)

- 12_define_corpus.py extended. It additionally writes work/chain_conflict_groups.csv (212 records of the 34 groups), applies the final partition when it exists, chooses the representative with the decided rule and writes the outputs: work/pair_decisions.csv, work/corpus_clusters.csv, work/undecidable_EC12.csv, results/screening_corpus_phase1_n<N>_<date>.ris with the literal RIS blocks of the representatives, and results/corpus_definition_report_<date>.txt with the PRISMA chain. It replaces the version whose hash appears in the first list of files.
- 13_make_partition_sheets.py. Blind partition sheets: one row per record, without previous decisions or identifiers. Random order within each group, with seed 20261013. The key is sealed in work/chain_partition_key.csv.
- 14_close_partition.py. Closure analogous to 07: agreement on the implied pairs (raw agreement and Cohen's kappa) and groups with an identical partition; consensus sheet for the discordant groups; letters normalised within each group. Records with a doubt in any note go to the full-text list (EC12).
- End-to-end test outside the project folder, with simulated partitions. Scripts 12, 13 and 14 run completely and the outputs are consistent: one representative per work, RIS blocks without repetition, SAME_WORK pairs separated only within the partitioned groups, and the abstract priority respected. No figure from that test is used or kept.
- Declared risk. The reviewers had already read 151 pairs from these groups in the L3/L4 queue (86 separated, 60 merged and 5 undecidable). The reading by group is independent between reviewers, but it is not blind with respect to their own previous reading.

## Partition files (sha256)

- algorithm/12_define_corpus.py: b823fc1c16513f869e4df553cbbca9b74fbb80bea5607c4c8939d9f333237a93
- algorithm/13_make_partition_sheets.py: 21dde5598ab5aa0720fb1c3a1a684aa08021e5c0f24aa501994d60fd277258cd
- algorithm/14_close_partition.py: 313521b355d82cab6c632561ee6d16dd79581cdcd4891a7796811a748cb98b52
- work/chain_conflicts.csv: 0778ad7a6a868d3a06e2edbd315edf3626260240c57baf1981625552cb4fd25f
- work/chain_conflict_groups.csv: ed8950d53bf2ea79ed84881b50baafa7309bd88258686f176a8cad574b22bc75
- work/chain_partition_blind.csv: e64b260307e56ce5bddea3b4112ac15d784336af22514ef3d33725a9e814a93b
- work/chain_partition_key.csv: 72a67cb2ed298ae4aeb36909d58f10b8f97c14bf13785e762e4c6e0df819fab1
- work/chain_partition_reviewer_2.xlsx: aba5a6840cec2e45506e8f28bf782b944680c9ff8a07ef7771910845448c181c
- work/chain_partition_reviewer_1.xlsx: df3cafdce187b7754c118e3396da7c49e71d4d28c8dccbb82788ca1df6ae1a31

## Partition sheets submitted (2026-10-13)

- Copied to work at 15:05 Colombia time. sha256 as submitted:
  - work/chain_partition_reviewer_2.xlsx: b7d289752e7563a4c169e00390184d8bea1ebb024d54eaa7fb178ee14d7183cb
  - work/chain_partition_reviewer_1.xlsx: bbf919c295b52742d3d7cb422fc823f6a424221a334d41ad1d809fd2b39c7882
- Format check, without opening the key: both sheets keep the header, codes, row order and bibliographic cells; 212 valid letters in each; reviewer and date complete and homogeneous (2026-10-13 in all rows).
- Spelling of the notes: no errors; brief notes in lower case and without a full stop, homogeneous within each sheet. Nothing was modified.
- Consistency between letters and notes: in reviewer_1's sheet, every record with a doubt has its own letter. In reviewer_2's sheet, two couples with a doubt share a letter (G16-05 and G16-09; G22-03 and G22-06); pending the reviewer's confirmation of whether this was intended.

## Correction of reviewer_2's sheet (2026-10-13, 15:30 Colombia time)

- Decided by reviewer_2, reviewer of that sheet, after the consistency check and before calculating agreement and opening the key. It was applied by a script with their authorisation. reviewer_1's sheet was not modified.
- G16-05 and G16-09: from B to A, with the note "rule 5; version of record: J. Fungi 7(5):383". According to the reviewer, they are the same preprint (10.20944/preprints202103.0147.v1) of the J. Fungi 7(5):383 article, with the same results.
- G22-03 and G22-06: remain in B; the note "doubt" becomes "rule 3". According to the reviewer, they are the same work as each other (same title, authors and year; the SSRN DOI does not separate them, rule 2) and a work different from A.
- 6 cells change: 2 letters and 4 notes. Details in adjudication/partition_corrections_2026-10-13.csv.
- The submitted sheet is kept in work/_superseded/chain_partition_reviewer_2_submitted_2026-10-13.xlsx (sha256 b7d289752e7563a4c169e00390184d8bea1ebb024d54eaa7fb178ee14d7183cb), so that agreement can also be calculated on the sheets as submitted.
- sha256 of the corrected sheet: 38fb54a10a06291ebabbdcb6d7483f326087f78ca34d50c016bbcde0f7307a8c.

## Closure of the partition, first run (2026-10-13, 15:36 Colombia time)

- 14_close_partition.py was extended before running it on the real sheets, with reviewer_2's authorisation: it warns, without stopping the closure, when a record with a doubt shares a letter, and it also reports agreement on the sheets as submitted. The previous version was left in work/_superseded/14_close_partition_v1_313521b3.py. New sha256: 84004fb2f5bab7c76dcfcc84d2c42393eb01c2b48b2b3292e8a9f81a6589cd6e.
- No warning of a doubt with a shared letter in the final sheets.
- Agreement on the final sheets: 686 implied pairs, raw agreement 0.9461, Cohen's kappa 0.8912; identical partition in 24 of 34 groups.
- Agreement on the sheets as submitted: raw agreement 0.9665, Cohen's kappa 0.9322; identical partition in 25 of 34 groups. reviewer_2's correction reduced agreement: G16 was identical between the submitted sheets and became discordant.
- 10 groups with a different partition (G03, G04, G05, G10, G12, G16, G20, G26, G31, G34; 42 records). In 9 of them reviewer_2 separated more works than reviewer_1; in G16, the reverse. work/chain_partition_consensus.xlsx was written (sha256 585192bbb71f66e589a010722ebc1b9d6afc4de01712d92ffcf571a4929c8263). The key was not opened.

## Partition consensus sheet submitted (2026-10-13, 15:50 Colombia time)

- sha256 as submitted: 4eccdc818b7ddb038ca3371393e3a4b5936cd6d51dab88b044f214f18e57b6e1.
- Format: 42 records; codes, order, reviewers' letters and notes and bibliographic cells intact; valid WORK_consensus in all 42 rows; decided_by "consensus" in all of them.
- The 10 resolutions coincide with reviewer_1's partition. The note column is empty: there is no written reason or criterion.
- In G03, G04, G05, G10, G20 and G26 the consensus joins all the records of the group, thereby reversing 4 pairs that the L3/L4 queue judged to be different works and 2 that it left undecidable, plus 1 L2 pair.
- In G16 the consensus keeps the preprint (G16-05 and G16-09) separate, contrary to the rule 5 correction that reviewer_2 documented before the closure.
- Pending before running 14: reason for each resolution or general criterion, especially for G16 and for the previous judgements that are reversed.

## Notes of the partition consensus (2026-10-13, 16:13 Colombia time)

- Sheet with the notes as submitted: work/_superseded/chain_partition_consensus_submitted_2026-10-13.xlsx (sha256 d9f862b2e03f7d785c5826b6ea5dee13a8527149a6dbb0e7b3bbf906bc27e016). The consensus letters did not change from the previous check.
- Spelling without errors. The wording of 7 notes was standardised, without changing their meaning: "author" becomes "first author" in G20-02 and G26 (rule 3 requires the same first author, and in the data it matches), and the notes of G16-05 and G16-09 begin with the rule, like the others. Details in adjudication/partition_corrections_2026-10-13.csv. sha256 of the corrected sheet: fb56bf7b92763f24733fe1749a0a0c7a3adbd943ff31e6fed042e1d3896cd958.
- Criterion shown by the notes: the manual's order of precedence was applied. Rule 3 joins records with the same title, first author and year even if one is a thesis or a communication at another conference (G04, G05, G20, G26); rule 4 joins records with the same journal, volume and first page (G10, G20); rule 5 was applied when the preprint and the published version share a title (G31) and not when the title changes (G16).
- Pending: in G34 the note says "other authors", but the two authors of G34-01 (Adhiyanti and Rahadiyanto) appear in the list of G34-03 and G34-04; what changes is the first author.

## Closure of phase 1 (2026-10-13, 16:22 Colombia time)

- G34 note corrected with reviewer_2's authorisation: "other authors" becomes "different first author" in the four records; the decision is maintained. Details in adjudication/partition_corrections_2026-10-13.csv.
- 14_close_partition.py: 10 groups resolved by consensus; key opened. The 212 records of the 34 groups end up in 72 works; 18 records with a doubt go to full text (EC12).
- 12_define_corpus.py: 47,960 records, 22,403 works, 25,557 duplicates removed. Representative with an abstract in 20,467 works.
- PRISMA chain: 51,030 identified − 3,132 consolidated copies (R3) − 316 not incorporated on import (R4) + 62 corpus records without a counterpart = 47,644 imported; + 316 recovered = 47,960 entering deduplication; − 25,557 duplicates = 22,403 records for screening.
- List for full text (EC12): 57 entries (39 undecidable pairs whose records remain separate and 18 records with a doubt in the partition).
- Verification of the outputs: one representative per work; the RIS has 22,403 records with a unique identifier, equal to the set of representatives; no SAME_WORK pair remains separated outside the partitioned groups; wherever a work has a record with an abstract, the representative has an abstract.

Declared in the manuscript:
- The partition separated 134 L1 pairs (false L1 merges found through chaining, 0.26% of the 51,197 pairs merged by L1), compared with zero in the random audit of 200 pairs. The L1 escalation was not applied, by the decision of 12:48.
- With the complete group in view, the partition reversed 39 previous human judgements at pair level (35 same-work judgements that ended up separated and 4 different-works judgements that ended up joined) and resolved 3 undecidable pairs by joining them.
- Partition agreement: kappa 0.8912 on the final sheets and 0.9322 on the sheets as submitted; the 10 consensus resolutions coincide with reviewer_1's partition; criterion: the manual's order of precedence.

## Closure files (sha256)

- work/chain_partition_consensus.xlsx: 9019e7d320d272fb104811866775eba303eb8e2fa4728003195179141f972568
- work/chain_partition_final.csv: 83e88dd0f3d2cafb8ec1b61bf77926816f06434420c36dc6afee17f43efe790c
- work/chain_partition_result.txt: f6ffe405b9b15f4e833bc597d47d48b7dd3539c71b6d56f2d5de74c20bfc595c
- work/pair_decisions.csv: ed96fbaeebb9f8026f8df6340e70033126c54621931691347af24b669558aaa1
- work/corpus_clusters.csv: 09158ded222ec8c4ea893ce1f874d79d3adfd2d0d854ec47340bf65f3365e397
- work/undecidable_EC12.csv: 54e2812af4ea3fb2daaf1eddb7e2aebc2fa7e43cbebe84dd50a7d430c94fc9da
- results/screening_corpus_phase1_n22403_2026-10-13.ris: 63c2334e755ece3efcaddcb697cf5b133de3e1cacf05788f5194ec2961fcf9be
- results/corpus_definition_report_2026-10-13.txt: 7ff21bd5e57da800e5abc593546dab2f1d258ff5e668bfd52f40a58e5aef5e90

## Pending items closed (2026-10-13, 16:38 Colombia time)

Approved by reviewer_2 as a block ("go ahead with everything that is pending").

- Reconciliation residual (rule R5): the 62 records have a counterpart in the exports under another key (57 with the DOI only in the export, 5 with a different year). No unexplained residual remains. The v2 reconciliation figures do not change; the explanation is recorded in the project's rules document.
- Phase 1 metrics and comparison with Rayyan: plan written before calculating (adjudication/metrics_plan_phase1_2026-10-13.md, with a declared addendum) and report in results/phase1_metrics_report_2026-10-13.txt.
- Not-incorporated segment: reported separately from the metrics, descriptively.
- Phase 2 calibration: sample of 200 works drawn with seed 13102026, declared before the draw; plan and instructions for import into Rayyan in 04_phase2_calibration/.
- PROSPERO amendment: draft in English in 00_protocol_and_registration/amendments/, pending review by the team.
- Project counting rules document: final figure of the chain and explanation of the residual added.

## Files (sha256)

- 02_phase0_raw_corpus/reconciliation/investigate_residual_v2.py: 208a57f36c609b7d46b098fb346315c99f38e9277b01bb8ea714e1c667121d7c
- 02_phase0_raw_corpus/reconciliation/reconciliation_residual_explained_v2_2026-10-13.csv: 907025790b90d512c79b1c769d762c066f3ce6937e18368e7ec3a9ea2b9ef3c2
- 03_phase1_deduplication/adjudication/metrics_plan_phase1_2026-10-13.md: e577b43b71cd99ed36579ddbd4af617b7e46b5871031824af730c8c254d80cb3
- 03_phase1_deduplication/algorithm/15_phase1_metrics.py: af41e52f60b8895db981109424b8884dc8b4545deb9590d7091f449d2830f761
- 03_phase1_deduplication/results/phase1_metrics_report_2026-10-13.txt: 0873010ecda72ce81e78bbe2c16f9773eab32c336fd8af7254e12a7d1a0790a5
- 03_phase1_deduplication/results/phase1_metrics_2026-10-13.csv: a59d536981a69ee720ed9872642210c067b61419bc82e2b6c2c8d0a0f3c9d23e
- 03_phase1_deduplication/results/rayyan_lost_works_2026-10-13.csv: b173b4993914dfc806ce6ac9ef8d54256a49dcf9a42e09adeb21c3f28e6d3bce
- 04_phase2_calibration/calibration_plan_2026-10-13.md: 587acd7218791d8c77921899ab0b47a7e7ce423cd150b1796d4261095b1bcea0
- 04_phase2_calibration/draw_calibration_sample.py: 1b5c0e752c6b5e22905e2961f2b25d82f32202c14e7916d3e368b711c9f2e145
- 04_phase2_calibration/calibration_sample_200_seed13102026.ris: adc9abb0b76cad2ba2fbd0cbf7dccf381f03a54e525ee23e924d2bd58a4a984a
- 04_phase2_calibration/calibration_sample_200_seed13102026.csv: 4785903623246d1096e64ff255aaba14e531603b177fb59fee88ade9d3650c86
- 00_protocol_and_registration/amendments/PROSPERO_amendment_1_draft_2026-10-13.md: 86613eb79b9d41efd0256cc2a073228cd56e6e9c5c9302dc22ff0e78f03c2e09

- Wording correction of the metrics report (16:39): the phrase "análisis sensibilidad" becomes "análisis de sensibilidad" (sensitivity analysis) in the report and in the CSV. The figures are identical; the previous versions remain in results/_superseded. New sha256: 15_phase1_metrics.py c8538a705ed31d4f1438e730bd04ac86027ef2a27c2ca2ed9ef35fd89eacd537; phase1_metrics_report_2026-10-13.txt 9e3f9534cb8bdd23f4907425ec4287aac6147a85c65ffa075ff19b9393ed6b76; phase1_metrics_2026-10-13.csv 857414d9bc8a8d450317c91312d8ab76d7e7b498a3841510e708b1e7cd9b6453; rayyan_lost_works_2026-10-13.csv unchanged.

- Clarification on the false L1 merges (16:40), which corrects the wording of the section Closure of phase 1: of the 134 L1 pairs that the partition separated, 34 are different works by firm judgement and 100 involve a record that was kept separate because of a doubt, without being confirmed as a different work (1 of them from the development set). The confirmed false L1 merges in the main workflow are 148: 114 by rule RC-1 and 34 by the partition, 0.29% of the 51,066 L1 pairs, all found through non-random routes. This is the figure declared alongside the random audit of 0 in 200.

- Clarification on Wanfang Data (16:45): the WAN-1 search was indeed run on 2026-09-11 (1,609 records, according to the search strategy and the master document) and was not retrieved, as the registered protocol states. The .txt file saved in 01_search/exports/Wanfang_Data/ is the VIP export in another format: its 159 records link to cqvip.com and name VIP as the provider. The row of 01_search/prisma_s_log.csv that attributes it to Wanfang Data is a recording error; the input file is not edited and the correction is recorded here and in the project's rules document.
