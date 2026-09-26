#!/usr/bin/env python3
"""The vintage structure of the Freddie Mac sample, and its default trajectory.

The counterpart of `vintage_structure.py` and `label_trajectory.py` for the
second book, run on the reduced parquet rather than the zips. Three questions,
in the order a wrong answer does damage:

  1. Is the origination quarter in the loan identifier the axis the user guide
     says it is? The first payment date is the only date in the file, and the
     lag between the two is measured per cohort rather than assumed.
  2. How many loans in each quarterly cohort carry a mature label, and how
     many of those defaulted, under the twelve- and twenty-four-month windows?
     A cohort below the floors carries no rate worth plotting.
  3. Which cohorts survive the floors at quarterly, semi-annual and annual
     resolution? That decides the resolution the trajectory can be read at.

Writes summary.json and two plots beside it: the cohort sizes with the share
that could be labelled, and the default-rate trajectory under both windows with
Wilson bands.

    python scripts/record_run.py fm-vintage-structure -- \\
        python scripts/freddie_mac_structure.py data/derived/freddie-mac
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from outoftime.freddie_mac import LATE_FIRST_PAYMENT_MONTHS
from outoftime.performance_label import (
    LoanHistory,
    PerformanceLabelDefinition,
    build_performance_labels,
)

WINDOWS = (12, 24)

# The same floors as the Lending Club trajectory: a cohort carries a rate only
# if it carries enough loans to bound one and enough defaults for the bound to
# be narrow. Stated in the output so a quoted extreme names its population.
MIN_LOANS = 5_000
MIN_DEFAULTS = 100


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def wilson(defaults: int, size: int, z: float = 1.96) -> tuple[float, float]:
    if size == 0:
        return (float("nan"), float("nan"))
    p = defaults / size
    denominator = 1 + z * z / size
    centre = (p + z * z / (2 * size)) / denominator
    half = z * ((p * (1 - p) / size + z * z / (4 * size * size)) ** 0.5) / denominator
    return (round(max(0.0, centre - half), 5), round(min(1.0, centre + half), 5))


def load(derived: Path) -> tuple[pd.DataFrame, dict[str, str]]:
    paths = sorted(derived.glob("loans_*.parquet"))
    if not paths:
        raise SystemExit(f"no loans_*.parquet under {derived}")
    columns = [
        "loan_id", "origination_year", "origination_quarter",
        "first_payment_date", "first_payment_lag", "last_age",
        "first_bad_age", "first_bad_age_outside_relief",
        "termination_code", "termination_age",
    ]
    frame = pd.concat(
        [pd.read_parquet(path, columns=columns) for path in paths],
        ignore_index=True,
    )
    return frame, {path.name: sha256(path) for path in paths}


def performance_cutoff(derived: Path) -> dt.date:
    """The last month on file across every year's reduction record."""
    last = 0
    for record in derived.glob("reduce_*.json"):
        last = max(last, int(json.loads(
            record.read_text(encoding="utf-8"))["last_period_on_file"]))
    if not last:
        raise SystemExit(f"no reduce_*.json under {derived}")
    return dt.date(last // 100, last % 100, 1)


def histories(frame: pd.DataFrame, bad_column: str = "first_bad_age") -> list[LoanHistory]:
    out = []
    for fpd, last, bad, code, at in zip(
        frame["first_payment_date"].tolist(),
        frame["last_age"].tolist(),
        frame[bad_column].tolist(),
        frame["termination_code"].tolist(),
        frame["termination_age"].tolist(),
    ):
        out.append(LoanHistory(
            first_payment=dt.date(int(fpd) // 100, int(fpd) % 100, 1),
            last_age=int(last),
            first_bad_age=None if pd.isna(bad) else int(bad),
            termination_code=None if pd.isna(code) else int(code),
            termination_age=None if pd.isna(at) else int(at),
        ))
    return out


def cohort_table(
    frame: pd.DataFrame, cohort: pd.Series, labelled: pd.Series, label: pd.Series
) -> dict[str, dict]:
    """Per cohort: size, labelled count, defaults, rate, band, floor status."""
    table = {}
    grouped = pd.DataFrame({
        "cohort": cohort, "labelled": labelled, "label": label.fillna(0),
    }).groupby("cohort", sort=True)
    for key, group in grouped:
        size = len(group)
        n = int(group["labelled"].sum())
        defaults = int(group.loc[group["labelled"], "label"].sum())
        rate = defaults / n if n else float("nan")
        table[str(key)] = {
            "loans": size,
            "labelled": n,
            "labelled_share": round(n / size, 4) if size else None,
            "defaults": defaults,
            "rate": None if n == 0 else round(rate, 5),
            "wilson_95": list(wilson(defaults, n)) if n else None,
            "above_floors": n >= MIN_LOANS and defaults >= MIN_DEFAULTS,
        }
    return table


def summarise(derived: Path) -> dict:
    frame, hashes = load(derived)
    frame = frame.sort_values(["origination_quarter", "loan_id"]).reset_index(drop=True)
    cutoff = performance_cutoff(derived)

    lag = frame["first_payment_lag"].astype(int)
    quarter = frame["origination_quarter"]
    half = frame["origination_year"].astype(str) + "H" + (
        (quarter.str[-1].astype(int) + 1) // 2).astype(str)
    year = frame["origination_year"].astype(str)

    lag_by_cohort = {}
    for key, group in lag.groupby(quarter, sort=True):
        lag_by_cohort[str(key)] = {
            "median": float(group.median()),
            "p95": float(group.quantile(0.95)),
            "late_share": round(float((group >= LATE_FIRST_PAYMENT_MONTHS).mean()), 5),
            "negative_share": round(float((group < 0).mean()), 5),
        }

    # Re-dated loans: the first payment date is a conversion or modification
    # date, the servicing record begins before it, and a window run from it
    # is not a window from origination. Excluded from the label, and counted.
    redated = lag >= LATE_FIRST_PAYMENT_MONTHS
    # A delinquency at or before age zero on a loan that is not re-dated would
    # mean the clock is wrong for a reason the lag does not catch. Counted so
    # the audit can see it is zero, or is not. A termination at age zero is a
    # different thing: a loan paid off, or repurchased, before its first
    # payment came due, with one performance row. Counted separately.
    delinquent_before_clock = (frame["first_bad_age"].fillna(1) < 1).fillna(False)
    terminated_before_clock = (frame["termination_age"].fillna(1) < 1).fillna(False)

    # A loan with no performance record has no history to label; the reducer
    # admits such loans only inside the reporting lag before the cutoff, so
    # they are immature under any window. Counted, not labelled.
    unrecorded = frame["last_age"].isna()
    kept = frame.loc[~redated & ~unrecorded]
    kept_positions = kept.index.to_numpy()
    # Two readings of the same label. `first_bad_age` counts every month at
    # ninety days or more; `first_bad_age_outside_relief` sets aside the
    # months spent under a borrower assistance plan or a declared disaster
    # hardship, which Freddie Mac reports as delinquent off the last paid
    # installment. Both are tabulated so the choice between them is measured.
    readings = {
        "relief_counts": ("first_bad_age", True),
        "relief_set_aside": ("first_bad_age_outside_relief", False),
    }
    windows = {}
    for window in WINDOWS:
        block = {
            "excluded_redated": int(redated.sum()),
            "excluded_without_performance_record": int(unrecorded.sum()),
        }
        for reading, (bad_column, counts) in readings.items():
            definition = PerformanceLabelDefinition(
                window_months=window, performance_cutoff=cutoff,
                relief_months_count=counts)
            labels = build_performance_labels(histories(kept, bad_column), definition)
            labelled = pd.Series(False, index=frame.index)
            labelled.iloc[kept_positions[list(labels.indices)]] = True
            label = pd.Series(pd.NA, index=frame.index, dtype="Int8")
            label.iloc[kept_positions[list(labels.indices)]] = labels.labels

            by_quarter = cohort_table(frame, quarter, labelled, label)
            by_half = cohort_table(frame, half, labelled, label)
            by_year = cohort_table(frame, year, labelled, label)
            block[reading] = {
                "label": labels.as_dict(),
                "cohorts_above_floors": {
                    "quarterly": sum(v["above_floors"] for v in by_quarter.values()),
                    "semi_annual": sum(v["above_floors"] for v in by_half.values()),
                    "annual": sum(v["above_floors"] for v in by_year.values()),
                },
                "by_quarter": by_quarter,
                "by_half": by_half,
                "by_year": by_year,
            }
        # The reading that the log and the plots call the label, until an
        # ADR says otherwise, is the one that counts every delinquent month.
        block.update(block["relief_counts"])
        # Per cohort, how many of the defaults under the first reading were
        # under relief at their first bad month. That share is the size of
        # the definitional choice, cohort by cohort.
        raw = block["relief_counts"]["by_quarter"]
        aside = block["relief_set_aside"]["by_quarter"]
        block["defaults_under_relief_by_quarter"] = {
            c: {
                "defaults": raw[c]["defaults"],
                "defaults_outside_relief": aside[c]["defaults"],
                "share_under_relief": (
                    round(1 - aside[c]["defaults"] / raw[c]["defaults"], 4)
                    if raw[c]["defaults"] else None
                ),
            }
            for c in raw
        }
        windows[str(window)] = block

    termination = frame["termination_code"].value_counts(dropna=False)
    return {
        "derived_dir": derived.as_posix(),
        "inputs_sha256": hashes,
        "loans": len(frame),
        "redated": {
            "rule": f"first payment {LATE_FIRST_PAYMENT_MONTHS}+ months after the "
                    f"origination quarter opens",
            "count": int(redated.sum()),
            "share": round(float(redated.mean()), 5),
            "delinquent_before_age_one_among_redated": int((delinquent_before_clock & redated).sum()),
            "delinquent_before_age_one_among_the_rest": int((delinquent_before_clock & ~redated).sum()),
            "terminated_before_age_one_among_the_rest": int((terminated_before_clock & ~redated).sum()),
        },
        "origination_span": {
            "first": str(quarter.min()),
            "last": str(quarter.max()),
            "quarterly_cohorts": int(quarter.nunique()),
        },
        "performance_cutoff": cutoff.isoformat(),
        "floors": {"min_loans": MIN_LOANS, "min_defaults": MIN_DEFAULTS},
        "late_first_payment_months": LATE_FIRST_PAYMENT_MONTHS,
        "first_payment_lag": {
            "overall_median": float(lag.median()),
            "overall_late_share": round(float((lag >= LATE_FIRST_PAYMENT_MONTHS).mean()), 5),
            "overall_negative_share": round(float((lag < 0).mean()), 5),
            "by_cohort": lag_by_cohort,
        },
        "cohort_sizes": {str(k): int(v) for k, v in quarter.value_counts().sort_index().items()},
        "termination_codes": {
            "none" if pd.isna(k) else str(int(k)): int(v) for k, v in termination.items()
        },
        "windows": windows,
    }


def plot_cohorts(summary: dict, out: Path) -> None:
    cohorts = list(summary["cohort_sizes"])
    sizes = [summary["cohort_sizes"][c] for c in cohorts]
    positions = range(len(cohorts))
    figure, top = plt.subplots(figsize=(14, 5.5))
    top.bar(positions, sizes, color="#9fb8c8", width=0.85, label="loans in the sample")
    top.set_ylabel("loans in the sample")
    top.set_xlabel("origination quarter")
    bottom = top.twinx()
    for window, style in (("12", "-"), ("24", "--")):
        table = summary["windows"][window]["by_quarter"]
        bottom.plot(
            positions, [table[c]["labelled_share"] for c in cohorts],
            color="#0E6B66", linestyle=style, linewidth=2,
            label=f"share labelled at {window} months",
        )
    bottom.set_ylabel("share of cohort with a mature label")
    bottom.set_ylim(0, 1.05)
    bottom.legend(loc="lower left")
    step = max(1, len(cohorts) // 28)
    top.set_xticks(list(positions)[::step])
    top.set_xticklabels(cohorts[::step], rotation=90, fontsize=8)
    top.set_title("Freddie Mac sample: cohort size and the share carrying a mature label")
    figure.tight_layout()
    figure.savefig(out, dpi=140)
    plt.close(figure)


def plot_trajectory(summary: dict, out: Path) -> None:
    cohorts = list(summary["cohort_sizes"])
    positions = list(range(len(cohorts)))
    figure, axis = plt.subplots(figsize=(14, 5.5))
    for window, colour in (("12", "#B5451B"), ("24", "#0E6B66")):
        table = summary["windows"][window]["by_quarter"]
        rates = [table[c]["rate"] if table[c]["rate"] is not None else float("nan")
                 for c in cohorts]
        low = [table[c]["wilson_95"][0] if table[c]["wilson_95"] else float("nan")
               for c in cohorts]
        high = [table[c]["wilson_95"][1] if table[c]["wilson_95"] else float("nan")
                for c in cohorts]
        axis.fill_between(positions, low, high, color=colour, alpha=0.15, linewidth=0)
        axis.plot(positions, rates, color=colour, linewidth=2,
                  label=f"{window}-month 90+ rate")
        below = [i for i, c in enumerate(cohorts) if not table[c]["above_floors"]]
        axis.scatter([positions[i] for i in below], [rates[i] for i in below],
                     color=colour, marker="x", s=30, zorder=3,
                     label=f"{window}-month: below the floors")
        aside = summary["windows"][window]["relief_set_aside"]["by_quarter"]
        aside_rates = [aside[c]["rate"] if aside[c]["rate"] is not None else float("nan")
                       for c in cohorts]
        axis.plot(positions, aside_rates, color=colour, linewidth=1.2, linestyle="--",
                  label=f"{window}-month, relief months set aside")
    axis.set_ylabel("share of labelled loans 90+ days past due within the window")
    axis.set_xlabel("origination quarter")
    axis.set_ylim(bottom=0)
    step = max(1, len(cohorts) // 28)
    axis.set_xticks(positions[::step])
    axis.set_xticklabels(cohorts[::step], rotation=90, fontsize=8)
    axis.legend(loc="upper right")
    axis.set_title(
        f"Freddie Mac sample: default trajectory by origination quarter, floors "
        f"{summary['floors']['min_loans']:,} loans and {summary['floors']['min_defaults']} defaults"
    )
    figure.tight_layout()
    figure.savefig(out, dpi=140)
    plt.close(figure)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("derived", type=Path, help="directory of loans_YYYY.parquet")
    parser.add_argument("--out-dir", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    summary = summarise(args.derived)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    plot_cohorts(summary, args.out_dir / "cohorts.png")
    plot_trajectory(summary, args.out_dir / "trajectory.png")

    span = summary["origination_span"]
    lag = summary["first_payment_lag"]
    print(f"loans                    : {summary['loans']:,}")
    print(f"origination span         : {span['first']} .. {span['last']} "
          f"({span['quarterly_cohorts']} quarterly cohorts)")
    print(f"performance cutoff       : {summary['performance_cutoff']}")
    print(f"first payment lag        : median {lag['overall_median']:.0f} months, "
          f"{lag['overall_late_share']:.2%} at {summary['late_first_payment_months']}+ months, "
          f"{lag['overall_negative_share']:.2%} before the quarter")
    redated = summary["redated"]
    unrecorded = summary["windows"]["12"]["excluded_without_performance_record"]
    print(f"no performance record    : {unrecorded:,}, not labelled")
    print(f"re-dated, excluded       : {redated['count']:,} ({redated['share']:.2%}); "
          f"delinquent before age one: {redated['delinquent_before_age_one_among_redated']:,} "
          f"among them, {redated['delinquent_before_age_one_among_the_rest']:,} among the rest; "
          f"terminated before age one among the rest: "
          f"{redated['terminated_before_age_one_among_the_rest']:,}")
    for window in WINDOWS:
        block = summary["windows"][str(window)]
        label = block["label"]
        above = block["cohorts_above_floors"]
        print(f"\n{window}-month window")
        print(f"  labelled               : {label['labelled']:,}  "
              f"defaults {label['defaults']:,}  rate {label['default_rate']:.2%}")
        print(f"  immature / censored    : {label['dropped_immature']:,} / {label['censored']:,}")
        print(f"  cohorts above floors   : quarterly {above['quarterly']}, "
              f"semi-annual {above['semi_annual']}, annual {above['annual']}")
        table = block["by_quarter"]
        rated = [(c, v["rate"]) for c, v in table.items() if v["above_floors"]]
        if rated:
            low = min(rated, key=lambda cv: cv[1])
            high = max(rated, key=lambda cv: cv[1])
            print(f"  quarterly rate range   : {low[1]:.2%} ({low[0]}) .. "
                  f"{high[1]:.2%} ({high[0]}) over cohorts above the floors")
        aside = block["relief_set_aside"]
        above = aside["cohorts_above_floors"]
        print(f"  relief months set aside: defaults {aside['label']['defaults']:,}  "
              f"rate {aside['label']['default_rate']:.2%}; cohorts above floors "
              f"quarterly {above['quarterly']}, semi-annual {above['semi_annual']}, "
              f"annual {above['annual']}")
        shares = block["defaults_under_relief_by_quarter"]
        heavy = [(c, v["share_under_relief"]) for c, v in shares.items()
                 if v["share_under_relief"] is not None and v["share_under_relief"] >= 0.25]
        if heavy:
            print("  cohorts with 25%+ of defaults under relief: "
                  + ", ".join(f"{c} {s:.0%}" for c, s in heavy))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
