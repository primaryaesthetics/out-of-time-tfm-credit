#!/usr/bin/env python3
"""Fits the classical models on one Freddie Mac build and keeps every score they produce.

The counterpart of `score_build.py` on the second book. It reads the reduced
parquet of `freddie_mac_reduce.py` rather than the zips, and it writes the same
four files in the same schema — `scores.parquet`, `reference.parquet`,
`cohorts.csv`, `build.json` — so that `build_intervals.py` and
`arm_intervals.py` read a Freddie Mac build exactly as they read a Lending Club
one. The three model units are the same: the scorecard and the GBM on the
whole training pool, and the GBM on each fifty-thousand-row context sample at
the point the full pool chose. What differs is the book (ADR-0006, EXP-005),
and every quantity in which it differs is an argument whose default is the
book's:

  * The label is ninety days past due, REO or a bad termination within
    twenty-four months of the first payment month, with the months spent
    under a borrower assistance plan or a declared disaster set aside. Two
    more readings are built on the same rows and written beside `outcome`
    in both parquet files, so every metric can be recomputed under them
    without refitting anything: `outcome_reported`, with the relief months
    counted, and `outcome_horizon`, the first reading over a twelve-month
    window. The models are fitted on the first reading only.
  * The pool of a build at T is the whole origination quarters ending
    twenty-seven months before T. The builder checks that gap against the
    label window and the latest first payment the book admits before it
    reads a row, and every training loan's own window afterwards; the build
    record counts the loans in the blind gap whose own window had closed,
    which is what cutting on whole quarters costs.
  * The cohorts are half-years of the origination quarter in the loan
    identifier, named `2005H1`, and each is scored whole. A cohort is scored
    only if every admitted loan's window had closed by the performance
    cutoff; a later last cohort is refused rather than scored in part.
    `age_quarters` is counted in quarters from the build's quarter to the
    cohort's first quarter, so half-year cohorts sit at odd quarter ages:
    one, three, five and on.
  * Loans whose first payment falls six months or more after their quarter
    opens carry a conversion date rather than an origination date and are
    excluded as re-dated, as are the loans with no servicing record yet.
  * A loan first observed after `MAX_FIRST_OBSERVED_AGE` was acquired
    seasoned and its window is only partly on file, and a loan whose record
    misses a month inside its window is the same gap in another place; a gap
    after the window is not read, as no other event after the window is.
    Both are excluded from every reading and counted per scored cohort, and
    both are read from the monthly slice the reducer keeps for the window.
  * The sample carries no borrower key, so a borrower can be trained on and
    scored under two loans. The build record counts the scored loans whose
    pre-HARP identifier names a training loan, a lower bound on that.

The three feature gates of `fm_features` run on every invocation, and so does
its shift report; all four reports go into `build.json` with the maturity of
every scored cohort. No build date is written here: `--as-of` names one
build, and a grid is a list of invocations. Per-model discrimination and
calibration are printed to the console as `score_build.py` prints them unless
`--quiet-metrics` is given; the files carry them either way.

    python scripts/record_run.py fm-<build>-scores -- \\
        python scripts/fm_score_build.py data/derived/freddie-mac \\
            --out-dir experiments/<date>-fm-<build>-scores --as-of <date> --arm E
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from freddie_mac_reduce import WINDOW_KEPT_MONTHS
from freddie_mac_structure import performance_cutoff, sha256
from score_build import (
    CONTEXT,
    CONTROL_REFIT,
    FULL,
    SCORECARD,
    SHARE_TAIL_POLICY,
    cohort_aggregates,
    refit_point,
)

from outoftime import fm_features
from outoftime import gbm as gb
from outoftime import scorecard as sc
from outoftime.freddie_mac import LATE_FIRST_PAYMENT_MONTHS, safe_features
from outoftime.label import add_months
from outoftime.performance_label import (
    MAX_FIRST_OBSERVED_AGE,
    LoanHistory,
    PerformanceLabelDefinition,
    PerformanceLabelSet,
    build_performance_labels,
)
from outoftime.vintage import (
    CONTEXT_ROWS,
    CONTEXT_SEEDS,
    FREDDIE_MAC,
    TEST_SAMPLE_SEED,
    HalfYear,
    Quarter,
    VintageBuild,
    builds,
    parse_cohort,
)

# What the matrix, the gates, the label readings and the records read.
LOAN_COLUMNS = [
    *safe_features(), "loan_id", "pre_harp_loan_id", "origination_quarter",
    "origination_year", "first_payment_date", "first_payment_lag", "n_periods", "last_age",
    "first_bad_age", "first_bad_age_outside_relief", "termination_code", "termination_age",
]

# The two readings of the label, ADR-0006: the first is the study's, the
# second the sensitivity. Each names the reducer's column and whether a month
# under relief counts as a default event.
PRIMARY = "relief_set_aside"
REPORTED = "relief_counts"
READINGS = {
    PRIMARY: ("first_bad_age_outside_relief", False),
    REPORTED: ("first_bad_age", True),
}

# The horizon check of ADR-0006: the first reading over twelve months.
HORIZON_WINDOW_MONTHS = 12

FIRST_OBSERVED_BUCKETS = ((None, 1), (2, 3), (4, 6), (7, 12), (13, 24), (25, None))


@dataclasses.dataclass
class Prepared:
    """One build and everything a model unit or a bundle needs from the book."""

    build: VintageBuild
    grid: dict
    matrix: pd.DataFrame
    labels: list[int | None]
    outcome: np.ndarray
    outcome_reported: np.ndarray
    outcome_horizon: np.ndarray
    origination: list[dt.date]
    primary: PerformanceLabelSet
    reported: PerformanceLabelSet
    horizon: PerformanceLabelSet
    gates: dict
    exclusions: dict
    cohort_maturity: dict
    exposure: dict
    cutoff: dt.date
    inputs: dict[str, str]
    seconds: float


def load(derived: Path) -> tuple[pd.DataFrame, dict[str, str]]:
    """Every loan of the reduced files, in a fixed order, and the files' hashes."""
    paths = sorted(derived.glob("loans_*.parquet"))
    if not paths:
        raise SystemExit(f"no loans_*.parquet under {derived}")
    frame = pd.concat([pd.read_parquet(path, columns=LOAN_COLUMNS) for path in paths],
                      ignore_index=True)
    frame = frame.sort_values(["origination_quarter", "loan_id"], kind="mergesort")
    return frame.reset_index(drop=True), {path.name: sha256(path) for path in paths}


def first_records(derived: Path, book: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Per loan, the age of its first record and whether its record misses a month.

    The monthly slice holds the first `WINDOW_KEPT_MONTHS` of every loan, so
    the first record is its earliest age there; a loan absent from the slice
    was first observed later, at its last age less its records plus one if
    the record is whole. A record misses a month when a month is absent
    between the loan's first record and the end of the slice, which is the
    window; a month missing later is not read.
    """
    paths = sorted(derived.glob("perf_*.parquet"))
    if not paths:
        raise SystemExit(f"no perf_*.parquet under {derived}")
    parts = [pd.read_parquet(path, columns=["loan_id", "age"]).groupby(
        "loan_id", sort=False)["age"].agg(["min", "count"]) for path in paths]
    summary = pd.concat(parts).groupby(level=0).agg({"min": "min", "count": "sum"})
    aligned = summary.reindex(book["loan_id"].to_numpy())
    last = book["last_age"].to_numpy(dtype=int)
    whole_start = last - book["n_periods"].to_numpy(dtype=int) + 1
    in_slice = aligned["min"].notna().to_numpy()
    first = np.where(in_slice, aligned["min"].fillna(0).to_numpy(), whole_start).astype(int)
    rows = aligned["count"].fillna(0).to_numpy(dtype=int)
    expected = np.maximum(np.minimum(last, WINDOW_KEPT_MONTHS) - first + 1, 0)
    gap = in_slice & (rows < expected)
    return first, gap


def bucket_counts(ages: np.ndarray) -> dict[str, int]:
    out = {}
    for low, high in FIRST_OBSERVED_BUCKETS:
        mask = np.ones(ages.size, dtype=bool)
        if low is not None:
            mask &= ages >= low
        if high is not None:
            mask &= ages <= high
        name = (f"<={high}" if low is None else f">={low}" if high is None else f"{low}-{high}")
        out[name] = int(mask.sum())
    return out


def loan_histories(book: pd.DataFrame, bad_column: str, first_observed: np.ndarray,
                   gapped: np.ndarray) -> list[LoanHistory]:
    """What the label needs of each loan, with when its record began and whether it is whole."""
    out = []
    for fpd, last, bad, code, at, seen, gap in zip(
        book["first_payment_date"].tolist(),
        book["last_age"].tolist(),
        book[bad_column].tolist(),
        book["termination_code"].tolist(),
        book["termination_age"].tolist(),
        first_observed.tolist(),
        gapped.tolist(),
    ):
        out.append(LoanHistory(
            first_payment=dt.date(int(fpd) // 100, int(fpd) % 100, 1),
            last_age=int(last),
            first_bad_age=None if pd.isna(bad) else int(bad),
            termination_code=None if pd.isna(code) else int(code),
            termination_age=None if pd.isna(at) else int(at),
            first_observed_age=int(seen),
            record_gap=bool(gap),
        ))
    return out


def quarter_starts(quarters: pd.Series) -> list[dt.date]:
    """The first day of each loan's origination quarter: its cohort date."""
    starts = {q: dt.date(int(q[:4]), (int(q[-1]) - 1) * 3 + 1, 1) for q in quarters.unique()}
    return [starts[q] for q in quarters]


def payment_months(yyyymm: pd.Series) -> list[dt.date]:
    """The first day of each loan's first payment month: its label clock."""
    months = {m: dt.date(int(m) // 100, int(m) % 100, 1) for m in yyyymm.unique()}
    return [months[m] for m in yyyymm]


def cohort_names(quarters: pd.Series, period: type) -> pd.Series:
    """Each loan's cohort at the grid's resolution, `2005H1` or `2005Q1`."""
    if period is Quarter:
        return quarters.astype(str)
    half = (quarters.str[-1].astype(int) + 1) // 2
    return quarters.str[:4] + "H" + half.astype(str)


def age_in_quarters(as_of: dt.date, cohort) -> int:
    """Quarters from the build's quarter to the cohort's first quarter.

    On quarterly cohorts this is `score_build.age_in_quarters`; half-year
    cohorts sit at odd quarter ages, one, three, five and on. The unit stays
    the quarter so that a slope on age reads in the same unit on both books.
    """
    built = Quarter.of(as_of)
    opened = Quarter.of(cohort.start)
    return (opened.year * 4 + opened.quarter) - (built.year * 4 + built.quarter)


def grid_cohorts(args: argparse.Namespace):
    """The first and last cohort of the grid, at the resolution asked for."""
    period = HalfYear if args.resolution == "half-year" else Quarter

    def default(cohort, edge: str):
        if period is HalfYear:
            return cohort
        return Quarter.of(cohort.start if edge == "first" else cohort.end)

    first = (parse_cohort(args.first_cohort) if args.first_cohort
             else default(FREDDIE_MAC.first_cohort, "first"))
    last = (parse_cohort(args.last_cohort) if args.last_cohort
            else default(FREDDIE_MAC.last_test_cohort, "last"))
    if type(first) is not period or type(last) is not period:
        raise SystemExit(f"--first-cohort and --last-cohort name {args.resolution} cohorts, "
                         f"not {first} and {last}")
    return first, last


def age_or_none(text: str) -> int | None:
    return None if text.strip().lower() == "none" else int(text)


def design_parser(description: str) -> argparse.ArgumentParser:
    """The arguments that decide a build, shared with the bundle exporter."""
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("derived", type=Path,
                        help="directory of loans_YYYY.parquet, perf_YYYY.parquet and "
                             "reduce_YYYY.json")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--as-of", type=dt.date.fromisoformat, required=True,
                        help="the build's as-of date, the last day of a cohort")
    parser.add_argument("--arm", default="E", choices=("E", "R"))
    parser.add_argument("--window", type=int, default=FREDDIE_MAC.label_lag_months,
                        help="label window in months from the first payment month; also the "
                             "blind gap on the label clock")
    parser.add_argument("--axis-gap", type=int, default=FREDDIE_MAC.axis_gap_months,
                        help="months from the end of the last training quarter to the build, "
                             "on the cohort axis")
    parser.add_argument("--max-clock-lag", type=int, default=FREDDIE_MAC.max_clock_lag_months,
                        help="latest first payment the book admits, in months from the first "
                             "day of the loan's quarter")
    parser.add_argument("--horizon-window", type=int, default=HORIZON_WINDOW_MONTHS,
                        help="window of the horizon-check reading, written as outcome_horizon")
    parser.add_argument("--resolution", default="half-year", choices=("half-year", "quarter"),
                        help="cohort resolution")
    parser.add_argument("--first-cohort", default=None,
                        help=f"first cohort of the book; default {FREDDIE_MAC.first_cohort} "
                             f"at the resolution asked for")
    parser.add_argument("--last-cohort", default=None,
                        help=f"last cohort scored; default {FREDDIE_MAC.last_test_cohort} "
                             f"at the resolution asked for")
    parser.add_argument("--test-rows", type=int, default=FREDDIE_MAC.rows_per_cohort,
                        help="rows sampled per cohort; default every cohort whole")
    parser.add_argument("--context-rows", type=int, default=CONTEXT_ROWS,
                        help="rows in each context sample")
    parser.add_argument("--seeds", default=",".join(str(s) for s in CONTEXT_SEEDS),
                        help="context seeds, comma-separated")
    parser.add_argument("--rolling-quarters", type=int, default=FREDDIE_MAC.rolling_quarters,
                        help="width of the rolling arm in quarters")
    parser.add_argument("--max-first-observed-age", type=age_or_none,
                        default=MAX_FIRST_OBSERVED_AGE,
                        help="exclude every loan whose first servicing record is later than "
                             "this age in months; 'none' excludes none")
    parser.add_argument("--keep-record-gaps", action="store_true",
                        help="label loans whose record misses a month instead of excluding them")
    parser.add_argument("--ablation", default=None, choices=sorted(fm_features.ABLATIONS),
                        help="build the ablation matrix EXP-005 names instead of the primary")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = design_parser(__doc__)
    parser.add_argument("--n-jobs", type=int, default=-1)
    parser.add_argument("--control-refit", type=Path, default=None,
                        help="a recorded score run of this build: fit only the control, at that "
                             f"run's full GBM point, with the share-sized tail, as {CONTROL_REFIT}")
    parser.add_argument("--quiet-metrics", action="store_true",
                        help="print row counts and fit times only, no per-model metric")
    return parser.parse_args(argv)


def seeds_of(args: argparse.Namespace) -> tuple[int, ...]:
    return tuple(int(v) for v in args.seeds.split(",") if v.strip())


def outcome_of(labels: PerformanceLabelSet, size: int) -> np.ndarray:
    """A label set as one value per row, -1 where the row carries no label."""
    out = np.full(size, -1, dtype=np.int8)
    out[list(labels.indices)] = labels.labels
    return out


def mask_of(positions, size: int) -> np.ndarray:
    out = np.zeros(size, dtype=bool)
    out[list(positions)] = True
    return out


@dataclasses.dataclass
class Loaded:
    """The book after its exclusions, its three label readings, and the columns a build reads."""

    frame: pd.DataFrame | None
    inputs: dict[str, str]
    cutoff: dt.date
    exclusions: dict
    loaded_by_cohort: pd.Series
    primary: PerformanceLabelSet
    reported: PerformanceLabelSet
    horizon: PerformanceLabelSet
    outcome: np.ndarray
    outcome_reported: np.ndarray
    outcome_horizon: np.ndarray
    labels: list[int | None]
    origination: list[dt.date]
    first_payment: list[dt.date]
    open_at_cutoff: np.ndarray
    book_cohort: np.ndarray
    loan_ids: np.ndarray
    pre_harp: np.ndarray


def load_book(args: argparse.Namespace, period: type) -> Loaded:
    """The book every Freddie Mac run reads, loaded and labelled one way.

    The re-dated loans and those with no servicing record are out; the three
    readings are built under the seasoned-acquisition and record-gap rules
    the arguments set. `frame` is the book itself, for the gates and the
    matrix, and a caller that needs neither deletes it.
    """
    frame, inputs = load(args.derived)
    cutoff = performance_cutoff(args.derived)
    loaded_by_cohort = cohort_names(frame["origination_quarter"], period).value_counts()

    redated = frame["first_payment_lag"].astype(int) >= LATE_FIRST_PAYMENT_MONTHS
    unrecorded = frame["last_age"].isna()
    exclusions = {
        "loaded": len(frame),
        "redated": int(redated.sum()),
        "redated_rule": f"first payment {LATE_FIRST_PAYMENT_MONTHS}+ months after the "
                        f"origination quarter opens",
        "without_performance_record": int(unrecorded.sum()),
    }
    book = frame.loc[~redated & ~unrecorded].reset_index(drop=True)
    del frame
    exclusions["book"] = len(book)
    first_observed, gapped = first_records(args.derived, book)
    exclusions["first_observed_age"] = bucket_counts(first_observed)
    exclusions["record_gaps"] = int(gapped.sum())

    histories = {column: loan_histories(book, column, first_observed, gapped)
                 for column, _ in READINGS.values()}

    def reading(column: str, counts: bool, window: int) -> PerformanceLabelSet:
        definition = PerformanceLabelDefinition(
            window_months=window, performance_cutoff=cutoff, relief_months_count=counts,
            max_first_observed_age=args.max_first_observed_age,
            exclude_record_gaps=not args.keep_record_gaps)
        return build_performance_labels(histories[column], definition)

    primary = reading(*READINGS[PRIMARY], args.window)
    reported = reading(*READINGS[REPORTED], args.window)
    horizon = reading(*READINGS[PRIMARY], args.horizon_window)
    size = len(book)
    outcome = outcome_of(primary, size)
    outcome_reported = outcome_of(reported, size)
    # Counting the relief months only adds default events, so every loan the
    # first reading labels the second labels too, and never as a better loan.
    labelled = np.asarray(primary.indices, dtype=np.int64)
    if (outcome_reported[labelled] < 0).any() or (
            outcome_reported[labelled] < outcome[labelled]).any():
        raise SystemExit("a loan the relief-set-aside reading labels is unlabelled or better "
                         "under the reading that counts relief months")
    labels: list[int | None] = [None] * size
    for index, value in zip(primary.indices, primary.labels):
        labels[index] = value
    exclusions["excluded_first_observed_late"] = len(primary.left_truncated)
    exclusions["excluded_record_gap"] = len(primary.record_gaps)

    fpd = book["first_payment_date"].astype(int).to_numpy()
    return Loaded(
        frame=book, inputs=inputs, cutoff=cutoff, exclusions=exclusions,
        loaded_by_cohort=loaded_by_cohort, primary=primary, reported=reported, horizon=horizon,
        outcome=outcome, outcome_reported=outcome_reported,
        outcome_horizon=outcome_of(horizon, size), labels=labels,
        origination=quarter_starts(book["origination_quarter"]),
        first_payment=payment_months(book["first_payment_date"]),
        open_at_cutoff=((cutoff.year - fpd // 100) * 12 + cutoff.month - fpd % 100 + 1)
        < args.window,
        book_cohort=cohort_names(book["origination_quarter"], period).to_numpy(),
        loan_ids=book["loan_id"].to_numpy(),
        pre_harp=book["pre_harp_loan_id"].to_numpy(),
    )


def prepare(args: argparse.Namespace) -> Prepared:
    """The book, the gates, the label readings, the matrix and the one build.

    The single place that decides which rows a build trains on, scores and
    samples as context, so that the score run and the bundle of the same
    build are the same rows by construction.
    """
    started = time.time()
    first_cohort, last_cohort = grid_cohorts(args)
    period = type(first_cohort)
    loaded = load_book(args, period)
    book, loaded.frame = loaded.frame, None
    inputs, cutoff, exclusions = loaded.inputs, loaded.cutoff, loaded.exclusions
    loaded_by_cohort = loaded.loaded_by_cohort

    gate_span = {"first_cohort": fm_features.FIRST_COHORT,
                 "last_cohort": str(last_cohort)}
    gates = {
        "redundancy": fm_features.redundancy_report(book),
        "coverage": fm_features.coverage_report(book, **gate_span, ablation=args.ablation),
        "values": fm_features.value_report(book, **gate_span, ablation=args.ablation),
        "shifts": fm_features.shift_report(book, **gate_span, ablation=args.ablation),
    }

    primary, reported, horizon = loaded.primary, loaded.reported, loaded.horizon
    outcome, outcome_reported = loaded.outcome, loaded.outcome_reported
    outcome_horizon, labels = loaded.outcome_horizon, loaded.labels
    size = len(outcome)
    origination, first_payment = loaded.origination, loaded.first_payment
    open_at_cutoff, book_cohort = loaded.open_at_cutoff, loaded.book_cohort
    loan_ids, pre_harp = loaded.loan_ids, loaded.pre_harp
    matrix = fm_features.model_matrix(book, ablation=args.ablation)
    del book

    (build,) = builds(
        origination, knowable=first_payment, as_of_dates=(args.as_of,), arm=args.arm,
        label_lag_months=args.window, axis_gap_months=args.axis_gap,
        max_clock_lag_months=args.max_clock_lag,
        first_cohort=first_cohort, last_cohort=last_cohort,
        rows_per_quarter=args.test_rows, seed=TEST_SAMPLE_SEED, labels=primary,
        rolling_quarters=args.rolling_quarters,
    )

    # Every scored cohort, against the loans the file holds for it: how many
    # carry each reading, how many were left out and why. A cohort with a
    # loan whose window was still open at the cutoff is labelled on part of
    # its loans only, and it is refused rather than scored.
    late_first = mask_of(primary.left_truncated, size)
    with_gap = mask_of(primary.record_gaps, size)
    train_ids = set(loan_ids[list(build.train)])
    linked = np.asarray([value is not None and value in train_ids for value in pre_harp])
    cohort_maturity = {}
    unfinished = []
    for cohort, rows in build.test:
        name = str(cohort)
        in_book = book_cohort == name
        loans = int(loaded_by_cohort.get(name, 0))
        still_open = int((in_book & open_at_cutoff).sum())
        cohort_maturity[name] = {
            "loans": loans,
            "book": int(in_book.sum()),
            "labelled": int((in_book & (outcome >= 0)).sum()),
            "labelled_reported": int((in_book & (outcome_reported >= 0)).sum()),
            "labelled_horizon": int((in_book & (outcome_horizon >= 0)).sum()),
            "labelled_share": round(float((in_book & (outcome >= 0)).sum() / loans), 4)
            if loans else None,
            "window_open_at_cutoff": still_open,
            "excluded_first_observed_late": int((in_book & late_first).sum()),
            "excluded_record_gap": int((in_book & with_gap).sum()),
            "scored": len(rows),
            "scored_linked_to_training_by_pre_harp_id": int(linked[list(rows)].sum()),
        }
        if still_open:
            unfinished.append((name, still_open))
    if unfinished:
        raise SystemExit(f"scored cohorts hold loans whose {args.window}-month window was open "
                         f"at the cutoff {cutoff.isoformat()}: {unfinished}; move "
                         f"--last-cohort back")
    label_horizon = add_months(build.as_of, -args.window)
    exposure = {
        "training_windows_open_at_as_of": sum(first_payment[i] > label_horizon
                                               for i in build.train),
        "blind_loans_with_closed_windows": sum(first_payment[i] <= label_horizon
                                               for i in build.blind if outcome[i] >= 0),
        "scored_linked_to_training_by_pre_harp_id": int(sum(
            linked[list(rows)].sum() for _, rows in build.test)),
    }
    exclusions["excluded_first_observed_late"] = len(primary.left_truncated)
    exclusions["excluded_record_gap"] = len(primary.record_gaps)

    grid = {
        "book": dataclasses.replace(
            FREDDIE_MAC, label_lag_months=args.window, axis_gap_months=args.axis_gap,
            max_clock_lag_months=args.max_clock_lag, first_cohort=first_cohort,
            last_test_cohort=last_cohort, rows_per_cohort=args.test_rows,
            rolling_quarters=args.rolling_quarters).as_dict(),
        "arm": args.arm,
        "context_rows": args.context_rows,
        "horizon_window": args.horizon_window,
        "max_first_observed_age": args.max_first_observed_age,
        "exclude_record_gaps": not args.keep_record_gaps,
        "ablation": args.ablation,
        "gate_span": gate_span,
    }
    return Prepared(
        build=build, grid=grid, matrix=matrix, labels=labels, outcome=outcome,
        outcome_reported=outcome_reported, outcome_horizon=outcome_horizon,
        origination=origination, primary=primary, reported=reported, horizon=horizon,
        gates=gates, exclusions=exclusions, cohort_maturity=cohort_maturity, exposure=exposure,
        cutoff=cutoff, inputs=inputs, seconds=time.time() - started,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    seeds = seeds_of(args)

    started = time.time()
    prepared = prepare(args)
    build, matrix, labels = prepared.build, prepared.matrix, prepared.labels
    outcome = prepared.outcome
    readings = {"outcome_reported": prepared.outcome_reported,
                "outcome_horizon": prepared.outcome_horizon}
    exclusions = prepared.exclusions
    print(f"loans loaded          : {exclusions['loaded']:,}")
    print(f"re-dated, excluded    : {exclusions['redated']:,}")
    print(f"no servicing record   : {exclusions['without_performance_record']:,}")
    print(f"first observed late   : {exclusions['excluded_first_observed_late']:,}")
    print(f"record with a gap     : {exclusions['excluded_record_gap']:,}")
    print(f"performance cutoff    : {prepared.cutoff.isoformat()}")
    print(f"prepared in           : {prepared.seconds:.0f}s")
    print(f"features              : {len(matrix.columns)}", flush=True)
    flagged = prepared.gates["shifts"]["flagged"]
    print(f"shifts flagged        : {', '.join(sorted(flagged)) or 'none'}")
    print(build.summary(), "\n", flush=True)

    # Every unit is (model, context seed, rows fitted on). The control reuses
    # the full pool's chosen point, as on Lending Club.
    units: list[tuple[str, int | None, tuple[int, ...]]] = [
        (SCORECARD, None, build.train), (FULL, None, build.train),
    ]
    units += [(CONTEXT, seed, build.context(seed=seed, size=args.context_rows))
              for seed in seeds]
    chosen: dict | None = None
    if args.control_refit is not None:
        chosen = refit_point(args.control_refit, build.build_id)
        units = [(CONTROL_REFIT, seed, positions) for _, seed, positions in units[2:]]

    scores: list[pd.DataFrame] = []
    reference: list[pd.DataFrame] = []
    aggregates: list[dict] = []
    summaries: dict[str, dict] = {}
    for model_name, context_seed, positions in units:
        fit_started = time.time()
        if model_name == SCORECARD:
            model = sc.fit(matrix, labels, rows=positions,
                           policy=sc.ScorecardPolicy(n_jobs=args.n_jobs),
                           declaration=fm_features.declaration(args.ablation))
        elif model_name == CONTROL_REFIT:
            model = gb.fit(matrix, labels, prepared.origination, rows=positions,
                           policy=SHARE_TAIL_POLICY, point=chosen,
                           declaration=fm_features.declaration(args.ablation))
        else:
            model = gb.fit(matrix, labels, prepared.origination, rows=positions,
                           policy=gb.DEFAULT_POLICY,
                           point=chosen if model_name == CONTEXT else None,
                           declaration=fm_features.declaration(args.ablation))
            if model_name == FULL:
                chosen = {knob: model.params[knob] for knob in gb.DEFAULT_POLICY.grid()[0]}
        elapsed = time.time() - fit_started
        tag = model_name if context_seed is None else f"{model_name}/{context_seed}"
        summaries[tag] = {
            "model": model_name, "context_seed": context_seed,
            "train_rows": len(positions), "pool_rows": len(build.train),
            "context_is_whole_pool": context_seed is not None and len(positions) == len(build.train),
            "fit_seconds": round(elapsed, 2),
            "summary": model.as_dict(),
        }

        index = list(positions)
        reference.append(pd.DataFrame({
            "model": model_name, "context_seed": context_seed,
            "row": np.asarray(index, dtype=np.int64), "outcome": outcome[index],
            "pd": model.predict_pd(matrix, rows=positions),
            **{name: values[index] for name, values in readings.items()},
        }))

        for cohort, rows in build.test:
            predicted = model.predict_pd(matrix, rows=rows)
            index = list(rows)
            truth = outcome[index]
            age = age_in_quarters(build.as_of, cohort)
            scores.append(pd.DataFrame({
                "model": model_name, "context_seed": context_seed, "cohort": str(cohort),
                "age_quarters": age, "row": np.asarray(index, dtype=np.int64), "outcome": truth,
                "pd": predicted, **{name: values[index] for name, values in readings.items()},
            }))
            record = cohort_aggregates(truth, predicted)
            record.update({"defaults_reported": int(readings["outcome_reported"][index].sum()),
                           "model": model_name, "context_seed": context_seed,
                           "cohort": str(cohort), "age_quarters": age})
            aggregates.append(record)
        if args.quiet_metrics:
            print(f"{tag:<18} {len(positions):>9,} rows  fit {elapsed:>6.1f}s", flush=True)
        else:
            mine = [a for a in aggregates if a["model"] == model_name
                    and a["context_seed"] == context_seed]
            print(f"{tag:<18} {len(positions):>9,} rows  fit {elapsed:>6.1f}s  "
                  f"gini {mine[0]['gini']:.3f}->{mine[-1]['gini']:.3f}  "
                  f"O/E {mine[0]['observed_over_expected']:.2f}->"
                  f"{mine[-1]['observed_over_expected']:.2f}", flush=True)

    score_frame = pd.concat(scores, ignore_index=True)
    score_frame["context_seed"] = score_frame["context_seed"].astype("Int64")
    reference_frame = pd.concat(reference, ignore_index=True)
    reference_frame["context_seed"] = reference_frame["context_seed"].astype("Int64")
    stamp = {"build_id": build.build_id, "arm": build.arm, "as_of": build.as_of.isoformat()}
    for name in ("build_id", "arm", "as_of"):
        score_frame.insert(0, name, stamp[name])
        reference_frame.insert(0, name, stamp[name])
    score_frame.to_parquet(args.out_dir / "scores.parquet", index=False)
    reference_frame.to_parquet(args.out_dir / "reference.parquet", index=False)

    cohorts = pd.DataFrame(aggregates)
    cohorts["context_seed"] = cohorts["context_seed"].astype("Int64")
    cohorts.insert(0, "build_id", build.build_id)
    cohorts.to_csv(args.out_dir / "cohorts.csv", index=False)

    summary = {
        "build": build.as_dict(),
        "grid": prepared.grid,
        "ablation": args.ablation,
        "label": prepared.primary.as_dict(),
        "label_reported": prepared.reported.as_dict(),
        "label_horizon": prepared.horizon.as_dict(),
        "performance_cutoff": prepared.cutoff.isoformat(),
        "exclusions": exclusions,
        "exposure": prepared.exposure,
        "cohort_maturity": prepared.cohort_maturity,
        "inputs_sha256": prepared.inputs,
        "features": list(matrix.columns),
        "categorical": list(fm_features.categorical_names(args.ablation)),
        "gates": prepared.gates,
        "seeds": {"test_sample": TEST_SAMPLE_SEED, "test_sample_inert": args.test_rows is None,
                  "context": list(seeds), "booster": gb.DEFAULT_POLICY.seed},
        "policy": {"scorecard": sc.ScorecardPolicy(n_jobs=args.n_jobs).as_dict(),
                   "gbm": gb.DEFAULT_POLICY.as_dict(),
                   **({CONTROL_REFIT: SHARE_TAIL_POLICY.as_dict()} if args.control_refit else {})},
        "control_refit_from": args.control_refit.as_posix() if args.control_refit else None,
        "units": summaries,
        "scored_rows": len(score_frame),
        "reference_rows": len(reference_frame),
        "wall_seconds": round(time.time() - started, 1),
    }
    (args.out_dir / "build.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\nscored rows           : {len(score_frame):,}")
    print(f"reference rows        : {len(reference_frame):,}")
    print(f"wall                  : {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
