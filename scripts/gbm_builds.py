#!/usr/bin/env python3
"""Tunes and fits the GBM on every build of the grid, in both its variants.

Two models come out of this script and they answer different questions. The
full-pool GBM is the study's strongest classical challenger: it reads every
labelled row the builder had. The fifty-thousand-row control reads exactly the
rows a foundation model will read, three draws of them, so that a later
TFM-against-GBM difference is a difference between model classes and not
between data budgets.

Both are tuned per build against the end of that build's pool, never against a
random fold. The chosen point, the number of rounds and the held-out log-loss
are written out per build, because a control whose hyperparameters wander
across the grid is telling the study something about the book.

Point estimates only. The intervals, the Murphy decomposition and the
population-stability inference belong to the metrics module.

    python scripts/record_run.py lc-gbm-builds -- \
        python scripts/gbm_builds.py data/raw/accepted_2007_to_2018Q4.csv.gz \
            --out-dir experiments/2026-09-04-lc-gbm-builds
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
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

from outoftime import gbm as gb
from outoftime.features import (
    CALENDAR_CARRIERS,
    DATE_TO_DURATION,
    LATE_COVERAGE,
    REDUNDANT,
    VALUE_CARRIERS,
    coverage_report,
    feature_names,
    model_matrix,
    redundancy_report,
    value_report,
)
from outoftime.label import LabelDefinition, build_labels
from outoftime.lending_club import AXIS, LABEL_SOURCES
from outoftime.vintage import (
    CONTEXT_ROWS,
    CONTEXT_SEEDS,
    DEFAULT_AS_OF,
    LABEL_LAG_MONTHS,
    ROLLING_QUARTERS,
    TEST_SAMPLE_SEED,
    Quarter,
    builds,
)

MONTH_YEAR = "%b-%Y"
ARMS = {"E": "expanding", "R": f"rolling, {ROLLING_QUARTERS} quarters"}
FULL = "gbm"
CONTEXT = f"gbm-{CONTEXT_ROWS // 1000}k"
MODEL_COLOUR = {FULL: "#0E6B66", CONTEXT: "#9A5B24"}


def raw_columns() -> list[str]:
    """What the matrix, the label and the three gates on the matrix read."""
    needed = set(feature_names()) - set(DATE_TO_DURATION.values())
    needed |= set(DATE_TO_DURATION) | {AXIS} | set(LABEL_SOURCES)
    needed |= set(REDUNDANT) | set(REDUNDANT.values()) | set(CALENDAR_CARRIERS)
    needed |= set(LATE_COVERAGE) | set(VALUE_CARRIERS)
    return sorted(needed)


def load(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, usecols=raw_columns(), low_memory=False)
    for column in (AXIS, "last_pymnt_d"):
        frame[column] = pd.to_datetime(frame[column], format=MONTH_YEAR, errors="coerce")
    return frame.dropna(subset=[AXIS]).reset_index(drop=True)


def to_dates(series: pd.Series) -> list[dt.date | None]:
    return [None if pd.isna(v) else v.date() for v in series]


def auc(outcome: np.ndarray, score: np.ndarray) -> float:
    """The Mann-Whitney statistic, with ties split as the definition requires."""
    from scipy.stats import rankdata

    positives = int(outcome.sum())
    negatives = int(outcome.size - positives)
    if positives == 0 or negatives == 0:
        return float("nan")
    ranks = rankdata(score)
    return float((ranks[outcome == 1].sum() - positives * (positives + 1) / 2)
                 / (positives * negatives))


def ks(outcome: np.ndarray, score: np.ndarray) -> float:
    """The largest gap between the two cumulative score distributions."""
    order = np.argsort(score, kind="mergesort")
    ordered = outcome[order]
    positives, negatives = ordered.sum(), (1 - ordered).sum()
    if positives == 0 or negatives == 0:
        return float("nan")
    return float(np.abs(np.cumsum(ordered) / positives
                        - np.cumsum(1 - ordered) / negatives).max())


def cohort_metrics(outcome: np.ndarray, predicted: np.ndarray) -> dict:
    area = auc(outcome, predicted)
    observed = float(outcome.mean())
    expected = float(predicted.mean())
    return {
        "rows": int(outcome.size),
        "defaults": int(outcome.sum()),
        "auc": round(area, 6),
        "gini": round(2 * area - 1, 6),
        "ks": round(ks(outcome, predicted), 6),
        "brier": round(float(np.mean((predicted - outcome) ** 2)), 8),
        "observed_rate": round(observed, 6),
        "expected_rate": round(expected, 6),
        "observed_over_expected": round(observed / expected, 6) if expected else None,
    }


def age_in_quarters(as_of: dt.date, cohort: Quarter) -> int:
    """How old the model is when it scores this cohort, in quarters."""
    built = Quarter.of(as_of)
    return (cohort.year * 4 + cohort.quarter) - (built.year * 4 + built.quarter)


def score_cohorts(model, build, matrix, outcome) -> list[dict]:
    records = []
    for quarter, positions in build.test:
        predicted = model.predict_pd(matrix, rows=positions)
        metrics = cohort_metrics(outcome[list(positions)], predicted)
        metrics["cohort"] = str(quarter)
        metrics["age_quarters"] = age_in_quarters(build.as_of, quarter)
        records.append(metrics)
    return records


def fit_grid(
    matrix: pd.DataFrame,
    labels: list[int | None],
    origination: list[dt.date | None],
    labelled,
    *,
    as_of_dates,
    policy: gb.GBMPolicy,
    models: tuple[str, ...],
    seeds: tuple[int, ...],
    verbose: bool = True,
) -> dict:
    outcome = np.asarray([-1 if v is None else v for v in labels])
    summary: dict = {"arms": {}}
    for arm, name in ARMS.items():
        rows: list[dict] = []
        for build in builds(
            origination, as_of_dates=as_of_dates, arm=arm, labels=labelled
        ):
            # The full pool is tuned; each context draw then reuses its build's
            # chosen point and re-chooses only the round count, so the spread
            # across draws is the spread of the rows.
            units: list[tuple[str, int | None, tuple[int, ...]]] = [(FULL, None, build.train)]
            if CONTEXT in models:
                units += [
                    (CONTEXT, seed, build.context(seed=seed)) for seed in seeds
                ]

            chosen: dict | None = None
            for model_name, context_seed, positions in units:
                started = time.time()
                model = gb.fit(
                    matrix, labels, origination, rows=positions, policy=policy,
                    point=chosen if model_name == CONTEXT else None,
                )
                elapsed = time.time() - started
                if model_name == FULL:
                    chosen = {knob: model.params[knob] for knob in policy.grid()[0]}
                    if FULL not in models:
                        continue
                cohorts = score_cohorts(model, build, matrix, outcome)

                record = {
                    "build_id": build.build_id,
                    "as_of": build.as_of.isoformat(),
                    "arm": arm,
                    "model": model_name,
                    "context_seed": context_seed,
                    "context_is_whole_pool": (
                        context_seed is not None and len(positions) == len(build.train)
                    ),
                    "train_rows": len(positions),
                    "pool_rows": len(build.train),
                    "train_first": build.train_first.isoformat(),
                    "train_last": build.train_last.isoformat(),
                    "fit_seconds": round(elapsed, 2),
                    "model_summary": model.as_dict(),
                    "cohorts": cohorts,
                }
                rows.append(record)
                if verbose:
                    youngest, oldest = cohorts[0], cohorts[-1]
                    tag = model_name if context_seed is None else f"{model_name}/{context_seed}"
                    print(
                        f"{build.build_id:>9} {tag:<16} {len(positions):>9,} rows  "
                        f"{model.rounds:>4} rounds  fit {elapsed:>6.1f}s  "
                        f"gini {youngest['gini']:.3f}->{oldest['gini']:.3f}  "
                        f"O/E {youngest['observed_over_expected']:.2f}->"
                        f"{oldest['observed_over_expected']:.2f}",
                        flush=True,
                    )
        summary["arms"][arm] = rows
        if verbose:
            print(f"--- arm {arm}: {name} done ---\n", flush=True)
    return summary


def determinism_check(
    matrix, labels, origination, labelled, *, as_of_dates, policy
) -> dict:
    """Fits the smallest build twice and reports whether it landed identically.

    LightGBM is asked for determinism explicitly, and a library that is asked
    for it and does not deliver it is worth catching here rather than in a
    reviewer's rerun.
    """
    build = builds(origination, as_of_dates=as_of_dates[:1], arm="E", labels=labelled)[0]
    first = gb.fit(matrix, labels, origination, rows=build.train, policy=policy)
    second = gb.fit(matrix, labels, origination, rows=build.train, policy=policy)
    sample = build.test[0][1][:2000]
    gap = float(
        np.abs(first.predict_pd(matrix, rows=sample) - second.predict_pd(matrix, rows=sample)).max()
    )
    return {
        "build_id": build.build_id,
        "same_params": first.params == second.params,
        "same_rounds": first.rounds == second.rounds,
        "max_prediction_gap": gap,
    }


def write_cohorts(summary: dict, path: Path) -> None:
    fields = [
        "model", "arm", "build_id", "as_of", "context_seed", "context_is_whole_pool",
        "cohort", "age_quarters", "rows", "defaults", "auc", "gini", "ks", "brier",
        "observed_rate", "expected_rate", "observed_over_expected",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for records in summary["arms"].values():
            for record in records:
                head = {
                    key: record[key]
                    for key in (
                        "model", "arm", "build_id", "as_of", "context_seed",
                        "context_is_whole_pool",
                    )
                }
                for row in record["cohorts"]:
                    writer.writerow({**head, **row})


def write_tuning(summary: dict, path: Path) -> None:
    fields = [
        "model", "arm", "build_id", "context_seed", "context_is_whole_pool", "train_rows",
        "fit_rows", "validation_quarters", "validation_rows", "validation_logloss", "rounds",
        "num_leaves", "learning_rate", "min_child_samples", "feature_fraction",
        "fit_seconds", "notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for records in summary["arms"].values():
            for record in records:
                fitted = record["model_summary"]
                params = fitted["params"]
                writer.writerow({
                    "model": record["model"],
                    "arm": record["arm"],
                    "build_id": record["build_id"],
                    "context_seed": record["context_seed"],
                    "context_is_whole_pool": record["context_is_whole_pool"],
                    "train_rows": fitted["train_rows"],
                    "fit_rows": fitted["fit_rows"],
                    "validation_quarters": " ".join(fitted["validation_quarters"]),
                    "validation_rows": fitted["validation_rows"],
                    "validation_logloss": fitted["validation_logloss"],
                    "rounds": fitted["rounds"],
                    "num_leaves": params["num_leaves"],
                    "learning_rate": params["learning_rate"],
                    "min_child_samples": params["min_child_samples"],
                    "feature_fraction": params["feature_fraction"],
                    "fit_seconds": record["fit_seconds"],
                    "notes": " | ".join(fitted["notes"]),
                })


def write_importances(summary: dict, path: Path) -> None:
    fields = [
        "model", "arm", "build_id", "context_seed", "feature", "gain", "gain_share",
        "splits",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for records in summary["arms"].values():
            for record in records:
                head = {
                    key: record[key]
                    for key in ("model", "arm", "build_id", "context_seed")
                }
                for row in record["model_summary"]["importances"]:
                    writer.writerow({**head, **row})


def by_model(records: list[dict], model: str) -> list[dict]:
    return [record for record in records if record["model"] == model]


def seed_band(records: list[dict], build_id: str, key: str):
    """The per-cohort mean and spread across the context seeds of one build."""
    runs = [record for record in records if record["build_id"] == build_id]
    if not runs:
        return [], [], [], []
    ages = [cohort["age_quarters"] for cohort in runs[0]["cohorts"]]
    values = np.array([[cohort[key] for cohort in run["cohorts"]] for run in runs], dtype=float)
    return ages, values.mean(axis=0), values.min(axis=0), values.max(axis=0)


def plot_trajectories(summary: dict, out: Path) -> None:
    """Discrimination against model age: full pool above, context control below."""
    models = [
        model
        for model in (FULL, CONTEXT)
        if any(by_model(records, model) for records in summary["arms"].values())
    ]
    figure, panels = plt.subplots(
        len(models), len(ARMS), figsize=(13, 4.6 * len(models)), sharey=True, squeeze=False
    )
    for row, model in enumerate(models):
        for column, (arm, name) in enumerate(ARMS.items()):
            panel = panels[row][column]
            records = by_model(summary["arms"][arm], model)
            build_ids = sorted({record["build_id"] for record in records})
            shades = plt.cm.viridis(np.linspace(0, .88, len(build_ids)))
            for build_id, colour in zip(build_ids, shades):
                ages, mean, low, high = seed_band(records, build_id, "gini")
                panel.plot(ages, mean, marker="o", markersize=3.5, linewidth=1.5,
                           color=colour, label=build_id[:-2])
                if np.any(high - low > 0):
                    panel.fill_between(ages, low, high, color=colour, alpha=.22, linewidth=0)
            panel.set_title(f"{model}, arm {arm}: {name}")
            panel.grid(alpha=.25)
            if row == len(models) - 1:
                panel.set_xlabel("model age at scoring, quarters")
        panels[row][0].set_ylabel("Gini on the cohort's fixed sample")
    panels[0][-1].legend(frameon=False, fontsize=8, ncol=2, title="build")
    figure.suptitle(
        "Discrimination against model age, one line per build. Where the lines wiggle "
        "together they are scoring the same cohort, not reaching the same age.\n"
        "The band is the spread across context draws; no band, the model read the whole pool",
        y=.995, fontsize=10)
    figure.tight_layout()
    figure.savefig(out, dpi=140)
    plt.close(figure)


def plot_calibration(summary: dict, out: Path) -> None:
    """The book's realised rate against what each ageing model expected of it."""
    quarters = sorted(
        {c["cohort"] for r in summary["arms"]["E"] for c in r["cohorts"]},
        key=lambda q: (int(q[:4]), int(q[-1])),
    )
    position = {quarter: index for index, quarter in enumerate(quarters)}
    observed = {
        cohort["cohort"]: cohort["observed_rate"]
        for record in summary["arms"]["E"]
        for cohort in record["cohorts"]
    }

    figure, panels = plt.subplots(len(ARMS), 1, figsize=(13, 8.4), sharex=True)
    for panel, (arm, name) in zip(panels, ARMS.items()):
        records = summary["arms"][arm]
        for model in (FULL, CONTEXT):
            subset = by_model(records, model)
            build_ids = sorted({record["build_id"] for record in subset})
            for index, build_id in enumerate(build_ids):
                runs = [record for record in subset if record["build_id"] == build_id]
                cohorts = runs[0]["cohorts"]
                x = [position[cohort["cohort"]] for cohort in cohorts]
                y = np.mean(
                    [[cohort["expected_rate"] for cohort in run["cohorts"]] for run in runs],
                    axis=0,
                )
                panel.plot(x, y, marker="o", markersize=3, linewidth=1.2,
                           color=MODEL_COLOUR[model], alpha=.75,
                           label=model if index == 0 else None)
        panel.plot([position[q] for q in quarters], [observed[q] for q in quarters],
                   color="#20303a", linewidth=2.2, linestyle="--", label="realised")
        panel.set_ylabel(f"{summary['label_lag_months']}-month default rate")
        panel.yaxis.set_major_formatter(lambda v, _: f"{v:.1%}")
        panel.set_title(f"arm {arm}: {name}")
        panel.grid(alpha=.25)
        panel.legend(frameon=False, fontsize=9)
    panels[-1].set_xticks(range(len(quarters)))
    panels[-1].set_xticklabels(quarters, rotation=90, fontsize=7)
    panels[-1].set_xlabel("cohort scored")
    figure.suptitle(
        "Calibration in the large by cohort scored: what each build expected of every "
        "later cohort,\nagainst what the book realised. One line per build, both variants",
        y=.995, fontsize=11)
    figure.tight_layout()
    figure.savefig(out, dpi=140)
    plt.close(figure)


def plot_importance_drift(summary: dict, out: Path, top: int = 12) -> None:
    """Which columns carry the model, and whether that moves across the grid."""
    records = by_model(summary["arms"]["E"], FULL) or by_model(summary["arms"]["E"], CONTEXT)
    if not records:
        return
    build_ids = sorted({record["build_id"] for record in records})
    totals: dict[str, float] = {}
    for record in records:
        for row in record["model_summary"]["importances"]:
            totals[row["feature"]] = totals.get(row["feature"], 0.0) + row["gain_share"]
    features = [name for name, _ in sorted(totals.items(), key=lambda item: -item[1])][:top]

    grid = np.zeros((len(features), len(build_ids)))
    for column, build_id in enumerate(build_ids):
        runs = [record for record in records if record["build_id"] == build_id]
        shares: dict[str, float] = {}
        for run in runs:
            for row in run["model_summary"]["importances"]:
                shares[row["feature"]] = shares.get(row["feature"], 0.0) + row["gain_share"]
        for row_index, feature in enumerate(features):
            grid[row_index, column] = shares.get(feature, 0.0) / len(runs)

    figure, panel = plt.subplots(figsize=(11, 0.44 * len(features) + 2.6))
    image = panel.imshow(grid, aspect="auto", cmap="magma_r", vmin=0)
    panel.set_xticks(range(len(build_ids)))
    panel.set_xticklabels([build_id[:-2] for build_id in build_ids], rotation=45, fontsize=8)
    panel.set_yticks(range(len(features)))
    panel.set_yticklabels(features, fontsize=8)
    panel.set_title(
        "Share of split gain by column, expanding arm: a column that changes "
        "shade across the row is a model whose story moved")
    figure.colorbar(image, ax=panel, fraction=.025, pad=.02, label="share of gain")
    figure.tight_layout()
    figure.savefig(out, dpi=140)
    plt.close(figure)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--models", default=f"{FULL},{CONTEXT}",
        help="which variants to run, comma separated",
    )
    parser.add_argument(
        "--as-of", default="", help="comma-separated as-of dates, for a probe run",
    )
    parser.add_argument(
        "--seeds", default=",".join(str(seed) for seed in CONTEXT_SEEDS),
        help="context seeds for the fifty-thousand-row control",
    )
    parser.add_argument("--skip-determinism", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    models = tuple(name.strip() for name in args.models.split(",") if name.strip())
    unknown = [name for name in models if name not in (FULL, CONTEXT)]
    if unknown:
        raise SystemExit(f"unknown model variants: {unknown}")
    seeds = tuple(int(value) for value in args.seeds.split(",") if value.strip())
    as_of_dates = (
        tuple(dt.date.fromisoformat(value.strip()) for value in args.as_of.split(","))
        if args.as_of
        else DEFAULT_AS_OF
    )

    started = time.time()
    frame = load(args.data)
    snapshot = frame["last_pymnt_d"].max().date()
    origination = to_dates(frame[AXIS])
    definition = LabelDefinition(window_months=LABEL_LAG_MONTHS, snapshot=snapshot)
    labelled = build_labels(
        origination=origination,
        status=list(frame["loan_status"]),
        last_payment=to_dates(frame["last_pymnt_d"]),
        definition=definition,
    )
    labels: list[int | None] = [None] * len(origination)
    for index, value in zip(labelled.indices, labelled.labels):
        labels[index] = value

    # The three rules that shape the matrix are measured on this book, by this
    # run, before anything is fitted on it; each refuses a book it does not hold on.
    gates = {
        "redundancy": redundancy_report(frame),
        "coverage": coverage_report(frame),
        "values": value_report(frame),
    }
    matrix = model_matrix(frame)
    del frame
    policy = gb.DEFAULT_POLICY

    print(f"rows                  : {len(origination):,}")
    print(f"snapshot from data    : {snapshot}")
    print(f"loaded in             : {time.time() - started:.0f}s")
    print(f"features              : {len(matrix.columns)}")
    print(f"labelled              : {labelled.size:,}")
    print(f"search points per fit : {len(policy.grid())}")
    print(f"variants              : {', '.join(models)}\n", flush=True)

    summary = fit_grid(
        matrix, labels, origination, labelled,
        as_of_dates=as_of_dates, policy=policy, models=models, seeds=seeds,
    )
    summary["label_lag_months"] = LABEL_LAG_MONTHS
    summary["label"] = definition.as_dict()
    summary["snapshot"] = snapshot.isoformat()
    summary["policy"] = policy.as_dict()
    summary["features"] = list(matrix.columns)
    summary["gates"] = gates
    summary["context_seeds"] = list(seeds)
    summary["seeds"] = {"test_sample": TEST_SAMPLE_SEED, "context": list(seeds),
                        "booster": policy.seed}
    summary["tuning_budget"] = (
        f"{len(policy.grid())} search points per full-pool build, early stopping on the "
        f"latest quarters of the pool; the context control reuses its build's chosen "
        f"point and re-chooses only the round count"
    )
    summary["entity_check"] = (
        "not run: the file carries no borrower key (member_id is null on every "
        "row and id is the loan), so a repeat borrower can sit in a training "
        "pool and in a scored cohort undetected"
    )
    summary["as_of_dates"] = [date.isoformat() for date in as_of_dates]
    if not args.skip_determinism:
        summary["determinism"] = determinism_check(
            matrix, labels, origination, labelled,
            as_of_dates=as_of_dates, policy=policy,
        )
        print(f"determinism check     : {summary['determinism']}", flush=True)

    write_cohorts(summary, args.out_dir / "cohorts.csv")
    write_tuning(summary, args.out_dir / "tuning.csv")
    write_importances(summary, args.out_dir / "importances.csv")
    (args.out_dir / "gbm.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    plot_trajectories(summary, args.out_dir / "gini-trajectory.png")
    plot_calibration(summary, args.out_dir / "calibration-drift.png")
    plot_importance_drift(summary, args.out_dir / "importance-drift.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
