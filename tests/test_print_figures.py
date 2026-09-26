"""The four figures drawn again at print size: each subcommand draws from small recorded runs
built here, reproduces what they hold, prints legibly at 6.5 inches, and refuses a source the
claim gate refuses.

Every test runs inside a repository of its own under `tmp_path`: a script whose hash the
synthetic manifests pin, and the recorded runs the figures read. Where a test reads what a
figure drew, it reads the figure's artists, and the values it compares them with are computed
here, not by the functions under test.
"""

from __future__ import annotations

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
from matplotlib.collections import LineCollection
from matplotlib.patches import Polygon, Rectangle
from scipy.stats import rankdata

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import print_figures as pf
import record_run as rr

TOOL = "scripts/tool.py"
SEEDS = (20260911, 20260912, 20260913)


# --- a repository of the test's own -----------------------------------------------------


@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / "scripts").mkdir()
    monkeypatch.setattr(pf, "ROOT", tmp_path)
    monkeypatch.setattr(pf, "EXPECTED", {})
    monkeypatch.setattr(pf, "SOURCES", {})
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


def recorded(root: Path, name: str, kind: str, monkeypatch, *, changed: bool = False) -> Path:
    """A recorded run whose manifest pins the tool, unchanged unless `changed`, named as the
    source of figure `kind`."""
    path = root / TOOL
    if not path.exists():
        path.write_text("x = 2\n", encoding="utf-8")
    run = root / "experiments" / name
    run.mkdir(parents=True, exist_ok=True)
    manifest = {"command": ["python", TOOL], "git_dirty": False, "exit_code": 0,
                "input_sha256": {},
                "code_sha256": {TOOL: "0" * 64 if changed else rr.file_hash(path)}}
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setitem(pf.SOURCES, kind, f"experiments/{name}")
    return run


def main(*argv) -> int:
    return pf.main([str(a) for a in argv])


def summary(out: Path) -> dict:
    return json.loads((out / "summary.json").read_text(encoding="utf-8"))


def auc(y: np.ndarray, s: np.ndarray) -> float:
    ranks = rankdata(s)
    positives = int(y.sum())
    negatives = y.size - positives
    return float((ranks[y == 1].sum() - positives * (positives + 1) / 2)
                 / (positives * negatives))


def within_slope(age: np.ndarray, value: np.ndarray, group: np.ndarray) -> float:
    """Least squares of value on age with one intercept per group, written out here."""
    cross = square = 0.0
    for g in set(group):
        pick = group == g
        a = age[pick] - age[pick].mean()
        cross += float(a @ (value[pick] - value[pick].mean()))
        square += float(a @ a)
    return cross / square


def band(ax) -> tuple[float, float]:
    """The y extent of the one shaded band of an axis."""
    spans = [p for p in ax.patches if isinstance(p, (Polygon, Rectangle))]
    assert len(spans) == 1
    span = spans[0]
    if isinstance(span, Rectangle):
        return float(span.get_y()), float(span.get_y() + span.get_height())
    ys = span.get_xy()[:, 1]
    return float(min(ys)), float(max(ys))


def flat(pairs) -> list[float]:
    return [float(v) for pair in pairs for v in pair]


# --- the rows of Freddie Mac's arm ------------------------------------------------------------


BUILDS = ["2002H2-E", "2004H2-E", "2006H2-E"]
ROWS_METRICS = (("auc_slope_build", "gbm-50k"), ("cox_slope_deviation", "scorecard"),
                ("psi", "gbm-50k"), ("psi_first_cohort", "gbm-50k"))


def rows_value(metric: str, pair: str, scope: str) -> tuple[float, float, float]:
    """A distinct value and interval for every row, so that a row read in the wrong place shows."""
    v = (zlib.crc32(f"{metric}|{pair}|{scope}".encode()) % 1000) / 1000 - 0.5
    return v, v - 0.1, v + 0.1


def fm_rows_run(repo: Path, monkeypatch, *, changed: bool = False, drop: str | None = None
                ) -> Path:
    run = recorded(repo, "fm-arm", "fm-build-rows", monkeypatch, changed=changed)
    models = {"scorecard": [], "gbm-50k": list(SEEDS), "tabpfn": list(SEEDS),
              "tabicl": list(SEEDS)}
    (run / "intervals.json").write_text(json.dumps(
        {"builds": {b: [] for b in BUILDS}, "models": models}), encoding="utf-8")
    rows = []
    for metric, against in ROWS_METRICS:
        for m in ("tabpfn", "tabicl"):
            pair = f"{m} - {against}"
            for scope in ["arm", *BUILDS]:
                if (metric, pair, scope) == drop:
                    continue
                v, lo, hi = rows_value(metric, pair, scope)
                rows.append({"cohorts": "all", "draw": np.nan, "scope": scope, "metric": metric,
                             "pair": pair, "is_difference": True, "value": v, "ci_lo": lo,
                             "ci_hi": hi})
    # A row of another pooling and one with a draw held fixed, which the figure does not read.
    rows.append({**rows[0], "cohorts": "nearest", "value": 9.0})
    rows.append({**rows[1], "draw": SEEDS[0], "value": 9.0})
    pd.DataFrame(rows).to_csv(run / "paired.csv", index=False)
    return run


def test_fm_build_rows_draws_every_build_row_and_the_arm_band_as_recorded(
        repo, monkeypatch, drawn):
    run = fm_rows_run(repo, monkeypatch)
    out = repo / "out"
    assert main("fm-build-rows", "--pooling", run, "--out-dir", out) == 0
    s = summary(out)
    assert (s["panels"], s["builds"], s["build_rows"], s["arm_rows"]) == (8, 3, 24, 8)
    fig = drawn["build-rows.png"]
    # One line of panels per metric, the models in the pooling's order.
    expected_panels = [(m, f"{t} - {a}") for m, a in ROWS_METRICS for t in ("tabpfn", "tabicl")]
    assert s["panels_drawn"] == [f"{m} | {p}" for m, p in expected_panels]
    for ax, (metric, pair) in zip(fig.axes, expected_panels, strict=True):
        assert " ".join(ax.get_title().split()).endswith(pair)
        assert [t.get_text() for t in ax.get_xticklabels()] == BUILDS
        dots = next(ln for ln in ax.lines if ln.get_label() == "one build")
        assert list(dots.get_ydata()) == pytest.approx(
            [rows_value(metric, pair, b)[0] for b in BUILDS])
        segments = next(c for c in ax.collections if isinstance(c, LineCollection))
        assert flat(seg[:, 1] for seg in segments.get_segments()) == pytest.approx(
            flat(rows_value(metric, pair, b)[1:] for b in BUILDS))
        whole = rows_value(metric, pair, "arm")
        pooled = next(ln for ln in ax.lines if ln.get_label() == "arm, pooled")
        assert list(pooled.get_ydata()) == pytest.approx([whole[0]] * 2)
        assert band(ax) == pytest.approx(whole[1:])
    assert sorted(t.get_text() for t in fig.legends[0].get_texts()) == ["arm, pooled",
                                                                          "one build"]


def test_fm_build_rows_refuses_a_changed_source_another_run_and_a_missing_row(
        repo, monkeypatch):
    run = fm_rows_run(repo, monkeypatch, changed=True)
    with pytest.raises(SystemExit, match="the claim gate refuses it"):
        main("fm-build-rows", "--pooling", run, "--out-dir", repo / "out")
    # Refused before anything is written: not even the output directory.
    assert not (repo / "out").exists()
    run = fm_rows_run(repo, monkeypatch)
    other = repo / "experiments" / "other"
    other.mkdir()
    with pytest.raises(SystemExit, match="is not experiments/fm-arm"):
        main("fm-build-rows", "--pooling", other, "--out-dir", repo / "out")
    run = fm_rows_run(repo, monkeypatch, drop=("psi", "tabicl - gbm-50k", BUILDS[1]))
    with pytest.raises(SystemExit, match="no row for 2004H2-E"):
        main("fm-build-rows", "--pooling", run, "--out-dir", repo / "out")


# --- the rows between the arms -----------------------------------------------------------------


DATES = ["2004H2", "2006H2", "2008H2", "2010H2"]
SHARES = {"2004H2": 0.5485, "2006H2": 0.3548, "2008H2": 0.2594, "2010H2": 0.2075}


def between_run(repo: Path, monkeypatch, *, changed: bool = False) -> Path:
    run = recorded(repo, "between", "fm-between-arm-rows", monkeypatch, changed=changed)
    (run / "summary.json").write_text(json.dumps(
        {"build_dates": DATES, "contrast": {d: {"share_held": v} for d, v in SHARES.items()}}),
        encoding="utf-8")
    rows = []
    for m in ("tabicl@t1", "scorecard", "tabpfn", "gbm"):
        for scope in ["arm", "builds", "pre-flag", *DATES]:
            v, lo, hi = rows_value("h4", m, scope)
            rows.append({"cohorts": "all", "draw": np.nan, "scope": scope, "kind": "h4",
                         "model": m, "value": v, "ci_lo": lo, "ci_hi": hi})
        v, lo, hi = rows_value("reduction", m, "arm")
        rows.append({"cohorts": "all", "draw": np.nan, "scope": "arm", "kind": "reduction",
                     "model": m, "value": v, "ci_lo": lo, "ci_hi": hi})
    pd.DataFrame(rows).to_csv(run / "paired.csv", index=False)
    return run


def test_between_arm_rows_draws_each_date_with_its_share_and_the_pooled_band(
        repo, monkeypatch, drawn):
    run = between_run(repo, monkeypatch)
    out = repo / "out"
    assert main("fm-between-arm-rows", "--pooling", run, "--out-dir", out) == 0
    s = summary(out)
    assert (s["panels"], s["dates"], s["date_rows"], s["pooled_rows"]) == (4, 4, 16, 4)
    # The recorded figure's order: the models of the study's order, then the tagged ones.
    assert s["models"] == ["scorecard", "gbm", "tabpfn", "tabicl@t1"]
    fig = drawn["build-rows.png"]
    labels = ["2004H2\nholds 55%", "2006H2\nholds 35%", "2008H2\nholds 26%", "2010H2\nholds 21%"]
    for ax, model in zip(fig.axes, s["models"], strict=True):
        assert [t.get_text() for t in ax.get_xticklabels()] == labels
        dots = next(ln for ln in ax.lines if ln.get_label() == "one build date")
        assert list(dots.get_ydata()) == pytest.approx(
            [rows_value("h4", model, d)[0] for d in DATES])
        assert band(ax) == pytest.approx(rows_value("h4", model, "arm")[1:])
        assert "minus the control" in ax.get_title()
    title = " ".join(fig._suptitle.get_text().split())
    assert title.endswith("the share of the expanding pool the rolling window holds")


def test_between_arm_rows_refuses_a_changed_source(repo, monkeypatch):
    run = between_run(repo, monkeypatch, changed=True)
    with pytest.raises(SystemExit, match="the claim gate refuses it"):
        main("fm-between-arm-rows", "--pooling", run, "--out-dir", repo / "out")


# --- AUC against age on Lending Club -----------------------------------------------------------


# Two builds of one arm: the cohorts each scores, with their age in quarters there.
ARM_BUILDS = {"2013H1-E": {"2013Q3": 1, "2013Q4": 2, "2014Q1": 3},
              "2013H2-E": {"2014Q1": 1, "2014Q2": 2}}
CELL_ROWS = 400


def cohort_outcome(cohort: str) -> np.ndarray:
    rng = np.random.default_rng(zlib.crc32(cohort.encode()))
    y = rng.binomial(1, 0.2, CELL_ROWS)
    y[:2] = (0, 1)
    return y


def arm_scores(build: str, model: str, seed, cohort: str) -> np.ndarray:
    y = cohort_outcome(cohort)
    rng = np.random.default_rng(zlib.crc32(f"{build}|{model}|{seed}|{cohort}".encode()))
    return np.clip(0.1 + 0.15 * y * rng.uniform(0, 1, CELL_ROWS) + rng.uniform(0, 0.3, CELL_ROWS),
                   1e-4, 0.99)


# Three models, so that the panels stand three to a line at the width the book prints them.
LC_MODELS = (("scorecard", [None]), ("gbm", [None]), ("tabpfn", list(SEEDS)))


def lc_arm_run(repo: Path, monkeypatch, *, changed: bool = False, off_by: float = 0.0,
               tamper: bool = False) -> tuple[Path, dict]:
    """The score directories of the arm and a recorded pooling over them; returns the values
    drawn as computed here, per model and build."""
    sources, pinned = [], {}
    for build, cohorts in ARM_BUILDS.items():
        d = repo / "experiments" / f"scores-{build.lower()}"
        d.mkdir(parents=True, exist_ok=True)
        frames, refs = [], []
        for model, seeds in LC_MODELS:
            for seed in seeds:
                for cohort, age in cohorts.items():
                    frames.append(pd.DataFrame({
                        "build_id": build, "arm": "E", "model": model, "context_seed": seed,
                        "cohort": cohort, "age_quarters": age, "row": np.arange(CELL_ROWS),
                        "outcome": cohort_outcome(cohort),
                        "pd": arm_scores(build, model, seed, cohort)}))
                refs.append(pd.DataFrame({"build_id": build, "model": model,
                                          "context_seed": seed,
                                          "pd": np.linspace(0.01, 0.5, 200)}))
        scores = pd.concat(frames, ignore_index=True)
        scores["context_seed"] = scores["context_seed"].astype("Int64")
        ref = pd.concat(refs, ignore_index=True)
        ref["context_seed"] = ref["context_seed"].astype("Int64")
        scores.to_parquet(d / "scores.parquet", index=False)
        ref.to_parquet(d / "reference.parquet", index=False)
        source = d.relative_to(repo).as_posix()
        sources.append(source)
        for name in ("scores.parquet", "reference.parquet"):
            pinned[f"{source}/{name}"] = rr.file_hash(d / name)
    if tamper:
        pinned[f"{sources[0]}/scores.parquet"] = "f" * 64
    run = recorded(repo, "lc-arm", "lc-auc-age", monkeypatch, changed=changed)
    (run / "intervals.json").write_text(json.dumps({
        "sources": sources, "builds": {b: sorted(c) for b, c in ARM_BUILDS.items()},
        "models": {m: [] if s == [None] else s for m, s in LC_MODELS}, "models_dropped": []}),
        encoding="utf-8")
    (run / "inputs.json").write_text(json.dumps(pinned), encoding="utf-8")
    values: dict = {}
    rows = []
    for model, seeds in LC_MODELS:
        ages, aucs, groups = [], [], []
        for build, cohorts in ARM_BUILDS.items():
            for cohort, age in sorted(cohorts.items(), key=lambda kv: kv[1]):
                a = auc(cohort_outcome(cohort), arm_scores(build, model, seeds[0], cohort))
                values[(model, build, age)] = a
                ages.append(age)
                aucs.append(a)
                groups.append(build)
        ages_, aucs_ = np.array(ages, dtype=float), np.array(aucs)
        base = {"cohorts": "all", "scope": "arm", "pair": model, "is_difference": False}
        rows.append({**base, "draw": SEEDS[0], "metric": "gini",
                     "value": float(np.mean(2 * aucs_ - 1)) + off_by, "ci_lo": 0, "ci_hi": 0})
        rows.append({**base, "draw": SEEDS[0], "metric": "auc_slope_build",
                     "value": within_slope(ages_, aucs_, np.array(groups)), "ci_lo": 0,
                     "ci_hi": 0})
        rows.append({**base, "draw": np.nan, "metric": "auc_slope_build", "value": -0.00123,
                     "ci_lo": -0.00456, "ci_hi": 0.00078})
        # The arm's pooled slope with a draw held fixed, not the one the title prints.
        rows.append({**base, "draw": SEEDS[1], "metric": "auc_slope_build", "value": 0.5,
                     "ci_lo": 0.4, "ci_hi": 0.6})
    frame = pd.DataFrame(rows)
    frame["draw"] = frame["draw"].astype("Int64")
    frame.to_csv(run / "paired.csv", index=False)
    return run, values


def test_lc_auc_age_draws_every_cell_on_the_first_draw_and_prints_the_recorded_slope(
        repo, monkeypatch, drawn):
    run, values = lc_arm_run(repo, monkeypatch)
    out = repo / "out"
    assert main("lc-auc-age", "--pooling", run, "--out-dir", out) == 0
    s = summary(out)
    assert (s["panels"], s["builds"], s["cells"], s["points"]) == (3, 2, 5, 15)
    assert s["check"]["largest_difference"] <= 1e-12
    fig = drawn["auc-age.png"]
    panel = {ax.get_title().split("\n")[0]: ax for ax in fig.axes}
    for model, _ in LC_MODELS:
        ax = panel[model]
        for build in ARM_BUILDS:
            line = next(ln for ln in ax.lines if ln.get_label() == build)
            assert line.get_marker() == "o"
            assert list(line.get_ydata()) == pytest.approx(
                [values[(model, build, age)] for age in line.get_xdata()], abs=1e-12)
        _, _, rest = ax.get_title().partition("\n")
        # The interval stands on one line of the title.
        assert any("[-0.00456, +0.00078]" in line for line in rest.split("\n"))
        assert " ".join(rest.split()) == "slope -0.00123 [-0.00456, +0.00078] per quarter"
        dashed = next(ln for ln in ax.lines if ln.get_label().startswith("arm slope"))
        xs, ys = dashed.get_xdata(), dashed.get_ydata()
        assert (ys[1] - ys[0]) / (xs[1] - xs[0]) == pytest.approx(-0.00123)
    legend = [t.get_text() for t in fig.legends[0].get_texts()]
    assert legend == [*ARM_BUILDS, "arm slope, one intercept per build"]
    inputs = json.loads((out / "inputs.json").read_text(encoding="utf-8"))
    assert "experiments/scores-2013h1-e/scores.parquet" in inputs


def test_a_title_keeps_its_interval_on_one_line_where_plain_wrapping_would_break_it():
    # A slope title of the Lending Club figure at the width of one of its three panels.
    width = (pf.PRINT_WIDTH - 0.72 - 0.05 - 2 * 0.12) / 3
    interval = "[-0.00150, +0.00064]"
    text = f"slope -0.00046 {interval} per quarter"
    assert not any(interval in line for line in pf.wrap(text, width).split("\n"))
    wrapped = pf.unbroken(text, interval, width)
    assert any(interval in line for line in wrapped.split("\n"))
    assert " ".join(wrapped.split()) == text


def test_lc_auc_age_refuses_a_changed_source_a_score_file_it_did_not_read_and_other_values(
        repo, monkeypatch):
    run, _ = lc_arm_run(repo, monkeypatch, changed=True)
    with pytest.raises(SystemExit, match="the claim gate refuses it"):
        main("lc-auc-age", "--pooling", run, "--out-dir", repo / "out")
    run, _ = lc_arm_run(repo, monkeypatch, tamper=True)
    with pytest.raises(SystemExit, match="scores.parquet hashes to"):
        main("lc-auc-age", "--pooling", run, "--out-dir", repo / "out")
    run, _ = lc_arm_run(repo, monkeypatch, off_by=1e-6)
    with pytest.raises(SystemExit, match="gini of scorecard on draw 20260911"):
        main("lc-auc-age", "--pooling", run, "--out-dir", repo / "out")
    assert not (repo / "out" / "auc-age.png").exists()


# --- reliability under both protocols -------------------------------------------------------


PROTOCOL_MODELS = ("scorecard", "gbm-50k", "tabpfn")
OOT = {"2015Q3": 1, "2016Q1": 3, "2018Q1": 11}
OOT_ROWS = 5000


def oot_outcome(cohort: str) -> np.ndarray:
    return np.random.default_rng(zlib.crc32(cohort.encode())).binomial(1, 0.04, OOT_ROWS)


def score_of(y: np.ndarray, key: str) -> np.ndarray:
    rng = np.random.default_rng(zlib.crc32(key.encode()))
    return np.clip(0.02 + 0.04 * y * rng.uniform(0, 1, y.size) + rng.uniform(0, 0.06, y.size),
                   1e-4, 0.99)


def seeds_of(model: str) -> list:
    return [None] if model == "scorecard" else [SEEDS[1], SEEDS[0]]


def recorded_columns(frames: list[pd.DataFrame]) -> dict[str, float]:
    """AUC, Brier score and observed over expected, each the mean over the cells given,
    written out here."""
    def each(f):
        y, s = f["outcome"].to_numpy(), f["pd"].to_numpy(dtype=float)
        return auc(y, s), float(np.mean((s - y) ** 2)), float(y.mean() / s.mean())
    values = np.array([each(f) for f in frames])
    return dict(zip(("auc", "brier", "observed_over_expected"), values.mean(axis=0).tolist(),
                    strict=True))


def swapped(frame: pd.DataFrame, where: str, seed, rescale: str | None) -> pd.DataFrame:
    """TabPFN's first draw with every probability raised to a power where `rescale` says: the
    same ranks, so the same AUC, and another level, as a model at another temperature."""
    if rescale != where or seed != SEEDS[0]:
        return frame
    return frame.assign(pd=frame["pd"] ** 0.8)


def protocol_run(repo: Path, monkeypatch, *, changed: bool = False, off_by: float = 0.0,
                 rescale: str | None = None) -> tuple[Path, dict]:
    """A protocol run over one fold: the classical folds directory, a node directory for the
    foundation model, the out-of-time directory; returns the curves' inputs as built here.
    With `rescale` ("in" or "out"), TabPFN's first draw is written rescaled on that side while
    cells.csv records it as built."""
    exp = repo / "experiments"
    folds, node, oot = exp / "folds", exp / "node-tabpfn", exp / "oot"
    for d in (folds, node, oot):
        d.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(3)
    test_rows = np.arange(0, 600)
    y_test = rng.binomial(1, 0.05, test_rows.size)
    y_test[:2] = (0, 1)
    y_val = rng.binomial(1, 0.05, 300)
    frames, refs, node_frames, node_refs = [], [], [], []
    inputs = {}
    for model in PROTOCOL_MODELS:
        for seed in seeds_of(model):
            key = f"{model}|{seed}"
            test = pd.DataFrame({"model": model, "context_seed": seed, "cohort": "fold1-test",
                                 "row": test_rows, "outcome": y_test,
                                 "pd": score_of(y_test, key + "|test")})
            inputs[("in", model, seed)] = test
            if model == "tabpfn":
                val = pd.DataFrame({"model": model, "context_seed": seed,
                                    "cohort": "fold1-validation", "row": 1000 + np.arange(300),
                                    "outcome": y_val, "pd": score_of(y_val, key + "|val")})
                node_frames += [swapped(test, "in", seed, rescale), val]
                node_refs.append(pd.DataFrame({"model": model, "context_seed": seed,
                                               "row": np.arange(100),
                                               "pd": np.linspace(0.01, 0.2, 100)}))
            else:
                # A row outside the test cell, which no curve reads.
                extra = test.iloc[:1].assign(row=99999, pd=0.9)
                frames.append(pd.concat([test, extra]).assign(fold=1, part="test"))
                refs.append(pd.DataFrame({"model": model, "context_seed": seed, "fold": 1,
                                          "row": np.arange(100),
                                          "pd": np.linspace(0.01, 0.2, 100)}))
            for cohort in OOT:
                y = oot_outcome(cohort)
                inputs[("out", model, seed, cohort)] = pd.DataFrame({
                    "build_id": "2015H1-E", "model": model, "context_seed": seed,
                    "cohort": cohort, "row": np.arange(OOT_ROWS), "outcome": y,
                    "pd": score_of(y, f"{key}|{cohort}")})
    for frame_list, path in ((frames, folds / "scores.parquet"), (refs, folds / "reference.parquet"),
                             (node_frames, node / "scores.parquet"),
                             (node_refs, node / "reference.parquet")):
        frame = pd.concat(frame_list, ignore_index=True)
        frame["context_seed"] = frame["context_seed"].astype("Int64")
        frame.to_parquet(path, index=False)
    pd.DataFrame({"cohort": "fold1-test", "row": test_rows}).to_parquet(folds / "scored.parquet")
    out_frame = pd.concat([swapped(v, "out", k[2], rescale) if k[1] == "tabpfn" else v
                           for k, v in inputs.items() if k[0] == "out"], ignore_index=True)
    out_frame["context_seed"] = out_frame["context_seed"].astype("Int64")
    out_frame.to_parquet(oot / "scores.parquet", index=False)
    ref = pd.DataFrame({"build_id": "2015H1-E", "model": list(PROTOCOL_MODELS),
                        "context_seed": pd.array([None, SEEDS[0], SEEDS[0]], dtype="Int64"),
                        "pd": 0.05})
    ref.to_parquet(oot / "reference.parquet", index=False)
    run = recorded(repo, "protocols", "lc-protocols-reliability", monkeypatch, changed=changed)
    (run / "protocols.json").write_text(json.dumps({
        "build": "2015H1-E", "folds_runs": ["experiments/folds"],
        "in_time_tfm": ["experiments/node-tabpfn"], "out_of_time": ["experiments/oot"],
        "folds": [1], "models": list(PROTOCOL_MODELS)}), encoding="utf-8")
    cells = []
    for model in PROTOCOL_MODELS:
        seed = seeds_of(model)[-1] if model == "scorecard" else SEEDS[0]
        test = recorded_columns([inputs[("in", model, seed)]])
        test["auc"] += off_by
        cells.append({"protocol": "in time, random fold", "model": model, "context_seed": seed,
                      "unit": "fold 1", **test})
        cells.append({"protocol": "out of time, vintage cohorts", "model": model,
                      "context_seed": seed, "unit": f"{len(OOT)} cohorts, threshold of fold 1",
                      **recorded_columns([inputs[("out", model, seed, c)] for c in OOT])})
        # The same model's other draw, which the figure does not draw.
        if model != "scorecard":
            cells.append({**cells[-1], "context_seed": SEEDS[1], "auc": 0.1, "brier": 0.5,
                          "observed_over_expected": 3.0})
    table = pd.DataFrame(cells)
    table["context_seed"] = table["context_seed"].astype("Int64")
    table.to_csv(run / "cells.csv", index=False)
    return run, inputs


def binned(y: np.ndarray, s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Ten quantile bins written out here: each bin's mean score and observed rate."""
    edges = np.quantile(s, np.arange(1, 10) / 10)
    which = np.searchsorted(edges, s, side="right")
    return (np.array([s[which == b].mean() for b in range(10)]),
            np.array([y[which == b].mean() for b in range(10)]))


def test_reliability_draws_the_test_cell_and_the_youngest_and_oldest_cohort_on_the_first_draw(
        repo, monkeypatch, drawn):
    run, inputs = protocol_run(repo, monkeypatch)
    out = repo / "out"
    assert main("lc-protocols-reliability", "--protocols", run, "--out-dir", out) == 0
    s = summary(out)
    assert (s["panels"], s["curves"], s["youngest"], s["oldest"], s["fold"]) == (
        3, 9, "2015Q3", "2018Q1", 1)
    assert s["check"]["values_checked"] == 18
    fig = drawn["reliability-protocols.png"]
    for ax, model in zip(fig.axes, PROTOCOL_MODELS, strict=True):
        assert ax.get_title() == model
        seed = None if model == "scorecard" else SEEDS[0]
        legend = ax.get_legend()
        assert [t.get_text() for t in legend.get_texts()] == [
            "in time, test cell", "out of time, 2015Q3", "out of time, 2018Q1"]
        # The curves themselves: ten bins each, drawn as a line; the caps are markers alone.
        data = [ln for ln in ax.lines
                if len(ln.get_xdata()) == 10 and ln.get_linestyle() not in ("None", "none")]
        assert len(data) == 3
        for line, frame, style in zip(
                data, [inputs[("in", model, seed)], inputs[("out", model, seed, "2015Q3")],
                       inputs[("out", model, seed, "2018Q1")]], ("-", "--", ":"), strict=True):
            x, y = binned(frame["outcome"].to_numpy(), frame["pd"].to_numpy())
            assert list(line.get_xdata()) == pytest.approx(list(x))
            assert list(line.get_ydata()) == pytest.approx(list(y))
            assert line.get_linestyle() == style


def test_reliability_refuses_a_changed_source_and_rows_other_than_the_run_read(
        repo, monkeypatch):
    run, _ = protocol_run(repo, monkeypatch, changed=True)
    with pytest.raises(SystemExit, match="the claim gate refuses it"):
        main("lc-protocols-reliability", "--protocols", run, "--out-dir", repo / "out")
    run, _ = protocol_run(repo, monkeypatch, off_by=1e-6)
    with pytest.raises(SystemExit, match="scorecard in time: the rows read give auc"):
        main("lc-protocols-reliability", "--protocols", run, "--out-dir", repo / "out")
    assert not (repo / "out" / "reliability-protocols.png").exists()


@pytest.mark.parametrize("where", ["in", "out"])
def test_reliability_refuses_rows_that_rank_alike_at_another_level(where, repo, monkeypatch):
    """A directory of the same model at another temperature ranks every row alike, so its AUC
    is the recorded one; its Brier score and observed over expected are not."""
    run, inputs = protocol_run(repo, monkeypatch, rescale=where)
    frame = inputs[("in", "tabpfn", SEEDS[0])] if where == "in" else \
        inputs[("out", "tabpfn", SEEDS[0], "2015Q3")]
    y, s = frame["outcome"].to_numpy(), frame["pd"].to_numpy()
    assert auc(y, s ** 0.8) == pytest.approx(auc(y, s), abs=1e-15)
    side = "in time" if where == "in" else "out of time"
    with pytest.raises(SystemExit, match=f"tabpfn {side}: the rows read give brier"):
        main("lc-protocols-reliability", "--protocols", run, "--out-dir", repo / "out")
    assert not (repo / "out" / "reliability-protocols.png").exists()


def test_counts_other_than_the_entry_fixes_stop_the_run(repo, monkeypatch):
    run = fm_rows_run(repo, monkeypatch)
    monkeypatch.setitem(pf.EXPECTED, "fm-build-rows", {"panels": 16})
    with pytest.raises(SystemExit, match="panels is 8, the entry says 16"):
        pf.main(["fm-build-rows", "--pooling", str(run), "--out-dir", str(repo / "out")])


def test_the_entries_fix_the_recorded_runs_and_their_counts():
    assert pf.SOURCES == {
        "lc-auc-age": "experiments/2026-09-22-lc-arm-e-intervals",
        "fm-build-rows": "experiments/2026-09-21-fm-arm-e-intervals-refit-control",
        "fm-between-arm-rows": "experiments/2026-09-22-fm-between-arm-intervals",
        "lc-protocols-reliability": "experiments/2026-09-23-lc-2015h1e-protocols5-tfm"}
    assert pf.EXPECTED["lc-auc-age"] == {"panels": 7, "builds": 9, "cells": 99, "points": 693}
    assert pf.EXPECTED["fm-build-rows"]["panels"] == 16


# --- the print size -----------------------------------------------------------------------


def printed_texts(fig) -> list[tuple[str, float, bool, object]]:
    """Every text the figure prints: its text, size, whether it is a tick label, its extent."""
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
        ticks[id(axis.get_offset_text())] = True
    out, seen = [], set()
    for t in fig.findobj(matplotlib.text.Text):
        if id(t) in seen:
            continue
        seen.add(id(t))
        if not t.get_visible() or not t.get_text().strip() or not ticks.get(id(t), True):
            continue
        out.append((t.get_text(), t.get_fontsize(), id(t) in ticks, t.get_window_extent(renderer)))
    return out


def colliding(fig, found) -> list[tuple[str, str]]:
    slack = 0.5 * fig.dpi / 72
    return [(a, b) for i, (a, _, _, ea) in enumerate(found) for b, _, _, eb in found[i + 1:]
            if min(ea.x1, eb.x1) - max(ea.x0, eb.x0) > slack
            and min(ea.y1, eb.y1) - max(ea.y0, eb.y0) > slack]


def draw_kind(kind: str, repo: Path, monkeypatch) -> None:
    out = repo / "out"
    if kind == "fm-build-rows":
        # Every metric's panels for four foundation-model settings, the sixteen of the book.
        run = recorded(repo, "fm-arm", "fm-build-rows", monkeypatch)
        models = {"scorecard": [], "gbm-50k": list(SEEDS)}
        models.update({m: list(SEEDS) for m in ("tabicl", "tabicl@t1", "tabpfn", "tabpfn@t1")})
        builds = [f"{2002 + 2 * k}H2-E" for k in range(9)]
        (run / "intervals.json").write_text(json.dumps(
            {"builds": {b: [] for b in builds}, "models": models}), encoding="utf-8")
        rows = []
        for metric, against in ROWS_METRICS:
            for m in ("tabicl", "tabicl@t1", "tabpfn", "tabpfn@t1"):
                for scope in ["arm", *builds]:
                    v, lo, hi = rows_value(metric, m, scope)
                    scale = 0.001 if metric == "auc_slope_build" else 0.1
                    rows.append({"cohorts": "all", "draw": np.nan, "scope": scope,
                                 "metric": metric, "pair": f"{m} - {against}",
                                 "is_difference": True, "value": v * scale,
                                 "ci_lo": lo * scale, "ci_hi": hi * scale})
        pd.DataFrame(rows).to_csv(run / "paired.csv", index=False)
        main("fm-build-rows", "--pooling", run, "--out-dir", out)
    elif kind == "fm-between-arm-rows":
        run = recorded(repo, "between", "fm-between-arm-rows", monkeypatch)
        dates = [f"{2004 + 2 * k}H2" for k in range(8)]
        (run / "summary.json").write_text(json.dumps(
            {"build_dates": dates, "contrast": {d: {"share_held": 0.55 - 0.05 * k}
                                                for k, d in enumerate(dates)}}),
            encoding="utf-8")
        rows = []
        for m in ("scorecard", "gbm", "tabpfn", "tabicl", "tabicl@t1", "tabpfn@t1"):
            for scope in ["arm", *dates]:
                v, lo, hi = rows_value("h4", m, scope)
                rows.append({"cohorts": "all", "draw": np.nan, "scope": scope, "kind": "h4",
                             "model": m, "value": v, "ci_lo": lo, "ci_hi": hi})
        pd.DataFrame(rows).to_csv(run / "paired.csv", index=False)
        main("fm-between-arm-rows", "--pooling", run, "--out-dir", out)
    elif kind == "lc-auc-age":
        run, _ = lc_arm_run(repo, monkeypatch)
        main("lc-auc-age", "--pooling", run, "--out-dir", out)
    elif kind == "lc-protocols-reliability":
        run, _ = protocol_run(repo, monkeypatch)
        main("lc-protocols-reliability", "--protocols", run, "--out-dir", out)


KINDS = {"fm-build-rows": "build-rows.png", "fm-between-arm-rows": "build-rows.png",
         "lc-auc-age": "auc-age.png", "lc-protocols-reliability": "reliability-protocols.png"}


@pytest.mark.parametrize("kind", list(KINDS))
def test_every_figure_is_drawn_at_its_print_size_with_type_legible_there(
        kind, repo, monkeypatch, drawn):
    draw_kind(kind, repo, monkeypatch)
    assert sorted(drawn) == [KINDS[kind]]
    fig = drawn[KINDS[kind]]
    width, height = fig.get_size_inches()
    assert width == pytest.approx(6.5) and height <= 8.5
    found = printed_texts(fig)
    ticks = [size for _, size, tick, _ in found if tick]
    others = [(text, size) for text, size, tick, _ in found if not tick]
    assert ticks and min(ticks) >= 6.5
    assert all(size >= 7.0 for _, size in others), min(others, key=lambda o: o[1])
    # Nothing printed reaches past the page, not by a fraction of a pixel.
    page = fig.bbox
    for text, _, _, extent in found:
        assert (extent.x0 >= page.x0 and extent.y0 >= page.y0
                and extent.x1 <= page.x1 and extent.y1 <= page.y1), text
    assert colliding(fig, found) == []
    # The file is written at 300 dots per inch: its pixels are the page's inches times 300.
    image = matplotlib.image.imread(repo / "out" / KINDS[kind])
    assert image.shape[1] == round(6.5 * pf.DPI)
    assert image.shape[0] == round(height * pf.DPI)
