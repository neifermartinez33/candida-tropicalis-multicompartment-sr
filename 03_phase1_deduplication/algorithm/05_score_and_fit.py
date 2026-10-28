#!/usr/bin/env python3
"""Phase 1, step 5: similarity function and threshold fitting.

The FORMULA is fixed a priori and declared here; only the two thresholds are
fitted, on the 300 labelled development pairs (document, section 5.6).

Similarity, for a pair (x, y):
  - If x and y share any valid DOI            -> score = 1.0        (manual, rule 1)
  - Otherwise, weighted mean of the available components:
        title   0.55   Dice coefficient over token sets
        page    0.20   first page equal
        year    0.15   year equal
        author  0.10   first-author surname equal
    A component whose value is missing on either side is dropped and the
    remaining weights are renormalised, so absence never counts as mismatch.
  - If both sides carry a valid DOI and none match, the result is multiplied
    by 0.75: a DOI mismatch is evidence against, not proof (manual, rule 2).

Tokenisation splits on any non-alphanumeric character and, for CJK runs, uses
character bigrams, since CJK titles carry no spaces.

Threshold rule, preregistered:
  tau_high = lowest score above which NO pair labelled DIFFERENT was observed
  tau_low  = highest score below which NO pair labelled DUPLICATE was observed
Everything in between goes to human adjudication.

Writes: work/pair_scores.csv, work/thresholds.json, work/fit_report.txt
"""
import os, re, csv, json, pickle, unicodedata
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
WORK = os.path.join(ROOT, '03_phase1_deduplication', 'work')
ADJ  = os.path.join(ROOT, '03_phase1_deduplication', 'adjudication')

W_TITLE, W_PAGE, W_YEAR, W_AUTHOR = 0.55, 0.20, 0.15, 0.10
DOI_MISMATCH_FACTOR = 0.75

CJK = lambda ch: ('一' <= ch <= '鿿') or ('぀' <= ch <= 'ヿ') or ('가' <= ch <= '힯')
KEEP = (('À','ɏ'), ('Ͱ','Ͽ'), ('Ѐ','ӿ'),
        ('一','鿿'), ('぀','ヿ'), ('가','힯'))

def tokens(title):
    if not title: return frozenset()
    s = unicodedata.normalize('NFKC', title).lower()
    s = re.sub(r'<[^>]+>', ' ', s)
    buf = []
    for ch in s:
        buf.append(ch if (ch.isalnum() and (ch.isascii() or any(a <= ch <= b for a, b in KEEP))) else ' ')
    out = set()
    for tok in ''.join(buf).split():
        if any(CJK(c) for c in tok):
            out.update(tok[i:i+2] for i in range(max(1, len(tok) - 1)))
        elif len(tok) > 1:
            out.add(tok)
    return frozenset(out)

def dice(a, b):
    if not a or not b: return 0.0
    inter = len(a & b)
    return 2.0 * inter / (len(a) + len(b))

def score(x, y, TOK):
    dx, dy = set(x.get('dois') or []), set(y.get('dois') or [])
    if dx and dy and (dx & dy): return 1.0
    parts = [(W_TITLE, dice(TOK[x['id']], TOK[y['id']]))]
    for w, f in ((W_PAGE, 'sp'), (W_YEAR, 'year'), (W_AUTHOR, 'a1')):
        a, b = x.get(f, ''), y.get(f, '')
        if a and b: parts.append((w, 1.0 if a == b else 0.0))
    tw = sum(w for w, _ in parts)
    s = sum(w * v for w, v in parts) / tw if tw else 0.0
    if dx and dy and not (dx & dy): s *= DOI_MISMATCH_FACTOR
    return s

recs  = pickle.load(open(os.path.join(WORK, 'records.pkl'), 'rb'))
pairs = pickle.load(open(os.path.join(WORK, 'pairs.pkl'), 'rb'))
print('tokenising %d records' % len(recs), flush=True)
TOK = {rid: tokens(r.get('title', '')) for rid, r in recs.items()}

lab = {}
for r in csv.DictReader(open(os.path.join(ADJ, 'development_set_300_2026-09-28.csv'), encoding='utf-8-sig')):
    v = (r.get('label') or '').strip().upper()
    if v: lab[(r['id_1'], r['id_2'])] = v
strata = {}
for r in csv.DictReader(open(os.path.join(WORK, 'development_set_strata.csv'), encoding='utf-8')):
    strata[(r['id_1'], r['id_2'])] = int(r['n_keys'])

dev = []
for (a, b), v in lab.items():
    dev.append((score(recs[a], recs[b], TOK), v, strata.get((a, b), 0), a, b))
dev.sort()

dups  = sorted(s for s, v, *_ in dev if v == 'DUPLICATE')
dist  = sorted(s for s, v, *_ in dev if v == 'DIFFERENT')
indec = sorted(s for s, v, *_ in dev if v == 'UNDECIDABLE')

tau_high = (max(dist) if dist else 0.0)          # above the highest DIFFERENT
tau_low  = (min(dups) if dups else 1.0)          # below the lowest DUPLICATE
inverted = tau_low <= tau_high

lines = []
def rep(s=''):
    print(s, flush=True); lines.append(s)

def q(v, p):
    if not v: return float('nan')
    i = max(0, min(len(v) - 1, int(round(p * (len(v) - 1)))))
    return v[i]

rep('=' * 78)
rep('PHASE 1 - STEP 5: similarity and thresholds')
rep('weights  title %.2f | page %.2f | year %.2f | author %.2f | doi-mismatch x%.2f'
    % (W_TITLE, W_PAGE, W_YEAR, W_AUTHOR, DOI_MISMATCH_FACTOR))
rep('=' * 78)
rep()
rep('%-14s %5s %7s %7s %7s %7s %7s' % ('label', 'n', 'min', 'p25', 'median', 'p75', 'max'))
for name, v in (('DUPLICATE', dups), ('DIFFERENT', dist), ('UNDECIDABLE', indec)):
    if v: rep('%-14s %5d %7.3f %7.3f %7.3f %7.3f %7.3f'
              % (name, len(v), v[0], q(v, .25), q(v, .5), q(v, .75), v[-1]))
rep()
rep('highest score seen among DIFFERENT : %.4f' % (max(dist) if dist else float('nan')))
rep('lowest  score seen among DUPLICATE : %.4f' % (min(dups) if dups else float('nan')))
rep()
if inverted:
    rep('THE TWO ZONES OVERLAP: some DUPLICATE score below some DIFFERENT.')
    rep('No pair of thresholds separates them cleanly. Reported below as an overlap band.')
    rep('overlap band: %.4f to %.4f' % (tau_low, tau_high))
else:
    rep('tau_high = %.4f   (at or above: merge without human reading)' % tau_high)
    rep('tau_low  = %.4f   (at or below: discard without human reading)' % tau_low)
rep()
rep('DUPLICATE below the highest DIFFERENT (would be missed by tau_high): %d'
    % sum(1 for s in dups if dist and s <= max(dist)))
rep('DIFFERENT above the lowest DUPLICATE (would be merged by tau_low)  : %d'
    % sum(1 for s in dist if dups and s >= min(dups)))
rep()
rep('where the UNDECIDABLE fall: %s' % (', '.join('%.3f' % s for s in indec) if indec else 'none'))
rep()
rep('development pairs by stratum and label, with score range')
by = defaultdict(list)
for s, v, k, *_ in dev: by[(k, v)].append(s)
rep('%-10s %-13s %5s %8s %8s' % ('stratum', 'label', 'n', 'min', 'max'))
for k in sorted({k for k, _ in by}):
    for v in ('DUPLICATE', 'DIFFERENT', 'UNDECIDABLE'):
        if (k, v) in by:
            ss = sorted(by[(k, v)])
            rep('%-10s %-13s %5d %8.3f %8.3f' % ('%d key(s)' % k, v, len(ss), ss[0], ss[-1]))

# --- score the whole candidate space ---
print('\nscoring the full pair space...', flush=True)
rows = []
for (a, b), keys in pairs.items():
    rows.append((a, b, keys, score(recs[a], recs[b], TOK)))
with open(os.path.join(WORK, 'pair_scores.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh); w.writerow(['id_1', 'id_2', 'keys', 'score'])
    for a, b, k, s in rows: w.writerow([a, b, k, '%.6f' % s])

hi = tau_high if not inverted else tau_high
lo = tau_low if not inverted else tau_low
above = sum(1 for *_, s in rows if s >= hi)
below = sum(1 for *_, s in rows if s <= lo)
mid = len(rows) - above - below
rep()
rep('APPLIED TO THE %d CANDIDATE PAIRS' % len(rows))
rep('  score >= %.4f  (automatic merge)   : %8d  (%.1f%%)' % (hi, above, 100 * above / len(rows)))
rep('  score <= %.4f  (automatic discard)  : %8d  (%.1f%%)' % (lo, below, 100 * below / len(rows)))
rep('  in between      (human adjudication): %8d  (%.1f%%)' % (mid, 100 * mid / len(rows)))

json.dump({'tau_high': tau_high, 'tau_low': tau_low, 'overlap': bool(inverted),
           'weights': {'title': W_TITLE, 'page': W_PAGE, 'year': W_YEAR, 'author': W_AUTHOR,
                       'doi_mismatch_factor': DOI_MISMATCH_FACTOR},
           'fitted_on': 'development_set_300_2026-09-28.csv', 'date': '2026-09-28'},
          open(os.path.join(WORK, 'thresholds.json'), 'w'), indent=2)
open(os.path.join(WORK, 'fit_report.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('done', flush=True)
