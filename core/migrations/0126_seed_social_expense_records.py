import datetime
from decimal import Decimal

from django.db import migrations

# ------------------------------------------------------------------
# Social expense records from:
# Situation les Amis Sept 2023 Version.xlsx / Vue d'Ensemble
# ------------------------------------------------------------------
# SOCIAL total      : Vue d'Ensemble!C7  =  3,169,780
# SOCIAL_PLUS total : Vue d'Ensemble!C10 =  9,956,100
# ------------------------------------------------------------------

SOURCE_WORKBOOK = 'Situation les Amis Sept 2023 Version.xlsx'
SUMMARY_DATE = datetime.date(2026, 3, 5)

# (fund_code, activity_date, category, name, description, amount)
SOCIAL_EXPENSES = [
    ('SOCIAL', SUMMARY_DATE, 'support', 'Ayakoreshejwe muri social', 'Details!E57 formula component: 156000+195780.', 351780),
    ('SOCIAL', SUMMARY_DATE, 'support', 'Guhemba Sandrine', 'Details!G57 referenced by Vue d\'Ensemble!C7.', 100000),
    ('SOCIAL', SUMMARY_DATE, 'support', 'Muhazi', 'Details!H57 referenced by Vue d\'Ensemble!C7.', 67000),
    ('SOCIAL', SUMMARY_DATE, 'support', 'Guhemba Diane & Thadee', 'Details!I57 referenced by Vue d\'Ensemble!C7.', 100000),
    ('SOCIAL', SUMMARY_DATE, 'support', 'Gufata mu mugongo Clement', 'Details!G59 referenced by Vue d\'Ensemble!C7.', 100000),
    ('SOCIAL', SUMMARY_DATE, 'support', 'Guhemba Tuyizere & Edissa', 'Details!I59 referenced by Vue d\'Ensemble!C7.', 150000),
    ('SOCIAL', SUMMARY_DATE, 'support', 'Guhemba Venuste', 'Details!K57 referenced by Vue d\'Ensemble!C7.', 150000),
    ('SOCIAL', SUMMARY_DATE, 'support', 'Gutwerera Semanzi', 'Details!K59 referenced by Vue d\'Ensemble!C7.', 100000),
    ('SOCIAL', SUMMARY_DATE, 'support', 'Guhemba Yvonne', 'Details!K61 referenced by Vue d\'Ensemble!C7.', 150000),
    ('SOCIAL', SUMMARY_DATE, 'support', 'Guhemba Arnauld & Joelle', 'Details!U57 referenced by Vue d\'Ensemble!C7.', 150000),
    ('SOCIAL', SUMMARY_DATE, 'support', 'Intwererano Vital', 'Details!U63 referenced by Vue d\'Ensemble!C7.', 50000),
    ('SOCIAL', SUMMARY_DATE, 'support', 'Guhemba Phoebe & Semanzi', 'Details!U65 referenced by Vue d\'Ensemble!C7.', 150000),
    ('SOCIAL', SUMMARY_DATE, 'support', 'Gutwerera Vanessa Mupenzi', 'Details!S57 referenced by Vue d\'Ensemble!C7.', 100000),
    ('SOCIAL', SUMMARY_DATE, 'support', 'Guhemba Tuyizere & Edissa Mars 2024', 'Details!L57 referenced by Vue d\'Ensemble!C7.', 300000),
    ('SOCIAL', SUMMARY_DATE, 'support', 'Cadeau Tuyizere & Edissa Mars 2024', 'Details!L59 referenced by Vue d\'Ensemble!C7.', 100000),
    ('SOCIAL', datetime.date(2024, 6, 6), 'support', 'Phoebe & Semanzi', 'Social Loisirs!C3 dated social support row.', 250000),
    ('SOCIAL', datetime.date(2024, 11, 2), 'support', 'Belyse & Florent', 'Social Loisirs!C4 formula component: 350000+1000.', 351000),
    ('SOCIAL', datetime.date(2024, 11, 8), 'support', 'Cadeau Guhemba B&F', 'Social Loisirs!C5 dated social support row.', 50000),
    ('SOCIAL', datetime.date(2025, 11, 20), 'support', 'Guhemba Vanessa & Didier', 'Social Loisirs!C6 dated social support row.', 400000),
]

SOCIAL_PLUS_EXPENSES = [
    ('SOCIAL_PLUS', SUMMARY_DATE, 'event', 'Kwidagadura hardcoded expenses', 'Vue d\'Ensemble!C10 hardcoded constants: 540000+400000+158000+50000+800000.', 1948000),
    ('SOCIAL_PLUS', SUMMARY_DATE, 'event', 'Inama rusange du 24 Juin', 'Details!U59 referenced by Vue d\'Ensemble!C10.', 250000),
    ('SOCIAL_PLUS', SUMMARY_DATE, 'event', 'Inama rusange du 24 Juin', 'Details!U61 referenced by Vue d\'Ensemble!C10.', 470000),
    ('SOCIAL_PLUS', SUMMARY_DATE, 'event', 'Inama rusange du 22 Decembre', 'Details!U67 referenced by Vue d\'Ensemble!C10.', 150000),
    ('SOCIAL_PLUS', SUMMARY_DATE, 'event', 'Inama rusange du 22 Decembre supplement', 'Details!U68 formula component: 266500.', 266500),
    ('SOCIAL_PLUS', SUMMARY_DATE, 'event', 'Avance sortie 27 Janvier 2024', 'Details!U70 formula component: 100000+50250+100000+800000.', 1050250),
    ('SOCIAL_PLUS', SUMMARY_DATE, 'event', 'Inama 11 Gicurasi 2024', 'Details!U72 formula component: 586000+10000.', 596000),
    ('SOCIAL_PLUS', datetime.date(2025, 1, 23), 'event', 'Avance sortie du 25', 'Social Loisirs!G6 dated Kwidagadura row.', 200000),
    ('SOCIAL_PLUS', datetime.date(2025, 1, 25), 'event', 'Sortie', 'Social Loisirs!G7 dated Kwidagadura row.', 725500),
    ('SOCIAL_PLUS', datetime.date(2025, 2, 4), 'event', 'Remboursement', 'Social Loisirs!G8 formula component: 152000+5000.', 157000),
    ('SOCIAL_PLUS', datetime.date(2025, 5, 1), 'event', 'Frais de notaire', 'Social Loisirs!G9 formula component: 50000+200. Note: Rurangirwa.', 50200),
    ('SOCIAL_PLUS', datetime.date(2025, 5, 1), 'event', 'Frais de representation', 'Social Loisirs!G10 dated Kwidagadura row.', 498000),
    ('SOCIAL_PLUS', datetime.date(2025, 5, 14), 'event', 'Inama ya komite', 'Social Loisirs!G11 dated Kwidagadura row.', 20000),
    ('SOCIAL_PLUS', datetime.date(2025, 10, 13), 'event', 'Inama ya komite', 'Social Loisirs!G12 formula component: 2525+100+2525+100+6775+2525.', 14550),
    ('SOCIAL_PLUS', datetime.date(2025, 11, 20), 'event', 'Avance Sortie du 20 Dec', 'Social Loisirs!G13 dated Kwidagadura row.', 300000),
    ('SOCIAL_PLUS', datetime.date(2025, 12, 17), 'event', 'Avance Jumping Castle', 'Social Loisirs!G14 formula component: 100000+200.', 100200),
    ('SOCIAL_PLUS', datetime.date(2025, 12, 20), 'event', 'Solde Jumping Castle', 'Social Loisirs!G15 formula component: 100000+200.', 100200),
    ('SOCIAL_PLUS', datetime.date(2025, 12, 20), 'event', 'Solde Sortie', 'Social Loisirs!G16 formula component: 1292500-G13.', 992500),
    ('SOCIAL_PLUS', datetime.date(2025, 12, 21), 'event', 'Noel', 'Social Loisirs!G17 formula component: (50000*40)+(200*38).', 2007600),
    ('SOCIAL_PLUS', datetime.date(2026, 1, 18), 'event', 'Audit meeting', 'Social Loisirs!G18 formula component: 100+4900+100+4900+4900.', 14900),
    ('SOCIAL_PLUS', datetime.date(2026, 4, 12), 'event', 'Audit meeting', 'Social Loisirs!G19 formula component: 4900+100+4900+100+4900.', 14900),
    ('SOCIAL_PLUS', datetime.date(2026, 4, 20), 'event', 'Logiciel meeting', 'Social Loisirs!G20 formula component: 4900+100+4900+100+4900.', 14900),
    ('SOCIAL_PLUS', datetime.date(2026, 5, 1), 'event', 'Logiciel meeting', 'Social Loisirs!G21 formula component: 4900+100+4900+100+4900.', 14900),
]

EXPENSES = SOCIAL_EXPENSES + SOCIAL_PLUS_EXPENSES

EXPECTED_TOTALS = {
    'SOCIAL': 3169780,
    'SOCIAL_PLUS': 9956100,
}


def seed(apps, schema_editor):
    SocialActivityRecord = apps.get_model('core', 'SocialActivityRecord')
    LedgerEntry = apps.get_model('core', 'LedgerEntry')
    FundAccount = apps.get_model('core', 'FundAccount')

    totals = {
        'SOCIAL': sum(amount for fund_code, _, _, _, _, amount in EXPENSES if fund_code == 'SOCIAL'),
        'SOCIAL_PLUS': sum(amount for fund_code, _, _, _, _, amount in EXPENSES if fund_code == 'SOCIAL_PLUS'),
    }
    if totals != EXPECTED_TOTALS:
        raise ValueError(f'Social expense seed totals do not match workbook totals: {totals}')

    funds = {
        'SOCIAL': FundAccount.objects.get(code='SOCIAL'),
        'SOCIAL_PLUS': FundAccount.objects.get(code='SOCIAL_PLUS'),
    }
    entry_types = {
        'SOCIAL': 'social_expense',
        'SOCIAL_PLUS': 'social_plus_expense',
    }

    ledger_entries = []

    for fund_code, activity_date, category, name, description, amount in EXPENSES:
        record = SocialActivityRecord.objects.create(
            fund_account=funds[fund_code],
            activity_date=activity_date,
            category=category,
            name=name,
            description=f'{description} Source: {SOURCE_WORKBOOK}.',
            amount=Decimal(amount),
            recorded_by=None,
        )
        ledger_entries.append(LedgerEntry(
            fund_account=funds[fund_code],
            member=None,
            entry_date=activity_date,
            entry_type=entry_types[fund_code],
            amount=Decimal(amount),
            direction='debit',
            reference_id=record.id,
            reference_type='social_activity_record',
            notes=f'Seeded from {SOURCE_WORKBOOK}.',
            recorded_by=None,
        ))

    LedgerEntry.objects.bulk_create(ledger_entries)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0125_reconcile_contributions_mbr_0049'),
    ]

    operations = [
        migrations.RunPython(seed, reverse_code=migrations.RunPython.noop),
    ]
