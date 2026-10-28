# -*- coding: utf-8 -*-
"""Draws the calibration sample of phase 2 according to calibration_plan_2026-10-13.md.

Usage, from the project root:  python3 -I -B 04_phase2_calibration/draw_calibration_sample.py
Simple random sampling of 200 works from the phase 1 screening corpus, seed 13102026.
Does not overwrite.
"""
import csv, os, sys, random, pickle

SEED_, N = 13102026, 200
RIS = '03_phase1_deduplication/results/screening_corpus_phase1_n22403_2026-10-13.ris'
CLU = '03_phase1_deduplication/work/corpus_clusters.csv'
OUT = '04_phase2_calibration/calibration_sample_%d_seed%d' % (N, SEED_)
if any(os.path.exists(OUT + e) for e in ('.ris', '.csv')):
    sys.exit("STOP: the sample already exists; it is not overwritten.")

rep = {r['work']: r['record_id'] for r in csv.DictReader(open(CLU, encoding='utf-8')) if r['representative'] == 'yes'}
blocks, cur = {}, []
for line in open(RIS, encoding='utf-8'):
    if not cur and not line.startswith('TY  -'):
        continue
    cur.append(line)
    if line.startswith('ER  -'):
        an = next(l[6:].strip() for l in cur if l.startswith('AN  -'))
        blocks[an] = ''.join(cur)
        cur = []
assert set(blocks) == set(rep.values()), "the RIS does not match the representatives"
marco = sorted(rep)
sample = random.Random(SEED_).sample(marco, N)
R = pickle.load(open('03_phase1_deduplication/work/records.pkl', 'rb'))
N_ = pickle.load(open('03_phase1_deduplication/work/records_not_incorporated.pkl', 'rb'))
with open(OUT + '.ris', 'w', encoding='utf-8') as fh:
    for o in sample:
        fh.write(blocks[rep[o]].rstrip('\n') + '\n\n')
with open(OUT + '.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['order', 'work', 'record_id', 'title', 'year'])
    for i, o in enumerate(sample, 1):
        d = R.get(rep[o]) or N_[rep[o]]
        w.writerow([i, o, rep[o], (d.get('title') or '')[:300], d.get('year', '')])
print("frame: %d works; sample: %d; seed: %d" % (len(marco), len(sample), SEED_))
print("written %s.ris and %s.csv" % (OUT, OUT))
