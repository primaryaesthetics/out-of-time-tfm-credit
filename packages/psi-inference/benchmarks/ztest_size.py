#!/usr/bin/env python3
"""Null size and power of the delta-method PSI z-test beside the Yurdakul-Naranjo test.

The z-test is the one of Sudjianto and Burakov, arXiv:2509.09855, section 4:

    SE(IV) = sqrt( sum_j (p_b,j - p_g,j)^2 * (1/n_j,g + 1/n_j,b) )      eq. (18)
    H0: IV = 0,  H1: IV > 0                                             eq. (19)-(20)
    Z = IV / SE(IV) ~ N(0, 1) under H0                                  eq. (21)
    CI_{1-alpha}(IV) = IV +/- z_{alpha/2} * SE(IV)                      eq. (22)

carried to the PSI in section 4.5 ("IV = PSI for identical binning schemes").
Here the reference sample plays the role of the goods (g) and the current
sample the role of the bads (b); eq. (18) is symmetric in the two, so the
labelling does not matter.

The Yurdakul-Naranjo test is taken from this package itself
(`psi_statistic`, `psi_critical_value`, `psi_test`), not re-implemented.

Designs under H0:
  fixed_uniform   bins fixed in advance, both samples multinomial, equal shares
  fixed_skewed    bins fixed in advance, both samples multinomial, geometric
                  shares (a credit-grade-like monotone decay)
  ref_quantile    bins at the reference sample's own B-quantiles, so the
                  reference holds exactly n/B per bin; the current sample is
                  drawn from the same continuous distribution. By the
                  probability integral transform the distribution is
                  immaterial; the current sample's bin probabilities are the
                  uniform spacings between order statistics n/B, 2n/B, ...,
                  which are Dirichlet(n/B, ..., n/B, n/B + 1), and the current
                  counts are multinomial on them. `check_ref_quantile` compares
                  this representation with brute-force sorting.

Replications with a zero count in either sample are excluded and counted:
the PSI and eq. (18) are both infinite there, and the package refuses them.

Outputs ``results.csv``, one row per (cell, method, alpha), and
``environment.txt``, the versions the cells were drawn under.

    pip install -e .
    python benchmarks/ztest_size.py --out-dir benchmarks/ztest_size

The committed ``benchmarks/ztest_size/results.csv`` is the output of this
command with the seed below; a rerun reproduces it.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from scipy import stats

import psi_inference
from psi_inference import psi_critical_value, psi_statistic, psi_test

SEED = 20260914
REPS_NULL = 50_000
REPS_POWER = 20_000
ALPHAS = (0.05, 0.01)
SIZES = ((1_000, 1_000), (5_000, 5_000), (50_000, 20_000), (50_000, 50_000))
BINS = (10, 20)
DESIGNS = ("fixed_uniform", "fixed_skewed", "ref_quantile")
SHIFTS = (0.01, 0.02)
THRESHOLDS = (0.10, 0.25)


def shares(design: str, bins: int) -> np.ndarray:
    if design in ("fixed_uniform", "ref_quantile"):
        return np.full(bins, 1.0 / bins)
    ratio = {10: 0.75, 20: 0.85}[bins]
    w = ratio ** np.arange(bins)
    return w / w.sum()


def draw(rng, design, bins, n, m, reps, current_shares=None):
    """Reference and current count matrices, shape (reps, bins)."""
    pi = shares(design, bins)
    if design == "ref_quantile":
        k = n // bins
        ref = np.full((reps, bins), k, dtype=np.int64)
        alpha_dir = np.full(bins, float(k))
        alpha_dir[-1] += 1.0
        spacings = rng.dirichlet(alpha_dir, size=reps)
        cur = np.empty((reps, bins), dtype=np.int64)
        for r in range(reps):
            cur[r] = rng.multinomial(m, spacings[r])
        return ref, cur
    ref = rng.multinomial(n, pi, size=reps)
    cur = rng.multinomial(m, pi if current_shares is None else current_shares, size=reps)
    return ref, cur


def z_statistic(ref: np.ndarray, cur: np.ndarray, psi: np.ndarray) -> np.ndarray:
    """Eq. (18) and (21), vectorised over replications."""
    n = ref.sum(axis=1, keepdims=True)
    m = cur.sum(axis=1, keepdims=True)
    p_g = ref / n
    p_b = cur / m
    se = np.sqrt(np.sum((p_b - p_g) ** 2 * (1.0 / ref + 1.0 / cur), axis=1))
    return psi / se


def psi_vector(ref: np.ndarray, cur: np.ndarray) -> np.ndarray:
    p = ref / ref.sum(axis=1, keepdims=True)
    q = cur / cur.sum(axis=1, keepdims=True)
    return np.sum((p - q) * (np.log(p) - np.log(q)), axis=1)


def run_cell(rng, hypothesis, design, bins, n, m, reps, shift=0.0):
    cur_shares = None
    if shift:
        cur_shares = shares(design, bins).copy()
        cur_shares[0] -= shift
        cur_shares[1] += shift
    ref, cur = draw(rng, design, bins, n, m, reps, cur_shares)
    keep = (ref > 0).all(axis=1) & (cur > 0).all(axis=1)
    excluded = int((~keep).sum())
    ref, cur = ref[keep], cur[keep]
    used = ref.shape[0]

    # The package's statistic on every replication; the vectorised copy is only
    # used for the z-test's numerator and must agree with it.
    psi_pkg = np.array([psi_statistic(a, b) for a, b in zip(ref, cur)])
    psi_vec = psi_vector(ref, cur)
    assert np.max(np.abs(psi_pkg - psi_vec)) < 1e-12
    z = z_statistic(ref, cur, psi_pkg)

    for a, b in zip(ref[:200], cur[:200]):
        t = psi_test(a, b, alpha=0.05)
        assert t.reject == (psi_statistic(a, b) > psi_critical_value(n, m, bins, 0.05))

    common = {
        "hypothesis": hypothesis, "design": design, "B": bins, "n": n, "m": m,
        "n_eff": round(n * m / (n + m), 1), "shift": shift,
        "reps_drawn": reps, "reps_used": used, "zero_count_excluded": excluded,
        "z_mean": float(z.mean()), "z_sd": float(z.std(ddof=1)),
        "z_sq_mean": float((z**2).mean()),
        "psi_over_scale_mean": float((psi_pkg / (1 / n + 1 / m)).mean()),
    }
    rows = []

    def add(method, alpha, rejected, prediction=""):
        k = int(rejected.sum())
        rate = k / used
        rows.append(dict(common, method=method, alpha=alpha, rejections=k,
                         rate=rate, mc_se=np.sqrt(rate * (1 - rate) / used),
                         asymptotic_prediction=prediction))

    for alpha in ALPHAS:
        z1 = stats.norm.ppf(1 - alpha)
        z2 = stats.norm.ppf(1 - alpha / 2)
        add("z_one_sided", alpha, z > z1, float(stats.chi2.sf(z1**2, bins - 1)))
        add("z_two_sided", alpha, np.abs(z) > z2, float(stats.chi2.sf(z2**2, bins - 1)))
        crit = psi_critical_value(n, m, bins, alpha)
        add("yurdakul", alpha, psi_pkg > crit, alpha)
        add("z_squared_vs_chi2", alpha, z**2 > stats.chi2.ppf(1 - alpha, bins - 1), alpha)
    for thr in THRESHOLDS:
        add(f"psi_gt_{thr:.2f}", "", psi_pkg > thr)
    return rows


def check_ref_quantile(rng, n=1_000, m=1_000, bins=10, reps=4_000):
    """Dirichlet-spacings representation against sorting actual samples."""
    brute = np.empty(reps)
    for r in range(reps):
        x = rng.random(n)
        y = rng.random(m)
        edges = np.sort(x)[np.arange(1, bins) * (n // bins) - 1]
        ref = np.bincount(np.searchsorted(edges, x, side="left"), minlength=bins)
        cur = np.bincount(np.searchsorted(edges, y, side="left"), minlength=bins)
        assert (ref == n // bins).all()
        brute[r] = psi_statistic(ref, cur)
    ref, cur = draw(rng, "ref_quantile", bins, n, m, reps)
    fast = psi_vector(ref, cur)
    ks = stats.ks_2samp(brute, fast)
    return float(brute.mean()), float(fast.mean()), float(ks.pvalue)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    root = np.random.SeedSequence(SEED)
    cells = []
    for design in DESIGNS:
        for bins in BINS:
            for n, m in SIZES:
                cells.append(("null", design, bins, n, m, REPS_NULL, 0.0))
    for design in ("fixed_uniform", "fixed_skewed"):
        for bins in BINS:
            for n, m in SIZES:
                for shift in SHIFTS:
                    cells.append(("shift", design, bins, n, m, REPS_POWER, shift))
    children = root.spawn(len(cells) + 1)

    brute_mean, fast_mean, ks_p = check_ref_quantile(np.random.default_rng(children[-1]))
    print(f"ref_quantile check: brute mean PSI {brute_mean:.6f}, "
          f"Dirichlet mean PSI {fast_mean:.6f}, KS p = {ks_p:.3f}")

    rows = []
    for cell, child in zip(cells, children):
        hyp, design, bins, n, m, reps, shift = cell
        rows += run_cell(np.random.default_rng(child), hyp, design, bins, n, m, reps, shift)
        print(hyp, design, bins, n, m, shift, "done", flush=True)

    fields = list(rows[0].keys())
    with open(out / "results.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})
    with open(out / "environment.txt", "w") as fh:
        fh.write(f"python {sys.version.split()[0]}\nnumpy {np.__version__}\n")
        fh.write(f"scipy {sys.modules['scipy'].__version__}\n")
        fh.write(f"psi_inference {psi_inference.__version__}\n")
        fh.write(f"seed {SEED}\nreps_null {REPS_NULL}\nreps_power {REPS_POWER}\n")
        fh.write(f"ref_quantile check: brute mean {brute_mean:.6f}, "
                 f"Dirichlet mean {fast_mean:.6f}, KS p {ks_p:.3f}\n")
    print(f"\nwritten: {out.as_posix()} ({len(rows)} rows over {len(cells)} cells)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
