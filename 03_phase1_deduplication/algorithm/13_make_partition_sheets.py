# -*- coding: utf-8 -*-
"""Builds the partition sheets of the groups in conflict by chaining.

  python3 -I -B algorithm/13_make_partition_sheets.py reviewer_2 reviewer_1

Reads work/chain_conflict_groups.csv, written by 12. Writes:
  work/chain_partition_blind.csv     one record per row, with a code and without identifiers
  work/chain_partition_key.csv       code and record_id; only 14 opens it at closure
  work/chain_partition_<reviewer>.xlsx
Each reviewer assigns each record a work letter within its group. The sheet
shows no previous decisions, neither of the algorithm, nor of the model, nor of the reviewers. The
order of the records within each group is random, with a declared seed.
Does not overwrite.
"""
import csv, os, sys, pickle, random
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

if len(sys.argv) < 3:
    sys.exit("usage: python3 -I -B algorithm/13_make_partition_sheets.py <reviewer> <reviewer>")
REVIEWERS = sys.argv[1:]
SEED = 20261013
LETTERS = "ABCDEFGHIJKLMNOP"
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(os.path.dirname(HERE), 'work')
GROUPS = os.path.join(WORK, 'chain_conflict_groups.csv')
BLIND = os.path.join(WORK, 'chain_partition_blind.csv')
KEY = os.path.join(WORK, 'chain_partition_key.csv')
SHEETS = [os.path.join(WORK, 'chain_partition_%s.xlsx' % r) for r in REVIEWERS]
ya = [os.path.basename(p) for p in [BLIND, KEY] + SHEETS if os.path.exists(p)]
if ya:
    sys.exit("STOP: %s already exist; they are not overwritten." % ", ".join(ya))

R = pickle.load(open(os.path.join(WORK, 'records.pkl'), 'rb'))
N = pickle.load(open(os.path.join(WORK, 'records_not_incorporated.pkl'), 'rb'))
groups = {}
for r in csv.DictReader(open(GROUPS, newline='', encoding='utf-8')):
    groups.setdefault(r['group'], []).append(r['record_id'])
if max(len(v) for v in groups.values()) > len(LETTERS):
    sys.exit("STOP: there is a group with more records than available letters.")

def fields(rid):
    r = R.get(rid) or N[rid]
    au = r.get('authors') or []
    return {'title': (r.get('title') or '')[:300], 'authors': '; '.join(au[:5]) + (' et al.' if len(au) > 5 else ''),
            'year': r.get('year', ''), 'journal': r.get('journal', ''), 'vol': r.get('vol', ''),
            'num': r.get('issue', ''), 'pag': r.get('sp', ''), 'doi': '; '.join(r.get('dois', [])),
            'type': r.get('type', ''), 'issn': r.get('issn', '')}
FIELDS = [('title', 'Title', 70), ('authors', 'Authors', 42), ('year', 'Anio', 7), ('journal', 'Journal', 24),
          ('vol', 'Vol', 7), ('num', 'Num', 7), ('pag', 'Pag', 11), ('doi', 'DOI', 30), ('type', 'Type', 8),
          ('issn', 'ISSN', 13)]
IZQ = [('Group', 7), ('Code', 10), ('WORK', 8), ('Reviewer', 11), ('Date', 11), ('Note', 30)]

rnd = random.Random(SEED)
rows, key = [], []
for g in sorted(groups):
    ids = sorted(groups[g])
    rnd.shuffle(ids)
    for i, rid in enumerate(ids, 1):
        cod = "%s-%02d" % (g, i)
        rows.append(dict(group=g, code=cod, **fields(rid)))
        key.append({'code': cod, 'record_id': rid})

with open(BLIND, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
with open(KEY, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=['code', 'record_id']); w.writeheader(); w.writerows(key)

LEEME = [
    "Partition sheet of chained groups. Phase 1, deduplication of the Candida tropicalis review.",
    "",
    "What each group is. Records that the automatic procedure joined as a single work through successive links. Each group contains records that should not be together.",
    "",
    "What to do. In the WORK column, assign the same letter to the records that are the same published document, according to the pair adjudication manual (model/pair_adjudication_manual.txt), and different letters to different works.",
    "Letters are only valid within their group: the A of group G01 has no relation to the A of group G02.",
    "Every record gets a letter, from A to P.",
    "If you cannot decide which work a record belongs to, give it its own letter and write doubt in the Note. It is kept separate and its overlap is resolved at full text (EC12).",
    "Reading is independent: do not consult the other reviewer's sheet or earlier decisions.",
    "No other column, the order of the rows or the name of the partition sheet is modified.",
    "",
    "Example with a fictitious group, G00:",
    "  G00-01  Article in journal X, 2003, pp. 96-98               A",
    "  G00-02  The same article retrieved from another database    A",
    "  G00-03  Conference abstract of the same work, p. 379        B",
    "",
    "When finished, save with the same name in work. The closure is run with 14_close_partition.py, which reads this sheet directly.",
]
thin, thick = Side(style='thin', color='999999'), Side(style='medium', color='000000')
for rev, path in zip(REVIEWERS, SHEETS):
    wb = Workbook(); ws = wb.active; ws.title = 'partition'
    cab = [t for t, _ in IZQ] + [t for _, t, _ in FIELDS]
    ws.append(cab)
    for c in range(1, len(cab) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(name='Arial', size=10, bold=True, color='000000')
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = Border(bottom=thick, top=thin, left=thin, right=thin)
    for k, f in enumerate(rows):
        ws.append([f['group'], f['code'], '', rev, '', ''] + [f[c] for c, _, _ in FIELDS])
        last = k + 1 == len(rows) or rows[k + 1]['group'] != f['group']
        for c in range(1, len(cab) + 1):
            cell = ws.cell(row=k + 2, column=c)
            cell.font = Font(name='Arial', size=10, color='000000')
            cell.alignment = Alignment(vertical='top', wrap_text=(c > len(IZQ)))
            cell.border = Border(bottom=thick if last else thin, top=thin, left=thin, right=thin)
    dv = DataValidation(type='list', formula1='"%s"' % ",".join(LETTERS), allow_blank=True, showDropDown=False)
    dv.error, dv.errorTitle = 'Only a letter from A to P is admitted', 'Value not admitted'
    ws.add_data_validation(dv)
    dv.add('C2:C%d' % (len(rows) + 1))
    for i, (_, wdt) in enumerate(IZQ, 1):
        ws.column_dimensions[get_column_letter(i)].width = wdt
    for i, (_, _, wdt) in enumerate(FIELDS, len(IZQ) + 1):
        ws.column_dimensions[get_column_letter(i)].width = wdt
    ws.freeze_panes = 'G2'
    ws.row_dimensions[1].height = 26
    le = wb.create_sheet('leeme')
    for line in LEEME:
        le.append([line])
    for row in le.iter_rows():
        for cell in row:
            cell.font = Font(name='Courier New' if cell.value and cell.value.startswith('  G00') else 'Arial',
                             size=10, color='000000')
    le.column_dimensions['A'].width = 150
    wb.active = 0
    wb.save(path)
    print("written %s" % os.path.basename(path))
print("groups: %d   records: %d   seed: %d" % (len(groups), len(rows), SEED))
