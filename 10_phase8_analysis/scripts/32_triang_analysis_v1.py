"""Auxiliary triangulation with isolate-level repository data (PubMLST, NCBI BioSample and SRA).

Registered in the protocol as an auxiliary triangulation analysis: repository records are not studies, are
reported separately and are never merged with the pooled proportions of the review.

Rules (written before the comparison with the review was computed):
  1. Unit: the isolate. PubMLST: one record per isolate. NCBI: one BioSample per isolate after excluding
     laboratory-derived samples (experimental replicates, culture conditions, reference or collection strains,
     metagenomic assemblies) and collapsing BioSamples that share the strain or isolate name within the same
     BioProject (or submitter when there is no BioProject).
  2. Compartment: assigned from the source fields with the ordered keyword rules of RULES below, applied to
     each distinct combination of fields; the combinations and their assignment are written to a dictionary
     for review. Repositories never document the agronomic management of a natural matrix, so natural matrices
     go to C5 only in its broad reading (the reading of SA1); fruit and cultivated plants go to C3.
  3. Resistance (PubMLST only, the only source with MICs): fluconazole resistant when MIC >= 8 mg/L, the
     category in which the CLSI species-specific breakpoint (R >= 8) and the EUCAST breakpoint (R > 4)
     coincide for doubling dilutions; voriconazole resistant when MIC >= 1 mg/L (CLSI species-specific).
     Censored values are classified only when the censoring leaves the category unambiguous.
     Exact binomial 95% CI; no pooling, since the records carry no study structure.
  4. Submission structure (a single large deposit of related or resistance-selected isolates can dominate a
     repository): the submission is the BioProject (or submitter) in NCBI and the sender in PubMLST. For each
     compartment the number of submissions and the share of the largest one are reported, the distribution is
     also given with each submission counted once in each compartment it contributes to, and the resistance
     proportion is also given without the largest sender.
  5. Region: continent of the isolate, compared with the review by WHO region only descriptively.
Usage: python 32_triang_analysis_v1.py DATA_DIR OUT_DIR
"""
import csv, glob, json, math, os, re, sys, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_log  # noqa: E402

BAD = {"", "missing", "not collected", "not applicable", "na", "n/a", "unknown", "not available", "no_host"}

def v(r, *keys):
    for k in keys:
        x = (r["attributes"].get(k) or "").strip()
        if x.lower() not in BAD:
            return x
    return ""

LAB = re.compile(r"replicat|\brep\s?\d|\bcontrol\b|treated|phenol|fermentation tank|culture with|rnaseq|\bypd\b|"
                 r"nadca|mya-3404|cbs ?94\b|nrrl|nbrc|jcm ?\d|atcc|untagged|metagenom|resequencing|"
                 r"^culture$|neat-ypd|\bdox\b|adaptor|teto-|_(hom|rpmi|spglu)-\d|opaque|qs-ph|^ct_\d_\d+$|"
                 r"wor1|^parent$|library|mngs|mixed culture", re.I)
HUMAN_SRC = re.compile(r"clinical|blood|urin|sputum|patient|\bbal\b|lavage|catheter|\bcvc\b|wound|\bpus\b|\bcsf\b|"
                       r"bile|oral|mouth|oroph|pharyn|vagin|vulvo|nail|fe?a?ces|stool|duoden|jejun|pleural|knee|"
                       r"periton|laryn|lung|secretion|trache|\bet[t]?\b|aspirate|saliva|injury|body fluid|swab|"
                       r"subclv|hospitali[sz]ed|human|tissue", re.I)
RULES = [  # (compartment, pattern on isolation source + environment fields + host)
    ("C2", re.compile(r"mastitis|cow|cattle|bovine|chicken|poultry|pig|swine|dog|cat\b|bird|fish|melanotus|insect|"
                      r"animal", re.I)),
    ("C3", re.compile(r"planting soil|agricultur|farm|orchard|crop|cultivat|tobacco|pear|coconut|fruit|vegetable|"
                      r"irrigation", re.I)),
    ("C6", re.compile(r"wwtp|wastewater|sewage|sludge|effluent|influent|street soil|landfill", re.I)),
    ("C4", re.compile(r"hospital surface|surface|bed rail|equipment|sink|environmental swab", re.I)),
    ("C5", re.compile(r"seawater|sea water|freshwater|marine|sediment|benthos|soil|mangrove|wetland|saltern|river|"
                      r"lake|herbaceous|plant|water", re.I)),
]
NOT_ALLOC = re.compile(r"neera|pit mud|ferment|food|yeast isolated|type description|bloodstream infection \(", re.I)

def compartment(src, host, env, stype, title):
    text = " | ".join([src, env, stype, title])
    if LAB.search(text) or LAB.search(host):
        return "excluded_laboratory", "laboratory-derived sample, reference strain or metagenome"
    if len(src) > 120 or NOT_ALLOC.search(src + " " + env):
        return "not_allocated", "source outside the compartment definitions or not a single source"
    h = host.lower()
    if h in ("homo sapiens", "human") or h.startswith("patient"):
        return "C1", "human host"
    if host and not re.search(r"homo|human|patient", h):
        for c, rx in RULES:
            if rx.search(host + " " + src):
                return c, f"host or source matches {c} rule"
    for c, rx in RULES:
        if rx.search(src + " " + env):
            return c, f"source matches {c} rule"
    if HUMAN_SRC.search(src + " " + env):
        return "C1", "human clinical source"
    return "not_allocated", "no usable source field"

def exact_ci(x, n, a=0.05):
    from math import comb
    def cdf(k, p): return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
    def solve(f):
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2
            if f(mid): lo = mid
            else: hi = mid
        return (lo + hi) / 2
    lower = 0.0 if x == 0 else solve(lambda p: 1 - cdf(x - 1, p) < a / 2)
    upper = 1.0 if x == n else solve(lambda p: cdf(x, p) > a / 2)
    return lower, upper

def mic(s):
    """(operator, value) from a PubMLST MIC string, or None."""
    t = (s or "").replace(",", ".").replace("24h", "").replace("48h", "").strip()
    m = re.match(r"^(<=|≤|<|>=|≥|>|=)?\s*([0-9.]+)$", re.sub(r"\s+", " ", t).replace("= ", "="))
    if not m:
        m = re.match(r"^(<=|≤|<|>=|≥|>|=)?\s*([0-9.]+)$", re.sub(r"\s+", "", t))
    if not m:
        return None
    op = {"<=": "<=", "≤": "<=", "<": "<", ">=": ">=", "≥": ">=", ">": ">", "=": "=", None: "="}[m.group(1)]
    return op, float(m.group(2))

def resistant(s, r_min):
    """True/False when unambiguous at R if MIC >= r_min, else None."""
    p = mic(s)
    if p is None:
        return None
    op, x = p
    if op == "=":
        return x >= r_min * 0.98   # 0.13 and 0.125 are the same dilution
    if op in ("<=",):
        return False if x < r_min * 0.98 else None
    if op == "<":
        return False if x <= r_min * 1.02 else None
    if op in (">", ">="):
        return True if x >= r_min * 0.98 or (op == ">" and x * 2 >= r_min * 0.98) else None
    return None

COMPS = ["C1", "C2", "C3", "C4", "C5", "C6"]

def dist_rows(source, unit_comp):
    """unit_comp: list of (submission, compartment) per isolate."""
    rows = []
    alloc = [(s, c) for s, c in unit_comp if c in COMPS]
    subs = collections.defaultdict(collections.Counter)
    for s, c in alloc:
        subs[c][s] += 1
    sub_once = {c: len(subs[c]) for c in COMPS}
    tot_sub = sum(sub_once.values())
    for c in COMPS + ["not_allocated"]:
        n = sum(1 for _, x in unit_comp if x == c)
        if c == "not_allocated":
            rows.append([source, c, n, "", "", "", "", ""]); continue
        big = max(subs[c].values()) if subs[c] else 0
        rows.append([source, c, n, f"{100 * n / len(alloc):.1f}" if alloc else "", sub_once[c],
                     f"{100 * sub_once[c] / tot_sub:.1f}" if tot_sub else "", big,
                     f"{100 * big / n:.1f}" if n else ""])
    return rows

def prop(x, n):
    if not n:
        return ["", "", ""]
    lo, hi = exact_ci(x, n)
    return [f"{100 * x / n:.1f}", f"{100 * lo:.1f}", f"{100 * hi:.1f}"]

def main(data, out):
    os.makedirs(out, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S")
    log = []
    head = ["source", "compartment", "isolates", "percent_of_allocated_isolates", "submissions",
            "percent_of_submissions", "isolates_in_largest_submission", "largest_submission_percent"]
    # ---------------- PubMLST
    f_p = sorted(glob.glob(os.path.join(data, "pubmlst_ctropicalis_isolates_*.jsonl")))[-1]
    P = [json.loads(l)["provenance"] for l in open(f_p, encoding="utf-8")]
    def pcomp(r):
        s = (r.get("anat_source") or "").lower()
        return "not_allocated" if not s else ("C2" if s == "animal" else "C1")
    rows = [head] + dist_rows("PubMLST", [(r.get("sender", ""), pcomp(r)) for r in P])
    res = [["source", "compartment", "agent", "criterion", "subset", "resistant", "classified", "unclassifiable",
            "senders", "percent", "ci_lower", "ci_upper"]]
    for agent, rmin, crit in [("fluconazole", 8, "MIC >= 8 mg/L (CLSI species-specific and EUCAST coincide)"),
                              ("voriconazole", 1, "MIC >= 1 mg/L (CLSI species-specific)")]:
        for comp in ["C1", "C2"]:
            recs = [(r.get("sender", ""), resistant(r.get(agent), rmin)) for r in P if pcomp(r) == comp and r.get(agent)]
            ok = [(s, x) for s, x in recs if x is not None]
            cnt = collections.Counter(s for s, _ in ok)
            subsets = [("all senders", ok)]
            if len(cnt) > 1:
                top = cnt.most_common(1)[0][0]
                subsets.append((f"without the largest sender ({cnt[top]} isolates)", [(s, x) for s, x in ok if s != top]))
            for lab, sub in subsets:
                x = sum(1 for _, y in sub if y); n = len(sub)
                res.append(["PubMLST", comp, agent, crit, lab, x, n, len(recs) - len(ok) if lab == "all senders" else "",
                            len({s for s, _ in sub})] + prop(x, n))
    years = [r["year"] for r in P if isinstance(r.get("year"), int)]
    cont_p = collections.Counter(r.get("continent") or "not recorded" for r in P)
    log.append(f"PubMLST: {len(P)} isolates, {len({r.get('country') for r in P if r.get('country')})} countries, "
               f"years {min(years)}-{max(years)}, {len({r.get('sender') for r in P})} senders; "
               f"anat_source {dict(collections.Counter(r.get('anat_source') for r in P))}; continents {dict(cont_p)}")
    # ---------------- NCBI
    f_n = sorted(glob.glob(os.path.join(data, "ncbi_biosample_ctropicalis_*.jsonl")))[-1]
    N = [json.loads(l) for l in open(f_n, encoding="utf-8")]
    f_s = sorted(glob.glob(os.path.join(data, "ncbi_sra_runinfo_ctropicalis_*.csv")))[-1]
    with_reads = {r["BioSample"] for r in csv.DictReader(open(f_s, encoding="utf-8"))}
    dic = collections.OrderedDict(); assign = []
    for r in N:
        key = (v(r, "isolation_source"), v(r, "host"), v(r, "env_broad_scale", "env_local_scale", "env_medium"),
               v(r, "sample_type"), r["title"] if not v(r, "isolation_source", "host") else "")
        org = r["organism"]
        c, why = compartment(key[0], key[1], key[2], key[3] + (" " + org if org != "Candida tropicalis" else ""),
                             key[4])
        dic.setdefault(key, [c, why, 0]); dic[key][2] += 1
        name = (v(r, "strain") or v(r, "isolate") or r["accession"]).strip().lower()
        grp = r["bioproject"] or r["owner"] or r["accession"]
        assign.append({"accession": r["accession"], "submission": grp, "isolate_key": f"{grp}|{name}",
                       "compartment": c, "reads_in_sra": r["accession"] in with_reads,
                       "country": v(r, "geo_loc_name").split(":")[0], "year": v(r, "collection_date")[:4]})
    iso = collections.defaultdict(set); iso_sub = {}; iso_cty = {}
    for a in assign:
        if a["compartment"] != "excluded_laboratory":
            iso[a["isolate_key"]].add(a["compartment"]); iso_sub[a["isolate_key"]] = a["submission"]
            iso_cty[a["isolate_key"]] = a["country"]
    units = [(iso_sub[k], (list(s)[0] if len(s) == 1 else "not_allocated")) for k, s in iso.items()]
    rows += dist_rows("NCBI BioSample", units)
    n_lab = sum(1 for a in assign if a["compartment"] == "excluded_laboratory")
    log.append(f"NCBI: {len(N)} BioSamples, {n_lab} laboratory-derived excluded, "
               f"{sum(1 for a in assign if a['compartment'] != 'excluded_laboratory')} remaining, {len(iso)} isolates "
               f"after collapsing by BioProject and strain, {len({s for s, _ in units})} submissions; "
               f"{len(with_reads)} BioSamples with SRA reads; countries {len({c for c in iso_cty.values() if c})}; "
               f"top countries {collections.Counter(c or 'not recorded' for c in iso_cty.values()).most_common(6)}")
    # ---------------- outputs
    written = []
    def w(name, rr):
        p = os.path.join(out, f"{name}_v1_{stamp}.csv")
        written.append(p)
        with open(p, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rr)
        return p
    w("triang_distribution", rows)
    w("triang_resistance_pubmlst", res)
    w("triang_ncbi_source_dictionary", [["isolation_source", "host", "environment", "sample_type", "title_if_no_source",
                                          "compartment", "rule", "biosamples"]] +
      [list(k) + val for k, val in dic.items()])
    w("triang_ncbi_assignment", [list(assign[0])] + [list(a.values()) for a in assign])
    open(os.path.join(out, f"triang_log_v1_{stamp}.txt"), "w").write(
        "\n".join(log + [f"inputs: {os.path.basename(f_p)}, {os.path.basename(f_n)}, {os.path.basename(f_s)}"]) + "\n")
    written.append(os.path.join(out, f"triang_log_v1_{stamp}.txt"))
    print(run_log.write(__file__, [f_p, f_n, f_s], written))
    print("\n".join(log))
    for r in rows: print(*r, sep="\t")
    for r in res: print(*r, sep="\t")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
