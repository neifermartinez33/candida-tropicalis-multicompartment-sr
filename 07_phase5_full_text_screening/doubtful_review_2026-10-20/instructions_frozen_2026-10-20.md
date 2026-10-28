> English translation of the frozen instruction. The original Spanish file used as the reader's input (SHA-256 414197ed3dca1abc3adea85a575f3ff7fe523be910f2565048f187854921258f, before two local working paths were redacted) is kept in the project archive.

# Review of doubtful articles: instructions for the reviewer

Systematic review registered in PROSPERO (CRD420261486387): *Multicompartment distribution and dynamics of the antifungal resistome of Candida tropicalis*. Population: *Candida tropicalis* isolates from any country and compartment. Unit of observation: the isolate.

Each article in your batch was marked DOUBTFUL by an assisted extraction that read a text conversion of the PDF (which sometimes lost tables or took the wrong PDF). Your task is to decide, with the full text, whether the article **can enter**, and to leave the evidence so that a human reviewer can verify it. You propose; the human decides. Do not invent any figure.

## Files

- Batch: `[temporary working path]` Each record contains: ID, title, year, journal, DOI, path to the PDF, path to the text extracted with pdftotext (`extracted_text`), path to the OCR if the PDF is scanned (`ocr_text`), whether the same PDF (identical hash) is assigned to other records (`pdf_same_hash`), and what the previous screening and extraction said (reason for the doubt in `extraction.change_reason` and `extraction.comments`).
- Result: `[temporary working path]`, one JSON line per article. **Write each line as soon as you finish each article** (append it to the file with Bash `cat >>` or Python), not at the end.

## How to read each article

1. Read the batch record and the reason for the doubt.
2. Check that the PDF corresponds to the record: title, authors, year or journal on the first page. If `pdf_same_hash` is not null, the same file is assigned to other records: it almost certainly corresponds to at most one of them. If the PDF does not correspond to the record, the verdict is NOT_RETRIEVED (state which work the PDF corresponds to if it can be recognised).
3. Locate the information with `grep -n -i` in the extracted text (tropicalis, identif, CHROMagar, API, Vitek, MALDI, PCR, CLSI, NCCLS, EUCAST, M27, M44, breakpoint, MIC, resist, Table/Tabla, country, hospital, etc.) and read only the relevant fragments with Read (offset/limit). Do not read the whole text if it is not necessary.
4. If the doubt is that a table "is not in the text", if the text is empty, corrupted or bad OCR, or if you need to see a table, open the PDF with the Read tool using the `pages` parameter (for example "3-5") and read the table in the image. At most about 8 pages per article. Tables are the main reason these articles were left doubtful: look for them.
5. Apply the criteria below and write the result line.

## Registered criteria (literal text of the protocol)

Compartments: C1 human host (invasive and non-invasive clinical, cutaneous and mucosal colonisation, carriage in occupationally exposed healthy population); C2 animal host (domestic, production, wild or captive animals); C3 agroecosystem (agricultural soil, fruit and its surface, cultivated vegetation, irrigation water); C4 inanimate healthcare environment (surfaces, furniture, equipment and devices in healthcare settings); C5 natural environment without management (wild soil, sediment, fresh and marine water, uncultivated vegetation, hypersaline matrices); C6 anthropogenic matrix without attributable regimen (urban and hospital wastewater, beaches and coastal waters receiving discharge, periurban soil with effluent, sludge). Between C1 and C4, the purpose of the culture discriminates: diagnostic is C1, environmental surveillance is C4. Between C3 and C5, documented agronomic management discriminates. A matrix with documented anthropogenic input is C6.

- IC1 The microorganism of interest is Candida tropicalis
- IC2 The study declares the method used for species identification
- IC3 The study specifies the source of recovery with precision sufficient to assign it to one of the six compartments
- IC4 The study reports antifungal susceptibility profile, molecular resistance determinants, genotype or clade assignment
- IC5 Denominators are recoverable: total number of isolates and their breakdown by compartment and by antifungal agent tested
- IC6 Geographical origin is identifiable at country level
- IC7 Original article derived from primary research
- IC8 The study declares the interpretive criterion and, where it reports resistance categories, allows identification of the document and version of the standard applied, or else reports individual minimum inhibitory concentrations or their distribution

**Application rule.** A study enters the review if it meets IC1, IC2, IC5, IC6 and IC7 and at least one of IC3 or IC4. It additionally enters the meta-analysis of resistance proportions if it meets IC4 with denominators disaggregated by antifungal (number of *C. tropicalis* isolates tested and number resistant, or non-wild-type, per antifungal) **and** IC8.

- EC1 The microorganism of interest is not the species; it appears as an incidental finding within Candida spp. series without disaggregable data
- EC2 The species identification method is not declared
- EC3 Geographical origin is not identifiable at country level, or is attributed solely from author affiliation
- EC4 The source of recovery is unspecified or does not admit assignment to any of the six compartments
- EC6 Neither the susceptibility testing method nor the interpretive criterion is declared, and no minimum inhibitory concentrations are reported
- EC7 Denominators are not recoverable, or data are aggregated without possibility of disaggregation. The correct denominator is the number of isolates actually tested against the antifungal agent in question
- EC8 Studies using exclusively international reference strains with no isolate of documented origin
- EC9 Studies centred on the antifungal activity of novel compounds, plant extracts, essential oils, nanoparticles, metal complexes, peptides, disinfectants or agent combinations, whose only measurement is the efficacy of the tested agent without characterising the resistance profile against conventional antifungals
- EC10 Studies on the species as an industrial or biotechnological organism (xylitol, ethanol, organic acids, bioprocesses), unrelated to antifungal resistance
- EC11 Only computational or in silico modelling, without isolates
- EC12 Cohorts or collections duplicated or overlapping between publications of the same surveillance programme, institution and period
- EC13 Systematic reviews, meta-analyses, narrative reviews, clinical guidelines, editorials, letters and commentaries without primary data; conference abstracts without extractable data. Does not exclude preprints

## Application rules set by the team

- Single case reports and case series are primary research (IC7) and can enter if they meet the rest.
- A conference abstract enters if it provides extractable data; it is excluded (EC13) if not.
- Detection without isolation (direct PCR on the sample, metabarcoding) does not meet IC1: the unit is the isolate.
- Processed or fermented foods and industrial environments do not correspond to any compartment (EC4). Raw fruit or vegetables are C3.
- The species as an experimental agent with no specified origin: EC4; with reference or collection strains only: EC8.
- IC2: the method is declared if it is named (morphology on cornmeal agar, germ tube, CHROMagar, API 20C, ID32C, Vitek, MicroScan, MALDI-TOF, PCR, ITS/D1-D2 sequencing, etc.) or a specific procedure is cited. "Conventional methods" or "standard methods" without any specification is not a declaration: flag it and lower the confidence.
- IC6: the country must come from the sampling described in the study (hospital, city, region), not only from the authors' affiliation.
- IC5 and EC7: the correct denominator is the number of *C. tropicalis* isolates actually tested against each antifungal. If the study gives only percentages, reconstruct the number only if it is unambiguous (a percentage of a known n that yields an integer) and flag it as reconstructed. If the susceptibility data are for "Candida spp." or "non-albicans" without a *C. tropicalis* breakdown, they are not usable for the meta-analysis, but the study can enter the review if it provides the number of *C. tropicalis* isolates with their source (IC3) or molecular or genotype data for the species (IC4).
- IC8: acceptable is the declared standard with an identifiable document (for example CLSI M27-A3, M27-S4, M60, M27M44S, EUCAST E.Def 7.3.2 with breakpoint table v10), or the version inferable from the year and the declared breakpoints (flag it as inferred), or individual MICs or their distribution. A commercial system (Vitek 2, Sensititre YeastOne, Etest, ATB Fungus) with a declared interpretation standard meets it; without a standard or MICs, it does not.
- If the PDF is correct but illegible even when viewed as an image, the verdict is NOT_DETERMINABLE.

## Verdicts (use exactly one)

- `ENTERS_REVIEW_AND_MA`: meets the general rule and also IC4 with denominators per antifungal and IC8.
- `ENTERS_REVIEW`: meets the general rule, but not the meta-analysis requirements.
- `REMAINS_EXCLUDED`: fails a criterion; state the EC code.
- `NOT_RETRIEVED`: the PDF does not correspond to the record, is truncated or contains only an unrelated part (cover, table of contents, supplement, another article). It is not an exclusion by criterion: the correct text is not available.
- `NOT_DETERMINABLE`: the PDF is the correct one but the necessary information cannot be read.

## Format of each line of the results file

```json
{"ID": "O12345", "pdf_matches": "yes|no|partial", "pdf_is_of": "title of the work the PDF corresponds to if it is not that of the record, or null",
 "document_type": "article|case_report|case_series|conference_abstract|thesis|letter|review|other",
 "verdict": "ENTERS_REVIEW_AND_MA|ENTERS_REVIEW|REMAINS_EXCLUDED|NOT_RETRIEVED|NOT_DETERMINABLE",
 "criteria": {"IC1": "yes|no|doubt", "IC2": "...", "IC3": "...", "IC4": "...", "IC5": "...", "IC6": "...", "IC7": "...", "IC8": "..."},
 "exclusion_code": "EC7 or null",
 "compartment": "C1..C6 or null", "source": "brief text", "country": "...", "period": "yyyy-yyyy or null",
 "n_tropicalis": 12, "identification_method": "...", "susceptibility_method": "...", "interpretive_criterion": "document and version, or 'individual MICs', or null",
 "ma_data": [{"antifungal": "fluconazole", "n_tested": 12, "n_R": 2, "n_SDD_I": 1, "category": "R according to CLSI M27-S4", "reconstructed": false, "location": "Table 3, p. 5"}],
 "molecular_or_genotype": "brief text or null",
 "resolves_the_doubt": "what resolved (or did not resolve) the original doubt, in one or two sentences",
 "evidence": ["brief verbatim quote (max. 25 words) with page or table", "..."],
 "confidence": "high|medium|low",
 "note": "brief text or null"}
```

`ma_data` only when the verdict is `ENTERS_REVIEW_AND_MA`; in all other cases, an empty list. The figures in `ma_data` must be locatable in the document with the `location` you give; if you cannot locate a figure, do not include it.

## When finished

Check that the results file has one valid line for each article in the batch (count the lines and validate the JSON with Python). Reply only with a short summary: number of articles per verdict and the IDs of those that enter (with or without meta-analysis). Do not repeat the content of the file.
