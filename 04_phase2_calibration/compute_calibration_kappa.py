# -*- coding: utf-8 -*-
"""Cohen's kappa of a calibration round and lists for the consensus session.

Usage, from the project root:
  python3 -I -B 04_phase2_calibration/compute_calibration_kappa.py ROUND COD1=EXPORT1 COD2=EXPORT2 [--out DIR]
ROUND: CAL1 (sample of 200, seed 13102026).
CODn=EXPORTn: reader code and its Rayyan export in RIS, made with blind mode on
(each file carries only the decisions of its reader), for example
  reviewer_2=04_phase2_calibration/rayyan_exports/02_decisions_reviewer_2_blind_on.ris

Each work is identified by the SCREEN_ID note. "Maybe" counts as inclusion (rule 1 of the plan).
Writes in DIR (by default 04_phase2_calibration/results), without overwriting:
  calibration_kappa_ROUND_<date>.txt       report with the table, the kappa and its 95 % CI, and the input hashes
  calibration_ROUND_decisions.csv          the works of the sample with the decision of each reader and,
                                           when they agree, the final decision
  calibration_ROUND_discrepancies.csv      only the discrepancies, with title and abstract, for the consensus
95 % CI: asymptotic standard error of Fleiss, Cohen and Everitt (1969).
"""
import csv, datetime, hashlib, math, os, re, sys

D = '04_phase2_calibration'
RONDAS = {'CAL1': (D + '/calibration_sample_200_seed13102026.csv',
                   D + '/calibration_sample_200_seed13102026_import.ris')}


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def now_co():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo('America/Bogota')), 'Colombia time'
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc), 'UTC'


def records(p):
    out, cur = [], []
    with open(p, encoding='utf-8-sig', errors='replace') as fh:
        for l in fh:
            cur.append(l)
            if l.startswith('ER  -'):
                out.append(''.join(cur)); cur = []
    if ''.join(cur).strip():
        out.append(''.join(cur))
    return out


def field(t, *tags):
    for tag in tags:
        v = re.findall(r'^%s  - (.*)$' % tag, t, re.M)
        if v:
            return ' '.join(x.strip() for x in v)
    return ''


def leave(msg):
    sys.exit('ERROR: ' + msg)


args = list(sys.argv[1:])
out = D + '/results'
if '--out' in args:
    k = args.index('--out'); out = args[k + 1]; del args[k:k + 2]
if len(args) != 3 or args[0] not in RONDAS or not all('=' in a for a in args[1:]):
    sys.exit(__doc__)
ronda = args[0]
readers = [tuple(a.split('=', 1)) for a in args[1:]]
if readers[0][0] == readers[1][0]:
    leave('the two readers have the same code')
sample_csv, import_ris = RONDAS[ronda]

sample = list(csv.DictReader(open(sample_csv, encoding='utf-8')))
order = {r['work']: int(r['order']) for r in sample}
info = {}
for t in records(import_ris):
    m = re.search(r'SCREEN_ID\s+(O\d{5})', t)
    if m:
        info[m.group(1)] = {'title': field(t, 'TI', 'T1'), 'year': field(t, 'PY', 'Y1')[:4],
                            'journal': field(t, 'T2', 'JO', 'JF', 'J2'), 'doi': field(t, 'DO'),
                            'abstract': field(t, 'AB')}
if set(info) != set(order):
    leave('the import file does not match the sample')

decs, names = {}, {}
for cod, p in readers:
    d, ns = {}, set()
    for t in records(p):
        m = re.search(r'SCREEN_ID\s+(O\d{5})', t)
        if not m:
            leave('%s: record without SCREEN_ID' % p)
        inc = re.search(r'RAYYAN-INCLUSION: \{(.*?)\}', t)
        pairs = re.findall(r'"([^"]+)"=>"([^"]+)"', inc.group(1)) if inc else []
        if len(pairs) != 1:
            leave('%s: work %s does not carry exactly one decision (%d); the export must be made with blind mode on' % (p, m.group(1), len(pairs)))
        ns.add(pairs[0][0])
        v = pairs[0][1].lower()
        if v not in ('included', 'excluded', 'maybe'):
            leave('%s: unknown decision %r in %s' % (p, pairs[0][1], m.group(1)))
        if m.group(1) in d:
            leave('%s: repeated work %s' % (p, m.group(1)))
        d[m.group(1)] = 'Include' if v in ('included', 'maybe') else 'Exclude'
    if len(ns) != 1:
        leave('%s: carries decisions of more than one reader: %s' % (p, sorted(ns)))
    if set(d) != set(order):
        leave('%s: %d works missing and %d in excess' % (p, len(set(order) - set(d)), len(set(d) - set(order))))
    decs[cod], names[cod] = d, ns.pop()

(c1, p1), (c2, p2) = readers
A, B = decs[c1], decs[c2]
works = sorted(order, key=order.get)
n = len(works)
a = sum(A[o] == 'Include' and B[o] == 'Include' for o in works)
b = sum(A[o] == 'Include' and B[o] == 'Exclude' for o in works)
c = sum(A[o] == 'Exclude' and B[o] == 'Include' for o in works)
d = sum(A[o] == 'Exclude' and B[o] == 'Exclude' for o in works)
po = (a + d) / n
pa, pb = (a + b) / n, (a + c) / n
pe = pa * pb + (1 - pa) * (1 - pb)
kappa = (po - pe) / (1 - pe)
p = [[a / n, b / n], [c / n, d / n]]
row, col = [pa, 1 - pa], [pb, 1 - pb]
t1 = sum(p[i][i] * (1 - (row[i] + col[i]) * (1 - kappa)) ** 2 for i in range(2))
t2 = (1 - kappa) ** 2 * sum(p[i][j] * (col[i] + row[j]) ** 2 for i in range(2) for j in range(2) if i != j)
t3 = (kappa - pe * (1 - kappa)) ** 2
se = math.sqrt(max(t1 + t2 - t3, 0) / n) / (1 - pe)
li, ls = kappa - 1.96 * se, kappa + 1.96 * se

os.makedirs(out, exist_ok=True)
now, zone = now_co()
destinations = {
    'report': os.path.join(out, 'calibration_kappa_%s_%s.txt' % (ronda, now.strftime('%Y%m%d_%H%M%S'))),
    'decisions': os.path.join(out, 'calibration_%s_decisions.csv' % ronda),
    'discrepancies': os.path.join(out, 'calibration_%s_discrepancies.csv' % ronda)}
for p_ in destinations.values():
    if os.path.exists(p_):
        leave('%s already exists; it is not overwritten' % p_)

with open(destinations['decisions'], 'x', encoding='utf-8-sig', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['order', 'work', 'title', 'year', 'decision_' + c1, 'decision_' + c2, 'agreement',
                'decision_final', 'EC_code', 'note'])
    for o in works:
        ac = A[o] == B[o]
        w.writerow([order[o], o, info[o]['title'], info[o]['year'], A[o], B[o], 'yes' if ac else 'no',
                    A[o] if ac else '', '', ''])
disc = [o for o in works if A[o] != B[o]]
with open(destinations['discrepancies'], 'x', encoding='utf-8-sig', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['order', 'work', 'title', 'year', 'journal', 'doi', 'abstract', 'decision_' + c1,
                'decision_' + c2, 'consensus_decision', 'EC_code', 'note'])
    for o in disc:
        i = info[o]
        w.writerow([order[o], o, i['title'], i['year'], i['journal'], i['doi'], i['abstract'] or '(no abstract)',
                    A[o], B[o], '', '', ''])

inf = ["Cohen's kappa of the calibration, round %s. %s, %s." % (ronda, now.strftime('%Y-%m-%d %H:%M'), zone),
       '',
       'Inputs (sha256):',
       '  %s  %s' % (sha256(sample_csv), sample_csv),
       '  %s  %s  (reader %s, name in Rayyan: %s)' % (sha256(p1), p1, c1, names[c1]),
       '  %s  %s  (reader %s, name in Rayyan: %s)' % (sha256(p2), p2, c2, names[c2]),
       '',
       'Works: %d. "Maybe" counts as inclusion.' % n,
       '',
       '                    %s includes  %s excludes  total %s' % (c2, c2, c1),
       '  %s includes      %8d     %8d     %8d' % (c1, a, b, a + b),
       '  %s excludes      %8d     %8d     %8d' % (c1, c, d, c + d),
       '  total %s         %8d     %8d     %8d' % (c2, a + c, b + d, n),
       '',
       'Observed agreement: %.3f (%d of %d). Agreement expected by chance: %.3f.' % (po, a + d, n, pe),
       "Cohen's kappa: %.3f. 95 %% CI: %.3f to %.3f (asymptotic standard error of Fleiss, Cohen and Everitt, 1969)." % (kappa, li, ls),
       'Rule of the plan: second round if kappa falls below 0.60.',
       'Discrepancies: %d (%s includes and %s excludes: %d; %s excludes and %s includes: %d).' % (b + c, c1, c2, b, c1, c2, c),
       '',
       'Outputs:',
       '  %s' % destinations['decisions'],
       '  %s' % destinations['discrepancies']]
with open(destinations['report'], 'x', encoding='utf-8') as fh:
    fh.write('\n'.join(inf) + '\n')
print('\n'.join(inf))
print('Report:', destinations['report'])
