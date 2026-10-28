"""Download every public isolate record of the PubMLST Candida tropicalis isolate database.

Auxiliary triangulation analysis registered in the protocol (isolate-level data, reported separately and
never merged with pooled proportions). Output: one JSON record per line, plus a manifest with the query date,
the record count and the SHA-256 of the file.
Usage: python 30_triang_pubmlst_download_v1.py OUT_DIR
"""
import hashlib, json, os, sys, time, datetime
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://rest.pubmlst.org/db/pubmlst_ctropicalis_isolates"

def get(url, tries=5):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            if k == tries - 1:
                raise
            time.sleep(2 * (k + 1))

def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    meta = get(BASE + "/isolates?page_size=1")
    n = meta["records"]
    ids = []
    page = BASE + "/isolates?page_size=500"
    while page:
        d = get(page)
        ids += [int(u.rsplit("/", 1)[1]) for u in d["isolates"]]
        page = d.get("paging", {}).get("next")
    assert len(ids) == n, (len(ids), n)
    with ThreadPoolExecutor(4) as ex:
        recs = list(ex.map(lambda i: get(f"{BASE}/isolates/{i}"), sorted(ids)))
    path = os.path.join(out_dir, f"pubmlst_ctropicalis_isolates_{stamp}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    man = {"source": BASE, "queried_utc": stamp, "records": n, "database_last_updated": meta.get("last_updated"),
           "database_last_added": meta.get("last_added"), "file": os.path.basename(path), "sha256": sha}
    json.dump(man, open(path.replace(".jsonl", "_manifest.json"), "w"), indent=2)
    print(json.dumps(man, indent=2))

if __name__ == "__main__":
    main(sys.argv[1])
