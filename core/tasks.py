import calendar
import datetime
import logging

from background_task import background
from django.utils import timezone

from .models import ContributionCycle, Member, MemberContributionObligation, Penalty, SystemConfig

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


def _tomorrow():
    """Return a timezone-aware datetime for midnight UTC tomorrow."""
    tomorrow = timezone.now().date() + datetime.timedelta(days=1)
    return datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=datetime.timezone.utc)


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


def _apply_penalties(cycle, penalty_type, amount_per_share):
    """Bulk-create penalties for unconfirmed obligations in a cycle that don't yet have this penalty type."""
    already_penalised = Penalty.objects.filter(
        contribution_obligation__contribution_cycle=cycle,
        penalty_type=penalty_type,
    ).values_list('contribution_obligation_id', flat=True)

    obligations = (
        MemberContributionObligation.objects
        .filter(contribution_cycle=cycle)
        .exclude(status=MemberContributionObligation.Status.CONFIRMED)
        .exclude(id__in=already_penalised)
    )

    penalties = []
    updated_obligations = []
    for obligation in obligations:
        amount = amount_per_share * obligation.share_count_snapshot
        penalties.append(Penalty(
            contribution_obligation=obligation,
            penalty_type=penalty_type,
            amount=amount,
            auto_generated=True,
            reason=f'Auto-generated {penalty_type} for cycle {cycle}.',
        ))
        obligation.total_amount_expected += amount
        updated_obligations.append(obligation)

    Penalty.objects.bulk_create(penalties)
    MemberContributionObligation.objects.bulk_update(updated_obligations, ['total_amount_expected'])
    logger.info('Generated %d %s penalties for cycle %s.', len(penalties), penalty_type, cycle)


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


@background()
def generate_penalties():
    """Generate late and extra-late penalties for all unconfirmed obligations in open cycles."""
    config = SystemConfig.objects.first()
    if config is None:
        logger.warning('No SystemConfig found — skipping penalty generation, will retry tomorrow.')
        generate_penalties(schedule=_tomorrow())
        return

    today = timezone.now().date()

    for cycle in ContributionCycle.objects.filter(status=ContributionCycle.Status.OPEN):
        if today >= cycle.late_penalty_start_date and config.late_penalty_amount > 0:
            _apply_penalties(cycle, Penalty.PenaltyType.LATE_PENALTY, config.late_penalty_amount)
        if today >= cycle.extra_penalty_start_date and config.extra_penalty_amount > 0:
            _apply_penalties(cycle, Penalty.PenaltyType.EXTRA_LATE_PENALTY, config.extra_penalty_amount)

    generate_penalties(schedule=_tomorrow())
