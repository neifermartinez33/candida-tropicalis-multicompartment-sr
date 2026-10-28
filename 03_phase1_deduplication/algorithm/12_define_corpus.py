# -*- coding: utf-8 -*-
"""Defines the screening corpus of phase 1 (Candida tropicalis review).

Prespecified rule (Methodological approach v4, section 5.7): screening corpus equal to
raw corpus minus confirmed merges. Confirmed merge: one in layer L1 or one that a
human confirmed in L3 or L4. Undecidable pairs keep their records separate and
resolution moves to full text (EC12).

Decision per pair, in this order:
  1. Layer. L1 merges if both L1 audits met their criterion; L2 does not merge;
     L3 and L4 require a human judgement.
  2. Human judgement where it exists: queues closed with 07 (agreement plus consensus) and
     development set. In L1 the human judgement only confirms: DIFFERENT_WORKS stops the
     script and UNDECIDABLE does not undo the L1 merge.
  3. Adjudication rules (work/adjudication_rules*.csv, RC-1), which prevail.

Records: the 47,644 of the raw corpus plus the absent ones of reconciliation v2 (rule R4).
The 19 VIP patents do not enter: reconciliation v2 shows that they were already in the corpus
(decision of 2026-10-13). Their pairs in the not-incorporated queue are excluded.

Grouping by union of the SAME_WORK pairs. If a non-merged pair ends up inside a
group (conflict by chaining), it writes work/chain_conflicts.csv and
work/chain_conflict_groups.csv and stops until work/chain_partition_final.csv exists,
the human partition of those groups (13 and 14), which replaces the union inside them.

Representative of each work (decision of 2026-10-13): has an abstract; has a valid DOI;
more filled fields among authors, journal, year, volume, issue and page; lowest identifier.

Outputs: work/pair_decisions.csv, work/corpus_clusters.csv, work/undecidable_EC12.csv,
results/screening_corpus_phase1_n<N>_<date>.ris (literal RIS blocks of the
representatives) and results/corpus_definition_report_<date>.txt. Does not overwrite.

Usage, from 03_phase1_deduplication:  python3 -I -B algorithm/12_define_corpus.py [--dry]
--dry writes nothing.
"""
import csv, glob, os, sys, re, pickle, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
ROOT = os.path.dirname(BASE)
WORK = os.path.join(BASE, 'work')
DRY = '--dry' in sys.argv[1:]
REC = os.path.join(ROOT, '02_phase0_raw_corpus', 'reconciliation')
ABSENT_V2 = os.path.join(REC, 'reconciliation_absent_v2_2026-10-13.csv')
SUMMARY_V2 = os.path.join(REC, 'reconciliation_summary_v2_2026-10-13.txt')
DEVELOPMENT = os.path.join(BASE, 'adjudication', 'development_set_300_2026-09-28.csv')
CONFLICTS = os.path.join(WORK, 'chain_conflicts.csv')
GROUPS_C = os.path.join(WORK, 'chain_conflict_groups.csv')
PARTITION = os.path.join(WORK, 'chain_partition_final.csv')
RESULTS = os.path.join(BASE, 'results')
RAW_RIS = os.path.join(ROOT, '02_phase0_raw_corpus', 'raw_corpus_n47644_2026-09-28.ris')
NOINC_RIS = os.path.join(ROOT, '02_phase0_raw_corpus', 'not_incorporated', 'not_incorporated_n335_2026-10-13.ris')
HOY = datetime.date.today().isoformat()
COLAS_Q = ['audit_L1_with_doi', 'audit_L1_without_doi', 'sample_L2_1000', 'human_queue_L3_L4']
COLA_N = 'not_incorporated_queue'
ETIQ_DES = {'DUPLICATE': 'SAME_WORK', 'DIFFERENT': 'DIFFERENT_WORKS', 'UNDECIDABLE': 'UNDECIDABLE'}
VALID = ('SAME_WORK', 'DIFFERENT_WORKS', 'UNDECIDABLE')
RESERVED = ('consensus', 'discrepancies', 'key', 'result')

out = []
A = out.append

def stop(*lines):
    print("\n".join(out))
    print("")
    for l in lines:
        print(l)
    print("The corpus was NOT written.")
    sys.exit(3)

# Reading functions of 07, without running its main flow.
_src = open(os.path.join(HERE, '07_audit_close.py'), encoding='utf-8').read()
_src = _src[:_src.index('RESERVADOS = (')]
_argv, sys.argv = sys.argv, ['07_audit_close.py', '-']
G07 = {'__file__': os.path.join(HERE, '07_audit_close.py'), '__name__': 'aud07'}
exec(compile(_src, '07_audit_close.py', 'exec'), G07)
sys.argv = _argv
G07['stop'] = stop

def leer_csv(p):
    return list(csv.DictReader(open(p, newline='', encoding='utf-8-sig')))

# Adjudication rules, as in 07.
RULES_DOC, ORIGIN = {}, {}
for f in sorted(glob.glob(os.path.join(WORK, 'adjudication_rules*.csv'))):
    for r in leer_csv(f):
        p = r['pair_id']
        if p in RULES_DOC and RULES_DOC[p] != r['rule_judgement']:
            stop("STOP: pair %s has contradictory rules." % p)
        RULES_DOC[p], ORIGIN[p] = r['rule_judgement'], r['rule']

def finales(pref):
    """Final judgement of a closed queue, with the same logic as 07."""
    sheets = sorted(h for h in glob.glob(os.path.join(WORK, pref + '_*.xlsx'))
                   + glob.glob(os.path.join(WORK, pref + '_blind_*.csv'))
                   if not any(x in os.path.basename(h)[len(pref):].lower() for x in RESERVED))
    if len(sheets) != 2:
        stop("STOP: %s does not have exactly two reviewer sheets." % pref)
    J = [G07['leer'](h) for h in sheets]
    U = [r['pair_id'] for r in leer_csv(os.path.join(WORK, pref + '_blind.csv'))]
    if any(p not in j for j in J for p in U):
        stop("STOP: %s has pairs without judgement." % pref)
    F = {p: J[0][p] for p in U if J[0][p] == J[1][p]}
    disc = [p for p in U if p not in F]
    if disc:
        cx, cc = (os.path.join(WORK, pref + '_consensus.' + e) for e in ('xlsx', 'csv'))
        if not (os.path.exists(cx) or os.path.exists(cc)):
            stop("STOP: %s has discrepancies and no consensus." % pref)
        c, _ = G07['read_consensus'](cx if os.path.exists(cx) else cc)
        if any(c.get(p) not in VALID for p in disc):
            stop("STOP: the consensus of %s does not resolve all the discrepancies." % pref)
        for p in disc:
            F[p] = c[p]
    for p in U:
        if p in RULES_DOC:
            F[p] = RULES_DOC[p]
    if any(v not in VALID for v in F.values()):
        stop("STOP: %s has judgements with a value not admitted." % pref)
    return F

def expected(pref):
    """Count by category that 07 wrote in <pref>_result.txt."""
    txt = open(os.path.join(WORK, pref + '_result.txt'), encoding='utf-8').read()
    m = re.search(r'confirmed same work\s*:\s*(\d+)', txt)
    if m:
        return {'SAME_WORK': int(m.group(1)),
                'DIFFERENT_WORKS': int(re.search(r'confirmed different works\s*:\s*(\d+)', txt).group(1)),
                'UNDECIDABLE': int(re.search(r'undecidable after human reading\s*:\s*(\d+)', txt).group(1))}
    lin = txt.splitlines()
    i = next(k for k, l in enumerate(lin) if l.startswith('model \\ human'))
    rows = [l.split() for l in lin[i + 1:i + 4]]
    return {c: sum(int(f[k + 1]) for f in rows) for k, c in enumerate(VALID)}

A("Definition of the screening corpus, phase 1" + ("  [--dry: writes nothing]" if DRY else ""))
A("")

# 1. Criterion of the L1 audits.
for pref in COLAS_Q[:2]:
    if 'CRITERION MET' not in open(os.path.join(WORK, pref + '_result.txt'), encoding='utf-8').read():
        stop("STOP: %s did not meet the criterion; L1 cannot be merged automatically." % pref)
A("L1 audits: criterion met in both strata")

# 2. Human judgements of the queues, checked against what 07 wrote.
FIN = {}
A("")
A("final judgement per queue (checked against <queue>_result.txt):")
for pref in COLAS_Q + [COLA_N]:
    FIN[pref] = finales(pref)
    obs = collections.Counter(FIN[pref].values())
    esp = expected(pref)
    if any(obs[c] != esp[c] for c in VALID):
        stop("STOP: %s does not reproduce its result: %s versus %s." % (pref, dict(obs), esp))
    A("  %-24s %5d pairs  SW %5d  DW %5d  UND %3d  matches" % (pref, len(FIN[pref]), obs['SAME_WORK'],
      obs['DIFFERENT_WORKS'], obs['UNDECIDABLE']))

# 3. Layers and development set.
L = {r['pair_id']: r for r in leer_csv(os.path.join(WORK, 'layers.csv'))}
by_records = {frozenset((r['id_1'], r['id_2'])): p for p, r in L.items()}
HUM = {}
for pref in COLAS_Q:
    for p, j in FIN[pref].items():
        if p not in L or p in HUM:
            stop("STOP: pair %s of %s is not in layers.csv or is in two queues." % (p, pref))
        HUM[p] = (j, pref)
n_des = 0
for r in leer_csv(DEVELOPMENT):
    p = by_records.get(frozenset((r['id_1'], r['id_2'])))
    if not p or L[p]['is_development'] != 'yes' or p in HUM or r['label'] not in ETIQ_DES:
        stop("STOP: development pair %s cannot be assigned." % r['pair_id'])
    HUM[p] = (ETIQ_DES[r['label']], 'development')
    n_des += 1

DEC = {}
for p, r in L.items():
    layer, h = r['layer'], HUM.get(p)
    if layer == 'L1':
        if h and h[0] == 'DIFFERENT_WORKS':
            stop("STOP: L1 pair %s has the human judgement DIFFERENT_WORKS." % p)
        d, f = 'SAME_WORK', 'L1'
    elif layer == 'L2':
        d, f = h if h else ('DIFFERENT_WORKS', 'L2')
    elif layer in ('L3', 'L4'):
        if not h:
            stop("STOP: pair %s of %s has no human judgement." % (p, layer))
        d, f = h
    else:
        stop("STOP: unknown layer in pair %s." % p)
    if p in RULES_DOC:
        d, f = RULES_DOC[p], ORIGIN[p]
    DEC[p] = [r['id_1'], r['id_2'], layer, r['is_development'], d, f]

# 4. Records: raw corpus plus R4 of reconciliation v2.
R = pickle.load(open(os.path.join(WORK, 'records.pkl'), 'rb'))
N = pickle.load(open(os.path.join(WORK, 'records_not_incorporated.pkl'), 'rb'))
aus = {(r['file'], int(r['position'])) for r in leer_csv(ABSENT_V2)}
R4 = {k for k, d in N.items() if (d['source_file'], d['source_index']) in aus}
if len(R4) != len(aus):
    stop("STOP: %d absent in reconciliation v2 and %d records recovered." % (len(aus), len(R4)))
OUTSIDE = set(N) - R4
IDS = set(R) | R4
NP = {r['pair_id']: r for r in leer_csv(os.path.join(WORK, 'not_incorporated_pairs.csv'))}
excl = collections.Counter()
for p, j in FIN[COLA_N].items():
    a, b = NP[p]['id_1'], NP[p]['id_2']
    if a in OUTSIDE or b in OUTSIDE:
        excl[(NP[p]['type'], j)] += 1
        continue
    DEC[p] = [a, b, 'P0NC', 'no', j, ORIGIN[p] if p in RULES_DOC else COLA_N]
if any(a not in IDS or b not in IDS for a, b, *_ in DEC.values()):
    stop("STOP: there are pairs with records outside the corpus.")
A("")
A("records: %d of the raw corpus + %d recovered by R4 = %d" % (len(R), len(R4), len(IDS)))
A("  outside the corpus by reconciliation v2: %d (%s)" % (len(OUTSIDE), ", ".join(
    "%s %d" % kv for kv in sorted(collections.Counter(N[k]['source'] for k in OUTSIDE).items()))))
A("  pairs of %s excluded with them: %d (%s)" % (COLA_N, sum(excl.values()),
    ", ".join("%s %s %d" % (t, j, n) for (t, j), n in sorted(excl.items()))))

A("")
A("decision per pair, by origin:")
tab = collections.Counter((d, f) for *_, d, f in DEC.values())
for (d, f), n in sorted(tab.items(), key=lambda x: (x[0][0], -x[1])):
    A("  %-16s %-24s %6d" % (d, f, n))
A("  %-41s %6d" % ("total pairs", len(DEC)))
A("  pairs of the development set with a human label: %d" % n_des)
A("  L1 pairs with human judgement UNDECIDABLE that keep the L1 merge: %d"
  % sum(1 for p, (j, o) in HUM.items() if L[p]['layer'] == 'L1' and j == 'UNDECIDABLE'))

# 5. Grouping.
padre = {x: x for x in IDS}
def root_(x):
    while padre[x] != x:
        padre[x] = padre[padre[x]]
        x = padre[x]
    return x
for a, b, *_, d, f in DEC.values():
    if d == 'SAME_WORK':
        ra, rb = root_(a), root_(b)
        if ra != rb:
            padre[max(ra, rb)] = min(ra, rb)
GR = {x: root_(x) for x in IDS}
tam = collections.Counter(GR.values())
A("")
A("groups (works): %d   duplicates removed: %d   largest group: %d records"
  % (len(tam), len(IDS) - len(tam), max(tam.values())))

# 6. Conflicts by chaining.
ady = collections.defaultdict(list)
for p, (a, b, *_, d, f) in DEC.items():
    if d == 'SAME_WORK':
        ady[a].append((b, p))
        ady[b].append((a, p))
def path_(a, b):
    prev, cola = {a: None}, collections.deque([a])
    while cola:
        x = cola.popleft()
        if x == b:
            break
        for y, p in sorted(ady[x]):
            if y not in prev:
                prev[y] = (x, p)
                cola.append(y)
    steps, x = [], b
    while prev[x]:
        x, p = prev[x]
        steps.append("%s[%s]" % (p, DEC[p][5]))
    return " > ".join(reversed(steps))

def freeze(path, rows, key):
    """Writes a working table; if it already exists, requires the same keys and leaves it untouched."""
    if os.path.exists(path):
        if {r[key] for r in leer_csv(path)} != {f[key] for f in rows}:
            stop("STOP: %s already exists with other content; move it to _superseded." % os.path.basename(path))
        A("  %s already exists with the same content; not overwritten" % os.path.basename(path))
        return
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    A("  written %s" % os.path.basename(path))

CONF = sorted((GR[a], p) for p, (a, b, *_, d, f) in DEC.items() if d != 'SAME_WORK' and GR[a] == GR[b])
groups_c = sorted({g for g, _ in CONF})
label = {g: "G%02d" % (i + 1) for i, g in enumerate(groups_c)}
IN_CONFLICT = {x: label[GR[x]] for x in IDS if GR[x] in label}
DOUBT = set()
if CONF:
    A("")
    A("CONFLICTS BY CHAINING: %d non-merged pairs remain inside %d groups (%d records)"
      % (len(CONF), len(groups_c), len(IN_CONFLICT)))
    for (d, f), n in sorted(collections.Counter((DEC[p][4], DEC[p][5]) for _, p in CONF).items()):
        A("  %-16s %-24s %4d" % (d, f, n))
    rows = [{'group': label[g], 'group_records': tam[g], 'pair_id': p, 'id_1': DEC[p][0], 'id_2': DEC[p][1],
              'decision': DEC[p][4], 'origin': DEC[p][5], 'same_work_path': path_(DEC[p][0], DEC[p][1])}
             for g, p in CONF]
    members = [{'group': g, 'group_records': tam[GR[x]], 'record_id': x}
                for x, g in sorted(IN_CONFLICT.items(), key=lambda t: (t[1], t[0]))]
    if not DRY:
        freeze(CONFLICTS, rows, 'pair_id')
        freeze(GROUPS_C, members, 'record_id')
    if not os.path.exists(PARTITION):
        stop("STOP: the union of SAME_WORK pairs joins records that a human or a layer separated.",
                "The partition of those groups is pending: sheets with 13_make_partition_sheets.py,",
                "closure with 14_close_partition.py.")
    PT = leer_csv(PARTITION)
    if ({r['record_id'] for r in PT} != set(IN_CONFLICT)
            or any(IN_CONFLICT[r['record_id']] != r['group'] or not r['work'].strip() for r in PT)):
        stop("STOP: %s does not cover exactly the records of the groups in conflict." % os.path.basename(PARTITION))
    for r in PT:
        GR[r['record_id']] = "%s|%s" % (r['group'], r['work'].strip().upper())
        if r.get('doubt') == 'yes':
            DOUBT.add(r['record_id'])
    A("")
    A("partition applied from %s: %d records in %d works; %d records with doubt (EC12)"
      % (os.path.basename(PARTITION), len(PT), len({GR[x] for x in IN_CONFLICT}), len(DOUBT)))
    cont = collections.Counter()
    for p, (a, b, layer, des, d, f) in DEC.items():
        if a in IN_CONFLICT and b in IN_CONFLICT and IN_CONFLICT[a] == IN_CONFLICT[b]:
            cont[(d, f if f in ('L1', 'L2', 'RC-1') else 'human', 'together' if GR[a] == GR[b] else 'separate')] += 1
    A("  previous decisions inside those groups, against the partition:")
    for (d, f, s), n in sorted(cont.items()):
        A("    %-16s %-7s %-10s %4d" % (d, f, s, n))
    tam = collections.Counter(GR.values())

# 7. Representative record: abstract, valid DOI, filled fields, lowest identifier.
def blocks(path):
    B, cur = {}, []
    for line in open(path, encoding='utf-8', errors='replace'):
        if not cur and not line.startswith('TY  -'):
            continue
        cur.append(line)
        if line.startswith('ER  -'):
            an = next((l[6:].strip() for l in cur if l.startswith('AN  -')), None)
            if an is None or an in B:
                stop("STOP: RIS block without AN or with a repeated AN in %s." % os.path.basename(path))
            B[an] = ''.join(cur)
            cur = []
    return B
BLOQ = blocks(RAW_RIS)
BLOQ.update({k: v for k, v in blocks(NOINC_RIS).items() if k in R4})
if set(BLOQ) != IDS:
    stop("STOP: %d records without an RIS block." % len(IDS - set(BLOQ)))
def order(x):
    d = R.get(x) or N.get(x)
    ab = any(l.startswith('AB  -') and l[6:].strip() for l in BLOQ[x].splitlines())
    filled = sum(1 for k in ('authors', 'journal', 'year', 'vol', 'issue', 'sp') if d.get(k))
    return (not ab, not d.get('dois'), -filled, x)
REP = {}
for x in IDS:
    g = GR[x]
    if g not in REP or order(x) < order(REP[g]):
        REP[g] = x
WORK_COLUMN = {g: "O%05d" % (i + 1) for i, g in enumerate(sorted(REP, key=lambda g: REP[g]))}
n_works = len(REP)
with_ab = sum(1 for g, x in REP.items() if not order(x)[0])
A("")
A("works: %d   duplicates removed: %d   representatives with abstract: %d" % (n_works, len(IDS) - n_works, with_ab))

# 8. PRISMA chain.
m = re.search(r'exported (\d+) - absent (\d+) - consolidated copies (\d+) \+ residual (\d+) = corpus (\d+)',
              open(SUMMARY_V2, encoding='utf-8').read())
exp_, aus_, cop_, res_, cor_ = map(int, m.groups())
if exp_ - aus_ - cop_ + res_ != cor_ or cor_ != len(R) or aus_ != len(R4):
    stop("STOP: the chain of reconciliation v2 does not reconcile with the records of the script.")
A("")
A("PRISMA CHAIN")
A("  records identified (R1, R2)                         %6d" % exp_)
A("  identical copies consolidated (R3)                  %6d" % cop_)
A("  not incorporated at import (R4)                     %6d" % aus_)
A("  corpus records without a counterpart (residual)     %6d" % res_)
A("  imported corpus                                     %6d" % cor_)
A("  not incorporated, recovered (R4)                    %6d" % len(R4))
A("  records entering deduplication                      %6d" % len(IDS))
A("  duplicates removed in phase 1                       %6d" % (len(IDS) - n_works))
A("  records for screening                              %6d" % n_works)

# 9. Outputs.
OUTPUTS = {
    'pairs': os.path.join(WORK, 'pair_decisions.csv'),
    'works': os.path.join(WORK, 'corpus_clusters.csv'),
    'ec12': os.path.join(WORK, 'indecidibles_EC12.csv'),
    'ris': os.path.join(RESULTS, 'screening_corpus_phase1_n%d_%s.ris' % (n_works, HOY)),
    'report': os.path.join(RESULTS, 'corpus_definition_report_%s.txt' % HOY)}
if DRY:
    print("\n".join(out))
    print("\n[--dry] no output was written.")
    sys.exit(0)
ya = [os.path.basename(s) for s in OUTPUTS.values() if os.path.exists(s)]
if ya:
    stop("STOP: outputs already exist (%s); they are not overwritten." % ", ".join(ya))
with open(OUTPUTS['pairs'], 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['pair_id', 'id_1', 'id_2', 'layer', 'is_development', 'decision', 'origin', 'same_work_final'])
    for p in sorted(DEC):
        a, b, layer, des, d, f = DEC[p]
        w.writerow([p, a, b, layer, des, d, f, 'yes' if GR[a] == GR[b] else 'no'])
with open(OUTPUTS['works'], 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['record_id', 'origin', 'work', 'work_records', 'representative', 'conflict_group'])
    for x in sorted(IDS, key=lambda x: (WORK_COLUMN[GR[x]], x)):
        w.writerow([x, 'R4' if x in R4 else 'raw_corpus', WORK_COLUMN[GR[x]], tam[GR[x]],
                    'yes' if REP[GR[x]] == x else 'no', IN_CONFLICT.get(x, '')])
ec12 = [(p, DEC[p][0], DEC[p][1], 'undecidable pair', DEC[p][5]) for p in sorted(DEC)
        if DEC[p][4] == 'UNDECIDABLE' and GR[DEC[p][0]] != GR[DEC[p][1]]]
ec12 += [('', x, '', 'doubt in the partition', IN_CONFLICT[x]) for x in sorted(DOUBT)]
with open(OUTPUTS['ec12'], 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['pair_id', 'id_1', 'id_2', 'reason', 'origin'])
    w.writerows(ec12)
with open(OUTPUTS['ris'], 'w', encoding='utf-8') as fh:
    for g in sorted(REP, key=lambda g: WORK_COLUMN[g]):
        fh.write(BLOQ[REP[g]].rstrip('\n') + '\n\n')
A("")
A("for full text (EC12): %d entries" % len(ec12))
A("outputs:")
A("  " + "\n  ".join(os.path.relpath(s, BASE) for s in OUTPUTS.values()))
open(OUTPUTS['report'], 'w', encoding='utf-8').write("\n".join(out) + "\n")
print("\n".join(out))
