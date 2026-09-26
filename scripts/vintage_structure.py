#!/usr/bin/env python3
"""Describes the vintage structure of a loan book, and audits its date columns.

Every later claim in this repository is conditional on the origination axis
being what it is assumed to be, so the axis is measured before anything is
modelled. Three questions, in order of how much damage a wrong answer does:

  1. What does the origination axis actually span, and how many loans sit in
     each cohort? A trajectory needs cohorts wide enough to carry a metric.
  2. Which other columns hold dates, and how far do they reach? A column that
     extends past the last origination date is a performance-window column. It
     is not a candidate for splitting on, and a split built on one sorts loans
     by outcome while looking like it sorts them by time.
  3. How many loans have resolved, under which definition? A loan whose term
     has not elapsed contributes a censored label, and the later cohorts are
     mostly such loans.

Writes a JSON summary and a plot of the cohort distribution beside it. Run
through scripts/record_run.py so the output is evidence rather than a number
in a terminal.

    python scripts/record_run.py lc-vintage-structure -- \
        python scripts/vintage_structure.py data/raw/accepted_2007_to_2018Q4.csv.gz
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from outoftime.label import TERMINAL_STATUSES

# Lending Club writes dates as "Dec-2018". Pandas will not infer this reliably
# across a column with missing values, so the format is stated.
MONTH_YEAR = "%b-%Y"

# Statuses that mean the loan reached a terminal state, taken from the label
# module rather than restated here. Two definitions of "resolved" in one
# repository is one too many, and the credit-policy variants are exactly the
# ones a second list forgets. Anything not listed there is unresolved and
# counted separately rather than silently dropped.
RESOLVED = set(TERMINAL_STATUSES)

# One row in every `SAMPLE_EVERY`, spread across the file. A contiguous head is
# not a sample of this dataset: it is a concatenation of quarterly releases, so
# the first twenty thousand rows are one origination month, and any column that
# is entirely null in that month is invisible to a detector that reads them.
SAMPLE_EVERY = 100


def date_like_columns(path: Path, sample_every: int = SAMPLE_EVERY) -> list[str]:
    """Finds the columns that parse as month-year dates, by trying them.

    The set of date columns is not stable across releases of this dataset and
    guessing from names misses `earliest_cr_line` while catching `term`. So
    every text column of a sample is offered to the parser and the ones that
    parse are returned. The sample is spread across the whole file, because a
    column that only ever carries a value in the later vintages — a servicing
    field introduced mid-book — is invisible to a detector that reads one
    contiguous block, and it is precisely the column that must not be missed.
    """
    sample = pd.read_csv(
        path,
        skiprows=lambda i: i > 0 and i % sample_every != 0,
        low_memory=False,
    )
    found = []
    for name in sample.columns:
        column = sample[name]
        # Text columns are `object` before pandas 3 and `str` from 3 onward, so
        # neither dtype can be tested for by name. Everything that is not
        # already numeric, boolean or datetime is offered to the parser.
        if not pd.api.types.is_string_dtype(column):
            continue
        non_null = column.dropna()
        if non_null.empty:
            continue
        parsed = pd.to_datetime(non_null, format=MONTH_YEAR, errors="coerce")
        # A real date column parses almost entirely. A free-text column that
        # happens to contain one date-shaped value does not.
        if parsed.notna().mean() > 0.95:
            found.append(name)
    return found


def summarise(path: Path, origination: str) -> dict:
    dates = date_like_columns(path)
    if origination not in dates:
        raise SystemExit(
            f"{origination!r} did not parse as a date column. Parsed: {dates}"
        )

    columns = sorted(set(dates) | {"loan_status", "term"})
    frame = pd.read_csv(path, usecols=columns, low_memory=False)

    # Every quarterly release ends in a footer line ("Total amount funded in
    # policy code 1: ..."). They parse as rows, they have no origination date,
    # and left in they make the denominator of every share slightly wrong and
    # the row count disagree with any other run over the same file.
    footers = int(pd.to_datetime(
        frame[origination], format=MONTH_YEAR, errors="coerce").isna().sum())
    frame = frame[pd.to_datetime(
        frame[origination], format=MONTH_YEAR, errors="coerce").notna()]
    frame = frame.reset_index(drop=True)

    parsed = {
        name: pd.to_datetime(frame[name], format=MONTH_YEAR, errors="coerce")
        for name in dates
    }
    origin = parsed[origination]
    last_origination = origin.max()

    # The audit that matters. A date column reaching past the last origination
    # is measured after the loan was written, so it cannot be known at decision
    # time and cannot define a split.
    date_audit = {}
    for name, series in parsed.items():
        latest = series.max()
        date_audit[name] = {
            "min": None if pd.isna(series.min()) else series.min().date().isoformat(),
            "max": None if pd.isna(latest) else latest.date().isoformat(),
            "null_fraction": round(float(series.isna().mean()), 6),
            "reaches_past_last_origination": bool(
                pd.notna(latest) and latest > last_origination
            ),
        }

    cohorts = origin.dt.to_period("Q").value_counts().sort_index()
    status = frame["loan_status"].value_counts()
    resolved_mask = frame["loan_status"].isin(RESOLVED)

    resolved_by_cohort = (
        resolved_mask.groupby(origin.dt.to_period("Q")).mean().sort_index()
    )

    return {
        "file": path.name,
        "rows": len(frame),
        "rows_without_an_origination_date": footers,
        "origination_column": origination,
        "origination_span": {
            "first": origin.min().date().isoformat(),
            "last": last_origination.date().isoformat(),
            "quarterly_cohorts": int(cohorts.size),
        },
        "date_column_audit": date_audit,
        "columns_reaching_past_last_origination": [
            name for name, info in date_audit.items()
            if info["reaches_past_last_origination"]
        ],
        "loan_status_counts": {k: int(v) for k, v in status.items()},
        "resolved": {
            "definition": sorted(RESOLVED),
            "count": int(resolved_mask.sum()),
            "fraction": round(float(resolved_mask.mean()), 4),
        },
        "cohort_sizes": {str(k): int(v) for k, v in cohorts.items()},
        "resolved_fraction_by_cohort": {
            str(k): round(float(v), 4) for k, v in resolved_by_cohort.items()
        },
    }


def plot(summary: dict, out: Path) -> None:
    """Cohort size against the share of the cohort that has resolved.

    Not a bar chart of a headline number. The shape being looked for is the
    fall in resolved share across the later cohorts: where it falls, the label
    is censored, and a model evaluated there is evaluated on whichever loans
    happened to finish early.
    """
    cohorts = list(summary["cohort_sizes"])
    sizes = [summary["cohort_sizes"][c] for c in cohorts]
    resolved = [summary["resolved_fraction_by_cohort"][c] for c in cohorts]
    positions = range(len(cohorts))

    figure, top = plt.subplots(figsize=(13, 5.5))
    top.bar(positions, sizes, color="#9fb8c8", width=0.85, label="loans originated")
    top.set_ylabel("loans originated")
    top.set_xlabel("origination quarter")

    bottom = top.twinx()
    bottom.plot(positions, resolved, color="#0E6B66", linewidth=2, label="resolved share")
    bottom.set_ylabel("share of cohort resolved")
    bottom.set_ylim(0, 1.05)

    step = max(1, len(cohorts) // 24)
    top.set_xticks(list(positions)[::step])
    top.set_xticklabels(cohorts[::step], rotation=90, fontsize=8)
    top.set_title(
        f"{summary['file']}: cohort size and resolved share, "
        f"{summary['origination_span']['first']} to {summary['origination_span']['last']}"
    )
    figure.tight_layout()
    figure.savefig(out, dpi=140)
    plt.close(figure)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("path", type=Path, help="the loan-level csv, gzipped or not")
    parser.add_argument(
        "--origination-column", default="issue_d",
        help="the column holding the origination date (default: issue_d)",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=Path("."),
        help="where summary.json and cohorts.png are written",
    )
    args = parser.parse_args(argv)

    if not args.path.exists():
        raise SystemExit(f"{args.path} does not exist")

    summary = summarise(args.path, args.origination_column)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    plot(summary, args.out_dir / "cohorts.png")

    span = summary["origination_span"]
    print(f"rows                     : {summary['rows']:,}")
    print(f"origination span         : {span['first']} .. {span['last']}")
    print(f"quarterly cohorts        : {span['quarterly_cohorts']}")
    print(f"resolved                 : {summary['resolved']['count']:,} "
          f"({summary['resolved']['fraction']:.1%})")
    if summary["rows_without_an_origination_date"]:
        print(f"non-loan rows dropped    : "
              f"{summary['rows_without_an_origination_date']}  "
              f"(release footers, no origination date)")
    print()
    print("date columns reaching past the last origination date:")
    late = summary["columns_reaching_past_last_origination"]
    if late:
        for name in late:
            info = summary["date_column_audit"][name]
            share = info["null_fraction"]
            reading = "0%" if share == 0 else (
                "<0.01%" if share < 0.0001 else f"{share:.2%}")
            print(f"  {name:<28} .. {info['max']}   (null {reading})")
        print()
        print("  These are performance-window columns. Splitting on one sorts")
        print("  loans by outcome, not by origination.")
    else:
        print("  none")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
