"""The model matrix: what every model in the study is shown, and nothing else.

`lending_club.py` says which of the 151 columns are knowable at origination.
That set is not yet a model matrix. Three things stand between them, and each
is a decision that has to be made once, for every model, rather than inside
whichever model happens to need it first:

  * **Free text.** `emp_title` carries 512,694 distinct strings across the
    book, `desc` 124,500 and `title` 63,154. Binned as a categorical any of
    them becomes a lookup table; handed to a gradient booster, a
    high-cardinality split; handed to a foundation model in 50,000 rows of
    context, noise with a large alphabet. Text features are a study of their
    own and this is not it, so all three are out.
  * **Redundant pairs.** Four columns are transforms of another column rather
    than characteristics in their own right: `funded_amnt` is `loan_amnt`,
    `funded_amnt_inv` is `loan_amnt` up to the part investors funded,
    `fico_range_high` is `fico_range_low` plus a constant, and `grade` is the
    first character of `sub_grade`. Keeping both members of such a pair puts
    two near-identical columns into a logistic regression whose coefficient
    stability across vintages is one of the things being measured, and the
    instability would be the encoding's rather than the book's. The identities
    are asserted on the data by `redundancy_report`, not assumed here.
  * **Dates that are not the axis.** `earliest_cr_line` is a calendar date and
    a scorecard wants the duration it implies. It becomes
    `credit_history_months`, the months from the first credit line to
    origination, and the same for the co-applicant. This uses `issue_d`
    arithmetically without letting calendar time into the matrix as a feature.

Two more columns are dropped for carrying the calendar. Lending Club prices by
a rate table indexed on sub-grade and month, so within one origination month
and one sub-grade `int_rate` is the table's rate on 94.7% of the book; given
`sub_grade`, what is left of the rate is mostly the month the loan was written.
`installment` is the level-payment amortisation of amount, rate and term and
carries the rate with it. A model that reads either can date a loan, and dating
the loan is reading the regime. Both identities are measured on the book by
`redundancy_report` before any model is fitted.

The largest exclusion is for the same reason and is easier to miss, because the
calendar is carried by the *absence* of a value rather than by a value. Lending
Club added bureau attributes to its files in batches — thirty-seven columns
from 2012Q2 to 2012Q4, one in 2013Q2, fourteen in 2016Q1, sixteen with the
joint applications of 2017Q3 — and before its batch date a column is empty on
every loan. Inside an expanding training pool that starts in 2010, "missing"
on any of those columns means "originated before the batch", a binner turns
that into a bin, and the bin is a vintage indicator with a default rate
attached. Out of time nobody is in it. So the rule is uniform coverage: a
column stays only if it is populated from the first cohort of the usable book
onward. `LATE_COVERAGE` lists the sixty-eight that are not, with the quarter
each begins, and `coverage_report` re-measures every column on the book being
used and refuses to proceed if the list and the data disagree in either
direction.

Coverage by presence is not enough, because a value can arrive late while the
column was there all along. Five bureau counts — `tax_liens`,
`collections_12_mths_ex_med`, `chargeoff_within_12_mths`, `acc_now_delinq`,
`delinq_amnt` — read zero on every loan through 2012Q3 and take their first
non-zero value in 2012Q4: the file was back-filled with zeros where the field
was not yet collected. `initial_list_status` has one level until the
whole-loan programme of 2012Q4, `application_type` one level until the joint
applications of 2015Q4, `disbursement_method` one level until 2016Q1. On a
training pool that straddles the date, `tax_liens > 0` or `'w'` is "originated
after", exactly as a missing bin was, and a booster with no bin-size floor
splits on it. `addr_state` is the same thing by degrees: Lending Club entered
states one at a time, and 8% of the book sits in a state that did not exist in
the first cohort. Two numeric columns carry the calendar in their range rather
than their support — Lending Club's caps on `dti` moved 25 → 30 → 35 → 40 and
on `loan_amnt` 25,000 → 35,000 → 40,000 — so a value above the first cohort's
cap dates a loan as surely as a level does; 23% and 13% of the book sit above
those caps.

So the rule is uniform coverage *by value*: every value or level the matrix
holds must exist in the first cohort of the book. A column constant in the
first cohort, or carrying a late level on more than `VALUE_FLOOR` of the book,
is out — `VALUE_CARRIERS` lists the nine. A numeric column whose range grows is
clipped to the first cohort's support — `CLIPPED` holds the two bounds. Late
values under the floor (a rare state of `home_ownership`, one loan purpose)
are left alone, since a split that isolates a fiftieth of a percent of the
book has no default-rate leverage to date anything with. `value_report`
re-measures all of it on the book being used and refuses a disagreement. The
first cohort is 2010Q2 rather than 2010Q1 because the 60-month product was
launched in May 2010, and a book starting one quarter earlier would have to
drop `term` under the same rule. What survives is twenty columns: the
application and bureau set Lending Club reported, in full, from the start.

`zip_code` is dropped on a narrower argument. It holds 956 three-digit
prefixes, a tenth of a percent of the book each, and it would be refitted
inside every build; a bin whose membership is that thin moves between vintages
because the sample moved, not because the risk did, and this study reads
exactly that kind of movement as a result.

Two columns are ordinal strings and are mapped to numbers rather than binned as
unordered categories, so that a monotonic binning has something to be monotonic
in: `sub_grade` to 1..35 and `emp_length` to 0..10.

Everything here applies to every model in the study. A column dropped for the
scorecard and kept for the booster would make the comparison a comparison of
feature sets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .lending_club import AXIS, FEATURE_AVAILABILITY
from .splits import LeakageError, assert_features_knowable

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pandas as pd

# Free text. Out of the matrix for every model, and named so a reader can see
# what was given up rather than discovering it from a column count.
FREE_TEXT: frozenset[str] = frozenset({"emp_title", "title", "desc"})

# Geography below the state. See the module docstring for why it is not here.
FINE_GEOGRAPHY: frozenset[str] = frozenset({"zip_code"})

# Column -> the column it duplicates. `redundancy_report` measures each of
# these on the book being used and the run records what it measured.
REDUNDANT: dict[str, str] = {
    "funded_amnt": "loan_amnt",
    "funded_amnt_inv": "loan_amnt",
    "fico_range_high": "fico_range_low",
    "grade": "sub_grade",
}

# Columns that are a function of another column *and the calendar*. Lending
# Club prices by a rate table indexed on sub-grade and month: within one
# origination month and one sub-grade the interest rate is the table's rate on
# 94.7% of the book, so given `sub_grade` the residual of `int_rate` is mostly
# the month the loan was written. `installment` is the amortisation of amount,
# rate and term, and carries the rate. Either column lets a model date a loan,
# and the whole point of removing the axis from the matrix is that no model
# can. Both are dropped for every model, and `redundancy_report` measures the
# two identities rather than assuming them.
CALENDAR_CARRIERS: dict[str, str] = {
    "int_rate": "sub_grade and the origination month",
    "installment": "loan_amnt, int_rate and term",
}

# Columns Lending Club began reporting after the first cohort of the usable
# book, keyed to the quarter their coverage first reaches half of its eventual
# level. Before that quarter every loan is missing the value, so on a training
# pool that straddles it the missing bin is an origination-date indicator.
# Measured on the book; `coverage_report` re-measures and refuses a mismatch.
LATE_COVERAGE: dict[str, str] = {
    **dict.fromkeys((
        "acc_open_past_24mths", "bc_open_to_buy", "bc_util", "mort_acc",
        "mths_since_recent_bc", "mths_since_recent_inq",
        "mths_since_recent_revol_delinq", "percent_bc_gt_75",
        "total_bal_ex_mort", "total_bc_limit",
    ), "2012Q2"),
    **dict.fromkeys(("num_bc_sats", "num_sats"), "2012Q3"),
    **dict.fromkeys((
        "avg_cur_bal", "mo_sin_old_il_acct", "mo_sin_old_rev_tl_op",
        "mo_sin_rcnt_rev_tl_op", "mo_sin_rcnt_tl", "mths_since_last_major_derog",
        "mths_since_recent_bc_dlq", "num_accts_ever_120_pd", "num_actv_bc_tl",
        "num_actv_rev_tl", "num_bc_tl", "num_il_tl", "num_op_rev_tl",
        "num_rev_accts", "num_rev_tl_bal_gt_0", "num_tl_120dpd_2m",
        "num_tl_30dpd", "num_tl_90g_dpd_24m", "num_tl_op_past_12m",
        "pct_tl_nvr_dlq", "tot_coll_amt", "tot_cur_bal", "tot_hi_cred_lim",
        "total_il_high_credit_limit", "total_rev_hi_lim",
    ), "2012Q4"),
    "mths_since_last_record": "2013Q2",
    **dict.fromkeys((
        "all_util", "il_util", "inq_fi", "inq_last_12m", "max_bal_bc",
        "mths_since_rcnt_il", "open_acc_6m", "open_act_il", "open_il_12m",
        "open_il_24m", "open_rv_12m", "open_rv_24m", "total_bal_il",
        "total_cu_tl",
    ), "2016Q1"),
    **dict.fromkeys((
        "annual_inc_joint", "dti_joint", "revol_bal_joint",
        "sec_app_chargeoff_within_12_mths", "sec_app_collections_12_mths_ex_med",
        "sec_app_earliest_cr_line", "sec_app_fico_range_high",
        "sec_app_fico_range_low", "sec_app_inq_last_6mths", "sec_app_mort_acc",
        "sec_app_mths_since_last_major_derog", "sec_app_num_rev_accts",
        "sec_app_open_acc", "sec_app_open_act_il", "sec_app_revol_util",
        "verification_status_joint",
    ), "2017Q3"),
}

# The share of a column's peak quarterly coverage it must reach in the first
# cohort of the book to count as present from the start.
COVERAGE_FLOOR = 0.5

# The first cohort of the usable book, and the reference every value rule is
# measured against. Later than the first quarter Lending Club wrote loans in
# 2010 because the 60-month product appeared in May of that year; the vintage
# grid reads its first cohort from here.
FIRST_QUARTER = "2010Q2"

# The share of the book a value absent from the first cohort may reach before
# the column carrying it is treated as a calendar carrier.
VALUE_FLOOR = 0.05

# Columns whose values, rather than whose presence, begin after the first
# cohort: constant on every loan of the first cohort, or carrying a level that
# did not exist then on more than `VALUE_FLOOR` of the book. Each maps to what
# was measured; `value_report` re-measures and refuses a mismatch.
VALUE_CARRIERS: dict[str, str] = {
    **dict.fromkeys((
        "acc_now_delinq", "chargeoff_within_12_mths", "collections_12_mths_ex_med",
        "delinq_amnt", "tax_liens",
    ), "zero on every loan before 2012Q4"),
    "initial_list_status": "one level before the whole-loan programme of 2012Q4",
    "application_type": "one level before the joint applications of 2015Q4",
    "disbursement_method": "one level before 2016Q1",
    "addr_state": "states entered after the first cohort hold 8% of the book",
}

# Numeric columns whose range grew with a policy cap, clipped to the support of
# the first cohort so that a value above the old cap no longer dates a loan.
# The bounds are the first cohort's minimum and maximum; `value_report` checks
# them against the book.
CLIPPED: dict[str, tuple[float, float]] = {
    "dti": (0.0, 24.99),
    "loan_amnt": (1000.0, 25000.0),
}

# Credit-line dates, and the durations they become. The value is months from
# the date in the column to origination. The co-applicant's line is not here:
# it arrives with the joint applications of 2017Q3 and is out with them.
DATE_TO_DURATION: dict[str, str] = {
    "earliest_cr_line": "credit_history_months",
}

# Ordinal strings, and the numbers behind them.
SUB_GRADE_LETTERS = "ABCDEFG"
EMP_LENGTH_YEARS: dict[str, int] = {
    "< 1 year": 0,
    "1 year": 1,
    "2 years": 2,
    "3 years": 3,
    "4 years": 4,
    "5 years": 5,
    "6 years": 6,
    "7 years": 7,
    "8 years": 8,
    "9 years": 9,
    "10+ years": 10,
}

# The month-year format Lending Club writes every date column in.
MONTH_YEAR = "%b-%Y"

# Every unordered categorical among the origination-knowable columns, whether
# or not the matrix keeps it. `categorical_names` filters this by the matrix.
DECLARED_CATEGORICAL: tuple[str, ...] = (
    "addr_state",
    "application_type",
    "disbursement_method",
    "home_ownership",
    "initial_list_status",
    "purpose",
    "verification_status",
)

DROPPED: frozenset[str] = (
    FREE_TEXT
    | FINE_GEOGRAPHY
    | frozenset(REDUNDANT)
    | frozenset(CALENDAR_CARRIERS)
    | frozenset(LATE_COVERAGE)
    | frozenset(VALUE_CARRIERS)
)

# The derived columns are knowable at origination because both of their sources
# are, which is checked rather than asserted in prose.
AVAILABILITY: dict[str, int] = {
    **FEATURE_AVAILABILITY,
    **{derived: 0 for derived in DATE_TO_DURATION.values()},
}


class FeatureError(AssertionError):
    """A model matrix that does not describe what a lender knew at origination."""


for _source, _derived in DATE_TO_DURATION.items():
    if FEATURE_AVAILABILITY.get(_source, 1) > 0:
        raise FeatureError(
            f"{_derived} is derived from {_source}, which is not knowable at "
            f"origination"
        )
del _source, _derived


def feature_names() -> tuple[str, ...]:
    """The columns of the model matrix, sorted, before any per-build screen."""
    kept = {
        name
        for name, offset in FEATURE_AVAILABILITY.items()
        if offset <= 0 and name not in DROPPED and name not in DATE_TO_DURATION
    }
    return tuple(sorted(kept | set(DATE_TO_DURATION.values())))


def categorical_names() -> tuple[str, ...]:
    """The columns optbinning must treat as unordered categories.

    Declared rather than inferred from dtype. A dtype is a property of how the
    file was read, and a study whose binning changes when pandas changes its
    string backend is not reproducible. Only the ones the matrix keeps are
    returned; the declaration itself covers every categorical the file has,
    so that a column dropped and later restored does not arrive as a number.
    """
    kept = set(feature_names())
    return tuple(name for name in DECLARED_CATEGORICAL if name in kept)


def _months_between(later, earlier):
    """Whole months from `earlier` to `later`, as a float column with NaN."""
    return (later.dt.year - earlier.dt.year) * 12 + (later.dt.month - earlier.dt.month)


def model_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """Builds the matrix every model in the study is fitted and scored on.

    Takes the raw Lending Club frame, which must carry `issue_d` because two
    features are durations measured to it, and returns a new frame holding
    `feature_names()` and nothing else. The axis itself does not survive into
    the result: a model that can read the calendar can read the regime, and
    reading the regime is the thing being tested.
    """
    import pandas as pd

    if AXIS not in frame.columns:
        raise FeatureError(f"the matrix needs {AXIS} to measure durations against it")

    missing = [
        name
        for name in feature_names()
        if name not in frame.columns and name not in DATE_TO_DURATION.values()
    ]
    if missing:
        raise FeatureError(f"{len(missing)} declared features are absent: {missing[:10]}")

    issued = frame[AXIS]
    if not pd.api.types.is_datetime64_any_dtype(issued):
        issued = pd.to_datetime(issued, format=MONTH_YEAR, errors="coerce")

    out = pd.DataFrame(index=frame.index)
    categorical = set(categorical_names())

    for name in feature_names():
        if name in DATE_TO_DURATION.values():
            continue
        column = frame[name]
        if name == "sub_grade":
            out[name] = _sub_grade_ordinal(column)
        elif name == "emp_length":
            out[name] = column.map(EMP_LENGTH_YEARS).astype("float64")
        elif name == "term":
            out[name] = column.str.extract(r"(\d+)", expand=False).astype("float64")
        elif name in categorical:
            # Object rather than an extension dtype: optbinning reads the
            # underlying numpy array and a categorical column has to arrive as
            # one whatever the reader produced.
            out[name] = column.astype(object)
        else:
            out[name] = pd.to_numeric(column, errors="coerce").astype("float64")
        if name in CLIPPED:
            low, high = CLIPPED[name]
            out[name] = out[name].clip(lower=low, upper=high)

    for source, derived in DATE_TO_DURATION.items():
        opened = frame[source]
        if not pd.api.types.is_datetime64_any_dtype(opened):
            opened = pd.to_datetime(opened, format=MONTH_YEAR, errors="coerce")
        out[derived] = _months_between(issued, opened).astype("float64")

    out = out[list(feature_names())]
    assert_features_knowable(AVAILABILITY, list(out.columns))
    return out


def _sub_grade_ordinal(column):
    """A1..G5 as 1..35, and anything else as missing."""
    import pandas as pd

    text = column.astype(object)
    values = []
    for value in text:
        if not isinstance(value, str) or len(value) != 2:
            values.append(float("nan"))
            continue
        letter, number = value[0], value[1]
        if letter not in SUB_GRADE_LETTERS or not number.isdigit():
            values.append(float("nan"))
            continue
        step = int(number)
        if not 1 <= step <= 5:
            values.append(float("nan"))
            continue
        values.append(SUB_GRADE_LETTERS.index(letter) * 5 + step)
    return pd.Series(values, index=column.index, dtype="float64")


def informative(matrix: pd.DataFrame, rows) -> tuple[str, ...]:
    """The columns that distinguish one of the rows given from another.

    A column that holds one value on a build's training rows gives a binner
    nothing to split. Which columns are like that is a property of the training
    rows and is therefore computed on them, never on the book — reading the
    whole book to decide what to fit would be a decision taken with information
    the builder did not have.

    Missingness counts as a value, because on this book it usually is one:
    `mths_since_last_delinq` is absent for half the loans and its absence means
    the borrower has no delinquency on record, which is the strongest thing the
    column says. A column holding a single value and nothing else carries
    nothing and is dropped; the same column with some rows missing separates
    those rows from the rest and is kept.
    """
    positions = list(rows)
    if not positions:
        raise FeatureError("no rows to screen features on")
    subset = matrix.iloc[positions]
    kept = []
    for name in matrix.columns:
        column = subset[name]
        distinct = int(column.nunique(dropna=True))
        if distinct == 0:
            continue
        if distinct > 1 or bool(column.isna().any()):
            kept.append(name)
    return tuple(kept)


def redundancy_report(frame: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Measures each pair in `REDUNDANT` on the book actually being used.

    The pairs are dropped on the strength of an identity, and an identity that
    holds on a sample is a hypothesis. This returns the agreement rate of every
    pair so that a run records what it was true of, and it raises if a pair is
    not close enough to identical to justify having dropped one of them.
    """
    import pandas as pd

    out: dict[str, dict[str, float]] = {}
    for dropped, kept in REDUNDANT.items():
        if dropped not in frame.columns or kept not in frame.columns:
            raise FeatureError(f"cannot check {dropped} against {kept}: column absent")
        left, right = frame[dropped], frame[kept]
        if dropped == "grade":
            agreement = float((left.astype(object) == right.astype(str).str[0]).mean())
            report = {"exact_agreement": round(agreement, 6)}
        elif dropped == "fico_range_high":
            offsets = (
                pd.to_numeric(left, errors="coerce")
                - pd.to_numeric(right, errors="coerce")
            ).dropna()
            report = {
                "distinct_offsets": float(offsets.nunique()),
                "offset_min": float(offsets.min()),
                "offset_max": float(offsets.max()),
                "exact_agreement": float((offsets == offsets.mode().iloc[0]).mean()),
            }
        else:
            numeric_left = pd.to_numeric(left, errors="coerce")
            numeric_right = pd.to_numeric(right, errors="coerce")
            report = {
                "exact_agreement": float((numeric_left == numeric_right).mean()),
                "correlation": round(float(numeric_left.corr(numeric_right)), 6),
            }
        out[dropped] = {"duplicates": kept, **report}

    for dropped, report in out.items():
        agreement = report.get("exact_agreement", 0.0)
        correlation = report.get("correlation", 0.0)
        if agreement < 0.9 and correlation < 0.99:
            raise FeatureError(
                f"{dropped} was dropped as a duplicate of {report['duplicates']} and "
                f"is not one on this book: agreement {agreement:.4f}, correlation "
                f"{correlation:.4f}"
            )

    out.update(_calendar_carrier_report(frame))
    return out


def _calendar_carrier_report(frame: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Measures the two identities behind `CALENDAR_CARRIERS`.

    For `int_rate` the statement is that the rate is constant within one
    origination month and one sub-grade, so the reported number is the share
    of rows whose rate equals the modal rate of their (month, sub-grade) cell.
    For `installment` it is the level-payment amortisation of amount, rate and
    term, and the number is the share of rows within five cents of it. Either
    identity failing on a book means the column is not what it is dropped for
    being, and the run must not proceed on an argument that no longer holds.
    """
    import pandas as pd

    for name in ("int_rate", "installment", "sub_grade", "loan_amnt", "term", AXIS):
        if name not in frame.columns:
            raise FeatureError(f"cannot check the calendar carriers: {name} absent")

    issued = frame[AXIS]
    if not pd.api.types.is_datetime64_any_dtype(issued):
        issued = pd.to_datetime(issued, format=MONTH_YEAR, errors="coerce")
    rate = pd.to_numeric(frame["int_rate"], errors="coerce")
    cells = pd.DataFrame({
        "month": issued.dt.year * 12 + issued.dt.month,
        "sub_grade": frame["sub_grade"].astype(object),
        "rate": rate,
    }).dropna()
    modal = cells.groupby(["month", "sub_grade"])["rate"].transform(
        lambda s: s.mode().iloc[0]
    )
    rate_agreement = float((cells["rate"] == modal).mean())

    amount = pd.to_numeric(frame["loan_amnt"], errors="coerce")
    months = pd.to_numeric(
        frame["term"].astype(object).str.extract(r"(\d+)", expand=False), errors="coerce"
    )
    monthly = rate / 1200.0
    formula = amount * monthly / (1.0 - (1.0 + monthly) ** (-months))
    gap = (pd.to_numeric(frame["installment"], errors="coerce") - formula).abs().dropna()
    installment_agreement = float((gap <= 0.05).mean())

    out = {
        "int_rate": {
            "duplicates": CALENDAR_CARRIERS["int_rate"],
            "exact_agreement": round(rate_agreement, 6),
        },
        "installment": {
            "duplicates": CALENDAR_CARRIERS["installment"],
            "exact_agreement": round(installment_agreement, 6),
            "median_abs_gap": round(float(gap.median()), 6),
        },
    }
    for name, report in out.items():
        if report["exact_agreement"] < 0.9:
            raise FeatureError(
                f"{name} was dropped as a function of {report['duplicates']} and is "
                f"not one on this book: agreement {report['exact_agreement']:.4f}"
            )
    return out


def coverage_report(
    frame: pd.DataFrame, *, first_quarter: str = FIRST_QUARTER, last_quarter: str = "2018Q1"
) -> dict[str, dict]:
    """Measures when every column begins on the book, and checks `LATE_COVERAGE`.

    For each column the matrix reads or drops for coverage, the share of loans
    carrying a value is computed per origination quarter inside the usable
    book. A column is present from the start if its share in the first quarter
    is at least `COVERAGE_FLOOR` of its peak share. Every column the matrix
    keeps must pass that test and every column in `LATE_COVERAGE` must fail it;
    either way round, a disagreement means the list was measured on a different
    file from the one being used, and the run stops rather than proceed on a
    rule that does not hold.
    """
    import pandas as pd

    if AXIS not in frame.columns:
        raise FeatureError(f"the coverage check needs {AXIS}")
    issued = frame[AXIS]
    if not pd.api.types.is_datetime64_any_dtype(issued):
        issued = pd.to_datetime(issued, format=MONTH_YEAR, errors="coerce")
    quarter = issued.dt.year.astype("Int64").astype(str) + "Q" + issued.dt.quarter.astype(
        "Int64"
    ).astype(str)
    inside = (quarter >= first_quarter) & (quarter <= last_quarter) & issued.notna()

    raw_kept = [n for n in feature_names() if n not in DATE_TO_DURATION.values()]
    raw_kept += list(DATE_TO_DURATION)
    names = sorted(set(raw_kept) | set(LATE_COVERAGE))
    absent = [n for n in names if n not in frame.columns]
    if absent:
        raise FeatureError(f"cannot measure coverage: {absent[:10]} absent")

    share = frame.loc[inside, names].notna().groupby(quarter[inside]).mean().sort_index()
    out: dict[str, dict] = {}
    disagreements = []
    for name in names:
        column = share[name]
        peak = float(column.max())
        first = float(column.iloc[0])
        onset = None
        if peak > 0:
            reached = column[column >= COVERAGE_FLOOR * peak]
            onset = str(reached.index[0]) if len(reached) else None
        from_start = peak > 0 and first >= COVERAGE_FLOOR * peak
        declared_late = name in LATE_COVERAGE
        out[name] = {
            "onset": onset,
            "first_quarter_share": round(first, 4),
            "peak_share": round(peak, 4),
            "kept": not declared_late,
        }
        if declared_late == from_start:
            disagreements.append((name, onset, declared_late))
    if disagreements:
        raise FeatureError(
            f"{len(disagreements)} columns disagree with LATE_COVERAGE on this book "
            f"(name, measured onset, listed as late): {disagreements[:8]}"
        )
    return out


def _value_onset(column, first, quarter, *, categorical: bool) -> dict:
    """How much of a column lies outside what its first cohort held, and since when."""
    import pandas as pd

    present = column.notna()
    head = column[first & present]
    if categorical:
        levels = set(head.unique())
        outside = present & ~column.isin(levels)
        distinct = len(levels)
        support = sorted(str(level) for level in levels)
    else:
        distinct = int(head.nunique())
        if distinct <= 1:
            outside = present & (column != head.iloc[0]) if len(head) else present
            support = [float(head.iloc[0])] if len(head) else []
        else:
            low, high = float(head.min()), float(head.max())
            outside = present & ((column < low) | (column > high))
            support = [low, high]
    share = float(outside.sum() / present.sum()) if present.any() else 0.0
    onset = str(pd.Series(quarter[outside]).min()) if outside.any() else None
    return {
        "distinct_in_first_cohort": distinct,
        "share_outside_first_cohort": round(share, 6),
        "onset": onset,
        "first_cohort_support": support,
    }


def value_report(
    frame: pd.DataFrame, *, first_quarter: str = FIRST_QUARTER, last_quarter: str = "2018Q1"
) -> dict[str, dict]:
    """Measures whether any value the matrix holds could date a loan, and checks the lists.

    For every column the matrix keeps, after its transforms and its clipping,
    the share of the book carrying a value or level that the first cohort did
    not hold; the same for every column `VALUE_CARRIERS` drops, measured raw.
    A kept column may not be constant in the first cohort and vary later, and
    may not exceed `VALUE_FLOOR`; a dropped column must fail one of those two
    tests, or the list was measured on another book; and the bounds in
    `CLIPPED` must be the first cohort's own minimum and maximum. Any
    disagreement stops the run.
    """
    import pandas as pd

    if AXIS not in frame.columns:
        raise FeatureError(f"the value check needs {AXIS}")
    issued = frame[AXIS]
    if not pd.api.types.is_datetime64_any_dtype(issued):
        issued = pd.to_datetime(issued, format=MONTH_YEAR, errors="coerce")
    quarter = issued.dt.year.astype("Int64").astype(str) + "Q" + issued.dt.quarter.astype(
        "Int64"
    ).astype(str)
    inside = (quarter >= first_quarter) & (quarter <= last_quarter) & issued.notna()
    if not inside.any():
        raise FeatureError(f"no rows fall in {first_quarter}..{last_quarter}")

    absent = [n for n in VALUE_CARRIERS if n not in frame.columns]
    if absent:
        raise FeatureError(f"cannot measure value onsets: {absent} absent")

    book = frame.loc[inside]
    quarters = quarter.loc[inside].to_numpy()
    first = (quarter.loc[inside] == first_quarter).to_numpy()
    if not first.any():
        raise FeatureError(f"the book holds no rows in its first cohort {first_quarter}")

    matrix = model_matrix(book)
    categorical = set(DECLARED_CATEGORICAL)
    out: dict[str, dict] = {}
    disagreements: list[tuple[str, str]] = []

    for name in matrix.columns:
        report = _value_onset(matrix[name], first, quarters, categorical=name in categorical)
        report["kept"] = True
        out[name] = report
        constant_then_varies = (
            report["distinct_in_first_cohort"] <= 1
            and report["share_outside_first_cohort"] > 0
        )
        if constant_then_varies:
            disagreements.append((name, "kept, but constant in the first cohort and not after"))
        elif report["share_outside_first_cohort"] > VALUE_FLOOR:
            disagreements.append((name, "kept, but over the value floor"))

    for name, reason in VALUE_CARRIERS.items():
        raw = book[name]
        is_categorical = raw.dtype == object or name in categorical
        column = raw.astype(object) if is_categorical else pd.to_numeric(raw, errors="coerce")
        report = _value_onset(column, first, quarters, categorical=is_categorical)
        report["kept"] = False
        report["reason"] = reason
        out[name] = report
        carrier = (
            report["distinct_in_first_cohort"] <= 1 and report["share_outside_first_cohort"] > 0
        ) or report["share_outside_first_cohort"] > VALUE_FLOOR
        if not carrier:
            disagreements.append((name, "listed as a value carrier and not one on this book"))

    for name, (low, high) in CLIPPED.items():
        raw = pd.to_numeric(book[name], errors="coerce")
        head = raw[first].dropna()
        measured = (float(head.min()), float(head.max()))
        # The share the clip moved, measured before it: after the clip the
        # column cannot lie outside its bounds, so that number says nothing.
        present = raw.notna().to_numpy()
        pinned = ((raw < low) | (raw > high)).to_numpy() & present
        out[name]["clip"] = {
            "declared": [low, high],
            "first_cohort": list(measured),
            "share_pinned": round(float(pinned.sum() / present.sum()), 6),
            "share_pinned_by_quarter": {
                str(q): round(float(v), 6)
                for q, v in pd.Series(pinned[present]).groupby(quarters[present]).mean().items()
            },
        }
        if abs(measured[0] - low) > 1e-9 or abs(measured[1] - high) > 1e-9:
            disagreements.append(
                (name, f"clipped to {(low, high)} but the first cohort spans {measured}")
            )

    if disagreements:
        raise FeatureError(
            f"{len(disagreements)} columns disagree with the value rule on this book: "
            f"{disagreements[:8]}"
        )
    return out


def assert_matrix_clean(matrix: pd.DataFrame) -> None:
    """The gate a runner calls before fitting anything on a matrix it was handed.

    Cheap, and it catches the failure that a frame passed through three
    functions no longer holds what its first caller thought: a servicing column
    reintroduced by a merge, the axis carried along as a feature, or a text
    column that was supposed to have been dropped.
    """
    columns = list(matrix.columns)
    if AXIS in columns:
        raise LeakageError(f"{AXIS} is the split axis and is not a feature")
    smuggled = sorted(set(columns) & DROPPED)
    if smuggled:
        raise FeatureError(f"columns dropped from the study are present: {smuggled}")
    assert_features_knowable(AVAILABILITY, columns)
