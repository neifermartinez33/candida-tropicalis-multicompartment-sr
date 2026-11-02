#!/usr/bin/env python3
"""70_lab_recoding_sheet_v1.py (2026-11-02)

Review sheet for the recoding of research groups by laboratory in the non-human compartments. It proposes a laboratory per
collection from shared authors (Crossref, by DOI) and the recorded institution, and computes no estimate: the team fixes the
coding before any refit. Two reports are linked when they share at least two authors (surname and first initial); laboratories
are the connected components of those links. Reports without authors are left alone and flagged for review.

Usage, from the project root:
  python3 10_phase8_analysis/scripts/70_lab_recoding_sheet_v1.py
Outputs: 10_phase8_analysis/results/lab_recoding_review_v1_<date-time>.xlsx
         10_phase8_analysis/data/lookups/crossref_authors_nonhuman_v1.json (cache)
"""
import csv
import datetime
import glob
import itertools
import json
import os
import time
import unicodedata
import urllib.parse
import urllib.request

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

RES = "10_phase8_analysis/results/"
DS = "10_phase8_analysis/data/analysis_dataset_v3_2026-10-30T133231/"
CACHE = "10_phase8_analysis/data/lookups/crossref_authors_nonhuman_v1.json"
MIN_SHARED = 2


def newest(pat):
    return sorted(f for f in glob.glob(RES + pat) if "PROVISIONAL" not in f)[-1]


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return "".join(c for c in s if c.isalpha() or c == " ").strip()


def author_keys(authors):
    out = set()
    for a in authors:
        fam, giv = norm(a.get("family")), norm(a.get("given"))
        if fam:
            out.add(fam.split()[-1] + " " + (giv[:1] if giv else ""))
    return out


def fetch(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    req = urllib.request.Request(url, headers={"User-Agent": "candida-tropicalis-review/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)["message"]
        return [{"family": a.get("family", ""), "given": a.get("given", ""),
                 "aff": "; ".join(x.get("name", "") for x in a.get("affiliation", []))} for a in d.get("author", [])]
    except Exception as e:
        return {"error": str(e)[:80]}


def main():
    mi = newest("ma_input_v2_*.csv")
    rows = [r for r in csv.DictReader(open(mi, encoding="utf-8")) if r["compartment"] != "C1" and r["main"] in ("1", "True", "TRUE")]
    strata = {tuple(r[k] for k in ("compartment", "agent", "outcome", "regime_stratum")) for r in csv.DictReader(open(newest("ma_results_v3_*.csv"), encoding="utf-8")) if r["compartment"] != "C1"}
    st = {r["study_id"]: r for r in csv.DictReader(open(DS + "studies.csv", encoding="utf-8"))}
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    ids = sorted({r["study_id"] for r in rows})
    for i in ids:
        doi = (st[i].get("doi") or "").strip()
        if doi and (doi not in cache or isinstance(cache[doi], dict)):
            cache[doi] = fetch(doi)
            time.sleep(0.25)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    keys = {}
    for i in ids:
        a = cache.get((st[i].get("doi") or "").strip())
        keys[i] = author_keys(a) if isinstance(a, list) else set()
    par = {i: i for i in ids}

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    links = []
    for a, b in itertools.combinations(ids, 2):
        sh = keys[a] & keys[b]
        if len(sh) >= MIN_SHARED:
            links.append((a, b, sh))
            par[find(a)] = find(b)
    comps = {}
    for i in ids:
        comps.setdefault(find(i), []).append(i)
    lab = {}
    for n, (root, mem) in enumerate(sorted(comps.items(), key=lambda kv: (-len(kv[1]), kv[0])), 1):
        for i in mem:
            lab[i] = f"LAB{n:02d}"
    size = {i: len(comps[find(i)]) for i in ids}
    wb = Workbook()
    ws = wb.active
    ws.title = "Rules"
    for t in ["Laboratory recoding of the non-human collections: proposal for team review. No estimate has been computed from it.",
              f"Link: two reports share at least {MIN_SHARED} authors (surname and first initial; Crossref by DOI). Laboratory: connected component of the links.",
              "Fill team_laboratory only to change the proposal; add a reason in team_note. Check every row with review = YES.",
              "review = YES: no authors retrieved, or the link rests on few shared authors, or the current groups of a linked set differ.",
              "Refit rule to be fixed by the team: one collection per laboratory, the one with most isolates tested (SX10), then AR12 and AR18."]:
        ws.append([t])
    ws.column_dimensions["A"].width = 130
    w = wb.create_sheet("Collections")
    H = ["compartment", "study_id", "report", "year", "country", "doi", "institution_recorded", "current_group", "authors_crossref", "in_stratum_meeting_AR12",
         "proposed_laboratory", "reports_in_laboratory", "review", "review_reason", "team_laboratory", "team_note"]
    w.append(H)
    for c in w[1]:
        c.font = Font(bold=True)
    seen = {}
    for r in rows:
        seen.setdefault(r["study_id"], r)
    grp = {}
    for i, r in seen.items():
        grp.setdefault(lab[i], set()).add(r["research_group"])
    for i, r in sorted(seen.items(), key=lambda kv: (lab[kv[0]], kv[1]["study_label"])):
        a = cache.get((st[i].get("doi") or "").strip())
        names = "; ".join((x["family"] + " " + x["given"]).strip() for x in a) if isinstance(a, list) else ""
        why = []
        if not keys[i]:
            why.append("no authors retrieved")
        if size[i] > 1 and len(grp[lab[i]]) > 1:
            why.append("linked reports had different current groups")
        ins = any((r["compartment"], x["agent"], x["outcome"], x["regime_stratum"]) in strata for x in rows if x["study_id"] == i)
        w.append([r["compartment"], i, r["study_label"], st[i]["year"], st[i]["country"], st[i]["doi"], st[i]["programme_institution_raw"], r["research_group"], names,
                  "YES" if ins else "NO", lab[i], size[i], "YES" if why else "NO", "; ".join(why), "", ""])
    for col, wd in zip("ABCDEFGHIJKLMNOP", (11, 10, 26, 6, 14, 26, 42, 30, 60, 12, 12, 10, 8, 34, 16, 26)):
        w.column_dimensions[col].width = wd
    w.freeze_panes = "A2"
    w.auto_filter.ref = w.dimensions
    for row in w.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    l = wb.create_sheet("Links")
    l.append(["report_a", "report_b", "shared_authors", "n_shared"])
    for c in l[1]:
        c.font = Font(bold=True)
    for a, b, sh in sorted(links, key=lambda t: -len(t[2])):
        l.append([seen[a]["study_label"], seen[b]["study_label"], "; ".join(sorted(sh)), len(sh)])
    for col, wd in zip("ABCD", (28, 28, 60, 9)):
        l.column_dimensions[col].width = wd
    p = RES + "lab_recoding_review_v1_" + datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S") + ".xlsx"
    wb.save(p)
    print(p)
    print("reports", len(ids), "with authors", sum(1 for i in ids if keys[i]), "labs", len(comps), "links", len(links))
    for root, mem in sorted(comps.items(), key=lambda kv: -len(kv[1])):
        if len(mem) > 1:
            print(lab[root], [seen[i]["study_label"] for i in mem])
    print("sin autores:", [seen[i]["study_label"] for i in ids if not keys[i]])
    print("enlaces con 2 autores:", [(seen[a]["study_label"], seen[b]["study_label"], sorted(s)) for a, b, s in links if len(s) == 2])


if __name__ == "__main__":
    main()
