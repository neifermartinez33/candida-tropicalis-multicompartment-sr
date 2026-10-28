# -*- coding: utf-8 -*-
"""Investigates the residual of reconciliation v2 (rule R5): corpus records without a
key counterpart in the exports.

For each residual key it searches, in the exports that enter the chain (without the
format-redundant one, rule R2), records with another unique key that match some copy
of the corpus by a relaxed criterion:
  same DOI; same normalised title plus year (the DOI is on one side and not the other);
  same normalised title without year (different or missing year).
If the counterparts are enough to cover the residual of the key, the residual is
explained by a key difference: in the balance, the counterpart appears as a
consolidated copy (R3). What is not covered is declared as not explained.

Run from the project root. Writes
02_phase0_raw_corpus/reconciliation/reconciliation_residual_explained_v2_2026-10-13.csv and does not
overwrite. It does not change any figure of the chain.
"""
import csv, os, sys, collections
DIR = "02_phase0_raw_corpus/reconciliation"
OUT = os.path.join(DIR, "reconciliation_residual_explained_v2_2026-10-13.csv")
if os.path.exists(OUT):
    sys.exit("STOP: %s already exists; it is not overwritten." % OUT)
src = open(os.path.join(DIR, "reconcile_sources_v2.py"), encoding="utf-8").read()
g = {}
exec(compile(src[:src.index("if __name__ == '__main__':")], "reconcile_sources_v2.py", "exec"), g)

def without_year(t):
    return t.rsplit('|', 1)[0] if t else ''

crs = g['recs_ris'](open(g['RAW'], encoding='utf-8', errors='replace').read())
corpus = []
for r in crs:
    d, t = g['keys_from'](r, 'ris')
    corpus.append({'id': r.get('AN', [''])[0], 'doi': d, 'tk': t, 'tt': without_year(t),
                   'title': ' '.join(r.get('TI', []) or r.get('T1', [])), 'year': ' '.join(r.get('Y1', []) or r.get('PY', []))})
idx = {}
for root, _, fs in os.walk(g['EXP']):
    for f in fs:
        idx.setdefault(f, os.path.join(root, f))
exp = []
for r in csv.DictReader(open(g['LOG'], encoding='utf-8')):
    if r['file'] not in idx or r['file'] in g['R2_REDUNDANT']:
        continue
    for i, (d, t) in enumerate(g['parse'](idx[r['file']]), 1):
        exp.append({'file': r['file'], 'pos': i, 'doi': d, 'tk': t, 'tt': without_year(t), 'sk': d or t})
E = collections.Counter(e['sk'] for e in exp)
C = collections.Counter(c['doi'] or c['tk'] for c in corpus)
by_doi, by_tk, by_tt = (collections.defaultdict(list) for _ in range(3))
for e in exp:
    if e['doi']: by_doi[e['doi']].append(e)
    if e['tk']: by_tk[e['tk']].append(e)
    if e['tt']: by_tt[e['tt']].append(e)
copies = collections.defaultdict(list)
for c in corpus:
    copies[c['doi'] or c['tk']].append(c)

rows, abstract = [], collections.Counter()
for k, n in sorted(C.items()):
    if n <= E[k]:
        continue
    res = n - E[k]
    socios = {}
    for c in copies[k]:
        cand = []
        if c['doi']:
            cand += [(e, 'same DOI, different key') for e in by_doi[c['doi']]]
        if c['tk']:
            cand += [(e, 'DOI only in the export' if e['doi'] and not c['doi'] else
                      ('DOI only in the corpus' if c['doi'] and not e['doi'] else 'different DOI, same title and year'))
                     for e in by_tk[c['tk']]]
        if c['tt']:
            cand += [(e, 'different or missing year') for e in by_tt[c['tt']] if e['tk'] != c['tk']]
        for e, reason in cand:
            if e['sk'] != k:
                socios.setdefault((e['file'], e['pos']), reason)
    explained = min(res, len(socios))
    reasons = collections.Counter(socios.values())
    reason = reasons.most_common(1)[0][0] if socios else ''
    abstract['explained'] += explained
    abstract['not explained'] += res - explained
    if explained:
        abstract['reason: ' + reason] += explained
    rows.append({'key': k, 'n_corpus': n, 'n_exported': E[k], 'residual': res, 'explained': explained,
                  'reason': reason, 'contrapartes': ';'.join('%s#%d' % fp for fp in sorted(socios)[:5]),
                  'rayyan_ids': ';'.join(c['id'] for c in copies[k]),
                  'title': copies[k][0]['title'][:200], 'year': copies[k][0]['year']})
with open(OUT, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print("residual keys: %d   residual records: %d" % (len(rows), sum(f['residual'] for f in rows)))
for k, v in sorted(abstract.items()):
    print("  %-45s %d" % (k, v))
print("written", OUT)
