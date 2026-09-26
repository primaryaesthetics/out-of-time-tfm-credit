"""A default label with a fixed performance window, and the maturity gate.

The gate is the point of this module, and it is load-bearing for the whole
study in a way that is worth stating plainly.

A loan originated three months before the data ends has not had time to default
within a twelve-month window. Its label is not zero. It is *unknown*, and the
difference decides whether this study measures anything. Label it zero and the
recent cohorts acquire an artificially low default rate; a model scored across
those cohorts then appears to lose calibration as time advances, and it appears
to do so no matter which model it is. That is the exact shape of the finding
this project exists to test for, manufactured out of nothing but a bad label.

So immature loans are removed, never defaulted. `LabelSet` reports how many it
dropped and why, and the counts belong in the manifest of any run that uses it.

The second thing here is that the default *date* is estimated, because Lending
Club publishes no charge-off date. The only timing signal is the last payment,
and the estimate is `last_payment + charge_off_lag`, with the lag standing for
the issuer's practice of charging a loan off after a set delinquency. ADR-0005
records the choice and its uncertainty. The bias runs one way across the whole
book, since the practice is a policy rather than a per-loan accident, so
cohorts stay comparable even where the level is off.

The lag also has to cover the issuer's own recognition delay, and that is a
second maturity condition the cutoff does not express. A loan that stopped
paying inside the window but has not been charged off at the snapshot is still
sitting in a delinquent status, so it is labelled non-default and the window
misses a default it should have caught. That censoring falls entirely on the
newest cohorts, which is the same manufactured shape the immaturity gate exists
to prevent. Shortening the lag brings it back: the window then admits loans that
stopped paying too recently for the issuer to have acted. So `LabelSet` counts
them, `unrecognised_rate` reports the share, and a configuration that produces a
non-zero count is one whose late cohorts are not comparable to its early ones.

Works on plain sequences so it can sit under pandas, polars or numpy.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass, field

Date = dt.date

# Terminal states. "Default" and "Charged Off" are distinct in this book and
# both are terminal. The credit-policy variants were found in EXP-001 and are
# 0.12% of the book; they are terminal too and omitting them was an oversight
# rather than a definition.
BAD_STATUSES = frozenset({
    "Charged Off",
    "Default",
    "Does not meet the credit policy. Status:Charged Off",
})
GOOD_STATUSES = frozenset({
    "Fully Paid",
    "Does not meet the credit policy. Status:Fully Paid",
})
TERMINAL_STATUSES = BAD_STATUSES | GOOD_STATUSES


class LabelError(AssertionError):
    """A label that cannot be constructed honestly from what is available."""


@dataclass(frozen=True)
class LabelDefinition:
    """Every choice that decides the label, in one object that a manifest eats.

    `window_months` is the performance window measured from origination.
    `charge_off_lag_months` converts a last payment into an estimated default
    date. `snapshot` is the last date on which performance is observable; a
    loan whose window closes after it cannot be labelled at all.
    """

    window_months: int
    snapshot: Date
    charge_off_lag_months: int = 5
    bad_statuses: frozenset[str] = BAD_STATUSES
    good_statuses: frozenset[str] = GOOD_STATUSES

    def __post_init__(self) -> None:
        if self.window_months <= 0:
            raise LabelError("window_months must be positive")
        if self.charge_off_lag_months < 0:
            raise LabelError("charge_off_lag_months cannot be negative")
        if self.bad_statuses & self.good_statuses:
            raise LabelError(
                "a status cannot be both good and bad: "
                f"{sorted(self.bad_statuses & self.good_statuses)}"
            )

    @property
    def last_labelable_origination(self) -> Date:
        """The newest origination whose window has closed by the snapshot."""
        return add_months(self.snapshot, -self.window_months)

    def as_dict(self) -> dict:
        return {
            "window_months": self.window_months,
            "snapshot": self.snapshot.isoformat(),
            "charge_off_lag_months": self.charge_off_lag_months,
            "last_labelable_origination":
                self.last_labelable_origination.isoformat(),
            "bad_statuses": sorted(self.bad_statuses),
            "good_statuses": sorted(self.good_statuses),
        }


@dataclass(frozen=True)
class LabelSet:
    """Labels for the rows that could be labelled, and an account of the rest."""

    definition: LabelDefinition
    indices: tuple[int, ...]
    labels: tuple[int, ...]
    dropped_immature: tuple[int, ...]
    still_running: tuple[int, ...]
    unrecognised: tuple[int, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def size(self) -> int:
        return len(self.indices)

    @property
    def default_rate(self) -> float:
        return sum(self.labels) / self.size if self.size else 0.0

    @property
    def unrecognised_rate(self) -> float:
        """The share of labelled loans the issuer had not yet charged off.

        Zero means the charge-off lag is at least the issuer's own recognition
        delay, so every default the window admits had been recorded as one by
        the snapshot. A non-zero value is censoring that falls entirely on the
        newest cohorts, which is the shape of a manufactured finding, and it
        rises as the lag is shortened.
        """
        return len(self.unrecognised) / self.size if self.size else 0.0

    def as_dict(self) -> dict:
        """What a run manifest records about how the label was built."""
        return {
            "definition": self.definition.as_dict(),
            "labelled": self.size,
            "defaults": sum(self.labels),
            "default_rate": round(self.default_rate, 6),
            "dropped_immature": len(self.dropped_immature),
            "still_running_at_snapshot": len(self.still_running),
            "unrecognised": len(self.unrecognised),
            "notes": list(self.notes),
        }


def add_months(date: Date, months: int) -> Date:
    """Calendar-month arithmetic, clamped to the end of a short month."""
    total = date.month - 1 + months
    year = date.year + total // 12
    month = total % 12 + 1
    day = min(date.day, _days_in_month(year, month))
    return dt.date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (dt.date(year, month + 1, 1) - dt.timedelta(1)).day


def build_labels(
    origination: Sequence[Date],
    status: Sequence[str],
    last_payment: Sequence[Date | None],
    definition: LabelDefinition,
) -> LabelSet:
    """Labels every loan whose performance window has closed, and only those.

    A loan is a default when its status is terminal-bad *and* the estimated
    default date falls inside the window. A loan that eventually charged off,
    but was still paying when the window closed, is not a default: at the point
    the label describes, it was performing. Getting that backwards imports the
    future into the label, which is the same failure the split module exists to
    prevent, arriving through a different door.

    A missing last payment on a bad loan means the borrower never paid at all,
    so the default is dated at origination plus the lag.
    """
    n = len(origination)
    if not (len(status) == len(last_payment) == n):
        raise LabelError(
            f"ragged inputs: {n} originations, {len(status)} statuses, "
            f"{len(last_payment)} last payments"
        )
    if n == 0:
        raise LabelError("no rows")

    cutoff = definition.last_labelable_origination
    indices, labels = [], []
    immature, running, unrecognised = [], [], []
    never_paid = 0

    for i in range(n):
        issued = origination[i]
        if issued is None:
            raise LabelError(f"row {i} has no origination date")

        # The gate. Everything else in this module is downstream of it.
        if issued > cutoff:
            immature.append(i)
            continue

        state = status[i]
        if state in definition.bad_statuses:
            paid_until = last_payment[i]
            if paid_until is None:
                never_paid += 1
                estimated = add_months(issued, definition.charge_off_lag_months)
            else:
                estimated = add_months(
                    paid_until, definition.charge_off_lag_months)
            window_closes = add_months(issued, definition.window_months)
            labels.append(1 if estimated <= window_closes else 0)
        elif state in definition.good_statuses:
            labels.append(0)
        else:
            # Still running at the snapshot. Its window has closed, so it did
            # not charge off inside the window, whatever it does afterwards.
            # Counted, because a definition built on charge-off is stricter
            # than one built on 90 days past due, and a loan sitting in "Late"
            # at the snapshot is where the two disagree.
            running.append(i)
            labels.append(0)
            paid_until = last_payment[i]
            estimated = add_months(
                issued if paid_until is None else paid_until,
                definition.charge_off_lag_months,
            )
            if estimated <= add_months(issued, definition.window_months):
                unrecognised.append(i)
        indices.append(i)

    if not indices:
        raise LabelError(
            f"no loan was originated on or before {cutoff.isoformat()}, so "
            f"nothing has a mature {definition.window_months}-month label"
        )

    notes = [
        (
            f"{len(immature)} loans originated after {cutoff.isoformat()} were "
            f"dropped as immature, not labelled non-default"
        ),
    ]
    if running:
        notes.append(
            f"{len(running)} loans were still running at the snapshot and are "
            f"labelled non-default: this definition turns on charge-off, not "
            f"on days past due, and those are the rows where the two differ"
        )
    if never_paid:
        notes.append(
            f"{never_paid} bad loans had no last payment and were dated at "
            f"origination plus {definition.charge_off_lag_months} months"
        )
    notes.append(
        f"{len(unrecognised)} labelled loans stopped paying early enough to be "
        f"in-window defaults and had not been charged off at the snapshot; they "
        f"are labelled non-default and each is a default the window misses"
    )

    return LabelSet(
        definition=definition,
        indices=tuple(indices),
        labels=tuple(labels),
        dropped_immature=tuple(immature),
        still_running=tuple(running),
        unrecognised=tuple(unrecognised),
        notes=tuple(notes),
    )
