# -*- coding: utf-8 -*-
"""Adjudication rule RC-1, adopted on 2026-10-13.

  python3 algorithm/10_adjudication_rules.py

A component of an article (supplementary material, figure or table, with a DOI ending in
.s###, .g### or .t###) or a figshare deposit is not the same published document as the
article nor as another component: the pair is DIFFERENT_WORKS. It applies the manual frozen on
2026-09-28 ("the same published document"). Exception: if the two DOIs are identical, rule 1
of the manual (SAME_WORK) prevails and the rule does not apply.

Goes through all the pairs (model/all_pairs.jsonl), crosses them with work/layers.csv and writes
work/adjudication_rules.csv. 07_audit_close.py applies this table after the consensus and the
corpus definition uses it so as not to merge these pairs in L1.
"""
import csv, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'work', 'adjudication_rules.csv')
if os.path.exists(OUT):
    raise SystemExit("ERROR: %s already exists; it is not overwritten." % OUT)
COMP = re.compile(r'\.(s|t|g)\d{3}$')
base = lambda d: COMP.sub('', d)
fig = lambda d: d.startswith('10.6084/m9.figshare')
layers_ = {r['pair_id']: r['layer'] for r in csv.DictReader(open(os.path.join(ROOT, 'work', 'layers.csv'), encoding='utf-8'))}
rows = []
with open(os.path.join(ROOT, 'model', 'all_pairs.jsonl'), encoding='utf-8') as fh:
    for line in fh:
        x = json.loads(line)
        da = (x['a'].get('doi') or '').strip().lower(); db = (x['b'].get('doi') or '').strip().lower()
        if not (COMP.search(da) or COMP.search(db) or fig(da) or fig(db)):
            continue
        if da and da == db:
            continue
        if COMP.search(da) or COMP.search(db):
            type = 'component_same_article' if base(da) == base(db) else 'component_other_article'
        else:
            type = 'figshare_deposit'
        rows.append([x['pair_id'], layers_.get(x['pair_id'], ''), type, da, db, 'DIFFERENT_WORKS', 'RC-1'])
with open(OUT, 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['pair_id', 'layer', 'type', 'doi_a', 'doi_b', 'rule_judgement', 'rule'])
    w.writerows(rows)
print('written %s: %d pairs' % (os.path.basename(OUT), len(rows)))
