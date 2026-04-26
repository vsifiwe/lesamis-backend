from decimal import Decimal

from django.db import migrations

# ──────────────────────────────────────────────────────────────────
# Member : Dalyda  (MBR-0018)
# Months : 59
# ──────────────────────────────────────────────────────────────────
# Fund           Total credited
# CAPITAL              1,798,711
# SOCIAL                 158,000
# SOCIAL_PLUS            168,000
# TOTAL                2,124,711
# ──────────────────────────────────────────────────────────────────

MEMBER_NUMBER = 'MBR-0018'

# (year, month, capital, social, social_plus)
CONTRIBUTIONS = [
    (2020,  8,  160000, 32000,    0),
    (2020,  9,   10000, 2000,    0),
    (2020, 10,   10000, 2000,    0),
    (2020, 11,   10000, 2000,    0),
    (2021,  1,   20000, 4000,    0),
    (2021,  2,   10000, 2000,    0),
    (2021,  4,   10000, 2000,    0),
    (2021,  5,   10000, 2000, 3000),
    (2021,  6,   10000, 2000, 3000),
    (2021,  7,   10000, 2000, 3000),
    (2021,  8,   10000, 2000, 3000),
    (2021,  9,   10000, 2000, 3000),
    (2021, 10,   10000, 2000, 3000),
    (2021, 11,   10000, 2000, 3000),
    (2021, 12,  340000, 4000, 6000),
    (2022,  1,   20000, 2000, 3000),
    (2022,  3,   40000, 4000, 6000),
    (2022,  5,   20000, 2000, 3000),
    (2022,  6,   20000, 2000, 3000),
    (2022,  7,   20000, 2000, 3000),
    (2022,  8,   20000, 2000, 3000),
    (2022,  9,   20000, 2000, 3000),
    (2022, 10,   10000, 2000, 3000),
    (2022, 11,   10000, 2000, 3000),
    (2022, 12,  318711, 2000, 3000),
    (2023,  1,   20000, 2000, 3000),
    (2023,  2,   20000, 2000, 3000),
    (2023,  3,   20000, 2000, 3000),
    (2023,  4,   20000, 2000, 3000),
    (2023,  5,   20000, 2000, 3000),
    (2023,  6,   20000, 2000, 3000),
    (2023,  7,   20000, 2000, 3000),
    (2023,  8,   20000, 2000, 3000),
    (2023,  9,   20000, 2000, 3000),
    (2023, 10,   20000, 2000, 3000),
    (2023, 11,   20000, 2000, 3000),
    (2023, 12,   20000, 2000, 3000),
    (2024,  1,   20000, 2000, 3000),
    (2024,  2,   20000, 2000, 3000),
    (2024,  3,   40000, 4000, 6000),
    (2024,  5,   20000, 2000, 3000),
    (2024,  6,   20000, 2000, 3000),
    (2024,  7,   20000, 2000, 3000),
    (2024,  8,   20000, 2000, 3000),
    (2024,  9,   20000, 2000, 3000),
    (2024, 11,   40000, 4000, 6000),
    (2024, 12,   20000, 2000, 3000),
    (2025,  1,   20000, 2000, 3000),
    (2025,  2,   20000, 2000, 3000),
    (2025,  3,   20000, 2000, 3000),
    (2025,  4,   20000, 2000, 3000),
    (2025,  5,   20000, 2000, 3000),
    (2025,  6,   20000, 2000, 3000),
    (2025,  7,   20000, 2000, 3000),
    (2025,  8,       0, 2000, 3000),
    (2025,  9,   10000, 2000, 3000),
    (2025, 10,   10000, 2000, 3000),
    (2025, 11,   10000, 2000, 3000),
    (2025, 12,   10000, 2000, 3000),
]


def seed(apps, schema_editor):
    Member = apps.get_model('core', 'Member')
    ContributionCycle = apps.get_model('core', 'ContributionCycle')
    MemberContributionObligation = apps.get_model('core', 'MemberContributionObligation')
    LedgerEntry = apps.get_model('core', 'LedgerEntry')
    FundAccount = apps.get_model('core', 'FundAccount')

    member      = Member.objects.get(member_number=MEMBER_NUMBER)
    cap_fund    = FundAccount.objects.get(code='CAPITAL')
    soc_fund    = FundAccount.objects.get(code='SOCIAL')
    socp_fund   = FundAccount.objects.get(code='SOCIAL_PLUS')

    SHARE_PRICE = 10_000
    entries = []

    for year, month, capital, social, social_plus in CONTRIBUTIONS:
        cycle = ContributionCycle.objects.get(year=year, month=month)
        total = capital + social + social_plus

        ob, _ = MemberContributionObligation.objects.get_or_create(
            member=member,
            contribution_cycle=cycle,
            obligation_type='contribution',
            defaults={
                'share_count_snapshot':        max(1, capital // SHARE_PRICE),
                'share_unit_value_snapshot':   SHARE_PRICE,
                'capital_amount_expected':     capital,
                'social_amount_expected':      social,
                'social_plus_amount_expected': social_plus,
                'total_amount_expected':       total,
                'status':                      'confirmed',
            },
        )

        ref_id, ref_type, date = ob.id, 'member_contribution_obligation', cycle.due_date

        if capital:
            entries.append(LedgerEntry(
                fund_account=cap_fund, member=member, entry_date=date,
                entry_type='contribution_capital', amount=Decimal(capital),
                direction='credit', reference_id=ref_id, reference_type=ref_type,
            ))
        if social:
            entries.append(LedgerEntry(
                fund_account=soc_fund, member=member, entry_date=date,
                entry_type='contribution_social', amount=Decimal(social),
                direction='credit', reference_id=ref_id, reference_type=ref_type,
            ))
        if social_plus:
            entries.append(LedgerEntry(
                fund_account=socp_fund, member=member, entry_date=date,
                entry_type='contribution_social_plus', amount=Decimal(social_plus),
                direction='credit', reference_id=ref_id, reference_type=ref_type,
            ))

    LedgerEntry.objects.bulk_create(entries)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0044_seed_contributions_mbr_0017'),
    ]

    operations = [
        migrations.RunPython(seed, reverse_code=migrations.RunPython.noop),
    ]
