#!/usr/bin/env python3
"""What the vintage trajectory does not tell you, measured rather than caveated.

The per-cohort default rate is the backbone every model result here is read
against, so the three things it silently depends on are worth putting numbers
on before any model exists.

  1. **The charge-off lag.** Lending Club publishes no charge-off date, so the
     default date is estimated from the last payment plus a lag. The lag is a
     policy assumption. If the level of the rate moves with it, every statement
     about the level carries the assumption; if the ordering of cohorts moves
     with it, so does every statement about the shape, and the trajectory is
     not a measurement at all.
  2. **The grade mix.** A book that stops writing its riskiest grades gets a
     lower realised default rate without any borrower behaving differently.
     Direct standardisation to a fixed mix separates the two, and the answer
     decides whether a sentence about the trajectory may say "the book's risk"
     or must say "the book's realised rate".
  3. **Repeat borrowers.** A time-ordered split assumes a loan in one window
     and a loan in another belong to different people. This file carries no
     borrower key, so that assumption cannot be checked directly; a proxy puts
     an upper bound on how much of it is at risk.

Nothing here is a model result. It is the width of the ground everything else
stands on.

    python scripts/record_run.py lc-label-sensitivity -- \
        python scripts/label_sensitivity.py data/raw/accepted_2007_to_2018Q4.csv.gz
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from outoftime.label import LabelDefinition, build_labels

MONTH_YEAR = "%b-%Y"
WINDOW = 12
LAGS = (0, 2, 3, 5, 8, 11)

# The mix every cohort is standardised to. Chosen as a cohort in the middle of
# the usable book and stated rather than derived, so the standardised series is
# reproducible and comparable across runs.
REFERENCE_COHORT = "2015Q2"

# The columns a borrower proxy is built from. Every one is knowable at
# application, and none identifies anybody: the zip is three digits, and the
# employer field is free text. The proxy overcounts by construction and its
# only job is an upper bound.
PROXY_COLUMNS = ["zip_code", "addr_state", "earliest_cr_line", "emp_title",
                 "home_ownership"]

# A cohort carries a standardised rate only where every grade it is
# standardised over is present in it.
MIN_LOANS = 5_000


def spearman(a: list[float], b: list[float]) -> float:
    """Rank correlation, written out rather than imported.

    The question it answers is whether two trajectories order their cohorts the
    same way, which is the part of a trajectory that survives an assumption
    about the level. Ties are given their average rank.
    """
    def ranks(values: list[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        out = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            average = (i + j) / 2 + 1
            for k in range(i, j + 1):
                out[order[k]] = average
            i = j + 1
        return out

    x, y = ranks(a), ranks(b)
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    vx = sum((xi - mx) ** 2 for xi in x) ** 0.5
    vy = sum((yi - my) ** 2 for yi in y) ** 0.5
    return cov / (vx * vy) if vx and vy else float("nan")


def load(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        usecols=["issue_d", "loan_status", "last_pymnt_d", "grade", "member_id",
                 *PROXY_COLUMNS],
        low_memory=False,
    )
    for column in ("issue_d", "last_pymnt_d"):
        frame[column] = pd.to_datetime(
            frame[column], format=MONTH_YEAR, errors="coerce")
    return frame.dropna(subset=["issue_d"]).reset_index(drop=True)


def to_dates(series: pd.Series) -> list[dt.date | None]:
    return [None if pd.isna(v) else v.date() for v in series]


def labelled_frame(frame: pd.DataFrame, snapshot: dt.date, lag: int) -> pd.DataFrame:
    labels = build_labels(
        origination=to_dates(frame["issue_d"]),
        status=list(frame["loan_status"]),
        last_payment=to_dates(frame["last_pymnt_d"]),
        definition=LabelDefinition(
            window_months=WINDOW, snapshot=snapshot, charge_off_lag_months=lag),
    )
    kept = frame.iloc[list(labels.indices)].copy()
    kept["label"] = list(labels.labels)
    kept["cohort"] = kept["issue_d"].dt.to_period("Q").astype(str)
    return kept, labels


def lag_sweep(frame: pd.DataFrame, snapshot: dt.date) -> dict:
    """The trajectory under every plausible lag, and whether its shape moves."""
    series: dict[str, dict[str, float]] = {}
    unrecognised: dict[str, int] = {}
    for lag in LAGS:
        kept, labels = labelled_frame(frame, snapshot, lag)
        big = kept.groupby("cohort").filter(lambda g: len(g) >= MIN_LOANS)
        rates = big.groupby("cohort")["label"].mean()
        series[str(lag)] = {k: round(float(v), 5) for k, v in rates.items()}
        unrecognised[str(lag)] = len(labels.unrecognised)

    shared = sorted(set.intersection(*(set(s) for s in series.values())))
    reference = series[str(LAGS[LAGS.index(5)])]
    correlations = {}
    for lag, rates in series.items():
        a = [reference[c] for c in shared]
        b = [rates[c] for c in shared]
        correlations[lag] = round(spearman(a, b), 4)
    levels = {lag: round(sum(r[c] for c in shared) / len(shared), 5)
              for lag, r in series.items()}
    return {
        "lags": list(LAGS),
        "cohorts_compared": shared,
        "trajectory_by_lag": series,
        "mean_rate_by_lag": levels,
        "rank_correlation_against_lag_5": correlations,
        "unrecognised_by_lag": unrecognised,
    }


def grade_standardised(frame: pd.DataFrame, snapshot: dt.date) -> dict:
    """The trajectory with the grade mix held fixed at one cohort's.

    Direct standardisation: each cohort's grade-specific rates are reweighted
    to the reference cohort's grade distribution. Where the two series diverge,
    the raw one is describing what the lender chose to write rather than how
    the borrowers behaved.
    """
    kept, _ = labelled_frame(frame, snapshot, 5)
    kept = kept.dropna(subset=["grade"])
    big = kept.groupby("cohort").filter(lambda g: len(g) >= MIN_LOANS)

    weights = big[big["cohort"] == REFERENCE_COHORT]["grade"].value_counts(
        normalize=True)
    by_grade = big.groupby(["cohort", "grade"])["label"].agg(["mean", "size"])

    raw, standardised, mix = {}, {}, {}
    for cohort, group in big.groupby("cohort"):
        raw[cohort] = round(float(group["label"].mean()), 5)
        shares = group["grade"].value_counts(normalize=True)
        mix[cohort] = {
            "risky_share": round(float(
                shares.reindex(["E", "F", "G"]).fillna(0).sum()), 5)}
        total = weight_used = 0.0
        for grade, weight in weights.items():
            if (cohort, grade) in by_grade.index:
                total += weight * float(by_grade.loc[(cohort, grade), "mean"])
                weight_used += weight
        standardised[cohort] = (
            round(total / weight_used, 5) if weight_used else None)
    return {
        "reference_cohort": REFERENCE_COHORT,
        "reference_mix": {k: round(float(v), 5) for k, v in weights.items()},
        "raw": raw,
        "standardised": standardised,
        "mix": mix,
    }


def borrower_proxy(frame: pd.DataFrame) -> dict:
    """An upper bound on repeat borrowing, since the file carries no key."""
    present = frame["member_id"].notna().sum() if "member_id" in frame else 0
    # A missing value is its own bucket rather than a wildcard, so two rows
    # that share nothing but their blanks do not become the same borrower.
    parts = [frame[column].fillna("~").astype(str) for column in PROXY_COLUMNS]
    key = parts[0]
    for part in parts[1:]:
        key = key + "|" + part
    quarters = frame["issue_d"].dt.to_period("Q").astype(str)
    grouped = pd.DataFrame({"key": key, "quarter": quarters})
    per_key = grouped.groupby("key")["quarter"].agg(["size", "nunique"])
    spanning = per_key[per_key["nunique"] > 1]
    rows_in_spanning = int(spanning["size"].sum())
    return {
        "columns": PROXY_COLUMNS,
        "member_id_non_null": int(present),
        "rows": len(frame),
        "distinct_keys": len(per_key),
        "keys_with_more_than_one_loan": int((per_key["size"] > 1).sum()),
        "keys_spanning_more_than_one_quarter": len(spanning),
        "rows_in_such_keys": rows_in_spanning,
        "share_of_rows": round(rows_in_spanning / len(frame), 5),
        "note": "an upper bound with an unknown false-positive rate: the zip is "
                "three digits and the employer field is free text, so unrelated "
                "borrowers collide",
    }


def plot(summary: dict, out: Path) -> None:
    """Level against shape, and mix against quality.

    The top panel answers whether the lag moves the trajectory or only lifts
    it. The bottom answers whether the book got riskier or only looks that way,
    and it is the panel that decides what a sentence about the trajectory is
    allowed to say.
    """
    figure, (top, bottom) = plt.subplots(2, 1, figsize=(12, 9))

    sweep = summary["lag"]
    cohorts = sweep["cohorts_compared"]
    x = range(len(cohorts))
    shades = plt.cm.plasma(
        [i / (len(sweep["lags"]) - 1) for i in range(len(sweep["lags"]))])
    for lag, colour in zip(sweep["lags"], shades):
        rates = sweep["trajectory_by_lag"][str(lag)]
        width = 2.6 if lag == 5 else 1.2
        top.plot(x, [rates[c] for c in cohorts], color=colour, linewidth=width,
                 marker="o" if lag == 5 else None, markersize=3,
                 label=f"lag {lag} months" + (" (the study's)" if lag == 5 else ""))
    top.set_yscale("log")
    top.set_ylabel(f"{WINDOW}-month default rate")
    top.yaxis.set_major_formatter(lambda v, _: f"{v:.1%}")
    top.yaxis.set_minor_formatter(lambda v, _: f"{v:.1%}")
    top.tick_params(axis="y", which="minor", labelsize=7)
    top.grid(axis="y", alpha=.25)
    top.legend(frameon=False, ncol=3, fontsize=9)
    top.set_title("The charge-off lag is not a nuisance parameter: it moves the "
                  "level of the trajectory by more than an order of magnitude")
    step = max(1, len(cohorts) // 20)
    top.set_xticks(list(x)[::step])
    top.set_xticklabels(cohorts[::step], rotation=90, fontsize=8)

    grade = summary["grade"]
    ordered = sorted(grade["raw"])
    gx = range(len(ordered))
    bottom.plot(gx, [grade["raw"][c] for c in ordered], color="#20303a",
                linewidth=2, marker="o", markersize=3, label="realised rate")
    bottom.plot(gx, [grade["standardised"][c] for c in ordered], color="#b0392b",
                linewidth=2, marker="s", markersize=3,
                label=f"standardised to the {grade['reference_cohort']} grade mix")
    bottom.set_ylabel(f"{WINDOW}-month default rate")
    bottom.yaxis.set_major_formatter(lambda v, _: f"{v:.1%}")
    bottom.grid(axis="y", alpha=.25)
    bottom.set_xticks(list(gx)[::step])
    bottom.set_xticklabels(ordered[::step], rotation=90, fontsize=8)
    bottom.set_xlabel("origination quarter")

    share = bottom.twinx()
    share.plot(gx, [grade["mix"][c]["risky_share"] for c in ordered],
               color="#9A5B24", linewidth=1.4, linestyle="--",
               label="share of the cohort in grades E, F, G")
    share.set_ylabel("share in grades E, F, G")
    share.set_ylim(0, None)
    lines = bottom.get_lines() + share.get_lines()
    bottom.legend(lines, [line.get_label() for line in lines],
                  frameon=False, fontsize=9, loc="upper left")

    figure.tight_layout()
    figure.savefig(out, dpi=140)
    plt.close(figure)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    frame = load(args.path)
    snapshot = frame["last_pymnt_d"].max().date()
    print(f"rows                  : {len(frame):,}")
    print(f"snapshot from data    : {snapshot}\n")

    summary = {
        "snapshot": snapshot.isoformat(),
        "window_months": WINDOW,
        "min_loans_per_cohort": MIN_LOANS,
        "lag": lag_sweep(frame, snapshot),
        "grade": grade_standardised(frame, snapshot),
        "borrower_proxy": borrower_proxy(frame),
    }

    sweep = summary["lag"]
    print(f"--- charge-off lag, {WINDOW}-month window, "
          f"{len(sweep['cohorts_compared'])} cohorts ---")
    print(f"{'lag':>5} {'mean rate':>10} {'rank corr vs 5':>15} "
          f"{'unrecognised':>13}")
    for lag in sweep["lags"]:
        print(f"{lag:>5} {sweep['mean_rate_by_lag'][str(lag)]:>9.2%} "
              f"{sweep['rank_correlation_against_lag_5'][str(lag)]:>15.4f} "
              f"{sweep['unrecognised_by_lag'][str(lag)]:>13,}")
    spread = [sweep["mean_rate_by_lag"][str(lag)] for lag in sweep["lags"]]
    print(f"\nlevel spans {min(spread):.2%} to {max(spread):.2%}, "
          f"a factor of {max(spread) / min(spread):.1f}")

    grade = summary["grade"]
    print(f"\n--- grade mix, standardised to {grade['reference_cohort']} ---")
    ordered = sorted(grade["raw"])
    print(f"{'cohort':>8} {'realised':>10} {'standardised':>13} {'E/F/G':>8}")
    for cohort in ordered[::4] + [ordered[-1]]:
        print(f"{cohort:>8} {grade['raw'][cohort]:>9.2%} "
              f"{grade['standardised'][cohort]:>12.2%} "
              f"{grade['mix'][cohort]['risky_share']:>7.1%}")

    proxy = summary["borrower_proxy"]
    print("\n--- borrower proxy ---")
    print(f"member_id non-null    : {proxy['member_id_non_null']:,}")
    print(f"rows in keys spanning more than one quarter: "
          f"{proxy['rows_in_such_keys']:,} ({proxy['share_of_rows']:.1%})")
    print("  upper bound only; the proxy collides unrelated borrowers")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "sensitivity.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    plot(summary, args.out_dir / "label-sensitivity.png")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
