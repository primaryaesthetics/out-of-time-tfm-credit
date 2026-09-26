"""The date-column audit has to catch a performance-window column.

These tests construct the mistake rather than the happy path. The mistake is a
date column that looks like an origination axis and is not: `last_pymnt_d` is
written after the loan is, and a split on it sorts loans by outcome while
reading like it sorts them by time. An assertion that has never fired is an
assertion nobody has checked.

Skipped where pandas is absent, which is the case in the gate workflow that
installs only pytest and ruff.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("matplotlib")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import vintage_structure as vs


def write(tmp_path: Path, frame: pd.DataFrame) -> Path:
    path = tmp_path / "book.csv"
    frame.to_csv(path, index=False)
    return path


def book(
    issue: list[str],
    status: list[str],
    **extra_columns: list[str | None],
) -> pd.DataFrame:
    data = {"issue_d": issue, "loan_status": status, "term": [" 36 months"] * len(issue)}
    data.update(extra_columns)
    return pd.DataFrame(data)


def test_flags_a_column_that_reaches_past_the_last_origination(tmp_path):
    """The planted trap: payments continue after the last loan is written."""
    frame = book(
        issue=["Jan-2015", "Feb-2015", "Mar-2015"] * 40,
        status=["Fully Paid", "Charged Off", "Current"] * 40,
        last_pymnt_d=["Jun-2018", "Jul-2018", "Aug-2018"] * 40,
    )
    summary = vs.summarise(write(tmp_path, frame), "issue_d")

    assert "last_pymnt_d" in summary["columns_reaching_past_last_origination"]
    assert "issue_d" not in summary["columns_reaching_past_last_origination"]
    assert summary["date_column_audit"]["last_pymnt_d"]["max"] == "2018-08-01"


def test_does_not_flag_a_column_that_predates_origination(tmp_path):
    """A credit line opened before the loan is knowable at decision time."""
    frame = book(
        issue=["Jan-2015", "Feb-2015", "Mar-2015"] * 40,
        status=["Fully Paid", "Charged Off", "Current"] * 40,
        earliest_cr_line=["Jan-2001", "Feb-2002", "Mar-2003"] * 40,
    )
    summary = vs.summarise(write(tmp_path, frame), "issue_d")

    assert summary["columns_reaching_past_last_origination"] == []


def test_resolved_excludes_loans_still_running(tmp_path):
    frame = book(
        issue=["Jan-2015"] * 100,
        status=["Fully Paid"] * 40 + ["Charged Off"] * 25 + ["Default"] * 5
        + ["Current"] * 20 + ["Late (31-120 days)"] * 10,
    )
    summary = vs.summarise(write(tmp_path, frame), "issue_d")

    assert summary["resolved"]["count"] == 70
    assert summary["resolved"]["fraction"] == pytest.approx(0.70)


def test_missing_origination_column_is_refused(tmp_path):
    """A wrong axis is refused loudly rather than measured quietly."""
    frame = book(
        issue=["Jan-2015", "Feb-2015"] * 60,
        status=["Fully Paid", "Charged Off"] * 60,
    )
    with pytest.raises(SystemExit, match="did not parse as a date column"):
        vs.summarise(write(tmp_path, frame), "origination_date")


def test_free_text_is_not_mistaken_for_a_date(tmp_path):
    """One date-shaped value in a text column must not promote the column."""
    titles = ["Debt consolidation"] * 119 + ["Mar-2015"]
    frame = book(
        issue=["Jan-2015", "Feb-2015"] * 60,
        status=["Fully Paid", "Charged Off"] * 60,
        title=titles,
    )
    summary = vs.summarise(write(tmp_path, frame), "issue_d")

    assert "title" not in summary["date_column_audit"]
