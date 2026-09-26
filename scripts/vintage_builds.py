#!/usr/bin/env python3
"""Materialises the build grid on a real book, and shows what each build saw.

The grid is nine as-of dates by two training arms, and every model in the study
is fitted on these and no others. Before any model exists it is worth seeing the
grid itself: how much book each build gets, how much of it a fifty-thousand-row
context can hold, and how far the training pool's default rate sits from the
rate of the cohorts the build is then scored on.

The third of those is the one with teeth. A build trained on a 2% book and
scored on a 3.4% book will lose calibration-in-the-large no matter which model
is fitted, so the distance between those two numbers is the size of the effect
every model has to be judged against. It is a property of the design, and it can
be read off before a single forward pass.

    python scripts/record_run.py lc-vintage-builds -- \
        python scripts/vintage_builds.py data/raw/accepted_2007_to_2018Q4.csv.gz
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from outoftime.label import LabelDefinition, build_labels
from outoftime.vintage import (
    CONTEXT_ROWS,
    DEFAULT_AS_OF,
    FIRST_COHORT,
    LABEL_LAG_MONTHS,
    LAST_TEST_COHORT,
    ROLLING_QUARTERS,
    TEST_SAMPLE_SEED,
    Quarter,
    builds,
    quarters_between,
    scoring_samples,
)

MONTH_YEAR = "%b-%Y"
ARMS = {"E": "expanding", "R": f"rolling, {ROLLING_QUARTERS} quarters"}
ARM_COLOUR = {"E": "#0E6B66", "R": "#9A5B24"}


def load(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        usecols=["issue_d", "loan_status", "last_pymnt_d"],
        low_memory=False,
    )
    for column in ("issue_d", "last_pymnt_d"):
        frame[column] = pd.to_datetime(
            frame[column], format=MONTH_YEAR, errors="coerce")
    return frame.dropna(subset=["issue_d"]).reset_index(drop=True)


def to_dates(series: pd.Series) -> list[dt.date | None]:
    return [None if pd.isna(v) else v.date() for v in series]


def describe(grid, labels: list[int | None]) -> list[dict]:
    """Per build: its shape, and the default rate on both sides of the gap."""
    out = []
    for build in grid:
        record = build.as_dict()
        record["context_rows"] = min(CONTEXT_ROWS, len(build.train))
        record["context_covers_pool"] = len(build.train) <= CONTEXT_ROWS
        record["train_default_rate"] = _rate(build.train, labels)
        record["cohort_default_rate"] = {
            str(quarter): _rate(rows, labels) for quarter, rows in build.test
        }
        out.append(record)
    return out


def _rate(rows, labels: list[int | None]) -> float | None:
    values = [labels[i] for i in rows if labels[i] is not None]
    return round(sum(values) / len(values), 5) if values else None


def plot(summary: dict, out: Path) -> None:
    """Three views of the grid, none of which is a bar of a headline number.

    The top panel is the design itself on a calendar: what each build trains
    on, what it cannot see, and what it is scored on. The middle is where the
    expanding arm stops expanding for a foundation model, since past the
    context cap a larger pool is a larger sample of the same size. The bottom
    is the base-rate distance the models are asked to carry.
    """
    axis = quarters_between(FIRST_COHORT, LAST_TEST_COHORT)
    position = {str(q): i for i, q in enumerate(axis)}
    ids = [b["build_id"][:-2] for b in summary["arms"]["E"]]
    rows = {name: len(ids) - 1 - i for i, name in enumerate(ids)}

    figure, (top, middle, bottom) = plt.subplots(
        3, 1, figsize=(13, 12), height_ratios=(3, 2, 2))

    # --- the grid on a calendar ---
    for arm, offset, height in (("E", .18, .3), ("R", -.18, .3)):
        for build in summary["arms"][arm]:
            y = rows[build["build_id"][:-2]] + offset
            train = build["train_quarters"]
            left = position[train[0]]
            top.barh(y, position[train[-1]] - left + 1, left=left, height=height,
                     color=ARM_COLOUR[arm], alpha=.85,
                     label=ARMS[arm] if build is summary["arms"][arm][0] else None)
    for build in summary["arms"]["E"]:
        y = rows[build["build_id"][:-2]]
        blind_from = position[str(Quarter.of(dt.date.fromisoformat(
            build["knowable_through"])).shift(1))]
        blind_to = position[str(Quarter.of(dt.date.fromisoformat(build["as_of"])))]
        top.barh(y, blind_to - blind_from + 1, left=blind_from, height=.66,
                 facecolor="none", edgecolor="#b0392b", hatch="///", linewidth=.8,
                 label="blind gap" if build is summary["arms"]["E"][0] else None)
        scored = [position[c] + .5 for c in build["test_cohorts"]]
        top.plot(scored, [y] * len(scored), linestyle="none", marker="o",
                 markersize=4, color="#20303a",
                 label="scored" if build is summary["arms"]["E"][0] else None)
    top.set_yticks(list(rows.values()))
    top.set_yticklabels(list(rows), fontsize=9)
    top.set_ylabel("build")
    top.legend(frameon=False, ncol=4, fontsize=9, loc="lower left",
               bbox_to_anchor=(0, 1.02))
    top.set_title(
        "What each build was allowed to know: training window, the twelve months "
        "it could not see, and the cohorts it is scored on", pad=28)

    # --- where the pool outgrows the context ---
    x = list(range(len(ids)))
    for arm, name in ARMS.items():
        middle.plot(x, [b["train_rows"] for b in summary["arms"][arm]],
                    marker="o", color=ARM_COLOUR[arm], linewidth=2, label=name)
    middle.axhline(CONTEXT_ROWS, color="#b0392b", linestyle="--", linewidth=1.2,
                   label=f"context cap, {CONTEXT_ROWS:,} rows")
    middle.set_yscale("log")
    middle.set_ylabel("rows in the training pool")
    middle.set_xticks(x)
    middle.set_xticklabels(ids, fontsize=9)
    middle.grid(axis="y", alpha=.25)
    middle.legend(frameon=False, fontsize=9)

    # --- the base-rate distance ---
    for arm, name in ARMS.items():
        bottom.plot(
            [position[summary["arms"][arm][i]["train_quarters"][-1]] + .5
             for i in x],
            [b["train_default_rate"] for b in summary["arms"][arm]],
            linestyle="none", marker="s", markersize=7, color=ARM_COLOUR[arm],
            label=f"training pool, {name}")
    cohort_rate = summary["cohort_default_rate"]
    bottom.plot([position[c] + .5 for c in cohort_rate], list(cohort_rate.values()),
                color="#20303a", linewidth=1.6, marker="o", markersize=3,
                label="scored cohort, on the sampled rows")
    bottom.set_ylabel(f"{summary['label_lag_months']}-month default rate")
    bottom.yaxis.set_major_formatter(lambda v, _: f"{v:.1%}")
    bottom.set_xlabel("origination quarter")
    step = max(1, len(axis) // 24)
    bottom.set_xticks(list(range(len(axis)))[::step])
    bottom.set_xticklabels([str(q) for q in axis][::step], rotation=90, fontsize=8)
    bottom.grid(axis="y", alpha=.25)
    bottom.legend(frameon=False, fontsize=9)

    top.set_xlim(-.5, len(axis) + .5)
    bottom.set_xlim(-.5, len(axis) + .5)
    top.set_xticks(list(range(len(axis)))[::step])
    top.set_xticklabels([str(q) for q in axis][::step], rotation=90, fontsize=8)

    figure.tight_layout()
    figure.savefig(out, dpi=140)
    plt.close(figure)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    frame = load(args.path)
    snapshot = frame["last_pymnt_d"].max().date()
    origination = to_dates(frame["issue_d"])
    print(f"rows                  : {len(frame):,}")
    print(f"snapshot from data    : {snapshot}")

    labelled = build_labels(
        origination=origination,
        status=list(frame["loan_status"]),
        last_payment=to_dates(frame["last_pymnt_d"]),
        definition=LabelDefinition(window_months=LABEL_LAG_MONTHS, snapshot=snapshot),
    )
    labels: list[int | None] = [None] * len(frame)
    for i, value in zip(labelled.indices, labelled.labels):
        labels[i] = value
    print(f"labelled              : {labelled.size:,}")
    print(f"dropped immature      : {len(labelled.dropped_immature):,}\n")

    samples = scoring_samples(origination, eligible=labelled.indices)
    summary: dict = {
        "snapshot": snapshot.isoformat(),
        "label_lag_months": LABEL_LAG_MONTHS,
        "as_of_dates": [d.isoformat() for d in DEFAULT_AS_OF],
        "first_cohort": str(FIRST_COHORT),
        "last_cohort": str(LAST_TEST_COHORT),
        "label": labelled.as_dict(),
        "seeds": {"test_sample": TEST_SAMPLE_SEED},
        "scoring_sample": {str(q): len(rows) for q, rows in samples.items()},
        "cohort_default_rate": {
            str(q): _rate(rows, labels) for q, rows in samples.items()},
        "arms": {},
    }

    for arm in ARMS:
        grid = builds(origination, arm=arm, labels=labelled)
        summary["arms"][arm] = describe(grid, labels)
        del grid

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "builds.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    plot(summary, args.out_dir / "build-grid.png")

    header = (f"{'build':>9} {'train':>10} {'quarters':>9} {'blind':>9} "
              f"{'cohorts':>8} {'scored':>9} {'train PD':>9} {'scored PD':>10}")
    for arm, name in ARMS.items():
        print(f"--- arm {arm}: {name} ---")
        print(header)
        for build in summary["arms"][arm]:
            rates = [v for v in build["cohort_default_rate"].values() if v is not None]
            scored_pd = sum(rates) / len(rates) if rates else float("nan")
            print(f"{build['build_id']:>9} {build['train_rows']:>10,} "
                  f"{len(build['train_quarters']):>9} {build['blind_rows']:>9,} "
                  f"{len(build['test_cohorts']):>8} {build['test_rows']:>9,} "
                  f"{build['train_default_rate']:>8.2%} {scored_pd:>10.2%}")
        print()

    capped = [b["build_id"] for b in summary["arms"]["E"]
              if not b["context_covers_pool"]]
    print(f"expanding builds whose pool exceeds the {CONTEXT_ROWS:,}-row context: "
          f"{len(capped)} of {len(summary['arms']['E'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
