#!/usr/bin/env python3
"""Phase 1, step 1: parse the raw corpus, normalise, build blocking keys.

Does NOT generate pairs yet: it reports block-size distributions first, so that
any oversized block is seen before it is expanded into pairs.

Reads : 02_phase0_raw_corpus/raw_corpus_n47644_2026-09-28.ris
Writes: 03_phase1_deduplication/work/records.pkl
        03_phase1_deduplication/work/blocks_report.txt
"""
import os, re, sys, pickle, unicodedata
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC  = os.path.join(ROOT, '02_phase0_raw_corpus', 'raw_corpus_n47644_2026-09-28.ris')
WORK = os.path.join(ROOT, '03_phase1_deduplication', 'work')
os.makedirs(WORK, exist_ok=True)

TAG = re.compile(r'^([A-Z][A-Z0-9])  -[ ]?(.*)$')
KEEP = {'TY','AN','TI','T1','Y1','PY','AU','A1','T2','JO','J2','VL','IS','SP','EP','DO','SN','UR','LA','PB'}

# Normalisation keeps CJK, Cyrillic, Greek and extended Latin. Dropping them
# empties non-Latin titles and makes them collide with each other.
KEEP_RANGES = (
    ('À','ɏ'), ('Ͱ','Ͽ'), ('Ѐ','ӿ'),
    ('一','鿿'), ('぀','ヿ'), ('가','힯'),
)
def norm(s):
    if not s: return ''
    s = unicodedata.normalize('NFKC', s).lower()
    s = re.sub(r'<[^>]+>', ' ', s)
    out = []
    for ch in s:
        if ch.isalnum() and (ch.isascii() or any(a <= ch <= b for a, b in KEEP_RANGES)):
            out.append(ch)
    return ''.join(out)

def norm_doi(d):
    if not d: return ''
    d = d.strip().lower().rstrip('.')
    for pre in ('https://doi.org/','http://dx.doi.org/','http://doi.org/','doi:'):
        if d.startswith(pre): d = d[len(pre):]
    return d.strip()

def surname(a):
    return norm(a.split(',')[0]) if a else ''

def parse(path):
    recs, cur, last = [], None, None
    with open(path, encoding='utf-8', errors='replace') as fh:
        for raw in fh:
            line = raw.rstrip('\n').rstrip('\r')
            m = TAG.match(line)
            if m:
                tag, val = m.group(1), m.group(2)
                if tag == 'TY':
                    cur = defaultdict(list); cur['TY'].append(val); last = 'TY'; continue
                if tag == 'ER':
                    if cur is not None: recs.append(cur)
                    cur, last = None, None; continue
                if cur is not None and tag in KEEP:
                    cur[tag].append(val); last = tag
                else:
                    last = None
            elif cur is not None and last and line.strip():
                cur[last][-1] += ' ' + line.strip()   # wrapped continuation line
    if cur is not None: recs.append(cur)
    return recs

def first(d, *tags):
    for t in tags:
        if d.get(t): return d[t][0]
    return ''

print('parsing', SRC, flush=True)
raw = parse(SRC)
print('records parsed:', len(raw), flush=True)

records = {}
for d in raw:
    rid = first(d, 'AN')
    title = first(d, 'TI', 'T1')
    doi = norm_doi(first(d, 'DO'))
    if not doi:
        for u in d.get('UR', []):
            if 'doi.org/' in u: doi = norm_doi(u.split('doi.org/')[-1]); break
    authors = d.get('AU', []) or d.get('A1', [])
    records[rid] = {
        'id': rid,
        'type': first(d, 'TY'),
        'title': title,
        'tnorm': norm(title),
        'year': re.sub(r'\D', '', first(d, 'Y1', 'PY'))[:4],
        'authors': authors,
        'a1': surname(authors[0]) if authors else '',
        'journal': norm(first(d, 'T2', 'JO', 'J2')),
        'vol': norm(first(d, 'VL')),
        'issue': norm(first(d, 'IS')),
        'sp': norm(first(d, 'SP')),
        'doi': doi,
        'issn': re.sub(r'[^0-9xX]', '', first(d, 'SN')).lower(),
        'lang': first(d, 'LA'),
    }

with open(os.path.join(WORK, 'records.pkl'), 'wb') as fh:
    pickle.dump(records, fh, protocol=4)
print('records.pkl written:', len(records), flush=True)

# ---- blocking keys, prespecified in 5.1 of the phases document ----
keys = {'A_doi': {}, 'B_author_year': {}, 'C_title60': {}, 'D_issn_vol_page': {}}
for r in records.values():
    if r['doi']:                       keys['A_doi'].setdefault(r['doi'], []).append(r['id'])
    if r['a1'] and r['year']:          keys['B_author_year'].setdefault(r['a1'] + '|' + r['year'], []).append(r['id'])
    if len(r['tnorm']) >= 10:          keys['C_title60'].setdefault(r['tnorm'][:60], []).append(r['id'])
    if r['issn'] and r['vol'] and r['sp']:
        keys['D_issn_vol_page'].setdefault(r['issn'] + '|' + r['vol'] + '|' + r['sp'], []).append(r['id'])

lines = []
def rep(s=''):
    print(s, flush=True); lines.append(s)

rep('=' * 78)
rep('PHASE 1 - STEP 1: parsing and blocking')
rep('corpus: %s records' % len(records))
rep('=' * 78)
rep()
rep('field coverage')
for f in ('title', 'doi', 'year', 'a1', 'journal', 'issn', 'vol', 'sp'):
    n = sum(1 for r in records.values() if r[f])
    rep('  %-10s %6d  (%.1f%%)' % (f, n, 100 * n / len(records)))
rep()
rep('%-18s %9s %9s %9s %12s %14s' % ('blocking key', 'blocks', 'records', 'largest', 'blocks>1', 'pairs'))
total_pairs = set()
for name, idx in keys.items():
    multi = {k: v for k, v in idx.items() if len(v) > 1}
    pairs = sum(len(v) * (len(v) - 1) // 2 for v in multi.values())
    largest = max((len(v) for v in idx.values()), default=0)
    rep('%-18s %9d %9d %9d %12d %14d' % (name, len(idx), sum(len(v) for v in idx.values()), largest, len(multi), pairs))
rep()
rep('largest blocks per key (top 5)')
for name, idx in keys.items():
    top = sorted(idx.items(), key=lambda kv: -len(kv[1]))[:5]
    rep('  %s' % name)
    for k, v in top:
        rep('      %5d  %s' % (len(v), k[:70]))
rep()
rep('NOTE: pair counts above are per key and overlap between keys.')
rep('The union is computed in step 2 once oversized blocks are settled.')

with open(os.path.join(WORK, 'blocks_report.txt'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(lines) + '\n')
with open(os.path.join(WORK, 'blocks.pkl'), 'wb') as fh:
    pickle.dump(keys, fh, protocol=4)
print('done', flush=True)
