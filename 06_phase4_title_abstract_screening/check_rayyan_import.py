# -*- coding: utf-8 -*-
"""Checks a Rayyan export against what was imported: no missing, surplus or repeated records.
Replaces check_rayyan_block.py (six-block design, without effect since 2026-10-13).

Usage, from the project root:
  python3 -I -B 06_phase4_title_abstract_screening/check_rayyan_import.py REVIEW EXPORT [--out DIR]
REVIEW: CAL1 (calibration, round 1) or S (screening with two readers).
EXPORT: file exported from Rayyan, .ris or .csv.
Each exported record is identified by the SCREEN_ID note or, if Rayyan dropped it, by the AN
(record identifier). The report says which field survived. It is written in import_checks/
(or in DIR) with date and time in the name; does not overwrite.
"""
import csv, datetime, os, re, sys
from collections import Counter

D = '06_phase4_title_abstract_screening'
EXPECTED = {'CAL1': '04_phase2_calibration/calibration_sample_200_seed13102026.csv',
            'S': D + '/allocation/two_reader_order_and_arbiters_seed1310202643.csv'}
csv.field_size_limit(sys.maxsize)

def now_co():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo('America/Bogota')), 'Colombia time'
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc), 'UTC'

args = list(sys.argv[1:])
out = D + '/import_checks'
if '--out' in args:
    k = args.index('--out'); out = args[k + 1]; del args[k:k + 2]
if len(args) != 2 or args[0] not in EXPECTED:
    sys.exit(__doc__)
rev, exp = args
expected = {r['work']: r['record_id'] for r in csv.DictReader(open(EXPECTED[rev], encoding='utf-8'))}
rid2obra = {}
for f in EXPECTED.values():
    if os.path.exists(f):
        rid2obra.update({r['record_id']: r['work'] for r in csv.DictReader(open(f, encoding='utf-8'))})

with open(exp, encoding='utf-8-sig', errors='replace', newline='') as fh:
    if exp.lower().endswith('.csv'):
        rows = [f for f in csv.reader(fh)]
        records = [' | '.join(f) for f in rows[1:] if any(c.strip() for c in f)]
    else:
        records, cur = [], []
        for l in fh:
            cur.append(l)
            if l.startswith('ER  -'):
                records.append(''.join(cur)); cur = []
        if ''.join(cur).strip():
            records.append(''.join(cur))

SID = re.compile(r'SCREEN_ID\s+(O\d{5})')
TOK = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]*[A-Za-z0-9]')
found, without_id, ambiguous = [], [], []
for i, t in enumerate(records, 1):
    s, via = set(SID.findall(t)), 'SCREEN_ID'
    if not s:
        s, via = {rid2obra[x] for x in TOK.findall(t) if x in rid2obra}, 'AN'
    if len(s) == 1:
        found.append((i, s.pop(), via))
    elif not s:
        without_id.append(i)
    else:
        ambiguous.append((i, sorted(s)))
cnt = Counter(o for _, o, _ in found)
repeated = sorted(o for o, c in cnt.items() if c > 1)
faltan = sorted(set(expected) - set(cnt))
sobran = sorted(set(cnt) - set(expected))
vias = Counter(v for _, _, v in found)
closes = not (faltan or sobran or repeated or without_id or ambiguous) and len(records) == len(expected)

now, zone = now_co()
inf = ['Import check. Review %s. %s, %s.' % (rev, now.strftime('%Y-%m-%d %H:%M'), zone),
       'Export: %s' % exp,
       'Expected works: %d. Exported records: %d.' % (len(expected), len(records)),
       'Identified: %d (by SCREEN_ID: %d; by AN: %d).' % (len(found), vias['SCREEN_ID'], vias['AN']),
       'Without identifier: %d. Ambiguous: %d. Repeated: %d. Missing: %d. Surplus: %d.'
       % (len(without_id), len(ambiguous), len(repeated), len(faltan), len(sobran)),
       'Verdict: %s' % ('CLOSES' if closes else 'DOES NOT RECONCILE: no screening until it is resolved')]
for label, items in (('Missing', faltan), ('Surplus', sobran), ('Repeated', repeated),
                        ('Records without identifier (position in the export)', without_id),
                        ('Ambiguous', ambiguous)):
    if items:
        inf.append('%s: %s' % (label, ', '.join(str(x) for x in items[:200])))
os.makedirs(out, exist_ok=True)
base = os.path.join(out, 'import_check_%s_%s' % (rev, now.strftime('%Y%m%d_%H%M%S')))
p, k = base + '.txt', 1
while os.path.exists(p):
    k += 1
    p = '%s_%d.txt' % (base, k)
with open(p, 'x', encoding='utf-8') as fh:
    fh.write('\n'.join(inf) + '\n')
print('\n'.join(inf))
print('Report:', p)
sys.exit(0 if closes else 1)
