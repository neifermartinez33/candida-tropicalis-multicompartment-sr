# -*- coding: utf-8 -*-
"""Independent verification of the preparation of screening with two readers (phase 4).
It does not reuse code from prepare_two_reader_screening.py: it rereads the corpus and the generated files.

Usage, from the project root:
  python3 -I -B 06_phase4_title_abstract_screening/verify_two_reader_import.py
Writes allocation/verification_two_readers_2026-10-14.txt. Does not overwrite.
"""
import csv, hashlib, json, os, sys

D = '06_phase4_title_abstract_screening'
OUT = D + '/allocation/verification_two_readers_2026-10-14.txt'
IMP = D + '/import/screening_reviewer_1_reviewer_2_n22203_seed1310202643.ris'
CSV = D + '/allocation/two_reader_order_and_arbiters_seed1310202643.csv'
MOD = D + '/model/model_input_n22203_seed1310202642.jsonl'
MOD_SHA = '879c79a7c80d76a3f48d66599a2058f9afdfe4e3bc81a7d228be4290a16e8512'
if os.path.exists(OUT):
    sys.exit('STOP: %s already exists; it is not overwritten.' % OUT)
L, failures = [], []
def ok(cond, text):
    L.append(('OK    ' if cond else 'FAIL ') + text)
    if not cond:
        failures.append(text)
def ris_blocks(p):
    out, cur = [], []
    for l in open(p, encoding='utf-8'):
        if not cur and not l.startswith('TY  -'):
            continue
        cur.append(l)
        if l.startswith('ER  -'):
            out.append(cur); cur = []
    return out
def body(b):
    return ''.join(l for l in b if not l.startswith('ER  -') and not l.startswith('N1  - SCREEN_ID ')).rstrip('\n')
orig = {}
for b in ris_blocks('03_phase1_deduplication/results/screening_corpus_phase1_n22403_2026-10-13.ris'):
    orig[next(l[6:].strip() for l in b if l.startswith('AN  -'))] = body(b)
rep = {r['work']: r['record_id'] for r in csv.DictReader(open('03_phase1_deduplication/work/corpus_clusters.csv', encoding='utf-8')) if r['representative'] == 'yes'}
cal = {r['work'] for r in csv.DictReader(open('04_phase2_calibration/calibration_sample_200_seed13102026.csv', encoding='utf-8'))}
rows = list(csv.DictReader(open(CSV, encoding='utf-8')))
A = {r['work']: r for r in rows}
ok(len(rows) == len(A) == 22203, 'table: %d rows, %d unique works (expected 22203)' % (len(rows), len(A)))
ok(not set(A) & cal and set(A) | cal == set(rep), 'table without calibration; table plus calibration = the 22403 works of the corpus')
ok([int(r['order']) for r in rows] == list(range(1, len(rows) + 1)), 'order 1 to n without gaps')
ok(all(r['record_id'] == rep[r['work']] for r in rows), 'each work with its representative record')
ok(all((r['reader_1'], r['reader_2']) == ('reviewer_1', 'reviewer_2') for r in rows), 'readers reviewer_1 and reviewer_2 on every work')
bl = ris_blocks(IMP)
sids = []
equal = 0
for x in bl:
    s = [l.strip().split()[-1] for l in x if l.startswith('N1  - SCREEN_ID ')]
    an = next(l[6:].strip() for l in x if l.startswith('AN  -'))
    sids.append(s[0] if len(s) == 1 else None)
    equal += len(s) == 1 and rep.get(s[0]) == an and body(x) == orig[an]
ok(len(bl) == 22203 and sids == [r['work'] for r in rows],
   'import file: %d records, in the order of the table' % len(bl))
ok(equal == len(bl), 'content identical to the corpus except the SCREEN_ID note: %d of %d' % (equal, len(bl)))
team = {r['work']: set(r['team_authors'].split(';')) for r in csv.DictReader(open(D + '/allocation/team_authored_records.csv', encoding='utf-8'))}
arb = [r['arbiter'] for r in rows]
n_o, n_a, n_t = arb.count('reviewer_3'), arb.count('reviewer_4'), arb.count('none_team_authored')
ok(n_t == len(team) and all(A[o]['arbiter'] == 'none_team_authored' for o in team if o in A),
   'works with team authorship: %d, all without arbiter' % n_t)
ok(abs(n_o - n_a) <= 1 and n_o + n_a + n_t == 22203, 'arbiters: reviewer_3 %d, reviewer_4 %d' % (n_o, n_a))
ok(not any({'reviewer_1', 'reviewer_2'} & a for a in team.values()), 'no reader is an author of a team work')
h = hashlib.sha256(open(MOD, 'rb').read()).hexdigest()
ok(h == MOD_SHA, 'model input unchanged with respect to the earlier manifest (sha256 %s)' % h)
M = [json.loads(l) for l in open(MOD, encoding='utf-8')]
ok({m['work'] for m in M} == set(A), 'model input with the same 22203 works of the frame')
L.insert(0, 'Independent verification of screening with two readers (phase 4). Failures: %d.' % len(failures))
with open(OUT, 'x', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')
print('\n'.join(L))
sys.exit(1 if failures else 0)
