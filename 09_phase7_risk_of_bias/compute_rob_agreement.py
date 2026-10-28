# -*- coding: utf-8 -*-
"""Agreement between the two reviewers in the risk-of-bias extraction, and consensus lists.

Usage, from the project root:
  python3 -I -B 09_phase7_risk_of_bias/compute_rob_agreement.py PHASE COD1=BOOK1 COD2=BOOK2 [--out DIR]
PHASE: CAL-RB1 (calibration of 200) or PASS (the remaining 904).
CODn=BOOKn: reviewer code and their filled workbook, for example
  reviewer_1=09_phase7_risk_of_bias/rob_cal1_reviewer_1_2026-10-22T094816.xlsx

Rules: manual rob_manual_v2_2026-10-21.md and rules rob_rules_v2_2026-10-21.md.
The field compared is dedup_rule, in two forms: its eight values and the collapse to the
RB8 score (Yes, No, Not applicable, Unclear), which is the one that enters the overall judgement. With a
dominant category kappa underestimates agreement, so the report always gives the
observed agreement and the contingency table next to kappa.

Writes in DIR (by default 09_phase7_risk_of_bias/results), without overwriting:
  rob_agreement_PHASE_<date>.txt        report with the two tables, agreement, kappa and 95 % CI
  rob_PHASE_decisions.csv               one report per row, the value of each reviewer and the final one
  rob_PHASE_discrepancies.csv           only the discrepancies, with both quotes, for arbitration
  rob_PHASE_structural_issues.csv       rows that break the recording rules of the manual
95 % CI: asymptotic standard error of Fleiss, Cohen and Everitt (1969), general form.
"""
import csv, datetime, hashlib, math, os, sys

import openpyxl

PHASES = ("CAL-RB1", "PASS")
DEDUP = ["by_patient", "by_host_or_site", "by_sampling_point",
         "declared_unspecified", "repeated_included", "not_declared",
         "single_sampling", "not_retrievable"]
RB8 = {"by_patient": "Yes", "by_host_or_site": "Yes", "by_sampling_point": "Yes",
       "declared_unspecified": "Yes", "repeated_included": "No", "not_declared": "No",
       "single_sampling": "Not applicable", "not_retrievable": "Unclear"}
RB8_ORDER = ["Yes", "No", "Not applicable", "Unclear"]
EDITORIAL = ["peer_reviewed", "preprint", "grey"]
C5DEF = ["strict", "broad", "not_applicable"]
AGRO = ["documented_present", "documented_absent", "not_evaluated"]
THRESHOLD = 0.60


def leave(msg):
    sys.exit("ERROR: " + msg)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def now_co():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("America/Bogota")), "Colombia time"
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc), "UTC"


def read_book(path, cod):
    """Returns (order of report_id, rows per report_id). Requires the sheet and the columns of the workbook."""
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception as e:
        leave("%s: cannot be opened (%s)" % (path, e))
    if "Extraction" not in wb.sheetnames:
        leave("%s: does not carry the sheet Extraction" % path)
    ws = wb["Extraction"]
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        leave("%s: the sheet Extraction is empty" % path)
    hdr = [str(h).strip() if h is not None else "" for h in rows[0]]
    for c in ("report_id", "dedup_rule", "dedup_quote", "dedup_page", "methods_read",
              "editorial_status"):
        if c not in hdr:
            leave("%s: the column %s is missing" % (path, c))
    idx = {c: hdr.index(c) for c in hdr if c}
    order, data_ = [], {}
    for r in rows[1:]:
        if r is None or all(v is None or str(v).strip() == "" for v in r):
            continue
        g = lambda c: ("" if idx.get(c) is None or idx[c] >= len(r) or r[idx[c]] is None
                       else str(r[idx[c]]).strip())
        rid = g("report_id")
        if not rid:
            leave("%s: there is a row without report_id" % path)
        if rid in data_:
            leave("%s: report %s appears more than once" % (path, rid))
        order.append(rid)
        data_[rid] = {c: g(c) for c in idx}
        data_[rid]["_reviewer"] = cod
    wb.close()
    return order, data_


def review(data_, cod, has_site):
    """Recording rules of the manual. Returns a list of (report_id, reviewer, problem)."""
    out = []
    for rid, d in data_.items():
        v = d.get("dedup_rule", "")
        if not v:
            out.append((rid, cod, "dedup_rule without value"))
        elif v not in DEDUP:
            out.append((rid, cod, "dedup_rule with a value not allowed: %s" % v))
        else:
            if v != "not_declared" and not (d.get("dedup_quote") and d.get("dedup_page")):
                out.append((rid, cod, "%s without quote or without page" % v))
            if v == "not_declared" and d.get("methods_read", "").upper() != "YES":
                out.append((rid, cod, "not_declared without methods_read"))
        e = d.get("editorial_status", "")
        if not e:
            out.append((rid, cod, "editorial_status without value"))
        elif e not in EDITORIAL:
            out.append((rid, cod, "editorial_status with a value not allowed: %s" % e))
        if not has_site:
            continue
        aplica = d.get("site_applies", "").upper() == "YES"
        c5, ag = d.get("c5_definition", ""), d.get("agronomic_management", "")
        if aplica:
            if not c5 or not ag:
                out.append((rid, cod, "site_applies YES but c5_definition or agronomic_management is missing"))
            if c5 and c5 not in C5DEF:
                out.append((rid, cod, "c5_definition with a value not allowed: %s" % c5))
            if ag and ag not in AGRO:
                out.append((rid, cod, "agronomic_management with a value not allowed: %s" % ag))
            if c5 == "strict" and ag != "documented_absent":
                out.append((rid, cod, "strict without agronomic_management documented_absent"))
            if ag != "not_evaluated" and ag and not (d.get("agro_quote") and d.get("agro_page")):
                out.append((rid, cod, "%s without quote or without page" % ag))
        elif c5 or ag or d.get("agro_quote") or d.get("agro_page"):
            out.append((rid, cod, "site_applies NO but carries site fields"))
    return out


def kappa_ic(A, B, cats, ids):
    """Unweighted Cohen's kappa and its 95 % CI. Returns (n, table, po, pe, kappa, li, ls, note)."""
    n = len(ids)
    k = len(cats)
    pos = {c: i for i, c in enumerate(cats)}
    tab = [[0] * k for _ in range(k)]
    for o in ids:
        tab[pos[A[o]]][pos[B[o]]] += 1
    p = [[tab[i][j] / n for j in range(k)] for i in range(k)]
    row = [sum(p[i]) for i in range(k)]                 # marginals of reviewer 1
    col = [sum(p[i][j] for i in range(k)) for j in range(k)]   # marginals of reviewer 2
    po = sum(p[i][i] for i in range(k))
    pe = sum(row[i] * col[i] for i in range(k))
    if 1 - pe < 1e-12:
        return n, tab, po, pe, None, None, None, (
            "Kappa not defined: the agreement expected by chance is 1, because practically everything "
            "falls in a single category. The decision has to rest on the observed agreement.")
    kap = (po - pe) / (1 - pe)
    t1 = sum(p[i][i] * (1 - (row[i] + col[i]) * (1 - kap)) ** 2 for i in range(k))
    t2 = (1 - kap) ** 2 * sum(p[i][j] * (col[i] + row[j]) ** 2
                              for i in range(k) for j in range(k) if i != j)
    t3 = (kap - pe * (1 - kap)) ** 2
    se = math.sqrt(max(t1 + t2 - t3, 0) / n) / (1 - pe)
    return n, tab, po, pe, kap, kap - 1.96 * se, kap + 1.96 * se, ""


def table_txt(cats, tab, c1, c2, width=22):
    enc = " " * (width + 2) + "".join("%10s" % c[:10] for c in cats) + "%10s" % "total"
    out = ["  %s (rows) against %s (columns)" % (c1, c2), enc]
    for i, c in enumerate(cats):
        out.append("  %-*s" % (width, c[:width]) + "".join("%10d" % v for v in tab[i])
                   + "%10d" % sum(tab[i]))
    out.append("  %-*s" % (width, "total")
               + "".join("%10d" % sum(tab[i][j] for i in range(len(cats))) for j in range(len(cats)))
               + "%10d" % sum(sum(f) for f in tab))
    return out


def main():
    args = list(sys.argv[1:])
    out = "09_phase7_risk_of_bias/results"
    if "--out" in args:
        i = args.index("--out"); out = args[i + 1]; del args[i:i + 2]
    if len(args) != 3 or args[0] not in PHASES or not all("=" in a for a in args[1:]):
        sys.exit(__doc__)
    phase = args[0]
    readers = [tuple(a.split("=", 1)) for a in args[1:]]
    if readers[0][0] == readers[1][0]:
        leave("the two reviewers have the same code")
    (c1, p1), (c2, p2) = readers
    for p in (p1, p2):
        if not os.path.exists(p):
            leave("cannot find %s" % p)

    orden1, d1 = read_book(p1, c1)
    orden2, d2 = read_book(p2, c2)
    if set(orden1) != set(orden2):
        leave("the two workbooks do not cover the same reports: %d in excess in %s and %d in %s"
              % (len(set(orden1) - set(orden2)), c1, len(set(orden2) - set(orden1)), c2))
    if orden1 != orden2:
        leave("the two workbooks carry the same reports in a different order; someone sorted the sheet. "
              "Go back to the original copy before continuing.")
    has_site = "site_applies" in d1[orden1[0]] and "site_applies" in d2[orden2[0]]

    problems = review(d1, c1, has_site) + review(d2, c2, has_site)
    bad = {rid for rid, _, _ in problems}
    ids = [o for o in orden1 if o not in bad]
    if not ids:
        leave("no row passes the recording rules; check the issues file")

    A8 = {o: d1[o]["dedup_rule"] for o in ids}
    B8 = {o: d2[o]["dedup_rule"] for o in ids}
    A4 = {o: RB8[A8[o]] for o in ids}
    B4 = {o: RB8[B8[o]] for o in ids}
    r8 = kappa_ic(A8, B8, DEDUP, ids)
    r4 = kappa_ic(A4, B4, RB8_ORDER, ids)

    os.makedirs(out, exist_ok=True)
    now, zone = now_co()
    stamp = now.strftime("%Y%m%d_%H%M%S")
    dest = {"report": os.path.join(out, "rob_agreement_%s_%s.txt" % (phase, stamp)),
            "decisions": os.path.join(out, "rob_%s_decisions.csv" % phase),
            "discrepancies": os.path.join(out, "rob_%s_discrepancies.csv" % phase),
            "issues": os.path.join(out, "rob_%s_structural_issues.csv" % phase)}
    for p in dest.values():
        if os.path.exists(p):
            leave("%s already exists; it is not overwritten" % p)

    with open(dest["decisions"], "x", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["report_id", "dedup_" + c1, "dedup_" + c2, "agreement", "RB8_" + c1, "RB8_" + c2,
                    "agreement_RB8", "dedup_final", "editorial_" + c1, "editorial_" + c2,
                    "editorial_final", "structure_reviewed"])
        for o in orden1:
            if o in bad:
                w.writerow([o, d1[o].get("dedup_rule", ""), d2[o].get("dedup_rule", ""), "", "", "",
                            "", "", d1[o].get("editorial_status", ""),
                            d2[o].get("editorial_status", ""), "", "with issue"])
                continue
            ac, ac4 = A8[o] == B8[o], A4[o] == B4[o]
            e1, e2 = d1[o]["editorial_status"], d2[o]["editorial_status"]
            w.writerow([o, A8[o], B8[o], "yes" if ac else "no", A4[o], B4[o], "yes" if ac4 else "no",
                        A8[o] if ac else "", e1, e2, e1 if e1 == e2 else "", "ok"])

    disc = [o for o in ids if A8[o] != B8[o] or d1[o]["editorial_status"] != d2[o]["editorial_status"]]
    with open(dest["discrepancies"], "x", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["report_id", "study_label", "year", "pdf_file", "dedup_" + c1, "quote_" + c1,
                    "page_" + c1, "dedup_" + c2, "quote_" + c2, "page_" + c2, "same_RB8",
                    "editorial_" + c1, "editorial_" + c2, "dedup_consensus", "editorial_consensus",
                    "arbiter", "note"])
        for o in disc:
            w.writerow([o, d1[o].get("study_label", ""), d1[o].get("year", ""),
                        d1[o].get("pdf_file", ""), A8[o], d1[o].get("dedup_quote", ""),
                        d1[o].get("dedup_page", ""), B8[o], d2[o].get("dedup_quote", ""),
                        d2[o].get("dedup_page", ""), "yes" if A4[o] == B4[o] else "no",
                        d1[o]["editorial_status"], d2[o]["editorial_status"], "", "", "", ""])

    with open(dest["issues"], "x", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["report_id", "reviewer", "problem"])
        for row in sorted(problems):
            w.writerow(row)

    def block(title, cats, r):
        n, tab, po, pe, kap, li, ls, note = r
        out = ["", title, ""] + table_txt(cats, tab, c1, c2) + [""]
        out.append("  Observed agreement: %.3f (%d of %d). Agreement expected by chance: %.3f."
                   % (po, round(po * n), n, pe))
        if kap is None:
            out.append("  " + note)
        else:
            out.append("  Cohen's kappa: %.3f. 95 %% CI: %.3f to %.3f." % (kap, li, ls))
        return out

    inf = ["Agreement of the risk-of-bias extraction, phase %s. %s, %s."
           % (phase, now.strftime("%Y-%m-%d %H:%M"), zone), "",
           "Inputs (sha256):",
           "  %s  %s  (reviewer %s)" % (sha256(p1), p1, c1),
           "  %s  %s  (reviewer %s)" % (sha256(p2), p2, c2), "",
           "Reports in the workbooks: %d. With a recording issue, excluded from the calculation: %d. "
           "Compared: %d." % (len(orden1), len(bad), len(ids))]
    inf += block("dedup_rule, the eight values of the manual", DEDUP, r8)
    inf += block("RB8, the collapse that enters the overall judgement", RB8_ORDER, r4)
    kap4 = r4[4]
    inf += ["", "Rule of the manual: second round if the collapsed kappa falls below %.2f."
            % THRESHOLD]
    if kap4 is None:
        inf.append("  It cannot be judged against the threshold: the collapsed kappa is not defined.")
    elif kap4 < THRESHOLD:
        inf.append("  NOT REACHED. Discuss discrepancies, move the manual to the next version "
                   "and calibrate again on 200 new reports.")
    else:
        inf.append("  REACHED. The full pass can go ahead.")
    disc8 = sum(1 for o in ids if A8[o] != B8[o])
    disc4 = sum(1 for o in ids if A4[o] != B4[o])
    ediff = sum(1 for o in ids if d1[o]["editorial_status"] != d2[o]["editorial_status"])
    inf += ["", "Discrepancies in dedup_rule: %d of %d (%.1f %%). That change the RB8 score: "
            "%d." % (disc8, len(ids), 100 * disc8 / len(ids), disc4),
            "Discrepancies in editorial_status: %d." % ediff,
            "Rows with a recording issue: %d, in %d reports." % (len(problems), len(bad)),
            "", "Outputs:"] + ["  %s" % dest[k] for k in ("decisions", "discrepancies", "issues")]
    with open(dest["report"], "x", encoding="utf-8") as fh:
        fh.write("\n".join(inf) + "\n")
    print("\n".join(inf))
    print("Report:", dest["report"])


if __name__ == "__main__":
    main()
