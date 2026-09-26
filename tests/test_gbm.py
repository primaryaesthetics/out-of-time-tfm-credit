"""The GBM, tested on the two things that would make its numbers meaningless.

The first is the same property the scorecard is held to: a model fitted on a
build's rows must be identical to a model fitted on a frame holding only those
rows. Bin edges are not the risk here — LightGBM builds its histograms from the
rows it is handed — but the category list is, and so is anything a future
version might compute frame-wide.

The second is specific to a tuned model. Hyperparameters chosen against a
random fold of a book whose default rate moves would be chosen with the future
in hand, and the resulting control would flatter itself against the foundation
models. So the tests pin the early-stopping set to the end of the pool by
construction, drive the sizing rule with numbers rather than with a fitted
book, and check the rule survives the rolling arm, whose whole pool is four
quarters long.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from outoftime.gbm import DEFAULT_POLICY, GBMError, GBMPolicy, fit, validation_split
from outoftime.vintage import Quarter

SEED = 4711

# One search point, few rounds: these tests are about what the fit reads and
# where it stops, not about how well it is tuned.
FAST = GBMPolicy(
    num_leaves=(15,),
    learning_rate=(0.1,),
    min_child_samples=(20,),
    feature_fraction=(1.0,),
    max_rounds=60,
    early_stopping_rounds=10,
    min_validation_rows=100,
    n_jobs=1,
)


def book(
    n: int = 6000, seed: int = SEED, quarters: int = 8
) -> tuple[pd.DataFrame, list[int], list[dt.date]]:
    """A small book with an origination axis, risk driven by two characteristics.

    Rows are laid out in time order across `quarters` quarters starting at
    2011Q1, with volume growing quarter on quarter the way the real book does —
    which is what makes the row-share sizing rule worth testing at all.
    """
    rng = np.random.default_rng(seed)
    fico = rng.normal(690, 30, n).round()
    dti = np.clip(rng.gamma(3.0, 6.0, n), 0, 60)
    purpose = rng.choice(["car", "credit_card", "small_business"], n, p=[.4, .4, .2])
    log_odds = (
        -3.0
        - 0.035 * (fico - 690)
        + 0.03 * (dti - 18)
        + 0.8 * (purpose == "small_business")
    )
    labels = rng.binomial(1, 1.0 / (1.0 + np.exp(-log_odds))).astype(int)

    matrix = pd.DataFrame(
        {
            "fico_range_low": fico,
            "dti": dti,
            "annual_inc": rng.lognormal(11.0, 0.5, n),
            "revol_util": np.clip(100.0 - (fico - 600) / 3.0 + rng.normal(0, 1.0, n), 0, 100),
            "purpose": purpose.astype(object),
        }
    )

    weights = np.array([1.25 ** i for i in range(quarters)])
    sizes = np.maximum(1, (weights / weights.sum() * n).astype(int))
    sizes[-1] += n - sizes.sum()
    origination: list[dt.date] = []
    start = Quarter(2011, 1)
    for step, size in enumerate(sizes):
        quarter = start.shift(int(step))
        origination += [quarter.start] * int(size)
    return matrix, list(labels), origination


def counts_of(origination) -> dict[Quarter, int]:
    out: dict[Quarter, int] = {}
    for date in origination:
        quarter = Quarter.of(date)
        out[quarter] = out.get(quarter, 0) + 1
    return out


def test_the_early_stopping_set_is_the_end_of_the_pool():
    matrix, labels, origination = book()
    model = fit(matrix, labels, origination, policy=FAST)

    held = set(model.validation_quarters)
    earlier = set(model.train_quarters) - held
    assert held, "a tuned model must hold something out"
    assert earlier, "the early-stopping set may not be the whole pool"
    assert max(earlier) < min(held)
    # Contiguous, and running to the end of the pool.
    assert max(held) == max(model.train_quarters)
    assert len(held) == (max(held).year * 4 + max(held).quarter) - (
        min(held).year * 4 + min(held).quarter
    ) + 1


def test_the_sizing_rule_takes_the_fewest_latest_quarters_that_carry_the_share():
    quarters = tuple(Quarter(2011, 1).shift(i) for i in range(8))
    # A pool whose last quarter alone is a quarter of the rows.
    counts = dict(zip(quarters, [100, 100, 150, 200, 300, 400, 600, 1500]))
    policy = GBMPolicy(validation_row_share=0.20, min_validation_rows=1)
    assert validation_split(quarters, counts, policy=policy) == (quarters[-1],)

    # The same pool with a flat volume profile needs two quarters to get there.
    flat = dict.fromkeys(quarters, 1000)
    assert validation_split(quarters, flat, policy=policy) == quarters[-2:]


def test_the_sizing_rule_never_takes_more_than_half_the_pools_quarters():
    # The shape of the rolling arm: four quarters, and a last quarter too small
    # to reach the share on its own. It may still not eat the pool.
    quarters = tuple(Quarter(2012, 3).shift(i) for i in range(4))
    counts = dict(zip(quarters, [10_000, 10_000, 10_000, 100]))
    held = validation_split(quarters, counts, policy=DEFAULT_POLICY)
    assert held == quarters[-2:]
    assert len(held) <= len(quarters) // 2


def test_a_pool_spanning_one_quarter_has_no_tail_to_stop_on():
    quarters = (Quarter(2013, 2),)
    with pytest.raises(GBMError):
        validation_split(quarters, {quarters[0]: 5000}, policy=DEFAULT_POLICY)


def test_a_fit_reads_only_the_rows_it_was_given():
    matrix, labels, origination = book()
    rows = list(range(3000))

    # Everything outside the window is replaced by a book from another planet:
    # different location, a category that never appears in the window, the
    # opposite label, and dates that would change the pool's quarters.
    other = matrix.copy()
    other.loc[3000:, "fico_range_low"] = 400.0
    other.loc[3000:, "dti"] = 90.0
    other.loc[3000:, "purpose"] = "wedding"
    other_labels = [1 - v if i >= 3000 else v for i, v in enumerate(labels)]
    other_dates = [dt.date(2001, 1, 1) if i >= 3000 else d for i, d in enumerate(origination)]

    on_window = fit(
        matrix.iloc[rows].reset_index(drop=True),
        labels[:3000],
        origination[:3000],
        policy=FAST,
    )
    in_place = fit(other, other_labels, other_dates, rows=rows, policy=FAST)

    assert on_window.validation_quarters == in_place.validation_quarters
    assert on_window.categories == in_place.categories
    assert on_window.rounds == in_place.rounds
    assert on_window.validation_logloss == pytest.approx(in_place.validation_logloss)

    scored = list(range(500))
    assert on_window.predict_pd(matrix, rows=scored) == pytest.approx(
        in_place.predict_pd(matrix, rows=scored)
    )


def test_the_same_rows_twice_give_the_same_model_and_a_fit_disturbs_no_other():
    matrix, labels, origination = book()
    rows = list(range(4000))
    scored = list(range(4000, 4100))

    first = fit(matrix, labels, origination, rows=rows, policy=FAST)
    before = first.predict_pd(matrix, rows=scored)
    second = fit(matrix, labels, origination, rows=list(range(1000, 5000)), policy=FAST)
    again = fit(matrix, labels, origination, rows=rows, policy=FAST)

    assert first.params == again.params
    assert first.rounds == again.rounds
    assert first.predict_pd(matrix, rows=scored) == pytest.approx(before)
    assert again.predict_pd(matrix, rows=scored) == pytest.approx(before)
    assert second.train_rows == 4000


def test_a_category_the_pool_never_held_is_scored_as_unseen():
    matrix, labels, origination = book()
    rows = [i for i, value in enumerate(matrix["purpose"]) if value != "small_business"]
    model = fit(matrix, labels, origination, rows=rows, policy=FAST)

    assert "small_business" not in model.categories["purpose"]
    unseen = [i for i, value in enumerate(matrix["purpose"]) if value == "small_business"]
    predicted = model.predict_pd(matrix, rows=unseen[:200])
    assert np.isfinite(predicted).all()
    assert ((predicted > 0.0) & (predicted < 1.0)).all()


def test_the_shipped_model_saw_every_row_of_the_pool():
    matrix, labels, origination = book()
    model = fit(matrix, labels, origination, policy=FAST)

    assert model.train_rows == len(matrix)
    assert model.validation_rows == sum(
        count
        for quarter, count in counts_of(origination).items()
        if quarter in model.validation_quarters
    )
    assert 0 < model.fit_rows < model.train_rows
    assert model.model.num_trees() == model.rounds


def test_rows_without_a_label_or_a_date_are_refused():
    matrix, labels, origination = book(n=2000, quarters=4)

    unlabelled = list(labels)
    unlabelled[7] = None
    with pytest.raises(GBMError):
        fit(matrix, unlabelled, origination, policy=FAST)

    undated = list(origination)
    undated[7] = None
    with pytest.raises(GBMError):
        fit(matrix, labels, undated, policy=FAST)


def test_one_class_on_the_training_rows_is_refused():
    matrix, labels, origination = book(n=2000, quarters=4)
    good = [i for i, value in enumerate(labels) if value == 0][:500]
    with pytest.raises(GBMError):
        fit(matrix, labels, origination, rows=good, policy=FAST)


def test_the_search_grid_is_fixed_and_ordered():
    grid = DEFAULT_POLICY.grid()
    assert len(grid) == 36
    assert grid == DEFAULT_POLICY.grid()
    assert grid[0]["num_leaves"] <= grid[-1]["num_leaves"]
    assert len({tuple(sorted(point.items())) for point in grid}) == len(grid)


def test_a_policy_that_holds_out_most_of_the_pool_is_refused():
    with pytest.raises(GBMError):
        GBMPolicy(validation_row_share=0.8)
    with pytest.raises(GBMError):
        GBMPolicy(num_leaves=())


def test_it_learns_the_books_signal():
    matrix, labels, origination = book()
    rows = list(range(4500))
    model = fit(matrix, labels, origination, rows=rows, policy=FAST)

    scored = list(range(4500, 6000))
    predicted = model.predict_pd(matrix, rows=scored)
    outcome = np.asarray([labels[i] for i in scored])
    order = np.argsort(predicted)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(order) + 1)
    positives, negatives = outcome.sum(), (1 - outcome).sum()
    auc = (ranks[outcome == 1].sum() - positives * (positives + 1) / 2) / (positives * negatives)
    assert auc > 0.65


def test_a_fixed_point_skips_the_search_and_chooses_only_the_rounds():
    matrix, labels, origination = book()
    wide = GBMPolicy(
        num_leaves=(7, 15, 31),
        learning_rate=(0.1,),
        min_child_samples=(20, 50),
        feature_fraction=(1.0,),
        max_rounds=60,
        early_stopping_rounds=10,
        min_validation_rows=100,
        n_jobs=1,
    )
    searched = fit(matrix, labels, origination, policy=wide)
    assert len(searched.trials) == 6
    # An edge is reported only on a knob with an interior, and only when the
    # winner sits at one of its ends; the two-level knob never qualifies.
    on_edge = any(note.startswith("the chosen point sits on the grid's edge") for note in searched.notes)
    assert on_edge == (searched.params["num_leaves"] in (7, 31))
    assert not any("min_child_samples" in note for note in searched.notes)
    assert any(note.startswith("chosen over the runner-up") for note in searched.notes)

    point = {knob: searched.params[knob] for knob in wide.grid()[0]}
    fixed = fit(matrix, labels, origination, policy=wide, point=point)
    assert len(fixed.trials) == 1
    assert fixed.trials[0].params == point
    assert fixed.rounds == searched.rounds
    assert not any("grid's edge" in note for note in fixed.notes)

    with pytest.raises(GBMError, match="searched knobs"):
        fit(matrix, labels, origination, policy=wide, point={"max_depth": 3})


def test_a_random_validation_set_and_the_auc_objective_replace_the_tail_when_given():
    matrix, labels, origination = book()
    rng = np.random.default_rng(SEED)
    fifth = sorted(rng.choice(len(labels), size=len(labels) // 5, replace=False).tolist())
    wide = GBMPolicy(
        num_leaves=(7, 31),
        learning_rate=(0.1,),
        min_child_samples=(20,),
        feature_fraction=(1.0,),
        max_rounds=60,
        early_stopping_rounds=10,
        min_validation_rows=100,
        n_jobs=1,
    )
    model = fit(matrix, labels, origination, policy=wide, validation_rows=fifth, objective="auc")
    assert model.validation_rows == len(fifth)
    assert model.validation_quarters == ()
    assert model.fit_rows == len(labels) - len(fifth)
    assert model.objective == "auc"
    assert any("named by the caller" in note for note in model.notes)
    assert any("validation AUC" in note for note in model.notes)
    assert all(trial.validation_auc is not None for trial in model.trials)
    assert model.validation_auc == max(trial.validation_auc for trial in model.trials)
    assert model.as_dict()["validation_auc"] == pytest.approx(model.validation_auc, abs=1e-8)
    # The same rows under the study's own recipe carry no AUC and stop on the tail.
    study = fit(matrix, labels, origination, policy=wide)
    assert study.objective == "logloss" and study.validation_auc is None
    assert study.validation_quarters != ()
    assert all(trial.validation_auc is None for trial in study.trials)
    assert "validation_auc" not in study.trials[0].as_dict()

    # Without the refit the shipped model is the tuning fit: scores on the
    # validation rows differ from the refitted model's, and the account says so.
    kept = fit(matrix, labels, origination, policy=wide, validation_rows=fifth, objective="auc",
               refit=False)
    assert not kept.refitted and model.refitted
    assert any("not refitted" in note for note in kept.notes)
    assert kept.rounds == model.rounds and kept.params == model.params
    assert not np.allclose(kept.predict_pd(matrix, rows=fifth), model.predict_pd(matrix, rows=fifth))

    with pytest.raises(GBMError, match="subset"):
        fit(matrix, labels, origination, policy=wide, validation_rows=[len(labels) + 5])
    with pytest.raises(GBMError, match="objective"):
        fit(matrix, labels, origination, policy=wide, objective="brier")
    with pytest.raises(GBMError, match="nothing to fit"):
        fit(matrix, labels, origination, policy=wide, validation_rows=list(range(len(labels))))


def test_a_search_point_scores_the_same_alone_as_inside_a_grid():
    # A column too sparse for the larger leaf size: LightGBM's dataset-time
    # pre-filter would drop its bins under one leaf size and keep them under
    # another, and a dataset built once for the first grid point would then
    # score every later point on the first point's bins.
    matrix, labels, origination = book()
    matrix = matrix.copy()
    matrix["pub_rec"] = 0.0
    matrix.loc[matrix.index[::60], "pub_rec"] = 1.0
    base = {
        "num_leaves": (15,), "learning_rate": (0.1,), "feature_fraction": (1.0,),
        "max_rounds": 200, "early_stopping_rounds": 20, "min_validation_rows": 100, "n_jobs": 1,
    }
    in_grid = fit(matrix, labels, origination, policy=GBMPolicy(min_child_samples=(20, 200), **base))
    alone = fit(matrix, labels, origination, policy=GBMPolicy(min_child_samples=(200,), **base))
    grid_trial = next(t for t in in_grid.trials if t.params["min_child_samples"] == 200)
    alone_trial = alone.trials[0]
    assert grid_trial.rounds == alone_trial.rounds
    assert grid_trial.validation_logloss == pytest.approx(alone_trial.validation_logloss, abs=1e-12)
