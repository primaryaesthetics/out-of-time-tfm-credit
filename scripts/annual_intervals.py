#!/usr/bin/env python3
"""The horizon check of EXP-005: H1 under the twelve-month label on annual cohorts.

The second book's trajectory is read on half-year cohorts under the
twenty-four-month label. The horizon check reads the same scores under the
twelve-month label, `outcome_horizon` in the score files, on annual cohorts,
and reads discrimination only: a twelve-month default is a twenty-four-month
default by construction, so a twenty-four-month probability ranks
twelve-month outcomes and does not price them. Nothing is refitted.

An annual cell is one build's scored rows of the two half-years of one
calendar year, taken together: one AUC on their union, and the bootstrap
resampling inside it, one index per year shared by every build that scores
it. A year a build does not score in both halves is no cell of that build.
The cell's age is the mean of its two halves' ages in quarters; every build
is dated at a year's end, so that mean moves every cell of a build by the
same amount and leaves the within-build slope as it is.

A year enters when its annual cohort holds at least 5,000 labelled loans
and 100 defaults under the twelve-month label on the book, both floors of
EXP-003 read on the check's own label, counted from the build run's
`cells.csv` and summed over the year's two halves; a half under either
count does not keep its year out. A year admitted whose scored rows fall
under either count stops the run rather than entering. The counts are
printed beside the rows.

What is read is H1 only: the slope of AUC on age with one intercept per
build and with one intercept per cohort, each model's and every paired
difference, at the arm pooling's poolings, each in annual cohorts: every
cell; the nearest cohorts, each build's three youngest annual cohorts
(`--nearest`) and then the floor; and every cell with the cohorts
resampled. Beside the arm's rows come the mean over builds with every build
weighted alike, each build on its own, the context draws held fixed one at
a time, and the check seeds. A build left with fewer than two annual cells
in a pooling has no slope of its own there: its row reads NaN and the build
is named as unreadable, and the mean over builds reads NaN with it rather
than being taken over the builds that remain. No build is dropped. None of
this is a criterion.

The figures draw every annual cell a build scores whole, one panel per
model: the cells pooled filled and joined, the years under the floor as
open markers outside the fit, and a line never joined across them.

The score directories and recorded poolings named are read as
`arm_intervals.py` reads them, and a directory whose scores do not carry
the twelve-month label takes it from the build's other directories.
`--resolution half` reads the arm's half-year cells with the build run's
floor verdicts instead, which reproduces the arm pooling's H1 rows; it is
the check of this script, not a reading of the book.

    python scripts/record_run.py fm-arm-e-intervals-horizon -- \\
        python scripts/annual_intervals.py \\
            experiments/2026-09-15-fm-2002h2e-intervals-grid \\
            ... \\
            experiments/2026-09-17-fm-2018h2e-control-refit \\
            --check-seeds 20260906,20260907 \\
            --cells experiments/2026-09-13-fm-vintage-builds2/cells.csv \\
            --out-dir experiments/<date>-fm-arm-e-intervals-horizon
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import arm_intervals as ai
import build_intervals as bi
import record_run as rr

from outoftime import metrics as mt

OUTCOME = "outcome_horizon"
H1_METRICS = ("auc_slope_build", "auc_slope_cohort")
# The slope that exists on one build: the cohort-intercept slope needs a
# cohort scored at more than one age, which one build never has.
BUILD_H1 = ("auc_slope_build",)
HALF_YEAR = re.compile(r"^(\d{4})H([12])$")
YEAR = re.compile(r"^\d{4}$")
LABEL_TEXT = {OUTCOME: "the twelve-month label"}


@dataclass
class Cells:
    """The cells a pooling reads: the builds, each cell's age in quarters keyed by
    (build, cohort), the cohorts with every build's scores on their rows, and each
    model's context seeds."""

    builds: list[str]
    ages: dict[tuple[str, str], float]
    cohorts: dict[str, mt.ScoredCohort]
    models: dict[str, list[int | None]]

    def cohorts_of(self, build: str) -> list[str]:
        return sorted(c for (b, c) in self.ages if b == build)


def year_of(cohort: str) -> tuple[str, int]:
    """The calendar year and the half of a half-year cohort `YYYYH1` or `YYYYH2`."""
    match = HALF_YEAR.match(cohort)
    if match is None:
        raise SystemExit(f"{cohort}: not a half-year cohort of the form YYYYH1 or YYYYH2")
    return match.group(1), int(match.group(2))


def half_year_cells(arm: ai.Arm, keep: set[str]) -> Cells:
    """The arm's own cells on the cohorts kept, as the arm pooling reads them."""
    return Cells(list(arm.builds),
                 {(b, c): float(a) for (b, c), a in arm.ages.items() if c in keep},
                 {c: v for c, v in arm.cohorts().items() if c in keep},
                 arm.models)


def annual_cells(arm: ai.Arm) -> tuple[Cells, dict[str, list[str]]]:
    """Every build's annual cells, and per year the builds that score one of its halves only.

    A year's rows are its first half's rows followed by its second's; every
    score vector is joined in the same order, per build and per context draw.
    A build enters a year only when it scores both halves.
    """
    halves: dict[str, dict[int, str]] = {}
    for cohort in arm.outcome:
        year, half = year_of(cohort)
        halves.setdefault(year, {})[half] = cohort
    cohorts: dict[str, mt.ScoredCohort] = {}
    ages: dict[tuple[str, str], float] = {}
    partial: dict[str, list[str]] = {}
    for year in sorted(halves):
        pair = halves[year]
        whole = [b for b in arm.builds
                 if all(h in pair and (b, pair[h]) in arm.ages for h in (1, 2))]
        one = [b for b in arm.builds
               if b not in whole and any((b, c) in arm.ages for c in pair.values())]
        if one:
            partial[year] = one
        if not whole:
            continue
        first, second = pair[1], pair[2]
        fixed: dict[tuple[str, str], np.ndarray] = {}
        seeded: dict[tuple[str, str], list[np.ndarray]] = {}
        for build in whole:
            for model, seeds in arm.models.items():
                key = (build, model)
                if seeds == [None]:
                    fixed[key] = np.concatenate([arm.fixed[first][key], arm.fixed[second][key]])
                else:
                    seeded[key] = [np.concatenate([a, b]) for a, b in
                                   zip(arm.seeded[first][key], arm.seeded[second][key], strict=True)]
            ages[(build, year)] = (arm.ages[(build, first)] + arm.ages[(build, second)]) / 2.0
        cohorts[year] = mt.ScoredCohort(
            np.concatenate([arm.outcome[first], arm.outcome[second]]), fixed, seeded)
    return Cells(list(arm.builds), ages, cohorts, arm.models), partial


def book_years(path: Path) -> pd.DataFrame:
    """Per calendar year, the twelve-month label's counts on the book and the primary floor.

    Read from the build run's cells.csv, where a cohort's counts are a
    property of the cohort and a cohort that carries two of them is refused.
    `halves` is how many of the year's half-years the file holds; `labelled`
    and `defaults` are summed over them; `halves_above_primary` counts the
    halves the primary label's floor admits.
    """
    table = pd.read_csv(path, usecols=["cohort", "labelled_horizon", "defaults_horizon", "floor"],
                        dtype={"cohort": str})
    table["floor"] = table["floor"].map({True: True, False: False, "True": True, "False": False})
    if table["floor"].isna().any():
        raise SystemExit(f"{path.as_posix()}: a floor verdict that is neither True nor False")
    per = table.drop_duplicates()
    if per["cohort"].duplicated().any():
        both = sorted(per.loc[per["cohort"].duplicated(), "cohort"].unique())
        raise SystemExit(f"{path.as_posix()}: {', '.join(both)} carries two twelve-month counts "
                         "or two floor verdicts")
    per = per.assign(year=[year_of(c)[0] for c in per["cohort"]])
    years = per.groupby("year").agg(
        halves=("cohort", "size"), labelled=("labelled_horizon", "sum"),
        defaults=("defaults_horizon", "sum"), halves_above_primary=("floor", "sum"))
    return years.astype(int)


def admitted(years: pd.DataFrame, rows: int | None = None, defaults: int | None = None) -> set[str]:
    """The years whose annual cohort, both halves on the book, clears both floors on the sum."""
    rows = bi.FLOOR_ROWS if rows is None else rows
    defaults = bi.FLOOR_DEFAULTS if defaults is None else defaults
    ok = (years["halves"] == 2) & (years["labelled"] >= rows) & (years["defaults"] >= defaults)
    return {str(y) for y in years.index[ok]}


def unreadable(cells: Cells, subset: set[tuple[str, str]] | None) -> list[str]:
    """The builds with fewer than two cells in the pooling: no slope of their own."""
    return [b for b in cells.builds
            if sum(1 for c in cells.cohorts_of(b)
                   if c in cells.cohorts and (subset is None or (b, c) in subset)) < 2]


def ordinal(cohort: str) -> int:
    """A cohort's place on the calendar in its own unit: years count in years, halves in halves."""
    if YEAR.match(cohort):
        return int(cohort)
    year, half = year_of(cohort)
    return 2 * int(year) + half - 1


def runs(cohorts: list[str], keep: set[str]) -> list[list[str]]:
    """The stretches of consecutive cohorts that enter, in calendar order.

    A cohort left out, or a gap on the calendar, ends a stretch, so that a
    line drawn through one stretch never joins cells across the hole.
    """
    out: list[list[str]] = []
    for cohort in sorted(cohorts, key=ordinal):
        if cohort not in keep:
            continue
        if out and ordinal(cohort) - ordinal(out[-1][-1]) == 1:
            out[-1].append(cohort)
        else:
            out.append([cohort])
    return out


def plot_auc_age(every: Cells, keep: set[str], paired: pd.DataFrame, out: Path, by: str,
                 outcome: str, resolution: str) -> dict:
    """AUC against age on every cell scored, one panel per model, one line per build or cohort.

    `every` holds every cell, `keep` the cohorts that enter the poolings. A
    cell that enters is a filled marker, and the line joins it to the next
    cohort along the line only when that cohort enters too: along a build,
    the calendar's next one; along a cohort, every build's cell of it. A
    cell of a cohort left out is an open marker on no line, and neither it
    nor its age enters the arm's fitted slope, which is laid through the
    grand mean of the cells that do. Drawn by build, the legend names every
    build; drawn by cohort, it names only the cohorts that enter. The first
    context draw is drawn for a seeded model.

    Returns what was drawn beyond the cells: per model the fitted line's two
    end points, and the legend's labels.
    """
    names = list(every.models)
    fig, axes = plt.subplots(1, len(names), figsize=(3.6 * len(names), 4.4), sharey=True)
    axes = np.atleast_1d(axes)
    cmap = plt.get_cmap("viridis")
    statistic = f"auc_slope_{by}"
    slopes = paired[(paired["metric"] == statistic) & ~paired["is_difference"]
                    & (paired["scope"] == ai.ARM) & (paired["cohorts"] == "all")
                    & paired["draw"].isna()].set_index("pair")
    lines = every.builds if by == "build" else sorted(every.cohorts, key=ordinal)
    colours = {line: cmap(i / max(1, len(lines) - 1)) for i, line in enumerate(lines)}
    left_out = False
    fits: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for ax, model in zip(axes, names):
        auc: dict[tuple[str, str], float] = {}
        for (build, cohort) in every.ages:
            c = every.cohorts[cohort]
            s = c.scores.get((build, model))
            if s is None:
                s = c.seeds[(build, model)][0]
            auc[(build, cohort)] = mt.auc(c.outcome, s)
        for line in lines:
            colour = colours[line]
            if by == "build":
                own = every.cohorts_of(line)
                joined = [[(line, c) for c in stretch] for stretch in runs(own, keep)]
                outside = [(line, c) for c in own if c not in keep]
            else:
                cells = sorted(((b, line) for b in every.builds if (b, line) in every.ages),
                               key=lambda k: every.ages[k])
                joined = [cells] if line in keep and cells else []
                outside = [] if line in keep else cells
            for stretch in joined:
                ax.plot([every.ages[k] for k in stretch], [auc[k] for k in stretch],
                        color=colour, marker="o", markersize=2.5, linewidth=1.0)
            if outside:
                left_out = True
                ax.plot([every.ages[k] for k in outside], [auc[k] for k in outside],
                        color=colour, marker="o", markersize=4.0, markerfacecolor="none",
                        markeredgewidth=0.9, linestyle="none")
        pooled = [k for k in every.ages if k[1] in keep]
        if model in slopes.index and pooled:
            row = slopes.loc[model]
            ages = np.array([every.ages[k] for k in pooled], dtype=float)
            gx = np.array([ages.min(), ages.max()])
            mean_auc = float(np.mean([auc[k] for k in pooled]))
            fits[model] = (gx, mean_auc + row.value * (gx - ages.mean()))
            ax.plot(*fits[model], color="black", linewidth=1.4, linestyle="--")
            ax.set_title(f"{bi.describe(model)}\nslope {row.value:+.5f} "
                         f"[{row.ci_lo:+.5f}, {row.ci_hi:+.5f}] per quarter", fontsize=9)
        else:
            ax.set_title(bi.describe(model), fontsize=9)
        ax.set_xlabel("model age, quarters")
        ax.grid(alpha=0.3)
    unit = "annual" if resolution == "year" else "half-year"
    label = LABEL_TEXT.get(outcome, f"the label in {outcome}")
    axes[0].set_ylabel(f"AUC on the {unit} cell, {label},\nfirst context draw")
    named = lines if by == "build" else [line for line in lines if line in keep]
    handles = [Line2D([], [], color=colours[line], marker="o", markersize=3, linewidth=1.0,
                      label=line) for line in named]
    handles.append(Line2D([], [], color="black", linewidth=1.4, linestyle="--",
                          label=f"arm slope, one intercept per {by}"))
    if left_out:
        handles.append(Line2D([], [], color="grey", marker="o", markerfacecolor="none",
                              linestyle="none", label="cohort under the floor, not pooled"))
    fig.legend(handles=handles, loc="lower center", ncol=min(len(handles), 10), frameon=False,
               fontsize=8)
    floor = (f"a year enters with {bi.FLOOR_ROWS:,} labelled loans and {bi.FLOOR_DEFAULTS} "
             "defaults on the book under this label" if resolution == "year"
             else "a half-year enters on the build run's floor verdict")
    fig.suptitle(f"AUC against model age under {label}, {unit} cohorts, one line per {by}\n"
                 f"{floor}; filled cells are pooled"
                 + ("; open ones are under the floor, outside the fit, and no line crosses them"
                    if left_out else ""), fontsize=10)
    fig.tight_layout(rect=(0, 0.1, 1, 0.92))
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return {"fits": fits, "legend": [h.get_label() for h in handles]}


def h1_statistics(cells: Cells, models: dict[str, list[int | None]],
                  subset: set[tuple[str, str]] | None, per_build: bool):
    """H1's two slopes and their paired differences, as `arm_intervals.arm_statistics` pools them.

    The cells are visited in the same order and the same least squares is
    fitted, so on the arm's cells every value is the arm pooling's.
    """
    names = [m for m in bi.MODEL_ORDER if m in models] + sorted(set(models) - set(bi.MODEL_ORDER))
    pairs = [(later, earlier) for earlier, later in itertools.combinations(names, 2)]
    builds = list(cells.builds)
    scopes = [ai.ARM, ai.BUILDS, *builds] if per_build else [ai.ARM]

    def compute(cohorts):
        age: dict[str, list[float]] = {m: [] for m in names}
        build_of: dict[str, list[str]] = {m: [] for m in names}
        cohort_of: dict[str, list] = {m: [] for m in names}
        auc: dict[str, list[float]] = {m: [] for m in names}
        for key, cohort in cohorts.items():
            name = ai.cohort_name(key)
            for build in builds:
                if (build, name) not in cells.ages:
                    continue
                if subset is not None and (build, name) not in subset:
                    continue
                for model in names:
                    age[model].append(cells.ages[(build, name)])
                    build_of[model].append(build)
                    cohort_of[model].append(key)
                    auc[model].append(mt.auc(cohort.outcome, cohort.scores[(build, model)]))
        per_scope: dict = {}
        for scope in [ai.ARM, *builds] if per_build else [ai.ARM]:
            value: dict[str, dict[str, float]] = {}
            for model in names:
                groups = np.asarray(build_of[model])
                pick = np.ones(groups.size, dtype=bool) if scope == ai.ARM else groups == scope
                ages = np.asarray(age[model], dtype=float)[pick]
                aucs = np.asarray(auc[model])[pick]
                labels = np.asarray([str(k) for k in cohort_of[model]])[pick]
                value[model] = {"auc_slope_build": ai.slope(ages, aucs, groups[pick]),
                                "auc_slope_cohort": ai.slope(ages, aucs, labels)}
            per_scope[scope] = value
        if per_build:
            per_scope[ai.BUILDS] = {
                model: {"auc_slope_build": float(np.mean(
                    [per_scope[b][model]["auc_slope_build"] for b in builds]))}
                for model in names}
        out: dict[str, float] = {}
        for scope in scopes:
            for stat in H1_METRICS if scope == ai.ARM else BUILD_H1:
                for model in names:
                    out[f"{stat}|slope|{scope}|{model}"] = per_scope[scope][model][stat]
                for later, earlier in pairs:
                    out[f"{stat}|diff|{scope}|{later}|{earlier}"] = (
                        per_scope[scope][later][stat] - per_scope[scope][earlier][stat])
        return out

    return compute


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dirs", type=Path, nargs="+",
                        help="score directories of the arm's builds, or recorded poolings whose "
                             "intervals.json names them")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--cells", type=Path, required=True,
                        help="the build run's cells.csv: the twelve-month counts on the book, "
                             "and the primary floor verdicts read with --resolution half")
    parser.add_argument("--drop", default="",
                        help="comma-separated model names to leave out of everything")
    parser.add_argument("--resamples", type=int, default=mt.RESAMPLES)
    parser.add_argument("--seed", type=int, default=bi.BOOTSTRAP_SEED)
    parser.add_argument("--check-seeds", default="",
                        help="comma-separated bootstrap seeds to repeat the poolings under")
    parser.add_argument("--nearest", type=int, default=bi.NEAREST,
                        help="how many of each build's youngest cohorts, taken before the floor, "
                             "form the second pooling")
    parser.add_argument("--no-per-draw", action="store_true",
                        help="skip the poolings with each context draw held fixed")
    parser.add_argument("--outcome", default=OUTCOME,
                        help="the score files' column read as the outcome")
    parser.add_argument("--resolution", choices=("year", "half"), default="year",
                        help="annual cells (the horizon check) or the arm's half-year cells")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    dropped_models = [m for m in args.drop.split(",") if m]

    sources = ai.expand_sources(args.dirs)
    by_build: dict[str, list[Path]] = {}
    derived: dict[str, list[dict]] = {}
    for path in sources:
        head = pd.read_parquet(path / "scores.parquet", columns=["build_id"])
        if head["build_id"].nunique() != 1:
            raise SystemExit(f"{path.as_posix()}: more than one build")
        by_build.setdefault(str(head["build_id"].iloc[0]), []).append(path)
        entry = bi.derivation_of(path)
        if entry is not None:
            derived.setdefault(entry["model"], []).append(
                {"build_id": str(head["build_id"].iloc[0]), **entry})

    arm = ai.Arm(outcome=args.outcome)
    stage = time.time()
    for build, dirs in sorted(by_build.items()):
        arm.add_build(dirs, dropped_models)
    print(f"arm                   : {arm.arm}")
    print(f"builds                : {len(arm.builds)}: " + ", ".join(
        f"{b} ({len(arm.cohorts_of(b))} half-years)" for b in arm.builds))
    print(f"scored rows           : {arm.scored_rows:,} on "
          f"{sum(v.size for v in arm.outcome.values()):,} distinct")
    print("models                : " + ", ".join(
        f"{m} ({len(s)} draw{'s' if len(s) > 1 else ''})" if s != [None] else m
        for m, s in arm.models.items()))
    print(f"outcome read          : {args.outcome}")
    print(f"resolution            : {args.resolution}")
    print(f"loaded in             : {time.time() - stage:.0f}s")

    year_rows: list[dict] = []
    if args.resolution == "half":
        keep, under = ai.floor_cohorts(arm, args.cells)
        every = half_year_cells(arm, set(arm.outcome))
        cells = half_year_cells(arm, keep)
        nearest = {(b, c) for b in arm.builds for c in arm.cohorts_of(b)[:args.nearest] if c in keep}
        for cohort, on in under.items():
            print(f"  {cohort} left out of the pooling: under the floors, on {', '.join(on)}")
    else:
        years = book_years(args.cells)
        every, partial = annual_cells(arm)
        scored = sorted(set(every.cohorts) | set(partial))
        missing = [y for y in scored if y not in years.index]
        if missing:
            raise SystemExit(f"{args.cells.as_posix()} holds no count for {', '.join(missing)}")
        above = admitted(years)
        keep = {y for y in every.cohorts if y in above}
        whole_on = {y: sorted(b for (b, c) in every.ages if c == y) for y in every.cohorts}
        bi.check_floors({f"{y} ({', '.join(whole_on[y])})": every.cohorts[y].outcome
                         for y in sorted(keep)}, args.cells)
        print(f"\nannual cohorts under {args.outcome}: a year enters with at least "
              f"{bi.FLOOR_ROWS:,} labelled loans and {bi.FLOOR_DEFAULTS} defaults on the book")
        print("  year  labelled  defaults  scored defaults  halves above the primary floor  "
              "builds scoring it whole")
        for year in scored:
            row = years.loc[year]
            cohort = every.cohorts.get(year)
            scored_defaults = None if cohort is None else int(cohort.outcome.sum())
            entry = {"year": year, "labelled_book": int(row["labelled"]),
                     "defaults_book": int(row["defaults"]),
                     "scored_rows": None if cohort is None else cohort.rows,
                     "defaults_scored": scored_defaults,
                     "halves_above_primary": int(row["halves_above_primary"]),
                     "admitted": year in keep,
                     "builds_whole": whole_on.get(year, []),
                     "builds_one_half": partial.get(year, [])}
            year_rows.append(entry)
            print(f"  {year}  {entry['labelled_book']:>8,}  {entry['defaults_book']:>8}  "
                  f"{'-' if scored_defaults is None else scored_defaults:>15}  "
                  f"{entry['halves_above_primary']:>30}  {len(entry['builds_whole'])}"
                  f"{'' if year in keep else '   left out'}")
        for year, on in partial.items():
            print(f"  {year} scored in one half only on {', '.join(on)}: no cell of those builds")
        kept_under_primary = [e["year"] for e in year_rows
                              if e["admitted"] and e["halves_above_primary"] < 2]
        if kept_under_primary:
            print("  admitted years holding a half under the primary floor: "
                  + ", ".join(kept_under_primary))
        cells = Cells(list(arm.builds), {k: a for k, a in every.ages.items() if k[1] in keep},
                      {y: c for y, c in every.cohorts.items() if y in keep}, arm.models)
        nearest = {(b, y) for b in arm.builds for y in every.cohorts_of(b)[:args.nearest]
                   if y in keep}
        # The annual cells hold every score the rest of main reads; the half-year arrays are freed.
        arm.fixed.clear()
        arm.seeded.clear()

    pooled_cells = sorted(cells.ages)
    print(f"\ncells                 : {len(pooled_cells)} over {len(cells.cohorts)} cohorts")
    for build in cells.builds:
        print(f"  {build}: {', '.join(cells.cohorts_of(build)) or 'none'}")
    poolings = [("all", None, False, True), ("nearest", nearest, False, True),
                ("all, cohorts resampled", None, True, False)]
    if not nearest:
        poolings = [p for p in poolings if p[0] != "nearest"]
        print(f"nearest {args.nearest} holds no cohort above the floors; that pooling is not read")
    elif len(nearest) == len(pooled_cells):
        poolings = [p for p in poolings if p[0] != "nearest"]
        print(f"nearest {args.nearest} is every cell; that pooling is not repeated")
    unread = {which: unreadable(cells, subset) for which, subset, _, per in poolings if per}
    for which, builds in unread.items():
        if builds:
            print(f"unreadable ({which}): {', '.join(builds)}, fewer than two cells; no slope of "
                  "their own, and the mean over builds reads NaN with them")

    paired_records: list[dict] = []

    def record(which: str, draw: int | None, result: dict[str, mt.Bootstrap]) -> None:
        for name, boot in result.items():
            metric, kind, scope, *parts = name.split("|")
            difference = kind == "diff"
            paired_records.append({
                "arm": arm.arm, "cohorts": which, "draw": draw, "scope": scope,
                "metric": metric, "pair": " - ".join(parts) if difference else parts[0],
                "is_difference": difference, **boot.as_dict(),
                "excludes_zero": boot.excludes_zero if difference else None,
                "reads_derived": bi.reads_derived(" - ".join(parts), derived),
            })

    for which, subset, clustered, per_build in poolings:
        stage = time.time()
        result = mt.cohort_blocked_bootstrap_many(
            cells.cohorts, h1_statistics(cells, cells.models, subset, per_build),
            resamples=args.resamples, seed=args.seed, resample_cohorts=clustered)
        record(which, None, result)
        print(f"bootstrap {which:<22}: {args.resamples} resamples in {time.time() - stage:.0f}s",
              flush=True)

    check_seeds = [int(s) for s in args.check_seeds.split(",") if s.strip()]
    if args.seed in check_seeds:
        raise SystemExit(f"--check-seeds repeats the primary seed {args.seed}")
    repeat_records: list[dict] = []
    for check_seed in check_seeds:
        stage = time.time()
        for which, subset, clustered, per_build in poolings:
            result = mt.cohort_blocked_bootstrap_many(
                cells.cohorts, h1_statistics(cells, cells.models, subset, per_build),
                resamples=args.resamples, seed=check_seed, resample_cohorts=clustered)
            for name, boot in result.items():
                metric, kind, scope, *parts = name.split("|")
                if kind != "diff":
                    continue
                repeat_records.append({
                    "arm": arm.arm, "bootstrap_seed": check_seed, "cohorts": which,
                    "scope": scope, "metric": metric, "pair": " - ".join(parts),
                    **boot.as_dict(), "excludes_zero": boot.excludes_zero})
        print(f"bootstrap seed {check_seed:<17}: every pooling again in "
              f"{time.time() - stage:.0f}s", flush=True)

    draw_count = next(iter(cells.cohorts.values())).draws
    common = sorted(set.intersection(*(set(s) for s in cells.models.values() if s != [None]))) \
        if draw_count > 1 and not args.no_per_draw else []
    for k, seed_value in enumerate(common):
        stage = time.time()
        fixed = {key: c.realise(k) for key, c in cells.cohorts.items()}
        models_k = {m: ([None] if s == [None] else [s[k]]) for m, s in cells.models.items()}
        result = mt.cohort_blocked_bootstrap_many(
            fixed, h1_statistics(cells, models_k, None, False),
            resamples=args.resamples, seed=args.seed)
        record("all", seed_value, result)
        print(f"draw {seed_value} held fixed   : {args.resamples} resamples in "
              f"{time.time() - stage:.0f}s", flush=True)

    paired = pd.DataFrame(paired_records)
    paired["draw"] = paired["draw"].astype("Int64")
    paired.to_csv(args.out_dir / "paired.csv", index=False)

    disagreeing: dict[str, list[dict]] = {}
    if common:
        per_draw = paired[paired["draw"].notna() & paired["is_difference"]]
        for (metric, pair), rows in per_draw.groupby(["metric", "pair"]):
            spans = list(zip(rows["draw"], rows["ci_lo"], rows["ci_hi"]))
            if any(a_hi < b_lo or b_hi < a_lo
                   for i, (_, a_lo, a_hi) in enumerate(spans) for (_, b_lo, b_hi) in spans[i + 1:]):
                disagreeing[f"{metric}|{pair}"] = [
                    {"draw": int(d), "ci_lo": float(lo), "ci_hi": float(hi)} for d, lo, hi in spans]

    checked: dict | None = None
    seed_sensitive: set[tuple[str, str, str, str]] = set()
    if repeat_records:
        repeats = pd.DataFrame(repeat_records)
        primary = paired[paired["draw"].isna() & paired["is_difference"]]
        checked = ai.seed_check(primary, repeats)
        seed_sensitive = {(c["cohorts"], c["scope"], c["metric"], c["pair"])
                          for c in checked["star_changed"]}
        pd.concat([primary.assign(bootstrap_seed=args.seed)[repeats.columns], repeats],
                  ignore_index=True).to_csv(args.out_dir / "paired-seeds.csv", index=False)

    print(f"\nH1 under {args.outcome}, {args.resolution} cells, paired differences at the arm "
          "(value [lo, hi], * excludes zero, ! draws disagree"
          + (", ? star changes with the bootstrap seed" if checked else "")
          + (", ~ reads derived rows" if derived else "") + "; none a criterion):")
    shown = paired[paired["is_difference"] & paired["draw"].isna()
                   & paired["scope"].isin([ai.ARM, ai.BUILDS])]
    for row in shown.itertuples():
        flag = "*" if row.excludes_zero else " "
        flag += "!" if f"{row.metric}|{row.pair}" in disagreeing else " "
        flag += "?" if (row.cohorts, row.scope, row.metric, row.pair) in seed_sensitive else " "
        flag += "~" if row.reads_derived else ""
        print(f"  {row.cohorts:<22} {row.scope:<6} {row.metric:<16} {row.pair:<24} "
              f"{row.value:+.5f} [{row.ci_lo:+.5f}, {row.ci_hi:+.5f}] {flag}")
    slopes = paired[~paired["is_difference"] & paired["draw"].isna() & (paired["cohorts"] == "all")]
    print("\nAUC slope on age per quarter, one intercept per build: the arm, the mean over "
          "builds, and each build:")
    for model in cells.models:
        sub = slopes[(slopes["pair"] == model)
                     & (slopes["metric"] == "auc_slope_build")].set_index("scope")
        print(f"  {model:<11} arm {sub.loc[ai.ARM].value:+.5f} [{sub.loc[ai.ARM].ci_lo:+.5f}, "
              f"{sub.loc[ai.ARM].ci_hi:+.5f}]  builds alike {sub.loc[ai.BUILDS].value:+.5f}  each "
              + " ".join(f"{sub.loc[b].value:+.5f}" for b in cells.builds))
    print("AUC slope on age per quarter, one intercept per cohort, the arm:")
    for model in cells.models:
        row = slopes[(slopes["pair"] == model) & (slopes["metric"] == "auc_slope_cohort")
                     & (slopes["scope"] == ai.ARM)].iloc[0]
        print(f"  {model:<11} arm {row.value:+.5f} [{row.ci_lo:+.5f}, {row.ci_hi:+.5f}]")
    if checked:
        print(f"\nbootstrap seed check over seeds {', '.join(map(str, checked['seeds']))}: "
              f"{checked['arm_starred']} of {checked['arm_differences']} arm differences starred "
              f"under seed {args.seed}, {checked['arm_star_changed']} change their star; "
              f"{checked['starred']} of {checked['differences']} at every scope, "
              f"{len(checked['star_changed'])} change")
    for model, entries in derived.items():
        for entry in entries:
            print(f"  ~ {bi.derivation_text(entry, f'{model} on ' + entry['build_id'])}")

    for by, name in (("build", "auc-age.png"), ("cohort", "auc-age-cohort.png")):
        plot_auc_age(every, set(cells.cohorts), paired, args.out_dir / name, by, args.outcome,
                     args.resolution)

    summary = {
        "arm": arm.arm,
        "outcome": args.outcome,
        "resolution": args.resolution,
        "builds": {b: cells.cohorts_of(b) for b in cells.builds},
        "cells": len(pooled_cells),
        "unreadable": unread,
        "years": year_rows,
        "floors": {
            "record": args.cells.as_posix(), "rows": bi.FLOOR_ROWS,
            "defaults": bi.FLOOR_DEFAULTS,
            "rule": ("a year enters when its annual cohort, both halves on the book, holds both "
                     "floors under the twelve-month label, counted from the record and summed "
                     "over the two halves; an admitted year whose scored rows fall under either "
                     "floor stops the run"
                     if args.resolution == "year" else
                     "the arm pooling's: the record's floor verdict per half-year cohort")},
        "models": {m: ([] if s == [None] else s) for m, s in cells.models.items()},
        "models_dropped": dropped_models,
        "sources": [d.as_posix() for d in sources],
        "derived_rows": derived,
        "nearest": args.nearest,
        "nearest_cells": {b: sorted(c for (x, c) in nearest if x == b) for b in cells.builds},
        "bootstrap": {
            "resamples": args.resamples, "seed": args.seed, "alpha": mt.ALPHA,
            "blocking": ("the annual cohort, one index over the union of its two half-years "
                         "shared by every build that scores it" if args.resolution == "year"
                         else "cohort, one index per cohort shared by every build that scores it"),
            "context_draw": ("drawn with the resample, jointly across models and builds"
                             if draw_count > 1 else "one draw; every interval is conditional on it"),
            "poolings": [p[0] for p in poolings],
            "per_draw": ("the 'all' pooling repeated with each context draw held fixed, in the "
                         "rows whose draw is set" if common else None),
            "draws_disagree": disagreeing if common else None,
            "seed_check": checked,
            "multiplicity": "none: every interval is reported at alpha on its own"},
        "statistics": {
            "auc_slope_build": "least-squares slope of the cell's AUC on its age in quarters "
                               "with one intercept per build, as arm_intervals.py fits it; an "
                               "annual cell's age is the mean of its halves' ages",
            "auc_slope_cohort": "the same least squares with one intercept per cohort; at the "
                                "arm's scope only",
            "unreadable": "a build with fewer than two cells in a pooling has no slope of its "
                          "own; its rows and the mean over builds read NaN",
            "difference": "later model minus earlier in the order scorecard, gbm, gbm-50k, "
                          "tabpfn, tabicl, then the tagged settings",
            "standing": "the horizon check of EXP-005: reported beside H1, no criterion"},
        "wall_seconds": round(time.time() - started, 1),
    }
    inputs = [*sources, *(d / "intervals.json" for d in args.dirs
                          if not (d / "scores.parquet").exists()), args.cells]
    hashed = {}
    for path in inputs:
        for item in sorted(path.rglob("*") if path.is_dir() else [path]):
            if item.is_file():
                hashed[item.as_posix()] = rr.file_hash(item)
    (args.out_dir / "inputs.json").write_text(json.dumps(hashed, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "intervals.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nwall                  : {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
