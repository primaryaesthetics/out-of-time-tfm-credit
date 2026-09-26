"""The registered figures: each subcommand draws its figure from small books built here,
and a recorded run the claim gate refuses is refused as a source.

Every test runs inside a repository of its own under `tmp_path`: a script
whose hash the synthetic manifests pin, the recorded runs the figures read,
the grid recordings whose source lists bind the score directories, and the
build record's two files, pinned by a recording the gate accepts. Where a test
reads what a figure drew, it reads the figure's artists before the file is
written, and the values it compares them with are computed here, not by the
functions under test.
"""

from __future__ import annotations

import hashlib
import json
import sys
import zlib
from pathlib import Path

import matplotlib
import matplotlib.figure
import numpy as np
import pandas as pd
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.collections import LineCollection, PathCollection
from matplotlib.colors import to_hex
from scipy.stats import rankdata

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import record_run as rr
import registered_figures as rf

SEEDS = (20260911, 20260912, 20260913)
TOOL = "scripts/tool.py"
BUILD = "2002H2-E"
# The cohorts of the synthetic build, with their age in quarters.
COHORTS = {"2003H1": 1, "2003H2": 3, "2007H2": 19, "2013H2": 43, "2019H1": 65, "2023H2": 83}
RATES = {"2003H1": 0.03, "2003H2": 0.05, "2007H2": 0.2, "2013H2": 0.04, "2019H1": 0.03,
         "2023H2": 0.08}
# 2019H1 is scored far below every other cohort, so that an axis range that
# leaves its curves out leaves them off the axis.
SCALE = {"2019H1": 0.005}
UNDER = {"2003H1"}
ROWS = 300


# --- a repository of the test's own -----------------------------------------------------


@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / "scripts").mkdir()
    (tmp_path / TOOL).write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(rf, "ROOT", tmp_path)
    monkeypatch.setattr(rf, "EXPECTED", {})
    monkeypatch.setattr(rf, "PINS", {})
    monkeypatch.setattr(rf, "NAMED", {})
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def drawn(monkeypatch):
    """Every figure the script saves, by file name, with its artists intact."""
    figures: dict[str, matplotlib.figure.Figure] = {}
    original = matplotlib.figure.Figure.savefig

    def keep(self, fname, *args, **kwargs):
        figures[Path(fname).name] = self
        return original(self, fname, *args, **kwargs)

    monkeypatch.setattr(matplotlib.figure.Figure, "savefig", keep)
    return figures


def recorded(root: Path, name: str, *, script: str = TOOL, changed: bool = False,
             dirty: bool = False, inputs: dict | None = None, extra: list[str] | None = None
             ) -> Path:
    """A recorded run whose manifest pins `script`, unchanged unless `changed`."""
    path = root / script
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x = 2\n", encoding="utf-8")
    run = root / "experiments" / name
    run.mkdir(parents=True, exist_ok=True)
    manifest = {"command": ["python", script, *(extra or [])], "git_dirty": dirty,
                "input_sha256": inputs or {},
                "code_sha256": {script: "0" * 64 if changed else rr.file_hash(path)}}
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return run


def rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def pin(root: Path, path: Path, monkeypatch, run: str = "pin-run") -> None:
    """Names a recording the gate accepts as pinning `path` at its present value."""
    name = rel(root, path)
    recorded(root, run, inputs={name: rr.file_hash(path)})
    monkeypatch.setitem(rf.PINS, name, f"experiments/{run}")


def lists_sources(run: Path, root: Path, dirs: list[Path]) -> Path:
    run.mkdir(parents=True, exist_ok=True)
    (run / "intervals.json").write_text(
        json.dumps({"sources": [rel(root, d) for d in dirs]}), encoding="utf-8")
    return run


def named(monkeypatch, root: Path, kind: str, run: Path) -> None:
    monkeypatch.setitem(rf.NAMED, kind, rel(root, run))


def cohort_rows(cohort: str) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(zlib.crc32(cohort.encode("utf-8")))
    return np.arange(ROWS) + 1000 * COHORTS.get(cohort, 1), rng.binomial(1, RATES[cohort], ROWS)


MODELS = (("scorecard", [None]), ("gbm", [None]), ("gbm-50k", list(SEEDS)),
          ("tabpfn", list(SEEDS)), ("tabicl", list(SEEDS)), ("tabpfn@t1", list(SEEDS)),
          ("tabicl@t1", list(SEEDS)))


def separated(y: np.ndarray, p: np.ndarray) -> np.ndarray:
    """The same probabilities, the highest given to the defaults: a cell whose Cox fit has no
    maximum to reach, and whose deciles are those of every other cell."""
    out = np.empty_like(p)
    out[np.argsort(y, kind="stable")] = np.sort(p)
    return out


def drifted(y: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Every other probability three times as high: a cell whose PSI is far above the others'
    and finite, the rest of its rows still in the reference's lowest deciles."""
    out = p.copy()
    out[::2] = np.clip(3 * p[::2], 1e-6, 0.99)
    return out


def constant(y: np.ndarray, p: np.ndarray) -> np.ndarray:
    """One probability on every row: nine of the reference's ten bins empty, an infinite PSI."""
    return np.full_like(p, 0.05)


def score_dirs(root: Path, build: str = BUILD, arm: str = "E", cohorts=COHORTS,
               rewrite: dict | None = None) -> list[Path]:
    """A build's score directories: the classical models with the reported reading beside the
    label, and the foundation models in two directories without it. Every cell and every
    reference draws its probabilities from one distribution, so no decile is empty; `rewrite`
    maps a (model, cohort) to a function that replaces that cell's probabilities."""
    rng = np.random.default_rng(zlib.crc32(build.encode("utf-8")))
    groups = {"classical": MODELS[:3], "tabpfn": (MODELS[3], MODELS[5]),
              "tabicl": (MODELS[4], MODELS[6])}
    out = []
    for group, models in groups.items():
        frames, refs = [], []
        for model, seeds in models:
            for seed in seeds:
                for cohort, age in cohorts.items():
                    rows, y = cohort_rows(cohort)
                    pd_ = np.clip((0.05 * rng.lognormal(0, 0.6, ROWS) + 0.02 * y)
                                  * SCALE.get(cohort, 1.0), 1e-6, 0.99)
                    if (model, cohort) in (rewrite or {}):
                        pd_ = rewrite[(model, cohort)](y, pd_)
                    frame =pd.DataFrame({"build_id": build, "arm": arm, "model": model,
                                          "context_seed": seed, "cohort": cohort,
                                          "age_quarters": age, "row": rows, "outcome": y,
                                          "pd": pd_})
                    if group == "classical":
                        extra = np.random.default_rng(COHORTS.get(cohort, 1)).binomial(1, 0.05,
                                                                                       ROWS)
                        frame["outcome_reported"] = np.maximum(y, extra)
                    frames.append(frame)
                refs.append(pd.DataFrame({"build_id": build, "model": model,
                                          "context_seed": seed,
                                          "pd": np.clip(0.05 * rng.lognormal(0, 0.6, 400), 1e-6,
                                                        0.99)}))
        d = root / "experiments" / f"scores-{build.lower()}-{group}"
        d.mkdir(parents=True, exist_ok=True)
        scores = pd.concat(frames, ignore_index=True)
        scores["context_seed"] = scores["context_seed"].astype("Int64")
        ref = pd.concat(refs, ignore_index=True)
        ref["context_seed"] = ref["context_seed"].astype("Int64")
        scores.to_parquet(d / "scores.parquet", index=False)
        ref.to_parquet(d / "reference.parquet", index=False)
        out.append(d)
    return out


def record_cells(root: Path, builds: dict[str, dict[str, int]], under=UNDER,
                 name: str = "cells.csv", rates: dict[str, float] | None = None) -> Path:
    """The build record's cells.csv over the builds named, with the floor verdicts of `under`
    and the rates of `rates` over those of `RATES`."""
    rows = []
    for build, cohorts in builds.items():
        for cohort in cohorts:
            rate = {**RATES, **(rates or {})}.get(cohort, 0.01)
            rows.append({"build_id": build, "arm": build[-1], "cohort": cohort,
                         "labelled": 24000, "defaults": int(rate * 24000), "rate": rate,
                         "labelled_reported": 24001, "defaults_reported": int(rate * 24000) + 9,
                         "floor": cohort not in under, "regime": rf.regime_of_half(cohort)})
    path = root / "experiments" / "builds" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def fm_setup(repo: Path, monkeypatch, cohorts=COHORTS, under=UNDER) -> tuple[list[Path], Path]:
    """The Freddie Mac score directories, the grid recording that lists them, the pinned record."""
    dirs = score_dirs(repo, cohorts=cohorts)
    named(monkeypatch, repo, "fm-grid", lists_sources(repo / "experiments" / "fm-grid", repo,
                                                      dirs))
    cells = record_cells(repo, {BUILD: cohorts}, under=under)
    pin(repo, cells, monkeypatch)
    return dirs, cells


def main(*argv) -> int:
    return rf.main([str(a) for a in argv])


def summary(out: Path) -> dict:
    return json.loads((out / "summary.json").read_text(encoding="utf-8"))


def points(ax, *, open_: bool) -> int:
    """How many scatter markers an axis holds with a white face (open) or not."""
    total = 0
    for c in ax.collections:
        if not isinstance(c, PathCollection):
            continue
        faces = c.get_facecolor()
        if len(c.get_offsets()) == 0 or len(faces) == 0:
            continue
        white = bool(np.all(faces[:, :3] == 1.0) and np.all(faces[:, 3] > 0))
        if white == open_:
            total += len(c.get_offsets())
    return total


def texts(fig) -> str:
    out = [fig._suptitle.get_text() if fig._suptitle else ""]
    out += [t.get_text() for t in fig.texts]
    for legend in [*fig.legends, *(ax.get_legend() for ax in fig.axes)]:
        if legend is not None:
            out += [t.get_text() for t in legend.get_texts()]
    # Each text with its lines joined: a text wrapped to the width it is printed at reads the
    # same as unwrapped.
    return "\n".join(" ".join(t.split()) for t in out)


# --- statistics computed here, not by the module under test ---------------------------------


def auc(y: np.ndarray, s: np.ndarray) -> float:
    ranks = rankdata(s)
    positives = int(y.sum())
    negatives = y.size - positives
    return float((ranks[y == 1].sum() - positives * (positives + 1) / 2)
                 / (positives * negatives))


def cox_slope(y: np.ndarray, p: np.ndarray) -> float:
    """Newton's method from (0, 1); NaN where it does not settle."""
    x = np.log(p / (1 - p))
    design = np.column_stack([np.ones_like(x), x])
    beta = np.array([0.0, 1.0])
    with np.errstate(all="ignore"):
        for _ in range(100):
            mu = 1 / (1 + np.exp(-design @ beta))
            try:
                step = np.linalg.solve(design.T @ (design * (mu * (1 - mu))[:, None]),
                                       design.T @ (y - mu))
            except np.linalg.LinAlgError:
                return float("nan")
            beta = beta + step
            if not np.isfinite(beta).all():
                return float("nan")
            if np.abs(step).max() < 1e-12:
                return float(beta[1])
    return float("nan")


def psi(reference: np.ndarray, current: np.ndarray) -> float:
    cuts = np.quantile(reference, np.arange(1, 10) / 10)
    r = np.bincount(np.searchsorted(cuts, reference, side="right"), minlength=10) / reference.size
    c = np.bincount(np.searchsorted(cuts, current, side="right"), minlength=10) / current.size
    with np.errstate(divide="ignore"):
        return float(np.sum((c - r) * np.log(c / r)))


# --- the claim gate as the source rule -----------------------------------------------------


def test_a_run_the_gate_accepts_is_read_and_one_it_refuses_is_not(repo):
    good = recorded(repo, "good")
    rf.require_accepted(good)
    for name, kwargs in (("changed", {"changed": True}), ("dirty", {"dirty": True})):
        with pytest.raises(SystemExit, match="the claim gate refuses it"):
            rf.require_accepted(recorded(repo, name, **kwargs))
    unpinned = recorded(repo, "unpinned")
    manifest = json.loads((unpinned / "manifest.json").read_text(encoding="utf-8"))
    manifest["code_sha256"] = {}
    (unpinned / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(SystemExit, match="does not pin it"):
        rf.require_accepted(unpinned)


def test_a_statistics_source_the_gate_refuses_stops_the_figure(repo):
    run = recorded(repo, "in-sample", changed=True)
    level_tables(run)
    with pytest.raises(SystemExit, match="the claim gate refuses it"):
        main("level", "--in-sample", run, "--out-dir", repo / "out")
    assert not (repo / "out" / "level-prevalence.png").exists()


def test_the_build_record_is_read_only_at_the_value_an_accepted_run_pins(repo, monkeypatch):
    path = repo / "experiments" / "builds" / "cells.csv"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"a,b\r\n1,2\r\n")
    hashes: dict[str, str] = {}
    with pytest.raises(SystemExit, match="no recording the claim gate accepts"):
        rf.check_pin(path, hashes)
    # The pin is the hash of the file as the repository stores it, with LF endings.
    lf = hashlib.sha256(b"a,b\n1,2\n").hexdigest()
    recorded(repo, "pinning", inputs={"experiments/builds/cells.csv": lf})
    monkeypatch.setitem(rf.PINS, "experiments/builds/cells.csv", "experiments/pinning")
    rf.check_pin(path, hashes)
    assert hashes == {"experiments/builds/cells.csv": lf}
    path.write_bytes(b"a,b\r\n1,3\r\n")
    with pytest.raises(SystemExit, match="hashes to"):
        rf.check_pin(path, {})
    recorded(repo, "pinning", changed=True, inputs={"experiments/builds/cells.csv": lf})
    with pytest.raises(SystemExit, match="the claim gate refuses it"):
        rf.check_pin(path, {})


def test_inputs_other_than_the_entry_fixes_stop_the_run():
    rf.check_expected({"cells": 426}, {"cells": 426})
    rf.check_expected({"cells": 1}, None)
    with pytest.raises(SystemExit, match="cells is 425, the entry says 426"):
        rf.check_expected({"cells": 425}, {"cells": 426})


# --- axes --------------------------------------------------------------------------------


def test_log_ticks_are_1_2_5_of_each_decade_in_plain_decimals():
    assert rf.decade_ticks(0.0015, 0.06) == pytest.approx([0.002, 0.005, 0.01, 0.02, 0.05])
    assert [rf.plain(t) for t in (0.0002, 0.05, 1.0, 0.001)] == ["0.0002", "0.05", "1", "0.001"]
    assert rf.margin_range([0.01, 0.0, np.nan, 0.1], 1.4) == pytest.approx((0.01 / 1.4, 0.14))


def test_a_narrow_range_is_labelled_at_every_integer_of_the_decade():
    # 0.0119 to 0.048 holds one of the 1, 2, 5 ticks, 0.02: every integer 2 to 4 instead.
    assert rf.decade_ticks(0.0119, 0.048) == pytest.approx([0.02, 0.03, 0.04])
    # Across a decade boundary, the integers of both decades that fall inside.
    assert rf.decade_ticks(0.0085, 0.035) == pytest.approx([0.009, 0.01, 0.02, 0.03])
    # Three or more of the 1, 2, 5 ticks inside: the rule is unchanged.
    assert rf.decade_ticks(8.5e-6, 0.26) == pytest.approx(
        [1e-5, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2])
    assert rf.decade_ticks(0.0045, 0.06) == pytest.approx([0.005, 0.01, 0.02, 0.05])
    assert [rf.plain(t) for t in rf.decade_ticks(0.0119, 0.048)] == ["0.02", "0.03", "0.04"]


def test_the_ridge_bins_sit_on_multiples_of_the_width_and_an_outlier_lands_in_the_end_bin():
    values = np.r_[np.full(998, 0.01), 1e-6, 0.9]
    lo, hi = rf.ridge_range([values])
    for edge in (lo, hi):
        assert abs(edge / rf.BIN_WIDTH - round(edge / rf.BIN_WIDTH)) < 1e-9
    edges = np.round(np.arange(-3.0, -1.0 + rf.BIN_WIDTH / 2, rf.BIN_WIDTH), 10)
    d = rf.density(values, edges)
    assert d.sum() * rf.BIN_WIDTH == pytest.approx(1.0)
    assert d[0] > 0 and d[-1] > 0
    with pytest.raises(SystemExit, match="zero or below"):
        rf.density(np.array([0.0, 0.1]), edges)


# --- the ridges ----------------------------------------------------------------------------


def lc_setup(repo: Path, monkeypatch) -> tuple[list[Path], Path]:
    dirs = score_dirs(repo)
    grid = lists_sources(recorded(repo, "grid"), repo, dirs)
    named(monkeypatch, repo, "lc-grid", grid)
    return dirs, grid


def test_lc_ridge_draws_every_model_at_every_cohort(repo, monkeypatch):
    dirs, grid = lc_setup(repo, monkeypatch)
    out = repo / "out"
    assert main("lc-ridge", *dirs, "--psi-run", grid, "--out-dir", out) == 0
    s = summary(out)
    assert (out / "ridge.png").is_file()
    assert s["columns"] == len(rf.COLUMNS) and s["rows"] == len(COHORTS)
    assert s["training_rows"] == 400 and s["draw_rows"] == 400
    inputs = json.loads((out / "inputs.json").read_text(encoding="utf-8"))
    assert len(inputs) == 2 * len(dirs) + 1


def test_lc_ridge_reads_only_the_named_grid_recording_and_its_sources(repo, monkeypatch):
    dirs, grid = lc_setup(repo, monkeypatch)
    other = lists_sources(recorded(repo, "other-grid"), repo, dirs)
    with pytest.raises(SystemExit, match="the recording the log entry names"):
        main("lc-ridge", *dirs, "--psi-run", other, "--out-dir", repo / "out")
    with pytest.raises(SystemExit, match="not the sources"):
        main("lc-ridge", *dirs[:2], "--psi-run", grid, "--out-dir", repo / "out")
    with pytest.raises(SystemExit, match="not the sources"):
        main("lc-ridge", *reversed(dirs), "--psi-run", grid, "--out-dir", repo / "out")
    recorded(repo, "grid", changed=True)
    with pytest.raises(SystemExit, match="the claim gate refuses it"):
        main("lc-ridge", *dirs, "--psi-run", grid, "--out-dir", repo / "out")


def filled_rows(ax) -> set[float]:
    """The baselines of the rows drawn with a fill."""
    return {float(p.get_data().baseline) for p in ax.patches
            if type(p).__name__ == "StepPatch" and p.get_fill()}


def test_fm_ridge_puts_the_youngest_on_top_and_the_reference_row_as_its_outline(
        repo, monkeypatch, drawn):
    dirs, cells = fm_setup(repo, monkeypatch)
    out = repo / "out"
    assert main("fm-ridge", *dirs, "--cells", cells, "--out-dir", out) == 0
    s = summary(out)
    assert s["first_cohort"] == "2003H1" and s["under_floors"] == ["2003H1"]
    n = len(COHORTS)
    youngest = min(COHORTS, key=COHORTS.get)
    for name, reference_row in (("ridge-training.png", False), ("ridge-first-cohort.png", True)):
        fig = drawn[name]
        for ax in fig.axes:
            expected = set(range(n - 1 if reference_row else n))
            assert filled_rows(ax) == {float(b) for b in expected}, name
        labels = fig.axes[0].get_yticklabels()
        assert labels[-1].get_text().startswith(youngest), name
        assert labels[0].get_text() == max(COHORTS, key=COHORTS.get), name
        styles = {t.get_text().split(",")[0]: t.get_fontstyle() for t in labels}
        assert styles[youngest] == "italic" and styles["2007H2"] == "normal"
    assert drawn["ridge-first-cohort.png"].axes[0].get_yticklabels()[-1].get_text() == \
        "2003H1, the reference"
    assert "under the floors: scored, pooled into nothing" in texts(drawn["ridge-training.png"])
    assert "(label in italics)" not in texts(drawn["ridge-training.png"])


def test_fm_ridge_draws_its_two_figures_at_one_panel_width(repo, monkeypatch, drawn):
    dirs, cells = fm_setup(repo, monkeypatch)
    assert main("fm-ridge", *dirs, "--cells", cells, "--out-dir", repo / "out") == 0
    training, first = drawn["ridge-training.png"], drawn["ridge-first-cohort.png"]
    assert len(training.axes) == len(first.axes)
    for a, b in zip(training.axes, first.axes, strict=True):
        assert a.get_xlim() == b.get_xlim()
        wa = a.get_position().width * training.get_figwidth()
        wb = b.get_position().width * first.get_figwidth()
        assert wa == pytest.approx(wb)
        assert a.get_position().x0 == pytest.approx(b.get_position().x0)


def decile_marks(ax) -> list[np.ndarray]:
    """The x of the decile marks of each row of a ridge panel."""
    return [np.sort([seg[0][0] for seg in c.get_segments()]) for c in ax.collections
            if isinstance(c, LineCollection)]


def test_fm_ridge_fills_the_rows_under_the_floors_lighter_and_bins_the_second_at_2003h1(
        repo, monkeypatch, drawn):
    dirs, cells = fm_setup(repo, monkeypatch, under={"2003H1", "2013H2"})
    out = repo / "out"
    assert main("fm-ridge", *dirs, "--cells", cells, "--out-dir", out) == 0
    order = sorted(COHORTS, key=COHORTS.get)
    n = len(order)
    lighter = {float(n - 1 - order.index(c)) for c in ("2003H1", "2013H2")}
    for ax in drawn["ridge-training.png"].axes:
        alpha = {float(p.get_data().baseline): p.get_alpha() for p in ax.patches
                 if type(p).__name__ == "StepPatch" and p.get_fill()}
        assert set(alpha) == {float(b) for b in range(n)}
        assert {b for b, a in alpha.items() if a == pytest.approx(0.22)} == lighter
        assert {b for b, a in alpha.items() if a == pytest.approx(0.6)} == set(alpha) - lighter
    scores = pd.concat([pd.read_parquet(d / "scores.parquet") for d in dirs])
    reference = pd.concat([pd.read_parquet(d / "reference.parquet") for d in dirs])
    tenths = np.arange(1, 10) / 10
    for model, training, first in zip(rf.COLUMNS, drawn["ridge-training.png"].axes,
                                      drawn["ridge-first-cohort.png"].axes, strict=True):
        seed = None if model in rf.FIXED else SEEDS[0]

        def own(frame, model=model, seed=seed):
            return frame[(frame["model"] == model)
                         & (frame["context_seed"].isna() if seed is None
                            else frame["context_seed"] == seed)]["pd"].to_numpy(dtype=float)

        cohort = own(scores[scores["cohort"] == "2003H1"])
        for marks, values in ((decile_marks(training), own(reference)),
                              (decile_marks(first), cohort)):
            assert len(marks) == n
            for row in marks:
                assert row == pytest.approx(np.log10(np.quantile(values, tenths))), model


def test_fm_ridge_refuses_a_build_record_at_another_value_and_other_directories(
        repo, monkeypatch):
    dirs, cells = fm_setup(repo, monkeypatch)
    with pytest.raises(SystemExit, match="not the sources"):
        main("fm-ridge", *dirs[1:], "--cells", cells, "--out-dir", repo / "out")
    table = pd.read_csv(cells)
    table.loc[0, "defaults"] += 1
    table.to_csv(cells, index=False)
    with pytest.raises(SystemExit, match="hashes to"):
        main("fm-ridge", *dirs, "--cells", cells, "--out-dir", repo / "out")


# --- reliability ---------------------------------------------------------------------------


def test_reliability_reads_both_label_readings_on_one_axis(repo, monkeypatch, drawn):
    dirs, cells = fm_setup(repo, monkeypatch)
    out = repo / "out"
    assert main("reliability", *dirs, "--cells", cells, "--out-dir", out) == 0
    s = summary(out)
    base = pd.read_parquet(dirs[0] / "scores.parquet")
    base = base[(base["model"] == "scorecard") & (base["cohort"] == "2019H1")]
    assert s["rows_2019H1"] == ROWS
    assert s["defaults_2019H1"] == int(base["outcome"].sum())
    assert s["reported_2019H1"] == int(base["outcome_reported"].sum())
    assert s["span"] == round(0.2 / 0.03, 1)
    assert s["span_above_floors"] == round(0.2 / 0.04, 1)
    four, both = drawn["reliability.png"], drawn["reliability-2019h1.png"]
    low, high = s["axis"]
    # One axis for every panel of both figures, and every 2019H1 curve inside it.
    for fig in (four, both):
        for ax in fig.axes[:len(rf.COLUMNS)]:
            assert ax.get_xlim() == pytest.approx((low, high))
            assert ax.get_ylim() == pytest.approx((low, high))
    xs = np.concatenate([line.get_xdata() for ax in both.axes[:len(rf.COLUMNS)]
                         for line in ax.lines if len(line.get_xdata()) == 10])
    assert xs.min() >= low and xs.max() <= high
    assert xs.min() < 0.001
    # The other draws are thin lines without markers.
    for fig in (four, both):
        for ax in fig.axes[:len(rf.COLUMNS)]:
            thin = [line for line in ax.lines if line.get_alpha() == pytest.approx(0.45)]
            assert all(line.get_marker() in ("None", "", None) for line in thin)
    assert len([line for line in four.axes[3].lines
                if line.get_alpha() == pytest.approx(0.45)]) == 2 * 4
    # The cohort under the floors has open markers, the others filled.
    faces = {}
    for line in four.axes[0].lines:
        if line.get_marker() == "o":
            faces[to_hex(line.get_color())] = to_hex(line.get_markerfacecolor())
    assert faces[rf.COHORT_COLOUR["2003H1"].lower()] == "#ffffff"
    assert faces[rf.COHORT_COLOUR["2007H2"].lower()] == rf.COHORT_COLOUR["2007H2"].lower()
    for fig in (four, both):
        assert "a bin with no default" in texts(fig)


def test_reliability_draws_only_the_sources_the_named_grid_recording_lists(repo, monkeypatch):
    dirs, cells = fm_setup(repo, monkeypatch)
    for other in (list(reversed(dirs)), [*dirs, dirs[0]]):
        with pytest.raises(SystemExit, match="not the sources"):
            main("reliability", *other, "--cells", cells, "--out-dir", repo / "out")
    assert not (repo / "out" / "reliability.png").exists()


def zero_bins(y: np.ndarray, s: np.ndarray) -> list[float]:
    """The mean probability of each of ten quantile bins that holds no default."""
    which = np.searchsorted(np.quantile(s, np.arange(1, 10) / 10), s, side="right")
    return sorted(float(s[which == b].mean()) for b in range(10)
                  if (which == b).any() and y[which == b].sum() == 0)


def test_reliability_puts_a_bin_with_no_default_on_the_lower_edge_for_the_first_draw_alone(
        repo, monkeypatch, drawn):
    dirs, cells = fm_setup(repo, monkeypatch)
    out = repo / "out"
    assert main("reliability", *dirs, "--cells", cells, "--out-dir", out) == 0
    low = summary(out)["axis"][0]
    scores = pd.concat([pd.read_parquet(d / "scores.parquet") for d in dirs])
    other_draws = 0
    for model, ax in zip(rf.COLUMNS, drawn["reliability.png"].axes, strict=False):
        expected = []
        for cohort in rf.RELIABILITY_COHORTS:
            own = scores[(scores["model"] == model) & (scores["cohort"] == cohort)]
            for k, seed in enumerate([None] if model in rf.FIXED else SEEDS):
                cell = own[own["context_seed"].isna() if seed is None
                           else own["context_seed"] == seed].sort_values("row")
                zeros = zero_bins(cell["outcome"].to_numpy(), cell["pd"].to_numpy(dtype=float))
                if k == 0:
                    expected += zeros
                else:
                    other_draws += len(zeros)
        marks = [xy for c in ax.collections if isinstance(c, PathCollection)
                 for xy in c.get_offsets()]
        assert sorted(float(x) for x, _ in marks) == pytest.approx(sorted(expected)), model
        assert all(y == pytest.approx(low) for _, y in marks), model
        assert expected, model
    # The other draws hold bins with no default too, and none of them is marked.
    assert other_draws > 0


def test_reliability_legend_states_each_rate_as_the_entry_does_and_marks_2003h1_open(
        repo, monkeypatch, drawn):
    dirs, cells = fm_setup(repo, monkeypatch)
    # The rates the build record gives the four cohorts of 2002H2-E.
    table = pd.read_csv(cells, dtype={"cohort": str})
    for cohort, rate in (("2003H1", 0.002966), ("2007H2", 0.064021), ("2013H2", 0.005923),
                         ("2023H2", 0.014598)):
        table.loc[table["cohort"] == cohort, "rate"] = rate
    table.to_csv(cells, index=False)
    pin(repo, cells, monkeypatch)
    out = repo / "out"
    assert main("reliability", *dirs, "--cells", cells, "--out-dir", out) == 0
    s = summary(out)
    assert (s["span"], s["span_above_floors"]) == (21.6, 10.8)
    legend = drawn["reliability.png"].axes[len(rf.COLUMNS)].get_legend()
    entries = {" ".join(t.get_text().split()): h
               for t, h in zip(legend.get_texts(), legend.legend_handles, strict=True)}
    faces = {text.split(",")[0]: to_hex(h.get_markerfacecolor()) for text, h in entries.items()}
    assert set(entries) >= {f"2003H1, 0.297% ({rf.UNDER})", "2007H2, 6.40%", "2013H2, 0.592%",
                            "2023H2, 1.46%"}
    assert faces["2003H1"] == "#ffffff"
    for cohort in ("2007H2", "2013H2", "2023H2"):
        assert faces[cohort] == rf.COHORT_COLOUR[cohort].lower()


def test_the_reported_reading_is_refused_where_a_row_does_not_join(repo):
    scores = pd.DataFrame({"cohort": ["a", "a", "a"], "row": [1, 2, 3], "outcome": [0, 1, 0],
                           rf.REPORTED: [0.0, 1.0, np.nan]})
    joined = rf.join_reported(scores.iloc[:2].copy())
    assert list(joined[rf.REPORTED]) == [0, 1]
    with pytest.raises(SystemExit, match="cannot be joined"):
        rf.join_reported(scores)
    bad = pd.DataFrame({"cohort": ["a", "a"], "row": [1, 1], "outcome": [0, 1],
                        rf.REPORTED: [0.0, np.nan]})
    with pytest.raises(SystemExit, match="primary label differs"):
        rf.join_reported(bad)


# --- the build grid and the relief share ------------------------------------------------------


SPAN = [f"{y}H{h}" for y in range(2010, 2016) for h in (1, 2)]


def builds_json(root: Path, *, regimes_wrong: bool = False, blind_r: int = 950,
                regimes_reversed: bool = False) -> Path:
    cohorts = {c: {"rate": 0.01} for c in ["2009H1", "2009H2", *SPAN]}
    regimes: dict[str, list[str]] = {}
    for c in cohorts:
        regimes.setdefault(rf.regime_of_half(c), []).append(c)
    if regimes_wrong:
        regimes["pre-flag"].append("2012H1")
    if regimes_reversed:
        regimes = {name: held[::-1] for name, held in regimes.items()}

    def build(bid, arm, as_of, train, blind, cells, rate):
        return {"build_id": bid, "arm": arm, "as_of": as_of, "train_quarters": train,
                "pool": {"rate": rate}, "blind_rows": blind, "cells": cells}

    arms = {"E": [build("2011H2-E", "E", "2011-12-31", ["2009Q1", "2009Q2", "2009Q3"], 900,
                        SPAN[4:], 0.012),
                  build("2013H2-E", "E", "2013-12-31", ["2009Q1", "2009Q2", "2009Q3", "2009Q4",
                                                       "2010Q1", "2010Q2", "2010Q3"], 950,
                        SPAN[8:], 0.011)],
            "R": [build("2013H2-R", "R", "2013-12-31", ["2010Q2", "2010Q3"], blind_r, SPAN[8:],
                        0.02)]}
    # The first date has no rolling build, its window reaching before the first cohort.
    data = {"parameters": {"window": 24}, "cohorts": cohorts, "arms": arms, "regimes": regimes,
            "skipped": [{"as_of": "2011-12-31", "arm": "R", "reason": "a reason"}]}
    path = root / "experiments" / "builds" / "builds.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def grid_inputs(repo: Path, monkeypatch, **kwargs) -> tuple[Path, Path]:
    builds = builds_json(repo, **kwargs)
    # 2015H2 has the highest rate of every cell, so that it sits at the top of each panel's
    # data, under the reason the 2011-12-31 panel prints at its top right.
    cells = record_cells(repo, {"2011H2-E": SPAN[4:], "2013H2-E": SPAN[8:],
                                "2013H2-R": SPAN[8:]}, under={"2012H1"},
                         rates={"2015H2": 0.05})
    pin(repo, builds, monkeypatch, "pin-builds")
    pin(repo, cells, monkeypatch, "pin-cells")
    return builds, cells


def test_build_grid_draws_what_each_build_knew_and_its_blind_rows(repo, monkeypatch, drawn):
    builds, cells = grid_inputs(repo, monkeypatch)
    out = repo / "out"
    assert main("build-grid", "--builds", builds, "--cells", cells, "--out-dir", out) == 0
    s = summary(out)
    assert (s["panels"], s["blind_rows_min"], s["blind_rows_max"]) == (2, 900, 950)
    fig = drawn["build-grid.png"]
    # 2012H1, under the floors, is open on the panel that scores it and nowhere else.
    assert [points(ax, open_=True) for ax in fig.axes[:2]] == [1, 0]
    assert [points(ax, open_=False) for ax in fig.axes[:2]] == [7, 4]
    for text in ("expanding arm: its training quarters", "rolling arm: its eight training",
                 "blind quarters", "training rate, rolling arm", "900 rows"):
        assert text in texts(fig) + "\n".join(t.get_text() for ax in fig.axes
                                              for t in ax.texts), text
    # The date with no rolling build says why, in the build record's words; the other does not.
    reasons = [[t.get_text() for t in ax.texts if t.get_text().startswith("no rolling build")]
               for ax in fig.axes[:2]]
    assert reasons == [["no rolling build:\na reason"], []]


def regime_bounds(ax) -> list[float]:
    return sorted(float(ln.get_xdata()[0]) for ln in ax.lines
                  if to_hex(ln.get_color()) == "#b0392b" and ln.get_linestyle() == ":")


@pytest.mark.parametrize("regimes_reversed", [False, True])
def test_build_grid_draws_the_regime_boundaries_before_the_first_half_year_of_each(
        repo, monkeypatch, drawn, regimes_reversed):
    builds, cells = grid_inputs(repo, monkeypatch, regimes_reversed=regimes_reversed)
    assert main("build-grid", "--builds", builds, "--cells", cells, "--out-dir",
                repo / "out") == 0
    # 2009H1 is at 0 on the axis: straddling starts at 2011H2, 5, and flagged at 2014H1, 10.
    for ax in drawn["build-grid.png"].axes[:2]:
        assert regime_bounds(ax) == [4.5, 9.5]


def test_build_grid_refuses_regimes_other_than_the_setting_s_and_blind_rows_that_differ(
        repo, monkeypatch):
    builds, cells = grid_inputs(repo, monkeypatch, regimes_wrong=True)
    with pytest.raises(SystemExit, match="regime is not the Setting's"):
        main("build-grid", "--builds", builds, "--cells", cells, "--out-dir", repo / "out")
    builds, cells = grid_inputs(repo, monkeypatch, blind_r=901)
    with pytest.raises(SystemExit, match="different blind rows"):
        main("build-grid", "--builds", builds, "--cells", cells, "--out-dir", repo / "out")


QUARTERS = [f"{y}Q{q}" for y in range(2010, 2016) for q in (1, 2, 3, 4)]


def structure_run(root: Path, changed: bool = False) -> Path:
    run = recorded(root, "structure", changed=changed)
    by_quarter = {}
    for i, q in enumerate(QUARTERS):
        defaults = 100 + i
        outside = defaults if q < "2012Q2" else defaults - 10 - i
        by_quarter[q] = {"defaults": defaults, "defaults_outside_relief": outside,
                         "share_under_relief": round(1 - outside / defaults, 4)}
    (run / "summary.json").write_text(json.dumps(
        {"windows": {"24": {"defaults_under_relief_by_quarter": by_quarter}}}), encoding="utf-8")
    return run


def relief_expected() -> dict:
    """The gap the figure's caption states, worked out from the synthetic counts by hand."""
    gaps = {}
    for k, half in enumerate(SPAN):
        d = o = 0
        for i in (2 * k, 2 * k + 1):
            d += 100 + i
            o += 100 + i if QUARTERS[i] < "2012Q2" else 100 + i - 10 - i
        gaps[half] = abs((1 - o / d) - (1 - 240 / 249))
    worst = max(gaps, key=gaps.get)
    return {"quarters": 24, "criterion_cells": 20, "criterion_E": 11, "criterion_R": 9,
            "max_gap": round(gaps[worst], 4), "max_gap_half": worst, "first_nonzero": "2012Q2"}


def relief_inputs(repo: Path, monkeypatch, changed: bool = False,
                  under: set[str] | None = None) -> list:
    builds = builds_json(repo)
    cells = record_cells(repo, {"2011H2-E": SPAN, "2011H2-R": SPAN[2:]},
                         under=under or {"2012H1"})
    pin(repo, builds, monkeypatch, "pin-builds")
    pin(repo, cells, monkeypatch, "pin-cells")
    run = structure_run(repo, changed=changed)
    sensitivity = recorded(repo, "sensitivity")
    named(monkeypatch, repo, "structure", run)
    named(monkeypatch, repo, "sensitivity", sensitivity)
    return ["relief-share", "--structure", run, "--sensitivity", sensitivity, "--cells", cells,
            "--builds", builds]


def test_relief_share_reads_the_quarters_counts_the_criterion_cells_and_states_the_gap(
        repo, monkeypatch, drawn):
    args = relief_inputs(repo, monkeypatch)
    expected = relief_expected()
    monkeypatch.setitem(rf.EXPECTED, "relief-share", expected)
    out = repo / "out"
    assert main(*args, "--out-dir", out) == 0
    s = summary(out)
    assert {k: s[k] for k in expected} == expected
    assert f"at most {expected['max_gap']} ({expected['max_gap_half']})" in texts(
        drawn["relief-share.png"])
    top = drawn["relief-share.png"].axes[0]
    # The two quarters of 2012H1, under the floors, open; the other 22 filled.
    assert (points(top, open_=True), points(top, open_=False)) == (2, 22)
    # 2012H1 is labelled as under the floors between its two quarters, and no other half-year.
    marked = [(t.get_text(), t.get_position()[0]) for t in top.texts
              if "under the floors" in t.get_text()]
    assert marked == [("2012H1 under the floors", QUARTERS.index("2012Q1") + 0.5)]
    monkeypatch.setitem(rf.EXPECTED, "relief-share", {**expected, "criterion_E": 12})
    with pytest.raises(SystemExit, match="criterion_E is 11, the entry says 12"):
        main(*args, "--out-dir", repo / "out2")


def test_relief_share_refuses_a_structure_run_the_gate_refuses_and_another_pointer(
        repo, monkeypatch):
    args = relief_inputs(repo, monkeypatch, changed=True)
    with pytest.raises(SystemExit, match="the claim gate refuses it"):
        main(*args, "--out-dir", repo / "out")
    args = relief_inputs(repo, monkeypatch)
    recorded(repo, "sensitivity", changed=True)
    with pytest.raises(SystemExit, match="experiments/sensitivity: the claim gate refuses it"):
        main(*args, "--out-dir", repo / "out")
    args = relief_inputs(repo, monkeypatch)
    other = recorded(repo, "other-sensitivity")
    args[args.index("--sensitivity") + 1] = other
    with pytest.raises(SystemExit, match="the recording the log entry names"):
        main(*args, "--out-dir", repo / "out")


# --- metric against age -----------------------------------------------------------------------


def grid_run(root: Path, name: str, dirs: list[Path], shift: float = 0.0) -> Path:
    """A grid recording as metric-age reads it: its sources and a metrics.csv whose values are
    computed here, on the first draw, by the functions at the top of this file."""
    run = lists_sources(root / "experiments" / name, root, dirs)
    scores = pd.concat([pd.read_parquet(d / "scores.parquet") for d in dirs], ignore_index=True)
    reference = pd.concat([pd.read_parquet(d / "reference.parquet") for d in dirs],
                          ignore_index=True)
    keep = scores["context_seed"].isna() | (scores["context_seed"] == SEEDS[0])
    records = []
    for (model, seed, cohort), cell in scores[keep].groupby(
            ["model", "context_seed", "cohort"], dropna=False):
        cell = cell.sort_values("row")
        y = cell["outcome"].to_numpy()
        s = cell["pd"].to_numpy(dtype=float)
        ref = reference[(reference["model"] == model)
                        & (reference["context_seed"].isna() if pd.isna(seed)
                           else reference["context_seed"] == seed)]["pd"].to_numpy(dtype=float)
        for metric, value in (("auc", auc(y, s)), ("cox_slope", cox_slope(y, s)),
                              ("psi", psi(ref, s))):
            records.append({"build_id": cell["build_id"].iloc[0], "model": model,
                            "context_seed": seed, "cohort": cohort, "metric": metric,
                            "value": value + shift, "ci_lo": np.nan, "ci_hi": np.nan})
    pd.DataFrame(records).to_csv(run / "metrics.csv", index=False)
    return run


COHORTS_FEW = ("2003H1", "2007H2", "2023H2")


def metric_age_inputs(repo: Path, monkeypatch, shift: float = 0.0,
                      rewrite: dict | None = None) -> list:
    few = {c: COHORTS[c] for c in COHORTS_FEW}
    e = score_dirs(repo, cohorts=few, rewrite=rewrite)
    r = score_dirs(repo, build="2004H2-R", arm="R", cohorts={"2007H2": 11, "2023H2": 75})
    cells = record_cells(repo, {BUILD: few, "2004H2-R": ["2007H2", "2023H2"]})
    pin(repo, cells, monkeypatch)
    grids = [grid_run(repo, "grid-e", e, shift), grid_run(repo, "grid-r", r, shift)]
    return ["metric-age", *grids, "--cells", cells]


def test_metric_age_draws_every_cell_as_computed_independently(repo, monkeypatch, drawn):
    out = repo / "out"
    assert main(*metric_age_inputs(repo, monkeypatch), "--out-dir", out) == 0
    s = summary(out)
    assert (s["builds"], s["cells"], s["under_floors"]) == (2, 5, 1)
    for build in (BUILD, "2004H2-R"):
        against = s["per_build"][build]["against_recorded"]
        assert against["auc"]["max_abs_difference"] < 1e-12
        assert against["psi"]["max_abs_difference"] < 1e-12
        assert against["cox_slope"]["max_abs_difference"] < 1e-7
        assert all(v["cells_unmatched"] == 0 for v in against.values())
    # The figures are the output: no table of per-cell values is written beside them.
    assert sorted(p.name for p in out.iterdir()) == sorted(
        ["inputs.json", "summary.json", *(f"metric-age-{n}.png" for n in ("auc", "cox-slope",
                                                                           "psi"))])
    assert "table" not in s and "drawn_rows" not in s
    auc_fig = drawn["metric-age-auc.png"]
    top = auc_fig.axes[0]
    assert top.get_title() == BUILD
    # 2003H1 is under the floors: open on each of the five lines; the other two cells filled.
    assert (points(top, open_=True), points(top, open_=False)) == (5, 10)
    # Ages in half-years, the quarter age halved and rounded up: 1, 10, 42 and 6, 38.
    for ax, ages in ((top, {1.0, 10.0, 42.0}), (drawn["metric-age-auc.png"].axes[-1],
                                                 {6.0, 38.0})):
        assert {float(x) for c in ax.collections if isinstance(c, PathCollection)
                for x, _ in c.get_offsets()} == ages
    # The tempered models are on the Cox slope figure alone.
    for name, lines in (("metric-age-auc.png", 5), ("metric-age-cox-slope.png", 7),
                        ("metric-age-psi.png", 5)):
        assert len([ln for ln in drawn[name].axes[0].lines
                    if ln.get_label() and not ln.get_label().startswith("_")
                    and ln.get_label() != "Cox slope 1: the calibrated scale"]) == lines, name
    assert drawn["metric-age-psi.png"].axes[0].get_yscale() == "log"
    assert drawn["metric-age-auc.png"].axes[0].get_yscale() == "linear"
    cox = texts(drawn["metric-age-cox-slope.png"])
    assert "Cox slope 1: the calibrated scale" in cox
    assert "0 model cells whose Cox fit did not converge" in cox
    assert "context draw 20260911 for GBM-50k" in texts(drawn["metric-age-psi.png"])
    # Every figure's legend carries the open marker of a cell under the floors.
    for name in ("metric-age-auc.png", "metric-age-cox-slope.png", "metric-age-psi.png"):
        legend = drawn[name].legends[0]
        entries = dict(zip((t.get_text() for t in legend.get_texts()), legend.legend_handles,
                           strict=True))
        assert to_hex(entries[rf.UNDER].get_markerfacecolor()) == "#ffffff", name


def test_metric_age_counts_the_cells_whose_cox_fit_did_not_converge(repo, monkeypatch, drawn):
    # The scorecard's scores on 2007H2 separate its defaults from the rest: no maximum.
    args = metric_age_inputs(repo, monkeypatch, rewrite={("scorecard", "2007H2"): separated})
    out = repo / "out"
    assert main(*args, "--out-dir", out) == 0
    assert summary(out)["per_build"][BUILD]["not_estimable"] == 1
    assert "1 model cells whose Cox fit did not converge" in texts(
        drawn["metric-age-cox-slope.png"])
    # The cell has its AUC, 1, and no Cox point.
    top = drawn["metric-age-cox-slope.png"].axes[0]
    line = next(ln for ln in top.lines if ln.get_label() == "scorecard")
    assert list(line.get_xdata()) == [1, 42]


def test_metric_age_stops_on_a_value_that_is_not_finite(repo, monkeypatch, drawn):
    # The GBM scores every row of 2023H2 alike: its PSI is infinite.
    args = metric_age_inputs(repo, monkeypatch, rewrite={("gbm", "2023H2"): constant})
    with pytest.raises(SystemExit, match="gbm: a psi that is not finite"):
        main(*args, "--out-dir", repo / "out")
    assert "metric-age-psi.png" not in drawn


def against_of(out: Path, build: str = BUILD) -> dict:
    return summary(out)["per_build"][build]["against_recorded"]


def test_metric_age_counts_only_a_cell_held_by_one_side_as_unmatched(repo, monkeypatch):
    # The scorecard's Cox fit on 2007H2 has no maximum on either side: a matched cell whose
    # recorded value is NaN, not an unmatched one.
    args = metric_age_inputs(repo, monkeypatch, rewrite={("scorecard", "2007H2"): separated})
    recorded_csv = repo / "experiments" / "grid-e" / "metrics.csv"
    table = pd.read_csv(recorded_csv, dtype={"cohort": str})
    nan_cox = table[(table["model"] == "scorecard") & (table["cohort"] == "2007H2")
                    & (table["metric"] == "cox_slope")]
    assert nan_cox["value"].isna().all() and len(nan_cox) == 1
    assert main(*args, "--out-dir", repo / "out") == 0
    assert {m: v["cells_unmatched"] for m, v in against_of(repo / "out").items()} == {
        "auc": 0, "cox_slope": 0, "psi": 0}
    # One AUC cell dropped from the recording and one it holds that no score directory scores,
    # and the other draws, which are not the cells computed here: two unmatched AUC cells.
    gone = (table["model"] == "gbm") & (table["cohort"] == "2023H2") & (table["metric"] == "auc")
    extra = table[gone].assign(cohort="2010H1")
    other_draw = table[table["context_seed"] == SEEDS[0]].assign(context_seed=SEEDS[1])
    pd.concat([table[~gone], extra, other_draw]).to_csv(recorded_csv, index=False)
    assert main(*args, "--out-dir", repo / "out2") == 0
    assert {m: v["cells_unmatched"] for m, v in against_of(repo / "out2").items()} == {
        "auc": 2, "cox_slope": 0, "psi": 0}


def test_metric_age_counts_every_value_finite_on_one_side_alone(repo, monkeypatch):
    # The recordings made here hold no interval; each AUC and Cox cell computed by the script
    # carries both bounds, and no PSI cell carries one on either side.
    args = metric_age_inputs(repo, monkeypatch)
    assert main(*args, "--out-dir", repo / "out") == 0
    cells = len(COHORTS_FEW) * len(MODELS)
    one_sided = {m: v["values_not_finite_on_one_side"]
                 for m, v in against_of(repo / "out").items()}
    assert one_sided == {"auc": 2 * cells, "cox_slope": 2 * cells, "psi": 0}
    # One recorded AUC value blanked: one more value finite on one side alone.
    recorded_csv = repo / "experiments" / "grid-e" / "metrics.csv"
    table = pd.read_csv(recorded_csv, dtype={"cohort": str})
    table.loc[(table["model"] == "tabpfn") & (table["cohort"] == "2023H2")
              & (table["metric"] == "auc"), "value"] = np.nan
    table.to_csv(recorded_csv, index=False)
    assert main(*args, "--out-dir", repo / "out2") == 0
    assert against_of(repo / "out2")["auc"]["values_not_finite_on_one_side"] == 2 * cells + 1
    assert against_of(repo / "out2")["auc"]["max_abs_difference"] < 1e-12


def spans(ax) -> dict[str, tuple[float, float]]:
    return {p.get_label(): (p.get_x(), p.get_x() + p.get_width()) for p in ax.patches
            if type(p).__name__ == "Rectangle" and p.get_label() in rf.MARKS}


def test_metric_age_marks_the_crisis_and_2022_cohorts_and_draws_what_each_statistic_carries(
        repo, monkeypatch, drawn):
    assert main(*metric_age_inputs(repo, monkeypatch), "--out-dir", repo / "out") == 0
    # 2007H2 lies inside the crisis mark and 2023H2 inside the 2022 mark: at 10 and 42
    # half-years on the expanding build, at 6 and 38 on the rolling one.
    for name in ("metric-age-auc.png", "metric-age-cox-slope.png", "metric-age-psi.png"):
        fig = drawn[name]
        assert spans(fig.axes[0]) == {"crisis 2007H1 to 2008H2": (9.5, 10.5),
                                      "2022H1 to 2023H2": (41.5, 42.5)}, name
        assert spans(fig.axes[-1]) == {"crisis 2007H1 to 2008H2": (5.5, 6.5),
                                       "2022H1 to 2023H2": (37.5, 38.5)}, name
    # The foundation models at 1.0 dashed in their model's colour, the models at 0.9 solid.
    cox = drawn["metric-age-cox-slope.png"].axes[0]
    style = {ln.get_label(): (ln.get_linestyle(), to_hex(ln.get_color())) for ln in cox.lines}
    for model in ("tabpfn", "tabicl"):
        tempered = f"{model}, softmax temperature 1"
        assert style[model][0] == "-" and style[tempered][0] == "--", model
        assert style[model][1] == style[tempered][1], model
    # Every AUC and Cox cell carries its interval, as a vertical bar from its lower to its
    # upper bound; no PSI cell carries one.
    for name, models in (("metric-age-auc.png", 5), ("metric-age-cox-slope.png", 7),
                         ("metric-age-psi.png", 0)):
        bars = [c for c in drawn[name].axes[0].collections if isinstance(c, LineCollection)
                and c.get_label() not in rf.MARKS]
        assert len(bars) == models, name
        for c in bars:
            segments = c.get_segments()
            assert len(segments) == len(COHORTS_FEW), name
            assert all(s[0][0] == s[1][0] and s[1][1] > s[0][1] for s in segments), name


def test_metric_age_reports_a_grid_value_it_does_not_reproduce(repo, monkeypatch):
    out = repo / "out"
    assert main(*metric_age_inputs(repo, monkeypatch, shift=0.01), "--out-dir", out) == 0
    against = summary(out)["per_build"][BUILD]["against_recorded"]
    assert against["auc"]["max_abs_difference"] == pytest.approx(0.01)
    assert against["psi"]["max_abs_difference"] == pytest.approx(0.01)


# --- the arm pooling's AUC against age -------------------------------------------------------


def auc_age_inputs(repo: Path, monkeypatch, changed: bool = False) -> tuple[list, list[Path]]:
    few = {c: COHORTS[c] for c in ("2003H1", "2007H2", "2023H2")}
    e1 = score_dirs(repo, cohorts=few)
    e2 = score_dirs(repo, build="2004H2-E", cohorts={"2007H2": 11, "2023H2": 75})
    cells = record_cells(repo, {BUILD: few, "2004H2-E": ["2007H2", "2023H2"]})
    pin(repo, cells, monkeypatch)
    dirs = [rel(repo, d) for d in (*e1, *e2)]
    pooling = recorded(repo, "pooling", script="scripts/arm_intervals.py", changed=changed,
                       extra=[*dirs, "--out-dir", "x"])
    # The recorded slope is the arm's, on every cohort, of no single draw and no difference;
    # a row that differs in any one of these carries another value.
    read = {"metric": "auc_slope_build", "is_difference": False, "scope": "arm",
            "cohorts": "all", "draw": np.nan}
    others = [{"metric": "auc_slope_pooled"}, {"is_difference": True},
              {"scope": "crisis cells"}, {"cohorts": "above floors"}, {"draw": SEEDS[1]}]
    rows = []
    for m, _ in MODELS:
        rows += [{**read, **change, "pair": m, "value": 0.25 + k, "ci_lo": 0.2 + k,
                  "ci_hi": 0.3 + k} for k, change in enumerate(others)]
        rows.append({**read, "pair": m, "value": -0.001, "ci_lo": -0.002, "ci_hi": 0.0})
    pd.DataFrame(rows).to_csv(pooling / "paired.csv", index=False)
    return ["auc-age", *dirs, "--pooling", pooling, "--cells", cells], e1


def test_auc_age_draws_the_first_draw_with_the_cells_under_the_floors_open(
        repo, monkeypatch, drawn):
    args, e1 = auc_age_inputs(repo, monkeypatch)
    out = repo / "out"
    assert main(*args, "--out-dir", out) == 0
    s = summary(out)
    assert (s["builds"], s["cells"], s["under_floors"]) == (2, 5, 1)
    fig = drawn["auc-age.png"]
    panel = {ax.get_title().split("\n")[0]: ax for ax in fig.axes}
    for model, _ in MODELS:
        # One open cell per panel, 2003H1 on 2002H2-E; four filled.
        assert (points(panel[model if "@" not in model else
                             model.replace("@t1", ", softmax temperature 1")], open_=True),
                points(panel[model if "@" not in model else
                             model.replace("@t1", ", softmax temperature 1")], open_=False)
                ) == (1, 4), model
    scores = pd.read_parquet(e1[1] / "scores.parquet")
    for seed_index, should_match in ((0, True), (2, False)):
        cell = scores[(scores["model"] == "tabpfn") & (scores["cohort"] == "2007H2")
                      & (scores["context_seed"] == SEEDS[seed_index])].sort_values("row")
        expected = auc(cell["outcome"].to_numpy(), cell["pd"].to_numpy(dtype=float))
        line = next(ln for ln in panel["tabpfn"].lines if ln.get_label() == BUILD)
        drawn_value = float(np.asarray(line.get_ydata())[
            list(np.asarray(line.get_xdata())).index(COHORTS["2007H2"])])
        assert (drawn_value == pytest.approx(expected, abs=1e-12)) is should_match
    assert "a cell under the floors: scored, entering no slope" in texts(fig)
    # Each title carries the recorded arm slope and no other row of paired.csv.
    for ax in fig.axes:
        head, _, rest = ax.get_title().partition("\n")
        assert " ".join(rest.split()) == "slope -0.00100 [-0.00200, +0.00000] per quarter", head


def test_auc_age_refuses_a_pooling_the_gate_refuses_and_other_directories(repo, monkeypatch):
    args, _ = auc_age_inputs(repo, monkeypatch, changed=True)
    with pytest.raises(SystemExit, match="the claim gate refuses it"):
        main(*args, "--out-dir", repo / "out")
    args, _ = auc_age_inputs(repo, monkeypatch)
    dirs_end = args.index("--pooling")
    with pytest.raises(SystemExit, match="not the ones"):
        main(*args[:4], *args[dirs_end:], "--out-dir", repo / "out")


# --- the level across prevalence --------------------------------------------------------------


def level_tables(run: Path, *, rows: int = 20000, defaults: int = 400,
                 zero: bool = False) -> None:
    """Three models' in-sample and cohort cells; with `zero`, the context cell of tabpfn and
    every 2007H2 cell hold no default."""
    cells, cohorts = [], []
    for model in ("scorecard", "gbm", "tabpfn"):
        kind = "context draw" if model == "tabpfn" else "training pool"
        empty = zero and model == "tabpfn"
        cells.append({"build_id": BUILD, "arm": "E", "model": model, "context_seed": np.nan,
                      "kind": kind, "rows": 50000, "defaults": 0 if empty else 600,
                      "realised_rate": 0.0 if empty else 0.012,
                      "mean_pd": 0.012 if model != "tabpfn" else 0.008})
        for cohort, rate in (("2003H1", 0.003), ("2007H2", 0.06)):
            d = 0 if zero and cohort == "2007H2" else defaults
            cohorts.append({"build_id": BUILD, "arm": "E", "model": model,
                            "context_seed": np.nan, "cohort": cohort, "rows": rows,
                            "defaults": d, "mean_pd": rate * 1.5,
                            "realised_rate": d / rows if d else 0.0})
    pd.DataFrame(cells).to_csv(run / "cells.csv", index=False)
    pd.DataFrame(cohorts).to_csv(run / "cohort-cells.csv", index=False)


def test_level_draws_every_panel_on_one_axis_and_counts_what_it_leaves_off(
        repo, monkeypatch, drawn):
    run = recorded(repo, "in-sample")
    level_tables(run, zero=True)
    cells = record_cells(repo, {BUILD: COHORTS})
    pin(repo, cells, monkeypatch)
    out = repo / "out"
    assert main("level", "--in-sample", run, "--cells", cells, "--out-dir", out) == 0
    s = summary(out)
    # Three 2007H2 cohort cells and the tabpfn context cell hold no default.
    assert s["left_off"] == 4
    assert s["under_floors"] == 3
    values = [0.012, 0.003 * 1.5, 400 / 20000]
    assert s["axis"] == pytest.approx([min(values) / rf.LEVEL_MARGIN,
                                       max(values) * rf.LEVEL_MARGIN])
    fig = drawn["level-prevalence.png"]
    title = " ".join(fig._suptitle.get_text().split())
    assert "experiments/in-sample" in title and "4 cells with no default" in title
    for ax in fig.axes[:3]:
        assert ax.get_xlim() == pytest.approx(s["axis"])
        marked = [c for c in ax.collections
                  if len(c.get_offsets()) and to_hex(c.get_edgecolor()[0]) == "#b0392b"]
        assert sum(len(c.get_offsets()) for c in marked) == 1


def test_level_without_a_build_record_refuses_a_cohort_cell_under_the_floors(repo):
    run = recorded(repo, "in-sample")
    level_tables(run)
    assert main("level", "--in-sample", run, "--out-dir", repo / "out") == 0
    assert summary(repo / "out")["under_floors"] == 0
    level_tables(run, defaults=99)
    with pytest.raises(SystemExit, match="under the floors and no build record"):
        main("level", "--in-sample", run, "--out-dir", repo / "out2")


# --- the print size -----------------------------------------------------------------------


def draw_kind(kind: str, repo: Path, monkeypatch) -> None:
    """Draws one figure kind on the books above."""
    out = repo / "out"
    if kind == "lc-ridge":
        dirs, grid = lc_setup(repo, monkeypatch)
        main("lc-ridge", *dirs, "--psi-run", grid, "--out-dir", out)
    elif kind in ("fm-ridge", "reliability"):
        dirs, cells = fm_setup(repo, monkeypatch)
        main(kind, *dirs, "--cells", cells, "--out-dir", out)
    elif kind == "relief-share":
        # Two adjacent half-years under the floors: their labels stand one half-year apart.
        main(*relief_inputs(repo, monkeypatch, under={"2012H1", "2012H2"}), "--out-dir", out)
    elif kind == "build-grid":
        builds, cells = grid_inputs(repo, monkeypatch)
        main("build-grid", "--builds", builds, "--cells", cells, "--out-dir", out)
    elif kind == "metric-age":
        # One drifted cell puts the PSI axis across more than a decade, as the grid's cells
        # span it; the cells as built above span less than one.
        main(*metric_age_inputs(repo, monkeypatch, rewrite={("gbm", "2023H2"): drifted}),
             "--out-dir", out)
    elif kind == "auc-age":
        args, _ = auc_age_inputs(repo, monkeypatch)
        main(*args, "--out-dir", out)
    elif kind == "level":
        run = recorded(repo, "in-sample")
        level_tables(run, zero=True)
        cells = record_cells(repo, {BUILD: COHORTS})
        pin(repo, cells, monkeypatch)
        main("level", "--in-sample", run, "--cells", cells, "--out-dir", out)
    elif kind == "tall-ridge":
        # A ridge as tall as the Freddie Mac build's, 42 rows, drawn by the ridge function.
        rng = np.random.default_rng(7)
        rows = [(f"{2003 + i // 2}H{1 + i % 2}" + (", the reference" if i == 0 else ""),
                 i in (0, 20, 23)) for i in range(42)]
        columns = [{"model": m, "values": [rng.uniform(1e-4, 0.25, 500) for _ in rows],
                    "reference": rng.uniform(1e-4, 0.25, 500),
                    "subtitle": "reference: context draw 20260911,\n50,000 rows"}
                   for m in rf.COLUMNS]
        edges = np.round(np.arange(-4.0, -0.6 + rf.BIN_WIDTH / 2, rf.BIN_WIDTH), 10)
        out.mkdir()
        with matplotlib.rc_context(rf.PRINT_RC):
            rf.draw_ridge(columns, rows, edges, out / "ridge-tall.png", "a tall ridge",
                          [*rf.RIDGE_NOTES, "A third note."], reference_row=0)


KINDS = {"lc-ridge": ["ridge.png"], "fm-ridge": ["ridge-training.png", "ridge-first-cohort.png"],
         "reliability": ["reliability.png", "reliability-2019h1.png"],
         "relief-share": ["relief-share.png"], "build-grid": ["build-grid.png"],
         "metric-age": [f"metric-age-{n}.png" for n in ("auc", "cox-slope", "psi")],
         "auc-age": ["auc-age.png"], "level": ["level-prevalence.png"],
         "tall-ridge": ["ridge-tall.png"]}


def printed_texts(fig) -> list[tuple[str, float, bool, object]]:
    """Every text the figure prints: its text, size, whether it is a tick label, its extent."""
    # The figure was closed once saved; a canvas of its own lays it out again.
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    renderer = canvas.get_renderer()
    ticks = {}
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            low, high = sorted(axis.get_view_interval())
            for which in ("major", "minor"):
                locs = axis.get_majorticklocs() if which == "major" else axis.get_minorticklocs()
                made = (axis.get_major_ticks(len(locs)) if which == "major"
                        else axis.get_minor_ticks(len(locs)))
                for tick, loc in zip(made, locs, strict=True):
                    shown = low - 1e-9 * abs(high) <= loc <= high + 1e-9 * abs(high)
                    for label in (tick.label1, tick.label2):
                        ticks[id(label)] = shown
    out, seen = [], set()
    for t in fig.findobj(matplotlib.text.Text):
        if id(t) in seen:
            continue
        seen.add(id(t))
        if not t.get_visible() or not t.get_text().strip() or not ticks.get(id(t), True):
            continue
        if t.axes is not None and not t.axes.get_visible():
            continue
        out.append((t.get_text(), t.get_fontsize(), id(t) in ticks, t.get_window_extent(renderer)))
    return out


# Two boxes that share less than this, in points, along either side merely touch.
TOUCH_PT = 0.5


def overlaps(a, b, slack: float) -> bool:
    return (min(a.x1, b.x1) - max(a.x0, b.x0) > slack
            and min(a.y1, b.y1) - max(a.y0, b.y0) > slack)


def colliding(fig, found) -> list[tuple[str, str]]:
    """The pairs of printed texts whose boxes overlap."""
    slack = TOUCH_PT * fig.dpi / 72
    return [(a, b) for i, (a, _, _, ea) in enumerate(found)
            for b, _, _, eb in found[i + 1:] if overlaps(ea, eb, slack)]


def covered_points(fig, starts: tuple[str, ...]) -> list[tuple[str, tuple[float, float]]]:
    """The scatter points of each axis that lie inside a text of that axis beginning with one
    of `starts`, with the text they lie in."""
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    renderer = canvas.get_renderer()
    out = []
    for ax in fig.axes:
        boxes = [(t.get_text(), t.get_window_extent(renderer)) for t in ax.texts
                 if t.get_visible() and t.get_text().startswith(starts)]
        for c in ax.collections:
            if not isinstance(c, PathCollection) or len(c.get_offsets()) == 0:
                continue
            for x, y in c.get_offset_transform().transform(c.get_offsets()):
                out += [(text, (x, y)) for text, box in boxes
                        if box.x0 <= x <= box.x1 and box.y0 <= y <= box.y1]
    return out


@pytest.mark.parametrize("kind", list(KINDS))
def test_every_figure_is_drawn_at_its_print_size_with_type_legible_there(
        kind, repo, monkeypatch, drawn):
    draw_kind(kind, repo, monkeypatch)
    assert sorted(drawn) == sorted(KINDS[kind])
    for name, fig in drawn.items():
        width, height = fig.get_size_inches()
        # The tmlr text width, and a page with its caption.
        assert width == pytest.approx(6.5) and height <= 8.5, name
        found = printed_texts(fig)
        assert found, name
        ticks = [size for _, size, tick, _ in found if tick]
        others = [(text, size) for text, size, tick, _ in found if not tick]
        assert ticks and min(ticks) >= 6.5, name
        assert all(size >= 7.0 for _, size in others), (name, min(others, key=lambda o: o[1]))
        # Nothing printed falls off the page.
        page = fig.bbox
        for text, _, _, extent in found:
            assert (extent.x0 >= page.x0 - 1 and extent.y0 >= page.y0 - 1
                    and extent.x1 <= page.x1 + 1 and extent.y1 <= page.y1 + 1), (name, text)
        # No two printed texts overlap, tick labels included.
        assert colliding(fig, found) == [], name
    if kind == "build-grid":
        # The blind rows and the reason a date has no rolling build sit clear of every rate.
        assert covered_points(drawn["build-grid.png"], ("blind", "no rolling build")) == []
