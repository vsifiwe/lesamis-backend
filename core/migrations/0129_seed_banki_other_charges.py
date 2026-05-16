import datetime
from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

# ------------------------------------------------------------------
# Banki seed data from:
# Situation les Amis Sept 2023 Version.xlsx / Vue d'Ensemble
# ------------------------------------------------------------------
# Included:
#   C16 Inyungu za konti muri banki = 4,599,159
#   C17 Inyungu zo kwinjira         = 1,835,400
#   C19 Bank/service charges        =   916,936
# Excluded by request:
#   C18 Ibihano                     = 5,572,513
# ------------------------------------------------------------------

SOURCE_WORKBOOK = 'Situation les Amis Sept 2023 Version.xlsx'
SUMMARY_DATE = datetime.date(2026, 3, 5)

# (cell, charge_type, direction, amount, name, description)
BANKI_ROWS = [
    (
        'C16',
        'adjustment',
        'credit',
        '4599159.00',
        'Inyungu za konti muri banki',
        'Vue d\'Ensemble!C16: Inyungu za konti muri banki.',
    ),
    (
        'C17',
        'adjustment',
        'credit',
        '1835400.00',
        'Inyungu zo kwinjira',
        'Vue d\'Ensemble!C17: Inyungu zo kwinjira.',
    ),
    (
        'C19',
        'bank_charge',
        'debit',
        '916936.00',
        'Ayishyuwe kuri serivisi za banki + izindi services',
        'Vue d\'Ensemble!C19: Ayishyuwe kuri serivisi za banki + izindi services.',
    ),
]

EXPECTED_TOTALS = {
    'credit': Decimal('6434559.00'),
    'debit': Decimal('916936.00'),
}


def _d(value):
    return Decimal(value)


def _validate_totals():
    actual = {
        'credit': sum(_d(row[3]) for row in BANKI_ROWS if row[2] == 'credit'),
        'debit': sum(_d(row[3]) for row in BANKI_ROWS if row[2] == 'debit'),
    }
    if actual != EXPECTED_TOTALS:
        raise ValueError(f'Banki seed totals do not match workbook totals: {actual}')


def seed(apps, schema_editor):
    OtherCharge = apps.get_model('core', 'OtherCharge')
    LedgerEntry = apps.get_model('core', 'LedgerEntry')
    FundAccount = apps.get_model('core', 'FundAccount')

    _validate_totals()

    capital = FundAccount.objects.get(code='CAPITAL')
    ledger_entries = []

    for cell, charge_type, direction, amount, name, description in BANKI_ROWS:
        source = f'{description} Source: {SOURCE_WORKBOOK}.'
        charge = OtherCharge.objects.create(
            charge_type=charge_type,
            amount=_d(amount),
            direction=direction,
            fund_account=capital,
            charge_date=SUMMARY_DATE,
            description=source,
            recorded_by=None,
        )
        ledger_entries.append(LedgerEntry(
            fund_account=capital,
            member=None,
            entry_date=SUMMARY_DATE,
            entry_type='other_charge',
            amount=_d(amount),
            direction=direction,
            reference_id=charge.id,
            reference_type='other_charge',
            notes=f'Seeded from {SOURCE_WORKBOOK}; Vue d\'Ensemble!{cell}: {name}.',
            recorded_by=None,
        ))

    LedgerEntry.objects.bulk_create(ledger_entries)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0128_seed_investments_and_profits'),
    ]

    operations = [
        migrations.AlterField(
            model_name='othercharge',
            name='recorded_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='recorded_charges',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(seed, reverse_code=migrations.RunPython.noop),
    ]
