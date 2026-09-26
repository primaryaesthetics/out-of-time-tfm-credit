#!/usr/bin/env python3
"""Turns a measured device speed into the Freddie Mac grid, by a rule fixed before the speed.

EXP-005 sizes the foundation-model side of its grid from a one-hour timing
probe on the rented device, and it fixes the rule that does so before the
probe has run: otherwise the grid would be chosen after its cost was seen, and
the choice of what to score would be one more thing tuned on the result. This
file is that rule, executable, with the row counts and the thresholds as
EXP-005 states them.

A speed is seconds per scored row, context set-up included, for each model:
`s_I` for TabICL, `s_P` for TabPFN. Given directly, or read from the node
records of the probe, where it is every cell's seconds over every cell's rows
for that model, reference cells included, whatever temperature a pass ran at:

    python scripts/fm_grid_budget.py --s-tabicl 0.0021 --s-tabpfn 0.0048
    python scripts/fm_grid_budget.py --probe out/*-scored-*

The walls, with the 25% margin:

    W_full    = 1.25 x R_E x (3 s_I + 6 s_P)    TabPFN at both temperatures
    W_derived = 1.25 x R_E x (3 s_I + 3 s_P)    TabPFN at 1.0 derived from 0.9
    W_R       = 1.25 x R_R x (3 s_I + 3 s_P)    the rolling arm, 1.0 derived

and the rule: both TabPFN temperatures on the expanding arm if W_full is at
most 30 hours; else the derivation if W_derived is; else the derivation
anyway, over as many hours as it takes, because no seed, row, build or cohort
is cut to fit a budget. The rolling arm's foundation-model cells run on the
device if the chosen expanding wall plus W_R is at most 45 hours; otherwise
the rolling arm is classical and H4 is not tested on this book.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Rows per pass — one model, one context seed, one temperature — as EXP-005
# counts them: every scored row of the arm plus one 50,000-row context per build.
ROWS_EXPANDING = 5_754_654 + 9 * 50_000
ROWS_ROLLING = 4_726_804 + 8 * 50_000
SEEDS = 3
MARGIN = 1.25
FULL_LIMIT_HOURS = 30.0
ROLLING_LIMIT_HOURS = 45.0


def walls(s_tabicl: float, s_tabpfn: float) -> dict[str, float]:
    """Projected hours of the three configurations the rule chooses between."""
    if s_tabicl <= 0 or s_tabpfn <= 0:
        raise ValueError("a speed is a positive number of seconds per row")
    hours = 3600.0
    return {
        "full": MARGIN * ROWS_EXPANDING * (SEEDS * s_tabicl + 2 * SEEDS * s_tabpfn) / hours,
        "derived": MARGIN * ROWS_EXPANDING * (SEEDS * s_tabicl + SEEDS * s_tabpfn) / hours,
        "rolling": MARGIN * ROWS_ROLLING * (SEEDS * s_tabicl + SEEDS * s_tabpfn) / hours,
    }


def decide(s_tabicl: float, s_tabpfn: float) -> dict:
    """The grid EXP-005's rule selects for these two speeds."""
    w = walls(s_tabicl, s_tabpfn)
    if w["full"] <= FULL_LIMIT_HOURS:
        rule, tabpfn_t1, expanding = 1, "scored", w["full"]
    elif w["derived"] <= FULL_LIMIT_HOURS:
        rule, tabpfn_t1, expanding = 2, "derived", w["derived"]
    else:
        rule, tabpfn_t1, expanding = 3, "derived", w["derived"]
    rolling = expanding + w["rolling"] <= ROLLING_LIMIT_HOURS
    return {
        "speeds": {"tabicl": s_tabicl, "tabpfn": s_tabpfn},
        "walls_hours": {k: round(v, 2) for k, v in w.items()},
        "rule": rule,
        "tabpfn_at_1": tabpfn_t1,
        "rolling_arm_on_device": rolling,
        "device_hours": round(expanding + (w["rolling"] if rolling else 0.0), 2),
        "h4_tested": rolling,
    }


def base_model(name: str) -> str:
    return name.split("@", 1)[0]


def probe_speeds(directories: list[Path]) -> dict[str, float]:
    """Seconds per row for each model, over every cell of every node record given."""
    seconds: dict[str, float] = {}
    rows: dict[str, int] = {}
    for directory in directories:
        node = json.loads((directory / "node.json").read_text(encoding="utf-8"))
        for cell in node["cells"]:
            model = base_model(cell["model"])
            seconds[model] = seconds.get(model, 0.0) + float(cell["seconds"])
            rows[model] = rows.get(model, 0) + int(cell["rows"])
    return {model: seconds[model] / rows[model] for model in seconds}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--s-tabicl", type=float, default=None,
                        help="TabICL seconds per scored row, context set-up included")
    parser.add_argument("--s-tabpfn", type=float, default=None,
                        help="TabPFN seconds per scored row, context set-up included")
    parser.add_argument("--probe", type=Path, nargs="*", default=[],
                        help="scored directories of the probe, each holding a node.json")
    parser.add_argument("--json", action="store_true", help="print the decision as JSON")
    args = parser.parse_args(argv)

    measured = probe_speeds(args.probe) if args.probe else {}
    s_tabicl = args.s_tabicl if args.s_tabicl is not None else measured.get("tabicl")
    s_tabpfn = args.s_tabpfn if args.s_tabpfn is not None else measured.get("tabpfn")
    if s_tabicl is None or s_tabpfn is None:
        raise SystemExit("both speeds are needed: --s-tabicl and --s-tabpfn, or --probe "
                         "directories that hold cells of both models")
    decision = decide(s_tabicl, s_tabpfn)
    if args.json:
        print(json.dumps(decision, indent=2))
        return 0
    w = decision["walls_hours"]
    print(f"speeds       : tabicl {s_tabicl:.3e} s/row, tabpfn {s_tabpfn:.3e} s/row")
    print(f"walls        : full {w['full']:.1f} h, derived {w['derived']:.1f} h, "
          f"rolling {w['rolling']:.1f} h (margin {MARGIN})")
    print(f"rule         : {decision['rule']} - TabPFN at 1.0 {decision['tabpfn_at_1']}")
    print(f"rolling arm  : {'on the device' if decision['rolling_arm_on_device'] else 'classical only; H4 not tested'}")
    print(f"device hours : {decision['device_hours']:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
