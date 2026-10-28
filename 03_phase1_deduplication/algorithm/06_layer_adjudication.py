# -*- coding: utf-8 -*-
"""Layered adjudication of phase 1.

Crosses the classification of the deterministic algorithm (thresholds of work/thresholds.json
applied to work/pair_scores.csv) against the model decisions
(model/output/decisions_clean.csv) and assigns each pair to one of the four layers
defined in section 5.7 of the phases document.

  L1  algorithm DUPLICATE  and  model SAME_WORK        -> automatic merge, audit of 200
  L2  algorithm DIFFERENT  and  model DIFFERENT_WORKS  -> no merge, sample of 1,000
  L3  disagreement between the two procedures          -> 100 % human reading
  L4  zone between thresholds or model UNDECIDABLE     -> 100 % human reading

Outputs, all in work/:
  layers.csv                  one row per pair, with the assigned layer
  layers_report.txt           cross table, counts and queue sizes
  audit_L1_200.csv            stratified sample for the L1 audit
  sample_L2_1000.csv          sample for the estimation of false negatives
  human_queue_L3_L4.csv       human adjudication queue

It decides nothing by itself: it only allocates and produces the queues.
Declared seed: 424242, the same as the production shuffle.
"""
import csv, json, os, random, sys, collections

SEED = 424242
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.join(ROOT, 'work')
MODEL = os.path.join(ROOT, 'model')
DEC = os.path.join(MODEL, 'output', 'decisions_clean.csv')

if not os.path.exists(DEC):
    sys.exit("ERROR: %s is missing. Run first: python3 verify_output.py --dedup" % DEC)

th = json.load(open(os.path.join(WORK, 'thresholds.json'), encoding='utf-8'))
TAU_LOW, TAU_HIGH = th['tau_low'], th['tau_high']

# --- algorithm scores, indexed by unordered pair of ids ---
score, keys = {}, {}
with open(os.path.join(WORK, 'pair_scores.csv'), encoding='utf-8') as fh:
    for r in csv.DictReader(fh):
        k = tuple(sorted((r['id_1'], r['id_2'])))
        score[k] = float(r['score']); keys[k] = r['keys']
print("algorithm scores:", len(score))

# --- pair_id -> pair of ids ---
pid2ids, pid2rec = {}, {}
with open(os.path.join(MODEL, 'all_pairs.jsonl'), encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if not line: continue
        d = json.loads(line)
        pid2ids[d['pair_id']] = tuple(sorted((d['a']['id'], d['b']['id'])))
        pid2rec[d['pair_id']] = (d['a'], d['b'])
print("pairs in the universe:", len(pid2ids))

# --- pairs of the development set, flagged and removed from the queues ---
# They are matched by pair of record identifiers and not by pair_id: the development
# set was numbered with prefix P and the universe with prefix Q, so the
# identifiers are not comparable.
dev_ids = set()
p = os.path.join(MODEL, 'development_pairs.jsonl')
if os.path.exists(p):
    with open(p, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line:
                d = json.loads(line)
                dev_ids.add(tuple(sorted((d['a']['id'], d['b']['id']))))
dev = {pid for pid, ii in pid2ids.items() if ii in dev_ids}
print("pairs of the development set:", len(dev_ids),
      "| located in the universe:", len(dev))
if len(dev) != len(dev_ids):
    print("WARNING: %d development pairs were not located in the universe"
          % (len(dev_ids) - len(dev)))

# --- model decisions ---
model_dec = {}
with open(DEC, newline='', encoding='utf-8') as fh:
    for r in csv.DictReader(fh):
        model_dec[r['pair_id']] = r['decision'].strip()
print("model decisions:", len(model_dec))

def alg_class(s):
    if s > TAU_HIGH: return 'DUPLICATE'
    if s < TAU_LOW:  return 'DIFFERENT'
    return 'HUMAN_ZONE'

def layer(a, m):
    if m == 'UNDECIDABLE' or a == 'HUMAN_ZONE': return 'L4'
    if a == 'DUPLICATE' and m == 'SAME_WORK':      return 'L1'
    if a == 'DIFFERENT'  and m == 'DIFFERENT_WORKS': return 'L2'
    return 'L3'

rows, cross, cap = [], collections.Counter(), collections.Counter()
without_score = 0
for pid, ids in pid2ids.items():
    m = model_dec.get(pid)
    if m is None:
        continue
    if ids not in score:
        without_score += 1
        continue
    s, kk = score[ids], keys[ids]
    a = alg_class(s)
    L = layer(a, m)
    cross[(a, m)] += 1; cap[L] += 1
    rows.append(dict(pair_id=pid, id_1=ids[0], id_2=ids[1], score='%.6f' % s,
                     keys=kk, shares_doi=('yes' if 'A' in kk else 'no'),
                     algorithm=a, model=m, layer=L,
                     is_development=('yes' if pid in dev else 'no')))

with open(os.path.join(WORK, 'layers.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=['pair_id','id_1','id_2','score','keys','shares_doi',
                                       'algorithm','model','layer','is_development'])
    w.writeheader(); w.writerows(rows)

# --- samples, with declared seed ---
rnd = random.Random(SEED)

FIELDS = ['title', 'authors', 'year', 'journal', 'vol', 'num', 'pag', 'doi', 'type', 'issn']

def take(pool, n, name, stratum=''):
    """Writes two files: the blind sheet the reviewer reads, with the bibliographic
    metadata of the two records and no sign of what the algorithm and the model
    decided; and the key, which stays sealed until the judgements are
    recorded. Without this separation the audit is not independent:
    showing the verdict before judging induces confirmation."""
    pool = sorted(pool, key=lambda r: r['pair_id'])
    sel = pool if len(pool) <= n else rnd.sample(pool, n)
    sel = sorted(sel, key=lambda x: x['pair_id'])
    order = list(range(len(sel)))
    rnd.shuffle(order)                      # the reading order does not reveal the stratum

    cab = ['row', 'pair_id'] + ['a_' + c for c in FIELDS] + ['b_' + c for c in FIELDS] \
          + ['human_judgement', 'reviewer', 'date', 'note']
    with open(os.path.join(WORK, name + '_blind.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(cab)
        for i, k in enumerate(order, 1):
            r = sel[k]; a, b = pid2rec[r['pair_id']]
            w.writerow([i, r['pair_id']] + [a.get(c, '') for c in FIELDS]
                       + [b.get(c, '') for c in FIELDS] + ['', '', '', ''])
    with open(os.path.join(WORK, name + '_key.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['pair_id', 'stratum', 'score', 'keys', 'shares_doi',
                    'algorithm', 'model', 'layer'])
        for r in sorted(sel, key=lambda x: x['pair_id']):
            w.writerow([r['pair_id'], stratum, r['score'], r['keys'],
                        r['shares_doi'], r['algorithm'], r['model'], r['layer']])
    return len(sel)

L1 = [r for r in rows if r['layer'] == 'L1' and r['is_development'] == 'no']
L2 = [r for r in rows if r['layer'] == 'L2' and r['is_development'] == 'no']
HQ = [r for r in rows if r['layer'] in ('L3', 'L4') and r['is_development'] == 'no']

n_with = take([r for r in L1 if r['shares_doi'] == 'yes'], 100, 'audit_L1_with_doi', 'L1_with_doi')
n_without = take([r for r in L1 if r['shares_doi'] == 'no'], 100, 'audit_L1_without_doi', 'L1_without_doi')
n_l2  = take(L2, 1000, 'sample_L2_1000', 'L2')
n_hq  = take(HQ, len(HQ), 'human_queue_L3_L4', 'L3_L4')

# --- report ---
out = []
A = out.append
A("Layered adjudication, phase 1")
A("thresholds: tau_low=%.4f  tau_high=%.4f  (strict inequalities)" % (TAU_LOW, TAU_HIGH))
A("pairs crossed: %d   without algorithm score: %d" % (len(rows), without_score))
A("")
A("CROSS TABLE  (rows: algorithm, columns: model)")
cols = ['SAME_WORK', 'DIFFERENT_WORKS', 'UNDECIDABLE']
A("%-14s %12s %16s %13s %10s" % ('', *cols, 'total'))
for a in ('DUPLICATE', 'HUMAN_ZONE', 'DIFFERENT'):
    vals = [cross[(a, c)] for c in cols]
    A("%-14s %12d %16d %13d %10d" % (a, *vals, sum(vals)))
tot = sum(cross.values())
A("%-14s %12d %16d %13d %10d" % ('total', *[sum(cross[(a,c)] for a in ('DUPLICATE','HUMAN_ZONE','DIFFERENT')) for c in cols], tot))
A("")
A("ALLOCATION BY LAYER")
for L, desc in (('L1','automatic merge, stratified audit'),
                ('L2','no merge, false-negative sample'),
                ('L3','disagreement, 100 % human reading'),
                ('L4','undecidable or zone between thresholds, 100 % human reading')):
    A("  %s  %7d  %6.2f %%   %s" % (L, cap[L], 100*cap[L]/tot, desc))
A("")
A("QUEUES PRODUCED")
A("  L1 audit with shared DOI       : %d pairs  (audit_L1_with_doi_blind.csv)" % n_with)
A("  L1 audit without shared DOI    : %d pairs  (audit_L1_without_doi_blind.csv)" % n_without)
A("  L2 false-negative sample       : %d pairs  (sample_L2_1000_blind.csv)" % n_l2)
A("  human queue L3 and L4          : %d pairs  (human_queue_L3_L4_blind.csv)" % n_hq)
A("")
A("pairs of the development set excluded from the queues: %d"
  % sum(1 for r in rows if r['is_development'] == 'yes'))
A("sampling seed: %d" % SEED)

# --- decisions file restricted to the declared universe ---
FINAL = os.path.join(MODEL, 'output', 'decisions_corpus.csv')
with open(DEC, newline='', encoding='utf-8') as fh:
    rd = csv.DictReader(fh); fields = rd.fieldnames
    keep = [r for r in rd if r['pair_id'] in pid2ids]
with open(FINAL, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(keep)
A("")
A("FINAL DECISIONS FILE")
A("  decisions_clean.csv   : %d rows (removes repeats, keeps fabricated identifiers)"
  % sum(1 for _ in open(DEC, encoding='utf-8')) )
A("  decisions_corpus.csv  : %d rows, restricted to the declared universe. This is the one deposited."
  % len(keep))

txt = "\n".join(out)
open(os.path.join(WORK, 'layers_report.txt'), 'w', encoding='utf-8').write(txt + "\n")
print()
print(txt)
