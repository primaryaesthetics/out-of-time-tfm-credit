"""Which Lending Club column is knowable when, declared by hand.

`splits.assert_features_knowable` refuses any feature that is not knowable at
origination, and it can only do that against a map somebody wrote. There is no
way to infer this from the data. A column of numbers carries no record of when
it was measured, and the ones that sink a credit study look exactly like the
ones that carry it: `last_fico_range_high` is a credit score, sits beside
`fico_range_high`, and is refreshed every month of the loan's life. Train on it
and the model reads the borrower's score *after* they started missing payments.

So every one of the 151 columns is listed below with the offset, in days from
origination, at which its value becomes known. Zero means it was on the
application or came from the bureau pull that supported it. A positive number
means it is written during servicing and belongs to the future.

Two traps are worth naming before the table, because both have a plausible
column sitting next to them:

  * `chargeoff_within_12_mths` reads like an outcome and is a bureau attribute
    describing the borrower's *other* accounts at application. Measured on this
    book its mean is 0.0098 among charged-off loans against 0.0089 among fully
    paid ones, which is what an application-time input looks like: no
    separation. It is a legitimate feature.
  * `last_pymnt_d` and `loan_status` are how the label is built, and that is
    the only thing they may ever be used for. They are listed as label sources
    rather than as features so that using one by accident is a lookup failure
    rather than a silent success.

The offsets for post-origination columns are deliberately coarse. Nothing
depends on whether a servicing field appears on day 30 or day 45; what matters
is that it is after zero, and the gate only tests the sign.
"""

from __future__ import annotations

# Not features under any circumstances. Identifiers leak the row, `url` leaks
# the row, and `policy_code` is the constant 1 across the whole book.
NON_FEATURES = frozenset({"id", "member_id", "url", "policy_code"})

# The origination axis itself. It defines the split; it is never an input.
AXIS = "issue_d"

# The label is built from these and they are never inputs. ADR-0005 records
# how: terminal status plus the last payment, offset by the charge-off lag.
LABEL_SOURCES = frozenset({"loan_status", "last_pymnt_d"})

# Terms of the loan, fixed when it is written.
_LOAN_TERMS = [
    "loan_amnt", "funded_amnt", "funded_amnt_inv", "term", "int_rate",
    "installment", "grade", "sub_grade", "purpose", "title", "desc",
    "zip_code", "addr_state", "initial_list_status", "application_type",
    "disbursement_method",
]

# Stated by the borrower on the application, and in some years verified.
_APPLICATION = [
    "emp_title", "emp_length", "home_ownership", "annual_inc",
    "verification_status", "dti", "annual_inc_joint", "dti_joint",
    "verification_status_joint",
]

# The bureau pull that supported the decision. Every one of these describes the
# borrower's history *before* this loan existed, including the delinquency and
# charge-off counters, which are about their other accounts.
_BUREAU_AT_APPLICATION = [
    "delinq_2yrs", "earliest_cr_line", "fico_range_low", "fico_range_high",
    "inq_last_6mths", "mths_since_last_delinq", "mths_since_last_record",
    "open_acc", "pub_rec", "revol_bal", "revol_util", "total_acc",
    "collections_12_mths_ex_med", "mths_since_last_major_derog",
    "acc_now_delinq", "tot_coll_amt", "tot_cur_bal", "open_acc_6m",
    "open_act_il", "open_il_12m", "open_il_24m", "mths_since_rcnt_il",
    "total_bal_il", "il_util", "open_rv_12m", "open_rv_24m", "max_bal_bc",
    "all_util", "total_rev_hi_lim", "inq_fi", "total_cu_tl", "inq_last_12m",
    "acc_open_past_24mths", "avg_cur_bal", "bc_open_to_buy", "bc_util",
    "chargeoff_within_12_mths", "delinq_amnt", "mo_sin_old_il_acct",
    "mo_sin_old_rev_tl_op", "mo_sin_rcnt_rev_tl_op", "mo_sin_rcnt_tl",
    "mort_acc", "mths_since_recent_bc", "mths_since_recent_bc_dlq",
    "mths_since_recent_inq", "mths_since_recent_revol_delinq",
    "num_accts_ever_120_pd", "num_actv_bc_tl", "num_actv_rev_tl",
    "num_bc_sats", "num_bc_tl", "num_il_tl", "num_op_rev_tl", "num_rev_accts",
    "num_rev_tl_bal_gt_0", "num_sats", "num_tl_120dpd_2m", "num_tl_30dpd",
    "num_tl_90g_dpd_24m", "num_tl_op_past_12m", "pct_tl_nvr_dlq",
    "percent_bc_gt_75", "pub_rec_bankruptcies", "tax_liens", "tot_hi_cred_lim",
    "total_bal_ex_mort", "total_bc_limit", "total_il_high_credit_limit",
]

# The co-applicant, pulled at the same moment as the primary borrower's.
_SECONDARY_APPLICANT = [
    "revol_bal_joint", "sec_app_fico_range_low", "sec_app_fico_range_high",
    "sec_app_earliest_cr_line", "sec_app_inq_last_6mths", "sec_app_mort_acc",
    "sec_app_open_acc", "sec_app_revol_util", "sec_app_open_act_il",
    "sec_app_num_rev_accts", "sec_app_chargeoff_within_12_mths",
    "sec_app_collections_12_mths_ex_med",
    "sec_app_mths_since_last_major_derog",
]

# Written while the loan is being serviced. Each of these is the future.
_SERVICING = [
    "pymnt_plan", "out_prncp", "out_prncp_inv", "total_pymnt",
    "total_pymnt_inv", "total_rec_prncp", "total_rec_int",
    "total_rec_late_fee", "recoveries", "collection_recovery_fee",
    "last_pymnt_amnt", "next_pymnt_d", "last_credit_pull_d",
    "last_fico_range_high", "last_fico_range_low",
]

# Hardship and settlement programmes: entered only by loans already in trouble,
# so these are close to being the label written under another name.
_DISTRESS = [
    "hardship_flag", "hardship_type", "hardship_reason", "hardship_status",
    "deferral_term", "hardship_amount", "hardship_start_date",
    "hardship_end_date", "payment_plan_start_date", "hardship_length",
    "hardship_dpd", "hardship_loan_status",
    "orig_projected_additional_accrued_interest",
    "hardship_payoff_balance_amount", "hardship_last_payment_amount",
    "debt_settlement_flag", "debt_settlement_flag_date", "settlement_status",
    "settlement_date", "settlement_amount", "settlement_percentage",
    "settlement_term",
]

FEATURE_AVAILABILITY: dict[str, int] = {
    **{name: 0 for name in _LOAN_TERMS},
    **{name: 0 for name in _APPLICATION},
    **{name: 0 for name in _BUREAU_AT_APPLICATION},
    **{name: 0 for name in _SECONDARY_APPLICANT},
    # 30 days stands for "during servicing". The gate tests the sign, not the
    # size, and pretending to know the exact day would be false precision.
    **{name: 30 for name in _SERVICING},
    **{name: 30 for name in _DISTRESS},
}

# Every column in accepted_2007_to_2018Q4.csv.gz, accounted for exactly once.
ALL_COLUMNS = (
    frozenset(FEATURE_AVAILABILITY)
    | NON_FEATURES
    | LABEL_SOURCES
    | {AXIS}
)


def safe_features() -> tuple[str, ...]:
    """The columns a model may see, sorted, with nothing else in them."""
    return tuple(sorted(
        name for name, offset in FEATURE_AVAILABILITY.items() if offset <= 0
    ))


def leaking_features() -> tuple[str, ...]:
    """The columns that would import the future, named so tests can use them."""
    return tuple(sorted(
        name for name, offset in FEATURE_AVAILABILITY.items() if offset > 0
    ))


def audit_columns(columns) -> dict[str, tuple[str, ...]]:
    """Compares a file's header against this map, both directions.

    A release of this dataset that adds a column must fail loudly rather than
    let an undeclared field through as though it had been considered.
    """
    present = frozenset(columns)
    return {
        "undeclared": tuple(sorted(present - ALL_COLUMNS)),
        "declared_but_absent": tuple(sorted(ALL_COLUMNS - present)),
    }
