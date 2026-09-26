"""The floors, on the five scripts that pool over cohorts, at the floors themselves.

A cohort under 5,000 labelled loans or 100 defaults enters no pooling
(EXP-005, Floors). Read where the answer is known: the middle cohort of a
book of 5,000-row cohorts holds 60 defaults. Without the build run's verdict
every pooling refuses; with a verdict that puts the cohort under the floors,
the pooled statistics over every pooled cohort equal the ones read with the
cohort absent and the per-cell table still holds it; a verdict that admits
it is refused. Two readings are not the absent run's, by design. The
nearest pooling is a window of age: a cohort under the floors leaves it and
nothing replaces it, so it is read against the window's remaining cells. And
the arm's second PSI keeps its reference on the build's first scored cohort
under the floors or not, since it reads no label; on a build whose first
cohort is the one under the floors it is read by hand.
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

import ablation_intervals as ab
import arm_intervals as ai
import between_arm_intervals as ba
import build_intervals as bi
import protocol_table as pt

ROWS = 5_000
UNDER = "2016H1"
DEFAULTS = {"2015H2": 300, UNDER: 60, "2016H2": 300, "2017H1": 300}
# Two build dates of three half-years each; the cohort under the floors is scored by both,
# the last of the first date's cohorts and the first of the second's.
DATES = {"2015H1": ["2015H2", UNDER, "2016H2"], "2015H2": [UNDER, "2016H2", "2017H1"]}
MODELS = {"scorecard": [None], "gbm-50k": [11], "tabpfn": [11]}


def seed_of(text: str) -> int:
    return zlib.crc32(text.encode("utf-8"))


def cohort(name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One cohort's rows, its outcomes with exactly its defaults, and a latent score."""
    rng = np.random.default_rng(seed_of(name))
    y = np.zeros(ROWS, dtype=int)
    y[:DEFAULTS[name]] = 1
    y = rng.permutation(y)
    rows = np.sort(rng.choice(1_000_000, size=ROWS, replace=False))
    return rows, y, rng.normal(size=ROWS) + 1.5 * y


def probability(latent: np.ndarray, noise: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-(-4.0 + 0.9 * latent + 0.3 * noise)))


def write_build(root: Path, date: str, arm: str, cohorts: list[str] | None = None,
                name: str | None = None) -> Path:
    build = f"{date}-{arm}"
    frames, references = [], []
    for c in DATES[date] if cohorts is None else cohorts:
        rows, y, latent = cohort(c)
        age = 2 * (int(c[:4]) - int(date[:4])) + int(c[-1]) - int(date[-1])
        for model, seeds in MODELS.items():
            for s in seeds:
                noise = np.random.default_rng(seed_of(f"{model}{c}{s}")).normal(size=ROWS)
                frames.append(pd.DataFrame({
                    "build_id": build, "arm": arm, "model": model, "context_seed": s,
                    "cohort": c, "age_quarters": age, "row": rows, "outcome": y,
                    "outcome_reported": y, "pd": probability(latent, noise)}))
    for model, seeds in MODELS.items():
        for s in seeds:
            rng = np.random.default_rng(seed_of(f"{model}{s}reference"))
            latent = rng.normal(size=2_000) + 1.5 * rng.binomial(1, 0.05, 2_000)
            references.append(pd.DataFrame({
                "build_id": build, "arm": arm, "model": model, "context_seed": s,
                "pd": probability(latent, rng.normal(size=2_000))}))
    directory = root / (name or build)
    directory.mkdir(parents=True)
    for file, parts in (("scores.parquet", frames), ("reference.parquet", references)):
        frame = pd.concat(parts, ignore_index=True)
        frame["context_seed"] = frame["context_seed"].astype("Int64")
        frame.to_parquet(directory / file, index=False)
    (directory / "build.json").write_text(json.dumps({
        "build": {"build_id": build, "train_rows": 200_000 if arm == "E" else 100_000},
        "ablation": None, "features": ["fico", "ltv"]}), encoding="utf-8")
    return directory


def without(root: Path, date: str, arm: str) -> Path:
    """The build with the cohort under the floors absent: the known answer."""
    return write_build(root, date, arm, [c for c in DATES[date] if c != UNDER],
                       name=f"{date}-{arm}-absent")


def cells_file(path: Path, builds: list[str], floor: dict[str, bool]) -> Path:
    """A build run's cells.csv: every cohort of the builds named, above the floors unless said."""
    pd.DataFrame([{"build_id": b, "cohort": c, "floor": floor.get(c, True), "regime": "pre-flag"}
                  for b in builds for c in DATES[b.rsplit("-", 1)[0]]]).to_csv(path, index=False)
    return path


def same_file(a: Path, b: Path) -> None:
    pd.testing.assert_frame_equal(pd.read_csv(a), pd.read_csv(b))


def test_the_floor_constants_are_those_of_the_floors_paragraph():
    assert (bi.FLOOR_ROWS, bi.FLOOR_DEFAULTS) == (5_000, 100)
    assert not bi.under_floors(np.r_[np.ones(100), np.zeros(4_900)])
    assert bi.under_floors(np.r_[np.ones(99), np.zeros(4_901)])
    assert bi.under_floors(np.r_[np.ones(100), np.zeros(4_899)])


def test_build_intervals_leaves_a_cohort_under_the_floors_out_of_every_pooling(tmp_path):
    full, absent = write_build(tmp_path, "2015H1", "E"), without(tmp_path, "2015H1", "E")

    def run(directory: Path, out: str, *extra: str) -> int:
        return bi.main([str(directory), "--out-dir", str(tmp_path / out), "--resamples", "20",
                        *extra])

    with pytest.raises(SystemExit, match=f"2015H1-E {UNDER}: the scored rows hold 5,000 rows "
                                         "and 60 defaults, under the floors .* --cells"):
        run(full, "refused")
    verdict = cells_file(tmp_path / "cells.csv", ["2015H1-E"], {UNDER: False})
    assert run(full, "floors", "--cells", str(verdict), "--check-seeds", "5") == 0
    assert run(absent, "absent", "--check-seeds", "5") == 0
    for name in ("paired.csv", "paired-seeds.csv"):
        same_file(tmp_path / "floors" / name, tmp_path / "absent" / name)
    metrics = pd.read_csv(tmp_path / "floors" / "metrics.csv")
    under = metrics[metrics["cohort"] == UNDER]
    assert len(under) == 3 * bi.CELL_METRICS and not under["floor"].any()
    assert under[under["metric"] == "auc"][["ci_lo", "ci_hi"]].notna().all().all()
    kept = metrics[metrics["cohort"] != UNDER].drop(columns="floor").reset_index(drop=True)
    pd.testing.assert_frame_equal(kept, pd.read_csv(tmp_path / "absent" / "metrics.csv"))
    summary = json.loads((tmp_path / "floors" / "intervals.json").read_text(encoding="utf-8"))
    assert summary["floors"]["reading"] == "2 of 3 cells above the floors"
    assert summary["floors"]["under"] == [UNDER]
    assert summary["cohorts"] == ["2015H2", "2016H2"] and summary["cohorts_scored"] == 3
    absent_summary = json.loads((tmp_path / "absent" / "intervals.json").read_text(encoding="utf-8"))
    assert "floors" not in absent_summary

    # The nearest pooling is a window of age, the youngest two cohorts less those under the
    # floors: 2015H2 alone, where the run with the cohort absent reads 2015H2 and 2016H2. Its
    # point values are held to the window's remaining cell, not to the absent run.
    assert run(full, "nearest", "--cells", str(verdict), "--nearest", "2") == 0
    summary = json.loads((tmp_path / "nearest" / "intervals.json").read_text(encoding="utf-8"))
    assert summary["nearest"] == ["2015H2"] and "nearest" in summary["bootstrap"]["poolings"]
    assert run(absent, "absent-nearest", "--nearest", "2") == 0
    other = json.loads((tmp_path / "absent-nearest" / "intervals.json").read_text(encoding="utf-8"))
    assert other["nearest"] == ["2015H2", "2016H2"]
    paired = pd.read_csv(tmp_path / "nearest" / "paired.csv")
    near = paired[(paired["cohorts"] == "nearest") & ~paired["is_difference"]]
    scores = pd.read_parquet(full / "scores.parquet")
    for model in MODELS:
        cell = scores[(scores["model"] == model) & (scores["cohort"] == "2015H2")]
        y, s = cell["outcome"].to_numpy(), cell["pd"].to_numpy(dtype=float)
        value = near[near["pair"] == model].set_index("metric")["value"]
        assert np.isclose(value["gini"], bi.mt.gini(y, s), rtol=1e-12, atol=0)
        assert np.isclose(value["abs_log_oe"], bi.abs_log_oe(y, s), rtol=1e-12, atol=0)

    admits = cells_file(tmp_path / "admits.csv", ["2015H1-E"], {})
    with pytest.raises(SystemExit, match=f"admits 2015H1-E {UNDER}, whose scored rows hold 5,000 "
                                         "rows and 60 defaults"):
        run(full, "admits", "--cells", str(admits))
    short = pd.read_csv(verdict)
    short[short["cohort"] != UNDER].to_csv(tmp_path / "short.csv", index=False)
    with pytest.raises(SystemExit, match=f"holds no row for 2015H1-E {UNDER}"):
        run(full, "short", "--cells", str(tmp_path / "short.csv"))
    two = pd.concat([pd.read_csv(verdict), pd.read_csv(admits).assign(build_id="2015H2-E")])
    two.to_csv(tmp_path / "two.csv", index=False)
    with pytest.raises(SystemExit, match=f"{UNDER} carries two floor verdicts"):
        run(full, "two", "--cells", str(tmp_path / "two.csv"))


def test_arm_intervals_leaves_a_cohort_under_the_floors_out_of_every_pooling(tmp_path, capsys):
    full = [write_build(tmp_path, d, "E") for d in DATES]
    absent = [without(tmp_path, d, "E") for d in DATES]

    def run(dirs: list[Path], out: str, *extra: str) -> int:
        return ai.main([*map(str, dirs), "--out-dir", str(tmp_path / out), "--resamples", "20",
                        *extra])

    with pytest.raises(SystemExit, match=rf"{UNDER} \(2015H1-E, 2015H2-E\): the scored rows hold "
                                         "5,000 rows and 60 defaults.* --cells"):
        run(full, "refused")
    builds = [f"{d}-E" for d in DATES]
    verdict = cells_file(tmp_path / "cells.csv", builds, {UNDER: False})
    assert run(full, "floors", "--cells", str(verdict), "--check-seeds", "5") == 0
    printed = capsys.readouterr().out
    assert "floors                : 4 of 6 cells above the floors" in printed
    assert f"{UNDER} left out of the pooling: under the floors, on 2015H1-E, 2015H2-E" in printed
    assert (f"2015H2-E: the second stability reference is {UNDER}, under the floors; its cells "
            "are in no pooling") in printed
    assert run(absent, "absent", "--check-seeds", "5") == 0

    # Every statistic of the poolings over every pooled cell, but the second PSI, is the one
    # read with the cohort absent; nearest 3 is every pooled cell here, so the nearest pooling
    # is not read, and it is held to its own rule below. The second PSI's reference on
    # 2015H2-E stays its first scored cohort, under the floors, where the absent run's is the
    # next cohort; on 2015H1-E the reference is 2015H2 in both.
    def other(f: pd.DataFrame) -> pd.DataFrame:
        return f[f["metric"] != "psi_first_cohort"].reset_index(drop=True)

    def same_reference(f: pd.DataFrame) -> pd.DataFrame:
        return f[(f["metric"] == "psi_first_cohort")
                 & (f["scope"] == "2015H1-E")].reset_index(drop=True)

    # The verdict file also names the label's pre-flag and flagged scopes, which the run
    # without it does not pool; the comparison is over the scopes both runs hold.
    for name in ("paired.csv", "paired-seeds.csv"):
        floors, gone = (pd.read_csv(tmp_path / run_ / name) for run_ in ("floors", "absent"))
        assert set(gone["scope"]) <= set(floors["scope"])
        floors = floors[floors["scope"].isin(set(gone["scope"]))].reset_index(drop=True)
        pd.testing.assert_frame_equal(other(floors), other(gone))
        pd.testing.assert_frame_equal(same_reference(floors), same_reference(gone))
    summary = json.loads((tmp_path / "floors" / "intervals.json").read_text(encoding="utf-8"))
    assert summary["floors"]["reading"] == "4 of 6 cells above the floors"
    assert summary["floors"]["under"] == {UNDER: builds}
    assert summary["psi"]["first_cohort"] == {"2015H1-E": "2015H2", "2015H2-E": UNDER}
    assert summary["floors"]["first_cohort_under_floors"] == ["2015H2-E"]
    assert summary["cells"] == 6

    # By hand on 2015H2-E: each model's scores on the two cohorts above the floors read against
    # its deciles on the cohort under them; the reference cohort's own cells enter no mean, so
    # the build's mean is over exactly these two cells. One draw per model: the point is exact.
    paired = pd.read_csv(tmp_path / "floors" / "paired.csv")
    scores = pd.read_parquet(full[1] / "scores.parquet")
    for model in MODELS:
        cell = scores[scores["model"] == model]
        reference = cell.loc[cell["cohort"] == UNDER, "pd"].to_numpy()
        edges = ai.mt.psi_edges(reference)
        shares = np.bincount(np.searchsorted(edges, reference, side="right"),
                             minlength=edges.size + 1) / reference.size
        hand = np.mean([bi.psi_value(cell.loc[cell["cohort"] == c, "pd"].to_numpy(), edges, shares)
                        for c in ("2016H2", "2017H1")])
        row = paired[(paired["metric"] == "psi_first_cohort") & (paired["scope"] == "2015H2-E")
                     & (paired["cohorts"] == "all") & paired["draw"].isna()
                     & ~paired["is_difference"] & (paired["pair"] == model)]
        assert len(row) == 1 and np.isclose(row["value"].iloc[0], hand, rtol=1e-12, atol=0)

    # The nearest pooling at two: each build's youngest two cohorts less the one under the
    # floors, 2015H2 on 2015H1-E and 2016H2 on 2015H2-E, and nothing in their place. Its point
    # values are the mean over those two cells, not the absent run's window.
    assert run(full, "nearest", "--cells", str(verdict), "--nearest", "2") == 0
    summary = json.loads((tmp_path / "nearest" / "intervals.json").read_text(encoding="utf-8"))
    assert "nearest" in summary["bootstrap"]["poolings"]
    paired = pd.read_csv(tmp_path / "nearest" / "paired.csv")
    near = paired[(paired["cohorts"] == "nearest") & (paired["scope"] == "arm")
                  & paired["draw"].isna() & ~paired["is_difference"]]
    window = [(full[0], "2015H2"), (full[1], "2016H2")]
    for model in MODELS:
        cells = []
        for directory, name in window:
            frame = pd.read_parquet(directory / "scores.parquet")
            cell = frame[(frame["model"] == model) & (frame["cohort"] == name)]
            cells.append((cell["outcome"].to_numpy(), cell["pd"].to_numpy(dtype=float)))
        value = near[near["pair"] == model].set_index("metric")["value"]
        assert np.isclose(value["gini"], np.mean([2 * ai.mt.auc(y, s) - 1 for y, s in cells]),
                          rtol=1e-12, atol=0)
        assert np.isclose(value["abs_log_oe"], np.mean([bi.abs_log_oe(y, s) for y, s in cells]),
                          rtol=1e-12, atol=0)

    admits = cells_file(tmp_path / "admits.csv", builds, {})
    with pytest.raises(SystemExit, match=rf"admits {UNDER} \(2015H1-E, 2015H2-E\), whose scored "
                                         "rows hold"):
        run(full, "admits", "--cells", str(admits))
    short = pd.read_csv(verdict)
    short[short["build_id"] != "2015H2-E"].to_csv(tmp_path / "short.csv", index=False)
    with pytest.raises(SystemExit, match="holds no row for 2015H2-E"):
        run(full, "short", "--cells", str(tmp_path / "short.csv"))


def test_ablation_intervals_leaves_a_cohort_under_the_floors_out_of_the_pooling(tmp_path):
    def matrix_pair(root: Path, cohorts: list[str] | None, name: str) -> tuple[Path, Path]:
        """The build on the primary matrix and on a dti_kept matrix, the same scores on both."""
        primary = write_build(root, "2015H1", "E", cohorts, name=f"{name}-primary")
        ablation = write_build(root, "2015H1", "E", cohorts, name=f"{name}-dti-kept")
        (ablation / "build.json").write_text(json.dumps({
            "ablation": "dti_kept", "features": ["dti", "fico", "ltv"]}), encoding="utf-8")
        return primary, ablation

    full = matrix_pair(tmp_path, None, "full")
    absent = matrix_pair(tmp_path, [c for c in DATES["2015H1"] if c != UNDER], "absent")

    def run(pair: tuple[Path, Path], out: str, *extra: str) -> int:
        return ab.main(["--primary", str(pair[0]), "--ablation", str(pair[1]), "--out-dir",
                        str(tmp_path / out), "--resamples", "20", *extra])

    with pytest.raises(SystemExit, match=f"2015H1-E {UNDER}: the scored rows hold 5,000 rows "
                                         "and 60 defaults.* --cells"):
        run(full, "refused")
    verdict = cells_file(tmp_path / "cells.csv", ["2015H1-E"], {UNDER: False})
    assert run(full, "floors", "--cells", str(verdict), "--check-seeds", "5") == 0
    assert run(absent, "absent", "--check-seeds", "5") == 0
    for name in ("paired.csv", "paired-seeds.csv"):
        same_file(tmp_path / "floors" / name, tmp_path / "absent" / name)
    cells = pd.read_csv(tmp_path / "floors" / "cells.csv")
    assert not cells.loc[cells["cohort"] == UNDER, "floor"].any()
    assert cells.loc[cells["cohort"] != UNDER, "floor"].all()
    kept = cells[cells["cohort"] != UNDER].drop(columns="floor").reset_index(drop=True)
    pd.testing.assert_frame_equal(kept, pd.read_csv(tmp_path / "absent" / "cells.csv"))
    summary = json.loads((tmp_path / "floors" / "summary.json").read_text(encoding="utf-8"))
    assert summary["floors"]["reading"] == "2 of 3 cells above the floors"
    assert summary["floors"]["under"] == [UNDER] and summary["cohorts"] == ["2015H2", "2016H2"]
    admits = cells_file(tmp_path / "admits.csv", ["2015H1-E"], {})
    with pytest.raises(SystemExit, match=f"admits 2015H1-E {UNDER}, whose scored rows hold"):
        run(full, "admits", "--cells", str(admits))


def test_protocol_table_holds_its_mean_over_cohorts_to_the_floors(tmp_path):
    scores = pd.read_parquet(write_build(tmp_path, "2015H1", "E") / "scores.parquet")
    with pytest.raises(SystemExit, match=f"2015H1-E {UNDER}: the scored rows hold 5,000 rows "
                                         "and 60 defaults.* --cells"):
        pt.floor_pooling(scores, "2015H1-E", None)
    verdict = cells_file(tmp_path / "cells.csv", ["2015H1-E"], {UNDER: False})
    kept, under = pt.floor_pooling(scores, "2015H1-E", verdict)
    assert under == [UNDER]
    absent = pd.read_parquet(without(tmp_path, "2015H1", "E") / "scores.parquet")
    read, none = pt.floor_pooling(absent, "2015H1-E", None)
    assert none == [] and read is absent
    pd.testing.assert_frame_equal(kept, absent)
    admits = cells_file(tmp_path / "admits.csv", ["2015H1-E"], {})
    with pytest.raises(SystemExit, match=f"admits 2015H1-E {UNDER}, whose scored rows hold"):
        pt.floor_pooling(scores, "2015H1-E", admits)


def test_between_arm_intervals_reads_no_verdict_over_a_cohort_under_the_floors(tmp_path):
    e = [write_build(tmp_path, d, "E") for d in DATES]
    r = [write_build(tmp_path, d, "R") for d in DATES]

    def run(out: str, *extra: str, arms: tuple[list[Path], list[Path]] | None = None) -> int:
        expanding, rolling = arms or (e, r)
        return ba.main(["--expanding", *map(str, expanding), "--rolling", *map(str, rolling),
                        "--out-dir", str(tmp_path / out), "--resamples", "20", *extra])

    with pytest.raises(SystemExit, match=f"{UNDER}: the scored rows hold 5,000 rows and 60 "
                                         "defaults.* --cells"):
        run("refused")
    assert not (tmp_path / "refused" / "summary.json").exists()
    builds = [f"{d}-{arm}" for d in DATES for arm in "ER"]
    verdict = cells_file(tmp_path / "cells.csv", builds, {UNDER: False})
    assert run("floors", "--cells", str(verdict), "--check-seeds", "5") == 0
    summary = json.loads((tmp_path / "floors" / "summary.json").read_text(encoding="utf-8"))
    # One cell per build date leaves the criterion.
    assert summary["cells_shared"] == 6 and summary["cells_criterion"] == 4
    assert summary["cohorts_under_floors"] == [UNDER]
    assert len(pd.read_csv(tmp_path / "floors" / "cells.csv")) == 6 * len(MODELS)

    # The same inputs with the cohort's rows removed: the resample reaches only the criterion's
    # cohorts, so every row of the reading, interval and seed check alike, is the absent run's.
    # The verdict file of that run admits every cohort it holds, so both pool the same regime.
    absent = ([without(tmp_path, d, "E") for d in DATES], [without(tmp_path, d, "R") for d in DATES])
    every = cells_file(tmp_path / "every.csv", builds, {})
    assert run("absent", "--cells", str(every), "--check-seeds", "5", arms=absent) == 0
    for name in ("paired.csv", "paired-seeds.csv"):
        same_file(tmp_path / "floors" / name, tmp_path / "absent" / name)
    admits = cells_file(tmp_path / "admits.csv", builds, {})
    with pytest.raises(SystemExit, match=f"admits {UNDER}, whose scored rows hold 5,000 rows"):
        run("admits", "--cells", str(admits))
