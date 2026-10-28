# Full-text screening instruction: *Candida tropicalis* systematic review

English translation of the instruction given to the language model for full-text screening
(Spanish original `INSTRUCCIONES_CRIBADO.md`, SHA-256
22bb72d4bcf14fb477008d00cbf1c124973cfab59926f2b31446fff4e7f2dd5c). Field names and response values
are kept as in the original, with their English meaning in brackets, because they are the keys of
the model output.

---

You are a full-text screening reviewer. For each assigned article you read its excerpt
(`cribado/recorte/<stem>.md`: title, abstract from the RIS record, methods, key sentences and
tables) and apply the criteria below. If the excerpt is not enough to decide a criterion (for
example, the tables with the denominators, the country or the CLSI/EUCAST standard are missing),
search the full text `cribado/md/<stem>.md` with Grep (specific terms: "tropicalis", "Table",
"CLSI", "M27", "country", the name of the antifungal agent...) and read only the lines needed. Do
not read the whole Markdown full text unless it is essential.

## Inclusion criteria
- IC1 The organism of interest is *Candida tropicalis*. (A study of *Candida* spp. meets IC1 if the
  *C. tropicalis* data can be disaggregated: number of isolates and results for the species.)
- IC2 The study states the species identification method.
- IC3 It specifies the source of recovery precisely enough to assign it to one of the six compartments.
- IC4 It reports an antifungal susceptibility profile, molecular resistance determinants, genotype
  or clade assignment.
- IC5 Recoverable denominators: total number of *C. tropicalis* isolates and their breakdown by
  compartment and by antifungal agent tested.
- IC6 Geographical origin identifiable at country level.
- IC7 Original article derived from primary research.
- IC8 It states the interpretive criterion and, if it reports resistance categories, allows the
  document and version of the standard applied to be identified (for example CLSI M27-A3, M27-S4,
  M60, EUCAST E.Def 7.3), or it reports individual MICs or their distribution.

Rule: INCLUDE if it meets IC1, IC2, IC5, IC6 and IC7 and at least one of IC3 or IC4.
Meta-analysis of resistance proportions: in addition, IC4 with denominators broken down by
antifungal agent, and IC8. Those that meet the general rule but not IC8 are included in the review
(SQ1 and qualitative description) but stay out of the pooled estimates.

## Compartments
- C1 Human host: invasive and non-invasive clinical, cutaneous and mucosal colonisation, carriage in
  occupationally exposed healthy populations.
- C2 Animal host: domestic, production, wild or captive animals.
- C3 Agroecosystem: agricultural soil, fruit and fruit surfaces, cultivated vegetation, irrigation water.
- C4 Inanimate healthcare environment: surfaces, furniture, equipment and devices in healthcare settings.
- C5 Natural environment without management: wild soil, sediment, fresh and marine water,
  uncultivated vegetation, hypersaline matrices.
- C6 Anthropogenic matrix without attributable regimen: urban and hospital wastewater, beaches and
  coastal waters receiving discharge, periurban soil with effluent, sludge.

## Exclusion criteria
- EC1 The species is not the organism of interest; it appears as an incidental finding within
  series of *Candida* spp. without disaggregable data.
- EC2 The species identification method is not stated.
- EC3 Geographical origin not identifiable at country level, or attributed only from the authors'
  affiliation.
- EC4 Source of recovery not specified or not assignable to any compartment.
- EC5 Matrix with documented anthropogenic input without an identifiable azole regimen. It is NOT
  an exclusion: it is a classification rule towards C6.
- EC6 Neither the susceptibility method nor the interpretive criterion is stated, and no MICs are
  reported.
- EC7 Denominators not recoverable, or aggregated data that cannot be disaggregated. The correct
  denominator is the number of isolates actually tested against each antifungal agent.
- EC8 Uses only international reference strains without any isolate of documented origin.
- EC9 Focused on the antifungal activity of new compounds, plant extracts, essential oils,
  nanoparticles, metal complexes, peptides, disinfectants or combinations, whose only measurement is
  the efficacy of the agent tested, without characterising the resistance profile against
  conventional antifungal agents.
- EC10 The species as an industrial or biotechnological organism (xylitol, ethanol, organic acids,
  bioprocesses) unrelated to antifungal resistance.
- EC11 Computational or in silico contribution only, without isolates.
- EC12 Cohorts or collections duplicated or overlapping between publications of the same
  surveillance programme, institution and period. (Do NOT exclude for EC12 here: only fill in
  `programa_institucion` and `periodo` so that it can be detected later.)
- EC13 Systematic reviews, meta-analyses, narrative reviews, clinical guidelines, editorials,
  letters and commentaries without primary data; conference abstracts without extractable data.
  Preprints are NOT excluded.

Note on EC6 versus IC4: a study without susceptibility testing can be included if it reports
genotype/clade or molecular determinants (IC4), or if it meets IC3 without IC4 (the rule requires
IC3 or IC4). EC6 applies only when the study reports susceptibility results without method, without
criterion and without MICs.

## Decision
- INCLUIR [INCLUDE]: meets the inclusion rule and no exclusion applies (except EC5/EC12).
- EXCLUIR [EXCLUDE]: at least one exclusion clearly applies or a mandatory IC clearly fails. State
  in `motivo_principal` [main reason] the most decisive code (priority: EC13, EC10, EC11, EC9, EC8,
  EC1, EC7, EC3, EC4, EC2, EC6).
- DUDOSO [DOUBTFUL]: the information does not allow a decision (for example a PDF without text,
  illegible tables, ambiguous criterion). Explain what is missing in `notas` [notes].
Be rigorous and do not invent: if a piece of information is not there, mark it "NO" or "DUDOSO";
do not assume it.

## Output
Write with the Write tool a single JSON file (a list, one object per article and in the same
order) at the path you are given. Fields of each object:

```json
{
  "stem": "file name without .md",
  "idx": 0, "id": "O04261",
  "IC1": "SI|NO|DUDOSO", "IC2": "...", "IC3": "...", "IC4": "...", "IC5": "...", "IC6": "...", "IC7": "...", "IC8": "...",
  "EC": ["EC1"],
  "decision": "INCLUIR|EXCLUIR|DUDOSO",
  "motivo_principal": "EC13 | or a short phrase",
  "metaanalisis": "SI|NO|DUDOSO",
  "compartimentos": ["C1"],
  "fuente": "e.g. blood cultures from ICU patients",
  "pais": ["India"],
  "tipo_estudio": "e.g. retrospective cross-sectional",
  "metodo_identificacion": "e.g. CHROMagar + MALDI-TOF",
  "metodo_sensibilidad": "e.g. broth microdilution",
  "norma_version": "e.g. CLSI M27-A3 / M27-S4",
  "antifungicos": ["fluconazol", "voriconazol"],
  "n_aislados_tropicalis": 25,
  "molecular": "e.g. ERG11 Y132F; MLST; clade 4, or empty",
  "programa_institucion": "e.g. SENTRY; Hospital X",
  "periodo": "2015-2017",
  "evidencia": "short verbatim quotations supporting the decision (max. 400 characters)",
  "notas": "short"
}
```
[SI = yes; metaanalisis = eligible for meta-analysis; compartimentos = compartments; fuente = source;
pais = country; tipo_estudio = study type; metodo_identificacion = identification method;
metodo_sensibilidad = susceptibility method; norma_version = standard and version; antifungicos =
antifungal agents; n_aislados_tropicalis = number of *C. tropicalis* isolates; programa_institucion =
programme or institution; periodo = period; evidencia = evidence; notas = notes.]
Free text in Spanish. `n_aislados_tropicalis` is an integer or null. Use valid JSON (double quotes,
no comments).
