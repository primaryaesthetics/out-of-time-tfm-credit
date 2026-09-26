"""Unit tests for the PSI statistic and its asymptotic null."""

import numpy as np
import pytest
from scipy import stats

from psi_inference import psi_critical_value, psi_pvalue, psi_scale, psi_statistic, psi_test


def test_psi_zero_when_proportions_match():
    a = np.array([10, 20, 30, 40])
    b = np.array([5, 10, 15, 20])
    assert psi_statistic(a, b) == pytest.approx(0.0, abs=1e-12)


def test_psi_worked_example_yurdakul_table_1():
    # Yurdakul & Naranjo (2020), Table 1: seven credit grades, base and target
    # proportions given to three decimals. The paper reports PSI = 0.068.
    a = np.array([253, 302, 204, 134, 72, 26, 8])
    b = np.array([177, 262, 285, 158, 88, 25, 6])
    assert psi_statistic(a, b) == pytest.approx(0.068, abs=5e-4)


def test_psi_symmetric_in_its_two_arguments():
    a = np.array([40, 30, 20, 10])
    b = np.array([25, 25, 25, 25])
    assert psi_statistic(a, b) == pytest.approx(psi_statistic(b, a))


def test_psi_rejects_mismatched_bin_counts():
    with pytest.raises(ValueError):
        psi_statistic(np.array([1, 2, 3]), np.array([1, 2]))


def test_psi_rejects_zero_count_bin():
    with pytest.raises(ValueError):
        psi_statistic(np.array([10, 0, 5]), np.array([5, 5, 5]))


def test_psi_scale_matches_yurdakul_formula():
    assert psi_scale(100, 200) == pytest.approx(1 / 100 + 1 / 200)


def test_psi_scale_rejects_nonpositive_sample_size():
    with pytest.raises(ValueError):
        psi_scale(0, 100)


@pytest.mark.parametrize(
    "n,m,bins,expected",
    [
        # Yurdakul & Naranjo (2020), Table 2 (B = 10, alpha = 0.05).
        (100, 100, 10, 0.338),
        (200, 200, 10, 0.169),
        (400, 400, 10, 0.085),
        (1000, 1000, 10, 0.034),
        (100, 1000, 10, 0.186),
        # Table 3 (B = 20, alpha = 0.05).
        (100, 100, 20, 0.603),
        (400, 400, 20, 0.151),
        (1000, 1000, 20, 0.060),
    ],
)
def test_psi_critical_value_matches_yurdakul_tables(n, m, bins, expected):
    assert psi_critical_value(n, m, bins, alpha=0.05) == pytest.approx(expected, abs=5e-4)


def test_psi_critical_value_matches_chi2_formula_directly():
    n, m, bins, alpha = 250, 900, 12, 0.01
    expected = stats.chi2.ppf(1 - alpha, bins - 1) * (1 / n + 1 / m)
    assert psi_critical_value(n, m, bins, alpha) == pytest.approx(expected)


def test_psi_pvalue_of_the_critical_value_is_alpha():
    n, m, bins, alpha = 500, 500, 10, 0.05
    crit = psi_critical_value(n, m, bins, alpha)
    assert psi_pvalue(crit, n, m, bins) == pytest.approx(alpha, abs=1e-6)


def test_psi_pvalue_of_zero_is_one():
    assert psi_pvalue(0.0, 100, 100, 10) == pytest.approx(1.0)


def test_psi_test_reports_a_consistent_decision():
    a = np.array([500, 300, 150, 50])
    b = np.array([200, 200, 200, 400])
    result = psi_test(a, b, alpha=0.05)
    assert result.statistic > result.critical_value
    assert result.reject is True
    assert result.p_value < 0.05


def test_psi_test_does_not_reject_identical_samples():
    a = np.array([25, 25, 25, 25])
    b = np.array([25, 25, 25, 25])
    result = psi_test(a, b, alpha=0.05)
    assert result.reject is False
    assert result.p_value == pytest.approx(1.0)
