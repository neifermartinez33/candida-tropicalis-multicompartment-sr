# Reviewer guide: eligibility criteria for workbook B15

Temporary aid for the re-reading of workbook B15 (`r4_b15_ast_exclusions_rescreen.xlsx`); to be deleted
when the reading is finished. The criteria are copied from the frozen full-text screening manual
(File S1, `full_text_screening_instruction_EN.md`) and from the team decisions of 2026-10-24 (rule I1).

## Inclusion criteria

- **IC1** The organism of interest is *Candida tropicalis*. (A study of *Candida* spp. meets IC1 if the
  *C. tropicalis* data can be disaggregated: number of isolates and results for the species.)
- **IC2** The study states the species identification method.
- **IC3** It specifies the source of recovery precisely enough to assign it to one of the six compartments.
- **IC4** It reports an antifungal susceptibility profile, molecular resistance determinants, genotype or
  clade assignment.
- **IC5** Recoverable denominators: total number of *C. tropicalis* isolates and their breakdown by
  compartment and by antifungal agent tested.
- **IC6** Geographical origin identifiable at country level.
- **IC7** Original article derived from primary research.
- **IC8** It states the interpretive criterion and, if it reports resistance categories, allows the document
  and version of the standard applied to be identified (for example CLSI M27-A3, M27-S4, M60, EUCAST
  E.Def 7.3), or it reports individual MICs or their distribution.

**Rule.** INCLUDE if it meets IC1, IC2, IC5, IC6 and IC7 and at least one of IC3 or IC4.
**Meta-analysis.** In addition, IC4 with denominators broken down by antifungal agent, and IC8. Reports
that meet the general rule but not IC8 enter the review (distribution analysis, SQ1) but not the pooled
estimates.

**Rule I1 (team decision, 2026-10-24).** EC6 and EC7 are read as criteria on the susceptibility data: a
report without those data is not excluded by them and enters SQ1 (`INCLUDE_SQ1`).

## Compartments

| Code | Compartment | Sources |
|---|---|---|
| C1 | Human host | Invasive and non-invasive clinical samples; cutaneous and mucosal colonisation; carriage in occupationally exposed healthy populations |
| C2 | Animal host | Domestic, production, wild and captive animals |
| C3 | Agroecosystem | Agricultural soil; fruit and fruit surfaces; cultivated vegetation; irrigation water |
| C4 | Inanimate healthcare environment | Surfaces, furniture, equipment and devices in healthcare settings |
| C5 | Natural environment without management | Wild soil; sediment; fresh and marine water; uncultivated vegetation; hypersaline matrices |
| C6 | Anthropogenic matrix without attributable regimen | Urban and hospital wastewater; beaches and coastal waters receiving discharge; periurban soil with effluent; sludge |

## Exclusion criteria

- **EC1** The species is not the organism of interest; it appears as an incidental finding within series of
  *Candida* spp. without disaggregable data.
- **EC2** The species identification method is not stated.
- **EC3** Geographical origin not identifiable at country level, or attributed only from the authors'
  affiliation.
- **EC4** Source of recovery not specified or not assignable to any compartment.
- **EC5** Not an exclusion: a matrix with documented anthropogenic input without an identifiable azole
  regimen is classified as C6.
- **EC6** Neither the susceptibility method nor the interpretive criterion is stated, and no MICs are
  reported. (Rule I1: it removes the susceptibility data, not the report.)
- **EC7** Denominators not recoverable, or aggregated data that cannot be disaggregated. The correct
  denominator is the number of isolates actually tested against each antifungal agent. (Rule I1: when it
  concerns only the susceptibility data, the report still enters SQ1.)
- **EC8** Uses only international reference strains without any isolate of documented origin.
- **EC9** Focused on the antifungal activity of new compounds, plant extracts, essential oils,
  nanoparticles, metal complexes, peptides, disinfectants or combinations, whose only measurement is the
  efficacy of the agent tested, without characterising the resistance profile against conventional
  antifungal agents.
- **EC10** The species as an industrial or biotechnological organism (xylitol, ethanol, organic acids,
  bioprocesses) unrelated to antifungal resistance.
- **EC11** Computational or in silico contribution only, without isolates.
- **EC12** Cohorts or collections duplicated or overlapping between publications of the same surveillance
  programme, institution and period. Do not exclude for EC12 here: record the programme or institution and
  the period in `comment`; overlaps are resolved later.
- **EC13** Systematic reviews, meta-analyses, narrative reviews, clinical guidelines, editorials, letters and
  commentaries without primary data; conference abstracts without extractable data. Preprints are not
  excluded.

When several exclusions apply, record the most decisive one, in this order of priority:
EC13, EC10, EC11, EC9, EC8, EC1, EC7, EC3, EC4, EC2, EC6.

## From the criteria to the workbook columns

| Situation | `decision` | `ec_code` |
|---|---|---|
| An exclusion applies (other than EC6 or EC7 on the susceptibility data only) | `EXCLUSION_CONFIRMED` | the most decisive code |
| Meets the general rule; no susceptibility data usable for pooling (no IC8, or no denominators by agent) | `INCLUDE_SQ1` | empty |
| Meets the general rule, IC4 with denominators by agent and IC8 | `INCLUDE_MA` | empty |
| The PDF is another work, truncated or unreadable | `NOT_RETRIEVED` | empty |

`has_ast_tropicalis` is `YES` whenever the report gives susceptibility results of its own for
*C. tropicalis* isolates (MICs, categories or counts), whatever the decision.
