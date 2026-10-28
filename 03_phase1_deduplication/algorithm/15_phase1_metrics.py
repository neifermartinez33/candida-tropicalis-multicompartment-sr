# -*- coding: utf-8 -*-
"""Phase 1 metrics according to adjudication/metrics_plan_phase1_2026-10-13.md.

Usage, from 03_phase1_deduplication:  python3 -I -B algorithm/15_phase1_metrics.py [--dry]
--dry computes and prints without writing anything. Writes results/phase1_metrics_report_<date>.txt, results/phase1_metrics_<date>.csv and
results/rayyan_lost_works_<date>.csv. Does not overwrite.
"""
import csv, os, sys, re, math, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
ROOT = os.path.dirname(BASE)
WORK, RESULTS = os.path.join(BASE, 'work'), os.path.join(BASE, 'results')
HOY = datetime.date.today().isoformat()
OUT_TXT = os.path.join(RESULTS, 'phase1_metrics_report_%s.txt' % HOY)
OUT_CSV = os.path.join(RESULTS, 'phase1_metrics_%s.csv' % HOY)
OUT_RAY = os.path.join(RESULTS, 'rayyan_lost_works_%s.csv' % HOY)
DRY = '--dry' in sys.argv[1:]
ya = [os.path.basename(p) for p in (OUT_TXT, OUT_CSV, OUT_RAY) if os.path.exists(p)]
if ya and not DRY:
    sys.exit("STOP: %s already exist; they are not overwritten." % ", ".join(ya))

# ---------- statistics without dependencies ----------
def _betacf(a, b, x):
    fpmin, qab, qap, qam = 1e-300, a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > fpmin else fpmin)
    h = d
    for m in range(1, 100000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d; d = 1.0 / (d if abs(d) > fpmin else fpmin)
        c = 1.0 + aa / c; c = c if abs(c) > fpmin else fpmin
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d; d = 1.0 / (d if abs(d) > fpmin else fpmin)
        c = 1.0 + aa / c; c = c if abs(c) > fpmin else fpmin
        de = d * c
        h *= de
        if abs(de - 1.0) < 1e-15:
            break
    return h

def betainc(a, b, x):
    if x <= 0.0: return 0.0
    if x >= 1.0: return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b

def beta_ppf(q, a, b):
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if betainc(a, b, mid) < q: lo = mid
        else: hi = mid
    return (lo + hi) / 2.0

def cp(k, n, alpha=0.05):
    """Exact Clopper-Pearson interval."""
    if n <= 0: return (float('nan'), float('nan'))
    lo = 0.0 if k <= 0 else beta_ppf(alpha / 2.0, k, n - k + 1)
    hi = 1.0 if k >= n else beta_ppf(1.0 - alpha / 2.0, k + 1, n - k)
    return lo, hi

def binom_cdf_half(k, n):
    if k >= n: return 1.0
    return betainc(n - k, k + 1, 0.5)

def mcnemar_exact(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2.0 * binom_cdf_half(min(b, c), n))

def kappa(x, y):
    n = len(x)
    po = sum(1 for a, b in zip(x, y) if a == b) / n
    p1, p2 = sum(x) / n, sum(y) / n
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    return po, ((po - pe) / (1 - pe) if pe < 1 else float('nan'))

# check against known values
assert abs(cp(0, 100)[1] - (1 - 0.025 ** (1 / 100))) < 1e-6
assert abs(cp(0, 1000)[1] - (1 - 0.025 ** (1 / 1000))) < 1e-6
assert abs(cp(50, 100)[0] - 0.3983) < 1e-3 and abs(cp(50, 100)[1] - 0.6017) < 1e-3

def leer(p):
    return list(csv.DictReader(open(p, newline='', encoding='utf-8-sig')))

out = []
A = out.append
A("Phase 1 metrics. Plan: adjudication/metrics_plan_phase1_2026-10-13.md")
A("")

# ---------- data ----------
PD = {r['pair_id']: r for r in leer(os.path.join(WORK, 'pair_decisions.csv'))}
LY = {r['pair_id']: r for r in leer(os.path.join(WORK, 'layers.csv'))}
CL = {r['record_id']: r for r in leer(os.path.join(WORK, 'corpus_clusters.csv'))}
DOUBT = {r['record_id'] for r in leer(os.path.join(WORK, 'chain_partition_final.csv')) if r['doubt'] == 'yes'}
AUD = {}
for est in ('with_doi', 'without_doi'):
    for r in leer(os.path.join(WORK, 'audit_L1_%s_key.csv' % est)):
        AUD[r['pair_id']] = est
MUE = {r['pair_id'] for r in leer(os.path.join(WORK, 'sample_L2_1000_key.csv'))}

Q = [p for p, r in PD.items() if r['layer'] in ('L1', 'L2', 'L3', 'L4') and r['is_development'] == 'no']
assert len(Q) == sum(1 for r in LY.values() if r['is_development'] == 'no')

def partition(r):
    g1, g2 = CL[r['id_1']]['conflict_group'], CL[r['id_2']]['conflict_group']
    return bool(g1) and g1 == g2

rows = []
for p in Q:
    r, ly = PD[p], LY[p]
    part = partition(r)
    etiq = r['layer'] in ('L3', 'L4') or p in AUD or p in MUE or r['origin'] == 'RC-1' or part
    if etiq:
        if part and (r['id_1'] in DOUBT or r['id_2'] in DOUBT):
            ref = 'UNRESOLVED'
        elif not part and r['decision'] == 'UNDECIDABLE' and r['same_work_final'] == 'no':
            ref = 'UNRESOLVED'
        else:
            ref = 'MO' if r['same_work_final'] == 'yes' else 'OD'
    else:
        ref = {'L1': 'MO', 'L2': 'OD'}[r['layer']]
    rows.append({'p': p, 'layer': r['layer'], 'doi': ly['shares_doi'], 'etiq': etiq, 'ref': ref,
                  'alg': ly['algorithm'], 'mod': ly['model']})

A("POPULATION AND REFERENCE STANDARD")
A("  pairs of the main flow without the development set: %d" % len(rows))
for layer in ('L1', 'L2', 'L3', 'L4'):
    fs = [f for f in rows if f['layer'] == layer]
    c = collections.Counter((f['etiq'], f['ref']) for f in fs)
    A("  %s: %6d pairs | with human judgement or rule: %5d (same work %d, different works %d, unresolved %d) | imputed: %d"
      % (layer, len(fs), sum(v for (e, _), v in c.items() if e), c[(True, 'MO')], c[(True, 'OD')], c[(True, 'UNRESOLVED')],
         sum(v for (e, _), v in c.items() if not e)))
l1_known = sum(1 for f in rows if f['layer'] == 'L1' and f['etiq'] and f['ref'] == 'OD')
A("  known false merges in L1 (RC-1 and partition, not random): %d of %d (%.2f %%)"
  % (l1_known, sum(1 for f in rows if f['layer'] == 'L1'), 100.0 * l1_known / sum(1 for f in rows if f['layer'] == 'L1')))
l2_known = sum(1 for f in rows if f['layer'] == 'L2' and f['etiq'] and f['ref'] == 'MO')
A("  known duplicates in L2 (partition, not random): %d" % l2_known)

# ---------- classification and metrics ----------
POS = {'alg': 'DUPLICATE', 'mod': 'SAME_WORK'}
ABS = {'alg': 'HUMAN_ZONE', 'mod': 'UNDECIDABLE'}
NAME = {'alg': 'algorithm', 'mod': 'model'}
det = [f for f in rows if f['ref'] in ('MO', 'OD')]

def matrix(proc, exclude_abst):
    t = collections.Counter()
    for f in det:
        if exclude_abst and f[proc] == ABS[proc]:
            continue
        pos = f[proc] == POS[proc]
        t[('TP' if pos else 'FN') if f['ref'] == 'MO' else ('FP' if pos else 'TN')] += 1
    return t

def metrics(t):
    tp, fp, fn, tn = t['TP'], t['FP'], t['FN'], t['TN']
    res = {}
    for name, k, n in (('sensitivity', tp, tp + fn), ('especificidad', tn, tn + fp), ('VPP', tp, tp + fp)):
        lo, hi = cp(round(k), round(n)) if abs(k - round(k)) < 1e-9 and abs(n - round(n)) < 1e-9 else (float('nan'), float('nan'))
        res[name] = (k / n if n else float('nan'), lo, hi)
    return res

csv_rows = []
A("")
A("SENSITIVITY, SPECIFICITY AND PPV (determined reference: %d pairs; unresolved: %d)"
  % (len(det), sum(1 for f in rows if f['ref'] == 'UNRESOLVED')))
for analysis, excl in (('main analysis (abstention = not positive)', False), ('sensitivity analysis (abstentions excluded)', True)):
    A("  %s" % analysis)
    for proc in ('alg', 'mod'):
        t = matrix(proc, excl)
        m = metrics(t)
        A("    %-9s TP %6d  FP %5d  FN %5d  TN %6d | sens %.4f [%.4f, %.4f]  espec %.4f [%.4f, %.4f]  VPP %.4f [%.4f, %.4f]"
          % (NAME[proc], t['TP'], t['FP'], t['FN'], t['TN'], *m['sensitivity'], *m['especificidad'], *m['VPP']))
        csv_rows.append(dict(procedure=NAME[proc], analysis=analysis, TP=t['TP'], FP=t['FP'], FN=t['FN'], TN=t['TN'],
                              **{'%s%s' % (k, s): '%.6f' % v[i] for k, v in m.items() for i, s in enumerate(('', '_li', '_ls'))}))
    if excl:
        for proc in ('alg', 'mod'):
            n_abs = sum(1 for f in det if f[proc] == ABS[proc])
            A("    abstentions of the %s: %d (%.2f %% of the pairs with a determined reference)" % (NAME[proc], n_abs, 100.0 * n_abs / len(det)))

# worst case within the intervals of the samples
p_l1 = {est: cp(0, 100)[1] for est in ('yes', 'no')}
q_l2 = cp(0, 1000)[1]
rem_l1 = collections.Counter(f['doi'] for f in rows if f['layer'] == 'L1' and not f['etiq'])
rem_l2 = sum(1 for f in rows if f['layer'] == 'L2' and not f['etiq'])
mover_fp = sum(rem_l1[s] * p_l1[s] for s in rem_l1)
mover_fn = rem_l2 * q_l2
A("")
A("WORST CASE WITHIN THE INTERVALS OF THE SAMPLES (main analysis)")
A("  rest of L1 not read: %d pairs (shared DOI %d, no shared DOI %d); false merges at the upper limit: %.1f"
  % (sum(rem_l1.values()), rem_l1['yes'], rem_l1['no'], mover_fp))
A("  rest of L2 not read: %d pairs; duplicates at the upper limit: %.1f" % (rem_l2, mover_fn))
for proc in ('alg', 'mod'):
    t = matrix(proc, False)
    tp, fp, fn, tn = t['TP'] - mover_fp, t['FP'] + mover_fp, t['FN'] + mover_fn, t['TN'] - mover_fn
    A("    %-9s sens %.4f  espec %.4f  VPP %.4f" % (NAME[proc], tp / (tp + fn), tn / (tn + fp), tp / (tp + fp)))

# McNemar and kappa
b = c = 0
for f in det:
    ca = (f['alg'] == POS['alg']) == (f['ref'] == 'MO')
    cm = (f['mod'] == POS['mod']) == (f['ref'] == 'MO')
    b += ca and not cm
    c += cm and not ca
A("")
A("PAIRED COMPARISON (exact McNemar, main analysis)")
pm = mcnemar_exact(b, c)
A("  algorithm right and model wrong: %d   model right and algorithm wrong: %d   %s"
  % (b, c, 'p < 0.0001' if pm < 1e-4 else 'p = %.4f' % pm))
po, k = kappa([f['alg'] == POS['alg'] for f in rows], [f['mod'] == POS['mod'] for f in rows])
A("  Cohen's kappa between algorithm and model (%d pairs, positive versus not positive): %.4f (raw agreement %.4f)" % (len(rows), k, po))

# random samples
A("")
A("RANDOM SAMPLES")
for est, name in (('with_doi', 'with shared DOI'), ('without_doi', 'without shared DOI')):
    ps = [p for p, e in AUD.items() if e == est]
    fp = sum(1 for p in ps if PD[p]['same_work_final'] == 'no')
    lo, hi = cp(fp, len(ps))
    A("  L1 audit, %s: %d false merges in %d pairs, 95 %% CI [%.4f, %.4f]" % (name, fp, len(ps), lo, hi))
fn = sum(1 for p in MUE if PD[p]['same_work_final'] == 'yes')
lo, hi = cp(fn, len(MUE))
n_l2 = sum(1 for f in rows if f['layer'] == 'L2')
A("  L2 sample: %d duplicates in %d pairs, 95 %% CI [%.4f, %.4f]; projection to %d L2 pairs: %.0f [%.0f, %.0f]"
  % (fn, len(MUE), lo, hi, n_l2, n_l2 * fn / len(MUE), n_l2 * lo, n_l2 * hi))

# duplicate rate of the candidate space (development set)
nk = collections.Counter(len(r['keys']) for r in LY.values())
by_rec = {frozenset((r['id_1'], r['id_2'])): p for p, r in LY.items()}
dev = collections.defaultdict(collections.Counter)
for r in leer(os.path.join(BASE, 'adjudication', 'development_set_300_2026-09-28.csv')):
    p = by_rec[frozenset((r['id_1'], r['id_2']))]
    dev[len(LY[p]['keys'])][r['label']] += 1
N = sum(nk.values())
est = var = lo_b = hi_b = 0.0
A("")
A("DUPLICATE RATE OF THE CANDIDATE SPACE (development set, strata by number of keys)")
for k in sorted(nk):
    d, s, i = dev[k]['DUPLICATE'], dev[k]['DIFFERENT'], dev[k]['UNDECIDABLE']
    pk = d / (d + s)
    w = nk[k] / N
    est += w * pk
    var += w * w * pk * (1 - pk) / (d + s)
    lo_b += w * d / (d + s + i)
    hi_b += w * (d + i) / (d + s + i)
    A("  %d key(s): %6d candidate pairs | sample: %d duplicates, %d different, %d undecidable" % (k, nk[k], d, s, i))
se = math.sqrt(var)
A("  weighted rate over decidable pairs: %.4f (approximate 95 %% CI %.4f to %.4f); with the undecidable ones as different or as duplicates: %.4f to %.4f"
  % (est, est - 1.96 * se, est + 1.96 * se, lo_b, hi_b))

# Rayyan
def an_of(path):
    return [l[6:].strip() for l in open(path, encoding='utf-8', errors='replace') if l.startswith('AN  -')]
surv = set(an_of(os.path.join(ROOT, '02_phase0_raw_corpus', 'screening_corpus_n23024_2026-09-28.ris')))
deleted = set(an_of(os.path.join(ROOT, '02_phase0_raw_corpus', 'deleted_duplicates_n24620_2026-09-28.ris')))
corp = {x for x, r in CL.items() if r['origin'] == 'raw_corpus'}
assert not (surv & deleted) and (surv | deleted) == corp, "the Rayyan sets do not match the corpus"
works = collections.defaultdict(list)
for x in corp:
    works[CL[x]['work']].append(x)
tp = fp = fn = tn = 0
lost, pairs_fn = [], 0
for o, xs in works.items():
    k, d = sum(1 for x in xs if x in surv), sum(1 for x in xs if x in deleted)
    if k >= 1:
        tn += 1; fn += k - 1; tp += d; pairs_fn += k * (k - 1) // 2
    else:
        fp += 1; tp += d - 1; lost.append((o, xs))
A("")
A("RAYYAN, HISTORICAL RUN (record level, %d records, %d works)" % (len(corp), len(works)))
A("  kept %d, removed %d" % (len(surv), len(deleted)))
for name, kk, nn in (('sensitivity', tp, tp + fn), ('especificidad', tn, tn + fp), ('VPP', tp, tp + fp)):
    lo, hi = cp(kk, nn)
    A("  %-13s %.4f [%.4f, %.4f]   (%d of %d)" % (name, kk / nn, lo, hi, kk, nn))
A("  works removed entirely (studies withdrawn without reason): %d, with %d records" % (len(lost), sum(len(xs) for _, xs in lost)))
A("  duplicates not detected: %d surplus records kept; %d pairs of kept records that are the same work" % (fn, pairs_fn))
csv_rows.append(dict(procedure='Rayyan', analysis='record level', TP=tp, FP=fp, FN=fn, TN=tn))

# Check not prespecified (addendum to the plan): what was lost in the works removed entirely
import pickle
RP = pickle.load(open(os.path.join(WORK, 'records.pkl'), 'rb'))
with_surv = {o for o, xs in works.items() if any(x in surv for x in xs)}
tit = collections.defaultdict(set)
for o in with_surv:
    for x in works[o]:
        t = RP[x].get('tnorm', '')
        if len(t) >= 20:
            tit[t[:80]].add(o)
by_works = collections.defaultdict(list)
for r in PD.values():
    if r['id_1'] in CL and r['id_2'] in CL:
        by_works[frozenset((CL[r['id_1']]['work'], CL[r['id_2']]['work']))].append(r)
lost_class = {}
for o, xs in lost:
    socios = set()
    for x in xs:
        t = RP[x].get('tnorm', '')
        if len(t) >= 20:
            socios |= tit.get(t[:80], set())
    if not socios:
        lost_class[o] = 'no surviving document with the same title'
        continue
    orig = {('RC-1' if r['origin'] == 'RC-1' else ('L2' if r['origin'] == 'L2' else 'human ' + r['decision']))
            for so in socios for r in by_works.get(frozenset((o, so)), [])}
    if 'RC-1' in orig: c_ = 'component or deposit separated by RC-1'
    elif 'human DIFFERENT_WORKS' in orig: c_ = 'separated by human judgement of the pair'
    elif 'human UNDECIDABLE' in orig: c_ = 'human undecidable'
    elif 'human SAME_WORK' in orig: c_ = 'separated by the partition of groups'
    elif orig == {'L2'}: c_ = 'separated only by automatic L2'
    else: c_ = 'same title, no pair assessed'
    lost_class[o] = c_
A("  check not prespecified of the %d works removed entirely (normalised title, 80 characters):" % len(lost))
for c_, n_ in collections.Counter(lost_class.values()).most_common():
    A("    %-50s %4d works" % (c_, n_))
A("    with a surviving document of the same title, the study can remain in the corpus through that document;")
A("    those separated only by L2 are possible duplicates that phase 1 did not join")

# not-incorporated stretch (descriptive)
NIP = {r['pair_id']: r for r in leer(os.path.join(WORK, 'not_incorporated_pairs.csv'))}
nc = [p for p, r in PD.items() if r['layer'] == 'P0NC']
tab = collections.Counter((NIP[p]['algorithm'], 'same work' if PD[p]['same_work_final'] == 'yes' else 'different works') for p in nc)
A("")
A("NOT-INCORPORATED STRETCH (descriptive, without model; %d pairs without the VIP ones)" % len(nc))
for a in ('DUPLICATE', 'DOUBTFUL', 'DIFFERENT'):
    A("  algorithm %-10s same work %3d   different works %3d" % (a, tab[(a, 'same work')], tab[(a, 'different works')]))

# agreement between reviewers
A("")
A("AGREEMENT BETWEEN REVIEWERS (from the closure results)")
for pref, name in (('audit_L1_with_doi', 'L1 audit, with DOI'), ('audit_L1_without_doi', 'L1 audit, without DOI'),
                     ('sample_L2_1000', 'L2 sample'), ('human_queue_L3_L4', 'cola L3/L4'),
                     ('not_incorporated_queue', 'not incorporated'), ('chain_partition', 'partition of chained groups')):
    t = open(os.path.join(WORK, pref + '_result.txt'), encoding='utf-8').read()
    m = re.search(r"raw agreement:\s*([\d.]+)\s+Cohen's kappa:\s*(\S+)", t)
    A("  %-34s raw agreement %s   kappa %s" % (name, m.group(1), 'not defined (a single category)' if m.group(2) == 'nan' else m.group(2)))

if DRY:
    print("\n".join(out))
    print("\n[--dry] nothing was written.")
    sys.exit(0)
with open(OUT_CSV, 'w', newline='', encoding='utf-8') as fh:
    fields = ['procedure', 'analysis', 'TP', 'FP', 'FN', 'TN'] + ['%s%s' % (k, s) for k in ('sensitivity', 'especificidad', 'VPP') for s in ('', '_li', '_ls')]
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    w.writerows(csv_rows)
with open(OUT_RAY, 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['work', 'record_id', 'type', 'year', 'title', 'class'])
    for o, xs in sorted(lost):
        for x in sorted(xs):
            w.writerow([o, x, RP[x].get('type', ''), RP[x].get('year', ''), (RP[x].get('title') or '')[:200], lost_class[o]])
open(OUT_TXT, 'w', encoding='utf-8').write("\n".join(out) + "\n")
print("\n".join(out))
