from decimal import Decimal

from django.db import migrations

# ──────────────────────────────────────────────────────────────────
# Member : Belyse  (MBR-0036)
# Months : 27
# ──────────────────────────────────────────────────────────────────
# Fund           Total credited
# CAPITAL                790,000
# SOCIAL                 158,000
# SOCIAL_PLUS            168,000
# TOTAL                1,116,000
# ──────────────────────────────────────────────────────────────────

MEMBER_NUMBER = 'MBR-0036'

# (year, month, capital, social, social_plus)
CONTRIBUTIONS = [
    (2023,  6,  490000,    0,    0),
    (2023,  7,   10000, 2000, 3000),
    (2023,  8,   10000, 100000, 81000),
    (2023,  9,   10000, 2000, 3000),
    (2023, 10,   10000, 2000, 3000),
    (2023, 11,   10000, 2000, 3000),
    (2023, 12,   10000, 2000, 3000),
    (2024,  1,   10000, 2000, 3000),
    (2024,  2,   10000, 2000, 3000),
    (2024,  3,   10000, 2000, 3000),
    (2024,  4,   10000, 2000, 3000),
    (2024,  5,   10000, 2000, 3000),
    (2024,  6,   10000, 2000, 3000),
    (2024,  7,   10000, 2000, 3000),
    (2024,  8,   10000, 2000, 3000),
    (2024,  9,   10000, 2000, 3000),
    (2024, 10,   10000, 2000, 3000),
    (2024, 11,   10000, 2000, 3000),
    (2024, 12,   10000, 2000, 3000),
    (2025,  1,   10000, 2000, 3000),
    (2025,  3,   20000, 4000, 6000),
    (2025,  4,   20000, 4000, 6000),
    (2025,  7,   20000, 4000, 6000),
    (2025,  8,   10000, 2000, 3000),
    (2025,  9,   10000, 2000, 3000),
    (2025, 11,   20000, 4000, 6000),
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
        ('core', '0062_seed_contributions_mbr_0035'),
    ]

    operations = [
        migrations.RunPython(seed, reverse_code=migrations.RunPython.noop),
    ]
