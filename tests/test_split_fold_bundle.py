"""A fold's bundle holds that fold's context and that fold's cells, and nothing else.

Every assertion here constructs the mistake the splitter is for. The one that
matters is `test_a_context_that_meets_its_own_cell_is_refused`: a bundle whose
context holds the rows of a cell it scores puts those outcomes in front of the
model, which no downstream check would see, because a scored cell carries no
record of what conditioned it.
"""
import importlib.util
import json
import pathlib

import pandas as pd
import pytest

SPEC = importlib.util.spec_from_file_location(
    "split_fold_bundle",
    pathlib.Path(__file__).resolve().parents[1] / "scripts" / "split_fold_bundle.py")
split_fold_bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(split_fold_bundle)

SEEDS = [20260911, 20260912]
FEATURES = {"annual_inc": 1.0, "dti": 2.0}


def context_rows(fold, rows):
    return pd.DataFrame({"build_id": "2015H1-E", "arm": "E", "as_of": "2015-06-30",
                         "context_seed": [s for s in SEEDS for _ in rows],
                         "fold": fold, "row": list(rows) * len(SEEDS),
                         "outcome": 0, **FEATURES})


def cell_rows(name, rows):
    return pd.DataFrame({"build_id": "2015H1-E", "arm": "E", "as_of": "2015-06-30",
                         "cohort": name, "age_quarters": 0, "row": list(rows),
                         "outcome": 0, **FEATURES})


def build(tmp_path, context, scored, *, name="folds-2to5"):
    source = tmp_path / name
    source.mkdir()
    context.to_parquet(source / "context.parquet", index=False)
    scored.to_parquet(source / "scored.parquet", index=False)
    (source / "bundle.json").write_text(json.dumps({
        "build": {"build_id": "2015H1-E"}, "features": list(FEATURES),
        "context": {"rows": 3, "seeds": SEEDS,
                    "sizes": {str(s): len(context) // len(SEEDS) for s in SEEDS}},
        "cohorts": {n: int((scored["cohort"] == n).sum()) for n in scored["cohort"].unique()},
        "files": {"context.parquet": "aa", "scored.parquet": "bb"},
        "in_time": {"folds": [2, 3], "note": "cells are a fold's parts"},
    }), encoding="utf-8")
    return source


def two_folds(tmp_path, **kwargs):
    context = pd.concat([context_rows(2, [10, 11, 12]), context_rows(3, [20, 21, 22])],
                        ignore_index=True)
    scored = pd.concat([cell_rows("fold2-test", [20, 21]), cell_rows("fold2-validation", [22]),
                        cell_rows("fold3-test", [10, 11]), cell_rows("fold3-validation", [12])],
                       ignore_index=True)
    return build(tmp_path, context, scored, **kwargs)


def test_each_fold_gets_its_own_rows(tmp_path):
    source = two_folds(tmp_path)
    out = tmp_path / "out"
    record = split_fold_bundle.split(source, out, None, "fold")

    assert sorted(record["bundles"]) == ["folds-2to5-fold2", "folds-2to5-fold3"]
    two = pd.read_parquet(out / "folds-2to5-fold2" / "context.parquet")
    assert set(two["fold"]) == {2}
    assert sorted(set(two["row"])) == [10, 11, 12]
    cells = pd.read_parquet(out / "folds-2to5-fold2" / "scored.parquet")
    assert sorted(cells["cohort"].unique()) == ["fold2-test", "fold2-validation"]


def test_the_written_bundles_partition_the_source(tmp_path):
    source = two_folds(tmp_path)
    out = tmp_path / "out"
    split_fold_bundle.split(source, out, None, "fold")

    directories = sorted(d for d in out.iterdir() if d.is_dir())
    for name in ("context.parquet", "scored.parquet"):
        parts = pd.concat([pd.read_parquet(d / name) for d in directories], ignore_index=True)
        whole = pd.read_parquet(source / name)
        assert len(parts) == len(whole)
        assert sorted(parts["row"].tolist()) == sorted(whole["row"].tolist())


def test_a_context_that_meets_its_own_cell_is_refused(tmp_path):
    """The mistake: fold two's context holds rows of fold two's own test cell."""
    context = pd.concat([context_rows(2, [10, 11, 12]), context_rows(3, [20, 21, 22])],
                        ignore_index=True)
    scored = pd.concat([cell_rows("fold2-test", [11, 20]), cell_rows("fold2-validation", [22]),
                        cell_rows("fold3-test", [10]), cell_rows("fold3-validation", [12])],
                       ignore_index=True)
    source = build(tmp_path, context, scored)
    with pytest.raises(SystemExit, match=r"1 of the 2 rows of fold2-test"):
        split_fold_bundle.split(source, tmp_path / "out", None, "fold")


def test_the_description_is_narrowed_to_the_fold(tmp_path):
    source = two_folds(tmp_path)
    out = tmp_path / "out"
    split_fold_bundle.split(source, out, None, "fold")

    written = json.loads((out / "folds-2to5-fold3" / "bundle.json").read_text(encoding="utf-8"))
    assert written["in_time"]["folds"] == [3]
    assert written["cohorts"] == {"fold3-test": 2, "fold3-validation": 1}
    assert written["context"] == {"rows": 3, "seeds": SEEDS,
                                  "sizes": {"20260911": 3, "20260912": 3}}
    assert written["split_from"] == {"bundle": "folds-2to5", "fold": 3,
                                     "files": {"context.parquet": "aa", "scored.parquet": "bb"}}
    assert written["files"]["context.parquet"] != "aa"
    assert written["build"] == {"build_id": "2015H1-E"}


def test_a_fold_with_no_cell_is_refused(tmp_path):
    context = pd.concat([context_rows(2, [10, 11, 12]), context_rows(4, [30, 31, 32])],
                        ignore_index=True)
    scored = pd.concat([cell_rows("fold2-test", [30]), cell_rows("fold2-validation", [31])],
                       ignore_index=True)
    source = build(tmp_path, context, scored)
    with pytest.raises(SystemExit, match="fold 4: no cell"):
        split_fold_bundle.split(source, tmp_path / "out", None, "fold")


def test_a_fold_the_source_does_not_hold_is_refused(tmp_path):
    source = two_folds(tmp_path)
    with pytest.raises(SystemExit, match=r"holds folds \[2, 3\]"):
        split_fold_bundle.split(source, tmp_path / "out", [2, 5], "fold")


def test_draws_of_unequal_size_are_refused(tmp_path):
    context = pd.concat([context_rows(2, [10, 11, 12]), context_rows(3, [20, 21, 22])],
                        ignore_index=True)
    context = context.drop(index=context.index[-1]).reset_index(drop=True)
    scored = pd.concat([cell_rows("fold2-test", [20, 21]), cell_rows("fold3-test", [10, 11])],
                       ignore_index=True)
    source = build(tmp_path, context, scored)
    with pytest.raises(SystemExit, match="not one size"):
        split_fold_bundle.split(source, tmp_path / "out", None, "fold")
