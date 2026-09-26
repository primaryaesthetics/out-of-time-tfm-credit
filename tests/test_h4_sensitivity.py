"""The H4 sensitivity points: the criterion's arithmetic and the fit replacement."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import h4_sensitivity as hs


def _cells() -> pd.DataFrame:
    rows = []
    for cohort in ("c1", "c2"):
        for draw, control_e in (("1", 0.9), ("2", 0.3), ("3", 0.1)):
            rows.append({"build_date": "b", "cohort": cohort, "model": "gbm-50k", "draw": draw,
                         "deviation_E": control_e, "deviation_R": 0.2})
            rows.append({"build_date": "b", "cohort": cohort, "model": "tabpfn", "draw": draw,
                         "deviation_E": 0.25, "deviation_R": 0.2})
    return pd.DataFrame(rows)


def test_h4_is_the_foundation_models_reduction_less_the_controls():
    cells = _cells()
    # control E - R: mean(0.7, 0.1, -0.1) = 0.2333; tabpfn: 0.05
    assert hs.h4(cells)["tabpfn"] == pytest.approx(0.05 - 0.7 / 3)


def test_replacing_a_fit_uses_the_mean_of_the_other_draws_on_the_same_cells():
    out = hs.replaced(_cells(), "b", "E", "1")
    control = out[out["model"] == "gbm-50k"]
    assert control.loc[control["draw"] == "1", "deviation_E"].tolist() == pytest.approx([0.2, 0.2])
    assert control.loc[control["draw"] != "1", "deviation_E"].tolist() == [0.3, 0.1, 0.3, 0.1]
    assert out["deviation_R"].eq(0.2).all()
    # control E - R now mean(0.0, 0.1, -0.1) = 0
    assert hs.h4(out)["tabpfn"] == pytest.approx(0.05)
