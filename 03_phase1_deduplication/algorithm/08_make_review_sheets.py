# -*- coding: utf-8 -*-
"""Builds the reading sheets in xlsx format from a blind sheet.

  python3 algorithm/08_make_review_sheets.py audit_L1_without_doi reviewer_1 reviewer_2

Each pair takes two adjacent rows, one per record, so that title against
title and author against author are aligned vertically and are compared without
scrolling. The judgement columns are on the left and stay frozen when
scrolling. The judgement is chosen from a drop-down list, which avoids typos that
the closure would reject.

It shows no score, nor the verdict of the algorithm, the model or the layer.
"""
import csv, os, sys
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

if len(sys.argv) < 3:
    sys.exit("usage: python3 algorithm/08_make_review_sheets.py <prefix> <reviewer> [<reviewer> ...]")
PREF, REVIEWERS = sys.argv[1], sys.argv[2:]
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(os.path.dirname(HERE), 'work')
SRC = os.path.join(WORK, PREF + '_blind.csv')
if not os.path.exists(SRC):
    sys.exit("ERROR: %s does not exist" % SRC)

rows = list(csv.DictReader(open(SRC, newline='', encoding='utf-8')))
print("pairs in the sheet: %d" % len(rows))

FIELDS = [('title', 'Title', 78), ('authors', 'Authors', 46), ('year', 'Anio', 7),
          ('journal', 'Journal', 26), ('vol', 'Vol', 7), ('num', 'Num', 7),
          ('pag', 'Pag', 11), ('doi', 'DOI', 30), ('type', 'Type', 8), ('issn', 'ISSN', 13)]
IZQ = [('row', 'Row', 6), ('pair_id', 'Par', 10), ('reg', 'Reg', 5),
       ('human_judgement', 'JUDGEMENT', 19), ('reviewer', 'Reviewer', 12),
       ('date', 'Date', 12), ('note', 'Note', 34)]

thin = Side(style='thin', color='999999')
thick = Side(style='medium', color='000000')
gris = PatternFill('solid', fgColor='EFEFEF')

for rev in REVIEWERS:
    wb = Workbook(); ws = wb.active; ws.title = 'auditoria'
    cab = [t for _, t, _ in IZQ] + [t for _, t, _ in FIELDS]
    ws.append(cab)
    for c in range(1, len(cab) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, size=10)
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = Border(bottom=thick, top=thin, left=thin, right=thin)
    ws.freeze_panes = 'H2'
    ws.row_dimensions[1].height = 26

    r = 2
    for f in rows:
        for side in ('a', 'b'):
            vals = [f['row'], f['pair_id'], side.upper(), '', rev if side == 'a' else '', '', '']
            vals += [f.get(side + '_' + k, '') for k, _, _ in FIELDS]
            ws.append(vals)
            for c in range(1, len(vals) + 1):
                cell = ws.cell(row=r, column=c)
                cell.alignment = Alignment(vertical='top', wrap_text=(c > len(IZQ)))
                cell.font = Font(size=10)
                below = thick if side == 'b' else thin
                cell.border = Border(bottom=below, top=thin, left=thin, right=thin)
                if side == 'b': cell.fill = gris
            r += 1

    dv = DataValidation(type='list',
                        formula1='"SAME_WORK,DIFFERENT_WORKS,UNDECIDABLE"',
                        allow_blank=True, showDropDown=False)
    dv.error = 'Only SAME_WORK, DIFFERENT_WORKS or UNDECIDABLE is admitted'
    dv.errorTitle = 'Value not admitted'
    ws.add_data_validation(dv)
    dv.add('D2:D%d' % (r - 1))

    for i, (_, _, w) in enumerate(IZQ + FIELDS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    out = os.path.join(WORK, '%s_%s.xlsx' % (PREF, rev))
    wb.save(out)
    print("  written %s" % os.path.basename(out))

print()
print("The judgement is written ONCE per pair, in row A. Row B stays blank.")
print("When finished, the closure is run with 07_audit_close.py, which reads the xlsx directly.")
