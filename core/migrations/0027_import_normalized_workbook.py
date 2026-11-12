from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('core', '0026_workbook_import_support')]
    operations = []  # Tracker data is loaded explicitly after migrate.
