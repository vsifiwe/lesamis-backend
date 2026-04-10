from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_share_purchase_entry_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='investment',
            name='expected_interest_rate_percent',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name='investment',
            name='vesting_period_months',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
