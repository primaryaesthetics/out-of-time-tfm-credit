"""A synthetic Freddie Mac book in the reducer's layout, drawn so that the feature gates pass.

Every decision the feature module declares is planted where the lists say it
is. The late-coverage columns begin late; the columns the value rule removes
fire the clause it names — constant on 1999Q1, a seller level absent from it,
a channel level gone by 2023H2, an MSA and a debt-to-income ratio missing more
often at the start than at the end; every kept numeric column holds its
`CLIPPED` bounds in both the first and the last cohort and strays outside
them in between, so that the clip has something to do; and an occupancy level
that lives only in the middle of the axis stays under the floor. The
performance side plants defaults that depend on the credit score and the
loan-to-value, relief months after 2013, re-dated loans, two loans with no
servicing record, loans first observed late, records with a missing month,
and relief refinances whose pre-HARP identifier names an older loan.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from outoftime.fm_features import ABLATION_CLIPPED, CLIPPED, CONFORMING_LIMIT
from outoftime.freddie_mac import ORIGINATION_COLUMNS

CUTOFF = 202603
FIRST_YEAR, LAST_YEAR = 1999, 2025
REDATED_PER_YEAR = 1
WITHOUT_RECORD = 2
SLICE_MONTHS = 24


def months_observable(fpd: int) -> int:
    return (CUTOFF // 100 - fpd // 100) * 12 + CUTOFF % 100 - fpd % 100 + 1


def _bounded(rng, name: str, i: int, late: bool, middle: list[float]) -> float:
    """A value of a clipped column: its bounds on two fixed loans of every
    quarter, something beyond the upper bound on a third loan after 2009."""
    low, high = CLIPPED[name]
    if i == 3:
        return low
    if i == 4:
        return high
    if i == 5 and late:
        return high * 1.3
    return float(rng.choice(middle))


def book(per_quarter: int = 24, seed: int = 20260912) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The loans frame and the monthly slice, both as the reducer writes them."""
    rng = np.random.default_rng(seed)
    loans: list[dict] = []
    perf: list[dict] = []
    old_ids: list[str] = []
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        for quarter in range(1, 5):
            for i in range(per_quarter):
                start = year * 12 + (quarter - 1) * 3 + 1
                lag = 1 + int(rng.integers(0, 4))
                if quarter == 2 and i == per_quarter - 1:
                    lag = 8
                unrecorded = year == LAST_YEAR and quarter == 4 and i < WITHOUT_RECORD
                if unrecorded:
                    lag = 3
                total = start + lag
                fpd = ((total - 1) // 12) * 100 + (total - 1) % 12 + 1
                loan_id = f"F{year % 100:02d}Q{quarter}{len(loans):07d}"
                first_cohort = year == FIRST_YEAR and quarter == 1
                late = year >= 2010

                harp = "Y" if 2009 <= year <= 2019 and rng.random() < 0.25 else "N"
                # The ablation's shared range at both ends of the axis, and
                # values above it on the early cohorts for the clip to move.
                dti_low, dti_high = ABLATION_CLIPPED["dti"]
                dti = ("999" if harp == "Y" or (first_cohort and i % 8 in (6, 7))
                       else f"{dti_low:g}" if i == 3 else f"{dti_high:g}" if i == 4
                       else "60" if i == 5 and year <= 2010
                       else str(rng.choice([20, 35, 45])))
                ltv = _bounded(rng, "ltv", i, late, [60, 80, 95])
                cltv = ltv if i in (3, 4, 5) else min(ltv + (5 if rng.random() < 0.1 else 0), 100)
                if i == 5 and late:
                    cltv = CLIPPED["cltv"][1] * 1.3
                fico = _bounded(rng, "fico", i, late, [640, 700, 780])
                term = _bounded(rng, "term", i, False, [180, 360])
                rate = (8.0 - 0.19 * (total - FIRST_YEAR * 12) / 12 + (0.4 if term == 360 else 0.0)
                        + float(rng.normal(0.0, 0.03)))
                # Nominal amounts that rise with the year's limit, with the
                # declared ranges of both forms at both ends of the axis: the
                # first cohort spans the ratio's range exactly, the last
                # holds the nominal floor of 19,000 and more than the
                # first cohort's ceiling, and loans past the ceiling after
                # 2009 give the clip something to move.
                limit = CONFORMING_LIMIT[year]
                if i == 3:
                    upb = 14_000 if year == FIRST_YEAR else 19_000
                elif i == 4:
                    upb = 461_000 if year == FIRST_YEAR else round(limit * 461_000 / 240_000 * 1.1)
                elif i == 5 and late:
                    upb = round(limit * 2.2)
                else:
                    upb = round(limit * float(rng.choice([0.3, 0.45, 0.6])))
                occupancy = ("S" if 2000 <= year <= 2010 and i % 10 == 7
                             else str(rng.choice(["P", "P", "P", "I"])))
                record = {
                    "fico": "9999" if i == 0 else f"{fico:g}",
                    "first_payment_date": str(fpd),
                    "first_time_homebuyer": str(rng.choice(["N", "N", "Y"])),
                    "maturity_date": str(fpd + 3000),
                    "msa": (None if (i % 2 == 1 if year < 2005 else i % 10 == 3)
                            else str(rng.choice(["31080", "19100", "35620"]))),
                    "mi_pct": f"{_bounded(rng, 'mi_pct', i, False, [0, 0, 25]):g}",
                    "units": f"{_bounded(rng, 'units', i, False, [1, 1, 2]):g}",
                    "occupancy": occupancy,
                    "cltv": f"{cltv:g}",
                    "dti": dti,
                    "upb": str(upb),
                    "ltv": f"{ltv:g}",
                    "rate": f"{rate:.3f}",
                    "channel": ("T" if year < 2008 and i == 9 else str(rng.choice(
                        ["R", "C", "B", "T"] if year < 2008 else ["R", "C", "B"]))),
                    "prepayment_penalty": "Y" if i == 6 else "N",
                    "amortization_type": "FRM",
                    "state": str(rng.choice(["CA", "TX", "NY"])),
                    "property_type": str(rng.choice(["SF", "SF", "PU"])),
                    "postal_code": str(rng.choice(["900", "750", "100"])),
                    "loan_id": loan_id,
                    "purpose": str(rng.choice(["P", "N", "C"])),
                    "term": f"{term:g}",
                    "borrowers": f"{_bounded(rng, 'borrowers', i, False, [1, 2]):g}",
                    "seller": ("ALPHA" if i % 2 else "BETA") if first_cohort else f"SELLER{year % 7}",
                    "super_conforming": ("Y" if (year, quarter) >= (2008, 3) and rng.random() < 0.05
                                         else "N"),
                    "pre_harp_loan_id": (str(rng.choice(old_ids)) if harp == "Y" and old_ids
                                         else None),
                    "special_eligibility_program": "H" if year >= 2017 and rng.random() < 0.4 else None,
                    "harp": harp,
                    "valuation_method": "2" if year >= 2020 else "7",
                    "interest_only": "N",
                    "vantage_score": "9999",
                    "origination_year": year,
                    "origination_quarter": f"{year}Q{quarter}",
                    "first_payment_lag": lag,
                }
                if year <= 2005:
                    old_ids.append(loan_id)

                if unrecorded:
                    record.update({"n_periods": 0, "last_age": None, "first_bad_age": None,
                                   "first_bad_age_outside_relief": None,
                                   "termination_code": None, "termination_age": None})
                    loans.append(record)
                    continue
                observable = months_observable(fpd)
                p = 0.07 * (2.5 if fico <= 640 else 1.0) * (1.5 if ltv >= 95 else 1.0) * (
                    2.0 if 2006 <= year <= 2008 else 1.0)
                # Two defaults outside relief in every quarter, so that no
                # cohort of the build holds one class only.
                forced = i in (1, 2)
                bad = forced or rng.random() < p
                first_bad = int(rng.integers(4, 20)) if bad else None
                relief = bad and not forced and year >= 2013 and rng.random() < 0.5
                code = at = None
                if bad and rng.random() < 0.4:
                    code, at = 3, first_bad + 6
                elif not bad and rng.random() < 0.35:
                    code, at = 1, int(rng.integers(30, 120))
                elif not bad and rng.random() < 0.02:
                    code, at = 96, int(rng.integers(2, 20))
                if at is not None and at > observable:
                    code = at = None
                if first_bad is not None and first_bad > observable:
                    first_bad, relief = None, False
                last = observable if at is None else at
                draw = rng.random()
                seen = int(rng.choice([15, 30])) if draw < 0.03 else (
                    int(rng.choice([2, 3])) if draw < 0.08 else 1)
                if seen > last:
                    seen = 1
                # A month missing in the middle of the record: after the
                # slice on some loans, inside it on others.
                gap_after = i == 10 and quarter == 3 and last > SLICE_MONTHS + 1
                gap_inside = i == 11 and quarter == 4 and last > seen + 3
                periods = last - seen + 1 - (1 if gap_after or gap_inside else 0)
                record.update({
                    "n_periods": periods, "last_age": last, "first_bad_age": first_bad,
                    "first_bad_age_outside_relief": None if relief else first_bad,
                    "termination_code": code, "termination_age": at,
                })
                loans.append(record)
                perf.extend({"loan_id": loan_id, "age": age}
                            for age in range(seen, min(last, SLICE_MONTHS) + 1)
                            if not (gap_inside and age == seen + 1))

    frame = pd.DataFrame(loans)
    for name in ("last_age", "first_bad_age", "first_bad_age_outside_relief",
                 "termination_code", "termination_age"):
        frame[name] = pd.array(frame[name], dtype="Int32")
    frame["n_periods"] = frame["n_periods"].astype("int32")
    frame["origination_year"] = frame["origination_year"].astype("int16")
    frame["first_payment_lag"] = frame["first_payment_lag"].astype("int16")
    for name in ORIGINATION_COLUMNS:
        frame[name] = frame[name].astype(object)
    slice_ = pd.DataFrame(perf)
    slice_["age"] = slice_["age"].astype("int16")
    return frame, slice_


def write_derived(path: Path, **kwargs) -> Path:
    """The reduced files of the synthetic book, one parquet pair and record per year."""
    frame, slice_ = book(**kwargs)
    path.mkdir(parents=True, exist_ok=True)
    for year, loans in frame.groupby("origination_year"):
        loans.to_parquet(path / f"loans_{year}.parquet", index=False)
        slice_[slice_["loan_id"].isin(set(loans["loan_id"]))].to_parquet(
            path / f"perf_{year}.parquet", index=False)
        (path / f"reduce_{year}.json").write_text(
            json.dumps({"year": int(year), "last_period_on_file": CUTOFF}), encoding="utf-8")
    return path
