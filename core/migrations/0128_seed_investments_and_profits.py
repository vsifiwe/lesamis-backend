import datetime
from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

# ------------------------------------------------------------------
# Investment seed data from:
# Situation les Amis Sept 2023 Version.xlsx / Vue d'Ensemble
# ------------------------------------------------------------------
# Purchases: C27 + C29 + C31 + C33 = 51,805,870
# Profits  : C28 + C30 + C32       =  6,351,200
# C34 has no value in the source workbook.
# ------------------------------------------------------------------

SOURCE_WORKBOOK = 'Situation les Amis Sept 2023 Version.xlsx'

# (key, name, investment_type, investment_date, amount, expected_rate, vesting_months, description)
INVESTMENTS = [
    (
        'brd_sustainability_aug_2024',
        'BRD Sustainability Bond August 2024',
        'bond',
        datetime.date(2024, 8, 1),
        '20000000.00',
        '12.90',
        84,
        'Vue d\'Ensemble!C27: Ayashowe (BRD Sustainability Bond August 2024) [imyaka 7] [12,9%].',
    ),
    (
        'treasury_bond_apr_2025',
        'Treasury Bond April 2025',
        'bond',
        datetime.date(2025, 4, 1),
        '10000000.00',
        '12.15',
        120,
        'Vue d\'Ensemble!C29: Ayashowe (Treasury Bond April 2025) [Imyaka 10] [12,150%].',
    ),
    (
        'treasury_bond_may_2025',
        'Treasury Bond May 2025',
        'bond',
        datetime.date(2025, 5, 1),
        '11805870.00',
        '13.27',
        240,
        'Vue d\'Ensemble!C31: Ayashowe [Treasury Bond May 2025] [Imyaka 20] [13,27% with WHT 5%].',
    ),
    (
        'treasury_bond_jan_2026',
        'Treasury Bond Jan 2026',
        'bond',
        datetime.date(2026, 1, 1),
        '10000000.00',
        '12.15',
        120,
        'Vue d\'Ensemble!C33: Ayashowe (Treasury Bond Jan 2026) [Imyaka 10] [12,150%].',
    ),
]

# (investment_key, profit_date, amount, description)
PROFIT_ENTRIES = [
    (
        'brd_sustainability_aug_2024',
        datetime.date(2025, 3, 31),
        '1225500.00',
        'Vue d\'Ensemble!C28 formula term for Werurwe 2025.',
    ),
    (
        'brd_sustainability_aug_2024',
        datetime.date(2025, 9, 30),
        '1225500.00',
        'Vue d\'Ensemble!C28 formula term for Nzeri 2025.',
    ),
    (
        'brd_sustainability_aug_2024',
        datetime.date(2026, 3, 31),
        '1225500.00',
        'Vue d\'Ensemble!C28 formula term for Werurwe 2026.',
    ),
    (
        'treasury_bond_apr_2025',
        datetime.date(2025, 10, 31),
        '607500.00',
        'Vue d\'Ensemble!C30 formula term for Ukwakira 2025.',
    ),
    (
        'treasury_bond_apr_2025',
        datetime.date(2026, 4, 30),
        '607500.00',
        'Vue d\'Ensemble!C30 formula term for Mata 2026.',
    ),
    (
        'treasury_bond_may_2025',
        datetime.date(2025, 6, 30),
        '729850.00',
        'Vue d\'Ensemble!C32 formula term for Kamena 2025.',
    ),
    (
        'treasury_bond_may_2025',
        datetime.date(2025, 12, 31),
        '729850.00',
        'Vue d\'Ensemble!C32 formula term for Ukuboza 2025.',
    ),
]

EXPECTED_TOTALS = {
    'invested': Decimal('51805870.00'),
    'profit': Decimal('6351200.00'),
}


def _d(value):
    return Decimal(value)


def _validate_totals():
    actual = {
        'invested': sum(_d(row[4]) for row in INVESTMENTS),
        'profit': sum(_d(row[2]) for row in PROFIT_ENTRIES),
    }
    if actual != EXPECTED_TOTALS:
        raise ValueError(f'Investment seed totals do not match workbook totals: {actual}')


def seed(apps, schema_editor):
    Investment = apps.get_model('core', 'Investment')
    InvestmentProfitEntry = apps.get_model('core', 'InvestmentProfitEntry')
    LedgerEntry = apps.get_model('core', 'LedgerEntry')
    FundAccount = apps.get_model('core', 'FundAccount')

    _validate_totals()

    capital = FundAccount.objects.get(code='CAPITAL')
    investments_by_key = {}
    ledger_entries = []

    for key, name, investment_type, investment_date, amount, expected_rate, vesting_months, description in INVESTMENTS:
        investment = Investment.objects.create(
            name=name,
            investment_type=investment_type,
            investment_date=investment_date,
            amount_invested=_d(amount),
            expected_interest_rate_percent=_d(expected_rate),
            vesting_period_months=vesting_months,
            status='active',
            description=f'{description} Source: {SOURCE_WORKBOOK}.',
            created_by=None,
        )
        investments_by_key[key] = investment
        ledger_entries.append(LedgerEntry(
            fund_account=capital,
            member=None,
            entry_date=investment_date,
            entry_type='investment_purchase',
            amount=_d(amount),
            direction='debit',
            reference_id=investment.id,
            reference_type='investment',
            notes=f'Seeded from {SOURCE_WORKBOOK}.',
            recorded_by=None,
        ))

    for investment_key, profit_date, amount, description in PROFIT_ENTRIES:
        profit_entry = InvestmentProfitEntry.objects.create(
            investment=investments_by_key[investment_key],
            profit_date=profit_date,
            amount=_d(amount),
            description=f'{description} Source: {SOURCE_WORKBOOK}.',
            recorded_by=None,
        )
        ledger_entries.append(LedgerEntry(
            fund_account=capital,
            member=None,
            entry_date=profit_date,
            entry_type='investment_profit',
            amount=_d(amount),
            direction='credit',
            reference_id=profit_entry.id,
            reference_type='investment_profit_entry',
            notes=f'Seeded from {SOURCE_WORKBOOK}.',
            recorded_by=None,
        ))

    LedgerEntry.objects.bulk_create(ledger_entries)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0127_seed_member_loans'),
    ]

    operations = [
        migrations.AlterField(
            model_name='investment',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='created_investments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='investmentprofitentry',
            name='recorded_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='recorded_profit_entries',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(seed, reverse_code=migrations.RunPython.noop),
    ]
