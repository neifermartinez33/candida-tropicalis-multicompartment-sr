"""verification_rules_v1.py (2026-10-24)

Mechanical rules and proposals of verification round 2. Imported by
make_verification_books_v1.py (which writes the books for the team) and
build_analysis_dataset_v3.py (which applies the decisions), so both use exactly
the same rule and a proposal is never computed in two ways.

Nothing in this module decides for a reviewer. Functions marked 'mechanical' apply a rule
registered or fixed in team_decisions_2026-10-24.md; those marked 'proposal' only suggest, and the
builder of the v3 dataset uses the human decision in the book when one exists.
"""
import difflib
import re
import unicodedata

import pandas as pd

# ------------------------------------------------------------------------------------------------
# 1. Interpretive criterion: regime of each resistance row (mechanical, Rule 1 and AR6)
# ------------------------------------------------------------------------------------------------
# CLSI documents and their regime. Changes from dictionaries.py v0:
#   - 'M44' without a version is no longer read as M44-A (2004): 'CLSI M44 (2020)' fell into the
#     pre-2012 regime. An unversioned M44 does not set the regime; the year written in the string
#     or the publication year decides.
#   - M44-S1 (2006) and M44-S2 (2007), pre-2012 disc supplements, are recognized.
SS_DOCS = {"M27-S4", "M60", "M60 2nd ed", "M27 4th ed", "M27M44S", "M44 3rd ed", "M59", "M57S"}
PRE_DOCS = {"M27-P", "M27-T", "M27-A", "M27-A2", "M27-A3", "M27-S3", "M44-A", "M44-A2", "M44-S1",
            "M44-S2", "M44-S3"}
CLSI_DOC_PATTERNS = [
    (r"m27[- ]?p\b", "M27-P"), (r"m27[- ]?t\b", "M27-T"),
    (r"m27[- ]?a4|m27 ?4|m27[- ]?ed ?4|m27 4", "M27 4th ed"),
    (r"m27[- ]?a3", "M27-A3"), (r"m27[- ]?a2", "M27-A2"), (r"m27[- ]?a\b", "M27-A"),
    (r"m27[- ]?s4|m27[- ]?a3 ?/ ?s4", "M27-S4"), (r"m27[- ]?s3|m27[- ]?a3 ?/ ?s3", "M27-S3"),
    (r"m27[- ]?m44[- ]?s|m27 ?/ ?m44s", "M27M44S"), (r"m60[- ]?(ed)?2|m60 2", "M60 2nd ed"),
    (r"m60", "M60"), (r"m57s", "M57S"), (r"m59", "M59"),
    (r"m44[- ]?a2", "M44-A2"), (r"m44[- ]?(ed)?3|m44 3|m44[- ]?a3", "M44 3rd ed"), (r"m44[- ]?a\b", "M44-A"),
    (r"m44[- ]?s1", "M44-S1"), (r"m44[- ]?s2", "M44-S2"), (r"m44[- ]?s3", "M44-S3"),
]
YEAR = re.compile(r"(?<!\d)(?:19[89]\d|20[0-2]\d)(?!\d)")

# Aliases of each agent within a string that declares breakpoints for several agents
AGENT_ALIAS = {
    "fluconazole": r"\b(flc|flu|fcz|flz|fluconazol\w*)\b",
    "voriconazole": r"\b(vrc|vor|vcz|vori\w*)\b",
    "itraconazole": r"\b(itc|itr|itz|itra\w*)\b",
    "posaconazole": r"\b(pos|psc|pcz|posa\w*)\b",
    "flucytosine": r"(5-?fc|\bfcy\b|flucytosin\w*)",
    "amphotericin B": r"\b(amb|amph\w*)\b",
    "caspofungin": r"\b(cas|csf|caspo\w*)\b",
    "micafungin": r"\b(mcf|mfg|mica\w*)\b",
    "anidulafungin": r"\b(anf|anid\w*)\b",
}
# Other agents: only act as a boundary between pieces ('mic' is not one, it is the concentration)
OTHER_AGENTS = (r"\b(micon\w*|nyst\w*|keto\w*|ktc|clotri\w*|isav\w*|terbin\w*|econ\w*|"
                r"tioco\w*|ravuc\w*|griseo\w*|amorol\w*)\b")
ECHINO = {"caspofungin", "micafungin", "anidulafungin"}
ECHINO_ALIAS = r"echinocandin\w*|equinocandin\w*"
AZOLES = {"fluconazole", "voriconazole", "itraconazole", "posaconazole"}
AZOLE_ALIAS = r"\b(tri)?azol(es)?\b"
LE = r"(?:≤|<=|=<)"
GE = r"(?:≥|>=|=>)"
NUM = r"\s*([0-9]+(?:[.,][0-9]+)?)"

# Declared breakpoints that identify the regime (Rex 1997; Pfaller and Diekema 2012; M27-S4)
SS_CUT = {
    "fluconazole": [rf"\bs\s*{LE}\s*2\b", r"\bsdd\s*4\b", rf"\br\s*{GE}\s*8\b", r"\br\s*>\s*4\b"],
    "voriconazole": [rf"\bs\s*{LE}\s*0[.,]12", rf"\br\s*{GE}\s*1\b(?![.,]\d)", r"\br\s*>\s*0[.,]5"],
    "echino": [rf"\bs\s*{LE}\s*0[.,]25", rf"\br\s*{GE}\s*1\b(?![.,]\d)", r"\br\s*>\s*0[.,]5"],
}
PRE_CUT = {
    "fluconazole": [rf"\bs\s*{LE}\s*8\b", r"\bsdd\s*16", rf"\br\s*{GE}\s*64\b"],
    "voriconazole": [rf"\bs\s*{LE}\s*1\b(?![.,]\d)", r"\bsdd\s*2\b", rf"\br\s*{GE}\s*4\b"],
    "echino": [rf"\bs\s*{LE}\s*2\b", r"\bns\s*>\s*2\b", r"\br\s*>\s*2\b"],
}
# (2026-10-26, B10) Breakpoints the rule did not read. Used only as a last resort, when the string gives
# neither a document nor a year (so they change neither the regime nor the flags of any row that had one):
#   itraconazole: only M27-A to M27-S3 published breakpoints (S <=0.125, SDD 0.25-0.5, R >=1); there are no
#   species-specific ones
#   disc zone diameters (mm): M44-A2/M44-S3 versus M44 3rd ed./M60 for C. tropicalis; for zones S goes with
#   >= and R with <=
FALLBACK_PRE_CUT = {"itraconazole": [rf"\bs\s*{LE}\s*0[.,]12", r"\bs\s*<\s*0[.,]25", r"\bsdd\s*0[.,]25\s*-\s*0[.,]5",
                                     rf"\br\s*{GE}\s*1\b(?![.,]\d)", r"\br\s*>\s*1\b(?![.,]\d)"]}
ZONE = re.compile(r"\bmm\b|halo|zone|diameter")
ZONE_SS_CUT = {"fluconazole": [rf"\bs\s*{GE}\s*17\b", rf"\br\s*{LE}\s*13\b"],
               "voriconazole": [rf"\br\s*{LE}\s*14\b", r"\bi\s*15\s*-\s*16\b"]}
ZONE_PRE_CUT = {"fluconazole": [rf"\bs\s*{GE}\s*19\b", rf"\br\s*{LE}\s*14\b", r"\bi\s*15\s*-\s*18\b"],
                "voriconazole": [rf"\br\s*{LE}\s*13\b", r"\bi\s*14\s*-\s*16\b"]}
# General markers: only valid for the agents whose breakpoints CLSI revised in 2010-2012
REVISED = re.compile(r"revised|reviewed|species[- ]?specific|24 ?h revis|"
                     r"new (cut-offs|breakpoints|cbp)|cbp new|pfaller[^;()]{0,25}(2010|2011|2012)|"
                     r"(2010|2011) ?/ ?(2011|2012)|clsi 2011")
# Pfaller 2006 and 2008 are the voriconazole and echinocandin breakpoints of M27-S3: earlier regime
OLD = re.compile(r"of the time|histor|earlier than 2012|earlier documents|\bold\b|"
                 r"pfaller[^;()]{0,25}(2006|2007|2008|2009)")
REVISED_AGENTS = {"fluconazole", "voriconazole"} | ECHINO


def norm_text(x):
    return "" if x is None or (isinstance(x, float) and x != x) else str(x).lower().strip()


def clsi_documents(raw):
    """CLSI documents named in the criterion string."""
    k = norm_text(raw)
    docs = []
    for pat, doc in CLSI_DOC_PATTERNS:
        if re.search(pat, k) and doc not in docs:
            docs.append(doc)
    # loose 'm44', with no M44 document identified: no version
    if re.search(r"m44\b", k) and not any(d.startswith("M44") for d in docs):
        docs.append("M44 unversioned")
    return docs


def agent_segments(raw, agent):
    """Pieces of the string that refer to the agent: from each mention of the agent to the next
    mention of another agent. If the string names no agent, the whole string; if it names
    others but not this one, an empty list, because their breakpoints are not this agent's."""
    k = norm_text(raw)
    hits = []
    for ag, pat in AGENT_ALIAS.items():
        hits += [(m.start(), ag) for m in re.finditer(pat, k)]
    hits += [(m.start(), "echino") for m in re.finditer(ECHINO_ALIAS, k)]
    hits += [(m.start(), "azole_class") for m in re.finditer(AZOLE_ALIAS, k)]
    hits += [(m.start(), "other") for m in re.finditer(OTHER_AGENTS, k)]
    if not hits:
        return [k]
    hits.sort()
    segs = []
    for i, (pos, ag) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else len(k)
        if ag == agent or (ag == "echino" and agent in ECHINO) or (ag == "azole_class" and agent in AZOLES):
            segs.append(k[pos:end])
    return segs


# Row with CLSI and EUCAST: many strings declare the method of one standard and the criterion of the
# other ('EUCAST E.Def 7.1; CLSI M27-A3 breakpoints') or the ECV of one and the breakpoint of the other.
# The regime is set by the interpretive criterion, not by the method (Rule 1).
CRIT_CLSI = re.compile(r"(cbp|\bpc\b|cut-offs?|breakpoints?|interpret\w*( with| according to| by)?|criteri(on|a))[^;]{0,15}"
                       r"\b(clsi|nccls)|\b(clsi|nccls)[^;/]{0,6}(cbp|cut-offs?|breakpoints?)|according to (the )?(clsi|nccls)")
CRIT_EUCAST = re.compile(r"(cbp|\bpc\b|cut-offs?|breakpoints?|interpret\w*( with| according to| by)?|criteri(on|a))[^;]{0,15}"
                         r"\beucast|\beucast[^;/]{0,6}(cbp|cut-offs?|breakpoints?)|according to (the )?eucast")
# 'EUCAST' with its document and version ('EUCAST E.Def 7.1', 'EUCAST v10', 'EUCAST 2008'), removed from
# the string when the criterion is CLSI
EUCAST_TOKEN = re.compile(r"\beucast\b\s*(e\.? ?def|e\.? ?dis|edef|bp|ecv|v(ersion)?)?\s*[\d.]*")
EUCAST_ECV_ONLY = re.compile(r"\beucast[^;/]{0,8}\becv|\becv[^;/]{0,8}\beucast")


def _mentions(clause, agent):
    k = clause
    if re.search(AGENT_ALIAS.get(agent, r"$^"), k):
        return True
    if agent in ECHINO and re.search(ECHINO_ALIAS, k):
        return True
    return agent in AZOLES and bool(re.search(AZOLE_ALIAS, k))


def _mentions_any(clause):
    return any(_mentions(clause, ag) for ag in AGENT_ALIAS) or bool(re.search(OTHER_AGENTS, clause))


def agent_text(raw, agent):
    """Text of the criterion that applies to the agent. If the string is divided into clauses (';')
    and some name the agent, those clauses count plus the ones that name no agent; otherwise the
    whole string. 'CLSI M60 (azoles); EUCAST v10 (amphotericin B)' gives 'CLSI M60 (azoles)' for
    fluconazole and 'EUCAST v10 (amphotericin B)' for amphotericin B."""
    k = norm_text(raw)
    clauses = [c for c in k.split(";") if c.strip()]
    if len(clauses) < 2:
        return k
    own = [c for c in clauses if _mentions(c, agent)]
    if not own:
        return k
    general = [c for c in clauses if not _mentions_any(c)]
    return ";".join(own + general)


def criterion_standard(raw, agent):
    """'CLSI', 'EUCAST' or None for a row whose string names both standards."""
    k = agent_text(raw, agent)
    if not re.search(r"\b(clsi|nccls|eucast)\b", k):
        k = norm_text(raw)
    c, e = bool(re.search(r"\b(clsi|nccls)\b", k)), bool(re.search(r"\beucast\b", k))
    if c != e:
        return "CLSI" if c else "EUCAST"
    c, e = bool(CRIT_CLSI.search(k)), bool(CRIT_EUCAST.search(k))
    if c != e:
        return "CLSI" if c else "EUCAST"
    if EUCAST_ECV_ONLY.search(k) and not e and not re.search(r"\bclsi\b[^;/]{0,20}\becv|\bm59\b", k):
        return "CLSI"
    return None


def declared_cutoff_regime(raw, agent):
    """'CLSI_SS', 'CLSI_pre2012' or None according to the breakpoints the string declares for the agent."""
    key = "echino" if agent in ECHINO else agent
    if key not in SS_CUT:
        return None
    segs = agent_segments(raw, agent)
    text = " ".join(segs)
    if not text:
        return None
    ss = any(re.search(p, text) for p in SS_CUT[key])
    pre = any(re.search(p, text) for p in PRE_CUT[key])
    if ss and not pre:
        return "CLSI_SS"
    if pre and not ss:
        return "CLSI_pre2012"
    return None


# (2026-10-26) MIC thresholds published by CLSI for C. tropicalis (R and S), to recognize an "author's"
# breakpoint that is in fact the standard's. Only the signs >= and <= (">1" is not ">=1").
AUTHOR_STD = {
    "fluconazole": {"CLSI_pre2012": [rf"{GE}\s*64\b", rf"{LE}\s*8\b"], "CLSI_SS": [rf"{GE}\s*8\b", rf"{LE}\s*2\b"]},
    "voriconazole": {"CLSI_pre2012": [rf"{GE}\s*4\b", rf"{LE}\s*1\b(?![.,]\d)"],
                     "CLSI_SS": [rf"{GE}\s*1\b(?![.,]\d)", rf"{LE}\s*0[.,]12"]},
    "itraconazole": {"CLSI_pre2012": [rf"{GE}\s*1\b(?![.,]\d)", rf"{LE}\s*0[.,]12"]},
}


# (2026-10-26) Breakpoint defined by the author: "author's", "of the authors", "authors' own", "authors'
# categories", "defined by the authors", "author (s<=4 ...)"... The note that the authors applied a
# versioned standard does not count: 'R according to EUCAST v11.0 (authors)', 'CLSI M100 (according to authors)'.
AUTHOR = re.compile(r"\bauthors?\b|\bauthors?'")
AUTHOR_APPLIED_STANDARD = re.compile(r"(eucast|clsi|nccls)[^;()]*\((according to )?(the )?authors\)")


def author_cut_matches(raw, agent):
    """CLSI regime whose threshold matches the 'author's' breakpoint declared for the agent, or None."""
    if agent not in AUTHOR_STD:
        return None
    text = " ".join(agent_segments(raw, agent))
    hits = [reg for reg, pats in AUTHOR_STD[agent].items() if any(re.search(p, text) for p in pats)]
    return hits[0] if len(hits) == 1 else None


def fallback_cutoff_regime(raw, agent):
    """(2026-10-26, B10) Regime from itraconazole breakpoints or disc zone diameters, if the string declares them."""
    text = " ".join(agent_segments(raw, agent))
    if not text:
        return None
    if agent in FALLBACK_PRE_CUT and any(re.search(p, text) for p in FALLBACK_PRE_CUT[agent]):
        return "CLSI_pre2012"
    if agent in ZONE_SS_CUT and ZONE.search(text):
        ss = any(re.search(p, text) for p in ZONE_SS_CUT[agent])
        pre = any(re.search(p, text) for p in ZONE_PRE_CUT[agent])
        if ss != pre:
            return "CLSI_SS" if ss else "CLSI_pre2012"
    return None


def row_regime(agent, interp_standard, interp_raw, pub_year):
    """Regime of a resistance row by clinical breakpoint (mechanical).

    Returns (regime, basis, flag). basis says where the regime comes from:
      declared_cutoff  breakpoints declared in the string itself (Rule 1)
      revised_marker   the string says 'revised CBP', 'Pfaller 2011'... (agents revised in 2012)
      document         CLSI document identified
      year_in_string   year written in the string (Rule 1)
      publication_year publication year <= 2012 (AR6): the only inferred basis
      eucast           EUCAST standard
    regime None: excluded, and basis gives the reason.
    flag: 'pre2012_doc_published_2013plus' when a pre-2012 document appears in a report published
    from 2013 on (AR6, SX1); 'inferred_from_year' for the basis inferred from the publication year;
    'inferred_from_cutoffs' when the regime comes from declared breakpoints without a document
    (Rule 1); 'criterion_split' when the string names CLSI and EUCAST and the criterion is separated
    from the method.
    """
    st = str(interp_standard)
    clsi, eucast = "CLSI" in st, "EUCAST" in st
    split = ""
    if clsi and eucast:
        crit = criterion_standard(interp_raw, agent)
        if crit is None:
            return None, "mixed_standard", ""
        clsi, eucast, split = crit == "CLSI", crit == "EUCAST", "criterion_split"
    if eucast:
        return "EUCAST", "eucast", split
    if not clsi:
        return None, "not_clsi_or_eucast", ""
    raw = norm_text(interp_raw)
    txt = agent_text(interp_raw, agent)
    if split:   # EUCAST markers and documents do not count for the CLSI regime
        raw = EUCAST_TOKEN.sub(" ", raw)
        txt = EUCAST_TOKEN.sub(" ", txt)

    def fl(*f):
        return "; ".join(x for x in (split,) + f if x)
    by_cut = declared_cutoff_regime(raw, agent)
    if by_cut:
        # Rule 1: the version comes from the declared breakpoints, not from a document: flagged
        return by_cut, "declared_cutoff", fl("inferred_from_cutoffs")
    # (2026-10-26, team decision) author's breakpoint for this agent: it is not the standard's CBP (AR6),
    # even if the string names a CLSI document as the method. It only counts if it matches the standard's
    # breakpoints, and declared_cutoff_regime above already resolved that.
    if AUTHOR.search(txt) and not AUTHOR_APPLIED_STANDARD.search(txt):
        m = author_cut_matches(raw, agent)
        if m:
            return m, "declared_cutoff", fl("inferred_from_cutoffs", "author_cut_equals_standard")
        return None, "author_breakpoint", ""
    seg = " ".join(agent_segments(raw, agent))   # markers only count in the agent's piece
    if agent in REVISED_AGENTS and OLD.search(seg):
        return "CLSI_pre2012", "revised_marker", fl()
    if agent in REVISED_AGENTS and REVISED.search(seg):
        return "CLSI_SS", "revised_marker", fl()
    # documents and years: those of the agent's clause; if it has none, those of the whole string
    docs = (set(clsi_documents(txt)) - {"M44 unversioned"}) or (set(clsi_documents(raw)) - {"M44 unversioned"})
    if docs & SS_DOCS:
        return "CLSI_SS", "document", fl()
    if docs & PRE_DOCS:
        flag = "pre2012_doc_published_2013plus" if (pub_year is not None and pub_year == pub_year
                                                    and pub_year >= 2013) else ""
        return "CLSI_pre2012", "document", fl(flag)
    yrs = [int(y) for y in (YEAR.findall(txt) or YEAR.findall(raw))]
    if yrs:
        return ("CLSI_SS" if max(yrs) >= 2012 else "CLSI_pre2012"), "year_in_string", fl()
    fb = fallback_cutoff_regime(raw, agent)
    if fb:
        return fb, "declared_cutoff", fl("inferred_from_cutoffs")
    if pub_year is not None and pub_year == pub_year and pub_year <= 2012:
        return "CLSI_pre2012", "publication_year", fl("inferred_from_year")
    return None, "version_not_inferable", fl()


def has_mic(row):
    """The row carries some concentration (MIC50, MIC90, range or geometric mean)."""
    for c in ("mic50_mg_l", "mic90_mg_l", "mic_min_mg_l", "mic_max_mg_l", "mic_gm_mg_l"):
        v = row.get(c) if isinstance(row, dict) else getattr(row, c, None)
        if v is not None and v == v and str(v).strip() not in ("", "nan"):
            return True
    return False


UNVERSIONED_BASES = {"publication_year", "eucast_unversioned"}
# flags removed by SX1 (inferred version, or a pre-2012 document in a recent publication)
SX1_FLAGS = ("pre2012_doc_published_2013plus", "inferred_from_year", "inferred_from_cutoffs")


def rule4_excluded(basis, mic, has_r):
    """Protocol Rule 4 (mechanical): the resistance row is left out of the pooled estimates when the
    version of its criterion is not declared in any form (no document, no written year, no declared
    breakpoints) and it carries no MIC that could remedy it. The unversioned bases are
    'publication_year' (CLSI, version inferred from the publication year) and 'eucast_unversioned'."""
    return basis in UNVERSIONED_BASES and not mic and has_r


# ------------------------------------------------------------------------------------------------
# 2. Rows that do not measure prevalence (D3, AR20): proposal from the extraction notes
# ------------------------------------------------------------------------------------------------
SELECTED = re.compile(
    r"selected|subset|inclusion criteri|does not estimate prevalence|not (apt|usable|suitable|"
    r"representative)\w*( for)?( the)? prevalence|not representative|selected panel|enriched|"
    r"all (the )?isolates (of the collection )?(were|are|exceed|exceeded) (resistant|non[- ]susceptible)|"
    r"selected sample|strains were excluded|only (the )?(\d+ )?(resistant|non[- ]susceptible|selected) isolates|"
    r"only (the )?(\d+ )?isolates (with [^.;]{0,15}(halo|zone|mic)|fns)|resistant (isolates )?sent|"
    r"sent (for|because of) (resistance|failure)|referred (for|because of) (resistance|failure)")
RANDOM = re.compile(r"at random|random")
PHENO_WORDS = re.compile(r"resist|suscept|sensitiv|phenotyp|\bfns\b|\bnwt\b|\bfr\b|\bmic|halo|zone|fks|erg11|"
                         r"mutation|clade|g464s|y132f|failure|echinocand|azol")
INFERRED_DEN = re.compile(r"denominator (\d+ )?(inferred|deduced|estimated|supposed)|denominator [^.;]{0,25}inferred|"
                          r"inferred denominator|\bn (tested )?inferred|denominator = n of|assuming that (all|they were tested)")
# denominator that is the sum of the reported categories: not inferred, but checked
DEN_FROM_SUM = re.compile(r"inferred\w* from the sum|sum of (the table|the categor|s, ?i|s\+)")
COMPILED = re.compile(r"literature ?/ ?sra|\bsra\b|(public|published|literature|downloaded) genomes?|genomes? (published|from (the )?"
                      r"literature|downloaded)|public databases?|\bncbi\b|isolates from (the )?literature|"
                      r"compiled|previously published data|genome meta-?analysis|meta-?analysis of genomes")


def d3_proposal(note_row, note_report=""):
    """AR20 proposal for a row. Returns (reason or '', evidence)."""
    t = norm_text(note_row)
    r = norm_text(note_report)
    if COMPILED.search(t) or COMPILED.search(r):
        m = COMPILED.search(t) or COMPILED.search(r)
        return "compiled_dataset", m.group(0)
    if INFERRED_DEN.search(t):
        if DEN_FROM_SUM.search(t):
            return "denominator_check", DEN_FROM_SUM.search(t).group(0)
        return "inferred_denominator", INFERRED_DEN.search(t).group(0)
    m = SELECTED.search(t)
    if m and not RANDOM.search(t) and PHENO_WORDS.search(t):
        return "phenotype_selected", m.group(0)
    if m and not RANDOM.search(t):
        return "selected_check", m.group(0)
    return "", ""


# ------------------------------------------------------------------------------------------------
# 3. Species identification (proposal, RB4 and SA8)
# ------------------------------------------------------------------------------------------------
SPECIES_RULES = [
    ("molecular", r"pcr|sequenc|\bits\b|d1/d2|d1-d2|\blsu\b|wgs|genom|rflp|molecular"),
    ("MALDI_TOF", r"maldi"),
    ("automated", r"vitek|microscan|phoenix|autoscan|\batb\b|automated"),
    ("biochemical", r"\bapi\b|api ?20|id ?32|32 ?c id|auxacolor|rapid ?yeast|uni-?yeast|biochem|"
                    r"as+[iy]milation|fermentation|z[iy]mogram|aux[ao]nogram"),
    ("chromogenic", r"chrom|hicrome|candida ?id"),
    ("conventional", r"germ tube|germinal tube|germinative tube|chlamydosp|corn ?meal|cornmeal|"
                     r"morpholog|conventional|dalmau|phenotypic|microscop|physiologic|"
                     r"warren|hazen|kurtzman|yarrow|barnett|conant|dolan|van der walt|lodder|de hoog|larone"),
]


def _plain(x):
    t = unicodedata.normalize("NFKD", norm_text(x)).encode("ascii", "ignore").decode()
    return t


MOL_NEG = re.compile(r"(without|no) (molecular )?(confirmation |identification )?molecular|"
                     r"(not|no|without) (been )?(performed|confirmed|used|applied|carried out)[^.;]{0,40}(molecular|pcr|sequenc)|"
                     r"\bnot molecular|non-?molecular|without pcr|no pcr|without sequenc|no sequenc")
MOL_RESTRICTED = re.compile(
    r"(molecular|pcr|sequenc\w*)[^.;]{0,30}\bonly (for|in|of|to|on)\b|"
    r"\bonly (for|in|of|to|on) (a |the |one )?(patients? )?(subset|isolates?\b|c\. ?)|"
    r"subset|\bsome( isolates)?\b|part of the isolates|\bin part\b(?! of)|\bpartly\b|\b(for|in|of) [\w. ]{1,25} only\b|"
    r"c\. ?\w+-only|dubious|where (necessar|needed|required)|when [^.;]{0,8}confidence|when unreliable|"
    r"\bonly (for|in|of|to|on) \d+|"
    r"\bwhen (it was |it is |was |is |were )?(necessar|needed|required|fail|there (was|were|is|are)|not )|"
    r"\bwhen (the )?(probability|confidence|identification)|"
    r"(in|for) (the )?(doubtful|discordant|unresolved|ambiguous|uncertain) cases?|discordan|"
    r"not identified|unidentified|doubtful|atypical|selected|\bif (there was )?(a )?discordance|"
    r"(for|of|in) (the )?([\w.]+ ){0,3}complex(es)?\b|pcr specific (to |for )?(the )?complex|"
    r"(pcr|sequenc\w*|molecular identification|molecular confirmation|its|d1/d2)[^.;]{0,20}"
    r"(for|of|in|to) (\d+ )?(c\. ?)?(auris|parapsilosis|albicans|glabrata|dubliniensis|krusei|orthopsilosis|"
    r"metapsilosis)")


def classify_species(raw, skip_molecular=False):
    t = _plain(raw)
    for cat, pat in SPECIES_RULES:
        if skip_molecular and cat == "molecular":
            continue
        if re.search(pat, t):
            return cat
    return "not_specified"


def species_proposal(raw):
    """(proposed category, problem). problem '' when the v1 classification holds."""
    base = classify_species(raw)
    if base != "molecular":
        return base, ""
    t = norm_text(raw)
    if MOL_NEG.search(t):
        return classify_species(raw, skip_molecular=True), "negation"
    if MOL_RESTRICTED.search(t):
        return classify_species(raw, skip_molecular=True), "molecular_restricted_or_conditional"
    return base, ""


# ------------------------------------------------------------------------------------------------
# 4. Prior azole exposure on three levels (mechanical; H5 is left for the second report)
# ------------------------------------------------------------------------------------------------
AZ_NOT_DOC = re.compile(r"^not recorded|not (documented|reported|stated|mentioned|specified)|"
                        r"unknown|no data|no information")
AZ_ABSENT = re.compile(r"^none\b|no exposure|not exposed|na[iï]ve|no prior (antifungal|azole) treatment|"
                       r"did not receive (treatment|azoles|antifungals)\b|absence of (exposure|treatment)")


def azole_exposure_3(raw):
    t = norm_text(raw)
    if not t:
        return "not_documented"
    if AZ_ABSENT.search(t):
        return "documented_absent"
    if AZ_NOT_DOC.search(t):
        return "not_documented"
    return "documented_present"


# ------------------------------------------------------------------------------------------------
# 5. Pairs of reports that may be the same collection (proposal, EC12 and AR1)
# ------------------------------------------------------------------------------------------------
PROGRAMMES = [("CHIF-NET", r"chif[- ]?net"), ("CANDIPOP", r"candipop"), ("SENTRY", r"sentry"),
              ("ARTEMIS", r"artemis"), ("SCOPE", r"\bscope\b"), ("ECMM", r"\becmm\b"),
              ("NRZMyk", r"nrz ?myk|nationales referenzzentrum"), ("TRANSNET", r"transnet"),
              ("ATLAS", r"\batlas\b"), ("PATH", r"\bpath alliance\b"), ("CANDIDA-RIS", r"candida[- ]?ris"),
              ("FUNGISCOPE", r"fungiscope"), ("EMERGE", r"\bemerge\b"), ("ARLG", r"\barlg\b"),
              ("CDC-EIP", r"emerging infections program|\beip\b"), ("IFI-SURV", r"ifi[- ]?surv\b"),
              ("SIRCLE", r"sircle"), ("MYCOMIC", r"mycomic"), ("FIDELIO", r"fidelio"),
              ("CARST-fungi", r"carst"), ("JIMS", r"\bjims\b|japan invasive mycosis")]
# Words that do not distinguish one institution from another. Ordinals (first, second...) are NOT here:
# the first and second affiliated hospitals of the same university are different hospitals.
GENERIC = set("""
of the and for in at a an do da dos das di du des le et und der die
hospital hospitals hospitais hospitalar hosp
university universities universidade universitat universite universitaire universita univ
medical medicine college colleges school schools faculty faculdade department dept division
center centre centers centres institute institut national network surveillance study
program programme project affiliated people peoples general central
clinical clinics clinic laboratory laboratories lab microbiology mycology sciences science health
reference complex teaching research children womens women maternal municipal
provincial city state regional district county public tertiary care multicentre multicenter
multicentric multiple several nine eight seven six five four three two one other others
spanish brazilian chinese korean iranian indian
""".split())
ORDINALS = {"first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"}


def norm_inst(text):
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def inst_tokens(text):
    """Distinctive words of the description of the institution or programme."""
    toks = set(norm_inst(text).split())
    return {w for w in toks if (w in ORDINALS or (w not in GENERIC and not w.isdigit() and len(w) > 2))}


def inst_segments(text):
    """A description can name several institutions: they are split on ; + / and parentheses
    (not on commas, which usually separate the institution from its city)."""
    return [x for x in re.split(r"[;+/()\[\]]", str(text)) if x.strip()]


def inst_jaccard(a, b):
    """Highest Jaccard index between the distinctive words of one piece of each description
    (0 if a description has no distinctive word)."""
    best = 0.0
    for sa in inst_segments(a):
        ta = inst_tokens(sa)
        if not ta:
            continue
        for sb in inst_segments(b):
            tb = inst_tokens(sb)
            if tb:
                best = max(best, len(ta & tb) / len(ta | tb))
    return round(best, 2)


SAME_INST = 0.5     # probably the same institution: Jaccard >= 0.5 between distinctive words
MIN_N_IDENTICAL = 10  # identical figures only count if the stratum has at least 10 isolates tested


def programmes_of(text):
    t = norm_text(text)
    return {name for name, pat in PROGRAMMES if re.search(pat, t)}


def periods_overlap(a0, a1, b0, b1):
    if a0 is None or b0 is None or a0 != a0 or b0 != b0:
        return False
    a1 = a0 if a1 is None or a1 != a1 else a1
    b1 = b0 if b1 is None or b1 != b1 else b1
    return a0 <= b1 and b0 <= a1


def nested(a0, a1, b0, b1):
    a1 = a0 if a1 is None or a1 != a1 else a1
    b1 = b0 if b1 is None or b1 != b1 else b1
    return (a0 <= b0 and b1 <= a1) or (b0 <= a0 and a1 <= b1)


def pair_proposal(p):
    """YES / PARTIAL / REVIEW proposal for a candidate pair, with its reason in one line.
    p: programme (string, empty if they share no programme), jaccard, n_a, n_b, same_period,
    nested, identical_counts (strata with the same figures and at least MIN_N_IDENTICAL tested),
    identical_example."""
    link = bool(p["programme"]) or p["jaccard"] >= SAME_INST
    same_n = (p["n_a"] == p["n_a"] and p["n_b"] == p["n_b"] and p["n_a"] == p["n_b"] and p["n_a"] >= 10)
    if link and p["identical_counts"]:
        return "YES", f"same institution or programme and same figures in {p['identical_counts']} stratum(s): {p['identical_example']}"
    if link and same_n and p["same_period"]:
        return "YES", "same institution or programme, same period and same number of isolates"
    if link and p["nested"]:
        return "PARTIAL", "same institution or programme; one period contains the other"
    if link:
        return "REVIEW", "same institution or programme with overlapping periods; check in the text"
    return "REVIEW", f"same figures in {p['identical_counts']} stratum(s) with no other match: {p['identical_example']}"


# ------------------------------------------------------------------------------------------------
# 6. Exclusion reason of the 500 reports excluded at extraction (proposal)
# ------------------------------------------------------------------------------------------------
WRONG_DOC = re.compile(
    r"does not correspond|corresponds to (an)?other (\w+ )?(article|publication|abstract|case)|corresponds to the abstract|"
    r"(pdf|text)[^.;]{0,40}\b(is|was|contains|corresponds to) (only )?(the |a |an )?(\w+ ){0,4}(user guide|"
    r"polic|technical sheet|list of reviewers|instructions (for|to) authors|advertis|"
    r"technical note|editorial material|caption of a figure|nursing report|(japanese|persian) article)|"
    r"without (the )?text of the article|no text of the article|does not contain the article|wrong full text|"
    r"is not the article|unrelated to (candida|c\. tropicalis)|not about candida|does not deal with candida|"
    r"not related to c\. tropicalis|illegible|(corrupt|damaged) (encoding|coding)|"
    r"full text not available|only the caption|publisher's advertising|does not mention c\. tropicalis|"
    r"no mention of c\. tropicalis")
RETRACTED = re.compile(r"retract")
SCANNED = re.compile(r"scanned|truncated")
REFERS_ID = re.compile(r"identification[^.;]{0,60}\b(refer(s|red)?|remit\w*) to\b|\b(refer(s|red)?|remit\w*) to\b[^.;]{0,60}identification")
REVIEW = re.compile(r"\b(narrative|systematic|bibliographic|literature) review|\breview (of|on|about)\b|\beditorial\b|"
                    r"\bletter to\b|\bcommentary\b|\bcomment\b")
NO_ISOLATE = re.compile(
    r"direct (molecular )?detection|without isolation|without isolates|there was no isolation|there are no isolates|"
    r"culture[- ]independent|without culture|no culture|metabarcod|\bm?ngs\b|negative blood culture|"
    r"(panfungal|direct|broad[- ]range|semi-?nested) pcr|pcr (on|in) (a )?biops|"
    r"detected (only |exclusively )?by (pcr|ngs|mngs|sequencing)|only detected by")
REF_STRAINS = re.compile(r"reference strains?|\batcc\b|\bcbs\b|collection strains?|strains? from (a |the )?collection|"
                         r"collection isolates|isolates from (a |the )?collection")
NOT_SPECIES = re.compile(r"\bno c\. tropicalis (isolates?|was isolated|is included)\b|does not include c\. tropicalis|"
                         r"c\. tropicalis (was|is) not (isolated|confirmed)|no c\. tropicalis data|c\. tropicalis no data|"
                         r"no data (for|on|of) c\. tropicalis")
EC_CITED = re.compile(r"\b(ec(?:1[0-3]|[1-9]))\b")
AST_NOT_FOR_SPECIES = re.compile(
    r"(susceptibility|sensitivity|mic|antifungigram|\bast\b|tests?|results?)[^.;]{0,90}\bonly "
    r"(for|in|of|to|on|reported|performed|determined|presented)|"
    r"no (results|mic|data) (were|was|are|is) (reported|presented|shown)[^.;]{0,50}(for|of|by)|"
    r"(mic|results|data)[^.;]{0,20}not (reported|presented|shown)[^.;]{0,50}(by species|for c\. "
    r"tropicalis|of c\. tropicalis)|aggregat|not disaggregat|without disaggregat|no breakdown|without breakdown|"
    r"globally|\bglobal\b|overall|data not shown|not shown|not (species[- ])?specific|no susceptibility data "
    r"(of|for|by|specific)")
SUSC = r"(antifungal )?(susceptibility|sensitivity)"
GAP = r"(?:[^.;]|(?<=\bc)\.)"   # free text, letting 'c. tropicalis' through
NO_AST = re.compile(
    rf"\b(no|not|never)\b (\w+ ){{0,2}}(tested|evaluated|determined|analy[sz]ed|performed|reported|presented)\b[^.;]{{0,15}}(any )?"
    rf"(antifungals?|{SUSC}|tests?|testing)|"
    rf"\b(does|do|did|were|was|is|are) not (\w+ ){{0,1}}(include|contain|test|evaluate|determine|analy[sz]e|perform|report|present|provide|"
    rf"carry out|done|performed|tested|evaluated|reported|included)\w*[^.;]{{0,40}}({SUSC}|antifungigram|antifungal|resistance)|"
    rf"(tests|testing|antifungigram)[^.;]{{0,40}}(was|were|is|are) not (performed|reported|done|carried out|made)|"
    rf"no c\. tropicalis (isolate )?was tested|"
    rf"\b(no|without) ({SUSC} )?(results|data) (of|on) {SUSC}|\b(without|no) (any )?{SUSC} test|(without|no) (any )?(antifungal )?(tests?|testing) "
    rf"(of {SUSC}|for {SUSC}|antif)|\b(without|no) (antifungal )?(susceptibility|sensitivity)\b|"
    rf"\bonly (in|for|on|to) (the )?bacteria|\bbacteria only|antibacterial|bacterial antibiotics?|kirby-?bauer|"
    rf"optamos por n[aã]o realizar|(state|declare)s? (explicitly )?(that )?(they )?(did not|had not|have not) (perform|evaluat|analy)|"
    rf"neither mic nor categor|no tests were performed|no {SUSC} (tests?|testing|data)|"
    rf"\bno {GAP}{{0,40}}(susceptibility|sensitivity) test\w* (is|was|were|are) (reported|performed|presented|done)|"
    rf"antifungals? (were|was) not tested|\bno (\w+ ){{0,2}}antifungals? (were|was) tested|"
    rf"\b(does|do|did) not (report|perform|evaluate|determine|present)\w*{GAP}{{0,40}}{SUSC}")
NONSTANDARD_AST = re.compile(r"non-?standard|not standardi[sz]ed|clinically defined|clinical definition|"
                             r"without (a )?method,? (or|nor)? ?(a )?standard|does not describe (the )?method|"
                             r"method (of susceptibility )?and standard not declared|does not (meet|comply with) ic8")

ID_REFERRED = re.compile(r"according to (the |a |an )?(report|study|article|protocol|ref)|\bref\. ?\d|"
                         r"\[\d+\]|referred to (publicat|studies)|\b(refer(s|red)?|remit\w*) to\b|previously described|previous study|"
                         r"previous report|previous publications")
NOT_STATED = re.compile(r"^(not recorded|not declared|not specified|not stated|unknown|"
                        r"not detailed|not described|not legible|illegible|nd\b|n/a)")


def _blank_or_not_stated(v):
    return is_blank(v) or bool(NOT_STATED.search(norm_text(v)))


def _missing(n_tropicalis, compartments, country, species_method):
    return [n for n, v in (("n of C. tropicalis", n_tropicalis), ("compartment", compartments),
                           ("country", country), ("identification method", species_method))
            if _blank_or_not_stated(v)]


def exclusion500_proposal(reason, n_tropicalis, compartments, country, species_method):
    """Proposal for a report excluded at extraction ('No extractable data'). Protocol application
    rule: a report enters the review with IC1, IC2, IC5, IC6, IC7 and at least IC3 or IC4.
    EC6 and EC7 refer to the susceptibility data: a report without susceptibility testing, or whose
    susceptibility cannot be used, is not excluded by them if it contributes C. tropicalis isolates
    assignable to a compartment (IC3); it then contributes to SQ1. Order: first what prevents reading
    the report, then the exclusions of the whole report, last what only affects susceptibility."""
    t = norm_text(reason)
    missing = _missing(n_tropicalis, compartments, country, species_method)
    n0 = is_blank(n_tropicalis) or safe_int(n_tropicalis) == 0
    if RETRACTED.search(t):
        return "REVIEW", "retracted article: not a valid source if the retraction is confirmed"
    if WRONG_DOC.search(t):
        return "NOT_RETRIEVED", "the available text is not the record's, or it is illegible; the correct PDF counts if obtained"
    if SCANNED.search(t):
        return "REVIEW", "scanned or truncated PDF: the extraction did not read it; requires human reading of the original"
    if NO_ISOLATE.search(t):
        return "EXCLUDE_EC1", "detection without isolation: the unit of observation is the isolate"
    if REFERS_ID.search(t):
        return "EXCLUDE_EC2", "identification is referred to another publication (EC2 triage of 2026-10-23, group B)"
    if NOT_SPECIES.search(t) and n0:
        return "EXCLUDE_EC1", "there are no C. tropicalis isolates in the report"
    if REF_STRAINS.search(t):
        if is_blank(compartments):
            return "EXCLUDE_EC8", "only reference or collection strains, without documented origin"
        return "REVIEW", "reference or collection strains: check whether they have a documented origin (EC8)"
    if REVIEW.search(t):
        if n0:
            return "EXCLUDE_EC13", "review, letter or editorial without primary data"
        return "REVIEW", "letter or commentary with own isolates: EC13 does not apply if it carries primary data"
    m = EC_CITED.search(t)
    if m and m.group(1) not in ("ec6", "ec7"):
        return f"EXCLUDE_{m.group(1).upper()}", f"the extractor cites {m.group(1).upper()}; check"
    if NONSTANDARD_AST.search(t) or (m and m.group(1) == "ec6"):
        if missing:
            return "REVIEW", "susceptibility without standard method or criterion; missing " + ", ".join(missing)
        return "REVIEW", ("susceptibility without standard method or criterion: EC6 if it reports susceptibility without "
                          "method, criterion or MIC; otherwise it meets IC3 and contributes to SQ1")
    if NO_AST.search(t) or AST_NOT_FOR_SPECIES.search(t) or (m and m.group(1) == "ec7"):
        why = ("without susceptibility testing" if NO_AST.search(t) else
               "susceptibility not reported for C. tropicalis or not disaggregable")
        if missing:
            return "REVIEW", why + "; missing " + ", ".join(missing) + " in the extraction"
        # same criterion as the EC2 triage of 2026-10-23 on the identification method
        sm = norm_text(species_method)
        if ID_REFERRED.search(sm):
            return "EXCLUDE_EC2", why + "; identification is referred to another source (EC2 triage of 2026-10-23, group B)"
        if classify_species(species_method) == "not_specified":
            return "REVIEW", why + "; generic identification method: EC2 unless the PDF specifies it (groups A and D of the 2026-10-23 triage)"
        return "INCLUDE_SQ1", why + "; the C. tropicalis count meets IC3 and contributes to SQ1"
    return "REVIEW", "reason cannot be classified automatically"


def safe_int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def is_blank(x):
    return x is None or (isinstance(x, float) and x != x) or str(x).strip() in ("", "nan", "None")


def frame_blank(series):
    return series.isna() | series.astype(str).str.strip().isin(["", "nan", "None"])


__all__ = [n for n in dir() if not n.startswith("_")]
