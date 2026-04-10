from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_ledger_entry'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ledgerentry',
            name='entry_type',
            field=models.CharField(
                choices=[
                    ('contribution_capital',     'Contribution — Capital'),
                    ('contribution_social',      'Contribution — Social'),
                    ('contribution_social_plus', 'Contribution — Social+'),
                    ('late_penalty',             'Late Penalty'),
                    ('other_charge',             'Other Charge'),
                    ('loan_disbursement',        'Loan Disbursement'),
                    ('loan_repayment',           'Loan Repayment'),
                    ('investment_purchase',      'Investment Purchase'),
                    ('investment_profit',        'Investment Profit'),
                    ('social_expense',           'Social Expense'),
                    ('social_plus_expense',      'Social+ Expense'),
                    ('share_purchase',           'Share Purchase'),
                ],
                max_length=30,
            ),
        ),
    ]
