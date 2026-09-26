#!/usr/bin/env python3
"""EXP-004's kill criteria, read from the recorded protocol table and pooling.

The table (`protocol_table.py`) records every model's metrics per in-time
unit, one fold's test cell under one context draw, and the mean over the
build's cohorts out of time. The criteria read differences between models
and their spread, which the table does not print. This script computes them
from the table's `cells.csv` and the out-of-time pooling's `paired.csv`, and
applies each criterion as EXP-004 writes it. Definitions, fixed before any
of the numbers below was computed:

- **The five models** are the scorecard, the GBM, GBM-50k, TabPFN and TabICL
  at the shipped setting. The rows at 1.0 (`tabpfn@t1`, `tabicl@t1`) are
  read beside, in the same way, and enter no verdict.
- **An in-time difference** A − B is taken per unit: on each fold, per
  context draw when either model is drawn (a drawn model against another
  drawn model on the same draw, since the foundation models and the control
  read the same 50,000 rows; an undrawn model against each draw of a drawn
  one), and on each fold alone when neither is. Its point is the mean over
  the units, its **fold spread** the least and the greatest unit value, the
  convention the table's brackets use for a single model.
- **An out-of-time difference** and its interval are the pooling's row for
  the pair on all cohorts, the primary bootstrap seed, no draw held fixed;
  a pair is **starred** when that row excludes zero.
- **Criterion 1** (the protocol does not change the ranking) fires when, on
  every starred Gini pair, the in-time difference has the out-of-time sign
  and its fold spread excludes zero on that side.
- **Criterion 2** (the scalar sees the level) fires when the Brier score
  and the log-loss both order the five models as |log O/E| orders them, in
  time and out of time, each order taken on the table's means at full
  precision.
- **Criterion 3** (the threshold is unreadable) fires when on any in-time
  unit of any of the five models the F1-optimal threshold puts fewer than
  one row in a hundred of the test cell above it, or none.
- **The branch kill** (the choice of protocol does not matter) fires when,
  for both foundation models against the GBM, on Gini and on |log O/E|
  alike, the in-time gap lies inside the out-of-time interval and the
  out-of-time gap lies inside the in-time fold spread.

    python scripts/record_run.py lc-2015h1e-protocols5-criteria -- \\
        python scripts/exp004_criteria.py experiments/<protocol table run> \\
            --pooling experiments/<out-of-time pooling> --out-dir experiments/<run>
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

IN_TIME = "in time, random fold"
OUT_OF_TIME = "out of time, vintage cohorts"
FIVE = ("scorecard", "gbm", "gbm-50k", "tabpfn", "tabicl")
AT_ONE = ("tabpfn@t1", "tabicl@t1")
FOUNDATION = ("tabpfn", "tabicl")
SEED = 20260905


def fold_of(unit: str) -> int:
    if not unit.startswith("fold "):
        raise SystemExit(f"an in-time unit named {unit!r}")
    return int(unit.split()[1])


def in_time_units(cells: pd.DataFrame, model: str, metric: str) -> pd.Series:
    """One model's in-time metric, indexed by (fold, context draw or -1)."""
    part = cells[(cells["protocol"] == IN_TIME) & (cells["model"] == model)]
    if part.empty:
        raise SystemExit(f"{model}: no in-time rows in the table")
    keys = [(fold_of(u), -1 if pd.isna(s) else int(s))
            for u, s in zip(part["unit"], part["context_seed"])]
    series = pd.Series(part[metric].to_numpy(dtype=float), index=pd.MultiIndex.from_tuples(
        keys, names=["fold", "draw"]))
    if series.index.duplicated().any():
        raise SystemExit(f"{model}: two in-time rows for one fold and draw")
    return series


def in_time_difference(cells: pd.DataFrame, a: str, b: str, metric: str) -> dict:
    """A − B per unit, as the docstring defines the unit, with its point and fold spread."""
    sa, sb = in_time_units(cells, a, metric), in_time_units(cells, b, metric)
    drawn_a = (sa.index.get_level_values("draw") >= 0).all()
    drawn_b = (sb.index.get_level_values("draw") >= 0).all()
    values = []
    for (fold, draw), va in sa.items():
        if drawn_a and drawn_b:
            if (fold, draw) not in sb.index:
                raise SystemExit(f"{b}: no fold {fold} draw {draw} to pair with {a}")
            values.append(va - sb[(fold, draw)])
        elif drawn_a:
            values.append(va - sb[(fold, -1)])
        elif drawn_b:
            values.extend(va - vb for (f, _), vb in sb.items() if f == fold)
        else:
            values.append(va - sb[(fold, -1)])
    values = np.array(values)
    return {"point": float(values.mean()), "lo": float(values.min()), "hi": float(values.max()),
            "units": int(values.size), "values": values.tolist()}


def out_of_time_difference(paired: pd.DataFrame, a: str, b: str, metric: str) -> dict:
    rows = paired[(paired["metric"] == metric) & (paired["is_difference"])
                  & (paired["cohorts"] == "all") & (paired["draw"].isna())
                  & (paired["seed"] == SEED)]
    sign = 1.0
    row = rows[rows["pair"] == f"{a} - {b}"]
    if row.empty:
        row, sign = rows[rows["pair"] == f"{b} - {a}"], -1.0
    if len(row) != 1:
        raise SystemExit(f"the pooling holds {len(row)} rows for {a} − {b} on {metric}")
    r = row.iloc[0]
    lo, hi = sorted((sign * float(r["ci_lo"]), sign * float(r["ci_hi"])))
    return {"point": sign * float(r["value"]), "lo": lo, "hi": hi,
            "starred": bool(r["excludes_zero"] in (True, "True"))}


def order(table: pd.DataFrame, protocol: str, metric: str, models) -> list[str]:
    sub = table[(table["protocol"] == protocol) & (table["model"].isin(models))]
    return list(sub.sort_values(f"{metric}_mean", kind="stable")["model"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("table", type=Path, help="a recorded run of protocol_table.py")
    parser.add_argument("--pooling", type=Path, required=True,
                        help="the build's recorded out-of-time pooling (paired.csv)")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    cells = pd.read_csv(args.table / "cells.csv")
    table = pd.read_csv(args.table / "table.csv")
    paired = pd.read_csv(args.pooling / "paired.csv")
    paired["is_difference"] = paired["is_difference"].astype(str) == "True"
    missing = set(FIVE) - set(cells["model"])
    if missing:
        raise SystemExit(f"the table holds no rows for {sorted(missing)}")

    pairs = {}
    for a, b in itertools.combinations(FIVE + AT_ONE, 2):
        if a in AT_ONE and b in AT_ONE:
            continue
        # Oriented as the pooling names them, the later model minus the earlier.
        a2, b2 = b, a
        oot = {m: out_of_time_difference(paired, a2, b2, m) for m in ("gini", "abs_log_oe")}
        pairs[f"{a2} - {b2}"] = {
            "a": a2, "b": b2,
            "gini": {"in_time": in_time_difference(cells, a2, b2, "gini"),
                     "out_of_time": oot["gini"]},
            "abs_log_oe": {"in_time": in_time_difference(cells, a2, b2, "abs_log_oe"),
                           "out_of_time": oot["abs_log_oe"]},
            "at_one": a2 in AT_ONE or b2 in AT_ONE,
        }

    # Criterion 1.
    starred = {k: v for k, v in pairs.items() if not v["at_one"] and v["gini"]["out_of_time"]["starred"]}
    c1_rows = []
    for name, v in starred.items():
        it, oot = v["gini"]["in_time"], v["gini"]["out_of_time"]
        same_sign = np.sign(it["point"]) == np.sign(oot["point"])
        outside = (it["lo"] > 0) if oot["point"] > 0 else (it["hi"] < 0)
        c1_rows.append({"pair": name, "out_of_time": oot["point"], "ci": [oot["lo"], oot["hi"]],
                        "in_time": it["point"], "fold_spread": [it["lo"], it["hi"]],
                        "same_sign": bool(same_sign), "spread_excludes_zero_that_side": bool(outside)})
    c1 = all(r["same_sign"] and r["spread_excludes_zero_that_side"] for r in c1_rows)

    # Criterion 2.
    orders = {p: {m: order(table, p, m, FIVE) for m in ("abs_log_oe", "brier", "log_loss")}
              for p in (IN_TIME, OUT_OF_TIME)}
    c2_rows = {p: {m: orders[p][m] == orders[p]["abs_log_oe"] for m in ("brier", "log_loss")}
               for p in orders}
    c2 = all(all(v.values()) for v in c2_rows.values())

    # Criterion 3.
    it_rows = cells[(cells["protocol"] == IN_TIME) & (cells["model"].isin(FIVE))]
    low = it_rows[it_rows["predicted_positive_share"] < 0.01]
    c3 = not low.empty
    shares = [float(it_rows["predicted_positive_share"].min()),
              float(it_rows["predicted_positive_share"].max())]

    # The branch kill.
    branch_rows = []
    for fm in FOUNDATION:
        key = f"{fm} - gbm"
        v = pairs[key]
        for metric in ("gini", "abs_log_oe"):
            it, oot = v[metric]["in_time"], v[metric]["out_of_time"]
            in_inside = oot["lo"] <= it["point"] <= oot["hi"]
            oot_inside = it["lo"] <= oot["point"] <= it["hi"]
            branch_rows.append({"pair": key, "metric": metric, "in_time": it["point"],
                                "fold_spread": [it["lo"], it["hi"]], "out_of_time": oot["point"],
                                "ci": [oot["lo"], oot["hi"]],
                                "in_time_inside_out_of_time_interval": bool(in_inside),
                                "out_of_time_inside_fold_spread": bool(oot_inside)})
    branch = all(r["in_time_inside_out_of_time_interval"] and r["out_of_time_inside_fold_spread"]
                 for r in branch_rows)

    result = {
        "table": args.table.as_posix(), "pooling": args.pooling.as_posix(),
        "criterion_1": {"fires": c1, "reading": "agreement" if c1 else "the ranking changes",
                        "starred_pairs": c1_rows},
        "criterion_2": {"fires": c2, "orders": orders, "agrees_with_abs_log_oe": c2_rows},
        "criterion_3": {"fires": c3, "predicted_positive_share_range": shares,
                        "units_under_one_percent": len(low)},
        "branch_kill": {"fires": branch, "rows": branch_rows},
        "pairs": {k: {m: {s: {kk: vv for kk, vv in d.items() if kk != "values"}
                          for s, d in v[m].items()} for m in ("gini", "abs_log_oe")}
                  for k, v in pairs.items()},
    }
    (args.out_dir / "criteria.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    rows = []
    for k, v in pairs.items():
        for m in ("gini", "abs_log_oe"):
            it, oot = v[m]["in_time"], v[m]["out_of_time"]
            rows.append({"pair": k, "metric": m, "at_one": v["at_one"],
                         "in_time": it["point"], "in_time_lo": it["lo"], "in_time_hi": it["hi"],
                         "units": it["units"], "out_of_time": oot["point"], "oot_lo": oot["lo"],
                         "oot_hi": oot["hi"], "oot_starred": oot["starred"]})
    pd.DataFrame(rows).to_csv(args.out_dir / "differences.csv", index=False)

    print(f"criterion 1 (ranking unchanged)   : {'fires' if c1 else 'does not fire'}")
    for r in c1_rows:
        print(f"  {r['pair']:<22} out {r['out_of_time']:+.4f} [{r['ci'][0]:+.4f}, {r['ci'][1]:+.4f}]"
              f"  in {r['in_time']:+.4f} [{r['fold_spread'][0]:+.4f}, {r['fold_spread'][1]:+.4f}]"
              f"  same sign {r['same_sign']}, spread clear {r['spread_excludes_zero_that_side']}")
    print(f"criterion 2 (scalar sees level)   : {'fires' if c2 else 'does not fire'}")
    for p in orders:
        for m in ("abs_log_oe", "brier", "log_loss"):
            print(f"  {p:<30} {m:<11} {' < '.join(orders[p][m])}")
    print(f"criterion 3 (threshold unreadable): {'fires' if c3 else 'does not fire'}; "
          f"predicted positive share {shares[0]:.4f} to {shares[1]:.4f}")
    print(f"branch kill (protocol irrelevant) : {'fires' if branch else 'does not fire'}")
    for r in branch_rows:
        print(f"  {r['pair']:<14} {r['metric']:<11} in {r['in_time']:+.4f} "
              f"[{r['fold_spread'][0]:+.4f}, {r['fold_spread'][1]:+.4f}]  out {r['out_of_time']:+.4f} "
              f"[{r['ci'][0]:+.4f}, {r['ci'][1]:+.4f}]  in-in-out {r['in_time_inside_out_of_time_interval']}"
              f"  out-in-in {r['out_of_time_inside_fold_spread']}")

    plot(pairs, args.out_dir / "differences.png")
    return 0


def plot(pairs: dict, out: Path) -> None:
    """Every pair's in-time units beside its out-of-time interval, per metric."""
    names = [k for k, v in pairs.items() if not v["at_one"]]
    fig, axes = plt.subplots(1, 2, figsize=(12, 0.45 * len(names) + 1.5), sharey=True)
    for ax, metric in zip(axes, ("gini", "abs_log_oe")):
        for i, name in enumerate(names):
            it, oot = pairs[name][metric]["in_time"], pairs[name][metric]["out_of_time"]
            ax.scatter(it["values"], np.full(len(it["values"]), i + 0.12), s=8, color="#4B3F8F",
                       alpha=0.6, label="in time, one fold and draw" if i == 0 else None)
            ax.errorbar(oot["point"], i - 0.12, xerr=[[oot["point"] - oot["lo"]],
                                                     [oot["hi"] - oot["point"]]],
                        fmt="o", color="#B23A48", markersize=4, capsize=2,
                        label="out of time, 95% interval" if i == 0 else None)
        ax.axvline(0, color="black", linewidth=0.8, linestyle=":")
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=8)
        ax.set_title(f"{metric}: A − B", fontsize=10)
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=7)
    fig.suptitle("each pair's difference in time, per fold and draw, beside its out-of-time "
                 "interval", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out, dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
