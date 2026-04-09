import calendar
import datetime

from background_task import background
from django.utils import timezone

from .models import ContributionCycle, SystemConfig


def _clamped_date(year, month, day):
    """Return date(year, month, day), clamping day to the last day of the month.

    Prevents ValueError when a config day (e.g. 31) doesn't exist in shorter months.
    """
    last_day = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, min(day, last_day))


def _next_month(year, month):
    """Return (year, month) for the month following the given one."""
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _seconds_until_first_of_next_month():
    """Compute how many seconds from now until midnight UTC on the 1st of next month."""
    now = timezone.now()
    next_year, next_month = _next_month(now.year, now.month)
    next_run = datetime.datetime(next_year, next_month, 1, tzinfo=datetime.timezone.utc)
    return max(0, (next_run - now).total_seconds())


@background()
def generate_monthly_cycle():
    """Create a ContributionCycle for the current month, then schedule next month's run."""
    config = SystemConfig.objects.first()
    if config is None:
        # No config yet — reschedule and wait.
        generate_monthly_cycle(schedule=_seconds_until_first_of_next_month())
        return

    today = timezone.now().date()
    year, month = today.year, today.month

    extra_year, extra_month = _next_month(year, month)

    ContributionCycle.objects.get_or_create(
        year=year,
        month=month,
        defaults={
            'due_date':                 _clamped_date(year, month, config.cycle_due_day),
            'late_penalty_start_date':  _clamped_date(year, month, config.late_penalty_start_day),
            'extra_penalty_start_date': _clamped_date(extra_year, extra_month, config.extra_penalty_start_day),
            'status':                   ContributionCycle.Status.OPEN,
        },
    )

    generate_monthly_cycle(schedule=_seconds_until_first_of_next_month())
