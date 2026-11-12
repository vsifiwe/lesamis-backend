import hashlib
import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection

from core.workbook_import import WorkbookImportError, apply_workbook
from core.workbook_manifest import (
    ManifestSerializer,
    expected_counts,
    financial_report,
    manifest_totals,
    write_private_json,
)


class Command(BaseCommand):
    help = 'Preview a tracker manifest or apply it to a fresh PostgreSQL database.'

    def add_arguments(self, parser):
        parser.add_argument('manifest', type=Path)
        parser.add_argument('--report', required=True, type=Path)
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--expect-sha256')
        parser.add_argument('--operator')

    def handle(self, *args, **options):
        manifest = options['manifest']
        report_path = options['report']
        if manifest.resolve() == report_path.resolve():
            raise CommandError('The report path must differ from the manifest path.')

        operator = (options['operator'] or '').strip()
        if options['apply'] and (not options['expect_sha256'] or not 1 <= len(operator) <= 255):
            raise CommandError('Applying requires --expect-sha256 and a nonempty --operator (at most 255 characters).')

        try:
            payload = manifest.read_bytes()
            raw_data = json.loads(payload)
        except (OSError, ValueError) as exc:
            raise CommandError(f'Cannot read manifest: {exc}') from exc

        digest = hashlib.sha256(payload).hexdigest()
        report = {'manifest_sha256': digest}
        try:
            if options['apply'] and digest != options['expect_sha256']:
                raise WorkbookImportError('Manifest SHA-256 does not match the reviewed hash.')

            serializer = ManifestSerializer(data=raw_data)
            if not serializer.is_valid():
                raise WorkbookImportError('Manifest validation failed.', {'validation_errors': serializer.errors})

            data = serializer.validated_data
            latest = max((row['year'], row['month']) for row in data['contributions'])
            report.update(
                status='preview',
                source_name=data['source_name'],
                source_sha256=data['source_sha256'],
                fixture_version=data['fixture_version'],
                declared_summary_date=data['declared_summary_date'].isoformat(),
                latest_transaction_date=(
                    data['latest_transaction_date'].isoformat() if data['latest_transaction_date'] else None
                ),
                latest_contribution_month=date(*latest, 1).isoformat()[:7],
                expected_counts=expected_counts(data),
                reconciliation=financial_report(data, manifest_totals(data)),
            )
            if report['reconciliation']['discrepancies']:
                raise WorkbookImportError('Manifest totals do not reconcile with the workbook.')

            if options['apply']:
                report['database'] = connection.settings_dict['NAME']
                report = apply_workbook(data, digest, operator, report)
        except WorkbookImportError as exc:
            report.update(exc.report, status='rejected', error=str(exc))
            self.write_report(report_path, report)
            raise CommandError(str(exc)) from exc
        except DatabaseError as exc:
            message = 'The database rejected the import. Check the database connection and schema.'
            report.update(status='rejected', error=message)
            self.write_report(report_path, report)
            raise CommandError(message) from exc

        self.write_report(report_path, report)
        self.stdout.write(self.style.SUCCESS(f'{report["status"]}: {digest}\nAudit report: {report_path}'))

    def write_report(self, path, report):
        try:
            write_private_json(path, report)
        except OSError as exc:
            raise CommandError(f'Could not write the {report["status"]} report: {exc}') from exc
