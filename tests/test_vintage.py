"""The vintage builder, tested by building the situations it must refuse.

The checks that matter here are the two inequalities of the blind gap, and an
assertion that has never fired is an assertion nobody has checked. So the leak
is constructed rather than described: a build assembled under a six-month label
is handed to the twelve-month assertion, and a build is stitched by hand with a
training row on the wrong side of its own horizon.

The second family of tests is about the sample. A trajectory is only readable
if a step between two cohorts is the model moving; if the scored rows differ
between builds, every step is partly the draw, and no amount of care later
recovers the difference.
"""

from __future__ import annotations

import datetime as dt

import pytest

from outoftime.label import LabelDefinition, add_months, build_labels
from outoftime.splits import LeakageError
from outoftime.vintage import (
    DEFAULT_AS_OF,
    FIRST_COHORT,
    ROLLING_QUARTERS,
    Quarter,
    VintageBuild,
    VintageError,
    assert_no_leakage,
    builds,
    cohorts,
    quarters_between,
    scoring_samples,
)

PER_MONTH = 7


def monthly_book(
    first: dt.date = dt.date(2009, 1, 1),
    last: dt.date = dt.date(2018, 12, 1),
    per_month: int = PER_MONTH,
) -> list[dt.date]:
    """A book that originates the same number of loans every month.

    Flat on purpose. A test that has to reason about both the calendar and an
    uneven volume profile stops testing the calendar.
    """
    dates: list[dt.date] = []
    month = first
    while month <= last:
        dates.extend([month] * per_month)
        month = add_months(month, 1)
    return dates


def small_grid(book: list[dt.date], **kwargs):
    return builds(book, rows_per_quarter=5, **kwargs)


# --- the calendar ---------------------------------------------------------


def test_quarter_arithmetic_crosses_years():
    assert Quarter.of(dt.date(2013, 6, 30)) == Quarter(2013, 2)
    assert Quarter(2013, 4).shift(1) == Quarter(2014, 1)
    assert Quarter(2013, 1).shift(-1) == Quarter(2012, 4)
    assert Quarter(2013, 4).end == dt.date(2013, 12, 31)
    assert Quarter(2016, 1).end == dt.date(2016, 3, 31)  # leap year
    assert len(quarters_between(Quarter(2010, 3), Quarter(2012, 2))) == 8


def test_quarters_sort_chronologically():
    unsorted = [Quarter(2014, 1), Quarter(2013, 4), Quarter(2013, 2)]
    assert sorted(unsorted) == [Quarter(2013, 2), Quarter(2013, 4), Quarter(2014, 1)]


# --- the grid -------------------------------------------------------------


def test_the_grid_is_nine_half_yearly_builds():
    grid = small_grid(monthly_book())
    assert len(grid) == len(DEFAULT_AS_OF) == 9
    assert [b.build_id for b in grid][:3] == ["2013H1-E", "2013H2-E", "2014H1-E"]
    assert grid[-1].build_id == "2017H1-E"
    assert [b.as_of for b in grid] == list(DEFAULT_AS_OF)


def test_training_stops_at_the_label_horizon():
    book = monthly_book()
    for build in small_grid(book):
        horizon = add_months(build.as_of, -12)
        assert max(book[i] for i in build.train) <= horizon
        assert build.train_last <= horizon


def test_scoring_starts_after_the_as_of_date():
    book = monthly_book()
    for build in small_grid(book):
        for _, rows in build.test:
            assert min(book[i] for i in rows) > build.as_of


def test_the_blind_gap_is_neither_trained_on_nor_scored():
    book = monthly_book()
    for build in small_grid(book):
        horizon = add_months(build.as_of, -12)
        expected = {
            i for i, date in enumerate(book)
            if horizon < date <= build.as_of and Quarter.of(date) >= FIRST_COHORT
        }
        assert set(build.blind) == expected
        assert build.blind, "a book with monthly originations has rows in the gap"
        assert not set(build.blind) & set(build.train)
        assert not set(build.blind) & {i for _, rows in build.test for i in rows}


def test_an_as_of_date_off_a_quarter_end_is_refused():
    # A horizon inside a quarter would leave the rolling arm spanning seven
    # quarters and a stub, and the two arms would stop being comparable.
    with pytest.raises(VintageError, match="last day"):
        small_grid(monthly_book(), as_of_dates=[dt.date(2013, 5, 31)])


def test_an_unknown_arm_is_refused():
    with pytest.raises(VintageError, match="neither"):
        small_grid(monthly_book(), arm="rolling")


# --- the two arms ---------------------------------------------------------


def test_the_rolling_arm_spans_exactly_its_stated_width():
    book = monthly_book()
    for build in small_grid(book, arm="R"):
        assert len(build.train_quarters) == ROLLING_QUARTERS
        spanned = {Quarter.of(book[i]) for i in build.train}
        assert spanned == set(build.train_quarters)
        assert build.train_quarters[-1] == Quarter.of(add_months(build.as_of, -12))


def test_the_expanding_arm_starts_at_the_first_cohort_and_only_grows():
    book = monthly_book()
    sizes = []
    for build in small_grid(book, arm="E"):
        assert build.train_quarters[0] == FIRST_COHORT
        assert build.train_first == FIRST_COHORT.start
        sizes.append(len(build.train))
    assert sizes == sorted(sizes)
    assert sizes[0] < sizes[-1]


def test_the_arms_differ_only_in_how_far_back_they_reach():
    book = monthly_book()
    expanding = {b.build_id[:-2]: b for b in small_grid(book, arm="E")}
    rolling = {b.build_id[:-2]: b for b in small_grid(book, arm="R")}
    for key, rolled in rolling.items():
        grown = expanding[key]
        assert set(rolled.train) < set(grown.train)
        assert rolled.train_last == grown.train_last
        assert rolled.test == grown.test


# --- the shared scoring sample -------------------------------------------


def test_a_quarter_is_scored_on_the_same_rows_in_every_build_and_arm():
    book = monthly_book()
    seen: dict[Quarter, tuple[int, ...]] = {}
    for arm in ("E", "R"):
        for build in small_grid(book, arm=arm):
            for quarter, rows in build.test:
                if quarter in seen:
                    assert rows == seen[quarter], f"{quarter} moved in {build.build_id}"
                seen[quarter] = rows
    assert len(seen) > 1


def test_a_sample_does_not_depend_on_which_quarters_were_asked_for():
    book = monthly_book()
    wide = scoring_samples(book, rows_per_quarter=5)
    narrow = scoring_samples(
        book, rows_per_quarter=5, first=Quarter(2014, 1), last=Quarter(2015, 4)
    )
    for quarter, rows in narrow.items():
        assert rows == wide[quarter]


def test_a_sample_is_a_sample_and_a_short_quarter_is_used_whole():
    book = monthly_book()
    drawn = scoring_samples(book, rows_per_quarter=5)
    every = cohorts(book)
    for quarter, rows in drawn.items():
        assert set(rows) <= set(every[quarter])
        assert len(rows) == min(5, len(every[quarter]))
    assert any(len(rows) == 5 for rows in drawn.values())


def test_a_different_seed_draws_different_rows():
    book = monthly_book()
    one = scoring_samples(book, rows_per_quarter=5, seed=1)
    two = scoring_samples(book, rows_per_quarter=5, seed=2)
    assert any(one[q] != two[q] for q in one)


# --- the context sample ---------------------------------------------------


def test_the_context_sample_is_deterministic_by_seed_and_build():
    book = monthly_book()
    grid = small_grid(book)
    first, second = grid[0], grid[1]
    assert first.context(seed=3, size=40) == first.context(seed=3, size=40)
    assert first.context(seed=3, size=40) != first.context(seed=4, size=40)
    assert first.context(seed=3, size=40) != second.context(seed=3, size=40)
    assert set(first.context(seed=3, size=40)) <= set(first.train)
    assert len(first.context(seed=3, size=40)) == 40


def test_a_pool_below_the_cap_is_taken_whole():
    build = small_grid(monthly_book())[0]
    assert build.context(seed=3, size=10**9) == build.train


# --- the leak, constructed ------------------------------------------------


def test_a_build_made_for_a_shorter_label_is_refused_by_the_longer_one():
    # The mistake in full: a six-month blind gap under a twelve-month label.
    # The build is internally consistent and the leak is invisible in it; only
    # the assertion, told what the label actually is, can see it.
    book = monthly_book()
    # Year ends only: a six-month horizon off a June date lands on the 30th of
    # December, which is not a quarter end, and the builder refuses it there.
    year_ends = [dt.date(2013, 12, 31), dt.date(2014, 12, 31), dt.date(2015, 12, 31)]
    grid = small_grid(book, as_of_dates=year_ends, label_lag_months=6)
    assert len(grid) == 3
    for build in grid:
        assert_no_leakage(build, book, label_lag_months=6)
        with pytest.raises(LeakageError, match="not knowable"):
            assert_no_leakage(build, book, label_lag_months=12)


def test_a_training_row_past_the_horizon_is_refused():
    book = monthly_book()
    clean = small_grid(book)[0]
    intruder = clean.blind[-1]  # the newest loan the builder could not see
    leaked = VintageBuild(
        build_id=clean.build_id,
        as_of=clean.as_of,
        arm=clean.arm,
        label_lag_months=clean.label_lag_months,
        train=clean.train + (intruder,),
        train_first=clean.train_first,
        train_last=clean.train_last,  # stale, and deliberately so
        train_quarters=clean.train_quarters,
        blind=clean.blind,
        test=clean.test,
    )
    with pytest.raises(LeakageError, match="after the label horizon"):
        assert_no_leakage(leaked, book)


def test_a_cohort_written_before_the_as_of_date_is_not_out_of_time():
    book = monthly_book()
    clean = small_grid(book)[0]
    early = Quarter.of(clean.as_of)
    smuggled = VintageBuild(
        build_id=clean.build_id,
        as_of=clean.as_of,
        arm=clean.arm,
        label_lag_months=clean.label_lag_months,
        train=clean.train,
        train_first=clean.train_first,
        train_last=clean.train_last,
        train_quarters=clean.train_quarters,
        blind=clean.blind,
        test=((early, clean.blind[:5]),) + clean.test,
    )
    with pytest.raises(LeakageError, match="not out of time"):
        assert_no_leakage(smuggled, book)


def test_a_row_that_is_both_trained_on_and_scored_is_refused():
    book = monthly_book()
    clean = small_grid(book)[0]
    quarter, rows = clean.test[0]
    doubled = VintageBuild(
        build_id=clean.build_id,
        as_of=clean.as_of,
        arm=clean.arm,
        label_lag_months=clean.label_lag_months,
        train=clean.train + rows[:1],
        train_first=clean.train_first,
        train_last=clean.train_last,
        train_quarters=clean.train_quarters,
        blind=clean.blind,
        test=clean.test,
    )
    with pytest.raises(LeakageError, match="trains on and scores"):
        assert_no_leakage(doubled, book)
    assert quarter in clean.test_cohorts


# --- the maturity gate reaches the cohorts -------------------------------


def test_immature_loans_cannot_enter_a_cohort():
    """The gate of `label.build_labels`, carried through to the builds.

    The failure this prevents is the one that manufactures the study's own
    headline: label the newest cohorts non-default because their window has not
    closed, and every model appears to lose calibration as it ages.
    """
    book = monthly_book()
    labels = build_labels(
        origination=book,
        status=["Fully Paid"] * len(book),
        last_payment=[None] * len(book),
        definition=LabelDefinition(window_months=12, snapshot=dt.date(2019, 3, 1)),
    )
    assert labels.dropped_immature

    grouped = cohorts(book, eligible=labels.indices)
    latest = max(book[i] for rows in grouped.values() for i in rows)
    assert latest <= labels.definition.last_labelable_origination
    for dropped in labels.dropped_immature:
        assert not any(dropped in rows for rows in grouped.values())


def test_a_grid_cut_for_a_wider_window_than_its_labels_is_refused():
    """A twenty-four-month lag over twelve-month labels is a year of immature
    loans scored as non-defaults, and nothing downstream could tell."""
    book = monthly_book()
    twelve = build_labels(
        origination=book,
        status=["Fully Paid"] * len(book),
        last_payment=[None] * len(book),
        definition=LabelDefinition(window_months=12, snapshot=dt.date(2019, 3, 1)),
    )
    with pytest.raises(VintageError, match="24-month lag"):
        builds(book, labels=twelve, label_lag_months=24)
    with pytest.raises(VintageError, match="not both"):
        builds(book, labels=twelve, eligible=twelve.indices)

    # The same labels under the lag they were built for are accepted, and they
    # select exactly the rows `eligible` would have.
    by_labels = builds(book, labels=twelve)
    by_eligible = builds(book, eligible=twelve.indices)
    assert [b.train for b in by_labels] == [b.train for b in by_eligible]
    assert [b.test for b in by_labels] == [b.test for b in by_eligible]


def test_a_book_with_nothing_left_to_score_is_refused():
    book = monthly_book(last=dt.date(2013, 12, 1))
    with pytest.raises(VintageError, match="scores nothing"):
        small_grid(book, as_of_dates=[dt.date(2014, 6, 30)])


def test_the_summary_names_every_cohort_it_scores():
    build = small_grid(monthly_book())[0]
    text = build.summary()
    for quarter in build.test_cohorts:
        assert f"| {quarter} |" in text
    assert build.as_dict()["test_rows"] == build.n_test
