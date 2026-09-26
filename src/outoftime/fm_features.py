"""The Freddie Mac model matrix: what every model is shown on the second book.

`freddie_mac.py` says which of the thirty-one origination columns are knowable
when the loan is written, and `safe_features()` is that set. The matrix is
what survives three gates run on the whole book before any model is fitted —
redundancy, coverage by onset, and uniform coverage by value — under the rule
EXP-005 fixes. Every list below is measured by the report that enforces it,
which refuses to proceed when the list and the book disagree in either
direction; a matrix is not read off this docstring.

**Two columns out a priori.** `postal_code`, the first three digits of the
ZIP code, because geography stays at the state, on the argument `features.py`
makes for `zip_code`. `rate`, because on a book whose note rates fell from
eight percent to three and a half across the axis the rate is the calendar,
and the value rule below would clip it to nothing. The spread over the
month's market rate would be knowable at origination and needs a series the
dataset does not carry. `redundancy_report` still measures how much of the
rate's variance the cell of first payment month and term explains, so the
build record shows it, and the exclusion does not depend on the number.

**Sentinels.** Most numeric columns write "not available" as a number — a 9999
credit score, a 999 loan-to-value — and the number differs by column. The
loader lists them in `SENTINELS`, and every function here reads them as
missing before anything else sees the column.

**Coverage by onset.** As on Lending Club: a column whose share of loans
carrying a value in the first cohort is under half of its peak share begins
late, and its missing bin dates a loan. The valuation method, the special
eligibility programme and VantageScore 4.0, which carries its not-available
value on every loan of the sample, are out by it.

**The value rule, symmetric.** On a twenty-five-year axis a value dates a
loan by leaving as well as by arriving, so the Lending Club rule is made
symmetric, against 1999Q1 as the first cohort and 2023H2 as the last:

  * a column constant on the first cohort is out;
  * a level absent from the first cohort and present on more than
    `VALUE_FLOOR` of the book is out, and so is a level present on the first
    cohort, absent from the last, and carried by more than `VALUE_FLOOR` of
    the book;
  * a numeric range is clipped to the range the first and the last cohort
    share, on every numeric column, so that no value either end of the axis
    lacks can date a loan;
  * missingness is a level for the onset test, is exempt from the offset
    test, and removes a column when its share differs between the first and
    the last cohort by more than `VALUE_FLOOR` of the cohort;
  * late and departed levels under the floor are left alone.

`VALUE_DROPPED` names what the rule removes on this book, with the clause
that removes it, and `CLIPPED` the shared ranges; `value_report` measures the
rule on the book and refuses either list if it is not what the rule gives.

**What the rule removes on this book.** Besides the three late columns, which
it would remove too: the amortisation type, the interest-only flag, `harp`
and `super_conforming`, each constant on the first cohort; `seller`, whose
largest sellers are absent from it; `channel`, whose unspecified level is
carried by a fifth of the book and by no loan of the last cohort; `msa`,
missing on half the first cohort and a ninth of the last; and `dti`, missing
on one loan in eighteen of the first cohort and on none of the last, a
difference over the floor. EXP-005's Setting expected `dti` to stay, with
its missing level marking the relief refinances of 2009 to 2018, and did
not name `super_conforming`; its note of 2026-09-13 confirms both
removals under the rule, and `value_report` records the clause that
fires on each. The fifteen-column matrix with `dti` kept is the ablation
that note names, built by the same functions with `dti` taken out of
`VALUE_DROPPED` and its shared range added to `CLIPPED`.

**The loan amount, read against the year's limit.** `upb` is a nominal dollar
amount on a twenty-five-year axis, and nominal amounts rise with house
prices: clipped at the first cohort's ceiling it pins a small share of the
book and a large one of every recent cohort, and it tells a model the year
better than any other kept column does. The matrix carries `upb_to_limit` in
its place, the original balance over the baseline one-unit conforming loan
limit of the loan's origination year, `CONFORMING_LIMIT`, twenty-eight
statutory annual values with their sources. The limit is set for each year
before it begins and every loan of the book was written under it, so the
ratio is a quantity the underwriting read; the objection to the rate's spread
was a weekly market series the dataset does not carry, and a table of annual
statutory values is not that series. The year is read arithmetically, as
`features.py` reads `issue_d` for a duration, and does not survive into the
matrix. What the ratio does not remove is house prices: the limit tracks the
national average and stops in a downturn, so the crisis is in the column as
it is in `ltv`. The multi-unit schedule and the higher limits of Alaska,
Hawaii, Guam and the Virgin Islands are not applied; `units` and `state` are
columns of their own. `redundancy_report` records `calendar_share`, the share
of a column's variance between cells of first payment month and term, for
the rate, every kept numeric column and both forms of the amount, so the
record shows where each sits against the rate. The numeric columns kept are
clipped to their shared ranges.

**The ablations.** Every function that decides or checks the matrix takes
`ablation`. Under `dti_kept` the column `dti` is in the matrix, its missing
value left missing so that each model reads it as a level of its own, its
range clipped to `ABLATION_CLIPPED`; `value_report` then requires the rule
to disagree with the declaration on `dti` alone, on the missing-share clause
alone, and refuses any other disagreement. Under `upb_nominal` the loan
amount is in nominal dollars in place of the ratio, clipped to
`ABLATION_CLIPPED`: a change of form rather than of a clause, so
`value_report` checks `upb` as a kept numeric column and requires no clause
to fire on it. `assert_matrix_clean` refuses a matrix holding `dti` unless
`dti_kept` is declared, `upb` unless `upb_nominal` is, and `upb_to_limit`
under `upb_nominal`, so a run on either cannot forget to say so.

**What moves inside the axis.** The value rule reads the two ends of the
axis. `shift_report` reads the middle of it on the kept columns — the lowest
and highest missing share, how much of that missingness sits on a late level
of a dropped carrier, and the levels absent from the last cohort that some
half-year carries over the floor — and refuses nothing.

**Kept pairs.** `ltv` and `cltv` agree on most loans and are both kept. The
combined ratio is not a transform of the first: the difference is secondary
financing, which is a characteristic of the loan. `redundancy_report` records
their agreement.

Everything here applies to every model on this book, for the reason
`features.py` gives: a column dropped for one model and kept for another would
make the comparison a comparison of feature sets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .features import FeatureError, informative
from .freddie_mac import (
    AXIS,
    CALENDAR,
    FEATURE_AVAILABILITY,
    NON_FEATURES,
    SENTINELS,
    safe_features,
)
from .splits import LeakageError, assert_features_knowable

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pandas as pd

__all__ = [
    "FeatureError",
    "assert_matrix_clean",
    "calendar_share",
    "categorical_names",
    "coverage_report",
    "feature_names",
    "informative",
    "model_matrix",
    "redundancy_report",
    "shift_report",
    "value_report",
    "value_rule",
]

# Out before any rule runs, each for the reason in the module docstring.
A_PRIORI: dict[str, str] = {
    "postal_code": "geography below the state",
    "rate": "the calendar on this book",
}

# Pairs that agree on most loans and are both kept. `redundancy_report`
# measures them and refuses nothing.
KEPT_PAIRS: dict[str, str] = {"cltv": "ltv"}

# What the rate and every numeric column are measured against, for the record.
RATE_CELLS = "the first payment month and the loan term"

# Columns whose coverage begins after the first cohort, keyed to the half-year
# it first reaches half of its peak, or "never" for a column that holds no
# value anywhere on the book. `coverage_report` refuses a mismatch.
LATE_COVERAGE: dict[str, str] = {
    "special_eligibility_program": "2017H1",
    "valuation_method": "2020H1",
    "vantage_score": "never",
}

# The share of a column's peak coverage it must reach in the first cohort to
# count as present from the start. The same as `features.py`.
COVERAGE_FLOOR = 0.5

# The first cohort, the reference of every value test, and the last. The
# grid's own first and last cohorts are read from here by `vintage`.
FIRST_COHORT = "1999Q1"
LAST_COHORT = "2023H2"

# A twentieth: of the book for a late or a departed level, of the cohort for a
# difference in missing share. The same floor as `features.py`.
VALUE_FLOOR = 0.05

# What the value rule removes on this book, and the clause that removes it.
VALUE_DROPPED: dict[str, str] = {
    "amortization_type": "constant on the first cohort",
    "channel": "a level present on the first cohort and absent from the last",
    "dti": "missing share differs between the first and the last cohort",
    "harp": "constant on the first cohort",
    "interest_only": "constant on the first cohort",
    "msa": "missing share differs between the first and the last cohort",
    "seller": "a level absent from the first cohort",
    "super_conforming": "constant on the first cohort",
}

# The baseline conforming loan limit for a one-unit property in the
# contiguous states, by calendar year, in dollars. Set for each year before
# it begins; the loan's year is its origination year. Sources, read in full:
#   1999-2007: OFHEO, Report to Congress 2007, Table 26 "Loan Limits"
#              (https://www.fhfa.gov/document/d/cll/loanlimitshistory07), and
#              OFHEO Mortgage Market Note 07-2, 2007-10-16
#              (https://www.fhfa.gov/media/32966), for the statute and the
#              MIRS indexing through 2008.
#   2008-2016: HERA §1124, 12 U.S.C. 1454(a)(2), as quoted in FHFA's CLL
#              FAQs (updated November 2025, https://www.fhfa.gov/document/d/
#              cll/fhfa-cll-faqs-2026.pdf): "shall not exceed $417,000",
#              held there "from 2006 until 2017" because the statute does
#              not let the baseline fall.
#   2017-2026: FHFA's annual announcements of 2016-11-23, 2017-11-28,
#              2018-11-27, 2019-11-26, 2020-11-24, 2021-11-30, 2023-11-28,
#              2024-11-26 and 2025-11-25, each stating the new value and the
#              one it rose from (2023's value, 726,200, is the 2024 release's
#              "an increase of $40,350 from 2023" against 766,550; the 2023
#              release itself was not reached).
CONFORMING_LIMIT: dict[int, int] = {
    1999: 240_000, 2000: 252_700, 2001: 275_000, 2002: 300_700, 2003: 322_700,
    2004: 333_700, 2005: 359_650, 2006: 417_000, 2007: 417_000, 2008: 417_000,
    2009: 417_000, 2010: 417_000, 2011: 417_000, 2012: 417_000, 2013: 417_000,
    2014: 417_000, 2015: 417_000, 2016: 417_000, 2017: 424_100, 2018: 453_100,
    2019: 484_350, 2020: 510_400, 2021: 548_250, 2022: 647_200, 2023: 726_200,
    2024: 766_550, 2025: 806_500, 2026: 832_750,
}

# A column computed from two knowable quantities, in place of its source.
# `upb_to_limit` is the original balance over the baseline one-unit limit of
# the loan's origination year: the characteristic the underwriting read, with
# the nominal dollar taken out. The year is read arithmetically, as
# `features.py` reads `issue_d` for a duration, and does not survive into the
# matrix.
DERIVED: dict[str, tuple[str, str]] = {"upb_to_limit": ("upb", "origination_year")}
REPLACED: frozenset[str] = frozenset(source for source, _ in DERIVED.values())

# The range the first and the last cohort share, for every kept numeric
# column. `value_report` measures it and refuses a mismatch. The ratio's is
# the first cohort's own, since 2023H2's range contains it on both sides, and
# it is written as the fractions it is so that the check to 1e-9 holds.
CLIPPED: dict[str, tuple[float, float]] = {
    "borrowers": (1.0, 2.0),
    "cltv": (6.0, 100.0),
    "fico": (601.0, 826.0),
    "ltv": (6.0, 100.0),
    "mi_pct": (0.0, 35.0),
    "term": (96.0, 360.0),
    "units": (1.0, 4.0),
    "upb_to_limit": (14_000 / 240_000, 461_000 / 240_000),
}

# The ablations EXP-005 names. `dti_kept` puts a dropped column back, with
# its missing value a level of its own; `upb_nominal` restores a replaced
# column in its raw form and takes its derived column out. Each restored
# column is clipped to the range the first and the last cohort share, which
# `value_report` measures under the ablation and refuses if it moves.
ABLATION_DTI_KEPT: frozenset[str] = frozenset({"dti"})
ABLATIONS: dict[str, frozenset[str]] = {
    "dti_kept": ABLATION_DTI_KEPT,
    "upb_nominal": frozenset({"upb"}),
}
ABLATION_CLIPPED: dict[str, tuple[float, float]] = {
    "dti": (2.0, 50.0),
    "upb": (19_000.0, 461_000.0),
}

# The clause an ablation overrides, or None for an ablation that changes a
# column's form and overrides no clause.
MISSING_SHARE_CLAUSE = "missing share differs between the first and the last cohort"
ABLATION_OVERRIDES: dict[str, str | None] = {
    "dti_kept": MISSING_SHARE_CLAUSE,
    "upb_nominal": None,
}

# Every unordered categorical among the origination-knowable columns, whether
# or not the matrix keeps it. Codes that look like numbers — the MSA, the
# valuation method — are categories, not quantities.
DECLARED_CATEGORICAL: tuple[str, ...] = (
    "amortization_type",
    "channel",
    "first_time_homebuyer",
    "harp",
    "interest_only",
    "msa",
    "occupancy",
    "postal_code",
    "prepayment_penalty",
    "property_type",
    "purpose",
    "seller",
    "special_eligibility_program",
    "state",
    "super_conforming",
    "valuation_method",
)

DROPPED: frozenset[str] = (
    frozenset(A_PRIORI) | frozenset(LATE_COVERAGE) | frozenset(VALUE_DROPPED)
)

# The axis and the calendar, which no matrix may carry. The year is written
# beside the quarter by the reducer and dates a loan as surely.
AXIS_COLUMNS: frozenset[str] = frozenset({AXIS, "origination_year"}) | CALENDAR | NON_FEATURES

# A derived column is knowable at origination when its source is and the
# year it reads is the axis, which is known by construction and refused as
# a column. Checked rather than asserted in prose.
AVAILABILITY: dict[str, int] = dict(FEATURE_AVAILABILITY)
for _derived, (_source, _year) in DERIVED.items():
    if FEATURE_AVAILABILITY.get(_source, 1) > 0 or _year not in AXIS_COLUMNS:
        raise FeatureError(f"{_derived} is derived from {_source} and {_year}, which are not "
                           f"both knowable at origination")
    AVAILABILITY[_derived] = 0
del _derived, _source, _year

_unknown = sorted(
    (set(DROPPED) | set(DECLARED_CATEGORICAL) | set(KEPT_PAIRS) | set(CLIPPED)
     | set(ABLATION_CLIPPED) | set().union(*ABLATIONS.values()) | set(REPLACED))
    - set(safe_features()) - set(DERIVED)
)
if _unknown:
    raise FeatureError(f"declared columns that are not knowable origination columns: {_unknown}")
del _unknown


def _ablated(ablation: str | None) -> frozenset[str]:
    """The columns an ablation restores, or none."""
    if ablation is None:
        return frozenset()
    if ablation not in ABLATIONS:
        raise FeatureError(f"no ablation {ablation!r}; the declared ones are {sorted(ABLATIONS)}")
    return ABLATIONS[ablation]


def _dropped(ablation: str | None) -> frozenset[str]:
    return DROPPED - _ablated(ablation)


def _derived(ablation: str | None) -> tuple[str, ...]:
    """The derived columns the matrix builds: those whose source is not restored."""
    ablated = _ablated(ablation)
    return tuple(name for name, (source, _) in DERIVED.items() if source not in ablated)


def _replaced(ablation: str | None) -> frozenset[str]:
    """The source columns the matrix carries in derived form."""
    return REPLACED - _ablated(ablation)


def _clipped(ablation: str | None) -> dict[str, tuple[float, float]]:
    ablated = _ablated(ablation)
    built = set(_derived(ablation))
    out = {k: v for k, v in CLIPPED.items() if k not in DERIVED or k in built}
    out.update({k: v for k, v in ABLATION_CLIPPED.items() if k in ablated})
    return out


def feature_names(ablation: str | None = None) -> tuple[str, ...]:
    """The columns of the model matrix, sorted, before any per-build screen."""
    excluded = _dropped(ablation) | _replaced(ablation)
    raw = {name for name in safe_features() if name not in excluded}
    return tuple(sorted(raw | set(_derived(ablation))))


def categorical_names(ablation: str | None = None) -> tuple[str, ...]:
    """The columns optbinning must treat as unordered categories.

    Declared rather than inferred from dtype, for the reason `features.py`
    gives; only the ones the matrix keeps are returned.
    """
    kept = set(feature_names(ablation))
    return tuple(name for name in DECLARED_CATEGORICAL if name in kept)


def declaration(ablation: str | None = None):
    """This module as the scorecard and the GBM read it, bound to an ablation."""
    from functools import partial
    from types import SimpleNamespace

    _ablated(ablation)
    return SimpleNamespace(
        assert_matrix_clean=partial(assert_matrix_clean, ablation=ablation),
        categorical_names=partial(categorical_names, ablation),
    )


def cohort_of(frame: pd.DataFrame):
    """The half-year of every loan, `2005H1`, from the quarter in its identifier."""
    import pandas as pd

    if AXIS not in frame.columns:
        raise FeatureError(f"the cohort is read off {AXIS}, which is absent")
    quarter = frame[AXIS].astype(str)
    half = (quarter.str[-1].astype(int) + 1) // 2
    return pd.Series(quarter.str[:4] + "H" + half.astype(str), index=frame.index)


def _quarters_of(name: str) -> tuple[str, str]:
    """The first and last quarter of a cohort named `1999Q1` or `2023H2`."""
    year, kind, number = name[:4], name[4], int(name[5])
    if kind == "Q":
        return name, name
    return f"{year}Q{2 * number - 1}", f"{year}Q{2 * number}"


def _in(frame: pd.DataFrame, first: str, last: str):
    """Loans whose origination quarter lies from the start of `first` to the end of `last`."""
    quarter = frame[AXIS].astype(str)
    return ((quarter >= _quarters_of(first)[0]) & (quarter <= _quarters_of(last)[1])).to_numpy()


def _cleaned(frame: pd.DataFrame, names) -> pd.DataFrame:
    """The columns named, with every sentinel read as missing."""
    out = frame[list(names)].copy()
    for name in out.columns:
        sentinel = SENTINELS.get(name)
        if sentinel is not None:
            column = out[name]
            out[name] = column.where(column.astype(object) != sentinel)
    return out


def _derived_values(frame: pd.DataFrame, name: str):
    """A derived column computed on the frame, before any clip.

    The loan amount over the conforming limit of the loan's origination year,
    both read from the frame; a year the table does not hold is refused
    rather than extrapolated.
    """
    import pandas as pd

    source, year = DERIVED[name]
    for needed in (source, year):
        if needed not in frame.columns:
            raise FeatureError(f"{name} is computed from {needed}, which is absent")
    amount = pd.to_numeric(_cleaned(frame, [source])[source], errors="coerce")
    years = pd.to_numeric(frame[year], errors="coerce").astype("Int64")
    limit = years.map(CONFORMING_LIMIT)
    unknown = sorted({int(y) for y in years[limit.isna() & years.notna()].unique()})
    if unknown or years.isna().any():
        raise FeatureError(f"{name} needs the conforming limit of the years {unknown}, which "
                           f"CONFORMING_LIMIT does not hold")
    return (amount / limit.astype("float64")).astype("float64")


def model_matrix(frame: pd.DataFrame, ablation: str | None = None) -> pd.DataFrame:
    """Builds the matrix every model on this book is fitted and scored on.

    Takes the frame of the reduced loans parquet and returns a new frame
    holding `feature_names(ablation)` and nothing else, sentinels read as
    missing, categorical columns as objects, numeric columns as floats
    clipped to `CLIPPED` and, under an ablation, `ABLATION_CLIPPED`. A derived
    column is computed from its sources, which the frame must hold. Neither
    the axis nor any calendar column survives into it.
    """
    import pandas as pd

    names = feature_names(ablation)
    built = set(_derived(ablation))
    raw = [name for name in names if name not in built]
    needed = raw + [part for name in built for part in DERIVED[name]]
    missing = [name for name in dict.fromkeys(needed) if name not in frame.columns]
    if missing:
        raise FeatureError(f"{len(missing)} declared features are absent: {missing[:10]}")

    cleaned = _cleaned(frame, raw)
    categorical = set(categorical_names(ablation))
    clipped = _clipped(ablation)
    out = pd.DataFrame(index=frame.index)
    for name in names:
        if name in categorical:
            column = cleaned[name]
            # Object rather than an extension dtype, for the reason
            # `features.model_matrix` gives.
            out[name] = column.astype(object).where(column.notna(), None)
            continue
        if name in built:
            out[name] = _derived_values(frame, name)
        else:
            out[name] = pd.to_numeric(cleaned[name], errors="coerce").astype("float64")
        if name not in clipped:
            raise FeatureError(f"{name} is a kept numeric column with no shared range")
        low, high = clipped[name]
        out[name] = out[name].clip(lower=low, upper=high)

    assert_features_knowable(AVAILABILITY, list(out.columns))
    return out


def calendar_share(frame: pd.DataFrame, name: str) -> float | None:
    """The share of a column's variance between cells of first payment month and term.

    One minus the within-cell sum of squares over the total, on the loans
    carrying a value, with the sentinels read as missing and a derived
    column computed from its sources. The statistic the rate is out a
    priori on, measured on any numeric column.
    """
    import pandas as pd

    for needed in ("term", "first_payment_date"):
        if needed not in frame.columns:
            raise FeatureError(f"cannot measure {name} against the calendar: {needed} absent")
    if name in DERIVED:
        values = _derived_values(frame, name)
    else:
        values = pd.to_numeric(_cleaned(frame, [name])[name], errors="coerce")
    cells = pd.DataFrame({
        "month": pd.to_numeric(frame["first_payment_date"], errors="coerce"),
        "term": pd.to_numeric(frame["term"], errors="coerce"),
        "value": values,
    }).dropna()
    if len(cells) < 2:
        return None
    within = cells["value"] - cells.groupby(["month", "term"])["value"].transform("mean")
    total = float(((cells["value"] - cells["value"].mean()) ** 2).sum())
    return round(1.0 - float((within ** 2).sum()) / total, 6) if total > 0 else None


def redundancy_report(frame: pd.DataFrame, ablation: str | None = None) -> dict[str, dict]:
    """Measures the kept pairs and every numeric column against the calendar, refusing nothing.

    The rate is out a priori; `calendar_share` is recorded for it, for every
    numeric column the matrix keeps under the ablation, and for both forms of
    the loan amount whatever the ablation.
    """
    import pandas as pd

    out: dict[str, dict] = {}
    for kept, other in KEPT_PAIRS.items():
        if kept not in frame.columns or other not in frame.columns:
            raise FeatureError(f"cannot check {kept} against {other}: column absent")
        both = _cleaned(frame, [kept, other])
        left = pd.to_numeric(both[kept], errors="coerce")
        right = pd.to_numeric(both[other], errors="coerce")
        present = left.notna() & right.notna()
        out[kept] = {
            "duplicates": other,
            "kept": True,
            "exact_agreement": round(float((left[present] == right[present]).mean()), 6),
            "correlation": round(float(left.corr(right)), 6),
        }

    if "rate" not in frame.columns:
        raise FeatureError("cannot measure the rate against the calendar: rate absent")
    categorical = set(DECLARED_CATEGORICAL)
    measured = ["rate"] + [n for n in feature_names(ablation) if n not in categorical]
    measured += [part for pair in DERIVED.items() for part in (pair[1][0], pair[0])]
    shares = {name: calendar_share(frame, name) for name in dict.fromkeys(measured)}
    out["rate"] = {
        "kept": False,
        "reason": A_PRIORI["rate"],
        "cells": RATE_CELLS,
        "variance_share": shares["rate"],
        "loans": int(pd.to_numeric(frame["rate"], errors="coerce").notna().sum()),
    }
    out["calendar_share"] = {"cells": RATE_CELLS, **shares}
    return out


def coverage_report(
    frame: pd.DataFrame, *, first_cohort: str = FIRST_COHORT, last_cohort: str = LAST_COHORT,
    ablation: str | None = None,
) -> dict[str, dict]:
    """Measures when every column begins on the book, and checks `LATE_COVERAGE`.

    The rule of `features.coverage_report`, with the sentinels read as
    missing: a column is present from the start if its share on the first
    cohort is at least `COVERAGE_FLOOR` of its peak half-year share. Every
    column the matrix keeps must pass and every late one must fail; a derived
    column is measured through its source. Each column's lowest half-year
    share is recorded beside its onset.
    """
    inside = _in(frame, first_cohort, last_cohort)
    if not inside.any():
        raise FeatureError(f"no rows fall in {first_cohort}..{last_cohort}")
    book = frame.loc[inside]
    first = _in(book, first_cohort, first_cohort)
    if not first.any():
        raise FeatureError(f"the book holds no rows in its first cohort {first_cohort}")
    built = set(_derived(ablation))
    kept = {n for n in feature_names(ablation) if n not in built}
    kept |= {DERIVED[name][0] for name in built}
    names = sorted(kept | set(LATE_COVERAGE))
    absent = [n for n in names if n not in frame.columns]
    if absent:
        raise FeatureError(f"cannot measure coverage: {absent[:10]} absent")

    present = _cleaned(book, names).notna()
    share = present.groupby(cohort_of(book)).mean().sort_index()
    out: dict[str, dict] = {}
    disagreements = []
    for name in names:
        column = share[name]
        peak = float(column.max())
        at_first = float(present[name].to_numpy()[first].mean())
        onset = None
        if peak > 0:
            reached = column[column >= COVERAGE_FLOOR * peak]
            onset = str(reached.index[0]) if len(reached) else None
        from_start = peak > 0 and at_first >= COVERAGE_FLOOR * peak
        declared_late = name in LATE_COVERAGE
        out[name] = {
            "onset": onset,
            "first_cohort_share": round(at_first, 4),
            "peak_share": round(peak, 4),
            "lowest_share": round(float(column.min()), 4),
            "lowest_cohort": str(column.idxmin()),
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


def _top(shares: dict, limit: int = 10) -> dict:
    ordered = sorted(shares.items(), key=lambda item: -item[1])
    out = {str(k): round(float(v), 6) for k, v in ordered[:limit]}
    if len(ordered) > limit:
        out[f"... {len(ordered)} levels"] = round(float(sum(v for _, v in ordered[limit:])), 6)
    return out


def value_rule(
    frame: pd.DataFrame, *, first_cohort: str = FIRST_COHORT, last_cohort: str = LAST_COHORT
) -> dict[str, dict]:
    """The symmetric value rule measured on the book, one verdict per column.

    Every origination column not out a priori is measured, including the
    ones the coverage gate drops, so that the record says which gates fire
    on each; so is every derived column, computed on the book and measured
    as a kept numeric one, beside its source, whose record names the column
    that replaces it. Each record carries the clauses that fire, the missing
    share on the first cohort, the last and the book, the late and departed
    levels of a categorical with their shares of the book, and the shared
    range of a numeric column.
    """
    import pandas as pd

    inside = _in(frame, first_cohort, last_cohort)
    if not inside.any():
        raise FeatureError(f"no rows fall in {first_cohort}..{last_cohort}")
    book = frame.loc[inside]
    first = _in(book, first_cohort, first_cohort)
    last = _in(book, last_cohort, last_cohort)
    if not first.any() or not last.any():
        raise FeatureError(f"the book holds no rows in {first_cohort} or in {last_cohort}")
    names = [n for n in safe_features() if n not in A_PRIORI]
    absent = [n for n in names if n not in frame.columns]
    if absent:
        raise FeatureError(f"cannot measure the value rule: {absent[:10]} absent")
    cleaned = _cleaned(book, names)
    columns = {name: cleaned[name] for name in names}
    for name in DERIVED:
        columns[name] = _derived_values(book, name)
    size = len(book)

    out: dict[str, dict] = {}
    for name, column in columns.items():
        present = column.notna().to_numpy()
        missing_first = 1.0 - float(present[first].mean())
        missing_last = 1.0 - float(present[last].mean())
        missing_book = 1.0 - float(present.mean())
        record: dict = {
            "missing_share": {"first": round(missing_first, 4), "last": round(missing_last, 4),
                              "book": round(missing_book, 4)},
        }
        if name in DERIVED:
            record["derived_from"] = list(DERIVED[name])
        replacement = [d for d, (source, _) in DERIVED.items() if source == name]
        if replacement:
            record["replaced_by"] = replacement[0]
        clauses: list[str] = []
        if name in DECLARED_CATEGORICAL:
            values = column.astype(object)
            held_first = set(values[first & present].unique())
            held_last = set(values[last & present].unique())
            shares = (values[present].value_counts() / size).to_dict()
            late = {level: share for level, share in shares.items() if level not in held_first}
            departed = {level: shares.get(level, 0.0) for level in held_first
                        if level not in held_last}
            record["distinct_first"] = len(held_first)
            record["late_levels"] = _top(late)
            record["departed_levels"] = _top(departed)
            if len(held_first) <= 1:
                clauses.append("constant on the first cohort")
            if any(share > VALUE_FLOOR for share in late.values()):
                clauses.append("a level absent from the first cohort")
            if any(share > VALUE_FLOOR for share in departed.values()):
                clauses.append("a level present on the first cohort and absent from the last")
        else:
            numbers = pd.to_numeric(column, errors="coerce").to_numpy(dtype=float)
            head, tail = numbers[first & present], numbers[last & present]
            record["distinct_first"] = len(set(head.tolist()))
            if record["distinct_first"] <= 1:
                clauses.append("constant on the first cohort")
            if len(head) and len(tail):
                low = max(float(head.min()), float(tail.min()))
                high = min(float(head.max()), float(tail.max()))
                record["first_range"] = [float(head.min()), float(head.max())]
                record["last_range"] = [float(tail.min()), float(tail.max())]
                record["shared_range"] = [low, high]
                values = numbers[present]
                record["share_clipped"] = {
                    "below": round(float((values < low).sum() / size), 6),
                    "above": round(float((values > high).sum() / size), 6),
                }
                if low > high:
                    clauses.append("the first and the last cohort share no range")
        if missing_first == 0.0 and missing_book > VALUE_FLOOR:
            clauses.append("missing is a level absent from the first cohort")
        if abs(missing_first - missing_last) > VALUE_FLOOR:
            clauses.append(MISSING_SHARE_CLAUSE)
        record["clauses"] = clauses
        record["out"] = bool(clauses)
        out[name] = record
    return out


def value_report(
    frame: pd.DataFrame, *, first_cohort: str = FIRST_COHORT, last_cohort: str = LAST_COHORT,
    ablation: str | None = None,
) -> dict[str, dict]:
    """The value rule on the book, checked against `VALUE_DROPPED` and `CLIPPED`.

    Every column the coverage gate keeps must be out under the rule exactly
    when it is listed in `VALUE_DROPPED`, and every numeric column the matrix
    keeps must have its `CLIPPED` bounds as its shared range. The columns the
    coverage gate drops, and the form of a column the matrix does not carry,
    are measured and recorded with the clauses that fire on them, and
    checked against nothing. Any disagreement stops the run.

    Under an ablation that overrides a clause, the columns it puts back must
    disagree, each out under the rule on that clause alone, and their records
    say so; under one that changes a column's form, the restored column is
    checked as every kept numeric column is and no clause may fire on it.
    The restored columns' shared ranges are checked against
    `ABLATION_CLIPPED`. Any other disagreement stops the run, and so does
    the absence of an override the ablation declares.
    """
    ablated = _ablated(ablation)
    override = ABLATION_OVERRIDES.get(ablation) if ablation is not None else None
    kept = set(feature_names(ablation))
    declared_dropped = set(VALUE_DROPPED) - ablated
    clipped = _clipped(ablation)
    rule = value_rule(frame, first_cohort=first_cohort, last_cohort=last_cohort)
    disagreements: list[tuple[str, str]] = []
    overridden: list[str] = []
    for name, record in rule.items():
        record["gates"] = (["coverage"] if name in LATE_COVERAGE else []) + (
            ["value"] if record["out"] else [])
        if name in LATE_COVERAGE:
            continue
        if name not in kept and name not in declared_dropped:
            record["checked"] = False
            continue
        if name in ablated:
            record["ablation"] = ablation
        if record["out"] != (name in declared_dropped):
            if name in ablated and override is not None and record["clauses"] == [override]:
                overridden.append(name)
            else:
                verdict = "out" if record["out"] else "kept"
                disagreements.append((name, f"rule says {verdict}: {record['clauses']}"))
        if name in kept and name not in DECLARED_CATEGORICAL:
            measured = tuple(record.get("shared_range", ()))
            declared = clipped.get(name)
            if declared is None or any(abs(a - b) > 1e-9 for a, b in zip(measured, declared)):
                disagreements.append((name, f"shared range {measured}, declared {declared}"))
    if override is not None and sorted(overridden) != sorted(ablated):
        message = (f"the ablation expects {sorted(ablated)} out on the clause {override!r} "
                   f"alone, and the rule gives {sorted(overridden)}")
        disagreements.append((ablation, message))
    if disagreements:
        raise FeatureError(
            f"{len(disagreements)} columns disagree with the value rule on this book: "
            f"{disagreements[:8]}"
        )
    return rule


def shift_report(
    frame: pd.DataFrame, *, first_cohort: str = FIRST_COHORT, last_cohort: str = LAST_COHORT,
    ablation: str | None = None,
) -> dict[str, dict]:
    """What moves inside the axis on the kept columns, measured at the floor, refusing nothing.

    The value rule reads the two ends of the axis; this reads the middle.
    For every kept column: the lowest and highest half-year missing share;
    for a categorical, every level that the last cohort does not hold and
    some half-year holds on more than `VALUE_FLOOR` of its loans; for a
    numeric column, the share of the book outside the last cohort's range. A
    column whose missing share moves by more than `VALUE_FLOOR` also records
    how much of its missingness sits on each late level of a dropped column
    that held one level in the first cohort. `flagged` names every column
    with a share over the floor.
    """
    import numpy as np
    import pandas as pd

    inside = _in(frame, first_cohort, last_cohort)
    book = frame.loc[inside]
    cohorts = cohort_of(book).to_numpy()
    first = _in(book, first_cohort, first_cohort)
    last = _in(book, last_cohort, last_cohort)
    if not last.any():
        raise FeatureError(f"the book holds no rows in its last cohort {last_cohort}")
    sizes = pd.Series(cohorts).value_counts().sort_index()

    ablated = _ablated(ablation)
    dropped = [n for n in VALUE_DROPPED
               if n in DECLARED_CATEGORICAL and n in book.columns and n not in ablated]
    carriers = _cleaned(book, dropped)
    late_levels: list[tuple[str, np.ndarray]] = []
    for name in carriers.columns:
        column = carriers[name]
        held = set(column[first & column.notna().to_numpy()].unique())
        if len(held) == 1:
            for level in sorted(set(column.dropna().unique()) - held):
                late_levels.append((f"{name}={level}", (column == level).to_numpy()))

    matrix = model_matrix(book, ablation=ablation)
    categorical = set(categorical_names(ablation))
    columns: dict[str, dict] = {}
    flagged: dict[str, list[str]] = {}
    for name in matrix.columns:
        column = matrix[name]
        missing = column.isna().to_numpy()
        by_cohort = pd.Series(missing).groupby(cohorts).mean()
        record: dict = {
            "missing_share_min": round(float(by_cohort.min()), 4),
            "missing_share_min_cohort": str(by_cohort.idxmin()),
            "missing_share_max": round(float(by_cohort.max()), 4),
            "missing_share_max_cohort": str(by_cohort.idxmax()),
        }
        reasons: list[str] = []
        if by_cohort.max() - by_cohort.min() > VALUE_FLOOR:
            reasons.append("its missing share moves across cohorts by more than the floor")
            record["missing_on_late_carrier_levels"] = {
                label: round(float((mask & missing).sum() / missing.sum()), 4)
                for label, mask in late_levels
            }
        present = ~missing
        if name in categorical:
            held_last = set(column[last & present].unique())
            counts = pd.crosstab(cohorts[present], column[present].to_numpy())
            shares = counts.div(sizes.reindex(counts.index), axis=0)
            vanished = {}
            for level in shares.columns:
                if level in held_last or shares[level].max() <= VALUE_FLOOR:
                    continue
                holding = shares[level][shares[level] > 0]
                vanished[str(level)] = {
                    "peak_share": round(float(shares[level].max()), 4),
                    "peak_cohort": str(shares[level].idxmax()),
                    "last_cohort_holding": str(holding.index.max()),
                    "share_of_book": round(float(counts[level].sum() / len(column)), 4),
                }
            record["levels_absent_from_last_cohort"] = vanished
            if vanished:
                reasons.append(f"levels absent from the last cohort: {sorted(vanished)}")
        else:
            values = column[last & present]
            low, high = float(values.min()), float(values.max())
            outside = present & ((column < low) | (column > high)).to_numpy()
            share = float(outside.sum() / present.sum()) if present.any() else 0.0
            record["last_cohort_support"] = [low, high]
            record["share_outside_last_cohort"] = round(share, 6)
            if share > VALUE_FLOOR:
                reasons.append("over the floor outside the last cohort's range")
        columns[name] = record
        if reasons:
            flagged[name] = reasons
    return {"columns": columns, "flagged": flagged, "floor": VALUE_FLOOR}


def assert_matrix_clean(matrix: pd.DataFrame, ablation: str | None = None) -> None:
    """The gate a runner calls before fitting anything on a matrix it was handed.

    The counterpart of `features.assert_matrix_clean`: the axis, a calendar
    column or an identifier is a leak; a dropped column, a column the matrix
    carries in derived form, or a derived column whose source the ablation
    restores is a mistake unless the ablation that allows it is declared; and
    any column whose availability is not declared is refused.
    """
    columns = list(matrix.columns)
    leaked = sorted(set(columns) & AXIS_COLUMNS)
    if leaked:
        raise LeakageError(f"{leaked} are the axis, the calendar or an identifier, not features")
    refused = _dropped(ablation) | _replaced(ablation) | (set(DERIVED) - set(_derived(ablation)))
    smuggled = sorted(set(columns) & refused)
    if smuggled:
        raise FeatureError(f"columns dropped from the study are present: {smuggled}")
    assert_features_knowable(AVAILABILITY, columns)
