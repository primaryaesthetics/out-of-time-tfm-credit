#!/usr/bin/env python3
"""Four recorded figures of the paper drawn again at the size the paper prints them.

The paper prints every figure at the text width of the tmlr style, 6.5 inches.
Four of the figures it takes from recorded runs were drawn 17 to 27 inches wide,
so their type prints at two to three points. The dated entries of 2026-09-26 in
`docs/experiments/EXP-002-log.md`, `EXP-004-published-protocol-beside-this-one.md`
and `EXP-005-log.md` fix a redraw of each: the same marks, bands, intervals,
titles and legend entries as the recorded figure, with only the size, the type
and the arrangement of the panels changed. One subcommand per figure, each run
in a recording of its own:

    lc-auc-age          AUC against model age on every cell of Lending Club's
                        expanding arm, one panel per model, one line per build
                        (arm_intervals.py, `auc-age.png`)
    fm-build-rows       the per-build rows of each criterion difference on
                        Freddie Mac's expanding arm beside the arm's
                        (arm_intervals.py, `build-rows.png`)
    fm-between-arm-rows the rolling arm's reduction of calibration drift per
                        build date on Freddie Mac (between_arm_intervals.py,
                        `build-rows.png`)
    lc-protocols-reliability
                        reliability in ten quantile bins on 2015H1-E in time
                        and out of time (protocol_table.py,
                        `reliability-protocols.png`)

The size rule is the one `registered_figures.py` draws under, read from its
constants PRINT_WIDTH, PRINT_HEIGHT, TEXT_PT, TICK_PT and DPI: at most 6.5 by
8.5 inches, text of at least 7 points and tick labels of at least 6.5 at that
size, 300 dots per inch, the panels in more rows where one row does not fit.

Nothing is refitted and nothing is pooled. Each figure reads one recorded run
that the claim gate accepts at HEAD, and refuses one it does not. Where that
run's outputs hold every value drawn, the figure reads them and nothing else.
Where the recorded figure computed its values from row-level scores, as the
AUC of each cell and the reliability curves were, the figure computes them from
the same score files with the same functions of the metric module, and checks
them against numbers the recorded run wrote: every score file of the arm
pooling hashes to the value its `inputs.json` records, and the values drawn
reproduce the pooling's rows on the first context draw; the protocol run
records no hash of its score files, so the figure reproduces the AUC, the Brier
score and the observed over expected that run's `cells.csv` holds for every
model in time and out of time before it draws.

Each run writes the figure under the recorded figure's file name,
`summary.json` with the counts it drew and checked, and `inputs.json` with the
sha256 of every file it read.

    python scripts/record_run.py lc-arm-e-auc-age-print -- \\
        python scripts/print_figures.py lc-auc-age \\
            --pooling experiments/2026-09-22-lc-arm-e-intervals \\
            --out-dir experiments/2026-09-26-lc-arm-e-auc-age-print
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import arm_intervals as ai
import between_arm_intervals as ba
import build_intervals as bi
import protocol_table as pt
import record_run as rr
import registered_figures as rf

from outoftime import metrics as mt

ROOT = Path(__file__).resolve().parent.parent

PRINT_WIDTH = rf.PRINT_WIDTH
PRINT_HEIGHT = rf.PRINT_HEIGHT
TEXT_PT = rf.TEXT_PT
TICK_PT = rf.TICK_PT
TITLE_PT = rf.TITLE_PT
DPI = rf.DPI
PRINT_RC = rf.PRINT_RC
wrap = rf.wrap
wrap_title = rf.wrap_title
lines_in = rf.lines_in
pt_ = rf.pt

FIRST_DRAW = 20260911
# The largest difference allowed between a value drawn and the recorded value it reproduces.
TOLERANCE = 1e-9
# The columns of the protocol run's cells.csv the reliability figure reproduces before it draws,
# each as the run computes it on a cell.
CHECKED_COLUMNS = {
    "auc": mt.auc,
    "brier": mt.brier,
    "observed_over_expected": lambda y, s: mt.observed_over_expected(y, s).value,
}

# The recorded run each figure is drawn from, and what the log entries of 2026-09-26 state
# about it; a run that reads anything else stops.
SOURCES = {
    "lc-auc-age": "experiments/2026-09-22-lc-arm-e-intervals",
    "fm-build-rows": "experiments/2026-09-21-fm-arm-e-intervals-refit-control",
    "fm-between-arm-rows": "experiments/2026-09-22-fm-between-arm-intervals",
    "lc-protocols-reliability": "experiments/2026-09-23-lc-2015h1e-protocols5-tfm",
}
EXPECTED: dict[str, dict] = {
    "lc-auc-age": {"panels": 7, "builds": 9, "cells": 99, "points": 693},
    "fm-build-rows": {"panels": 16, "builds": 9, "build_rows": 144, "arm_rows": 16},
    "fm-between-arm-rows": {"panels": 6, "dates": 8, "date_rows": 48, "pooled_rows": 6},
    "lc-protocols-reliability": {"panels": 7, "curves": 21, "youngest": "2015Q3",
                                 "oldest": "2018Q1", "fold": 1},
}


# --- what may be read ---------------------------------------------------------------------


def relative(path: Path) -> str:
    return Path(os.path.relpath(Path(path).resolve(), ROOT.resolve())).as_posix()


def hashed(path: Path, hashes: dict[str, str]) -> Path:
    hashes[relative(path)] = rr.file_hash(path)
    return path


def require_source(kind: str, run: Path) -> dict:
    """The run the log entry names for this figure, accepted by the claim gate, exited 0."""
    if relative(run) != SOURCES[kind]:
        raise SystemExit(f"{relative(run)} is not {SOURCES[kind]}, the recording the log "
                         "entry names")
    rf.require_accepted(ROOT / relative(run), ROOT)
    manifest = json.loads((ROOT / relative(run) / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("exit_code") != 0:
        raise SystemExit(f"{relative(run)} exited {manifest.get('exit_code')}")
    return manifest


def check_expected(found: dict, expected: dict | None) -> None:
    if not expected:
        return
    wrong = {k: (found.get(k), v) for k, v in expected.items() if found.get(k) != v}
    if wrong:
        raise SystemExit("the figure is not the one the log entry fixes: " + "; ".join(
            f"{k} is {got!r}, the entry says {want!r}" for k, (got, want) in wrong.items()))


def write_outputs(out_dir: Path, summary: dict, hashes: dict[str, str]) -> None:
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n",
                                          encoding="utf-8")
    (out_dir / "inputs.json").write_text(json.dumps(dict(sorted(hashes.items())), indent=2)
                                         + "\n", encoding="utf-8")


def one_row(frame: pd.DataFrame, what: str) -> pd.Series:
    if len(frame) != 1:
        raise SystemExit(f"{what}: {len(frame)} rows in the recorded table, not one")
    return frame.iloc[0]


def unbroken(text: str, keep: str, inches: float) -> str:
    """`text` wrapped to `inches` of 7-point type with `keep` never broken across two lines."""
    glue = "\u00a0"
    return wrap(text.replace(keep, keep.replace(" ", glue)), inches).replace(glue, " ")


def axes_at(fig, x0: float, y0: float, w: float, h: float, height: float, **kwargs):
    return fig.add_axes((x0 / PRINT_WIDTH, y0 / height, w / PRINT_WIDTH, h / height), **kwargs)


# --- AUC against age on Lending Club's expanding arm ---------------------------------------


def cmd_lc_auc_age(args, expected: dict | None) -> dict:
    hashes: dict[str, str] = {}
    require_source("lc-auc-age", args.pooling)
    pooling = ROOT / relative(args.pooling)
    summary = json.loads(hashed(pooling / "intervals.json", hashes).read_text(encoding="utf-8"))
    pinned = json.loads(hashed(pooling / "inputs.json", hashes).read_text(encoding="utf-8"))
    paired = pd.read_csv(hashed(pooling / "paired.csv", hashes))
    by_build: dict[str, list[Path]] = {}
    for source in summary["sources"]:
        d = ROOT / source
        for name in ("scores.parquet", "reference.parquet"):
            key = f"{source}/{name}"
            found = rr.file_hash(d / name)
            if pinned.get(key) != found:
                raise SystemExit(f"{key} hashes to {found}, not the {pinned.get(key)} "
                                 f"{relative(pooling)} read")
            hashes[key] = found
        head = pd.read_parquet(d / "scores.parquet", columns=["build_id"])
        by_build.setdefault(str(head["build_id"].iloc[0]), []).append(d)
    arm = ai.Arm()
    for build, dirs in sorted(by_build.items()):
        arm.add_build(dirs, summary.get("models_dropped") or [])
    if list(arm.builds) != list(summary["builds"]):
        raise SystemExit(f"the builds read are not the ones {relative(pooling)} pooled")
    if {m: [] if s == [None] else s for m, s in arm.models.items()} != summary["models"]:
        raise SystemExit(f"the models read are not the ones {relative(pooling)} pooled")
    cohorts = arm.cohorts()
    names = list(arm.models)

    # Every cell's AUC on the first context draw, as the recorded figure computes it.
    lines_of: dict[str, list[tuple[str, np.ndarray, np.ndarray]]] = {}
    for model in names:
        lines_of[model] = []
        for line in arm.builds:
            points = []
            for cohort in arm.cohorts_of(line):
                c = cohorts[cohort]
                s = c.scores.get((line, model))
                if s is None:
                    s = c.seeds[(line, model)][0]
                points.append((arm.ages[(line, cohort)], mt.auc(c.outcome, s)))
            points.sort()
            lines_of[model].append((line, np.array([p[0] for p in points], dtype=float),
                                    np.array([p[1] for p in points])))

    # The values drawn reproduce the pooling's rows with the first draw held fixed: the mean
    # Gini over every cell, and the slope with one intercept per build.
    first = paired[(paired["cohorts"] == "all") & (paired["draw"] == FIRST_DRAW)
                   & (paired["scope"] == ai.ARM) & ~paired["is_difference"]]
    worst = 0.0
    for model in names:
        ages = np.concatenate([x for _, x, _ in lines_of[model]])
        aucs = np.concatenate([y for _, _, y in lines_of[model]])
        groups = np.concatenate([[b] * x.size for b, x, _ in lines_of[model]])
        for metric, value in (("gini", float(np.mean(2.0 * aucs - 1.0))),
                              ("auc_slope_build", ai.slope(ages, aucs, groups))):
            row = one_row(first[(first["metric"] == metric) & (first["pair"] == model)],
                          f"{metric} of {model}, draw {FIRST_DRAW}")
            gap = abs(float(row["value"]) - value)
            worst = max(worst, gap)
            if not gap <= TOLERANCE:
                raise SystemExit(f"{metric} of {model} on draw {FIRST_DRAW}: the cells drawn "
                                 f"give {value!r}, {relative(pooling)} records {row['value']!r}")
    slopes = paired[(paired["metric"] == "auc_slope_build") & ~paired["is_difference"]
                    & (paired["scope"] == ai.ARM) & (paired["cohorts"] == "all")
                    & paired["draw"].isna()].set_index("pair")

    # Three panels to a line; the legend in the slots the last line leaves free, or under the
    # panels where it leaves fewer than two.
    per_line = min(3, len(names))
    lines = math.ceil(len(names) / per_line)
    free = lines * per_line - len(names)
    left, right, gap = 0.72, 0.05, 0.12
    panel_w = (PRINT_WIDTH - left - right - gap * (per_line - 1)) / per_line
    panel_h = 1.55
    head_h = pt_(TEXT_PT * 1.25 * 3) + 0.05
    foot_h = pt_(TICK_PT * 1.3) + pt_(TEXT_PT * 1.3) + 0.1
    title_text = wrap_title("AUC against model age on every cell of the arm, one line per build")
    top = pt_(TITLE_PT * 1.3 * lines_in(title_text)) + 0.1
    legend_h = (0.0 if free >= 2 else
                pt_(TEXT_PT * 1.45 * math.ceil((len(arm.builds) + 1) / 3)) + 0.1)
    height = top + lines * (head_h + panel_h + foot_h) + legend_h
    fig = plt.figure(figsize=(PRINT_WIDTH, height))

    def place(k: int) -> tuple[float, float]:
        line, column = divmod(k, per_line)
        return (left + column * (panel_w + gap),
                height - top - line * (head_h + panel_h + foot_h) - head_h - panel_h)

    axes = []
    for k in range(len(names)):
        x0, y0 = place(k)
        axes.append(axes_at(fig, x0, y0, panel_w, panel_h, height,
                            sharey=axes[0] if axes else None))
    cmap = plt.get_cmap("viridis")
    drawn = 0
    for k, (ax, model) in enumerate(zip(axes, names, strict=True)):
        ages_all: list[float] = []
        aucs_all: list[float] = []
        for i, (line, x, y) in enumerate(lines_of[model]):
            ages_all.extend(x)
            aucs_all.extend(y)
            ax.plot(x, y, color=cmap(i / max(1, len(arm.builds) - 1)), marker="o",
                    markersize=1.8, linewidth=0.7, label=line)
            drawn += x.size
        if model in slopes.index:
            row = slopes.loc[model]
            gx = np.array([min(ages_all), max(ages_all)], dtype=float)
            ax.plot(gx, float(np.mean(aucs_all)) + row.value * (gx - float(np.mean(ages_all))),
                    color="black", linewidth=1.0, linestyle="--",
                    label="arm slope, one intercept per build")
            interval = f"[{row.ci_lo:+.5f}, {row.ci_hi:+.5f}]"
            ax.set_title(bi.describe(model) + "\n"
                         + unbroken(f"slope {row.value:+.5f} {interval} per quarter", interval,
                                    panel_w), fontsize=TEXT_PT)
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
    found = {"panels": len(names), "builds": len(arm.builds), "cells": len(arm.cells()),
             "points": drawn}
    check_expected(found, expected)
    write_outputs(args.out_dir, {
        "figure": "auc-age.png", "source": relative(pooling), **found,
        "slopes_printed": int(sum(m in slopes.index for m in names)),
        "check": {"rows": f"gini and auc_slope_build, scope arm, draw {FIRST_DRAW}, every model",
                  "largest_difference": worst, "tolerance": TOLERANCE}}, hashes)
    return found


# --- the per-build rows of the criterion differences on Freddie Mac ------------------------


def cmd_fm_build_rows(args, expected: dict | None) -> dict:
    hashes: dict[str, str] = {}
    require_source("fm-build-rows", args.pooling)
    pooling = ROOT / relative(args.pooling)
    summary = json.loads(hashed(pooling / "intervals.json", hashes).read_text(encoding="utf-8"))
    paired = pd.read_csv(hashed(pooling / "paired.csv", hashes))
    builds = list(summary["builds"])
    models = list(summary["models"])
    # The panels the recorded figure draws, in its order: each metric of the criteria for
    # every foundation model, those the pooling holds no row of left out as it leaves them.
    tfms = [m for m in models if bi.base_model(m) in ("tabpfn", "tabicl")]
    focus = [(metric, f"{m} - {against}") for metric, against in (
        ("auc_slope_build", "gbm-50k"), ("cox_slope_deviation", "scorecard"),
        ("psi", "gbm-50k"), ("psi_first_cohort", "gbm-50k")) for m in tfms]
    rows = paired[paired["is_difference"] & paired["draw"].isna() & (paired["cohorts"] == "all")]
    focus = [(m, p) for m, p in focus if ((rows["metric"] == m) & (rows["pair"] == p)).any()]
    if not focus:
        raise SystemExit(f"{relative(pooling)} holds no row of the figure's differences")

    # One line per metric where the models fill it, four panels to a line.
    columns = min(4, len(focus))
    lines = math.ceil(len(focus) / columns)
    left, right, gap = 0.5, 0.15, 0.48
    panel_w = (PRINT_WIDTH - left - right - gap * (columns - 1)) / columns
    title_w = panel_w + 0.5 * gap
    titles = [wrap(f"{ai.ARM_TITLE[metric]}\n{pair}", title_w) for metric, pair in focus]
    head_h = pt_(TEXT_PT * 1.25 * max(lines_in(t) for t in titles)) + 0.06
    label_len = max(len(b) for b in builds)
    foot_h = pt_(TICK_PT * 0.62 * label_len) + 0.12
    title_text = wrap_title("the per-build rows of each difference beside the arm's, one shared "
                            "resample")
    top = pt_(TITLE_PT * 1.3 * lines_in(title_text)) + 0.12
    legend_h = pt_(TEXT_PT * 1.6) + 0.1
    panel_h = min(1.4, (PRINT_HEIGHT - top - legend_h) / lines - head_h - foot_h)
    height = top + lines * (head_h + panel_h + foot_h) + legend_h
    fig = plt.figure(figsize=(PRINT_WIDTH, height))
    x = np.arange(len(builds))
    build_rows = arm_rows = 0
    axes = []
    for k, ((metric, pair), title) in enumerate(zip(focus, titles, strict=True)):
        line, column = divmod(k, columns)
        y0 = height - top - line * (head_h + panel_h + foot_h) - head_h - panel_h
        ax = axes_at(fig, left + column * (panel_w + gap), y0, panel_w, panel_h, height)
        axes.append(ax)
        sub = rows[(rows["metric"] == metric) & (rows["pair"] == pair)]
        if sub["scope"].duplicated().any():
            raise SystemExit(f"{metric} {pair}: a scope held twice in {relative(pooling)}")
        sub = sub.set_index("scope")
        missing = [s for s in [ai.ARM, *builds] if s not in sub.index]
        if missing:
            raise SystemExit(f"{metric} {pair}: no row for {', '.join(missing)}")
        whole = sub.loc[ai.ARM]
        ax.axhspan(whole.ci_lo, whole.ci_hi, color="#0E6B66", alpha=0.15, linewidth=0)
        ax.axhline(whole.value, color="#0E6B66", linewidth=0.9, label="arm, pooled")
        arm_rows += 1
        per = sub.loc[builds]
        ax.vlines(x, per["ci_lo"], per["ci_hi"], color="#9A5B24", linewidth=0.9)
        ax.plot(x, per["value"], marker="o", markersize=2.6, color="#9A5B24", linestyle="none",
                label="one build")
        build_rows += len(per)
        ax.axhline(0.0, color="black", linewidth=0.6, linestyle=":")
        ax.set_xticks(x)
        ax.set_xticklabels(builds, rotation=90, fontsize=TICK_PT)
        ax.tick_params(axis="y", labelsize=TICK_PT)
        ax.yaxis.get_offset_text().set_fontsize(TICK_PT)
        ax.set_title(title, fontsize=TEXT_PT)
        ax.grid(alpha=0.3, axis="y")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False, fontsize=TEXT_PT,
               bbox_to_anchor=(0.5, 0.05 / height), borderaxespad=0)
    fig.suptitle(title_text, fontsize=TITLE_PT, y=1 - 0.05 / height, va="top")
    fig.savefig(args.out_dir / "build-rows.png", dpi=DPI)
    plt.close(fig)
    found = {"panels": len(focus), "builds": len(builds), "build_rows": build_rows,
             "arm_rows": arm_rows}
    check_expected(found, expected)
    write_outputs(args.out_dir, {"figure": "build-rows.png", "source": relative(pooling),
                                 **found, "panels_drawn": [f"{m} | {p}" for m, p in focus]},
                  hashes)
    return found


# --- the rolling arm's reduction per build date on Freddie Mac -----------------------------


def cmd_fm_between_arm_rows(args, expected: dict | None) -> dict:
    hashes: dict[str, str] = {}
    require_source("fm-between-arm-rows", args.pooling)
    pooling = ROOT / relative(args.pooling)
    summary = json.loads(hashed(pooling / "summary.json", hashes).read_text(encoding="utf-8"))
    paired = pd.read_csv(hashed(pooling / "paired.csv", hashes))
    dates = list(summary["build_dates"])
    contrast = summary.get("contrast") or {}
    rows = paired[(paired["kind"] == "h4") & (paired["cohorts"] == "all") & paired["draw"].isna()]
    models = ba.model_names(rows["model"].unique())
    if not models:
        raise SystemExit(f"{relative(pooling)} holds no h4 row")
    labels = []
    for date in dates:
        share = contrast.get(date, {}).get("share_held")
        labels.append(date if share is None else f"{date}\nholds {share:.0%}")

    # Two panels to a line, so that each date's two-line label stands clear of the next.
    columns = min(2, len(models))
    lines = math.ceil(len(models) / columns)
    left, right, gap = 0.5, 0.05, 0.45
    panel_w = (PRINT_WIDTH - left - right - gap * (columns - 1)) / columns
    titles = [wrap(f"{bi.describe(m)} minus the control\n(E - R) of |Cox slope - 1|",
                   panel_w + 0.8 * gap) for m in models]
    head_h = pt_(TEXT_PT * 1.25 * max(lines_in(t) for t in titles)) + 0.06
    label_len = max(len(part) for text in labels for part in text.split("\n"))
    foot_h = pt_(TEXT_PT * 0.62 * label_len) + 0.12
    title_text = wrap_title("the rolling arm's reduction of calibration drift, model minus "
                            "control, per build date; the label under a date is the share of "
                            "the expanding pool the rolling window holds")
    top = pt_(TITLE_PT * 1.3 * lines_in(title_text)) + 0.12
    legend_h = pt_(TEXT_PT * 1.6) + 0.1
    panel_h = min(1.5, (PRINT_HEIGHT - top - legend_h) / lines - head_h - foot_h)
    height = top + lines * (head_h + panel_h + foot_h) + legend_h
    fig = plt.figure(figsize=(PRINT_WIDTH, height))
    x = np.arange(len(dates))
    date_rows = pooled_rows = 0
    axes = []
    for k, (model, title) in enumerate(zip(models, titles, strict=True)):
        line, column = divmod(k, columns)
        y0 = height - top - line * (head_h + panel_h + foot_h) - head_h - panel_h
        ax = axes_at(fig, left + column * (panel_w + gap), y0, panel_w, panel_h, height)
        axes.append(ax)
        sub = rows[rows["model"] == model]
        if sub["scope"].duplicated().any():
            raise SystemExit(f"h4 of {model}: a scope held twice in {relative(pooling)}")
        sub = sub.set_index("scope")
        missing = [s for s in [ba.POOLED, *dates] if s not in sub.index]
        if missing:
            raise SystemExit(f"h4 of {model}: no row for {', '.join(missing)}")
        whole = sub.loc[ba.POOLED]
        ax.axhspan(whole.ci_lo, whole.ci_hi, color="#0E6B66", alpha=0.15, linewidth=0)
        ax.axhline(whole.value, color="#0E6B66", linewidth=0.9, label="every shared cell")
        pooled_rows += 1
        per = sub.loc[dates]
        ax.vlines(x, per["ci_lo"], per["ci_hi"], color="#9A5B24", linewidth=0.9)
        ax.plot(x, per["value"], marker="o", markersize=2.6, color="#9A5B24", linestyle="none",
                label="one build date")
        date_rows += len(per)
        ax.axhline(0.0, color="black", linewidth=0.6, linestyle=":")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=90, fontsize=TEXT_PT)
        ax.tick_params(axis="y", labelsize=TICK_PT)
        ax.set_title(title, fontsize=TEXT_PT)
        ax.grid(alpha=0.3, axis="y")
    handles, texts = axes[0].get_legend_handles_labels()
    fig.legend(handles, texts, loc="lower center", ncol=2, frameon=False, fontsize=TEXT_PT,
               bbox_to_anchor=(0.5, 0.05 / height), borderaxespad=0)
    fig.suptitle(title_text, fontsize=TITLE_PT, y=1 - 0.05 / height, va="top")
    fig.savefig(args.out_dir / "build-rows.png", dpi=DPI)
    plt.close(fig)
    found = {"panels": len(models), "dates": len(dates), "date_rows": date_rows,
             "pooled_rows": pooled_rows}
    check_expected(found, expected)
    write_outputs(args.out_dir, {"figure": "build-rows.png", "source": relative(pooling),
                                 **found, "models": models, "date_labels": labels}, hashes)
    return found


# --- reliability under both protocols on 2015H1-E -------------------------------------------


def load_protocol_scores(run: Path, hashes: dict[str, str]
                         ) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, set[int]], dict]:
    """The rows the protocol run read, read as it reads them: in time and out of time."""
    description = json.loads(hashed(run / "protocols.json", hashes).read_text(encoding="utf-8"))
    folds_dirs = [ROOT / d for d in description["folds_runs"]]
    node_dirs = [ROOT / d for d in description["in_time_tfm"]]
    out_dirs = [ROOT / d for d in description["out_of_time"]]
    for d in [*folds_dirs, *node_dirs, *out_dirs]:
        for name in ("scores.parquet", "reference.parquet"):
            hashed(d / name, hashes)
    for d in folds_dirs:
        hashed(d / "scored.parquet", hashes)
    in_scores, in_reference = pt.load_scores(folds_dirs)
    if node_dirs:
        node_scores, node_reference = pt.load_node_scores(node_dirs)
        in_scores = pd.concat([in_scores, node_scores], ignore_index=True)
        in_reference = pd.concat([in_reference, node_reference], ignore_index=True)
    pt.refuse_duplicate_keys(in_scores, in_reference)
    cells = pd.concat([pd.read_parquet(d / "scored.parquet", columns=["cohort", "row"])
                       for d in folds_dirs], ignore_index=True)
    cell_rows = {name: set(part["row"]) for name, part in cells.groupby("cohort")}
    out_scores, _ = pt.load_scores(out_dirs)
    if out_scores["build_id"].nunique() != 1 or out_scores["build_id"].iloc[0] != description[
            "build"]:
        raise SystemExit("the out-of-time scores are not the protocol run's build")
    if description.get("floors"):
        raise SystemExit("the protocol run read the floors from a build record; this figure "
                         "reads a run that did not")
    out_scores, _ = pt.floor_pooling(out_scores, description["build"], None)
    return in_scores, out_scores, cell_rows, description


def cmd_lc_protocols_reliability(args, expected: dict | None) -> dict:
    hashes: dict[str, str] = {}
    require_source("lc-protocols-reliability", args.protocols)
    run = ROOT / relative(args.protocols)
    in_scores, out_scores, cell_rows, description = load_protocol_scores(run, hashes)
    table = pd.read_csv(hashed(run / "cells.csv", hashes))
    models = list(description["models"])
    fold = int(description["folds"][0])
    cohorts = sorted(out_scores["cohort"].unique())
    test = in_scores[in_scores["part"] == "test"]

    # The rows drawn are the rows the run read: every model's AUC, Brier score and observed
    # over expected on the fold's test cell, and their means over the cohorts out of time, on
    # its first draw, as cells.csv records them. AUC alone would not tell a model at 1.0 from
    # the same model at 0.9, which rank alike; the two calibration columns do.
    worst = 0.0
    checked = 0
    for model in models:
        cell = pt.first_cell(test, model, cell_rows[f"fold{fold}-test"])
        seeds = cell["context_seed"].dropna().unique()
        seed = None if not seeds.size else int(min(seeds))
        mine = table[(table["model"] == model)
                     & (table["context_seed"].isna() if seed is None
                        else table["context_seed"] == seed)]
        frames = {"in time": [cell]}
        rows = {"in time": one_row(mine[(mine["protocol"] == pt.IN_TIME)
                                        & (mine["unit"] == f"fold {fold}")],
                                   f"{model} in time, fold {fold}")}
        if model in set(out_scores["model"]):
            part = pt.first_cell(out_scores, model)
            frames["out of time"] = [c.sort_values("row") for _, c in part.groupby("cohort")]
            rows["out of time"] = one_row(
                mine[(mine["protocol"] == pt.OUT_OF_TIME)
                     & (mine["unit"] == f"{len(cohorts)} cohorts, threshold of fold {fold}")],
                f"{model} out of time")
        for where, parts in frames.items():
            for column, statistic in CHECKED_COLUMNS.items():
                value = float(np.mean([statistic(c["outcome"].to_numpy(),
                                                 c["pd"].to_numpy(dtype=float)) for c in parts]))
                gap = abs(float(rows[where][column]) - value)
                worst = max(worst, gap)
                checked += 1
                if not gap <= TOLERANCE:
                    raise SystemExit(f"{model} {where}: the rows read give {column} {value!r}, "
                                     f"{relative(run)} records {rows[where][column]!r}")

    # Three square panels to a line; each panel's legend under its axis label.
    columns = min(3, len(models))
    lines = math.ceil(len(models) / columns)
    left, right, gap = 0.55, 0.05, 0.42
    head_h = pt_(TEXT_PT * 1.3) + 0.06
    xlabel = "mean predicted probability in the bin"
    legend_h = pt_(TEXT_PT * 1.45 * 3) + 0.1
    title_text = wrap_title("reliability, ten quantile bins: the in-time test cell and the "
                            "youngest and oldest cohort out of time")
    top = pt_(TITLE_PT * 1.3 * lines_in(title_text)) + 0.1
    side = (PRINT_WIDTH - left - right - gap * (columns - 1)) / columns
    foot_h = pt_(TICK_PT * 1.3) + pt_(TEXT_PT * 1.3 * lines_in(wrap(xlabel, side))) + 0.08
    if top + lines * (head_h + side + foot_h + legend_h) > PRINT_HEIGHT:
        side = (PRINT_HEIGHT - top) / lines - head_h - foot_h - legend_h
        foot_h = (pt_(TICK_PT * 1.3) + pt_(TEXT_PT * 1.3 * lines_in(wrap(xlabel, side)))
                  + 0.08)
        side = (PRINT_HEIGHT - top) / lines - head_h - foot_h - legend_h
        gap = (PRINT_WIDTH - left - right - columns * side) / max(1, columns - 1)
    row_h = head_h + side + foot_h + legend_h
    height = top + lines * row_h
    fig = plt.figure(figsize=(PRINT_WIDTH, height))
    curves = bins = 0
    for k, model in enumerate(models):
        line, column = divmod(k, columns)
        x0 = left + column * (side + gap)
        y0 = height - top - line * row_h - head_h - side
        ax = axes_at(fig, x0, y0, side, side, height)
        colour = bi.model_colour(model)
        high = 0.0
        sets = [("in time, test cell", "-", pt.first_cell(test, model,
                                                           cell_rows[f"fold{fold}-test"]))]
        if model in set(out_scores["model"]):
            sets += [(f"out of time, {cohorts[0]}", "--",
                      pt.first_cell(out_scores[out_scores["cohort"] == cohorts[0]], model)),
                     (f"out of time, {cohorts[-1]}", ":",
                      pt.first_cell(out_scores[out_scores["cohort"] == cohorts[-1]], model))]
        for label, style, frame in sets:
            if frame.empty:
                continue
            curve = mt.reliability(frame["outcome"].to_numpy(), frame["pd"].to_numpy(dtype=float))
            xs, ys = np.array(curve.mean_score), np.array(curve.observed)
            ax.errorbar(xs, ys, yerr=[ys - np.array(curve.lo), np.array(curve.hi) - ys],
                        color=colour, linestyle=style, marker="o", markersize=1.8, capsize=1.2,
                        linewidth=0.8, elinewidth=0.6, capthick=0.6, label=label)
            high = max(high, float(np.nanmax(np.array(curve.hi))), float(np.nanmax(xs)))
            curves += 1
            bins += int(np.isfinite(xs).sum())
        limit = high * 1.05 if high > 0 else 1.0
        ax.plot([0, limit], [0, limit], color="black", linewidth=0.6, linestyle=":")
        ax.set_xlim(0, limit)
        ax.set_ylim(0, limit)
        ax.set_title(bi.describe(model), fontsize=TEXT_PT)
        ax.set_xlabel(wrap(xlabel, side), fontsize=TEXT_PT)
        ax.tick_params(labelsize=TICK_PT)
        if column == 0:
            ax.set_ylabel(wrap("observed default rate, binomial interval", side + 0.3),
                          fontsize=TEXT_PT)
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=TEXT_PT, loc="upper left",
                  bbox_to_anchor=(0.0, -(foot_h + 0.02) / side), borderaxespad=0)
    fig.suptitle(title_text, fontsize=TITLE_PT, y=1 - 0.05 / height, va="top")
    fig.savefig(args.out_dir / "reliability-protocols.png", dpi=DPI)
    plt.close(fig)
    found = {"panels": len(models), "curves": curves, "youngest": cohorts[0],
             "oldest": cohorts[-1], "fold": fold}
    check_expected(found, expected)
    write_outputs(args.out_dir, {
        "figure": "reliability-protocols.png", "source": relative(run), **found,
        "bins_drawn": bins, "models": models,
        "check": {"rows": f"{', '.join(CHECKED_COLUMNS)} in time on the test cell of fold {fold} "
                          "and their means over the cohorts out of time, first context draw, "
                          "every model",
                  "values_checked": checked, "largest_difference": worst,
                  "tolerance": TOLERANCE}}, hashes)
    return found


# --- the command -----------------------------------------------------------------------------


COMMANDS = {"lc-auc-age": cmd_lc_auc_age, "fm-build-rows": cmd_fm_build_rows,
            "fm-between-arm-rows": cmd_fm_between_arm_rows,
            "lc-protocols-reliability": cmd_lc_protocols_reliability}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="figure", required=True)
    for name in ("lc-auc-age", "fm-build-rows", "fm-between-arm-rows"):
        p = sub.add_parser(name)
        p.add_argument("--pooling", type=Path, required=True,
                       help="the recorded pooling that drew the figure")
        p.add_argument("--out-dir", type=Path, required=True)
    p = sub.add_parser("lc-protocols-reliability")
    p.add_argument("--protocols", type=Path, required=True,
                   help="the recorded protocol run that drew the figure")
    p.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source = args.protocols if args.figure == "lc-protocols-reliability" else args.pooling
    require_source(args.figure, source)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    with plt.rc_context(PRINT_RC):
        found = COMMANDS[args.figure](args, EXPECTED.get(args.figure))
    for key, value in found.items():
        print(f"{key:<32}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
