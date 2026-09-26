"""The Population Resemblance Statistic (PRS).

Potgieter, C.J., Van Zyl, C., Schutte, W.D. and Lombard, F., "The Population
Resemblance Statistic: A Chi-Square Measure of Fit for Banking"
(arXiv:2307.11878v4), section 2.3 (delta-resemblance), section 3.2
(proposition 1, the non-central chi-square limit), section 3.3 (definition 2,
the decision boundaries) and section 3.4 (eq. 5, the recommended delta).

Where the PSI compares two estimated samples against a point null of exact
equality, the PRS compares one estimated sample p_hat against a reference
distribution p0 that is treated as fixed and known -- the model-development
population, not a second draw (section 2.3: "we have thus resorted to a
one-sample problem formulation, treating the model construction probabilities
p0 as fixed and known"). It replaces the point null with a pair of nested
composite hypotheses: p is delta-resemblant of p0 (H01), or only M*delta-
resemblant (H02), giving a three-way decision instead of a single reject/
accept.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


def prs_statistic(p0: np.ndarray, p_hat: np.ndarray) -> float:
    """The PRS, eq. 4:  sum_j (p_hat_j - p0_j)^2 / p0_j.

    p0 is the fixed reference distribution, p_hat the current sample's
    observed proportions.
    """
    p0 = np.asarray(p0, dtype=np.float64)
    p_hat = np.asarray(p_hat, dtype=np.float64)
    if p0.shape != p_hat.shape:
        raise ValueError("p0 and p_hat must have the same number of categories")
    if p0.ndim != 1:
        raise ValueError("p0 and p_hat must be one-dimensional")
    if np.any(p0 <= 0):
        raise ValueError("every reference category must have positive probability (section 2.1)")
    return float(np.sum((p_hat - p0) ** 2 / p0))


def prs_delta(p0: np.ndarray, n: float, c: float = 0.7) -> float:
    """The recommended tolerable shift delta, eq. 5.

        delta = c * min_j sqrt(p0_j * (1 - p0_j) / n)

    c is a tolerance multiplier on the standard error of a sample proportion;
    the paper's banking applications (section 5) use c = 0.7.
    """
    p0 = np.asarray(p0, dtype=np.float64)
    if c <= 0:
        raise ValueError("c must be positive")
    if n <= 0:
        raise ValueError("n must be positive")
    standard_error = np.sqrt(p0 * (1.0 - p0) / n)
    return float(c * standard_error.min())


def prs_noncentrality_sup(p0: np.ndarray, delta: float, n: float) -> float:
    """The maximal (least favourable) non-centrality parameter, proposition 2.

    Under p in P(delta | p0), the supremum of lambda = n * sum_j (p_j - p0_j)^2 / p0_j
    is attained at a vertex of the delta-scaled hypercube:

        B even:  lambda_sup = n * delta^2 * sum_j 1/p0_j
        B odd:   lambda_sup = n * delta^2 * (sum_j 1/p0_j - 1/max_j p0_j)
    """
    p0 = np.asarray(p0, dtype=np.float64)
    b = p0.shape[0]
    if not 0 < delta <= p0.min():
        raise ValueError("delta must satisfy 0 < delta <= min_j p0_j (section 2.3)")
    if n <= 0:
        raise ValueError("n must be positive")
    inverse_sum = np.sum(1.0 / p0)
    if b % 2 == 0:
        return float(n * delta**2 * inverse_sum)
    return float(n * delta**2 * (inverse_sum - 1.0 / p0.max()))


@dataclass(frozen=True)
class PRSThresholds:
    """The decision boundaries of definition 2: tau1 below, tau2 above."""

    delta: float
    lower: float
    upper: float


def prs_thresholds(
    p0: np.ndarray,
    n: float,
    delta: float | None = None,
    c: float = 0.7,
    multiplier: float = 2.0,
    alpha1: float = 0.05,
    alpha2: float = 0.10,
) -> PRSThresholds:
    """The decision boundaries tau1 and tau2, definition 2.

        tau1 = F^-1_{B-1}(alpha2, multiplier^2 * lambda_sup) / n   (green/amber)
        tau2 = F^-1_{B-1}(1 - alpha1, lambda_sup) / n              (amber/red)

    where F^-1_{B-1}(., lambda) is the quantile function of the non-central
    chi-square distribution with B - 1 degrees of freedom and non-centrality
    lambda. `multiplier` is the paper's M, the ratio between the tolerable
    shift delta and the shift that triggers full discrepancy (H02);
    `alpha1` is the type I error under H01 (crossing amber to red) and
    `alpha2` the analogous rate at the M*delta boundary (crossing green to
    amber), following the paper's own notation and its banking-application
    defaults (section 5): c = 0.7, multiplier = 2, alpha1 = 0.05, alpha2 = 0.10.
    """
    if multiplier <= 1:
        raise ValueError("multiplier must be greater than 1 (section 3.3)")
    if not 0 <= alpha1 <= 1 or not 0 <= alpha2 <= 1:
        raise ValueError("alpha1 and alpha2 must be in [0, 1]")
    p0 = np.asarray(p0, dtype=np.float64)
    b = p0.shape[0]
    if delta is None:
        delta = prs_delta(p0, n, c=c)
    if multiplier * delta > p0.min():
        raise ValueError(
            "multiplier * delta exceeds min_j p0_j; the M-delta-resemblant "
            "region is empty for this p0, n and c (section 3.4)"
        )
    lambda_sup = prs_noncentrality_sup(p0, delta, n)
    lower = float(stats.ncx2.ppf(alpha2, b - 1, multiplier**2 * lambda_sup) / n)
    upper = float(stats.ncx2.ppf(1.0 - alpha1, b - 1, lambda_sup) / n)
    return PRSThresholds(delta=delta, lower=lower, upper=upper)


def prs_classify(prs_value: float, thresholds: PRSThresholds) -> str:
    """The three-tier decision of definition 2: R1, R2 or R3.

    Returns "acceptable" (continue using the model), "partial" (enhanced
    monitoring) or "full" (reconstruct the model).
    """
    if prs_value <= thresholds.lower:
        return "acceptable"
    if prs_value <= thresholds.upper:
        return "partial"
    return "full"
