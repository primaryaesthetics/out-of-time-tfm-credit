---
id: 003
title: The vintage structure of the Freddie Mac sample, and its label
dataset: freddie-mac (Single-Family Loan-Level Dataset, sample files, Release 47)
status: open
opened: 2026-09-06
closed:
---

# EXP-003 — the second book: its axis, its label, and the resolution it can be read at

The Lending Club study rests on one book, and every audit so far has said so.
The Freddie Mac single-family sample is the second: a different product, a
different lender population, and 2008 inside the origination axis rather than
at its edge. Before anything is modelled on it, this measures whether it
supports the same trajectory, at what resolution, and whether the axis is what
the documentation says it is. The counterpart of EXP-001 and of the label
trajectory of ADR-0005, on the reduced files rather than the raw ones.

## Question

Does the Freddie Mac sample support a quarterly vintage trajectory under a
twelve-month ninety-day-delinquency label, and is the origination quarter
encoded in the loan identifier the axis the user guide says it is?

## What the measurement discriminates

> If at least eight quarterly cohorts clear the floors under the twelve-month
> window, and they are spread across the book rather than confined to the
> 2005–2009 vintages, the second book runs on the grid of EXP-002 unchanged,
> at quarterly resolution, and the out-of-time experiment on it is opened with
> that grid.
>
> If the floors are cleared only inside the crisis vintages, a quarterly
> twelve-month trajectory on this sample is a trajectory of the crisis and of
> nothing else, and the design is written at semi-annual or annual resolution,
> or on the twenty-four-month window as the primary one, rather than stretched
> to a resolution the sample cannot carry.
>
> If the first payment date lags the origination quarter by six months or more
> on more than a few percent of loans, or the median lag falls outside the
> ordinary settlement range in any cohort, the identifier's quarter and the
> file's only date disagree about when loans were written, and the axis has to
> be re-established before anything is built on it.

The arithmetic that makes the first branch uncertain, written before the run:
the sample holds 12,500 loans per quarter, so a hundred defaults needs a
twelve-month rate of 0.8%. A prime thirty-year fixed-rate book is expected to
sit below that outside the crisis years, and a twenty-four-month window is
expected to clear it across more of the book. Which cohorts clear which floor
is the measurement.

## Setting

- **Dataset.** The sample files of the Single-Family Loan-Level Dataset,
  Release 47 (July 2026): `sample_1999.zip` through `sample_2026.zip`, a
  random 50,000 loans per full origination year and proportionally fewer for
  the partial ones, each zip holding an origination file and a monthly
  performance file. Origination cutoff 2026-03-31, performance cutoff
  2026-03-31. Registered and downloaded from Clarity Data Intelligence on
  2026-09-06; the hashes of the zips are in the reduction records.
- **Layout.** Transcribed by hand from the July 2026 file layout into
  `src/outoftime/freddie_mac.py` and asserted against the files by width.
  Release 47 moved two columns from the origination file to the performance
  file and appended one, so any parser written against an earlier layout
  reads these files wrongly.
- **Origination axis.** The origination year and quarter encoded in the loan
  identifier. There is no origination date in the dataset.
- **Clock.** The first payment date, the only origination-side date a clock
  can run from. *Note of 2026-09-20:* the origination file carries a second
  date, the maturity date, which this bullet's "only" overlooked; nothing
  reads it as a clock and no count changes.
  A loan is one month old in its first payment month. Loans whose first
  payment falls six or more months after the origination quarter opens carry
  a conversion or modification date rather than an origination one, and are
  excluded from the label as re-dated; `LATE_FIRST_PAYMENT_MONTHS` in the
  loader states the threshold and the reason.
- **Label.** `src/outoftime/performance_label.py`: a default is the first
  month at or over ninety days past due, or REO acquisition, or a termination
  by third-party sale, short sale or REO disposition, at or before the window
  closes. Twelve months from the first payment month is the primary window,
  twenty-four the check, as in ADR-0005. A loan observed through the window
  with no such event is a non-default; a loan paid off inside the window is a
  non-default; a loan that left the dataset inside the window through a
  whole-loan sale, a reperforming-loan sale or a confirmed defect is censored
  and dropped; a loan whose record ends inside the window with no termination
  is immature and dropped. The counts of every bucket go in the summary.
- **Reduction.** `scripts/freddie_mac_reduce.py` streams each zip without
  writing its text to disk and keeps, per year, one row per loan with the
  origination columns and the four numbers the label reads, plus the first
  twenty-four months of every loan on the columns that decide a label. Age is
  computed from the period and the first payment date rather than read from
  the file's loan-age field, which resets on modification.
- **Split.** None. No model is fitted and no split is built.
- **Models and tuning budget.** None.
- **Metrics.** Descriptive: cohort sizes by origination quarter; the first
  payment lag per cohort; the share of each cohort carrying a mature label;
  defaults and the default rate per cohort under both windows with Wilson
  intervals; the number of cohorts clearing the floors at quarterly,
  semi-annual and annual resolution. Floors: 5,000 labelled loans and 100
  defaults, the same as the Lending Club trajectory.
- **Seeds.** None. Deterministic given the files.

## Kill criteria

Written before the run. They kill a design rather than a hypothesis.

1. **Fewer than eight quarterly cohorts clearing both floors under the
   twelve-month window.** The quarterly twelve-month trajectory dies on this
   sample. The fallback resolution is read off the same run: the semi-annual
   and annual counts under both windows. If the annual twelve-month
   trajectory fails too, the sample is too thin for the primary label and the
   choice is between the full standard files for the years concerned and
   dropping the book; that decision is not made here.
2. **Re-dated loans at five percent or more of the book, or a cohort whose
   median first payment lag is outside one to four months.** The identifier's
   quarter is not the axis the guide describes, and nothing is built on it
   until it is re-established.
3. **A layout width other than 31 and 35, or a loan with no performance
   record, or a performance record with no loan.** The reduction refuses and
   nothing runs.

   *Amended 2026-09-06, before the structure run and after the first
   reduction refused on it.* Ten loans across `sample_2025.zip` and
   `sample_2026.zip` have no performance record, all with a first payment
   between 2025-12 and 2026-04 against a last period on file of 2026-03:
   the servicing record of a loan acquired shortly before the cutoff has not
   arrived. The reducer now admits a loan with no record when its first
   payment falls inside six months before the last period on file
   (`REPORTING_LAG_MONTHS`), counts it per year, and still refuses any
   older one. Such loans are immature under any window and are never
   labelled. The refused run is `experiments/2026-09-06-fm-reduce`.
4. **Labelled share below one half across the majority of cohorts old enough
   to be mature.** The label is not usable as built, and no modelling proceeds
   until the reason is found. Cohorts inside the last window before the
   performance cutoff are expected to be immature and are not counted here.

## Cheapest falsifying run

The whole experiment is the cheapest version: the reduction over the
twenty-eight zips, then `scripts/freddie_mac_structure.py` over the reduced
files, both wrapped in `scripts/record_run.py`. CPU, minutes, no model.

The single output that decides the first branch is the count of quarterly
cohorts above the floors under the twelve-month window, and where on the axis
they sit.

## Prior art check

No row of [../landscape/prior-art.md](../landscape/prior-art.md) uses this
dataset. The experiment stands on the rows that establish what has been
measured on credit data and on which books:

- arXiv:2605.18147, `verified` 2026-08-27, full text: no temporal structure.
- arXiv:2605.18635, `verified` 2026-08-27, full text: one temporal cut on
  Lending Club.
- arXiv:2606.30410, `verified` 2026-09-04, full text: rolling-origin temporal
  splits on Lending Club and Home Credit, one metric, no trajectory.

None of the three touches a mortgage book. Opened under the sweep of
2026-09-05, green on that date.

## Plot

Two, saved beside the manifest. `cohorts.png`: cohort size against the share
carrying a mature label under each window, on the origination-quarter axis.
`trajectory.png`: the twelve- and twenty-four-month default rates per quarterly
cohort with Wilson bands, the cohorts below the floors marked. The shape being
looked for is whether the twelve-month curve stays above the floor outside
2005–2009 or only inside it, because that decides the resolution of everything
built on this book.

## Log

Append-only. Date, what was run, what was observed, pointer to the run
directory. No conclusion without a pointer.

- **2026-09-06** — the reduction, `experiments/2026-09-06-fm-reduce2`
  (444 s, sha `4fae963`, clean tree; the first attempt,
  `2026-09-06-fm-reduce`, refused on criterion 3 as amended above and is
  kept). All 28 zips at the expected widths, 31 and 35. 1,362,500 loans,
  exactly 12,500 per quarter from 1999Q1 to 2026Q1, one loan filed under
  2008 with a 2009Q1 identifier and counted there. 74,937,616 performance
  rows read, 28,979,738 kept inside the first 24 months. Last period on
  file 2026-03. Ten loans with no performance record, first payment
  2025-12 to 2026-04; one termination without a date. 227 MB of parquet,
  hashes of every zip in the per-year records.

- **2026-09-06** — the structure, `experiments/2026-09-06-fm-vintage-structure2`
  (15 s, sha `7565c59`, clean tree). Supersedes
  `2026-09-06-fm-vintage-structure`, which labelled a young cohort's early
  defaults and payoffs while dropping the rest, and showed the bias as a
  24-month rate of 5.7% on 2024Q3; the label now drops every loan whose
  window has not closed by the cutoff, and the counts below are from the
  corrected run.

  *The axis holds.* Median first payment lag is 3 months in every quarterly
  cohort, the 95th percentile 4 to 5. Re-dated loans, 6+ months after the
  quarter opens, are 0.52% of the book, at most 4.6% in any cohort
  (2000Q1); none has a first payment before its quarter. No loan that is not
  re-dated is delinquent before age one; 977 are terminated at age zero,
  paid off or repurchased before the first payment came due. Criterion 2
  does not fire.

  *The label matures.* At 12 months every cohort through 2024Q4 carries a
  label on at least 95% of its loans; 2025Q1 is partial (7,518 of 12,500,
  the loans whose first payment fell by 2025-03) and nothing later is
  labelled. At 24 months the same through 2023Q4, with 2024Q1 partial
  (7,445). Immature 54,931 and 104,929; censored 1,470 and 1,678; 140
  defaults dated at a bad termination with no ninety-day month before it.
  Criterion 4 does not fire.

  *The quarterly twelve-month trajectory is a trajectory of two crises and
  of nothing else.* Eleven quarterly cohorts clear both floors under the
  twelve-month window: 2007Q3 through 2008Q4, and 2019Q2 through 2020Q2.
  Outside those the twelve-month rate on a full cohort of 12,500 loans runs
  from 0.07% (2016Q3, 9 defaults) to 0.7%, under the hundred-default floor
  everywhere. The count passes criterion 1 as written; the spread condition
  in the discriminating sentence does not, and it is the second branch that
  holds: no quarterly design on this label.

  *What the sample can carry.* Twelve months: 21 of 26 full origination
  years clear the floors, the misses being 2003 and 2013 through 2016, at
  rates from 0.13% to 2.3%; 23 of 52 half-years. Twenty-four months: 25 of
  25 full years and the partial 2024, 48 of 51 full half-years (2003H1,
  2013H1 and 2015H1 miss), 55 of 100 quarters with the 2009 to 2018 stretch
  mostly under. Book-wide rates 0.52% at twelve months and 1.45% at
  twenty-four. The plot is `trajectory.png`.

  *One thing the plot shows that the criteria did not ask.* The 2019Q2 to
  2020Q1 cohorts sit at 1.7% to 3.8% twelve-month ninety-day delinquency,
  above 2007Q4 (1.9%), and fall back to 0.8% by 2020Q2. Those loans were
  in their first year in spring 2020, and the delinquency status is
  reported off the due date of the last paid installment, so a loan in
  pandemic forbearance reads as delinquent. Whether that is a default under
  this study's label is a decision, not a measurement, and the columns that
  would inform it (`borrower_assistance_plan`, `disaster_delinquency`) are
  not in the reduced slice. Nothing is concluded about it here.

- **2026-09-06** — the reduction again with two more performance columns
  and a second reading of the first bad month,
  `experiments/2026-09-06-fm-reduce3` (513 s, sha `17bedd2`, clean tree),
  and the structure on it, `experiments/2026-09-06-fm-vintage-structure3`
  (sha `304d00d`, clean tree). Supersedes `fm-reduce2` and
  `fm-vintage-structure2`; every count of the previous entry reproduces to
  the digit under the reported reading, and the run adds the reading with
  the months under a borrower assistance plan or a declared disaster
  hardship set aside.

  *What the relief share is.* Of the twelve-month defaults under the
  reported reading, 91% in the 2019 cohorts, 86% in 2020, 62% in 2021 and
  45% in 2017 were under a plan or a disaster flag at their first
  ninety-day month; at twenty-four months 77% of 2018, 89% of 2019, 77% of
  2020 and 50% of 2021. Before 2014 the two readings coincide, because the
  flags are populated from January 2014; the only pre-2014 quarters that
  differ are 2012Q2 to 2013Q4 at twenty-four months, whose windows reach
  into 2014. In the benign years after 2014 the share is 3% to 15%.

  *What the trajectory looks like with relief set aside.* The 2018 to 2020
  hump is gone: those cohorts read 0.4% to 0.6% at twenty-four months and
  0.17% to 0.20% at twelve, level with their neighbours. What remains of the
  shape is 2007 to 2008 at 4% to 5% and a rise from 2022 at 1.3% to 1.8%
  under both readings. Book-wide, 0.35% at twelve months (4,555 defaults)
  and 1.09% at twenty-four (13,630).

  *What the sample can carry under that reading.* Twelve months: six
  quarterly cohorts above the floors, 2007Q3 to 2008Q4; sixteen
  half-years; 19 of 26 full years. Twenty-four months: 41 quarters, 45 of
  51 full half-years (2003H1, 2013H1, 2014H2, 2015H1, 2020H2, 2021H1 miss),
  every full year. The plot is `trajectory.png`, with the set-aside reading
  dashed.

  The reading, the window and the resolution are decided in ADR-0006 on
  this run: relief months set aside, twenty-four months on half-year
  cohorts, twelve months on years as the check.

  *Note of 2026-09-20, on the shares above.* Two things in this entry are
  narrower than they read. The quantity is not the share of defaults under a
  flag at their first ninety-day month: the recorded value is one minus the
  set-aside defaults over the reported defaults, so a loan flagged at its
  first ninety-day month that reaches another, unflagged, ninety-day month
  inside the window is a default under both readings and never enters the
  share. And the four years named at twelve months are a selection under no
  stated rule: every year whose share reaches 0.40 is 2019 at 0.913, 2020 at
  0.8624, 2021 at 0.6162, 2022 at 0.4577 and 2017 at 0.4474, so 2022 belongs
  in the list ahead of 2017 and is missing from it. At twenty-four months the
  four named are the complete set at that threshold. The same description of
  the quantity is in ADR-0006 and in a comment in `freddie_mac_structure.py`;
  the comment is inside the code this book's runs pin, so it is not edited
  here.

  *Note of 2026-09-20.* "the only pre-2014 quarters that differ are 2012Q2 to
  2013Q4 at twenty-four months" is two things at once, and both are narrower
  than the sentence. At twenty-four months five quarters differ, not every
  quarter of that range: 2012Q2, 2012Q4, 2013Q2, 2013Q3 and 2013Q4. At twelve
  months two do, 2013Q2 and 2013Q4, which the sentence excludes by naming the
  window. The reason is the one it gives — a window that reaches into 2014
  meets the flags — and it applies to either window. Under both, the earliest
  cohort whose reading moves is the earliest whose window closes after
  2014-01, and EXP-005's pre-flag regime is drawn on that boundary rather
  than on the origination year.

- **2026-09-19** — the structure recorded again at `049c826`,
  `experiments/2026-09-19-fm-vintage-structure`, the command of
  `fm-vintage-structure3` with the output directory alone changed, on the
  same machine from a clean tree, 64 s. It is cited in place of
  `fm-vintage-structure3` and carries the same numbers: `summary.json` and
  `stdout.txt` equal the earlier recording's once line endings are
  normalised, which the repository does to every text file it stores, and
  `stderr.txt` and both plots are byte for byte what the earlier recording
  wrote. Between the two, `src/outoftime/performance_label.py` changed three
  times, adding the left-truncation and seasoned-acquisition options and
  the in-window reading of a gap in a loan's record; each is off unless a
  definition sets it, and the structure run sets none, which is what the
  identity measures.

  What moves is the manifest, and it is the reason for the repeat. The
  earlier recording pins the label module at bytes this checkout no longer
  holds, and it predates the manifest's list of the repository files a run
  executes, so the claim gate refuses it. The 2026-09-19 recording passes
  it, and a ledger row about this book's axis, label or trajectory cites it
  and nothing earlier.

## Cold audit

Audited 2026-09-12 on `fm-reduce3` and `fm-vintage-structure3` together, by an
auditor given the two scripts, the label module, the twenty-eight sample zips,
the two manifests and this file down to its log, and asked what the runs show.
It was not given what they were expected to show. Nor the log entries above,
nor ADR-0006, where the reading of the label had already been decided. The
recording of 2026-09-19 carries the audit unchanged: its summary and its
standard output are what `fm-vintage-structure3` wrote once line endings are
normalised, and its standard error and both plots are byte for byte the same.

Every figure in both recorded outputs reproduced under an independent
reimplementation that read the zips rather than the reduced files. The layout
widths hold at 31 and 35 on all twenty-eight and the twenty-eight hashes match.
The origination quarter encoded in the identifier and the first payment date
disagree on none of the 1,362,500 loans. The whole of 2005, 2009 and 2019,
150,000 loans, was rebuilt from the raw monthly records with no mismatch on
the period count, the last age, the first ninety-day month under either
reading, the termination code or the termination age, and the label itself is
identical on every one of the 49,537, 49,907 and 49,908 labelled loans, under
both windows and under both readings. In the structure run no cohort figure
differs under either window or either reading of relief, and the counts above
the floors reproduce at all three resolutions. Kill criteria 2 to 4 do not
fire. No cohort has a median first payment lag outside one to four months, and
the largest late share in any of them is 4.58%, on 2000Q1. The
widths are what the layout says. The smallest labelled share of a mature cohort
is 0.9534 at twelve months and 0.9530 at twenty-four, both on 2000Q1, against a
floor of one half.

Four findings are not defects in the runs. Each constrains what the runs can
be read to mean, and each is now carried by code or by a pre-registered rule
rather than by care. Three further observations were deferred.

- **Kill criterion 1 fires under the reading this book is modelled on.** The
  criterion counts quarterly cohorts above the floors at twelve months under
  the reported reading, where there are eleven; with relief set aside there are
  six, 2007Q3 through 2008Q4, against the eight it asks for. The resolutions
  move with it: sixteen half-years rather than twenty-three and nineteen years
  rather than twenty-one at twelve months, and at twenty-four months 41
  quarters rather than 55 and 45 half-years rather than 48, the annual count
  unchanged at 26. The kill is what ADR-0006 acts on when it takes
  twenty-four months on half-year cohorts as the primary reading. The quarterly
  twelve-month design dies either way: on the spread condition under the
  reported reading, on the count under the set-aside one.
- **The relief flags are populated only from 2014, so the set-aside label is
  two definitions along the axis rather than one.** The earliest month carrying
  a borrower assistance plan anywhere in the book is 2014-01 and the earliest
  carrying a declared disaster delinquency is 2014-06; before those no loan can
  be read as relieved, whatever its state. A build trained before the flags and
  scored after them therefore meets a label that changed under it, and the
  difference would read as drift. What carries this is not a caveat: EXP-005
  partitions the grid into a *pre-flag* regime whose windows close before
  2014-01, a *straddling* one from 2011H2 to 2013H2 and a *flagged* one from
  2014H1, reports the criterion rows on the pre-flag and flagged scopes beside
  the pooled reading, and kills a verdict whose sign differs between them.
- **The label as this run builds it accepts a loan whose record begins after
  the window it is labelled over.** Across the book the first observed age is
  one month or less for 1,303,405 loans, two to six for 39,392, seven to twelve
  for 5,990 and thirteen to twenty-four for 5,630, while 8,083 have no row in
  the twenty-four-month slice at all — ten of them the loans with no
  performance record the reduction admits, the rest acquired later than the
  slice reaches. On the structure run's label that leaves 13,258 loans labelled
  at twelve months whose record starts after the window has closed, three of
  them defaults, at worst 9.6% of 1999Q1, 6.1% of 1999Q2 and 3.7% of 2013Q3,
  and 7,814 at twenty-four months with one default among them. Descriptively
  the effect is small; as a training label it is a missing observation read as
  a non-default. `performance_label` now takes a `max_first_observed_age`, the
  grid sets it to 3, and the structure run sets none. That is why the counts
  above are the ones this run reports and not the ones the modelled book uses.
- **Seven columns shift their coverage or their levels along the axis.** The
  vantage score holds its sentinel in every year and is empty throughout. The
  valuation method and the special eligibility programme begin partway along.
  The channel's third-party level runs above half in 2005 and reaches zero
  after 2008, and the HARP flag cannot exist before 2009. The debt-to-income
  ratio and the metropolitan area differ in missing share between the first
  cohort and the last. A feature set that merely happens to be populated in
  the training years and empty in the scored ones measures the file rather
  than the borrower. All seven are now named in `src/outoftime/fm_features.py`,
  in two tables that between them hold eleven columns, each with the clause
  that removes it or the half-year its coverage begins; `coverage_report`
  refuses a column whose behaviour does not match its entry.
- **The three deferred observations, none of them a defect.** 2024Q1 is partly
  matured at twenty-four months, 7,445 of its 12,500 loans, and reads as a
  whole cohort unless the floors exclude it. A whole-loan sale, a
  reperforming-loan sale or a confirmed defect terminates 11,333 loans
  book-wide, of which 1,470 and 1,678 fall inside the two windows.
  Thirty-three loans among the three rebuilt years carry a gap in their
  monthly record, which `performance_label` gained a reading of on 2026-09-12
  beside the truncation parameter, off unless a definition sets it.
