---
id: 002
title: Tabular foundation models out of time on a book whose risk moved
dataset: lending-club (wordsforthewise, accepted_2007_to_2018Q4)
status: open
opened: 2026-09-04
closed:
---

# EXP-002 — TFMs out of time, in calibration, and under population shift

The published evaluations of tabular foundation models report discrimination on
splits that do not order time. This one holds the split fixed at what a lender
actually faced — a build date, the twelve months of outcomes nobody had seen
yet, and the cohorts written afterwards — and asks what happens to
discrimination, to calibration and to the score distribution as the model ages
across a book whose own default rate rose by a factor of 1.72, from 1.99% at
2013Q4 to 3.43% at 2016Q2, in one step rather than as a trend.

The hypotheses below are written before any model is fitted. Each carries the
observation that ends it.

## Question

Across nine half-yearly build dates on Lending Club originations, do TabPFN-3
and TabICLv2 decay in discrimination, lose calibration, or destabilise their
score distributions faster than a WOE-and-logistic scorecard and a tuned
gradient-boosting model given the same training rows?

## What the measurement discriminates

> If the TFMs' AUC-against-age slope is no worse than the GBM's while their Cox
> calibration slope drifts further from one, the belief that a zero-shot
> in-context learner inherits the calibration of its prior is wrong, and the
> failure is in the level rather than the ranking. That is a specific,
> actionable finding for a model-acceptance process, which cares about the
> level.
>
> If both slopes track the GBM's, the paradigm survives an out-of-time test it
> has not been given, and the finding is that the published rankings hold under
> a protocol the published work did not use.
>
> If the TFMs decay faster on both axes, the in-context prior is doing worse
> than a fitted model at exactly the point where it is claimed to need no
> fitting.

The design cannot produce a fourth outcome in which everything is stable,
because the book is not: on the scored rows themselves the twelve-month default
rate runs from 2.0% at 2013Q4 to 3.4% at 2016Q2, and every model carries that
shift. The size of it is measured in
[`experiments/2026-09-04-lc-vintage-builds-rolling4`](../../experiments/2026-09-04-lc-vintage-builds-rolling4),
where each expanding build's training-pool default rate sits 0.1 to 0.9 points
below the mean rate of the cohorts it is then scored on. The rolling arm sits
level with what it scores at the two ends of the grid, 2013H1 and 2017H1, and
up to 0.9 points below it in the middle.

## Setting

- **Dataset and vintage range.** `accepted_2007_to_2018Q4.csv.gz`. Origination
  quarters 2010Q1 through 2018Q1; the last is a measurement rather than a
  choice, since performance is observable to 2019-03 and a twelve-month label
  therefore matures no later than an origination in 2018-03 (EXP-001).
- **Label.** Twelve-month default from origination, ADR-0005, with the
  twenty-four-month window as the sensitivity check. Immature loans are dropped
  rather than labelled non-default.
- **Split.** `outoftime.vintage.builds`, which assembles every build through
  `splits.temporal_split` and then asserts, against the origination dates
  rather than against its own summary fields, that no training loan was
  originated after `T − 12 months` and no scored loan on or before `T`. Nine
  as-of dates, the end of each half-year from 2013-06 to 2017-06. The rows
  originated inside the blind gap `(T − 12m, T]` are neither trained on nor
  scored; there are between 88,218 and 472,734 of them per build, and they are
  the twelve months of outcomes a study that trains up to `T` gives itself.
- **What the split cannot check.** This file carries no borrower key —
  `member_id` is null in all 2,260,668 rows and `id` is a loan key — so the
  entity check of `splits.temporal_split` runs on nothing here, and a borrower
  who took a loan before `T` and another after it appears in both windows. A
  crude proxy bounds the exposure at 15.9% of rows
  ([`experiments/2026-09-04-lc-label-sensitivity`](../../experiments/2026-09-04-lc-label-sensitivity)).
  The bound is loose and it applies equally to every model, so it does not
  favour one over another; it does mean no result here may be described as free
  of entity leakage, and a reviewer will ask.
- **Training arms.** Expanding, 2010Q1 to `T − 12m`, as the primary; rolling,
  the last four quarters ending at `T − 12m`, as the robustness arm. Four
  rather than the customary eight because eight is not a rolling window on
  this book — see H4 below. For a TFM the arm and the context sample are the
  same knob: every expanding pool and every rolling pool but the first exceed
  the 50,000-row context, so the arm decides what the context is a sample
  *of*.
- **Scoring rows.** One fixed sample of 20,000 rows per test quarter, drawn
  from that quarter alone under seed 20260902, shared by every build, arm,
  model and seed. Quarters below 20,000 eligible rows are used whole.
- **Models and tuning budget.** Scorecard (monotonic WOE binning, IV ≥ 0.02
  screen, at most 20 characteristics, logistic regression), LightGBM on the
  full pool, LightGBM on the same 50,000-row context the TFM gets, TabPFN-3 and
  TabICLv2 at defaults with no fine-tuning. The GBM's tuning budget is a fixed
  small grid with time-ordered inner validation on the last four quarters of
  the pool; the TFMs get none, and that asymmetry is stated wherever a
  comparison is reported. Binning and tuning are refitted inside every build on
  its training rows only.
- **Features.** The model matrix of `features.py`, the same for every model:
  the origination-knowable set of `lending_club.py` less free text, geography
  below the state, four columns that duplicate another column, and two that
  are a function of another column and the calendar — `int_rate`, which Lending
  Club sets from a rate table indexed on sub-grade and month so that given
  `sub_grade` its residual is the origination month, and `installment`, which
  carries the rate. Two credit-line dates become durations. Ninety-seven
  characteristics, screened by `assert_features_knowable`, with every drop
  measured on the book by the run that uses it. The largest drop is for
  coverage: sixty-eight columns that Lending Club began reporting after the
  first cohort of the book — in batches at 2012Q2 to 2012Q4, 2013Q2, 2016Q1
  and 2017Q3 — are out, because on a training pool that straddles the batch
  date their missingness is an origination-date indicator with a default rate
  attached, and out of time nobody is missing. The matrix is the twenty-nine
  columns reported from 2010Q1 onward, and the run re-measures every column's
  onset and refuses to proceed on a book where the list does not hold.
  `sub_grade` stays: it is the
  lender's own grade, known at origination, and what a lender's model actually
  reads. Every model therefore inherits Lending Club's regradings across the
  book, and any drift measured here is drift in the population and in the
  lender's grading together — the same for every model class, and not
  separable on this file.
- **Metrics.** AUC with a DeLong interval, Gini, KS; Brier with its Murphy
  decomposition, calibration-in-the-large as observed over expected with a
  binomial interval, Cox recalibration intercept and slope, a ten-bin quantile
  reliability curve; PSI of the score distribution against the build's training
  rows on ten bins fixed at the training deciles, read against the Yurdakul
  critical value at α = 0.05 rather than the 0.10 and 0.25 folklore.
- **Seeds.** Three context seeds per TFM build and per GBM-50k build. The
  scorecard and the full-pool GBM are deterministic given the build. Every
  number is reported beside its seed spread, and an effect inside that spread
  is not an effect.

**Note of 2026-09-19, on the borrower proxy.** The bullet on what the split
cannot check says a crude proxy "bounds the exposure at 15.9% of rows". It
does not bound it. The proxy is an exact-match key on the three-digit zip,
the state, the earliest credit line, the employer text and the home
ownership, and 358,431 rows, 15.9%, sit in keys spanning more than one
origination quarter
([`experiments/2026-09-19-lc-label-sensitivity`](../../experiments/2026-09-19-lc-label-sensitivity),
which restates the run the bullet cites). The key joins unrelated borrowers
who share those five fields, so the count can overstate repeat borrowing;
and it misses every repeat borrower whose employer text or any other of the
five changed between loans, case and spacing of the free-text employer
included, so it can understate it. The count is a property of the key and
bounds repeat borrowing in neither direction, as the cold audit recorded in
[EXP-002-log.md](EXP-002-log.md) already reads it. The bullet's conclusion
stands and is the one to quote: the file carries no borrower key, the
exposure is unmeasured, and no result here may be described as free of
entity leakage. It still applies alike to every model, since every model
reads the same split.

## Pre-registered hypotheses and their kill criteria

**H1 — discrimination decay.** The slope of AUC against model age in quarters
is no worse for the TFMs than for GBM-50k, which sees the identical rows.

> *Killed if* the TFM slope is more negative than the GBM-50k slope by more
> than the seed spread of either, on the expanding arm, pooled over builds.
> Killed in the other direction — that is, H1 confirmed and uninteresting — if
> no model's slope differs from zero by more than its seed spread, because then
> the book's twenty-quarter span does not age a model at all and the
> discrimination axis carries no signal on this dataset.

**H2 — calibration under a base-rate shift.** Across the rise in the book's own
default rate, every model loses calibration-in-the-large, and the TFMs' Cox
slope stays closer to one than the scorecard's.

> *Killed if* the TFMs' mean absolute Cox-slope deviation exceeds the
> scorecard's on the expanding arm. This one may well fail, and the failure is
> as publishable as the confirmation. A second kill: if no model's
> observed-over-expected ratio leaves its binomial interval on any cohort, the
> base-rate shift is not large enough to test calibration and the calibration
> axis needs a dataset with a wider swing.

The shift H2 rides on is the book's realised rate, and that is the right
yardstick for a model's calibration — the model was fitted on realised
outcomes and is scored against them. It is not a statement about the lender's
credit quality, and the two diverge here:
[`experiments/2026-09-04-lc-label-sensitivity`](../../experiments/2026-09-04-lc-label-sensitivity)
holds the grade mix fixed and finds the deterioration running to the end of the
book, 3.14% to 3.98% at 2018Q1, where the realised line flattens after 2016.
Any sentence this experiment produces about "the book getting riskier" names
which of the two it means.

**H3 — stability.** TFM score distributions cross the PSI critical value on no
more cohorts than GBM-50k does.

> *Killed if* the TFMs cross on strictly more cohorts than GBM-50k, counting a
> cohort once per model across seeds. Killed as uninformative if every model
> crosses on every cohort past a given age, since the test then measures the
> book rather than the model — in which case the reported quantity becomes the
> age at first crossing rather than the count.

**H4 — context policy.** The rolling arm reduces calibration drift for the TFMs
by more than it does for GBM-50k.

> *Killed if* the difference in mean absolute Cox-slope deviation between arms
> is no larger for the TFMs than for GBM-50k, within the seed spread.

H4 is only a hypothesis if the two arms differ, and on this book the customary
eight-quarter window does not deliver that:
[`experiments/2026-09-04-lc-arm-contrast-rolling4`](../../experiments/2026-09-04-lc-arm-contrast-rolling4)
measures it as holding 71% to 90% of the expanding pool and as making the mean
training row between 0.56 and 2.63 quarters younger — half a quarter at the
2013H1 build, which is the build with the longest trajectory. The lender's
volume grows fast enough that its last two years are most of its history. The
study's window is therefore four quarters, which holds 43% to 63% of the pool
and moves the mean row by 1.99 to 4.13 quarters at every build. The contrast
still grows across the grid, roughly doubling from 2013H1 to 2017H1, so H4 is
reported per build against that build's measured contrast as well as pooled,
and the pooled number is read with the gradient beside it.

### Amendment of 2026-09-04

Made after the cold audit below and after the scorecard run, before any
gradient-boosting or foundation-model run, and before any Cox slope or PSI had
been computed for any model. The hypotheses above are left as written; what
follows replaces their kill criteria, and every later result is read against
this text.

**The noise floor.** "Seed spread" is not a noise floor for a deterministic
model, and a paired comparison across cells that share their scored rows
cannot take the cells as independent — the 20,000 rows of a cohort enter every
build that scores it, so the 99 cells of an arm hold 380,000 distinct rows,
not 1,980,000. Every criterion below is therefore read against a
**cohort-blocked bootstrap**: resample the scored rows within each cohort,
recompute every model's metric on every build from the same resample, and
take the interval of the pooled paired statistic over 200 resamples. Where a
model has context seeds, the seed is drawn with the resample, so the interval
carries both sources. "Beyond the interval" below means outside the 95%
bootstrap interval of the paired difference.

**H1.** The primary criterion stands as a paired difference of slopes and is
read against the bootstrap interval rather than the seed spread. The second
branch is rewritten: H1 is uninformative if, for every pair of models, the
difference of slopes lies inside its interval — the discrimination axis then
does not separate model classes on this book. Model age and calendar quarter
are exactly collinear given the build, so no slope is read as ageing; only
differences between models on the same cells are read, and the common
component is whatever the book did.

**H2.** The first clause — that every model loses calibration-in-the-large —
is withdrawn as a hypothesis. It is a property of the grid, measured before any
model was fitted, and it is reported, not tested. What remains: on the
expanding arm, the TFMs' mean absolute Cox-slope deviation is no larger than
the scorecard's, paired by cell. *Killed if* the TFM exceeds the scorecard
beyond the interval. The second kill, on the observed-over-expected ratio, is
withdrawn: it was already known not to fire in the direction it was written
for.

**H3.** The count of critical-value crossings is withdrawn. At 20,000 scored
rows against reference pools of 31,016 and upward the Yurdakul critical value
at α = 0.05 lies between 0.0009 and 0.0014, every real movement of the book
crosses it, and a count of crossings compares two saturated counters. The
critical value is reported beside every PSI, as the statement that the movement
is real, and the hypothesis becomes one of magnitude: the PSI of the TFM score
distribution against its own training reference — the build's training rows
for a fitted model, the context sample for a TFM — is no larger than GBM-50k's
on the same cell. *Killed if* the TFM's PSI exceeds GBM-50k's beyond the
interval, pooled over the expanding arm. Read with H2 rather than alone: a
score distribution that moves with the book is what a calibrated model does
on a book that moved, so a smaller PSI is not by itself the better result.

**H4.** Unchanged in form; "within the seed spread" is read as "inside the
interval".

**The experiment's second kill criterion** below is read the same way: an
effect inside the interval is not an effect.

### Amendment of 2026-09-04, late

Made after the cold audit of the uniform scorecard run (below), after one
gradient-boosting run on the matrix that audit broke, and before any
foundation-model run. It replaces three sentences of the Setting — the
description of the matrix, the GBM's tuning budget, and the naming of the
context seeds — and changes no hypothesis and no kill criterion. Every later
result is read against this text.

**The matrix is twenty columns, and the coverage rule reads values.** The
Setting says the twenty-nine columns Lending Club reported from 2010Q1. Five of
them — `tax_liens`, `collections_12_mths_ex_med`, `chargeoff_within_12_mths`,
`acc_now_delinq`, `delinq_amnt` — are zero on every loan of the book through
2012Q3 and take their first non-zero value in 2012Q4: the file was back-filled
with zeros where the field was not yet collected, so `coverage_report`, which
reads presence, passed them. On a training pool that crosses 2012Q4,
`tax_liens > 0` is "originated after", with the book's rising default rate
attached, which is the failure the coverage rule was written against arriving
through a value instead of a gap. The scorecard never split on them because
their non-zero mass sits under the bin-size floor; a booster has no such floor.
Three categoricals do the same with a level: `initial_list_status` has one
level until the whole-loan programme of 2012Q4 and the other on 64% of the
book, `application_type` one level until 2015Q4, `disbursement_method` one
until 2016Q1. `addr_state` does it by degrees — Lending Club entered states one
at a time, and 8% of the book sits in a state absent from the first cohort;
3% of the 2018Q1 sample is in a state the 2013H1 pool never held. Two numeric
columns carry the calendar in their range: the lender's caps on `dti` moved
25 → 30 → 35 → 40 and on `loan_amnt` 25,000 → 35,000 → 40,000, so a value
above the first cohort's cap dates a loan, on 23% and 13% of the book.

The rule is now uniform coverage *by value*: every value or level the matrix
holds must exist in the first cohort. A column constant there, or carrying a
late level on more than a twentieth of the book, is out — the nine above,
listed with what was measured in `features.VALUE_CARRIERS`. A numeric range
that grew is clipped to the first cohort's own bounds, `features.CLIPPED`.
Late values under the floor — one loan purpose, two rare tenure codes — are
left alone. `value_report` re-measures every column on the book in use and
refuses a disagreement, and both run scripts call the three gates on the
matrix before fitting anything. The first cohort moves from 2010Q1 to 2010Q2,
a cost of 2,172 rows, because the 60-month product appeared in May 2010 and
the same rule applied one quarter earlier would take `term`. What survives is
the application and bureau set reported in full from the start: twenty
columns.

The cost of the previous matrix was measured before it was replaced.
[`experiments/2026-09-04-lc-gbm-builds`](../../experiments/2026-09-04-lc-gbm-builds)
is a full GBM grid on the twenty-nine columns, superseded on arrival and kept
for one number: how much split gain the booster took from the columns now
removed. On the expanding arm it took under half a percent from the five
zero-backfilled counts and under a quarter of a percent from
`initial_list_status`, `application_type` and `disbursement_method` together
— but 7% to 13% from `addr_state`, its second-ranked column at every build,
and 3% to 6% each from `dti` and `loan_amnt`. The carriers the rule removes
were in use, through geography and the caps rather than through the columns
the audit named first.

**The GBM's early-stopping set is sized by row share, not by four quarters.**
The Setting says the last four quarters of the pool. That is sound on the
expanding arm and impossible on the rolling one, whose whole pool is four
quarters wide: holding four out leaves nothing to fit on. The rule in
`gbm.validation_split` is the fewest latest whole quarters of the pool that
together hold at least 20% of its rows, never fewer than one, never more than
four, and never more than half the quarters in the pool; on this book that is
one or two quarters on either arm, because volume roughly doubles each year.
What the sentence was for is untouched: the early-stopping set is the *end* of
the pool and no fold of it is random. Hyperparameters and the round count are
chosen against that tail; the model that is scored is then rebuilt on every
labelled row the builder had, at the chosen round count, because the
alternative hands the GBM a fifth fewer rows than the scorecard reads on the
same build and turns a model-class comparison into a data-budget comparison.
The search is sixteen points — `num_leaves`, `learning_rate`,
`min_child_samples` and `feature_fraction` at both ends of their useful
ranges — with early stopping on validation log-loss, patience 50, ceiling
2,000. LightGBM is run with `deterministic` and `force_row_wise` set, for the
reason the binning solver moved off CP-SAT, and every run refits one build
twice and records the largest disagreement in its predictions.

**The context seeds are named:** `vintage.CONTEXT_SEEDS = (20260911, 20260912,
20260913)`, read by GBM-50k and by both foundation models, so that a
difference between two models is never a difference between two draws. Only
the context seed varies across the three; the booster seed is held fixed,
which makes the spread a sampling spread.

**The scorecard's missing bins.** A missing bin is outside the bin-size floor,
and on the uniform run the largest-magnitude weight anywhere in the grid,
−3.65 on `dti` at 2016H2, rested on two training rows and was applied to
fifty-five scored ones. A missing bin thinner than a hundred rows now scores
at WOE zero, `ScorecardPolicy.min_missing_count`; the card records which
characteristics it applied that to.

**Addendum after the fourth cold audit, the same night.** Two changes to the
GBM protocol above, both from that audit's findings on the byvalue runs. The
context control no longer runs its own search: it takes the point its build's
full-pool search chose and re-chooses only the round count, so that the spread
across its three draws is the spread of the rows — the search had been
deciding between draws sharing 97.6% of their rows by margins of a
ten-thousandth in log-loss, and a zero-shot model carries no such component.
The grid is thirty-six points rather than sixteen — seven, fifteen or
thirty-one leaves; two hundred or a thousand rows per leaf; four, six or ten
columns in ten; the two learning rates — because the sixteen-point search sat
on its most regularised corner at thirty-five of seventy-two fits, and a run
now writes a note whenever the best point sits on any edge of the grid, with
the margin it won by.

**Second addendum, after the fifth cold audit.** LightGBM's dataset-time
`feature_pre_filter` is switched off for every dataset the module builds: with
it on, the thirty-six points were scored on bins filtered for the first
point's leaf size and the refit at the chosen point saw different bins, a gap
of 5.6 × 10⁻⁴ in log-loss on 2013H1-R that exceeded every margin the search
decided by. The GBM is described from here on as tuned within a stated budget
on a surface that is flat at the resolution of the result — margins of
3 × 10⁻⁶ to 3 × 10⁻⁴ against a paired standard error near 0.01 of Gini — and
neither the per-build hyperparameter table nor the importance heatmap is read
as a measurement of drift. The edge note reports only knobs with an interior.

### Amendment of 2026-09-06

Made after the cheapest falsifying run and its seventh cold audit, after one
probe on the same bundle with one setting moved, and before the grid. It
changes no hypothesis and no kill criterion; it fixes the setting every
calibration statistic is read at, which the Setting left to the libraries'
defaults, and it adds one derived row to the grid.

**The temperature is a calibration statistic's setting, and it is named.**
Both foundation models ship `softmax_temperature = 0.9`, and on the
falsifying run's rows the temperature is a scale on the logit — exactly so
for TabICL, which averages logits before the softmax, and to a mean
departure of 0.008 on the logit for TabPFN, which averages after it. A
scale on the logit leaves ranks and deciles fixed, so H1, H3 and the
stability statistics do not see it; it multiplies the Cox slope by its
reciprocal and moves the level, so H2 does. What the falsifying build's
slope and level read at each setting is in the log's entry of 2026-09-19,
later, "the falsifying build's statistics and the verdicts the amendment
notes stated, carried here" ([EXP-002-log.md](EXP-002-log.md)) (pointer of
2026-09-19). The two readings are one number, and a sentence about either
that does not name the temperature is not a sentence about the model.

From here: **H2 is read at the shipped setting as the primary reading**,
because the object under study is the model as a risk team would adopt it,
and **the same statistics at 1.0 are reported beside it on every table and
figure that carries them**, from the same rows. The kill criterion of the
amendment of 2026-09-04 is applied to the primary reading; a verdict that
differs between the two settings is reported as differing, with both
intervals, and is not resolved by choosing a setting. Every sentence in the
log or the paper about a foundation model's level or slope carries its
temperature.

**The grid scores TabPFN at both settings and TabICL at the shipped one.**
TabICL's rows at 1.0 are derived from its rows at 0.9 by the exact scale,
checked against the probe's scored rows to 1e-6 before any statistic is
read from them and refused if the check fails on any row; TabPFN's are
scored, since the scale is not exact for it. Any later version of either
library that changes how the temperature is applied breaks the derivation,
and the check is what says so.

**`balance_probabilities` is not a calibration setting and is not read.**
It divides each class probability by its context frequency and renormalises,
a shift on the logit by the log of the prior ratio; where it puts the mean
probability on this book is in the log's entry of 2026-09-19, later
(pointer of 2026-09-19). Its rows are on the record from the probe and
are not pooled into any hypothesis.

**Note of 2026-09-06, after the eighth cold audit.** Three things the
amendment left unsaid. The setting nominated as primary was nominated after
the falsifying build's rows at both settings had been read; the log's
entries of 2026-09-06 say what they read at each, and what this note said
of it is in the log's entry of 2026-09-19, later (pointer of 2026-09-19);
the obligation to report both settings on every table is
what makes the nomination bearable. The sentence that a scale on the logit
leaves the rank statistics fixed is exact for TabICL and holds only to the
fourth decimal for TabPFN, whose two settings so far were scored on two
machines; the grid scores TabPFN's two passes on one device, and no
difference between its two settings on a rank statistic is read until
they are. The level read on the context rows is a statement about the
rows the model conditioned on, and the level out of time at either
temperature is reported beside it wherever it appears.

**Note of 2026-09-06, late, after the bootstrap seed check.** A star on a
pooled difference is an interval of two hundred resamples under one seed,
and the check the eighth audit asked for
(`experiments/2026-09-06-lc-2015h1e-intervals-seeds`) read the H2 rows at
the shipped setting under the primary seed and both check seeds; what each
row's star did under them is in the log's entry of 2026-09-19, later
(pointer of 2026-09-19). From here every pooled interval that a verdict
rests on is recorded with `--check-seeds`, and a star that does not survive
every seed is reported as holding zero at the margin with the intervals
under each seed; the verdict of H2 on the falsifying build read with the
seeds in view is in the same entry (pointer of 2026-09-19). The grid's
per-build poolings carry the same check.

**Note of 2026-09-12, after the ninth cold audit.** Five things the text
above leaves unsaid or says wrongly, each read against from here.

*H1 has two identifications on this grid, and the amendment named one.*
Within a build, model age and calendar quarter are one axis, so the slope
of AUC on age with one intercept per build — the statistic the amendment
of 2026-09-04 describes and the one the arm-level pooling first computed —
is the calendar slope net of build, and a difference of two models'
calendar slopes is a difference of age slopes only if the two respond to
the calendar alike. The grid identifies age the other way as well: a
cohort is scored by up to nine builds at nine ages, so the same least
squares with one intercept per cohort holds the calendar fixed and varies
the model's age, together with the pool the model was built from. Neither
identification is free of the other's confound. From here both are
reported on every table, the build-intercept slope keeps its standing as
the criterion's statistic because it is the one written down before any
foundation-model run, the cohort-intercept slope is a reading added after
the audit and is named as such, and where the two disagree on a pair H1
supports at most the weaker claim and any text says both. The weights are
stated beside each: the build-intercept slope weights a build by the
spread of its ages, so 2013H1-E carries 34.5% of it and the four oldest
builds 87.3%; the cohort-intercept slope weights a cohort by the spread
of the ages it is scored at, so the youngest cohorts, scored by the most
builds, carry most of it and the two oldest none.

*H3's reference holds the rows the model was fitted on.* The amended
statistic reads each cell against the build's training rows for a fitted
model and the context draw for a foundation model, and that reference is
in sample for every model alike; the step from in sample to the first
scored cohort is part of what it measures, and that step is a property of
the model class before any vintage has aged. A second PSI is reported
beside it from here: the cell against the same model's scores on the
build's first scored cohort, bins fixed at that cohort's deciles, the
first cohort's own cells left out. Every model's reference is then out of
sample alike and only the movement along the vintage axis remains. The
amended statistic keeps its standing as the criterion's; the second is
added after the audit and named as such, and a verdict on H3 is read
with both in view.

*"Pooled over the expanding arm" was left unweighted.* The arm-level
pooling takes the mean over the 99 cells, which is what "paired by cell"
means and was fixed before that pooling ran; it gives 2013H1-E nineteen
cells of 99 and the three oldest builds forty-nine. The mean over builds
with every build weighted alike is reported beside it from here, under
its own scope, and a difference is not read as a property of the arm
where the two disagree in sign.

*Two numbers above are stale.* Kill criterion 1 says the smallest
expanding pool is 52,781 rows at 2013H1 and clears the context cap by
5.6%; on the matrix of the late amendment, whose first cohort is 2010Q2,
it is 50,609 rows and clears the cap by 1.2%. The criterion does not
fire. The consequence is that on 2013H1-E the three context draws are
drawn from a pool 609 rows larger than the draw and share 49,397 to
49,402 of their 50,000 rows, so the context-draw component of the
bootstrap interval is absent on that build by construction, as the
criterion already says of the rolling arm at 2013H1. The Setting's
"ninety-seven characteristics" and "twenty-nine columns" describe the
matrix before the late amendment; the matrix every recorded run uses is
the twenty columns that amendment names.

*The control inherits its hyperparameters from the full pool.* The late
amendment says so and gives the reason; it does not say what it costs.
The point chosen on a pool of up to 1,108,732 rows is applied to 50,000,
so the control is regularised for a pool up to twenty times its own; what
this does to its Gini on 2017H1-E against the scorecard's and against the
foundation models' on the identical rows is in the log's entry of
2026-09-19, later (pointer of 2026-09-19). Within a build the point is
fixed across cohorts and does not move H1's slope; it does move the
control's level and the width of its score distribution, and every
verdict against the control is read with that asymmetry named. A control
searched on its own 50,000 rows is the ablation a reviewer may ask for
and is not part of this experiment.

**Note of 2026-09-15, before any H4 statistic is read.** H4's criterion,
above and as the amendment of 2026-09-04 reads it, admits more than one
reading on five points, and the contrast its paragraph quotes was measured on
a grid the late amendment replaced. Each is fixed here before the number it
governs exists; none changes a criterion.

*The kill fires unless the interval lies above zero.* H1 to H3 are written
"no worse than", and their kill is a star on the wrong side. H4 is written
"by more than", and its kill is the absence of a star on the right side: "no
larger for the TFMs than for GBM-50k, inside the interval" holds whenever the
interval of the foundation model's reduction minus the control's holds zero,
and the experiment's second kill criterion, read as the amendment reads it,
says the same. The statistic is, per model, the mean of |Cox slope − 1| over
the 99 cells the two arms share on the expanding arm minus the same mean on
the rolling arm; H4's row is that reduction for the foundation model minus
GBM-50k's, on the same resample. The row survives when its interval lies
above zero. It is killed when the interval holds zero, and killed with a
finding of its own when the interval lies below zero, since the rolling
window then brings the control nearer a slope of one by more than it brings
the foundation model; the reading names which of the two. "Pooled" is the
cell-weighted mean the note of 2026-09-12 names, 2013H1 holding nineteen
cells of the 99, with the mean over builds beside it; the per-build rows and
the cohort-resampled pooling are beside it too, and none of them is the
criterion.

*The row is read at 0.9, with the row at 1.0 beside it.* The amendment of
2026-09-06 fixes the setting every calibration statistic is read at, and its
next sentence names H2. H4 is on the same statistic, and the temperature
moves it: a scale on the logit multiplies the slope, so |slope − 1| on either
arm changes with the setting and the reduction between arms can change sign.
H4 is read as H2 is, at the shipped 0.9 as the criterion's, with the row at
1.0 on every table and figure from the same rows, and a verdict that differs
between the settings reported as differing, with both intervals, and not
resolved by choosing one. The setting was fixed for the slope before any
rolling-arm cell existed.

*A star that a check seed loses is the kill.* The note of 2026-09-06, late,
reports a star that does not survive every seed as holding zero at the
margin. On H2 that reading lets the hypothesis stand, since its kill needs a
star; on H4 it is the kill, since survival needs one. H4 survives only under
the primary seed and both check seeds. A star lost under a check seed is
reported as killed at the margin, with the three intervals, and a star under
a check seed alone is not a star.

*A cell on which some model's Cox fit does not finish on either arm leaves
both arms for every model.* The metrics module's damped fit returns NaN where
a fit cannot finish (EXP-005, note of 2026-09-14), and a pooling stays on
identical cells. H4 compares one model's two arms and then two models'
reductions, so the same cells enter all four means; a cell left out on one
arm alone would put a cell difference inside a reduction. The count left out
of the point estimate and the largest left out of any resample are printed
beside the row.

*Draw k on one arm is read beside draw k on the other.* One context draw is
chosen per resample for every model and every build of both arms, as the arm
pooling chooses it across builds and models; the two draws are samples of
different pools under one seed, as draw k of two expanding builds already
are, and the control reads the same draws on both arms as the foundation
models. On 2013H1-R the three draws are the whole pool, and on 2013H1-E they
share all but a few hundred of their 50,000 rows (the note of 2026-09-12), so
the per-build row at 2013H1 carries no draw component, as the first kill
criterion says of that build; the pooling with each draw held fixed on both
arms is beside the mixture.

*The contrast beside H4 is re-measured on the grid the runs use.* The
paragraph on H4 quotes `lc-arm-contrast-rolling4`, measured on a grid whose
first cohort was 2010Q1. The late amendment moved the first cohort to
2010Q2, and every recorded run's expanding pool is the byvalue grid's,
smaller by the same 2,172 rows at every build, the rolling arm unchanged; so
the share the window holds and the mean age of an expanding-arm row have
both moved a little at every build. `arm_contrast.py` is recorded again on
that grid before the H4 pooling, and its share and mean-age gap are the
numbers printed beside H4 per build; they supersede the paragraph's 43% to
63% and 1.99 to 4.13 quarters as the Setting's counts are superseded by a
run's. The choice of a four-quarter window stands on the record that made
it.

**Note of 2026-09-17, after the H4 pooling and its cold audit.** Written
after
[`experiments/2026-09-16-lc-between-arm-intervals`](../../experiments/2026-09-16-lc-between-arm-intervals)
was recorded, read and audited, and after every other pooling of this
grid. It changes no hypothesis and no criterion. Five things the text
above leaves unsaid or that the run's output says wrongly, each read
against from here.

*A string in the run's summary is read against the criterion.* What H4's
criterion rows read on this book at 0.9 and at 1.0, and the string the
recorded summary gave one of them, are in the log's entry of 2026-09-19
"the numbers and verdicts the note of 2026-09-17 stated, carried here"
([EXP-002-log.md](EXP-002-log.md)) (pointer of 2026-09-19); the reading
is corrected in the script and the pooling is recorded again as superseding, which must
reproduce every value, bound and star of the first recording to the bit,
the strings alone changing.

*The row that needs no control is the one the text leads with.* Each
foundation model's own E − R is on the table as the note of 2026-09-15
has it, and the log's entry of 2026-09-19 named above says what it read
(pointer of 2026-09-19). That sentence does not depend on the control and is the one
this experiment can make about H4.

*The control's reduction is not a measurement of the window alone.* Its
E − R, the control's fits it rests on and the sensitivity rows computed
around them are in the log's entry of 2026-09-19 named above (pointer of
2026-09-19).
A sensitivity row is read for one thing, whether it lies outside the
criterion row's interval; what the rows move is the magnitude and the sign
of the point estimate, which the criterion does not read and which is not
quoted as the size of anything. The rows starred below zero, which that
entry of the log names (pointer of 2026-09-19), rest on the same fit and are
not read as the window helping the control more than the foundation models.
The point the control inherits, its build's full-pool point, differs between the arms at
every one of the nine dates, and the round count is re-chosen on each
arm's own tail, so the control's E − R mixes the window with a re-tuning
that a foundation model does not have; the per-date table of both is
printed beside H4. A control fitted at one point on both arms is the
ablation a reviewer may ask for and is not part of this experiment. The
sensitivity rows and the per-date table are recorded from the run's
`cells.csv` and the builds' fit records in
[`experiments/2026-09-17-lc-h4-sensitivity`](../../experiments/2026-09-17-lc-h4-sensitivity),
as point estimates: they replace per-cell deviations and carry no interval.

*The interval is a mixture over the context draws, as the amendment of
2026-09-04 has it.* The draw is chosen with the resample, so the interval
carries the draws' disagreement, and the per-draw rows are beside it. A
kill that holds under the mixture and under every draw held fixed is
reported as holding under both; a kill that held under the mixture and not
under some draw would be reported as holding at the margin, with the draw
named. The log's entry of 2026-09-19 named above says which this book's kill reads
(pointer of 2026-09-19).

*Kill criterion 3 is read before any trajectory is described as ageing.*
The criterion says the axis does not resolve if the per-cohort metric moves
more between the three context draws than between adjacent cohorts, and
gives no reading of "moves more". Fixed here, before the number exists: per
seeded model and build, the mean over its cohorts of the range of AUC
across the three draws, against the mean over adjacent cohort pairs of
|AUC difference| under one draw, averaged over the draws; the criterion
fires for a model when the first exceeds the second on a majority of the
nine expanding builds, and the consequence is the one written, more scored
rows rather than more models. It cannot fire on 2013H1-R, where the three
draws are one pool and the range is zero, and it is not evaluated for a
deterministic model, which has no draw. It is computed from the recorded
per-build outputs and its own run is appended to the log; if it fires,
every earlier sentence of this file's log about a slope is read with it.

**Note of 2026-09-19, on the results the note of 2026-09-17 stated.** That
note was written after H4's pooling on this book existed, and quoted it:
H4's criterion rows at 0.9 and at 1.0 with their seed checks, the recorded
summary's string for one of them, each foundation model's own E − R, the
control's E − R, its three fits at 2013H2-E, the sensitivity points around
them, and what each read. From this date the pre-registration carries no
number produced by a model fit or a pooling on this book and no statement
of what a criterion or a star read on it; numbers about the data stay. The
passages that stated such numbers or verdicts were moved whole to the log's
entry of 2026-09-19 "the numbers and verdicts the note of 2026-09-17 stated,
carried here" ([EXP-002-log.md](EXP-002-log.md)), and each place they stood
points there. The five readings the note fixes are unchanged, in words: how
a summary string is corrected, that each model's own E − R is the sentence
this book supports on H4, what the sensitivity rows are read for and that
they carry no interval, the reading of a kill under the mixture and under
each draw, and kill criterion 3's reading. No hypothesis, criterion or
reading was changed by the move; the text as it stood is in the history of
this file.

**Note of 2026-09-19, later, correcting the note above.** The sentence above
that the pre-registration carries no number produced by a model fit or a
pooling on this book was wider than the file, and the file is read against
this one instead. From this date the pre-registration carries no statistic
of a model under study on this book's rows — no metric, level, slope,
pooled difference or star — and no statement of what a criterion or a star
read on a hypothesis of this file. The falsifying build's slopes and levels
at both settings, its H2 rows' stars under the seeds and the verdict read
from them, the mean probability under `balance_probabilities`, and the
per-cell Gini of 2017H1-E were moved whole to the log's entry of 2026-09-19,
later, "the falsifying build's statistics and the verdicts the amendment
notes stated, carried here" ([EXP-002-log.md](EXP-002-log.md)), and each
place points there. What the file keeps, and why none of it is a result:
the weight that exposed the missing-bin defect, the size of the tuning
defect and the margins of its surface, the derivation's departure on the
logit, the weights of the criterion's statistic, and every number about the
data. No hypothesis, criterion or reading changed; the text as it stood is
in the history of this file.

## Kill criteria for the experiment

1. **The blind gap makes the design unrunnable.** If any build's training pool
   falls below the 50,000-row context on the expanding arm, the TFM comparison
   at that build is between a sample and a whole pool and is not comparable to
   the others. Measured: the smallest expanding pool is 52,781 rows at 2013H1,
   which clears the cap by 5.6%, and the smallest rolling pool is 31,016, which
   does not. The rolling arm at 2013H1 is therefore reported as a whole-pool
   build, not as a sample, and the seed spread there is zero by construction.
2. **The effect is inside the seed spread.** If the TFM-against-GBM-50k
   difference on the primary axis of a hypothesis is smaller than the
   seed-to-seed spread of either model, the answer is that there is no effect.
   Seeds are not added until it separates.
3. **The trajectory is sampling noise.** If the per-cohort metric moves more
   between the three context seeds of one model than between adjacent cohorts
   of one seed, the vintage axis is not resolving anything at 20,000 scored
   rows per quarter, and the fix is more scored rows rather than more models.

The criterion that kills the project branch rather than this run: if the
scorecard and the GBM are indistinguishable from the TFMs on all three axes
within their spreads, the finding is that the choice of model class does not
matter out of time on this book, and that is the paper. It is not a reason to
search for a fourth model or a fourth metric.

## Cheapest falsifying run

One build, 2015H1, expanding arm, one context seed, all five models, on the
three test cohorts nearest the as-of date rather than all eleven. That is one
TabPFN context and one TabICL context, under twenty minutes of accelerator time
at the rates recorded in
[`experiments/2026-09-04-m4pro-tabpfn-timing`](../../experiments/2026-09-04-m4pro-tabpfn-timing),
and it settles three things before the grid is committed to: whether the
scorecard and GBM land where a credit model should on this book, whether the
TFM calibration is anywhere near the others at age zero, and whether the metric
module's intervals are wide enough to swallow the effect.

If the TFMs' age-zero calibration is already outside the scorecard's interval,
H2 is answered without the grid and the grid becomes a robustness check rather
than the experiment.

## Prior art check

Stands on the same two rows of [../landscape/prior-art.md](../landscape/prior-art.md)
as EXP-001, both `verified` on 2026-08-27 from full text: arXiv:2605.18147 for
the absence of temporal structure in the other credit TFM evaluation, and
arXiv:2605.18635 for the one temporal split in the area. The statement this
experiment does *not* rest on is what the second paper's split was actually
built from; that is open until the cold audit of EXP-001 closes it.

Opened under the sweep of 2026-08-27, green on 2026-09-04 at eight days.

## Plot

Three, and none is a bar of a headline number.

- Metric against model age in quarters, one line per model, one panel per
  build — the trajectory, which is the whole point of the vintage axis.
- The reliability curve per model at the youngest and oldest scored cohort of a
  build, on the same axes, so the shape of the miscalibration is visible rather
  than a Brier score standing in for it.
- The score distribution of one model at every cohort of one build, as a ridge,
  against the training distribution the PSI bins were fixed on.

The design's own plot is already recorded:
[`build-grid.png`](../../experiments/2026-09-04-lc-vintage-builds-rolling4/build-grid.png)
shows what each build was allowed to know, where the pool outgrows the context,
and the base-rate distance every model has to carry.

## Log and cold audits

Kept apart from the pre-registration, in
[EXP-002-log.md](EXP-002-log.md): the append-only log of every run this
experiment cites, and the cold audits in the order they were made. An auditor
is given this file and not that one.
