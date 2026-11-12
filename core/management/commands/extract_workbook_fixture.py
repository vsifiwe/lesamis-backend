import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from core.workbook_manifest import FIXTURE_VERSION, write_private_json


MEMBER_ALIASES = {
    'Chrisitan': 'Christian',
    'Obadias': 'Obadiah',
}
FRENCH_MONTHS = {
    'janvier': 1, 'fevrier': 2, 'février': 2, 'werurwe': 3, 'mars': 3,
    'avril': 4, 'mata': 4, 'mai': 5, 'juin': 6, 'kamena': 6,
    'juillet': 7, 'nyakanga': 7, 'aout': 8, 'août': 8, 'septembre': 9,
    'nzeri': 9, 'octobre': 10, 'novembre': 11, 'decembre': 12,
    'décembre': 12, 'ukuboza': 12, 'mutarama': 1,
}


def decimal_string(value):
    return str(Decimal(str(value or 0)).quantize(Decimal('0.01')))


def parse_date(value):
    if value in (None, ''):
        return None
    if isinstance(value, (date, datetime)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    text = str(value).strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    match = re.match(r'(\d{1,2})\s+([^\s]+)\s+(\d{4})', text.lower())
    if match and match.group(2) in FRENCH_MONTHS:
        return date(int(match.group(3)), FRENCH_MONTHS[match.group(2)], int(match.group(1))).isoformat()
    raise CommandError(f'Cannot parse workbook date: {value!r}')


class WorkbookExtractor:
    def __init__(self, source):
        self.source = Path(source)
        payload = self.source.read_bytes()
        self.sha256 = hashlib.sha256(payload).hexdigest()
        self.values = load_workbook(BytesIO(payload), data_only=True)
        self.formulas = load_workbook(BytesIO(payload), data_only=False)

    def source_ref(self, sheet, cell, notes=''):
        value_cell = self.values[sheet][cell]
        formula_cell = self.formulas[sheet][cell]
        if isinstance(value_cell, tuple):
            values = {item.coordinate: item.value for row in value_cell for item in row}
            formulas = {
                item.coordinate: item.value for row in formula_cell for item in row if item.data_type == 'f'
            }
            value = json.dumps(values, default=str, ensure_ascii=False)
            formula = json.dumps(formulas, ensure_ascii=False) if formulas else ''
        else:
            value = value_cell.value
            formula = formula_cell.value if formula_cell.data_type == 'f' else ''
        return {
            'sheet': sheet,
            'cell': cell,
            'formula': formula,
            'value': '' if value is None else str(value),
            'notes': notes,
        }

    def number(self, cell, *, optional=False):
        formula = self.formulas[cell.parent.title][cell.coordinate]
        value = cell.value
        if value is None and optional and formula.data_type != 'f':
            return Decimal('0')
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise CommandError(f'Expected a saved number at {cell.parent.title}!{cell.coordinate}.')
        return Decimal(str(value))

    def amount(self, cell, *, optional=False):
        return decimal_string(self.number(cell, optional=optional))

    def whole_number(self, cell, *, optional=False):
        value = self.number(cell, optional=optional)
        if value < 0 or value != int(value):
            raise CommandError(f'Expected a whole number at {cell.parent.title}!{cell.coordinate}.')
        return int(value)

    def extract(self):
        summary = self.values["Vue d'Ensemble"]
        declared = parse_date(str(summary['B3'].value).removeprefix('Ku wa '))
        members, contributions = self.extract_contributions()
        loans = self.extract_loans()
        social_expenses = self.extract_social_expenses()
        dated_records = loans['active'] + social_expenses
        target_cells = {
            'contribution_capital': 'C15',
            'contribution_social': 'C6',
            'contribution_social_plus': 'C9',
            'social_expenses': 'C7',
            'social_plus_expenses': 'C10',
            'bank_interest': 'C16',
            'joining_fees': 'C17',
            'collected_penalties': 'C18',
            'bank_charges': 'C19',
            'loan_principal': 'C22',
            'loan_interest': 'C23',
            'loan_repayments': 'C24',
            'calculated_cash_balance': 'C39',
            'expected_total_assets': 'C40',
        }
        targets = {key: self.amount(summary[cell]) for key, cell in target_cells.items()}
        targets.update(
            active_loan_principal=self.amount(self.values['Details de credits']['G52']),
            active_loan_outstanding=self.amount(self.values['Details de credits']['L52']),
            investments=decimal_string(sum(self.number(summary[cell]) for cell in ('C27', 'C29', 'C31', 'C33'))),
            investment_profits=decimal_string(sum(self.number(summary[cell]) for cell in ('C28', 'C30', 'C32', 'C34'))),
            shares=self.whole_number(self.values['Details']['V53']),
        )
        return {
            'fixture_version': FIXTURE_VERSION,
            'source_name': self.source.name,
            'source_sha256': self.sha256,
            'declared_summary_date': declared,
            'latest_transaction_date': max((row['date'] for row in dated_records if row['date']), default=None),
            'members': members,
            'contributions': contributions,
            'loans': loans,
            'social_expenses': social_expenses,
            'income': self.extract_income(),
            'bank_charges': [{
                'amount': targets['bank_charges'],
                'description': summary['B19'].value,
                'date': None,
                'date_precision': 'unknown',
                'source': self.source_ref(summary.title, 'C19'),
            }],
            'investments': self.extract_investments(),
            'reconciliation': {
                'as_of_date': None,
                'calculated_cash_balance': targets['calculated_cash_balance'],
                'stated_bank_balance': self.amount(summary['E39']),
                'variance': self.amount(summary['G39']),
                'expected_total_assets': targets['expected_total_assets'],
                'source': self.source_ref(summary.title, 'C39:G40'),
            },
            'targets': targets,
        }

    def extract_contributions(self):
        sheet = self.values['Contribution Individuel Mensuel']
        periods = []
        year = 2020
        month = 8
        while (year, month) <= (2021, 4):
            periods.append((year, month, ('capital', 'social')))
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        year, month = 2021, 5
        while (year, month) <= (2026, 12):
            periods.append((year, month, ('capital', 'social', 'social_plus')))
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)

        details = self.values['Details']
        members = []
        contributions = []
        for row in range(3, 52):
            source_name = sheet.cell(row, 2).value
            if not isinstance(source_name, str) or not source_name.strip():
                raise CommandError(f'Expected a member name at {sheet.title}!B{row}.')
            detail_name = details.cell(row + 1, 3).value
            canonical = MEMBER_ALIASES.get(source_name, source_name)
            if MEMBER_ALIASES.get(detail_name, detail_name) != canonical:
                raise CommandError(f'Member and share rows disagree at {sheet.title}!B{row}.')
            first_period = None
            member_number = f'MBR-{row - 2:04d}'
            row_contributions = []
            scan_column = 3
            for period_year, period_month, funds in periods:
                for offset, fund in enumerate(funds):
                    cell = sheet.cell(row, scan_column + offset)
                    amount = self.number(cell, optional=True)
                    if amount:
                        first_period = first_period or date(period_year, period_month, 1)
                        row_contributions.append({
                            'member_number': member_number,
                            'year': period_year,
                            'month': period_month,
                            'fund': fund,
                            'amount': decimal_string(amount),
                            'source': self.source_ref(sheet.title, cell.coordinate),
                        })
                scan_column += len(funds)
            if first_period is None:
                raise CommandError(f'No contribution month available to derive a join date at {sheet.title}!B{row}.')
            contributions.extend(row_contributions)
            members.append({
                'member_number': member_number,
                'source_name': source_name,
                'first_name': canonical,
                'last_name': '',
                'aliases': sorted(set([source_name]) - {canonical}),
                'join_date': first_period.isoformat(),
                'share_count': self.whole_number(details.cell(row + 1, 22), optional=True),
                'source': self.source_ref('Details', f'V{row + 1}', f'Join date derived from {sheet.title}!{row_contributions[0]["source"]["cell"]}.'),
            })
        headers = {'capital': 'Capital', 'social': 'Social', 'social_plus': 'Kwidagadura'}
        column = 3
        for year, month, funds in periods:
            heading = sheet.cell(1, column)
            label = str(heading.value).lower().replace('/', ' ').split()
            if not label or FRENCH_MONTHS.get(label[0]) != month or (len(label) > 1 and label[-1] != str(year)):
                raise CommandError(f'Unexpected month heading at {sheet.title}!{heading.coordinate}.')
            for fund in funds:
                heading = sheet.cell(2, column)
                if str(heading.value).strip().lower() != headers[fund].lower():
                    raise CommandError(f'Unexpected fund heading at {sheet.title}!{heading.coordinate}.')
                column += 1
        return members, contributions

    def extract_loans(self):
        sheet = self.values['Details de credits']
        active = []
        historical = []
        for row in range(3, 52):
            source_name = sheet.cell(row, 3).value
            if not source_name:
                continue
            canonical = MEMBER_ALIASES.get(source_name, source_name)
            total_principal = self.number(sheet.cell(row, 4), optional=True)
            total_interest = self.number(sheet.cell(row, 5), optional=True)
            total_paid = self.number(sheet.cell(row, 6), optional=True)
            active_principal = self.number(sheet.cell(row, 7), optional=True)
            duration = self.whole_number(sheet.cell(row, 8), optional=True)
            rate_fraction = self.number(sheet.cell(row, 9), optional=True)
            active_interest = active_principal * rate_fraction
            active_paid = self.number(sheet.cell(row, 11), optional=True)
            active_outstanding = self.number(sheet.cell(row, 12), optional=True)
            if active_principal:
                active.append({
                    'member_name': canonical,
                    'principal': decimal_string(active_principal),
                    'interest': decimal_string(active_interest),
                    'paid': decimal_string(active_paid),
                    'outstanding': decimal_string(active_outstanding),
                    'duration_months': duration,
                    'rate_percent': decimal_string(rate_fraction * 100),
                    'date': parse_date(sheet.cell(row, 13).value),
                    'maturity_date': parse_date(sheet.cell(row, 14).value),
                    'source': self.source_ref('Details de credits', f'G{row}:N{row}'),
                })
            opening_principal = total_principal - active_principal
            opening_interest = total_interest - active_interest
            opening_paid = total_paid - active_paid
            if opening_principal or opening_interest or opening_paid:
                historical.append({
                    'member_name': canonical,
                    'principal': decimal_string(opening_principal),
                    'interest': decimal_string(opening_interest),
                    'paid': decimal_string(opening_paid),
                    'source': self.source_ref('Details de credits', f'D{row}:L{row}', 'Aggregate totals less the active loan amounts.'),
                })
        return {'active': active, 'historical': historical}

    def extract_social_expenses(self):
        rows = []
        details_sources = [
            ('SOCIAL', 'E57', 'Ayakoreshejwe muri social'), ('SOCIAL', 'G57', 'Guhemba Sandrine'),
            ('SOCIAL', 'H57', 'Muhazi'), ('SOCIAL', 'I57', 'Guhemba Diane & Thadee'),
            ('SOCIAL', 'G59', 'Gufata mu mugongo Clement'), ('SOCIAL', 'I59', 'Guhemba Tuyizere & Edissa'),
            ('SOCIAL', 'K57', 'Guhemba Venuste'), ('SOCIAL', 'K59', 'Gutwerera Semanzi'),
            ('SOCIAL', 'K61', 'Guhemba Yvonne'), ('SOCIAL', 'U57', 'Guhemba Arnauld & Joelle'),
            ('SOCIAL', 'U63', 'Intwererano Vital'), ('SOCIAL', 'U65', 'Guhemba Phoebe & Semanzi'),
            ('SOCIAL', 'S57', 'Gutwerera Vanessa Mupenzi'), ('SOCIAL', 'L57', 'Guhemba Tuyizere & Edissa Mars 2024'),
            ('SOCIAL', 'L59', 'Cadeau Tuyizere & Edissa Mars 2024'),
            ('SOCIAL_PLUS', 'U59', 'Inama rusange du 24 Juin'), ('SOCIAL_PLUS', 'U61', 'Inama rusange du 24 Juin'),
            ('SOCIAL_PLUS', 'U67', 'Inama rusange du 22 Decembre'), ('SOCIAL_PLUS', 'U68', 'Inama rusange du 22 Decembre supplement'),
            ('SOCIAL_PLUS', 'U70', 'Avance sortie 27 Janvier 2024'), ('SOCIAL_PLUS', 'U72', 'Inama 11 Gicurasi 2024'),
        ]
        for fund, cell, name in details_sources:
            amount = self.amount(self.values['Details'][cell])
            rows.append({'fund': fund, 'date': None, 'date_precision': 'unknown', 'category': 'support' if fund == 'SOCIAL' else 'event',
                         'name': name, 'amount': amount, 'source': self.source_ref('Details', cell)})
        rows.append({'fund': 'SOCIAL_PLUS', 'date': None, 'date_precision': 'unknown', 'category': 'event',
                     'name': 'Kwidagadura hardcoded expenses', 'amount': decimal_string(1948000),
                     'source': self.source_ref("Vue d'Ensemble", 'C10', 'Hardcoded formula constants total 1,948,000.')})
        social = self.values['Social Loisirs']
        for row in range(3, 23):
            for fund, date_col, name_col, amount_col in [('SOCIAL', 1, 2, 3), ('SOCIAL_PLUS', 5, 6, 7)]:
                amount = self.number(social.cell(row, amount_col), optional=True)
                if amount:
                    rows.append({
                        'fund': fund, 'date': parse_date(social.cell(row, date_col).value), 'date_precision': 'exact',
                        'category': 'support' if fund == 'SOCIAL' else 'event',
                        'name': social.cell(row, name_col).value, 'amount': decimal_string(amount),
                        'source': self.source_ref('Social Loisirs', f'{get_column_letter(amount_col)}{row}'),
                    })
        return rows

    def extract_income(self):
        details = self.values['Details']
        summary = self.values["Vue d'Ensemble"]
        return [
            {'type': 'bank_interest', 'amount': self.amount(summary['C16']), 'source': self.source_ref("Vue d'Ensemble", 'C16')},
            {'type': 'joining_fee', 'amount': self.amount(summary['C17']), 'source': self.source_ref("Vue d'Ensemble", 'C17')},
            {'type': 'contribution_penalty', 'amount': self.amount(details['H53']), 'source': self.source_ref('Details', 'H53')},
            {'type': 'loan_exit_penalty', 'amount': self.amount(details['J53']), 'source': self.source_ref('Details', 'J53')},
        ]

    def extract_investments(self):
        summary = self.values["Vue d'Ensemble"]
        bonds = [
            (27, 'BRD Sustainability Bond August 2024', '2024-08-01', '12.90', 84),
            (29, 'Treasury Bond April 2025', '2025-04-01', '12.15', 120),
            (31, 'Treasury Bond May 2025', '2025-05-01', '13.27', 240),
            (33, 'Treasury Bond Jan 2026', '2026-01-01', '12.15', 120),
        ]
        investments = []
        for row, name, month, rate, term in bonds:
            amount_cell = f'C{row}'
            profit_cell = f'C{row + 1}'
            profit = self.amount(summary[profit_cell])
            investments.append({
                'name': name, 'type': 'bond', 'date': month, 'rate': rate, 'vesting_months': term,
                'amount': self.amount(summary[amount_cell]),
                'source': self.source_ref(summary.title, f'B{row}:C{row}', 'Purchase month from workbook label.'),
                'profits': [{
                    'date': None, 'amount': profit, 'source': self.source_ref(summary.title, profit_cell),
                }] if Decimal(profit) else [],
            })
        return investments


class Command(BaseCommand):
    help = 'Extract the tracker into a deterministic normalized JSON manifest.'

    def add_arguments(self, parser):
        parser.add_argument('workbook')
        parser.add_argument('--output', required=True, type=Path)

    def handle(self, *args, **options):
        output = options['output']
        source = Path(options['workbook'])
        legacy_fixture = Path(__file__).resolve().parents[2] / 'fixtures' / 'workbook_import_v1.json'
        if output.resolve() in (source.resolve(), legacy_fixture):
            raise CommandError('Choose an output path separate from the workbook and archived fixture.')
        try:
            data = WorkbookExtractor(source).extract()
            write_private_json(output, data)
        except (OSError, KeyError, ValueError) as exc:
            raise CommandError(f'Cannot extract workbook: {exc}') from exc
        self.stdout.write(self.style.SUCCESS(f'Wrote workbook manifest to {output}'))
