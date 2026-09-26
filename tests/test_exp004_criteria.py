"""EXP-004's criteria on a synthetic table whose verdicts are known by construction."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("matplotlib")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import exp004_criteria as ec

MODELS = ec.FIVE + ec.AT_ONE
DRAWN = {"gbm-50k", "tabpfn", "tabicl", "tabpfn@t1", "tabicl@t1"}
# In time and out of time: Gini, |log O/E|, Brier, log-loss.
IN = {"scorecard": (0.37, 0.036, 0.02280, 0.1066), "gbm": (0.40, 0.038, 0.02270, 0.1057),
      "gbm-50k": (0.37, 0.033, 0.02281, 0.1067), "tabpfn": (0.40, 0.38, 0.02285, 0.1073),
      "tabicl": (0.39, 0.31, 0.02283, 0.1071), "tabpfn@t1": (0.40, 0.03, 0.0227, 0.1057),
      "tabicl@t1": (0.39, 0.05, 0.0227, 0.1059)}
OUT = {"scorecard": (0.40, 0.40, 0.02990, 0.1335), "gbm": (0.42, 0.35, 0.02980, 0.1319),
       "gbm-50k": (0.41, 0.37, 0.02985, 0.1331), "tabpfn": (0.42, 0.76, 0.03000, 0.1375),
       "tabicl": (0.43, 0.63, 0.02995, 0.1352), "tabpfn@t1": (0.42, 0.38, 0.0298, 0.1322),
       "tabicl@t1": (0.43, 0.26, 0.0297, 0.1309)}


def build(tmp: Path, star_tabicl_gbm: bool = True, share: float = 0.05):
    rows, table = [], []
    for model in MODELS:
        g, lo, br, ll = IN[model]
        for fold in range(1, 6):
            for seed in ((1, 2, 3) if model in DRAWN else (None,)):
                jitter = 0.002 * (fold - 3)
                rows.append({"protocol": ec.IN_TIME, "model": model, "context_seed": seed,
                             "unit": f"fold {fold}", "gini": g + jitter, "abs_log_oe": lo + jitter,
                             "brier": br, "log_loss": ll, "predicted_positive_share": share})
        for protocol, (g2, lo2, br2, ll2) in ((ec.IN_TIME, IN[model]), (ec.OUT_OF_TIME, OUT[model])):
            table.append({"protocol": protocol, "model": model, "gini_mean": g2,
                          "abs_log_oe_mean": lo2, "brier_mean": br2, "log_loss_mean": ll2})
    paired = []
    names = list(MODELS)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for metric, k in (("gini", 0), ("abs_log_oe", 1)):
                v = OUT[b][k] - OUT[a][k]
                starred = abs(v) > 0.005 and not (metric == "gini" and {a, b} == {"gbm", "tabicl"}
                                                  and not star_tabicl_gbm)
                paired.append({"cohorts": "all", "draw": None, "metric": metric,
                               "pair": f"{b} - {a}", "is_difference": True, "value": v,
                               "ci_lo": v - 0.004, "ci_hi": v + 0.004, "seed": ec.SEED,
                               "excludes_zero": starred})
    t, p = tmp / "table", tmp / "pooling"
    t.mkdir(parents=True)
    p.mkdir()
    pd.DataFrame(rows).to_csv(t / "cells.csv", index=False)
    pd.DataFrame(table).to_csv(t / "table.csv", index=False)
    pd.DataFrame(paired).to_csv(p / "paired.csv", index=False)
    return t, p


def run(tmp: Path, **kw) -> dict:
    t, p = build(tmp, **kw)
    assert ec.main([str(t), "--pooling", str(p), "--out-dir", str(tmp / "out")]) == 0
    return json.loads((tmp / "out" / "criteria.json").read_text(encoding="utf-8"))


def test_a_starred_pair_whose_sign_flips_in_time_keeps_criterion_1_from_firing(tmp_path):
    result = run(tmp_path)
    row = {r["pair"]: r for r in result["criterion_1"]["starred_pairs"]}["tabicl - gbm"]
    assert row["out_of_time"] > 0 and row["in_time"] < 0 and not row["same_sign"]
    assert not result["criterion_1"]["fires"]


def test_the_in_time_difference_pairs_drawn_models_on_their_draw(tmp_path):
    t, _ = build(tmp_path)
    cells = pd.read_csv(t / "cells.csv")
    d = ec.in_time_difference(cells, "tabicl", "gbm-50k", "gini")
    assert d["units"] == 15 and d["point"] == pytest.approx(0.02)
    d = ec.in_time_difference(cells, "tabicl", "gbm", "gini")
    assert d["units"] == 15 and d["lo"] == pytest.approx(-0.01)


def test_orders_that_differ_in_time_keep_criterion_2_from_firing(tmp_path):
    result = run(tmp_path)
    assert result["criterion_2"]["agrees_with_abs_log_oe"][ec.OUT_OF_TIME]["log_loss"]
    assert not result["criterion_2"]["agrees_with_abs_log_oe"][ec.IN_TIME]["brier"]
    assert not result["criterion_2"]["fires"]


def test_a_threshold_that_selects_almost_nothing_fires_criterion_3(tmp_path):
    assert not run(tmp_path)["criterion_3"]["fires"]
    assert run(tmp_path / "low", share=0.005)["criterion_3"]["fires"]


def test_the_branch_kill_reads_both_inclusions(tmp_path):
    result = run(tmp_path)
    level = [r for r in result["branch_kill"]["rows"] if r["metric"] == "abs_log_oe"]
    assert {r["pair"] for r in level} == {"tabpfn - gbm", "tabicl - gbm"}
    assert not result["branch_kill"]["fires"]
