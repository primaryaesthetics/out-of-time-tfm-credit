#!/usr/bin/env python3
"""Sensitivity points for a recorded H4 pooling, and the control's fit table.

H4 reads, per foundation model, the expanding arm's mean |Cox slope - 1| minus
the rolling arm's, less the same reduction for GBM-50k, over the criterion
cells the arms share. The control is a 50,000-row draw refitted three times per
build, so one early-stopping decision can carry the pooled number. This script
reads a recorded pooling's `cells.csv` and writes the points that say whether
it does:

  recorded       the criterion's point, checked against the run's paired.csv
  per_draw       the foundation model's and the control's rows of one draw
  drop_build     every row of one build date left out
  replace_fit    one control fit's deviations, on one arm, replaced by the
                 mean of the other two draws' on the same cells

and, beside them, per build date, arm and draw, the control's inherited point,
its round count, its early-stopping quarters and rows, and its mean deviation
over the criterion cells, read from the build's score run through the
provenance the manifests record.

    python scripts/h4_sensitivity.py experiments/<h4 run> --out-dir experiments/<dir>

Every row is a point estimate: the perturbations change per-cell deviations,
and the rows underneath are not resampled here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CONTROL = "gbm-50k"
MODELS = ("tabpfn", "tabicl", "tabpfn@t1", "tabicl@t1")
ARMS = ("E", "R")


def criterion_cells(run: Path) -> pd.DataFrame:
    cells = pd.read_csv(run / "cells.csv", keep_default_na=False)
    flag = cells["criterion"]
    if flag.dtype != bool:
        flag = flag.astype(str) == "True"
    cells = cells[flag].copy()
    for arm in ARMS:
        cells[f"deviation_{arm}"] = cells[f"deviation_{arm}"].astype(float)
    cells["draw"] = cells["context_seed"].astype(str)
    return cells


def h4(cells: pd.DataFrame) -> dict[str, float]:
    reduction = (cells["deviation_E"] - cells["deviation_R"]).groupby(cells["model"]).mean()
    return {model: float(reduction[model] - reduction[CONTROL]) for model in MODELS if model in reduction}


def replaced(cells: pd.DataFrame, build: str, arm: str, draw: str) -> pd.DataFrame:
    """The control's fit on (build, arm, draw) replaced, cell by cell, by the
    mean of the other draws' deviations on the same cells."""
    out = cells.copy()
    column = f"deviation_{arm}"
    control = out[(out["model"] == CONTROL) & (out["build_date"] == build)]
    others = control[control["draw"] != draw].groupby("cohort")[column].mean()
    target = control.index[control["draw"] == draw]
    out.loc[target, column] = out.loc[target, "cohort"].map(others).to_numpy()
    return out


def score_runs(run: Path) -> dict[tuple[str, str], Path]:
    """(build date, arm) -> the score run holding the control's fit records,
    followed from the pooling's manifest through each build's interval run."""
    command = json.loads((run / "manifest.json").read_text(encoding="utf-8"))["command"]
    found: dict[tuple[str, str], Path] = {}
    arm = None
    for argument in command:
        if argument in ("--expanding", "--rolling"):
            arm = "E" if argument == "--expanding" else "R"
            continue
        if argument.startswith("--"):
            arm = None
            continue
        if arm is None or not argument.startswith("experiments/"):
            continue
        interval = json.loads((ROOT / argument / "manifest.json").read_text(encoding="utf-8"))
        scores = [a for a in interval["command"] if a.startswith("experiments/") and a.endswith("-scores")]
        if len(scores) != 1:
            raise SystemExit(f"{argument}: expected one score run in its command, found {scores}")
        build = json.loads((ROOT / scores[0] / "build.json").read_text(encoding="utf-8"))
        found[(str(build.get("build_date") or _build_date(scores[0])), arm)] = ROOT / scores[0]
    return found


def _build_date(scores: str) -> str:
    # experiments/<date>-<book>-<yyyy>h<n><e|r>-scores
    tag = scores.rstrip("/").split("-")[-2]
    return f"{tag[:4]}H{tag[5]}"


def control_fits(run: Path, cells: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (build, arm), scores in sorted(score_runs(run).items()):
        units = json.loads((scores / "build.json").read_text(encoding="utf-8"))["units"]
        for name, unit in sorted(units.items()):
            if not name.startswith(f"{CONTROL}/"):
                continue
            draw = name.split("/", 1)[1]
            summary = unit["summary"]
            params = summary["params"]
            mine = cells[(cells["model"] == CONTROL) & (cells["build_date"] == build) & (cells["draw"] == draw)]
            rows.append(
                {
                    "build_date": build,
                    "arm": arm,
                    "draw": draw,
                    "num_leaves": params["num_leaves"],
                    "learning_rate": params["learning_rate"],
                    "min_child_samples": params["min_child_samples"],
                    "feature_fraction": params["feature_fraction"],
                    "rounds": summary["rounds"],
                    "validation_quarters": " ".join(summary["validation_quarters"]),
                    "validation_rows": summary["validation_rows"],
                    "criterion_cells": len(mine),
                    "mean_deviation": float(mine[f"deviation_{arm}"].mean()) if len(mine) else float("nan"),
                    "score_run": scores.relative_to(ROOT).as_posix(),
                }
            )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run", type=Path, help="a recorded between-arm pooling")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    run = args.run if args.run.is_absolute() else ROOT / args.run
    cells = criterion_cells(run)
    recorded = h4(cells)

    paired = pd.read_csv(run / "paired.csv", keep_default_na=False)
    primary = paired["seed"].iloc[0]
    arm_rows = paired[
        (paired["kind"] == "h4") & (paired["scope"] == "arm") & (paired["draw"] == "")
        & (paired["seed"] == primary) & (paired["cohorts"] == "all")
    ].set_index("model")["value"]
    for model, value in recorded.items():
        if abs(value - float(arm_rows[model])) > 1e-12:
            raise SystemExit(f"{model}: point {value} does not reproduce the run's {arm_rows[model]}")

    rows = [{"kind": "recorded", "build_date": "", "arm": "", "draw": "", **recorded}]
    for draw in sorted(set(cells.loc[cells["model"] == CONTROL, "draw"])):
        keep = (cells["draw"] == draw) | ~cells["model"].isin((CONTROL, *MODELS))
        rows.append({"kind": "per_draw", "build_date": "", "arm": "", "draw": draw, **h4(cells[keep])})
    for build in sorted(set(cells["build_date"])):
        rows.append({"kind": "drop_build", "build_date": build, "arm": "", "draw": "",
                     **h4(cells[cells["build_date"] != build])})
    control = cells[cells["model"] == CONTROL]
    for build, draw in sorted(set(zip(control["build_date"], control["draw"], strict=True))):
        for arm in ARMS:
            rows.append({"kind": "replace_fit", "build_date": build, "arm": arm, "draw": draw,
                         **h4(replaced(cells, build, arm, draw))})
    points = pd.DataFrame(rows)

    fits = control_fits(run, cells)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    points.to_csv(args.out_dir / "sensitivity.csv", index=False)
    fits.to_csv(args.out_dir / "control-fits.csv", index=False)

    print(f"run: {run.relative_to(ROOT).as_posix()}, {len(cells)} criterion rows")
    print("recorded point reproduces the run's paired.csv to 1e-12")
    models = [m for m in MODELS if m in recorded]
    for kind in ("recorded", "per_draw", "drop_build"):
        print(f"\n{kind}")
        print(points[points["kind"] == kind][["build_date", "draw", *models]].round(4).to_string(index=False))
    loo = points[points["kind"] == "replace_fit"]
    print(f"\nreplace_fit over {len(loo)} control fits (build, arm, draw)")
    for model in models:
        low, high = loo[model].idxmin(), loo[model].idxmax()
        print(f"  {model:<10} [{loo.at[low, model]:+.4f}, {loo.at[high, model]:+.4f}]"
              f"  lowest {loo.at[low, 'build_date']}-{loo.at[low, 'arm']} {loo.at[low, 'draw']},"
              f"  highest {loo.at[high, 'build_date']}-{loo.at[high, 'arm']} {loo.at[high, 'draw']}")
    shift = (loo[models[0]] - recorded[models[0]]).abs()
    top = loo.loc[shift.idxmax()]
    print(f"  largest move of {models[0]}: {top['build_date']}-{top['arm']} {top['draw']}")
    print("\ncontrol fits")
    print(fits.drop(columns=["score_run", "validation_quarters"]).round(4).to_string(index=False))
    same = fits.pivot_table(index="build_date", columns="arm",
                            values=["num_leaves", "learning_rate", "min_child_samples", "feature_fraction"],
                            aggfunc="first")
    differs = sum(
        any(same[(p, "E")].get(b) != same[(p, "R")].get(b) for p in
            ("num_leaves", "learning_rate", "min_child_samples", "feature_fraction"))
        for b in same.index if not same.loc[b].isna().any()
    )
    paired_dates = int((~same.isna().any(axis=1)).sum())
    print(f"\ninherited point differs between the arms at {differs} of {paired_dates} paired build dates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
