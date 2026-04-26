from decimal import Decimal

from django.db import migrations

# ──────────────────────────────────────────────────────────────────
# Member : Arsene  (MBR-0027)
# Months : 8
# ──────────────────────────────────────────────────────────────────
# Fund           Total credited
# CAPITAL                690,000
# SOCIAL                  70,000
# SOCIAL_PLUS             36,000
# TOTAL                  796,000
# ──────────────────────────────────────────────────────────────────

MEMBER_NUMBER = 'MBR-0027'

# (year, month, capital, social, social_plus)
CONTRIBUTIONS = [
    (2021,  8,  102000, 54000, 12000),
    (2021,  9,   10000, 2000, 3000),
    (2021, 11,   20000, 4000, 6000),
    (2021, 12,  198000, 6000, 9000),
    (2022,  1,  310000,    0,    0),
    (2022,  2,   20000,    0,    0),
    (2022,  3,   10000, 2000, 3000),
    (2022,  4,   20000, 2000, 3000),
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
        ('core', '0053_seed_contributions_mbr_0026'),
    ]

    operations = [
        migrations.RunPython(seed, reverse_code=migrations.RunPython.noop),
    ]
