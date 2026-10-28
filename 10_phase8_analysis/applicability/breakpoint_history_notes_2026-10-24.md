# Breakpoint history for *Candida tropicalis* (CLSI/NCCLS and EUCAST): notes

Research date: 2026-10-24. Companion file: `breakpoint_history_2026-10-24.csv` (280 rows = 28 documents/versions × 10 agents).
Every CSV row has at least one URL that was opened when the table was compiled (24-10-2026). The table is the input of `build_cbp_applicability_v1.py`, which writes the D4 matrix.

## 1. Access limits (these affect confidence)

- **EUCAST.** The fetch tool is blocked by robots.txt for the archived antifungal tables. This covers the PDF and XLS files under `fileadmin/eucast/pdf/AFST/archive/` (v4.1–v9.0), v10.0 and v11.0 under `clinical_breakpoints/`, `BP_ECOFF_v5.0` and the October 2025 update PDF. The v12.0 URL is not on the allowlist. The only table opened on eucast.org is **v12.1**. The other sources used were:
  - a copy of the **v8.0** PDF hosted by aspergillus.org.uk (Fungal Infection Trust);
  - a copy of the **v10.0** PDF hosted by policlinico.pa.it (the EUCAST file itself, not a translation);
  - **v4.1** as reproduced on a slide (Lass-Flörl, PEG 2012). This is not peer-reviewed;
  - **v6.1** through Orasch et al., CMI 2014;
  - **v10.0** through Arendrup et al., CMI 2020;
  - EUCAST rationale documents (RDs) and technical notes (TNs), used for change history.
- **NCBI.** `pmc.ncbi.nlm.nih.gov` and PubMed returned a reCAPTCHA page for most of the session. The following full texts were therefore not read: Pfaller & Diekema JCM 2012 (PMC3421803), Rex et al. CMR 2001, the Pfaller 2008 echinocandin paper and Berkow et al. CMR 2020. Abstracts from Iowa Research Online were used instead.
- **CLSI.** CLSI documents are paywalled. The sources used were:
  - ANSI preview pages: M27-A2 (foreword and table of contents), M27-S4 (front matter only, no Table 1), M27 4th ed. (foreword), M44-A (abstract) and M44 3rd ed.;
  - the CLSI sample of M27M44S Ed3 (Table 1 and Overview of Changes);
  - a full copy of **M27-A3** hosted on a Kerman University server;
  - CLSI, GlobalSpec and ANSI catalogue pages, used for dates and abstracts.
- **Not opened:** M27-P, M27-T, M27-A, M27-S3, M27-S4 Table 1, M60 Ed1, M60 Ed2, M44-A2 and M44-S3. Their values come from secondary sources, from previews, or from derivation (see §2).

## 2. Coding rules

| Code | Meaning |
|---|---|
| `YES` | A clinical breakpoint applicable to *C. tropicalis* exists (species-specific, or genus-level "Candida spp."). |
| `NO` | The document gives no usable CBP. This covers: method documents with no table; "IP" (in preparation); EUCAST caspofungin "Note"; deleted CLSI breakpoints; agents discussed without a CBP. |
| `IE` | EUCAST "insufficient evidence". |
| `not_covered` | The agent is absent from the interpretive table. |
| `not_located` | No opened source covers this cell. Where possible, the expected value is given in `scope_note` and marked "NOT VERIFIED". |

- **Method documents** are coded `NO`, with a pointer in `scope_note` to the companion supplement row:
  - **M27-A3**: interpret with M27-S3 for Apr 2008 – Dec 2012, or M27-S4 for Dec 2012 – Nov 2017.
  - **M27 4th ed.**: interpret with M60 Ed1 (2017), M60 Ed2 (2020) or M27M44S Ed3 (2022).
  - **M44 3rd ed.**: interpret with M60 / M27M44S.
  - M27-A, M27-A2, M44-A and M44-A2 contain their own interpretive criteria. They are coded on their own content.
- **`DERIVED`** (start of `scope_note`, about 76 cells): the value was not read in that version's own table. It was deduced in one of three ways:
  - (a) **Adjacent change log.** The next version's change log, issued by the same body, lists no change for that agent:
    - v7.0 from v8.0;
    - v9.0 from v10.0;
    - v12.0 from v12.1;
    - CLSI M60 Ed2 from M27M44S Ed3.
  - (b) **Bracketing plus RD history.** The value is identical in the opened versions on both sides, and the agent's EUCAST RD history shows no revision in that interval (v5.0, v6.1, v8.1, v11.0).
  - (c) **Global logic.** Three statements cover every version:
    - EUCAST caspofungin is "not yet established" in every version from 2012 to 2026;
    - the first EUCAST flucytosine RD is v1.0, July 2025;
    - isavuconazole was first added to the Candida table in v8.0.
- **`confidence`**:
  - `primary`: read in the issuing body's own document or in a verbatim copy of it, including derivations of type (a)–(c) from such documents.
  - `secondary`: a peer-reviewed paper, or a conference slide (flagged), that names the version. A derived cell is also `secondary` when its key evidence is secondary (for example, bracketing by the v4.1 slide or by Orasch 2014).

## 3. EUCAST table versions and dates

| Version | Valid from | Superseded | Source of date |
|---|---|---|---|
| 1.0 / 2.0 | — | — | Not in the archive; existence not verified |
| 3.0 | unknown | — | Archive lists it without a file ("contact the EUCAST webmaster") |
| 4.1 | 2012-03-05 | 2013-01-09 | Slide heading; archive "until" label |
| 5.0 | not verified (presumably 2013-01-09) | 2013-03-01 | Archive |
| 6.0 (not requested) | ~2013-03-01 | 2013-03-11 | Archive |
| 6.1 | 2013-03-11 (inferred) | 2014-08-12 | Archive; Orasch 2014 ("March 2013", v6.1) |
| 7.0 | ~2014-08-12 (file name "August_2014") | 2015-11-15 | Archive |
| 8.0 | 2015-11-16 | (not in archive list) | Document |
| 8.1 | March 2017 (file name) | 2018-02-11 | Archive |
| 9.0 | 2018-02-12 (file name "180212") | 2020-02-04 | Archive |
| 10.0 | 2020-02-04 | 2024-12-02 | Document; Arendrup 2020 |
| 11.0 | 2024-12-02 (EUCAST news) | 2025-06-26 | News; archive |
| 12.0 | 2025-06-26 | 2026-04-10 | EUCAST "Latest website changes" (posted 2025-10-20) |
| 12.1 | 2026-04-10 (current) | — | Document; the change page says 2026-04-03 |

Do not confuse these with the separate "Overview of antifungal ECOFFs and clinical breakpoints" series (BP_ECOFF v2.0–v6.1, 2020–2026). It was used only as a cross-check: BP_ECOFF v4.0 (2023-08-14) matches v10.0 for *C. tropicalis*.

## 4. Key findings

### CLSI / NCCLS

1. **M27-P (1992) and M27-T (1995)** had no interpretive breakpoints. The M27-A2 foreword says breakpoints were first included in M27-A (1997). Rex et al. (1997) put the tentative fluconazole and itraconazole values out for public comment.
2. **M27-A (1997) and M27-A2 (2002, Appendix C)** give genus-level breakpoints that apply to *C. tropicalis*:
   - fluconazole S ≤8, SDD 16–32, R ≥64 (not for *C. krusei*);
   - itraconazole S ≤0.125, SDD 0.25–0.5, R ≥1, for **mucosal infections only**;
   - flucytosine S ≤4, I 8–16, R ≥32;
   - no breakpoint for amphotericin B or for any later agent.
3. **M27-A3 (2008) is a method document.** Interpretation is in "Table 1 of the M27 Informational Supplement" (M27-S3). §6.5.3 lists breakpoints for anidulafungin, caspofungin, fluconazole, flucytosine, itraconazole, micafungin and voriconazole. There is no approved breakpoint for amphotericin B or posaconazole.
4. **M27-S3 (2008)** adds:
   - voriconazole S ≤1, SDD 2, R ≥4 (genus-level);
   - echinocandins S ≤2 as a **susceptible-only** category: MIC >2 is "non-susceptible", with no R category, one value for all three agents and all *Candida* species.

   The fluconazole, itraconazole and flucytosine values carry over from M27-A2.
5. **M27-S4 (Dec 2012)** gives species-specific values for *C. tropicalis*:
   - fluconazole S ≤2, SDD 4, R ≥8;
   - voriconazole S ≤0.12, I 0.25–0.5, R ≥1;
   - caspofungin, micafungin and anidulafungin S ≤0.25, I 0.5, R ≥1.

   For itraconazole and flucytosine there is no CBP for *C. tropicalis* according to three secondary sources (contradiction §5.1).
6. **The 2017 revision (M27 4th ed. / M60 Ed1)** explicitly deleted the itraconazole and flucytosine breakpoints. The M27 Ed4 foreword says: "Added an explanation for deleting breakpoints for itraconazole and flucytosine". M27M44S Ed3 adds that the previous breakpoints "should not be used".
7. **Current M27M44S Ed3 (Aug 2022), *C. tropicalis***:
   - fluconazole S ≤2, SDD 4, R ≥8;
   - voriconazole S ≤0.12, I 0.25–0.5, R ≥1;
   - anidulafungin, caspofungin and micafungin S ≤0.25, I 0.5, R ≥1 (caspofungin footnote: confirm I/R because of inter-laboratory variability);
   - rezafungin S ≤0.25, susceptible-only (new; not a requested agent);
   - no CBP for itraconazole, flucytosine, posaconazole, isavuconazole or amphotericin B.

   The Ed3 change list against M60 Ed2 contains nothing for these agents, so M60 Ed2 (2020) carries the same values.
8. **Disk diffusion**:
   - **M44-A (2004):** only fluconazole has zone breakpoints (≥19 / 15–18 / ≤14 mm); voriconazole has QC ranges only.
   - **M44-A2 / M44-S3 (2009):** fluconazole as above; voriconazole ≥17 / 14–16 / ≤13 mm; caspofungin S ≥11 mm (susceptible-only); posaconazole QC only.
   - **M44 3rd ed. (2018):** method only. Zone breakpoints for caspofungin, micafungin, fluconazole and voriconazole are in M60 / M27M44S; the *C. tropicalis* zone values were **not located**.

### EUCAST (*C. tropicalis* column)

- **Fluconazole** is S ≤2 / R >4 (I = 4) in every verified source, from the 2007 technical note to v12.1.
- **Voriconazole** is ≤0.125 / >0.125 up to v8.0. From v9.0 (2018) it is ≤0.125 / I 0.25 / >0.25; the Candida I category came with voriconazole RD v3.0 (Dec 2017). v8.1 is not verified (expected ≤0.125 / >0.125).
- **Posaconazole** (0.06/0.06), **amphotericin B** (1/1) and **anidulafungin** (0.06/0.06) are stable from v4.1 (2012) to v12.1.
- **Itraconazole** is "IP" in v4.1 and ≤0.125 / >0.125 from v7.0 (Aug 2014). The first Candida itraconazole RD is dated 26 June 2014.
- **Micafungin** is "IP" in v4.1 and IE for *C. tropicalis* from RD v1.0 (Feb 2013) through v10.0. It becomes ≤0.06 / >0.06 after RD v3.0 (22 Nov 2024); this is verified in v12.0 and v12.1. v11.0 is not verified but expected SI.
- **Caspofungin** has never had a EUCAST breakpoint. The table shows a Note: isolates susceptible to anidulafungin and micafungin are regarded as susceptible to caspofungin.
- **Isavuconazole** is absent before v8.0 and IE from v8.0 onwards.
- **Flucytosine** has never appeared in the Candida table. RD v1.0 (July 2025) assigns IE to *C. tropicalis*; v12.1 lists flucytosine only under Dosages.
- **The meaning of "I" changed in v10.0 (2020).** It went from "intermediate" to "susceptible, increased exposure". This matters for fluconazole at 4 mg/L and voriconazole at 0.25 mg/L.

## 5. Contradictions and caveats

1. **Itraconazole and flucytosine in M27-S4 are unresolved.** The CSV codes them `NO` (secondary).
   - Evidence that M27-S4 had no CBP:
     - Santos et al. 2014 (Rev Inst Med Trop São Paulo) say itraconazole is "absent among the new M27-S4 breakpoints", and the Table 3 footnote reads "(--) antifungal agents not contemplated in M27-S4" for itraconazole and flucytosine.
     - Fan et al. 2017 (Front Microbiol), citing CLSI 2012, used ECVs for itraconazole, posaconazole, flucytosine and amphotericin B.
     - The IDSA 2016 Table 1 ("Clinical breakpoints adopted by CLSI") shows itraconazole values only under *C. albicans* (flattened extraction) and no flucytosine.
   - Evidence that leaves the edition open:
     - M27-A3 §6.5.3 (2008) lists both agents as having breakpoints.
     - The CLSI M27 Ed4 foreword (2017) explains their deletion without naming the edition in which they were removed.
   - M27-S4 Table 1 itself could not be opened. Even if M27-S4 kept a genus-level itraconazole row, it would be the mucosal-only criterion.
2. **The voriconazole middle category in M27-S4 is labelled differently.** It is "I" in M27M44S Ed3 and in the Pfaller 2011 proposal. It is "SDD" in Fan 2017, in the Santos 2014 table header, and in Ghanem-Zoubi 2017 ("SDD applies for fluconazole and voriconazole instead of intermediate").
3. **EUCAST amphotericin B RD v3.0.** Its history says that v2.0 (2020) "lowered the R breakpoint for all species". However, *C. tropicalis* is 1/1 in v4.1, v8.0, v10.0 and v12.1, and Arendrup 2020 says "For Candida, the breakpoints have remained unchanged". The CSV follows the tables.
4. **EUCAST archive inconsistencies:**
   - v12.0 is labelled "until 25 June, 2026", but its link points to the v11.0 file.
   - v12.1 is valid from 2026-04-10, while its change page says 2026-04-03.
   - The itraconazole RD v4.0 file is named "20260410", but its history says "June 2026".
   - A news item dated 2026-06-16 announces new fluconazole and itraconazole RDs. **Watch for a post-v12.1 table.**
5. **v12.0 may have been edited in October 2025.** It was posted on 2025-10-20 as "valid from 2025-06-26", and EUCAST reported on 2025-10-22 that "ECOFFs and breakpoints … established or revised" (the detail PDF is robots-blocked). The v12.1 change log shows no change for *C. tropicalis* against v12.0, so *C. tropicalis* values are unaffected.
6. **Minor anomalies:**
   - The v4.1 slide prints voriconazole as "0.124". This is read as 0.12 plus footnote 4; the column order was checked through internal consistency, e.g. *C. krusei* "-" for fluconazole and *C. parapsilosis* "-" for the echinocandins.
   - The anidulafungin RD history dates are inverted (v1.0 dated 5 Feb 2013, v2.0 dated 15 Jan 2013).
   - The posaconazole RD introduction says 2012 for the Candida breakpoints, while its history says 2010.
7. **Labelling in primary studies.** Santos 2014 and Orasch 2014 call the 2008 CLSI values "M27-A3" or "CLSI 2008", which in practice means M27-A3 together with M27-S3. Map them accordingly.
8. **PDF text extraction.** The v8.0, v10.0 and v12.1 values come from token sequences extracted from the PDFs. Column alignment was checked against internally consistent rows (*C. krusei* fluconazole "-", *C. glabrata* fluconazole 0.001/16 or 0.002/32, *C. parapsilosis* echinocandins 4/4). A visual check of these three PDFs is still recommended before the protocol is frozen.

## 6. Unverified cells (`not_located`, 28)

- EUCAST 1.0/2.0: all 10 agents.
- EUCAST 3.0: fluconazole, itraconazole, voriconazole, posaconazole, amphotericin B, micafungin, anidulafungin.
- EUCAST 5.0 micafungin (it is IP or IE, so no usable CBP either way).
- EUCAST 8.1 voriconazole (expected ≤0.125 / >0.125).
- EUCAST 11.0 micafungin (expected ≤0.06 / >0.06).
- CLSI M60 Ed1: fluconazole, voriconazole, caspofungin, micafungin, anidulafungin, posaconazole, isavuconazole, amphotericin B. The expected values equal M27-S4 and M60 Ed2. M60 Ed1 itraconazole and flucytosine are sourced as `NO`.
- Not located anywhere: CLSI M60 / M27M44S zone diameters for *C. tropicalis*; Berkow et al. CMR 2020; Pfaller & Diekema JCM 2012 full text.

## 7. Documents not requested but likely to appear in the corpus

- **CLSI supplements:** M27-S1 (May 2004) and M27-S2 (Apr 2005); M44-S1 (Jan 2006) and M44-S2 (Aug 2007). These come from the "Previous Editions" list of M27M44S Ed3. FDA 510(k) K082271 (2008) cites M44-S2 for fluconazole zones ≥19 / 15–18 / ≤14 mm. Their contents were not examined; for example, when CLSI first issued voriconazole breakpoints remains open.
- **EUCAST v6.0** was in force for only about 10 days in March 2013.

## 8. Methodological risks for the review

- **The change in CLSI breakpoints in 2012 changes the R cut-off.** For *C. tropicalis*:

  | Agent | R before Dec 2012 | R from Dec 2012 |
  |---|---|---|
  | Fluconazole | ≥64 | ≥8 (3 dilutions lower) |
  | Voriconazole | ≥4 | ≥1 |
  | Echinocandins | none (NS >2) | ≥1 |

  Resistance proportions over time are therefore confounded with breakpoint version. Version or period should be a pre-specified covariate or stratum, or all studies should be re-categorised only where raw MICs are available. The re-categorisation rule must be fixed before extraction.
- **Agents without a CBP produce outcome-conditioned denominators.** These are itraconazole and flucytosine after 2012/2017, posaconazole, isavuconazole, amphotericin B (CLSI), and caspofungin (EUCAST). Studies that still report "R" for such agents are using ECVs, non-WT categories or obsolete breakpoints. Decide a priori whether to exclude them or code them as non-WT.
- **Categories differ between versions.** CLSI 2008 echinocandin "NS" is not R. EUCAST "I" before and after 2020 means different things. The CLSI itraconazole breakpoint before 2012 applied to mucosal infections only.
- **Cross-system application is a classification error.** EUCAST breakpoints applied to CLSI MICs, or the reverse, misclassify isolates. Flag studies that mix methods and breakpoint systems.
