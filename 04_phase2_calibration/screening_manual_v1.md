# Criteria application manual: title and abstract screening

Review: *Multicompartment distribution and dynamics of the antifungal resistome of Candida tropicalis, with emphasis on the azole-resistant clade 4*.
Version 1, frozen on 2026-10-16. Written on the basis of calibration CAL1 (200 works, seed 13102026).

This manual does not change the registered criteria (section 5 of the protocol; literal text in the annex). It sets how they are applied with the information in a title and an abstract. It is the single instruction for the two human readers and for the language model.

## 1. Decision

1. Each work receives one of two decisions: **Include** or **Exclude**. "Maybe" is not used.
2. Include means passing to full text; it does not mean that the work is eligible.
3. When excluding, the code of the criterion that excludes it is recorded (EC1 to EC4, EC6 to EC11, EC13). In Rayyan it goes in "Reason"; for the human readers it is recommended, not mandatory.

## 2. General rule

1. **A work is excluded only when the title or the abstract shows that an exclusion criterion is met.** If the information is missing or ambiguous, it is a doubt, and doubt is included.
2. The absence of an item in the abstract (identification method, country, source, denominators, interpretive criterion) does not exclude: that is decided at full text.
3. **A work without an abstract is decided by its title** (section 7 of the protocol). The lack of an abstract is never a reason for exclusion.
4. For languages the reader does not master, machine translation is used (section 7 of the protocol). Language, year and journal type do not exclude. Preprints are not excluded.
5. **Mentioning *C. tropicalis* is necessary, but not sufficient.** The criteria of step 2 exclude even if the species appears in the title or the abstract.

## 3. Decision sequence

It is applied in this order; the first rule that excludes decides.

### Step 1. Are there, or could there be, *C. tropicalis* isolates?

- **Include** if *C. tropicalis* appears as the organism studied or among the species isolated or identified (any form of the name, including those in other alphabets).
- **Include due to doubt** if the abstract speaks of "Candida spp.", "yeasts", "non-albicans" or names only the predominant species without giving the complete list.
- **Exclude, EC1**, if the abstract names the species found and *C. tropicalis* is not among them, or if the study deals with a single different organism (for example, a case due to *C. albicans*).
- **Exclude, EC1**, if *C. tropicalis* appears only as a test organism for the activity of another organism or substance, and not as an isolate of the study.
- **Exclude, EC1, with the note "no isolates"**, if the species is only detected without culture (metabarcoding, DGGE, direct PCR on the sample) and the study does not report isolates. The unit of observation of the protocol is the isolate.

### Step 2. Exclusions recognised in the title and abstract even if the species is named

- **EC13.** Systematic or narrative reviews, meta-analyses, guidelines, editorials, letters and commentaries without primary data. A conference abstract is excluded only if it shows that it has no extractable data; if it provides isolates, counts by species or resistance, it is included.
- **EC10.** Process studies with the species as a production or transformation organism: xylitol, ethanol, organic acids, enzymes, biodegradation or optimised fermentations, unrelated to antifungal resistance.
  It does not apply to studies that isolate yeasts from a compartment (soil, sediment, water, plants, flowers, mangroves, animals) and identify *C. tropicalis*, even if their aim is biotechnological (enzymes, carotenoids, plant growth promotion). Those are included, because they report isolates with a documented source.
- **EC9.** Activity of novel compounds, plant extracts, essential oils, nanoparticles, metal complexes, peptides, disinfectants or combinations, when the only thing measured is the efficacy of the tested agent.
  It is included, on the other hand, when the abstract indicates isolates of documented origin (clinical or environmental) and reports their susceptibility to conventional antifungals (azoles, echinocandins, polyenes, flucytosine); for example, fluconazole MICs or isolates characterised as resistant to a conventional antifungal.
- **EC8.** Only reference or collection strains (ATCC, CBS, IFO, NRRL, MTCC or others) and no isolate of documented origin. It includes experimental models (animal infection, immunology, vaccines, gene function) that declare the use of reference or collection strains.
- **EC11.** Only computational or *in silico* modelling, without isolates.

### Step 3. Criteria that are almost never judged on title and abstract

EC2, EC3, EC4, EC6 and EC7 are applied only if the title or the abstract expressly shows that they are not met; for example, an abstract that declares that the origin of the isolates is unknown. In any other case, the work is included and the criterion is judged at full text.

EC4 is additionally applied in two situations established in the calibration:

- **Processed or fermented foods and industrial processing environments**, which do not correspond to any of the six compartments. A raw fruit or vegetable is C3 and is not excluded by this rule.
- **The species as an experimental agent** (animal infection, immunology, vaccines, gene function) without the origin of the strains being specified. If reference or collection strains are declared, the code is EC8.

### Step 4. What never excludes at this phase

- **EC5** is not an exclusion: it is a classification rule towards C6.
- **EC12** (collections overlapping between publications) is applied at full text.
- Lack of an abstract, language, year and preprint status.
- Single case reports are included at this phase if they meet the rest of the manual; their eligibility is judged at full text with the registered criteria.

## 4. Calibration cases that set the application

| Work | Situation | Decision |
|---|---|---|
| O04118 | Ethanol production in co-culture with *S. cerevisiae* | Exclude, EC10 |
| O02837, O04571, O05027 | Xylitol production with *C. tropicalis* strains | Exclude, EC10 |
| O06951, O19295 | Surveys of yeasts in flowers and in trees | Include |
| O07430 | Novel cationic polymers tested against a panel of species | Exclude, EC9 |
| O04720 | Silver nanoparticles on clinical strains; only the activity of the agent is measured | Exclude, EC9 |
| O17065 | Essential oils on fluconazole-resistant isolates; reports their susceptibility to itraconazole and voriconazole | Include |
| O02797 | Disinfectants on yeast biofilms from a juice industry | Exclude, EC9 |
| O03416 | Antigenicity of four IFO strains | Exclude, EC8 |
| O08042 | Yeasts from the fermentation of table olives | Exclude, EC4 |
| O08777 | Endophytes whose activity is tested against *C. tropicalis* | Exclude, EC1 (test organism) |
| O21697 | Fungi from soils of 108 countries detected by sequencing | Exclude, EC1 (no isolates) |
| O20835 | Prosthetic endocarditis due to *C. albicans* | Exclude, EC1 |
| O21052 | "Candida arthritis", without abstract | Include: without an abstract it is decided by the title, and the title does not rule out the species |
| O02566 | Oral colonisation by yeasts; the abstract names only the predominant species | Include due to doubt |
| O06308 | 115 urine strains, 25 of *C. tropicalis*, with MICs | Include |
| O01289 | Identification by MALDI-TOF in blood cultures; 5 *C. tropicalis* | Include |
| O03819 | Conference abstract on virulence that declares having evaluated resistance | Include |
| O12928 | Single case report of *C. tropicalis* fungaemia | Include |

## 5. Works authored by the team

They are screened with the same rules. What changes is who arbitrates, according to the screening plan.

## Annex. Registered criteria (protocol, sections 3 and 5; literal text)

### Recovery compartments

- C1 Human host: invasive and non-invasive clinical, cutaneous and mucosal colonisation, carriage in occupationally exposed healthy population.
- C2 Animal host: domestic, production, wild or captive animals.
- C3 Agroecosystem: agricultural soil, fruit and its surface, cultivated vegetation, irrigation water.
- C4 Inanimate healthcare environment: surfaces, furniture, equipment and devices in healthcare settings.
- C5 Natural environment without management: wild soil, sediment, fresh and marine water, uncultivated vegetation, hypersaline matrices.
- C6 Anthropogenic matrix without attributable regimen: urban and hospital wastewater, beaches and coastal waters receiving discharge, periurban soil with effluent, sludge.

### Inclusion criteria

- IC1 The microorganism of interest is Candida tropicalis
- IC2 The study declares the method used for species identification
- IC3 The study specifies the source of recovery with precision sufficient to assign it to one of the six compartments
- IC4 The study reports antifungal susceptibility profile, molecular resistance determinants, genotype or clade assignment
- IC5 Denominators are recoverable: total number of isolates and their breakdown by compartment and by antifungal agent tested
- IC6 Geographical origin is identifiable at country level
- IC7 Original article derived from primary research
- IC8 The study declares the interpretive criterion and, where it reports resistance categories, allows identification of the document and version of the standard applied, or else reports individual minimum inhibitory concentrations or their distribution

Application rule. A study is included if it meets IC1, IC2, IC5, IC6 and IC7 and at least one of IC3 or IC4. Entry into the meta-analysis of resistance proportions additionally requires IC4 with denominators disaggregated by antifungal agent, and IC8. Studies meeting the general rule but not IC8 are included in the review, feed SQ1 and the qualitative description, and remain outside pooled resistance estimates.

### Exclusion criteria

- EC1 The microorganism of interest is not the species; it appears as an incidental finding within Candida spp. series without disaggregable data
- EC2 The species identification method is not declared
- EC3 Geographical origin is not identifiable at country level, or is attributed solely from author affiliation
- EC4 The source of recovery is unspecified or does not admit assignment to any of the six compartments
- EC5 The matrix shows documented anthropogenic input without identifiable azole regimen. Operates as a classification rule towards C6, not as exclusion
- EC6 Neither the susceptibility testing method nor the interpretive criterion is declared, and no minimum inhibitory concentrations are reported
- EC7 Denominators are not recoverable, or data are aggregated without possibility of disaggregation. The correct denominator is the number of isolates actually tested against the antifungal agent in question
- EC8 Studies using exclusively international reference strains with no isolate of documented origin
- EC9 Studies centred on the antifungal activity of novel compounds, plant extracts, essential oils, nanoparticles, metal complexes, peptides, disinfectants or agent combinations, whose only measurement is the efficacy of the tested agent without characterising the resistance profile against conventional antifungals
- EC10 Studies on the species as an industrial or biotechnological organism, including xylitol, ethanol and organic acid production and bioprocesses, unrelated to antifungal resistance
- EC11 Studies whose only contribution is computational or in silico modelling, without isolates
- EC12 Cohorts or collections of isolates duplicated or overlapping between publications of the same surveillance programme, institution and period
- EC13 Systematic reviews, meta-analyses, narrative reviews, clinical guidelines, editorials, letters and commentaries without primary data; conference abstracts without extractable data. Does not exclude preprints
