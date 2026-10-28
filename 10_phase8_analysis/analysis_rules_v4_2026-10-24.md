# Analysis rules v4: synthesis of resistance proportions (SQ2)

*Candida tropicalis* review, PROSPERO CRD420261486387 (version 2.0, 2026-10-15).
**Fixed on 2026-10-24, after the pre-drafting audit and before re-running the pipeline.** They supersede `analysis_rules_v3_2026-10-22.md`, which is not deleted. Warning about v3: the file on disk (MD5 `3a5fbb5b14eaafda96de6607696c12b1`) is the version prior to the 2026-10-22 amendment and is the one cited by the nine logs of 2026-10-23; the amended text remained only in the Project. This v4 incorporates the amendment and corrects it; the MD5 of this file is recorded in the log of each script that reads it. Any future change goes into a v5, dated, with its reason.

To be read together with `09_phase7_risk_of_bias/rob_rules_v3_2026-10-24.md` (phase 7) and `10_phase8_analysis/team_decisions_2026-10-24.md` (decisions D1 to D6 and the team's pending items).

**Protection against decisions made after seeing the data.** All new rules in this version were written after seeing Tables 3 and 4 of 2026-10-23 and before computing anything with them. None is chosen for the result it produces; those that change the selection of rows have a sensitivity analysis that undoes the change (SX1, SX3, SA1), and all are listed in the table of deviations (section 10).

## 0. What changes with respect to v3, and why

1. **Scope (D1).** The first article answers SQ1 (distribution by compartment) and phenotypic SQ2 (proportion of non-wild type by ECV and of resistance by clinical breakpoint). Molecular SQ2, SQ3 to SQ7, H1 to H5 and the MIC distributions are left for a second report, declared before seeing those results. C1 enters as the comparator.
2. **Analysis dataset v3 with the round-2 verification (D2).** It supersedes v2 without deleting it: R stream matched to its screening record, programme collections decided by the team, doubtful records and extraction exclusions decided report by report, rows of pooled strata verified against the PDF.
3. **EC6 and EC7 refer to the susceptibility data.** A report without susceptibility data is not excluded by them: it enters SQ1 if it meets the remaining criteria (via `INCLUDE_SQ1` of workbook B09).
4. **Rows that do not estimate prevalence (D3): AR20, new.** Excluded from the main analysis; SX3 reincorporates them.
5. **C5 returns to the registered hierarchy:** strict reading in the main analysis, broad reading in SA1. Deviation 5 of v3 is withdrawn.
6. **Rule 1 symmetric across all agents** (previously only for fluconazole), with declared breakpoints, revision markers, document and year read in the agent's clause, and separation between method and criterion when a single string names both CLSI and EUCAST.
7. **Rule 4 applied:** the resistance row without a declared version and without MICs is excluded.
8. **D4: applicability matrix by document or version and agent**, which replaces AR8.
9. **AR10 v4:** disjoint subsets of the same report are summed when there is no total row.
10. **Corrected sensitivity analyses:** 7-node quadrature in all single-level fits, estimability by AR12 and AR18 at each level, SA7 on the regime field, SA11 with its Laplace comparator, AR2 recomputed within each subset, seeds by key.
11. **AR21, new:** exploratory meta-regression with covariates unrelated to the deferred hypotheses.
12. **Provisional mode:** the whole pipeline runs with the missing team decisions replaced by the mechanical proposals, and every output carries `_PROVISIONAL` in its name and in its title. Nothing provisional goes into the manuscript.

## 1. Unit of analysis: independent collection (EC12)

- **AR1.** Two reports are the same collection if (a) they belong to the same candidate group in `collection_candidates.csv` (same institution or programme and same country) and their collection periods overlap, or (b) the team declared them the same collection in workbook B03 (`YES` or `PARTIAL`), which contains the pairs from named programmes (CHIF-NET, CANDIPOP, NRZMyk, SENTRY, ARTEMIS and similar) even when they are in different candidate groups. The transitive closure is taken. A report without a period, or outside every group and pair, is a collection of its own. In provisional mode, B03 pairs without a decision count as different collections.
- **AR2.** In each stratum only one report per collection enters: the one with the largest number of isolates tested against the agent; if tied, the most recent, and then the lowest identifier. The others are secondary. SA3 treats each report as independent. In the analyses that remove rows (SA1, SA2, SX1, SX2, SX3), AR2 is recomputed within the subset: if the main report of a collection leaves, the next one from the same collection enters.

## 2. Strata

- **AR3.** Compartment × agent × outcome × interpretive regime (AR5 and AR6).
- **AR4.** C5 enters under the **strict reading** (documented absence of agronomic management, `c5_definition_v3 = strict`) in the main analysis. C5 rows that meet only the broad reading enter only SA1. If the strict reading does not reach AR12, H2 is not estimable and SQ5 is described narratively. C6 is descriptive and does not enter contrasts.

## 3. Outcomes and regimes

- **AR5. Primary: non-wild type (NWT) by ECV**, as declared by the study. Only rows with *n* NWT whose ECV source is CLSI or EUCAST, alone or together with that of the manufacturer or of the author; those that cite both standards, or neither, are excluded. Regime: CLSI ECV or EUCAST ECV, never pooled with each other. Caspofungin is excluded (no ECV).
- **AR6. Secondary: resistance (R) by clinical breakpoint (CBP)**, according to the standard declared by the study. Categories without a declared breakpoint type count as CBP (operational clarification; SX2). The regime of each row is assigned by `verification_rules_v1.row_regime`, in this order:
  1. **Standard.** If the string names both CLSI and EUCAST, the method is separated from the criterion: what counts is the standard of the clause that gives the breakpoints for that agent (for example, "EUCAST method, CLSI breakpoints" is CLSI). If they cannot be separated, the row is excluded (`mixed_standard`). EUCAST only: EUCAST regime.
  2. **Declared breakpoints (Rule 1).** If the string declares the agent's breakpoints, the regime is that of the document that published those breakpoints (fluconazole S ≤ 2, SDD 4, R ≥ 8 is species-specific; S ≤ 8, SDD 16–32, R ≥ 64 is pre-2012). Flag `inferred_from_cutoffs`.
  3. **Revision markers** in the agent's segment ("revised breakpoints", "Pfaller 2011", "M27-S4"…), only for the agents revised in 2012 (fluconazole, voriconazole, echinocandins).
  4. **CLSI document** of the agent's clause or, if it has none, of the whole string: after the 2012 change (M27-S4, M60, M27 4th ed., M27M44S, M44 3rd ed.) → species-specific CLSI; before it (M27-A to M27-A3, M27-S3, M44-A, M44-A2, M44-S3) → pre-2012 CLSI. An earlier document in a report published from 2013 onwards is flagged `pre2012_doc_published_2013plus`; M27-A3 alone, in that situation, is ambiguous between S3 and S4 and is therefore included in the flag. "M44" without a version does not identify a document.
  5. **Year written in the string** (Rule 1): the document in force in that year.
  6. **Publication year ≤ 2012:** pre-2012 CLSI, flag `inferred_from_year`. After 2012 without any of the preceding bases: version not inferable, excluded.
- **Rule 4 (protocol).** The resistance row whose version is not declared in any form (bases `publication_year` in CLSI and EUCAST without version) and which provides no MIC with which to remedy this is excluded from the pooled estimates.
- **AR7.** Only for fluconazole are species-specific CLSI and EUCAST pooled (matching R threshold, ≥ 8 mg/L): stratum `CLSI_SS+EUCAST`. No other pair of regimes is pooled.
- **AR8 (replaced by D4).** A resistance row enters only if the document or version applied by the study published a clinical breakpoint for *C. tropicalis* and that agent. This is decided by the matrix `10_phase8_analysis/applicability/cbp_applicability_v1_2026-10-24.csv`, built by `build_cbp_applicability_v1.py` from `breakpoint_history_2026-10-24.csv` with the source of each cell (primary or secondary). Values:
  - `YES`: it published a CBP for the species and the agent → the row enters.
  - `NS_only`: the document published only the susceptible category (CLSI M27-S3 for echinocandins, S ≤ 2; M44-A2 and M44-S3 for caspofungin) → there is no resistance stratum.
  - `NO` or `IE`: no CBP, or insufficient evidence → excluded.
  - `UNVERIFIED`: the value could not be confirmed in any source (M60 and M44 3rd ed. zones for the species, CLSI without document or year) → excluded, and counted.
  Rows without a declared document are placed by the year in which the breakpoints were applied (written year or, failing that, publication year), using the validity window of each document or version (EUCAST with decimal dates). Itraconazole under pre-2012 CLSI has a CBP for *Candida* spp. only for mucosal candidiasis (Rex et al. 1997): the matrix codes it `YES` with a note and the team must confirm it (pending item P4 of the decisions). The ECVs of M59 and M57S are not clinical breakpoints (`NO`).
- **AR9.** Biofilm rows and rows with an undeclared method are excluded.

## 4. Row selection

- **AR10 v4.** One row per report × compartment × agent × outcome × regime. If there are several: (1) the method (reference microdilution, commercial, gradient, disc, others); (2) for species-specific fluconazole with a CLSI row and a EUCAST row for the same isolates, the one that corresponds to the method; (3) if the remaining rows are **disjoint subsets** of the same report (different periods, sources or centres, same method and criterion) and none is the total, events and isolates **are summed**, and the sum is recorded in `ar10_sums_v2`; (4) otherwise, the row with the most isolates tested; (5) the lowest row identifier.
- **AR11.** The denominator is the number of isolates tested against the agent (EC7).
- **AR20 (D3).** Rows that do not estimate prevalence are excluded from the main analysis: (a) samples selected by phenotype (for example, only resistant or non-susceptible isolates sent to a reference laboratory), (b) denominator inferred by the extractor and not reported by the study, and (c) sets compiled from the literature or from public databases (SRA genomes, collections assembled from other studies). The mechanical proposal (`verification_rules_v1.d3_proposal`) is confirmed by the team in workbook B04. SX3 reincorporates them. Partial coverage and case designs are not AR20: they follow the registered route of RB1, RB3 and SA9.

## 5. Minimum condition and research groups

- **AR12.** At least 5 independent collections from at least 2 research groups (protocol §9). If this is not met, the stratum is described collection by collection.
- **AR13. Research group** (declared approximation): candidate group, or the first institution of `programme_institution_raw`, normalised, or the report itself.

## 6. Model, estimation and intervals

- **AR14.** Binomial-normal GLMM, logit, random intercept per collection: `lme4::glmer(cbind(events, non_events) ~ 1 + (1 | collection), family = binomial, nAGQ = 7)`, with *τ*² by maximum likelihood; `meta::metaprop(method = "GLMM", sm = "PLOGIT")` gives the median and the prediction interval.
- **AR15. Main estimate: population (marginal) mean**, the mean of logit⁻¹(μ̂ + σ̂*z*) over the standard normal with 4,096 quantile nodes. 95% CI by percentile parametric bootstrap (`bootMer`, 999 replicates). **The seed of each stratum is derived from its key** (not from its position), so that adding or removing strata does not change the others.
- **AR15 bis. Supporting quantities:** the median (back-transformed pooled logit) with CI by *t* with *k* − 1 df on the standard error of the GLMM (what `meta` calls "HK" in a GLMM; it is not Hartung-Knapp); the Higgins, Thompson and Spiegelhalter prediction interval with *t* on *k* − 2 df (`meta`: "HTS"); the crude proportion with its exact binomial CI.
- **AR16 (D5).** The main analysis is single-level; collection nested in country is SA11 in every pooled stratum.
- **AR17. Reported per stratum:** *k*, groups, events and isolates, crude proportion with exact CI, population mean with CI, median with CI, prediction interval, *τ*² with profile-likelihood CI, percentage of the largest collection and rows flagged for SX1. *Q* and *I*² go to the supplementary material, with the caveat that `meta` computes them with the inverse-variance formulation.
- **AR18. Strata that are not pooled.** While meeting AR12, there is no estimate when (a) all collections are at the boundary (no events, or all events), (b) the upper limit of the profile CI of *τ*² exceeds 25, or (c) the profile cannot be obtained. *k*, groups, events, isolates, the crude proportion with its exact binomial CI and the range across collections are reported, **in the table**.
- **AR19. Comparisons between strata.** No contrast is obtained by subtracting rows of Tables 3 or 4, either in the analyses or in the text. Every contrast between two levels of a factor (SA4, SA5, SA7, SA8) gives two quantities with different names: the **contrast on the logit scale** and the **difference in population means**, the latter with a parametric bootstrap CI.
  - **Unpaired** (each collection in a single level): the model with level-specific variances has a separable likelihood, so it is fitted as two single-level GLMMs with 7 nodes; the standard error of the contrast is the square root of the sum of the squares (zero covariance) and the CI of the difference comes from two independent bootstraps.
  - **Paired** (SA5): common random intercept per collection and outcome as a fixed effect, 7 nodes; the contrast is within collection.
  - **Estimability:** each level must meet AR12 and AR18 on its own (in SA5, AR18 on the common variance). Otherwise, the cell is reported with that status and without figures.

## 7. Sensitivity analyses

Pre-specified and run: SA1, SA2, SA3, SA4, SA5, SA7, SA8, SA9, SA10 and SA11. Not run: SA6 (requires reinterpreting MIC distributions that were not extracted) and SA12 (C3 has no dominant corpus to remove). Not pre-specified, declared: SX1, SX2 and SX3.

**Refit family** (`09a_sens_refit_v3.R`). Each analysis changes one decision, reapplies AR12 and AR18, and forms its strata in its own subset. Strata of the main analysis that do not reach AR12 in the subset are reported with that status.

| Analysis | What changes | Comparator |
| --- | --- | --- |
| SA1 | C5 under the broad reading | population mean of the main analysis |
| SA2 | without preprints (`editorial_status = preprint`) | same |
| SA3 | each report as an independent unit | same |
| SA9 | without the collections whose main report is at high risk (registered phase 7 rule) | same |
| SA10a | inverse-variance logit, continuity correction 0.5, DL *τ*² | **median** of the main analysis (the back-transformed value is median-type) |
| SA10b | Freeman-Tukey double arcsine, inverse variance | **median** of the main analysis; a back-transformed value equal to zero is reported as not estimable (Schwarzer et al. 2019) |
| SA11 | collection nested in country, Laplace; each multinational collection is its own country group | single-level model with the **same Laplace approximation** |
| SX1 | without rows flagged `pre2012_doc_published_2013plus`, `inferred_from_year` or `inferred_from_cutoffs` | population mean of the main analysis |
| SX2 | without rows with `bp_type = CBP_assumed` | same |
| SX3 | with the AR20 rows | same |

In SA10a, SA10b and SA11 only the strata that meet AR12 in the main analysis are fitted, and each row carries the status from the main analysis: a stratum not pooled there is reported as such even if the alternative estimator gives a number, because those estimators cannot reapply AR18. The difference from the comparator is given only when both pool the stratum.

**Contrast family** (`09b_sens_contrast_v3.R`), per AR19:

| Analysis | Levels | Cell |
| --- | --- | --- |
| SA4_R | species-specific CLSI versus EUCAST, resistance | compartment × agent; AR2 within each regime |
| SA4_NWT | CLSI ECV versus EUCAST ECV | compartment × agent |
| SA5 | NWT versus R of the same standard (CLSI ECV with CLSI CBP; EUCAST ECV with EUCAST CBP), paired | compartment × agent × standard; only collections with both outcomes |
| SA7 | species-specific CLSI versus pre-2012 CLSI | compartment × agent; **by the `regime` field**, so that for fluconazole the CLSI rows of the combined stratum enter |
| SA8 | molecular or MALDI-TOF identification versus phenotypic identification | stratum; collections with unspecified identification are excluded |

In SA9 a stratum that falls below AR12 is reported as not estimable, not as a change in the estimate; since most of the RB8 "No" ratings are `not_declared`, SA9 measures reporting quality rather than the direction of bias, and it is written up as such.

## 8. Exploratory meta-regression

- **AR21.** Exploratory, to describe heterogeneity (protocol §9). Only strata pooled in the main analysis, with at least 10 collections with data on the covariate. One covariate at a time: susceptibility method, WHO region, overall risk-of-bias judgement of the main report (high versus not high), species identification method (molecular or MALDI-TOF versus phenotypic; unspecified treated as missing data) and editorial status. Compartment (H2), clade (H1), period and criterion version (H4) are not used: they belong to deferred hypotheses (D1). Levels with fewer than 3 collections are grouped into "other levels"; if only one usable level remains, the model is not fitted. Model: single-level GLMM with the covariate as a fixed effect, 7 nodes; the coefficient for each level versus the most frequent level, the likelihood-ratio test against the model without the covariate and the relative reduction in *τ*² are reported. No correction for multiplicity; the number of tests is reported. The coefficients describe association across collections, not effect.

## 9. Outputs and software

- **Table 2** (`03_tab02_characteristics_v2.py`): characteristics by collection (representative report: largest *n*, most recent, identifier).
- **Table 3** (`07_tab03_v2.py`): C1, both outcomes; **Table 4** (`08_tab04_v2.py`): C2 to C6, strata with at least two collections.
- **Figure 1** (`20_fig01_prisma_v4.R`, from `prisma_counts_v3`), **Figure 2** (`21_fig02_evidence_map_v2.R`, by collections), **Figure 3** (`22_fig03_forest_c1_v2.R`).
- **Supplementary:** S1 heterogeneity, S2 inventory of strata, S3 non-clinical strata (`10_tabS_supplementary_v2.py`); S4 refit and S5 contrasts (`11_tabS_sensitivity_v2.py`); S6 included, S7 excluded with reason, S8 risk of bias, S9 D4 matrix, S10 meta-regression, S11 not retrieved versus assessed (`13_tabS_lists_v1.py`).
- **Software:** R 4.5.3, meta 8.5-0, metafor 5.0-1, lme4 2.0-6; Python 3.12, pandas 3.0.6. One script per output; log with the MD5 of inputs and outputs; no output is overwritten. Every number in the manuscript comes from the final CSV of the FINAL run.

## 10. Deviations from the registered protocol (declared in the Methods)

| No. | Deviation | Reason | Since |
| --- | --- | --- | --- |
| 1 | Minimal human verification (D2) rather than duplicate verification of everything: rows of pooled strata, doubtful records, extraction exclusions and a 20% blind sample of excluded records with agreement | volume of the corpus; declared with the agreement in the sample | v4 |
| 2 | Collections by deterministic rule plus human decision on the programme pairs (B03); non-identifiable overlap may remain | no isolate identifiers | v2, v4 |
| 3 | Risk of bias assessed after the primary synthesis and by a partial route | see `rob_rules_v3` | v2 |
| 4 | Primary outcome without reinterpretation of MIC distributions | they were not extracted | v2 |
| 5 | (withdrawn in v4: C5 returns to the registered strict reading) | — | — |
| 6 | Research group approximated by the declared institution (AR13) | it was not extracted | v2 |
| 7 | Stratification by interpretive regime for all agents, instead of the version as a covariate | thresholds change between versions | v2 |
| 8 | Applicability of CBPs by document or version (D4), with a matrix built on 2026-10-24 before re-running | Table 5 of the protocol does not distinguish versions | v4 |
| 9 | Population mean as the main functional, chosen after the v1 run | the median departs from the data when many collections are at zero | v2 |
| 10 | Threshold of 25 in AR18b fixed after seeing the *τ*² profiles of v1 | identifiability of *τ*² | v2 |
| 11 | AR19 fixed after producing Tables 3 and 4 | marginal means mix location and heterogeneity | v3 |
| 12 | SX1, SX2 and SX3 not pre-specified | assumptions of the extraction and of AR20 | v3, v4 |
| 13 | AR20 written after seeing results (D3); SX3 undoes it | denominators conditioned on the outcome | v4 |
| 14 | Rule 1 extended: declared breakpoints, separation of method and criterion, the agent's clause | v3 applied it only to fluconazole | v4 |
| 15 | AR10 sums disjoint subsets without a total row | v3 discarded isolates from different periods | v4 |
| 16 | Scope of the first article: SQ1 and phenotypic SQ2 (D1) | volume; the rest is declared for a second report before seeing its results | v4 |
| 17 | *τ*² by maximum likelihood (registered: REML or Paule-Mandel) and without Hartung-Knapp, which does not apply to the GLMM | the GLMM has no REML in `lme4`; the CI of the median uses *t* with *k* − 1 df | v4 |
| 18 | EC6 and EC7 read as criteria on the susceptibility data: reports without those data enter SQ1 | consistency with SQ1 | v4 |
| 19 | Phases 1 to 6: language-model safety net without output; citation tracking, PubMLST and seed set not run; contact with authors and interlibrary loan ruled out by the group; full title and abstract pass without kappa or retained arbitrations | decisions of the group and records not retained | v4 |
| 20 | Round-2 phase 7 (150 new reports): one reviewer and one verifier, not two independent reviewers | see `rob_rules_v3`, deviation 16 | v4 |
| 21 | PROSPERO amendment: the deviations are declared in the manuscript with their table; submission of the amendment is decided by the team (D6) | contradiction between deviation 15 of the risk-of-bias rules and the decision of 2026-10-16 | v4 |
