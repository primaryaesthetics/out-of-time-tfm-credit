#!/usr/bin/env python3
"""The feature gates of the Lending Club book, and the matrix they leave.

Loads the book the Lending Club builds read — every loan of the accepted file
with a parseable issue date, the columns the matrix, the label and the gates
read, by `gbm_builds.load` — and runs on it the three reports of `features`
exactly as the builds call them: the redundancy report, which also measures
the two calendar carriers, coverage by onset, and the value rule with its two
caps. Then it writes what they decide and fits nothing:

  * `gates.json`, the three reports whole;
  * `features.json`, the kept columns in the order of the model matrix with
    their dtypes, every dropped column with the gate that removes it and the
    fields its report gives, the measured onset quarter of every column the
    coverage gate drops and the batches those onsets form, the constants the
    gates read, and the two caps with the share of the book each pins;
  * `dropped-columns.png`, one small panel per column the coverage or the
    value gate removes, with the share of its missing value or of its
    offending value by origination quarter, so that a reader sees the onset
    on the axis.

Nothing row-level is written.

    python scripts/record_run.py lc-features -- \\
        <venv python> scripts/lc_feature_run.py data/raw/accepted_2007_to_2018Q4.csv.gz \\
            --out-dir experiments/<date>-lc-features
"""

from __future__ import annotations

import argparse
import inspect
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from gbm_builds import load

from outoftime import features as fx
from outoftime.lending_club import AXIS, FEATURE_AVAILABILITY

MISSING = "missing"

# The window the coverage and value reports read when called without one, as
# the builds call them. Read from the signatures so the record states what ran.
WINDOW = {
    "first_quarter": inspect.signature(fx.coverage_report).parameters["first_quarter"].default,
    "last_quarter": inspect.signature(fx.coverage_report).parameters["last_quarter"].default,
}
if WINDOW != {
    key: inspect.signature(fx.value_report).parameters[key].default for key in WINDOW
}:
    raise SystemExit("coverage_report and value_report default to different windows")

A_PRIORI = {
    **{name: "free text" for name in sorted(fx.FREE_TEXT)},
    **{name: "geography below the state" for name in sorted(fx.FINE_GEOGRAPHY)},
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data", type=Path, help="the accepted-loans file of Lending Club")
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


def gate_reports(frame: pd.DataFrame) -> dict:
    """The three reports, called as the builds call them before fitting."""
    return {
        "redundancy": fx.redundancy_report(frame),
        "coverage": fx.coverage_report(frame),
        "values": fx.value_report(frame),
    }


def origination_knowable() -> set[str]:
    """Every column Lending Club reported at origination: what the gates partition."""
    return {name for name, offset in FEATURE_AVAILABILITY.items() if offset <= 0}


def dropped_columns(gates: dict) -> dict[str, dict]:
    """Every dropped column, the gate that removes it and what its report measured."""
    dropped: dict[str, dict] = {
        name: {"gate": "a priori", "reason": reason} for name, reason in A_PRIORI.items()
    }
    for name, record in gates["redundancy"].items():
        rule = "calendar carrier" if name in fx.CALENDAR_CARRIERS else "duplicate"
        dropped[name] = {"gate": "redundancy", "rule": rule, **record}
    for name, record in gates["coverage"].items():
        if record["kept"]:
            continue
        dropped[name] = {
            "gate": "coverage",
            "onset": record["onset"],
            "declared_onset": fx.LATE_COVERAGE[name],
            "first_quarter_share": record["first_quarter_share"],
            "peak_share": record["peak_share"],
        }
    for name, record in gates["values"].items():
        if record["kept"]:
            continue
        if name in dropped:
            raise SystemExit(f"{name} is dropped by {dropped[name]['gate']} and by values")
        dropped[name] = {"gate": "values", **{k: v for k, v in record.items() if k != "kept"}}
    return dropped


def partition(kept: list[str], dropped: dict, universe: set[str]) -> dict:
    """Checks that kept and dropped split the knowable columns, with none in both.

    A kept derived column stands for the raw column it is computed from, so the
    partition is over raw columns: `credit_history_months` counts as
    `earliest_cr_line`.
    """
    derived = {value: key for key, value in fx.DATE_TO_DURATION.items()}
    kept_raw = {derived.get(name, name) for name in kept}
    both = sorted(kept_raw & set(dropped))
    lost = sorted(universe - kept_raw - set(dropped))
    extra = sorted((kept_raw | set(dropped)) - universe)
    if both or lost or extra:
        raise SystemExit(
            f"the gates do not partition the knowable columns: in both {both}, "
            f"in neither {lost}, not knowable {extra}"
        )
    return {"knowable": len(universe), "kept": len(kept_raw), "dropped": len(dropped)}


def onset_batches(dropped: dict) -> dict[str, list[str]]:
    batches: dict[str, list[str]] = {}
    for name, record in dropped.items():
        if record["gate"] == "coverage":
            batches.setdefault(str(record["onset"]), []).append(name)
    return {quarter: sorted(batches[quarter]) for quarter in sorted(batches)}


def quarter_of(frame: pd.DataFrame) -> pd.Series:
    issued = frame[AXIS]
    return issued.dt.year.astype("Int64").astype(str) + "Q" + issued.dt.quarter.astype(
        "Int64").astype(str)


def offending(book: pd.DataFrame, name: str, record: dict) -> tuple[np.ndarray, np.ndarray]:
    """The loans a dropped column dates, and the loans the share is taken over.

    For a coverage drop, the loans missing the value, over every loan. For a
    value drop, the loans carrying a value the first cohort did not hold, over
    the loans carrying any value, as `value_report` measures its share.
    """
    raw = book[name]
    if record["gate"] == "coverage":
        return raw.isna().to_numpy(), np.ones(len(raw), dtype=bool)
    categorical = raw.dtype == object or name in fx.DECLARED_CATEGORICAL
    column = raw.astype(object) if categorical else pd.to_numeric(raw, errors="coerce")
    present = column.notna().to_numpy()
    support = record["first_cohort_support"]
    if categorical:
        outside = ~column.astype(str).isin(support).to_numpy()
    elif record["distinct_in_first_cohort"] <= 1:
        outside = (column != support[0]).to_numpy() if support else np.ones(len(raw), bool)
    else:
        outside = ((column < support[0]) | (column > support[1])).to_numpy()
    return outside & present, present


def plot(book: pd.DataFrame, dropped: dict, out: Path) -> None:
    quarters = quarter_of(book)
    inside = ((quarters >= WINDOW["first_quarter"]) & (quarters <= WINDOW["last_quarter"])
              & book[AXIS].notna()).to_numpy()
    order = sorted(quarters[inside].unique())
    names = sorted((n for n, r in dropped.items() if r["gate"] == "coverage"),
                   key=lambda n: (str(dropped[n]["onset"]), n))
    names += sorted(n for n, r in dropped.items() if r["gate"] == "values")
    columns = 7
    rows = max(1, math.ceil(len(names) / columns))
    figure, axes = plt.subplots(rows, columns, figsize=(2.6 * columns, 2.0 * rows),
                                sharex=True, squeeze=False)
    labels = quarters[inside].to_numpy()
    for axis, name in zip(axes.flat, names):
        record = dropped[name]
        hit, base = offending(book, name, record)
        hit, base = hit[inside], base[inside]
        share = (pd.Series(hit[base]).groupby(labels[base]).mean()
                 .reindex(order).to_numpy(dtype=float))
        # The panel draws what the gate read, or the figure is refused.
        if record["gate"] == "coverage":
            drawn, measured = round(1.0 - share[0], 4), record["first_quarter_share"]
        else:
            drawn, measured = round(float(hit[base].mean()), 6), record[
                "share_outside_first_cohort"]
        if drawn != measured:
            raise SystemExit(f"the panel of {name} draws {drawn}, the gate read {measured}")
        colour = "#0E6B66" if record["gate"] == "coverage" else "#9A5B24"
        axis.plot(range(len(order)), share, color=colour, linewidth=1.3)
        if record.get("onset") in order:
            axis.axvline(order.index(record["onset"]), color="#b0392b", linewidth=0.8,
                         linestyle=":")
        what = MISSING if record["gate"] == "coverage" else "outside the first cohort"
        axis.set_title(f"{name}\n{record['gate']}: {what}, onset {record.get('onset')}",
                       fontsize=6.5)
        # A missing share runs from none to all; an offending share is a few
        # percent at most on most columns and is drawn on its own scale.
        if record["gate"] == "coverage":
            axis.set_ylim(-0.02, 1.02)
        else:
            axis.set_ylim(bottom=0.0)
        axis.tick_params(axis="y", labelsize=6)
        axis.grid(axis="y", alpha=0.25)
    for axis in list(axes.flat)[len(names):]:
        axis.axis("off")
    step = max(1, len(order) // 8)
    for axis in axes[-1]:
        axis.set_xticks(range(0, len(order), step))
        axis.set_xticklabels(order[::step], rotation=90, fontsize=6)
    figure.suptitle(
        "every column the coverage or the value gate removes: the share of loans missing it "
        "(coverage)\nor carrying a value the first cohort did not hold (values), by origination "
        f"quarter, {WINDOW['first_quarter']} to {WINDOW['last_quarter']}; dotted, the "
        "measured onset; the value panels each on their own scale", fontsize=10)
    figure.tight_layout(rect=(0, 0, 1, 1 - 0.9 / (2.0 * rows)))
    figure.savefig(out, dpi=110)
    plt.close(figure)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    frame = load(args.data)
    quarters = quarter_of(frame)
    in_window = int(((quarters >= WINDOW["first_quarter"])
                     & (quarters <= WINDOW["last_quarter"])).sum())

    gates = gate_reports(frame)
    matrix = fx.model_matrix(frame)
    fx.assert_matrix_clean(matrix)

    kept = list(matrix.columns)
    dropped = dropped_columns(gates)
    split = partition(kept, dropped, origination_knowable())
    batches = onset_batches(dropped)
    caps = {name: gates["values"][name]["clip"] for name in fx.CLIPPED}
    features = {
        "book": {"rows": len(frame), "rows_in_window": in_window,
                 "first_origination": str(frame[AXIS].min().date()),
                 "last_origination": str(frame[AXIS].max().date())},
        "constants": {
            "COVERAGE_FLOOR": fx.COVERAGE_FLOOR,
            "FIRST_QUARTER": fx.FIRST_QUARTER,
            "VALUE_FLOOR": fx.VALUE_FLOOR,
            "window": WINDOW,
        },
        "partition": split,
        "kept": kept,
        "categorical": list(fx.categorical_names()),
        "derived": {derived: source for source, derived in fx.DATE_TO_DURATION.items()},
        "dropped_by_gate": {
            gate: sorted(n for n, r in dropped.items() if r["gate"] == gate)
            for gate in ("a priori", "redundancy", "coverage", "values")
        },
        "dropped": dropped,
        "coverage_onsets": batches,
        "caps": caps,
        "matrix": {"columns": kept,
                   "dtypes": {k: str(v) for k, v in matrix.dtypes.items()},
                   "rows": len(matrix)},
    }
    del matrix
    (args.out_dir / "gates.json").write_text(
        json.dumps(gates, indent=2, default=str), encoding="utf-8")
    (args.out_dir / "features.json").write_text(
        json.dumps(features, indent=2, default=str), encoding="utf-8")
    plot(frame, dropped, args.out_dir / "dropped-columns.png")

    print(f"rows                  : {len(frame):,} ({in_window:,} in "
          f"{WINDOW['first_quarter']}..{WINDOW['last_quarter']})")
    print(f"knowable columns      : {split['knowable']}")
    print(f"kept                  : {len(kept)}: {', '.join(kept)}")
    for gate, names in features["dropped_by_gate"].items():
        print(f"dropped, {gate:<13}: {len(names)}")
    for quarter, names in batches.items():
        print(f"coverage onset {quarter:<7}: {len(names)}")
    for name in features["dropped_by_gate"]["values"]:
        record = dropped[name]
        print(f"value {name:<28}: onset {record['onset']}, share "
              f"{record['share_outside_first_cohort']}: {record['reason']}")
    for name, clip in caps.items():
        low, high = clip["declared"]
        print(f"cap {name:<30}: {low:.6g} .. {high:.6g}, pins {clip['share_pinned']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
