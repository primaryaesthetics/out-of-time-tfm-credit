"""The gradient-boosted challenger, tuned the way a time-ordered book allows.

The scorecard is what a credit function would defend; this is what it would be
asked why it did not use. A tuned GBM on the same twenty-nine columns is the
strongest classical model on tabular credit data, and a foundation-model result
that does not clear it is not a result.

Two things about the recipe are load-bearing, and both are about time.

**The tuning split is the end of the training pool, never a random fold.** A
random K-fold on a book whose default rate rises from 1.92% to 3.44% inside the
window hands every fold a sample of every regime, so the chosen hyperparameters
are the ones that work when the future is in the training set. That is the
leakage this study exists to measure, and it would be embarrassing to commit it
in the control. The early-stopping set is therefore the *latest* whole quarters
of the pool, and the model is tuned to predict forward, as it will be used.

How many quarters is not a constant. A fixed four would suit the expanding arm
and be impossible on the rolling one, whose whole pool is four quarters wide:
holding out four leaves nothing to fit on. The rule that covers both arms is
stated by row share instead —

  the validation set is the fewest latest quarters of the pool that together
  hold at least `validation_row_share` of its rows, never fewer than one
  quarter, never more than `validation_quarters_max`, and never more than half
  the quarters in the pool

— which on this book gives one or two quarters on either arm, because Lending
Club's volume roughly doubles each year and the last quarter of a pool is a
large share of it. If a validation slice comes out with one class in it, it
grows by a quarter until it does not; that has never happened on this book and
the code says so rather than assuming it.

**The model that ships is refitted on the whole pool.** Hyperparameters and the
number of rounds are chosen against the held-out tail, and then the model is
built again on every row the builder had, at the chosen number of rounds. The
alternative — ship the model that never saw its own early-stopping set — would
give the GBM a fifth fewer rows than the scorecard gets and turn a model
comparison into a data-budget comparison. Rounds are not rescaled for the extra
rows: a boosting round fits a tree to whatever rows are there, so the same
count on more rows is more information, not less.

One LightGBM default is switched off for the search to mean anything.
`feature_pre_filter` drops, at dataset construction, every bin that cannot
satisfy `min_data_in_leaf` — and the dataset is constructed once, by the first
training call, then reused. Thirty-six points searched on one dataset would all
be scored on bins filtered for the first point's leaf size, and a model fitted
later on a fresh dataset at the chosen point would be a different model: on the
first rolling build that gap was 77 rounds against 71 and 5.6 × 10⁻⁴ in
log-loss, larger than every margin the search decided by. With the filter off
every point sees the same bins and the chosen point refits to the same model.

Determinism is forced. LightGBM's default histogram construction chooses
row-wise or column-wise by a runtime timing test and sums gradients in whatever
order the threads finish in, which makes the same pool give slightly different
trees under CPU contention — the same failure the binning solver had. Setting
`deterministic` and `force_row_wise` costs some speed and buys a model that is
a function of its rows.

Categories are learned from the training pool alone. A state or a purpose that
first appears after the as-of date arrives at scoring time as missing, which is
what it was to the builder: unseen.
"""

from __future__ import annotations

import datetime as dt
import math
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import product
from typing import TYPE_CHECKING, Any

from .features import assert_matrix_clean, categorical_names
from .vintage import Quarter

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pandas as pd


class GBMError(AssertionError):
    """A GBM that could not be built honestly from the rows it was given."""


@dataclass(frozen=True)
class GBMPolicy:
    """Every choice that decides the GBM, in one object a manifest eats.

    The search is a screening grid rather than a dense one: thirty-six points,
    one early-stopped fit each, three levels on the knobs that decide a tree's
    shape and two on the rest. It reaches further into regularisation than a
    first version did — seven leaves, a thousand rows per leaf, four columns in
    ten — because on this book the search kept choosing the most regularised
    corner of a grid that stopped at fifteen, two hundred and six. A best point
    on the edge is recorded as a note so that the next reader knows. A denser
    grid buys hours of CPU and a third decimal place, and the study's claim is
    about model classes rather than about the last percent of a LightGBM.
    """

    num_leaves: tuple[int, ...] = (7, 15, 31)
    learning_rate: tuple[float, ...] = (0.03, 0.1)
    min_child_samples: tuple[int, ...] = (200, 1000)
    feature_fraction: tuple[float, ...] = (0.4, 0.6, 1.0)
    max_rounds: int = 2000
    early_stopping_rounds: int = 50
    validation_quarters_max: int = 4
    validation_row_share: float = 0.20
    min_validation_rows: int = 1000
    seed: int = 20260904
    n_jobs: int = 0
    verbose: int = -1

    def __post_init__(self) -> None:
        if not 0.0 < self.validation_row_share < 0.5:
            raise GBMError(
                "the early-stopping set is the tail of the pool, not most of it: "
                "validation_row_share must lie in (0, 0.5)"
            )
        if self.validation_quarters_max < 1:
            raise GBMError("the early-stopping set is at least one quarter")
        if self.early_stopping_rounds < 1 or self.max_rounds < 1:
            raise GBMError("rounds must be positive")
        for name in ("num_leaves", "learning_rate", "min_child_samples", "feature_fraction"):
            if not getattr(self, name):
                raise GBMError(f"the search grid has no {name} to try")

    def grid(self) -> tuple[dict, ...]:
        """The search points, in a fixed order so that a tie breaks the same way."""
        points = product(
            sorted(self.num_leaves),
            sorted(self.learning_rate),
            sorted(self.min_child_samples),
            sorted(self.feature_fraction),
        )
        return tuple(
            {
                "num_leaves": leaves,
                "learning_rate": rate,
                "min_child_samples": children,
                "feature_fraction": fraction,
            }
            for leaves, rate, children, fraction in points
        )

    def as_dict(self) -> dict:
        return {
            "num_leaves": list(self.num_leaves),
            "learning_rate": list(self.learning_rate),
            "min_child_samples": list(self.min_child_samples),
            "feature_fraction": list(self.feature_fraction),
            "grid_points": len(self.grid()),
            "max_rounds": self.max_rounds,
            "early_stopping_rounds": self.early_stopping_rounds,
            "validation_quarters_max": self.validation_quarters_max,
            "validation_row_share": self.validation_row_share,
            "min_validation_rows": self.min_validation_rows,
            "seed": self.seed,
        }


DEFAULT_POLICY = GBMPolicy()

# Everything that is not searched over. `deterministic` and `force_row_wise`
# are the reproducibility pair; the rest are LightGBM's defaults written down
# so that a version bump cannot move them silently.
FIXED_PARAMS = {
    "objective": "binary",
    "boosting_type": "gbdt",
    "metric": "binary_logloss",
    "bagging_fraction": 1.0,
    "bagging_freq": 0,
    "lambda_l1": 0.0,
    "lambda_l2": 0.0,
    "min_split_gain": 0.0,
    "max_bin": 255,
    "deterministic": True,
    "force_row_wise": True,
}

# Dataset construction. See the module docstring on `feature_pre_filter`.
DATASET_PARAMS = {"feature_pre_filter": False}


@dataclass(frozen=True)
class Trial:
    """One search point and what the held-out tail of the pool said about it."""

    params: dict
    rounds: int
    validation_logloss: float
    seconds: float
    validation_auc: float | None = None

    def as_dict(self) -> dict:
        out = {
            "params": dict(self.params),
            "rounds": self.rounds,
            "validation_logloss": round(self.validation_logloss, 8),
            "seconds": round(self.seconds, 3),
        }
        if self.validation_auc is not None:
            out["validation_auc"] = round(self.validation_auc, 8)
        return out


@dataclass(frozen=True)
class GBM:
    """A fitted GBM, and the account of how its hyperparameters were chosen."""

    policy: GBMPolicy
    params: dict
    rounds: int
    features: tuple[str, ...]
    categorical: tuple[str, ...]
    categories: dict[str, tuple]
    train_rows: int
    train_default_rate: float
    train_quarters: tuple[Quarter, ...]
    validation_quarters: tuple[Quarter, ...]
    validation_rows: int
    validation_logloss: float
    trials: tuple[Trial, ...]
    seed: int
    model: Any = field(repr=False, default=None)
    notes: tuple[str, ...] = ()
    objective: str = "logloss"
    validation_auc: float | None = None
    refitted: bool = True

    @property
    def fit_rows(self) -> int:
        """Rows the tuning fits saw; the shipped model was refitted on all of them."""
        return self.train_rows - self.validation_rows

    def predict_pd(self, matrix: pd.DataFrame, rows: Sequence[int] | None = None):
        """The probability of default, one number per row, in row order."""
        import numpy as np

        frame = _encode(_subset(matrix, rows)[list(self.features)], self.categories)
        raw = self.model.predict(frame, num_iteration=self.rounds)
        return np.asarray(raw, dtype=float)

    def predict_proba(self, matrix: pd.DataFrame, rows: Sequence[int] | None = None):
        """Both class probabilities, in scikit-learn's column order."""
        import numpy as np

        pd_hat = self.predict_pd(matrix, rows)
        return np.column_stack([1.0 - pd_hat, pd_hat])

    def importances(self) -> list[dict]:
        """Gain and split counts per feature, largest gain first."""
        gains = self.model.feature_importance(importance_type="gain")
        splits = self.model.feature_importance(importance_type="split")
        records = [
            {
                "feature": name,
                "gain": round(float(gain), 6),
                "splits": int(split),
            }
            for name, gain, split in zip(self.features, gains, splits)
        ]
        total = sum(record["gain"] for record in records) or 1.0
        for record in records:
            record["gain_share"] = round(record["gain"] / total, 6)
        return sorted(records, key=lambda record: -record["gain"])

    def as_dict(self) -> dict:
        return {
            "policy": self.policy.as_dict(),
            "params": dict(self.params),
            "rounds": self.rounds,
            "seed": self.seed,
            "train_rows": self.train_rows,
            "fit_rows": self.fit_rows,
            "train_default_rate": round(self.train_default_rate, 6),
            "train_quarters": [str(q) for q in self.train_quarters],
            "validation_quarters": [str(q) for q in self.validation_quarters],
            "validation_rows": self.validation_rows,
            "validation_logloss": round(self.validation_logloss, 8),
            "objective": self.objective,
            "validation_auc": (None if self.validation_auc is None
                               else round(self.validation_auc, 8)),
            "refitted": self.refitted,
            "n_features": len(self.features),
            "unseen_categories": {
                name: len(values) for name, values in sorted(self.categories.items())
            },
            "trials": [trial.as_dict() for trial in self.trials],
            "importances": self.importances(),
            "notes": list(self.notes),
        }


def _subset(matrix: pd.DataFrame, rows: Sequence[int] | None):
    if rows is None:
        return matrix
    positions = list(rows)
    if not positions:
        raise GBMError("no rows")
    return matrix.iloc[positions]


def _targets(labels: Sequence[int | None], rows: Sequence[int]):
    import numpy as np

    values = []
    for position in rows:
        value = labels[position]
        if value is None or (isinstance(value, float) and math.isnan(value)):
            raise GBMError(
                f"row {position} has no label: a model is fitted on loans whose "
                f"performance window has closed, and the maturity gate belongs "
                f"upstream of this module"
            )
        values.append(int(value))
    target = np.asarray(values, dtype=int)
    if target.min() == target.max():
        raise GBMError(
            "the training rows hold one class only; nothing can be boosted against "
            "a constant outcome"
        )
    return target


def _categories(frame: pd.DataFrame, names: Sequence[str]) -> dict[str, tuple]:
    """The category values present in the pool, sorted, one tuple per column."""
    out: dict[str, tuple] = {}
    for name in names:
        values = frame[name].dropna().unique().tolist()
        out[name] = tuple(sorted(str(value) for value in values))
    return out


def _encode(frame: pd.DataFrame, categories: dict[str, tuple]):
    """The matrix as LightGBM reads it: categories fixed to what the pool held.

    A value the pool never held becomes missing rather than a new level, which
    is the only encoding that is a function of the training rows alone. Numeric
    columns pass through; LightGBM splits on NaN natively and the study's
    missingness is informative, so nothing is imputed.
    """
    import pandas as pd

    out = frame.copy()
    for name, known in categories.items():
        column = out[name].astype(object).map(str, na_action="ignore")
        seen = column.isin(set(known))
        out[name] = pd.Categorical(column.where(seen, other=None), categories=list(known))
    for name in out.columns:
        if name not in categories:
            out[name] = pd.to_numeric(out[name], errors="coerce").astype("float64")
    return out


def validation_split(
    quarters: Sequence[Quarter],
    counts: dict[Quarter, int],
    *,
    policy: GBMPolicy = DEFAULT_POLICY,
) -> tuple[Quarter, ...]:
    """The latest quarters of a pool that make up its early-stopping set.

    Takes the pool's quarters in any order and how many rows each holds, and
    returns the tail, newest included first in time order. The rule is the one
    in the module docstring; it is a pure function of the counts so that a test
    can drive it with numbers rather than with a fitted book.
    """
    ordered = sorted(set(quarters))
    if len(ordered) < 2:
        raise GBMError(
            "a pool spanning one quarter has no time-ordered tail to stop on; "
            "the vintage grid never produces one"
        )
    total = sum(counts[quarter] for quarter in ordered)
    ceiling = min(policy.validation_quarters_max, len(ordered) // 2)
    taken = 0
    for size in range(1, ceiling + 1):
        tail = ordered[-size:]
        taken = sum(counts[quarter] for quarter in tail)
        enough_share = taken >= policy.validation_row_share * total
        enough_rows = taken >= min(policy.min_validation_rows, total // 4)
        if enough_share and enough_rows:
            return tuple(tail)
    return tuple(ordered[-ceiling:])


def fit(
    matrix: pd.DataFrame,
    labels: Sequence[int | None],
    origination: Sequence[dt.date | None],
    *,
    rows: Sequence[int] | None = None,
    policy: GBMPolicy = DEFAULT_POLICY,
    seed: int | None = None,
    point: dict | None = None,
    validation_rows: Sequence[int] | None = None,
    objective: str = "logloss",
    refit: bool = True,
    declaration: Any = None,
) -> GBM:
    """Tunes and fits a GBM on the rows given, and reads nothing outside them.

    `matrix` is the study's model matrix, `labels` and `origination` are aligned
    to it by position, and `rows` are the positions to fit on — a build's
    training pool for the full-data variant, a build's context sample for the
    fifty-thousand-row control. The origination dates are needed here and
    nowhere else in the fit: they carve the early-stopping set out of the end of
    the pool, and they never enter the matrix.

    `point` fixes the hyperparameters and skips the search; only the round
    count is then chosen, by early stopping on the same tail. The context
    control is fitted this way with its build's full-pool point, so that the
    spread across its three draws is the spread of the rows and not of a search
    decided by margins of a ten-thousandth in log-loss — which is what a
    zero-shot model, with no search at all, should be compared against.

    `validation_rows` replaces the time-ordered tail with rows the caller
    names, a subset of `rows`, and `objective` chooses the point by
    `"logloss"` or by `"auc"` on that set. Both exist for one purpose: to
    run the published benchmark's recipe — a random validation split, the
    point chosen by AUC — on this study's matrix beside the study's own
    recipe. `refit=False` ships the model fitted on the rows outside the
    validation set at the chosen rounds instead of refitting on every row,
    so that a threshold chosen on the validation rows is chosen on rows the
    shipped model never saw. Left at their defaults the fit is the study's,
    unchanged.

    `declaration` is the feature module of the book the matrix was built by,
    which supplies the matrix gate and the categorical columns: `features`
    for Lending Club, the default, and `fm_features` for the Freddie Mac
    sample. On that book `origination` is the first day of the origination
    quarter, the axis its pool of whole quarters is cut on, so the
    early-stopping tail is the pool's latest quarters exactly as on Lending
    Club.
    """
    import lightgbm as lgb
    import numpy as np

    if declaration is None:
        assert_matrix_clean(matrix)
        declared_categorical = categorical_names()
    else:
        declaration.assert_matrix_clean(matrix)
        declared_categorical = declaration.categorical_names()

    positions = list(range(len(matrix))) if rows is None else list(rows)
    if not positions:
        raise GBMError("no training rows")
    target = _targets(labels, positions)
    chosen_seed = policy.seed if seed is None else seed

    quarters = []
    for position in positions:
        date = origination[position]
        if date is None:
            raise GBMError(f"row {position} has no origination date to order the pool by")
        quarters.append(Quarter.of(date))
    quarter_array = np.asarray([(q.year, q.quarter) for q in quarters])
    counts: dict[Quarter, int] = {}
    for quarter in quarters:
        counts[quarter] = counts.get(quarter, 0) + 1

    if objective not in ("logloss", "auc"):
        raise GBMError(f"the objective is 'logloss' or 'auc', not {objective!r}")
    notes: list[str] = []
    if validation_rows is not None:
        wanted = {int(v) for v in validation_rows}
        if not wanted or not wanted <= set(positions):
            raise GBMError("validation_rows must be a non-empty subset of the rows fitted on")
        mask = np.asarray([position in wanted for position in positions], dtype=bool)
        if mask.all():
            raise GBMError("validation_rows leave nothing to fit on")
        if target[mask].min() == target[mask].max() or target[~mask].min() == target[~mask].max():
            raise GBMError("the validation rows given leave one side with one class only")
        held: tuple[Quarter, ...] = ()
        notes.append(
            f"the early-stopping set is {int(mask.sum())} rows named by the caller, "
            "not the pool's time-ordered tail"
        )
    else:
        held = validation_split(quarters, counts, policy=policy)
        while True:
            mask = np.zeros(len(positions), dtype=bool)
            for quarter in held:
                mask |= (quarter_array[:, 0] == quarter.year) & (quarter_array[:, 1] == quarter.quarter)
            if target[mask].min() != target[mask].max() and target[~mask].min() != target[~mask].max():
                break
            earlier = sorted(set(quarters) - set(held))
            if not earlier or len(held) >= len(set(quarters)) - 1:
                raise GBMError(
                    "no time-ordered split of this pool leaves both sides with both "
                    "classes in them"
                )
            held = (earlier[-1], *held)
            notes.append(
                f"the early-stopping set was grown to {len(held)} quarters because a "
                f"shorter tail held one class only"
            )
    if objective == "auc":
        notes.append("the search point was chosen by the validation AUC, not log-loss")

    features = tuple(matrix.columns)
    categorical = tuple(name for name in declared_categorical if name in features)
    pool = matrix.iloc[positions]
    categories = _categories(pool, categorical)
    encoded = _encode(pool[list(features)], categories)

    fit_x, fit_y = encoded[~mask], target[~mask]
    held_x, held_y = encoded[mask], target[mask]

    train_set = lgb.Dataset(
        fit_x, label=fit_y, categorical_feature=list(categorical), params=dict(DATASET_PARAMS)
    )
    valid_set = lgb.Dataset(
        held_x, label=held_y, reference=train_set, categorical_feature=list(categorical),
        params=dict(DATASET_PARAMS),
    )

    if point is not None:
        unknown = set(point) - set(policy.grid()[0])
        if unknown:
            raise GBMError(f"a fixed point may only set the searched knobs, not {sorted(unknown)}")
        search = (dict(point),)
    else:
        search = policy.grid()

    # Under the AUC objective LightGBM stops on the AUC and reports the
    # log-loss beside it; under log-loss the parameters are exactly the
    # study's, so a recorded fit reproduces.
    metric_params = {} if objective == "logloss" else {
        "metric": ["auc", "binary_logloss"], "first_metric_only": True}
    trials: list[Trial] = []
    for candidate in search:
        started = time.time()
        params = {
            **FIXED_PARAMS,
            **candidate,
            **metric_params,
            "seed": chosen_seed,
            "num_threads": policy.n_jobs,
            "verbose": policy.verbose,
        }
        booster = lgb.train(
            params,
            train_set,
            num_boost_round=policy.max_rounds,
            valid_sets=[valid_set],
            callbacks=[lgb.early_stopping(policy.early_stopping_rounds, verbose=False)],
        )
        scores = booster.best_score["valid_0"]
        trials.append(
            Trial(
                params=dict(candidate),
                rounds=int(booster.best_iteration),
                validation_logloss=float(scores["binary_logloss"]),
                seconds=time.time() - started,
                validation_auc=float(scores["auc"]) if objective == "auc" else None,
            )
        )

    # The grid is generated in a fixed order and `min` keeps the first of any
    # tie, so two runs on the same pool choose the same point.
    if objective == "auc":
        best = max(trials, key=lambda trial: trial.validation_auc)
    else:
        best = min(trials, key=lambda trial: trial.validation_logloss)
    if best.rounds >= policy.max_rounds:
        notes.append(
            f"the chosen point never stopped early: it used all "
            f"{policy.max_rounds} rounds and may be under-trained"
        )
    if all(trial.rounds <= policy.early_stopping_rounds for trial in trials):
        notes.append(
            "every search point stopped within the early-stopping patience; the "
            "learning rates in the grid are too high for this pool"
        )
    if point is None:
        # A best point on the edge of the grid says the grid is too narrow on
        # that side, and a run that does not say so records a tuned model it
        # does not have.
        # Only a knob with an interior can have an edge worth reporting; on a
        # two-level knob every choice is an end and the note would say nothing.
        edges = []
        for knob in ("num_leaves", "learning_rate", "min_child_samples", "feature_fraction"):
            values = sorted(getattr(policy, knob))
            if len(values) > 2 and best.params[knob] in (values[0], values[-1]):
                edges.append(f"{knob}={best.params[knob]}")
        if edges:
            notes.append(f"the chosen point sits on the grid's edge: {', '.join(edges)}")
        if objective == "auc":
            runner_up = sorted((trial.validation_auc for trial in trials), reverse=True)
            if len(runner_up) > 1:
                notes.append(
                    f"chosen over the runner-up by {runner_up[0] - runner_up[1]:.2e} in AUC"
                )
        else:
            runner_up = sorted(trial.validation_logloss for trial in trials)
            if len(runner_up) > 1:
                notes.append(
                    f"chosen over the runner-up by {runner_up[1] - runner_up[0]:.2e} in log-loss"
                )

    params = {
        **FIXED_PARAMS,
        **best.params,
        **metric_params,
        "seed": chosen_seed,
        "num_threads": policy.n_jobs,
        "verbose": policy.verbose,
    }
    if refit:
        whole = lgb.Dataset(
            encoded, label=target, categorical_feature=list(categorical),
            params=dict(DATASET_PARAMS),
        )
    else:
        whole = lgb.Dataset(
            fit_x, label=fit_y, categorical_feature=list(categorical), params=dict(DATASET_PARAMS)
        )
        notes.append("the shipped model was not refitted on the validation rows")
    model = lgb.train(params, whole, num_boost_round=best.rounds)

    return GBM(
        policy=policy,
        params={k: v for k, v in params.items() if k != "verbose"},
        rounds=best.rounds,
        features=features,
        categorical=categorical,
        categories=categories,
        train_rows=len(positions),
        train_default_rate=float(np.mean(target)),
        train_quarters=tuple(sorted(set(quarters))),
        validation_quarters=tuple(held),
        validation_rows=int(mask.sum()),
        validation_logloss=best.validation_logloss,
        trials=tuple(trials),
        seed=chosen_seed,
        model=model,
        notes=tuple(notes),
        objective=objective,
        validation_auc=best.validation_auc,
        refitted=refit,
    )
