#!/usr/bin/env python3
"""Packs one build's context samples and scoring cohorts for a compute node.

A foundation model is not fitted; it reads a context and scores rows against
it. The context is the build's fifty-thousand-row sample of the training pool
and the rows to score are the shared scoring sample of every test cohort, and
both are decided here, on the machine that holds the book, by the same
`vintage` code that decided them for the scorecard and the GBM. The node that
holds the accelerator receives only those rows, as two parquet files and a
description, and never sees the raw file, the label code or the repository.

What the bundle holds, per build:

- `context.parquet`: one row per (context seed, sampled training row), with
  the outcome and the model matrix. These rows are also the reference the
  stability index of that context reads against.
- `scored.parquet`: one row per (cohort, scored row), with the outcome and the
  model matrix. Every cohort of the build is included; the node chooses how
  many of them to score.
- `bundle.json`: the build as `vintage` describes it, the feature list with
  the categorical columns named, the label definition, the hash of both
  parquet files, and the check below.

When the recorded score run of the same build is given, the bundle is checked
against it row by row: the context of every seed has to be the rows the
fifty-thousand-row control was fitted on, and every cohort has to be the rows
the classical models scored, with the same outcome on each. The two files a
node returns are then paired with the classical scores by construction.

    python scripts/record_run.py lc-2015h1e-bundle -- \\
        python scripts/export_context.py data/raw/accepted_2007_to_2018Q4.csv.gz \\
            --out-dir experiments/2026-09-05-lc-2015h1e-bundle \\
            --seeds 20260911 \\
            --expect-scores experiments/2026-09-05-lc-2015h1e-scores
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

from score_build import CONTEXT, age_in_quarters, load, to_dates

from outoftime.features import categorical_names, model_matrix
from outoftime.label import LabelDefinition, build_labels
from outoftime.lending_club import AXIS
from outoftime.vintage import (
    CONTEXT_ROWS,
    CONTEXT_SEEDS,
    LABEL_LAG_MONTHS,
    TEST_SAMPLE_SEED,
    builds,
)

CONTEXT_FILE = "context.parquet"
SCORED_FILE = "scored.parquet"
DESCRIPTION_FILE = "bundle.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--as-of", type=dt.date.fromisoformat, default=dt.date(2015, 6, 30),
                        help="the build's as-of date")
    parser.add_argument("--arm", default="E", choices=("E", "R"))
    parser.add_argument("--seeds", default=",".join(str(s) for s in CONTEXT_SEEDS),
                        help="context seeds to pack, comma-separated")
    parser.add_argument("--expect-scores", type=Path, default=None,
                        help="directory of the recorded score_build run of the same build, "
                             "whose rows this bundle has to reproduce")
    return parser.parse_args(argv)


def check_against(scores_dir: Path, context: pd.DataFrame, scored: pd.DataFrame) -> dict:
    """Row-by-row agreement with the recorded classical run, or a refusal.

    Agreement is on the row positions and on the outcome carried by each. A
    bundle whose rows differ from the recorded run's would produce scores that
    pair with nothing, so a mismatch stops the export rather than being noted.
    """
    reference = pd.read_parquet(scores_dir / "reference.parquet")
    recorded = pd.read_parquet(scores_dir / "scores.parquet")
    report: dict[str, dict] = {"context": {}, "cohorts": {}}

    control = reference[reference["model"] == CONTEXT]
    for seed, mine in context.groupby("context_seed"):
        theirs = control[control["context_seed"] == seed].sort_values("row")
        mine = mine.sort_values("row")
        if theirs.empty:
            raise SystemExit(f"{scores_dir} holds no {CONTEXT} reference for seed {seed}")
        if not np.array_equal(theirs["row"].to_numpy(), mine["row"].to_numpy()):
            raise SystemExit(f"context seed {seed}: rows differ from the recorded control")
        if not np.array_equal(theirs["outcome"].to_numpy(), mine["outcome"].to_numpy()):
            raise SystemExit(f"context seed {seed}: outcomes differ from the recorded control")
        report["context"][str(seed)] = {"rows": len(mine), "identical": True}

    one_model = recorded["model"].iloc[0]
    one_seed = recorded.loc[recorded["model"] == one_model, "context_seed"].iloc[0]
    theirs_all = recorded[(recorded["model"] == one_model)
                          & (recorded["context_seed"].isna() if pd.isna(one_seed)
                             else recorded["context_seed"] == one_seed)]
    for cohort, mine in scored.groupby("cohort"):
        theirs = theirs_all[theirs_all["cohort"] == cohort].sort_values("row")
        mine = mine.sort_values("row")
        if theirs.empty:
            raise SystemExit(f"{scores_dir} scored no rows of cohort {cohort}")
        if not np.array_equal(theirs["row"].to_numpy(), mine["row"].to_numpy()):
            raise SystemExit(f"cohort {cohort}: rows differ from the recorded scoring sample")
        if not np.array_equal(theirs["outcome"].to_numpy(), mine["outcome"].to_numpy()):
            raise SystemExit(f"cohort {cohort}: outcomes differ from the recorded run")
        report["cohorts"][str(cohort)] = {"rows": len(mine), "identical": True}
    missing = set(theirs_all["cohort"]) - set(scored["cohort"])
    if missing:
        raise SystemExit(f"the recorded run scored cohorts this bundle lacks: {sorted(missing)}")
    report["against"] = scores_dir.as_posix()
    return report


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
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
    outcome = np.full(len(origination), -1, dtype=np.int64)
    outcome[list(labelled.indices)] = list(labelled.labels)
    matrix = model_matrix(frame)
    del frame
    print(f"rows                  : {len(origination):,}")
    print(f"loaded in             : {time.time() - started:.0f}s", flush=True)

    (build,) = builds(origination, as_of_dates=(args.as_of,), arm=args.arm, labels=labelled)
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
        positions = build.context(seed=seed)
        contexts.append(rows_of(positions, context_seed=seed))
        whole = " (the whole pool)" if len(positions) == len(build.train) else ""
        print(f"context {seed}: {len(positions):,} rows{whole}")
    context = pd.concat(contexts, ignore_index=True)
    context["context_seed"] = context["context_seed"].astype("Int64")

    scored = pd.concat(
        [rows_of(rows, cohort=str(quarter), age_quarters=age_in_quarters(build.as_of, quarter))
         for quarter, rows in build.test],
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
        "label": labelled.as_dict(),
        "snapshot": snapshot.isoformat(),
        "features": features,
        "categorical": [name for name in categorical_names() if name in features],
        "context": {"rows": CONTEXT_ROWS, "seeds": list(seeds),
                    "sizes": {str(s): int((context["context_seed"] == s).sum()) for s in seeds}},
        "cohorts": {str(q): len(rows) for q, rows in build.test},
        "seeds": {"test_sample": TEST_SAMPLE_SEED},
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
