import uuid

from django.db import models

from .contribution_receipt import ContributionReceipt
from .member_contribution_obligation import MemberContributionObligation


class ContributionReceiptItem(models.Model):

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt         = models.ForeignKey(ContributionReceipt, on_delete=models.CASCADE, related_name='items')
    obligation      = models.ForeignKey(MemberContributionObligation, on_delete=models.PROTECT, related_name='receipt_items')
    amount_applied  = models.DecimalField(max_digits=10, decimal_places=2)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Contribution Receipt Item'
        verbose_name_plural = 'Contribution Receipt Items'
        ordering            = ['receipt', 'created_at']
        constraints         = [
            models.UniqueConstraint(
                fields=['receipt', 'obligation'],
                name='unique_receipt_item_receipt_obligation',
            ),
        ]

    def __str__(self):
        return f'{self.receipt} → {self.obligation.member} — {self.amount_applied}'
