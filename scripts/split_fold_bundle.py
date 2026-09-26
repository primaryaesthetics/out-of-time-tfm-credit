#!/usr/bin/env python3
"""One node bundle per cross-validation fold, out of a bundle that holds several.

The node scorer conditions a foundation model on the context rows of one draw
and scores every cell of the bundle against that model. On a vintage build
that is right: the build has one context and its cohorts lie after it in time.
On a bundle holding several random folds it is wrong, and wrong in the
direction that flatters the model. The folds partition one pool, so the rows
a fold draws its context from are the rows another fold holds out: pooling the
contexts of folds two to five puts about 9,000 of the 20,000 rows of each test
cell, with their outcomes, into the context that scores it.

`in_time_folds.py` writes the fold on every context row and the fold in every
cell's name, so the bundle carries what tells them apart; nothing downstream
reads it. This splits such a bundle into one bundle per fold — the same rows,
the same columns, the same description narrowed to that fold — and refuses to
write a bundle whose context meets its own cells.

    python scripts/record_run.py lc-2015h1e-fold-bundles -- \\
        python scripts/split_fold_bundle.py experiments/2026-09-12-lc-2015h1e-folds-2to5 \\
            --out-dir experiments/<date>-lc-2015h1e-fold-bundles

Each written bundle names the bundle it came out of and that bundle's file
hashes, so a node record made from it resolves to the run that packed the rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

BUNDLE_FILES = ("bundle.json", "context.parquet", "scored.parquet")
CELL = "{prefix}{fold}-"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def cells_of(scored: pd.DataFrame, fold: int, prefix: str) -> list[str]:
    """The cell names of one fold, in the order the bundle lists them."""
    start = CELL.format(prefix=prefix, fold=fold)
    return [name for name in dict.fromkeys(scored["cohort"]) if str(name).startswith(start)]


def check_disjoint(context: pd.DataFrame, scored: pd.DataFrame, fold: int) -> None:
    """A cell scored by a model conditioned on its own rows is scored in sample."""
    conditioned = set(context["row"])
    for name, cell in scored.groupby("cohort", sort=True):
        met = conditioned & set(cell["row"])
        if met:
            raise SystemExit(
                f"fold {fold}: {len(met):,} of the {len(cell):,} rows of {name} are in the "
                f"context that would score it; the bundle is not written")


def split(source: Path, out_dir: Path, folds: list[int] | None, prefix: str) -> dict:
    for name in BUNDLE_FILES:
        if not (source / name).exists():
            raise SystemExit(f"{source.as_posix()} has no {name}; not a node bundle")
    description = json.loads((source / "bundle.json").read_text(encoding="utf-8"))
    context = pd.read_parquet(source / "context.parquet")
    scored = pd.read_parquet(source / "scored.parquet")
    if "fold" not in context.columns:
        raise SystemExit(f"{source.as_posix()}: context.parquet carries no fold column")
    present = sorted(int(f) for f in context["fold"].unique())
    wanted = present if folds is None else sorted(folds)
    unknown = set(wanted) - set(present)
    if unknown:
        raise SystemExit(f"{source.as_posix()} holds folds {present}, not "
                         f"{sorted(unknown)}")

    written: dict[str, dict] = {}
    seen_context, seen_cells = 0, 0
    for fold in wanted:
        rows = context[context["fold"].astype(int) == fold].reset_index(drop=True)
        names = cells_of(scored, fold, prefix)
        if not names:
            raise SystemExit(f"fold {fold}: no cell of scored.parquet is named "
                             f"{CELL.format(prefix=prefix, fold=fold)}*")
        cells = scored[scored["cohort"].isin(names)].reset_index(drop=True)
        check_disjoint(rows, cells, fold)

        target = out_dir / f"{source.name}-fold{fold}"
        target.mkdir(parents=True, exist_ok=True)
        rows.to_parquet(target / "context.parquet", index=False)
        cells.to_parquet(target / "scored.parquet", index=False)
        sizes = {str(seed): int((rows["context_seed"] == seed).sum())
                 for seed in description["context"]["seeds"]}
        if len(set(sizes.values())) != 1:
            raise SystemExit(f"fold {fold}: the draws hold {sizes}, not one size")
        narrowed = dict(description)
        narrowed["context"] = {"rows": next(iter(sizes.values())),
                               "seeds": description["context"]["seeds"], "sizes": sizes}
        narrowed["cohorts"] = {name: int((cells["cohort"] == name).sum()) for name in names}
        narrowed["in_time"] = {**description.get("in_time", {}), "folds": [fold]}
        narrowed["files"] = {name: sha256(target / name)
                             for name in ("context.parquet", "scored.parquet")}
        narrowed["split_from"] = {"bundle": source.name, "fold": fold,
                                  "files": description.get("files", {})}
        (target / "bundle.json").write_text(
            json.dumps(narrowed, indent=2, default=str) + "\n", encoding="utf-8")
        written[target.name] = {"fold": fold, "context_rows": len(rows),
                                "cells": narrowed["cohorts"],
                                "files": narrowed["files"]}
        seen_context += len(rows)
        seen_cells += len(cells)
        print(f"{target.name:<46} context {len(rows):>7,}  "
              + "  ".join(f"{n} {c:,}" for n, c in narrowed["cohorts"].items()))

    if folds is None:
        if seen_context != len(context) or seen_cells != len(scored):
            raise SystemExit(
                f"the written bundles hold {seen_context:,} context and {seen_cells:,} cell "
                f"rows against the source's {len(context):,} and {len(scored):,}")
    return {"source": source.name, "source_files": description.get("files", {}),
            "folds": wanted, "prefix": prefix, "bundles": written,
            "source_rows": {"context": len(context), "scored": len(scored)}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="a bundle directory holding several folds")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--folds", default="",
                        help="comma-separated folds to write, 1-based; all of them by default")
    parser.add_argument("--cell-prefix", default="fold",
                        help="what a cell of fold k is named: <prefix>k-<part>")
    args = parser.parse_args(argv)
    folds = [int(v) for v in args.folds.split(",") if v.strip()] or None

    args.out_dir.mkdir(parents=True, exist_ok=True)
    record = split(args.source, args.out_dir, folds, args.cell_prefix)
    (args.out_dir / "summary.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"\n{len(record['bundles'])} bundles from {record['source']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
