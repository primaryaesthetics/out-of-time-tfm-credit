---
id: 001
title: The vintage structure of the Lending Club book, and its date columns
dataset: lending-club (wordsforthewise, accepted_2007_to_2018Q4)
status: open
opened: 2026-08-27
closed:
---

# EXP-001 — vintage structure and date-column audit

Every later claim in this repository is conditional on the origination axis
being what it is assumed to be. This measures the axis before anything is
modelled, and it audits the columns that could be mistaken for it.

## Question

Does this book support a quarterly vintage trajectory, and does any date column
other than the origination date reach past the last origination — such that a
split built on it would sort loans by outcome while appearing to sort them by
time?

## What the measurement discriminates

> If the origination axis ends in 2018Q4 and no other candidate splitting
> column carries origination-like dates into 2019, then the split reported in
> arXiv:2605.18635 — train to June 2019, test on the half-year after — cannot
> have been built on the origination date of this dataset. It was built on a
> performance-window column, or on a different source than the one cited.
>
> If the axis does reach into 2019, the file naming is misleading, that paper
> is reproducible as described, and the framing that tests across the 2020
> regime shift may still be available.
>
> If the resolved share falls steeply across the later cohorts, the usable
> evaluation window is materially shorter than the data span, and every cohort
> near the end contributes a censored label rather than a matured one.

The first branch is the one with consequences beyond this repository. The
literature's only temporal validation describes itself as built "to prevent
leakage", and a split on a performance-window column is the leakage it names.

## Setting

- **Dataset.** `accepted_2007_to_2018Q4.csv.gz` from `wordsforthewise/lending-club`
  on Kaggle, the dataset cited as reference [19] by arXiv:2605.18635. Roughly
  2.26M rows, 145 to 151 columns depending on release.
- **Origination column.** `issue_d`, parsed as `%b-%Y`.
- **Split.** None. No model is fitted and no split is built. This experiment
  exists to decide whether a split is constructible.
- **Models and tuning budget.** None.
- **Metrics.** Descriptive: cohort sizes by quarter, per-column date ranges and
  null fractions, `loan_status` distribution, resolved share by cohort.
- **Seeds.** None. The measurement is deterministic given the file, and the
  file's hash goes in the manifest.

## Kill criteria

Written before the run, and they kill a design rather than a hypothesis.

1. **Fewer than eight quarterly cohorts carrying at least five thousand
   resolved loans each.** Below that the per-vintage metric has a confidence
   band wider than any effect worth reporting, and the quarterly trajectory
   dies. The fallback is semi-annual, and if that fails too, the dataset is
   wrong for this study and Freddie Mac moves from extension to starting point.
2. **Resolved share below one half across the majority of cohorts.** Then the
   label is censored across most of the book, and no modelling proceeds until
   a maturity-aware label definition and an embargo are written into the
   loader. This does not kill the study; it blocks it until a prerequisite
   exists.
3. **The origination column is absent, or parses at under 95%.** Then the
   origination axis is not what it is assumed to be, and everything downstream
   is rebuilt on whatever the axis turns out to be.

The criterion that kills the comparison rather than the design: if the
origination axis does end in 2018Q4, the framing that runs Lending Club across
2020 is dead, and it is dropped rather than stretched. That framing is not owed
to this project.

## Cheapest falsifying run

The whole experiment is the cheapest version. One pass over four columns of one
file on CPU, minutes, no accelerator and no model. `scripts/vintage_structure.py`,
wrapped in `scripts/record_run.py`.

The single output that decides the first branch is the maximum of `issue_d`
against the maxima of every other date column in the file.

## Prior art check

Stands on two rows of [../landscape/prior-art.md](../landscape/prior-art.md):

- arXiv:2605.18635, status `verified` 2026-08-27, full text. The split
  description is quoted from §4.1 and the dataset reference from [19].
- arXiv:2605.18147, status `verified` 2026-08-27, full text. Establishes that
  the other credit TFM paper has no temporal structure at all, which is why the
  one that does carries the weight.

Opened under the sweep of 2026-08-27, green on that date.

## Plot

Cohort size against resolved share, both on the origination-quarter axis. Not a
bar chart of a headline number: the shape being looked for is where the
resolved curve falls away, because that is where the label stops being a label.
Saved beside the manifest as `cohorts.png`.

## Log

Append-only. Date, what was run, what was observed, pointer to the run
directory. No conclusion without a pointer.

- **2026-08-27** — opened. Dataset download in progress; the file listing from
  the Kaggle API shows all four assets named `2007_to_2018Q4` with a creation
  date of 2019-12-17, which is the reason the first branch above is written as
  the primary question. A file name is not its contents and nothing is
  concluded from it.

- **2026-08-30** — first run, `experiments/2026-08-30-lc-vintage-structure`.
  The file is intact: 392,582,231 bytes as listed, sha256
  `55c16f75120f897683f02e7aabcf080d0e4a20c4832feb1d592cfa941bd62a2d`,
  151 columns, 2,260,701 rows.

  The manifest records a dirty working tree, so this run is not citable. It is
  repeated from a clean tree before anything here reaches the ledger.

  Origination spans 2007-06 to 2018-12 across 47 quarterly cohorts. The file
  name matches the contents.

  Kill criteria, all measured rather than assumed. Thirty-one quarters carry at
  least five thousand resolved loans, against a floor of eight, so the
  quarterly trajectory survives. Thirty-six of forty-seven cohorts are at least
  half resolved, so the second criterion does not fire either.

  What does bind is the shape rather than the threshold. Resolved share is
  above 88% through 2015Q4 and then falls monotonically: 83.6% at 2016Q1,
  48.4% at 2017Q1, 20.9% at 2018Q1, 3.9% at 2018Q4. The book has 47 cohorts and
  something closer to 20 usable ones. A trajectory run to the end of the data
  would report, in its last cohorts, on whichever loans happened to finish
  early.

  Eight date columns reach past the last origination: `last_pymnt_d` to
  2019-03, `next_pymnt_d` to 2019-05, `last_credit_pull_d` to 2019-04,
  `hardship_end_date` to 2019-06, and four others. These are performance-window
  columns and none is a candidate for splitting on.

  Bearing on arXiv:2605.18635, which cites this dataset as its reference [19]
  and reports "temporal splitting (train ≤ June 2019; test: H2 2019)". On this
  file, a training window bounded at June 2019 contains every row, and a test
  window of H2 2019 is empty on the origination axis. It is also empty on every
  other date column present: the furthest any of them reaches is 2019-06, and
  that column is 99.5% null. Their reported resolved count of ~533K is also
  2.5 times below the 1,345,350 measured here under the stated definition.

  What follows from that is not yet written down. The measurement says the
  described split is not constructible from the cited file; it does not say
  what they did instead. That inference is exactly what the cold audit is for,
  and no statement about this paper leaves this experiment before then.

  One definitional loose end, found in the status distribution and not yet
  acted on: 1,988 loans carry "Does not meet the credit policy. Status:Fully
  Paid" and 761 carry the Charged Off variant. Both are terminal and neither is
  counted by the `RESOLVED` set used in this run. The effect is 0.12% of the
  book, and the definition is settled before the repeat run rather than
  adjusted afterwards.

- **2026-08-30, second run** — `experiments/2026-08-30-lc-label-trajectory`,
  clean tree at 1a671cc. The label from ADR-0005 applied to the whole book,
  both windows side by side.

  The snapshot is read from the data rather than assumed. Performance is
  observable to 2019-03 while originations stop at 2018-12, so the book keeps
  reporting on loans for three months after it stops writing them, and the
  twelve-month label runs to the 2018Q1 cohort.

  Twelve-month window: 1,873,290 labelled, 387,378 dropped as immature, overall
  rate 2.90%, 44 cohorts. Twenty-four-month window: 1,418,626 labelled, 842,042
  dropped, overall 10.27%, 40 cohorts.

  **The book's own risk moved, and that matters more than the levels.** On
  cohorts of at least five thousand labelled loans, the twelve-month rate falls
  to 1.92% at 2013Q4 and rises to 3.44% at 2016Q2, a factor of 1.79. The
  twenty-four-month rate does the same thing between the same quarters, 7.91%
  to 11.89% at 2016Q3, a factor of 1.50.

  Both windows agree on where the trough is and roughly on where the peak is,
  which is the sensitivity check ADR-0005 asked for: the shape does not depend
  on the window. The rise matches the period in which this issuer's
  underwriting is independently understood to have loosened, though nothing
  here establishes that and it is not claimed.

  What this buys the study is a regime shift inside the data. The 2020 shift is
  unavailable and the 2008 one sits in cohorts too small to carry a metric, but
  a book whose default rate nearly doubles across twelve quarters is a real
  out-of-time test, and any model measured across it has to be judged against
  this line rather than against a flat expectation.

- **2026-09-04** — both runs repeated after a cold audit,
  `experiments/2026-09-04-lc-vintage-structure` and
  `experiments/2026-09-04-lc-label-trajectory`, clean tree at f486c8d. They
  supersede the 2026-08-30 pair. Five things moved.

  *The resolved share was wrong before 2013Q4, and wrong in a way that reads as
  censoring.* The script carried its own three-status definition of a resolved
  loan while the label module carried a five-status one; the two credit-policy
  variants, 2,749 loans, fell in the gap. Under the label module's set, every
  cohort from 2007Q2 to 2013Q3 — twenty-six of them — is fully resolved. The
  ramp on the left of the earlier `cohorts.png`, rising from 4% at 2007Q2 to 1.0
  at 2011Q1, was that definition and nothing else. The fall on the right is real
  and unchanged, and it now has an explanation: the two kinks sit at 2014Q1/Q2
  and 2016Q1/Q2, which is the sixty-month and the thirty-six-month term crossing
  the 2019-03 snapshot. The curve is the survival function of loan term against
  the snapshot, not a credit signal.

  *One date column had been missed.* Detection read the first twenty thousand
  rows, and this file is a concatenation of quarterly releases, so those rows
  are all `Dec-2015`. `sec_app_earliest_cr_line` is entirely null in that month
  and was invisible. Eleven date columns parse, not ten. The missed column runs
  1934-03 to 2018-06 and does not reach past the last origination, so the
  conclusion survives — but it survived by luck rather than by coverage.

  *Thirty-three rows are not loans.* Each quarterly release ends in a footer
  line, and they carried into the row count. The book is 2,260,668 loans, which
  is what the label run had reported all along; the two runs no longer disagree
  on the size of the file they both read.

  *The reported extremes were properties of cohort size.* The minimum and
  maximum were taken over all cohorts, and the smallest hold 24 and 389 loans,
  so the extremes landed there every time. With a floor of five thousand loans
  and a hundred defaults, and with Wilson intervals: the twelve-month rate runs
  1.92% [1.80, 2.05] at 2013Q4 to 3.44% [3.33, 3.56] at 2016Q2, and the
  twenty-four-month rate 7.91% [7.66, 8.17] at 2013Q4 to 11.89% [11.69, 12.09]
  at 2016Q3. The intervals do not overlap in either window. Those are the same
  numbers reported on 2026-08-30, now with the population they were taken over
  stated by the run rather than applied by hand afterwards.

  *A second maturity condition was found and is now measured.* The label's
  charge-off lag has to cover the issuer's own recognition delay: a loan that
  stopped paying inside the window but has not been charged off at the snapshot
  reads as a non-default, and that censoring falls only on the newest cohorts —
  the same manufactured shape the immaturity gate exists to prevent. `LabelSet`
  now counts them. At the chosen lag of five months the count is **zero** across
  all forty-four twelve-month cohorts and **one** across the forty
  twenty-four-month cohorts. The lag covers the delay; that was an assumption
  before and is now a number in the manifest.

  *What the file cannot support.* No column in this file carries a single value
  between 2019-07-01 and 2019-12-31. The latest date anywhere is 2019-06-01, in
  `hardship_end_date`, which is 99.5% null. A test window of H2 2019 is
  therefore empty on the origination axis, on every performance column and on
  every credit-history column — not sparse, empty. That is a fact about this
  file and it is as far as the measurement reaches: it says the split described
  in arXiv:2605.18635 §4.1 cannot be built from the dataset that paper cites as
  its reference [19], and it does not say what was built instead. Three
  possibilities remain open and this experiment distinguishes none of them: a
  different release of the same lender's book, a cut applied to a column that is
  not an origination date, or a split defined on something other than loan
  dates. Nothing further about that paper is written down here.

- **2026-09-19** — all three readings recorded again at `d87152c`:
  `experiments/2026-09-19-lc-vintage-structure`,
  `experiments/2026-09-19-lc-label-trajectory` and
  `experiments/2026-09-19-lc-label-sensitivity`. They are cited in place of the
  2026-09-04 trio and they carry the same numbers: every output file —
  `summary.json`, `trajectory.json`, `sensitivity.json`, all four plots and both
  streams of each run — is byte for byte what the earlier recording wrote,
  although `vintage_structure.py`, `label_trajectory.py`, `label_sensitivity.py`
  and the label module all changed in between. The changes are `noqa` markers,
  integer casts and a parenthesised format string, and none of them is on a path
  that computes a number, which is what the identity measures.

  What moves is the manifest, and it is the reason for the repeat. The earlier
  recordings pin script bytes this checkout no longer holds, and they do not pin
  `src/outoftime/__init__.py` at all, so the claim gate — which requires every
  file of this repository a cited run executes to be pinned and unchanged —
  refuses them. The 2026-09-19 trio passes it. C-003, C-004 and C-005 in
  [the ledger](../ledger/CLAIMS.md) cite these three and nothing earlier.

## Cold audit

Audited 2026-09-04 by an auditor given the two scripts, the label module, the
data file and the manifests, and asked what the runs show — not what they were
expected to show, and not the reasoning behind either.

Every number in both recorded outputs reproduced under independent
reimplementation: the cohort counts, the date-column maxima and null fractions,
the status distribution, the labelled and dropped counts under both windows, and
all eighty-four per-cohort default rates to the fifth decimal. The corrections
in the 2026-09-04 log entry are what came up around those numbers rather than in
them, and each is now carried by code rather than by care.

Four findings are not defects in the runs. They constrain what the runs can be
read to mean, and three of them are now measured in
[`experiments/2026-09-04-lc-label-sensitivity`](../../experiments/2026-09-04-lc-label-sensitivity)
rather than left as caveats. Two of the three came back larger than the audit
put them.

- **The trajectory is the book's realised rate, not its credit quality.**
  Lending Club moved away from its riskiest grades across the same period: the
  E, F and G share falls from 12.4% at 2015Q2 to 4.2% at 2018Q1. Direct
  standardising the twelve-month rate to the 2015Q2 grade mix lifts 2018Q1 from
  3.14% to 3.98% and 2016Q2 from 3.44% to 3.94%, so within grade the
  deterioration runs to the end of the book while the realised line flattens
  after 2016. For measuring a model's calibration drift the realised rate is the
  right yardstick and nothing needs to change; for any sentence about the
  lender's risk appetite it is the wrong one, and the two must not be written
  as though they were the same series.
- **The charge-off lag is not a nuisance parameter.** Across lags from zero to
  eleven months the mean cohort rate spans 0.24% to 5.68%, a factor of
  twenty-four rather than the four or five a narrower sweep suggests. Nor is the
  shape untouched: the rank correlation of the trajectory against the study's
  five-month lag is 0.93 at three months, 0.87 at eight and 0.65 at eleven,
  where the window has emptied to a quarter-per-cent event rate. What the sweep
  does establish is that five months is the only value in it that both admits a
  usable event rate and leaves no loan unrecognised, so the choice is now
  measured rather than inherited from the issuer's stated practice.
- **This file has no borrower identifier.** `member_id` is null in every one of
  its 2,260,668 rows and `id` is unique per row, so it is a loan key. The entity
  check that `splits.temporal_split` offers cannot be satisfied on this dataset
  by anything but a proxy, and a deliberately crude one — matching on three-digit
  zip, state, earliest credit line, employer text and home ownership — puts
  358,431 rows, 15.9%, in keys that span more than one quarter. That is an upper
  bound with an unknown false-positive rate. Repeat borrowing is an unmeasured
  exposure of every split built on this file, and saying otherwise would be an
  assumption rather than a measurement.
- **The label is not the regulatory PD it will be read as.** It is charge-off
  within N months of origination. On cohorts old enough to have been observed to
  the end, a twelve-month window admits 14.9% of the charge-offs those cohorts
  eventually suffer and a twenty-four-month window 57.5%. ADR-0005 carries the
  corrected figures.

The verdict was that the runs support a weaker claim than their outputs suggest,
and that the weakening is about scope rather than correctness: the axis, the
date-column classification, the maturity gate and the still-running convention
are all as described, and the per-cohort statements hold only above the size
floor the runs now apply.
