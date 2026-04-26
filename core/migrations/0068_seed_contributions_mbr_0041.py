from decimal import Decimal

from django.db import migrations

# ──────────────────────────────────────────────────────────────────
# Member : Epimaque  (MBR-0041)
# Months : 20
# ──────────────────────────────────────────────────────────────────
# Fund           Total credited
# CAPITAL                800,000
# SOCIAL                 160,000
# SOCIAL_PLUS            171,000
# TOTAL                1,131,000
# ──────────────────────────────────────────────────────────────────

MEMBER_NUMBER = 'MBR-0041'

# (year, month, capital, social, social_plus)
CONTRIBUTIONS = [
    (2024,  1,  200000,    0,    0),
    (2024,  2,   10000, 2000, 3000),
    (2024,  3,   10000, 2000, 3000),
    (2024,  4,   10000, 2000, 3000),
    (2024,  5,  370000, 2000, 58000),
    (2024,  6,   10000, 2000, 3000),
    (2024,  7,   10000, 2000, 3000),
    (2024,  8,   10000, 2000, 3000),
    (2024,  9,   10000, 2000, 3000),
    (2024, 10,   20000, 4000, 6000),
    (2024, 12,   20000, 4000, 6000),
    (2025,  2,   10000, 2000, 3000),
    (2025,  3,   10000, 2000, 3000),
    (2025,  4,   10000, 2000, 3000),
    (2025,  5,   10000, 2000, 3000),
    (2025,  6,   10000, 114000, 47000),
    (2025,  7,   20000, 4000, 6000),
    (2025,  8,   10000, 2000, 3000),
    (2025,  9,   20000, 4000, 6000),
    (2025, 11,   20000, 4000, 6000),
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
        ('core', '0067_seed_contributions_mbr_0040'),
    ]

    operations = [
        migrations.RunPython(seed, reverse_code=migrations.RunPython.noop),
    ]
