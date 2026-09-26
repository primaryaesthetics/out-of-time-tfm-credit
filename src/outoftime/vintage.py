"""Vintage builds: what a model built on a given date was allowed to know.

A bank does not train on a random half of its book. It rebuilds a scorecard on
a date, using the loans whose outcome it could already see on that date, and it
then watches the model age against the cohorts written afterwards. This module
constructs exactly that and refuses to construct anything else.

Three quantities define a build:

  * the **as-of date** `T`, the day the model is built;
  * the **label lag**, the performance window the label is defined over, which
    is twelve months here;
  * the **arm**, expanding or rolling, which decides how far back the training
    pool reaches.

The consequence that separates this from the usual out-of-time split is the
blind gap. At `T` the loans originated in `(T - 12m, T]` exist, are on the
books, and have no label yet. They are not training rows and they are not test
rows; they are invisible to the model builder. A study that trains right up to
`T` has quietly used twelve months of outcomes that nobody had. The gap is not
a conservatism margin, it is the thing being modelled, and it is the most
common leak in published out-of-time credit work.

Three properties are worth stating because the tests assert them and a
refactor that loses one would not otherwise be noticed:

  * the per-quarter test sample is drawn once, from the quarter alone, and is
    therefore identical across builds, arms, models and seeds — cohort-to-
    cohort movement in a trajectory is then the model moving, not the sample;
  * the rolling arm spans exactly four quarters, not "about a year of rows",
    so the two arms differ in what they hold and not in how it was cut. This
    does not hold volume fixed — a four-quarter pool grows fifteenfold across
    the grid, an expanding one twenty-twofold — so the arm contrast is a
    recency contrast at growing volume, and volume itself is held fixed only
    by the fifty-thousand-row context;
  * every build is assembled by `splits.temporal_split`, which validates and
    raises, rather than by slicing a sorted frame.

Two books run on this grid, and `Book` holds what differs between them: the
label window, the gap on the cohort axis, the first and last cohort, the
cohort resolution, the rolling width, and whether a cohort is scored whole or
sampled. One difference is structural. On Lending Club a loan's cohort and its
label clock are the same date, `issue_d`, and the gap on the axis is the label
window. The Freddie Mac sample has no origination date: the cohort is the
origination quarter encoded in the loan identifier, grouped into half-years,
and the label window runs from the first payment month (ADR-0006), which falls
up to five months after the quarter opens. A pool of whole quarters ending
twenty-four months before the build would then hold loans whose windows were
still open, so on that book the gap on the axis is longer than the window, and
`builds` takes the first payment date as `knowable` and checks every training
loan's window on it. Left out, the one date does both jobs, which is the
Lending Club grid exactly.

Stdlib only, like the rest of the core: it takes sequences of dates and returns
positions into them, so it sits under pandas, polars or numpy without importing
any of them.
"""

from __future__ import annotations

import datetime as dt
import random
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from .features import FIRST_QUARTER
from .fm_features import FIRST_COHORT as FM_FIRST_COHORT_NAME
from .fm_features import LAST_COHORT as FM_LAST_COHORT_NAME
from .freddie_mac import LATE_FIRST_PAYMENT_MONTHS
from .label import LabelSet, add_months
from .splits import LeakageError, temporal_split

Date = dt.date

# The label the study runs on. ADR-0005: twelve months from origination, with
# twenty-four as the sensitivity check. Passing anything else here changes what
# the blind gap means, so it is a parameter rather than a constant only so that
# the leakage assertion can be tested against a build that violates it.
LABEL_LAG_MONTHS = 12

# The build grid. End of each half-year, 2013-06 through 2017-06: nine builds,
# every model on the same nine, nothing compared across grids.
DEFAULT_AS_OF: tuple[Date, ...] = (
    dt.date(2013, 6, 30),
    dt.date(2013, 12, 31),
    dt.date(2014, 6, 30),
    dt.date(2014, 12, 31),
    dt.date(2015, 6, 30),
    dt.date(2015, 12, 31),
    dt.date(2016, 6, 30),
    dt.date(2016, 12, 31),
    dt.date(2017, 6, 30),
)

# The rolling arm's width, in whole quarters. Four rather than the customary
# eight, because on a book whose volume grows this fast eight quarters is most
# of the book: it holds 71% to 90% of the expanding pool and moves the mean age
# of a training row by half a quarter at the earliest build. Four holds 43% to
# 63% and moves it by two to four quarters at every build, so the arm changes
# the thing it exists to change.
ROLLING_QUARTERS = 4

# One fixed sample per test quarter, shared by every build and every model. The
# seed is written down rather than passed around, because the whole point is
# that it never varies. Quarters holding fewer rows are used whole.
TEST_ROWS_PER_QUARTER = 20_000
TEST_SAMPLE_SEED = 20260902

# The in-context cap of the tabular foundation models. For a TFM the training
# window and the context sample are the same knob, so the arm decides which
# pool the sample is drawn from and this decides how much of it fits.
CONTEXT_ROWS = 50_000

# The three draws of that sample. Every model that reads a context — the two
# foundation models and the GBM control that exists to see the identical rows —
# reads these three and no others, so that a difference between two models is
# never a difference between two draws. Written down here rather than passed in
# for the same reason the scoring seed is.
CONTEXT_SEEDS = (20260911, 20260912, 20260913)


class VintageError(AssertionError):
    """A build that does not describe a situation any model builder was in."""


@dataclass(frozen=True, order=True)
class Quarter:
    """An origination cohort. Ordered, so ranges of them are ranges."""

    year: int
    quarter: int

    def __post_init__(self) -> None:
        if not 1 <= self.quarter <= 4:
            raise VintageError(f"quarter {self.quarter} is not in 1..4")

    @classmethod
    def of(cls, date: Date) -> Quarter:
        return cls(date.year, (date.month - 1) // 3 + 1)

    @property
    def start(self) -> Date:
        return dt.date(self.year, (self.quarter - 1) * 3 + 1, 1)

    @property
    def end(self) -> Date:
        """The last day of the quarter."""
        first_of_next = self.shift(1).start
        return first_of_next - dt.timedelta(days=1)

    def shift(self, quarters: int) -> Quarter:
        total = (self.year * 4 + self.quarter - 1) + quarters
        return Quarter(total // 4, total % 4 + 1)

    def __str__(self) -> str:
        return f"{self.year}Q{self.quarter}"


@dataclass(frozen=True, order=True)
class HalfYear:
    """A half-year origination cohort, ordered like `Quarter`, named `2005H1`.

    The resolution of the Freddie Mac trajectory, for the reason ADR-0006
    gives: at twelve thousand five hundred loans a quarter, the half-year is
    the finest cohort that carries a hundred defaults across nearly the whole
    book. The name sorts chronologically as text, which the node scorer
    relies on when it takes the youngest cohorts of a build.
    """

    year: int
    half: int

    def __post_init__(self) -> None:
        if not 1 <= self.half <= 2:
            raise VintageError(f"half {self.half} is not in 1..2")

    @classmethod
    def of(cls, date: Date) -> HalfYear:
        return cls(date.year, 1 if date.month <= 6 else 2)

    @property
    def start(self) -> Date:
        return dt.date(self.year, 1 if self.half == 1 else 7, 1)

    @property
    def end(self) -> Date:
        """The last day of the half-year."""
        return self.shift(1).start - dt.timedelta(days=1)

    def shift(self, halves: int) -> HalfYear:
        total = (self.year * 2 + self.half - 1) + halves
        return HalfYear(total // 2, total % 2 + 1)

    def __str__(self) -> str:
        return f"{self.year}H{self.half}"


Cohort = Quarter | HalfYear

_COHORT_NAME = re.compile(r"^(\d{4})([QH])(\d)$")


def parse_cohort(text: str) -> Cohort:
    """`2010Q2` as a `Quarter`, `2005H1` as a `HalfYear`, anything else refused."""
    match = _COHORT_NAME.match(text.strip())
    if match is None:
        raise VintageError(f"{text!r} names no cohort: write 2010Q2 or 2005H1")
    year, kind, number = int(match.group(1)), match.group(2), int(match.group(3))
    return Quarter(year, number) if kind == "Q" else HalfYear(year, number)


def cohorts_between(first: Cohort, last: Cohort) -> tuple[Cohort, ...]:
    """Every cohort from `first` to `last` inclusive, at their resolution."""
    if type(first) is not type(last):
        raise VintageError(f"{first} and {last} are cohorts of different resolutions")
    out = []
    cohort = first
    while cohort <= last:
        out.append(cohort)
        cohort = cohort.shift(1)
    return tuple(out)


# The usable book. The first cohort is a design choice made in the feature
# module, because it is the reference every value in the matrix is measured
# against: before 2010 the product and the volume describe another lender, and
# 2010Q2 rather than 2010Q1 because the 60-month product appeared in May 2010.
# The last is a measurement: performance is observable to 2019-03, so the
# newest origination carrying a mature twelve-month label is 2018-03, which is
# inside 2018Q1. A cohort past that has no labels, only immature loans that an
# unguarded pipeline would record as non-defaults.
FIRST_COHORT = Quarter(int(FIRST_QUARTER[:4]), int(FIRST_QUARTER[-1]))
LAST_TEST_COHORT = Quarter(2018, 1)

# The Freddie Mac sample, ADR-0006. The label is read over twenty-four months
# from the first payment month, so the blind gap on the label clock is
# twenty-four months. The first cohort is the half-year holding the feature
# module's first cohort, 1999Q1, the reference its value gate measures
# against; the expanding pool starts on that quarter either way. The last is a
# measurement, as on Lending
# Club: performance is on file to 2026-03, the newest cohort whose every loan
# has a closed twenty-four-month window is 2023H2, and 2024H1 is labelled on
# part of its loans only — the partial cohort the maturity gate exists to
# keep out.
FM_LABEL_LAG_MONTHS = 24
FM_FIRST_COHORT = HalfYear.of(parse_cohort(FM_FIRST_COHORT_NAME).start)
FM_LAST_TEST_COHORT = parse_cohort(FM_LAST_COHORT_NAME)

# The gap on the cohort axis. A loan's first payment falls up to five months
# after its quarter opens — six or more and it is re-dated and excluded — so
# its twenty-four-month window closes up to twenty-nine months after the
# quarter opens, twenty-seven after it ends. A pool of whole quarters ending
# twenty-seven months before the build holds no loan whose window is open;
# one ending twenty-four months before holds thousands, and
# `assert_no_leakage` refuses it on the loans' own first payment dates.
FM_AXIS_GAP_MONTHS = 27

# The latest label clock the book admits, in months from the first day of the
# loan's quarter: five, since a first payment six or more months on is
# re-dated and excluded.
FM_MAX_CLOCK_LAG_MONTHS = LATE_FIRST_PAYMENT_MONTHS - 1


def required_axis_gap(label_lag_months: int, max_clock_lag_months: int) -> int:
    """The shortest gap on the cohort axis under which no training window is open.

    A pool ends on a quarter's last day, two months after the quarter's first;
    a loan of that quarter starts its label clock up to `max_clock_lag_months`
    after the first, so up to that many months less two after the pool ends,
    and its window closes the label lag after that.
    """
    return label_lag_months + max(0, max_clock_lag_months - 2)


# The rolling arm on this book, eight quarters. The sample writes the same
# number of loans every quarter, so four quarters are one year of it and
# under the fifty-thousand-row context, which would then be the pool itself
# on every rolling build and its three draws one draw.
FM_ROLLING_QUARTERS = 8


@dataclass(frozen=True)
class Book:
    """What a vintage grid takes from the book rather than from the study.

    The context size and its seeds and the two leakage inequalities are the
    study's and are the same on both books. These are not. `axis_gap_months`
    is the gap between the last training quarter and the build on the cohort
    axis, at least the label window and longer where the label clock starts
    after the cohort date. `rows_per_cohort` is the scoring sample of each
    cohort, or `None` when every cohort is scored whole: on the Freddie Mac
    sample a half-year holds twenty-five thousand loans, already the size of
    the Lending Club sample, and a whole cohort is the same rows in every
    build without a seed to make it so.
    """

    name: str
    label_lag_months: int
    axis_gap_months: int
    max_clock_lag_months: int
    first_cohort: Cohort
    last_test_cohort: Cohort
    rows_per_cohort: int | None
    rolling_quarters: int
    cohort_axis: str
    label_clock: str

    def __post_init__(self) -> None:
        if type(self.first_cohort) is not type(self.last_test_cohort):
            raise VintageError(f"{self.name}: the first and last cohorts differ in resolution")
        need = required_axis_gap(self.label_lag_months, self.max_clock_lag_months)
        if self.axis_gap_months < need:
            raise VintageError(f"{self.name}: a {self.axis_gap_months}-month gap on the cohort "
                               f"axis, where the label window and the clock lag need {need}")

    @property
    def resolution(self) -> type:
        return type(self.first_cohort)

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "label_lag_months": self.label_lag_months,
            "axis_gap_months": self.axis_gap_months,
            "max_clock_lag_months": self.max_clock_lag_months,
            "first_cohort": str(self.first_cohort),
            "last_test_cohort": str(self.last_test_cohort),
            "resolution": self.resolution.__name__,
            "rows_per_cohort": self.rows_per_cohort,
            "rolling_quarters": self.rolling_quarters,
            "cohort_axis": self.cohort_axis,
            "label_clock": self.label_clock,
        }


LENDING_CLUB = Book(
    name="lending-club",
    label_lag_months=LABEL_LAG_MONTHS,
    axis_gap_months=LABEL_LAG_MONTHS,
    max_clock_lag_months=0,
    first_cohort=FIRST_COHORT,
    last_test_cohort=LAST_TEST_COHORT,
    rows_per_cohort=TEST_ROWS_PER_QUARTER,
    rolling_quarters=ROLLING_QUARTERS,
    cohort_axis="issue_d, by quarter",
    label_clock="issue_d",
)
FREDDIE_MAC = Book(
    name="freddie-mac",
    label_lag_months=FM_LABEL_LAG_MONTHS,
    axis_gap_months=FM_AXIS_GAP_MONTHS,
    max_clock_lag_months=FM_MAX_CLOCK_LAG_MONTHS,
    first_cohort=FM_FIRST_COHORT,
    last_test_cohort=FM_LAST_TEST_COHORT,
    rows_per_cohort=None,
    rolling_quarters=FM_ROLLING_QUARTERS,
    cohort_axis="the origination quarter in the loan identifier, by half-year",
    label_clock="first_payment_date",
)


def quarters_between(first: Quarter, last: Quarter) -> tuple[Quarter, ...]:
    if last < first:
        return ()
    span = (last.year * 4 + last.quarter) - (first.year * 4 + first.quarter)
    return tuple(first.shift(i) for i in range(span + 1))


def _rng(*parts: object) -> random.Random:
    """A generator seeded by what it is sampling, not by call order.

    Seeding from a string is deliberate. `random.Random` hashes a string seed
    with sha512, so the stream depends on the text and not on `PYTHONHASHSEED`,
    and the seed of any given sample can be read off the label in the manifest.
    Selection is shuffle-and-take rather than `random.sample`, whose algorithm
    switches strategy on the ratio of k to n and is an implementation detail.
    """
    return random.Random(":".join(str(part) for part in parts))


def _take(rng: random.Random, indices: Sequence[int], size: int) -> tuple[int, ...]:
    pool = sorted(indices)
    if len(pool) <= size:
        return tuple(pool)
    rng.shuffle(pool)
    return tuple(sorted(pool[:size]))


def cohorts(
    origination: Sequence[Date],
    *,
    first: Quarter = FIRST_COHORT,
    last: Quarter = LAST_TEST_COHORT,
    eligible: Iterable[int] | None = None,
) -> dict[Quarter, tuple[int, ...]]:
    """Groups row positions by origination quarter, inside the usable book.

    `eligible` restricts the rows considered, and it is how the maturity gate
    of `label.build_labels` reaches this module: pass `LabelSet.indices` and no
    immature loan can enter a cohort. Left at `None` every row counts, which is
    correct only when the caller has already filtered — the same contract as
    `embargo_days=0` in `splits.temporal_split`, and the same trap.

    The cohorts are at the resolution of `first` and `last`: quarters on
    Lending Club, half-years on the Freddie Mac sample.
    """
    if not origination:
        raise VintageError("no rows")
    period = type(first)
    if type(last) is not period:
        raise VintageError(f"{first} and {last} are cohorts of different resolutions")
    positions = range(len(origination)) if eligible is None else sorted(set(eligible))

    grouped: dict[Quarter, list[int]] = {}
    for i in positions:
        date = origination[i]
        if date is None:
            raise VintageError(f"row {i} has no origination date")
        quarter = period.of(date)
        if quarter < first or quarter > last:
            continue
        grouped.setdefault(quarter, []).append(i)
    return {q: tuple(sorted(rows)) for q, rows in sorted(grouped.items())}


def scoring_samples(
    origination: Sequence[Date],
    *,
    rows_per_quarter: int | None = TEST_ROWS_PER_QUARTER,
    seed: int = TEST_SAMPLE_SEED,
    first: Quarter = FIRST_COHORT,
    last: Quarter = LAST_TEST_COHORT,
    eligible: Iterable[int] | None = None,
) -> dict[Quarter, tuple[int, ...]]:
    """The scoring sample of every quarter, drawn once for the whole study.

    Each quarter is sampled from its own seed, so the sample of 2015Q3 does not
    depend on which other quarters were asked for, on the order they were asked
    in, or on which build is being assembled. Two builds that both score 2015Q3
    score the identical rows, which is what makes a trajectory readable: a step
    between cohorts is the model, never the draw.

    `rows_per_quarter=None` scores every cohort whole, and the seed is then
    inert; the property above holds without it.
    """
    if rows_per_quarter is not None and rows_per_quarter <= 0:
        raise VintageError("rows_per_quarter must be positive")
    grouped = cohorts(origination, first=first, last=last, eligible=eligible)
    if rows_per_quarter is None:
        return dict(grouped)
    return {
        quarter: _take(_rng(seed, quarter), rows, rows_per_quarter)
        for quarter, rows in grouped.items()
    }


@dataclass(frozen=True)
class VintageBuild:
    """One model build: an as-of date, an arm, and what it may see."""

    build_id: str
    as_of: Date
    arm: str
    label_lag_months: int
    train: tuple[int, ...]
    train_first: Date
    train_last: Date
    train_quarters: tuple[Quarter, ...]
    blind: tuple[int, ...]
    test: tuple[tuple[Quarter, tuple[int, ...]], ...]
    notes: tuple[str, ...] = field(default_factory=tuple)
    # The gap on the cohort axis, where it is not the label window. None on
    # Lending Club, whose summary then reads as it always has.
    axis_gap_months: int | None = None

    @property
    def knowable_through(self) -> Date:
        """The newest origination whose label was readable at the as-of date."""
        return add_months(self.as_of, -self.label_lag_months)

    @property
    def axis_horizon(self) -> Date:
        """The newest origination the training pool may reach on the cohort axis."""
        if self.axis_gap_months is None:
            return self.knowable_through
        return months_back(self.as_of, self.axis_gap_months)

    @property
    def test_cohorts(self) -> tuple[Quarter, ...]:
        return tuple(quarter for quarter, _ in self.test)

    @property
    def n_test(self) -> int:
        return sum(len(rows) for _, rows in self.test)

    def test_rows(self, quarter: Quarter) -> tuple[int, ...]:
        for candidate, rows in self.test:
            if candidate == quarter:
                return rows
        raise VintageError(f"{self.build_id} does not score {quarter}")

    def context(self, *, seed: int, size: int = CONTEXT_ROWS) -> tuple[int, ...]:
        """A uniform sample of the training pool, capped at the context size.

        For a foundation model this replaces fitting: the sample *is* the
        model's knowledge of the book, so the arm and this cap together are the
        training-window policy, and three seeds of it are what make the
        expanding-against-rolling comparison an experiment rather than a
        footnote. A pool at or below the cap is returned whole, and the seed is
        then inert — recorded anyway, so a manifest never implies a draw that
        did not happen.
        """
        if size <= 0:
            raise VintageError("context size must be positive")
        return _take(_rng(seed, self.build_id, "context"), self.train, size)

    def as_dict(self) -> dict:
        out = {
            "build_id": self.build_id,
            "as_of": self.as_of.isoformat(),
            "arm": self.arm,
            "label_lag_months": self.label_lag_months,
            "knowable_through": self.knowable_through.isoformat(),
            "train_rows": len(self.train),
            "train_first": self.train_first.isoformat(),
            "train_last": self.train_last.isoformat(),
            "train_quarters": [str(q) for q in self.train_quarters],
            "blind_rows": len(self.blind),
            "test_cohorts": {
                str(quarter): len(rows) for quarter, rows in self.test
            },
            "test_rows": self.n_test,
            "notes": list(self.notes),
        }
        if self.axis_gap_months is not None:
            out["axis_gap_months"] = self.axis_gap_months
            out["axis_horizon"] = self.axis_horizon.isoformat()
        return out

    def summary(self) -> str:
        head = (
            f"{self.build_id}: train {len(self.train)} rows "
            f"{self.train_first.isoformat()}..{self.train_last.isoformat()} "
            f"({len(self.train_quarters)} quarters), blind {len(self.blind)} rows, "
            f"test {self.n_test} rows over {len(self.test)} cohorts"
        )
        rows = ["| cohort | rows |", "| --- | --- |"]
        rows += [f"| {quarter} | {len(sample)} |" for quarter, sample in self.test]
        return "\n".join([head, "", *rows])


def _arm_pool(
    grouped: dict[Quarter, tuple[int, ...]],
    *,
    arm: str,
    knowable_through: Date,
    first_cohort: Quarter,
    rolling_quarters: int = ROLLING_QUARTERS,
) -> tuple[tuple[int, ...], tuple[Quarter, ...]]:
    """The training quarters of an arm, and the rows in them."""
    last_train = Quarter.of(knowable_through)
    if last_train.end != knowable_through:
        raise VintageError(
            f"the label horizon {knowable_through.isoformat()} is not the last day "
            f"of {last_train}: with a partial quarter the rolling arm would span "
            f"seven quarters and a stub, and the two arms would stop being "
            f"comparable. Choose as-of dates on quarter ends."
        )
    if arm == "E":
        window = quarters_between(first_cohort, last_train)
    elif arm == "R":
        window = quarters_between(last_train.shift(-(rolling_quarters - 1)), last_train)
        if len(window) != rolling_quarters:
            raise VintageError(
                f"the rolling arm wants {rolling_quarters} quarters ending at "
                f"{last_train} and got {len(window)}"
            )
    else:
        raise VintageError(f"arm {arm!r} is neither 'E' (expanding) nor 'R' (rolling)")

    present = tuple(q for q in window if q in grouped)
    rows = tuple(sorted(i for q in present for i in grouped[q]))
    return rows, present


def months_back(as_of: Date, months: int) -> Date:
    """`months` before `as_of`, landing on a month end when `as_of` is one.

    `add_months` keeps the day, so twenty-seven months before the 30th of
    June is the 30th of March, a day short of the quarter end a pool is cut
    on. A gap on the cohort axis is counted in whole months from the end of
    the as-of month, which is what an as-of date on a cohort end is.
    """
    if (as_of + dt.timedelta(days=1)).day != 1:
        return add_months(as_of, -months)
    first = add_months(as_of.replace(day=1), -months)
    return add_months(first, 1) - dt.timedelta(days=1)


def _build_id(as_of: Date, arm: str) -> str:
    half = 1 if as_of.month <= 6 else 2
    return f"{as_of.year}H{half}-{arm}"


def builds(
    origination: Sequence[Date],
    *,
    as_of_dates: Sequence[Date] = DEFAULT_AS_OF,
    arm: str = "E",
    label_lag_months: int = LABEL_LAG_MONTHS,
    first_cohort: Quarter = FIRST_COHORT,
    last_cohort: Quarter = LAST_TEST_COHORT,
    rows_per_quarter: int | None = TEST_ROWS_PER_QUARTER,
    seed: int = TEST_SAMPLE_SEED,
    eligible: Iterable[int] | None = None,
    labels: LabelSet | None = None,
    entity_ids: Sequence[object] | None = None,
    knowable: Sequence[Date] | None = None,
    rolling_quarters: int = ROLLING_QUARTERS,
    axis_gap_months: int | None = None,
    max_clock_lag_months: int | None = None,
) -> list[VintageBuild]:
    """Every build of the grid, on one arm, validated or refused.

    Each build is assembled through `splits.temporal_split` on the rows it
    touches, so the window ordering, the emptiness checks and the entity check
    are the ones the leakage gate names. The vintage-specific check that
    `temporal_split` cannot make is the width of the middle window: it is the
    blind gap, and it has to be at least the performance window, because that
    is what "the builder could not see these outcomes" means.

    Pass `labels` rather than `eligible` whenever a `LabelSet` exists. The two
    say the same thing about which rows may enter a cohort, but `labels` also
    carries the window the label was built over, and that window has to be the
    lag the grid is cut on: a grid cut for twenty-four months over rows
    labelled at twelve would score a year of loans whose windows had not
    closed, every one of them recorded as a non-default, and nothing downstream
    could tell. With `eligible` alone that agreement is the caller's to keep.

    `knowable` is the date each row's label window runs from, when it is not
    the cohort's date, and `axis_gap_months` the gap on the cohort axis, when
    it is not the label window. On Lending Club both are left out. On the
    Freddie Mac sample `origination` is the first day of the loan's
    origination quarter, `knowable` its first payment date, and the gap on
    the axis is longer than the window by the latest first payment the book
    admits: the pool of a build at T is the whole quarters ending that gap
    before T, every loan in it has a first payment at least the label window
    before T, and `assert_no_leakage` checks the second statement loan by
    loan. The pool is cut in quarters whatever the cohort resolution, so both
    arms keep their quarter widths; every as-of date has to close a cohort,
    or the cohort it falls in would be written partly before the build and
    partly after and could be neither trained on nor scored.

    `max_clock_lag_months` is the latest the label clock may start after the
    first day of a loan's quarter. Given, the gap is checked before any row
    is read against `required_axis_gap`, and every row's clock against the
    lag: the static statement of what `assert_no_leakage` then checks loan by
    loan.
    """
    clock = origination if knowable is None else knowable
    if len(clock) != len(origination):
        raise VintageError(
            f"{len(clock)} label-clock dates against {len(origination)} cohort dates"
        )
    axis_gap = label_lag_months if axis_gap_months is None else axis_gap_months
    if axis_gap < label_lag_months:
        raise VintageError(
            f"a {axis_gap}-month gap on the cohort axis under a {label_lag_months}-month "
            f"label admits loans whose windows had not closed"
        )
    if max_clock_lag_months is not None:
        need = required_axis_gap(label_lag_months, max_clock_lag_months)
        if axis_gap < need:
            raise VintageError(
                f"a {axis_gap}-month gap on the cohort axis admits a last quarter whose "
                f"loans start their clock up to {max_clock_lag_months} months after it "
                f"opens; their {label_lag_months}-month windows need a gap of {need}"
            )
    period = type(first_cohort)
    if labels is not None:
        if eligible is not None:
            raise VintageError("pass either labels or eligible, not both")
        window = labels.definition.window_months
        if window != label_lag_months:
            raise VintageError(
                f"the labels were built over a {window}-month window and the grid "
                f"is cut for a {label_lag_months}-month lag: the cohorts would hold "
                f"loans whose outcome the label does not describe"
            )
        eligible = labels.indices

    grouped = cohorts(
        origination, first=first_cohort, last=last_cohort, eligible=eligible
    )
    if not grouped:
        raise VintageError(
            f"no rows fall in {first_cohort}..{last_cohort}; the usable book is empty"
        )
    samples = scoring_samples(
        origination,
        rows_per_quarter=rows_per_quarter,
        seed=seed,
        first=first_cohort,
        last=last_cohort,
        eligible=eligible,
    )

    # The pool is whole quarters of the cohort axis. Where the cohort is a
    # quarter, that grouping is `grouped` itself.
    if period is Quarter:
        pool = grouped
    else:
        regrouped: dict[Quarter, list[int]] = {}
        for rows in grouped.values():
            for i in rows:
                regrouped.setdefault(Quarter.of(origination[i]), []).append(i)
        pool = {q: tuple(sorted(rows)) for q, rows in sorted(regrouped.items())}
    pool_start = Quarter.of(first_cohort.start)
    if knowable is not None and any(clock[i] is None for rows in grouped.values() for i in rows):
        raise VintageError("a row of the book has no label-clock date")
    if knowable is not None and max_clock_lag_months is not None:
        late = [
            i for rows in grouped.values() for i in rows
            if (clock[i].year * 12 + clock[i].month)
            - (Quarter.of(origination[i]).start.year * 12
               + Quarter.of(origination[i]).start.month) > max_clock_lag_months
        ]
        if late:
            raise VintageError(
                f"{len(late)} rows start their label clock more than "
                f"{max_clock_lag_months} months after their quarter opens, for example "
                f"row {late[0]}: the gap on the cohort axis does not cover them"
            )

    out: list[VintageBuild] = []
    for as_of in as_of_dates:
        knowable_through = add_months(as_of, -label_lag_months)
        horizon = knowable_through if axis_gap_months is None else months_back(as_of, axis_gap)
        train_rows, train_quarters = _arm_pool(
            pool, arm=arm, knowable_through=horizon,
            first_cohort=pool_start, rolling_quarters=rolling_quarters,
        )
        if period.of(as_of).end != as_of:
            raise VintageError(
                f"the as-of date {as_of.isoformat()} is not the last day of its cohort "
                f"{period.of(as_of)}: that cohort would be written partly before the "
                f"build and partly after, and could be neither trained on nor scored. "
                f"Choose as-of dates on cohort ends."
            )
        if not train_rows:
            raise VintageError(
                f"build at {as_of.isoformat()} has no training rows on arm {arm}: "
                f"nothing was originated in {train_quarters or 'the window'}"
            )

        test_pairs = tuple(
            (quarter, samples[quarter])
            for quarter in cohorts_between(period.of(as_of).shift(1), last_cohort)
            if quarter in samples
        )
        if not test_pairs:
            raise VintageError(
                f"build at {as_of.isoformat()} scores nothing: no cohort between "
                f"{period.of(as_of).shift(1)} and {last_cohort} carries eligible rows"
            )

        blind_rows = tuple(sorted(
            i
            for quarter, rows in grouped.items()
            for i in rows
            if horizon < origination[i] <= as_of
        ))

        keep = sorted(set(train_rows) | set(blind_rows)
                      | {i for _, rows in test_pairs for i in rows})
        sub_dates = [origination[i] for i in keep]
        sub_entities = (
            None if entity_ids is None else [entity_ids[i] for i in keep]
        )
        split = temporal_split(
            sub_dates,
            valid_from=horizon + dt.timedelta(days=1),
            oot_from=as_of + dt.timedelta(days=1),
            entity_ids=sub_entities,
        )
        train = tuple(keep[j] for j in split.train.indices)
        if set(train) != set(train_rows):
            raise VintageError(
                f"build at {as_of.isoformat()} disagrees with its own split: "
                f"{len(train_rows)} rows in the arm window against {len(train)} "
                f"before the label horizon"
            )

        # The blind gap restated as the thing it buys: the newest training
        # loan's performance window has to close before the oldest scored loan
        # is written. Given the two inequalities the split has already
        # enforced this cannot fail, so it is a consistency check on the month
        # arithmetic and the split's own bounds, not an independent gate. It
        # stays because it is the sentence a reviewer will ask to see.
        matures = add_months(split.train.last, axis_gap)
        if matures >= split.oot.first:
            raise LeakageError(
                f"the newest training loan of the build at {as_of.isoformat()} was "
                f"originated {split.train.last.isoformat()} and its "
                f"{axis_gap}-month window closes {matures.isoformat()}, on "
                f"or after the oldest scored loan of "
                f"{split.oot.first.isoformat()}: the builder is being credited "
                f"with outcomes nobody had seen"
            )

        if knowable is None and axis_gap_months is None:
            blind_note = (
                f"{len(blind_rows)} rows originated in "
                f"({knowable_through.isoformat()}, {as_of.isoformat()}] carry no mature "
                f"label at the as-of date and are neither trained on nor scored"
            )
            book_notes: tuple[str, ...] = ()
        else:
            blind_note = (
                f"{len(blind_rows)} rows of the quarters in ({horizon.isoformat()}, "
                f"{as_of.isoformat()}] are neither trained on nor scored"
            )
            book_notes = (
                (f"cohorts are {period.__name__} cohorts of the origination date; the "
                 f"pool is the whole quarters to {horizon.isoformat()}, {axis_gap} months "
                 f"before the build, and every training loan's {label_lag_months}-month "
                 f"window, read on its label clock, closed by "
                 f"{knowable_through.isoformat()}"),
            )
        build = VintageBuild(
            build_id=_build_id(as_of, arm),
            as_of=as_of,
            arm=arm,
            label_lag_months=label_lag_months,
            train=train,
            train_first=split.train.first,
            train_last=split.train.last,
            train_quarters=train_quarters,
            blind=blind_rows,
            test=test_pairs,
            notes=split.notes + (blind_note,) + book_notes,
            axis_gap_months=axis_gap_months,
        )
        assert_no_leakage(build, origination, label_lag_months=label_lag_months,
                          knowable=knowable, axis_gap_months=axis_gap_months)
        out.append(build)
    return out


def assert_no_leakage(
    build: VintageBuild,
    origination: Sequence[Date],
    *,
    label_lag_months: int = LABEL_LAG_MONTHS,
    knowable: Sequence[Date] | None = None,
    axis_gap_months: int | None = None,
) -> None:
    """The two inequalities, checked against the dates rather than the metadata.

    Called on every build the constructor emits, and callable on any build a
    runner has carried through a serialisation, a checkpoint or a resume. It
    reads the origination dates again instead of trusting the summary fields,
    because a build whose `train_last` says one thing and whose rows say another
    is the exact object this project has to be unable to score.

    On a book whose label clock is not the cohort date, pass it as `knowable`,
    and the gap on the cohort axis as `axis_gap_months` when it is not the
    label window; a build that carries its own gap is checked against it when
    none is passed. The pool is then checked on the cohort axis against the
    gap, every training loan's window on its own clock against the label
    window — the check that refuses a pool of whole quarters whose last
    quarter holds loans with a late first payment — and the scoring side on
    both dates, since a scored loan whose clock had started by the as-of date
    was on the books when the model was built, whatever cohort it is filed in.
    """
    if axis_gap_months is None:
        axis_gap_months = build.axis_gap_months
    horizon = add_months(build.as_of, -label_lag_months)
    axis_horizon = horizon if axis_gap_months is None else months_back(build.as_of,
                                                                       axis_gap_months)

    if not build.train:
        raise LeakageError(f"{build.build_id} has no training rows")

    # Checked before the two date inequalities, because on any build that
    # satisfies both of them a shared row would trip the horizon check first
    # and this one would never be the one that fires.
    scored = {i for _, rows in build.test for i in rows}
    overlap = scored & set(build.train)
    if overlap:
        raise LeakageError(
            f"{build.build_id} trains on and scores {len(overlap)} of the same "
            f"rows, for example {sorted(overlap)[:5]}"
        )

    latest_train = max(origination[i] for i in build.train)
    if latest_train > axis_horizon:
        which = "label horizon" if axis_gap_months is None else "cohort-axis horizon"
        raise LeakageError(
            f"{build.build_id} trains on a loan originated "
            f"{latest_train.isoformat()}, after the {which} "
            f"{axis_horizon.isoformat()} of an as-of date {build.as_of.isoformat()}: "
            f"its outcome was not knowable when the model was built"
        )

    if knowable is not None:
        still_open = [i for i in build.train if knowable[i] > horizon]
        if still_open:
            latest = max(knowable[i] for i in still_open)
            raise LeakageError(
                f"{build.build_id} trains on {len(still_open)} loans whose "
                f"{label_lag_months}-month label window opens after "
                f"{horizon.isoformat()}, the latest on {latest.isoformat()}: their "
                f"windows were still open at the as-of date {build.as_of.isoformat()} "
                f"and their outcomes were not knowable"
            )

    for quarter, rows in build.test:
        if not rows:
            raise LeakageError(f"{build.build_id} has an empty cohort {quarter}")
        earliest_test = min(origination[i] for i in rows)
        if earliest_test <= build.as_of:
            raise LeakageError(
                f"{build.build_id} scores {quarter}, which holds a loan originated "
                f"{earliest_test.isoformat()}, on or before the as-of date "
                f"{build.as_of.isoformat()}: that cohort was already written when "
                f"the model was built and is not out of time"
            )
        if knowable is not None:
            earliest_clock = min(knowable[i] for i in rows)
            if earliest_clock <= build.as_of:
                raise LeakageError(
                    f"{build.build_id} scores {quarter}, which holds a loan whose label "
                    f"window opens {earliest_clock.isoformat()}, on or before the as-of "
                    f"date {build.as_of.isoformat()}: that loan was on the books when "
                    f"the model was built and is not out of time"
                )
