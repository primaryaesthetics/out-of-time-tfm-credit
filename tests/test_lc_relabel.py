"""The twenty-four-month relabelling of recorded Lending Club scores, on a synthetic book.

A row whose window is open at the snapshot has to leave and be counted, never
be read as a non-default; a cohort has to enter whole or not at all; the
recorded directories have to stay as they were; and the twelve-month reading
through the copies has to be the pooling of the recorded scores on the same
cells, row for row.
"""

from __future__ import annotations

import hashlib
import json
import sys
import zlib
from pathlib import Path

import numpy as np
import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("matplotlib")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import arm_intervals as ai
import arm_weights as aw
import lc_relabel as lr

SEED = 20260924
QUARTERS = {"2016Q3": (2016, 7), "2016Q4": (2016, 10), "2017Q1": (2017, 1), "2017Q2": (2017, 4)}
BUILDS = {"2016H1-E": ["2016Q3", "2016Q4", "2017Q1", "2017Q2"],
          "2016H2-E": ["2016Q4", "2017Q1", "2017Q2"]}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@pytest.fixture(autouse=True)
def small_cohorts_clear_the_floors(monkeypatch):
    monkeypatch.setattr(ai.bi, "FLOOR_ROWS", 0)
    monkeypatch.setattr(ai.bi, "FLOOR_DEFAULTS", 0)


def month(year: int, m: int, plus: int = 0) -> str:
    total = year * 12 + m - 1 + plus
    return f"{MONTHS[total % 12]}-{total // 12}"


def write_book(path: Path, snapshot: tuple[int, int] = (2019, 3), per_month: int = 90) -> Path:
    """Loans issued monthly from Jul-2016 to Jun-2017; the latest last payment is the snapshot.

    A charged-off loan's last payment lies one to thirty months after issue, so some
    default inside twelve months, some between twelve and twenty-four, some later.
    The first row has no issue date and is dropped by the loader, which moves every
    position after it by one.
    """
    rng = np.random.default_rng(SEED)
    rows = [{"issue_d": None, "loan_status": "Fully Paid", "last_pymnt_d": "Jan-2017"}]
    snap = month(*snapshot)
    for year, first in QUARTERS.values():
        for k in range(3):
            for _ in range(per_month):
                draw = rng.uniform()
                # No payment falls after the snapshot, which is the latest one.
                room = (snapshot[0] * 12 + snapshot[1]) - (year * 12 + first + k)
                if draw < 0.35:
                    status, paid = "Charged Off", month(year, first + k,
                                                        min(int(rng.integers(1, 31)), room))
                elif draw < 0.7:
                    status, paid = "Fully Paid", month(year, first + k,
                                                       min(int(rng.integers(1, 26)), room))
                else:
                    status, paid = "Current", snap
                rows.append({"issue_d": month(year, first + k), "loan_status": status,
                             "last_pymnt_d": paid})
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def cohort_positions(frame: pd.DataFrame, cohort: str, size: int = 200) -> np.ndarray:
    year, first = QUARTERS[cohort]
    issued = frame["issue_d"]
    inside = np.flatnonzero((issued.dt.year == year) & issued.dt.month.isin([first, first + 1,
                                                                              first + 2]))
    rng = np.random.default_rng(zlib.crc32(cohort.encode("utf-8")))
    return np.sort(rng.choice(inside, size=size, replace=False))


def write_scores(book: Path, root: Path, builds: dict[str, list[str]] = BUILDS) -> dict[str, list[Path]]:
    """Two score directories per build: the fitted models, and a seeded model with a derive.json."""
    frame = lr.load(book)
    twelve, _ = lr.labels_at(frame, 12)
    rng = np.random.default_rng(SEED)
    out: dict[str, list[Path]] = {}
    for build, cohorts in builds.items():
        parts = {"fitted": (("scorecard", [None]), ("gbm", [None]), ("gbm-50k", [11, 12])),
                 "tabpfn": (("tabpfn", [11, 12]),)}
        dirs = []
        for part, models in parts.items():
            frames, refs = [], []
            for age, cohort in enumerate(cohorts, start=1):
                rows = cohort_positions(frame, cohort)
                y = twelve[rows]
                assert (y >= 0).all()
                for model, seeds in models:
                    for s in seeds:
                        score = 1 / (1 + np.exp(-(-2.5 + 1.2 * y + rng.normal(0, 1, rows.size))))
                        frames.append(pd.DataFrame({
                            "as_of": "2016-06-30", "build_id": build, "arm": "E", "model": model,
                            "context_seed": s, "cohort": cohort, "age_quarters": age,
                            "row": rows, "outcome": y, "pd": score}))
            for model, seeds in models:
                for s in seeds:
                    refs.append(pd.DataFrame({"build_id": build, "model": model, "context_seed": s,
                                              "pd": rng.uniform(0.02, 0.3, 400)}))
            directory = root / f"{build.lower()}-{part}"
            directory.mkdir(parents=True)
            scores = pd.concat(frames, ignore_index=True)
            scores["context_seed"] = scores["context_seed"].astype("Int64")
            scores.sample(frac=1.0, random_state=SEED).to_parquet(directory / "scores.parquet",
                                                                  index=False)
            reference = pd.concat(refs, ignore_index=True)
            reference["context_seed"] = reference["context_seed"].astype("Int64")
            reference.to_parquet(directory / "reference.parquet", index=False)
            if part == "tabpfn":
                (directory / "derive.json").write_text(json.dumps({
                    "derived_as": "tabpfn", "approximate": True, "checked_build": [build],
                    "check": {"cells": [{"build_id": build, "context_seed": 11, "cell": "reference",
                                         "logit_slope_gap": 4e-4, "cox_slope_gap": 0.01,
                                         "oe_gap": 0.001}]}}), encoding="utf-8")
            dirs.append(directory)
        out[build] = dirs
    return out


def relabel(book: Path, dirs: list[Path], out: Path) -> dict:
    assert lr.main([str(book), *map(str, dirs), "--out-dir", str(out)]) == 0
    return json.loads((out / "label24.json").read_text(encoding="utf-8"))


def digest(directory: Path) -> dict[str, str]:
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob("*")) if p.is_file()}


def test_a_row_with_an_open_window_is_dropped_and_counted_never_labelled_zero(tmp_path):
    book = write_book(tmp_path / "book.csv")
    dirs = write_scores(book, tmp_path / "scores")
    account = relabel(book, dirs["2016H1-E"], tmp_path / "label24")
    assert account["label"]["24"]["definition"]["last_labelable_origination"] == "2017-03-01"
    late = account["cohorts"]["2017Q2"]
    assert late == {"rows": 200, "open_window_rows": 200, "enters": False, "rows_dropped": 200,
                    "defaults_12": late["defaults_12"], "defaults_24": None}
    assert account["rows_dropped"] == 200 and account["open_window_rows"] == 200
    labels = pd.read_parquet(tmp_path / "label24" / "labels.parquet")
    assert "2017Q2" not in set(labels["cohort"])
    assert set(labels["outcome_24"]) <= {0, 1}
    for copy in account["copies"]:
        scores = pd.read_parquet(Path(copy) / "scores.parquet")
        assert "2017Q2" not in set(scores["cohort"])
        assert scores["outcome_24"].notna().all()


def test_a_cohort_after_2017q1_contributes_no_cell(tmp_path):
    book = write_book(tmp_path / "book.csv")
    dirs = write_scores(book, tmp_path / "scores")
    a = relabel(book, dirs["2016H1-E"], tmp_path / "a")
    b = relabel(book, dirs["2016H2-E"], tmp_path / "b")
    assert a["cohorts_kept"] == ["2016Q3", "2016Q4", "2017Q1"] and a["cells_kept"] == 3
    assert b["cohorts_kept"] == ["2016Q4", "2017Q1"] and b["cohorts_dropped"] == ["2017Q2"]


def test_a_cell_is_read_whole_or_not_at_all(tmp_path):
    # At a February snapshot the window closes on 2017-02-01: 2017Q1's January and
    # February loans are labelled, its March loans are not, and the cohort leaves whole.
    book = write_book(tmp_path / "book.csv", snapshot=(2019, 2))
    dirs = write_scores(book, tmp_path / "scores")
    account = relabel(book, dirs["2016H1-E"], tmp_path / "label24")
    q1 = account["cohorts"]["2017Q1"]
    assert 0 < q1["open_window_rows"] < q1["rows"]
    assert q1["enters"] is False and q1["rows_dropped"] == q1["rows"] == 200
    assert account["cohorts_kept"] == ["2016Q3", "2016Q4"]
    labels = pd.read_parquet(tmp_path / "label24" / "labels.parquet")
    assert set(labels["cohort"]) == {"2016Q3", "2016Q4"}


def test_a_build_with_no_closed_cohort_writes_its_account_and_no_copy(tmp_path):
    book = write_book(tmp_path / "book.csv")
    dirs = write_scores(book, tmp_path / "scores", {"2017H1-E": ["2017Q2"]})
    account = relabel(book, dirs["2017H1-E"], tmp_path / "label24")
    assert account["cells_kept"] == 0 and account["copies"] == []
    assert sorted(p.name for p in (tmp_path / "label24").iterdir()) == ["label24.json"]


def test_a_recorded_outcome_that_differs_from_the_rebuilt_label_refuses_the_build(tmp_path):
    book = write_book(tmp_path / "book.csv")
    dirs = write_scores(book, tmp_path / "scores")
    path = dirs["2016H1-E"][1] / "scores.parquet"
    scores = pd.read_parquet(path)
    scores.loc[0, "outcome"] = 1 - scores.loc[0, "outcome"]
    scores.to_parquet(path, index=False)
    with pytest.raises(SystemExit, match="differs from the 12-month label"):
        lr.main([str(book), *map(str, dirs["2016H1-E"]), "--out-dir", str(tmp_path / "out")])


def test_the_recorded_directories_stay_as_they_were(tmp_path):
    book = write_book(tmp_path / "book.csv")
    dirs = write_scores(book, tmp_path / "scores")
    before = {d: digest(d) for d in dirs["2016H1-E"]}
    account = relabel(book, dirs["2016H1-E"], tmp_path / "label24")
    assert {d: digest(d) for d in dirs["2016H1-E"]} == before
    for source, copy in zip(dirs["2016H1-E"], map(Path, account["copies"])):
        assert copy.parent == tmp_path / "label24" and copy.name == source.name
        for name in ("reference.parquet", "derive.json"):
            if (source / name).exists():
                assert (copy / name).read_bytes() == (source / name).read_bytes()
        original = pd.read_parquet(source / "scores.parquet")
        copied = pd.read_parquet(copy / "scores.parquet")
        kept = original[original["cohort"].isin(account["cohorts_kept"])].reset_index(drop=True)
        pd.testing.assert_frame_equal(copied.drop(columns="outcome_24"), kept)
    labels = pd.read_parquet(tmp_path / "label24" / "labels.parquet")
    assert (labels["outcome_24"] >= labels["outcome"]).all()
    assert ((labels["outcome"] == 0) & (labels["outcome_24"] == 1)).any()


def _filtered(dirs: dict[str, list[Path]], root: Path, kept: dict[str, list[str]]) -> list[Path]:
    """The recorded directories with only the kept cohorts, written by hand for the comparison."""
    out = []
    for build, sources in dirs.items():
        for source in sources:
            target = root / source.name
            target.mkdir(parents=True)
            scores = pd.read_parquet(source / "scores.parquet")
            scores[scores["cohort"].isin(kept[build])].to_parquet(target / "scores.parquet",
                                                                  index=False)
            for name in ("reference.parquet", "derive.json"):
                if (source / name).exists():
                    (target / name).write_bytes((source / name).read_bytes())
            out.append(target)
    return out


def test_the_twelve_month_reading_through_the_copies_is_the_recorded_pooling(tmp_path):
    book = write_book(tmp_path / "book.csv")
    dirs = write_scores(book, tmp_path / "scores")
    copies, kept = [], {}
    for build, sources in dirs.items():
        account = relabel(book, sources, tmp_path / f"{build}-label24")
        copies += [Path(c) for c in account["copies"]]
        kept[build] = account["cohorts_kept"]
    by_hand = _filtered(dirs, tmp_path / "by-hand", kept)
    common = ["--resamples", "20", "--check-seeds", "5"]
    assert ai.main([*map(str, by_hand), "--out-dir", str(tmp_path / "hand"), *common]) == 0
    assert aw.main([*map(str, copies), "--out-dir", str(tmp_path / "copy"), "--outcome",
                    "outcome", *common]) == 0
    for name in ("paired.csv", "paired-seeds.csv"):
        pd.testing.assert_frame_equal(pd.read_csv(tmp_path / "copy" / name),
                                      pd.read_csv(tmp_path / "hand" / name))


def test_with_every_cohort_closed_the_copies_reproduce_the_recorded_pooling(tmp_path):
    book = write_book(tmp_path / "book.csv")
    builds = {"2016H1-E": ["2016Q3", "2016Q4", "2017Q1"], "2016H2-E": ["2016Q4", "2017Q1"]}
    dirs = write_scores(book, tmp_path / "scores", builds)
    copies = []
    for build, sources in dirs.items():
        account = relabel(book, sources, tmp_path / f"{build}-label24")
        assert account["cells_dropped"] == 0
        copies += [Path(c) for c in account["copies"]]
    originals = [d for sources in dirs.values() for d in sources]
    common = ["--resamples", "20", "--check-seeds", "5"]
    assert ai.main([*map(str, originals), "--out-dir", str(tmp_path / "rec"), *common]) == 0
    assert aw.main([*map(str, copies), "--out-dir", str(tmp_path / "copy"), *common]) == 0
    for name in ("paired.csv", "paired-seeds.csv"):
        pd.testing.assert_frame_equal(pd.read_csv(tmp_path / "copy" / name),
                                      pd.read_csv(tmp_path / "rec" / name))


def test_the_longer_reading_reads_the_twenty_four_month_label(tmp_path):
    book = write_book(tmp_path / "book.csv")
    dirs = write_scores(book, tmp_path / "scores")
    account = relabel(book, dirs["2016H1-E"], tmp_path / "label24")
    arm = ai.Arm(outcome="outcome_24")
    arm.add_build([Path(c) for c in account["copies"]], [])
    labels = pd.read_parquet(tmp_path / "label24" / "labels.parquet")
    for cohort, frame in labels.groupby("cohort"):
        ordered = frame.sort_values("row")
        assert np.array_equal(arm.rows[cohort], ordered["row"].to_numpy())
        assert np.array_equal(arm.outcome[cohort], ordered["outcome_24"].to_numpy())
    assert sorted(arm.outcome) == account["cohorts_kept"]


def test_the_pooling_prints_its_cells_and_each_build_s_weight(tmp_path, capsys):
    book = write_book(tmp_path / "book.csv")
    builds = {"2016H1-E": ["2016Q3", "2016Q4", "2017Q1", "2017Q2"],
              "2016H2-E": ["2016Q4", "2017Q1", "2017Q2"]}
    dirs = write_scores(book, tmp_path / "scores", builds)
    copies = []
    for build, sources in dirs.items():
        copies += [Path(c) for c in relabel(book, sources, tmp_path / f"{build}-l")["copies"]]
    out = tmp_path / "out"
    assert aw.main([*map(str, copies), "--out-dir", str(out), "--outcome", "outcome_24",
                    "--resamples", "10", "--no-per-draw"]) == 0
    weights = json.loads((out / "weights.json").read_text(encoding="utf-8"))
    a, b = weights["builds"]["2016H1-E"], weights["builds"]["2016H2-E"]
    assert weights["cells"] == 5 and (a["cells"], b["cells"]) == (3, 2)
    assert (a["weight_mean"], b["weight_mean"]) == pytest.approx((0.6, 0.4))
    # The second PSI leaves each build's first cohort: 2 and 1 cells of 3.
    assert (a["weight_second_psi"], b["weight_second_psi"]) == pytest.approx((2 / 3, 1 / 3))
    # Ages 1..3 and 1..2: squared deviations 2 and 0.5.
    assert (a["weight_auc_slope_build"], b["weight_auc_slope_build"]) == pytest.approx((0.8, 0.2))
    assert a["weight_builds"] == b["weight_builds"] == 0.5
    printed = capsys.readouterr().out
    assert "outcome read          : outcome_24" in printed
    assert "cells in the pooling  : 5" in printed
    assert "2016H1-E     3 cells  mean 0.6000" in printed


def test_a_build_left_with_one_cell_weighs_nothing_in_the_build_slope(tmp_path):
    book = write_book(tmp_path / "book.csv")
    builds = {"2016H1-E": ["2016Q3", "2016Q4", "2017Q1"], "2016H2-E": ["2017Q1", "2017Q2"]}
    dirs = write_scores(book, tmp_path / "scores", builds)
    copies = []
    for build, sources in dirs.items():
        copies += [Path(c) for c in relabel(book, sources, tmp_path / f"{build}-l")["copies"]]
    out = tmp_path / "out"
    assert aw.main([*map(str, copies), "--out-dir", str(out), "--outcome", "outcome_24",
                    "--resamples", "10", "--no-per-draw"]) == 0
    weights = json.loads((out / "weights.json").read_text(encoding="utf-8"))["builds"]
    assert weights["2016H2-E"]["cells"] == 1
    assert weights["2016H2-E"]["weight_auc_slope_build"] == 0.0
    assert weights["2016H2-E"]["weight_second_psi"] == 0.0
