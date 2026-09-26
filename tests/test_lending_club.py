"""The availability map has to match the file, and has to stop the traps.

These tests exist because the map is hand-written and hand-written things rot.
A new release of the dataset that adds a column must fail here rather than let
an undeclared field through as though somebody had thought about it.

The named traps are the ones that would pass a casual review: a bureau counter
whose name reads like an outcome, and a credit score refreshed monthly sitting
beside the one taken at application.
"""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from outoftime.lending_club import (
    ALL_COLUMNS,
    AXIS,
    FEATURE_AVAILABILITY,
    LABEL_SOURCES,
    NON_FEATURES,
    audit_columns,
    leaking_features,
    safe_features,
)
from outoftime.splits import LeakageError, assert_features_knowable

DATA = Path(__file__).resolve().parent.parent / "data" / "raw" / \
    "accepted_2007_to_2018Q4.csv.gz"


def test_every_column_is_classified_exactly_once():
    groups = [frozenset(FEATURE_AVAILABILITY), NON_FEATURES, LABEL_SOURCES,
              {AXIS}]
    total = sum(len(g) for g in groups)
    assert total == len(ALL_COLUMNS), "a column is in two groups at once"
    assert len(ALL_COLUMNS) == 151


@pytest.mark.skipif(not DATA.exists(), reason="the raw file is not present")
def test_the_map_matches_the_actual_file():
    with gzip.open(DATA, "rt") as handle:
        header = handle.readline().strip().split(",")
    audit = audit_columns(header)
    assert audit["undeclared"] == (), \
        "the file has columns nobody has classified"
    assert audit["declared_but_absent"] == (), \
        "the map declares columns the file does not have"


def test_a_new_column_is_reported_rather_than_ignored():
    audit = audit_columns([*ALL_COLUMNS, "some_new_2019_field"])
    assert audit["undeclared"] == ("some_new_2019_field",)


def test_the_bureau_counter_that_reads_like_an_outcome_is_a_feature():
    """chargeoff_within_12_mths describes the borrower's other accounts.

    Measured on this book: mean 0.0098 among charged-off loans against 0.0089
    among fully paid. No separation, which is what an application-time input
    looks like.
    """
    assert FEATURE_AVAILABILITY["chargeoff_within_12_mths"] == 0
    assert "chargeoff_within_12_mths" in safe_features()


def test_the_refreshed_credit_score_is_not_a_feature():
    """last_fico_range_* is updated monthly and sits beside the safe one."""
    for name in ("last_fico_range_high", "last_fico_range_low"):
        assert FEATURE_AVAILABILITY[name] > 0
        assert name in leaking_features()
    for name in ("fico_range_high", "fico_range_low"):
        assert FEATURE_AVAILABILITY[name] == 0


def test_the_label_sources_are_not_available_as_features():
    """Using one by accident must be a lookup failure, not a silent success."""
    for name in ("loan_status", "last_pymnt_d"):
        assert name in LABEL_SOURCES
        assert name not in FEATURE_AVAILABILITY
        assert name not in safe_features()


def test_the_origination_axis_is_not_a_feature():
    assert AXIS not in FEATURE_AVAILABILITY


def test_distress_programmes_are_the_label_under_another_name():
    for name in ("hardship_flag", "settlement_amount", "debt_settlement_flag"):
        assert FEATURE_AVAILABILITY[name] > 0


def test_safe_and_leaking_do_not_overlap_and_cover_the_map():
    safe, leaking = set(safe_features()), set(leaking_features())
    assert safe & leaking == set()
    assert safe | leaking == set(FEATURE_AVAILABILITY)


def test_the_gate_accepts_every_safe_feature():
    """The whole point of the map: it has to satisfy the gate it feeds."""
    assert_features_knowable(FEATURE_AVAILABILITY, safe_features())


def test_the_gate_refuses_each_leaking_feature_one_at_a_time():
    for name in leaking_features():
        with pytest.raises(LeakageError):
            assert_features_knowable(FEATURE_AVAILABILITY, [name])


def test_the_gate_refuses_a_safe_set_with_one_leak_hidden_in_it():
    """The realistic failure: someone keeps 'all the numeric columns'."""
    sneaky = [*safe_features()[:20], "out_prncp"]
    with pytest.raises(LeakageError):
        assert_features_knowable(FEATURE_AVAILABILITY, sneaky)


def test_an_undeclared_feature_is_refused_rather_than_assumed_safe():
    with pytest.raises(LeakageError):
        assert_features_knowable(FEATURE_AVAILABILITY, ["invented_column"])


def test_there_are_enough_safe_features_to_build_a_scorecard():
    """A hundred columns of application and bureau data is a real book."""
    assert len(safe_features()) > 100
