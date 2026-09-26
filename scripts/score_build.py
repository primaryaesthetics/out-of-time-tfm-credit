#!/usr/bin/env python3
"""Fits the classical models on one build and keeps every score they produce.

The grid runs record a number per cohort, and a number per cohort is not
enough to put an interval on anything: the cohort-blocked bootstrap of the
metrics module resamples rows, so it needs the row-level scores of every model
on the shared scoring sample. This script fits the scorecard, the full-pool GBM
and the fifty-thousand-row control on one build and writes the score of every
scored row and of every training row, so that the intervals can be computed,
recomputed and audited without refitting anything.

Two parquet files come out. `scores.parquet` holds one row per (model, context
seed, scored row) with the outcome and the predicted probability; the row is a
position in the loaded book, the same for every model, which is what makes the
comparison paired. `reference.parquet` holds the same models' scores on the
rows they were fitted on — the training pool for a fitted model, the context
sample for the control — which is the reference distribution the stability
index reads against. A foundation model scored on the same rows appends to the
first file and its context sample to the second; the metrics script reads
whatever models the files hold.

When the recorded grid runs are given, every cohort aggregate this script
computes is checked against the one they recorded and the largest gap is
written out: the same build on the same commit has to land on the same
numbers, and the check is cheaper than an argument.

With `--control-refit` naming a recorded score run of the same build, only the
control is fitted, at that run's full-GBM point, with its early-stopping tail
sized by row share alone and no cap on the number of quarters, and written as
`gbm-50k@share`. Where the cap never bound, the refit reproduces the recorded
control's scores exactly.

    python scripts/record_run.py lc-2015h1e-scores -- \\
        python scripts/score_build.py data/raw/accepted_2007_to_2018Q4.csv.gz \\
            --out-dir experiments/2026-09-05-lc-2015h1e-scores \\
            --expect-scorecard experiments/2026-09-04-lc-scorecard-byvalue3/cohorts.csv \\
            --expect-gbm experiments/2026-09-04-lc-gbm-wide2/cohorts.csv
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from outoftime import gbm as gb
from outoftime import metrics as mt
from outoftime import scorecard as sc
from outoftime.features import (
    CALENDAR_CARRIERS,
    DATE_TO_DURATION,
    FINE_GEOGRAPHY,
    FREE_TEXT,
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
    CONTEXT_SEEDS,
    LABEL_LAG_MONTHS,
    TEST_SAMPLE_SEED,
    Quarter,
    builds,
)

MONTH_YEAR = "%b-%Y"
SCORECARD = "scorecard"
FULL = "gbm"
CONTEXT = "gbm-50k"
# The control refitted with its early-stopping tail sized by row share alone: the fewest latest
# quarters holding the policy's share of the draw's rows, never more than half the quarters, the
# four-quarter cap lifted (EXP-005, note of 2026-09-17). Its point is the recorded full GBM's.
CONTROL_REFIT = "gbm-50k@share"
SHARE_TAIL_POLICY = dataclasses.replace(gb.DEFAULT_POLICY, validation_quarters_max=10_000)


def refit_point(recorded: Path, build_id: str) -> dict:
    """The full GBM's chosen point from a recorded score run of the same build, checked against
    the point every recorded control fit of that run inherited."""
    record = json.loads((recorded / "build.json").read_text(encoding="utf-8"))
    if record["build"]["build_id"] != build_id:
        raise SystemExit(f"{recorded.as_posix()} records {record['build']['build_id']}, "
                         f"not {build_id}")
    knobs = gb.DEFAULT_POLICY.grid()[0]
    point = {k: record["units"][FULL]["summary"]["params"][k] for k in knobs}
    for tag, unit in record["units"].items():
        if unit["model"] == CONTEXT and {k: unit["summary"]["params"][k] for k in knobs} != point:
            raise SystemExit(f"{recorded.as_posix()}: {tag} was not fitted at the full GBM's point")
    return point


def raw_columns() -> list[str]:
    """What the matrix, the three gates and the label read."""
    needed = set(feature_names()) - set(DATE_TO_DURATION.values())
    needed |= set(DATE_TO_DURATION) | set(REDUNDANT) | set(REDUNDANT.values())
    needed |= {AXIS} | set(LABEL_SOURCES) | FREE_TEXT | FINE_GEOGRAPHY
    needed |= set(CALENDAR_CARRIERS) | set(LATE_COVERAGE) | set(VALUE_CARRIERS)
    return sorted(needed)


def load(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, usecols=raw_columns(), low_memory=False)
    for column in (AXIS, "last_pymnt_d"):
        frame[column] = pd.to_datetime(frame[column], format=MONTH_YEAR, errors="coerce")
    return frame.dropna(subset=[AXIS]).reset_index(drop=True)


def to_dates(series: pd.Series) -> list[dt.date | None]:
    return [None if pd.isna(v) else v.date() for v in series]


def age_in_quarters(as_of: dt.date, cohort: Quarter) -> int:
    built = Quarter.of(as_of)
    return (cohort.year * 4 + cohort.quarter) - (built.year * 4 + built.quarter)


def cohort_aggregates(outcome: np.ndarray, predicted: np.ndarray) -> dict:
    """The per-cohort numbers the grid runs recorded, for the check against them."""
    area = mt.auc(outcome, predicted)
    return {
        "rows": int(outcome.size),
        "defaults": int(outcome.sum()),
        "auc": round(area, 6),
        "gini": round(2 * area - 1, 6),
        "ks": round(mt.ks(outcome, predicted), 6),
        "brier": round(mt.brier(outcome, predicted), 8),
        "observed_rate": round(float(outcome.mean()), 6),
        "expected_rate": round(float(predicted.mean()), 6),
        "observed_over_expected": round(float(outcome.mean() / predicted.mean()), 6),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--as-of", type=dt.date.fromisoformat, default=dt.date(2015, 6, 30),
                        help="the build's as-of date")
    parser.add_argument("--arm", default="E", choices=("E", "R"))
    parser.add_argument("--seeds", default=",".join(str(s) for s in CONTEXT_SEEDS),
                        help="context seeds for the fifty-thousand-row control")
    parser.add_argument("--expect-scorecard", type=Path, default=None,
                        help="cohorts.csv of the recorded scorecard grid run to check against")
    parser.add_argument("--expect-gbm", type=Path, default=None,
                        help="cohorts.csv of the recorded GBM grid run to check against")
    parser.add_argument("--n-jobs", type=int, default=-1)
    parser.add_argument("--control-refit", type=Path, default=None,
                        help="a recorded score run of this build: fit only the control, at that "
                             f"run's full GBM point, with the share-sized tail, as {CONTROL_REFIT}")
    return parser.parse_args(argv)


def check_against(recorded: Path, computed: pd.DataFrame, build_id: str, *, model: str | None,
                  keys: tuple[str, ...] = ("gini", "ks", "brier", "observed_over_expected")) -> dict:
    """The largest gap, per aggregate, between this run and the recorded one."""
    expected = pd.read_csv(recorded)
    expected = expected[expected["build_id"] == build_id]
    on = ["cohort"]
    if model is not None:
        expected = expected[expected["model"] == model]
        if expected["context_seed"].notna().any():
            expected = expected.assign(context_seed=expected["context_seed"].astype("Int64"))
            on = ["cohort", "context_seed"]
    merged = computed.merge(expected, on=on, suffixes=("", "_recorded"))
    if merged.empty:
        raise SystemExit(f"{recorded} holds no rows for {build_id} / {model}")
    gaps = {key: float(np.abs(merged[key] - merged[f"{key}_recorded"]).max()) for key in keys}
    return {"recorded": recorded.as_posix(), "cells": len(merged), "max_gap": gaps}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.control_refit is not None and (args.expect_scorecard or args.expect_gbm):
        raise SystemExit("--control-refit fits the control alone; there is no scorecard or full "
                         "GBM to check against a recorded grid")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    seeds = tuple(int(v) for v in args.seeds.split(",") if v.strip())

    started = time.time()
    frame = load(args.data)
    snapshot = frame["last_pymnt_d"].max().date()
    origination = to_dates(frame[AXIS])
    definition = LabelDefinition(window_months=LABEL_LAG_MONTHS, snapshot=snapshot)
    labelled = build_labels(
        origination=origination, status=list(frame["loan_status"]),
        last_payment=to_dates(frame["last_pymnt_d"]), definition=definition,
    )
    labels: list[int | None] = [None] * len(origination)
    for index, value in zip(labelled.indices, labelled.labels):
        labels[index] = value
    outcome = np.asarray([-1 if v is None else v for v in labels])

    gates = {
        "redundancy": redundancy_report(frame),
        "coverage": coverage_report(frame),
        "values": value_report(frame),
    }
    matrix = model_matrix(frame)
    del frame
    print(f"rows                  : {len(origination):,}")
    print(f"snapshot from data    : {snapshot}")
    print(f"loaded in             : {time.time() - started:.0f}s")
    print(f"features              : {len(matrix.columns)}", flush=True)

    grid = builds(origination, as_of_dates=(args.as_of,), arm=args.arm, labels=labelled)
    (build,) = grid
    print(build.summary(), "\n", flush=True)

    # Every unit is (model, context seed, rows fitted on). The control reuses
    # the full pool's chosen point, as the grid run does.
    units: list[tuple[str, int | None, tuple[int, ...]]] = [
        (SCORECARD, None, build.train), (FULL, None, build.train),
    ]
    units += [(CONTEXT, seed, build.context(seed=seed)) for seed in seeds]
    chosen: dict | None = None
    if args.control_refit is not None:
        chosen = refit_point(args.control_refit, build.build_id)
        units = [(CONTROL_REFIT, seed, positions) for _, seed, positions in units[2:]]

    scores: list[pd.DataFrame] = []
    reference: list[pd.DataFrame] = []
    aggregates: list[dict] = []
    summaries: dict[str, dict] = {}
    for model_name, context_seed, positions in units:
        fit_started = time.time()
        if model_name == SCORECARD:
            model = sc.fit(matrix, labels, rows=positions,
                           policy=sc.ScorecardPolicy(n_jobs=args.n_jobs))
        elif model_name == CONTROL_REFIT:
            model = gb.fit(matrix, labels, origination, rows=positions, policy=SHARE_TAIL_POLICY,
                           point=chosen)
        else:
            model = gb.fit(matrix, labels, origination, rows=positions, policy=gb.DEFAULT_POLICY,
                           point=chosen if model_name == CONTEXT else None)
            if model_name == FULL:
                chosen = {knob: model.params[knob] for knob in gb.DEFAULT_POLICY.grid()[0]}
        elapsed = time.time() - fit_started
        tag = model_name if context_seed is None else f"{model_name}/{context_seed}"
        summaries[tag] = {
            "model": model_name, "context_seed": context_seed,
            "train_rows": len(positions), "pool_rows": len(build.train),
            "context_is_whole_pool": context_seed is not None and len(positions) == len(build.train),
            "fit_seconds": round(elapsed, 2),
            "summary": model.as_dict(),
        }

        fitted = model.predict_pd(matrix, rows=positions)
        reference.append(pd.DataFrame({
            "model": model_name, "context_seed": context_seed,
            "row": np.asarray(positions, dtype=np.int64), "outcome": outcome[list(positions)],
            "pd": fitted,
        }))

        for quarter, rows in build.test:
            predicted = model.predict_pd(matrix, rows=rows)
            truth = outcome[list(rows)]
            scores.append(pd.DataFrame({
                "model": model_name, "context_seed": context_seed, "cohort": str(quarter),
                "age_quarters": age_in_quarters(build.as_of, quarter),
                "row": np.asarray(rows, dtype=np.int64), "outcome": truth, "pd": predicted,
            }))
            record = cohort_aggregates(truth, predicted)
            record.update({"model": model_name, "context_seed": context_seed,
                           "cohort": str(quarter),
                           "age_quarters": age_in_quarters(build.as_of, quarter)})
            aggregates.append(record)
        youngest = [a for a in aggregates if a["model"] == model_name
                    and a["context_seed"] == context_seed]
        print(f"{tag:<18} {len(positions):>9,} rows  fit {elapsed:>6.1f}s  "
              f"gini {youngest[0]['gini']:.3f}->{youngest[-1]['gini']:.3f}  "
              f"O/E {youngest[0]['observed_over_expected']:.2f}->"
              f"{youngest[-1]['observed_over_expected']:.2f}", flush=True)

    score_frame = pd.concat(scores, ignore_index=True)
    score_frame["context_seed"] = score_frame["context_seed"].astype("Int64")
    reference_frame = pd.concat(reference, ignore_index=True)
    reference_frame["context_seed"] = reference_frame["context_seed"].astype("Int64")
    for name in ("build_id", "arm", "as_of"):
        value = {"build_id": build.build_id, "arm": build.arm, "as_of": build.as_of.isoformat()}[name]
        score_frame.insert(0, name, value)
        reference_frame.insert(0, name, value)
    score_frame.to_parquet(args.out_dir / "scores.parquet", index=False)
    reference_frame.to_parquet(args.out_dir / "reference.parquet", index=False)

    cohorts = pd.DataFrame(aggregates)
    cohorts["context_seed"] = cohorts["context_seed"].astype("Int64")
    cohorts.insert(0, "build_id", build.build_id)
    cohorts.to_csv(args.out_dir / "cohorts.csv", index=False)

    checks = {}
    if args.expect_scorecard is not None:
        checks[SCORECARD] = check_against(
            args.expect_scorecard, cohorts[cohorts["model"] == SCORECARD], build.build_id,
            model=None)
    if args.expect_gbm is not None:
        for name in (FULL, CONTEXT):
            checks[name] = check_against(
                args.expect_gbm, cohorts[cohorts["model"] == name], build.build_id, model=name)
    for name, check in checks.items():
        worst = max(check["max_gap"].values())
        print(f"check {name:<12}: {check['cells']} cells against {check['recorded']}, "
              f"largest gap {worst:.2e}", flush=True)

    summary = {
        "build": build.as_dict(),
        "label": labelled.as_dict(),
        "snapshot": snapshot.isoformat(),
        "features": list(matrix.columns),
        "gates": gates,
        "seeds": {"test_sample": TEST_SAMPLE_SEED, "context": list(seeds),
                  "booster": gb.DEFAULT_POLICY.seed},
        "policy": {"scorecard": sc.ScorecardPolicy(n_jobs=args.n_jobs).as_dict(),
                   "gbm": gb.DEFAULT_POLICY.as_dict(),
                   **({CONTROL_REFIT: SHARE_TAIL_POLICY.as_dict()} if args.control_refit else {})},
        "control_refit_from": args.control_refit.as_posix() if args.control_refit else None,
        "units": summaries,
        "checks": checks,
        "scored_rows": len(score_frame),
        "reference_rows": len(reference_frame),
        "wall_seconds": round(time.time() - started, 1),
    }
    (args.out_dir / "build.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\nscored rows           : {len(score_frame):,}")
    print(f"reference rows        : {len(reference_frame):,}")
    print(f"wall                  : {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
