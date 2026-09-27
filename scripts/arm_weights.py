#!/usr/bin/env python3
"""An arm pooling, with the cell count and each build's weight printed beside its rows.

Runs `arm_intervals.py` on the arguments given, unchanged, and then reads the
pooling it wrote to say how much each build weighs in the arm's rows. The
arm's level statistics are means over cells, so a build weighs its share of
the pooled cells; the second PSI leaves each build's first scored cohort out,
so there a build weighs its share of the cells less that one; the slope of
AUC with one intercept per build pools the within-build movements, so a build
weighs its share of the summed squared deviations of its cells' ages from
their mean, and a build with one cell weighs nothing. The mean over builds
weighs every build alike. The slope with one intercept per cohort weighs
cohorts, not builds, and is not given here.

The weights are those of the cells in the pooling, after the floors; a cell
on which a Cox fit did not finish leaves the Cox statistics as well, and the
pooling prints those counts itself. `weights.json` beside `intervals.json`
holds the table.

    python scripts/record_run.py lc-arm-e-intervals-label24 -- \\
        python scripts/arm_weights.py <the arm_intervals.py arguments>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import arm_intervals as ai


def build_weights(out_dir: Path) -> dict:
    """Each build's cells and weights in the pooling recorded under `out_dir`."""
    summary = json.loads((out_dir / "intervals.json").read_text(encoding="utf-8"))
    under = set(summary.get("floors", {}).get("under", {}))
    first = summary["psi"]["first_cohort"]
    ages: dict[tuple[str, str], int] = {}
    for source in summary["sources"]:
        frame = pd.read_parquet(Path(source) / "scores.parquet",
                                columns=["build_id", "cohort", "age_quarters"]).drop_duplicates()
        for build, cohort, age in frame.itertuples(index=False):
            ages[(str(build), str(cohort))] = int(age)
    rows = {}
    for build, cohorts in summary["builds"].items():
        pooled = [c for c in cohorts if c not in under]
        age = np.asarray([ages[(build, c)] for c in pooled], dtype=float)
        rows[build] = {
            "cells": len(pooled),
            "cells_second_psi": len([c for c in pooled if c != first[build]]),
            "age_sum_of_squares": float(np.sum((age - age.mean()) ** 2)) if age.size else 0.0,
        }
    totals = {key: sum(r[key] for r in rows.values())
              for key in ("cells", "cells_second_psi", "age_sum_of_squares")}
    for entry in rows.values():
        entry["weight_mean"] = entry["cells"] / totals["cells"] if totals["cells"] else 0.0
        entry["weight_second_psi"] = (entry["cells_second_psi"] / totals["cells_second_psi"]
                                      if totals["cells_second_psi"] else 0.0)
        entry["weight_auc_slope_build"] = (entry["age_sum_of_squares"] / totals["age_sum_of_squares"]
                                           if totals["age_sum_of_squares"] else 0.0)
        entry["weight_builds"] = 1.0 / len(rows)
    return {"cells": totals["cells"], "builds": rows,
            "reading": {
                "weight_mean": "share of the pooled cells: gini, abs_log_oe, cox_slope_deviation, "
                               "cox_slope and psi at the arm's scope",
                "weight_second_psi": "share of the pooled cells less each build's first scored "
                                     "cohort: psi_first_cohort at the arm's scope",
                "weight_auc_slope_build": "share of the summed squared deviations of the cells' "
                                          "ages from their build's mean: auc_slope_build at the "
                                          "arm's scope",
                "weight_builds": "every build alike: the builds scope"}}


def print_weights(weights: dict) -> None:
    print(f"\ncells in the pooling  : {weights['cells']}")
    print("build weights         : cells, then the build's weight in the arm's mean statistics, "
          "in the second PSI, in the AUC slope with one intercept per build, and in the mean "
          "over builds")
    for build, entry in weights["builds"].items():
        print(f"  {build:<10} {entry['cells']:>3} cells  mean {entry['weight_mean']:.4f}  "
              f"second psi {entry['weight_second_psi']:.4f}  "
              f"auc slope {entry['weight_auc_slope_build']:.4f}  "
              f"builds {entry['weight_builds']:.4f}")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    code = ai.main(argv)
    if code:
        return code
    out_dir = ai.parse_args(argv).out_dir
    weights = build_weights(out_dir)
    print_weights(weights)
    (out_dir / "weights.json").write_text(json.dumps(weights, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
