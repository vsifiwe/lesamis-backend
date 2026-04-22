import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_contributioncycle_share_unit_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='membercontributionobligation',
            name='obligation_type',
            field=models.CharField(
                choices=[('contribution', 'Contribution'), ('share_purchase', 'Share Purchase')],
                default='contribution',
                max_length=20,
            ),
        ),
        migrations.RemoveConstraint(
            model_name='membercontributionobligation',
            name='unique_obligation_member_cycle',
        ),
        migrations.AddConstraint(
            model_name='membercontributionobligation',
            constraint=models.UniqueConstraint(
                condition=models.Q(obligation_type='contribution'),
                fields=['member', 'contribution_cycle'],
                name='unique_obligation_member_cycle',
            ),
        ),
        migrations.AlterField(
            model_name='membercontributionobligation',
            name='contribution_cycle',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='obligations',
                to='core.contributioncycle',
            ),
        ),
        migrations.AlterModelOptions(
            name='membercontributionobligation',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Member Contribution Obligation',
                'verbose_name_plural': 'Member Contribution Obligations',
            },
        ),
    ]
