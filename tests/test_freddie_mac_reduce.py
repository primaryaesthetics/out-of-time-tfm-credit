"""The reduction admits a missing servicing record only where it cannot have
arrived yet, and refuses a gap anywhere else."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from freddie_mac_reduce import (
    REPORTING_LAG_MONTHS,
    check_missing_histories,
    months,
)

LAST_PERIOD = 2026 * 12 + 3  # 2026-03 as a month count


def test_a_loan_acquired_just_before_the_cutoff_may_have_no_record_yet():
    young = pd.Series([LAST_PERIOD, LAST_PERIOD - 1, LAST_PERIOD - REPORTING_LAG_MONTHS])
    check_missing_histories(young, LAST_PERIOD)


def test_an_older_loan_with_no_record_is_a_gap_and_is_refused():
    stale = pd.Series([LAST_PERIOD, LAST_PERIOD - REPORTING_LAG_MONTHS - 1])
    with pytest.raises(SystemExit):
        check_missing_histories(stale, LAST_PERIOD)


def test_months_turns_yyyymm_into_a_month_count():
    assert months(pd.Series(["202603", "202512"])).tolist() == [LAST_PERIOD, LAST_PERIOD - 3]
    assert pd.isna(months(pd.Series([None])).iloc[0])
