"""Round 3 (reference-list check of previous reviews): register the candidate reports and retrieve their full texts.

Candidates: references cited by the four previous reviews that the search did not retrieve and that, on title,
abstract or open full text, may be primary studies with C. tropicalis isolates (proposal of 2026-10-27, listed in
CANDIDATES with the reason). Each receives a report ID B001... (prefix B, backward citation; the prefixes O and R
belong to the search streams). Full texts are retrieved only from open or free sources (Europe PMC / PMC, the
publisher's open page, SciELO); reports behind a paywall are recorded as not retrieved, the rule applied to the
main search. PDFs are stored outside the project with the other full texts (copyright).
When no PDF is open, the free HTML or XML full text is stored in PDF_DIR + '_html'.
Usage: python 36_reference_check_retrieve_v1.py PDF_DIR   (from the project root)
"""
import csv, hashlib, json, os, sys, time, datetime, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_log  # noqa: E402

OUT = "07_phase5_full_text_screening/reference_check_2026-10-27"
UA = {"User-Agent": "Mozilla/5.0 (systematic review full-text retrieval)"}
# doi, reason for candidacy, compartment suggested by the title or open text
CANDIDATES = [
    ("10.1186/s12879-019-4065-5", "candidaemia cohort; 10 C. tropicalis episodes in the open text", "C1"),
    ("10.3201/eid1210.060389", "candidaemia surveillance; C. tropicalis 5.1% of 1068 episodes in the open text", "C1"),
    ("10.15585/mmwr.ss6808a1", "candidaemia surveillance; 292 C. tropicalis isolates with susceptibility in the open text", "C1"),
    ("10.1155/2013/236903", "susceptibility of Candida species; 3 C. tropicalis isolates in the open text", "C1"),
    ("10.1016/j.lana.2021.100117", "candidaemia cohort; 100 C. tropicalis isolates in the open text", "C1"),
    ("10.3390/jof7080596", "candidaemia; 11 C. tropicalis isolates with MICs in the open text", "C1"),
    ("10.1128/aac.05947-11", "fluconazole-resistant Candida bloodstream infection; tropicalis in the record", "C1"),
    ("10.1099/jmm.0.037812-0", "prevalence and susceptibility of Candida species", "C1"),
    ("10.1128/aac.00466-11", "multicentre candidaemia study; tropicalis in the record", "C1"),
    ("10.1007/s42770-023-00943-1", "neonatal candidaemia; tropicalis in the record", "C1"),
    ("10.1093/jac/dkr394", "Candida species distribution and susceptibility in intensive care", "C1"),
    ("10.1128/aac.00479-10", "risk factors of fluconazole-resistant candidaemia; tropicalis in the record", "C1"),
    ("10.1007/s00284-022-02915-4", "microorganisms from human stool", "C1"),
    ("10.1111/myc.70026", "vulvovaginal candidiasis", "C1"),
    ("10.1128/jcm.01096-09", "susceptibility of 205 Candida isolates; tropicalis in the record", "C1"),
    ("10.1007/s11046-011-9413-y", "susceptibility testing of Candida isolates", "C1"),
    ("10.1136/sti.2002.003855", "vaginal yeast colonisation; tropicalis in the record", "C1"),
    ("10.4067/s0716-10182013000600004", "candidaemia in critically ill patients", "C1"),
    ("10.1016/j.femsle.2005.01.043", "yeasts of hypersaline habitats", "C5"),
    ("10.1177/0300985812446153", "fungal tracheitis in captive dolphins", "C2"),
    ("10.1016/j.vetmic.2009.12.012", "yeast flora of the genital tract of camels", "C2"),
    ("PMCID:PMC6379607", "Candida species from horticulturists with onychomycosis (no DOI in the citation)", "C1"),
    ("10.7860/jcdr/2013/6298.3578", "candiduria and antifungal susceptibility (no DOI in the citation)", "C1"),
]
EXTRA_URLS = {"10.1016/j.femsle.2005.01.043": ["https://academic.oup.com/femsle/article-pdf/244/2/229/19125595/244-2-229.pdf"],
              "10.4067/s0716-10182013000600004": ["http://www.scielo.cl/pdf/rci/v30n6/art04.pdf"],
              "10.1155/2013/236903": ["https://downloads.hindawi.com/journals/tswj/2013/236903.pdf"],
              "10.3390/jof7080596": ["https://www.mdpi.com/2309-608X/7/8/596/pdf"],
              "10.15585/mmwr.ss6808a1": ["https://www.cdc.gov/mmwr/volumes/68/ss/pdfs/ss6808a1-H.pdf"]}

def get(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read()
        return data if binary else data.decode("utf-8", "replace")

def epmc(q):
    u = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
        {"query": q, "format": "json", "resultType": "core"})
    res = json.loads(get(u))["resultList"]["result"]
    return res[0] if res else {}

def main(pdf_dir):
    html_dir = pdf_dir.rstrip("/") + "_html"
    os.makedirs(OUT, exist_ok=True); os.makedirs(pdf_dir, exist_ok=True); os.makedirs(html_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S")
    rows = []
    for k, (key, why, comp) in enumerate(CANDIDATES, 1):
        rid = f"B{k:03d}"
        rec = epmc(key if key.startswith("PMCID") else f'DOI:"{key}"'); time.sleep(0.3)
        doi = rec.get("doi", "" if key.startswith("PMCID") else key)
        title = (rec.get("title") or "").replace("<i>", "").replace("</i>", "")
        pmcid = rec.get("pmcid")
        urls = ([f"https://europepmc.org/articles/{pmcid}?pdf=render"] if pmcid else []) + EXTRA_URLS.get(doi, [])
        status, fname, md5, used = "not_retrieved_no_open_full_text", "", "", ""
        prev = sorted(f for f in os.listdir(pdf_dir) if f.startswith(rid + "_") and f.endswith(".pdf"))
        if prev:   # resumable: a PDF already retrieved in an earlier run is kept
            fname = prev[0]; b = open(os.path.join(pdf_dir, fname), "rb").read()
            md5 = hashlib.md5(b).hexdigest(); status = "retrieved"; used = "earlier run of this script"
            urls = []
        for u in urls:
            try:
                b = get(u, binary=True)
            except Exception:
                continue
            if b[:4] == b"%PDF" and len(b) > 20000:
                safe = "".join(c if c.isalnum() else "_" for c in title)[:60]
                fname = f"{rid}_{safe}.pdf"
                open(os.path.join(pdf_dir, fname), "wb").write(b)
                md5 = hashlib.md5(b).hexdigest(); status = "retrieved"; used = u
                break
        if status != "retrieved" and pmcid:
            # free full text in HTML/XML (Europe PMC full-text XML for the open subset, PMC article page otherwise)
            for u in (f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML",
                      f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"):
                try:
                    b = get(u, binary=True)
                except Exception:
                    continue
                if len(b) > 30000 and (b"<body" in b or b"<article" in b):
                    safe = "".join(c if c.isalnum() else "_" for c in title)[:60]
                    ext = "xml" if u.endswith("XML") else "html"
                    fname = f"{rid}_{safe}.{ext}"
                    open(os.path.join(html_dir, fname), "wb").write(b)
                    md5 = hashlib.md5(b).hexdigest(); status = "retrieved"; used = u
                    break
        rows.append({"report_id": rid, "doi": doi, "pmcid": pmcid or "", "title": title,
                     "first_author": (rec.get("authorString") or "").split(",")[0], "year": rec.get("pubYear", ""),
                     "journal": (rec.get("journalInfo") or {}).get("journal", {}).get("title", ""),
                     "language": rec.get("language", ""), "candidacy_reason": why, "suggested_compartment": comp,
                     "retrieval_status": status, "retrieval_url": used, "pdf_file": fname, "pdf_md5": md5})
        print(rid, status, title[:70])
    p = os.path.join(OUT, f"reference_check_candidates_v1_{stamp}.csv")
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
    print(run_log.write(__file__, [], [p], retrieved=sum(r["retrieval_status"] == "retrieved" for r in rows),
                        candidates=len(rows)))
    print(p)

if __name__ == "__main__":
    main(sys.argv[1])
