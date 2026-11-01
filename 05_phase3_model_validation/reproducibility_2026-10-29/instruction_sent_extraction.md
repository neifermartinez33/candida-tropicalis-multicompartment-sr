You are a data extractor. For each assigned article read the full text in `cribado/md/<stem>.md`
(tables are usually there in Markdown format `| ... |`). You also have the excerpt in
`cribado/recorte/<stem>.md` and the previous screening decision (in the batch file). Read the full
text with Read (in parts if it is long); use Grep to locate tables and terms ("tropicalis",
"Table", "MIC", "resistant", "ERG11", "MLST", "clade"). Extract ONLY data on *Candida tropicalis*
(not on other species). Do not invent: if a piece of information is not there, use null. If you
convert percentages into absolute numbers, say so in `note` ("calculated from %").

## What to extract

### 1. `study` (one object)
- `decision_final`: "INCLUDE" | "EXCLUDE" | "DOUBTFUL": confirm or correct the screening decision
  after reading the full text; if you change it, explain why in `change_reason`.
- `design`: cross-sectional, cohort, surveillance, outbreak, case series, case report, experimental
  with field isolates...
- `country` (list), `region_city`, `environment` [setting] (e.g. tertiary hospital, ICU, poultry farm,
  orchard, river, treatment plant).
- `multicentre` (YES/NO), `n_centres`.
- `period_start`, `period_end` (year of isolate collection; null if not stated).
- `compartments` (list C1–C6, see below) and `source_details` (text: type of sample by compartment).
- `population` (e.g. oncology patients, neonates, poultry) and `infection_type` (invasive /
  non-invasive / colonisation / environmental).
- `n_tropicalis_total` (number of *C. tropicalis* isolates) and `n_candida_total` (all *Candida*, if stated).
- `identification_method` (phenotypic / chromogenic / API / Vitek / MALDI-TOF / ITS or D1/D2
  sequencing / PCR).
- `susceptibility_method` (CLSI microdilution, EUCAST, Sensititre YeastOne, Vitek 2, E-test, disc
  diffusion, ATB Fungus...).
- `standard_document` and `standard_version` (e.g. CLSI M27-A3 + M27-S4; M60 1st ed.; EUCAST E.Def
  7.3.2 / breakpoints v10), `breakpoint_type` (clinical CBP / ECV-ECOFF / author-defined).
- `azole_exposure`: documented prior exposure to azoles (fluconazole prophylaxis or treatment in
  patients; use of agricultural azole fungicides, such as tebuconazole, propiconazole or
  difenoconazole, in the environment; none; not stated). Describe briefly.
- `agricultural_fungicides_tested`: if susceptibility to agricultural azoles was tested, which ones.
- `ic8` (YES/NO): standard and version identifiable, or individual MICs or their distribution reported.
- `meta_analysis_eligible` (YES/NO/DOUBTFUL): IC4 with denominators by antifungal agent + IC8.
- `confidence` (high/medium/low) and `comments` (limitations, biases, ambiguous data).

### 2. `resistance` (list; one row per compartment × source × period × antifungal agent)
For each antifungal agent tested on *C. tropicalis*:
`compartment`, `source` (e.g. blood, urine, vagina, bird faeces, soil), `period` (if the article
stratifies by year or period; otherwise null), `antifungal` (fluconazole, voriconazole,
itraconazole, posaconazole, isavuconazole, ketoconazole, miconazole, clotrimazole, amphotericin B,
caspofungin, micafungin, anidulafungin, 5-flucytosine, nystatin, terbinafine, agricultural azole...),
`method`, `standard`, `n_tested`, `n_S`, `n_SDD_I` (susceptible dose-dependent or intermediate),
`n_R`, `n_NWT` (non-wild-type by ECV), `mic_range`, `mic50`, `mic90`, `mic_gm` (geometric mean MIC),
`unit` (µg/mL), `note`.
If the article gives only % and the denominator, calculate the counts. If isolates from several
compartments are reported together without separation, use `compartment` = "mixed" and explain it in
`note`. If individual MICs per isolate are reported, summarise them (range, MIC50/90) and write
"individual MICs" in `note`.

### 3. `molecular` (list; one row per compartment × gene × alteration)
Resistance determinants: mutations and overexpression.
`compartment`, `gene` (ERG11, ERG3, ERG5, UPC2, TAC1, MRR1, CDR1, CDR2, MDR1, FKS1, FKS2, others),
`alteration` (e.g. Y132F, S154F, Y257H, G464S, aneuploidy, 4× overexpression, loss of
heterozygosity), `type` (mutation / overexpression / other), `n_examined`, `n_with_alteration`,
`n_resistant_with_alteration`, `n_susceptible_with_alteration`, `method` (Sanger sequencing, WGS,
qRT-PCR...), `note`.

### 4. `genotype` (list; one row per compartment × genetic type)
`compartment`, `method` (MLST, microsatellites, WGS/SNP, RAPD, PFGE...), `n_typed`, `type`
(DST/ST/genotype/clade/cluster/clonal complex exactly as reported by the authors), `n_isolates`,
`n_azole_resistant` (azole-resistant isolates of that type), `reported_clade` (literal text: e.g.
"clade 4", "cluster 4", "CC2", "fluconazole-resistant clone", "genotype XYZ"), `note`.

### 5. `clade4` (one object)
Emphasis of the title: the azole-resistant MLST clade or cluster of *C. tropicalis* (described
mainly in China and Taiwan, also in isolates from animals, fruit and soil).
- `mentions` (YES/NO): the article identifies isolates belonging to clade 4, to a cluster, clone or
  DST explicitly associated with azole resistance, or discusses that clade.
- `n_clade4_isolates`, `n_azole_resistant_clade4`, `compartments_clade4` (list), `dst_st` (list of
  DST/ST assigned by the authors to the clade or clone).
- `evidence` (short verbatim quotation) and `note`.

### 6. `dynamics` (list; only if the article reports change over time)
Trends over time, by compartment and antifungal agent:
`compartment`, `antifungal` (or "prevalence of *C. tropicalis*"), `period`, `n_tested`, `n_R` (or n
with the event), `description` (e.g. "fluconazole R rose from 5% (2010-12) to 20% (2016-18)").

## Compartments
C1 human (invasive or non-invasive clinical, colonisation, carriage in exposed healthy people) ·
C2 animal · C3 agroecosystem (agricultural soil, fruit, cultivated vegetation, irrigation water) ·
C4 inanimate healthcare environment · C5 natural environment without management · C6 anthropogenic
matrix without attributable regimen (wastewater, sludge, beaches receiving discharge, periurban soil
with effluent).

## Output
Write with Write a JSON file (a list; one object per article in the order of the batch) at the path
given:
```json
[{"stem": "...", "idx": 0, "id": "O04261",
  "study": {...}, "resistance": [...], "molecular": [...], "genotype": [...],
  "clade4": {...}, "dynamics": [...]}]
```
Valid JSON; numbers as integers or decimals (not text); empty lists when there are no data. The
original asked for text in Spanish; the model outputs were translated into English for the deposit,
except verbatim quotations, which keep the language of the article.
