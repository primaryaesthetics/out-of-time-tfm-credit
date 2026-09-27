#!/usr/bin/env python3
"""Puts an interval on every number of one build, from its recorded scores.

Reads the row-level scores that `score_build.py` writes and produces the
study's metric table for that build: one row per (model, context seed,
cohort, metric) with the value and its interval, in the long format every
later run appends to. Three kinds of interval appear, and they answer
different questions.

The per-cell intervals — DeLong on the AUC, the binomial interval on observed
over expected — say how far one cell's number could move under its own
sampling. They are the intervals a reader expects beside a number and they
are not the ones a comparison is read against.

Calibration is read three ways per cell, because they disagree on purpose.
Observed over expected is the level. The Cox intercept and slope separate a
constant shift of every probability from a stretch or compression of the
scale, and the slope is the statistic the experiment's second hypothesis is
written on. The Brier score is given with its CORP decomposition, since at a
two-percent default rate the scalar is almost all uncertainty and two models
a factor of two apart in the large differ in its fourth decimal. The
reliability curve of every model on the youngest and the oldest pooled
cohort shows the shape the three numbers summarise.

The population stability index of each cell is read against the critical
value of Yurdakul's null at the cell's own sample sizes. At twenty thousand
scored rows the value is of the order of a thousandth, and a PSI above it
says the movement is real, not that it is large.

The paired differences are read against the cohort-blocked bootstrap of the
metrics module: the rows of every cohort are resampled once per draw and the
same resample reaches every model, so the interval of a difference between
two models is the interval of that difference and not of two numbers. Where
the control carries context seeds, the seed is drawn with the resample. Each
difference is pooled over every cohort the build scores and, separately, over
the three cohorts nearest the build date, which is the subset the cheapest
foundation-model run will score. A difference whose interval holds zero is
not a difference.

The bootstrap is two hundred resamples under one seed, and a difference near
the edge of its interval can gain or lose the star on the seed alone. With
`--check-seeds` every pooling is repeated under each seed named, apart from
the primary rows; `paired-seeds.csv` holds the differences under every seed,
the summary names each difference whose star changes, and the console marks
it. A star that does not survive the seed is not cited.

Whatever models the score files hold are compared, every pair of them, so a
foundation model scored later on the same rows enters this table by naming
its directory beside the classical one. The per-cell table then covers every
cell of every directory; the bootstrap pools over the cohorts every cell
scored, and names the cohorts it left out.

A book whose cohorts can be small or poor in defaults carries floors: a cell
enters a pooling only if its cohort holds at least 5,000 labelled loans and
100 defaults under the primary label (EXP-005, Floors). The verdict on each
cell is the build run's, read per build and cohort from its `cells.csv`
under `--cells`. A cohort under the floors stays in the per-cell table with
its interval, marked in a `floor` column, and leaves every pooling; the
nearest pooling is then the youngest cohorts less those under the floors.
The file is held against the scored rows one way: a cohort it admits whose
scored rows fall under the floors is refused. Without `--cells`, a pooling
whose scored rows fall under the floors on any cohort is refused, since it
would pool those cells with no verdict on them.

    python scripts/record_run.py lc-2015h1e-intervals -- \\
        python scripts/build_intervals.py experiments/2026-09-05-lc-2015h1e-scores \\
            experiments/2026-09-06-lc-2015h1e-tfm \\
            --out-dir experiments/2026-09-06-lc-2015h1e-intervals
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from derive_temperature import LENDING_CLUB_FIGURE

from outoftime import metrics as mt

# The order models are listed and paired in; a pair is (later, earlier), so
# a positive difference favours the model further down this list.
MODEL_ORDER = ("scorecard", "gbm", "gbm-50k", "tabpfn", "tabicl")
MODEL_COLOUR = {
    "scorecard": "#0E6B66", "gbm": "#9A5B24", "gbm-50k": "#C9A227",
    "tabpfn": "#4B3F8F", "tabicl": "#B23A48",
}
NEAREST = 3
BOOTSTRAP_SEED = 20260905
# How a tag in a model's name reads where a reader sees it. A model scored
# off its library defaults is written as name@tag+tag by score_context.py.
TAG_TEXT = {"bal": "balanced"}
# The floors of EXP-005's Floors paragraph, those of EXP-001 and EXP-003: a
# cell enters a pooling only if its cohort holds at least this many labelled
# loans and this many defaults under the primary label. The verdict on each
# cell is the build run's, in its cells.csv; the scored rows are held against
# it one way only, since a sampled book scores fewer rows than its cohorts hold.
FLOOR_ROWS = 5_000
FLOOR_DEFAULTS = 100


def under_floors(outcome) -> bool:
    """Whether scored rows hold fewer rows or fewer defaults than the floors."""
    y = np.asarray(outcome)
    return y.size < FLOOR_ROWS or int(y.sum()) < FLOOR_DEFAULTS


def floors_text(outcome) -> str:
    y = np.asarray(outcome)
    return (f"{y.size:,} rows and {int(y.sum()):,} defaults, under the floors of "
            f"{FLOOR_ROWS:,} rows and {FLOOR_DEFAULTS:,} defaults")


def read_floors(path: Path) -> dict[tuple[str, str], bool]:
    """The build run's floor verdict on every (build, cohort) its cells.csv holds.

    The verdict is a property of the cohort, so a cohort the file reads both
    ways, on one build or across builds, is refused.
    """
    table = pd.read_csv(path, usecols=["build_id", "cohort", "floor"],
                        dtype={"build_id": str, "cohort": str})
    verdict = table["floor"].map({True: True, False: False, "True": True, "False": False})
    if verdict.isna().any():
        raise SystemExit(f"{path.as_posix()}: a floor verdict that is neither True nor False")
    table["floor"] = verdict.astype(bool)
    verdicts = table.groupby("cohort")["floor"].nunique()
    both = sorted(verdicts[verdicts > 1].index)
    if both:
        raise SystemExit(f"{path.as_posix()}: {', '.join(both)} carries two floor verdicts")
    return {(b, c): bool(f) for b, c, f in
            table[["build_id", "cohort", "floor"]].itertuples(index=False)}


def floor_verdicts(verdicts: dict[tuple[str, str], bool], path: Path, build: str,
                   cohorts) -> dict[str, bool]:
    """The verdict on each cohort a build scored; a cohort the file does not hold is refused."""
    missing = [c for c in cohorts if (build, c) not in verdicts]
    if missing:
        raise SystemExit(f"{path.as_posix()} holds no row for {build} {', '.join(missing)}")
    return {c: verdicts[(build, c)] for c in cohorts}


def check_floors(outcomes: dict[str, np.ndarray], path: Path | None) -> None:
    """Refuses scored rows under the floors that a pooling would read.

    `outcomes` maps a label naming the cells to the outcome on their scored
    rows. Without the build run's verdict (`path` None) every one of them
    has to clear the floors; with it, `outcomes` holds the cohorts the file
    admits, and each of those has to.
    """
    for label, outcome in outcomes.items():
        if not under_floors(outcome):
            continue
        if path is None:
            raise SystemExit(f"{label}: the scored rows hold {floors_text(outcome)}; name the "
                             "build run's cells.csv with --cells, so that a cell under the "
                             "floors leaves the pooling")
        raise SystemExit(f"{path.as_posix()} admits {label}, whose scored rows hold "
                         f"{floors_text(outcome)}")


def base_model(model: str) -> str:
    """The library model a tagged name was scored with: tabicl@t1 is tabicl."""
    return model.split("@", 1)[0]


def describe(model: str) -> str:
    """A model's name with its tags spelt out, so a figure states the setting."""
    name, _, tags = model.partition("@")
    parts = []
    for tag in tags.split("+") if tags else []:
        if tag.startswith("t") and tag[1:].replace(".", "", 1).isdigit():
            parts.append(f"softmax temperature {tag[1:]}")
        else:
            parts.append(TAG_TEXT.get(tag, tag))
    return ", ".join([name, *parts])


def model_colour(model: str) -> str:
    return MODEL_COLOUR.get(base_model(model), "#555555")


def model_style(model: str) -> str:
    """Solid at the library defaults, dashed off them; the colour is the model's."""
    return "-" if "@" not in model else "--"


def drop_models(scores: pd.DataFrame, reference: pd.DataFrame, names: list[str]
                ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The rows without the models named, which then enter no table, pooling or figure."""
    missing = sorted(set(names) - set(scores["model"].unique()))
    if missing:
        raise SystemExit(f"--drop names models that hold no rows: {', '.join(missing)}")
    keep = ~scores["model"].isin(names)
    keep_ref = ~reference["model"].isin(names)
    return scores[keep].reset_index(drop=True), reference[keep_ref].reset_index(drop=True)


def abs_log_oe(outcome, score) -> float:
    """How far calibration-in-the-large is from one, either side counted alike."""
    return abs(mt.log_oe(outcome, score))


def cox_slope_deviation(outcome, score) -> float:
    """How far the Cox slope is from one, either side counted alike; NaN where the fit did not finish."""
    fit = mt.cox(outcome, score)
    return abs(fit.slope - 1.0) if fit.converged else float("nan")


def cox_slope_pair(outcome, score) -> tuple[float, float]:
    """|Cox slope − 1| and the signed slope from one fit; both NaN where the fit did not finish."""
    fit = mt.cox(outcome, score)
    if not fit.converged:
        return float("nan"), float("nan")
    return abs(fit.slope - 1.0), fit.slope


# The statistics the bootstrap pools, in the order they are reported and drawn.
# The signed slope reads the direction |slope − 1| folds away: above one is a
# logit less spread than the outcomes warrant, below one a logit more spread.
POOLED_METRICS = ("gini", "abs_log_oe", "cox_slope_deviation", "cox_slope", "psi")
POOLED_TITLE = {"gini": "Gini difference", "abs_log_oe": "|log O/E| difference",
                "cox_slope_deviation": "|Cox slope − 1| difference",
                "cox_slope": "Cox slope difference", "psi": "PSI difference"}
# How many rows the per-cell table holds for one cell.
CELL_METRICS = 13
# The pooled statistics read from a Cox fit. A cell on which some model's fit
# did not finish is not estimable, and it leaves the pairing of these
# statistics for every model, in the point estimate and in every resample
# alike, so that the models are compared on the same cells.
COX_METRICS = ("cox_slope_deviation", "cox_slope")
# The prefix of the counts a pooling returns beside its statistics: how many
# cells a Cox statistic left out.
LEFT_OUT = "left_out"


def estimable(per_model: dict[str, dict[str, list[float]]], names: list[str]) -> np.ndarray:
    """Which cells every model's Cox fit finished on: the cells a Cox statistic pairs over."""
    values = np.array([per_model[m]["cox_slope_deviation"] for m in names], dtype=float)
    return np.isfinite(values).all(axis=0)


def paired_mean(values, keep: np.ndarray) -> float:
    """The mean over the cells kept; NaN only when no cell is."""
    kept = np.asarray(values)[keep]
    return float(np.mean(kept)) if kept.size else float("nan")


def left_out_of(result: dict[str, mt.Bootstrap]) -> tuple[dict[str, mt.Bootstrap], dict[str, dict]]:
    """The pooled statistics, and apart from them how many cells each Cox statistic left out.

    ``point`` is the count on the unresampled cells, averaged over the context
    draws as the point estimate is; ``largest_in_a_resample`` is the most any
    one resample left out.
    """
    statistics, counts = {}, {}
    for name, boot in result.items():
        if name.startswith(LEFT_OUT + "|"):
            counts[name.split("|", 1)[1]] = {"point": boot.value,
                                             "largest_in_a_resample": float(max(boot.draws))}
        else:
            statistics[name] = boot
    return statistics, counts


# |b - 1| as the Lending Club grid measured it for an approximate derivation,
# the figure derive_temperature.py counts against; a statistic read from
# derived rows is printed with the count of checked cells above it.
DERIVATION_FIGURE = LENDING_CLUB_FIGURE


def gap_extremes(cells: list[dict], key: str) -> dict | None:
    """The worst (largest in size, with its sign) and the mean of a derived-minus-scored gap."""
    values = np.array([c.get(key, np.nan) for c in cells], dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return None
    return {"worst": float(finite[np.argmax(np.abs(finite))]), "mean": float(finite.mean())}


def derivation_of(directory: Path) -> dict | None:
    """What a derived directory's derive.json says of the error its rows carry; None if scored.

    Read from the check's per-cell records, so that a derive.json written
    before its summaries existed reads alike. An approximate derivation
    carries the worst and mean |b − 1| over the checked cells, the count
    above the Lending Club figure, and the worst and mean derived-minus-
    scored gap in Cox slope and in observed over expected; an exact one the
    largest gap on the probability over the rows checked.
    """
    path = directory / "derive.json"
    if not path.is_file():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    check = record.get("check", {})
    cells = check.get("cells", [])
    builds = sorted({str(c["build_id"]) for c in cells if "build_id" in c})
    entry = {"directory": directory.as_posix(), "model": record["derived_as"],
             "checked_build": (record.get("checked_build") or check.get("checked_build")
                               or builds or None),
             "cells_checked": len(cells)}
    if record.get("approximate"):
        gaps = np.array([c["logit_slope_gap"] for c in cells], dtype=float)
        entry.update({"kind": "approximate",
                      "worst_cell_error": float(gaps.max()), "mean_cell_error": float(gaps.mean()),
                      "cells_above_figure": int((gaps > DERIVATION_FIGURE).sum()),
                      "figure": DERIVATION_FIGURE,
                      "cox_slope_gap": gap_extremes(cells, "cox_slope_gap"),
                      "oe_gap": gap_extremes(cells, "oe_gap")})
    else:
        entry.update({"kind": "exact", "max_abs_pd_gap": float(check["max_abs_pd_gap"]),
                      "rows_checked": int(check["rows_checked"]),
                      "unchecked_cells": len(check.get("unchecked_cells", []))})
    return entry


def derivation_text(entry: dict, label: str | None = None) -> str:
    """One line on the error a derived model's rows carry, printed beside its statistics."""
    head = f"{label or entry['model']}: "
    where = (f"build {', '.join(entry['checked_build'])}" if entry["checked_build"]
             else "the build's own cells")
    if entry["kind"] == "exact":
        return (head + f"derived exactly, {entry['rows_checked']:,} rows checked on {where}, "
                f"largest |d pd| {entry['max_abs_pd_gap']:.1e}; {entry['unchecked_cells']} "
                "cells unchecked by row")

    def gap(name: str) -> str:
        found = entry[name]
        return "n/a" if found is None else f"worst {found['worst']:+.2e}, mean {found['mean']:+.2e}"

    return (head + f"derived approximately, checked on {where}: |b - 1| worst "
            f"{entry['worst_cell_error']:.2e}, mean {entry['mean_cell_error']:.2e}, "
            f"{entry['cells_above_figure']} of {entry['cells_checked']} cells above "
            f"{entry['figure']:g}; Cox slope derived - scored {gap('cox_slope_gap')}; O/E derived "
            f"- scored {gap('oe_gap')}")


def reads_derived(pair: str, derived) -> bool:
    return bool(set(pair.split(" - ")) & set(derived))


def cell_key(model: str, seed) -> str:
    return model if pd.isna(seed) else f"{model}/{int(seed)}"


def shared_cohorts(scores: pd.DataFrame) -> tuple[list[str], dict[str, list[str]]]:
    """The cohorts every cell scored, and the ones some cell did not.

    The classical models score every cohort of a build and a foundation model
    run may score the youngest few, so the bootstrap pools over the cohorts
    all of them hold. What was left out is returned by name, with the cells
    that lack it, so that the pooling is stated and not silent.
    """
    held: dict[str, set[str]] = {}
    for (model, seed, cohort) in scores[["model", "context_seed", "cohort"]].drop_duplicates(
            ).itertuples(index=False):
        held.setdefault(cell_key(model, seed), set()).add(str(cohort))
    every = set.union(*held.values())
    shared = set.intersection(*held.values())
    dropped = {cohort: sorted(k for k, s in held.items() if cohort not in s)
               for cohort in sorted(every - shared)}
    return sorted(shared), dropped


def shared_seeds(scores: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, list[int]]]:
    """The scores restricted to the context seeds every seeded model carries.

    Draw k of one model is the same context draw as draw k of another, which
    is what lets the bootstrap draw the context jointly; a model that holds
    three draws beside one that holds one cannot be paired on the two draws
    the other lacks. Those cells stay in the per-cell table and leave the
    pooling, and which ones did is returned by model.
    """
    seeded = scores[scores["context_seed"].notna()]
    if seeded.empty:
        return scores, {}
    held = {model: {int(s) for s in frame["context_seed"].unique()}
            for model, frame in seeded.groupby("model")}
    common = set.intersection(*held.values())
    if not common:
        raise SystemExit("the seeded models share no context seed; nothing pairs")
    dropped = {model: sorted(s - common) for model, s in sorted(held.items()) if s - common}
    keep = scores["context_seed"].isna() | scores["context_seed"].isin(sorted(common))
    return scores[keep].reset_index(drop=True), dropped


def load_cohorts(scores: pd.DataFrame, cohorts_wanted: list[str] | None = None
                 ) -> tuple[dict[str, mt.ScoredCohort], dict[str, list[int | None]]]:
    """The shared rows of every cohort, with every cell's scores aligned to them.

    Every cell of a cohort has to hold the same rows in the same order for the
    resample to reach them all, and the outcome on a row has to be the same
    whichever model scored it; both are asserted rather than assumed. A cohort
    that some cell did not score is an error unless the cohorts to load are
    named, in which case only those are read.
    """
    models: dict[str, list[int | None]] = {}
    for model, seed in scores[["model", "context_seed"]].drop_duplicates().itertuples(index=False):
        models.setdefault(model, []).append(None if pd.isna(seed) else int(seed))
    for seeds in models.values():
        seeds.sort(key=lambda s: -1 if s is None else s)

    if cohorts_wanted is not None:
        scores = scores[scores["cohort"].isin(cohorts_wanted)]
    cohorts: dict[str, mt.ScoredCohort] = {}
    for cohort, frame in scores.groupby("cohort", sort=True):
        fixed: dict[str, np.ndarray] = {}
        seeded: dict[str, list[np.ndarray]] = {}
        outcome: np.ndarray | None = None
        rows: np.ndarray | None = None
        for model, seeds in models.items():
            for seed in seeds:
                mask = (frame["model"] == model) & (
                    frame["context_seed"].isna() if seed is None else frame["context_seed"] == seed
                )
                cell = frame[mask].sort_values("row")
                if cell.empty:
                    raise SystemExit(f"{cohort}: no scores for {cell_key(model, seed)}")
                if rows is None:
                    rows = cell["row"].to_numpy()
                    outcome = cell["outcome"].to_numpy()
                elif not np.array_equal(cell["row"].to_numpy(), rows):
                    raise SystemExit(f"{cohort}: {cell_key(model, seed)} scores different rows")
                elif not np.array_equal(cell["outcome"].to_numpy(), outcome):
                    raise SystemExit(f"{cohort}: {cell_key(model, seed)} carries a different outcome")
                if seed is None:
                    fixed[model] = cell["pd"].to_numpy(dtype=float)
                else:
                    seeded.setdefault(model, []).append(cell["pd"].to_numpy(dtype=float))
        cohorts[str(cohort)] = mt.ScoredCohort(outcome, fixed, seeded)
    return cohorts, models


def reference_edges(reference: pd.DataFrame) -> dict[str, tuple[np.ndarray, int]]:
    """Per cell, the decile edges of its own reference scores and the reference size."""
    out = {}
    for (model, seed), frame in reference.groupby(["model", "context_seed"], dropna=False):
        key = cell_key(model, seed)
        values = frame["pd"].to_numpy(dtype=float)
        out[key] = (mt.psi_edges(values), values.size)
    return out


def cell_table(scores: pd.DataFrame, reference: pd.DataFrame, edges,
               not_estimable: list[dict] | None = None) -> pd.DataFrame:
    """One row per cell and metric, with the interval each metric owes.

    A cell whose Cox fit did not finish carries NaN in the Cox rows, and is
    appended to ``not_estimable`` with the steps the fit took.
    """
    records = []
    head = scores.iloc[0]
    for (model, seed, cohort), frame in scores.groupby(["model", "context_seed", "cohort"],
                                                       dropna=False, sort=False):
        frame = frame.sort_values("row")
        y = frame["outcome"].to_numpy()
        s = frame["pd"].to_numpy(dtype=float)
        key = cell_key(model, seed)
        cuts, _ = edges[key]
        ref = reference[(reference["model"] == model)
                        & (reference["context_seed"].isna() if pd.isna(seed)
                           else reference["context_seed"] == seed)]["pd"].to_numpy(dtype=float)
        area = mt.delong(y, s)
        oe = mt.observed_over_expected(y, s)
        fit = mt.cox(y, s)
        if not fit.converged:
            nan = float("nan")
            if not_estimable is not None:
                not_estimable.append({"model": model,
                                      "context_seed": None if pd.isna(seed) else int(seed),
                                      "cohort": cohort, "iterations": fit.iterations})
            fit = mt.Cox(nan, nan, nan, nan, False, fit.alpha, fit.iterations)
        slope, intercept = fit.slope_interval, fit.intercept_interval
        split = mt.murphy(y, s)
        stability = mt.psi(ref, s, edges=cuts)
        base = {"build_id": head["build_id"], "arm": head["arm"], "model": model,
                "context_seed": None if pd.isna(seed) else int(seed), "cohort": cohort,
                "age_quarters": int(frame["age_quarters"].iloc[0]),
                "rows": int(y.size), "defaults": int(y.sum())}
        rows = [
            ("auc", area.value, area.lo, area.hi),
            ("gini", 2 * area.value - 1, 2 * area.lo - 1, 2 * area.hi - 1),
            ("ks", mt.ks(y, s), None, None),
            ("brier", split.brier, None, None),
            ("brier_miscalibration", split.miscalibration, None, None),
            ("brier_discrimination", split.discrimination, None, None),
            ("brier_uncertainty", split.uncertainty, None, None),
            ("observed_over_expected", oe.value, oe.lo, oe.hi),
            ("log_oe", mt.log_oe(y, s), np.log(oe.lo) if oe.lo > 0 else None, np.log(oe.hi)),
            ("cox_intercept", intercept.value, intercept.lo, intercept.hi),
            ("cox_slope", slope.value, slope.lo, slope.hi),
            ("psi", stability.value, None, None),
            ("psi_critical", stability.critical, None, None),
        ]
        assert len(rows) == CELL_METRICS
        for metric, value, lo, hi in rows:
            records.append({**base, "metric": metric, "value": value, "ci_lo": lo, "ci_hi": hi})
    table = pd.DataFrame(records)
    table["context_seed"] = table["context_seed"].astype("Int64")
    return table


def reference_shares(reference: pd.DataFrame, edges) -> dict[str, np.ndarray]:
    """Per cell, the share of its own reference in each of its decile bins."""
    out = {}
    for (model, seed), frame in reference.groupby(["model", "context_seed"], dropna=False):
        key = cell_key(model, seed)
        cuts, _ = edges[key]
        values = frame["pd"].to_numpy(dtype=float)
        counts = np.bincount(np.searchsorted(cuts, values, side="right"), minlength=cuts.size + 1)
        out[key] = counts / values.size
    return out


def psi_value(current: np.ndarray, cuts: np.ndarray, reference_share: np.ndarray) -> float:
    """PSI of a resampled score vector against fixed reference shares on fixed edges."""
    counts = np.bincount(np.searchsorted(cuts, current, side="right"), minlength=cuts.size + 1)
    share = counts / current.size
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = (share - reference_share) * np.log(share / reference_share)
    terms = np.where((share == 0) & (reference_share == 0), 0.0, terms)
    return float(np.sum(terms))


def pooled_statistics(models: dict[str, list[int | None]], edges, shares,
                      subset: list[str] | None):
    """The statistics the bootstrap pools: per-model means and every paired difference.

    Returns a callable of the cohorts, with the context draw chosen, that
    computes each cell's metrics once and assembles every name from them. A
    seeded model's reference is its own context sample, so its PSI reads
    against the reference of the draw the cohort carries: draw k of the
    control against context seed k.
    """
    names = [m for m in MODEL_ORDER if m in models] + sorted(set(models) - set(MODEL_ORDER))
    pairs = [(later, earlier) for earlier, later in itertools.combinations(names, 2)]

    def compute(cohorts):
        chosen = cohorts if subset is None else {k: cohorts[k] for k in subset}
        per_model: dict[str, dict[str, list[float]]] = {
            m: {k: [] for k in POOLED_METRICS} for m in names}
        for cohort in chosen.values():
            for model in names:
                s = cohort.scores[model]
                seeds = models[model]
                key = cell_key(model, None if seeds == [None] else seeds[cohort.draw])
                per_model[model]["gini"].append(mt.gini(cohort.outcome, s))
                per_model[model]["abs_log_oe"].append(abs_log_oe(cohort.outcome, s))
                deviation, signed = cox_slope_pair(cohort.outcome, s)
                per_model[model]["cox_slope_deviation"].append(deviation)
                per_model[model]["cox_slope"].append(signed)
                per_model[model]["psi"].append(psi_value(s, edges[key][0], shares[key]))
        keep = estimable(per_model, names)
        means = {m: {k: (paired_mean(v, keep) if k in COX_METRICS else float(np.mean(v)))
                     for k, v in d.items()} for m, d in per_model.items()}
        out: dict[str, float] = {}
        for metric in POOLED_METRICS:
            for model in names:
                out[f"{metric}|mean|{model}"] = means[model][metric]
            for later, earlier in pairs:
                out[f"{metric}|diff|{later}|{earlier}"] = (
                    means[later][metric] - means[earlier][metric]
                )
        for metric in COX_METRICS:
            out[f"{LEFT_OUT}|{metric}"] = float((~keep).sum())
        return out

    return compute


def plot_cells(table: pd.DataFrame, out: Path, pooled_cells: set[str] | None = None) -> None:
    """Every cell's trajectory with its interval.

    A cell in the per-cell table that the pooling left out (a draw no other
    seeded model holds) is drawn dotted and named as not pooled, so a spread
    the paired numbers do not carry is not read as one they do.
    """
    fig, axes = plt.subplots(1, 4, figsize=(19, 4.6))
    build = table["build_id"].iloc[0]
    draws_of = table.groupby("model")["context_seed"].nunique()
    # PSI is drawn as a multiple of each cell's own critical value, because
    # the critical value depends on the cell's reference size and one line
    # for all cells would be the wrong line for some of them.
    keys = ["model", "context_seed", "cohort"]
    ratio = table[table["metric"] == "psi"].merge(
        table[table["metric"] == "psi_critical"][[*keys, "value"]], on=keys,
        suffixes=("", "_critical"))
    ratio["value"] = ratio["value"] / ratio["value_critical"]
    ratio["metric"] = "psi_ratio"
    table = pd.concat([table, ratio.drop(columns="value_critical")], ignore_index=True)
    for ax, metric, title in zip(
        axes, ("gini", "observed_over_expected", "cox_slope", "psi_ratio"),
        ("Gini, DeLong interval", "observed over expected, binomial interval",
         "Cox slope, Wald interval",
         "PSI over the cell's Yurdakul critical value, log scale"),
    ):
        sub = table[table["metric"] == metric]
        labelled: set[tuple[str, bool]] = set()
        for (model, seed), cell in sub.groupby(["model", "context_seed"], dropna=False):
            cell = cell.sort_values("age_quarters")
            colour = model_colour(model)
            unpooled = pooled_cells is not None and cell_key(model, seed) not in pooled_cells
            alpha = 1.0 if pd.isna(seed) else (0.3 if unpooled else 0.45)
            style = ":" if unpooled else model_style(model)
            label = None
            legend_key = (model, unpooled)
            if legend_key not in labelled:
                labelled.add(legend_key)
                label = describe(model)
                if unpooled:
                    label += ", draw not pooled"
                elif not pd.isna(seed) and draws_of.get(model, 1) > 1:
                    label += ", one line per context draw"
            if metric != "psi_ratio":
                ax.errorbar(cell["age_quarters"], cell["value"],
                            yerr=[cell["value"] - cell["ci_lo"], cell["ci_hi"] - cell["value"]],
                            color=colour, alpha=alpha, marker="o", markersize=3, capsize=2,
                            linewidth=1.2, linestyle=style, label=label)
            else:
                ax.plot(cell["age_quarters"], cell["value"], color=colour, alpha=alpha,
                        marker="o", markersize=3, linewidth=1.2, linestyle=style, label=label)
        if metric in ("observed_over_expected", "cox_slope"):
            ax.axhline(1.0, color="black", linewidth=0.8, linestyle=":")
        if metric == "psi_ratio":
            ax.axhline(1.0, color="black", linewidth=0.8, linestyle="--",
                       label="the cell's critical value, α = 0.05")
            ax.set_yscale("log")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("model age, quarters")
        ax.grid(alpha=0.3)
    handles, labels = axes[0].get_legend_handles_labels()
    seen = {}
    for h, l in zip(handles, labels):
        seen.setdefault(l, h)
    h2, l2 = axes[3].get_legend_handles_labels()
    for h, l in zip(h2, l2):
        seen.setdefault(l, h)
    columns = min(len(seen), 4)
    rows = -(-len(seen) // columns)
    fig.legend(seen.values(), seen.keys(), loc="lower center", ncol=columns, frameon=False,
               fontsize=9)
    fig.suptitle(f"{build}: every cell with the interval it owes", fontsize=11)
    fig.tight_layout(rect=(0, 0.05 + 0.035 * rows, 1, 0.95))
    fig.savefig(out, dpi=130)
    plt.close(fig)


def pooling_label(which: str, pooled: int, scored: int) -> str:
    """What a pooling is called where a reader sees it: with its cohort count.

    "all" is every cohort the pooling could reach, which is the cohorts every
    cell scored and not every cohort of the build; the label says how many of
    each so that a pooling over three of eleven is not read as eleven.
    """
    count = f"{pooled} shared cohort{'s' if pooled != 1 else ''} of {scored} scored"
    if which == "all":
        return count
    if which.startswith("all,"):
        return count + which[3:]
    return f"{which} cohorts"


def plot_paired(paired: pd.DataFrame, out: Path, pooled: int, scored: int,
                disagreeing: set[str] | None = None) -> None:
    """Every paired difference with its pooled interval.

    A difference whose per-draw intervals do not all overlap is drawn with a
    hollow marker: its pooled interval is the percentiles of a mixture of
    draws that disagree, not an interval on one quantity.
    """
    diffs = paired[paired["is_difference"] & paired["draw"].isna()].copy()
    disagreeing = disagreeing or set()
    poolings = [(which, colour) for which, colour in (
        ("all", "#0E6B66"), ("nearest", "#9A5B24"), ("all, cohorts resampled", "#4B3F8F"))
        if which in set(diffs["cohorts"])]
    pairs = diffs[diffs["cohorts"] == "all"]["pair"].nunique()
    height = max(4.2, 1.6 + 0.2 * pairs * max(1, len(poolings)))
    fig, axes = plt.subplots(1, len(POOLED_METRICS), figsize=(5 * len(POOLED_METRICS), height))
    hollow = False
    for ax, metric in zip(axes, POOLED_METRICS):
        sub = diffs[diffs["metric"] == metric]
        labels = sub[sub["cohorts"] == "all"]["pair"].tolist()
        y = np.arange(len(labels))
        for offset, (which, colour) in enumerate(poolings):
            part = sub[sub["cohorts"] == which].set_index("pair").loc[labels]
            positions = y + (offset - (len(poolings) - 1) / 2) * 0.25
            for row, pos in zip(part.itertuples(), positions):
                disagree = f"{metric}|{row.Index}" in disagreeing
                hollow = hollow or disagree
                ax.errorbar(row.value, pos, xerr=[[row.value - row.ci_lo], [row.ci_hi - row.value]],
                            fmt="o", color=colour, capsize=3, markersize=4,
                            markerfacecolor="white" if disagree else colour)
            ax.errorbar([], [], fmt="o", color=colour, capsize=3, markersize=4,
                        label=pooling_label(which, pooled, scored))
        ax.axvline(0.0, color="black", linewidth=0.8, linestyle=":")
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_title(POOLED_TITLE[metric], fontsize=10)
        ax.grid(alpha=0.3, axis="x")
    handles, labels = axes[0].get_legend_handles_labels()
    if hollow:
        handles.append(plt.Line2D([], [], marker="o", color="black", markerfacecolor="white",
                                  linestyle="none", markersize=4))
        labels.append("hollow: the per-draw intervals do not all overlap")
    fig.legend(handles, labels, loc="lower center", ncol=len(labels), frameon=False, fontsize=9)
    fig.suptitle(f"paired differences pooled over the {pooled} cohorts every cell scored, "
                 "cohort-blocked bootstrap interval", fontsize=11)
    fig.tight_layout(rect=(0, min(0.08, 0.34 / height), 1, 0.94))
    fig.savefig(out, dpi=130)
    plt.close(fig)


def plot_reliability(scores: pd.DataFrame, models: dict[str, list[int | None]],
                     youngest: str, oldest: str, out: Path) -> None:
    """Every model's reliability curve on the youngest and the oldest pooled cohort.

    One panel per model, the youngest cohort solid and the oldest dashed; the
    diagonal is calibration. A seeded model's first draw carries the
    binomial intervals and its other draws are drawn thin beside it, so the
    draw spread is on the figure. Each panel takes its own square axis, since
    one axis shared across models is set by the model with the widest range
    and leaves the others unreadable. Ten quantile bins, so the curve reads
    where the scores are and not where a fixed grid would put them.
    """
    names = list(models)
    fig, axes = plt.subplots(1, len(names), figsize=(3.8 * len(names), 4.0))
    axes = np.atleast_1d(axes)
    for ax, model in zip(axes, names):
        colour = model_colour(model)
        top = 0.0
        for k, seed in enumerate(models[model]):
            for cohort, style in ((youngest, "-"), (oldest, "--")):
                frame = scores[(scores["cohort"] == cohort) & (scores["model"] == model)
                               & (scores["context_seed"].isna() if seed is None
                                  else scores["context_seed"] == seed)]
                curve = mt.reliability(frame["outcome"].to_numpy(),
                                       frame["pd"].to_numpy(dtype=float))
                x = np.array(curve.mean_score)
                y = np.array(curve.observed)
                if k == 0:
                    ax.errorbar(x, y, yerr=[y - np.array(curve.lo), np.array(curve.hi) - y],
                                color=colour, linestyle=style, marker="o", markersize=3,
                                capsize=2, linewidth=1.2, label=cohort)
                    top = max(top, float(np.nanmax(np.array(curve.hi))))
                else:
                    ax.plot(x, y, color=colour, linestyle=style, linewidth=0.8, alpha=0.4)
                top = max(top, float(np.nanmax(x)), float(np.nanmax(y)))
        seeds = [s for s in models[model] if s is not None]
        if not seeds:
            title = describe(model)
        elif len(seeds) == 1:
            title = f"{describe(model)}, draw {seeds[0]}"
        else:
            others = ", ".join(map(str, seeds[1:]))
            title = f"{describe(model)}, draw {seeds[0]}\nthin: draws {others}"
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("mean predicted probability in the bin")
        ax.legend(frameon=False, fontsize=8, title="cohort", title_fontsize=8)
        ax.grid(alpha=0.3)
        limit = top * 1.05
        ax.plot([0, limit], [0, limit], color="black", linewidth=0.8, linestyle=":")
        ax.set_xlim(0, limit)
        ax.set_ylim(0, limit)
    axes[0].set_ylabel("observed default rate, binomial interval")
    fig.suptitle("reliability, ten quantile bins, youngest and oldest pooled cohort", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out, dpi=130)
    plt.close(fig)


PAIR_KEYS = ["cohorts", "metric", "pair"]


def seed_check(primary: pd.DataFrame, repeats: pd.DataFrame) -> dict:
    """Which differences keep or lose their star when the bootstrap is re-drawn.

    A star says an interval of two hundred resamples excludes zero, and a
    difference near the edge of its interval can gain or lose it on the
    resampling seed alone. `primary` holds the pooled difference rows of the
    main seed, `repeats` the same rows under other seeds with a
    `bootstrap_seed` column; every row whose star differs under any seed is
    named, with its interval under each, and the largest movement of any
    interval bound across seeds is reported for every difference.
    """
    diffs = primary[primary["is_difference"]]
    seeds = sorted(int(s) for s in repeats["bootstrap_seed"].unique())
    changed: list[dict] = []
    widest = 0.0
    for row in diffs.itertuples():
        same = repeats[(repeats["cohorts"] == row.cohorts) & (repeats["metric"] == row.metric)
                       & (repeats["pair"] == row.pair)]
        if len(same) != len(seeds):
            raise SystemExit(f"{row.metric} {row.pair} ({row.cohorts}) was not repeated under "
                             "every check seed")
        under = {int(s): {"excludes_zero": bool(e), "ci_lo": float(lo), "ci_hi": float(hi)}
                 for s, e, lo, hi in zip(same["bootstrap_seed"], same["excludes_zero"],
                                         same["ci_lo"], same["ci_hi"])}
        movement = max(max(abs(v["ci_lo"] - row.ci_lo), abs(v["ci_hi"] - row.ci_hi))
                       for v in under.values())
        widest = max(widest, movement)
        if any(v["excludes_zero"] != bool(row.excludes_zero) for v in under.values()):
            changed.append({"cohorts": row.cohorts, "metric": row.metric, "pair": row.pair,
                            "value": float(row.value), "primary": {
                                "excludes_zero": bool(row.excludes_zero),
                                "ci_lo": float(row.ci_lo), "ci_hi": float(row.ci_hi)},
                            "under": under, "bound_movement": movement})
    starred = int(diffs["excludes_zero"].fillna(False).astype(bool).sum())
    return {"seeds": seeds, "differences": len(diffs), "starred": starred,
            "star_changed": changed, "largest_bound_movement": widest}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scores_dirs", type=Path, nargs="+",
                        help="directories holding scores.parquet and reference.parquet of one "
                             "build; a foundation-model run is a second directory")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--drop", default="",
                        help="comma-separated model names to leave out of everything: the "
                             "per-cell table, the pooling and the figures")
    parser.add_argument("--resamples", type=int, default=mt.RESAMPLES)
    parser.add_argument("--seed", type=int, default=BOOTSTRAP_SEED)
    parser.add_argument("--check-seeds", default="",
                        help="comma-separated bootstrap seeds to repeat the poolings under; "
                             "the differences whose star changes with the seed are named")
    parser.add_argument("--nearest", type=int, default=NEAREST,
                        help="how many of the youngest cohorts form the second pooling")
    parser.add_argument("--cells", type=Path, default=None,
                        help="the build run's cells.csv: a cohort it puts under the floors stays "
                             "in the per-cell table and leaves every pooling")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()

    scores = pd.concat([pd.read_parquet(d / "scores.parquet") for d in args.scores_dirs],
                       ignore_index=True)
    reference = pd.concat([pd.read_parquet(d / "reference.parquet") for d in args.scores_dirs],
                          ignore_index=True)
    dropped_models = [m for m in args.drop.split(",") if m]
    if dropped_models:
        scores, reference = drop_models(scores, reference, dropped_models)
    build = scores["build_id"].iloc[0]
    if scores["build_id"].nunique() != 1 or reference["build_id"].nunique() != 1:
        raise SystemExit("one build per score file")
    duplicated = scores[["model", "context_seed", "cohort", "row"]].duplicated()
    if duplicated.any():
        raise SystemExit("the same cell is scored in more than one of the directories")
    print(f"build                 : {build}")
    print(f"sources               : {', '.join(d.as_posix() for d in args.scores_dirs)}")
    derived: dict[str, dict] = {}
    for directory in args.scores_dirs:
        entry = derivation_of(directory)
        if entry is not None:
            derived[entry["model"]] = entry
    print(f"scored rows           : {len(scores):,}")
    print(f"reference rows        : {len(reference):,}")
    if dropped_models:
        print(f"models dropped        : {', '.join(dropped_models)}")

    scored_cohorts = sorted(scores["cohort"].astype(str).unique())
    floor_of: dict[str, bool] | None = None
    if args.cells is not None:
        floor_of = floor_verdicts(read_floors(args.cells), args.cells, build, scored_cohorts)
    pooled, dropped_seeds = shared_seeds(scores)
    shared, dropped = shared_cohorts(pooled)
    cohorts, models = load_cohorts(pooled, shared)
    under: list[str] = []
    if floor_of is None:
        check_floors({f"{build} {c}": v.outcome for c, v in cohorts.items()}, None)
    else:
        under = [c for c in scored_cohorts if not floor_of[c]]
        check_floors({f"{build} {c}": v.outcome for c, v in cohorts.items() if floor_of[c]},
                     args.cells)
        cohorts = {c: v for c, v in cohorts.items() if floor_of[c]}
        if not cohorts:
            raise SystemExit(f"{build}: no shared cohort is above the floors; nothing pools")

    edges = reference_edges(reference)
    not_estimable: list[dict] = []
    table = cell_table(scores, reference, edges, not_estimable)
    if floor_of is not None:
        table["floor"] = table["cohort"].astype(str).map(floor_of)
    table.to_parquet(args.out_dir / "metrics.parquet", index=False)
    table.to_csv(args.out_dir / "metrics.csv", index=False)
    print(f"cells                 : {len(table) // CELL_METRICS}")
    pd.DataFrame(not_estimable, columns=["model", "context_seed", "cohort", "iterations"]).to_csv(
        args.out_dir / "cox-not-estimable.csv", index=False)
    if not_estimable:
        print(f"Cox not estimable     : {len(not_estimable)} cells whose fit did not finish: "
              + ", ".join(f"{cell_key(c['model'], c['context_seed'])} {c['cohort']} "
                          f"({c['iterations']} steps)" for c in not_estimable))

    shares = reference_shares(reference, edges)
    order = sorted(cohorts)
    nearest = [c for c in shared[:args.nearest] if c in cohorts]
    window = (f"nearest {args.nearest}" if floor_of is None
              else f"nearest {args.nearest} less those under the floors")
    print(f"cohorts pooled        : {len(order)} of {len(scored_cohorts)} scored, "
          f"{window}: {', '.join(nearest)}")
    if floor_of is not None:
        print(f"floors                : {len(scored_cohorts) - len(under)} of "
              f"{len(scored_cohorts)} cells above the floors of {FLOOR_ROWS:,} rows and "
              f"{FLOOR_DEFAULTS} defaults, the verdict of {args.cells.as_posix()}")
        for cohort in under:
            print(f"  {cohort} left out of the pooling: under the floors")
    for cohort, cells in dropped.items():
        print(f"  {cohort} left out of the pooling: not scored by {', '.join(cells)}")
    for model, seeds in dropped_seeds.items():
        print(f"  {model} draws {seeds} left out of the pooling: no other seeded model "
              f"holds them")
    print("models                : " + ", ".join(
        f"{m} ({len(s)} draw{'s' if len(s) > 1 else ''})" if s != [None] else m
        for m, s in models.items()))

    paired_records = []
    left_out: dict[str, dict] = {}

    def record(which: str, draw: int | None, result: dict[str, mt.Bootstrap]) -> None:
        result, counts = left_out_of(result)
        left_out[which if draw is None else f"{which}, draw {draw}"] = counts
        for name, boot in result.items():
            metric, kind, *cells = name.split("|")
            difference = kind == "diff"
            paired_records.append({
                "build_id": build, "cohorts": which, "draw": draw, "metric": metric,
                "pair": " - ".join(cells) if difference else cells[0],
                "is_difference": difference, **boot.as_dict(),
                "excludes_zero": boot.excludes_zero if difference else None,
                "reads_derived": reads_derived(" - ".join(cells), derived),
            })

    # Three poolings: every shared cohort with the cohorts held fixed, the
    # youngest few, and every shared cohort with the cohorts resampled too.
    # When the youngest few are all there is, the second is the first and is
    # not repeated as if it were another measurement.
    poolings = [("all", None, False), ("nearest", nearest, False),
                ("all, cohorts resampled", None, True)]
    if not nearest:
        poolings = [p for p in poolings if p[0] != "nearest"]
        print(f"nearest {args.nearest} holds no cohort above the floors; that pooling is not read")
    elif len(nearest) == len(order):
        poolings = [p for p in poolings if p[0] != "nearest"]
        print(f"nearest {args.nearest} is every pooled cohort; that pooling is not repeated")
    for which, subset, clustered in poolings:
        stage = time.time()
        result = mt.cohort_blocked_bootstrap_many(
            cohorts, pooled_statistics(models, edges, shares, subset),
            resamples=args.resamples, seed=args.seed, resample_cohorts=clustered,
        )
        record(which, None, result)
        print(f"bootstrap {which:<22}: {args.resamples} resamples in {time.time() - stage:.0f}s")

    # The same poolings under other bootstrap seeds, kept apart from the
    # primary rows: they say which stars are the resampling's and not the
    # difference's, and they are not averaged into the primary interval.
    check_seeds = [int(s) for s in args.check_seeds.split(",") if s.strip()]
    if args.seed in check_seeds:
        raise SystemExit(f"--check-seeds repeats the primary seed {args.seed}")
    repeat_records = []
    for check_seed in check_seeds:
        stage = time.time()
        for which, subset, clustered in poolings:
            result = mt.cohort_blocked_bootstrap_many(
                cohorts, pooled_statistics(models, edges, shares, subset),
                resamples=args.resamples, seed=check_seed, resample_cohorts=clustered,
            )
            for name, boot in result.items():
                metric, kind, *cells = name.split("|")
                if kind != "diff":
                    continue
                repeat_records.append({
                    "build_id": build, "bootstrap_seed": check_seed, "cohorts": which,
                    "metric": metric, "pair": " - ".join(cells), **boot.as_dict(),
                    "excludes_zero": boot.excludes_zero,
                })
        print(f"bootstrap seed {check_seed:<17}: every pooling again in {time.time() - stage:.0f}s")

    # The same interval with the context draw held fixed, once per draw. The
    # pooled interval above mixes the draws, and a mixture of a few draws can
    # look like one distribution when the draws disagree; these rows say
    # whether they do.
    draw_count = cohorts[order[0]].draws
    common = sorted(set.intersection(*(set(s) for s in models.values() if s != [None]))) \
        if draw_count > 1 else []
    for k, seed_value in enumerate(common):
        fixed = {key: c.realise(k) for key, c in cohorts.items()}
        models_k = {m: ([None] if s == [None] else [s[k]]) for m, s in models.items()}
        result = mt.cohort_blocked_bootstrap_many(
            fixed, pooled_statistics(models_k, edges, shares, None),
            resamples=args.resamples, seed=args.seed,
        )
        record("all", seed_value, result)
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
    seed_sensitive: set[tuple[str, str, str]] = set()
    if repeat_records:
        repeats = pd.DataFrame(repeat_records)
        primary = paired[paired["draw"].isna() & paired["is_difference"]]
        checked = seed_check(primary, repeats)
        seed_sensitive = {(c["cohorts"], c["metric"], c["pair"]) for c in checked["star_changed"]}
        pd.concat([primary.assign(bootstrap_seed=args.seed)[repeats.columns], repeats],
                  ignore_index=True).to_csv(args.out_dir / "paired-seeds.csv", index=False)

    print(f"\npaired differences over the {len(order)} shared cohorts of {len(scored_cohorts)} "
          "scored (value [lo, hi], * excludes zero, ! draws disagree"
          + (", ? star changes with the bootstrap seed" if checked else "")
          + (", ~ reads derived rows, their error below" if derived else "") + "):")
    mixture = paired[(paired["cohorts"] == "all") & paired["is_difference"] & paired["draw"].isna()]
    for row in mixture.itertuples():
        flag = "*" if row.excludes_zero else " "
        flag += "!" if f"{row.metric}|{row.pair}" in disagreeing else " "
        flag += "?" if ("all", row.metric, row.pair) in seed_sensitive else " "
        flag += "~" if reads_derived(row.pair, derived) else ""
        print(f"  {row.metric:<11} {row.pair:<22} {row.value:+.4f} "
              f"[{row.ci_lo:+.4f}, {row.ci_hi:+.4f}] {flag}")
    for name, spans in disagreeing.items():
        print(f"  {name}: draw intervals " + "; ".join(
            f"{s['draw']} [{s['ci_lo']:+.4f}, {s['ci_hi']:+.4f}]" for s in spans))
    for which, counts in left_out.items():
        for metric, count in counts.items():
            over = "" if ", draw " in which else ", averaged over the context draws"
            print(f"  {metric} ({which}): {count['point']:g} cohorts not estimable left out of "
                  f"the point estimate{over}, at most {count['largest_in_a_resample']:g} of any "
                  "resample")
    for entry in derived.values():
        print(f"  ~ {derivation_text(entry)}")
    if checked:
        print(f"\nbootstrap seed check over seeds {', '.join(map(str, checked['seeds']))}: "
              f"{checked['starred']} of {checked['differences']} differences starred under "
              f"seed {args.seed}, {len(checked['star_changed'])} change their star, largest "
              f"movement of an interval bound {checked['largest_bound_movement']:.4f}")
        for change in checked["star_changed"]:
            print(f"  {change['metric']:<11} {change['pair']:<22} ({change['cohorts']}) "
                  f"{change['value']:+.4f} " + "; ".join(
                      f"{s} [{v['ci_lo']:+.4f}, {v['ci_hi']:+.4f}]{'*' if v['excludes_zero'] else ''}"
                      for s, v in ((args.seed, change["primary"]), *change["under"].items())))
    if not common:
        held = sorted({int(s) for seeds in models.values() for s in seeds if s is not None})
        print(f"  one context draw shared ({', '.join(map(str, held))}): no per-draw rows, "
              "and every interval above is a single-draw interval")

    pooled_cells = {cell_key(m, s) for m, seeds in models.items() for s in seeds}
    plot_cells(table, args.out_dir / "cell-intervals.png", pooled_cells)
    plot_paired(paired, args.out_dir / "paired-differences.png", len(order), len(scored_cohorts),
                set(disagreeing))
    plot_reliability(pooled, models, order[0], order[-1], args.out_dir / "reliability.png")

    if common:
        per_draw: str | None = ("the 'all' pooling repeated with each context draw held fixed, "
                                "in the rows of paired.csv whose draw is set")
        context_draw = "drawn with the resample, jointly"
    else:
        per_draw = None
        context_draw = ("one draw shared by every seeded model, so the draw is fixed and "
                        "every interval is conditional on it; the seed spread is not measured")
    summary = {
        "build_id": build,
        "models": {m: ([] if s == [None] else s) for m, s in models.items()},
        "sources": [d.as_posix() for d in args.scores_dirs],
        "derived_rows": derived,
        "cohorts": order,
        "cohorts_pooled": len(order),
        "cohorts_scored": len(scored_cohorts),
        "cohorts_not_pooled": dropped,
        **({} if floor_of is None else {"floors": {
            "record": args.cells.as_posix(), "rows": FLOOR_ROWS, "defaults": FLOOR_DEFAULTS,
            "cells_above": len(scored_cohorts) - len(under), "cells": len(scored_cohorts),
            "reading": f"{len(scored_cohorts) - len(under)} of {len(scored_cohorts)} cells "
                       "above the floors",
            "under": under,
            "rule": "a cell under the floors is in metrics.csv with its interval and floor "
                    "False, and enters no pooling; the nearest pooling is the youngest "
                    "cohorts less those under the floors"}}),
        "draws_not_pooled": dropped_seeds,
        "models_dropped": dropped_models,
        "nearest": nearest,
        "bootstrap": {"resamples": args.resamples, "seed": args.seed, "alpha": mt.ALPHA,
                      "blocking": "cohort", "context_draw": context_draw,
                      "poolings": [p[0] for p in poolings],
                      "pooled_metrics": list(POOLED_METRICS),
                      "per_draw": per_draw,
                      "draws_disagree": disagreeing if common else None,
                      "seed_check": checked,
                      "cox_left_out": left_out,
                      "multiplicity": "none: every interval is reported at alpha on its own, "
                                      "and the pairs are not adjusted for one another"},
        "cox_not_estimable": {
            "cells": not_estimable,
            "rule": "a cell whose Cox fit did not finish carries NaN in the Cox rows of the "
                    "per-cell table and leaves the pairing of every Cox statistic for every "
                    "model, in the point estimate and in every resample; cox_left_out counts "
                    "the cells left out"},
        "calibration": {
            "observed_over_expected": "observed defaults over the mean predicted probability, "
                                      "Clopper-Pearson on the count; the level",
            "cox": "logit P(y) = intercept + slope * logit(score), Newton on the logistic "
                   "likelihood, Wald intervals; a level shift is the intercept, a stretch or "
                   "compression of the scale is the slope; the pooled statistic is |slope - 1|",
            "cox_signed": "the signed slope pooled beside |slope - 1| over the same estimable "
                          "cells: its mean rows read against one, its differences against zero",
            "brier": "with the CORP decomposition of Dimitriadis, Gneiting and Jordan (2021): "
                     "miscalibration - discrimination + uncertainty, recalibrated by isotonic "
                     "regression",
            "reliability": "ten quantile bins of each cell's own scores, reliability.png on "
                           "the youngest and oldest pooled cohort"},
        "psi": {"bins": mt.PSI_BINS, "edges": "the cell's own reference deciles",
                "critical": "Yurdakul, alpha 0.05, at the cell's sample sizes"},
        "reference_sizes": {k: n for k, (_, n) in edges.items()},
        "wall_seconds": round(time.time() - started, 1),
    }
    (args.out_dir / "intervals.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nwall                  : {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
