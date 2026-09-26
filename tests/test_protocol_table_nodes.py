"""The protocol table on a foundation model's node directories, one fold each.

A node writes its cells as `fold<k>-test` and `fold<k>-validation` with no
fold column, and its reference is that fold's context. The folds partition
one pool, so one row sits in several folds' contexts with another
probability each time: a fold's stability index has to be read against its
own context and no other's.
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

import protocol_table as pt

from outoftime import metrics as mt

BUILD = {"build_id": "T-E", "arm": "E", "as_of": "2015-06-30"}
SEEDS = (11, 12)


def frame(rows, outcome, score, **columns):
    return pd.DataFrame({**BUILD, **columns, "row": rows, "outcome": outcome, "pd": score})


def write(d: Path, scores: pd.DataFrame, reference: pd.DataFrame) -> Path:
    d.mkdir(parents=True)
    scores.to_parquet(d / "scores.parquet")
    reference.to_parquet(d / "reference.parquet")
    return d


def book(tmp: Path):
    """Two folds of a 4,000-row pool, a classical folds run and one node directory per fold."""
    rng = np.random.default_rng(7)
    pool = np.arange(4_000)
    y = rng.binomial(1, 0.1, pool.size)
    fold_of = np.repeat([1, 2], 2_000)
    cells, classical, classical_ref, thresholds = [], [], [], []
    nodes = []
    for fold in (1, 2):
        held = pool[fold_of == fold]
        test, validation = held[:1_000], held[1_000:]
        rest = pool[fold_of != fold]
        for part, rows in (("test", test), ("validation", validation)):
            cohort = f"fold{fold}-{part}"
            cells.append(pd.DataFrame({"cohort": cohort, "row": rows}))
            s = np.clip(0.1 + 0.1 * (y[rows] - 0.1) + rng.normal(0, 0.03, rows.size), 0.01, 0.9)
            classical.append(frame(rows, y[rows], s, fold=fold, part=part, model="scorecard",
                                   context_seed=pd.NA, cohort=cohort, age_quarters=0))
        classical_ref.append(frame(rest, y[rest], rng.uniform(0.02, 0.3, rest.size), fold=fold,
                                   model="scorecard", context_seed=pd.NA))
        thresholds.append({"fold": fold, "model": "scorecard", "context_seed": None,
                           "threshold": 0.12})
        # The node: its context is drawn from the other fold's rows, at a
        # level that differs between the folds, so a reference pooled over
        # both would move every fold's stability index.
        node_scores, node_ref = [], []
        for seed in SEEDS:
            context = pool[:1_500] if fold == 2 else pool[2_000:3_500]
            shift = 0.09 if fold == 1 else 0.13
            node_ref.append(frame(context, y[context],
                                  np.clip(rng.normal(shift, 0.04, context.size), 0.01, 0.9),
                                  model="tfm", context_seed=seed))
            for part, rows in (("test", test), ("validation", validation)):
                s = np.clip(0.1 + 0.1 * (y[rows] - 0.1) + rng.normal(0, 0.03, rows.size),
                            0.01, 0.9)
                node_scores.append(frame(rows, y[rows], s, model="tfm", context_seed=seed,
                                         cohort=f"fold{fold}-{part}", age_quarters=0))
        nodes.append(write(tmp / f"node-fold{fold}", pd.concat(node_scores, ignore_index=True),
                           pd.concat(node_ref, ignore_index=True)))
    folds = write(tmp / "folds", pd.concat(classical, ignore_index=True),
                  pd.concat(classical_ref, ignore_index=True))
    pd.concat(cells, ignore_index=True).to_parquet(folds / "scored.parquet")
    (folds / "folds.json").write_text(json.dumps({
        "build": {"build_id": BUILD["build_id"]}, "protocol": {"fold_seed": 1},
        "thresholds": thresholds}), encoding="utf-8")
    # Out of time: one cohort above the floors for both models.
    rows = np.arange(10_000, 16_000)
    yo = rng.binomial(1, 0.1, rows.size)
    out = []
    for model, seed in (("scorecard", pd.NA), ("tfm", SEEDS[0]), ("tfm", SEEDS[1])):
        s = np.clip(0.1 + 0.1 * (yo - 0.1) + rng.normal(0, 0.03, rows.size), 0.01, 0.9)
        out.append(frame(rows, yo, s, model=model, context_seed=seed, cohort="2016Q1",
                         age_quarters=2))
    reference = pd.concat([frame(pool, y, rng.uniform(0.02, 0.3, pool.size), model=m,
                                 context_seed=s)
                           for m, s in (("scorecard", pd.NA), ("tfm", SEEDS[0]),
                                        ("tfm", SEEDS[1]))], ignore_index=True)
    oot = write(tmp / "oot", pd.concat(out, ignore_index=True), reference)
    return folds, nodes, oot


def test_a_node_directory_is_given_the_fold_its_cells_name(tmp_path):
    _, nodes, _ = book(tmp_path)
    scores, reference = pt.load_node_scores(nodes)
    assert set(zip(scores["fold"], scores["part"], scores["cohort"])) == {
        (1, "test", "fold1-test"), (1, "validation", "fold1-validation"),
        (2, "test", "fold2-test"), (2, "validation", "fold2-validation")}
    assert sorted(reference["fold"].unique()) == [1, 2]
    assert not reference.duplicated(["fold", "model", "context_seed", "row"]).any()


def test_each_fold_reads_its_own_context_and_no_other(tmp_path):
    folds, nodes, oot = book(tmp_path)
    out = tmp_path / "table"
    assert pt.main([str(folds), "--in-time-tfm", *map(str, nodes), "--out-of-time", str(oot),
                    "--out-dir", str(out)]) == 0
    cells = pd.read_csv(out / "cells.csv")
    scores, reference = pt.load_node_scores(nodes)
    for fold in (1, 2):
        for seed in SEEDS:
            test = scores[(scores["fold"] == fold) & (scores["part"] == "test")
                          & (scores["context_seed"] == seed)].sort_values("row")
            own = reference[(reference["fold"] == fold) & (reference["context_seed"] == seed)]
            pooled = reference[reference["context_seed"] == seed]
            expected = mt.psi(own["pd"], test["pd"], edges=mt.psi_edges(own["pd"])).value
            wrong = mt.psi(pooled["pd"], test["pd"], edges=mt.psi_edges(pooled["pd"])).value
            got = cells[(cells["protocol"] == pt.IN_TIME) & (cells["model"] == "tfm")
                        & (cells["context_seed"] == seed)
                        & (cells["unit"] == f"fold {fold}")]["psi"]
            assert len(got) == 1
            assert np.isfinite(expected) and got.iloc[0] == pytest.approx(expected, rel=1e-12)
            assert abs(expected - wrong) > 0.01


def test_a_directory_holding_two_folds_is_refused(tmp_path):
    _, nodes, _ = book(tmp_path)
    s1 = pd.read_parquet(nodes[0] / "scores.parquet")
    s2 = pd.read_parquet(nodes[1] / "scores.parquet")
    both = write(tmp_path / "both", pd.concat([s1, s2], ignore_index=True),
                 pd.read_parquet(nodes[0] / "reference.parquet"))
    with pytest.raises(SystemExit, match="one fold's bundle"):
        pt.load_node_scores([both])


def test_a_cell_named_otherwise_is_refused(tmp_path):
    _, nodes, _ = book(tmp_path)
    s = pd.read_parquet(nodes[0] / "scores.parquet")
    s.loc[s.index[:5], "cohort"] = "2016Q1"
    odd = write(tmp_path / "odd", s, pd.read_parquet(nodes[0] / "reference.parquet"))
    with pytest.raises(SystemExit, match="not named fold"):
        pt.load_node_scores([odd])


def test_the_same_fold_given_twice_is_refused(tmp_path):
    folds, nodes, oot = book(tmp_path)
    with pytest.raises(SystemExit, match="share a key"):
        pt.main([str(folds), "--in-time-tfm", str(nodes[0]), str(nodes[0]), str(nodes[1]),
                 "--out-of-time", str(oot), "--out-dir", str(tmp_path / "table")])
