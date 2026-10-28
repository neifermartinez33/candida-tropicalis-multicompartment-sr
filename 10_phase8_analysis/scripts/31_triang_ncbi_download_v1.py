"""Download NCBI BioSample records of Candida tropicalis and the SRA run table linked to them.

Auxiliary triangulation analysis registered in the protocol. SRA sample metadata are BioSample records, so
the SRA run table is used only to record which BioSamples have sequencing reads and to add any BioSample
referenced by SRA that the BioSample query did not return.
Usage: python 31_triang_ncbi_download_v1.py OUT_DIR
"""
import csv, hashlib, io, json, os, sys, time, datetime
import urllib.request, urllib.parse
import xml.etree.ElementTree as ET

EU = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
TERM = '"Candida tropicalis"[Organism]'

def fetch(url, data=None, tries=6):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None)
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(3 * (k + 1))
        finally:
            time.sleep(0.4)  # below 3 requests per second without an API key

def esearch(db, term):
    d = json.loads(fetch(EU + "esearch.fcgi", {"db": db, "term": term, "retmax": 100000, "retmode": "json"}))
    return d["esearchresult"]["idlist"], int(d["esearchresult"]["count"])

def parse_biosample(xml):
    out = []
    for s in ET.fromstring(xml).iter("BioSample"):
        attrs = {a.get("harmonized_name") or a.get("attribute_name"): (a.text or "").strip()
                 for a in s.iter("Attribute")}
        ids = {i.get("db"): i.text for i in s.iter("Id")}
        org = s.find("Description/Organism")
        out.append({
            "uid": s.get("id"), "accession": s.get("accession"), "publication_date": s.get("publication_date"),
            "title": (s.findtext("Description/Title") or "").strip(),
            "organism": org.get("taxonomy_name") if org is not None else "",
            "taxonomy_id": org.get("taxonomy_id") if org is not None else "",
            "package": (s.findtext("Package") or "").strip(),
            "owner": (s.findtext("Owner/Name") or "").strip(),
            "sra": ids.get("SRA", ""), "bioproject": ";".join(l.get("label") or l.text or ""
                                                            for l in s.iter("Link") if l.get("target") == "bioproject"),
            "attributes": attrs,
        })
    return out

def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    ids, n = esearch("biosample", TERM)
    assert len(ids) == n
    recs = []
    for i in range(0, len(ids), 200):
        recs += parse_biosample(fetch(EU + "efetch.fcgi", {"db": "biosample", "id": ",".join(ids[i:i + 200])}))
    # SRA run table
    sra_ids, n_sra = esearch("sra", TERM)
    runs = []
    for i in range(0, len(sra_ids), 300):
        txt = fetch(EU + "efetch.fcgi", {"db": "sra", "id": ",".join(sra_ids[i:i + 300]), "rettype": "runinfo",
                                         "retmode": "text"}).decode("utf-8", "replace")
        runs += [r for r in csv.DictReader(io.StringIO(txt)) if r.get("Run") and r["Run"] != "Run"]
    have = {r["accession"] for r in recs}
    extra = sorted({r["BioSample"] for r in runs if r.get("BioSample") and r["BioSample"] not in have})
    for i in range(0, len(extra), 200):
        ids2, _ = esearch("biosample", " OR ".join(f"{a}[accn]" for a in extra[i:i + 200]))
        if ids2:
            recs += parse_biosample(fetch(EU + "efetch.fcgi", {"db": "biosample", "id": ",".join(ids2)}))
    p1 = os.path.join(out_dir, f"ncbi_biosample_ctropicalis_{stamp}.jsonl")
    with open(p1, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    p2 = os.path.join(out_dir, f"ncbi_sra_runinfo_ctropicalis_{stamp}.csv")
    cols = sorted({k for r in runs for k in r})
    with open(p2, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(runs)
    man = {"query": TERM, "queried_utc": stamp, "biosample_count_query": n, "biosample_records": len(recs),
           "biosamples_added_from_sra": len(extra), "sra_experiment_count_query": n_sra, "sra_runs": len(runs),
           "files": {os.path.basename(p): hashlib.sha256(open(p, "rb").read()).hexdigest() for p in (p1, p2)}}
    json.dump(man, open(os.path.join(out_dir, f"ncbi_ctropicalis_{stamp}_manifest.json"), "w"), indent=2)
    print(json.dumps(man, indent=2))

if __name__ == "__main__":
    main(sys.argv[1])
