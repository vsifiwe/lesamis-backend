from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_socialactivityrecord'),
    ]

    operations = [
        # Add nullable first so no default is needed for empty table
        migrations.AddField(
            model_name='othercharge',
            name='fund_account',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='other_charges',
                to='core.fundaccount',
                null=True,
            ),
        ),
        # Then tighten to non-nullable (table has no rows)
        migrations.AlterField(
            model_name='othercharge',
            name='fund_account',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='other_charges',
                to='core.fundaccount',
            ),
        ),
    ]
