# ADR-0005 — a twelve-month default window, on an estimated default date

Date: 2026-08-30. Status: accepted.

## Decision

Lending Club alone carries the study. Freddie Mac stays an extension and is not
collected now.

The label is default within twelve months of origination. The same trajectory
is computed again at twenty-four months and reported beside it, as a check that
the conclusions belong to the models rather than to the window.

## Context

The book runs 2007-06 to 2018-12 across 47 quarterly cohorts, measured in
EXP-001 rather than assumed. Performance columns stop in 2019-03, so a
twelve-month window admits cohorts through 2018Q1 and a twenty-four-month
window through 2017Q1: forty-four labelled quarters against forty, and above a
floor of five thousand loans and a hundred defaults, twenty-eight against
twenty-four.

A twelve-month horizon is what the regulatory frame is written in. It is
also short for this product. Among the charge-offs of cohorts old enough to have been observed to
the end — originations through 2016-03 — the median last payment falls at month
17 and the upper quartile at month 25, so a twelve-month window admits 14.9% of
the charge-offs those cohorts eventually suffer and a twenty-four-month window
57.5%. On that same population the rate reads 17.2% ever charged off, 9.9%
within twenty-four months and 2.6% within twelve. The three are not
interchangeable, and a lifetime rate quoted beside a windowed one is the
commonest way this label is misread.

Neither horizon is wrong and the disagreement between them is informative, so
both are computed. Reporting one and mentioning the other is what invites the
question of whether the finding is an artefact of the window; answering it
costs one more pass over cohorts that are already built.

**There is no charge-off date in this file.** The default date has to be
estimated, and the only usable signal is `last_pymnt_d` together with Lending
Club's practice of charging a loan off after roughly 120 days of delinquency. A
loan is taken to have defaulted within the window when its status is terminal
and its last payment falls at least five months before the window closes.

Five months is measured, not inherited. The lag decides the level of every
rate in the study — across lags from zero to eleven months the mean cohort rate
spans 0.24% to 5.68% — and it decides how much of the recent book is silently
censored, because a loan the issuer has not yet charged off reads as a
non-default. Five is the only value in that sweep that both admits a usable
event rate and leaves no such loan unrecognised; at zero months there are
34,014 of them. The sweep is
[`experiments/2026-09-04-lc-label-sensitivity`](../../experiments/2026-09-04-lc-label-sensitivity)
and `LabelSet.unrecognised` reports the count for any configuration.

*Note of 2026-09-19, on the order of the paragraph above.* The paragraph was
added on 2026-09-04. The five months were fixed on 2026-08-30 from the
issuer's charge-off practice, as the paragraph before it says, and the label
module has defaulted to them since then; the count of unrecognised loans and
the sweep that reads it were written on 2026-09-04. The sweep therefore
confirms a lag already chosen rather than choosing it, and "measured, not
inherited" is to be read that way. The sweep covers 0, 2, 3, 5, 8 and 11
months, so whether four months also leaves no loan unrecognised is not
recorded, and five is the shortest lag in the sweep that does. Claim C-005 in
[../ledger/CLAIMS.md](../ledger/CLAIMS.md) states it in those terms.

**`chargeoff_within_12_mths` is not the label.** The name reads like an
outcome and the column is a bureau attribute measured when the borrower
applied. Its mean is 0.0098 among charged-off loans against 0.0089 among fully
paid ones — no separation, which is what an application-time input looks like.
Anything that shape belongs on the feature side of the leakage gate or nowhere.

## Consequences

- The default date is an estimate with real uncertainty, and every number
  resting on it inherits that. The bias runs one way across the whole book,
  since the charge-off practice is a policy rather than a per-loan accident, so
  cohorts stay comparable even where the level is off.
- The estimate degrades where a loan was in hardship or settlement, because
  payments resume on a different schedule. Those columns are almost entirely
  null before 2017, which means the degradation is not uniform across the
  trajectory and has to be reported rather than assumed away.
- Seven of the eight date columns that reach past the last origination are
  performance-window columns and none may define a split. `last_pymnt_d` is now
  a deliberate exception: it builds the label, never a feature, and the leakage
  gate has to be able to tell those apart.
- The twenty-four-month trajectory is four quarters shorter. Where the two
  disagree, the disagreement is the finding and not a defect to be tuned away.
- The regime-shift framing is dead on this dataset and is dropped. Nothing here
  tests behaviour across 2020.

## What this does not settle

Whether arXiv:2605.18635 built its reported split on a performance-window
column. EXP-001 establishes that the split it describes cannot be constructed
from the file it cites, and that is as far as measurement reaches. The rest is
for the cold audit, and no statement about that paper is written anywhere until
the audit has run.

## Addendum of 2026-09-19 — the eight columns

The consequence above calls seven of the eight date columns that reach past
the last origination performance-window columns, with `last_pymnt_d` an
exception. What the recorded run measures is narrower: each of the eight
carries values later than the book's last origination, so none can define an
origination-time split, and a split cut on any of them sorts loans by outcome
rather than by origination time
([`experiments/2026-09-19-lc-vintage-structure`](../../experiments/2026-09-19-lc-vintage-structure)).
Which of them is a performance-window column in the sense of the paragraph
above is a reading the run does not make. Claim C-003 in
[../ledger/CLAIMS.md](../ledger/CLAIMS.md) states the eight on the measurement
and leaves the classification out, and that is the statement to quote; the
classification stays here as a reading beside it. The decision does not
change, and neither does the role of `last_pymnt_d`: it builds the label and
is never a feature.
