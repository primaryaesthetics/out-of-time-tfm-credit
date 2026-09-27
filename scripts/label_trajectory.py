#!/usr/bin/env python3
"""The default rate of each origination cohort, under both label windows.

This is the backbone the study is measured against. Every later claim about a
model losing calibration across vintages has to be read against what the book
itself did, because a book whose credit quality moved will move any model's
calibration with it, and that is not the model's failure.

Both windows from ADR-0005 are computed side by side. Where the twelve-month
and twenty-four-month trajectories disagree, the disagreement is reported and
not averaged: it is the honest width of what a single window can tell you.

The snapshot is read from the data rather than assumed. It is the last date on
which performance is observable, and it sets how far the labelled trajectory
can run.

    python scripts/record_run.py lc-label-trajectory -- \
        python scripts/label_trajectory.py data/raw/accepted_2007_to_2018Q4.csv.gz
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

MONTH_YEAR = "%b-%Y"
WINDOWS = (12, 24)

# A cohort carries a rate only if it carries enough loans to bound one, and
# enough defaults for the bound to be narrow. Without a floor the extremes of
# the series are properties of cohort size rather than of credit: this book's
# oldest quarter holds twenty-four loans and its second-oldest three hundred
# and eighty-nine, and an unrestricted minimum and maximum land on those every
# time. Both conditions are applied, and the floors are stated in the output so
# that a quoted extreme names the population it was taken over.
MIN_LOANS = 5_000
MIN_DEFAULTS = 100


def wilson(defaults: int, size: int, z: float = 1.96) -> tuple[float, float]:
    """Score interval for a proportion. Sound at the small counts here."""
    if size == 0:
        return (float("nan"), float("nan"))
    p = defaults / size
    denominator = 1 + z * z / size
    centre = (p + z * z / (2 * size)) / denominator
    half = z * ((p * (1 - p) / size + z * z / (4 * size * size)) ** 0.5) / denominator
    return (round(max(0.0, centre - half), 5), round(min(1.0, centre + half), 5))


def load(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        usecols=["issue_d", "loan_status", "last_pymnt_d"],
        low_memory=False,
    )
    for column in ("issue_d", "last_pymnt_d"):
        frame[column] = pd.to_datetime(
            frame[column], format=MONTH_YEAR, errors="coerce")
    return frame.dropna(subset=["issue_d"])


def to_dates(series: pd.Series) -> list[dt.date | None]:
    """pandas timestamps to plain dates, keeping the missing ones missing."""
    return [None if pd.isna(v) else v.date() for v in series]


def trajectory(frame: pd.DataFrame, window: int, snapshot: dt.date) -> dict:
    labels = build_labels(
        origination=to_dates(frame["issue_d"]),
        status=list(frame["loan_status"]),
        last_payment=to_dates(frame["last_pymnt_d"]),
        definition=LabelDefinition(window_months=window, snapshot=snapshot),
    )
    kept = frame.iloc[list(labels.indices)]
    by_cohort = pd.DataFrame({
        "cohort": kept["issue_d"].dt.to_period("Q").astype(str),
        "label": list(labels.labels),
    })
    grouped = by_cohort.groupby("cohort")["label"]
    sizes = {k: int(v) for k, v in grouped.size().items()}
    counts = {k: int(v) for k, v in grouped.sum().items()}
    return {
        "window_months": window,
        "summary": labels.as_dict(),
        "cohort_default_rate": {
            k: round(float(v), 5) for k, v in grouped.mean().items()},
        "cohort_size": sizes,
        "cohort_defaults": counts,
        "cohort_interval": {
            k: wilson(counts[k], sizes[k]) for k in sizes},
        "floor_for_a_reported_extreme": {
            "loans": MIN_LOANS, "defaults": MIN_DEFAULTS},
        "cohorts_clearing_the_floor": sorted(
            k for k in sizes
            if sizes[k] >= MIN_LOANS and counts[k] >= MIN_DEFAULTS),
    }


def plot(results: list[dict], out: Path) -> None:
    """Both trajectories on one axis, with cohort size underneath.

    The shape being looked for is whether the book's own risk moved. A model
    evaluated across a moving book has to be judged against this line, not
    against a flat expectation.
    """
    figure, (top, bottom) = plt.subplots(
        2, 1, figsize=(13, 7), height_ratios=(2, 1), sharex=True)

    widest = max(results, key=lambda r: len(r["cohort_default_rate"]))
    cohorts = list(widest["cohort_default_rate"])
    positions = {c: i for i, c in enumerate(cohorts)}

    for result, colour in zip(results, ("#0E6B66", "#9A5B24")):
        rates = result["cohort_default_rate"]
        x = [positions[c] for c in rates if c in positions]
        y = [rates[c] for c in rates if c in positions]
        top.plot(x, y, linewidth=2, color=colour, marker="o", markersize=3,
                 label=f"{result['window_months']}-month window")
    top.set_ylabel("default rate of the cohort")
    top.legend(frameon=False)
    top.grid(axis="y", alpha=.25)
    top.set_title("Lending Club: default rate by origination quarter, "
                  "on labels whose window has closed")

    sizes = widest["cohort_size"]
    bottom.bar([positions[c] for c in sizes], list(sizes.values()),
               color="#9fb8c8", width=.85)
    bottom.set_ylabel("labelled loans")
    bottom.set_xlabel("origination quarter")
    step = max(1, len(cohorts) // 24)
    bottom.set_xticks(list(range(len(cohorts)))[::step])
    bottom.set_xticklabels(cohorts[::step], rotation=90, fontsize=8)

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
    # The snapshot is the last observable performance date, not the last
    # origination: the book keeps reporting on loans after it stops writing them.
    snapshot = frame["last_pymnt_d"].max().date()
    print(f"rows                  : {len(frame):,}")
    print(f"last origination      : {frame['issue_d'].max().date()}")
    print(f"snapshot from data    : {snapshot}\n")

    results = [trajectory(frame, w, snapshot) for w in WINDOWS]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "trajectory.json").write_text(
        json.dumps({"snapshot": snapshot.isoformat(), "windows": results},
                   indent=2), encoding="utf-8")
    plot(results, args.out_dir / "default-rate-by-vintage.png")

    for result in results:
        s = result["summary"]
        rates = result["cohort_default_rate"]
        print(f"--- {result['window_months']}-month window ---")
        print(f"  labelled          : {s['labelled']:,}")
        print(f"  dropped immature  : {s['dropped_immature']:,}")
        print(f"  overall rate      : {s['default_rate']:.2%}")
        print(f"  unrecognised      : {s['unrecognised']:,}")
        print(f"  cohorts           : {len(rates)}"
              f"  ({min(rates)} .. {max(rates)})")

        # Extremes are taken only over cohorts that carry enough defaults to
        # bound a rate. Without the floor the minimum and the maximum are both
        # properties of cohort size rather than of credit.
        eligible = result["cohorts_clearing_the_floor"]
        print(f"  above the floor   : {len(eligible)}"
              f"  ({eligible[0]} .. {eligible[-1]}),"
              f" >= {MIN_LOANS:,} loans and >= {MIN_DEFAULTS} defaults"
              if eligible else
              f"  no cohort reaches {MIN_LOANS:,} loans and {MIN_DEFAULTS} defaults")
        if eligible:
            intervals = result["cohort_interval"]
            lo = min(eligible, key=lambda c: rates[c])
            hi = max(eligible, key=lambda c: rates[c])
            for name, cohort in (("lowest ", lo), ("highest", hi)):
                low, high = intervals[cohort]
                print(f"  {name} cohort    : {cohort} at {rates[cohort]:.2%} "
                      f"[{low:.2%}, {high:.2%}] on "
                      f"{result['cohort_defaults'][cohort]:,} defaults in "
                      f"{result['cohort_size'][cohort]:,} loans")
            print(f"  ratio             : {rates[hi] / rates[lo]:.2f}x, "
                  f"{lo} to {hi}, the extremes of the series above the floor "
                  f"rather than a tested change point")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
