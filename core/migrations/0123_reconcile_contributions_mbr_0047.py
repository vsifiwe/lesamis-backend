from decimal import Decimal

from django.db import migrations

# ------------------------------------------------------------------
# Excel reconciliation for Yannick (MBR-0047)
# Source: Situation les Amis Sept 2023 Version.xlsx / Contribution Individuel Mensuel
# Rows: 1
# ------------------------------------------------------------------
# Fund           Delta credited
# CAPITAL                120,000
# SOCIAL                  24,000
# SOCIAL_PLUS             36,000
# TOTAL                  180,000
# ------------------------------------------------------------------

MEMBER_NUMBER = 'MBR-0047'
SOURCE_WORKBOOK = 'Situation les Amis Sept 2023 Version.xlsx'
REFERENCE_TYPE = 'excel_contribution_reconciliation'

# (year, month, capital_delta, social_delta, social_plus_delta)
DELTAS = [
    (2026,  1,   120000,  24000,  36000)
]


def seed(apps, schema_editor):
    Member = apps.get_model('core', 'Member')
    ContributionCycle = apps.get_model('core', 'ContributionCycle')
    MemberContributionObligation = apps.get_model('core', 'MemberContributionObligation')
    LedgerEntry = apps.get_model('core', 'LedgerEntry')
    FundAccount = apps.get_model('core', 'FundAccount')

    member = Member.objects.get(member_number=MEMBER_NUMBER)
    funds = {
        'capital': FundAccount.objects.get(code='CAPITAL'),
        'social': FundAccount.objects.get(code='SOCIAL'),
        'social_plus': FundAccount.objects.get(code='SOCIAL_PLUS'),
    }
    entry_types = {
        'capital': 'contribution_capital',
        'social': 'contribution_social',
        'social_plus': 'contribution_social_plus',
    }

    SHARE_PRICE = 10_000
    entries = []

    for year, month, capital, social, social_plus in DELTAS:
        cycle = ContributionCycle.objects.get(year=year, month=month)
        amounts = {
            'capital': capital,
            'social': social,
            'social_plus': social_plus,
        }
        ref_id = None

        if all(amount >= 0 for amount in amounts.values()) and any(amounts.values()):
            total = capital + social + social_plus
            obligation, _ = MemberContributionObligation.objects.get_or_create(
                member=member,
                contribution_cycle=cycle,
                obligation_type='contribution',
                defaults={
                    'share_count_snapshot': max(1, capital // SHARE_PRICE),
                    'share_unit_value_snapshot': SHARE_PRICE,
                    'capital_amount_expected': capital,
                    'social_amount_expected': social,
                    'social_plus_amount_expected': social_plus,
                    'total_amount_expected': total,
                    'status': 'confirmed',
                },
            )
            ref_id = obligation.id

        notes = f'Excel reconciliation from {SOURCE_WORKBOOK} for {year}-{month:02d}.'

        for key, amount in amounts.items():
            if amount:
                entries.append(LedgerEntry(
                    fund_account=funds[key],
                    member=member,
                    entry_date=cycle.due_date,
                    entry_type=entry_types[key],
                    amount=Decimal(amount),
                    direction='credit',
                    reference_id=ref_id,
                    reference_type=REFERENCE_TYPE,
                    notes=notes,
                ))

    LedgerEntry.objects.bulk_create(entries)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0122_reconcile_contributions_mbr_0046'),
    ]

    operations = [
        migrations.RunPython(seed, reverse_code=migrations.RunPython.noop),
    ]
