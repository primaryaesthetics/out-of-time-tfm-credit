"""The scorecard, tested on what it must not read and what it must not keep.

The property that carries the whole study is the first one below: a scorecard
fitted on a build's rows must be identical to a scorecard fitted on a frame
that contains only those rows. If it is not, then something in the pipeline —
a bin edge, an information value, a category list — was computed on rows the
model builder did not have, and every out-of-time number downstream is a number
about a model nobody could have built.

The rest are the properties a credit reviewer would check by hand: that a
characteristic with no predictive power is screened out, that the card does not
exceed the size it is allowed, that every coefficient carries the sign the
weight-of-evidence convention requires, and that the same rows twice give the
same card.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from outoftime.scorecard import ScorecardError, ScorecardPolicy, fit

SEED = 4711
FAST = ScorecardPolicy(n_jobs=1)


def book(n: int = 6000, seed: int = SEED) -> tuple[pd.DataFrame, list[int]]:
    """A small book whose risk is driven by two of its five characteristics.

    `fico_range_low` and `dti` carry the signal, monotonically in opposite
    directions. `annual_inc` is noise, `purpose` is a categorical with one
    risky level, and `revol_util` is a copy of the fico signal with its sign
    reversed, which is what a wrong-signed coefficient is made of.
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
    probability = 1.0 / (1.0 + np.exp(-log_odds))
    labels = rng.binomial(1, probability).astype(int)

    matrix = pd.DataFrame(
        {
            "fico_range_low": fico,
            "dti": dti,
            "annual_inc": rng.lognormal(11.0, 0.5, n),
            "revol_util": 100.0 - (fico - 600) / 3.0 + rng.normal(0, 1.0, n),
            "purpose": purpose.astype(object),
        }
    )
    return matrix, list(labels)


def test_a_fit_reads_only_the_rows_it_was_given():
    matrix, labels = book()
    rows = list(range(2000))

    # The rows outside the window are replaced by a book from another planet:
    # different location, different spread, a category that never appears in
    # the window, and the opposite label pattern. Nothing about the fitted card
    # may move.
    other = matrix.copy()
    other.loc[2000:, "fico_range_low"] = 400.0
    other.loc[2000:, "dti"] = 90.0
    other.loc[2000:, "purpose"] = "wedding"
    other_labels = list(labels)
    for i in range(2000, len(matrix)):
        other_labels[i] = 1 - labels[i]

    on_window = fit(matrix.iloc[rows].reset_index(drop=True), labels[:2000], policy=FAST)
    in_place = fit(other, other_labels, rows=rows, policy=FAST)

    assert on_window.names == in_place.names
    assert on_window.coefficients == pytest.approx(in_place.coefficients)
    assert on_window.intercept == pytest.approx(in_place.intercept)
    assert on_window.bin_tables() == in_place.bin_tables()


def test_the_same_rows_twice_give_the_same_card_and_a_fit_disturbs_no_other():
    matrix, labels = book()
    first = fit(matrix, labels, rows=list(range(3000)), policy=FAST)
    before = first.predict_pd(matrix, rows=list(range(3000, 3100)))

    fit(matrix, labels, rows=list(range(3000, 6000)), policy=FAST)
    again = fit(matrix, labels, rows=list(range(3000)), policy=FAST)

    assert again.coefficients == pytest.approx(first.coefficients)
    assert again.intercept == pytest.approx(first.intercept)
    assert first.predict_pd(matrix, rows=list(range(3000, 3100))) == pytest.approx(before)


def test_every_coefficient_carries_the_weight_of_evidence_sign():
    matrix, labels = book()
    card = fit(matrix, labels, policy=FAST)
    # WOE is ln(%non-event / %event): a high-WOE bin is a safe bin, so in a
    # model of the event every coefficient is negative.
    assert card.characteristics
    assert all(c.coefficient < 0 for c in card.characteristics), card.coefficients


def test_a_wrong_signed_characteristic_is_dropped_and_recorded():
    matrix, labels = book()
    kept = fit(matrix, labels, policy=FAST)
    unscreened = fit(matrix, labels, policy=ScorecardPolicy(drop_wrong_sign=False, n_jobs=1))

    if any(c.coefficient > 0 for c in unscreened.characteristics):
        assert kept.dropped_wrong_sign
        assert set(kept.dropped_wrong_sign).isdisjoint(kept.names)
    else:
        assert kept.dropped_wrong_sign == ()


def test_a_characteristic_with_no_power_is_screened_out():
    matrix, labels = book()
    card = fit(matrix, labels, policy=FAST)
    assert "annual_inc" not in card.names
    assert "annual_inc" in card.screened_out
    assert "fico_range_low" in card.names
    ivs = dict(card.iv_all)
    assert ivs["annual_inc"] < card.policy.iv_min < ivs["fico_range_low"]


def test_the_card_does_not_exceed_the_size_it_is_allowed():
    matrix, labels = book()
    card = fit(matrix, labels, policy=ScorecardPolicy(max_characteristics=2, n_jobs=1))
    assert len(card.characteristics) <= 2


def test_predictions_rank_the_book_and_points_run_the_other_way():
    matrix, labels = book()
    rows = list(range(4000))
    card = fit(matrix, labels, rows=rows, policy=FAST)

    held_out = list(range(4000, 6000))
    probability = card.predict_pd(matrix, rows=held_out)
    points = card.points(matrix, rows=held_out)
    outcome = np.asarray([labels[i] for i in held_out])

    assert probability.shape == (len(held_out),)
    assert ((probability > 0) & (probability < 1)).all()
    assert probability[outcome == 1].mean() > probability[outcome == 0].mean()
    # Points are an affine function of the log-odds of *not* defaulting, so
    # they must reverse the probability exactly.
    assert np.corrcoef(points, np.log(probability / (1 - probability)))[0, 1] < -0.999

    both = card.predict_proba(matrix, rows=held_out)
    assert both.shape == (len(held_out), 2)
    assert both[:, 1] == pytest.approx(probability)


def test_an_unlabelled_row_is_refused_rather_than_counted_as_good():
    matrix, labels = book(n=2000)
    labels[7] = None
    with pytest.raises(ScorecardError, match="no label"):
        fit(matrix, labels, policy=FAST)


def test_one_class_and_no_rows_are_refused():
    matrix, labels = book(n=2000)
    with pytest.raises(ScorecardError, match="one class"):
        fit(matrix, [0] * len(labels), policy=FAST)
    with pytest.raises(ScorecardError, match="no training rows"):
        fit(matrix, labels, rows=[], policy=FAST)


def test_a_non_monotonic_trend_is_not_a_policy_this_study_admits():
    with pytest.raises(ScorecardError, match="monotonic"):
        ScorecardPolicy(monotonic_trend="peak")


def test_a_category_never_seen_in_training_scores_neutrally():
    matrix, labels = book()
    rows = [i for i in range(4000) if matrix["purpose"][i] != "small_business"]
    # The risky level is what gives `purpose` its information value, so with it
    # withheld the characteristic is admitted on a policy that screens nothing;
    # the question here is what the card does with a category it never saw, not
    # whether this one earns its place.
    card = fit(
        matrix,
        labels,
        rows=rows,
        policy=ScorecardPolicy(iv_min=0.0, drop_wrong_sign=False, n_jobs=1),
    )
    assert "purpose" in card.names

    unseen = [i for i in range(4000, 6000) if matrix["purpose"][i] == "small_business"]
    woe = card.transform(matrix, rows=unseen)
    assert (woe["purpose"] == 0.0).all()


def test_bin_tables_hold_bins_and_name_categories_by_their_members():
    matrix, labels = book()
    card = fit(matrix, labels, policy=ScorecardPolicy(iv_min=0.0, n_jobs=1))
    rows = card.bin_tables()
    assert rows
    assert all(row["bin"] not in ("", "Totals") for row in rows)
    assert not any("Array" in row["bin"] for row in rows)
    purpose_bins = [row["bin"] for row in rows if row["characteristic"] == "purpose"]
    assert any("small_business" in label for label in purpose_bins)
    # Every characteristic's bin shares sum to one, which a totals row would break.
    for name in card.names:
        share = sum(row["count_share"] for row in rows if row["characteristic"] == name)
        assert share == pytest.approx(1.0, abs=1e-4)
