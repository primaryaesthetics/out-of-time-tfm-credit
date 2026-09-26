"""The scorecard: monotonic WOE binning, an information-value screen, logistic.

This is the baseline the study is answerable to. It is not a strawman and it is
not tuned to lose: it is the model a credit-risk function would actually put in
front of a validator, built the way that function would build it, and if a
foundation model cannot beat it out of time then that is the result.

The recipe, in the order it runs:

  1. **Bin every characteristic monotonically**, on the training rows alone.
     `monotonic_trend="auto_asc_desc"` restricts the event rate across a
     characteristic's bins to ascending or descending. optbinning's plain
     `"auto"` also admits peak, valley, convex and concave shapes, which fit
     the training book better and are exactly what a validator sends back: a
     characteristic whose risk rises and then falls has no explanation a credit
     policy can carry.
  2. **Screen on information value.** Anything below `iv_min` is not
     predictive enough to defend, and at most `max_characteristics` survive,
     taken by IV. Both numbers are policy, both are recorded.
  3. **Transform to weight of evidence.** optbinning's WOE is
     `ln(%non-event / %event)`, the credit convention: a high WOE bin is a
     *safe* bin. A characteristic's missing bin keeps its own empirical WOE
     rather than being flattened to zero — on this book `mths_since_last_delinq`
     is missing for half the loans and the missingness means "never delinquent",
     which is the strongest thing the column says. The exception is a missing
     bin thinner than `min_missing_count` rows: the bin-size floor does not
     reach it, so its empirical WOE can be the largest weight on the card and
     rest on two loans, and out of time it is applied to every row that lacks
     the value. Such a bin scores at WOE zero instead, the neutral value, which
     is also what a category never seen in training scores at.
  4. **Fit a logistic regression by maximum likelihood** on the WOE matrix.
     With at most twenty characteristics and pools from thirty thousand rows
     upwards, a penalty would shrink nothing that matters and would make the
     coefficients unreadable, so there is none.
  5. **Drop wrong-signed characteristics and refit.** Under the WOE convention
     every coefficient in a model of the *event* must be negative: more
     evidence of goodness, less default. A positive one is a characteristic
     whose univariate story is reversed by its correlation with another, and a
     scorecard developer removes it rather than shipping it. Removal is
     one-at-a-time, largest offender first, and every removal is recorded.

Everything above is refitted inside every build, on that build's training rows
and nothing else. The module holds no state between fits: two calls with the
same rows give the same scorecard, and a call with different rows does not
disturb a scorecard already returned.

One choice is about reproducibility rather than credit. optbinning's default
solver is CP-SAT, which searches with a portfolio of parallel workers and, when
two binnings tie on the objective, returns whichever worker finished first —
so the same rows can bin differently under CPU contention, with every status
reading `OPTIMAL`. The policy therefore uses the single-threaded mixed-integer
solver on the same model, which returns the same optimum every time.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .features import assert_matrix_clean, categorical_names, informative

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pandas as pd

# Points scaling. A scorecard is read in points, not in log-odds: 600 points at
# odds of fifty good to one bad, and twenty points to double the odds. The
# scaling is affine in the log-odds, so it changes no ranking and no
# probability — it exists so that the artefact is legible to the people who
# would use it.
BASE_POINTS = 600.0
BASE_ODDS = 50.0
POINTS_TO_DOUBLE_ODDS = 20.0


class ScorecardError(AssertionError):
    """A scorecard that could not be built honestly from the rows it was given."""


@dataclass(frozen=True)
class ScorecardPolicy:
    """Every choice that decides the scorecard, in one object a manifest eats."""

    iv_min: float = 0.02
    max_characteristics: int = 20
    monotonic_trend: str = "auto_asc_desc"
    max_n_prebins: int = 20
    min_prebin_size: float = 0.02
    min_bin_size: float = 0.05
    max_n_bins: int = 6
    min_missing_count: int = 100
    drop_wrong_sign: bool = True
    solver: str = "mip"
    mip_solver: str = "bop"
    solver_time_limit: int = 100
    logistic_tol: float = 1e-8
    n_jobs: int | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.iv_min:
            raise ScorecardError("iv_min cannot be negative")
        if self.solver not in ("mip", "cp"):
            raise ScorecardError(f"{self.solver!r} is not a binning solver this policy knows")
        if self.max_characteristics < 1:
            raise ScorecardError("a scorecard needs at least one characteristic")
        if self.monotonic_trend not in ("auto_asc_desc", "ascending", "descending"):
            raise ScorecardError(
                f"{self.monotonic_trend!r} is not a monotonic trend: a scorecard "
                f"characteristic whose risk peaks in the middle has no credit story"
            )

    def as_dict(self) -> dict:
        return {
            "iv_min": self.iv_min,
            "max_characteristics": self.max_characteristics,
            "monotonic_trend": self.monotonic_trend,
            "max_n_prebins": self.max_n_prebins,
            "min_prebin_size": self.min_prebin_size,
            "min_bin_size": self.min_bin_size,
            "max_n_bins": self.max_n_bins,
            "min_missing_count": self.min_missing_count,
            "drop_wrong_sign": self.drop_wrong_sign,
            "solver": self.solver,
            "mip_solver": self.mip_solver,
            "solver_time_limit": self.solver_time_limit,
            "logistic_tol": self.logistic_tol,
        }


DEFAULT_POLICY = ScorecardPolicy()


@dataclass(frozen=True)
class Characteristic:
    """One binned characteristic that survived the screen and the sign check."""

    name: str
    dtype: str
    iv: float
    n_bins: int
    status: str
    coefficient: float

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "dtype": self.dtype,
            "iv": round(self.iv, 6),
            "n_bins": self.n_bins,
            "solver_status": self.status,
            "coefficient": round(self.coefficient, 6),
        }


@dataclass(frozen=True)
class Scorecard:
    """A fitted scorecard, and the account of how it came to hold what it holds."""

    policy: ScorecardPolicy
    characteristics: tuple[Characteristic, ...]
    intercept: float
    train_rows: int
    train_default_rate: float
    screened_out: tuple[str, ...]
    constant_on_train: tuple[str, ...]
    dropped_wrong_sign: tuple[str, ...]
    iv_all: tuple[tuple[str, float], ...]
    neutral_missing: tuple[str, ...] = ()
    binning: Any = field(repr=False, default=None)
    model: Any = field(repr=False, default=None)
    notes: tuple[str, ...] = ()

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.characteristics)

    @property
    def coefficients(self) -> dict[str, float]:
        return {c.name: c.coefficient for c in self.characteristics}

    def transform(self, matrix: pd.DataFrame, rows: Sequence[int] | None = None):
        """The WOE matrix of the characteristics this scorecard kept."""
        frame = _subset(matrix, rows)
        woe = self.binning.transform(
            frame[list(self._binning_inputs)],
            metric="woe",
            metric_missing="empirical",
        )
        return _neutralise(woe[list(self.names)], frame, self.neutral_missing)

    def predict_pd(self, matrix: pd.DataFrame, rows: Sequence[int] | None = None):
        """The probability of default, one number per row, in row order."""
        import numpy as np

        woe = self.transform(matrix, rows)
        return np.asarray(self.model.predict_proba(woe.to_numpy())[:, 1], dtype=float)

    def predict_proba(self, matrix: pd.DataFrame, rows: Sequence[int] | None = None):
        """Both class probabilities, in scikit-learn's column order."""
        import numpy as np

        pd_hat = self.predict_pd(matrix, rows)
        return np.column_stack([1.0 - pd_hat, pd_hat])

    def points(self, matrix: pd.DataFrame, rows: Sequence[int] | None = None):
        """The scorecard in points: higher is safer, twenty points doubles odds."""
        import numpy as np

        pd_hat = np.clip(self.predict_pd(matrix, rows), 1e-12, 1 - 1e-12)
        factor = POINTS_TO_DOUBLE_ODDS / math.log(2.0)
        offset = BASE_POINTS - factor * math.log(BASE_ODDS)
        log_odds_good = np.log((1.0 - pd_hat) / pd_hat)
        return offset + factor * log_odds_good

    def bin_tables(self) -> list[dict]:
        """Every kept characteristic's bins, as records a run directory can hold."""
        out: list[dict] = []
        for characteristic in self.characteristics:
            binned = self.binning.get_binned_variable(characteristic.name)
            table = binned.binning_table.build()
            for index, row in table.iterrows():
                # The totals line is a summary of the rows above it, not a bin.
                if index == "Totals":
                    continue
                out.append(
                    {
                        "characteristic": characteristic.name,
                        "bin": _bin_label(row["Bin"]),
                        "count": int(row["Count"]),
                        "count_share": round(float(row["Count (%)"]), 6),
                        "non_event": int(row["Non-event"]),
                        "event": int(row["Event"]),
                        "event_rate": _round_or_none(row["Event rate"]),
                        "woe": _round_or_none(row["WoE"]),
                        "iv": _round_or_none(row["IV"]),
                    }
                )
        return out

    def as_dict(self) -> dict:
        return {
            "policy": self.policy.as_dict(),
            "train_rows": self.train_rows,
            "train_default_rate": round(self.train_default_rate, 6),
            "intercept": round(self.intercept, 6),
            "characteristics": [c.as_dict() for c in self.characteristics],
            "n_characteristics": len(self.characteristics),
            "constant_on_train": list(self.constant_on_train),
            "screened_out": list(self.screened_out),
            "dropped_wrong_sign": list(self.dropped_wrong_sign),
            "neutral_missing": list(self.neutral_missing),
            "iv_all": [{"name": n, "iv": round(v, 6)} for n, v in self.iv_all],
            "notes": list(self.notes),
        }

    @property
    def _binning_inputs(self) -> tuple[str, ...]:
        """The columns the fitted binning process expects to be handed."""
        return tuple(self.binning.variable_names)


def _bin_label(label) -> str:
    """A bin as text: an interval as optbinning prints it, a category set joined.

    A categorical bin arrives as an array of category values, and the string
    form of an array is the array's type and shape rather than its contents.
    """
    if isinstance(label, str):
        return label
    try:
        members = list(label)
    except TypeError:
        return str(label)
    return ", ".join(str(member) for member in members)


def _neutralise(woe, frame, names: Sequence[str]):
    """Sets the WOE of missing values to zero on the characteristics named."""
    if not names:
        return woe
    out = woe.copy()
    for name in names:
        missing = frame[name].isna().to_numpy()
        if missing.any():
            out.loc[out.index[missing], name] = 0.0
    return out


def _missing_counts(binning, names: Sequence[str]) -> dict[str, int]:
    """How many training rows fell in each characteristic's Missing bin."""
    out = {}
    for name in names:
        table = binning.get_binned_variable(name).binning_table.build()
        # A categorical bin's label is an array of its members, so the column
        # is compared row by row rather than vectorised.
        counts = [
            int(count)
            for label, count in zip(table["Bin"], table["Count"])
            if isinstance(label, str) and label == "Missing"
        ]
        out[name] = counts[0] if counts else 0
    return out


def _round_or_none(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) else round(number, 6)


def _subset(matrix: pd.DataFrame, rows: Sequence[int] | None):
    if rows is None:
        return matrix
    positions = list(rows)
    if not positions:
        raise ScorecardError("no rows")
    return matrix.iloc[positions]


def _targets(labels: Sequence[int | None], rows: Sequence[int]):
    import numpy as np

    values = []
    for position in rows:
        value = labels[position]
        if value is None or (isinstance(value, float) and math.isnan(value)):
            raise ScorecardError(
                f"row {position} has no label: a scorecard is fitted on loans whose "
                f"performance window has closed, and the maturity gate belongs "
                f"upstream of this module"
            )
        values.append(int(value))
    target = np.asarray(values, dtype=int)
    if target.min() == target.max():
        raise ScorecardError(
            "the training rows hold one class only; nothing can be binned against "
            "a constant outcome"
        )
    return target


def fit(
    matrix: pd.DataFrame,
    labels: Sequence[int | None],
    *,
    rows: Sequence[int] | None = None,
    policy: ScorecardPolicy = DEFAULT_POLICY,
    declaration: Any = None,
) -> Scorecard:
    """Fits a scorecard on the rows given, and reads nothing outside them.

    `matrix` is the study's model matrix — `features.model_matrix` — and
    `labels` is aligned to it by position, carrying `None` where a loan's
    performance window had not closed. `rows` are the positions to fit on,
    normally a `VintageBuild.train`. Nothing here consults the rest of the
    frame: the columns screened as constant, the bin edges, the information
    values and the coefficients are all properties of these rows, because on
    the build date they were the only rows there were.

    `declaration` is the feature module of the book the matrix was built by,
    which supplies the matrix gate and the categorical columns: `features`
    for Lending Club, the default, and `fm_features` for the Freddie Mac
    sample.
    """
    import numpy as np
    from optbinning import BinningProcess
    from sklearn.linear_model import LogisticRegression

    if declaration is None:
        assert_matrix_clean(matrix)
        declared_categorical = categorical_names()
    else:
        declaration.assert_matrix_clean(matrix)
        declared_categorical = declaration.categorical_names()

    positions = list(range(len(matrix))) if rows is None else list(rows)
    if not positions:
        raise ScorecardError("no training rows")
    target = _targets(labels, positions)

    usable = informative(matrix, positions)
    constant = tuple(name for name in matrix.columns if name not in usable)
    if not usable:
        raise ScorecardError("every characteristic is constant on the training rows")

    train = matrix.iloc[positions][list(usable)]
    categorical = [name for name in declared_categorical if name in usable]

    binning = BinningProcess(
        variable_names=list(usable),
        categorical_variables=categorical,
        max_n_prebins=policy.max_n_prebins,
        min_prebin_size=policy.min_prebin_size,
        min_bin_size=policy.min_bin_size,
        max_n_bins=policy.max_n_bins,
        selection_criteria={
            "iv": {
                "min": policy.iv_min,
                "strategy": "highest",
                "top": policy.max_characteristics,
            }
        },
        binning_fit_params={
            name: {
                "monotonic_trend": policy.monotonic_trend,
                "solver": policy.solver,
                "mip_solver": policy.mip_solver,
                "time_limit": policy.solver_time_limit,
            }
            for name in usable
        },
        n_jobs=policy.n_jobs,
    )
    binning.fit(train, target)

    summary = binning.summary()
    iv_all = tuple(
        (str(row["name"]), float(row["iv"]))
        for _, row in summary.sort_values("iv", ascending=False).iterrows()
    )
    selected = tuple(binning.get_support(names=True))
    if not selected:
        raise ScorecardError(
            f"no characteristic reaches an information value of {policy.iv_min} on "
            f"{len(positions)} training rows"
        )
    screened_out = tuple(name for name in usable if name not in selected)

    woe = binning.transform(train, metric="woe", metric_missing="empirical")
    woe = woe[list(selected)]
    missing_counts = _missing_counts(binning, selected)
    neutral = tuple(
        name
        for name in selected
        if 0 < missing_counts[name] < policy.min_missing_count
    )
    woe = _neutralise(woe, train, neutral)

    kept = list(selected)
    dropped: list[str] = []
    while True:
        model = LogisticRegression(
            C=np.inf, solver="lbfgs", max_iter=5000, tol=policy.logistic_tol
        )
        model.fit(woe[kept].to_numpy(), target)
        coefficients = dict(zip(kept, model.coef_[0]))
        if not policy.drop_wrong_sign:
            break
        offenders = {n: c for n, c in coefficients.items() if c > 0}
        if not offenders or len(kept) == 1:
            break
        worst = max(offenders, key=lambda name: offenders[name])
        kept.remove(worst)
        dropped.append(worst)

    statuses = {
        name: str(binning.get_binned_variable(name).status) for name in kept
    }
    ivs = {str(row["name"]): float(row["iv"]) for _, row in summary.iterrows()}
    dtypes = {str(row["name"]): str(row["dtype"]) for _, row in summary.iterrows()}
    n_bins = {str(row["name"]): int(row["n_bins"]) for _, row in summary.iterrows()}

    characteristics = tuple(
        Characteristic(
            name=name,
            dtype=dtypes[name],
            iv=ivs[name],
            n_bins=n_bins[name],
            status=statuses[name],
            coefficient=float(coefficients[name]),
        )
        for name in kept
    )

    notes = []
    not_optimal = sorted(n for n, s in statuses.items() if s != "OPTIMAL")
    if not_optimal:
        notes.append(
            f"{len(not_optimal)} characteristics did not reach a proven optimum "
            f"within {policy.solver_time_limit}s and their bins depend on the "
            f"solver's search: {not_optimal}"
        )
    if constant:
        notes.append(
            f"{len(constant)} characteristics carry one value or none on these "
            f"training rows and were not binned"
        )
    neutral_kept = tuple(name for name in neutral if name in kept)
    if neutral_kept:
        notes.append(
            f"{len(neutral_kept)} characteristics had a missing bin under "
            f"{policy.min_missing_count} rows and score missing values at WOE zero: "
            f"{list(neutral_kept)}"
        )

    return Scorecard(
        policy=policy,
        characteristics=characteristics,
        intercept=float(model.intercept_[0]),
        train_rows=len(positions),
        train_default_rate=float(np.mean(target)),
        screened_out=screened_out,
        constant_on_train=constant,
        dropped_wrong_sign=tuple(dropped),
        iv_all=iv_all,
        neutral_missing=neutral_kept,
        binning=binning,
        model=model,
        notes=tuple(notes),
    )
