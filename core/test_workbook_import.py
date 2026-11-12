import hashlib
import importlib.util
import json
from copy import deepcopy
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipUnless
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase

from .models import (
    BankReconciliationSnapshot,
    HistoricalContributionEntry,
    ImportBatch,
    InvestmentProfitEntry,
    LedgerEntry,
    Member,
    SourceReference,
)
from .serializers import CreateInvestmentProfitEntrySerializer
from .tasks import first_live_contribution_month
from .workbook_manifest import TOTAL_FIELDS
from .workbook_writer import write_workbook


def example_manifest():
    source = {'sheet': 'Tracker', 'cell': 'A1', 'formula': '', 'value': '100', 'notes': ''}
    totals = dict.fromkeys(TOTAL_FIELDS, '0.00')
    totals.update(
        contribution_capital='100.00', investments='50.00', investment_profits='20.00',
        calculated_cash_balance='70.00', expected_total_assets='120.00', shares='1.00',
    )
    return {
        'fixture_version': 2, 'source_name': 'Tracker.xlsx', 'source_sha256': 'f' * 64,
        'declared_summary_date': '2026-03-05', 'latest_transaction_date': None,
        'members': [{
            'member_number': 'MBR-0001', 'source_name': 'Example', 'first_name': 'Example',
            'last_name': '', 'aliases': [], 'join_date': '2026-11-01', 'share_count': 1, 'source': source,
        }],
        'contributions': [{
            'member_number': 'MBR-0001', 'year': 2026, 'month': 11, 'fund': 'capital',
            'amount': '100.00', 'source': source,
        }],
        'loans': {'active': [], 'historical': []},
        'social_expenses': [], 'income': [], 'bank_charges': [],
        'investments': [{
            'name': 'Example bond', 'type': 'bond', 'date': '2026-01-01', 'rate': '7.00',
            'vesting_months': 24, 'amount': '50.00', 'source': source,
            'profits': [{'date': None, 'amount': '20.00', 'source': source}],
        }],
        'reconciliation': {
            'as_of_date': None, 'calculated_cash_balance': '70.00', 'stated_bank_balance': '60.00',
            'variance': '-10.00', 'expected_total_assets': '120.00', 'source': source,
        },
        'targets': totals,
    }


class WorkbookCommandFiles:
    def setUp(self):
        super().setUp()
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.manifest_path = Path(directory.name) / 'manifest.json'
        self.report_path = Path(directory.name) / 'report.json'
        self.manifest = example_manifest()
        self.write_manifest()

    def write_manifest(self):
        payload = json.dumps(self.manifest).encode()
        self.manifest_path.write_bytes(payload)
        self.digest = hashlib.sha256(payload).hexdigest()

    def run_import(self, *flags):
        call_command(
            'import_workbook', str(self.manifest_path), '--report', str(self.report_path),
            *flags, stdout=StringIO(),
        )
        return json.loads(self.report_path.read_text())


class WorkbookPreviewTests(WorkbookCommandFiles, SimpleTestCase):
    def test_preview_reconciles_without_a_database(self):
        report = self.run_import()
        self.assertEqual(report['status'], 'preview')
        self.assertEqual(report['manifest_sha256'], self.digest)
        self.assertEqual(report['latest_contribution_month'], '2026-11')
        self.assertEqual(report['expected_counts']['members'], 1)
        self.assertEqual(report['reconciliation']['calculated_totals']['calculated_cash_balance'], '70.00')
        self.assertEqual(report['reconciliation']['reported_bank_variance'], '-10.00')
        self.assertEqual(report['reconciliation']['discrepancies'], {})
        self.assertEqual(self.report_path.stat().st_mode & 0o777, 0o600)

    def test_invalid_records_and_mismatched_totals_report_errors(self):
        original = deepcopy(self.manifest)
        self.manifest['contributions'].append(self.manifest['contributions'][0])
        self.write_manifest()
        with self.assertRaisesMessage(CommandError, 'Manifest validation failed'):
            self.run_import()
        self.assertIn('contributions', json.loads(self.report_path.read_text())['validation_errors'])

        self.manifest = original
        self.manifest['targets']['contribution_capital'] = '99.00'
        self.write_manifest()
        with self.assertRaisesMessage(CommandError, 'Manifest totals do not reconcile'):
            self.run_import()
        reconciliation = json.loads(self.report_path.read_text())['reconciliation']
        self.assertEqual(reconciliation['discrepancies']['contribution_capital'], {
            'expected': '99.00', 'calculated': '100.00',
        })

    def test_joining_fees_are_included_in_cash_and_assets(self):
        self.manifest['income'].append({
            'type': 'joining_fee',
            'amount': '10.00',
            'source': self.manifest['contributions'][0]['source'],
        })
        self.manifest['targets'].update(
            joining_fees='10.00', calculated_cash_balance='80.00', expected_total_assets='130.00',
        )
        self.manifest['reconciliation'].update(
            calculated_cash_balance='80.00', expected_total_assets='130.00', variance='-20.00',
        )
        self.write_manifest()

        report = self.run_import()
        self.assertEqual(report['reconciliation']['calculated_totals']['joining_fees'], '10.00')
        self.assertEqual(report['reconciliation']['discrepancies'], {})

    def test_wrong_reviewed_hash_is_rejected_before_connecting(self):
        with self.assertRaisesMessage(CommandError, 'does not match'):
            self.run_import('--apply', '--expect-sha256', '0' * 64, '--operator', 'Test operator')
        self.assertEqual(json.loads(self.report_path.read_text())['status'], 'rejected')

    def test_manually_recorded_profit_requires_a_date(self):
        serializer = CreateInvestmentProfitEntrySerializer(data={'profit_date': None, 'amount': '20.00'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('profit_date', serializer.errors)


class CleanWorkbookSchemaTests(TestCase):
    def test_migrations_do_not_seed_workbook_data(self):
        self.assertFalse(ImportBatch.objects.exists())
        self.assertFalse(Member.objects.exists())
        self.assertFalse(LedgerEntry.objects.exists())


@skipUnless(connection.vendor == 'postgresql', 'Workbook apply requires PostgreSQL')
class WorkbookApplyTests(WorkbookCommandFiles, TestCase):
    def apply(self):
        return self.run_import('--apply', '--expect-sha256', self.digest, '--operator', 'Test operator')

    def test_apply_persists_audit_and_repeat_is_idempotent(self):
        report = self.apply()
        batch = ImportBatch.objects.get()
        self.assertEqual(report, batch.audit_summary)
        self.assertEqual(batch.manifest_sha256, self.digest)
        self.assertEqual(batch.operator, 'Test operator')
        self.assertEqual(report['inserted_counts'], report['expected_counts'])
        self.assertEqual(report['database_reconciliation']['discrepancies'], {})
        self.assertEqual(Member.objects.count(), 1)
        self.assertEqual(SourceReference.objects.filter(import_batch=batch).count(), 5)

        self.assertEqual(HistoricalContributionEntry.objects.get().amount, Decimal('100.00'))
        self.assertIsNone(InvestmentProfitEntry.objects.get().profit_date)
        ledger = LedgerEntry.objects.get(entry_type='investment_profit')
        self.assertIsNone(ledger.entry_date)
        self.assertEqual(ledger.date_precision, 'unknown')
        snapshot = BankReconciliationSnapshot.objects.get()
        self.assertIsNone(snapshot.as_of_date)
        self.assertEqual(snapshot.variance, Decimal('-10.00'))
        self.assertEqual(first_live_contribution_month(2026, 11), (2026, 12))
        self.assertEqual(first_live_contribution_month(2027, 1), (2027, 1))

        repeat = self.apply()
        self.assertEqual(repeat, {**report, 'status': 'already_applied'})
        self.assertEqual(ImportBatch.objects.count(), 1)
        self.assertEqual(LedgerEntry.objects.count(), 3)

    def test_apply_refuses_a_populated_target(self):
        Member.objects.create(first_name='Existing', join_date=date(2026, 1, 1))
        with self.assertRaisesMessage(CommandError, 'already contains business records'):
            self.apply()
        self.assertEqual(Member.objects.count(), 1)
        self.assertFalse(ImportBatch.objects.exists())

    def test_failed_reconciliation_rolls_back_entities_and_audit(self):
        def write_with_missing_ledger(data, batch):
            write_workbook(data, batch)
            LedgerEntry.objects.filter(entry_type='investment_profit').delete()

        with patch('core.workbook_import.write_workbook', side_effect=write_with_missing_ledger):
            with self.assertRaisesMessage(CommandError, 'import was rolled back'):
                self.apply()
        report = json.loads(self.report_path.read_text())
        self.assertIn('ledger_entries', report['count_discrepancies'])
        self.assertIn('calculated_cash_balance', report['database_reconciliation']['discrepancies'])
        self.assertFalse(Member.objects.exists())
        self.assertFalse(ImportBatch.objects.exists())
        self.assertFalse(SourceReference.objects.exists())


WORKBOOK = Path(__file__).resolve().parents[2] / 'Situation les Amis Sept 2023 Version (1).xlsx'
WORKBOOK_SHA256 = '9334189e6925fa18da5f5042f793a8dee63e7a23d8684296524107da5aa0879a'


@skipUnless(
    importlib.util.find_spec('openpyxl') and WORKBOOK.is_file()
    and hashlib.sha256(WORKBOOK.read_bytes()).hexdigest() == WORKBOOK_SHA256,
    'The November 2026 tracker and openpyxl are required',
)
class WorkbookExtractorTests(SimpleTestCase):
    def test_latest_tracker_is_deterministic_and_reconciles(self):
        from .management.commands.extract_workbook_fixture import WorkbookExtractor
        from .workbook_manifest import ManifestSerializer, financial_report, manifest_totals

        raw = WorkbookExtractor(WORKBOOK).extract()
        self.assertEqual(raw, WorkbookExtractor(WORKBOOK).extract())
        self.assertEqual(raw['source_sha256'], WORKBOOK_SHA256)
        self.assertEqual(raw['declared_summary_date'], '2026-03-05')
        self.assertEqual(raw['latest_transaction_date'], '2026-11-02')
        self.assertEqual(len(raw['members']), 49)
        self.assertEqual(len(raw['contributions']), 6184)
        self.assertEqual(raw['targets']['investment_profits'], '9506550.00')

        serializer = ManifestSerializer(data=raw)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        data = serializer.validated_data
        report = financial_report(data, manifest_totals(data))
        self.assertEqual(report['discrepancies'], {})
        self.assertEqual(report['calculated_totals']['calculated_cash_balance'], '26184193.00')
        self.assertEqual(report['reported_bank_variance'], '-9186438.00')

    def test_missing_formula_cache_fails_with_cell_reference(self):
        from .management.commands.extract_workbook_fixture import WorkbookExtractor

        extractor = WorkbookExtractor(WORKBOOK)
        extractor.values["Vue d'Ensemble"]['C28'].value = None
        with self.assertRaisesMessage(CommandError, "Vue d'Ensemble!C28"):
            extractor.extract()
