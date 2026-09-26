"""The arm-level pooling, on the things that would make its table wrong.

The shared resample rests on a cohort holding the same rows on every build
that scores it; the loader has to refuse a file where that is not so. The
two slopes are one least squares with different intercepts and each has to
recover a slope planted in its own direction and ignore one planted in the
other. The second PSI has to leave the reference cohort out of its mean.
"""

from __future__ import annotations

import sys
import zlib
from pathlib import Path

import numpy as np
import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("matplotlib")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import arm_intervals as ai

SEED = 20260905
# Two builds that share their younger cohorts: the first scores three
# cohorts at ages 1 to 3, the second the last two of them at ages 1 and 2.
BUILDS = {"2015H1-E": ["2015Q3", "2015Q4", "2016Q1"], "2015H2-E": ["2015Q4", "2016Q1"]}


@pytest.fixture(autouse=True)
def small_cohorts_clear_the_floors(monkeypatch):
    """The synthetic cohorts hold hundreds of rows, not a book's thousands; the floors are
    lowered so that they pool. tests/test_floors.py reads the floors themselves."""
    monkeypatch.setattr(ai.bi, "FLOOR_ROWS", 0)
    monkeypatch.setattr(ai.bi, "FLOOR_DEFAULTS", 0)


def cohort_rows(cohort: str, rows: int = 400) -> tuple[np.ndarray, np.ndarray]:
    # A checksum of the name, not hash(): Python salts a string's hash per process,
    # and the rows would change from one run to the next.
    rng = np.random.default_rng(zlib.crc32(cohort.encode("utf-8")))
    return rng.choice(100_000, size=rows, replace=False), rng.binomial(1, 0.1, rows)


def write_build(directory: Path, build: str, *, shift: dict[str, float] | None = None) -> Path:
    """One build's score and reference files, two fixed models and one seeded."""
    rng = np.random.default_rng(SEED)
    shift = shift or {}
    frames = []
    for age, cohort in enumerate(BUILDS[build], start=1):
        positions, y = cohort_rows(cohort)
        for model, seeds in (("scorecard", [None]), ("gbm", [None]), ("gbm-50k", [11, 12])):
            for s in seeds:
                score = rng.uniform(0.01, 0.2, positions.size) + shift.get(model, 0.0) * age
                frames.append(pd.DataFrame({
                    "build_id": build, "arm": "E", "model": model, "context_seed": s,
                    "cohort": cohort, "age_quarters": age, "row": positions, "outcome": y,
                    "pd": np.clip(score, 0.001, 0.999)}))
    scores = pd.concat(frames, ignore_index=True)
    scores["context_seed"] = scores["context_seed"].astype("Int64")
    reference = pd.concat([
        pd.DataFrame({"build_id": build, "model": m, "context_seed": s,
                      "pd": rng.uniform(0.01, 0.2, 500)})
        for m, seeds in (("scorecard", [None]), ("gbm", [None]), ("gbm-50k", [11, 12]))
        for s in seeds], ignore_index=True)
    reference["context_seed"] = reference["context_seed"].astype("Int64")
    directory.mkdir(parents=True, exist_ok=True)
    scores.sample(frac=1.0, random_state=SEED).to_parquet(directory / "scores.parquet", index=False)
    reference.to_parquet(directory / "reference.parquet", index=False)
    return directory


def poison_cox(monkeypatch) -> None:
    """The Cox fit returns its failure value on scores above 0.9, and only there."""
    real = ai.mt.cox

    def cox(outcome, score, **kw):
        if np.all(np.asarray(score) > 0.9):
            nan = float("nan")
            return ai.mt.Cox(nan, nan, nan, nan, False, ai.mt.ALPHA, 100)
        return real(outcome, score, **kw)

    monkeypatch.setattr(ai.mt, "cox", cox)


def poisoned_build(directory: Path, build: str, cell: tuple[str, int, str] | None) -> Path:
    """write_build, with one seeded cell's scores moved above 0.9 where its Cox fit fails."""
    write_build(directory, build)
    if cell is not None:
        scores = pd.read_parquet(directory / "scores.parquet")
        model, seed, cohort = cell
        hit = (scores["model"] == model) & (scores["context_seed"] == seed) & (scores["cohort"] == cohort)
        scores.loc[hit, "pd"] = np.random.default_rng(SEED).uniform(0.91, 0.99, int(hit.sum()))
        scores.to_parquet(directory / "scores.parquet", index=False)
    return directory


def load(tmp_path: Path, **kwargs) -> ai.Arm:
    arm = ai.Arm()
    for build in BUILDS:
        arm.add_build([write_build(tmp_path / build, build, **kwargs)], [])
    return arm


def test_a_cell_whose_cox_fit_did_not_finish_leaves_every_arm_row_a_number(tmp_path, monkeypatch,
                                                                         capsys):
    import json

    poison_cox(monkeypatch)
    dirs = [poisoned_build(tmp_path / "a", "2015H1-E", ("gbm-50k", 11, "2015Q4")),
            poisoned_build(tmp_path / "b", "2015H2-E", None)]
    out = tmp_path / "out"
    assert ai.main([*map(str, dirs), "--out-dir", str(out), "--resamples", "20",
                    "--check-seeds", "5"]) == 0
    paired = pd.read_csv(out / "paired.csv")
    cox = paired[paired["metric"] == "cox_slope_deviation"]
    assert set(cox["scope"]) >= {"arm", "builds", "2015H1-E", "2015H2-E"}
    assert np.isfinite(cox[["value", "ci_lo", "ci_hi"]].to_numpy()).all()
    differences = cox[cox["is_difference"]]
    assert differences["excludes_zero"].isin([True, False]).all()
    summary = json.loads((out / "intervals.json").read_text(encoding="utf-8"))
    left = summary["bootstrap"]["cox_left_out"]
    # Draw 0 (seed 11) leaves the poisoned cell out; draw 1 leaves none.
    assert left["all"]["cox_slope_deviation|arm"] == {"point": 0.5, "largest_in_a_resample": 1.0}
    assert left["all"]["cox_slope_deviation|2015H2-E"]["largest_in_a_resample"] == 0.0
    # No build loses every cell, so the mean over builds leaves none out.
    assert left["all"]["cox_slope_deviation|builds"] == {"point": 0.0, "largest_in_a_resample": 0.0}
    assert left["all, draw 11"]["cox_slope_deviation|arm"]["point"] == 1.0
    assert np.isfinite(summary["bootstrap"]["seed_check"]["largest_bound_movement"])
    printed = capsys.readouterr().out
    assert "cells not estimable left out of the arm's point estimate" in printed
    assert "builds with no estimable cell left out of the mean over builds" in printed


def test_the_arm_cox_mean_is_over_the_cells_every_model_finished_on(tmp_path, monkeypatch):
    poison_cox(monkeypatch)
    arm = ai.Arm()
    arm.add_build([poisoned_build(tmp_path / "a", "2015H1-E", ("gbm-50k", 11, "2015Q4"))], [])
    arm.add_build([poisoned_build(tmp_path / "b", "2015H2-E", None)], [])
    cohorts = arm.cohorts()
    compute = ai.arm_statistics(arm, arm.models, None, True)
    first = compute({k: c.realise(0) for k, c in cohorts.items()})
    assert first["left_out|cox_slope_deviation|arm"] == 1
    assert first["left_out|cox_slope_deviation|2015H1-E"] == 1
    assert first["left_out|cox_slope_deviation|2015H2-E"] == 0
    kept = [(b, c) for b, c in arm.cells() if (b, c) != ("2015H1-E", "2015Q4")]
    want = np.mean([ai.bi.cox_slope_deviation(cohorts[c].outcome, cohorts[c].scores[(b, "scorecard")])
                    for b, c in kept])
    assert first["cox_slope_deviation|mean|arm|scorecard"] == pytest.approx(want, abs=1e-15)
    assert all(np.isfinite(v) for k, v in first.items() if k.startswith("cox_slope_deviation"))


def test_derived_rows_on_the_arm_carry_each_build_s_derivation_error(tmp_path, capsys):
    import json

    dirs = []
    for k, build in enumerate(BUILDS):
        base = write_build(tmp_path / build, build)
        derived = tmp_path / f"{build}-derived"
        derived.mkdir()
        for name in ("scores.parquet", "reference.parquet"):
            frame = pd.read_parquet(base / name)
            frame[frame["model"] == "gbm-50k"].assign(model="gbm-50k@t1").to_parquet(
                derived / name, index=False)
        (derived / "derive.json").write_text(json.dumps({
            "derived_as": "gbm-50k@t1", "approximate": True, "checked_build": [build],
            "check": {"cells": [{"build_id": build, "context_seed": 11, "cell": "reference",
                                 "logit_slope_gap": 4e-4 * (k + 1), "cox_slope_gap": 0.01,
                                 "oe_gap": 0.001}]}}), encoding="utf-8")
        dirs += [base, derived]
    out = tmp_path / "out"
    assert ai.main([*map(str, dirs), "--out-dir", str(out), "--resamples", "10",
                    "--no-per-draw"]) == 0
    import re

    printed = capsys.readouterr().out
    table_row = re.compile(r"^  \w+ +\S+ - \S+ +[+-]\d+\.\d+ \[")
    rows = [line for line in printed.splitlines() if table_row.match(line) and "gbm-50k@t1" in line]
    assert rows and all(line.rstrip().endswith("~") for line in rows)
    others = [line for line in printed.splitlines()
              if table_row.match(line) and "gbm-50k@t1" not in line]
    assert others and not any(line.rstrip().endswith("~") for line in others)
    assert printed.count("~ gbm-50k@t1 on ") == 2
    paired = pd.read_csv(out / "paired.csv")
    marked = paired[paired["reads_derived"]]
    assert len(marked) and marked["pair"].str.contains("gbm-50k@t1").all()
    assert not paired[~paired["reads_derived"]]["pair"].str.contains("gbm-50k@t1").any()
    summary = json.loads((out / "intervals.json").read_text(encoding="utf-8"))
    recorded = summary["derived_rows"]["gbm-50k@t1"]
    assert [r["build_id"] for r in recorded] == list(BUILDS)
    assert [r["cells_above_figure"] for r in recorded] == [0, 0]
    assert recorded[1]["worst_cell_error"] == pytest.approx(8e-4)


def test_loader_shares_a_cohort_across_builds_and_keys_cells_by_build(tmp_path):
    arm = load(tmp_path)
    assert arm.builds == ["2015H1-E", "2015H2-E"]
    assert arm.cells() == [("2015H1-E", "2015Q3"), ("2015H1-E", "2015Q4"),
                           ("2015H1-E", "2016Q1"), ("2015H2-E", "2015Q4"),
                           ("2015H2-E", "2016Q1")]
    assert arm.ages[("2015H1-E", "2016Q1")] == 3 and arm.ages[("2015H2-E", "2016Q1")] == 2
    assert arm.first_cohort == {"2015H1-E": "2015Q3", "2015H2-E": "2015Q4"}
    cohorts = arm.cohorts()
    shared = cohorts["2016Q1"]
    positions, y = cohort_rows("2016Q1")
    order = np.argsort(positions)
    assert np.array_equal(shared.outcome, y[order])
    assert set(shared.scores) == {(b, m) for b in BUILDS for m in ("scorecard", "gbm")}
    assert set(shared.seeds) == {(b, "gbm-50k") for b in BUILDS}
    assert shared.draws == 2
    # One resample index reaches every build's cell of the cohort.
    index = np.array([0, 0, 1])
    drawn = shared.realise(1, index)
    for build in BUILDS:
        assert drawn.scores[(build, "gbm-50k")].shape == (3,)
        assert np.array_equal(drawn.scores[(build, "gbm-50k")],
                              np.asarray(shared.seeds[(build, "gbm-50k")][1])[index])


def test_loader_refuses_a_cohort_whose_rows_differ_between_builds(tmp_path):
    arm = ai.Arm()
    arm.add_build([write_build(tmp_path / "a", "2015H1-E")], [])
    broken = pd.read_parquet(tmp_path / "a" / "scores.parquet")
    broken = broken[broken["cohort"].isin(BUILDS["2015H2-E"])].copy()
    broken["build_id"] = "2015H2-E"
    broken["age_quarters"] = broken["age_quarters"] - 1
    victim = broken[(broken["cohort"] == "2016Q1") & (broken["model"] == "scorecard")].index[0]
    broken.loc[victim, "row"] = 999_999
    (tmp_path / "b").mkdir()
    broken.to_parquet(tmp_path / "b" / "scores.parquet", index=False)
    pd.read_parquet(tmp_path / "a" / "reference.parquet").assign(build_id="2015H2-E").to_parquet(
        tmp_path / "b" / "reference.parquet", index=False)
    with pytest.raises(SystemExit, match="different rows"):
        arm.add_build([tmp_path / "b"], [])


def test_the_outcome_column_read_is_the_one_named(tmp_path):
    # A second reading of the label written beside the study's: every outcome flipped.
    directory = write_build(tmp_path / "a", "2015H1-E")
    scores = pd.read_parquet(directory / "scores.parquet")
    scores["outcome_reported"] = 1 - scores["outcome"]
    scores.to_parquet(directory / "scores.parquet", index=False)
    arm = ai.Arm(outcome="outcome_reported")
    arm.add_build([directory], [])
    for cohort in BUILDS["2015H1-E"]:
        positions, y = cohort_rows(cohort)
        assert np.array_equal(arm.outcome[cohort], 1 - y[np.argsort(positions)])
    study = ai.Arm()
    study.add_build([directory], [])
    assert np.array_equal(study.outcome["2015Q3"], 1 - arm.outcome["2015Q3"])


def test_an_outcome_column_the_scores_do_not_hold_is_refused(tmp_path):
    directory = write_build(tmp_path / "a", "2015H1-E")
    with pytest.raises(SystemExit, match=r"no scores\.parquet of the build holds a column "
                                         "outcome_reported; outcome_reported is written beside the "
                                         "study's label on the Freddie Mac book only"):
        ai.Arm(outcome="outcome_reported").add_build([directory], [])


def _split(directory: Path, root: Path, foundation: str) -> tuple[Path, Path]:
    """The build's directory split in two: every model but one, with the second reading, and
    that one model without it, as a rented-accelerator run writes its scores."""
    scores = pd.read_parquet(directory / "scores.parquet")
    reference = pd.read_parquet(directory / "reference.parquet")
    scores["outcome_reported"] = 1 - scores["outcome"]
    holder, lacking = root / "classical", root / "foundation"
    for target, pick in ((holder, scores["model"] != foundation), (lacking, scores["model"] == foundation)):
        target.mkdir(parents=True)
        part = scores[pick]
        if target == lacking:
            part = part.drop(columns="outcome_reported")
        part.to_parquet(target / "scores.parquet", index=False)
        keep = reference["model"] != foundation if target == holder else reference["model"] == foundation
        reference[keep].to_parquet(target / "reference.parquet", index=False)
    return holder, lacking


def test_a_directory_without_the_second_reading_takes_it_from_the_build_s_others(tmp_path):
    directory = write_build(tmp_path / "a", "2015H1-E")
    models = pd.read_parquet(directory / "scores.parquet")["model"].unique()
    foundation = next(m for m in models if m != models[0])
    holder, lacking = _split(directory, tmp_path / "split", foundation)
    whole = ai.Arm(outcome="outcome_reported")
    scores = pd.read_parquet(directory / "scores.parquet")
    scores["outcome_reported"] = 1 - scores["outcome"]
    (tmp_path / "whole").mkdir()
    scores.to_parquet(tmp_path / "whole" / "scores.parquet", index=False)
    pd.read_parquet(directory / "reference.parquet").to_parquet(
        tmp_path / "whole" / "reference.parquet", index=False)
    whole.add_build([tmp_path / "whole"], [])
    split = ai.Arm(outcome="outcome_reported")
    split.add_build([holder, lacking], [])
    for cohort in BUILDS["2015H1-E"]:
        assert np.array_equal(split.outcome[cohort], whole.outcome[cohort])
        for key, values in whole.fixed[cohort].items():
            assert np.array_equal(split.fixed[cohort][key], values)
        for key, draws in whole.seeded[cohort].items():
            assert all(np.array_equal(a, b) for a, b in zip(split.seeded[cohort][key], draws, strict=True))


def test_a_second_reading_is_not_taken_across_a_label_that_differs(tmp_path):
    directory = write_build(tmp_path / "a", "2015H1-E")
    models = pd.read_parquet(directory / "scores.parquet")["model"].unique()
    holder, lacking = _split(directory, tmp_path / "split", models[-1])
    bad = pd.read_parquet(lacking / "scores.parquet")
    bad.loc[bad.index[0], "outcome"] = 1 - bad.loc[bad.index[0], "outcome"]
    bad.to_parquet(lacking / "scores.parquet", index=False)
    with pytest.raises(SystemExit, match="the study's label differs"):
        ai.Arm(outcome="outcome_reported").add_build([holder, lacking], [])


def test_the_two_slopes_see_different_directions():
    # Age 1..4 within a group, one group per line; a slope planted within
    # the groups is seen with the matching intercepts and only there.
    age = np.array([1, 2, 3, 4, 1, 2, 3, 4], dtype=float)
    group = np.array(["a"] * 4 + ["b"] * 4)
    within = 0.5 * age + np.where(group == "a", 10.0, 20.0)
    assert ai.slope(age, within, group) == pytest.approx(0.5)
    # The same values with every point its own group: no within movement.
    assert np.isnan(ai.slope(age, within, np.arange(8).astype(str)))
    # A level that differs by group and no slope within it.
    assert ai.slope(age, np.where(group == "a", 1.0, 2.0), group) == pytest.approx(0.0)


def test_arm_statistics_recover_a_planted_slope_in_each_direction(tmp_path):
    # Every model's score rises with age within a build by the same amount
    # per quarter, which the build-intercept slope reads and the
    # cohort-intercept slope reads as well: a cohort scored at age 3 on one
    # build and age 2 on the next carries the shift too. The AUC is what is
    # regressed, so plant the shift on the positive class only.
    arm = ai.Arm()
    for build in BUILDS:
        directory = write_build(tmp_path / build, build)
        scores = pd.read_parquet(directory / "scores.parquet")
        scores["pd"] = np.clip(scores["pd"] + 0.05 * scores["age_quarters"] * scores["outcome"],
                               0.001, 0.999)
        scores.to_parquet(directory / "scores.parquet", index=False)
        arm.add_build([directory], [])
    cohorts = arm.cohorts()
    compute = ai.arm_statistics(arm, arm.models, None, True)
    out = compute({k: c.realise(0) for k, c in cohorts.items()})
    for model in ("scorecard", "gbm", "gbm-50k"):
        assert out[f"auc_slope_build|slope|arm|{model}"] > 0.02
        assert out[f"auc_slope_cohort|slope|arm|{model}"] > 0.02
        assert out[f"auc_slope_build|slope|2015H1-E|{model}"] > 0.02
        assert f"auc_slope_cohort|slope|2015H1-E|{model}" not in out
        # The equal-weight scope is the mean of the two builds' values.
        assert out[f"gini|mean|builds|{model}"] == pytest.approx(
            (out[f"gini|mean|2015H1-E|{model}"] + out[f"gini|mean|2015H2-E|{model}"]) / 2)
    assert out["gini|diff|arm|gbm|scorecard"] == pytest.approx(
        out["gini|mean|arm|gbm"] - out["gini|mean|arm|scorecard"])


def test_the_second_psi_leaves_the_first_cohort_out_and_reads_zero_on_a_still_model(tmp_path):
    arm = ai.Arm()
    for build, build_cohorts in BUILDS.items():
        directory = write_build(tmp_path / build, build)
        scores = pd.read_parquet(directory / "scores.parquet")
        # The scorecard scores every cohort with the same vector: nothing
        # moves, so its PSI against the first cohort is zero on every cell.
        still = np.linspace(0.01, 0.2, 400)
        for cohort in build_cohorts:
            mask = (scores["model"] == "scorecard") & (scores["cohort"] == cohort)
            scores.loc[scores[mask].sort_values("row").index, "pd"] = still
        scores.to_parquet(directory / "scores.parquet", index=False)
        arm.add_build([directory], [])
    cohorts = arm.cohorts()
    compute = ai.arm_statistics(arm, arm.models, None, True)
    out = compute({k: c.realise(0) for k, c in cohorts.items()})
    assert out["psi_first_cohort|mean|arm|scorecard"] == pytest.approx(0.0, abs=1e-12)
    assert out["psi_first_cohort|mean|arm|gbm"] > 0.0
    # The mean over the arm is over the three cells that are not a build's
    # first cohort, so the value equals that mean and not one over five.
    edges = arm.first_edges[("2015H1-E", "gbm", None)]
    shares = arm.first_shares[("2015H1-E", "gbm", None)]
    hand = []
    for build, cohort in arm.cells():
        if cohort == arm.first_cohort[build]:
            continue
        key = (build, "gbm", None)
        hand.append(ai.bi.psi_value(cohorts[cohort].scores[(build, "gbm")],
                                    arm.first_edges[key], arm.first_shares[key]))
    assert len(hand) == 3
    assert out["psi_first_cohort|mean|arm|gbm"] == pytest.approx(np.mean(hand))
    assert edges.size == 9 and shares.sum() == pytest.approx(1.0)


def test_expand_sources_reads_a_recorded_pooling(tmp_path):
    (tmp_path / "scores").mkdir()
    (tmp_path / "scores" / "scores.parquet").write_bytes(b"")
    (tmp_path / "pooled").mkdir()
    (tmp_path / "pooled" / "intervals.json").write_text(
        '{"sources": ["one", "two"]}', encoding="utf-8")
    assert ai.expand_sources([tmp_path / "scores", tmp_path / "pooled"]) == [
        tmp_path / "scores", Path("one"), Path("two")]
    (tmp_path / "empty").mkdir()
    with pytest.raises(SystemExit, match="neither"):
        ai.expand_sources([tmp_path / "empty"])


def test_cohort_scopes_add_rows_and_change_none(tmp_path):
    arm = load(tmp_path)
    cohorts = {k: c.realise(0) for k, c in arm.cohorts().items()}
    models = {m: s[:1] for m, s in arm.models.items()}
    plain = ai.arm_statistics(arm, models, None, True)(cohorts)
    scope = {"2015Q4", "2016Q1"}
    scoped = ai.arm_statistics(arm, models, None, True, {"late": scope},
                               ({"2016Q1"}, {"2015Q3"}))(cohorts)
    assert all(scoped[k] == v or (np.isnan(v) and np.isnan(scoped[k])) for k, v in plain.items())

    # The scope pools as the arm does over its own cells.
    cells = {(b, c) for b in arm.builds for c in arm.cohorts_of(b) if c in scope}
    restricted = ai.arm_statistics(arm, models, cells, False)(cohorts)
    for stat in ("gini", "cox_slope_deviation", "psi", "auc_slope_build"):
        kind = "slope" if stat.startswith("auc_slope") else "mean"
        assert scoped[f"{stat}|{kind}|late|scorecard"] == restricted[f"{stat}|{kind}|arm|scorecard"]

    # Every build holding the scope weighted alike.
    first = ai.arm_statistics(arm, models, {("2015H1-E", c) for c in scope}, False)(cohorts)
    second = ai.arm_statistics(arm, models, {("2015H2-E", c) for c in scope}, False)(cohorts)
    assert scoped["gini|mean|builds, late|gbm"] == pytest.approx(
        (first["gini|mean|arm|gbm"] + second["gini|mean|arm|gbm"]) / 2, abs=1e-15)

    # O/E ratio only on the build holding both windows.
    one = cohorts["2016Q1"]
    base = cohorts["2015Q3"]
    s_late, s_early = one.scores[("2015H1-E", "gbm")], base.scores[("2015H1-E", "gbm")]
    expected = (one.outcome.sum() / s_late.sum()) / (base.outcome.sum() / s_early.sum())
    assert scoped[f"{ai.OE_RATIO}|mean|2015H1-E|gbm"] == pytest.approx(expected, rel=1e-12)
    assert f"{ai.OE_RATIO}|mean|2015H2-E|gbm" not in scoped
    assert scoped[f"{ai.OE_RATIO}|mean|builds|gbm"] == scoped[f"{ai.OE_RATIO}|mean|2015H1-E|gbm"]


def test_the_arm_signed_slope_pairs_over_the_cells_the_deviation_pairs_over(tmp_path, monkeypatch):
    poison_cox(monkeypatch)
    arm = ai.Arm()
    arm.add_build([poisoned_build(tmp_path / "a", "2015H1-E", ("gbm-50k", 11, "2015Q4"))], [])
    arm.add_build([poisoned_build(tmp_path / "b", "2015H2-E", None)], [])
    cohorts = arm.cohorts()
    first = ai.arm_statistics(arm, arm.models, None, True)(
        {k: c.realise(0) for k, c in cohorts.items()})
    assert first["left_out|cox_slope|arm"] == first["left_out|cox_slope_deviation|arm"] == 1
    kept = [(b, c) for b, c in arm.cells() if (b, c) != ("2015H1-E", "2015Q4")]
    want = np.mean([ai.bi.cox_slope_pair(cohorts[c].outcome,
                                         cohorts[c].scores[(b, "scorecard")])[1]
                    for b, c in kept])
    assert first["cox_slope|mean|arm|scorecard"] == pytest.approx(want, abs=1e-15)
    for scope in ("arm", "builds", "2015H1-E", "2015H2-E"):
        assert np.isfinite(first[f"cox_slope|mean|{scope}|scorecard"])


@pytest.mark.parametrize("with_cells", [False, True])
def test_every_file_the_pooling_reads_is_hashed(tmp_path, with_cells):
    import json

    import record_run as rr

    first = write_build(tmp_path / "a", "2015H1-E")
    second = write_build(tmp_path / "b", "2015H2-E")
    # A recorded pooling named in place of a score directory stands for the directories it read.
    pooled = tmp_path / "pooled"
    pooled.mkdir()
    (pooled / "intervals.json").write_text(json.dumps({"sources": [second.as_posix()]}),
                                           encoding="utf-8")
    extra = []
    if with_cells:
        # The build run's cells.csv, every cohort above the floors: read for the floors and
        # the label's regimes, and hashed with the score files.
        cells = tmp_path / "cells.csv"
        pd.DataFrame([{"build_id": b, "cohort": c, "floor": True, "regime": "pre-flag"}
                      for b, cohorts in BUILDS.items() for c in cohorts]).to_csv(cells, index=False)
        extra = ["--cells", str(cells)]
    out = tmp_path / "out"
    assert ai.main([str(first), str(pooled), "--out-dir", str(out), "--resamples", "10",
                    *extra]) == 0
    hashed = json.loads((out / "inputs.json").read_text(encoding="utf-8"))
    read = [d / name for d in (first, second) for name in ("scores.parquet", "reference.parquet")]
    read.append(pooled / "intervals.json")
    if with_cells:
        read.append(cells)
    assert hashed == {p.as_posix(): rr.file_hash(p) for p in read}
