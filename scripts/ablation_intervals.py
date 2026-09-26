#!/usr/bin/env python3
"""Reads what one matrix ablation does to every model, paired on identical cells.

EXP-005 reports two ablations of its primary matrix beside every verdict:
``dti_kept``, the fourteen columns and ``dti``, and ``upb_nominal``, the loan
amount in nominal dollars in place of its ratio to the year's conforming
limit. For each it asks, per model, for the paired difference in AUC and in
Brier score between the two matrices on the falsifying cells, with the
bootstrap interval the interval scripts give on the same rows; and it
carries a trigger: if the gain from the ablation for a foundation model
differs from GBM-50k's gain beyond that interval, the foundation-model grid
is run on the ablation's matrix as well. The trigger reads the foundation
models at their library settings only, both at the temperature 0.9 the
libraries default to, on AUC and on Brier: a row of ``tabpfn@t1`` or
``tabicl@t1`` is on the table and does not fire it.

The script reads the row-level scores of both matrices for one build, each
matrix from as many directories as hold it — the classical score run and
the foundation-model runs of that matrix — and refuses unless, for every
model, context seed and cohort, the two matrices hold exactly the same rows
with the same outcomes. The difference between two matrices is then the
matrix and nothing else: not a different sample, not a different label.
It also refuses unless every directory of a group records the same feature
columns, the two groups record different ones, and a classical run's own
declaration of its ablation agrees with the group it is named in.

The pooling is the one `build_intervals.py` makes. The cohorts are those
every cell of both matrices scored, and the context seeds those every
seeded model holds on both; on the falsifying run's cells that is three
cohorts and one seed, and the rest of the classical cells stay in the
per-cell table and leave the pooling, named. A cohort under the floors of
EXP-005 (5,000 labelled loans and 100 defaults) leaves the pooling too, on
the build run's verdict under `--cells`, marked in a `floor` column of
``cells.csv``; without it a pooling whose scored rows fall under the floors
is refused. Each resample of the
cohort-blocked bootstrap draws one row index per cohort and applies it to
both matrices and every model, and the context draw is drawn with the
resample, so every difference below is paired on the same rows. A setting
off the library defaults is a model of its own (``tabicl@t1``). Per resample:

- per model and matrix, the mean over the pooled cohorts of the AUC and of
  the Brier score;
- per model, the ablation's mean minus the primary's: what the ablation
  does to that model;
- per model other than the control, that difference minus the control's on
  the same resample: (model_ablation − model_primary) − (control_ablation −
  control_primary), the trigger's statistic. The control is GBM-50k, which
  reads the foundation models' context rows.

A star marks an interval that excludes zero. Two hundred resamples under
one seed; `--check-seeds` repeats the pooling under each seed named and
names every difference whose star changes, as the other interval scripts
do. No multiplicity correction is applied.

Outputs: ``cells.csv``, the AUC and Brier score of every cell of both
matrices, pooled or not; ``paired.csv``, every pooled statistic with its
interval; ``paired-seeds.csv`` under `--check-seeds`; ``summary.json``; and
``ablation-differences.png``, each model's difference between matrices and
its difference from the control's, with the interval.

    python scripts/record_run.py fm-2004h2e-ablation-dti-kept -- \\
        python scripts/ablation_intervals.py \\
            --primary experiments/2026-09-13-fm-2004h2e-scores \\
                experiments/2026-09-13-fm-2004h2e-tabicl-rental-4090 ... \\
            --ablation experiments/2026-09-13-fm-2004h2e-scores-dti-kept \\
                experiments/2026-09-13-fm-2004h2e-dti-kept-tabicl-rental-4090 ... \\
            --check-seeds 20260906,20260907 \\
            --out-dir experiments/<date>-fm-2004h2e-ablation-dti-kept
"""

from __future__ import annotations

import argparse
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_intervals as bi

from outoftime import metrics as mt

PRIMARY = "primary"
CONTROL = "gbm-50k"
METRICS = ("auc", "brier")
METRIC_TITLE = {"auc": "AUC", "brier": "Brier score"}
COLUMNS = ["build_id", "arm", "model", "context_seed", "cohort", "age_quarters", "row",
           "outcome", "pd"]
CELL_KEYS = ["model", "context_seed", "cohort"]
# Joins a model and a matrix into one cell name for the loader of build_intervals.
JOIN = "#"


# --- what a directory says about its matrix -----------------------------------------


def matrix_of(directory: Path) -> dict:
    """The feature columns a directory's rows were scored on, and the ablation it declares.

    A classical score run writes build.json with its features and its
    ablation; a foundation-model run writes node.json with the bundle's
    features; a derived directory stands for the source it was derived from.
    """
    build = directory / "build.json"
    if build.is_file():
        record = json.loads(build.read_text(encoding="utf-8"))
        features = record.get("features")
        if isinstance(features, dict):
            features = features.get("columns") or features.get("kept")
        return {"features": sorted(features) if features else None,
                "declared": record.get("ablation"), "declares": True, "record": "build.json"}
    node = directory / "node.json"
    if node.is_file():
        bundle = json.loads(node.read_text(encoding="utf-8")).get("bundle", {})
        features = bundle.get("features")
        return {"features": sorted(features) if features else None,
                "declared": None, "declares": False, "record": "node.json"}
    derived = directory / "derive.json"
    if derived.is_file():
        sources = json.loads(derived.read_text(encoding="utf-8")).get("sources", [])
        if sources:
            found = matrix_of(Path(sources[0]["directory"]))
            return {**found, "record": f"derive.json -> {found['record']}"}
    return {"features": None, "declared": None, "declares": False, "record": None}


def matrices(primary: list[Path], ablation: list[Path], name: str | None) -> dict:
    """The two groups' feature columns, refused unless each group is one matrix and they differ."""
    found: dict[str, dict] = {}
    for group, dirs in ((PRIMARY, primary), ("ablation", ablation)):
        columns: list[str] | None = None
        declared: set[str | None] = set()
        for directory in dirs:
            record = matrix_of(directory)
            if record["features"] is None:
                raise SystemExit(f"{directory.as_posix()}: its feature columns are not recorded; "
                                 "which matrix it was scored on is unknown")
            if columns is None:
                columns = record["features"]
            elif record["features"] != columns:
                raise SystemExit(f"{directory.as_posix()} was scored on other columns than the "
                                 f"{group} directories before it; one group, one matrix")
            if record["declares"]:
                declared.add(record["declared"])
        if group == PRIMARY and declared - {None}:
            raise SystemExit(f"a directory named as primary declares the ablation "
                             f"{sorted(d for d in declared if d)}")
        if group == "ablation":
            if None in declared:
                raise SystemExit("a directory named as the ablation declares none")
            if len(declared) > 1:
                raise SystemExit(f"the ablation directories declare {sorted(declared)}; one "
                                 "reading, one ablation")
        found[group] = {"features": columns, "declared": sorted(d for d in declared if d)}
    if found[PRIMARY]["features"] == found["ablation"]["features"]:
        raise SystemExit("the two groups were scored on the same columns; there is no ablation "
                         "to read")
    declared = found["ablation"]["declared"]
    if name is None:
        if not declared:
            raise SystemExit("no directory declares the ablation's name; give --name")
        name = declared[0]
    elif declared and declared[0] != name:
        raise SystemExit(f"--name {name} but the ablation directories declare {declared[0]}")
    added = sorted(set(found["ablation"]["features"]) - set(found[PRIMARY]["features"]))
    removed = sorted(set(found[PRIMARY]["features"]) - set(found["ablation"]["features"]))
    return {"name": name, "primary_features": found[PRIMARY]["features"],
            "ablation_features": found["ablation"]["features"],
            "added": added, "removed": removed}


# --- the rows -------------------------------------------------------------------------


def read_group(dirs: list[Path]) -> tuple[pd.DataFrame, str, str]:
    frame = pd.concat([pd.read_parquet(d / "scores.parquet", columns=COLUMNS) for d in dirs],
                      ignore_index=True)
    if frame["build_id"].nunique() != 1:
        raise SystemExit("one build per reading: " + ", ".join(d.as_posix() for d in dirs))
    if frame[CELL_KEYS + ["row"]].duplicated().any():
        raise SystemExit("the same cell is scored in more than one directory of a group")
    return frame, str(frame["build_id"].iloc[0]), str(frame["arm"].iloc[0])


def cells_identical(primary: pd.DataFrame, ablation: pd.DataFrame) -> dict:
    """Refuses unless every (model, seed, cohort) holds the same rows and outcomes on both matrices."""
    def cells(frame):
        return {(m, None if pd.isna(s) else int(s), str(c))
                for m, s, c in frame[CELL_KEYS].drop_duplicates().itertuples(index=False)}

    held_p, held_a = cells(primary), cells(ablation)
    if held_p != held_a:
        only_p = sorted(held_p - held_a, key=str)[:5]
        only_a = sorted(held_a - held_p, key=str)[:5]
        raise SystemExit(f"the two matrices do not hold the same cells: primary only {only_p}, "
                         f"ablation only {only_a}")

    def ordered(frame):
        out = frame.assign(seed_key=frame["context_seed"].fillna(-1).astype("int64"))
        return out.sort_values(["model", "seed_key", "cohort", "row"]).reset_index(drop=True)

    a, b = ordered(primary), ordered(ablation)
    if len(a) != len(b):
        raise SystemExit(f"the two matrices hold {len(a):,} and {len(b):,} rows over the same cells")
    same_cell = ((a["model"].to_numpy() == b["model"].to_numpy())
                 & (a["seed_key"].to_numpy() == b["seed_key"].to_numpy())
                 & (a["cohort"].to_numpy() == b["cohort"].to_numpy()))
    same_row = a["row"].to_numpy() == b["row"].to_numpy()
    if not (same_cell & same_row).all():
        first = int(np.flatnonzero(~(same_cell & same_row))[0])
        raise SystemExit(f"cell {a.loc[first, 'model']}/{a.loc[first, 'seed_key']}/"
                         f"{a.loc[first, 'cohort']}: the two matrices hold different rows")
    same_outcome = a["outcome"].to_numpy() == b["outcome"].to_numpy()
    if not same_outcome.all():
        first = int(np.flatnonzero(~same_outcome)[0])
        raise SystemExit(f"cell {a.loc[first, 'model']}/{a.loc[first, 'seed_key']}/"
                         f"{a.loc[first, 'cohort']}: an outcome differs between the matrices")
    return {"cells": len(held_p), "rows": len(a),
            "statement": "every (model, context seed, cohort) holds exactly the same rows with "
                         "the same outcomes on both matrices"}


def cell_table(frame: pd.DataFrame, matrix: str) -> pd.DataFrame:
    records = []
    for (model, seed, cohort), cell in frame.groupby(CELL_KEYS, dropna=False, sort=True):
        y = cell["outcome"].to_numpy()
        s = cell["pd"].to_numpy(dtype=float)
        records.append({"matrix": matrix, "model": model,
                        "context_seed": None if pd.isna(seed) else int(seed), "cohort": cohort,
                        "age_quarters": int(cell["age_quarters"].iloc[0]),
                        "rows": int(y.size), "defaults": int(y.sum()),
                        "auc": mt.auc(y, s), "brier": mt.brier(y, s)})
    return pd.DataFrame(records)


# --- the pooled statistics ------------------------------------------------------------


def model_names(models: list[str]) -> list[str]:
    return [m for m in bi.MODEL_ORDER if m in models] + sorted(set(models) - set(bi.MODEL_ORDER))


def ablation_statistics(names: list[str], ablation: str, control: str):
    """Per model and matrix the pooled AUC and Brier, their difference, and its gap to the control's.

    Returns a callable of the cohorts with the context draw chosen, as
    `metrics.cohort_blocked_bootstrap_many` expects. Every statistic is a
    mean over the cohorts of a per-cohort metric, paired by cohort.
    """
    matrices_ = (PRIMARY, ablation)

    def compute(cohorts):
        per = {(m, x): {k: [] for k in METRICS} for m in names for x in matrices_}
        for cohort in cohorts.values():
            for m in names:
                for x in matrices_:
                    s = cohort.scores[f"{m}{JOIN}{x}"]
                    per[(m, x)]["auc"].append(mt.auc(cohort.outcome, s))
                    per[(m, x)]["brier"].append(mt.brier(cohort.outcome, s))
        out: dict[str, float] = {}
        for metric in METRICS:
            mean = {key: float(np.mean(v[metric])) for key, v in per.items()}
            gap = {m: mean[(m, ablation)] - mean[(m, PRIMARY)] for m in names}
            for m in names:
                for x in matrices_:
                    out[f"{metric}|mean|{m}|{x}"] = mean[(m, x)]
                out[f"{metric}|diff|{m}"] = gap[m]
            for m in names:
                if m != control:
                    out[f"{metric}|did|{m}"] = gap[m] - gap[control]
        return out

    return compute


def label(kind: str, model: str, matrix: str | None, ablation: str, control: str) -> str:
    if kind == "mean":
        return f"{model}: {matrix}"
    if kind == "diff":
        return f"{model}: {ablation} - {PRIMARY}"
    return f"{model} - {control}: {ablation} - {PRIMARY}"


def records_of(result: dict[str, mt.Bootstrap], ablation: str, control: str, build: str,
               **extra) -> list[dict]:
    out = []
    for key, boot in result.items():
        metric, kind, model, *rest = key.split("|")
        difference = kind != "mean"
        out.append({"build_id": build, "ablation": ablation, "cohorts": "all", **extra,
                    "metric": metric, "kind": kind, "model": model,
                    "matrix": rest[0] if rest else None,
                    "pair": label(kind, model, rest[0] if rest else None, ablation, control),
                    "is_difference": difference, **boot.as_dict(),
                    "excludes_zero": boot.excludes_zero if difference else None})
    return out


# --- the figure -----------------------------------------------------------------------


def plot_differences(paired: pd.DataFrame, names: list[str], ablation: str, control: str,
                     out: Path, pooled: int, seeds: list[int], seed_sensitive: set[str]) -> None:
    """Each model's difference between the matrices and its gap to the control's, with the interval.

    Four panels: the AUC difference and the Brier difference per model, and
    the same two minus the control's, which is the statistic the trigger
    reads. A hollow marker is a difference whose star changes with the
    bootstrap seed.
    """
    fig, axes = plt.subplots(1, 4, figsize=(19, max(3.6, 1.4 + 0.42 * len(names))))
    panels = [("diff", "auc"), ("diff", "brier"), ("did", "auc"), ("did", "brier")]
    for ax, (kind, metric) in zip(axes, panels):
        rows = paired[(paired["kind"] == kind) & (paired["metric"] == metric)]
        order = [m for m in names if m in set(rows["model"])]
        for y, model in enumerate(order):
            row = rows[rows["model"] == model].iloc[0]
            colour = bi.model_colour(model)
            ax.plot([row.ci_lo, row.ci_hi], [y, y], color=colour, linewidth=1.4)
            ax.plot([row.ci_lo, row.ci_lo, None, row.ci_hi, row.ci_hi],
                    [y - 0.12, y + 0.12, None, y - 0.12, y + 0.12], color=colour, linewidth=1.4)
            hollow = f"{metric}|{row.pair}" in seed_sensitive
            ax.plot(row.value, y, marker="o", markersize=5, color=colour, linestyle="none",
                    markerfacecolor="white" if hollow else colour)
        ax.axvline(0.0, color="black", linewidth=0.8, linestyle=":")
        ax.set_yticks(range(len(order)))
        ax.set_yticklabels([bi.describe(m) for m in order], fontsize=8)
        ax.invert_yaxis()
        if kind == "diff":
            ax.set_title(f"{METRIC_TITLE[metric]}: {ablation} minus {PRIMARY}", fontsize=10)
        else:
            ax.set_title(f"{METRIC_TITLE[metric]}: the model's difference minus {control}'s",
                         fontsize=10)
        ax.grid(alpha=0.3, axis="x")
    fig.suptitle(f"the {ablation} ablation on {pooled} pooled cohort{'s' if pooled != 1 else ''}, "
                 f"context seed{'s' if len(seeds) != 1 else ''} {', '.join(map(str, seeds))}: "
                 "cohort-blocked bootstrap interval, the same resample on both matrices"
                 + ("; hollow: the star changes with the bootstrap seed" if seed_sensitive else ""),
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out, dpi=130)
    plt.close(fig)


# --- the command ----------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--primary", type=Path, nargs="+", required=True,
                        help="directories holding the build's scores on the primary matrix")
    parser.add_argument("--ablation", type=Path, nargs="+", required=True,
                        help="directories holding the same build's scores on the ablation's "
                             "matrix, the same models")
    parser.add_argument("--name", default=None,
                        help="the ablation's name; read from a classical run's build.json when "
                             "one is named, and refused if it disagrees")
    parser.add_argument("--control", default=CONTROL,
                        help=f"the model every other model's difference is read against "
                             f"(default {CONTROL})")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--cohorts", default="",
                        help="comma-separated cohorts to read, every other cohort left out of "
                             "both groups before the cells are compared; a directory scored on "
                             "every cohort then pairs with one scored on these alone. Each "
                             "named cohort must be held by both groups")
    parser.add_argument("--resamples", type=int, default=mt.RESAMPLES)
    parser.add_argument("--seed", type=int, default=bi.BOOTSTRAP_SEED)
    parser.add_argument("--check-seeds", default="",
                        help="comma-separated bootstrap seeds to repeat the pooling under; the "
                             "differences whose star changes with the seed are named")
    parser.add_argument("--cells", type=Path, default=None,
                        help="the build run's cells.csv: a cohort it puts under the floors stays "
                             "in the per-cell table and leaves every pooling")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.time()
    check_seeds = [int(s) for s in args.check_seeds.split(",") if s.strip()]
    if args.seed in check_seeds:
        raise SystemExit(f"--check-seeds repeats the primary seed {args.seed}")

    matrix = matrices(args.primary, args.ablation, args.name)
    ablation = matrix["name"]
    if ablation == PRIMARY:
        raise SystemExit(f"the ablation cannot be named {PRIMARY}")
    primary, build, arm = read_group(args.primary)
    other, build_a, arm_a = read_group(args.ablation)
    if (build_a, arm_a) != (build, arm):
        raise SystemExit(f"the primary directories hold {build}, the ablation's {build_a}")
    wanted = [c.strip() for c in args.cohorts.split(",") if c.strip()]
    if wanted:
        for label, frame in ((PRIMARY, primary), (ablation, other)):
            missing = sorted(set(wanted) - set(frame["cohort"].astype(str)))
            if missing:
                raise SystemExit(f"--cohorts names {', '.join(missing)}, which the {label} "
                                 "directories do not hold")
        primary = primary[primary["cohort"].astype(str).isin(wanted)].reset_index(drop=True)
        other = other[other["cohort"].astype(str).isin(wanted)].reset_index(drop=True)
    models = sorted(primary["model"].unique())
    if sorted(other["model"].unique()) != models:
        raise SystemExit(f"the two matrices hold different models: {models} against "
                         f"{sorted(other['model'].unique())}")
    if args.control not in models:
        raise SystemExit(f"the control {args.control} holds no rows")
    identical = cells_identical(primary, other)
    print(f"build                 : {build}")
    print(f"ablation              : {ablation}, adds {matrix['added'] or 'nothing'}, removes "
          f"{matrix['removed'] or 'nothing'}")
    print(f"primary sources       : {', '.join(d.as_posix() for d in args.primary)}")
    print(f"ablation sources      : {', '.join(d.as_posix() for d in args.ablation)}")
    print(f"cells checked         : {identical['cells']} cells, {identical['rows']:,} rows on each "
          "matrix, identical rows and outcomes")

    scored = sorted(primary["cohort"].astype(str).unique())
    floor_of: dict[str, bool] | None = None
    if args.cells is not None:
        floor_of = bi.floor_verdicts(bi.read_floors(args.cells), args.cells, build, scored)

    table = pd.concat([cell_table(primary, PRIMARY), cell_table(other, ablation)],
                      ignore_index=True)
    table["context_seed"] = table["context_seed"].astype("Int64")
    if floor_of is not None:
        table["floor"] = table["cohort"].astype(str).map(floor_of)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out_dir / "cells.csv", index=False)

    both = pd.concat([primary.assign(model=primary["model"] + JOIN + PRIMARY),
                      other.assign(model=other["model"] + JOIN + ablation)], ignore_index=True)
    both["context_seed"] = both["context_seed"].astype("Int64")
    pooled, dropped_seeds = bi.shared_seeds(both)
    shared, dropped_cohorts = bi.shared_cohorts(pooled)
    cohorts, loaded = bi.load_cohorts(pooled, shared)
    under: list[str] = []
    if floor_of is None:
        bi.check_floors({f"{build} {c}": v.outcome for c, v in cohorts.items()}, None)
    else:
        under = [c for c in scored if not floor_of[c]]
        bi.check_floors({f"{build} {c}": v.outcome for c, v in cohorts.items() if floor_of[c]},
                        args.cells)
        cohorts = {c: v for c, v in cohorts.items() if floor_of[c]}
        shared = [c for c in shared if floor_of[c]]
        if not cohorts:
            raise SystemExit(f"{build}: no pooled cohort is above the floors; nothing pools")
    names = model_names(models)
    seeds = sorted({s for v in loaded.values() for s in v if s is not None})
    print(f"cohorts pooled        : {len(shared)} of {len(scored)} scored: {', '.join(shared)}")
    if floor_of is not None:
        print(f"floors                : {len(scored) - len(under)} of {len(scored)} cells above "
              f"the floors of {bi.FLOOR_ROWS:,} rows and {bi.FLOOR_DEFAULTS} defaults, the "
              f"verdict of {args.cells.as_posix()}")
        for cohort in under:
            print(f"  {cohort} left out of the pooling: under the floors")
    print(f"context seeds pooled  : {', '.join(map(str, seeds)) or 'none'}")
    unpooled_draws = {}
    for key, left in dropped_seeds.items():
        model, _, which = key.partition(JOIN)
        unpooled_draws.setdefault(model, left)
        if which == PRIMARY:
            print(f"  {model} draws {left} left out of the pooling: no other seeded model holds "
                  "them")
    unpooled_cohorts = {c: sorted({k.split(JOIN)[0] for k in cells})
                        for c, cells in dropped_cohorts.items()}
    if unpooled_cohorts:
        print(f"  {len(unpooled_cohorts)} cohorts left out of the pooling: not scored by every "
              "model")

    statistics = ablation_statistics(names, ablation, args.control)
    stage = time.time()
    result = mt.cohort_blocked_bootstrap_many(cohorts, statistics, resamples=args.resamples,
                                              seed=args.seed)
    print(f"bootstrap             : {args.resamples} resamples in {time.time() - stage:.0f}s")
    paired = pd.DataFrame(records_of(result, ablation, args.control, build))
    paired.to_csv(args.out_dir / "paired.csv", index=False)

    checked: dict | None = None
    seed_sensitive: set[str] = set()
    if check_seeds:
        repeats = []
        for check_seed in check_seeds:
            stage = time.time()
            again = mt.cohort_blocked_bootstrap_many(cohorts, statistics,
                                                     resamples=args.resamples, seed=check_seed)
            repeats += [r for r in records_of(again, ablation, args.control, build,
                                              bootstrap_seed=check_seed) if r["is_difference"]]
            print(f"bootstrap seed {check_seed:<8}: again in {time.time() - stage:.0f}s")
        repeats = pd.DataFrame(repeats)
        primary_rows = paired[paired["is_difference"]]
        checked = bi.seed_check(primary_rows, repeats)
        seed_sensitive = {f"{c['metric']}|{c['pair']}" for c in checked["star_changed"]}
        pd.concat([primary_rows.assign(bootstrap_seed=args.seed)[repeats.columns], repeats],
                  ignore_index=True).to_csv(args.out_dir / "paired-seeds.csv", index=False)

    print(f"\nper model, {PRIMARY} and {ablation}, and {ablation} minus {PRIMARY} "
          f"(value [lo, hi], * excludes zero"
          + (", ? star changes with the bootstrap seed" if checked else "") + "):")
    for metric in METRICS:
        for model in names:
            mean = paired[(paired["metric"] == metric) & (paired["kind"] == "mean")
                          & (paired["model"] == model)].set_index("matrix")
            gap = paired[(paired["metric"] == metric) & (paired["kind"] == "diff")
                         & (paired["model"] == model)].iloc[0]
            flag = ("*" if gap.excludes_zero else " ") + (
                "?" if f"{metric}|{gap.pair}" in seed_sensitive else " ")
            print(f"  {metric:<5} {model:<11} {mean.loc[PRIMARY].value:.4f}  "
                  f"{mean.loc[ablation].value:.4f}  {gap.value:+.4f} "
                  f"[{gap.ci_lo:+.4f}, {gap.ci_hi:+.4f}] {flag}")
    print(f"\nthe trigger: each model's difference minus {args.control}'s, on the same resample:")
    for metric in METRICS:
        for row in paired[(paired["metric"] == metric) & (paired["kind"] == "did")].itertuples():
            flag = ("*" if row.excludes_zero else " ") + (
                "?" if f"{metric}|{row.pair}" in seed_sensitive else " ")
            print(f"  {metric:<5} {row.model:<11} {row.value:+.4f} "
                  f"[{row.ci_lo:+.4f}, {row.ci_hi:+.4f}] {flag}")
    if checked:
        print(f"\nbootstrap seed check over seeds {', '.join(map(str, checked['seeds']))}: "
              f"{checked['starred']} of {checked['differences']} differences starred under seed "
              f"{args.seed}, {len(checked['star_changed'])} change their star, largest movement "
              f"of an interval bound {checked['largest_bound_movement']:.4f}")

    plot_differences(paired, names, ablation, args.control,
                     args.out_dir / "ablation-differences.png", len(shared), seeds, seed_sensitive)
    tfms = [m for m in names if m in ("tabpfn", "tabicl")]
    triggered = sorted({f"{r.model} ({r.metric})" for r in paired[
        (paired["kind"] == "did") & paired["model"].isin(tfms)].itertuples() if r.excludes_zero})
    summary = {
        "build_id": build,
        "arm": arm,
        "ablation": ablation,
        "matrices": matrix,
        "sources": {PRIMARY: [d.as_posix() for d in args.primary],
                    "ablation": [d.as_posix() for d in args.ablation]},
        "cell_check": identical,
        "models": {m: [s for s in loaded[f"{m}{JOIN}{PRIMARY}"] if s is not None] for m in names},
        "control": args.control,
        "cohorts": shared,
        "cohorts_pooled": len(shared),
        "cohorts_scored": len(scored),
        "cohorts_not_pooled": unpooled_cohorts,
        **({} if floor_of is None else {"floors": {
            "record": args.cells.as_posix(), "rows": bi.FLOOR_ROWS,
            "defaults": bi.FLOOR_DEFAULTS, "cells_above": len(scored) - len(under),
            "cells": len(scored),
            "reading": f"{len(scored) - len(under)} of {len(scored)} cells above the floors",
            "under": under,
            "rule": "a cell under the floors is in cells.csv with floor False and enters no "
                    "pooling"}}),
        "draws_not_pooled": unpooled_draws,
        "bootstrap": {"resamples": args.resamples, "seed": args.seed, "alpha": mt.ALPHA,
                      "blocking": "cohort, one row index per cohort applied to both matrices "
                                  "and every model",
                      "context_draw": ("drawn with the resample, jointly across models and "
                                       "matrices" if len(seeds) > 1 else
                                       "one draw shared by every seeded model, so every "
                                       "interval is conditional on it"),
                      "seed_check": checked,
                      "multiplicity": "none: every interval is reported at alpha on its own"},
        "statistics": {
            "mean": "per model and matrix, the mean over the pooled cohorts of the cohort's AUC "
                    "or Brier score",
            "diff": f"per model, the {ablation} mean minus the {PRIMARY} mean",
            "did": f"per model other than the control, its diff minus the control's diff on the "
                   f"same resample: (model_{ablation} - model_{PRIMARY}) - "
                   f"({args.control}_{ablation} - {args.control}_{PRIMARY})"},
        "trigger": {"statement": "a foundation model at its library settings (tabpfn, tabicl; "
                                 "not @t1) whose did interval excludes zero on the AUC or the "
                                 "Brier score",
                    "excludes_zero": triggered},
        "wall_seconds": round(time.time() - started, 1),
    }
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nwall                  : {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
