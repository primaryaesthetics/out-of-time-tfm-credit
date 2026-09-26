"""Unit tests for the Population Resemblance Statistic."""

import numpy as np
import pytest

from psi_inference import (
    PRSThresholds,
    prs_classify,
    prs_delta,
    prs_noncentrality_sup,
    prs_statistic,
    prs_thresholds,
)


def test_prs_zero_when_sample_matches_reference():
    p0 = np.array([0.2, 0.2, 0.2, 0.2, 0.2])
    assert prs_statistic(p0, p0) == pytest.approx(0.0, abs=1e-12)


def test_prs_rejects_nonpositive_reference_probability():
    with pytest.raises(ValueError):
        prs_statistic(np.array([0.5, 0.0, 0.5]), np.array([0.4, 0.2, 0.4]))


def test_prs_delta_matches_arxiv_2307_11878_eq5():
    p0 = np.array([0.5, 0.5])
    # eq. 5: delta = c * min_j sqrt(p0_j (1 - p0_j) / n)
    expected = 0.7 * np.sqrt(0.5 * 0.5 / 200)
    assert prs_delta(p0, n=200, c=0.7) == pytest.approx(expected)


@pytest.mark.parametrize(
    "n,bins,expected_delta,expected_lower,expected_upper",
    [
        # arXiv:2307.11878, Table 2 (c, M) = (0.7, 2), (alpha1, alpha2) = (5%, 10%),
        # equi-probable p0 with B categories.
        (50, 5, 0.039598, 0.07441, 0.25722),
        (500, 10, 0.009391, 0.03063, 0.04890),
        (2_000, 10, 0.004696, 0.00766, 0.01222),
        (10_000, 20, 0.001526, 0.00394, 0.00439),
    ],
)
def test_prs_thresholds_match_arxiv_2307_11878_table_2(
    n, bins, expected_delta, expected_lower, expected_upper
):
    p0 = np.full(bins, 1.0 / bins)
    th = prs_thresholds(p0, n, c=0.7, multiplier=2.0, alpha1=0.05, alpha2=0.10)
    assert th.delta == pytest.approx(expected_delta, abs=2e-6)
    assert th.lower == pytest.approx(expected_lower, abs=2e-5)
    assert th.upper == pytest.approx(expected_upper, abs=2e-5)


def test_prs_noncentrality_sup_even_b_has_no_correction_term():
    p0 = np.array([0.25, 0.25, 0.25, 0.25])
    n, delta = 400, 0.01
    expected = n * delta**2 * np.sum(1.0 / p0)
    assert prs_noncentrality_sup(p0, delta, n) == pytest.approx(expected)


def test_prs_noncentrality_sup_odd_b_subtracts_the_largest_category():
    p0 = np.array([0.5, 0.3, 0.2])
    n, delta = 400, 0.01
    expected = n * delta**2 * (np.sum(1.0 / p0) - 1.0 / p0.max())
    assert prs_noncentrality_sup(p0, delta, n) == pytest.approx(expected)


def test_prs_thresholds_reject_delta_beyond_min_probability():
    p0 = np.array([0.05, 0.95])
    with pytest.raises(ValueError):
        prs_thresholds(p0, n=50, delta=0.1)


def test_prs_classify_boundaries():
    thresholds = PRSThresholds(delta=0.01, lower=0.05, upper=0.20)
    assert prs_classify(0.01, thresholds) == "acceptable"
    assert prs_classify(0.05, thresholds) == "acceptable"
    assert prs_classify(0.10, thresholds) == "partial"
    assert prs_classify(0.20, thresholds) == "partial"
    assert prs_classify(0.21, thresholds) == "full"


def test_prs_thresholds_lower_is_below_upper():
    p0 = np.full(10, 0.1)
    th = prs_thresholds(p0, n=1_000)
    assert th.lower < th.upper
