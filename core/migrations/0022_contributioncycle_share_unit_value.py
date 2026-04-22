from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_investment_expected_interest_rate_percent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='contributioncycle',
            name='share_unit_value',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
