"""The node script, on what would make a returned file unusable.

The script runs on a machine that has no repository, so what it writes has to
pair with the classical scores by construction: the same columns, the same
rows in the same cohorts, the same outcomes. And it has to survive the way a
free notebook ends, which is by being killed: a second start must skip every
cell already on disk and score only what is missing. Neither model is needed
to test either property, so the estimator is replaced with one that scores a
row from a single column.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("pyarrow")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import score_context as sc

SEED = 20260906


class ColumnModel:
    """Scores a row from `dti` alone, deterministically, and reads nothing else."""

    def __init__(self, categorical):
        self.categorical = categorical
        self.rate = None

    def get_params(self):
        return {"categorical": self.categorical}

    def fit(self, x, y):
        assert isinstance(x, pd.DataFrame)
        assert x["purpose"].dtype == object
        self.rate = float(np.mean(y))
        return self

    def predict_proba(self, x):
        p = np.clip(self.rate + 0.002 * (x["dti"].to_numpy(dtype=float) - 18.0), 0.01, 0.99)
        return np.column_stack([1 - p, p])


def bundle(path: Path, *, seeds=(11, 12), cohorts=("2015Q3", "2015Q4", "2016Q1"),
           rows: int = 40) -> Path:
    rng = np.random.default_rng(SEED)
    stamp = {"build_id": "2015H1-E", "arm": "E", "as_of": "2015-06-30"}
    features = ["dti", "fico_range_low", "purpose"]

    def block(n: int, **columns) -> pd.DataFrame:
        return pd.DataFrame({
            **stamp, **columns,
            "row": rng.choice(100_000, size=n, replace=False),
            "outcome": rng.binomial(1, 0.1, n).astype(np.int8),
            "dti": rng.gamma(3.0, 6.0, n),
            "fico_range_low": rng.normal(690, 30, n).round(),
            "purpose": rng.choice(["car", "credit_card", None], n).astype(object),
        })

    context = pd.concat([block(rows * 2, context_seed=s) for s in seeds], ignore_index=True)
    context["context_seed"] = context["context_seed"].astype("Int64")
    scored = pd.concat([block(rows, cohort=c, age_quarters=k + 1)
                        for k, c in enumerate(cohorts)], ignore_index=True)
    path.mkdir(parents=True, exist_ok=True)
    context.to_parquet(path / sc.CONTEXT_FILE, index=False)
    scored.to_parquet(path / sc.SCORED_FILE, index=False)
    description = {
        "build": {"build_id": "2015H1-E"}, "features": features, "categorical": ["purpose"],
        "context": {"seeds": list(seeds)},
        "files": {name: sc.sha256(path / name) for name in (sc.CONTEXT_FILE, sc.SCORED_FILE)},
    }
    (path / sc.DESCRIPTION_FILE).write_text(json.dumps(description), encoding="utf-8")
    return path


@pytest.fixture
def fake_models(monkeypatch):
    built = []

    def build(name, device, categorical, settings=None):
        built.append((name, device, categorical) if not settings
                     else (name, device, categorical, settings))
        return ColumnModel(categorical)

    monkeypatch.setattr(sc, "build", build)
    monkeypatch.setattr(sc, "MODELS", ("tabpfn", "tabicl"))
    return built


def test_the_output_pairs_with_the_classical_format(tmp_path: Path, fake_models):
    src = bundle(tmp_path / "bundle")
    out = tmp_path / "out"
    node = sc.run(src, out, ["tabpfn"], nearest=2, seeds=None, device="auto", chunk=0,
                  repeat=True)

    scores = pd.read_parquet(out / "scores.parquet")
    reference = pd.read_parquet(out / "reference.parquet")
    assert list(scores.columns) == sc.SCORE_COLUMNS
    assert list(reference.columns) == sc.REFERENCE_COLUMNS
    assert set(scores["cohort"]) == {"2015Q3", "2015Q4"}
    assert set(scores["context_seed"]) == {11, 12}
    assert str(scores["context_seed"].dtype) == "Int64"

    scored = pd.read_parquet(src / sc.SCORED_FILE)
    for (seed, cohort), cell in scores.groupby(["context_seed", "cohort"]):
        expected = scored[scored["cohort"] == cohort]
        assert np.array_equal(cell["row"].to_numpy(), expected["row"].to_numpy())
        assert np.array_equal(cell["outcome"].to_numpy(), expected["outcome"].to_numpy())
        assert cell["age_quarters"].nunique() == 1
    context = pd.read_parquet(src / sc.CONTEXT_FILE)
    for seed, cell in reference.groupby("context_seed"):
        expected = context[context["context_seed"] == seed]
        assert np.array_equal(cell["row"].to_numpy(), expected["row"].to_numpy())

    # The categorical column was declared by index, and the repeat recorded.
    assert fake_models[0] == ("tabpfn", "auto", [2])
    assert len(node["repeats"]) == 2 and node["repeats"][0]["max_abs_difference"] == 0.0
    assert len(node["cells"]) == 2 * 3
    assert node["scored_rows"] == 2 * 2 * 40 and node["reference_rows"] == 2 * 80


def test_a_second_start_scores_only_what_is_missing(tmp_path: Path, fake_models):
    src = bundle(tmp_path / "bundle", seeds=(11,))
    out = tmp_path / "out"
    sc.run(src, out, ["tabicl"], nearest=None, seeds=None, device="auto", chunk=0, repeat=False)
    first = pd.read_parquet(out / "scores.parquet")
    fits_before = len(fake_models)

    # Kill the run after two cohorts: remove the third part and the final files.
    sc.part_path(out, "tabicl", 11, "2016Q1").unlink()
    (out / "scores.parquet").unlink()
    sc.run(src, out, ["tabicl"], nearest=None, seeds=None, device="auto", chunk=0, repeat=False)
    again = pd.read_parquet(out / "scores.parquet")
    assert len(fake_models) == fits_before + 1
    merged = first.merge(again, on=["model", "context_seed", "cohort", "row"])
    assert len(merged) == len(first) == len(again)
    assert np.allclose(merged["pd_x"], merged["pd_y"])

    # Nothing missing: no fit at all.
    sc.run(src, out, ["tabicl"], nearest=None, seeds=None, device="auto", chunk=0, repeat=False)
    assert len(fake_models) == fits_before + 1


def test_chunked_scoring_is_the_same_scoring(tmp_path: Path, fake_models):
    src = bundle(tmp_path / "bundle", seeds=(11,))
    whole = sc.run(src, tmp_path / "whole", ["tabpfn"], nearest=1, seeds=None, device="auto",
                   chunk=0, repeat=False)
    pieces = sc.run(src, tmp_path / "pieces", ["tabpfn"], nearest=1, seeds=None, device="auto",
                    chunk=7, repeat=False)
    a = pd.read_parquet(tmp_path / "whole" / "scores.parquet")
    b = pd.read_parquet(tmp_path / "pieces" / "scores.parquet")
    assert np.array_equal(a["pd"].to_numpy(), b["pd"].to_numpy())
    assert whole["scored_rows"] == pieces["scored_rows"] == 40


def test_a_damaged_bundle_is_refused(tmp_path: Path, fake_models):
    src = bundle(tmp_path / "bundle", seeds=(11,))
    scored = pd.read_parquet(src / sc.SCORED_FILE)
    scored.loc[0, "outcome"] = 1 - scored.loc[0, "outcome"]
    scored.to_parquet(src / sc.SCORED_FILE, index=False)
    with pytest.raises(SystemExit, match="damaged"):
        sc.run(src, tmp_path / "out", ["tabpfn"], nearest=None, seeds=None, device="auto",
               chunk=0, repeat=False)


def test_a_seed_the_bundle_lacks_is_refused(tmp_path: Path, fake_models):
    src = bundle(tmp_path / "bundle", seeds=(11,))
    with pytest.raises(SystemExit, match="no context for seeds"):
        sc.run(src, tmp_path / "out", ["tabpfn"], nearest=None, seeds=[12], device="auto",
               chunk=0, repeat=False)


def rewrite_scored(src: Path, scored: pd.DataFrame) -> None:
    """Puts a new scored.parquet in the bundle and repairs the hash beside it.

    Without the repair a test that rewrites the cells would stop at the
    damaged-bundle refusal, which is a different refusal from the one it is
    about.
    """
    scored.to_parquet(src / sc.SCORED_FILE, index=False)
    description = json.loads((src / sc.DESCRIPTION_FILE).read_text(encoding="utf-8"))
    description["files"][sc.SCORED_FILE] = sc.sha256(src / sc.SCORED_FILE)
    (src / sc.DESCRIPTION_FILE).write_text(json.dumps(description), encoding="utf-8")


def test_a_cell_whose_rows_are_in_its_own_context_is_refused(tmp_path: Path, fake_models):
    src = bundle(tmp_path / "bundle", seeds=(11,))
    context = pd.read_parquet(src / sc.CONTEXT_FILE)
    scored = pd.read_parquet(src / sc.SCORED_FILE)
    # Three rows of the youngest cohort are given row numbers the context holds,
    # which is what a bundle packing several folds of one pool does to every cell.
    borrowed = context["row"].to_numpy()[:3]
    cell = scored.index[scored["cohort"] == "2015Q3"][:3]
    scored.loc[cell, "row"] = borrowed
    rewrite_scored(src, scored)

    out = tmp_path / "out"
    with pytest.raises(SystemExit, match=r"3 of the 40 rows of 2015Q3 are in the context"):
        sc.run(src, out, ["tabpfn"], nearest=None, seeds=None, device="auto", chunk=0,
               repeat=False)
    # Refused before anything was fitted or written: no model was built and the
    # output directory was never created.
    assert fake_models == []
    assert not out.exists()


def test_the_refusal_reads_the_seed_that_would_score_the_cell(tmp_path: Path, fake_models):
    src = bundle(tmp_path / "bundle", seeds=(11, 12))
    context = pd.read_parquet(src / sc.CONTEXT_FILE)
    scored = pd.read_parquet(src / sc.SCORED_FILE)
    # Only the second context draw meets the cell, so scoring with the first
    # alone is allowed and scoring with both is not.
    borrowed = context.loc[context["context_seed"] == 12, "row"].to_numpy()[:2]
    cell = scored.index[scored["cohort"] == "2016Q1"][:2]
    scored.loc[cell, "row"] = borrowed
    rewrite_scored(src, scored)

    sc.run(src, tmp_path / "out-11", ["tabpfn"], nearest=None, seeds=[11], device="auto",
           chunk=0, repeat=False)
    with pytest.raises(SystemExit, match=r"context seed 12: 2 of the 40 rows of 2016Q1"):
        sc.run(src, tmp_path / "out-both", ["tabpfn"], nearest=None, seeds=None, device="auto",
               chunk=0, repeat=False)


def test_a_cohort_the_run_does_not_score_is_not_read(tmp_path: Path, fake_models):
    src = bundle(tmp_path / "bundle", seeds=(11,))
    context = pd.read_parquet(src / sc.CONTEXT_FILE)
    scored = pd.read_parquet(src / sc.SCORED_FILE)
    # The oldest cohort meets the context; the youngest does not.
    cell = scored.index[scored["cohort"] == "2016Q1"][:2]
    scored.loc[cell, "row"] = context["row"].to_numpy()[:2]
    rewrite_scored(src, scored)

    # Scoring only the youngest cohort writes no cell that met its context.
    sc.run(src, tmp_path / "out-near", ["tabpfn"], nearest=1, seeds=None, device="auto",
           chunk=0, repeat=False)
    with pytest.raises(SystemExit, match=r"2 of the 40 rows of 2016Q1"):
        sc.run(src, tmp_path / "out-all", ["tabpfn"], nearest=None, seeds=None, device="auto",
               chunk=0, repeat=False)


def test_the_reference_cell_may_be_the_context(tmp_path: Path, fake_models):
    # The reference is the context scored on itself, which is the whole point of
    # it, so the refusal must not read it as a cell that meets its own context.
    src = bundle(tmp_path / "bundle", seeds=(11,))
    out = tmp_path / "out"
    sc.run(src, out, ["tabpfn"], nearest=None, seeds=None, device="auto", chunk=0, repeat=False)
    reference = pd.read_parquet(out / "reference.parquet")
    context = pd.read_parquet(src / sc.CONTEXT_FILE)
    assert set(reference["row"]) == set(context.loc[context["context_seed"] == 11, "row"])


def test_the_nearest_cohorts_are_the_youngest():
    scored = pd.DataFrame({"cohort": ["2016Q1", "2015Q3", "2015Q4", "2015Q3"]})
    assert sc.select_cohorts(scored, 2) == ["2015Q3", "2015Q4"]
    assert sc.select_cohorts(scored, None) == ["2015Q3", "2015Q4", "2016Q1"]


def test_a_model_off_its_defaults_is_written_under_its_own_name(tmp_path: Path, fake_models):
    src = bundle(tmp_path / "bundle", seeds=(11,))
    out = tmp_path / "out"
    node = sc.run(src, out, ["tabpfn"], nearest=1, seeds=None, device="auto", chunk=0,
                  repeat=False, settings={"temperature": 1.0, "balance": True})

    # The settings reached the constructor, and only the settings that were set.
    assert fake_models[0] == ("tabpfn", "auto", [2], {"temperature": 1.0, "balance": True})
    # Rows, parts and the node record all carry the tagged name, so they sit
    # beside the default rows instead of replacing them.
    assert set(pd.read_parquet(out / "scores.parquet")["model"]) == {"tabpfn@t1+bal"}
    assert set(pd.read_parquet(out / "reference.parquet")["model"]) == {"tabpfn@t1+bal"}
    assert sorted(p.name for p in (out / "parts").glob("*.parquet")) == [
        "tabpfn@t1+bal-11-2015Q3.parquet", "tabpfn@t1+bal-11-reference.parquet"]
    assert list(node["models"]) == ["tabpfn@t1+bal/11"]
    assert node["command"]["settings"] == {"temperature": 1.0, "balance": True}

    # At the defaults the name is bare, whatever the command passed as unset.
    assert sc.variant("tabicl", {"temperature": None, "balance": False}) == "tabicl"
    assert sc.variant("tabicl", {"temperature": 1.0}) == "tabicl@t1"
    assert sc.variant("tabpfn", {"temperature": 0.9}) == "tabpfn@t0.9"


def test_balance_is_refused_for_tabicl(tmp_path: Path):
    with pytest.raises(SystemExit, match="tabicl has no such setting"):
        sc.build("tabicl", "auto", [], {"balance": True})
