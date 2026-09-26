"""Unit tests for the shared parametric-bootstrap null (arXiv:2303.01227, section 3.1)."""

import numpy as np
import pytest

from psi_inference.bootstrap import bootstrap_critical_value, bootstrap_null, bootstrap_pvalue


def _l1_distance(reference: np.ndarray, sample: np.ndarray) -> float:
    return float(np.abs(reference - sample).sum())


def test_bootstrap_null_has_the_requested_number_of_draws():
    reference = np.array([0.5, 0.3, 0.2])
    null = bootstrap_null(reference, m=200, statistic=_l1_distance, draws=500, rng=0)
    assert null.shape == (500,)


def test_bootstrap_null_is_reproducible_with_a_seed():
    reference = np.array([0.5, 0.5])
    a = bootstrap_null(reference, m=100, statistic=_l1_distance, draws=200, rng=42)
    b = bootstrap_null(reference, m=100, statistic=_l1_distance, draws=200, rng=42)
    assert np.array_equal(a, b)


def test_bootstrap_critical_value_is_the_requested_order_statistic():
    reference = np.array([0.5, 0.5])
    draws = 1000
    null = bootstrap_null(reference, m=300, statistic=_l1_distance, draws=draws, rng=1)
    alpha = 0.05
    expected = np.sort(null)[int(np.floor(draws * (1 - alpha)))]
    crit = bootstrap_critical_value(reference, m=300, statistic=_l1_distance, alpha=alpha, draws=draws, rng=1)
    assert crit == pytest.approx(expected)


def test_bootstrap_pvalue_of_a_value_beyond_the_null_is_small():
    reference = np.array([0.9, 0.1])
    p = bootstrap_pvalue(2.0, reference, m=200, statistic=_l1_distance, draws=2_000, rng=0)
    assert p == pytest.approx(0.0, abs=1e-9)


def test_bootstrap_pvalue_of_zero_discrepancy_is_close_to_one():
    reference = np.array([0.5, 0.5])
    p = bootstrap_pvalue(0.0, reference, m=200, statistic=_l1_distance, draws=2_000, rng=0)
    assert p == pytest.approx(1.0, abs=1e-9)


def test_bootstrap_rejects_nonpositive_alpha():
    reference = np.array([0.5, 0.5])
    with pytest.raises(ValueError):
        bootstrap_critical_value(reference, m=100, statistic=_l1_distance, alpha=0.0)
