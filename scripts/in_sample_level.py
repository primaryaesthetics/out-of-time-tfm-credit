#!/usr/bin/env python3
"""The in-sample level of every context cell, and H5: whether it moves with prevalence.

A foundation model scores its own context as well as the cohorts: each
context of EXP-005 is a draw of fifty thousand rows from a build's pool
under one context seed, and the scorer writes the model's probability on
every one of them to reference.parquet. A fitted model's reference rows are
its own training rows — the whole pool for the scorecard and the full GBM,
the context draw for GBM-50k. Every such cell is read here: its rows, its
realised rate, the model's mean probability on it, and observed over
expected, with the binomial interval of the metrics module and a bootstrap
interval over the cell's rows.

On its own training rows a model fitted by likelihood reads observed over
expected of one by construction, and those cells are the known answer the
reading is checked against: they are reported beside the foundation
models', each with whether its bootstrap interval holds one.

H5 is written across the contexts of an arm: the in-sample observed over
expected at the shipped temperature of the highest-rate context minus that
of the lowest-rate context, per foundation model, read against the
bootstrap interval over context rows with the context seed drawn with the
resample. Here a context is a build's pool as its draws sample it, and the
two ends of an arm are the builds with the highest and the lowest pool rate
in the build run's record (`--builds-json`), fixed before any model was
fitted, as EXP-005's note of 2026-09-14 reads the hypothesis. The mean
realised rate of each build's shared draws is printed beside its pool
rate; where the draws rank an arm's ends otherwise, H5 under that ranking
is bootstrapped on its own and reported beside the criterion's, labelled as
not a criterion. Each resample draws one context seed for both builds
and every model — draw k of one build is draw k of the other, as the arm
pooling draws it — and within each of the two contexts one row index,
applied to the outcomes and to every model's probability on those rows.
Every seeded model that holds both builds is read: the foundation models at
every temperature some directory holds, a model named ``model@t1`` (derived
or scored) being the reading at 1.0 and printed beside the model at 0.9;
and GBM-50k, whose row is the known answer, zero, since its level is one on
every context it was fitted on. A star marks an interval that excludes
zero. `--check-seeds` repeats the pooling under other bootstrap seeds and
names every star that changes.

The Cox slope of every context cell is fitted beside its level, with its
Wald interval, and pooled per arm in a bootstrap of its own: the mean over
the arm's builds of each seeded model's slope on its context, one context
seed drawn per resample for every build and model and one row index per
context, as H5 draws. The scorecard on its own pool is the known answer: an
unpenalised logistic model with an intercept solves at its maximum the
score equations the Cox fit solves at (0, 1), so its cells read slope one
and intercept zero to the solver's tolerance, and a cell that does not is
named. The reading is one-sided (EXP-005, the smoothing reading of
2026-09-17): a model that has seen a row's label predicts it better than its
probability says, which also reads a slope above one, so an in-sample slope
above one is confounded and only one at or below one reads anything.

Every seeded model of one (build, seed) reads one context draw, so all of
them have to hold the same context rows with the same outcomes; the reading
refuses otherwise, and refuses a cell that two directories hold.

The figure EXP-005 names: mean predicted probability against realised rate,
both axes log, the identity line drawn, one panel per model, one marker per
cell, the in-sample cells marked by arm. With `--with-cohorts` the
out-of-sample cohort cells of the same directories are drawn beside them
from their scores; a cohort cell with no default has no place on a log axis
and is counted instead.

Unlike the interval scripts, any number of builds can be named at once, and
the arm of each is read from its rows.

``inputs.json`` holds the sha256 of every file in the directories read and of
the build run's record named with `--builds-json`.

    python scripts/record_run.py fm-grid-in-sample -- \\
        python scripts/in_sample_level.py \\
            experiments/2026-09-13-fm-2002h2e-scores ... \\
            experiments/2026-09-14-fm-2002h2e-tabicl-rental-4090 ... \\
            --with-cohorts --check-seeds 20260906,20260907 \\
            --out-dir experiments/<date>-fm-grid-in-sample
"""

from __future__ import annotations

import argparse
import json
import math
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

import build_intervals as bi
import record_run as rr

from outoftime import metrics as mt

TFM = ("tabpfn", "tabicl")
KEY_COLUMNS = ["build_id", "arm", "model", "context_seed"]
REFERENCE_COLUMNS = KEY_COLUMNS + ["row", "outcome", "pd"]
SCORE_COLUMNS = KEY_COLUMNS + ["cohort", "outcome", "pd"]
# The name the outcomes of a context draw travel under inside the bootstrap,
# beside the models' probabilities on the same rows.
OUTCOME = "__outcome__"
CELL = "cell"
ARM_COLOUR = {"E": "#0E6B66", "R": "#9A5B24"}
# How far from (0, 1) the scorecard's Cox fit on its own pool may land and still read as the
# known answer: the solvers' tolerance, well above the 1e-6 measured on both books' pools.
SLOPE_TOLERANCE = 1e-4
KNOWN_SLOPE_MODEL = "scorecard"

Key = tuple[str, str, str, "int | None"]


def cell_name(key: Key) -> str:
    build, _, model, seed = key
    return f"{build} {bi.cell_key(model, seed)}"


def order_key(key: Key) -> tuple:
    build, arm, model, seed = key
    rank = bi.MODEL_ORDER.index(bi.base_model(model)) if bi.base_model(model) in bi.MODEL_ORDER \
        else len(bi.MODEL_ORDER)
    return (arm, build, rank, model, -1 if seed is None else seed)


def model_names(models) -> list[str]:
    return sorted(set(models), key=lambda m: order_key(("", "", m, None)))


# --- the context cells ----------------------------------------------------------------


def load_contexts(dirs: list[Path], drop: list[str]
                  ) -> tuple[dict[Key, tuple[np.ndarray, np.ndarray, np.ndarray]], dict[Key, str]]:
    """Every context cell of the directories named, as sorted rows, outcomes and probabilities."""
    cells: dict[Key, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    origin: dict[Key, str] = {}
    held: set[str] = set()
    for directory in dirs:
        reference = pd.read_parquet(directory / "reference.parquet", columns=REFERENCE_COLUMNS)
        held |= set(reference["model"].unique())
        if drop:
            reference = reference[~reference["model"].isin(drop)]
        for (build, arm, model, seed), frame in reference.groupby(KEY_COLUMNS, dropna=False,
                                                                  sort=True):
            key = (str(build), str(arm), str(model), None if pd.isna(seed) else int(seed))
            if key in cells:
                raise SystemExit(f"{cell_name(key)} is held by {origin[key]} and "
                                 f"{directory.as_posix()}; one context cell, one directory")
            frame = frame.sort_values("row")
            rows = frame["row"].to_numpy()
            if np.unique(rows).size != rows.size:
                raise SystemExit(f"{cell_name(key)} holds a row twice")
            # A training pool is compared with nothing, so its row ids are not kept.
            cells[key] = (rows if key[3] is not None else np.empty(0, dtype=np.int64),
                          frame["outcome"].to_numpy(dtype=np.int8),
                          frame["pd"].to_numpy(dtype=float))
            origin[key] = directory.as_posix()
    missing = sorted(set(drop) - held)
    if missing:
        raise SystemExit(f"--drop names models that hold no rows: {', '.join(missing)}")
    if not cells:
        raise SystemExit("no context cell in the directories named")
    return cells, origin


def check_contexts(cells) -> dict:
    """Refuses unless every seeded model of one (build, seed) holds one context: same rows, same outcomes."""
    by_draw: dict[tuple[str, int], list[tuple[str, np.ndarray, np.ndarray]]] = {}
    for (build, _, model, seed), (rows, y, _) in cells.items():
        if seed is not None:
            by_draw.setdefault((build, seed), []).append((model, rows, y))
    compared = 0
    for (build, seed), entries in sorted(by_draw.items()):
        first, rows0, y0 = entries[0]
        for model, rows, y in entries[1:]:
            if not np.array_equal(rows, rows0):
                raise SystemExit(f"{build} draw {seed}: {model} and {first} hold different context "
                                 "rows; they do not read one context")
            if not np.array_equal(y, y0):
                raise SystemExit(f"{build} draw {seed}: an outcome differs between {model} and "
                                 f"{first} on the same context row")
            compared += 1
    return {"draws": len(by_draw), "pairs_compared": compared,
            "statement": "every seeded model of one (build, context seed) holds the same context "
                         "rows with the same outcomes"}


def level(cohorts) -> dict[str, float]:
    (cohort,) = cohorts.values()
    return {"oe": float(cohort.outcome.mean() / cohort.scores[CELL].mean())}


def cell_table(cells, resamples: int, seed: int) -> pd.DataFrame:
    """One row per context cell: its level with the binomial interval and the bootstrap over its rows."""
    records = []
    for key in sorted(cells, key=order_key):
        build, arm, model, context_seed = key
        _, y, p = cells[key]
        binomial = mt.observed_over_expected(y, p)
        boot = mt.cohort_blocked_bootstrap_many({CELL: mt.ScoredCohort(y, {CELL: p})}, level,
                                                resamples=resamples, seed=seed)["oe"]
        fitted = bi.base_model(model) not in TFM
        cox = mt.cox(y, p)
        slope, intercept = cox.slope_interval, cox.intercept_interval
        pool = context_seed is None and bi.base_model(model) == KNOWN_SLOPE_MODEL
        records.append({
            "build_id": build, "arm": arm, "model": model, "context_seed": context_seed,
            "kind": "context draw" if context_seed is not None else "training pool",
            "fitted": fitted, "rows": int(y.size), "defaults": int(y.sum()),
            "realised_rate": float(y.mean()), "mean_pd": float(p.mean()),
            "observed_over_expected": binomial.value,
            "binomial_lo": binomial.lo, "binomial_hi": binomial.hi,
            "bootstrap_lo": boot.lo, "bootstrap_hi": boot.hi,
            "bootstrap_holds_one": bool(boot.lo <= 1.0 <= boot.hi),
            "cox_converged": bool(cox.converged),
            "cox_slope": slope.value, "cox_slope_lo": slope.lo, "cox_slope_hi": slope.hi,
            "cox_intercept": intercept.value, "cox_intercept_lo": intercept.lo,
            "cox_intercept_hi": intercept.hi,
            "slope_known_answer": (bool(cox.converged and abs(cox.slope - 1.0) <= SLOPE_TOLERANCE
                                        and abs(cox.intercept) <= SLOPE_TOLERANCE)
                                   if pool else None),
        })
    table = pd.DataFrame(records)
    table["context_seed"] = table["context_seed"].astype("Int64")
    return table


# --- H5 -------------------------------------------------------------------------------


def pool_rates(path: Path) -> dict[str, tuple[str, float]]:
    """Every build's arm and pool rate, as the build run recorded them before any model."""
    record = json.loads(path.read_text(encoding="utf-8"))
    arms = record.get("arms")
    if not isinstance(arms, dict):
        raise SystemExit(f"{path.as_posix()} records no builds by arm")
    out: dict[str, tuple[str, float]] = {}
    for arm, builds in arms.items():
        for build in builds:
            out[str(build["build_id"])] = (str(arm), float(build["pool"]["rate"]))
    return out


def arm_contexts(cells, arm: str, pools: dict[str, tuple[str, float]] | None) -> dict:
    """The highest- and the lowest-rate context of an arm, aligned for the joint bootstrap.

    The two ends are the builds with the highest and the lowest pool rate in
    the build run's record, fixed before any model. The mean realised rate of
    each build's shared draws is returned beside it; where the draws rank the
    ends otherwise, the ends they pick are returned as ``draw_ranking``, a
    second reading that is not the criterion.

    Returns the builds, both rates, the two ends, the models read, the models
    left out and why, the shared seeds, and the two contexts as cohorts of
    the metrics module — the outcomes of each draw carried as a seeded vector
    beside every model's probabilities, so that one row index and one draw
    reach them all. ``reason`` is set when there is nothing to read.
    """
    builds = sorted({b for (b, a, _, _) in cells if a == arm})
    seeded: dict[str, dict[str, set[int]]] = {}
    for (build, a, model, seed) in cells:
        if a == arm and seed is not None:
            seeded.setdefault(model, {}).setdefault(build, set()).add(seed)
    out: dict = {"arm": arm, "builds": builds, "reason": None}
    if len(builds) < 2:
        out["reason"] = f"one build on arm {arm}; H5 compares two contexts"
        return out
    if pools is None:
        raise SystemExit(f"arm {arm} holds {len(builds)} builds; H5 ranks them by the pool rate "
                         "the build run recorded, and --builds-json is not given")
    missing = [b for b in builds if b not in pools]
    if missing:
        raise SystemExit(f"{', '.join(missing)} not in the build run's record; the pool rate "
                         "that ranks it is unknown")
    elsewhere = [b for b in builds if pools[b][0] != arm]
    if elsewhere:
        raise SystemExit(f"{', '.join(elsewhere)} is on arm {arm} in the rows and on another in "
                         "the build run's record")
    names = model_names(m for m, held in seeded.items() if set(held) == set(builds))
    out["models_not_read"] = {m: sorted(set(builds) - set(held))
                              for m, held in sorted(seeded.items()) if m not in names}
    if not names:
        out["reason"] = f"no seeded model holds every build of arm {arm}"
        return out
    common = set.intersection(*(s for m in names for s in seeded[m].values()))
    if not common:
        raise SystemExit(f"the seeded models of arm {arm} share no context seed on every build")
    seeds = sorted(common)
    first = names[0]
    pool_rate = {b: pools[b][1] for b in builds}
    draw_rate = {b: float(np.mean([cells[(b, arm, first, s)][1].mean() for s in seeds]))
                 for b in builds}
    high = max(builds, key=pool_rate.get)
    low = min(builds, key=pool_rate.get)
    draw_high = max(builds, key=draw_rate.get)
    draw_low = min(builds, key=draw_rate.get)

    def contexts(ends: tuple[str, str]) -> dict[str, mt.ScoredCohort]:
        found = {}
        for build in ends:
            sizes = {cells[(build, arm, first, s)][1].size for s in seeds}
            if len(sizes) != 1:
                raise SystemExit(f"{build}: the context draws hold different numbers of rows; "
                                 "one row index cannot reach them all")
            vectors = {OUTCOME: [cells[(build, arm, first, s)][1].astype(float) for s in seeds]}
            for model in names:
                vectors[model] = [cells[(build, arm, model, s)][2] for s in seeds]
            found[build] = mt.ScoredCohort(np.zeros(sizes.pop(), dtype=int), {}, vectors)
        return found

    second = None
    if (draw_high, draw_low) != (high, low):
        second = {"high": draw_high, "low": draw_low, "cohorts": contexts((draw_high, draw_low))}
    out.update({"models": names, "seeds": seeds, "pool_rates": pool_rate,
                "draw_rates": draw_rate, "high": high, "low": low,
                "cohorts": contexts((high, low)), "draw_ranking": second})
    return out


def h5_statistics(names: list[str], high: str, low: str):
    """Per model, the level of the highest- and the lowest-rate context and their difference."""
    def compute(cohorts):
        out: dict[str, float] = {}
        levels = {}
        for build in (high, low):
            cohort = cohorts[build]
            observed = float(cohort.scores[OUTCOME].mean())
            for model in names:
                levels[(build, model)] = observed / float(cohort.scores[model].mean())
        for model in names:
            out[f"oe_high|{model}"] = levels[(high, model)]
            out[f"oe_low|{model}"] = levels[(low, model)]
            out[f"h5|{model}"] = levels[(high, model)] - levels[(low, model)]
        return out
    return compute


def h5_records(result: dict[str, mt.Bootstrap], arm: str, high: str, low: str, ranking: str,
               **extra) -> list[dict]:
    """The rows of one H5 reading: ``ranking`` is "pool" for the criterion, "draws" beside it."""
    label = f"arm {arm}" if ranking == "pool" else f"arm {arm}, draw ranking"
    records = []
    for name, boot in result.items():
        metric, model = name.split("|", 1)
        difference = metric == "h5"
        records.append({"arm": arm, "cohorts": label, **extra, "ranking": ranking,
                        "criterion": ranking == "pool",
                        "high_build": high, "low_build": low,
                        "metric": metric, "model": model, "pair": model,
                        "known_answer": bi.base_model(model) not in TFM,
                        "is_difference": difference, **boot.as_dict(),
                        "excludes_zero": boot.excludes_zero if difference else None})
    return records


# --- the in-sample Cox slope ----------------------------------------------------------


def slope_contexts(cells, arm: str) -> dict:
    """Every build of an arm as one context for the slope's pooling, aligned for the bootstrap.

    The models read are the seeded models holding every build of the arm, and
    the seeds those every such model holds on every build. ``reason`` is set
    when there is nothing to read.
    """
    builds = sorted({b for (b, a, _, _) in cells if a == arm})
    seeded: dict[str, dict[str, set[int]]] = {}
    for (build, a, model, seed) in cells:
        if a == arm and seed is not None:
            seeded.setdefault(model, {}).setdefault(build, set()).add(seed)
    names = model_names(m for m, held in seeded.items() if set(held) == set(builds))
    out: dict = {"arm": arm, "builds": builds, "reason": None,
                 "models_not_read": {m: sorted(set(builds) - set(held))
                                     for m, held in sorted(seeded.items()) if m not in names}}
    if not names:
        out["reason"] = f"no seeded model holds every build of arm {arm}"
        return out
    common = set.intersection(*(s for m in names for s in seeded[m].values()))
    if not common:
        raise SystemExit(f"the seeded models of arm {arm} share no context seed on every build")
    seeds = sorted(common)
    first = names[0]
    found = {}
    for build in builds:
        sizes = {cells[(build, arm, first, s)][1].size for s in seeds}
        if len(sizes) != 1:
            raise SystemExit(f"{build}: the context draws hold different numbers of rows; "
                             "one row index cannot reach them all")
        vectors = {OUTCOME: [cells[(build, arm, first, s)][1].astype(float) for s in seeds]}
        for model in names:
            vectors[model] = [cells[(build, arm, model, s)][2] for s in seeds]
        found[build] = mt.ScoredCohort(np.zeros(sizes.pop(), dtype=int), {}, vectors)
    out.update({"models": names, "seeds": seeds, "cohorts": found})
    return out


def fitted_slope(outcome, score) -> float:
    """The Cox slope, NaN where the fit did not finish or cannot be fitted."""
    try:
        fit = mt.cox(outcome, score)
    except mt.MetricError:
        return float("nan")
    return fit.slope if fit.converged else float("nan")


def slope_statistics(names: list[str], builds: list[str]):
    """Per model, the mean over builds of its in-sample Cox slope.

    A build on which some model's fit did not finish leaves the mean for
    every model, as a Cox statistic's cell does in the interval scripts, and
    the count left out is returned beside.
    """
    def compute(cohorts):
        values = np.array([[fitted_slope(cohorts[b].scores[OUTCOME], cohorts[b].scores[m])
                            for b in builds] for m in names], dtype=float)
        keep = np.isfinite(values).all(axis=0)
        out: dict[str, float] = {}
        for i, model in enumerate(names):
            out[f"slope|{model}"] = float(values[i, keep].mean()) if keep.any() else float("nan")
        out[f"{bi.LEFT_OUT}|slope"] = float((~keep).sum())
        return out
    return compute


def slope_records(result: dict[str, mt.Bootstrap], arm: str, builds: list[str],
                  **extra) -> list[dict]:
    """The rows of one arm's in-sample slope: each model's mean with where its interval sits."""
    left = result[f"{bi.LEFT_OUT}|slope"]
    records = []
    for name, boot in result.items():
        metric, model = name.split("|", 1)
        if metric != "slope":
            continue
        records.append({"arm": arm, "cohorts": f"arm {arm}", **extra, "builds": len(builds),
                        "metric": "in_sample_cox_slope", "model": model,
                        **boot.as_dict(),
                        "above_one": bool(boot.lo > 1.0), "below_one": bool(boot.hi < 1.0),
                        "builds_left_out": left.value,
                        "builds_left_out_largest": float(max(left.draws))})
    return records


# --- the cohort cells and the figure --------------------------------------------------


def cohort_cells(dirs: list[Path], drop: list[str]) -> pd.DataFrame:
    """Every out-of-sample cell's rows, defaults and mean probability, from the scores."""
    parts = []
    for directory in dirs:
        scores = pd.read_parquet(directory / "scores.parquet", columns=SCORE_COLUMNS)
        if drop:
            scores = scores[~scores["model"].isin(drop)]
        grouped = scores.groupby(KEY_COLUMNS + ["cohort"], dropna=False, sort=True).agg(
            rows=("outcome", "size"), defaults=("outcome", "sum"), mean_pd=("pd", "mean"))
        parts.append(grouped.reset_index())
    table = pd.concat(parts, ignore_index=True)
    if table[KEY_COLUMNS + ["cohort"]].duplicated().any():
        raise SystemExit("the same cohort cell is scored in more than one directory")
    table["realised_rate"] = table["defaults"] / table["rows"]
    return table


def plot_level(table: pd.DataFrame, cohorts: pd.DataFrame | None, out: Path) -> int:
    """Mean predicted probability against realised rate, both axes log, one panel per model.

    The in-sample cells are filled, coloured by arm, a fitted model's
    training pool drawn as a diamond and a context draw as a circle; the
    cohort cells, when given, are small hollow grey circles. Returns how many
    cohort cells were left off for holding no default.
    """
    names = model_names(table["model"])
    columns = min(4, len(names))
    lines = math.ceil(len(names) / columns)
    fig, axes = plt.subplots(lines, columns, figsize=(4.3 * columns, 4.1 * lines), squeeze=False)
    unplaced = 0
    for ax, model in zip(axes.flat, names):
        values: list[float] = []
        if cohorts is not None:
            sub = cohorts[cohorts["model"] == model]
            placed = sub[sub["defaults"] > 0]
            unplaced += int(len(sub) - len(placed))
            ax.scatter(placed["realised_rate"], placed["mean_pd"], s=9, facecolors="none",
                       edgecolors="#8C8C8C", linewidths=0.6, label="a cohort cell, out of sample")
            values += list(placed["realised_rate"]) + list(placed["mean_pd"])
        sub = table[table["model"] == model]
        for (arm, kind), part in sub.groupby(["arm", "kind"], sort=True):
            marker = "D" if kind == "training pool" else "o"
            ax.scatter(part["realised_rate"], part["mean_pd"], s=30, marker=marker,
                       color=ARM_COLOUR.get(arm, "#4B3F8F"), edgecolors="black", linewidths=0.4,
                       zorder=3, label=f"in sample, arm {arm}, {kind}")
            values += list(part["realised_rate"]) + list(part["mean_pd"])
        positive = [v for v in values if v > 0]
        lo, hi = min(positive) / 1.4, max(positive) * 1.4
        ax.plot([lo, hi], [lo, hi], color="black", linewidth=0.8, linestyle=":",
                label="identity: calibrated in the large")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_title(bi.describe(model), fontsize=9)
        ax.set_xlabel("realised default rate of the cell", fontsize=8)
        ax.set_ylabel("mean predicted probability", fontsize=8)
        ax.grid(alpha=0.3, which="both")
    for ax in list(axes.flat)[len(names):]:
        ax.set_visible(False)
    seen: dict[str, object] = {}
    for ax in list(axes.flat)[:len(names)]:
        for handle, text in zip(*ax.get_legend_handles_labels()):
            seen.setdefault(text, handle)
    fig.legend(seen.values(), seen.keys(), loc="lower center", ncol=min(len(seen), 4),
               frameon=False, fontsize=8)
    fig.suptitle("the level across prevalence: mean predicted probability against realised rate, "
                 "one marker per cell", fontsize=11)
    fig.tight_layout(rect=(0, 0.04 + 0.03 * math.ceil(len(seen) / 4), 1, 0.95))
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return unplaced


# --- the command ----------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dirs", type=Path, nargs="+",
                        help="directories holding reference.parquet: classical score runs and "
                             "foundation-model runs, any number of builds and both arms")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--drop", default="",
                        help="comma-separated model names to leave out of everything")
    parser.add_argument("--builds-json", type=Path, default=None,
                        help="the build run's builds.json, whose pool rates rank each arm's "
                             "builds for H5; required when an arm holds more than one build")
    parser.add_argument("--with-cohorts", action="store_true",
                        help="draw the out-of-sample cohort cells from the directories' scores "
                             "beside the in-sample cells")
    parser.add_argument("--resamples", type=int, default=mt.RESAMPLES)
    parser.add_argument("--seed", type=int, default=bi.BOOTSTRAP_SEED)
    parser.add_argument("--check-seeds", default="",
                        help="comma-separated bootstrap seeds to repeat H5 under; the rows whose "
                             "star changes with the seed are named")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.time()
    drop = [m for m in args.drop.split(",") if m]
    check_seeds = [int(s) for s in args.check_seeds.split(",") if s.strip()]
    if args.seed in check_seeds:
        raise SystemExit(f"--check-seeds repeats the primary seed {args.seed}")

    cells, _origin = load_contexts(args.dirs, drop)
    contexts = check_contexts(cells)
    builds = sorted({b for (b, _, _, _) in cells})
    print(f"sources               : {len(args.dirs)} directories, {len(builds)} builds: "
          f"{', '.join(builds)}")
    print(f"context cells         : {len(cells)}, {sum(c[1].size for c in cells.values()):,} rows")
    print(f"context check         : {contexts['draws']} context draws, {contexts['pairs_compared']} "
          "model pairs with identical rows and outcomes")

    stage = time.time()
    table = cell_table(cells, args.resamples, args.seed)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"per-cell bootstrap    : {args.resamples} resamples per cell in {time.time() - stage:.0f}s")
    fitted = table[table["fitted"]]
    off = fitted[~fitted["bootstrap_holds_one"]]
    print(f"known answer          : {len(fitted) - len(off)} of {len(fitted)} fitted-model cells "
          "read one inside their bootstrap interval")
    for row in off.itertuples():
        print(f"  {row.build_id} {bi.cell_key(row.model, row.context_seed)}: the interval does not "
              "hold one")
    known = table[table["slope_known_answer"].notna()]
    wrong = known[~known["slope_known_answer"].astype(bool)]
    print(f"known answer, Cox     : {len(known) - len(wrong)} of {len(known)} {KNOWN_SLOPE_MODEL} "
          f"pool cells read slope one and intercept zero within {SLOPE_TOLERANCE:g}")
    for row in wrong.itertuples():
        print(f"  {row.build_id} {row.model}: slope {row.cox_slope:.8f}, intercept "
              f"{row.cox_intercept:+.8f}; the run is wrong")

    print("\nper cell (rows, realised rate, mean probability, O/E [binomial] [bootstrap]):")
    for row in table.itertuples():
        print(f"  {row.build_id:<9} {bi.cell_key(row.model, row.context_seed):<20} "
              f"{row.rows:>8,} {row.realised_rate:.4f} {row.mean_pd:.4f} "
              f"{row.observed_over_expected:.3f} [{row.binomial_lo:.3f}, {row.binomial_hi:.3f}] "
              f"[{row.bootstrap_lo:.3f}, {row.bootstrap_hi:.3f}]")

    pools = pool_rates(args.builds_json) if args.builds_json else None
    records, repeats, arms = [], [], {}
    for arm in sorted({a for (_, a, _, _) in cells}):
        context = arm_contexts(cells, arm, pools)
        arms[arm] = {k: v for k, v in context.items() if k not in ("cohorts", "draw_ranking")}
        if context["reason"]:
            print(f"\nH5, arm {arm}: {context['reason']}")
            continue
        second = context["draw_ranking"]
        arms[arm]["draw_ranking"] = (None if second is None
                                     else {"high": second["high"], "low": second["low"]})
        readings = [("pool", context["high"], context["low"], context["cohorts"])]
        if second is not None:
            readings.append(("draws", second["high"], second["low"], second["cohorts"]))
        stage = time.time()
        for ranking, high, low, contexts in readings:
            statistics = h5_statistics(context["models"], high, low)
            result = mt.cohort_blocked_bootstrap_many(contexts, statistics,
                                                      resamples=args.resamples, seed=args.seed)
            records += h5_records(result, arm, high, low, ranking)
            for check_seed in check_seeds:
                again = mt.cohort_blocked_bootstrap_many(contexts, statistics,
                                                         resamples=args.resamples,
                                                         seed=check_seed)
                repeats += [r for r in h5_records(again, arm, high, low, ranking,
                                                  bootstrap_seed=check_seed)
                            if r["is_difference"]]
        pool, draws = context["pool_rates"], context["draw_rates"]
        print(f"\nH5, arm {arm}: the criterion's contexts by the build run's pool rate, highest "
              f"{context['high']} (pool {pool[context['high']]:.4f}, draws "
              f"{draws[context['high']]:.4f}), lowest {context['low']} (pool "
              f"{pool[context['low']]:.4f}, draws {draws[context['low']]:.4f}); seeds "
              f"{context['seeds']}; {args.resamples} resamples in {time.time() - stage:.0f}s")
        if second is not None:
            print(f"  the draws' mean rate ranks the ends {second['high']} and {second['low']}: "
                  "H5 under that ranking is reported beside, not a criterion")
        for model, left in context["models_not_read"].items():
            print(f"  {model} not read: holds no context on {', '.join(left)}")

    ends = {(a["high"], "high") for a in arms.values() if a.get("high")} | {
        (a["low"], "low") for a in arms.values() if a.get("low")}
    table["h5_context"] = [next((end for build, end in ends if build == b), None)
                           for b in table["build_id"]]
    table.to_csv(args.out_dir / "cells.csv", index=False)

    h5 = pd.DataFrame(records)
    checked: dict | None = None
    checked_draws: dict | None = None
    sensitive: set[tuple[str, str]] = set()
    if not h5.empty:
        h5.to_csv(args.out_dir / "h5.csv", index=False)
        if repeats:
            repeats_df = pd.DataFrame(repeats)
            primary = h5[h5["is_difference"]]
            # The criterion's rows are checked on their own, the draw ranking's apart,
            # so that the counts of the check are the criterion's.
            criterion = primary["criterion"].astype(bool)
            repeated = repeats_df["criterion"].astype(bool)
            checked = bi.seed_check(primary[criterion], repeats_df[repeated])
            changed = list(checked["star_changed"])
            if (~criterion).any():
                checked_draws = bi.seed_check(primary[~criterion], repeats_df[~repeated])
                changed += checked_draws["star_changed"]
            sensitive = {(c["cohorts"], c["pair"]) for c in changed}
            pd.concat([primary.assign(bootstrap_seed=args.seed)[repeats_df.columns], repeats_df],
                      ignore_index=True).to_csv(args.out_dir / "h5-seeds.csv", index=False)
        print("\nH5: O/E of the highest-rate context minus the lowest's (value [lo, hi], "
              "* excludes zero" + (", ? star changes with the bootstrap seed" if checked else "")
              + "); a model@t1 row is the reading at 1.0:")
        for (label, model), rows in h5.groupby(["cohorts", "model"], sort=False):
            row = rows.set_index("metric")
            diff = row.loc["h5"]
            flag = ("*" if diff.excludes_zero else " ") + (
                "?" if (label, model) in sensitive else " ")
            note = "  known answer" if bool(diff.known_answer) else ""
            if not bool(diff.criterion):
                note += "  draw ranking, not a criterion"
            print(f"  {label:<24} {model:<11} high {row.loc['oe_high'].value:.3f}  low "
                  f"{row.loc['oe_low'].value:.3f}  {diff.value:+.3f} [{diff.ci_lo:+.3f}, "
                  f"{diff.ci_hi:+.3f}] {flag}{note}")

    slope_rows, slope_repeats, slope_arms = [], [], {}
    for arm in sorted({a for (_, a, _, _) in cells}):
        context = slope_contexts(cells, arm)
        slope_arms[arm] = {k: v for k, v in context.items() if k != "cohorts"}
        if context["reason"]:
            print(f"\nin-sample Cox slope, arm {arm}: {context['reason']}")
            continue
        stage = time.time()
        statistics = slope_statistics(context["models"], context["builds"])
        result = mt.cohort_blocked_bootstrap_many(context["cohorts"], statistics,
                                                  resamples=args.resamples, seed=args.seed)
        slope_rows += slope_records(result, arm, context["builds"])
        for check_seed in check_seeds:
            again = mt.cohort_blocked_bootstrap_many(context["cohorts"], statistics,
                                                     resamples=args.resamples, seed=check_seed)
            slope_repeats += slope_records(again, arm, context["builds"],
                                           bootstrap_seed=check_seed)
        print(f"\nin-sample Cox slope, arm {arm}: the mean over {len(context['builds'])} builds, "
              f"seeds {context['seeds']}; {args.resamples} resamples in "
              f"{time.time() - stage:.0f}s")
        for model, left in context["models_not_read"].items():
            print(f"  {model} not read: holds no context on {', '.join(left)}")
    slope_changed: list[dict] = []
    if slope_rows:
        slopes = pd.DataFrame(slope_rows)
        slopes.to_csv(args.out_dir / "in-sample-slope.csv", index=False)
        if slope_repeats:
            again = pd.DataFrame(slope_repeats)
            for row in slopes.itertuples():
                same = again[(again["arm"] == row.arm) & (again["model"] == row.model)]
                moved = (same["above_one"] != row.above_one) | (same["below_one"] != row.below_one)
                if moved.any():
                    slope_changed.append({"arm": row.arm, "model": row.model})
            pd.concat([slopes.assign(bootstrap_seed=args.seed)[again.columns], again],
                      ignore_index=True).to_csv(args.out_dir / "in-sample-slope-seeds.csv",
                                                index=False)
        print("\nin-sample Cox slope, each model's mean over the arm's builds (value [lo, hi], "
              "> or < one beyond the interval"
              + (", ? side changes with the bootstrap seed" if slope_repeats else "")
              + "); above one is confounded with the pull toward a row's own label:")
        changed = {(c["arm"], c["model"]) for c in slope_changed}
        for row in slopes.itertuples():
            side = ">" if row.above_one else ("<" if row.below_one else " ")
            flag = side + ("?" if (row.arm, row.model) in changed else " ")
            left = f"  {row.builds_left_out:g} builds left out" if row.builds_left_out else ""
            print(f"  arm {row.arm} {row.model:<11} {row.value:.4f} [{row.ci_lo:.4f}, "
                  f"{row.ci_hi:.4f}] {flag}{left}")

    cohort_table = None
    unplaced = 0
    if args.with_cohorts:
        stage = time.time()
        cohort_table = cohort_cells(args.dirs, drop)
        cohort_table.to_csv(args.out_dir / "cohort-cells.csv", index=False)
        print(f"\ncohort cells          : {len(cohort_table)} read in {time.time() - stage:.0f}s")
    unplaced = plot_level(table, cohort_table, args.out_dir / "level-prevalence.png")
    if unplaced:
        print(f"  {unplaced} cohort cells hold no default and are not on the log axes")

    summary = {
        "sources": [d.as_posix() for d in args.dirs],
        "builds": builds,
        "models_dropped": drop,
        "context_cells": len(cells),
        "context_rows": int(sum(c[1].size for c in cells.values())),
        "context_check": contexts,
        "known_answer": {
            "statement": "a model fitted by likelihood reads observed over expected of one on "
                         "its own training rows; its cells are read as the check",
            "fitted_cells": len(fitted),
            "interval_holds_one": int(len(fitted) - len(off)),
            "interval_does_not_hold_one": [f"{r.build_id} {bi.cell_key(r.model, r.context_seed)}"
                                           for r in off.itertuples()]},
        "per_cell": {"observed_over_expected": "observed defaults over the sum of the "
                                               "probabilities on the cell's rows",
                     "cox": "logit P(y) = intercept + slope * logit(p) on the cell's rows, Wald "
                            "intervals; h5_context marks the builds H5 reads as an arm's ends",
                     "binomial": "Clopper-Pearson on the count over the expected rate, the "
                                 "metrics module's interval",
                     "bootstrap": "percentile interval of the ratio over resamples of the "
                                  "cell's rows"},
        "h5": {"arms": arms,
               "statistic": "per seeded model, observed over expected on the highest-rate "
                            "context of the arm minus that on the lowest-rate context; the two "
                            "builds are the highest and lowest pool rate of the build run's "
                            "record; the rows whose ranking is 'draws' rank by the mean "
                            "realised rate of the shared draws and are not a criterion",
               "builds_json": None if args.builds_json is None else args.builds_json.as_posix(),
               "bootstrap": {"resamples": args.resamples, "seed": args.seed, "alpha": mt.ALPHA,
                             "blocking": "one row index per context, applied to its outcomes "
                                         "and every model's probabilities",
                             "context_draw": "one seed per resample for both builds and every "
                                             "model",
                             "seed_check": checked,
                             "seed_check_draw_ranking": checked_draws},
               "known_answer": "the rows of fitted seeded models (GBM-50k) are zero by "
                               "construction"},
        "in_sample_slope": {
            "arms": slope_arms,
            "statistic": "per seeded model holding every build of the arm, the mean over the "
                         "builds of the Cox slope on its context rows; a build on which some "
                         "model's fit did not finish leaves the mean for every model",
            "bootstrap": {"resamples": args.resamples, "seed": args.seed, "alpha": mt.ALPHA,
                          "blocking": "one row index per context, applied to its outcomes and "
                                      "every model's probabilities",
                          "context_draw": "one seed per resample for every build and model",
                          "check_seeds": check_seeds, "side_changed": slope_changed},
            "known_answer": {
                "statement": f"the {KNOWN_SLOPE_MODEL}, an unpenalised logistic model with an "
                             "intercept, reads Cox slope one and intercept zero on its own pool "
                             f"to within {SLOPE_TOLERANCE:g}",
                "cells": len(known),
                "within_tolerance": int(len(known) - len(wrong)),
                "not_within": [f"{r.build_id} {r.model}" for r in wrong.itertuples()]},
            "reading": "one-sided: a slope above one is smoothing, the pull toward a row's own "
                       "label, or both; a slope below one beyond its interval is over-dispersion "
                       "on the rows the model conditions on"},
        "cohort_cells": None if cohort_table is None else {
            "cells": len(cohort_table), "without_a_default": unplaced},
        "wall_seconds": round(time.time() - started, 1),
    }
    # The run's manifest pins the paths named on its command line; the reference and score
    # files read sit inside the directories named there, so each is hashed here.
    inputs = [*args.dirs, *(p for p in (args.builds_json,) if p is not None)]
    hashed = {}
    for path in inputs:
        for item in sorted(path.rglob("*") if path.is_dir() else [path]):
            if item.is_file():
                hashed[item.as_posix()] = rr.file_hash(item)
    (args.out_dir / "inputs.json").write_text(json.dumps(hashed, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str),
                                               encoding="utf-8")
    print(f"\nwall                  : {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
