"""The two runs EXP-005 records before any model, on the synthetic book.

The build run has to describe the grid `vintage.builds` emits, on the book the
score runs read, with every count it names and nothing row-level; the feature
run has to write the matrix the gates leave, and the ablation's when asked.
Both write aggregates only, and every file they write under an `-fm-`
directory has to stay trackable.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("pyarrow")
pytest.importorskip("matplotlib")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fm_feature_run as ffr
import fm_synthetic
import fm_vintage_builds as fvb

from outoftime import fm_features as ff


@pytest.fixture(scope="module")
def derived(tmp_path_factory):
    return fm_synthetic.write_derived(tmp_path_factory.mktemp("fm-grid") / "derived",
                                      per_quarter=40)


@pytest.fixture(scope="module")
def grid(derived, tmp_path_factory):
    out = tmp_path_factory.mktemp("fm-vintage-builds")
    assert fvb.main([str(derived), "--out-dir", str(out), "--as-of", "2002-12-31",
                     "2008-12-31", "2012-12-31", "--arms", "E,R", "--min-loans", "50",
                     "--min-defaults", "9"]) == 0
    return out


def test_the_build_run_describes_every_build_and_cell(grid):
    summary = json.loads((grid / "builds.json").read_text(encoding="utf-8"))
    e, r = summary["arms"]["E"], summary["arms"]["R"]
    assert [b["build_id"] for b in e] == ["2002H2-E", "2008H2-E", "2012H2-E"]
    assert [b["build_id"] for b in r] == ["2008H2-R", "2012H2-R"]
    assert summary["skipped"][0]["as_of"] == "2002-12-31"
    assert all(len(b["train_quarters"]) == 8 for b in r)
    assert e[-1]["train_quarters"][-1] == "2010Q3"
    for build in e + r:
        assert build["training_windows_open_at_as_of"] == 0
        assert build["pool"]["labelled"] > 0
        assert build["pool_reported"]["defaults"] >= build["pool"]["defaults"]
    assert e[-1]["blind_loans_with_closed_windows"] > 0
    assert e[-1]["scored_linked_to_training_by_pre_harp_id"] > 0

    # 42, 30 and 22 half-years after the three as-of dates, through 2023H2.
    counts = summary["cell_counts"]
    assert (counts["E"]["cells"], counts["R"]["cells"]) == (94, 52)
    assert counts["E"]["criterion"] + counts["E"]["below_floors"] == 94

    cells = pd.read_csv(grid / "cells.csv")
    assert len(cells) == 94 + 52
    assert (cells["floor"] == ((cells["labelled"] >= 50) & (cells["defaults"] >= 9))).all()
    assert counts["E"]["criterion"] == int(cells[cells["arm"] == "E"]["floor"].sum())
    assert cells["floor"].any() and not cells["floor"].all()
    regime = cells.drop_duplicates("cohort").set_index("cohort")["regime"]
    assert (regime["2011H1"], regime["2011H2"], regime["2013H2"], regime["2014H1"]) == (
        "pre-flag", "straddling", "straddling", "flagged")
    assert (cells["maturity_share"] == 1.0).all()
    assert (cells["defaults_reported"] >= cells["defaults"]).all()
    cohorts = summary["cohorts"]
    assert sum(c["excluded_first_observed_late"] for c in cohorts.values()) > 0
    assert sum(c["excluded_record_gap"] for c in cohorts.values()) > 0
    assert (grid / "build-grid.png").stat().st_size > 0
    assert not list(grid.glob("*.parquet"))


def test_the_feature_run_writes_the_matrix_the_gates_leave(derived, tmp_path):
    primary = tmp_path / "primary"
    assert ffr.main([str(derived), "--out-dir", str(primary)]) == 0
    features = json.loads((primary / "features.json").read_text(encoding="utf-8"))
    assert features["kept"] == list(ff.feature_names()) == features["matrix"]["columns"]
    assert features["dropped"]["dti"] == {"gates": ["value"],
                                          "clauses": [ff.MISSING_SHARE_CLAUSE]}
    assert features["dropped"]["rate"]["gates"] == ["a priori"]
    assert features["dropped"]["vantage_score"]["gates"][0] == "coverage"
    assert features["clip"] == {k: list(v) for k, v in ff.CLIPPED.items()}
    assert features["matrix"]["dtypes"]["purpose"] == "object"
    assert set(json.loads((primary / "gates.json").read_text(encoding="utf-8"))) == {
        "redundancy", "coverage", "values", "shifts"}
    assert (primary / "dropped-columns.png").stat().st_size > 0
    assert (primary / "loan-amount.png").stat().st_size > 0
    assert features["derived"] == {"upb_to_limit": ["upb", "origination_year"]}
    assert features["replaced"] == {"upb": "upb_to_limit"}
    assert len(features["conforming_limit"]) == 28
    assert {"rate", "upb", "upb_to_limit"} <= set(features["calendar_share"])

    nominal = tmp_path / "nominal"
    assert ffr.main([str(derived), "--out-dir", str(nominal), "--ablation", "upb_nominal"]) == 0
    features = json.loads((nominal / "features.json").read_text(encoding="utf-8"))
    assert "upb" in features["kept"] and "upb_to_limit" not in features["kept"]
    assert features["clip"]["upb"] == list(ff.ABLATION_CLIPPED["upb"])
    assert features["derived"] == {}

    ablation = tmp_path / "ablation"
    assert ffr.main([str(derived), "--out-dir", str(ablation), "--ablation", "dti_kept"]) == 0
    features = json.loads((ablation / "features.json").read_text(encoding="utf-8"))
    assert features["ablation"] == "dti_kept" and "dti" in features["kept"]
    assert len(features["kept"]) == len(ff.feature_names()) + 1
    assert features["clip"]["dti"] == list(ff.ABLATION_CLIPPED["dti"])
    assert "dti" not in features["dropped"]
    for out in (primary, ablation):
        assert not list(out.glob("*.parquet"))


def test_what_the_two_runs_write_stays_trackable():
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is not on the path")
    root = Path(__file__).resolve().parent.parent
    for name in ("fm-vintage-builds/builds.json", "fm-vintage-builds/cells.csv",
                 "fm-vintage-builds/build-grid.png", "fm-features/features.json",
                 "fm-features/gates.json", "fm-features/dropped-columns.png",
                 "fm-features/loan-amount.png"):
        path = f"experiments/2026-01-01-{name}"
        result = subprocess.run([git, "check-ignore", "-q", "--no-index", path], cwd=root,
                                check=False)
        assert result.returncode == 1, path
