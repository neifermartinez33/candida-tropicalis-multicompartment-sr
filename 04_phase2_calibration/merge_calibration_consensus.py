# -*- coding: utf-8 -*-
"""Final title and abstract decision for the works of a calibration round.

Usage, from the project root:
  python3 -I -B 04_phase2_calibration/merge_calibration_consensus.py ROUND CONSENSUS_XLSX [--out DIR]
ROUND: CAL1.
CONSENSUS_XLSX: consensus workbook (sheet "Consensus"), for example
  04_phase2_calibration/results/calibration_CAL1_consensus_adjusted.xlsx

Joins the works on which the two readers agree (results/calibration_ROUND_decisions.csv) with the
consensus decision on the discrepancies. "Full text" (no agreement) goes to full text
as an inclusion. Writes in DIR (by default 04_phase2_calibration/results), without overwriting:
  calibration_ROUND_final_decisions.csv       one row per work with its final decision and its route
  calibration_ROUND_final_summary_<date>.txt  counts and hashes of the inputs
"""
import csv, datetime, hashlib, os, sys
from openpyxl import load_workbook

D = '04_phase2_calibration'
VALIDAS = ('Include', 'Exclude', 'Full text')
VALID_EC = {'EC1', 'EC2', 'EC3', 'EC4', 'EC6', 'EC7', 'EC8', 'EC9', 'EC10', 'EC11', 'EC13'}


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


def leave(msg):
    sys.exit('ERROR: ' + msg)


def txt(v):
    return '' if v is None else str(v).strip()


args = list(sys.argv[1:])
out = D + '/results'
if '--out' in args:
    k = args.index('--out'); out = args[k + 1]; del args[k:k + 2]
if len(args) != 2 or args[0] != 'CAL1':
    sys.exit(__doc__)
ronda, xlsx = args
dec_csv = os.path.join(D, 'results', 'calibration_%s_decisions.csv' % ronda)

rows = list(csv.DictReader(open(dec_csv, encoding='utf-8-sig')))
lect = [c[len('decision_'):] for c in rows[0] if c.startswith('decision_') and c != 'decision_final']
if len(lect) != 2:
    leave('the two readers cannot be identified in %s' % dec_csv)
disc = {f['work'] for f in rows if f['agreement'] == 'no'}

ws = load_workbook(xlsx, data_only=True)['Consensus']
hdr = [txt(c.value) for c in ws[1]]
cons = {}
for row in ws.iter_rows(min_row=2, values_only=True):
    d = dict(zip(hdr, row))
    if not txt(d.get('work')):
        continue
    o, dc, ec, note = txt(d['work']), txt(d['consensus_decision']), txt(d['EC_code']), txt(d['note'])
    if dc not in VALIDAS:
        leave('%s: invalid consensus_decision: %r' % (o, dc))
    if dc == 'Exclude' and ec not in VALID_EC:
        leave('%s: excluded without a valid EC code (%r)' % (o, ec))
    if dc != 'Exclude' and ec:
        leave('%s: has an EC code without being an exclusion' % o)
    if not note:
        leave('%s: the note is missing' % o)
    if o in cons:
        leave('%s: repeated in the consensus' % o)
    cons[o] = (dc, ec, note, txt(d.get('adjustment')))
if set(cons) != disc:
    leave('the consensus does not cover exactly the discrepancies: missing %s, in excess %s'
          % (sorted(disc - set(cons)), sorted(set(cons) - disc)))

now, zone = now_co()
final_csv = os.path.join(out, 'calibration_%s_final_decisions.csv' % ronda)
abstract = os.path.join(out, 'calibration_%s_final_summary_%s.txt' % (ronda, now.strftime('%Y%m%d_%H%M%S')))
for p in (final_csv, abstract):
    if os.path.exists(p):
        leave('%s already exists; it is not overwritten' % p)

cont = {}
with open(final_csv, 'x', encoding='utf-8-sig', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['order', 'work', 'title', 'year', 'decision_' + lect[0], 'decision_' + lect[1],
                'decision_final', 'via', 'EC_code', 'note', 'adjustment'])
    for f in sorted(rows, key=lambda f: int(f['order'])):
        o = f['work']
        if f['agreement'] == 'yes':
            df, via, ec, note, aj = f['decision_final'], 'match', '', '', ''
        else:
            dc, ec, note, aj = cons[o]
            df, via = ('Include', 'no consensus, goes to full text') if dc == 'Full text' else (dc, 'consensus')
        if df not in ('Include', 'Exclude'):
            leave('%s: invalid final decision %r' % (o, df))
        cont[(df, via)] = cont.get((df, via), 0) + 1
        w.writerow([f['order'], o, f['title'], f['year'], f['decision_' + lect[0]], f['decision_' + lect[1]],
                    df, via, ec, note, aj])

n_inc = sum(v for (df, _), v in cont.items() if df == 'Include')
n_exc = sum(v for (df, _), v in cont.items() if df == 'Exclude')
fits = sum(1 for v in cons.values() if v[3])
inf = ['Final title and abstract decision, calibration round %s. %s, %s.' % (ronda, now.strftime('%Y-%m-%d %H:%M'), zone),
       '',
       'Inputs (sha256):',
       '  %s  %s' % (sha256(dec_csv), dec_csv),
       '  %s  %s' % (sha256(xlsx), xlsx),
       '',
       'Works: %d. Go to full text: %d. Excluded: %d.' % (len(rows), n_inc, n_exc)]
for (df, via), v in sorted(cont.items()):
    inf.append('  %s by %s: %d' % (df, via, v))
inf += ['Consensus rows with a documented adjustment: %d.' % fits,
        '', 'Output: %s' % final_csv]
with open(abstract, 'x', encoding='utf-8') as fh:
    fh.write('\n'.join(inf) + '\n')
print('\n'.join(inf))
print('Resumen:', abstract)
