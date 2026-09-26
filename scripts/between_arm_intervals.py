#!/usr/bin/env python3
"""Reads what the rolling training window does to calibration drift, against the expanding one.

The context-policy hypothesis (H4 of EXP-002 and EXP-005) is written on the
Cox slope: the rolling arm reduces calibration drift for the foundation
models by more than it does for GBM-50k, and it is killed if the difference
in mean absolute Cox-slope deviation between arms is no larger for a
foundation model than for GBM-50k, inside the interval. For a foundation
model the training window and the context sample are one knob, so the arm
decides what the context is a sample of; GBM-50k reads the same draws.

The statistic, per model m, on the cells the two arms share:

    mean_m(arm)  = the mean over the cells of |Cox slope - 1|, one arm's scores
    reduction_m  = mean_m(E) - mean_m(R)
    h4_m         = reduction_m - reduction_GBM-50k

A positive reduction says the rolling arm's scores drift less from a Cox
slope of one than the expanding arm's on the same cohorts; a positive h4
says it does so for the model by more than for the control. A cell is a
(build date, cohort) pair: the two arms' builds at one as-of date score the
same cohorts, whole cohorts on Freddie Mac and one fixed sample per quarter
on Lending Club, so a cohort's rows are one set of loans on every build of
either arm. The Cox slope is invariant to a shift of every score on the
logit, so a model whose rolling-arm level differs from its expanding-arm
level by a constant, as a context at a different default rate can make it,
moves no row of this statistic; a stretch or compression of its scale does.

The interval is the cohort-blocked bootstrap of the metrics module, shared
across both arms: each resample draws one row index per cohort and applies
it to every build of either arm that scores the cohort and to every model,
and one context draw is chosen per resample for every build of both arms at
once, so draw k of a model on the rolling arm is read beside draw k on the
expanding arm. The point estimate averages over the draws. A cell on which
some model's Cox fit did not finish, on either arm, leaves the pairing for
every model on both arms, in the point estimate and in every resample, so
that the two arms and the models stay on identical cells; the count left out
is printed beside the statistic.

The criterion reads the mean over every shared cell (scope ``arm``), with the
cohorts held fixed. Reported beside it and entering no criterion: the mean
over build dates with every date weighted alike (``builds``), each build date
on its own, the same pooling with the cohorts resampled, each context draw
held fixed, and every model's row at 1.0 (``tabpfn@t1``, ``tabicl@t1``),
which is on the table and reads no verdict. Given the build run's
``cells.csv`` (``--cells``), a cell enters only if its cohort clears the
floors, and the pre-flag and flagged cells are pooled as two scopes of their
own, whose signs kill criterion 4 of EXP-005 compares. The floors are the
per-build script's, 5,000 labelled loans and 100 defaults under the primary
label (EXP-005, Floors), and the scored rows are held against them: without
`--cells` a pairing whose scored rows fall under the floors on any shared
cohort is refused and reads no verdict; with it, a cohort the file admits
whose scored rows fall under them is refused.

A model at softmax temperature 1.0 that some build of either arm does not
hold, as when its derivation is refused on a rolling build, leaves the
pairing: its H4 rows are not computed, and it is named on stdout and in
the summary. Any other model missing on a build refuses the pairing.

An arm-contrast record named with `--contrast` has to describe the grid read:
where its share of the expanding pool held by the rolling window and the
share the score runs' build.json give differ by more than half a point on
any build date, it is refused.

A verdict per foundation model at its library settings: the kill fires
unless the interval of h4 lies above zero under the primary bootstrap seed
and every check seed. A star a check seed loses is reported as holding zero
at the margin, and the kill fires, whichever side of zero the interval
lies. Where the pre-flag and flagged scopes read the row with different
signs, kill criterion 4 of EXP-005 makes the verdict undetermined on the
book, with the arm row's own reading kept beside it; the pre-flag row minus
the flagged row on the same resample is reported beside it and enters no
criterion. `--check-seeds` repeats every pooling under each seed named. No
multiplicity correction is applied.

Outputs: ``paired.csv``, every pooled statistic with its interval;
``paired-seeds.csv`` under `--check-seeds`; ``cells.csv``, every cell's
|Cox slope - 1| per model, arm and draw; ``summary.json``; ``arm-cells.png``,
each cell's deviation on one arm against the other; ``build-rows.png``, the
per-date rows beside the pooled one; ``inputs.json``, the sha256 of every file
in the directories read and of the cells and contrast records; and the table
on stdout.

    python scripts/record_run.py lc-between-arm-intervals -- \\
        python scripts/between_arm_intervals.py \\
            --expanding experiments/2026-09-11-lc-2013h1e-intervals-grid ... \\
            --rolling experiments/2026-09-12-lc-2013h1r-scores ... \\
            --contrast experiments/2026-09-04-lc-arm-contrast-rolling4/arm-contrast.json \\
            --check-seeds 20260906,20260907 \\
            --out-dir experiments/<date>-lc-between-arm-intervals
"""

from __future__ import annotations

import argparse
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ablation_intervals as ab
import arm_intervals as ai
import build_intervals as bi
import record_run as rr

from outoftime import metrics as mt

EXPANDING, ROLLING = "E", "R"
ARMS = (EXPANDING, ROLLING)
ARM_NAME = {EXPANDING: "expanding", ROLLING: "rolling"}
CONTROL = "gbm-50k"
# The models the criterion reads, at their library settings.
CRITERION_MODELS = ("tabpfn", "tabicl")
METRIC = "cox_slope_deviation"
# Every shared cell in the pooling, and every build date weighted alike.
POOLED = ai.ARM
BUILDS = ai.BUILDS
# The label regimes pooled as scopes of their own when the build run's cells are given.
REGIME_SCOPES = ("pre-flag", "flagged")
# H4 on the pre-flag scope minus H4 on the flagged scope, on the same resample: read beside
# kill criterion 4's comparison of signs (EXP-005, note of 2026-09-17), entering no criterion.
SCOPE_DIFFERENCE = "scope_difference"
SCOPE_CONTRAST = "pre-flag - flagged"
UNDETERMINED = ("undetermined on this book (kill criterion 4): the pre-flag and flagged scopes "
                "disagree in sign")
# The floors of EXP-005's Floors paragraph are build_intervals.FLOOR_ROWS and
# FLOOR_DEFAULTS, one pair for every pooling script; a cohort's scored rows
# are held against them through build_intervals.check_floors.
# How far, as a share, an arm-contrast record's share of the expanding pool
# may sit from the one the score runs' build.json give: half a point.
SHARE_TOLERANCE = 0.005
HOLDS = "holds"


def build_date(build_id: str, arm: str) -> str:
    """The as-of half-year a build id names: 2015H1-R is 2015H1 on the rolling arm."""
    date, sep, suffix = build_id.rpartition("-")
    if not sep or suffix != arm:
        raise SystemExit(f"{build_id} is not a build of arm {arm}")
    return date


def at_temperature_one(model: str) -> bool:
    """Whether a model's tags set the softmax temperature to 1.0: tabpfn@t1, tabicl@t1+bal."""
    _, _, tags = model.partition("@")
    return any(t.startswith("t") and t[1:].replace(".", "", 1).isdigit() and float(t[1:]) == 1.0
               for t in tags.split("+") if t)


def models_held(dirs: list[Path]) -> set[str]:
    return set().union(*(set(pd.read_parquet(d / "scores.parquet", columns=["model"])["model"])
                         for d in dirs))


def group_sources(paths: list[Path], arm: str) -> dict[str, list[Path]]:
    """Score directories by build, refused where a directory holds another arm's build."""
    flag = "--expanding" if arm == EXPANDING else "--rolling"
    by_build: dict[str, list[Path]] = {}
    for path in ai.expand_sources(paths):
        head = pd.read_parquet(path / "scores.parquet", columns=["build_id", "arm"])
        if head["build_id"].nunique() != 1:
            raise SystemExit(f"{path.as_posix()}: more than one build")
        build = str(head["build_id"].iloc[0])
        held = sorted(set(head["arm"].astype(str)))
        if held != [arm]:
            raise SystemExit(f"{path.as_posix()}: {build} is on arm {', '.join(held)}, named "
                             f"under {flag}")
        build_date(build, arm)
        by_build.setdefault(build, []).append(path)
    return by_build


def matrix_check(sources: dict[str, list[Path]]) -> dict:
    """Refuses unless every directory of either arm that records its matrix records the same one.

    A classical score run and a foundation-model run record their columns in
    different files, so each kind is compared with its own kind; the
    ablation a classical run declares is compared across both arms.
    """
    seen: dict[str, tuple[list[str], str]] = {}
    declared: dict[str | None, str] = {}
    for dirs in sources.values():
        for path in dirs:
            record = ab.matrix_of(path)
            if record["features"] is None:
                continue
            kind = record["record"].rsplit(" ", 1)[-1]
            if kind in seen and seen[kind][0] != record["features"]:
                raise SystemExit(f"{path.as_posix()} was scored on other columns than "
                                 f"{seen[kind][1]}; both arms have to be read on one matrix")
            seen.setdefault(kind, (record["features"], path.as_posix()))
            if record["declares"]:
                declared.setdefault(record["declared"], path.as_posix())
    if len(declared) > 1:
        raise SystemExit("the score runs declare different ablations: " + "; ".join(
            f"{name or 'none'} ({where})" for name, where in declared.items()))
    return {"features": {kind: cols for kind, (cols, _) in seen.items()},
            "ablation": next(iter(declared), None)}


def read_cells(path: Path, builds: dict[tuple[str, str], str], cells: list[tuple[str, str]],
               outcomes: dict[str, np.ndarray]) -> tuple[dict[str, bool], dict[str, str]]:
    """The floor verdict and label regime of every shared cell's cohort, from the build run.

    Both are properties of the cohort; a cohort read differently on two
    rows of the file is refused, and so is a cell the file does not hold.
    A cohort the file admits whose scored rows, `outcomes`, fall under the
    floors is refused; the other direction is not checked, since a sampled
    book scores fewer rows than its cohorts hold.
    """
    table = pd.read_csv(path, usecols=["build_id", "cohort", "floor", "regime"])
    table["cohort"] = table["cohort"].astype(str)
    index = table.set_index(["build_id", "cohort"]).sort_index()
    floor: dict[str, bool] = {}
    regime: dict[str, str] = {}
    for date, cohort in cells:
        for arm in ARMS:
            key = (builds[(arm, date)], cohort)
            if key not in index.index:
                raise SystemExit(f"{path.as_posix()} holds no row for {key[0]} {cohort}")
            row = index.loc[key]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            got = (bool(row["floor"]), str(row["regime"]))
            if cohort in floor and (floor[cohort], regime[cohort]) != got:
                raise SystemExit(f"{path.as_posix()}: {cohort} carries two floor or regime verdicts")
            floor[cohort], regime[cohort] = got
    bi.check_floors({c: outcomes[c] for c in sorted(floor) if floor[c]}, path)
    return floor, regime


class Pairing:
    """The two arms loaded, aligned on the cells they share.

    `arms` holds one `arm_intervals.Arm` per arm, restricted to the build
    dates the rolling arm has; `builds` maps (arm, date) to the build id;
    `cells` is every shared (date, cohort); `criterion` the cells a
    criterion reads; `regime` the label regime of a cohort where known.
    """

    def __init__(self, expanding: ai.Arm, rolling: ai.Arm, dates: list[str],
                 builds: dict[tuple[str, str], str]) -> None:
        self.arms = {EXPANDING: expanding, ROLLING: rolling}
        self.dates = dates
        self.builds = builds
        if expanding.models != rolling.models:
            raise SystemExit(f"the arms carry different models or seeds: {expanding.models} "
                             f"against {rolling.models}")
        self.models = expanding.models
        cells: list[tuple[str, str]] = []
        for date in dates:
            e, r = builds[(EXPANDING, date)], builds[(ROLLING, date)]
            ce, cr = expanding.cohorts_of(e), rolling.cohorts_of(r)
            if ce != cr:
                raise SystemExit(f"{e} and {r} score different cohorts: "
                                 f"{sorted(set(ce) ^ set(cr))}")
            for cohort in ce:
                if expanding.ages[(e, cohort)] != rolling.ages[(r, cohort)]:
                    raise SystemExit(f"{cohort} is at age {expanding.ages[(e, cohort)]} on {e} "
                                     f"and {rolling.ages[(r, cohort)]} on {r}")
                cells.append((date, cohort))
        for cohort in sorted({c for _, c in cells}):
            if not np.array_equal(expanding.rows[cohort], rolling.rows[cohort]):
                raise SystemExit(f"{cohort}: the arms score different rows")
            if not np.array_equal(expanding.outcome[cohort], rolling.outcome[cohort]):
                raise SystemExit(f"{cohort}: the arms carry different outcomes")
        self.cells = cells
        self.criterion = set(cells)
        self.regime: dict[str, str] = {}
        self.floor: dict[str, bool] = {}

    def cohorts(self) -> dict[str, mt.ScoredCohort]:
        """Every shared cohort with both arms' cells in one record, keyed (build id, model)."""
        e, r = self.arms[EXPANDING], self.arms[ROLLING]
        return {cohort: mt.ScoredCohort(e.outcome[cohort], {**e.fixed[cohort], **r.fixed[cohort]},
                                        {**e.seeded[cohort], **r.seeded[cohort]})
                for cohort in sorted({c for _, c in self.cells})}

    def age(self, date: str, cohort: str) -> int:
        return self.arms[EXPANDING].ages[(self.builds[(EXPANDING, date)], cohort)]


def model_names(models) -> list[str]:
    return [m for m in bi.MODEL_ORDER if m in models] + sorted(set(models) - set(bi.MODEL_ORDER))


def between_arm_statistics(pairing: Pairing, models: dict[str, list[int | None]], control: str,
                           per_build: bool):
    """Per model and arm the pooled |Cox slope - 1|, the reduction E - R, and its gap to the control's.

    Returns a callable of the cohorts with the context draw chosen, as
    `metrics.cohort_blocked_bootstrap_many` expects. Each cell's deviation
    is computed once per model and arm; the scopes are assembled from them.
    A cell pairs over both arms: where any model's fit did not finish on
    either arm, the cell leaves every model's mean on both.
    """
    names = model_names(models)
    dates = list(pairing.dates)
    regimes = [s for s in REGIME_SCOPES if any(pairing.regime.get(c) == s
                                               for _, c in pairing.criterion)]

    def compute(cohorts):
        date_of: list[str] = []
        regime_of: list[str | None] = []
        values = {(m, a): [] for m in names for a in ARMS}
        for key, cohort in cohorts.items():
            name = ai.cohort_name(key)
            for date in dates:
                if (date, name) not in pairing.criterion:
                    continue
                date_of.append(date)
                regime_of.append(pairing.regime.get(name))
                for arm in ARMS:
                    build = pairing.builds[(arm, date)]
                    for model in names:
                        values[(model, arm)].append(
                            bi.cox_slope_deviation(cohort.outcome, cohort.scores[(build, model)]))
        matrix = {k: np.asarray(v, dtype=float) for k, v in values.items()}
        keep = np.isfinite(np.vstack(list(matrix.values()))).all(axis=0)
        date_of_a = np.asarray(date_of)
        regime_of_a = np.asarray(regime_of, dtype=object)
        picks = {POOLED: np.ones(keep.size, dtype=bool)}
        if per_build:
            picks.update({date: date_of_a == date for date in dates})
            picks.update({scope: regime_of_a == scope for scope in regimes})
        means: dict[str, dict[tuple[str, str], float]] = {}
        for scope, pick in picks.items():
            means[scope] = {k: bi.paired_mean(v[pick], keep[pick]) for k, v in matrix.items()}
        out: dict[str, float] = {}
        if per_build:
            # A date none of whose cells is estimable reads NaN for every model and
            # arm alike, and leaves the mean over dates.
            estimable_date = np.array([keep[date_of_a == d].any() for d in dates])
            means[BUILDS] = {k: bi.paired_mean([means[d][k] for d in dates], estimable_date)
                             for k in matrix}
        for scope, value in means.items():
            reduction = {m: value[(m, EXPANDING)] - value[(m, ROLLING)] for m in names}
            for model in names:
                for arm in ARMS:
                    out[f"{METRIC}|mean|{scope}|{model}|{arm}"] = value[(model, arm)]
                out[f"{METRIC}|reduction|{scope}|{model}"] = reduction[model]
            for model in names:
                if model != control:
                    out[f"{METRIC}|h4|{scope}|{model}"] = reduction[model] - reduction[control]
        if per_build and len(regimes) == 2:
            # Whether the two label regimes disagree beyond the interval, on the same resample.
            for model in names:
                if model != control:
                    out[f"{METRIC}|{SCOPE_DIFFERENCE}|{SCOPE_CONTRAST}|{model}"] = (
                        out[f"{METRIC}|h4|{REGIME_SCOPES[0]}|{model}"]
                        - out[f"{METRIC}|h4|{REGIME_SCOPES[1]}|{model}"])
        for scope, pick in picks.items():
            out[f"{bi.LEFT_OUT}|{METRIC}|{scope}"] = float((~keep[pick]).sum())
        if per_build:
            out[f"{bi.LEFT_OUT}|{METRIC}|{BUILDS}"] = float((~estimable_date).sum())
        return out

    return compute


def pair_label(kind: str, model: str, arm: str | None, control: str) -> str:
    if kind == "mean":
        return f"{model} on {arm}"
    if kind == "reduction":
        return f"{model}: E - R"
    if kind == SCOPE_DIFFERENCE:
        return f"{model} - {control}: E - R, {SCOPE_CONTRAST}"
    return f"{model} - {control}: E - R"


def records_of(result: dict[str, mt.Bootstrap], control: str,
               derived_arms: set[tuple[str, str]], **extra) -> list[dict]:
    """The rows of one pooling; a row reads derived rows where a (model, arm) it reads is derived.

    A mean reads its own arm, a reduction both arms, and h4 both arms of the
    model and of the control.
    """
    out = []
    for name, boot in result.items():
        metric, kind, scope, model, *rest = name.split("|")
        arm = rest[0] if rest else None
        difference = kind != "mean"
        involved = {model, control} if kind in ("h4", SCOPE_DIFFERENCE) else {model}
        arms = ARMS if arm is None else (arm,)
        out.append({**extra, "scope": scope, "metric": metric, "kind": kind, "model": model,
                    "arm": arm, "pair": pair_label(kind, model, arm, control),
                    "is_difference": difference, **boot.as_dict(),
                    "excludes_zero": boot.excludes_zero if difference else None,
                    "reads_derived": any((m, a) in derived_arms for m in involved for a in arms)})
    return out


def verdict(row, sensitive: bool) -> str:
    """The criterion's reading of one h4 row: whether the kill fires, and how."""
    if row.ci_lo > 0.0 and not sensitive:
        return HOLDS
    if row.ci_lo > 0.0:
        return "killed: holds zero at the margin, the star lost under a check seed"
    if row.ci_hi < 0.0 and sensitive:
        return "killed: inside the interval, holding zero at the margin, the star lost under a check seed"
    if row.ci_hi < 0.0:
        return "killed: the reduction is smaller than the control's, beyond the interval"
    return "killed: inside the interval"


def json_value(value):
    """A numpy scalar as its JSON type; anything else JSON does not hold as its string."""
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return str(value)


def cell_table(pairing: Pairing, cohorts: dict[str, mt.ScoredCohort]) -> pd.DataFrame:
    """Every shared cell's |Cox slope - 1| per model, arm and context draw, unresampled."""
    records = []
    for date, cohort in pairing.cells:
        c = cohorts[cohort]
        for model, seeds in pairing.models.items():
            for k, seed in enumerate(seeds):
                row = {"build_date": date, "cohort": cohort, "age_quarters": pairing.age(date, cohort),
                       "model": model, "context_seed": seed, "rows": int(c.outcome.size),
                       "defaults": int(c.outcome.sum()),
                       "criterion": (date, cohort) in pairing.criterion,
                       "regime": pairing.regime.get(cohort)}
                for arm in ARMS:
                    key = (pairing.builds[(arm, date)], model)
                    s = c.scores[key] if seed is None else c.seeds[key][k]
                    row[f"deviation_{arm}"] = bi.cox_slope_deviation(c.outcome, s)
                records.append(row)
    table = pd.DataFrame(records)
    table["context_seed"] = table["context_seed"].astype("Int64")
    return table


def contrast_of(pairing: Pairing, sources: dict[str, dict[str, list[Path]]],
                path: Path | None) -> dict[str, dict]:
    """Per build date the arm contrast: the share of the expanding pool the rolling window holds.

    The pools are read from the classical score runs' build.json; the mean
    age of a training row on each arm comes from an arm-contrast record
    when one is named (`arm_contrast.py`, keyed by the build's half-year).
    A record whose share differs from build.json's by more than
    `SHARE_TOLERANCE` on a date was measured on another grid, and is refused.
    """
    out: dict[str, dict] = {d: {} for d in pairing.dates}
    for date in pairing.dates:
        pools = {}
        for arm in ARMS:
            for directory in sources[arm][pairing.builds[(arm, date)]]:
                record = directory / "build.json"
                if record.is_file():
                    build = json.loads(record.read_text(encoding="utf-8")).get("build", {})
                    if "train_rows" in build:
                        pools[arm] = int(build["train_rows"])
                        break
        if len(pools) == 2:
            out[date].update({"expanding_rows": pools[EXPANDING], "rolling_rows": pools[ROLLING],
                              "share_held": round(pools[ROLLING] / pools[EXPANDING], 4)})
    if path is not None:
        record = json.loads(path.read_text(encoding="utf-8"))
        width = str(record["study_rolling_quarters"])
        by_date = {b["build_id"]: b for b in record["builds"]}
        for date in pairing.dates:
            entry = by_date.get(date)
            if entry is None:
                raise SystemExit(f"{path.as_posix()} holds no build {date}")
            rolling = entry["rolling"][width]
            recorded, held = rolling["share_of_expanding"], out[date].get("share_held")
            if recorded is not None and held is not None and abs(recorded - held) > SHARE_TOLERANCE:
                raise SystemExit(f"{path.as_posix()} records the rolling window holding "
                                 f"{recorded:.2%} of the expanding pool at {date}, the score "
                                 f"runs' build.json {held:.2%}; the record is of another grid")
            out[date].update({
                "recorded_share_held": rolling["share_of_expanding"],
                "mean_age_gap_quarters": round(entry["expanding_mean_age_quarters"]
                                               - rolling["mean_age_quarters"], 3)})
    return out


def plot_cells(table: pd.DataFrame, paired: pd.DataFrame, out: Path) -> None:
    """Each criterion cell's |Cox slope - 1| on the rolling arm against the expanding, per model.

    A point under the diagonal is a cell the rolling window brought nearer
    a slope of one. A seeded model's point is the mean over its draws.
    """
    cells = table[table["criterion"]].groupby(["model", "build_date", "cohort"], sort=False)[
        [f"deviation_{EXPANDING}", f"deviation_{ROLLING}"]].mean().reset_index()
    names = model_names(cells["model"].unique())
    fig, axes = plt.subplots(1, len(names), figsize=(3.6 * len(names), 4.0), squeeze=False)
    rows = paired[(paired["kind"] == "reduction") & (paired["scope"] == POOLED)
                  & (paired["cohorts"] == "all") & paired["draw"].isna()].set_index("model")
    top = float(np.nanmax(cells[[f"deviation_{EXPANDING}", f"deviation_{ROLLING}"]].to_numpy()))
    top = 1.05 * top if np.isfinite(top) and top > 0 else 1.0
    for ax, model in zip(axes[0], names):
        sub = cells[cells["model"] == model]
        ax.scatter(sub[f"deviation_{EXPANDING}"], sub[f"deviation_{ROLLING}"], s=9,
                   color=bi.model_colour(model), alpha=0.7)
        ax.plot([0, top], [0, top], color="black", linewidth=0.8, linestyle=":")
        ax.set_xlim(0, top)
        ax.set_ylim(0, top)
        title = bi.describe(model)
        if model in rows.index:
            r = rows.loc[model]
            title += f"\nE - R {r.value:+.4f} [{r.ci_lo:+.4f}, {r.ci_hi:+.4f}]"
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("|Cox slope - 1|, expanding arm")
        ax.grid(alpha=0.3)
    axes[0][0].set_ylabel("|Cox slope - 1|, rolling arm")
    fig.suptitle("every criterion cell on both arms, one point per build date and cohort", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=130)
    plt.close(fig)


def plot_build_rows(paired: pd.DataFrame, dates: list[str], contrast: dict[str, dict],
                    out: Path) -> None:
    """Per non-control model, h4 on each build date with its interval, the pooled row as a band."""
    rows = paired[(paired["kind"] == "h4") & (paired["cohorts"] == "all") & paired["draw"].isna()]
    models = model_names(rows["model"].unique())
    if not models:
        return
    fig, axes = plt.subplots(1, len(models), figsize=(4.2 * len(models), 3.8), squeeze=False)
    x = np.arange(len(dates))
    labels = []
    for date in dates:
        share = contrast.get(date, {}).get("share_held")
        labels.append(date if share is None else f"{date}\nholds {share:.0%}")
    for ax, model in zip(axes[0], models):
        sub = rows[rows["model"] == model].set_index("scope")
        whole = sub.loc[POOLED]
        ax.axhspan(whole.ci_lo, whole.ci_hi, color="#0E6B66", alpha=0.15, linewidth=0)
        ax.axhline(whole.value, color="#0E6B66", linewidth=1.2, label="every shared cell")
        per = sub.loc[dates]
        ax.vlines(x, per["ci_lo"], per["ci_hi"], color="#9A5B24", linewidth=1.2)
        ax.plot(x, per["value"], marker="o", markersize=4, color="#9A5B24", linestyle="none",
                label="one build date")
        ax.axhline(0.0, color="black", linewidth=0.8, linestyle=":")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        ax.set_title(f"{bi.describe(model)} minus the control\n(E - R) of |Cox slope - 1|",
                     fontsize=9)
        ax.grid(alpha=0.3, axis="y")
    handles, texts = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, texts, loc="lower center", ncol=2, frameon=False, fontsize=9)
    fig.suptitle("the rolling arm's reduction of calibration drift, model minus control, per build "
                 "date; the label under a date is the share of the expanding pool the rolling "
                 "window holds", fontsize=10)
    fig.tight_layout(rect=(0, 0.06, 1, 0.9))
    fig.savefig(out, dpi=130)
    plt.close(fig)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--expanding", type=Path, nargs="+", required=True,
                        help="score directories of the expanding arm's builds, or recorded "
                             "poolings whose intervals.json names them")
    parser.add_argument("--rolling", type=Path, nargs="+", required=True,
                        help="score directories of the rolling arm's builds, or recorded "
                             "poolings whose intervals.json names them")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--control", default=CONTROL,
                        help=f"the model every other model's reduction is read against "
                             f"(default {CONTROL})")
    parser.add_argument("--cells", type=Path, default=None,
                        help="the build run's cells.csv: a cell enters only if its cohort clears "
                             "the floors, and the pre-flag and flagged cells are pooled apart")
    parser.add_argument("--contrast", type=Path, default=None,
                        help="an arm-contrast record (arm_contrast.py) whose mean training-row "
                             "ages are printed beside each build date")
    parser.add_argument("--outcome", default="outcome",
                        help="the score files' column read as the outcome: outcome, the study's "
                             "label, or outcome_reported, the sensitivity reading, which the "
                             "Freddie Mac book's score files hold")
    parser.add_argument("--drop", default="",
                        help="comma-separated model names to leave out of everything")
    parser.add_argument("--resamples", type=int, default=mt.RESAMPLES)
    parser.add_argument("--seed", type=int, default=bi.BOOTSTRAP_SEED)
    parser.add_argument("--check-seeds", default="",
                        help="comma-separated bootstrap seeds to repeat every pooling under")
    parser.add_argument("--no-per-draw", action="store_true",
                        help="skip the pooling with each context draw held fixed")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.time()
    check_seeds = [int(s) for s in args.check_seeds.split(",") if s.strip()]
    if args.seed in check_seeds:
        raise SystemExit(f"--check-seeds repeats the primary seed {args.seed}")
    dropped = [m for m in args.drop.split(",") if m]
    if args.control in dropped:
        raise SystemExit(f"--drop removes the control {args.control}")

    sources = {EXPANDING: group_sources(args.expanding, EXPANDING),
               ROLLING: group_sources(args.rolling, ROLLING)}
    dated = {arm: {build_date(b, arm): b for b in sources[arm]} for arm in ARMS}
    alone = sorted(set(dated[ROLLING]) - set(dated[EXPANDING]))
    if alone:
        raise SystemExit("rolling builds with no expanding build at the same date: "
                         + ", ".join(dated[ROLLING][d] for d in alone))
    unpaired = sorted(dated[EXPANDING][d] for d in set(dated[EXPANDING]) - set(dated[ROLLING]))
    dates = sorted(dated[ROLLING])
    builds = {(arm, d): dated[arm][d] for arm in ARMS for d in dates}
    matrix = matrix_check({arm: [p for b in sources[arm] if b not in unpaired
                                 for p in sources[arm][b]] for arm in ARMS})

    # A model at 1.0 that some build of either arm does not hold, as when its
    # derivation is refused on a rolling build, leaves the pairing and is named;
    # any other model missing on a build refuses the pairing.
    held = {builds[(arm, d)]: models_held(sources[arm][builds[(arm, d)]]) for arm in ARMS
            for d in dates}
    every = set().union(*held.values())
    missing = sorted(set(dropped) - every)
    if missing:
        raise SystemExit(f"--drop names models that hold no rows: {', '.join(missing)}")
    partial = {m: sorted(b for b, ms in held.items() if m not in ms)
               for m in sorted(every - set(dropped)) if any(m not in ms for ms in held.values())}
    refused = [m for m in partial if not at_temperature_one(m)]
    if refused:
        raise SystemExit("the arms carry different models or seeds: " + "; ".join(
            f"{m} absent on {', '.join(partial[m])}" for m in refused))

    stage = time.time()
    loaded = {arm: ai.Arm(outcome=args.outcome) for arm in ARMS}
    for arm in ARMS:
        for date in dates:
            build = builds[(arm, date)]
            loaded[arm].add_build(sources[arm][build],
                                  [m for m in [*dropped, *partial] if m in held[build]])
    pairing = Pairing(loaded[EXPANDING], loaded[ROLLING], dates, builds)
    if args.control not in pairing.models:
        raise SystemExit(f"the control {args.control} holds no rows")
    if not any(bi.base_model(m) in CRITERION_MODELS for m in pairing.models):
        raise SystemExit("no foundation model holds rows on both arms; H4 is not read off the "
                         "classical models")
    outcomes = pairing.arms[EXPANDING].outcome
    if args.cells is not None:
        pairing.floor, pairing.regime = read_cells(args.cells, builds, pairing.cells, outcomes)
        pairing.criterion = {(d, c) for d, c in pairing.cells if pairing.floor[c]}
    else:
        bi.check_floors({c: outcomes[c] for c in sorted({c for _, c in pairing.cells})}, None)
    under = sorted({c for d, c in pairing.cells if (d, c) not in pairing.criterion})
    contrast = contrast_of(pairing, sources, args.contrast)
    derived: dict[str, list[dict]] = {}
    for arm in ARMS:
        for build in (builds[(arm, d)] for d in dates):
            for path in sources[arm][build]:
                entry = bi.derivation_of(path)
                if entry is not None and entry["model"] in pairing.models:
                    derived.setdefault(entry["model"], []).append(
                        {"build_id": build, "arm": arm, **entry})
    derived_arms = {(model, e["arm"]) for model, entries in derived.items() for e in entries}

    print(f"build dates           : {len(dates)}: {', '.join(dates)}")
    print("builds                : " + ", ".join(f"{builds[(EXPANDING, d)]} / {builds[(ROLLING, d)]}"
                                                 for d in dates))
    if unpaired:
        print(f"left out              : {', '.join(unpaired)}, no rolling build at the same date")
    print(f"shared cells          : {len(pairing.cells)} over "
          f"{len({c for _, c in pairing.cells})} distinct cohorts; {len(pairing.criterion)} "
          "enter the criterion")
    if args.cells is not None:
        print(f"under the floors      : {', '.join(under) or 'none'}, scored and pooled into nothing")
    print(f"outcome read          : {args.outcome}")
    print("models                : " + ", ".join(
        f"{m} ({len(s)} draw{'s' if len(s) > 1 else ''})" if s != [None] else m
        for m, s in pairing.models.items()))
    if dropped:
        print(f"models dropped        : {', '.join(dropped)}")
    for model, lacking in partial.items():
        print(f"  {model} left out: at softmax temperature 1.0 and absent on "
              f"{', '.join(lacking)}; no H4 row is computed for it")
    print(f"matrix                : {matrix['ablation'] or 'primary'}; columns recorded by "
          f"{', '.join(sorted(matrix['features'])) or 'no directory'}, the same on both arms")
    print(f"loaded in             : {time.time() - stage:.0f}s")
    if not pairing.criterion:
        raise SystemExit("no shared cell enters the criterion")

    every_cohort = pairing.cohorts()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    table = cell_table(pairing, every_cohort)
    table.to_csv(args.out_dir / "cells.csv", index=False)
    # Only the criterion's cohorts enter the resample: a cohort under the floors would draw
    # a row index, and under the resampled pooling be picked, for no cell of the statistic.
    in_criterion = {c for _, c in pairing.criterion}
    cohorts = {c: v for c, v in every_cohort.items() if c in in_criterion}

    poolings = [("all", False, True), ("all, cohorts resampled", True, False)]
    records: list[dict] = []
    left_out: dict[str, dict] = {}

    def record(which: str, draw: int | None, result: dict[str, mt.Bootstrap]) -> None:
        result, counts = bi.left_out_of(result)
        left_out[which if draw is None else f"{which}, draw {draw}"] = counts
        records.extend(records_of(result, args.control, derived_arms, cohorts=which, draw=draw))

    for which, clustered, per_build in poolings:
        stage = time.time()
        result = mt.cohort_blocked_bootstrap_many(
            cohorts, between_arm_statistics(pairing, pairing.models, args.control, per_build),
            resamples=args.resamples, seed=args.seed, resample_cohorts=clustered)
        record(which, None, result)
        print(f"bootstrap {which:<22}: {args.resamples} resamples in {time.time() - stage:.0f}s",
              flush=True)

    repeats: list[dict] = []
    for check_seed in check_seeds:
        stage = time.time()
        for which, clustered, per_build in poolings:
            result = mt.cohort_blocked_bootstrap_many(
                cohorts, between_arm_statistics(pairing, pairing.models, args.control, per_build),
                resamples=args.resamples, seed=check_seed, resample_cohorts=clustered)
            result, _ = bi.left_out_of(result)
            repeats.extend(r for r in records_of(result, args.control, derived_arms, cohorts=which,
                                                 bootstrap_seed=check_seed)
                           if r["is_difference"])
        print(f"bootstrap seed {check_seed:<17}: every pooling again in {time.time() - stage:.0f}s",
              flush=True)

    draw_count = next(iter(cohorts.values())).draws
    common = sorted(set.intersection(*(set(s) for s in pairing.models.values() if s != [None]))) \
        if draw_count > 1 and not args.no_per_draw else []
    for k, seed_value in enumerate(common):
        stage = time.time()
        fixed = {key: c.realise(k) for key, c in cohorts.items()}
        models_k = {m: ([None] if s == [None] else [s[k]]) for m, s in pairing.models.items()}
        # Every scope, so that a disagreement between the draws is measured on each row it flags.
        result = mt.cohort_blocked_bootstrap_many(
            fixed, between_arm_statistics(pairing, models_k, args.control, True),
            resamples=args.resamples, seed=args.seed)
        record("all", seed_value, result)
        print(f"draw {seed_value} held fixed   : {args.resamples} resamples in "
              f"{time.time() - stage:.0f}s", flush=True)

    paired = pd.DataFrame(records)
    paired["draw"] = paired["draw"].astype("Int64")
    paired.to_csv(args.out_dir / "paired.csv", index=False)

    # Keyed by (scope, pair): a row is flagged only where its own scope's draws disagree.
    disagreeing: dict[tuple[str, str], list[dict]] = {}
    if common:
        per_draw = paired[paired["draw"].notna() & paired["is_difference"]]
        for (scope, pair), rows in per_draw.groupby(["scope", "pair"], sort=False):
            spans = list(zip(rows["draw"], rows["ci_lo"], rows["ci_hi"]))
            if any(a_hi < b_lo or b_hi < a_lo for i, (_, a_lo, a_hi) in enumerate(spans)
                   for (_, b_lo, b_hi) in spans[i + 1:]):
                disagreeing[(scope, pair)] = [{"draw": int(d), "ci_lo": float(lo), "ci_hi": float(hi)}
                                              for d, lo, hi in spans]

    checked: dict | None = None
    sensitive: set[tuple[str, str, str]] = set()
    if repeats:
        again = pd.DataFrame(repeats)
        primary = paired[paired["draw"].isna() & paired["is_difference"]]
        checked = ai.seed_check(primary, again)
        sensitive = {(c["cohorts"], c["scope"], c["pair"]) for c in checked["star_changed"]}
        pd.concat([primary.assign(bootstrap_seed=args.seed)[again.columns], again],
                  ignore_index=True).to_csv(args.out_dir / "paired-seeds.csv", index=False)

    main_rows = paired[(paired["cohorts"] == "all") & paired["draw"].isna()]
    names = model_names(pairing.models)
    print(f"\n|Cox slope - 1| over the {len(pairing.criterion)} shared criterion cells, the mean "
          "on each arm and E - R (value [lo, hi], * excludes zero, ! draws disagree"
          + (", ? star changes with the bootstrap seed" if checked else "")
          + (", ~ reads derived rows, their error below" if derived else "") + "):")

    def flags(row) -> str:
        out = "*" if row.excludes_zero else " "
        out += "!" if (row.scope, row.pair) in disagreeing else " "
        out += "?" if ("all", row.scope, row.pair) in sensitive else " "
        return out + ("~" if row.reads_derived else "")

    pooled = main_rows[main_rows["scope"] == POOLED]
    for model in names:
        mean = pooled[(pooled["kind"] == "mean") & (pooled["model"] == model)].set_index("arm")
        red = pooled[(pooled["kind"] == "reduction") & (pooled["model"] == model)].iloc[0]
        print(f"  {model:<11} E {mean.loc[EXPANDING].value:.4f}  R {mean.loc[ROLLING].value:.4f}"
              f"  E - R {red.value:+.4f} [{red.ci_lo:+.4f}, {red.ci_hi:+.4f}] {flags(red)}")
    print(f"\nH4, each model's E - R minus {args.control}'s, on the same resample:")
    scopes_shown = [POOLED, BUILDS, *[s for s in REGIME_SCOPES if s in set(main_rows["scope"])]]
    for scope in scopes_shown:
        for row in main_rows[(main_rows["kind"] == "h4") & (main_rows["scope"] == scope)].itertuples():
            print(f"  {scope:<9} {row.model:<11} {row.value:+.4f} "
                  f"[{row.ci_lo:+.4f}, {row.ci_hi:+.4f}] {flags(row)}")
    resampled = paired[(paired["cohorts"] == "all, cohorts resampled") & (paired["kind"] == "h4")]
    for row in resampled.itertuples():
        print(f"  resampled {row.model:<11} {row.value:+.4f} [{row.ci_lo:+.4f}, {row.ci_hi:+.4f}] "
              f"{flags(row)}")
    contrast_rows = main_rows[main_rows["kind"] == SCOPE_DIFFERENCE]
    if len(contrast_rows):
        print("\nH4 on the pre-flag scope minus H4 on the flagged scope, on the same resample "
              "(beside kill criterion 4, no criterion):")
        for row in contrast_rows.itertuples():
            print(f"  {row.model:<11} {row.value:+.4f} [{row.ci_lo:+.4f}, {row.ci_hi:+.4f}] "
                  f"{flags(row)}")
    for (scope, pair), spans in disagreeing.items():
        if scope not in (POOLED, *REGIME_SCOPES):
            continue
        print(f"  {scope} {pair}: draw intervals " + "; ".join(
            f"{s['draw']} [{s['ci_lo']:+.4f}, {s['ci_hi']:+.4f}]" for s in spans))
    for which, counts in left_out.items():
        for key, count in counts.items():
            _, _, scope = key.partition("|")
            if scope not in (POOLED, BUILDS):
                continue
            over = "" if ", draw " in which else ", averaged over the context draws"
            unit = "cells" if scope == POOLED else "build dates"
            print(f"  {METRIC} ({which}, {scope}): {count['point']:g} {unit} not estimable left out "
                  f"on both arms{over}, at most {count['largest_in_a_resample']:g} of any resample")
    for model, entries in derived.items():
        for entry in entries:
            label = f"{model} on {entry['build_id']}"
            print(f"  ~ {bi.derivation_text(entry, label)}")

    print("\nper build date, H4 with its interval and the arm contrast:")
    for date in dates:
        c = contrast[date]
        parts = []
        if "share_held" in c:
            parts.append(f"score runs' build.json: rolling holds {c['share_held']:.1%} of "
                         f"{c['expanding_rows']:,}")
        if "mean_age_gap_quarters" in c:
            parts.append(f"contrast record: rolling holds {c['recorded_share_held']:.1%}, mean "
                         f"row {c['mean_age_gap_quarters']:.2f} quarters younger")
        rows = main_rows[(main_rows["kind"] == "h4") & (main_rows["scope"] == date)]
        print(f"  {date:<8} " + "  ".join(
            f"{r.model} {r.value:+.4f} [{r.ci_lo:+.4f}, {r.ci_hi:+.4f}]{'*' if r.excludes_zero else ''}"
            for r in rows.itertuples()) + (f"   ({'; '.join(parts)})" if parts else ""))

    reading: dict[str, dict] = {}
    h4_rows = pooled[pooled["kind"] == "h4"].set_index("model")
    for model in h4_rows.index:
        row = h4_rows.loc[model]
        entry = {"value": float(row.value), "ci_lo": float(row.ci_lo), "ci_hi": float(row.ci_hi),
                 "star_changes_with_seed": ("all", POOLED, row.pair) in sensitive,
                 "reading": verdict(row, ("all", POOLED, row.pair) in sensitive),
                 "criterion": model in CRITERION_MODELS}
        entry["kill_fires"] = entry["reading"] != HOLDS
        if pairing.regime:
            signs = {}
            for scope in REGIME_SCOPES:
                sub = main_rows[(main_rows["kind"] == "h4") & (main_rows["scope"] == scope)
                                & (main_rows["model"] == model)]
                if len(sub):
                    signs[scope] = float(sub["value"].iloc[0])
            entry["regime_values"] = signs
            entry["regimes_disagree_in_sign"] = bool(
                len(signs) == 2 and np.sign(signs["pre-flag"]) != np.sign(signs["flagged"]))
            if entry["regimes_disagree_in_sign"]:
                # Kill criterion 4 of EXP-005: the verdict belongs to the label's reporting
                # regime and is undetermined; the arm row's own reading is kept beside it.
                entry["reading_on_arm_row"] = entry["reading"]
                entry["kill_fires_on_arm_row"] = entry["kill_fires"]
                entry["reading"] = UNDETERMINED
                entry["kill_fires"] = None
        reading[model] = entry
    print(f"\nthe criterion, per foundation model at its library settings, on the "
          f"{len(pairing.criterion)} shared criterion cells under the {args.outcome} column:")
    for model, entry in reading.items():
        if not entry["criterion"]:
            continue
        line = f"  {model:<11} {entry['reading']}"
        if entry.get("regimes_disagree_in_sign"):
            line += f"; on the arm row alone: {entry['reading_on_arm_row']}"
        print(line)
        tagged = [m for m in reading if bi.base_model(m) == model and m != model]
        for other in tagged:
            if reading[other]["kill_fires"] != entry["kill_fires"]:
                print(f"  {'':<11} {other} reads otherwise: {reading[other]['reading']}")
        for other, lacking in partial.items():
            if bi.base_model(other) == model:
                print(f"  {'':<11} {other} not read: absent on {', '.join(lacking)}")
    if args.outcome != "outcome":
        print("  read under a second label; reported beside the criterion, not a verdict")
    if checked:
        print(f"\nbootstrap seed check over seeds {', '.join(map(str, checked['seeds']))}: "
              f"{checked['arm_starred']} of {checked['arm_differences']} pooled differences "
              f"starred under seed {args.seed}, {checked['arm_star_changed']} change their star; "
              f"{checked['starred']} of {checked['differences']} at every scope, "
              f"{len(checked['star_changed'])} change; largest movement of an interval bound "
              f"{checked['largest_bound_movement']:.4f}")
    if not common:
        print("  no per-draw rows: every interval above mixes the context draws"
              if not args.no_per_draw else "  per-draw rows skipped")

    plot_cells(table, paired, args.out_dir / "arm-cells.png")
    plot_build_rows(paired, dates, contrast, args.out_dir / "build-rows.png")

    summary = {
        "hypothesis": "H4: the rolling arm reduces calibration drift for the foundation models "
                      "by more than for GBM-50k",
        "build_dates": dates,
        "builds": {d: {arm: builds[(arm, d)] for arm in ARMS} for d in dates},
        "builds_left_out": unpaired,
        "cells_shared": len(pairing.cells),
        "cells_criterion": len(pairing.criterion),
        "cohorts_under_floors": under,
        "outcome": args.outcome,
        "matrix": matrix,
        "models": {m: ([] if s == [None] else s) for m, s in pairing.models.items()},
        "models_dropped": dropped,
        "models_not_on_every_build": partial,
        "control": args.control,
        "sources": {arm: {b: [p.as_posix() for p in ps] for b, ps in sources[arm].items()}
                    for arm in ARMS},
        "derived_rows": derived,
        "contrast": contrast,
        "contrast_sources": {
            "expanding_rows, rolling_rows, share_held": "the score runs' build.json, train_rows",
            "recorded_share_held, mean_age_gap_quarters": "the arm-contrast record"},
        "contrast_record": args.contrast.as_posix() if args.contrast else None,
        "cells_record": args.cells.as_posix() if args.cells else None,
        "statistics": {
            "mean": "per model and arm, the mean over the shared criterion cells of |Cox slope - "
                    "1|, the cells every model's fit finished on, on both arms",
            "reduction": "per model, the expanding arm's mean minus the rolling arm's: positive "
                         "when the rolling window brings the scores nearer a slope of one",
            "h4": f"per model other than the control, its reduction minus {args.control}'s on "
                  "the same resample"},
        "scopes": "'arm' is every shared criterion cell; 'builds' is the mean over build dates of "
                  "each date's own statistic, every date weighted alike; a date is that date "
                  "alone; 'pre-flag' and 'flagged' are the cells of those label regimes when the "
                  "build run's cells are given. Only 'arm' is reported with the cohorts resampled",
        "criterion": {
            "statement": "the kill fires for a foundation model at its library settings, at the "
                         "shipped softmax temperature 0.9, unless its h4 interval at the scope "
                         "'arm', cohorts held fixed, lies above zero under the primary bootstrap "
                         "seed and every check seed; the rows at 1.0 are on the table, and a "
                         "verdict that differs between the settings is reported as differing",
            "reading": reading},
        "bootstrap": {
            "resamples": args.resamples, "seed": args.seed, "alpha": mt.ALPHA,
            "blocking": "cohort, one row index per cohort shared by every build of both arms "
                        "that scores it and by every model",
            "context_draw": ("drawn with the resample, jointly across models, builds and arms"
                             if draw_count > 1 else "one draw; every interval is conditional on it"),
            "poolings": [p[0] for p in poolings],
            "per_draw": ("the 'all' pooling repeated with each context draw held fixed, in the "
                         "rows whose draw is set" if common else None),
            "draws_disagree": ({f"{scope}: {pair}": spans for (scope, pair), spans
                                in disagreeing.items()} if common else None),
            "seed_check": checked,
            "cox_left_out": left_out,
            "cox_rule": "a cell on which some model's Cox fit did not finish, on either arm, "
                        "leaves the pairing for every model on both arms, in the point estimate "
                        "and in every resample",
            "multiplicity": "none: every interval is reported at alpha on its own"},
        "wall_seconds": round(time.time() - started, 1),
    }
    # The run's manifest pins the files named on its command line; the score files it reads
    # sit inside the directories named there, so each is hashed here.
    inputs = [*(p for arm in ARMS for ps in sources[arm].values() for p in ps),
              *(p for p in (args.cells, args.contrast) if p is not None)]
    hashed = {}
    for path in inputs:
        for item in sorted(path.rglob("*") if path.is_dir() else [path]):
            if item.is_file():
                hashed[item.as_posix()] = rr.file_hash(item)
    (args.out_dir / "inputs.json").write_text(json.dumps(hashed, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=json_value),
                                               encoding="utf-8")
    print(f"\nwall                  : {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
