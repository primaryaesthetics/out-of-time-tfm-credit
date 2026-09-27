#!/usr/bin/env python3
"""Kill criterion 3 of EXP-002 and EXP-005: whether the vintage axis resolves anything.

Both books state the criterion as a comparison of two spreads per model and
build on the expanding arm, and both fire it on a majority of the builds.
The statistics are read from the per-build interval runs' `metrics.parquet`,
on the AUC.

Lending Club (EXP-002, reading fixed in the note of 2026-09-17). Per seeded
model and build: the mean over the build's cohorts of the range of the AUC
across the three context draws, against the mean over adjacent cohort pairs
of |AUC difference| under one draw, averaged over the draws. The criterion
fires for a model when the first exceeds the second on a majority of the
builds read. A deterministic model has no draw and is not read.

Freddie Mac (EXP-005, criterion 3 as written). Per model and build, over the
build's criterion cells (the cohorts above the floors): the width of the
DeLong interval of the median criterion cell against the range of that
model's AUC across the criterion cells. It fires when the width exceeds the
range for every model on a majority of the builds read. "The median
criterion cell" is read two ways, both reported: the median of the cells'
interval widths, and the width of the cell whose AUC is the median. A seeded
model is read on each draw, and counts as wider on a build when a majority
of its draws are. Where the two readings of the median cell disagree on the
verdict, both are printed and neither is chosen.

    python scripts/kill_criterion_3.py lc experiments/2026-09-11-lc-*e-intervals-grid --out-dir ...
    python scripts/kill_criterion_3.py fm experiments/2026-09-1?-fm-*h2e-intervals-grid --out-dir ...
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def auc_cells(directory: Path) -> pd.DataFrame:
    metrics = pd.read_parquet(directory / "metrics.parquet")
    cells = metrics[metrics["metric"] == "auc"].copy()
    if cells["build_id"].nunique() != 1 or set(cells["arm"]) != {"E"}:
        raise SystemExit(f"{directory.as_posix()}: not one expanding-arm build")
    cells["width"] = cells["ci_hi"] - cells["ci_lo"]
    return cells


def lc_rows(cells: pd.DataFrame) -> list[dict]:
    rows = []
    build = str(cells["build_id"].iloc[0])
    for model, sub in cells[cells["context_seed"].notna()].groupby("model", sort=True):
        wide = sub.pivot_table(index="cohort", columns="context_seed", values="value")
        if wide.shape[1] < 2:
            continue
        wide = wide.sort_index()
        between_draws = float((wide.max(axis=1) - wide.min(axis=1)).mean())
        between_cohorts = float(wide.diff().abs().iloc[1:].mean(axis=0).mean())
        rows.append({"build_id": build, "model": model, "draws": wide.shape[1],
                     "cohorts": wide.shape[0], "between_draws": between_draws,
                     "between_adjacent_cohorts": between_cohorts,
                     "draws_move_more": between_draws > between_cohorts})
    return rows


def fm_rows(cells: pd.DataFrame) -> list[dict]:
    rows = []
    build = str(cells["build_id"].iloc[0])
    criterion = cells[cells["floor"].astype(bool)]
    for (model, seed), sub in criterion.groupby(["model", "context_seed"], dropna=False, sort=True):
        ordered = sub.sort_values("value").reset_index(drop=True)
        median_auc_cell = ordered.iloc[(len(ordered) - 1) // 2 : len(ordered) // 2 + 1]
        auc_range = float(sub["value"].max() - sub["value"].min())
        width_median = float(sub["width"].median())
        width_of_median_auc = float(median_auc_cell["width"].mean())
        rows.append({"build_id": build, "model": model,
                     "context_seed": None if pd.isna(seed) else int(seed),
                     "criterion_cells": len(sub), "auc_range": auc_range,
                     "median_width": width_median, "width_at_median_auc": width_of_median_auc,
                     "wider_by_median_width": width_median > auc_range,
                     "wider_by_median_auc_cell": width_of_median_auc > auc_range})
    return rows


def fm_verdict(table: pd.DataFrame, column: str) -> tuple[pd.DataFrame, int, bool]:
    per_model = (table.groupby(["build_id", "model"])[column]
                 .agg(lambda s: s.sum() * 2 > len(s)).rename("wider").reset_index())
    per_build = per_model.groupby("build_id")["wider"].all()
    fires = int(per_build.sum()) * 2 > len(per_build)
    return per_model, int(per_build.sum()), fires


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("book", choices=("lc", "fm"))
    parser.add_argument("runs", type=Path, nargs="+", help="per-build interval runs, expanding arm")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    frames = [auc_cells(d) for d in args.runs]
    builds = sorted(str(f["build_id"].iloc[0]) for f in frames)
    if len(set(builds)) != len(builds):
        raise SystemExit(f"a build is named twice: {builds}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary: dict = {"book": args.book, "builds": builds,
                     "sources": [d.as_posix() for d in args.runs]}

    if args.book == "lc":
        table = pd.DataFrame([r for f in frames for r in lc_rows(f)])
        table.to_csv(args.out_dir / "criterion-3.csv", index=False)
        print(f"{len(builds)} expanding builds; per seeded model, mean range of AUC across the "
              "draws against mean |AUC difference| between adjacent cohorts under one draw")
        print(table.round(5).to_string(index=False))
        models = {}
        for model, sub in table.groupby("model"):
            count = int(sub["draws_move_more"].sum())
            models[model] = {"builds_where_draws_move_more": count, "builds": len(sub),
                             "fires": count * 2 > len(sub)}
            print(f"  {model:<11} draws move more on {count} of {len(sub)} builds: "
                  f"{'FIRES' if models[model]['fires'] else 'does not fire'}")
        summary["models"] = models
        summary["fires_for_any_model"] = any(m["fires"] for m in models.values())
    else:
        table = pd.DataFrame([r for f in frames for r in fm_rows(f)])
        table.to_csv(args.out_dir / "criterion-3.csv", index=False)
        print(f"{len(builds)} expanding builds; per model and draw, the DeLong width of the median "
              "criterion cell against the range of AUC over the build's criterion cells")
        print(table.round(5).to_string(index=False))
        readings = {}
        for column, name in (("wider_by_median_width", "median of the cells' widths"),
                             ("wider_by_median_auc_cell", "width of the median-AUC cell")):
            per_model, count, fires = fm_verdict(table, column)
            readings[column] = {"reading": name, "builds_where_every_model_is_wider": count,
                                "builds": len(builds), "fires": fires,
                                "models_wider_per_build": {
                                    b: sorted(per_model[(per_model["build_id"] == b)
                                                        & per_model["wider"]]["model"])
                                    for b in builds}}
            print(f"\n{name}: every model wider on {count} of {len(builds)} builds: "
                  f"{'FIRES' if fires else 'does not fire'}")
            for b in builds:
                wider = readings[column]["models_wider_per_build"][b]
                total = per_model[per_model["build_id"] == b]["model"].nunique()
                print(f"  {b:<9} {len(wider)} of {total} models wider")
        summary["readings"] = readings
        verdicts = {r["fires"] for r in readings.values()}
        summary["readings_agree"] = len(verdicts) == 1
        if len(verdicts) != 1:
            print("\nthe two readings of the median criterion cell disagree on the verdict; "
                  "both are reported and neither is chosen")

    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, default=lambda v: v.item() if isinstance(v, np.generic) else str(v))
        + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
