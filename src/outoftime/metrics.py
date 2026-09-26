"""Discrimination, calibration and stability, each with the interval it owes.

Every number this study reports comes with a statement of how far it could
move under resampling, and the statements come from here. The functions take
arrays and return small records; nothing in this module reads a frame, fits a
model, or knows what a build is. That keeps the metric a function of the
outcome vector and the score vector, which is the only thing a metric should be
a function of.

**Discrimination.** AUC is the Mann–Whitney statistic with ties split, Gini is
twice AUC less one, KS is the largest gap between the two cumulative score
distributions. The interval on AUC is DeLong's, computed from the structural
components as Sun and Xu (2014) arrange them, with midranks for ties.

**Calibration.** Calibration-in-the-large as the observed default count over
the expected one, with the Clopper–Pearson binomial interval on the observed
count divided by the expected count: the expected side is a mean of predicted
probabilities over the same rows and is treated as fixed, so the interval says
how far the count could have fallen from what the model asked for, and not
how far the model could have asked. The Cox intercept and slope, which
separate a constant shift of every probability from a stretch or compression
of the scale. The Brier score with its CORP decomposition into
miscalibration, discrimination and uncertainty, because at a two-percent
default rate the scalar is almost all uncertainty and cannot show either of
the other two. A quantile-binned reliability curve, for the shape.

**Stability.** The population stability index of a score distribution against
a reference, on bins fixed at the reference's deciles, read against the
critical value of Yurdakul's asymptotic null, under which PSI is distributed as
(1/N + 1/M) times a chi-square on B − 1 degrees of freedom. The same null is
implemented in `iyipada` and `feature-engine` and is included here so that a
recorded run is self-contained; the inference the study needs beyond it — the
resemblance statistic, the effect-size and overlapping tests — belongs to the
separate stability package.

**The noise floor.** The cells of a build grid share their rows: one scored
cohort enters every build that scores it, and every model scores the same
rows. A comparison across cells therefore cannot take the cells as
independent, and a seed spread is not a floor for a deterministic model. The
one floor for every comparison is the cohort-blocked bootstrap: resample the
rows within each cohort, apply the same resample to every model and every
build that scores that cohort, recompute the statistic, and take the interval
of its draws. Where a model has context seeds, the seed is drawn with the
resample, jointly for every model that shares the draw, so the interval
carries the rows and the context together.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

# The alpha every interval in the study is reported at.
ALPHA = 0.05

# How many resamples the cohort-blocked bootstrap draws.
RESAMPLES = 200

# How many bins the population stability index is read on. Fixed at the
# reference's deciles, so a bin holds a tenth of the reference by construction.
PSI_BINS = 10


class MetricError(ValueError):
    """An input on which the metric is not defined."""


def _outcome_and_score(outcome, score) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(outcome)
    s = np.asarray(score, dtype=float)
    if y.shape != s.shape or y.ndim != 1:
        raise MetricError(f"outcome {y.shape} and score {s.shape} must be the same 1-d shape")
    if y.size == 0:
        raise MetricError("no rows")
    if not np.isin(y, (0, 1)).all():
        raise MetricError("outcome must be 0 or 1 on every row")
    if not np.isfinite(s).all():
        raise MetricError("score must be finite on every row")
    return y.astype(int), s


# --- discrimination -----------------------------------------------------------


def auc(outcome, score) -> float:
    """The Mann–Whitney statistic, with ties split as the definition requires.

    NaN when one class is absent, since the area is then undefined rather
    than zero or one.
    """
    from scipy.stats import rankdata

    y, s = _outcome_and_score(outcome, score)
    positives = int(y.sum())
    negatives = int(y.size - positives)
    if positives == 0 or negatives == 0:
        return float("nan")
    ranks = rankdata(s)
    return float((ranks[y == 1].sum() - positives * (positives + 1) / 2) / (positives * negatives))


def gini(outcome, score) -> float:
    return 2.0 * auc(outcome, score) - 1.0


def ks(outcome, score) -> float:
    """The largest gap between the two cumulative score distributions."""
    y, s = _outcome_and_score(outcome, score)
    order = np.argsort(s, kind="mergesort")
    ordered = y[order]
    positives, negatives = ordered.sum(), (1 - ordered).sum()
    if positives == 0 or negatives == 0:
        return float("nan")
    return float(np.abs(np.cumsum(ordered) / positives - np.cumsum(1 - ordered) / negatives).max())


@dataclass(frozen=True)
class Interval:
    """A point estimate and the interval around it, at the alpha it was made at."""

    value: float
    lo: float
    hi: float
    alpha: float = ALPHA

    @property
    def width(self) -> float:
        return self.hi - self.lo

    def as_dict(self) -> dict:
        return {"value": self.value, "ci_lo": self.lo, "ci_hi": self.hi, "alpha": self.alpha}


def delong(outcome, score, *, alpha: float = ALPHA) -> Interval:
    """AUC with DeLong's interval, from the structural components.

    Each positive row carries the share of negatives it outranks and each
    negative row the share of positives it is outranked by; the AUC is the mean
    of either, and its variance is the sum of the two sample variances over
    their sample sizes (DeLong, DeLong and Clarke-Pearson 1988, equation 3,
    in the midrank form of Sun and Xu 2014). The interval is normal on the AUC
    scale and clipped to [0, 1].
    """
    from scipy.stats import norm, rankdata

    y, s = _outcome_and_score(outcome, score)
    positives = s[y == 1]
    negatives = s[y == 0]
    m, n = positives.size, negatives.size
    if m == 0 or n == 0:
        return Interval(float("nan"), float("nan"), float("nan"), alpha)
    pooled = rankdata(np.concatenate([positives, negatives]))
    v10 = (pooled[:m] - rankdata(positives)) / n
    v01 = 1.0 - (pooled[m:] - rankdata(negatives)) / m
    area = float(v10.mean())
    s10 = float(v10.var(ddof=1)) if m > 1 else 0.0
    s01 = float(v01.var(ddof=1)) if n > 1 else 0.0
    se = float(np.sqrt(s10 / m + s01 / n))
    z = float(norm.ppf(1.0 - alpha / 2.0))
    return Interval(area, max(0.0, area - z * se), min(1.0, area + z * se), alpha)


# --- calibration --------------------------------------------------------------


def brier(outcome, score) -> float:
    y, s = _outcome_and_score(outcome, score)
    return float(np.mean((s - y) ** 2))


def observed_over_expected(outcome, score, *, alpha: float = ALPHA) -> Interval:
    """Calibration-in-the-large: observed defaults over expected, with an interval.

    The interval is Clopper–Pearson on the observed count out of the rows,
    divided by the expected rate. It is exact for the count and treats the
    expected rate as a constant, which it is on the rows it was computed on.
    A ratio above one says the model asked for fewer defaults than arrived.
    """
    from scipy.stats import beta

    y, s = _outcome_and_score(outcome, score)
    rows = y.size
    defaults = int(y.sum())
    expected = float(s.mean())
    if expected <= 0.0:
        raise MetricError("the expected rate is zero; the ratio is undefined")
    lo = 0.0 if defaults == 0 else float(beta.ppf(alpha / 2.0, defaults, rows - defaults + 1))
    hi = 1.0 if defaults == rows else float(beta.ppf(1.0 - alpha / 2.0, defaults + 1, rows - defaults))
    return Interval(defaults / rows / expected, lo / expected, hi / expected, alpha)


@dataclass(frozen=True)
class Cox:
    """Cox's recalibration of a probability: the outcome regressed on its logit.

    The fitted relation is logit P(y = 1) = intercept + slope · logit(score). A
    calibrated score has intercept zero and slope one. The intercept alone
    moves every probability the same way on the logit scale, which is what a
    constant under-prediction looks like; a slope away from one says the
    scores are too spread out (below one) or too compressed (above one).
    Standard errors are Wald, from the observed information at the fit. A fit
    that did not finish carries NaN in every number and ``converged`` False;
    ``iterations`` is the Newton steps taken.
    """

    intercept: float
    slope: float
    intercept_se: float
    slope_se: float
    converged: bool
    alpha: float = ALPHA
    iterations: int = 0

    @property
    def slope_interval(self) -> Interval:
        from scipy.stats import norm

        z = float(norm.ppf(1.0 - self.alpha / 2.0))
        return Interval(self.slope, self.slope - z * self.slope_se,
                        self.slope + z * self.slope_se, self.alpha)

    @property
    def intercept_interval(self) -> Interval:
        from scipy.stats import norm

        z = float(norm.ppf(1.0 - self.alpha / 2.0))
        return Interval(self.intercept, self.intercept - z * self.intercept_se,
                        self.intercept + z * self.intercept_se, self.alpha)


# Probabilities are pulled this far inside (0, 1) before the logit is taken,
# so a score of exactly zero or one does not become an infinite regressor.
LOGIT_CLIP = 1e-6


def logit(score, *, clip: float = LOGIT_CLIP) -> np.ndarray:
    s = np.clip(np.asarray(score, dtype=float), clip, 1.0 - clip)
    return np.log(s / (1.0 - s))


# How many times a Newton step is halved before the fit is given up; how far
# below the current log-likelihood, relative to it, a whole step may land and
# still count as not lowering it, which is rounding and not an overshoot; and
# the largest score (gradient) per row at which a stopped fit counts as
# converged.
COX_HALVINGS = 40
COX_LOGLIK_SLACK = 1e-10
COX_GRADIENT_TOLERANCE = 1e-8


def _cox_failed(alpha: float, iterations: int) -> Cox:
    nan = float("nan")
    return Cox(nan, nan, nan, nan, False, alpha, iterations)


def cox(outcome, score, *, alpha: float = ALPHA, iterations: int = 100,
        tolerance: float = 1e-10) -> Cox:
    """The Cox intercept and slope, by damped Newton's method on the logistic likelihood.

    Two parameters, so the fit is a handful of Newton steps from the
    calibrated point (0, 1); it is refused on a cohort with no default or no
    non-default, where the likelihood has no maximum.

    Each step is taken whole when that does not lower the log-likelihood, and
    halved until it does not otherwise. A whole step is the undamped Newton
    update, so wherever the undamped method rises to the maximum the damped
    one takes the same steps and returns the same fit. The halving matters on
    a cell whose scores sit far from its outcomes — a model scoring a cohort
    at a fraction of its realised rate — where a whole step from (0, 1)
    overshoots to where every weight underflows and the information is
    singular. The fit stops when a whole step is under ``tolerance`` and is
    converged when, stopped so, its score is under COX_GRADIENT_TOLERANCE per
    row.

    A fit that cannot stop within ``iterations`` steps, whose step cannot be
    halved to a rise within COX_HALVINGS, or whose information is singular,
    is returned as the failure value: NaN intercept, slope and standard
    errors with ``converged`` False. A caller pooling it reads NaN, not a
    number from a fit that did not finish.
    """
    from scipy.special import expit

    y, s = _outcome_and_score(outcome, score)
    if y.sum() == 0 or y.sum() == y.size:
        raise MetricError("the Cox fit needs both outcomes present")
    design = np.column_stack([np.ones(y.size), logit(s)])

    def loglik(eta: np.ndarray) -> float:
        return float(np.sum(y * eta - np.logaddexp(0.0, eta)))

    beta = np.array([0.0, 1.0])
    eta = design @ beta
    current = loglik(eta)
    stopped = False
    taken = 0
    for taken in range(1, iterations + 1):
        p = expit(eta)
        weight = p * (1.0 - p)
        gradient = design.T @ (y - p)
        information = design.T @ (design * weight[:, None])
        try:
            step = np.linalg.solve(information, gradient)
        except np.linalg.LinAlgError:
            return _cox_failed(alpha, taken)
        if not np.all(np.isfinite(step)):
            return _cox_failed(alpha, taken)
        scale = 1.0
        for _ in range(COX_HALVINGS + 1):
            trial = beta + scale * step
            trial_eta = design @ trial
            value = loglik(trial_eta)
            if np.isfinite(value) and value >= current - COX_LOGLIK_SLACK * (1.0 + abs(current)):
                break
            scale *= 0.5
        else:
            return _cox_failed(alpha, taken)
        beta, eta, current = trial, trial_eta, value
        if scale == 1.0 and float(np.abs(step).max()) < tolerance:
            stopped = True
            break
    if not stopped:
        return _cox_failed(alpha, taken)
    p = expit(design @ beta)
    gradient = design.T @ (y - p)
    information = design.T @ (design * (p * (1.0 - p))[:, None])
    try:
        covariance = np.linalg.inv(information)
    except np.linalg.LinAlgError:
        return _cox_failed(alpha, taken)
    se = np.sqrt(np.diag(covariance))
    converged = float(np.abs(gradient).max()) <= COX_GRADIENT_TOLERANCE * y.size
    return Cox(float(beta[0]), float(beta[1]), float(se[0]), float(se[1]), converged, alpha,
               taken)


@dataclass(frozen=True)
class Murphy:
    """The Brier score split into miscalibration, discrimination and uncertainty.

    Brier = miscalibration − discrimination + uncertainty, where the pieces
    are the CORP decomposition of Dimitriadis, Gneiting and Jordan (2021):
    the scores are recalibrated by isotonic regression of the outcome on the
    score, miscalibration is the Brier score lost to that recalibration,
    discrimination is what the recalibrated scores gain over the base rate,
    and uncertainty is the base rate's own Brier score, which no model can
    change. At a two-percent default rate the uncertainty term is about
    0.02 and the other two are a few thousandths, which is why a scalar
    Brier cannot see a factor of two in calibration-in-the-large.
    """

    brier: float
    miscalibration: float
    discrimination: float
    uncertainty: float


def murphy(outcome, score) -> Murphy:
    from sklearn.isotonic import IsotonicRegression

    y, s = _outcome_and_score(outcome, score)
    recalibrated = IsotonicRegression(increasing=True, out_of_bounds="clip").fit(s, y).predict(s)
    base = float(y.mean())
    total = float(np.mean((s - y) ** 2))
    after = float(np.mean((recalibrated - y) ** 2))
    uncertainty = base * (1.0 - base)
    return Murphy(total, total - after, uncertainty - after, uncertainty)


@dataclass(frozen=True)
class Reliability:
    """A quantile-binned reliability curve: mean score against observed rate per bin.

    Bins are the score's own quantiles, so each holds about the same number
    of rows; the observed rate carries a Clopper–Pearson interval. A bin the
    quantiles could not separate, because the scores tie, is empty and is
    reported as NaN.
    """

    edges: tuple[float, ...]
    mean_score: tuple[float, ...]
    observed: tuple[float, ...]
    lo: tuple[float, ...]
    hi: tuple[float, ...]
    rows: tuple[int, ...]
    alpha: float = ALPHA


def reliability(outcome, score, *, bins: int = 10, alpha: float = ALPHA) -> Reliability:
    from scipy.stats import beta

    y, s = _outcome_and_score(outcome, score)
    edges = np.quantile(s, np.arange(1, bins) / bins)
    which = np.searchsorted(edges, s, side="right")
    mean_score, observed, lo, hi, rows = [], [], [], [], []
    for b in range(bins):
        mask = which == b
        n = int(mask.sum())
        rows.append(n)
        if n == 0:
            mean_score.append(float("nan"))
            observed.append(float("nan"))
            lo.append(float("nan"))
            hi.append(float("nan"))
            continue
        k = int(y[mask].sum())
        mean_score.append(float(s[mask].mean()))
        observed.append(k / n)
        lo.append(0.0 if k == 0 else float(beta.ppf(alpha / 2.0, k, n - k + 1)))
        hi.append(1.0 if k == n else float(beta.ppf(1.0 - alpha / 2.0, k + 1, n - k)))
    return Reliability(tuple(float(e) for e in edges), tuple(mean_score), tuple(observed),
                       tuple(lo), tuple(hi), tuple(rows), alpha)


# --- stability ----------------------------------------------------------------


@dataclass(frozen=True)
class PSI:
    """A population stability index and the bins it was read on."""

    value: float
    edges: tuple[float, ...]
    reference_share: tuple[float, ...]
    current_share: tuple[float, ...]
    critical: float
    alpha: float = ALPHA

    @property
    def bins(self) -> int:
        return len(self.reference_share)

    @property
    def exceeds(self) -> bool:
        return self.value > self.critical

    def as_dict(self) -> dict:
        return {
            "value": self.value,
            "critical": self.critical,
            "alpha": self.alpha,
            "bins": self.bins,
            "edges": list(self.edges),
            "reference_share": list(self.reference_share),
            "current_share": list(self.current_share),
        }


def psi_edges(reference, *, bins: int = PSI_BINS) -> np.ndarray:
    """The interior cut points that split the reference into `bins` quantile bins."""
    r = np.asarray(reference, dtype=float)
    if r.size == 0 or not np.isfinite(r).all():
        raise MetricError("the reference must be non-empty and finite")
    if bins < 2:
        raise MetricError("PSI needs at least two bins")
    return np.quantile(r, np.arange(1, bins) / bins)


def _shares(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    counts = np.bincount(np.searchsorted(edges, values, side="right"), minlength=edges.size + 1)
    return counts / values.size


def psi_critical(n_reference: int, n_current: int, *, bins: int = PSI_BINS, alpha: float = ALPHA) -> float:
    """Yurdakul's critical value: the (1 − alpha) quantile of (1/N + 1/M) χ²(B − 1).

    Under no shift, PSI on B bins between samples of N and M rows is
    asymptotically that scaled chi-square (Yurdakul 2018; Yurdakul and Naranjo
    2020). At the row counts of this study the value is of the order of a
    thousandth, so it separates "the book moved" from "sampling noise" and
    says nothing about how far it moved.
    """
    from scipy.stats import chi2

    if n_reference <= 0 or n_current <= 0:
        raise MetricError("both sample sizes must be positive")
    return float(chi2.ppf(1.0 - alpha, bins - 1) * (1.0 / n_reference + 1.0 / n_current))


def psi(reference, current, *, bins: int = PSI_BINS, alpha: float = ALPHA, edges=None) -> PSI:
    """PSI of `current` against `reference`, on bins fixed at the reference's deciles.

    The edges are the reference's quantiles unless given, so a bin holds a
    tenth of the reference and the index reads how the current distribution
    departs from that. A bin that is empty on one side and not the other makes
    the index infinite, which is what the definition says and is reported
    rather than smoothed away; with deciles of the reference it can only
    happen on the current side.
    """
    r = np.asarray(reference, dtype=float)
    c = np.asarray(current, dtype=float)
    if c.size == 0 or not np.isfinite(c).all():
        raise MetricError("the current sample must be non-empty and finite")
    cuts = psi_edges(r, bins=bins) if edges is None else np.asarray(edges, dtype=float)
    ref_share = _shares(r, cuts)
    cur_share = _shares(c, cuts)
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = (cur_share - ref_share) * np.log(cur_share / ref_share)
    # A bin empty on both sides contributes nothing rather than NaN.
    both_empty = (cur_share == 0) & (ref_share == 0)
    terms = np.where(both_empty, 0.0, terms)
    value = float(np.sum(terms))
    return PSI(
        value=value,
        edges=tuple(float(v) for v in cuts),
        reference_share=tuple(float(v) for v in ref_share),
        current_share=tuple(float(v) for v in cur_share),
        critical=psi_critical(r.size, c.size, bins=cuts.size + 1, alpha=alpha),
        alpha=alpha,
    )


# --- the published protocol's metrics ----------------------------------------
#
# The credit foundation-model benchmark reports log-loss and average
# precision beside the Brier score, and six classification metrics at the
# threshold that maximises F1 on a validation set. They are here so that the
# two protocols can be read on the same rows, and they are computed from
# their definitions rather than through a library so that an audit can
# re-derive them.


LOG_LOSS_CLIP = 1e-15


def log_loss(outcome, score, *, clip: float = LOG_LOSS_CLIP) -> float:
    """The mean negative log-likelihood of the outcome under the score.

    Probabilities are clipped away from zero and one by `clip` before the
    logarithm, as the reference implementations do, so a confident wrong
    score costs a large finite amount and not infinity.
    """
    y, s = _outcome_and_score(outcome, score)
    p = np.clip(s, clip, 1.0 - clip)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log1p(-p)))


def average_precision(outcome, score) -> float:
    """The area under the precision–recall curve as the step sum of precision over recall gains.

    Rows are taken in descending score; at every distinct score the
    precision of everything at or above it is weighted by the recall gained
    there, which is the definition the reference implementations use, and
    ties are handled by moving to the next distinct score rather than by a
    row at a time. NaN when there is no positive, since recall is then
    undefined.
    """
    y, s = _outcome_and_score(outcome, score)
    positives = int(y.sum())
    if positives == 0:
        return float("nan")
    order = np.argsort(-s, kind="stable")
    y_sorted = y[order]
    s_sorted = s[order]
    true_positive = np.cumsum(y_sorted)
    predicted_positive = np.arange(1, y.size + 1)
    # Keep the last row of every run of equal scores: the cut sits below it.
    last_of_tie = np.append(s_sorted[1:] != s_sorted[:-1], True)
    precision = true_positive[last_of_tie] / predicted_positive[last_of_tie]
    recall = true_positive[last_of_tie] / positives
    gained = np.diff(np.concatenate(([0.0], recall)))
    return float(np.sum(precision * gained))


@dataclass(frozen=True)
class Classification:
    """Six classification metrics at one threshold, with the threshold and what it cuts."""

    threshold: float
    predicted_positive_share: float
    accuracy: float
    balanced_accuracy: float
    f1: float
    precision: float
    recall: float
    mcc: float

    def as_dict(self) -> dict:
        return {
            "threshold": self.threshold,
            "predicted_positive_share": self.predicted_positive_share,
            "accuracy": self.accuracy,
            "balanced_accuracy": self.balanced_accuracy,
            "f1": self.f1,
            "precision": self.precision,
            "recall": self.recall,
            "mcc": self.mcc,
        }


def classification_at(outcome, score, threshold: float) -> Classification:
    """The confusion-matrix metrics with a row predicted positive at or above the threshold.

    Precision is zero when nothing is predicted positive, recall zero when
    there is no positive, and the Matthews coefficient zero when any margin
    of the table is empty; the reference implementations do the same.
    """
    y, s = _outcome_and_score(outcome, score)
    predicted = (s >= threshold).astype(int)
    tp = int(np.sum((predicted == 1) & (y == 1)))
    fp = int(np.sum((predicted == 1) & (y == 0)))
    fn = int(np.sum((predicted == 0) & (y == 1)))
    tn = int(np.sum((predicted == 0) & (y == 0)))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
    denominator = float(np.sqrt(float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)))
    mcc = (tp * tn - fp * fn) / denominator if denominator else 0.0
    return Classification(
        threshold=float(threshold),
        predicted_positive_share=float(predicted.mean()),
        accuracy=(tp + tn) / y.size,
        balanced_accuracy=(recall + specificity) / 2.0,
        f1=f1,
        precision=precision,
        recall=recall,
        mcc=float(mcc),
    )


def f1_threshold(outcome, score) -> float:
    """The score at which predicting positive at or above it maximises F1 on these rows.

    Every distinct score is a candidate cut; the first of any tie in F1 in
    descending score order is kept, so two runs on the same rows choose the
    same threshold. The threshold is meant to be chosen on one set of rows
    and applied to another, which is what the published protocol does with
    its validation fold.
    """
    y, s = _outcome_and_score(outcome, score)
    if y.sum() == 0:
        raise MetricError("no positive row; F1 is zero at every threshold")
    order = np.argsort(-s, kind="stable")
    y_sorted = y[order]
    s_sorted = s[order]
    true_positive = np.cumsum(y_sorted)
    predicted_positive = np.arange(1, y.size + 1)
    last_of_tie = np.append(s_sorted[1:] != s_sorted[:-1], True)
    tp = true_positive[last_of_tie]
    f1 = 2 * tp / (predicted_positive[last_of_tie] + int(y.sum()))
    best = int(np.argmax(f1))
    return float(s_sorted[last_of_tie][best])


# --- the noise floor ----------------------------------------------------------


@dataclass(frozen=True)
class ScoredCohort:
    """One cohort's shared rows, and every model's score on them.

    `outcome` is one value per row. `scores` maps a cell key to a vector on
    the same rows in the same order; a key is whatever the caller uses to name
    a (build, model) — a string, a tuple — and `seeds` maps the keys that
    exist in several context draws to the list of their per-draw score
    vectors, in the shared draw order, so that draw k of one model is the same
    context draw as draw k of another.
    """

    outcome: np.ndarray
    scores: Mapping[Any, np.ndarray] = field(default_factory=dict)
    seeds: Mapping[Any, Sequence[np.ndarray]] = field(default_factory=dict)
    # Which context draw a realised cohort carries; None until realised, so a
    # statistic can find the reference that belongs to the draw it was handed.
    draw: int | None = None

    def __post_init__(self) -> None:
        y = np.asarray(self.outcome)
        if y.ndim != 1 or y.size == 0:
            raise MetricError("a cohort needs a 1-d, non-empty outcome")
        for key, vector in self.scores.items():
            if np.asarray(vector).shape != y.shape:
                raise MetricError(f"scores for {key!r} are not aligned to the cohort's rows")
        for key, vectors in self.seeds.items():
            if not vectors:
                raise MetricError(f"{key!r} declares seeds but carries no draws")
            for vector in vectors:
                if np.asarray(vector).shape != y.shape:
                    raise MetricError(f"a draw of {key!r} is not aligned to the cohort's rows")
        object.__setattr__(self, "outcome", y.astype(int))

    @property
    def rows(self) -> int:
        return int(self.outcome.size)

    @property
    def draws(self) -> int:
        """How many context draws the seeded cells carry; one when none is seeded."""
        counts = {len(v) for v in self.seeds.values()}
        if len(counts) > 1:
            raise MetricError(f"seeded cells carry different draw counts: {sorted(counts)}")
        return counts.pop() if counts else 1

    def realise(self, draw: int, index: np.ndarray | None = None) -> ScoredCohort:
        """The cohort with one context draw chosen, and optionally its rows resampled."""
        pick = slice(None) if index is None else index
        scores = {key: np.asarray(v)[pick] for key, v in self.scores.items()}
        scores.update({key: np.asarray(v[draw])[pick] for key, v in self.seeds.items()})
        return ScoredCohort(self.outcome[pick], scores, {}, draw=draw)


Statistic = Callable[[Mapping[Any, ScoredCohort]], float]
Statistics = Callable[[Mapping[Any, ScoredCohort]], Mapping[str, float]]


@dataclass(frozen=True)
class Bootstrap:
    """A pooled statistic, its interval, and every draw that produced it."""

    value: float
    lo: float
    hi: float
    draws: tuple[float, ...]
    alpha: float = ALPHA
    resamples: int = RESAMPLES
    seed: int = 0

    @property
    def excludes_zero(self) -> bool:
        return self.lo > 0.0 or self.hi < 0.0

    @property
    def se(self) -> float:
        return float(np.std(self.draws, ddof=1)) if len(self.draws) > 1 else float("nan")

    def as_dict(self) -> dict:
        return {
            "value": self.value,
            "ci_lo": self.lo,
            "ci_hi": self.hi,
            "se": self.se,
            "alpha": self.alpha,
            "resamples": self.resamples,
            "seed": self.seed,
        }


def cohort_blocked_bootstrap_many(
    cohorts: Mapping[Any, ScoredCohort],
    statistics: Statistics,
    *,
    resamples: int = RESAMPLES,
    seed: int,
    alpha: float = ALPHA,
    resample_cohorts: bool = False,
) -> dict[str, Bootstrap]:
    """The intervals of several pooled statistics under one set of resamples.

    Each resample draws, within every cohort, `rows` positions with
    replacement and applies that one index to the outcome and to every score
    vector of that cohort — every model, every build — so that whatever the
    statistics pair stays paired. Where cells carry context draws, one draw is
    chosen per resample, uniformly and jointly, so the draws' spread enters
    the interval alongside the rows'. The point estimate is each statistic on
    the unresampled rows, averaged over the draws; the interval is the
    percentile interval of its resampled values.

    With the cohorts held fixed, which is the default, the interval says how
    far the pooled statistic could move under different loans inside the same
    cohorts. With `resample_cohorts`, each resample first draws as many
    cohorts as there are, with replacement, and then rows within each; the
    interval then also carries the movement between cohorts, and is the one
    to read against a statement about a cohort not in the pool. The pooled
    statistic receives the drawn cohorts under keys of the form
    `(key, position)`, so a cohort drawn twice enters twice.

    `statistics` receives the cohorts with the draw already chosen and
    returns a mapping of name to number, the same names on every call. It is
    called once per draw for the point and once per resample, so it should be
    the arithmetic and not the model; computing every statistic in one call
    is what lets a metric be evaluated once per cell per resample.
    """
    if resamples < 2:
        raise MetricError("a bootstrap needs at least two resamples")
    if not cohorts:
        raise MetricError("no cohorts")
    draws = {c.draws for c in cohorts.values()}
    if len(draws) > 1:
        raise MetricError(f"cohorts carry different draw counts: {sorted(draws)}")
    n_draws = draws.pop()

    def evaluate(sample: Mapping[Any, ScoredCohort]) -> dict[str, float]:
        result = dict(statistics(sample))
        if not result:
            raise MetricError("the statistics returned nothing")
        return result

    per_draw = [evaluate({key: c.realise(draw) for key, c in cohorts.items()})
                for draw in range(n_draws)]
    names = list(per_draw[0])
    point = {name: float(np.mean([d[name] for d in per_draw])) for name in names}

    rng = np.random.default_rng(seed)
    values = {name: np.empty(resamples) for name in names}
    keys = list(cohorts)
    for b in range(resamples):
        draw = int(rng.integers(n_draws))
        if resample_cohorts:
            picks = rng.integers(len(keys), size=len(keys))
            chosen = [(keys[i], (keys[i], j)) for j, i in enumerate(picks)]
        else:
            chosen = [(key, key) for key in keys]
        sample = {}
        for key, label in chosen:
            cohort = cohorts[key]
            index = rng.integers(cohort.rows, size=cohort.rows)
            sample[label] = cohort.realise(draw, index)
        result = evaluate(sample)
        if list(result) != names:
            raise MetricError("the statistics changed their names between calls")
        for name in names:
            values[name][b] = result[name]

    out = {}
    for name in names:
        lo, hi = np.quantile(values[name], [alpha / 2.0, 1.0 - alpha / 2.0])
        out[name] = Bootstrap(
            value=point[name], lo=float(lo), hi=float(hi),
            draws=tuple(float(v) for v in values[name]),
            alpha=alpha, resamples=resamples, seed=seed,
        )
    return out


def cohort_blocked_bootstrap(
    cohorts: Mapping[Any, ScoredCohort],
    statistic: Statistic,
    *,
    resamples: int = RESAMPLES,
    seed: int,
    alpha: float = ALPHA,
    resample_cohorts: bool = False,
) -> Bootstrap:
    """The interval of one pooled statistic; see `cohort_blocked_bootstrap_many`."""
    return cohort_blocked_bootstrap_many(
        cohorts, lambda sample: {"value": statistic(sample)},
        resamples=resamples, seed=seed, alpha=alpha, resample_cohorts=resample_cohorts,
    )["value"]


def paired_mean_difference(
    metric: Callable[[np.ndarray, np.ndarray], float], first: Any, second: Any
) -> Statistic:
    """A statistic: the mean over cohorts of metric(first) − metric(second).

    The two keys are cells of the same cohorts — two models on one build, or
    one model on two builds — and the difference is taken cell by cell before
    the mean, which is what makes it paired.
    """

    def pooled(cohorts: Mapping[Any, ScoredCohort]) -> float:
        gaps = [
            metric(c.outcome, c.scores[first]) - metric(c.outcome, c.scores[second])
            for c in cohorts.values()
        ]
        return float(np.mean(gaps))

    return pooled


def cohort_mean(metric: Callable[[np.ndarray, np.ndarray], float], key: Any) -> Statistic:
    """A statistic: the mean over cohorts of one cell's metric."""

    def pooled(cohorts: Mapping[Any, ScoredCohort]) -> float:
        return float(np.mean([metric(c.outcome, c.scores[key]) for c in cohorts.values()]))

    return pooled


def log_oe(outcome, score) -> float:
    """The log of observed over expected: zero when calibrated, symmetric either side."""
    y, s = _outcome_and_score(outcome, score)
    expected = float(s.mean())
    observed = float(y.mean())
    if expected <= 0.0 or observed <= 0.0:
        return float("nan")
    return float(np.log(observed / expected))
