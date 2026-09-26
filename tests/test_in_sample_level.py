"""The in-sample reading, where its answer is known.

A calibrated model reads observed over expected of one on its own rows, and
the reading has to say so with an interval that holds one; a model scaled
on the logit reads the shortfall the scale implies; and H5 is near zero for
a model whose level is a constant ratio of the truth on every context and is
detected for one pulled toward a fixed prevalence. The reading also refuses
contexts that are not one context and cells that two directories hold.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("matplotlib")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import in_sample_level as isl

SEEDS = [11, 12, 13]
ROWS = 20_000


def logit(p):
    return np.log(p / (1 - p))


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def context(build: str, seed: int | None, prevalence: float, rows: int = ROWS):
    """One context draw: its rows, the true probability of each and outcomes drawn from it."""
    tag = sum(map(ord, build)) * 1000 + (seed or 0)
    rng = np.random.default_rng(tag)
    positions = np.sort(rng.choice(10_000_000, size=rows, replace=False))
    truth = sigmoid(logit(prevalence) + 0.7 * rng.normal(size=rows))
    outcome = rng.binomial(1, truth)
    return positions, truth, outcome


def write_dir(root: Path, name: str, build: str, prevalence: float, models: dict,
              seeds=SEEDS, arm: str = "E", cohorts: bool = False) -> Path:
    """A scored directory whose reference rows are each model's probability on its context."""
    directory = root / name
    directory.mkdir()
    reference, scores = [], []
    for model, (how, seeded) in models.items():
        for seed in (seeds if seeded else [None]):
            positions, truth, outcome = context(build, seed, prevalence)
            reference.append(pd.DataFrame({
                "build_id": build, "arm": arm, "as_of": "2004-12-31", "model": model,
                "context_seed": seed, "row": positions, "outcome": outcome, "pd": how(truth)}))
            if cohorts:
                rows, truth_c, outcome_c = context(build + "-cohort", 99, prevalence * 1.5, 5_000)
                scores.append(pd.DataFrame({
                    "build_id": build, "arm": arm, "as_of": "2004-12-31", "model": model,
                    "context_seed": seed, "cohort": "2005H1", "age_quarters": 1, "row": rows,
                    "outcome": outcome_c, "pd": how(truth_c)}))
    frame = pd.concat(reference, ignore_index=True)
    frame["context_seed"] = frame["context_seed"].astype("Int64")
    frame.to_parquet(directory / "reference.parquet", index=False)
    if cohorts:
        s = pd.concat(scores, ignore_index=True)
        s["context_seed"] = s["context_seed"].astype("Int64")
        s.to_parquet(directory / "scores.parquet", index=False)
    return directory


def truth(p):
    return p


def scaled(p):
    return sigmoid(logit(p) / 0.8)


def ratio(p):
    return 0.66 * p


def pulled(p):
    return 0.5 * p + 0.5 * 0.015


def run(dirs, out, *extra) -> int:
    return isl.main([*map(str, dirs), "--out-dir", str(out), "--resamples", "100", *extra])


def builds_json(root: Path, pools: dict[str, tuple[str, float]], name="builds.json") -> Path:
    """A build run's record in the shape fm-vintage-builds writes: pools by arm."""
    arms: dict[str, list] = {}
    for build, (arm, rate) in pools.items():
        arms.setdefault(arm, []).append({"build_id": build, "pool": {"rate": rate}})
    path = root / name
    path.write_text(json.dumps({"arms": arms}), encoding="utf-8")
    return path


# The pools agree with the draws: 2008H2-E the highest, 2004H2-E the lowest.
AGREEING = {"2004H2-E": ("E", 0.005), "2006H2-E": ("E", 0.015), "2008H2-E": ("E", 0.04)}


def test_a_calibrated_model_reads_one_and_a_scaled_model_its_shortfall(tmp_path):
    directory = write_dir(tmp_path, "d", "2004H2-E", 0.03,
                          {"gbm-50k": (truth, True), "tabicl": (scaled, True)}, seeds=[11])
    out = tmp_path / "out"
    assert run([directory], out) == 0
    cells = pd.read_csv(out / "cells.csv").set_index("model")
    calibrated = cells.loc["gbm-50k"]
    assert calibrated["observed_over_expected"] == pytest.approx(1.0, abs=0.08)
    assert calibrated["bootstrap_lo"] <= 1.0 <= calibrated["bootstrap_hi"]
    assert calibrated["binomial_lo"] <= 1.0 <= calibrated["binomial_hi"]
    assert bool(calibrated["bootstrap_holds_one"]) and bool(calibrated["fitted"])
    # The scale on the logit lowers every probability under a half: the level it implies is
    # the true mean over the scaled mean, and the reading holds it and not one.
    _, p, _ = context("2004H2-E", 11, 0.03)
    known = p.mean() / scaled(p).mean()
    scaled_cell = cells.loc["tabicl"]
    assert known > 1.1
    assert scaled_cell["bootstrap_lo"] <= known <= scaled_cell["bootstrap_hi"]
    assert scaled_cell["bootstrap_lo"] > 1.0
    assert not bool(scaled_cell["fitted"])
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["known_answer"]["interval_does_not_hold_one"] == []
    assert summary["h5"]["arms"]["E"]["reason"].startswith("one build")
    assert not (out / "h5.csv").exists()
    assert (out / "level-prevalence.png").is_file()


def test_h5_is_near_zero_for_a_constant_ratio_and_detected_for_a_pulled_level(tmp_path):
    models = {"gbm-50k": (truth, True), "tabicl": (ratio, True), "tabpfn": (pulled, True),
              "tabicl@t1": (truth, True), "scorecard": (truth, False)}
    dirs = [write_dir(tmp_path, "low", "2004H2-E", 0.005, models, cohorts=True),
            write_dir(tmp_path, "mid", "2006H2-E", 0.015, models, cohorts=True),
            write_dir(tmp_path, "high", "2008H2-E", 0.04, models, cohorts=True)]
    out = tmp_path / "out"
    assert run(dirs, out, "--with-cohorts", "--check-seeds", "5,6",
               "--builds-json", str(builds_json(tmp_path, AGREEING))) == 0
    h5 = pd.read_csv(out / "h5.csv")
    assert set(h5["ranking"]) == {"pool"} and h5["criterion"].all()
    diff = h5[h5["metric"] == "h5"].set_index("model")
    assert set(diff.index) == {"gbm-50k", "tabicl", "tabpfn", "tabicl@t1"}
    assert (h5["high_build"] == "2008H2-E").all() and (h5["low_build"] == "2004H2-E").all()
    # A constant ratio reads the same level at every prevalence.
    assert diff.loc["tabicl", "ci_lo"] <= 0.0 <= diff.loc["tabicl", "ci_hi"]
    assert abs(diff.loc["tabicl", "value"]) < 0.2
    # A level pulled toward 1.5% reads under one below it and over one above it.
    assert diff.loc["tabpfn", "value"] > 0.6 and bool(diff.loc["tabpfn", "excludes_zero"])
    assert bool(diff.loc["gbm-50k", "known_answer"])
    assert diff.loc["gbm-50k", "ci_lo"] <= 0.0 <= diff.loc["gbm-50k", "ci_hi"]
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    arm = summary["h5"]["arms"]["E"]
    assert arm["seeds"] == SEEDS and arm["high"] == "2008H2-E" and arm["low"] == "2004H2-E"
    assert arm["pool_rates"]["2004H2-E"] == 0.005 and arm["draw_ranking"] is None
    assert summary["h5"]["bootstrap"]["seed_check"]["seeds"] == [5, 6]
    assert summary["cohort_cells"]["cells"] == 3 * (4 * 3 + 1)
    assert (out / "h5-seeds.csv").is_file() and (out / "cohort-cells.csv").is_file()
    # Every build's pool cell of the scorecard is in the table and read as a known answer.
    cells = pd.read_csv(out / "cells.csv")
    pools = cells[cells["kind"] == "training pool"]
    assert len(pools) == 3 and pools["fitted"].all()


def test_the_criterion_ranks_by_the_pool_and_the_draws_ranking_is_reported_beside(tmp_path):
    models = {"gbm-50k": (truth, True), "tabpfn": (pulled, True)}
    dirs = [write_dir(tmp_path, "low", "2004H2-E", 0.005, models),
            write_dir(tmp_path, "mid", "2006H2-E", 0.015, models),
            write_dir(tmp_path, "high", "2008H2-E", 0.04, models)]
    # The record puts 2006H2-E's pool lowest; its draws sit above 2004H2-E's.
    pools = builds_json(tmp_path, {"2004H2-E": ("E", 0.006), "2006H2-E": ("E", 0.004),
                                   "2008H2-E": ("E", 0.04)})
    out = tmp_path / "out"
    assert run(dirs, out, "--builds-json", str(pools), "--check-seeds", "5") == 0
    h5 = pd.read_csv(out / "h5.csv")
    criterion = h5[h5["criterion"]]
    # The seed check counts the criterion's rows, and the draw ranking's apart.
    checks = json.loads((out / "summary.json").read_text(encoding="utf-8"))["h5"]["bootstrap"]
    assert checks["seed_check"]["differences"] == 2
    assert checks["seed_check_draw_ranking"]["differences"] == 2
    beside = h5[~h5["criterion"]]
    assert set(criterion["low_build"]) == {"2006H2-E"} and set(criterion["high_build"]) == {"2008H2-E"}
    assert set(beside["low_build"]) == {"2004H2-E"} and set(beside["ranking"]) == {"draws"}
    assert set(beside["cohorts"]) == {"arm E, draw ranking"}
    # The criterion's reading is the same whether or not the second reading exists.
    agree = builds_json(tmp_path, {"2004H2-E": ("E", 0.0065), "2006H2-E": ("E", 0.004),
                                   "2008H2-E": ("E", 0.04)}, name="again.json")
    alone = tmp_path / "alone"
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["h5"]["arms"]["E"]["draw_ranking"] == {"high": "2008H2-E", "low": "2004H2-E"}
    assert run(dirs, alone, "--builds-json", str(agree)) == 0
    again = pd.read_csv(alone / "h5.csv")
    pd.testing.assert_frame_equal(again[again["criterion"]].reset_index(drop=True),
                                  criterion.reset_index(drop=True))


def test_h5_is_refused_without_the_build_run_record_or_with_a_build_missing_from_it(tmp_path):
    models = {"tabicl": (ratio, True)}
    dirs = [write_dir(tmp_path, "a", "2004H2-E", 0.005, models),
            write_dir(tmp_path, "b", "2006H2-E", 0.015, models)]
    with pytest.raises(SystemExit, match="--builds-json is not given"):
        run(dirs, tmp_path / "out")
    partial = builds_json(tmp_path, {"2004H2-E": ("E", 0.005)})
    with pytest.raises(SystemExit, match="2006H2-E not in the build run's record"):
        run(dirs, tmp_path / "out", "--builds-json", str(partial))
    elsewhere = builds_json(tmp_path, {"2004H2-E": ("E", 0.005), "2006H2-E": ("R", 0.015)},
                            name="elsewhere.json")
    with pytest.raises(SystemExit, match="on another in the build run's record"):
        run(dirs, tmp_path / "out", "--builds-json", str(elsewhere))


def test_contexts_that_are_not_one_context_are_refused(tmp_path):
    good = write_dir(tmp_path, "a", "2004H2-E", 0.02, {"gbm-50k": (truth, True)}, seeds=[11])
    other = write_dir(tmp_path, "b", "2004H2-E", 0.02, {"tabicl": (ratio, True)}, seeds=[11])
    frame = pd.read_parquet(other / "reference.parquet")
    frame.loc[3, "row"] = 99_999_999
    frame.sort_values("row").to_parquet(other / "reference.parquet", index=False)
    with pytest.raises(SystemExit, match="different context rows"):
        run([good, other], tmp_path / "out")
    frame = pd.read_parquet(write_dir(tmp_path, "c", "2004H2-E", 0.02,
                                      {"tabicl": (ratio, True)}, seeds=[11]) / "reference.parquet")
    frame.loc[3, "outcome"] = 1 - frame.loc[3, "outcome"]
    frame.to_parquet(tmp_path / "c" / "reference.parquet", index=False)
    with pytest.raises(SystemExit, match="an outcome differs"):
        run([good, tmp_path / "c"], tmp_path / "out")


def test_a_cell_held_by_two_directories_is_refused(tmp_path):
    a = write_dir(tmp_path, "a", "2004H2-E", 0.02, {"tabicl": (ratio, True)}, seeds=[11])
    b = write_dir(tmp_path, "b", "2004H2-E", 0.02, {"tabicl": (ratio, True)}, seeds=[11])
    with pytest.raises(SystemExit, match="one context cell, one directory"):
        run([a, b], tmp_path / "out")


def recalibrated(directory: Path, model: str) -> None:
    """The model's pool cell replaced by its own Cox recalibration: the unpenalised logistic fit
    of the outcome on its logit, which reads slope one and intercept zero on those rows."""
    frame = pd.read_parquet(directory / "reference.parquet")
    pick = frame["model"] == model
    y, p = frame.loc[pick, "outcome"].to_numpy(), frame.loc[pick, "pd"].to_numpy()
    fit = isl.mt.cox(y, p)
    frame.loc[pick, "pd"] = sigmoid(fit.intercept + fit.slope * logit(p))
    frame.to_parquet(directory / "reference.parquet", index=False)


def test_the_in_sample_slope_reads_the_scorecard_s_known_answer_and_a_stretch(tmp_path, capsys):
    models = {"gbm-50k": (truth, True), "tabicl": (scaled, True), "scorecard": (scaled, False)}
    dirs = [write_dir(tmp_path, "low", "2004H2-E", 0.005, models),
            write_dir(tmp_path, "mid", "2006H2-E", 0.015, models),
            write_dir(tmp_path, "high", "2008H2-E", 0.04, models)]
    for directory in dirs[:2]:
        recalibrated(directory, "scorecard")
    out = tmp_path / "out"
    assert run(dirs, out, "--check-seeds", "5",
               "--builds-json", str(builds_json(tmp_path, AGREEING))) == 0
    cells = pd.read_csv(out / "cells.csv")
    pools = cells[cells["kind"] == "training pool"].set_index("build_id")
    # Recalibrated on its pool, the scorecard reads the known answer; left stretched, it does not.
    assert bool(pools.loc["2004H2-E", "slope_known_answer"])
    assert pools.loc["2004H2-E", "cox_slope"] == pytest.approx(1.0, abs=1e-6)
    assert not bool(pools.loc["2008H2-E", "slope_known_answer"])
    assert cells[cells["kind"] == "context draw"]["slope_known_answer"].isna().all()
    assert set(cells.set_index("build_id")["h5_context"].dropna().items()) == {
        ("2008H2-E", "high"), ("2004H2-E", "low")}
    printed = capsys.readouterr().out
    assert "2 of 3 scorecard pool cells read slope one" in printed
    assert "2008H2-E scorecard" in printed and "the run is wrong" in printed
    slopes = pd.read_csv(out / "in-sample-slope.csv").set_index("model")
    assert set(slopes.index) == {"gbm-50k", "tabicl"} and (slopes["builds"] == 3).all()
    # A logit stretched by 1/0.8 reads a slope near 0.8, below one beyond its interval; the
    # truth reads one inside it.
    assert slopes.loc["tabicl", "value"] == pytest.approx(0.8, abs=0.03)
    assert bool(slopes.loc["tabicl", "below_one"]) and not bool(slopes.loc["tabicl", "above_one"])
    assert slopes.loc["gbm-50k", "ci_lo"] <= 1.0 <= slopes.loc["gbm-50k", "ci_hi"]
    seeds = pd.read_csv(out / "in-sample-slope-seeds.csv")
    assert sorted(seeds["bootstrap_seed"].unique()) == [5, isl.bi.BOOTSTRAP_SEED]
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))["in_sample_slope"]
    assert summary["known_answer"]["not_within"] == ["2008H2-E scorecard"]
    assert summary["arms"]["E"]["seeds"] == SEEDS


def test_the_slope_pooling_leaves_the_h5_rows_as_they_were(tmp_path, monkeypatch):
    models = {"gbm-50k": (truth, True), "tabpfn": (pulled, True)}
    dirs = [write_dir(tmp_path, "low", "2004H2-E", 0.005, models),
            write_dir(tmp_path, "high", "2008H2-E", 0.04, models)]
    pools = builds_json(tmp_path, {"2004H2-E": ("E", 0.005), "2008H2-E": ("E", 0.04)})
    with_slope = tmp_path / "with"
    assert run(dirs, with_slope, "--builds-json", str(pools)) == 0
    monkeypatch.setattr(isl, "slope_contexts",
                        lambda cells, arm: {"arm": arm, "builds": [], "reason": "skipped",
                                            "models_not_read": {}})
    without = tmp_path / "without"
    assert run(dirs, without, "--builds-json", str(pools)) == 0
    assert not (without / "in-sample-slope.csv").exists()
    pd.testing.assert_frame_equal(pd.read_csv(with_slope / "h5.csv"), pd.read_csv(without / "h5.csv"))
    pd.testing.assert_frame_equal(pd.read_csv(with_slope / "cells.csv"),
                                  pd.read_csv(without / "cells.csv"))


def test_every_file_the_reading_reads_is_hashed(tmp_path):
    import record_run as rr

    models = {"gbm-50k": (truth, True), "tabpfn": (pulled, True), "scorecard": (truth, False)}
    dirs = [write_dir(tmp_path, "low", "2004H2-E", 0.005, models, cohorts=True),
            write_dir(tmp_path, "high", "2008H2-E", 0.04, models, cohorts=True)]
    record = builds_json(tmp_path, {"2004H2-E": ("E", 0.005), "2008H2-E": ("E", 0.04)})
    out = tmp_path / "out"
    assert run(dirs, out, "--with-cohorts", "--builds-json", str(record)) == 0
    hashed = json.loads((out / "inputs.json").read_text(encoding="utf-8"))
    read = [d / name for d in dirs for name in ("reference.parquet", "scores.parquet")]
    read.append(record)
    assert hashed == {p.as_posix(): rr.file_hash(p) for p in read}
