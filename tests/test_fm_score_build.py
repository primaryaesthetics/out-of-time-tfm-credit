"""One Freddie Mac build end to end, from the reduced files to the interval scripts.

The claim of `fm_score_build.py` is that a build on the second book lands in
the files and the schema of the first, so that the node scorer, the per-build
intervals and the arm pooling read it with no change. That is tested by doing
it: a synthetic book in the reducer's layout, one build scored with a one-point
GBM grid, the bundle exported from the same code and checked against the score
run, the bundle scored on a fake node with the node script's own loader, and
both files handed to the loaders of `build_intervals.py` and `arm_intervals.py`.
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("pyarrow")
pytest.importorskip("lightgbm")
pytest.importorskip("optbinning")
pytest.importorskip("matplotlib")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import arm_intervals as ai
import build_intervals as bi
import fm_export_context as fec
import fm_score_build as fsb
import fm_synthetic
import score_context as node

from outoftime import fm_features
from outoftime import gbm as gb
from outoftime.vintage import HalfYear

AS_OF = "2012-12-31"
SMALL_GRID = gb.GBMPolicy(num_leaves=(7,), learning_rate=(0.1,), min_child_samples=(20,),
                          feature_fraction=(1.0,), max_rounds=40, early_stopping_rounds=5)


class FicoModel:
    """Scores a row from the credit score and the loan size, and checks what the node hands it."""

    def __init__(self):
        self.rate = None

    def get_params(self):
        return {}

    def fit(self, x, y):
        assert x["purpose"].dtype == object and x["state"].dtype == object
        self.rate = float(np.mean(y))
        return self

    def predict_proba(self, x):
        fico = x["fico"].fillna(700.0).to_numpy(dtype=float)
        size = x["upb_to_limit"].to_numpy(dtype=float) + x["ltv"].to_numpy(dtype=float) / 100.0
        p = np.clip(self.rate + 0.001 * (700.0 - fico) + 0.01 * size, 0.01, 0.99)
        return np.column_stack([1 - p, p])


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    root = tmp_path_factory.mktemp("fm-build")
    # A hundred loans a quarter: the Cox fit of the interval script on a
    # cohort needs more defaults than a smaller book leaves it.
    derived = fm_synthetic.write_derived(root / "derived", per_quarter=100)
    design = [str(derived), "--as-of", AS_OF, "--context-rows", "400", "--seeds", "11,12"]
    console = io.StringIO()
    with pytest.MonkeyPatch.context() as patch, contextlib.redirect_stdout(console):
        patch.setattr(gb, "DEFAULT_POLICY", SMALL_GRID)
        assert fsb.main([*design, "--out-dir", str(root / "scores"), "--quiet-metrics",
                         "--n-jobs", "1"]) == 0
        assert fec.main([*design, "--out-dir", str(root / "bundle"),
                         "--expect-scores", str(root / "scores")]) == 0
    return {"root": root, "derived": derived, "design": design, "console": console.getvalue()}


def test_the_score_files_carry_the_classical_schema_and_the_other_readings(run):
    scores_dir = run["root"] / "scores"
    scores = pd.read_parquet(scores_dir / "scores.parquet")
    reference = pd.read_parquet(scores_dir / "reference.parquet")
    assert set(node.SCORE_COLUMNS) <= set(scores.columns)
    assert set(node.REFERENCE_COLUMNS) <= set(reference.columns)
    for name in ("outcome_reported", "outcome_horizon"):
        assert name in scores.columns and name in reference.columns
    assert set(scores["model"]) == {"scorecard", "gbm", "gbm-50k"}
    assert set(scores["context_seed"].dropna()) == {11, 12}
    assert str(scores["context_seed"].dtype) == "Int64"
    assert scores["build_id"].unique().tolist() == ["2012H2-E"]

    cohorts = sorted(scores["cohort"].unique())
    assert cohorts[0] == "2013H1" and cohorts[-1] == "2023H2" and len(cohorts) == 22
    ages = scores.groupby("cohort")["age_quarters"].unique()
    assert [int(ages[c][0]) for c in cohorts] == list(range(1, 44, 2))
    # Counting the relief months only ever adds defaults, and a default inside
    # twelve months is a default inside twenty-four.
    assert (scores["outcome_reported"] >= scores["outcome"]).all()
    assert (scores["outcome_reported"] > scores["outcome"]).any()
    horizon = scores[scores["outcome_horizon"] >= 0]
    assert len(horizon) == len(scores)
    assert (horizon["outcome_horizon"] <= horizon["outcome"]).all()
    assert (horizon["outcome_horizon"] < horizon["outcome"]).any()

    table = pd.read_csv(scores_dir / "cohorts.csv")
    assert {"rows", "defaults", "defaults_reported", "cohort", "age_quarters"} <= set(table.columns)


def test_the_build_record_holds_the_gates_the_exclusions_and_the_exposure(run):
    record = json.loads((run["root"] / "scores" / "build.json").read_text(encoding="utf-8"))
    assert set(record["gates"]) == {"redundancy", "coverage", "values", "shifts"}
    assert record["gates"]["values"]["dti"]["gates"] == ["value"]
    assert "occupancy" in record["gates"]["shifts"]["flagged"]
    exclusions = record["exclusions"]
    years = fm_synthetic.LAST_YEAR - fm_synthetic.FIRST_YEAR + 1
    assert exclusions["redated"] == years * fm_synthetic.REDATED_PER_YEAR
    assert exclusions["without_performance_record"] == fm_synthetic.WITHOUT_RECORD
    assert sum(exclusions["first_observed_age"].values()) == exclusions["book"]
    assert exclusions["excluded_first_observed_late"] > 0
    assert exclusions["excluded_record_gap"] > 0
    assert record["label"]["left_truncated"] == exclusions["excluded_first_observed_late"]
    assert record["label"]["record_gaps"] == exclusions["excluded_record_gap"]
    exposure = record["exposure"]
    assert exposure["training_windows_open_at_as_of"] == 0
    assert exposure["blind_loans_with_closed_windows"] > 0
    assert exposure["scored_linked_to_training_by_pre_harp_id"] > 0

    grid = record["grid"]
    assert grid["max_first_observed_age"] == 3 and grid["exclude_record_gaps"] is True
    assert (grid["book"]["first_cohort"], grid["book"]["axis_gap_months"],
            grid["book"]["rolling_quarters"], grid["book"]["max_clock_lag_months"]) == (
        "1999H1", 27, 8, 5)
    assert grid["gate_span"] == {"first_cohort": "1999Q1", "last_cohort": "2023H2"}
    assert record["build"]["train_quarters"][-1] == "2010Q3"
    assert record["build"]["axis_horizon"] == "2010-09-30"
    assert record["label"]["definition"]["relief_months_count"] is False
    assert record["label_reported"]["definition"]["relief_months_count"] is True
    assert record["label_horizon"]["definition"]["window_months"] == 12
    assert record["seeds"]["test_sample_inert"] is True
    assert record["features"] == list(fm_features.feature_names())

    scores = pd.read_parquet(run["root"] / "scores" / "scores.parquet")
    card = scores[scores["model"] == "scorecard"]
    linked = 0
    for cohort, maturity in record["cohort_maturity"].items():
        # Whole cohorts: every labelled loan of the half-year is scored.
        assert maturity["scored"] == maturity["labelled"] == int((card["cohort"] == cohort).sum())
        assert 0 < maturity["labelled_share"] <= 1
        assert maturity["window_open_at_cutoff"] == 0
        assert {"excluded_first_observed_late", "excluded_record_gap"} <= set(maturity)
        linked += maturity["scored_linked_to_training_by_pre_harp_id"]
    assert linked == exposure["scored_linked_to_training_by_pre_harp_id"]


def test_quiet_metrics_prints_counts_and_times_only(run):
    console = run["console"]
    assert "gbm-50k/11" in console and "fit" in console
    assert "gini" not in console and "O/E" not in console


def test_the_bundle_is_the_score_runs_rows_and_the_node_reads_it(run, monkeypatch):
    bundle = run["root"] / "bundle"
    description = json.loads((bundle / node.DESCRIPTION_FILE).read_text(encoding="utf-8"))
    assert description["categorical"] == list(fm_features.categorical_names())
    assert description["context"]["seeds"] == [11, 12]
    assert description["checks"]["context"]["11"]["identical"] is True
    assert next(iter(description["cohorts"])) == "2013H1"

    built = []

    def fake(name, device, categorical, settings=None):
        built.append(categorical)
        return FicoModel()

    monkeypatch.setattr(node, "build", fake)
    out = run["root"] / "node"
    node.run(bundle, out, ["tabpfn"], nearest=None, seeds=None, device="auto", chunk=0,
             repeat=True)
    features = description["features"]
    assert built[0] == [features.index(name) for name in description["categorical"]]

    tfm = pd.read_parquet(out / "scores.parquet")
    classical = pd.read_parquet(run["root"] / "scores" / "scores.parquet")
    card = classical[classical["model"] == "scorecard"]
    assert set(tfm["context_seed"]) == {11, 12}
    assert sorted(tfm["cohort"].unique()) == sorted(card["cohort"].unique())
    for (_, cohort), cell in tfm.groupby(["context_seed", "cohort"]):
        mine = cell.sort_values("row")
        theirs = card[card["cohort"] == cohort].sort_values("row")
        assert np.array_equal(mine["row"].to_numpy(), theirs["row"].to_numpy())
        assert np.array_equal(mine["outcome"].to_numpy(), theirs["outcome"].to_numpy())
        assert mine["age_quarters"].unique().tolist() == theirs["age_quarters"].unique().tolist()


def test_the_interval_scripts_read_the_build_unchanged(run, monkeypatch):
    bundle = run["root"] / "bundle"
    out = run["root"] / "node-intervals"
    monkeypatch.setattr(node, "build", lambda name, device, categorical, settings=None: FicoModel())
    node.run(bundle, out, ["tabicl"], nearest=None, seeds=None, device="auto", chunk=0,
             repeat=False)
    scores_dir = run["root"] / "scores"
    # The loading and per-cell path of build_intervals.main, on the two
    # directories as it would be given them.
    dirs = (scores_dir, out)
    scores = pd.concat([pd.read_parquet(d / "scores.parquet") for d in dirs], ignore_index=True)
    reference = pd.concat([pd.read_parquet(d / "reference.parquet") for d in dirs],
                          ignore_index=True)
    assert scores["build_id"].nunique() == 1 and reference["build_id"].nunique() == 1
    assert not scores[["model", "context_seed", "cohort", "row"]].duplicated().any()
    edges = bi.reference_edges(reference)
    table = bi.cell_table(scores, reference, edges)
    assert set(table["model"]) == {"scorecard", "gbm", "gbm-50k", "tabicl"}
    pooled, dropped_seeds = bi.shared_seeds(scores)
    shared, dropped = bi.shared_cohorts(pooled)
    cohorts, models = bi.load_cohorts(pooled, shared)
    assert not dropped and not dropped_seeds
    assert min(cohorts) == "2013H1" and len(cohorts) == 22
    assert set(models) == {"scorecard", "gbm", "gbm-50k", "tabicl"}

    arm = ai.Arm()
    assert arm.add_build([scores_dir, out], []) == "2012H2-E"
    assert arm.first_cohort["2012H2-E"] == "2013H1"
    assert arm.ages[("2012H2-E", "2023H2")] == 43


def test_the_seasoned_and_gapped_exclusions_are_arguments(run):
    design = [*run["design"], "--out-dir", str(run["root"] / "unused")]
    default = fsb.prepare(fsb.parse_args(design))
    loose = fsb.prepare(fsb.parse_args([*design, "--max-first-observed-age", "none",
                                        "--keep-record-gaps"]))
    assert "left_truncated" not in loose.primary.as_dict()
    assert "record_gaps" not in loose.primary.as_dict()
    # Every loan the loose reading labels is labelled the same way unless it
    # was excluded; an excluded loan the loose reading could not label either
    # is counted as excluded and changes nothing else.
    excluded = set(default.primary.left_truncated) | set(default.primary.record_gaps)
    assert excluded
    assert set(default.primary.indices) == set(loose.primary.indices) - excluded
    assert loose.grid["max_first_observed_age"] is None


def test_the_ablation_reaches_the_matrix_and_the_record(run):
    design = [*run["design"], "--out-dir", str(run["root"] / "unused"), "--ablation", "dti_kept"]
    prepared = fsb.prepare(fsb.parse_args(design))
    assert list(prepared.matrix.columns) == list(fm_features.feature_names(ablation="dti_kept"))
    assert prepared.grid["ablation"] == "dti_kept"
    assert prepared.gates["values"]["dti"]["ablation"] == "dti_kept"
    fm_features.declaration("dti_kept").assert_matrix_clean(prepared.matrix)


def test_a_gap_after_the_window_does_not_exclude_a_loan(run):
    # The synthetic book plants a month missing after the slice on loan 10
    # of every third quarter and one inside it on loan 11 of every fourth.
    args = fsb.parse_args([*run["design"], "--out-dir", str(run["root"] / "unused")])
    book = fsb.load_book(args, HalfYear)
    index = np.asarray([int(loan[-7:]) % 100 for loan in book.loan_ids])
    quarter = np.asarray([loan[4] for loan in book.loan_ids])
    after = set(np.flatnonzero((index == 10) & (quarter == "3")).tolist())
    inside = set(np.flatnonzero((index == 11) & (quarter == "4")).tolist())
    primary = book.primary
    gaps = set(primary.record_gaps)
    assert gaps and gaps <= inside and not gaps & after
    unlabelled = set(primary.left_truncated) | set(primary.dropped_immature) | set(
        primary.censored)
    labelled_after = sorted(after - unlabelled)
    assert labelled_after
    for i in labelled_after:
        assert book.outcome[i] >= 0 and book.outcome_reported[i] >= 0
        assert book.outcome_horizon[i] >= 0
    assert book.exclusions["excluded_record_gap"] == len(gaps)


def test_a_last_cohort_whose_windows_are_still_open_is_refused(run):
    design = [*run["design"], "--out-dir", str(run["root"] / "unused"), "--last-cohort", "2024H1"]
    with pytest.raises(SystemExit, match="open at the cutoff"):
        fsb.prepare(fsb.parse_args(design))


def test_row_level_files_of_either_book_are_never_tracked():
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is not on the path")
    root = Path(__file__).resolve().parent.parent

    def ignored(path: str) -> bool:
        return subprocess.run([git, "check-ignore", "-q", "--no-index", path], cwd=root,
                              check=False).returncode == 0

    assert ignored("experiments/2026-01-01-fm-2008h2e-scores/scores.parquet")
    assert ignored("experiments/2026-01-01-fm-2008h2e-bundle/context.parquet")
    assert ignored("experiments/2026-01-01-fm-2008h2e-node/parts/tabpfn-11-2009H1.parquet")
    assert not ignored("experiments/2026-01-01-fm-2008h2e-scores/cohorts.csv")
    assert not ignored("experiments/2026-01-01-fm-2008h2e-scores/build.json")
    assert not ignored("experiments/2026-01-01-fm-2008h2e-scores/manifest.json")
    assert ignored("experiments/2026-01-01-lc-2015h1e-scores/scores.parquet")
    assert ignored("experiments/2026-01-01-lc-2015h1e-scores/reference.parquet")
    assert ignored("experiments/2026-01-01-lc-2015h1e-bundle/scored.parquet")
    assert ignored("experiments/2026-01-01-lc-2015h1e-tabicl-colab-t4/parts/tabicl-20260911-2015Q3.parquet")
    assert not ignored("experiments/2026-01-01-lc-2015h1e-intervals/metrics.parquet")
    assert not ignored("experiments/2026-01-01-lc-2015h1e-folds/folds.parquet")
    assert not ignored("experiments/2026-01-01-lc-2015h1e-scores/manifest.json")
