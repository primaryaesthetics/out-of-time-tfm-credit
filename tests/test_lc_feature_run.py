"""The Lending Club feature run, on a small book whose gates are known.

The book is written as the accepted-loans file is, read back by the builds'
own loader, and passes all three reports: two identities per redundant pair,
the calendar carriers exact, every late-coverage column empty before a
quarter, every value carrier turning on after the first cohort and the two
capped columns spanning their bounds in it. On it the run must split the
knowable columns into kept and dropped with none in both and none lost, date
each coverage drop by the quarter the data gives rather than the one the list
declares, and write the reports exactly as they come when called directly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("matplotlib")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import gbm_builds
import lc_feature_run as lcf

from outoftime.features import (
    CALENDAR_CARRIERS,
    CLIPPED,
    DATE_TO_DURATION,
    FIRST_QUARTER,
    LATE_COVERAGE,
    VALUE_CARRIERS,
    coverage_report,
    feature_names,
    redundancy_report,
    value_report,
)

MONTHS = ["Apr-2010", "Jul-2010", "Oct-2010", "Jan-2011",
          "Apr-2011", "Jul-2011", "Oct-2011", "Jan-2012"]
QUARTERS = ["2010Q2", "2010Q3", "2010Q4", "2011Q1", "2011Q2", "2011Q3", "2011Q4", "2012Q1"]
PER_QUARTER = 4
RATE = {"A1": 7.0, "C3": 13.0}


def amortised(amount: float, rate: float, months: int) -> float:
    monthly = rate / 1200.0
    return round(amount * monthly / (1.0 - (1.0 + monthly) ** (-months)), 2)


def book(late_onset: int = 2, probe: str = "open_il_12m", probe_onset: int = 5) -> pd.DataFrame:
    """Eight quarters from the first cohort, every gate passing on them.

    Every late-coverage column is empty before quarter `late_onset`, and the
    column `probe` before quarter `probe_onset`, both counted from the first
    cohort. The value carriers turn on at the fifth quarter.
    """
    n = PER_QUARTER * len(MONTHS)
    quarter = [i // PER_QUARTER for i in range(n)]
    late = [q >= 4 for q in quarter]
    frame = pd.DataFrame({"issue_d": [MONTHS[q] for q in quarter]})
    frame["earliest_cr_line"] = [
        f"{month[:3]}-{int(month[-4:]) - (10 if i % 2 == 0 else 20)}"
        for i, month in enumerate(frame["issue_d"])
    ]
    for name in feature_names():
        if name not in frame.columns and name not in DATE_TO_DURATION.values():
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

    # The redundant pairs and the calendar carriers hold exactly.
    frame["funded_amnt"] = frame["loan_amnt"]
    frame["funded_amnt_inv"] = frame["loan_amnt"]
    frame["fico_range_high"] = frame["fico_range_low"] + 4.0
    frame["grade"] = frame["sub_grade"].str[0]
    frame["int_rate"] = frame["sub_grade"].map(RATE)
    frame["installment"] = [
        amortised(amount, rate, int(term.split()[0]))
        for amount, rate, term in zip(frame["loan_amnt"], frame["int_rate"], frame["term"])
    ]

    for name in ("acc_now_delinq", "chargeoff_within_12_mths", "collections_12_mths_ex_med",
                 "delinq_amnt", "tax_liens"):
        frame[name] = [1.0 if is_late else 0.0 for is_late in late]
    frame["initial_list_status"] = ["w" if is_late else "f" for is_late in late]
    frame["application_type"] = ["Joint App" if is_late else "Individual" for is_late in late]
    frame["disbursement_method"] = ["DirectPay" if is_late else "Cash" for is_late in late]
    frame["addr_state"] = ["NY" if i >= PER_QUARTER else "CA" for i in range(n)]

    for name in LATE_COVERAGE:
        start = probe_onset if name == probe else late_onset
        frame[name] = [None if q < start else 1.0 for q in quarter]

    frame["loan_status"] = ["Fully Paid", "Charged Off"] * (n // 2)
    frame["last_pymnt_d"] = "Mar-2013"
    return frame


def run(tmp_path: Path, frame: pd.DataFrame, name: str = "run") -> tuple[dict, dict, Path]:
    source = tmp_path / f"{name}.csv"
    frame.to_csv(source, index=False)
    out = tmp_path / name
    assert lcf.main([str(source), "--out-dir", str(out)]) == 0
    gates = json.loads((out / "gates.json").read_text(encoding="utf-8"))
    features = json.loads((out / "features.json").read_text(encoding="utf-8"))
    return gates, features, out


def partition_faults(features: dict) -> list[str]:
    """What is wrong with a written split of the knowable columns, read from the file alone."""
    kept = {features["derived"].get(name, name) for name in features["kept"]}
    dropped = set(features["dropped"])
    faults = [f"in both: {name}" for name in sorted(kept & dropped)]
    faults += [f"lost: {name}" for name in sorted(lcf.origination_knowable() - kept - dropped)]
    return faults


def test_the_written_split_is_a_partition_of_the_knowable_columns(tmp_path):
    _, features, out = run(tmp_path, book())
    assert partition_faults(features) == []
    assert features["kept"] == list(feature_names())
    assert features["kept"] == features["matrix"]["columns"]
    assert set(features["matrix"]["dtypes"]) == set(features["kept"])
    assert features["partition"]["knowable"] == len(lcf.origination_knowable())
    by_gate = features["dropped_by_gate"]
    assert set(by_gate["coverage"]) == set(LATE_COVERAGE)
    assert set(by_gate["values"]) == set(VALUE_CARRIERS)
    assert set(by_gate["redundancy"]) == {"funded_amnt", "funded_amnt_inv", "fico_range_high",
                                          "grade", *CALENDAR_CARRIERS}
    assert sum(len(names) for names in by_gate.values()) == len(features["dropped"])
    assert set(features["caps"]) == set(CLIPPED)
    assert features["caps"]["dti"]["declared"] == list(CLIPPED["dti"])
    assert features["constants"]["FIRST_QUARTER"] == FIRST_QUARTER
    assert (out / "dropped-columns.png").stat().st_size > 0

    # The file-level check catches a column written on both sides and one written on neither.
    doubled = json.loads(json.dumps(features))
    doubled["dropped"]["dti"] = {"gate": "values"}
    assert partition_faults(doubled) == ["in both: dti"]
    thinned = json.loads(json.dumps(features))
    del thinned["dropped"]["tax_liens"]
    assert partition_faults(thinned) == ["lost: tax_liens"]

    # And the run's own check refuses both before anything is written.
    kept = features["kept"]
    with pytest.raises(SystemExit, match="in both"):
        lcf.partition(kept, {**features["dropped"], "dti": {}}, lcf.origination_knowable())
    fewer = {k: v for k, v in features["dropped"].items() if k != "tax_liens"}
    with pytest.raises(SystemExit, match="tax_liens"):
        lcf.partition(kept, fewer, lcf.origination_knowable())
    # The derived duration stands for its raw date; dropping that date too is a double count.
    with pytest.raises(SystemExit, match="earliest_cr_line"):
        lcf.partition(kept, {**features["dropped"], "earliest_cr_line": {}},
                      lcf.origination_knowable())


def test_a_column_that_begins_late_is_dropped_by_coverage_with_the_measured_onset(tmp_path):
    _, features, _ = run(tmp_path, book(late_onset=2, probe_onset=5), "early")
    record = features["dropped"]["open_il_12m"]
    assert record["gate"] == "coverage"
    # The list declares 2016Q1; the book says 2011Q3, and the book is what is written.
    assert record["declared_onset"] == LATE_COVERAGE["open_il_12m"] == "2016Q1"
    assert record["onset"] == QUARTERS[5]
    assert record["first_quarter_share"] == 0.0
    assert features["coverage_onsets"] == {
        QUARTERS[2]: sorted(set(LATE_COVERAGE) - {"open_il_12m"}),
        QUARTERS[5]: ["open_il_12m"],
    }

    # Moving the column's first value one quarter later moves its written onset with it.
    _, later, _ = run(tmp_path, book(late_onset=2, probe_onset=6), "later")
    assert later["dropped"]["open_il_12m"]["onset"] == QUARTERS[6]
    assert later["coverage_onsets"][QUARTERS[6]] == ["open_il_12m"]
    assert features["dropped"]["mort_acc"]["onset"] == later["dropped"]["mort_acc"]["onset"]


def test_gates_json_is_the_reports_called_directly(tmp_path):
    frame = book()
    gates, _, _ = run(tmp_path, frame)
    source = tmp_path / "run.csv"
    loaded = gbm_builds.load(source)
    direct = {
        "redundancy": redundancy_report(loaded),
        "coverage": coverage_report(loaded),
        "values": value_report(loaded),
    }
    assert gates == json.loads(json.dumps(direct, default=str))
    assert set(CALENDAR_CARRIERS) <= set(gates["redundancy"])
    assert "share_pinned" in gates["values"]["dti"]["clip"]

    # A report read on another book is not the one written: the comparison sees a
    # single loan's capped amount moved back inside the cap.
    other = loaded.copy()
    other.loc[len(other) - 1, "loan_amnt"] = 20000.0
    moved = {**direct, "values": value_report(other)}
    assert gates != json.loads(json.dumps(moved, default=str))
