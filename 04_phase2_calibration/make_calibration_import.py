# -*- coding: utf-8 -*-
"""Generates the calibration import file (round 1) with the SCREEN_ID note, in the order
of the sample. It does not modify the drawn sample: it writes a derived file. Does not overwrite.

Usage, from the project root:
  python3 -I -B 04_phase2_calibration/make_calibration_import.py
"""
import csv, os, sys

BASE = '04_phase2_calibration/calibration_sample_200_seed13102026'
OUT = BASE + '_import.ris'
if os.path.exists(OUT):
    sys.exit('STOP: %s already exists; it is not overwritten.' % OUT)
blocks, cur = {}, []
for line in open(BASE + '.ris', encoding='utf-8'):
    if not cur and not line.startswith('TY  -'):
        continue
    cur.append(line)
    if line.startswith('ER  -'):
        an = next(l[6:].strip() for l in cur if l.startswith('AN  -'))
        blocks[an] = cur
        cur = []
sample = list(csv.DictReader(open(BASE + '.csv', encoding='utf-8')))
assert len(sample) == 200 and {r['record_id'] for r in sample} == set(blocks)
with open(OUT, 'x', encoding='utf-8', newline='\n') as fh:
    for r in sorted(sample, key=lambda r: int(r['order'])):
        body = [l for l in blocks[r['record_id']] if not l.startswith('ER  -')]
        fh.write(''.join(body).rstrip('\n') + '\n')
        fh.write('N1  - SCREEN_ID %s\n' % r['work'])
        fh.write('ER  - \n\n')
print('written', OUT)
