# Out of Time

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22994434.svg)](https://doi.org/10.5281/zenodo.22994434)

The code and the record behind *Out of Time: A Pre-Registered Vintage,
Calibration and Stability Evaluation of Tabular Foundation Models for Credit
Default* (Nikolai Khobotov, 2026),
[10.5281/zenodo.22999138](https://doi.org/10.5281/zenodo.22999138).

The study reads TabPFN-3 and TabICLv2 as shipped, beside a weight-of-evidence
scorecard and a tuned gradient-boosting model, out of time on the origination
vintages of two credit books: Lending Club's accepted loans and the sample of
Freddie Mac's Single-Family Loan-Level Dataset. Each model's discrimination
is read on the scored cohorts as they age. Its calibration and the stability
of its score population are read beside it, against kill criteria fixed in
the pre-registrations, by dated amendment where they changed, before any
foundation-model run they judge.

This repository is an export of the study's working repository at a single
commit, without its history. It holds the code with its tests and the
pre-registrations with their logs. The claim ledger is here too, and every
recorded run with its manifest and aggregate outputs. It holds no row of
either book.

## Where things are

| Path | What it holds |
| --- | --- |
| `docs/experiments/` | The pre-registrations, EXP-001 to EXP-005, and the dated logs of EXP-002 (Lending Club) and EXP-005 (Freddie Mac). Changes to a registered design are dated amendments inside the file. |
| `docs/ledger/CLAIMS.md` | Every number the paper states, one row per claim, each pointing at the recorded run it was read from. A corrected claim is superseded by a new row, and the old one stays. |
| `docs/protocol/gates.md` | The six gates a result passes before it is a claim: leakage, determinism, baseline, literature sweep, claim and hygiene. |
| `docs/protocol/deposit.md` | The archived protocol on Zenodo, [10.5281/zenodo.22803069](https://doi.org/10.5281/zenodo.22803069), and what it contains. |
| `docs/decisions/` | Decision records: evidence before code, the verdict and not the win, the scoring rules, the compute and the dataset, the label, the second book and its compute. |
| `docs/landscape/` | What the published evaluations of tabular foundation models on credit measure and what they leave out (`prior-art.md`), and the dated literature sweeps (`SWEEPS.md`). |
| `experiments/<date>-<slug>/` | One directory per recorded run. `manifest.json` gives the command, the commit it ran at, the machine and the Python version. A run recorded by `scripts/record_run.py` also gives the versions of the libraries and, in all but 22 runs of 2026-08-30 to 2026-09-04, the sha256 of every input and of every code file the command executed. A run made on a machine that held no copy of the repository has a manifest assembled from what that machine returned, marked `written_by_hand`, with the hashes of its job and result archives. Two probes of 2026-08-30 on a hosted notebook have a manifest assembled by hand from their surviving output, marked `recorded_by`. |
| `CODE.md` | Per run, whether the code it ran is identical in this snapshot or was changed afterwards, and which files changed. |
| `src/outoftime/` | The library: time-ordered splits that refuse a leaking configuration, the label, the vintage grid, the scorecard and gradient-boosting builds, the metrics. |
| `scripts/` | The run scripts, the paper's table and figure scripts, and the gates. |
| `tests/` | The test suite. |
| `packages/psi-inference/` | A copy of the population-stability package; see below. |

`prior-art.md` and `SWEEPS.md` name `papers/<id>` as the place a paper's full
text was extracted to by `scripts/extract_paper.py`. That directory holds
third-party texts and is not included.

## Data

Neither book is redistributed.

**Lending Club.** The file is `accepted_2007_to_2018Q4.csv.gz` from the Kaggle
dataset [wordsforthewise/lending-club](https://www.kaggle.com/datasets/wordsforthewise/lending-club):
392,582,231 bytes, sha256
`55c16f75120f897683f02e7aabcf080d0e4a20c4832feb1d592cfa941bd62a2d`, the size and
hash recorded in the Setting of claim C-003. Check a downloaded copy against
the hash before any script reads it, and put it at
`data/raw/accepted_2007_to_2018Q4.csv.gz`. The loans are Lending Club's, and
no file here carries one. The Lending Club runs are included through their
aggregate outputs: cohort-level metrics, tables and figures, and fold
assignments that give a row's position and fold and no field of the
dataset.

**Freddie Mac.** The book is the sample of the
[Single-Family Loan-Level Dataset](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset),
Release 47 (July 2026): the 28 files `sample_1999.zip` to `sample_2026.zip`,
obtained from Freddie Mac under the dataset's terms and put in
`data/raw/freddie-mac/`. A later release of the sample can differ from the
one read here. The terms allow research results and related derived products
to be made public for noncommercial purposes, provided they cannot be used to derive or recreate any
part of the dataset or to identify any individual. The Freddie Mac results
here are therefore held at the level of cohorts and builds, and no file
carries a row or a loan identifier.

The data are provided by Freddie Mac; the results are the author's own.

## Reproducing a table or a figure

Every result in the paper comes from a recorded run. The ledger row names the
run, and the run's `manifest.json` gives the command that produced it and the
commit and package versions it ran under. A new run is recorded the same way:

```
python scripts/record_run.py <slug> -- python scripts/<script>.py <arguments>
```

which writes `experiments/<date>-<slug>/` with a fresh manifest beside the
output. Compare its output with the recorded one file by file; a file that
records the sha256 of its inputs differs wherever an input has changed since,
the ledger above all, or was hashed with other line endings.

The paper's two tables are read from recorded runs and from the ledger alone,
so they can be rebuilt from this repository without either book. The script
compares the code of each run it reads against the committed files, so it needs
a git checkout. A clone is one. In the release archive, which has no history,
commit the contents first:

```
git init
git add -A
git commit -m snapshot
```

Then:

```
python scripts/paper_tables.py --out-dir tables
```

The script refuses to print if the code of any run it reads differs from what
that run executed, and it checks every value of the second table against the
ledger row that states it.

A figure is a file a recorded run drew, copied into the paper byte for byte.
`scripts/paper_figures.py` lists each figure with its run. Redrawing one
reads the row-level score files, which are not included. It needs the book
itself, and the score runs rebuilt from it with the commands in their
manifests. The manifests of the foundation-model scoring runs name the machine
and the library versions each ran under.

## Gates

The tests and the gates run on Python 3.12 with the project's optional
dependencies installed:

```
pip install -e ".[data,models,metrics,dev]"
python scripts/check_claims.py      # every ledger pointer resolves; cited code is unchanged
python scripts/check_hygiene.py     # public text carries no process commentary or private path
python scripts/check_sweep.py       # the last literature sweep is recent enough
python -m pytest -q
ruff check .
```

`check_claims.py` and `check_hygiene.py` read `git ls-files`, so they too need a
git checkout; in the release archive, commit its contents first as above.
`check_sweep.py` fails once the last sweep recorded in `SWEEPS.md` is
older than its limit, which it will be for a reader of this snapshot; that
failure dates the snapshot and says nothing about the claims.
`scripts/check_recorded_code.py` needs the history of the working repository,
which is not published because it holds row-level files of the Lending Club
book. `CODE.md` is the table it wrote at the exported commit.

## psi-inference

The population-stability tests, the Yurdakul–Naranjo critical value of the
PSI, the Population Resemblance Statistic and the effect-size and overlapping
tests, are released as a separate package:
[primaryaesthetics/psi-inference](https://github.com/primaryaesthetics/psi-inference),
DOI [10.5281/zenodo.22342343](https://doi.org/10.5281/zenodo.22342343).
`packages/psi-inference/` is a copy of it, and `scripts/psi_ztest_size.py`
imports it.

## Citing

`CITATION.cff` gives the citation for the paper. The paper is a preprint on
Zenodo. Its DOI,
[10.5281/zenodo.22999138](https://doi.org/10.5281/zenodo.22999138), resolves
to the latest version. The repository is archived on Zenodo: release v1.0.0 is
[10.5281/zenodo.22994435](https://doi.org/10.5281/zenodo.22994435), and the
concept DOI [10.5281/zenodo.22994434](https://doi.org/10.5281/zenodo.22994434)
resolves to the latest release. The archived protocol is
[10.5281/zenodo.22803069](https://doi.org/10.5281/zenodo.22803069).

## Licences

Three licences cover this repository, by path.

- **MIT**, in `LICENSE`: the code, meaning every file under `src/`, `scripts/`,
  `tests/` and `packages/`, and the configuration files at the root and under
  `.github/`.
- **CC BY-NC 4.0**, in `LICENSE-CC-BY-NC-4.0.md`: the recorded runs on the
  Freddie Mac book. These are every file under a directory of `experiments/`
  whose name contains `-fm-`, and the directory
  `experiments/2026-09-25-paper-tables/`, whose second table states Freddie Mac
  results. `git ls-files 'experiments/*-fm-*' experiments/2026-09-25-paper-tables`
  lists them.
- **CC BY 4.0**, in `LICENSE-CC-BY-4.0.md`: everything else, meaning the
  documents under `docs/`, this README, `CODE.md` and every other directory of
  `experiments/`.

The Freddie Mac outputs carry a noncommercial licence because the dataset's
terms allow research results derived from it to be made public for
noncommercial purposes only. The Lending Club and Freddie Mac data themselves
are under the terms of their providers and are not part of this repository.
