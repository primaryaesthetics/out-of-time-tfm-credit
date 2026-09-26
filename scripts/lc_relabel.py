#!/usr/bin/env python3
"""One Lending Club build's recorded scores, relabelled at twenty-four months.

ADR-0005 registers the label at twelve months and the same trajectory at
twenty-four months beside it. This script puts the twenty-four-month label of
C-004 (the same file, the snapshot the file reports, the five-month charge-off
lag, the window twenty-four months) beside `outcome` in a copy of every score
file of one build, so that `arm_intervals.py --outcome outcome_24` reads the
recorded scores against it. Nothing is refitted and no recorded file is
written to: each score directory of the build is copied into a directory of
its own under `--out-dir`, its `scores.parquet` rewritten with the column
added and its `reference.parquet` and `derive.json` copied byte for byte.

A scored row whose twenty-four-month window is open at the snapshot has no
label. It is dropped and counted, never written as a non-default. A cohort
enters the copies whole or not at all: if any of its scored rows has an open
window, every row of it leaves and is counted, so a cell is never read on part
of its rows. On this book the window closes for loans originated on or before
2017-03-01, so every quarter through 2017Q1 enters whole and every later one
leaves whole.

The row is a position in the loaded file, as `score_build.py` writes it. The
twelve-month label is rebuilt from the file beside the twenty-four-month one
and has to equal the recorded `outcome` on every scored row of every
directory; a row where it does not refuses the build, since the positions
would then name other loans. A twelve-month default is a twenty-four-month
default by construction, and a row where that fails refuses the build too.

A build none of whose cohorts has closed writes its account and no copy.

    python scripts/record_run.py lc-2013h1e-label24 -- \\
        python scripts/lc_relabel.py data/raw/accepted_2007_to_2018Q4.csv.gz \\
            experiments/2026-09-11-lc-2013h1e-intervals-grid \\
            --out-dir experiments/<date>-lc-2013h1e-label24
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import arm_intervals as ai
import record_run as rr

from outoftime.label import LabelDefinition, build_labels
from outoftime.lending_club import AXIS
from outoftime.vintage import LABEL_LAG_MONTHS

MONTH_YEAR = "%b-%Y"
WINDOW_MONTHS = 24
COLUMN = "outcome_24"
# Copied beside the rewritten scores: what arm_intervals.py reads from a score
# directory other than its scores.
COPIED = ("reference.parquet", "derive.json")


def load(path: Path) -> pd.DataFrame:
    """The label's three columns, rows at the positions `score_build.load` gives them.

    `score_build.load` drops the rows with no origination date and renumbers;
    the drop reads the origination column alone, so the positions agree.
    """
    frame = pd.read_csv(path, usecols=[AXIS, "loan_status", "last_pymnt_d"], low_memory=False)
    for column in (AXIS, "last_pymnt_d"):
        frame[column] = pd.to_datetime(frame[column], format=MONTH_YEAR, errors="coerce")
    return frame.dropna(subset=[AXIS]).reset_index(drop=True)


def to_dates(series: pd.Series) -> list[dt.date | None]:
    return [None if pd.isna(v) else v.date() for v in series]


def labels_at(frame: pd.DataFrame, window_months: int) -> tuple[np.ndarray, dict]:
    """Every position's label under the window, -1 where the window is open at the snapshot."""
    snapshot = frame["last_pymnt_d"].max().date()
    labelled = build_labels(
        origination=to_dates(frame[AXIS]), status=list(frame["loan_status"]),
        last_payment=to_dates(frame["last_pymnt_d"]),
        definition=LabelDefinition(window_months=window_months, snapshot=snapshot))
    out = np.full(len(frame), -1, dtype=np.int64)
    out[np.asarray(labelled.indices, dtype=np.int64)] = np.asarray(labelled.labels, dtype=np.int64)
    return out, labelled.as_dict()


def relabel(sources: list[Path], twelve: np.ndarray, longer: np.ndarray, out_dir: Path) -> dict:
    """Writes the copies of one build's score directories and returns the account of it."""
    builds: set[str] = set()
    scored: list[pd.DataFrame] = []
    for source in sources:
        rows = pd.read_parquet(source / "scores.parquet", columns=["build_id", "cohort", "row", "outcome"])
        builds.update(str(b) for b in rows["build_id"].unique())
        position = rows["row"].to_numpy(dtype=np.int64)
        if position.min() < 0 or position.max() >= twelve.size:
            raise SystemExit(f"{source.as_posix()}: a row outside the file's {twelve.size:,} positions")
        if not np.array_equal(rows["outcome"].to_numpy(dtype=np.int64), twelve[position]):
            raise SystemExit(f"{source.as_posix()}: the recorded outcome differs from the "
                             f"{LABEL_LAG_MONTHS}-month label rebuilt from the file, so its rows "
                             "do not name the loans at those positions")
        scored.append(rows[["cohort", "row"]])
    if len(builds) != 1:
        raise SystemExit("one build per invocation: " + ", ".join(sorted(builds)))
    (build,) = builds

    distinct = pd.concat(scored, ignore_index=True).drop_duplicates()
    distinct["cohort"] = distinct["cohort"].astype(str)
    if distinct["row"].duplicated().any():
        raise SystemExit(f"{build}: a row is scored in two cohorts")
    distinct["outcome"] = twelve[distinct["row"].to_numpy()]
    distinct[COLUMN] = longer[distinct["row"].to_numpy()]
    labelled = distinct[distinct[COLUMN] >= 0]
    if (labelled[COLUMN] < labelled["outcome"]).any():
        raise SystemExit(f"{build}: a {LABEL_LAG_MONTHS}-month default is not a "
                         f"{WINDOW_MONTHS}-month default")

    cohorts: dict[str, dict] = {}
    kept: list[str] = []
    for cohort, frame in distinct.groupby("cohort", sort=True):
        cohort = str(cohort)
        open_rows = int((frame[COLUMN] < 0).sum())
        whole = open_rows == 0
        cohorts[cohort] = {
            "rows": len(frame), "open_window_rows": open_rows, "enters": whole,
            "rows_dropped": 0 if whole else len(frame),
            "defaults_12": int(frame["outcome"].sum()),
            "defaults_24": int(frame[COLUMN].sum()) if whole else None,
        }
        if whole:
            kept.append(cohort)

    labels = distinct[distinct["cohort"].isin(kept)].sort_values(["cohort", "row"])
    copies: list[str] = []
    if kept:
        out_dir.mkdir(parents=True, exist_ok=True)
        labels.to_parquet(out_dir / "labels.parquet", index=False)
        names = [s.name for s in sources]
        if len(set(names)) != len(names):
            raise SystemExit(f"{build}: two score directories share a name")
        for source in sources:
            target = out_dir / source.name
            target.mkdir(parents=True, exist_ok=True)
            scores = pd.read_parquet(source / "scores.parquet")
            scores = scores[scores["cohort"].astype(str).isin(kept)]
            label = labels[["cohort", "row", COLUMN]].rename(columns={"cohort": "_cohort"})
            joined = scores.assign(_cohort=scores["cohort"].astype(str)).merge(
                label, on=["_cohort", "row"], how="left", validate="many_to_one"
            ).drop(columns="_cohort")
            if joined[COLUMN].isna().any():
                raise SystemExit(f"{source.as_posix()}: a row of a closed cohort without its label")
            joined[COLUMN] = joined[COLUMN].astype(np.int64)
            joined.to_parquet(target / "scores.parquet", index=False)
            for name in COPIED:
                if (source / name).is_file():
                    shutil.copyfile(source / name, target / name)
            copies.append(target.as_posix())

    dropped = [c for c in cohorts if not cohorts[c]["enters"]]
    return {
        "build_id": build,
        "column": COLUMN,
        "cells_kept": len(kept),
        "cells_dropped": len(dropped),
        "cohorts_kept": kept,
        "cohorts_dropped": dropped,
        "rows_kept": len(labels),
        "rows_dropped": int(sum(cohorts[c]["rows_dropped"] for c in dropped)),
        "open_window_rows": int(sum(v["open_window_rows"] for v in cohorts.values())),
        "cohorts": cohorts,
        "sources": [s.as_posix() for s in sources],
        "copies": copies,
        "rule": "a scored row whose window is open at the snapshot has no label and is dropped, "
                "never written as a non-default; a cohort with any such row leaves whole and "
                "every row of it is counted under rows_dropped",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data", type=Path, help="the Lending Club file score_build.py read")
    parser.add_argument("dirs", type=Path, nargs="+",
                        help="the build's score directories, or a recorded pooling naming them")
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    sources = ai.expand_sources(args.dirs)
    for source in sources:
        target = args.out_dir / source.name
        if target.resolve() == source.resolve():
            raise SystemExit(f"{source.as_posix()}: the copy would overwrite the recorded directory")
    frame = load(args.data)
    twelve, twelve_record = labels_at(frame, LABEL_LAG_MONTHS)
    longer, longer_record = labels_at(frame, WINDOW_MONTHS)
    del frame
    account = relabel(sources, twelve, longer, args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    account["label"] = {"12": twelve_record, "24": longer_record}
    account["inputs"] = {item.as_posix(): rr.file_hash(item)
                         for source in sources for item in sorted(source.rglob("*"))
                         if item.is_file()}
    (args.out_dir / "label24.json").write_text(json.dumps(account, indent=2) + "\n",
                                               encoding="utf-8")

    print(f"build                 : {account['build_id']}")
    print(f"snapshot              : {longer_record['definition']['snapshot']}, last labelable "
          f"origination {longer_record['definition']['last_labelable_origination']} at "
          f"{WINDOW_MONTHS} months")
    print(f"cells                 : {account['cells_kept']} kept, {account['cells_dropped']} dropped")
    print(f"rows                  : {account['rows_kept']:,} kept, {account['rows_dropped']:,} "
          f"dropped, {account['open_window_rows']:,} of them with an open window")
    for cohort, entry in account["cohorts"].items():
        if entry["enters"]:
            print(f"  {cohort} {entry['rows']:>7,} rows  defaults {entry['defaults_12']:>6,} at 12, "
                  f"{entry['defaults_24']:>6,} at 24")
        else:
            print(f"  {cohort} {entry['rows']:>7,} rows  dropped whole, "
                  f"{entry['open_window_rows']:,} with an open window")
    if not account["copies"]:
        print("no cohort of this build has closed; no copy is written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
