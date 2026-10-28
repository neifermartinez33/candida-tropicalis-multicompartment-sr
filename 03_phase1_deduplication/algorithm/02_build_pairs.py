#!/usr/bin/env python3
"""Phase 1, step 2: DOI hygiene and the union of candidate pairs.

Two data problems found in step 1 are handled here and both are declared:
  - 89 records carry the literal string 暂无 ("none available") in the DOI field.
    It is a placeholder, not a DOI. Left in, it would propose 3,916 pairs as
    duplicates on a false identity match.
  - 73 records carry a JSON array of two DOIs (legacy + current, from LENS).
    Both are kept, so the record blocks under either one. This raises recall.

Writes: work/pairs.pkl, work/pairs.csv, work/pairs_report.txt
"""
import os, re, json, pickle, itertools
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
WORK = os.path.join(ROOT, '03_phase1_deduplication', 'work')
recs = pickle.load(open(os.path.join(WORK, 'records.pkl'), 'rb'))

DOI_OK = re.compile(r'^10\.\d{4,9}/\S+$')
def doi_list(raw):
    if not raw: return []
    if raw.startswith('['):
        try: cand = [str(x).strip().lower() for x in json.loads(raw)]
        except Exception: cand = []
    else:
        cand = [raw]
    return [d for d in dict.fromkeys(cand) if DOI_OK.match(d)]

n_placeholder = n_multi = 0
for r in recs.values():
    dl = doi_list(r['doi'])
    if r['doi'] and not dl: n_placeholder += 1
    if len(dl) > 1: n_multi += 1
    r['dois'] = dl

keys = {'A_doi': defaultdict(list), 'B_author_year': defaultdict(list),
        'C_title60': defaultdict(list), 'D_issn_vol_page': defaultdict(list)}
for r in recs.values():
    for d in r['dois']:                 keys['A_doi'][d].append(r['id'])
    if r['a1'] and r['year']:           keys['B_author_year'][r['a1'] + '|' + r['year']].append(r['id'])
    if len(r['tnorm']) >= 10:           keys['C_title60'][r['tnorm'][:60]].append(r['id'])
    if r['issn'] and r['vol'] and r['sp']:
        keys['D_issn_vol_page'][r['issn'] + '|' + r['vol'] + '|' + r['sp']].append(r['id'])

LETTER = {'A_doi': 'A', 'B_author_year': 'B', 'C_title60': 'C', 'D_issn_vol_page': 'D'}
pairs = defaultdict(set)
per_key = {}
for name, idx in keys.items():
    c = 0
    for members in idx.values():
        if len(members) < 2: continue
        for a, b in itertools.combinations(sorted(set(members)), 2):
            pairs[(a, b)].add(LETTER[name]); c += 1
    per_key[name] = c

lines = []
def rep(s=''):
    print(s, flush=True); lines.append(s)

rep('=' * 78)
rep('PHASE 1 - STEP 2: DOI hygiene and candidate pair space')
rep('=' * 78)
rep()
rep('DOI hygiene')
rep('  records with something in the DOI field   : %d' % sum(1 for r in recs.values() if r['doi']))
rep('  values rejected as not a DOI              : %d  (of which 暂无: 89)' % n_placeholder)
rep('  records carrying two DOIs, both kept      : %d' % n_multi)
rep('  usable DOI strings after cleaning         : %d' % sum(len(r['dois']) for r in recs.values()))
rep()
rep('candidate pairs per blocking key (with overlap between keys)')
for k, v in per_key.items(): rep('  %-18s %10d' % (k, v))
rep()
rep('UNION of distinct candidate pairs          : %d' % len(pairs))
rep()
rep('how many keys support each pair')
dist = defaultdict(int)
for v in pairs.values(): dist[len(v)] += 1
for k in sorted(dist): rep('  supported by %d key(s): %8d  (%.1f%%)' % (k, dist[k], 100*dist[k]/len(pairs)))
rep()
rep('most frequent key combinations')
combo = defaultdict(int)
for v in pairs.values(): combo[''.join(sorted(v))] += 1
for k, v in sorted(combo.items(), key=lambda kv: -kv[1])[:10]:
    rep('  %-6s %8d' % (k, v))

with open(os.path.join(WORK, 'pairs.pkl'), 'wb') as fh:
    pickle.dump({k: ''.join(sorted(v)) for k, v in pairs.items()}, fh, protocol=4)
with open(os.path.join(WORK, 'pairs.csv'), 'w', encoding='utf-8') as fh:
    fh.write('id1,id2,keys\n')
    for (a, b), v in pairs.items(): fh.write('%s,%s,%s\n' % (a, b, ''.join(sorted(v))))
pickle.dump(recs, open(os.path.join(WORK, 'records.pkl'), 'wb'), protocol=4)
open(os.path.join(WORK, 'pairs_report.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('done', flush=True)
