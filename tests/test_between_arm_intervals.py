"""The between-arm reading, on what would make its difference of differences wrong.

A difference between arms is only the window's if both arms hold the same
rows with the same outcomes on the same cohorts at the same ages; the
reading refuses when they do not, and when a directory sits on the wrong
arm. Its statistic is checked where the answer is known: identical arms
read zero with an interval that holds zero; a stretch of the logit planted
in one model on one arm is read, with its sign; and a shift of one model's
level on the logit between arms, which a context at another default rate
produces, moves the Cox slope not at all and must not fire the kill's
complement.
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

import between_arm_intervals as ba

SEED = 20260915
ROWS = 1200
# Two build dates; the first scores three half-years, the second the last two.
DATES = {"2004H2": ["2005H1", "2005H2", "2006H1"], "2005H1": ["2005H2", "2006H1"]}
MODELS = {"scorecard": [None], "gbm-50k": [11, 12], "tabpfn": [11, 12]}


@pytest.fixture(autouse=True)
def small_cohorts_clear_the_floors(monkeypatch):
    """The synthetic cohorts hold 1,200 rows, not a book's thousands; the floors are lowered
    so that they pool. tests/test_floors.py reads the floors themselves."""
    monkeypatch.setattr(ba.bi, "FLOOR_ROWS", 0)
    monkeypatch.setattr(ba.bi, "FLOOR_DEFAULTS", 0)


def latent(cohort: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One cohort's rows, a latent logit and outcomes drawn from it, the same on every build."""
    rng = np.random.default_rng(SEED + sum(map(ord, cohort)))
    rows = np.sort(rng.choice(1_000_000, size=ROWS, replace=False))
    x = rng.normal(size=ROWS)
    y = rng.binomial(1, 1.0 / (1.0 + np.exp(-(-2.2 + x))))
    return rows, x, y


def score(x: np.ndarray, stretch: float, shift: float, noise_seed: int) -> np.ndarray:
    """A score whose logit is the truth's stretched by `stretch`, shifted by `shift`, with noise.

    The true logit is -2.2 + x; a score at stretch b has a Cox slope near 1/b.
    """
    jitter = 0.15 * np.random.default_rng(noise_seed).normal(size=x.size)
    return 1.0 / (1.0 + np.exp(-(-2.2 + stretch * (x + jitter) + shift)))


def write_build(root: Path, date: str, arm: str, *, stretch: dict | None = None,
                shift: dict | None = None, arm_label: str | None = None,
                cohorts: list[str] | None = None, name: str | None = None,
                noise_of: dict | None = None) -> Path:
    """One build's score and reference files; every model's noise depends on the cohort and draw only.

    With no stretch or shift the rolling arm's scores are the expanding
    arm's, row for row. `noise_of` gives a model another model's noise, so
    that the two score alike where their stretch and shift agree.
    """
    stretch, shift, noise_of = stretch or {}, shift or {}, noise_of or {}
    build = f"{date}-{arm}"
    frames, refs = [], []
    for k, cohort in enumerate(cohorts or DATES[date]):
        rows, x, y = latent(cohort)
        halves = 2 * (int(cohort[:4]) - int(date[:4])) + int(cohort[-1]) - int(date[-1])
        age = 2 * halves - 1
        for model, seeds in MODELS.items():
            for s in seeds:
                noise = (sum(map(ord, noise_of.get(model, model))) + 31 * sum(map(ord, cohort))
                         + (s or 0))
                frames.append(pd.DataFrame({
                    "as_of": f"{date[:4]}-12-31", "arm": arm_label or arm, "build_id": build,
                    "model": model, "context_seed": s, "cohort": cohort, "age_quarters": age,
                    "row": rows, "outcome": y, "outcome_reported": y,
                    "pd": score(x, stretch.get(model, 1.0), shift.get(model, 0.0), noise)}))
    for model, seeds in MODELS.items():
        for s in seeds:
            refs.append(pd.DataFrame({"as_of": f"{date[:4]}-12-31", "arm": arm_label or arm,
                                      "build_id": build, "model": model, "context_seed": s,
                                      "pd": np.random.default_rng(7).uniform(0.02, 0.3, 300)}))
    directory = root / (name or build)
    directory.mkdir(parents=True)
    scores = pd.concat(frames, ignore_index=True)
    scores["context_seed"] = scores["context_seed"].astype("Int64")
    scores.to_parquet(directory / "scores.parquet", index=False)
    reference = pd.concat(refs, ignore_index=True)
    reference["context_seed"] = reference["context_seed"].astype("Int64")
    reference.to_parquet(directory / "reference.parquet", index=False)
    (directory / "build.json").write_text(json.dumps({
        "build": {"build_id": build, "train_rows": 200_000 if arm == "E" else 100_000},
        "ablation": None, "features": ["fico", "ltv"]}), encoding="utf-8")
    return directory


def both_arms(root: Path, rolling: dict | None = None, expanding: dict | None = None
              ) -> tuple[list[Path], list[Path]]:
    e = [write_build(root, d, "E", **(expanding or {})) for d in DATES]
    r = [write_build(root, d, "R", **(rolling or {})) for d in DATES]
    return e, r


def run(e: list[Path], r: list[Path], out: Path, *extra: str) -> int:
    return ba.main(["--expanding", *map(str, e), "--rolling", *map(str, r), "--out-dir", str(out),
                    "--resamples", "30", *extra])


def read(out: Path) -> tuple[pd.DataFrame, dict]:
    return (pd.read_csv(out / "paired.csv"),
            json.loads((out / "summary.json").read_text(encoding="utf-8")))


def pooled(paired: pd.DataFrame, kind: str) -> pd.DataFrame:
    return paired[(paired["kind"] == kind) & (paired["scope"] == "arm")
                  & (paired["cohorts"] == "all") & paired["draw"].isna()].set_index("model")


def test_identical_arms_read_zero_inside_an_interval_that_holds_zero(tmp_path):
    e, r = both_arms(tmp_path)
    out = tmp_path / "out"
    assert run(e, r, out) == 0
    paired, summary = read(out)
    differences = paired[paired["is_difference"]]
    assert set(differences["kind"]) == {"reduction", "h4"}
    assert (differences["value"] == 0).all()
    assert (differences["ci_lo"] <= 0).all() and (differences["ci_hi"] >= 0).all()
    assert not differences["excludes_zero"].astype(bool).any()
    assert summary["cells_shared"] == 5 and summary["cells_criterion"] == 5
    assert summary["criterion"]["reading"]["tabpfn"]["kill_fires"]
    assert summary["criterion"]["reading"]["tabpfn"]["reading"] == "killed: inside the interval"
    assert (out / "arm-cells.png").is_file() and (out / "build-rows.png").is_file()
    cells = pd.read_csv(out / "cells.csv")
    assert len(cells) == 5 * 5 and (cells["deviation_E"] == cells["deviation_R"]).all()


def test_a_stretch_planted_in_one_model_on_one_arm_is_read_with_its_sign(tmp_path):
    # The expanding arm stretches the foundation model's logit by 1.6, a Cox slope near
    # 0.63; the rolling arm scores it as the truth does. Every other model is the same on
    # both arms, so only the foundation model's reduction moves, and it is positive.
    e, r = both_arms(tmp_path, expanding={"stretch": {"tabpfn": 1.6}})
    out = tmp_path / "out"
    assert run(e, r, out, "--check-seeds", "5") == 0
    paired, summary = read(out)
    reduction, h4 = pooled(paired, "reduction"), pooled(paired, "h4")
    assert reduction.loc["gbm-50k", "value"] == 0 and reduction.loc["scorecard", "value"] == 0
    assert reduction.loc["tabpfn", "value"] > 0.2
    assert h4.loc["tabpfn", "value"] == pytest.approx(reduction.loc["tabpfn", "value"])
    assert h4.loc["tabpfn", "ci_lo"] > 0 and bool(h4.loc["tabpfn", "excludes_zero"])
    assert h4.loc["scorecard", "value"] == 0 and not bool(h4.loc["scorecard", "excludes_zero"])
    reading = summary["criterion"]["reading"]
    assert reading["tabpfn"]["reading"] == ba.HOLDS and not reading["tabpfn"]["kill_fires"]
    assert not reading["scorecard"]["criterion"]
    # Per build date the same sign, and the mean over dates between the two dates' values.
    rows = paired[(paired["kind"] == "h4") & (paired["model"] == "tabpfn")
                  & (paired["cohorts"] == "all") & paired["draw"].isna()].set_index("scope")
    assert (rows.loc[list(DATES), "value"] > 0).all()
    assert rows.loc["builds", "value"] == pytest.approx(rows.loc[list(DATES), "value"].mean())

    # The same stretch on the rolling arm: the window makes the drift worse, and the sign turns.
    e2, r2 = both_arms(tmp_path / "flip", rolling={"stretch": {"tabpfn": 1.6}})
    out2 = tmp_path / "out2"
    assert run(e2, r2, out2) == 0
    paired2, summary2 = read(out2)
    h4_2 = pooled(paired2, "h4")
    assert h4_2.loc["tabpfn", "value"] == pytest.approx(-h4.loc["tabpfn", "value"])
    assert h4_2.loc["tabpfn", "ci_hi"] < 0
    assert summary2["criterion"]["reading"]["tabpfn"]["reading"].startswith(
        "killed: the reduction is smaller")


def test_a_level_shift_between_arms_does_not_fire(tmp_path):
    # The dry run the kill's complement owes: the rolling arm moves the foundation
    # model's every score by +0.9 on the logit, the ratio of a 4.5% context to a 1.8%
    # one, and nothing else. Brier and O/E move a great deal; the Cox slope does not
    # move, so no row of the statistic moves and the criterion reads the kill.
    e, r = both_arms(tmp_path, rolling={"shift": {"tabpfn": 0.9}})
    out = tmp_path / "out"
    assert run(e, r, out, "--check-seeds", "5,6") == 0
    paired, summary = read(out)
    cells = pd.read_csv(out / "cells.csv")
    tabpfn = cells[cells["model"] == "tabpfn"]
    assert np.abs(tabpfn["deviation_E"] - tabpfn["deviation_R"]).max() < 1e-8
    h4 = pooled(paired, "h4")
    assert abs(h4.loc["tabpfn", "value"]) < 1e-8
    assert not paired[paired["kind"] == "h4"]["excludes_zero"].astype(bool).any()
    assert summary["criterion"]["reading"]["tabpfn"]["kill_fires"]
    seeds = pd.read_csv(out / "paired-seeds.csv")
    assert not seeds[seeds["pair"].str.startswith("tabpfn - ")]["excludes_zero"].astype(bool).any()


def test_an_arm_effect_shared_with_the_control_reads_zero(tmp_path):
    # The must-not-fire case of the difference of differences: the expanding arm stretches
    # the control's logit and the foundation model's alike, on the same noise. Each reduction
    # is large, the model's equals the control's, and h4 is zero in every resample.
    twin = {"tabpfn": "gbm-50k"}
    e, r = both_arms(tmp_path, expanding={"stretch": {"gbm-50k": 1.6, "tabpfn": 1.6},
                                          "noise_of": twin}, rolling={"noise_of": twin})
    out = tmp_path / "out"
    assert run(e, r, out, "--check-seeds", "5") == 0
    paired, summary = read(out)
    reduction, h4 = pooled(paired, "reduction"), pooled(paired, "h4")
    assert reduction.loc["gbm-50k", "value"] > 0.2
    assert reduction.loc["tabpfn", "value"] == reduction.loc["gbm-50k", "value"]
    assert (h4.loc["tabpfn", ["value", "ci_lo", "ci_hi"]] == 0).all()
    assert summary["criterion"]["reading"]["tabpfn"]["reading"] == "killed: inside the interval"

    # A level shift of the foundation model on the expanding arm besides: the Cox slope does
    # not see it, and h4 stays at zero to the precision of the fit.
    e2, r2 = both_arms(tmp_path / "shift", expanding={
        "stretch": {"gbm-50k": 1.6, "tabpfn": 1.6}, "shift": {"tabpfn": 0.9}, "noise_of": twin},
        rolling={"noise_of": twin})
    assert run(e2, r2, tmp_path / "out2") == 0
    h4_2 = pooled(read(tmp_path / "out2")[0], "h4")
    assert np.abs(h4_2.loc["tabpfn", ["value", "ci_lo", "ci_hi"]].to_numpy(dtype=float)).max() < 1e-8


def test_h4_is_the_model_s_reduction_minus_the_control_s(tmp_path):
    # Both drift on the expanding arm, by different stretches: the control's reduction is not
    # zero, and h4 is the difference of the two reductions read off the cell table by hand.
    e, r = both_arms(tmp_path, expanding={"stretch": {"gbm-50k": 1.3, "tabpfn": 1.6}})
    out = tmp_path / "out"
    assert run(e, r, out) == 0
    paired, _ = read(out)
    cells = pd.read_csv(out / "cells.csv")
    hand = {m: float((cells.loc[cells["model"] == m, "deviation_E"]
                      - cells.loc[cells["model"] == m, "deviation_R"]).mean())
            for m in ("tabpfn", "gbm-50k", "scorecard")}
    reduction, h4 = pooled(paired, "reduction"), pooled(paired, "h4")
    assert hand["gbm-50k"] > 0.05 and hand["tabpfn"] > hand["gbm-50k"]
    for model, value in hand.items():
        assert reduction.loc[model, "value"] == pytest.approx(value, abs=1e-12)
    assert h4.loc["tabpfn", "value"] == pytest.approx(hand["tabpfn"] - hand["gbm-50k"], abs=1e-12)
    assert h4.loc["scorecard", "value"] == pytest.approx(-hand["gbm-50k"], abs=1e-12)


def test_an_expanding_build_with_no_rolling_build_is_left_out_and_named(tmp_path):
    e, r = both_arms(tmp_path)
    early = write_build(tmp_path, "2002H2", "E", cohorts=["2005H1", "2005H2"])
    out = tmp_path / "out"
    assert run([early, *e], r, out) == 0
    _, summary = read(out)
    assert summary["builds_left_out"] == ["2002H2-E"]
    assert summary["build_dates"] == list(DATES)


def test_floors_and_regimes_from_the_build_run(tmp_path):
    # The foundation model drifts on the expanding arm on 2005H1 and 2005H2 and on the
    # rolling arm on 2006H1: the two regimes read opposite signs.
    e = [write_build(tmp_path, d, "E") for d in DATES]
    r = [write_build(tmp_path, d, "R") for d in DATES]
    for directory, arm in [*((p, "E") for p in e), *((p, "R") for p in r)]:
        scores = pd.read_parquet(directory / "scores.parquet")
        hit = (scores["model"] == "tabpfn") & scores["cohort"].isin(
            ["2005H1", "2005H2"] if arm == "E" else ["2006H1"])
        logit = np.log(scores.loc[hit, "pd"] / (1 - scores.loc[hit, "pd"]))
        scores.loc[hit, "pd"] = 1 / (1 + np.exp(-(-2.2 + 1.6 * (logit + 2.2))))
        scores.to_parquet(directory / "scores.parquet", index=False)
    regime = {"2005H1": "pre-flag", "2005H2": "pre-flag", "2006H1": "flagged"}
    table = pd.DataFrame([{"build_id": f"{d}-{arm}", "cohort": c, "floor": True,
                           "regime": regime[c]}
                          for d, cs in DATES.items() for c in cs for arm in "ER"])
    table.to_csv(tmp_path / "cells.csv", index=False)
    out = tmp_path / "out"
    assert run(e, r, out, "--cells", str(tmp_path / "cells.csv")) == 0
    paired, summary = read(out)
    rows = paired[(paired["kind"] == "h4") & (paired["model"] == "tabpfn")
                  & (paired["cohorts"] == "all") & paired["draw"].isna()].set_index("scope")
    assert rows.loc["pre-flag", "value"] > 0 > rows.loc["flagged", "value"]
    entry = summary["criterion"]["reading"]["tabpfn"]
    # Kill criterion 4: disagreeing signs make the verdict undetermined, the arm row's kept beside.
    assert entry["regimes_disagree_in_sign"] is True
    assert entry["reading"] == ba.UNDETERMINED and entry["kill_fires"] is None
    assert entry["reading_on_arm_row"].startswith("killed") and entry["kill_fires_on_arm_row"] is True
    # The scope difference is the pre-flag row minus the flagged row, on the same resample.
    diff = paired[(paired["kind"] == ba.SCOPE_DIFFERENCE) & (paired["model"] == "tabpfn")
                  & (paired["cohorts"] == "all") & paired["draw"].isna()]
    assert len(diff) == 1 and diff["scope"].iloc[0] == ba.SCOPE_CONTRAST
    assert diff["value"].iloc[0] == pytest.approx(
        rows.loc["pre-flag", "value"] - rows.loc["flagged", "value"], abs=1e-12)
    # Every file read is hashed.
    hashed = json.loads((out / "inputs.json").read_text(encoding="utf-8"))
    assert any(k.endswith("scores.parquet") for k in hashed) and any(k.endswith("cells.csv") for k in hashed)

    # A cohort under the floors leaves every criterion pooling and stays in the cell table.
    table.loc[table["cohort"] == "2006H1", "floor"] = False
    table.to_csv(tmp_path / "cells.csv", index=False)
    out2 = tmp_path / "out2"
    assert run(e, r, out2, "--cells", str(tmp_path / "cells.csv")) == 0
    paired2, summary2 = read(out2)
    assert summary2["cells_criterion"] == 3 and summary2["cohorts_under_floors"] == ["2006H1"]
    assert "flagged" not in set(paired2["scope"])
    assert len(pd.read_csv(out2 / "cells.csv")) == 5 * 5
    table.iloc[:-1].to_csv(tmp_path / "short.csv", index=False)
    with pytest.raises(SystemExit, match="holds no row"):
        run(e, r, tmp_path / "out3", "--cells", str(tmp_path / "short.csv"))


def test_a_cell_whose_cox_fit_did_not_finish_leaves_both_arms(tmp_path, monkeypatch):
    real = ba.mt.cox

    def cox(outcome, s, **kw):
        if np.all(np.asarray(s) > 0.9):
            nan = float("nan")
            return ba.mt.Cox(nan, nan, nan, nan, False, ba.mt.ALPHA, 100)
        return real(outcome, s, **kw)

    monkeypatch.setattr(ba.mt, "cox", cox)
    e, r = both_arms(tmp_path)
    scores = pd.read_parquet(r[0] / "scores.parquet")
    hit = (scores["model"] == "scorecard") & (scores["cohort"] == "2005H2")
    scores.loc[hit, "pd"] = 0.95
    scores.to_parquet(r[0] / "scores.parquet", index=False)
    out = tmp_path / "out"
    assert run(e, r, out) == 0
    paired, summary = read(out)
    left = summary["bootstrap"]["cox_left_out"]["all"]
    assert left["cox_slope_deviation|arm"]["point"] == 1.0
    assert left["cox_slope_deviation|2004H2"]["point"] == 1.0
    assert left["cox_slope_deviation|2005H1"]["point"] == 0.0
    # The cell leaves the expanding arm as well, so the foundation model's arms stay equal.
    assert pooled(paired, "reduction").loc["tabpfn", "value"] == 0
    assert np.isfinite(paired[["value", "ci_lo", "ci_hi"]].to_numpy()).all()


def test_derived_rows_are_marked(tmp_path, capsys):
    e, r = both_arms(tmp_path)
    extra = []
    for directory in r:
        derived = directory.parent / f"{directory.name}-t1"
        derived.mkdir()
        for name in ("scores.parquet", "reference.parquet"):
            frame = pd.read_parquet(directory / name)
            frame[frame["model"] == "tabpfn"].assign(model="tabpfn@t1").to_parquet(
                derived / name, index=False)
        (derived / "derive.json").write_text(json.dumps({
            "derived_as": "tabpfn@t1", "approximate": True,
            "check": {"cells": [{"build_id": "x", "logit_slope_gap": 5e-4, "cox_slope_gap": 0.01,
                                 "oe_gap": 0.001}]}}), encoding="utf-8")
        extra.append(derived)
    scored = []
    for directory in e:
        twin = directory.parent / f"{directory.name}-t1"
        twin.mkdir()
        for name in ("scores.parquet", "reference.parquet"):
            frame = pd.read_parquet(directory / name)
            frame[frame["model"] == "tabpfn"].assign(model="tabpfn@t1").to_parquet(
                twin / name, index=False)
        scored.append(twin)
    out = tmp_path / "out"
    assert run([*e, *scored], [*r, *extra], out, "--no-per-draw") == 0
    paired, summary = read(out)
    # Only the rolling arm's rows at 1.0 are derived: the expanding arm's mean is scored, and
    # every row reading the rolling arm, a mean on it, E - R and h4, reads derived rows.
    t1 = paired[paired["model"] == "tabpfn@t1"]
    means = t1[t1["kind"] == "mean"]
    assert means[means["arm"] == "R"]["reads_derived"].all()
    assert not means[means["arm"] == "E"]["reads_derived"].any()
    assert t1[t1["kind"] != "mean"]["reads_derived"].all()
    assert not paired[paired["model"] == "tabpfn"]["reads_derived"].any()
    assert [d["arm"] for d in summary["derived_rows"]["tabpfn@t1"]] == ["R", "R"]
    assert not summary["criterion"]["reading"]["tabpfn@t1"]["criterion"]
    assert "~ tabpfn@t1 on 2004H2-R" in capsys.readouterr().out


def at_one(directory: Path) -> Path:
    """The directory's foundation-model rows as the model at softmax temperature 1.0."""
    twin = directory.parent / f"{directory.name}-t1"
    twin.mkdir()
    for name in ("scores.parquet", "reference.parquet"):
        frame = pd.read_parquet(directory / name)
        frame[frame["model"] == "tabpfn"].assign(model="tabpfn@t1").to_parquet(twin / name,
                                                                                index=False)
    return twin


def test_a_model_at_one_missing_on_a_build_is_left_out_and_named(tmp_path, capsys):
    # tabpfn@t1 on every expanding build and on the first rolling build only, as when its
    # derivation is refused on the second rolling build.
    e, r = both_arms(tmp_path)
    out = tmp_path / "out"
    assert run([*e, *map(at_one, e)], [*r, at_one(r[0])], out, "--no-per-draw") == 0
    paired, summary = read(out)
    assert "tabpfn@t1" not in set(paired["model"]) and "tabpfn" in set(paired["model"])
    assert summary["models_not_on_every_build"] == {"tabpfn@t1": ["2005H1-R"]}
    assert "tabpfn@t1" not in summary["models"]
    printed = capsys.readouterr().out
    assert ("tabpfn@t1 left out: at softmax temperature 1.0 and absent on 2005H1-R; no H4 row "
            "is computed for it") in printed
    assert "tabpfn@t1 not read: absent on 2005H1-R" in printed

    # The model at the shipped temperature missing on one build refuses the pairing.
    scores = pd.read_parquet(r[1] / "scores.parquet")
    scores[scores["model"] != "tabpfn"].to_parquet(r[1] / "scores.parquet", index=False)
    with pytest.raises(SystemExit, match="the arms carry different models or seeds: tabpfn absent "
                                         "on 2005H1-R"):
        run(e, r, tmp_path / "out2")


def test_a_directory_on_the_wrong_arm_is_refused(tmp_path):
    e, r = both_arms(tmp_path)
    with pytest.raises(SystemExit, match="is on arm E, named under --rolling"):
        run(e, [*r, e[0]], tmp_path / "out")
    odd = write_build(tmp_path, "2004H2", "R", arm_label="E", name="odd")
    with pytest.raises(SystemExit, match="is not a build of arm E"):
        run([odd], r, tmp_path / "out")


def test_a_rolling_build_with_no_expanding_build_is_refused(tmp_path):
    e, r = both_arms(tmp_path)
    with pytest.raises(SystemExit, match="no expanding build at the same date: 2005H1-R"):
        run(e[:1], r, tmp_path / "out")


def test_arms_that_do_not_share_cohorts_rows_or_models_are_refused(tmp_path):
    e, r = both_arms(tmp_path)
    fewer = write_build(tmp_path / "fewer", "2005H1", "R", cohorts=["2006H1"])
    with pytest.raises(SystemExit, match="score different cohorts"):
        run(e, [r[0], fewer], tmp_path / "out")

    # Every rolling build is changed alike, so the rolling arm agrees with itself and
    # only the comparison across arms can refuse.
    pristine = {d: pd.read_parquet(d / "scores.parquet") for d in r}

    def rewrite(change) -> None:
        for directory, frame in pristine.items():
            frame = frame.copy()
            victim = frame["cohort"] == "2006H1"
            change(frame, victim)
            frame.to_parquet(directory / "scores.parquet", index=False)

    rewrite(lambda f, v: f.__setitem__("row", f["row"].where(~v, f["row"] + 1)))
    with pytest.raises(SystemExit, match="2006H1: the arms score different rows"):
        run(e, r, tmp_path / "out")
    rewrite(lambda f, v: f.__setitem__("outcome", f["outcome"].where(~v, 1 - f["outcome"])))
    with pytest.raises(SystemExit, match="2006H1: the arms carry different outcomes"):
        run(e, r, tmp_path / "out")
    for directory, frame in pristine.items():
        frame[frame["model"] != "tabpfn"].to_parquet(directory / "scores.parquet", index=False)
    with pytest.raises(SystemExit, match="the arms carry different models or seeds"):
        run(e, r, tmp_path / "out")


def test_arms_scored_on_different_matrices_are_refused(tmp_path):
    e, r = both_arms(tmp_path)
    record = json.loads((r[0] / "build.json").read_text(encoding="utf-8"))
    record["features"] = ["fico", "ltv", "dti"]
    (r[0] / "build.json").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(SystemExit, match="one matrix"):
        run(e, r, tmp_path / "out")
    record["features"] = ["fico", "ltv"]
    record["ablation"] = "upb_nominal"
    (r[0] / "build.json").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(SystemExit, match="different ablations"):
        run(e, r, tmp_path / "out")


def contrast_record(path: Path, share: float) -> Path:
    path.write_text(json.dumps({"study_rolling_quarters": 4, "builds": [
        {"build_id": d, "expanding_mean_age_quarters": 6.0,
         "rolling": {"4": {"share_of_expanding": share, "mean_age_quarters": 1.5}}}
        for d in DATES]}), encoding="utf-8")
    return path


def test_a_contrast_record_of_another_grid_is_refused(tmp_path, capsys):
    # The score runs' build.json give the rolling window half of the expanding pool.
    e, r = both_arms(tmp_path)
    off = contrast_record(tmp_path / "off.json", 0.51)
    with pytest.raises(SystemExit, match=r"holding 51\.00% .* build\.json 50\.00%; the record is "
                                         "of another grid"):
        run(e, r, tmp_path / "off", "--contrast", str(off), "--no-per-draw")
    same = contrast_record(tmp_path / "same.json", 0.5)
    assert run(e, r, tmp_path / "same", "--contrast", str(same), "--no-per-draw") == 0
    assert "mean row 4.50 quarters younger" in capsys.readouterr().out
    _, summary = read(tmp_path / "same")
    assert summary["contrast"]["2004H2"]["recorded_share_held"] == 0.5
    assert "shipped softmax temperature 0.9" in summary["criterion"]["statement"]
    assert "reported as differing" in summary["criterion"]["statement"]


def test_each_face_of_the_kill_reads_as_it_fires():
    from types import SimpleNamespace as row

    assert ba.verdict(row(ci_lo=0.01, ci_hi=0.05), sensitive=False) == ba.HOLDS
    # Above zero under the primary seed, the star lost under a check seed.
    assert ba.verdict(row(ci_lo=0.01, ci_hi=0.05), sensitive=True).startswith(
        "killed: holds zero at the margin")
    # A star under a check seed alone, none under the primary.
    assert ba.verdict(row(ci_lo=-0.01, ci_hi=0.05), sensitive=True) == "killed: inside the interval"
    assert ba.verdict(row(ci_lo=-0.05, ci_hi=-0.01), sensitive=False).startswith(
        "killed: the reduction is smaller than the control's")
    # Below zero under the primary seed, the star lost under a check seed: holds zero at the margin.
    assert ba.verdict(row(ci_lo=-0.05, ci_hi=-0.01), sensitive=True).startswith(
        "killed: inside the interval, holding zero at the margin")


def test_numpy_scalars_reach_the_summary_as_json_types():
    import numpy as np

    assert json.loads(json.dumps({"a": np.bool_(False), "b": np.int64(3), "c": np.float64(0.5)},
                                 default=ba.json_value)) == {"a": False, "b": 3, "c": 0.5}


def test_no_foundation_model_means_no_reading(tmp_path):
    e, r = both_arms(tmp_path)
    with pytest.raises(SystemExit, match="not read off the classical models"):
        run(e, r, tmp_path / "out", "--drop", "tabpfn")
