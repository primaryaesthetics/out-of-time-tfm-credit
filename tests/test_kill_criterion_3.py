"""Kill criterion 3 on constructed AUC tables where the answer is known."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import kill_criterion_3 as kc


def _cells(values: dict[tuple[str, int | None], list[float]], width: float, floors=None) -> pd.DataFrame:
    rows = []
    for (model, seed), aucs in values.items():
        for k, auc in enumerate(aucs):
            rows.append({"build_id": "2010H2-E", "arm": "E", "model": model, "context_seed": seed,
                         "cohort": f"c{k}", "value": auc, "ci_lo": auc - width / 2,
                         "ci_hi": auc + width / 2, "width": width,
                         "floor": True if floors is None else floors[k]})
    return pd.DataFrame(rows)


def test_lc_draws_that_move_more_than_cohorts_are_read_as_such():
    # Cohorts step by 0.01; draws spread by 0.05.
    base = [0.70, 0.71, 0.72, 0.73]
    cells = _cells({("tabpfn", 1): base, ("tabpfn", 2): [v + 0.05 for v in base],
                    ("tabpfn", 3): [v - 0.00 for v in base], ("scorecard", None): base}, 0.02)
    (row,) = kc.lc_rows(cells)
    assert row["model"] == "tabpfn"
    assert abs(row["between_draws"] - 0.05) < 1e-12
    assert abs(row["between_adjacent_cohorts"] - 0.01) < 1e-12
    assert row["draws_move_more"]


def test_fm_width_against_range_on_criterion_cells_only():
    # Criterion cells span 0.02 of AUC; widths 0.05 -> wider. A cell under the floors at 0.9
    # would widen the range past the width if it were read.
    cells = _cells({("gbm", None): [0.70, 0.71, 0.72, 0.90]}, 0.05, floors=[True, True, True, False])
    (row,) = kc.fm_rows(cells)
    assert row["criterion_cells"] == 3
    assert abs(row["auc_range"] - 0.02) < 1e-12
    assert row["wider_by_median_width"] and row["wider_by_median_auc_cell"]


def test_fm_fires_only_when_every_model_is_wider_on_a_majority_of_builds():
    table = pd.DataFrame([
        {"build_id": b, "model": m, "wider_by_median_width": w}
        for b, pattern in (("b1", (True, True)), ("b2", (True, False)), ("b3", (True, True)))
        for m, w in zip(("gbm", "tabpfn"), pattern, strict=True)])
    _, count, fires = kc.fm_verdict(table, "wider_by_median_width")
    assert count == 2 and fires
