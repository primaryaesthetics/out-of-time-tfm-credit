#!/usr/bin/env python3
"""Fits the scorecard on every build of the grid and scores every cohort after it.

This is the study's classical baseline carried across the whole vintage grid:
nine as-of dates by two training arms, each card binned and fitted on that
build's training rows alone, then scored on the fixed per-quarter samples of
every cohort originated after the build date.

It answers three questions before any accelerator is rented. Does a scorecard
built the way a risk team builds one land where a credit model should on this
book? Does its discrimination decay as it ages, and how fast? And does its
composition — which characteristics it keeps at all — move across the grid,
which is a form of instability no per-cohort metric shows.

The discrimination and calibration numbers here are point estimates. The
intervals, the Murphy decomposition and the population-stability inference
belong to the metrics module and are not approximated here.

    python scripts/record_run.py lc-scorecard-builds -- \
        python scripts/scorecard_builds.py data/raw/accepted_2007_to_2018Q4.csv.gz \
            --out-dir experiments/2026-09-04-lc-scorecard-builds
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from outoftime import scorecard as sc
from outoftime.features import (
    CALENDAR_CARRIERS,
    DATE_TO_DURATION,
    FINE_GEOGRAPHY,
    FREE_TEXT,
    LATE_COVERAGE,
    REDUNDANT,
    VALUE_CARRIERS,
    coverage_report,
    feature_names,
    model_matrix,
    redundancy_report,
    value_report,
)
from outoftime.label import LabelDefinition, build_labels
from outoftime.lending_club import AXIS, LABEL_SOURCES
from outoftime.vintage import (
    DEFAULT_AS_OF,
    LABEL_LAG_MONTHS,
    ROLLING_QUARTERS,
    TEST_SAMPLE_SEED,
    Quarter,
    builds,
)

MONTH_YEAR = "%b-%Y"
ARMS = {"E": "expanding", "R": f"rolling, {ROLLING_QUARTERS} quarters"}
ARM_COLOUR = {"E": "#0E6B66", "R": "#9A5B24"}


def raw_columns() -> list[str]:
    """What the matrix, the redundancy check, the label and the drop report read."""
    needed = set(feature_names()) - set(DATE_TO_DURATION.values())
    needed |= set(DATE_TO_DURATION) | set(REDUNDANT) | set(REDUNDANT.values())
    needed |= {AXIS} | set(LABEL_SOURCES) | FREE_TEXT | FINE_GEOGRAPHY
    needed |= set(CALENDAR_CARRIERS) | set(LATE_COVERAGE) | set(VALUE_CARRIERS)
    return sorted(needed)


def dropped_report(frame: pd.DataFrame) -> dict[str, dict]:
    """How wide the columns this study drops actually are on the book it uses.

    Free text and three-digit geography are dropped on an argument about
    cardinality, and an argument about cardinality is worth exactly the count
    behind it. Measured here so that the count lives in a recorded run rather
    than in a docstring.
    """
    out = {}
    for name in sorted(FREE_TEXT | FINE_GEOGRAPHY):
        column = frame[name]
        out[name] = {
            "reason": "free text" if name in FREE_TEXT else "geography below the state",
            "distinct": int(column.nunique(dropna=True)),
            "missing_share": round(float(column.isna().mean()), 6),
        }
    return out


def load(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, usecols=raw_columns(), low_memory=False)
    for column in (AXIS, "last_pymnt_d"):
        frame[column] = pd.to_datetime(frame[column], format=MONTH_YEAR, errors="coerce")
    return frame.dropna(subset=[AXIS]).reset_index(drop=True)


def to_dates(series: pd.Series) -> list[dt.date | None]:
    return [None if pd.isna(v) else v.date() for v in series]


def auc(outcome: np.ndarray, score: np.ndarray) -> float:
    """The Mann-Whitney statistic, with ties split as the definition requires."""
    from scipy.stats import rankdata

    positives = int(outcome.sum())
    negatives = int(outcome.size - positives)
    if positives == 0 or negatives == 0:
        return float("nan")
    ranks = rankdata(score)
    return float((ranks[outcome == 1].sum() - positives * (positives + 1) / 2)
                 / (positives * negatives))


def ks(outcome: np.ndarray, score: np.ndarray) -> float:
    """The largest gap between the two cumulative score distributions."""
    order = np.argsort(score, kind="mergesort")
    ordered = outcome[order]
    positives, negatives = ordered.sum(), (1 - ordered).sum()
    if positives == 0 or negatives == 0:
        return float("nan")
    return float(np.abs(np.cumsum(ordered) / positives
                        - np.cumsum(1 - ordered) / negatives).max())


def cohort_metrics(outcome: np.ndarray, predicted: np.ndarray) -> dict:
    area = auc(outcome, predicted)
    observed = float(outcome.mean())
    expected = float(predicted.mean())
    return {
        "rows": int(outcome.size),
        "defaults": int(outcome.sum()),
        "auc": round(area, 6),
        "gini": round(2 * area - 1, 6),
        "ks": round(ks(outcome, predicted), 6),
        "brier": round(float(np.mean((predicted - outcome) ** 2)), 8),
        "observed_rate": round(observed, 6),
        "expected_rate": round(expected, 6),
        "observed_over_expected": round(observed / expected, 6) if expected else None,
    }


def age_in_quarters(as_of: dt.date, cohort: Quarter) -> int:
    """How old the model is when it scores this cohort, in quarters."""
    built = Quarter.of(as_of)
    return (cohort.year * 4 + cohort.quarter) - (built.year * 4 + built.quarter)


def fit_grid(
    matrix: pd.DataFrame,
    labels: list[int | None],
    origination: list[dt.date | None],
    labelled,
    *,
    as_of_dates,
    policy: sc.ScorecardPolicy,
    verbose: bool = True,
) -> dict:
    outcome = np.asarray([-1 if v is None else v for v in labels])
    summary: dict = {"arms": {}}
    for arm, name in ARMS.items():
        rows = []
        for build in builds(
            origination, as_of_dates=as_of_dates, arm=arm, labels=labelled
        ):
            started = time.time()
            card = sc.fit(matrix, labels, rows=build.train, policy=policy)
            elapsed = time.time() - started

            cohorts = []
            for quarter, positions in build.test:
                predicted = card.predict_pd(matrix, rows=positions)
                metrics = cohort_metrics(outcome[list(positions)], predicted)
                metrics["cohort"] = str(quarter)
                metrics["age_quarters"] = age_in_quarters(build.as_of, quarter)
                cohorts.append(metrics)

            record = {
                "build_id": build.build_id,
                "as_of": build.as_of.isoformat(),
                "arm": arm,
                "train_rows": len(build.train),
                "train_first": build.train_first.isoformat(),
                "train_last": build.train_last.isoformat(),
                "fit_seconds": round(elapsed, 2),
                "card": card.as_dict(),
                "bins": card.bin_tables(),
                "cohorts": cohorts,
            }
            rows.append(record)
            if verbose:
                youngest, oldest = cohorts[0], cohorts[-1]
                print(
                    f"{build.build_id:>9} {len(build.train):>9,} rows  "
                    f"{len(card.characteristics):>2} chars  "
                    f"fit {elapsed:>6.1f}s  "
                    f"gini {youngest['gini']:.3f}->{oldest['gini']:.3f}  "
                    f"O/E {youngest['observed_over_expected']:.2f}->"
                    f"{oldest['observed_over_expected']:.2f}",
                    flush=True,
                )
        summary["arms"][arm] = rows
        if verbose:
            print(f"--- arm {arm}: {name} done ---\n", flush=True)
    return summary


def determinism_check(
    matrix: pd.DataFrame, labels, origination, labelled, *, as_of_dates, policy
) -> dict:
    """Refits the smallest build twice and reports whether it landed identically.

    The binning solver is given a time limit, and a solver that runs out of time
    returns the best split it found rather than the best split there is. That is
    the one component here that could make a rerun disagree with itself, so the
    disagreement is measured rather than assumed away.
    """
    build = builds(origination, as_of_dates=as_of_dates[:1], arm="E", labels=labelled)[0]
    first = sc.fit(matrix, labels, rows=build.train, policy=policy)
    second = sc.fit(matrix, labels, rows=build.train, policy=policy)
    same_names = first.names == second.names
    gaps = [
        abs(first.coefficients[n] - second.coefficients[n])
        for n in first.names
        if n in second.coefficients
    ]
    return {
        "build_id": build.build_id,
        "same_characteristics": same_names,
        "max_coefficient_gap": max(gaps) if gaps else None,
        "same_bins": first.bin_tables() == second.bin_tables(),
    }


def write_bins(summary: dict, path: Path) -> None:
    fields = [
        "arm", "build_id", "characteristic", "bin", "count", "count_share",
        "non_event", "event", "event_rate", "woe", "iv",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for arm, records in summary["arms"].items():
            for record in records:
                for row in record["bins"]:
                    writer.writerow({"arm": arm, "build_id": record["build_id"], **row})


def write_cohorts(summary: dict, path: Path) -> None:
    fields = [
        "arm", "build_id", "as_of", "cohort", "age_quarters", "rows", "defaults",
        "auc", "gini", "ks", "brier", "observed_rate", "expected_rate",
        "observed_over_expected",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for arm, records in summary["arms"].items():
            for record in records:
                for row in record["cohorts"]:
                    writer.writerow({
                        "arm": arm, "build_id": record["build_id"],
                        "as_of": record["as_of"], **row,
                    })


def plot_trajectories(summary: dict, out: Path) -> None:
    """Discrimination against model age, one line per build, one panel per arm."""
    figure, panels = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
    for panel, (arm, name) in zip(panels, ARMS.items()):
        records = summary["arms"][arm]
        shades = plt.cm.viridis(np.linspace(0, .88, len(records)))
        for record, colour in zip(records, shades):
            ages = [c["age_quarters"] for c in record["cohorts"]]
            panel.plot(ages, [c["gini"] for c in record["cohorts"]], marker="o",
                       markersize=3.5, linewidth=1.5, color=colour,
                       label=record["build_id"][:-2])
        panel.set_title(f"arm {arm}: {name}")
        panel.set_xlabel("model age at scoring, quarters")
        panel.grid(alpha=.25)
    panels[0].set_ylabel("Gini on the cohort's fixed sample")
    panels[1].legend(frameon=False, fontsize=8, ncol=2, title="build")
    figure.suptitle(
        "Discrimination against model age, one line per build: where the lines "
        "wiggle together they are scoring the same cohort, not reaching the same age",
        y=.99)
    figure.tight_layout()
    figure.savefig(out, dpi=140)
    plt.close(figure)


def plot_calibration(summary: dict, out: Path) -> None:
    """The book's realised rate against what each ageing card expected of it."""
    figure, panels = plt.subplots(2, 1, figsize=(13, 8.4), sharex=True)
    quarters = sorted(
        {c["cohort"] for r in summary["arms"]["E"] for c in r["cohorts"]},
        key=lambda q: (int(q[:4]), int(q[-1])),
    )
    position = {q: i for i, q in enumerate(quarters)}

    observed = {}
    for record in summary["arms"]["E"]:
        for cohort in record["cohorts"]:
            observed[cohort["cohort"]] = cohort["observed_rate"]

    for panel, (arm, name) in zip(panels, ARMS.items()):
        records = summary["arms"][arm]
        shades = plt.cm.viridis(np.linspace(0, .88, len(records)))
        for record, colour in zip(records, shades):
            x = [position[c["cohort"]] for c in record["cohorts"]]
            panel.plot(x, [c["expected_rate"] for c in record["cohorts"]],
                       marker="o", markersize=3, linewidth=1.3, color=colour,
                       label=record["build_id"][:-2])
        panel.plot([position[q] for q in quarters],
                   [observed[q] for q in quarters], color="#20303a", linewidth=2.2,
                   linestyle="--", label="realised")
        panel.set_ylabel(f"{summary['label_lag_months']}-month default rate")
        panel.yaxis.set_major_formatter(lambda v, _: f"{v:.1%}")
        panel.set_title(f"arm {arm}: {name}")
        panel.grid(alpha=.25)
    panels[0].legend(frameon=False, fontsize=8, ncol=5)
    panels[1].set_xticks(range(len(quarters)))
    panels[1].set_xticklabels(quarters, rotation=90, fontsize=8)
    panels[1].set_xlabel("origination quarter scored")
    figure.suptitle(
        "Calibration in the large by cohort scored: what each build expected of "
        "every later cohort against the rate the book realised.\nCards of nine "
        "ages bunch together; the gap follows the calendar, not the card",
        y=.995, fontsize=11)
    figure.tight_layout()
    figure.savefig(out, dpi=140)
    plt.close(figure)


def plot_composition(summary: dict, out: Path) -> None:
    """Which characteristics the card keeps, build by build, and at what weight."""
    figure, panels = plt.subplots(
        1, 2, figsize=(14, 8.6), sharey=True,
        gridspec_kw={"width_ratios": (1, 1)})
    # Every column the matrix offered, so that a characteristic no build ever
    # kept shows as a row of dots rather than vanishing from the picture.
    order = sorted(summary["characteristics_offered"])

    grids = {}
    for arm in ARMS:
        records = summary["arms"][arm]
        grid = np.full((len(order), len(records)), np.nan)
        for column, record in enumerate(records):
            for characteristic in record["card"]["characteristics"]:
                grid[order.index(characteristic["name"]), column] = characteristic["iv"]
        grids[arm] = grid
    # One colour scale for both panels, so that the same IV is the same shade
    # whichever arm it appears in.
    finite = [np.nanmax(g) for g in grids.values() if np.isfinite(g).any()]
    vmax = max(finite) if finite else 1

    for panel, (arm, name) in zip(panels, ARMS.items()):
        records = summary["arms"][arm]
        grid = grids[arm]
        for column, record in enumerate(records):
            card = record["card"]
            # The three ways a cell is blank, drawn differently: a cross for a
            # characteristic the sign check removed, a dot for one the IV
            # screen refused, and a hatch for one that carried a single value
            # on the training rows and was never offered to the binner.
            for characteristic in card["dropped_wrong_sign"]:
                if characteristic in order:
                    panel.plot(column, order.index(characteristic), marker="x",
                               color="#b0392b", markersize=5, linestyle="none")
            for characteristic in card["screened_out"]:
                if characteristic in order:
                    panel.plot(column, order.index(characteristic), marker=".",
                               color="#8a8f94", markersize=4, linestyle="none")
            for characteristic in card["constant_on_train"]:
                if characteristic in order:
                    panel.add_patch(plt.Rectangle(
                        (column - .5, order.index(characteristic) - .5), 1, 1,
                        facecolor="none", edgecolor="#8a8f94", hatch="////",
                        linewidth=0))
        image = panel.imshow(grid, aspect="auto", cmap="magma_r", vmin=0, vmax=vmax)
        panel.set_xticks(range(len(records)))
        panel.set_xticklabels([r["build_id"][:-2] for r in records], rotation=90,
                              fontsize=8)
        panel.set_title(f"arm {arm}: {name}")
        figure.colorbar(image, ax=panel, fraction=.03, pad=.02,
                        label="information value")
    panels[0].set_yticks(range(len(order)))
    panels[0].set_yticklabels(order, fontsize=8)
    figure.suptitle(
        "The card's own composition across the grid. Colour: kept, at its IV. "
        "Cross: removed for a wrong sign.\nDot: below the IV screen. "
        "Hatch: one value on the training rows, never offered.", y=.995,
        fontsize=11)
    figure.tight_layout()
    figure.savefig(out, dpi=140)
    plt.close(figure)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("."))
    parser.add_argument(
        "--as-of", type=dt.date.fromisoformat, nargs="+", default=list(DEFAULT_AS_OF),
        help="build dates; the full nine-date grid unless given otherwise")
    parser.add_argument(
        "--n-jobs", type=int, default=-1,
        help="binning workers; every characteristic is binned independently, so "
             "this changes the wall clock and not the result")
    args = parser.parse_args(argv)

    policy = sc.ScorecardPolicy(n_jobs=args.n_jobs)
    partial = list(args.as_of) != list(DEFAULT_AS_OF)
    if partial:
        print("running a partial grid; this is not the study's grid\n")

    started = time.time()
    frame = load(args.path)
    snapshot = frame["last_pymnt_d"].max().date()
    origination = to_dates(frame[AXIS])
    print(f"rows                  : {len(frame):,}")
    print(f"snapshot from data    : {snapshot}")
    print(f"loaded in             : {time.time() - started:.0f}s")

    dropped = dropped_report(frame)
    for name, report in dropped.items():
        print(f"dropped               : {name}, {report['reason']}, "
              f"{report['distinct']:,} distinct values")

    redundancy = redundancy_report(frame)
    for dropped_name, report in redundancy.items():
        print(f"redundant             : {dropped_name} against {report['duplicates']}, "
              + ", ".join(f"{k}={v}" for k, v in report.items() if k != "duplicates"))

    coverage = coverage_report(frame)
    late = sorted((r["onset"], n) for n, r in coverage.items() if not r["kept"])
    print(f"coverage              : {sum(r['kept'] for r in coverage.values())} columns "
          f"present from {min(r['onset'] for r in coverage.values() if r['kept'])}, "
          f"{len(late)} begin later and are out")
    for onset in sorted({o for o, _ in late}):
        names = [n for o, n in late if o == onset]
        print(f"                        {onset}: {len(names)} columns, e.g. {', '.join(names[:4])}")

    values = value_report(frame)
    carriers = sorted((r["onset"] or "", n) for n, r in values.items() if not r["kept"])
    print(f"values                : {sum(r['kept'] for r in values.values())} columns hold "
          f"only values their first cohort held; {len(carriers)} carry the calendar by "
          f"value and are out")
    for onset, name in carriers:
        report = values[name]
        print(f"                        {name}: from {onset}, "
              f"{report['share_outside_first_cohort']:.1%} of the book, "
              f"{report['distinct_in_first_cohort']} value(s) in the first cohort")
    for name, report in values.items():
        if "clip" in report:
            print(f"clipped               : {name} to {report['clip']['declared']}, "
                  f"the first cohort's own range")

    labelled = build_labels(
        origination=origination,
        status=list(frame["loan_status"]),
        last_payment=to_dates(frame["last_pymnt_d"]),
        definition=LabelDefinition(window_months=LABEL_LAG_MONTHS, snapshot=snapshot),
    )
    labels: list[int | None] = [None] * len(frame)
    for i, value in zip(labelled.indices, labelled.labels):
        labels[i] = value
    print(f"labelled              : {labelled.size:,}")

    matrix = model_matrix(frame)
    del frame
    print(f"model matrix          : {matrix.shape[1]} characteristics\n")

    determinism = determinism_check(
        matrix, labels, origination, labelled,
        as_of_dates=args.as_of, policy=policy,
    )
    print(f"determinism, refitting {determinism['build_id']}: "
          f"same characteristics {determinism['same_characteristics']}, "
          f"same bins {determinism['same_bins']}, "
          f"largest coefficient gap {determinism['max_coefficient_gap']}\n")

    summary = fit_grid(
        matrix, labels, origination, labelled,
        as_of_dates=args.as_of, policy=policy,
    )
    summary.update({
        "snapshot": snapshot.isoformat(),
        "label_lag_months": LABEL_LAG_MONTHS,
        "as_of_dates": [d.isoformat() for d in args.as_of],
        "partial_grid": partial,
        "label": labelled.as_dict(),
        "policy": policy.as_dict(),
        "seeds": {"test_sample": TEST_SAMPLE_SEED},
        "tuning_budget": "none: the policy is fixed and no search is run",
        "characteristics_offered": list(matrix.columns),
        "dropped_columns": dropped,
        "redundancy": redundancy,
        "coverage": coverage,
        "values": values,
        "entity_check": (
            "not run: the file carries no borrower key (member_id is null on every "
            "row and id is the loan), so a repeat borrower can sit in a training "
            "pool and in a scored cohort undetected"
        ),
        "determinism": determinism,
        "wall_seconds": round(time.time() - started, 1),
    })

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "scorecard.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    write_bins(summary, args.out_dir / "bins.csv")
    write_cohorts(summary, args.out_dir / "cohorts.csv")
    plot_trajectories(summary, args.out_dir / "gini-trajectory.png")
    plot_calibration(summary, args.out_dir / "calibration-drift.png")
    plot_composition(summary, args.out_dir / "card-composition.png")

    # Two columns per metric: the first cohort each build scores, which is a
    # different quarter for every build, and the last cohort of the book, which
    # is the same 20,000 rows for every build. Read down the second column for
    # the effect of build date on one cohort; read across a row for the effect
    # of the calendar on one card. Neither is model age on its own.
    shared = summary["arms"]["E"][0]["cohorts"][-1]["cohort"]
    print(f"{'build':>9} {'chars':>6} {'dropped':>8} {'first cohort':>13} "
          f"{'gini':>6} {shared + ' gini':>12} {'O/E':>6} {shared + ' O/E':>11}")
    for arm in ARMS:
        for record in summary["arms"][arm]:
            first, last = record["cohorts"][0], record["cohorts"][-1]
            print(f"{record['build_id']:>9} "
                  f"{record['card']['n_characteristics']:>6} "
                  f"{len(record['card']['dropped_wrong_sign']):>8} "
                  f"{first['cohort']:>13} "
                  f"{first['gini']:>6.3f} {last['gini']:>12.3f} "
                  f"{first['observed_over_expected']:>6.2f} "
                  f"{last['observed_over_expected']:>11.2f}")
    print(f"\nwall: {summary['wall_seconds']:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
