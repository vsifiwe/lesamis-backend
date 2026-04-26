from decimal import Decimal

from django.db import migrations

# ──────────────────────────────────────────────────────────────────
# Member : Vanessa  (MBR-0008)
# Months : 58
# ──────────────────────────────────────────────────────────────────
# Fund           Total credited
# CAPITAL              7,880,000
# SOCIAL                 130,500
# SOCIAL_PLUS            168,000
# TOTAL                8,178,500
# ──────────────────────────────────────────────────────────────────

MEMBER_NUMBER = 'MBR-0008'

# (year, month, capital, social, social_plus)
CONTRIBUTIONS = [
    (2020,  8,  300000, 2000,    0),
    (2020,  9,   20000, 2000,    0),
    (2020, 10,   20000, 2000,    0),
    (2020, 11,   20000, 2000,    0),
    (2020, 12,   20000, 2000,    0),
    (2021,  1,   20000, 2000,    0),
    (2021,  2,   20000, 2000,    0),
    (2021,  3,   20000, 2000,    0),
    (2021,  4,   20000, 2000,    0),
    (2021,  5,   20000, 2000, 3000),
    (2021,  6,   20000, 2500, 3000),
    (2021,  7,   20000, 2000, 3000),
    (2021,  8,   20000, 2000, 3000),
    (2021,  9,   20000, 2000, 3000),
    (2021, 10,   20000, 2000, 3000),
    (2021, 11,   20000, 2000, 3000),
    (2022,  1,  690000, 4000, 6000),
    (2022,  2,   40000, 2000, 3000),
    (2022,  3,   30000, 2000, 3000),
    (2022,  4,   40000, 2000, 3000),
    (2022,  5,   40000, 2000, 3000),
    (2022,  6,   40000, 2000, 3000),
    (2022,  7,   40000, 2000, 3000),
    (2022,  8,   40000, 2000, 3000),
    (2022,  9,   40000, 2000, 3000),
    (2022, 10,   80000, 4000, 6000),
    (2022, 12,   40000, 2000, 3000),
    (2023,  1,   40000, 2000, 3000),
    (2023,  2,   40000, 2000, 3000),
    (2023,  3,   40000, 2000, 3000),
    (2023,  4,   40000, 2000, 3000),
    (2023,  5,   40000, 2000, 3000),
    (2023,  6,   40000, 2000, 3000),
    (2023,  7,   40000, 2000, 3000),
    (2023,  8,   40000, 2000, 3000),
    (2023,  9,   40000, 2000, 3000),
    (2023, 10,   40000, 2000, 3000),
    (2023, 11,   40000, 2000, 3000),
    (2023, 12,   80000, 4000, 6000),
    (2024,  2,   40000, 2000, 3000),
    (2024,  3, 2360000, 2000, 3000),
    (2024,  4,   80000, 2000, 3000),
    (2024,  5,   80000, 2000, 3000),
    (2024,  6,   80000, 2000, 3000),
    (2024,  7,   80000, 2000, 3000),
    (2024,  8,  160000, 4000, 6000),
    (2024, 10,   80000, 2000, 3000),
    (2024, 11,   80000, 2000, 3000),
    (2024, 12,   80000, 2000, 3000),
    (2025,  1,   80000, 2000, 3000),
    (2025,  2,  240000, 6000, 9000),
    (2025,  3, 1500000, 2000, 3000),
    (2025,  4,  100000, 2000, 3000),
    (2025,  5,  100000, 2000, 3000),
    (2025,  7,  200000, 4000, 6000),
    (2025,  8,  100000, 2000, 3000),
    (2025,  9,  100000, 2000, 3000),
    (2025, 10,  100000, 2000, 3000),
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
        ('core', '0034_seed_contributions_mbr_0007'),
    ]

    operations = [
        migrations.RunPython(seed, reverse_code=migrations.RunPython.noop),
    ]
