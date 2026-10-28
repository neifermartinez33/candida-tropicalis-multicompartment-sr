"""Controlled vocabularies for the C. tropicalis review (v0, 2026-10-20).

Every mapping here is a proposal derived from the raw strings of the data
extraction. Each dictionary is exported to CSV so the team can review and correct
it; the build script reads the CSV back if it exists, so human corrections win.
"""
import re

# ---------------------------------------------------------------------------
# Antifungal agents: raw string (lower-case, stripped) -> (agent_std, agent_class, per_agent)
# per_agent = False when the row aggregates several agents (not usable per agent).
# ---------------------------------------------------------------------------
AGENT_EXACT = {
    '5-flucytosine': ('flucytosine', 'pyrimidine analogue', True),
    'agricultural azole: difenoconazole': ('difenoconazole', 'agricultural azole', True),
    'agricultural azole: tebuconazole': ('tebuconazole', 'agricultural azole', True),
    'agricultural azole: triadimenol': ('triadimenol', 'agricultural azole', True),
    'amorolfine': ('amorolfine', 'morpholine', True),
    'amphotericin b': ('amphotericin B', 'polyene', True),
    'amphotericin b (liposomal)': ('amphotericin B liposomal', 'polyene', True),
    'amphotericin b lipid complex': ('amphotericin B lipid complex', 'polyene', True),
    'amphotericin b liposomal': ('amphotericin B liposomal', 'polyene', True),
    'amphotericin b methyl ester': ('amphotericin B methyl ester', 'polyene', True),
    'anidulafungin': ('anidulafungin', 'echinocandin', True),
    'azole (isoconazole)': ('isoconazole', 'imidazole', True),
    'azole experimental (shr8008/oteseconazole, vt-1161)': ('oteseconazole', 'tetrazole', True),
    'bifonazole': ('bifonazole', 'imidazole', True),
    'boric acid': ('boric acid', 'other', True),
    'butoconazole': ('butoconazole', 'imidazole', True),
    'caspofungin': ('caspofungin', 'echinocandin', True),
    'chlorhexidine': ('chlorhexidine', 'antiseptic', True),
    'chlorhexidine (antiseptic)': ('chlorhexidine', 'antiseptic', True),
    'cholesteryl amphotericin b sulphate (abcd)': ('amphotericin B colloidal dispersion', 'polyene', True),
    'ciclopirox': ('ciclopirox', 'hydroxypyridone', True),
    'cilofungin': ('cilofungin', 'echinocandin', True),
    'cilofungin (echinocandins)': ('cilofungin', 'echinocandin', True),
    'clotrimazole': ('clotrimazole', 'imidazole', True),
    'econazole': ('econazole', 'imidazole', True),
    'efinaconazole': ('efinaconazole', 'triazole', True),
    'fenticonazole': ('fenticonazole', 'imidazole', True),
    'fluconazole': ('fluconazole', 'triazole', True),
    'griseofulvin': ('griseofulvin', 'other', True),
    'ibrexafungerp': ('ibrexafungerp', 'triterpenoid', True),
    'ibrexafungerp (scy-078)': ('ibrexafungerp', 'triterpenoid', True),
    'isavuconazole': ('isavuconazole', 'triazole', True),
    'isoconazole': ('isoconazole', 'imidazole', True),
    'itraconazole': ('itraconazole', 'triazole', True),
    'ketoconazole': ('ketoconazole', 'imidazole', True),
    'liposomal amphotericin b': ('amphotericin B liposomal', 'polyene', True),
    'luliconazole': ('luliconazole', 'imidazole', True),
    'manogepix': ('manogepix', 'Gwt1 inhibitor', True),
    'manogepix (apx001a)': ('manogepix', 'Gwt1 inhibitor', True),
    'micafungin': ('micafungin', 'echinocandin', True),
    'miconazole': ('miconazole', 'imidazole', True),
    'natamycin': ('natamycin', 'polyene', True),
    'nitroxoline': ('nitroxoline', 'other', True),
    'nystatin': ('nystatin', 'polyene', True),
    'nystatin liposomal': ('nystatin liposomal', 'polyene', True),
    'oteseconazole (vt-1161/shr8008, tetrazole)': ('oteseconazole', 'tetrazole', True),
    'oxiconazole': ('oxiconazole', 'imidazole', True),
    'parconazole': ('parconazole', 'imidazole', True),
    'posaconazole': ('posaconazole', 'triazole', True),
    'ravuconazole': ('ravuconazole', 'triazole', True),
    'rezafungin': ('rezafungin', 'echinocandin', True),
    'sertaconazole': ('sertaconazole', 'imidazole', True),
    'tavaborole': ('tavaborole', 'oxaborole', True),
    'terbinafine': ('terbinafine', 'allylamine', True),
    'terconazole': ('terconazole', 'triazole', True),
    'tioconazole': ('tioconazole', 'imidazole', True),
    'voriconazole': ('voriconazole', 'triazole', True),
}

def map_agent(raw):
    """Return (agent_std, agent_class, per_agent, rule)."""
    if raw is None:
        return (None, None, False, "missing")
    k = str(raw).strip().lower()
    if k in AGENT_EXACT:
        a, c, p = AGENT_EXACT[k]
        return (a, c, p, "exact")
    if re.search(r"experimental|investigat|research|mxp-|do870|attaf", k):
        return ("experimental compound", "experimental", False, "pattern")
    if re.search(r"agricultural azole|azole agr", k):
        return ("agricultural azole (unspecified)", "agricultural azole", False, "pattern")
    if re.search(r"echinocandin", k):
        return ("echinocandin class (aggregated)", "echinocandin", False, "pattern")
    if re.search(r"azol|triazol", k):
        return ("azole class (aggregated)", "azole", False, "pattern")
    if re.search(r"multi-?resist|multidrug|not specified|unspecified|antimic|common|\bothers?\b", k):
        return ("aggregated or unspecified", "aggregated", False, "pattern")
    if re.search(r"^fc ", k):
        return ("unclear (FC)", "unclear", False, "pattern")
    return ("unmapped", "unmapped", False, "unmapped")


# ---------------------------------------------------------------------------
# Susceptibility testing method -> category (rule 6 of the protocol)
# ---------------------------------------------------------------------------
METHOD_RULES = [
    (r"biofilm|mbec|calgary|xtt", "biofilm_susceptibility_not_resistance"),
    (r"clinical definition|clinically defined|therapeutic failure|treatment failure", "clinical_definition_not_in_vitro"),
    (r"\bwells?\b", "well_diffusion_nonstandard"),
    (r"mixed|/phoenix/|vitek 2/|, etest|and etest|\+ etest", "mixed_methods"),
    (r"sensititre|yeastone|yo9|yo10|syo", "commercial_microdilution_SYO"),
    (r"vitek", "commercial_automated_VITEK2"),
    (r"atb ?fungus", "commercial_ATB_FUNGUS"),
    (r"micronaut|microscan|phoenix|fungitest|integral system|eiken|candifast|biom[eé]rieux|liofilchem|commercial", "commercial_other"),
    (r"e-?test|etest|epsil|gradient|strip", "gradient_diffusion"),
    (r"\bdis[ck]s?\b|disk|neo-?sensitab|agar diffusion|kirby", "disk_diffusion"),
    (r"agar dilu|dilution agar|steers", "agar_dilution"),
    (r"macrodilu", "broth_macrodilution"),
    (r"eucast|e\.def", "broth_microdilution_EUCAST"),
    (r"microdilu|m27|clsi|nccls|broth", "broth_microdilution_CLSI_or_unspecified"),
    (r"not specified|unspecified|not recorded|not performed|unknown|not reported", "not_reported"),
]

def map_method(raw):
    if raw is None or str(raw).strip() == "" or str(raw).lower() == "nan":
        return "not_reported"
    k = str(raw).lower()
    for pat, cat in METHOD_RULES:
        if re.search(pat, k):
            return cat
    return "other"


# ---------------------------------------------------------------------------
# Interpretive criterion: parse the free-text 'norma' field
# ---------------------------------------------------------------------------
# document -> (standard, year, role, fluconazole regime for C. tropicalis)
# role: method document, interpretive (clinical breakpoints), interpretive (ECV)
CLSI_DOCS = [
    (r"m27[- ]?p\b", "M27-P", 1992, "method", "historical"),
    (r"m27[- ]?t\b", "M27-T", 1995, "method", "historical"),
    (r"m27[- ]?a4|m27 ?4|m27[- ]?ed4|m27 4", "M27 4th ed", 2017, "method", "species_specific"),
    (r"m27[- ]?a3", "M27-A3", 2008, "method", "historical"),
    (r"m27[- ]?a2", "M27-A2", 2002, "method", "historical"),
    (r"m27[- ]?a\b", "M27-A", 1997, "method", "historical"),
    (r"m27[- ]?s4|(m27[- ]?a3 ?/ ?s4)", "M27-S4", 2012, "interpretive_CBP", "species_specific"),
    (r"m27[- ]?s3|(m27[- ]?a3 ?/ ?s3)", "M27-S3", 2008, "interpretive_CBP", "historical"),
    (r"m27m44s|m27 ?/ ?m44s", "M27M44S", 2022, "interpretive_CBP", "species_specific"),
    (r"m60[- ]?(ed)?2|m60 2", "M60 2nd ed", 2020, "interpretive_CBP", "species_specific"),
    (r"m60", "M60", 2017, "interpretive_CBP", "species_specific"),
    (r"m57s", "M57S", 2022, "interpretive_ECV", None),
    (r"m59", "M59", 2016, "interpretive_ECV", None),
    (r"m44[- ]?a2", "M44-A2", 2009, "method_disk", "historical"),
    (r"m44[- ]?(ed)?3|m44 3", "M44 3rd ed", 2018, "method_disk", "species_specific"),
    (r"m44[- ]?a\b|m44\b", "M44-A", 2004, "method_disk", "historical"),
    (r"m44[- ]?s3", "M44-S3", 2009, "interpretive_CBP", "historical"),
]

def parse_interpretive(raw, pub_year=None):
    """Parse the 'norma' string. Returns a dict with standard, documents,
    bp_type, fluconazole regime and flags. Heuristic: every output carries
    parse_confidence and needs_check."""
    out = {"interp_standard": None, "interp_documents": None, "bp_type": None,
           "flc_regime": None, "version_inferred": False,
           "parse_confidence": "low", "needs_check": True}
    if raw is None or str(raw).strip() == "" or str(raw).lower() == "nan":
        out.update(interp_standard="not_reported", parse_confidence="high", needs_check=False)
        return out
    k = str(raw).lower()
    std = []
    if re.search(r"clsi|nccls", k): std.append("CLSI")
    if re.search(r"eucast|e\.def|afst", k): std.append("EUCAST")
    if re.search(r"brcast", k): std.append("EUCAST")
    if re.search(r"manufactur|sensititre|yeastone|\bsyo\b|bio-?m[eé]rieux|of the system|rosco|neo-?sensitab|liofilchem|vitek|etest technical guide", k): std.append("manufacturer")
    if re.search(r"author|\bown\b|adapted|human cut-offs|bsac|ca-sfm|jsmm|criteri|literature|publish|intern|et al|phls|chakrabarti", k): std.append("author_or_other")
    if re.search(r"not declared|does not declare|not recorded|not specified|no standard\b|no cut-off|not indicated|unknown|no cbp|no criteri|not identifiable", k) and not std:
        std.append("not_reported")
    if not std and re.search(r"ecv|ecoff", k):
        std.append("ECV_source_not_stated")
    docs = []
    regimes = set()
    roles = set()
    for pat, doc, yr, role, reg in CLSI_DOCS:
        if re.search(pat, k):
            docs.append(doc); roles.add(role)
            if reg: regimes.add(reg)
    eu_ver = re.findall(r"v\s?(\d{1,2}(?:\.\d)?)", k)
    edef = re.findall(r"e\.?def\s?(7\.\d(?:\.\d)?)", k)
    if edef: docs += [f"E.Def {v}" for v in edef]
    if "EUCAST" in std and eu_ver: docs += [f"EUCAST BP v{v}" for v in eu_ver]
    bp = set()
    if re.search(r"ecv|ecoff|epidemiol|m59|m57s|non-?wild|wild", k): bp.add("ECV")
    if re.search(r"cbp|clinical cut-off\b(?!s)|breakpoint|m27[- ]?s[34]|m60|m27m44s|m44[- ]?s3", k) or ("EUCAST" in std and eu_ver): bp.add("CBP")
    if not bp and (("CLSI" in std) or ("EUCAST" in std)):
        bp.add("CBP_assumed")
    out["interp_standard"] = "+".join(sorted(set(std))) if std else "unparsed"
    out["interp_documents"] = "; ".join(dict.fromkeys(docs)) if docs else None
    out["bp_type"] = "+".join(sorted(bp)) if bp else None
    # fluconazole regime for C. tropicalis (protocol section 8)
    if "EUCAST" in std and "CLSI" not in std:
        out["flc_regime"] = "EUCAST"
    elif "species_specific" in regimes:
        out["flc_regime"] = "CLSI_species_specific_2012plus"
    elif "historical" in regimes:
        # M27-A3 alone after 2012 is ambiguous: the method document is M27-A3,
        # the interpretive table may be S3 (historical) or S4 (species-specific)
        if pub_year and pub_year >= 2013 and not re.search(r"s3", k):
            out["flc_regime"] = "ambiguous_check_declared_cutoffs"
        else:
            out["flc_regime"] = "CLSI_historical_pre2012"
    elif "CLSI" in std:
        # Rule 1 of the protocol: infer the version from a year written in the string
        yrs = [int(y) for y in re.findall(r"(?<!\d)(19[89]\d|20[0-2]\d)(?!\d)", k)]
        if yrs:
            out["flc_regime"] = "CLSI_species_specific_2012plus" if max(yrs) >= 2012 else "CLSI_historical_pre2012"
        else:
            out["flc_regime"] = "CLSI_version_not_stated"
        out["version_inferred"] = True
    else:
        out["flc_regime"] = "not_applicable_or_not_reported"
    # confidence
    if docs and out["interp_standard"] in ("CLSI", "EUCAST") and out["flc_regime"] not in ("ambiguous_check_declared_cutoffs", "CLSI_version_not_stated"):
        out["parse_confidence"] = "medium"
        out["needs_check"] = False
    return out


# ---------------------------------------------------------------------------
# Countries: names used in the extraction -> ISO 3166-1 alpha-3 and WHO region
# Taiwan is mapped to WPR by geographical convention (it is not a WHO member).
# ---------------------------------------------------------------------------
COUNTRY = {
    'India': ('IND', 'SEAR'), 'Brazil': ('BRA', 'AMR'), 'China': ('CHN', 'WPR'), 'Iran': ('IRN', 'EMR'),
    'Turkey': ('TUR', 'EUR'), 'Spain': ('ESP', 'EUR'), 'United States': ('USA', 'AMR'), 'Italy': ('ITA', 'EUR'),
    'Taiwan': ('TWN', 'WPR'), 'Japan': ('JPN', 'WPR'), 'Nigeria': ('NGA', 'AFR'), 'Egypt': ('EGY', 'EMR'),
    'Vietnam': ('VNM', 'WPR'), 'South Korea': ('KOR', 'WPR'), 'Republic of Korea': ('KOR', 'WPR'),
    'France': ('FRA', 'EUR'), 'Mexico': ('MEX', 'AMR'), 'Thailand': ('THA', 'SEAR'), 'Iraq': ('IRQ', 'EMR'),
    'Colombia': ('COL', 'AMR'), 'Saudi Arabia': ('SAU', 'EMR'), 'Greece': ('GRC', 'EUR'), 'Pakistan': ('PAK', 'EMR'),
    'Malaysia': ('MYS', 'WPR'), 'Indonesia': ('IDN', 'SEAR'), 'Germany': ('DEU', 'EUR'), 'Poland': ('POL', 'EUR'),
    'Argentina': ('ARG', 'AMR'), 'United Kingdom': ('GBR', 'EUR'), 'United Kingdom (Scotland)': ('GBR', 'EUR'),
    'Venezuela': ('VEN', 'AMR'), 'Russia': ('RUS', 'EUR'), 'Russia (Crimea)': ('RUS', 'EUR'),
    'Canada': ('CAN', 'AMR'), 'Australia': ('AUS', 'WPR'), 'Singapore': ('SGP', 'WPR'), 'Portugal': ('PRT', 'EUR'),
    'Nepal': ('NPL', 'SEAR'), 'Denmark': ('DNK', 'EUR'), 'Chile': ('CHL', 'AMR'), 'Kuwait': ('KWT', 'EMR'),
    'Cameroon': ('CMR', 'AFR'), 'Tunisia': ('TUN', 'EMR'), "Côte d'Ivoire": ('CIV', 'AFR'), 'Hungary': ('HUN', 'EUR'),
    'Romania': ('ROU', 'EUR'), 'Austria': ('AUT', 'EUR'), 'Morocco': ('MAR', 'EMR'), 'Jordan': ('JOR', 'EMR'),
    'Lebanon': ('LBN', 'EMR'), 'Belgium': ('BEL', 'EUR'), 'Uganda': ('UGA', 'AFR'), 'Peru': ('PER', 'AMR'),
    'South Africa': ('ZAF', 'AFR'), 'Yemen': ('YEM', 'EMR'), 'Ethiopia': ('ETH', 'AFR'), 'Ghana': ('GHA', 'AFR'),
    'Switzerland': ('CHE', 'EUR'), 'Bangladesh': ('BGD', 'SEAR'), 'Tanzania': ('TZA', 'AFR'),
    'Bulgaria': ('BGR', 'EUR'), 'Libya': ('LBY', 'EMR'), 'Israel': ('ISR', 'EUR'), 'Burkina Faso': ('BFA', 'AFR'),
    'Sri Lanka': ('LKA', 'SEAR'), 'Algeria': ('DZA', 'AFR'), 'Paraguay': ('PRY', 'AMR'), 'Slovakia': ('SVK', 'EUR'),
    'Costa Rica': ('CRI', 'AMR'), 'Netherlands': ('NLD', 'EUR'), 'Norway': ('NOR', 'EUR'),
    'Philippines': ('PHL', 'WPR'), 'China (Hong Kong)': ('HKG', 'WPR'), 'Hong Kong (China)': ('HKG', 'WPR'),
    'Kenya': ('KEN', 'AFR'), 'Sweden': ('SWE', 'EUR'), 'Czech Republic': ('CZE', 'EUR'),
    'New Zealand': ('NZL', 'WPR'), 'Gabon': ('GAB', 'AFR'), 'Qatar': ('QAT', 'EMR'), 'Palestine': ('PSE', 'EMR'),
    'Ecuador': ('ECU', 'AMR'), 'Oman': ('OMN', 'EMR'), 'Uruguay': ('URY', 'AMR'), 'Iceland': ('ISL', 'EUR'),
    'Niger': ('NER', 'AFR'), 'Cuba': ('CUB', 'AMR'), 'Panama': ('PAN', 'AMR'), 'Serbia': ('SRB', 'EUR'),
    'Chad': ('TCD', 'AFR'), 'Angola': ('AGO', 'AFR'), 'Ukraine': ('UKR', 'EUR'), 'Grenada': ('GRD', 'AMR'),
    'Mali': ('MLI', 'AFR'), 'North Macedonia': ('MKD', 'EUR'), 'Dominican Republic': ('DOM', 'AMR'),
    'Croatia': ('HRV', 'EUR'), 'United Arab Emirates': ('ARE', 'EMR'), 'Senegal': ('SEN', 'AFR'),
    'Sudan': ('SDN', 'EMR'), 'Honduras': ('HND', 'AMR'), 'Bahrain': ('BHR', 'EMR'), 'Finland': ('FIN', 'EUR'),
    'Nicaragua': ('NIC', 'AMR'), 'Belarus': ('BLR', 'EUR'), 'Ireland': ('IRL', 'EUR'),
    'Somaliland (Somalia)': ('SOM', 'EMR'), 'Cambodia': ('KHM', 'WPR'), 'Lithuania': ('LTU', 'EUR'),
    'Republic of the Congo': ('COG', 'AFR'), 'Latvia': ('LVA', 'EUR'), 'Slovenia': ('SVN', 'EUR'),
    'Czechoslovakia': ('CSK', 'EUR'), 'Georgia': ('GEO', 'EUR'), 'Cyprus': ('CYP', 'EUR'), 'Brunei': ('BRN', 'WPR'),
    'Bahamas': ('BHS', 'AMR'), 'Greenland': ('GRL', 'EUR'), 'Faroe Islands': ('FRO', 'EUR'),
    'Hong Kong': ('HKG', 'WPR'), 'France (Mayotte)': ('MYT', 'AFR'), 'France (Réunion Island)': ('REU', 'AFR'),
}

def map_country(raw):
    """Return (iso3_list, who_region, multi, inferred_flag, rule)."""
    if raw is None or str(raw).strip() == "" or str(raw).lower() == "nan":
        return ([], None, False, False, "missing")
    s = str(raw).strip()
    inferred = bool(re.search(r"inferred|affiliation", s, re.I))
    s2 = re.sub(r"\s*\((inferred[^)]*)\)", "", s).strip()
    if re.search(r"multinational|europe \(|global|several|various|mixed|\bothers?\b", s2, re.I):
        parts = [p.strip() for p in re.split(r";", s2) if p.strip()]
        iso = [COUNTRY[p][0] for p in parts if p in COUNTRY]
        return (iso, "MULTI", True, inferred, "multinational")
    parts = [p.strip() for p in re.split(r";", s2) if p.strip()]
    iso, reg = [], set()
    for p in parts:
        if p in COUNTRY:
            iso.append(COUNTRY[p][0]); reg.add(COUNTRY[p][1])
    if not iso:
        return ([], None, len(parts) > 1, inferred, "unmapped")
    if len(iso) == 1:
        return (iso, reg.pop(), False, inferred, "single")
    return (iso, "+".join(sorted(reg)) if len(reg) > 1 else reg.pop(), True, inferred, "multi_listed")


# ---------------------------------------------------------------------------
# Genes and determinants
# ---------------------------------------------------------------------------
GENE_STD = {"ERG11": "ERG11", "FKS1": "FKS1", "FKS2": "FKS2", "UPC2": "UPC2", "CDR1": "CDR1", "CDR2": "CDR2",
            "MDR1": "MDR1", "ERG3": "ERG3", "TAC1": "TAC1", "MRR1": "MRR1", "FCY1": "FCY1", "FCY2": "FCY2",
            "FUR1": "FUR1", "URA3": "URA3", "ERG1": "ERG1", "ERG6": "ERG6", "ERG9": "ERG9", "ERG2": "ERG2",
            "SNQ2": "SNQ2", "STB5": "STB5", "FLU1": "FLU1", "XYR1 (CTRG_05978)": "XYR1", "CTRG_05978": "XYR1"}

# nucleotide -> protein consolidation. A395T=Y132F and C461T=S154F are fixed by the
# protocol (section 6); the others are the translations stated by the source papers
# in this corpus and must be checked before use.
NT_TO_AA = {"A395T": "Y132F", "C461T": "S154F", "A395W": "Y132F", "C461Y": "S154F",
            "T374C": "V125A", "A428G": "K143R", "G1390A": "G464S"}
# Nucleotide designations seen in the corpus. A token made only of A/C/G/T letters
# (for example G464S or T241A) is ambiguous between DNA and protein, so a token is
# read as nucleotide only if it is listed here or its position exceeds 600.
KNOWN_NT = set(NT_TO_AA) | {"T225C", "G264A", "G1362A", "T1554C", "T769C", "C774T",
                            "A2977G", "A529G", "C21T", "A16T"}
AA_PATTERN = re.compile(r"\b([ACDEFGHIKLMNPQRSTVWY])(\d{2,4})([ACDEFGHIKLMNPQRSTVWY*])\b")
NT_PATTERN = re.compile(r"\b([ACGT])(\d{2,4})([ACGTWYRSKM])\b")

def parse_determinants(gene_raw, alt_raw):
    """Return gene_std and the list of protein-level substitutions found, plus flags."""
    g = str(gene_raw).strip() if gene_raw is not None else ""
    m_others = re.match(r"(?i)others? \((\w+)\)$", g)
    if m_others and m_others.group(1) in GENE_STD:
        g = m_others.group(1)
    gene = GENE_STD.get(g, "other_or_multiple" if g else None)
    a = str(alt_raw) if alt_raw is not None else ""
    nt = [f"{m[0]}{m[1]}{m[2]}" for m in NT_PATTERN.findall(a)]
    nt = [x for x in nt if x in KNOWN_NT or int(re.sub(r"\D", "", x)) > 600]
    aa = [f"{m[0]}{m[1]}{m[2]}" for m in AA_PATTERN.findall(a)]
    aa = [x for x in aa if x not in nt]
    converted = [NT_TO_AA[x] for x in nt if x in NT_TO_AA]
    absent = bool(re.search(r"without mutation|\bnone\b|not detected|without overexpression|without difference|\bwild\b(?!-type)", a, re.I))
    presence_only = bool(re.search(r"presence of amplicon|gene detected|gene detection", a, re.I))
    combo = bool(re.search(r"\+| and |/", a)) and (len(set(aa + converted)) > 1)
    return {"gene_std": gene,
            "aa_substitutions": "; ".join(dict.fromkeys(aa + converted)) or None,
            "nt_designations": "; ".join(nt) or None,
            "is_combination": combo,
            "is_absence_statement": absent,
            "is_gene_presence_only": presence_only}
