#!/usr/bin/env python3
"""A fitted model's in-sample probabilities with the logit rescaled, as a temperature would.

A foundation model at softmax temperature T divides its logit by T. A model
calibrated at 1.0 and read at 0.9 therefore reads an in-sample level that
moves with prevalence by arithmetic alone: on a small probability the rescale
multiplies it by roughly p^(1/T - 1), more on a low-rate context than on a
high-rate one. EXP-005's note of 2026-09-17 withdraws H5's mechanism sentence
on that ground and names the demonstration: the control, calibrated on its
own context rows by construction, rescaled to 0.9 and read by the same H5
statistic.

This writes, per score run named, a directory whose `reference.parquet` holds
the named model's context rows with p' = sigmoid(logit(p) / T), under the
model name `<model>@t<T>`, with the same rows, outcomes and context seeds.
`in_sample_level.py` reads it beside the score runs.

    python scripts/record_run.py fm-h5-rescaled-control -- \\
        python scripts/rescale_reference.py experiments/2026-09-13-fm-*-scores \\
            --model gbm-50k --temperature 0.9 --out-dir experiments/<date>-fm-h5-rescaled-control
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNS = ["build_id", "arm", "model", "context_seed", "row", "outcome", "pd"]
EDGE = 1e-12


def rescale(pd_values: np.ndarray, temperature: float) -> tuple[np.ndarray, int]:
    clipped = np.clip(pd_values, EDGE, 1.0 - EDGE)
    moved = int(np.count_nonzero(clipped != pd_values))
    logit = np.log(clipped) - np.log1p(-clipped)
    return 1.0 / (1.0 + np.exp(-logit / temperature)), moved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", type=Path, nargs="+", help="score runs holding reference.parquet")
    parser.add_argument("--model", default="gbm-50k")
    parser.add_argument("--temperature", type=float, default=0.9)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if not 0.0 < args.temperature:
        raise SystemExit("the temperature is positive")

    name = f"{args.model}@t{args.temperature:g}"
    record = {"model": args.model, "written_as": name, "temperature": args.temperature,
              "transform": "sigmoid(logit(p) / temperature)", "builds": {}}
    for run in args.runs:
        reference = pd.read_parquet(run / "reference.parquet")
        cells = reference[reference["model"] == args.model]
        if cells.empty:
            raise SystemExit(f"{run.as_posix()}: no {args.model} rows in reference.parquet")
        missing = [c for c in COLUMNS if c not in cells.columns]
        if missing:
            raise SystemExit(f"{run.as_posix()}: reference.parquet lacks {', '.join(missing)}")
        cells = cells[COLUMNS].copy()
        build = str(cells["build_id"].iloc[0])
        cells["pd"], moved = rescale(cells["pd"].to_numpy(dtype=float), args.temperature)
        cells["model"] = name
        target = args.out_dir / build.lower()
        target.mkdir(parents=True, exist_ok=True)
        cells.to_parquet(target / "reference.parquet", index=False)
        by_seed = cells.groupby("context_seed")
        record["builds"][build] = {
            "source": run.as_posix(), "rows": len(cells), "clipped": moved,
            "observed_over_expected": {int(s): float(f["outcome"].mean() / f["pd"].mean())
                                       for s, f in by_seed}}
        print(f"{build:<10} {len(cells):>7,} rows  O/E at {args.temperature:g} " + "  ".join(
            f"{s}: {v:.3f}" for s, v in record["builds"][build]["observed_over_expected"].items()))
    (args.out_dir / "rescale.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
