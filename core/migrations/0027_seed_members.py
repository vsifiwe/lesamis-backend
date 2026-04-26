import datetime

from django.db import migrations

# (first_name, last_name, join_year, join_month)
# Names taken from "Contribution Individuel Mensuel" sheet, sheet row order preserved.
# last_name is empty where the Excel shows only a single name.
# "Vanessa M" and "Claudine M" use "M" as last_name to distinguish from their namesakes.
# join_date = 1st of the month of their first recorded contribution.
MEMBERS = [
    ('Didier',     '',  2020,  8),
    ('Claudine',   '',  2020,  8),
    ('Eric',       '',  2020,  8),
    ('Delphine',   '',  2020,  8),
    ('Clement',    '',  2020,  8),
    ('Sandrine',   '',  2020,  8),
    ('Semanzi',    '',  2020,  8),
    ('Vanessa',    '',  2020,  8),
    ('Musonera',   '',  2020,  8),
    ('Yvonne',     '',  2020,  8),
    ('Fidele',     '',  2020,  8),
    ('Thadée',     '',  2020,  8),
    ('Diane',      '',  2020,  8),
    ('Kamana',     '',  2020,  8),
    ('Gerardine',  '',  2020,  8),
    ('Tuyizere',   '',  2020,  8),
    ('Venuste',    '',  2020,  8),
    ('Dalyda',     '',  2020,  8),
    ('Chantal',    '',  2021,  1),
    ('Edissa',     '',  2021,  6),
    ('Vital',      '',  2021,  6),
    ('Obadias',    '',  2021,  6),
    ('Arnauld',    '',  2021,  7),
    ('Joelle',     '',  2021,  7),
    ('Florent',    '',  2021,  8),
    ('Edgard',     '',  2021,  9),
    ('Arsene',     '',  2021,  8),
    ('Emmanuel',   '',  2021,  9),
    ('Vanessa',    'M', 2021,  9),
    ('Janvier',    '',  2021,  9),
    ('Claude',     '',  2022,  3),
    ('Gedeon',     '',  2022,  9),
    ('Phoebe',     '',  2022,  9),
    ('Claudine',   'M', 2023,  2),
    ('Edmond',     '',  2023,  5),
    ('Belyse',     '',  2023,  6),
    ('Byiringiro', '',  2023,  9),
    ('Elie',       '',  2023, 12),
    ('Seraphina',  '',  2023, 12),
    ('Faustin',    '',  2024,  1),
    ('Epimaque',   '',  2024,  1),
    ('Simon',      '',  2024,  3),
    ('Manzi',      '',  2024,  9),
    ('Divine',     '',  2024,  9),
    ('Frank',      '',  2024,  9),
    ('Chrisitan',  '',  2024, 10),  # spelling preserved from source sheet
    ('Yannick',    '',  2025,  1),
    ('Janviere',   '',  2025,  1),
    ('Emily',      '',  2025,  4),
]


def seed_members(apps, schema_editor):
    Member = apps.get_model('core', 'Member')
    MemberShareAccount = apps.get_model('core', 'MemberShareAccount')

    for i, (first_name, last_name, join_year, join_month) in enumerate(MEMBERS, start=1):
        member_number = f'MBR-{i:04d}'
        member, _ = Member.objects.get_or_create(
            member_number=member_number,
            defaults={
                'first_name': first_name,
                'last_name':  last_name,
                'status':     'active',
                'join_date':  datetime.date(join_year, join_month, 1),
            },
        )
        MemberShareAccount.objects.get_or_create(
            member=member,
            defaults={
                'share_count':      0,
                'share_unit_value': 10000,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_seed_contribution_cycles'),
    ]

    operations = [
        migrations.RunPython(seed_members, reverse_code=migrations.RunPython.noop),
    ]
