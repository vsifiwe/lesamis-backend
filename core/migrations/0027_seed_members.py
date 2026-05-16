import datetime

from django.db import migrations

# (first_name, last_name, join_year, join_month)
# Names taken from "Contribution Individuel Mensuel" sheet, sheet row order preserved.
# last_name is empty where the Excel shows only a single name.
# "Vanessa M" and "Claudine M" use "M" as last_name to distinguish from their namesakes.
# join_date = 1st of the month of their first recorded contribution.
MEMBERS = [
    ('Didier',     '',  2020,  8, 10),
    ('Claudine',   '',  2020,  8, 2),
    ('Eric',       '',  2020,  8, 5),
    ('Delphine',   '',  2020,  8, 2),
    ('Clement',    '',  2020,  8, 0),
    ('Sandrine',   '',  2020,  8, 2),
    ('Semanzi',    '',  2020,  8, 1),
    ('Vanessa',    '',  2020,  8, 10),
    ('Musonera',   '',  2020,  8, 0),
    ('Yvonne',     '',  2020,  8, 0),
    ('Fidele',     '',  2020,  8, 3),
    ('Thadée',     '',  2020,  8, 0),
    ('Diane',      '',  2020,  8, 0),
    ('Kamana',     '',  2020,  8, 0),
    ('Gerardine',  '',  2020,  8, 1),
    ('Tuyizere',   '',  2020,  8, 3),
    ('Venuste',    '',  2020,  8, 2),
    ('Dalyda',     '',  2020,  8, 1),
    ('Chantal',    '',  2021,  1, 1),
    ('Edissa',     '',  2021,  6, 1),
    ('Vital',      '',  2021,  6, 2),
    ('Obadias',    '',  2021,  6, 1),
    ('Arnauld',    '',  2021,  7, 1),
    ('Joelle',     '',  2021,  7, 2),
    ('Florent',    '',  2021,  8, 1),
    ('Edgard',     '',  2021,  9, 0),
    ('Arsene',     '',  2021,  8, 0),
    ('Emmanuel',   '',  2021,  9, 0),
    ('Vanessa',    'M', 2021,  9, 1),
    ('Janvier',    '',  2021,  9, 1),
    ('Claude',     '',  2022,  3, 2),
    ('Gedeon',     '',  2022,  9, 2),
    ('Phoebe',     '',  2022,  9, 1),
    ('Claudine',   'M', 2023,  2, 1),
    ('Edmond',     '',  2023,  5, 3),
    ('Belyse',     '',  2023,  6, 1),
    ('Byiringiro', '',  2023,  9, 2),
    ('Elie',       '',  2023, 12, 1),
    ('Seraphina',  '',  2023, 12, 1),
    ('Faustin',    '',  2024,  1, 1),
    ('Epimaque',   '',  2024,  1, 1),
    ('Simon',      '',  2024,  3, 0),
    ('Manzi',      '',  2024,  9, 1),
    ('Divine',     '',  2024,  9, 1),
    ('Frank',      '',  2024,  9, 1),
    ('Chrisitan',  '',  2024, 10, 1),  # spelling preserved from source sheet
    ('Yannick',    '',  2025,  1, 1),
    ('Janviere',   '',  2025,  1, 1),
    ('Emily',      '',  2025,  4, 1),
]


def seed_members(apps, schema_editor):
    Member = apps.get_model('core', 'Member')
    MemberShareAccount = apps.get_model('core', 'MemberShareAccount')

    for i, (first_name, last_name, join_year, join_month, share_count) in enumerate(MEMBERS, start=1):
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
                'share_count':      share_count,
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
