"""The rule that sizes the Freddie Mac grid, at its thresholds and on a probe's records.

The rule is fixed before the speed it reads exists, so what has to hold is
that it selects what EXP-005 says it selects on either side of each threshold,
and that a probe's node records are read into the same two speeds a person
would compute by hand.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fm_grid_budget as fb


def speed_for(hours: float, rows: int, passes: int) -> float:
    """The per-row speed at which `passes` passes over `rows` take `hours` with the margin."""
    return hours * 3600.0 / (fb.MARGIN * rows * passes)


def test_the_walls_are_the_formulas_of_the_file() -> None:
    w = fb.walls(0.002, 0.005)
    assert w["full"] == pytest.approx(1.25 * fb.ROWS_EXPANDING * (3 * 0.002 + 6 * 0.005) / 3600)
    assert w["derived"] == pytest.approx(1.25 * fb.ROWS_EXPANDING * (3 * 0.002 + 3 * 0.005) / 3600)
    assert w["rolling"] == pytest.approx(1.25 * fb.ROWS_ROLLING * (3 * 0.002 + 3 * 0.005) / 3600)
    assert fb.ROWS_EXPANDING == 6_204_654
    assert fb.ROWS_ROLLING == 5_126_804


def test_each_rule_is_chosen_on_its_side_of_the_threshold() -> None:
    # Equal speeds for both models make W_full nine passes and W_derived six.
    under_full = speed_for(29.9, fb.ROWS_EXPANDING, 9)
    assert fb.decide(under_full, under_full)["rule"] == 1
    assert fb.decide(under_full, under_full)["tabpfn_at_1"] == "scored"
    between = speed_for(29.9, fb.ROWS_EXPANDING, 6)
    assert fb.decide(between, between)["rule"] == 2
    assert fb.decide(between, between)["tabpfn_at_1"] == "derived"
    over = speed_for(31.0, fb.ROWS_EXPANDING, 6)
    third = fb.decide(over, over)
    assert third["rule"] == 3
    assert third["tabpfn_at_1"] == "derived"
    assert third["rolling_arm_on_device"] is False


def test_the_rolling_arm_rides_on_the_chosen_expanding_wall() -> None:
    fast = fb.decide(1e-4, 1e-4)
    assert fast["rolling_arm_on_device"] is True
    assert fast["device_hours"] == pytest.approx(
        fast["walls_hours"]["full"] + fast["walls_hours"]["rolling"], abs=0.02)
    # A speed at which the full expanding arm fits under 30 h but adding the
    # rolling arm passes 45 h leaves the rolling arm classical.
    s = speed_for(29.9, fb.ROWS_EXPANDING, 9)
    mid = fb.decide(s, s)
    assert mid["rule"] == 1
    assert mid["walls_hours"]["full"] + mid["walls_hours"]["rolling"] > fb.ROLLING_LIMIT_HOURS
    assert mid["rolling_arm_on_device"] is False
    assert mid["h4_tested"] is False


def test_a_probe_is_read_as_seconds_over_rows_per_model(tmp_path: Path) -> None:
    for name, cells in {
        "a": [{"model": "tabpfn", "rows": 50_000, "seconds": 100.0},
              {"model": "tabpfn", "rows": 20_000, "seconds": 40.0}],
        "b": [{"model": "tabpfn@t1", "rows": 20_000, "seconds": 40.0},
              {"model": "tabicl", "rows": 50_000, "seconds": 50.0}],
    }.items():
        (tmp_path / name).mkdir()
        (tmp_path / name / "node.json").write_text(json.dumps({"cells": cells}), encoding="utf-8")
    speeds = fb.probe_speeds([tmp_path / "a", tmp_path / "b"])
    assert speeds["tabpfn"] == pytest.approx(180.0 / 90_000)
    assert speeds["tabicl"] == pytest.approx(50.0 / 50_000)


def test_a_speed_that_is_not_positive_is_refused() -> None:
    with pytest.raises(ValueError):
        fb.walls(0.0, 0.001)
