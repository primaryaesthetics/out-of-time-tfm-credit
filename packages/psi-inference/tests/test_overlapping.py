"""Unit tests for the overlapping statistic."""

import numpy as np
import pytest

from psi_inference import overlapping_critical_value, overlapping_pvalue, overlapping_statistic


def test_overlapping_is_one_for_identical_distributions():
    q = np.array([0.2, 0.3, 0.5])
    assert overlapping_statistic(q, q) == pytest.approx(1.0)


def test_overlapping_is_zero_for_disjoint_support():
    q = np.array([1.0, 0.0])
    p = np.array([0.0, 1.0])
    assert overlapping_statistic(q, p) == pytest.approx(0.0)


def test_overlapping_worked_example_arxiv_2303_01227_section_3_6():
    # Same shift as the effect-size worked example: q = (50%, 50%),
    # P = (50.5%, 49.5%). eta = sum min(q_j, P_j) = 0.5 + 0.495 = 0.995.
    q = np.array([0.5, 0.5])
    p = np.array([0.505, 0.495])
    assert overlapping_statistic(q, p) == pytest.approx(0.995)


def test_overlapping_is_symmetric():
    q = np.array([0.1, 0.4, 0.5])
    p = np.array([0.2, 0.3, 0.5])
    assert overlapping_statistic(q, p) == pytest.approx(overlapping_statistic(p, q))


def test_overlapping_critical_value_is_below_one():
    q = np.array([0.5, 0.3, 0.2])
    crit = overlapping_critical_value(q, m=500, alpha=0.05, draws=5_000, rng=0)
    assert 0.0 < crit < 1.0


def test_overlapping_pvalue_of_no_shift_is_close_to_one():
    q = np.array([0.5, 0.3, 0.2])
    assert overlapping_pvalue(1.0, q, m=500, draws=2_000, rng=0) == pytest.approx(1.0)


def test_overlapping_pvalue_decreases_as_shift_grows():
    q = np.array([0.5, 0.5])
    small_shift = overlapping_statistic(q, np.array([0.52, 0.48]))
    large_shift = overlapping_statistic(q, np.array([0.7, 0.3]))
    p_small = overlapping_pvalue(small_shift, q, m=1_000, draws=5_000, rng=1)
    p_large = overlapping_pvalue(large_shift, q, m=1_000, draws=5_000, rng=1)
    assert p_large < p_small
