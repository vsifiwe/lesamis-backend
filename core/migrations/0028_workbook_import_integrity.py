from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_import_normalized_workbook'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='loan',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('first_due_date__isnull', True), ('is_opening_balance', True), ('issued_date__isnull', True)), models.Q(('first_due_date__isnull', False), ('is_opening_balance', False), ('issued_date__isnull', False)), _connector='OR'), name='loan_opening_balance_dates'),
        ),
        migrations.AddConstraint(
            model_name='incomeentry',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('date_precision', 'unknown'), ('income_date__isnull', True)), models.Q(('date_precision__in', ['exact', 'month', 'period']), ('income_date__isnull', False)), _connector='OR'), name='income_date_matches_precision'),
        ),
        migrations.AddConstraint(
            model_name='ledgerentry',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('date_precision', 'unknown'), ('entry_date__isnull', True)), models.Q(('date_precision__in', ['exact', 'month', 'period']), ('entry_date__isnull', False)), _connector='OR'), name='ledger_date_matches_precision'),
        ),
        migrations.AddConstraint(
            model_name='loanrepayment',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('date_precision', 'unknown'), ('paid_date__isnull', True)), models.Q(('date_precision__in', ['exact', 'month', 'period']), ('paid_date__isnull', False)), _connector='OR'), name='repayment_date_matches_precision'),
        ),
        migrations.AddConstraint(
            model_name='othercharge',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('charge_date__isnull', True), ('date_precision', 'unknown')), models.Q(('charge_date__isnull', False), ('date_precision__in', ['exact', 'month', 'period'])), _connector='OR'), name='other_charge_date_matches_precision'),
        ),
        migrations.AddConstraint(
            model_name='socialactivityrecord',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('activity_date__isnull', True), ('date_precision', 'unknown')), models.Q(('activity_date__isnull', False), ('date_precision__in', ['exact', 'month', 'period'])), _connector='OR'), name='social_activity_date_matches_precision'),
        ),
    ]
