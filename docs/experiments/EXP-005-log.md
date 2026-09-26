# EXP-005 — log and cold audits

The append-only log of
[EXP-005](EXP-005-tfm-out-of-time-second-book.md) and the cold audits of its
runs, kept apart from the pre-registration so that an auditor reads the
hypotheses and the kill criteria without the entries that read results
against them.

## Log

Append-only. Date, what was run, what was observed, pointer to the run
directory. No conclusion without a pointer.

### 2026-09-13 — the grid and the matrix, before any model

Three runs from a clean tree at `d432210`, no model in any of them.

`experiments/2026-09-13-fm-vintage-builds` (78 s). The book after the
re-dated and unrecorded loans: 1,355,395 of 1,362,500. Excluded from
labelling: 25,159 loans first observed after age 3 and 190 whose record
has a gap, 25,349 in all, against the 25,315 this file states; the pools
move with it. Arm E: nine builds, 234 cells, 196 above the floors, pools
79,501 (2002H2) to 856,721 (2018H2) against the stated 79,532 to 856,817.
Arm R: eight builds, 192 cells, 160 above the floors, pools 95,562 to
99,152 against the stated 95,582 to 99,160; 2002H2-R is not a build, its
eight-quarter window reaching before 1999Q1. No training loan's window is
open at any build date. Blind-gap loans whose own window had closed, the
cost of cutting on whole quarters: 3,800 to 4,699 per build. Scored loans
whose pre-HARP identifier names a training loan of the build, the lower
bound on borrower overlap: 0 to 1,313 on arm E, largest at 2010H2 and
2008H2 (1,313 and 918), 0 to 609 on arm R. The cells, the floors and the
six floor-failing half-years are the ones this file names.
`build-grid.png`: the training rate against every scored cohort's rate,
one panel per build, the regimes drawn.

`experiments/2026-09-13-fm-features` (78 s). Fourteen columns kept, as the
note of 2026-09-13 states; the clause that removes each other column is in
`gates.json` and on `dropped-columns.png`, one panel per column with its
offending share by origination half-year. Clip ranges: `upb` 19,000 to
461,000, `fico` 601 to 826, `cltv` and `ltv` 6 to 100, `term` 96 to 360,
`mi_pct` 0 to 35, `units` 1 to 4, `borrowers` 1 to 2.

`experiments/2026-09-13-fm-features-dti-kept` (114 s). The ablation's
matrix: the fourteen and `dti`, clipped to 2 to 50, its missing values a
level.

The counts this file states before the run are superseded by these; no
cell, floor verdict or build changes.

### 2026-09-13, later — the grid and the matrix recorded again

The same three runs and the second ablation, from a clean tree at
`de586ec`, under the note of 2026-09-13 (later); they supersede the three
above.

`experiments/2026-09-13-fm-vintage-builds2`. Excluded from labelling:
25,159 loans first observed after age 3, as before, and 49 whose record
misses a month inside the window, where the rule read at any age excluded
190. The 141 loans that rule no longer excludes are labelled: pools on arm
E 79,511 (2002H2) to 856,861 (2018H2), on arm R 95,615 to 99,162; 81 of
the 426 cells gain up to 21 labelled loans and 56 of them up to 6
defaults. The blind gap gains the same loans where they fall inside it,
up to 61 a build (2006H2). Builds, cells, floor verdicts, regimes, ages and
pre-HARP links are those of the first recording.

`experiments/2026-09-13-fm-features2`. Fourteen columns, `upb_to_limit` in
place of `upb`, clipped to 14,000/240,000 to 461,000/240,000 of the limit;
every other drop and clip as before. The share of variance between cells
of first payment month and term: rate 0.931, `upb` 0.250, `ltv` 0.122,
`cltv` 0.117, `mi_pct` 0.100, `fico` 0.096, `upb_to_limit` 0.068,
`borrowers` 0.028, `units` 0.005; `term` is one of the two dimensions of
the cells and reads 1.0 by construction. `loan-amount.png`: the median and
the 90th percentile of both forms by origination half-year, and the share
of each cohort each clip pins — up to 19% of a cohort for the nominal
amount from 2020, under 1% for the ratio everywhere.

`experiments/2026-09-13-fm-features-dti-kept2`: the fifteen columns, the
fourteen above and `dti` clipped to 2 to 50.
`experiments/2026-09-13-fm-features-upb-nominal`: the fourteen with `upb`
in nominal dollars, clipped to 19,000 to 461,000, in place of the ratio.

### 2026-09-13, later — the falsifying run's classical side and its bundles

From a clean tree at `dc50bdc`, on 2004H2-E, the primary matrix and both
ablations: `experiments/2026-09-13-fm-2004h2e-scores`, `…-scores-dti-kept`
and `…-scores-upb-nominal` (326 to 345 s each), the scorecard, the full
GBM and GBM-50k on three context seeds, every one of the build's 38
half-year cohorts scored whole (23,169 to 24,929 rows, 931,123 in all);
pool 176,092 labelled rows over 1999Q1 to 2002Q3, blind gap 108,929.
The halt this file sets: the scorecard's AUC on 2005H1 (24,233 rows, 248
defaults) is 0.8107 on the primary matrix, 0.8097 with `dti` and 0.8113
with the nominal amount, above the 0.70 below which the matrix or the
label would be taken as broken; the grid is not halted. No other
statistic of these runs is read here; they are read with the
foundation-model cells.

`experiments/2026-09-13-fm-2004h2e-bundle`, `…-bundle-dti-kept`,
`…-bundle-upb-nominal` (179 to 183 s each): the three contexts of 50,000
rows and the 38 cohorts, every row and outcome identical to the score run
of the same matrix. Row-level files stay on the machine
(`.gitignore`, ADR-0007); the records and bundle descriptions are here.

### 2026-09-14 — the device's tier and both sides of the grid

*The probe and the tier.* The one-hour probe on a rented RTX 4090 scored
the Lending Club 2015H1-E bundle with both foundation models at both
temperatures (`experiments/2026-09-13-lc-rental-probe-4090` and its four
job directories). `experiments/2026-09-13-fm-grid-budget`, the rule run
with `--probe` over those four directories on a clean tree at `001b24b`,
reads `s_I` = 3.757 × 10⁻⁴ and `s_P` = 7.026 × 10⁻⁴ seconds per row. The
walls it computes are 11.51 h full, 6.97 h derived and 5.76 h for the
rolling arm, so it selects rule 1: TabPFN scored at both temperatures on
the expanding arm, the rolling arm's foundation-model cells on the device,
17.27 device hours, H4 tested. Each timing was taken twice, the two
temperatures of a model being two passes over the same rows: TabPFN
97.5 s and 96.4 s of wall, TabICL 58.5 s and 55.0 s. This book's rows
score slower on the same device than the rows the rule was read on.
Pooled over the falsifying run's three matrices: 879 µs a row for TabPFN
and 452 for TabICL; the probe's 703 and 376 make ratios of 1.25 and
1.20, the rule's margin being 25%. The tier is the probe's, as the rule
is written.

*The falsifying run's foundation-model cells.*
`experiments/2026-09-13-fm-2004h2e-rental-4090` and its twelve job
directories: TabPFN and TabICL at 0.9 and at 1.0 on the three bundles of
2004H2-E, context seed 20260911, the cohorts 2005H1, 2005H2 and 2006H1
and the 50,000 context rows, 71,595 scored rows a job. Every scored and
context row, with its outcome, is the score run's of the same matrix.
The first cohort scored a second time from a fresh fit agrees to 0.0 on
every job. The libraries are tabpfn 8.5.0 and tabicl 2.1.1 on torch
2.14.0, CUDA.

TabICL's derivation, checked before any statistic is read from it as the
Setting requires: `derive_temperature.py` over the three TabICL
directories at 0.9, each checked against its matrix's directory scored at
1.0, on a clean tree at `0c1f005`
(`experiments/2026-09-14-fm-2004h2e-tabicl-t1-derived`,
`…-dti-kept-tabicl-t1-derived`, `…-upb-nominal-tabicl-t1-derived`). On
every one of the 121,595 rows of each matrix the derived probability is
within 1.7 × 10⁻⁷ of the scored one, 1.4 × 10⁻⁶ on the logit, against a
tolerance of 10⁻⁶ on the probability. The grid's sixteen other builds
carry no TabICL cell scored at 1.0; the check available to them is these
cells, scored by the same library with the same checkpoint on the same
device, and the script does not accept a check drawn from another build.
No grid row at 1.0 is derived here.

*The classical side of the grid.* From a clean tree at `001b24b`, the
sixteen builds beside 2004H2-E, eight on each arm: a score run per build
(212 s to 837 s) and a bundle per build whose context and cohort rows are
the score run's row for row (165 s to 198 s). The `dti_kept` and
`upb_nominal` score runs of every build: 228 s to 1,041 s and 220 s to
608 s. Every cohort is scored whole, and on every build the scored rows
and the number of cohorts are those of the build run's `cells.csv`. The
rows one pass of a model scores: 5,754,776 on arm E and 4,726,863 on arm
R, superseding the Setting's 5,754,654 and 4,726,804. Aggregates, build
records and bundle descriptions are committed. The rows are not.

*The grid on the device.* `experiments/2026-09-14-fm-grid-rental-4090`
and its 43 job directories: TabICL and TabPFN at 0.9 on all seventeen
bundles, TabPFN at 1.0 on the nine of arm E, three context seeds, every
cohort. 67,011.6 s of scoring in one process, 18.61 h against the 17.27 h
the rule projected. That is 8% over, inside its margin. The rows are
checked as on the falsifying run: 3,387 parts, 80,154,162 scored and
6,450,000 context rows, no mismatch against the score run or the bundle,
no probability missing or outside [0, 1]; python 3.12.3, torch 2.14.0,
tabpfn 8.5.0, tabicl 2.1.1 and the same two checkpoints on every job. On
2004H2-E the grid's cells of seed 20260911 are the falsifying run's to
the bit: none of the 121,595 rows differs, for each of the three passes.

123 of the 129 repeat cells agree to 0.0. The six that do not are
TabICL's first cohort on two rolling-arm builds, on each of the three
seeds: 2017H1 on 2016H2-R, 4,316 to 4,360 rows differing and at most
1.7 × 10⁻⁴ on the probability; 2019H1 on 2018H2-R, 4,648 to 4,695 rows
and at most 1.03 × 10⁻³; the mean difference 0.9 × 10⁻⁶ to 3.6 × 10⁻⁶.
The same cohorts on 2016H2-E and 2018H2-E repeat exactly, as does every
TabPFN pass on either arm. A second full pass of TabICL on the two
builds, in a fresh process
(`experiments/2026-09-14-fm-2016h2r-tabicl-rerun-rental-4090`,
`…-2018h2r-tabicl-rerun-rental-4090`), returns the recorded rows exactly,
context rows included; the first pass's repeat values are reproduced
exactly too. So a fresh process reproduces the rows every statistic will
be read on. What moves is a second scoring of the first cell inside the
same process, on these two contexts only. The cause is not measured.

What is not here. Any statistic of a foundation model on this book. The
falsifying run is read when the scripts for the ablation's difference of
gains and for the in-sample level exist, and before its cold audit; the
grid's intervals follow both. TabICL at 1.0 on the grid's builds, and
TabPFN at 1.0 on the rolling arm, which rule 4 derives.

### 2026-09-14, later — the falsifying run read

From a clean tree at `960c3b5`: `experiments/2026-09-14-fm-2004h2e-intervals`
and its `-dti-kept` and `-upb-nominal` siblings, the two ablations'
difference of gains (`…-ablation-dti-kept`, `…-ablation-upb-nominal`) and
the in-sample level (`…-in-sample`). The three cohorts nearest the build
pooled, 2005H1, 2005H2 and 2006H1, under context draw 20260911; bootstrap
seed 20260905, checked under 20260906 and 20260907. Every interval here is
conditional on the one draw.

*Ranking.* On Gini neither foundation model differs from the scorecard:
TabPFN +0.0022 [−0.0077, +0.0108], TabICL −0.0011 [−0.0108, +0.0088].
Both rank above GBM, +0.0195 and +0.0162, and above GBM-50k, +0.0295 and
+0.0262, each of the four intervals excluding zero.

*Level.* On its own context at 0.9, TabPFN's observed over expected is
1.416 [1.308, 1.530] and TabICL's 1.403 [1.296, 1.516], the binomial
interval: the context's realised rate is 1.26% and the mean probabilities
0.89% and 0.90%. At 1.0 the two read 0.980 and 0.972; the classical models
read 0.994 to 1.000 on their own rows. Out of time the gap stays: pooled
|log O/E| minus the scorecard's is +0.201 [+0.108, +0.233] for TabPFN and
+0.180 [+0.086, +0.212] for TabICL at 0.9, and holds zero at 1.0.

*H2 at age zero.* |Cox slope − 1| minus the scorecard's, at 0.9: TabPFN
+0.014 [−0.004, +0.033], TabICL +0.023 [+0.002, +0.042]. At 1.0 both sit
below the scorecard's, TabPFN −0.078 and TabICL −0.068, both intervals
excluding zero.

*Stability.* PSI minus the scorecard's: TabICL +0.0081, TabPFN +0.0039,
GBM-50k +0.0028, each excluding zero; GBM holds zero.

*The ablations.* `dti_kept` does not fire: for both foundation models at
0.9 the difference of gains against GBM-50k holds zero on AUC and on
Brier. `upb_nominal` fires on Brier for both, TabPFN +5.77 × 10⁻⁵
[+3.39 × 10⁻⁵, +8.58 × 10⁻⁵] and TabICL +6.26 × 10⁻⁵ [+3.66 × 10⁻⁵,
+9.13 × 10⁻⁵], starred under all three bootstrap seeds; on AUC both hold
zero. The nominal amount makes both foundation models worse on Brier,
+2.91 × 10⁻⁵ and +3.39 × 10⁻⁵, and GBM-50k better, −2.86 × 10⁻⁵, each
excluding zero. The difference of gains is about half a percent of a
Brier score of 0.0125.

### 2026-09-14, later — `upb_nominal` over three context draws

The interval above is conditional on one draw of GBM-50k's context.
TabPFN and TabICL scored 2004H2-E's `upb_nominal` bundle under draws
20260912 and 20260913 on the same three cohorts and the context rows, on
a rented RTX 4090
(`experiments/2026-09-14-fm-2004h2e-upb-nominal-{tabpfn,tabicl}-draws-rental-4090`,
hand manifests): every scored and context row with its outcome is the
score run's and the bundle's, and the first cohort scored a second time
from a fresh fit agrees to 0.0 on each draw. `ablation_intervals.py
--cohorts` pairs them with the primary grid's cells of the build under the
same draws (`experiments/2026-09-14-fm-2004h2e-ablation-upb-nominal-draws`,
clean tree at `b1da1a9`), the draw resampled with the bootstrap as the
Setting has it.

The trigger fires on Brier for both foundation models and for no other
model, under all three seeds: TabPFN +6.30 × 10⁻⁵ [+2.5 × 10⁻⁵,
+1.05 × 10⁻⁴], TabICL +6.19 × 10⁻⁵ [+2.0 × 10⁻⁵, +1.02 × 10⁻⁴]. The
scorecard's row, +3.49 × 10⁻⁵, and GBM's, +1.16 × 10⁻⁵, hold zero, as
does every row on AUC. The foundation models' own change stays worse,
+2.76 × 10⁻⁵ and +2.64 × 10⁻⁵, each excluding zero; GBM-50k's,
−3.54 × 10⁻⁵, holds zero over the three draws.

The consequence the note of 2026-09-13 (later) fixes follows: the
foundation-model grid runs on the nominal matrix as well, and every
verdict is reported on both, the ratio's reading being the criterion's.
That grid scores TabICL and TabPFN at 0.9 on all seventeen bundles and
nothing at 1.0, and the reading of TabPFN's rows at 1.0 on that matrix is
fixed here, before any of them exists: they are derived by rule 2's
formula under the note of 2026-09-14, the error measured per cell and
printed beside every statistic that reads them, a cell above 8.4 × 10⁻³
refused. The only cells scored at 1.0 on that matrix are the falsifying
run's on 2004H2-E
(`experiments/2026-09-13-fm-2004h2e-upb-nominal-tabpfn-t1-rental-4090`),
three cohorts and the context under one draw, so the check of every
build, 2004H2-E's own included, is made on those cells and their error is
what is carried — a narrower check than the primary grid's, where every
expanding-arm build holds its own rows scored at 1.0. No criterion reads a
statistic at 1.0 on the nominal matrix: the criterion reads 0.9, and it
reads the ratio.

### 2026-09-15 — the grid on the nominal matrix

`experiments/2026-09-15-fm-grid-upb-rental-4090` and its 34 job
directories
(`experiments/2026-09-15-fm-<build>-upb-nominal-{tabicl,tabpfn}-rental-4090`):
TabICL and TabPFN at 0.9 on the seventeen `upb_nominal` bundles
(`c44985a`), three context draws, every cohort, on a rented RTX 4090.
49,481.2 s of scoring in one process, 13.7 h. The rows are checked as on
the primary grid: 2,658 parts, 62,889,834 scored and 5,100,000 context
rows, no mismatch against the `upb_nominal` score run or the bundle, no
probability missing or outside [0, 1]. On 2004H2-E the grid's cells are
the ones scored earlier on the same bundle, to the bit: the falsifying
run's under draw 20260911 and the two further draws', none of the 24 parts
differing on any row.

The node's image had moved since the primary grid: python 3.12.14 in place
of 3.12.3, a newer kernel, and driver 615.71.09 in place of 595.58.03
(`gpu.txt` of the index); torch 2.14.0, tabpfn 8.5.0, tabicl 2.1.1,
CUDA 13.0 and the two checkpoints are the same on every job. The identity
on 2004H2-E spans that change for draw 20260911, whose cells were scored on
the earlier image; the two further draws were scored on this one.

99 of the 102 repeat cells agree to 0.0. The three that do not are
TabICL's first cohort on 2018H2-R, 2019H1, one per draw: 4,566 to 4,679
rows differing, at most 1.35 × 10⁻³ on the probability, the mean
difference 1.3 × 10⁻⁶ to 3.6 × 10⁻⁶ — one of the two cells that moved on
the primary grid. 2017H1 on 2016H2-R, which moved there, repeats exactly
here.

### 2026-09-15 — two statements of this file corrected

- The Setting puts the Yurdakul critical value at 24,000 scored rows
  against a 50,000-row reference near 0.0015. At ten bins and α = 0.05 it
  is 0.00104 (`psi_critical_value(24000, 50000, 10)` of `psi-inference`).
  What the sentence says of it stands: every real movement of the book
  crosses it.
- The note of 2026-09-14 names eight trigger rows, the two foundation
  models at 0.9 on AUC and Brier for each ablation. `ablation_intervals.py`
  counted the rows at 1.0 as well, so `summary.json` of
  `…-ablation-dti-kept` lists `tabicl@t1` and `tabpfn@t1` on Brier among
  the rows excluding zero, and that of `…-ablation-upb-nominal` lists them
  beside the two that fired. Those four rows are outside the rule and fire
  nothing. From `9b84a0b` the script counts the eight; the two entries
  above read the eight.

### 2026-09-15 — the grid's rows at 1.0

From a clean tree at `7a7a798`, 34 recorded runs of `derive_temperature.py`
(`experiments/2026-09-15-fm-<build>-{tabicl-t1-derived,tabpfn-t1-measure,tabpfn-t1-derived}`;
2004H2-E's TabICL run is `…-2004h2e-grid-tabicl-t1-derived`). TabICL at
1.0 on all seventeen builds by the exact scale: 2004H2-E's rows checked
against its cells scored at 1.0, 121,595 of its 2,943,369 rows, the other
sixteen carried by the same check (`--check-source`); worst 1.36 × 10⁻⁷
on the probability against a tolerance of 10⁻⁶. TabPFN's rows at 1.0 on
arm E are scored, so the derivation is measured against them on the nine
builds (`--measure-only`, a `derive.json` and no rows): worst |b − 1| per
build 1.3 × 10⁻⁴ to 1.83 × 10⁻³, above the Lending Club figure of
8.4 × 10⁻⁴ on 7 of 129 cells of 2002H2-E, 8 of 93 of 2008H2-E and 1 of 81
of 2010H2-E, on no cell of the other six; derived minus scored at most
2.5 × 10⁻³ on the Cox slope and 5.2 × 10⁻³ on observed over expected;
every Cox fit finished. TabPFN at 1.0 on arm R is derived through the same
year's expanding build, as the note of 2026-09-14 has it, the error
carried from that build's measurement: on every one of the eight the worst
cell is within the 8.4 × 10⁻³ at which the derivation is refused.
Statistics at 1.0 read TabPFN's scored rows on arm E, as rule 1 has it,
its derived rows on arm R, as rule 4 has it, and TabICL's derived rows on
both arms; every statistic that reads derived rows is printed with the
derivation's error beside it. The criterion reads 0.9.

### 2026-09-16 — the whole grid's per-build intervals, on both matrices

`build_intervals.py` over every build of both arms, one run per build and
matrix, each with `--check-seeds 20260906,20260907` and `--cells
experiments/2026-09-13-fm-vintage-builds2/cells.csv`: seventeen runs on the
primary matrix and seventeen on `upb_nominal`, every one exit 0 on a clean
tree.

Fifteen of the primary-matrix runs carry the date 2026-09-16. The other two
are 2002H2-E and 2004H2-E, recorded on 2026-09-15 as
[`experiments/2026-09-15-fm-2002h2e-intervals-grid`](../../experiments/2026-09-15-fm-2002h2e-intervals-grid)
and
[`-2004h2e-intervals-grid`](../../experiments/2026-09-15-fm-2004h2e-intervals-grid),
and those two directories are the ones the poolings read: the expanding-arm
pooling and kill criterion 3 name both by path, the between-arm pooling
names 2004H2-E, and no pooling of the primary matrix names a 2026-09-16
directory for either build. The fifteen run from
[`-2004h2r-intervals-grid`](../../experiments/2026-09-16-fm-2004h2r-intervals-grid)
to
[`-2018h2r-intervals-grid`](../../experiments/2026-09-16-fm-2018h2r-intervals-grid).

Two machines and two commits, one script. The Windows laptop recorded
2002H2-E to 2014H2-E, the five oldest at `c599ebb` and 2012H2-E and 2014H2-E
at `1c786fe`; the Apple M4 Pro recorded 2016H2-E, 2018H2-E and all eight
rolling builds at `1c786fe`. `scripts/build_intervals.py` hashes to
`456f268f` in all thirty-four manifests, and the diff between those two
commits is recorded output alone, so no build read a different script from
any other. Walls run 662.0 s on 2018H2-R to 10,457.6 s on 2002H2-E,
69,346.9 s over the seventeen, 19.3 h.

The seventeen `upb_nominal` builds,
[`-2002h2e-intervals-grid-upb-nominal`](../../experiments/2026-09-16-fm-2002h2e-intervals-grid-upb-nominal)
to
[`-2018h2r-intervals-grid-upb-nominal`](../../experiments/2026-09-16-fm-2018h2r-intervals-grid-upb-nominal),
all ran on the Apple node at `1c786fe` over the nominal score runs and the
nominal derivations of 2026-09-15: 670.1 s to 2,766.4 s each, 27,540.3 s in
all, 7.65 h.

[`-2004h2e-intervals-apple-check`](../../experiments/2026-09-16-fm-2004h2e-intervals-apple-check)
(138.2 s, Apple node at `1c786fe`) is the falsifying reading of 2004H2-E
recorded again on the machine the grid was pooled on. Its command is that of
[`experiments/2026-09-14-fm-2004h2e-intervals`](../../experiments/2026-09-14-fm-2004h2e-intervals)
with the output directory changed and the interpreter the node's own; the
twelve library hashes agree and
`build_intervals.py` differs, `fac7ec59` against `456f268f`. The two runs
hold the same rows in the same order under the same columns — 224 of
`paired.csv`, 504 of `paired-seeds.csv`, 2,626 of `metrics.csv` — and
`excludes_zero` reads the same on every one of them. What moves is the last
bits. In `paired.csv` 54 `value` cells, 55 `ci_lo`, 57 `ci_hi` and 58 `se`
differ in the digits written, by at most 1.3 × 10⁻¹⁵ on a value, 2.1 × 10⁻¹⁵
on a bound and 8.7 × 10⁻¹⁷ on a standard error; in `metrics.csv` the largest
movement is 4.4 × 10⁻¹⁴ on a value and 4.0 × 10⁻¹³ on a bound.
`cox-not-estimable.csv` is identical once the line endings are normalised.
Of the 384 leaves of `intervals.json` none is lost, none is added and eight
change, all eight the value and the bounds of one seed-check entry, by at
most 1.3 × 10⁻¹⁵; the wall changes with them, 586.5 s to 137.6 s.

### 2026-09-16 — the two arms pooled, and the arms against each other

Four arm poolings and one between-arm pooling, all on the Apple node from a
clean tree at `1c786fe`, all exit 0.

[`experiments/2026-09-16-fm-arm-e-intervals`](../../experiments/2026-09-16-fm-arm-e-intervals)
(14,205.7 s) pools the nine expanding builds: 234 cells over 42 distinct
cohorts, 196 of them above the floors of 5,000 rows and 100 defaults;
97,831,192 scored rows on 1,027,913 distinct loans and 15,160,150 reference
rows. Its seed check over 20260906 and 20260907 reads 243 of 441 arm
differences starred under 20260905 with 25 changing their star, 1,341 of
2,961 at every scope with 103 changing, and a largest movement of an
interval bound of 0.0418.
[`-arm-r-intervals`](../../experiments/2026-09-16-fm-arm-r-intervals)
(12,310.4 s) pools the eight rolling builds: 192 cells over 38 cohorts, 160
above the floors, 80,356,671 scored rows on 931,123 distinct and 7,554,700
reference rows; 198 of 441 arm differences starred with 16 changing, 1,311
of 2,709 at every scope with 71 changing, largest bound movement 0.0819.

The `upb_nominal` twins read the same cells and the same row counts.
[`-arm-e-intervals-upb-nominal`](../../experiments/2026-09-16-fm-arm-e-intervals-upb-nominal)
(14,543.4 s) reads 215 of 441 arm differences starred with 12 changing,
1,368 of 2,961 with 85 changing, largest bound movement 0.0444;
[`-arm-r-intervals-upb-nominal`](../../experiments/2026-09-16-fm-arm-r-intervals-upb-nominal)
(12,216.0 s) reads 215 of 441 with 11 changing, 1,326 of 2,709 with 70
changing, largest bound movement 0.0822.

[`-between-arm-intervals`](../../experiments/2026-09-16-fm-between-arm-intervals)
(11,407.4 s) pairs the eight build dates the two arms share: 192 shared
cells over 38 cohorts, 160 of them entering the criterion, the cohorts
2013H1, 2014H2, 2015H1, 2020H2 and 2021H1 scored and pooled into nothing.
The seed check reads 12 of 26 pooled differences starred with 0 changing, 60
of 169 at every scope with 5 changing, and a largest bound movement of
0.0163. The run's criterion line reads, for TabPFN and for TabICL at their
library settings, "killed: inside the interval; the pre-flag and flagged
scopes disagree in sign (kill criterion 4)"; `contrast_record` is null,
the run naming no contrast file.

The two primary-matrix arm poolings and the between-arm pooling are
superseded by the runs of 2026-09-17 and 2026-09-18 below, and the criterion
line above is replaced there. The two `upb_nominal` arm poolings stand.

### 2026-09-16 — every context scored on its own rows

[`experiments/2026-09-16-fm-grid-in-sample`](../../experiments/2026-09-16-fm-grid-in-sample)
(32.9 s) and
[`-grid-in-sample-upb-nominal`](../../experiments/2026-09-16-fm-grid-in-sample-upb-nominal)
(34.9 s), `in_sample_level.py` over the 85 score, scoring and derivation
directories of each matrix, on the Apple node at `1c786fe`, both exit 0.
Each reads 289 context cells over 22,714,850 rows and 7,242 cohort cells;
the context check finds 51 draws and 204 model pairs carrying identical rows
and outcomes; the known answer holds, 85 of 85 fitted-model cells reading
one inside their bootstrap interval, on both matrices.

H5's criterion row is the observed-over-expected of an arm's highest-rate
context minus that of its lowest-rate context, at 0.9 and with the reading
at 1.0 beside it; the ends are 2010H2-E against 2006H2-E and 2010H2-R
against 2018H2-R, ranked by the build run's pool rate. On the primary matrix
the arm-E rows read gbm-50k +0.001 [−0.111, +0.103] as the known answer,
TabPFN −0.048 [−0.221, +0.097], TabPFN at 1.0 +0.020 [−0.094, +0.123],
TabICL −0.085 [−0.293, +0.093] and TabICL at 1.0 −0.002 [−0.141, +0.116].
The arm-R rows read gbm-50k +0.005 [−0.137, +0.122], TabPFN −0.355
[−0.581, −0.175] excluding zero, TabPFN at 1.0 +0.034 [−0.107, +0.148],
TabICL −0.632 [−0.897, −0.405] excluding zero and TabICL at 1.0 −0.139
[−0.302, +0.008]. On the nominal matrix no row moves by more than 0.011 and
the same two rows exclude zero. The primary-matrix run is superseded by the
recording of 2026-09-17 below; the nominal one stands.

H5 read off these rows. On the rolling arm, the tenfold range the hypothesis
names as its sharp test, the kill fires for both foundation models at the
shipped temperature: TabPFN's row, −0.355 [−0.581, −0.175], and TabICL's,
−0.632 [−0.897, −0.405], exclude zero under the primary seed and under both
check seeds, whose nearest bounds are −0.140 and −0.360; the draws rank the
two ends as the pools do, so no second ranking is reported. The level at
0.9 depends on the context's realised rate on this book, and in one
direction for both models: the shortfall is larger where the rate is lower,
1.601 and 1.731 on 2018H2-R at 0.45% against 1.246 and 1.098 on 2010H2-R at
4.48%. H5 is one criterion row per model and it fires on an arm; the verdict
for each is killed at 0.9. On the expanding arm, the weaker test over a
1.8-fold range, neither row excludes zero under any seed, −0.048 [−0.221,
+0.097] for TabPFN and −0.085 [−0.293, +0.093] for TabICL, with both models
between 1.39 and 1.47 on both ends; at intervals that wide the arm shows no
dependence, which is not the same as none. What the kill means is what the
note of 2026-09-17 in the Setting leaves it: that the level at 0.9 moves
with the rate, and nothing about why, the sentence attributing a kill to a
prior having been withdrawn there and the rescaled control of 2026-09-17
below being the demonstration. The reading at 1.0 beside the criterion
differs from it and is reported as differing. TabPFN's rolling row at 1.0,
+0.034 [−0.107, +0.148], holds zero under every seed with 1.007 against
0.974; TabICL's, −0.139 [−0.302, +0.008], holds zero at its upper bound
under the primary seed and at +0.011 and +0.049 under the check seeds, with
0.896 against 1.035 — a lower observed-over-expected on the higher-rate
context, the reverse of what a prior toward a fixed low prevalence
produces. GBM-50k's rows, +0.001 on E and +0.005 on R, hold zero as the
known answer. The nominal matrix returns the same verdict on every row:
−0.354 [−0.578, −0.177] and −0.643 [−0.918, −0.405] on the rolling arm at
0.9, starred under all three seeds; the expanding rows and the rows at 1.0
holding zero, TabICL's at 1.0 reading −0.144 [−0.312, +0.005]. The
superseding recording,
[`experiments/2026-09-17-fm-grid-in-sample`](../../experiments/2026-09-17-fm-grid-in-sample),
writes `h5.csv` and `h5-seeds.csv` byte-identical to this run's, so the
reading is that recording's as well, and it is the one cited for the
primary matrix.

### 2026-09-17 — the arm contrast, the sensitivity of H4's row, and kill criterion 3

Three short runs on the Windows laptop, each exit 0 on a clean tree.

[`experiments/2026-09-17-fm-arm-contrast`](../../experiments/2026-09-17-fm-arm-contrast)
(`fm_arm_contrast.py` at `45c6f7b`, 109.2 s) measures what the rolling
window removes at each of the nine as-of dates, for widths of 2, 4, 6, 8 and
12 quarters. At the study's eight quarters the rolling pool holds 54.9% of
the expanding pool at 2004H2 and 11.4% at 2018H2, and its mean row is 3.38
quarters younger at 2004H2 and 31.23 at 2018H2. The expanding pool runs
79,511 rows at a mean age of 2.97 quarters to 856,861 at 34.71; the rolling
pool runs 95,615 to 99,162 rows at 3.45 to 3.53. 2002H2 has no rolling build
and the file records it as the expanding pool at 100.0%.

[`-h4-sensitivity`](../../experiments/2026-09-17-fm-h4-sensitivity)
(`h4_sensitivity.py` at `4044017`, 2.5 s) reads the 2,720 criterion rows of
the between-arm pooling of 2026-09-16 and states that its recorded point
reproduces that run's `paired.csv` to 1 × 10⁻¹². It then rewrites H4's row
three further ways. Held to one context draw the row runs −0.0374 to
+0.0110 for TabPFN, −0.0284 to +0.0192 for TabICL, −0.0465 to −0.0041 for
TabPFN at 1.0 and −0.0388 to +0.0125 for TabICL at 1.0. Dropping one build
date at a time it runs −0.0349 to −0.0067, −0.0322 to +0.0058, −0.0464 to
−0.0125 and −0.0373 to +0.0043, the low on 2006H2 for all four, the high on
2018H2 for the two library-setting rows and on 2008H2 for the two at 1.0.
Replacing the control's fit by each of the 48 (build, arm, draw) fits it
runs [−0.0252, −0.0029], [−0.0122, +0.0102], [−0.0339, −0.0115] and
[−0.0190, +0.0033], with the lowest at 2008H2-E under draw 20260913 and the
highest at 2008H2-E under 20260912 on all four models. `control-fits.csv`
records those 48 fits: 2,880 to 12,834 validation rows, 15 to 243 boosting
rounds, and the point the control inherits from its build's full-pool search
differing between the arms at 8 of 8 paired build dates.

[`-kill-criterion-3`](../../experiments/2026-09-17-fm-kill-criterion-3)
(`kill_criterion_3.py` at `774fe4f`, 2.4 s) reads the nine expanding-arm
build directories — the two dated 2026-09-15 among them — and writes 153
rows, seven models by their context draws on each build. Both readings say
the same thing in the run's own words: "every model wider on 0 of 9 builds:
does not fire", under the median of the cells' widths and under the width of
the median-AUC cell alike, with `readings_agree` true. That answers the
experiment's third kill criterion, the one that would retire H1's slope for
an axis that does not resolve.

What the three sensitivities do to H4's reading. Nothing to the verdict.
The superseding pooling of 2026-09-17 below reads H4 as undetermined on
this book under kill criterion 4, and on the arm row alone as killed inside
the interval; the cells the sensitivities perturb are that pooling's to the
bit, since it reproduces the 2026-09-16 run's 432 rows with a maximum
difference of 0.0, and every point `h4_sensitivity.py` writes is a point
without an interval, so no sensitivity can show a row lying above zero
beyond one, and none recomputes the two scoped rows whose signs make the
row undetermined. What they measure is how much of the recorded point one
draw, one build date or one control fit carries. One draw carries its
sign: held to draw 20260912 the row reads +0.0110 for TabPFN and +0.0192
for TabICL, and to the other two draws −0.0374 and −0.0220, −0.0284 and
−0.0002; the pooling's own per-draw rows, cohorts resampled with the draw
held, put TabPFN below zero beyond the interval under two draws and TabICL
under one, and no draw puts either model above zero beyond it. No build
date carries it: dropped one at a time the row runs −0.0349 to −0.0067 for
TabPFN and −0.0322 to +0.0058 for TabICL, every point inside the recorded
interval, and lowest without 2006H2 on all four rows, 2006H2 being the one
date whose own row is starred on the hypothesis's side, +0.1281 [+0.0168,
+0.2135] for TabICL. One control fit moves the row by about 0.013 either
way: the 48 replacements span [−0.0252, −0.0029] for TabPFN and [−0.0122,
+0.0102] for TabICL, inside the interval on both, with the extremes on
2008H2-E under draws 20260913 and 20260912, where the control stopped at
128 rounds with a mean deviation of 0.104 over its 25 criterion cells and
at 60 rounds with 0.390, at one inherited point and 6,414 to 6,419
validation rows. The interval's width, about 0.06, is therefore mostly the
spread between the three control fits, which are also the three draws, as
the note of 2026-09-17 says of the control's own reduction. What the
sensitivities license is a description of the arm row: it holds zero, and
the sign of its point is not stable to the control's fit. What they do not
license is a sentence that the rolling window does no more for the
foundation models than for the control, since the control the row is read
against was fitted on the expanding arm with an early-stopping tail of
2,880 to 10,390 rows and its fit moves between draws by more than the
foundation models' rows do; the refit control the same note names is the
reading that separates the window from the tail, and it is not read here.
Per build against the contrast, reported and not tested: the two dates
where the rolling pool holds most of the expanding one, 2004H2 at 54.9%
and 2006H2 at 35.5%, are the two where the row is positive, +0.0171 and
+0.0686 for TabPFN, +0.0189 and +0.1281 for TabICL; from 2008H2 at 25.9% to
2018H2 at 11.4% it is negative on every date, ending at −0.1959 [−0.2940,
−0.0475] and −0.1721 [−0.3053, −0.0062]. Those four oldest paired dates are
where the pre-flag cells sit, so the per-date pattern and the disagreement
between scopes are one thing seen twice, and which of the regime, the label
and the calendar it is, the scopes cannot say.

### 2026-09-17 — the between-arm pooling with the contrast, and the reported label beside it

[`experiments/2026-09-17-fm-between-arm-intervals`](../../experiments/2026-09-17-fm-between-arm-intervals)
(`116b5cb`, Apple node, 12,183.6 s, exit 0 on a clean tree) **supersedes the
between-arm recording of 2026-09-16; cite it.** The two commands differ by
the inserted `--contrast
experiments/2026-09-17-fm-arm-contrast/arm-contrast.json` and the output
directory; packages and library hashes are identical, and
`scripts/between_arm_intervals.py` moves from `113396df` to `2f7ba3bb`,
which is that file's blob at `116b5cb`.

*What comes back unchanged.* All 432 rows of the superseded `paired.csv` and
all 507 of its `paired-seeds.csv` are present, with a maximum absolute
difference of 0.0 on `value`, `ci_lo` and `ci_hi` and 0 rows differing in
`excludes_zero`, `is_difference`, `se`, `alpha`, `resamples`, `seed` or
`reads_derived`; no old row is missing and no key occurs twice. `cells.csv`
is byte-identical, sha256 `4fb40268…`. The pooled part of the seed check
holds its numbers, 12 of 26 starred and 0 changing, and so does the largest
bound movement, 0.0163.

*What is new.* 915 rows of `paired.csv` and 18 of `paired-seeds.csv`: the
per-draw rows at the eleven scopes that had none, 891 in all, and the 24
rows of the scope difference `pre-flag - flagged`. The seed check's
scope-wide counts move with them, 169 differences to 175 and 60 starred to
64. Every per-build line of stdout gains the contrast record — the share of
the expanding pool the rolling arm holds, and how many quarters younger its
mean row is — with the numbers before that suffix unchanged, and
`contrast_record` now names the contrast file.

*What the run says about its criterion.* For TabPFN and TabICL at their
library settings and at 1.0, the summary's reading changes from "killed:
inside the interval" to "undetermined on this book (kill criterion 4): the
pre-flag and flagged scopes disagree in sign", `kill_fires` goes from true
to null, and a second field, `reading_on_arm_row`, holds "killed: inside the
interval". No value, bound or `regime_values` entry moves for any model;
what changed is that the flag marking a disagreement between draws is now
keyed by scope and pair rather than by pair alone, and that the scope
difference exists to be read. The scorecard's reading and GBM's are
unchanged.

*The expectation the scope difference does not meet.* The note of 2026-09-17
set the expectation down before this run existed: on H4 both scoped rows hold
zero and the difference between them is expected to hold zero. The scoped rows
do hold zero — TabPFN +0.0227 [−0.0259, +0.0741] on the pre-flag cells and
−0.0238 [−0.0478, +0.0099] on the flagged, TabICL +0.0416 [−0.0055, +0.0866]
and −0.0117 [−0.0399, +0.0177]. The difference between them does not. It reads
+0.0465 [+0.0005, +0.0802] for TabPFN, whose lower bound runs 0.0004 to 0.0014
across the three seeds and sits at the margin, and +0.0533 [+0.0154, +0.0803]
for TabICL, starred under all three seeds. That was a statement of
expectation and not a criterion, so its failing kills nothing and saves
nothing; what it costs is the reading that would have made "undetermined" on
this row two readings of zero disagreeing by chance. The entry of 2026-09-17
below records that the star is lost under each of the three alternatives —
the refit control, the nominal matrix and the reported label.

[`-between-arm-intervals-outcome-reported`](../../experiments/2026-09-17-fm-between-arm-intervals-outcome-reported)
(`5130710`, 12,994.6 s, exit 0) is the same pooling under `--outcome
outcome_reported`, the sensitivity ADR-0006 requires. Its command differs
from the primary's by that flag and the output directory, and its packages
and library hashes are the primary's. Where the two labels coincide the runs
agree to the bit: on the `pre-flag` scope 108 of 108 rows of `paired.csv`
and 39 of 39 of `paired-seeds.csv` match with a maximum absolute difference
of 0.0 and 0 changes of `excludes_zero`, and 476 pre-flag rows of
`cells.csv` are equal on every field. Outside that scope the runs differ on
108 rows of `paired.csv` at each per-build scope and at `builds` and
`flagged`, on 135 at the arm and on 24 at the scope difference. Under the
reported label the summary reads "killed: inside the interval" for TabICL at
both temperatures where the primary reads "undetermined", and
`regimes_disagree_in_sign` goes true to false on those two rows; TabPFN's
two rows read "undetermined" under both labels. No per-build scope of this
book is wholly pre-flag under the `all` pooling, so the identity check covers
the `pre-flag` scope alone.

### 2026-09-17 — a temperature-scaled control for H5

Two runs on the Windows laptop, each exit 0 on a clean tree, that put a
classical model through the transform the foundation models' temperature
applies and read H5's row on it.

[`experiments/2026-09-17-fm-h5-rescaled-control`](../../experiments/2026-09-17-fm-h5-rescaled-control)
(`rescale_reference.py` at `0ce5b32`, 7.2 s) reads the seventeen classical
score runs of 2026-09-13 and writes `gbm-50k@t0.9`, the control's
probabilities under `sigmoid(logit(p) / 0.9)`, 150,000 rows per build over
its three context draws and 0 rows clipped. Its in-sample observed over
expected runs 1.241 on 2010H2-R to 1.650 on 2018H2-R.

[`-h5-rescaled-control-in-sample`](../../experiments/2026-09-17-fm-h5-rescaled-control-in-sample)
(`in_sample_level.py` at `8e3a020`, 135.0 s) reads those seventeen score
runs and the seventeen rescaled copies: 136 context cells over 15,064,850
rows, and a context check finding 51 draws and 51 model pairs with identical
rows and outcomes. The known answer holds on 85 of 136 cells; the 51 that do
not hold one are the rescaled cells, which the transform moves off one by
construction, and the run lists every one of them. H5's row reads, at the
same two ends the grid uses, gbm-50k +0.001 [−0.111, +0.103] and
`gbm-50k@t0.9` −0.064 [−0.267, +0.123] on arm E, and gbm-50k +0.005
[−0.137, +0.122] and `gbm-50k@t0.9` −0.395 [−0.624, −0.220], excluding zero,
on arm R.

What the control settles. The as-written kill at 0.9 reads the scale: a
model whose in-sample level is one by construction on every context, put
through the transform the shipped temperature applies and nothing else,
fires H5's kill on the rolling arm, −0.395 [−0.624, −0.220] under all three
seeds, 1.243 on 2010H2-R against 1.638 on 2018H2-R, and holds zero on the
expanding arm, −0.064 [−0.267, +0.123] — the pattern both foundation models
show at 0.9 on both arms. A kill at 0.9 is therefore evidence of a prior for
neither model, and the withdrawal in the note of 2026-09-17 now rests on a
recorded row. The two explanations separate at 1.0, where a control has
nothing to add, its own row there being one by construction. For TabPFN
the scale is the whole of the level this book can see: at 0.9 its ends,
1.246 and 1.601, sit within 0.04 of the rescaled control's, and at 1.0 its
row holds zero under every seed, +0.034 [−0.107, +0.148], both ends within
0.03 of one. A prior smaller than that interval, under about 0.13 across a
tenfold range, is not excluded, and TabPFN's rolling rows at 1.0 are
derived, with the error on O/E the note of 2026-09-17 puts under
5 × 10⁻³. For TabICL the control settles less. Its row at 0.9, −0.632
[−0.897, −0.405], is larger than the control's and the two intervals
overlap; at 1.0 the row is −0.139 [−0.302, +0.008], zero at its upper
bound under the primary seed and inside under the check seeds, and its
sign is 0.896 on the 4.48% context against 1.035 on the 0.45% one, a lower
observed-over-expected where the rate is higher, which is the reverse of
what a prior toward a fixed low prevalence produces. On 2010H2-R TabICL's
level at 1.0 varies by draw, 0.968, 0.921 and 0.801 on three draws of
50,000 rows from one pool, beyond the binomial interval of each, so its
level on the crisis window is a property of the draw as much as of the
pool's rate. What stays open for TabICL is whether its level at 1.0 depends
on prevalence at a size under 0.14, and the row that would settle it is not
a control but TabICL's own: its level at 1.0 on every rolling context
against the pool rate over the eight builds, which no run pools, or more
draws of the two end contexts. The label. `in_sample_level.py` marks an H5
row "known answer" by the base model's name, so `gbm-50k@t0.9` inherits it
from `gbm-50k`, and the same run's known-answer check reads the opposite,
85 of 136 cells holding one and every one of the 51 rescaled cells named
as not holding it. The label is wrong on the rescaled rows and nothing
above rests on it. What the demonstration rests on is that `gbm-50k`'s own
rows hold one, that the transform is the temperature's, `sigmoid(logit(p)
/ 0.9)` with 0 rows clipped on every build, and that the number it
produces is measured and not known in advance: the note's arithmetic put
the rescaled level near 1.4 at 4.5% and 1.8 at 0.45% before the spread of
the scores, and the spread brings it to 1.243 and 1.638.

*Note of 2026-09-20.* The in-sample reading of this entry was recorded again
at `1f32bca`, and the entry of 2026-09-20 below supersedes it: every row
quoted here comes back there to the bit, and the later recording is the one to
cite.

### 2026-09-17 — the control refitted with a validation tail sized by share

Seventeen runs of `fm_score_build.py --control-refit`, one per build of both
arms, on the Windows laptop from a clean tree at `8816e91`, 186.0 to 213.6 s
each and 3,389.1 s in all, every one exit 0:
[`experiments/2026-09-17-fm-2002h2e-control-refit`](../../experiments/2026-09-17-fm-2002h2e-control-refit)
through
[`-2018h2e-control-refit`](../../experiments/2026-09-17-fm-2018h2e-control-refit)
and
[`-2004h2r-control-refit`](../../experiments/2026-09-17-fm-2004h2r-control-refit)
through
[`-2018h2r-control-refit`](../../experiments/2026-09-17-fm-2018h2r-control-refit).

Each run fits the control alone, on the three 50,000-row contexts of its
build, at the hyperparameter point of the score run it names, and with the
early-stopping tail sized by row share under no cap on the number of
quarters it may take, where the recorded control's policy takes whole
quarters. The fit is written as `gbm-50k@share`. What it is for is the
measurement above: the point the control inherits differs between the arms
at every paired build date, and on this book the quarter rule leaves the
control's validation tail at 2,880 rows on the youngest expanding builds
against some 12,000 on the rolling arm, so the control's E − R mixes the
window with a re-tuning and a tail size a foundation model does not have.
Together the seventeen runs score 31,444,917 rows and write 150,000
reference rows apiece; the build record, the cohort table and the fits are
in each directory's `build.json`, and the score files stay out of the
repository as they do for every build of this book. The poolings that read
them are not entered here.

### 2026-09-17 — the expanding arm with the label-regime and H2 scopes

[`experiments/2026-09-17-fm-arm-e-intervals`](../../experiments/2026-09-17-fm-arm-e-intervals)
(`1ad2915`, Apple node, 14,202.5 s, exit 0 on a clean tree) **supersedes
the expanding-arm pooling of 2026-09-16; cite it until the entry of
2026-09-18 below, which supersedes it in turn.** The command is that
recording's with `--h2-scopes` inserted and the output directory changed,
the nine grid directories, the check seeds and the cells file identical and
in the same order; host, CPU, Python and the twelve library hashes are the
same, and `scripts/arm_intervals.py` moves from `b0f60e80` to `5712374a`,
its blob at `1ad2915`.

*What comes back unchanged.* Every one of the 4,536 rows of the superseded
`paired.csv` and the 8,883 of its `paired-seeds.csv` is matched, with a
maximum absolute difference of 0.0 on `value`, `ci_lo`, `ci_hi`, `se`,
`alpha`, `resamples` and `seed`, 0 rows differing as written text, and
`excludes_zero` and `reads_derived` equal on every row; the 28 blank-value
rows of the old table are blank at the same 28 keys. Of `intervals.json`'s
2,638 leaves none is lost and three change: two counts of rows in the seed
check, and the wall. The arm's own seed-check fields are untouched — 441
differences, 243 starred, 25 changing their star, largest bound movement
0.041836042206761154 — and all 103 `star_changed` entries of the old run are
present with identical values and bounds. All four figures are
byte-identical.

*What is added.* 3,192 rows of `paired.csv` and 7,182 of `paired-seeds.csv`,
every one of them at a scope the older script had none of, and none carrying
a held context draw. The scopes are the two label regimes and the two H2
windows — pre-flag, 16 cohorts over 44 cells; flagged, 16 over 131; the
crisis cells 2007H1 to 2009H2, 6 over 20; the 2022 cells 2022H1 to 2023H2, 4
over 36 — each with its mean over the builds that hold any of its cells.
Beside them the metric `oe_ratio_2022`, per model and build the ratio of
observed over expected on 2022H2, 2023H1 and 2023H2 to the same on 2020H1
and 2021H2, at each of the nine build scopes and at the mean over builds.
`intervals.json` gains `cohort_scopes`, `oe_ratio`, 32 `cox_left_out` leaves
and 74 further `star_changed` entries, 177 in all, none of them replacing an
old one. The run writes 530 bytes to stderr, three numpy `RuntimeWarning`s:
two of the mean of an empty slice and one of the division that follows it,
which is the `nanmean` of
`psi_first_cohort` over a scope holding no non-blank cell; those blank rows
are among the ones listed above, and no shared value moved.

[`-arm-e-intervals-outcome-reported`](../../experiments/2026-09-17-fm-arm-e-intervals-outcome-reported)
(the same commit, 14,640.5 s, exit 0) is the same pooling under `--outcome
outcome_reported`. Because that flag picks a column inside the same score
files, the two manifests hash the same three inputs, the same twelve library
files and the same six code files, and the two stderr files are byte-equal.
The key sets are equal, 7,728 rows of `paired.csv` and 16,065 of
`paired-seeds.csv` on each side with 0 keys on one side only. Over the nine
expanding builds' scorecard rows, 1,027,913 distinct (cohort, row) pairs,
the two labels differ on 0 rows in every cohort from 2003H1 to 2011H2 and on
1 to 1,024 rows from 2012H1 on, the largest counts at 2019H1, 2019H2 and
2018H2. The pre-flag scopes therefore hold bit for bit: 392 and 336 rows of
`paired.csv` and 882 and 756 of `paired-seeds.csv` differ in 0 rows with a
maximum absolute difference of 0, and the crisis scopes, being a subset of
the pre-flag cohorts, do the same. Elsewhere 795 of the 1,176 rows at the
arm differ, by at most 0.332 on a value, while `psi` and `psi_first_cohort`
differ in 0 rows at every scope of both files. `oe_ratio_2022` differs on
all 280 of its rows, and it is the metric the largest per-build movements
belong to; every cohort of both of its windows carries label rows that
differ.

### 2026-09-17 — the refit control and the nominal matrix on H4, and the expanding arm with the refit control

Three poolings on the Apple node from a clean tree at `1ad2915`, all exit 0:
[`experiments/2026-09-17-fm-between-arm-intervals-refit-control`](../../experiments/2026-09-17-fm-between-arm-intervals-refit-control)
(13,867.4 s),
[`-between-arm-intervals-upb-nominal`](../../experiments/2026-09-17-fm-between-arm-intervals-upb-nominal)
(12,421.5 s) and
[`-arm-e-intervals-refit-control`](../../experiments/2026-09-17-fm-arm-e-intervals-refit-control)
(15,318.6 s). Every directory named on their commands is present and tracked,
32, 16 and 18 of them; every file hash of the three manifests matches the blob
at `1ad2915`, 24, 24 and 20 of them; the two between-arm runs re-hash their
own `inputs.json` here without a mismatch, 3,570 and 2,866 entries. None of
the three is a criterion row. No verdict on H4 is restated in this entry: the
criterion's reading is the one recorded above, undetermined for both
foundation models under kill criterion 4, with the reported-label reading
beside it.

*The refit control on H4.* The first run is the reading the note of
2026-09-17 names beside the criterion's: the same pooling with
`gbm-50k@share` in the control's role and the recorded control kept as a
model of its own. Every row naming neither control, the recorded control's
own 147 rows and the 3,264 per-cell rows of the other seven models are the
primary reading's to the bit. The recorded control's E − R is −0.0132
[−0.0474, +0.0308] and the refit's −0.0338 [−0.0582, +0.0049]; their
difference, +0.0206 [+0.0019, +0.0353], is starred under all three seeds, and
it is the amount by which every foundation-model row moves, to six decimals,
since only the control changed. Against the refit control TabPFN reads
+0.0044 [−0.0168, +0.0223], the pre-flag scope +0.0472 and the flagged
−0.0022, the scopes still disagreeing in sign; TabICL reads +0.0174 [−0.0072,
+0.0356], +0.0660 and +0.0098, the scopes agreeing and the arm row holding
zero under every seed. At 1.0, −0.0043 [−0.0250, +0.0164] and +0.0106
[−0.0199, +0.0342]. The pre-flag minus flagged difference reads +0.0494
[−0.0042, +0.1172] for TabPFN and +0.0562 [−0.0012, +0.1178] for TabICL,
holding zero under every seed where the primary reading's is starred. The
summary's strings for this reading — "undetermined on this book (kill
criterion 4)" for TabPFN, "killed: inside the interval" for TabICL — are the
strings of a reading beside the criterion, and not the criterion's. TabICL's
standing differs between the two controls: undetermined under the recorded
control, inside the interval with the scopes agreeing under the refit. Both
are reported, the recorded control's is the criterion's, and what the text may
say of TabICL on H4 is that the book does not resolve it. TabPFN's standing is
the same under both. Its seed check reads 13 of 30 pooled differences starred
with 0 changing, 66 of 202 at every scope with 7 changing, largest bound
movement 0.0181.

*The nominal matrix on H4.* The second run is the ablation the trigger of
2026-09-14 (later) requires, the matrix of 2026-09-16 with the nominal balance
in place of the ratio, the recorded control and the study's label. Every row
of the primary reading has its partner and 1,327 of 1,347 values move, by up
to 0.323. At arm scope TabPFN reads +0.0311 [−0.0061, +0.0555], the scopes
+0.0422 and +0.0258; TabICL +0.0389 [−0.0030, +0.0669], +0.0525 and +0.0333;
at 1.0, +0.0262 [−0.0080, +0.0478] and +0.0313 [−0.0090, +0.0533], TabPFN's
rows at 1.0 on this matrix derived on both arms with the error carried from
2004H2-E's check alone. Every foundation-model row holds zero under all three
seeds, the scopes agree, and the pre-flag minus flagged difference holds zero
(+0.0163 [−0.0306, +0.0769], +0.0192 [−0.0266, +0.0806]). The scorecard reads
−0.0672 [−0.1050, −0.0372] and GBM −0.0091 [−0.0469, +0.0152]. The summary's
"killed: inside the interval" on all four foundation-model rows is this
matrix's reading in the summary's words; the criterion reads the ratio, on
which both models are undetermined. Every foundation-model point estimate
changes sign between the matrices, by +0.041 to +0.051. Its seed check reads
12 of 26 pooled differences starred with 0 changing, 75 of 175 at every scope
with 2 changing, largest bound movement 0.0309.

*The commit gap.* The two between-arm readings above were recorded at
`1ad2915`; the primary reading they sit beside was recorded at `116b5cb`.
`between_arm_intervals.py` is byte-identical at both commits; three modules it
imports differ — `arm_intervals.py` by 245 lines, `ablation_intervals.py` by
two and `derive_temperature.py` by sixteen. The two small differences replace
`int(len())` by `len()` and join a nested condition, and touch no arithmetic.
Of `arm_intervals.py` the script uses two constants, three functions whose
bodies are identical at both commits, and the class that loads an arm, whose
one added branch runs only when a build's directories do not all carry the
outcome column, which under the study's label they do. The reading with the
refit control, at the later commit, reproduces every row it shares with the
primary reading to the bit, the recorded control's own rows included; the H4
rows are the difference of a model's reduction and the control's on the same
resample inside the unchanged script, and the refit reading's H4 rows differ
from the primary's by the difference of the two controls' reductions to six
decimals. What the commits changed is therefore bounded on every row of both
readings, and the rows that move on the nominal matrix move by the matrix.
Neither reading supersedes another, so no bit-for-bit statement is made of
them; the between-arm poolings are recorded again at one commit before any H4
row enters the ledger, and that recording is held to the bit against these.

*The expanding arm with the refit control.* The third run is the arm pooling
of the same commit with the nine refit-control directories of the expanding
arm added beside its nine grid directories: the refit
enters as a model of its own and all 7,728 rows and 16,065 seed rows of the
pooling it sits beside come back to the bit, the 2,208 and 5,355 added rows
all naming `gbm-50k@share`. Read against the recorded control's own rows,
1,140 of 1,380 values and 120 stars move, by at most 0.145 on a value;
2002H2-E and 2004H2-E, where the four-quarter cap did not bind, move on no row
and no metric, and every later build moves on all of its. At arm scope, with
the rows at 0.9 quoted in the model-minus-control orientation the recorded
control's rows are written in — this run writes those two as control minus
model — H1's row, the difference of the AUC slopes on age at one intercept per
build, reads +0.000157 [+0.000083, +0.000236] for TabPFN and +0.000186
[+0.000109, +0.000266] for TabICL against the refit control, against
+0.000168 [+0.000091, +0.000246] and +0.000197 [+0.000112, +0.000275] under
the recorded one; all four exclude zero and no star changes. H3's row, PSI
against the model's own training reference, reads −0.0032 [−0.0092, +0.0020]
and −0.0150 [−0.0194, −0.0124] against the refit, against −0.0052 [−0.0121,
+0.0012] and −0.0170 [−0.0217, −0.0132] under the recorded control; TabPFN's
holds zero and TabICL's excludes it under both, and neither star changes. The
first-scored-cohort reference reported beside H3 does change on one row:
TabICL reads −0.0079 [−0.0231, +0.0022] against the refit, holding zero, where
under the recorded control it reads −0.0105 [−0.0288, −0.0002] and is starred;
TabPFN's, +0.0031 [−0.0049, +0.0101] against +0.0005 [−0.0105, +0.0104], holds
zero under both. The rows at 1.0 stand as their counterparts at 0.9 do on all
three metrics. Where a row's standing differs between the two controls both
are reported, the recorded control's is the criterion's, and the text supports
at most the weaker claim.

*Note of 2026-09-20.* The pooling of this paragraph was recorded again at
`386c629`, and the entry of 2026-09-20 below supersedes it: every row quoted
here comes back there to the bit, and the later recording is the one to cite.

### 2026-09-17 — the rolling arm, and the contexts read again on their own rows

[`experiments/2026-09-17-fm-arm-r-intervals`](../../experiments/2026-09-17-fm-arm-r-intervals)
(`9f0e110`, Apple node, 11,189.9 s, exit 0 on a clean tree) **supersedes the
rolling-arm pooling of 2026-09-16; cite it.** The two commands are the same
length and differ at one position, the output directory; packages agree on
all sixteen entries, the twelve library hashes agree, and
`scripts/arm_intervals.py` moves from `b0f60e80` to `419ee0ae`. Every
recorded hash of a file inside the tree matches the blob at the commit its
own manifest names, 14 of 14 in the old run and 20 of 20 in the new.

*What comes back unchanged.* All 4,200 rows of the old `paired.csv` and all
8,127 of its `paired-seeds.csv` are matched, 0 rows differ in any column,
and the maximum absolute difference is exactly 0.0 on every numeric column
of both files; the blank-value rows are the same rows on both sides, 28 and
63. Of 2,382 `intervals.json` leaves none is lost and nine change: four
positions of the `pooled_metrics` list, which is the old list one entry
longer, the four counts of rows in the seed check, and the wall. The largest
movement of an interval bound is identical to its last digit,
0.08192649333119256, and `arm_star_changed` reads 16 in both.

*What is added.* Two things at once, and the entry separates them. The
commit `80afaa8` between the two runs makes the arm pooling write the
label-regime scopes whenever `--cells` is given, and this command gives it:
`pre-flag`, `flagged` and their two means over builds add 1,680 rows to
`paired.csv` and 3,780 to `paired-seeds.csv`, together with the three
unconditional keys `outcome`, `cohort_scopes` and `oe_ratio`, the last null
because `--h2-scopes` was not given. The second is the signed Cox slope,
written key for key with `cox_slope_deviation` at every scope of both files
— 896 rows of each metric in `paired.csv`, 1,827 in `paired-seeds.csv`, and
0 keys of either metric without a partner — with its own `cox_left_out`
entries, which equal the deviation's at all 32 pooling-and-scope pairs and
read 0 cells and 0 builds everywhere on this arm. Each added row's value,
bounds and standard error are finite, every interval brackets its value, and
no standard error is negative. The four seed-check counts grow by 1,701,
956, 63 and 46, and each growth splits exactly into the signed slope's rows
at the old scopes and the new scopes' rows at every metric, with 0 rows
unexplained. `arm-differences.png` gains one panel, 4,186 px wide to 4,784
at an unchanged height of 1,846; the other three figures are byte-identical.
stderr holds one warning, the `nanmean` of `psi_first_cohort` over the 56
blank rows of `builds, pre-flag`.

[`-grid-in-sample`](../../experiments/2026-09-17-fm-grid-in-sample)
(the same commit, 290.2 s, exit 0) **supersedes the in-sample recording of
2026-09-16 on the primary matrix; cite it.** Both commands hold 94
arguments and differ at one position, the output directory; every source
directory, `--builds-json`, `--with-cohorts` and the check seeds are
identical and in the same order, and `scripts/in_sample_level.py` moves from
`0a00f13b` to `4115326d`. The 289 keys of `cells.csv` come back with a
maximum absolute difference of 0.0 on all sixteen columns the old run wrote
and 0 rows differing on any of them; `h5.csv`, `h5-seeds.csv`,
`cohort-cells.csv` and `level-prevalence.png` are byte-identical, and the
only leaf of `summary.json` that moved is the wall.

The run adds nine columns to `cells.csv` — whether the per-cell Cox fit
converged, its slope and intercept with their Wald intervals, a known-answer
flag for the scorecard's own pool, and the label marking a build as an arm's
high- or low-rate end — and two files and one `summary.json` section for the
in-sample Cox slope pooled over an arm's builds. Mechanically: 289 of 289
rows converged, no Cox column holds a non-finite value, and every interval
brackets its estimate. The known answer holds on all 17 scorecard
training-pool cells, the largest |slope − 1| 1.24 × 10⁻⁶ and the largest
|intercept| 4.12 × 10⁻⁶ against the tolerance of 1 × 10⁻⁴ the code compares
against, and every scorecard training-pool cell in the file is marked, with
none missed. The end-of-arm label falls on exactly the 68 rows of the four
builds the summary names as ends, 0 rows carrying the wrong label and none
of those rows left unlabelled. `in-sample-slope.csv` holds 10 rows, one per
arm and model, with all 60 numeric cells finite, every interval bracketing
its value, 0 builds left out of any pooling, and the models on each arm the
models H5 reads there; `in-sample-slope-seeds.csv` holds 30, and its
primary-seed block repeats the 10 exactly. Rebuilt from the same run's
`cells.csv`, each pooled slope equals the mean over that arm's (build,
context seed) cells to at most 2.2 × 10⁻¹⁶, and the unchanged H5 table
rebuilds from the same cells to 1.1 × 10⁻¹⁶, so the old statistic and the
new columns read one set of cells. The summary states the new statistic's
reading key as "one-sided: a slope above one is smoothing, the pull toward a
row's own label, or both; a slope below one beyond its interval is
over-dispersion on the rows the model conditions on".

Its ten rows are read where they belong, with the signed slope's rows, in the
entry of 2026-09-18 below that reads the signed Cox slope on both arms.

### 2026-09-18 — the expanding arm's pair, recorded again with the signed slope

[`experiments/2026-09-18-fm-arm-e-intervals`](../../experiments/2026-09-18-fm-arm-e-intervals)
(14,198.4 s) and
[`-arm-e-intervals-outcome-reported`](../../experiments/2026-09-18-fm-arm-e-intervals-outcome-reported)
(14,592.4 s), both at `9f0e110` on the Apple node, both exit 0 on a clean
tree. **They supersede the two expanding-arm poolings of 2026-09-17; cite
them.** Each command is its baseline's with the output directory alone
changed: the nine grid directories, `--check-seeds 20260906,20260907`,
`--cells experiments/2026-09-13-fm-vintage-builds2/cells.csv`,
`--h2-scopes`, and in the second run `--outcome outcome_reported`, are
unchanged. Of the 21 hashed paths in each manifest two differ, the same two
in both pairs — `scripts/arm_intervals.py` and `scripts/build_intervals.py`,
the two files the commits differ in — and every hash of a path inside the
tree was checked against the blob at the commit its run names, 20 of 20 on
each side of each pair with 0 failures.

*What comes back unchanged.* In both pairs the baseline's 7,728 rows of
`paired.csv` and 16,065 of `paired-seeds.csv` are matched, none missing,
with 0 cells differing read as written text, 0 differing read as floats, and
a maximum absolute difference of exactly 0.0 over every column of both
files. The 616 blank entries sit at the same keys on both sides. Of
`intervals.json` none of the baseline's leaves is lost, and ten change in
the first pair and nine in the second: four positions of the
`pooled_metrics` list, the counts of rows in the seed check, and the wall.
Recomputed from each new run's own two tables, all seven seed-check readings
agree with what is written, and `largest_bound_movement` does not move in
either pair — 0.041836042206761154 and 0.04879401416306392, the same in the
new run as in its baseline. Three of the four figures are byte-identical in
both pairs.

*What is added.* One metric and nothing else. Every added row of both files
in both runs carries `cox_slope`: 1,176 rows of `paired.csv` and 2,457 of
`paired-seeds.csv` per run, 0 rows added under any other metric, at exactly
the keys `cox_slope_deviation` holds — the same 19 scopes, the same three
poolings, the same row count at every scope, and the same blank rows.
`cox_left_out` reads the same two numbers for the signed slope as for the
deviation at all 42 pooling-and-scope pairs, 0 mismatches, every count 0 on
this arm. The added leaves are that block, the signed slope's entries in
`star_changed` and `draws_disagree`, the position `pooled_metrics` gains,
and the one `statistics` key that defines it, and nothing else.
`arm-differences.png` is the one figure that changes, and it is the one
drawn per metric.

*The check the pair supports.* Where the study's label and
`outcome_reported` coincide the two new runs must agree, and they do: 5,460
matched rows over the pre-flag and crisis scopes of both files, 0 rows on
one side only, 0 differing cells in any column, and a maximum absolute
difference of 0.0 for the signed slope and for the seven older metrics
alike. The same comparison on the scopes where the labels are not expected
to coincide is not empty — 552 differing value cells on the flagged scopes,
963 at the arm, 304 at `builds`, 165 and 138 on the two 2022 scopes, the
largest among them 1.583, at `builds` — so the identity above is a result
and not an
artefact of how the comparison was made.

What is not here. The reading of the signed slope. Its rows on this arm are
recorded here and read in the entry below, which reads the statistic on both
arms from the recorded tables.

### 2026-09-18 — the signed Cox slope read on both arms, and the in-sample slope beside it

The reading fixed on 2026-09-17 is made on the three recordings above:
[`experiments/2026-09-18-fm-arm-e-intervals`](../../experiments/2026-09-18-fm-arm-e-intervals),
the 196 criterion cells of arm E;
[`experiments/2026-09-17-fm-arm-r-intervals`](../../experiments/2026-09-17-fm-arm-r-intervals),
the 160 of arm R; and
[`experiments/2026-09-17-fm-grid-in-sample`](../../experiments/2026-09-17-fm-grid-in-sample),
289 context cells over 17 builds and 22,714,850 rows. 200 resamples under seed
20260905, checked under 20260906 and 20260907, the context seed drawn with the
resample. No cell was left out of any `cox_slope` point estimate or any
resample, at any pooling or scope, on either arm. Both owed readings are
here, the signed slope's and the in-sample slope's.

*The attribution is not supported on either arm, and both arms contradict it.*
On arm E at temperature 1.0 the mean signed slope minus the scorecard's is
+0.0113 [−0.0132, +0.0387] for TabPFN and +0.0154 [−0.0087, +0.0349] for
TabICL. Both hold zero under all three seeds, so the paired half decides
nothing. The models' own slopes on the same cells are 0.8795 [0.8447, 0.9162]
and 0.8837 [0.8496, 0.9215], each wholly below one, and a slope below one is a
logit more spread than the outcomes warrant.

On arm R the paired half reads the other way and the verdict does not change.
The difference is +0.0797 [+0.0643, +0.0949] for TabPFN and +0.1042 [+0.0890,
+0.1223] for TabICL, both excluding zero under all three seeds and both above
the minimum effect of 0.05; their own slopes are 0.8415 [0.8154, 0.8691] and
0.8661 [0.8360, 0.8975], again wholly below one. Support asks for both halves,
and a positive difference between two models under one is a model less
over-dispersed than the scorecard. The scorecard's own slope is 0.8682 [0.8457,
0.8969] on arm E and 0.7619 [0.7404, 0.7848] on arm R: out of time this book
puts every model below one, and the pairing subtracts what it does to all of
them alike.

No criterion star is lost under a check seed. Over both arms three rows of the
four pairs lose a primary-seed star: the expanding arm's `nearest` pooling at
2004H2-E at 0.9 and at 2008H2-E at 1.0, and the rolling arm's `nearest` pooling
at the scope `builds, pre-flag` at 0.9. All three sit at the `nearest` pooling
and none at a criterion scope. Four rows gain a star under a check seed alone,
one of them at the `all` pooling, the rolling arm's 2008H2-R. Every one of
the four criterion rows at 1.0 is listed under `bootstrap.draws_disagree`; on
arm E the three fixed context draws run −0.0078, +0.0127 and +0.0289 for
TabPFN, and the criterion pooling draws the context seed with the resample, so
its interval covers that spread.

*The shipped setting.* At 0.9 the difference is −0.0767 [−0.0990, −0.0538] and
−0.0729 [−0.0953, −0.0556] on arm E, and −0.0045 [−0.0180, +0.0104] and
+0.0176 [+0.0036, +0.0346] on arm R, TabPFN first. Every model's own slope at
0.9 is wholly below one, 0.7915 and 0.7953 on arm E and 0.7574 and 0.7795 on
arm R. The knob multiplies the slope by 0.9 and moves both models further from
the direction the attribution predicts.

*Derived rows.* TabPFN's rows at 1.0 are scored on arm E and derived on arm R,
TabICL's derived on both, so both starred rows of arm R rest on derived rows.
TabICL's derivation is exact, worst probability gap 1.36 × 10⁻⁷. TabPFN's on
arm R carries a worst per-build Cox-slope gap of 1.89 × 10⁻³ on 2008H2-R,
below the 2.5 × 10⁻³ measured against scored rows and a fortieth of the
starred difference it enters, measured on contexts of a narrower range than
the ones it is applied to.

*In sample, one-sided.* Every in-sample slope lies above one under all three
seeds and no build is left out: on arm E, TabPFN 1.1517 [1.1281, 1.1740] and
TabICL 1.1784 [1.1502, 1.2029] at 1.0, 1.0369 [1.0156, 1.0570] and 1.0606
[1.0352, 1.0826] at 0.9; on arm R, 1.2295 [1.1898, 1.2695] and 1.3097 [1.2716,
1.3439] at 1.0, 1.1065 [1.0709, 1.1425] and 1.1787 [1.1445, 1.2095] at 0.9;
GBM-50k, fitted and not at the likelihood's maximum, reads 1.5024 [1.4216,
1.5847] and 1.3565 [1.3152, 1.3938]. Above one is the confounded side —
smoothing, the pull of a row's own label in the context, or both — so these
rows support nothing. The one thing an in-sample cell can say, a slope below
one beyond its interval, is said on no row.

*The known answer.* The scorecard reads Cox slope one and intercept zero on
its own pool on 17 of 17 cells, worst |slope − 1| 1.24 × 10⁻⁶ against a
tolerance of 10⁻⁴, and the level block of the same run reads observed over
expected of one on 85 of 85 fitted-model cells. The fit, the interval and the
pooling return the known answer where the answer is known.

*Beside the reading, entering none of it.* The mean over builds, each build on
its own, the pre-flag and flagged scopes, the crisis-cell and 2022-cell scopes
of arm E, the nearest-cohorts window, the cohorts-resampled pooling and the
three fixed draws. Several of them change a sign: at 1.0 on arm E the
difference for TabPFN is +0.0626 [+0.0385, +0.1000] at 2004H2-E and
−0.1077 [−0.1539, −0.0503] at 2010H2-E. A build's row is read as a
build's row. The sensitivity label was passed to neither arm pooling; a pooling
of arm E under it,
[`experiments/2026-09-18-fm-arm-e-intervals-outcome-reported`](../../experiments/2026-09-18-fm-arm-e-intervals-outcome-reported),
reads +0.0049 [−0.0190, +0.0291] and +0.0081 [−0.0141, +0.0242] with own
slopes of 0.8424 and 0.8456, and moves neither half.

*What the reading does not see.* A shift of every probability on the logit,
the slope being invariant to a shift of its regressor, so the level half of the
attribution is H5's and not this one's; a stretch this book does to every model
alike, which the pairing subtracts and which arm R's scorecard at 0.7619 makes
large here; and a model at one or at the scorecard's slope, which reads zero.
The own-slope half is read under the primary seed alone, `paired-seeds.csv`
carrying difference rows only, so the check seeds cover the paired half and not
the half that decided all four rows. Arm R carries no crisis-cell or
2022-cell scope, and Lending Club holds no in-sample pooling to set beside
this one, beyond the falsifying build's one draw.

### 2026-09-19 — the results the Setting quoted, carried here

The Setting's note of 2026-09-17 and its smoothing reading quoted numbers
produced by model fits and poolings on this book. From this date the Setting
carries numbers about the data — pool sizes, prevalence, cohort and cell
counts, quarters, the arm contrast — and none produced by a fit or a pooling;
the passages below left it and are quoted here whole, as they stood, and each
place they stood now points to this entry. Nothing is recomputed, and no
hypothesis, criterion or reading changes: the Setting keeps the sentences that
fix a reading, and these are the numbers and findings those sentences were
written beside.

Where each number is read from. H4's arm and scoped rows and each foundation
model's own E − R are rows of `paired.csv` of
[`experiments/2026-09-16-fm-between-arm-intervals`](../../experiments/2026-09-16-fm-between-arm-intervals),
reproduced to the bit by the superseding
[`experiments/2026-09-17-fm-between-arm-intervals`](../../experiments/2026-09-17-fm-between-arm-intervals),
which is the one cited; the control's E − R under each draw held fixed is the
per-draw arm row of GBM-50k's reduction in the same file. The control's
early-stopping rows, round counts and mean |slope − 1| per build and draw are
`validation_rows`, `rounds` and `mean_deviation` of `control-fits.csv` of
[`experiments/2026-09-17-fm-h4-sensitivity`](../../experiments/2026-09-17-fm-h4-sensitivity).
H5's rows are those of the entry of 2026-09-16 on every context scored on its
own rows, and the width of H4's interval is the one the entry of 2026-09-17 on
the sensitivity of H4's row reads.

From the note of 2026-09-17, on H4 at arm and scope level:

> *H4 is undetermined on this book, as kill criterion 4 reads it.* At arm
> scope over the 160 criterion cells at 0.9 the row reads −0.0162 [−0.0446,
> +0.0175] for TabPFN and −0.0031 [−0.0345, +0.0254] for TabICL, holding zero
> under every seed; on that row alone the kill would fire inside the
> interval. Under the two scopes criterion 4 compares, the row reads +0.0227
> [−0.0259, +0.0741] on the 28 pre-flag cells and −0.0238 [−0.0478, +0.0099]
> on the 115 flagged cells for TabPFN, +0.0416 [−0.0055, +0.0866] and −0.0117
> [−0.0399, +0.0177] for TabICL. The signs differ, and the criterion says
> what follows: H4 is reported as undetermined on this book, with both
> scopes and the sensitivity reading beside it. The recorded run computes
> the disagreement and prints it but reads the verdict off the arm row alone,
> so its summary says "killed: inside the interval"; the script is corrected
> to read the criterion and the pooling is recorded again as superseding,
> which must reproduce every value, bound and star to the bit, the verdict
> alone changing. The sensitivity reading the criterion names, the same pooling
> under the reported label, has not been run and is recorded before the
> verdict enters the log; on the pre-flag cells the two labels are one by
> construction, so the sensitivity reading reproduces the primary reading's
> pre-flag rows to the bit, and a run on which it does not is wrong. What
> the grid shows about H4 without the control is on the table already:
> TabPFN's own E − R is −0.0294 [−0.0483, −0.0067], TabICL's −0.0164
> [−0.0281, +0.0024]; at 1.0, −0.0381 [−0.0509, −0.0152] and −0.0232
> [−0.0355, −0.0103], read on derived rows with the error printed. The
> eight-quarter window leaves TabPFN's slope further from one than the
> expanding pool does, beyond the interval, and moves TabICL's within it.
> That is the sentence this book supports on H4.

From the same note, on the control's early-stopping set:

> *The control's early-stopping set shrinks along the expanding arm, and a
> refit control is read beside it.* The rule that sizes the set takes the
> fewest latest quarters holding a fifth of the rows, never more than four.
> The cap was written for a book whose volume doubles each year; on this
> book, flat at 12,500 loans a quarter, four quarters of a 50,000-row draw
> from a 71-quarter pool are 5.6% of the draw. The control's early-stopping
> rows on the expanding arm, per date, are 14,506–14,669 at 2002H2, then
> 10,230–10,390, 8,778–8,947, 6,343–6,419, 5,143–5,361, 4,311–4,441,
> 3,600–3,684, 3,196–3,251 and 2,880–2,940 at 2018H2, on the order of ten to twenty-five defaults at the benign decade's rates,
> an estimate, since the count is not recorded; on the rolling arm two quarters
> hold a quarter of the draw and the set is 12,311 to 12,834 rows at every
> date. The round count is the one thing the control re-chooses, and on
> those rows it is chosen by little: 167, 32 and 144 rounds on 2018H2-E at
> the full pool's point of learning rate 0.1 and 31 leaves, with mean
> |slope − 1| over the build's 8 cells of 0.586, 0.187 and 0.530; 95, 60 and
> 128 rounds on 2008H2-E, 0.166, 0.390 and 0.104. The control's own E − R
> under each draw held fixed, +0.027 [+0.015, +0.033], −0.044 [−0.051,
> −0.024] and −0.023 [−0.031, −0.010], do not overlap, and the pooled
> interval is mostly their spread. The asymmetry runs with the arm, so the
> control's E − R mixes the window with the size of its stopping set, and a
> row that reads "no different from the control" could be describing early
> stopping. The recorded control stays the criterion's: it is the control
> this file describes, every verdict against it is recorded as read, and
> this note is dated after those verdicts were seen. Beside it, from here, a
> refit control as a named reading: GBM-50k alone, the inherited point
> unchanged, the early-stopping tail the fewest latest whole quarters
> holding a fifth of the draw's rows and never more than half its quarters,
> the four-quarter cap not applied. It is fitted on every build of both arms
> of both books: on Lending Club, where the cap never binds, and on this
> book's rolling arm, where two quarters already hold a quarter of the draw,
> it must reproduce every recorded control fit bit for bit, and a refit
> that does not is not recorded; on this book's expanding arm it differs. Read
> from it: H4's row, and the expanding arm's rows of H1 and H3 against the
> control. Where a row's standing differs between the two controls — a star
> appearing or vanishing, the kill it reads — both are reported, the
> recorded control's is the criterion's, and the text supports at most the
> weaker claim. The point the control inherits differs between the arms at
> all eight paired dates, as on the first book; the per-date table, the
> rows above and the control's sensitivity points are recorded in
> [`experiments/2026-09-17-fm-h4-sensitivity`](../../experiments/2026-09-17-fm-h4-sensitivity)
> and printed beside H4; a control at one point on both arms, a control searched
> on its own rows, and the full GBM with the cap lifted are reviewer's runs.

From the same note, on H5:

> *H5's kill at 0.9 is the scale, and the reading at 1.0 is the test.* On
> the rolling arm the criterion fires: O/E of the highest-rate context minus
> the lowest's at 0.9 is −0.355 [−0.581, −0.175] for TabPFN (1.246 against
> 1.601) and −0.632 [−0.897, −0.405] for TabICL (1.098 against 1.731); on
> the expanding arm both hold zero over its 1.8-fold range. The sentence
> above that a kill "says the shortfall is a prior pulling the level toward
> a fixed prevalence rather than a scale on the logit" is withdrawn, dated
> after the result, because it is wrong by arithmetic: a scale of the logit
> by 1/0.9 multiplies a small probability by about p^0.11, so a model
> exactly calibrated at 1.0 reads an O/E at 0.9 that rises as prevalence
> falls, near 1.4 at 4.5% and 1.8 at 0.45% before the spread of the scores
> is accounted for, and fires the kill across a tenfold range. At 0.9 the
> temperature cannot be told from a prior. The reading at 1.0 was fixed
> beside the criterion before any number existed and is where the two
> separate: a prior shows as a dependence of O/E on prevalence at 1.0, a
> scale as none. At 1.0 TabPFN reads 1.007 against 0.974, +0.034 [−0.107,
> +0.148] — the scale is the whole of it, and the derived rows' error on O/E
> of under 5 × 10⁻³ is immaterial against that interval; TabICL reads 0.896
> against 1.035, −0.139 [−0.302, +0.008], holding zero at its upper bound
> with its in-sample level on 2010H2-R varying by draw, 0.968, 0.921 and
> 0.801, and the question is open for it. The demonstration that the
> as-written kill reads the scale is recorded beside the reading: the
> classical models' in-sample O/E on the same context rows after the same
> rescaling of the logit by 1/0.9 — calibrated by construction at 1.0, they
> fire the kill at 0.9 or the arithmetic above is wrong.

From the smoothing reading of 2026-09-17, the sentence on H5 at 1.0:

> H5 was read at 1.0 before this note was written: for TabPFN the temperature
> scale is the whole of the level and the dependence on prevalence is inside
> its interval; for TabICL the row holds zero at its upper bound and the
> question is open. That reading is dated after its result and cannot be
> pre-registered here; it is not.

From the same reading, the width of H4's interval in the argument for the
minimum effect:

> And the pooled intervals on slope statistics of this book are about 0.06
> wide at arm scope (H4's row), so 0.05 sits at the resolution of the
> instrument: a star under it is a direction the pooling can see and a size a
> risk team cannot.

### 2026-09-19 — H4's draw component

No run. Every number below is read from a recorded table and the file each
comes from is named beside it; the shares of the pool are ratios of two
recorded counts. The entry changes no verdict: H4 stays undetermined on this
book under kill criterion 4, and the refit control stays a reading beside,
`gbm-50k@share` on every row it touches.

*The rows.* Arm scope, mean |Cox slope − 1| at 0.9, each model's E − R: one
row per context draw with the draw held fixed and the cohorts resampled,
`cohorts` `all` and `draw` set; then the pooled row with the draw drawn
with the resample, `cohorts` `all, cohorts resampled`. Metric
`cox_slope_deviation`, kind `reduction`, seed 20260905; a star marks an
interval that excludes zero. From `paired.csv` of
[`experiments/2026-09-17-fm-between-arm-intervals`](../../experiments/2026-09-17-fm-between-arm-intervals):

    draw       gbm-50k                   tabpfn                    tabicl
    20260911   +0.0271 [+0.015, +0.033] *  −0.0104 [−0.017, −0.005] *  −0.0013 [−0.007, +0.005]
    20260912   −0.0437 [−0.051, −0.024] *  −0.0327 [−0.039, −0.027] *  −0.0245 [−0.031, −0.018] *
    20260913   −0.0231 [−0.031, −0.010] *  −0.0452 [−0.050, −0.039] *  −0.0233 [−0.028, −0.017] *
    pooled     −0.0132 [−0.056, +0.034]    −0.0294 [−0.054, −0.004] *  −0.0164 [−0.034, +0.005]

The refit control, from `paired.csv` of
[`experiments/2026-09-17-fm-between-arm-intervals-refit-control`](../../experiments/2026-09-17-fm-between-arm-intervals-refit-control),
whose rows for the other models equal the table above:

    draw       gbm-50k@share
    20260911   +0.0019 [−0.008, +0.007]
    20260912   −0.0479 [−0.055, −0.033] *
    20260913   −0.0554 [−0.061, −0.042] *
    pooled     −0.0338 [−0.068, +0.011]

The scorecard and the full-pool GBM read one value on every draw, −0.0805 and
−0.0311, since both are fitted on the whole pool and have no draw.

*The rounds.* From `control-fits.csv` of
[`experiments/2026-09-17-fm-h4-sensitivity`](../../experiments/2026-09-17-fm-h4-sensitivity),
`rounds` and `validation_rows` per build, arm and draw. On the expanding arm
the recorded control stops on 2,880 to 10,390 rows over three or four
quarters and runs 15 to 227 rounds; on the rolling arm it stops on 12,311 to
12,834 rows over two quarters and runs 39 to 243. Across the three draws of
one build the round count moves by a factor of up to 5.2 on the expanding arm
— 167/32/144 at 2018H2, 15/21/70 at 2016H2, 95/60/128 at 2008H2 — and of at
most 1.64 on the rolling arm. At 2018H2-E the mean |slope − 1| over the
build's 8 criterion cells is 0.586/0.187/0.530 by draw. The refit, from
`units/gbm-50k@share/<draw>/summary` of `build.json` of
[`experiments/2026-09-17-fm-2018h2e-control-refit`](../../experiments/2026-09-17-fm-2018h2e-control-refit),
stops at 2018H2-E on 10,118/10,517/10,709 rows and runs 31/120/31 rounds:
four times the stopping rows, and still a factor of four across draws.

*The full-pool GBM's tail.* The rule that caps the control's stopping set at
four quarters sizes the full-pool GBM's as well, and the point every GBM-50k
inherits is that model's. From `units/gbm/summary` and `pool_rows` of
`build.json` of each score run of 2026-09-13
([`experiments/2026-09-13-fm-2002h2e-scores`](../../experiments/2026-09-13-fm-2002h2e-scores)
through
[`-2018h2r-scores`](../../experiments/2026-09-13-fm-2018h2r-scores)):

    build      pool rows   quarters   tail rows   share
    2002H2-E      79,511          2      23,167   29.1%
    2004H2-E     176,092          3      36,351   20.6%
    2006H2-E     272,936          4      48,290   17.7%
    2008H2-E     368,551          4      47,218   12.8%
    2010H2-E     465,066          4      49,270   10.6%
    2012H2-E     564,228          4      49,619    8.8%
    2014H2-E     662,396          4      48,899    7.4%
    2016H2-E     759,434          4      48,651    6.4%
    2018H2-E     856,861          4      49,179    5.7%
    every -R      95,615–99,162    2   23,578–24,795   24.7%–25.6%

From 2006H2 on the expanding arm the cap binds and the share falls with the
pool; the rolling arm sits near a quarter at every date. This is a fact about
the point the control inherits and it is stated as one; the full GBM with the
cap lifted is a reviewer's run, as the note of 2026-09-17 has it.

*What the rows say.* Every 50,000-row model moves with the draw, fitted or
not. TabPFN has no fit and no stopping rule, and its per-draw E − R run
−0.010, −0.033 and −0.045, the first draw's interval disjoint from the
other two. The refit lifts the cap and quadruples the
stopping set, and its per-draw values spread as widely as the recorded
control's, 0.057 against 0.071, with the first draw's interval disjoint from
the other two. **A between-arm test on 50,000-row contexts is dominated by
which 50,000 rows the context holds, the between-draw spread of every model's
E − R is several hundredths on both books, and three draws make that
component a three-point distribution, so H4's pooled interval is the draw
spread, not the effect's.** The cap is a second defect inside that one, of the
control alone and of this book: along the expanding arm the control's
stopping set falls to a few thousand rows and its round count is chosen on
them, which adds an instability the refit reading isolates. Neither is
repaired, because repairing the cap does not resolve the draw. TabPFN's own
E − R, −0.0294 [−0.054, −0.004] with the draw component in, keeps its star
and is quoted with the three-draw caveat beside it, never as a verdict on the
context policy.

### 2026-09-19 — H4's signed reading

No run. A reading beside, dated after the result, entering no criterion: H4's
statistic stays the folded mean |Cox slope − 1|, which was pre-registered and
under which every verdict was read, and H4 stays undetermined on this book
under kill criterion 4. The signed slope is read for one thing, what the
folded reduction between the arms is a reduction of. The entry of 2026-09-18
above reads the signed slope against the scorecard; this one reads it between
the arms.

*The arm rows.* Metric `cox_slope`, `cohorts` `all`, `draw` empty,
`is_difference` False, scope `arm`, each model's mean signed Cox slope over
the arm's criterion cells, seed 20260905. Arm E is 196 cells (nine expanding
builds) and arm R is 160 (eight rolling ones), so the two rows are not on
identical cells. From `paired.csv` l. 86–92 of
[`experiments/2026-09-18-fm-arm-e-intervals`](../../experiments/2026-09-18-fm-arm-e-intervals)
and of
[`experiments/2026-09-17-fm-arm-r-intervals`](../../experiments/2026-09-17-fm-arm-r-intervals):

    model        arm E (196 cells)            arm R (160 cells)
    scorecard    0.8682 [0.8457, 0.8969]      0.7619 [0.7404, 0.7848]
    gbm          0.9108 [0.8916, 0.9375]      0.8463 [0.8227, 0.8686]
    gbm-50k      0.9515 [0.8891, 1.0504]      0.8579 [0.8218, 0.8973]
    tabpfn       0.7915 [0.7602, 0.8245]      0.7574 [0.7339, 0.7822]
    tabicl       0.7953 [0.7647, 0.8294]      0.7795 [0.7524, 0.8078]
    tabpfn@t1    0.8795 [0.8447, 0.9162]      0.8415 [0.8154, 0.8691]
    tabicl@t1    0.8837 [0.8496, 0.9215]      0.8661 [0.8360, 0.8975]

*The same 160 cells.* The per-build `cox_slope` rows of the two arm runs
(same filters, scope the build), from arm E's `paired.csv` l. 702–708,
898–904, 1094–1100, 1290–1296, 1486–1492, 1682–1688, 1878–1884, 2074–2080
(2004H2-E to 2018H2-E) and arm R's l. 506–512, 702–708, 898–904, 1094–1100,
1290–1296, 1486–1492, 1682–1688, 1878–1884 (2004H2-R to 2018H2-R). Each arm's
signed value on the shared cells is the sum over the eight paired builds of
the build's row times its criterion cells, over 160. The cells per build are
33/29/25/21/17/15/12/8 from 2004H2 to 2018H2, counted in `cells.csv` of
[`experiments/2026-09-17-fm-between-arm-intervals`](../../experiments/2026-09-17-fm-between-arm-intervals)
(`criterion` True, one model, one draw). On arm R the weighted value
reproduces the arm row above to the fourth decimal, as it must, since arm R's
cells are these 160. Points, no interval. Beside them, the recorded folded
reduction, E − R of mean |Cox slope − 1| at arm scope in the criterion's
pooling (`cohorts` `all`, `draw` empty: cohorts held fixed, the draw drawn
with the resample; the entry above quotes the pooling with the cohorts
resampled), from the same run's `paired.csv` l. 4–22; a star marks an
interval that excludes zero:

    model        signed E    signed R    signed E − R   folded E − R (recorded)
    scorecard    0.862       0.762       +0.100         −0.0805 [−0.0859, −0.0648] *
    gbm          0.872       0.846       +0.025         −0.0311 [−0.0355, −0.0233] *
    gbm-50k      0.945       0.858       +0.087         −0.0132 [−0.0474, +0.0308]
    tabpfn       0.783       0.757       +0.025         −0.0294 [−0.0483, −0.0067] *
    tabicl       0.791       0.780       +0.011         −0.0164 [−0.0281, +0.0024]
    tabpfn@t1    0.870       0.842       +0.028         −0.0381 [−0.0509, −0.0152] *
    tabicl@t1    0.879       0.866       +0.013         −0.0232 [−0.0355, −0.0103] *

*What this says.* The foundation models at 0.9 sit wholly below one on both
arms, and the window moves their signed slope by 0.011 to 0.028, always
further from one and nowhere toward it. The control is a different object:
on the expanding arm its interval covers one, and on the shared cells its
signed mean falls by 0.087 under the window. In signed terms the window
moves the control 3.4 to 7.8 times as far as a foundation model at 0.9
(0.0869 against 0.0254 and 0.0112, unrounded). H4's statistic therefore
compares a distance below one, at which both foundation models sit on both
arms, with a spread about one, where the control sits on the expanding arm;
a fall in the control's slope lowers its folded deviation on the cells where
it stood above one. What this book does not support: that the foundation
models' calibration slope is as sensitive to the context policy as the
control's, or that the rolling window helps or hurts a foundation model's
slope by a named amount against the control. The between-arm signed
reduction with an interval is not recorded; `between_arm_intervals.py`
carries only `cox_slope_deviation`.

*Note of 2026-09-19, later.* "3.4 to 7.8 times" above is 3.4 to 7.7: from
the unrounded weighted means the ratios are 3.417 and 7.733, and 7.8 is
0.0869 over 0.0112, the four-decimal figures in the parenthesis, which are
rounded and not the unrounded values it names.

*Note of 2026-09-19, later still.* TabICL's signed R in the table above is
0.779, not 0.780: the cell-weighted mean over the 160 criterion cells of
`experiments/2026-09-17-fm-arm-r-intervals/paired.csv` is 0.779495, and
0.780 is the four-decimal 0.7795 rounded once more. The difference +0.011
is unchanged.

### 2026-09-19 — what criterion 4's disagreement is carried by

No run. H4 stays undetermined on this book under kill criterion 4, as the
criterion's sign rule reads it; this entry names what the disagreement
between the scopes is carried by, which the Setting's second reading of
2026-09-17 left to the same-cells reading ("the regime, label or calendar,
until the same-cells reading says which"). That reading is recorded in
[`experiments/2026-09-17-fm-between-arm-intervals-outcome-reported`](../../experiments/2026-09-17-fm-between-arm-intervals-outcome-reported)
and is read here beside the primary one,
[`experiments/2026-09-17-fm-between-arm-intervals`](../../experiments/2026-09-17-fm-between-arm-intervals).
Nothing in the criterion changes.

*The scopes.* Of the 160 criterion cells, 28 are pre-flag, 17 straddle the
flag and 115 are flagged (`cells.csv` of either run, `criterion` True, one
model). The pre-flag cells are 13/9/5/1 on the builds of 2004H2, 2006H2,
2008H2 and 2010H2, the four oldest paired dates, and their cohorts run from
2005H1 to 2011H1. On them the two labels are one by construction, and the
reported-label run's pre-flag rows equal the primary's to the bit (all 108
pre-flag rows of the two `paired.csv` files, the criterion's pooling at
l. 245–271 of each).

*The rows.* E − R of mean |Cox slope − 1| at 0.9 per scope, `cohorts` `all`,
`draw` empty, seed 20260905; a star marks an interval that excludes zero.
Lines are of `paired.csv` in each run; the pre-flag rows are one table for
both labels. The last column is each model's own pre-flag row minus its
flagged row, a difference of two recorded points:

    model       pre-flag (28 cells)                flagged (115), primary             flagged (115), reported label      own scope gap, primary / reported
    scorecard   −0.0780 [−0.0852, −0.0710] * l247  −0.0852 [−0.0938, −0.0648] * l274  −0.0818 [−0.0903, −0.0663] * l274  +0.007 / +0.004
    gbm         −0.0639 [−0.0694, −0.0487] * l250  −0.0227 [−0.0295, −0.0136] * l277  −0.0179 [−0.0230, −0.0116] * l277  −0.041 / −0.046
    gbm-50k     −0.0500 [−0.0864, +0.0046]   l253  −0.0079 [−0.0472, +0.0337]   l280  −0.0178 [−0.0658, +0.0248]   l280  −0.042 / −0.032
    tabpfn      −0.0272 [−0.0525, −0.0111] * l256  −0.0317 [−0.0505, −0.0032] * l283  −0.0268 [−0.0470, +0.0007]   l283  +0.004 / −0.000
    tabicl      −0.0084 [−0.0321, +0.0044]   l259  −0.0196 [−0.0372, +0.0040]   l286  −0.0103 [−0.0268, +0.0105]   l286  +0.011 / +0.002

The criterion's rows, each foundation model minus GBM-50k, and the scope
difference beside them (pre-flag minus flagged on the same resample):

    row                         primary                                reported label
    tabpfn, pre-flag            +0.0227 [−0.0259, +0.0741]   l268      the same
    tabpfn, flagged             −0.0238 [−0.0478, +0.0099]   l295      −0.0090 [−0.0420, +0.0332]   l295
    tabicl, pre-flag            +0.0416 [−0.0055, +0.0866]   l269      the same
    tabicl, flagged             −0.0117 [−0.0399, +0.0177]   l296      +0.0075 [−0.0194, +0.0459]   l296
    scope difference, tabpfn    +0.0465 [+0.0005, +0.0802] * l328      +0.0318 [−0.0100, +0.0689]   l328
    scope difference, tabicl    +0.0533 [+0.0154, +0.0803] * l329      +0.0341 [−0.0059, +0.0628]   l329
    scope difference, gbm       +0.0008 [−0.0294, +0.0285]   l327      −0.0139 [−0.0526, +0.0256]   l327

*What the rows say.* The two GBMs' E − R is about 0.04 more negative on the
pre-flag cells than on the flagged ones, and the full-pool GBM, which has no
context draw, moves as GBM-50k does (the scope difference of the one against
the other is +0.0008), so the gap is not draw noise. Each foundation model's
E − R differs by at most 0.011 between the scopes, the scorecard's by 0.007.
The criterion's rows change sign between the scopes because the control's
term changes by 0.042 and the foundation models' do not. The same-cells
reading, the flagged cells under the reported label against the primary,
moves the flagged criterion rows by +0.015 (TabPFN) and +0.019 (TabICL) and
the control's own flagged E − R by 0.010, and takes the star off both scope
differences; under it the control's own scope gap is still 0.032. The label
accounts for at most a quarter of the control's gap, and on the pre-flag
cells, where the gap is carried, it cannot act at all.

*The sentence this book carries on H4:* "H4 is undetermined on this book
under kill criterion 4: the criterion's rows disagree in sign between the
pre-flag and the flagged scope. The disagreement is carried by the control.
GBM-50k's E − R is −0.050 on the 28 pre-flag cells and −0.008 on the 115
flagged cells, the full-pool GBM's −0.064 and −0.023, while each foundation
model's differs by at most 0.011 between the scopes. The pre-flag cells are
the 2005H1–2011H1 cohorts of the four oldest paired dates, on which the
label's two readings coincide, and the same-cells reading moves the flagged
rows by at most 0.019: the reporting regime does not account for the
disagreement; what the scopes separate is the crisis-era cells from the
rest, and it is the GBMs' E − R that differs between them."

Under the reported label TabICL's two scoped rows agree in sign and both
hold zero, so that label reads "killed: inside the interval" for TabICL
where the primary reads undetermined. Both are reported, as the note of
2026-09-17 requires, and both say the same to the claim. The criterion's
clause that a disagreement "belongs to the reporting regime of the label
rather than to the model" is the rationale the rule was written under; the
verdict is the rule's, and the cause named beside it is this reading's.

### 2026-09-19 — H5's rows read per draw

No run. The criterion's interval is unchanged: it was pre-registered ("the
bootstrap interval over context rows, seeds drawn with the resample") and
every H5 row was read under it. What this entry adds is a reading beside,
from the recorded cells, of two things: whether the three context draws
agree in sign, and how far apart they lie against the row interval's width.
No draw-level interval is computed; three points give none.

*The rows.* From `h5.csv` of
[`experiments/2026-09-17-fm-grid-in-sample`](../../experiments/2026-09-17-fm-grid-in-sample),
oe_high − oe_low with the higher-rate context first, seed 20260905; a star
marks an interval that excludes zero:

    arm  model       row                                  line
    E    gbm-50k     +0.0014 [−0.1111, +0.1031]           l4    known answer
    E    tabpfn      −0.0483 [−0.2209, +0.0967]           l7
    E    tabpfn@t1   +0.0204 [−0.0940, +0.1234]           l10
    E    tabicl      −0.0849 [−0.2929, +0.0931]           l13
    E    tabicl@t1   −0.0017 [−0.1409, +0.1159]           l16
    R    gbm-50k     +0.0049 [−0.1368, +0.1218]           l19   known answer
    R    tabpfn      −0.3546 [−0.5806, −0.1753] *         l22
    R    tabpfn@t1   +0.0337 [−0.1065, +0.1477]           l25
    R    tabicl      −0.6323 [−0.8971, −0.4050] *         l28
    R    tabicl@t1   −0.1386 [−0.3023, +0.0085]           l31

*The same contexts per draw.* From `cells.csv` of the same run,
`observed_over_expected`, the high context minus the low one (E: 2010H2-E −
2006H2-E; R: 2010H2-R − 2018H2-R); the lines are the high context's, then
the low one's:

    arm  model       draw 20260911              draw 20260912              draw 20260913              lines
    E    gbm-50k     0.9898 − 0.9932 = −0.003   0.9934 − 0.9906 = +0.003   0.9929 − 0.9882 = +0.005   72–74, 38–40
    E    tabpfn      1.3824 − 1.4412 = −0.059   1.4049 − 1.4367 = −0.032   1.4000 − 1.4545 = −0.054   75–77, 41–43
    E    tabpfn@t1   0.9954 − 0.9791 = +0.016   0.9956 − 0.9794 = +0.016   1.0054 − 0.9767 = +0.029   78–80, 44–46
    E    tabicl      1.3709 − 1.5242 = −0.153   1.4123 − 1.5106 = −0.098   1.3825 − 1.3855 = −0.003   81–83, 47–49
    E    tabicl@t1   0.9839 − 1.0274 = −0.044   0.9996 − 1.0209 = −0.021   0.9931 − 0.9334 = +0.060   84–86, 50–52
    R    gbm-50k     0.9993 − 0.9928 = +0.007   0.9990 − 0.9924 = +0.007   0.9990 − 0.9976 = +0.001   208–210, 276–278
    R    tabpfn      1.2434 − 1.6164 = −0.373   1.2449 − 1.5752 = −0.330   1.2502 − 1.6106 = −0.360   211–213, 279–281
    R    tabpfn@t1   1.0081 − 0.9734 = +0.035   1.0058 − 0.9776 = +0.028   1.0082 − 0.9698 = +0.038   214–216, 282–284
    R    tabicl      1.1925 − 1.7767 = −0.584   1.1310 − 1.6978 = −0.567   0.9719 − 1.7179 = −0.746   217–219, 285–287
    R    tabicl@t1   0.9681 − 1.0517 = −0.084   0.9206 − 1.0396 = −0.119   0.8007 − 1.0137 = −0.213   220–222, 288–290

*The known answer, per cell.* The entry of 2026-09-18 states the known answer
as observed over expected of one on 85 of 85 fitted-model cells. The same
table carries a sharper figure: GBM-50k's in-sample O/E lies in 0.9781–0.9993
over all 51 of its context cells (the lowest at 2016H2-E, draw 20260911,
l. 123; the highest at 2010H2-R, draw 20260911, l. 208), and in 0.9882–0.9993
on the four H5 contexts, while its per-cell bootstrap interval at 2018H2-R,
draw 20260911, is [0.8370, 1.1383] (l. 276) and its two H5 rows' intervals
are 0.21 and 0.26 wide.

*What this says.* The row interval is not the sampling distribution of an
in-sample row. A fitted model's in-sample O/E is pinned near one by the fit
whichever rows it is fitted on, so its variation across contexts is two
hundredths over 51 draws; resampling the rows while holding the in-sample
predictions fixed forgets that the predictions were conditioned on those
rows, and gives an interval 0.30 wide around it. The same holds, more
weakly, for a foundation model whose context is the scored set: TabPFN's O/E
at 2018H2-R moves by 0.041 across the three draws (l. 279–281) against a
per-cell interval 0.48 wide. The criterion's interval is therefore
conservative for every in-sample row: a kill under it is a kill under any
narrower reference, and a survival under it says little. The kills on the
rolling arm at 0.9 are also agreed on by every draw, to within 0.043
(TabPFN) and 0.179 (TabICL). The survivals divide. At 0.9 on the expanding
arm TabPFN's three draws agree in sign (−0.032 to −0.059, a 1.8-fold range);
TabICL's agree in sign and not in size (−0.153, −0.098, −0.003, the last
at zero to the third decimal). At 1.0 on the expanding arm TabICL's draws
disagree in sign (−0.044, −0.021, +0.060). At 1.0
TabPFN reads +0.016 to +0.038 on every draw of both arms, a small pull toward
the middle of the prevalence range that no row of this run can resolve; and
TabICL on the rolling arm reads −0.084, −0.119 and −0.213, every draw the same
sign, with its per-draw O/E at 2010H2-R spread from 0.80 to 0.97, its row
holding zero at the margin.

*The sentences.* H5 at 0.9 on the rolling arm: killed for both foundation
models, and the kill is the temperature's arithmetic, as the Setting's note
of 2026-09-17 withdrew the prior reading. Every other H5 row: "not killed
under an interval that the known answer shows is not the sampling
distribution of an in-sample row; the three draws read [range] and agree /
do not agree in sign." In particular this book does not support the
sentence that at 1.0 the in-sample level does not depend on prevalence:
TabPFN's three draws agree on a small positive dependence, TabICL's on the
rolling arm on a larger negative one, and neither is resolved. A reference
distribution the known answer passes, such as a resample over context
draws, needs ten or more draws and is not recorded.

### 2026-09-19 — the interval's other bound

No run. Every interval of this book is the percentile interval of the
resampled values (`src/outoftime/metrics.py` l. 759), the recorded method on
every row, and it stays the method: changing it after the verdicts would be
a rewrite. A percentile interval of a statistic with a skewed resampling
distribution sits off-centre about the point, so its other bound is read
here beside it: the basic interval, reflected about the point estimate from
the recorded bounds, [2v − hi, 2v − lo]. A star marks an interval that
excludes zero.

*H4's criterion rows,* each model minus GBM-50k, E − R of mean
|Cox slope − 1| at 0.9 and at 1.0, `cohorts` `all`, `draw` empty, from
`paired.csv` of
[`experiments/2026-09-17-fm-between-arm-intervals`](../../experiments/2026-09-17-fm-between-arm-intervals):

    scope               row          line   value     percentile             basic
    arm                 tabpfn       l25    −0.0162   [−0.0446, +0.0175]     [−0.0499, +0.0123]
    arm                 tabicl       l26    −0.0031   [−0.0345, +0.0254]     [−0.0317, +0.0282]
    arm                 tabicl@t1    l27    −0.0100   [−0.0500, +0.0194]     [−0.0394, +0.0300]
    arm                 tabpfn@t1    l28    −0.0248   [−0.0536, +0.0035]     [−0.0531, +0.0040]
    pre-flag            tabpfn       l268   +0.0227   [−0.0259, +0.0741]     [−0.0286, +0.0713]
    pre-flag            tabicl       l269   +0.0416   [−0.0055, +0.0866]     [−0.0035, +0.0886]
    pre-flag            tabicl@t1    l270   +0.0201   [−0.0260, +0.0617]     [−0.0215, +0.0662]
    pre-flag            tabpfn@t1    l271   +0.0079   [−0.0343, +0.0494]     [−0.0336, +0.0501]
    flagged             tabpfn       l295   −0.0238   [−0.0478, +0.0099]     [−0.0574, +0.0002]
    flagged             tabicl       l296   −0.0117   [−0.0399, +0.0177]     [−0.0411, +0.0165]
    flagged             tabicl@t1    l297   −0.0146   [−0.0537, +0.0165]     [−0.0458, +0.0244]
    flagged             tabpfn@t1    l298   −0.0313   [−0.0548, −0.0017] *   [−0.0610, −0.0078] *
    scope difference    tabpfn       l328   +0.0465   [+0.0005, +0.0802] *   [+0.0128, +0.0925] *
    scope difference    tabicl       l329   +0.0533   [+0.0154, +0.0803] *   [+0.0264, +0.0912] *
    scope difference    tabicl@t1    l330   +0.0347   [−0.0021, +0.0696]     [−0.0002, +0.0715]
    scope difference    tabpfn@t1    l331   +0.0392   [+0.0018, +0.0728] *   [+0.0056, +0.0767] *

*H5's rows,* from `h5.csv` of
[`experiments/2026-09-17-fm-grid-in-sample`](../../experiments/2026-09-17-fm-grid-in-sample):

    arm  model       line   value     percentile             basic
    E    gbm-50k     l4     +0.0014   [−0.1111, +0.1031]     [−0.1003, +0.1139]
    E    tabpfn      l7     −0.0483   [−0.2209, +0.0967]     [−0.1934, +0.1242]
    E    tabpfn@t1   l10    +0.0204   [−0.0940, +0.1234]     [−0.0826, +0.1347]
    E    tabicl      l13    −0.0849   [−0.2929, +0.0931]     [−0.2629, +0.1231]
    E    tabicl@t1   l16    −0.0017   [−0.1409, +0.1159]     [−0.1193, +0.1376]
    R    gbm-50k     l19    +0.0049   [−0.1368, +0.1218]     [−0.1120, +0.1465]
    R    tabpfn      l22    −0.3546   [−0.5806, −0.1753] *   [−0.5339, −0.1285] *
    R    tabpfn@t1   l25    +0.0337   [−0.1065, +0.1477]     [−0.0802, +0.1740]
    R    tabicl      l28    −0.6323   [−0.8971, −0.4050] *   [−0.8597, −0.3676] *
    R    tabicl@t1   l31    −0.1386   [−0.3023, +0.0085]     [−0.2856, +0.0251]

No star changes on any H4 criterion row or any H5 row of this book. The
flagged TabPFN row's basic upper bound, +0.0002, and the TabICL@1.0 scope
difference's, −0.0002 lower, sit at zero; neither crosses it.

*What H4's statistic is a level of.* The arm-scope reductions of the same
run, `paired.csv` l. 4–22: every model's E − R of mean |Cox slope − 1| is
negative on this book, starred for the scorecard (−0.0805), the full-pool
GBM (−0.0311), TabPFN (−0.0294), TabPFN at 1.0 (−0.0381) and TabICL at 1.0
(−0.0232), not starred for TabICL (−0.0164) and GBM-50k (−0.0132). On this
book the rolling window raised the slope error of every model, and "drift"
in H4's statement is the level the criterion names, the mean |slope − 1|
over the arm's cells, not its change with age.

### 2026-09-19 — the verdicts the Setting stated, carried here

The Setting's note of 2026-09-17 stated, in three places, what a criterion
read on this book. From this date the Setting carries no statement of a
verdict, as it already carries no number produced by a fit or a pooling; the
three passages left it and are quoted here whole, as they stood, and each
place they stood now points to this entry. Nothing is recomputed, and no
hypothesis, criterion or reading changes. Where a sentence both stated a
verdict and fixed a reading, the reading stayed in the Setting and is also
inside the quotation below.

Where each verdict is read from. H4's arm and scoped rows are rows of
`paired.csv` of
[`experiments/2026-09-17-fm-between-arm-intervals`](../../experiments/2026-09-17-fm-between-arm-intervals),
which superseded the recording of 2026-09-16 with the verdict string
corrected (entry of 2026-09-17 on the between-arm pooling with the
contrast); the scope difference is the same run's `scope_difference` rows,
l. 326–331, and the entry of 2026-09-19 on what criterion 4's disagreement
is carried by reads them. H5's rows are `h5.csv` of
[`experiments/2026-09-17-fm-grid-in-sample`](../../experiments/2026-09-17-fm-grid-in-sample),
l. 4–31, read per draw in the entry of 2026-09-19 above.

From the note of 2026-09-17, on H4 under criterion 4:

> *H4 is undetermined on this book, as kill criterion 4 reads it.* At arm
> scope over the 160 criterion cells at 0.9 the row holds zero for both
> foundation models under every seed; on that row alone the kill would fire
> inside the interval. Under the two scopes criterion 4 compares, the 28
> pre-flag cells and the 115 flagged cells, the signs differ, and the
> criterion says what follows: H4 is reported as undetermined on this book, with both
> scopes and the sensitivity reading beside it. The recorded run computes
> the disagreement and prints it but reads the verdict off the arm row alone,
> so its summary says "killed: inside the interval"; the script is corrected
> to read the criterion and the pooling is recorded again as superseding,
> which must reproduce every value, bound and star to the bit, the verdict
> alone changing.

From the same note, closing the paragraph on criterion 4's second reading:

> On H4 both scoped rows hold zero and the
> difference is expected to hold zero; the superseding run says whether it
> does.

The entry of 2026-09-17 on the between-arm pooling with the contrast records
that the expectation is not met ("the expectation the scope difference does
not meet"), and the entry of 2026-09-19 on what criterion 4's disagreement is
carried by reads it.

From the same note, on H5:

> On
> the rolling arm the criterion fires for both foundation models; on the
> expanding arm both hold zero over its 1.8-fold range.

### 2026-09-19, later — the smoothing note's record of the falsifying run and of Lending Club, carried here

The Setting's smoothing note of 2026-09-17 said, so that no reader would take
it for blind where it was not, what was already on the record when its
reading was fixed, and in saying so stated a verdict and a direction: that
H2's clause for settling the question on the falsifying run was not met, and
where both foundation models' signed slopes on Lending Club's falsifying
build sat against one and against the scorecard at 1.0. The Setting from
this date carries no statistic of a model under study on this book's rows,
no statement of what a hypothesis or a kill criterion of this file read, and
no statistic of a model under study on the other book that gives a direction
on a reading of this file. The passage left it and is quoted here whole, as
it stood; its place now says that the record existed and names this entry,
and says nothing of what the record read. Nothing is recomputed, and no
hypothesis, criterion or reading changes.

Where each number is read from. The audit's finding on the falsifying run
is this log's cold audit of the falsifying run, below, in its own words.
Lending Club's slopes are EXP-002's: the foundation models' at 1.0 are read
in [EXP-002-log.md](EXP-002-log.md)'s entry of 2026-09-06 on the temperature
probe, from
[`experiments/2026-09-06-lc-2015h1e-intervals-probe3`](../../experiments/2026-09-06-lc-2015h1e-intervals-probe3),
and the scorecard's per-cohort slopes in the entry of 2026-09-06 on the
pooled intervals re-recorded with the calibration statistics, from
[`experiments/2026-09-06-lc-2015h1e-intervals-tfm2`](../../experiments/2026-09-06-lc-2015h1e-intervals-tfm2).

From the smoothing note of 2026-09-17, on what is already on the record:

> the cold audit of the falsifying run, recorded in
> [EXP-005-log.md](EXP-005-log.md), states that
> every foundation-model slope at 0.9 on 2004H2-E's three cohorts lay inside
> the scorecard's per-cohort Wald interval; and on Lending Club the signed
> slopes of both foundation models and every classical model on 2015H1-E's
> three cohorts are quoted at both temperatures in EXP-002's log of
> 2026-09-06 — at 1.0 TabICL 1.13 to 1.18 and TabPFN 1.16 to 1.23 against the
> scorecard's 1.07 to 1.21, every model above one, TabPFN above the scorecard
> on every cohort and TabICL on two of three.

### 2026-09-19, later — both arm-level poolings and the in-sample reading recorded again at `386c629`, with the files they read hashed

[`experiments/2026-09-19-fm-arm-e-intervals`](../../experiments/2026-09-19-fm-arm-e-intervals)
(14,061 s),
[`-fm-arm-r-intervals`](../../experiments/2026-09-19-fm-arm-r-intervals)
(11,923 s) and
[`-fm-grid-in-sample`](../../experiments/2026-09-19-fm-grid-in-sample)
(291 s), all at `386c629` on the Apple node, all exit 0 on a clean tree, on
the machine of the recordings they replace: the same host, the same CPU and
the same interpreter binary by hash. The two poolings ran side by side, and
the in-sample reading after the expanding arm. Each command is its
baseline's with the output directory alone changed. **They supersede
[`experiments/2026-09-18-fm-arm-e-intervals`](../../experiments/2026-09-18-fm-arm-e-intervals),
[`experiments/2026-09-17-fm-arm-r-intervals`](../../experiments/2026-09-17-fm-arm-r-intervals)
and
[`experiments/2026-09-17-fm-grid-in-sample`](../../experiments/2026-09-17-fm-grid-in-sample);
cite them.**

*Why they were recorded.* `891e78f` made `arm_intervals.py` and
`in_sample_level.py` write `inputs.json` and import `scripts/record_run.py`
for the hash. Against this checkout the three recordings read red under
`check_claims`: each script has changed since its run, and `record_run.py`
runs under their commands without a pin. Between `9f0e110`, the commit all
three baselines name, and `386c629` the two scripts differ by the hashing
block, its docstring and the import, seventeen and thirteen added lines and
none removed, and `record_run.py` does not differ.

*What comes back.* On each arm `paired.csv` (8,904 rows on the expanding
arm, 6,552 on the rolling arm), `paired-seeds.csv` (18,522 and 13,230) and
all four figures are byte-identical to the recording they replace. So are
the six tables of the in-sample reading — `cells.csv` (289 rows),
`cohort-cells.csv` (7,242), `h5.csv` and `h5-seeds.csv` (30 each),
`in-sample-slope.csv` (10) and `in-sample-slope-seeds.csv` (30) — and its
figure. Every value, bound and star is reproduced to the bit. Of
`intervals.json` every leaf is present on both sides, 4,228 and 3,257, and
of `summary.json` 256; one changes in each file, the wall. The standard
output differs on its timing lines alone. The error output of the
in-sample reading is empty on both sides; that of each pooling differs on
one line, the line of `arm_intervals.py` its first numpy warning names, 542
to 547, the five lines the hashing block adds above it.

*What is added.* `inputs.json`: 2,449 entries for the expanding arm, 1,441
for the rolling arm and 3,872 for the in-sample reading. A pooling's list is
the `intervals.json` of each grid run it names, every file of the score
directories those runs name, and the builds' `cells.csv`; the in-sample
reading's is every file of the score directories on its command and the
builds' `builds.json`. Every entry re-hashes against the file on disk without a
mismatch, parquet files outside git included. The manifests pin
`scripts/record_run.py` beside the other code hashes and carry each
script's new hash.

What is not here. A reading. Nothing is read in these runs that the
recordings they replace did not already hold, and every entry above that
reads those recordings reads these unchanged.

*Note of 2026-09-20.* "re-hashes against the file on disk without a mismatch"
holds on a tree whose text files carry LF endings, which is the tree all three
ran on. Repeated on a Windows checkout of this repository it does not read that
way: 71 entries of the expanding arm's list, 81 of the rolling arm's and 144 of
the in-sample reading's do not match the file as it stands on disk, each of
them a tracked text file whose working copy carries CRLF endings while the blob
it was committed from carries LF. `.gitattributes` normalises on commit rather
than on a checkout already made, so the tree reads clean and the difference
shows only in a hash. Every one of those entries hashes to the git blob at
HEAD, and no entry of the three lists is unaccounted for: 2,378 of 2,449, 1,360
of 1,441 and 3,728 of 3,872 match the file on disk and the rest the blob, none
neither. The parquet files, which lie outside git and carry no line endings,
match on disk throughout.

### 2026-09-20 — the expanding arm with the refit control, recorded again at `386c629`

[`experiments/2026-09-20-fm-arm-e-intervals-refit-control`](../../experiments/2026-09-20-fm-arm-e-intervals-refit-control),
15,513.7 s on the Apple node, exit 0 on a clean tree at `386c629`, on the
machine of the recording it replaces and with the same interpreter binary by
hash. Its command is that recording's with the output directory alone changed:
the nine expanding-arm interval grids, the nine `*-control-refit` directories,
`--check-seeds 20260906,20260907`, the builds' `cells.csv` and `--h2-scopes`.
**It supersedes
[`experiments/2026-09-17-fm-arm-e-intervals-refit-control`](../../experiments/2026-09-17-fm-arm-e-intervals-refit-control);
cite it.**

*Why it was recorded.* Against this checkout the recording it replaces reads
`changed` under the recorded-code gate on two files, `arm_intervals.py` and
`build_intervals.py` at `1ad2915`, and a run cited from the claim ledger is
held to the stricter rule that its code in the checkout is identical to what
ran. The readings of the refit control are read beside H1's and H3's on this
book, so the pooling was recorded again at the commit those readings are
written against.

*This one is not a bit-repeat, and what it adds was named before it ran.*
`386c629` carries the signed `cox_slope` among the arm metrics and `1ad2915`
does not, so the recording holds whole added rows: `paired.csv` 9,936 to
11,448 and `paired-seeds.csv` 21,420 to 24,696. Every one of the 1,512 and
3,276 added rows names `cox_slope`, the counts this run writes for
`cox_slope_deviation` exactly, and their keys sit one for one with that
metric's — the same fit on the same cells, with the folded distance left
folded and the signed value beside it.

*What comes back.* All 9,936 rows of `paired.csv` and 21,420 of
`paired-seeds.csv` are present here and none differs, on value, on either
bound, on the standard error, on the star or on any other shared column, at
full precision; the headers are byte-identical. Neither file of either
recording carries a duplicate key, so the identity is by construction and not
by one row standing in for another. Of the four figures three are identical by
sha256 and `arm-differences.png` differs, the figure that plots every pooled
metric and so had to take the added one. Of `intervals.json` all 4,457 leaves
of the earlier recording are present and ten change: four are the single
insertion of `cox_slope` into the list of pooled metrics, five are seed-check
counts re-derived over a table 1,092 difference rows larger, and one is the
wall. `largest_bound_movement` is 0.042303553451 in both. The seed check's
list of stars that move with a check seed grows from 203 entries to 219; the
203 are here unchanged and all sixteen added name `cox_slope`. The standard
output holds 657 unchanged lines against 11 removed and 98 added, and every
line on either side falls in a class: ten timing lines and one re-derived
seed-check sentence on each, and on this side 77 `cox_slope` rows and a
nine-line block of the signed Cox slope. No other line changed. The error
output differs on one line, the line of `arm_intervals.py` its first numpy
warning names, 532 to 547.

*Against the pooling of the same arm without the refit.* Every row of
[`experiments/2026-09-19-fm-arm-e-intervals`](../../experiments/2026-09-19-fm-arm-e-intervals)
— 8,904 in `paired.csv` and 18,522 in `paired-seeds.csv` — is present here and
none differs. The refit control enters as a model of its own and moves no row
of the reading it sits beside, so a figure read from either recording is the
same figure read from this one.

*What is added beside the rows.* `inputs.json`: 2,512 entries over 64
directories, the `intervals.json` of each grid run named on the command, every
file of the score directories those runs name, and the builds' `cells.csv`.
Every entry is accounted for: 2,405 match the file as it stands on disk and the
other 107 the git blob at HEAD, the class of tracked text file the note above
describes. The manifest pins `scripts/record_run.py` beside the other code
hashes, and every code file of this recording is identical at HEAD.

*What it reads.* What the entry of 2026-09-17 records of this pooling stands as
written, every row it quotes coming back to the bit: on H1 the same standing
under both identifications, and on H3 agreement on the model's own training
reference with a difference on the first-scored-cohort reference, where TabICL
reads −0.0079 [−0.0231, +0.0022] against this control and holds zero, against
−0.0105 [−0.0288, −0.0002] under the recorded control. Where a standing differs
between the two controls both are reported, the recorded control's is the
criterion's, and no more than the weaker of the two is claimed. The signed Cox
slope of the added rows is new here and nothing in this file is read from it.

### 2026-09-20 — the rescaled control's in-sample reading, recorded again at `1f32bca`

[`experiments/2026-09-20-fm-h5-rescaled-control-in-sample`](../../experiments/2026-09-20-fm-h5-rescaled-control-in-sample),
885.3 s on the Windows laptop, exit 0 on a clean tree at `1f32bca`, on the
machine of the recording it replaces. Its command is that recording's with the
output directory alone changed, 42 arguments read from the superseded
manifest: the seventeen classical score runs of 2026-09-13, the seventeen
rescaled copies, the build run's record and `--check-seeds 20260906,20260907`.
**It supersedes
[`experiments/2026-09-17-fm-h5-rescaled-control-in-sample`](../../experiments/2026-09-17-fm-h5-rescaled-control-in-sample);
cite it.**

*Why it was recorded.* Against this checkout the earlier recording reads
`changed` under the recorded-code gate on `in_sample_level.py` and
`build_intervals.py` at `8e3a020`, and a run cited from the claim ledger is
held to the stricter rule that its code in the checkout is identical to what
ran. The demonstration this reading carries is what a ledger row on H5 must
point at, so the pooling was recorded again at the commit that row will be
written against.

*Not a bit-repeat, and what would be added was named before it ran.* Since
`8e3a020` `in_sample_level.py` has gained the Cox slope of every context cell
with its known answer on the scorecard's own pool, 211 lines, and
`build_intervals.py` 24. The prediction written before the run: three files
added (`inputs.json`, `in-sample-slope.csv`, `in-sample-slope-seeds.csv`),
`cells.csv` keeping its 136 rows and sixteen columns to the bit with nine
columns added, **`h5.csv` and `h5-seeds.csv` identical to the bit** because
H5's statistic did not change, and a moved digit there to be reported rather
than adopted.

*What comes back.* All of it as predicted. `h5.csv` and `h5-seeds.csv`: twelve
rows each, present on both sides, **0 differing on any field** — the
demonstration's own numbers, `gbm-50k@t0.9` −0.395 [−0.624, −0.220] on the
rolling arm and −0.064 [−0.267, +0.123] on the expanding, `gbm-50k` +0.005 and
+0.001, reproduced exactly. `cells.csv`: the same 136 rows, none differing on
any of the sixteen columns the earlier recording holds, and nine added
(`cox_converged`, `cox_slope`, its two bounds, `cox_intercept`, its two
bounds, `slope_known_answer`, `h5_context`). `summary.json`: all 199 leaves
present, 44 added, one changed, the wall. The error output is byte-identical.
The standard output holds 203 unchanged lines against three removed and
fourteen added: two timing lines and the wall on each side, and on this side
the known-answer line for the Cox fit, the two slope poolings and the block of
signed slopes. No line that carries a reading changed.

*Two things the prediction got wrong, both knowable from the command.* It
expected `cohort-cells.csv` among the added files: that table is written only
under `--with-cohorts`, which this command does not pass and the in-sample
grid run does. And it allowed `level-prevalence.png` to change; the figure is
identical by sha256, which follows from the same flag, since the figure takes
the cohort table and has none on either side, and the Cox reading does not
enter it.

*What is added beside the rows.* `inputs.json`, 137 entries: every file of the
seventeen score directories and the seventeen rescaled copies, and the build
run's record. Every entry is accounted for here, 68 matching the file on disk
and 69 the git blob at HEAD, the tracked text files a Windows checkout holds
with CRLF endings. Every code file of this recording is identical at HEAD.

*What it reads.* What the entry of 2026-09-17 records of this pooling stands as
written, every row it quotes coming back to the bit; the label on the rescaled
rows is the same wrong one, from the same rule, and nothing here rests on it.
What is new is the in-sample Cox slope, which sits above one for the control
on both arms and for its rescaled copy alike (1.5024 [1.4216, 1.5847] and
1.3521 [1.2794, 1.4262] on the expanding arm, 1.3565 [1.3152, 1.3938] and
1.2208 [1.1837, 1.2544] on the rolling), and an in-sample slope above one is
confounded with the pull toward a row's own label, so it reads nothing on its
own. The known answer holds: 17 of 17 scorecard pool cells read slope one and
intercept zero within 0.0001.

### 2026-09-22 — four poolings and the in-sample reading recorded again at `a36c751`

`a36c751` changed `scripts/score_context.py`, which the manifests of these
recordings pin, so each read `changed` under `check_claims`. Nothing between
`386c629` and `a36c751` touches `arm_intervals.py`, `grid_in_sample.py` or
`src/`. Each was recorded again at `a36c751` on the Apple node, the machine
of the recording it replaces, on a clean tree, exit 0. Each command is the
replaced recording's command with the output directory alone changed, and
every entry of each `inputs.json` hashes the same on both sides.

| Recording | Supersedes | Wall |
| --- | --- | --- |
| [`2026-09-21-fm-arm-e-intervals`](../../experiments/2026-09-21-fm-arm-e-intervals) | [`2026-09-19-fm-arm-e-intervals`](../../experiments/2026-09-19-fm-arm-e-intervals) | 14,196.6 s |
| [`2026-09-21-fm-arm-e-intervals-refit-control`](../../experiments/2026-09-21-fm-arm-e-intervals-refit-control) | [`2026-09-20-fm-arm-e-intervals-refit-control`](../../experiments/2026-09-20-fm-arm-e-intervals-refit-control) | 16,239.5 s |
| [`2026-09-22-fm-grid-in-sample`](../../experiments/2026-09-22-fm-grid-in-sample) | [`2026-09-19-fm-grid-in-sample`](../../experiments/2026-09-19-fm-grid-in-sample) | 307.2 s |
| [`2026-09-22-fm-arm-r-intervals-refit-control`](../../experiments/2026-09-22-fm-arm-r-intervals-refit-control) | [`2026-09-21-fm-arm-r-intervals-refit-control`](../../experiments/2026-09-21-fm-arm-r-intervals-refit-control) | 13,042.3 s |

**Each supersedes the recording beside it; cite it.**

*What comes back.* Every CSV and every figure is byte-identical to the
recording it replaces: `paired.csv` and `paired-seeds.csv` on the three
poolings (8,904 and 18,522 rows, 11,448 and 24,696, 10,908 and 23,436), and
`cells.csv`, `cohort-cells.csv`, `h5.csv`, `h5-seeds.csv`,
`in-sample-slope.csv` and `in-sample-slope-seeds.csv` on the in-sample
reading. Of `intervals.json` and `summary.json` every leaf is present on
both sides, and one differs in each, the wall. The standard output differs
on its timing lines alone. The error output is the same on both sides:
empty for the in-sample reading, and the same six lines of numpy warning
for the three poolings.

What is not here. A reading. Every entry above that reads a replaced
recording reads its replacement, to the bit.

### 2026-09-23 — the three between-arm poolings recorded again at `a36c751`

H4's three poolings were `changed` under `check_recorded_code`, each
pinning a module a later commit had changed: the primary at `116b5cb`, the
outcome-reported pooling at `5130710`, the refit control at `1ad2915`. They
were recorded once at `5c65336`; `a36c751`, committed before the last of
those finished, changed `scripts/score_context.py`, which they pin. So each
is recorded a second time at `a36c751`, on the Apple node, the machine of
the recording it replaces, on a clean tree, exit 0. Each
command is the command of the 2026-09-17 recording with the output
directory alone changed. The primary and the outcome-reported pooling ran
beside each other and the refit control ran alone afterwards, the shape of
the runs they replace.

| Recording | Supersedes | Wall |
| --- | --- | --- |
| [`2026-09-22-fm-between-arm-intervals`](../../experiments/2026-09-22-fm-between-arm-intervals) | [`2026-09-17-fm-between-arm-intervals`](../../experiments/2026-09-17-fm-between-arm-intervals) | 12,205.4 s |
| [`2026-09-22-fm-between-arm-intervals-outcome-reported`](../../experiments/2026-09-22-fm-between-arm-intervals-outcome-reported) | [`2026-09-17-fm-between-arm-intervals-outcome-reported`](../../experiments/2026-09-17-fm-between-arm-intervals-outcome-reported) | 12,935.6 s |
| [`2026-09-22-fm-between-arm-intervals-refit-control`](../../experiments/2026-09-22-fm-between-arm-intervals-refit-control) | [`2026-09-17-fm-between-arm-intervals-refit-control`](../../experiments/2026-09-17-fm-between-arm-intervals-refit-control) | 13,628.4 s |

**Each supersedes the recording beside it; cite it.** Every code file each
of them pins hashes at `a36c751` to its recorded value, 19 of 19.

*What comes back.* Every CSV and every figure is byte-identical to the
2026-09-17 recording: `paired.csv`, `paired-seeds.csv` and `cells.csv`
(1,347, 525 and 3,264 rows on the primary and the outcome-reported pooling,
1,547, 606 and 3,840 on the refit control), `arm-cells.png` and
`build-rows.png`. Every entry of each `inputs.json` hashes the same on both
sides. Of `summary.json` every leaf is present on both sides, and one
differs in each, the wall. The standard output differs on its timing lines
alone. The error output is empty on all three; the 2026-09-17 primary
carries one line more, matplotlib building its font cache.

*The intermediate recording.* The three recordings at `5c65336`,
[`2026-09-21-fm-between-arm-intervals`](../../experiments/2026-09-21-fm-between-arm-intervals),
[`-outcome-reported`](../../experiments/2026-09-21-fm-between-arm-intervals-outcome-reported)
and
[`-refit-control`](../../experiments/2026-09-21-fm-between-arm-intervals-refit-control),
are kept as the record of that pass and are not cited. They are `changed`
on `scripts/score_context.py` alone, and they agree with both the
2026-09-17 recordings and the `a36c751` ones on the same terms as above:
every CSV, figure and `inputs.json` entry equal to the byte, `summary.json`
differing in the wall.

What is not here. A reading. Nothing in the ledger cites a between-arm
pooling of this book yet; the H4 row, when it comes, cites these.

### 2026-09-23 — the nominal matrix's poolings recorded again at `a36c751`

Since the `upb_nominal` trigger fired, every verdict of this book is
reported on both matrices, the ratio's reading being the criterion's. The
nominal matrix's four readings were `changed` under `check_recorded_code`:
the two arm poolings and the in-sample reading were recorded at `1c786fe`,
the between-arm pooling at `1ad2915`, and later commits changed modules
each of them pins. Each is recorded again at `a36c751`, on the Apple node,
the machine of the recording it replaces, on a clean tree, exit 0. Each
command is the replaced recording's command with the output directory
changed, and the two arm poolings add `--h2-scopes`, which the ratio
matrix's cited arm poolings carry.

| Recording | Supersedes | Wall |
| --- | --- | --- |
| [`2026-09-23-fm-arm-e-intervals-upb-nominal`](../../experiments/2026-09-23-fm-arm-e-intervals-upb-nominal) | [`2026-09-16-fm-arm-e-intervals-upb-nominal`](../../experiments/2026-09-16-fm-arm-e-intervals-upb-nominal) | 14,277.1 s |
| [`2026-09-23-fm-arm-r-intervals-upb-nominal`](../../experiments/2026-09-23-fm-arm-r-intervals-upb-nominal) | [`2026-09-16-fm-arm-r-intervals-upb-nominal`](../../experiments/2026-09-16-fm-arm-r-intervals-upb-nominal) | 11,983.4 s |
| [`2026-09-23-fm-between-arm-intervals-upb-nominal`](../../experiments/2026-09-23-fm-between-arm-intervals-upb-nominal) | [`2026-09-17-fm-between-arm-intervals-upb-nominal`](../../experiments/2026-09-17-fm-between-arm-intervals-upb-nominal) | 11,631.9 s |
| [`2026-09-23-fm-grid-in-sample-upb-nominal`](../../experiments/2026-09-23-fm-grid-in-sample-upb-nominal) | [`2026-09-16-fm-grid-in-sample-upb-nominal`](../../experiments/2026-09-16-fm-grid-in-sample-upb-nominal) | 306.0 s |

**Each supersedes the recording beside it; cite it.** Every code file each
pins hashes at `a36c751` to its recorded value: 17 of 17 on the arm
poolings and the in-sample reading, 19 of 19 on the between-arm pooling.
Every entry of the four `inputs.json` hashes the same as the checkout, and
the four agree with each other on every path they share.

*What comes back.* The between-arm pooling is byte-identical to the
recording it replaces in every CSV and figure: `paired.csv`,
`paired-seeds.csv` and `cells.csv` (1,347, 525 and 3,264 rows),
`arm-cells.png` and `build-rows.png`; `summary.json` differs in the wall
alone. The other three read code that grew after `1c786fe`, and they add
rows and never change one. Every row of each replaced recording is present,
equal to the bit in value, bounds and standard error, with no star moved:
4,536 and 8,883 rows of `paired.csv` and `paired-seeds.csv` on arm E,
4,200 and 8,127 on arm R, 289 rows of the in-sample `cells.csv`. The rows
added on the arms are the scopes of `--h2-scopes` (the crisis and 2022
cells, per arm and per build, and `oe_ratio_2022`), the pre-flag and
flagged scopes the pooling reads from `--cells` since `80afaa8`, and the
signed Cox slope pooled since `9f0e110`; arm E's `paired.csv` goes from
4,536 to 8,904 rows, arm R's from 4,200 to 8,484. Of the star changes under
a check seed, every one of the replaced recording is present, and the
added ones all fall on a new scope or metric. On the added scopes the
early-cohort stability index has no cohort in some cells, so the error
output carries six lines of numpy's warning on an empty mean, and 644 rows
on each arm hold no value; the 28 such rows of the replaced recordings are unchanged.
The in-sample reading adds nine per-cell columns to `cells.csv`, the Cox
fit's among them, and
the files `in-sample-slope.csv`, `in-sample-slope-seeds.csv` and
`inputs.json`, and its wall grows by the Cox fits. `arm-differences.png`
on each arm is drawn from the larger table and differs; every other figure
is byte-identical.

What is not here. A reading. The H4 reading on this matrix is the
2026-09-17 one, to the bit; the ledger row for H4 carries it beside the
criterion's.

### 2026-09-23 — the rolling arm on the nominal matrix, beside C-017 to C-019

The rows the ledger holds on the rolling arm, C-017 to C-019, read the
ratio matrix and are no criterion's rows. Their nominal-matrix reading is
[`2026-09-23-fm-arm-r-intervals-upb-nominal`](../../experiments/2026-09-23-fm-arm-r-intervals-upb-nominal),
set here beside the recording they cite,
[`2026-09-22-fm-arm-r-intervals-refit-control`](../../experiments/2026-09-22-fm-arm-r-intervals-refit-control).
The nominal pooling holds no refit control. Where a standing moves between
the matrices, it moves as follows; the seed checks agree with the primary
seed on every row below.

- *Cox-slope deviation (C-017).* TabICL − GBM-50k is +0.0355 [+0.0035,
  +0.0663] with the cohorts fixed, above zero beyond the interval under all
  three seeds, and holds zero with the cohorts resampled ([−0.0034,
  +0.0789]). On the ratio matrix it holds zero both ways (+0.0239
  [−0.0006, +0.0456] fixed).
- *The slope of AUC on age (C-018).* With one intercept per build, TabICL −
  GBM-50k is −0.000098 [−0.000177, −0.000006] with the cohorts fixed, below
  zero beyond the interval under all three seeds, the side a kill would
  read, and holds zero with the cohorts resampled ([−0.000245, +0.000040]);
  on the ratio matrix it holds zero both ways (−0.000026 fixed). Against
  the scorecard both foundation models lie below zero beyond the interval
  with the cohorts fixed and resampled, −0.000336 [−0.000553, −0.000126]
  and −0.000397 [−0.000633, −0.000191] resampled, where the ratio matrix's
  rows hold zero resampled. With one intercept per cohort, TabPFN −
  scorecard is −0.000179 [−0.000373, −0.000026] with the cohorts fixed,
  where the ratio's holds zero, and TabICL − scorecard reverses its sign
  inside the interval. The scorecard's own slope is the shallowest under
  both identifications on the nominal matrix (−0.001033 per build and
  −0.000161 per cohort), where on the ratio matrix TabICL's is the
  shallowest per cohort.
- *Stability against the first cohort (C-019).* TabICL − GBM-50k is
  +0.0099 [−0.0012, +0.0181] and holds zero, where the ratio matrix's row
  lies above zero beyond the interval with the cohorts fixed (+0.0066
  [+0.0002, +0.0145]).

What is not here. A verdict: none of these rows is a criterion's row, on
either matrix.

### 2026-09-24 — the `dti_kept` ablation's fitted-model poolings, registered on 2026-09-13 and computed on 2026-09-24

The note of 2026-09-13 registers the fifteen-column matrix — the fourteen
and `dti` with its missing values a level and its range clipped to 50 — as
the ablation reported beside every verdict of this experiment, and names two
readings from it: per model the paired difference in AUC and in Brier
between the two matrices on the falsifying cells, with the trigger for a
foundation-model grid on the fifteen columns; and, for the three fitted
models, every pooling of H1 to H3 on both matrices with its sign. The first
reading was taken on 2026-09-14, above, on the rows the note of 2026-09-14
fixed before the falsifying run, both foundation models at 0.9 on AUC and on
Brier: all four hold zero under all three seeds, and the trigger did not
fire. The recorded summary of
[`2026-09-14-fm-2004h2e-ablation-dti-kept`](../../experiments/2026-09-14-fm-2004h2e-ablation-dti-kept)
also lists the two rows at 1.0 on Brier, `tabicl@t1` and `tabpfn@t1`, as
excluding zero. The rule does not name them; `ablation_intervals.py`
counted them until 2026-09-15, as the entry of that day says, and they fire
nothing. No foundation model was scored on the fifteen columns beyond the
falsifying build. The second reading was not computed until 2026-09-24. The score runs existed since
2026-09-13 (`experiments/2026-09-13-fm-<build>-scores-dti-kept`, seventeen
builds, `--ablation dti_kept`); no interval run and no arm pooling had read
them, and C-025 to C-027 entered the ledger without this reading beside them:
they report the nominal matrix beside their verdicts and do not name this ablation. It is
reported here late.

The runs, all at `c697dd1` from a clean tree on the M4 Pro node:
seventeen per-build interval runs
[`2026-09-24-fm-<build>-intervals-grid-dti-kept`](../../experiments/2026-09-24-fm-2004h2e-intervals-grid-dti-kept)
by `build_intervals.py` over the `dti_kept` score runs, with the check seeds
20260906 and 20260907 and the cells record of
[`2026-09-13-fm-vintage-builds2`](../../experiments/2026-09-13-fm-vintage-builds2);
and two arm poolings by `arm_intervals.py --h2-scopes`,
[`2026-09-24-fm-arm-e-intervals-dti-kept`](../../experiments/2026-09-24-fm-arm-e-intervals-dti-kept)
over the nine expanding builds and
[`2026-09-24-fm-arm-r-intervals-dti-kept`](../../experiments/2026-09-24-fm-arm-r-intervals-dti-kept)
over the eight rolling ones — the command of the ratio-matrix poolings with
the fifteen-column inputs in place of the fourteen-column ones. Each holds
the scorecard and the full-pool GBM, with GBM-50k on its three context
draws, no foundation model and no refit control; the cells above the floors are the
ratio matrix's, 196 of 234 on the expanding arm and 160 of 192 on the
rolling arm, cohort for cohort. The fourteen-column figures below are
[`2026-09-21-fm-arm-e-intervals`](../../experiments/2026-09-21-fm-arm-e-intervals)
(whose classical rows equal those of the refit-control pooling C-025 and
C-026 cite, on all 1,908 of them) and
[`2026-09-22-fm-arm-r-intervals-refit-control`](../../experiments/2026-09-22-fm-arm-r-intervals-refit-control).
The nominal matrix is a different fourteen-column matrix and is not compared
here. Every figure is the primary seed's with the cohorts held fixed unless
it says otherwise; the fifteen-column figure follows the fourteen-column one.

*What the criterion rows quote, on the expanding arm.* The classical
readings C-025 to C-027 set beside their verdicts stand on the fifteen
columns. The own AUC slopes on the build intercept are a little shallower
with `dti` — scorecard −0.001047 → −0.000977, GBM −0.001207 → −0.001125,
GBM-50k −0.001335 → −0.001260 — every one below zero beyond its interval,
the control's the steepest on both matrices. GBM-50k − scorecard on the
mean absolute Cox-slope deviation, the classical comparison C-027 reads, is
+0.0201 [+0.0043, +0.0365] → +0.0197 [+0.0016, +0.0444], starred under all
three seeds with the cohorts fixed and holding zero with them resampled on
both matrices; the signed Cox slope's point sits below one for every model
on both (scorecard 0.8682 → 0.8754, GBM 0.9108 → 0.8961, GBM-50k 0.9515 →
0.9721), GBM-50k's interval covering one on both ([0.8891, 1.0504] →
[0.9311, 1.0201]). The PSI levels are higher with `dti` — scorecard 0.1314 →
0.1371, GBM 0.1059 → 0.1131, GBM-50k 0.1049 → 0.1208 — and both boosted
models still sit below the scorecard beyond the interval with the cohorts
fixed: GBM − scorecard −0.0255 [−0.0263, −0.0249] → −0.0240 [−0.0247,
−0.0234] under all three seeds, fixed and resampled alike; GBM-50k − scorecard −0.0265 [−0.0351, −0.0197] → −0.0163
[−0.0202, −0.0097] under all three seeds fixed, but with the cohorts
resampled that star is lost (−0.0265 [−0.0451, −0.0091] → −0.0163
[−0.0395, +0.0018]).

*H1 on the expanding arm.* On the build intercept every classical
difference keeps its sign and its star: GBM − scorecard −0.000159
[−0.000239, −0.000080] → −0.000148 [−0.000225, −0.000073], GBM-50k − GBM
−0.000129 [−0.000225, −0.000051] → −0.000135 [−0.000193, −0.000081],
GBM-50k − scorecard −0.000288 [−0.000397, −0.000182] → −0.000283
[−0.000367, −0.000201], each below zero under all three seeds with the
cohorts fixed on both matrices and, on the fifteen columns, with them
resampled as well (on the fourteen, GBM-50k − GBM resampled is starred under
the primary seed and one check seed). With every build weighted alike the
standing is unchanged between the matrices; on the nearest pooling all three hold zero on both matrices
and GBM − scorecard changes sign inside the interval. On the cohort
intercept, the second identification, the fifteen columns move the
differences against the scorecard to zero: GBM − scorecard −0.000224
[−0.000284, −0.000143], starred under all three seeds, → −0.000023
[−0.000084, +0.000062], holding zero under all three fixed and resampled;
GBM-50k − scorecard −0.000162 [−0.000280, −0.000045], starred under all
three seeds fixed and resampled and on every draw, → +0.000102 [−0.000016,
+0.000262], the sign reversed and holding zero under all three seeds fixed
and resampled; on the draws it is starred above zero on one and holds zero on two. And
GBM-50k − GBM gains a star: +0.000062 [−0.000050, +0.000153] → +0.000125
[+0.000003, +0.000278] under all three seeds with the cohorts fixed, holding
zero with them resampled, the run marking its draws as disagreeing
(+0.000065 holding zero, +0.000221 and +0.000088 starred). GBM-50k's own
cohort-intercept slope holds zero on the fifteen columns (−0.000295
[−0.000431, −0.000168] → −0.000117 [−0.000257, +0.000053]). At the cohort
scopes the same reversal appears with a star on one side: on the 2022 cells
GBM − scorecard −0.000220 [−0.000298, −0.000112] → +0.000027 [−0.000059,
+0.000138] and GBM-50k − scorecard −0.000137 [−0.000302, +0.000047] →
+0.000158 [+0.000046, +0.000307]; on the flagged cohorts GBM-50k −
scorecard −0.000191 [−0.000296, −0.000075] → +0.000084 [−0.000033,
+0.000225]. On the build intercept no scope reverses a starred sign; on the
2022 cells the two differences against the scorecard lose their star.

*H2 on the expanding arm.* GBM − scorecard +0.0147 [+0.0029, +0.0259],
starred under the primary seed and one check seed, → +0.0092 [−0.0033,
+0.0174], holding zero under all three fixed and resampled; with every
build weighted alike +0.0235 [+0.0104, +0.0356] under all three → +0.0150
[−0.0004, +0.0240], holding zero under the primary seed and starred under
both check seeds ([+0.0010, +0.0243], [+0.0003, +0.0247]); on the 2022
cells +0.0498 [+0.0194, +0.0638] → +0.0162 [−0.0067, +0.0325]. GBM-50k −
GBM +0.0054 [−0.0012, +0.0166] → +0.0105 [−0.0011, +0.0310], holding zero
on both; with every build weighted alike +0.0167 [−0.0103, +0.0401] →
+0.0205 [+0.0122, +0.0392] under all three seeds, and on the nearest
pooling +0.0246 [−0.0116, +0.0908] → +0.0250 [+0.0029, +0.0601], starred
under the primary seed alone. GBM-50k − scorecard at the arm pooling
(+0.0201 → +0.0197, above) is starred on each of the three draws on the
fourteen columns and on two of three on the fifteen (+0.0114 [−0.0015,
+0.0286] on 20260911); with every build weighted alike it is +0.0402
[+0.0041, +0.0667] → +0.0354 [+0.0209, +0.0531], starred under all three
on both.

*H3 on the expanding arm.* GBM-50k − GBM against the model's own training
reference reverses its sign with a star on the fifteen columns: −0.0010
[−0.0094, +0.0058], holding zero under every seed fixed and resampled with
its three draws disagreeing in sign (−0.0089 starred below, +0.0054 and
+0.0005 starred above), → +0.0078 [+0.0038, +0.0144], above zero under all
three seeds fixed and resampled ([+0.0018, +0.0174]) and on each of the
three draws held fixed, +0.0051 [+0.0047, +0.0056], +0.0140 [+0.0135,
+0.0144] and +0.0042 [+0.0038, +0.0047], intervals that do not overlap
(in the order 20260911, 20260912 and 20260913, the second clear of both, the first one's lower bound +0.004685 above the
third one's upper bound +0.004684), so the run carries its draws-disagree
mark on the pair. Among the statistics H1 to H3 read it carries the mark on
PSI GBM-50k − scorecard, on both GBM-50k pairs against the first scored
cohort and on the cohort-intercept GBM-50k − GBM as well; the
fourteen-column run carries it on the two PSI pairs and the two first-cohort
pairs. With every build weighted alike it is
−0.0027 [−0.0113, +0.0036] → +0.0052 [+0.0010, +0.0116] under all three;
on the nearest pooling it holds zero on both. The same reversal is starred
on the fifteen columns on the pre-flag cohorts (−0.0016 → +0.0049
[+0.0010, +0.0093]), the flagged cohorts (−0.0002 → +0.0091 [+0.0045,
+0.0153]), the crisis cells (−0.0008 → +0.0066 [+0.0029, +0.0100]) and the
flagged cohorts with every build weighted alike (−0.0012 → +0.0074
[+0.0031, +0.0128]). Two more PSI differences reverse a starred sign: on
the flagged cohorts GBM-50k − scorecard −0.0063 [−0.0143, +0.0019] →
+0.0078 [+0.0029, +0.0141], and with every build weighted alike there
−0.0103 [−0.0182, −0.0028] → +0.0029 [−0.0016, +0.0085]; and on the
nearest pooling of the crisis cells with every build weighted alike GBM −
scorecard +0.0182 [+0.0160, +0.0205] → −0.0015 [−0.0037, +0.0010]. Against
the first scored cohort the arm pooling does not move: GBM − scorecard
−0.0112 [−0.0120, −0.0106] → −0.0115 [−0.0122, −0.0109] under all three
seeds fixed and resampled; GBM-50k −
scorecard −0.0090 [−0.0136, −0.0008] → −0.0104 [−0.0237, −0.0008] under all
three fixed, holding zero resampled on both ([−0.0195, +0.0022] →
[−0.0302, +0.0027]); GBM-50k − GBM +0.0022 → +0.0011, holding zero on both with its three draws
disagreeing in sign on both (on 20260911 −0.0015 → +0.0048, starred on
both sides); on the nearest pooling GBM-50k − GBM
−0.001535 [−0.002599, −0.000449] under all three → −0.002766 [−0.005037,
−0.000024], starred under the primary seed and one check seed. On the
nearest pooling of the pre-flag cohorts GBM − scorecard reverses with a star
on both sides against that reference, −0.0020 [−0.0030, −0.0012] → +0.0033
[+0.0026, +0.0041], and GBM-50k − scorecard −0.0029 [−0.0041, −0.0017] →
+0.0016 [−0.0043, +0.0052]; on the nearest pooling of the crisis cells GBM −
scorecard −0.0008 [−0.0024, +0.0004] → +0.0052 [+0.0038, +0.0063].

*Per build, on the expanding arm.* The starred sign reversals are on
2002H2-E, where GBM-50k − GBM on H2 is −0.0333 [−0.0541, −0.0069] →
+0.0463 [−0.0280, +0.1153] with the cohorts fixed and −0.0989 [−0.1505,
−0.0149] → +0.0519 [−0.0894, +0.1421] on the nearest pooling, the star on
the fourteen-column side, and on PSI −0.0032 [−0.0130, +0.0037] → +0.0161
[+0.0046, +0.0239]; on 2006H2-E, where PSI GBM-50k − GBM is −0.0066
[−0.0123, +0.0018] → +0.0105 [+0.0024, +0.0236] and GBM − scorecard on the
2022 ratio of observed over expected, H2's third scoped reading, +0.0419
[+0.0228, +0.0605] → −0.0425 [−0.0589, −0.0234], starred on both sides; and on the nearest pooling
of 2012H2-E, where PSI GBM − scorecard is +0.0026 [+0.0006, +0.0046] →
−0.0016 [−0.0043, +0.0007]. No build reverses a starred sign on the build
intercept.

*The rolling arm.* At the arm pooling the fifteen columns add stars below
zero. On the build intercept the three differences keep sign and star (GBM
− scorecard −0.000101 → −0.000181, GBM-50k − scorecard −0.000107 →
−0.000226, both under all three seeds; GBM-50k − GBM −0.000006 → −0.000046
holding zero), and with the cohorts resampled the two against the scorecard
become starred ([−0.000243, +0.000055] → [−0.000316, −0.000036];
[−0.000269, +0.000059] → [−0.000386, −0.000057]). On H2 GBM-50k − GBM
−0.0038 [−0.0359, +0.0218] → −0.0143 [−0.0289, −0.0034] under all three
seeds fixed and resampled, and GBM-50k − scorecard −0.0404 [−0.0727,
−0.0050] → −0.0520 [−0.0669, −0.0331], starred resampled on the fifteen
columns where it holds zero on the fourteen. On H3 GBM-50k − GBM −0.0060
[−0.0139, +0.0063] → −0.0102 [−0.0166, −0.0027] and GBM-50k − scorecard
−0.0103 [−0.0184, +0.0022] → −0.0127 [−0.0194, −0.0049], each under all
three seeds with the cohorts fixed; with them resampled GBM-50k − scorecard
holds zero, and GBM-50k − GBM holds zero at the margin, [−0.0178, +0.0002]
under the primary seed and 20260906 and starred under 20260907; against the
first scored cohort GBM-50k − GBM −0.0002 [−0.0094, +0.0100] → −0.0048
[−0.0108, −0.0015] fixed. Two stars are removed: on the cohort intercept
GBM-50k − scorecard −0.000326 [−0.000521, −0.000063] → −0.000068 [−0.000330,
+0.000246], where GBM-50k − GBM changes sign inside the interval (−0.000044
→ +0.000131); and against the first scored cohort on the nearest pooling
GBM-50k − scorecard −0.0035 [−0.0066, −0.0005] → +0.0021 [−0.0005, +0.0065],
where GBM − scorecard reverses with a star on both sides, −0.0039 [−0.0045,
−0.0033] → +0.0033 [+0.0026, +0.0040], both the same with every build
weighted alike. At the pooled scopes the starred
reversals are these. On H1's build intercept: on the pre-flag cohorts GBM −
scorecard −0.000589 [−0.001002, −0.000217] → +0.000435 [+0.000017,
+0.000850] and GBM-50k − scorecard −0.000840 [−0.001464, −0.000240] →
+0.000820 [+0.000214, +0.001411], starred under all three seeds on both
sides; on the crisis cells GBM-50k − scorecard −0.001227 [−0.002554,
−0.000026] → +0.000329 [−0.000941, +0.001461], the star under the primary
seed alone. On H2 with every build weighted alike on the pre-flag cohorts:
GBM-50k − GBM +0.0084 [−0.0402, +0.0443] → −0.0171 [−0.0295, −0.0068] with
the cohorts fixed and +0.0072 [−0.0388, +0.0435] → −0.0168 [−0.0434,
−0.0020] on the nearest pooling, the latter starred under the primary seed
alone. Against the first scored cohort: GBM-50k − GBM +0.0008 [−0.0077,
+0.0100] → −0.0037 [−0.0092, −0.0006] with every build weighted alike; and
GBM − scorecard on the nearest pooling, starred on both sides, −0.0052 →
+0.0024 on the pre-flag cohorts, −0.0041 → +0.0026 on the flagged, and
with every build weighted alike −0.0066 → +0.0021 on the crisis cells and
−0.0056 → +0.0039 on the flagged, with GBM-50k − scorecard beside it losing its
star on the flagged cohorts (−0.0041 → +0.0018), on the crisis cells with
every build weighted alike (−0.0064 → +0.0009) and on the flagged with
every build weighted alike (−0.0056 → +0.0023). On single context draws
starred signs reverse on both sides: on 20260911 PSI GBM-50k − GBM +0.0060
→ −0.0029 and GBM-50k − scorecard +0.0017 → −0.0054, the first-cohort
GBM-50k − GBM +0.0097 → −0.0023 and the cohort-intercept GBM-50k −
scorecard −0.000148 → +0.000168; H2 GBM-50k − GBM on 20260912 and
20260913, +0.0178 → −0.0094 and +0.0065 → −0.0077; the cohort-intercept
GBM-50k − GBM on 20260913, −0.000110 → +0.000068. No draw reverses a
starred sign on the build intercept. Per build: on 2008H2-R the
build-intercept GBM-50k − GBM −0.000198 [−0.000346, −0.000076] → +0.000004
[−0.000168, +0.000190]; on 2012H2-R, PSI GBM − scorecard −0.0462 → +0.0021,
starred on both sides (−0.0049 → +0.0211 on the nearest pooling, the same),
PSI GBM-50k − GBM +0.0001 → −0.0211 (+0.0027 → −0.0192 nearest),
first-cohort GBM-50k − GBM +0.0020 → −0.0072, and on the nearest pooling
against the first scored cohort GBM − scorecard −0.0145 → +0.0057, starred
on both sides, and GBM-50k − scorecard −0.0157 → +0.0005; on 2016H2-R, PSI
GBM − scorecard +0.0090 → −0.0049, starred on both sides (+0.0066 →
−0.0010 nearest, the star on the fourteen-column side), PSI GBM-50k −
scorecard +0.0137 → −0.0190 (+0.0086 → −0.0077 nearest), the star on the
fourteen-column side, and first-cohort GBM-50k − scorecard +0.0026 → −0.0029,
starred on both sides; on 2018H2-R, first-cohort GBM − scorecard −0.0025 →
+0.0021 and −0.0069 → +0.0027 on the nearest pooling, starred on both
sides. On the 2022 ratio of observed over expected: 2012H2-R GBM-50k − GBM
−0.0371 → +0.0726, starred on both sides; 2016H2-R GBM-50k − scorecard
−0.0670 → +0.1078, the star on the fifteen-column side; 2018H2-R GBM −
scorecard +0.0878 → −0.0076, the star on the fourteen-column side.

*The reading.* The classical readings the criterion rows quote keep their
sign and star: on the criterion identification of H1, on H2's classical
comparison and on the PSI levels nothing changes standing on the expanding
arm. Other classical comparisons move: GBM-50k against the full-pool GBM on
PSI and on H2, GBM − scorecard on H2, and the three cohort-intercept
comparisons. The signed Cox slope and |log O/E|, reported beside H2 and not
tested, carry starred reversals of their own that this entry does not list;
at the arm pooling |log O/E| GBM − scorecard goes from +0.0307 [+0.0212,
+0.0378] to −0.0025 [−0.0119, +0.0075]. The rolling arm does not
carry that over to every scope: there the build intercept's pre-flag
differences against the scorecard reverse with a star on both sides.

What is not here. No foundation model on the fifteen columns: the trigger,
read on 2026-09-14 on the rows the note of that day fixed, did not fire,
and neither TabPFN nor TabICL is scored on that
matrix beyond the falsifying build, so no criterion verdict is read from
these runs — the criteria of H1 and H3 read the foundation models against
GBM-50k and H2's against the scorecard, and this ablation touches only the
classical side. No refit control on the fifteen columns. No comparison with
the nominal matrix. The ledger row is C-033, beside C-025 to C-027 and
superseding none of them.

## Cold audit

The audit of `fm-reduce3` and `fm-vintage-structure3` re-derived the layout,
the axis, the reduction and the label from the zips and found no mismatch
on the loans it rebuilt and no difference on any cohort count; what it
found in the design — the label's definition changing at January 2014, the
seasoned acquisitions, the columns that date a loan, and the partly matured
cohorts at the cutoff — is fixed above in the paragraphs on the label's
definition along the axis, on seasoned acquisitions, on features and on
maturity at the cutoff. The audits of the build run, the feature run, the
falsifying run and the grid follow in that order, each independent of the
work it checks.

The audit of the falsifying reading
(`experiments/2026-09-14-fm-2004h2e-{intervals,intervals-dti-kept,intervals-upb-nominal,ablation-dti-kept,ablation-upb-nominal,in-sample}`),
given the code, the data, the manifests and this file through
"Multiplicity", re-derived every table from the rows with its own code:
AUC, Brier, Cox slope and PSI to a difference of 0, observed over expected
to 2 × 10⁻¹⁶, the Cox intercept to 3 × 10⁻¹⁴, every Cox fit converged.
Its verdict is that the reading supports a weaker claim: at 0.9 both
foundation models under-predict at age zero by 20 to 25% more than the
classical models while ranking as well as the scorecard, and the
`upb_nominal` trigger fires as the rule is written but on a Brier change
under one percent, carried by the level, and conditional on one draw of
the control — draw 20260911 is GBM-50k's worst on AUC, and the Brier
difference stays positive against each of its three draws. The reading
over three draws above answers the draw. The audit found no leakage: the
pool's rows end before the first scored row, every context is a subset of
the pool, one checkpoint, repeats at 0.0. It notes that H2's clause for
settling the question without the grid is not met, every foundation-model
Cox slope lying inside the scorecard's per-cohort Wald interval; that
2006H1's rate had already moved and dominates the pooled |log O/E|, the
level effect holding on each cohort alone; that the percentile interval of
an absolute statistic near zero is biased, conservatively for the claim
that a foundation model is worse; and that the classical score runs'
manifests hash no outputs. It found the two statements corrected above and
two figure defects, the level-prevalence ticks and the ablation title,
which are not yet redrawn.

- **2026-09-24 — the horizon check, fixed before its number.** The Setting
  registers the horizon check as a reading of every run: the twelve-month
  label on annual cohorts, read on the scores the primary label's builds
  produce, discrimination only, on the criterion cells of the primary label
  whatever their own counts, with the annual cohorts under the floor as its
  hole. The score runs write the label as `outcome_horizon`. No pooling has
  read it, as the note of 2026-09-17 says. The existing pooling reads
  half-year cohorts and refuses a cell under the floor, so the check cannot
  be read without code the registration does not describe in full. This
  entry fixes what the code does, before any number of the check exists and
  after every criterion row of this book was recorded.

  *The cells.* An annual cell is one build's scored rows of the two
  half-years of one calendar year, taken together: one AUC on their union,
  the bootstrap resampling inside it. Nothing is refitted. Every build is dated at a year's end,
  so its scored cohorts come in whole years; a year a build does not score
  in both halves does not enter. The cell's age is the mean of its two
  halves' ages in quarters, which shifts every cell of a build alike and so
  leaves the within-build slope as it is.

  *The floor.* A year enters when its annual cohort holds at least 100
  defaults under the twelve-month label on the book, the floor of EXP-003
  read on the check's own label. That is the only reading under which the
  hole the Setting lists is the check's hole, and it agrees with "whatever
  their own counts" on the cells it keeps, since every half-year under the
  primary floor lies in a year this floor removes. The rule also removes
  2018, which the Setting's list omits. The counts are printed beside the
  rows, and a year near the floor is not read with a second one.

  *What is read.* H1 only, the slope of AUC on age under both
  identifications, at the criterion's poolings and check seeds, on both
  arms. Most of the hole sits at the end of the axis, so the slope reads
  mostly the years before 2013 and a few later ones, and that is said
  beside the rows. The Cox slope and the level are not read: a
  twenty-four-month probability ranks twelve-month outcomes and does not price them. The
  stability index does not read the label. The ratio matrix only: the
  trigger of 2026-09-14 asks for the nominal matrix beside every verdict,
  and this check is none. A build left with fewer than two annual cells has
  no slope of its own and is reported as unreadable. No build is dropped.

  *Standing.* Reported beside H1, entering no criterion.

- **2026-09-25 — the horizon check, three points of the entry above made
  exact, still before any number of it.** First, the entry says the rule
  removes 2018, "which the Setting's list omits". The Setting's correction
  of the two counts already puts 2018 in the hole, at 98 defaults, so the
  rule and the Setting's list agree and nothing is omitted. Second, the
  floor of EXP-003 is two counts, 5,000 labelled loans and 100 defaults;
  the check applies both to the annual cohort under its own label, and a
  year whose scored rows fall under either count on any build stops the
  run rather than entering. Third, "the criterion's poolings" includes the
  pooling of the nearest cohorts, which takes each build's three youngest
  cohorts and then applies the floors. The check reads it in its own unit:
  each build's three youngest annual cohorts, then the floor. Where the
  hole leaves a build fewer than two annual cells in that pooling, the build
  is reported as unreadable there, as the entry above says, and a mean that
  weights every build alike is reported as unreadable with it rather than
  taken over the builds that remain.

- **2026-09-25 — the registered plots not yet drawn, and the figure
  defects, fixed before any is drawn.** The Plot section registers six
  figures. Three are drawn in no recorded run: the ridge, the reliability
  curves at four named cohorts with 2019H1 under both label readings, and
  the relief share redrawn. Two recorded figures fall short of their
  bullets: the build grid and metric against age. The audit of the
  falsifying reading found two defects, the level figure's ticks and axes
  and the ablation title. A third is added here: the arm pooling's figure
  of AUC against age draws the cells under the floors like every other
  cell, where the Floors paragraph has them "reported on every figure with
  their interval". This entry fixes every open detail. It is written after
  every criterion row of this book was recorded and before any of these
  figures exists.

  *What every figure below shares.* Each is drawn by
  `scripts/registered_figures.py` in a recording of its own under
  `record_run.py`, from a clean tree, with the script final before the
  first recording starts, and the hash of every input is written beside the
  figure. The recorded figures stay in their run directories. Nothing is
  refitted and nothing is pooled. No figure enters a criterion and no
  number governs one. A figure reads score directories and records made
  with no model in them, and prints no statistic of a recording the claim
  gate refuses at HEAD. The gate refuses the seventeen per-build grid
  recordings of this book, which pin a version of `build_intervals.py` that
  has changed since, the three ablation recordings of 2026-09-14, and the
  build run
  [`2026-09-13-fm-vintage-builds2`](../../experiments/2026-09-13-fm-vintage-builds2),
  which runs scripts its manifest does not pin and pins a version of
  `metrics.py` that has changed since. The build run's `builds.json` and
  `cells.csv` are read as the criterion's recordings read them:
  [`2026-09-22-fm-grid-in-sample`](../../experiments/2026-09-22-fm-grid-in-sample)
  pins the first and
  [`2026-09-21-fm-arm-e-intervals`](../../experiments/2026-09-21-fm-arm-e-intervals)
  the second, and the script stops unless each file hashes to that pin once
  line endings are normalised, as the repository stores it. The control is
  the recorded GBM-50k, the criterion's, and not the control refitted on
  2026-09-17, except where a recorded figure that carries both is redrawn.
  The matrix is the fourteen-column ratio matrix. A seeded model is drawn
  on its first context draw, 20260911, unless a paragraph below says
  otherwise. The six half-years under the floors, 2003H1, 2013H1, 2014H2,
  2015H1, 2020H2 and 2021H1, are drawn on every figure that carries them
  and marked there as under the floors.

  *The ridge.* The bullet: "the score distribution of one model at every
  cohort of one build, as a ridge, against the training reference the PSI
  bins were fixed on, and the same ridge against the first scored cohort."
  The build is 2002H2-E. It scores 42 half-year cohorts, 2003H1 to 2023H2,
  at ages 1 to 83 quarters, the width the bullet on metric against age
  names, and it is the build of the reliability figure below, so the two
  distribution figures read one build. The design is the Lending Club
  ridge's, fixed in the EXP-002 log on this date: the five models in
  columns, TabPFN and TabICL again at 1.0, seven columns; the first draw; a
  histogram density of log10 of the probability, in bins 0.05 wide with
  edges at multiples of 0.05; one x range from the 0.1st to the 99.9th
  percentile of every row drawn, widened to the nearest edge, a probability
  beyond it counted in the end bin; every row on one vertical scale,
  youngest at the top; the reference as an outline behind every row and its
  nine interior deciles as ticks; no statistic printed. The references are
  the build's 79,511 training rows for the scorecard and the GBM and the
  50,000-row context draw otherwise.

  Two figures, sharing one x range. The first is against the training
  reference, the one H3 reads. The second is against the first scored
  cohort, 2003H1, with the bins at that model's deciles on 2003H1. The note
  of 2026-09-15 keeps the reference on the first scored cohort whatever its
  floor verdict, and 2003H1 is under the floors at 72 defaults. The second
  reading leaves the first cohort's own cells out, so on the second figure
  the 2003H1 row is drawn as the reference outline alone and labelled as
  the reference. Rows under the floors are drawn like the others, in a
  lighter fill with the label marked, and the legend reads "under the
  floors: scored, pooled into nothing". A ridge row is a distribution and
  has no interval, above the floors or under them, and the figure says so
  rather than leaving those rows out. No PSI is printed on either figure:
  this build's per-cell values are held only by its grid recording, which
  the gate refuses. The score directories are the five that recording names
  as its sources:
  [`2026-09-13-fm-2002h2e-scores`](../../experiments/2026-09-13-fm-2002h2e-scores)
  (the scorecard, the GBM and GBM-50k),
  [`2026-09-14-fm-2002h2e-tabicl-rental-4090`](../../experiments/2026-09-14-fm-2002h2e-tabicl-rental-4090),
  [`2026-09-15-fm-2002h2e-tabicl-t1-derived`](../../experiments/2026-09-15-fm-2002h2e-tabicl-t1-derived),
  [`2026-09-14-fm-2002h2e-tabpfn-rental-4090`](../../experiments/2026-09-14-fm-2002h2e-tabpfn-rental-4090)
  and
  [`2026-09-14-fm-2002h2e-tabpfn-t1-rental-4090`](../../experiments/2026-09-14-fm-2002h2e-tabpfn-t1-rental-4090).
  TabPFN at 1.0 is scored and TabICL at 1.0 is derived.

  *The reliability curves.* The bullet: "the reliability curve per model at
  four cohorts of one build — the youngest, 2007H2, 2013H2, 2023H2 — on the
  same axes, so the shape of the miscalibration is visible across a
  twentyfold range of realised rate". The build is 2002H2-E and the
  youngest cohort is its first scored one, 2003H1, at age 1. Of the five
  builds that score 2007H2, it is the one on which the four named cohorts
  span a twentyfold range. At twenty-four months under the primary label
  the build record gives 0.297% on 2003H1 (72 defaults of 24,276), 6.40% on
  2007H2 (1,560 defaults), 0.592% on 2013H2 (142) and 1.46% on 2023H2
  (363), a span of 21.6×. On the 2004H2 and 2006H2 builds of either arm the
  youngest cohort clears the floors and the four span 10.8×.

  A text that shows the figure states the range as drawn: the four cohorts
  span 21.6×, and the low end is 2003H1, under the floors at 72 defaults,
  about seven to a bin, so its curve is read through its intervals. The
  three drawn cohorts above the floors span 10.8×, and the 36 half-years
  above the floors span 14.4×, from 2019H1 to 2007H2. The "twentyfold" of
  the title is the range of the whole book, 22.5× over the 42 half-years of
  the build record, and its low end, 2020H2 at 71 defaults, is under the
  floors as well. 2003H1 is drawn and marked as under the floors, with its
  intervals. 2003H2 is neither put in its place nor drawn beside it.

  Seven panels, the five models at 0.9 and TabPFN and TabICL at 1.0, from
  the five score directories above. In each, ten quantile bins of the
  cohort's scores for that model and draw, as the metric module's
  reliability curve takes them. The first draw carries its 95%
  Clopper–Pearson interval per bin, and draws 20260912 and 20260913 are
  thin lines without markers. "On the same axes" is one square log–log
  range for every panel of this figure and of the 2019H1 figure below, with
  the identity drawn. On a linear axis a cohort at a twentieth of the rate
  sits in the corner, and on a log axis a model with a wider range no
  longer crowds the others, which is why the recorded per-build figure gave
  each model its own linear axis. The range runs from the smallest to the
  largest plotted bin mean, observed rate and positive interval bound,
  divided and multiplied by 1.2. A bin with no default has no place on a
  log axis. It is drawn as an open downward triangle on the lower edge at
  its mean probability, with its upper bound, under a legend entry that
  says so.

  *2019H1 under both readings.* The bullet goes on: "and the same curves on
  2019H1 under both label readings". Same build, same seven panels, same
  axis range, in a second figure of the same recording. Each panel holds
  two curves on the same bins, the primary label solid and the reported
  reading dashed, the first draw with its intervals and the others thin;
  the bins read the score and not the label, so only the observed rate
  moves. On 2002H2-E, 2019H1 is at age 65 quarters, with 24,752 scored
  rows, 110 defaults under the primary label and 1,134 under the reported
  reading. The build record counts 24,753 loans and 1,135 defaults under
  the reported reading: one loan the reported reading labels, as a default,
  and the primary label does not, and no model scored it. The foundation
  models' score files carry the primary label alone, so the reported one is
  joined from the classical score file by cohort and row, and the script
  stops unless every row joins and the primary label agrees on every joined
  row. The Setting carries the hump of the sensitivity reading "in the
  reliability figure below"; 2019H1 is one of its four cohorts, and the
  other three are not added.

  *The relief share.* The bullet: "the relief share by cohort from EXP-003,
  redrawn with the criterion cells of this grid marked and the three
  regimes shaded". The source is EXP-003's structure recording,
  [`2026-09-19-fm-vintage-structure`](../../experiments/2026-09-19-fm-vintage-structure),
  which the gate accepts: `summary.json`, the twenty-four-month window's
  `defaults_under_relief_by_quarter`, drawn per quarter as recorded, with
  no share derived again. Twenty-four months only, the window of the
  primary label and of the sensitivity reading. The span is the grid's,
  2003Q1 to 2023Q4, 84 quarters, each with a recorded value. The quantity
  is what the EXP-003 note of 2026-09-20 says it is, one minus the
  set-aside defaults over the reported defaults, and the axis says that in
  those words. It never uses the name of the recorded field,
  `share_under_relief`, which the note says the value is not. Each
  half-year spans its two quarters. The six half-years under the floors are
  drawn open and labelled. Under the share a strip gives, per half-year,
  the number of criterion cells, stacked by arm, from the build record's
  `cells.csv`: 356 in all, 196 on the expanding arm and 160 on the rolling.
  One build scores each half-year at the start of the axis and all
  seventeen score each one from 2019H1. The regimes are shaded on the
  half-year boundaries the Setting defines, pre-flag through 2011H1,
  straddling from 2011H2 to 2013H2 and flagged from 2014H1, read from the
  build record's `regimes` and checked against that definition. The first
  quarter with a share above zero, 2012Q2, lies inside the straddling
  regime. Nothing of the sensitivity reading's results is drawn; the
  caption points to its recorded pooling,
  [`2026-09-22-fm-between-arm-intervals-outcome-reported`](../../experiments/2026-09-22-fm-between-arm-intervals-outcome-reported).
  The grid's cells also leave out the seasoned acquisitions and the loans
  with a gap in their performance record, which EXP-003's recording keeps.
  Summed to half-years, the two shares differ by at most 0.0017, at 2023H2,
  and the caption says so.

  *The build grid.* The bullet: "the build grid, from `fm-vintage-builds`
  before any model: what each build was allowed to know, the blind rows,
  and the training rate against the rate of every cohort it scores". The
  recorded `build-grid.png` of the build run draws the rates, the pools and
  the regime boundaries. It does not draw what each build was allowed to
  know or the blind rows, and its legend, taken from the 2002H2 panel,
  which has no rolling build, leaves out the rolling pool. That is a
  departure from the bullet and is listed as one. The redraw reads the
  build run's `builds.json` and `cells.csv` and no model output, and it is
  drawn after every model result, which the figure and any text that shows
  it say. The recorded layout is kept: one panel per as-of date, nine, the
  cohort rates on a log axis with the cohorts under the floors open, the
  expanding pool's rate solid and the rolling pool's dashed, the regime
  boundaries dotted. Each panel adds the expanding arm's training quarters
  (`train_quarters`) as a light band from 1999Q1, the rolling arm's eight
  quarters as a darker band inside it, and the blind quarters, after the
  last training quarter up to the as-of date, as a hatched band with
  `blind_rows` written in it: 107,578 to 111,469 rows, the same on both
  arms of a date. The 2002H2 panel says why it has no rolling build, in the
  build record's words. The legend is built from every panel.

  *Metric against age.* The bullet: "metric against age in half-years, one
  line per model, one panel per build, the crisis and the 2022 cohorts
  marked and the floor-failing cells drawn open". The recorded
  `cell-intervals.png` of each grid recording has one figure per build and
  a panel per metric, and the recorded `auc-age.png` of the arm poolings
  has a panel per model and a line per build. Neither marks the crisis or
  the 2022 cohorts, and neither draws the cells under the floors open. That
  is a departure from the bullet and is listed as one. The figure is drawn
  as registered, after every model result, which the figure and any text
  that shows it say:
  - One figure per criterion statistic: the AUC (H1); the Cox slope (H2),
    each foundation model at 0.9 solid and at 1.0 dashed in the same
    colour; and the PSI against the build's own training reference (H3), on
    a log axis. Rank statistics do not see the temperature, and H1 and H3
    are read once.
  - One panel per build, all seventeen of both arms, one line per model,
    the first draw.
  - Age in half-years, the stored quarter age halved and rounded up as the
    note of 2026-09-12 fixes, 1 to 42, and the axis says so.
  - The crisis cohorts are 2007H1 to 2008H2, the Setting's "crisis cohorts
    at 807 to 1,557 defaults", which the build record gives as 808 to
    1,560. The pooling scripts' scope named `crisis cells`, 2007H1 to
    2009H2, is the scope of H2's scoped reading and not this mark. The 2022
    cohorts are 2022H1 to 2023H2, the Setting's "2022–2023 cohorts at 291
    to 381 defaults", the four half-years the build record gives at exactly
    those counts. Each is a shaded band.
  - Every cell carries its interval: DeLong on the AUC and the fit's own
    interval on the Cox slope, as the metric module gives them. The metric
    module gives no interval for a single cell's PSI, so no cell of that
    figure has one, and the figure says so. The cells under the floors are
    drawn open. A cell whose Cox fit does not converge has no point, and
    the figure counts such cells.
  - The seventeen grid recordings hold these values, but the gate refuses
    all of them. Each cell is computed from the score directories those
    recordings name as sources, by the metric module the criterion's
    poolings pin, as a grid recording computes a cell. The values are
    compared with those recordings' `metrics.csv`, and any difference is
    stated in this log beside the figure. No value is drawn from them.

  *AUC against age on the arm pooling.* The `auc-age.png` of
  [`2026-09-21-fm-arm-e-intervals-refit-control`](../../experiments/2026-09-21-fm-arm-e-intervals-refit-control),
  the pooling C-025 and C-026 cite, draws every cell of the expanding arm,
  and the 38 under the floors are drawn like the rest, unmarked, beside a
  slope fitted without them. It is redrawn in a recording of its own with
  the same panels, lines, slope lines and titles. The slopes and their
  intervals are read from that pooling's `paired.csv`, the pooling being
  one the gate accepts, and each cell's AUC is computed from the score
  directories the pooling reads, as its figure computes it. The 38 cells
  are drawn open, under a legend entry that says they are scored and enter
  no slope. The panel of the refitted control stays, since the redraw
  replaces a figure that carries it. The figure carries no per-cell
  interval for any cell; the intervals are on the figure of metric against
  age. A text that carries the recorded figure carries the redraw in its
  place and says that the open cells enter no slope.

  *The level across prevalence.* The bullet: "mean predicted probability
  against realised rate, one marker per cell, one panel per model, both
  axes log, the identity line drawn and the in-sample cells marked". The
  recorded figure takes each panel's limits from that panel's own values
  and labels the minor ticks, so the panels differ in range and the x
  labels overlap. Redrawn: every recording that carries the figure, that a
  ledger row names, and that the gate accepts —
  [`2026-09-22-fm-grid-in-sample`](../../experiments/2026-09-22-fm-grid-in-sample),
  [`2026-09-23-fm-grid-in-sample-upb-nominal`](../../experiments/2026-09-23-fm-grid-in-sample-upb-nominal),
  and the nine
  [`2026-09-23-lc-<build>-in-sample`](../../experiments/2026-09-23-lc-2015h1e-in-sample)
  of the Lending Club book, which C-023 cites. A ledger row also names
  [`2026-09-20-fm-h5-rescaled-control-in-sample`](../../experiments/2026-09-20-fm-h5-rescaled-control-in-sample),
  but it pins a version of `score_context.py` that has changed since, and
  the gate refuses it, so it is not redrawn. It stays as recorded with the
  defect, as do the six recordings no row names:
  `2026-09-14-fm-2004h2e-in-sample`, the recording the audit read,
  `2026-09-16-fm-grid-in-sample`,
  `2026-09-16-fm-grid-in-sample-upb-nominal`,
  `2026-09-17-fm-grid-in-sample`,
  `2026-09-17-fm-h5-rescaled-control-in-sample` and
  `2026-09-19-fm-grid-in-sample`.

  The fix: one square log range for every panel of a figure, from the
  smallest to the largest plotted value divided and multiplied by 1.4, as
  the recorded figure takes each panel's; labelled ticks at 1, 2 and 5 of
  each decade inside the range, in plain decimals; minor ticks unlabelled;
  the grid on the labelled ticks alone. Everything else is drawn as
  recorded. The cohort cells under the floors are marked on this book; on
  Lending Club none is under them, the smallest cohort cell holding 20,000
  rows and 398 defaults. No interval is drawn, since the recordings hold
  none for a cohort cell and none is computed. A cell with no default is
  left off, as the recorded figure leaves it, and the figure gives the
  count. The script reads each recording's `cells.csv` and
  `cohort-cells.csv`, stops unless it places every row of both files or
  counts it as left off, and plots the columns unchanged. A test on a
  synthetic table checks the shared range and the tick rule.

  *The ablation title.* Not redrawn. The three recordings,
  `2026-09-14-fm-2004h2e-ablation-dti-kept`, `-ablation-upb-nominal` and
  `-ablation-upb-nominal-draws`, draw no registered plot. One of them,
  `-dti-kept`, is named by C-033 for its recorded summary and not for its
  figure. The gate refuses all three, since each pins a version of
  `ablation_intervals.py` that has changed since. The truncated title hides
  no value: the panel is whole and `paired.csv` holds every number. They
  stay as recorded, and this is listed as a departure.

  *Standing.* No figure enters a criterion, and no reading changes.

- **2026-09-25, later — the level figures' ticks, fixed before any is
  recorded.** On a range narrower than a decade the rule of labelled ticks
  at 1, 2 and 5 of each decade can leave one labelled tick or none: the
  Lending Club level figures span a factor of four to five. Where fewer
  than three of those ticks fall inside a figure's range, the ticks at
  every integer from 1 to 9 of each decade inside it are labelled instead,
  in plain decimals. The range, the minor ticks and everything else stand
  as the entry above fixes them. The shared axis of the reliability figures
  keeps the rule that entry states, positive Clopper–Pearson lower bounds
  included, although for a bin holding one default those bounds sit near
  one in a hundred thousand.

- **2026-09-25 — the horizon check of H1, on annual cohorts under the twelve-month label.** The Setting registers the horizon check as a reading of every run, and the
  entries of 2026-09-24 and 2026-09-25 above fix how it is read, after every
  criterion row of this book. The recorded runs below are the first of the
  check. The code ran unrecorded before them: on two expanding builds with two
  resamples and on the eight rolling builds with three resamples, both before
  the entry of 2026-09-25, and on the nine expanding builds with three
  resamples before the code was committed; figures of these runs were opened.
  A point estimate does not depend on the number of resamples, so the points
  of both arms existed unrecorded before the recording, the rolling arm's before the entry of 2026-09-25. Every rule the two entries fix
  reads the cells record and the build calendar and no score. The three points
  of the entry of 2026-09-25 were fixed after the first two of these runs, the
  nearest window among them after rows under the three-year window had been
  read, and each reads the cells record alone: the loans floor binds on no
  year, the nearest pooling keeps the criterion's three cohorts in the check's
  unit, and a mean over builds that includes an unreadable build withholds a
  number rather than choosing one. The heading of the entry of 2026-09-25 says its
  three points were made exact "still before any number of it"; that holds of
  recorded numbers only, and this entry corrects it. Two recorded
  poolings compute the check, both by `annual_intervals.py` at `7a85efc` from a clean
  tree on the M4 Pro node:
  [`2026-09-25-fm-arm-e-intervals-horizon`](../../experiments/2026-09-25-fm-arm-e-intervals-horizon)
  over the nine expanding builds and
  [`2026-09-25-fm-arm-r-intervals-horizon`](../../experiments/2026-09-25-fm-arm-r-intervals-horizon)
  over the eight rolling ones, each on the inputs of the criterion's pooling of
  its arm (the per-build grid recordings and the recordings of the control
  refitted on 2026-09-17), with the check seeds 20260906 and 20260907 and the
  cells record of
  [`2026-09-13-fm-vintage-builds2`](../../experiments/2026-09-13-fm-vintage-builds2).
  Nothing is refitted. The half-year readings set beside them are
  [`2026-09-21-fm-arm-e-intervals-refit-control`](../../experiments/2026-09-21-fm-arm-e-intervals-refit-control),
  which C-025 cites, and
  [`2026-09-22-fm-arm-r-intervals-refit-control`](../../experiments/2026-09-22-fm-arm-r-intervals-refit-control),
  which C-018 cites. Every figure is the primary seed's with the cohorts held
  fixed unless it says otherwise, and "starred" means the interval excludes
  zero.

  *The cells.* The years admitted are 2004 to 2012, 2017, 2019, 2022 and 2023.
  The hole is the one the Setting's correction lists, with each year's
  twelve-month defaults on the book: 2003 (82), 2013 (79), 2014 (76), 2015
  (58), 2016 (52), 2018 (98), 2020 (85) and 2021 (71). The admitted years
  nearest the floor are 2019 at 101, 2009 at 102, 2010 at 104 and 2017 at 105;
  the smallest annual cohort holds 47,189 labelled loans, so the defaults floor
  is the one that binds. The Setting's correction gives 2017 at 104 on
  49,229 loans, from the first build record,
  [`2026-09-13-fm-vintage-builds`](../../experiments/2026-09-13-fm-vintage-builds);
  the second record, read by the criterion's poolings as by these runs, holds
  one more loan and one more default. The year enters either way. No admitted
  year's scored rows fell under a floor. The expanding arm holds 64 annual
  cells over 13 cohorts, 13 on 2002H2-E down to 3 on 2018H2-E; the rolling arm
  51 over 12. Every build reads at least two cells, so no build is unreadable
  at the pooling of every cell. On the nearest pooling, each build's three
  youngest annual cohorts and then the floor, 2012H2-E keeps none of its three
  (2013 to 2015), 2014H2-E keeps 2017 alone and 2018H2-E 2019 alone, so those
  three have no slope there, and the mean over builds is reported as
  unreadable; the rolling arm loses 2012H2-R, 2014H2-R and 2018H2-R the same
  way.

  *Where the admitted years sit.* The entry of 2026-09-24 says the slope reads
  mostly the years before 2013. By years that holds and by nothing else:
  nine of thirteen. By cells it does not: every build scores 2019, 2022 and 2023, every build but
  the youngest scores 2017, and only the five builds from 2002H2-E to
  2010H2-E score any year before 2013, so of the 64 cells of the expanding arm
  29 lie in 2004 to 2012 and 35 in the four later years, counted from the
  run's `builds`; on the rolling arm 20 of 51 and 31. The builds from 2012H2
  on read the four later years alone, and the older builds set the years
  before 2013 against the later ones across the hole. The check reads the
  years up to 2012 against four flagged years, with nothing between 2012 and
  2017. The cohort-intercept slope is identified mostly on the four later
  years, the one identification on which both of C-025's stars are lost below.

  *H1 on the expanding arm, the criterion's identification.* On the build
  intercept, TabICL − GBM-50k is +0.000224 [+0.000080, +0.000406], starred
  under all three seeds ([+0.000058, +0.000392] and [+0.000056, +0.000374])
  and on each draw held fixed (+0.000193, +0.000194, +0.000284), as C-025's
  half-year row is (+0.000197 [+0.000112, +0.000275]). TabPFN − GBM-50k is
  +0.000155 [+0.000017, +0.000320], starred under the primary seed and
  20260907 ([+0.000015, +0.000292]) and holding zero under 20260906, whose
  lower bound is −0.0000004, so the run marks the star as changing with the
  seed and the row holds zero at the margin; C-025's is +0.000168 [+0.000091,
  +0.000246] under all three. Held fixed, TabPFN's draws read +0.000149
  (starred), +0.000119 [−0.000003, +0.000265] (holding zero) and +0.000197
  (starred). With the cohorts resampled both hold zero under the primary seed,
  TabPFN [−0.000113, +0.000425] and TabICL [−0.000022, +0.000497]; TabICL's
  interval excludes zero under both check seeds, a star under check seeds
  alone, which the Setting does not read as a star. C-025 has both starred
  resampled under all three. With every build weighted alike TabPFN holds zero
  (+0.000419 [−0.000001, +0.000839]) and TabICL is starred under the primary
  seed alone (+0.000469 [+0.000081, +0.000878]), where C-025 has +0.000210 and
  +0.000242, both starred. On the nearest pooling both hold zero, +0.000526
  [−0.001578, +0.002694] and +0.000600 [−0.001239, +0.002478], the points
  above zero where C-025's are below it (−0.000219 and −0.000371).

  Per build, both rows are starred on 2002H2-E alone, above zero (+0.000287
  [+0.000039, +0.000504] and +0.000380 [+0.000148, +0.000634]). The other
  eight hold zero, the points above zero on every build but 2008H2-E
  (−0.000166 and −0.000133). On the nearest pooling every readable build holds
  zero. No row of either foundation model against GBM-50k is starred below
  zero anywhere in the run: at any pooling, under any seed, on any draw, on
  any build.

  *The second identification.* On the cohort intercept TabPFN − GBM-50k is
  +0.000165 [+0.000011, +0.000345], starred under the primary seed and holding
  zero under both check seeds ([−0.000014, +0.000331] and [−0.000011,
  +0.000316]) and with the cohorts resampled; held fixed, the first two draws
  hold zero and the third is starred. C-025's +0.000322 [+0.000235, +0.000426]
  is starred everywhere. TabICL − GBM-50k is +0.000011 [−0.000176, +0.000239],
  holding zero under every seed with the cohorts fixed or resampled and on
  every draw, the first draw at −0.000069; C-025's +0.000148 [+0.000025, +0.000273] is starred under all
  three with the cohorts fixed. Both stars are lost; neither sign turns at the
  arm pooling.

  *The second control.* Against the control refitted with its early-stopping
  tail uncapped, the build intercept keeps both stars under all three seeds and
  on each draw: TabPFN +0.000158 [+0.000039, +0.000309] and TabICL +0.000227
  [+0.000095, +0.000403]. The cohort intercept loses both, +0.000236
  [−0.000066, +0.000489] and +0.000083 [−0.000113, +0.000293]. The two controls'
  own slopes differ by −0.000003 [−0.000029, +0.000034], holding zero, so
  TabPFN's star at the margin against the recorded control and its star under
  every seed against the refitted one are two readings of nearly the same
  slope.

  *The scorecard and the own slopes.* TabPFN − scorecard on the build
  intercept is −0.000172 [−0.000347, −0.000034], starred under all three
  seeds with the cohorts fixed and holding zero resampled ([−0.000407,
  +0.000152]), as C-025 reads it (−0.000120). TabICL − scorecard holds zero
  (−0.000104 [−0.000253, +0.000034]), as in C-025. On the cohort intercept
  TabPFN − scorecard is +0.000046 [−0.000084, +0.000166], holding zero, where
  C-025 has +0.000161 [+0.000091, +0.000241] starred; the disagreement between
  the identifications C-025 records for TabPFN against the scorecard keeps its
  signs and loses the star on the cohort side. Every own build-intercept slope
  is starred below zero: scorecard −0.000982, full-pool GBM −0.001123,
  GBM-50k −0.001309, TabPFN −0.001154, TabICL −0.001086, the second control
  −0.001312. On the cohort intercept TabICL's own slope is starred below zero
  (−0.000209 [−0.000407, −0.000021]) where C-025's holds zero (−0.000147), and
  the scorecard's holds zero (−0.000101) where C-025's is starred (−0.000134);
  TabPFN's holds zero as well (−0.000055). As in C-025, no own slope is read as
  ageing.

  *The rolling arm.* On the build intercept both rows hold zero under every
  seed with the cohorts fixed or resampled and on every draw, TabPFN − GBM-50k +0.000078 [−0.000061,
  +0.000180] and TabICL − GBM-50k +0.000072 [−0.000068, +0.000181], against
  C-018's −0.000016 and −0.000026, holding zero as well: the sign turns inside
  the interval. On the cohort intercept both are starred under every seed and
  on every draw, +0.000386 [+0.000106, +0.000729] and +0.000475 [+0.000232,
  +0.000730], against +0.000309 and +0.000413. Resampled, TabICL keeps its
  star under all three seeds and TabPFN holds zero under all three
  ([−0.000040, +0.001266] under the primary). The half-year recording has
  TabPFN's resampled row starred under the primary seed ([+0.000006,
  +0.000625]) and 20260907 and holding zero under 20260906 ([−0.000022,
  +0.000595]) (C-018 is corrected by C-037). With every build weighted alike both build-intercept
  rows are starred above zero under all three seeds, +0.000426 [+0.000016,
  +0.000789] and +0.000385 [+0.000068, +0.000722], where the half-year
  recording's +0.000197 and +0.000185 hold zero under 20260906. Per build,
  2016H2-R is the one build with both rows starred, above zero; on the nearest
  pooling TabICL − GBM-50k is starred above zero on 2004H2-R alone (+0.003553
  [+0.001218, +0.007236]). Against the scorecard the two build-intercept stars
  C-018 records below zero are lost (−0.000029 [−0.000202, +0.000116] and
  −0.000035 [−0.000213, +0.000133]); with every build weighted alike the same
  differences are starred above zero, +0.000535 and +0.000495, opposite in sign
  to the arm pooling's, so they are not read as a property of the arm. On this
  arm the second control's rows equal the recorded control's exactly, here as
  in the half-year recording.

  *The seed check.* Of the 168 arm-level differences the check covers on the
  expanding arm, 26 are starred under the primary seed and the run lists 20
  whose star changes with the seed; on the rolling arm 33 and 2. The expanding
  arm's annual stars sit close to zero more often than the rolling arm's. No
  criterion pair is among the rows either run marks as having its draws
  disagree. The rows at 1.0 are not read, as the Setting reads H1 once:
  TabICL's derived rows equal its rows at 0.9 on every finite row, and
  TabPFN's scored rows on the expanding arm differ from its rows at 0.9 by at
  most 0.000006 in point, with the same star under every seed at every pooling
  of its criterion row.

  *The reading.* On annual cohorts under the twelve-month label, neither
  foundation model's slope falls below GBM-50k's beyond the interval at any
  scope on either arm. On the criterion's arm and identification both rows
  keep the sign C-025 records. The check does not carry C-025 at full
  strength: TabICL keeps its star with the cohorts fixed and loses it with them
  resampled, TabPFN keeps it only at the margin, and both cohort-intercept
  stars are lost. Beside H1's verdict this says that the verdict's direction
  survives a change of label and of cohort width on the years the check can
  read, and that its margins shrink there. It says nothing about 2013 to 2016,
  2018, 2020 or 2021, which the check cannot read, and its later years are
  flagged cohorts only. The ledger row is C-036, beside C-025 and C-018 and
  superseding neither.

  What is not here. The Cox slope and the level: a twenty-four-month
  probability ranks twelve-month outcomes and does not price them. The
  stability index, which reads no label. The nominal matrix, owed beside every
  verdict, and the check is none. The pre-flag and flagged scopes are not read: they
  belong to the criteria (kill criterion 4 reads them on a criterion row's
  sign), and the check enters none, the reason the nominal matrix is not read.
  The sensitivity reading has no twelve-month counterpart here:
  `outcome_horizon` is built from the primary reading only. That the scopes are
  left out was fixed in the code and its test at `7a85efc`, before the runs,
  and not in a dated entry. The figures
  `auc-age.png` and `auc-age-cohort.png` of both runs are recorded and not
  read here.

- **2026-09-25 — metric against age, the recomputed cells beside the grid
  recordings.** The entry above fixing the figure says any difference
  between the cells it computes and the seventeen grid recordings'
  `metrics.csv` is stated here.
  [`2026-09-25-fm-metric-age`](../../experiments/2026-09-25-fm-metric-age)
  computes 426 cells over the seventeen builds, 70 of them under the
  floors. Its `summary.json` gives, per build and metric, the largest
  absolute difference from the recording: at most 1.1e-16 on the AUC,
  5.2e-13 on the Cox slope and 9.9e-17 on the PSI. No cell is unmatched,
  none has a value finite on one side only, and no Cox fit fails to
  converge. The figure draws the same values as the recordings, to
  floating-point rounding. No criterion, finding or verdict changes.

- **2026-09-25 — the cold audit of the build run and the feature run,
  written up.** The paragraph under "Cold audit" says the audits of the
  build run, the feature run, the falsifying run and the grid follow in
  that order, and only the falsifying run's did. This entry and the next
  write up the others, and the two after them the two audits of 2026-09-19,
  in the order the audits were made, on 2026-09-25 and from each audit's own
  record, after every criterion row
  of this book was recorded; none of them is an entry made at the time.
  Nothing below is a new measurement. A number is either the auditor's,
  and said to be, or a recorded run's, and the run is named.

  *What it read.* Audited 2026-09-13, before any model was fitted on this
  book, on the three runs of the entry "2026-09-13 — the grid and the
  matrix, before any model", recorded at `d432210`: `fm-vintage-builds`,
  `fm-features` and `fm-features-dti-kept`. The auditor was given the code,
  the three runs, `fm-reduce3`, the pre-registration up to its Log, and
  ADR-0006 and ADR-0007, and was asked, among the rest, whether the
  fourteen kept columns recover a loan's origination half-year, with no
  outcome read. It reports that the subjects of the newest commits, and
  text it had not asked for that states no result, were in its context
  before it began, and that the request named `upb` and `fico` as columns
  to test. The report itself was not kept; a summary made on receiving it
  and the auditor's scripts were, and this entry is written from them.

  *Checked and clean.* The label's clock, recomputed independently on all
  seventeen builds: no training loan's window open at its build date, and
  no scored loan among a build's training loans. The exclusions, the grid,
  the regimes and the matrix reproduced with no mismatch over the 1,355,395
  loans and fourteen columns, and the ablation's matrix is the primary
  one with `dti` added, exactly. Every manifest clean at `d432210`.

  *Findings, and what was done about each.*

  1. The kept columns date a loan. By the auditor's measure a booster
     given the fourteen, held out on the labelled book, recovered the
     origination year at R² 0.418, the rate alone at 0.481 and `upb`
     alone at 0.19, and on 2004H2-E a classifier told the pool from the
     scored rows at AUC 0.818 to 0.973. Acted on before any fit: the
     Setting's note of 2026-09-13, later (`f95fa0e`), puts `upb_to_limit`
     in place of `upb` and makes the nominal amount the second ablation,
     `upb_nominal`; the code is `876b547`, merged at `de586ec`, and the
     runs recorded again there are the entry "2026-09-13, later — the grid
     and the matrix recorded again" (`a02eb6b`).
  2. The record-gap exclusion read a loan's record to the cutoff. Of the
     gapped loans 144 of 194 first miss a month after age 24, and 44 loans
     of 2004H2-E's pool were excluded on an event after the build date.
     Acted on in the same note: a gap counts inside the window only
     (`2bf8c4b`), and the recording at `de586ec` excludes 49 loans on gaps
     where the first excluded 190.
  3. Three statements were stale: the twelve-month hole of the horizon
     check includes 2018, at 98 defaults; the last scored cohort is at age
     83 in quarters, not 43; and ADR-0007's "metropolitan area" bounds a
     column the matrix does not carry. Corrected in the same note and in
     ADR-0007's note of 2026-09-13, both at `f95fa0e`.
  4. Named as able to wait. The build-grid figure's legend and the
     blind-row panel the Plot section promises: drawn as registered in
     [`2026-09-25-fm-build-grid`](../../experiments/2026-09-25-fm-build-grid)
     (`e55fdbf`), under the entry of 2026-09-25 above. The manifest not
     hashing the scripts a script imports: `record_run.py` pins the whole
     local import closure from `d0dc349`, 2026-09-17. The pre-HARP count,
     which bounds borrower overlap from below: it stays the lower bound the
     entry of 2026-09-13 calls it, and nothing bounds the overlap from
     above.

  No cold audit of the recordings at `de586ec` is recorded; their
  differences from the first recording are those the entry of 2026-09-13,
  later, lists.

  *Verdict: supports a weaker claim.* The summary kept records the verdict
  and the findings above, and not the weaker claim in the auditor's words.

- **2026-09-25 — the cold audit of the grid's readings and of H4, written
  up.** Audited 2026-09-17, after the recordings of the entries of
  2026-09-16 and before the Setting's notes of 2026-09-17, which were
  written after it. Written up on 2026-09-25 from the record of its report
  made when it was received.

  *What it read.* The code, the manifests, the recorded tables and the
  row-level score files of the 34 per-build readings on both matrices; the
  four arm poolings
  [`2026-09-16-fm-arm-e-intervals`](../../experiments/2026-09-16-fm-arm-e-intervals),
  `-arm-r-intervals` and their `-upb-nominal` twins; the in-sample readings
  `2026-09-16-fm-grid-in-sample` and `-upb-nominal`; and H4's first
  recording,
  [`2026-09-16-fm-between-arm-intervals`](../../experiments/2026-09-16-fm-between-arm-intervals);
  with the pre-registration and not this log. The auditor reports that the
  subject of the commit recording H4, which words its result, was in its
  environment, and that it re-derived its findings from the code, the
  manifests, the tables and the score files. Its first two findings were
  checked against `build.json` and the pooling script before the notes of
  2026-09-17 were written.

  *Checked and clean.* 41 manifests clean at exit 0, five per-build
  readings at `c599ebb` and 36 at `1c786fe`, with no difference in any
  script or library file between the two commits. Cox deviations
  recomputed from the score rows match H4's `cells.csv` to 8 × 10⁻¹⁴ on
  five builds. The Apple node's repeat of the falsifying reading matches
  the first to 2 × 10⁻¹⁵. H4's pooling does what the note of 2026-09-15
  specifies on the 160 criterion cells, the seeds, the joint draw, the Cox
  pairing and no cell left out, apart from findings 1, 2 and 5 to 7.

  *Findings, the most serious first, and what was done about each.*

  1. The control is unstable across its three draws, and differently on
     the two arms, and that instability sets H4's interval. The rule that
     sizes GBM-50k's early-stopping set caps it at four quarters, written
     for a book whose volume doubles each year; on this book's flat volume
     the set on the expanding arm falls to 2,880 to 2,940 rows at
     2018H2-E, where the rolling arm's holds about 12,700, and the three
     draws there stop at 167, 32 and 144 rounds. The control's own E − R
     per draw has intervals that do not overlap, so the pooled H4 interval
     is mostly the spread between draws. Replacing each of the 48 control
     fits in turn by the mean of its other two draws flips no interval
     verdict, by the auditor's count. Done: the Setting's note of
     2026-09-17 (`05305ee`) names the defect and adds the refit control,
     `gbm-50k@share`, as a named reading (`8816e91`), fitted on every build
     of both books (`1ad2915`) and read in
     [`2026-09-17-fm-between-arm-intervals-refit-control`](../../experiments/2026-09-17-fm-between-arm-intervals-refit-control)
     and
     [`2026-09-17-fm-arm-e-intervals-refit-control`](../../experiments/2026-09-17-fm-arm-e-intervals-refit-control);
     the sensitivity points and each control fit are in
     [`2026-09-17-fm-h4-sensitivity`](../../experiments/2026-09-17-fm-h4-sensitivity).
     The entry "2026-09-19 — H4's draw component" reads the refit's
     per-draw rows as spreading as widely as the recorded control's: the
     draw, not the cap alone, carries the instability. C-020 records H4
     with both controls.
  2. Kill criterion 4 was computed and not applied. The first recording's
     summary read both foundation models as killed inside the interval,
     where the registered verdict is undetermined on the book; the
     sensitivity reading the criterion names had not been run; and the two
     scopes differ in calendar, build mix and age as well as in the
     label's regime. Done: `9f04171` reads criterion 4 into the verdict and
     puts the pre-flag row minus the flagged row beside it;
     [`2026-09-17-fm-between-arm-intervals`](../../experiments/2026-09-17-fm-between-arm-intervals)
     (`357f00c`) supersedes the first recording, every earlier row
     reproduced to the bit, and reads both models undetermined; the
     sensitivity reading,
     [`2026-09-17-fm-between-arm-intervals-outcome-reported`](../../experiments/2026-09-17-fm-between-arm-intervals-outcome-reported)
     (`a97e254`), reproduces the primary reading's pre-flag rows to the
     bit. The Setting's note of 2026-09-17 attributes a scope disagreement
     to "the regime, label or calendar" until the same-cells reading says
     which, and the entry "2026-09-19 — what criterion 4's disagreement is
     carried by" reads it.
  3. H5 at 0.9 cannot separate its two mechanisms: the temperature alone
     makes the ratio depend on prevalence, about p^−0.11. The auditor
     also notes that the derivation of the rows at 1.0 was checked on
     contexts of the expanding arm, 0.96% to 1.76%, while the rolling arm
     spans 0.45% to 4.48%. Done: the Setting's note of 2026-09-17
     withdraws the sentence that read a kill as a prior, and the
     classical models rescaled to 0.9 demonstrate the arithmetic,
     [`2026-09-17-fm-h5-rescaled-control`](../../experiments/2026-09-17-fm-h5-rescaled-control)
     and
     [`-in-sample`](../../experiments/2026-09-17-fm-h5-rescaled-control-in-sample)
     (`8e3a020`, `8f4f58d`), in the entry "2026-09-17 — a
     temperature-scaled control for H5". TabPFN's rows at 1.0 on the
     rolling arm stay derived; C-028 names them as derived and says that
     the contexts their error is measured on span a narrower range of
     rates than the ones it is carried to.
  4. Readings the pre-registration requires were missing: the pre-flag
     and flagged scopes of H1 to H3, the sensitivity label and the horizon
     check on the arm poolings, kill criterion 3, H2's three scoped
     readings, H4 on the nominal matrix, and the arm contrast before H4.
     Done: kill criterion 3,
     [`2026-09-17-fm-kill-criterion-3`](../../experiments/2026-09-17-fm-kill-criterion-3)
     (`c2065f2`), does not fire; the arm contrast,
     [`2026-09-17-fm-arm-contrast`](../../experiments/2026-09-17-fm-arm-contrast)
     (`116b5cb`), and H4 read again with it (`357f00c`); the scopes and
     H2's scoped readings in `arm_intervals.py` (`80afaa8`), recorded in
     [`2026-09-17-fm-arm-e-intervals`](../../experiments/2026-09-17-fm-arm-e-intervals)
     (`735cb9f`) and under the reported label (`c3efdc3`); H4 on the
     nominal matrix,
     [`2026-09-17-fm-between-arm-intervals-upb-nominal`](../../experiments/2026-09-17-fm-between-arm-intervals-upb-nominal)
     (`feaa7c0`); the horizon check, H1 only, in the entry of 2026-09-25
     above and C-036.
  5. A row below zero read as beyond the interval whatever the check seeds
     said; not triggered on this book's criterion rows. Done at `9f04171`:
     a star a check seed loses reads as holding zero at the margin.
  6. The summary wrote booleans as the strings "True" and "False", and
     "False" is true to a reader that tests it. Done at `9f04171`.
  7. The mark that a pair's draws disagree was copied to rows on which no
     per-draw pooling had been run. Done at `9f04171`: every draw is pooled
     at every scope, and the mark is set only where it was measured.
  8. The manifests did not hash the row-level inputs; provenance rested on
     recomputation. Done: the between-arm pooling writes `inputs.json` from
     `9f04171`, the arm pooling and the in-sample reading from `891e78f`,
     and both were recorded again with it at `386c629` (`c522c16`);
     `record_run.py` pins the import closure from `d0dc349`. A score run's
     manifest still hashes no output; the files are pinned by the
     `inputs.json` of the poolings that read them.

  *Not examined.* The split and leakage code, the feature matrix, the
  derivation scripts beyond their recorded error, the stability code line
  by line, the rolling arm's and the nominal matrix's per-build outputs
  cell by cell, the prior art, and the provenance of the rows scored on the
  rented node.

  *Verdict: supports a weaker claim.* At the shipped temperature both
  foundation models rank at least as well as every classical model and
  lose AUC with age no faster than GBM-50k; on the expanding arm their Cox
  slope lies further from one than the scorecard's, and the gap closes at
  1.0; the rolling window leaves every model's slope further from one on
  average. Per hypothesis: H1 is not killed, against a weak and
  draw-unstable control; H2 is killed at 0.9 on the expanding arm and not
  at 1.0; H4 is undetermined under the pre-registration and not resolvable
  with this control; H5's kill at 0.9 does not indicate the mechanism the
  pre-registration attached to it. Not shown: a differential effect of
  context policy on calibration; that the label causes the scopes'
  disagreement; a prevalence prior; any reading of H1 to H3 across label
  regimes, under the sensitivity label or with the age axis resolved; H4
  on the nominal matrix; and that the foundation models decay no faster
  than a well-tuned GBM.

- **2026-09-25 — the end-to-end cold audit of this book, written up.**
  Audited 2026-09-19, after the recordings of 2026-09-18 and before this
  log was split from the pre-registration. Written up on 2026-09-25 from
  the report as received.

  *What it read.* The code, the data, the manifests and the
  pre-registration; not this log and no write-up. The auditor declares two
  contaminations. Text it had not asked for was in its context before it
  began; it states the study's framing and no result. And the
  pre-registration it was told to read then carried dated notes of
  2026-09-17 that quoted H4's arm and scoped rows, the control's per-draw
  E − R and H5's rolling-arm rows, so the audit is not blind on H4 and H5.
  Its account of what the chain shows was written from the artefacts.

  *Checked and clean.* The split runs through `splits.temporal_split` and
  `assert_no_leakage` on each loan's own clock, and `builds.json` of
  `fm-vintage-builds2` records no training window open at any build date;
  the auditor could not construct a leak. The maturity gate and every
  exclusion lean the conservative way. Each of the fourteen features is
  knowable at origination, checked one by one, and every performance
  column is declared after origination and refused. The scorecard is built
  as a risk team builds one, and the GBM's tuning tail is time-ordered.
  Every contender reads identical rows, checked within and across arms.
  The bootstrap keys cohorts by name across builds and draws one context
  per resample for every model. The Cox fit returns no number when it does
  not converge, the stability index is read against its critical value,
  and the scorecard's in-sample Cox slope and intercept read one and zero
  on all 17 pools. Kill criterion 3 is evaluated, and criterion 4 in the
  superseding H4 recording. Three bit-for-bit claims hold as the auditor
  re-derived them: the expanding arm's pooling of 2026-09-18 against
  2026-09-17, 7,728 shared rows equal; of 2026-09-17 against 2026-09-16,
  4,536, and the same for the rolling arm; the between-arm pooling of
  2026-09-17 against 2026-09-16, 432 rows, the verdict string alone
  changed. The accelerator's repeat checks read zero; TabICL's derivation
  is exact to 1.4 × 10⁻⁷ on 121,595 rows. 351 manifests of this book, none
  dirty, and the pooling and scoring code identical at `9f0e110` and at
  the head it read. The three prior-art rows the experiment stands on are
  verified from the full text, and the sweep gate was green.

  *Findings, the most serious first, and what was done about each.*

  1. H4's comparator is too unstable to test H4 as built. The control's
     own E − R changes sign across the three draws with disjoint
     intervals, and the refit control does not remove it: the two
     specifications of the control differ from each other by more than
     either foundation model differs from either. Done: H4 is reported
     undetermined, as criterion 4 reads it, and no run was added for it;
     the entry "2026-09-19 — H4's draw component" (`049c826`) carries the
     per-draw rows and the mechanism, and C-020 records H4 on this book.
  2. H2's kill at 0.9 is the shipped temperature and a data budget. On
     [`2026-09-18-fm-arm-e-intervals`](../../experiments/2026-09-18-fm-arm-e-intervals)
     TabPFN − scorecard is +0.0553 starred at 0.9 and −0.0121 holding zero
     at 1.0, GBM-50k − scorecard +0.0201 starred, and TabPFN's mean signed
     slope at 0.9 is 0.9 times its slope at 1.0 to five figures; the
     scorecard is fitted on the whole pool and the foundation models on
     50,000 rows. Done: C-027 reports the verdict as differing between the
     two settings and measures the row-count asymmetry by the control's
     own row against the scorecard.
  3. The arm poolings average per-build effects that are starred with
     opposite signs: on the stability index TabICL − GBM-50k is starred
     above zero on 2016H2-E, and the pooled value is carried by the oldest
     builds. Done for the stability rows: C-026 states the reversal on
     2016H2-E on both matrices, beside the mean over builds weighted alike.
     For the other rows the audit names, TabICL's Cox slope at 1.0 against
     the scorecard among them, no disposition is recorded.
  4. H1's star lives on the pre-flag and crisis cells of the oldest
     builds: it holds zero on the flagged cells, reverses sign on the
     nearest cohorts, and vanishes for TabICL on the nominal matrix. Done:
     C-025 reports the pre-flag, flagged and nearest readings and the
     nominal matrix beside the criterion's row; the horizon check (C-036)
     reads H1 on annual cohorts.
  5. Verdicts move with the matrix: H3 for TabPFN is killed on the nominal
     matrix, H1's star for TabICL goes, H2 at 1.0 for TabICL is starred, and
     H4's scoped signs agree, so H4 reads killed inside the interval there. The auditor found the ratio matrix fixed before any fit, by
     a diagnostic that reads no outcome. Done: the nominal matrix's
     poolings were recorded again (entry "2026-09-23 — the nominal matrix's
     poolings recorded again at `a36c751`"), and C-025 to C-027 report
     both matrices, the ratio's reading being the criterion's.
  6. Borrower overlap between training and scored rows is bounded below,
     by the pre-HARP count, and not above: no borrower key is supplied to
     the entity check. Left: the data carry no borrower key, and the
     Setting's paragraph on what the split cannot check stands: the pre-HARP
     count is a lower bound, and the exposure applies to every model alike.
     The auditor notes that it bears on levels and not on the paired
     differences the criteria read.
  7. The four-quarter cap also binds on the full-pool GBM, whose point
     every GBM-50k inherits: its tail falls to 5.7% of the pool at
     2018H2-E. Done: stated as a fact about the inherited point in the
     entry "2026-09-19 — H4's draw component"; the full GBM with the cap
     lifted stays a reviewer's run.
  8. Three context draws are a coarse basis for any statistic the draw
     dominates: TabICL's in-sample level on 2002H2-E moves from 1.089 to
     1.460 across them. Done in part: the entry "2026-09-19 — H5's rows
     read per draw" reads the draws beside the interval. No fourth draw is
     recorded.
  9. Smaller. Scoring in chunks of 20,000 splits each cohort, which a
     library fitting anything on the query batch would feel; no recorded
     run checks it. The rented node's hand manifests carry no code or input
     hashes, the library versions and checkpoints being in `node.json`;
     left as written. The ablation summaries of 2026-09-14 count rows at
     1.0 in the trigger that the correction of 2026-09-15 puts outside it,
     and the decisions taken from them match the rule as corrected; the
     three recordings stay as recorded, as the entry of 2026-09-25 above
     says. The reducer takes the termination code and its age by maximum
     independently, which on a loan with two zero-balance rows could mix
     rows; no recorded run checks it. The level figure's overlapping tick
     labels: redrawn at `e55fdbf` under the entries of 2026-09-25 above.

  The contamination was acted on as well: this log was moved out of the
  pre-registration (`0ccfa32`), the Setting's numbers and verdicts were
  carried here (`e2d9591`, `3fa08a5`, `a5a6207`), and an audit of H4 and
  H5 blind to them was ordered, the next entry.

  *Not examined.* The chunking above, the size of the borrower overlap,
  whether a fourth draw moves H4 or H5, the horizon check, the reliability
  and ridge figures, the Lending Club book, and the internals of
  `ablation_intervals.py` beyond its outputs.

  *Verdict: supports a weaker claim.* In the auditor's words: on a
  mortgage book spanning twenty-two-fold prevalence and up to twenty-one
  years of cohorts, two tabular foundation models at their library
  defaults discriminate better than a WOE scorecard and a 50,000-row tuned
  GBM, lose discrimination with model age no faster than that control,
  and destabilise their score distributions no more than it does, pooled
  over the expanding arm, while every model loses calibration in the
  large by a factor of roughly 1.65 and carries a Cox slope below one; the
  shipped temperature of 0.9 moves both foundation models' slope further
  from one than a full-pool scorecard's, and at 1.0 the comparison
  reverses; the heterogeneity across build dates is larger than every
  pooled difference and changes sign. Per hypothesis: H1 and H2 support a
  weaker claim; H3 supports the registered claim at arm scope and not
  across vintages; H4 cannot be told from these runs; H5 supports the
  claim, the kill at 0.9 being the temperature. Kill criteria 1 to 3 are
  correctly evaluated; criterion 4 is, and its disagreement fires for the
  scorecard's scope contrast too, a model with no context, so it is a
  property of the cells and not of a model class.

- **2026-09-25 — the blind cold audit of H4 and H5, written up.** Audited
  2026-09-19 at `049c826`, after this log was split from the
  pre-registration. Written up on 2026-09-25 from the report as received.

  *What it read.* The pre-registration without the end of its Setting,
  which held the dated notes of 2026-09-17 to 2026-09-19; the first 590
  lines of EXP-002's; the run list and the
  code; not the logs, the ledger or the commit messages. No expected
  finding was given. The auditor declares that text it had not asked for,
  stating no H4 or H5 result, was in its context; that a commit subject in
  its environment named H4's draw component, the topic of its finding
  H4-3; that a search of EXP-002 printed lines past 590, among them
  Lending Club's H4 values from the note of 2026-09-17 and the sentence
  that points at the control's tuning; and that the names of later run
  directories were visible, none of which it opened.

  *Checked and clean.* H4's recording clean at `116b5cb`, the arm contrast
  at `45c6f7b`, the in-sample reading at `9f0e110`, every code hash equal
  to the file at its commit. Of the 3,320 files H4's `inputs.json` lists,
  every one of the 3,160 parquet files matches its hash, and the 138 text
  files that differ do so by line endings alone. Every criterion cell
  refitted from the score rows, 160 cells on two arms for eleven model
  draws, matches `cells.csv` to 8 × 10⁻¹³, and every pooled point, scope
  and H5 point reproduces from the recorded cells. 192 shared cells, 32
  under the floors, 160 in the criterion; 28 pre-flag, 115 flagged, 17
  straddling.

  *Findings, and what was done about each.*

  - H5-1. The kill at 0.9 fires under the mechanism the registered reading
    said it rules out. The auditor's simulation of a model calibrated at
    1.0 and scaled to 0.9 gives an H5 difference of −0.33 to −0.42 on the
    rolling arm, against the recorded −0.355 for TabPFN and −0.632 for
    TabICL; at 1.0 TabPFN's row is +0.034 [−0.107, +0.148]. Already acted
    on before the audit: the withdrawal in the Setting's note of 2026-09-17
    and the rescaled control; the audit reaches the same arithmetic blind to
  both, without opening the rescaled control's runs. C-028
    carries it.
  - H4-1. The control's arm contrast includes a change of tuning point and
    a round count re-chosen per draw, where a foundation model changes only
    its context. Already stated in the Setting's note of 2026-09-17 and the
    entry "2026-09-19 — H4's draw component"; H4 stays undetermined.
  - H4-2. The folded statistic hides that the foundation models' slopes lie
    below one on nearly every cell while the control's straddle one, so in
    signed terms the window moves the control several times as far. Done:
    the entry "2026-09-19 — H4's signed reading" (`2ca080c`), its ratio
    corrected to 3.4 to 7.7 in a dated note (`7031b23`). No verdict
    changes.
  - H4-3. The interval is decided by three draws: TabPFN's H4 reads −0.037,
    +0.011 and −0.022 per draw. Carried by the entry "2026-09-19 — H4's
    draw component", made before the audit; C-020 quotes the rows with the
    three-draw caveat.
  - H4-4. Criterion 4's disagreement is the GBMs', not the label's: the
    foundation models' E − R is nearly the same in both scopes, and the
    scope row is starred for TabPFN only at the margin. Done: the entry
    "2026-09-19 — what criterion 4's disagreement is carried by" (`0fdb082`)
    and a dated pointer in the Setting.
  - H5-2. The row bootstrap is not the sampling distribution of an
    in-sample statistic: GBM-50k's in-sample ratio lies between 0.978 and
    0.999 on all 51 draws, against a per-cell interval of [0.837, 1.138]
    on 2018H2-R. The bootstrap is conservative for the kills, which stand,
  and the survivals are uninformative.
    Done: the criterion's interval stays the recorded method, and the
    entry "2026-09-19 — H5's rows read per draw" (`4afe1ff`) reads the
    draws beside it with no interval; C-028 reports both.
  - H5-3. The two contexts H5 compares also differ in era, and TabICL's
    ratio at 1.0 moves by up to 0.2 between draws of one pool. The draw
    spread is read in the same entry. The contexts stay those the note of
    2026-09-14 fixed from the build record.
  - H4-5. The window raises the mean |slope − 1| of every model on this
    book, beyond the interval for all but TabICL and GBM-50k, and H4's statistic is that level over cells of every age, not
    its change with age. Done: stated in the entry "2026-09-19 — the
    interval's other bound" (`b93d152`).
  - Minor. The percentile interval of a folded statistic sits off-centre;
    the same entry reflects the recorded bounds about the point, and no
    star of an H4 or H5 row of this book changes. The in-sample reading
    wrote no `inputs.json`: done at `891e78f` and recorded again at
    `386c629` (`c522c16`).

  The lines of EXP-002 the search printed also carried verdicts, not only
  numbers; both Settings' remaining verdicts were carried to the logs
  (`3fa08a5`, `5dfe450`, `c9066e7`).

  *Not examined.* The nominal-matrix twins; the reported-label,
  sensitivity, refit-control, rescaled-control and kill-criterion-3
  recordings; the GBM and scoring code in depth; the split and leakage
  code; the in-sample Cox slope; the derivation beyond its formula; the
  literature; and the superseded recordings of 2026-09-16 beyond the H5
  table, which is identical to the one of 2026-09-17.

  *Verdict.* H4: killed inside the interval on the arm row at 0.9 under
  all three seeds, TabPFN −0.0162 [−0.0446, +0.0175] and TabICL −0.0031
  [−0.0345, +0.0254], and undetermined on this book under kill criterion
  4, the pre-flag and flagged signs disagreeing; the same at 1.0. The
  strongest sentence it supports: on the 160 shared cells the rolling
  context changed neither foundation model's mean |Cox slope − 1| by an
  amount distinguishable from GBM-50k's change, and the rolling window
  raised the slope error of every model. H5: killed on the rolling arm for
  both foundation models at 0.9 under all three seeds, surviving on the
  expanding arm; the interpretation the pre-registration attached to a
  kill does not follow, and at 1.0 TabPFN's in-sample ratio lies between
  0.97 and 1.01 on every draw from 0.44% to 4.6%, which the temperature
  alone produces.

- **2026-09-26 — the per-build rows and the rows between the arms drawn
  again at the size the paper prints them, fixed before they are drawn.**
  The paper prints two figures of this book that recorded poolings drew far
  wider than its page. The per-build rows of the criterion differences, with
  the difference reported beside H3's, are `build-rows.png` of
  [`2026-09-21-fm-arm-e-intervals-refit-control`](../../experiments/2026-09-21-fm-arm-e-intervals-refit-control),
  17.6 by 12.8 inches, sixteen panels in four lines of four. The rolling
  arm's reduction per build date is `build-rows.png` of
  [`2026-09-22-fm-between-arm-intervals`](../../experiments/2026-09-22-fm-between-arm-intervals),
  25.2 by 3.8 inches, six panels in one row. Printed at the text width of
  the tmlr style, 6.5 inches, their titles come out near three points and
  near two. This entry fixes a redraw of each at print
  size, under this rule: at most 6.5 by 8.5 inches, text of at least 7
  points and tick labels of at least 6.5 at that size, 300 dots per inch,
  and the panels in more lines where one line does not fit.
  The numbers are the constants `PRINT_WIDTH`, `PRINT_HEIGHT`, `TEXT_PT`,
  `TICK_PT` and `DPI` of `scripts/registered_figures.py`, which draws the
  registered figures; the redraw imports them. The size, the type and the arrangement of the
  panels change, and nothing either figure shows. It is written after every
  criterion row of this book was recorded; neither figure enters a
  criterion.

  *The per-build rows.* What stays: sixteen panels, four differences for
  TabICL and TabPFN at 0.9 and at 1.0, in the recorded order. Three are the
  criteria's statistics: the slope of AUC on age against GBM-50k, the
  Cox-slope deviation against the scorecard, and the PSI against GBM-50k
  under the build's own training reference. The fourth is the PSI against
  GBM-50k under the build's first scored cohort, which the Setting reports
  beside H3's statistic and which enters no criterion. In each, the nine
  builds 2002H2-E to 2018H2-E along the axis with each build's
  difference and its interval, the arm's pooled difference as a line and
  its interval as a band, zero dotted, and the panel's own vertical axis:
  144 build rows and 16 arm rows of `paired.csv`, with the cohorts held
  fixed and the draws pooled. The titles, legend entries and figure title
  are the recorded ones word for word. What changes: the four lines of four
  kept, on a page of 6.5 by 8.5 inches; the build names turned vertical
  rather than at 45 degrees, so that at the print size no name runs into the
  next; the titles wrapped to the panel's width; lines and markers thinned.

  *The rows between the arms.* What stays: six panels, one for each model
  other than the control, in the pooling's order: the scorecard, the GBM,
  TabPFN, TabICL, TabICL at 1.0 and TabPFN at 1.0. In each, the eight build
  dates 2004H2 to 2018H2 with each date's h4 row and its interval, the row
  over every shared cell as a line and its interval as a band, zero dotted:
  48 date rows and 6 pooled rows of `paired.csv`, with the cohorts held
  fixed and the draws pooled. The label under a date carries the share of
  the expanding pool the rolling window holds, from the pooling's
  `summary.json`, as recorded. The titles, legend entries and figure title
  are the recorded ones word for word. What changes: two panels to a line,
  in three lines, so that each date's two-line label stands clear of the
  next; the labels turned vertical; the figure title wrapped to two lines;
  lines and markers thinned.

  *What is read.* Each redraw reads its pooling's `paired.csv`, with
  `intervals.json` or `summary.json` for the order of the builds, the models
  and the dates, and nothing else: those files hold every value drawn. It
  stops unless the pooling passes the claim gate at HEAD, unless each panel
  holds one row for every scope it draws, and unless the counts are the
  ones above.

  *How.* `scripts/print_figures.py fm-build-rows` and `fm-between-arm-rows`
  draw them, each in a recording of its own under `record_run.py`, from a
  clean tree, with the script final before the first recording starts.
  `summary.json` gives the counts drawn and `inputs.json` the hash of every
  file read. The recorded figures stay in their run directories; the paper
  takes the redraws in their place.

- **2026-09-26 — kill criterion 3 on the nominal matrix.** Since the
  `upb_nominal` trigger fired, every verdict of this book is reported on
  both matrices, the ratio's reading being the criterion's (the entry of
  2026-09-23 on the nominal matrix's poolings). The reading of kill
  criterion 3 of 2026-09-17,
  [`2026-09-17-fm-kill-criterion-3`](../../experiments/2026-09-17-fm-kill-criterion-3),
  read the nine expanding-arm build directories of the ratio matrix only;
  the nominal matrix's nine,
  `2026-09-16-fm-{2002,2004,…,2018}h2e-intervals-grid-upb-nominal`, were
  not read. They are read with `kill_criterion_3.py` unchanged since
  `774fe4f`, by the same command with those nine directories in place of
  the ratio matrix's and an output directory of its own, in a recording of
  its own from a clean tree. The statistic and both readings of the median
  criterion cell are the ones the script fixed on 2026-09-17; nothing of
  them is chosen here. Every other reading of this book was known when this
  entry was written. The result is reported beside the ratio matrix's,
  which stays the criterion's.
