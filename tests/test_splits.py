"""The leakage gate, tested by trying to leak.

An assertion that has never fired is an assertion nobody has checked. Every
test here constructs the specific mistake the corresponding check exists to
catch, so a refactor that silently weakens a check fails here rather than in a
result six weeks later.
"""

from __future__ import annotations

import datetime as dt

import pytest

from outoftime.splits import LeakageError, assert_features_knowable, temporal_split


def day(offset: int) -> dt.date:
    return dt.date(2020, 1, 1) + dt.timedelta(days=offset)


def clean_dates() -> list[dt.date]:
    # Three years of daily originations: train 2020, validate 2021, oot 2022.
    return [day(i) for i in range(1096)]


def test_clean_split_builds_and_orders():
    split = temporal_split(
        clean_dates(), valid_from=dt.date(2021, 1, 1), oot_from=dt.date(2022, 1, 1)
    )
    assert split.train.last < split.valid.first < split.oot.first
    assert split.train.size == 366  # 2020 was a leap year
    assert split.oot.span_days >= 90
    assert "| train |" in split.summary()


def test_immature_labels_are_refused_under_embargo():
    # Loans originated the day before the cutoff cannot have a 12-month label
    # yet, so training on them means training on an outcome that was observed
    # inside the out-of-time period. With daily originations the gap is one day
    # and a 365-day embargo has to refuse it.
    with pytest.raises(LeakageError, match="embargo of 365"):
        temporal_split(
            clean_dates(),
            valid_from=dt.date(2021, 1, 1),
            oot_from=dt.date(2022, 1, 1),
            embargo_days=365,
        )


def test_embargo_is_satisfied_once_the_gap_rows_are_dropped():
    # The same three years with the year before each cutoff removed, which is
    # what a caller does when the embargo refuses the naive split.
    dates = [
        d for d in clean_dates()
        if not (dt.date(2020, 1, 2) <= d < dt.date(2021, 1, 1))
        and not (dt.date(2021, 1, 2) <= d < dt.date(2022, 1, 1))
    ]
    split = temporal_split(
        dates,
        valid_from=dt.date(2021, 1, 1),
        oot_from=dt.date(2022, 1, 1),
        embargo_days=364,
    )
    assert split.train.last == dt.date(2020, 1, 1)
    assert split.valid.last == dt.date(2021, 1, 1)


def test_empty_window_is_refused():
    with pytest.raises(LeakageError, match="valid window is empty"):
        temporal_split(
            [day(i) for i in range(30)] + [dt.date(2022, 6, 1) + dt.timedelta(days=i) for i in range(120)],
            valid_from=dt.date(2021, 1, 1),
            oot_from=dt.date(2021, 6, 1),
        )


def test_narrow_oot_window_is_refused():
    dates = clean_dates()[: 366 + 365 + 30]
    with pytest.raises(LeakageError, match="below the 90 required"):
        temporal_split(
            dates, valid_from=dt.date(2021, 1, 1), oot_from=dt.date(2022, 1, 1)
        )


def test_boundaries_must_be_ordered():
    with pytest.raises(LeakageError, match="is not before"):
        temporal_split(
            clean_dates(), valid_from=dt.date(2022, 1, 1), oot_from=dt.date(2021, 1, 1)
        )


def test_entity_crossing_windows_is_refused():
    dates = clean_dates()
    # One borrower who took a loan in 2020 and another in 2022: the model would
    # be scored out of time on somebody it had already memorised.
    ids = [f"acct-{i}" for i in range(len(dates))]
    ids[900] = ids[10]
    with pytest.raises(LeakageError, match="appear in more than one window"):
        temporal_split(
            dates,
            valid_from=dt.date(2021, 1, 1),
            oot_from=dt.date(2022, 1, 1),
            entity_ids=ids,
        )


def test_distinct_entities_pass_and_are_counted():
    dates = clean_dates()
    ids = [f"acct-{i}" for i in range(len(dates))]
    split = temporal_split(
        dates,
        valid_from=dt.date(2021, 1, 1),
        oot_from=dt.date(2022, 1, 1),
        entity_ids=ids,
    )
    assert any("none crossing a window" in note for note in split.notes)


def test_entity_length_mismatch_is_refused():
    with pytest.raises(LeakageError, match="against"):
        temporal_split(
            clean_dates(),
            valid_from=dt.date(2021, 1, 1),
            oot_from=dt.date(2022, 1, 1),
            entity_ids=["a", "b"],
        )


def test_undeclared_feature_is_refused():
    with pytest.raises(LeakageError, match="no declared availability"):
        assert_features_knowable({"fico": 0}, ["fico", "dti"])


def test_future_feature_is_refused():
    with pytest.raises(LeakageError, match="only knowable after origination"):
        assert_features_knowable(
            {"fico": 0, "last_fico_range_high": 30},
            ["fico", "last_fico_range_high"],
        )


def test_features_known_at_or_before_origination_pass():
    assert_features_knowable({"fico": 0, "age_of_oldest_line": -30}, ["fico", "age_of_oldest_line"])
