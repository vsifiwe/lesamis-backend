"""
ledger_service.py

Auto-generates LedgerEntry rows whenever money moves.
Call the appropriate function from the view/serializer after the source record is saved.
"""
from decimal import Decimal

from .models import FundAccount, LedgerEntry, Penalty

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_fund_cache: dict[str, FundAccount] = {}


def _get_fund(code: str) -> FundAccount:
    if code not in _fund_cache:
        _fund_cache[code] = FundAccount.objects.get(code=code)
    return _fund_cache[code]


def _entry(fund_account, member, entry_date, entry_type, amount, direction,
           reference_id, reference_type, recorded_by, notes='') -> LedgerEntry:
    return LedgerEntry(
        fund_account=fund_account,
        member=member,
        entry_date=entry_date,
        entry_type=entry_type,
        amount=Decimal(str(amount)),
        direction=direction,
        reference_id=reference_id,
        reference_type=reference_type,
        notes=notes,
        recorded_by=recorded_by,
    )


# ---------------------------------------------------------------------------
# Public recording functions
# ---------------------------------------------------------------------------

def record_contribution_receipt(receipt, user):
    """
    For each receipt item create ledger entries split across CAPITAL / SOCIAL / SOCIAL_PLUS,
    plus one LATE_PENALTY credit entry per outstanding penalty linked to the receipt.
    """
    capital     = _get_fund('CAPITAL')
    social      = _get_fund('SOCIAL')
    social_plus = _get_fund('SOCIAL_PLUS')

    entries = []
    items = receipt.items.select_related('obligation__member').all()

    for item in items:
        obligation = item.obligation
        member     = obligation.member
        ref_id     = receipt.id
        ref_type   = 'contribution_receipt'
        date       = receipt.received_date

        if obligation.capital_amount_expected:
            entries.append(_entry(
                capital, member, date,
                LedgerEntry.EntryType.CONTRIBUTION_CAPITAL,
                obligation.capital_amount_expected,
                LedgerEntry.Direction.CREDIT,
                ref_id, ref_type, user,
            ))

        if obligation.social_amount_expected:
            entries.append(_entry(
                social, member, date,
                LedgerEntry.EntryType.CONTRIBUTION_SOCIAL,
                obligation.social_amount_expected,
                LedgerEntry.Direction.CREDIT,
                ref_id, ref_type, user,
            ))

        if obligation.social_plus_amount_expected:
            entries.append(_entry(
                social_plus, member, date,
                LedgerEntry.EntryType.CONTRIBUTION_SOCIAL_PLUS,
                obligation.social_plus_amount_expected,
                LedgerEntry.Direction.CREDIT,
                ref_id, ref_type, user,
            ))

        penalties = Penalty.objects.filter(
            contribution_obligation=obligation,
            receipt=receipt,
            waived=False,
        )
        for penalty in penalties:
            entries.append(_entry(
                capital, member, date,
                LedgerEntry.EntryType.LATE_PENALTY,
                penalty.amount,
                LedgerEntry.Direction.CREDIT,
                ref_id, ref_type, user,
            ))

    LedgerEntry.objects.bulk_create(entries)


def record_loan_disbursement(loan, user):
    """Debit CAPITAL when a loan is issued."""
    LedgerEntry.objects.create(
        fund_account=_get_fund('CAPITAL'),
        member=loan.member,
        entry_date=loan.issued_date,
        entry_type=LedgerEntry.EntryType.LOAN_DISBURSEMENT,
        amount=loan.principal_amount,
        direction=LedgerEntry.Direction.DEBIT,
        reference_id=loan.id,
        reference_type='loan',
        recorded_by=user,
    )


def record_loan_repayment(repayment, user):
    """Credit CAPITAL when a loan repayment is recorded."""
    LedgerEntry.objects.create(
        fund_account=_get_fund('CAPITAL'),
        member=repayment.loan.member,
        entry_date=repayment.paid_date,
        entry_type=LedgerEntry.EntryType.LOAN_REPAYMENT,
        amount=repayment.amount_paid,
        direction=LedgerEntry.Direction.CREDIT,
        reference_id=repayment.id,
        reference_type='loan_repayment',
        recorded_by=user,
    )


def record_other_charge(charge, user):
    """Mirror the charge's own direction into the specified fund account."""
    LedgerEntry.objects.create(
        fund_account=charge.fund_account,
        member=None,
        entry_date=charge.charge_date,
        entry_type=LedgerEntry.EntryType.OTHER_CHARGE,
        amount=charge.amount,
        direction=charge.direction,
        reference_id=charge.id,
        reference_type='other_charge',
        notes=charge.description,
        recorded_by=user,
    )


def record_investment_purchase(investment, user):
    """Debit CAPITAL when an investment is purchased."""
    LedgerEntry.objects.create(
        fund_account=_get_fund('CAPITAL'),
        member=None,
        entry_date=investment.investment_date,
        entry_type=LedgerEntry.EntryType.INVESTMENT_PURCHASE,
        amount=investment.amount_invested,
        direction=LedgerEntry.Direction.DEBIT,
        reference_id=investment.id,
        reference_type='investment',
        recorded_by=user,
    )


def record_investment_profit(profit_entry, user):
    """Credit CAPITAL when investment profit is recorded."""
    LedgerEntry.objects.create(
        fund_account=_get_fund('CAPITAL'),
        member=None,
        entry_date=profit_entry.profit_date,
        entry_type=LedgerEntry.EntryType.INVESTMENT_PROFIT,
        amount=profit_entry.amount,
        direction=LedgerEntry.Direction.CREDIT,
        reference_id=profit_entry.id,
        reference_type='investment_profit_entry',
        recorded_by=user,
    )


def record_social_expense(social_record, user):
    """Debit the social record's fund account (SOCIAL or SOCIAL_PLUS)."""
    code = social_record.fund_account.code
    entry_type = (
        LedgerEntry.EntryType.SOCIAL_EXPENSE
        if code == 'SOCIAL'
        else LedgerEntry.EntryType.SOCIAL_PLUS_EXPENSE
    )
    LedgerEntry.objects.create(
        fund_account=social_record.fund_account,
        member=None,
        entry_date=social_record.activity_date,
        entry_type=entry_type,
        amount=social_record.amount,
        direction=LedgerEntry.Direction.DEBIT,
        reference_id=social_record.id,
        reference_type='social_activity_record',
        recorded_by=user,
    )
