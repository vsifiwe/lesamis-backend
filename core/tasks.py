import calendar
import datetime
import logging

from background_task import background
from django.utils import timezone

from .models import ContributionCycle, Member, MemberContributionObligation, SystemConfig

logger = logging.getLogger(__name__)


def _clamped_date(year, month, day):
    """Return date(year, month, day), clamping day to the last day of the month."""
    last_day = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, min(day, last_day))


def _next_month(year, month):
    """Return (year, month) for the month following the given one."""
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _first_of_next_month():
    """Return a timezone-aware datetime for midnight UTC on the 1st of next month."""
    now = timezone.now()
    next_year, next_month = _next_month(now.year, now.month)
    return datetime.datetime(next_year, next_month, 1, tzinfo=datetime.timezone.utc)


def _generate_obligations(cycle, config):
    """Bulk-create MemberContributionObligation for all active members."""
    members = (
        Member.objects
        .filter(status=Member.Status.ACTIVE)
        .select_related('share_account')
    )

    obligations = []
    for member in members:
        try:
            share_account = member.share_account
        except Member.share_account.RelatedObjectDoesNotExist:
            logger.warning('Member %s has no share account — skipping obligation generation.', member.member_number)
            continue

        share_count      = share_account.share_count
        share_unit_value = share_account.share_unit_value
        capital          = share_count * share_unit_value
        social           = config.social_amount
        social_plus      = config.social_plus_amount

        obligations.append(MemberContributionObligation(
            member=member,
            contribution_cycle=cycle,
            share_count_snapshot=share_count,
            share_unit_value_snapshot=share_unit_value,
            capital_amount_expected=capital,
            social_amount_expected=social,
            social_plus_amount_expected=social_plus,
            total_amount_expected=capital + social + social_plus,
        ))

    MemberContributionObligation.objects.bulk_create(obligations)
    logger.info('Generated %d obligations for cycle %s.', len(obligations), cycle)


@background()
def generate_monthly_cycle():
    """Create a ContributionCycle for the current month, generate obligations, then schedule next month's run."""
    config = SystemConfig.objects.first()
    if config is None:
        logger.warning('No SystemConfig found — skipping cycle generation, will retry next month.')
        generate_monthly_cycle(schedule=_first_of_next_month())
        return

    today = timezone.now().date()
    year, month = today.year, today.month

    extra_year, extra_month = _next_month(year, month)

    cycle, created = ContributionCycle.objects.get_or_create(
        year=year,
        month=month,
        defaults={
            'due_date':                 _clamped_date(year, month, config.cycle_due_day),
            'late_penalty_start_date':  _clamped_date(year, month, config.late_penalty_start_day),
            'extra_penalty_start_date': _clamped_date(extra_year, extra_month, config.extra_penalty_start_day),
            'status':                   ContributionCycle.Status.OPEN,
        },
    )

    if created:
        _generate_obligations(cycle, config)

    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    ContributionCycle.objects.filter(
        year=prev_year,
        month=prev_month,
        status=ContributionCycle.Status.OPEN,
    ).update(status=ContributionCycle.Status.CLOSED)

    generate_monthly_cycle(schedule=_first_of_next_month())
