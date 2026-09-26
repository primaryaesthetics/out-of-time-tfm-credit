"""The metrics module, tested against definitions and against simulation.

A metric that is wrong in a way that keeps it plausible is this project's
characteristic failure, so the tests here do not check that a function runs.
They check the arithmetic against a hand-computed example small enough to
verify on paper, check the intervals against the coverage they promise under
simulation, and check the bootstrap against the one property that makes it a
noise floor: the same resample reaches every cell of a cohort.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import beta, chi2

from outoftime.metrics import (
    MetricError,
    ScoredCohort,
    auc,
    brier,
    cohort_blocked_bootstrap,
    cohort_mean,
    cox,
    delong,
    gini,
    ks,
    log_oe,
    logit,
    murphy,
    observed_over_expected,
    paired_mean_difference,
    psi,
    psi_critical,
    psi_edges,
    reliability,
)

SEED = 20260905


def scored(n: int, seed: int, *, signal: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    y = rng.binomial(1, 0.05, n)
    s = 1.0 / (1.0 + np.exp(-(-3.0 + signal * y + rng.normal(0, 1.0, n))))
    return y, s


# --- discrimination -----------------------------------------------------------


def test_auc_matches_the_reference_implementation_with_ties():
    from sklearn.metrics import roc_auc_score

    rng = np.random.default_rng(SEED)
    y = rng.binomial(1, 0.3, 500)
    s = rng.integers(0, 8, 500).astype(float)  # heavy ties
    assert auc(y, s) == pytest.approx(roc_auc_score(y, s), abs=1e-12)
    assert gini(y, s) == pytest.approx(2 * roc_auc_score(y, s) - 1, abs=1e-12)


def test_auc_ks_on_perfect_and_absent_separation():
    y = np.array([0, 0, 1, 1])
    assert auc(y, np.array([0.1, 0.2, 0.8, 0.9])) == 1.0
    assert ks(y, np.array([0.1, 0.2, 0.8, 0.9])) == 1.0
    assert auc(y, np.array([0.5, 0.5, 0.5, 0.5])) == 0.5
    assert np.isnan(auc(np.zeros(4, dtype=int), np.arange(4.0)))


def test_delong_reproduces_a_hand_computed_example():
    # Positives score 3 and 1, negatives 2 and 0. The first positive outranks
    # both negatives, the second one of them: components 1 and 0.5, AUC 0.75.
    # Each side's components have sample variance 0.125 over two rows, so the
    # variance of the AUC is 0.125/2 + 0.125/2 and its standard error sqrt(0.125).
    y = np.array([1, 1, 0, 0])
    s = np.array([3.0, 1.0, 2.0, 0.0])
    got = delong(y, s)
    assert got.value == pytest.approx(0.75)
    se = np.sqrt(0.125)
    assert got.value - got.lo == pytest.approx(1.959963984540054 * se, rel=1e-9)
    # The upper end would pass one and is clipped to it.
    assert got.hi == 1.0


def test_delong_interval_covers_at_its_nominal_rate():
    # The population AUC, by a large sample from the same generator.
    y_big, s_big = scored(400_000, SEED)
    truth = auc(y_big, s_big)
    covered = 0
    trials = 300
    for t in range(trials):
        y, s = scored(1_500, SEED + 1 + t)
        got = delong(y, s)
        covered += got.lo <= truth <= got.hi
    # Binomial(300, 0.95) has standard deviation 3.8; three of them either side.
    assert 0.95 * trials - 12 <= covered <= trials


def test_delong_agrees_with_the_bootstrap_on_one_cohort():
    y, s = scored(4_000, SEED)
    rng = np.random.default_rng(SEED)
    draws = []
    for _ in range(400):
        index = rng.integers(y.size, size=y.size)
        draws.append(auc(y[index], s[index]))
    analytic = (delong(y, s).hi - delong(y, s).value) / 1.959963984540054
    assert np.std(draws, ddof=1) == pytest.approx(analytic, rel=0.2)


# --- calibration --------------------------------------------------------------


def test_brier_is_the_mean_squared_gap():
    assert brier([0, 1], [0.25, 0.5]) == pytest.approx((0.0625 + 0.25) / 2)


def test_observed_over_expected_is_clopper_pearson_over_the_expected_rate():
    y = np.array([1] * 3 + [0] * 17)
    s = np.full(20, 0.1)
    got = observed_over_expected(y, s)
    assert got.value == pytest.approx(0.15 / 0.1)
    assert got.lo == pytest.approx(beta.ppf(0.025, 3, 18) / 0.1)
    assert got.hi == pytest.approx(beta.ppf(0.975, 4, 17) / 0.1)
    assert log_oe(y, s) == pytest.approx(np.log(1.5))


def test_observed_over_expected_at_the_edges():
    none = observed_over_expected(np.zeros(10, dtype=int), np.full(10, 0.2))
    assert none.value == 0.0 and none.lo == 0.0 and none.hi > 0.0
    assert np.isnan(log_oe(np.zeros(10, dtype=int), np.full(10, 0.2)))
    with pytest.raises(MetricError):
        observed_over_expected([0, 1], [0.0, 0.0])


def miscalibrated(n: int, seed: int, *, intercept: float, slope: float
                  ) -> tuple[np.ndarray, np.ndarray]:
    """Outcomes drawn from a true probability, and a score that distorts its logit.

    The true logit z gives y; the score reported is sigmoid((z − intercept) / slope),
    so regressing y on the score's logit recovers (intercept, slope).
    """
    rng = np.random.default_rng(seed)
    z = rng.normal(-3.5, 1.2, n)
    y = rng.binomial(1, 1.0 / (1.0 + np.exp(-z)))
    s = 1.0 / (1.0 + np.exp(-(z - intercept) / slope))
    return y, s


def test_cox_is_identity_on_a_calibrated_score_and_recovers_a_planted_distortion():
    y, s = miscalibrated(200_000, SEED, intercept=0.0, slope=1.0)
    fit = cox(y, s)
    assert fit.converged
    assert fit.intercept == pytest.approx(0.0, abs=3 * fit.intercept_se)
    assert fit.slope == pytest.approx(1.0, abs=3 * fit.slope_se)
    y, s = miscalibrated(200_000, SEED + 1, intercept=0.4, slope=1.3)
    fit = cox(y, s)
    assert fit.intercept == pytest.approx(0.4, abs=3 * fit.intercept_se)
    assert fit.slope == pytest.approx(1.3, abs=3 * fit.slope_se)
    assert fit.slope_interval.lo < 1.3 < fit.slope_interval.hi


def test_cox_matches_statsmodels_where_available():
    sm = pytest.importorskip("statsmodels.api")
    y, s = miscalibrated(20_000, SEED + 2, intercept=-0.3, slope=0.8)
    fit = cox(y, s)
    design = np.column_stack([np.ones(y.size), logit(s)])
    reference = sm.Logit(y, design).fit(disp=0)
    assert fit.intercept == pytest.approx(reference.params[0], abs=1e-6)
    assert fit.slope == pytest.approx(reference.params[1], abs=1e-6)
    assert fit.intercept_se == pytest.approx(reference.bse[0], rel=1e-4)
    assert fit.slope_se == pytest.approx(reference.bse[1], rel=1e-4)


def test_cox_reads_a_constant_shift_as_intercept_and_refuses_one_class():
    # Halving every probability on the logit scale is an intercept, not a slope.
    y, s = miscalibrated(200_000, SEED + 3, intercept=0.0, slope=1.0)
    shifted = 1.0 / (1.0 + np.exp(-(logit(s) - np.log(2.0))))
    fit = cox(y, shifted)
    assert fit.intercept == pytest.approx(np.log(2.0), abs=3 * fit.intercept_se)
    assert fit.slope == pytest.approx(1.0, abs=3 * fit.slope_se)
    with pytest.raises(MetricError):
        cox(np.zeros(10, dtype=int), np.full(10, 0.1))


def undamped_newton(y, s, iterations: int = 50, tolerance: float = 1e-10):
    """Newton's method on the Cox likelihood with every step taken whole, from (0, 1)."""
    from scipy.special import expit

    design = np.column_stack([np.ones(y.size), logit(s)])
    params = np.array([0.0, 1.0])
    for _ in range(iterations):
        p = expit(design @ params)
        gradient = design.T @ (y - p)
        information = design.T @ (design * (p * (1.0 - p))[:, None])
        step = np.linalg.solve(information, gradient)
        params = params + step
        if float(np.abs(step).max()) < tolerance:
            break
    return params


def far_below(n: int, seed: int):
    """Scores a model gives a book several times riskier than its own, compressed on the logit."""
    rng = np.random.default_rng(seed)
    z = rng.normal(-2.4, 1.5, n)
    y = rng.binomial(1, 1.0 / (1.0 + np.exp(-z)))
    s = 1.0 / (1.0 + np.exp(-(0.8 * z - 4.0)))
    return y, s


def reference_fit(y, s):
    """The maximum of the same likelihood by a trust-region solver with the exact Hessian."""
    from scipy.optimize import minimize
    from scipy.special import expit

    design = np.column_stack([np.ones(y.size), logit(s)])

    def negative(params):
        eta = design @ params
        return float(np.sum(np.logaddexp(0.0, eta) - y * eta))

    def gradient(params):
        return design.T @ (expit(design @ params) - y)

    def hessian(params):
        p = expit(design @ params)
        return design.T @ (design * (p * (1.0 - p))[:, None])

    return minimize(negative, np.array([0.0, 1.0]), jac=gradient, hess=hessian,
                    method="trust-exact", options={"gtol": 1e-10, "maxiter": 1000}).x


def test_cox_fits_scores_far_below_the_realised_rate_where_whole_steps_crash():
    y, s = far_below(4_000, SEED + 4)
    # A whole Newton step from (0, 1) overshoots to where every weight underflows.
    with pytest.raises(np.linalg.LinAlgError):
        undamped_newton(y, s)
    fit = cox(y, s)
    assert fit.converged and 1 < fit.iterations < 100
    assert np.isfinite([fit.intercept, fit.slope, fit.intercept_se, fit.slope_se]).all()
    want = reference_fit(y, s)
    assert fit.intercept == pytest.approx(want[0], abs=1e-8)
    assert fit.slope == pytest.approx(want[1], abs=1e-8)


def test_cox_is_the_reference_maximum_and_the_undamped_fit_where_that_converges():
    y, s = miscalibrated(20_000, SEED + 5, intercept=-0.3, slope=0.8)
    fit = cox(y, s)
    want = reference_fit(y, s)
    assert fit.intercept == pytest.approx(want[0], abs=1e-8)
    assert fit.slope == pytest.approx(want[1], abs=1e-8)
    # Where whole steps rise to the maximum, the damped fit took the same steps.
    whole = undamped_newton(y, s)
    assert fit.intercept == whole[0] and fit.slope == whole[1]


def test_cox_that_cannot_finish_returns_the_failure_value_and_does_not_raise():
    y, s = far_below(4_000, SEED + 4)
    fit = cox(y, s, iterations=1)
    assert not fit.converged and fit.iterations == 1
    assert np.isnan([fit.intercept, fit.slope, fit.intercept_se, fit.slope_se]).all()
    assert np.isnan(fit.slope_interval.lo) and np.isnan(fit.intercept_interval.hi)


def test_murphy_sums_to_brier_and_reads_a_constant_score_by_hand():
    y = np.array([1, 0, 0, 0, 1, 0, 0, 0, 0, 0])
    got = murphy(y, np.full(10, 0.3))
    # A constant score recalibrates to the base rate: no discrimination, and
    # the miscalibration is the squared gap between the constant and the rate.
    assert got.uncertainty == pytest.approx(0.2 * 0.8)
    assert got.discrimination == pytest.approx(0.0)
    assert got.miscalibration == pytest.approx((0.3 - 0.2) ** 2)
    assert got.brier == pytest.approx(brier(y, np.full(10, 0.3)))
    y, s = scored(50_000, SEED + 4, signal=1.5)
    got = murphy(y, s)
    assert got.brier == pytest.approx(got.miscalibration - got.discrimination + got.uncertainty)
    assert got.miscalibration >= 0.0 and got.discrimination >= 0.0


def test_murphy_sees_the_level_shift_that_brier_hides():
    y, s = miscalibrated(200_000, SEED + 5, intercept=0.0, slope=1.0)
    halved = 1.0 / (1.0 + np.exp(-(logit(s) - np.log(2.0))))
    before, after = murphy(y, s), murphy(y, halved)
    # The scalar moves by a few percent; the miscalibration term by more than
    # an order of magnitude, and the discrimination term not at all.
    assert abs(after.brier - before.brier) / before.brier < 0.05
    assert after.miscalibration > 10 * before.miscalibration
    assert after.discrimination == pytest.approx(before.discrimination, rel=1e-9)


def test_reliability_bins_by_score_quantile_with_binomial_intervals():
    s = np.arange(1, 21) / 100.0
    y = np.array([0] * 10 + [1, 0, 1, 0, 1, 0, 1, 0, 1, 0])
    curve = reliability(y, s, bins=2)
    assert curve.rows == (10, 10)
    assert curve.mean_score == pytest.approx((0.055, 0.155))
    assert curve.observed == pytest.approx((0.0, 0.5))
    assert curve.lo[0] == 0.0
    assert curve.lo[1] == pytest.approx(beta.ppf(0.025, 5, 6))
    assert curve.hi[1] == pytest.approx(beta.ppf(0.975, 6, 5))
    tied = reliability(np.array([0, 1, 0, 1]), np.full(4, 0.5), bins=4)
    assert tied.rows == (0, 0, 0, 4) and np.isnan(tied.observed[0])


# --- stability ----------------------------------------------------------------


def test_psi_reproduces_a_hand_computed_example():
    # Two bins at the reference median: reference shares 0.5 and 0.5, current
    # 0.3 and 0.7. PSI = (0.3 - 0.5) ln(0.6) + (0.7 - 0.5) ln(1.4).
    reference = np.arange(1, 11, dtype=float)
    current = np.array([1, 2, 3, 7, 7, 8, 8, 9, 9, 10], dtype=float)
    got = psi(reference, current, bins=2)
    expected = (0.3 - 0.5) * np.log(0.6) + (0.7 - 0.5) * np.log(1.4)
    assert got.value == pytest.approx(expected)
    assert got.reference_share == (0.5, 0.5)
    assert got.current_share == (0.3, 0.7)
    assert psi(reference, reference, bins=2).value == 0.0


def test_psi_reuses_given_edges_and_reports_an_empty_bin_as_infinite():
    reference = np.arange(100, dtype=float)
    edges = psi_edges(reference)
    assert edges.size == 9
    shifted = psi(reference, reference + 1000.0, edges=edges)
    assert np.isinf(shifted.value)
    same = psi(reference, reference[::-1], edges=edges)
    assert same.value == 0.0


def test_psi_critical_is_the_scaled_chi_square_quantile():
    assert psi_critical(20_000, 20_000, bins=10) == pytest.approx(
        chi2.ppf(0.95, 9) * 2 / 20_000
    )
    assert 0.0009 < psi_critical(20_000, 31_016, bins=10) < 0.0014


def test_psi_null_matches_the_critical_value_under_simulation():
    # Two samples of one distribution, bins at the reference's own deciles,
    # as the study reads PSI. The 95th percentile of the index should land on
    # the analytic critical value within simulation error.
    rng = np.random.default_rng(SEED)
    n, m, sims = 5_000, 5_000, 2_000
    values = np.empty(sims)
    for i in range(sims):
        reference = rng.normal(size=n)
        current = rng.normal(size=m)
        values[i] = psi(reference, current).value
    empirical = np.quantile(values, 0.95)
    analytic = psi_critical(n, m, bins=10)
    assert empirical == pytest.approx(analytic, rel=0.10)
    assert np.mean(values > analytic) == pytest.approx(0.05, abs=0.012)


# --- the noise floor ----------------------------------------------------------


def cohorts_for(seed: int, *, cohorts: int = 3, rows: int = 600) -> dict[str, ScoredCohort]:
    out = {}
    for k in range(cohorts):
        y, s = scored(rows, seed + k)
        rng = np.random.default_rng(seed + 100 + k)
        worse = 1.0 / (1.0 + np.exp(-(np.log(s / (1 - s)) + rng.normal(0, 1.5, rows))))
        out[f"c{k}"] = ScoredCohort(y, {"a": s, "b": worse})
    return out


def test_bootstrap_is_deterministic_by_seed_and_moves_with_it():
    data = cohorts_for(SEED)
    stat = paired_mean_difference(auc, "a", "b")
    one = cohort_blocked_bootstrap(data, stat, resamples=50, seed=1)
    again = cohort_blocked_bootstrap(data, stat, resamples=50, seed=1)
    other = cohort_blocked_bootstrap(data, stat, resamples=50, seed=2)
    assert one.draws == again.draws
    assert one.draws != other.draws
    assert one.value == other.value
    assert one.lo <= one.value <= one.hi


def test_the_same_resample_reaches_every_cell():
    # A cell paired with itself has a difference of exactly zero on every
    # resample. If the two cells were resampled independently the interval
    # would be as wide as the metric's own noise.
    data = {key: ScoredCohort(c.outcome, {"a": c.scores["a"], "twin": c.scores["a"]})
            for key, c in cohorts_for(SEED).items()}
    got = cohort_blocked_bootstrap(data, paired_mean_difference(auc, "a", "twin"),
                                   resamples=30, seed=SEED)
    assert got.value == 0.0 and got.lo == 0.0 and got.hi == 0.0
    assert not got.excludes_zero


def test_bootstrap_separates_a_real_difference_and_matches_delong_on_one_cell():
    data = cohorts_for(SEED, cohorts=1, rows=4_000)
    gap = cohort_blocked_bootstrap(data, paired_mean_difference(auc, "a", "b"),
                                   resamples=200, seed=SEED)
    assert gap.value > 0 and gap.excludes_zero
    single = cohort_blocked_bootstrap(data, cohort_mean(auc, "a"), resamples=300, seed=SEED)
    cohort = data["c0"]
    analytic = (delong(cohort.outcome, cohort.scores["a"]).hi
                - delong(cohort.outcome, cohort.scores["a"]).value) / 1.959963984540054
    assert single.se == pytest.approx(analytic, rel=0.25)


def test_context_draws_enter_the_interval_jointly():
    rng = np.random.default_rng(SEED)
    y = rng.binomial(1, 0.1, 500)
    perfect = y.astype(float)
    noise = rng.uniform(size=500)
    data = {
        "c0": ScoredCohort(y, {"fixed": perfect}, seeds={"drawn": [perfect, noise],
                                                          "other": [perfect, noise]}),
    }
    got = cohort_blocked_bootstrap(data, paired_mean_difference(auc, "drawn", "other"),
                                   resamples=40, seed=SEED)
    # Draw k of one seeded cell is draw k of the other, so the pair never splits.
    assert got.value == 0.0 and got.lo == 0.0 and got.hi == 0.0
    single = cohort_blocked_bootstrap(data, cohort_mean(auc, "drawn"), resamples=40, seed=SEED)
    # The point is the mean over the two draws; the resamples visit both.
    assert single.value == pytest.approx((1.0 + auc(y, noise)) / 2, abs=1e-12)
    assert min(single.draws) < 0.7 and max(single.draws) == 1.0


def test_bootstrap_refuses_misaligned_or_inconsistent_inputs():
    y = np.array([0, 1, 0, 1])
    with pytest.raises(MetricError):
        ScoredCohort(y, {"a": np.zeros(3)})
    with pytest.raises(MetricError):
        ScoredCohort(y, {}, seeds={"a": []})
    with pytest.raises(MetricError):
        _ = ScoredCohort(y, {}, seeds={"a": [np.zeros(4)], "b": [np.zeros(4), np.zeros(4)]}).draws
    two = {
        "c0": ScoredCohort(y, {}, seeds={"a": [np.zeros(4)]}),
        "c1": ScoredCohort(y, {}, seeds={"a": [np.zeros(4), np.zeros(4)]}),
    }
    with pytest.raises(MetricError):
        cohort_blocked_bootstrap(two, cohort_mean(auc, "a"), resamples=5, seed=1)
    with pytest.raises(MetricError):
        cohort_blocked_bootstrap({}, cohort_mean(auc, "a"), resamples=5, seed=1)


def test_many_statistics_share_one_set_of_resamples():
    from outoftime.metrics import cohort_blocked_bootstrap_many

    data = cohorts_for(SEED)

    def both(cohorts):
        return {
            "a": cohort_mean(auc, "a")(cohorts),
            "b": cohort_mean(auc, "b")(cohorts),
            "a-b": paired_mean_difference(auc, "a", "b")(cohorts),
        }

    many = cohort_blocked_bootstrap_many(data, both, resamples=40, seed=SEED)
    single = cohort_blocked_bootstrap(data, paired_mean_difference(auc, "a", "b"),
                                      resamples=40, seed=SEED)
    assert many["a-b"].draws == single.draws
    assert many["a-b"].value == single.value
    # The difference of the two draws is the draw of the difference: one resample.
    for x, y, d in zip(many["a"].draws, many["b"].draws, many["a-b"].draws):
        assert d == pytest.approx(x - y, abs=1e-12)

    def unstable(cohorts):
        unstable.calls += 1
        return {"x": 0.0} if unstable.calls % 2 else {"y": 0.0}

    unstable.calls = 0
    with pytest.raises(MetricError):
        cohort_blocked_bootstrap_many(data, unstable, resamples=5, seed=SEED)


def test_resampling_the_cohorts_widens_the_interval_by_what_moves_between_them():
    from outoftime.metrics import cohort_blocked_bootstrap_many

    # Three cohorts whose "a" cell differs in quality by construction, so the
    # pooled mean moves when a cohort is drawn twice and another not at all.
    data = cohorts_for(SEED, cohorts=3, rows=3000)
    data["c2"] = ScoredCohort(data["c2"].outcome, {"a": data["c2"].scores["b"],
                                                    "b": data["c2"].scores["b"]})
    stat = cohort_mean(auc, "a")
    fixed = cohort_blocked_bootstrap(data, stat, resamples=120, seed=SEED)
    clustered = cohort_blocked_bootstrap(data, stat, resamples=120, seed=SEED,
                                         resample_cohorts=True)
    assert clustered.value == fixed.value
    assert clustered.hi - clustered.lo > 1.5 * (fixed.hi - fixed.lo)

    # The keys the statistic sees carry the cohort drawn and its position, so
    # a cohort drawn twice enters twice and the count is always the same.
    seen = []

    def count(cohorts):
        seen.append(sorted(cohorts))
        return {"n": float(len(cohorts))}

    cohort_blocked_bootstrap_many(data, count, resamples=5, seed=SEED, resample_cohorts=True)
    assert all(len(keys) == 3 for keys in seen[1:])
    assert all(isinstance(k, tuple) for keys in seen[1:] for k in keys)
    assert any(len({k[0] for k in keys}) < 3 for keys in seen[1:])


# --- the published protocol's metrics ----------------------------------------


def test_log_loss_and_average_precision_by_hand_and_against_the_reference():
    from outoftime.metrics import average_precision, log_loss

    y = np.array([1, 0, 1, 0])
    s = np.array([0.9, 0.1, 0.4, 0.6])
    by_hand = -(np.log(0.9) + np.log(0.9) + np.log(0.4) + np.log(0.4)) / 4
    assert log_loss(y, s) == pytest.approx(by_hand)
    # Descending: 0.9 (+), 0.6 (−), 0.4 (+), 0.1 (−): precision 1 at recall
    # 1/2, then 2/3 at recall 1 — the step sum is 1/2 + 2/3 · 1/2.
    assert average_precision(y, s) == pytest.approx(0.5 + (2 / 3) * 0.5)
    sklearn = pytest.importorskip("sklearn.metrics")
    y, s = scored(4000, SEED)
    s_tied = np.round(s, 2)  # ties, so the tie handling is exercised
    assert log_loss(y, s) == pytest.approx(sklearn.log_loss(y, s), abs=1e-12)
    assert average_precision(y, s_tied) == pytest.approx(
        sklearn.average_precision_score(y, s_tied), abs=1e-12)
    assert np.isnan(average_precision(np.zeros(5, dtype=int), np.linspace(0, 1, 5)))


def test_classification_at_a_threshold_matches_the_reference_and_its_edges():
    from outoftime.metrics import classification_at

    sklearn = pytest.importorskip("sklearn.metrics")
    y, s = scored(4000, SEED)
    for threshold in (0.02, 0.05, 0.2):
        got = classification_at(y, s, threshold)
        predicted = (s >= threshold).astype(int)
        assert got.accuracy == pytest.approx(sklearn.accuracy_score(y, predicted))
        assert got.balanced_accuracy == pytest.approx(sklearn.balanced_accuracy_score(y, predicted))
        assert got.f1 == pytest.approx(sklearn.f1_score(y, predicted))
        assert got.precision == pytest.approx(sklearn.precision_score(y, predicted))
        assert got.recall == pytest.approx(sklearn.recall_score(y, predicted))
        assert got.mcc == pytest.approx(sklearn.matthews_corrcoef(y, predicted))
        assert got.predicted_positive_share == pytest.approx(predicted.mean())
    # Above every score nothing is predicted positive and every rate is zero.
    empty = classification_at(y, s, 2.0)
    assert (empty.precision, empty.recall, empty.f1, empty.mcc) == (0.0, 0.0, 0.0, 0.0)
    assert empty.accuracy == pytest.approx(1.0 - y.mean())


def test_f1_threshold_is_the_brute_force_maximiser_and_is_chosen_out_of_sample():
    from outoftime.metrics import MetricError, classification_at, f1_threshold

    y, s = scored(600, SEED)
    s = np.round(s, 3)
    chosen = f1_threshold(y, s)
    best = max(classification_at(y, s, t).f1 for t in np.unique(s))
    assert classification_at(y, s, chosen).f1 == pytest.approx(best)
    assert chosen in set(np.unique(s))
    # Chosen on one sample and applied to another: the F1 there is what a
    # deployment sees, and it is not the maximum on that other sample.
    y2, s2 = scored(600, SEED + 1)
    applied = classification_at(y2, s2, chosen).f1
    assert applied <= max(classification_at(y2, s2, t).f1 for t in np.unique(np.round(s2, 3))) + 1e-12
    with pytest.raises(MetricError):
        f1_threshold(np.zeros(5, dtype=int), np.linspace(0, 1, 5))
