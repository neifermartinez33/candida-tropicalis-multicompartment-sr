# -*- coding: utf-8 -*-
"""Prepares title and abstract screening with two readers (phase 4): reading order, arbiter
assigned per work, RIS import file and check of the model input.

Usage, from the project root:
  python3 -I -B 06_phase4_title_abstract_screening/prepare_two_reader_screening.py [--dry]
Applies the section "Change of design ... two readers" of screening_plan_2026-10-13.md:
seed 1310202643 for the reading order and the arbiters. The model input (seed
1310202642) is not rewritten: it is reproduced and checked to be identical byte for byte.
Does not overwrite. With --dry it computes and shows the report without writing anything.
"""
import csv, datetime, hashlib, json, os, random, re, sys

SEED, MODEL_SEED = 1310202643, 1310202642
RIS = '03_phase1_deduplication/results/screening_corpus_phase1_n22403_2026-10-13.ris'
CLU = '03_phase1_deduplication/work/corpus_clusters.csv'
CAL = ['04_phase2_calibration/calibration_sample_200_seed13102026.csv']
D = '06_phase4_title_abstract_screening'
PLAN = D + '/screening_plan_2026-10-13.md'
TEAM = D + '/allocation/team_authored_records.csv'
MODEL = D + '/model/model_input_n22203_seed1310202642.jsonl'
READERS = ('reviewer_1', 'reviewer_2')
NO_ARB = 'none_team_authored'
DRY = '--dry' in sys.argv

def now_co():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo('America/Bogota')), 'Colombia time'
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc), 'UTC'

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for ch in iter(lambda: fh.read(1 << 20), b''):
            h.update(ch)
    return h.hexdigest()

TAG = re.compile(r'^([A-Z][A-Z0-9])  -( |$)')
def fields(lines):
    d, ult = {}, None
    for l in lines:
        s = l.rstrip('\n')
        m = TAG.match(s)
        if m:
            ult = m.group(1)
            d.setdefault(ult, []).append(s[6:].strip())
        elif s.strip() and ult:
            d[ult][-1] = (d[ult][-1] + ' ' + s.strip()).strip()
    return d

# 1. Inputs
blocks, cur = {}, []
for line in open(RIS, encoding='utf-8'):
    if not cur and not line.startswith('TY  -'):
        continue
    cur.append(line)
    if line.startswith('ER  -'):
        an = next(l[6:].strip() for l in cur if l.startswith('AN  -'))
        assert an not in blocks, 'repeated AN: %s' % an
        blocks[an] = cur
        cur = []
rep = {r['work']: r['record_id'] for r in csv.DictReader(open(CLU, encoding='utf-8'))
       if r['representative'] == 'yes'}
assert len(rep) == 22403 and set(rep.values()) == set(blocks), 'the RIS does not match the representatives'
cal = set()
for f in CAL:
    cal |= {r['work'] for r in csv.DictReader(open(f, encoding='utf-8'))}
assert len(cal) == 200 * len(CAL) and cal <= set(rep)
frame = sorted(o for o in rep if o not in cal)
team = {r['work']: r for r in csv.DictReader(open(TEAM, encoding='utf-8'))}
assert set(team) <= set(rep)
team_frame = {o: r for o, r in team.items() if o not in cal}
n = len(frame)

# 2. Reading order and arbiters (a single generator, in the order declared in the plan)
rng = random.Random(SEED)
order_list = frame[:]
rng.shuffle(order_list)
order = {o: k for k, o in enumerate(order_list, 1)}
without_team = sorted(o for o in frame if o not in team_frame)
half = len(without_team) // 2
arbiter_reviewer_3 = set(rng.sample(without_team, half))
arbiter = {o: (NO_ARB if o in team_frame else ('reviewer_3' if o in arbiter_reviewer_3 else 'reviewer_4')) for o in frame}

# 3. Checks
assert n == 22203 and len(order) == n and sorted(order.values()) == list(range(1, n + 1))
assert sum(1 for v in arbiter.values() if v == 'reviewer_3') == half
assert sum(1 for v in arbiter.values() if v == 'reviewer_4') == len(without_team) - half
for o, r in team_frame.items():
    authors = set(r['team_authors'].split(';'))
    assert arbiter[o] == NO_ARB and not set(READERS) & authors

# 4. The model input is reproduced with the logic of the earlier allocation and compared
rng2 = random.Random(MODEL_SEED)
model = frame[:]
rng2.shuffle(model)
h = hashlib.sha256()
for k, o in enumerate(model, 1):
    d = fields(blocks[rep[o]])
    rec = {'model_order': k, 'work': o, 'record_id': rep[o],
           'title': ' '.join(d.get('TI', [])),
           'other_titles': d.get('TT', []),
           'abstract': '\n\n'.join(x for x in d.get('AB', []) if x),
           'keywords': list(dict.fromkeys(d.get('KW', []) + d.get('MH', []))),
           'journal': next((d[t][0] for t in ('T2', 'JO', 'J2') if d.get(t)), ''),
           'year': next((x[:4] for t in ('PY', 'Y1') for x in d.get(t, []) if x[:4].isdigit()), ''),
           'authors': d.get('AU', []),
           'language': d.get('LA', []),
           'doi': (d.get('DO') or [''])[0]}
    h.update((json.dumps(rec, ensure_ascii=False) + '\n').encode('utf-8'))
h_model, h_file = h.hexdigest(), sha(MODEL)
assert h_model == h_file, 'the model input is not reproduced: %s versus %s' % (h_model, h_file)

# 5. Report and outputs
p_imp = '%s/import/screening_reviewer_1_reviewer_2_n%d_seed%d.ris' % (D, n, SEED)
p_csv = '%s/allocation/two_reader_order_and_arbiters_seed%d.csv' % (D, SEED)
p_rep = '%s/allocation/two_reader_report_2026-10-14.txt' % D
p_man = '%s/manifest_two_readers_2026-10-14.txt' % D
outputs = [p_imp, p_csv, p_rep, p_man]
_t, _z = now_co()
now = '%s, %s' % (_t.strftime('%Y-%m-%d %H:%M'), _z)
def with_abstract(obs):
    return 100.0 * sum(1 for o in obs if ''.join(fields(blocks[rep[o]]).get('AB', [])).strip()) / len(obs)
inf = ['Preparation of screening with two readers (phase 4). Run: %s.' % now,
       'Plan applied: %s (sha256 when run: %s)' % (PLAN, sha(PLAN)),
       'Seed of the reading order and of the arbiters: %d. Seed of the model order: %d.' % (SEED, MODEL_SEED),
       '',
       'Works in the corpus: %d. Calibration removed: %d. Frame: %d.' % (len(rep), len(cal), n),
       'Readers: %s and %s, the %d works each, in the same order.' % (READERS[0], READERS[1], n),
       'Arbiter reviewer_3: %d works (%.1f %% with abstract). Arbiter reviewer_4: %d works (%.1f %% with abstract). Without arbiter (team authorship): %d.'
       % (half, with_abstract([o for o in frame if arbiter[o] == 'reviewer_3']),
          len(without_team) - half, with_abstract([o for o in frame if arbiter[o] == 'reviewer_4']), len(team_frame)),
       'Model input reproduced byte for byte: %s (sha256 %s).' % (h_model == h_file, h_file),
       '']
for o in sorted(team_frame):
    inf.append('Team authorship: %s (%s; authors %s), position %d; without arbiter: tie or network go to full text.'
               % (o, team_frame[o]['record_id'], team_frame[o]['team_authors'], order[o]))
inf.append('')
inf.append('Inputs (sha256):')
for p in [RIS, CLU, TEAM] + CAL:
    inf.append('  %s  %s' % (sha(p), p))

if DRY:
    print('\n'.join(inf))
    print('\n[--dry] nothing was written. Planned outputs:')
    print('\n'.join('  ' + s for s in outputs))
    sys.exit(0)
ya = [p for p in outputs if os.path.exists(p)]
if ya:
    sys.exit('STOP: outputs already exist; nothing is overwritten:\n' + '\n'.join(ya))
with open(p_csv, 'x', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['work', 'record_id', 'order', 'reader_1', 'reader_2', 'arbiter', 'team_authored', 'team_authors'])
    for o in order_list:
        t = o in team_frame
        w.writerow([o, rep[o], order[o], READERS[0], READERS[1], arbiter[o],
                    'yes' if t else 'no', team_frame[o]['team_authors'] if t else ''])
with open(p_imp, 'x', encoding='utf-8', newline='\n') as fh:
    for o in order_list:
        body = [l for l in blocks[rep[o]] if not l.startswith('ER  -')]
        fh.write(''.join(body).rstrip('\n') + '\n')
        fh.write('N1  - SCREEN_ID %s\n' % o)
        fh.write('ER  - \n\n')
with open(p_rep, 'x', encoding='utf-8') as fh:
    fh.write('\n'.join(inf) + '\n')
with open(p_man, 'x', encoding='utf-8') as fh:
    fh.write('Manifest of the preparation of screening with two readers (phase 4). %s.\n' % now)
    for p in [p_imp, p_csv, p_rep, MODEL]:
        fh.write('%s  %s\n' % (sha(p), p))
print('\n'.join(inf))
print('\nEscritos:')
print('\n'.join('  ' + s for s in outputs))
