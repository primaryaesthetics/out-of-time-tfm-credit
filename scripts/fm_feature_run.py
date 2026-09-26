#!/usr/bin/env python3
"""The feature gates of EXP-005 on the Freddie Mac book, and the matrix they leave.

The second of the two runs EXP-005 records before its falsifying run. It
loads the book the score runs read — every loan of the reduced files less the
re-dated ones and those with no servicing record, by `fm_score_build.load` —
and runs on it the redundancy report, coverage by onset, the value rule of
EXP-005 and the shift report of `fm_features`, then writes what they decide:

  * `gates.json`, the four reports whole;
  * `features.json`, the kept columns, every dropped column with the gate and
    the clauses that remove it, the derived columns and the columns they
    replace, the clip range of every kept numeric column, the share of each
    numeric column's variance that lies between cells of first payment
    month and term, the conforming-limit table the ratio was computed with,
    and the matrix's columns and dtypes;
  * `dropped-columns.png`, one small panel per column a gate removes, with
    the share of its offending level or of its missing value by origination
    half-year, so that a reader sees on the axis what the rule read at its
    two ends;
  * `loan-amount.png`, the median and the ninetieth percentile of the loan
    amount in dollars and as a share of the year's limit by origination
    half-year, and the share of each cohort each form's clip pins, so that
    a reader sees what the transform took out.

`--ablation` names one of `fm_features.ABLATIONS` and records that matrix
instead of the primary. Nothing row-level is written.

    python scripts/record_run.py fm-features -- \\
        <venv python> scripts/fm_feature_run.py data/derived/freddie-mac \\
            --out-dir experiments/<date>-fm-features
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fm_score_build import load

from outoftime import fm_features as ff
from outoftime.freddie_mac import LATE_FIRST_PAYMENT_MONTHS

MISSING = "missing"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("derived", type=Path, help="directory of loans_YYYY.parquet")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--first-cohort", default=ff.FIRST_COHORT,
                        help="the first cohort, the value rule's reference")
    parser.add_argument("--last-cohort", default=ff.LAST_COHORT)
    parser.add_argument("--ablation", default=None, choices=sorted(ff.ABLATIONS),
                        help="record the ablation's matrix instead of the primary")
    return parser.parse_args(argv)


def offending(book: pd.DataFrame, name: str, record: dict, first: str, last: str):
    """What a dropped column carries that dates a loan, as a boolean per loan, and its name.

    The missing value for a column the coverage gate drops or the missing-share
    clause removes; the levels the last cohort lacks for a departed level; the
    levels the first cohort lacks for a late level; the values the first
    cohort did not hold for a column constant on it.
    """
    column = ff._cleaned(book, [name])[name].astype(object)
    present = column.notna()
    held_first = set(column[ff._in(book, first, first) & present.to_numpy()].unique())
    held_last = set(column[ff._in(book, last, last) & present.to_numpy()].unique())
    clauses = record.get("clauses", [])
    if name in ff.LATE_COVERAGE or ff.MISSING_SHARE_CLAUSE in clauses:
        return ~present, MISSING
    if "a level present on the first cohort and absent from the last" in clauses:
        levels = held_first - held_last
        return present & column.isin(levels), f"levels gone by {last}: {sorted(map(str, levels))[:3]}"
    if "a level absent from the first cohort" in clauses:
        return present & ~column.isin(held_first), f"levels absent from {first}"
    return present & ~column.isin(held_first), f"values {first} did not hold"


def plot(book: pd.DataFrame, dropped: dict, values: dict, args, out: Path) -> None:
    names = [n for n in dropped if n not in ff.A_PRIORI]
    columns = 4
    rows = max(1, math.ceil(len(names) / columns))
    figure, axes = plt.subplots(rows, columns, figsize=(4.2 * columns, 2.8 * rows),
                                sharex=True, squeeze=False)
    half = ff.cohort_of(book)
    inside = ff._in(book, args.first_cohort, args.last_cohort)
    for axis, name in zip(axes.flat, names):
        mask, label = offending(book, name, values[name], args.first_cohort, args.last_cohort)
        share = pd.Series(np.asarray(mask)[inside]).groupby(half.to_numpy()[inside]).mean()
        axis.plot(range(len(share)), share.to_numpy(), color="#0E6B66", linewidth=1.4)
        axis.set_ylim(-0.02, 1.02)
        axis.axhline(ff.VALUE_FLOOR, color="#b0392b", linewidth=0.8, linestyle=":")
        axis.set_title(f"{name}: {label}", fontsize=8)
        axis.set_xticks(range(0, len(share), 8))
        axis.set_xticklabels(list(share.index)[::8], rotation=90, fontsize=7)
        axis.text(0.02, 0.9, " / ".join(dropped[name]["gates"]), transform=axis.transAxes,
                  fontsize=7, color="#555555")
        axis.grid(axis="y", alpha=0.25)
    for axis in list(axes.flat)[len(names):]:
        axis.axis("off")
    figure.suptitle("every column a gate removes: the share of loans carrying what dates them, "
                    f"by origination half-year; dotted, the floor of {ff.VALUE_FLOOR:.0%}",
                    fontsize=10)
    figure.tight_layout()
    figure.savefig(out, dpi=130)
    plt.close(figure)


def plot_amount(book: pd.DataFrame, args, out: Path) -> None:
    """The loan amount in both forms by origination half-year, and what each clip pins."""
    inside = ff._in(book, args.first_cohort, args.last_cohort)
    frame = pd.DataFrame({
        "half": ff.cohort_of(book).to_numpy(),
        "upb": pd.to_numeric(ff._cleaned(book, ["upb"])["upb"], errors="coerce").to_numpy(),
        "ratio": ff._derived_values(book, "upb_to_limit").to_numpy(),
    })[inside]
    grouped = frame.groupby("half")
    halves = list(grouped.groups)
    x = range(len(halves))
    figure, (top, bottom) = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                                         height_ratios=(3, 2))
    top.plot(x, grouped["upb"].median().to_numpy(), color="#20303a", linewidth=1.6,
             label="upb, median")
    top.plot(x, grouped["upb"].quantile(0.9).to_numpy(), color="#20303a", linewidth=1.0,
             linestyle="--", label="upb, 90th percentile")
    top.set_ylabel("original balance, dollars")
    twin = top.twinx()
    twin.plot(x, grouped["ratio"].median().to_numpy(), color="#0E6B66", linewidth=1.6,
              label="upb_to_limit, median")
    twin.plot(x, grouped["ratio"].quantile(0.9).to_numpy(), color="#0E6B66", linewidth=1.0,
              linestyle="--", label="upb_to_limit, 90th percentile")
    twin.set_ylabel("balance over the year's conforming limit")
    lines = top.get_legend_handles_labels()
    more = twin.get_legend_handles_labels()
    top.legend(lines[0] + more[0], lines[1] + more[1], frameon=False, fontsize=8,
               loc="upper left")

    for column, (low, high), colour, name in (
        ("upb", ff.ABLATION_CLIPPED["upb"], "#20303a", "upb"),
        ("ratio", ff.CLIPPED["upb_to_limit"], "#0E6B66", "upb_to_limit"),
    ):
        values = frame[column]
        pinned = values.notna() & ((values < low) | (values > high))
        bottom.plot(x, pinned.groupby(frame["half"]).mean().reindex(halves).to_numpy(),
                    color=colour, linewidth=1.4,
                    label=f"{name} pinned by its clip, {low:.4g} to {high:.4g}")
    bottom.set_ylabel("share of the cohort pinned")
    bottom.legend(frameon=False, fontsize=8)
    bottom.set_xticks(range(0, len(halves), 4))
    bottom.set_xticklabels(halves[::4], rotation=90, fontsize=8)
    figure.suptitle("the loan amount in dollars and against the year's conforming limit, "
                    "by origination half-year", fontsize=11)
    figure.tight_layout()
    figure.savefig(out, dpi=130)
    plt.close(figure)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    frame, inputs = load(args.derived)
    redated = frame["first_payment_lag"].astype(int) >= LATE_FIRST_PAYMENT_MONTHS
    unrecorded = frame["last_age"].isna()
    book = frame.loc[~redated & ~unrecorded].reset_index(drop=True)
    exclusions = {"loaded": len(frame), "redated": int(redated.sum()),
                  "without_performance_record": int(unrecorded.sum()), "book": len(book)}
    del frame

    span = {"first_cohort": args.first_cohort, "last_cohort": args.last_cohort}
    gates = {
        "redundancy": ff.redundancy_report(book, ablation=args.ablation),
        "coverage": ff.coverage_report(book, **span, ablation=args.ablation),
        "values": ff.value_report(book, **span, ablation=args.ablation),
        "shifts": ff.shift_report(book, **span, ablation=args.ablation),
    }
    matrix = ff.model_matrix(book, ablation=args.ablation)
    ff.assert_matrix_clean(matrix, ablation=args.ablation)

    kept = list(ff.feature_names(args.ablation))
    dropped: dict[str, dict] = {
        name: {"gates": ["a priori"], "clauses": [reason]} for name, reason in ff.A_PRIORI.items()
    }
    for name, record in gates["values"].items():
        if name not in kept and record["gates"]:
            dropped[name] = {"gates": record["gates"], "clauses": record["clauses"]}
    clipped = ff._clipped(args.ablation)
    built = [name for name in ff.DERIVED if name in kept]
    features = {
        "ablation": args.ablation,
        "book": exclusions,
        "inputs_sha256": inputs,
        "span": span,
        "kept": kept,
        "categorical": list(ff.categorical_names(args.ablation)),
        "dropped": dropped,
        "derived": {name: list(ff.DERIVED[name]) for name in built},
        "replaced": {ff.DERIVED[name][0]: name for name in built},
        "clip": {name: list(bounds) for name, bounds in clipped.items() if name in kept},
        "calendar_share": gates["redundancy"]["calendar_share"],
        "conforming_limit": {str(year): value for year, value in ff.CONFORMING_LIMIT.items()},
        "matrix": {"columns": list(matrix.columns),
                   "dtypes": {k: str(v) for k, v in matrix.dtypes.items()},
                   "rows": len(matrix)},
        "shifts_flagged": gates["shifts"]["flagged"],
        "wall_seconds": round(time.time() - started, 1),
    }
    (args.out_dir / "gates.json").write_text(
        json.dumps(gates, indent=2, default=str), encoding="utf-8")
    (args.out_dir / "features.json").write_text(
        json.dumps(features, indent=2, default=str), encoding="utf-8")
    plot(book, dropped, gates["values"], args, args.out_dir / "dropped-columns.png")
    plot_amount(book, args, args.out_dir / "loan-amount.png")

    print(f"book                  : {len(book):,} of {exclusions['loaded']:,} loans")
    print(f"ablation              : {args.ablation or 'none'}")
    print(f"kept                  : {len(kept)}: {', '.join(kept)}")
    for name, record in dropped.items():
        print(f"dropped {name:<28}: {' + '.join(record['gates'])}: {'; '.join(record['clauses'])}")
    for name, (low, high) in features["clip"].items():
        print(f"clip {name:<31}: {low:.6g} .. {high:.6g}")
    for name, share in features["calendar_share"].items():
        if name != "cells":
            print(f"calendar share {name:<21}: {share}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
