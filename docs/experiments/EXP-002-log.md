# EXP-002 — log and cold audits

The append-only log of
[EXP-002](EXP-002-tfm-out-of-time.md) and the cold audits of its runs, kept
apart from the pre-registration so that an auditor reads the hypotheses and
the kill criteria without the entries that read results against them.

## Log

Append-only. Date, what was run, what was observed, pointer to the run.

- **2026-09-04** — opened. The grid is materialised and the leakage assertions
  hold on all eighteen builds:
  [`experiments/2026-09-04-lc-vintage-builds`](../../experiments/2026-09-04-lc-vintage-builds).
  Expanding pools run 52,781 rows at 2013H1 to 1,110,904 at 2017H1; rolling
  pools 47,603 to 785,706. Every build scores between 3 and 19 cohorts, at
  20,000 rows each. Training-pool default rates run 2.27% to 2.86% against
  scored-cohort means of 2.82% to 3.21%, so no build is trained on a book as
  bad as the one it is measured on.

  The arm contrast is measured rather than assumed:
  [`experiments/2026-09-04-lc-arm-contrast`](../../experiments/2026-09-04-lc-arm-contrast).
  It is what put the power caveat into H4 above.

  No model has been fitted.

- **2026-09-04, later** — the rolling arm is re-cut from eight quarters to
  four on the strength of the arm-contrast measurement, and both runs are
  repeated:
  [`experiments/2026-09-04-lc-vintage-builds-rolling4`](../../experiments/2026-09-04-lc-vintage-builds-rolling4)
  and
  [`experiments/2026-09-04-lc-arm-contrast-rolling4`](../../experiments/2026-09-04-lc-arm-contrast-rolling4),
  superseding the pair above. Rolling pools now run 31,016 rows at 2013H1 to
  472,734 at 2017H1; the expanding arm, the blind gaps and the scoring samples
  are unchanged. The rolling arm's training-pool rate runs 2.17% to 3.02%, and
  at both ends of the grid it sits level with the cohorts it scores. Still no
  model fitted.

- **2026-09-04, the scorecard** — the first model, on all eighteen builds:
  [`experiments/2026-09-04-lc-scorecard-uniform`](../../experiments/2026-09-04-lc-scorecard-uniform),
  323 s on CPU, 131 tests green, the smallest build refitted twice inside the
  run with identical bins and a coefficient gap of zero, the binning solved by
  the single-threaded mixed-integer solver. It supersedes two runs of the same
  day: `lc-scorecard-builds`, fitted on a matrix that still held `int_rate` and
  `installment`, and `lc-scorecard-grid`, fitted on one that still held the
  sixty-eight late-coverage columns — both audited, both retained, neither
  citable. The matrix is the twenty-nine columns present from 2010Q1; the run
  re-measured every onset, and `scorecard.json` holds the identities behind
  every other drop: `int_rate` equals the modal rate of its (origination
  month, sub-grade) cell on 94.7% of the book, `installment` is within five
  cents of the level payment on 99.9%.

  The card keeps 8 to 13 characteristics per build. `sub_grade` carries by far
  the most information at every build, IV 0.28 at 2013H1, 0.22 at 2013H2 and
  then rising every build to 0.52 at 2017H1, with the second characteristic —
  `inq_last_6mths` until 2016H1, `fico_range_low` after — never above 0.14.
  Wrong-signed removals are `term` in nine builds from 2014H2 on and
  `fico_range_low` in five: given the lender's own sub-grade, which already
  prices the term and the bureau score, both residuals run the wrong way,
  which is the collinearity a scorecard developer expects and removes.

  Gini at age one runs from 0.315 at 2013H2 to 0.458 at 2015H2 and back to
  0.436 at 2017H1; at the oldest scored cohort it sits between 0.364 and
  0.391 for every build, because the oldest cohort is 2018Q1 for every build.
  On the expanding arm the variance of mean Gini across scored cohorts is 3.5
  times the variance across model ages, and the spread within a cohort, 0.023,
  is smaller than the spread within an age, 0.038, from the run's
  `cohorts.csv`. With cohort fixed effects the slope of Gini on age is
  −0.006 per quarter; the same regression on observed-over-expected gives
  +0.004. Neither is separable from build date or training-pool size on this
  grid, which is the age–calendar collinearity of the audit below, seen in
  data before any foundation model has run.

  Calibration in the large moves with the calendar far more than with age:
  observed over expected on the expanding arm runs 0.85 to 1.02 on the
  twelve cells that score cohorts 2013Q3 to 2014Q4, and 1.16 to 1.65 on the
  eighty-seven cells from 2015Q1 on, twelve of them outside 1.20 to 1.60.
  The youngest cell of the newest build, 2017H1-E on 2017Q3, under-predicts by
  16%; the oldest cell of the oldest, 2013H1-E on 2018Q1, by 55%. The plots:
  `gini-trajectory.png`, `calibration-drift.png` and `card-composition.png`
  in the run directory. No Cox slope, no PSI and no interval computed yet; all
  three wait for the metrics module and the amendment's bootstrap.

- **2026-09-04, night — the matrix re-cut, the grid and the scorecard
  re-recorded.** After the late amendment the grid is re-cut from 2010Q2 on the
  twenty-column matrix:
  [`experiments/2026-09-04-lc-vintage-builds-byvalue`](../../experiments/2026-09-04-lc-vintage-builds-byvalue),
  197 s, superseding the `-rolling4` pair for the expanding arm. Expanding
  pools now run 50,609 rows over nine quarters at 2013H1 to 1,108,732 at
  2017H1; the rolling arm, the blind gaps and the scoring samples are
  unchanged, since none of them reaches back to 2010Q1. The smallest expanding
  pool clears the 50,000-row context by 1.2% rather than 5.6%, which the
  first kill criterion below reads: it is still a sample, barely. Its manifest
  carries the commit that followed it rather than the one it ran on, a defect
  of the recorder fixed the same night; the two commits hold the same scripts.

  The scorecard on the same grid:
  [`experiments/2026-09-04-lc-scorecard-byvalue`](../../experiments/2026-09-04-lc-scorecard-byvalue),
  541 s, 149 tests green, the smallest build refitted twice with identical
  bins and a coefficient gap of zero. It supersedes `lc-scorecard-uniform`,
  whose audit is the third subsection below. The run re-measured the value
  rule on the book and wrote the result into `scorecard.json`: nine columns
  carry the calendar by value, from 2010Q4 for `addr_state` to 2016Q1 for
  `disbursement_method`, and the two clipped columns' first-cohort ranges are
  the declared bounds.

  The card keeps 7 to 12 characteristics per build. `sub_grade` carries the
  most information at every build — IV 0.27 at 2013H1, 0.21 at 2013H2, then
  rising every build to 0.53 at 2017H1 on the expanding arm, and 0.16 to 0.65
  on the rolling arm — with the second characteristic never above 0.16:
  `purpose` at the first two builds, `inq_last_6mths` through 2016H1,
  `fico_range_low` after. Wrong-signed removals are `term` at four expanding
  builds from 2015H2 and six rolling builds from 2014H2, `fico_range_low` at
  five builds, `open_acc` and `credit_history_months` at 2013H1, `annual_inc`
  at the last two rolling builds. Missing bins under a hundred rows scored at
  zero on `revol_util` at the first three expanding builds, `dti` at the last
  two of each arm, and `inq_last_6mths` at 2017H1. The clip has a visible
  cost: `dti`, capped at 24.99, falls below the IV screen at the first five
  expanding builds and the first two rolling ones, and enters the card only
  once the pool is mostly loans written under the higher caps — the risk
  above the first cohort's cap is the part the rule gives up.

  On the cohort every build shares, 2018Q1, Gini runs 0.354 to 0.387 across
  the nine expanding builds, a spread of 0.010, against 0.364 to 0.391 on the
  twenty-nine-column matrix: the columns removed cost about 0.005 of Gini
  there, inside the 0.024 standard error of a single Gini at 638 defaults in
  20,000 rows. Gini at age one runs from 0.336 at 2013H2 to 0.452 at 2015H2
  and 0.433 at 2017H1. Observed over expected on the expanding arm runs 0.85
  to 1.02 on the twelve cells that score cohorts before 2015Q1 and 1.16 to
  1.67 on the eighty-seven from 2015Q1 on; the youngest cell of the newest
  build, 2017H1-E on 2017Q3, under-predicts by 16%, the oldest cell of the
  oldest, 2013H1-E on 2018Q1, by 57%. Nothing here is read as ageing; the
  audit below says why. No Cox slope, no PSI, no interval yet.

- **2026-09-04, night — the challenger, both variants, all eighteen builds.**
  [`experiments/2026-09-04-lc-gbm-byvalue`](../../experiments/2026-09-04-lc-gbm-byvalue),
  47 minutes on four CPU cores, on the same commit and matrix as the
  scorecard run above; the smallest build refitted twice with the same
  point, the same round count and a largest prediction gap of zero. It
  supersedes `lc-gbm-builds`, the run on the previous matrix that the
  amendment cites for its gain shares. Both variants of the amendment's
  protocol ran as written: the full-pool GBM on every build, and GBM-50k on
  the three named context draws, sixteen search points each, 72 fits.

  The early-stopping set resolved as the amendment predicted — one quarter at
  the first three expanding builds and at every rolling build, two quarters
  from 2014H2-E on — holding 10,447 to 240,993 rows. The search chose the
  same corner of the grid at fifteen of eighteen full-pool builds: fifteen
  leaves, learning rate 0.03, two hundred rows per leaf, six columns in ten
  per tree; 2017H1-E took sixty-three leaves, 2016H2-R the fast learning
  rate, and two builds the small leaf. Round counts run 84 to 700 and no
  build ran to the ceiling. `sub_grade` takes 19% of split gain at 2013H1-E
  and 58% at 2016H2-E; nothing else exceeds 12%. At 2013H1-R the pool is
  31,016 rows, the context is the whole pool, and the three seeds returned
  the same model to the last digit, as the first kill criterion says they
  must.

  On the shared cohort, 2018Q1, the full-pool GBM's Gini rises with every
  build date, 0.353 at 2013H1 to 0.425 at 2017H1, spread 0.023 across the
  nine expanding builds; GBM-50k on the same cohort runs 0.337 to 0.394, with
  a seed range of 0.015 to 0.038 per build. The scorecard sat at 0.354 to
  0.387. So on this cohort the newest full-pool booster is about 0.04 of Gini
  ahead of both its own fifty-thousand-row control and the scorecard, and the
  control is not ahead of the scorecard — which is the data-budget effect the
  control exists to isolate, read here without an interval and against a seed
  range that reaches 0.038. Calibration in the large tells the scorecard's
  story again for both variants: observed over expected on the expanding arm
  runs 0.77 to 0.98 on the cells before 2015Q1 and 1.02 to 1.60 (full pool)
  or 1.68 (GBM-50k) from 2015Q1 on. Gini at age one on the expanding arm
  runs 0.345 at 2013H2 to 0.482 at 2015H2. The plots: `gini-trajectory.png`
  with the seed band, `calibration-drift.png` and `importance-drift.png`.
  Nothing here is read as ageing; no Cox slope, no PSI, no interval yet. Both
  runs await a cold audit before any number is cited.

- **2026-09-04, late night — both re-recorded under the corrected protocol.**
  [`experiments/2026-09-04-lc-scorecard-byvalue2`](../../experiments/2026-09-04-lc-scorecard-byvalue2)
  is the scorecard run again with the artifacts the fourth audit asked for:
  all 198 cells identical to `lc-scorecard-byvalue` to the last digit, the
  composition figure with all twenty rows, the calibration figure titled by
  its axis, and the value report carrying what the clip moved — 23.2% of the
  book on `dti` and 13.1% on `loan_amnt`, from nothing in 2010Q2 to 25.0% and
  17.9% of 2018Q1.
  [`experiments/2026-09-04-lc-gbm-wide`](../../experiments/2026-09-04-lc-gbm-wide),
  76 minutes, is the challenger on the thirty-six-point grid with the context
  control on its build's point. Every control draw now shares its build's
  point, and the seed range on 2018Q1 runs 0.005 to 0.032 against 0.015 to
  0.038 before. The search still ends on an edge at every build — a thousand
  rows per leaf at all eighteen, the slow rate at eleven, seven or thirty-one
  leaves at fourteen — and the run says so in every note. What the edge costs
  is also in the notes: the best point beat its runner-up by 3 × 10⁻⁶ to
  3 × 10⁻⁴ in log-loss, and beat the same point at two hundred rows per leaf
  by 5 × 10⁻⁵ to 1.3 × 10⁻³. The surface is flat there; a wider grid would
  move the third decimal of the log-loss and not the comparison. On 2018Q1
  the full-pool GBM runs 0.359 to 0.425 across the expanding builds, mean
  0.402 against 0.393 on the sixteen-point grid; the control 0.352 to 0.395,
  mean 0.373; the scorecard 0.354 to 0.387. The reading of the fourth audit
  stands: about 0.03 of Gini for the full pool over the scorecard on this
  cohort, roughly nothing for the control, and the difference between them is
  the data budget. Both runs await their own cold audit.

- **2026-09-05, past midnight — the challenger with the dataset filter off,
  and the scorecard once more.**
  [`experiments/2026-09-04-lc-gbm-wide2`](../../experiments/2026-09-04-lc-gbm-wide2),
  75 minutes, supersedes `lc-gbm-wide`; the fifth audit below is why.
  [`experiments/2026-09-04-lc-scorecard-byvalue3`](../../experiments/2026-09-04-lc-scorecard-byvalue3)
  repeats every one of the scorecard's 198 cells to the last digit and is the
  run to cite for it, carrying the wrapped figure titles and a manifest that
  now hashes the eight modules of the library beside the script and the data.
  With `feature_pre_filter` off the search chose the same point at all
  eighteen builds and the same round count at 2013H1-R, 77; the control at
  2013H1-R, whose rows are the whole pool, now returns 77 rounds on every
  draw where it had returned 71, which is the inconsistency the audit
  demonstrated, closed. Across the 792 cells of the grid Gini moved by
  −0.0001 on average, −0.014 to +0.011 at the extremes, inside the seed
  range. On 2018Q1: full pool 0.359 to 0.425, mean 0.402; control 0.352 to
  0.395, mean 0.373, seed range 0.005 to 0.032; scorecard 0.354 to 0.387.
  Observed over expected for the full pool on the expanding arm, 0.79 to
  1.60. These are the numbers the scorecard and the challenger carry into
  the study, read with the fifth audit's qualifiers: no per-build difference
  is quoted before the metrics module puts an interval on it, and the GBM is
  tuned within a stated budget on a flat surface.

- **2026-09-05 — the first intervals, on 2015H1-E.** The metrics module
  landed with the amendment's bootstrap as its central object, and two runs
  put it on the build of the cheapest falsifying run.
  [`experiments/2026-09-05-lc-2015h1e-scores`](../../experiments/2026-09-05-lc-2015h1e-scores),
  375 s, refits the scorecard, the full-pool GBM and the three draws of the
  control on 2015H1-E and keeps every row's score: 1,100,000 scored rows over
  the eleven cohorts and 796,052 reference rows. All 55 cohort aggregates
  match `lc-scorecard-byvalue3` and `lc-gbm-wide2` to the last recorded
  digit, so the scores are the scores of the cited runs.
  [`experiments/2026-09-05-lc-2015h1e-intervals`](../../experiments/2026-09-05-lc-2015h1e-intervals),
  55 s, reads them: 200 cohort-blocked resamples, the context draw drawn with
  each, seed 20260905, and the per-cell intervals beside them.

  What the intervals say, on this one build. A single cell's Gini carries a
  DeLong half-width of 0.036 to 0.042, which is the auditor's 0.020 standard
  error again and is why no per-cell difference was ever readable. Pooled
  over the eleven cohorts and paired by resample, the full-pool GBM is ahead
  of the scorecard by 0.020 Gini, interval 0.014 to 0.025; the control is
  ahead by 0.007, interval −0.002 to 0.016, which holds zero; and the control
  trails the full pool by 0.013, interval −0.022 to −0.004. On the three
  nearest cohorts, the subset the falsifying run scores, the same three
  differences read 0.016 (0.007 to 0.027), 0.010 (−0.001 to 0.022) and −0.007
  (−0.018 to 0.004). The reading the fourth and fifth audits allowed only as
  a sign pattern now has a floor under it: rows, not model class, and the
  floor on a paired Gini difference is about ±0.006 over eleven cohorts and
  ±0.011 over three. A foundation model that differs from the scorecard by
  one Gini point will not resolve in the falsifying run; one that differs by
  two will.

  Calibration in the large is the withdrawn first clause of H2, reported and
  not tested: the lower end of the binomial interval on observed over
  expected is above 1.07 on every one of the 55 cells, so every model on
  every cohort of this build asks for fewer defaults than arrive, beyond
  sampling. The paired |log O/E| differences are tight because the observed
  side cancels in a pair: the full pool sits 0.045 closer to one than the
  scorecard (−0.047 to −0.044), the control 0.022 closer (−0.054 to −0.006).
  No Cox slope yet; it follows in the same module.

  PSI against each model's own reference — the training pool for the fitted
  models, the context sample for each draw of the control — runs 0.006 to
  0.069 across the cells against a Yurdakul critical value of 0.0009 to
  0.0012, five to sixty times over on every cell, which is what the amendment
  said the critical value would do on this book and why H3 became a
  magnitude. The magnitude: the scorecard's score distribution moves more
  than either GBM's, 0.033 against 0.017 pooled, and the two GBMs do not
  differ (0.0003, −0.002 to 0.003). Read with H2: the model whose scores move
  most is also the one furthest from calibration, and neither is read as the
  better property. The plots: `cell-intervals.png`, every cell with its own
  interval on three panels, and `paired-differences.png`, the pooled
  differences on both poolings against zero.

- **2026-09-05 — the intervals re-read after the sixth audit, and the bundle
  for the node.** Two runs on the same commit.
  [`experiments/2026-09-05-lc-2015h1e-intervals2`](../../experiments/2026-09-05-lc-2015h1e-intervals2),
  194 s, is the first intervals run repeated with what the audit asked for:
  every one of its 36 recorded rows reproduces to the last digit, and beside
  them the script now writes the pooled interval with each context draw held
  fixed and a third pooling with the cohorts resampled as well as the rows.
  Held fixed, the draws disagree on four of the nine differences: |log O/E|
  of the control against the full pool reads +0.037 to +0.040 on two draws
  and −0.010 to −0.006 on the third, where the mixture reads +0.023 with an
  interval holding zero; PSI of the control against the full pool is
  +0.002 to +0.004 on one draw and −0.002 to −0.0003 on the other two, where
  the mixture reads +0.0003; the same two statistics against the scorecard
  split the same way. The three Gini differences are not flagged: their draw
  intervals overlap. Resampling the cohorts widens every interval and moves
  no sign: the full pool's lead over the scorecard becomes 0.012 to 0.030
  from 0.014 to 0.025, the control's shortfall against the full pool
  −0.024 to −0.003 from −0.022 to −0.004, and the |log O/E| gap between the
  full pool and the scorecard −0.061 to −0.034 from −0.047 to −0.044, seven
  times wider. Two sentences of the 2026-09-05 entry above are read from
  here on with these rows: "the two GBMs do not differ" on PSI is three
  draws that each differ and cancel, and the control's |log O/E| interval
  is not one distribution. The Gini reading — rows, not model class, with a
  floor near ±0.006 over eleven cohorts — stands on the mixture and on the
  cohort-resampled pooling alike. The PSI panel of `cell-intervals.png` now
  draws each cell as a multiple of its own critical value.
  [`experiments/2026-09-05-lc-2015h1e-bundle`](../../experiments/2026-09-05-lc-2015h1e-bundle),
  143 s, packs 2015H1-E for the machine that holds the accelerator: the
  three context samples of 50,000 rows and the eleven scoring cohorts of
  20,000, with the twenty-column matrix, three columns categorical, 8.5 MB
  in two parquet files, checked row by row and outcome by outcome against
  `lc-2015h1e-scores`. What the node returns from it is the falsifying
  run's first foundation-model number, in the row format the classical
  scores already use.

- **2026-09-06 — the TabPFN half of the falsifying run.**
  [`experiments/2026-09-06-lc-2015h1e-tabpfn-m4pro`](../../experiments/2026-09-06-lc-2015h1e-tabpfn-m4pro),
  a hand manifest over what the node returned: TabPFN 8.5.0 at its
  defaults on the M4 Pro, the 50,000-row context of seed 20260911 from the
  bundle, the three cohorts nearest the build date, 1,744 s of wall, the
  first cell scored twice from a fresh fit with no row differing. Every
  scored row and every reference row matches the classical run's rows and
  outcomes, so the pairing below is on identical rows.
  [`experiments/2026-09-06-lc-2015h1e-intervals-tabpfn`](../../experiments/2026-09-06-lc-2015h1e-intervals-tabpfn),
  38 s, pools it with `lc-2015h1e-scores` over those three cohorts. The
  eight cohorts TabPFN did not score and the control's two other draws are
  left out of the pooling by name; with one draw on each side the mixture
  rows and the fixed-draw rows coincide, and "nearest" is the whole pooling.

  Discrimination. TabPFN's Gini reads 0.445, 0.462 and 0.476 on 2015Q3,
  2015Q4 and 2016Q1, with DeLong half-widths near 0.04, so no cell is read
  alone. Paired and pooled: TabPFN over the scorecard +0.022 (0.013 to
  0.032), over the control +0.017 (0.009 to 0.026), over the full-pool GBM
  +0.005 (−0.005 to 0.015), which holds zero. Resampling the cohorts as well
  widens the first two to (0.003, 0.041) and (0.000, 0.032) and moves no
  sign. The previous entry said a foundation model two Gini points from the
  scorecard would resolve on three cohorts and one point would not; this one
  sits two points above the scorecard and resolves, and the comparison that
  isolates model class from rows — TabPFN against the control, both reading
  the same 50,000 rows — is the one with the clearer interval. Against the
  GBM fitted on 323,026 rows the difference is inside its floor.

  Calibration in the large, reported and not tested as the amendment says.
  TabPFN's observed over expected is 1.85 (1.70 to 2.01), 1.96 (1.80 to
  2.13) and 2.30 (2.13 to 2.48) on the three cohorts, where the scorecard,
  the full pool and the control read 1.21 to 1.59 on the same cells and the
  highest cell of any of them on any of the eleven cohorts is 1.67 (2017Q2,
  the scorecard, upper bound 1.79). The shortfall is there before any
  cohort: on the context rows themselves, whose outcomes the model was given
  and whose realised rate is 2.25%, its mean probability is 1.54%, a ratio of
  1.46 where a fitted model sits at 1.00 on its own training rows. The drift
  across the three cohorts is the book's and not the model's: log O/E rises
  by 0.22 from 2015Q3 to 2016Q1 for TabPFN and by 0.23 for the full-pool
  GBM, so the two lines on the middle panel of `cell-intervals.png` are
  parallel and 0.4 apart. Paired |log O/E|: TabPFN against the scorecard
  +0.391 (0.388 to 0.394), against the control +0.395, against the full pool
  +0.422, each a hundred times its interval. The score distribution is
  compressed rather than shifted: the median probability is 1.04% against
  the GBM's 1.66%, and 2.0% of scored rows sit above 5% against 7.2%. Brier
  is highest for TabPFN on all three cells, 0.02605 against 0.02586 for the
  full pool on 2015Q3, which is where the discrimination gain goes. The
  parameters that shipped are in `node.json`, every one at its default
  except the categorical indices and `ignore_pretraining_limits`; why the
  probabilities come out at two thirds of the rate is not measured here and
  is not guessed at.

  Stability. Against its own context sample TabPFN's score distribution
  moves least of the four: PSI 0.0115, 0.0151 and 0.0241, ten to twenty
  times the critical value, against the control's 0.0130, 0.0195 and 0.0267
  on the same reference size; paired, −0.0028 (−0.0042 to −0.0015) against
  the control and −0.0136 against the scorecard. Read with the paragraph
  above as the amendment asks: the model whose scores move least is the one
  furthest from the realised rate on every cell, and a compressed
  distribution has less room to move.

  What the cheapest falsifying run was sent to settle. The classical models
  land where the earlier entries put them. The foundation model's
  calibration is not near theirs at age zero: at one quarter its interval
  (1.70 to 2.01) is clear of every classical cell's upper bound at that age
  (1.26 to 1.35), and clear of every classical cell of the build. The
  intervals do not swallow the effect on Gini against the scorecard or the
  control, and do swallow it against the full pool. No kill criterion is
  read on one draw and three cohorts, and H2's own criterion is the Cox
  slope, which the metrics module does not yet compute; nothing here is an
  answer to H2, and the sentence the section allowed — that the grid becomes
  the robustness check if age-zero calibration is already outside the
  scorecard's interval — is written down as what this one build shows. The
  plots: `cell-intervals.png` with TabPFN's three cells on each panel, and
  `paired-differences.png` with the six pairs on both poolings.

  Next: the TabICL half from the same bundle on a CUDA node, the seventh
  audit over both halves and this intervals run, and the Cox slope in the
  metrics module before any sentence about H2.

- **2026-09-06 — the TabICL half, and the two halves pooled.**
  [`experiments/2026-09-06-lc-2015h1e-tabicl-colab-t4`](../../experiments/2026-09-06-lc-2015h1e-tabicl-colab-t4),
  a hand manifest over what a hosted T4 returned: tabicl 2.1.1 at its
  defaults, checkpoint `tabicl-classifier-v2-20260212`, the same bundle, the
  same 50,000-row context of seed 20260911 and the same three cohorts as the
  TabPFN half, 526 s of wall, 20,000 rows per forward call, peak 10.97 GB,
  the first cell scored twice from a fresh fit with no row differing. Every
  scored row and every reference row matches the classical run's rows and
  outcomes, so the three models are paired on identical rows.
  [`experiments/2026-09-06-lc-2015h1e-intervals-tfm`](../../experiments/2026-09-06-lc-2015h1e-intervals-tfm),
  40 s, pools both halves with `lc-2015h1e-scores` over the three cohorts;
  it supersedes `lc-2015h1e-intervals-tabpfn`, whose rows it reproduces.

  Discrimination. TabICL's Gini reads 0.451, 0.460 and 0.477 on the three
  cohorts, within 0.006 of TabPFN's on every cell, and the two models' row
  probabilities correlate at 0.976 (Spearman 0.982). Paired and pooled:
  TabICL over the scorecard +0.023 (0.014 to 0.034), over the control +0.019
  (0.011 to 0.027), over the full-pool GBM +0.007 (−0.003 to 0.016), which
  holds zero; TabICL over TabPFN +0.002 (−0.003 to 0.006), which holds zero.
  Two foundation models of different lineage, given the same 50,000 rows,
  rank the same three cohorts the same way and both sit two Gini points
  above the scorecard, one and a half above the control, and inside the
  floor of the GBM fitted on 323,026 rows.

  Calibration in the large, reported and not tested. TabICL's observed over
  expected is 1.65 (1.51 to 1.79), 1.74 (1.60 to 1.89) and 2.04 (1.89 to
  2.20), between the classical models' 1.21 to 1.59 and TabPFN's 1.85 to
  2.30 on the same cells, and clear of every classical upper bound on every
  cell. The shortfall is again there before any cohort: on the context rows
  themselves, realised rate 2.25%, TabICL's mean probability is 1.53%, a
  ratio of 1.47 against TabPFN's 1.46 — two architectures, two checkpoints,
  the same two thirds of the rate they were shown. The drift across the
  cohorts is the book's: log O/E rises by 0.21 for TabICL, 0.22 for TabPFN
  and 0.23 for the full-pool GBM. Paired |log O/E|: TabICL against the
  scorecard +0.271 (0.268 to 0.274), against the full pool +0.302, against
  TabPFN −0.120 (−0.121 to −0.119). The distribution is compressed as
  TabPFN's is: median probability 1.16% against the GBM's 1.66%, 3.4% of
  scored rows above 5% against 7.2%. Brier sits between TabPFN's and the
  classical models' on all three cells. Why both models return two thirds
  of the rate is not measured here; that both do, and by the same factor,
  is the one new fact of this half.

  Stability. TabICL's score distribution moves least of the five: PSI
  0.0116, 0.0038 and 0.0081 against its own context sample, three to ten
  times the critical value where every other model sits at ten to fifty;
  paired, −0.0119 (−0.0153 to −0.0093) against the control and −0.0091
  against TabPFN. The sentence of the previous entry — that the model
  furthest from the rate moves least — does not survive this half: TabICL
  is nearer the rate than TabPFN and moves less. What the two halves say
  together is that a compressed distribution moves less, whatever its
  centre.

  What the cheapest falsifying run now says. On one build, one draw and
  three cohorts, both foundation models clear the scorecard and the control
  on Gini and neither clears the full-pool GBM; both are outside every
  classical calibration interval at age zero, in the same direction, and
  both were already there on their own context rows. No kill criterion is
  read on this run; H2's criterion is the Cox slope, still uncomputed. The
  grid is now the robustness check for the calibration sentence and the
  experiment for the discrimination one. The plots: `cell-intervals.png`
  with five models on each panel, `paired-differences.png` with the ten
  pairs.

  Next: the seventh audit over both halves and the pooled intervals; the
  Cox slope, the Murphy decomposition and the reliability curve in the
  metrics module; then a sentence about H2.

- **2026-09-06 — the pooled intervals re-recorded with the calibration
  statistics the Setting names, after the seventh audit (below).**
  [`experiments/2026-09-06-lc-2015h1e-intervals-tfm2`](../../experiments/2026-09-06-lc-2015h1e-intervals-tfm2),
  94 s, the same three score directories, clean tree. Every row of
  `lc-2015h1e-intervals-tfm` reproduces to zero — 90 paired rows, 488 cell
  rows — and **this run supersedes it; cite this one.** New per cell: the
  Cox intercept and slope with Wald intervals, the Brier score split into
  miscalibration, discrimination and uncertainty by isotonic recalibration,
  and `reliability.png` on the youngest and oldest pooled cohort. New in the
  pooling: the mean over cohorts of |Cox slope − 1|, which is the statistic
  H2 is written on. The poolings are named by count where a reader sees
  them: three shared cohorts of eleven scored. The summary says, where
  before it said that no draws disagreed, that one context draw is shared
  and the seed spread is not measured.

  The Cox slope, per cell. TabICL 1.018, 1.062 and 1.025, TabPFN 1.041,
  1.109 and 1.054, every Wald interval holding one; the full-pool GBM 1.065,
  1.097 and 1.071, holding one; the scorecard 1.130, 1.206 and 1.073, clear
  of one on 2015Q4 (1.073 to 1.339); the control 1.272, 1.276 and 1.202,
  clear of one on every cell. Pooled |slope − 1|: TabICL 0.035, TabPFN
  0.068, GBM 0.078, scorecard 0.136, control 0.250. Paired: TabPFN −
  scorecard −0.068 (−0.096 to −0.017), TabICL − scorecard −0.101 (−0.131 to
  −0.029), both clear of zero with the cohorts held fixed and with the
  cohorts resampled (−0.115 to −0.004; −0.154 to −0.008); against the
  full-pool GBM −0.010 and −0.043, holding zero; against the control −0.182
  and −0.215, clear of zero either way. A caution on the intercept: Cox's
  intercept is read at a logit of zero, four logits from where these scores
  sit, so on a cell whose slope is away from one it mixes the two terms;
  the level is read from observed over expected and the shape from the
  slope, and the intercept column is kept for completeness.

  H2, read on this run for the first time. The amendment asks whether the
  TFMs' mean absolute Cox-slope deviation is no larger than the scorecard's,
  and kills if it exceeds the scorecard's beyond the interval. On one build,
  one draw and three cohorts it does not fire: both foundation models sit
  nearer a slope of one than the scorecard, and the difference clears the
  floor under both poolings. The first clause holds — every model's
  observed over expected is above one on every cell, with lower bounds of
  1.069 and up for the classical models and 1.51 and up for the TFMs — and
  the second kill, no ratio leaving its binomial interval, does not fire.
  What this says beside the previous entry: the TFMs' miscalibration on
  these cells is a level, the classical models' partly a stretch, and the
  two statistics disagree by construction. On |log O/E| the TFMs are the
  worst of five by 0.27 to 0.39; on |slope − 1| they are the best. Both are
  true; neither is the other, and the reliability figure shows why. The
  TFM curves run above the diagonal and parallel to it on both cohorts, the
  scorecard's and the control's start on the diagonal at the low scores and
  steepen away from it, and the full-pool GBM's lies between. The TFM
  curves also end early: their top bin's mean probability is 0.043 and
  0.050 where the GBM's is 0.063, the compression the previous entry
  measured as a median.

  The decomposition. Brier on 2015Q3 runs 0.02586 to 0.02605 across the
  five models and 0.0311 to 0.0315 on 2016Q1, of which the uncertainty
  term, 0.02632 and 0.03168, is 98 to 99 percent. Miscalibration: TabPFN
  0.00039, 0.00050 and 0.00069, TabICL 0.00029, 0.00040 and 0.00056,
  against the scorecard's 0.00014, 0.00023 and 0.00035 and the GBM's
  0.00011, 0.00016 and 0.00032 — two to three times, which is where the
  factor of two in the large goes when the scalar is reported: into its
  fourth decimal. Discrimination: TFMs 0.00063 to 0.00089, level with or
  above the GBM's 0.00057 to 0.00087 and above the scorecard's 0.00054 to
  0.00069. The foundation models give up more to recalibration and gain
  more from it, on the same rows.

  Next: the temperature probe on the same bundle and cells, since 0.9 is
  the one knob both models shipped with and a level is what a temperature
  moves; the TFM cells on context seeds 20260912 and 20260913, so the
  per-draw rows exist before any sentence about the control.

- **2026-09-06 — the temperature probe: the same bundle, draw and cohorts
  at `softmax_temperature = 1.0`, and the pooled intervals with those rows
  beside everything before them.**
  [`experiments/2026-09-06-lc-2015h1e-probe3-colab-t4`](../../experiments/2026-09-06-lc-2015h1e-probe3-colab-t4)
  (free T4, three commands in one session: TabICL at 1.0, 510 s; TabPFN at
  1.0, 1,075 s; TabPFN at 1.0 with `balance_probabilities`, 939 s; hand
  manifest with the archive hashes both ways, the scorer hash equal to the
  tree at `fd5eadf`, the bundle hashes equal to the recorded export, every
  scored and reference row matched against `lc-2015h1e-scores` with zero
  mismatches, the repeat cell at 0.0 for all three) and
  [`experiments/2026-09-06-lc-2015h1e-intervals-probe3`](../../experiments/2026-09-06-lc-2015h1e-intervals-probe3)
  (144 s, clean tree, the four score directories, eight models, 28 pairs,
  one draw). **Cite `intervals-probe3` for any sentence at 1.0**;
  `intervals-tfm2` stays the citation at the shipped setting. The scorer
  gained `--temperature` and `--balance` for this run and writes a model
  off its defaults under a tagged name, `tabicl@t1`, `tabpfn@t1`,
  `tabpfn@t1+bal`, so the rows pair beside the default rows rather than
  replacing them. The console log is included with one line removed: the
  notebook held no licence secret, the library prompted inside the cell,
  and the key pasted at the prompt was echoed; the manifest says so.

  The question the probe was sent with, written before the
  run: both models shipped 0.9 and both returned two thirds of the realised
  rate on their own context rows; the kill was a context-row ratio of mean
  probability to realised rate inside 1.00 ± 0.05 at 1.0. It fired. On the
  50,000 context rows, realised rate 2.248 %, the mean probability at 1.0
  is 0.02227 for TabICL and 0.02244 for TabPFN — ratios 0.991 and 0.998 —
  against 0.680 and 0.685 at 0.9 on the same rows. The two-thirds level of
  the previous two entries was the shipped temperature.

  What the temperature is, measured on the rows. For TabICL the logit at
  1.0 equals 0.9 times the logit at 0.9 on every one of the 110,000 rows to
  1e-6 (the library averages logits before the softmax, so the temperature
  is a scale on the logit and nothing else). For TabPFN it is nearly so:
  the fitted scale is 0.8996, the mean absolute departure 0.008 on the
  logit, one reference row at 0.99 (it averages after the softmax, so the
  scale is applied per estimator and the average of rescaled probabilities
  is not a rescaled average). A monotone map leaves ranks and deciles where
  they were: Gini and PSI at 1.0 equal those at 0.9 exactly for TabICL and
  to 0.0002 and 0.0004 for TabPFN, so every discrimination and stability
  sentence of the previous entries stands unchanged.

  What it does to H2. The Cox slope regresses the outcome on the logit, so
  dividing the logit by 0.9 multiplies the slope by 0.9 in reverse: at 1.0
  TabICL's slopes are 1.132, 1.180 and 1.139 where they were 1.018, 1.062
  and 1.025, and TabPFN's 1.157, 1.233 and 1.173 where they were 1.041,
  1.109 and 1.054, every Wald interval now clear of one. Pooled |slope − 1|
  against the scorecard's 0.136: TabICL at 1.0 +0.014 (−0.018 to +0.045),
  holding zero; TabPFN at 1.0 +0.052 (+0.018 to +0.083), clear of zero,
  the foundation model further from one. Against the full-pool GBM both
  are clear of zero on the wrong side (+0.072 and +0.110); against the
  control both are still nearer one (−0.100 and −0.063). The sentence the
  previous entry read from this criterion — both foundation models nearer
  a slope of one than the scorecard — is a sentence about the shipped
  temperature, and at 1.0 it does not hold for TabPFN and is a tie for
  TabICL. The intercept does not move (it is read at a logit of zero, the
  fixed point of a scale); the level does, and the two are one number seen
  twice: the shipped 0.9 is a correction to the slope, paid for in the
  level. At 1.0 the foundation models' miscalibration is the classical
  models' stretch, no longer a shift.

  What it does to the level out of time. Observed over expected at 1.0:
  TabICL 1.140, 1.196 and 1.410 on the three cohorts, TabPFN 1.263, 1.334
  and 1.572, against the scorecard's 1.238, 1.318 and 1.587 and the GBM's
  1.210, 1.285 and 1.516. Pooled |log O/E| against the scorecard: TabICL
  −0.099 (−0.102 to −0.097), TabPFN +0.007 (+0.005 to +0.010), both clear
  of zero on a single draw; against the GBM −0.068 and +0.039. The rise
  from the first cohort to the third is 0.21 on the log scale for TabICL,
  0.22 for TabPFN, 0.25 for the scorecard, 0.23 for the GBM: the decay is
  the book's, at one temperature or the other. Murphy at 1.0: TabICL's
  miscalibration 0.00013, 0.00021 and 0.00027, TabPFN's 0.00021, 0.00031
  and 0.00038, against the scorecard's 0.00014, 0.00023 and 0.00035 and
  the GBM's 0.00011, 0.00016 and 0.00032 — level with them, where at 0.9
  they were two to three times. Brier at 1.0 is the lowest of the eight
  on every cell (TabICL 0.02582, 0.02624, 0.03106), by amounts in the
  fourth decimal, which is the same decimal the factor of 1.46 lived in.
  The run's `reliability.png` shares one axis across eight panels, and the
  balanced model stretches it to 0.75, so the six panels at the credit
  scale are unreadable there; the reliability at 1.0 is read from the
  level and the decomposition above, and a figure without the balanced
  rows belongs to the grid.

  `balance_probabilities`. TabPFN's mean probability becomes 0.444 on the
  context rows and 0.42 to 0.43 on the cohorts: the setting divides each
  class probability by its context frequency and renormalises, a shift on
  the logit by the log of the prior ratio, and it leaves Gini, PSI and the
  Cox slope exactly where the unbalanced model at 1.0 has them. It is a
  decision rule for balanced accuracy, not a probability, and it is set
  aside here with its rows on the record.

  What this run cannot say. One build, one draw, three cohorts, as
  before; the seed spread is unmeasured and every interval above is
  conditional on draw 20260911. The probe moved one scalar that a risk
  team adopting the library would not have known to move; the object
  under study remains the model as shipped, and the amendment of
  2026-09-06 in the pre-registration says how the two settings are
  reported from here.

  Next: the eighth audit over this run and its pooled intervals; the TFM
  cells on context seeds 20260912 and 20260913 at the shipped setting, so
  the per-draw rows exist; then the grid at both temperatures for TabPFN
  and at the shipped one for TabICL, its 1.0 rows derived by the exact
  scale and checked against this probe's rows before use.

- **2026-09-06 — the two context draws the falsifying run did not score,
  and the pooled intervals with three draws on every seeded model.**
  [`experiments/2026-09-06-lc-2015h1e-draws-colab-t4`](../../experiments/2026-09-06-lc-2015h1e-draws-colab-t4)
  (free T4, one session after the probe, both models on seeds 20260912 and
  20260913 at the shipped settings, 2,905 s; hand manifest with the
  archive hash, the scorer hash equal to the tree, the bundle hashes equal
  to the recorded export, every scored row matched against the classical
  rows and every reference row against the control's own reference of the
  same seed, zero mismatches, the repeat cell at 0.0 for all four) and
  [`experiments/2026-09-06-lc-2015h1e-intervals-draws`](../../experiments/2026-09-06-lc-2015h1e-intervals-draws)
  (197 s, clean tree, the classical scores, both halves of the falsifying
  run and this run; five models, three draws each for the control and both
  foundation models, ten pairs). The probe's rows at 1.0 hold one draw and
  are left out here, since the pooling keeps the draws every seeded model
  carries and would otherwise drop the two this run adds. **Cite
  [`experiments/2026-09-06-lc-2015h1e-intervals-draws2`](../../experiments/2026-09-06-lc-2015h1e-intervals-draws2)
  for any sentence about the control**: the same pooling recorded again
  after the eighth audit with the figures it asked for, every number bit
  for bit the same; `intervals-tfm2` and `intervals-probe3-nobal` stay the
  citations for the single-draw readings.

  The level, per draw. The ratio of mean probability to realised rate on
  the context rows is 0.694 and 0.707 for TabICL and 0.704 and 0.695 for
  TabPFN on the new draws, against 0.680 and 0.685 on the first: the same
  number on three samples of the same pool, as a default setting should
  give. Cohort-row probabilities correlate 0.936 to 0.940 between draws
  for both models, so the draw moves rows and not the level.

  What the mixture of three draws says against the control, and what the
  draws say one at a time. Gini: TabICL − control +0.015 (+0.004 to
  +0.024), clear of zero, and clear on every draw (+0.019, +0.018,
  +0.009); TabPFN − control +0.010 (−0.002 to +0.025), holding zero, and
  clear on two draws of three (+0.017, +0.010, +0.004). The previous
  entries' +0.017 was the first draw, the control's worst on Gini (0.444
  against 0.451 and 0.451); the number to carry is +0.010, and it does not
  clear the floor. Against the scorecard both foundation models still do,
  +0.020 and +0.025; against the full-pool GBM both still hold zero. |log
  O/E| − control: +0.394 and +0.274, clear of zero on the mixture and on
  every draw, all of one sign; the flag marks that the draws' intervals
  do not all overlap, not a disagreement of sign. |Cox slope − 1| − control:
  −0.120 (−0.200 to +0.014) and −0.141 (−0.231 to +0.026), holding zero
  on the mixture; per draw, clear on the first and the third, holding
  zero on the second, where the control's own deviation is 0.091 against
  0.250 and 0.194. The first draw was the control's worst on this
  statistic too, and the previous entry's −0.18 and −0.22 were read on
  it. PSI − control: TabPFN +0.002 (−0.004 to +0.008), sign changing
  across the draws (−0.003, +0.007, +0.000), which confirms the seventh
  audit's withdrawal; TabICL −0.010 (−0.015 to −0.006), clear on every
  draw. The control against the full-pool GBM on Gini, −0.007 (−0.019 to
  +0.004), now holds zero where the first draw alone had it clear; rows
  are still what separates the two, but the three-draw floor is wider
  than one draw showed.

  What stands from the earlier entries, unchanged by the draws: both
  foundation models above the scorecard on Gini and inside the full-pool
  GBM's floor; the level at two thirds on the context rows at the shipped
  temperature; the slope nearer one than the scorecard's at that
  temperature (−0.078 and −0.099, clear of zero); TabICL's PSI the lowest
  of five. What the draws change: every sentence that ranked a foundation
  model against the 50,000-row control on Gini or on the slope was read
  on the control's worst draw, and with three draws mixed TabICL keeps
  the Gini sentence and neither model keeps the slope sentence.

  Next: the eighth audit over the probe, this run and both pooled
  intervals; then the grid.

- **2026-09-06 — TabICL's rows at 1.0 on all three draws, derived from its
  rows at the shipped setting and checked against the probe, and the
  pooled intervals with them.**
  [`experiments/2026-09-06-lc-2015h1e-tabicl-t1-derived`](../../experiments/2026-09-06-lc-2015h1e-tabicl-t1-derived)
  (`scripts/derive_temperature.py` over the TabICL half of the falsifying
  run and the draws run, checked against the probe; 330,000 rows written,
  110,000 of them checked, clean tree) and
  [`experiments/2026-09-06-lc-2015h1e-intervals-tabicl-t1`](../../experiments/2026-09-06-lc-2015h1e-intervals-tabicl-t1)
  (307 s, clean tree, the classical scores, both halves, the draws and the
  derived rows; six models, three draws each for the control, both
  foundation models and TabICL at 1.0, fifteen pairs). The probe's TabPFN
  rows at 1.0 hold one draw and stay out, as before. **Cite
  [`experiments/2026-09-06-lc-2015h1e-intervals-tabicl-t1-2`](../../experiments/2026-09-06-lc-2015h1e-intervals-tabicl-t1-2)
  for any sentence about TabICL at 1.0**, the same pooling recorded again
  after the eighth audit with the figures it asked for and every number
  the same; `intervals-probe3-nobal` is the citation for TabPFN at 1.0, on
  one draw.

  What the derivation is, and what it refuses. The temperature is a scale
  on the logit for a model that averages its ensemble on the logit scale,
  so the probability at 1.0 is the probability at 0.9 with the logit
  multiplied by 0.9. The script reads the source temperature, the library
  version, the checkpoint hash and `average_logits` from the scorer's own
  `node.json` rather than assuming them, refuses a model whose parameters
  do not say the logits are averaged (TabPFN is refused on that field,
  not by name), refuses a check scored by another version, another
  checkpoint or another temperature, and writes nothing unless every
  cell it shares with rows the library scored at the target holds the
  same rows and agrees on every one to 1e-6 on the probability. Against
  the probe's four cells of draw 20260911 the worst gap is 1.3e-7 on the
  probability and 1.2e-6 on the logit, the precision of a probability
  stored from single-precision arithmetic; the eight cells of draws
  20260912 and 20260913 are derived under the same library and
  checkpoint and are named as unchecked in `derive.json`. Twelve tests
  exercise the identity and each refusal.

  The level at 1.0, per draw. Mean probability over realised rate on the
  context rows: 0.991, 1.001 and 1.021 on the three draws, against 0.680,
  0.694 and 0.707 at 0.9. The probe's kill read on one draw holds on
  three: at 1.0 TabICL returns the realised rate on the rows it was
  shown, within two per cent on every draw. Out of time, observed over
  expected 1.14, 1.20 and 1.41 on the first draw, 1.14, 1.21 and 1.43 on
  the second, 1.06, 1.12 and 1.34 on the third, against the control's
  1.16 to 1.25, 1.24 to 1.31 and 1.48 to 1.57 on the same draws: the
  foundation model at 1.0 sits under the control on every cohort of
  every draw, and the rise across the three cohorts is the book's.

  What the three-draw mixture says, and what the single draw said. |log
  O/E| − scorecard −0.117 (−0.163 to −0.090), clear of zero and clear on
  every draw (−0.10, −0.09, −0.15); − control −0.091 (−0.098 to −0.080),
  clear on every draw; − full-pool GBM −0.086, clear. |Cox slope − 1|:
  the slopes at 1.0 are 1.13, 1.18 and 1.14 on the first draw, 1.03,
  1.07 and 1.04 on the second, 1.11, 1.17 and 1.12 on the third, each the
  slope at 0.9 over 0.9 as the identity requires. Against the scorecard
  −0.026 (−0.104 to +0.035), holding zero on the mixture; per draw,
  holding zero on the first and third and clear on the second, the draw
  whose slope is nearest one. Against the control −0.068 (−0.121 to
  −0.011), clear, where the single draw had −0.100; against the full-pool
  GBM +0.033 (−0.041 to +0.092), holding zero, where the single draw had
  +0.072 clear of zero on the wrong side. Murphy miscalibration at 1.0:
  0.00013 to 0.00027 on the three cohorts of every draw, against the
  control's 0.00012 to 0.00037 — level. Gini and PSI equal the rows at
  0.9 to the last digit, as a monotone map must leave them: +0.025
  against the scorecard, +0.015 against the control, PSI the lowest of
  the six. The flag on the calibration rows marks that the draws'
  intervals do not all overlap, not a disagreement of sign; the third
  draw is the one with the lower level throughout, for the control as
  much as for the foundation model.

  The sentence this run supports, with its temperature. At 1.0 TabICL's
  level on its own context rows is the realised rate on every draw; out
  of time the |log O/E| is below the scorecard's, the GBM's and the
  control's on every draw. The slope is the classical models' stretch,
  1.03 to 1.18, a tie with the scorecard's on |slope − 1|. The Murphy
  miscalibration is level with the control's. At 0.9 the same rows read as a two-thirds
  level and a slope near one. Both readings are in the table from here,
  per the amendment of 2026-09-06.

  `reliability.png` of this run is the figure the probe entry deferred:
  six panels on one axis at the credit scale, without the balanced rows,
  and the panel at 1.0 has the shape of the GBM's, near the diagonal in
  the low bins on the youngest cohort and above it throughout on the
  oldest.

  What this run cannot say. The derived rows on the two new draws rest
  on the identity holding on the first draw and on the library and
  checkpoint being the same, which the script checks by hash and version
  and not by scoring; a scored cell on one of those draws would close
  that. TabPFN at 1.0 is still one draw. Three cohorts, one build.

  Next: the eighth audit over the probe, the draws, this derivation and
  the three pooled intervals; then the grid, TabPFN at both settings and
  TabICL at the shipped one with the 1.0 rows derived by this script
  against the probe.

- **2026-09-06, late — the classical side of the expanding-arm grid, and
  the node bundles of every build.** Eight score runs and eight bundle
  runs, one per build that had none, all on one commit and a clean tree:
  [`experiments/2026-09-06-lc-2013h1e-scores`](../../experiments/2026-09-06-lc-2013h1e-scores),
  [`-2013h2e-scores`](../../experiments/2026-09-06-lc-2013h2e-scores),
  [`-2014h1e-scores`](../../experiments/2026-09-06-lc-2014h1e-scores),
  [`-2014h2e-scores`](../../experiments/2026-09-06-lc-2014h2e-scores),
  [`-2015h2e-scores`](../../experiments/2026-09-06-lc-2015h2e-scores),
  [`-2016h1e-scores`](../../experiments/2026-09-06-lc-2016h1e-scores),
  [`-2016h2e-scores`](../../experiments/2026-09-06-lc-2016h2e-scores),
  [`-2017h1e-scores`](../../experiments/2026-09-06-lc-2017h1e-scores),
  and the bundle of the same name beside each; 2015H1-E keeps the runs of
  2026-09-05. Every score run is `score_build.py` on one build: the
  scorecard, the full-pool GBM and the fifty-thousand-row control on all
  three context draws, every scored row and every training row kept.
  Every cohort aggregate of every unit was checked against the recorded
  grid runs (`lc-scorecard-byvalue3`, `lc-gbm-wide2`): 88 scorecard
  cells, 88 GBM cells and 264 control cells over the eight builds,
  largest gap 0.00e+00 on each — the same build on a later commit lands
  on the same numbers to the last bit. Every bundle was checked row by row against its score
  run: three contexts of 50,000 rows and every cohort at 20,000, every
  row and outcome identical. Fit times run from 229 s at 2013H1 to
  1,492 s at 2017H1 on this machine, the GBM's grid on the growing pool
  being the cost.

  What is now on disk for the nodes: nine bundles, 99 cohort cells per
  context draw, three draws each — 27 contexts per foundation model, as
  H1 to H3 are read. Packed as three archives
  under `data/derived/node/` by `pack_node_run.py`, which now carries a
  list of jobs: `outoftime-run-grid-e-tabpfn.tar.gz` for the Apple node
  (TabPFN at 0.9 and at 1.0, two passes per bundle, eighteen jobs), the
  same jobs as a zip for a CUDA machine, and
  `outoftime-run-grid-e-tabicl.zip` (TabICL at the shipped 0.9 on every
  bundle, plus one cell of one draw at 1.0 per bundle, so that the
  derivation of the 1.0 rows is checked on every build against rows the
  library scored there, and not on 2015H1-E alone). A node walks the
  list with `node_jobs.py`, one scorer call per job into its own output
  directory, and skips what a previous start finished.

  No foundation model has been run on any build but 2015H1-E.

- **2026-09-06, late — the bootstrap seed check on the three-draw
  pooling.**
  [`experiments/2026-09-06-lc-2015h1e-intervals-seeds`](../../experiments/2026-09-06-lc-2015h1e-intervals-seeds)
  (353 s, clean tree): `build_intervals.py` over the same four
  directories as `intervals-draws2`, with `--check-seeds
  20260906,20260907`, which repeats every pooling under each of those
  seeds beside the primary seed 20260905 and names each difference
  whose star changes. The primary rows are the rows of `intervals-draws2`
  to the last digit, as they have to be; the check rows are in
  `paired-seeds.csv` and the summary under `bootstrap.seed_check` in
  `intervals.json`. The eighth audit asked for this before any
  borderline star reaches the ledger.

  What it found. 42 of the 80 pooled differences carry a star under the
  primary seed; four change it under at least one of the two others,
  and the largest movement of any interval bound across seeds is 0.030,
  on the cohort-resampled TabICL − scorecard slope row. Three of the four are on the cohort-resampled
  pooling, which is the wider one by construction: |slope − 1| TabPFN −
  scorecard (−0.078, starred under 20260905 and 20260907, not under
  20260906), PSI TabICL − control (−0.010, lost under 20260907) and PSI
  TabICL − TabPFN (−0.011, lost under 20260906). The fourth is on the
  cohort-blocked pooling the kill criteria read, and it is the H2 row:
  **|slope − 1| TabICL − scorecard, −0.099, [−0.154, −0.012] under the
  primary seed, [−0.143, +0.001] and [−0.170, +0.013] under the two
  others.** The star was the seed's. TabPFN − scorecard on the same
  pooling, −0.078 [−0.151, −0.007], keeps its star under both check
  seeds. Everything else that is starred — every Gini and |log O/E|
  row, every PSI row on the blocked pooling, the GBM's slope against
  the scorecard — keeps its star under every seed.

  What it changes. The sentence "on |Cox slope − 1| both foundation
  models sit nearer one than the scorecard, clear of zero under both
  poolings" (this log, 2026-09-06) holds for TabPFN
  and does not hold for TabICL as a starred difference: TabICL's
  −0.099 is a difference whose interval touches zero under two of three
  bootstrap seeds, on three cohorts and three draws, and it is written
  from here as holding zero at the margin, with the three intervals.
  H2's verdict at the shipped setting is unchanged in direction and
  weaker in support: one of the two models clears the scorecard on the
  slope, the other sits at the edge. At 1.0 the row was already a tie
  (`intervals-tabicl-t1-2`). The grid, with 99 cells per draw instead of
  three, is where this resolves; nothing is added to the ledger from the
  falsifying build's slope rows.

  Next: the nodes — TabPFN at both settings on one device, TabICL at
  the shipped setting with a 1.0 cell per build for the derivation's
  check; the derived rows per bundle; the per-build poolings with
  `--check-seeds` on every one.

- **2026-09-08 to 2026-09-09 — the per-build poolings of the grid's
  TabICL side.** Nine runs of `build_intervals.py`, one per build of the
  expanding arm, each over the build's score run, its TabICL directory
  from the hosted notebook and its derived rows at 1.0, with
  `--check-seeds 20260906,20260907`:
  [`experiments/2026-09-09-lc-2013h1e-intervals-tabicl`](../../experiments/2026-09-09-lc-2013h1e-intervals-tabicl),
  [`2026-09-08-lc-2013h2e-intervals-tabicl`](../../experiments/2026-09-08-lc-2013h2e-intervals-tabicl),
  [`-2014h1e-`](../../experiments/2026-09-08-lc-2014h1e-intervals-tabicl),
  [`-2014h2e-`](../../experiments/2026-09-08-lc-2014h2e-intervals-tabicl),
  [`-2015h1e-`](../../experiments/2026-09-08-lc-2015h1e-intervals-tabicl),
  [`-2015h2e-`](../../experiments/2026-09-08-lc-2015h2e-intervals-tabicl),
  [`-2016h1e-`](../../experiments/2026-09-08-lc-2016h1e-intervals-tabicl),
  [`-2016h2e-`](../../experiments/2026-09-08-lc-2016h2e-intervals-tabicl),
  [`-2017h1e-`](../../experiments/2026-09-08-lc-2017h1e-intervals-tabicl).
  Recorded on clean trees, the five youngest at `265da43` and the four
  oldest at `a10d1e4`; 2013H1-E is dated by the day it finished. Five
  models per build: the scorecard, the full-pool GBM, the control on
  three draws, TabICL at the shipped 0.9 on the same three draws and its
  rows at 1.0 on them; 120 pooled differences per build, 80 on 2017H1-E,
  where the nearest three cohorts are every cohort and that pooling is
  not repeated. Wall from 386 s on three cohorts to 1,906 s on nineteen,
  on a machine in other use at the time, so the times are an order of
  magnitude and not a measurement.

  Two checks on the runs themselves. The nearest-three pooling of
  2015H1-E is the pooling of `intervals-seeds` on the same rows without
  TabPFN's cells: the 24 differences the two runs share agree on the
  point value to the last digit, and the interval bounds differ by up
  to 0.020. The H2 row, |slope − 1| TabICL − scorecard −0.099, reads
  [−0.151, +0.008] here against [−0.154, −0.012] there under the same
  primary seed — the star the seed check called the seed's is absent on
  this run as well. The seed check per build, with the number of
  differences starred under the primary seed, the number that change
  their star under a check seed, and the largest movement of any bound:

  | build | cohorts | starred | change | largest movement |
  |---|---|---|---|---|
  | 2013H1-E | 19 | 72 of 120 | 2 | 0.023 |
  | 2013H2-E | 17 | 58 of 120 | 3 | 0.040 |
  | 2014H1-E | 15 | 57 of 120 | 5 | 0.025 |
  | 2014H2-E | 13 | 63 of 120 | 0 | 0.026 |
  | 2015H1-E | 11 | 69 of 120 | 5 | 0.013 |
  | 2015H2-E | 9 | 63 of 120 | 0 | 0.018 |
  | 2016H1-E | 7 | 63 of 120 | 1 | 0.027 |
  | 2016H2-E | 5 | 59 of 120 | 1 | 0.034 |
  | 2017H1-E | 3 | 46 of 80 | 1 | 0.038 |

  What the nine say, on the cohort-blocked pooling and at the shipped
  setting unless said, with the cohort-resampled row named where it
  disagrees. The builds divide into the eight from 2013H2-E onward,
  which agree with each other, and 2013H1-E, which does not.

  *Discrimination.* Gini TabICL − scorecard is +0.022 to +0.043 on the
  eight, starred on every one; +0.003 on 2013H1-E, holding zero. Against
  the control, starred positive on seven, from +0.016 (2016H1-E) to
  +0.030 (2014H1-E); +0.001 on 2013H2-E, holding zero; −0.011 on
  2013H1-E, starred on the blocked pooling and holding zero on the
  resampled one. Against the full GBM the sign moves with the build:
  +0.013* at 2014H1-E, +0.007 at 2015H1-E (starred blocked, zero
  resampled), zero on five, −0.016* at 2013H1-E and −0.017* at 2017H1-E.
  The GBM's margin over the scorecard grows with its pool, +0.019 at
  2013H1-E to +0.043 at 2017H1-E; TabICL's margin over the scorecard does
  not, +0.039 at 2013H2-E and +0.026 at 2017H1-E, so the GBM passes it
  by the last build.

  *Level.* |log O/E| at 0.9: TabICL above every classical model on the
  eight, by +0.062 (2013H2-E, scorecard) to +0.318 (2017H1-E, GBM),
  every row starred; the per-cell median O/E is 1.42 to 1.94 against
  1.11 to 1.53 for the classical models. On 2013H1-E the sign turns:
  −0.061* against the scorecard, level with the GBM and the control. The
  six cohorts 2013Q3 to 2014Q4 have O/E below one for every model there
  (GBM 0.79 to 0.90, scorecard 0.85 to 1.01, TabICL 0.87 to 0.99): the
  pool of 2010 to 2012 originations defaulted at a higher rate than the
  cohorts that followed, every model over-predicts on them, and
  TabICL's shortfall lands it nearer one. On the context rows the ratio
  of mean pd to realised rate is 0.66 to 0.74 on all 27 contexts,
  computed from the reference files of the nine TabICL directories
  against the outcomes they carry and printed by no recorded run; the
  two-thirds level of the falsifying build is the level of every
  context in the arm. At 1.0, TabICL's |log O/E| is below the
  scorecard's on every build (−0.072 to −0.173, starred on the blocked
  pooling on all nine; the resampled row holds zero on 2013H1-E), below
  the GBM's on seven (2013H1-E holds zero, 2017H1-E's star depends on
  the seed) and below the control's on eight (2013H1-E holds zero).

  *Slope.* |slope − 1| TabICL − scorecard holds zero on the eight,
  −0.014 to +0.053, on both poolings. On 2013H1-E it is +0.119 [+0.099,
  +0.132], starred on both poolings, and TabICL is further from one
  than the GBM (+0.180*) and the control (+0.149*) there as well. Per
  cell TabICL's slope at 0.9 sits below one on every build, median 0.86
  to 0.93 on the eight and 0.72 on 2013H1-E (0.65 to 0.85), where every
  model is below one (GBM median 0.95, scorecard 0.86). At 1.0 the
  median is 0.95 to 1.03 on the eight and 0.80 on 2013H1-E; against the
  scorecard the difference holds zero on eight and is +0.038* on
  2013H1-E. H2's kill as amended, that the TFM's mean |slope − 1|
  exceeds the scorecard's beyond the interval pooled over the arm,
  lands on the wrong side on one build of nine at either temperature
  and inside the interval on the other eight.

  *Stability.* Per cell, TabICL's PSI is the smallest of the five
  models on the five builds from 2015H1-E (median 0.007 to 0.014,
  against 0.008 to 0.017 for the GBM and 0.024 to 0.036 for the
  scorecard), and it grows toward the old end of the arm: median 0.031
  at 2014H2-E, 0.039 at 2013H2-E, 0.123 at 2013H1-E with a largest cell
  of 0.206, against GBM medians of 0.010 to 0.013 on the same builds.
  The paired differences follow. TabICL − control is starred negative
  on four of the five youngest (−0.005 to −0.011; 2016H2-E −0.005 holds
  zero), zero on 2014H1-E, and starred positive on 2014H2-E (+0.020),
  2013H2-E (+0.034) and 2013H1-E (+0.111 [+0.106, +0.117], every draw's
  own interval between +0.104 and +0.117). H3's kill as amended, that
  the TFM's PSI exceeds the control's beyond the interval pooled over
  the arm, lands on the wrong side on the three oldest builds and
  inside the interval or on the right side on the six youngest. The movement
  is in TabICL's own level: its mean pd on the scored cohorts against
  its mean pd on the context rows (draw 20260911, the other draws
  within 0.001) is 0.0242 against 0.0185 on 2013H1-E, a third higher,
  0.0215 against 0.0179 on 2013H2-E, 0.0179 against 0.0153 on 2014H2-E,
  and within a tenth from 2015H1-E on. The reference rows and the
  cohorts are the same rows for every model, so what moves is TabICL's
  distribution and not the book's. What the oldest contexts have that
  the others do not, pools of 50,609 and 85,453 rows from the lender's
  first years scored up to five years out, is for the audit to weigh
  and not for this entry.

  What is not here. TabPFN: the Apple node's archive is not back. The
  arm-level pooling that H1 to H3 are written against: `build_intervals.py`
  takes one build and refuses more, and the paired difference of
  AUC-against-age slopes that H1 names is computed nowhere yet, so no
  kill criterion is read in this entry, only where each build's row
  lands relative to it. The ninth cold audit. These nine runs are
  superseded by the same nine with TabPFN's directories added, as
  `intervals-tfm` superseded `intervals-tabpfn`.

- **2026-09-11 — the TabPFN side of the grid, back from the Apple node,
  and the per-build poolings with both foundation models.** Two things
  recorded. First, the archive: eighteen jobs, TabPFN at the shipped 0.9
  and at softmax temperature 1.0 on every build of the expanding arm, on
  the control's three context draws, scored by one process on the Apple
  M4 Pro between 2026-09-06 and 2026-09-09, one directory per job with a
  hand manifest each
  ([`experiments/2026-09-11-lc-<build>-tabpfn-m4pro`](../../experiments/2026-09-11-lc-2015h1e-tabpfn-m4pro)
  and [`-tabpfn-t1-m4pro`](../../experiments/2026-09-11-lc-2015h1e-tabpfn-t1-m4pro))
  and an index directory holding the node's log, its job list, its
  tally and the archive-level checks
  ([`experiments/2026-09-11-lc-grid-e-tabpfn-m4pro`](../../experiments/2026-09-11-lc-grid-e-tabpfn-m4pro)).
  Every bundle hash equals the build's `bundle.json`; every part count
  equals the cell count; every scored row, its outcome and its age
  match the GBM rows of the build's score run and every reference row
  the control's of the same draw; the parameters are the defaults but
  for the temperature; all 54 repeats read 0.0. The scorer is the
  `score_context.py` of `fd5eadf`, byte for byte, the same file the
  TabICL grid ran. The 2015H1-E rows at 0.9 on draw 20260911 equal the
  falsifying half of 2026-09-06 (`lc-2015h1e-tabpfn-m4pro`, the same
  machine) to the last bit, 110,000 rows and no row differing: TabPFN
  on the Apple GPU is deterministic across runs and days. Against the
  T4 the same rows are not: on the draws 20260912 and 20260913 that
  `draws-colab-t4` scored at 0.9, every one of 120,000 scored rows
  differs, by 1.1e-4 on the probability on average and 2.4e-3 at most,
  and the reference rows by up to 0.053 on a single row; at 1.0 against
  probe 3 the picture is the same (1.6e-4 mean, 3.0e-3 largest). That
  is the device term the eighth audit named, now measured on identical
  rows, and it no longer enters any within-TabPFN difference: both
  temperatures come from the one device. The same-device logit rescale
  on 2015H1-E, logit at 1.0 against 0.9 times logit at 0.9, misses by
  7.7e-4 on average and 0.060 at most, so the rescale stays approximate
  for TabPFN and its 1.0 rows are scored, not derived. Three jobs carry
  the machine's incidents in their walls and not in their rows: the
  closed lid on job 5 (2014H1-E at 0.9, 24 cells at three times the
  undisturbed rate), a sleep on job 6 and another on job 14, each named
  in its manifest with its cells; no timing from the run is quotable,
  and the manifests say so. On the context rows TabPFN's mean
  probability over the realised rate is 0.681 to 0.712 at 0.9 and 0.981
  to 1.013 at 1.0 on all 27 contexts, the two-thirds level of the
  falsifying build on every context of the arm, as for TabICL.

  Second, the poolings: nine runs of `build_intervals.py`, one per
  build, over the build's score run, its TabICL directory and derived
  rows, and its two TabPFN directories, with `--check-seeds
  20260906,20260907`, recorded on a clean tree at `e7b617c`:
  [`experiments/2026-09-11-lc-2013h1e-intervals-grid`](../../experiments/2026-09-11-lc-2013h1e-intervals-grid),
  [`-2013h2e-`](../../experiments/2026-09-11-lc-2013h2e-intervals-grid),
  [`-2014h1e-`](../../experiments/2026-09-11-lc-2014h1e-intervals-grid),
  [`-2014h2e-`](../../experiments/2026-09-11-lc-2014h2e-intervals-grid),
  [`-2015h1e-`](../../experiments/2026-09-11-lc-2015h1e-intervals-grid),
  [`-2015h2e-`](../../experiments/2026-09-11-lc-2015h2e-intervals-grid),
  [`-2016h1e-`](../../experiments/2026-09-11-lc-2016h1e-intervals-grid),
  [`-2016h2e-`](../../experiments/2026-09-11-lc-2016h2e-intervals-grid),
  [`-2017h1e-`](../../experiments/2026-09-11-lc-2017h1e-intervals-grid).
  Seven models per build, 252 pooled differences (168 on 2017H1-E),
  wall 417 s to 2,858 s on a machine in other use. **These supersede
  the nine `intervals-tabicl` runs of 2026-09-08/09; cite these.** The
  TabICL rows here are those runs' rows: on every build the 120
  differences and every cell the two share agree on the value and on
  both interval bounds to the last digit, so the bootstrap does not
  depend on which models sit beside it, and the reading of the previous
  entry stands unchanged. The nearest-three pooling of 2015H1-E against
  `intervals-seeds`: the 24 differences without TabPFN agree to the
  last digit, the 16 with it move by up to 8.5e-4 on the value, which
  is the device term above (that run's draws 20260912 and 20260913
  were T4 rows); the one star that differs is the H2 TabICL row,
  −0.099 [−0.151, +0.008], already written as holding zero at the
  margin. The seed check per build:

  | build | cohorts | starred | change | largest movement |
  |---|---|---|---|---|
  | 2013H1-E | 19 | 176 of 252 | 5 | 0.026 |
  | 2013H2-E | 17 | 119 of 252 | 4 | 0.040 |
  | 2014H1-E | 15 | 105 of 252 | 12 | 0.032 |
  | 2014H2-E | 13 | 121 of 252 | 3 | 0.026 |
  | 2015H1-E | 11 | 116 of 252 | 5 | 0.020 |
  | 2015H2-E | 9 | 118 of 252 | 2 | 0.018 |
  | 2016H1-E | 7 | 115 of 252 | 8 | 0.026 |
  | 2016H2-E | 5 | 126 of 252 | 3 | 0.034 |
  | 2017H1-E | 3 | 89 of 168 | 3 | 0.037 |

  What the TabPFN rows say, on the cohort-blocked pooling and at the
  shipped setting unless said, the cohort-resampled row named where it
  disagrees. The temperature is a monotone map of the score, so the
  Gini and PSI rows are the same at 0.9 and at 1.0 and are given once.

  *Discrimination.* Gini TabPFN − scorecard is +0.018 (2015H2-E) to
  +0.040 (2013H2-E), starred on every build, 2013H1-E included (+0.031),
  where TabICL ties the scorecard. Against the control, starred on
  eight, +0.014 (2016H1-E) to +0.026 (2017H1-E); 2013H2-E +0.003 holds
  zero. Against the full GBM: zero on six, +0.012 starred on 2013H1-E,
  +0.009 on 2014H1-E starred on the blocked pooling and not the
  resampled one, −0.020 starred on 2017H1-E, where the GBM's pool has
  outgrown both foundation models. TabPFN against TabICL holds zero on
  eight builds (−0.005 to +0.005) and is +0.028 starred on 2013H1-E.

  *Level.* At 0.9 TabPFN's |log O/E| is above every classical model on
  all nine builds, every row starred: +0.138 (2013H1-E) to +0.370
  (2016H1-E) against the scorecard, +0.199 to +0.414 against the GBM,
  +0.203 to +0.387 against the control. The sign holds on 2013H1-E,
  where TabICL's turned: TabPFN's per-cell median O/E is 1.52 there and
  1.64 to 2.17 on the eight, against 1.15 to 1.94 for TabICL and 1.10
  to 1.53 for the classical models, and TabICL − TabPFN is −0.090 to
  −0.199 starred on every build. At 1.0 the level is the classical
  level: per-cell median O/E 1.07 to 1.48; TabPFN − scorecard −0.005 to
  −0.078, starred negative on six builds and holding zero on 2014H2-E,
  2015H1-E and 2016H1-E; against the GBM zero on six, +0.039 and +0.046
  starred on 2016H1-E and 2017H1-E, −0.018 starred on 2013H1-E on the
  blocked pooling only; against the control zero on five and within
  ±0.025 on the four that star. TabICL at 1.0 sits nearer one than
  TabPFN at 1.0 by 0.046 to 0.138, starred on eight; on 2013H1-E the two
  are level. TabPFN's mean probability on the scored cohorts against
  its mean on the context rows (draw 20260911) is 0.90 to 1.04 on every
  build at either temperature, 1.00 on 2013H1-E: the third that
  TabICL's level rises by on that build has no counterpart in TabPFN.

  *Slope.* |slope − 1| TabPFN − scorecard at 0.9 holds zero on eight
  builds, −0.034 to +0.039, on both poolings; on 2013H1-E it is +0.077
  starred on both, and TabPFN is further from one than the GBM
  (+0.138) and the control (+0.107) there as well, as TabICL is. Per
  cell TabPFN's slope at 0.9 sits below one on every build, median 0.90
  to 0.98 on the eight and 0.78 on 2013H1-E. At 1.0 the median is 1.00
  to 1.09 on the eight and 0.86 on 2013H1-E, and TabPFN − scorecard
  holds zero on all nine (−0.028 to +0.027; 2013H1-E −0.009). Against
  the GBM at 1.0: +0.052 starred on 2013H1-E, −0.085 starred on
  2013H2-E, zero on seven. Against TabICL at 1.0: −0.047 starred on
  2013H1-E, TabPFN the nearer, zero on the eight. H2's kill as amended
  lands on the wrong side for TabPFN on one build of nine at 0.9 and on
  none at 1.0.

  *Stability.* Per cell TabPFN's PSI median is 0.007 to 0.024 on the
  nine builds against 0.008 to 0.017 for the GBM, and it does not grow
  toward the old end of the arm: 0.010 on 2013H1-E with a largest cell
  of 0.029, where TabICL's median is 0.123 and its largest cell 0.206.
  The paired rows: TabPFN − scorecard negative and starred on every
  build (−0.012 to −0.047). TabPFN − control holds zero on five builds
  and is starred negative and small on four (−0.002 on 2013H2-E and
  2014H2-E, −0.004 on 2016H1-E, −0.008 on 2016H2-E, every one holding
  zero on the resampled pooling). Its largest positive value, +0.005
  on 2014H1-E, holds zero. TabPFN − GBM: zero on six, −0.003 on
  2013H1-E and −0.008 on 2016H2-E starred, +0.008 on 2017H1-E starred, its
  resampled row starred under two of three seeds. TabICL − TabPFN is +0.113 on 2013H1-E,
  +0.036 on 2013H2-E and +0.022 on 2014H2-E, starred, and within ±0.010,
  starred or not, from 2014H1-E on. H3's kill as amended lands inside the interval or
  on the right side for TabPFN on every build; the wrong side on the
  three oldest builds is TabICL's alone.

  What is not here. The arm-level pooling H1 to H3 are written
  against, and H1's AUC-against-age slope difference, are still
  computed nowhere; this entry, like the previous one, reads where each
  build's row lands relative to the criteria and reads no criterion.
  The ninth cold audit, over the whole grid. Why 2013H1-E is the odd
  build for TabICL and not for TabPFN is for the audit to weigh and not
  for this entry.

- **2026-09-11, late, to 2026-09-12 — the arm-level pooling, and the
  three kill criteria read as written.** One run of `arm_intervals.py`
  over the sources of the nine per-build poolings, recorded on a clean
  tree at `af04f93`:
  [`experiments/2026-09-11-lc-arm-e-intervals`](../../experiments/2026-09-11-lc-arm-e-intervals).
  Seven models on the 99 cells of the expanding arm, nine builds of
  nineteen to three cohorts, 33,660,000 scored rows that are 380,000
  distinct loans: a cohort's 20,000 rows are the same rows on every
  build that scores them, so each of the 200 resamples draws one index
  per cohort and applies it to every build's cell of that cohort, and
  the context draw is chosen once per resample for every model and
  every build. Three poolings as on one build — every cell, the
  youngest three cohorts of every build, every cell with the cohorts
  resampled — the per-draw rows, and `--check-seeds 20260906,20260907`.
  The run also reports every statistic per build under the shared
  resample, and those rows equal the nine recorded per-build poolings
  on every value to the last digit, 1,904 rows over the first two
  poolings; only the intervals differ, by the resample. The arm's
  statistic for the four cell metrics is the mean over the 99 cells,
  so 2013H1-E's nineteen cells weigh six times 2017H1-E's three. The
  statistic H1 names, computed here for the first time, is the
  least-squares slope of each cell's AUC on its age in quarters with
  one intercept per build, on the arm and per build. The seed check:
  175 of 315 arm-level differences starred under the primary seed and
  9 change their star under one of the two others; 995 of 2,205 at
  every scope, 58 change; the largest movement of a bound 0.061. Wall
  14,626 s.

  *H1, discrimination decay.* No model's arm slope leaves zero: the
  scorecard −0.00046 [−0.00150, +0.00064] of AUC per quarter, the GBM
  −0.00022, the control −0.00033, TabICL +0.00022, TabPFN +0.00008,
  each interval holding zero, and the largest of them is 0.009 of AUC
  over the nineteen quarters of the longest build. The per-cell plot
  ([`auc-age.png`](../../experiments/2026-09-11-lc-arm-e-intervals/auc-age.png))
  shows the lines of neighbouring builds repeating one another's shape
  shifted by the builds' spacing: what moves a cell's AUC is its
  cohort, the same for every model and every build, and not its age.
  The paired differences against the control: TabICL +0.00055
  [+0.00020, +0.00088] and TabPFN +0.00041 [+0.00007, +0.00075], both
  starred with the cohorts held fixed and on each of the three context
  draws, both holding zero with the cohorts resampled ([−0.00020,
  +0.00107] and [−0.00032, +0.00091]). Per build, TabICL − control is
  starred on 2013H2-E, 2014H1-E and 2014H2-E (+0.0006 to +0.0009) and
  holds zero on the other six; TabPFN − control is starred on 2014H2-E
  and 2015H1-E (+0.0012, +0.0009) and holds zero on seven; on 2017H1-E,
  three cohorts, they read −0.003 and −0.004 with intervals wider than
  any value on the arm. Against the scorecard +0.00068 and +0.00054,
  starred; against the GBM +0.00043 starred and +0.00029 holding zero.
  The classical differences among themselves hold zero (GBM −
  scorecard +0.00024, control − scorecard +0.00013, control − GBM
  −0.00011), as does TabICL − TabPFN (+0.00014). H1's kill as amended,
  the foundation model's slope more negative than the control's beyond
  the interval, does not fire for either model: the sign is the other
  way. Its second branch, that the axis is uninformative if every
  pair's difference lies inside its interval, is read per pooling: ten
  of the 21 differences leave zero with the cohorts held fixed and none
  of the ten favours a classical model, two of the 21 with the cohorts
  resampled (TabICL − scorecard at either temperature), none on the
  youngest three cohorts. Every slope difference is of the order of
  half a thousandth of AUC per quarter, a hundredth over the arm's
  longest trajectory.

  *H2, the slope at the shipped setting.* The arm mean of |Cox slope
  − 1|: scorecard 0.092, GBM 0.088, control 0.145, TabPFN 0.113, TabICL
  0.139; at 1.0, TabICL 0.087 and TabPFN 0.088. TabICL − scorecard is
  +0.047 [+0.012, +0.068], starred with the cohorts held fixed, starred
  with them resampled ([+0.007, +0.068]), starred on each context draw
  (+0.037, +0.049, +0.055) and under all three bootstrap seeds. **H2's
  kill as amended fires for TabICL at 0.9 on the arm.** Its per-build
  rows are +0.119 starred on 2013H1-E and zero on the eight others
  (−0.014 to +0.053, positive on seven of them); the arm's row is
  2013H1-E's nineteen cells with the eight builds' lean behind them.
  TabPFN − scorecard is +0.021 [−0.004, +0.042]: it holds zero under
  the primary seed and 20260906 and is starred under 20260907 ([+0.000,
  +0.037]), holds zero with the cohorts resampled ([−0.008, +0.041])
  and on two draws of three (the third, 20260913, +0.029 [+0.002,
  +0.042]). It holds zero at the margin, and the kill does not fire
  for TabPFN. At 1.0 both hold zero: TabICL −0.006 [−0.016, +0.011],
  TabPFN −0.005 [−0.017, +0.012]. The control is further from one than
  the scorecard, +0.053 [+0.019, +0.101] starred, and further than
  either foundation model at 1.0 (−0.059 and −0.058, starred, the
  draws disagreeing on how far); TabICL − TabPFN at 0.9 is +0.026
  [+0.014, +0.033], starred.

  *H3, stability.* The arm mean PSI against the model's own reference:
  scorecard 0.040, GBM 0.015, control 0.015, TabPFN 0.015, TabICL
  0.043. TabICL − control is +0.028 [+0.024, +0.032], starred on all
  three poolings and on every draw (+0.025 to +0.031). **H3's kill as
  amended fires for TabICL on the arm.** Per build the sign turns with
  the build's age: +0.111, +0.034 and +0.020 starred on 2013H1-E,
  2013H2-E and 2014H2-E, zero on 2014H1-E, and starred negative, −0.005
  to −0.011, on 2015H1-E, 2015H2-E, 2016H1-E and 2017H1-E, with 2016H2-E
  (−0.005) holding zero; the arm's row sets the three oldest builds' 49
  cells against the other six builds' 50. TabICL − scorecard, +0.003,
  holds zero: on the arm TabICL's score distribution moves as much as
  the scorecard's. TabPFN − control is −0.0008 [−0.0033, +0.0013],
  holding zero with the cohorts fixed and resampled; on the youngest
  three cohorts of every build it is +0.0029 [+0.0005, +0.0049],
  starred, with the draws disagreeing on the sign (−0.0031, −0.0002,
  +0.0011). The kill does not fire for TabPFN. TabPFN − scorecard is
  −0.025, starred; TabPFN − GBM +0.0001 holds zero.

  *Discrimination and level, the arm rows.* Gini: TabPFN − scorecard
  +0.030 [+0.026, +0.034] and TabICL − scorecard +0.026 [+0.022,
  +0.030]; against the control +0.018 and +0.014; all four starred.
  Against the GBM +0.003 and −0.001, holding zero. TabPFN − TabICL
  +0.004 [+0.002, +0.006], starred; control − GBM −0.015, starred.
  Level, |log O/E| at 0.9: TabPFN − scorecard +0.272 and TabICL −
  scorecard +0.131, starred, the arm means 0.595 and 0.454 against
  0.323 for the scorecard and 0.270 for the GBM. At 1.0: TabICL −0.124
  and TabPFN −0.052 against the scorecard, starred; TabPFN level with
  the GBM and the control (+0.000, −0.001, holding zero), TabICL below
  both (−0.071, −0.072, starred).

  On the arm, then: both foundation models discriminate above the
  scorecard and the control and level with the GBM, and neither ages
  faster than the control. TabPFN's slope row and stability row hold
  zero against the criteria's comparators on every pooling but one
  marginal row each. TabICL's fail H2 at the shipped setting and H3,
  and its per-build rows put both failures in the oldest contexts and
  nowhere else. Whether an arm statistic that gives 2013H1-E nineteen
  cells of 99 is what the pre-registration meant by "pooled over
  builds", read beside the per-build rows recorded with it, is for the
  audit to weigh and not for this entry.

  What is not here. The ninth cold audit, over the grid and this run.
  The two-row table. Arm R.

- **2026-09-12 — the CPU side of the rolling arm.** Nine score runs and
  nine bundles, `score_build.py` and `export_context.py` with `--arm R` on
  the same as-of dates as the expanding arm, recorded one after another on
  a clean tree:
  [`experiments/2026-09-12-lc-2013h1r-scores`](../../experiments/2026-09-12-lc-2013h1r-scores)
  to [`-2017h1r-scores`](../../experiments/2026-09-12-lc-2017h1r-scores)
  and [`-2013h1r-bundle`](../../experiments/2026-09-12-lc-2013h1r-bundle)
  to [`-2017h1r-bundle`](../../experiments/2026-09-12-lc-2017h1r-bundle).
  The four-quarter pools run 31,016 rows at 2013H1-R to 472,734 at
  2017H1-R; every cohort aggregate of the scorecard, the GBM and the
  control equals the recorded grid runs of 2026-09-04 to 0.00e+00 on every
  build, and every bundle's context and cohort rows are the score run's,
  row for row with the same outcome. On 2013H1-R the pool is below the
  50,000-row cap, so the control's three contexts and the foundation
  models' three draws are the whole pool, 31,016 rows each, and the seed
  is inert there, as the first kill criterion says of that build; on
  2013H2-R the pool of 53,367 rows clears the cap by 6.7% and the three
  draws are distinct. Walls 181 s to 445 s per score run and about 120 s
  per bundle, on a machine running the arm-level pooling at the same time.
  The two node archives, `outoftime-run-grid-r-tabpfn.tar.gz` for the
  Apple node with TabPFN at 0.9 and at 1.0 on every bundle, and
  `outoftime-run-grid-r-tabicl.zip` for a T4 with TabICL at 0.9 and one
  cell at 1.0 per bundle for the derivation's check, are packed with the
  job lists the expanding arm's archives carried. Nothing of arm R is
  scored by a foundation model yet, and H4 is read on nothing.

- **2026-09-12 — the arm-level pooling again, with what the ninth audit
  asked for.** One run of the extended `arm_intervals.py` (`a9edd51`) over
  the same nine sources, recorded on a clean tree:
  [`experiments/2026-09-12-lc-arm-e-intervals`](../../experiments/2026-09-12-lc-arm-e-intervals),
  wall 16,702 s beside two other batches on the same machine. **It
  supersedes the recording of 2026-09-11; cite it.** Every row that
  recording holds is here to the last bit, the value and both interval
  bounds on all 3,360 rows, so the reading in the entry above stands
  unchanged, and the per-build rows equal the nine per-build poolings on
  1,904 rows as before. Three things are new. The slope of AUC on age is
  fitted twice, with one intercept per build as before and with one
  intercept per cohort; the stability index is read twice, against the
  model's training reference as amended and against the same model's
  scores on the build's first scored cohort, the first cohort's own cells
  left out; and every statistic is reported under a third scope, the mean
  over builds with every build weighted alike, beside the mean over cells.
  The seed check now covers 441 arm differences, 247 starred under the
  primary seed and 15 changing their star under one of the other two.

  *H1 under the second identification.* With one intercept per cohort,
  every model's AUC falls with age: the scorecard −0.00282 [−0.00319,
  −0.00244] per quarter, the GBM −0.00278, the control −0.00181, TabPFN
  −0.00196, TabICL −0.00267, every interval clear of zero, a twentieth of
  AUC over the nineteen quarters of the arm for the scorecard. The
  per-cohort figure
  ([`auc-age-cohort.png`](../../experiments/2026-09-12-lc-arm-e-intervals/auc-age-cohort.png))
  shows the same cohort scored at up to nine ages falling for every
  model, the youngest cohorts falling from the highest level. The paired
  differences against the control: TabICL −0.00087 [−0.00136, −0.00051],
  starred with the cohorts held fixed and resampled and on each of the
  three draws (−0.00072, −0.00117, −0.00071); TabPFN −0.00016 [−0.00046,
  +0.00008], holding zero on both poolings and on two draws of three.
  TabPFN's slope is shallower than the scorecard's (+0.00086) and the
  GBM's (+0.00082), starred; TabICL's is level with both (+0.00015,
  +0.00011); the control's is shallower than the scorecard's (+0.00101,
  starred), the GBM's is not (+0.00004); TabICL − TabPFN −0.00071,
  starred. On the youngest three cohorts every difference holds zero.
  Under the identification the pre-registration named, one intercept per
  build, the rows are those of the entry above: TabICL − control
  +0.00055 and TabPFN − control +0.00041, starred with the cohorts fixed,
  holding zero with them resampled; with every build weighted alike
  +0.00031 [−0.00049, +0.00125] and −0.00002 [−0.00090, +0.00107], both
  holding zero. H1 read as the note of 2026-09-12 says: the criterion's
  statistic does not fire for either model; the reading added after the
  audit fires for TabICL, whose AUC falls with age at fixed calendar
  faster than the control's on the identical rows, and holds zero for
  TabPFN; so H1 supports at most the weaker claim for TabICL, and for
  TabPFN neither identification puts it on the wrong side.

  *H3 under the second reference.* Against the build's first scored
  cohort the arm means are scorecard 0.0279, GBM 0.0178, control 0.0173,
  TabPFN 0.0155, TabICL 0.0138, each interval within 0.0026 of its value.
  TabICL − control is −0.0034 [−0.0051, −0.0021] with the cohorts held
  fixed, −0.0034 [−0.0070, −0.0001] with them resampled, its star there
  lost under one of the two check seeds, and starred negative on every
  draw (−0.0047, −0.0032, −0.0024); with every build weighted alike
  −0.0023 [−0.0034, −0.0014]; on the youngest three cohorts +0.0013
  [+0.0005, +0.0021], the other sign. Per build it is negative on seven
  builds, starred on five, and positive and starred on 2015H2-E (+0.0042)
  and 2017H1-E (+0.0029). TabPFN − control −0.0018 [−0.0036, −0.0006]
  with the cohorts fixed, holding zero resampled and with the builds
  weighted alike, +0.0018 starred on the youngest three. Both foundation
  models are below the scorecard by 0.012 to 0.014, starred everywhere,
  and TabICL is below TabPFN by 0.0016, starred. Under the amended
  reference the equal-weight rows are TabICL − control +0.0146 [+0.0121,
  +0.0179], starred, and TabPFN − control −0.0012 [−0.0036, +0.0004],
  holding zero: TabICL's kill as amended fires under both weightings, half
  as large when 2013H1-E counts once, and against a reference that holds
  no fitted rows its sign reverses on the arm and reverses again on the
  youngest cohorts, where every model is a quarter from the reference it
  was fitted or conditioned near.

  *H2 and the discrimination rows with every build weighted alike.*
  |Cox slope − 1| TabICL − scorecard at 0.9 is +0.0346 [−0.0101, +0.0654],
  holding zero, against +0.047 starred with the cells weighted; TabPFN −
  scorecard +0.0087 [−0.0234, +0.0380]; at 1.0 −0.0149 and −0.0075, both
  holding zero. H2's firing for TabICL at the shipped setting therefore
  depends on the weighting: it fires on the mean over cells, where
  2013H1-E holds nineteen of 99, and holds zero on the mean over builds.
  Gini with the builds weighted alike: TabICL and TabPFN above the control
  by +0.018 and +0.019 and above the scorecard by +0.026 and +0.027, all
  starred, as with the cells weighted.

  What is not here. Which of the two weightings and which of the two
  identifications the paper leads with; the note of 2026-09-12 fixes the
  criterion's statistic and the audit's readings are beside it. Arm R.

- **2026-09-14 — TabICL on the rolling arm, and its rows at 1.0.**
  [`experiments/2026-09-13-lc-grid-r-tabicl-colab-t4`](../../experiments/2026-09-13-lc-grid-r-tabicl-colab-t4)
  indexes eighteen passes on a hosted T4: TabICL at 0.9 on the nine
  rolling-arm bundles, every cohort under the three draws
  ([`-2013h1r-tabicl-colab-t4`](../../experiments/2026-09-13-lc-2013h1r-tabicl-colab-t4)
  to [`-2017h1r-tabicl-colab-t4`](../../experiments/2026-09-13-lc-2017h1r-tabicl-colab-t4)),
  and one cell at 1.0 per bundle for the derivation's check
  (`…-tabicl-t1-check-colab-t4`). Every part holds the bundle's rows with
  their outcomes, with no mismatch against the build's score run; the
  first cohort of every draw scored a second time agrees to 0.0; tabicl
  2.1.1 on the checkpoint the expanding arm loaded. The pass on 2015H1-R
  was interrupted and resumed on a fresh machine. The runner kept the
  parts already written and scored the rest, and its repeat across the two
  machines agrees to 0.0. The seconds the notebook recorded are a shared
  host's and are not quoted.

  Nine runs of `derive_temperature.py`, one per build, over the pass at 0.9
  and checked against the cell at 1.0, recorded on a clean tree at
  `0c1f005`:
  [`experiments/2026-09-14-lc-2013h1r-tabicl-t1-derived`](../../experiments/2026-09-14-lc-2013h1r-tabicl-t1-derived)
  to [`-2017h1r-tabicl-t1-derived`](../../experiments/2026-09-14-lc-2017h1r-tabicl-t1-derived).
  70,000 rows are checked per build, the check cohort with the context;
  on 2013H1-R, whose context is the whole 31,016-row pool, 51,016. No
  checked row is further than 2.2 × 10⁻⁷ from the probability the library
  scored at 1.0. The derived files hold 330,000 rows at 2017H1-R to
  1,233,048 at 2013H1-R. Row-level files stay on the machine, as for every
  score file of this book.

  What is not here. TabPFN on the rolling arm, still on the Apple node;
  H4 and the arm's pooling wait on it.

- **2026-09-15 to 2026-09-16 — the rolling arm scored by both foundation models, pooled per build and over the arm.**
  *TabPFN on the rolling arm.*
  [`experiments/2026-09-15-lc-grid-r-tabpfn-m4pro`](../../experiments/2026-09-15-lc-grid-r-tabpfn-m4pro)
  indexes eighteen jobs on the Apple node: TabPFN at 0.9 and at 1.0 on the
  nine rolling-arm bundles, every cohort under the three context draws
  ([`-2013h1r-tabpfn-m4pro`](../../experiments/2026-09-15-lc-2013h1r-tabpfn-m4pro)
  to [`-2017h1r-tabpfn-m4pro`](../../experiments/2026-09-15-lc-2017h1r-tabpfn-m4pro)
  and [`-2013h1r-tabpfn-t1-m4pro`](../../experiments/2026-09-15-lc-2013h1r-tabpfn-t1-m4pro)
  to [`-2017h1r-tabpfn-t1-m4pro`](../../experiments/2026-09-15-lc-2017h1r-tabpfn-t1-m4pro)).
  The runner walked the eighteen jobs in order in one call, the first
  finishing 2026-09-12T18:04:23Z and the last 2026-09-15T01:26:52Z, none
  skipped or resumed; the scorer inside the job archive is byte-identical to
  `scripts/score_context.py`, unchanged since `fd5eadf`. On all eighteen the
  bundle hashes in `node.json` equal the bundle's `bundle.json`; the part
  files equal the cell records in number and concatenate to the score and
  reference files; every scored (cohort, row), its outcome and its age match
  the GBM rows of the build's score run and every reference row matches the
  control's reference of the same draw, with zero mismatches; the first
  cohort of every draw scored a second time agrees to 0.0 on all 54 repeats.
  The library, the checkpoint and the device are the expanding arm's:
  tabpfn 8.5.0 on torch 2.14.0 over Metal, `categorical_features_indices`
  [6, 13, 19], `n_estimators` auto, `balance_probabilities` false. On
  2013H1-R the context is the whole 31,016-row pool under each draw; on the
  other eight it is 50,000 rows. No time from this run is a measurement: the
  eighteen jobs sum to 57.9 h of wall on a machine whose other use over the
  stretch is not checked. What is checked is that no cell runs more than
  1.054 times the median of its kind; a 20,000-row cohort cell at a
  50,000-row context ran 311 to 337 s against the 319.5 s the idle-machine
  timing of 2026-09-04 recorded, and a cell at the 31,016-row context 140 to
  141 s.

  *The contrast beside the arm, recorded again.*
  [`experiments/2026-09-15-lc-arm-contrast-byvalue`](../../experiments/2026-09-15-lc-arm-contrast-byvalue),
  `arm_contrast.py` on a clean tree at `2a09188`, 150 s, on the grid every
  recorded run uses, whose first cohort is 2010Q2. Its expanding and
  four-quarter pools are the score runs' own training rows on all nine
  builds, 50,609 and 31,016 at 2013H1 to 1,108,732 and 472,734 at 2017H1, so
  the share it prints is the share the runs hold: 61.3% at 2013H1, 63.5% at
  2014H1 at the top, 42.6% at 2017H1 at the bottom, and the mean training
  row 1.74 quarters younger at 2013H1 to 4.09 at 2017H1. The record of
  2026-09-04, measured with the first cohort at 2010Q1 and expanding pools
  2,172 rows larger, reads the share 0.09 of a point lower at 2017H1 to 2.53
  lower at 2013H1, and the age gap 1.99 to 4.13; as the note of 2026-09-15
  says, this record is the one printed beside H4.

  *The nine per-build readings.* `build_intervals.py` on each rolling
  build's five sources, the score run, the TabICL pass, TabICL's derived
  rows at 1.0 and the two TabPFN passes, recorded on a clean tree at
  `5724c4d` for 2013H1-R and 2013H2-R, `fd0818a` for 2014H1-R and 2014H2-R
  and `c599ebb` for the other five, the script changing between the second
  and the third in how it takes the floors of the second book, which no run
  here passes:
  [`experiments/2026-09-15-lc-2013h1r-intervals-grid`](../../experiments/2026-09-15-lc-2013h1r-intervals-grid)
  to [`-2017h1r-intervals-grid`](../../experiments/2026-09-15-lc-2017h1r-intervals-grid),
  walls 5,213 s at 2013H1-R to 709 s at 2017H1-R, 200 resamples under
  20260905 and every pooling again under 20260906 and 20260907. No Cox fit
  failed to finish on any cell of any build. TabICL's rows at 1.0 are
  derived: 51,016 rows checked against the library's own cells at 1.0 on
  2013H1-R and 70,000 on each other build, the largest gap on the
  probability 1.0 × 10⁻⁷ to 2.2 × 10⁻⁷, and 10 to 58 cells a build
  unchecked by row, printed beside every statistic that reads them. Per
  build, 3 to 12 differences change their star under a check seed.

  *The arm pooling.*
  [`experiments/2026-09-16-lc-arm-r-intervals`](../../experiments/2026-09-16-lc-arm-r-intervals),
  `arm_intervals.py` over the nine, on a clean tree at `c599ebb`, wall
  27,811 s: 99 cells over 19 cohorts, 33,660,000 scored rows on 380,000
  distinct, seven models with three draws each for the five seeded ones,
  200 resamples under 20260905 with the cohorts held fixed and resampled,
  every pooling again under the two check seeds, and every pooling with
  each draw held fixed. No Cox fit left any cell out. The arm reads as the
  expanding arm read on 2026-09-11 and 2026-09-12, with the same
  statistics, the same scopes and the same marks.

  *Ranking.* Gini against the scorecard over the 99 cells: TabPFN +0.0283
  [+0.0245, +0.0320], TabICL +0.0240 [+0.0206, +0.0273], the full-pool GBM
  +0.0203 [+0.0171, +0.0233], the control +0.0107 [+0.0064, +0.0147].
  Against the full-pool GBM the foundation models read +0.0080 [+0.0050,
  +0.0113] and +0.0037 [+0.0009, +0.0066], and against the control +0.0176
  [+0.0151, +0.0204] and +0.0133 [+0.0096, +0.0165], every interval clear of
  zero; the control against the full-pool GBM −0.0096 [−0.0120, −0.0066],
  its three draws disagreeing. Between TabPFN's two settings Gini differs by
  2 × 10⁻⁵ on the arm, and TabICL's rows at 1.0 are the exact scale of its
  rows at 0.9.

  *Level.* |log O/E| against the scorecard at 0.9: TabPFN +0.2470 [+0.2356,
  +0.2612], TabICL +0.1314 [+0.1227, +0.1466], where the full-pool GBM reads
  −0.0344 [−0.0358, −0.0302] and the control −0.0354 [−0.0418, −0.0211]. At
  1.0 the sign turns: TabICL −0.0789 [−0.0939, −0.0594], TabPFN −0.0440
  [−0.0546, −0.0298], both clear of zero on the other side; against the
  control at 1.0, −0.0435 [−0.0541, −0.0334] and −0.0086 [−0.0138, −0.0034],
  and TabPFN against the full-pool GBM −0.0096 [−0.0199, +0.0019], holding
  zero.

  *H2, the Cox slope.* |slope − 1| against the scorecard at 0.9: TabPFN
  +0.0141 [−0.0064, +0.0266], holding zero; TabICL +0.0440 [+0.0166,
  +0.0578], starred on the wrong side, as on the expanding arm. At 1.0
  TabICL reads −0.0142 [−0.0264, −0.0022], starred, and TabPFN −0.0201
  [−0.0359, +0.0000], holding zero at its bound. Against the control every
  foundation-model row holds zero at either temperature: +0.0087 [−0.0329,
  +0.0399] and +0.0386 [−0.0086, +0.0706] at 0.9, −0.0255 [−0.0531,
  +0.0050] and −0.0196 [−0.0495, +0.0117] at 1.0. Against the full-pool
  GBM at 0.9 both sit above, +0.0393 [+0.0070, +0.0645] and +0.0692
  [+0.0308, +0.0967], starred; the full-pool GBM itself sits below the
  scorecard, −0.0251 [−0.0416, −0.0082]. With every build weighted alike
  TabPFN against the scorecard reads +0.0343 [+0.0004, +0.0467], its star
  lost under 20260906.

  *H3, stability.* PSI against the amended reference, minus the
  scorecard's: TabICL +0.0323 [+0.0285, +0.0357], TabPFN −0.0078 [−0.0093,
  −0.0064]; against the control +0.0435 [+0.0383, +0.0488] and +0.0034
  [+0.0005, +0.0061], both starred above it, TabPFN's on each draw held
  fixed as well ([+0.0055, +0.0062], [+0.0005, +0.0013], [+0.0031,
  +0.0039]). H3's criterion is pooled over the expanding arm and is not
  read here; the rolling arm's rows sit beside it. The temperature moves no
  PSI row of TabICL and moves TabPFN's by 3 × 10⁻⁵. On the second reading,
  against the build's first scored cohort, every model reads below the
  scorecard: the full-pool GBM −0.0076, the control −0.0079, TabPFN −0.0092
  [−0.0101, −0.0084], TabICL −0.0105 [−0.0117, −0.0095]; against the control
  TabICL −0.0026 [−0.0050, −0.0003], starred, and TabPFN −0.0013 [−0.0036,
  +0.0011], holding zero.

  *H1, the slope of AUC on age.* With one intercept per build the arm
  reads −0.00062 [−0.00164, +0.00047] a quarter for the scorecard, −0.00053
  for the full-pool GBM, −0.00066 for the control, −0.00032 [−0.00137,
  +0.00083] for TabICL and −0.00024 [−0.00119, +0.00076] for TabPFN, every
  interval holding zero. The differences from the scorecard are +0.00030
  [−0.00008, +0.00067] for TabICL and +0.00038 [+0.00002, +0.00076] for
  TabPFN, the second starred under the primary seed and holding zero under
  20260907; from the control +0.00034 [−0.00007, +0.00084] and +0.00042
  [+0.00004, +0.00079]. With one intercept per cohort every model's AUC
  falls with age: the scorecard −0.00291 [−0.00325, −0.00252], the full-pool
  GBM −0.00299, the control −0.00228 [−0.00273, −0.00184], TabICL −0.00283
  [−0.00317, −0.00243], TabPFN −0.00220 [−0.00254, −0.00182]; against the
  control TabICL −0.00055 [−0.00088, −0.00015], starred on the wrong side as
  on the expanding arm, and TabPFN +0.00008 [−0.00023, +0.00045], holding
  zero.

  *What the seeds and the draws move.* 245 of the 441 arm differences are
  starred under the primary seed and 11 change their star under a check
  seed; over every scope 1,395 of 2,961 are starred and 67 change; the
  largest movement of an interval bound is 0.0536, and every such row is
  named in the run's output. Of the 147 differences at the arm's scope with
  the cohorts held fixed, 40 carry the mark that the three context draws
  disagree: eighteen on the population stability index and eight on its
  second reading, nine on the level, two on the Cox slope, and one each on
  Gini and on the two slopes of AUC on age.

  Not here: the comparison between the arms, which H4 is written on and
  which is read on the two arms' cells together.

- **2026-09-16 — H4, the two arms against each other.**
  [`experiments/2026-09-16-lc-between-arm-intervals`](../../experiments/2026-09-16-lc-between-arm-intervals),
  `between_arm_intervals.py` over the nine expanding-arm readings of
  2026-09-11 and the nine rolling-arm readings above, with the contrast of
  `lc-arm-contrast-byvalue` beside every build date, recorded on the Apple
  node from a clean tree at `1c786fe`, wall 6,450 s. The nine build dates
  hold 99 cells the two arms share, over 19 cohorts, and all 99 enter the
  criterion; seven models; 200 resamples under 20260905 with the cohorts held
  fixed and resampled, every pooling again under 20260906 and 20260907, and
  every pooling with each draw held fixed. No Cox fit left a cell out on
  either arm. TabICL's rows at 1.0 are derived on both arms, 70,000 rows
  checked per build and 51,016 on 2013H1-R, the largest gap on the
  probability 2.2 × 10⁻⁷. Per build date the share of the expanding pool the
  window holds is printed twice, from the score runs' `build.json` and from
  the contrast record, and the two agree on every date.

  *What each arm does on its own.* The mean of |Cox slope − 1| over the 99
  cells, expanding against rolling: the scorecard 0.0921 against 0.0999, the
  full-pool GBM 0.0883 against 0.0748, the control 0.1455 against 0.1053,
  TabPFN 0.1129 against 0.1140, TabICL 0.1394 against 0.1439; at 1.0 TabPFN
  0.0876 against 0.0798 and TabICL 0.0866 against 0.0857. Each model's own
  E − R: the full-pool GBM +0.0135 [+0.0045, +0.0187], starred; the control
  +0.0402 [−0.0054, +0.0786], holding zero, its draws disagreeing; TabPFN
  −0.0011 [−0.0141, +0.0182] and TabICL −0.0045 [−0.0167, +0.0155], both
  holding zero, and at 1.0 +0.0078 [−0.0098, +0.0189] and +0.0009 [−0.0070,
  +0.0106]. The four-quarter window moves neither foundation model's slope
  deviation on this book, at either temperature; that row needs no control.

  *The criterion's row.* Each model's E − R minus the control's on the same
  resample, over the 99 cells with the cohorts held fixed, at 0.9: TabPFN
  −0.0412 [−0.0885, +0.0181], TabICL −0.0447 [−0.0916, +0.0167]. Both hold
  zero under the primary seed and under both check seeds, so the kill fires
  for both, inside the interval, as the note of 2026-09-15 reads it. At 1.0
  TabICL reads −0.0393 [−0.0806, +0.0058], holding zero; TabPFN −0.0324
  [−0.0700, −0.0006], below zero under the primary seed, the star lost under
  20260906 ([−0.0659, +0.0015]) and kept under 20260907 ([−0.0693,
  −0.0007]), which by the note of 2026-09-06, late, holds zero at the
  margin. The verdict at 1.0 does not differ in kind from the verdict at
  0.9: killed for both models at both settings. The scorecard's row,
  −0.0480 [−0.0918, −0.0022], lies below zero; the full-pool GBM's, −0.0267
  [−0.0676, +0.0189], holds it.

  *The other scopes.* With every build date weighted alike TabPFN reads
  −0.0516 [−0.0904, −0.0021] and TabICL −0.0569 [−0.0996, −0.0013], below
  zero; with the cohorts resampled −0.0412 [−0.0948, +0.0208] and −0.0447
  [−0.0962, +0.0184], holding it. Under each draw held fixed the TabPFN row
  reads [−0.0640, −0.0293], [−0.0927, −0.0702] and [−0.0001, +0.0213] on
  draws 20260911, 20260912 and 20260913, and the TabICL row [−0.0712,
  −0.0330], [−0.0939, −0.0739] and [−0.0019, +0.0182]: two draws below zero,
  the third holding it, and every H4 row on the table carries the mark. Per
  build date the sign is not stable: at 2014H1 both models read above zero
  and starred, +0.0529 [+0.0020, +0.0823] and +0.0630 [+0.0188, +0.0996]; at
  2017H1 below it and starred, −0.1477 [−0.3211, −0.0255] and −0.1499
  [−0.2929, −0.0239]; at 2013H2 the intervals are half a unit wide, −0.1628
  [−0.5431, +0.1183] and −0.1719 [−0.5450, +0.0990]. Of the 26 pooled
  differences 4 are starred under the primary seed and 1 changes its star
  under a check seed; over every scope 28 of 156 are starred and 8 change;
  the largest movement of an interval bound is 0.0223.

  *What the summary says wrongly.* The run's `summary.json` calls TabPFN's
  row at 1.0 "killed: the reduction is smaller than the control's, beyond
  the interval": the script read the interval's upper bound before the seed
  check, which it records in the same object as changing the star. The
  reading above is the note of 2026-09-17's; the pooling is recorded again
  with the string corrected, below.

- **2026-09-17 — H4 recorded again with the verdict string corrected, and the sensitivity points.**
  [`experiments/2026-09-17-lc-between-arm-intervals`](../../experiments/2026-09-17-lc-between-arm-intervals),
  the same command over the same eighteen readings and the same contrast,
  on the Apple node from a clean tree at `5130710`, wall 5,427 s. **It
  supersedes the recording of 2026-09-16; cite it.** Its `cells.csv`,
  `paired-seeds.csv` and both figures are byte-identical to the first
  recording's, and every
  one of the 405 rows of the first recording's `paired.csv` appears
  unchanged in its `paired.csv`, which holds 1,215 rows because the per-draw
  poolings are now written at every scope; the first recording's stdout
  table is reproduced value for value, bound for bound and mark for mark.
  Two things are new. The manifest pins every file the pooling read,
  2,449 files under `inputs.json`, beside the code hashes. And the string
  for TabPFN at 1.0 now reads "killed: inside the interval, holding zero at
  the margin, the star lost under a check seed". Its interval under the
  primary seed still lies below zero, [−0.0700, −0.0006]; the string names
  the reading the note of 2026-09-06, late, gives such a row, and the
  sentence in the entry above stands.

  *The sensitivity points.*
  [`experiments/2026-09-17-lc-h4-sensitivity`](../../experiments/2026-09-17-lc-h4-sensitivity),
  `h4_sensitivity.py` over the first recording's `cells.csv`, on a clean
  tree at `4044017`, 3 s. Points only, no interval: each row replaces
  per-cell deviations and is read for one thing, whether it leaves the
  criterion row's interval. The recorded point reproduces the run's
  `paired.csv` to 10⁻¹². Under each draw held fixed the TabPFN row reads
  −0.0512, −0.0842 and +0.0118 and the TabICL row −0.0577, −0.0862 and
  +0.0098 on draws 20260911, 20260912 and 20260913. With each build date
  left out in turn the TabPFN row lies between −0.0580 (2014H1 out) and
  −0.0160 (2013H2 out), the TabICL row between −0.0639 and −0.0183. With
  each of the 54 control fits replaced in turn by the mean of its other two
  draws on the same cells, the TabPFN row lies in [−0.0622, −0.0122] and
  the TabICL row in [−0.0656, −0.0157], the lowest and the highest on
  2013H2-E under draws 20260913 and 20260912 in both cases. None of the
  rows leaves the criterion row's interval, [−0.0885, +0.0181] and
  [−0.0916, +0.0167].

  *The control's fits.* `control-fits.csv` follows each control fit from the
  pooling's manifest to its build's score run: on 2013H2-E the three draws
  stopped at 29, 19 and 51 rounds at learning rate 0.1 with fifteen leaves,
  on 10,951, 10,882 and 11,010 rows of 2012Q4, with mean |slope − 1| over the
  build's 17 cells of 0.2089, 0.6400 and 0.0587 for draws 20260911, 20260912
  and 20260913; the largest move of any row above is that one fit's. The
  point the control inherits from its build's full-pool search differs
  between the arms at every one of the nine dates, the leaf count, the
  learning rate or the feature fraction changing at each: at 2013H1 the
  expanding arm's control runs 31 leaves at 0.03 on every column and the
  rolling arm's 7 leaves at 0.1 on 0.4 of them; at 2017H1 both run 31 leaves
  at 0.03, on 0.4 and 0.6 of the columns. The control's E − R therefore
  mixes the window with a re-tuning a foundation model does not have, as the
  note of 2026-09-17 says.

- **2026-09-17 — kill criterion 3, read as the note of 2026-09-17 fixes it.**
  [`experiments/2026-09-17-lc-kill-criterion-3`](../../experiments/2026-09-17-lc-kill-criterion-3),
  `kill_criterion_3.py` over the nine expanding-arm readings of 2026-09-11,
  on a clean tree at `774fe4f`, 2 s. Per seeded model and build, the mean
  over the build's cohorts of the range of AUC across the three context
  draws against the mean over adjacent cohort pairs of |AUC difference|
  under one draw, averaged over the draws; the criterion fires for a model
  when the first exceeds the second on a majority of the nine builds. The
  draws move the AUC more than the adjacent cohorts do on 1 of 9 builds for
  the control (2013H2-E, 0.01285 against 0.01172), on 1 of 9 for TabPFN at
  either temperature (2016H2-E, 0.00953 against 0.00907), and on 0 of 9 for
  TabICL at either temperature. The criterion does not fire for any model.
  Across the 45 rows the range across draws runs 0.00050 (TabICL on
  2013H1-E, whose three draws share all but a few hundred rows) to 0.01285,
  and the movement between adjacent cohorts 0.00907 to 0.01859. The
  rolling arm is not read: on 2013H1-R the three draws are one pool and the
  range is zero by construction.

- **2026-09-17 — the control refitted with its early-stopping tail sized by row share, on every build.**
  Eighteen runs of `score_build.py --control-refit`, one per build of both
  arms, on a clean tree at `8816e91`, 166 to 197 s each:
  [`experiments/2026-09-17-lc-2013h1e-control-refit`](../../experiments/2026-09-17-lc-2013h1e-control-refit)
  to [`-2017h1e-control-refit`](../../experiments/2026-09-17-lc-2017h1e-control-refit)
  and [`-2013h1r-control-refit`](../../experiments/2026-09-17-lc-2013h1r-control-refit)
  to [`-2017h1r-control-refit`](../../experiments/2026-09-17-lc-2017h1r-control-refit).
  Each fits the control alone, at the point of the score run it names, with
  the validation tail chosen by row share alone and no cap on the number of
  quarters it may take, where the recorded control's policy caps the tail at
  four, and writes it as `gbm-50k@share`. The reading exists for the second
  book, where the cap binds on the later expanding builds; on this book it
  never bound. On all eighteen builds and all three draws the refit's
  validation quarters are the recorded control's, one or two quarters, its
  validation rows and its round count are the recorded control's exactly
  (97, 93 and 137 rounds on 10,345, 10,330 and 10,335 rows on 2013H1-E; 77
  rounds on 10,447 rows on each draw of 2013H1-R, whose three contexts are
  the whole 31,016-row pool), and its scored probabilities equal the
  recorded control's on every one of the 180,000 to 1,140,000 rows per
  build, with a largest absolute difference of 0.0. The score files stay
  out of the repository, as for every score file of this book; `build.json`
  carries the fits.

- **2026-09-18 — the arm-level pooling at the commit before the signed slope.**
  [`experiments/2026-09-18-lc-arm-e-intervals-at-1ad2915`](../../experiments/2026-09-18-lc-arm-e-intervals-at-1ad2915),
  `arm_intervals.py` at `1ad2915` over the nine sources of the recording of
  2026-09-12 and with the same `--check-seeds 20260906,20260907`, on a clean
  tree, exit 0, wall 27,329 s. The command is that recording's with the
  output directory alone changed, and the two manifests name the same host,
  the same CPU, Python 3.12.1 and the same interpreter binary by hash. **It
  supersedes the recording of 2026-09-12; cite it until the entry below,
  which supersedes it in turn.** Its commit is the last one before the
  signed Cox slope on every file the pooling reads, so it is the baseline
  the entry below is held against.

  *What comes back unchanged.* Every `value` and every star
  (`excludes_zero`) is identical to the bit: 0 of the 4,536 rows of
  `paired.csv`, keyed on `arm, cohorts, draw, scope, metric, pair,
  is_difference`, differ in either column, and 0 of the 8,883 rows of
  `paired-seeds.csv`, keyed on `arm, bootstrap_seed, cohorts, scope, metric,
  pair`. Every row of the superseded recording is matched, 0 rows are
  missing on either side and no key occurs twice; of its `intervals.json`
  all 1,802 leaves are present and 0 are dropped. The seed check reads the
  same numbers: 2,961 differences with 1,340 starred, 441 at the arm's scope
  with 247 starred there, 15 changing their star under a check seed, and the
  largest movement of an interval bound identical to its last digit,
  0.061486787724620795. All four figures are byte-identical, and neither run
  wrote to stderr.

  *What moved.* 30 cells of `paired.csv`, in 28 rows, and 56 cells of
  `paired-seeds.csv`, in 54 rows. Every one of them sits on a
  `cox_slope_deviation` row and every one is a bound or a standard error: in
  `paired.csv` 26 cells of `se` and 4 of `ci_hi`, the largest movement
  2.5 × 10⁻¹⁶; in `paired-seeds.csv` 45 of `se`, 7 of `ci_lo` and 4 of
  `ci_hi`, the largest 4.0 × 10⁻¹⁶. That is 28 of the first table's 728 Cox
  rows and 54 of the second's 1,449. No row of `gini`, `abs_log_oe`, `psi`,
  `psi_first_cohort`, `auc_slope_build` or `auc_slope_cohort` moved in any
  column. The scopes that moved in `paired.csv` are 2013H2-E, 2014H2-E,
  2015H1-E, 2016H1-E, 2016H2-E and the arm; in `paired-seeds.csv`, those six
  with 2017H1-E and the mean over builds; 2013H1-E, 2014H1-E and 2015H2-E
  moved in neither. Of `intervals.json`, two numeric leaves moved, each one
  the `ci_hi` of a `cox_slope_deviation` reading, by at most 5.6 × 10⁻¹⁷,
  and `wall_seconds` with them.

  *Where the movement comes from.* Between `a9edd51`, the commit of the
  recording of 2026-09-12, and `1ad2915` two commits change the Cox
  arithmetic: `db12783`, the fit, and `3a7d012`, the pooling. EXP-005's
  *Addition of 2026-09-14* records the same movement on the per-build
  poolings — Cox interval bounds and standard errors read from resamples, at
  most 3 × 10⁻¹⁶, the point estimates and the stars unchanged — on the
  replay of 2016H2-E, which is one of the scopes above. Which of the two
  commits moves a given cell is not established, and nothing here depends on
  it.

  *What stands.* No number quoted in the entries of 2026-09-11 and
  2026-09-12 changes at the precision it is quoted at. The values and the
  stars are bit-identical, and a movement of a bound or a standard error at
  10⁻¹⁶ is fourteen orders below the last digit those entries write, so the
  readings there stand as they are.

  *The columns and leaves the commits between them add.* `paired.csv` gains
  `reads_derived`, true on a pair naming a model whose rows are derived
  rather than scored, `bool(set(pair.split(" - ")) & set(derived))` in the
  code; it reads true on 1,134 of 4,536 rows, and recomputing it from the
  `pair` column against `derived_rows` disagrees on 0 of them.
  `paired-seeds.csv` gains no column. `intervals.json` gains 137 leaves.
  `derived_rows` holds the derivation of each source read at another
  temperature, here the nine entries of `tabicl@t1`, every one of kind
  `exact` with a largest probability gap of 1.1 × 10⁻⁷ to 1.6 × 10⁻⁷.
  `cox_left_out` holds, per pooling and scope, the count of cells the Cox
  point estimate could not use and the most any one resample left out; it
  reads `0.0` at all 52 of its leaves, so the pooled mean is over the cells
  it was over before. `cox_rule` states in prose the rule the Cox statistics
  pair under. `outcome` names the outcome column read, the default
  `outcome` here; `cohort_scopes` is empty unless `--cells` or `--h2-scopes`
  is given, and `oe_ratio` is null unless `--h2-scopes` is. They are
  reported beside the statistics and none of them is read into one.

- **2026-09-17 — the arm-level pooling with the signed Cox slope, held against the recording above.**
  [`experiments/2026-09-17-lc-arm-e-intervals`](../../experiments/2026-09-17-lc-arm-e-intervals),
  `arm_intervals.py` at `9f0e110` over the same nine sources and the same
  check seeds, on a clean tree, exit 0, wall 32,197 s, on the machine of the
  recording above: the same host, the same CPU, Python 3.12.1 and the same
  interpreter binary by hash. The two commands are fifteen tokens each and
  differ at one position, the output directory. This run finished on
  2026-09-17 and the recording it supersedes on 2026-09-18; the two ran on
  one machine and their hashed files differ at `scripts/arm_intervals.py`
  and `scripts/build_intervals.py` alone, so the order of the two walls
  enters nothing. **It supersedes the recording of 2026-09-18 at `1ad2915`;
  cite it.**

  *Every row, bound and star of that recording is reproduced to the bit.*
  The maximum absolute difference is exactly 0.0 on `value`, `ci_lo`,
  `ci_hi`, `se`, `alpha`, `resamples` and `seed`, over the 4,536 rows of
  `paired.csv` and the 8,883 of `paired-seeds.csv`; 0 cells differ read as
  text and 0 read as floats, `excludes_zero` and `reads_derived` are equal
  on every row, and 0 rows are missing. Every line of the superseded
  tables, the header with them, occurs verbatim in the new ones. Of
  `intervals.json`, 0 of 1,935 shared leaves are lost and ten change: the
  wall, four entries of the `pooled_metrics` list, which is the old list
  with `cox_slope` inserted at index 3, and five counts of rows in the seed
  check — `differences` 2,961 to 3,444, `starred` 1,340 to 1,698,
  `arm_differences` 441 to 504, `arm_starred` 247 to 303 and
  `arm_star_changed` 15 to 17. Re-derived from `paired.csv`, each count
  equals its own run's rows, and each new count with the `cox_slope` rows
  dropped equals the old count exactly. The largest movement of an interval
  bound is unchanged to its last digit, 0.061486787724620795.

  *What is added.* 728 rows of `paired.csv` and 1,449 of
  `paired-seeds.csv`, every one of metric `cox_slope`, at exactly the keys
  `cox_slope_deviation` holds: with the metric dropped from the key the two
  sets are equal in both tables, 0 keys on either side lack a partner, and
  the rows per scope agree — 56 at each build's scope and at the mean over
  builds and 168 at the arm in `paired.csv`, 126 and 189 in
  `paired-seeds.csv`. The 1,449 are 483 difference rows under the primary
  seed and under each of the two check seeds. `cox_left_out` reads the same
  two numbers for `cox_slope` as for `cox_slope_deviation` at all 26
  pooling-and-scope entries, 0 mismatches, and `statistics` gains the one
  key `cox_slope` with none dropped. `arm-differences.png` is one panel
  wider, 4,784 px against 4,186 px at the same height of 1,846 px, the
  added panel 598 px like the seven beside it; the other three figures are
  byte-identical.

  *The statistic on its own, at three builds.* Beside the arm, 2015H1-E,
  2016H1-E and 2017H1-E are pooled at both commits with the same command,
  once without the check seeds
  ([`experiments/2026-09-17-lc-arm-e-signed-slope-control`](../../experiments/2026-09-17-lc-arm-e-signed-slope-control)
  against [`-parent`](../../experiments/2026-09-17-lc-arm-e-signed-slope-control-parent))
  and once with them
  ([`-seeds`](../../experiments/2026-09-17-lc-arm-e-signed-slope-control-seeds)
  against [`-seeds-parent`](../../experiments/2026-09-17-lc-arm-e-signed-slope-control-seeds-parent)).
  On both pairs the maximum absolute difference is 0.0 on every numeric
  column of the tables the parent run wrote and on every shared numeric
  leaf of `intervals.json` but the wall and, on the seeded pair, the
  seed-check counts of rows; 0 parent rows and 0 parent leaves are missing,
  and the only rows added are `cox_slope`.

  What is not here. The reading of the signed slope. The arm's `cox_slope`
  rows are recorded and unread; the reading is owed, and it is written from
  the recorded tables.

- **2026-09-17 — the rolling arm pooled again with the signed Cox slope.**
  [`experiments/2026-09-17-lc-arm-r-intervals`](../../experiments/2026-09-17-lc-arm-r-intervals),
  `arm_intervals.py` at `9f0e110` over the nine sources of the recording of
  2026-09-16 and the same check seeds, on a clean tree, exit 0, wall 32,277 s,
  beside the expanding arm's pooling on the same machine. **It supersedes the
  recording of 2026-09-16; cite it.** Every row, bound and star that recording
  wrote comes back identical to the bit: the maximum absolute difference is
  exactly 0.0 on every numeric column of the 4,536 rows of `paired.csv` and the
  8,883 of `paired-seeds.csv`, no field differs read as text, and of
  `intervals.json` all 1,708 leaves are present with nine changed — the four
  positions of the pooled-metric list into which the new statistic is inserted,
  the four counts of the seed check, and the wall. Each of those counts grows by
  exactly the rows the statistic adds, 483 differences and 390 starred, 63 at the
  arm's scope and 57 starred there, re-derived from `paired.csv` and equal to the
  old counts once the new rows are dropped.

  *What is added.* 728 rows of `paired.csv`, 182 of them mean rows and 546
  differences, and 1,449 of `paired-seeds.csv`, every one of metric `cox_slope`
  and at exactly the keys `cox_slope_deviation` holds, no key of either metric
  without its partner in either file. The mean rows sit 14 on each of the nine
  build scopes, 42 at the arm and 14 at the mean over builds; none of them
  carries a non-finite value, bound or standard error, and the pattern of cells
  left empty is the deviation's on all 728 keys. The cells the Cox fit could not
  use are the same for the two statistics at all 26 poolings and scopes. The rows
  are recorded and unread here; the reading of the statistic is entered under its
  own date.

- **2026-09-18 — the signed Cox slope read on both arms.** The reading owed by
  the two entries above is made on the runs they record,
  [`experiments/2026-09-17-lc-arm-e-intervals`](../../experiments/2026-09-17-lc-arm-e-intervals)
  and
  [`experiments/2026-09-17-lc-arm-r-intervals`](../../experiments/2026-09-17-lc-arm-r-intervals),
  at temperature 1.0 with the shipped setting beside it. 200 resamples under
  seed 20260905, checked under 20260906 and 20260907, the context seed drawn
  with the resample. No cell was left out of any `cox_slope` point estimate or
  any resample, at any pooling or scope.

  *The attribution is not supported on either arm.* At temperature 1.0 on the
  expanding arm the mean signed slope minus the scorecard's is +0.0193
  [−0.0053, +0.0415] for TabPFN and −0.0213 [−0.0428, +0.0015] for TabICL, both
  holding zero under the primary seed. TabICL's row excludes zero under
  20260906 alone, [−0.0429, −0.0002]; a star under a check seed alone is not a
  star. On the rolling arm the difference is +0.05023 [+0.0242, +0.0735] for
  TabPFN, excluding zero under all three seeds and clearing the minimum effect
  of 0.05 by 2.3 × 10⁻⁴, and +0.0069 [−0.0133, +0.0236] for TabICL, holding
  zero.

  *The models' own slopes decide the rest.* TabPFN reads 1.0011 [0.9629,
  1.0368] on the expanding arm and 0.9996 [0.9603, 1.0331] on the rolling one,
  each interval holding one, so neither of its rows has the half that support
  requires and neither has the half that contradicts: the book does not resolve
  the mechanism for TabPFN at this size. TabICL reads 0.9605 [0.9227, 0.9976]
  and 0.9563 [0.9226, 0.9837], both wholly below one, which contradicts the
  attribution on both arms — a logit more spread than the outcomes warrant, not
  less. The scorecard reads 0.9818 [0.9508, 1.0144] on the expanding arm and
  0.9494 [0.9198, 0.9833] on the rolling one. No criterion star is lost under a
  check seed; over both arms one row of the four pairs loses a primary-seed
  star, the rolling arm's `nearest` pooling at 2014H1-R at 0.9, which is
  neither a criterion pooling nor a criterion scope. Three rows gain a star
  under a check seed alone, and one of those is at a criterion scope: the
  expanding arm's `all` pooling at the arm, TabICL at 1.0, the row reported
  above as a star under one check seed alone.

  *The shipped setting.* At 0.9 the difference is −0.0808 [−0.1036, −0.0592]
  and −0.1173 [−0.1378, −0.0956] on the expanding arm and −0.0497 [−0.0739,
  −0.0279] and −0.0887 [−0.1069, −0.0738] on the rolling one, TabPFN first,
  each excluding zero under all three seeds, and every model's own slope at 0.9
  is wholly below one: 0.9010 and 0.8645 on the expanding arm, 0.8997 and
  0.8607 on the rolling one. The knob multiplies the slope by 0.9 and carries
  both models further below one.

  *Beside the reading, entering none of it.* The mean over builds, each build
  on its own, the nearest-cohorts window, the cohorts-resampled pooling and the
  three fixed draws; every criterion row at 1.0 is listed under
  `bootstrap.draws_disagree`, and the criterion pooling covers that spread by
  drawing the context seed with the resample. TabICL's rows at 1.0 are derived
  on both arms, exactly, worst probability gap 1.0 × 10⁻⁷ to 2.2 × 10⁻⁷;
  TabPFN's are scored.

  *What this book cannot carry.* The direction on 2015H1-E was already on the
  record from 2026-09-06, so the arm replicates a sign there rather than
  measuring it blind; at that build's own scope the difference reads +0.0222
  [−0.0776, +0.0835] and −0.0346 [−0.1157, +0.0273], both holding zero, and a
  build's row is read as a build's row. The book is one product over five years
  with a 1.72-fold prevalence range. Neither pooling was given `--cells`, so
  neither arm carries a pre-flag, flagged or cohort scope and the reading
  cannot be cut by the flag. Neither was given the sensitivity label. There is
  no in-sample pooling on this book beyond the falsifying build's one draw, so
  the in-sample slope is read on the second book alone. The own-slope half is
  read under the primary seed only, `paired-seeds.csv` carrying difference rows
  alone. And the slope does not see a shift of the logit, so the level half of
  the attribution is not read here.

  *The second book, by sign and star alone.* Its arms are read in EXP-005 under
  the same statistic and the same rule. No row there supports the attribution
  either; the own-slope half falls below one on every row of both its arms, and
  the paired half at 1.0 excludes zero on the positive side on its rolling arm
  for both models. As the Multiplicity paragraph of EXP-005 has it, the sign
  and the star carry across and no number does.

- **2026-09-19 — H4's draw component.** No run. Every number below is read
  from a recorded table named beside it. The entry changes no verdict: H4
  stays killed inside the interval on this book, as the entries of
  2026-09-16 and 2026-09-17 read it.

  *The rows.* Arm scope, mean |Cox slope − 1| at 0.9, each model's E − R:
  one row per context draw with the draw held fixed and the cohorts
  resampled, `cohorts` `all` and `draw` set; then the pooled row with the
  draw drawn with the resample, `cohorts` `all, cohorts resampled`. Metric
  `cox_slope_deviation`, kind `reduction`, seed 20260905; a star marks an
  interval that excludes zero. From `paired.csv` of
  [`experiments/2026-09-17-lc-between-arm-intervals`](../../experiments/2026-09-17-lc-between-arm-intervals):

      draw       gbm-50k                     tabpfn                      tabicl
      20260911   +0.0440 [+0.023, +0.060] *  −0.0072 [−0.013, +0.002]    −0.0137 [−0.018, −0.007] *
      20260912   +0.0730 [+0.065, +0.082] *  −0.0112 [−0.016, −0.001] *  −0.0132 [−0.017, −0.005] *
      20260913   +0.0035 [−0.006, +0.010]    +0.0153 [+0.005, +0.019] *  +0.0133 [+0.005, +0.017] *
      pooled     +0.0402 [−0.008, +0.087]    −0.0011 [−0.018, +0.022]    −0.0045 [−0.023, +0.020]

  The scorecard and the full-pool GBM read one value on every draw, −0.0078
  and +0.0135, having no draw.

  *The rounds.* From `control-fits.csv` of
  [`experiments/2026-09-17-lc-h4-sensitivity`](../../experiments/2026-09-17-lc-h4-sensitivity),
  `rounds`, `validation_quarters` and `validation_rows` per build, arm and
  draw. The control stops on 10,330 to 18,518 rows over one or two quarters
  on the expanding arm and on 10,250 to 17,530 rows over one quarter on the
  rolling arm, so the four-quarter cap never binds, which is why the refit
  control of 2026-09-17 equals the recorded one on every build. The round
  count still moves across the three draws of one build: 29/19/51 at
  2013H2-E, where the mean |slope − 1| over the build's 17 criterion cells
  is 0.209/0.640/0.059, 322/106/156 at 2015H1-R and 151/119/303 at
  2016H1-R. At 2013H1-R the three draws are one pool and read 77 rounds
  each.

  *What the rows say.* With a stopping set of ten to eighteen thousand rows
  on both arms, the control's E − R spans 0.070 across three draws, two of
  its per-draw intervals starred and disjoint from each other; and both
  foundation models' E − R change sign between draws, each starred on both
  sides of zero. **A between-arm test on 50,000-row contexts is dominated by
  which 50,000 rows the context holds, the between-draw spread of every
  model's E − R is several hundredths on both books, and three draws make
  that component a three-point distribution, so H4's pooled interval is the
  draw spread, not the effect's.** The second book adds a defect of its own
  to the control, a stopping set the four-quarter cap shrinks along the
  expanding arm (EXP-005's log, 2026-09-19); this book has none, and the
  draw spread is there regardless.

- **2026-09-19 — H4's signed reading.** No run. A reading beside, dated
  after the result, entering no criterion: H4's statistic stays the folded
  mean |Cox slope − 1|, which was pre-registered and under which every
  verdict was read, and H4 stays killed inside the interval on this book, as
  the entries of 2026-09-16 and 2026-09-17 read it. The signed slope is read
  for one thing, what the folded reduction between the arms is a reduction
  of. The entry of 2026-09-18 above reads the signed slope against the
  scorecard; this one reads it between the arms.

  *The rows.* Metric `cox_slope`, `cohorts` `all`, `draw` empty,
  `is_difference` False, scope `arm`, each model's mean signed Cox slope over
  the arm's criterion cells, seed 20260905. Both arms hold the same 99 cells
  (`cells` 99 in `intervals.json` of both arm runs, `cells_shared` 99 in
  `summary.json` of the between-arm run), so the arm rows are on identical
  cells and no weighting enters. From `paired.csv` l. 86–92 of
  [`experiments/2026-09-17-lc-arm-e-intervals`](../../experiments/2026-09-17-lc-arm-e-intervals)
  and of
  [`experiments/2026-09-17-lc-arm-r-intervals`](../../experiments/2026-09-17-lc-arm-r-intervals).
  Beside them, the recorded folded reduction, E − R of mean |Cox slope − 1|
  at arm scope in the criterion's pooling (`cohorts` `all`, `draw` empty:
  cohorts held fixed, the draw drawn with the resample; the entry above
  quotes the pooling with the cohorts resampled), from `paired.csv` l. 4–22
  of
  [`experiments/2026-09-17-lc-between-arm-intervals`](../../experiments/2026-09-17-lc-between-arm-intervals);
  a star marks an interval that excludes zero:

      model        signed E                  signed R                  E − R     folded E − R (recorded)
      scorecard    0.9818 [0.9508, 1.0144]   0.9494 [0.9198, 0.9833]   +0.032    −0.0078 [−0.0184, +0.0011]
      gbm          1.0429 [1.0129, 1.0718]   1.0278 [0.9973, 1.0562]   +0.015    +0.0135 [+0.0045, +0.0187] *
      gbm-50k      1.0851 [1.0147, 1.1582]   1.0522 [0.9955, 1.0989]   +0.033    +0.0402 [−0.0054, +0.0786]
      tabpfn       0.9010 [0.8665, 0.9331]   0.8997 [0.8643, 0.9299]   +0.001    −0.0011 [−0.0141, +0.0182]
      tabicl       0.8645 [0.8304, 0.8978]   0.8607 [0.8303, 0.8854]   +0.004    −0.0045 [−0.0167, +0.0155]
      tabpfn@t1    1.0011 [0.9629, 1.0368]   0.9996 [0.9603, 1.0331]   +0.001    +0.0078 [−0.0098, +0.0189]
      tabicl@t1    0.9605 [0.9227, 0.9976]   0.9563 [0.9226, 0.9837]   +0.004    +0.0009 [−0.0070, +0.0106]

  *What this says.* The foundation models at 0.9 sit wholly below one on
  both arms, and the window moves their signed slope by at most 0.004. The
  control is a different object: its signed mean sits above one on both
  arms, its interval wholly so on the expanding arm, and falls by 0.033
  toward one under the window. The folded statistic reads that fall as an
  improvement of +0.040, which is why this book's H4 rows read −0.041 and
  −0.045 (`paired.csv` l. 25 and 26 of the between-arm run) for models whose
  slope did not move. In signed terms the window moves the control 8.8 to 26
  times as far as a foundation model at 0.9 (0.0329 against 0.0037 and
  0.0013, unrounded). H4's statistic therefore compares a distance below
  one, at which both foundation models sit on both arms, with a distance
  above one, at which the control sits; a fall in the control's slope lowers
  its folded deviation on the cells where it stood above one. What this book
  does not support: that the foundation models' calibration slope is as
  sensitive to the context policy as the control's, or that the rolling
  window helps or hurts a foundation model's slope by a named amount against
  the control. The between-arm signed reduction with an interval is not
  recorded; `between_arm_intervals.py` carries only `cox_slope_deviation`.

- **2026-09-19 — the interval's other bound.** No run. Every interval of
  this book is the percentile interval of the resampled values
  (`src/outoftime/metrics.py` l. 759), the recorded method on every row, and
  it stays the method: changing it after the verdicts would be a rewrite. A
  percentile interval of a statistic with a skewed resampling distribution
  sits off-centre about the point, so its other bound is read here beside
  it: the basic interval, reflected about the point estimate from the
  recorded bounds, [2v − hi, 2v − lo]. A star marks an interval that
  excludes zero.

  H4's rows, each model minus GBM-50k, E − R of mean |Cox slope − 1| at arm
  scope, `cohorts` `all`, `draw` empty, from `paired.csv` of
  [`experiments/2026-09-17-lc-between-arm-intervals`](../../experiments/2026-09-17-lc-between-arm-intervals):

      row          line   value     percentile             basic
      scorecard    l23    −0.0480   [−0.0918, −0.0022] *   [−0.0937, −0.0041] *
      gbm          l24    −0.0267   [−0.0676, +0.0189]     [−0.0722, +0.0143]
      tabpfn       l25    −0.0412   [−0.0885, +0.0181]     [−0.1006, +0.0061]
      tabicl       l26    −0.0447   [−0.0916, +0.0167]     [−0.1061, +0.0022]
      tabicl@t1    l27    −0.0393   [−0.0806, +0.0058]     [−0.0844, +0.0020]
      tabpfn@t1    l28    −0.0324   [−0.0700, −0.0006] *   [−0.0642, +0.0052]

  One star changes: TabPFN at 1.0, whose percentile interval lies below
  zero and whose basic interval holds it. The entry of 2026-09-17 above
  already reads that row as "killed: inside the interval, holding zero at
  the margin, the star lost under a check seed"; the basic interval says the
  same thing a second way, and the reading does not change. The two
  foundation models' rows at 0.9 hold zero under both intervals, so H4's
  kill inside the interval stands under either.

- **2026-09-19 — the numbers and verdicts the note of 2026-09-17 stated,
  carried here.** The pre-registration's note of 2026-09-17 quoted H4's
  pooling on this book and stated what its criterion read. From this date
  the pre-registration carries no number produced by a model fit or a
  pooling on this book and no statement of what a criterion or a star read
  on it, as EXP-005's Setting already does not; the passages below left it
  and are quoted here whole, as they stood, and each place they stood now
  points to this entry. Nothing is recomputed, and no hypothesis, criterion
  or reading changes. Where a passage both stated a result and fixed a
  reading, the reading stayed in the pre-registration and is also inside the
  quotation below.

  Where each number is read from. H4's criterion rows, their seed checks and
  each foundation model's own E − R are rows of `paired.csv` and
  `paired-seeds.csv` of
  [`experiments/2026-09-16-lc-between-arm-intervals`](../../experiments/2026-09-16-lc-between-arm-intervals),
  reproduced to the bit by the superseding
  [`experiments/2026-09-17-lc-between-arm-intervals`](../../experiments/2026-09-17-lc-between-arm-intervals),
  which is the one cited; the entry of 2026-09-16 on H4, the two arms against
  each other, reads them, and the entry of 2026-09-17 on H4 recorded again
  says how the summary string was corrected. The control's fits at 2013H2-E
  and the sensitivity points are `control-fits.csv` and the sensitivity table
  of
  [`experiments/2026-09-17-lc-h4-sensitivity`](../../experiments/2026-09-17-lc-h4-sensitivity),
  read in the same entry of 2026-09-17.

  From the note of 2026-09-17, on H4's criterion rows and the summary string:

  > *H4's verdict stands as read; a string in the run's summary does not.* The
  > criterion's row, each foundation model's E − R of mean |Cox slope − 1|
  > minus the control's on the same resample over the 99 shared cells at 0.9,
  > reads −0.0412 [−0.0885, +0.0181] for TabPFN and −0.0447 [−0.0916, +0.0167]
  > for TabICL, holding zero under the primary seed and both check seeds: the
  > kill fires, inside the interval. At 1.0 both rows are killed too. TabPFN's
  > row at 1.0, −0.0324 [−0.0700, −0.0006], is starred below zero under the
  > primary seed and loses the star under 20260906 ([−0.0659, +0.0015]); by
  > the note of 2026-09-06 (late) it holds zero at the margin, and the verdict
  > at 1.0 does not differ in kind from the verdict at 0.9. The recorded
  > summary calls that row "killed: the reduction is smaller than the
  > control's, beyond the interval", because the script read the interval's
  > upper bound before it read the seed check;

  On each model's own E − R:

  > Each
  > foundation model's own E − R is on the table as the note of 2026-09-15
  > has it: TabPFN −0.0011 [−0.0141, +0.0182], TabICL −0.0045 [−0.0167,
  > +0.0155]. The four-quarter window moves neither model's slope deviation
  > on this book, at either temperature.

  On the control's reduction and the sensitivity rows:

  > Its
  > E − R, +0.0402 [−0.0054, +0.0786], holds zero and is carried by one fit:
  > on 2013H2-E the three draws stopped at 19, 29 and 51 rounds at learning
  > rate 0.1 on 10,882 to 11,010 rows of 2012Q4, with mean |slope − 1| over
  > the build's 17 cells of 0.640, 0.209 and 0.059 (draws 20260912, 20260911,
  > 20260913). With that one fit replaced by the mean of its other two draws
  > the pooled H4 row reads −0.012 for TabPFN and −0.016 for TabICL; with the
  > build date dropped, −0.016 and −0.018; over every one of the 54 control
  > fits replaced in turn the row lies in [−0.062, −0.012] and [−0.066,
  > −0.016]; under each draw held fixed, −0.051 [−0.064, −0.029], −0.084
  > [−0.093, −0.070] and +0.012 [−0.000, +0.021] for TabPFN, the third
  > holding zero. A sensitivity row is read for one thing, whether it lies
  > outside the criterion row's interval, and none does;

  > The rows starred
  > below zero — the scorecard at arm scope, both foundation models with every
  > build date weighted alike — rest on the same fit

  On the kill under the mixture and under each draw:

  > Here it holds under both.

- **2026-09-19, later — the falsifying build's statistics and the verdicts
  the amendment notes stated, carried here.** The entry above says the
  pre-registration carries no number produced by a model fit or a pooling
  on this book; the file kept numbers of both kinds, in the amendment of
  2026-09-06 and in its notes of 2026-09-06 and 2026-09-12, and not all of
  them are results. The pre-registration is read from this date against a
  narrower rule. It carries no statistic of a model under study on this
  book's rows — a metric, a level, a slope, a Gini, a pooled difference, a
  star — and no verdict on a hypothesis or a criterion of the file, in
  numbers or in words. It keeps a parameter of a fit quoted as the size of
  a defect an audit found, the size of a defect of the instrument or of a
  derivation measured to fix it, a check value, a statistic of the data,
  and the weights of a statistic fixed by the grid's geometry: the weight
  that exposed the missing-bin defect, the tuning gap and the margins
  of the search's surface, the derivation's departure on the logit, the
  weights of the build-intercept slope, and every pool size and count. The
  passages below failed the rule and left the pre-registration; they are
  quoted here whole, as they stood, and each place they stood now points to
  this entry. Nothing is recomputed, and no hypothesis, criterion or
  reading changes. Where a passage both stated a result and fixed a
  reading, the reading stayed in the pre-registration and is also inside
  the quotation below.

  Where each number is read from. The slopes at 0.9 are the per-cell Cox
  slopes of
  [`experiments/2026-09-06-lc-2015h1e-intervals-tfm2`](../../experiments/2026-09-06-lc-2015h1e-intervals-tfm2),
  read in the entry of 2026-09-06 on the pooled intervals with the
  calibration statistics; the slopes at 1.0 and both context-row levels are
  read in the entry of 2026-09-06 on the temperature probe, from
  [`experiments/2026-09-06-lc-2015h1e-intervals-probe3`](../../experiments/2026-09-06-lc-2015h1e-intervals-probe3)
  and the scoring run
  [`experiments/2026-09-06-lc-2015h1e-probe3-colab-t4`](../../experiments/2026-09-06-lc-2015h1e-probe3-colab-t4).
  The mean probability under `balance_probabilities` is the mean of `pd`
  over the 50,000 `tabpfn@t1+bal` rows of that scoring run's
  `reference.parquet`, printed in its `score.log` as the reference rows'
  mean pd, and read in the same entry on the temperature probe. The stars
  under the seeds are rows of `paired-seeds.csv` of
  [`experiments/2026-09-06-lc-2015h1e-intervals-seeds`](../../experiments/2026-09-06-lc-2015h1e-intervals-seeds),
  read in the entry of 2026-09-06, late, on the bootstrap seed check. The
  per-cell Gini of 2017H1-E is from
  [`experiments/2026-09-11-lc-2017h1e-intervals-grid`](../../experiments/2026-09-11-lc-2017h1e-intervals-grid),
  and the ninth cold audit's item on the control below quotes it.

  From the amendment of 2026-09-06, on the temperature:

  > At 0.9 the models' Cox slope
  > sits near one and their mean probability at two thirds of the realised rate
  > on their own context rows; at 1.0 the mean probability is the realised rate
  > and the slope is 1.13 to 1.23, the classical models' stretch.

  From the same amendment, on `balance_probabilities`:

  > It divides each class probability by its context frequency and renormalises,
  > a shift on the logit by the log of the prior ratio; on this book it puts
  > the mean probability at 0.44.

  From the note of 2026-09-06, after the eighth cold audit, on the setting
  nominated as primary:

  > The setting nominated as primary is the one under
  > which the slope criterion of H2 does not fire, and the nomination was made
  > knowing that;

  From the note of 2026-09-06, late, after the bootstrap seed check:

  > A star on a pooled difference is an interval of two hundred resamples under one seed,
  > and the check the eighth audit asked for
  > (`experiments/2026-09-06-lc-2015h1e-intervals-seeds`) found that the H2
  > row at the shipped setting, |slope − 1| TabICL − scorecard, keeps its
  > star under the primary seed and loses it under both check seeds, while
  > TabPFN's row against the scorecard keeps it under all three. From here
  > every pooled interval that a verdict rests on is recorded with
  > `--check-seeds`, a star that does not survive every seed is reported as
  > holding zero at the margin with the intervals under each seed, and the
  > verdict of H2 on the falsifying build reads: TabPFN clears the scorecard
  > on the slope at 0.9, TabICL sits at the edge, and neither clears the
  > control.

  From the note of 2026-09-12, after the ninth cold audit, on the control's
  inherited hyperparameters:

  > and
  > on 2017H1-E its Gini sits below the scorecard's
  > ([`experiments/2026-09-11-lc-2017h1e-intervals-grid`](../../experiments/2026-09-11-lc-2017h1e-intervals-grid):
  > 0.410 against 0.412 per cell on average) where both foundation models on
  > the identical rows sit at 0.435 to 0.438.

- **2026-09-19, later — both arm-level poolings recorded again at `386c629`, with the files they read hashed.**
  [`experiments/2026-09-19-lc-arm-e-intervals`](../../experiments/2026-09-19-lc-arm-e-intervals)
  and
  [`-lc-arm-r-intervals`](../../experiments/2026-09-19-lc-arm-r-intervals),
  `arm_intervals.py` at `386c629` over the same nine sources per arm and the
  same check seeds, on a clean tree, exit 0, walls 31,655 s and 31,685 s,
  the two side by side on the machine of the recordings they replace: the
  same host, the same CPU and the same interpreter binary by hash. Each
  command is its baseline's with the output directory alone changed.
  **They supersede the two recordings of 2026-09-17 of the same names; cite
  them.**

  *Why they were recorded.* `891e78f` made `arm_intervals.py` write
  `inputs.json` and import `scripts/record_run.py` for the hash. Against
  this checkout the recordings of 2026-09-17 read red under `check_claims`:
  the script has changed since they ran, and `record_run.py` runs under
  their command without a pin. Between `9f0e110` and `386c629` the script
  differs by the hashing block, its docstring and the import, seventeen
  added lines and none removed, and `record_run.py` does not differ.

  *What comes back.* On each arm `paired.csv` (5,264 rows),
  `paired-seeds.csv` (10,332 rows) and all four figures are byte-identical
  to the recording they replace, so every value, bound and star is
  reproduced to the bit. Of `intervals.json` every leaf is present on both
  sides, 2,247 on the expanding arm and 2,013 on the rolling arm, and one
  changes on each, the wall. The standard output differs on its timing
  lines alone, and the error output is empty in all four runs.

  *What is added.* `inputs.json`, 261 entries on each arm: the
  `intervals.json` of each of the nine grid runs and every file of the
  score directories those runs name, 90 of them parquet files outside git. Every
  entry re-hashes against the file on disk without a mismatch. The
  manifests pin `scripts/record_run.py` beside the other code hashes and
  carry the script's new hash.

  What is not here. A reading. Nothing is read in these runs that the
  recordings of 2026-09-17 did not already hold, and every entry above that
  reads those recordings reads these unchanged.

- **2026-09-22 — the expanding arm's pooling recorded again at `a36c751`.**
  [`experiments/2026-09-22-lc-arm-e-intervals`](../../experiments/2026-09-22-lc-arm-e-intervals),
  `arm_intervals.py` at `a36c751` on the Apple node, clean tree, exit 0,
  6,004.7 s. Its command is that of the recording it replaces with the
  output directory alone changed, and every input it shares with that
  recording hashes the same. **It supersedes
  [`experiments/2026-09-19-lc-arm-e-intervals`](../../experiments/2026-09-19-lc-arm-e-intervals);
  cite it.**

  *Why it was recorded.* `a36c751` changed `scripts/score_context.py`,
  which the manifest of 2026-09-19 pins, so that recording reads `changed`
  under `check_claims`. Nothing between `386c629` and `a36c751` touches
  `arm_intervals.py` or `src/`.

  *Not a bit-repeat, because the machine differs.* The recording it
  replaces ran on the x86 machine and this one on the arm64 node, with the
  same numpy, scipy, pandas and pyarrow. All 5,264 rows of `paired.csv` and
  10,332 of `paired-seeds.csv` are present on both sides under the same
  keys, and no row is on one side only. Values, bounds and standard errors
  differ in their last bits: the largest absolute difference is 3.7e-15 on a
  value, 8.2e-15 on a bound and 3.1e-16 on a standard error, the largest
  relative 2.8e-11. Not one `excludes_zero`, `is_difference` or
  `reads_derived` changes, in either file. Of `intervals.json` all 2,247
  leaves are present on both sides, no non-numeric leaf differs, so every
  star and every list of moved stars is the same, and 359 numeric leaves of
  the bootstrap block differ at the same scale, the largest being
  `largest_bound_movement`, by 1.1e-14. All four figures are byte-identical.
  The standard output differs on its timing lines alone and the error
  output is empty on both sides.

  *What `inputs.json` adds.* 1,233 entries against 261. The 261 shared
  entries hash the same. The 972 added entries are the `parts/*.parquet`
  cell files of the nine TabICL and eighteen TabPFN score directories. The
  script hashes every file of each score directory it names, and git
  ignores these files. The pooling reads `scores.parquet` and
  `reference.parquet` and not the parts. All 972 hash the same against
  the files on this machine.

  What is not here. A reading. Every entry above that reads the recording
  of 2026-09-19 reads this one, at the four decimal places the ledger
  quotes.

## Cold audit

Audited 2026-09-04 by an auditor given `vintage.py` and what it imports, the
tests, the two producing scripts, the four recorded runs with their manifests
and this file, and asked what the grid permits a model to see — not what it was
designed to permit, and not the reasoning behind either.

All four manifests carry `git_dirty: false` and the same input hash, and the
data file on disk still hashes to it. `arm-contrast.json` re-derived
byte-identical under independent reimplementation; every `train_rows`,
`blind_rows`, cohort count and scored-row count in `builds.json` re-derived
exactly on both arms; the scoring sample is stable under three settings of
`PYTHONHASHSEED`, and both arms score identical row tuples per build.

The temporal separation holds on all eighteen builds, re-derived from the
origination dates rather than from the summary fields. The newest training loan
of every build is originated thirteen months before the oldest loan it is then
scored on, 395 to 397 days, and no row is on both sides of any build. A build
cut for a six-month lag is refused under a twelve-month label. The label reads
only `loan_status` and `last_pymnt_d`, both declared label sources and excluded
from the feature set, and it dates a default by the estimated default date, so a
loan that charged off in month twenty is a non-default at twelve months. No
imputation, encoding, screening, sort or index reuse crosses the boundary,
because no such step exists in the audited pipeline. All 151 column
classifications in `lending_club.py` were checked one by one with no
misclassification found.

Four findings constrain what this grid can be read to answer, and they are about
the hypotheses rather than about the split.

- **The stability criterion of H3 is saturated before a model is fitted.** At
  the study's sample sizes the Yurdakul critical value
  `chi2(0.95, 9) * (1/M + 1/N)` is 0.00086 against the largest expanding pool
  and 0.00139 against the smallest rolling pool — sixty to a hundred and twenty
  times *below* the 0.10 folklore line this file rejects. Every model crosses on
  every cohort, so a count of crossings compares two saturated counters, and the
  stated fallback of reporting the age at first crossing degenerates the same
  way at age one. The critical value is right for a statement about one cohort
  and wrong as the input to a counter.
- **Two kill criteria have no noise floor and one cannot fire.** The scorecard
  and the full-pool GBM are deterministic given the build, so their seed spread
  is zero. H1's second branch asks whether a slope differs from zero by more
  than a spread of zero, which every non-zero estimate does. H2's primary
  compares a three-seed quantity against a zero-variance one with no interval on
  either.
- **The first clause of H2 is entailed by the design.** Each build's training
  pool sits 0.12 to 0.92 points below the mean rate of the cohorts it scores, on
  both arms and at every build. Any model calibrated on its own pool therefore
  arrives at an observed-over-expected ratio of roughly 0.73 to 0.97, against a
  binomial standard error of about 4% relative at 20,000 rows and a 3% rate. The
  loss of calibration-in-the-large is a property of the split; only the
  comparative half of H2 carries information about the models.
- **Model age and calendar quarter are exactly collinear given the build.** For
  a build with label horizon quarter `h`, the age at which it scores cohort `q`
  is `q - h`, and `h` takes one value per build, so age, period and build are
  rank-deficient. A difference of slopes cancels the common component and H1
  survives as a comparative statement; a sentence of the form "models decay out
  of time on this book" does not follow from this grid. The scorecard run of
  2026-09-04 shows the same thing directly, from the `cohorts.csv` of
  [`experiments/2026-09-04-lc-scorecard-uniform`](../../experiments/2026-09-04-lc-scorecard-uniform):
  the variance of mean Gini across scored cohorts is 3.5 times the variance
  across model ages, and the spread within a cohort is smaller than the spread
  within an age.

The rewriting the last two points call for is not made here. The hypotheses
stand as pre-registered; an amendment is dated and recorded in this file when it
is made, and no result is written up against a criterion that changed after the
numbers were seen.

Three further findings are defects rather than constraints, and none of them
touches a recorded run.

- **`builds()` accepts a label lag that disagrees with its eligible set.**
  Called with `label_lag_months=24` and the twelve-month `LabelSet`, it returns
  nine builds and nothing raises, and 35.4% of the scored rows then carry an
  immature label counted as a non-default, concentrated in the newest cohorts.
  That is the failure the label module exists to prevent, arriving through the
  splitter. The twenty-four-month sensitivity check of ADR-0005 runs into it,
  and no test covers that path.
- **`eligible=` is presently doing no work.** The twelve-month maturity cutoff
  of 2018-03 and the constant `LAST_TEST_COHORT = 2018Q1` coincide, so passing
  the `LabelSet` changes no cohort. Immature loans are kept out by the constant,
  which has to be changed by hand whenever the window changes.
- **Two assertions are not exercised by any test.** Under mutation testing nine
  of eleven assertions in `vintage.py` and `splits.py` went red when disabled.
  The train-and-score overlap check did not, because the horizon check fires
  first on the case its test constructs and the test matches no message. Nor did
  the check that the newest training loan's window closes before the oldest
  scored loan is written, which is unreachable given the two inequalities that
  precede it, while the comment above it describes it as an independent second
  check.

Two statements in this file were narrower than written and are corrected above:
the book's rate rose by a factor of 1.72 rather than nearly doubling, and it
rose in one step between 2015Q4 and 2016Q1 rather than as a trend — the last
nine of the nineteen scored cohorts are flat at 2.9% to 3.4%, so the three
newest builds score almost no base-rate movement. The margin between a training
loan's label maturing and the oldest scored origination is 0 to 31 days rather
than 30, because `issue_d` has one-month resolution.

Three gate texts describe checks the code does not run, all in
[../protocol/gates.md](../protocol/gates.md): `embargo_days` is left at zero by
`vintage.builds`, which is safe here only because `assert_no_leakage` does the
work by another route; no manifest carries a seed field; and the hygiene checker
implements attribution and meta-commentary but not the rule about numbers in
prose without a claim ID.

The verdict was that the runs support a weaker claim than the design suggests:
that a grid exists on this book in which no training loan's twelve-month outcome
was observable at the build date, no scored loan existed at it, and no row is on
both sides — and that the grid forces every model to carry a base-rate gap of
0.1 to 0.9 points at every build. Not supported: that the grid separates entity
leakage, that H2 or H3 as written discriminate between models, that an
AUC-against-age slope from it measures ageing, and that the twenty-four-month
check runs as promised.

`src/outoftime/features.py` and `src/outoftime/scorecard.py` were written after
the audit began and were not examined by it. They were audited separately the
same day, below.

### The matrix and the scorecard

Audited 2026-09-04, later, by a second auditor given `features.py`,
`scorecard.py`, their tests, `scripts/scorecard_builds.py` and the recorded run
`experiments/2026-09-04-lc-scorecard-grid`, and asked whether anything the
model is shown carries information from after origination or carries the
calendar, whether the fit reads only the rows it is given, whether the card is
what it says it is, and whether the run reproduces.

What held. The fit reads only its rows: under an adversarial frame — rows
outside the window given an all-missing column, an unseen dominant category,
values of 10⁹ and inverted labels, and a permuted row order — names, IVs, bin
tables, coefficients and intercept were bit-identical to the fit on the window
alone, and scoring pathological rows then re-scoring the originals returned
identical predictions. The card is what it says: over 293 characteristics
across the eighteen builds none exceeds twenty per build, none is below the IV
screen, none has a non-negative coefficient, none has a non-monotone event
rate across its bins, and WOE and IV recomputed from the raw bin counts match
the recorded values to 5×10⁻⁷. Three of four builds refitted at the manifest
commit reproduced every bin, coefficient and per-cohort metric exactly; 47
per-cohort cells recomputed with independent implementations agreed to 3×10⁻⁶
on AUC and 10⁻⁸ on Brier. The label rebuilt independently matched in every
count. The declared identities behind every dropped column reproduced.

What did not, in order of weight.

- **Sixty-eight columns carried the calendar in their missingness.** Lending
  Club began reporting them in batches — 2012Q2 to 2012Q4, 2013Q2, 2016Q1,
  2017Q3 — and before the batch date they are empty on every loan. On a
  training pool starting in 2010 the binner's Missing bin is therefore "written
  before the batch", with a default rate attached: in the 2017H1 expanding
  build the Missing bin of `open_il_12m` held 77% of the pool at WOE +0.07 and
  0% of the scored rows. Holding those characteristics at their training-mean
  contribution moved the 2017H1-E observed-over-expected on 2018Q1 from 1.25
  to 1.43. The rule adopted in reply is uniform coverage: a column stays only
  if it is populated from the first cohort of the book, the sixty-eight are
  listed with their onset quarter in `features.LATE_COVERAGE`, the run
  re-measures every onset and stops on a disagreement, and the matrix is the
  twenty-nine columns reported from 2010Q1. The run superseding the audited one
  is `experiments/2026-09-04-lc-scorecard-uniform`.
- **The binning was not reproducible across processes.** Refitting 2013H1-E at
  the recorded commit under CPU load gave `revol_util` an extra split at
  48.45, status `OPTIMAL` in both cases: optbinning's CP-SAT solver runs a
  portfolio of workers and returns whichever member of a tie set finished
  first. Reproduced here — two binnings in eight fits under load — and absent
  under the single-threaded mixed-integer solver on the same model, eight of
  eight. The policy now names the solver, and the recorded determinism check,
  which refits inside one process, is kept as the weaker check it is. The
  effect on the audited numbers was below 10⁻⁴ on every metric.
- **The log entry above overstated three things.** The post-2015Q1 O/E range
  on the expanding arm was 1.015 to 1.696 with sixteen of ninety-nine cells
  outside the stated 1.20 to 1.60; the age-invariance clause hid a
  cohort-fixed-effect O/E slope of +0.005 per quarter of age; and
  `fico_range_low` was removed for sign in ten builds, not eight. The entry
  for the superseding run is written from its own artifacts.
- **`sec_app_fico_range_high`** satisfied the module's own redundancy rule and
  was not listed under it. It is out with the joint-application batch.
- **The composition figure** drew "never offered" identically to "below the
  screen"; the three blank meanings now have three marks. The trajectory
  figure's title claimed to show what ageing costs; it does not, and says so.
- **The entity check never runs** on this file, which the Setting states; the
  run's summary now says it too, so the artifact carries the limitation.
- The coefficient tolerance was 10⁻⁴ against six reported decimals; it is
  10⁻⁸. The `int_rate` identity was written as exact and holds on 94.7% of the
  book; the wording now says so.

Verdict: supports a weaker claim. What the audited run supported — a properly
built scorecard refit at nine dates under-predicts every cohort from 2015Q1
onward by a fifth to seven tenths, and the movement in discrimination and
calibration tracks the cohort scored far more than the card's age — is
restated from the superseding run in the log, and every cross-build sentence
about calibration is read with the coverage finding in mind.

### The uniform run

Audited 2026-09-04, late, by a third auditor given the run
`experiments/2026-09-04-lc-scorecard-uniform`, its manifest, the seven modules
and the script that produced it, and the raw file — and told not to read the
working notes. It recomputed from the raw gzip: the row, snapshot, label and
training-pool counts; two cohorts' default counts; and, refitting 2013H1-E and
2017H1-E at the recorded commit under a different CPU load, every reported
Gini, observed-over-expected and Brier on those builds to six decimals.
Everything reproduced. Temporal discipline held on all eighteen builds against
the origination dates: no training row after `T − 12m`, no scored row on or
before `T`, no row on both sides, a minimum of 395 days between the newest
training origination and the oldest scored one. The written artifacts held no
NaN, no repr strings, no duplicate cells.

What did not hold, in order of weight, and what was done.

- **Five kept columns were zero on every loan before 2012Q4**, passing the
  presence-based coverage rule while carrying the calendar by value; the
  auditor found them by measuring per-quarter non-zero shares, which
  `coverage_report` could not. Answered by the amendment above, which widened
  the finding on re-measurement to nine columns and two clipped ranges.
- **The stdout table presented a cohort effect as an ageing effect.** Its
  "oldest" column was 2018Q1 for every build and its "age 0" column a
  different quarter for each, at age one. On `cohorts.csv` cohort explains
  51% of Gini variance, build 48%, age 13%; on the one cohort every build
  shares, the spread across all eighteen is 0.0082, under the 0.024 standard
  error of a single Gini at 638 defaults in 20,000 rows. The table now names
  the cohort in each column. The claim "the scorecard decays out of time on
  this book" is not supported by the run and is not made.
- **No noise floor anywhere in the run**, and swings of 0.05 to 0.09 inside
  one build's Gini line are about 1.5 standard errors. The run's docstring
  says intervals belong to the metrics module; the auditor's point is that
  the plots' visible structure is not established by the artifact that draws
  it, and six-decimal Gini in `cohorts.csv` exceeds what gates.md §2 permits.
  Answered by the amendment's cohort-blocked bootstrap, owed by the metrics
  module; nothing in this run is cited to more than three figures.
- **`card-composition.png` used a different colour scale per panel**, and the
  recorded figure predates the commit that fixed its clipped title, so the
  artifact and the branch head disagree. One scale now; the superseding run
  carries the figure its code draws.
- **Missing bins of two rows carried the largest weight on the card**, −3.65
  on `dti` at 2016H2, applied out of time to every row lacking the value. The
  amendment's `min_missing_count` answers it.
- **Entity leakage is unmeasured, not measured clean**, and the auditor could
  not bound it either: two proxy keys with a shifted-key placebo gave an
  excess over coincidence of −0.11% to +0.25%, so the 15.9% crude bound cited
  in the Setting from `lc-label-sensitivity` most likely measures coincidence
  too. The Setting's statement stands — no result here may be described as
  free of entity leakage — and the 15.9% figure is not to be read as a bound
  on repeat borrowers.
- **The card's discrimination is increasingly the lender's own grade**:
  `sub_grade` IV rises from 0.28 to 0.52 on the expanding arm with nothing
  else above 0.13, which the Setting already states. The auditor's addition is
  that most of the build-to-build movement in age-one Gini is Lending Club's
  grading sharpening, not the scorecard method behaving differently, and that
  the 0.05 bin-size floor against a 2.9% event rate excludes every rare flag a
  risk team would coarse-class as 0 versus 1+. Recorded; not changed.
- **The manifest's input hash is of the CRLF working-tree file**, not the LF
  blob git stores, so it will not verify on a POSIX checkout. Recorded as
  repository debt; the hash convention is the recorder's to fix.
- Smaller: `age0` was age one; one stdout number printed to sixteen digits;
  the log entry for the grid run was not yet superseded in this file (it is
  above, and the uniform run's entry stands on its own artifacts).

The verdict was that the run supports a weaker claim than its table invites:
that on this book, under a grid where no training loan's twelve-month outcome
was observable at the build date and no scored loan existed at it, a
monotonic-WOE-and-logistic scorecard reaches a Gini near 0.37 on the 2018Q1
cohort whichever of nine build dates or two window policies produced it, and
under-predicts the realised twelve-month default rate on every cohort from
2015Q1 onward by 20% to 77%, by an amount that is a near-deterministic function
of its own training-pool base rate — `expected / train rate = 0.83 ± 0.03`
across all eighteen builds. Not supported: that the scorecard ages, that
discrimination decays with model age, that expanding beats rolling, or that the
matrix carried nothing that dates a loan. The run is superseded by
`experiments/2026-09-04-lc-scorecard-byvalue` on the twenty-column matrix.

### The byvalue runs

Audited 2026-09-04, late night, by a fourth auditor given the two `-byvalue`
runs, the grid run, the code and the raw file, and told not to read this
document or the notes. Three builds refitted from raw at the recorded commit
landed on the recorded numbers to six decimals: the scorecard at 2013H1-E, the
GBM at 2013H1-E and 2013H1-R with the same point, round count and log-loss.
Row, label, cohort and pool counts reproduced. Temporal discipline held on all
eighteen builds against the dates, and every GBM early-stopping slice
re-derived to the recorded quarters, was the latest of its pool, and held no
scored row. The value rule's twenty shares reproduced to six decimals; the
values inside the first cohort's range but absent from it — 21.6% of `dti`,
11.1% of `loan_amnt` — were tested and are the first cohort's sample size, not
an onset. Artifacts clean; the fixed sample identical across builds, arms and
runs.

What did not hold, and what was done.

- **The context control's seed band was mostly search noise.** At 2013H1-E
  the three draws share 97.6% of their rows — the pool is 50,609 — and still
  chose three points and 150, 147 and 63 rounds; fifteen of eighteen builds
  had their draws land on different points, by margins from 1.5 × 10⁻⁴ to
  3 × 10⁻⁶ in log-loss. A zero-shot model has no search, so the band was a bar
  built from the challenger's own instability. The control now takes the
  point its build's full-pool search chose and re-chooses only the round
  count; the band is the band of the rows.
- **The search's best point sat on the grid's edge** — fifteen leaves at 69
  of 72 fits, the slow rate at 62, two hundred rows per leaf at 53, six
  columns in ten at 53, all four at once at 35 — and no note said so. The one
  full-pool fit that chose sixty-three leaves, 2017H1-E, did so by 3 × 10⁻⁶
  and is the one column of `importance-drift.png` where `sub_grade`'s share
  falls. The grid now reaches seven leaves, a thousand rows per leaf and four
  columns in ten, and a best point on any edge is written into the run's
  notes with the margin it won by.
- **The clip moves expected rates in the direction of the drift**, on a share
  of each cohort that rises from 0% in 2010 to 38% by 2018Q1, and the value
  report recorded a zero for it because it measured after clipping. Measured
  against the unclipped uniform run on the 198 cells the two share: the clip
  lowers the expanding arm's expected rate by 0.002 points before 2015Q1,
  0.008 in 2015–2016 and 0.022 from 2017Q1, moving observed-over-expected by
  +0.001, +0.006 and +0.015 on average (+0.07 at most in one cell) against a
  drift from 0.85 to 1.55. The mechanism is real and its size is one to three
  percent of the drift. The report now records the pinned share per quarter.
- **`calibration-drift.png` was titled by age** over an axis of cohort, and
  the GBM's trajectory figure had dropped the scorecard's warning; both
  titles now say what the axes hold. `card-composition.png` omitted the five
  columns no card ever kept; it shows all twenty.
- **`gbm.json` carried no `entity_check`, `seeds` or `tuning_budget`.** It
  does.
- **`vintage.py` said the arms make volume and recency separable.** They do
  not — rolling pools grow fifteenfold across the grid, expanding ones
  twenty-twofold — and the sentence now says so. What holds volume fixed is
  the context, and on the shared cohort the context control's flat Gini
  against the full pool's rising one is the reading: volume buys about 0.02,
  recency at fixed volume little.
- Recorded, not changed: `mths_since_last_delinq`'s missing share steps from
  64% to 46% at the 2012Q4 bureau batch, a shape the coverage floor cannot
  see; the column never reaches a card and takes 3.8% of GBM gain. The matrix
  is chosen with knowledge of the whole book, which no 2013 builder had; the
  handicap is identical for every model, and the runs do not measure what a
  2013 team could have built. The 15.9% entity figure stays uncited.

The verdict: the temporal design supports its claim on every build; the model
comparison supports a weaker one — on the full pool the tuned GBM edges the
scorecard by about 0.024 of Gini on the shared cohort, 16 of 18 builds
positive, against a paired standard error of 0.012 and a seed range of the
same order; at a 50,000-row context the GBM and the scorecard are
indistinguishable, +0.001; the GBM's whole advantage is a data-budget effect.
Nothing about ageing is supported: cohort explains three to four times the
Gini variance that age does, for all three models, and nine cards of nine ages
expect nearly the same rate of any cohort. The runs are superseded by
`lc-scorecard-byvalue2` and `lc-gbm-wide` under the corrected protocol.

### The corrected-protocol runs

Audited 2026-09-04, past midnight, by a fifth auditor given `lc-scorecard-byvalue2`,
`lc-gbm-wide`, the grid, the code and the raw file, and told not to read this
document, the notes or the sibling runs. One scorecard build and two GBM
builds refitted from raw at the recorded commits landed on every recorded
number — the card, the bins, all seventeen cohorts' metrics, the thirty-six
trials, the three context draws — to the last digit; the only field that
differed anywhere was a trial's wall time. All eighteen builds held the
temporal inequalities against the dates; every validation slice was the
latest tail of its pool; every context draw carried its build's point with
only the round count differing; every edge note named exactly the knobs at an
extremum and every stated margin matched the trials; the clip shares
reproduced to six decimals; the manifests named the commits the runs started
from and their hashes verified after line-ending normalisation.

What did not hold, and what was done.

- **LightGBM's `feature_pre_filter` had made the search and the control two
  different models.** The option drops, when the dataset is built, every bin
  that cannot satisfy `min_data_in_leaf`; the dataset is built once, by the
  first training call, and reused. Thirty-six points were therefore scored on
  bins filtered for the first point's two hundred rows per leaf, and the
  control, building a fresh dataset at the chosen thousand, saw different
  bins. Demonstrated on 2013H1-R, where the control's rows *are* the pool:
  77 rounds and log-loss 0.12299 through the search, 71 and 0.12355 alone,
  identical rows and parameters — a gap of 5.6 × 10⁻⁴, larger than every
  margin the search decided by. Reproduced here on the same build before
  anything was changed. The filter is now off on every dataset the module
  builds, a test holds a point to the same score alone and inside a grid, and
  the run is repeated.
- **The edge note reported every choice on a two-level knob as an edge**,
  which says nothing. It now reports only knobs with an interior.
- **The tuning is nominal.** Margins of 3 × 10⁻⁶ to 3 × 10⁻⁴ in log-loss
  decide between points whose Gini on the shared cohort differs by less than
  a paired standard error of 0.008 to 0.010; a thousand rows per leaf won at
  all eighteen builds. The word for what the GBM is, from here on, is *tuned
  within a stated budget on a surface flat at the resolution of the result*,
  and the per-build hyperparameter table and `importance-drift.png` are not
  read as measurements of drift — the search re-chose per build on noise.
  The `sub_grade` trend survives (its share of gain does not correlate with
  the column fraction chosen); the rest of the heatmap is not separable from
  the search.
- **No noise estimate exists for the scorecard or the full-pool GBM in the
  artifacts**, and the auditor supplied the missing one by paired bootstrap on
  2018Q1: single-Gini standard error 0.020; paired standard error of the
  GBM-minus-scorecard difference on identical rows 0.0099, so a single build's
  +0.017 has an interval straddling zero and only the pooled sign pattern and
  the pool-size trend stand. This is the amendment's bootstrap, owed by the
  metrics module, and until it lands no per-build difference is cited.
- Recorded, not changed: the per-quarter pinned share divided by all rows
  while the pooled one divided by non-missing (now both non-missing; the
  values move by under 10⁻³); two figure titles were clipped by the layout
  (wrapped); the CSVs did not carry `context_is_whole_pool` (they do); the
  manifest hashed the script and the data but not the library that the
  command never names (it now hashes every module under `src/outoftime`).
- Restated by the auditor, already in the Setting: the entity check cannot
  run on this file; the matrix is twenty columns with two of them clipped,
  and 0.35 to 0.43 of Gini is the ceiling of this matrix rather than of the
  problem; `sub_grade` is the lender's own grade and by 2016 carries 0.60 of
  the GBM's gain, so both contenders re-predict the lender's underwriting and
  the calibration failure across 2015–2018 is partly the grade's failure to
  keep up with its own book; nothing about calibration shape or population
  stability exists in the runs.

The verdict: supports a weaker claim. The strongest statement the artifacts
carry, on the shared 2018Q1 cohort: *the challenger's advantage over the
scorecard is bought with rows, not with model class* — given the same 50,000
rows the two are indistinguishable, +0.005 on average and negative at four of
eighteen builds against a seed spread of 0.005–0.032 and a paired standard
error near 0.008; given the whole pool the GBM leads at all eighteen, and the
lead tracks the pool, +0.006 at 50,609 rows to +0.059 at 1,108,732. Two weaker
statements also hold: neither model's discrimination decays with age on this
book, and both fail calibration in the large in the same direction by the
same amount, dated by the calendar. Not supported: "the tuned GBM" without
its qualifier, anything drawn from hyperparameter or importance movement, any
per-build significance, and anything about calibration beyond its level. The
GBM run is superseded by `lc-gbm-wide2` with the filter off.

### The scores and intervals of 2015H1-E

Audited 2026-09-05 by a sixth auditor given `lc-2015h1e-scores`,
`lc-2015h1e-intervals`, the code, the raw file and the pre-registration
sections of this document only. The auditor reports that the file arrived
whole and that the log entry of 2026-09-05 was read with the rest, so the
audit was not blind to the expected finding; the arithmetic below was all
re-derived in the auditor's own code and is independent, the framing is not.
The log and the audits should live apart from the pre-registration before the
next audit is ordered.

Every class of number reproduced from the row-level artifacts: Gini on 2016Q2
for three models to 2 × 10⁻¹⁶ against `metrics.parquet`; DeLong from the
structural components (standard error 0.0093 on the GBM's 2016Q2 cell,
against 0.0089 by row bootstrap); the observed-over-expected cell and its
binomial interval exactly; six PSI cells and both critical values exactly,
with nine interior edges and ten non-empty bins on every cell, so the nine
degrees of freedom are the binning's; and all eighteen pooled intervals and
standard errors to five decimals from a reimplementation of the
cohort-blocked resample. All five cells hold the identical 220,000
(cohort, row) pairs in the same order with identical outcomes, none of them
among the 323,026 reference rows; the labels rebuilt from the raw file
matched on every scored and every training row; the newest training
origination is 2014-06-01 and the oldest scored one 2015-07-01. The manifests
say clean, and every recorded hash matches the committed blob after
line-ending normalisation.

What did not hold, and what was done.

- **An interval that mixes three context draws is not a distribution.** The
  bootstrap chooses one of the control's three draws per resample, so its
  interval on anything involving `gbm-50k` is a percentile of a three-atom
  mixture, and the auditor found the three atoms disjoint on every paired
  statistic once the draw is held fixed: on Gini against the scorecard
  [−0.003, +0.006], [+0.004, +0.014] and [+0.004, +0.016] where the mixture
  reads +0.007 [−0.002, +0.016]; on |log O/E| against the full-pool GBM two
  draws sit at +0.037 to +0.040 and the third at −0.010 to −0.006, and the
  mixture reads +0.023 with an interval holding zero; on PSI against the
  full-pool GBM one draw is positive and two negative, each clear of zero,
  and the mixture reads +0.0003, "no difference". The mixture is the
  amendment's own kill criterion firing — the effect inside the seed
  spread — dressed as an ordinary interval, and every comparison of a
  foundation model against the control would inherit it. The intervals
  script now repeats the pooled interval with each draw held fixed, writes
  those rows beside the mixture with the draw named, and flags every
  difference whose draw intervals are disjoint; the mixture remains the
  pre-registered floor and is read only with the flag. The three draws also
  differ in early-stopping rounds (44, 59, 51), so the draw spread carries a
  round-count re-selection with the rows.
- **The cohorts are held fixed, so the floor is conditional on these eleven
  quarters.** Resampling the cohorts as well as the rows leaves the sign of
  the full-pool GBM's lead intact ([+0.010, +0.030] against [+0.014, +0.025]),
  takes the control's shortfall against the full pool to the edge of zero
  ([−0.024, −0.0005]), and widens the |log O/E| difference between the GBM
  and the scorecard seven and a half times: the observed side cancels within
  a pair on one cohort, and the difference swings from cohort to cohort with
  a between-cohort standard deviation of 0.012 on the paired Gini. The
  bootstrap now offers the cohort-resampled pooling and the script reports
  it as a third row. Which of the two the kill criteria read is not decided
  here; the amendment names the cohort-blocked one, and any sentence about a
  quarter outside the pool needs the wider.
- **The control carries the full pool's hyperparameters** — seven leaves, a
  thousand rows per leaf, chosen on 323,026 rows and handed to 50,000, where
  a thousand rows is two percent of the sample per leaf and one draw's search
  note says every point stopped inside the patience. `gbm-50k − gbm` is
  therefore rows and inherited tuning together, and the asymmetry runs the
  other way from the one the Setting names: the foundation models get no
  tuning, the control gets tuning it cannot use. Recorded; the protocol is
  unchanged until the falsifying run says whether it matters, and the
  alternative — the control searched on its own tail — is one flag away.
- **The stability comparison carries a reference-size term.** Under the null
  the expected PSI is (B − 1)(1/N + 1/M): 4.8 × 10⁻⁴ for a full-pool
  reference and 6.3 × 10⁻⁴ for a 50,000-row one, and the 1.5 × 10⁻⁴ between
  them is half of the +2.9 × 10⁻⁴ reported for `gbm-50k − gbm`. The reference
  is each model's fitted values on its own training rows, which the two-sample
  null does not describe, and it is seventeen quarters against one, which is
  common to every model and not instability. Nothing turns on it at five to
  seventy-seven times the critical value, and a foundation model's context
  reference will carry the same term against a full-pool comparator; the
  figure now draws PSI as a multiple of each cell's own critical value rather
  than one line at the median, which was the control's value drawn as if it
  applied to all.
- **Eighteen intervals at α = 0.05, no adjustment.** Now stated in
  `intervals.json`; immaterial for the GBM's lead on Gini at seven standard
  errors, material for the one starred |log O/E| difference of the control.
- The manifest recorded the label definition and not the label set, so the
  immature, still-running and unrecognised counts the label module says
  belong there were absent; the auditor recomputed them (unrecognised zero
  book-wide, still-running rising from 11% to 79% across the cohorts). Both
  scripts now record the set.
- The three stability rows of the prior-art table still read `abstract-only`
  after the sweep of 2026-09-05 had read the papers in full and pinned their
  tables in the package's tests; the rows now say so.
- Two numbers in the log entry are restated: the smallest lower bound on
  observed over expected is 1.069, not "above 1.07", and PSI runs 5.0 to 77
  times its critical value, not five to sixty.
- Forward: a foundation-model run that scores the three youngest cohorts
  makes the "all" and "nearest" poolings one pooling; the script no longer
  repeats it as if it were two.

The verdict: supports a weaker claim. Supported, on the 2015H1 expanding
build and conditional on the eleven scored quarters: the full-pool GBM
outranks the scorecard by about 0.020 Gini paired, and that survives
resampling rows and cohorts; every model on every cell under-predicts
defaults beyond binomial sampling, which a 2.33% training pool scored against
2.7–3.4% cohorts entails; and both runs reproduce number for number. Not
supported: any statement about the control that rests on its mixed-draw
interval, including "the control does not differ from the full pool"; a
general noise floor for a paired difference on this book; any reading of the
cells as ageing, since age and calendar are one axis on one build; the
data-budget reading of `gbm-50k − gbm`; and, most of all, the readiness of
the mixed-draw interval to adjudicate a foundation model against the control
— the per-draw rows are what that reading will use.

### The falsifying run and its pooled intervals

Audited 2026-09-06 by a seventh auditor given the two node runs, the bundle,
`lc-2015h1e-scores`, `lc-2015h1e-intervals-tfm`, the job archive, the code,
the raw file and the pre-registration only, with this file kept out. The
auditor reports that it opened none of the excluded files and that the
subject lines of the five newest commits were shown to it by its environment
before it began; those lines state the findings, so the framing was not blind
where the sixth audit's was not either, and the arithmetic below is its own.

What reproduced. The job archive hashes to its manifest; the scorer inside
it is the tree's after line-ending normalisation; the bundle's two parquets
are identical in the archive, in the hosted node's zip and in the tree; the
parts of each node run concatenate to its score files. The twelve-month
label rebuilt from the raw file matches every one of the 60,000 scored and
50,000 context rows; the context is the control's seed-20260911 reference,
row for row, inside the 323,026-row pool; the newest context origination is
2014-06-01 and the oldest scored one 2015-07-01, no row on both sides; the
three cohorts are the three the pre-registration names. Sixty-one cells of
Gini, Brier, observed over expected, PSI and its critical value reproduce to
3 × 10⁻¹⁶, DeLong's interval to 6 × 10⁻¹⁷, and every pooled name of both
poolings to 10⁻¹⁶ from a resampler written without the module. The
stability ordering survives a change of reference: read against each model's
own 2015Q3 scores rather than its training or context rows, PSI on the two
later cohorts orders the five the same way — TabICL, TabPFN, control, GBM,
scorecard — at a quarter of the magnitude; a random half-split of each
reference falls under the critical value; the reference-size term runs
against the finding. The split is built through `temporal_split` with the
gap enforced on dates; the column classification holds at the canonical
trap; `member_id` is null on all 2,260,668 rows, so entity leakage is
unaddressable on this file and is stated as such.

What did not hold, and what was done.

- **|log O/E| against the scorecard is a level, and the level is there
  before any cohort.** Removing each model's own reference-row ratio — one
  scalar, 1.460 for TabPFN and 1.470 for TabICL, 0.999 to 1.000 for the
  classical models — takes the paired |log O/E| from +0.391 to +0.012 for
  TabPFN and from +0.271 to −0.115 for TabICL. Anchored on the first scored
  cohort instead, so that no in-context quantity enters, the drift over the
  next two is 0.139 for TabPFN and 0.132 for TabICL against the scorecard's
  0.155 and the GBM's 0.143. The entry of that run carried the parallel
  drift (log O/E rising 0.21 to 0.23 for all three) and still led with the
  paired |log O/E| rows. The sentence "the foundation models lose
  calibration out of time worse than the classical models" is not
  supported; what is supported is a constant under-prediction of about
  1.46 present on the rows the models were shown, and a decay across the
  cohorts no worse than the scorecard's. Done: the Cox intercept and slope,
  the CORP decomposition and the reliability curve are in the metrics
  module and the intervals script, recorded as `intervals-tfm2`, whose log
  entry reads H2 on the slope.
- **The statistic H2 is written on had not been computed.** The Setting
  names the Cox slope; the amendment's criterion is the slope; the run
  pooled the level. The escape clause of the cheapest falsifying run — H2
  answered without the grid if age-zero calibration is already outside the
  scorecard's interval — is not available on the level: every model on a
  cell shares the identical observed count (541 of 20,000 on 2015Q3 for all
  five), so the five binomial intervals in the middle panel are one
  interval divided by five expected rates, and their non-overlap is not
  evidence. Done: computed, and it points the other way from the level.
- **One context draw, and the summary read as if three had agreed.** The
  TFMs were run on seed 20260911 only, so the script dropped the control's
  other two draws, no per-draw rows existed, and `draws_disagree` was
  written empty. Against each of the control's three draws the pooled PSI
  difference TabPFN − control is −0.0028, +0.0020 and +0.0031 — the starred
  row flips sign on both draws not used, and its size is under half the
  control's own spread of 0.0059, which is the amendment's own "no effect".
  TabICL − control holds its sign (−0.0119, −0.0071, −0.0060). The Gini
  differences hold their sign on every draw, and the reported points are on
  the draw where the control did worst: TabPFN − control +0.0167 against
  +0.0097 and +0.0098 on the other two. Done: the summary now says the seed
  spread is unmeasured when one draw is shared; the starred PSI row for
  TabPFN against the control is withdrawn from the entries above; the TFM
  cells on seeds 20260912 and 20260913 are owed before any sentence about
  the control is written, and the TabICL sentence waits with them.
- **"All cohorts" was three of eleven.** The pooling was right and named
  what it dropped in the summary; the plot legend, the console and the
  paired table said "all". Done: named by count everywhere. The
  cohort-resampled pooling on three cohorts draws from ten multisets and
  is not a between-cohort generalisation; the entries above do not use it
  as one.
- **Settings that move a calibration number and are stated nowhere the
  number is.** Both models shipped `softmax_temperature = 0.9`, and the
  prior-art row on TabPFN records that the package changed its temperature
  handling across versions; TabPFN's realised ensemble size under
  `n_estimators = "auto"` is not recorded; TabICL 2.1.1 ran four days after
  2.2.0 was released; and the tuning-budget asymmetry the baseline gate
  wants in the manifest was in the pre-registration only — in both
  directions, since the control inherits the full pool's point. Done: the
  node script records the budget, the two hand manifests carry a dated
  field, and the temperature is the next probe.
- **The determinism repeat is in-process.** A second fit and score in the
  same process on the same device with the same library seed shows the
  estimator is a function of its inputs there, not across processes or
  drivers. TabICL under automatic mixed precision returned 14,404 distinct
  probabilities in 50,000 rows; the mass on a decile edge is at most
  0.09%, so the binning is unaffected. Recorded; a cross-process repeat
  belongs to the next node run.
- Not checked: no accelerator here, so the recorded probabilities were not
  regenerated from the libraries; what the libraries did with the three
  object columns and with `sub_grade` and `term` passed as numbers; the
  checkpoint hashes against their publishers. One adjacent paper surfaced
  for the next sweep, arXiv:2605.22892 on TabPFN in insurance pricing.

The verdict: supports a weaker claim, and one starred row does not survive.
Supported, on the 2015H1 expanding build, on the three cohorts nearest the
build date, on one context draw: TabPFN-3 and TabICLv2 read zero-shot from
50,000 rows rank 0.022 and 0.023 of Gini above the scorecard, clear of zero
under both poolings, and inside the floor of the full-pool GBM; both
under-predict the arriving defaults by a factor of about 1.5 relative to the
classical models, and that factor is a level already present on their own
context rows; after it is removed their decay across the three cohorts is no
worse than the scorecard's; every model's score distribution moves far past
its critical value on every cohort. Not supported: that the foundation
models lose calibration out of time worse than the classical models; any
sentence about the control that rests on one draw, and the PSI advantage of
TabPFN over it in particular; anything about discrimination decay, since the
TFMs have no cell at the ages where the classical models' Gini falls; the
rolling arm; and any reading past three cohorts of one build.

### The temperature probe, the two draws, the derivation and their poolings

Audited 2026-09-06 by an eighth auditor given the probe run, the draws run,
`lc-2015h1e-intervals-probe3`, `lc-2015h1e-intervals-draws`, the two node
runs of the falsifying run, `lc-2015h1e-scores`, `lc-2015h1e-intervals-tfm2`,
the job archive, the code and the pre-registration with its amendments,
with this file kept out; the derivation run and its pooling were added to
its scope after it had started. The auditor reports that the subject lines
of the newest commits were shown to it by its environment and state the
findings of the draws and the derivation, and that it measured both from
the parquet files before reading the derivation's commit; the finding on
the control's draw count it reached from the pooling's own console line.

What reproduced. The archive hashes to its manifest and sidecar; the scorer
inside is byte-identical to `scripts/score_context.py` at every commit from
`fd5eadf` to the tree, after line-ending normalisation. Every scored row of
all seven (model, seed) cells across the four node runs matches the
classical rows on cohort, row, outcome and age, and every reference row
matches the control's reference of the same seed; realised rates 2.248,
2.278 and 2.340 %. Context and scored rows are disjoint, the context draws
overlap 15.4 to 15.6 %, the twenty features hold no `last_*` column. Every
repeat cell disagrees by 0.0. `build_intervals.py` re-run on the draws
reproduces `paired.csv`, `metrics.csv` and the cell figure bit for bit. From
the rows: TabICL's logit at 1.0 over its logit at 0.9 is 0.90000 with zero
spread, the Cox intercept bit-identical between the two settings, the slope
multiplied by exactly 1/0.9, Gini, KS, AUC and PSI unchanged to six
decimals; TabPFN's departure from the scale 0.0084 on the logit; the
balanced model a constant logit shift of +3.7724 with zero spread. The
derivation's `derive.json` was read as exemplary: formula, source hashes,
library, checkpoint, tolerance, the gaps found, and the eight cells it
could not check named.

What did not hold, and what was done.

- **The probe's pooling holds the control on one draw, and four of its
  seven starred rows against the control do not survive the other two.**
  `shared_seeds` keeps the draws every seeded model carries, the probe's
  models hold draw 20260911 only, and so every comparison against the
  control in `intervals-probe3` is conditional on the control's low-Gini
  draw. Beside the three-draw pooling: Gini TabPFN − control +0.017 starred
  against +0.010 holding zero; |slope − 1| −0.182 and −0.215 starred
  against −0.120 and −0.141 holding zero; PSI TabPFN − control −0.003
  starred against +0.002, a change of sign. The console and
  `intervals.json` said so; `cell-intervals.png` did not, drawing the
  control's three lines beside single lines with nothing to say two of
  them were not in the pooling. The draws entry of the log had already
  read the control on three draws; the probe's comparisons against the
  control are not cited for anything from here. The figure now draws a
  draw the pooling left out dotted and names it as not pooled.
- **The TabPFN temperature contrast is confounded with a change of
  machine.** Its 0.9 rows were scored on the M4 Pro (Metal, torch 2.14,
  one `predict_proba` call) and its 1.0 rows on the T4 (CUDA, torch 2.11,
  chunks of 20,000), so the 0.008 departure from the exact scale is an
  upper bound on the averaging mechanism and not a measurement of it, and
  a fourth-decimal difference between the two settings on a rank statistic
  carries an unmeasured device term: PSI TabPFN at 1.0 − TabPFN at 0.9
  +0.0004 (+0.0001 to +0.0007), clear of zero, a third of the critical
  value. The amendment's "a scale on the logit leaves ranks and deciles
  fixed" is exact for TabICL and holds only to the fourth decimal for
  TabPFN. Acted on in the grid's protocol: TabPFN's two passes are scored
  on one device, and the note of 2026-09-06 below the amendment says so.
- **The probe's kill criterion is an in-sample check.** The reference cell
  is the model's own context rows, so "returns the realised rate at 1.0"
  is a statement about the conditioning set; out of time at 1.0 observed
  over expected is 1.14 to 1.57, which the log entries carry beside it.
  One temperature was tried, and nothing separates "0.9 is a shrinkage and
  1.0 is neutral" from "the level-matching temperature on this book is near
  1.0". Every sentence about the level at 1.0 names the rows it was read
  on; no sentence calls 1.0 the calibrated setting.
- **The primary reading was nominated knowing which reading H2 survives.**
  At 0.9 the slope criterion does not fire for either model; at 1.0 it
  fires for TabPFN and holds zero for TabICL. The amendment is dated after
  the probe and gives its reason, and it obliges both settings on every
  table; the note below it now says in one sentence that the nomination
  was made with that knowledge. The gloss "the classical models' stretch"
  was loose: the full-pool GBM's slope on these cohorts is 1.07 to 1.10 and
  the scorecard's 1.07 to 1.21, and the foundation models at 1.0 sit at or
  above the top of both.
- **The probe's three figures supported nothing.** One shared axis set by
  the balanced model at 0.75 collapsed the other seven reliability panels
  to a dot; the paired figure's |log O/E| panel was set by the balanced
  rows at +2.4; the three tagged models shared one grey; the legend was
  clipped; "one line per context draw" was written for models holding one
  draw; and no figure said that `@t1` is a temperature. The pooling now
  takes `--drop`, and the probe is re-pooled without the balanced rows,
  which the amendment says are not read and which carried nothing beyond
  the level. Each reliability panel takes its own axis and shows every draw,
  the first with intervals and the others thin; a tagged model takes its
  base model's colour with a dashed line and a legend that spells the
  temperature out; the draw sentence appears only where there is more than
  one; the legend wraps. Recorded as
  [`experiments/2026-09-06-lc-2015h1e-intervals-probe3-nobal`](../../experiments/2026-09-06-lc-2015h1e-intervals-probe3-nobal)
  (150 s, seven models, 21 pairs, every interval equal to the probe's
  pooling without the balanced rows), and the two three-draw poolings
  recorded again with the same figures as
  [`experiments/2026-09-06-lc-2015h1e-intervals-draws2`](../../experiments/2026-09-06-lc-2015h1e-intervals-draws2)
  and
  [`experiments/2026-09-06-lc-2015h1e-intervals-tabicl-t1-2`](../../experiments/2026-09-06-lc-2015h1e-intervals-tabicl-t1-2),
  their tables bit for bit those of the runs they replace as citations.
- **The paired figure of the draws hid the disagreement its console
  flagged.** Eighteen of forty differences have per-draw intervals that do
  not all overlap, and the figure drew each as one bar. A difference whose
  draws disagree is now drawn hollow, with the legend saying so. The
  reliability figure of the draws was byte-identical to the one-draw run's,
  since it drew the first draw only; the panels named the draw, and the
  figure now draws all of them.
- **The hand manifests assert fields that were not measured.** `git_dirty`
  and `git_sha` sit in the slots the recorder fills from a working tree, on
  a host that had none; what is established is the scorer's byte identity
  with the commit, not the tree's state. The next hand manifest names the
  commit the scorer equals and carries no dirty flag.
- **PSI is compared across references of different sizes.** The scorecard
  and the full-pool GBM read against 323,026 rows and the seeded models
  against their own 50,000, a difference of 1.5 × 10⁻⁴ under the null,
  about one per cent of the observed differences; the sixth audit recorded
  the term. H3's criterion is the foundation model against the control,
  which is like for like, and only that row is read as H3.
- **Two hundred resamples, one bootstrap seed.** The endpoints are the fifth
  and 195th order statistics and no run varies the seed, so a star at the
  fourth decimal rests on unreported Monte Carlo spread; the context-draw
  term is a plug-in over three draws and understates it. Recorded; a
  sensitivity run on the bootstrap seed is owed before any borderline star
  reaches the ledger.
- The prior-art row on the TabPFN-3 report's temperature history is
  `abstract-only`; the installed defaults are read from `get_params` in
  every `node.json` and stand on their own, and no sentence about the
  default's intent is written until the row is read in full.

Left unexamined by the auditor and still owed to a later one: the classical
run's own construction — the binning, the GBM's search, the split and
knowability code paths — which every pooling stands on and which the third
to sixth audits covered in part; the metric implementations against an
outside reference; cross-device reproduction of any accelerator run, which
the second finding turns on; and `paired.csv`'s standard errors row by row.

The verdict: supports a weaker claim for the probe and its pooling, supports
the claim for the draws, their pooling, the derivation and its pooling.
Supported, on the 2015H1 expanding build, three cohorts, three draws: the
foundation models rank at least as well as the classical models, TabICL
above the control on Gini and PSI, TabPFN holding zero against it on both,
neither clearing the control on the slope; at the shipped temperature both
under-predict by a factor of 1.65 to 2.30 out of time against 1.21 to 1.59
for the classical models, and their slope sits nearer one than the
scorecard's; at 1.0 the level on the context rows is the realised rate, the
out-of-time level 1.14 to 1.57, and the slope 1.13 to 1.23, at or above the
classical range, with H2's verdict differing between the settings as the
amendment obliges the write-up to report. Not supported: any comparison of a
foundation model against the control read from the probe's pooling; the
attribution of TabPFN's 0.008 departure to post-softmax averaging; "1.0 is
the calibrated setting"; any statement of calibration shape from the probe's
figures as recorded; and ageing beyond three quarters.

### The grid and the arm-level pooling

Audited 2026-09-12 by a ninth auditor given the pre-registration with its
amendments, the code and its tests, the nine score runs and bundles of the
expanding arm, the thirty-six node directories and two index directories
of the two foundation models, the nine derived directories, the nine
per-build poolings and the arm-level pooling, with this file and the
working notes kept out. The auditor reports that its environment
showed it the subjects of the newest commits, which state findings, and
that it measured every number it relies on from the parquet and CSV files
before reading any narrative.

What reproduced. The auditor re-implemented the arm pooling on its own
and reports every one of the 2,800 recorded point estimates — the arm and
the nine builds, both poolings with the cohorts fixed, five statistics,
seven models and twenty-one pairs — to 2.2e-16, and the recorded interval
of the H1 row TabICL − control bound for bound with its own resampler.
The split: every build through `temporal_split`, the leakage assertion
against origination dates, the twelve-month blind window, train and test
row sets disjoint, `member_id` empty on the file and the entity
limitation disclosed with its 15.9% bound. The label: immature loans
dropped, the default dated from the last payment and required inside the
window. The twenty features declared knowable at day zero, and the
declaration right column by column. Every foundation-model row on all
nine builds, four directories and three draws matched to the classical
rows on cohort, row, outcome and age, every reference row to the
control's context of the same draw, every probability strictly inside
(0, 1), the temperatures and `balance_probabilities` as declared on every
node manifest, one checkpoint hash per library, all 54 TabPFN and 27
TabICL repeat cells at 0.0. The derivation at 1.0 recomputed from the 0.9
rows with a difference of exactly zero on all nine builds, and TabICL and
TabICL at 1.0 bit-identical on Gini, the AUC slope and PSI, as a monotone
map must be. TabPFN's 2015H1-E rows on draw 20260911 equal to the
2026-09-06 run bit for bit. Every manifest in scope clean and at exit
zero. The baselines read as a risk team builds them and the metric module
carrying the decomposition beside the scalar. The sweep gate green.

What did not hold, and what was done.

- **H1's slope was fitted in the one direction in which model age is not
  identified, and the other direction reverses its sign for TabICL.**
  With one intercept per build, age and calendar quarter are the same
  axis, so the recorded statistic is the calendar slope of AUC net of
  build. The grid identifies age the other way: a cohort is scored by up
  to nine builds, so one intercept per cohort holds the calendar fixed
  and varies the model's age with the pool it was built from. From the
  recorded per-cell AUCs, averaged over draws, the slopes per quarter:

  | model | one intercept per build | one intercept per cohort |
  |---|---|---|
  | scorecard | −0.00046 | −0.00282 |
  | GBM | −0.00022 | −0.00278 |
  | control | −0.00033 | −0.00181 |
  | TabPFN | +0.00008 | −0.00196 |
  | TabICL | +0.00022 | −0.00267 |

  and the differences H1 is written on: TabICL − control +0.00055 with
  build intercepts, −0.00087 with cohort intercepts; TabPFN − control
  +0.00041 and −0.00016. Under the auditor's own bootstrap the
  cohort-intercept TabICL row excludes zero on the wrong side and the
  TabPFN row holds it. The two identifications carry different confounds
  and different weights — the build-intercept slope gives 2013H1-E 34.5%
  and the four oldest builds 87.3%, the cohort-intercept slope gives the
  youngest cohorts most and the two oldest nothing — and neither is
  clean; the finding is that only one was computed. Acted on: the arm
  pooling computes both (`a9edd51`), with a second figure that joins the
  same cells by cohort, and the pre-registration carries a note that the
  build-intercept slope keeps its standing as the criterion's statistic,
  the cohort-intercept slope is reported beside it as a reading added
  after the audit, and where they disagree H1 supports at most the weaker
  claim.
- **H3's pooled excess for TabICL is the step out of sample, not the
  movement along the vintage axis.** The amended reference — the training
  rows for a fitted model, the context draw for a foundation model — is
  the same 50,000 rows for the control and both foundation models (the
  auditor checked all 27 contexts, zero mismatches), and it is in sample
  for every model alike, so the step from those rows to the first scored
  cohort is part of the measurement. Against the build's first scored
  cohort, the same construction for every model and out of sample for
  all, the arm means of PSI over the cells that are not a first cohort
  are scorecard 0.028, GBM 0.018, control 0.017, TabPFN 0.016, TabICL
  0.014: the ordering inverts and TabICL is the most stable model of the
  five, below the control on seven builds of nine. On 2013H1-E, draw
  20260911, TabICL's mean probability on its context rows is 0.0185 and
  on the first scored cohort 0.0236, a step of a quarter before any
  ageing; the control's is 0.0268 to 0.0270. Acted on: the second PSI is
  computed on every table beside the amended one (`a9edd51`) and the
  pre-registration note says which is the criterion's and which was
  added after the audit.
- **The arm pooling gives its weight to the build least like the
  others.** Cells per build run 19 to 3, so 2013H1-E holds 19 of 99 for
  the means and, by the spread of its ages, 34.5% of the build-intercept
  slope. On the H3 row TabICL − control, 2013H1-E supplies 77% of the arm
  value and the two oldest builds 98%; the five youngest builds carry the
  other sign, four of them starred. 2013H1-E's expanding pool is 50,609
  rows against the 50,000-row context, so its three draws share 49,397 to
  49,402 rows and the context-draw component of the interval is absent on
  that build by construction. Acted on: the mean over builds with every
  build weighted alike is reported beside the mean over cells under its
  own scope (`a9edd51`), and the note says a difference is not read as a
  property of the arm where the two disagree in sign.
- **The per-draw intervals of the TabPFN rows against the control do not
  overlap.** Thirty-three pairs on the recorded table carry three draw
  intervals that do not all overlap; on PSI TabPFN − control the three
  draws read −0.0031, −0.0002 and +0.0011, each clear of zero on its own
  side, and the pooled interval of the mixture holds zero. The run flags
  them; the auditor's point is that the flag has to travel with the
  number. Nine of 315 arm differences change their star across the three
  bootstrap seeds, the H2 row for TabPFN among them, and 175 of 315 are
  starred with no adjustment for multiplicity; the six pre-registered
  rows are protected by the pre-registration and the rest of the table is
  not. Recorded here; nothing further to act on beyond the seed check and
  the hollow markers already in place.
- **The control is tuned at twenty times the pool it is fitted on.** By
  the late amendment the control takes the hyperparameter point of the
  full-pool search and re-chooses only the round count; at 2017H1-E that
  point was chosen on 1,108,732 rows and applied to 50,000, and there the
  control's Gini sits below the scorecard's, 0.410 against 0.412 per cell
  on average, where both foundation models on the identical rows sit at
  0.435 to 0.438. The gap between the GBM and the control grows across the
  grid. Acted on: the consequence is stated in the pre-registration note;
  a control searched on its own rows stays an appendix ablation.
- **Two numbers in the pre-registration are stale.** Kill criterion 1's
  52,781 rows at 2013H1 became 50,609 with the late amendment's first
  cohort, clearing the cap by 1.2% and not 5.6%; the Setting's
  ninety-seven characteristics and twenty-nine columns describe the matrix
  the late amendment replaced with twenty. Acted on: both corrected in
  the note.
- **The seeded models' trajectories sit close to their own draw
  spread.** Mean Gini movement between adjacent cohorts within one draw
  against the mean spread across the three draws of one cell: control
  0.0245 against 0.0172, TabPFN 0.0233 against 0.0141, TabICL 0.0242
  against 0.0093. The experiment's third kill criterion does not fire,
  and no single cohort's movement on a seeded model is readable; only the
  paired pooled rows are. Recorded here.
- **The arm script had no test.** Acted on: six tests on the shared
  resample, the two slopes and the second reference (`a9edd51`).
- Smaller: every TabPFN − TabICL row is a cross-device comparison, the
  device term measured at up to 3e-3 on a probability and 2.6e-3 on
  |Cox slope − 1| per cell; the TabPFN-3 and TabICLv2 rows of the
  landscape are `abstract-only` and `tabicl` 2.2.0 was released on
  2026-09-02 while the grid ran 2.1.1; arXiv:2506.02978 is not in the
  landscape. To the next sweep.

Verdicts as reported. H1: does not support the claim as stated — the
computed statistic is the calendar slope net of build, and under the
cohort-intercept identification TabICL's kill fires; at most the weaker
claim that net of build the foundation-model-minus-control AUC gap widens
by about half a thousandth per calendar quarter and no model's own slope
leaves zero. H2: supports a weaker claim — at 0.9 TabICL's |Cox slope − 1|
exceeds the scorecard's on the arm, driven by the oldest build, TabPFN's
holds zero at the margin, and at 1.0 neither differs from the scorecard.
H3: does not support the claim it would be read as — the amended statistic
is measured correctly and TabICL fails it, but the excess is two builds and
the step out of sample, and against an out-of-sample reference the
ordering inverts. The arm pooling: correct arithmetic, contestable
weighting, documented. What the auditor says the runs show: on a correctly
built out-of-time split with a full twelve-month blind gap, two zero-shot
foundation models on the control's 50,000 rows rank borrowers slightly
better than the control, and at the shipped temperature both predict a
level far below the realised rate, which the temperature alone removes.
Left unexamined: the scorecard and GBM internals line by line, the packing
scripts and the archive hashes, the cause of TabICL's step on 2013H1-E,
and any re-score of a cell with either library.

- **2026-09-23 — the level on the context rows, read on every build of the
  expanding arm.** `scripts/in_sample_level.py` on each of the nine builds
  of the arm, one recording per build, over the five score directories the
  arm pooling of 2026-09-22 reads for that build:
  [`experiments/2026-09-23-lc-2013h1e-in-sample`](../../experiments/2026-09-23-lc-2013h1e-in-sample)
  to
  [`experiments/2026-09-23-lc-2017h1e-in-sample`](../../experiments/2026-09-23-lc-2017h1e-in-sample),
  clean tree, exit 0 on all nine. One recording per build because the
  script ranks an arm's builds for EXP-005's H5 from a build record this
  book's does not carry; with one build per recording no ranking is asked
  for, and H5 is not read here.

  *The known answer holds.* On every build the scorecard and the GBM read
  observed over expected of one on their own pool and GBM-50k on each of
  its three draws, 45 cells, each inside its bootstrap interval, and the
  scorecard's Cox fit on its pool reads slope one and intercept zero within
  0.0001.

  *The foundation models, on the rows they were shown.* At 0.9 the mean
  probability over the 50,000 context rows is 0.681 to 0.712 of the
  realised rate for TabPFN and 0.656 to 0.736 for TabICL across the 27
  contexts, observed over expected 1.405 to 1.469 and 1.359 to 1.524, and
  no context's bootstrap interval holds one. At 1.0, TabPFN scored and
  TabICL derived, every one of the 27 contexts of each holds one, the ratio
  0.981 to 1.013 and 0.955 to 1.044. The two-thirds level the entries of
  2026-09-06 read on one build and one draw is the level of every context
  of the arm, and the temperature alone removes it, now from recordings
  that pin the current code.

- **2026-09-23 — the feature gates recorded on their own, at `652f83f`.**
  The gates that shape the matrix were recorded only inside the GBM runs of
  2026-09-04, whose code has since changed, so no recording at the current
  code held them.
  [`experiments/2026-09-23-lc-features`](../../experiments/2026-09-23-lc-features)
  runs them alone on the book the builds load, by
  `scripts/lc_feature_run.py`, and fits nothing: clean tree, exit 0.

  *What comes back.* The three reports agree with
  `2026-09-04-lc-gbm-byvalue/gbm.json → gates` on every one of its 607
  values, bit for bit; the new recording adds the share of the window each
  cap pins, overall and per quarter, which `value_report` records since.
  Of the 107 columns knowable at origination, 20 are kept; 68 are dropped
  for coverage, their measured onsets equal to the declared ones, in six
  batches (2012Q2 10, 2012Q3 2, 2012Q4 25, 2013Q2 1, 2016Q1 14, 2017Q3 16);
  9 by the value rule, eight of them with an onset at 2012Q4 or later and
  `addr_state` at 2010Q4; 6 as redundant, two of them the calendar carriers
  `int_rate` and `installment`; 4 before any measurement, free text and the
  three-digit zip code. The two caps pin 23.2% of the window on `dti` and
  13.1% on `loan_amnt`. `dropped-columns.png` draws every coverage and
  value drop by origination quarter with its onset.

  What is not here. A reading of any model.

- **2026-09-24 — the twenty-four-month check of ADR-0005, fixed before its
  number.** ADR-0005 registers the label at twelve months and the same
  trajectory computed again at twenty-four months and reported beside it;
  the Setting names it the sensitivity check. No model has been read under
  it. The first cold audit found that the splitter, called with a
  twenty-four-month lag and the twelve-month label set, counts immature
  loans as non-defaults; the guard added then refuses that path. The
  check was not taken up again before this entry, which is written after
  every criterion row of this book was recorded.

  *What is read.* The recorded scores of every model on every build of the
  expanding arm, as the criterion's poolings read them
  ([`experiments/2026-09-22-lc-arm-e-intervals`](../../experiments/2026-09-22-lc-arm-e-intervals)),
  are read against the twenty-four-month label of C-004: the same snapshot
  and charge-off lag, the window twenty-four months. The label is written
  beside `outcome` in each score file and read through `arm_intervals.py
  --outcome`, which already reads a second label written that way on the
  other book, with everything else in the criterion's reading held as it
  is. Nothing is refitted. The models are the
  twelve-month models, so the check shows whether a criterion's paired
  difference holds when the same scores meet a longer outcome; it does not
  show whether models fitted to that outcome would rank alike. A refit on
  pools cut for a twenty-four-month window is not done: it changes the
  pools and the blind gap, so a difference could no longer be put on the
  window, and TabICL scores only on a CUDA accelerator, which the study does
  not have.

  *The cells.* A scored cohort enters only if its twenty-four-month window
  has closed at the snapshot, which ends the trajectory at 2017Q1, four
  quarters before the twelve-month one ends. A scored row whose window is
  open is dropped and counted. It is never written as a non-default. A
  cell is read whole or not at all. The criterion's floors apply
  unchanged. The cell count and each build's weight are printed beside every row, because
  the youngest builds lose most or all of their cells.

  *What each criterion reads.* H1: the slope of AUC on age under both
  identifications, at the criterion's poolings and check seeds. H2: the Cox
  slope against the twenty-four-month outcome, reported under that name and
  not as a reading of calibration. A twelve-month probability read against
  a twenty-four-month outcome is off by the horizon, and a scaling common to
  every model's slope can reorder their distances from one. Observed over
  expected and the other level statistics are not read. H3: the stability
  index does not read the label. On the twenty-four-month cells it is the
  same statistic on fewer cells and is reported as that, never as a label
  check. The criterion's temperature is read, with the rows at 1.0 beside
  it as on the twelve-month rows.

  *What counts as a disagreement.* The two windows disagree on a
  criterion's pair when its difference lies beyond the interval on one
  window and holds zero, or lies beyond it with the opposite sign, on the
  other, both read on the cells the two windows share. A change of size
  with both intervals on the same side of zero, or both holding it, is not
  a disagreement. A disagreement is reported beside the twelve-month
  verdict as the finding. No verdict changes standing. The criteria are
  twelve-month by registration.

- **2026-09-24, later — three details of the twenty-four-month check, fixed
  before its number.** The entry above leaves three things to the code, and
  the code is now written.

  The cells are 64. Each expanding build keeps its scored cohorts through
  2017Q1: 2013H1-E keeps 15, each later build two fewer, 2016H2-E one and
  2017H1-E none. A build with one cell has no slope of its own and no second
  stability reference, so the build-intercept slope and the other arm-wide
  rows read it as they read any build, while the rows that weight every
  build alike average over builds and cannot be read with it. They are
  reported as unreadable. No build is dropped to make them readable.

  The comparison the disagreement rule names, on the cells the two windows
  share, needs the twelve-month label read on the same 64 cells, so that
  pooling is recorded beside the twenty-four-month one, from the same copies
  of the score files, with `--outcome outcome` and nothing else changed.

  The cell count and each build's weight are printed once per pooling.
  They follow its table and are written to `weights.json` beside it.

- **2026-09-25 — H4's pooling recorded again at `3e8954b`.**
  [`experiments/2026-09-24-lc-between-arm-intervals`](../../experiments/2026-09-24-lc-between-arm-intervals),
  `between_arm_intervals.py` with the command of the recording of 2026-09-17
  and the output directory alone changed, on the Apple node from a clean tree
  at `3e8954b`, exit 0, wall 5,355 s, on the same host, Python and package
  versions as that recording. **It supersedes the recording of 2026-09-17;
  cite it.** That recording pins five scripts whose code has changed since
  (`ablation_intervals.py`, `arm_intervals.py`, `build_intervals.py`,
  `derive_temperature.py`, `score_context.py`), so it can no longer be cited
  as evidence; every code file the new recording pins is identical at HEAD.
  The 2,449 files it read are the ones `inputs.json` of 2026-09-17 records,
  hash for hash. Its `paired.csv` (1,215 rows), `paired-seeds.csv` (468),
  `cells.csv` (1,683), `inputs.json` and both figures are byte-identical to
  that recording's; `summary.json` differs in `wall_seconds` alone and
  `stdout.txt` in its timing lines. No value, bound, star or reading string
  changes, the entries of 2026-09-16, 2026-09-17 and 2026-09-19 on H4 stand as
  read, and the line numbers they quote hold in the new recording: each
  model's own E − R at `paired.csv` l. 4–22, H4's rows at l. 23–28, their
  check seeds at `paired-seeds.csv` l. 165–170 and l. 321–326. The
  sensitivity points of
  [`experiments/2026-09-17-lc-h4-sensitivity`](../../experiments/2026-09-17-lc-h4-sensitivity)
  were computed over a `cells.csv` byte-identical to the new recording's and
  are not recorded again.

- **2026-09-25 — the draw component at 2013H1.** No run. The note of
  2026-09-15 says that on 2013H1-R the three context draws are the whole pool
  and on 2013H1-E they share all but a few hundred of their 50,000 rows, so
  the per-build row at 2013H1 carries no draw component. The recorded fits
  hold that for the foundation models: the run records no disagreement
  between the draws on either model's own E − R at 2013H1, which lies
  between +0.0293 and +0.0378 on every draw (`paired.csv` l. 364, 367, 661,
  664, 958, 961 of
  [`experiments/2026-09-24-lc-between-arm-intervals`](../../experiments/2026-09-24-lc-between-arm-intervals)).
  They do not hold it for the control. On 2013H1-E its three fits stop at
  97, 93 and 137 rounds, with a mean deviation over the build's 19 cells of
  0.0860, 0.0837 and 0.1820 (`control-fits.csv` l. 2–4 of
  [`experiments/2026-09-17-lc-h4-sensitivity`](../../experiments/2026-09-17-lc-h4-sensitivity)).
  Its own E − R at 2013H1 reads +0.0064 [−0.0085, +0.0221], +0.0041
  [−0.0112, +0.0203] and +0.1024 [+0.0707, +0.1068] with each draw held
  fixed (`paired.csv` l. 361, 658, 955). The H4 rows there are starred above
  zero on the first two draws and below it on the third: TabPFN − GBM-50k
  +0.0276 [+0.0092, +0.0403], +0.0253 [+0.0068, +0.0393] and −0.0699
  [−0.0748, −0.0387], TabICL − GBM-50k +0.0288 [+0.0100, +0.0436], +0.0337
  [+0.0167, +0.0493] and −0.0683 [−0.0736, −0.0353] (l. 376–377, 673–674,
  970–971). The run lists both rows under `bootstrap.draws_disagree`. The
  per-build row at 2013H1 therefore carries a draw component through the
  control, and from here it is read as a mixture of draws, as every other
  date's row is. No hypothesis, criterion or reading changes: the per-build
  rows enter no criterion.

- **2026-09-25 — the ridge, fixed before it is drawn.** The Plot section
  registers "the score distribution of one model at every cohort of one
  build, as a ridge, against the training distribution the PSI bins were
  fixed on". No recorded run draws it. This entry fixes what the
  registration leaves open. It is written after every criterion row of this
  book was recorded and before the figure exists. The figure reads recorded
  scores. It refits nothing, pools nothing and enters no criterion.

  *The model.* All five, one column each on the same cohort rows: the
  scorecard, the GBM, GBM-50k, TabPFN and TabICL. The registration names
  one model and gives no rule for choosing it, and a model chosen now would
  be chosen with every stability row known. The figure is shown whole
  wherever it is shown. GBM-50k is the recorded control, the criterion's;
  the control refitted on 2026-09-17 is not drawn.

  *The build.* 2015H1-E, the falsifying build. Its grid recording,
  [`experiments/2026-09-23-lc-2015h1e-intervals-grid`](../../experiments/2026-09-23-lc-2015h1e-intervals-grid),
  is the only grid recording of this book that the claim gate accepts at
  HEAD; every other one pins a version of `build_intervals.py` that has
  changed since. The build scores eleven quarterly cohorts, 2015Q3 to
  2018Q1, at ages 1 to 11, each of 20,000 rows with 541 to 686 defaults, so
  none is under the floors.

  *The reference.* The one H3 reads since the note of 2026-09-12: the
  build's 323,026 training rows for the scorecard and the GBM, and the
  50,000-row context draw for GBM-50k and the foundation models. Both are
  recorded, as `reference.parquet` in each score directory. No other
  reference exists as rows.

  *The draw and the temperature.* The first context draw, 20260911, each
  column against that draw's own reference. The draws are not pooled, since
  the statistic never mixes their references. The foundation models are
  drawn at 0.9 and again at 1.0 in two more columns, seven columns in all.
  A scale on the logit leaves the deciles where they are, but it moves a
  row along a probability axis, and that position is the level H2 reads;
  the amendment of 2026-09-06 puts the same statistics at 1.0 beside every
  table and figure that carries them. TabPFN at 1.0 is scored and TabICL at
  1.0 is derived.

  *What a row shows.* A histogram density of log10 of the predicted
  probability, in bins 0.05 wide with edges at multiples of 0.05, so no
  bandwidth is chosen. The figure has one x range. It runs from the 0.1st
  to the 99.9th percentile of every row the figure draws, cohorts and
  references pooled, widened to the nearest bin edge, and a probability
  beyond it is counted in the end bin, which the figure says. A probability
  of zero has no place on the axis and stops the script; no row is dropped.
  Every row sits on one vertical scale. The reference is an outline behind
  every row, and its nine interior deciles, the statistic's bin edges, are
  ticks on every row. Rows run by age, youngest at the top, and are
  labelled by cohort. The x ticks are labelled in probability.

  *What is printed.* No statistic. Each cell's PSI and its critical value
  are in `metrics.csv` of the grid recording, and the caption points there.

  *What is read.* The five score directories the grid recording names as
  its sources:
  [`2026-09-05-lc-2015h1e-scores`](../../experiments/2026-09-05-lc-2015h1e-scores)
  (the scorecard, the GBM and GBM-50k),
  [`2026-09-08-lc-2015h1e-tabicl-colab-t4`](../../experiments/2026-09-08-lc-2015h1e-tabicl-colab-t4),
  [`2026-09-08-lc-2015h1e-tabicl-t1-derived`](../../experiments/2026-09-08-lc-2015h1e-tabicl-t1-derived),
  [`2026-09-11-lc-2015h1e-tabpfn-m4pro`](../../experiments/2026-09-11-lc-2015h1e-tabpfn-m4pro)
  and
  [`2026-09-11-lc-2015h1e-tabpfn-t1-m4pro`](../../experiments/2026-09-11-lc-2015h1e-tabpfn-t1-m4pro).
  `scripts/registered_figures.py` draws the figure in a recording of its
  own under `record_run.py`, from a clean tree, with the script final
  before the recording starts. The hash of every input is written beside
  the figure.

  *The level figures of this book.* The nine in-sample recordings of
  2026-09-23, which C-023 cites, each carry the level figure whose ticks
  and axes the audit of EXP-005's falsifying reading found defective. They
  are redrawn as the entry of this date in the [EXP-005
  log](EXP-005-log.md) fixes. The recorded figures stay in their run
  directories.

- **2026-09-25 — the twenty-four-month check of ADR-0005, read.** The two
  poolings the entries of 2026-09-24 fix, recorded at `b6e4ddc` by
  `scripts/arm_weights.py` from a clean tree, exit 0 on both:
  [`experiments/2026-09-25-lc-arm-e-intervals-label24`](../../experiments/2026-09-25-lc-arm-e-intervals-label24)
  reads the expanding arm's recorded scores against the twenty-four-month
  label, and
  [`experiments/2026-09-25-lc-arm-e-intervals-label24-at12`](../../experiments/2026-09-25-lc-arm-e-intervals-label24-at12)
  reads the same 64 cells against the twelve-month label, from the same
  copies of the score files, the command differing in `--outcome` and the
  output directory alone. The copies, with the label written beside
  `outcome`, are those of the nine relabel runs
  `experiments/2026-09-24-lc-<build>-label24`, committed at `b6e4ddc`.
  Nothing is refitted. Both poolings run the criterion's bootstrap, 200
  resamples at seed 20260905 with the check seeds 20260906 and 20260907, the
  cohorts resampled and each context draw held fixed beside it. Line numbers
  below are those of `paired.csv`, the same in both runs.

  *Before the reading.* A trial of the relabel code on 2016H2-E, before the
  second entry of 2026-09-24, counted that build's 2017Q1 defaults under both
  labels, 629 at twelve months and 2,030 at twenty-four, the counts the
  recorded relabel run of that build holds in `label24.json`, and computed no
  statistic of any model. The pair was first recorded at `57f6bce` and not kept. Its
  `paired.csv` and `paired-seeds.csv` are byte-identical to those of the
  recording read here.

  *The cells.* 64 over 15 cohorts on eight builds, as the entry fixed:
  2013H1-E keeps 15, each later build two fewer, 2016H2-E one (its first
  scored cohort is 2017Q1, the last whose twenty-four-month window has
  closed) and 2017H1-E none (its first is 2017Q3). 2013H1-E carries 0.2344
  of the cell-weighted mean (`weights.json`). Every row that weights the
  builds alike is unreadable, since 2016H2-E has no slope of its own and no
  second stability reference. The runs leave the build-intercept slope and
  the first-cohort index empty at that scope and print finite values on the
  others, among them the "builds alike" column of the signed Cox slope in
  `stdout.txt`; none of those is read.

  *H1, both identifications, each foundation model against GBM-50k.* On the
  criterion's identification, one intercept per build, all four rows hold
  zero under every seed on both labels (l. 188–191): TabPFN − GBM-50k
  +0.00016 [−0.00020, +0.00047] against +0.00001 [−0.00056, +0.00050],
  TabICL − GBM-50k +0.00017 [−0.00019, +0.00053] against +0.00024 [−0.00034,
  +0.00081]; the untempered rows repeat these. With the third draw held
  fixed TabPFN's lies above zero against the longer outcome, +0.00030
  [+0.00004, +0.00056], where the twelve-month one holds zero, +0.00006
  [−0.00044, +0.00055] (l. 4836 of each run), so on that draw the two labels
  disagree on a criterion's pair, while the pooled reading the rule names
  reads alike.

  On one intercept per cohort TabICL − GBM-50k lies below zero on both
  labels, −0.00126 [−0.00177, −0.00082] against −0.00156 [−0.00214,
  −0.00105] (l. 217); against the longer outcome the run marks its draws as
  disagreeing, each of the three below zero. TabPFN − GBM-50k disagrees:
  −0.00006 [−0.00031, +0.00020] against the longer outcome, holding zero, and
  −0.00042 [−0.00080, −0.00002] against the twelve-month one, below zero,
  under all three seeds (l. 216; untempered l. 219, the same intervals). With
  the cohorts resampled the twelve-month interval holds zero too, [−0.00106,
  +0.00014] (l. 4192 of the second run). With each draw held fixed (l. 4416,
  4640, 4864) the labels agree on the first draw, both below zero, −0.00018
  [−0.00038, −0.00002] against −0.00040 [−0.00077, −0.00002]; disagree on the
  second, −0.00005 [−0.00027, +0.00009] against −0.00053 [−0.00087,
  −0.00016]; and agree on the third, both holding zero, +0.00006 [−0.00016,
  +0.00025] against −0.00032 [−0.00069, +0.00004].

  *H2, the Cox slope against the longer outcome, under that name.* Against
  the full-pool scorecard, the criterion's comparator (l. 67–70), both
  foundation models at the shipped temperature lie above zero under every
  seed on both labels: TabICL − scorecard +0.1131 [+0.0936, +0.1225] against
  +0.0534 [+0.0229, +0.0704], TabPFN − scorecard +0.0848 [+0.0665, +0.0942]
  against +0.0326 [+0.0054, +0.0506]. Untempered, TabPFN − scorecard holds
  zero on both, +0.0050 [−0.0074, +0.0157] against −0.0012 [−0.0175,
  +0.0124], and TabICL − scorecard disagrees: +0.0305 [+0.0139, +0.0406],
  above zero under every seed and with the cohorts resampled, against
  +0.0016 [−0.0137, +0.0141], holding zero under every seed.

  The control on identical rows, reported beside the comparison, disagrees
  on all four pairs under every seed (l. 76–79): at the shipped temperature
  TabPFN − GBM-50k +0.0782 [+0.0179, +0.1140] and TabICL − GBM-50k +0.1064
  [+0.0487, +0.1406] above zero, against −0.0243 [−0.1132, +0.0301] and
  −0.0035 [−0.0926, +0.0495] holding zero; untempered −0.0017 [−0.0584,
  +0.0332] and +0.0238 [−0.0325, +0.0576] holding zero, against −0.0581
  [−0.1272, −0.0071] and −0.0553 [−0.1288, −0.0042] below zero. Both runs
  mark the draws of all four pairs as disagreeing. At the shipped
  temperature the twelve-month reading holds zero on the first and third
  draws and lies below zero on the second, −0.0832 [−0.1201, −0.0547] for
  TabPFN and −0.0558 [−0.0990, −0.0280] for TabICL (l. 4500–4501 of the
  second run). The longer outcome lies above zero on that draw, so there the
  two labels carry stars of opposite sign. Against the longer outcome every
  draw lies above zero, on intervals that do not all overlap (l. 4276–4277,
  4500–4501, 4724–4725). Untempered every draw lies below zero against the
  twelve-month label. Against the longer outcome it lies below zero on the
  second draw, −0.0501 [−0.0615, −0.0389] for TabPFN and −0.0206 [−0.0346,
  −0.0088] for TabICL (l. 4502–4503), and above it on the other two. On both
  labels the pooled interval of these pairs is the spread of the draws.

  The direction is the one the entry of 2026-09-24 named before any score was
  read against the longer label: a twelve-month probability read against a
  twenty-four-month outcome lowers every model's signed Cox slope (l. 86–92),
  here by about a tenth of its value, so the scaling is common only roughly.
  The scorecard reads 0.8828 against 0.9606, the full-pool GBM 0.9314
  against 1.0357, GBM-50k 0.9732 against 1.0791, TabPFN 0.7911 against 0.8861
  and TabICL 0.7629 against 0.8569 at the shipped temperature, and 0.8790
  against 0.9846 and 0.8476 against 0.9522 untempered. GBM-50k, above one on
  the twelve-month label, comes nearer to one. The full-pool GBM, above one
  as well, ends below one and further from it. Every model below one moves
  further from it, and each foundation model's difference against the
  control rises. The entry reads the direction and does not decompose the
  change. The rows say how the same scores meet a longer outcome; they are
  not a reading of calibration at twenty-four months.

  *H3.* The stability index does not read the label, and all 672 rows of
  each of its two statistics are the same in the two runs in value and in
  both bounds. Its four criterion pairs therefore cannot disagree, and the
  rows are the same statistic on fewer cells: TabICL − GBM-50k +0.0418
  [+0.0374, +0.0470] against the model's own reference and −0.0013 [−0.0026,
  −0.0001] against the build's first scored cohort, both beyond the interval;
  TabPFN − GBM-50k +0.0015 [−0.0010, +0.0035] and −0.0015 [−0.0028, +0.0000],
  both holding zero (l. 132–133, 160–161). The runs mark the draws of all
  four as disagreeing. On TabPFN − GBM-50k against its own reference the
  draws disagree in sign, −0.0007 [−0.0011, −0.0003], +0.0018 [+0.0014,
  +0.0023] and +0.0032 [+0.0029, +0.0036] (l. 4332, 4556, 4780), so its
  pooled interval is the spread of the draws.

  *The count.* The rule names a criterion's pair. Applied beyond those, to
  the 21 pairs each run records for each of the five statistics H1 to H3
  read, 16 disagree and none with stars of opposite sign: 1 on the build
  intercept, 3 on the cohort intercept, 12 on the Cox-slope deviation, 0 on
  either stability index. Of the ten pairs the criteria read at the shipped
  temperature one disagrees (TabPFN − GBM-50k on the cohort intercept); of
  the ten untempered, two; of the four control-beside pairs of H2, four. The
  other nine are classical pairs or foundation models against each other:
  GBM − scorecard on the build intercept (l. 177) and on the cohort intercept
  (l. 205), and on the Cox-slope deviation four classical pairs (GBM −
  scorecard, GBM-50k − scorecard, GBM-50k − GBM, TabPFN − GBM) and three
  untempered ones (TabICL − GBM, TabPFN − GBM, TabPFN − TabICL) (l. 65–66,
  71–72, 74–75, 85). On the signed Cox slope, beside H2 and not tested, one
  pair disagrees: TabICL − scorecard untempered, −0.0352 [−0.0463, −0.0205]
  against −0.0085 [−0.0319, +0.0156] (l. 97). All sixteen disagree under
  both check seeds as well, except TabPFN − GBM on the Cox-slope deviation,
  starred on both labels under 20260906. Three more pairs on the build
  intercept agree under the primary seed and disagree under a check seed;
  they are not counted. They are GBM-50k − scorecard, under both check
  seeds, and TabPFN − scorecard at both temperatures, under 20260907. Of the
  504 arm differences the seed check covers, 335 are starred under the
  primary seed against the longer outcome and 287 against the twelve-month
  one.

  *The 64 cells against the 99.* The twelve-month rows here are on the 64
  cells, not on the 99 the criteria read in
  [`experiments/2026-09-22-lc-arm-e-intervals`](../../experiments/2026-09-22-lc-arm-e-intervals).
  The smaller set alone moves five of the ten criterion pairs at the shipped
  temperature at twelve months:
  - On the build intercept, TabPFN − GBM-50k and TabICL − GBM-50k lie above
    zero on the 99 cells (C-021) and hold zero on the 64.
  - On the cohort intercept, TabPFN − GBM-50k holds zero on the 99 and lies
    below zero on the 64. The disagreement above is with that reading, and
    the longer outcome reads the pair as the 99 cells do.
  - On H2, TabPFN − scorecard holds zero at the margin on the 99 (C-007). On
    the 64 it lies above zero under every seed with the cohorts fixed. With
    them resampled it loses the star under 20260906 ([−0.0012, +0.0535],
    `paired-seeds.csv` l. 6178 of the second run).
  - Against the first scored cohort, TabPFN − GBM-50k lies below zero on the
    99 (C-008) and holds zero on the 64.

  Untempered four move: the same pairs less H2's, where both models hold
  zero on both cell sets.

  *What it means for the verdicts.* None changes standing; the criteria are
  twelve-month by registration. H1 on its criterion identification reads
  alike under both labels. TabICL's excess over the scorecard at the shipped
  temperature, on which H2's kill fires in C-007, stands against the longer
  outcome. H3 is not touched by the label. The readings C-007 reports beside
  H2 do not carry to the longer outcome: the foundation models against the
  control on identical rows, and TabICL against the scorecard untempered.
  They move in the direction a roughly common shift of every model's slope
  produces, so they are not read at any horizon but twelve months.

  What is not here. A model fitted to the twenty-four-month outcome; the
  rolling arm and H4; Gini, observed over expected and the other level
  statistics, held in the runs and not read here; any row that weights the
  builds alike.

- **2026-09-25 — the prior-art check's "one temporal split", qualified.** No
  run. The Prior art check of the pre-registration cites arXiv:2605.18635
  "for the one temporal split in the area". It stands as written, and this
  entry is read beside it. The sentence holds for the credit papers on
  foundation models read on 2026-08-27, the date of the check, and for no
  later date. BeyondArena, arXiv:2606.30410, verified on 2026-09-04, scores
  TabICLv2, TabPFN-2.6 and TabDPT on two credit datasets under a
  rolling-origin temporal split, by ROC AUC alone. The FinTFM software
  deposit, Zenodo 10.5281/zenodo.22950210, read as a repository on
  2026-09-25, splits V4FinBench company-years into training rows through
  2016 and test rows from 2017, and scores its own foundation model and a
  per-horizon logistic regression by ROC AUC and a ten-bin expected
  calibration error at horizons 0 to 3, and its own model alone also by the
  mean predicted default rate beside the observed one. Both rows are in
  [prior-art.md](../landscape/prior-art.md). The sentence is read as "the one
  temporal split among the credit papers on foundation models read on that
  date". Neither row scores TabPFN or TabICL with a calibration measure on a
  time-ordered credit split, and neither reports a vintage trajectory. No
  hypothesis, criterion or reading changes.

- **2026-09-25 — the cold audit of H4's pooling, written up.** The ninth
  audit above is the last written up in this section, and the note of
  2026-09-17 says H4's pooling was read and audited. That audit was made
  on 2026-09-16, the tenth, and is written up here on 2026-09-25 from its
  report as received, after every criterion row of this book was
  recorded; it is not an entry made at the time.

  *What it read.* The recording
  [`experiments/2026-09-16-lc-between-arm-intervals`](../../experiments/2026-09-16-lc-between-arm-intervals)
  at `1c786fe`: its manifest, the script and its imports at that commit,
  every output file and both figures, the score runs' `build.json` files
  and manifests, and H4's criterion with the notes of 2026-09-04 and
  2026-09-15. The expected result was left out of the request, but the
  auditor reports that the subject of the commit recording the pooling,
  which states the verdict and both rows, was in its environment before it
  began, and it treats the audit as partly contaminated. Everything it
  relies on it re-derived from the code and the row-level files.

  *What reproduced.* Every arm and build-weighted point in `paired.csv`
  from `cells.csv`, for all seven models. From the score files with its
  own fits and resampler: 30 cell deviations to 1.2 × 10⁻⁸, and H4 at
  −0.0412 [−0.089, +0.018] for TabPFN and −0.0447 [−0.092, +0.017] for
  TabICL against the run's [−0.0885, +0.0181] and [−0.0916, +0.0167]. The
  script computes what the note of 2026-09-15 specifies: the cell-weighted
  mean over the 99 shared cells, E − R per model and that minus the
  control's on the same resample, survival only with the lower bound above
  zero under all three seeds, one row index per cohort shared across both
  arms and every model, the Cox-failure rule leaving no cell out, and the
  cells matched between arms on cohort, age, row and outcome, which its own
  load confirmed on all eighteen builds. The contrast is printed beside the
  reading and enters no statistic. The two arms' classical score runs ran
  different versions of `gbm.py`, and the difference adds options whose
  defaults change nothing, each run's checks reading a gap of zero against
  its recorded cohorts.

  *Findings, the most serious first, and what was done about each.*

  1. The size and sign of H4's pooled rows come from one control fit. On
     2013H2-E, draw 20260912, GBM-50k stopped at 19 rounds at a learning
     rate of 0.1, and its mean |slope − 1| over the build's 17 cells is
     0.6400 against 0.2089 and 0.0587 for the other two draws
     (`control-fits.csv` of
     [`experiments/2026-09-17-lc-h4-sensitivity`](../../experiments/2026-09-17-lc-h4-sensitivity)).
     Replacing that one fit by the mean of its other two draws, the
     auditor's resampler gives the control's reduction +0.011 [−0.019,
     +0.051] and H4 −0.012 [−0.057, +0.019] for TabPFN and −0.016 [−0.063,
     +0.017] for TabICL: the kill still fires, and the reading that the
     window helps the control more mostly goes. The point the control
     inherits differs between the arms at eight of nine dates by the
     auditor's count, so its reduction mixes the window with a re-tuning,
     and the figure of the arm cells averages each cell over its draws, so
     the fit does not show. Done: the sensitivity points and the control's
     fit table are recorded in the run named above (`c965ea5`), points
     only, and read in the entry "2026-09-17 — H4 recorded again with the
     verdict string corrected, and the sensitivity points", which finds the
     inherited point differing at every one of the nine dates; the note of
     2026-09-17 (`05305ee`) says the control's reduction is not a
     measurement of the window alone and reads a sensitivity row only for
     whether it leaves the criterion's interval; C-034 names the fit. A
     control fitted at one point on both arms stays a reviewer's run. The
     figure is unchanged.
  2. The interval is a quantile over a mixture of three context draws that
     disagree, and the resampling unit understates fit variance: each
     (build, draw) fit is shared by up to 19 cells counted as independent.
     Per draw H4 reads −0.051, −0.084 and +0.012 for TabPFN and −0.058,
     −0.086 and +0.010 for TabICL; the kill holds on every draw, and the
     width is not a noise floor. Kill criterion 3 had not been read. Done:
     the note of 2026-09-17 fixes how a kill is read under the mixture and
     under each draw held fixed, and kill criterion 3's reading, computed
     in
     [`experiments/2026-09-17-lc-kill-criterion-3`](../../experiments/2026-09-17-lc-kill-criterion-3)
     (`c2065f2`), does not fire; the entries "2026-09-19 — H4's draw
     component" and "2026-09-25 — the draw component at 2013H1" read the
     draws; C-034 reads the pooled interval as the spread of three draws.
     The resampling unit is the registered method and is unchanged.
  3. The manifest did not hash the row-level inputs or the imported
     scripts. Done: the pooling writes `inputs.json` from `9f04171`, and
     the superseding recording,
     [`experiments/2026-09-17-lc-between-arm-intervals`](../../experiments/2026-09-17-lc-between-arm-intervals)
     (`357f00c`), pins the 2,449 files it read; `record_run.py` pins the
     import closure from `d0dc349`.
  4. A row below zero read as beyond the interval whatever the check seeds
     said. TabPFN at 1.0 was summarised as killed beyond the interval
     although its star is lost under 20260906; the criterion rows were not
     affected. Done at `9f04171`; the superseding recording reads that row
     as holding zero at the margin, and so does C-034.
  5. The folded statistic's bootstrap is biased upward, so the point sits
     off-centre in its interval; for H4 the bias largely cancels, the
     auditor's resampled mean −0.039 against a point of −0.041, and no
     verdict changes. Done: the entry "2026-09-19 — the interval's other
     bound" reflects the recorded bounds about the point, the method
     staying; on this book the one star that changes is TabPFN's at 1.0,
     already read at the margin.

  *Not examined.* The prior-art table, the split and feature
  construction, the derivation of TabICL's rows at 1.0, and the contrast
  script.

  *Verdict: supports a weaker claim.* On this book and grid there is no
  evidence that the four-quarter rolling window reduces Cox-slope drift
  for TabPFN or TabICL more than for GBM-50k; the kill fires, and survives
  the removal of the anomalous control fit and every bootstrap seed. The
  values −0.041 and −0.045, and any reading that the control benefits
  more, are not to be quoted without naming the 2013H2-E fit of draw
  20260912, which moves them to about −0.012 and −0.016. Not shown: that
  the rolling window worsens the foundation models' calibration drift
  relative to the control, since the negative sign rests on one under-fit
  control; that their calibration is insensitive to the window, since
  their per-draw reductions change sign and the per-build rows run from
  +0.06 at 2014H1 to −0.15 at 2017H1, starred; and anything about a window
  of another width or a control tuned on its own 50,000 rows.

- **2026-09-26 — AUC against age drawn again at the size the paper prints
  it, fixed before it is drawn.** The paper prints the figure of AUC against
  model age that
  [`2026-09-22-lc-arm-e-intervals`](../../experiments/2026-09-22-lc-arm-e-intervals)
  wrote as `auc-age.png`. That figure is 25.2 inches wide, seven panels in
  one row; printed at the text width of the tmlr style, 6.5 inches, its
  titles come out near two points. This entry fixes a redraw at print
  size, under this rule: at most 6.5 by 8.5 inches, text of at least 7
  points and tick labels of at least 6.5 at that size, 300 dots per inch,
  and the panels in more lines where one line does not fit.
  The numbers are the constants `PRINT_WIDTH`, `PRINT_HEIGHT`, `TEXT_PT`,
  `TICK_PT` and `DPI` of `scripts/registered_figures.py`, which draws the
  registered figures; the redraw imports them. The size, the type and the arrangement of the
  panels change, and nothing the figure shows. It is written after every
  criterion row of this book was recorded, and the figure enters no
  criterion.

  *What stays.* One panel per model, the seven of the pooling in its order:
  the scorecard, the GBM, GBM-50k, TabICL, TabICL at 1.0, TabPFN and TabPFN
  at 1.0. One line per build, the nine builds 2013H1-E to 2017H1-E in the
  recorded colours, with a marker at every cell: 99 cells, 693 points over
  the seven panels. Each cell's AUC is read on the first context draw,
  20260911. The arm slope with one intercept per build is a dashed line
  through the panel's mean, and its value and interval stand in the panel's
  title as the pooling's `paired.csv` records them, with the draws pooled.
  Every panel shares one AUC axis. The titles, axis labels, legend entries
  and figure title are the recorded ones word for word.

  *What changes.* Three panels to a line, in three lines; the legend, its
  ten entries in two columns, in the two slots the last line leaves free;
  the AUC axis labelled on the first panel of each line; the titles wrapped
  to the panel's width, an interval kept on one line; markers and lines
  thinned to the print size. The layout is the one
  `scripts/registered_figures.py` gives the same figure on Freddie Mac,
  except where the legend sits: there eight panels leave one slot free and
  the legend runs under the panels in three columns.

  *What is read.* The pooling writes no cell's AUC; its figure computed each
  one from the score files. The redraw computes them the same way, with the
  metric module's AUC on the same rows, from the 45 score directories the
  pooling's `intervals.json` lists under `sources`. It stops unless each
  `scores.parquet` and `reference.parquet` it reads hashes to the value the
  pooling's `inputs.json` records, and unless the cells drawn reproduce,
  for every model, the pooling's own rows with the first draw held fixed:
  the mean Gini over the arm and the slope with one intercept per build, to
  within 1e-9. The pooling passes the claim gate at HEAD, and a pooling the
  gate refuses is refused.

  *How.* `scripts/print_figures.py lc-auc-age` draws it in a recording of
  its own under `record_run.py`, from a clean tree, with the script final
  before the first recording starts. `summary.json` gives the counts drawn
  and checked, and `inputs.json` the hash of every file read. The recorded
  figure stays in its run directory; the paper takes the redraw in its
  place.
