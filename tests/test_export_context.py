"""The exporter's check against the recorded classical run.

A bundle whose rows are not the rows the scorecard and the GBM scored would
come back from the node as scores that pair with nothing, so the exporter
refuses to write one. The check is on positions and outcomes, per context
seed and per cohort, and a missing cohort is a refusal too.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("pyarrow")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import export_context as ec


def recorded(path: Path, rows: np.ndarray, outcome: np.ndarray) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    cells = []
    for model, seed in (("scorecard", None), ("gbm-50k", 11), ("gbm-50k", 12)):
        for cohort in ("2015Q3", "2015Q4"):
            cells.append(pd.DataFrame({"model": model, "context_seed": seed, "cohort": cohort,
                                       "row": rows, "outcome": outcome, "pd": 0.1}))
    scores = pd.concat(cells, ignore_index=True)
    scores["context_seed"] = scores["context_seed"].astype("Int64")
    scores.to_parquet(path / "scores.parquet", index=False)
    reference = pd.concat([
        pd.DataFrame({"model": "gbm-50k", "context_seed": seed, "row": rows + 500,
                      "outcome": outcome, "pd": 0.1}) for seed in (11, 12)
    ], ignore_index=True)
    reference["context_seed"] = reference["context_seed"].astype("Int64")
    reference.to_parquet(path / "reference.parquet", index=False)
    return path


def frames(rows: np.ndarray, outcome: np.ndarray):
    context = pd.concat([pd.DataFrame({"context_seed": seed, "row": rows + 500,
                                       "outcome": outcome}) for seed in (11, 12)],
                        ignore_index=True)
    scored = pd.concat([pd.DataFrame({"cohort": cohort, "row": rows, "outcome": outcome})
                        for cohort in ("2015Q3", "2015Q4")], ignore_index=True)
    return context, scored


def test_identical_rows_pass_and_are_counted(tmp_path: Path):
    rows = np.arange(0, 100, 3)
    outcome = (rows % 7 == 0).astype(int)
    run = recorded(tmp_path / "run", rows, outcome)
    context, scored = frames(rows, outcome)
    report = ec.check_against(run, context, scored)
    assert report["context"] == {"11": {"rows": 34, "identical": True},
                                 "12": {"rows": 34, "identical": True}}
    assert set(report["cohorts"]) == {"2015Q3", "2015Q4"}


@pytest.mark.parametrize("damage", ["context_rows", "context_outcome", "cohort_rows",
                                    "cohort_outcome", "cohort_missing"])
def test_any_disagreement_stops_the_export(tmp_path: Path, damage: str):
    rows = np.arange(0, 100, 3)
    outcome = (rows % 7 == 0).astype(int)
    run = recorded(tmp_path / "run", rows, outcome)
    context, scored = frames(rows, outcome)
    if damage == "context_rows":
        context.loc[0, "row"] = 999_999
    elif damage == "context_outcome":
        context.loc[0, "outcome"] = 1 - context.loc[0, "outcome"]
    elif damage == "cohort_rows":
        scored.loc[0, "row"] = 999_999
    elif damage == "cohort_outcome":
        scored.loc[0, "outcome"] = 1 - scored.loc[0, "outcome"]
    else:
        scored = scored[scored["cohort"] == "2015Q3"]
    with pytest.raises(SystemExit, match="differ|lacks"):
        ec.check_against(run, context, scored)
