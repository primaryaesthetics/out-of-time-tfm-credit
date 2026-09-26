"""Critical values and p-values for population stability testing.

Four statistics used to test whether the population a model scores today
still resembles the one it was built on, each with the inference the
rule-of-thumb thresholds of 0.10 and 0.25 never had:

- `psi_statistic`, `psi_critical_value`, `psi_pvalue`, `psi_test` --
  the population stability index, tested against Yurdakul and Naranjo's
  (2020) asymptotic chi-square null.
- `prs_statistic`, `prs_delta`, `prs_thresholds`, `prs_classify` --
  the Population Resemblance Statistic of Potgieter, Van Zyl, Schutte and
  Lombard (arXiv:2307.11878), a fixed-reference alternative with
  sample-size-calibrated critical values from the non-central chi-square.
- `effect_size_statistic`, `effect_size_critical_value`, `effect_size_pvalue` --
  the category-level effect-size test of Du Pisanie, Allison, Budde and
  Visagie (arXiv:2303.01227), which does not grow with sample size.
- `overlapping_statistic`, `overlapping_critical_value`, `overlapping_pvalue` --
  the overlapping statistic from the same paper, the share of probability
  mass two distributions hold in common.

See the README for which statistic to reach for and why 0.10/0.25 are not
thresholds.
"""

from .effect_size import (
    effect_size_critical_value,
    effect_size_per_category,
    effect_size_pvalue,
    effect_size_statistic,
)
from .overlapping import (
    overlapping_critical_value,
    overlapping_pvalue,
    overlapping_statistic,
)
from .prs import (
    PRSThresholds,
    prs_classify,
    prs_delta,
    prs_noncentrality_sup,
    prs_statistic,
    prs_thresholds,
)
from .yurdakul import (
    PSITestResult,
    psi_critical_value,
    psi_pvalue,
    psi_scale,
    psi_statistic,
    psi_test,
)

__version__ = "0.1.0"

__all__ = [
    "PRSThresholds",
    "PSITestResult",
    "effect_size_critical_value",
    "effect_size_per_category",
    "effect_size_pvalue",
    "effect_size_statistic",
    "overlapping_critical_value",
    "overlapping_pvalue",
    "overlapping_statistic",
    "prs_classify",
    "prs_delta",
    "prs_noncentrality_sup",
    "prs_statistic",
    "prs_thresholds",
    "psi_critical_value",
    "psi_pvalue",
    "psi_scale",
    "psi_statistic",
    "psi_test",
]
