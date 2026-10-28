# -*- coding: utf-8 -*-
"""Converts <prefix>_discrepancies.csv into <prefix>_consensus.xlsx to fill in the consensus.

  python3 algorithm/09_make_consensus_sheet.py human_queue_L3_L4

Two rows per pair, record A and record B, as in the review sheets. Row A
carries the judgement and the note of each reviewer. consensus_judgement and
decided_by are filled in row A; note is optional. 07_audit_close.py reads the sheet
'consensus'. It does not overwrite a consensus file that already exists.
"""
import csv, io, os, sys, warnings
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

if len(sys.argv) < 2:
    sys.exit("usage: python3 algorithm/09_make_consensus_sheet.py <prefix>")
PREF = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(os.path.dirname(HERE), 'work')
src = os.path.join(WORK, PREF + '_discrepancies.csv')
dst = os.path.join(WORK, PREF + '_consensus.xlsx')
if not os.path.exists(src):
    sys.exit("ERROR: %s does not exist; run 07_audit_close.py first." % os.path.basename(src))
if os.path.exists(dst):
    sys.exit("ERROR: %s already exists; it is not overwritten." % os.path.basename(dst))

txt = open(src, 'rb').read().decode('utf-8-sig')
for delim in (';', ','):
    rows = list(csv.DictReader(io.StringIO(txt), delimiter=delim))
    if rows and 'pair_id' in rows[0]:
        break
revs = sorted(c[len('judgement_'):] for c in rows[0] if c.startswith('judgement_') and c != 'consensus_judgement')

def notes(rev):
    """Note of row A of each pair in the reviewer's sheet."""
    p = os.path.join(WORK, '%s_%s.xlsx' % (PREF, rev))
    if not os.path.exists(p):
        return {}
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        ws = load_workbook(p, read_only=True).worksheets[0]
    it = ws.iter_rows(values_only=True)
    cab = list(next(it))
    ip, ir, inn = cab.index('Par'), cab.index('Reg'), cab.index('Note')
    return {r[ip]: (r[inn] or '') for r in it if r[ir] == 'A'}
NOTES = {r: notes(r) for r in revs}

FIELDS = ['title', 'authors', 'year', 'journal', 'vol', 'num', 'pag', 'doi', 'type', 'issn']
CAB = (['n', 'sheet_row', 'pair_id', 'reg'] + ['judgement_' + r for r in revs]
       + ['consensus_judgement', 'decided_by', 'note'] + FIELDS + ['note_' + r for r in revs])

wb = Workbook()
ws = wb.active
ws.title = 'consensus'
ws.append(CAB)
for k, r in enumerate(rows, 1):
    for reg, pre in (('A', 'a_'), ('B', 'b_')):
        row = [k, int(r['row']), r['pair_id'], reg]
        row += [r['judgement_' + v] if reg == 'A' else None for v in revs]
        row += [None, None, None]
        row += [(r.get(pre + c) or None) for c in FIELDS]
        row += [(NOTES[v].get(r['pair_id']) or None) if reg == 'A' else None for v in revs]
        ws.append(row)

normal = Font(name='Arial', size=10, color='000000')
bold_font = Font(name='Arial', size=10, bold=True, color='000000')
line = Side(style='medium', color='000000')
for c in ws[1]:
    c.font = bold_font
    c.alignment = Alignment(vertical='center', wrap_text=True)
    c.border = Border(bottom=line)
for row in ws.iter_rows(min_row=2):
    es_b = row[3].value == 'B'
    for c in row:
        c.font = normal
        c.alignment = Alignment(vertical='top', wrap_text=True)
        if es_b:
            c.border = Border(bottom=line)

WIDTH = {'n': 5, 'sheet_row': 8, 'pair_id': 10, 'reg': 4, 'consensus_judgement': 19, 'decided_by': 14,
         'note': 28, 'title': 50, 'authors': 30, 'year': 6, 'journal': 22, 'vol': 6, 'num': 6,
         'pag': 10, 'doi': 26, 'type': 12, 'issn': 12}
for i, h in enumerate(CAB, 1):
    width = WIDTH.get(h, 17 if h.startswith('judgement_') else 45)
    ws.column_dimensions[get_column_letter(i)].width = width
col = {h: get_column_letter(i) for i, h in enumerate(CAB, 1)}
ws.freeze_panes = '%s2' % get_column_letter(CAB.index('note') + 2)

ult = ws.max_row
dv = DataValidation(type='list', formula1='"SAME_WORK,DIFFERENT_WORKS,UNDECIDABLE"', allow_blank=True)
dv.promptTitle = 'Consensus judgement'
dv.prompt = 'Only in row A: SAME_WORK, DIFFERENT_WORKS or UNDECIDABLE.'
dv.errorTitle = 'Value not admitted'
dv.error = 'Use SAME_WORK, DIFFERENT_WORKS or UNDECIDABLE.'
dv.showInputMessage = True
dv.showErrorMessage = True
ws.add_data_validation(dv)
dv.add('%s2:%s%d' % (col['consensus_judgement'], col['consensus_judgement'], ult))
dq = DataValidation(type='list', formula1='"consensus"', allow_blank=True)
dq.promptTitle = 'Decided by'
dq.prompt = 'consensus, or the identifier of whoever decided if there was no agreement.'
dq.showInputMessage = True
dq.showErrorMessage = False
ws.add_data_validation(dq)
dq.add('%s2:%s%d' % (col['decided_by'], col['decided_by'], ult))

ls = wb.create_sheet('leeme')
text = [
    ('Consensus of discrepancies: %s (%d pairs)' % (PREF, len(rows)), None),
    (None, None),
    ('What is filled in', 'Only in the consensus sheet and only in row A of each pair: consensus_judgement and decided_by. The note is optional.'),
    ('consensus_judgement', 'SAME_WORK, DIFFERENT_WORKS or UNDECIDABLE, from the drop-down list.'),
    ('decided_by', '"consensus" if the two reviewers resolved it. If there was no agreement, the identifier of whoever decided, who must not have read the queue.'),
    ('note', 'Brief reason for the decision, if needed.'),
    ('Not modified', 'No other column, the order of the rows or the name of the consensus sheet.'),
    ('When finished', 'Save with the same name in work and run: python3 algorithm/07_audit_close.py %s' % PREF),
    (None, None),
    ('Example of a filled row A', None),
    ('consensus_judgement: SAME_WORK', 'decided_by: consensus   |   note: B is the Spanish version of the same article; authors, volume and pages match.'),
]
for a, b in text:
    ls.append([a, b])
for row in ls.iter_rows():
    for c in row:
        c.font = normal
        c.alignment = Alignment(vertical='top', wrap_text=True)
ls['A1'].font = bold_font
ls['A10'].font = bold_font
ls.column_dimensions['A'].width = 28
ls.column_dimensions['B'].width = 100
wb.active = 0
wb.save(dst)
print('written %s: %d pairs, %d rows, reviewers %s' % (os.path.basename(dst), len(rows), ult - 1, ', '.join(revs)))
