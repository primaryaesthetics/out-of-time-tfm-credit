"""The protocol table, on a Cox fit that does not finish.

Such a cell is not estimable: the table must not read its slope as a number,
nor let one NaN cohort turn a model's mean over cohorts into NaN.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("pandas")
pytest.importorskip("matplotlib")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import protocol_table as pt

from outoftime import metrics as mt


def cell(seed: int, n: int = 2_000):
    rng = np.random.default_rng(seed)
    y = rng.binomial(1, 0.1, n)
    s = np.clip(0.1 + 0.1 * (y - 0.1) + rng.normal(0, 0.04, n), 0.005, 0.8)
    return y, s, rng.uniform(0.005, 0.8, 3 * n)


def test_a_cox_fit_that_does_not_finish_is_not_read_as_a_number(monkeypatch):
    y, s, reference = cell(1)
    values, fit = pt.cell_metrics(y, s, 0.12, reference)
    assert fit.converged and values["cox_slope"] == fit.slope

    def unfinished(outcome, score, **kw):
        nan = float("nan")
        return mt.Cox(nan, nan, nan, nan, False, mt.ALPHA, 100)

    monkeypatch.setattr(pt.mt, "cox", unfinished)
    values, fit = pt.cell_metrics(y, s, 0.12, reference)
    assert not fit.converged and fit.iterations == 100
    assert np.isnan(values["cox_slope"]) and np.isfinite(values["auc"])


def test_a_cohort_not_estimable_leaves_the_cox_mean_and_only_that_one():
    cohorts = []
    for seed in (1, 2, 3):
        y, s, reference = cell(seed)
        values, _ = pt.cell_metrics(y, s, 0.12, reference)
        cohorts.append(values)
    whole, left = pt.mean_over_cohorts(cohorts)
    assert left == 0
    assert whole["cox_slope"] == float(np.mean([c["cox_slope"] for c in cohorts]))
    cohorts[1] = {**cohorts[1], "cox_slope": float("nan")}
    mean, left = pt.mean_over_cohorts(cohorts)
    assert left == 1
    assert mean["cox_slope"] == pytest.approx(np.mean([cohorts[0]["cox_slope"],
                                                       cohorts[2]["cox_slope"]]))
    assert mean["auc"] == whole["auc"] and mean["brier"] == whole["brier"]
