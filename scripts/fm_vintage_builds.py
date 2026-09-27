#!/usr/bin/env python3
"""The Freddie Mac build grid as `vintage.builds` emits it, before any model exists.

The counterpart of `vintage_builds.py` on the second book, and the first of
the two runs EXP-005 records before its falsifying run. For a list of as-of
dates and the arms named it assembles every build on the book the score runs
read — the same loading, the same exclusions and the same three readings of
the label, through `fm_score_build.load_book` — and describes it without
fitting anything:

  * per build: the training quarters; the pool's labelled loans, defaults and
    rate under the study's reading, the reading with relief months counted
    and the twelve-month reading; the blind gap, and the loans in it whose own
    window had closed, which is what cutting the pool on whole quarters
    costs; the training loans whose window was open at the as-of date, which
    must be none or the grid is refused; the scored loans whose pre-HARP
    identifier names a training loan;
  * per scored cell: labelled loans and defaults under all three readings,
    the floor verdict under the study's reading, the label regime of the
    cohort, and the cohort's maturity at the cutoff and labelled share;
  * per cohort: the loans excluded as first observed late and for a gap in
    their record.

The label regime is where a cohort's windows fall against the month the
assistance and disaster flags begin: pre-flag when every admitted loan's
window closed before it, flagged when every window opened on or after it,
straddling between. The boundaries follow from the flag month, the label
window and the latest first payment the book admits, and are computed rather
than written. A rolling build whose window would reach back before the first
cohort is not assembled and is named in the output as skipped.

Three files, all aggregates: `builds.json`, `cells.csv` and `build-grid.png`,
which shows per build the training pool's rate against the rate of every
cohort it scores, on a log axis, with the regime boundaries drawn and the
cells under the floors left open. No model, no score, no row.

    python scripts/record_run.py fm-vintage-builds -- \\
        <venv python> scripts/fm_vintage_builds.py data/derived/freddie-mac \\
            --out-dir experiments/<date>-fm-vintage-builds --as-of <dates> --arms E,R
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fm_score_build import (
    HORIZON_WINDOW_MONTHS,
    age_in_quarters,
    age_or_none,
    grid_cohorts,
    load_book,
)

from outoftime.label import add_months
from outoftime.performance_label import MAX_FIRST_OBSERVED_AGE
from outoftime.vintage import (
    CONTEXT_ROWS,
    FREDDIE_MAC,
    Quarter,
    builds,
    cohorts_between,
    months_back,
)

# The floors of EXP-001 and EXP-003: a cell enters a criterion only with this
# many labelled loans and defaults under the study's reading.
MIN_LOANS = 5_000
MIN_DEFAULTS = 100

# The month the assistance and disaster flags begin on the performance file.
FLAG_START = "2014-01"

REGIMES = ("pre-flag", "straddling", "flagged")
ARM_COLOUR = {"E": "#0E6B66", "R": "#9A5B24"}


def month_index(date: dt.date) -> int:
    return date.year * 12 + date.month - 1


def regime(cohort, flag_start: dt.date, window: int, max_lag: int) -> str:
    """Where a cohort's label windows fall against the first flagged month.

    The latest window of a cohort belongs to a loan of its last quarter whose
    first payment came as late as the book admits, and it ends `window`
    months after that payment month begins; the earliest opens in the
    cohort's first month.
    """
    latest_end = month_index(Quarter.of(cohort.end).start) + max_lag + window - 1
    if latest_end < month_index(flag_start):
        return "pre-flag"
    if month_index(cohort.start) >= month_index(flag_start):
        return "flagged"
    return "straddling"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("derived", type=Path,
                        help="directory of loans_YYYY.parquet, perf_YYYY.parquet and "
                             "reduce_YYYY.json")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--as-of", type=dt.date.fromisoformat, nargs="+", required=True,
                        help="the as-of dates of the grid, each the last day of a cohort")
    parser.add_argument("--arms", default="E", help="arms to assemble, comma-separated")
    parser.add_argument("--rolling-quarters", type=int, default=FREDDIE_MAC.rolling_quarters)
    parser.add_argument("--window", type=int, default=FREDDIE_MAC.label_lag_months)
    parser.add_argument("--axis-gap", type=int, default=FREDDIE_MAC.axis_gap_months)
    parser.add_argument("--max-clock-lag", type=int, default=FREDDIE_MAC.max_clock_lag_months)
    parser.add_argument("--horizon-window", type=int, default=HORIZON_WINDOW_MONTHS)
    parser.add_argument("--resolution", default="half-year", choices=("half-year", "quarter"))
    parser.add_argument("--first-cohort", default=None)
    parser.add_argument("--last-cohort", default=None)
    parser.add_argument("--max-first-observed-age", type=age_or_none,
                        default=MAX_FIRST_OBSERVED_AGE)
    parser.add_argument("--keep-record-gaps", action="store_true")
    parser.add_argument("--flag-start", default=FLAG_START,
                        help="first month of the assistance and disaster flags, YYYY-MM")
    parser.add_argument("--min-loans", type=int, default=MIN_LOANS)
    parser.add_argument("--min-defaults", type=int, default=MIN_DEFAULTS)
    return parser.parse_args(argv)


def reading_counts(rows, values: np.ndarray) -> dict:
    labelled = values[rows]
    labelled = labelled[labelled >= 0]
    defaults = int((labelled == 1).sum())
    return {"labelled": int(labelled.size), "defaults": defaults,
            "rate": round(defaults / labelled.size, 6) if labelled.size else None}


def plot(summary: dict, cohort_rows: dict, out: Path) -> None:
    """Per build, the pool's rate against the rate of every cohort it scores."""
    arms = summary["arms"]
    main = "E" if arms.get("E") else next(iter(arms))
    panels = arms[main]
    columns = 3
    rows = max(1, math.ceil(len(panels) / columns))
    figure, axes = plt.subplots(rows, columns, figsize=(5.2 * columns, 3.6 * rows),
                                sharey=True, squeeze=False)
    names = list(cohort_rows)
    position = {name: i for i, name in enumerate(names)}
    regimes = [cohort_rows[name]["regime"] for name in names]
    bounds = [i - 0.5 for i in range(1, len(names)) if regimes[i] != regimes[i - 1]]
    others = {b["as_of"]: b for arm, records in arms.items() if arm != main for b in records}

    for axis, build in zip(axes.flat, panels):
        cells = [c for c in build["cells"] if cohort_rows[c]["rate"]]
        x = [position[c] for c in cells]
        y = [cohort_rows[c]["rate"] for c in cells]
        axis.plot(x, y, color="#20303a", linewidth=1.0)
        passed = [cohort_rows[c]["floor"] for c in cells]
        axis.scatter([v for v, p in zip(x, passed) if p], [v for v, p in zip(y, passed) if p],
                     color="#20303a", s=14, zorder=3, label="scored cohort")
        axis.scatter([v for v, p in zip(x, passed) if not p],
                     [v for v, p in zip(y, passed) if not p],
                     facecolor="none", edgecolor="#20303a", s=14, zorder=3,
                     label="under the floors")
        axis.axhline(build["pool"]["rate"], color=ARM_COLOUR.get(main, "#0E6B66"),
                     linewidth=1.6, label=f"pool, arm {main}")
        other = others.get(build["as_of"])
        if other is not None:
            axis.axhline(other["pool"]["rate"], color=ARM_COLOUR.get(other["arm"], "#9A5B24"),
                         linewidth=1.2, linestyle="--", label=f"pool, arm {other['arm']}")
        for bound in bounds:
            axis.axvline(bound, color="#b0392b", linewidth=0.8, linestyle=":")
        axis.set_yscale("log")
        axis.set_title(build["build_id"], fontsize=10)
        step = max(1, len(names) // 8)
        axis.set_xticks(range(0, len(names), step))
        axis.set_xticklabels(names[::step], rotation=90, fontsize=7)
        axis.set_xlim(-0.5, len(names) - 0.5)
        axis.grid(axis="y", alpha=0.25)
    for axis in list(axes.flat)[len(panels):]:
        axis.axis("off")
    axes.flat[0].legend(frameon=False, fontsize=7)
    figure.suptitle(
        f"{summary['parameters']['window']}-month default rate of every scored cohort against "
        f"the training pool; dotted lines divide the label regimes "
        f"{', '.join(REGIMES)}", fontsize=11)
    figure.tight_layout()
    figure.savefig(out, dpi=130)
    plt.close(figure)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = sorted(set(arms) - {"E", "R"})
    if unknown:
        raise SystemExit(f"arms are E and R, not {unknown}")
    first, last = grid_cohorts(args)
    flag_start = dt.date(int(args.flag_start[:4]), int(args.flag_start[5:7]), 1)

    book = load_book(args, type(first))
    del book.frame
    print(f"loans loaded          : {book.exclusions['loaded']:,}")
    print(f"book                  : {book.exclusions['book']:,}")
    print(f"first observed late   : {book.exclusions['excluded_first_observed_late']:,}")
    print(f"record with a gap     : {book.exclusions['excluded_record_gap']:,}", flush=True)

    late = np.zeros(len(book.outcome), dtype=bool)
    late[list(book.primary.left_truncated)] = True
    gapped = np.zeros(len(book.outcome), dtype=bool)
    gapped[list(book.primary.record_gaps)] = True
    cohort_rows: dict[str, dict] = {}
    for cohort in cohorts_between(first, last):
        name = str(cohort)
        mask = book.book_cohort == name
        if not mask.any():
            continue
        positions = np.flatnonzero(mask)
        primary = reading_counts(positions, book.outcome)
        loans = int(book.loaded_by_cohort.get(name, 0))
        cohort_rows[name] = {
            "loans": loans,
            "book": int(mask.sum()),
            **{f"{k}": v for k, v in primary.items()},
            "reported": reading_counts(positions, book.outcome_reported),
            "horizon": reading_counts(positions, book.outcome_horizon),
            "floor": primary["labelled"] >= args.min_loans
            and primary["defaults"] >= args.min_defaults,
            "regime": regime(cohort, flag_start, args.window, args.max_clock_lag),
            "maturity_share": round(1.0 - float(book.open_at_cutoff[mask].mean()), 6),
            "labelled_share": round(primary["labelled"] / loans, 6) if loans else None,
            "excluded_first_observed_late": int((mask & late).sum()),
            "excluded_record_gap": int((mask & gapped).sum()),
        }

    summary: dict = {
        "parameters": {
            "as_of": [d.isoformat() for d in args.as_of], "arms": arms,
            "rolling_quarters": args.rolling_quarters, "window": args.window,
            "axis_gap_months": args.axis_gap, "max_clock_lag_months": args.max_clock_lag,
            "horizon_window": args.horizon_window, "first_cohort": str(first),
            "last_cohort": str(last), "flag_start": args.flag_start,
            "floors": {"min_loans": args.min_loans, "min_defaults": args.min_defaults},
            "max_first_observed_age": args.max_first_observed_age,
            "exclude_record_gaps": not args.keep_record_gaps,
            "context_rows": CONTEXT_ROWS,
        },
        "performance_cutoff": book.cutoff.isoformat(),
        "inputs_sha256": book.inputs,
        "exclusions": book.exclusions,
        "labels": {"primary": book.primary.as_dict(), "reported": book.reported.as_dict(),
                   "horizon": book.horizon.as_dict()},
        "regimes": {r: [c for c, v in cohort_rows.items() if v["regime"] == r] for r in REGIMES},
        "cohorts": cohort_rows,
        "arms": {},
        "skipped": [],
        "cell_counts": {},
    }

    cells: list[dict] = []
    pool_start = Quarter.of(first.start)
    for arm in arms:
        dates = []
        for as_of in args.as_of:
            last_train = Quarter.of(months_back(as_of, args.axis_gap))
            if arm == "R" and last_train.shift(-(args.rolling_quarters - 1)) < pool_start:
                summary["skipped"].append({
                    "as_of": as_of.isoformat(), "arm": arm,
                    "reason": f"a {args.rolling_quarters}-quarter window ending {last_train} "
                              f"reaches before the first cohort"})
                continue
            dates.append(as_of)
        grid = builds(
            book.origination, knowable=book.first_payment, as_of_dates=tuple(dates), arm=arm,
            label_lag_months=args.window, axis_gap_months=args.axis_gap,
            max_clock_lag_months=args.max_clock_lag, first_cohort=first, last_cohort=last,
            rows_per_quarter=None, labels=book.primary, rolling_quarters=args.rolling_quarters,
        ) if dates else []
        records = []
        for build in grid:
            pool = np.asarray(build.train, dtype=np.int64)
            horizon = add_months(build.as_of, -args.window)
            still_open = sum(book.first_payment[i] > horizon for i in build.train)
            if still_open:
                raise SystemExit(f"{build.build_id} trains on {still_open} loans whose window "
                                 f"was open at the as-of date")
            train_ids = set(book.loan_ids[pool])
            linked = np.asarray([v is not None and v in train_ids for v in book.pre_harp])
            record = {
                "build_id": build.build_id, "arm": arm, "as_of": build.as_of.isoformat(),
                "train_quarters": [str(q) for q in build.train_quarters],
                "pool": reading_counts(pool, book.outcome),
                "pool_reported": reading_counts(pool, book.outcome_reported),
                "pool_horizon": reading_counts(pool, book.outcome_horizon),
                "context_rows": min(CONTEXT_ROWS, len(pool)),
                "blind_rows": len(build.blind),
                "blind_loans_with_closed_windows": sum(
                    book.first_payment[i] <= horizon for i in build.blind
                    if book.outcome[i] >= 0),
                "training_windows_open_at_as_of": still_open,
                "cells": [str(c) for c in build.test_cohorts],
                "criterion_cells": sum(cohort_rows[str(c)]["floor"] for c in build.test_cohorts),
                "scored_linked_to_training_by_pre_harp_id": 0,
            }
            for cohort, rows in build.test:
                name = str(cohort)
                row = cohort_rows[name]
                links = int(linked[list(rows)].sum())
                record["scored_linked_to_training_by_pre_harp_id"] += links
                cells.append({
                    "build_id": build.build_id, "arm": arm, "as_of": build.as_of.isoformat(),
                    "cohort": name, "age_quarters": age_in_quarters(build.as_of, cohort),
                    "labelled": row["labelled"], "defaults": row["defaults"],
                    "rate": row["rate"],
                    "labelled_reported": row["reported"]["labelled"],
                    "defaults_reported": row["reported"]["defaults"],
                    "labelled_horizon": row["horizon"]["labelled"],
                    "defaults_horizon": row["horizon"]["defaults"],
                    "floor": row["floor"], "regime": row["regime"],
                    "maturity_share": row["maturity_share"],
                    "labelled_share": row["labelled_share"],
                    "excluded_first_observed_late": row["excluded_first_observed_late"],
                    "excluded_record_gap": row["excluded_record_gap"],
                    "scored_linked_to_training_by_pre_harp_id": links,
                    "pool_rate": record["pool"]["rate"],
                })
            records.append(record)
        summary["arms"][arm] = records
        arm_cells = [c for c in cells if c["arm"] == arm]
        summary["cell_counts"][arm] = {
            "builds": len(records),
            "cells": len(arm_cells),
            "criterion": sum(c["floor"] for c in arm_cells),
            "below_floors": sum(not c["floor"] for c in arm_cells),
        }

    (args.out_dir / "builds.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")
    pd.DataFrame(cells).to_csv(args.out_dir / "cells.csv", index=False)
    if summary["arms"] and any(summary["arms"].values()):
        plot(summary, cohort_rows, args.out_dir / "build-grid.png")

    for arm, records in summary["arms"].items():
        counts = summary["cell_counts"][arm]
        print(f"\n--- arm {arm}: {counts['builds']} builds, {counts['cells']} cells, "
              f"{counts['criterion']} above the floors ---")
        print(f"{'build':>9} {'quarters':>9} {'pool':>10} {'blind':>9} {'closed':>8} "
              f"{'cells':>6} {'links':>6}")
        for record in records:
            print(f"{record['build_id']:>9} {len(record['train_quarters']):>9} "
                  f"{record['pool']['labelled']:>10,} {record['blind_rows']:>9,} "
                  f"{record['blind_loans_with_closed_windows']:>8,} {len(record['cells']):>6} "
                  f"{record['scored_linked_to_training_by_pre_harp_id']:>6}")
    for skipped in summary["skipped"]:
        print(f"skipped {skipped['as_of']} arm {skipped['arm']}: {skipped['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
