#!/usr/bin/env python3
"""Phase 1, step 3: draw the stratified development set (300 pairs).

Sampling is stratified by the number of blocking keys supporting each pair:
75 pairs from each of the four support levels. Seed is declared and deposited.
Section 5.6 of the phase document, version 3, fixed this before the draw.

Writes: adjudication/development_set_300_2026-09-28.csv   (and .xlsx)
        work/development_set_sampling.txt
"""
import os, pickle, random, csv, collections

SEED = 424242
N_PER_STRATUM = 75
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
WORK = os.path.join(ROOT, '03_phase1_deduplication', 'work')
OUT  = os.path.join(ROOT, '03_phase1_deduplication', 'adjudication')
os.makedirs(OUT, exist_ok=True)

recs  = pickle.load(open(os.path.join(WORK, 'records.pkl'), 'rb'))
pairs = pickle.load(open(os.path.join(WORK, 'pairs.pkl'), 'rb'))

strata = collections.defaultdict(list)
for pr, keys in pairs.items():
    strata[len(keys)].append((pr, keys))
for k in strata:
    strata[k].sort()                      # deterministic order before sampling

rng = random.Random(SEED)
sample, lines = [], []
def rep(s=''):
    print(s, flush=True); lines.append(s)

rep('=' * 78)
rep('PHASE 1 - STEP 3: stratified development set')
rep('seed = %d   target = %d pairs per stratum' % (SEED, N_PER_STRATUM))
rep('=' * 78)
rep()
rep('%-10s %10s %10s %14s' % ('stratum', 'population', 'sampled', 'fraction'))
for k in sorted(strata):
    pop = strata[k]
    take = min(N_PER_STRATUM, len(pop))
    chosen = rng.sample(pop, take)
    sample.extend(chosen)
    rep('%-10s %10d %10d %13.4f%%' % ('%d key(s)' % k, len(pop), take, 100 * take / len(pop)))
rep()
rep('total sampled: %d' % len(sample))
rep()
rep('Inverse sampling weights, for estimating the duplicate rate of the whole')
rep('candidate space from this stratified sample:')
for k in sorted(strata):
    pop = strata[k]; take = min(N_PER_STRATUM, len(pop))
    rep('  %d key(s): weight = %.4f  (%d / %d)' % (k, len(pop) / take, len(pop), take))

def rec(rid):
    r = recs.get(rid, {})
    au = r.get('authors', [])
    return {
        'id': rid, 'title': r.get('title', ''),
        'authors': '; '.join(au[:3]) + (' et al.' if len(au) > 3 else ''),
        'year': r.get('year', ''), 'journal': r.get('journal', ''),
        'vol': r.get('vol', ''), 'pages': r.get('sp', ''),
        'doi': '; '.join(r.get('dois', [])), 'type': r.get('type', ''),
    }

COLS = ['pair_id', 'keys', 'label', 'notes',
        'title_1', 'title_2', 'authors_1', 'authors_2', 'year_1', 'year_2',
        'journal_1', 'journal_2', 'vol_1', 'vol_2', 'pages_1', 'pages_2',
        'doi_1', 'doi_2', 'type_1', 'type_2', 'id_1', 'id_2']

rows = []
for n, ((a, b), keys) in enumerate(sorted(sample), 1):
    ra, rb = rec(a), rec(b)
    row = {'pair_id': 'P%04d' % n, 'keys': keys, 'label': '', 'notes': ''}
    for f in ('title', 'authors', 'year', 'journal', 'vol', 'pages', 'doi', 'type', 'id'):
        row[f + '_1'] = ra[f]; row[f + '_2'] = rb[f]
    rows.append(row)

csv_path = os.path.join(OUT, 'development_set_300_2026-09-28.csv')
with open(csv_path, 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader(); w.writerows(rows)
rep('\nCSV written: %s' % csv_path)

try:
    from openpyxl import Workbook
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.styles import Font, Alignment
    wb = Workbook(); ws = wb.active; ws.title = 'development_set'
    ws.append(COLS)
    for c in ws[1]: c.font = Font(bold=True); c.alignment = Alignment(vertical='top')
    for r in rows: ws.append([r[c] for c in COLS])
    dv = DataValidation(type='list', formula1='"DUPLICATE,DIFFERENT,UNDECIDABLE"', allow_blank=True)
    ws.add_data_validation(dv); dv.add('C2:C%d' % (len(rows) + 1))
    ws.freeze_panes = 'E2'
    widths = {'A': 9, 'B': 7, 'C': 14, 'D': 24, 'E': 60, 'F': 60, 'G': 30, 'H': 30}
    for k, v in widths.items(): ws.column_dimensions[k].width = v
    for col in ('I','J','K','L','M','N','O','P','Q','R','S','T','U','V'):
        ws.column_dimensions[col].width = 16
    for row in ws.iter_rows(min_row=2):
        for c in row: c.alignment = Alignment(vertical='top', wrap_text=True)
    xlsx_path = os.path.join(OUT, 'development_set_300_2026-09-28.xlsx')
    wb.save(xlsx_path); rep('XLSX written: %s' % xlsx_path)
except Exception as e:
    rep('XLSX not written: %s' % e)

open(os.path.join(WORK, 'development_set_sampling.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
