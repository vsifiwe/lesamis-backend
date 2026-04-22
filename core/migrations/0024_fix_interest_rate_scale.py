from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations


def fix_rates(apps, schema_editor):
    LoanProduct = apps.get_model('core', 'LoanProduct')
    Loan = apps.get_model('core', 'Loan')

    # Multiply all stored rates by 100 (0.05 → 5.00)
    for product in LoanProduct.objects.all():
        product.interest_rate_percent = (product.interest_rate_percent * 100).quantize(Decimal('0.01'))
        product.save(update_fields=['interest_rate_percent'])

    for loan in Loan.objects.all():
        rate = (loan.interest_rate_percent_snapshot * 100).quantize(Decimal('0.01'))
        principal = loan.principal_amount
        duration = loan.duration_months_snapshot
        total = (principal * (1 + rate / 100)).quantize(Decimal('0.01'))
        monthly = (total / duration).quantize(Decimal('0.01'))
        loan.interest_rate_percent_snapshot = rate
        loan.total_repayment_amount = total
        loan.monthly_installment_amount = monthly
        loan.save(update_fields=[
            'interest_rate_percent_snapshot',
            'total_repayment_amount',
            'monthly_installment_amount',
        ])


def reverse_rates(apps, schema_editor):
    LoanProduct = apps.get_model('core', 'LoanProduct')
    Loan = apps.get_model('core', 'Loan')

    for product in LoanProduct.objects.all():
        product.interest_rate_percent = (product.interest_rate_percent / 100).quantize(Decimal('0.0001'))
        product.save(update_fields=['interest_rate_percent'])

    for loan in Loan.objects.all():
        rate = (loan.interest_rate_percent_snapshot / 100).quantize(Decimal('0.0001'))
        principal = loan.principal_amount
        duration = loan.duration_months_snapshot
        total = (principal * (1 + rate / 100)).quantize(Decimal('0.01'))
        monthly = (total / duration).quantize(Decimal('0.01'))
        loan.interest_rate_percent_snapshot = rate
        loan.total_repayment_amount = total
        loan.monthly_installment_amount = monthly
        loan.save(update_fields=[
            'interest_rate_percent_snapshot',
            'total_repayment_amount',
            'monthly_installment_amount',
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_membercontributionobligation_obligation_type'),
    ]

    operations = [
        migrations.RunPython(fix_rates, reverse_rates),
    ]
