import calendar
import datetime

from django.db import migrations

# (year, month, status)
# Aug 2020 → Mar 2026: closed  |  Apr 2026 → Dec 2026: open
CYCLES = [
    # 2020
    (2020,  8, 'closed'),
    (2020,  9, 'closed'),
    (2020, 10, 'closed'),
    (2020, 11, 'closed'),
    (2020, 12, 'closed'),
    # 2021
    (2021,  1, 'closed'),
    (2021,  2, 'closed'),
    (2021,  3, 'closed'),
    (2021,  4, 'closed'),
    (2021,  5, 'closed'),
    (2021,  6, 'closed'),
    (2021,  7, 'closed'),
    (2021,  8, 'closed'),
    (2021,  9, 'closed'),
    (2021, 10, 'closed'),
    (2021, 11, 'closed'),
    (2021, 12, 'closed'),
    # 2022
    (2022,  1, 'closed'),
    (2022,  2, 'closed'),
    (2022,  3, 'closed'),
    (2022,  4, 'closed'),
    (2022,  5, 'closed'),
    (2022,  6, 'closed'),
    (2022,  7, 'closed'),
    (2022,  8, 'closed'),
    (2022,  9, 'closed'),
    (2022, 10, 'closed'),
    (2022, 11, 'closed'),
    (2022, 12, 'closed'),
    # 2023
    (2023,  1, 'closed'),
    (2023,  2, 'closed'),
    (2023,  3, 'closed'),
    (2023,  4, 'closed'),
    (2023,  5, 'closed'),
    (2023,  6, 'closed'),
    (2023,  7, 'closed'),
    (2023,  8, 'closed'),
    (2023,  9, 'closed'),
    (2023, 10, 'closed'),
    (2023, 11, 'closed'),
    (2023, 12, 'closed'),
    # 2024
    (2024,  1, 'closed'),
    (2024,  2, 'closed'),
    (2024,  3, 'closed'),
    (2024,  4, 'closed'),
    (2024,  5, 'closed'),
    (2024,  6, 'closed'),
    (2024,  7, 'closed'),
    (2024,  8, 'closed'),
    (2024,  9, 'closed'),
    (2024, 10, 'closed'),
    (2024, 11, 'closed'),
    (2024, 12, 'closed'),
    # 2025
    (2025,  1, 'closed'),
    (2025,  2, 'closed'),
    (2025,  3, 'closed'),
    (2025,  4, 'closed'),
    (2025,  5, 'closed'),
    (2025,  6, 'closed'),
    (2025,  7, 'closed'),
    (2025,  8, 'closed'),
    (2025,  9, 'closed'),
    (2025, 10, 'closed'),
    (2025, 11, 'closed'),
    (2025, 12, 'closed'),
    # 2026
    (2026,  1, 'closed'),
    (2026,  2, 'closed'),
    (2026,  3, 'closed'),
    (2026,  4, 'open'),
    (2026,  5, 'open'),
    (2026,  6, 'open'),
    (2026,  7, 'open'),
    (2026,  8, 'open'),
    (2026,  9, 'open'),
    (2026, 10, 'open'),
    (2026, 11, 'open'),
    (2026, 12, 'open'),
]


def _clamped_date(year, month, day):
    last_day = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, min(day, last_day))


def _next_month(year, month):
    return (year + 1, 1) if month == 12 else (year, month + 1)


def seed_contribution_cycles(apps, schema_editor):
    ContributionCycle = apps.get_model('core', 'ContributionCycle')
    for year, month, status in CYCLES:
        extra_year, extra_month = _next_month(year, month)
        ContributionCycle.objects.get_or_create(
            year=year,
            month=month,
            defaults={
                'due_date':                 _clamped_date(year, month, 20),
                'late_penalty_start_date':  _clamped_date(year, month, 25),
                'extra_penalty_start_date': _clamped_date(extra_year, extra_month, 5),
                'status':                   status,
                'share_unit_value':         None,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_membercontributionobligation_shares_to_grant'),
    ]

    operations = [
        migrations.RunPython(seed_contribution_cycles, reverse_code=migrations.RunPython.noop),
    ]
