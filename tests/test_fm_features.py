"""The Freddie Mac matrix and its gates, tested on the ways a column can arrive wrong.

The synthetic book of `fm_synthetic` plants every decision the module
declares, so each report passes on it; each test then moves one thing and the
report that owns it has to refuse. The clauses of the value rule are tested
one by one, each constructed on the book rather than described.
"""

from __future__ import annotations

import numpy as np
import pytest

pd = pytest.importorskip("pandas")

import fm_synthetic

from outoftime import fm_features as ff
from outoftime.features import FeatureError
from outoftime.splits import LeakageError


@pytest.fixture(scope="module")
def loans():
    frame, _ = fm_synthetic.book()
    return frame


def in_quarters(frame, first: str, last: str):
    quarter = frame["origination_quarter"].astype(str)
    return (quarter >= first) & (quarter <= last)


def test_the_matrix_holds_the_declared_features_clipped_and_sentinels_missing(loans):
    assert ff.feature_names() == (
        "borrowers", "cltv", "fico", "first_time_homebuyer", "ltv", "mi_pct", "occupancy",
        "prepayment_penalty", "property_type", "purpose", "state", "term", "units",
        "upb_to_limit")
    assert ff.categorical_names() == (
        "first_time_homebuyer", "occupancy", "prepayment_penalty", "property_type", "purpose",
        "state")
    assert set(ff.CLIPPED) == set(ff.feature_names()) - set(ff.categorical_names())
    matrix = ff.model_matrix(loans)
    assert list(matrix.columns) == list(ff.feature_names())
    assert matrix.loc[(loans["fico"] == "9999").to_numpy(), "fico"].isna().all()
    for name, (low, high) in ff.CLIPPED.items():
        values = matrix[name].dropna()
        assert values.min() >= low and values.max() <= high, name
    assert "upb" not in matrix.columns
    low, high = ff.CLIPPED["upb_to_limit"]
    ratio = loans["upb"].astype(float) / loans["origination_year"].astype(int).map(
        ff.CONFORMING_LIMIT)
    assert (matrix["upb_to_limit"] == high).sum() > (ratio == high).sum()
    planted = loans.index[(ratio > low) & (ratio < high)][7]
    year = int(loans.loc[planted, "origination_year"])
    assert matrix.loc[planted, "upb_to_limit"] == pytest.approx(
        float(loans.loc[planted, "upb"]) / ff.CONFORMING_LIMIT[year])
    for name in ff.categorical_names():
        assert matrix[name].dtype == object, name
    ff.assert_matrix_clean(matrix)

    outside = loans.head(20).copy()
    outside["origination_year"] = 1998
    with pytest.raises(FeatureError, match="1998"):
        ff.model_matrix(outside)


def test_the_conforming_limit_table_is_whole_and_never_falls(loans):
    years = sorted(ff.CONFORMING_LIMIT)
    assert years == list(range(1999, 2027))
    values = [ff.CONFORMING_LIMIT[year] for year in years]
    assert values == sorted(values)
    assert all(value % 50 == 0 for value in values)
    assert all(ff.CONFORMING_LIMIT[year] == 417_000 for year in range(2006, 2017))
    assert set(loans["origination_year"].astype(int)) <= set(years)


def test_the_gate_refuses_the_axis_the_calendar_a_dropped_and_a_servicing_column(loans):
    matrix = ff.model_matrix(loans)
    for name, error, match in (
        ("origination_quarter", LeakageError, "axis"),
        ("first_payment_date", LeakageError, "axis"),
        ("loan_id", LeakageError, "axis"),
        ("rate", FeatureError, "rate"),
        ("dti", FeatureError, "dti"),
        ("channel", FeatureError, "channel"),
        ("upb", FeatureError, "upb"),
        ("current_upb", LeakageError, "after origination"),
        ("made_up", LeakageError, "no declared availability"),
    ):
        smuggled = matrix.copy()
        smuggled[name] = 1.0
        with pytest.raises(error, match=match):
            ff.assert_matrix_clean(smuggled)


def test_the_rate_is_measured_and_its_exclusion_does_not_depend_on_it(loans):
    report = ff.redundancy_report(loans)
    assert report["rate"]["variance_share"] > 0.9 and report["rate"]["kept"] is False
    assert report["cltv"]["kept"] is True and report["cltv"]["exact_agreement"] > 0.8
    broken = loans.copy()
    broken["rate"] = [f"{v:.3f}" for v in np.random.default_rng(1).uniform(2, 9, len(broken))]
    assert ff.redundancy_report(broken)["rate"]["variance_share"] < 0.5
    assert "rate" not in ff.feature_names()

    shares = report["calendar_share"]
    numeric = set(ff.feature_names()) - set(ff.categorical_names())
    assert numeric | {"rate", "upb", "upb_to_limit"} <= set(shares)
    # The nominal amount rises with the year's limit; the ratio does not.
    assert shares["upb_to_limit"] < shares["upb"]


def test_late_coverage_is_measured_and_a_disagreement_stops_the_run(loans):
    report = ff.coverage_report(loans)
    assert report["valuation_method"]["onset"] == "2020H1"
    assert report["special_eligibility_program"]["onset"] == "2017H1"
    assert report["vantage_score"]["peak_share"] == 0.0

    early = loans.copy()
    early["valuation_method"] = "2"
    with pytest.raises(FeatureError, match="disagree"):
        ff.coverage_report(early)

    late_kept = loans.copy()
    late_kept.loc[late_kept["origination_year"] < 2003, "fico"] = "9999"
    with pytest.raises(FeatureError, match="fico"):
        ff.coverage_report(late_kept)


def test_each_clause_of_the_value_rule_fires_where_it_is_planted(loans):
    report = ff.value_report(loans)
    clauses = {name: report[name]["clauses"] for name in report}
    assert clauses["harp"][0] == "constant on the first cohort"
    assert clauses["super_conforming"] == ["constant on the first cohort"]
    assert clauses["seller"] == ["a level absent from the first cohort"]
    assert clauses["channel"] == ["a level present on the first cohort and absent from the last"]
    assert clauses["msa"] == ["missing share differs between the first and the last cohort"]
    assert clauses["dti"] == ["missing share differs between the first and the last cohort"]
    # A level that lives in the middle of the axis under the floor is left alone.
    assert "S" in report["occupancy"]["late_levels"] and not report["occupancy"]["out"]
    assert report["vantage_score"]["gates"] == ["coverage", "value"]
    assert all(not report[name]["out"] for name in ff.feature_names())
    assert report["upb_to_limit"]["shared_range"] == list(ff.CLIPPED["upb_to_limit"])
    assert report["upb"]["replaced_by"] == "upb_to_limit" and report["upb"]["checked"] is False


@pytest.mark.parametrize("damage, column", [
    ("late level over the floor", "purpose"),
    ("level gone from the last cohort", "state"),
    ("missing share moved", "fico"),
    ("constant on the first cohort", "purpose"),
    ("shared range moved", "upb_to_limit"),
])
def test_a_kept_column_that_breaks_the_rule_stops_the_run(loans, damage, column):
    broken = loans.copy()
    if damage == "late level over the floor":
        broken.loc[broken["origination_year"] >= 2010, "purpose"] = "X"
    elif damage == "level gone from the last cohort":
        last = in_quarters(broken, "2023Q3", "2023Q4") & (broken["state"] == "NY")
        broken.loc[last, "state"] = "CA"
    elif damage == "missing share moved":
        last = in_quarters(broken, "2023Q3", "2023Q4")
        broken.loc[last[last].index[::5], "fico"] = "9999"
    elif damage == "constant on the first cohort":
        broken.loc[in_quarters(broken, "1999Q1", "1999Q1"), "purpose"] = "P"
    else:
        first = in_quarters(broken, "1999Q1", "1999Q1")
        broken.loc[first[first].index[0], "upb"] = "500000"
    with pytest.raises(FeatureError, match=column):
        ff.value_report(broken)


def test_a_dropped_column_the_rule_would_keep_stops_the_run(loans):
    # Both levels on the first cohort and on the last: nothing in the rule
    # fires, and a list that drops the column no longer describes the book.
    healed = loans.copy()
    healed["harp"] = np.where(np.arange(len(healed)) % 2 == 0, "N", "Y")
    with pytest.raises(FeatureError, match="harp"):
        ff.value_report(healed)


def test_the_dti_kept_ablation_is_declared_measured_and_refused_when_undeclared(loans):
    assert ff.feature_names(ablation="dti_kept") == tuple(sorted(ff.feature_names() + ("dti",)))
    assert ff.categorical_names(ablation="dti_kept") == ff.categorical_names()
    matrix = ff.model_matrix(loans, ablation="dti_kept")
    low, high = ff.ABLATION_CLIPPED["dti"]
    assert (matrix["dti"].min(), matrix["dti"].max()) == (low, high)
    assert matrix.loc[(loans["dti"] == "999").to_numpy(), "dti"].isna().all()

    report = ff.value_report(loans, ablation="dti_kept")
    assert report["dti"]["out"] is True and report["dti"]["ablation"] == "dti_kept"
    assert report["dti"]["clauses"] == [ff.MISSING_SHARE_CLAUSE]
    assert report["dti"]["shared_range"] == [low, high]
    ff.shift_report(loans, ablation="dti_kept")
    ff.assert_matrix_clean(matrix, ablation="dti_kept")
    # A run that forgets to declare the ablation is refused.
    with pytest.raises(FeatureError, match="dti"):
        ff.assert_matrix_clean(matrix)

    # Any other disagreement under the ablation stops the run, and so does
    # the absence of the one it declares.
    broken = loans.copy()
    broken.loc[broken["origination_year"] >= 2010, "purpose"] = "X"
    with pytest.raises(FeatureError, match="purpose"):
        ff.value_report(broken, ablation="dti_kept")
    healed = loans.copy()
    healed.loc[in_quarters(healed, "1999Q1", "1999Q1") & (healed["dti"] == "999"), "dti"] = "35"
    with pytest.raises(FeatureError, match="dti_kept"):
        ff.value_report(healed, ablation="dti_kept")
    with pytest.raises(FeatureError, match="no ablation"):
        ff.feature_names(ablation="rate_kept")


def test_the_upb_nominal_ablation_is_declared_measured_and_refused_when_undeclared(loans):
    names = ff.feature_names(ablation="upb_nominal")
    assert "upb" in names and "upb_to_limit" not in names
    assert len(names) == len(ff.feature_names())
    matrix = ff.model_matrix(loans, ablation="upb_nominal")
    low, high = ff.ABLATION_CLIPPED["upb"]
    assert (matrix["upb"].min(), matrix["upb"].max()) == (low, high)

    report = ff.value_report(loans, ablation="upb_nominal")
    assert report["upb"]["ablation"] == "upb_nominal" and report["upb"]["out"] is False
    assert report["upb"]["shared_range"] == [low, high]
    # Both forms are recorded, whichever the matrix carries.
    assert report["upb_to_limit"]["shared_range"] == list(ff.CLIPPED["upb_to_limit"])
    assert report["upb_to_limit"]["checked"] is False
    ff.shift_report(loans, ablation="upb_nominal")

    ff.assert_matrix_clean(matrix, ablation="upb_nominal")
    with pytest.raises(FeatureError, match="upb"):
        ff.assert_matrix_clean(matrix)
    with pytest.raises(FeatureError, match="upb_to_limit"):
        ff.assert_matrix_clean(ff.model_matrix(loans), ablation="upb_nominal")


def test_the_shift_report_names_what_moves_inside_the_axis(loans):
    report = ff.shift_report(loans)
    occupancy = report["columns"]["occupancy"]["levels_absent_from_last_cohort"]
    assert set(occupancy) == {"S"} and occupancy["S"]["last_cohort_holding"] == "2010H2"
    assert "occupancy" in report["flagged"]
    assert report["columns"]["upb_to_limit"]["share_outside_last_cohort"] == 0.0
    # And it refuses nothing: the gates still pass on the same book.
    ff.value_report(loans)
