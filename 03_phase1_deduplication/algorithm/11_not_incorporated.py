# -*- coding: utf-8 -*-
"""Phase 0 records that did not reach the imported corpus (rule R4) and their deduplication.

  python3 algorithm/11_not_incorporated.py [--dry]

1. Extracts from the exports the records whose reconciliation key (valid DOI or
   normalised title plus year, the same as reconcile_sources.py) is not in the raw
   corpus: LILACS non_clinical_matrices.ris and VIP_VIP-1_chinese_159_2026-09-11.ris. The
   Wanfang .txt file is the same VIP sweep in another format and is not used.
2. Gives them a stable identifier, p0nc-<source>-<position in the file>, and
   normalises them with the functions of 01, 02 and 05, without copying them.
3. Builds the candidate pairs with the four blocking keys, against the corpus and
   among themselves, and scores them with the function and thresholds of 05.
4. All candidate pairs go to double, blind human reading: there is no model in this
   stretch, and no merge happens without a human judgement (principle P1).

Writes (overwrites nothing):
  02_phase0_raw_corpus/not_incorporated/not_incorporated_n<N>_<date>.ris and .csv
  03_phase1_deduplication/work/records_not_incorporated.pkl
  03_phase1_deduplication/work/not_incorporated_pairs.csv
  03_phase1_deduplication/work/not_incorporated_queue_blind.csv and _key.csv
  03_phase1_deduplication/work/adjudication_rules_not_incorporated.csv (rule RC-1)
The reading sheets are generated afterwards with 08_make_review_sheets.py.
"""
import os, re, sys, csv, json, pickle, random, itertools, collections, datetime

DRY = '--dry' in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
D1 = os.path.dirname(HERE)
ROOT = os.path.dirname(D1)
WORK = os.path.join(D1, 'work')
DATE = datetime.date.today().isoformat()
SEED = 424242
FUENTES = (('LILACS', '01_search/exports/LILACS/Non_clinical_matrices/non_clinical_matrices.ris'),
           ('VIP', '01_search/exports/VIP/VIP_VIP-1_chinese_159_2026-09-11.ris'))

def functions(path, cutoff, extra=None):
    ns = dict(extra or {}); ns['__file__'] = path
    exec(compile(open(path, encoding='utf-8').read().split(cutoff)[0], path, 'exec'), ns)
    return ns
rec = functions(os.path.join(ROOT, '02_phase0_raw_corpus/reconciliation/reconcile_sources.py'), 'print("reading corpus...", file=sys.stderr)')
f01 = functions(os.path.join(HERE, '01_parse_and_block.py'), "print('parsing', SRC, flush=True)")
f02 = functions(os.path.join(HERE, '02_build_pairs.py'), "n_placeholder = n_multi = 0")
f05 = functions(os.path.join(HERE, '05_score_and_fit.py'), "recs  = pickle.load(")

# 1. absent records
text = open(os.path.join(ROOT, '02_phase0_raw_corpus/raw_corpus_n47644_2026-09-28.ris'), encoding='utf-8', errors='replace').read()
keys = [rec['keys_from'](r, 'ris') for r in rec['recs_ris'](text)]
CD = {d for d, t in keys if d}; CT = {t for d, t in keys if t}
absent = []
for source, rel in FUENTES:
    rs = rec['recs_ris'](open(os.path.join(ROOT, rel), encoding='utf-8', errors='replace').read())
    for i, r in enumerate(rs, 1):
        d, t = rec['keys_from'](r, 'ris')
        if not ((d and d in CD) or (t and t in CT)):
            absent.append(('p0nc-%s-%04d' % (source, i), source, os.path.basename(rel), i, r))
N = len(absent)

# 2. normalisation with the functions of the pipeline
first = lambda d, *t: next((d[x][0] for x in t if d.get(x)), '')
new = {}
for rid, source, arch, i, d in absent:
    title = first(d, 'TI', 'T1')
    doi = f01['norm_doi'](first(d, 'DO'))
    if not doi:
        for u in d.get('UR', []):
            if 'doi.org/' in u:
                doi = f01['norm_doi'](u.split('doi.org/')[-1]); break
    au = d.get('AU', []) or d.get('A1', [])
    r = {'id': rid, 'type': first(d, 'TY'), 'title': title, 'tnorm': f01['norm'](title),
         'year': re.sub(r'\D', '', first(d, 'Y1', 'PY'))[:4], 'authors': au,
         'a1': f01['surname'](au[0]) if au else '', 'journal': f01['norm'](first(d, 'T2', 'JO', 'J2')),
         'vol': f01['norm'](first(d, 'VL')), 'issue': f01['norm'](first(d, 'IS')),
         'sp': f01['norm'](first(d, 'SP')), 'doi': doi,
         'issn': re.sub(r'[^0-9xX]', '', first(d, 'SN')).lower(), 'lang': first(d, 'LA'),
         'source': source, 'source_file': arch, 'source_index': i}
    r['dois'] = f02['doi_list'](r['doi'])
    new[rid] = r

# 3. candidate pairs and scoring
corpus = pickle.load(open(os.path.join(WORK, 'records.pkl'), 'rb'))
all_ = dict(corpus); all_.update(new)
blocks = {k: collections.defaultdict(list) for k in 'ABCD'}
for r in all_.values():
    for x in r.get('dois') or []: blocks['A'][x].append(r['id'])
    if r['a1'] and r['year']: blocks['B'][r['a1'] + '|' + r['year']].append(r['id'])
    if len(r['tnorm']) >= 10: blocks['C'][r['tnorm'][:60]].append(r['id'])
    if r['issn'] and r['vol'] and r['sp']: blocks['D'][r['issn'] + '|' + r['vol'] + '|' + r['sp']].append(r['id'])
pairs = collections.defaultdict(set)
for k, idx in blocks.items():
    for members in idx.values():
        m = sorted(set(members))
        if len(m) > 1 and any(x in new for x in m):
            for a, b in itertools.combinations(m, 2):
                if a in new or b in new:
                    pairs[(a, b)].add(k)
TH = json.load(open(os.path.join(WORK, 'thresholds.json'), encoding='utf-8'))
TOK = {x: f05['tokens'](all_[x].get('title', '')) for p in pairs for x in p}
rows = []
for n, ((a, b), ks) in enumerate(sorted(pairs.items()), 1):
    s = f05['score'](all_[a], all_[b], TOK)
    alg = 'DUPLICATE' if s > TH['tau_high'] else ('DIFFERENT' if s < TH['tau_low'] else 'DOUBTFUL')
    rows.append({'pair_id': 'N%04d' % n, 'id_1': a, 'id_2': b, 'keys': ''.join(sorted(ks)), 'score': '%.6f' % s,
                  'shares_doi': 'yes' if 'A' in ks else 'no', 'algorithm': alg,
                  'type': 'new-new' if (a in new and b in new) else 'new-corpus'})

print('records not incorporated:', N, dict(collections.Counter(r['source'] for r in new.values())))
print('records with at least one candidate pair:', len({x for p in pairs for x in p if x in new}))
print('candidate pairs:', len(rows), '|', dict(collections.Counter((f['type'], f['algorithm']) for f in rows)))
COMP = re.compile(r'\.(s|t|g)\d{3}$')
def type_rc1(f):
    da, db = (all_[f['id_1']].get('doi') or '').lower(), (all_[f['id_2']].get('doi') or '').lower()
    if not any(COMP.search(x) or x.startswith('10.6084/m9.figshare') for x in (da, db)) or (da and da == db):
        return None
    if COMP.search(da) or COMP.search(db):
        return 'component_same_article' if COMP.sub('', da) == COMP.sub('', db) else 'component_other_article'
    return 'figshare_deposit'
rc1 = [f for f in rows if type_rc1(f)]
print('pairs covered by rule RC-1:', len(rc1))
if DRY:
    sys.exit(0)

# 4. writing, without overwriting
dest = os.path.join(ROOT, '02_phase0_raw_corpus', 'not_incorporated')
outputs = [os.path.join(dest, 'not_incorporated_n%d_%s.ris' % (N, DATE)), os.path.join(dest, 'not_incorporated_n%d_%s.csv' % (N, DATE)),
           os.path.join(WORK, 'records_not_incorporated.pkl'), os.path.join(WORK, 'not_incorporated_pairs.csv'),
           os.path.join(WORK, 'not_incorporated_queue_blind.csv'), os.path.join(WORK, 'not_incorporated_queue_key.csv'),
           os.path.join(WORK, 'adjudication_rules_not_incorporated.csv')]
ya = [p for p in outputs if os.path.exists(p)]
if ya:
    sys.exit('ERROR: they already exist; nothing is overwritten:\n  ' + '\n  '.join(ya))
os.makedirs(dest, exist_ok=True)
with open(outputs[0], 'w', encoding='utf-8') as fh:
    for rid, source, arch, i, d in absent:
        fh.write('TY  - %s\n' % first(d, 'TY'))
        fh.write('AN  - %s\n' % rid)
        for tag, vals in d.items():
            if tag in ('TY', 'AN', 'ER'): continue
            for v in vals: fh.write('%s  - %s\n' % (tag, v))
        fh.write('ER  - \n\n')
with open(outputs[1], 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh); w.writerow(['id', 'source', 'file', 'position_in_file', 'type', 'title', 'year', 'doi'])
    for rid, source, arch, i, d in absent:
        r = new[rid]; w.writerow([rid, source, arch, i, r['type'], r['title'], r['year'], r['doi']])
pickle.dump(new, open(outputs[2], 'wb'), protocol=4)
with open(outputs[3], 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=['pair_id', 'id_1', 'id_2', 'keys', 'score', 'shares_doi', 'algorithm', 'type'])
    w.writeheader(); w.writerows(rows)
def side(rid):
    r = all_[rid]; au = r.get('authors', [])
    return {'title': (r.get('title') or '')[:300], 'authors': '; '.join(au[:5]) + (' et al.' if len(au) > 5 else ''),
            'year': r.get('year', ''), 'journal': r.get('journal', ''), 'vol': r.get('vol', ''), 'num': r.get('issue', ''),
            'pag': r.get('sp', ''), 'doi': '; '.join(r.get('dois', [])), 'type': r.get('type', ''), 'issn': r.get('issn', '')}
FIELDS = ['title', 'authors', 'year', 'journal', 'vol', 'num', 'pag', 'doi', 'type', 'issn']
rnd = random.Random(SEED); order = list(range(len(rows))); rnd.shuffle(order)
with open(outputs[4], 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['row', 'pair_id'] + ['a_' + c for c in FIELDS] + ['b_' + c for c in FIELDS] + ['human_judgement', 'reviewer', 'date', 'note'])
    for k, j in enumerate(order, 1):
        f = rows[j]; a, b = side(f['id_1']), side(f['id_2'])
        w.writerow([k, f['pair_id']] + [a[c] for c in FIELDS] + [b[c] for c in FIELDS] + ['', '', '', ''])
with open(outputs[5], 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh); w.writerow(['pair_id', 'stratum', 'score', 'keys', 'shares_doi', 'algorithm', 'model', 'layer'])
    for f in rows:
        w.writerow([f['pair_id'], f['type'], f['score'], f['keys'], f['shares_doi'], f['algorithm'], 'NOT_RUN', 'P0NC'])
with open(outputs[6], 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh); w.writerow(['pair_id', 'layer', 'type', 'doi_a', 'doi_b', 'rule_judgement', 'rule'])
    for f in rc1:
        w.writerow([f['pair_id'], 'P0NC', type_rc1(f), (all_[f['id_1']].get('doi') or '').lower(),
                    (all_[f['id_2']].get('doi') or '').lower(), 'DIFFERENT_WORKS', 'RC-1'])
for p in outputs: print('written', os.path.relpath(p, ROOT))
