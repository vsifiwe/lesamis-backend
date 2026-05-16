from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Sum

SOURCE_WORKBOOK = 'Situation les Amis Sept 2023 Version.xlsx'

CONTRIBUTION_ENTRY_TYPES = {
    'contribution_capital': 'capital_amount_expected',
    'contribution_social': 'social_amount_expected',
    'contribution_social_plus': 'social_plus_amount_expected',
}

EXPECTED_RECEIPT_COUNT = 1934
EXPECTED_RECEIPT_ITEM_TOTAL = Decimal('86599111.00')


def _zero():
    return Decimal('0.00')


def _as_int_amount(amount):
    if amount != amount.to_integral_value():
        raise ValueError(f'Expected whole-currency contribution amount, got {amount}')
    return int(amount)


def backfill_receipts(apps, schema_editor):
    ContributionReceipt = apps.get_model('core', 'ContributionReceipt')
    ContributionReceiptItem = apps.get_model('core', 'ContributionReceiptItem')
    MemberContributionObligation = apps.get_model('core', 'MemberContributionObligation')
    LedgerEntry = apps.get_model('core', 'LedgerEntry')

    obligations = (
        MemberContributionObligation.objects
        .filter(
            obligation_type='contribution',
            status='confirmed',
            receipt_items__isnull=True,
        )
        .select_related('member', 'contribution_cycle')
        .order_by('member__member_number', 'contribution_cycle__year', 'contribution_cycle__month')
    )

    receipts = []
    receipt_items = []
    total_receipted = _zero()
    adjusted_obligation_count = 0

    for obligation in obligations:
        ledger_totals = {
            row['entry_type']: row['total'] or _zero()
            for row in (
                LedgerEntry.objects
                .filter(
                    reference_id=obligation.id,
                    entry_type__in=CONTRIBUTION_ENTRY_TYPES.keys(),
                    amount__gt=0,
                )
                .values('entry_type')
                .annotate(total=Sum('amount'))
            )
        }
        capital = ledger_totals.get('contribution_capital', _zero())
        social = ledger_totals.get('contribution_social', _zero())
        social_plus = ledger_totals.get('contribution_social_plus', _zero())
        receipt_total = capital + social + social_plus

        if receipt_total <= _zero():
            raise ValueError(f'No positive linked contribution ledger total for obligation {obligation.id}')

        stored_total = Decimal(obligation.total_amount_expected)
        if receipt_total != stored_total:
            if receipt_total < stored_total:
                raise ValueError(
                    f'Linked ledger total {receipt_total} is below obligation total '
                    f'{stored_total} for obligation {obligation.id}'
                )
            obligation.capital_amount_expected = _as_int_amount(capital)
            obligation.social_amount_expected = _as_int_amount(social)
            obligation.social_plus_amount_expected = _as_int_amount(social_plus)
            obligation.total_amount_expected = _as_int_amount(receipt_total)
            obligation.save(update_fields=[
                'capital_amount_expected',
                'social_amount_expected',
                'social_plus_amount_expected',
                'total_amount_expected',
                'updated_at',
            ])
            adjusted_obligation_count += 1

        cycle = obligation.contribution_cycle
        receipt = ContributionReceipt.objects.create(
            amount_received=receipt_total,
            received_date=cycle.due_date,
            payment_method='bank',
            status='confirmed',
            confirmed_by=None,
            confirmed_at=None,
            notes=(
                'Historical workbook receipt backfill. '
                f'Source: {SOURCE_WORKBOOK}; '
                f'member={obligation.member.member_number}; '
                f'cycle={cycle.year}-{cycle.month:02d}.'
            ),
            created_by=None,
        )
        receipts.append(receipt)
        receipt_items.append(ContributionReceiptItem(
            receipt=receipt,
            obligation=obligation,
            amount_applied=receipt_total,
        ))
        total_receipted += receipt_total

    ContributionReceiptItem.objects.bulk_create(receipt_items)

    created_count = len(receipts)
    if created_count != EXPECTED_RECEIPT_COUNT:
        raise ValueError(f'Expected {EXPECTED_RECEIPT_COUNT} receipts, created {created_count}')
    if len(receipt_items) != EXPECTED_RECEIPT_COUNT:
        raise ValueError(f'Expected {EXPECTED_RECEIPT_COUNT} receipt items, created {len(receipt_items)}')
    if total_receipted != EXPECTED_RECEIPT_ITEM_TOTAL:
        raise ValueError(
            f'Expected receipt item total {EXPECTED_RECEIPT_ITEM_TOTAL}, got {total_receipted}'
        )
    if adjusted_obligation_count != 14:
        raise ValueError(f'Expected to adjust 14 obligations, adjusted {adjusted_obligation_count}')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0129_seed_banki_other_charges'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contributionreceipt',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='created_receipts',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(backfill_receipts, reverse_code=migrations.RunPython.noop),
    ]
