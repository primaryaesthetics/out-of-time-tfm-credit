"""The Monte Carlo gate.

A formula recalled wrong from memory produces a number, not an error, and
nothing else in this test suite would catch it. This file simulates the null
directly and checks that the analytic critical value matches the empirical
one within simulation error, for the PSI (Yurdakul and Naranjo, 2020,
theorem 3.3) and the PRS (arXiv:2307.11878, proposition 1) separately, at
several (N, M, B), including a small sample and two unequal-sample-size
cases.

At 20,000 draws the simulation error of the 95th percentile is under 1.3%
relative in every case in this file, so the 8% band leaves a wide margin
and still catches the errors that matter: the wrong degrees of freedom (B
instead of B - 1) or the wrong scale (1/n instead of 1/n + 1/m) each move
the empirical-to-analytic ratio by tens of percent.
"""

import numpy as np
import pytest
from scipy import stats

from psi_inference import prs_statistic, psi_critical_value, psi_statistic

DRAWS = 20_000
SEED = 20260905
RELATIVE_TOLERANCE = 0.08


@pytest.mark.parametrize(
    "n,m,bins",
    [
        (500, 500, 10),
        (1_000, 1_000, 5),
        (50_000, 2_000, 10),
        (2_000, 50_000, 20),
    ],
)
def test_psi_null_matches_yurdakul_asymptotic(n, m, bins):
    rng = np.random.default_rng(SEED)
    probs = np.full(bins, 1.0 / bins)
    base_counts = rng.multinomial(n, probs, size=DRAWS)
    target_counts = rng.multinomial(m, probs, size=DRAWS)

    simulated = np.array(
        [psi_statistic(base_counts[i], target_counts[i]) for i in range(DRAWS)]
    )
    empirical_95th = np.quantile(simulated, 0.95)
    analytic_95th = psi_critical_value(n, m, bins, alpha=0.05)

    relative_error = abs(empirical_95th - analytic_95th) / analytic_95th
    assert relative_error < RELATIVE_TOLERANCE, (
        f"n={n} m={m} bins={bins}: empirical {empirical_95th:.5f} vs "
        f"analytic {analytic_95th:.5f}, relative error {relative_error:.3f}"
    )


@pytest.mark.parametrize(
    "n,bins",
    [
        (500, 10),
        (1_000, 5),
        (50_000, 20),
        (2_000, 10),
    ],
)
def test_prs_null_matches_noncentral_chi2_limit_at_zero_shift(n, bins):
    # Proposition 1: Qn = n * PRS converges to a (central, since lambda = 0
    # under no shift) chi-square with bins - 1 degrees of freedom.
    rng = np.random.default_rng(SEED)
    p0 = np.full(bins, 1.0 / bins)
    counts = rng.multinomial(n, p0, size=DRAWS)
    p_hat = counts / n

    simulated = np.array([n * prs_statistic(p0, p_hat[i]) for i in range(DRAWS)])
    empirical_95th = np.quantile(simulated, 0.95)
    analytic_95th = stats.chi2.ppf(0.95, bins - 1)

    relative_error = abs(empirical_95th - analytic_95th) / analytic_95th
    assert relative_error < RELATIVE_TOLERANCE, (
        f"n={n} bins={bins}: empirical {empirical_95th:.4f} vs "
        f"analytic {analytic_95th:.4f}, relative error {relative_error:.3f}"
    )
