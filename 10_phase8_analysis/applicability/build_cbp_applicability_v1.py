#!/usr/bin/env python3
"""build_cbp_applicability_v1.py (2026-10-24)

Applicability matrix of the clinical breakpoint by document or version (decision D4 of 2026-10-24): one
cell per standard, document or version and agent, which says whether that document published a clinical
resistance breakpoint applicable to C. tropicalis. It is read by 04_ma_input_v2.py.

Single source: breakpoint_history_2026-10-24.csv (280 cells, each with its open URL and quote), with its
notes in breakpoint_history_notes_2026-10-24.md. This script adds no new value: it translates the code
of the source into that of the matrix with the rules below, and each row of the matrix keeps the source row
it comes from (column source).

Translation
  YES in the source                     -> YES, unless the document only has a susceptible category
                                           (echinocandins in M27-S3; caspofungin in M44-A2 and M44-S3), which
                                           becomes NS_only: there is no R category, so the row does not enter
                                           a resistance stratum.
  NO and not_covered                    -> NO.
  IE                                    -> IE (EUCAST, insufficient evidence): does not enter.
  not_located                           -> UNVERIFIED (does not enter), except for two declared derivations:
                                           M60 1st ed. (2017), when M27-S4 (2012) and M60 2nd ed. (2020) give
                                           the same code for the agent (the foreword of M27 4th ed. only
                                           announces the removal of itraconazole and flucytosine); and EUCAST 8.1
                                           voriconazole, bounded by 8.0 and 9.0, both YES.
  Method documents                      -> inherit the table with which they are interpreted (source, section 2):
                                           M27-A3 = M27-S3 (the pre-2012 regime that the parser
                                           assigns to M27-A3); M27 4th ed. = M60 1st ed.; M44 3rd ed. = zones of
                                           M60, whose values for C. tropicalis were not located:
                                           UNVERIFIED for fluconazole, voriconazole, caspofungin and
                                           micafungin, NO for the rest.
  M59 and M57S                          -> NO: they are ECV documents, not clinical breakpoint documents.
  Agents outside the tables (ketoconazole, nystatin, clotrimazole, miconazole, terbinafine and others)
                                        -> NO in every document: the tables of M27-A3 (section 6.5.3),
                                           M27M44S 3rd ed. (Table 1) and EUCAST 12.1 list the agents with a
                                           breakpoint and these are not there.
  Disc with M27 or M60 documents        -> 04_ma_input_v2.py uses the M44 documents or the row M60_disk: the
                                           M60 zone values for C. tropicalis were not located
                                           (UNVERIFIED).
Validity (valid_from, valid_to) in decimal years, from the source (section 3 of the notes) and from the
publication dates of each CLSI document.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/applicability/build_cbp_applicability_v1.py
Output (not overwritten): 10_phase8_analysis/applicability/cbp_applicability_v1_2026-10-24.csv
"""
import hashlib
import json
import os
import sys
from datetime import datetime

import pandas as pd

SRC = "10_phase8_analysis/applicability/breakpoint_history_2026-10-24.csv"
OUT = "10_phase8_analysis/applicability/cbp_applicability_v1_2026-10-24.csv"
AGENTS = ["fluconazole", "itraconazole", "voriconazole", "posaconazole", "isavuconazole", "flucytosine",
          "amphotericin B", "caspofungin", "micafungin", "anidulafungin"]
OTHER_AGENTS = ["ketoconazole", "nystatin", "clotrimazole", "miconazole", "econazole", "terbinafine", "ciclopirox",
                "butoconazole", "amorolfine", "parconazole", "ibrexafungerp", "rezafungin", "amphotericin B liposomal",
                "griseofulvin", "tioconazole", "sertaconazole", "oxiconazole", "natamycin", "ravuconazole"]
ECHINO = {"caspofungin", "micafungin", "anidulafungin"}
# matrix document: (key in the source, regime, from, to, scope)
CLSI_DOCS = [
    ("M27-P", "M27-P", "CLSI_pre2012", 1992.0, 1995.0, "broth"),
    ("M27-T", "M27-T", "CLSI_pre2012", 1995.0, 1997.0, "broth"),
    ("M27-A", "M27-A", "CLSI_pre2012", 1997.0, 2002.6, "broth"),
    ("M27-A2", "M27-A2", "CLSI_pre2012", 2002.6, 2008.3, "broth"),
    ("M27-A3", "M27-S3", "CLSI_pre2012", 2008.3, 2012.92, "broth"),
    ("M27-S3", "M27-S3", "CLSI_pre2012", 2008.3, 2012.92, "broth"),
    ("M27-S4", "M27-S4", "CLSI_SS", 2012.92, 2017.9, "broth"),
    ("M60", "M60 (1st ed)", "CLSI_SS", 2017.9, 2020.45, "broth"),
    ("M27 4th ed", "M60 (1st ed)", "CLSI_SS", 2017.9, 2020.45, "broth"),
    ("M60 2nd ed", "M60 (2nd ed)", "CLSI_SS", 2020.45, 2022.6, "broth"),
    ("M27M44S", "M27M44S (3rd ed)", "CLSI_SS", 2022.6, 2100.0, "broth"),
    ("M44-A", "M44-A", "CLSI_pre2012", 2004.4, 2009.6, "disk"),
    ("M44-A2", "M44-A2", "CLSI_pre2012", 2009.6, 2018.9, "disk"),
    ("M44-S3", "M44-S3", "CLSI_pre2012", 2009.6, 2018.9, "disk"),
    ("M44 3rd ed", "M44 3rd ed", "CLSI_SS", 2018.9, 2100.0, "disk"),
]
NS_ONLY = {("M27-S3", a) for a in ECHINO} | {("M44-A2", "caspofungin"), ("M44-S3", "caspofungin")}
EUCAST_VERSIONS = [("4.1", 2012.17, 2013.02), ("5.0", 2013.02, 2013.17), ("6.1", 2013.19, 2014.61),
                   ("7.0", 2014.61, 2015.87), ("8.0", 2015.87, 2017.17), ("8.1", 2017.17, 2018.11),
                   ("9.0", 2018.11, 2020.09), ("10.0", 2020.09, 2024.92), ("11.0", 2024.92, 2025.48),
                   ("12.0", 2025.48, 2026.27), ("12.1", 2026.27, 2100.0)]


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def code(v):
    return {"YES": "YES", "NO": "NO", "not_covered": "NO", "IE": "IE", "not_located": "UNVERIFIED"}[v]


def main():
    if not os.path.exists(SRC):
        sys.exit(f"Missing {SRC}")
    if os.path.exists(OUT):
        sys.exit(f"Already exists {OUT}: not overwritten")
    b = pd.read_csv(SRC, dtype=str, keep_default_na=False)
    cell = {(r["document_or_version"], r["agent"]): r for r in b.to_dict("records")}
    rows = []

    def add(standard, scope, key, agent, applicable, vf, vt, regime, scope_method, src, note):
        rows.append({"standard": standard, "scope": scope, "key": key, "agent": agent, "applicable": applicable,
                     "valid_from": vf, "valid_to": vt, "regime": regime, "method_scope": scope_method,
                     "source": src, "note": note})

    for key, src_doc, regime, vf, vt, msc in CLSI_DOCS:
        for ag in AGENTS:
            r = cell.get((src_doc, ag))
            if r is None:
                sys.exit(f"The source does not carry {src_doc} / {ag}")
            app = code(r["cbp_for_c_tropicalis"])
            note = r["scope_note"]
            if (src_doc, ag) in NS_ONLY and app == "YES":
                app, note = "NS_only", "Only a susceptible category (there is no R). " + note
            if src_doc == "M60 (1st ed)" and app == "UNVERIFIED":
                lo, hi = code(cell[("M27-S4", ag)]["cbp_for_c_tropicalis"]), code(cell[("M60 (2nd ed)", ag)]["cbp_for_c_tropicalis"])
                if lo == hi and lo != "UNVERIFIED":
                    app, note = lo, ("DERIVED: bounded by M27-S4 (2012) and M60 2nd ed (2020), which agree; the "
                                     "foreword of M27 4th ed only announces the removal of itraconazole and flucytosine. " + note)
            if key == "M44 3rd ed" and ag in {"fluconazole", "voriconazole", "caspofungin", "micafungin"}:
                app, note = "UNVERIFIED", "M60 zones for C. tropicalis not located. " + note
            src = f"{src_doc} | {r['source_url']} | {r['confidence']}"
            add("CLSI", "document", key, ag, app, vf, vt, regime, msc, src,
                ("Interpreted with " + src_doc + ". " if src_doc != key else "") + note)
        for ag in OTHER_AGENTS:
            add("CLSI", "document", key, ag, "NO", vf, vt, regime, msc,
                "M27-A3 sec. 6.5.3; M27M44S 3rd ed Table 1 (breakpoint_history_2026-10-24.csv)",
                "Agent outside the CLSI clinical breakpoint tables for Candida")
    for key in ("M59", "M57S"):
        for ag in AGENTS + OTHER_AGENTS:
            add("CLSI", "document", key, ag, "NO", 2016.0, 2100.0, "CLSI_SS", "broth",
                "breakpoint_history_notes_2026-10-24.md, sec. 2", "ECV document: it does not publish a clinical breakpoint")
    # disc zones with M27/M60 documents (without M44): M60 values for C. tropicalis not located
    for ag in AGENTS + OTHER_AGENTS:
        app = "UNVERIFIED" if ag in {"fluconazole", "voriconazole", "caspofungin", "micafungin"} else "NO"
        add("CLSI", "document", "M60_disk", ag, app, 2017.9, 2100.0, "CLSI_SS", "disk",
            "M44 3rd ed | breakpoint_history_2026-10-24.csv", "M60 zones for C. tropicalis not located")
    # EUCAST by version
    for v, vf, vt in EUCAST_VERSIONS:
        for ag in AGENTS:
            r = cell.get((v, ag))
            if r is None:
                sys.exit(f"The source does not carry EUCAST {v} / {ag}")
            app, note = code(r["cbp_for_c_tropicalis"]), r["scope_note"]
            if v == "8.1" and ag == "voriconazole" and app == "UNVERIFIED":
                app, note = "YES", "DERIVED: bounded by 8.0 and 9.0, both with a breakpoint. " + note
            if v == "5.0" and ag == "micafungin" and app == "UNVERIFIED":
                app, note = "NO", "IP or IE in the neighbouring versions: no usable breakpoint. " + note
            add("EUCAST", "version", v, ag, app, vf, vt, "EUCAST", "any",
                f"EUCAST {v} | {r['source_url']} | {r['confidence']}", note)
        for ag in OTHER_AGENTS:
            add("EUCAST", "version", v, ag, "NO", vf, vt, "EUCAST", "any",
                "EUCAST 12.1 Candida table (breakpoint_history_2026-10-24.csv)", "Agent outside the EUCAST table")
    # EUCAST before table 4.1 (technical notes): only fluconazole has a source
    for ag in AGENTS + OTHER_AGENTS:
        if ag == "fluconazole":
            app, src, note = "YES", "breakpoint_history_notes_2026-10-24.md, sec. 4 (EUCAST TN 2007)", "Technical note of 2007: 2/4"
        elif ag in ("caspofungin", "flucytosine", "isavuconazole") or ag in OTHER_AGENTS:
            app, src, note = "NO", "breakpoint_history_notes_2026-10-24.md, sec. 4", "Never had a EUCAST breakpoint in that period"
        else:
            app, src, note = "UNVERIFIED", "breakpoint_history_notes_2026-10-24.md, sec. 6", "Versions 1.0-3.0 not located"
        add("EUCAST", "version", "pre-4.1", ag, app, 2007.0, 2012.17, "EUCAST", "any", src, note)
    mx = pd.DataFrame(rows)
    mx.to_csv(OUT, index=False)
    log = {"script": os.path.basename(__file__), "run_time": datetime.now().astimezone().isoformat(timespec="seconds"),
           "inputs": {SRC: md5(SRC)}, "outputs": {os.path.basename(OUT): md5(OUT)}, "cells": len(mx),
           "by_applicable": mx.applicable.value_counts().to_dict()}
    with open(OUT.replace(".csv", ".json"), "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False)
    print(f"Matrix: {OUT} ({len(mx)} cells) {log['by_applicable']}")


if __name__ == "__main__":
    main()
