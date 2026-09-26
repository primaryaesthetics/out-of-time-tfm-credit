"""Time-ordered splits that refuse to be built wrong.

Temporal leakage is how a study like this one dies quietly. The model looks
excellent, the numbers are real, and the split let it see the future. It never
announces itself: an out-of-time score that is too good is exactly what a
promising result looks like.

So the split is an object with a constructor that validates, not a pair of
index arrays produced by a slice. Every check here has been the cause of a
published retraction somewhere:

  * consecutive windows must be separated by at least the performance window,
    because a loan originated a week before the cutoff has no mature label yet
    and training on it means training on an outcome observed inside the
    out-of-time period;
  * an account may appear in one window only, or the model memorises borrowers
    rather than learning risk;
  * the windows must not be empty, and the out-of-time window must be wide
    enough to carry more than one origination cohort, or "out of time" means
    "one week later";
  * every feature must declare when it becomes knowable relative to the
    origination date, and a feature knowable only afterwards is refused.

Works on plain sequences - dates and identifiers - so it can sit under pandas,
polars or numpy without importing any of them.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

Date = dt.date


class LeakageError(AssertionError):
    """A split or a feature set that would let the model see the future."""


@dataclass(frozen=True)
class Window:
    name: str
    indices: tuple[int, ...]
    first: Date
    last: Date

    @property
    def size(self) -> int:
        return len(self.indices)

    @property
    def span_days(self) -> int:
        return (self.last - self.first).days

    def __repr__(self) -> str:
        return (
            f"Window({self.name}, n={self.size}, "
            f"{self.first.isoformat()}..{self.last.isoformat()})"
        )


@dataclass(frozen=True)
class TemporalSplit:
    """Validated train / validation / out-of-time windows."""

    train: Window
    valid: Window
    oot: Window
    entity_column: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def summary(self) -> str:
        rows = [
            "| window | n | first | last | days |",
            "| --- | --- | --- | --- | --- |",
        ]
        for window in (self.train, self.valid, self.oot):
            rows.append(
                f"| {window.name} | {window.size} | {window.first.isoformat()} "
                f"| {window.last.isoformat()} | {window.span_days} |"
            )
        return "\n".join(rows)


def _window(name: str, indices: Iterable[int], dates: Sequence[Date]) -> Window:
    ordered = tuple(sorted(indices))
    if not ordered:
        raise LeakageError(f"{name} window is empty")
    selected = [dates[i] for i in ordered]
    return Window(name=name, indices=ordered, first=min(selected), last=max(selected))


def temporal_split(
    dates: Sequence[Date],
    *,
    valid_from: Date,
    oot_from: Date,
    entity_ids: Sequence[object] | None = None,
    entity_column: str | None = None,
    min_oot_days: int = 90,
    embargo_days: int = 0,
) -> TemporalSplit:
    """Builds the three windows and validates them, or raises `LeakageError`.

    `valid_from` and `oot_from` are inclusive lower bounds. Rows before
    `valid_from` train, rows in between validate, rows from `oot_from` onward
    are the out-of-time window and are never touched during model selection.

    `embargo_days` is the gap required between consecutive windows, and it is
    the parameter that does the work: set it to the performance window the
    label is defined over - 12 or 18 months on a card book, 24 on a mortgage.
    Left at zero it checks nothing, which is the right default only for a
    dataset whose labels are already known to be mature at every cutoff. Rows
    inside the embargo are dropped by the caller, before the split; this
    function reports the gap it finds and refuses one that is too small.
    """
    if not dates:
        raise LeakageError("no rows")
    if not valid_from < oot_from:
        raise LeakageError(
            f"valid_from {valid_from.isoformat()} is not before "
            f"oot_from {oot_from.isoformat()}"
        )

    train_idx, valid_idx, oot_idx = [], [], []
    for index, date in enumerate(dates):
        if date < valid_from:
            train_idx.append(index)
        elif date < oot_from:
            valid_idx.append(index)
        else:
            oot_idx.append(index)

    train = _window("train", train_idx, dates)
    valid = _window("valid", valid_idx, dates)
    oot = _window("oot", oot_idx, dates)

    for earlier, later in ((train, valid), (valid, oot)):
        gap = (later.first - earlier.last).days
        if gap < embargo_days:
            raise LeakageError(
                f"{earlier.name} ends {earlier.last.isoformat()} and {later.name} "
                f"begins {later.first.isoformat()}, a gap of {gap} days against an "
                f"embargo of {embargo_days}: labels in {earlier.name} are not mature "
                f"before {later.name} opens. Drop the rows inside the embargo."
            )

    if oot.span_days < min_oot_days:
        raise LeakageError(
            f"the out-of-time window spans {oot.span_days} days, below the "
            f"{min_oot_days} required: one cohort is not an out-of-time test"
        )

    notes: list[str] = []
    if entity_ids is not None:
        if len(entity_ids) != len(dates):
            raise LeakageError(
                f"entity_ids has {len(entity_ids)} rows against {len(dates)} dates"
            )
        seen: dict[object, str] = {}
        collisions: dict[object, tuple[str, str]] = {}
        for window in (train, valid, oot):
            for index in window.indices:
                key = entity_ids[index]
                if key in seen and seen[key] != window.name:
                    collisions.setdefault(key, (seen[key], window.name))
                seen.setdefault(key, window.name)
        if collisions:
            sample = list(collisions.items())[:5]
            raise LeakageError(
                f"{len(collisions)} entities appear in more than one window, "
                f"for example {sample}"
            )
        notes.append(f"{len(seen)} distinct entities, none crossing a window")

    return TemporalSplit(
        train=train, valid=valid, oot=oot,
        entity_column=entity_column, notes=tuple(notes),
    )


def assert_features_knowable(
    feature_availability: dict[str, int],
    features_used: Sequence[str],
) -> None:
    """Refuses any feature that is not knowable at origination.

    `feature_availability` maps a feature name to the offset, in days from the
    origination date, at which its value becomes known. Zero or negative is
    knowable at decision time; positive is the future.

    There is no way to infer this from the data, and pretending otherwise is
    the whole problem. The traps come in near-identical pairs: on Lending Club,
    `fico_range_high` is the bureau score that supported the decision and
    `last_fico_range_high` is the same score refreshed every month of the
    loan's life, so a model trained on the second reads the borrower's score
    after they started missing payments. Nothing in either column says which is
    which. So the mapping is declared by hand, per dataset, and lives beside
    the dataset loader where a reviewer can see it.
    """
    undeclared = [name for name in features_used if name not in feature_availability]
    if undeclared:
        raise LeakageError(
            f"{len(undeclared)} features have no declared availability: {undeclared[:10]}"
        )
    future = {
        name: feature_availability[name]
        for name in features_used
        if feature_availability[name] > 0
    }
    if future:
        raise LeakageError(
            f"{len(future)} features are only knowable after origination: {future}"
        )
