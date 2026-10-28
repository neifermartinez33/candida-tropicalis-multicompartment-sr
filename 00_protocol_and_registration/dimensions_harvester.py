#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIMENSIONS HARVESTER  -  version 1.0  -  Windows

Retrieves the records of an app.dimensions.ai search when the native export
is not enough, because of the limit of five hundred records per download.

Method. It does not depend on the page markup, which the platform changes
often. It listens to the browser's network responses, detects those that carry
lists of bibliographic records and extracts the fields from them. If network
capture gives nothing, it falls back to reading the document.

Modes.
  1  Harvest  : goes through the results and writes RIS and CSV.
  2  Inspect  : does not harvest; records which calls the platform makes and
                which fields each one carries. Useful the first time or if the
                platform changes.

Requirements.
  pip install playwright
  playwright install chromium

Use from the Windows command prompt.
  python dimensions_harvester.py
"""

import csv
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# The Windows command prompt uses an old code page. If the user's path
# contains accents, a plain print aborts the program.
if sys.platform == "win32":
    for flow in (sys.stdout, sys.stderr):
        try:
            flow.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright is missing. Install it with these two commands:")
    print("   pip install playwright")
    print("   playwright install chromium")
    sys.exit(1)

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

PROFILE = Path.home() / ".dimensions_harvester_profile"
LOAD_WAIT = 2500        # ms after each scroll
MAX_NO_NEWS = 6        # consecutive scrolls without new records
PARTIAL_SAVE = 200     # write to disk every N new records

# Keys that reveal a bibliographic record inside any JSON
TITLE_KEYS = ("title", "title", "document_title", "name")
DOI_KEYS = ("doi", "DOI", "doi_url")
YEAR_KEYS = ("year", "pub_year", "publication_year", "date", "date_normal")
AUTHOR_KEYS = ("authors", "author_list", "researchers", "author_names")
JOURNAL_KEYS = ("journal", "journal_title", "source_title", "venue",
                  "publication_venue", "source")
ABSTRACT_KEYS = ("abstract", "abstract_text", "summary")
ID_KEYS = ("id", "publication_id", "dimensions_id", "uuid")


# --------------------------------------------------------------------------
# Console utilities, without accents for the Windows command prompt
# --------------------------------------------------------------------------

def ask(text, default_=""):
    suf = f" [{default_}]" if default_ else ""
    r = input(f"{text}{suf}: ").strip()
    return r if r else default_


def warning(text):
    print(text, flush=True)


# --------------------------------------------------------------------------
# Generic detection of records inside a JSON structure
# --------------------------------------------------------------------------

def first_value(d, keys):
    for k in keys:
        if k in d and d[k] not in (None, "", [], {}):
            return d[k]
    return ""


def text_of(v):
    """Flattens authors, journals and other fields that may come nested."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, dict):
        for k in ("name", "title", "full_name", "display_name", "value"):
            if k in v:
                return text_of(v[k])
        return ""
    if isinstance(v, list):
        parts = [text_of(x) for x in v]
        return "; ".join(p for p in parts if p)
    return str(v)


def looks_like_record(d):
    """A dictionary is a record if it has a title and some bibliographic field."""
    if not isinstance(d, dict):
        return False
    tit = text_of(first_value(d, TITLE_KEYS))
    if not tit or len(tit) < 12:
        return False
    others = any(k in d for k in DOI_KEYS + YEAR_KEYS + AUTHOR_KEYS + JOURNAL_KEYS)
    return others


def recolecta(obj, output, depth=0):
    """Walks the structure and collects the dictionaries that look like records."""
    if depth > 8:
        return
    if isinstance(obj, dict):
        if looks_like_record(obj):
            output.append(obj)
            return
        for v in obj.values():
            recolecta(v, output, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            recolecta(v, output, depth + 1)


def normaliza(d):
    """Maps a raw record to the fields we write."""
    doi = text_of(first_value(d, DOI_KEYS))
    # The resolver prefix is removed but the published form is kept:
    # duplicate matching uses the lower-case version, not this one.
    doi = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", doi.strip(), flags=re.I)
    year = text_of(first_value(d, YEAR_KEYS))
    m = re.search(r"(19|20)\d{2}", year)
    year = m.group(0) if m else ""
    ident = text_of(first_value(d, ID_KEYS))
    return {
        "id": ident,
        "title": text_of(first_value(d, TITLE_KEYS)),
        "authors": text_of(first_value(d, AUTHOR_KEYS)),
        "year": year,
        "journal": text_of(first_value(d, JOURNAL_KEYS)),
        "doi": doi,
        "abstract": text_of(first_value(d, ABSTRACT_KEYS)),
        "volume": text_of(d.get("volume", "")),
        "number": text_of(d.get("issue", "")),
        "pages": text_of(d.get("pages", "")),
        "type": text_of(d.get("type", "")) or "article",
    }


def unique_key(r):
    if r["doi"]:
        return "doi:" + r["doi"].lower()
    if r["id"]:
        return "id:" + r["id"]
    t = re.sub(r"[^a-z0-9]+", "", r["title"].lower())
    return "ti:" + t[:80]


# --------------------------------------------------------------------------
# Fallback: reading the document if the network gives nothing
# --------------------------------------------------------------------------

JS_FALLBACK = r"""
() => {
  const out = [];
  const nodes = document.querySelectorAll(
    '[data-test*="result"], .search-result, article, li[class*="result"]');
  nodes.forEach(n => {
    const a = n.querySelector('a[href*="/details/publication/"], h3 a, h2 a, a[class*="title"]');
    const t = a ? a.innerText.trim() : '';
    if (!t || t.length < 12) return;
    const txt = n.innerText || '';
    const mDoi = txt.match(/10\.\d{4,9}\/[^\s"'<>]+/);
    const mYear = txt.match(/\b(19|20)\d{2}\b/);
    out.push({
      title: t,
      doi: mDoi ? mDoi[0] : '',
      year: mYear ? mYear[0] : '',
      journal: '',
      authors: '',
      abstract: '',
      id: a && a.href ? a.href.split('/').pop() : ''
    });
  });
  return out;
}
"""


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------

RIS_TYPE = {
    "article": "JOUR", "journal article": "JOUR", "publication": "JOUR",
    "chapter": "CHAP", "book": "BOOK", "proceeding": "CONF",
    "preprint": "JOUR", "monograph": "BOOK",
}


def escribe(records, prefix, folder):
    ris = folder / f"{prefix}.ris"
    csvf = folder / f"{prefix}.csv"

    with ris.open("w", encoding="utf-8", newline="") as f:
        for r in records:
            ty = RIS_TYPE.get(r["type"].lower(), "JOUR")
            f.write(f"TY  - {ty}\n")
            f.write(f"TI  - {r['title']}\n")
            for a in [x.strip() for x in r["authors"].split(";") if x.strip()]:
                f.write(f"AU  - {a}\n")
            if r["journal"]:
                f.write(f"JO  - {r['journal']}\n")
            if r["year"]:
                f.write(f"PY  - {r['year']}\n")
            if r["volume"]:
                f.write(f"VL  - {r['volume']}\n")
            if r["number"]:
                f.write(f"IS  - {r['number']}\n")
            if r["pages"]:
                p = r["pages"]
                if "-" in p:
                    sp, ep = p.split("-", 1)
                    f.write(f"SP  - {sp.strip()}\n")
                    f.write(f"EP  - {ep.strip()}\n")
                else:
                    f.write(f"SP  - {p}\n")
            if r["doi"]:
                f.write(f"DO  - {r['doi']}\n")
                f.write(f"UR  - https://doi.org/{r['doi']}\n")
            if r["abstract"]:
                f.write(f"AB  - {r['abstract']}\n")
            if r["id"]:
                f.write(f"AN  - {r['id']}\n")
            f.write("DB  - Dimensions\n")
            f.write("ER  - \n\n")

    fields = ["id", "title", "authors", "year", "journal", "doi",
              "volume", "number", "pages", "type", "abstract"]
    with csvf.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in records:
            w.writerow(r)
    return ris, csvf


def write_summary(records, prefix, folder, url, mode, reported):
    p = folder / f"{prefix}_summary.txt"
    with_doi = sum(1 for r in records if r["doi"])
    with_ab = sum(1 for r in records if r["abstract"])
    with_year = sum(1 for r in records if r["year"])
    anios = sorted(r["year"] for r in records if r["year"])
    with p.open("w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("DIMENSIONS HARVEST SUMMARY\n")
        f.write("=" * 70 + "\n")
        f.write(f"Search address           : {url}\n")
        f.write(f"Run date                 : {datetime.now():%Y-%m-%d %H:%M}\n")
        f.write(f"Extraction route         : {mode}\n")
        f.write(f"Reported yield           : {reported or 'not detected'}\n")
        f.write(f"Records retrieved        : {len(records)}\n")
        f.write(f"With DOI identifier      : {with_doi}\n")
        f.write(f"With abstract            : {with_ab}\n")
        f.write(f"With year                : {with_year}\n")
        if anios:
            f.write(f"Year range               : {anios[0]} a {anios[-1]}\n")
        f.write("\nThe figure reported by the platform and the records\n")
        f.write("retrieved are recorded separately in the flow diagram.\n")
    return p


# --------------------------------------------------------------------------
# Programme
# --------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("DIMENSIONS HARVESTER")
    print("=" * 70)
    print("First run the query in app.dimensions.ai and paste here the")
    print("full address of the results page.")
    print()

    url = ask("Address")
    if not url.startswith("http"):
        warning("The address is not valid.")
        return

    print()
    print("Working mode:")
    print("  1  Harvest")
    print("  2  Inspect the platform's calls")
    op_mode = ask("Option", "1")
    inspection = (op_mode == "2")

    prefix = ask("Prefix of the output files", "DIMENSIONS_DIM")
    maximum = ask("Maximum number of records, Enter for all", "0")
    try:
        maximum = int(maximum)
    except ValueError:
        maximum = 0

    folder = Path.cwd()
    print()
    print("-" * 70)
    print(f"Address   : {url[:110]}")
    print(f"Mode      : {'inspection' if inspection else 'harvest'}")
    print(f"Output    : {prefix}.ris and {prefix}.csv")
    print(f"Folder    : {folder}")
    print(f"Maximum   : {'no limit' if maximum == 0 else maximum}")
    print(f"Profile   : {PROFILE}")
    print("-" * 70)
    if ask("Confirm, y or n", "s").lower() not in ("s", "yes", ""):
        return

    records = {}
    calls = []
    reported = ""
    via = "network capture"

    def on_response(resp):
        try:
            ct = (resp.headers or {}).get("content-type", "")
            if "json" not in ct.lower():
                return
            body = resp.json()
        except Exception:
            return

        found = []
        recolecta(body, found)

        if inspection:
            calls.append({
                "url": resp.url[:220],
                "status": resp.status,
                "records_detected": len(found),
                "sample_keys": sorted(found[0].keys())[:25] if found else [],
            })
            return

        for d in found:
            r = normaliza(d)
            k = unique_key(r)
            if k not in records:
                records[k] = r

    print()
    warning("Opening the browser. Log in if the platform asks for it.")
    warning("The window stays open: do not close it until it finishes.")
    print()

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            headless=False,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.on("response", on_response)

        page.goto(url, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(6000)

        # Figure that the platform declares
        try:
            text = page.inner_text("body")[:6000]
            for pattern in (r"([\d][\d.,]{0,11})\s*(?:publications?|results?|resultados?)",
                           r"(?:publications?|results?|resultados?)\s*[:\(]?\s*([\d][\d.,]{0,11})"):
                m = re.search(pattern, text, re.I)
                if m:
                    reported = m.group(1)
                    warning(f"Yield reported by the platform: {reported}")
                    break
        except Exception:
            pass

        if inspection:
            warning("Scrolling to trigger calls. Wait a few seconds...")
            for _ in range(6):
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(1800)
            destination = folder / f"{prefix}_inspection.txt"
            with destination.open("w", encoding="utf-8") as f:
                f.write(f"Address inspected: {url}\n")
                f.write(f"JSON calls detected: {len(calls)}\n")
                f.write("=" * 70 + "\n\n")
                for c in calls:
                    f.write(f"URL      : {c['url']}\n")
                    f.write(f"Status   : {c['status']}\n")
                    f.write(f"Records: {c['records_detected']}\n")
                    if c["sample_keys"]:
                        f.write(f"Keys     : {', '.join(c['sample_keys'])}\n")
                    f.write("-" * 70 + "\n")
            warning(f"Inspection written to {destination}")
            warning("Send it to the maintainer so the harvester can be adapted to what the platform uses.")
            input("Press Enter to close the browser...")
            ctx.close()
            return

        # ---------------- harvest ----------------
        no_news = 0
        last_saved = 0
        round_ = 0

        while True:
            round_ += 1
            before = len(records)

            # 1. Scroll so that the platform requests the next block
            page.mouse.wheel(0, 6000)
            page.wait_for_timeout(LOAD_WAIT)
            new = len(records) - before

            # 2. Fallback to the document if the network gives nothing
            if len(records) == 0 and round_ >= 3:
                try:
                    raw_items = page.evaluate(JS_FALLBACK)
                    for d in raw_items:
                        r = normaliza(d)
                        if r["title"]:
                            records.setdefault(unique_key(r), r)
                    if records:
                        via = "document reading"
                        new = len(records) - before
                        warning("Network capture without results; the document is read.")
                except Exception:
                    pass

            # 3. Only when scrolling is exhausted, move to the next page
            if new == 0:
                for sel in ('button:has-text("Load more")',
                            'button:has-text("Show more")',
                            '[aria-label="Next page"]',
                            'button:has-text("Next")'):
                    try:
                        b = page.query_selector(sel)
                        if b and b.is_enabled() and b.is_visible():
                            b.click()
                            page.wait_for_timeout(LOAD_WAIT + 1500)
                            if via == "document reading":
                                for d in page.evaluate(JS_FALLBACK):
                                    r = normaliza(d)
                                    if r["title"]:
                                        records.setdefault(unique_key(r), r)
                            new = len(records) - before
                            break
                    except Exception:
                        pass

            print(f"Round {round_}: {new} new, cumulative {len(records)}",
                  flush=True)

            no_news = no_news + 1 if new == 0 else 0

            if len(records) - last_saved >= PARTIAL_SAVE:
                escribe(list(records.values()), prefix, folder)
                last_saved = len(records)
                warning(f"   partial save: {len(records)} records")

            if no_news >= MAX_NO_NEWS:
                warning("No new records. Stopping.")
                break
            if maximum and len(records) >= maximum:
                warning("Maximum reached.")
                break

        ctx.close()

    items = list(records.values())
    if not items:
        print()
        warning("No record was retrieved.")
        warning("Run again with option 2, Inspect, and send")
        warning("the file it produces so the harvester can be adapted.")
        return

    ris, csvf = escribe(items, prefix, folder)
    res = write_summary(items, prefix, folder, url, via, reported)
    print()
    print("=" * 70)
    print(f"Written {len(items)} records")
    print(f"  {ris}")
    print(f"  {csvf}")
    print(f"  {res}")
    with_doi = sum(1 for r in items if r["doi"])
    with_ab = sum(1 for r in items if r["abstract"])
    print(f"With DOI: {with_doi} | With abstract: {with_ab}")
    if reported:
        print(f"Yield reported by the platform: {reported}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by the operator.")
