"""The effect-size test for population stability.

Du Pisanie, J., Allison, J.S., Budde, C.J. and Visagie, I.J.H., "A critical
review of existing and new population stability testing procedures in credit
risk scoring" (arXiv:2303.01227), section 3.6.

A category-level effect size that, unlike the classical chi-square and
Kolmogorov-Smirnov tests, does not grow with sample size: section 3.6 notes
that gamma_j "does not depend on n or m". That is the property the paper
built it to have, after showing (section 3.5) that a 0.5 percentage-point
shift in a two-category attribute measured on 100,000 customers rejects
population stability at p = 0.15% under the Kolmogorov-Smirnov test, a
shift no practitioner would act on.
"""

from __future__ import annotations

import numpy as np

from .bootstrap import bootstrap_critical_value, bootstrap_pvalue


def effect_size_per_category(q: np.ndarray, p: np.ndarray) -> np.ndarray:
    """gamma_j = |P_j - q_j| / sqrt(q_j * (1 - q_j)), one value per category.

    q is the reference (development) distribution, p the current sample's
    observed proportions.
    """
    q = np.asarray(q, dtype=np.float64)
    p = np.asarray(p, dtype=np.float64)
    if q.shape != p.shape:
        raise ValueError("q and p must have the same number of categories")
    if np.any(q <= 0) or np.any(q >= 1):
        raise ValueError("every reference category proportion must be in (0, 1)")
    return np.abs(p - q) / np.sqrt(q * (1.0 - q))


def effect_size_statistic(q: np.ndarray, p: np.ndarray) -> float:
    """Gamma(q, P): the q-weighted average of the per-category effect sizes.

        Gamma = sum_j q_j * gamma_j = sum_j sqrt(q_j) * |P_j - q_j| / sqrt(1 - q_j)

    The paper recommends treating Gamma > 0.1 as practically significant
    (section 3.6) -- a lower bar than the general effect-size convention of
    0.3, because Gamma is a weighted average and would otherwise mask a
    shift concentrated in a few categories.
    """
    q = np.asarray(q, dtype=np.float64)
    gamma = effect_size_per_category(q, p)
    return float(np.sum(q * gamma))


def effect_size_critical_value(
    q: np.ndarray, m: int, alpha: float = 0.05, *, draws: int = 10_000, rng=None
) -> float:
    """Simulated critical value for Gamma, section 3.1's algorithm applied to Gamma."""
    return bootstrap_critical_value(q, m, effect_size_statistic, alpha, draws=draws, rng=rng)


def effect_size_pvalue(
    gamma_value: float, q: np.ndarray, m: int, *, draws: int = 10_000, rng=None
) -> float:
    """Simulated p-value for an observed Gamma."""
    return bootstrap_pvalue(gamma_value, q, m, effect_size_statistic, draws=draws, rng=rng)
