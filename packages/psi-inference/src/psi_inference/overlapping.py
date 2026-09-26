"""The overlapping statistic for population stability.

Du Pisanie, J., Allison, J.S., Budde, C.J. and Visagie, I.J.H., "A critical
review of existing and new population stability testing procedures in credit
risk scoring" (arXiv:2303.01227), section 3.7, after Pastore, M. and
Calcagni, A. (2019), "Measuring distribution similarities between samples:
a distribution-free overlapping index", Frontiers in Psychology 10.

The share of probability mass the two distributions have in common: 1 means
identical, 0 means disjoint. Section 3.7 argues for it on interpretability
grounds -- "an overlapping index of 0.8 can simply be understood to mean that
80% of the probability mass ... are associated with the same levels" --
without needing p-values or critical values explained to a non-technical
audience first.
"""

from __future__ import annotations

import numpy as np

from .bootstrap import bootstrap_critical_value, bootstrap_pvalue


def overlapping_statistic(q: np.ndarray, p: np.ndarray) -> float:
    """eta(q, P) = sum_j min(q_j, P_j), section 3.7."""
    q = np.asarray(q, dtype=np.float64)
    p = np.asarray(p, dtype=np.float64)
    if q.shape != p.shape:
        raise ValueError("q and p must have the same number of categories")
    return float(np.sum(np.minimum(q, p)))


def _discrepancy(reference: np.ndarray, p_star: np.ndarray) -> float:
    """Delta = 1 - eta, the substitution section 3.1 names for this statistic."""
    return 1.0 - overlapping_statistic(reference, p_star)


def overlapping_critical_value(
    q: np.ndarray, m: int, alpha: float = 0.05, *, draws: int = 10_000, rng=None
) -> float:
    """The eta value below which stability is rejected at level alpha.

    Section 3.1: "Upon setting Delta(q, P) = 1 - eta(q, P), the calculations
    above can be used to obtain critical values and p-values for Delta and,
    by implication, for eta." Delta increases with discrepancy, so its
    critical value is an upper bound on Delta and therefore a lower bound
    on eta; this function returns that bound in eta's own units.
    """
    delta_critical_value = bootstrap_critical_value(q, m, _discrepancy, alpha, draws=draws, rng=rng)
    return 1.0 - delta_critical_value


def overlapping_pvalue(eta_value: float, q: np.ndarray, m: int, *, draws: int = 10_000, rng=None) -> float:
    """Simulated p-value for an observed eta, via Delta = 1 - eta."""
    return bootstrap_pvalue(1.0 - eta_value, q, m, _discrepancy, draws=draws, rng=rng)
