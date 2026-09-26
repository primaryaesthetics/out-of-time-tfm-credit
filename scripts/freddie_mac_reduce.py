#!/usr/bin/env python3
"""Reduces the Freddie Mac sample, one origination year at a time, to parquet.

The sample is twenty-eight zips, one per origination year, each holding an
origination file and a monthly performance file. Unzipped they are eight and a
half gigabytes, most of it performance months that no label reads: the oldest
vintages carry more than two hundred months per loan. This streams each zip
without writing its text to disk and keeps three things per year:

  * ``loans_YYYY.parquet``: one row per loan, every origination column, the
    origination quarter parsed from the identifier, and the four numbers the
    label needs from the servicing record (``last_age``, ``first_bad_age``,
    ``termination_code``, ``termination_age``), all in months from the first
    payment month;
  * ``perf_YYYY.parquet``: the first twenty-four months of every loan, on the
    columns that decide a label, so that a different threshold or window can
    be recomputed without the zips;
  * ``reduce_YYYY.json``: what went in and what came out, with the zip's hash.

Age is computed from the period and the first payment date rather than read
from the file's own loan-age field, which resets on modification.

    python scripts/record_run.py fm-reduce -- \\
        python scripts/freddie_mac_reduce.py data/raw/freddie-mac \\
            --out-dir data/derived/freddie-mac
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from outoftime.freddie_mac import (
    ORIGINATION_COLUMNS,
    PERFORMANCE_COLUMNS,
    audit_widths,
    first_payment_lag,
    origination_quarter,
    widths_match,
)
from outoftime.performance_label import DELINQUENCY_MONTHS

# The performance columns kept in the monthly slice. Enough to rebuild the
# label under another threshold or window; nothing that only a loss study reads.
PERF_KEPT = (
    "loan_id", "period", "current_upb", "delinquency_status",
    "modification_flag", "zero_balance_code", "zero_balance_date",
    "borrower_assistance_plan", "disaster_delinquency",
)
WINDOW_KEPT_MONTHS = 24
CHUNK_ROWS = 1_000_000

# A loan with no performance record at all is tolerated only when its first
# payment falls inside this many months before the last period on file: the
# servicing record of a loan acquired shortly before the cutoff has not
# arrived yet, and the loan is immature under any window. A loan older than
# that with no record is a gap in the data, and the reduction refuses.
REPORTING_LAG_MONTHS = 6


def check_missing_histories(
    first_payment_months: pd.Series, last_period_months: int
) -> None:
    """Refuses a loan with no performance record unless it is young enough
    for the record not to have arrived."""
    stale = first_payment_months < last_period_months - REPORTING_LAG_MONTHS
    if stale.any():
        raise SystemExit(
            f"{int(stale.sum())} loans have no performance rows and a first "
            f"payment more than {REPORTING_LAG_MONTHS} months before the last "
            f"period on file"
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def months(yyyymm: pd.Series) -> pd.Series:
    """YYYYMM as a month count, so that differences are months."""
    value = pd.to_numeric(yyyymm, errors="coerce")
    return (value // 100) * 12 + value % 100


def first_line_width(archive: zipfile.ZipFile, member: str) -> int:
    with archive.open(member) as handle:
        line = io.TextIOWrapper(handle, encoding="utf-8").readline()
    return line.rstrip("\r\n").count("|") + 1


def read_origination(archive: zipfile.ZipFile, member: str) -> pd.DataFrame:
    with archive.open(member) as handle:
        frame = pd.read_csv(
            handle, sep="|", header=None, names=ORIGINATION_COLUMNS,
            dtype=str, keep_default_na=True, na_values=[""],
        )
    quarters = frame["loan_id"].map(origination_quarter)
    frame["origination_year"] = quarters.map(lambda q: q[0]).astype("int16")
    frame["origination_quarter"] = quarters.map(
        lambda q: f"{q[0]}Q{q[1]}").astype("string")
    first_payment = pd.to_numeric(frame["first_payment_date"], errors="coerce")
    if first_payment.isna().any():
        raise SystemExit(f"{member}: loans without a first payment date")
    frame["first_payment_lag"] = [
        first_payment_lag(q[0], q[1], int(fpd))
        for q, fpd in zip(quarters, first_payment)
    ]
    frame["first_payment_lag"] = frame["first_payment_lag"].astype("int16")
    return frame


def reduce_performance(
    archive: zipfile.ZipFile, member: str, first_payment: pd.Series
) -> tuple[pd.DataFrame, pd.DataFrame, int, int]:
    """One pass over the performance file, in chunks; returns the slice, the
    per-loan summary, the number of rows read and the last period on file."""
    kept_index = [PERFORMANCE_COLUMNS.index(name) for name in PERF_KEPT]
    slices: list[pd.DataFrame] = []
    partials: list[pd.DataFrame] = []
    rows = 0
    last_period = 0
    fpd = first_payment.rename("fpd_months")
    with archive.open(member) as handle:
        reader = pd.read_csv(
            handle, sep="|", header=None, usecols=kept_index,
            names=PERFORMANCE_COLUMNS, dtype=str, keep_default_na=True,
            na_values=[""], chunksize=CHUNK_ROWS,
        )
        for chunk in reader:
            rows += len(chunk)
            last_period = max(last_period, int(chunk["period"].astype(int).max()))
            chunk = chunk.join(fpd, on="loan_id")
            if chunk["fpd_months"].isna().any():
                unknown = chunk.loc[chunk["fpd_months"].isna(), "loan_id"].unique()
                raise SystemExit(
                    f"{member}: {len(unknown)} loans have performance rows and no "
                    f"origination row, e.g. {unknown[:3].tolist()}"
                )
            age = (months(chunk["period"]) - chunk["fpd_months"] + 1).astype("int32")
            chunk["age"] = age
            status = pd.to_numeric(chunk["delinquency_status"], errors="coerce")
            bad = (status >= DELINQUENCY_MONTHS) | (chunk["delinquency_status"] == "RA")
            # The same month read with a payment-relief plan or a declared
            # disaster hardship set aside: a borrower in forbearance is
            # reported delinquent off the last paid installment, and whether
            # that is a default is a definition rather than a fact. Both ages
            # are kept so the definition can be measured before it is chosen.
            under_relief = (
                chunk["borrower_assistance_plan"].notna()
                | chunk["disaster_delinquency"].notna()
            )
            bad_outside_relief = bad & ~under_relief
            code = pd.to_numeric(chunk["zero_balance_code"], errors="coerce")
            # The zero-balance date is the month of the event and is the
            # termination age where present. Where a code is set and the
            # date is blank, the period the code appears in stands in, and
            # the substitution is counted.
            zb_age = months(chunk["zero_balance_date"]) - chunk["fpd_months"] + 1
            undated = code.notna() & zb_age.isna()
            termination_age = zb_age.where(~undated, age).where(code.notna())

            partial = pd.DataFrame({
                "loan_id": chunk["loan_id"],
                "n_periods": 1,
                "last_age": age,
                "first_bad_age": age.where(bad),
                "first_bad_age_outside_relief": age.where(bad_outside_relief),
                "termination_code": code,
                "termination_age": termination_age,
                "undated_termination": undated.astype("int32"),
            })
            partials.append(partial.groupby("loan_id", sort=False).agg(
                n_periods=("n_periods", "sum"),
                last_age=("last_age", "max"),
                first_bad_age=("first_bad_age", "min"),
                first_bad_age_outside_relief=("first_bad_age_outside_relief", "min"),
                termination_code=("termination_code", "max"),
                termination_age=("termination_age", "max"),
                undated_termination=("undated_termination", "max"),
            ).reset_index())

            slices.append(
                chunk.loc[age <= WINDOW_KEPT_MONTHS, [*PERF_KEPT, "age"]]
            )

    summary = pd.concat(partials, ignore_index=True).groupby(
        "loan_id", sort=False).agg(
        n_periods=("n_periods", "sum"),
        last_age=("last_age", "max"),
        first_bad_age=("first_bad_age", "min"),
        first_bad_age_outside_relief=("first_bad_age_outside_relief", "min"),
        termination_code=("termination_code", "max"),
        termination_age=("termination_age", "max"),
        undated_termination=("undated_termination", "max"),
    ).reset_index()
    summary["n_periods"] = summary["n_periods"].astype("int32")
    summary["last_age"] = summary["last_age"].astype("int32")
    summary["undated_termination"] = summary["undated_termination"].astype(bool)
    for name in ("first_bad_age", "first_bad_age_outside_relief",
                 "termination_code", "termination_age"):
        summary[name] = summary[name].astype("Int32")

    window = pd.concat(slices, ignore_index=True)
    window["age"] = window["age"].astype("int16")
    return window, summary, rows, last_period


def reduce_year(zip_path: Path, out_dir: Path, year: int) -> dict:
    started = time.perf_counter()
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.namelist()
        orig_member = next(m for m in members if "orig" in m)
        perf_member = next(m for m in members if "perf" in m or "svcg" in m)
        audit = audit_widths(
            first_line_width(archive, orig_member),
            first_line_width(archive, perf_member),
        )
        if not widths_match(audit):
            raise SystemExit(f"{zip_path.name}: layout width mismatch {audit}")

        loans = read_origination(archive, orig_member)
        if loans["loan_id"].duplicated().any():
            raise SystemExit(f"{zip_path.name}: duplicate loan identifiers")
        fpd = months(loans["first_payment_date"])
        first_payment = pd.Series(fpd.values, index=loans["loan_id"].values)

        window, summary, perf_rows, last_period = reduce_performance(
            archive, perf_member, first_payment)

    loans = loans.merge(summary, on="loan_id", how="left")
    without_history = loans["last_age"].isna()
    if without_history.any():
        check_missing_histories(
            fpd[without_history.to_numpy()],
            (last_period // 100) * 12 + last_period % 100,
        )
    loans["n_periods"] = loans["n_periods"].fillna(0).astype("int32")
    loans["last_age"] = loans["last_age"].astype("Int32")
    loans["undated_termination"] = loans["undated_termination"].fillna(False).astype(bool)
    if (loans["termination_code"].notna() & loans["termination_age"].isna()).any():
        raise SystemExit(f"{zip_path.name}: a terminated loan has no termination age")

    loans.to_parquet(out_dir / f"loans_{year}.parquet", index=False)
    window.to_parquet(out_dir / f"perf_{year}.parquet", index=False)

    record = {
        "year": year,
        "zip": zip_path.name,
        "zip_bytes": zip_path.stat().st_size,
        "zip_sha256": sha256(zip_path),
        "members": [orig_member, perf_member],
        "widths": audit,
        "loans": len(loans),
        "loans_outside_file_year": int((loans["origination_year"] != year).sum()),
        "loans_without_performance_record": int(without_history.sum()),
        "reporting_lag_months": REPORTING_LAG_MONTHS,
        "performance_rows": perf_rows,
        "performance_rows_kept": len(window),
        "performance_rows_before_age_one": int((window["age"] < 1).sum()),
        "window_kept_months": WINDOW_KEPT_MONTHS,
        "delinquency_months": DELINQUENCY_MONTHS,
        "first_payment_months": {
            "min": int(loans["first_payment_date"].astype(int).min()),
            "max": int(loans["first_payment_date"].astype(int).max()),
        },
        "first_payment_lag_months": {
            "min": int(loans["first_payment_lag"].min()),
            "median": float(loans["first_payment_lag"].median()),
            "max": int(loans["first_payment_lag"].max()),
        },
        "last_period_on_file": last_period,
        "terminated": int(loans["termination_code"].notna().sum()),
        "terminated_without_a_zero_balance_date": int(loans["undated_termination"].sum()),
        "termination_codes": {
            str(int(k)): int(v)
            for k, v in loans["termination_code"].value_counts().items()
        },
        "with_default_event": int(loans["first_bad_age"].notna().sum()),
        "with_default_event_outside_relief": int(
            loans["first_bad_age_outside_relief"].notna().sum()),
        "seconds": round(time.perf_counter() - started, 1),
    }
    (out_dir / f"reduce_{year}.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8")
    return record


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("raw_dir", type=Path, help="directory of sample_YYYY.zip")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--years", type=int, nargs="*", default=None,
                        help="restrict to these years (default: every zip found)")
    parser.add_argument("--force", action="store_true",
                        help="redo years whose parquet already exists")
    args = parser.parse_args(argv)

    zips = sorted(args.raw_dir.glob("sample_*.zip"))
    if not zips:
        raise SystemExit(f"no sample_*.zip under {args.raw_dir}")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for zip_path in zips:
        year = int(zip_path.stem.split("_")[1])
        if args.years and year not in args.years:
            continue
        if not args.force and (args.out_dir / f"loans_{year}.parquet").exists():
            print(f"{year}: present, skipped")
            continue
        record = reduce_year(zip_path, args.out_dir, year)
        records.append(record)
        print(
            f"{year}: {record['loans']:,} loans, {record['performance_rows']:,} "
            f"performance rows, {record['performance_rows_kept']:,} kept, "
            f"{record['with_default_event']:,} with a default event, "
            f"{record['seconds']}s"
        )

    print(f"\n{len(records)} years reduced into {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
