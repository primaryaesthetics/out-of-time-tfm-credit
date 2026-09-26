#!/usr/bin/env python3
"""Packs one Freddie Mac build's context samples and scoring cohorts for a compute node.

The counterpart of `export_context.py` on the second book. The rows are
decided by `fm_score_build.prepare`, the code that decided them for the
scorecard and the GBM of the same build, and the bundle is written in the
format `score_context.py` reads, which needs no knowledge of the book:

- `context.parquet`: one row per (context seed, sampled training row), with
  the outcome and the model matrix;
- `scored.parquet`: one row per (cohort, scored row), with the cohort's name,
  its age in quarters, the outcome and the model matrix. A half-year cohort
  is a string like any other and sorts chronologically, so the node's choice
  of the youngest cohorts holds on this book unchanged;
- `bundle.json`: the build, the feature list with the categorical columns
  named, the label definition, the context seeds and sizes, the cohorts, the
  hash of both parquet files and the check below.

Only the study's reading of the label travels, as `outcome`. The reading that
counts the relief months is a column of the score run's files and is joined
back by row, which is the key the node's output shares with them.

The bundle is a derived product of the dataset under its terms and is never
tracked or distributed: every parquet file under an experiment directory
named `-fm-` is ignored by git. The ratio of the loan amount to the year's
conforming limit that the matrix carries is computed from a column the bundle
already held and a public table, so it takes nothing more off the machine.

When the recorded score run of the same build is given, the bundle is checked
against it row by row as on Lending Club, and a mismatch stops the export.

    python scripts/record_run.py fm-<build>-bundle -- \\
        python scripts/fm_export_context.py data/derived/freddie-mac \\
            --out-dir experiments/<date>-fm-<build>-bundle --as-of <date> --arm E \\
            --expect-scores experiments/<date>-fm-<build>-scores
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from export_context import CONTEXT_FILE, DESCRIPTION_FILE, SCORED_FILE, check_against, sha256
from fm_score_build import age_in_quarters, design_parser, prepare, seeds_of

from outoftime import fm_features
from outoftime.vintage import TEST_SAMPLE_SEED


def parse_args(argv: list[str] | None = None):
    parser = design_parser(__doc__)
    parser.add_argument("--expect-scores", type=Path, default=None,
                        help="directory of the recorded fm_score_build run of the same build, "
                             "whose rows this bundle has to reproduce")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    seeds = seeds_of(args)

    started = time.time()
    prepared = prepare(args)
    build, matrix, outcome = prepared.build, prepared.matrix, prepared.outcome
    print(f"book rows             : {prepared.exclusions['book']:,}")
    print(f"prepared in           : {prepared.seconds:.0f}s", flush=True)
    print(build.summary(), "\n", flush=True)
    stamp = {"build_id": build.build_id, "arm": build.arm, "as_of": build.as_of.isoformat()}

    def rows_of(positions, **columns) -> pd.DataFrame:
        index = list(positions)
        head = pd.DataFrame({**stamp, **columns,
                             "row": np.asarray(index, dtype=np.int64),
                             "outcome": outcome[index].astype(np.int8)})
        body = matrix.iloc[index].reset_index(drop=True)
        return pd.concat([head, body], axis=1)

    contexts = []
    for seed in seeds:
        positions = build.context(seed=seed, size=args.context_rows)
        contexts.append(rows_of(positions, context_seed=seed))
        whole = " (the whole pool)" if len(positions) == len(build.train) else ""
        print(f"context {seed}: {len(positions):,} rows{whole}")
    context = pd.concat(contexts, ignore_index=True)
    context["context_seed"] = context["context_seed"].astype("Int64")

    scored = pd.concat(
        [rows_of(rows, cohort=str(cohort), age_quarters=age_in_quarters(build.as_of, cohort))
         for cohort, rows in build.test],
        ignore_index=True,
    )
    if (context["outcome"] < 0).any() or (scored["outcome"] < 0).any():
        raise SystemExit("a packed row carries no label; the build should have refused it")

    checks = None
    if args.expect_scores is not None:
        checks = check_against(args.expect_scores, context, scored)
        print(f"checked against       : {args.expect_scores} — every row and outcome identical")

    context.to_parquet(args.out_dir / CONTEXT_FILE, index=False)
    scored.to_parquet(args.out_dir / SCORED_FILE, index=False)

    features = list(matrix.columns)
    description = {
        "build": build.as_dict(),
        "grid": prepared.grid,
        "ablation": args.ablation,
        "label": prepared.primary.as_dict(),
        "performance_cutoff": prepared.cutoff.isoformat(),
        "features": features,
        "categorical": [name for name in fm_features.categorical_names(args.ablation)
                        if name in features],
        "context": {"rows": args.context_rows, "seeds": list(seeds),
                    "sizes": {str(s): int((context["context_seed"] == s).sum()) for s in seeds}},
        "cohorts": {str(c): len(rows) for c, rows in build.test},
        "seeds": {"test_sample": TEST_SAMPLE_SEED if args.test_rows else None},
        "files": {name: sha256(args.out_dir / name) for name in (CONTEXT_FILE, SCORED_FILE)},
        "checks": checks,
        "wall_seconds": round(time.time() - started, 1),
    }
    (args.out_dir / DESCRIPTION_FILE).write_text(
        json.dumps(description, indent=2, default=str), encoding="utf-8")
    print(f"\ncontext rows          : {len(context):,}")
    print(f"scored rows           : {len(scored):,} over {len(build.test)} cohorts")
    print(f"features              : {len(features)}, {len(description['categorical'])} categorical")
    print(f"wall                  : {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
