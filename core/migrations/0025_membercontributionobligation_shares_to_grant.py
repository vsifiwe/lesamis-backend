from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_fix_interest_rate_scale'),
    ]

    operations = [
        migrations.AddField(
            model_name='membercontributionobligation',
            name='shares_to_grant',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
