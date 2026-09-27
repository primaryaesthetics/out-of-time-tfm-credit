#!/usr/bin/env python3
"""Pools the paired differences of one arm over every build it holds.

The experiment's hypotheses are written on the arm, not on a build: H1 on
the slope of AUC against model age, H2 on the Cox slope's distance from one
and H3 on the population stability index, each as a paired difference
between two models pooled over every cell of the expanding arm. This script
reads the row-level scores that `build_intervals.py` reads, for every build
of the arm at once, and puts one cohort-blocked bootstrap interval on each of
those differences.

The resample is shared across builds. A cohort's twenty thousand scored rows
are the same rows on every build that scores them, so the arm's ninety-nine
cells hold far fewer distinct loans than ninety-nine cells' worth; a
resample that drew each build's copy of a cohort separately would treat one
loan as up to nine and read an interval too narrow by that much. Here each
resample draws one index per cohort and applies it to every build's scores
on that cohort, and where the models carry context draws, one draw is chosen
per resample for every build at once, so draw k of one model on one build is
the same context draw as draw k on another.

Six statistics are pooled as the mean over the cells of the arm, paired by
cell: the Gini, |log O/E|, |Cox slope − 1| and the signed slope beside it,
the PSI of each cell against its
own reference, and the PSI of each cell against the same model's scores on
the build's first scored cohort. The two PSIs answer different questions.
Against the training rows or the context draw, the reference holds the
rows the model was fitted on or conditioned on, and the first step out of
sample is part of what is measured; against the first scored cohort, every
model's reference is out of sample alike and only the movement along the
vintage axis remains. A build with more cohorts contributes more cells to
the arm's mean, which is what "paired by cell" means; the mean over builds
with every build weighted alike is reported beside it, under the scope
`builds`.

Two slopes carry H1, and they are the same least squares with different
intercepts. With one intercept per build, only the movement of AUC within a
build reaches the slope; within a build, age and calendar quarter are one
axis, so this is the calendar slope net of build, and only the difference
of two models' slopes on the same cells is read. With one intercept per
cohort, only the movement of one cohort's AUC across the builds that score
it reaches the slope: the calendar is held fixed and the model's age varies,
together with the pool the model was built from. Neither identification is
free of the other's confound, and the two are reported side by side. The
per-build slopes are reported beside the arm's so that the reader can see
what the pooled slope weights: a build with nineteen cohorts moves it more
than a build with three, and a cohort scored by nine builds moves the
cohort-intercept slope more than one scored by two.

Three poolings, as on one build: every cell with the cohorts held fixed, the
youngest few cohorts of every build, and every cell with the cohorts
resampled too. The first two also report every statistic per build, under
the arm's shared resample; the point estimates equal the per-build
poolings' and the intervals differ only by the resample, which is the check
that the arm's pooling reads the same numbers. `--check-seeds` repeats every
pooling under other bootstrap seeds and names each difference whose star
changes, as the per-build script does.

Every directory named on the command line holds one build's `scores.parquet`
and `reference.parquet`, or is a recorded pooling whose `intervals.json`
names such directories under `sources`, in which case those are read. The
builds are grouped by their `build_id`; every build has to carry the same
models, the same context seeds and the same arm.

The floors are the per-build script's (EXP-005, Floors): a cell enters a
pooling only if its cohort holds at least 5,000 labelled loans and 100
defaults under the primary label, on the build run's verdict in its
`cells.csv`, named with `--cells`. The verdict is read per build and cohort
from that file, not from a recorded per-build pooling, since a pooling named
here stands for its score directories and is re-read from them. A cohort
under the floors leaves every pooling of the arm and the resample alike. The
second stability reference stays the build's first scored cohort, under the
floors or not: a reference is a score distribution read at its deciles and
the floors are counts of the label; its own cells leave the mean as before.
Without `--cells`, an arm whose scored rows fall under the floors on any
cohort is refused.

Further scopes, under the pooling of every cell and the nearest cohorts and
none a criterion. With `--cells`, the pre-flag and flagged cells of the label
(EXP-005, the label's definition) are pooled as scopes of their own, each
also as the mean over the builds holding any of its cells. With
`--h2-scopes`, the crisis cells of 2007H1 to 2009H2 and the cells of 2022H1 to
2023H2 are pooled the same way, and per model and build the ratio of O/E on
2022H2 to 2023H2 over O/E on 2020H1 and 2021H2 is read (EXP-005, H2). With
`--outcome outcome_reported` every statistic is read under the sensitivity
label; a directory whose scores do not carry that column takes it from the
build's other directories. Every row the plain pooling writes is written
unchanged beside the further ones.

``inputs.json`` holds the sha256 of every file in the score directories read,
of the ``intervals.json`` of any recorded pooling named in their place, and
of the build run's ``cells.csv``.

    python scripts/record_run.py lc-arm-e-intervals -- \\
        python scripts/arm_intervals.py \\
            experiments/2026-09-11-lc-2013h1e-intervals-grid \\
            ... \\
            experiments/2026-09-11-lc-2017h1e-intervals-grid \\
            --check-seeds 20260906,20260907 \\
            --out-dir experiments/2026-09-11-lc-arm-e-intervals
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_intervals as bi
import record_run as rr

from outoftime import metrics as mt

# The statistics pooled over the arm, and how each is read where a reader
# sees it. The first six are means over cells; the last two are slopes.
ARM_METRICS = ("gini", "abs_log_oe", "cox_slope_deviation", "cox_slope", "psi",
               "psi_first_cohort", "auc_slope_build", "auc_slope_cohort")
ARM_TITLE = {**bi.POOLED_TITLE,
             "psi_first_cohort": "PSI vs the build's first scored cohort, difference",
             "auc_slope_build": "AUC slope on age, one intercept per build, per quarter",
             "auc_slope_cohort": "AUC slope on age, one intercept per cohort, per quarter"}
# The statistics that exist on one build: the cohort-intercept slope needs
# a cohort scored at more than one age, which one build never has.
BUILD_METRICS = tuple(m for m in ARM_METRICS if m != "auc_slope_cohort")
ARM = "arm"
# The scope that weights every build alike: the mean over builds of the
# build's own statistic, beside the arm's mean over cells.
BUILDS = "builds"
# The label regimes pooled as scopes of their own when the build run's cells are given, and
# the scoped readings of H2 on the second book (EXP-005, H2): the crisis cells and the 2022
# cells, and per build the ratio of O/E on 2022H2 to 2023H2 over that on 2020H1 and 2021H2.
REGIME_SCOPES = ("pre-flag", "flagged")
H2_SCOPES = {"crisis cells": ("2007H1", "2009H2"), "2022 cells": ("2022H1", "2023H2")}
OE_RATIO = "oe_ratio_2022"
OE_RATIO_COHORTS = ({"2022H2", "2023H1", "2023H2"}, {"2020H1", "2021H2"})
SCORE_COLUMNS = ["build_id", "arm", "model", "context_seed", "cohort", "age_quarters",
                 "row", "outcome", "pd"]
REFERENCE_COLUMNS = ["build_id", "model", "context_seed", "pd"]


def expand_sources(paths: list[Path]) -> list[Path]:
    """The score directories behind the paths named: a recorded pooling stands for its sources."""
    out: list[Path] = []
    for path in paths:
        if (path / "scores.parquet").exists():
            out.append(path)
            continue
        summary = path / "intervals.json"
        if not summary.exists():
            raise SystemExit(f"{path.as_posix()}: neither scores.parquet nor intervals.json")
        sources = json.loads(summary.read_text(encoding="utf-8")).get("sources", [])
        if not sources:
            raise SystemExit(f"{path.as_posix()}: intervals.json names no sources")
        out.extend(Path(s) for s in sources)
    return out


class Arm:
    """Every build's scores of one arm, aligned on the cohorts they share.

    `cohorts` maps a cohort to a `ScoredCohort` whose cells are keyed by
    (build, model) — fixed models in `scores`, seeded ones in `seeds` in the
    shared seed order. `ages` maps (build, cohort) to the model's age in
    quarters on that cell, and is also the record of which build scores
    which cohort. `models` maps a model to its seed list, `[None]` for a
    deterministic one, the same on every build. `outcome` names the score
    file's column read as the outcome: `outcome` for the study's label, or a
    second reading written beside it, such as `outcome_reported`.
    """

    def _second_reading(self, dirs: list[Path], holding: list[Path]) -> pd.DataFrame:
        """A build's scores under a second reading that some of its directories do not carry.

        A foundation model's run on the rented accelerator writes the study's
        label and not the second reading beside it. The label is a property of
        the loan, so a directory without the column takes it from the build's
        directories that hold it, row by row on (cohort, row), and only where
        the study's label agrees on every row it joins; a row the holders do not
        score, or a label that differs, refuses the build.
        """
        wanted = self.outcome_column
        base = [c for c in SCORE_COLUMNS]
        held = pd.concat([pd.read_parquet(d / "scores.parquet", columns=[*base, wanted])
                          for d in holding], ignore_index=True)
        label = held[["cohort", "row", "outcome", wanted]].drop_duplicates()
        if label[["cohort", "row"]].duplicated().any():
            raise SystemExit(f"{holding[0].as_posix()}: a row carries two readings of {wanted}")
        frames = [held.drop(columns="outcome").rename(columns={wanted: "outcome"})]
        for d in dirs:
            if d in holding:
                continue
            own = pd.read_parquet(d / "scores.parquet", columns=base)
            joined = own.merge(label, on=["cohort", "row"], how="left", suffixes=("", "_held"),
                               validate="many_to_one")
            if joined[wanted].isna().any():
                raise SystemExit(f"{d.as_posix()}: rows the build's other directories do not "
                                 f"score, so {wanted} cannot be taken from them")
            if not np.array_equal(joined["outcome"].to_numpy(), joined["outcome_held"].to_numpy()):
                raise SystemExit(f"{d.as_posix()}: the study's label differs from the build's other "
                                 f"directories, so {wanted} cannot be taken from them")
            frames.append(joined.drop(columns=["outcome", "outcome_held"])
                          .rename(columns={wanted: "outcome"})[base])
        return pd.concat([f[base] for f in frames], ignore_index=True)

    def __init__(self, outcome: str = "outcome") -> None:
        self.outcome_column = outcome
        self.arm: str | None = None
        self.builds: list[str] = []
        self.models: dict[str, list[int | None]] = {}
        self.ages: dict[tuple[str, str], int] = {}
        self.outcome: dict[str, np.ndarray] = {}
        self.rows: dict[str, np.ndarray] = {}
        self.fixed: dict[str, dict[tuple[str, str], np.ndarray]] = {}
        self.seeded: dict[str, dict[tuple[str, str], list[np.ndarray]]] = {}
        self.edges: dict[tuple[str, str, int | None], tuple[np.ndarray, int]] = {}
        self.shares: dict[tuple[str, str, int | None], np.ndarray] = {}
        # The second stability reference: the cell's own scores on the
        # build's first scored cohort, decile edges and shares per cell
        # key, held fixed as the training reference is.
        self.first_cohort: dict[str, str] = {}
        self.first_edges: dict[tuple[str, str, int | None], np.ndarray] = {}
        self.first_shares: dict[tuple[str, str, int | None], np.ndarray] = {}
        self.scored_rows = 0
        self.reference_rows = 0

    def add_build(self, dirs: list[Path], drop: list[str]) -> str:
        holding = [d for d in dirs
                   if self.outcome_column in pq.read_schema(d / "scores.parquet").names]
        if not holding:
            raise SystemExit(f"{dirs[0].as_posix()}: no scores.parquet of the build holds a column "
                             f"{self.outcome_column}; outcome_reported is written beside the "
                             "study's label on the Freddie Mac book only")
        columns = [self.outcome_column if c == "outcome" else c for c in SCORE_COLUMNS]
        if len(holding) == len(dirs):
            scores = pd.concat([pd.read_parquet(d / "scores.parquet", columns=columns)
                                for d in dirs], ignore_index=True)
            scores = scores.rename(columns={self.outcome_column: "outcome"})
        else:
            scores = self._second_reading(dirs, holding)
        reference = pd.concat([pd.read_parquet(d / "reference.parquet", columns=REFERENCE_COLUMNS)
                               for d in dirs], ignore_index=True)
        if drop:
            missing = sorted(set(drop) - set(scores["model"].unique()))
            if missing:
                raise SystemExit(f"--drop names models that hold no rows: {', '.join(missing)}")
            scores = scores[~scores["model"].isin(drop)].reset_index(drop=True)
            reference = reference[~reference["model"].isin(drop)].reset_index(drop=True)
            if scores.empty:
                raise SystemExit("--drop leaves no model")
        if scores["build_id"].nunique() != 1 or reference["build_id"].nunique() != 1:
            raise SystemExit("one build per score directory: " + ", ".join(d.as_posix() for d in dirs))
        build = str(scores["build_id"].iloc[0])
        if build in self.builds:
            raise SystemExit(f"{build} is named twice")
        arm = str(scores["arm"].iloc[0])
        if self.arm is None:
            self.arm = arm
        elif arm != self.arm:
            raise SystemExit(f"{build} is on arm {arm}, the others on {self.arm}")
        if scores[["model", "context_seed", "cohort", "row"]].duplicated().any():
            raise SystemExit(f"{build}: the same cell is scored in more than one directory")

        models: dict[str, list[int | None]] = {}
        for model, seed in scores[["model", "context_seed"]].drop_duplicates().itertuples(index=False):
            models.setdefault(model, []).append(None if pd.isna(seed) else int(seed))
        for seeds in models.values():
            seeds.sort(key=lambda s: -1 if s is None else s)
        for model, seeds in models.items():
            if None in seeds and len(seeds) > 1:
                raise SystemExit(f"{build}: {model} is both fixed and seeded")
        if not self.models:
            self.models = models
        elif models != self.models:
            raise SystemExit(f"{build} carries models or seeds the first build does not: "
                             f"{models} against {self.models}")

        self.builds.append(build)
        self.scored_rows += len(scores)
        self.reference_rows += len(reference)
        for cohort, frame in scores.groupby("cohort", sort=True):
            cohort = str(cohort)
            ages = frame["age_quarters"].unique()
            if ages.size != 1:
                raise SystemExit(f"{build} {cohort}: more than one age")
            self.ages[(build, cohort)] = int(ages[0])
            rows: np.ndarray | None = None
            for model, seeds in self.models.items():
                for seed in seeds:
                    mask = (frame["model"] == model) & (
                        frame["context_seed"].isna() if seed is None
                        else frame["context_seed"] == seed)
                    cell = frame[mask].sort_values("row")
                    if cell.empty:
                        raise SystemExit(f"{build} {cohort}: no scores for {bi.cell_key(model, seed)}")
                    if rows is None:
                        rows = cell["row"].to_numpy()
                        outcome = cell["outcome"].to_numpy()
                        if cohort in self.rows:
                            if not np.array_equal(rows, self.rows[cohort]):
                                raise SystemExit(f"{build} {cohort}: different rows from the "
                                                 "builds before it")
                            if not np.array_equal(outcome, self.outcome[cohort]):
                                raise SystemExit(f"{build} {cohort}: different outcomes from the "
                                                 "builds before it")
                        else:
                            self.rows[cohort] = rows
                            self.outcome[cohort] = outcome
                            self.fixed[cohort] = {}
                            self.seeded[cohort] = {}
                    elif not np.array_equal(cell["row"].to_numpy(), rows):
                        raise SystemExit(f"{build} {cohort}: {bi.cell_key(model, seed)} scores "
                                         "different rows")
                    elif not np.array_equal(cell["outcome"].to_numpy(), outcome):
                        raise SystemExit(f"{build} {cohort}: {bi.cell_key(model, seed)} carries "
                                         "a different outcome")
                    values = cell["pd"].to_numpy(dtype=float)
                    if seed is None:
                        self.fixed[cohort][(build, model)] = values
                    else:
                        self.seeded[cohort].setdefault((build, model), []).append(values)
        self.first_reference(build, min(self.cohorts_of(build), key=lambda c: self.ages[(build, c)]))
        for (model, seed), frame in reference.groupby(["model", "context_seed"], dropna=False):
            key = (build, model, None if pd.isna(seed) else int(seed))
            values = frame["pd"].to_numpy(dtype=float)
            cuts = mt.psi_edges(values)
            self.edges[key] = (cuts, values.size)
            counts = np.bincount(np.searchsorted(cuts, values, side="right"), minlength=cuts.size + 1)
            self.shares[key] = counts / values.size
        return build

    def first_reference(self, build: str, first: str) -> None:
        """Makes `first` the build's second stability reference: its decile edges and shares per cell."""
        self.first_cohort[build] = first
        for model, seeds in self.models.items():
            for k, seed in enumerate(seeds):
                values = (self.fixed[first][(build, model)] if seed is None
                          else self.seeded[first][(build, model)][k])
                cuts = mt.psi_edges(values)
                counts = np.bincount(np.searchsorted(cuts, values, side="right"),
                                     minlength=cuts.size + 1)
                self.first_edges[(build, model, seed)] = cuts
                self.first_shares[(build, model, seed)] = counts / values.size

    def cohorts(self) -> dict[str, mt.ScoredCohort]:
        return {cohort: mt.ScoredCohort(self.outcome[cohort], self.fixed[cohort],
                                        self.seeded[cohort])
                for cohort in sorted(self.outcome)}

    def cohorts_of(self, build: str) -> list[str]:
        return sorted(c for (b, c) in self.ages if b == build)

    def cells(self) -> list[tuple[str, str]]:
        return sorted(self.ages)


def floor_cohorts(arm: Arm, path: Path | None) -> tuple[set[str], dict[str, list[str]]]:
    """The cohorts that enter the arm's poolings, and those under the floors with their builds.

    Without the build run's cells.csv (`path` None) every cohort enters, and
    one whose scored rows fall under the floors is refused. With it, a
    cohort the file puts under the floors leaves every pooling; a cohort it
    admits whose scored rows fall under them is refused, and so is a build
    left with no cohort. The second stability reference is the build's first
    scored cohort whatever its floor verdict, since it reads no label
    (EXP-005, note of 2026-09-15).
    """
    scored_by = {c: [b for b in arm.builds if (b, c) in arm.ages] for c in sorted(arm.outcome)}

    def label(cohort: str) -> str:
        return f"{cohort} ({', '.join(scored_by[cohort])})"

    if path is None:
        bi.check_floors({label(c): arm.outcome[c] for c in scored_by}, None)
        return set(scored_by), {}
    verdicts = bi.read_floors(path)
    floor: dict[str, bool] = {}
    for build in arm.builds:
        floor.update(bi.floor_verdicts(verdicts, path, build, arm.cohorts_of(build)))
    keep = {c for c, above in floor.items() if above}
    bi.check_floors({label(c): arm.outcome[c] for c in sorted(keep)}, path)
    empty = [b for b in arm.builds if not keep & set(arm.cohorts_of(b))]
    if empty:
        raise SystemExit(f"{', '.join(empty)}: no cohort above the floors; the build cannot "
                         "enter the pooling")
    return keep, {c: on for c, on in scored_by.items() if c not in keep}


def side_of_one(row) -> str:
    """'>' when an interval lies wholly above one, '<' wholly below, blank when it holds one."""
    return ">" if row.ci_lo > 1.0 else ("<" if row.ci_hi < 1.0 else "")


def cohort_name(key) -> str:
    """The cohort behind a bootstrap key: bare, or (cohort, position) when the cohorts were drawn."""
    return key[0] if isinstance(key, tuple) else key


def slope(age: np.ndarray, value: np.ndarray, group: np.ndarray) -> float:
    """Least-squares slope of value on age with one intercept per group.

    The within-group slope: every cell's age and value are taken from their
    group's means, and the slope is the ratio of the pooled cross-product to
    the pooled sum of squares. A single group is plain least squares. NaN
    when no group holds two distinct ages.
    """
    cross = 0.0
    square = 0.0
    for g in np.unique(group):
        pick = group == g
        a = age[pick] - age[pick].mean()
        cross += float(np.dot(a, value[pick] - value[pick].mean()))
        square += float(np.dot(a, a))
    return cross / square if square > 0 else float("nan")


def arm_statistics(arm: Arm, models: dict[str, list[int | None]],
                   subset: set[tuple[str, str]] | None, per_build: bool,
                   cohort_scopes: dict[str, set[str]] | None = None,
                   oe_ratio: tuple[set[str], set[str]] | None = None):
    """The pooled statistics: per-model values and every paired difference, per scope.

    Returns a callable of the cohorts with the context draw chosen. Each
    cell's metrics are computed once; the arm's statistics and, when asked,
    each build's and the equal-weight mean over builds are assembled from
    them. A seeded cell's PSI reads against the reference of the draw the
    cohort carries; its second PSI reads against the same cell's scores on
    the build's first scored cohort, and the first cohort's own cells enter
    that mean for no build, since they would read zero by construction.

    The two slopes are the same least squares with different intercepts.
    With one per build, only the movement within a build reaches the slope,
    and within a build age and calendar quarter are one axis. With one per
    cohort, only the movement of one cohort across the builds that score it
    reaches the slope: the calendar is held fixed and the model's age
    varies, together with the pool the model was built from.

    With the per-build scopes, `cohort_scopes` names further scopes by the
    cohorts they hold: each is pooled over its cells as the arm is, and over
    the builds that hold any of its cells with every such build weighted alike,
    under `builds, <scope>`. `oe_ratio` gives two sets of cohorts, later and
    earlier: per model and build, observed over expected pooled over the
    build's cells in the later set divided by the same over the earlier set,
    and the mean of that ratio over the builds holding both.
    """
    cohort_scopes = cohort_scopes if per_build and cohort_scopes else {}
    oe_ratio = oe_ratio if per_build else None
    names = [m for m in bi.MODEL_ORDER if m in models] + sorted(set(models) - set(bi.MODEL_ORDER))
    pairs = [(later, earlier) for earlier, later in itertools.combinations(names, 2)]
    scopes = [ARM, BUILDS, *arm.builds] if per_build else [ARM]
    builds = list(arm.builds)
    cell_metrics = ("auc", "abs_log_oe", "cox_slope_deviation", "cox_slope", "psi",
                    "psi_first_cohort")

    def compute(cohorts):
        # Per model: parallel lists over the cells in scope.
        age: dict[str, list[int]] = {m: [] for m in names}
        build_of: dict[str, list[str]] = {m: [] for m in names}
        cohort_of: dict[str, list] = {m: [] for m in names}
        metric: dict[str, dict[str, list[float]]] = {
            m: {k: [] for k in cell_metrics} for m in names}
        # Observed and expected defaults per cell, for the ratio of O/E between two windows.
        sums: dict[str, dict[str, list[float]]] = {m: {"observed": [], "expected": []}
                                                   for m in names}
        for key, cohort in cohorts.items():
            name = cohort_name(key)
            for build in builds:
                if (build, name) not in arm.ages:
                    continue
                if subset is not None and (build, name) not in subset:
                    continue
                first = name == arm.first_cohort[build]
                for model in names:
                    s = cohort.scores[(build, model)]
                    seeds = models[model]
                    ref = (build, model, None if seeds == [None] else seeds[cohort.draw])
                    age[model].append(arm.ages[(build, name)])
                    build_of[model].append(build)
                    cohort_of[model].append(key)
                    metric[model]["auc"].append(mt.auc(cohort.outcome, s))
                    metric[model]["abs_log_oe"].append(bi.abs_log_oe(cohort.outcome, s))
                    deviation, signed = bi.cox_slope_pair(cohort.outcome, s)
                    metric[model]["cox_slope_deviation"].append(deviation)
                    metric[model]["cox_slope"].append(signed)
                    metric[model]["psi"].append(
                        bi.psi_value(s, arm.edges[ref][0], arm.shares[ref]))
                    metric[model]["psi_first_cohort"].append(
                        float("nan") if first
                        else bi.psi_value(s, arm.first_edges[ref], arm.first_shares[ref]))
                    if oe_ratio is not None:
                        sums[model]["observed"].append(float(np.sum(cohort.outcome)))
                        sums[model]["expected"].append(float(np.sum(s)))
        # A cell on which some model's Cox fit did not finish leaves the pairing
        # of the Cox statistic for every model, at every scope, in the point
        # estimate and in every resample alike.
        keep = bi.estimable(metric, names)
        cohort_names = np.asarray([cohort_name(k) for k in cohort_of[names[0]]])
        in_scope = {scope: np.isin(cohort_names, sorted(members))
                    for scope, members in cohort_scopes.items()}

        def pick_of(scope, groups: np.ndarray) -> np.ndarray:
            if scope == ARM:
                return np.ones(groups.size, dtype=bool)
            if isinstance(scope, tuple):
                # (build, cohort scope): that build's cells in the scope.
                return (groups == scope[0]) & in_scope[scope[1]]
            if scope in in_scope:
                return in_scope[scope]
            return groups == scope

        per_scope: dict = {}
        scoped_builds = {name: [b for b in builds
                                if (pick_of((b, name), np.asarray(build_of[names[0]]))).any()]
                         for name in cohort_scopes}
        computed = ([ARM, *builds] if per_build else [ARM]) + list(cohort_scopes) + [
            (b, name) for name in cohort_scopes for b in scoped_builds[name]]
        for scope in computed:
            value: dict[str, dict[str, float]] = {}
            for model in names:
                groups = np.asarray(build_of[model])
                pick = pick_of(scope, groups)
                ages = np.asarray(age[model], dtype=float)[pick]
                aucs = np.asarray(metric[model]["auc"])[pick]
                labels = np.asarray([str(k) for k in cohort_of[model]])[pick]
                value[model] = {
                    "gini": float(np.mean(2.0 * aucs - 1.0)),
                    "abs_log_oe": float(np.mean(np.asarray(metric[model]["abs_log_oe"])[pick])),
                    "cox_slope_deviation": bi.paired_mean(
                        np.asarray(metric[model]["cox_slope_deviation"])[pick], keep[pick]),
                    "cox_slope": bi.paired_mean(
                        np.asarray(metric[model]["cox_slope"])[pick], keep[pick]),
                    "psi": float(np.mean(np.asarray(metric[model]["psi"])[pick])),
                    "psi_first_cohort": float(np.nanmean(
                        np.asarray(metric[model]["psi_first_cohort"])[pick])),
                    "auc_slope_build": slope(ages, aucs, groups[pick]),
                    "auc_slope_cohort": slope(ages, aucs, labels),
                }
            per_scope[scope] = value
        if per_build:
            # A build none of whose cells is estimable reads NaN for every model
            # alike, and leaves the equal-weight mean of a Cox statistic.
            build_estimable = np.array([keep[np.asarray(build_of[names[0]]) == b].any()
                                        for b in builds])
            per_scope[BUILDS] = {
                model: {stat: (bi.paired_mean([per_scope[b][model][stat] for b in builds],
                                              build_estimable)
                               if stat in bi.COX_METRICS
                               else float(np.mean([per_scope[b][model][stat] for b in builds])))
                        for stat in BUILD_METRICS}
                for model in names}
        weighted: dict[str, np.ndarray] = {}
        for name in cohort_scopes:
            members = scoped_builds[name]
            weighted[name] = np.array([keep[pick_of((b, name), np.asarray(build_of[names[0]]))]
                                       .any() for b in members], dtype=bool)
            per_scope[f"{BUILDS}, {name}"] = {
                model: {stat: (bi.paired_mean([per_scope[(b, name)][model][stat] for b in members],
                                              weighted[name])
                               if stat in bi.COX_METRICS
                               else float(np.mean([per_scope[(b, name)][model][stat]
                                                   for b in members])))
                        for stat in BUILD_METRICS}
                for model in names}
        out: dict[str, float] = {}
        extra = [*cohort_scopes, *(f"{BUILDS}, {name}" for name in cohort_scopes)]
        for scope in [*scopes, *extra]:
            value = per_scope[scope]
            for stat in ARM_METRICS if scope == ARM or scope in cohort_scopes else BUILD_METRICS:
                kind = "slope" if stat.startswith("auc_slope") else "mean"
                for model in names:
                    out[f"{stat}|{kind}|{scope}|{model}"] = value[model][stat]
                for later, earlier in pairs:
                    out[f"{stat}|diff|{scope}|{later}|{earlier}"] = (
                        value[later][stat] - value[earlier][stat])
        groups = np.asarray(build_of[names[0]])
        for scope in [ARM, *builds] if per_build else [ARM]:
            pick = np.ones(groups.size, dtype=bool) if scope == ARM else groups == scope
            for stat in bi.COX_METRICS:
                out[f"{bi.LEFT_OUT}|{stat}|{scope}"] = float((~keep[pick]).sum())
        if per_build:
            # At the scope that weights builds alike, what leaves is a build.
            for stat in bi.COX_METRICS:
                out[f"{bi.LEFT_OUT}|{stat}|{BUILDS}"] = float((~build_estimable).sum())
        for name in cohort_scopes:
            for stat in bi.COX_METRICS:
                out[f"{bi.LEFT_OUT}|{stat}|{name}"] = float((~keep[in_scope[name]]).sum())
                out[f"{bi.LEFT_OUT}|{stat}|{BUILDS}, {name}"] = float((~weighted[name]).sum())
        if oe_ratio is not None:
            later, earlier = oe_ratio
            groups = np.asarray(build_of[names[0]])
            in_later, in_earlier = np.isin(cohort_names, sorted(later)), np.isin(
                cohort_names, sorted(earlier))
            held = [b for b in builds
                    if ((groups == b) & in_later).any() and ((groups == b) & in_earlier).any()]
            ratio = {}
            for model in names:
                observed = np.asarray(sums[model]["observed"])
                expected = np.asarray(sums[model]["expected"])
                ratio[model] = {}
                for b in held:
                    late, early = (groups == b) & in_later, (groups == b) & in_earlier
                    ratio[model][b] = float((observed[late].sum() / expected[late].sum())
                                            / (observed[early].sum() / expected[early].sum()))
                if held:
                    ratio[model][BUILDS] = float(np.mean([ratio[model][b] for b in held]))
            for scope in [*held, BUILDS] if held else []:
                for model in names:
                    out[f"{OE_RATIO}|mean|{scope}|{model}"] = ratio[model][scope]
                for later_model, earlier_model in pairs:
                    out[f"{OE_RATIO}|diff|{scope}|{later_model}|{earlier_model}"] = (
                        ratio[later_model][scope] - ratio[earlier_model][scope])
        return out

    return compute


def seed_check(primary: pd.DataFrame, repeats: pd.DataFrame) -> dict:
    """Which differences keep or lose their star when the bootstrap is re-drawn.

    As `build_intervals.seed_check`, with the scope — the arm or one build —
    part of the key, since the same pair is pooled at every scope.
    """
    keys = ["cohorts", "scope", "metric", "pair"]
    diffs = primary[primary["is_difference"]]
    seeds = sorted(int(s) for s in repeats["bootstrap_seed"].unique())
    indexed = repeats.set_index(keys + ["bootstrap_seed"]).sort_index()
    changed: list[dict] = []
    widest = 0.0
    for row in diffs.itertuples():
        same = indexed.loc[(row.cohorts, row.scope, row.metric, row.pair)]
        if len(same) != len(seeds):
            raise SystemExit(f"{row.metric} {row.pair} ({row.cohorts}, {row.scope}) was not "
                             "repeated under every check seed")
        under = {int(s): {"excludes_zero": bool(r.excludes_zero), "ci_lo": float(r.ci_lo),
                          "ci_hi": float(r.ci_hi)} for s, r in same.iterrows()}
        movement = max(max(abs(v["ci_lo"] - row.ci_lo), abs(v["ci_hi"] - row.ci_hi))
                       for v in under.values())
        widest = max(widest, movement)
        if any(v["excludes_zero"] != bool(row.excludes_zero) for v in under.values()):
            changed.append({"cohorts": row.cohorts, "scope": row.scope, "metric": row.metric,
                            "pair": row.pair, "value": float(row.value),
                            "primary": {"excludes_zero": bool(row.excludes_zero),
                                        "ci_lo": float(row.ci_lo), "ci_hi": float(row.ci_hi)},
                            "under": under, "bound_movement": movement})
    starred = int(diffs["excludes_zero"].fillna(False).astype(bool).sum())
    arm_diffs = diffs[diffs["scope"] == ARM]
    return {"seeds": seeds, "differences": len(diffs), "starred": starred,
            "arm_differences": len(arm_diffs),
            "arm_starred": int(arm_diffs["excludes_zero"].fillna(False).astype(bool).sum()),
            "arm_star_changed": sum(c["scope"] == ARM for c in changed),
            "star_changed": changed, "largest_bound_movement": widest}


def plot_differences(paired: pd.DataFrame, out: Path, cells: int, poolings: list[str],
                     disagreeing: set[str], nearest: int, window: str | None = None) -> None:
    """Every arm-level paired difference with its pooled interval, per pooling.

    `window` names the nearest pooling where the floors took cells out of it.
    """
    diffs = paired[paired["is_difference"] & paired["draw"].isna() & (paired["scope"] == ARM)]
    colours = {"all": "#0E6B66", "nearest": "#9A5B24", "all, cohorts resampled": "#4B3F8F"}
    labels_of = {"all": f"every cell of the arm, {cells}",
                 "nearest": window or f"the youngest {nearest} cohorts of every build",
                 "all, cohorts resampled": "every cell, cohorts resampled"}
    pairs = diffs[(diffs["cohorts"] == "all") & (diffs["metric"] == ARM_METRICS[0])]["pair"].tolist()
    height = max(4.2, 1.6 + 0.2 * len(pairs) * max(1, len(poolings)))
    fig, axes = plt.subplots(1, len(ARM_METRICS), figsize=(4.6 * len(ARM_METRICS), height))
    hollow = False
    y = np.arange(len(pairs))
    for ax, metric in zip(axes, ARM_METRICS):
        sub = diffs[diffs["metric"] == metric]
        for offset, which in enumerate(poolings):
            part = sub[sub["cohorts"] == which].set_index("pair").loc[pairs]
            positions = y + (offset - (len(poolings) - 1) / 2) * 0.25
            for row, pos in zip(part.itertuples(), positions):
                disagree = f"{metric}|{row.Index}" in disagreeing
                hollow = hollow or disagree
                # The interval as a segment and the point on its own: a
                # percentile interval need not contain the point estimate.
                ax.plot([row.ci_lo, row.ci_hi], [pos, pos], color=colours[which], linewidth=1.2)
                ax.plot([row.ci_lo, row.ci_lo, None, row.ci_hi, row.ci_hi],
                        [pos - 0.08, pos + 0.08, None, pos - 0.08, pos + 0.08],
                        color=colours[which], linewidth=1.2)
                ax.plot(row.value, pos, marker="o", markersize=4, color=colours[which],
                        markerfacecolor="white" if disagree else colours[which], linestyle="none")
            ax.plot([], [], marker="o", color=colours[which], markersize=4,
                    label=labels_of[which])
        ax.axvline(0.0, color="black", linewidth=0.8, linestyle=":")
        ax.set_yticks(y)
        ax.set_yticklabels(pairs, fontsize=8)
        ax.set_title(ARM_TITLE[metric], fontsize=10)
        ax.grid(alpha=0.3, axis="x")
    handles, labels = axes[0].get_legend_handles_labels()
    if hollow:
        handles.append(plt.Line2D([], [], marker="o", color="black", markerfacecolor="white",
                                  linestyle="none", markersize=4))
        labels.append("hollow: the per-draw intervals do not all overlap")
    fig.legend(handles, labels, loc="lower center", ncol=len(labels), frameon=False, fontsize=9)
    fig.suptitle("paired differences pooled over the arm, one cohort-blocked resample shared "
                 "by every build", fontsize=11)
    fig.tight_layout(rect=(0, min(0.08, 0.34 / height), 1, 0.94))
    fig.savefig(out, dpi=130)
    plt.close(fig)


def plot_auc_age(arm: Arm, cohorts: dict[str, mt.ScoredCohort], paired: pd.DataFrame,
                 out: Path, by: str = "build") -> None:
    """AUC against age on every cell, one panel per model, one line per build or per cohort.

    The first context draw is drawn for a seeded model. With one line per
    build the panel shows what the build-intercept slope is fitted through;
    with one line per cohort, the same cells joined the other way, what the
    cohort-intercept slope is fitted through. The arm's fitted slope of that
    kind is laid through the grand mean of the panel so that its size can be
    read against the spread of the lines.
    """
    names = list(arm.models)
    fig, axes = plt.subplots(1, len(names), figsize=(3.6 * len(names), 4.0), sharey=True)
    axes = np.atleast_1d(axes)
    cmap = plt.get_cmap("viridis")
    statistic = f"auc_slope_{by}"
    slopes = paired[(paired["metric"] == statistic) & ~paired["is_difference"]
                    & (paired["scope"] == ARM) & (paired["cohorts"] == "all")
                    & paired["draw"].isna()].set_index("pair")
    lines = arm.builds if by == "build" else sorted(arm.outcome)
    for ax, model in zip(axes, names):
        ages_all: list[float] = []
        aucs_all: list[float] = []
        for i, line in enumerate(lines):
            cells = ([(line, c) for c in arm.cohorts_of(line)] if by == "build"
                     else [(b, line) for b in arm.builds if (b, line) in arm.ages])
            points = []
            for build, cohort in cells:
                c = cohorts[cohort]
                s = c.scores.get((build, model))
                if s is None:
                    s = c.seeds[(build, model)][0]
                points.append((arm.ages[(build, cohort)], mt.auc(c.outcome, s)))
            points.sort()
            x = [p[0] for p in points]
            y = [p[1] for p in points]
            ages_all.extend(x)
            aucs_all.extend(y)
            ax.plot(x, y, color=cmap(i / max(1, len(lines) - 1)), marker="o", markersize=2.5,
                    linewidth=1.0, label=line)
        if model in slopes.index:
            row = slopes.loc[model]
            gx = np.array([min(ages_all), max(ages_all)], dtype=float)
            mean_age = float(np.mean(ages_all))
            mean_auc = float(np.mean(aucs_all))
            ax.plot(gx, mean_auc + row.value * (gx - mean_age), color="black", linewidth=1.4,
                    linestyle="--", label=f"arm slope, one intercept per {by}")
            ax.set_title(f"{bi.describe(model)}\nslope {row.value:+.5f} "
                         f"[{row.ci_lo:+.5f}, {row.ci_hi:+.5f}] per quarter", fontsize=9)
        else:
            ax.set_title(bi.describe(model), fontsize=9)
        ax.set_xlabel("model age, quarters")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("AUC on the cell, first context draw")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=min(len(labels), 10), frameon=False,
               fontsize=8)
    fig.suptitle(f"AUC against model age on every cell of the arm, one line per {by}",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0.1, 1, 0.94))
    fig.savefig(out, dpi=130)
    plt.close(fig)


def plot_build_rows(arm: Arm, paired: pd.DataFrame, out: Path, focus: list[tuple[str, str]]
                    ) -> None:
    """The per-build rows of the hypotheses' pairs beside the arm's, under the shared resample.

    One panel per (metric, pair) named in `focus`; each build's difference
    with its interval along the x axis, the arm's pooled value and interval
    as a band across the panel.
    """
    rows = paired[paired["is_difference"] & paired["draw"].isna() & (paired["cohorts"] == "all")]
    focus = [(m, p) for m, p in focus if ((rows["metric"] == m) & (rows["pair"] == p)).any()]
    if not focus:
        return
    columns = min(4, len(focus))
    lines = -(-len(focus) // columns)
    fig, axes = plt.subplots(lines, columns, figsize=(4.4 * columns, 3.2 * lines), squeeze=False)
    x = np.arange(len(arm.builds))
    for ax, (metric, pair) in zip(axes.flat, focus):
        sub = rows[(rows["metric"] == metric) & (rows["pair"] == pair)].set_index("scope")
        whole = sub.loc[ARM]
        ax.axhspan(whole.ci_lo, whole.ci_hi, color="#0E6B66", alpha=0.15, linewidth=0)
        ax.axhline(whole.value, color="#0E6B66", linewidth=1.2, label="arm, pooled")
        per = sub.loc[arm.builds]
        ax.vlines(x, per["ci_lo"], per["ci_hi"], color="#9A5B24", linewidth=1.2)
        ax.plot(x, per["value"], marker="o", markersize=4, color="#9A5B24", linestyle="none",
                label="one build")
        ax.axhline(0.0, color="black", linewidth=0.8, linestyle=":")
        ax.set_xticks(x)
        ax.set_xticklabels(arm.builds, rotation=45, ha="right", fontsize=8)
        ax.set_title(f"{ARM_TITLE[metric]}\n{pair}", fontsize=9)
        ax.grid(alpha=0.3, axis="y")
    for ax in list(axes.flat)[len(focus):]:
        ax.set_visible(False)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False, fontsize=9)
    fig.suptitle("the per-build rows of each difference beside the arm's, one shared resample",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(out, dpi=130)
    plt.close(fig)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dirs", type=Path, nargs="+",
                        help="score directories of the arm's builds, or recorded poolings whose "
                             "intervals.json names them")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--drop", default="",
                        help="comma-separated model names to leave out of everything")
    parser.add_argument("--resamples", type=int, default=mt.RESAMPLES)
    parser.add_argument("--seed", type=int, default=bi.BOOTSTRAP_SEED)
    parser.add_argument("--check-seeds", default="",
                        help="comma-separated bootstrap seeds to repeat the poolings under")
    parser.add_argument("--nearest", type=int, default=bi.NEAREST,
                        help="how many of each build's youngest cohorts form the second pooling")
    parser.add_argument("--no-per-draw", action="store_true",
                        help="skip the poolings with each context draw held fixed")
    parser.add_argument("--cells", type=Path, default=None,
                        help="the build run's cells.csv: a cohort it puts under the floors "
                             "leaves every pooling of the arm, and the pre-flag and flagged "
                             "cells are pooled as scopes of their own")
    parser.add_argument("--outcome", default="outcome",
                        help="the score files' column read as the outcome: outcome, the study's "
                             "label, or outcome_reported, the sensitivity reading")
    parser.add_argument("--h2-scopes", action="store_true",
                        help="pool the crisis cells and the 2022 cells as scopes of their own, "
                             "and per build the ratio of O/E on 2022H2 to 2023H2 over 2020H1 "
                             "and 2021H2 (EXP-005, H2)")
    return parser.parse_args(argv)


def regime_of(path: Path) -> dict[str, str]:
    """Each cohort's label regime from the build run's cells.csv; one regime per cohort."""
    table = pd.read_csv(path, usecols=["cohort", "regime"], dtype={"cohort": str, "regime": str})
    regimes = table.drop_duplicates()
    if regimes["cohort"].duplicated().any():
        raise SystemExit(f"{path.as_posix()}: a cohort carries two label regimes")
    return dict(zip(regimes["cohort"], regimes["regime"], strict=True))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    dropped_models = [m for m in args.drop.split(",") if m]

    sources = expand_sources(args.dirs)
    by_build: dict[str, list[Path]] = {}
    derived: dict[str, list[dict]] = {}
    for path in sources:
        head = pd.read_parquet(path / "scores.parquet", columns=["build_id"])
        if head["build_id"].nunique() != 1:
            raise SystemExit(f"{path.as_posix()}: more than one build")
        by_build.setdefault(str(head["build_id"].iloc[0]), []).append(path)
        entry = bi.derivation_of(path)
        if entry is not None:
            derived.setdefault(entry["model"], []).append(
                {"build_id": str(head["build_id"].iloc[0]), **entry})

    arm = Arm(outcome=args.outcome)
    stage = time.time()
    for build, dirs in sorted(by_build.items()):
        arm.add_build(dirs, dropped_models)
    cells = arm.cells()
    print(f"arm                   : {arm.arm}")
    print(f"builds                : {len(arm.builds)}: " + ", ".join(
        f"{b} ({len(arm.cohorts_of(b))})" for b in arm.builds))
    print(f"cells                 : {len(cells)} over {len(arm.outcome)} distinct cohorts")
    print(f"scored rows           : {arm.scored_rows:,} on {sum(v.size for v in arm.outcome.values()):,} "
          "distinct")
    print(f"reference rows        : {arm.reference_rows:,}")
    print("models                : " + ", ".join(
        f"{m} ({len(s)} draw{'s' if len(s) > 1 else ''})" if s != [None] else m
        for m, s in arm.models.items()))
    if dropped_models:
        print(f"models dropped        : {', '.join(dropped_models)}")
    print(f"loaded in             : {time.time() - stage:.0f}s")

    every_cohort = arm.cohorts()
    keep, under = floor_cohorts(arm, args.cells)
    under_reference = [b for b in arm.builds if arm.first_cohort[b] not in keep]
    pooled_cells = [cell for cell in cells if cell[1] in keep]
    if args.cells is not None:
        print(f"floors                : {len(pooled_cells)} of {len(cells)} cells above the floors "
              f"of {bi.FLOOR_ROWS:,} rows and {bi.FLOOR_DEFAULTS} defaults, the verdict of "
              f"{args.cells.as_posix()}")
        for cohort, on in under.items():
            print(f"  {cohort} left out of the pooling: under the floors, on {', '.join(on)}")
        for build in under_reference:
            print(f"  {build}: the second stability reference is {arm.first_cohort[build]}, "
                  "under the floors; its cells are in no pooling")
    cohorts = {c: v for c, v in every_cohort.items() if c in keep}
    nearest = {(b, c) for b in arm.builds for c in arm.cohorts_of(b)[:args.nearest] if c in keep}
    poolings = [("all", None, False, True), ("nearest", nearest, False, True),
                ("all, cohorts resampled", None, True, False)]
    if not nearest:
        poolings = [p for p in poolings if p[0] != "nearest"]
        print(f"nearest {args.nearest} holds no cohort above the floors; that pooling is not read")
    elif len(nearest) == len(pooled_cells):
        poolings = [p for p in poolings if p[0] != "nearest"]
        print(f"nearest {args.nearest} is every cell; that pooling is not repeated")

    cohort_scopes: dict[str, set[str]] = {}
    if args.cells is not None:
        regimes = regime_of(args.cells)
        for regime in REGIME_SCOPES:
            members = {c for c in keep if regimes.get(c) == regime}
            if members:
                cohort_scopes[regime] = members
    oe_ratio = None
    if args.h2_scopes:
        for name, (first, last) in H2_SCOPES.items():
            members = {c for c in keep if first <= c <= last}
            if members:
                cohort_scopes[name] = members
        oe_ratio = OE_RATIO_COHORTS
    for name, members in cohort_scopes.items():
        print(f"scope {name:<16}: {len(members)} cohorts, "
              f"{sum(1 for _, c in pooled_cells if c in members)} cells")
    print(f"outcome read          : {args.outcome}")

    paired_records: list[dict] = []
    left_out: dict[str, dict] = {}

    def record(which: str, draw: int | None, result: dict[str, mt.Bootstrap]) -> None:
        result, counts = bi.left_out_of(result)
        left_out[which if draw is None else f"{which}, draw {draw}"] = counts
        for name, boot in result.items():
            metric, kind, scope, *parts = name.split("|")
            difference = kind == "diff"
            paired_records.append({
                "arm": arm.arm, "cohorts": which, "draw": draw, "scope": scope,
                "metric": metric, "pair": " - ".join(parts) if difference else parts[0],
                "is_difference": difference, **boot.as_dict(),
                "excludes_zero": boot.excludes_zero if difference else None,
                "reads_derived": bi.reads_derived(" - ".join(parts), derived),
            })

    for which, subset, clustered, per_build in poolings:
        stage = time.time()
        result = mt.cohort_blocked_bootstrap_many(
            cohorts, arm_statistics(arm, arm.models, subset, per_build, cohort_scopes, oe_ratio),
            resamples=args.resamples, seed=args.seed, resample_cohorts=clustered)
        record(which, None, result)
        print(f"bootstrap {which:<22}: {args.resamples} resamples in {time.time() - stage:.0f}s",
              flush=True)

    check_seeds = [int(s) for s in args.check_seeds.split(",") if s.strip()]
    if args.seed in check_seeds:
        raise SystemExit(f"--check-seeds repeats the primary seed {args.seed}")
    repeat_records: list[dict] = []
    for check_seed in check_seeds:
        stage = time.time()
        for which, subset, clustered, per_build in poolings:
            result = mt.cohort_blocked_bootstrap_many(
                cohorts, arm_statistics(arm, arm.models, subset, per_build, cohort_scopes,
                                        oe_ratio),
                resamples=args.resamples, seed=check_seed, resample_cohorts=clustered)
            for name, boot in result.items():
                metric, kind, scope, *parts = name.split("|")
                if kind != "diff":
                    continue
                repeat_records.append({
                    "arm": arm.arm, "bootstrap_seed": check_seed, "cohorts": which,
                    "scope": scope, "metric": metric, "pair": " - ".join(parts),
                    **boot.as_dict(), "excludes_zero": boot.excludes_zero})
        print(f"bootstrap seed {check_seed:<17}: every pooling again in {time.time() - stage:.0f}s",
              flush=True)

    draw_count = next(iter(cohorts.values())).draws
    common = sorted(set.intersection(*(set(s) for s in arm.models.values() if s != [None]))) \
        if draw_count > 1 and not args.no_per_draw else []
    for k, seed_value in enumerate(common):
        stage = time.time()
        fixed = {key: c.realise(k) for key, c in cohorts.items()}
        models_k = {m: ([None] if s == [None] else [s[k]]) for m, s in arm.models.items()}
        result = mt.cohort_blocked_bootstrap_many(
            fixed, arm_statistics(arm, models_k, None, False),
            resamples=args.resamples, seed=args.seed)
        record("all", seed_value, result)
        print(f"draw {seed_value} held fixed   : {args.resamples} resamples in {time.time() - stage:.0f}s",
              flush=True)

    paired = pd.DataFrame(paired_records)
    paired["draw"] = paired["draw"].astype("Int64")
    paired.to_csv(args.out_dir / "paired.csv", index=False)

    disagreeing: dict[str, list[dict]] = {}
    if common:
        per_draw = paired[paired["draw"].notna() & paired["is_difference"]]
        for (metric, pair), rows in per_draw.groupby(["metric", "pair"]):
            spans = list(zip(rows["draw"], rows["ci_lo"], rows["ci_hi"]))
            disjoint = any(a_hi < b_lo or b_hi < a_lo
                           for i, (_, a_lo, a_hi) in enumerate(spans)
                           for (_, b_lo, b_hi) in spans[i + 1:])
            if disjoint:
                disagreeing[f"{metric}|{pair}"] = [
                    {"draw": int(d), "ci_lo": float(lo), "ci_hi": float(hi)} for d, lo, hi in spans]

    checked: dict | None = None
    seed_sensitive: set[tuple[str, str, str, str]] = set()
    if repeat_records:
        repeats = pd.DataFrame(repeat_records)
        primary = paired[paired["draw"].isna() & paired["is_difference"]]
        checked = seed_check(primary, repeats)
        seed_sensitive = {(c["cohorts"], c["scope"], c["metric"], c["pair"])
                          for c in checked["star_changed"]}
        pd.concat([primary.assign(bootstrap_seed=args.seed)[repeats.columns], repeats],
                  ignore_index=True).to_csv(args.out_dir / "paired-seeds.csv", index=False)

    print(f"\npaired differences over the {len(pooled_cells)} cells of arm {arm.arm} (value [lo, hi], "
          "* excludes zero, ! draws disagree"
          + (", ? star changes with the bootstrap seed" if checked else "")
          + (", ~ reads derived rows, their error below" if derived else "") + "):")
    whole = paired[(paired["cohorts"] == "all") & paired["is_difference"] & paired["draw"].isna()
                   & (paired["scope"] == ARM)]
    for row in whole.itertuples():
        flag = "*" if row.excludes_zero else " "
        flag += "!" if f"{row.metric}|{row.pair}" in disagreeing else " "
        flag += "?" if ("all", ARM, row.metric, row.pair) in seed_sensitive else " "
        flag += "~" if bi.reads_derived(row.pair, derived) else ""
        digits = 5 if row.metric.startswith("auc_slope") else 4
        print(f"  {row.metric:<19} {row.pair:<22} {row.value:+.{digits}f} "
              f"[{row.ci_lo:+.{digits}f}, {row.ci_hi:+.{digits}f}] {flag}")
    for name, spans in disagreeing.items():
        print(f"  {name}: draw intervals " + "; ".join(
            f"{s['draw']} [{s['ci_lo']:+.4f}, {s['ci_hi']:+.4f}]" for s in spans))
    for which, counts in left_out.items():
        for key, count in counts.items():
            metric, _, scope = key.partition("|")
            over = "" if ", draw " in which else ", averaged over the context draws"
            if scope == ARM:
                print(f"  {metric} ({which}): {count['point']:g} cells not estimable left out of "
                      f"the arm's point estimate{over}, at most "
                      f"{count['largest_in_a_resample']:g} of any resample")
            elif scope == BUILDS:
                print(f"  {metric} ({which}): {count['point']:g} builds with no estimable cell "
                      f"left out of the mean over builds{over}, at most "
                      f"{count['largest_in_a_resample']:g} of any resample")
    for model, entries in derived.items():
        for entry in entries:
            label = f"{model} on {entry['build_id']}"
            print(f"  ~ {bi.derivation_text(entry, label)}")
    slopes = paired[paired["metric"].str.startswith("auc_slope") & ~paired["is_difference"]
                    & paired["draw"].isna() & (paired["cohorts"] == "all")]
    print("\nAUC slope on age per quarter, one intercept per build: the arm, the mean over "
          "builds, and each build (value [lo, hi]):")
    for model in arm.models:
        sub = slopes[(slopes["pair"] == model)
                     & (slopes["metric"] == "auc_slope_build")].set_index("scope")
        whole_row, equal = sub.loc[ARM], sub.loc[BUILDS]
        print(f"  {model:<11} arm {whole_row.value:+.5f} [{whole_row.ci_lo:+.5f}, "
              f"{whole_row.ci_hi:+.5f}]  builds alike {equal.value:+.5f} [{equal.ci_lo:+.5f}, "
              f"{equal.ci_hi:+.5f}]  each " + " ".join(
                  f"{sub.loc[b].value:+.5f}" for b in arm.builds))
    print("\nAUC slope on age per quarter, one intercept per cohort, the arm (value [lo, hi]):")
    for model in arm.models:
        row = slopes[(slopes["pair"] == model) & (slopes["metric"] == "auc_slope_cohort")
                     & (slopes["scope"] == ARM)].iloc[0]
        print(f"  {model:<11} arm {row.value:+.5f} [{row.ci_lo:+.5f}, {row.ci_hi:+.5f}]")
    signed = paired[(paired["metric"] == "cox_slope") & ~paired["is_difference"]
                    & paired["draw"].isna() & (paired["cohorts"] == "all")]
    print("\nsigned Cox slope, each model's mean over the estimable cells, the arm and the mean "
          "over builds (value [lo, hi], > or < one beyond the interval):")
    for model in arm.models:
        sub = signed[signed["pair"] == model].set_index("scope")
        print(f"  {model:<11} " + "  ".join(
            f"{label} {sub.loc[scope].value:.4f} [{sub.loc[scope].ci_lo:.4f}, "
            f"{sub.loc[scope].ci_hi:.4f}]{side_of_one(sub.loc[scope])}"
            for scope, label in ((ARM, "arm"), (BUILDS, "builds alike")) if scope in sub.index))
    if cohort_scopes or oe_ratio is not None:
        tfm_models = [m for m in arm.models if bi.base_model(m) in ("tabpfn", "tabicl")]
        shown = [("auc_slope_build", "gbm-50k"), ("cox_slope_deviation", "scorecard"),
                 ("psi", "gbm-50k")]
        extra_scopes = [*cohort_scopes, *(f"{BUILDS}, {n}" for n in cohort_scopes)]
        rows = paired[(paired["cohorts"] == "all") & paired["is_difference"] & paired["draw"].isna()]
        print(f"\nthe criterion pairs under the further scopes, outcome {args.outcome} "
              "(value [lo, hi], * excludes zero; none a criterion):")
        for scope in extra_scopes:
            for metric, against in shown:
                for model in tfm_models:
                    hit = rows[(rows["scope"] == scope) & (rows["metric"] == metric)
                               & (rows["pair"] == f"{model} - {against}")]
                    for row in hit.itertuples():
                        digits = 5 if metric.startswith("auc_slope") else 4
                        print(f"  {scope:<22} {metric:<19} {row.pair:<22} {row.value:+.{digits}f} "
                              f"[{row.ci_lo:+.{digits}f}, {row.ci_hi:+.{digits}f}] "
                              f"{'*' if row.excludes_zero else ''}")
        ratios = paired[(paired["cohorts"] == "all") & (paired["metric"] == OE_RATIO)
                        & ~paired["is_difference"] & paired["draw"].isna()]
        if len(ratios):
            print(f"\n{OE_RATIO}: O/E on {', '.join(sorted(oe_ratio[0]))} over O/E on "
                  f"{', '.join(sorted(oe_ratio[1]))}, per model, each build and the mean over builds:")
            for model in arm.models:
                sub = ratios[ratios["pair"] == model].set_index("scope")
                print(f"  {model:<11} " + "  ".join(
                    f"{scope} {sub.loc[scope].value:.3f} [{sub.loc[scope].ci_lo:.3f}, "
                    f"{sub.loc[scope].ci_hi:.3f}]" for scope in sub.index))
    if checked:
        print(f"\nbootstrap seed check over seeds {', '.join(map(str, checked['seeds']))}: "
              f"{checked['arm_starred']} of {checked['arm_differences']} arm differences "
              f"starred under seed {args.seed}, {checked['arm_star_changed']} change their star; "
              f"{checked['starred']} of {checked['differences']} at every scope, "
              f"{len(checked['star_changed'])} change; largest movement of an interval bound "
              f"{checked['largest_bound_movement']:.4f}")
        for change in checked["star_changed"]:
            print(f"  {change['metric']:<19} {change['pair']:<22} ({change['cohorts']}, "
                  f"{change['scope']}) {change['value']:+.4f} " + "; ".join(
                      f"{s} [{v['ci_lo']:+.4f}, {v['ci_hi']:+.4f}]{'*' if v['excludes_zero'] else ''}"
                      for s, v in ((args.seed, change["primary"]), *change["under"].items())))
    if not common:
        print("  no per-draw rows: every interval above mixes the context draws"
              if not args.no_per_draw else "  per-draw rows skipped")

    which_poolings = [p[0] for p in poolings]
    window = (None if args.cells is None else
              f"the youngest {args.nearest} cohorts of every build less those under the floors, "
              f"{len(nearest)} cells")
    plot_differences(paired, args.out_dir / "arm-differences.png", len(pooled_cells),
                     which_poolings, set(disagreeing), args.nearest, window)
    plot_auc_age(arm, every_cohort, paired, args.out_dir / "auc-age.png", by="build")
    plot_auc_age(arm, every_cohort, paired, args.out_dir / "auc-age-cohort.png", by="cohort")
    tfms = [m for m in arm.models if bi.base_model(m) in ("tabpfn", "tabicl")]
    focus = [(metric, f"{m} - {against}") for metric, against in (
        ("auc_slope_build", "gbm-50k"), ("cox_slope_deviation", "scorecard"),
        ("psi", "gbm-50k"), ("psi_first_cohort", "gbm-50k")) for m in tfms]
    plot_build_rows(arm, paired, args.out_dir / "build-rows.png", focus)

    summary = {
        "arm": arm.arm,
        "builds": {b: arm.cohorts_of(b) for b in arm.builds},
        "cells": len(cells),
        **({} if args.cells is None else {"floors": {
            "record": args.cells.as_posix(), "rows": bi.FLOOR_ROWS,
            "defaults": bi.FLOOR_DEFAULTS, "cells_above": len(pooled_cells), "cells": len(cells),
            "reading": f"{len(pooled_cells)} of {len(cells)} cells above the floors",
            "under": under,
            "first_cohort_under_floors": under_reference,
            "rule": "a cohort under the floors leaves every pooling and the resample; the "
                    "nearest pooling is each build's youngest cohorts less those under the "
                    "floors; the second PSI's reference is the first scored cohort on every "
                    "build, named under psi.first_cohort, whatever that cohort's floor verdict, "
                    "since the reference reads no label; first_cohort_under_floors names the "
                    "builds whose reference is under the floors"}}),
        "outcome": args.outcome,
        "cohort_scopes": {name: sorted(members) for name, members in cohort_scopes.items()},
        "oe_ratio": (None if oe_ratio is None else
                     {"metric": OE_RATIO, "later": sorted(oe_ratio[0]),
                      "earlier": sorted(oe_ratio[1]),
                      "reading": "per model and build, observed over expected pooled over the "
                                 "build's later cells divided by the same over its earlier "
                                 "cells; 'builds' is the mean over the builds holding both"}),
        "distinct_cohorts": len(arm.outcome),
        "rows_scored": arm.scored_rows,
        "rows_distinct": int(sum(v.size for v in arm.outcome.values())),
        "models": {m: ([] if s == [None] else s) for m, s in arm.models.items()},
        "models_dropped": dropped_models,
        "sources": [d.as_posix() for d in sources],
        "derived_rows": derived,
        "nearest": args.nearest,
        "bootstrap": {
            "resamples": args.resamples, "seed": args.seed, "alpha": mt.ALPHA,
            "blocking": "cohort, one index per cohort shared by every build that scores it",
            "context_draw": ("drawn with the resample, jointly across models and builds"
                             if draw_count > 1 else "one draw; every interval is conditional on it"),
            "poolings": which_poolings,
            "scopes": "'arm' is the mean over every cell in the pooling; 'builds' is the mean "
                      "over builds of each build's own statistic, every build weighted alike; "
                      "a build's name is that build alone. The 'builds' rows and the per-build "
                      "rows exist under the 'all' and 'nearest' poolings; with the cohorts "
                      "resampled a build can hold fewer than two ages and only 'arm' is "
                      "reported",
            "pooled_metrics": list(ARM_METRICS),
            "per_draw": ("the 'all' pooling repeated with each context draw held fixed, in the "
                         "rows whose draw is set" if common else None),
            "draws_disagree": disagreeing if common else None,
            "seed_check": checked,
            "cox_left_out": left_out,
            "cox_rule": "a cell on which some model's Cox fit did not finish is not estimable "
                        "and leaves the pairing of every Cox statistic for every model, at every "
                        "scope, in the point estimate and in every resample; cox_left_out counts "
                        "it per pooling and scope, as the count on the unresampled cells and "
                        "the largest in any resample",
            "multiplicity": "none: every interval is reported at alpha on its own"},
        "statistics": {
            "gini, abs_log_oe, cox_slope_deviation, psi, psi_first_cohort": "the mean over the "
                "cells in scope, paired by cell; a build with more cohorts contributes more "
                "cells at the arm's scope",
            "cox_slope": "the signed Cox slope, pooled as cox_slope_deviation is and over the "
                         "same estimable cells; its mean rows read against one, its differences "
                         "against zero",
            "psi_first_cohort": ("PSI of the cell against the same model's scores on the build's "
                                 "first scored cohort, ten bins fixed at that cohort's deciles; "
                                 "the first cohort's own cells are left out of the mean, since "
                                 "they would read zero by construction")
                                + ("" if args.cells is None else
                                   "; the reference is that cohort whatever its floor verdict, "
                                   "since it reads no label"),
            "auc_slope_build": "least-squares slope of the cell's AUC on its age in quarters "
                               "with one intercept per build; at the arm's scope the "
                               "within-build movements are pooled with each build weighted by "
                               "the spread of its ages, at a build's scope it is that build's "
                               "own slope. Within a build age and calendar quarter are one "
                               "axis, so this is the calendar slope net of build",
            "auc_slope_cohort": "the same least squares with one intercept per cohort: the "
                                "movement of one cohort's AUC across the builds that score it, "
                                "calendar held fixed, the model's age varying with the pool it "
                                "was built from; each cohort weighted by the spread of the ages "
                                "it is scored at, so the youngest cohorts, scored by the most "
                                "builds, weigh most. Undefined on one build",
            "difference": "later model minus earlier in the order scorecard, gbm, gbm-50k, "
                          "tabpfn, tabicl, then the tagged settings"},
        "psi": {"bins": mt.PSI_BINS, "edges": "the cell's own reference deciles",
                "reference": "the build's training rows for a fitted model, the context draw "
                             "for a seeded one",
                "first_cohort": {b: arm.first_cohort[b] for b in arm.builds}},
        "wall_seconds": round(time.time() - started, 1),
    }
    # The run's manifest pins the paths named on its command line; a recorded pooling named
    # there stands for score directories it does not hold, and the score files read sit
    # inside those directories, so each is hashed here.
    inputs = [*sources, *(d / "intervals.json" for d in args.dirs
                          if not (d / "scores.parquet").exists()),
              *(p for p in (args.cells,) if p is not None)]
    hashed = {}
    for path in inputs:
        for item in sorted(path.rglob("*") if path.is_dir() else [path]):
            if item.is_file():
                hashed[item.as_posix()] = rr.file_hash(item)
    (args.out_dir / "inputs.json").write_text(json.dumps(hashed, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "intervals.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nwall                  : {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
