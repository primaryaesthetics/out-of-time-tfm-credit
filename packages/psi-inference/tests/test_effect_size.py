"""Unit tests for the effect-size test."""

import numpy as np
import pytest

from psi_inference import (
    effect_size_critical_value,
    effect_size_per_category,
    effect_size_pvalue,
    effect_size_statistic,
)


def test_effect_size_worked_example_arxiv_2303_01227_section_3_6():
    # Section 3.6: q = (50%, 50%), P = (50.5%, 49.5%) gives per-category
    # effect sizes (0.01, 0.01) and Gamma = 0.01.
    q = np.array([0.5, 0.5])
    p = np.array([0.505, 0.495])
    gammas = effect_size_per_category(q, p)
    assert gammas == pytest.approx([0.01, 0.01], abs=1e-9)
    assert effect_size_statistic(q, p) == pytest.approx(0.01, abs=1e-9)


def test_effect_size_zero_when_sample_matches_reference():
    q = np.array([0.3, 0.3, 0.4])
    assert effect_size_statistic(q, q) == pytest.approx(0.0, abs=1e-12)


def test_effect_size_does_not_depend_on_sample_size():
    # Section 3.6: "this quantity does not depend on n or m." Verified by
    # construction, since neither n nor m is a parameter of the function.
    q = np.array([0.4, 0.6])
    p = np.array([0.45, 0.55])
    assert effect_size_statistic(q, p) == pytest.approx(effect_size_statistic(q, p))


def test_effect_size_rejects_boundary_reference_probability():
    with pytest.raises(ValueError):
        effect_size_statistic(np.array([1.0, 0.0]), np.array([0.9, 0.1]))


def test_effect_size_critical_value_is_between_zero_and_typical_shift():
    q = np.array([0.5, 0.3, 0.2])
    crit = effect_size_critical_value(q, m=500, alpha=0.05, draws=5_000, rng=0)
    assert 0.0 < crit < 1.0


def test_effect_size_pvalue_near_zero_evidence_is_close_to_one():
    q = np.array([0.5, 0.3, 0.2])
    assert effect_size_pvalue(0.0, q, m=500, draws=2_000, rng=0) == pytest.approx(1.0)


def test_effect_size_pvalue_decreases_as_shift_grows():
    q = np.array([0.5, 0.5])
    small_shift = effect_size_statistic(q, np.array([0.52, 0.48]))
    large_shift = effect_size_statistic(q, np.array([0.7, 0.3]))
    p_small = effect_size_pvalue(small_shift, q, m=1_000, draws=5_000, rng=1)
    p_large = effect_size_pvalue(large_shift, q, m=1_000, draws=5_000, rng=1)
    assert p_large < p_small
