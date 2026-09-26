"""Left truncation: a loan whose servicing record begins inside its own window.

The parameter defaults to off, and off has to mean the label this module
always built, to the last key of its summary. On, a loan first observed after
the stated age is dropped and counted, never labelled; and a history that does
not say when it was first observed is refused rather than guessed at.
"""

from __future__ import annotations

import datetime as dt

import pytest

from outoftime.performance_label import (
    MAX_FIRST_OBSERVED_AGE,
    LabelError,
    LoanHistory,
    PerformanceLabelDefinition,
    build_performance_labels,
)

CUTOFF = dt.date(2026, 3, 1)
OLD = dt.date(2015, 1, 1)


def histories(with_ages: bool = True) -> list[LoanHistory]:
    def seen(age):
        return age if with_ages else None

    return [
        LoanHistory(OLD, last_age=100, first_observed_age=seen(1)),
        LoanHistory(OLD, last_age=100, first_bad_age=5, first_observed_age=seen(1)),
        LoanHistory(OLD, last_age=100, first_observed_age=seen(13)),
        LoanHistory(OLD, last_age=100, first_bad_age=20, first_observed_age=seen(12)),
        LoanHistory(dt.date(2025, 6, 1), last_age=9, first_observed_age=seen(8)),
    ]


def test_off_is_the_label_as_it_was():
    definition = PerformanceLabelDefinition(window_months=24, performance_cutoff=CUTOFF)
    with_ages = build_performance_labels(histories(True), definition)
    without = build_performance_labels(histories(False), definition)
    assert with_ages.indices == without.indices == (0, 1, 2, 3)
    assert with_ages.labels == without.labels == (0, 1, 0, 1)
    assert "left_truncated" not in with_ages.as_dict()
    assert "max_first_observed_age" not in definition.as_dict()
    assert with_ages.as_dict() == without.as_dict()


def test_a_loan_first_observed_too_late_is_dropped_and_counted():
    definition = PerformanceLabelDefinition(window_months=24, performance_cutoff=CUTOFF,
                                            max_first_observed_age=12)
    labels = build_performance_labels(histories(), definition)
    assert labels.indices == (0, 1, 3)
    assert labels.left_truncated == (2,)
    # The immature loan is counted as immature, not as truncated.
    assert labels.dropped_immature == (4,)
    summary = labels.as_dict()
    assert summary["left_truncated"] == 1
    assert summary["definition"]["max_first_observed_age"] == 12
    assert any("left-truncated" in note for note in summary["notes"])


def test_a_record_with_a_gap_is_dropped_and_counted_apart():
    gapped = [
        LoanHistory(OLD, last_age=100, first_observed_age=1),
        LoanHistory(OLD, last_age=100, first_observed_age=1, record_gap=True),
        LoanHistory(OLD, last_age=100, first_observed_age=9, record_gap=True),
    ]
    off = PerformanceLabelDefinition(window_months=24, performance_cutoff=CUTOFF)
    assert build_performance_labels(gapped, off).indices == (0, 1, 2)
    on = PerformanceLabelDefinition(window_months=24, performance_cutoff=CUTOFF,
                                    max_first_observed_age=MAX_FIRST_OBSERVED_AGE,
                                    exclude_record_gaps=True)
    labels = build_performance_labels(gapped, on)
    assert labels.indices == (0,)
    # Late first and gapped: counted once, as late.
    assert labels.left_truncated == (2,) and labels.record_gaps == (1,)
    summary = labels.as_dict()
    assert summary["record_gaps"] == 1 and summary["left_truncated"] == 1
    assert summary["definition"]["exclude_record_gaps"] is True
    assert MAX_FIRST_OBSERVED_AGE == 3


def test_a_history_that_does_not_say_when_it_began_is_refused():
    definition = PerformanceLabelDefinition(window_months=24, performance_cutoff=CUTOFF,
                                            max_first_observed_age=6)
    with pytest.raises(LabelError, match="first observed"):
        build_performance_labels(histories(False), definition)
    with pytest.raises(LabelError, match="negative"):
        PerformanceLabelDefinition(window_months=24, performance_cutoff=CUTOFF,
                                   max_first_observed_age=-1)
