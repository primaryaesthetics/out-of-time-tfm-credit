#!/usr/bin/env python3
"""How much the Freddie Mac rolling window differs from the expanding pool, per build.

The same two quantities as `arm_contrast.py` reads on the first book, on this
book's grid: the share of the expanding pool a k-quarter window holds, and the
mean age of a training row in quarters before the newest quarter it holds,
weighted by rows. The pools are the grid's own, built by the same functions
and under the same arguments as `fm_vintage_builds.py`, so the record
describes the builds that were scored; at the study's width the rolling
window's quarters and rows are checked against the rolling arm's own build,
and a mismatch refuses the record.

The output, `arm-contrast.json`, has the layout `between_arm_intervals.py`
reads through `--contrast`, keyed by the build's half-year.

    python scripts/record_run.py fm-arm-contrast -- \\
        python scripts/fm_arm_contrast.py data/derived/freddie-mac \\
            --as-of 2002-12-31 ... 2018-12-31 --out-dir experiments/<date>-fm-arm-contrast
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import fm_vintage_builds as fvb
from arm_contrast import WIDTHS, mean_age
from fm_score_build import grid_cohorts, load_book

from outoftime.vintage import Quarter, builds, months_back


def grid(book, args, first, last, arm: str, dates):
    return builds(
        book.origination, knowable=book.first_payment, as_of_dates=tuple(dates), arm=arm,
        label_lag_months=args.window, axis_gap_months=args.axis_gap,
        max_clock_lag_months=args.max_clock_lag, first_cohort=first, last_cohort=last,
        rows_per_quarter=None, labels=book.primary, rolling_quarters=args.rolling_quarters,
    )


def main(argv: list[str] | None = None) -> int:
    args = fvb.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    first, last = grid_cohorts(args)
    book = load_book(args, type(first))
    del book.frame

    pool_start = Quarter.of(first.start)
    expanding = {b.as_of: b for b in grid(book, args, first, last, "E", args.as_of)}
    rolling_dates = [d for d in args.as_of
                     if Quarter.of(months_back(d, args.axis_gap)).shift(-(args.rolling_quarters - 1))
                     >= pool_start]
    rolling = {b.as_of: b for b in grid(book, args, first, last, "R", rolling_dates)}

    records = []
    for as_of, build in sorted(expanding.items()):
        sizes: dict[Quarter, int] = {}
        for i in build.train:
            quarter = Quarter.of(book.origination[i])
            sizes[quarter] = sizes.get(quarter, 0) + 1
        quarters = tuple(build.train_quarters)
        pool = sum(sizes.values())
        record = {
            "build_id": f"{as_of.year}H{1 if as_of.month <= 6 else 2}",
            "as_of": as_of.isoformat(),
            "newest_training_quarter": str(quarters[-1]),
            "expanding_rows": pool,
            "expanding_quarters": len(quarters),
            "expanding_mean_age_quarters": mean_age(sizes, quarters),
            "rolling": {},
        }
        for width in sorted({*WIDTHS, args.rolling_quarters}):
            window = quarters[-width:]
            rows = sum(sizes.get(q, 0) for q in window)
            record["rolling"][str(width)] = {
                "quarters": len(window), "rows": rows,
                "share_of_expanding": round(rows / pool, 4) if pool else None,
                "mean_age_quarters": mean_age(sizes, window),
            }
        if as_of in rolling:
            own = rolling[as_of]
            at_width = record["rolling"][str(args.rolling_quarters)]
            if tuple(own.train_quarters) != quarters[-args.rolling_quarters:] or \
                    len(own.train) != at_width["rows"]:
                raise SystemExit(f"{record['build_id']}: the rolling arm's build holds "
                                 f"{len(own.train):,} rows over {len(own.train_quarters)} quarters, "
                                 f"the {args.rolling_quarters}-quarter window of the expanding pool "
                                 f"{at_width['rows']:,}")
            record["rolling_build_rows"] = len(own.train)
        records.append(record)

    width = str(args.rolling_quarters)
    print(f"{'build':>7} {'expanding':>10} {'age':>6} {'rolling':>9} {'share':>6} {'age':>6} {'gap':>6}")
    for r in records:
        roll = r["rolling"][width]
        print(f"{r['build_id']:>7} {r['expanding_rows']:>10,} {r['expanding_mean_age_quarters']:>6.2f} "
              f"{roll['rows']:>9,} {roll['share_of_expanding']:>6.1%} {roll['mean_age_quarters']:>6.2f} "
              f"{r['expanding_mean_age_quarters'] - roll['mean_age_quarters']:>6.2f}"
              + ("" if "rolling_build_rows" in r else "  (no rolling build)"))

    (args.out_dir / "arm-contrast.json").write_text(json.dumps({
        "snapshot": book.cutoff.isoformat(),
        "label_lag_months": args.window,
        "axis_gap_months": args.axis_gap,
        "study_rolling_quarters": args.rolling_quarters,
        "widths": sorted({*WIDTHS, args.rolling_quarters}),
        "builds": records,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
