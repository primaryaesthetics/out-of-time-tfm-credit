---
id: 000
title: Template
dataset:
status: proposed
opened:
closed:
---

# EXP-000 — template

Copy to the next free number before writing any code. An experiment with no
kill criteria does not get opened.

## Question

One sentence, and it must be answerable by a measurement rather than by an
opinion. "How do TFMs do out of time" is not a question; "does the TFM/GBM AUC
gap on Lending Club survive a time-ordered split" is.

## What the measurement discriminates

Write the sentence before running anything:

> If this comes out high, hypothesis X is wrong; if low, Y is wrong.

A measurement with no such sentence is a benchmark, not an experiment. This is
the single check that catches the failure mode where every piece of work produces
honest numbers and the work moves sideways for weeks.

## Setting

- **Dataset and vintage range.** Which origination dates, how many cohorts.
- **Split.** The `temporal_split` call, in full, including `embargo_days` and
  the reason for its value.
- **Models and tuning budget.** Equal across contenders, stated in trials or
  wall-clock. Note explicitly where a zero-shot model is being compared to a
  tuned one, because that asymmetry cuts both ways and is not neutral.
- **Metrics.** Which, and why those. If a scalar is reported, say what its
  decomposition is expected to show.
- **Seeds.** How many, and what the run-to-run spread is expected to be.

## Kill criteria

The concrete observation that ends this experiment, written now, before any
code, so it cannot be renegotiated when the result starts being inconvenient.
Two or three, each cheap to check.

Include the one that kills the *project* branch, not just this run: if the
effect is within the seed-to-seed spread, there is no effect, and that is the
answer rather than a reason to add seeds until it moves.

## Cheapest falsifying run

The first thing to run. If it is not cheap, decompose further. Name the
dataset slice, the size, and what output would count as a kill.

## Prior art check

Which rows of [../landscape/prior-art.md](../landscape/prior-art.md) this
experiment stands on, and their status. Standing on an `abstract-only` row is
allowed for an exploratory run and forbidden for a claim.

Date of the sweep this was opened under. If `scripts/check_sweep.py` is red,
this section cannot be filled in and the experiment cannot be opened.

## Plot

Every run produces at least one plot of *structure*, saved beside the manifest:
the reliability curve rather than the Brier score, the per-vintage trajectory
rather than the pooled number, the distribution rather than its mean. A bar
chart of the headline number does not count.

The plot is worth making precisely when nobody knows what it will show. If the
answer is already known it is an illustration.

## Log

Append-only. Date, what was run, what was observed, pointer to the experiment
directory. No conclusion without a pointer.

## Cold audit

Who audited, on what date, from what — and what they said the run shows before
being told what it was supposed to show. A result audited only by whoever
produced it is not finished.
