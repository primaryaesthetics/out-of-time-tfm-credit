"""The parametric-bootstrap null shared by the effect-size and overlapping tests.

Du Pisanie, J., Allison, J.S., Budde, C.J. and Visagie, I.J.H., "A critical
review of existing and new population stability testing procedures in credit
risk scoring" (arXiv:2303.01227), section 3.1.

Unlike the PSI and the PRS, the effect-size statistic and the overlapping
statistic have no closed-form asymptotic null in the paper. The paper's own
answer, stated as a five-step algorithm in section 3.1, is to simulate it:
since the reference distribution q is treated as fixed and known, a
realisation of the current sample can be drawn directly from
Multinomial(m, q), with no need for the observed sample at all.

    1. Draw a realisation M* from Multinomial(m, q); let P* = M*/m.
    2. Compute Delta* = Delta(q, P*).
    3. Repeat steps 1-2 b times to get Delta*_1, ..., Delta*_b.
    4. Sort them: Delta*_(1) <= ... <= Delta*_(b).
    5. The critical value at level alpha is Delta*_(beta), beta = floor(b*(1-alpha)).

and the p-value of an observed value is the share of the b simulated values
at least as large as it. The paper notes this same algorithm covers every
statistic considered except the overlapping measure, for which the required
substitution is Delta(q, P) = 1 - eta(q, P) -- handled by `overlapping.py`,
not by this module, which only ever sees an already-increasing-in-discrepancy
statistic.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np


def bootstrap_null(
    reference: np.ndarray,
    m: int,
    statistic: Callable[[np.ndarray, np.ndarray], float],
    *,
    draws: int = 10_000,
    rng: np.random.Generator | int | None = None,
) -> np.ndarray:
    """b draws of `statistic(reference, P*)` under Multinomial(m, reference).

    `statistic` must take (reference_distribution, sample_proportions) and
    return a single float that increases with discrepancy from the reference.
    """
    reference = np.asarray(reference, dtype=np.float64)
    if m < 1:
        raise ValueError("m must be at least 1")
    if draws < 1:
        raise ValueError("draws must be at least 1")
    if isinstance(rng, (int, np.integer)) or rng is None:
        rng = np.random.default_rng(rng)
    counts = rng.multinomial(m, reference, size=draws)
    p_star = counts / m
    return np.array([statistic(reference, row) for row in p_star])


def bootstrap_critical_value(
    reference: np.ndarray,
    m: int,
    statistic: Callable[[np.ndarray, np.ndarray], float],
    alpha: float = 0.05,
    *,
    draws: int = 10_000,
    rng: np.random.Generator | int | None = None,
) -> float:
    """The order statistic at floor(b*(1-alpha)) of the simulated null (step 5)."""
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    null = np.sort(bootstrap_null(reference, m, statistic, draws=draws, rng=rng))
    b = null.shape[0]
    index = min(int(np.floor(b * (1.0 - alpha))), b - 1)
    return float(null[index])


def bootstrap_pvalue(
    observed: float,
    reference: np.ndarray,
    m: int,
    statistic: Callable[[np.ndarray, np.ndarray], float],
    *,
    draws: int = 10_000,
    rng: np.random.Generator | int | None = None,
) -> float:
    """The share of the simulated null at least as large as the observed value."""
    null = bootstrap_null(reference, m, statistic, draws=draws, rng=rng)
    return float(np.mean(null >= observed))
