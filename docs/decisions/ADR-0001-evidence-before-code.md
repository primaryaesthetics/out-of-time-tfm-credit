# ADR-0001 — the literature is verified before any modelling code

Date: 2026-08-27. Status: accepted.

## Decision

No modelling code is written until the papers the premise rests on have been
read in full and marked `verified` in `docs/landscape/prior-art.md`.

## Context

This project exists because of a gap: published evaluations of tabular
foundation models on credit PD do not measure what a model-acceptance process
measures. That is a claim about what other people did *not* do, and abstracts
omit non-findings by construction.

Both load-bearing papers were read on the day the repository was created, and
both readings changed the premise. One reports Brier and LogLoss, so
"calibration is ignored" was false. The other uses a temporal split on Lending
Club, so "no temporal evaluation exists" was false. The gap survived in a
narrower and more defensible form — neither paper has more than one test
window, neither decomposes calibration, neither measures stability — but the
first draft of the premise would have been wrong in print.

## Consequences

- A claim may not stand on an `abstract-only` row. Exploratory runs may.
- `scripts/extract_paper.py` runs every available engine and flags the pages
  where they disagree, because the tables are where extraction fails and the
  tables are what a protocol claim is read from.
- The sweep gate makes this recurrent rather than one-off: the verification is
  only true as of a date.

## What would overturn this

Nothing short of the gap closing, in which case the project is rescoped rather
than the rule relaxed.
