"""The model matrix, tested on the ways a column can arrive wrong.

Four families here. The first is arithmetic: a credit-line date has to become
a duration, and an ordinal string has to become a number in the order the words
imply, or the monotonic binning downstream is monotonic in nothing. The second
is the gate — a matrix that has picked up the axis, a servicing column or a
column this study dropped must be refused rather than fitted. The third is the
screen for constant columns, which is computed on the rows a build was given
and must not consult the rest of the book. The fourth is coverage: a column
that begins part-way through the book carries the calendar in its missingness,
and the list of those has to agree with the data it is used on.
"""

from __future__ import annotations

import pandas as pd
import pytest

from outoftime.features import (
    CLIPPED,
    DROPPED,
    FIRST_QUARTER,
    LATE_COVERAGE,
    VALUE_CARRIERS,
    VALUE_FLOOR,
    FeatureError,
    assert_matrix_clean,
    categorical_names,
    coverage_report,
    feature_names,
    informative,
    model_matrix,
    redundancy_report,
    value_report,
)
from outoftime.splits import LeakageError

RAW = {
    "issue_d": ["Jan-2015", "Feb-2015", "Mar-2015"],
    "earliest_cr_line": ["Jan-2005", "Aug-2014", "Mar-2015"],
    "sub_grade": ["A1", "C3", "G5"],
    "grade": ["A", "C", "G"],
    "emp_length": ["< 1 year", "10+ years", None],
    "term": [" 36 months", " 60 months", " 36 months"],
    "purpose": ["car", "credit_card", "car"],
    "addr_state": ["CA", "NY", "TX"],
    "loan_amnt": [10000.0, 20000.0, 5000.0],
    "funded_amnt": [10000.0, 20000.0, 5000.0],
    "funded_amnt_inv": [10000.0, 19975.0, 5000.0],
    "fico_range_low": [700.0, 660.0, 680.0],
    "fico_range_high": [704.0, 664.0, 684.0],
    "emp_title": ["driver", "nurse", "teacher"],
    "title": ["Car loan", "Debt", "Car"],
    "desc": [None, None, "text"],
    "zip_code": ["100xx", "200xx", "300xx"],
    "int_rate": [7.0, 13.0, 25.0],
}


def amortised(amount: float, rate: float, months: int) -> float:
    """The level payment on `amount` at `rate` percent a year over `months`."""
    monthly = rate / 1200.0
    return round(amount * monthly / (1.0 - (1.0 + monthly) ** (-months)), 2)


def raw_frame() -> pd.DataFrame:
    """A frame carrying every column the matrix reads, and the ones it drops."""
    frame = pd.DataFrame(RAW)
    frame["installment"] = [
        amortised(10000.0, 7.0, 36), amortised(20000.0, 13.0, 60),
        amortised(5000.0, 25.0, 36),
    ]
    for name in feature_names():
        if name not in frame.columns:
            frame[name] = [1.0, 2.0, 3.0]
    return frame


def test_matrix_holds_the_declared_features_and_no_others():
    matrix = model_matrix(raw_frame())
    assert list(matrix.columns) == list(feature_names())
    assert not set(matrix.columns) & DROPPED
    assert "issue_d" not in matrix.columns
    assert len(feature_names()) == 20
    assert not set(feature_names()) & set(VALUE_CARRIERS)
    assert set(CLIPPED) <= set(feature_names())


def test_credit_line_dates_become_durations():
    matrix = model_matrix(raw_frame())
    # January 2005 to January 2015 is ten years; a line opened in the month of
    # origination is a history of zero months, not a missing value.
    assert list(matrix["credit_history_months"]) == [120.0, 6.0, 0.0]


def test_ordinal_strings_become_numbers_in_the_order_the_words_imply():
    matrix = model_matrix(raw_frame())
    assert list(matrix["sub_grade"]) == [1.0, 13.0, 35.0]
    assert list(matrix["emp_length"])[:2] == [0.0, 10.0]
    assert pd.isna(matrix["emp_length"][2])
    assert list(matrix["term"]) == [36.0, 60.0, 36.0]


def test_declared_categoricals_survive_as_objects():
    matrix = model_matrix(raw_frame())
    for name in categorical_names():
        assert matrix[name].dtype == object, name


def test_an_absent_axis_is_refused():
    frame = raw_frame().drop(columns=["issue_d"])
    with pytest.raises(FeatureError, match="issue_d"):
        model_matrix(frame)


def test_the_gate_refuses_the_axis_a_servicing_column_and_a_dropped_column():
    matrix = model_matrix(raw_frame())
    assert_matrix_clean(matrix)

    with_axis = matrix.copy()
    with_axis["issue_d"] = pd.to_datetime(RAW["issue_d"], format="%b-%Y")
    with pytest.raises(LeakageError, match="split axis"):
        assert_matrix_clean(with_axis)

    with_future = matrix.copy()
    with_future["last_fico_range_high"] = [700.0, 660.0, 680.0]
    with pytest.raises(LeakageError, match="after origination"):
        assert_matrix_clean(with_future)

    with_dropped = matrix.copy()
    with_dropped["zip_code"] = RAW["zip_code"]
    with pytest.raises(FeatureError, match="zip_code"):
        assert_matrix_clean(with_dropped)

    with_late = matrix.copy()
    with_late["open_il_12m"] = [1.0, 2.0, 3.0]
    with pytest.raises(FeatureError, match="open_il_12m"):
        assert_matrix_clean(with_late)


def test_the_constant_screen_reads_only_the_rows_it_was_given():
    matrix = pd.DataFrame(
        {
            "dti": [1.0, 1.0, 1.0, 9.0],
            "annual_inc": [10.0, 20.0, 30.0, 40.0],
            "revol_bal": [None, None, None, 5.0],
        }
    )
    # On the first three rows dti is constant and revol_bal is entirely
    # missing, whatever the fourth row holds. A screen that saw the whole book
    # would keep both.
    assert informative(matrix, [0, 1, 2]) == ("annual_inc",)
    assert informative(matrix, [0, 1, 2, 3]) == ("dti", "annual_inc", "revol_bal")
    with pytest.raises(FeatureError, match="no rows"):
        informative(matrix, [])


def test_missingness_alone_keeps_a_column_and_a_bare_constant_does_not():
    matrix = pd.DataFrame(
        {
            "dti": [3.0, 3.0, 3.0, 3.0],
            "revol_bal": [5.0, 5.0, None, None],
            "annual_inc": [None, None, None, None],
        }
    )
    assert informative(matrix, [0, 1, 2, 3]) == ("revol_bal",)


def test_the_calendar_carriers_are_out_and_their_identities_measured():
    assert "int_rate" not in feature_names()
    assert "installment" not in feature_names()
    report = redundancy_report(raw_frame())
    assert report["int_rate"]["exact_agreement"] == 1.0
    assert report["installment"]["exact_agreement"] == 1.0

    broken = raw_frame()
    broken["installment"] = [999.0, 999.0, 999.0]
    with pytest.raises(FeatureError, match="installment"):
        redundancy_report(broken)


def test_redundancy_is_measured_and_a_pair_that_is_not_one_is_refused():
    frame = raw_frame()
    report = redundancy_report(frame)
    assert report["funded_amnt"]["exact_agreement"] == 1.0
    assert report["grade"]["exact_agreement"] == 1.0
    assert report["fico_range_high"]["distinct_offsets"] == 1.0
    assert report["funded_amnt_inv"]["correlation"] > 0.99

    broken = frame.copy()
    broken["grade"] = ["G", "A", "C"]
    with pytest.raises(FeatureError, match="grade"):
        redundancy_report(broken)


def book_with_coverage(late_from_quarter: int) -> pd.DataFrame:
    """Twelve quarters of loans; every late column is empty before a quarter."""
    months = [f"{m}-{y}" for y in (2010, 2011, 2012) for m in ("Jan", "Apr", "Jul", "Oct")]
    frame = pd.DataFrame({"issue_d": months})
    for name in feature_names():
        if name not in ("credit_history_months",):
            frame[name] = 1.0
    frame["earliest_cr_line"] = "Jan-2000"
    for name in LATE_COVERAGE:
        frame[name] = [None] * late_from_quarter + [1.0] * (12 - late_from_quarter)
    return frame


def test_late_coverage_is_measured_and_a_disagreement_stops_the_run():
    report = coverage_report(book_with_coverage(6))
    assert all(r["kept"] for n, r in report.items() if n not in LATE_COVERAGE)
    assert report["open_il_12m"]["onset"] == "2011Q3"
    assert report["open_il_12m"]["first_quarter_share"] == 0.0
    assert report["dti"]["onset"] == FIRST_QUARTER

    # A book on which every column is present from the start is not the book
    # the list was measured on, and the run must not proceed on it.
    with pytest.raises(FeatureError, match="disagree"):
        coverage_report(book_with_coverage(0))

    # Nor one on which a kept column begins late.
    late_kept = book_with_coverage(6)
    late_kept["dti"] = [None] * 6 + [1.0] * 6
    with pytest.raises(FeatureError, match="dti"):
        coverage_report(late_kept)


def book_with_values(per_quarter: int = 2, quarters: int = 8) -> pd.DataFrame:
    """Eight quarters from the first cohort; every value carrier turns on at the fifth.

    Kept columns alternate between two values from the first row, so nothing
    the matrix holds lies outside its first cohort; the two clipped columns
    span exactly their declared bounds in that cohort and exceed them later.
    """
    months = ["Apr-2010", "Jul-2010", "Oct-2010", "Jan-2011",
              "Apr-2011", "Jul-2011", "Oct-2011", "Jan-2012"][:quarters]
    n = per_quarter * len(months)
    late = [i >= 4 * per_quarter for i in range(n)]
    frame = pd.DataFrame({"issue_d": [m for m in months for _ in range(per_quarter)]})
    # Ten or twenty years of history on every row, so the duration the matrix
    # derives stays inside the first cohort's own range as the book advances.
    frame["earliest_cr_line"] = [
        f"{month[:3]}-{int(month[-4:]) - (10 if i % 2 == 0 else 20)}"
        for i, month in enumerate(frame["issue_d"])
    ]
    for name in feature_names():
        if name not in frame.columns and name != "credit_history_months":
            frame[name] = [1.0, 2.0] * (n // 2)
    frame["term"] = [" 36 months", " 60 months"] * (n // 2)
    frame["sub_grade"] = ["A1", "C3"] * (n // 2)
    frame["emp_length"] = ["< 1 year", "10+ years"] * (n // 2)
    frame["purpose"] = ["car", "credit_card"] * (n // 2)
    frame["home_ownership"] = ["RENT", "OWN"] * (n // 2)
    frame["verification_status"] = ["Verified", "Not Verified"] * (n // 2)
    low, high = CLIPPED["dti"]
    frame["dti"] = [35.0 if is_late else (low, high)[i % 2] for i, is_late in enumerate(late)]
    low, high = CLIPPED["loan_amnt"]
    frame["loan_amnt"] = [
        40000.0 if is_late else (low, high)[i % 2] for i, is_late in enumerate(late)
    ]
    for name in ("acc_now_delinq", "chargeoff_within_12_mths", "collections_12_mths_ex_med",
                 "delinq_amnt", "tax_liens"):
        frame[name] = [1.0 if is_late else 0.0 for is_late in late]
    frame["initial_list_status"] = ["w" if is_late else "f" for is_late in late]
    frame["application_type"] = ["Joint App" if is_late else "Individual" for is_late in late]
    frame["disbursement_method"] = ["DirectPay" if is_late else "Cash" for is_late in late]
    frame["addr_state"] = ["NY" if i >= per_quarter else "CA" for i in range(n)]
    return frame


def test_the_value_rule_is_measured_and_a_disagreement_stops_the_run():
    report = value_report(book_with_values())
    assert all(report[name]["kept"] for name in feature_names())
    assert all(not report[name]["kept"] for name in VALUE_CARRIERS)
    assert report["tax_liens"]["onset"] == "2011Q2"
    assert report["tax_liens"]["distinct_in_first_cohort"] == 1
    assert report["initial_list_status"]["first_cohort_support"] == ["f"]
    assert report["addr_state"]["share_outside_first_cohort"] > VALUE_FLOOR
    assert report["dti"]["clip"]["first_cohort"] == list(CLIPPED["dti"])
    # Clipping is what keeps the kept column under the rule.
    assert report["dti"]["share_outside_first_cohort"] == 0.0

    # A carrier that varies in the first cohort is not a carrier on this book.
    varied = book_with_values()
    varied["tax_liens"] = [0.0, 1.0] * (len(varied) // 2)
    with pytest.raises(FeatureError, match="tax_liens"):
        value_report(varied)

    # A kept column that is constant in the first cohort and not afterwards.
    late_kept = book_with_values()
    late_kept["pub_rec"] = [1.0 if i >= 8 else 0.0 for i in range(len(late_kept))]
    with pytest.raises(FeatureError, match="pub_rec"):
        value_report(late_kept)

    # A kept categorical whose late level is over the floor.
    late_level = book_with_values()
    late_level["purpose"] = ["wedding" if i >= 8 else "car" for i in range(len(late_level))]
    with pytest.raises(FeatureError, match="purpose"):
        value_report(late_level)

    # Clip bounds that are not the first cohort's own range.
    wider = book_with_values()
    wider.loc[1, "dti"] = 30.0
    with pytest.raises(FeatureError, match="clipped"):
        value_report(wider)


def test_clipped_columns_are_clipped_in_the_matrix():
    frame = raw_frame()
    frame["loan_amnt"] = [500.0, 40000.0, 5000.0]
    frame["dti"] = [-1.0, 39.9, 12.5]
    matrix = model_matrix(frame)
    assert list(matrix["loan_amnt"]) == [1000.0, 25000.0, 5000.0]
    assert list(matrix["dti"]) == [0.0, 24.99, 12.5]
