"""The temperature derivation, on what would make a derived row wrong.

A derived row is a claim that the installed library applies its temperature
as a scale on the logit. The script is only trusted because it refuses to
write when that claim is not checked against rows the library scored: a
different version, a different checkpoint, a model that averages after the
softmax, a check at the wrong temperature, a cell that is not shared, or a
row that disagrees. Each refusal is exercised; so is the identity itself.
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

import derive_temperature as dt

SEED = 20260906
ROWS = 40


def probabilities(seed: int, n: int) -> np.ndarray:
    return np.random.default_rng(seed).uniform(0.002, 0.3, n)


def scored_dir(root: Path, name: str, *, model: str, seeds: list[int], temperature: float,
               version: str = "2.1.1", checkpoint: str = "ckpt-a", average_logits: bool = True,
               pd_of=None, cohorts=("2015Q3", "2015Q4"), build: str = "2015H1-E",
               device: str = "NVIDIA GeForce RTX 4090", extra_parameters: dict | None = None
               ) -> Path:
    """A directory in the shape score_context.py writes, with rows keyed by seed and cell."""
    directory = root / name
    directory.mkdir()
    pd_of = pd_of or (lambda seed, cell, n: probabilities(seed * 7 + sum(map(ord, cell)) % 1000, n))
    scores, reference = [], []
    for seed in seeds:
        for k, cohort in enumerate(cohorts):
            scores.append(pd.DataFrame({
                "build_id": build, "arm": "E", "as_of": "2015-06-30", "model": model,
                "context_seed": seed, "cohort": cohort, "age_quarters": k + 1,
                "row": np.arange(ROWS) + 1000 * k, "outcome": (np.arange(ROWS) % 7 == 0).astype(int),
                "pd": pd_of(seed, cohort, ROWS),
            }))
        reference.append(pd.DataFrame({
            "build_id": build, "arm": "E", "as_of": "2015-06-30", "model": model,
            "context_seed": seed, "row": np.arange(ROWS) + 5000,
            "outcome": (np.arange(ROWS) % 5 == 0).astype(int), "pd": pd_of(seed, "reference", ROWS),
        }))
    scores_df = pd.concat(scores, ignore_index=True)
    reference_df = pd.concat(reference, ignore_index=True)
    for frame in (scores_df, reference_df):
        frame["context_seed"] = frame["context_seed"].astype("Int64")
    scores_df.to_parquet(directory / dt.SCORES_FILE, index=False)
    reference_df.to_parquet(directory / dt.REFERENCE_FILE, index=False)
    parameters = {"softmax_temperature": temperature, "checkpoint_version": checkpoint,
                  "n_estimators": 8}
    if average_logits is not None:
        parameters["average_logits"] = average_logits
    parameters.update(extra_parameters or {})
    node = {
        "environment": {"packages": {"tabicl": version, "tabpfn": "8.5.0"}, "device_name": device},
        "models": {f"{model}/{seed}": {"parameters": dict(parameters)} for seed in seeds},
        "checkpoints": {checkpoint: f"hash-of-{checkpoint}"},
    }
    (directory / dt.NODE_FILE).write_text(json.dumps(node), encoding="utf-8")
    return directory


def rescaled(seed_pd, from_t: float, to_t: float):
    """What the library would score at ``to_t`` if the temperature is a scale on the logit."""
    def scored(seed, cell, n):
        p = seed_pd(seed, cell, n)
        return 1.0 / (1.0 + np.exp(-np.log(p / (1 - p)) * from_t / to_t))
    return scored


def default_pd(seed, cell, n):
    return probabilities(seed * 7 + sum(map(ord, cell)) % 1000, n)


@pytest.fixture
def tree(tmp_path):
    """Sources at 0.9 on three draws; a check the library scored at 1.0 on the first."""
    source_a = scored_dir(tmp_path, "src-a", model="tabicl", seeds=[11], temperature=0.9)
    source_b = scored_dir(tmp_path, "src-b", model="tabicl", seeds=[12, 13], temperature=0.9)
    check = scored_dir(tmp_path, "probe", model="tabicl@t1", seeds=[11], temperature=1.0,
                       pd_of=rescaled(default_pd, 0.9, 1.0))
    return source_a, source_b, check, tmp_path / "out"


def run(sources, check, out, **extra) -> int:
    argv = [str(s) for s in sources] + ["--check", str(check), "--out-dir", str(out)]
    for key, value in extra.items():
        argv += [f"--{key}"] if value is True else [f"--{key}", str(value)]
    return dt.main(argv)


def test_the_identity_is_written_with_its_check(tree, capsys):
    source_a, source_b, check, out = tree
    assert run([source_a, source_b], check, out) == 0
    scores = pd.read_parquet(out / dt.SCORES_FILE)
    reference = pd.read_parquet(out / dt.REFERENCE_FILE)
    assert set(scores["model"]) == {"tabicl@t1"} and set(reference["model"]) == {"tabicl@t1"}
    assert sorted(scores["context_seed"].unique()) == [11, 12, 13]
    assert len(scores) == 3 * 2 * ROWS and len(reference) == 3 * ROWS
    # The unchecked draws carry the same identity as the checked one.
    got = scores[(scores["context_seed"] == 13) & (scores["cohort"] == "2015Q4")].sort_values("row")
    want = rescaled(default_pd, 0.9, 1.0)(13, "2015Q4", ROWS)
    assert np.allclose(got["pd"].to_numpy(), want, atol=1e-12)
    account = json.loads((out / dt.DERIVE_FILE).read_text(encoding="utf-8"))
    assert account["derived_as"] == "tabicl@t1"
    assert account["library"] == {"tabicl": "2.1.1"}
    assert account["checkpoints"] == {"ckpt-a": "hash-of-ckpt-a"}
    assert account["check"]["rows_checked"] == 3 * ROWS
    assert account["check"]["max_abs_pd_gap"] < 1e-12
    assert len(account["check"]["unchecked_cells"]) == 6
    assert "rows checked" in capsys.readouterr().out


def test_the_source_temperature_is_read_from_the_node_not_assumed(tmp_path):
    source = scored_dir(tmp_path, "src", model="tabicl", seeds=[11], temperature=0.8)
    check = scored_dir(tmp_path, "probe", model="tabicl@t1", seeds=[11], temperature=1.0,
                       pd_of=rescaled(default_pd, 0.8, 1.0))
    assert run([source], check, tmp_path / "out") == 0
    account = json.loads((tmp_path / "out" / dt.DERIVE_FILE).read_text(encoding="utf-8"))
    assert account["sources"][0]["from_temperature"] == {"11": 0.8}


def test_a_row_that_disagrees_refuses_and_writes_nothing(tmp_path):
    source = scored_dir(tmp_path, "src", model="tabicl", seeds=[11], temperature=0.9)

    def nearly(seed, cell, n):
        p = rescaled(default_pd, 0.9, 1.0)(seed, cell, n)
        if cell == "2015Q4":
            p[3] += 5e-6
        return p

    check = scored_dir(tmp_path, "probe", model="tabicl@t1", seeds=[11], temperature=1.0,
                       pd_of=nearly)
    with pytest.raises(SystemExit, match="exceed the tolerance"):
        run([source], check, tmp_path / "out")
    assert not (tmp_path / "out").exists()
    # The same rows pass a tolerance that admits the gap: the check is the tolerance.
    assert run([source], check, tmp_path / "out", tolerance=1e-5) == 0


def test_a_model_that_averages_after_the_softmax_is_refused(tmp_path):
    source = scored_dir(tmp_path, "src", model="tabpfn", seeds=[11], temperature=0.9,
                        average_logits=None)
    check = scored_dir(tmp_path, "probe", model="tabpfn@t1", seeds=[11], temperature=1.0,
                       average_logits=None, pd_of=rescaled(default_pd, 0.9, 1.0))
    with pytest.raises(SystemExit, match="average_logits"):
        run([source], check, tmp_path / "out", model="tabpfn", package="tabpfn")


def test_a_different_library_version_in_the_check_is_refused(tmp_path):
    source = scored_dir(tmp_path, "src", model="tabicl", seeds=[11], temperature=0.9)
    check = scored_dir(tmp_path, "probe", model="tabicl@t1", seeds=[11], temperature=1.0,
                       version="2.2.0", pd_of=rescaled(default_pd, 0.9, 1.0))
    with pytest.raises(SystemExit, match="2.2.0"):
        run([source], check, tmp_path / "out")


def test_a_different_checkpoint_is_refused(tmp_path):
    source = scored_dir(tmp_path, "src", model="tabicl", seeds=[11], temperature=0.9)
    check = scored_dir(tmp_path, "probe", model="tabicl@t1", seeds=[11], temperature=1.0,
                       checkpoint="ckpt-b", pd_of=rescaled(default_pd, 0.9, 1.0))
    with pytest.raises(SystemExit, match="checkpoint"):
        run([source], check, tmp_path / "out")


def test_a_check_at_the_wrong_temperature_is_refused(tmp_path):
    source = scored_dir(tmp_path, "src", model="tabicl", seeds=[11], temperature=0.9)
    check = scored_dir(tmp_path, "probe", model="tabicl@t1", seeds=[11], temperature=0.95,
                       pd_of=rescaled(default_pd, 0.9, 1.0))
    with pytest.raises(SystemExit, match="scored at 0.95"):
        run([source], check, tmp_path / "out")


def test_a_check_that_shares_no_cell_checks_nothing(tmp_path):
    source = scored_dir(tmp_path, "src", model="tabicl", seeds=[12], temperature=0.9)
    check = scored_dir(tmp_path, "probe", model="tabicl@t1", seeds=[11], temperature=1.0,
                       pd_of=rescaled(default_pd, 0.9, 1.0))
    with pytest.raises(SystemExit, match="shares no cell"):
        run([source], check, tmp_path / "out")


def test_a_shared_cell_with_other_rows_is_refused(tmp_path):
    source = scored_dir(tmp_path, "src", model="tabicl", seeds=[11], temperature=0.9)
    check = scored_dir(tmp_path, "probe", model="tabicl@t1", seeds=[11], temperature=1.0,
                       pd_of=rescaled(default_pd, 0.9, 1.0))
    scores = pd.read_parquet(check / dt.SCORES_FILE)
    scores = scores[~((scores["cohort"] == "2015Q3") & (scores["row"] == 5))]
    scores.to_parquet(check / dt.SCORES_FILE, index=False)
    with pytest.raises(SystemExit, match="not the same ones"):
        run([source], check, tmp_path / "out")


def test_two_sources_holding_the_same_cell_are_refused(tmp_path):
    source_a = scored_dir(tmp_path, "src-a", model="tabicl", seeds=[11], temperature=0.9)
    source_b = scored_dir(tmp_path, "src-b", model="tabicl", seeds=[11], temperature=0.9)
    check = scored_dir(tmp_path, "probe", model="tabicl@t1", seeds=[11], temperature=1.0,
                       pd_of=rescaled(default_pd, 0.9, 1.0))
    with pytest.raises(SystemExit, match="same cell"):
        run([source_a, source_b], check, tmp_path / "out")


def test_a_written_derivation_is_never_overwritten(tree):
    source_a, _, check, out = tree
    assert run([source_a], check, out) == 0
    with pytest.raises(SystemExit, match="not overwritten"):
        run([source_a], check, out)


# --- the check made on another build's cells ---------------------------------------


def through(tmp_path, *, source_kw=None, check_source_kw=None, check_kw=None):
    """Sources on one build, a check source and a check scored on another build's cells."""
    source = scored_dir(tmp_path, "src", **{
        "model": "tabicl", "seeds": [11, 12], "temperature": 0.9, "build": "2016H1-E",
        "cohorts": ("2016Q3", "2016Q4", "2017Q1"), **(source_kw or {})})
    check_source = scored_dir(tmp_path, "proxy", **{
        "model": "tabicl", "seeds": [11], "temperature": 0.9, **(check_source_kw or {})})
    check = scored_dir(tmp_path, "probe", **{
        "model": "tabicl@t1", "seeds": [11], "temperature": 1.0,
        "pd_of": rescaled(default_pd, 0.9, 1.0), **(check_kw or {})})
    return source, check_source, check, tmp_path / "out"


def run_through(source, check_source, check, out, **extra) -> int:
    return run([source], check, out, **{"check-source": check_source, **extra})


def test_a_check_on_another_build_is_carried_by_identity_and_says_so(tmp_path, capsys):
    source, check_source, check, out = through(tmp_path)
    # Without the check source the two builds share no cell and nothing is checked.
    with pytest.raises(SystemExit, match="shares no cell"):
        run([source], check, out)
    assert run_through(source, check_source, check, out) == 0
    scores = pd.read_parquet(out / dt.SCORES_FILE)
    reference = pd.read_parquet(out / dt.REFERENCE_FILE)
    # Only the sources' rows are written, and they are the identity on every draw.
    assert set(scores["build_id"]) == {"2016H1-E"} and set(reference["build_id"]) == {"2016H1-E"}
    assert len(scores) == 2 * 3 * ROWS and len(reference) == 2 * ROWS
    got = scores[(scores["context_seed"] == 12) & (scores["cohort"] == "2017Q1")].sort_values("row")
    assert np.allclose(got["pd"].to_numpy(), rescaled(default_pd, 0.9, 1.0)(12, "2017Q1", ROWS),
                       atol=1e-12)
    account = json.loads((out / dt.DERIVE_FILE).read_text(encoding="utf-8"))
    assert account["derived_build"] == ["2016H1-E"]
    assert account["checked_build"] == ["2015H1-E"]
    assert account["check"]["checked_build"] == ["2015H1-E"]
    assert account["check"]["rows_checked"] == 3 * ROWS
    assert account["check"]["max_abs_pd_gap"] < 1e-12
    # Every derived cell is unchecked by row: two draws, three cohorts and the reference.
    assert len(account["check"]["unchecked_cells"]) == 2 * 4
    assert account["check"]["check_source_unchecked_cells"] == []
    assert "no derived row of build 2016H1-E" in account["check"]["scope"]
    assert set(account["check_source"]["sha256"]) == {dt.SCORES_FILE, dt.REFERENCE_FILE,
                                                      dt.NODE_FILE}
    assert account["check_source"]["build_id"] == ["2015H1-E"]
    assert account["devices"]["check"] == account["devices"]["check_source"]
    assert "derived rows checked  : none by row" in capsys.readouterr().out


def test_without_a_check_source_the_record_is_the_one_it_was(tree):
    source_a, source_b, check, out = tree
    assert run([source_a, source_b], check, out) == 0
    account = json.loads((out / dt.DERIVE_FILE).read_text(encoding="utf-8"))
    assert list(account) == ["model", "derived_as", "to_temperature", "formula", "library",
                             "checkpoints", "sources", "check", "scored_rows", "reference_rows"]
    assert "scope" not in account["check"]


def test_a_check_source_row_beyond_the_tolerance_refuses_and_writes_nothing(tmp_path):
    def nearly(seed, cell, n):
        p = rescaled(default_pd, 0.9, 1.0)(seed, cell, n)
        if cell == "reference":
            p[7] += 5e-6
        return p

    source, check_source, check, out = through(tmp_path, check_kw={"pd_of": nearly})
    with pytest.raises(SystemExit, match="exceed the tolerance"):
        run_through(source, check_source, check, out)
    assert not out.exists()


@pytest.mark.parametrize("where", ["source_kw", "check_source_kw", "check_kw"])
def test_a_library_version_that_differs_anywhere_is_refused(tmp_path, where):
    source, check_source, check, out = through(tmp_path, **{where: {"version": "2.2.0"}})
    with pytest.raises(SystemExit, match="2.2.0"):
        run_through(source, check_source, check, out)
    assert not out.exists()


@pytest.mark.parametrize("where", ["source_kw", "check_source_kw", "check_kw"])
def test_a_checkpoint_that_differs_anywhere_is_refused(tmp_path, where):
    source, check_source, check, out = through(tmp_path, **{where: {"checkpoint": "ckpt-b"}})
    with pytest.raises(SystemExit, match="checkpoint|loaded"):
        run_through(source, check_source, check, out)
    assert not out.exists()


def test_a_check_source_at_another_temperature_than_the_sources_is_refused(tmp_path):
    source, check_source, check, out = through(
        tmp_path, check_source_kw={"temperature": 0.8},
        check_kw={"pd_of": rescaled(default_pd, 0.8, 1.0)})
    # The check source's own identity holds at 0.8; it is not the sources' setting.
    with pytest.raises(SystemExit, match="the sources' temperature"):
        run_through(source, check_source, check, out)
    assert not out.exists()


def test_a_check_on_another_device_than_the_check_source_is_refused(tmp_path):
    source, check_source, check, out = through(tmp_path,
                                               check_kw={"device": "NVIDIA Tesla T4"})
    with pytest.raises(SystemExit, match="one device"):
        run_through(source, check_source, check, out)
    assert not out.exists()


# --- the approximate derivation ------------------------------------------------------


def stretched(factor: float):
    """Rows at 1.0 whose logit is the derivation's times ``factor``: a known scale error."""
    exact = rescaled(default_pd, 0.9, 1.0)

    def scored(seed, cell, n):
        p = exact(seed, cell, n)
        return 1.0 / (1.0 + np.exp(-np.log(p / (1 - p)) * factor))
    return scored


def tabpfn_dir(root, name, **kw) -> Path:
    """A model that averages after the softmax, as TabPFN records itself."""
    return scored_dir(root, name, **{"average_logits": None,
                                     "extra_parameters": {"average_before_softmax": False}, **kw})


APPROX = {"model": "tabpfn", "package": "tabpfn", "approximate": True}


def test_an_approximate_derivation_is_measured_and_marked(tmp_path, capsys):
    source = tabpfn_dir(tmp_path, "src", model="tabpfn", seeds=[11, 12], temperature=0.9)
    check = tabpfn_dir(tmp_path, "probe", model="tabpfn@t1", seeds=[11], temperature=1.0,
                       pd_of=stretched(1.0005))
    out = tmp_path / "out"
    assert run([source], check, out, **APPROX, **{"max-cell-error": 1e-3}) == 0
    scores = pd.read_parquet(out / dt.SCORES_FILE)
    assert set(scores["model"]) == {"tabpfn@t1"}
    account = json.loads((out / dt.DERIVE_FILE).read_text(encoding="utf-8"))
    assert account["approximate"] is True
    verified = account["check"]
    assert verified["approximate"] is True and verified["max_cell_error"] == 1e-3
    assert verified["cell_error"] == dt.CELL_ERROR
    assert len(verified["cells"]) == 3 and verified["rows_checked"] == 3 * ROWS
    for cell in verified["cells"]:
        # The planted scale is read back as the slope of the scored logit on the derived one.
        assert cell["logit_slope"] == pytest.approx(1.0005, abs=1e-9)
        assert cell["logit_slope_gap"] == pytest.approx(5e-4, abs=1e-9)
        assert cell["mean_pd_gap"] == pytest.approx(cell["mean_pd_derived"] - cell["mean_pd_scored"])
        assert cell["oe_gap"] == pytest.approx(cell["oe_derived"] - cell["oe_scored"])
        assert np.isfinite(cell["cox_slope_gap"]) and cell["mean_abs_pd_gap"] > 0
    assert verified["worst_cell_error"] == pytest.approx(5e-4, abs=1e-9)
    assert len(verified["unchecked_cells"]) == 3
    assert account["devices"]["check"] == "NVIDIA GeForce RTX 4090"
    assert "approximate" in capsys.readouterr().out


def test_an_approximate_cell_beyond_the_bound_refuses_and_writes_nothing(tmp_path):
    source = tabpfn_dir(tmp_path, "src", model="tabpfn", seeds=[11], temperature=0.9)
    check = tabpfn_dir(tmp_path, "probe", model="tabpfn@t1", seeds=[11], temperature=1.0,
                       pd_of=stretched(1.01))
    with pytest.raises(SystemExit, match="exceed the bound"):
        run([source], check, tmp_path / "out", **APPROX, **{"max-cell-error": 1e-3})
    assert not (tmp_path / "out").exists()
    # The same rows pass a bound that admits the planted scale: the bound is the check.
    assert run([source], check, tmp_path / "out", **APPROX, **{"max-cell-error": 2e-2}) == 0


def test_an_exact_model_never_takes_the_approximate_path(tmp_path):
    source = scored_dir(tmp_path, "src", model="tabicl", seeds=[11], temperature=0.9)
    check = scored_dir(tmp_path, "probe", model="tabicl@t1", seeds=[11], temperature=1.0,
                       pd_of=rescaled(default_pd, 0.9, 1.0))
    with pytest.raises(SystemExit, match="derived exactly, not approximately"):
        run([source], check, tmp_path / "out", approximate=True, **{"max-cell-error": 1e-3})
    before = tabpfn_dir(tmp_path, "src-b", model="tabpfn", seeds=[11], temperature=0.9,
                        extra_parameters={"average_before_softmax": True})
    probe = tabpfn_dir(tmp_path, "probe-b", model="tabpfn@t1", seeds=[11], temperature=1.0,
                       pd_of=rescaled(default_pd, 0.9, 1.0))
    with pytest.raises(SystemExit, match="derived exactly, not approximately"):
        run([before], probe, tmp_path / "out", **APPROX, **{"max-cell-error": 1e-3})


def test_the_bound_and_the_approximation_are_asked_for_together(tmp_path):
    source = tabpfn_dir(tmp_path, "src", model="tabpfn", seeds=[11], temperature=0.9)
    check = tabpfn_dir(tmp_path, "probe", model="tabpfn@t1", seeds=[11], temperature=1.0,
                       pd_of=stretched(1.0005))
    with pytest.raises(SystemExit, match="needs --max-cell-error"):
        run([source], check, tmp_path / "out", **APPROX)
    with pytest.raises(SystemExit, match="--approximate is not given"):
        run([source], check, tmp_path / "out", model="tabpfn", package="tabpfn",
            **{"max-cell-error": 1e-3})


def test_an_approximate_source_on_another_device_than_the_check_is_refused(tmp_path):
    source = tabpfn_dir(tmp_path, "src", model="tabpfn", seeds=[11], temperature=0.9,
                        device="NVIDIA Tesla T4")
    check = tabpfn_dir(tmp_path, "probe", model="tabpfn@t1", seeds=[11], temperature=1.0,
                       pd_of=stretched(1.0005))
    with pytest.raises(SystemExit, match="checked on one device"):
        run([source], check, tmp_path / "out", **APPROX, **{"max-cell-error": 1e-3})


def test_an_approximate_derivation_through_another_build_carries_the_measured_error(tmp_path):
    source = tabpfn_dir(tmp_path, "src", model="tabpfn", seeds=[11, 12], temperature=0.9,
                        build="2016H1-R", cohorts=("2016Q3", "2016Q4"))
    check_source = tabpfn_dir(tmp_path, "proxy", model="tabpfn", seeds=[11], temperature=0.9)
    check = tabpfn_dir(tmp_path, "probe", model="tabpfn@t1", seeds=[11], temperature=1.0,
                       pd_of=stretched(1.0005))
    out = tmp_path / "out"
    assert run([source], check, out, **APPROX, **{"max-cell-error": 1e-3,
                                                  "check-source": check_source}) == 0
    account = json.loads((out / dt.DERIVE_FILE).read_text(encoding="utf-8"))
    assert account["approximate"] is True
    assert account["derived_build"] == ["2016H1-R"] and account["checked_build"] == ["2015H1-E"]
    assert "not a verification of the derived rows" in account["check"]["scope"]
    assert len(account["check"]["unchecked_cells"]) == 2 * 3
    assert account["check"]["worst_cell_error"] == pytest.approx(5e-4, abs=1e-9)


def test_a_cox_fit_that_fails_is_recorded_and_the_cell_still_measured(tmp_path, monkeypatch):
    source = tabpfn_dir(tmp_path, "src", model="tabpfn", seeds=[11], temperature=0.9)
    check = tabpfn_dir(tmp_path, "probe", model="tabpfn@t1", seeds=[11], temperature=1.0,
                       pd_of=stretched(1.0005))

    calls = {"n": 0}

    def unfinished(outcome, score, **kw):
        # The derived rows' fit returns the failure value; the scored rows' fit is refused.
        calls["n"] += 1
        if calls["n"] % 2:
            nan = float("nan")
            return dt.mt.Cox(nan, nan, nan, nan, False, dt.mt.ALPHA, 100)
        raise dt.mt.MetricError("the Cox fit needs both outcomes present")

    monkeypatch.setattr(dt.mt, "cox", unfinished)
    out = tmp_path / "out"
    assert run([source], check, out, **APPROX, **{"max-cell-error": 1e-3}) == 0
    account = json.loads((out / dt.DERIVE_FILE).read_text(encoding="utf-8"))
    for cell in account["check"]["cells"]:
        assert cell["cox_fit_failed"] == ["derived", "scored"]
        assert cell["cox_slope_gap"] is None or not np.isfinite(cell["cox_slope_gap"])
        assert cell["logit_slope_gap"] == pytest.approx(5e-4, abs=1e-9)


def test_default_weights_are_the_one_checkpoint_hashed_for_the_library(tmp_path):
    """TabPFN names no checkpoint and loads the library's default; the node hashed its cache."""
    auto = {"average_before_softmax": False, "checkpoint_version": None, "model_path": "auto"}
    source = tabpfn_dir(tmp_path, "src", model="tabpfn", seeds=[11], temperature=0.9,
                        checkpoint="tabpfn-v3-default.ckpt", extra_parameters=auto)
    check = tabpfn_dir(tmp_path, "probe", model="tabpfn@t1", seeds=[11], temperature=1.0,
                       checkpoint="tabpfn-v3-default.ckpt", extra_parameters=auto,
                       pd_of=stretched(1.0005))
    out = tmp_path / "out"
    assert run([source], check, out, **APPROX, **{"max-cell-error": 1e-3}) == 0
    account = json.loads((out / dt.DERIVE_FILE).read_text(encoding="utf-8"))
    assert account["checkpoints"] == {"tabpfn-v3-default.ckpt": "hash-of-tabpfn-v3-default.ckpt"}
    # Two checkpoints of the library in the cache, and the one it read is not on record.
    node = json.loads((source / dt.NODE_FILE).read_text(encoding="utf-8"))
    node["checkpoints"]["tabpfn-v2-default.ckpt"] = "hash-of-v2"
    (source / dt.NODE_FILE).write_text(json.dumps(node), encoding="utf-8")
    with pytest.raises(SystemExit, match="hashed 2 tabpfn checkpoints"):
        run([source], check, tmp_path / "out2", **APPROX, **{"max-cell-error": 1e-3})


# --- the measurement, the Lending Club figure, and what names a cell --------------------


def test_a_measurement_writes_its_record_and_no_rows(tmp_path, capsys):
    source = tabpfn_dir(tmp_path, "src", model="tabpfn", seeds=[11], temperature=0.9)
    check = tabpfn_dir(tmp_path, "probe", model="tabpfn@t1", seeds=[11], temperature=1.0,
                       pd_of=stretched(1.001))
    out = tmp_path / "out"
    # A bound under the planted error names the cells and refuses nothing: nothing is derived.
    assert run([source], check, out, **APPROX, **{"max-cell-error": 5e-4, "measure-only": True}) == 0
    assert sorted(p.name for p in out.iterdir()) == [dt.DERIVE_FILE]
    account = json.loads((out / dt.DERIVE_FILE).read_text(encoding="utf-8"))
    verified = account["check"]
    assert account["measure_only"] is True and account["approximate"] is True
    assert verified["refused_above_bound"] is False and len(verified["cells_above_bound"]) == 3
    assert verified["cells_above_lending_club_figure"] == 3
    assert verified["cells_above_lending_club_figure_named"][0].startswith("2015H1-E 11/")
    assert "only; no rows" in capsys.readouterr().out
    # Without a bound the measurement stands and records none.
    again = tmp_path / "again"
    assert run([source], check, again, **APPROX, **{"measure-only": True}) == 0
    assert json.loads((again / dt.DERIVE_FILE).read_text(encoding="utf-8"))["check"][
        "max_cell_error"] is None


def test_a_measurement_is_approximate_and_of_the_sources_own_cells(tmp_path):
    source = scored_dir(tmp_path, "src", model="tabicl", seeds=[11], temperature=0.9)
    check = scored_dir(tmp_path, "probe", model="tabicl@t1", seeds=[11], temperature=1.0,
                       pd_of=rescaled(default_pd, 0.9, 1.0))
    with pytest.raises(SystemExit, match="an exact derivation's check is written with its rows"):
        run([source], check, tmp_path / "out", **{"measure-only": True})
    with pytest.raises(SystemExit, match="would measure another build's"):
        run([source], check, tmp_path / "out", **APPROX,
            **{"measure-only": True, "check-source": source})


def test_the_lending_club_figure_is_counted_and_only_the_bound_refuses(tmp_path):
    source = tabpfn_dir(tmp_path, "src", model="tabpfn", seeds=[11], temperature=0.9)
    check = tabpfn_dir(tmp_path, "probe", model="tabpfn@t1", seeds=[11], temperature=1.0,
                       pd_of=stretched(1.001))
    out = tmp_path / "out"
    assert run([source], check, out, **APPROX, **{"max-cell-error": 8.4e-3}) == 0
    verified = json.loads((out / dt.DERIVE_FILE).read_text(encoding="utf-8"))["check"]
    assert verified["lending_club_figure"] == dt.LENDING_CLUB_FIGURE
    assert verified["cells_above_lending_club_figure"] == 3 and verified["cells_above_bound"] == []
    assert verified["mean_cell_error"] == pytest.approx(1e-3, abs=1e-9)
    for gap in (verified["cox_slope_gap"], verified["oe_gap"]):
        assert gap["cells"] == 3 and np.isfinite(gap["worst"]) and np.isfinite(gap["mean"])
        assert abs(gap["worst"]) >= abs(gap["mean"])
    cells = verified["cells"]
    assert verified["cox_slope_gap"]["mean"] == pytest.approx(
        np.mean([c["cox_slope_gap"] for c in cells]))


def test_a_probability_that_is_not_a_number_in_the_check_refuses(tmp_path):
    source = scored_dir(tmp_path, "src", model="tabicl", seeds=[11], temperature=0.9)

    def holed(seed, cell, n):
        p = rescaled(default_pd, 0.9, 1.0)(seed, cell, n)
        if cell == "2015Q4":
            p[5] = np.nan
        return p

    check = scored_dir(tmp_path, "probe", model="tabicl@t1", seeds=[11], temperature=1.0,
                       pd_of=holed)
    with pytest.raises(SystemExit, match="2015H1-E 11/2015Q4: a probability that is not a number"):
        run([source], check, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_every_checked_cell_is_named_by_its_build(tree):
    source_a, source_b, check, out = tree
    assert run([source_a, source_b], check, out) == 0
    verified = json.loads((out / dt.DERIVE_FILE).read_text(encoding="utf-8"))["check"]
    assert {c["build_id"] for c in verified["cells"]} == {"2015H1-E"}
    assert {c["build_id"] for c in verified["unchecked_cells"]} == {"2015H1-E"}
    scores = pd.read_parquet(check / dt.SCORES_FILE)
    scores[~((scores["cohort"] == "2015Q3") & (scores["row"] == 5))].to_parquet(
        check / dt.SCORES_FILE, index=False)
    with pytest.raises(SystemExit, match="cell 2015H1-E 11/2015Q3"):
        run([source_a], check, out.parent / "out2")


def test_a_check_source_draw_the_sources_do_not_hold_is_refused(tmp_path):
    source, check_source, check, out = through(tmp_path,
                                               check_source_kw={"seeds": [11, 13]})
    with pytest.raises(SystemExit, match="a draw the sources do not hold"):
        run_through(source, check_source, check, out)
    assert not out.exists()


def test_an_exact_source_on_another_device_than_the_check_is_refused(tmp_path):
    """The identity carried to the sources was measured on one device; a source on another is refused."""
    source, check_source, check, out = through(tmp_path,
                                               source_kw={"device": "NVIDIA Tesla T4"})
    with pytest.raises(SystemExit, match="checked on one device"):
        run_through(source, check_source, check, out)
    assert not out.exists()
    # On one device throughout the same rows are carried, and every device is recorded.
    (tmp_path / "same").mkdir()
    source, check_source, check, out = through(tmp_path / "same")
    assert run_through(source, check_source, check, out) == 0
    devices = json.loads((out / dt.DERIVE_FILE).read_text(encoding="utf-8"))["devices"]
    assert set(devices["sources"].values()) == {devices["check_source"]} == {devices["check"]}


def test_rescale_is_the_logit_scale_and_its_own_inverse():
    p = probabilities(SEED, 100)
    forward = dt.rescale(p, 0.9, 1.0)
    assert np.allclose(np.log(forward / (1 - forward)), 0.9 * np.log(p / (1 - p)))
    assert np.allclose(dt.rescale(forward, 1.0, 0.9), p, atol=1e-12)
    assert np.allclose(dt.rescale(p, 0.9, 0.9), p, atol=1e-15)
    with pytest.raises(SystemExit, match="no logit"):
        dt.rescale(np.array([0.0, 0.5]), 0.9, 1.0)
