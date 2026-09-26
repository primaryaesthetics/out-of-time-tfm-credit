"""The horizon check's pooling, on the things that would make its rows wrong.

An annual cell is one build's rows of both half-years of a year, one AUC on
their union, its age the mean of the halves'; a year a build scores in one
half only is no cell of that build. A year enters on the twelve-month
label's own count on the book. The build-intercept slope does not move when
every age of a build moves by one constant, which is what the mean of the
halves' ages does. Read on half-years, the new path has to give the H1 rows
of the arm pooling to the bit.
"""

from __future__ import annotations

import json
import sys
import zlib
from pathlib import Path

import numpy as np
import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("matplotlib")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import annual_intervals as an
import arm_intervals as ai

SEED = 20260905
# The floors as the build scripts define them, read before any test lowers them.
FLOORS = (ai.bi.FLOOR_ROWS, ai.bi.FLOOR_DEFAULTS)
BOOK_CELLS = (Path(__file__).resolve().parent.parent / "experiments"
              / "2026-09-13-fm-vintage-builds2" / "cells.csv")
# Two builds at a year's end and one at mid-year: the third scores 2015 in its
# second half only, so it has no 2015 cell while the first has one.
BUILDS = {
    "2014H2-E": ["2015H1", "2015H2", "2016H1", "2016H2", "2017H1", "2017H2"],
    "2015H2-E": ["2016H1", "2016H2", "2017H1", "2017H2"],
    "2015H1-E": ["2015H2", "2016H1", "2016H2", "2017H1", "2017H2"],
}
MODELS = (("scorecard", [None]), ("gbm", [None]), ("gbm-50k", [11, 12]))


@pytest.fixture(autouse=True)
def small_cohorts_clear_the_floors(monkeypatch):
    """Hundreds of rows a cohort, not a book's thousands: the floors are lowered where the
    scored rows are held against them. The admission test reads the real floors."""
    monkeypatch.setattr(ai.bi, "FLOOR_ROWS", 0)
    monkeypatch.setattr(ai.bi, "FLOOR_DEFAULTS", 0)


def cohort_rows(cohort: str, rows: int = 400) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(zlib.crc32(cohort.encode("utf-8")))
    positions = rng.choice(100_000, size=rows, replace=False)
    y = rng.binomial(1, 0.12, rows)
    # A twelve-month default is a twenty-four-month default; about half of them.
    horizon = y * rng.binomial(1, 0.5, rows)
    return positions, y, horizon


def write_build(directory: Path, build: str, cohorts: list[str] | None = None, *,
                slope: float = 0.0) -> Path:
    """One build's score and reference files; half-year cohorts at odd quarter ages, and a
    score that rises with age on the defaults by `slope` per quarter."""
    rng = np.random.default_rng(zlib.crc32(build.encode("utf-8")))
    frames = []
    for age, cohort in zip(range(1, 99, 2), cohorts or BUILDS[build]):
        positions, y, horizon = cohort_rows(cohort)
        for model, seeds in MODELS:
            for s in seeds:
                score = rng.uniform(0.01, 0.2, positions.size) + slope * age * y
                frames.append(pd.DataFrame({
                    "build_id": build, "arm": "E", "model": model, "context_seed": s,
                    "cohort": cohort, "age_quarters": age, "row": positions, "outcome": y,
                    "pd": np.clip(score, 0.001, 0.999), "outcome_horizon": horizon}))
    scores = pd.concat(frames, ignore_index=True)
    scores["context_seed"] = scores["context_seed"].astype("Int64")
    reference = pd.concat([
        pd.DataFrame({"build_id": build, "model": m, "context_seed": s,
                      "pd": rng.uniform(0.01, 0.2, 500)})
        for m, seeds in MODELS for s in seeds], ignore_index=True)
    reference["context_seed"] = reference["context_seed"].astype("Int64")
    directory.mkdir(parents=True, exist_ok=True)
    scores.sample(frac=1.0, random_state=SEED).to_parquet(directory / "scores.parquet", index=False)
    reference.to_parquet(directory / "reference.parquet", index=False)
    return directory


def write_cells(path: Path, builds=BUILDS, defaults: dict[str, int] | None = None) -> Path:
    """The build run's cells.csv: every half-year above the primary floor, the twelve-month
    counts those of the rows unless `defaults` says otherwise."""
    defaults = defaults or {}
    rows = []
    for build, cohorts in builds.items():
        for cohort in cohorts:
            _, _, horizon = cohort_rows(cohort)
            rows.append({"build_id": build, "cohort": cohort, "floor": True, "regime": "pre-flag",
                         "labelled_horizon": horizon.size,
                         "defaults_horizon": defaults.get(cohort, int(horizon.sum()))})
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def load(tmp_path: Path, builds=BUILDS, outcome: str = an.OUTCOME, **kwargs) -> ai.Arm:
    arm = ai.Arm(outcome=outcome)
    for build in builds:
        arm.add_build([write_build(tmp_path / build, build, **kwargs)], [])
    return arm


def test_an_annual_cell_is_the_union_of_its_halves_at_their_mean_age(tmp_path):
    arm = load(tmp_path)
    cells, _ = an.annual_cells(arm)
    first, second = arm.cohorts()["2016H1"], arm.cohorts()["2016H2"]
    year = cells.cohorts["2016"]
    assert np.array_equal(year.outcome, np.concatenate([first.outcome, second.outcome]))
    for build in BUILDS:
        assert np.array_equal(year.scores[(build, "gbm")],
                              np.concatenate([first.scores[(build, "gbm")],
                                              second.scores[(build, "gbm")]]))
        for a, b, c in zip(year.seeds[(build, "gbm-50k")], first.seeds[(build, "gbm-50k")],
                           second.seeds[(build, "gbm-50k")], strict=True):
            assert np.array_equal(a, np.concatenate([b, c]))
    # 2014H2-E scores 2016 at ages 5 and 7, 2015H2-E at 1 and 3.
    assert cells.ages[("2014H2-E", "2016")] == 6.0
    assert cells.ages[("2015H2-E", "2016")] == 2.0
    # The outcome read is the twelve-month label.
    positions, _, horizon = cohort_rows("2016H1")
    assert np.array_equal(first.outcome, horizon[np.argsort(positions)])


def test_a_year_scored_in_one_half_is_no_cell_of_that_build(tmp_path):
    arm = load(tmp_path)
    cells, partial = an.annual_cells(arm)
    assert ("2014H2-E", "2015") in cells.ages
    assert ("2015H1-E", "2015") not in cells.ages
    assert partial == {"2015": ["2015H1-E"]}
    # The year's cohort carries no score of the build that scored one half.
    assert all(b != "2015H1-E" for b, _ in cells.cohorts["2015"].scores)
    assert cells.cohorts_of("2015H1-E") == ["2016", "2017"]


def test_a_year_enters_at_one_hundred_twelve_month_defaults_and_not_one_under(tmp_path):
    cells = write_cells(tmp_path / "cells.csv", defaults={
        "2015H1": 50, "2015H2": 49, "2016H1": 50, "2016H2": 50, "2017H1": 60, "2017H2": 61})
    years = an.book_years(cells)
    assert years.loc["2015", "defaults"] == 99 and years.loc["2016", "defaults"] == 100
    # The real floors of EXP-003, not the fixture's lowered ones.
    assert an.admitted(years, rows=5_000, defaults=100) == set()  # 800 labelled a year
    assert an.admitted(years, rows=0, defaults=100) == {"2016", "2017"}
    assert an.admitted(years, rows=0, defaults=an.bi.FLOOR_DEFAULTS) == {"2015", "2016", "2017"}


def test_the_floor_is_on_the_year_s_sum_and_not_on_each_half(tmp_path):
    # 2015 holds 105 defaults with one half at 30; 2016 holds 99 with both halves near 50.
    cells = write_cells(tmp_path / "cells.csv", defaults={
        "2015H1": 30, "2015H2": 75, "2016H1": 50, "2016H2": 49, "2017H1": 100, "2017H2": 0})
    years = an.book_years(cells)
    admitted = an.admitted(years, rows=0, defaults=100)
    assert "2015" in admitted and "2017" in admitted and "2016" not in admitted
    # A floor of fifty on each half would keep 2015 and 2017 out.
    table = pd.read_csv(cells, dtype={"cohort": str}).drop_duplicates("cohort")
    per_half = table.groupby(table["cohort"].str[:4])["defaults_horizon"].min()
    assert per_half["2015"] < 50 and per_half["2017"] < 50


def test_the_book_admits_2004_to_2012_2017_2019_2022_and_2023(monkeypatch):
    if not BOOK_CELLS.exists():
        pytest.skip(f"{BOOK_CELLS.name} of the vintage build run is not on this machine")
    assert FLOORS == (5_000, 100)
    monkeypatch.setattr(ai.bi, "FLOOR_ROWS", FLOORS[0])
    monkeypatch.setattr(ai.bi, "FLOOR_DEFAULTS", FLOORS[1])
    years = an.book_years(BOOK_CELLS)
    expected = {str(y) for y in [*range(2004, 2013), 2017, 2019, 2022, 2023]}
    assert an.admitted(years) == expected
    # The hole: 2003, 2013 to 2016, 2018, 2020 and 2021, every one under the defaults floor.
    hole = {"2003", "2013", "2014", "2015", "2016", "2018", "2020", "2021"}
    assert hole <= set(years.index)
    assert (years.loc[sorted(hole), "defaults"] < 100).all()


def test_a_line_is_never_joined_across_a_cohort_left_out():
    years = ["2011", "2012", "2013", "2014", "2015", "2017", "2018"]
    keep = {"2011", "2012", "2015", "2017", "2018"}
    assert an.runs(years, keep) == [["2011", "2012"], ["2015"], ["2017", "2018"]]
    halves = ["2016H1", "2016H2", "2017H1", "2017H2"]
    assert an.runs(halves, {"2016H1", "2016H2", "2017H2"}) == [["2016H1", "2016H2"], ["2017H2"]]
    assert an.runs(["2016H2", "2017H1"], {"2016H2", "2017H1"}) == [["2016H2", "2017H1"]]


def test_a_year_with_one_half_on_the_book_is_not_admitted(tmp_path):
    cells = write_cells(tmp_path / "cells.csv", builds={"2015H1-E": BUILDS["2015H1-E"]})
    years = an.book_years(cells)
    assert years.loc["2015", "halves"] == 1
    assert "2015" not in an.admitted(years, rows=0, defaults=0)


def test_book_counts_that_differ_between_builds_are_refused(tmp_path):
    path = write_cells(tmp_path / "cells.csv")
    table = pd.read_csv(path)
    # 2016H1 is scored by every build; one of them now counts it differently.
    table.loc[table.index[table["cohort"] == "2016H1"][-1], "defaults_horizon"] += 1
    table.to_csv(path, index=False)
    with pytest.raises(SystemExit, match="two twelve-month counts"):
        an.book_years(path)


def test_the_build_slope_does_not_move_under_a_constant_age_shift(tmp_path):
    arm = load(tmp_path, slope=0.01)
    cells, _ = an.annual_cells(arm)
    realised = {k: c.realise(0) for k, c in cells.cohorts.items()}
    shifted = an.Cells(cells.builds, {(b, c): a + (1.0 if b == "2014H2-E" else -0.5)
                                      for (b, c), a in cells.ages.items()},
                       cells.cohorts, cells.models)
    plain = an.h1_statistics(cells, cells.models, None, True)(realised)
    moved = an.h1_statistics(shifted, cells.models, None, True)(realised)
    for key, value in plain.items():
        if key.startswith("auc_slope_build"):
            assert moved[key] == pytest.approx(value, abs=1e-12), key
    # The planted slope is read, per quarter of age.
    assert plain["auc_slope_build|slope|arm|scorecard"] > 0.0


def test_a_build_with_one_annual_cell_is_unreadable_and_stays(tmp_path):
    builds = {**BUILDS, "2016H2-E": ["2017H1", "2017H2"]}
    arm = ai.Arm(outcome=an.OUTCOME)
    for build, cohorts in builds.items():
        arm.add_build([write_build(tmp_path / build, build, cohorts)], [])
    cells, _ = an.annual_cells(arm)
    assert an.unreadable(cells, None) == ["2016H2-E"]
    out = an.h1_statistics(cells, cells.models, None, True)(
        {k: c.realise(0) for k, c in cells.cohorts.items()})
    assert np.isnan(out["auc_slope_build|slope|2016H2-E|gbm"])
    assert np.isnan(out["auc_slope_build|slope|builds|gbm"])
    assert np.isfinite(out["auc_slope_build|slope|arm|gbm"])
    assert "2016H2-E" in cells.builds


def test_read_on_half_years_the_new_path_gives_the_arm_pooling_s_h1_rows(tmp_path):
    for build in BUILDS:
        write_build(tmp_path / build, build, slope=0.004)
    cells = write_cells(tmp_path / "cells.csv")
    dirs = [str(tmp_path / b) for b in BUILDS]
    common = ["--resamples", "12", "--check-seeds", "7,8", "--cells", str(cells)]
    assert ai.main([*dirs, "--out-dir", str(tmp_path / "arm"), *common]) == 0
    assert an.main([*dirs, "--out-dir", str(tmp_path / "new"), "--resolution", "half",
                    "--outcome", "outcome", *common]) == 0
    keys = ["cohorts", "draw", "scope", "metric", "pair"]
    columns = ["value", "ci_lo", "ci_hi", "se", "excludes_zero"]
    for name in ("paired.csv", "paired-seeds.csv"):
        old = pd.read_csv(tmp_path / "arm" / name)
        new = pd.read_csv(tmp_path / "new" / name)
        keys_here = [k for k in keys if k in old.columns] + (
            ["bootstrap_seed"] if "bootstrap_seed" in old.columns else [])
        old = old[old["metric"].isin(an.H1_METRICS)]
        # The arm pooling's label-regime scopes are further scopes and not H1's poolings.
        regime = old["scope"].str.contains("pre-flag")
        assert set(old.loc[regime, "scope"]) == {"pre-flag", "builds, pre-flag"}
        old = old[~regime]
        assert len(old) == len(new) > 0
        joined = old.merge(new, on=keys_here, how="outer", suffixes=("_arm", "_new"),
                           indicator=True)
        assert (joined["_merge"] == "both").all()
        for column in columns:
            if f"{column}_arm" not in joined:
                continue
            a, b = joined[f"{column}_arm"], joined[f"{column}_new"]
            assert ((a == b) | (a.isna() & b.isna())).all(), (name, column)


def test_the_annual_run_writes_its_counts_and_hashes_its_inputs(tmp_path, capsys, monkeypatch):
    # One default is the floor here, and the book holds none in 2017, so 2017 leaves and the
    # two builds scoring 2016 and 2017 whole are left with one annual cell each.
    monkeypatch.setattr(ai.bi, "FLOOR_DEFAULTS", 1)
    for build in BUILDS:
        write_build(tmp_path / build, build)
    cells = write_cells(tmp_path / "cells.csv", defaults={"2017H1": 0, "2017H2": 0})
    out = tmp_path / "out"
    assert an.main([*(str(tmp_path / b) for b in BUILDS), "--out-dir", str(out),
                    "--resamples", "10", "--cells", str(cells)]) == 0
    printed = capsys.readouterr().out
    assert "unreadable" in printed and "2015H2-E" in printed
    summary = json.loads((out / "intervals.json").read_text(encoding="utf-8"))
    assert summary["resolution"] == "year" and summary["outcome"] == an.OUTCOME
    years = {y["year"]: y for y in summary["years"]}
    assert not years["2017"]["admitted"] and years["2017"]["defaults_book"] == 0
    assert years["2016"]["admitted"] and years["2016"]["builds_whole"] == sorted(BUILDS)
    assert years["2015"]["builds_one_half"] == ["2015H1-E"]
    assert summary["builds"] == {"2014H2-E": ["2015", "2016"], "2015H1-E": ["2016"],
                                 "2015H2-E": ["2016"]}
    assert summary["unreadable"]["all"] == ["2015H1-E", "2015H2-E"]
    paired = pd.read_csv(out / "paired.csv")
    assert set(paired["metric"]) == set(an.H1_METRICS)
    hashed = json.loads((out / "inputs.json").read_text(encoding="utf-8"))
    assert any(p.endswith("cells.csv") for p in hashed)
    assert sum(p.endswith("scores.parquet") for p in hashed) == len(BUILDS)
    assert (out / "auc-age.png").exists() and (out / "paired.csv").exists()


def test_the_nearest_pooling_takes_the_three_youngest_years_before_the_floor(tmp_path,
                                                                           monkeypatch):
    # 2013H2-E scores 2014 to 2018; the book holds no twelve-month default in 2014 or 2015.
    # Its three youngest years are 2014, 2015 and 2016, of which 2016 alone enters, so it is
    # unreadable there. The floor taken first would leave it 2016, 2017 and 2018, readable.
    monkeypatch.setattr(ai.bi, "FLOOR_DEFAULTS", 1)
    years = ["2014", "2015", "2016", "2017", "2018"]
    builds = {"2013H2-E": [f"{y}H{h}" for y in years for h in (1, 2)],
              "2015H2-E": [f"{y}H{h}" for y in years[2:] for h in (1, 2)]}
    for build, cohorts in builds.items():
        write_build(tmp_path / build, build, cohorts)
    cells = write_cells(tmp_path / "cells.csv", builds=builds, defaults={
        "2014H1": 0, "2014H2": 0, "2015H1": 0, "2015H2": 0})
    out = tmp_path / "out"
    assert an.main([*(str(tmp_path / b) for b in builds), "--out-dir", str(out),
                    "--resamples", "6", "--cells", str(cells)]) == 0
    summary = json.loads((out / "intervals.json").read_text(encoding="utf-8"))
    assert summary["nearest_cells"] == {"2013H2-E": ["2016"],
                                        "2015H2-E": ["2016", "2017", "2018"]}
    assert summary["unreadable"] == {"all": [], "nearest": ["2013H2-E"]}
    paired = pd.read_csv(out / "paired.csv")
    slopes = paired[~paired["is_difference"] & paired["draw"].isna()
                    & (paired["metric"] == "auc_slope_build")]
    for cohorts, readable in (("all", True), ("nearest", False)):
        rows = slopes[slopes["cohorts"] == cohorts].set_index(["scope", "pair"])["value"]
        assert np.isfinite(rows.loc[("2015H2-E", "gbm")])
        assert np.isfinite(rows.loc[("2013H2-E", "gbm")]) == readable
        assert np.isfinite(rows.loc[("builds", "gbm")]) == readable
        assert np.isfinite(rows.loc[("arm", "gbm")])


@pytest.mark.parametrize("floor, column", [("FLOOR_DEFAULTS", "defaults_horizon"),
                                           ("FLOOR_ROWS", "labelled_horizon")])
def test_an_admitted_year_whose_scored_rows_fall_under_a_floor_stops_the_run(
        tmp_path, monkeypatch, floor, column):
    # The book's counts clear a raised floor on every year; the 400 scored rows a half-year,
    # with a few dozen twelve-month defaults, do not.
    monkeypatch.setattr(ai.bi, floor, 1_000)
    for build in BUILDS:
        write_build(tmp_path / build, build)
    path = write_cells(tmp_path / "cells.csv")
    table = pd.read_csv(path)
    table[column] = 1_000
    table.to_csv(path, index=False)
    with pytest.raises(SystemExit, match="admits 2015 .*under the floors"):
        an.main([*(str(tmp_path / b) for b in BUILDS), "--out-dir", str(tmp_path / "out"),
                 "--resamples", "4", "--cells", str(path)])


def test_the_fit_line_and_the_legend_read_the_pooled_cells_only(tmp_path):
    # 2017 is left out; it holds every build's oldest cells, so a line fitted through it
    # would reach further along the age axis than the pooled cells do.
    arm = load(tmp_path)
    every, _ = an.annual_cells(arm)
    keep = {"2015", "2016"}
    slope = 0.002
    paired = pd.DataFrame([
        {"metric": f"auc_slope_{by}", "is_difference": False, "scope": ai.ARM, "cohorts": "all",
         "draw": np.nan, "pair": model, "value": slope, "ci_lo": 0.0, "ci_hi": 0.004}
        for by in ("build", "cohort") for model, _ in MODELS])
    pooled = [k for k in every.ages if k[1] in keep]
    ages = np.array([every.ages[k] for k in pooled])
    assert max(every.ages.values()) > ages.max()
    for by in ("build", "cohort"):
        drawn = an.plot_auc_age(every, keep, paired, tmp_path / f"{by}.png", by, an.OUTCOME,
                                "year")
        for model, _ in MODELS:
            x, y = drawn["fits"][model]
            assert list(x) == [ages.min(), ages.max()]
            aucs = []
            for build, year in pooled:
                cohort = every.cohorts[year]
                score = cohort.scores.get((build, model))
                if score is None:
                    score = cohort.seeds[(build, model)][0]
                aucs.append(an.mt.auc(cohort.outcome, score))
            assert np.interp(ages.mean(), x, y) == pytest.approx(np.mean(aucs), abs=1e-12)
        if by == "cohort":
            assert "2017" not in drawn["legend"] and {"2015", "2016"} <= set(drawn["legend"])
            assert "cohort under the floor, not pooled" in drawn["legend"]
        else:
            assert set(BUILDS) <= set(drawn["legend"])
