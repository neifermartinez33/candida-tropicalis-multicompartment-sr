#!/usr/bin/env python3
"""apply_ec2_triage_v1.py

Applies the EC2 triage on species_id (decided by the team on 2026-10-23) to the analysis
dataset, writing a new version instead of modifying the earlier one.

Of the 77 included reports with species_id = not_specified:
  A  the report DOES declare its method (API 20C, ATB 32 C, Vitek, MALDI-TOF, MLST, keys of
     Kurtzman and Fell or of Barnett...). species_id is recoded and the report is kept.
     Excluding them by EC2 would be inconsistent with the 780 'biochemical' reports and the 232
     'chromogenic' ones that are already in with the same class of method.
  B  the report only refers to another source ('as described previously [7]'). It is excluded by EC2.
  C  the extractor worked on an excerpt or the datum is in a supplement. It is kept as
     not_specified until the PDF is reviewed; RB4 scores it 'No' and SA9 measures its influence.
  D  generic, without method. It is excluded by EC2.

The quality of the declared method is not a matter for EC2 but for RB4, where 'biochemical' and
'chromogenic' score Unclear and only 'not_specified' scores No.

Usage, from the project root:
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/apply_ec2_triage_v1.py --check
  conda run --no-capture-output -n ctrop_ma python -B 10_phase8_analysis/scripts/apply_ec2_triage_v1.py
--check reports what it would do and writes nothing.
Outputs (never overwritten):
  10_phase8_analysis/data/analysis_dataset_v2_<date>/            corrected dataset
  10_phase8_analysis/data/logs/apply_ec2_triage_v1_<date-time>.json
"""
import csv, hashlib, json, os, shutil, sys
from datetime import datetime

SRC = "10_phase8_analysis/data/analysis_dataset_v1_2026-10-20"
DST = "10_phase8_analysis/data/analysis_dataset_v2_2026-10-23"
DEC = "07_phase5_full_text_screening/ec2_decisions_2026-10-23.csv"
LOG_DIR = "10_phase8_analysis/data/logs"
TABLES = ("studies.csv", "ast.csv", "molecular.csv", "genotypes.csv", "clade4.csv")
VALID = {"conventional", "chromogenic", "biochemical", "automated", "MALDI_TOF", "molecular"}
EXCLUDE_ = {"B_refers_to_other_source", "D_generic_no_method"}
RECODIFICAR = "A_declared_recode"
KEEP_ = "C_check_pdf"


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def leer(p, enc="utf-8-sig"):
    with open(p, encoding=enc, newline="") as f:
        r = csv.DictReader(f)
        return list(r), r.fieldnames


def main():
    check = "--check" in sys.argv[1:]
    if not os.path.isdir("10_phase8_analysis"):
        sys.exit("Run from the project root")
    for p in (SRC, DEC):
        if not os.path.exists(p):
            sys.exit(f"Missing {p}")
    if os.path.exists(DST) and not check:
        sys.exit(f"Already exists {DST}: not overwritten")

    dec, _ = leer(DEC)
    groups = {}
    recode = {}
    for r in dec:
        sid = (r.get("study_id") or "").strip()
        g = (r.get("group") or "").strip()
        if not sid or not g:
            sys.exit("The decisions file carries rows without study_id or without group")
        if g not in EXCLUDE_ and g != RECODIFICAR and g != KEEP_:
            sys.exit(f"Unknown group in the decisions: {g!r}")
        groups[sid] = g
        if g == RECODIFICAR:
            v = (r.get("species_id_proposed") or "").strip()
            if v not in VALID:
                sys.exit(f"{sid}: species_id_proposed {v!r} is not in the allowed vocabulary")
            recode[sid] = v
    outside = {s for s, g in groups.items() if g in EXCLUDE_}

    studies, cols_st = leer(os.path.join(SRC, "studies.csv"))
    ids = {r["study_id"] for r in studies}
    foreign = set(groups) - ids
    if foreign:
        sys.exit(f"The decisions name reports that are not in the dataset: {sorted(foreign)[:5]}")
    mal = [s for s in groups if next(r for r in studies if r["study_id"] == s)["species_id"]
           != "not_specified"]
    if mal:
        sys.exit(f"These are no longer not_specified; the dataset changed: {mal[:5]}")

    elig_before = sum(1 for r in studies if r.get("eligible_ma") == "YES")
    elig_out = sum(1 for r in studies if r["study_id"] in outside and r.get("eligible_ma") == "YES")
    print(f"Decisions: {len(groups)} reports | exclude {len(outside)} | recodificar {len(recode)} "
          f"| keep as not_specified {sum(1 for g in groups.values() if g == KEEP_)}")
    print(f"Reports in the dataset: {len(studies)} -> {len(studies) - len(outside)}")
    print(f"Eligible for meta-analysis: {elig_before} -> {elig_before - elig_out}")
    print("Recodings by category: " + ", ".join(
        f"{c} {sum(1 for v in recode.values() if v == c)}"
        for c in sorted(set(recode.values()))))
    if check:
        print("\n--check: nothing was written.")
        return

    os.makedirs(DST, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    outputs, row_list = {}, {}
    for t in TABLES:
        p_in = os.path.join(SRC, t)
        if not os.path.exists(p_in):
            continue
        rows, cols = leer(p_in)
        key = "study_id" if "study_id" in cols else None
        if key is None:
            shutil.copy2(p_in, os.path.join(DST, t))
            row_list[t] = (len(rows), len(rows))
            outputs[t] = md5(os.path.join(DST, t))
            continue
        before = len(rows)
        rows = [r for r in rows if r[key] not in outside]
        if t == "studies.csv":
            for r in rows:
                if r["study_id"] in recode:
                    r["species_id"] = recode[r["study_id"]]
        p_out = os.path.join(DST, t)
        with open(p_out, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        row_list[t] = (before, len(rows))
        outputs[t] = md5(p_out)
        print(f"  {t}: {before} -> {len(rows)} rows")

    # build_log.json: it is kept and the step is added to it, so that the PRISMA closure checks
    # still reconcile against the final number of studies.
    p_bl = os.path.join(SRC, "build_log.json")
    if os.path.exists(p_bl):
        with open(p_bl, encoding="utf-8") as f:
            bl = json.load(f)
        n_end = row_list.get("studies.csv", (0, 0))[1]
        STEP = "Without duplicate records of the same PDF"
        if isinstance(bl.get("log"), list):
            done = False
            for e in bl["log"]:
                if isinstance(e, (list, tuple)) and len(e) == 2 and e[0] == STEP:
                    e[1] = n_end; done = True
            if not done:
                sys.exit(f"ABORT: build_log.json does not carry the step {STEP!r}; "
                         "the PRISMA chain cannot be left consistent")
            bl["log"].append(["Excluded by EC2 after the species_id triage (2026-10-23)", n_end])
        else:
            sys.exit("ABORT: build_log.json does not carry 'log' as a list")
        if isinstance(bl.get("rows"), dict):
            for t, (_, d) in row_list.items():
                k = t.replace(".csv", "")
                if k in bl["rows"]:
                    bl["rows"][k] = d
        bl["ec2_triage_2026-10-23"] = {
            "excluded": sorted(outside), "recodificados": recode,
            "kept_not_specified": sorted(s for s, g in groups.items() if g == KEEP_)}
        with open(os.path.join(DST, "build_log.json"), "w", encoding="utf-8") as f:
            json.dump(bl, f, indent=1, ensure_ascii=False)
        outputs["build_log.json"] = md5(os.path.join(DST, "build_log.json"))

    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    log = {"script": os.path.basename(__file__),
           "run_time": datetime.now().astimezone().isoformat(timespec="seconds"),
           "origin": SRC, "destination": DST,
           "decisions": {DEC: md5(DEC)},
           "criterion": "EC2 applies to the non-declaration of the method, not to its quality; the quality "
                       "is graded by RB4. The reports that declare a method are recoded.",
           "excluded": len(outside), "excluded_ma_eligible": elig_out,
           "recodificados": len(recode),
           "kept_not_specified": sum(1 for g in groups.values() if g == KEEP_),
           "recodificaciones": recode,
           "rows_per_table": {t: {"before": a, "after": d} for t, (a, d) in row_list.items()},
           "md5_outputs": outputs}
    p_log = os.path.join(LOG_DIR, f"apply_ec2_triage_v1_{stamp}.json")
    with open(p_log, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=1, ensure_ascii=False)
    print(f"\nNew dataset: {DST}\nLog: {p_log}")
    print("\nThe scripts still have to be pointed to the new dataset: see the patching block.")


if __name__ == "__main__":
    main()
