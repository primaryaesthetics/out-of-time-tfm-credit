"""The Freddie Mac single-family sample: its layout, and which column is knowable when.

The files carry no header row. Every column is identified by its position in
the July 2026 file layout (Release 47), so the two tuples below are the layout,
transcribed by hand and asserted against the files by width. A release that
moves a column changes the width or the meaning of a position, and either must
fail loudly here rather than let a shifted field through under the wrong name.
Release 47 did exactly that: it moved the mortgage-insurance cancellation
indicator and the servicer name from the origination file to the performance
file and appended a VantageScore column, so any parser written against an
earlier layout reads the wrong fields from these files.

There is no origination date in this dataset. Two things stand in for it, and
they are not the same thing:

  * The **origination quarter** is encoded in the loan identifier,
    ``PYYQnXXXXXXX``, where ``YYQn`` is the origination year and quarter. It is
    the cohort axis. It is a quarter, not a date, and a build that needs a
    date uses the first day of the quarter.
  * The **first payment date** is the month the first scheduled payment was
    due. It is the clock the performance window runs on: a loan is one month
    old in its first payment month. It usually falls one to three months after
    the origination quarter opens, and it does not always: seller-modified,
    converted and construction-to-permanent loans carry the date of the
    conversion, years later in a few cases. The lag is measured, not assumed.

Every origination column but four is knowable when the loan is written: the
identifier and the pre-HARP identifier are not features, and the two dates are
the calendar. Every performance column is the future. The label is built from
the performance file and from nothing else.

Missing values are sentinels rather than blanks on most numeric columns, and
the sentinel differs by column. `SENTINELS` lists them so that a 9999 credit
score is read as unknown rather than as an exceptional borrower.
"""

from __future__ import annotations

import re

# The origination file, in position order. Thirty-one fields, pipe-delimited,
# no header. Names are this repository's; the layout's attribute names are in
# the comment where the two differ enough to need a lookup.
ORIGINATION_COLUMNS: tuple[str, ...] = (
    "fico",                         # Classic FICO
    "first_payment_date",           # YYYYMM
    "first_time_homebuyer",         # Y / N / 9
    "maturity_date",                # YYYYMM
    "msa",                          # MSA or Metropolitan Division code
    "mi_pct",                       # Mortgage Insurance Percentage
    "units",                        # Number of Units
    "occupancy",                    # P / I / S / 9
    "cltv",                         # Original Combined Loan-to-Value
    "dti",                          # Original Debt-to-Income Ratio
    "upb",                          # Original UPB
    "ltv",                          # Original Loan-to-Value
    "rate",                         # Original Interest Rate
    "channel",                      # R / B / C / T / 9
    "prepayment_penalty",           # Y / N
    "amortization_type",            # FRM / ARM
    "state",                        # Property State
    "property_type",                # CP / CO / PU / SF / MH / 99
    "postal_code",                  # first three digits, 000 unknown
    "loan_id",                      # Loan Identifier, PYYQnXXXXXXX
    "purpose",                      # P / C / N / R / 9
    "term",                         # Original Loan Term, months
    "borrowers",                    # Number of Borrowers
    "seller",                       # Seller Name or OTHER
    "super_conforming",             # Y / N
    "pre_harp_loan_id",             # Pre-HARP Loan Sequence Number
    "special_eligibility_program",  # H / F / R / blank
    "harp",                         # HARP Indicator, Y / N
    "valuation_method",             # Property Valuation Method, 1..4 / 7
    "interest_only",                # Y / N
    "vantage_score",                # VantageScore 4.0
)

# The monthly performance file, in position order. Thirty-five fields.
PERFORMANCE_COLUMNS: tuple[str, ...] = (
    "loan_id",
    "period",                       # YYYYMM, the as-of month
    "current_upb",
    "delinquency_status",           # 00, 01, 02, ... capped at 99; RA; XX
    "loan_age",                     # Freddie Mac's, resets on modification
    "months_to_maturity",
    "defect_settlement_date",
    "modification_flag",            # Y / P / blank
    "zero_balance_code",            # 01, 02, 03, 09, 15, 16, 96
    "zero_balance_date",            # YYYYMM
    "current_rate",
    "current_non_interest_upb",
    "ddlpi",                        # Due Date of Last Paid Installment
    "mi_recoveries",
    "net_sales_proceeds",
    "non_mi_recoveries",
    "total_expenses",
    "legal_costs",
    "maintenance_costs",
    "taxes_and_insurance",
    "miscellaneous_expenses",
    "actual_loss",
    "cumulative_modification_costs",
    "rate_step_indicator",
    "payment_deferral_flag",
    "eltv",                         # Estimated Loan-to-Value
    "zero_balance_removal_upb",
    "delinquent_accrued_interest",
    "disaster_delinquency",
    "borrower_assistance_plan",
    "current_modification_costs",
    "current_interest_bearing_upb",
    "mi_cancellation",              # moved here in Release 47
    "servicer",                     # moved here in Release 47
    "bankruptcy_cramdown_costs",    # new in Release 47
)

# The cohort axis. Not a file column: derived from `loan_id` by
# `origination_quarter`, and never an input.
AXIS = "origination_quarter"

# The clock the label runs on. A calendar date, never an input.
VINTAGE_CLOCK = "first_payment_date"

# Identifiers. The pre-HARP identifier links a relief refinance to the loan it
# replaced; as a feature it would be a lookup into another row.
NON_FEATURES = frozenset({"loan_id", "pre_harp_loan_id"})

# Calendar columns. Knowable at origination and excluded for the same reason
# the origination date is: a model that reads either dates the loan. The term
# survives, because it is the difference between them without the calendar.
CALENDAR = frozenset({"first_payment_date", "maturity_date"})

# The performance columns the label is built from. Listed so that using one as
# a feature is a lookup failure rather than a silent success.
LABEL_SOURCES = frozenset({
    "loan_id", "period", "delinquency_status", "zero_balance_code",
    "zero_balance_date",
})

_ORIGINATION_FEATURES = tuple(
    name for name in ORIGINATION_COLUMNS
    if name not in NON_FEATURES and name not in CALENDAR
)

FEATURE_AVAILABILITY: dict[str, int] = {
    **{name: 0 for name in _ORIGINATION_FEATURES},
    # Every performance column is written during servicing. Thirty days
    # stands for "after origination"; the gate tests the sign.
    **{name: 30 for name in PERFORMANCE_COLUMNS if name != "loan_id"},
}

ALL_ORIGINATION_COLUMNS = (
    frozenset(_ORIGINATION_FEATURES) | NON_FEATURES | CALENDAR
)

# Value that means "not available", per column, from the user guide. Blank is
# also missing on every column and is handled by the reader.
SENTINELS: dict[str, str] = {
    "fico": "9999",
    "vantage_score": "9999",
    "first_time_homebuyer": "9",
    "mi_pct": "999",
    "units": "99",
    "occupancy": "9",
    "cltv": "999",
    "dti": "999",
    "ltv": "999",
    "channel": "9",
    "property_type": "99",
    "postal_code": "000",
    "purpose": "9",
    "borrowers": "99",
    "valuation_method": "7",
}

# A first payment due this many months or more after the origination quarter
# opens is not a settlement lag. The ordinary lag is one to four months: a
# loan written in the last month of a quarter with the first payment due two
# months later sits at four. Beyond that the date is the conversion or
# modification date the user guide describes, the loan's servicing record
# begins before it, and a window run from it is not a window from
# origination. Such loans are re-dated, and they are excluded from the label
# rather than measured on the wrong clock.
LATE_FIRST_PAYMENT_MONTHS = 6

_LOAN_ID = re.compile(r"^([AF])(\d\d)Q([1-4])\d{7}$")


def first_payment_lag(year: int, quarter: int, first_payment_yyyymm: int) -> int:
    """Months from the first month of the origination quarter to the first
    payment month. Zero means the first payment fell in the quarter's first
    month; negative means before the quarter opened."""
    start = year * 12 + (quarter - 1) * 3 + 1
    first = (first_payment_yyyymm // 100) * 12 + first_payment_yyyymm % 100
    return first - start


def origination_quarter(loan_id: str) -> tuple[int, int]:
    """The origination year and quarter encoded in a loan identifier.

    Two-digit years: the dataset starts in 1999, so 99 is 1999 and everything
    below is this century. Raises on anything that is not a loan identifier,
    because a row whose identifier does not parse has no cohort and must not
    be counted in one by accident.
    """
    match = _LOAN_ID.match(loan_id)
    if match is None:
        raise ValueError(f"not a loan identifier: {loan_id!r}")
    yy, quarter = int(match.group(2)), int(match.group(3))
    year = 1900 + yy if yy >= 90 else 2000 + yy
    return year, quarter


def safe_features() -> tuple[str, ...]:
    """The columns a model may see, sorted, with nothing else in them."""
    return tuple(sorted(
        name for name, offset in FEATURE_AVAILABILITY.items() if offset <= 0
    ))


def leaking_features() -> tuple[str, ...]:
    """The columns that would import the future, named so tests can use them."""
    return tuple(sorted(
        name for name, offset in FEATURE_AVAILABILITY.items() if offset > 0
    ))


def audit_widths(origination_width: int, performance_width: int) -> dict[str, int]:
    """Compares the field counts of the two files against the layout.

    Files without a header can only be checked by width. A release that adds
    or removes a field changes the width, and this is the check that turns
    that into an error rather than a shifted column read under another name.
    """
    return {
        "origination_expected": len(ORIGINATION_COLUMNS),
        "origination_found": origination_width,
        "performance_expected": len(PERFORMANCE_COLUMNS),
        "performance_found": performance_width,
    }


def widths_match(audit: dict[str, int]) -> bool:
    return (
        audit["origination_expected"] == audit["origination_found"]
        and audit["performance_expected"] == audit["performance_found"]
    )
