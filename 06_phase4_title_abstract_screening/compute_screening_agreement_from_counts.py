"""Cohen's kappa of the two-reader title and abstract screening (phase 4) from the 2 x 2 counts
read in the Rayyan interface before the conflicts were resolved.

The per-reader decisions were not exported before conflict resolution, so the deposited exports
(rayyan_exports/by_reviewer) hold only the resolved decisions and the kappa cannot be recomputed
from them. The four cell counts below were written down by a team member from the Rayyan
conflicts view and are the only record of the independent decisions. Same formulas as
04_phase2_calibration/compute_calibration_kappa.py (asymptotic standard error of Fleiss, Cohen and
Everitt, 1969).

Usage: python3 -I -B 06_phase4_title_abstract_screening/compute_screening_agreement_from_counts.py
Writes rayyan_exports/screening_agreement_two_readers_<date>.txt without overwriting.
"""
import datetime, math, os, sys

D = '06_phase4_title_abstract_screening'
# Counts recorded from Rayyan (both readers, blinded, "maybe" counted as inclusion).
BOTH_INCLUDE = 8752
BOTH_EXCLUDE = 11555
R1_INCLUDE_R2_EXCLUDE = 848
R1_EXCLUDE_R2_INCLUDE = 1248
RECORDED_BY = 'team member, from the Rayyan conflicts view, before conflict resolution'
RECORDED_TOTALS = {'reviewer_1': (9600, 12803), 'reviewer_2': (10000, 12403)}  # (include, exclude)

n = BOTH_INCLUDE + BOTH_EXCLUDE + R1_INCLUDE_R2_EXCLUDE + R1_EXCLUDE_R2_INCLUDE
r1_inc = BOTH_INCLUDE + R1_INCLUDE_R2_EXCLUDE
r2_inc = BOTH_INCLUDE + R1_EXCLUDE_R2_INCLUDE
assert (r1_inc, n - r1_inc) == RECORDED_TOTALS['reviewer_1'], 'reviewer_1 totals do not match the cells'
assert (r2_inc, n - r2_inc) == RECORDED_TOTALS['reviewer_2'], 'reviewer_2 totals do not match the cells'

# p[i][j]: i = reviewer_2 (0 include, 1 exclude), j = reviewer_1
p = [[BOTH_INCLUDE / n, R1_EXCLUDE_R2_INCLUDE / n], [R1_INCLUDE_R2_EXCLUDE / n, BOTH_EXCLUDE / n]]
row = [p[0][0] + p[0][1], p[1][0] + p[1][1]]
col = [p[0][0] + p[1][0], p[0][1] + p[1][1]]
po = p[0][0] + p[1][1]
pe = sum(row[i] * col[i] for i in range(2))
kappa = (po - pe) / (1 - pe)
t1 = sum(p[i][i] * (1 - (row[i] + col[i]) * (1 - kappa)) ** 2 for i in range(2))
t2 = (1 - kappa) ** 2 * sum(p[i][j] * (col[i] + row[j]) ** 2 for i in range(2) for j in range(2) if i != j)
t3 = (kappa - pe * (1 - kappa)) ** 2
se = math.sqrt(max(t1 + t2 - t3, 0) / n) / (1 - pe)
li, ls = kappa - 1.96 * se, kappa + 1.96 * se
disagree = R1_INCLUDE_R2_EXCLUDE + R1_EXCLUDE_R2_INCLUDE

now = datetime.datetime.now()
out = os.path.join(D, 'rayyan_exports', 'screening_agreement_two_readers_%s.txt' % now.strftime('%Y%m%d_%H%M%S'))
if os.path.exists(out):
    sys.exit('exists: ' + out)
lines = [
    "Cohen's kappa of the two-reader title and abstract screening (phase 4). %s, Colombia time." % now.strftime('%Y-%m-%d %H:%M'),
    '',
    'Source of the counts: %s. The per-reader decisions were not exported before the conflicts' % RECORDED_BY,
    'were resolved; the deposited exports hold only the resolved decisions (22,203 works of the frame,',
    '9808 included). The counts below total %d records, 200 more than the 22,203 works of the frame' % n,
    'prepared on 2026-10-14; the difference equals the 200 calibration works, which the two readers had',
    'also decided (calibration_CAL1_final_decisions.csv). "Maybe" counts as inclusion.',
    '',
    '                    reviewer_1 includes  reviewer_1 excludes  total reviewer_2',
    '  reviewer_2 includes  %13d  %13d  %13d' % (BOTH_INCLUDE, R1_EXCLUDE_R2_INCLUDE, r2_inc),
    '  reviewer_2 excludes  %13d  %13d  %13d' % (R1_INCLUDE_R2_EXCLUDE, BOTH_EXCLUDE, n - r2_inc),
    '  total reviewer_1     %13d  %13d  %13d' % (r1_inc, n - r1_inc, n),
    '',
    'Observed agreement: %.3f (%d of %d). Agreement expected by chance: %.3f.' % (po, BOTH_INCLUDE + BOTH_EXCLUDE, n, pe),
    "Cohen's kappa: %.3f. 95 %% CI: %.3f to %.3f (asymptotic standard error of Fleiss, Cohen and Everitt, 1969)." % (kappa, li, ls),
    'Discrepancies: %d (%.1f %%; reviewer_1 includes and reviewer_2 excludes: %d; reviewer_1 excludes and reviewer_2 includes: %d),'
    % (disagree, 100 * disagree / n, R1_INCLUDE_R2_EXCLUDE, R1_EXCLUDE_R2_INCLUDE),
    'resolved by consensus of the pair or by the block arbiter (screening_plan_2026-10-13.md).',
    '',
    'Script: %s' % os.path.basename(__file__),
]
open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
print('\nWritten:', out)
