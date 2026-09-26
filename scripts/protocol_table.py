#!/usr/bin/env python3
"""The published protocol beside this one, on the same rows and models.

Reads one build's in-time run of `in_time_folds.py` and the recorded
out-of-time scores of the same build, and puts every model's numbers under
the two protocols side by side. The in-time numbers are read on the
20,000-row test cell of each fold, which every model scores, so that the two
protocols and every model stand on identical rows; the out-of-time numbers
are the mean over the build's scored cohorts of the per-cell value, the same
cells the per-build pooling reads. Both carry the published benchmark's
twelve metrics — AUC, Gini, KS, average precision, Brier, log-loss, and six
classification metrics at the F1-optimal threshold chosen on the validation
fifth — and this study's four: the observed-over-expected ratio, the Cox
slope, the Brier score's miscalibration component and the PSI against the
rows the model was fitted on or conditioned on. The threshold is chosen in
time and applied out of time, which is what a deployment of the published
recipe would do.

A foundation model enters when its in-time cells, scored on a node from the
bundle the folds run packed, are named beside its out-of-time directories;
without them the table holds the classical models, which is the falsifying
run of EXP-004. Each such directory holds one fold, read from the names of
its cells, and its reference is read as that fold's context and no other's.
A row held twice under one fold, model and draw is refused.

The mean over cohorts is held to the floors of EXP-005 (5,000 labelled loans
and 100 defaults): under `--cells`, a cohort the build run's cells.csv puts
under them leaves the mean, and one it admits whose scored rows fall under
them is refused; without it, scored rows under the floors are refused.

    python scripts/record_run.py lc-2015h1e-protocols -- \\
        python scripts/protocol_table.py experiments/2026-09-12-lc-2015h1e-folds \\
            --out-of-time experiments/2026-09-11-lc-2015h1e-intervals-grid \\
            --out-dir experiments/2026-09-12-lc-2015h1e-protocols
"""

from __future__ import annotations

import argparse
import json
import re
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
from arm_intervals import expand_sources

from outoftime import metrics as mt

IN_TIME = "in time, random fold"
OUT_OF_TIME = "out of time, vintage cohorts"
PUBLISHED = ("auc", "gini", "ks", "average_precision", "brier", "log_loss", "accuracy",
             "balanced_accuracy", "f1", "precision", "recall", "mcc")
STUDY = ("observed_over_expected", "abs_log_oe", "cox_slope", "brier_miscalibration", "psi")
COLUMNS = ("rows", "defaults", "threshold", "predicted_positive_share", *PUBLISHED, *STUDY)


def cell_metrics(y: np.ndarray, s: np.ndarray, threshold: float, reference: np.ndarray
                 ) -> tuple[dict, mt.Cox]:
    """Every column of the table on one cell, against one threshold and one reference.

    Returns the Cox fit beside the columns. A fit that did not finish is not
    estimable: its slope is NaN in the columns, and the caller counts it
    rather than read it as a number.
    """
    area = mt.auc(y, s)
    at = mt.classification_at(y, s, threshold)
    fit = mt.cox(y, s)
    slope = fit.slope if fit.converged else float("nan")
    split = mt.murphy(y, s)
    stability = mt.psi(reference, s, edges=mt.psi_edges(reference))
    return {
        "rows": int(y.size), "defaults": int(y.sum()), "threshold": threshold,
        "predicted_positive_share": at.predicted_positive_share,
        "auc": area, "gini": 2 * area - 1, "ks": mt.ks(y, s),
        "average_precision": mt.average_precision(y, s), "brier": mt.brier(y, s),
        "log_loss": mt.log_loss(y, s), "accuracy": at.accuracy,
        "balanced_accuracy": at.balanced_accuracy, "f1": at.f1, "precision": at.precision,
        "recall": at.recall, "mcc": at.mcc,
        "observed_over_expected": mt.observed_over_expected(y, s).value,
        "abs_log_oe": abs(mt.log_oe(y, s)), "cox_slope": slope,
        "brier_miscalibration": split.miscalibration, "psi": stability.value,
    }, fit


def mean_over_cohorts(per_cohort: list[dict]) -> tuple[dict, int]:
    """Every column's mean over the cohorts, and how many cohorts the Cox slope's mean left out.

    A cohort whose Cox fit did not finish carries a NaN slope; it leaves that
    mean, and only that one, and is counted. Where every fit finished the
    mean is taken over the same values as every other column's.
    """
    mean = {}
    for column in COLUMNS:
        values = [c[column] for c in per_cohort]
        if column == "cox_slope":
            kept = [v for v in values if np.isfinite(v)]
            mean[column] = float(np.mean(kept)) if kept else float("nan")
        else:
            mean[column] = float(np.mean(values))
    left_out = sum(1 for c in per_cohort if not np.isfinite(c["cox_slope"]))
    return mean, left_out


def floor_pooling(scores: pd.DataFrame, build: str, path: Path | None
                  ) -> tuple[pd.DataFrame, list[str]]:
    """The out-of-time rows the mean over cohorts reads, and the cohorts the floors left out.

    Without the build run's cells.csv (`path` None) every cohort is read,
    and one whose scored rows fall under the floors is refused. With it, a
    cohort the file puts under the floors leaves the rows; one it admits
    whose scored rows fall under them is refused.
    """
    distinct = scores.drop_duplicates(["cohort", "row"])
    outcomes = {str(c): part["outcome"].to_numpy() for c, part in distinct.groupby("cohort")}
    if path is None:
        bi.check_floors({f"{build} {c}": y for c, y in outcomes.items()}, None)
        return scores, []
    floor = bi.floor_verdicts(bi.read_floors(path), path, build, sorted(outcomes))
    bi.check_floors({f"{build} {c}": y for c, y in outcomes.items() if floor[c]}, path)
    under = [c for c in sorted(outcomes) if not floor[c]]
    if len(under) == len(outcomes):
        raise SystemExit(f"{build}: no cohort is above the floors; nothing is read out of time")
    return scores[~scores["cohort"].astype(str).isin(under)].reset_index(drop=True), under


def cell_key(model: str, seed) -> tuple[str, int | None]:
    return model, (None if pd.isna(seed) else int(seed))


def load_scores(dirs: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    scores = pd.concat([pd.read_parquet(d / "scores.parquet") for d in dirs], ignore_index=True)
    reference = pd.concat([pd.read_parquet(d / "reference.parquet") for d in dirs],
                          ignore_index=True)
    return scores, reference


FOLD_CELL = re.compile(r"^fold(\d+)-(test|validation)$")


def load_node_scores(dirs: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A foundation model's in-time scores, each directory given the fold it scored.

    A node scores one fold's bundle and writes its cells under the cohort
    names the folds run gave them, `fold<k>-test` and `fold<k>-validation`,
    with no fold column: the fold and the part are read from that name. Its
    reference is the context of that one fold, and carries the fold too,
    because the folds partition one pool and a row sits in the context of
    up to four of them, each time with another probability. Pooled without
    the fold, one fold's stability index would be read against five folds'
    contexts. A directory whose cells name more than one fold, or a cell
    name of another shape, is refused.
    """
    scores, references = [], []
    for d in dirs:
        s = pd.read_parquet(d / "scores.parquet")
        r = pd.read_parquet(d / "reference.parquet")
        names = s["cohort"].astype(str)
        parsed = names.str.extract(FOLD_CELL)
        if parsed[0].isna().any():
            odd = sorted(set(names[parsed[0].isna()]))
            raise SystemExit(f"{d.as_posix()}: cells {odd} are not named fold<k>-test or "
                             "fold<k>-validation")
        folds = sorted({int(f) for f in parsed[0]})
        if len(folds) != 1:
            raise SystemExit(f"{d.as_posix()}: cells of folds {folds} in one directory; a "
                             "node directory scores one fold's bundle")
        for frame in (s, r):
            if "fold" in frame.columns and set(frame["fold"].dropna().astype(int)) - set(folds):
                raise SystemExit(f"{d.as_posix()}: a fold column naming another fold")
        s["fold"] = folds[0]
        s["part"] = parsed[1].to_numpy()
        r["fold"] = folds[0]
        scores.append(s)
        references.append(r)
    return pd.concat(scores, ignore_index=True), pd.concat(references, ignore_index=True)


def refuse_duplicate_keys(scores: pd.DataFrame, reference: pd.DataFrame) -> None:
    """Each scored row and each reference row is held once per fold, model and draw.

    Two directories scoring the same fold for the same model, a scored run
    beside a derived one of the same label for instance, would otherwise
    enter every mean twice without any output showing it.
    """
    for name, frame, key in (("scores", scores, ["fold", "model", "context_seed", "cohort", "row"]),
                             ("reference", reference, ["fold", "model", "context_seed", "row"])):
        repeated = frame.duplicated(key, keep=False)
        if repeated.any():
            first = frame[repeated].iloc[0]
            raise SystemExit(f"{name}: {int(repeated.sum())} rows share a key "
                             f"({', '.join(key)}), the first fold {first['fold']} "
                             f"{first['model']}/{first['context_seed']}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folds_dirs", type=Path, nargs="+",
                        help="recorded runs of in_time_folds.py on one build, together holding "
                             "the folds to read")
    parser.add_argument("--in-time-tfm", type=Path, nargs="*", default=[],
                        help="node directories holding the foundation models' scores on the "
                             "folds run's cells, with their context references")
    parser.add_argument("--out-of-time", type=Path, nargs="+", required=True,
                        help="the build's out-of-time score directories, or a recorded pooling "
                             "whose intervals.json names them")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--cells", type=Path, default=None,
                        help="the build run's cells.csv: a cohort it puts under the floors "
                             "leaves the mean over cohorts")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()

    thresholds: dict[tuple[int, str, int | None], float] = {}
    builds_seen: set[str] = set()
    fold_seeds: set[int] = set()
    for folds_dir in args.folds_dirs:
        folds = json.loads((folds_dir / "folds.json").read_text(encoding="utf-8"))
        builds_seen.add(folds["build"]["build_id"])
        fold_seeds.add(int(folds["protocol"]["fold_seed"]))
        for t in folds["thresholds"]:
            key = (t["fold"], t["model"], t["context_seed"])
            if key in thresholds:
                raise SystemExit(f"fold {t['fold']} of {t['model']} is in two folds runs")
            thresholds[key] = t["threshold"]
    if len(builds_seen) != 1 or len(fold_seeds) != 1:
        raise SystemExit("the folds runs are not one build under one fold seed")
    build = builds_seen.pop()
    in_scores, in_reference = load_scores(args.folds_dirs)
    if "fold" not in in_scores.columns or "fold" not in in_reference.columns:
        raise SystemExit("the in-time scores carry no fold column")
    if args.in_time_tfm:
        node_scores, node_reference = load_node_scores(args.in_time_tfm)
        in_scores = pd.concat([in_scores, node_scores], ignore_index=True)
        in_reference = pd.concat([in_reference, node_reference], ignore_index=True)
    refuse_duplicate_keys(in_scores, in_reference)
    cells = pd.concat([pd.read_parquet(d / "scored.parquet", columns=["cohort", "row"])
                       for d in args.folds_dirs], ignore_index=True)
    cell_rows = {name: set(part["row"]) for name, part in cells.groupby("cohort")}

    out_dirs = expand_sources(args.out_of_time)
    out_scores, out_reference = load_scores(out_dirs)
    if out_scores["build_id"].nunique() != 1 or out_scores["build_id"].iloc[0] != build:
        raise SystemExit("the out-of-time scores are not the folds run's build")
    out_scores, under = floor_pooling(out_scores, build, args.cells)
    if args.cells is not None:
        read = out_scores["cohort"].nunique()
        print(f"floors                : {read} of {read + len(under)} cells above the floors, the "
              f"verdict of {args.cells.as_posix()}"
              + ("" if not under else f"; left out of the mean: {', '.join(under)}"))

    # A foundation model's threshold is chosen on its own validation cell,
    # as the classical models' were on the whole fifth.
    for (fold, model, seed), part in in_scores[in_scores["part"] == "validation"].groupby(
            ["fold", "model", "context_seed"], dropna=False):
        key = (int(fold), model, None if pd.isna(seed) else int(seed))
        if key not in thresholds:
            thresholds[key] = mt.f1_threshold(part["outcome"].to_numpy(),
                                              part["pd"].to_numpy(dtype=float))

    records: list[dict] = []
    not_estimable: list[dict] = []
    # In time: every model on the fold's 20,000-row test cell.
    for (fold, model, seed), part in in_scores[in_scores["part"] == "test"].groupby(
            ["fold", "model", "context_seed"], dropna=False):
        fold = int(fold)
        model_seed = cell_key(model, seed)
        cell = part[part["row"].isin(cell_rows[f"fold{fold}-test"])].sort_values("row")
        if cell.empty:
            raise SystemExit(f"fold {fold}: {model} scored none of the test cell's rows")
        ref = in_reference[(in_reference["model"] == model)
                           & (in_reference["context_seed"].isna() if model_seed[1] is None
                              else in_reference["context_seed"] == model_seed[1])]
        ref = ref[ref["fold"] == fold]
        if ref.empty:
            raise SystemExit(f"fold {fold}: {model} has no reference rows for this fold")
        threshold = thresholds[(fold, model, model_seed[1])]
        values, fit = cell_metrics(cell["outcome"].to_numpy(), cell["pd"].to_numpy(dtype=float),
                                   threshold, ref["pd"].to_numpy(dtype=float))
        if not fit.converged:
            not_estimable.append({"protocol": IN_TIME, "model": model,
                                  "context_seed": model_seed[1], "cell": f"fold {fold} test",
                                  "iterations": fit.iterations})
        records.append({"protocol": IN_TIME, "model": model, "context_seed": model_seed[1],
                        "unit": f"fold {fold}", **values})
    # Out of time: the same models on every cohort of the build, the
    # threshold of each fold applied in turn, so the fold's spread is carried.
    fold_ids = sorted({int(f) for f in in_scores["fold"].unique()})
    for (model, seed), part in out_scores.groupby(["model", "context_seed"], dropna=False):
        model_seed = cell_key(model, seed)
        if not any(k[1] == model for k in thresholds):
            continue
        ref = out_reference[(out_reference["model"] == model)
                            & (out_reference["context_seed"].isna() if model_seed[1] is None
                               else out_reference["context_seed"] == model_seed[1])]
        for fold in fold_ids:
            if (fold, model, model_seed[1]) not in thresholds:
                continue
            threshold = thresholds[(fold, model, model_seed[1])]
            per_cohort = []
            for cohort, cell in part.groupby("cohort"):
                cell = cell.sort_values("row")
                values, fit = cell_metrics(cell["outcome"].to_numpy(),
                                           cell["pd"].to_numpy(dtype=float), threshold,
                                           ref["pd"].to_numpy(dtype=float))
                # The Cox fit does not depend on the threshold: one entry per cohort.
                if not fit.converged and fold == fold_ids[0]:
                    not_estimable.append({"protocol": OUT_OF_TIME, "model": model,
                                          "context_seed": model_seed[1], "cell": str(cohort),
                                          "iterations": fit.iterations})
                per_cohort.append(values)
            mean, _ = mean_over_cohorts(per_cohort)
            mean["rows"] = int(sum(c["rows"] for c in per_cohort))
            mean["defaults"] = int(sum(c["defaults"] for c in per_cohort))
            records.append({"protocol": OUT_OF_TIME, "model": model,
                            "context_seed": model_seed[1],
                            "unit": f"{len(per_cohort)} cohorts, threshold of fold {fold}",
                            **mean})
    table = pd.DataFrame(records)
    table["context_seed"] = table["context_seed"].astype("Int64")
    table.to_csv(args.out_dir / "cells.csv", index=False)
    print(f"Cox not estimable     : {len(not_estimable)} cells whose fit did not finish"
          + ("" if not not_estimable else ": " + ", ".join(
              f"{c['protocol']} {c['model']}"
              + ("" if c["context_seed"] is None else f"/{c['context_seed']}")
              + f" {c['cell']} ({c['iterations']} steps)" for c in not_estimable))
          + "; an in-time cell reads NaN, an out-of-time cohort leaves the Cox slope's mean")

    # The two rows: per protocol and model, the mean over folds and seeds and
    # the spread across them.
    summary = table.groupby(["protocol", "model"])[list(COLUMNS)].agg(["mean", "min", "max"])
    summary.columns = [f"{metric}_{stat}" for metric, stat in summary.columns]
    summary = summary.reset_index()
    summary.to_csv(args.out_dir / "table.csv", index=False)

    models = [m for m in bi.MODEL_ORDER if m in set(table["model"])] + sorted(
        set(table["model"]) - set(bi.MODEL_ORDER))
    preface = (f"In time: the 20,000-row test cell of each of {len(fold_ids)} fold(s); out of "
               "time: the mean over the build's scored cohorts. Each entry is the mean over "
               "folds and context seeds, with the spread across them in brackets where it "
               "exceeds the fourth decimal.")
    lines = [f"# {build}: the published protocol beside this one", "", preface, ""]
    for metric in (*PUBLISHED, *STUDY, "predicted_positive_share", "threshold"):
        lines.append(f"| {metric} | " + " | ".join(models) + " |")
        lines.append("|---|" + "---|" * len(models))
        for protocol in (IN_TIME, OUT_OF_TIME):
            row = [protocol]
            for model in models:
                sub = summary[(summary["protocol"] == protocol) & (summary["model"] == model)]
                if sub.empty:
                    row.append("")
                    continue
                mean, lo, hi = (float(sub[f"{metric}_{s}"].iloc[0]) for s in ("mean", "min", "max"))
                text = f"{mean:.4f}"
                if hi - lo > 5e-5:
                    text += f" [{lo:.4f}, {hi:.4f}]"
                row.append(text)
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
    # The rankings under each protocol, on the metrics a reader ranks by.
    for metric, better in (("auc", "high"), ("brier", "low"), ("log_loss", "low"),
                           ("abs_log_oe", "low"), ("f1", "high")):
        lines.append(f"Ranking on {metric} ({better} is better):")
        for protocol in (IN_TIME, OUT_OF_TIME):
            sub = summary[summary["protocol"] == protocol].set_index("model")
            order = sub[f"{metric}_mean"].sort_values(ascending=(better == "low"))
            lines.append(f"- {protocol}: " + " > ".join(
                f"{m} ({v:.4f})" for m, v in order.items()))
        lines.append("")
    (args.out_dir / "table.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))

    plot_reliability(in_scores, out_scores, cell_rows, models, fold_ids[0],
                     args.out_dir / "reliability-protocols.png")
    plot_precision_recall(in_scores, out_scores, cell_rows, thresholds, models, fold_ids[0],
                          args.out_dir / "precision-recall.png")

    description = {
        "build": build,
        "folds_runs": [d.as_posix() for d in args.folds_dirs],
        "in_time_tfm": [d.as_posix() for d in args.in_time_tfm],
        "out_of_time": [d.as_posix() for d in out_dirs],
        "folds": fold_ids,
        "models": models,
        "in_time_rows": "the fold's 20,000-row test cell, scored by every model",
        "out_of_time_rows": "every scored cohort of the build, the mean over cohorts of the "
                            "per-cell value; the threshold of each fold applied in turn",
        "threshold": "the score maximising F1 on the fold's validation fifth, per model and "
                     "seed; a foundation model's on its validation cell",
        "psi_reference": "the rows the model was fitted on or conditioned on, in time the "
                         "fold's four fifths or its context sample, out of time the build's "
                         "training pool or its context draw",
        "thresholds": {f"{k[0]}/{k[1]}/{k[2]}": v for k, v in thresholds.items()},
        "cox_not_estimable": not_estimable,
        **({} if args.cells is None else {"floors": {
            "record": args.cells.as_posix(), "rows": bi.FLOOR_ROWS,
            "defaults": bi.FLOOR_DEFAULTS, "under": under,
            "rule": "a cohort under the floors leaves the out-of-time mean over cohorts"}}),
        "wall_seconds": round(time.time() - started, 1),
    }
    (args.out_dir / "protocols.json").write_text(json.dumps(description, indent=2),
                                                 encoding="utf-8")
    print(f"\nwall                  : {time.time() - started:.0f}s")
    return 0


def first_cell(scores: pd.DataFrame, model: str, rows: set[int] | None = None) -> pd.DataFrame:
    """One model's rows on its first context seed, restricted to a cell when given."""
    part = scores[scores["model"] == model]
    seeds = part["context_seed"].dropna().unique()
    if seeds.size:
        part = part[part["context_seed"] == min(seeds)]
    if rows is not None:
        part = part[part["row"].isin(rows)]
    return part.sort_values("row")


def plot_reliability(in_scores, out_scores, cell_rows, models, fold, out: Path) -> None:
    """Each model's reliability curve in time and on the youngest and oldest cohort out of time."""
    fig, axes = plt.subplots(1, len(models), figsize=(3.8 * len(models), 4.0))
    axes = np.atleast_1d(axes)
    cohorts = sorted(out_scores["cohort"].unique())
    for ax, model in zip(axes, models):
        colour = bi.model_colour(model)
        top = 0.0
        sets = [("in time, test cell", "-",
                 first_cell(in_scores[in_scores["part"] == "test"], model,
                            cell_rows[f"fold{fold}-test"]))]
        if model in set(out_scores["model"]):
            sets += [(f"out of time, {cohorts[0]}", "--",
                      first_cell(out_scores[out_scores["cohort"] == cohorts[0]], model)),
                     (f"out of time, {cohorts[-1]}", ":",
                      first_cell(out_scores[out_scores["cohort"] == cohorts[-1]], model))]
        for label, style, frame in sets:
            if frame.empty:
                continue
            curve = mt.reliability(frame["outcome"].to_numpy(), frame["pd"].to_numpy(dtype=float))
            x, y = np.array(curve.mean_score), np.array(curve.observed)
            ax.errorbar(x, y, yerr=[y - np.array(curve.lo), np.array(curve.hi) - y], color=colour,
                        linestyle=style, marker="o", markersize=3, capsize=2, linewidth=1.2,
                        label=label)
            top = max(top, float(np.nanmax(np.array(curve.hi))), float(np.nanmax(x)))
        limit = top * 1.05 if top > 0 else 1.0
        ax.plot([0, limit], [0, limit], color="black", linewidth=0.8, linestyle=":")
        ax.set_xlim(0, limit)
        ax.set_ylim(0, limit)
        ax.set_title(bi.describe(model), fontsize=9)
        ax.set_xlabel("mean predicted probability in the bin")
        ax.legend(frameon=False, fontsize=7)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("observed default rate, binomial interval")
    fig.suptitle("reliability, ten quantile bins: the in-time test cell and the youngest and "
                 "oldest cohort out of time", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out, dpi=130)
    plt.close(fig)


def precision_recall_curve(y: np.ndarray, s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    order = np.argsort(-s, kind="stable")
    tp = np.cumsum(y[order])
    positives = max(int(y.sum()), 1)
    return tp / positives, tp / np.arange(1, y.size + 1)


def plot_precision_recall(in_scores, out_scores, cell_rows, thresholds, models, fold,
                          out: Path) -> None:
    """Each model's precision–recall curve in time and out of time, the in-time threshold marked."""
    fig, axes = plt.subplots(1, len(models), figsize=(3.8 * len(models), 4.0), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, model in zip(axes, models):
        colour = bi.model_colour(model)
        sets = [("in time, test cell", "-",
                 first_cell(in_scores[in_scores["part"] == "test"], model,
                            cell_rows[f"fold{fold}-test"]))]
        if model in set(out_scores["model"]):
            sets.append(("out of time, every cohort", "--", first_cell(out_scores, model)))
        for label, style, frame in sets:
            if frame.empty:
                continue
            y = frame["outcome"].to_numpy()
            s = frame["pd"].to_numpy(dtype=float)
            recall, precision = precision_recall_curve(y, s)
            ax.plot(recall, precision, color=colour, linestyle=style, linewidth=1.2, label=label)
            seeds = frame["context_seed"].dropna().unique()
            key = (fold, model, None if not seeds.size else int(min(seeds)))
            if key in thresholds:
                at = mt.classification_at(y, s, thresholds[key])
                ax.plot(at.recall, at.precision, marker="o", markersize=6, color=colour,
                        markerfacecolor="white" if style != "-" else colour, linestyle="none")
        ax.axhline(float(np.mean(sets[0][2]["outcome"])) if not sets[0][2].empty else 0.0,
                   color="black", linewidth=0.8, linestyle=":", label="the default rate")
        ax.set_title(bi.describe(model), fontsize=9)
        ax.set_xlabel("recall")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 0.5)
        ax.legend(frameon=False, fontsize=7)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("precision")
    fig.suptitle("precision against recall, the F1-optimal threshold of the validation fifth "
                 "marked (filled in time, hollow out of time)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out, dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
