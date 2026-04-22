import calendar
import datetime
import logging

from background_task import background
from django.db.models import Sum
from django.utils import timezone

from .models import ContributionCycle, Member, MemberContributionObligation, MemberShareAccount, Penalty, SystemConfig

logger = logging.getLogger(__name__)

CONTRIBUTION_SHARE_PRICE = 10_000


def _clamped_date(year, month, day):
    """Return date(year, month, day), clamping day to the last day of the month."""
    last_day = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, min(day, last_day))


def _next_month(year, month):
    """Return (year, month) for the month following the given one."""
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _month_sequence(start_year, start_month, count):
    months = []
    year, month = start_year, start_month
    for _ in range(count):
        months.append((year, month))
        year, month = _next_month(year, month)
    return months


def _first_of_next_month():
    """Return a timezone-aware datetime for midnight UTC on the 1st of next month."""
    now = timezone.now()
    next_year, next_month = _next_month(now.year, now.month)
    return datetime.datetime(next_year, next_month, 1, tzinfo=datetime.timezone.utc)


def _tomorrow():
    """Return a timezone-aware datetime for midnight UTC tomorrow."""
    tomorrow = timezone.now().date() + datetime.timedelta(days=1)
    return datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=datetime.timezone.utc)


def ensure_cycle(year, month, config):
    extra_year, extra_month = _next_month(year, month)
    cycle, created = ContributionCycle.objects.get_or_create(
        year=year,
        month=month,
        defaults={
            'due_date': _clamped_date(year, month, config.cycle_due_day),
            'late_penalty_start_date': _clamped_date(year, month, config.late_penalty_start_day),
            'extra_penalty_start_date': _clamped_date(extra_year, extra_month, config.extra_penalty_start_day),
            'status': ContributionCycle.Status.OPEN,
        },
    )
    return cycle, created


def ensure_cycle_share_price(cycle):
    if cycle.share_unit_value is not None:
        return cycle.share_unit_value

    from .ledger_service import get_capital_balance

    total_shares = (
        MemberShareAccount.objects
        .filter(member__status=Member.Status.ACTIVE)
        .aggregate(total=Sum('share_count'))['total']
    ) or 0
    capital = get_capital_balance()
    price = int(capital / total_shares) if total_shares > 0 else 10_000
    cycle.share_unit_value = price
    cycle.save(update_fields=['share_unit_value'])
    return price


def ensure_contribution_obligation(member, cycle, config):
    price = CONTRIBUTION_SHARE_PRICE
    share_count = member.share_account.share_count
    capital = share_count * price
    social = config.social_amount
    social_plus = config.social_plus_amount

    obligation, created = MemberContributionObligation.objects.get_or_create(
        member=member,
        contribution_cycle=cycle,
        defaults={
            'obligation_type': MemberContributionObligation.ObligationType.CONTRIBUTION,
            'share_count_snapshot': share_count,
            'share_unit_value_snapshot': price,
            'capital_amount_expected': capital,
            'social_amount_expected': social,
            'social_plus_amount_expected': social_plus,
            'total_amount_expected': capital + social + social_plus,
            'status': MemberContributionObligation.Status.EXPECTED,
        },
    )

    if not created and obligation.status != MemberContributionObligation.Status.CONFIRMED:
        fields_to_update = []
        if obligation.share_unit_value_snapshot != price:
            obligation.share_unit_value_snapshot = price
            fields_to_update.append('share_unit_value_snapshot')
        if obligation.share_count_snapshot != share_count:
            obligation.share_count_snapshot = share_count
            fields_to_update.append('share_count_snapshot')
        if obligation.capital_amount_expected != capital:
            obligation.capital_amount_expected = capital
            fields_to_update.append('capital_amount_expected')
        if obligation.social_amount_expected != social:
            obligation.social_amount_expected = social
            fields_to_update.append('social_amount_expected')
        if obligation.social_plus_amount_expected != social_plus:
            obligation.social_plus_amount_expected = social_plus
            fields_to_update.append('social_plus_amount_expected')
        total = capital + social + social_plus
        if obligation.total_amount_expected != total:
            obligation.total_amount_expected = total
            fields_to_update.append('total_amount_expected')
        if fields_to_update:
            fields_to_update.append('updated_at')
            obligation.save(update_fields=fields_to_update)

    return obligation, created


def _generate_obligations(cycle, config):
    """Ensure MemberContributionObligation exists for all active members."""
    members = (
        Member.objects
        .filter(status=Member.Status.ACTIVE)
        .select_related('share_account')
    )
    created_count = 0
    for member in members:
        try:
            member.share_account
        except Member.share_account.RelatedObjectDoesNotExist:
            logger.warning('Member %s has no share account — skipping obligation generation.', member.member_number)
            continue
        _, created = ensure_contribution_obligation(member, cycle, config)
        if created:
            created_count += 1
    logger.info('Ensured obligations for cycle %s; created %d new rows.', cycle, created_count)


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

    cycle, created = ensure_cycle(year, month, config)

    if created:
        ensure_cycle_share_price(cycle)
        _generate_obligations(cycle, config)

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
