# ADR-0006 — the second book: a default outside relief, read at twenty-four months on half-year cohorts

Date: 2026-09-06. Status: accepted.

## Decision

On the Freddie Mac sample the label is ninety days past due, or REO, or a
termination by third-party sale, short sale or REO disposition, within
twenty-four months of the first payment month, **with the months spent under
a borrower assistance plan or a declared disaster hardship set aside**. The
same event counted with those months included is computed beside it in every
run as the reported-delinquency reading, and is never the headline.

The trajectory is read on half-year origination cohorts. The twelve-month
window on annual cohorts is the horizon check, the counterpart of the
twenty-four-month check in ADR-0005 with the roles reversed. No quarterly
design is built on this book, and the full standard files are not fetched.

## Context

EXP-003 measured the sample before anything was modelled on it, in
`experiments/2026-09-06-fm-vintage-structure3`.

**The relief months.** Freddie Mac reports the delinquency status off the due
date of the last paid installment, so a borrower in a payment-relief plan is
reported delinquent for as long as the plan runs. Of the twelve-month defaults
counted the reported way, 91% in the 2019 cohorts and 86% in the 2020 cohorts
were under a plan or a disaster flag at their first ninety-day month; at
twenty-four months, 77% of 2018, 89% of 2019 and 77% of 2020. Set those
months aside and the 2018 to 2020 hump in the trajectory, which stood above
2007 at twelve months, is not there: the cohorts read 0.4% to 0.6% at
twenty-four months, where their neighbours read the same. The hurricanes of
2017 are the same effect at a smaller scale, 45% of the 2017 cohorts'
twelve-month events.

*Note of 2026-09-20.* "under a plan or a disaster flag at their first
ninety-day month" describes the recorded quantity more strongly than the
record supports. What is recorded is one minus the set-aside defaults over the
reported defaults: a loan under relief at its first ninety-day month that
reaches another, unflagged, ninety-day month inside the window stays a default
under both readings and is not in the share. The percentages are unchanged and
the decision does not turn on the difference.

A study whose question is whether calibration holds across regimes cannot
carry a regime that is a reporting convention. A model scored on the 2019
cohorts under the reported reading would appear to have missed a fourfold
rise in default that mostly cured when the plans ended, and that appearance
is the manufactured finding this repository is built to refuse. The label
therefore counts a credit event, and a legislated payment holiday is not one.
A loan that is still ninety days past due after its plan ends, or that ends
in a bad termination, is a default on the month that happens.

**The window and the resolution.** A hundred defaults on 12,500 loans needs a
0.8% rate, and a prime thirty-year fixed-rate book sits under that at twelve
months outside 2007 to 2008: with relief set aside, six quarterly cohorts
clear the floors under the twelve-month window, all in 2007Q3 to 2008Q4, and
sixteen half-years. At twenty-four months, 41 quarters, 45 of 51 full
half-years, and every full year clear them; the half-years that miss are
2003H1, 2013H1, 2014H2, 2015H1, 2020H2 and 2021H1, each short of the hundred
defaults by a margin the floor exists to refuse. The half-year is the finest
resolution at which the trajectory is nearly continuous, and it is the
resolution the EXP-002 builds already use for their as-of dates. The
twelve-month window survives at annual resolution, 19 of 26 full years, which
is enough for a horizon check and not for a trajectory.

The product decides the horizon as much as the sample does. Twelve months is
the regulatory horizon and the one ADR-0005 chose for a three-to-five-year
consumer loan; on a thirty-year mortgage the twelve-month rate in a benign
year is one to two loans in a thousand, and the study's instruments have
nothing to read at that level.

## Consequences

- The blind gap on this book is twenty-four months. A build at date T trains
  on loans whose first payment is at least twenty-four months before T and
  scores the half-year cohorts after it. `vintage.LABEL_LAG_MONTHS` becomes a
  per-book parameter rather than a constant.
- The two books are not on the same label, and no number is compared across
  them as if they were. What is compared is the shape of each model's
  trajectory on each book.
- The assistance and disaster flags exist from January 2014. Before that the
  two readings coincide by construction, and relief that existed then, under
  the modification programmes of 2009 onward, is counted as default where it
  produced a ninety-day month. The size of that is bounded by what the flags
  show in the benign years after 2014, 3% to 15% of events, and it is
  reported beside the trajectory rather than corrected for.
- The relief share by cohort is a measurement of the reporting regime and is
  kept as a figure in its own right.
- The reduced slice keeps `borrower_assistance_plan` and
  `disaster_delinquency`, so both readings can be rebuilt without the zips.

## What this does not settle

Whether a model given the relief-set-aside label will show a shift at 2022,
where the twenty-four-month rate rises from 0.5% to 1.3% and stays there
through 2024 under both readings. That is a measurement for EXP-004, and
nothing about it is written until it has run.

*Note of 2026-09-12.* EXP-004 became the published-protocol comparison on
Lending Club; the out-of-time study on this book is EXP-005, and the
measurement above is one of its reported readings. EXP-005 also fixes what
this record leaves open along the axis: the flags' start in January 2014
partitions the scored cohorts into regimes read separately, and loans first
observed after age three are excluded from labelling.
