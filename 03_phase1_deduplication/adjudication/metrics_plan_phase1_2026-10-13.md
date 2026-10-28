# Plan for the phase 1 metrics

*Candida tropicalis* review. Written on 2026-10-13 at 16:30, Colombia time, before calculating any metric. It develops section 5.8 (and 5.4 for Rayyan) of the Methodological Approach v4, which sets the metrics but not these operational details. When it was written, the closing tables of each queue (human judgement versus the model) and the result of the partition were already known; for that reason each decision is fixed here and declared as made after seeing those tables.

## Population

- Candidate pairs of the main workflow excluding the development set (section 5.6): 77,303 pairs.
- The not-incorporated records segment is reported separately and only descriptively: the model was not run on it and its records are selected for not matching the corpus by key.

## Reference standard

- Pair with a human judgement or a rule: pairs of the L3/L4 queue, of the L1 audit, of the L2 sample, of rule RC-1 and all pairs within the partitioned groups. Their reference is the final status: same work if the two records end up in the same work.
- Unresolved pairs are excluded from the binary metrics and reported separately: an UNDECIDABLE decision that ends with the records separated, and pairs of a partitioned group in which either of the two records has a doubt.
- Pairs without human reading: the rest of L1 and the rest of L2. Their reference is imputed from the random samples: the L1 audit (0 of 100 false merges in each DOI stratum) and the L2 sample (0 of 1,000 duplicates). The point estimate is same work for the rest of L1 and different works for the rest of L2.

## Classification of each procedure

- Algorithm: positive DUPLICATE, negative DIFFERENT, abstention the zone between thresholds.
- Model: positive SAME_WORK, negative DIFFERENT_WORKS, abstention UNDECIDABLE.
- Main analysis: abstention counts as non-positive, because on its own it never produces a merge.
- Sensitivity analysis: abstentions excluded from the denominator of each procedure. The abstention rate is reported.

## Metrics

- Sensitivity, specificity and positive predictive value with exact 95% Clopper-Pearson intervals on the reconstructed counts. These intervals do not include the imputation uncertainty; for it, the worst case within the sample intervals is reported: false merges in the rest of L1 at the upper limit of the audit in each DOI stratum and duplicates in the rest of L2 at the upper limit of the sample.
- Paired comparison between algorithm and model with the exact McNemar test on the pairs with a determined reference.
- Cohen's kappa between algorithm and model on the 77,303 pairs (positive versus non-positive).

## Rayyan (section 5.4)

- It is evaluated at record level on the 47,644 records that Rayyan processed; the 316 recovered records are not included. The reference is the final works of phase 1.
- In each work with k records kept and d deleted: if k is at least 1, one kept record is a true negative, k minus 1 are undetected duplicates and the d deleted records are true positives; if k is 0, the work was lost entirely: one deletion is a false positive and d minus 1 are true positives.
- Magnitudes of section 5.4: works deleted completely (studies removed without reason, with their records) and pairs of kept records that are the same work (duplicates that Rayyan did not detect).
- Pair-level sensitivity and specificity are not identifiable for Rayyan, because its export does not state against which record it deleted each one.

## Other prespecified magnitudes

- L1 audit and L2 sample with their exact interval, and projection of the missed duplicates onto L2.
- Duplicate rate of the candidate space with the development set, weighting each blocking-key stratum by the inverse of its sampling fraction (section 5.6), on the decidable pairs; the undecidable ones are reported separately.
- Inter-reviewer agreement for each queue, taken from the closing results.

## Addendum (16:34, after the test run and before writing the outputs)

- A non-prespecified check of the works that Rayyan deleted completely is added. The test run showed that many share the normalised title with a work that keeps a record; in that case the study may remain in the corpus through the other document. Each lost work is classified according to how phase 1 separated it from the surviving work with the same title (RC-1, human judgement of the pair, partition, undecidable, L2 only) or whether there is none. It is reported as a check, not as a metric.
- No other definition of the plan changes.
