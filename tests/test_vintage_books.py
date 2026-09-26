"""The vintage builder on its two books, and the proof that the first did not move.

The Lending Club grid is the recorded one, and nothing written for the second
book may change a single position it emits. The first test builds both arms of
the nine-build grid on a synthetic book that exercises every path — uneven
volume, a quarter too thin to sample, immature and still-running loans, contexts
smaller and larger than the pool — and compares a digest of every position,
every note and every summary against the digest the code produced at commit
f25e3db, before the second book existed.

The rest build the Freddie Mac situation and the mistakes it invites. Its
cohorts are half-years of the origination quarter and its label clock is the
first payment date, which can fall months after the quarter closes, so a pool
of whole quarters cut at the label window holds loans whose windows are still
open. The tests construct that pool and the other leaks, and each has to be
refused.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import random

import pytest

from outoftime.label import LabelDefinition, add_months, build_labels
from outoftime.splits import LeakageError
from outoftime.vintage import (
    FIRST_COHORT,
    FM_AXIS_GAP_MONTHS,
    FM_FIRST_COHORT,
    FM_LABEL_LAG_MONTHS,
    FM_LAST_TEST_COHORT,
    FM_MAX_CLOCK_LAG_MONTHS,
    FM_ROLLING_QUARTERS,
    FREDDIE_MAC,
    LABEL_LAG_MONTHS,
    LAST_TEST_COHORT,
    LENDING_CLUB,
    ROLLING_QUARTERS,
    TEST_ROWS_PER_QUARTER,
    HalfYear,
    Quarter,
    VintageBuild,
    VintageError,
    assert_no_leakage,
    builds,
    cohorts_between,
    months_back,
    parse_cohort,
    required_axis_gap,
    scoring_samples,
)

# The digest of `lending_club_digest()` at f25e3db, the last commit before the
# vintage module learned a second book.
LENDING_CLUB_DIGEST = "f2a78b8e3d356c966551fa0c6ecbd88d3c5cf442de2482aa9492f80fdf25e7df"


def lending_club_book():
    rng = random.Random("lc-golden-book")
    dates, status, last = [], [], []
    month = dt.date(2009, 1, 1)
    while month <= dt.date(2019, 3, 1):
        n = 3 + (month.year - 2009) * 4 + rng.randrange(5)
        if month.year == 2014 and month.month in (4, 5, 6):
            n = 2
        for _ in range(n):
            dates.append(month.replace(day=rng.randrange(1, 28)))
            r = rng.random()
            if r < 0.15:
                status.append("Charged Off")
                last.append(None if rng.random() < 0.2 else add_months(month, rng.randrange(0, 30)))
            elif r < 0.8:
                status.append("Fully Paid")
                last.append(add_months(month, rng.randrange(1, 36)))
            else:
                status.append("Current")
                last.append(add_months(month, rng.randrange(1, 60)))
        month = add_months(month, 1)
    return dates, status, last


def lending_club_digest() -> tuple[int, str]:
    dates, status, last = lending_club_book()
    labels = build_labels(origination=dates, status=status, last_payment=last,
                          definition=LabelDefinition(window_months=12,
                                                     snapshot=dt.date(2019, 3, 1)))
    digest = hashlib.sha256()
    for arm in ("E", "R"):
        for b in builds(dates, arm=arm, labels=labels, rows_per_quarter=60,
                        entity_ids=list(range(len(dates)))):
            digest.update(repr((b.build_id, b.train, b.blind, b.test, b.train_quarters,
                                b.train_first, b.train_last, b.notes, b.as_dict())).encode())
            for seed in (20260911, 20260912, 20260913):
                digest.update(repr(b.context(seed=seed, size=150)).encode())
            digest.update(repr(b.context(seed=1)).encode())
    return len(dates), digest.hexdigest()


def test_the_lending_club_grid_is_the_one_recorded_before_the_second_book():
    assert lending_club_digest() == (2834, LENDING_CLUB_DIGEST)


def test_the_book_parameters():
    assert LENDING_CLUB.label_lag_months == LENDING_CLUB.axis_gap_months == LABEL_LAG_MONTHS
    assert LENDING_CLUB.first_cohort == FIRST_COHORT
    assert LENDING_CLUB.last_test_cohort == LAST_TEST_COHORT
    assert LENDING_CLUB.rows_per_cohort == TEST_ROWS_PER_QUARTER
    assert LENDING_CLUB.rolling_quarters == ROLLING_QUARTERS == 4
    assert LENDING_CLUB.resolution is Quarter
    assert FREDDIE_MAC.label_lag_months == FM_LABEL_LAG_MONTHS == 24
    assert FREDDIE_MAC.axis_gap_months == FM_AXIS_GAP_MONTHS == 27
    assert LENDING_CLUB.max_clock_lag_months == 0
    assert FREDDIE_MAC.max_clock_lag_months == FM_MAX_CLOCK_LAG_MONTHS == 5
    assert required_axis_gap(24, 5) == 27 and required_axis_gap(12, 0) == 12
    assert FREDDIE_MAC.rolling_quarters == FM_ROLLING_QUARTERS == 8
    assert (str(FM_FIRST_COHORT), str(FM_LAST_TEST_COHORT)) == ("1999H1", "2023H2")
    assert FREDDIE_MAC.rows_per_cohort is None
    assert FREDDIE_MAC.resolution is HalfYear
    assert FREDDIE_MAC.as_dict()["label_clock"] == "first_payment_date"


# --- half-years ----------------------------------------------------------


def test_half_year_arithmetic_crosses_years_and_names_sort():
    assert HalfYear.of(dt.date(2008, 6, 30)) == HalfYear(2008, 1)
    assert HalfYear.of(dt.date(2008, 7, 1)) == HalfYear(2008, 2)
    assert HalfYear(2008, 2).shift(1) == HalfYear(2009, 1)
    assert HalfYear(2009, 1).shift(-3) == HalfYear(2007, 2)
    assert HalfYear(2008, 1).end == dt.date(2008, 6, 30)
    assert HalfYear(2008, 2).end == dt.date(2008, 12, 31)
    span = cohorts_between(HalfYear(2007, 2), HalfYear(2010, 1))
    assert [str(h) for h in span] == ["2007H2", "2008H1", "2008H2", "2009H1", "2009H2", "2010H1"]
    assert sorted(str(h) for h in reversed(span)) == [str(h) for h in span]
    with pytest.raises(VintageError):
        HalfYear(2008, 3)


def test_cohort_names_parse_to_their_resolution_and_nothing_else_does():
    assert parse_cohort("2010Q2") == Quarter(2010, 2)
    assert parse_cohort("2005H1") == HalfYear(2005, 1)
    for bad in ("2005H3", "2005-1", "05H1", "2010Q5"):
        with pytest.raises(VintageError):
            parse_cohort(bad)
    with pytest.raises(VintageError, match="resolutions"):
        cohorts_between(Quarter(2010, 1), HalfYear(2011, 1))


def test_a_gap_counted_from_a_month_end_lands_on_a_month_end():
    assert months_back(dt.date(2012, 12, 31), 27) == dt.date(2010, 9, 30)
    assert months_back(dt.date(2012, 6, 30), 27) == dt.date(2010, 3, 31)
    assert months_back(dt.date(2012, 6, 15), 27) == dt.date(2010, 3, 15)


# --- the Freddie Mac grid -------------------------------------------------


def fm_book(per_month: int = 3):
    """Loans every month from 1999 to 2025, first payment one to three months on.

    `origination` is the first day of the loan's quarter, as the identifier
    gives it; `clock` is the first payment month, up to five months after
    the quarter opens.
    """
    origination, clock = [], []
    month = dt.date(1999, 1, 1)
    while month <= dt.date(2025, 12, 1):
        opened = dt.date(month.year, (month.month - 1) // 3 * 3 + 1, 1)
        for k in range(per_month):
            origination.append(opened)
            clock.append(add_months(month, 1 + k % 3))
        month = add_months(month, 1)
    return origination, clock


def fm_grid(origination, clock, **kwargs):
    options = {"as_of_dates": (dt.date(2012, 12, 31),), "label_lag_months": 24,
               "axis_gap_months": 27, "first_cohort": FM_FIRST_COHORT,
               "last_cohort": FM_LAST_TEST_COHORT, "rows_per_quarter": None,
               "knowable": clock}
    options.update(kwargs)
    return builds(origination, **options)


def test_the_pool_is_whole_quarters_and_every_training_window_had_closed():
    origination, clock = fm_book()
    (build,) = fm_grid(origination, clock)
    assert build.build_id == "2012H2-E"
    assert build.train_quarters[0] == Quarter(1999, 1)
    assert build.train_quarters[-1] == Quarter(2010, 3)
    assert set(build.train) == {i for i, o in enumerate(origination)
                                if Quarter(1999, 1) <= Quarter.of(o) <= Quarter(2010, 3)}
    assert max(clock[i] for i in build.train) <= dt.date(2010, 12, 31)
    assert set(build.blind) == {i for i, o in enumerate(origination)
                                if dt.date(2010, 9, 30) < o <= build.as_of}
    summary = build.as_dict()
    assert summary["axis_gap_months"] == 27 and summary["axis_horizon"] == "2010-09-30"
    assert summary["knowable_through"] == "2010-12-31"
    assert any("whole quarters" in note for note in build.notes)


def test_a_pool_cut_at_the_label_window_on_the_quarter_axis_is_refused():
    # The last admitted quarter is 2010Q4 and its loans pay first in 2011: on
    # the quarter axis the gap is twenty-four months, on their own clocks it
    # is less, and only the check on the clock can see it.
    origination, clock = fm_book()
    with pytest.raises(LeakageError, match="label window opens"):
        fm_grid(origination, clock, axis_gap_months=24)
    with pytest.raises(VintageError, match="gap on the cohort axis"):
        fm_grid(origination, clock, axis_gap_months=12)


def test_the_gap_is_checked_against_the_window_and_the_clock_lag_before_any_row():
    origination, clock = fm_book()
    (build,) = fm_grid(origination, clock, max_clock_lag_months=FM_MAX_CLOCK_LAG_MONTHS)
    assert build.train_quarters[-1] == Quarter(2010, 3)
    with pytest.raises(VintageError, match="need a gap of 27"):
        fm_grid(origination, clock, axis_gap_months=24,
                max_clock_lag_months=FM_MAX_CLOCK_LAG_MONTHS)
    # A book whose clocks start later than the lag it declares is refused.
    with pytest.raises(VintageError, match="more than 2 months"):
        fm_grid(origination, clock, max_clock_lag_months=2)


def test_every_half_year_after_the_build_is_scored_whole():
    origination, clock = fm_book()
    (build,) = fm_grid(origination, clock)
    assert build.test_cohorts == cohorts_between(HalfYear(2013, 1), HalfYear(2023, 2))
    for cohort, rows in build.test:
        assert set(rows) == {i for i, o in enumerate(origination) if HalfYear.of(o) == cohort}
    assert list(build.as_dict()["test_cohorts"])[:2] == ["2013H1", "2013H2"]
    whole = scoring_samples(origination, rows_per_quarter=None, first=FM_FIRST_COHORT,
                            last=FM_LAST_TEST_COHORT)
    assert sum(len(r) for r in whole.values()) == sum(
        1 for o in origination if FM_FIRST_COHORT <= HalfYear.of(o) <= FM_LAST_TEST_COHORT)


def test_the_rolling_arm_spans_its_quarters_on_the_cohort_axis():
    origination, clock = fm_book()
    (build,) = fm_grid(origination, clock, arm="R", rolling_quarters=FM_ROLLING_QUARTERS)
    assert len(build.train_quarters) == FM_ROLLING_QUARTERS
    assert build.train_quarters[-1] == Quarter(2010, 3)
    assert {Quarter.of(origination[i]) for i in build.train} == set(build.train_quarters)


def test_an_as_of_date_inside_a_half_year_is_refused():
    origination, clock = fm_book()
    with pytest.raises(VintageError, match="last day of its cohort"):
        fm_grid(origination, clock, as_of_dates=(dt.date(2012, 9, 30),))
    (build,) = fm_grid(origination, clock, as_of_dates=(dt.date(2012, 6, 30),))
    assert build.test_cohorts[0] == HalfYear(2012, 2)
    assert build.train_quarters[-1] == Quarter(2010, 1)


def test_a_scored_loan_already_on_the_books_is_refused():
    origination, clock = fm_book()
    (build,) = fm_grid(origination, clock)
    _, rows = build.test[0]
    early = list(clock)
    early[rows[0]] = build.as_of - dt.timedelta(days=30)
    with pytest.raises(LeakageError, match="on the books"):
        assert_no_leakage(build, origination, label_lag_months=24, knowable=early)
    # The same build read on the cohort date alone cannot see it.
    assert_no_leakage(build, origination, label_lag_months=24)


def test_a_training_loan_whose_window_had_not_closed_is_refused():
    origination, clock = fm_book()
    (build,) = fm_grid(origination, clock)
    late = list(clock)
    late[build.train[-1]] = dt.date(2011, 3, 1)
    with pytest.raises(LeakageError, match="label window opens"):
        assert_no_leakage(build, origination, label_lag_months=24, knowable=late)
    intruder = build.blind[-1]
    leaked = VintageBuild(
        build_id=build.build_id, as_of=build.as_of, arm=build.arm,
        label_lag_months=build.label_lag_months, train=build.train + (intruder,),
        train_first=build.train_first, train_last=build.train_last,
        train_quarters=build.train_quarters, blind=build.blind, test=build.test,
        axis_gap_months=build.axis_gap_months,
    )
    with pytest.raises(LeakageError, match="cohort-axis horizon"):
        assert_no_leakage(leaked, origination, label_lag_months=24, knowable=clock)


def test_a_grid_cut_for_a_shorter_label_is_refused_under_the_longer_one():
    origination, clock = fm_book()
    (build,) = fm_grid(origination, clock, label_lag_months=12, axis_gap_months=15)
    assert_no_leakage(build, origination, label_lag_months=12, knowable=clock)
    with pytest.raises(LeakageError, match="not knowable"):
        assert_no_leakage(build, origination, label_lag_months=24, knowable=clock,
                          axis_gap_months=27)


def test_a_clock_of_another_length_is_refused():
    origination, clock = fm_book()
    with pytest.raises(VintageError, match="label-clock"):
        fm_grid(origination, clock[:-1])
