from decimal import Decimal

from django.db import connection, transaction
from django.db.models import Sum

from .models import (
    BankReconciliationSnapshot,
    ContributionCycle,
    ContributionReceipt,
    HistoricalContributionEntry,
    ImportBatch,
    IncomeEntry,
    Investment,
    InvestmentProfitEntry,
    LedgerEntry,
    Loan,
    LoanProduct,
    LoanRepayment,
    LoanRepaymentSchedule,
    Member,
    MemberShareAccount,
    OtherCharge,
    SocialActivityRecord,
    SourceReference,
)
from .workbook_manifest import CONTRIBUTION_FUNDS, expected_assets, expected_counts, financial_report
from .workbook_writer import write_workbook


RECORD_QUERIES = {
    'members': Member.objects.all(),
    'share_accounts': MemberShareAccount.objects.all(),
    'contributions': HistoricalContributionEntry.objects.all(),
    'active_loans': Loan.objects.filter(is_opening_balance=False),
    'historical_loans': Loan.objects.filter(is_opening_balance=True),
    'loan_repayments': LoanRepayment.objects.all(),
    'loan_installments': LoanRepaymentSchedule.objects.all(),
    'social_expenses': SocialActivityRecord.objects.all(),
    'income': IncomeEntry.objects.all(),
    'bank_charges': OtherCharge.objects.all(),
    'investments': Investment.objects.all(),
    'investment_profits': InvestmentProfitEntry.objects.all(),
    'bank_snapshots': BankReconciliationSnapshot.objects.all(),
    'ledger_entries': LedgerEntry.objects.all(),
    'source_references': SourceReference.objects.all(),
}
BUSINESS_MODELS = {
    *(query.model for query in RECORD_QUERIES.values()),
    ImportBatch, LoanProduct, ContributionCycle, ContributionReceipt,
}


class WorkbookImportError(Exception):
    def __init__(self, message, report=None):
        super().__init__(message)
        self.report = report or {}


def database_totals():
    def total(queryset, field='amount'):
        return queryset.aggregate(value=Sum(field))['value'] or Decimal('0.00')

    active = Loan.objects.filter(status=Loan.Status.ACTIVE)
    totals = {
        f'contribution_{fund}': total(HistoricalContributionEntry.objects.filter(fund_type=fund))
        for fund in CONTRIBUTION_FUNDS
    }
    totals.update(
        social_expenses=total(SocialActivityRecord.objects.filter(fund_account__code='SOCIAL')),
        social_plus_expenses=total(SocialActivityRecord.objects.filter(fund_account__code='SOCIAL_PLUS')),
        bank_interest=total(IncomeEntry.objects.filter(income_type='bank_interest')),
        joining_fees=total(IncomeEntry.objects.filter(income_type='joining_fee')),
        collected_penalties=total(IncomeEntry.objects.filter(
            income_type__in=('contribution_penalty', 'loan_exit_penalty'),
        )),
        bank_charges=total(OtherCharge.objects.filter(charge_type='bank_charge', direction='debit')),
        loan_principal=total(Loan.objects.all(), 'principal_amount'),
        loan_repayments=total(LoanRepayment.objects.all(), 'amount_paid'),
        active_loan_principal=total(active, 'principal_amount'),
        active_loan_outstanding=total(active, 'source_outstanding_amount'),
        investments=total(Investment.objects.all(), 'amount_invested'),
        investment_profits=total(InvestmentProfitEntry.objects.all()),
        calculated_cash_balance=(
            total(LedgerEntry.objects.filter(direction=LedgerEntry.Direction.CREDIT))
            - total(LedgerEntry.objects.filter(direction=LedgerEntry.Direction.DEBIT))
        ),
        shares=total(MemberShareAccount.objects.all(), 'share_count'),
    )
    totals['loan_interest'] = total(Loan.objects.all(), 'total_repayment_amount') - totals['loan_principal']
    totals['expected_total_assets'] = expected_assets(totals)
    return totals


def lock_import_tables():
    tables = ', '.join(connection.ops.quote_name(name) for name in sorted(
        model._meta.db_table for model in BUSINESS_MODELS
    ))
    # Also blocks business writes from other connections between the empty check and commit.
    with connection.cursor() as cursor:
        cursor.execute(f'LOCK TABLE {tables} IN SHARE ROW EXCLUSIVE MODE')


@transaction.atomic
def apply_workbook(data, manifest_sha256, operator, preview):
    if connection.vendor != 'postgresql':
        raise WorkbookImportError('Applying a workbook requires PostgreSQL.')

    lock_import_tables()
    batch = ImportBatch.objects.filter(manifest_sha256=manifest_sha256).first()
    if batch is not None:
        return {**batch.audit_summary, 'status': 'already_applied'}

    populated = sorted(model._meta.model_name for model in BUSINESS_MODELS if model.objects.exists())
    if populated:
        raise WorkbookImportError('The target database already contains business records.', {
            'populated_tables': populated,
        })

    batch = ImportBatch.objects.create(
        source_name=data['source_name'],
        source_sha256=data['source_sha256'],
        fixture_version=data['fixture_version'],
        declared_summary_date=data['declared_summary_date'],
        latest_transaction_date=data['latest_transaction_date'],
        manifest_sha256=manifest_sha256,
        operator=operator,
    )
    write_workbook(data, batch)
    counts = {key: queryset.count() for key, queryset in RECORD_QUERIES.items()}
    differences = {
        key: {'expected': expected, 'inserted': counts[key]}
        for key, expected in expected_counts(data).items() if counts[key] != expected
    }
    reconciliation = financial_report(data, database_totals())
    snapshot = BankReconciliationSnapshot.objects.get(import_batch=batch)
    if any(getattr(snapshot, key) != value for key, value in data['reconciliation'].items() if key != 'source'):
        reconciliation['discrepancies']['bank_snapshot'] = 'Saved snapshot differs from the manifest.'

    if differences or reconciliation['discrepancies']:
        raise WorkbookImportError('Inserted records failed reconciliation. The import was rolled back.', {
            'inserted_counts': counts,
            'count_discrepancies': differences,
            'database_reconciliation': reconciliation,
        })

    report = {
        **preview,
        'status': 'applied',
        'batch_id': str(batch.pk),
        'operator': batch.operator,
        'imported_at': batch.imported_at.isoformat(),
        'inserted_counts': counts,
        'database_reconciliation': reconciliation,
    }
    batch.audit_summary = report
    batch.save(update_fields=['audit_summary'])
    return report
