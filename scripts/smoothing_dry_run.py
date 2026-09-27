#!/usr/bin/env python3
"""Dry run of the smoothing reading on synthetic cells, with the repository's own Cox fit and bootstrap.

The reading under test: per foundation model, the signed Cox slope at softmax
temperature 1.0 minus the scorecard's, paired by cell and pooled as H2 pools
(the mean over cells, cohorts held fixed, 200 resamples), with the model's
own pooled signed slope beside it. It is meant to catch under-dispersion of
the predicted logit -- "probabilities smoothed toward the mean" -- and to
ignore a level shift, a drift the book does to every model alike, and a
model whose slope sits at one or at the scorecard's.

Synthetic book. The true logit is eta = a + x1 + x2 with x1, x2 independent
normals; the outcome is Bernoulli(expit(eta)). The scorecard sees x1 and
scores P(y | x1), the foundation model sees x2 and scores P(y | x2), each
integrated over the unseen factor by Gauss-Hermite quadrature, so both are
exactly calibrated (Cox intercept 0, slope 1) on the rows they score and
differ from each other on every row. A treatment is then applied to the
foundation model's logit, or to the outcomes:

  calibrated   nothing                                        must not fire
  level        logit + ln(2/3), the two-thirds level of 0.9   must not fire
  drift        outcomes drawn from a stretched, shifted eta,  must not fire on the
               both models stale alike                        paired difference
  smooth-0.85  logit shrunk toward the cell's mean logit by   must fire
               0.85: slope 1/0.85 = 1.176
  smooth-0.95  the same at 0.95: slope 1.053, the minimum     at the threshold
               effect of the reading
  over-1.15    logit stretched by 1.15: slope 0.870           must read the other way
  memorised    in-sample: logit + 0.25 (2y - 1), a context    direction to be read:
               row pulled toward its own label                a label in view makes
                                                              the outcome more
                                                              predictable than the
                                                              logit says, so the fit
                                                              stretches it (above one)
  smooth+mem   0.85 shrink and the memorising pull together   whether the two add or
                                                              cancel: the in-sample
                                                              asymmetry

The row at the shipped 0.9 is logit / 0.9, whose Cox slope is 0.9 times the
slope at 1.0 by arithmetic; it is printed from the point estimate and not
bootstrapped again.

Cell sizes: one cell at EXP-005's floors (5,000 loans, about 100 defaults)
with its Wald interval and a bootstrap over its rows; poolings of 36 cells of
12,000 rows at 2 percent prevalence, about 240 defaults a cell, which is the
default count of a 24,000-loan half-year cohort of this book at 1 percent
and 2002H2-E's criterion cell count; and the calibrated and threshold cases
at the arm's 196 cells. The 36-cell poolings run under the primary bootstrap
seed 20260905, the threshold case also under the check seeds 20260906 and
20260907. Scenarios run in parallel processes; each is deterministic.
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from numpy.polynomial.hermite_e import hermegauss
from scipy.special import expit, logit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_intervals as bi

from outoftime import metrics as mt

SEEDS = (bi.BOOTSTRAP_SEED, 20260906, 20260907)
RESAMPLES = mt.RESAMPLES
MINIMUM_EFFECT = 0.05
SD1, SD2 = 0.8, 0.8
NODES, WEIGHTS = hermegauss(40)
WEIGHTS = WEIGHTS / WEIGHTS.sum()
MODELS = ("scorecard", "tfm@t1")


def calibrated(seen: np.ndarray, a: float, unseen_sd: float) -> np.ndarray:
    """P(y = 1 | seen) = E_u expit(a + seen + u), u ~ N(0, unseen_sd^2), by quadrature."""
    return (expit(a + seen[:, None] + unseen_sd * NODES[None, :]) * WEIGHTS[None, :]).sum(axis=1)


def intercept_for(prevalence: float) -> float:
    """The a at which E expit(a + x1 + x2) equals the prevalence."""
    sd = float(np.hypot(SD1, SD2))
    lo, hi = -15.0, 5.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if float((expit(mid + sd * NODES) * WEIGHTS).sum()) < prevalence:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def shrink(ell: np.ndarray, factor: float) -> np.ndarray:
    """The logit pulled toward the cell's own mean logit: smoothing toward the mean."""
    m = float(logit(expit(ell).mean()))
    return m + factor * (ell - m)


def make_cells(rng: np.random.Generator, n_cells: int, rows: int, prevalence,
               treatment: str) -> dict[str, mt.ScoredCohort]:
    cohorts = {}
    for i in range(n_cells):
        p = prevalence if np.isscalar(prevalence) else float(rng.uniform(*prevalence))
        a = intercept_for(p)
        x1 = rng.normal(0.0, SD1, rows)
        x2 = rng.normal(0.0, SD2, rows)
        eta = a + x1 + x2
        if treatment == "drift":
            # The book moved: risk differentiation stretched by 1.15 and the level
            # shifted up by 0.3 on the logit. Both models keep their stale scores.
            eta_out = eta.mean() + 1.15 * (eta - eta.mean()) + 0.3
        else:
            eta_out = eta
        y = (rng.uniform(size=rows) < expit(eta_out)).astype(int)
        while y.sum() < 2 or y.sum() > rows - 2:
            y = (rng.uniform(size=rows) < expit(eta_out)).astype(int)
        p_s = calibrated(x1, a, SD2)
        p_t = calibrated(x2, a, SD1)
        ell = logit(p_t)
        if treatment == "level":
            ell = ell + np.log(2.0 / 3.0)
        elif treatment.startswith(("smooth-", "over-")):
            ell = shrink(ell, float(treatment.split("-")[1]))
        elif treatment == "memorised":
            ell = ell + 0.25 * (2 * y - 1)
        elif treatment == "smooth+mem":
            ell = shrink(ell, 0.85) + 0.25 * (2 * y - 1)
        elif treatment not in ("calibrated", "drift"):
            raise ValueError(treatment)
        cohorts[f"cell{i:03d}"] = mt.ScoredCohort(y, {"scorecard": p_s, "tfm@t1": expit(ell)})
    return cohorts


def signed_slope(outcome, score) -> float:
    fit = mt.cox(outcome, score)
    return fit.slope if fit.converged else float("nan")


def pooled(cohorts):
    """The proposed statistic: per model the mean signed slope over cells, and the paired difference."""
    per = {m: [] for m in MODELS}
    for c in cohorts.values():
        for m in MODELS:
            per[m].append(signed_slope(c.outcome, c.scores[m]))
    values = np.array([per[m] for m in MODELS], dtype=float)
    keep = np.isfinite(values).all(axis=0)
    out = {f"slope|{m}": bi.paired_mean(per[m], keep) for m in MODELS}
    out["diff|tfm@t1|scorecard"] = out["slope|tfm@t1"] - out["slope|scorecard"]
    out["left_out"] = float((~keep).sum())
    return out


def verdict(diff: mt.Bootstrap, slope: mt.Bootstrap, stars_all: bool = True) -> str:
    """The reading EXP-005 fixes: supports, contradicts, or neither."""
    above = diff.lo > 0.0 and slope.lo > 1.0
    if above and diff.value >= MINIMUM_EFFECT and not stars_all:
        return "holds zero at the margin: a check seed loses the star"
    if above and diff.value >= MINIMUM_EFFECT:
        return "SUPPORTS: under-dispersed beyond the scorecard, at or above the minimum effect"
    if above:
        return "direction only: a star under the minimum effect"
    if diff.hi < 0.0 or slope.hi < 1.0:
        return "CONTRADICTS: over-dispersed relative to the scorecard, or below one"
    return "no reading: the interval holds zero"


def fmt(b: mt.Bootstrap) -> str:
    return f"{b.value:+.3f} [{b.lo:+.3f}, {b.hi:+.3f}]"


def run_pooling(name: str, treatment: str, n_cells: int, rows: int, prevalence, seeds) -> dict:
    """One scenario: the cells, the bootstrap under each seed, the reading."""
    rng = np.random.default_rng(7)
    cohorts = make_cells(rng, n_cells, rows, prevalence, treatment)
    defaults = [int(c.outcome.sum()) for c in cohorts.values()]
    started = time.time()
    results = {seed: mt.cohort_blocked_bootstrap_many(cohorts, pooled, resamples=RESAMPLES,
                                                      seed=seed) for seed in seeds}
    primary = results[seeds[0]]
    d, s = primary["diff|tfm@t1|scorecard"], primary["slope|tfm@t1"]
    stars = "".join("*" if results[x]["diff|tfm@t1|scorecard"].excludes_zero else "." for x in seeds)
    stars_all = all(results[x]["diff|tfm@t1|scorecard"].excludes_zero for x in seeds)
    lines = [(f"\n[{name}] {treatment}: {n_cells} cells x {rows:,} rows, defaults {min(defaults)}-"
              f"{max(defaults)} per cell, {RESAMPLES} resamples, seeds {list(seeds)}, "
              f"{time.time() - started:.0f}s")]
    for m in MODELS:
        lines.append(f"  slope {m:<10} {fmt(primary[f'slope|{m}'])}")
    lines.append(f"  tfm@t1 - scorecard {fmt(d)}  star by seed {stars}")
    lines.append(f"  the same model at the shipped 0.9: slope {0.9 * s.value:.3f}, "
                 f"difference {0.9 * s.value - primary['slope|scorecard'].value:+.3f}")
    v = verdict(d, s, stars_all)
    lines.append(f"  reading at 1.0: {v}")
    lines.append(f"  left out of the pairing: {primary['left_out'].value:g} cells")
    return {"name": name, "treatment": treatment, "cells": n_cells, "rows": rows, "diff": d,
            "slope": s, "verdict": v, "text": "\n".join(lines)}


def run_single_cell(treatment: str, rows: int = 5000, prevalence: float = 0.02) -> str:
    """One cell at the floors: the Wald interval on each slope, the bootstrap on the difference."""
    rng = np.random.default_rng(11)
    (cell,) = make_cells(rng, 1, rows, prevalence, treatment).values()
    fits = {m: mt.cox(cell.outcome, cell.scores[m]) for m in MODELS}
    boot = mt.cohort_blocked_bootstrap_many({"cell": cell}, pooled, resamples=RESAMPLES,
                                            seed=SEEDS[0])
    lines = [f"\n[floor cell] {treatment}: {rows:,} rows, {int(cell.outcome.sum())} defaults"]
    for m in MODELS:
        f = fits[m]
        lines.append(f"  slope {m:<10} {f.slope:.3f} Wald [{f.slope_interval.lo:.3f}, "
                     f"{f.slope_interval.hi:.3f}], se {f.slope_se:.3f}")
    d = boot["diff|tfm@t1|scorecard"]
    lines.append(f"  tfm@t1 - scorecard {fmt(d)}  bootstrap over the cell's rows; "
                 f"reading: {verdict(d, boot['slope|tfm@t1'])}")
    return "\n".join(lines)


def main() -> int:
    started = time.time()
    print("smoothing reading, dry run on synthetic cells")
    print("Cox fit and bootstrap: outoftime.metrics; pooling helper: build_intervals.paired_mean")
    print(f"minimum effect on the paired signed-slope difference: {MINIMUM_EFFECT}")

    rng = np.random.default_rng(1)
    (big,) = make_cells(rng, 1, 400_000, 0.015, "calibrated").values()
    for m in MODELS:
        f = mt.cox(big.outcome, big.scores[m])
        print(f"  construction check, 400,000 rows, {m}: intercept {f.intercept:+.4f}, "
              f"slope {f.slope:.4f} +- {f.slope_se:.4f}; "
              f"AUC {mt.auc(big.outcome, big.scores[m]):.3f}")
    f = mt.cox(big.outcome, expit(logit(big.scores["tfm@t1"]) / 0.9))
    print(f"  the same model at 0.9: slope {f.slope:.4f} (0.9 x the slope at 1.0)")

    for treatment in ("calibrated", "smooth-0.85", "smooth-0.95"):
        print(run_single_cell(treatment))

    cell36 = (36, 12_000, 0.02)
    jobs = [("36 cells", t, *cell36, SEEDS[:1])
            for t in ("calibrated", "level", "drift", "smooth-0.85", "over-1.15")]
    jobs.append(("36 cells", "smooth-0.95", *cell36, SEEDS))
    jobs += [("196 cells", t, 196, 12_000, 0.02, SEEDS[:1]) for t in ("calibrated", "smooth-0.95")]
    jobs += [("in-sample, 9 contexts", t, 9, 50_000, (0.0096, 0.0176), SEEDS[:1])
             for t in ("calibrated", "memorised", "smooth-0.85", "smooth+mem")]
    with ProcessPoolExecutor(max_workers=8) as pool:
        table = list(pool.map(run_pooling, *zip(*jobs)))
    for r in table:
        print(r["text"])

    print("\nsummary (reading at 1.0; the slope at 0.9 is 0.9 x the slope at 1.0):")
    print(f"  {'case':<22} {'cells':>5} {'tfm - scorecard':>26} {'tfm slope at 1.0':>26}  verdict")
    for r in table:
        print(f"  {r['treatment']:<22} {r['cells']:>5} {fmt(r['diff']):>26} "
              f"{fmt(r['slope']):>26}  {r['verdict']}")
    print(f"\nwall {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
