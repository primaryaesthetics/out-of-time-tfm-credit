"""The maturity gate has to hold, because faking it fakes the whole study.

The trap these tests are built around: labelling an immature loan non-default
rather than dropping it. That does not merely add noise. It drives the measured
default rate down in exactly the recent cohorts, so any model scored across the
trajectory appears to drift out of calibration as time advances, regardless of
the model. The study exists to detect that drift. A label that manufactures it
would produce a headline finding out of an arithmetic mistake.

So the first test builds a book where every recent loan is fine, and asserts
that those loans are removed rather than counted as good news.
"""

from __future__ import annotations

import datetime as dt

import pytest

from outoftime.label import (
    BAD_STATUSES,
    GOOD_STATUSES,
    LabelDefinition,
    LabelError,
    build_labels,
)

SNAPSHOT = dt.date(2019, 3, 1)


def d(year: int, month: int) -> dt.date:
    return dt.date(year, month, 1)


def definition(**over) -> LabelDefinition:
    return LabelDefinition(**{"window_months": 12, "snapshot": SNAPSHOT, **over})


def test_immature_loans_are_dropped_not_labelled_good():
    """The failure that would manufacture this study's own conclusion."""
    origination = [d(2015, 1), d(2016, 1), d(2018, 6), d(2019, 1)]
    status = ["Fully Paid", "Charged Off", "Current", "Current"]
    last_payment = [d(2017, 1), d(2016, 4), None, None]

    result = build_labels(origination, status, last_payment, definition())

    # 2018-06 and 2019-01 close their windows after the 2019-03 snapshot.
    assert result.dropped_immature == (2, 3)
    assert result.indices == (0, 1)
    assert result.size == 2
    assert "dropped as immature" in result.notes[0]


def test_the_cutoff_is_exactly_one_window_before_the_snapshot():
    on_the_line = definition().last_labelable_origination
    assert on_the_line == d(2018, 3)

    result = build_labels(
        [d(2018, 3), d(2018, 4)],
        ["Fully Paid", "Fully Paid"],
        [None, None],
        definition(),
    )
    assert result.indices == (0,), "the loan exactly on the cutoff is labelled"
    assert result.dropped_immature == (1,)


def test_a_charge_off_after_the_window_closes_is_not_a_default():
    """At the moment the label describes, this loan was paying."""
    # Issued 2015-01, window closes 2016-01. Last payment 2016-06 means the
    # estimated default lands at 2016-11, long after the window.
    result = build_labels(
        [d(2015, 1)], ["Charged Off"], [d(2016, 6)], definition()
    )
    assert result.labels == (0,)


def test_a_charge_off_inside_the_window_is_a_default():
    # Last payment 2015-03, plus a five-month lag, defaults at 2015-08, inside
    # a window that closes 2016-01.
    result = build_labels(
        [d(2015, 1)], ["Charged Off"], [d(2015, 3)], definition()
    )
    assert result.labels == (1,)


def test_the_lag_is_what_moves_a_loan_across_the_boundary():
    """The estimate is a policy constant, and the tests pin its effect."""
    # Last payment at 2015-09: with a five-month lag the default is 2016-02,
    # just outside a window closing 2016-01. With no lag it is inside.
    args = ([d(2015, 1)], ["Charged Off"], [d(2015, 9)])
    assert build_labels(*args, definition()).labels == (0,)
    assert build_labels(*args, definition(charge_off_lag_months=0)).labels == (1,)


def test_a_bad_loan_that_never_paid_defaults_at_origination_plus_the_lag():
    result = build_labels([d(2015, 1)], ["Charged Off"], [None], definition())
    assert result.labels == (1,)
    assert any("no last payment" in note for note in result.notes)


def test_a_wider_window_catches_a_later_default():
    """The 24-month check from ADR-0005 must disagree with the 12-month one."""
    args = ([d(2015, 1)], ["Charged Off"], [d(2016, 6)])
    assert build_labels(*args, definition(window_months=12)).labels == (0,)
    assert build_labels(*args, definition(window_months=24)).labels == (1,)


def test_a_wider_window_also_drops_more_loans():
    origination = [d(2016, 1), d(2017, 1), d(2018, 1)]
    status = ["Fully Paid"] * 3
    last_payment = [None] * 3
    twelve = build_labels(origination, status, last_payment,
                          definition(window_months=12))
    twentyfour = build_labels(origination, status, last_payment,
                              definition(window_months=24))
    assert twelve.size == 3
    assert twentyfour.size == 2, "2018-01 has no mature 24-month label"


def test_credit_policy_variants_are_terminal():
    """Found in EXP-001 at 0.12% of the book, and initially missed."""
    assert "Does not meet the credit policy. Status:Charged Off" in BAD_STATUSES
    assert "Does not meet the credit policy. Status:Fully Paid" in GOOD_STATUSES

    result = build_labels(
        [d(2015, 1), d(2015, 1)],
        ["Does not meet the credit policy. Status:Charged Off",
         "Does not meet the credit policy. Status:Fully Paid"],
        [d(2015, 2), d(2016, 1)],
        definition(),
    )
    assert result.labels == (1, 0)


def test_a_loan_still_running_is_counted_as_well_as_labelled():
    """Where a charge-off definition and a days-past-due one would differ."""
    result = build_labels(
        [d(2015, 1), d(2015, 1)],
        ["Late (31-120 days)", "Fully Paid"],
        [d(2018, 1), d(2016, 1)],
        definition(),
    )
    assert result.labels == (0, 0)
    assert result.still_running == (0,)
    assert any("days past due" in note for note in result.notes)


def test_default_rate_and_manifest_payload():
    result = build_labels(
        [d(2015, 1)] * 4,
        ["Charged Off", "Fully Paid", "Fully Paid", "Fully Paid"],
        [d(2015, 2), None, None, None],
        definition(),
    )
    assert result.default_rate == pytest.approx(0.25)
    payload = result.as_dict()
    assert payload["labelled"] == 4
    assert payload["defaults"] == 1
    assert payload["definition"]["last_labelable_origination"] == "2018-03-01"


def test_a_book_with_nothing_mature_is_refused_loudly():
    with pytest.raises(LabelError, match="nothing has a mature"):
        build_labels([d(2019, 1)], ["Current"], [None], definition())


def test_ragged_inputs_are_refused():
    with pytest.raises(LabelError, match="ragged inputs"):
        build_labels([d(2015, 1), d(2015, 2)], ["Fully Paid"], [None],
                     definition())


def test_a_status_cannot_be_both_good_and_bad():
    with pytest.raises(LabelError, match="both good and bad"):
        LabelDefinition(window_months=12, snapshot=SNAPSHOT,
                        bad_statuses=frozenset({"Fully Paid"}))


def test_a_non_positive_window_is_refused():
    with pytest.raises(LabelError, match="window_months must be positive"):
        LabelDefinition(window_months=0, snapshot=SNAPSHOT)


def test_month_arithmetic_survives_the_end_of_a_long_month():
    """31 January plus one month is 28 February, not an exception."""
    result = build_labels(
        [dt.date(2015, 1, 31)], ["Charged Off"], [dt.date(2015, 1, 31)],
        LabelDefinition(window_months=12, snapshot=SNAPSHOT,
                        charge_off_lag_months=1),
    )
    assert result.labels == (1,)


def test_a_late_loan_the_issuer_has_not_acted_on_is_counted():
    """The second maturity condition: the lag has to cover recognition.

    A borrower who stopped paying in month two of a twelve-month window is an
    in-window default under any lag below ten months. If the issuer has not yet
    charged the loan off, its status is still delinquent, the label reads
    non-default, and the window has missed a default. Left uncounted, that
    censoring lands only on the newest cohorts.
    """
    issued = dt.date(2018, 1, 1)
    labels = build_labels(
        origination=[issued, issued],
        status=["Late (31-120 days)", "Fully Paid"],
        last_payment=[dt.date(2018, 3, 1), dt.date(2018, 12, 1)],
        definition=LabelDefinition(
            window_months=12, snapshot=dt.date(2019, 3, 1), charge_off_lag_months=5),
    )
    assert labels.labels == (0, 0)
    assert labels.unrecognised == (0,)
    assert labels.unrecognised_rate == 0.5
    assert "each is a default the window misses" in " ".join(labels.notes)


def test_a_longer_lag_pushes_a_late_loan_out_of_the_window():
    # The same borrower with a lag long enough to cover recognition: the
    # estimated default date now falls after the window closes, so the loan is
    # not a default the window missed, it is a default the window excludes.
    issued = dt.date(2018, 1, 1)
    labels = build_labels(
        origination=[issued],
        status=["Late (31-120 days)"],
        last_payment=[dt.date(2018, 3, 1)],
        definition=LabelDefinition(
            window_months=12, snapshot=dt.date(2019, 3, 1), charge_off_lag_months=11),
    )
    assert labels.unrecognised == ()
    assert labels.unrecognised_rate == 0.0


def test_a_never_paying_running_loan_counts_as_unrecognised():
    issued = dt.date(2018, 1, 1)
    labels = build_labels(
        origination=[issued],
        status=["Current"],
        last_payment=[None],
        definition=LabelDefinition(window_months=12, snapshot=dt.date(2019, 3, 1)),
    )
    assert labels.unrecognised == (0,)
