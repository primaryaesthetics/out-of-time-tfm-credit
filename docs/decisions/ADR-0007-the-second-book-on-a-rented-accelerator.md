# ADR-0007 — the second book on a rented accelerator

Date: 2026-09-12. Status: accepted.

## Decision

The node bundles of the Freddie Mac sample are scored on a rented GPU
instance. Renting an instance is buying compute, not handing the data to
anyone: the licensee rents it, alone holds the key it is reached with, copies
the bundle in, runs the scorer, copies the scored rows out, and destroys the
instance. That is not a distribution of the dataset or of a Derived Product to
a third party in the sense of the terms of use (version of 2025-11-03), and it
is the reading EXP-005 makes the foundation-model side of its grid conditional
on.

## How the instance is used

- One instance, rented on the licensee's own account and reached by an SSH
  key only the licensee holds.
- The bundle carries what the scorer reads and nothing more: row positions
  into the loaded book, the outcome, and the model matrix. No loan identifier,
  no date column, no geography finer than the metropolitan area
  (`fm_export_context.py`, `fm_features.py`).
- Nothing is left behind: once the result is downloaded and its hash
  checked, the instance is destroyed, not stopped, and no snapshot or image
  of it is kept.
- The scored rows that come back are row-level material like the rest: they
  stay on the licensee's machine and out of the repository (`.gitignore`,
  `experiments/*-fm-*/`).

## What this does not cover

This record covers rented instances. No other device takes a Freddie Mac
bundle: not a machine lent by a person, and not a hosted notebook, where the
bundle would sit in the host's storage on terms the licensee does not set.

## Context

The terms were read in full on 2026-09-06: the
dataset "in whole or in part" and any Derived Products may not be distributed
to third parties; research results may be published when they cannot be used
to derive or recreate any part of the dataset. The scorer needs an NVIDIA
device for TabICL, and this study owns none; without a rented instance the
foundation-model side of EXP-005 has no device to run on.

*Note of 2026-09-13.* The bundle's geography is the state and nothing
finer. "No geography finer than the metropolitan area" above is a bound,
not the bundle: `msa` is out of the matrix under the value rule of EXP-005,
missing on half the first cohort and a ninth of the last; `postal_code` is
out a priori; `state` is the finest geography any bundle carries
(`fm_features.A_PRIORI`, `fm_features.VALUE_DROPPED`;
`experiments/2026-09-13-fm-features`). The decision is unchanged.
