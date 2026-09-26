# ADR-0003 — the calibration instrument is assembled, not written

Date: 2026-08-27. Status: accepted.

## Decision

The metrics module depends on `scores` for the PAV reliability curve and its
bands, adds the CORP score decomposition on top as three mean scores, and
implements no scoring rule of its own. Calibration is reported per vintage as
the curve plus miscalibration, discrimination and uncertainty. A pooled Brier
score is reported only beside its own decomposition, never instead of it.

## Context

The plan of record was to reuse the proper scoring rules in ScoringBench
(arXiv:2603.29928) rather than reimplement them. Full text shows the suite does
not apply. ScoringBench drops any target with exactly two unique values as
classification, so nothing in it has ever been run against a binary label, and
its rules do not survive the move: CRPS on a binary outcome is the Brier score,
and the interval, energy and weighted-CRPS rules have no direct analogue.

What the paper does hand over is protocol rather than code, and one piece of it
binds here. Fold scores within a dataset are collapsed to a single number
before anything is compared across datasets, because correlated repeated
measures on one subject inflate the effective sample size. Per-vintage scores
on one book are repeated measures on one subject in exactly that sense.

The instrument that does apply to a binary label is CORP (arXiv:2008.03033).
Reliability diagrams are unstable because of one free parameter, the bin
count. CORP removes it, fitting isotonic regression through the
pool-adjacent-violators algorithm instead, and decomposes the mean score under
any proper scoring rule into components that are non-negative and sum exactly.
That decomposition is the measurement the credit TFM papers reduce to a
scalar.

It is already in Python. `scores`, the Australian Bureau of Meteorology's
forecast-verification package, implements the PAV fit with bootstrap confidence
bands and cites the paper. The decomposition is not packaged, but it is the
difference between three mean scores computed on a fit that `scores` already
returns, which is a function and not a contribution.

## Consequences

- `scores` joins the dependency set, and its version is pinned in every
  manifest. It brings xarray, which the loaders do not otherwise need; the
  metrics module takes numpy arrays at its boundary so that dependency stops
  there.
- Reliability is a curve with bands, per vintage. A vintage too thin to carry a
  band is reported as too thin rather than plotted without one.
- Miscalibration and discrimination are reported separately. The finding this
  project exists to detect is a model whose ranking holds while its
  probabilities drift, and that is invisible in the sum.
- The threshold at which a lending decision is made is a parameter of the
  measurement, not a footnote. The mixture representation of proper scoring
  rules gives an advantage curve against the threshold instead of a number
  averaged over thresholds nobody lends at. Reading Ehm and colleagues in full
  is a precondition for using it, and it is unread.
- No claim rests on the CORP decomposition until the implementation is checked
  against a case with a known answer: a perfectly calibrated forecast has zero
  miscalibration, a constant forecast has zero discrimination, and the three
  components reproduce the mean score exactly. The published worked example
  supplies four such cases.

## What would overturn this

A Python implementation of the decomposition that is maintained and tested,
which makes the local function redundant. `calibre` claims to be one and is
unverified.
