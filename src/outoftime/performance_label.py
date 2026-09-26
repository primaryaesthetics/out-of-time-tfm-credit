"""A default label read off a monthly performance history, with the maturity gate.

The Lending Club label in `label.py` has to estimate the default date, because
that book reports a terminal status and a last payment and nothing between.
A servicing file is the opposite case: every month of every loan is on record,
with a delinquency status in each, so the default is observed rather than
inferred. What does not change is the gate. A loan whose history ends before
the window closes, and ends without a termination, has an unknown label, and
labelling it non-default manufactures the finding this study exists to test
for. So such loans are dropped, counted, and reported, exactly as in `label.py`.

The gate has two parts, and the second is the one that is easy to leave out. A
loan is immature when its record ends inside the window without a termination.
It is also immature when its window has not closed by the performance cutoff,
*whatever its record says*: a loan that defaulted at month three, or paid off
at month five, two months before the cutoff has a resolved outcome and belongs
to a cohort whose other loans do not. Label the resolved ones and drop the
rest and the cohort's rate is computed over its early defaults and early
payoffs alone, which overstates it by a factor that grows as the cohort gets
younger. So the cutoff test runs first and drops the whole tail of the book,
resolved or not, exactly as the origination cutoff does in `label.py`.

The history of a loan is reduced to five values before it reaches this module,
because the label needs no more than that and the full file is eight gigabytes:

  * ``first_payment``: the first payment month, the clock's origin;
  * ``last_age``: the age, in months from the first payment month, of the
    last performance record on file;
  * ``first_bad_age``: the age of the first month in which the loan was at
    least ninety days past due, or in REO, or ``None``;
  * ``termination_code``: the zero-balance code that closed the loan, or
    ``None`` if it is still on the books;
  * ``termination_age``: the age at which it closed.

Age runs from the first payment date, not from Freddie Mac's own loan-age
field, which resets when a loan is modified and would then let a modified loan
re-enter the window.

Termination codes fall into three groups and the label treats them differently.
A voluntary payoff before the window closes is a resolved good loan: it cannot
default afterwards. A short sale, third-party sale or REO disposition is a
default, dated at the termination if no ninety-day delinquency preceded it. A
whole-loan sale, a reperforming-loan sale or a confirmed defect removes the loan
from the dataset without saying what it went on to do, so a loan that leaves
that way inside the window with no default on record is censored and dropped,
not labelled.

A loan can also enter the file late. Some loans are acquired seasoned, and
their servicing record begins months or years after the first payment; a
window whose first months are not on file cannot show a default in them, and a
loan ninety days late before it was acquired would not have been acquired.
Labelled over the full window, such a loan is labelled on the part of it that
was observed, and the bias runs one way. A record with a month missing
between its first month and the close of the window is the same gap in
another place; the caller reads it from the window's months, since a month
missing after the window says nothing about the window. `max_first_observed_age` excludes
every loan whose first record is later than that age and counts it as
left-truncated, and `exclude_record_gaps` excludes every loan whose record
has a gap and counts it apart. Both default to off, which is the label this
module has always built; `MAX_FIRST_OBSERVED_AGE` is the age the second book
runs at.

Works on plain sequences so it can sit under pandas, polars or numpy.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass, field

Date = dt.date

# Zero-balance codes, from the user guide.
PREPAID = frozenset({1})                 # Prepaid or Matured (Voluntary Payoff)
BAD_TERMINATIONS = frozenset({2, 3, 9})  # Third Party Sale; Short Sale or
                                         # Charge Off; REO Disposition
CENSORING = frozenset({15, 16, 96})      # Whole Loan Sale; Reperforming Loan
                                         # Sale; Confirmed Defect

# The delinquency status at or above which a month counts as a default event.
# Status 03 is 90 to 119 days past due. The reducer applies this threshold when
# it computes `first_bad_age`; it is recorded here so a definition names the
# rule the history was built under.
DELINQUENCY_MONTHS = 3

# The latest first record a loan may have and still be labelled on the second
# book (EXP-005). The first ninety-day month on the book falls at age three on
# hundreds of loans and earlier on two, so a loan first observed at or before
# age three misses no event this label reads, and one first observed later
# may have missed one.
MAX_FIRST_OBSERVED_AGE = 3


class LabelError(AssertionError):
    """A label that cannot be constructed honestly from what is available."""


@dataclass(frozen=True)
class LoanHistory:
    """What the label needs of a loan's servicing record, and nothing else."""

    first_payment: Date
    last_age: int
    first_bad_age: int | None = None
    termination_code: int | None = None
    termination_age: int | None = None
    # The age of the loan's first performance record, or None when it was
    # not read. Needed only when the definition sets `max_first_observed_age`.
    first_observed_age: int | None = None
    # Whether a month is missing between the loan's first record and the
    # close of the window the caller labels under; the caller reads it from
    # the window's months. Read only when the definition sets
    # `exclude_record_gaps`.
    record_gap: bool = False

    def __post_init__(self) -> None:
        if self.termination_code is not None and self.termination_age is None:
            raise LabelError("a terminated loan needs a termination age")
        if self.first_bad_age is not None and self.first_bad_age < 0:
            raise LabelError("first_bad_age cannot be negative")


def months_observable(first_payment: Date, cutoff: Date) -> int:
    """Months of a loan's life on file by the cutoff: one in the first payment
    month, so a first payment in the cutoff month is one month observable."""
    return (cutoff.year - first_payment.year) * 12 + cutoff.month - first_payment.month + 1


@dataclass(frozen=True)
class PerformanceLabelDefinition:
    """Every choice that decides the label, in one object that a manifest eats.

    `window_months` is the performance window, in months from the first
    payment month. `performance_cutoff` is the last month on file, recorded
    so a manifest says what "immature" was measured against.
    """

    window_months: int
    performance_cutoff: Date
    delinquency_months: int = DELINQUENCY_MONTHS
    # Whether a delinquent month spent under a payment-relief plan or a
    # declared disaster hardship counts as a default event. The reducer keeps
    # both readings of `first_bad_age`; this records which one was passed.
    relief_months_count: bool = True
    bad_terminations: frozenset[int] = BAD_TERMINATIONS
    prepaid: frozenset[int] = PREPAID
    censoring: frozenset[int] = CENSORING
    # The latest age at which a loan's servicing record may begin for it to be
    # labelled. None labels every loan whatever its first record; see the
    # module docstring.
    max_first_observed_age: int | None = None
    # Whether a loan whose record has a gap is excluded rather than labelled.
    exclude_record_gaps: bool = False

    def __post_init__(self) -> None:
        if self.window_months <= 0:
            raise LabelError("window_months must be positive")
        if self.max_first_observed_age is not None and self.max_first_observed_age < 0:
            raise LabelError("max_first_observed_age cannot be negative")
        overlap = (
            (self.bad_terminations & self.prepaid)
            | (self.bad_terminations & self.censoring)
            | (self.prepaid & self.censoring)
        )
        if overlap:
            raise LabelError(f"a termination code cannot be in two groups: {sorted(overlap)}")

    def as_dict(self) -> dict:
        out = {
            "window_months": self.window_months,
            "performance_cutoff": self.performance_cutoff.isoformat(),
            "delinquency_months": self.delinquency_months,
            "relief_months_count": self.relief_months_count,
            "bad_terminations": sorted(self.bad_terminations),
            "prepaid": sorted(self.prepaid),
            "censoring": sorted(self.censoring),
        }
        if self.max_first_observed_age is not None:
            out["max_first_observed_age"] = self.max_first_observed_age
        if self.exclude_record_gaps:
            out["exclude_record_gaps"] = True
        return out


@dataclass(frozen=True)
class PerformanceLabelSet:
    """Labels for the loans that could be labelled, and an account of the rest."""

    definition: PerformanceLabelDefinition
    indices: tuple[int, ...]
    labels: tuple[int, ...]
    dropped_immature: tuple[int, ...]
    censored: tuple[int, ...]
    left_truncated: tuple[int, ...] = ()
    record_gaps: tuple[int, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def size(self) -> int:
        return len(self.indices)

    @property
    def default_rate(self) -> float:
        return sum(self.labels) / self.size if self.size else 0.0

    def as_dict(self) -> dict:
        """What a run manifest records about how the label was built."""
        out = {
            "definition": self.definition.as_dict(),
            "labelled": self.size,
            "defaults": sum(self.labels),
            "default_rate": round(self.default_rate, 6),
            "dropped_immature": len(self.dropped_immature),
            "censored": len(self.censored),
            "notes": list(self.notes),
        }
        if self.definition.max_first_observed_age is not None:
            out["left_truncated"] = len(self.left_truncated)
        if self.definition.exclude_record_gaps:
            out["record_gaps"] = len(self.record_gaps)
        return out


def build_performance_labels(
    histories: Sequence[LoanHistory],
    definition: PerformanceLabelDefinition,
) -> PerformanceLabelSet:
    """Labels every loan whose window has closed by the cutoff, and only those.

    In order, for each loan:

      0. a loan whose window has not closed by the performance cutoff is
         immature, whatever its record says, so that a cohort's rate is
         never computed over its early defaults and early payoffs alone;
         then, when `max_first_observed_age` is set, a loan whose first
         record is later than that age is left-truncated and dropped, and
         when `exclude_record_gaps` is set, a loan whose record has a gap is
         dropped and counted apart;
      1. a default event at or before the window closes is a default, whether
         it is a ninety-day delinquency or a bad termination;
      2. otherwise a history observed through the window is a non-default;
      3. otherwise a voluntary payoff inside the window is a non-default,
         because a loan that is gone cannot default;
      4. otherwise a censoring termination inside the window is censored;
      5. otherwise the history is too short, and the loan is immature.

    The order matters in one place: a loan that was ninety days past due at
    month six and prepaid at month nine is a default, not a payoff.
    """
    if not histories:
        raise LabelError("no rows")

    window = definition.window_months
    cutoff = definition.performance_cutoff
    indices: list[int] = []
    labels: list[int] = []
    immature: list[int] = []
    unclosed = 0
    censored: list[int] = []
    truncated: list[int] = []
    gapped: list[int] = []
    defaults_by_termination_only = 0
    latest_start = definition.max_first_observed_age

    for i, history in enumerate(histories):
        if months_observable(history.first_payment, cutoff) < window:
            immature.append(i)
            unclosed += 1
            continue

        if latest_start is not None:
            if history.first_observed_age is None:
                raise LabelError(
                    f"row {i}: the definition excludes loans first observed after age "
                    f"{latest_start}, and this history does not say when it was first "
                    f"observed"
                )
            if history.first_observed_age > latest_start:
                truncated.append(i)
                continue

        if definition.exclude_record_gaps and history.record_gap:
            gapped.append(i)
            continue

        bad_age = history.first_bad_age
        code = history.termination_code
        terminated_badly = code is not None and code in definition.bad_terminations
        if terminated_badly and (bad_age is None or history.termination_age < bad_age):
            if bad_age is None:
                defaults_by_termination_only += 1
            bad_age = history.termination_age

        observed_through = history.last_age >= window
        prepaid = code is not None and code in definition.prepaid
        if bad_age is not None and bad_age <= window:
            indices.append(i)
            labels.append(1)
        elif observed_through or prepaid:
            indices.append(i)
            labels.append(0)
        elif code is not None and code in definition.censoring:
            censored.append(i)
        elif terminated_badly:
            # Terminated badly after the window on a history shorter than the
            # window: impossible unless the ages disagree. Refuse rather than
            # guess.
            raise LabelError(
                f"row {i}: bad termination at age {history.termination_age} "
                f"but only {history.last_age} months of history"
            )
        else:
            immature.append(i)

    if not indices:
        raise LabelError(
            f"no loan has a resolved {window}-month label; the histories end "
            f"before the window closes"
        )

    notes = [
        (
            f"{unclosed} loans have a first payment within {window} months of "
            f"the cutoff {cutoff.isoformat()} and were dropped as immature "
            f"whatever their record says, and {len(immature) - unclosed} more "
            f"have fewer than {window} months of history, no termination and no "
            f"default on record; none was labelled non-default"
        ),
        (
            f"{len(censored)} loans left the dataset inside the window through a "
            f"sale or a confirmed defect with no default on record, and were "
            f"dropped as censored"
        ),
    ]
    if latest_start is not None:
        notes.append(
            f"{len(truncated)} loans were first observed after age {latest_start} and "
            f"were dropped as left-truncated: the months before their first record "
            f"are inside the window and not on file"
        )
    if definition.exclude_record_gaps:
        notes.append(
            f"{len(gapped)} loans with a month missing from their record inside the window "
            f"were dropped: a default in the missing month would not be on file"
        )
    if defaults_by_termination_only:
        notes.append(
            f"{defaults_by_termination_only} loans ended in a bad termination with "
            f"no ninety-day delinquency on record before it, and are dated at "
            f"the termination"
        )

    return PerformanceLabelSet(
        definition=definition,
        indices=tuple(indices),
        labels=tuple(labels),
        dropped_immature=tuple(immature),
        censored=tuple(censored),
        left_truncated=tuple(truncated),
        record_gaps=tuple(gapped),
        notes=tuple(notes),
    )
