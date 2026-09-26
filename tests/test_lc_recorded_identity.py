"""The Lending Club 2015H1-E build, rebuilt now, against the run recorded before the second book.

The digest test in `test_vintage_books.py` holds the builder to its old
positions on a synthetic book. This holds it to the real one: the book is
loaded from the Lending Club file, the 2015H1-E build is assembled by the
current code, and its training rows, every cohort's rows and outcomes and the
three context samples are compared with `experiments/2026-09-05-lc-2015h1e-scores`
and the bundle exported from it. The file is 1.7 GB unpacked and not in the
repository, so the test runs where it is, under the repository root or under
`OUTOFTIME_ROOT`, and is skipped elsewhere; it takes a few minutes.
"""

from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

import numpy as np
import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("pyarrow")

REPO = Path(__file__).resolve().parent.parent
DATA_ROOT = Path(os.environ.get("OUTOFTIME_ROOT", REPO))
RAW = DATA_ROOT / "data" / "raw" / "accepted_2007_to_2018Q4.csv.gz"
RUN = REPO / "experiments" / "2026-09-05-lc-2015h1e-scores"
BUNDLE = REPO / "experiments" / "2026-09-05-lc-2015h1e-bundle"

pytestmark = pytest.mark.skipif(
    not RAW.exists() or not (RUN / "scores.parquet").exists(),
    reason="the Lending Club file is not on this machine",
)


def test_the_recorded_2015h1e_build_is_rebuilt_row_for_row():
    sys.path.insert(0, str(REPO / "scripts"))
    from score_build import load, to_dates

    from outoftime.label import LabelDefinition, build_labels
    from outoftime.lending_club import AXIS
    from outoftime.vintage import CONTEXT_SEEDS, LABEL_LAG_MONTHS, builds

    frame = load(RAW)
    origination = to_dates(frame[AXIS])
    labels = build_labels(
        origination=origination, status=list(frame["loan_status"]),
        last_payment=to_dates(frame["last_pymnt_d"]),
        definition=LabelDefinition(window_months=LABEL_LAG_MONTHS,
                                   snapshot=frame["last_pymnt_d"].max().date()))
    outcome = np.full(len(origination), -1)
    outcome[list(labels.indices)] = labels.labels
    (build,) = builds(origination, as_of_dates=(dt.date(2015, 6, 30),), arm="E", labels=labels)

    scores = pd.read_parquet(RUN / "scores.parquet",
                             columns=["model", "context_seed", "cohort", "row", "outcome"])
    reference = pd.read_parquet(RUN / "reference.parquet",
                                columns=["model", "context_seed", "row"])
    card = scores[scores["model"] == "scorecard"]
    assert np.array_equal(
        np.sort(reference[reference["model"] == "scorecard"]["row"].to_numpy()),
        np.asarray(build.train))
    assert sorted(card["cohort"].unique()) == [str(q) for q in build.test_cohorts]
    for quarter, rows in build.test:
        theirs = card[card["cohort"] == str(quarter)].sort_values("row")
        assert np.array_equal(theirs["row"].to_numpy(), np.asarray(rows)), quarter
        assert np.array_equal(theirs["outcome"].to_numpy(), outcome[list(rows)]), quarter
    control = reference[reference["model"] == "gbm-50k"]
    packed = pd.read_parquet(BUNDLE / "context.parquet", columns=["context_seed", "row"])
    for seed in CONTEXT_SEEDS:
        mine = np.asarray(build.context(seed=seed))
        assert np.array_equal(
            np.sort(control[control["context_seed"] == seed]["row"].to_numpy()), mine)
        assert np.array_equal(
            np.sort(packed[packed["context_seed"] == seed]["row"].to_numpy()), mine)
