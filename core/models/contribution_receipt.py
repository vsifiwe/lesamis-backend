import uuid

from django.db import models

from .user import User


class ContributionReceipt(models.Model):

    class PaymentMethod(models.TextChoices):
        CASH         = 'cash',         'Cash'
        BANK         = 'bank',         'Bank'
        MOBILE_MONEY = 'mobile_money', 'Mobile Money'

    class Status(models.TextChoices):
        PENDING_CONFIRMATION = 'pending_confirmation', 'Pending Confirmation'
        CONFIRMED            = 'confirmed',            'Confirmed'
        REJECTED             = 'rejected',             'Rejected'

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    amount_received  = models.DecimalField(max_digits=10, decimal_places=2)
    received_date    = models.DateField()
    payment_method   = models.CharField(max_length=20, choices=PaymentMethod.choices)
    status           = models.CharField(max_length=25, choices=Status.choices, default=Status.PENDING_CONFIRMATION)
    confirmed_by     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_receipts')
    confirmed_at     = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    notes            = models.TextField(blank=True)
    created_by       = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_receipts')
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Contribution Receipt'
        verbose_name_plural = 'Contribution Receipts'
        ordering            = ['-received_date', '-created_at']

    def __str__(self):
        return f'Receipt {str(self.id)[:8]} — {self.received_date} — {self.status}'
