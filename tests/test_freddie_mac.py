"""The layout has to match the files, and the map has to stop the traps.

The files carry no header, so the layout is a hand transcription and a shifted
column would read under the wrong name without a sound. The width check is the
only thing standing between a new release and that. The traps here are the
performance columns: every one of them is the future, and the delinquency
status in particular is the label under another name.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from outoftime.freddie_mac import (
    ALL_ORIGINATION_COLUMNS,
    AXIS,
    CALENDAR,
    FEATURE_AVAILABILITY,
    LABEL_SOURCES,
    LATE_FIRST_PAYMENT_MONTHS,
    NON_FEATURES,
    ORIGINATION_COLUMNS,
    PERFORMANCE_COLUMNS,
    SENTINELS,
    VINTAGE_CLOCK,
    audit_widths,
    first_payment_lag,
    leaking_features,
    origination_quarter,
    safe_features,
    widths_match,
)
from outoftime.splits import LeakageError, assert_features_knowable

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "freddie-mac"


def test_layout_widths_are_release_47():
    assert len(ORIGINATION_COLUMNS) == 31
    assert len(PERFORMANCE_COLUMNS) == 35
    assert len(set(ORIGINATION_COLUMNS)) == 31
    assert len(set(PERFORMANCE_COLUMNS)) == 35


def test_release_47_moves_are_in_the_performance_file():
    assert "mi_cancellation" in PERFORMANCE_COLUMNS
    assert "servicer" in PERFORMANCE_COLUMNS
    assert "mi_cancellation" not in ORIGINATION_COLUMNS
    assert ORIGINATION_COLUMNS[-1] == "vantage_score"
    assert PERFORMANCE_COLUMNS[-1] == "bankruptcy_cramdown_costs"


def test_every_origination_column_is_classified_exactly_once():
    features = frozenset(n for n in FEATURE_AVAILABILITY if FEATURE_AVAILABILITY[n] <= 0)
    groups = [features, NON_FEATURES, CALENDAR]
    assert sum(len(g) for g in groups) == len(ALL_ORIGINATION_COLUMNS) == 31
    assert ALL_ORIGINATION_COLUMNS == frozenset(ORIGINATION_COLUMNS)


def test_the_axis_and_the_clock_are_not_features():
    assert AXIS not in FEATURE_AVAILABILITY
    assert VINTAGE_CLOCK in CALENDAR
    assert VINTAGE_CLOCK not in safe_features()


def test_every_performance_column_is_the_future():
    for name in PERFORMANCE_COLUMNS:
        if name == "loan_id":
            continue
        assert FEATURE_AVAILABILITY[name] > 0, name
    assert LABEL_SOURCES <= set(PERFORMANCE_COLUMNS)
    assert "delinquency_status" in leaking_features()


def test_the_gate_accepts_the_safe_set_and_refuses_the_label():
    assert_features_knowable(FEATURE_AVAILABILITY, safe_features())
    with pytest.raises(LeakageError):
        assert_features_knowable(FEATURE_AVAILABILITY, ["fico", "delinquency_status"])
    with pytest.raises(LeakageError):
        assert_features_knowable(FEATURE_AVAILABILITY, ["fico", "origination_quarter"])


def test_sentinels_name_declared_columns():
    assert set(SENTINELS) <= set(ORIGINATION_COLUMNS)


@pytest.mark.parametrize("loan_id, expected", [
    ("F08Q10000000", (2008, 1)),
    ("F99Q30000000", (1999, 3)),
    ("A12Q40000000", (2012, 4)),
    ("F26Q10000000", (2026, 1)),
])
def test_origination_quarter_is_read_from_the_identifier(loan_id, expected):
    assert origination_quarter(loan_id) == expected


@pytest.mark.parametrize("bad", ["", "F08Q5000001", "X08Q10000000", "F08Q1000000", "12345"])
def test_an_identifier_that_does_not_parse_has_no_cohort(bad):
    with pytest.raises(ValueError):
        origination_quarter(bad)


@pytest.mark.parametrize("year, quarter, fpd, lag", [
    (2008, 1, 200801, 0),
    (2008, 1, 200803, 2),
    (2008, 1, 200805, 4),
    (2008, 4, 200902, 4),
    (2008, 1, 201503, 86),
    (2008, 2, 200803, -1),
])
def test_first_payment_lag_counts_months_from_the_quarter_start(year, quarter, fpd, lag):
    assert first_payment_lag(year, quarter, fpd) == lag


def test_the_late_threshold_admits_the_ordinary_settlement_lag():
    # Written in the last month of the quarter, first payment two months on.
    assert first_payment_lag(2008, 1, 200805) < LATE_FIRST_PAYMENT_MONTHS
    assert first_payment_lag(2008, 1, 200807) >= LATE_FIRST_PAYMENT_MONTHS


def test_width_audit_catches_a_shifted_layout():
    assert widths_match(audit_widths(31, 35))
    assert not widths_match(audit_widths(32, 35))
    assert not widths_match(audit_widths(31, 34))


@pytest.mark.skipif(not (RAW / "sample_2008.zip").exists(), reason="the raw zips are not present")
def test_the_layout_matches_the_actual_files():
    with zipfile.ZipFile(RAW / "sample_2008.zip") as archive:
        widths = {}
        for member in archive.namelist():
            with archive.open(member) as handle:
                line = io.TextIOWrapper(handle, encoding="utf-8").readline()
            widths[member] = line.rstrip("\r\n").count("|") + 1
    orig = next(v for k, v in widths.items() if "orig" in k)
    perf = next(v for k, v in widths.items() if "perf" in k)
    assert widths_match(audit_widths(orig, perf)), widths
