"""Retrospective seed-set check and reference-list checking of previous systematic reviews.

Protocol: before closing identification each source is checked for recovery of a seed set of known and
necessarily eligible studies, and the proportion recovered by each source is recorded; reference lists are
checked (backward citation searching). Both are done here retrospectively, after full-text screening.

Seed set: references cited by four previous reviews of C. tropicalis or of Candida resistance (reference lists
from Crossref, saved with their query date) that were included in this review. Each source export is
searched for the DOI or the normalised title of every seed study. The references not retrieved by the search
are listed for eligibility assessment.
Usage: python 33_seed_set_check_v1.py REVIEW_REFS_DIR OUT_DIR   (from the project root)
"""
import csv, glob, json, os, re, sys, datetime
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_log  # noqa: E402

REVIEWS = {"10.1093/mmy/myae040": "Keighley 2024 (WHO priority list review)",
           "10.1186/s12879-026-12653-8": "Li 2026 (fluconazole resistance, non-albicans Candida)",
           "10.1016/j.envres.2026.125757": "dos Santos 2026 (environmental and animal reservoirs)",
           "10.3389/ffunb.2022.957021": "Fan 2022 (narrative review, humans, animals and environment)"}

def nd(x):
    x = (str(x) if x == x and x is not None else "").lower().strip()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", x).rstrip(".")

def nt(x):
    return re.sub(r"[^a-z0-9]", "", (str(x) if x == x and x is not None else "").lower())[:80]

def main(ref_dir, out):
    os.makedirs(out, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S")
    refs, seen = [], set()
    for f in sorted(glob.glob(os.path.join(ref_dir, "crossref_*.json"))):
        m = json.load(open(f))["message"]
        for r in m.get("reference", []):
            d = nd(r.get("DOI")); t = r.get("article-title") or r.get("unstructured", "")
            k = d or nt(t)
            if not k or k in seen:
                continue
            seen.add(k)
            refs.append({"review": REVIEWS.get(m["DOI"].lower(), m["DOI"]), "doi": d, "title": t, "year": r.get("year", "")})
    ft = pd.read_excel("07_phase5_full_text_screening/full_text_screening.xlsx", "All")
    inc = ft[ft["Decision"].astype(str).str.upper() == "INCLUDE"]
    by_doi = {nd(d): i for d, i in zip(inc["DOI"], inc["ID"]) if nd(d)}
    by_t = {nt(t): i for t, i in zip(inc["Title"], inc["ID"]) if nt(t)}
    raw = open("02_phase0_raw_corpus/raw_corpus_n47644_2026-09-28.ris", encoding="utf-8", errors="replace").read()
    corpus_d = set(nd(m) for m in re.findall(r"10\.\d{4,9}/[^\s\"<>]+", raw.lower()))
    corpus_t = set(nt(m) for m in re.findall(r"^(?:TI|T1)  - (.*)$", raw, re.M))
    srcs = {}
    for d in sorted(glob.glob("01_search/exports/*/")):
        txt = "".join(open(f, encoding="utf-8", errors="replace").read() for f in glob.glob(d + "**/*", recursive=True)
                      if os.path.isfile(f)).lower()
        srcs[os.path.basename(d.rstrip("/"))] = (txt, re.sub(r"[^a-z0-9]", "", txt))
    # references without DOI often carry only an unstructured citation: a title of at least 30 normalised
    # characters contained in that citation identifies the record (2026-10-27; exact title matching missed them)
    long_t = sorted((t for t in corpus_t if len(t) >= 30), key=len, reverse=True)
    inc_t = {t: i for t, i in by_t.items() if len(t) >= 30}
    def unstructured_match(cit):
        flat = re.sub(r"[^a-z0-9]", "", cit.lower())
        hit = next(((t, i) for t, i in inc_t.items() if t in flat), None)
        if hit:
            return hit[1], True, hit[0]
        t = next((t for t in long_t if t in flat), None)
        return None, t is not None, t
    seed, missing = [], []
    for r in refs:
        rid = by_doi.get(r["doi"]) or by_t.get(nt(r["title"]))
        um = (None, False, None)
        if not r["doi"] and not rid:
            um = unstructured_match(r["title"])
            rid = um[0]
        mt = um[2] or nt(r["title"])
        r["in_corpus"] = bool((r["doi"] and r["doi"] in corpus_d) or (nt(r["title"]) and nt(r["title"]) in corpus_t) or rid
                              or um[1])
        if rid:
            r["report_id"] = rid
            for s, (txt, flat) in srcs.items():
                r[s] = int(bool((r["doi"] and r["doi"] in txt) or (len(mt) >= 30 and mt in flat)))
            seed.append(r)
        elif not r["in_corpus"]:
            missing.append(r)
    cols = ["review", "report_id", "doi", "year", "title"] + list(srcs)
    pd.DataFrame(seed)[cols].to_csv(os.path.join(out, f"seed_set_recovery_v1_{stamp}.csv"), index=False)
    summ = [["source", "seed_studies_recovered", "seed_studies", "percent"]]
    for s in srcs:
        k = sum(r[s] for r in seed)
        summ.append([s, k, len(seed), f"{100 * k / len(seed):.1f}"])
    anyk = sum(1 for r in seed if any(r[s] for s in srcs))
    summ.append(["any source (exports)", anyk, len(seed), f"{100 * anyk / len(seed):.1f}"])
    with open(os.path.join(out, f"seed_set_by_source_v1_{stamp}.csv"), "w", newline="") as f:
        csv.writer(f).writerows(summ)
    pd.DataFrame(missing)[["review", "doi", "year", "title"]].to_csv(
        os.path.join(out, f"reference_check_not_retrieved_v1_{stamp}.csv"), index=False)
    ins = sorted(glob.glob(os.path.join(ref_dir, "crossref_*.json"))) + [
        "07_phase5_full_text_screening/full_text_screening.xlsx", "02_phase0_raw_corpus/raw_corpus_n47644_2026-09-28.ris"] + [
        f for d in srcs for f in glob.glob(f"01_search/exports/{d}/**/*", recursive=True) if os.path.isfile(f)]
    outs = [os.path.join(out, f"{n}_v1_{stamp}.csv") for n in
            ("seed_set_recovery", "seed_set_by_source", "reference_check_not_retrieved")]
    print(run_log.write(__file__, ins, outs, seed_studies=len(seed), references=len(refs), not_in_corpus=len(missing)))
    print(f"references {len(refs)}; seed (included in this review) {len(seed)}; not in the corpus {len(missing)}")
    for row in summ:
        print(*row, sep="\t")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
