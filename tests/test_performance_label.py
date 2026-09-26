"""The maturity gate on a servicing history, built around the same trap twice.

A loan whose history ends before the window closes, with no termination and no
default, has an unknown label. Labelling it non-default lowers the measured
rate in exactly the youngest cohorts, and a model scored across them then drifts
out of calibration whatever it is. The first test builds a book of such loans
and asserts they are dropped rather than counted as good news.

The second trap runs the other way. A loan resolved early — defaulted at month
three, paid off at month five — has a known outcome even when its window has
not closed by the cutoff. Label those and drop the rest, and the youngest
cohort's rate is computed over its early defaults and early payoffs alone,
which overstates it. The second test builds that cohort and asserts that the
resolved loans are dropped with the rest.
"""

from __future__ import annotations

import datetime as dt

import pytest

from outoftime.performance_label import (
    BAD_TERMINATIONS,
    CENSORING,
    PREPAID,
    LabelError,
    LoanHistory,
    PerformanceLabelDefinition,
    build_performance_labels,
    months_observable,
)

CUTOFF = dt.date(2026, 3, 1)
OLD = dt.date(2020, 1, 1)


def h(last_age: int, **over) -> LoanHistory:
    """A history old enough for any window, unless a first payment is given."""
    return LoanHistory(**{"first_payment": OLD, "last_age": last_age, **over})


def definition(**over) -> PerformanceLabelDefinition:
    return PerformanceLabelDefinition(
        **{"window_months": 12, "performance_cutoff": CUTOFF, **over})


def test_immature_loans_are_dropped_not_labelled_good():
    young = [h(5) for _ in range(20)]
    old = [h(30), h(30, first_bad_age=4)]
    labels = build_performance_labels(young + old, definition())
    assert labels.size == 2
    assert labels.labels == (0, 1)
    assert len(labels.dropped_immature) == 20
    assert labels.default_rate == 0.5


def test_a_cohort_inside_the_last_window_is_dropped_whole_even_where_resolved():
    """The early-resolver trap: an unclosed window admits only the loans that
    finished early, and their rate is not the cohort's."""
    recent = dt.date(2025, 10, 1)  # six months observable by the cutoff
    cohort = [
        h(3, first_payment=recent, first_bad_age=3),                            # defaulted early
        h(5, first_payment=recent, termination_code=1, termination_age=5),      # paid off early
        h(6, first_payment=recent),                                             # still running
        h(30),                                                                  # an old control
    ]
    labels = build_performance_labels(cohort, definition())
    assert labels.indices == (3,)
    assert labels.dropped_immature == (0, 1, 2)
    assert any("whatever their record says" in note for note in labels.notes)


def test_the_window_closes_in_the_cutoff_month_inclusive():
    assert months_observable(dt.date(2025, 4, 1), CUTOFF) == 12
    assert months_observable(dt.date(2025, 5, 1), CUTOFF) == 11
    assert months_observable(CUTOFF, CUTOFF) == 1
    closes = [h(12, first_payment=dt.date(2025, 4, 1)), h(12, first_payment=dt.date(2025, 5, 1))]
    labels = build_performance_labels(closes, definition())
    assert labels.indices == (0,)


def test_a_default_inside_the_window_is_a_default_and_outside_is_not():
    histories = [h(30, first_bad_age=12), h(30, first_bad_age=13)]
    twelve = build_performance_labels(histories, definition(window_months=12))
    twenty_four = build_performance_labels(histories, definition(window_months=24))
    assert twelve.labels == (1, 0)
    assert twenty_four.labels == (1, 1)


def test_a_payoff_inside_the_window_is_a_resolved_good_loan():
    prepaid = h(5, termination_code=1, termination_age=5)
    labels = build_performance_labels([prepaid], definition())
    assert labels.labels == (0,)
    assert labels.dropped_immature == ()


def test_delinquent_then_prepaid_is_a_default_not_a_payoff():
    history = h(9, first_bad_age=6, termination_code=1, termination_age=9)
    labels = build_performance_labels([history], definition())
    assert labels.labels == (1,)


def test_a_bad_termination_with_no_delinquency_on_record_is_dated_at_the_termination():
    reo = h(10, termination_code=9, termination_age=10)
    labels = build_performance_labels([reo], definition())
    assert labels.labels == (1,)
    assert any("no ninety-day delinquency on record" in note for note in labels.notes)


def test_a_bad_termination_after_the_window_on_a_clean_window_is_not_a_default():
    late = h(20, first_bad_age=15, termination_code=3, termination_age=20)
    labels = build_performance_labels([late], definition())
    assert labels.labels == (0,)


def test_a_sale_inside_the_window_is_censored_not_labelled():
    sold = h(4, termination_code=15, termination_age=4)
    reperforming = h(4, termination_code=16, termination_age=4)
    defect = h(4, termination_code=96, termination_age=4)
    control = h(12)
    labels = build_performance_labels([sold, reperforming, defect, control], definition())
    assert labels.indices == (3,)
    assert labels.censored == (0, 1, 2)


def test_a_history_that_reaches_the_window_end_is_labelled_whatever_happens_after():
    labels = build_performance_labels([h(12)], definition())
    assert labels.labels == (0,)


def test_inconsistent_ages_are_refused_not_guessed():
    broken = h(3, termination_code=9, termination_age=20)
    with pytest.raises(LabelError):
        build_performance_labels([broken], definition())


def test_empty_and_unresolvable_books_are_refused():
    with pytest.raises(LabelError):
        build_performance_labels([], definition())
    with pytest.raises(LabelError):
        build_performance_labels([h(3)], definition())


def test_the_definition_refuses_nonsense():
    with pytest.raises(LabelError):
        definition(window_months=0)
    with pytest.raises(LabelError):
        definition(prepaid=frozenset({1, 2}))
    with pytest.raises(LabelError):
        h(5, termination_code=1)


def test_the_code_groups_are_disjoint_and_complete():
    assert not (PREPAID & BAD_TERMINATIONS)
    assert not (PREPAID & CENSORING)
    assert not (BAD_TERMINATIONS & CENSORING)
    assert PREPAID | BAD_TERMINATIONS | CENSORING == {1, 2, 3, 9, 15, 16, 96}


def test_the_manifest_record_carries_the_counts():
    histories = [
        h(12, first_bad_age=2),
        h(12),
        h(2),
        h(2, termination_code=15, termination_age=2),
        h(2, first_payment=dt.date(2026, 2, 1), first_bad_age=2),
    ]
    record = build_performance_labels(histories, definition()).as_dict()
    assert record["labelled"] == 2
    assert record["defaults"] == 1
    assert record["dropped_immature"] == 2
    assert record["censored"] == 1
    assert record["definition"]["window_months"] == 12
