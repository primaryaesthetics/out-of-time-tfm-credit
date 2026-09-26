# psi-inference

[![PyPI](https://img.shields.io/pypi/v/psi-inference.svg)](https://pypi.org/project/psi-inference/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22342343.svg)](https://doi.org/10.5281/zenodo.22342343)

Critical values and p-values for population stability testing in credit risk
monitoring: pure numpy and scipy, no pandas dependency, Python 3.11+.

A model built on one population gets used on another one later, and the
question a monitoring report has to answer is whether the two still look
alike. The population stability index (PSI) is the standard tool for this,
and the standard reading of it is a pair of constants: below 0.10 is fine,
above 0.25 needs a rebuild. Those constants do not know the sample size or
the number of bins the PSI was computed on, so the same reading means
different things on a 500-row book and a 500,000-row one. This package
implements the statistics that do know it.

## Example

```python
import numpy as np
from psi_inference import psi_test

# Seven credit grades: the base sample and a later monitoring sample.
base = np.array([253, 302, 204, 134, 72, 26, 8])      # 999 accounts
current = np.array([177, 262, 285, 158, 88, 25, 6])    # 1001 accounts

result = psi_test(base, current, alpha=0.05)
print(result.statistic)        # 0.0677
print(result.critical_value)   # 0.0252
print(result.p_value)          # 7.2e-06
print(result.reject)           # True
```

Read against the 0.10 rule of thumb, 0.068 says nothing has changed. This
sample has seven categories and about a thousand rows on each side. At 5%
significance the critical value here is 0.025. The observed PSI is more than
two and a half times that. The p-value says the same thing in one number: a
shift this large would happen by chance in roughly seven per hundred
thousand comparisons if the population had not moved at all. The rule of
thumb and the correctly sized test disagree here. On this sample size, the
test is the one with a stated error rate.

## Critical values

At alpha = 0.05, from `psi_critical_value(n, m, bins, alpha=0.05)`:

| n = m     | B = 10  | B = 20  |
| --------- | ------- | ------- |
| 1,000     | 0.0338  | 0.0603  |
| 10,000    | 0.0034  | 0.0060  |
| 100,000   | 0.0003  | 0.0006  |

The critical value falls by roughly an order of magnitude for each order of
magnitude of sample size, and rises with the number of bins. A PSI of 0.05
is a strong signal at 100,000 rows per side and unremarkable at 1,000. Fixed
thresholds cannot see either fact.

## Why 0.10 and 0.25 are not thresholds

The 0.10 / 0.25 pair comes from Lewis (1994) as a rule of thumb, with no
stated error rate and no dependence on how much data the PSI was computed on.
Yurdakul and Naranjo (2020) show that under the hypothesis of no population
shift, PSI is approximately distributed as (1/n + 1/m) times a chi-square
random variable with B − 1 degrees of freedom. Here n and m are the two
sample sizes and B is the number of bins. That scale factor is exactly what
the fixed thresholds throw away. The practical consequence is two-sided: a
small monitoring sample crosses 0.10 routinely on pure sampling noise, and a
large one can move by an amount that would fail any honest test while never
approaching 0.25. Reporting a PSI against 0.10 or 0.25 is reporting a number
against constants that were never fit to this sample size, this bin count,
or any stated tolerance for being wrong.

## Why not a z-test on the PSI

Sudjianto and Burakov, "An Information-Theoretic Framework for Credit Risk
Modeling: Unifying Industry Practice with Statistical Theory for Fair and
Interpretable Scorecards" (arXiv:2509.09855, section 4), derive a
delta-method standard error for the information value,
SE(IV) = sqrt( sum_j (p_b,j − p_g,j)² (1/n_j,g + 1/n_j,b) ), and test
H0: IV = 0 against H1: IV > 0 with Z = IV / SE(IV) referred to the standard
normal. Section 4.5 carries the same test to the PSI, "where drift detection
becomes a hypothesis testing problem with controlled Type I and Type II
error rates". The Type I error rate is not controlled. With no population
shift at all, the one-sided test at nominal 5% rejects in 97.4–97.6% of
samples with 10 bins and, with 20 bins, in every sample but one:

| rejection rate under no shift, nominal 5% | B = 10        | B = 20          |
| ----------------------------------------- | ------------- | --------------- |
| z-test, one-sided                         | 0.974 – 0.976 | 1.000           |
| z-test, two-sided                         | 0.921 – 0.923 | 0.9999 – 1.0000 |
| Yurdakul–Naranjo (`psi_test`)             | 0.049 – 0.054 | 0.049 – 0.063   |

Each range runs over twelve cells: three binnings (equal shares fixed in
advance, geometrically decaying shares fixed in advance, and bins at the
reference sample's own deciles or vingtiles) and four sample-size pairs,
1,000 against 1,000, 5,000 against 5,000, 50,000 against 20,000 and 50,000
against 50,000. The two-sided row is the paper's confidence interval
(equation 22) read as a test. Every cell is 50,000 simulated sample pairs,
so the Monte Carlo standard error of a rate in the table is below 0.0013. Neither sample size nor the choice of bin shares moves the z-test's
rate; at nominal 1% the one-sided test rejects in 79.6–79.9% of samples with
10 bins and 99.9% with 20. The Yurdakul–Naranjo test holds 4.9–5.2% from
5,000 rows per side; its worst cell is 6.3%, at 1,000 rows per side with 20
bins and skewed shares.

The reason is structural. The PSI is zero exactly when the two distributions
coincide and grows quadratically away from that point, so its first
derivative vanishes at the null and the first-order delta method has nothing
to propagate: the sampling distribution there is a quadratic form, which is
why the Yurdakul–Naranjo null is a chi-square and not a normal. The paper's
formula gets past the zero derivative by holding the weights
w_j = p_b,j − p_g,j fixed (its equation 17) and propagating only the
variance of the WoE terms, so the plug-in standard error is evaluated at
observed differences that are pure sampling noise under the null. Write π_j
for the common bin probability. Then n_j,g ≈ n π_j and n_j,b ≈ m π_j, so
1/n_j,g + 1/n_j,b ≈ (1/n + 1/m) / π_j and
SE² ≈ (1/n + 1/m) × sum_j (p_b,j − p_g,j)² / π_j. That sum is the PSI to
leading order, since log p_b,j − log p_g,j ≈ (p_b,j − p_g,j) / π_j. So
SE² ≈ (1/n + 1/m) × PSI, and Z² = PSI² / SE² ≈ PSI / (1/n + 1/m), which is
the Yurdakul–Naranjo statistic and is asymptotically chi-square with B − 1
degrees of freedom under the null. Z itself is then roughly a chi variable
on B − 1 degrees of freedom: nonnegative, mean 2.9 for 10 bins, and with
the standard-normal critical value of 1.645 at its 2.5th percentile, so
almost every sample lands above it. The simulation agrees: the mean of Z²
is 8.9–9.0 for 10 bins and 18.4–19.0 for 20, against B − 1 = 9 and 19, and
the chi-square prediction of the one-sided 5% rejection rate with 10 bins
is 0.975. Referring Z² to the chi-square critical value instead of 1.645²
brings the rate back to 4.7–5.2% from 5,000 rows per side (3.3–5.1% at
1,000, where the expected counts in the smallest skewed bins fall to about
seven), which is this package's test with a noisier scale estimate.

The z-test's power is uninformative for the same reason. The shifted cells
move one or two percentage points of mass from the first bin into the
second, for both fixed binnings, both bin counts and all four sample-size
pairs, 20,000 simulated pairs per cell. Against a one-point shift between
two of ten equal bins, the Yurdakul–Naranjo test rejects in 8.9%, 29.0%,
98.1% and all but one of the samples at 1,000 against 1,000, 5,000 against
5,000, 50,000 against 20,000 and 50,000 against 50,000; the z-test rejects
in 97.8% or more of samples in every shifted cell, against 97.4% or more
with no shift.

Replications with an empty bin on either side, where both the PSI and the
standard error are infinite, are excluded and counted: 109 of 50,000 in one
null cell (1,000 rows per side, 20 bins with skewed shares), 43 and 40 of
20,000 in the two shifted cells of the same shape, none elsewhere.

The simulation is `benchmarks/ztest_size.py`, run against version 0.1.0 of
this package with seed 20260914; its output is committed beside it in
`benchmarks/ztest_size/results.csv`, and a rerun reproduces that file.

## What this package implements

- **PSI** (`psi_statistic`, `psi_critical_value`, `psi_pvalue`, `psi_test`):
  Yurdakul, B. and Naranjo, J. (2020), "Statistical properties of the
  population stability index", *Journal of Risk Model Validation* 14(4),
  89-100, section 3 (theorems 3.1-3.3) and section 4 (equation 4.1). Two
  other Python packages compute the same asymptotic critical value, `iyipada`
  and `feature-engine`'s `DropHighPSIFeatures(threshold="auto")`; this module
  is checked against both in `tests/test_cross_check.py` and is included here
  for completeness, not as a new result.
- **PRS** (`prs_statistic`, `prs_delta`, `prs_thresholds`, `prs_classify`):
  the Population Resemblance Statistic of Potgieter, C.J., Van Zyl, C.,
  Schutte, W.D. and Lombard, F., "The Population Resemblance Statistic: A
  Chi-Square Measure of Fit for Banking" (arXiv:2307.11878). Compares one
  sample against a fixed reference population rather than two samples
  against each other, and gives sample-size-calibrated critical values from
  the non-central chi-square distribution, plus a three-tier decision
  (acceptable / partial / full discrepancy) instead of a single cutoff.
- **Effect-size test** (`effect_size_statistic`, `effect_size_critical_value`,
  `effect_size_pvalue`) and **overlapping test** (`overlapping_statistic`,
  `overlapping_critical_value`, `overlapping_pvalue`): Du Pisanie, J.,
  Allison, J.S., Budde, C.J. and Visagie, I.J.H., "A critical review of
  existing and new population stability testing procedures in credit risk
  scoring" (arXiv:2303.01227), sections 3.6 and 3.7. The effect-size
  statistic does not grow with sample size, which is the failure mode of the
  classical goodness-of-fit tests on a bank-sized book. The overlapping
  statistic reports the share of probability mass two distributions hold in
  common, which needs no explanation of a p-value to a non-technical
  audience.

None of these three had a Python implementation before this package.
In R, `rpsi` implements the Yurdakul-Naranjo critical value and a multinomial
confidence interval, and `PDtoolkit::psi` the same chi-square value beside a
normal approximation of it; neither goes beyond the critical value.
`PDtoolkit` is on CRAN. `rpsi` is on GitHub only.

## Installing and running the tests

```
pip install psi-inference
```

To run the tests from a checkout:

```
uv venv --python 3.12
uv pip install -e ".[dev]"
uv run pytest
```

The test suite includes a Monte Carlo gate. It simulates the null directly
for several sample sizes and bin counts, including a small sample (500 rows)
and unequal sample sizes (50,000 against 2,000). It checks that the
empirical 95th percentile of the simulated statistic matches the analytic
critical value within simulation error for the PSI and for the PRS. A
formula recalled wrong from the paper produces a number, not an error. This
is the check that catches it.

## Notes on the sources

Every formula in this package is pinned by a test to a worked example
printed in its source paper: the PSI to Yurdakul and Naranjo's seven-grade
example and to their critical-value tables for B = 10 and B = 20; the PRS to
the four (sample size, bin count) cases of the source paper's critical-value
table; the effect-size and overlapping statistics to the paper's example of
a two-category shift from 50/50 to 50.5/49.5. Each matches to the digits the
source prints, and the test names say which table.

The PSI null agrees everywhere it was checked: Yurdakul and Naranjo's own
equation, the `rpsi` R source, `iyipada` and `feature-engine` all reduce to
the same line, `chi2.ppf(1 - alpha, bins - 1) * (1/n + 1/m)`. `rpsi` also
offers a mode that treats the base distribution as a fixed population rather
than a random sample, which drops the `1/n` term. That mode is not
implemented here. The PRS covers the fixed-reference case with a null that
is built for it.

## Citing

The package is archived on Zenodo. The concept DOI 10.5281/zenodo.22342343
resolves to the latest version; the DOI of version 0.1.0 is
10.5281/zenodo.22342344. `CITATION.cff` in the repository carries the full
record.

## Licence

MIT.
