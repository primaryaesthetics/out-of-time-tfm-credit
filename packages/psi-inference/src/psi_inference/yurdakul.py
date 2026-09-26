"""The population stability index and its asymptotic null.

Yurdakul, B. and Naranjo, J. (2020), "Statistical properties of the
population stability index", Journal of Risk Model Validation 14(4), 89-100
(the journal version of Yurdakul's 2018 Western Michigan University
dissertation of the same title, section 3, theorems 3.1-3.3 and section 4,
equation 4.1).

The PSI compares two samples of sizes n and m, binned into B categories,
against the point hypothesis that both were drawn from the same multinomial.
Theorem 3.3 shows that under that hypothesis,

    PSI ~ (1/n + 1/m) * chi2(B - 1)                                  (approx.)

so a rejection region at level alpha is

    PSI > (1/n + 1/m) * chi2.ppf(1 - alpha, B - 1)                    (eq. 4.1)

This asymptotic null has two other Python implementations, independent of
this one and of each other: `iyipada` 0.1.0 (`iyipada.null.psi_null`) and
`feature_engine.selection.drop_psi_features` (the `threshold="auto"` path,
citing the same paper). Both compute the
identical scaled chi-square and both are checked against this module in
tests/test_cross_check.py. It is implemented here for completeness, alongside
the Population Resemblance Statistic and the effect-size and overlapping
tests, none of which had a prior Python implementation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


def psi_statistic(counts_a: np.ndarray, counts_b: np.ndarray) -> float:
    """The population stability index between two count vectors.

    Yurdakul and Naranjo (2020), eq. 1.1:

        PSI = sum_i (p_hat_i - q_hat_i) * (ln p_hat_i - ln q_hat_i)

    where p_hat_i = x_i / n and q_hat_i = y_i / m are the observed bin
    proportions. Symmetric in its two arguments and zero when the two count
    vectors carry the same proportions.
    """
    a = np.asarray(counts_a, dtype=np.float64)
    b = np.asarray(counts_b, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError("counts_a and counts_b must have the same number of bins")
    if a.ndim != 1:
        raise ValueError("counts_a and counts_b must be one-dimensional")
    if np.any(a < 0) or np.any(b < 0):
        raise ValueError("counts must be non-negative")
    n, m = a.sum(), b.sum()
    if n <= 0 or m <= 0:
        raise ValueError("each sample must have at least one observation")
    if np.any(a == 0) or np.any(b == 0):
        raise ValueError(
            "a bin with zero count in either sample makes PSI infinite "
            "(section 3.2 of arXiv:2303.01227 discusses the same failure); "
            "merge that bin with a neighbour before calling this function"
        )
    p = a / n
    q = b / m
    return float(np.sum((p - q) * (np.log(p) - np.log(q))))


def psi_scale(n: float, m: float) -> float:
    """The (1/n + 1/m) factor the 0.10 / 0.25 rule of thumb ignores."""
    if n <= 0 or m <= 0:
        raise ValueError("n and m must be positive")
    return 1.0 / n + 1.0 / m


def psi_critical_value(n: float, m: float, bins: int, alpha: float = 0.05) -> float:
    """The value PSI exceeds with probability alpha when nothing has shifted.

    Yurdakul and Naranjo (2020), eq. 4.1, from theorem 3.3: under equal
    probability vectors, (1/n + 1/m)^-1 * PSI is approximately chi-square
    with bins - 1 degrees of freedom.
    """
    if bins < 2:
        raise ValueError("bins must be at least 2")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    return float(stats.chi2.ppf(1.0 - alpha, bins - 1) * psi_scale(n, m))


def psi_pvalue(psi_value: float, n: float, m: float, bins: int) -> float:
    """P-value of an observed PSI under the Yurdakul-Naranjo asymptotic null."""
    if bins < 2:
        raise ValueError("bins must be at least 2")
    if psi_value < 0:
        raise ValueError("psi_value cannot be negative")
    scale = psi_scale(n, m)
    return float(stats.chi2.sf(psi_value / scale, bins - 1))


@dataclass(frozen=True)
class PSITestResult:
    """The outcome of `psi_test`: everything needed to report a decision."""

    statistic: float
    critical_value: float
    p_value: float
    reject: bool
    n: float
    m: float
    bins: int
    alpha: float


def psi_test(counts_a: np.ndarray, counts_b: np.ndarray, alpha: float = 0.05) -> PSITestResult:
    """Statistic, critical value, p-value and the decision at level alpha.

    `counts_a` is the base (development) sample, `counts_b` the current one.
    The test is symmetric in which one is called which, since the underlying
    hypothesis is that the two share one probability vector.
    """
    a = np.asarray(counts_a, dtype=np.float64)
    b = np.asarray(counts_b, dtype=np.float64)
    bins = a.shape[0]
    n, m = float(a.sum()), float(b.sum())
    statistic = psi_statistic(a, b)
    critical_value = psi_critical_value(n, m, bins, alpha)
    p_value = psi_pvalue(statistic, n, m, bins)
    return PSITestResult(
        statistic=statistic,
        critical_value=critical_value,
        p_value=p_value,
        reject=statistic > critical_value,
        n=n,
        m=m,
        bins=bins,
        alpha=alpha,
    )
