# -*- coding: utf-8 -*-
"""Reconciliation v2 of the exports against the corpus imported into Rayyan.

Only change from reconcile_sources.py (v1, 2026-09-29), declared on 2026-10-13
after seeing the data: in RIS, the year of the title key is taken from PY, from Y1 or,
if both are missing, from DA. In v1 it was taken only from PY or Y1. Nineteen VIP patents
carry the date only in DA; Rayyan moved that year to Y1, the key did not match and v1
counted them as absent although they were in the corpus. Keys, normalisation, format
reading and method are identical to v1.

Method of the chain (the same that produced the v1 figures):
  exported : records read in the files of the PRISMA-S log, without the
             format-redundant export (rule R2).
  absent   : exported records whose DOI and title key do not appear in the
             corpus (rule R4).
  residual : corpus records without a counterpart, by multisets with a unique key
             (DOI if present; otherwise normalised title plus year).
  copies   : exported - absent + residual - corpus (rule R3).

Run from the project root. Writes new outputs with suffix _v2 and does not
overwrite any; the v1 outputs stay intact.
"""
import csv, os, re, unicodedata, sys, collections

RAW = "02_phase0_raw_corpus/raw_corpus_n47644_2026-09-28.ris"
LOG = "01_search/prisma_s_log.csv"
EXP = "01_search/exports"
DIR = "02_phase0_raw_corpus/reconciliation"
V1 = os.path.join(DIR, "reconciliation_by_file.csv")
SUF = "_v2_2026-10-13"
OUT_FILE = os.path.join(DIR, "reconciliation_by_file" + SUF + ".csv")
OUT_ABS = os.path.join(DIR, "reconciliation_absent" + SUF + ".csv")
OUT_RES = os.path.join(DIR, "reconciliation_residual" + SUF + ".csv")
OUT_TXT = os.path.join(DIR, "reconciliation_summary" + SUF + ".txt")

# Rule R2: the .txt is the same VIP sweep in another format and counts only once.
R2_REDUNDANT = {"VIP_VIP-1_chinese_159_2026-09-11.txt": "VIP_VIP-1_chinese_159_2026-09-11.ris"}

DOI_OK = re.compile(r'^10\.\d{4,9}/\S+$')
KEEP = (('À', 'ɏ'), ('Ͱ', 'Ͽ'), ('Ѐ', 'ӿ'),
        ('一', '鿿'), ('぀', 'ヿ'), ('가', '힯'))

def norm(s):
    s = unicodedata.normalize('NFKD', s or '').lower()
    out = []
    for ch in s:
        if ch.isalnum():
            if ch.isascii() or any(a <= ch <= b for a, b in KEEP):
                out.append(ch)
        elif ch.isspace():
            out.append(' ')
    return ' '.join(''.join(out).split())

def clean_doi(v):
    v = (v or '').strip().lower()
    v = re.sub(r'^(https?://)?(dx\.)?doi\.org/', '', v)
    v = re.sub(r'^doi:\s*', '', v)
    return v if DOI_OK.match(v) else ''

def recs_ris(text):
    cur, out = {}, []
    tag = re.compile(r'^([A-Z][A-Z0-9])  -[ ]?(.*)$')
    last = None
    for line in text.splitlines():
        m = tag.match(line)
        if m:
            k, v = m.group(1), m.group(2).strip()
            if k == 'ER':
                if cur: out.append(cur)
                cur, last = {}, None
                continue
            if k == 'TY' and cur:
                out.append(cur); cur = {}
            cur.setdefault(k, []).append(v); last = k
        elif line.strip() and last and cur:
            cur[last][-1] += ' ' + line.strip()
    if cur: out.append(cur)
    return out

def recs_nbib(text):
    out, cur, last = [], {}, None
    for line in text.splitlines():
        m = re.match(r'^([A-Z]{2,4})\s*-\s(.*)$', line)
        if m:
            k, v = m.group(1), m.group(2).strip()
            if k == 'PMID' and cur:
                out.append(cur); cur = {}
            cur.setdefault(k, []).append(v); last = k
        elif line.startswith('      ') and last and cur:
            cur[last][-1] += ' ' + line.strip()
        elif not line.strip():
            pass
    if cur: out.append(cur)
    return out

def recs_pct(text):
    out, cur, last = [], {}, None
    for line in text.splitlines():
        m = re.match(r'^%(.) (.*)$', line)
        if m:
            k, v = m.group(1), m.group(2).strip()
            if k == '0' and cur:
                out.append(cur); cur = {}
            cur.setdefault(k, []).append(v); last = k
        elif line.strip() and last and cur:
            cur[last][-1] += ' ' + line.strip()
    if cur: out.append(cur)
    return out

def keys_from(r, kind):
    if kind == 'ris':
        doi = ''
        for f in ('DO', 'DI'):
            for v in r.get(f, []):
                doi = doi or clean_doi(v)
        for v in r.get('UR', []) + r.get('L3', []):
            doi = doi or clean_doi(v)
        ti = ' '.join(r.get('TI', []) or r.get('T1', []) or r.get('BT', []))
        yr = ' '.join(r.get('PY', []) or r.get('Y1', []) or r.get('DA', []))   # v2: DA
    elif kind == 'nbib':
        doi = ''
        for v in r.get('AID', []) + r.get('LID', []):
            doi = doi or clean_doi(v.replace(' [doi]', ''))
        ti = ' '.join(r.get('TI', []))
        yr = ' '.join(r.get('DP', []))
    else:
        doi = ''
        for v in r.get('R', []) + r.get('U', []):
            doi = doi or clean_doi(v)
        ti = ' '.join(r.get('T', []))
        yr = ' '.join(r.get('D', []))
    y = re.search(r'(19|20)\d{2}', yr)
    return doi, (norm(ti)[:120] + '|' + (y.group(0) if y else '')) if ti.strip() else ''

def parse(path):
    text = open(path, encoding='utf-8', errors='replace').read()
    ext = os.path.splitext(path)[1].lower()
    if ext == '.nbib':
        return [keys_from(r, 'nbib') for r in recs_nbib(text)]
    if ext == '.enw' or (ext == '.txt' and '%0 ' in text[:2000]):
        return [keys_from(r, 'pct') for r in recs_pct(text)]
    return [keys_from(r, 'ris') for r in recs_ris(text)]

if __name__ == '__main__':
    ya = [p for p in (OUT_FILE, OUT_ABS, OUT_RES, OUT_TXT) if os.path.exists(p)]
    if ya:
        sys.exit("STOP: v2 outputs already exist (%s); they are not overwritten." % ", ".join(map(os.path.basename, ya)))

    crs = recs_ris(open(RAW, encoding='utf-8', errors='replace').read())
    corpus = [(r.get('AN', [''])[0],) + keys_from(r, 'ris') for r in crs]
    CD = {d for _, d, t in corpus if d}
    CT = {t for _, d, t in corpus if t}

    idx = {}
    for root, _, fs in os.walk(EXP):
        for f in fs:
            idx.setdefault(f, os.path.join(root, f))

    rows, absent, EK = [], [], []
    for r in csv.DictReader(open(LOG, encoding='utf-8')):
        p = idx.get(r['file'])
        if not p:
            continue
        ks = parse(p)
        count_ = r['file'] not in R2_REDUNDANT
        aus = [(i, d, t) for i, (d, t) in enumerate(ks, 1) if not ((d and d in CD) or (t and t in CT))]
        rows.append(dict(source=r['source'], file=r['file'], log=int(r['records']), parsed=len(ks),
                          in_corpus=len(ks) - len(aus), absent=len(aus),
                          in_chain='yes' if count_ else 'no (R2: ' + R2_REDUNDANT[r['file']] + ')'))
        if count_:
            EK += ks
            absent += [dict(source=r['source'], file=r['file'], position=i, doi=d, title_key=t) for i, d, t in aus]

    E = collections.Counter(d or t for d, t in EK)
    C = collections.Counter(d or t for _, d, t in corpus)
    ids_by_key = collections.defaultdict(list)
    for a, d, t in corpus:
        ids_by_key[d or t].append(a)
    resid = [(k, n, E[k], n - E[k]) for k, n in C.items() if n > E[k]]
    n_exp, n_aus, n_cor = len(EK), len(absent), len(corpus)
    n_res = sum(x[3] for x in resid)
    n_cop = n_exp - n_aus + n_res - n_cor

    with open(OUT_FILE, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    with open(OUT_ABS, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['source', 'file', 'position', 'doi', 'title_key'])
        w.writeheader(); w.writerows(absent)
    with open(OUT_RES, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['key', 'n_corpus', 'n_exported', 'residual', 'rayyan_ids'])
        for k, n, e, x in sorted(resid):
            w.writerow([k, n, e, x, ';'.join(ids_by_key[k])])

    v1 = {r['file']: int(r['absent']) for r in csv.DictReader(open(V1, encoding='utf-8'))}
    changes = [(f['file'], v1.get(f['file']), f['absent']) for f in rows if v1.get(f['file']) != f['absent']]
    L = ["Reconciliation v2 (2026-10-13). Year of the RIS key: PY, Y1 or DA.",
         "",
         "exported %d - absent %d - consolidated copies %d + residual %d = corpus %d"
         % (n_exp, n_aus, n_cop, n_res, n_exp - n_aus - n_cop + n_res),
         "files in the chain: %d of %d (R2 excludes %s)"
         % (sum(1 for f in rows if f['in_chain'] == 'yes'), len(rows), ", ".join(R2_REDUNDANT)),
         "",
         "absent by file:"]
    L += ["  %-50s %d" % (f['file'], f['absent']) for f in rows if f['absent'] and f['in_chain'] == 'yes']
    L += ["", "changes from v1 (file: absent v1 -> v2):"]
    L += ["  %-50s %s -> %d" % c for c in changes] or ["  none"]
    open(OUT_TXT, 'w', encoding='utf-8').write("\n".join(L) + "\n")
    print("\n".join(L))
