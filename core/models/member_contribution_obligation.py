import uuid

from django.db import models

from .contribution_cycle import ContributionCycle
from .member import Member


class MemberContributionObligation(models.Model):

    class Status(models.TextChoices):
        EXPECTED         = 'expected',         'Expected'
        PARTIALLY_PAID   = 'partially_paid',   'Partially Paid'
        PAID_UNCONFIRMED = 'paid_unconfirmed', 'Paid (Unconfirmed)'
        CONFIRMED        = 'confirmed',        'Confirmed'
        UNPAID           = 'unpaid',           'Unpaid'

    id                         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member                     = models.ForeignKey(Member, on_delete=models.PROTECT, related_name='obligations')
    contribution_cycle         = models.ForeignKey(ContributionCycle, on_delete=models.PROTECT, related_name='obligations')
    share_count_snapshot       = models.PositiveIntegerField()
    share_unit_value_snapshot  = models.PositiveIntegerField()
    capital_amount_expected    = models.PositiveIntegerField()
    social_amount_expected     = models.PositiveIntegerField(default=2000)
    social_plus_amount_expected = models.PositiveIntegerField(default=3000)
    total_amount_expected      = models.PositiveIntegerField()
    status                     = models.CharField(max_length=20, choices=Status.choices, default=Status.EXPECTED)
    created_at                 = models.DateTimeField(auto_now_add=True)
    updated_at                 = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Member Contribution Obligation'
        verbose_name_plural = 'Member Contribution Obligations'
        ordering            = ['-contribution_cycle__year', '-contribution_cycle__month']
        constraints         = [
            models.UniqueConstraint(
                fields=['member', 'contribution_cycle'],
                name='unique_obligation_member_cycle',
            ),
        ]

    def __str__(self):
        return f'{self.member} — {self.contribution_cycle} — {self.status}'
