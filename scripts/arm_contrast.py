#!/usr/bin/env python3
"""How much a rolling training window actually differs from an expanding one.

The rolling arm exists to separate recency from volume: if a model built on the
last few quarters holds its calibration better than one built on the whole
book, recency is what mattered. That argument only works if the two windows are
different, and on a book whose volume grows the way this one does they may not
be. The last two years of an exponentially growing lender can be most of the
lender, which is why the study's window is one year and not the customary two.

Two quantities decide it, and both are readable from cohort sizes alone:

  * the **share** of the expanding pool that a k-quarter window still holds;
  * the **mean age** of a training row, in quarters before the label horizon,
    which is what the window is really manipulating and what a foundation model
    sees through its context sample.

Where the share is near one and the ages are close, the two arms are the same
experiment run twice, and no result from comparing them means anything. The
sweep over k says which widths would carry a contrast on this book.

    python scripts/record_run.py lc-arm-contrast -- \
        python scripts/arm_contrast.py data/raw/accepted_2007_to_2018Q4.csv.gz
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

from outoftime.label import LabelDefinition, add_months, build_labels
from outoftime.vintage import (
    DEFAULT_AS_OF,
    FIRST_COHORT,
    LABEL_LAG_MONTHS,
    ROLLING_QUARTERS,
    Quarter,
    quarters_between,
)

MONTH_YEAR = "%b-%Y"
WIDTHS = (2, 4, 6, 8, 12)


def cohort_sizes(path: Path) -> tuple[dict[Quarter, int], dt.date, int]:
    """Labelled loans per origination quarter, under the study's label."""
    frame = pd.read_csv(
        path, usecols=["issue_d", "loan_status", "last_pymnt_d"], low_memory=False)
    for column in ("issue_d", "last_pymnt_d"):
        frame[column] = pd.to_datetime(
            frame[column], format=MONTH_YEAR, errors="coerce")
    frame = frame.dropna(subset=["issue_d"]).reset_index(drop=True)
    snapshot = frame["last_pymnt_d"].max().date()

    def dates(series):
        return [None if pd.isna(v) else v.date() for v in series]

    origination = dates(frame["issue_d"])
    labelled = build_labels(
        origination=origination,
        status=list(frame["loan_status"]),
        last_payment=dates(frame["last_pymnt_d"]),
        definition=LabelDefinition(window_months=LABEL_LAG_MONTHS, snapshot=snapshot),
    )
    sizes: dict[Quarter, int] = {}
    for i in labelled.indices:
        quarter = Quarter.of(origination[i])
        sizes[quarter] = sizes.get(quarter, 0) + 1
    return sizes, snapshot, labelled.size


def mean_age(sizes: dict[Quarter, int], window: tuple[Quarter, ...]) -> float:
    """Mean age of a training row, in quarters before the newest one it holds.

    Weighted by rows rather than by quarter, because the model sees rows. On a
    growing book this pulls hard toward the recent end, which is the whole
    reason a rolling window can fail to be a rolling window.
    """
    newest = window[-1]
    weight = total = 0.0
    for quarter in window:
        rows = sizes.get(quarter, 0)
        age = (newest.year * 4 + newest.quarter) - (quarter.year * 4 + quarter.quarter)
        weight += rows * age
        total += rows
    return round(weight / total, 3) if total else float("nan")


def measure(sizes: dict[Quarter, int]) -> list[dict]:
    out = []
    for as_of in DEFAULT_AS_OF:
        horizon = add_months(as_of, -LABEL_LAG_MONTHS)
        newest = Quarter.of(horizon)
        expanding = quarters_between(FIRST_COHORT, newest)
        pool = sum(sizes.get(q, 0) for q in expanding)
        record = {
            "build_id": f"{as_of.year}H{1 if as_of.month <= 6 else 2}",
            "as_of": as_of.isoformat(),
            "newest_training_quarter": str(newest),
            "expanding_rows": pool,
            "expanding_quarters": len(expanding),
            "expanding_mean_age_quarters": mean_age(sizes, expanding),
            "rolling": {},
        }
        for width in WIDTHS:
            window = quarters_between(newest.shift(-(width - 1)), newest)
            window = tuple(q for q in window if q >= FIRST_COHORT)
            rows = sum(sizes.get(q, 0) for q in window)
            record["rolling"][str(width)] = {
                "quarters": len(window),
                "rows": rows,
                "share_of_expanding": round(rows / pool, 4) if pool else None,
                "mean_age_quarters": mean_age(sizes, window),
            }
        out.append(record)
    return out


def plot(records: list[dict], out: Path) -> None:
    """Share and mean age against build, one line per window width.

    The line to look at is the one at the study's width. If it sits near the
    top of the share panel and near the expanding line in the age panel, the
    rolling arm is not manipulating what it was meant to manipulate.
    """
    figure, (top, bottom) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    x = list(range(len(records)))
    ids = [r["build_id"] for r in records]
    shades = plt.cm.viridis([i / (len(WIDTHS) - 1) for i in range(len(WIDTHS))])

    for width, colour in zip(WIDTHS, shades):
        style = "-" if width == ROLLING_QUARTERS else "--"
        lw = 2.6 if width == ROLLING_QUARTERS else 1.4
        top.plot(x, [r["rolling"][str(width)]["share_of_expanding"] for r in records],
                 style, color=colour, linewidth=lw, marker="o", markersize=4,
                 label=f"{width} quarters")
        bottom.plot(x, [r["rolling"][str(width)]["mean_age_quarters"] for r in records],
                    style, color=colour, linewidth=lw, marker="o", markersize=4)

    bottom.plot(x, [r["expanding_mean_age_quarters"] for r in records],
                color="#b0392b", linewidth=2, marker="s", markersize=5,
                label="expanding")
    top.axhline(1.0, color="#20303a", linewidth=.8)
    top.set_ylabel("share of the expanding pool")
    top.set_ylim(0, 1.05)
    top.grid(axis="y", alpha=.25)
    top.legend(frameon=False, ncol=len(WIDTHS), fontsize=9, title="rolling window")
    top.set_title("What a rolling training window leaves out, and how much "
                  "younger it makes the training rows")
    bottom.set_ylabel("mean age of a training row, quarters")
    bottom.set_xlabel("build")
    bottom.set_xticks(x)
    bottom.set_xticklabels(ids)
    bottom.grid(axis="y", alpha=.25)
    bottom.legend(frameon=False, fontsize=9)

    figure.tight_layout()
    figure.savefig(out, dpi=140)
    plt.close(figure)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    sizes, snapshot, labelled = cohort_sizes(args.path)
    records = measure(sizes)
    print(f"snapshot from data    : {snapshot}")
    print(f"labelled loans        : {labelled:,}")
    print(f"study rolling width   : {ROLLING_QUARTERS} quarters\n")

    header = f"{'build':>7} {'expanding':>11} {'age':>6} " + " ".join(
        f"{'k=' + str(w):>15}" for w in WIDTHS)
    print(header)
    for record in records:
        cells = []
        for width in WIDTHS:
            roll = record["rolling"][str(width)]
            cells.append(f"{roll['share_of_expanding']:>7.0%}"
                         f" {roll['mean_age_quarters']:>6.2f}")
        print(f"{record['build_id']:>7} {record['expanding_rows']:>11,} "
              f"{record['expanding_mean_age_quarters']:>6.2f} "
              + " ".join(f"{c:>15}" for c in cells))

    at_study_width = [r["rolling"][str(ROLLING_QUARTERS)] for r in records]
    shares = [r["share_of_expanding"] for r in at_study_width]
    gaps = [r["expanding_mean_age_quarters"] - roll["mean_age_quarters"]
            for r, roll in zip(records, at_study_width)]
    print(f"\nat {ROLLING_QUARTERS} quarters the rolling window holds "
          f"{min(shares):.0%} to {max(shares):.0%} of the expanding pool")
    print(f"and makes the mean training row {min(gaps):.2f} to {max(gaps):.2f} "
          f"quarters younger")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "arm-contrast.json").write_text(
        json.dumps({
            "snapshot": snapshot.isoformat(),
            "label_lag_months": LABEL_LAG_MONTHS,
            "study_rolling_quarters": ROLLING_QUARTERS,
            "widths": list(WIDTHS),
            "builds": records,
        }, indent=2), encoding="utf-8")
    plot(records, args.out_dir / "arm-contrast.png")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
