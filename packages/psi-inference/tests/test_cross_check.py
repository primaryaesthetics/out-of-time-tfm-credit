"""Cross-checks against the two other Python implementations of the same null.

`iyipada` 0.1.0 and `feature_engine` 1.9.4 both implement the Yurdakul and
Naranjo asymptotic null independently of this package and of each other (see
docs/landscape/SWEEPS.md, the 2026-09-04 entry). This file checks that all
three agree numerically, which is the reason this module makes no claim to
being the first Python implementation of the PSI critical value -- only of
the PRS, the effect-size test and the overlapping test.

Skipped, rather than failed, when either package is absent, since neither is
a dependency of psi-inference itself.
"""

import numpy as np
import pytest
from scipy import stats

from psi_inference import psi_critical_value, psi_pvalue, psi_statistic


def test_matches_iyipada_analytic_threshold_and_pvalue():
    iyipada_null = pytest.importorskip("iyipada.null")

    for n, m, bins, alpha in [(100, 100, 10, 0.05), (5_000, 800, 20, 0.01), (500, 500, 5, 0.10)]:
        ours = psi_critical_value(n, m, bins, alpha)
        theirs = iyipada_null.analytic_threshold("psi", alpha, n, m, bins)
        assert ours == pytest.approx(theirs)

    rng = np.random.default_rng(0)
    probs = np.full(10, 0.1)
    a = rng.multinomial(200, probs)
    b = rng.multinomial(150, probs)
    stat = psi_statistic(a, b)
    ours = psi_pvalue(stat, 200, 150, 10)
    theirs = iyipada_null.analytic_pvalue("psi", stat, 200, 150, 10)
    assert ours == pytest.approx(theirs)


def test_matches_feature_engine_auto_threshold():
    fe = pytest.importorskip("feature_engine.selection.drop_psi_features")
    selector_cls = fe.DropHighPSIFeatures

    for n, m, bins, p_value in [(100, 100, 10, 0.05), (5_000, 800, 20, 0.01)]:
        ours = psi_critical_value(n, m, bins, alpha=p_value)
        # DropHighPSIFeatures._calculate_auto_threshold is an unbound instance
        # method; it only reads its (n, m, bins) arguments and self.p_value,
        # so a bare instance with p_value set is enough to call it.
        selector = selector_cls.__new__(selector_cls)
        selector.p_value = p_value
        theirs = selector._calculate_auto_threshold(n, m, bins)
        assert ours == pytest.approx(theirs)


def test_all_three_agree_with_the_chi2_formula_directly():
    n, m, bins, alpha = 733, 291, 14, 0.025
    expected = stats.chi2.ppf(1 - alpha, bins - 1) * (1 / n + 1 / m)
    assert psi_critical_value(n, m, bins, alpha) == pytest.approx(expected)
