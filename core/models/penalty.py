import uuid

from django.db import models

from .contribution_receipt import ContributionReceipt
from .member_contribution_obligation import MemberContributionObligation
from .user import User


class Penalty(models.Model):

    class PenaltyType(models.TextChoices):
        LATE_PENALTY       = 'late_penalty',       'Late Penalty'
        EXTRA_LATE_PENALTY = 'extra_late_penalty', 'Extra Late Penalty'
        MANUAL             = 'manual',             'Manual'

    id                      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contribution_obligation = models.ForeignKey(MemberContributionObligation, on_delete=models.PROTECT, related_name='penalties')
    receipt                 = models.ForeignKey(ContributionReceipt, on_delete=models.SET_NULL, null=True, blank=True, related_name='penalties')
    penalty_type            = models.CharField(max_length=20, choices=PenaltyType.choices)
    amount                  = models.DecimalField(max_digits=10, decimal_places=2)
    reason                  = models.TextField(blank=True)
    auto_generated          = models.BooleanField(default=False)
    waived                  = models.BooleanField(default=False)
    waived_by               = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='waived_penalties')
    waived_at               = models.DateTimeField(null=True, blank=True)
    created_at              = models.DateTimeField(auto_now_add=True)
    updated_at              = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Penalty'
        verbose_name_plural = 'Penalties'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.penalty_type} — {self.contribution_obligation} — {self.amount}'
