# -*- coding: utf-8 -*-
"""Closes the partition of the groups in conflict by chaining (analogous to 07).

  python3 -I -B algorithm/14_close_partition.py

Reads exactly two sheets work/chain_partition_<reviewer>.xlsx. Each record must have
a letter from A to P. Agreement is measured on the implicit pairs of each group
(same letter or different letter), with raw agreement and Cohen's kappa, and the groups
with an identical partition are counted regardless of the names of the letters.
If there are groups with a different partition, it writes work/chain_partition_consensus.xlsx with the two
partitions side by side and stops until the consensus is complete.
With everything resolved it opens the key and writes work/chain_partition_final.csv and
work/chain_partition_result.txt. Does not overwrite. Exits with 3 if it stops.

Warnings that do not stop the closure: a record with doubt in the note that shares a letter with another
record of its group (the closure joins it to that work). If a reviewer corrected their sheet after
submitting it and the submitted version is in work/_superseded/chain_partition_<reviewer>_submitted_*.xlsx,
agreement is also reported on the sheets as submitted.
"""
import csv, glob, os, sys, itertools, collections, warnings
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(os.path.dirname(HERE), 'work')
PRE = 'chain_partition_'
BLIND, KEY = os.path.join(WORK, PRE + 'blind.csv'), os.path.join(WORK, PRE + 'key.csv')
CONS = os.path.join(WORK, PRE + 'consensus.xlsx')
FINAL, RESUL = os.path.join(WORK, PRE + 'final.csv'), os.path.join(WORK, PRE + 'result.txt')
RESERV = ('blind', 'key', 'consensus', 'final', 'result', 'discrepancies')
LETTERS = "ABCDEFGHIJKLMNOP"
FIELDS = [('title', 'Title', 70), ('authors', 'Authors', 42), ('year', 'Anio', 7), ('journal', 'Journal', 24),
          ('vol', 'Vol', 7), ('num', 'Num', 7), ('pag', 'Pag', 11), ('doi', 'DOI', 30), ('type', 'Type', 8),
          ('issn', 'ISSN', 13)]

out = []
A = out.append
def stop(*lines):
    print("\n".join(out)); print("")
    for l in lines:
        print(l)
    print("The key was NOT opened and the final partition was not written.")
    sys.exit(3)

def text(v):
    return '' if v is None else str(v).strip()

def leer_xlsx(path, sheet, col_letter, col_note):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        wb = load_workbook(path, data_only=True)
    ws = wb[sheet] if sheet in wb.sheetnames else wb.active
    it = ws.iter_rows(values_only=True)
    cab = [text(c) for c in next(it)]
    ic, il = cab.index('Code'), cab.index(col_letter)
    inota = cab.index(col_note) if col_note in cab else None
    iq = cab.index('decided_by') if 'decided_by' in cab else None
    L, NT, Q = {}, {}, {}
    for row in it:
        c = text(row[ic])
        if not c:
            continue
        L[c] = text(row[il]).upper()
        NT[c] = text(row[inota]) if inota is not None else ''
        Q[c] = text(row[iq]) if iq is not None else ''
    return L, NT, Q

ya = [os.path.basename(p) for p in (FINAL, RESUL) if os.path.exists(p)]
if ya:
    stop("STOP: %s already exist; they are not overwritten." % ", ".join(ya))
blind = {r['code']: r for r in csv.DictReader(open(BLIND, newline='', encoding='utf-8'))}
group = {c: r['group'] for c, r in blind.items()}
groups = sorted(set(group.values()))
cods = {g: sorted(c for c in group if group[c] == g) for g in groups}

sheets = sorted(h for h in glob.glob(os.path.join(WORK, PRE + '*.xlsx'))
               if not any(x in os.path.basename(h)[len(PRE):].lower() for x in RESERV))
A("Closure of the partition of chained groups")
if len(sheets) != 2:
    stop("STOP: exactly two reviewer sheets are expected and there are %d." % len(sheets),
            *["    " + os.path.basename(h) for h in sheets])
J, NOTES, revs = {}, {}, []
for h in sheets:
    rev = os.path.basename(h)[len(PRE):-5]
    J[rev], NOTES[rev], _ = leer_xlsx(h, 'partition', 'WORK', 'Note')
    revs.append(rev)
    A("  reviewer %-12s records with a letter: %d of %d" % (rev, sum(1 for c in group if J[rev].get(c)), len(group)))
for rev in revs:
    faltan = [c for c in group if not J[rev].get(c)]
    bad = [c for c in group if J[rev].get(c) and (len(J[rev][c]) != 1 or J[rev][c] not in LETTERS)]
    extra = [c for c in J[rev] if c not in group]
    if faltan or bad or extra:
        stop("STOP: the sheet of %s is not complete or has values not admitted." % rev,
                "    without letter: %d   letter not admitted: %d   foreign codes: %d" % (len(faltan), len(bad), len(extra)),
                *["    " + c for c in (faltan + bad + extra)[:10]])

def doubt_warnings(L, NT, who, gs=None):
    for g in (groups if gs is None else gs):
        count_ = collections.Counter(L[c] for c in cods[g])
        for c in cods[g]:
            if 'doubt' in NT.get(c, '').lower() and count_[L[c]] > 1:
                A("  WARNING: %s, %s has doubt in the note and shares letter %s; the closure joins it to that work."
                  % (who, c, L[c]))

for rev in revs:
    doubt_warnings(J[rev], NOTES[rev], rev)

def partition(L, g):
    b = collections.defaultdict(set)
    for c in cods[g]:
        b[L[c]].add(c)
    return frozenset(frozenset(v) for v in b.values())

def agreement_(La, Lb):
    ig = [g for g in groups if partition(La, g) == partition(Lb, g)]
    x = [La[a] == La[b] for g in groups for a, b in itertools.combinations(cods[g], 2)]
    y = [Lb[a] == Lb[b] for g in groups for a, b in itertools.combinations(cods[g], 2)]
    n = len(x)
    po = sum(1 for a, b in zip(x, y) if a == b) / n
    p0, p1 = sum(x) / n, sum(y) / n
    pe = p0 * p1 + (1 - p0) * (1 - p1)
    return n, po, ((po - pe) / (1 - pe) if pe < 1 else float('nan')), ig

r0, r1 = revs
n, po, kap, equal = agreement_(J[r0], J[r1])
discord = [g for g in groups if g not in equal]
A("")
A("AGREEMENT BETWEEN REVIEWERS (%s, %s)" % (r0, r1))
A("  implicit pairs: %d   raw agreement: %.4f   Cohen's kappa: %.4f" % (n, po, kap))
A("  groups with an identical partition: %d of %d" % (len(equal), len(groups)))
SUBMITTED = {}
for rev in revs:
    cand = sorted(glob.glob(os.path.join(WORK, '_superseded', PRE + rev + '_submitted_*.xlsx')))
    if len(cand) > 1:
        stop("STOP: there is more than one submitted sheet of %s in _superseded." % rev)
    if cand:
        Le, _, _ = leer_xlsx(cand[0], 'partition', 'WORK', 'Note')
        if set(Le) != set(group) or any(len(Le[c]) != 1 or Le[c] not in LETTERS for c in group):
            stop("STOP: the submitted sheet %s is not complete." % os.path.basename(cand[0]))
        SUBMITTED[rev] = Le
        A("  %s corrected their sheet after submitting it; submitted version: %s" % (rev, os.path.basename(cand[0])))
if SUBMITTED:
    n2, po2, kap2, ig2 = agreement_(SUBMITTED.get(r0, J[r0]), SUBMITTED.get(r1, J[r1]))
    A("  on the sheets as submitted: raw agreement %.4f   Cohen's kappa %.4f   identical groups %d of %d"
      % (po2, kap2, len(ig2), len(groups)))

FIN, NCONS = {}, {}
for g in equal:
    for c in cods[g]:
        FIN[c] = J[r0][c]
if discord:
    A("  groups with a different partition: %s" % ", ".join(discord))
    cod_d = [c for g in discord for c in cods[g]]
    if not os.path.exists(CONS):
        wb = Workbook(); ws = wb.active; ws.title = 'consensus'
        izq = [('Group', 7), ('Code', 10), ('WORK_' + r0, 11), ('WORK_' + r1, 11), ('WORK_consensus', 13),
               ('decided_by', 13), ('note', 30), ('Note_' + r0, 26), ('Note_' + r1, 26)]
        cab = [t for t, _ in izq] + [t for _, t, _ in FIELDS]
        ws.append(cab)
        thin, thick = Side(style='thin', color='999999'), Side(style='medium', color='000000')
        for k, c in enumerate(cod_d):
            ws.append([group[c], c, J[r0][c], J[r1][c], '', '', '', NOTES[r0].get(c, ''), NOTES[r1].get(c, '')]
                      + [blind[c][f] for f, _, _ in FIELDS])
        for row in ws.iter_rows(min_row=1, max_row=len(cod_d) + 1):
            for cell in row:
                r = cell.row
                ult = r == 1 or r == len(cod_d) + 1 or group[cod_d[r - 2]] != group[cod_d[r - 1]]
                cell.font = Font(name='Arial', size=10, bold=(r == 1), color='000000')
                cell.alignment = Alignment(vertical='top', wrap_text=(r == 1 or cell.column > len(izq)))
                cell.border = Border(bottom=thick if ult else thin, top=thin, left=thin, right=thin)
        dv = DataValidation(type='list', formula1='"%s"' % ",".join(LETTERS), allow_blank=True)
        dq = DataValidation(type='list', formula1='"consensus"', allow_blank=True, showErrorMessage=False)
        ws.add_data_validation(dv); ws.add_data_validation(dq)
        dv.add('E2:E%d' % (len(cod_d) + 1)); dq.add('F2:F%d' % (len(cod_d) + 1))
        for i, (_, wdt) in enumerate(izq, 1):
            ws.column_dimensions[get_column_letter(i)].width = wdt
        for i, (_, _, wdt) in enumerate(FIELDS, len(izq) + 1):
            ws.column_dimensions[get_column_letter(i)].width = wdt
        ws.freeze_panes = 'H2'
        le = wb.create_sheet('leeme')
        for line in [
                "Consensus of the partition of chained groups: %d groups, %d records." % (len(discord), len(cod_d)),
                "",
                "What is filled in. In the consensus sheet, for every record: WORK_consensus and decided_by. The note is optional.",
                "WORK_consensus: the same letter for the records of the group that are the same published document. Letters are only valid within their group and need not match the reviewers' letters.",
                "decided_by: consensus if the two reviewers resolved it. If there was no agreement, the identifier of whoever decided, who must not have read these groups.",
                "No other column, the order of the rows or the name of the consensus sheet is modified.",
                "When finished, save with the same name in work and run: python3 -I -B algorithm/14_close_partition.py"]:
            le.append([line])
        for row in le.iter_rows():
            for cell in row:
                cell.font = Font(name='Arial', size=10, color='000000')
        le.column_dimensions['A'].width = 150
        wb.active = 0
        wb.save(CONS)
        stop("STOP: there are %d groups with a different partition." % len(discord),
                "%s was written for the consensus; fill it in and run again." % os.path.basename(CONS))
    C, NCONS, QC = leer_xlsx(CONS, 'consensus', 'WORK_consensus', 'note')
    if set(C) != set(cod_d):
        stop("STOP: %s does not correspond to the current discordant groups; move it to _superseded." % os.path.basename(CONS))
    bad = [c for c in cod_d if len(C[c]) != 1 or C[c] not in LETTERS]
    sinq = [g for g in discord if not any(QC[c] for c in cods[g])]
    if bad or sinq:
        stop("STOP: the consensus is not complete: %d records without a valid letter, %d groups without decided_by."
                % (len(bad), len(sinq)))
    for c in cod_d:
        FIN[c] = C[c]
    doubt_warnings(C, NCONS, 'consensus', discord)
    who = collections.Counter(next(QC[c] for c in cods[g] if QC[c]) for g in discord)
    A("")
    A("consensus applied from %s: %d groups, %d records" % (os.path.basename(CONS), len(discord), len(cod_d)))
    A("  decided_by: " + ", ".join("%s %d" % kv for kv in sorted(who.items())))

# Letters normalised within each group: A, B, C... in code order.
NORM = {}
for g in groups:
    mapping = {}
    for c in cods[g]:
        mapping.setdefault(FIN[c], LETTERS[len(mapping)])
        NORM[c] = mapping[FIN[c]]
doubt = {c for c in group if any('doubt' in d.get(c, '').lower() for d in [NOTES[r0], NOTES[r1], NCONS])}

key = {r['code']: r['record_id'] for r in csv.DictReader(open(KEY, newline='', encoding='utf-8'))}
if set(key) != set(group):
    stop("STOP: the key does not correspond to the blind sheet.")
A("")
A("KEY OPENED. records: %d" % len(key))
works = {g: len(set(NORM[c] for c in cods[g])) for g in groups}
A("RESULT OF THE PARTITION")
A("  groups: %d   records: %d   works: %d   records with doubt (EC12): %d"
  % (len(groups), len(group), sum(works.values()), len(doubt)))
A("  works per group: " + ", ".join("%s %d" % (g, works[g]) for g in groups))
with open(FINAL, 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['group', 'code', 'record_id', 'work', 'doubt'])
    for g in groups:
        for c in cods[g]:
            w.writerow([g, c, key[c], NORM[c], 'yes' if c in doubt else 'no'])
open(RESUL, 'w', encoding='utf-8').write("\n".join(out) + "\n")
print("\n".join(out))
print("\nwritten %s and %s. Next step: python3 -I -B algorithm/12_define_corpus.py"
      % (os.path.basename(FINAL), os.path.basename(RESUL)))
