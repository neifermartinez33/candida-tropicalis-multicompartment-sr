# -*- coding: utf-8 -*-
"""Closure of a human reading queue of phase 1.

  python3 algorithm/07_audit_close.py human_queue_L3_L4

Reads in work/ the sheets of the two reviewers, <prefix>_<reviewer>.xlsx or
<prefix>_blind_<reviewer>.csv. Requires exactly two sheets, complete and with
admitted values. Computes the agreement and Cohen's kappa and, if there are
discrepancies, writes <prefix>_discrepancies.csv.

The discrepancies are resolved in <prefix>_consensus.csv or <prefix>_consensus.xlsx,
with the columns pair_id and consensus_judgement (in the xlsx, the sheet consensus); decided_by and
note are optional.
While a reading is missing or a discrepancy remains unresolved, the script
stops with code 3, does not open the key and does not write a result.

If tables work/adjudication_rules*.csv exist (scripts 10 and 11), it applies their rules after
the consensus to the pairs they cover and reports how many change; agreement between
reviewers is always computed on their original judgements.

Only with everything resolved does it open <prefix>_key.csv and cross the human judgement
against what the algorithm and the model decided. Writes <prefix>_result.txt.

Exact Clopper-Pearson intervals, computed by bisection on the binomial
distribution function, without external dependencies.
"""
import csv, io, os, sys, glob, math, collections

if len(sys.argv) < 2:
    sys.exit("usage: python3 algorithm/07_audit_close.py <prefix>")
PREF = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(os.path.dirname(HERE), 'work')
VALID = {'SAME_WORK', 'DIFFERENT_WORKS', 'UNDECIDABLE'}

def binom_cdf(k, n, p):
    return sum(math.comb(n, i) * p**i * (1-p)**(n-i) for i in range(0, k+1))

def clopper_pearson(k, n, alpha=0.05):
    if n == 0: return (0.0, 1.0)
    lo, hi = 0.0, 1.0
    if k > 0:
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a+b)/2
            if 1 - binom_cdf(k-1, n, m) < alpha/2: a = m
            else: b = m
        lo = (a+b)/2
    if k < n:
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a+b)/2
            if binom_cdf(k, n, m) > alpha/2: a = m
            else: b = m
        hi = (a+b)/2
    return lo, hi

def kappa(x, y):
    cats = sorted(set(x) | set(y))
    n = len(x)
    po = sum(1 for a, b in zip(x, y) if a == b) / n
    pe = sum((x.count(c)/n) * (y.count(c)/n) for c in cats)
    return po, (po - pe) / (1 - pe) if pe < 1 else float('nan')

def leer(path):
    """Reads the judgements from a csv or an xlsx. In the xlsx each pair takes two rows
    and the judgement is written only once; the first non-empty one of the pair is taken."""
    d = {}
    if path.lower().endswith('.xlsx'):
        import warnings
        from openpyxl import load_workbook
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            ws = load_workbook(path, data_only=True).active
        cab = [c.value for c in ws[1]]
        ip, ij = cab.index('Par'), cab.index('JUDGEMENT')
        clash = {}
        for row in ws.iter_rows(min_row=2, values_only=True):
            pid = row[ip]
            j = (str(row[ij]).strip().upper() if row[ij] else '')
            if not (pid and j): continue
            if pid in d and d[pid] != j:
                clash[pid] = (d[pid], j)     # two different judgements in the same pair
            d.setdefault(pid, j)
        if clash:
            print("ERROR in %s" % os.path.basename(path))
            print("  %d pair(s) with two different judgements written in their two rows." % len(clash))
            for pid, (x, y) in clash.items():
                print("    %s : row A = %s   row B = %s" % (pid, x, y))
            print("  The judgement is written ONLY once per pair, in row A.")
            print("  Correct the file leaving a single judgement per pair and run again.")
            sys.exit(2)
        return d
    with open(path, newline='', encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            j = (r.get('human_judgement') or '').strip().upper()
            if j: d[r['pair_id']] = j
    return d

def read_table(path):
    """Rows of a csv (semicolon or comma, utf-8 or cp1252) or of an xlsx, as dicts."""
    if path.lower().endswith('.xlsx'):
        import warnings
        from openpyxl import load_workbook
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            wb = load_workbook(path, data_only=True)
        ws = wb['consensus'] if 'consensus' in wb.sheetnames else next(
            (h for h in wb.worksheets
             if 'pair_id' in [str(c.value).strip() for c in h[1] if c.value is not None]), wb.active)
        it = ws.iter_rows(values_only=True)
        cab = [('' if c is None else str(c).strip()) for c in next(it, [])]
        return [{cab[i]: ('' if v is None else str(v)) for i, v in enumerate(row) if i < len(cab)}
                for row in it]
    raw = open(path, 'rb').read()
    try:
        txt = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        txt = raw.decode('cp1252')
    rows = []
    for delim in (';', ',', '\t'):
        rows = list(csv.DictReader(io.StringIO(txt), delimiter=delim))
        if rows and 'pair_id' in rows[0]:
            break
    return rows

def read_consensus(path):
    """Returns {pair_id: judgement} and {pair_id: decided_by}."""
    rows = read_table(path)
    col = next((c for c in ('consensus_judgement', 'third_reviewer_judgement', 'human_judgement')
                if rows and c in rows[0]), None)
    if col is None or 'pair_id' not in rows[0]:
        stop("STOP: %s does not have the columns pair_id and consensus_judgement." % os.path.basename(path))
    d, who, clash = {}, {}, set()
    for r in rows:
        p = (r.get('pair_id') or '').strip()
        j = (r.get(col) or '').strip().upper()
        q = (r.get('decided_by') or '').strip()
        if not p:
            continue
        if j:
            if p in d and d[p] != j:
                clash.add(p)
            d.setdefault(p, j)
        if q:
            who.setdefault(p, q)
    if clash:
        stop("STOP: %d pair(s) with two different consensus judgements in %s:" % (len(clash), os.path.basename(path)),
                *["    " + p for p in sorted(clash)[:10]],
                "The consensus judgement is written only once per pair, in row A.")
    return d, who

RESERVED = ('consensus', 'discrepancies', 'key', 'result')
sheets = sorted(h for h in glob.glob(os.path.join(WORK, PREF + '_*.xlsx'))
               + glob.glob(os.path.join(WORK, PREF + '_blind_*.csv'))
               if not any(r in os.path.basename(h)[len(PREF):].lower() for r in RESERVED))
cons_x = os.path.join(WORK, PREF + '_consensus.xlsx')
cons_c = os.path.join(WORK, PREF + '_consensus.csv')
out = []
A = out.append
A("Closure of the queue: %s" % PREF)

def stop(*lines):
    """Prints what has accumulated and the reason; exits without opening the key or writing a result."""
    print("\n".join(out))
    print("")
    for l in lines:
        print(l)
    print("The key was NOT opened and %s_result.txt was not written." % PREF)
    sys.exit(3)

if len(sheets) != 2:
    stop("STOP: exactly two reviewer sheets are expected in work/ and there are %d." % len(sheets),
            *["    " + os.path.basename(h) for h in sheets],
            "Leave in work/ only the two final sheets; the other versions go to _superseded.")

judgements = {}
for h in sheets:
    b = os.path.basename(h)
    rev = b[len(PREF)+1:-5] if b.endswith('.xlsx') else b[len(PREF)+7:-4]
    judgements[rev] = leer(h)
    A("  reviewer %-12s judgements recorded: %d" % (rev, len(judgements[rev])))

bad = {p: j for d in judgements.values() for p, j in d.items() if j not in VALID}
if bad:
    A("")
    A("WARNING: %d judgements with a value not admitted. Correct and run again." % len(bad))
    for p, j in list(bad.items())[:10]: A("   %s -> %r" % (p, j))
    print("\n".join(out)); sys.exit(1)

# Universe of pairs taken from the blind sheet, which reveals no decision.
universe = [r['pair_id'] for r in csv.DictReader(
    open(os.path.join(WORK, PREF + '_blind.csv'), newline='', encoding='utf-8'))]
revs = sorted(judgements)
faltan = {r: [p for p in universe if p not in judgements[r]] for r in revs}
if any(faltan.values()):
    stop("STOP: there are pairs without a judgement; reading is in duplicate and complete.",
            *["    %-12s %d pairs without judgement" % (r, len(faltan[r])) for r in revs if faltan[r]],
            "Complete the sheets and run again.")

final = {}
common = list(universe)
A("")
A("AGREEMENT BETWEEN REVIEWERS  (%s)" % ", ".join(revs))
A("  pairs read by everyone: %d" % len(common))
x = [judgements[revs[0]][p] for p in common]
y = [judgements[revs[1]][p] for p in common]
po, k = kappa(x, y)
A("  raw agreement: %.4f     Cohen's kappa: %.4f" % (po, k))
disc = [p for p in common if judgements[revs[0]][p] != judgements[revs[1]][p]]
A("  discrepancies: %d" % len(disc))
for p in common:
    if judgements[revs[0]][p] == judgements[revs[1]][p]:
        final[p] = judgements[revs[0]][p]

if disc:
    dp = os.path.join(WORK, PREF + '_discrepancies.csv')
    base = {r['pair_id']: r for r in csv.DictReader(
        open(os.path.join(WORK, PREF + '_blind.csv'), newline='', encoding='utf-8'))}
    if os.path.exists(dp):
        previous = {(r.get('pair_id') or '').strip() for r in read_table(dp)}
        if previous != set(disc):
            stop("STOP: %s already exists and does not correspond to the current discrepancies." % os.path.basename(dp),
                    "Move it to _superseded and run again.")
        A("  %s already exists with the same discrepancies; not overwritten" % os.path.basename(dp))
    else:
        cab = [c for c in base[disc[0]] if c not in ('human_judgement', 'reviewer', 'date', 'note')]
        with open(dp, 'w', newline='', encoding='utf-8-sig') as fh:
            w = csv.writer(fh, delimiter=';')
            w.writerow(cab + ['judgement_' + r for r in revs] + ['consensus_judgement', 'decided_by', 'note'])
            for p in disc:
                w.writerow([base[p][c] for c in cab] + [judgements[r][p] for r in revs] + ['', '', ''])
        A("  written %s for the consensus" % os.path.basename(dp))
    if os.path.exists(cons_x) and os.path.exists(cons_c):
        stop("STOP: %s_consensus.xlsx and %s_consensus.csv both exist; leave only one." % (PREF, PREF))
    cons = cons_x if os.path.exists(cons_x) else cons_c
    if not os.path.exists(cons):
        stop("STOP: there are %d discrepancies and the consensus file does not exist." % len(disc),
                "Fill consensus_judgement and decided_by in %s_discrepancies.csv," % PREF,
                "save it as %s_consensus.csv or .xlsx and run again." % PREF)
    c, who = read_consensus(cons)
    unresolved = [p for p in disc if p not in c]
    bad_c = [p for p in disc if p in c and c[p] not in VALID]
    if unresolved or bad_c:
        stop("STOP: the consensus does not resolve all the discrepancies.",
                "    discrepancies without a consensus judgement: %d" % len(unresolved),
                "    consensus judgements with a value not admitted: %d" % len(bad_c))
    for p in disc:
        final[p] = c[p]
    A("")
    A("consensus applied from %s: %d judgements" % (os.path.basename(cons), len(disc)))
    extra = len([p for p in c if p not in disc])
    if extra:
        A("  consensus entries outside the discrepancies, ignored: %d" % extra)
    qd = collections.Counter(who.get(p, '') for p in disc)
    A("  decided_by: " + ", ".join("%s %d" % (q or 'no data', n) for q, n in sorted(qd.items())))

rule_files = sorted(glob.glob(os.path.join(WORK, 'adjudication_rules*.csv')))
if rule_files:
    RG, origin = {}, {}
    for f in rule_files:
        for r in csv.DictReader(open(f, newline='', encoding='utf-8')):
            p = r['pair_id']
            if p in RG and RG[p]['rule_judgement'] != r['rule_judgement']:
                stop("STOP: pair %s has contradictory rules in %s and %s." % (p, origin[p], os.path.basename(f)))
            RG[p] = r
            origin[p] = os.path.basename(f)
    covered = [p for p in universe if p in RG]
    bad_r = [p for p in covered if RG[p]['rule_judgement'] not in VALID]
    if bad_r:
        stop("STOP: adjudication_rules.csv has %d judgements with a value not admitted." % len(bad_r))
    cambia = [p for p in covered if final.get(p) != RG[p]['rule_judgement']]
    for p in covered:
        final[p] = RG[p]['rule_judgement']
    if covered:
        A("")
        A("rules applied from %s: %d pairs covered, %d change judgement"
          % (', '.join(sorted({origin[p] for p in covered})), len(covered), len(cambia)))
        for rg, n in sorted(collections.Counter(RG[p]['rule'] for p in covered).items()):
            A("  rule %s: %d pairs" % (rg, n))

key = {r['pair_id']: r for r in csv.DictReader(
    open(os.path.join(WORK, PREF + '_key.csv'), newline='', encoding='utf-8'))}
A("")
A("KEY OPENED. pairs in the key: %d   with human judgement: %d" % (len(key), len(final)))
pend = len(key) - len([p for p in key if p in final])
if pend: A("WARNING: %d pairs remain without judgement; the result is partial." % pend)

cross = collections.Counter()
for p, r in key.items():
    if p in final: cross[(r['model'], final[p])] += 1
A("")
A("HUMAN JUDGEMENT versus MODEL DECISION")
cats = ['SAME_WORK', 'DIFFERENT_WORKS', 'UNDECIDABLE']
A("%-18s %14s %16s %13s" % ('model \\ human', *cats))
for m in cats:
    A("%-18s %14d %16d %13d" % (m, *[cross[(m, h)] for h in cats]))

n = sum(cross.values())
A("")
if PREF.startswith('audit_L1'):
    fp = sum(v for (m, h), v in cross.items() if h == 'DIFFERENT_WORKS')
    lo, hi = clopper_pearson(fp, n)
    A("RESULT OF THE L1 AUDIT")
    A("  pairs audited              : %d" % n)
    A("  false merges detected : %d" % fp)
    A("  false-positive rate   : %.4f   exact 95 %% CI [%.4f, %.4f]" % (fp/n if n else 0, lo, hi))
    A("")
    if fp == 0:
        A("  CRITERION MET. Layer L1 keeps the automatic merge.")
    else:
        A("  CRITERION NOT MET. Under the rule fixed a priori, a single false positive")
        A("  returns the whole of layer L1 to human adjudication. Nothing in L1 is")
        A("  merged automatically. Record the decision with its date.")
elif PREF.startswith('sample_L2'):
    fn = sum(v for (m, h), v in cross.items() if h == 'SAME_WORK')
    lo, hi = clopper_pearson(fn, n)
    A("RESULT OF THE L2 SAMPLE, FALSE NEGATIVES")
    A("  pairs read                     : %d" % n)
    A("  duplicates not detected        : %d" % fn)
    A("  false-negative rate            : %.4f   exact 95 %% CI [%.4f, %.4f]" % (fn/n if n else 0, lo, hi))
    A("  projection to the whole L2 layer: the rate and its interval are applied to the total")
    A("  of L2 pairs and reported as estimated missed duplicates.")
else:
    dup = cross_total = sum(v for (m, h), v in cross.items() if h == 'SAME_WORK')
    A("RESULT OF THE HUMAN ADJUDICATION QUEUE")
    A("  pairs adjudicated        : %d" % n)
    A("  confirmed same work      : %d" % dup)
    A("  confirmed different works: %d" % sum(v for (m,h),v in cross.items() if h=='DIFFERENT_WORKS'))
    A("  undecidable after human reading: %d" % sum(v for (m,h),v in cross.items() if h=='UNDECIDABLE'))
    A("")
    A("  The confirmed same-work pairs are added to the L1 merges to define the")
    A("  screening corpus. The undecidable ones are kept unmerged and are")
    A("  declared, according to the rule of section 5.7.")

txt = "\n".join(out)
open(os.path.join(WORK, PREF + '_result.txt'), 'w', encoding='utf-8').write(txt + "\n")
print(txt)
