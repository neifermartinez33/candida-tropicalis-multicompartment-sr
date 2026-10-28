#!/usr/bin/env python3
"""Phase 1, step 4: export pairs as JSONL for the model runs.

Writes: model/development_pairs.jsonl   (the 300 of the development set)
        model/all_pairs.jsonl           (the full candidate space)
"""
import os, json, pickle, csv
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
WORK = os.path.join(ROOT, '03_phase1_deduplication', 'work')
MODEL = os.path.join(ROOT, '03_phase1_deduplication', 'model')
ADJ = os.path.join(ROOT, '03_phase1_deduplication', 'adjudication')
os.makedirs(MODEL, exist_ok=True)

recs = pickle.load(open(os.path.join(WORK, 'records.pkl'), 'rb'))
pairs = pickle.load(open(os.path.join(WORK, 'pairs.pkl'), 'rb'))

def side(rid):
    r = recs.get(rid, {})
    au = r.get('authors', [])
    return {'id': rid, 'title': (r.get('title') or '')[:300],
            'authors': '; '.join(au[:5]) + (' et al.' if len(au) > 5 else ''),
            'year': r.get('year', ''), 'journal': r.get('journal', ''),
            'vol': r.get('vol', ''), 'num': r.get('issue', ''), 'pag': r.get('sp', ''),
            'doi': '; '.join(r.get('dois', [])), 'type': r.get('type', ''),
            'issn': r.get('issn', '')}

# development set, keeping the pair_id assigned in step 3
dev_path = os.path.join(ADJ, 'development_set_300_2026-09-28.csv')
n = 0
with open(os.path.join(MODEL, 'development_pairs.jsonl'), 'w', encoding='utf-8') as fh:
    for row in csv.DictReader(open(dev_path, encoding='utf-8-sig')):
        fh.write(json.dumps({'pair_id': row['pair_id'], 'a': side(row['id_1']), 'b': side(row['id_2'])},
                            ensure_ascii=False) + '\n'); n += 1
print('development_pairs.jsonl:', n)

m = 0
with open(os.path.join(MODEL, 'all_pairs.jsonl'), 'w', encoding='utf-8') as fh:
    for (x, y), keys in sorted(pairs.items()):
        m += 1
        fh.write(json.dumps({'pair_id': 'Q%06d' % m, 'keys': keys, 'a': side(x), 'b': side(y)},
                            ensure_ascii=False) + '\n')
print('all_pairs.jsonl:', m)
