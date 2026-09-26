---
id: 005
title: Tabular foundation models out of time on a mortgage book with two crises inside its axis
dataset: freddie-mac (Single-Family Loan-Level Dataset, sample files, Release 47)
status: open
opened: 2026-09-13
closed:
---

# EXP-005 — TFMs out of time on the second book: long trajectories across a twentyfold prevalence range

The Lending Club study (EXP-002) rests on one book, one product, twenty
quarters, and a default rate that moved by a factor of 1.72. The Freddie Mac
single-family sample is the second book: a thirty-year prime mortgage, a
different lender population, twenty-five years of origination, and two
regimes inside the axis rather than at its edge — the 2007–2008 vintages at a
twenty-four-month default rate of 3.5% to 6.4%, and a rise from 2022 to 1.2%
to 1.5% after a decade at 0.3% to 0.8%. The measurement is the same: a build
date, the outcomes nobody had yet seen, the cohorts written afterwards, and
what happens to discrimination, calibration and the score distribution as
each model ages — here over up to twenty-one years of cohorts rather than
five.

This file is fixed before any model is fitted on Freddie Mac data. Its basis
is the reduction `experiments/2026-09-06-fm-reduce3` and the structure run
`experiments/2026-09-06-fm-vintage-structure3` (EXP-003), whose layout, axis,
reduction and label were re-derived from the zips by their cold audit with no
mismatch on the loans rebuilt and no difference on any cohort count. Every
count below is a sum of that run's recorded per-quarter tables under the
label of ADR-0006, less the seasoned-acquisition exclusion this file
fixes; the build run named below records every one of them again before any
model is fitted, and a count it changes is amended here with a date.

The hypotheses and their kill criteria carry over from EXP-002 as amended on
2026-09-04 and 2026-09-06 and as noted on 2026-09-12, with the readings those
notes added pre-registered here from the start rather than appended. What is
new on this book is stated as new.

## Question

Across nine build dates two years apart on Freddie Mac originations, each
scored on every later half-year cohort through 2023H2, do TabPFN-3 and
TabICLv2 decay in discrimination, lose calibration, or destabilise their
score distributions faster than a WOE-and-logistic scorecard and a tuned
gradient-boosting model given the same training rows — and does the verdict
of EXP-002 hold on a book whose prevalence spans a factor of twenty-two
across the cohorts it is read on?

## What the measurement discriminates

> If the TFMs' AUC-against-age slope is no worse than the control's while
> their Cox slope drifts further from one than the scorecard's, the finding
> of EXP-002 replicates on a second product, a second lender population and
> a horizon four times longer, and the failure is in the level rather than
> the ranking on both books.
>
> If both slopes track the control's on this book but not on Lending Club,
> or the reverse, the verdict is a property of a book and not of the model
> class, and the paper says which property of the book — the prevalence
> range, the horizon, or the product — the two books differ in.
>
> If the TFMs decay faster on both axes here, the in-context prior does worse
> than a fitted model at the horizon a mortgage model actually serves.

The design cannot produce an outcome in which every model is stable in the
large, because the book is not: the scored cohorts run from 0.29% (2020H2) to
6.39% (2007H2) at twenty-four months under the primary label, and the builds
written before 2007 score the crisis vintages at five to seven times their
own training rate, while the build written after it — 2010H2, with a pool at
1.75% — scores every cohort it has at a quarter to seven eighths of its own.
Calibration in the large is a property of the grid, measured before any model
is fitted, and it is reported, not tested. What is tested is the slope, and
the difference between models on identical cells.

What the second book adds that the first cannot give: a prevalence range,
scored cohorts at 110 to 1,557 defaults, and a trajectory long enough that a
model built in 2002 is read on a cohort written twenty-one years later.

## Setting

- **Dataset and vintage range.** The sample files of the Single-Family
  Loan-Level Dataset, Release 47 (July 2026), reduced by
  `scripts/freddie_mac_reduce.py` to one row per loan with the origination
  columns and the label's inputs, `experiments/2026-09-06-fm-reduce3`; the
  hashes of the twenty-eight zips and of every parquet are in its records.
  1,362,500 loans, 12,500 per origination quarter from 1999Q1 to 2026Q1. The
  cohort axis is the origination quarter encoded in the loan identifier
  (EXP-003: the axis holds; median first-payment lag three months in every
  cohort, re-dated loans 0.52% of the book and excluded). Half-year cohorts
  `YYYYH1`, `YYYYH2`, each the union of its two quarterly cohorts. The last
  scored cohort is 2023H2, the newest whole half-year whose twenty-four-month
  window has closed by the performance cutoff of 2026-03; 2024H1 is partial
  (7,443 of 24,959 admitted loans mature) and is not scored.

- **Label.** ADR-0006: ninety days past due, or REO, or a termination by
  third-party sale, short sale or REO disposition, within twenty-four months
  of the first payment month, with the months under a borrower assistance
  plan or a declared disaster hardship set aside, built by
  `outoftime.performance_label` from the reduced slice's
  `first_bad_age_outside_relief`. Immature and censored loans are dropped,
  never labelled non-default. Two other readings of the same scores are made
  in every run and neither is a headline: the *sensitivity* reading, the
  same event with relief months counted (`first_bad_age`), and the *horizon
  check*, the twelve-month label on annual cohorts. Both are readings of the
  scores the primary label's builds produce; nothing is refitted under them.
  The horizon check is discrimination only — a twelve-month default is a
  twenty-four-month default by construction, so a twenty-four-month
  probability ranks twelve-month outcomes and does not price them.

- **The label's definition along the axis.** The assistance and disaster
  flags exist from January 2014. Before that month a relief month cannot be
  set aside because nothing marks it, so the primary label counts a
  ninety-day month under the modification programmes of 2009 to 2013 as a
  default and a ninety-day month under a plan in 2019 as none. The definition
  is uniform within each regime and changes at one month of the performance
  calendar, for every model alike. Its size is measured, not assumed. On the
  training side the pools of 2002H2 through 2012H2 close before 2014 and the
  two readings coincide on them; 2014H2's pool differs by one default,
  2016H2's by 17 and 2018H2's by 130 of 10,586, so no fitted model is trained
  on a label that is more than 1.2% mixed. On the scoring side the cohorts
  are partitioned by where their windows fall: *pre-flag*, windows closed
  before 2014-01, cohorts through 2011H1; *straddling*, 2011H2 to 2013H2,
  where the readings differ by at most six defaults a cohort; *flagged*,
  2014H1 onward, where the set-aside reading is uniform and the reported
  reading counts 1.1 to 10.3 times as many events — 929 against 146 on
  2018H2, 1,135 against 110 on 2019H1, 1,148 against 136 on 2019H2, 609
  against 111 on 2020H1. Every arm-level criterion is therefore reported
  three more ways, none a criterion: on the pre-flag cells alone, where the
  two readings are one; on the flagged cells alone, where the primary label
  is uniform; and under the sensitivity reading on every cell. The 2018H2 to
  2020H1 cells are read by H2 and H3 under the primary label as benign cells
  at 110 to 146 defaults; under the sensitivity reading they are the hump,
  and a model's level there under that reading is a measurement of the
  reporting convention, carried on the sensitivity table and in the
  reliability figure below and entering no criterion. Kill criterion 4 says
  what a disagreement between the scopes does to a verdict.

- **Seasoned acquisitions.** A loan's servicing record begins when Freddie
  Mac acquires it, and for some loans that is months or years after the
  first payment. A ninety-day month before the first observed month is not on
  record, so a loan first observed late carries an unknown label over the
  months it was not watched, and labelling it from the months it was is the
  same error as labelling an immature loan from its early months. The first
  ninety-day month on the book falls at age 3 on hundreds of loans and
  earlier on two, so a loan first observed at or before age 3 misses no
  event that this label reads. The rule, `MAX_FIRST_OBSERVED_AGE = 3` in the
  label module: a loan whose first performance record is later than age 3,
  or whose record has a gap, is excluded from the book, counted per cohort,
  and never labelled. That is 25,315 loans, 1.9% of the admitted book, at
  9.7% of 1999H1, 6.7% of 2007H1 and under 4% of every cohort from 2008;
  their observed default rate is 0.73% against 1.10% on the loans kept,
  which is what missed events look like. The 30,262 labelled loans first
  observed at ages 2 and 3 are kept and default at 1.36%. Both counts, per
  cohort, are in the build run's summary.

- **Maturity at the cutoff.** A cohort is scored only if every admitted loan
  in it has a window closed by the performance cutoff, and it enters a
  criterion only if at least 95% of those loans carry a label after
  censoring and the rules above. Every half-year through 2023H2 has every
  admitted loan mature and at least 99.5% labelled; 2024H1 has 30% mature
  and is out.

- **The clock and the gap.** The label window runs from the first payment
  month; the builder cuts pools on whole origination quarters and dates a
  loan by the first day of its quarter. A loan's twenty-four-month window has
  closed at the as-of date `T` when its first payment month is at or before
  `T − 24 months`, and every non-re-dated loan's first payment falls within
  five months of its quarter opening (`LATE_FIRST_PAYMENT_MONTHS = 6`). A
  training quarter is therefore admitted only when its whole admitted
  population satisfies that: on the quarter axis the newest training quarter
  is the one ending **twenty-seven months** before `T`. This is the tightest
  value that is a quarter end for December as-of dates and under which no
  training loan's window is open at `T`; a twenty-four-month gap on the
  quarter axis admits the last quarter whole, and with a median lag of three
  months most of that quarter's windows are still open at `T`. The build run
  records, for every build, the count of training loans whose window is open
  at `T` (zero, or the build is refused) and the count of blind-gap loans the
  per-loan rule would have admitted (the cost of cutting on whole quarters).
  `vintage.LABEL_LAG_MONTHS` is 27 on this book and the check in
  `vintage.builds` that the label's window equals the lag becomes the check
  that the lag covers the window plus the admitted first-payment lag; the
  leakage assertion is unchanged and runs against the quarter dates of every
  build it emits.

- **Split.** `outoftime.vintage.builds`, every build through
  `splits.temporal_split` and `assert_no_leakage`. Nine as-of dates, 31
  December of every even year from 2002 to 2018: builds `2002H2` … `2018H2`.
  Two years apart because the trajectory, not the replication, is what this
  book is for: a build at `T` scores every half-year from the one after `T`
  through 2023H2, so the oldest build has 42 cohorts and the youngest 10 —
  234 cells on the expanding arm. December rather than June because the
  builder's month arithmetic clamps to the end of a short month, and only
  December as-of dates put a 27-month horizon on a quarter end. 2001H2 is not
  a build: its pool holds three quarters and under 37,000 labelled rows,
  below the context cap, and a foundation model there would see a whole pool
  where every other build sees a sample. The rows originated in the blind
  gap `(T − 27m, T]` are neither trained on nor scored — nine quarters,
  112,500 loans per build; they are the outcomes a study that trains up to
  `T` gives itself.

- **What the split cannot check.** The sample carries one loan per row and no
  borrower key. The entity check of `temporal_split` runs on nothing, and a
  borrower with a 2004 loan and a 2012 refinance appears in both windows. The
  pre-HARP identifier links a relief refinance to the loan it replaced; the
  build run counts, per build, the scored loans whose pre-HARP identifier
  names a training loan, as a lower bound on that exposure. It applies to
  every model alike and favours none.

- **Training arms.** Expanding, 1999Q1 to `T − 27m`, the primary. Pools of
  79,532 to 856,817 labelled rows, 950 to 10,586 defaults, at 0.96% to
  1.75%. Rolling, the last **eight** quarters ending at `T − 27m`, the
  robustness arm: the customary width, and on this book it is a rolling
  window, because the sample is flat at 12,500 loans a quarter — eight
  quarters hold 55% of the expanding pool at 2004H2 and 11% at 2018H2, and
  move the mean training row by 3.5 to 31.5 quarters. Four quarters, the
  Lending Club width, would hold under 50,000 labelled rows at every build:
  the seed would be inert on the whole arm and the arm contrast would be a
  contrast of pools rather than of samples. The rolling arm starts at 2004H2,
  the first build with eight training quarters; eight builds, 192 cells,
  pools of 95,582 to 99,160 rows at 0.45% to 4.48% — the last is 2010H2-R,
  whose window is the 2006Q4–2008Q3 vintages and whose scored cohorts sit at
  a tenth of its rate. For a foundation model the arm and the context sample
  are one knob; every pool on either arm exceeds the cap, so the arm decides
  what the context is a sample *of*.

- **Scoring rows.** Whole cohorts. Every labelled loan of a half-year cohort
  is scored, 23,162 to 24,929 per cohort, and `rows_per_quarter` is set at
  the cohort size so the per-quarter sample is the quarter. Cohort-to-cohort
  movement is then the model and the book, never a draw. Scored rows are
  never cut to fit a budget: the floors below are default counts and a
  smaller sample fails them.

- **Floors.** A cell enters a criterion only if its cohort holds at least
  5,000 labelled loans and 100 defaults under the primary label, the floors
  of EXP-001 and EXP-003. Six half-years miss — 2003H1, 2013H1, 2014H2,
  2015H1, 2020H2, 2021H1, at 71 to 99 defaults — so 38 of the 234 expanding
  cells and 32 of the 192 rolling cells are scored, reported on every figure
  with their interval, and pooled into nothing. The sensitivity reading and
  the horizon check are read on the criterion cells of the primary label,
  whatever their own counts; under the twelve-month label the annual cohorts
  2003, 2013 to 2016, 2020 and 2021 sit under the floor and the horizon check
  has that hole in it.

- **Models and tuning budget.** As EXP-002 as amended: scorecard (monotonic
  WOE binning, IV ≥ 0.02 screen, at most twenty characteristics, missing bins
  under a hundred rows at WOE zero, logistic regression); LightGBM on the
  full pool, tuned on the thirty-six-point grid with the early-stopping set
  sized by row share at the end of the pool, refitted on every labelled row
  at the chosen round count, `deterministic` and `force_row_wise` set,
  `feature_pre_filter` off; LightGBM on the same 50,000-row context the
  foundation models read, inheriting its build's hyperparameters and
  re-choosing only the round count — on this book the inherited point was
  chosen on a pool up to 17 times the control's, and every verdict against
  the control carries that asymmetry as on Lending Club; TabPFN-3 and TabICLv2
  at defaults, no fine-tuning, both at the shipped `softmax_temperature = 0.9`
  and at 1.0. The foundation models get no tuning; the asymmetry is stated
  wherever a comparison is reported. Binning and tuning are refitted inside
  every build on its training rows only.

- **Features.** The origination columns of `freddie_mac.py` less the two
  identifiers, the two calendar dates, `postal_code` (geography stays at the
  state) and `rate`, which is the calendar on a book whose note rates fell
  from 8% to 3.5% across the axis and which the value rule below would clip
  to nothing; the spread over the month's market rate would be knowable at
  origination and needs a series the dataset does not carry, so it is the
  ablation a reviewer may ask for and not part of this experiment. Sentinels
  read as missing (`SENTINELS`). The three gates of EXP-002's late amendment
  run on the whole book before any model is fitted — redundancy, coverage by
  onset, and uniform coverage by value — with the value rule made symmetric,
  because on a twenty-five-year axis a level can date a loan by leaving as
  well as by arriving. The rule, against **1999Q1** as the first cohort and
  **2023H2** as the last: a column constant on the first cohort is out; a
  level absent from the first cohort and present on more than a twentieth of
  the book is out, and so is a level present on the first cohort, absent from
  the last, and carried by more than a twentieth of the book; a numeric range
  is clipped to the range the first and the last cohort share; missingness is
  a level for the onset test, is exempt from the offset test, and removes a
  column when its share differs between the first and the last cohort by more
  than a twentieth of the cohort. Late and departed levels under the floor
  are left alone. What the rule is expected to remove on this book, each to
  be measured by the feature run: `vantage_score`, empty on every loan;
  `amortization_type` and `interest_only`, constant; `valuation_method`, a
  sentinel until 2017 and populated after; `special_eligibility_program`,
  blank until 2013; `harp`, whose one level exists from 2009 to 2019 and
  marks six loans in a hundred; `channel`, whose unspecified level marks
  half of every cohort through 2007 and none after 2008; `seller`, whose
  levels enter and leave with the market; `msa`, missing on a third to a
  half of every cohort before 2005 and on a tenth after, with codes redefined
  in 2003. `dti` above 50 is clipped to 50 and `upb` to the first cohort's
  ceiling. HARP loans stay in the book: they carry half the defaults of the
  2009H2 to 2013H2 cohorts and removing them would put ten more half-years
  under the floor. Their debt-to-income ratio is missing, because the
  programme did not collect it, so from 2009 to 2018 the missing level of
  `dti` is the HARP programme — a product every model built before 2009
  meets out of time, and the one carrier this rule knowingly leaves in; the
  ablation with `harp` kept and missing `dti` imputed at the first cohort's
  median is a reviewer's run. The feature run measures every drop and every
  share on the book, its output is the matrix, and the matrix is appended to
  the log before the falsifying run. A matrix is not read off this
  paragraph.

- **Metrics.** As EXP-002: AUC with a DeLong interval, Gini, KS; Brier with
  its Murphy decomposition; calibration in the large as observed over
  expected with a binomial interval; Cox intercept and slope; a ten-bin
  quantile reliability curve; PSI on ten bins fixed at the reference deciles
  against the Yurdakul critical value at α = 0.05, which at 24,000 scored
  rows against a 50,000-row reference sits near 0.0015 and which every real
  movement of the book crosses — the value is reported as the statement that
  a movement is real, and the hypothesis is one of magnitude. Age is counted
  in **half-years** from the as-of date: the first scored cohort is age 1,
  the last age 42. On a benign cohort at 110 to 150 defaults the DeLong
  standard error of an AUC near 0.75 is about 0.025; on the crisis cohorts at
  807 to 1,557 defaults about 0.009; on the 2022–2023 cohorts at 291 to 381
  about 0.015. A trajectory on this book is read at that precision, and the
  third kill criterion says what happens if it does not resolve.

- **The two readings of every criterion, fixed here.** Every arm-level
  statistic is computed and reported four ways, and the one the criterion
  reads is named before any number exists:
  - *H1's identification.* The slope of AUC on age with one intercept per
    build — the calendar slope net of build — is the criterion's statistic.
    The same least squares with one intercept per cohort — age at fixed
    calendar — is reported beside it. Neither is free of the other's
    confound. The weights are stated now: with one intercept per build,
    2002H2-E carries 31% of the slope and the four oldest builds 85%; with
    one intercept per cohort, each of the eight cohorts scored by all nine
    builds carries 7.2% and the three cohorts scored by one build carry
    nothing. Where the two disagree in sign on a pair, H1 supports at most
    the weaker claim and the text says both.
  - *H3's reference.* PSI against the build's own training reference — the
    training rows for a fitted model, the context draw for a foundation
    model — is the criterion's statistic. PSI against the same model's scores
    on the build's first scored cohort, bins fixed at that cohort's deciles,
    the first cohort's own cells left out, is reported beside it: every
    model's reference is then out of sample alike.
  - *The pooling.* The mean over criterion cells of the arm, paired by cell,
    is the criterion's pooling; on this grid it gives 2002H2-E 36 cells of
    196 and the three oldest builds half. The mean over builds with every
    build weighted alike is reported beside it, and where the two disagree in
    sign the difference is not read as a property of the arm.
  - *The temperature.* H2's level and slope are read at 0.9 as the primary
    reading, the object under study being the model as a risk team would
    adopt it; the same statistics at 1.0 are on every table and figure that
    carries them, from the same rows, and a verdict that differs between the
    two settings is reported as differing and not resolved by choosing one.
    Rank statistics do not see the temperature — exactly for TabICL, to the
    fourth decimal for TabPFN on one device — and H1 and H3 are read once.

- **The noise floor.** The cohort-blocked bootstrap of EXP-002's first
  amendment: resample the scored rows within each cohort, recompute every
  model's metric on every build from the same resample, take the 95% interval
  of the pooled paired statistic over 200 resamples, the context seed drawn
  with the resample, and record every interval a verdict rests on under the
  primary seed and the two check seeds. A star that does not survive every
  seed is reported as holding zero at the margin. "Beyond the interval" below
  means outside that interval. A cohort enters every build that scores it, so
  the 234 cells of the expanding arm hold 1,027,850 distinct rows, not
  5,754,654.

- **Seeds.** Three context seeds, `vintage.CONTEXT_SEEDS = (20260911,
  20260912, 20260913)`, read by GBM-50k and both foundation models, so that a
  difference between two models is never a difference between two draws. The
  scorecard and the full-pool GBM are deterministic given the build. Every
  pool exceeds the cap on both arms, so no seed is inert anywhere on this
  grid.

- **The accelerator, and the rule that sizes the grid.** The foundation
  models' forward passes run on a rented CUDA device; the classical side runs
  on the development machine. A one-hour timing probe on that device, on the
  Lending Club 2015H1-E bundle at a 50,000-row context, records for each
  model the seconds per scored row including context set-up, `s_I` for
  TabICL and `s_P` for TabPFN. The grid's projected wall is then computed by
  `scripts/fm_grid_budget.py` from those two numbers and the row counts of
  this file, with a 25% margin:

      rows per pass, expanding: 5,754,654 scored + 450,000 context = 6,204,654
      rows per pass, rolling:   4,726,804 scored + 400,000 context = 5,126,804
      W_full    = 1.25 × R_E × (3 s_I + 6 s_P)      TabICL 3 seeds at 0.9; TabPFN 3 seeds × 2 temperatures
      W_derived = 1.25 × R_E × (3 s_I + 3 s_P)      TabPFN 1.0 derived from 0.9
      W_R       = 1.25 × R_R × (3 s_I + 3 s_P)      rolling arm, TabPFN 1.0 derived

  The rule, fixed before `s_I` and `s_P` exist:

  1. If `W_full ≤ 30 h`, TabPFN is scored at both temperatures on the
     expanding arm.
  2. Else, if `W_derived ≤ 30 h`, TabPFN's rows at 1.0 are derived from its
     rows at 0.9 by the logit scale, on the same device, with the error of
     that derivation measured on the Lending Club grid at or under 8.4 × 10⁻⁴
     per cell recorded beside every derived statistic.
  3. Else the expanding arm runs whole under rule 2 over as many rental
     hours as it takes. No seed, row, build or cohort is cut; the only
     quantity the budget moves is money.
  4. The rolling arm's foundation-model cells run on the same device if the
     wall of the chosen expanding configuration plus `W_R` is at or under
     45 h; otherwise the rolling arm is classical and GBM-50k only, and H4
     is not tested on this book. TabPFN at 1.0 is derived on the rolling arm
     in every case.

  TabICL's rows at 1.0 are derived from its rows at 0.9 by the exact scale on
  both arms, checked against the falsifying run's scored rows to 10⁻⁶ before
  any statistic is read from them and refused if the check fails on any row.
  The probe's two numbers, the arithmetic and the tier it selects are the
  first foundation-model entry in the log. Every timing on the device is
  taken twice and the disagreement recorded.

- **The terms of use.** The dataset's terms forbid distributing the dataset
  or any Derived Product to third parties and permit publishing research
  results that cannot be used to recreate any part of it. Row-level material
  — the reduced parquet, the node bundles, the scored probabilities of any
  loan — stays on the machines under the owner's sole control and enters no
  repository; the paths that hold it are ignored by git before the first run.
  The forward passes on a rented instance are conditional on the reading of
  the terms recorded under `docs/` before any bundle is packed; if that
  reading does not permit a rented device, the foundation-model side waits
  for one it does permit, and the classical grid runs meanwhile. What is
  published: the code, every manifest and hash, the per-cell aggregates
  (metrics with intervals, reliability-curve bins, PSI bins), the poolings,
  the figures, and the build definitions. Freddie Mac is attributed in the
  paper and the README.

*Note of 2026-09-12, before any model is fitted on this book.* Age is stored
and every slope is computed in **quarters** from the build's quarter, as on
Lending Club: a half-year cohort sits at an odd quarter age, the first scored
cohort at 1 and the last at 43. The age in half-years named above is that
number halved and rounded up. Every criterion reads a difference of slopes
against its own interval, so the unit rescales both alike and moves no
verdict; slopes quoted from this book say "per quarter", as the pooling
scripts write them.

*Note of 2026-09-13, before any model is fitted on this book.* The rule
above governs the matrix wherever this paragraph's expectations disagree
with it, and on this book it disagrees on two columns. Measured on the
reduced book against 1999Q1 and 2023H2, and recorded by the feature run:
`dti` is missing — the 999 sentinel — on 5.6% of the 1999Q1 cohort, 12,415
loans once re-dated loans are excluded, and on no loan of 2023H2, a
difference over the twentieth, so the clause on missing share removes it.
`super_conforming` is N on every loan of 1999Q1, Y on 250 of the 24,968
loans of 2023H2 and on 1.8% of the book, so the clause on a column constant
in the first cohort removes it; the sentence leaving late levels under the
floor alone does not reach it, because that sentence is about a level of a
column that already varies on the first cohort, and a column with one level
there has nothing to keep but the level that arrives later, which is the
calendar with certainty — the super-conforming limit did not exist before
2008. EXP-002's rule removed `initial_list_status` and the five back-filled
counts on the same ground with their late mass under the bin-size floor.
Both columns are out, and the matrix is fourteen columns: `borrowers`,
`cltv`, `fico`, `first_time_homebuyer`, `ltv`, `mi_pct`, `occupancy`,
`prepayment_penalty`, `property_type`, `purpose`, `state`, `term`, `units`,
`upb`, every numeric one clipped to the range the two cohorts share.

The expectation that `dti` stays was wrong about the first cohort, not
about the rule. The missing level was taken to sit at about the same share
at both ends of the axis, and it does not: 4% of the 1999 originations,
2% to 3% of every year from 2000 to 2008, 11% to 35% of every cohort from
2009 to 2014, none from 2019. What the clause removes is therefore the
carrier the paragraph knowingly left in. A build of 2004 or earlier meets a
missing `dti` on two or three loans in a hundred of its pool, as an
incomplete file of the early years, and would apply that bin to a third of
the loans of 2012, which are a product; with the column out, every model
scores a HARP loan on the characteristics it shares with the loans around
it, which is the out-of-time event this book is for. The floor is not moved
for an overshoot of six tenths of a point, and the reference is not moved
from the quarter to the half-year to see whether the share falls under it:
on Lending Club the first cohort moved one quarter for a product launch
dated before the rule was measured, and nothing dates this boundary.

What the column costs is measured rather than argued. The ablation reported
beside every verdict of this experiment is the fifteen-column matrix — the
fourteen and `dti`, its missing values a level and its range clipped to 50
as the paragraph says — with everything else identical: the scorecard, the
GBM and GBM-50k on every build of both arms; every model on the cells of
the falsifying run, both temperatures, the same context seed. Reported from
it: per model, the paired difference in AUC and Brier between the two
matrices on the falsifying cells, with the bootstrap interval the interval
scripts give on the same rows; for the three fitted models, every pooling of
H1 to H3 on both matrices with its sign. If on the falsifying cells the gain
from `dti` differs between a foundation model and GBM-50k beyond that
interval, the foundation-model grid is run on the fifteen columns as well
and every verdict is reported on both matrices, the fourteen-column reading
being the criterion's. The ablation with `harp` kept and missing `dti`
imputed at the first cohort's median remains a reviewer's run. The
scorecard's 0.70 on 2005H1 in the falsifying run stands as the threshold
for a broken matrix; the fifteen-column cells say what the third
characteristic of a mortgage model adds on this book, for each model class
alike.

*Note of 2026-09-13, later, before any model is fitted on this book.* Four
things the text above says wrongly or leaves unmeasured, each read against
from here.

*The loan amount is read against the year's conforming loan limit.* The
rate is out because it is the calendar: 93.1% of its variance lies between
cells of first payment month and term (`fm-features`, `gates.json`). The
same statistic on the kept numeric columns, measured on the labelled book
by the cold audit of the feature run: `upb` 0.25, `ltv` 0.12, `cltv` 0.12,
`mi_pct` 0.10, `fico` 0.10. The loan amount sits nearer the rate than the
others because it is a nominal dollar amount on a twenty-five-year axis:
its median rose from 105,000 in 1999 to 275,000 in 2023, and the clip at
the first cohort's ceiling of 461,000, which pins 4.0% of the book, pins
13% to 18% of every cohort from 2020 — the cells the 2022 rise is read on.
Held out on the labelled book, a booster given `upb` alone recovers the
origination year at R² 0.19 (`fico` 0.05, `ltv` 0.04, every other column
under 0.04), given the fourteen columns at 0.42, and given the thirteen
without a loan amount at 0.24.

From here the matrix carries `upb_to_limit`, the original balance divided
by the baseline one-unit conforming loan limit in force in the loan's
origination year, in place of `upb`. The limit is a statutory ceiling, set
for each calendar year before it begins and indexed by law to the national
average house price — the Federal Housing Finance Board's survey through
2008, the FHFA index under HERA since, and held at 417,000 from 2006 to
2016 because the statute does not let it fall — published as one number a
year by OFHEO and then FHFA; `fm_features.CONFORMING_LIMIT` holds the
twenty-eight values from 1999 to 2026 with their sources. Every loan in
this book was written under it: the charter forbids the purchase of a loan
above it outside the high-cost areas and the multi-unit schedule, so the
ratio is a quantity the underwriting read, not a series fitted afterwards.
The objection to the rate's spread was a weekly market series the dataset
does not carry; a table of statutory annual values is not that series and
does not raise that objection. Measured on the reduced book under the same
computation and recorded by the amended feature run before anything is
fitted, so that the record and not this paragraph is what is quoted: the
ratio has 0.07 of its variance between month-and-term cells, under every
other numeric column; alone it recovers the year at R² 0.03, and the
fourteen columns with it at 0.27, within 0.02 of the matrix with no loan
amount at all; its range shared by 1999Q1 and 2023H2 is the first cohort's
own, 14,000/240,000 to 461,000/240,000, and the clip pins 0.09% of the
book; its median by origination year lies between 0.38 and 0.52 with no
trend. What the ratio does not remove is house prices: the limit tracks
the national average and stops in a downturn, so the crisis and the
recovery are in the column as they are in `ltv`. It is a deflator for
every loan alike — the multi-unit schedule and the 150% limits of Alaska,
Hawaii, Guam and the Virgin Islands are not applied, `units` and `state`
being columns of their own. The value rule measures the derived column as
it measures every kept numeric one, `value_report` refuses a shared range
other than the declared one, `assert_matrix_clean` refuses a matrix that
holds `upb` unless the ablation below is declared, and the feature run
records the month-and-term statistic for every kept numeric column and
for both forms of the amount, so the record shows where each sits against
the rate. This is the treatment `features.py` gives the credit-line date
on Lending Club: a calendar-indexed transform that leaves the
characteristic and takes the calendar out. Lending Club's `loan_amnt`
stayed nominal on an eight-year axis with its cap clipped, and the clip
there pinned 13% of the book and no cohort's fifth. What the columns still
recover of the year without a loan amount — the score, the leverage, the
states, the purposes — is the population, and it is what the study
measures.

*The nominal amount is the second ablation.* Reported beside every verdict
on the terms of the fifteen-column ablation: `upb` in nominal dollars
clipped to 19,000 to 461,000 in place of the ratio, `ablation =
"upb_nominal"`, everything else identical — the scorecard, the GBM and
GBM-50k on every build of both arms; every model on the cells of the
falsifying run, both temperatures, the same context seed. Reported from
it: per model, the paired difference in AUC and Brier between the two
matrices on the falsifying cells with the bootstrap interval; for the
three fitted models, every pooling of H1 to H3 on both matrices with its
sign, which says how much of a fitted model's trajectory on this book was
the dollar. The trigger is the one the fifteen-column ablation carries: if
on the falsifying cells the difference between matrices differs between a
foundation model and GBM-50k beyond the interval, the foundation-model
grid runs on the nominal matrix as well and every verdict is reported on
both, the ratio's reading being the criterion's. The falsifying cells sit
one to three half-years from a pool whose limit moved by a quarter, so
they test whether a model reads the two forms alike at age zero and
nothing more; what the dollar does at age forty is read on the fitted
models. The fifteen-column ablation is from here the fourteen with the
ratio, and `dti`.

*A gap in the record counts inside the window only.* The rule under
"Seasoned acquisitions" excludes a loan whose record misses a month
anywhere, and the record runs to the cutoff: of the gapped loans on the
labelled book, three in four first miss a month after age 24, so a loan in
a 2004H2 pool can be excluded for a month missing in 2015. The count is
negligible — 44 such loans in the pool quarters of 2004H2-E, 166 in
2018H2-E's — but it selects training rows on an event after `T`, and no
training row is selected on one. From here a gap is a month missing
between the loan's first record and the close of its twenty-four-month
window, read from the monthly slice the reducer keeps for that window and
from nothing later; a gap after the window is not read, as no other event
after the window is. The three readings share the one exclusion, so the
twelve-month check is read on the loans the primary label reads. The
seasoned-acquisition rule is unchanged: a first record later than age 3
is inside the window by construction.

*Two counts and one statement above are corrected.* The twelve-month label
on annual cohorts sits under the hundred-default floor on 2018 as well, at
98 defaults on 48,969 labelled loans, so the horizon check's hole is 2003,
2013 to 2016, 2018, 2020 and 2021; 2017 and 2019 clear it at 104 and 101
(`fm-vintage-builds`, `cells.csv`). The note of 2026-09-12 puts the last
scored cohort at age 43 in quarters; a build of 2002H2 scores 2023H2 at
83, and every slope is on that axis. Every pool, cell and exclusion count
the Setting states before the build run is superseded by the run's, as the
Log says; the three runs of 2026-09-13 are themselves re-recorded under
this note, with the matrix and the gap rule fixed here, before the
falsifying run, and the Log carries the new counts under their own date.
No build, cell or floor verdict moves; the labelled counts move by the
gapped loans the window rule now labels.

*Note of 2026-09-14, before any foundation-model statistic of this book is
read.* Six sentences above admit two readings each, and one solver of the
metrics module was replaced after the grid was scored. The reading each
sentence is given from here is fixed before the number it governs exists.
Where the second reading is defensible it is reported beside the first and
enters no criterion.

*H5's contexts are builds, ranked by their pools.* The ranges the
hypothesis quotes, 0.96% to 1.75% on the expanding arm and 0.45% to 4.48%
on the rolling arm, are the pool rates of `fm-vintage-builds2`: 2006H2-E at
0.957% and 2010H2-E at 1.757%, 2018H2-R at 0.450% and 2010H2-R at 4.482%. A
context of H5 is therefore a build's pool as the three draws sample it.
Those four builds, two per arm, are the criterion's contexts, fixed by the
rate the build run recorded before any model was fitted. On each the
statistic is observed over expected on the draw's own 50,000 rows, mixed
over the draws as the bootstrap draws them. The mean realised rate of a
build's three draws is printed beside its pool's rate. On the rolling arm
2016H2-R's pool sits 0.03 points above 2018H2-R's, inside what three draws
of 50,000 rows can move; where the draws rank an arm's ends otherwise, the
difference under that ranking is reported beside the criterion's.

*H5's seed is drawn once per resample for both builds.* The context seed is
drawn jointly, draw k of the higher-rate build with draw k of the lower,
for every model at once, as the arm pooling draws it across builds and
models. The interval then carries the same two sources every other
criterion's carries. No second reading is needed. The per-cell table holds
every draw of every context on its own, each with its binomial interval
and its bootstrap interval, which is the per-draw reading Lending Club's
level was read on.

*The ablation trigger reads a difference of differences against its own
interval.* "The gain from `dti` differs between a foundation model and
GBM-50k beyond that interval" is read as every criterion of this file is
read. The statistic is (model on the ablation's matrix minus model on the
primary) minus (GBM-50k on the ablation's minus GBM-50k on the primary),
paired on identical rows, computed on the same resample of the same cells
for both matrices and both models, and read against the bootstrap interval
of that quantity. The per-model gains with their intervals are beside it.
It is read on the falsifying run's three cohorts and its one context draw,
so the interval is conditional on that draw, as the falsifying run's other
intervals are. Either metric fires it: the trigger holds for a foundation
model when its row on AUC or its row on Brier excludes zero. The row that
fired is named. Both rows are on the table for both ablations. The trigger
fires on the primary bootstrap seed. A star a check seed loses
fires it too and is reported as fired at the margin, because what it buys
is a further reading, and the fourteen-column matrix stays the criterion's
whatever it shows. Eight such rows exist, two per ablation for each
foundation model on each metric, and a star on one of eight is one star.

*Rule 2's error is the scale the derivation misses, recorded and not
bounded at the Lending Club figure.* The quantity is |b − 1| per cell, b
the least-squares slope of the scored logit on the derived logit over the
cell's rows: the derivation assumes the temperature is a scale on the
logit, and b is the scale it gets wrong. The level on the derived rows
against the scored ones is measured on every checked cell and reported:
mean probability, observed over expected, Cox slope. A gap on the
probability is reported and not bounded, since at a one-percent rate it
reads small whatever the scale error. The 8.4 × 10⁻⁴ is what |b − 1|
measured on the 297 expanding-arm cells of the Lending Club grid, on one
device, by a script that is not a recorded run. It is the scale a reader
should expect and is not a number of this experiment. What is recorded is
the same measurement on this book. Every expanding-arm build holds TabPFN
scored at both temperatures on one device, so the error is measured cell
by cell on all nine and recorded before any rolling-arm row is derived. A
rolling-arm build's rows at 1.0 are then derived with the same-year
expanding-arm build as the check: its rows at 0.9 are derived by the
formula and compared with its rows at 1.0, and derive.json then carries,
for every derived cell, the error measured on that build's cells. Beside
every statistic read from derived rows: the worst and the mean |b − 1| over
the check's cells, and the count of cells above 8.4 × 10⁻⁴. What the check
does not cover is named beside them. The expanding contexts span 0.96% to
1.76% and the rolling ones 0.45% to 4.48%, so the carried error is measured
on contexts of a narrower range than the ones it is applied to, while the
scored cohorts of the check span the book's 0.29% to 6.39%. The derivation
is refused at one point only: a cell above 8.4 × 10⁻³, ten times the
Lending Club figure, where the scale error reaches one percent on the logit
and the derivation is no longer the one that figure describes. A refusal
leaves TabPFN at 1.0 unread on that rolling-arm build, and says so.
Nothing coarser replaces it. A cell between the two figures is derived and
named. The bound sits there for two reasons. A bound at the
Lending Club worst would refuse on the maximum over two and a half times as
many cells; and a scale error of one percent moves |Cox slope − 1| by a
hundredth, where the pooled intervals on it on the Lending Club falsifying
build were a tenth wide and wider.

*TabICL's check on the falsifying run's rows is the check the sentence
names.* The rows at 1.0 exist on 2004H2-E only. The sentence says those
rows. The check was made on them, 121,595 rows on each of three matrices,
worst 1.7 × 10⁻⁷ on the probability against 10⁻⁶. The sixteen other builds
carry the identity rather than a row comparison: the same library version
and checkpoint hash, the same source temperature draw for draw, the same
device, each refused by the script where it differs. derive.json of every
build names the build the checked cells belong to and lists every derived
cell as unchecked by row. That is what the sentence requires before a
statistic is read from those rows. One cohort of every build scored at 1.0
would close the gap by row for minutes of the device at the probe's rate;
it is the check a reviewer may ask for, and a reviewer's run.

*The Cox fit is by damped Newton from here, and a cell that does not
converge is not estimable.* The metrics module's fit took whole Newton
steps from (0, 1). On a cell whose scores sit far below its outcomes a
whole step overshoots to where every weight underflows and the information
is singular, and the fit raised. That happened on TabPFN's cells of 2007H2
to 2008H2 on 2006H2-E, nine at 0.9 and two at 1.0, the cells the Setting
expects every model to score at a fraction of their rate. No statistic of
theirs was read, and the raise would have stopped every pooling of the
crisis builds. The fit now halves a step until the log-likelihood does not
fall. Wherever whole steps rose to the maximum it takes the same steps, and
on the 1,683 Cox cells of the nine Lending Club grid poolings it returns
every value bit for bit (`db12783`). A fit that cannot finish returns NaN
with `converged` false and the steps taken, and raises nothing. The rule
for such a cell is fixed now. No cell of this book is one. The cell is not
estimable, and the per-cell table says so with the steps taken. In the
mean of |Cox slope − 1| it leaves the pairing for every model, in the point
estimate and in every resample alike, so that the pooling stays on
identical cells. The count of cells left out of the point estimate and the
largest number left out of any resample are printed beside the pooled
statistic and its interval. A pooling that reads NaN into an arm's mean is
not a recorded reading. H4's difference between arms is on the same
statistic and follows the same rule.

*Addition of 2026-09-14.* The bit-for-bit statement is of the cells' fits:
the per-cell tables of the nine poolings reproduce byte for byte. On a
resampled cell the first whole step can lower the likelihood where it did
not on the cell itself, and the damped fit then halves it; on 2016H2-E three
of 672 rows of `paired.csv` and five of 756 of `paired-seeds.csv`, every one
a Cox interval bound or standard error, differ from the recorded run by at
most 3 × 10⁻¹⁶, the point estimates and the stars unchanged; 2017H1-E
reproduces byte for byte.

*Two statements above are corrected, 2026-09-15.* The Yurdakul critical
value at 24,000 scored rows against a 50,000-row reference, ten bins and
α = 0.05, is 0.00104, not near 0.0015 (`psi_critical_value(24000, 50000,
10)` of `psi-inference`); every real movement of the book still crosses it.
The trigger's eight rows are the two foundation models at 0.9 on AUC and
Brier for each ablation. `ablation_intervals.py` counted the rows at 1.0 as
well until `9b84a0b`, and the recorded `summary.json` of both ablations
lists such rows among those excluding zero; they are outside the rule.

*Note of 2026-09-15, before any H4 statistic is read.* Seven things the text
above leaves open on H4, or says only for the hypotheses that already have a
number, each fixed here before H4's number exists. Where a second reading is
defensible it is reported beside the first and enters no criterion. Nothing
below changes a criterion.

*The kill on H4 fires unless the interval lies above zero.* H1 to H3 are
written "no worse than", and their kill is a star on the wrong side. H4 is
written "by more than", and its kill is the absence of a star on the right
side: "no larger for the TFMs than for GBM-50k, inside the interval" holds
whenever the interval of the foundation model's reduction minus the control's
holds zero, and kill criterion 2 says the same of any TFM-against-control
difference that lies inside its interval. The statistic is, per model, the
mean of |Cox slope − 1| over the criterion cells on the expanding arm minus
the same mean on the rolling arm; H4's row is that reduction for the
foundation model minus the control's, on the same resample. The row survives
when its interval lies above zero. It is killed when the interval holds zero,
and killed with a finding of its own when the interval lies below zero, since
the rolling window then brings the control nearer a slope of one by more than
it brings the foundation model; the reading names which of the two.

*H4 is read at 0.9, with the row at 1.0 beside it.* The temperature bullet of
the Setting names H2 and says H1 and H3 are read once; it does not name H4.
H4 is on the Cox slope, which the temperature moves: a scale on the logit
multiplies the slope, so |slope − 1| on either arm changes with the setting
and the reduction between arms can change sign. The rule EXP-002's amendment
of 2026-09-06 fixes for every calibration statistic therefore applies to
H4's: read at the shipped 0.9 as the criterion's, the object under study
being the model as a risk team would adopt it, and the context policy a knob
that team would turn at the setting the model shipped with; the same row at
1.0 on every table and figure, from the same rows; a verdict that differs
between the two settings reported as differing, with both intervals, and not
resolved by choosing one. The setting was fixed for the slope before any
rolling-arm cell existed on either book.

*The criterion cells of H4 are the 160 of the 192 that clear the floors.* The
hypothesis names the 192 cells the two arms share; the paragraph on floors
says a cell enters a criterion only if its cohort holds 5,000 labelled loans
and 100 defaults, and 32 of the rolling arm's 192 do not. The two arms at
one build date score the same cohorts, so the same 32 leave both arms, and H4
reads 160 cells on eight build dates, `cells.csv` of `fm-vintage-builds2`
saying which. The 32 are scored and on every figure. The pooling and the seed
check are every other criterion's: the mean over criterion cells paired by
cell, the cohorts held fixed, under the primary bootstrap seed and the two
check seeds. Beside it, entering no criterion: the mean over build dates with
every date weighted alike, each date on its own, the same pooling with the
cohorts resampled, each context draw held fixed, and the pre-flag and flagged
cells as two scopes, whose signs kill criterion 4 compares.

*A star that a check seed loses is the kill.* The noise floor says a star
that does not survive every seed is reported as holding zero at the margin,
and on H4 a row that holds zero is a row the kill reads. H4 therefore
survives only under all three seeds. A star under the primary seed lost under
a check seed is reported as killed at the margin, with the three intervals; a
star under a check seed alone is not a star, the criterion reading the
primary seed as the ablation trigger does. This is the rule H2 was read under
on Lending Club, where holding zero at the margin let a "no worse" hypothesis
stand; here it is the same rule on a hypothesis of the other polarity.

*A cell on which some model's Cox fit does not finish on either arm leaves
both arms for every model.* The rule of 2026-09-14 keeps a pooling on
identical cells. H4 compares one model's two arms and then two models'
reductions, so identical cells means the same cells in all four means; a cell
left out on one arm alone would put a cell difference inside a reduction,
which is what the rule exists to prevent. The count left out of the point
estimate and the largest left out of any resample are printed beside the row,
as for every other pooling.

*Draw k on the expanding arm is read beside draw k on the rolling arm.* One
context draw is chosen per resample for every model and every build of both
arms, as the arm pooling chooses it across builds and models and as H5
chooses it across its two contexts. The two draws are samples of different
pools under one seed, as draw k of two expanding builds already are; the
control reads the same draws on both arms as the foundation models, so a
difference between arms is never a difference between draws, and the interval
carries the two sources every other criterion's carries. The pooling with
each draw held fixed on both arms is beside it.

*The contrast beside H4 is what a recorded run measured.* Per build date the
row carries the share of the expanding pool the eight-quarter window holds,
read from the build records of the score runs. The shares and mean-row ages
the paragraph on training arms states for this book were summed from the
structure run's tables, as the Setting's counts were, and no run records them
as a contrast; they are superseded the way the counts are: an arm-contrast
run over the build record of this book, the share and the mean age of a
training row per arm with no model in it, is recorded before the H4 pooling,
and its numbers are the ones printed beside H4 and quoted for that paragraph.
Until it exists the row carries the share alone.

*Note of 2026-09-15, on the floors in the poolings, before any statistic
of the grid is pooled.* The Floors paragraph puts a cell under them by its
cohort's counts and says what becomes of it: scored, on every figure with
its interval, pooled into nothing. Three places the pooling scripts reach
are not settled by that sentence alone, and the reading of each is fixed
here.

*The nearest pooling is a window of age, and the floors take cells out of
it.* Beside the arm's pooling the scripts pool, per build, the three
cohorts nearest the build date — the cells the falsifying run scored on
2004H2-E, at ages 1, 3 and 5 quarters. That pooling enters no criterion.
Where one of the three is under the floors the pooling holds the other two
and reaches no further: 2003H1 on 2002H2-E, 2013H1 on 2012H2-E and
2012H2-R, 2015H1 on 2014H2-E and 2014H2-R. On those five builds it is two
cells and on the twelve others three, 24 cells on the expanding arm and 22
on the rolling. Taking instead the three youngest cohorts above the
floors would put the reading on 2012H2 at ages 3, 5 and 11 with two
under-floor half-years stepped over, and "nearest" would mean a different
age on each build. H4 is on the same footing: of the 192 cells the arms
share, the 160 above the floors are the criterion's, as the Floors
paragraph counts them.

*The first-cohort reference stays the first scored cohort.* H3's second
reading takes as its reference the model's scores on the build's first
scored cohort. On 2002H2-E that is 2003H1, on 2012H2-E and 2012H2-R
2013H1, on 2014H2-E and 2014H2-R 2015H1, each under the floors at 72 to 85
defaults. The reference stays there. The floors are counts of labelled
loans and defaults; a PSI reference is a score distribution read at its
deciles and reads no label, so the count that puts those cohorts under the
floors touches nothing the reference is used for, and every cohort of the
grid clears the row floor more than four times over. Nor do the floors
read the rows of the criterion's own reference, the training rows or the
context draw, which is held fixed in the same way. What the second
reading is for is a reference out of sample alike for every model and at
the same age on
every build. Moved to the next cohort above the floors it would sit at
age 3 on five builds and at age 1 on twelve, and the movement along the
vintage axis it measures would start from different places. The
reference cohort's own cells are left out as the sentence says, and on
those five builds the floors leave them out already; the mean over the
arm then runs over 190 of the 196 criterion cells on the expanding arm and
154 of the 160 on the rolling. A reading with the reference moved is not
reported beside this one: it differs by the deciles of one cohort on five
builds and discriminates nothing named here.

*H5 and the ablation trigger have no cell to leave out.* H5 is read on
context cells, fifty thousand rows drawn from a pool, and the Floors
sentence speaks of a cell's cohort; a context has none. At the pool rates
the note of 2026-09-14 quotes, 0.96% to 1.76% on the expanding arm and
0.45% to 4.48% on the rolling, a draw holds about 225 to 2,240 defaults in
expectation, above the floor on every build of either arm. The trigger
reads the falsifying run's three cohorts, at 247 to 405 defaults each.
Neither statistic pools a cohort, and no script of this experiment pools
one under the floors, the ablation's included.

*Note of 2026-09-17, after the grid's poolings, the in-sample reading and
the H4 pooling were read and audited.* Written after
[`experiments/2026-09-16-fm-between-arm-intervals`](../../experiments/2026-09-16-fm-between-arm-intervals),
[`experiments/2026-09-16-fm-grid-in-sample`](../../experiments/2026-09-16-fm-grid-in-sample)
and the arm poolings of both matrices were recorded, and after the cold
audit of all of them. Nothing below changes a hypothesis or a criterion. It
fixes readings the text leaves open, names a defect in the control that the
recorded runs carry, and names what remains to be computed before any
verdict of this file is quoted outside it.

*H4 is read under kill criterion 4 from two scopes.* Criterion 4
compares the 28 pre-flag cells and the 115 flagged cells; what it read on
this book, at arm scope and under the two scopes, and the recorded run's
summary string and its correction, are in the log's entry of 2026-09-19
"the verdicts the Setting stated, carried here"
([EXP-005-log.md](EXP-005-log.md)) (pointer of 2026-09-19). The
sensitivity reading the criterion names, the same pooling under the
reported label, has not been run and is recorded before the
verdict enters the log; on the pre-flag cells the two labels are one by
construction, so the sensitivity reading reproduces the primary reading's
pre-flag rows to the bit, and a run on which it does not is wrong. What
the grid shows about H4 without the control is on the table already: each
foundation model's own E − R, at 0.9 and at 1.0, the rows at 1.0 read on
derived rows with the error printed. That is the sentence this book
supports on H4. The rows this paragraph quoted when it was written, and
what it read from them, are in the log's entry of 2026-09-19
([EXP-005-log.md](EXP-005-log.md)) (pointer of 2026-09-19).

*Criterion 4 as written reads a sign and has no noise floor, and a
second reading is put beside it.* Under a true differential of zero, two
scoped rows are two readings of zero and disagree in sign about half the
time; on a hypothesis of H4's polarity "undetermined" and "killed inside
the interval" then say the same thing to the claim, and differ only in
whether the text may say there is no effect on this book or that the book
does not resolve one. From here two readings are computed beside every
criterion row's scoped signs, entering no criterion: the difference
between the pre-flag and flagged scopes on the same resample, with its
interval, which says whether the scopes disagree beyond it; and the
sensitivity reading on the flagged cells against the primary reading on
the same cells, the one contrast that holds the cells fixed and moves the
label alone. The scopes themselves cannot separate the label's reporting
regime from the calendar the pre-flag cells sit in — the 28 cells of H4's
pre-flag scope are 2005H1 to 2011H1 on the four oldest paired dates, the
crisis inside them — and a disagreement between scopes is attributed to
"the regime, label or calendar" until the same-cells reading says which.
The as-written reading stays the verdict's on every row of this book, H1
to H3 included, so that no row is judged under a rule changed after
another row fired it; where the second reading disagrees with the first,
the text says both and supports at most the weaker claim, as it does for
H1's two identifications. What the scoped rows and their difference read
on H4 is in the log's entry of 2026-09-19 (pointer of 2026-09-19).

*Note of 2026-09-19.* The same-cells reading has been recorded, in
[`experiments/2026-09-17-fm-between-arm-intervals-outcome-reported`](../../experiments/2026-09-17-fm-between-arm-intervals-outcome-reported),
and read, and the attribution of H4's scope disagreement is in the log's
entry of this date "what criterion 4's disagreement is carried by"
([EXP-005-log.md](EXP-005-log.md)).

*The control's early-stopping set shrinks along the expanding arm, and a
refit control is read beside it.* The rule that sizes the set takes the
fewest latest quarters holding a fifth of the rows, never more than four.
The cap was written for a book whose volume doubles each year; on this
book, flat at 12,500 loans a quarter, four quarters of a 50,000-row draw
from a 71-quarter pool are 5.6% of the draw. The control's early-stopping
rows on the expanding arm fall with every build date, while on the rolling
arm two quarters hold a quarter of the draw at every date. The round count
is the one thing the control re-chooses, and on the youngest expanding
builds it is chosen on few defaults. The asymmetry runs with the arm, so the
control's E − R mixes the window with the size of its stopping set, and a
row that reads "no different from the control" could be describing early
stopping. The stopping rows per date, the round counts and mean |slope − 1|
per draw on 2018H2-E and 2008H2-E, and the control's own E − R under each
draw held fixed, which this paragraph quoted when it was written, are in
the log's entry of 2026-09-19 (pointer of 2026-09-19). The recorded control
stays the criterion's: it is the control this file describes, every verdict against it is recorded as read, and
this note is dated after those verdicts were seen. Beside it, from here, a
refit control as a named reading: GBM-50k alone, the inherited point
unchanged, the early-stopping tail the fewest latest whole quarters
holding a fifth of the draw's rows and never more than half its quarters,
the four-quarter cap not applied. It is fitted on every build of both arms
of both books: on Lending Club, where the cap never binds, and on this
book's rolling arm, where two quarters already hold a quarter of the draw,
it must reproduce every recorded control fit bit for bit, and a refit
that does not is not recorded; on this book's expanding arm it differs. Read
from it: H4's row, and the expanding arm's rows of H1 and H3 against the
control. Where a row's standing differs between the two controls — a star
appearing or vanishing, the kill it reads — both are reported, the
recorded control's is the criterion's, and the text supports at most the
weaker claim. The point the control inherits differs between the arms at
all eight paired dates, as on the first book; the per-date table, the
rows above and the control's sensitivity points are recorded in
[`experiments/2026-09-17-fm-h4-sensitivity`](../../experiments/2026-09-17-fm-h4-sensitivity)
and printed beside H4; a control at one point on both arms, a control searched
on its own rows, and the full GBM with the cap lifted are reviewer's runs.

*H5's kill at 0.9 is the scale, and the reading at 1.0 is the test.* What
the criterion read on each arm is in the log's entry of 2026-09-19 (pointer
of 2026-09-19). The
sentence above that a kill "says the shortfall is a prior pulling the level toward
a fixed prevalence rather than a scale on the logit" is withdrawn, dated
after the result, because it is wrong by arithmetic: a scale of the logit
by 1/0.9 multiplies a small probability by about p^0.11, so a model
exactly calibrated at 1.0 reads an O/E at 0.9 that rises as prevalence
falls, near 1.4 at 4.5% and 1.8 at 0.45% before the spread of the scores
is accounted for, and fires the kill across a tenfold range. At 0.9 the
temperature cannot be told from a prior. The reading at 1.0 was fixed
beside the criterion before any number existed and is where the two
separate: a prior shows as a dependence of O/E on prevalence at 1.0, a
scale as none. The rows at 0.9 and at 1.0, and what this paragraph read
from them when it was written, are in the log's entry of 2026-09-19
(pointer of 2026-09-19). The demonstration that the as-written kill reads the scale is recorded beside the reading: the
classical models' in-sample O/E on the same context rows after the same
rescaling of the logit by 1/0.9 — calibrated by construction at 1.0, they
fire the kill at 0.9 or the arithmetic above is wrong.

*Kill criterion 3 is read before any slope of this book is quoted.* Its
statistic is the one written, per model and build, the DeLong interval
width of the median criterion cell against the range of that model's AUC
over the build's criterion cells; it fires when the width exceeds the
range for every model on a majority of the nine expanding builds, and the
consequence is the one written. It is computed from the recorded per-build
outputs and appended to the log before the arm's H1 rows are quoted
anywhere.

*What the Setting names and no run yet holds, each with its reading fixed
here.* The pre-flag and flagged scopes and the sensitivity reading of H1 to
H3 on the expanding arm, with the build-weighted pooling under each, which
the paragraph on the label's definition requires of every arm-level
criterion and which the arm poolings do not compute: the arm pooling is
recorded again with the scopes added and every existing row reproduced to
the bit, and once more under the reported label. The three scoped readings
of H2 — the cells of 2007H1 to 2009H2, the cells of 2022H1 to 2023H2, and
the ratio of O/E on 2022H2–2023H2 to that on 2020H1 and 2021H2 per model
and build — are rows of that same pooling. H4 on the nominal matrix, which
the trigger of 2026-09-14 requires of every verdict, is recorded as the
primary H4 was. The arm-contrast record the note of 2026-09-15 says is
recorded before the H4 pooling was not; it is recorded before the
superseding pooling, which reads it. The horizon check, discrimination
only on annual cohorts, is the last of these and enters no criterion. A
reading of this list may be described as not yet computed in this log and
nowhere else.

*A smoothing reading, fixed on 2026-09-17 before any pooled signed Cox
slope exists on either book.* SSRN 7431058 (its row in
[../landscape/prior-art.md](../landscape/prior-art.md), verified against the
full text on the same date) reports TabPFN-2.6 worse calibrated than a
logistic model on eight credit datasets on stratified random folds, and
attributes it to probabilities "smoothed
toward the mean" by the synthetic class priors of pretraining — stated at
§5.3, p. 18, and measured nowhere in the paper. The rows of this grid can
measure it. What the attribution is on the logit, which statistic reads it,
at which temperature, in which direction, against what scale, and what does
not fire it, are fixed here before the statistic is computed. It is a named
reading beside H2, reported and not tested, and it adds no criterion row:
the count of the Multiplicity paragraph stands.

*The attribution has two halves, and one of them is already read.*
Probabilities pulled toward a mean are, on the logit, a predicted logit less
spread than the outcomes warrant, and the Cox fit of the outcome on that
logit then needs a slope above one to stretch it back: smoothing toward the
mean is a Cox slope above one, whatever the mean is. The other half is the
mean itself. A prior pulling the level toward a fixed rate shows as an
observed-over-expected that depends on the context's realised rate, and that
is H5. H5 was read at 1.0 before this note was written, and the reading is
in the log (pointer of 2026-09-19). That reading is dated after its result and cannot be
pre-registered here; it is not. What this note fixes is the slope half,
which no run has pooled and no in-sample table carries.

*The statistic is the signed Cox slope, paired against the scorecard and
pooled as H2 pools.* Per foundation model, the mean over the criterion cells
of the expanding arm of its signed Cox slope minus the scorecard's on the
same cell, cohorts held fixed, the context seed drawn with the resample,
200 resamples; the model's own mean signed slope over the same cells, with
its interval read against one, is beside it, and so is the scorecard's. The
rolling arm is pooled the same way over its 160 criterion cells. Beside
both, entering no reading: the mean over builds with every build weighted
alike, each build on its own, the pre-flag and flagged scopes, the same
pooling with the cohorts resampled, and the sensitivity label. A cell on
which some model's Cox fit does not finish leaves the pairing for every
model, in the point estimate and in every resample, as the rule of
2026-09-14 has it; the signed slope is NaN on exactly the cells |slope − 1|
is NaN on, so the two statistics pair over the same cells and the count left
out is the one already printed. The scorecard rather than GBM-50k is the
pair because the paper's comparison is against a logistic model and H2 is
written against the scorecard; the difference against GBM-50k is on the
table as every pair is.

*The reading is at 1.0, and the row at 0.9 says whether the shipped setting
offsets it.* The temperature is a scale on the logit — exact for TabICL,
0.8996 measured for TabPFN on Lending Club — and the Cox slope at 0.9 is
0.9 times the slope at 1.0, since dividing the regressor by 0.9 multiplies
the coefficient by 0.9. The slope at 1.0 is the model's own dispersion, the
one the pretraining prior produced; the slope at 0.9 is that dispersion
after the shipped correction. A model whose logit is shrunk by exactly 0.9
reads 1.11 at 1.0 and one at 0.9, and the shipped setting is then the
correction, paid for in the level as Lending Club measured on 2026-09-06.
So 1.0 is where the mechanism is visible and 0.9 is where a reader sees
what the shipped knob does to it; the same row from the same rows, at both
settings, on every table. This inverts the roles the temperature bullet
gives the two settings for H2's criterion, and it is not a change to that
criterion: H2 reads the model as adopted, this reading reads a mechanism.
TabPFN's rows at 1.0 are scored on the expanding arm and derived on the
rolling, TabICL's derived on both, as the log of 2026-09-15 has it, and
every statistic read from derived rows is printed with the derivation's
error beside it: at most 2.5 × 10⁻³ on the Cox slope where measured, and the
carried error on the rolling arm is measured on contexts of a narrower range
than those it is applied to, as the note of 2026-09-14 says.

*The direction that supports the attribution, the one that contradicts it,
and what does not fire it.* The attribution is supported for a foundation
model when, at 1.0 on the expanding arm, its paired difference against the
scorecard lies above zero under every seed with a point estimate at or above
the minimum effect below, and its own mean slope lies above one beyond its
interval. Both are required: a positive difference between two models below
one is a model less over-dispersed than the scorecard, not a smoothed one.
It is contradicted when the difference lies below zero, or the model's own
slope below one beyond its interval — the foundation model's logit is then
more spread than the outcomes warrant, the opposite of smoothing. A
difference whose interval holds zero, or a star with a point estimate under
the minimum effect, reads neither way: the first says the book does not
resolve the mechanism at this size, the second that a direction exists under
the scale a reader could act on. What the statistic does not see, by
construction: a shift of every probability on the logit, since the slope is
invariant to a shift of its regressor, so the two-thirds level of the
shipped temperature and any prior on the level move no row; a stretch the
book does to every model alike, since the pairing subtracts it, which is why
out-of-time slopes above one for every model — the scorecard read 1.07 to
1.21 on Lending Club's falsifying build — are not smoothing; and a model
whose slope sits at one, or at the scorecard's, which reads zero.

*The minimum effect is 0.05 on the paired difference.* Three scales fix it.
The shipped temperature moves the slope by a factor of 0.9, which is 0.10 to
0.11 on a slope near one, and that factor was measured as the whole of the
foundation models' level on Lending Club; a smoothing worth a calibration
verdict is at least half of what one shipped knob was set to. The
derivation of rows at 1.0 misses the slope by at most 2.5 × 10⁻³ where it
was measured against scored rows, so 0.05 is twenty times the error carried
by the derived rows the reading is made on. And the pooled intervals on
slope statistics of this book at arm scope, H4's row among them, are of the
width the log's entry of 2026-09-17 on the sensitivity of H4's row reads
(pointer of 2026-09-19), so 0.05 sits at the resolution of the instrument: a star under it is a
direction the pooling can see and a size a risk team cannot. On the
synthetic check recorded before this note
([`experiments/2026-09-17-smoothing-dry-run`](../../experiments/2026-09-17-smoothing-dry-run)),
with both models exactly calibrated by construction and the repository's
own Cox fit and bootstrap, a shrink of
0.95 — a slope of 1.053, the threshold — reads +0.059 [+0.015, +0.106] at
36 cells of 12,000 loans at two percent under every seed, 2002H2-E's
criterion count at the book's default count per cell, and +0.060 [+0.044,
+0.077] at 196, and it does not separate on one cell of the floors, where
the Wald standard error of a slope at 94 defaults is 0.14, so a difference
of two such slopes is resolved only near 0.4 and above; a shrink of 0.85 separates everywhere the pooling reaches; the
calibrated model and the level shift read the same row to the digit, since
the slope does not see a shift; the common drift puts every model at 1.12
to 1.14 and the difference at +0.017 [−0.015, +0.054]; the stretched model
reads −0.125 [−0.166, −0.086]. The per-cell signed slopes therefore read
nothing on their own, and the reading is the pooling. The threshold is at
the edge of what 36 cells resolve, and a build on its own is read as a
build's row and not as the arm's.

*Seeds and the star.* The bootstrap is the criterion's: 200 resamples under
the primary seed 20260905 and the check seeds 20260906 and 20260907, the
context seed drawn with the resample from the three draws every seeded
model holds. A star under the primary seed that a check seed loses is
reported as holding zero at the margin, and does not support the
attribution; a star under a check seed alone is not a star. No seed is
added.

*The in-sample slope is a named reading of its own, and it is asymmetric.*
On every context cell of the grid — one per build, seed and temperature,
50,000 rows — the Cox slope of the model on its own context rows, with its
Wald interval per cell, and per arm the mean over the arm's builds with one
draw chosen per resample and the rows of each context resampled, as H5's
pooling draws. The four contexts H5 names are marked on the table. The
scorecard on its own pool reads slope one and intercept zero by
construction, as it reads observed over expected of one: an unpenalised
logistic model with an intercept, which the scorecard is (`C=np.inf`),
solves at its maximum exactly the score equations the Cox fit solves at
(0, 1), and the Cox likelihood is concave, so that point is its maximum to
the solver's tolerance. Its cells are the check the code is held to, and a
run on which they do not read one is wrong. GBM-50k on its context
draw is beside it as what a fitted model that is not the likelihood's
maximum reads on rows it fitted. That reading is one-sided, and in the
direction that matters. A model that has seen a row's label predicts that
row better than its stated probability says: a prediction pulled toward its
own label is an outcome more predictable from the logit than the logit
claims, and the Cox fit stretches it, a slope above one. That is the same
direction as smoothing. The synthetic check makes the size plain: a pull of
0.25 on the logit toward the row's label, on a model otherwise calibrated,
reads an in-sample slope of 1.84, and with a shrink of 0.85 beside it 2.34;
the two add, and nothing in the slope tells them apart. An in-context model
scores a context row with that row's label in the context, so its in-sample
slope carries that pull to an unknown degree. An in-sample slope above one
therefore supports nothing on this reading: it is smoothing, or the pull,
or both, and it is reported as confounded. What the in-sample cell can say
is the other way: a slope at one says neither pull is visible on the rows
the model conditions on, and a slope below one beyond its interval is
over-dispersion on those rows, which no pull toward the label produces and
which contradicts smoothing there. Out of time no label is in view and the
reading above is two-sided; the in-sample slope is a description of what
the context does to the model's own scale, beside the level H5 reads on the
same cells.

*What is already on the record, so that no reader takes this note for
blind where it is not.* Every build's `metrics.csv` carries the signed Cox
slope of every cell with its Wald interval, and `cell-intervals.png` draws
it; the cold audit of the falsifying run, recorded in this file's log, had
read the per-cohort slopes of 2004H2-E at 0.9 against the scorecard's Wald
intervals, and Lending Club's signed slopes of every model on 2015H1-E's
three cohorts at both temperatures were in EXP-002's log of 2026-09-06,
before this reading was fixed; what each read is in the log's entry of
2026-09-19, later, "the smoothing note's record of the falsifying run and of
Lending Club, carried here" ([EXP-005-log.md](EXP-005-log.md)) (pointer of
2026-09-19). No pooled signed-slope statistic
with a bootstrap interval, and no in-sample slope, has been computed on
either book. The per-cell columns and figures of this book were drawn
before this note, and they are not claimed unseen; no statistic of this
reading was computed from them.

*Lending Club is read beside it, and it is the weaker reading.* The same
statistic is added to the arm poolings of EXP-002 from the rows the H2 row
at 1.0 reads, under the same seeds. It is weaker on three counts: the
direction on one build is known, above, so the arm's reading there is a
replication of a sign rather than a blind measurement; the book is one
product over five years with a 1.72-fold prevalence range, where this one
spans twenty-two; and it holds no in-sample reading at 1.0 beyond the
falsifying build's one draw. Its standing is the cross-book reading the
Multiplicity paragraph names for every row: the sign and the star on each
book, and no number compared across them.

*What changes in the code, and what must not.* `build_intervals.py` adds
the signed slope, `cox_slope`, to the pooled statistics and to the Cox
statistics that share the estimable mask, so its `mean` and `diff` rows
appear beside `cox_slope_deviation`'s in `paired.csv` and on the figure;
`arm_intervals.py` adds it to the arm's statistics at every scope, the
build-weighted mean under the same mask; `in_sample_level.py` fits the Cox
slope on every context cell, writes it with its Wald interval to
`cells.csv`, reads the scorecard's pool cells as the known answer, and pools
it per arm with the bootstrap it uses for H5, in a call of its own. The
bootstrap draws its row indices and context draws per resample before any
statistic is evaluated and the same resample reaches every name, so adding
names changes no existing value; each pooling is recorded again as
superseding, every existing row, bound and star reproduced to the bit, the
new rows alone added, and a run on which any existing row moves is not
recorded. Nothing is refitted and no row is rescored: the reading is
arithmetic on rows that exist.

*Addition of 2026-09-17, late, on what the bit-for-bit statement compares.*
The statement above is of the statistic and of nothing else: the pooling
with the signed slope must reproduce the same pooling without it, and the
two recordings it compares differ in nothing but the statistic — one
machine, one interpreter, one command but for the output directory, and the
commit before the statistic against the commit that adds it, `1ad2915`
against `9f0e110`, which differ on no file the pooling reads except
`arm_intervals.py` and `build_intervals.py`. A recorded pooling older than
that is not the comparison the statement makes, and a run compared with one
neither passes the statement nor fails it. Lending Club's expanding arm was
last recorded on 2026-09-12 at `a9edd51`, before the Cox fit of `db12783`
and the Cox pooling of `3a7d012`, both of 2026-09-14, and the addition of
2026-09-14 above records what those two do to a recorded pooling: the point
estimates and the stars unchanged, and Cox interval bounds and standard
errors read from resamples moving by at most 3 × 10⁻¹⁶. On that arm,
therefore, the pooling is recorded first at `1ad2915`, with the check seeds,
on the machine that recorded it, superseding the recording of 2026-09-12
with every value and star to the bit and every movement of a bound or a
standard error stated in EXP-002's log by file, column, scope and size as
the Cox commits' and not the statistic's; the pooling with the signed slope
is then held to the statement above against that recording, to the bit, or
it is not recorded. Every other pooling this note names was last recorded
after 2026-09-14 and is held to the statement as written. Beside the arm,
three of its builds are pooled at the two commits with and without the
check seeds
([`experiments/2026-09-17-lc-arm-e-signed-slope-control`](../../experiments/2026-09-17-lc-arm-e-signed-slope-control)
and its pair at `1ad2915`, and the same with the seeds); they are read
before the arm is recorded again, and a pair on which any row moves says
the statistic moved a row and the code is corrected before anything is
recorded. They are not the test; the test is the arm's own pooling. No
number this file or EXP-002 quotes is at a precision where 10⁻¹⁶ is
visible, and the movement enters no ledger row and no public sentence; it
lives in the log entries of the two recordings.

*Note of 2026-09-19, on the results the notes above quoted.* The note of
2026-09-17 and its smoothing reading were written after results on this book
existed, and quoted them: H4's arm and scoped rows, each foundation model's
own E − R, the control's early-stopping rows, round counts and E − R under
each draw, H5's rows at 0.9 and at 1.0, and the width of H4's interval. From
this date the Setting carries numbers about the data — pool sizes,
prevalence, cohort and cell counts, quarters, the arm contrast — and none
produced by a model fit or a pooling on this book. The passages that quoted
such numbers were moved whole to the log's entry of 2026-09-19, where their
sources are named, and each place they stood points there. The readings
those notes fix are unchanged, and no hypothesis, criterion or reading was
changed by the move; the text as it stood is in the history of this file.
*Amended 2026-09-19, later:* from this date the Setting also carries no
statement of what a criterion or a star read on this book. Three passages
that stated one — on H4 under criterion 4 with the recorded run's summary
string, on H4's scoped rows and their difference, and on H5's kill on each
arm — were moved whole to the log's entry of 2026-09-19 "the verdicts the
Setting stated, carried here", and each place points there. No reading
changed: the Setting keeps what criterion 4 compares, the order in which the
sensitivity reading is recorded, the pre-flag identity, the withdrawal of
H5's prior sentence, the arithmetic of the scale and the reading at 1.0 as
the test.
*Amended 2026-09-19, later still:* the note's sentence that the Setting
carries no number produced by a model fit or a pooling on this book, and the
amendment's that it carries no statement of what a criterion or a star read
on it, are read narrowly: it carries no statistic of a model under study on this book's rows
and no statement of what a hypothesis or a kill criterion of this file read.
What it keeps is about the data, the code or a check: the feature gate's R²
from a probe booster, the derivation's check values and its error on the
slope, the Cox fits that raised and the rule that replaced them, what
`ablation_intervals.py` counted under the trigger, the synthetic dry run,
and the other book's scorecard slopes as an example of what the paired
statistic subtracts. One further passage, the smoothing note's record of the
falsifying run's audit and of Lending Club's per-cohort slopes, was moved
whole to the log's entry of 2026-09-19, later, "the smoothing note's record
of the falsifying run and of Lending Club, carried here", its place pointing
there and keeping what it disclosed. No reading changed.

## Pre-registered hypotheses and their kill criteria

H1 to H4 are those of EXP-002 as amended, restated where the book requires
it. H5 is new to this book. Every criterion is a paired difference on
identical cells, read against the bootstrap interval under three seeds, and
"pooled over the arm" means the cell-weighted pooling named above.

**H1 — discrimination decay.** The slope of AUC on age in half-years, one
intercept per build, is no worse for the TFMs than for GBM-50k, which sees
the identical rows.

> *Killed if* the TFM slope is more negative than the GBM-50k slope beyond
> the interval, on the expanding arm, pooled over the arm. *Uninformative
> if* for every pair of models the difference of slopes lies inside its
> interval — the discrimination axis then does not separate model classes on
> this book, and that is reported as such. The cohort-intercept slope is
> reported beside every row; a pair on which the two identifications
> disagree in sign supports at most the weaker claim.

On this grid a build's cells span up to 42 half-years and the calendar inside
a build runs through both regimes, so the build-intercept slope is the
calendar slope net of build with the crisis and the 2022 rise inside it, for
every model alike. That is why only differences between models are read.

**H2 — calibration slope across the prevalence range.** On the expanding
arm the TFMs' mean absolute Cox-slope deviation is no larger than the
scorecard's, paired by cell, at the shipped temperature.

> *Killed if* a TFM exceeds the scorecard beyond the interval. Read at 0.9;
> the same row at 1.0 is beside it, and a verdict that differs between the
> two is reported as differing.

The clause of EXP-002's original H2 that every model loses calibration in
the large is a property of this grid too, larger here, and is reported, not
tested: the builds of 2002H2 to 2006H2 score the crisis cohorts at 5.4 to
6.7 times their training rate, and 2010H2-E scores every one of its cohorts
at 0.25 to 0.87 times its own. Three scoped readings of H2's row are
reported beside the arm pooling, each with its interval and none a
criterion: the cells of 2007H1 to 2009H2, which the three oldest builds score
at ages 9 to 15; the cells of 2022H1 to 2023H2, which every build scores, at
ages 8 to 42; and, per model and build, the ratio of observed-over-expected
on 2022H2–2023H2 to that on 2020H1 and 2021H2 — the measurement ADR-0006
names, of whether a model given the relief-set-aside label shows the 2022
shift. Any sentence about "the book getting riskier" names the realised
rate, the only yardstick this label has.

**H3 — stability.** The PSI of a TFM's score distribution against its own
training reference is no larger than GBM-50k's on the same cell.

> *Killed if* the TFM's PSI exceeds GBM-50k's beyond the interval, pooled
> over the expanding arm. Read with H2 rather than alone: a score
> distribution that moves with a book that moved twentyfold is what a
> calibrated model does, and a smaller PSI is not by itself the better
> result. The first-scored-cohort reference is reported beside every row and
> a verdict is read with both in view.

**H4 — context policy.** The rolling arm reduces calibration drift for the
TFMs by more than it does for GBM-50k, on the 192 cells the two arms share.

> *Killed if* the difference in mean absolute Cox-slope deviation between
> arms is no larger for the TFMs than for GBM-50k, inside the interval.
> *Not tested* on this book if rule 4 above leaves the rolling arm without
> foundation-model cells, and the file says so rather than reading H4 off
> the classical models.

H4 is a hypothesis on this book because the arms differ at every build the
rolling arm exists on — 45% to 89% of the pool removed, the mean row 3.5 to
31.5 quarters younger — and it is reported per build against that build's
measured contrast as well as pooled. The contrast is not monotone in what
it does to the level: at 2010H2 the rolling window is the crisis (4.48%) and
the expanding pool is not (1.75%), and both score a book at 0.44% to 1.53%.
H4 is about the slope, which is why it is written on the slope.

**H5 — the in-sample level across prevalence.** A fitted model reads
observed over expected of 1.00 on its own training rows by construction; on
Lending Club both foundation models at the shipped temperature read a mean
probability near two thirds of their context's realised rate, at
prevalences of 2.0% to 3.4%. Every context of this grid is scored on its own
rows — one cell per build, seed and temperature, 50,000 rows each — and the
hypothesis is that the TFMs' in-sample observed-over-expected at 0.9 does not
depend on the context's realised rate across the contexts of the grid: 0.96%
to 1.75% on the expanding arm, 0.45% to 4.48% on the rolling arm.

> *Killed if* the in-sample observed-over-expected at 0.9 differs between the
> highest-rate and the lowest-rate context of an arm beyond the bootstrap
> interval over context rows, seeds drawn with the resample. A kill says the
> shortfall is a prior pulling the level toward a fixed prevalence rather
> than a scale on the logit; a survival says the temperature is the whole of
> it. The reading at 1.0 is beside it. The tenfold range that makes H5 sharp
> is on the rolling arm; on the expanding arm alone the range is 1.8-fold
> and H5 is read as a weaker test.

H5 costs 7% of the expanding arm's rows and is the one hypothesis on this
book with a known answer to check against: on the context rows of a fitted
model the number is one.

## Kill criteria for the experiment

1. **A pool below the context cap.** If any build's training pool on the
   expanding arm falls below 50,000 labelled rows, the TFM comparison at that
   build is between a sample and a whole pool and is not comparable to the
   others. Measured on the structure run's tables under the exclusions
   above: the smallest expanding pool is 79,532 rows at 2002H2 and clears the
   cap by 59%; the smallest rolling pool is 95,582 at 2008H2 and clears it by
   91%. Neither arm has a whole-pool build, which is the reason the rolling
   arm is eight quarters and starts in 2004.
2. **The effect is inside the interval.** If the TFM-against-control
   difference on the primary axis of a hypothesis lies inside its bootstrap
   interval under every seed, the answer is that there is no effect. Seeds
   are not added until it separates.
3. **The axis does not resolve.** If, for every model on the majority of
   builds, the DeLong interval of the median criterion cell is wider than the
   range of that model's AUC across every criterion cell of the build, the
   benign cohorts at 110 to 150 defaults do not resolve ageing, and there
   are no more rows to add — the cohorts are already whole. The reported
   quantity then becomes the AUC pooled by regime (pre-crisis, crisis, the
   benign decade, the rise) and no slope is read; H1 is reported as
   unresolved at the sample's size rather than as confirmed.
4. **The label's regimes disagree on a verdict.** If a criterion row's sign
   under the primary label differs between its pre-flag scope and its
   flagged scope, the verdict on that row belongs to the reporting regime of
   the label rather than to the model, and it is reported as undetermined on
   this book, with both scopes and the sensitivity reading beside it. The
   pre-flag scope exists on the five oldest builds, 16 to 1 criterion cells
   each; the flagged scope on every build, 8 to 16 cells. A row whose sign
   holds across both scopes and flips only under the sensitivity reading is
   reported with that flip attributed to the cells that carry it, and the
   primary verdict stands, as ADR-0006 requires.

The criterion that kills the project branch rather than this run: if the
scorecard and the GBM are indistinguishable from the TFMs on all three axes
inside their intervals, on this book as on the first, the finding is that
the choice of model class does not matter out of time on either book, and
that is the paper.

## Cheapest falsifying run

One build, **2004H2**, expanding arm, one context seed, all five models, on
the three cohorts nearest the as-of date — 2005H1, 2005H2, 2006H1 — and on
the context's own rows. Fifteen training quarters, 176,111 labelled rows at
1.18%; scored cohorts at 1.02%, 1.09% and 1.74%, 247 to 405 defaults each,
so the age-zero calibration is read on a book that has not yet moved and
the intervals are the grid's median width. Three cells and one in-sample
cell per model and seed, 121,569 scored rows, under half an hour of the
rented device at any speed the probe can return.

It settles four things before the grid is committed to: whether the
scorecard and the GBM land where a mortgage model built on FICO, LTV and DTI
lands — an AUC under 0.70 on 2005H1 for the scorecard means the matrix or
the label is broken and the grid does not start; whether the TFMs'
calibration at age zero is anywhere near the others; whether the two-thirds
level of Lending Club reappears on the context rows at 1.18% prevalence;
and whether the metric module's intervals are narrower than the effect on
this book. If the TFMs' age-zero Cox slope is already outside the
scorecard's interval, H2 is answered without the grid and the grid becomes
the robustness check.

The crisis is not the falsifying run's job. 2006H2-E, which scores 2007H1 to
2008H1 at five to seven times its training rate, is the grid's most
informative build and is scored in the grid's first batch, not before it.

Before the falsifying run, two recorded runs on the CPU with no model in
them: `fm-vintage-builds`, the grid as `vintage.builds` emits it — every
build's pool, blind rows, open-window count, seasoned and gapped exclusions
per cohort, per-cell counts under all three readings, the regime of every
cell, and the base rate every model has to carry, with `build-grid.png`
beside the manifest — and the feature run with the three gates, whose output
is the matrix. Both are appended to the log, and neither is quoted until it
is recorded.

## Prior art check

No row of [../landscape/prior-art.md](../landscape/prior-art.md) uses this
dataset or a mortgage book. The experiment stands on the three rows EXP-003
stands on, each `verified` from full text: arXiv:2605.18147 (no temporal
structure in the other credit TFM evaluation), arXiv:2605.18635 (one
temporal cut, Lending Club), arXiv:2606.30410 (rolling-origin splits on
Lending Club and Home Credit, one metric, no trajectory). The stream learner
on TabICLv2 and the bankruptcy benchmark on random folds added by the sweep
of 2026-09-12 touch neither a mortgage book nor a vintage axis.

Opened under the sweep of 2026-09-12.

## Plot

Six, saved beside the manifests, and none is a bar of a headline number.

- The build grid, from `fm-vintage-builds` before any model: what each build
  was allowed to know, the blind rows, and the training rate against the
  rate of every cohort it scores — the prevalence distance every model
  carries, on a log axis, with the label's regime boundaries drawn.
- Metric against age in half-years, one line per model, one panel per build,
  the crisis and the 2022 cohorts marked and the floor-failing cells drawn
  open. The panels are up to 42 cohorts wide and the oldest is the one
  nobody has drawn for a foundation model.
- The reliability curve per model at four cohorts of one build — the
  youngest, 2007H2, 2013H2, 2023H2 — on the same axes, so the shape of the
  miscalibration is visible across a twentyfold range of realised rate; and
  the same curves on 2019H1 under both label readings, which is what the
  reporting convention does to a reliability diagram.
- The score distribution of one model at every cohort of one build, as a
  ridge, against the training reference the PSI bins were fixed on, and the
  same ridge against the first scored cohort.
- Mean predicted probability against realised rate, one marker per cell, one
  panel per model, both axes log, the identity line drawn and the in-sample
  cells marked: the level across prevalence, which is H5 in and out of
  sample on one figure.
- The relief share by cohort from EXP-003, redrawn with the criterion cells
  of this grid marked and the three regimes shaded: the size of the
  definitional choice, cell by cell, beside the sensitivity reading.

## Multiplicity

The criterion rows on this book are H1, H2 and H3 for each of the two
foundation models, H4 for each if the rolling arm runs on the device, and H5
for each: eight to ten rows, each a 95% bootstrap interval that has to hold
under three seeds. No correction is applied across hypotheses, because each
is a separate pre-registered question with its own kill; under a global null
the expected number of false stars over ten rows is half a star, and a
single star on one row of one book is reported as one star, not as a
finding. The added readings — the cohort-intercept slope, the
first-cohort reference, the build-weighted pooling, the temperature at 1.0,
the sensitivity label, the two regime scopes, the horizon check, the three
scoped readings of H2 — are reported and not tested, and they add no rows.
What the second book is for is the cross-book reading of every criterion
row: same sign and a star on both books, the same sign with a star on one,
or opposite signs. The two books are on different labels and no number is
compared across them (ADR-0006); what is compared is the sign and the
standing of each row, and the shape of each model's trajectory.

## Log and cold audits

Kept apart from the pre-registration, in
[EXP-005-log.md](EXP-005-log.md): the append-only log of every run this
experiment cites, and the cold audits in the order they were made. An auditor
is given this file and not that one.
