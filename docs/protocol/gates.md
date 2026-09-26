# Gates

Six gates. Nothing advances past one that is not green, and no gate is
negotiable after the fact.

The predecessor repositories used four. Two are new here, and both exist
because this project fails differently from an algorithms project. An
algorithm that is wrong produces a wrong distance and the differential gate
catches it in seconds. A model study that is wrong produces a plausible number
and nothing catches it at all — unless a gate is built for exactly that.

## 1. Leakage gate

A split that lets the model see the future is the failure mode of this project,
and it does not announce itself: an out-of-time score that is too good looks
exactly like a promising result.

- Every split is built through `outoftime.splits.temporal_split`, which
  validates and raises rather than returning something wrong. A split assembled
  by slicing a sorted frame by hand does not count, whatever it evaluates to.
- The gap between the last training origination and the first scored one is
  at least the performance window the label is defined over. Two mechanisms
  enforce it, and which one applies depends on the caller. A direct call to
  `temporal_split` sets `embargo_days` to the window and drops the rows inside
  it; left at zero the split checks nothing, and zero is only correct on a
  dataset whose labels are known to be mature at every cutoff. The vintage grid
  of `outoftime.vintage.builds` does not drop those rows — it keeps them as the
  named blind window between training and scoring, which is why it calls
  `temporal_split` with the embargo at zero — and enforces the gap instead in
  `assert_no_leakage`, against the origination dates of every build it emits.
- Every feature declares when it becomes knowable relative to origination, in
  the loader, by hand. `assert_features_knowable` refuses an undeclared one.
  There is no way to infer this from the data: on Lending Club
  `last_fico_range_high` sits beside `fico_range_high` under a name one word
  longer, and is refreshed every month of the loan's life.
- Enforced by `pytest`, and the tests construct the mistakes rather than
  asserting the happy path. An assertion that has never fired is an assertion
  nobody has checked.

## 2. Determinism gate

A result that does not reproduce is not a result.

- Every run records every seed it used, in its own output beside the manifest:
  `scripts/record_run.py` pins the commit and the package versions, and the
  producing script writes the seeds it drew from — the scoring-sample seed, the
  context seeds — into its summary under a `seeds` key. Model libraries with
  nondeterministic kernels (any GPU forward pass) are run twice and the
  disagreement is recorded rather than hidden by averaging.
- The same command on the same commit and the same input hash produces the same
  numbers, or the manifest says which component is nondeterministic and by how
  much.
- Reported to three significant figures at most, and never to more precision
  than the run-to-run spread supports.

## 3. Baseline gate

A comparison against a strawman is not a comparison.

- The classical baseline is a scorecard built the way a risk team builds one —
  WOE binning, logistic regression, the coarse-classing decisions written down
  — and a tuned gradient-boosting model. Not a default-parameter
  `LogisticRegression()` on raw columns.
- Tuning budget is stated and equal across contenders, in wall-clock or trial
  count, and recorded in the manifest. A foundation model that needs no tuning
  wins on that fact; it does not win because the baseline was given ten trials.
- Every model is evaluated on the identical split object, not on a
  re-derivation of the same intent.

## 4. Sweep gate

The premise of this repository is that a gap in the literature is open. That is
a claim about the world, and it goes stale.

- `docs/landscape/SWEEPS.md` carries one dated entry per sweep, newest first,
  including the sweeps that found nothing — an empty sweep is evidence and a
  missing sweep is not.
- `scripts/check_sweep.py` fails when the newest entry is older than fourteen
  days. `--queries` prints the standing search list.
- A stale sweep does not block a cleanup commit. It blocks opening an
  experiment, writing a claim, and any public text, because each of those
  asserts the gap is still open.
- Anything load-bearing gets the paper itself through the `primary-source`
  skill and `scripts/extract_paper.py`, and a `verified` status in
  [../landscape/prior-art.md](../landscape/prior-art.md). An abstract is not a
  source. Abstracts routinely omit what a study did not measure, which here is
  the whole question.

## 5. Claim gate

Every number and every assertion in a committed file traces to evidence.

- [../ledger/CLAIMS.md](../ledger/CLAIMS.md) is the index. Each row: claim ID,
  the statement, the dataset and split it holds on, a pointer to an experiment
  directory.
- Public files cite claim IDs. `scripts/check_claims.py` verifies that every
  cited ID exists and every pointer resolves, and fails CI otherwise.
- A number that did not come through `scripts/record_run.py` is not evidence.
- A claim whose evidence is superseded is not edited in place. It is marked
  superseded and a new row is added.

## 6. Hygiene gate

`scripts/check_hygiene.py` scans committed files and fails on:

- attribution of authorship to any tool or model,
- process meta-commentary — text about how the work was carried out, or what
  was tried and abandoned, in files that describe the artifact.

Runs in CI on every commit. The repository is one person's work and has to
read as such.

The rule that a number in public prose carries a claim ID is not automated.
No grep separates a result from a threshold, a date or a version number, and a
checker that flagged all of them would be switched off within a week. It is
enforced by the claim gate on the IDs that are cited, and by review on the
numbers that are not — every one of which has to trace to a run directory in
the sentence that states it.

## The cold audit

Not a gate, because it cannot be automated, and the most valuable check here.

No result is written up without an independent audit. The auditor, who did
not produce the work, is given the code, the data and the manifest, and **not** the reasoning, and asked to state what the
run shows. Where the two accounts differ, the difference is the finding.

This is how the false completeness clause in `beyond-dijkstra` was confirmed,
and it is the one practice that catches the error class no test suite reaches:
a correct measurement of the wrong thing.
