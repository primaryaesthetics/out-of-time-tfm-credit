"""The refit control's early-stopping tail and the point it inherits."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import score_build as sb

from outoftime import gbm as gb
from outoftime.vintage import Quarter


def _quarters(n: int) -> list[Quarter]:
    first = Quarter(1999, 1)
    return [first.shift(k) for k in range(n)]


def test_on_a_flat_book_the_share_tail_is_not_capped_at_four_quarters():
    quarters = _quarters(71)
    counts = dict.fromkeys(quarters, 704)
    assert len(gb.validation_split(quarters, counts)) == 4
    tail = gb.validation_split(quarters, counts, policy=sb.SHARE_TAIL_POLICY)
    # The fewest latest quarters holding a fifth of the rows: 15 of 71.
    assert len(tail) == 15 and tail[-1] == quarters[-1]


def test_where_the_cap_does_not_bind_both_rules_give_the_same_tail():
    # Eight quarters, a quarter of the rows in the last two: the rolling arm's shape.
    quarters = _quarters(8)
    counts = dict.fromkeys(quarters, 6_250)
    assert gb.validation_split(quarters, counts) == gb.validation_split(
        quarters, counts, policy=sb.SHARE_TAIL_POLICY)


def _record(tmp_path: Path, control_point: dict) -> Path:
    full = {"num_leaves": 31, "learning_rate": 0.1, "min_child_samples": 200, "feature_fraction": 0.6}
    units = {"gbm": {"model": "gbm", "summary": {"params": full}},
             "gbm-50k/1": {"model": "gbm-50k", "summary": {"params": control_point}}}
    (tmp_path / "build.json").write_text(json.dumps({"build": {"build_id": "2018H2-E"},
                                                     "units": units}), encoding="utf-8")
    return tmp_path


def test_refit_point_reads_and_checks(tmp_path):
    point = {"num_leaves": 31, "learning_rate": 0.1, "min_child_samples": 200, "feature_fraction": 0.6}
    (tmp_path / "a").mkdir()
    assert sb.refit_point(_record(tmp_path / "a", point), "2018H2-E") == point
    with pytest.raises(SystemExit, match="not 2018H2-R"):
        sb.refit_point(tmp_path / "a", "2018H2-R")
    (tmp_path / "b").mkdir()
    with pytest.raises(SystemExit, match="was not fitted at the full GBM's point"):
        sb.refit_point(_record(tmp_path / "b", {**point, "num_leaves": 7}), "2018H2-E")
