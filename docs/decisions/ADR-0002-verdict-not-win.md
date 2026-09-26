# ADR-0002 — the verdict is the deliverable, in either direction

Date: 2026-08-27. Status: accepted.

## Decision

The result of this project is the answer to "do these models survive
out-of-time, calibration and stability evaluation", and both answers are
shipped with equal weight.

## Context

The predecessor projects published negative results as headline findings: the
sorting-barrier algorithm never beats Dijkstra at storable sizes, and the
successor paper's completeness clause is false as stated. Both are more
citable than a marginal positive would have been.

The failure mode this rules out is subtle and common: a study that wants a
particular outcome chooses its split, its baseline and its seed count in ways
that each look defensible and together decide the answer.

## Consequences

- Kill criteria are written before code and cannot be renegotiated afterwards.
- Seed spread is reported beside every number, and an effect inside the spread
  is not an effect.
- The tuning budget is stated and equal, and the zero-shot-versus-tuned
  asymmetry is named wherever it applies.
- A confirmatory finding is written up as the first honest out-of-time
  validation of the paradigm, not buried.
