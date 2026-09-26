"""The intervals script, on the two things that would make its table wrong.

The bootstrap's noise floor rests on every cell of a cohort holding the same
rows in the same order with the same outcome; the loader has to refuse a file
where that is not so rather than pair rows that are not pairs. And the PSI the
bootstrap recomputes on a resample has to be the PSI the metrics module
reports on the unresampled cell, or the two tables disagree with each other.
"""

from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("matplotlib")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_intervals as bi

from outoftime import metrics as mt

SEED = 20260905


@pytest.fixture(autouse=True)
def small_cohorts_clear_the_floors(monkeypatch):
    """The synthetic cohorts hold hundreds of rows, not a book's thousands; the floors are
    lowered so that they pool. tests/test_floors.py reads the floors themselves."""
    monkeypatch.setattr(bi, "FLOOR_ROWS", 0)
    monkeypatch.setattr(bi, "FLOOR_DEFAULTS", 0)


def score_file(seed: int = SEED, *, cohorts: int = 2, rows: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    frames = []
    for k in range(cohorts):
        positions = rng.choice(100_000, size=rows, replace=False)
        y = rng.binomial(1, 0.1, rows)
        for model, seeds in (("scorecard", [None]), ("gbm-50k", [11, 12])):
            for s in seeds:
                frames.append(pd.DataFrame({
                    "build_id": "2015H1-E", "arm": "E", "model": model, "context_seed": s,
                    "cohort": f"2015Q{k + 3}", "age_quarters": k + 1,
                    "row": positions, "outcome": y, "pd": rng.uniform(0.01, 0.2, rows),
                }))
    out = pd.concat(frames, ignore_index=True)
    out["context_seed"] = out["context_seed"].astype("Int64")
    return out.sample(frac=1.0, random_state=seed).reset_index(drop=True)


def test_loader_aligns_every_cell_to_the_cohort_rows():
    scores = score_file()
    cohorts, models = bi.load_cohorts(scores)
    assert models == {"scorecard": [None], "gbm-50k": [11, 12]}
    assert sorted(cohorts) == ["2015Q3", "2015Q4"]
    cohort = cohorts["2015Q3"]
    assert cohort.draws == 2
    expected = scores[(scores["cohort"] == "2015Q3") & (scores["model"] == "scorecard")]
    expected = expected.sort_values("row")
    assert np.array_equal(cohort.outcome, expected["outcome"].to_numpy())
    assert np.array_equal(cohort.scores["scorecard"], expected["pd"].to_numpy())
    drawn = cohort.realise(1)
    assert drawn.draw == 1
    second = scores[(scores["cohort"] == "2015Q3") & (scores["context_seed"] == 12)]
    assert np.array_equal(drawn.scores["gbm-50k"], second.sort_values("row")["pd"].to_numpy())


def test_loader_refuses_cells_that_do_not_share_their_rows():
    scores = score_file()
    broken = scores.copy()
    victim = broken[(broken["cohort"] == "2015Q4") & (broken["model"] == "scorecard")].index[0]
    broken.loc[victim, "row"] = 999_999
    with pytest.raises(SystemExit, match="different rows"):
        bi.load_cohorts(broken)
    flipped = scores.copy()
    victim = flipped[(flipped["cohort"] == "2015Q4") & (flipped["context_seed"] == 11)].index[0]
    flipped.loc[victim, "outcome"] = 1 - flipped.loc[victim, "outcome"]
    with pytest.raises(SystemExit, match="different outcome"):
        bi.load_cohorts(flipped)


def test_resampled_psi_is_the_module_psi_on_the_unresampled_cell():
    rng = np.random.default_rng(SEED)
    reference = rng.beta(2, 20, 5_000)
    current = rng.beta(2, 15, 1_000)
    edges = mt.psi_edges(reference)
    counts = np.bincount(np.searchsorted(edges, reference, side="right"), minlength=edges.size + 1)
    share = counts / reference.size
    assert bi.psi_value(current, edges, share) == pytest.approx(
        mt.psi(reference, current, edges=edges).value, abs=1e-12
    )


def test_pooled_statistics_pair_every_model_and_follow_the_draw():
    scores = score_file()
    cohorts, models = bi.load_cohorts(scores)
    reference = pd.concat([
        pd.DataFrame({"model": "scorecard", "context_seed": None, "pd": np.linspace(0.01, 0.2, 500)}),
        pd.DataFrame({"model": "gbm-50k", "context_seed": 11, "pd": np.linspace(0.01, 0.2, 500)}),
        pd.DataFrame({"model": "gbm-50k", "context_seed": 12, "pd": np.linspace(0.05, 0.9, 500)}),
    ], ignore_index=True)
    reference["context_seed"] = reference["context_seed"].astype("Int64")
    edges = bi.reference_edges(reference)
    shares = bi.reference_shares(reference, edges)
    compute = bi.pooled_statistics(models, edges, shares, None)
    names = set(compute({k: c.realise(0) for k, c in cohorts.items()}))
    assert "cox_slope_deviation" in bi.POOLED_METRICS
    # Beside the statistics, the count of cells each Cox statistic left out.
    assert names == {
        f"{m}|{n}" for m in bi.POOLED_METRICS
        for n in ("mean|scorecard", "mean|gbm-50k", "diff|gbm-50k|scorecard")
    } | {f"{bi.LEFT_OUT}|{m}" for m in bi.COX_METRICS}
    # The control's PSI reads against the reference of the draw it carries:
    # the first draw's reference spans the scores, the second's leaves its
    # upper bins empty of them.
    first = compute({k: c.realise(0) for k, c in cohorts.items()})["psi|mean|gbm-50k"]
    second = compute({k: c.realise(1) for k, c in cohorts.items()})["psi|mean|gbm-50k"]
    assert np.isfinite(first) and np.isinf(second)


def test_the_pooling_takes_the_cohorts_every_cell_scored():
    scores = score_file(cohorts=3)
    # A foundation model scored only the two youngest cohorts.
    young = scores[(scores["model"] == "scorecard") & (scores["cohort"] != "2015Q5")].copy()
    young["model"] = "tabpfn"
    young["context_seed"] = 11
    young["pd"] = young["pd"] * 0.5
    both = pd.concat([scores, young], ignore_index=True)
    both["context_seed"] = both["context_seed"].astype("Int64")

    shared, dropped = bi.shared_cohorts(both)
    assert shared == ["2015Q3", "2015Q4"]
    assert dropped == {"2015Q5": ["tabpfn/11"]}

    with pytest.raises(SystemExit, match="no scores for tabpfn/11"):
        bi.load_cohorts(both)
    cohorts, models = bi.load_cohorts(both, shared)
    assert sorted(cohorts) == shared
    assert models == {"scorecard": [None], "gbm-50k": [11, 12], "tabpfn": [11]}
    drawn = cohorts["2015Q3"].realise(0)
    assert np.allclose(drawn.scores["tabpfn"], 0.5 * drawn.scores["scorecard"])

    # Two draws beside one cannot be paired jointly: the pooling keeps the
    # draw both hold and says which it left out.
    with pytest.raises(mt.MetricError, match="different draw counts"):
        _ = cohorts["2015Q3"].draws
    pooled, dropped_seeds = bi.shared_seeds(both)
    assert dropped_seeds == {"gbm-50k": [12]}
    cohorts, models = bi.load_cohorts(pooled, shared)
    assert models == {"scorecard": [None], "gbm-50k": [11], "tabpfn": [11]}
    assert cohorts["2015Q3"].draws == 1
    assert bi.shared_seeds(scores)[1] == {}


def test_a_tagged_model_is_described_coloured_and_styled_by_its_base():
    assert bi.base_model("tabicl@t1") == "tabicl"
    assert bi.describe("tabicl") == "tabicl"
    assert bi.describe("tabicl@t1") == "tabicl, softmax temperature 1"
    assert bi.describe("tabpfn@t1+bal") == "tabpfn, softmax temperature 1, balanced"
    assert bi.describe("tabpfn@t0.95") == "tabpfn, softmax temperature 0.95"
    assert bi.model_colour("tabicl@t1") == bi.MODEL_COLOUR["tabicl"]
    assert bi.model_style("tabicl") == "-" and bi.model_style("tabicl@t1") == "--"


def test_drop_models_removes_a_model_from_scores_and_reference_and_refuses_an_absent_one():
    scores = score_file()
    reference = scores.rename(columns={"cohort": "drop"}).drop(columns="drop")
    kept, kept_ref = bi.drop_models(scores, reference, ["gbm-50k"])
    assert set(kept["model"]) == {"scorecard"} and set(kept_ref["model"]) == {"scorecard"}
    with pytest.raises(SystemExit, match="hold no rows"):
        bi.drop_models(scores, reference, ["tabicl"])


def test_the_figures_draw_unpooled_draws_and_disagreeing_pairs(tmp_path):
    scores = score_file()
    reference = pd.concat([
        pd.DataFrame({"build_id": "2015H1-E", "arm": "E", "model": "scorecard",
                      "context_seed": pd.array([None] * 300, dtype="Int64"),
                      "row": np.arange(300), "outcome": np.arange(300) % 10 == 0,
                      "pd": np.random.default_rng(1).uniform(0.01, 0.2, 300)}),
        *[pd.DataFrame({"build_id": "2015H1-E", "arm": "E", "model": "gbm-50k",
                        "context_seed": pd.array([s] * 300, dtype="Int64"),
                        "row": np.arange(300), "outcome": np.arange(300) % 10 == 0,
                        "pd": np.random.default_rng(s).uniform(0.01, 0.2, 300)}) for s in (11, 12)],
    ], ignore_index=True)
    reference["outcome"] = reference["outcome"].astype(int)
    edges = bi.reference_edges(reference)
    table = bi.cell_table(scores, reference, edges)
    bi.plot_cells(table, tmp_path / "cells.png", pooled_cells={"scorecard", "gbm-50k/11"})
    paired = pd.DataFrame({
        "build_id": "2015H1-E", "cohorts": "all", "draw": pd.array([None, None], dtype="Int64"),
        "metric": ["gini", "psi"], "pair": ["gbm-50k - scorecard"] * 2, "is_difference": True,
        "value": [0.01, -0.002], "ci_lo": [-0.01, -0.004], "ci_hi": [0.03, 0.0]})
    bi.plot_paired(paired, tmp_path / "paired.png", 2, 2, {"psi|gbm-50k - scorecard"})
    _, models = bi.load_cohorts(scores)
    bi.plot_reliability(scores, models, "2015Q3", "2015Q4", tmp_path / "reliability.png")
    for name in ("cells.png", "paired.png", "reliability.png"):
        assert (tmp_path / name).stat().st_size > 10_000


# --- a cell whose Cox fit does not finish ---------------------------------------------

POISONED = ("tabpfn", 11, "2016Q4")
SIX = ["2015Q3", "2015Q4", "2016Q1", "2016Q2", "2016Q3", "2016Q4"]


def poison_cox(monkeypatch) -> None:
    """The Cox fit returns its failure value on the poisoned cell's scores, and only there.

    The poisoned cell's scores all lie on a grid of 1/1024, which no other
    cell's do and which any resample of the cell keeps.
    """
    real = mt.cox

    def cox(outcome, score, **kw):
        if np.all(np.mod(np.asarray(score) * 1024.0, 1.0) == 0.0):
            nan = float("nan")
            return mt.Cox(nan, nan, nan, nan, False, mt.ALPHA, 100)
        return real(outcome, score, **kw)

    monkeypatch.setattr(mt, "cox", cox)


def six_cohort_dir(root: Path) -> Path:
    """One build, six cohorts, a fixed model and two seeded ones; one seeded cell is poisoned."""
    rng = np.random.default_rng(SEED)
    frames, references = [], []
    models = (("scorecard", [None]), ("gbm-50k", [11, 12]), ("tabpfn", [11, 12]))
    for age, cohort in enumerate(SIX, start=1):
        positions = rng.choice(100_000, size=400, replace=False)
        y = rng.binomial(1, 0.12, 400)
        for model, seeds in models:
            for s in seeds:
                score = np.clip(0.12 + 0.1 * (y - 0.12) + rng.normal(0, 0.05, 400), 0.01, 0.6)
                if (model, s, cohort) == POISONED:
                    # The same spread on a grid of 1/1024, so its PSI stays a number.
                    score = np.clip(np.round(score * 1024.0), 11.0, 614.0) / 1024.0
                frames.append(pd.DataFrame({
                    "build_id": "2015H1-E", "arm": "E", "model": model, "context_seed": s,
                    "cohort": cohort, "age_quarters": age, "row": positions, "outcome": y,
                    "pd": score}))
    for model, seeds in models:
        for s in seeds:
            # Drawn as the scores are, so that every reference decile holds scored rows.
            y_ref = rng.binomial(1, 0.12, 500)
            references.append(pd.DataFrame({
                "build_id": "2015H1-E", "arm": "E", "model": model, "context_seed": s,
                "row": np.arange(500), "outcome": y_ref,
                "pd": np.clip(0.12 + 0.1 * (y_ref - 0.12) + rng.normal(0, 0.05, 500), 0.01, 0.6)}))
    directory = root / "build"
    directory.mkdir()
    for name, parts in (("scores.parquet", frames), ("reference.parquet", references)):
        frame = pd.concat(parts, ignore_index=True)
        frame["context_seed"] = frame["context_seed"].astype("Int64")
        frame.to_parquet(directory / name, index=False)
    return directory


def test_a_cell_whose_cox_fit_did_not_finish_leaves_the_pairing_for_every_model(tmp_path,
                                                                                 monkeypatch):
    poison_cox(monkeypatch)
    directory = six_cohort_dir(tmp_path)
    scores = pd.read_parquet(directory / "scores.parquet")
    reference = pd.read_parquet(directory / "reference.parquet")
    cohorts, models = bi.load_cohorts(scores)
    edges = bi.reference_edges(reference)
    compute = bi.pooled_statistics(models, edges, bi.reference_shares(reference, edges), None)
    # Draw 0 is context seed 11, which holds the poisoned cell; draw 1 holds none.
    first = compute({k: c.realise(0) for k, c in cohorts.items()})
    second = compute({k: c.realise(1) for k, c in cohorts.items()})
    assert first["left_out|cox_slope_deviation"] == 1
    assert second["left_out|cox_slope_deviation"] == 0
    kept = [k for k in SIX if k != POISONED[2]]
    for model, pick in (("scorecard", lambda c: c.scores["scorecard"]),
                        ("gbm-50k", lambda c: c.realise(0).scores["gbm-50k"])):
        want = np.mean([bi.cox_slope_deviation(cohorts[k].outcome, pick(cohorts[k])) for k in kept])
        assert first[f"cox_slope_deviation|mean|{model}"] == want
    assert all(np.isfinite(v) for k, v in first.items() if k.startswith("cox"))


def test_one_cell_of_six_that_does_not_finish_leaves_every_cox_row_a_number(tmp_path, monkeypatch,
                                                                            capsys):
    poison_cox(monkeypatch)
    directory = six_cohort_dir(tmp_path)
    out = tmp_path / "out"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert bi.main([str(directory), "--out-dir", str(out), "--resamples", "40",
                        "--check-seeds", "5"]) == 0
    # Every statistic of the reading is a number: no warning of an invalid value.
    assert not [w for w in caught if issubclass(w.category, RuntimeWarning)]
    paired = pd.read_csv(out / "paired.csv")
    cox = paired[paired["metric"] == "cox_slope_deviation"]
    assert len(cox) > 0 and np.isfinite(cox[["value", "ci_lo", "ci_hi"]].to_numpy()).all()
    differences = cox[cox["is_difference"]]
    assert differences["excludes_zero"].isin([True, False]).all()
    assert set(differences["pair"]) >= {"tabpfn - scorecard", "tabpfn - gbm-50k"}
    summary = json.loads((out / "intervals.json").read_text(encoding="utf-8"))
    left = summary["bootstrap"]["cox_left_out"]
    assert left["all"]["cox_slope_deviation"] == {"point": 0.5, "largest_in_a_resample": 1.0}
    assert left["all, draw 11"]["cox_slope_deviation"]["point"] == 1.0
    assert left["all, draw 12"]["cox_slope_deviation"]["point"] == 0.0
    assert np.isfinite(summary["bootstrap"]["seed_check"]["largest_bound_movement"])
    assert summary["cox_not_estimable"]["cells"] == [
        {"model": "tabpfn", "context_seed": 11, "cohort": "2016Q4", "iterations": 100}]
    listed = pd.read_csv(out / "cox-not-estimable.csv")
    assert listed.to_dict("records") == [
        {"model": "tabpfn", "context_seed": 11, "cohort": "2016Q4", "iterations": 100}]
    metrics = pd.read_csv(out / "metrics.csv")
    poisoned = metrics[(metrics["model"] == "tabpfn") & (metrics["context_seed"] == 11)
                       & (metrics["cohort"] == "2016Q4") & (metrics["metric"] == "cox_slope")]
    assert poisoned["value"].isna().all()
    printed = capsys.readouterr().out
    assert "cohorts not estimable left out of the point estimate" in printed
    assert "Cox not estimable     : 1 cells" in printed


# --- statistics read from derived rows -------------------------------------------------


def derived_dir(root: Path, source: Path, model: str, derive: dict) -> Path:
    """A derived directory: the source's rows of the base model under the derived name."""
    directory = root / f"derived-{model.replace('@', '-')}"
    directory.mkdir()
    base = bi.base_model(model)
    for name in ("scores.parquet", "reference.parquet"):
        frame = pd.read_parquet(source / name)
        frame = frame[frame["model"] == base].assign(model=model)
        frame.to_parquet(directory / name, index=False)
    (directory / "derive.json").write_text(json.dumps({"derived_as": model, **derive}),
                                           encoding="utf-8")
    return directory


# A row of the printed table of paired differences: metric, pair, value, interval.
TABLE_ROW = re.compile(r"^  \w+ +\S+ - \S+ +[+-]\d+\.\d+ \[")

APPROXIMATE = {"approximate": True, "checked_build": ["2015H1-E"], "check": {"cells": [
    {"build_id": "2015H1-E", "context_seed": 11, "cell": "2016Q3", "logit_slope_gap": 5e-4,
     "cox_slope_gap": 0.01, "oe_gap": 0.002},
    {"build_id": "2015H1-E", "context_seed": 11, "cell": "reference", "logit_slope_gap": 1e-3,
     "cox_slope_gap": -0.02, "oe_gap": -0.004}]}}
EXACT = {"check": {"cells": [{"context_seed": 11, "cell": "2016Q3"}], "rows_checked": 400,
                   "max_abs_pd_gap": 1.2e-7, "unchecked_cells": [{"context_seed": 12, "cell": "x"}]}}


def test_a_derivation_record_is_read_from_either_kind_of_derive_json(tmp_path):
    source = six_cohort_dir(tmp_path)
    assert bi.derivation_of(source) is None
    approximate = bi.derivation_of(derived_dir(tmp_path, source, "tabpfn@t1", APPROXIMATE))
    assert approximate["kind"] == "approximate" and approximate["model"] == "tabpfn@t1"
    assert approximate["worst_cell_error"] == 1e-3
    assert approximate["mean_cell_error"] == pytest.approx(7.5e-4)
    assert approximate["cells_above_figure"] == 1 and approximate["cells_checked"] == 2
    assert approximate["cox_slope_gap"] == {"worst": -0.02, "mean": pytest.approx(-0.005)}
    assert approximate["oe_gap"] == {"worst": -0.004, "mean": pytest.approx(-0.001)}
    exact = bi.derivation_of(derived_dir(tmp_path, source, "tabicl@t1", EXACT))
    assert exact["kind"] == "exact" and exact["max_abs_pd_gap"] == 1.2e-7
    assert exact["rows_checked"] == 400 and exact["unchecked_cells"] == 1
    # A record that names no checked build was checked on the build's own cells.
    assert exact["checked_build"] is None
    assert "checked on the build's own cells" in bi.derivation_text(exact)
    # A carried check names its build inside the check, where check_through writes it.
    nested = bi.derivation_of(derived_dir(tmp_path, source, "tabicl@t2", {
        "check": {**EXACT["check"], "checked_build": ["2014H2-E"]}}))
    assert nested["checked_build"] == ["2014H2-E"]
    assert "checked on build 2014H2-E" in bi.derivation_text(nested)


def test_every_statistic_read_from_derived_rows_is_printed_with_the_derivation_error(tmp_path,
                                                                                    capsys):
    source = six_cohort_dir(tmp_path)
    derived = derived_dir(tmp_path, source, "tabpfn@t1", APPROXIMATE)
    out = tmp_path / "out"
    assert bi.main([str(source), str(derived), "--out-dir", str(out), "--resamples", "20"]) == 0
    printed = capsys.readouterr().out
    rows = [line for line in printed.splitlines() if TABLE_ROW.match(line) and "tabpfn@t1" in line]
    assert rows and all(line.rstrip().endswith("~") for line in rows)
    others = [line for line in printed.splitlines()
              if TABLE_ROW.match(line) and "tabpfn@t1" not in line]
    assert others and not any(line.rstrip().endswith("~") for line in others)
    assert "~ tabpfn@t1: derived approximately" in printed
    assert "|b - 1| worst 1.00e-03, mean 7.50e-04, 1 of 2 cells above 0.00084" in printed
    assert "Cox slope derived - scored worst -2.00e-02, mean -5.00e-03" in printed
    paired = pd.read_csv(out / "paired.csv")
    marked = paired[paired["reads_derived"]]
    assert len(marked) and marked["pair"].str.contains("tabpfn@t1").all()
    assert not paired[~paired["reads_derived"]]["pair"].str.contains("tabpfn@t1").any()
    summary = json.loads((out / "intervals.json").read_text(encoding="utf-8"))
    recorded = summary["derived_rows"]["tabpfn@t1"]
    assert recorded["worst_cell_error"] == 1e-3 and recorded["cells_above_figure"] == 1
    assert recorded["cox_slope_gap"]["worst"] == -0.02 and recorded["oe_gap"]["worst"] == -0.004


def test_seed_check_names_the_stars_that_change_with_the_seed():
    def rows(seed, lo_gini, lo_psi):
        base = {"build_id": "2015H1-E", "cohorts": "all", "is_difference": True, "draw": None,
                "value": 0.01, "n_resamples": 200}
        out = pd.DataFrame([
            {**base, "metric": "gini", "pair": "tabpfn - gbm", "ci_lo": lo_gini, "ci_hi": 0.02},
            {**base, "metric": "psi", "pair": "tabpfn - gbm", "ci_lo": lo_psi, "ci_hi": 0.02},
        ])
        out["excludes_zero"] = (out["ci_lo"] > 0) | (out["ci_hi"] < 0)
        if seed is not None:
            out.insert(1, "bootstrap_seed", seed)
        return out

    primary = rows(None, 0.001, -0.004)
    repeats = pd.concat([rows(1, 0.002, -0.001), rows(2, -0.001, -0.003)], ignore_index=True)
    checked = bi.seed_check(primary, repeats)
    assert checked["seeds"] == [1, 2]
    assert checked["differences"] == 2 and checked["starred"] == 1
    assert [c["pair"] for c in checked["star_changed"]] == ["tabpfn - gbm"]
    change = checked["star_changed"][0]
    assert change["metric"] == "gini" and change["primary"]["excludes_zero"] is True
    assert change["under"][1]["excludes_zero"] is True
    assert change["under"][2]["excludes_zero"] is False
    assert change["bound_movement"] == pytest.approx(0.002)
    assert checked["largest_bound_movement"] == pytest.approx(0.003)
    with pytest.raises(SystemExit, match="not repeated"):
        bi.seed_check(primary, repeats.iloc[:3])


def logit_scaled_cohorts(scale: float, shift: float = 0.0, cohorts: int = 6, rows: int = 4_000):
    """Cohorts whose outcomes follow the scorecard's probability, and a second model on the same
    rows whose logit is the scorecard's times ``scale`` plus ``shift``."""
    rng = np.random.default_rng(SEED)
    found = {}
    for k in range(cohorts):
        z = np.log(0.1 / 0.9) + rng.normal(0.0, 1.0, rows)
        truth = 1.0 / (1.0 + np.exp(-z))
        y = rng.binomial(1, truth)
        other = 1.0 / (1.0 + np.exp(-(scale * z + shift)))
        found[f"2015Q{k % 4 + 1}-{k}"] = mt.ScoredCohort(y, {"scorecard": truth, "tabpfn": other})
    models = {"scorecard": [None], "tabpfn": [None]}
    reference = pd.DataFrame({"model": ["scorecard"] * 500 + ["tabpfn"] * 500,
                              "context_seed": pd.array([None] * 1000, dtype="Int64"),
                              "pd": np.tile(np.linspace(0.01, 0.5, 500), 2)})
    edges = bi.reference_edges(reference)
    return found, bi.pooled_statistics(models, edges, bi.reference_shares(reference, edges), None)


def test_the_signed_slope_reads_the_direction_the_deviation_folds_away():
    # A logit shrunk by 0.85 reads a slope near 1/0.85, one stretched by 1.2 near 1/1.2; both
    # sit about as far from one, and only the signed slope tells them apart.
    shrunk, compute = logit_scaled_cohorts(0.85)
    first = compute({k: c.realise(0) for k, c in shrunk.items()})
    stretched, compute_s = logit_scaled_cohorts(1.2)
    second = compute_s({k: c.realise(0) for k, c in stretched.items()})
    assert first["cox_slope|mean|scorecard"] == pytest.approx(1.0, abs=0.05)
    assert first["cox_slope|mean|tabpfn"] == pytest.approx(1 / 0.85, abs=0.05)
    assert second["cox_slope|mean|tabpfn"] == pytest.approx(1 / 1.2, abs=0.05)
    assert first["cox_slope|diff|tabpfn|scorecard"] > 0.1
    assert second["cox_slope|diff|tabpfn|scorecard"] < -0.1
    assert first["left_out|cox_slope"] == 0.0
    # The deviation is the absolute value of the same fit's slope less one, cell by cell.
    for cohort in shrunk.values():
        deviation, signed = bi.cox_slope_pair(cohort.outcome, cohort.scores["tabpfn"])
        assert deviation == abs(signed - 1.0)
        assert deviation == bi.cox_slope_deviation(cohort.outcome, cohort.scores["tabpfn"])


def test_the_signed_slope_does_not_see_a_shift_of_the_logit():
    shifted, compute = logit_scaled_cohorts(1.0, shift=0.7)
    out = compute({k: c.realise(0) for k, c in shifted.items()})
    assert abs(out["cox_slope|diff|tabpfn|scorecard"]) < 1e-6
    assert abs(out["abs_log_oe|diff|tabpfn|scorecard"]) > 0.3


def test_adding_the_signed_slope_moves_no_other_pooled_value():
    cohorts, compute = logit_scaled_cohorts(0.9, cohorts=4, rows=1_500)

    def without(sample):
        return {k: v for k, v in compute(sample).items() if not k.endswith("|cox_slope")
                and not k.startswith("cox_slope|")}

    full = mt.cohort_blocked_bootstrap_many(cohorts, compute, resamples=40, seed=SEED)
    plain = mt.cohort_blocked_bootstrap_many(cohorts, without, resamples=40, seed=SEED)
    assert set(full) - set(plain) == {"cox_slope|mean|scorecard", "cox_slope|mean|tabpfn",
                                      "cox_slope|diff|tabpfn|scorecard", "left_out|cox_slope"}
    for name, boot in plain.items():
        assert full[name].draws == boot.draws
        assert (full[name].value, full[name].lo, full[name].hi) == (boot.value, boot.lo, boot.hi)
