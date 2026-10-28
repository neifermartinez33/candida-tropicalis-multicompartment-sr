# Data extraction instruction: *Candida tropicalis* systematic review

English translation of the instruction given to the language model for data extraction (Spanish
original `INSTRUCCIONES_EXTRACCION.md`, SHA-256
a87f47fed9302e25e0dee9db67a24442a2caf0cfd981d2e5da5cfcd1767f9dca). Field names and response values
are kept as in the original, with their English meaning in brackets, because they are the keys of
the model output.

**Title:** *Multicompartment distribution and dynamics of the antifungal resistome of Candida
tropicalis, with emphasis on the azole-resistant clade 4.*

---

You are a data extractor. For each assigned article read the full text in `cribado/md/<stem>.md`
(tables are usually there in Markdown format `| ... |`). You also have the excerpt in
`cribado/recorte/<stem>.md` and the previous screening decision (in the batch file). Read the full
text with Read (in parts if it is long); use Grep to locate tables and terms ("tropicalis",
"Table", "MIC", "resistant", "ERG11", "MLST", "clade"). Extract ONLY data on *Candida tropicalis*
(not on other species). Do not invent: if a piece of information is not there, use null. If you
convert percentages into absolute numbers, say so in `nota` [note] ("calculated from %").

## What to extract

### 1. `estudio` [study] (one object)
- `decision_final` [final decision]: "INCLUIR" | "EXCLUIR" | "DUDOSO" [include | exclude | doubtful]:
  confirm or correct the screening decision after reading the full text; if you change it, explain
  why in `motivo_cambio` [reason for change].
- `diseno` [design]: cross-sectional, cohort, surveillance, outbreak, case series, case report,
  experimental with field isolates...
- `pais` [country] (list), `region_ciudad` [region or city], `entorno` [setting] (e.g. tertiary
  hospital, ICU, poultry farm, orchard, river, treatment plant).
- `multicentrico` [multicentre] (SI/NO), `n_centros` [number of centres].
- `periodo_inicio`, `periodo_fin` [start and end of period] (year of isolate collection; null if not stated).
- `compartimentos` [compartments] (list C1–C6, see below) and `fuentes_detalle` [source details]
  (text: type of sample by compartment).
- `poblacion` [population] (e.g. oncology patients, neonates, poultry) and `infeccion_tipo`
  [infection type] (invasive / non-invasive / colonisation / environmental).
- `n_tropicalis_total` (number of *C. tropicalis* isolates) and `n_candida_total` (all *Candida*, if stated).
- `metodo_identificacion` [identification method] (phenotypic / chromogenic / API / Vitek /
  MALDI-TOF / ITS or D1/D2 sequencing / PCR).
- `metodo_sensibilidad` [susceptibility method] (CLSI microdilution, EUCAST, Sensititre YeastOne,
  Vitek 2, E-test, disc diffusion, ATB Fungus...).
- `norma_documento` and `norma_version` [standard document and version] (e.g. CLSI M27-A3 + M27-S4;
  M60 1st ed.; EUCAST E.Def 7.3.2 / breakpoints v10), `tipo_punto_corte` [breakpoint type]
  (clinical CBP / ECV-ECOFF / author-defined).
- `exposicion_azoles` [azole exposure]: documented prior exposure to azoles (fluconazole prophylaxis
  or treatment in patients; use of agricultural azole fungicides, such as tebuconazole,
  propiconazole or difenoconazole, in the environment; none; not stated). Describe briefly.
- `fungicidas_agricolas_probados` [agricultural fungicides tested]: if susceptibility to
  agricultural azoles was tested, which ones.
- `ic8` (SI/NO): standard and version identifiable, or individual MICs or their distribution reported.
- `apto_metaanalisis` [eligible for meta-analysis] (SI/NO/DUDOSO): IC4 with denominators by
  antifungal agent + IC8.
- `confianza` [confidence] (high/medium/low) and `observaciones` [observations] (limitations, biases,
  ambiguous data).

### 2. `resistencia` [resistance] (list; one row per compartment × source × period × antifungal agent)
For each antifungal agent tested on *C. tropicalis*:
`compartimento` [compartment], `fuente` [source] (e.g. blood, urine, vagina, bird faeces, soil),
`periodo` [period] (if the article stratifies by year or period; otherwise null), `antifungico`
[antifungal agent] (in Spanish: fluconazol, voriconazol, itraconazol, posaconazol, isavuconazol,
ketoconazol, miconazol, clotrimazol, anfotericina B, caspofungina, micafungina, anidulafungina,
5-flucitosina, nistatina, terbinafina, azol agrícola...), `metodo` [method], `norma` [standard],
`n_probados` [tested], `n_S`, `n_SDD_I` (susceptible dose-dependent or intermediate), `n_R`, `n_NWT`
(non-wild-type by ECV), `cmi_rango` [MIC range], `cmi50`, `cmi90`, `cmi_mg` [geometric mean MIC],
`unidad` [unit] (µg/mL), `nota` [note].
If the article gives only % and the denominator, calculate the counts. If isolates from several
compartments are reported together without separation, use `compartimento` = "mixto" [mixed] and
explain it in `nota`. If individual MICs per isolate are reported, summarise them (range, MIC50/90)
and write "individual MICs" in `nota`.

### 3. `molecular` (list; one row per compartment × gene × alteration)
Resistance determinants: mutations and overexpression.
`compartimento`, `gen` [gene] (ERG11, ERG3, ERG5, UPC2, TAC1, MRR1, CDR1, CDR2, MDR1, FKS1, FKS2,
others), `alteracion` [alteration] (e.g. Y132F, S154F, Y257H, G464S, aneuploidy, 4× overexpression,
loss of heterozygosity), `tipo` [type] (mutation / overexpression / other), `n_examinados` [examined],
`n_con_alteracion` [with the alteration], `n_resistentes_con_alteracion` [resistant with the
alteration], `n_sensibles_con_alteracion` [susceptible with the alteration], `metodo` (Sanger
sequencing, WGS, qRT-PCR...), `nota`.

### 4. `genotipo` [genotype] (list; one row per compartment × genetic type)
`compartimento`, `metodo` (MLST, microsatellites, WGS/SNP, RAPD, PFGE...), `n_tipificados` [typed],
`tipo` [type] (DST/ST/genotype/clade/cluster/clonal complex exactly as reported by the authors),
`n_aislados` [isolates], `n_resistentes_azoles` [azole-resistant isolates of that type],
`clado_reportado` [reported clade] (literal text: e.g. "clade 4", "cluster 4", "CC2",
"fluconazole-resistant clone", "genotype XYZ"), `nota`.

### 5. `clado4` [clade 4] (one object)
Emphasis of the title: the azole-resistant MLST clade or cluster of *C. tropicalis* (described
mainly in China and Taiwan, also in isolates from animals, fruit and soil).
- `menciona` [mentions] (SI/NO): the article identifies isolates belonging to clade 4, to a
  cluster, clone or DST explicitly associated with azole resistance, or discusses that clade.
- `n_aislados_clado4` [clade 4 isolates], `n_resistentes_azoles_clado4` [azole-resistant clade 4
  isolates], `compartimentos_clado4` [clade 4 compartments] (list), `dst_st` (list of DST/ST
  assigned by the authors to the clade or clone).
- `evidencia` [evidence] (short verbatim quotation) and `nota`.

### 6. `dinamica` [dynamics] (list; only if the article reports change over time)
Trends over time, by compartment and antifungal agent:
`compartimento`, `antifungico` (or "prevalence of *C. tropicalis*"), `periodo`, `n_probados`, `n_R`
(or n with the event), `descripcion` [description] (e.g. "fluconazole R rose from 5% (2010-12) to
20% (2016-18)").

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
  "estudio": {...}, "resistencia": [...], "molecular": [...], "genotipo": [...],
  "clado4": {...}, "dinamica": [...]}]
```
Valid JSON; numbers as integers or decimals (not text); empty lists when there are no data; text in Spanish.
