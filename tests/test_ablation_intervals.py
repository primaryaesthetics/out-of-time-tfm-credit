"""The ablation reading, on what would make a difference between matrices wrong.

A difference between two matrices is only the matrix's if both hold the
same rows with the same outcomes; the reading refuses when they do not, and
when the two groups are not two matrices. Its statistics are checked where
the answer is known: an ablation that changes no score reads zero with an
interval that holds zero, and a gain planted in one model and not in the
control is read as a difference from the control's.
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

import ablation_intervals as ab

SEED = 20260914
COHORTS = ("2005H1", "2005H2", "2006H1")
ROWS = 1500
PRIMARY = ["borrowers", "cltv", "fico", "upb_to_limit"]
DTI_KEPT = PRIMARY + ["dti"]


@pytest.fixture(autouse=True)
def small_cohorts_clear_the_floors(monkeypatch):
    """The synthetic cohorts hold 1,500 rows, not a book's thousands; the floors are lowered
    so that they pool. tests/test_floors.py reads the floors themselves."""
    monkeypatch.setattr(ab.bi, "FLOOR_ROWS", 0)
    monkeypatch.setattr(ab.bi, "FLOOR_DEFAULTS", 0)


def latent(cohort: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One cohort's rows, a latent risk and outcomes drawn from it, the same on every matrix."""
    rng = np.random.default_rng(SEED + sum(map(ord, cohort)))
    rows = np.sort(rng.choice(1_000_000, size=ROWS, replace=False))
    x = rng.normal(size=ROWS)
    y = rng.binomial(1, 1.0 / (1.0 + np.exp(-(-2.4 + 1.2 * x))))
    return rows, x, y


def score(x: np.ndarray, sharpness: float, noise_seed: int, noise: float = 0.8) -> np.ndarray:
    """A score on the latent risk: sharpness 1.2 with no noise is the true probability."""
    jitter = np.random.default_rng(noise_seed).normal(size=x.size)
    return 1.0 / (1.0 + np.exp(-(-2.4 + sharpness * x + noise * jitter)))


def frame(models: dict[str, list], sharpness: dict[str, float], cohorts=COHORTS,
          noise: dict[str, float] | None = None) -> pd.DataFrame:
    parts = []
    for k, cohort in enumerate(cohorts):
        rows, x, y = latent(cohort)
        for model, seeds in models.items():
            for seed in seeds:
                parts.append(pd.DataFrame({
                    "build_id": "2004H2-E", "arm": "E", "as_of": "2004-12-31", "model": model,
                    "context_seed": seed, "cohort": cohort, "age_quarters": 2 * k + 1,
                    "row": rows, "outcome": y,
                    "pd": score(x, sharpness.get(model, 0.8), (seed or 7) + 31 * k,
                                (noise or {}).get(model, 0.8)),
                }))
    out = pd.concat(parts, ignore_index=True)
    out["context_seed"] = out["context_seed"].astype("Int64")
    return out


def write_classical(root: Path, name: str, features: list[str], ablation: str | None,
                    sharpness: dict[str, float] | None = None) -> Path:
    directory = root / name
    directory.mkdir()
    frame({"scorecard": [None], "gbm": [None], "gbm-50k": [11, 12]},
          sharpness or {}).to_parquet(directory / "scores.parquet", index=False)
    (directory / "build.json").write_text(json.dumps({"ablation": ablation, "features": features}),
                                          encoding="utf-8")
    return directory


def write_tfm(root: Path, name: str, features: list[str], model: str = "tabicl",
              sharpness: dict[str, float] | None = None, cohorts=COHORTS[:2],
              noise: dict[str, float] | None = None) -> Path:
    directory = root / name
    directory.mkdir()
    frame({model: [11]}, sharpness or {}, cohorts, noise).to_parquet(
        directory / "scores.parquet", index=False)
    (directory / "node.json").write_text(json.dumps({"bundle": {"features": features}}),
                                         encoding="utf-8")
    return directory


def run(primary: list[Path], ablation: list[Path], out: Path, *extra: str) -> int:
    return ab.main(["--primary", *map(str, primary), "--ablation", *map(str, ablation),
                    "--out-dir", str(out), "--resamples", "40", *extra])


def read(out: Path) -> tuple[pd.DataFrame, dict]:
    return (pd.read_csv(out / "paired.csv"),
            json.loads((out / "summary.json").read_text(encoding="utf-8")))


def test_an_ablation_that_changes_no_score_reads_zero_inside_its_interval(tmp_path):
    primary = [write_classical(tmp_path, "p", PRIMARY, None), write_tfm(tmp_path, "pt", PRIMARY)]
    ablation = [write_classical(tmp_path, "a", DTI_KEPT, "dti_kept"),
                write_tfm(tmp_path, "at", DTI_KEPT)]
    out = tmp_path / "out"
    assert run(primary, ablation, out) == 0
    paired, summary = read(out)
    differences = paired[paired["is_difference"]]
    assert set(differences["kind"]) == {"diff", "did"}
    assert (differences["value"] == 0).all()
    assert (differences["ci_lo"] <= 0).all() and (differences["ci_hi"] >= 0).all()
    assert not differences["excludes_zero"].astype(bool).any()
    assert summary["ablation"] == "dti_kept"
    assert summary["matrices"]["added"] == ["dti"] and summary["matrices"]["removed"] == []
    # The foundation model scored two cohorts and one draw: the pooling takes those.
    assert summary["cohorts"] == list(COHORTS[:2]) and summary["cohorts_scored"] == 3
    assert summary["models"]["gbm-50k"] == [11] and summary["draws_not_pooled"] == {"gbm-50k": [12]}
    assert summary["cell_check"]["cells"] == 3 * 4 + 2
    assert summary["trigger"]["excludes_zero"] == []
    assert (out / "ablation-differences.png").is_file() and (out / "cells.csv").is_file()


def test_a_gain_planted_in_one_model_is_read_against_the_control(tmp_path):
    primary = [write_classical(tmp_path, "p", PRIMARY, None),
               write_tfm(tmp_path, "pt", PRIMARY, sharpness={"tabicl": 0.4})]
    # The ablation turns the foundation model into the true probability and leaves every
    # classical score as it was: a better rank and a better Brier score, for it alone.
    ablation = [write_classical(tmp_path, "a", DTI_KEPT, "dti_kept"),
                write_tfm(tmp_path, "at", DTI_KEPT, sharpness={"tabicl": 1.2},
                          noise={"tabicl": 0.0})]
    out = tmp_path / "out"
    assert run(primary, ablation, out, "--check-seeds", "5,6") == 0
    paired, summary = read(out)
    did = paired[(paired["kind"] == "did") & (paired["model"] == "tabicl")].set_index("metric")
    diff = paired[(paired["kind"] == "diff")].set_index(["metric", "model"])
    assert diff.loc[("auc", "gbm-50k"), "value"] == 0
    assert did.loc["auc", "value"] > 0 and bool(did.loc["auc", "excludes_zero"])
    assert did.loc["auc", "value"] == pytest.approx(diff.loc[("auc", "tabicl"), "value"])
    assert did.loc["brier", "value"] < 0 and bool(did.loc["brier", "excludes_zero"])
    assert set(summary["trigger"]["excludes_zero"]) == {"tabicl (auc)", "tabicl (brier)"}
    assert summary["bootstrap"]["seed_check"]["seeds"] == [5, 6]
    assert (out / "paired-seeds.csv").is_file()
    # The per-model means are the per-cohort metrics averaged over the pooled cohorts.
    cells = pd.read_csv(out / "cells.csv")
    mean = paired[(paired["kind"] == "mean") & (paired["model"] == "tabicl")
                  & (paired["metric"] == "auc") & (paired["matrix"] == "dti_kept")]["value"].iloc[0]
    want = cells[(cells["model"] == "tabicl") & (cells["matrix"] == "dti_kept")]["auc"].mean()
    assert mean == pytest.approx(want, abs=1e-12)


def test_a_gain_in_a_model_off_its_library_settings_does_not_fire_the_trigger(tmp_path):
    primary = [write_classical(tmp_path, "p", PRIMARY, None), write_tfm(tmp_path, "pt", PRIMARY),
               write_tfm(tmp_path, "pt1", PRIMARY, model="tabicl@t1",
                         sharpness={"tabicl@t1": 0.4})]
    ablation = [write_classical(tmp_path, "a", DTI_KEPT, "dti_kept"),
                write_tfm(tmp_path, "at", DTI_KEPT),
                write_tfm(tmp_path, "at1", DTI_KEPT, model="tabicl@t1",
                          sharpness={"tabicl@t1": 1.2}, noise={"tabicl@t1": 0.0})]
    out = tmp_path / "out"
    assert run(primary, ablation, out) == 0
    paired, summary = read(out)
    did = paired[(paired["kind"] == "did")].set_index(["metric", "model"])
    assert bool(did.loc[("auc", "tabicl@t1"), "excludes_zero"])
    assert not bool(did.loc[("auc", "tabicl"), "excludes_zero"])
    assert summary["trigger"]["excludes_zero"] == []


def test_matrices_that_hold_other_rows_or_outcomes_are_refused(tmp_path):
    primary = [write_classical(tmp_path, "p", PRIMARY, None)]
    ablation = [write_classical(tmp_path, "a", DTI_KEPT, "dti_kept")]
    scores = pd.read_parquet(ablation[0] / "scores.parquet")
    pristine = scores.copy()
    victim = scores[(scores["model"] == "gbm") & (scores["cohort"] == "2005H2")].index[4]
    scores.loc[victim, "row"] = 5_000_000
    scores.to_parquet(ablation[0] / "scores.parquet", index=False)
    with pytest.raises(SystemExit, match="different rows"):
        run(primary, ablation, tmp_path / "out")
    flipped = pristine.copy()
    flipped.loc[victim, "outcome"] = 1 - flipped.loc[victim, "outcome"]
    flipped.to_parquet(ablation[0] / "scores.parquet", index=False)
    with pytest.raises(SystemExit, match="outcome differs"):
        run(primary, ablation, tmp_path / "out")
    short = pristine.drop(index=victim)
    short.to_parquet(ablation[0] / "scores.parquet", index=False)
    with pytest.raises(SystemExit, match="rows over the same cells"):
        run(primary, ablation, tmp_path / "out")


def test_groups_that_are_not_two_matrices_are_refused(tmp_path):
    primary = write_classical(tmp_path, "p", PRIMARY, None)
    same = write_classical(tmp_path, "same", PRIMARY, "dti_kept")
    with pytest.raises(SystemExit, match="same columns"):
        run([primary], [same], tmp_path / "out")
    declared = write_classical(tmp_path, "declared", PRIMARY, "upb_nominal")
    ablation = write_classical(tmp_path, "a", DTI_KEPT, "dti_kept")
    with pytest.raises(SystemExit, match="named as primary declares"):
        run([declared], [ablation], tmp_path / "out")
    with pytest.raises(SystemExit, match="declare upb_nominal|--name"):
        run([primary], [ablation], tmp_path / "out", "--name", "upb_nominal")
    mixed = write_tfm(tmp_path, "mixed", PRIMARY)
    with pytest.raises(SystemExit, match="one group, one matrix"):
        run([primary], [ablation, mixed], tmp_path / "out")
    missing = write_tfm(tmp_path, "only-primary", PRIMARY, model="tabpfn")
    with pytest.raises(SystemExit, match="different models"):
        run([primary, missing], [ablation], tmp_path / "out")


def test_cohorts_names_the_cells_read_when_one_group_scored_more(tmp_path):
    # A foundation model scored on every cohort of the primary matrix and on two of the ablation's.
    primary = [write_classical(tmp_path, "p", PRIMARY, None),
               write_tfm(tmp_path, "pt", PRIMARY, cohorts=COHORTS)]
    ablation = [write_classical(tmp_path, "a", DTI_KEPT, "dti_kept"),
                write_tfm(tmp_path, "at", DTI_KEPT)]
    with pytest.raises(SystemExit, match="do not hold the same cells"):
        run(primary, ablation, tmp_path / "refused")
    out = tmp_path / "out"
    assert run(primary, ablation, out, "--cohorts", ",".join(COHORTS[:2])) == 0
    _, summary = read(out)
    assert summary["cohorts"] == list(COHORTS[:2])
    assert summary["cell_check"]["cells"] == 2 * 4 + 2
    with pytest.raises(SystemExit, match="do not hold"):
        run(primary, ablation, tmp_path / "missing", "--cohorts", ",".join(COHORTS))
