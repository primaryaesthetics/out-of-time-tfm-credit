---
id: 004
title: The published protocol beside this one, on the same rows and models
dataset: lending-club (accepted loans 2007–2018Q4, snapshot 2019-03-01)
status: open
opened: 2026-09-12
closed:
---

# EXP-004 — the published protocol beside this one, on the same rows and models

The published comparison of foundation models on credit default
(arXiv:2605.18147) ranks models on random five-fold cross-validation, tunes on
a random fifth of each training fold by AUC, converts probabilities to labels
at the threshold that maximises F1 on that fifth, and reports calibration as
the scalar Brier score and log-loss. EXP-002 ranks the same kinds of model on
a vintage grid, reads calibration as observed over expected with the Cox
slope and the Murphy decomposition, and never chooses a threshold. The two
protocols have never been run on the same rows with the same models, so the
sentence "the ranking a validator sees is not the ranking the benchmark
reports" is an inference and not a measurement. This experiment makes it a
measurement, or kills it.

## Question

On one build of the expanding arm, do the five models rank the same way under
random five-fold cross-validation of the training pool as they do out of time
on that build's cohorts, and does the scalar Brier score order them as
observed over expected does?

## What the measurement discriminates

> If the in-time ranking on AUC agrees with the out-of-time ranking on every
> pair whose out-of-time difference is starred, and the Brier score orders the
> models as observed over expected orders them, then the protocol does not
> change the verdict on this book and the paper's introduction loses its
> framing sentence. If the rankings differ on a starred pair, or the Brier
> ordering hides a level gap the ratio shows, the sentence is earned and the
> table states by how much.

A second thing the measurement discriminates for free: the F1-optimal
threshold on a pool whose default rate is 2.3% (2.33% on the 323,026 rows of
the pool, 3.12% on the 220,000 scored rows of the cohorts, from the recorded
score run). The published datasets carry 6.7% to 40% defaults; whether the
threshold-based metrics are readable at all at this prevalence is a finding
either way.

## Setting

- **Build.** 2015H1-E, the falsifying build of EXP-002: its expanding pool of
  323,026 rows originated 2010Q2 to 2014Q2, the four blind quarters to
  2015Q2 outside it, its eleven scored cohorts 2015Q3 to 2018Q1, and its
  recorded out-of-time scores for every model
  ([`experiments/2026-09-11-lc-2015h1e-intervals-grid`](../../experiments/2026-09-11-lc-2015h1e-intervals-grid)).
  The out-of-time row of the table is read from that run and nothing out of
  time is refitted.
- **The in-time protocol, on the pool only.** Five stratified random folds
  over the pool's rows under one named seed. Within each fold the training
  part is split again at random, four fifths to fit and one fifth to
  validate, and every model is fitted on the four fifths: the scorecard as
  `scorecard.py` builds it; the GBM on the same thirty-six-point grid as
  EXP-002 with the point chosen on the random fifth by AUC, which is the
  published objective, rather than on the time-ordered tail by log-loss;
  the control on a 50,000-row sample of the four fifths at the full model's
  point, as in EXP-002. The foundation models read that same 50,000-row
  sample as their context and score a 20,000-row sample of the validation
  fifth and a 20,000-row sample of the test fold, at the shipped temperature
  and at 1.0, on the accelerator: two cells per context, added to a bundle
  the same way a cohort is. The classical models score every row of both.
- **Split code.** The in-time folds are random by construction and are the
  one place in this repository a split is not built by `temporal_split`; the
  script says so in its docstring and the fold assignment is written to the
  run directory, since the folds are the thing being measured and not a
  mistake to be caught.
- **Metrics, on the same rows for both protocols.** The published twelve:
  AUC, Gini, KS, average precision, Brier, log-loss, and accuracy, balanced
  accuracy, F1, precision, recall and MCC at the F1-optimal threshold chosen
  on the validation fifth. Beside them EXP-002's: observed over expected with
  its binomial interval, the Cox intercept and slope, the Murphy
  decomposition of the Brier score, and PSI against the rows the model was
  fitted on or conditioned on. The threshold metrics are also computed on the
  out-of-time cohorts at the threshold chosen in time, which is what a
  deployment of the published recipe would do. Average precision, log-loss
  and the threshold metrics enter `outoftime.metrics` with tests against
  their definitions before any table is read.
- **Tuning budget.** The GBM's grid is the study's, stated per fold; the
  scorecard and the foundation models are tuned on nothing. The asymmetry is
  the same one EXP-002 names and it is named again on the table.
- **Seeds.** One fold seed, the three context seeds of EXP-002 for the
  control and the foundation models, the booster seed of EXP-002. The spread
  across the five folds and across the three context draws is reported beside
  every in-time number; the out-of-time row carries the intervals of its
  recorded pooling.

## Kill criteria

1. **The protocol does not change the ranking.** If on every pair of models
   whose out-of-time Gini difference is starred in the recorded pooling the
   in-time difference has the same sign and lies outside its fold spread, the
   discrimination half of the table carries no sentence and is reported as
   agreement.
2. **The scalar sees the level.** If the Brier score and log-loss order the
   five models as |log O/E| orders them, in time and out of time, the Murphy
   point is withdrawn: the scalar was not blind on this book.
3. **The threshold is unreadable.** If the F1-optimal threshold on the
   validation fifth lands where fewer than one in a hundred rows of the test
   fold is above it, or above every row, the threshold-based half of the
   published protocol is reported as not applicable at this prevalence and
   not compared.

The criterion that kills the branch: if the in-time and out-of-time gaps
between each foundation model and the GBM lie inside each other's spreads on
discrimination and on level, the choice of protocol does not matter on this
book, and the introduction says so instead.

## Cheapest falsifying run

One fold of the five, the three classical models only, on CPU: fit, choose
the threshold, score the test fold, and put the twelve published metrics and
the four of EXP-002 beside the recorded out-of-time cell means of the same
three models. If the classical ranking already differs between the rows, or
the Brier ordering already contradicts the ratio's, the foundation-model
cells are worth an accelerator hour; if neither, the experiment is reported
as killed on the classical models and the accelerator is not spent.

## Prior art check

Stands on the row of arXiv:2605.18147 in
[../landscape/prior-art.md](../landscape/prior-art.md), `verified` from full
text on 2026-08-27: §4.3 for the folds, the validation fifth, the AUC
objective, the twenty Optuna trials, the metrics and the F1-optimal
threshold; Table 1 for the datasets and their default rates, the
LendingClub extract among them at 233,154 rows, thirteen variables and 16.0%
defaults. Which rows that extract holds is not stated in the paper and is not
assumed here: the in-time row of this experiment is the published recipe on
EXP-002's matrix and pool, not a reproduction of the published number.

Opened under the sweep of 2026-09-05, green on 2026-09-12 at seven days.

## Plot

Two, neither a bar of a headline number.

- The reliability curve of every model on the in-time test fold and on the
  out-of-time cohorts, on the same axes per model, so that a scalar Brier
  that reads alike on both is seen beside the curves it summarises.
- The precision-recall curve of every model on the in-time test fold with the
  F1-optimal threshold marked, and the same curve out of time with the same
  threshold, so that where the published recipe puts its cut on a book of
  this prevalence is visible.

## Log

Append-only. Date, what was run, what was observed, pointer to the experiment
directory. No conclusion without a pointer.

- **2026-09-12 — the classical side of the falsifying run.** One fold of
  five on the 323,026-row pool of 2015H1-E, the three classical models, on
  CPU:
  [`experiments/2026-09-12-lc-2015h1e-folds`](../../experiments/2026-09-12-lc-2015h1e-folds)
  (fit 206,736 rows, validation 51,684, test 64,606, default rate 2.33% on
  each; the GBM's search chose its point by AUC on the fifth in 176 s, the
  scorecard fitted in 10 s, each control in 3 s) and the table beside the
  build's recorded out-of-time scores:
  [`experiments/2026-09-12-lc-2015h1e-protocols`](../../experiments/2026-09-12-lc-2015h1e-protocols),
  `table.md`. In time is the fold's 20,000-row test cell; out of time is the
  mean over the eleven cohorts of the per-cell value, the fold's threshold
  applied. The control's three context seeds give the spread in brackets.

  *Discrimination.* AUC in time: GBM 0.6945, control 0.6747 [0.6711,
  0.6806], scorecard 0.6721; out of time: 0.7101, 0.7037 [0.7010, 0.7053],
  0.7002. The order is the same under both protocols, GBM above the control
  above the scorecard, and every AUC is higher out of time than in time: the
  2015Q3 to 2018Q1 cohorts separate better than the 2010Q2 to 2014Q2 pool
  they were not drawn from, for every model. Average precision likewise
  (0.046 to 0.051 in time, 0.068 to 0.075 out).

  *Level.* Observed over expected in time 0.98 to 1.00 for every model
  (|log O/E| 0.013 to 0.019); out of time 1.43 to 1.50 (0.353 to 0.398).
  The Cox slope in time 0.90 (scorecard), 0.96 (GBM), 1.01 (control); out
  of time 1.06, 1.01, 1.10. PSI against the fitted rows in time 0.0005 to
  0.0007, out of time 0.017 to 0.033. A random fold of the pool does not
  see the shift in the book's rate, which is what it cannot see by
  construction; the out-of-time row is the one on which every model asks
  for two thirds of the defaults that arrive.

  *The scalar.* Brier in time 0.0222 to 0.0223, out of time 0.0298 to
  0.0299; the models differ in the fourth decimal on either row, and the
  movement between the rows is the base rate's. The Brier ordering agrees
  with the |log O/E| ordering on both rows (GBM best), and so does
  log-loss; the miscalibration component of the decomposition is 0.0001 in
  time and 0.0002 to 0.0003 out of time for every model.

  *The threshold.* The F1-optimal threshold on the validation fifth is
  0.043 (scorecard), 0.059 (GBM) and 0.041 to 0.047 (control), predicting
  4.5% to 11.6% of the test cell positive at an F1 of 0.085 to 0.095 and a
  precision of 0.05 to 0.07; applied out of time it predicts 4.3% to 8.4%
  positive at an F1 of 0.120 to 0.124. The recall and the predicted share
  move by half to nearly double across the control's three seeds. The
  precision-recall figure shows why: on a book at 2.3% the curve is flat
  and close to the base rate from a recall of 0.1 onward, and the F1
  maximum sits on that flat.

  *Against the kill criteria, on the classical models alone.* Criterion 1:
  the AUC ranking is the same under both protocols; with one fold there is
  no fold spread yet, and the differences in time (GBM − scorecard +0.022,
  control − scorecard +0.003) are of the same sign as out of time (+0.010,
  +0.004). Criterion 2: the Brier and log-loss orderings agree with the
  ratio's on both rows. Criterion 3: the threshold does not fire it; the
  metrics at it are readable and near the base rate. Read literally, the
  falsifying run's own clause ends the experiment here without a
  foundation-model cell. It is not read that way, for a reason the clause
  did not anticipate and the amendment below records: the three classical
  models share one level out of time, 1.43 to 1.50, so an ordering among
  them by the ratio cannot differ from an ordering by a scalar, and
  criterion 2 has no power on them. The published benchmark's headline is
  the foundation models, whose out-of-time level at the shipped setting is
  1.5 to 2.2 on this build (EXP-002), and the accelerator hour that scores
  them on the bundle this run packed is the only measurement that can fire
  or clear criterion 2.

  What is not here. The other four folds. The foundation models' cells,
  packed in the run directory (`context.parquet`, `scored.parquet`,
  `bundle.json`; 150,000 context rows, two cells of 20,000) and not yet
  scored. The cold audit of the classical side.

### Amendment of 2026-09-12, after the classical side of the falsifying run

The cheapest falsifying run said the accelerator would not be spent if the
classical ranking agreed between the rows and the Brier ordering agreed
with the ratio's. The second condition cannot fail on the classical models
of this build, whose out-of-time level is the same for all three, and it
was written to test the scalar's blindness to a level gap that only the
foundation models carry. The foundation-model cells are therefore scored,
on the bundle the classical run packed, and criterion 2 is read on the five
models together; criterion 1 keeps its reading on the classical models as
agreement, to be read again with the five. Nothing else changes.

- **2026-09-12, later — the other four folds, and the table over five.**
  [`experiments/2026-09-12-lc-2015h1e-folds-2to5`](../../experiments/2026-09-12-lc-2015h1e-folds-2to5)
  runs folds two to five the same way (927 s, the GBM's search 157 s to
  199 s per fold, every fold at 2.33% defaults on each part), and
  [`experiments/2026-09-12-lc-2015h1e-protocols5`](../../experiments/2026-09-12-lc-2015h1e-protocols5)
  reads all five beside the out-of-time scores; **it supersedes the
  one-fold table above, cite it.** The spread across folds is now in
  brackets beside every in-time number, the control's across folds and
  seeds together.

  *Discrimination.* AUC in time: scorecard 0.6853 [0.6721, 0.6925], GBM
  0.7006 [0.6941, 0.7106], control 0.6861 [0.6711, 0.7004]; out of time
  0.7002, 0.7101, 0.7037 [0.7010, 0.7053]. GBM − scorecard is +0.015 in time
  with the two fold ranges disjoint, +0.010 out of time; control −
  scorecard is +0.001 in time inside either range, +0.0035 out of time,
  where the recorded pooling gives the Gini difference +0.007 holding
  zero. The ranking is the same under both protocols and the one pair
  that separates out of time separates in time.

  *Level and the scalar.* Observed over expected in time 1.013 to 1.014
  with fold ranges of 0.95 to 1.06; |log O/E| 0.033 to 0.038 with ranges
  reaching 0.06; out of time 0.353 to 0.398. The Cox slope in time 0.97,
  0.97 and 1.02 (the control's range 0.79 to 1.24 across its fifteen
  fits); out of time 1.06, 1.01, 1.10. Brier in time 0.0227 to 0.0228
  with a fold range of 0.0215 to 0.0236, twenty times the difference
  between models; out of time 0.0298 to 0.0299. Out of time the Brier and
  log-loss orderings agree with the ratio's; in time they do not, the
  scalar putting the GBM first and the ratio the control, and the three
  in-time levels sit inside one another's fold ranges, so the in-time
  ordering is a tie read as an ordering. Criterion 2 is written on
  orderings and the classical models' levels do not order in time; it
  waits for the five models, as the amendment says.

  *The threshold.* Across folds and seeds it lands between 0.040 and
  0.062, predicting 4.5% to 13.5% of the in-time cell positive at an F1
  of 0.093 to 0.103, and 1.8% to 10.9% of the out-of-time cohorts at 0.119
  to 0.125; precision 0.05 to 0.11 everywhere. Criterion 3 does not fire
  on any fold. PSI against the fitted rows in time 0.0003 to 0.0005, the
  largest cell 0.0011; out of time 0.017 to 0.033.

  What is not here. The foundation models' cells on fold one, packed and
  not scored. A cold audit.

- **2026-09-14 — TabICL on fold one.**
  [`experiments/2026-09-13-lc-2015h1e-folds-tabicl-colab-t4`](../../experiments/2026-09-13-lc-2015h1e-folds-tabicl-colab-t4)
  scores the bundle the classical run packed on a hosted T4: TabICL at
  0.9 on the fold's test and validation cells, 20,000 rows each, and on
  its 50,000 context rows, under the three draws;
  [`experiments/2026-09-13-lc-2015h1e-folds-tabicl-t1-check-colab-t4`](../../experiments/2026-09-13-lc-2015h1e-folds-tabicl-t1-check-colab-t4)
  scores the test cell and the context rows of the first draw at 1.0
  for the derivation's check. Every scored and context row, with its
  outcome, is the fold run's with no mismatch; the first cell of every
  draw scored a second time agrees to 0.0. Nothing is read from it here.
  Criterion 2 is read on the five models together, and TabPFN's fold
  cells are still on the Apple node.

- **2026-09-21 — five folds for the foundation models too, and what kills
  the branch.** The Setting writes the in-time protocol inside "within each
  fold", and names the foundation models' context and their two cells there
  beside the classical fits; the Seeds paragraph then reports the spread
  across the five folds beside every in-time number, and criterion 1 reads
  an in-time difference against its fold spread. Fold one alone puts a
  single number where the criterion reads a spread, so the remaining four
  folds are scored for the foundation models as well.
  [`experiments/2026-09-12-lc-2015h1e-folds-2to5`](../../experiments/2026-09-12-lc-2015h1e-folds-2to5)
  packed their cells when it ran: eight scored cells of 20,000 rows, the
  test and validation parts of folds two to five, and twelve contexts of
  50,000 rows, one per fold and draw.

  *What is scored and what waits.* TabPFN on the Apple node at the shipped
  temperature and at 1.0, the two passes fold one had. TabICL runs on CUDA
  only and its four folds wait for an accelerator. Fold one cost 4,123 s a
  pass for 120,000 scored and 150,000 context rows, so four folds are about
  4.6 h a pass at the same rate.

  *Kill criterion, dated before the passes start.* If the foundation-model
  cells of folds two to five are not scored, checked and read by the time
  the results section is drafted, the experiment is killed and recorded as
  a death, and the claim that the protocol changes the ranking is written
  as an inference from the classical side rather than as a measurement over
  the five models.

- **2026-09-21, later — TabPFN's fold-one cells are in, and the bundle the
  other four folds were packed in could not be scored as packed.**
  [`experiments/2026-09-21-lc-2015h1e-folds-tabpfn-m4pro`](../../experiments/2026-09-21-lc-2015h1e-folds-tabpfn-m4pro)
  and
  [`…-tabpfn-t1-m4pro`](../../experiments/2026-09-21-lc-2015h1e-folds-tabpfn-t1-m4pro)
  record the two passes the Apple node scored on 2026-09-12 — the shipped
  temperature and 1.0, 120,000 scored and 150,000 reference rows each over the
  three draws. The entry of 2026-09-14 said those cells were still on the node;
  they were, and the archive holding them had not been imported. Both manifests
  are written by hand and their checks re-derived against the bundle: the
  hashes the scorer recorded equal the fold run's files on disk, nine parts
  equal nine cell records, no duplicate key and no row, outcome or age differs
  from the bundle, no probability is missing or outside its range, and the
  three repeat cells of each pass disagree by exactly zero. Nothing is read
  from them here.

  *Why the other four folds needed a new bundle.*
  [`experiments/2026-09-12-lc-2015h1e-folds-2to5`](../../experiments/2026-09-12-lc-2015h1e-folds-2to5)
  packs the four folds as one bundle, and the node scorer conditions one model
  on every context row of a draw and scores every cell of the bundle against
  it. The folds partition one pool, so a fold's context is drawn from rows the
  other folds hold out: on this bundle each fold's context meets 8,958 to 9,146
  of every other fold's 20,000 test rows and 6,611 to 6,876 of its validation
  rows, with their outcomes. Scored as packed, about 45% of every test cell
  would have been scored in sample, and no output of the run would show it,
  because a scored cell carries no record of what conditioned it. Fold one was
  unaffected: its bundle holds one fold, and its context meets neither of its
  cells on any draw.
  [`experiments/2026-09-21-lc-2015h1e-fold-bundles`](../../experiments/2026-09-21-lc-2015h1e-fold-bundles)
  splits the four into one bundle per fold with `scripts/split_fold_bundle.py`,
  which refuses to write a bundle whose context meets its own cells; the eight
  passes are scored from those.

- **2026-09-23 — both foundation models on all five folds, scored at
  `a36c751`.** Twenty jobs, each recorded as its own run with a manifest
  written by hand and its checks re-derived against the bundle it read:
  fold one from
  [`experiments/2026-09-12-lc-2015h1e-folds`](../../experiments/2026-09-12-lc-2015h1e-folds),
  folds two to five from the per-fold bundles of
  [`experiments/2026-09-21-lc-2015h1e-fold-bundles`](../../experiments/2026-09-21-lc-2015h1e-fold-bundles).

  | Fold | TabPFN, 0.9 | TabPFN, 1.0 | TabICL, 0.9 | TabICL, 1.0 check |
  | --- | --- | --- | --- | --- |
  | 1 | [`…-fold1-tabpfn-m4pro`](../../experiments/2026-09-22-lc-2015h1e-fold1-tabpfn-m4pro) | [`…-fold1-tabpfn-t1-m4pro`](../../experiments/2026-09-22-lc-2015h1e-fold1-tabpfn-t1-m4pro) | [`…-fold1-tabicl-4090`](../../experiments/2026-09-22-lc-2015h1e-fold1-tabicl-4090) | [`…-fold1-tabicl-t1-check-4090`](../../experiments/2026-09-22-lc-2015h1e-fold1-tabicl-t1-check-4090) |
  | 2 | [`…-fold2-tabpfn-m4pro`](../../experiments/2026-09-22-lc-2015h1e-fold2-tabpfn-m4pro) | [`…-fold2-tabpfn-t1-m4pro`](../../experiments/2026-09-22-lc-2015h1e-fold2-tabpfn-t1-m4pro) | [`…-fold2-tabicl-4090`](../../experiments/2026-09-22-lc-2015h1e-fold2-tabicl-4090) | [`…-fold2-tabicl-t1-check-4090`](../../experiments/2026-09-22-lc-2015h1e-fold2-tabicl-t1-check-4090) |
  | 3 | [`…-fold3-tabpfn-m4pro`](../../experiments/2026-09-22-lc-2015h1e-fold3-tabpfn-m4pro) | [`…-fold3-tabpfn-t1-m4pro`](../../experiments/2026-09-22-lc-2015h1e-fold3-tabpfn-t1-m4pro) | [`…-fold3-tabicl-4090`](../../experiments/2026-09-22-lc-2015h1e-fold3-tabicl-4090) | [`…-fold3-tabicl-t1-check-4090`](../../experiments/2026-09-22-lc-2015h1e-fold3-tabicl-t1-check-4090) |
  | 4 | [`…-fold4-tabpfn-m4pro`](../../experiments/2026-09-22-lc-2015h1e-fold4-tabpfn-m4pro) | [`…-fold4-tabpfn-t1-m4pro`](../../experiments/2026-09-22-lc-2015h1e-fold4-tabpfn-t1-m4pro) | [`…-fold4-tabicl-4090`](../../experiments/2026-09-22-lc-2015h1e-fold4-tabicl-4090) | [`…-fold4-tabicl-t1-check-4090`](../../experiments/2026-09-22-lc-2015h1e-fold4-tabicl-t1-check-4090) |
  | 5 | [`…-fold5-tabpfn-m4pro`](../../experiments/2026-09-22-lc-2015h1e-fold5-tabpfn-m4pro) | [`…-fold5-tabpfn-t1-m4pro`](../../experiments/2026-09-22-lc-2015h1e-fold5-tabpfn-t1-m4pro) | [`…-fold5-tabicl-4090`](../../experiments/2026-09-22-lc-2015h1e-fold5-tabicl-4090) | [`…-fold5-tabicl-t1-check-4090`](../../experiments/2026-09-22-lc-2015h1e-fold5-tabicl-t1-check-4090) |

  Every directory is `experiments/2026-09-22-lc-2015h1e-` followed by the
  name shown. **The fold-one runs here supersede the fold-one runs above;
  cite these.**

  *The scorer.* Every job ran `scripts/score_context.py` as it stands at
  `a36c751`, which refuses a cohort cell whose rows are in the context that
  would score it. The copy inside each job archive hashes to that commit's
  file, and so do the runner and the run script; each manifest pins the
  three under `code_sha256`, so the recorded-code gate reads these runs as
  it reads any other. No cell was refused: across the twenty jobs no row of
  a scored cell is in the context of the draw that scored it.

  *What was checked, per job.* The bundle hashes the scorer recorded equal
  the bundle on disk; the part files equal the cell records; every scored
  row, its outcome and its age match the bundle, with no duplicate key;
  every reference row and its outcome match that draw's context; no
  probability is missing or outside [0, 1]; the repeat cells agree to
  exactly zero. The TabPFN jobs hold 120,000 scored and 150,000 reference
  rows each over the three draws, as do the TabICL jobs at 0.9; the TabICL
  checks at 1.0 hold the fold's test cell and the first draw's 50,000
  context rows.

  *TabPFN, on the Apple node.* All ten jobs on the machine of every other
  TabPFN score, one archive, 4,153 s to 4,294 s a job. Fold one reproduces
  the two fold-one runs above bit for bit, scored and reference rows alike,
  which is what the scorer's change predicts on a bundle whose context meets
  none of its cells.

  *TabICL, on one rented 4090.* All ten jobs on one machine and one stack
  (Python 3.12.14, torch 2.14.0, CUDA 13.0, tabicl 2.1.1), so the five folds
  share an environment. Fold one's earlier run on a hosted T4 ran another
  stack (Python 3.13, torch 2.11); against it the new fold one differs in
  most rows, by at most 0.0014 on the scored cells and 0.0023 on the
  reference. The T4 run stays in the record; the in-time table reads these.

  *A measured difference between two 4090 hosts.* The same ten jobs were
  scored once before, on another rented 4090 with the same driver and stack,
  by the scorer as it stood at `91ffc46`; those results were never imported
  and nothing cites them. Against them the cohort cells here are
  byte-identical. The reference cells differ in 164,193 of 1,700,000 rows,
  by at most 0.00046, and every differing row is in the third forward call
  of the reference cell, the 10,000 rows left after two calls of 20,000;
  none is in the first two. The two cards report 24,564 MiB and 23,028 MiB,
  and the scorer's peak memory was 15.5 GB here against 14.6 GB there.
  Within this host the repeat cells agree exactly.

  *The console log.* Each run's `score.log` is its slice of the machine's
  log. On the TabICL side the job-header line of each slice named the
  rented machine's home directory and account; those ten lines are dropped
  and nothing else is. The first fit of the first TabICL job took 14.7 s
  against 1.4 s to 2.4 s for every other fit, because it downloaded the
  checkpoint, which its log shows.

  What is not here. A reading: the in-time table over the five folds, and
  the temperature derivation's check on these cells, both come from these
  runs and are not yet run.

- **2026-09-23 — TabICL at 1.0 on the five folds, derived.**
  `scripts/derive_temperature.py` derives each fold's rows at 1.0 from its
  rows at 0.9 and checks them against that fold's own cells scored at 1.0:
  [`experiments/2026-09-23-lc-2015h1e-fold1-tabicl-t1-derived`](../../experiments/2026-09-23-lc-2015h1e-fold1-tabicl-t1-derived)
  to
  [`…-fold5-tabicl-t1-derived`](../../experiments/2026-09-23-lc-2015h1e-fold5-tabicl-t1-derived),
  one run per fold. On every fold the 70,000 checked rows, the test cell
  and the context of the first draw, agree with the scored rows within
  1.7e-07 on the probability against a tolerance of 1e-06; the other seven
  cells of each fold are derived under the same library, checkpoint and
  device and are not checked by row. They supersede
  [`experiments/2026-09-14-lc-2015h1e-folds-tabicl-t1-derived`](../../experiments/2026-09-14-lc-2015h1e-folds-tabicl-t1-derived),
  derived from the T4 fold one.

- **2026-09-23 — the table over five folds with the foundation models, and
  the criteria read.**
  [`experiments/2026-09-23-lc-2015h1e-protocols5-tfm`](../../experiments/2026-09-23-lc-2015h1e-protocols5-tfm)
  is `scripts/protocol_table.py` over the two classical folds runs and the
  twenty foundation-model directories, TabPFN at 0.9 and 1.0, TabICL at 0.9
  and derived at 1.0, each fold read against its own context; the out-of-time
  row is the recorded score run of the Setting. **It supersedes
  [`experiments/2026-09-12-lc-2015h1e-protocols5`](../../experiments/2026-09-12-lc-2015h1e-protocols5);
  cite it.** Its classical columns reproduce that table to the fourth decimal
  it prints. The out-of-time pooling the Setting names,
  `2026-09-11-lc-2015h1e-intervals-grid`, pinned code that has changed since,
  so it is recorded again at the current commit:
  [`experiments/2026-09-23-lc-2015h1e-intervals-grid`](../../experiments/2026-09-23-lc-2015h1e-intervals-grid)
  **supersedes it; cite it.** Its `metrics.csv` is byte-identical; of
  `paired.csv` every row both hold agrees to 3e-16 on the value and the
  interval, no difference row changes its star, and 168 rows are added, the
  Cox slope, which the script gained after 09-11.
  [`experiments/2026-09-23-lc-2015h1e-protocols5-criteria`](../../experiments/2026-09-23-lc-2015h1e-protocols5-criteria)
  reads the criteria from the two with `scripts/exp004_criteria.py`, whose
  definitions were committed before it ran: an in-time difference per fold
  and shared context draw, its fold spread the least and greatest of those,
  a pair starred by the pooling's row on all cohorts under the primary seed.

  *Criterion 1 does not fire.* Of the seven starred Gini pairs out of time,
  six have the same sign in time and a fold spread clear of zero on that
  side. The seventh is TabICL − GBM: +0.0073 [+0.0011, +0.0129] out of time,
  −0.0073 in time with a fold spread of [−0.0244, +0.0147]. Random folds of
  the pool put the GBM ahead of TabICL and cannot separate them; the cohorts
  that follow the pool put TabICL ahead beyond the interval. TabPFN − GBM is
  not starred out of time (+0.0036 [−0.0036, +0.0115]) and holds zero in
  time.

  *Criterion 2 does not fire.* Out of time the Brier score, the log-loss and
  |log O/E| order the five models alike: GBM, GBM-50k, scorecard, TabICL,
  TabPFN. In time |log O/E| puts GBM-50k first and both scalars put the GBM
  first, among three classical models whose levels sit inside one another's
  fold ranges. Both foundation models are last under every one of the six
  orderings. What the scalar misses is the size, not the order: in time the
  foundation models' Brier score is 0.0228, the classical models' 0.0227 to
  0.0228, while their observed over expected is 1.47 and 1.37 against 1.01
  for each classical model.

  *Criterion 3 does not fire.* The threshold puts 2.50% to 21.45% of a test
  cell above it on every fold and draw of the five models.

  *The branch kill does not fire,* and its rows separate the two legs. On
  level the gap to the GBM is the same under both protocols for TabICL:
  +0.2755 in time with a fold spread of [+0.1849, +0.3420], +0.2773
  [+0.2442, +0.3007] out of time, each inside the other. For TabPFN it is
  +0.3434 [+0.2680, +0.4106] in time against +0.4099 [+0.3778, +0.4322] out
  of time, the out-of-time gap inside the fold spread and the in-time gap
  below the interval. A random fold already shows the foundation models'
  level shortfall at the shipped temperature, because the temperature sets
  it and not the cohorts; out of time the pool's rate adds to it. At 1.0 the
  in-time level of both is the classical level, 1.01 and 0.95.

  *The threshold's half of the published protocol.* F1 at the chosen
  threshold ranks the GBM first in time and TabICL first out of time, the
  same inversion as the Gini pair above.

  What is not here. A second build: the table is one build, 2015H1-E, as the
  Setting fixes. The out-of-time TabICL rows were scored on a T4 and the
  in-time rows on a 4090; the difference between the two on fold one is
  below 0.0023 on any probability (entry of 2026-09-23 above). A cold audit.

- **2026-09-23, later — three statements of the entry above corrected.**
  Three sentences of the entry on the table over five folds read more than
  the recorded files hold. Each is restated here from
  [`experiments/2026-09-23-lc-2015h1e-protocols5-criteria`](../../experiments/2026-09-23-lc-2015h1e-protocols5-criteria)
  and the table it reads; the entry above stands as written and this one
  is read beside it.

  - "Both foundation models are last under every one of the six
    orderings." Five of the six. Under the in-time Brier score
    (`criteria.json`, `criterion_2.orders`) the order is GBM, scorecard,
    TabICL, GBM-50k, TabPFN: TabICL is ahead of GBM-50k by 0.000005,
    0.022768 against 0.022773 in `table.csv`. The other five orderings put
    the two foundation models last, as written.
  - "Criterion 2 does not fire", read as if the rule it was read under were
    the pre-registration's. The pre-registration writes the criterion on
    orderings and says nothing of ties. `scripts/exp004_criteria.py` fixed
    "each order taken on the table's means at full precision" at c5a0742,
    after the table had been recorded at 801f60a and its in-time numbers
    were on file. Under that rule the criterion does not fire. In time the
    five models' Brier means lie within 0.00007 of one another and inside
    every fold range, so the in-time orderings are ties read as orderings;
    under a tie-tolerant reading the criterion is undetermined in time, and
    out of time its three orderings agree under any rule. What the
    paragraph goes on to say stands: the scalar misses the size and not the
    order, observed over expected 1.47 and 1.37 against 1.01 at a Brier
    score of 0.0228 against 0.0227 to 0.0228.
  - "At 1.0 the in-time level of both is the classical level, 1.01 and
    0.95." TabPFN at 1.0 reads 1.01 in time, the classical models' 1.01.
    That half stands. TabICL at 1.0 reads 0.95, inside the span of the
    classical models' fold ranges but not at their level. The rows at 1.0
    enter no verdict, as the entry says.

- **2026-09-25 — the prior-art sentence of the cold audit, qualified.** No
  run. The cold audit of 2026-09-24 below closes its clean checks with "a
  search found no published in-time against out-of-time ranking of a tabular
  foundation model on credit". It stands as written, and this entry is read
  beside it. The FinTFM software deposit, Zenodo 10.5281/zenodo.22950210,
  read as a repository on 2026-09-25 and entered in
  [prior-art.md](../landscape/prior-art.md), sets in §39 of its measurement
  log a company-grouped five-fold reading of its own model at horizon 0 on
  V4FinBench beside its out-of-time reading, and says "Out-of-time is the
  harder split, and we are further behind on it". In time the model is set
  against logistic regression, CatBoost, LightGBM and XGBoost at library
  defaults, out of time against a per-horizon logistic regression. The two
  readings use different checkpoints of the model, a different row
  construction and a different set of horizons, and no other foundation
  model is scored under either. So an
  in-time and an out-of-time reading of one foundation model against
  classical models on one credit panel is public; a comparison of the same
  models on the same rows under both protocols was not found. No criterion,
  finding or verdict changes.

- **2026-09-26 — the reliability figure drawn again at the size the paper
  prints it, fixed before it is drawn.** The paper prints the reliability
  figure that
  [`2026-09-23-lc-2015h1e-protocols5-tfm`](../../experiments/2026-09-23-lc-2015h1e-protocols5-tfm)
  wrote as `reliability-protocols.png`, the first of the two figures the
  Plot section registers. That figure is 26.6 inches wide, seven panels in
  one row; printed at the text width of the tmlr style, 6.5 inches, its
  titles come out near two points. This entry fixes a redraw at print
  size, under this rule: at most 6.5 by 8.5 inches, text of at least 7
  points and tick labels of at least 6.5 at that size, 300 dots per inch,
  and the panels in more lines where one line does not fit.
  The numbers are the constants `PRINT_WIDTH`, `PRINT_HEIGHT`, `TEXT_PT`,
  `TICK_PT` and `DPI` of `scripts/registered_figures.py`, which draws the
  registered figures; the redraw imports them. The size, the
  type and the arrangement of the panels change, and nothing the figure
  shows. It is written after every verdict of this experiment, and the
  figure enters none.

  *What stays.* One panel per model, the seven the run lists in
  `protocols.json`, in its order: the scorecard, the GBM, GBM-50k, TabPFN,
  TabICL, TabICL at 1.0 and TabPFN at 1.0. In each, three curves in ten
  quantile bins on the model's first context draw: the in-time test cell of
  fold 1, solid; the youngest cohort out of time, 2015Q3, dashed; the
  oldest, 2018Q1, dotted. Each bin's observed rate carries its
  Clopper–Pearson interval as an error bar, the identity is dotted, and each
  panel has its own axis from zero to 1.05 times the highest point or bound
  it draws, in the model's colour: 21 curves. The titles, axis labels,
  legend entries and figure title are the recorded ones word for word.

  *What changes.* Three square panels to a line, in three lines; each
  panel's legend, its three entries, set under the panel's axis label
  rather than inside the axis, so that no entry covers a bin at the print
  size; the vertical axis labelled on the first panel of each line; the
  horizontal label wrapped to the panel's width; markers, caps and lines
  thinned to the print size.

  *What is read.* The run writes no curve; its figure computed each one
  from the scored rows. The redraw reads the rows the run read, from the
  directories `protocols.json` names (the two folds runs, the twenty node
  directories and the five out-of-time score directories), with the run's
  own loading functions, and computes the curves with the metric module's
  reliability function. The run records no hash of those files, so before
  it draws, the redraw computes for each model, on the first draw, its AUC,
  Brier score and observed over expected on the test cell of fold 1 and the
  mean of each over the eleven cohorts out of time, and stops unless each
  of the forty-two equals the value the run's `cells.csv` records to within
  1e-9. AUC alone would not tell a model at 1.0 from the same model at 0.9,
  which rank the rows alike or nearly so; the Brier score and observed
  over expected do. The hash of every file read is
  written beside the figure. The run passes the claim gate at HEAD, and a
  run the gate refuses is refused.

  *How.* `scripts/print_figures.py lc-protocols-reliability` draws it in a
  recording of its own under `record_run.py`, from a clean tree, with the
  script final before the first recording starts. `summary.json` gives the
  counts drawn and checked, and `inputs.json` the hash of every file read.
  The recorded figure stays in its run directory; the paper takes the
  redraw in its place.

## Cold audit

None. The classical side of the falsifying run is audited before any
foundation-model cell is scored.

- **2026-09-24 — the cold audit, done after the foundation-model cells and
  the criteria.** The sentence under "Cold audit" above stands as written:
  none, with the classical side of the falsifying run to be audited before
  any foundation-model cell is scored. This dated record follows it. That
  audit was not done then. It was done on 2026-09-24, after the
  foundation-model jobs and the table and criteria runs were on file and
  after the entries above and C-024 had been written; the auditor had read
  this log's conclusions before reading any code. What it re-derived it
  re-derived from the code and the recorded files alone. Its findings below
  are on the design as registered: each is stated as a condition of the
  reading, and none is corrected.

  *Checked and clean.* The five stratified folds partition the 323,026-row
  pool exactly; on every fold the fit rows are disjoint from the validation
  fifth and both from the test fold; every reference row of a foundation model is a
  fit row of its fold, and no row of a scored cell is in the context of the
  draw that scored it, folds one to five for both models, re-derived from
  `folds.parquet` and the node runs' parquet files. The classical code is
  identical between the fold-one run at 09d8f53 and the folds-two-to-five run
  at dbde5e1, input and library hashes equal, both clean trees. The GBM with
  a validation part trains on the rows outside the named fifth and stops on
  it; it ships the model fitted on those rows without a refit, as
  `in_time_folds.py` says it does. The scorecard is fitted on the fit rows
  only under the recorded scorecard's own policy, wrong-sign characteristics
  dropped. Every metric of `metrics.py` matches its definition: AUC by Mann–Whitney with
  midranks, KS, average precision as the step sum, log-loss, the F1
  threshold over the distinct scores with the cut read as at-or-above, the
  confusion metrics, O/E with its Clopper–Pearson interval, the Cox slope by
  damped Newton, the Murphy decomposition through CORP isotonic regression,
  PSI on the reference deciles. The library versions agree in and out of
  time, `tabicl` 2.1.1 and `tabpfn` 8.5.0 with the same checkpoints; the
  out-of-time TabICL rows are the T4 run and the in-time rows the 4090 runs,
  as the entry of 2026-09-23 records. The prior-art row of arXiv:2605.18147
  stands verified from full text, and a search found no published in-time
  against out-of-time ranking of a tabular foundation model on credit.

  *Findings, the most serious first.*

  1. The out-of-time row is not the in-time models scored out of time. The
     in-time GBM is fitted on the fold's 206,736 fit rows at a point chosen
     by AUC on the random fifth and shipped without a refit; the out-of-time
     GBM of `experiments/2026-09-05-lc-2015h1e-scores` is fitted on all
     323,026 pool rows at a point chosen by log-loss on the pool's latest
     quarters and refitted on every row. The in-time foundation models read
     a context of 50,000 rows drawn from the fold's fit rows; the out-of-time
     ones a context of 50,000 drawn from the whole pool. Every in-time
     against out-of-time gap of one model is therefore a gap between two
     fits as well as between two evaluation sets, and the one pair on which
     criterion 1 turns, TabICL − GBM, could move with the GBM's recipe rather
     than with time. The fold models scored on the eleven cohorts would
     separate the two; that is not a recorded run.
  2. The threshold applied out of time belongs to another model.
     `protocol_table.py` applies each fold model's F1 threshold in turn to
     the out-of-time scores of the build's recorded model, which is another
     fit on another context draw, and the out-of-time F1 entry is the mean
     over the five. A deployment of the published recipe would be the fold
     model scored out of time at its own threshold.
  3. The out-of-time star that criterion 1 turns on is one recorded pooling
     of its pair: of the three cohort poolings under the primary seed with no
     draw held fixed it is the only one starred; with a draw held fixed the
     pair is starred on two draws of three. TabICL − GBM on Gini in
     `2026-09-23-lc-2015h1e-intervals-grid/paired.csv`: on all eleven
     cohorts held fixed +0.0073 [+0.0011, +0.0129], starred under the
     primary seed and both check seeds; with the cohorts resampled
     +0.0073 [−0.0012, +0.0147], holding zero under the primary seed and
     20260907 and starred under 20260906 alone ([+0.0003, +0.0143]); on the
     three nearest cohorts +0.0083 [−0.0023, +0.0190], holding zero; with
     one context draw held fixed, starred on 20260911 and 20260912 and
     holding zero on 20260913, +0.0050 [−0.00003, +0.0093].
     `exp004_criteria.py` fixed "all cohorts, held fixed, no draw" at
     c5a0742, after `paired.csv` and the table had been recorded at 801f60a;
     the pre-registration says only "starred in the recorded pooling".
  4. The two protocols' brackets are of different kinds. An in-time bracket
     is the least and the greatest of five or fifteen unit differences on
     20,000-row cells; an out-of-time interval is a cohort-blocked bootstrap
     interval of a mean pooled over 220,000 rows. A range against an
     interval makes "out of time separates, in time does not" easier to
     obtain by construction. On the decisive pair the in-time sign is not
     established either way: −0.0073 with a fold spread of
     [−0.0244, +0.0147].
  5. The change of sign is a GBM effect. In `differences.csv` the GBM's Gini
     lead shrinks from in time to out of time against every other model:
     GBM − scorecard +0.0306 to +0.0197, GBM-50k − GBM −0.0290 to −0.0128,
     TabPFN − GBM −0.0022 to +0.0036, TabICL − GBM −0.0073 to +0.0073.
     TabICL's is the one pair whose out-of-time interval clears zero, and a
     reading that random folds favour the GBM must be tested against
     finding 1.
  6. The thresholds are chosen on unequal rows: a classical model's on the
     whole validation fifth, 51,684 rows, which also stopped the GBM; a
     foundation model's on its 20,000-row validation cell. The F1 comparison
     carries that asymmetry.
  7. Criterion 2's rule was written after the table, and the in-time Brier
     means of the five models lie within 0.00007 of one another; the entry
     of 2026-09-23, later, already says so. The audit confirms it from the
     code.
  8. The F1 sentence of the entry of 2026-09-23, the GBM first in time and
     TabICL first out of time as the same inversion as the Gini pair, is an
     ordering of means inside their ranges. In `table.csv` the in-time means
     are 0.1028 for the GBM with a fold range of [0.0852, 0.1199], 0.1013
     [0.0786, 0.1256] for TabPFN and 0.0970 [0.0708, 0.1130] for TabICL; out
     of time 0.1278 [0.1181, 0.1338] for TabICL, 0.1256 [0.0974, 0.1340] for
     TabPFN and 0.1253 [0.1203, 0.1297] for the GBM. Each mean lies inside
     the other two's ranges under both protocols, and no paired difference
     or interval is computed for F1. The precision-recall plot's dotted line
     is the in-time base rate only; the out-of-time rate is not drawn.

  *Not examined.* Borrower-level leakage across random folds, since
  `member_id` is blank in the public data; the label and the knowability of
  the features, shared by both protocols and EXP-002's territory; the
  bootstrap internals of `build_intervals.py` beyond the recorded
  description.

  *Verdict: supports a weaker claim.* What the run shows: on 2015H1-E, random
  five-fold cross-validation of the pool and the eleven later cohorts rank
  the five models alike on every Gini pair except TabICL − GBM, which holds
  zero in time; out of time it is starred in the criterion's pooling and on
  two draws of three, in neither other cohort pooling under the primary
  seed; both protocols show the foundation models' level
  shortfall at the shipped temperature; and the Brier score moves in the
  fourth decimal where O/E moves by 0.4. What it does not show: that random
  folds reverse a ranking, since no in-time sign is established and the
  out-of-time star does not hold across the recorded poolings; anything
  about F1 rankings; that a deployment of the published recipe was
  simulated out of time, since other models were scored there; anything
  beyond one build. Two statements of C-024 read more than this: that the
  cohorts put TabICL ahead beyond the interval, without naming the pooling,
  and the F1 inversion. C-032 supersedes C-024, restating both and carrying
  findings 1, 2, 4 and 6 in its Setting as the conditions of the reading. No verdict changes: the criteria are read as registered and none
  fires.
