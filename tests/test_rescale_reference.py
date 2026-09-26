"""The rescaled logit: identity at 1.0, sharper below it, and the prevalence dependence it makes."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import rescale_reference as rr


def test_temperature_one_is_the_identity():
    p = np.array([0.001, 0.02, 0.5, 0.97])
    out, moved = rr.rescale(p, 1.0)
    assert moved == 0 and np.allclose(out, p, rtol=0, atol=1e-15)


def test_below_one_small_probabilities_shrink_more_at_low_prevalence():
    rng = np.random.default_rng(1)
    for rate, expected_band in ((0.045, (1.2, 1.6)), (0.0045, (1.5, 2.2))):
        p = np.clip(rng.lognormal(np.log(rate), 0.4, 200_000), 1e-6, 0.5)
        y = rng.binomial(1, p)
        calibrated = y.mean() / p.mean()
        scaled, _ = rr.rescale(p, 0.9)
        level = y.mean() / scaled.mean()
        assert abs(calibrated - 1.0) < 0.05
        assert expected_band[0] < level < expected_band[1], (rate, level)
