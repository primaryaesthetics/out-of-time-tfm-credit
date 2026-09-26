#!/usr/bin/env python3
"""Runs the published benchmark's protocol on one build's training pool.

The credit foundation-model benchmark ranks models on random five-fold
cross-validation, tunes on a random fifth of each training fold by AUC, and
chooses the threshold that maximises F1 on that fifth. This script runs that
recipe on the study's own matrix and models, on the training pool of one
build of the vintage grid, so that the two protocols can be read on the same
rows. It is the one place in this repository where a split is random by
design: the folds are the thing being measured, and they are written to the
run directory so that they can be checked rather than caught.

Per fold, the training part is split again at random, four fifths to fit and
one fifth to validate. The scorecard is fitted on the four fifths. The GBM
searches the study's grid with the search point chosen on the fifth by AUC,
stops on the fifth, and ships the model fitted on the four fifths, not a
refit on every row, so that the threshold chosen on the fifth is chosen on
rows the shipped model never saw. The control takes the full model's point
on a 50,000-row sample of the four fifths, stopped on the same fifth; that
sample is also the context a foundation model reads. Every classical model
then scores every row of the validation fifth and of the test fold, and its
F1-optimal threshold on the fifth is recorded beside them.

The foundation models are scored elsewhere. For each fold and context seed
the bundle holds the context sample and two cells of 20,000 rows drawn from
the fifth and from the test fold, in the layout `export_context.py` packs a
build in, so that the node scores them as it scores a cohort; the classical
models score those same 20,000-row samples as well, in the score file, so
that every comparison stays paired on identical rows.

    python scripts/record_run.py lc-2015h1e-folds -- \\
        python scripts/in_time_folds.py data/raw/accepted_2007_to_2018Q4.csv.gz \\
            --run-folds 1 --out-dir experiments/2026-09-12-lc-2015h1e-folds
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from score_build import CONTEXT, FULL, SCORECARD, load, to_dates

from outoftime import gbm as gb
from outoftime import metrics as mt
from outoftime import scorecard as sc
from outoftime.features import categorical_names, model_matrix
from outoftime.label import LabelDefinition, build_labels
from outoftime.lending_club import AXIS
from outoftime.vintage import CONTEXT_ROWS, CONTEXT_SEEDS, LABEL_LAG_MONTHS, builds

FOLDS = 5
FOLD_SEED = 20260912
VALIDATION_SHARE = 0.2
CELL_ROWS = 20_000
PARTS = ("validation", "test")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stratified_folds(outcome: np.ndarray, positions: np.ndarray, folds: int, seed: int
                     ) -> np.ndarray:
    """The fold of every position, drawn at random with the classes balanced across folds.

    Positions are shuffled within each class under the seed and dealt round
    the folds, so every fold holds a fifth of the defaults and a fifth of the
    rest, which is what a stratified K-fold does.
    """
    rng = np.random.default_rng(seed)
    fold_of = np.empty(positions.size, dtype=np.int64)
    for label in (0, 1):
        where = np.flatnonzero(outcome[positions] == label)
        rng.shuffle(where)
        fold_of[where] = np.arange(where.size) % folds
    return fold_of


def stratified_share(outcome: np.ndarray, positions: np.ndarray, share: float, seed: int
                     ) -> np.ndarray:
    """A random share of the positions with the classes balanced, as a boolean mask."""
    rng = np.random.default_rng(seed)
    mask = np.zeros(positions.size, dtype=bool)
    for label in (0, 1):
        where = np.flatnonzero(outcome[positions] == label)
        rng.shuffle(where)
        mask[where[: round(share * where.size)]] = True
    return mask


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--as-of", type=dt.date.fromisoformat, default=dt.date(2015, 6, 30))
    parser.add_argument("--arm", default="E", choices=("E", "R"))
    parser.add_argument("--folds", type=int, default=FOLDS)
    parser.add_argument("--fold-seed", type=int, default=FOLD_SEED)
    parser.add_argument("--run-folds", default="",
                        help="comma-separated folds to fit and score, 1-based; all by default")
    parser.add_argument("--seeds", default=",".join(str(s) for s in CONTEXT_SEEDS),
                        help="context seeds: one control fit and one context sample per seed")
    parser.add_argument("--cell-rows", type=int, default=CELL_ROWS,
                        help="rows of the validation fifth and of the test fold packed as the "
                             "foundation models' cells")
    parser.add_argument("--n-jobs", type=int, default=-1)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    seeds = tuple(int(v) for v in args.seeds.split(",") if v.strip())
    run_folds = ([int(v) for v in args.run_folds.split(",") if v.strip()]
                 or list(range(1, args.folds + 1)))
    if any(k < 1 or k > args.folds for k in run_folds):
        raise SystemExit(f"--run-folds names a fold outside 1..{args.folds}")

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
    matrix = model_matrix(frame)
    del frame
    print(f"rows                  : {len(origination):,}")
    print(f"loaded in             : {time.time() - started:.0f}s", flush=True)

    (build,) = builds(origination, as_of_dates=(args.as_of,), arm=args.arm, labels=labelled)
    print(build.summary(), "\n", flush=True)
    pool = np.asarray(build.train, dtype=np.int64)
    if (outcome[pool] < 0).any():
        raise SystemExit("a pool row carries no label; the build should have refused it")
    fold_of = stratified_folds(outcome, pool, args.folds, args.fold_seed)
    stamp = {"build_id": build.build_id, "arm": build.arm, "as_of": build.as_of.isoformat()}

    def rows_of(positions, **columns) -> pd.DataFrame:
        index = [int(v) for v in positions]
        head = pd.DataFrame({**stamp, **columns,
                             "row": np.asarray(index, dtype=np.int64),
                             "outcome": outcome[index].astype(np.int8)})
        body = matrix.iloc[index].reset_index(drop=True)
        return pd.concat([head, body], axis=1)

    scores: list[pd.DataFrame] = []
    reference: list[pd.DataFrame] = []
    contexts: list[pd.DataFrame] = []
    cells: list[pd.DataFrame] = []
    assignments: list[pd.DataFrame] = []
    thresholds: list[dict] = []
    summaries: dict[str, dict] = {}
    policy = sc.ScorecardPolicy(n_jobs=args.n_jobs)

    for k in run_folds:
        fold_started = time.time()
        test = pool[fold_of == k - 1]
        train = pool[fold_of != k - 1]
        fifth = stratified_share(outcome, train, VALIDATION_SHARE, args.fold_seed + k)
        validation = train[fifth]
        fit_rows = train[~fifth]
        parts = {"validation": validation, "test": test}
        # The 20,000-row samples the foundation models score, drawn once per
        # fold and scored by every classical model too.
        sample_rng = np.random.default_rng(args.fold_seed * 100 + k)
        samples = {part: np.sort(sample_rng.choice(rows, size=min(args.cell_rows, rows.size),
                                                   replace=False))
                   for part, rows in parts.items()}
        assignments.append(pd.DataFrame({
            "fold": k, "row": np.concatenate([fit_rows, validation, test]),
            "part": (["fit"] * fit_rows.size + ["validation"] * validation.size
                     + ["test"] * test.size)}))
        for part, rows in samples.items():
            cells.append(rows_of(rows, cohort=f"fold{k}-{part}", age_quarters=0))
        print(f"fold {k}: fit {fit_rows.size:,}  validation {validation.size:,}  "
              f"test {test.size:,}  defaults {outcome[fit_rows].mean():.4f} / "
              f"{outcome[validation].mean():.4f} / {outcome[test].mean():.4f}", flush=True)

        units: list[tuple[str, int | None, np.ndarray]] = [
            (SCORECARD, None, fit_rows), (FULL, None, fit_rows)]
        for seed in seeds:
            draw = np.random.default_rng((seed, k)).choice(
                fit_rows, size=min(CONTEXT_ROWS, fit_rows.size), replace=False)
            units.append((CONTEXT, seed, np.sort(draw)))
        chosen: dict | None = None
        for model_name, context_seed, positions in units:
            fit_started = time.time()
            if model_name == SCORECARD:
                model = sc.fit(matrix, labels, rows=positions.tolist(), policy=policy)
            else:
                model = gb.fit(
                    matrix, labels, origination,
                    rows=np.concatenate([positions, validation]).tolist(),
                    policy=gb.DEFAULT_POLICY, point=chosen if model_name == CONTEXT else None,
                    validation_rows=validation.tolist(), objective="auc", refit=False)
                if model_name == FULL:
                    chosen = {knob: model.params[knob] for knob in gb.DEFAULT_POLICY.grid()[0]}
            elapsed = time.time() - fit_started
            tag = f"fold{k}/{model_name}" + ("" if context_seed is None else f"/{context_seed}")
            summaries[tag] = {
                "fold": k, "model": model_name, "context_seed": context_seed,
                "fit_rows": int(positions.size), "validation_rows": int(validation.size),
                "fit_seconds": round(elapsed, 2), "summary": model.as_dict(),
            }
            fitted = model.predict_pd(matrix, rows=positions.tolist())
            reference.append(pd.DataFrame({
                **stamp, "fold": k, "model": model_name, "context_seed": context_seed,
                "row": positions, "outcome": outcome[positions], "pd": fitted}))
            if context_seed is not None:
                contexts.append(rows_of(positions, context_seed=context_seed, fold=k))
            on_validation = model.predict_pd(matrix, rows=validation.tolist())
            threshold = mt.f1_threshold(outcome[validation], on_validation)
            at = mt.classification_at(outcome[validation], on_validation, threshold)
            thresholds.append({"fold": k, "model": model_name, "context_seed": context_seed,
                               "threshold": threshold, "on_validation": at.as_dict()})
            for part, rows in parts.items():
                predicted = (on_validation if part == "validation"
                             else model.predict_pd(matrix, rows=rows.tolist()))
                scores.append(pd.DataFrame({
                    **stamp, "fold": k, "part": part, "model": model_name,
                    "context_seed": context_seed, "cohort": f"fold{k}-{part}",
                    "age_quarters": 0, "row": rows, "outcome": outcome[rows],
                    "pd": predicted}))
            test_scores = scores[-1]
            print(f"  {tag:<28} {positions.size:>8,} rows  fit {elapsed:>6.1f}s  "
                  f"auc {mt.auc(test_scores['outcome'].to_numpy(), test_scores['pd'].to_numpy()):.4f}"
                  f"  O/E {test_scores['outcome'].mean() / test_scores['pd'].mean():.3f}"
                  f"  threshold {threshold:.4f} (F1 {at.f1:.3f}, "
                  f"{at.predicted_positive_share:.3%} positive)", flush=True)
        print(f"fold {k} in {time.time() - fold_started:.0f}s\n", flush=True)

    score_frame = pd.concat(scores, ignore_index=True)
    reference_frame = pd.concat(reference, ignore_index=True)
    for frame_ in (score_frame, reference_frame):
        frame_["context_seed"] = frame_["context_seed"].astype("Int64")
    score_frame.to_parquet(args.out_dir / "scores.parquet", index=False)
    reference_frame.to_parquet(args.out_dir / "reference.parquet", index=False)
    pd.concat(assignments, ignore_index=True).to_parquet(args.out_dir / "folds.parquet",
                                                         index=False)
    context = pd.concat(contexts, ignore_index=True)
    context["context_seed"] = context["context_seed"].astype("Int64")
    context.to_parquet(args.out_dir / "context.parquet", index=False)
    scored = pd.concat(cells, ignore_index=True)
    scored.to_parquet(args.out_dir / "scored.parquet", index=False)

    features = list(matrix.columns)
    summary = {
        "build": build.as_dict(),
        "label": labelled.as_dict(),
        "snapshot": snapshot.isoformat(),
        "protocol": {
            "folds": args.folds, "fold_seed": args.fold_seed, "run_folds": run_folds,
            "stratified": "classes dealt round the folds in a seeded shuffle",
            "validation_share": VALIDATION_SHARE,
            "validation_seed": "fold_seed + fold",
            "gbm": "the study's grid, the point chosen on the validation fifth by AUC, "
                   "stopped on it, the shipped model fitted on the four fifths without refit",
            "control": "the full model's point on a 50,000-row sample of the four fifths per "
                       "context seed, stopped on the same fifth; the sample is the context",
            "threshold": "the score maximising F1 on the validation fifth, per model and seed",
            "cells": {"rows": args.cell_rows, "seed": "fold_seed * 100 + fold",
                      "parts": list(PARTS)},
        },
        "features": features,
        "categorical": [name for name in categorical_names() if name in features],
        "context": {"rows": CONTEXT_ROWS, "seeds": list(seeds)},
        "seeds": {"fold": args.fold_seed, "context": list(seeds),
                  "booster": gb.DEFAULT_POLICY.seed},
        "policy": {"scorecard": policy.as_dict(), "gbm": gb.DEFAULT_POLICY.as_dict()},
        "units": summaries,
        "thresholds": thresholds,
        "files": {name: sha256(args.out_dir / name)
                  for name in ("context.parquet", "scored.parquet")},
        "scored_rows": len(score_frame),
        "reference_rows": len(reference_frame),
        "wall_seconds": round(time.time() - started, 1),
    }
    (args.out_dir / "folds.json").write_text(json.dumps(summary, indent=2, default=str),
                                             encoding="utf-8")
    # The bundle description the node scorer reads, in the shape it expects.
    bundle = {
        "build": build.as_dict(), "label": labelled.as_dict(), "snapshot": snapshot.isoformat(),
        "features": features, "categorical": summary["categorical"],
        "context": {"rows": CONTEXT_ROWS, "seeds": list(seeds),
                    "sizes": {str(s): int((context["context_seed"] == s).sum()) for s in seeds}},
        "cohorts": {name: int((scored["cohort"] == name).sum())
                    for name in sorted(scored["cohort"].unique())},
        "seeds": summary["seeds"], "files": summary["files"], "checks": None,
        "in_time": {"folds": run_folds, "note": "cells are samples of a random fold's "
                    "validation fifth and test part, not vintage cohorts; age is zero"},
        "wall_seconds": summary["wall_seconds"],
    }
    (args.out_dir / "bundle.json").write_text(json.dumps(bundle, indent=2, default=str),
                                              encoding="utf-8")
    print(f"scored rows           : {len(score_frame):,}")
    print(f"reference rows        : {len(reference_frame):,}")
    print(f"context rows          : {len(context):,}; cells {len(scored):,} rows over "
          f"{scored['cohort'].nunique()} cells")
    print(f"wall                  : {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
