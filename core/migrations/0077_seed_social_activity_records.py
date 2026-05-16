import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0076_seed_contributions_mbr_0049'),
    ]

    operations = [
        migrations.AlterField(
            model_name='socialactivityrecord',
            name='recorded_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='recorded_social_activities',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
