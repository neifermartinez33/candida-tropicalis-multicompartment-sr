"""Second retrieval attempt for the reports not retrieved: open-access copies only.

For every report of the PRISMA not-retrieved list, the open-access locations are looked up in OpenAlex
(which carries the Unpaywall data), Europe PMC and Semantic Scholar, by DOI; records without DOI are
searched by title in OpenAlex and accepted only if the normalised title matches (similarity >= 0.93)
and the publication year differs by at most one. Every candidate PDF URL is downloaded and kept only if
the file starts with %PDF. Whether the PDF is the right work is decided later, at full-text screening.

Outputs (07_phase5_full_text_screening/oa_retrieval_2026-10-29/):
  oa_lookup.csv          one row per report: identifiers, candidate URLs and their source
  oa_downloads.csv       one row per report: downloaded file, source URL, size, MD5 or failure reason
  pdfs/                  the PDFs, named <screen_id>_<title>.pdf
  43_oa_retrieval_v1_<ts>.json   log with counts and MD5 checksums of inputs and outputs

Usage: python3 43_oa_retrieval_v1.py [lookup|download|all]   (from the project root; default all)
"""
import difflib, hashlib, json, os, re, sys, time, unicodedata
from datetime import datetime
from urllib.parse import quote
import pandas as pd
import requests

NR = "10_phase8_analysis/results/prisma_not_retrieved_v3_2026-10-28T193926.csv"
RIS = "06_phase4_title_abstract_screening/import/screening_reviewer_1_reviewer_2_n22203_seed1310202643.ris"
OUT = "07_phase5_full_text_screening/oa_retrieval_2026-10-29"
UA = {"User-Agent": "candida-tropicalis-sr-oa-retrieval/1.0 (systematic review; open-access copies only)"}
S = requests.Session()
S.headers.update(UA)


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def norm(t):
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def get(url, **kw):
    for attempt in range(4):
        try:
            r = S.get(url, timeout=40, **kw)
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            return r
        except requests.RequestException:
            time.sleep(3 * (attempt + 1))
    return None


def read_records():
    nr = pd.read_csv(NR, dtype=str)
    txt = open(RIS, encoding="utf-8", errors="ignore").read()
    recs = []
    for blk in re.split(r"\nER  -.*", txt):
        d = {}
        for m in re.finditer(r"^([A-Z][A-Z0-9])  - ?(.*)$", blk, re.M):
            d.setdefault(m.group(1), []).append(m.group(2).strip())
        sid = next((mm.group(1) for v in d.get("N1", []) + d.get("AN", [])
                    for mm in [re.search(r"\b([ORB]\d{5})\b", v)] if mm), None)
        if sid:
            first = lambda *k: next((d[x][0] for x in k if d.get(x)), "")
            recs.append(dict(screen_id=sid, title=first("TI", "T1"), year=first("PY", "Y1")[:4],
                             journal=first("JO", "T2", "JF"), doi=first("DO").lower().removeprefix("https://doi.org/")))
    r = pd.DataFrame(recs).drop_duplicates("screen_id")
    out = nr.merge(r, on="screen_id", how="left")
    for c in ("title", "year", "journal", "doi"):
        out[c] = out[c].fillna("")
    return out


def openalex_by_doi(dois):
    found = {}
    for i in range(0, len(dois), 50):
        chunk = dois[i:i + 50]
        r = get("https://api.openalex.org/works", params={"filter": "doi:" + "|".join(chunk), "per-page": 50,
                                                          "select": "doi,locations,best_oa_location,ids"})
        if r is None or r.status_code != 200:
            continue
        for w in r.json().get("results", []):
            found[(w.get("doi") or "").lower().removeprefix("https://doi.org/")] = w
        time.sleep(0.2)
    return found


def openalex_by_title(title, year):
    r = get("https://api.openalex.org/works", params={"search": norm(title)[:250], "per-page": 5,
                                                      "select": "doi,title,publication_year,locations,best_oa_location,ids"})
    if r is None or r.status_code != 200:
        return None
    for w in r.json().get("results", []):
        sim = difflib.SequenceMatcher(None, norm(title), norm(w.get("title") or "")).ratio()
        y_ok = not str(year).isdigit() or not w.get("publication_year") or abs(int(year) - w["publication_year"]) <= 1
        if sim >= 0.93 and y_ok:
            return w
    return None


def pdf_urls_openalex(w):
    urls = []
    for loc in [w.get("best_oa_location") or {}] + (w.get("locations") or []):
        if loc and loc.get("is_oa") and loc.get("pdf_url"):
            urls.append(loc["pdf_url"])
    pmcid = (w.get("ids") or {}).get("pmcid")
    return urls, (pmcid.rsplit("/", 1)[-1] if pmcid else None)


def europepmc(doi):
    r = get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={"query": f'DOI:"{doi}"', "format": "json", "resultType": "core"})
    if r is None or r.status_code != 200:
        return [], None
    res = r.json().get("resultList", {}).get("result", [])
    if not res:
        return [], None
    urls = [u["url"] for u in res[0].get("fullTextUrlList", {}).get("fullTextUrl", [])
            if u.get("documentStyle") == "pdf" and u.get("availabilityCode") in ("OA", "F")]
    return urls, res[0].get("pmcid")


def semantic_scholar(doi):
    r = get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{quote(doi)}", params={"fields": "openAccessPdf"})
    time.sleep(1.1)
    if r is None or r.status_code != 200:
        return []
    u = (r.json().get("openAccessPdf") or {}).get("url")
    return [u] if u else []


def lookup(df):
    dois = sorted({d for d in df.doi.fillna("") if d})
    oa = openalex_by_doi(dois)
    rows = []
    for k, r in enumerate(df.itertuples(), 1):
        urls, src, pmcid, how = [], [], None, ""
        w = oa.get(r.doi) if r.doi else None
        if w is None and r.title and not r.doi:
            w = openalex_by_title(r.title, r.year)
            how = "title" if w else ""
        if w is not None:
            u, pmcid = pdf_urls_openalex(w)
            urls += u; src += ["openalex"] * len(u); how = how or "doi"
            if not r.doi and w.get("doi"):
                r = r._replace(doi=w["doi"].lower().removeprefix("https://doi.org/"))
        if r.doi:
            u, pm = europepmc(r.doi)
            urls += u; src += ["europepmc"] * len(u); pmcid = pmcid or pm
            if not urls:
                u = semantic_scholar(r.doi)
                urls += u; src += ["semanticscholar"] * len(u)
        if pmcid:
            urls.append(f"https://europepmc.org/articles/{pmcid}?pdf=render"); src.append("europepmc_pmc")
        seen, uu, ss = set(), [], []
        for u, s_ in zip(urls, src):
            if u not in seen:
                seen.add(u); uu.append(u); ss.append(s_)
        rows.append(dict(screen_id=r.screen_id, cause=r.cause, year=r.year, title=r.title, journal=r.journal,
                         doi=r.doi, match=how, pmcid=pmcid, n_urls=len(uu), urls=" | ".join(uu), sources=" | ".join(ss)))
        if k % 200 == 0:
            print(f"lookup {k}/{len(df)}", flush=True)
    return pd.DataFrame(rows)


def download(lk):
    os.makedirs(os.path.join(OUT, "pdfs"), exist_ok=True)
    rows = []
    for k, r in enumerate(lk.itertuples(), 1):
        res = dict(screen_id=r.screen_id, file="", url="", source="", bytes=0, md5="", failure="")
        if not r.n_urls:
            res["failure"] = "no_open_access_location"
        else:
            for u, s_ in zip(r.urls.split(" | "), r.sources.split(" | ")):
                resp = get(u, allow_redirects=True)
                if resp is None or resp.status_code != 200 or not resp.content.startswith(b"%PDF"):
                    res["failure"] = "not_a_pdf_or_blocked"
                    continue
                name = f"{r.screen_id}_{norm(r.title)[:60].replace(' ', '_')}.pdf"
                path = os.path.join(OUT, "pdfs", name)
                with open(path, "wb") as fh:
                    fh.write(resp.content)
                res.update(file=name, url=u, source=s_, bytes=len(resp.content), md5=md5(path), failure="")
                break
        rows.append(res)
        if k % 200 == 0:
            print(f"download {k}/{len(lk)}", flush=True)
    return pd.DataFrame(rows)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    ts = datetime.now().astimezone().strftime("%Y-%m-%dT%H%M%S")
    os.makedirs(OUT, exist_ok=True)
    p_lk, p_dl = os.path.join(OUT, "oa_lookup.csv"), os.path.join(OUT, "oa_downloads.csv")
    log = dict(script="43_oa_retrieval_v1.py", run_time=ts, mode=mode, inputs={p: md5(p) for p in (NR, RIS)})
    if mode in ("lookup", "all"):
        df = read_records()
        lk = lookup(df)
        lk.to_csv(p_lk, index=False)
        log["lookup"] = dict(reports=len(lk), with_doi=int((lk.doi.fillna("") != "").sum()),
                             matched_by=lk.match.value_counts().to_dict(), with_oa_url=int((lk.n_urls > 0).sum()))
    if mode in ("download", "all"):
        lk = pd.read_csv(p_lk, dtype={"n_urls": int}, keep_default_na=False)
        dl = download(lk)
        dl.to_csv(p_dl, index=False)
        lk["y"] = pd.to_numeric(lk.year, errors="coerce")
        got = dl.file != ""
        log["download"] = dict(pdfs=int(got.sum()), by_source=dl.source[got].value_counts().to_dict(),
                               failures=dl.failure[~got].value_counts().to_dict(),
                               pdfs_since_2015=int((got.values & (lk.y >= 2015).values).sum()))
    log["outputs"] = {os.path.basename(p): md5(p) for p in (p_lk, p_dl) if os.path.exists(p)}
    with open(os.path.join(OUT, f"43_oa_retrieval_v1_{ts}.json"), "w") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in log.items() if k not in ("inputs", "outputs")}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
