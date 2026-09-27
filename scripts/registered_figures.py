#!/usr/bin/env python3
"""The registered figures of EXP-002 and EXP-005 that no recorded run drew, and the redraws.

Every open detail of each figure is fixed in the dated entries of 2026-09-25
in `docs/experiments/EXP-002-log.md` (the Lending Club ridge) and
`docs/experiments/EXP-005-log.md` (everything else); this script draws what
those entries say and nothing else. One subcommand per figure, each run in a
recording of its own:

    lc-ridge       the score distribution of every model at every cohort of
                   2015H1-E against the reference its PSI bins were fixed on
    fm-ridge       the same on 2002H2-E, against the training reference and
                   against the first scored cohort
    reliability    the reliability curve per model at the youngest cohort,
                   2007H2, 2013H2 and 2023H2 of 2002H2-E, and on 2019H1 under
                   both label readings
    relief-share   EXP-003's relief share per quarter, the criterion cells of
                   the grid and the three label regimes
    build-grid     the build record's grid with what each build was allowed
                   to know and its blind rows
    metric-age     AUC, Cox slope and PSI against age in half-years, one panel
                   per build, one line per model
    auc-age        an arm pooling's AUC-against-age figure with the cells
                   under the floors drawn open
    level          an in-sample recording's level figure on one shared axis

Nothing is refitted and nothing is pooled. A figure reads score directories
and records made with no model in them, and draws or prints no statistic of a
recorded run the claim gate refuses at HEAD: every run read for a number
passes `check_claims.check_code` first, and the build record, whose own run
the gate refuses, is read only where it hashes to the value a run the gate
accepts pins for it. The per-build grid recordings of the Freddie Mac book
are refused, so `metric-age` computes each cell from their score directories
with the metric module, as a grid recording computes a cell, and compares
the values with theirs without drawing any of them.

Each run writes the figure, `summary.json` with the counts it read and
checked, and `inputs.json` with the sha256 of every file it read.

    python scripts/record_run.py fm-reliability -- \\
        python scripts/registered_figures.py reliability \\
            experiments/2026-09-13-fm-2002h2e-scores ... \\
            --cells experiments/2026-09-13-fm-vintage-builds2/cells.csv \\
            --out-dir experiments/2026-09-26-fm-reliability
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FixedLocator, LogLocator, NullFormatter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import arm_intervals as ai
import build_intervals as bi
import check_claims as cc
import in_sample_level as isl
import record_run as rr

from outoftime import metrics as mt

ROOT = Path(__file__).resolve().parent.parent

FIRST_DRAW = 20260911
# The columns of every figure that reads a build's score directories: the five
# models at 0.9 and the two foundation models again at 1.0.
COLUMNS = ("scorecard", "gbm", "gbm-50k", "tabpfn", "tabicl", "tabpfn@t1", "tabicl@t1")
FIXED = ("scorecard", "gbm")
SCORE_COLUMNS = ["build_id", "arm", "model", "context_seed", "cohort", "age_quarters", "row",
                 "outcome", "pd"]
REFERENCE_COLUMNS = ["build_id", "model", "context_seed", "pd"]

# The ridge: histogram bins of log10 of the probability, at fixed edges, and
# the x range from these percentiles of every row a figure draws.
BIN_WIDTH = 0.05
RANGE_PERCENTILES = (0.1, 99.9)
# How many row spacings the tallest density of a ridge reaches.
RIDGE_REACH = 1.6
# The reliability axes and the level axes: the plotted extremes divided and
# multiplied by these.
RELIABILITY_MARGIN = 1.2
LEVEL_MARGIN = 1.4
# The share of the build grid's log axis kept above the highest rate for its notes.
HEADROOM = 0.27

# Every figure is drawn at the size the paper prints it: the text width of the
# tmlr style and at most a page with its caption, in inches, with the smallest
# type at that size in points.
PRINT_WIDTH = 6.5
PRINT_HEIGHT = 8.5
TEXT_PT = 7.0
TICK_PT = 6.5
TITLE_PT = 8.0
DPI = 300
PRINT_RC = {"font.size": TEXT_PT, "axes.titlesize": TEXT_PT, "axes.labelsize": TEXT_PT,
            "xtick.labelsize": TICK_PT, "ytick.labelsize": TICK_PT, "legend.fontsize": TEXT_PT,
            "figure.titlesize": TITLE_PT, "axes.linewidth": 0.6, "lines.linewidth": 0.9,
            "lines.markersize": 3.5, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
            "xtick.minor.width": 0.4, "ytick.minor.width": 0.4, "xtick.major.size": 2.5,
            "ytick.major.size": 2.5, "xtick.minor.size": 1.5, "ytick.minor.size": 1.5,
            "xtick.major.pad": 2.0, "ytick.major.pad": 2.0, "axes.titlepad": 3.0,
            "axes.labelpad": 2.0, "legend.handlelength": 1.6, "legend.handletextpad": 0.5,
            "legend.columnspacing": 1.2, "legend.borderaxespad": 0.2, "grid.linewidth": 0.5,
            "hatch.linewidth": 0.5, "patch.linewidth": 0.6}
# How many characters of 7-point type fit in an inch, for wrapping text to a width.
CHARS_PER_INCH = 72 / (TEXT_PT * 0.55)


def wrap(text: str, inches: float) -> str:
    """Text broken into lines that fit `inches` of 7-point type, its own breaks kept."""
    width = max(8, int(inches * CHARS_PER_INCH))
    return "\n".join(textwrap.fill(line, width, break_on_hyphens=False, break_long_words=False)
                     for line in text.split("\n"))


def wrap_title(text: str) -> str:
    """A figure title broken into lines that fit the page at the title's size."""
    return wrap(text, (PRINT_WIDTH - 0.2) * TEXT_PT / TITLE_PT)


def lines_in(text: str) -> int:
    return text.count("\n") + 1


def pt(points: float) -> float:
    """Points in inches."""
    return points / 72

RELIABILITY_COHORTS = ("2003H1", "2007H2", "2013H2", "2023H2")
BOTH_READINGS = "2019H1"
REPORTED = "outcome_reported"
COHORT_COLOUR = {"2003H1": "#4B3F8F", "2007H2": "#B23A48", "2013H2": "#0E6B66",
                 "2023H2": "#C9A227"}

# The marks of the figure of metric against age (EXP-005 log, 2026-09-25).
MARKS = {"crisis 2007H1 to 2008H2": ("2007H1", "2008H2", "#B23A48"),
         "2022H1 to 2023H2": ("2022H1", "2023H2", "#C9A227")}
# The label regimes as the Setting defines them on half-years.
REGIMES = (("pre-flag", None, "2011H1", "#EDEDED"), ("straddling", "2011H2", "2013H2", "#D6D6D6"),
           ("flagged", "2014H1", None, "#F6F1E1"))
UNDER = "under the floors: scored, pooled into nothing"
REFERENCE_COLOUR = "#333333"

# The build record's files are read only where a recording the claim gate
# accepts pins them, and only at that recording's value.
PINS = {
    "experiments/2026-09-13-fm-vintage-builds2/builds.json":
        "experiments/2026-09-22-fm-grid-in-sample",
    "experiments/2026-09-13-fm-vintage-builds2/cells.csv":
        "experiments/2026-09-21-fm-arm-e-intervals",
}

# The recordings the log entries name as each figure's sources. A figure whose
# score directories are not the ones the named recording lists, or whose
# pointer names another run, stops.
NAMED = {
    "lc-grid": "experiments/2026-09-23-lc-2015h1e-intervals-grid",
    "fm-grid": "experiments/2026-09-15-fm-2002h2e-intervals-grid",
    "structure": "experiments/2026-09-19-fm-vintage-structure",
    "sensitivity": "experiments/2026-09-22-fm-between-arm-intervals-outcome-reported",
}

# What the log entries of 2026-09-25 state about the inputs of each figure; a
# run that reads anything else stops.
EXPECTED: dict[str, dict] = {
    "lc-ridge": {"build": "2015H1-E", "cohorts": 11, "rows_per_cohort": [20000],
                 "training_rows": 323026, "draw_rows": 50000, "under_floors": []},
    "fm-ridge": {"build": "2002H2-E", "cohorts": 42, "training_rows": 79511, "draw_rows": 50000,
                 "first_cohort": "2003H1",
                 "under_floors": ["2003H1", "2013H1", "2014H2", "2015H1", "2020H2", "2021H1"]},
    "reliability": {"build": "2002H2-E", "rows_2003H1": 24276, "defaults_2003H1": 72,
                    "rows_2019H1": 24752, "defaults_2019H1": 110, "reported_2019H1": 1134,
                    "record_labelled_reported_2019H1": 24753, "record_reported_2019H1": 1135,
                    "span": 21.6, "span_above_floors": 10.8},
    "relief-share": {"quarters": 84, "criterion_cells": 356, "criterion_E": 196,
                     "criterion_R": 160, "max_gap": 0.0017, "max_gap_half": "2023H2",
                     "first_nonzero": "2012Q2"},
    "build-grid": {"panels": 9, "blind_rows_min": 107578, "blind_rows_max": 111469},
    "metric-age": {"builds": 17, "cells": 426, "under_floors": 70},
    "auc-age": {"builds": 9, "cells": 234, "under_floors": 38},
    "level": {},
}


# --- what may be read ---------------------------------------------------------------------


def relative(path: Path, root: Path | None = None) -> Path:
    return Path(os.path.relpath(Path(path).resolve(), (root or ROOT).resolve()))


def require_accepted(run: Path, root: Path | None = None) -> None:
    """Refuses a recorded run the claim gate refuses at HEAD as a source of anything drawn.

    The test is the gate's own: the run was recorded on a clean tree and every
    file of this repository its command executes is pinned and unchanged.
    """
    root = root or ROOT
    name = relative(run, root).as_posix()
    if not (root / name / "manifest.json").exists():
        raise SystemExit(f"{name}: no manifest.json; not a recorded run")
    errors = cc.check_code(name, name, root)
    if errors:
        raise SystemExit(f"{name}: the claim gate refuses it, so nothing is read from it: "
                         + "; ".join(e.split(": ", 1)[1] for e in errors))


def check_pin(path: Path, hashes: dict[str, str], root: Path | None = None) -> None:
    """Reads a build-record file only at the value a recording the gate accepts pins for it."""
    root = root or ROOT
    name = relative(path, root).as_posix()
    run = PINS.get(name)
    if run is None:
        raise SystemExit(f"{name}: no recording the claim gate accepts is named as pinning it")
    require_accepted(Path(root / run), root)
    manifest = json.loads((root / run / "manifest.json").read_text(encoding="utf-8"))
    pinned = (manifest.get("input_sha256") or {}).get(name)
    found = rr.file_hash(root / name)
    if pinned != found:
        raise SystemExit(f"{name}: hashes to {found}, not the {pinned} {run} pins")
    hashes[name] = found


def posix(path) -> str:
    return relative(Path(path)).as_posix()


def check_named(kind: str, run: Path) -> None:
    """Refuses a run other than the one the log entry names for this role."""
    if posix(run) != posix(ROOT / NAMED[kind]):
        raise SystemExit(f"{posix(run)} is not {NAMED[kind]}, the recording the log entry names")


def check_sources(kind: str, dirs: list[Path], hashes: dict[str, str]) -> None:
    """The score directories drawn are the sources the named grid recording lists, in order.

    Only the list of paths is read from that recording, whatever the gate's
    verdict on it; none of its statistics is.
    """
    listed = json.loads(hashed(ROOT / NAMED[kind] / "intervals.json", hashes).read_text(
        encoding="utf-8"))["sources"]
    if [posix(d) for d in dirs] != [posix(ROOT / s) for s in listed]:
        raise SystemExit(f"the directories named are not the sources {NAMED[kind]} lists")


def hashed(path: Path, hashes: dict[str, str]) -> Path:
    hashes[relative(path).as_posix()] = rr.file_hash(path)
    return path


def check_expected(found: dict, expected: dict | None) -> None:
    if not expected:
        return
    wrong = {k: (found.get(k), v) for k, v in expected.items() if found.get(k) != v}
    if wrong:
        raise SystemExit("the inputs are not the ones the log entry fixes: " + "; ".join(
            f"{k} is {got!r}, the entry says {want!r}" for k, (got, want) in wrong.items()))


def write_outputs(out_dir: Path, summary: dict, hashes: dict[str, str]) -> None:
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n",
                                          encoding="utf-8")
    (out_dir / "inputs.json").write_text(json.dumps(dict(sorted(hashes.items())), indent=2)
                                         + "\n", encoding="utf-8")


# --- reading a build's score directories ---------------------------------------------------


def load_build(dirs: list[Path], hashes: dict[str, str], draws: str = "first",
               cohorts: list[str] | None = None, extra: list[str] | None = None
               ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One build's scores and references from its directories, the first draw or all three.

    `extra` names further columns of the score files, read from the files that
    hold them. A cell held by two directories, or rows of two builds, stop the run.
    """
    filters = [("cohort", "in", list(cohorts))] if cohorts else None
    frames, references = [], []
    for d in dirs:
        path = hashed(d / "scores.parquet", hashes)
        names = pq.read_schema(path).names
        columns = [*SCORE_COLUMNS, *[c for c in (extra or []) if c in names]]
        frames.append(pd.read_parquet(path, columns=columns, filters=filters))
        references.append(pd.read_parquet(hashed(d / "reference.parquet", hashes),
                                          columns=REFERENCE_COLUMNS))
    scores = pd.concat(frames, ignore_index=True)
    reference = pd.concat(references, ignore_index=True)
    if draws == "first":
        scores = scores[scores["context_seed"].isna() | (scores["context_seed"] == FIRST_DRAW)]
        reference = reference[reference["context_seed"].isna()
                              | (reference["context_seed"] == FIRST_DRAW)]
    if scores["build_id"].nunique() != 1 or reference["build_id"].nunique() != 1:
        raise SystemExit("one build per figure: " + ", ".join(d.as_posix() for d in dirs))
    if scores[["model", "context_seed", "cohort", "row"]].duplicated().any():
        raise SystemExit("the same cell is scored in more than one directory")
    models = set(scores["model"].unique())
    if models != set(COLUMNS):
        raise SystemExit(f"the directories hold {sorted(models)}, not {list(COLUMNS)}")
    return scores.reset_index(drop=True), reference.reset_index(drop=True)


def seed_of(model: str) -> int | None:
    return None if model in FIXED else FIRST_DRAW


def cell(frame: pd.DataFrame, model: str, seed: int | None) -> pd.DataFrame:
    mask = frame["model"] == model
    mask &= frame["context_seed"].isna() if seed is None else frame["context_seed"] == seed
    return frame[mask]


def floors_of(cells_csv: Path, build: str, cohorts) -> dict[str, bool]:
    """Whether each cohort clears the floors, the build record's verdict."""
    return bi.floor_verdicts(bi.read_floors(cells_csv), cells_csv, build, list(cohorts))


# --- axes ------------------------------------------------------------------------------------


def decade_ticks(lo: float, hi: float) -> list[float]:
    """1, 2 and 5 of every decade inside [lo, hi]; every integer 1 to 9 where that is under three.

    A range narrower than a decade can hold one of the 1, 2, 5 ticks or none,
    so there each integer multiple of the decade is labelled instead (EXP-005
    log, 2026-09-25, later).
    """
    def inside(mantissas) -> list[float]:
        out = []
        for exponent in range(math.floor(math.log10(lo)), math.ceil(math.log10(hi)) + 1):
            for mantissa in mantissas:
                value = mantissa * 10.0 ** exponent
                if lo <= value <= hi:
                    out.append(value)
        return out

    ticks = inside((1, 2, 5))
    return ticks if len(ticks) >= 3 else inside(range(1, 10))


def plain(value: float) -> str:
    """A probability in plain decimals: 0.0002, 0.05, 1."""
    text = f"{value:.8f}".rstrip("0").rstrip(".")
    return text or "0"


def log_axes(ax, lo: float, hi: float, x: bool = True, y: bool = True) -> None:
    """A log axis labelled at 1, 2 and 5 of each decade, minor ticks unlabelled."""
    ticks = decade_ticks(lo, hi)
    for use, axis, setter in ((x, ax.xaxis, ax.set_xlim), (y, ax.yaxis, ax.set_ylim)):
        if not use:
            continue
        setter(lo, hi)
        axis.set_major_locator(FixedLocator(ticks))
        axis.set_major_formatter(matplotlib.ticker.FixedFormatter([plain(t) for t in ticks]))
        axis.set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10) * 0.1, numticks=50))
        axis.set_minor_formatter(NullFormatter())


def margin_range(values, margin: float) -> tuple[float, float]:
    positive = np.asarray([v for v in values if np.isfinite(v) and v > 0], dtype=float)
    if positive.size == 0:
        raise SystemExit("nothing positive to place on a log axis")
    return float(positive.min() / margin), float(positive.max() * margin)


# --- the ridge -------------------------------------------------------------------------------


def ridge_range(arrays: list[np.ndarray]) -> tuple[float, float]:
    """The x range in log10: the percentiles of every row drawn, out to the nearest bin edge."""
    logs = np.concatenate([log10_of(a) for a in arrays])
    lo, hi = np.percentile(logs, RANGE_PERCENTILES)
    return (math.floor(round(lo / BIN_WIDTH, 9)) * BIN_WIDTH,
            math.ceil(round(hi / BIN_WIDTH, 9)) * BIN_WIDTH)


def log10_of(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if (values <= 0).any() or not np.isfinite(values).all():
        raise SystemExit("a probability of zero or below has no place on the axis; no row is "
                         "dropped, so the figure is not drawn")
    return np.log10(values)


def density(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """The histogram density of log10 of the values; one beyond the range is in the end bin."""
    x = np.clip(log10_of(values), edges[0], edges[-1])
    counts, _ = np.histogram(x, bins=edges)
    return counts / (values.size * BIN_WIDTH)


def ridge_ticks(lo: float, hi: float, inches: float) -> list[float]:
    """The labelled x ticks of a ridge panel `inches` wide, from log10 `lo` to `hi`.

    The ticks of `decade_ticks`, where each stands clear of the next by more
    than the height of its rotated label at print size; the decades alone,
    with the rest as unlabelled minor ticks, where they do not.
    """
    ticks = decade_ticks(10 ** lo, 10 ** hi)
    gaps = np.diff(np.log10(ticks)) * inches / (hi - lo)
    if gaps.size and float(gaps.min()) < pt(1.4 * TICK_PT):
        ticks = [t for t in ticks if abs(math.log10(t) - round(math.log10(t))) < 1e-9]
    return ticks


def draw_ridge(columns: list[dict], rows: list[tuple[str, bool]], edges: np.ndarray,
               out: Path, title: str, notes: list[str], reference_row: int | None = None,
               label_chars: int = 0) -> dict:
    """One panel per model, one row per cohort, youngest at the top, on one vertical scale.

    `columns` holds per model its `values` per row, in the order of `rows`,
    its `reference` scores and a `subtitle`. `rows` holds each cohort's label
    and whether it is under the floors. The row at `reference_row`, when
    given, is the reference itself and is drawn as its outline alone. A
    ridge of up to sixteen rows sets its panels four to a line; a taller one
    keeps them in one line, the height its row labels need. `label_chars`
    reserves a left margin for labels of at least that many characters, so
    that two ridges drawn on one x range draw it at one panel width.
    """
    n = len(rows)
    dens = [[density(v, edges) for v in c["values"]] for c in columns]
    refs = [density(c["reference"], edges) for c in columns]
    tallest = max(max(float(d.max()) for d in col) for col in dens)
    tallest = max(tallest, max(float(r.max()) for r in refs))
    scale = RIDGE_REACH / tallest

    per_line = 4 if n <= 16 else len(columns)
    lines = math.ceil(len(columns) / per_line)
    longest = max(label_chars, max(len(label) for label, _ in rows))
    left = 0.12 + pt(TICK_PT * 0.58 * longest)
    gap = 0.08
    panel_w = (PRINT_WIDTH - left - 0.08 - gap * (per_line - 1)) / per_line
    heads = [wrap(f"{bi.describe(c['model'])}\n{c['subtitle']}", panel_w) for c in columns]
    head_h = pt(TEXT_PT * 1.25 * max(lines_in(h) for h in heads)) + 0.06
    title_text = wrap_title(title)
    top = pt(TITLE_PT * 1.3 * lines_in(title_text)) + 0.12
    ticks_h = pt(TICK_PT * 0.62 * 6) + 0.1
    note_text = wrap("\n".join(notes), PRINT_WIDTH - 0.2)
    legend_h = pt(TEXT_PT * 1.35 * 2) + 0.06
    bottom = pt(TEXT_PT * 1.3) + 0.08 + legend_h + pt(TEXT_PT * 1.25 * lines_in(note_text)) + 0.12
    fixed = top + lines * (head_h + ticks_h) + bottom
    wanted = lines * (0.16 * (n + RIDGE_REACH) + 0.2)
    panel_h = min(wanted, PRINT_HEIGHT - fixed) / lines
    height = fixed + lines * panel_h

    fig = plt.figure(figsize=(PRINT_WIDTH, height))
    axes = []
    for k, (col, rows_d, ref_d, head) in enumerate(zip(columns, dens, refs, heads, strict=True)):
        line, place = divmod(k, per_line)
        y0 = height - top - (line + 1) * (head_h + panel_h) - line * ticks_h
        ax = fig.add_axes(((left + place * (panel_w + gap)) / PRINT_WIDTH, y0 / height,
                           panel_w / PRINT_WIDTH, panel_h / height),
                          sharey=axes[0] if axes else None)
        axes.append(ax)
        colour = bi.model_colour(col["model"])
        deciles = np.log10(mt.psi_edges(col["reference"]))
        for i, ((label, under), d) in enumerate(zip(rows, rows_d, strict=True)):
            base = n - 1 - i
            ax.stairs(base + ref_d * scale, edges, baseline=base, color=REFERENCE_COLOUR,
                      linewidth=0.45, zorder=2 + 2 * i)
            if i != reference_row:
                ax.stairs(base + d * scale, edges, baseline=base, fill=True, color=colour,
                          alpha=0.22 if under else 0.6, linewidth=0, zorder=3 + 2 * i)
            ax.vlines(deciles, base, base + 0.3, colors="black", linewidth=0.4, zorder=3 * n)
        ax.set_xlim(edges[0], edges[-1])
        ticks = ridge_ticks(edges[0], edges[-1], panel_w)
        ax.set_xticks(np.log10(ticks))
        ax.set_xticklabels([plain(t) for t in ticks], rotation=90, fontsize=TICK_PT)
        minor = [m * 10.0 ** e for e in range(math.floor(edges[0]), math.ceil(edges[-1]) + 1)
                 for m in range(1, 10)]
        ax.set_xticks([math.log10(m) for m in minor
                       if edges[0] <= math.log10(m) <= edges[-1]], minor=True)
        ax.set_title(head, fontsize=TEXT_PT)
        ax.grid(axis="x", alpha=0.25)
        ax.tick_params(axis="y", length=0)
        if place == 0:
            ax.set_yticks(range(n))
            ax.set_yticklabels([label for label, _ in reversed(rows)], fontsize=TICK_PT)
            for tick, (label, under) in zip(ax.get_yticklabels(), reversed(rows), strict=True):
                if under:
                    tick.set_fontstyle("italic")
                    tick.set_color("#777777")
        else:
            ax.tick_params(axis="y", labelleft=False)
    axes[0].set_ylim(-0.4, n - 1 + RIDGE_REACH + 0.2)
    last_y = height - top - lines * (head_h + panel_h) - (lines - 1) * ticks_h
    fig.text((left + (PRINT_WIDTH - 0.08)) / 2 / PRINT_WIDTH,
             (last_y - ticks_h - 0.02) / height, "predicted probability, log axis",
             ha="center", va="top", fontsize=TEXT_PT)
    handles = [Patch(color="#777777", alpha=0.6, label="a cohort's scored rows")]
    if any(under for _, under in rows):
        handles.append(Patch(color="#777777", alpha=0.22, label=UNDER))
    handles += [Line2D([], [], color=REFERENCE_COLOUR, linewidth=0.7, label="the reference"),
                Line2D([], [], color="black", linewidth=0.7, marker="|", linestyle="none",
                       markersize=6, label="the reference's nine interior deciles, the PSI bins")]
    legend_top = last_y - ticks_h - pt(TEXT_PT * 1.3) - 0.08
    fig.legend(handles=handles, loc="upper center", ncol=2, frameon=False, fontsize=TEXT_PT,
               bbox_to_anchor=(0.5, legend_top / height))
    fig.suptitle(title_text, fontsize=TITLE_PT, y=1 - 0.06 / height, va="top")
    fig.text(0.5, 0.06 / height, note_text, ha="center", va="bottom", fontsize=TEXT_PT)
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return {"rows": n, "columns": len(columns), "x_range_log10": [float(edges[0]),
                                                                    float(edges[-1])]}


RIDGE_NOTES = [
    ("Histogram density of log10 of the predicted probability in bins 0.05 wide; a probability "
     "beyond the axis is counted in the end bin. Every row is on one vertical scale."),
    ("A seeded model is drawn on its first context draw, 20260911, against that draw's own "
     "reference. A ridge row is a distribution and carries no interval."),
]


def ridge_columns(scores: pd.DataFrame, reference: pd.DataFrame, order: list[str],
                  found: dict) -> list[dict]:
    """Per model its first-draw values on each cohort of `order` and its reference."""
    columns = []
    for model in COLUMNS:
        seed = seed_of(model)
        own = cell(scores, model, seed)
        ref = cell(reference, model, seed)["pd"].to_numpy(dtype=float)
        values = []
        for cohort in order:
            v = own.loc[own["cohort"] == cohort, "pd"].to_numpy(dtype=float)
            if v.size == 0:
                raise SystemExit(f"{model}: no scores on {cohort}")
            values.append(v)
        key = "training_rows" if seed is None else "draw_rows"
        if found.setdefault(key, ref.size) != ref.size:
            raise SystemExit(f"{model}: a reference of {ref.size:,} rows, where another has "
                             f"{found[key]:,}")
        what = "the training rows" if seed is None else f"context draw {seed}"
        columns.append({"model": model, "values": values, "reference": ref,
                        "subtitle": f"reference: {what},\n{ref.size:,} rows"})
    return columns


def cohorts_by_age(scores: pd.DataFrame) -> list[str]:
    ages = scores.groupby("cohort")["age_quarters"].agg(["min", "max"])
    if (ages["min"] != ages["max"]).any():
        raise SystemExit("a cohort at more than one age")
    return list(ages.sort_values("min").index.astype(str))


def cmd_lc_ridge(args, expected: dict | None) -> dict:
    hashes: dict[str, str] = {}
    require_accepted(args.psi_run)
    check_named("lc-grid", args.psi_run)
    check_sources("lc-grid", args.dirs, hashes)
    scores, reference = load_build(args.dirs, hashes)
    build = str(scores["build_id"].iloc[0])
    order = cohorts_by_age(scores)
    found = {"build": build, "cohorts": len(order)}
    per = scores.groupby(["model", "context_seed", "cohort"], dropna=False).size()
    found["rows_per_cohort"] = sorted({int(v) for v in per})
    first = cell(scores, "gbm", None)
    found["under_floors"] = [c for c in order
                             if bi.under_floors(first.loc[first["cohort"] == c, "outcome"])]
    columns = ridge_columns(scores, reference, order, found)
    check_expected(found, expected)
    arrays = [v for c in columns for v in c["values"]] + [c["reference"] for c in columns]
    lo, hi = ridge_range(arrays)
    edges = np.round(np.arange(lo, hi + BIN_WIDTH / 2, BIN_WIDTH), 10)
    notes = [*RIDGE_NOTES, (
        "The reference is the one H3 reads: the training rows for a fitted model, the context "
        "draw for GBM-50k and the foundation models. Each cell's PSI and critical value: "
        f"metrics.csv of {relative(args.psi_run).as_posix()}.")]
    drawn = draw_ridge(columns, [(c, False) for c in order], edges, args.out_dir / "ridge.png",
                       f"{build}: the score distribution of every model at every cohort, "
                       "against its reference", notes)
    write_outputs(args.out_dir, {"figure": "ridge.png", **found, **drawn}, hashes)
    return found


def cmd_fm_ridge(args, expected: dict | None) -> dict:
    hashes: dict[str, str] = {}
    check_pin(args.cells, hashes)
    check_sources("fm-grid", args.dirs, hashes)
    scores, reference = load_build(args.dirs, hashes)
    build = str(scores["build_id"].iloc[0])
    order = cohorts_by_age(scores)
    floor = floors_of(args.cells, build, order)
    found = {"build": build, "cohorts": len(order), "first_cohort": order[0],
             "under_floors": [c for c in order if not floor[c]]}
    training = ridge_columns(scores, reference, order, found)
    check_expected(found, expected)
    first = [{**c, "reference": c["values"][0],
              "subtitle": f"reference: its scores\non {order[0]}"} for c in training]
    arrays = [v for c in training for v in c["values"]] + [c["reference"] for c in training]
    lo, hi = ridge_range(arrays)
    edges = np.round(np.arange(lo, hi + BIN_WIDTH / 2, BIN_WIDTH), 10)
    rows = [(c, not floor[c]) for c in order]
    notes = [*RIDGE_NOTES, ("No PSI is printed: this build's per-cell values are held only by a "
                            "recording the claim gate refuses.")]
    first_rows = [(f"{order[0]}, the reference", rows[0][1]), *rows[1:]]
    label_chars = max(len(label) for label, _ in rows + first_rows)
    drawn = draw_ridge(training, rows, edges, args.out_dir / "ridge-training.png",
                       f"{build}: the score distribution of every model at every cohort, against "
                       "the training reference H3 reads", notes, label_chars=label_chars)
    draw_ridge(first, first_rows, edges, args.out_dir / "ridge-first-cohort.png",
               f"{build}: the same ridge against the first scored cohort, {order[0]}, bins at "
               "its deciles", [*notes, (f"The row of {order[0]} is the reference and is drawn "
                                        "as its outline alone.")], reference_row=0,
               label_chars=label_chars)
    write_outputs(args.out_dir, {"figures": ["ridge-training.png", "ridge-first-cohort.png"],
                                 **found, **drawn}, hashes)
    return found


# --- reliability -----------------------------------------------------------------------------


def join_reported(scores: pd.DataFrame) -> pd.DataFrame:
    """The reported reading on every row, taken from the rows that carry it by (cohort, row).

    A row that does not join, or whose primary label differs from the holder's,
    stops the run.
    """
    held = scores[scores[REPORTED].notna()] if REPORTED in scores else scores.iloc[0:0]
    if held.empty:
        raise SystemExit(f"no score file of the build carries {REPORTED}")
    label = held[["cohort", "row", "outcome", REPORTED]].drop_duplicates()
    if label[["cohort", "row"]].duplicated().any():
        raise SystemExit(f"a row carries two readings of {REPORTED}")
    joined = scores.drop(columns=[REPORTED]).merge(label, on=["cohort", "row"], how="left",
                                                  suffixes=("", "_held"), validate="many_to_one")
    if joined[REPORTED].isna().any():
        raise SystemExit(f"rows no classical score file scores, so {REPORTED} cannot be joined")
    if not np.array_equal(joined["outcome"].to_numpy(), joined["outcome_held"].to_numpy()):
        raise SystemExit("the primary label differs between the score files on a joined row")
    return joined.drop(columns=["outcome_held"])


def curves(frame: pd.DataFrame, model: str, cohort: str, outcome: str = "outcome"
           ) -> list[mt.Reliability]:
    """The reliability curve of every draw of a model on a cohort, the first draw first."""
    own = frame[(frame["model"] == model) & (frame["cohort"] == cohort)]
    out = []
    seeds = [None] if model in FIXED else sorted(int(s) for s in own["context_seed"].unique())
    for seed in seeds:
        rows = cell(own, model, seed).sort_values("row")
        out.append(mt.reliability(rows[outcome].to_numpy(), rows["pd"].to_numpy(dtype=float)))
    return out


def percent(rate: float) -> str:
    """A rate in percent to three significant figures, as the log entry states them: 0.297%."""
    return f"{100 * rate:#.3g}%"


def curve_values(curve: mt.Reliability) -> list[float]:
    return [*curve.mean_score, *curve.observed, *curve.lo, *curve.hi]


def draw_curve(ax, curve: mt.Reliability, colour: str, style: str, first: bool, low: float,
               open_marker: bool, label: str | None) -> None:
    x = np.array(curve.mean_score)
    y = np.array(curve.observed)
    lo = np.array(curve.lo)
    hi = np.array(curve.hi)
    zero = y == 0
    face = "white" if open_marker else colour
    if first:
        yy = np.where(zero, np.nan, y)
        ax.errorbar(x, yy, yerr=[np.where(zero, 0, y - lo), np.where(zero, 0, hi - y)],
                    color=colour, linestyle=style, marker="o", markersize=2.4,
                    markerfacecolor=face, markeredgewidth=0.6, capsize=1.2, elinewidth=0.5,
                    capthick=0.5, linewidth=0.8, label=label)
        if zero.any():
            ax.vlines(x[zero], low, hi[zero], colors=colour, linewidth=0.5)
            ax.scatter(x[zero], np.full(zero.sum(), low), marker="v", s=10, facecolors="white",
                       edgecolors=colour, linewidths=0.6, zorder=4, clip_on=False)
    else:
        ax.plot(x, np.where(zero, np.nan, y), color=colour, linestyle=style, linewidth=0.5,
                alpha=0.45)


def cmd_reliability(args, expected: dict | None) -> dict:
    hashes: dict[str, str] = {}
    check_pin(args.cells, hashes)
    wanted = [*RELIABILITY_COHORTS, BOTH_READINGS]
    check_sources("fm-grid", args.dirs, hashes)
    scores, _ = load_build(args.dirs, hashes, draws="all", cohorts=wanted, extra=[REPORTED])
    build = str(scores["build_id"].iloc[0])
    scores = join_reported(scores)
    floor = floors_of(args.cells, build, wanted)
    record = pd.read_csv(args.cells, dtype={"build_id": str, "cohort": str})
    record = record[record["build_id"] == build].set_index("cohort")
    base = cell(scores, "scorecard", None)
    found: dict = {"build": build}
    for cohort in ("2003H1", BOTH_READINGS):
        rows = base[base["cohort"] == cohort]
        found[f"rows_{cohort}"] = len(rows)
        found[f"defaults_{cohort}"] = int(rows["outcome"].sum())
    found["reported_2019H1"] = int(base.loc[base["cohort"] == BOTH_READINGS, REPORTED].sum())
    found["record_labelled_reported_2019H1"] = int(record.loc[BOTH_READINGS, "labelled_reported"])
    found["record_reported_2019H1"] = int(record.loc[BOTH_READINGS, "defaults_reported"])
    rates = {c: float(record.loc[c, "rate"]) for c in RELIABILITY_COHORTS}
    above = [rates[c] for c in RELIABILITY_COHORTS if floor[c]]
    found["span"] = round(max(rates.values()) / min(rates.values()), 1)
    found["span_above_floors"] = round(max(above) / min(above), 1)
    check_expected(found, expected)

    four = {m: {c: curves(scores, m, c) for c in RELIABILITY_COHORTS} for m in COLUMNS}
    both = {m: {"outcome": curves(scores, m, BOTH_READINGS),
                REPORTED: curves(scores, m, BOTH_READINGS, REPORTED)} for m in COLUMNS}
    values = [v for m in COLUMNS for group in (four[m], both[m]) for cs in group.values()
              for c in cs for v in curve_values(c)]
    low, high = margin_range(values, RELIABILITY_MARGIN)
    under = [c for c in RELIABILITY_COHORTS if not floor[c]]
    span_note = (f"The four cohorts span {found['span']}x in realised rate at 24 months; the low "
                 f"end, {', '.join(under)}, is under the floors "
                 f"({int(record.loc[under[0], 'defaults'])} defaults, about "
                 f"{int(record.loc[under[0], 'defaults']) // 10} to a bin) and is read through "
                 f"its intervals; the three above the floors span {found['span_above_floors']}x."
                 if under else f"The four cohorts span {found['span']}x in realised rate.")

    def panels(title: str, series, legend: list, notes: list[str], out: Path) -> None:
        # Three square panels to a line, the legend and the notes in the two slots the
        # seven panels leave on the third line.
        per_line, left, gap, right = 3, 0.78, 0.45, 0.06
        side = (PRINT_WIDTH - left - right - gap * (per_line - 1)) / per_line
        heads = [wrap(bi.describe(m) + ("" if m in FIXED else
                                        f"\ndraw {FIRST_DRAW} with intervals; thin: the other "
                                        "two draws"), side) for m in COLUMNS]
        head_h = pt(TEXT_PT * 1.25 * max(lines_in(h) for h in heads)) + 0.05
        foot_h = pt(TICK_PT * 0.62 * 7) + pt(TEXT_PT * 1.25 * 2) + 0.1
        title_text = wrap_title(title)
        top = pt(TITLE_PT * 1.3 * lines_in(title_text)) + 0.1
        lines = math.ceil((len(COLUMNS) + 1) / per_line)
        if top + lines * (head_h + side + foot_h) > PRINT_HEIGHT:
            # Square panels that fit the page, the width they give up spread between them.
            side = (PRINT_HEIGHT - top) / lines - head_h - foot_h
            gap = (PRINT_WIDTH - left - right - per_line * side) / (per_line - 1)
        height = top + lines * (head_h + side + foot_h)
        fig = plt.figure(figsize=(PRINT_WIDTH, height))

        def slot(k: int, span: int = 1):
            line, place = divmod(k, per_line)
            y0 = height - top - line * (head_h + side + foot_h) - head_h - side
            return fig.add_axes(((left + place * (side + gap)) / PRINT_WIDTH, y0 / height,
                                 (span * side + (span - 1) * gap) / PRINT_WIDTH,
                                 side / height))

        for k, model in enumerate(COLUMNS):
            ax = slot(k)
            for colour, style, cs, open_marker, label in series(model):
                for j, c in enumerate(cs):
                    draw_curve(ax, c, colour, style, j == 0, low, open_marker,
                               label if j == 0 else None)
            ax.plot([low, high], [low, high], color="black", linewidth=0.6, linestyle=":")
            ax.set_xscale("log")
            ax.set_yscale("log")
            log_axes(ax, low, high)
            ax.tick_params(axis="x", labelrotation=90, labelsize=TICK_PT)
            ax.tick_params(axis="y", labelsize=TICK_PT)
            ax.set_aspect("equal")
            ax.grid(alpha=0.3, which="major")
            ax.set_title(heads[k], fontsize=TEXT_PT)
            ax.set_xlabel(wrap("mean predicted probability in the bin", side), fontsize=TEXT_PT)
            if k % per_line == 0:
                ax.set_ylabel(wrap("observed default rate, 95% Clopper-Pearson interval",
                                   side + 0.4), fontsize=TEXT_PT)
        spare = slot(len(COLUMNS), per_line - len(COLUMNS) % per_line)
        spare.axis("off")
        room = per_line - len(COLUMNS) % per_line
        width = room * side + (room - 1) * gap
        for handle in legend:
            handle.set_label(wrap(" ".join(handle.get_label().split()), width - 0.35))
        spare.legend(handles=legend, loc="upper left", frameon=False, fontsize=TEXT_PT,
                     bbox_to_anchor=(0.0, 1.0 + (head_h - 0.05) / side), borderaxespad=0)
        entries = sum(lines_in(h.get_label()) for h in legend)
        spare.text(0.0, 1.0 + (head_h - 0.05) / side - pt(TEXT_PT * 1.45 * entries + 8) / side,
                   "\n\n".join(wrap(n, width) for n in notes), ha="left", va="top",
                   fontsize=TEXT_PT, transform=spare.transAxes)
        fig.suptitle(title_text, fontsize=TITLE_PT, y=1 - 0.05 / height, va="top")
        fig.savefig(out, dpi=DPI)
        plt.close(fig)

    marker_note = "The dotted line is calibration."
    zero_bin = Line2D([], [], color="#555555", marker="v", linestyle="none", markersize=4,
                      markerfacecolor="white",
                      label="a bin with no default: on the lower edge at its mean probability, "
                            "with its upper bound")
    legend = [Line2D([], [], color=COHORT_COLOUR[c], marker="o", markersize=3.5,
                     markerfacecolor="white" if not floor[c] else COHORT_COLOUR[c],
                     label=f"{c}, {percent(rates[c])}" + (f" ({UNDER})" if not floor[c] else ""))
              for c in RELIABILITY_COHORTS] + [zero_bin]
    panels(f"{build}: reliability at four cohorts on one log axis, ten quantile bins of each "
           "cohort's scores, 24-month primary label",
           lambda m: [(COHORT_COLOUR[c], "-", four[m][c], not floor[c], c)
                      for c in RELIABILITY_COHORTS],
           legend, [span_note, marker_note], args.out_dir / "reliability.png")
    readings = [Line2D([], [], color="#555555", linestyle="-", marker="o", markersize=3.5,
                       label=f"primary label, relief months set aside "
                             f"({found['defaults_2019H1']:,} defaults)"),
                Line2D([], [], color="#555555", linestyle="--", marker="o", markersize=3.5,
                       label=f"reported reading ({found['reported_2019H1']:,} defaults)"),
                zero_bin]
    panels(f"{build}: reliability on {BOTH_READINGS} under both label readings, the same bins "
           f"({found['rows_2019H1']:,} scored rows) and the same axis",
           lambda m: [(bi.model_colour(m), "-", both[m]["outcome"], False, None),
                      (bi.model_colour(m), "--", both[m][REPORTED], False, None)],
           readings, [marker_note, ("The bins read the score and not the label; only the "
                                    "observed rate moves.")],
           args.out_dir / "reliability-2019h1.png")
    write_outputs(args.out_dir, {"figures": ["reliability.png", "reliability-2019h1.png"],
                                 "axis": [low, high], **found}, hashes)
    return found


# --- the relief share ------------------------------------------------------------------------


def half_of(quarter: str) -> str:
    return f"{quarter[:4]}H{1 if quarter[-1] in '12' else 2}"


def quarters_between(first: str, last: str) -> list[str]:
    out = []
    year, q = int(first[:4]), int(first[-1])
    while f"{year}Q{q}" <= last:
        out.append(f"{year}Q{q}")
        year, q = (year, q + 1) if q < 4 else (year + 1, 1)
    return out


def check_regimes(regimes: dict[str, list[str]]) -> None:
    """The build record's regimes against the Setting's definition on half-years."""
    for name, first, last, _ in REGIMES:
        held = regimes.get(name, [])
        wrong = [c for c in held if (first and c < first) or (last and c > last)]
        if not held or wrong:
            raise SystemExit(f"the build record's {name} regime is not the Setting's: "
                             f"{wrong or 'empty'}")


def regime_of_half(half: str) -> str:
    for name, first, last, _ in REGIMES:
        if (first is None or half >= first) and (last is None or half <= last):
            return name
    raise SystemExit(f"{half} falls in no regime")


def cmd_relief_share(args, expected: dict | None) -> dict:
    hashes: dict[str, str] = {}
    require_accepted(args.structure)
    require_accepted(args.sensitivity)
    check_named("structure", args.structure)
    check_named("sensitivity", args.sensitivity)
    check_pin(args.cells, hashes)
    check_pin(args.builds, hashes)
    summary = json.loads(hashed(args.structure / "summary.json", hashes).read_text(
        encoding="utf-8"))
    by_quarter = summary["windows"]["24"]["defaults_under_relief_by_quarter"]
    builds = json.loads(args.builds.read_text(encoding="utf-8"))
    check_regimes(builds["regimes"])
    record = pd.read_csv(args.cells, dtype={"build_id": str, "cohort": str, "arm": str})
    halves = sorted(record["cohort"].unique())
    quarters = quarters_between(f"{halves[0][:4]}Q{1 if halves[0][-1] == '1' else 3}",
                                f"{halves[-1][:4]}Q{2 if halves[-1][-1] == '1' else 4}")
    share = [by_quarter[q]["share_under_relief"] if q in by_quarter else None for q in quarters]
    if any(s is None for s in share):
        raise SystemExit("a quarter of the grid's span has no recorded value")
    share = np.asarray(share, dtype=float)
    per_cohort = record.groupby("cohort").first()
    floor = per_cohort["floor"].astype(str).eq("True")
    counts = (record[record["floor"].astype(str).eq("True")]
              .groupby(["cohort", "arm"]).size().unstack(fill_value=0)
              .reindex(index=halves, columns=["E", "R"], fill_value=0))
    q = pd.DataFrame({k: by_quarter[k] for k in quarters}).T.astype(float)
    q["half"] = [half_of(k) for k in q.index]
    summed = q.groupby("half")[["defaults", "defaults_outside_relief"]].sum()
    structure_half = 1 - summed["defaults_outside_relief"] / summed["defaults"]
    grid_half = 1 - per_cohort["defaults"] / per_cohort["defaults_reported"]
    gap = (structure_half - grid_half).abs()
    nonzero = [k for k, s in zip(quarters, share, strict=True) if s > 0]
    found = {"quarters": len(quarters), "criterion_cells": int(counts.to_numpy().sum()),
             "criterion_E": int(counts["E"].sum()), "criterion_R": int(counts["R"].sum()),
             "max_gap": round(float(gap.max()), 4), "max_gap_half": str(gap.idxmax()),
             "first_nonzero": nonzero[0] if nonzero else None}
    check_expected(found, expected)

    # In inches: the title, the regime names, the band of labels of the half-years under the
    # floors above the share, the share, the strip, the year labels and the caption.
    title_text = wrap_title("EXP-003's relief share per quarter at 24 months, the criterion cells of "
                      "the grid and the label regimes")
    caption = wrap(" ".join([
        (f"Per quarter as recorded in {relative(args.structure).as_posix()}/summary.json. The "
         "grid's cells also leave out the seasoned acquisitions and the loans with a gap in their "
         "performance record;"),
        (f"summed to half-years the two shares differ by at most {found['max_gap']} "
         f"({found['max_gap_half']}). The sensitivity reading's results: "
         f"{relative(args.sensitivity).as_posix()}.")]), PRINT_WIDTH - 0.2)
    label_band = pt(TEXT_PT * 0.5 * len(f"{halves[0]} under the floors")) + 0.1
    left, right = 0.62, 0.08
    share_h, strip_h, gap = 2.7, 0.95, 0.16
    below = pt(TICK_PT * 0.62 * 4) + 0.12 + pt(TEXT_PT * 1.25 * lines_in(caption)) + 0.1
    above = pt(TITLE_PT * 1.3 * lines_in(title_text)) + 0.12 + pt(TEXT_PT * 1.3) + label_band
    height = above + share_h + gap + strip_h + below
    fig = plt.figure(figsize=(PRINT_WIDTH, height))
    width = (PRINT_WIDTH - left - right) / PRINT_WIDTH
    top = fig.add_axes((left / PRINT_WIDTH, (below + strip_h + gap) / height, width,
                        share_h / height))
    strip = fig.add_axes((left / PRINT_WIDTH, below / height, width, strip_h / height),
                         sharex=top)
    top.tick_params(labelbottom=False)
    x = np.arange(len(quarters))
    for name, first, last, colour in REGIMES:
        inside = [i for i, k in enumerate(quarters) if regime_of_half(half_of(k)) == name]
        for ax in (top, strip):
            ax.axvspan(inside[0] - 0.5, inside[-1] + 0.5, color=colour, zorder=0, linewidth=0)
        top.text((inside[0] + inside[-1]) / 2, 1 + (label_band + 0.03) / share_h, name,
                 ha="center", va="bottom", fontsize=TEXT_PT,
                 transform=top.get_xaxis_transform())
    under_q = np.array([not floor[half_of(k)] for k in quarters])
    top.plot(x, share, color="#20303a", linewidth=0.7, zorder=2)
    top.scatter(x[~under_q], share[~under_q], color="#20303a", s=5, linewidths=0, zorder=3,
                label="a quarter of a half-year holding criterion cells")
    top.scatter(x[under_q], share[under_q], facecolors="white", edgecolors="#20303a", s=7,
                linewidths=0.6, zorder=3, label=f"a quarter of a half-year {UNDER}")
    for half in halves:
        if not floor[half]:
            at = [i for i, k in enumerate(quarters) if half_of(k) == half]
            top.text(np.mean(at), 1 + 0.03 / share_h, f"{half} under the floors", ha="center",
                     va="bottom", fontsize=TEXT_PT, rotation=90,
                     transform=top.get_xaxis_transform())
    top.set_ylim(0, 1)
    top.set_ylabel("one minus the set-aside defaults\nover the reported defaults, 24 months",
                   fontsize=TEXT_PT)
    top.grid(axis="y", alpha=0.3)
    top.legend(frameon=False, fontsize=TEXT_PT, loc="upper left")
    centre = np.array([np.mean([i for i, k in enumerate(quarters) if half_of(k) == h])
                       for h in halves])
    strip.bar(centre, counts["E"], width=1.8, color=isl.ARM_COLOUR["E"], label="expanding arm")
    strip.bar(centre, counts["R"], width=1.8, bottom=counts["E"], color=isl.ARM_COLOUR["R"],
              label="rolling arm")
    strip.set_ylabel("criterion cells\nper half-year", fontsize=TEXT_PT)
    strip.legend(frameon=False, fontsize=TEXT_PT, loc="upper left")
    years = [i for i, k in enumerate(quarters) if k.endswith("Q1")]
    strip.set_xticks(years)
    strip.set_xticklabels([quarters[i][:4] for i in years], rotation=90, fontsize=TICK_PT)
    strip.set_xlim(-0.5, len(quarters) - 0.5)
    fig.suptitle(title_text, fontsize=TITLE_PT, y=1 - 0.05 / height, va="top")
    fig.text(0.5, 0.06 / height, caption, ha="center", va="bottom", fontsize=TEXT_PT)
    fig.savefig(args.out_dir / "relief-share.png", dpi=DPI)
    plt.close(fig)
    write_outputs(args.out_dir, {"figure": "relief-share.png", **found}, hashes)
    return found


# --- the build grid --------------------------------------------------------------------------


def quarter_span(quarter: str, position: dict[str, int]) -> tuple[float, float]:
    """Where a quarter sits on the half-year axis: the first or second half of its half-year."""
    centre = position[half_of(quarter)]
    return (centre - 0.5, centre) if quarter[-1] in "13" else (centre, centre + 0.5)


def cmd_build_grid(args, expected: dict | None) -> dict:
    hashes: dict[str, str] = {}
    check_pin(args.builds, hashes)
    check_pin(args.cells, hashes)
    builds = json.loads(args.builds.read_text(encoding="utf-8"))
    record = pd.read_csv(args.cells, dtype={"build_id": str, "cohort": str})
    names = sorted(builds["cohorts"])
    position = {name: i for i, name in enumerate(names)}
    by_as_of: dict[str, dict[str, dict]] = {}
    for arm, entries in builds["arms"].items():
        for b in entries:
            held = sorted(record.loc[record["build_id"] == b["build_id"], "cohort"])
            if held != sorted(b["cells"]):
                raise SystemExit(f"{b['build_id']}: the build record's two files name different "
                                 "cohorts")
            by_as_of.setdefault(b["as_of"], {})[arm] = b
    skipped = {s["as_of"]: s for s in builds.get("skipped", [])}
    blind = [b["blind_rows"] for pair in by_as_of.values() for b in pair.values()]
    for pair in by_as_of.values():
        if len({b["blind_rows"] for b in pair.values()}) != 1:
            raise SystemExit("two arms of one date carry different blind rows")
    found = {"panels": len(by_as_of), "blind_rows_min": min(blind),
             "blind_rows_max": max(blind)}
    check_expected(found, expected)
    regimes = builds["regimes"]
    check_regimes(regimes)
    # A boundary sits before the earliest half-year of each regime after the first, whatever
    # order the build record lists them in.
    bounds = [position[min(regimes[name])] - 0.5 for name, *_ in REGIMES[1:]]
    columns = 3
    rows = math.ceil(len(by_as_of) / columns)
    left, right, gap = 0.55, 0.06, 0.1
    panel_w = (PRINT_WIDTH - left - right - gap * (columns - 1)) / columns
    title_text = wrap_title("The build grid: what each build was allowed to know, its blind rows, and "
                      "its training rate against every cohort it scores\ndrawn from the "
                      "build run's records after every model result")
    top = pt(TITLE_PT * 1.3 * lines_in(title_text)) + 0.12
    head_h = pt(TEXT_PT * 1.25 * 2) + 0.06
    ticks_h = pt(TICK_PT * 0.62 * 7) + 0.1
    legend_h = pt(TEXT_PT * 1.4 * 5) + 0.12
    panel_h = 1.55
    height = top + rows * (head_h + panel_h + ticks_h) + legend_h
    fig, axes = plt.subplots(rows, columns, figsize=(PRINT_WIDTH, height), sharey=True,
                             squeeze=False)
    handles: dict[str, object] = {}
    for ax, (as_of, pair) in zip(axes.flat, sorted(by_as_of.items()), strict=False):
        e = pair["E"]
        own = record[record["build_id"] == e["build_id"]].set_index("cohort").loc[e["cells"]]
        x = [position[c] for c in own.index]
        passed = own["floor"].astype(str).eq("True").to_numpy()
        spans = [quarter_span(q, position) for q in e["train_quarters"]]
        ax.axvspan(spans[0][0], spans[-1][1], color="#D8E8E6", zorder=0, linewidth=0,
                   label="expanding arm: its training quarters")
        if "R" in pair:
            r = [quarter_span(q, position) for q in pair["R"]["train_quarters"]]
            ax.axvspan(r[0][0], r[-1][1], color="#9CC3BE", zorder=0.5, linewidth=0,
                       label="rolling arm: its eight training quarters")
        last = spans[-1][1]
        as_of_q = f"{as_of[:4]}Q{(int(as_of[5:7]) - 1) // 3 + 1}"
        end = quarter_span(as_of_q, position)[1]
        ax.axvspan(last, end, facecolor="white", hatch="///", edgecolor="#9A9A9A",
                   linewidth=0, zorder=0.6, label="blind quarters, up to the as-of date")
        # Centred on the blind quarters, kept inside the panel.
        half_label = 0.36 / panel_w * len(names)
        ax.text(max((last + end) / 2, -0.5 + half_label), 0.97, f"blind\n{e['blind_rows']:,} rows", ha="center",
                va="top", fontsize=TEXT_PT, transform=ax.get_xaxis_transform(),
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
        ax.plot(x, own["rate"], color="#20303a", linewidth=0.7)
        ax.scatter([v for v, p in zip(x, passed, strict=True) if p],
                   own["rate"][passed], color="#20303a", s=5, linewidths=0, zorder=3,
                   label="a scored cohort's rate")
        ax.scatter([v for v, p in zip(x, passed, strict=True) if not p],
                   own["rate"][~passed], facecolor="white", edgecolor="#20303a", s=7,
                   linewidths=0.6, zorder=3, label=f"a scored cohort {UNDER}")
        ax.axhline(e["pool"]["rate"], color=isl.ARM_COLOUR["E"], linewidth=1.1,
                   label="training rate, expanding arm")
        if "R" in pair:
            ax.axhline(pair["R"]["pool"]["rate"], color=isl.ARM_COLOUR["R"], linewidth=0.9,
                       linestyle="--", label="training rate, rolling arm")
        elif as_of in skipped:
            ax.text(0.98, 0.97, wrap(f"no rolling build:\n{skipped[as_of]['reason']}",
                                     0.7 * panel_w), fontsize=TEXT_PT, ha="right", va="top",
                    transform=ax.transAxes)
        for bound in bounds:
            ax.axvline(bound, color="#b0392b", linewidth=0.6, linestyle=":",
                       label="a boundary of the label regimes")
        ax.set_yscale("log")
        ax.set_title(wrap(f"as of {as_of}: {e['build_id']}" + (f", {pair['R']['build_id']}"
                                                               if "R" in pair else ""), panel_w),
                     fontsize=TEXT_PT)
        step = max(1, len(names) // 12)
        ax.set_xticks(range(0, len(names), step))
        ax.set_xticklabels(names[::step], rotation=90, fontsize=TICK_PT)
        ax.set_xlim(-0.5, len(names) - 0.5)
        ax.grid(axis="y", alpha=0.25)
        for handle, text in zip(*ax.get_legend_handles_labels(), strict=True):
            handles.setdefault(text, handle)
    for ax in list(axes.flat)[len(by_as_of):]:
        ax.axis("off")
    # The top quarter of every panel is left clear of the rates for the blind rows and the
    # reason a date has no rolling build.
    low, high = axes[0][0].get_ylim()
    log_axes(axes[0][0], low, high * (high / low) ** (HEADROOM / (1 - HEADROOM)), x=False)
    for ax in axes[:, 0]:
        ax.set_ylabel(f"{builds['parameters']['window']}-month default rate", fontsize=TEXT_PT)
    fig.legend(list(handles.values()), list(handles.keys()), loc="lower center", ncol=2,
               frameon=False, fontsize=TEXT_PT, bbox_to_anchor=(0.5, 0.06 / height))
    fig.suptitle(title_text, fontsize=TITLE_PT, y=1 - 0.05 / height, va="top")
    fig.subplots_adjust(left=left / PRINT_WIDTH, right=1 - right / PRINT_WIDTH,
                        top=1 - (top + head_h) / height, bottom=(legend_h + ticks_h) / height,
                        hspace=(head_h + ticks_h) / panel_h, wspace=gap / panel_w)
    fig.savefig(args.out_dir / "build-grid.png", dpi=DPI)
    plt.close(fig)
    write_outputs(args.out_dir, {"figure": "build-grid.png", **found}, hashes)
    return found


# --- metric against age ----------------------------------------------------------------------


METRIC_FIGURES = {
    "auc": ("AUC on the cell, DeLong interval", ("scorecard", "gbm", "gbm-50k", "tabpfn",
                                                 "tabicl")),
    "cox_slope": (("Cox slope on the cell, the fit's interval; softmax temperature 1.0 dashed "
                   "in the model's colour; the dotted line is slope 1"), COLUMNS),
    "psi": (("PSI against the model's own reference, the training rows for the scorecard and "
             f"the GBM and context draw {FIRST_DRAW} for GBM-50k and the foundation models; no "
             "per-cell interval"), ("scorecard", "gbm", "gbm-50k", "tabpfn", "tabicl")),
}
COMPARED = ("value", "ci_lo", "ci_hi")
METRIC_NAME = {"auc": "AUC", "cox_slope": "Cox slope", "psi": "PSI"}
METRIC_AXIS = {"auc": "AUC on the cell", "cox_slope": "Cox slope on the cell",
               "psi": "PSI against the model's own reference"}


def half_years(quarters) -> np.ndarray:
    return np.ceil(np.asarray(quarters, dtype=float) / 2).astype(int)


def build_cells(grid: Path, cells_csv: Path, hashes: dict[str, str]) -> tuple[pd.DataFrame, dict]:
    """One build's cells, computed from the score directories its grid recording names.

    The grid recording is read for its list of sources and, for comparison
    only, for its own values; nothing drawn comes from it.
    """
    meta = json.loads(hashed(grid / "intervals.json", hashes).read_text(encoding="utf-8"))
    dirs = [Path(s) for s in meta["sources"]]
    scores, reference = load_build(dirs, hashes)
    build = str(scores["build_id"].iloc[0])
    not_estimable: list[dict] = []
    table = bi.cell_table(scores, reference, bi.reference_edges(reference), not_estimable)
    table = table[table["metric"].isin(METRIC_FIGURES)].copy()
    table["cohort"] = table["cohort"].astype(str)
    floor = floors_of(cells_csv, build, table["cohort"].unique())
    table["floor"] = table["cohort"].map(floor)
    table["age"] = half_years(table["age_quarters"])
    recorded = pd.read_csv(hashed(grid / "metrics.csv", hashes),
                           dtype={"cohort": str, "build_id": str})
    keys = ["build_id", "model", "context_seed", "cohort", "metric"]
    # The recording's cells of the three statistics on the first draw, the cells computed here.
    recorded = recorded[recorded["metric"].isin(METRIC_FIGURES)
                        & (recorded["context_seed"].isna()
                           | (recorded["context_seed"] == FIRST_DRAW))].copy()
    recorded["context_seed"] = recorded["context_seed"].astype("Int64")
    both = table.merge(recorded[[*keys, *COMPARED]], on=keys, how="outer",
                       suffixes=("", "_recorded"), validate="one_to_one", indicator=True)
    difference = {}
    for metric, part in both.groupby("metric"):
        # A cell held by one side alone is unmatched; the values are compared on the rest.
        matched = part[part["_merge"] == "both"]
        gap, one_sided = 0.0, 0
        for c in COMPARED:
            ours = matched[c].to_numpy(dtype=float)
            theirs = matched[f"{c}_recorded"].to_numpy(dtype=float)
            alike = (np.isnan(ours) & np.isnan(theirs)) | (ours == theirs)
            with np.errstate(invalid="ignore"):
                apart = np.abs(ours - theirs)
            one_sided += int((~alike & ~np.isfinite(apart)).sum())
            apart = apart[~alike & np.isfinite(apart)]
            gap = max(gap, float(apart.max()) if apart.size else 0.0)
        difference[metric] = {"max_abs_difference": gap, "values_not_finite_on_one_side": one_sided,
                              "cells_unmatched": int((part["_merge"] != "both").sum())}
    return table, {"build": build, "not_estimable": len(not_estimable),
                   "against_recorded": difference}


def band(ax, ages: dict[str, int], first: str, last: str, colour: str, label: str) -> None:
    inside = [a for c, a in ages.items() if first <= c <= last]
    if inside:
        ax.axvspan(min(inside) - 0.5, max(inside) + 0.5, color=colour, alpha=0.13, linewidth=0,
                   zorder=0, label=label)


def cmd_metric_age(args, expected: dict | None) -> dict:
    hashes: dict[str, str] = {}
    check_pin(args.cells, hashes)
    tables, per_build = [], {}
    for grid in args.grids:
        table, info = build_cells(grid, args.cells, hashes)
        tables.append(table)
        per_build[info["build"]] = info
        print(f"{info['build']}: {table['cohort'].nunique()} cells; against the grid "
              "recording: " + ", ".join(f"{m} {v['max_abs_difference']:.3g}"
                                       for m, v in info["against_recorded"].items()),
              flush=True)
    table = pd.concat(tables, ignore_index=True)
    cells = table[["build_id", "cohort", "floor"]].drop_duplicates()
    found = {"builds": len(per_build), "cells": len(cells),
             "under_floors": int((~cells["floor"]).sum())}
    check_expected(found, expected)
    builds = sorted(per_build, key=lambda b: (b.endswith("R"), b))
    expanding = [b for b in builds if b.endswith("E")]
    rolling = [b for b in builds if b.endswith("R")]
    # At most four panels to a line: the expanding arm's builds on the first lines, the rolling
    # arm's on the lines under them, and the legend in the slots the expanding arm leaves free
    # on its last line, or under every panel where it leaves none.
    per_line = min(4, max(len(expanding), len(rolling)))
    e_lines = math.ceil(len(expanding) / per_line)
    r_lines = math.ceil(len(rolling) / per_line)
    free = e_lines * per_line - len(expanding)
    left, right, gap, block_gap = 0.62, 0.05, 0.08, 0.1
    panel_w = (PRINT_WIDTH - left - right - gap * (per_line - 1)) / per_line
    head_h, ticks_h = pt(TEXT_PT * 1.3) + 0.04, pt(TICK_PT * 1.3) + 0.05
    panel_h = 1.1
    line_h = head_h + panel_h + ticks_h
    figures = []
    for metric, (label, models) in METRIC_FIGURES.items():
        note = (f"{label}. First context draw, {FIRST_DRAW}, for a seeded model; age is the "
                "stored quarter age halved and rounded up.")
        title_text = wrap_title(f"{METRIC_NAME[metric]} against age, one panel per build (top: "
                          "expanding arm, bottom: rolling arm), drawn after every model result")
        # The Cox figure's count is known once its panels are drawn; its line is reserved here.
        note_lines = lines_in(wrap_title(note + (" 0000 model cells whose Cox fit did not "
                                                 "converge have no point."
                                                 if metric == "cox_slope" else "")))
        top = pt(TITLE_PT * 1.3 * (lines_in(title_text) + note_lines)) + 0.1
        legend_below = 0.0 if free >= 2 else pt(TEXT_PT * 1.45 * 6) + 0.1
        height = (top + (e_lines + r_lines) * line_h + (block_gap if rolling else 0)
                  + pt(TEXT_PT * 1.3) + 0.06 + legend_below)
        fig = plt.figure(figsize=(PRINT_WIDTH, height))

        def place(line: int, column: int, below: bool, height: float = height,
                  top: float = top) -> tuple[float, float]:
            y = height - top - line * line_h - head_h - panel_h - (block_gap if below else 0)
            return left + column * (panel_w + gap), y

        slots: dict[str, object] = {}
        positions = ([(b, *divmod(i, per_line), False) for i, b in enumerate(expanding)]
                     + [(b, e_lines + i // per_line, i % per_line, True)
                        for i, b in enumerate(rolling)])
        for build, line, column, below in positions:
            x0, y0 = place(line, column, below)
            first = next(iter(slots.values()), None)
            ax = fig.add_axes((x0 / PRINT_WIDTH, y0 / height, panel_w / PRINT_WIDTH,
                               panel_h / height), sharex=first, sharey=first)
            ax.tick_params(labelleft=column == 0)
            slots[build] = ax
        unconverged = 0
        for build, ax in slots.items():
            own = table[(table["build_id"] == build) & (table["metric"] == metric)]
            ages = dict(own[["cohort", "age"]].drop_duplicates().itertuples(index=False))
            for name, (first, last, colour) in MARKS.items():
                band(ax, ages, first, last, colour, name)
            for model in models:
                rows = own[own["model"] == model].sort_values("age")
                colour = bi.model_colour(model)
                style = bi.model_style(model)
                ok = np.isfinite(rows["value"].to_numpy(dtype=float))
                if metric == "cox_slope":
                    unconverged += int((~ok).sum())
                elif not ok.all():
                    raise SystemExit(f"{build} {model}: a {metric} that is not finite; no point "
                                     "is dropped without a count")
                rows = rows[ok]
                ax.plot(rows["age"], rows["value"], color=colour, linestyle=style,
                        linewidth=0.6, label=bi.describe(model))
                if metric != "psi":
                    ax.errorbar(rows["age"], rows["value"],
                                yerr=[rows["value"] - rows["ci_lo"], rows["ci_hi"] - rows["value"]],
                                fmt="none", ecolor=colour, elinewidth=0.35, alpha=0.6)
                fl = rows["floor"].to_numpy(dtype=bool)
                ax.scatter(rows["age"][fl], rows["value"][fl], color=colour, s=2.5, linewidths=0,
                           zorder=3)
                ax.scatter(rows["age"][~fl], rows["value"][~fl], facecolors="white",
                           edgecolors=colour, s=6, linewidths=0.5, zorder=4)
            if metric == "cox_slope":
                ax.axhline(1.0, color="black", linewidth=0.5, linestyle=":",
                           label="Cox slope 1: the calibrated scale")
            ax.set_title(build, fontsize=TEXT_PT)
            ax.grid(alpha=0.25)
            ax.tick_params(labelsize=TICK_PT)
        first_ax = next(iter(slots.values()))
        if metric == "psi":
            first_ax.set_yscale("log")
            low, high = first_ax.get_ylim()
            log_axes(first_ax, low, high, x=False)
        last_line = max(line for _, line, _, _ in positions)
        for build, line, column, below in positions:
            if line == last_line or (below is False and not rolling
                                     and line == e_lines - 1):
                slots[build].set_xlabel("model age, half-years", fontsize=TEXT_PT)
            if column == 0:
                slots[build].set_ylabel(wrap(METRIC_AXIS[metric], panel_h + 0.3),
                                        fontsize=TEXT_PT)
        handles: dict[str, object] = {}
        for ax in slots.values():
            for handle, text in zip(*ax.get_legend_handles_labels(), strict=True):
                handles.setdefault(text, handle)
        handles[UNDER] = Line2D([], [], marker="o", linestyle="none", markerfacecolor="white",
                                markeredgecolor="#555555", markersize=3.5)
        if free >= 2:
            x0, y0 = place(e_lines - 1, per_line - free, False)
            anchor, loc = (x0 / PRINT_WIDTH, (y0 + panel_h + head_h) / height), "upper left"
        else:
            anchor, loc = (0.5, 0.06 / height), "lower center"
        fig.legend(list(handles.values()), list(handles.keys()), loc=loc, bbox_to_anchor=anchor,
                   ncol=2, frameon=False, fontsize=TEXT_PT, borderaxespad=0)
        if metric == "cox_slope":
            note += (f" {unconverged} model cells whose Cox fit did not converge have no "
                     "point.")
        fig.suptitle(title_text + "\n" + wrap_title(note), fontsize=TITLE_PT,
                     y=1 - 0.05 / height, va="top")
        name = f"metric-age-{metric.replace('_', '-')}.png"
        fig.savefig(args.out_dir / name, dpi=DPI)
        plt.close(fig)
        figures.append(name)
    write_outputs(args.out_dir, {"figures": figures, **found, "per_build": per_build}, hashes)
    return found


# --- the arm pooling's AUC against age -------------------------------------------------------


def command_dirs(manifest: dict, script: str) -> list[str]:
    """The positional directories a recorded command handed its script."""
    command = manifest["command"]
    start = next(i for i, part in enumerate(command) if part.endswith(script)) + 1
    out = []
    for part in command[start:]:
        if part.startswith("--"):
            break
        out.append(part.rstrip("/"))
    return out


def cmd_auc_age(args, expected: dict | None) -> dict:
    hashes: dict[str, str] = {}
    require_accepted(args.pooling)
    check_pin(args.cells, hashes)
    manifest = json.loads((args.pooling / "manifest.json").read_text(encoding="utf-8"))
    named = [d.as_posix().rstrip("/") for d in args.dirs]
    if named != command_dirs(manifest, "arm_intervals.py"):
        raise SystemExit(f"the directories named are not the ones {args.pooling.as_posix()} read")
    for d in args.dirs:
        if (d / "intervals.json").exists():
            hashed(d / "intervals.json", hashes)
    by_build: dict[str, list[Path]] = {}
    for path in ai.expand_sources(args.dirs):
        head = pd.read_parquet(hashed(path / "scores.parquet", hashes), columns=["build_id"])
        hashed(path / "reference.parquet", hashes)
        by_build.setdefault(str(head["build_id"].iloc[0]), []).append(path)
    arm = ai.Arm()
    for build, dirs in sorted(by_build.items()):
        arm.add_build(dirs, [])
    cohorts = arm.cohorts()
    paired = pd.read_csv(hashed(args.pooling / "paired.csv", hashes))
    verdicts = bi.read_floors(args.cells)
    floor = {cellkey: verdicts[cellkey] for cellkey in arm.cells()}
    found = {"builds": len(arm.builds), "cells": len(floor),
             "under_floors": sum(1 for v in floor.values() if not v)}
    check_expected(found, expected)

    names = list(arm.models)
    # Three panels to a line; the legend in the slots the last line leaves free, or under the
    # panels where it leaves fewer than two.
    per_line = min(3, len(names))
    lines = math.ceil(len(names) / per_line)
    free = lines * per_line - len(names)
    left, right, gap = 0.55, 0.05, 0.12
    panel_w = (PRINT_WIDTH - left - right - gap * (per_line - 1)) / per_line
    panel_h = 1.55
    head_h = pt(TEXT_PT * 1.25 * 3) + 0.05
    foot_h = pt(TICK_PT * 1.3) + pt(TEXT_PT * 1.3) + 0.1
    title_text = wrap_title("AUC against model age on every cell of the arm, one line per build")
    top = pt(TITLE_PT * 1.3 * lines_in(title_text)) + 0.1
    legend_h = 0.0 if free >= 2 else pt(TEXT_PT * 1.45 * math.ceil((len(arm.builds) + 2) / 3)) + 0.1
    height = top + lines * (head_h + panel_h + foot_h) + legend_h
    fig = plt.figure(figsize=(PRINT_WIDTH, height))

    def place(k: int) -> tuple[float, float]:
        line, column = divmod(k, per_line)
        return (left + column * (panel_w + gap),
                height - top - line * (head_h + panel_h + foot_h) - head_h - panel_h)

    axes = []
    for k in range(len(names)):
        x0, y0 = place(k)
        axes.append(fig.add_axes((x0 / PRINT_WIDTH, y0 / height, panel_w / PRINT_WIDTH,
                                  panel_h / height), sharey=axes[0] if axes else None))
    cmap = plt.get_cmap("viridis")
    slopes = paired[(paired["metric"] == "auc_slope_build") & ~paired["is_difference"]
                    & (paired["scope"] == ai.ARM) & (paired["cohorts"] == "all")
                    & paired["draw"].isna()].set_index("pair")
    for k, (ax, model) in enumerate(zip(axes, names, strict=True)):
        ages_all, aucs_all = [], []
        for i, line in enumerate(arm.builds):
            points = []
            for cohort in arm.cohorts_of(line):
                c = cohorts[cohort]
                s = c.scores.get((line, model))
                if s is None:
                    s = c.seeds[(line, model)][0]
                points.append((arm.ages[(line, cohort)], mt.auc(c.outcome, s),
                               floor[(line, cohort)]))
            points.sort()
            x = np.array([p[0] for p in points], dtype=float)
            y = np.array([p[1] for p in points])
            above = np.array([p[2] for p in points], dtype=bool)
            ages_all.extend(x)
            aucs_all.extend(y)
            colour = cmap(i / max(1, len(arm.builds) - 1))
            ax.plot(x, y, color=colour, linewidth=0.7, label=line)
            ax.scatter(x[above], y[above], color=colour, s=3, linewidths=0, zorder=3)
            ax.scatter(x[~above], y[~above], facecolors="white", edgecolors=colour, s=7,
                       linewidths=0.6, zorder=4)
        if model in slopes.index:
            row = slopes.loc[model]
            gx = np.array([min(ages_all), max(ages_all)], dtype=float)
            ax.plot(gx, float(np.mean(aucs_all)) + row.value * (gx - float(np.mean(ages_all))),
                    color="black", linewidth=1.0, linestyle="--",
                    label="arm slope, one intercept per build")
            ax.set_title(bi.describe(model) + "\n"
                         + wrap(f"slope {row.value:+.5f} [{row.ci_lo:+.5f}, {row.ci_hi:+.5f}] "
                                "per quarter", panel_w), fontsize=TEXT_PT)
        else:
            ax.set_title(bi.describe(model), fontsize=TEXT_PT)
        ax.set_xlabel("model age, quarters", fontsize=TEXT_PT)
        ax.grid(alpha=0.3)
        if k % per_line == 0:
            ax.set_ylabel(wrap("AUC on the cell, first context draw", panel_h + 0.3),
                          fontsize=TEXT_PT)
        else:
            ax.tick_params(labelleft=False)
    handles, labels = axes[0].get_legend_handles_labels()
    handles.append(Line2D([], [], marker="o", linestyle="none", markerfacecolor="white",
                          markeredgecolor="#555555", markersize=3.5))
    labels.append("a cell under the floors: scored, entering no slope")
    if free >= 2:
        x0, y0 = place(len(names))
        anchor, loc, ncol = (x0 / PRINT_WIDTH, (y0 + panel_h + head_h) / height), "upper left", 2
    else:
        anchor, loc, ncol = (0.5, 0.06 / height), "lower center", 3
    fig.legend(handles, labels, loc=loc, bbox_to_anchor=anchor, ncol=ncol, frameon=False,
               fontsize=TEXT_PT, borderaxespad=0)
    fig.suptitle(title_text, fontsize=TITLE_PT, y=1 - 0.05 / height, va="top")
    fig.savefig(args.out_dir / "auc-age.png", dpi=DPI)
    plt.close(fig)
    write_outputs(args.out_dir, {"figure": "auc-age.png", **found,
                                 "pooling": relative(args.pooling).as_posix()}, hashes)
    return found


# --- the level across prevalence -------------------------------------------------------------


def cmd_level(args, expected: dict | None) -> dict:
    hashes: dict[str, str] = {}
    require_accepted(args.in_sample)
    table = pd.read_csv(hashed(args.in_sample / "cells.csv", hashes), dtype={"build_id": str})
    cohorts = pd.read_csv(hashed(args.in_sample / "cohort-cells.csv", hashes),
                          dtype={"build_id": str, "cohort": str})
    if args.cells is not None:
        check_pin(args.cells, hashes)
        verdicts = bi.read_floors(args.cells)
        missing = [k for k in zip(cohorts["build_id"], cohorts["cohort"], strict=True)
                   if k not in verdicts]
        if missing:
            raise SystemExit(f"{args.cells.as_posix()} holds no verdict on {missing[0]}")
        above = np.array([verdicts[k] for k in zip(cohorts["build_id"], cohorts["cohort"],
                                                     strict=True)])
    else:
        above = ((cohorts["rows"] >= bi.FLOOR_ROWS)
                 & (cohorts["defaults"] >= bi.FLOOR_DEFAULTS)).to_numpy()
        if not above.all():
            raise SystemExit("a cohort cell under the floors and no build record to read "
                             "its verdict from; name it with --cells")
    cohorts = cohorts.assign(above=above)
    names = isl.model_names(table["model"])
    positive = (table["realised_rate"] > 0) & (table["mean_pd"] > 0)
    placed_c = (cohorts["defaults"] > 0) & (cohorts["mean_pd"] > 0)
    values = [*table.loc[positive, "realised_rate"], *table.loc[positive, "mean_pd"],
              *cohorts.loc[placed_c, "realised_rate"], *cohorts.loc[placed_c, "mean_pd"]]
    low, high = margin_range(values, LEVEL_MARGIN)
    left_off = int((~positive).sum() + (~placed_c).sum())
    # Three square panels to a line, as large as the page allows; the legend in the slots the
    # last line leaves free, or under the panels where it leaves fewer than two.
    columns = min(3, len(names))
    lines = math.ceil(len(names) / columns)
    free = lines * columns - len(names)
    title_text = wrap_title("the level across prevalence: mean predicted probability against realised "
                      "rate, one marker per cell, one axis for every panel\n"
                      f"{relative(args.in_sample).as_posix()}; {left_off} cells with no default "
                      "left off the log axis")
    left, right, gap = 0.55, 0.05, 0.5
    head_h = pt(TEXT_PT * 1.3 * 2) + 0.05
    foot_h = pt(TICK_PT * 0.62 * 6) + pt(TEXT_PT * 1.3) + 0.1
    top = pt(TITLE_PT * 1.3 * lines_in(title_text)) + 0.1
    legend_h = 0.0 if free >= 2 else pt(TEXT_PT * 1.45 * 4) + 0.12
    side = (PRINT_WIDTH - left - right - gap * (columns - 1)) / columns
    if top + lines * (head_h + side + foot_h) + legend_h > PRINT_HEIGHT:
        side = (PRINT_HEIGHT - top - legend_h) / lines - head_h - foot_h
        gap = (PRINT_WIDTH - left - right - columns * side) / max(1, columns - 1)
    height = top + lines * (head_h + side + foot_h) + legend_h
    fig = plt.figure(figsize=(PRINT_WIDTH, height))
    axes = []
    for k in range(len(names)):
        line, column = divmod(k, columns)
        y0 = height - top - line * (head_h + side + foot_h) - head_h - side
        axes.append(fig.add_axes(((left + column * (side + gap)) / PRINT_WIDTH, y0 / height,
                                  side / PRINT_WIDTH, side / height)))
    drawn = 0
    for ax, model in zip(axes, names, strict=True):
        sub = cohorts[(cohorts["model"] == model) & placed_c]
        for flag, edge, text in ((True, "#8C8C8C", "a cohort cell, out of sample"),
                                 (False, "#b0392b", f"a cohort cell {UNDER}")):
            part = sub[sub["above"] == flag]
            if part.empty:
                continue
            ax.scatter(part["realised_rate"], part["mean_pd"], s=4 if flag else 7,
                       facecolors="none", edgecolors=edge, linewidths=0.4 if flag else 0.6,
                       label=text)
            drawn += len(part)
        own = table[(table["model"] == model) & positive]
        for (arm, kind), part in own.groupby(["arm", "kind"], sort=True):
            ax.scatter(part["realised_rate"], part["mean_pd"], s=14,
                       marker="D" if kind == "training pool" else "o",
                       color=isl.ARM_COLOUR.get(arm, "#4B3F8F"), edgecolors="black",
                       linewidths=0.3, zorder=3, label=f"in sample, arm {arm}, {kind}")
            drawn += len(part)
        ax.plot([low, high], [low, high], color="black", linewidth=0.6, linestyle=":",
                label="identity: calibrated in the large")
        ax.set_xscale("log")
        ax.set_yscale("log")
        log_axes(ax, low, high)
        ax.set_aspect("equal")
        ax.tick_params(axis="x", labelrotation=90, labelsize=TICK_PT)
        ax.tick_params(axis="y", labelsize=TICK_PT)
        ax.set_title(wrap(bi.describe(model), side), fontsize=TEXT_PT)
        ax.set_xlabel(wrap("realised default rate of the cell", side + 0.4), fontsize=TEXT_PT)
        ax.set_ylabel(wrap("mean predicted probability", side), fontsize=TEXT_PT)
        ax.grid(alpha=0.3, which="major")
    if drawn + left_off != len(table) + len(cohorts):
        raise SystemExit(f"{drawn} cells drawn and {left_off} left off of "
                         f"{len(table) + len(cohorts)}")
    seen: dict[str, object] = {}
    for ax in axes:
        for handle, text in zip(*ax.get_legend_handles_labels(), strict=True):
            seen.setdefault(text, handle)
    if free >= 2:
        line, column = divmod(len(names), columns)
        anchor = ((left + column * (side + gap)) / PRINT_WIDTH,
                  (height - top - line * (head_h + side + foot_h)) / height)
        fig.legend(seen.values(), seen.keys(), loc="upper left", ncol=1, frameon=False,
                   fontsize=TEXT_PT, bbox_to_anchor=anchor, borderaxespad=0)
    else:
        fig.legend(seen.values(), seen.keys(), loc="lower center", ncol=min(len(seen), 2),
                   frameon=False, fontsize=TEXT_PT, bbox_to_anchor=(0.5, 0.06 / height),
                   borderaxespad=0)
    fig.suptitle(title_text, fontsize=TITLE_PT, y=1 - 0.05 / height, va="top")
    fig.savefig(args.out_dir / "level-prevalence.png", dpi=DPI)
    plt.close(fig)
    found = {"cells": len(table), "cohort_cells": len(cohorts), "left_off": left_off,
             "under_floors": int((~cohorts["above"]).sum()), "axis": [low, high]}
    check_expected(found, expected)
    write_outputs(args.out_dir, {"figure": "level-prevalence.png",
                                 "in_sample": relative(args.in_sample).as_posix(), **found},
                  hashes)
    return found


# --- the command -----------------------------------------------------------------------------


COMMANDS = {"lc-ridge": cmd_lc_ridge, "fm-ridge": cmd_fm_ridge, "reliability": cmd_reliability,
            "relief-share": cmd_relief_share, "build-grid": cmd_build_grid,
            "metric-age": cmd_metric_age, "auc-age": cmd_auc_age, "level": cmd_level}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="figure", required=True)

    def add(name: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name)
        p.add_argument("--out-dir", type=Path, required=True)
        return p

    p = add("lc-ridge")
    p.add_argument("dirs", type=Path, nargs="+", help="the build's score directories")
    p.add_argument("--psi-run", type=Path, required=True,
                   help="the grid recording whose metrics.csv holds each cell's PSI")
    p = add("fm-ridge")
    p.add_argument("dirs", type=Path, nargs="+")
    p.add_argument("--cells", type=Path, required=True, help="the build record's cells.csv")
    p = add("reliability")
    p.add_argument("dirs", type=Path, nargs="+")
    p.add_argument("--cells", type=Path, required=True)
    p = add("relief-share")
    p.add_argument("--structure", type=Path, required=True, help="EXP-003's structure recording")
    p.add_argument("--sensitivity", type=Path, required=True,
                   help="the recorded pooling of the sensitivity reading the caption points to")
    p.add_argument("--cells", type=Path, required=True)
    p.add_argument("--builds", type=Path, required=True, help="the build record's builds.json")
    p = add("build-grid")
    p.add_argument("--builds", type=Path, required=True)
    p.add_argument("--cells", type=Path, required=True)
    p = add("metric-age")
    p.add_argument("grids", type=Path, nargs="+", help="the per-build grid recordings")
    p.add_argument("--cells", type=Path, required=True)
    p = add("auc-age")
    p.add_argument("dirs", type=Path, nargs="+",
                   help="the directories the arm pooling read, as its command names them")
    p.add_argument("--pooling", type=Path, required=True)
    p.add_argument("--cells", type=Path, required=True)
    p = add("level")
    p.add_argument("--in-sample", type=Path, required=True)
    p.add_argument("--cells", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    with plt.rc_context(PRINT_RC):
        found = COMMANDS[args.figure](args, EXPECTED.get(args.figure))
    for key, value in found.items():
        print(f"{key:<32}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
