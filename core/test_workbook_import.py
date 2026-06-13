import importlib.util
from decimal import Decimal
from pathlib import Path
from unittest import skipUnless

from django.db.models import Sum
from django.test import TestCase

from .models import (
    BankReconciliationSnapshot,
    HistoricalContributionEntry,
    ImportBatch,
    IncomeEntry,
    Investment,
    InvestmentProfitEntry,
    LedgerEntry,
    Loan,
    LoanRepayment,
    LoanRepaymentSchedule,
    MemberShareAccount,
    OtherCharge,
    SocialActivityRecord,
    SourceReference,
)


class WorkbookImportReconciliationTests(TestCase):
    def total(self, queryset, field='amount'):
        return queryset.aggregate(value=Sum(field))['value'] or Decimal('0.00')

    def test_authoritative_workbook_targets(self):
        self.assertEqual(self.total(HistoricalContributionEntry.objects.filter(fund_type='capital')), Decimal('66539682.00'))
        self.assertEqual(self.total(HistoricalContributionEntry.objects.filter(fund_type='social')), Decimal('7297900.00'))
        self.assertEqual(self.total(HistoricalContributionEntry.objects.filter(fund_type='social_plus')), Decimal('7820000.00'))
        self.assertEqual(self.total(SocialActivityRecord.objects.filter(fund_account__code='SOCIAL')), Decimal('3569780.00'))
        self.assertEqual(self.total(SocialActivityRecord.objects.filter(fund_account__code='SOCIAL_PLUS')), Decimal('9981000.00'))
        self.assertEqual(self.total(IncomeEntry.objects.filter(income_type='bank_interest')), Decimal('4599159.00'))
        self.assertEqual(self.total(IncomeEntry.objects.filter(income_type='joining_fee')), Decimal('1835400.00'))
        self.assertEqual(
            self.total(IncomeEntry.objects.filter(income_type__in=['contribution_penalty', 'loan_exit_penalty'])),
            Decimal('5656422.00'),
        )
        self.assertEqual(self.total(OtherCharge.objects.filter(charge_type='bank_charge')), Decimal('918486.00'))
        self.assertEqual(self.total(Loan.objects.all(), 'principal_amount'), Decimal('153581900.00'))
        self.assertEqual(
            self.total(Loan.objects.all(), 'total_repayment_amount') - self.total(Loan.objects.all(), 'principal_amount'),
            Decimal('10190057.00'),
        )
        self.assertEqual(self.total(LoanRepayment.objects.all(), 'amount_paid'), Decimal('126583039.00'))
        self.assertEqual(self.total(Loan.objects.filter(status='active'), 'principal_amount'), Decimal('35970000.00'))
        self.assertEqual(self.total(Loan.objects.filter(status='active'), 'source_outstanding_amount'), Decimal('27596772.00'))
        self.assertEqual(self.total(Investment.objects.all(), 'amount_invested'), Decimal('51805870.00'))
        self.assertEqual(self.total(InvestmentProfitEntry.objects.all()), Decimal('6351200.00'))
        self.assertEqual(self.total(MemberShareAccount.objects.all(), 'share_count'), 78)

    def test_cash_and_bank_variance_are_preserved(self):
        credits = self.total(LedgerEntry.objects.filter(direction='credit'))
        debits = self.total(LedgerEntry.objects.filter(direction='debit'))
        snapshot = BankReconciliationSnapshot.objects.get()

        self.assertEqual(credits - debits, Decimal('6825766.00'))
        self.assertEqual(snapshot.calculated_cash_balance, Decimal('6825766.00'))
        self.assertEqual(snapshot.stated_bank_balance, Decimal('16997755.00'))
        self.assertEqual(snapshot.variance, Decimal('10171989.00'))
        self.assertEqual(snapshot.expected_total_assets, Decimal('94253434.00'))

    def test_unknown_dates_are_not_fabricated(self):
        self.assertFalse(LedgerEntry.objects.filter(date_precision='unknown', entry_date__isnull=False).exists())
        self.assertFalse(LoanRepayment.objects.filter(date_precision='unknown', paid_date__isnull=False).exists())
        self.assertFalse(SocialActivityRecord.objects.filter(date_precision='unknown', activity_date__isnull=False).exists())
        self.assertFalse(OtherCharge.objects.filter(date_precision='unknown', charge_date__isnull=False).exists())
        self.assertFalse(IncomeEntry.objects.filter(date_precision='unknown', income_date__isnull=False).exists())
        self.assertFalse(Loan.objects.filter(is_opening_balance=True, issued_date__isnull=False).exists())

    def test_import_has_provenance_and_is_single_batch(self):
        batch = ImportBatch.objects.get()
        self.assertEqual(batch.fixture_version, 1)
        self.assertEqual(batch.declared_summary_date.isoformat(), '2026-03-05')
        self.assertGreater(SourceReference.objects.filter(import_batch=batch).count(), 5700)
        self.assertEqual(HistoricalContributionEntry.objects.filter(import_batch=batch).count(), 5694)

    def test_current_share_and_member_corrections(self):
        expected = {'Eric': 6, 'Dalyda': 2, 'Emmanuel': 1, 'Edmond': 2, 'Christian': 1, 'Obadiah': 1}
        for name, shares in expected.items():
            account = MemberShareAccount.objects.get(member__first_name=name)
            self.assertEqual(account.share_count, shares)

    def test_active_loan_snapshot_corrections(self):
        self.assertEqual(Loan.objects.filter(status='active').count(), 20)
        self.assertTrue(Loan.objects.filter(status='active', member__first_name='Belyse').exists())
        self.assertTrue(Loan.objects.filter(status='active', member__first_name='Seraphina').exists())
        self.assertFalse(Loan.objects.filter(status='active', member__first_name='Sandrine').exists())
        self.assertFalse(Loan.objects.filter(status='active', member__first_name='Epimaque').exists())
        self.assertEqual(
            Loan.objects.get(status='active', member__first_name='Vanessa').principal_amount,
            Decimal('8500000.00'),
        )

    def test_active_loans_have_derived_repayment_schedules(self):
        active_loans = Loan.objects.filter(status='active')
        self.assertEqual(
            LoanRepaymentSchedule.objects.count(),
            sum(loan.duration_months_snapshot for loan in active_loans),
        )
        for loan in active_loans:
            schedule = loan.repayment_schedule.order_by('installment_number')
            self.assertEqual(schedule.count(), loan.duration_months_snapshot)
            self.assertEqual(self.total(schedule, 'amount_due'), loan.total_repayment_amount)


@skipUnless(importlib.util.find_spec('openpyxl'), 'openpyxl is required for workbook extraction tests')
class WorkbookExtractorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from .management.commands.extract_workbook_fixture import WorkbookExtractor

        workbook = Path(__file__).resolve().parents[2] / 'Situation les Amis Sept 2023 Version (1).xlsx'
        cls.data = WorkbookExtractor(workbook).extract()

    def test_contribution_mapping_handles_column_layout_and_formulas(self):
        didier_june = [
            row for row in self.data['contributions']
            if row['member_number'] == 'MBR-0001' and row['year'] == 2026 and row['month'] == 6
        ]
        self.assertEqual({row['fund']: row['amount'] for row in didier_june}, {
            'capital': '100000.00', 'social': '2000.00', 'social_plus': '3000.00',
        })
        self.assertTrue(any(row['source']['formula'] for row in self.data['contributions']))

    def test_aliases_dates_and_blank_cells_are_normalized(self):
        members = {row['member_number']: row for row in self.data['members']}
        self.assertEqual(members['MBR-0046']['first_name'], 'Christian')
        self.assertIn('Chrisitan', members['MBR-0046']['aliases'])
        self.assertEqual(members['MBR-0022']['first_name'], 'Obadiah')
        self.assertEqual(self.data['latest_transaction_date'], '2026-06-09')
        self.assertFalse(any(row['amount'] == '0.00' for row in self.data['contributions']))
