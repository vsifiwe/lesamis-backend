import uuid

from django.db import models


class LoanRepayment(models.Model):

    class PaymentMethod(models.TextChoices):
        BANK         = 'bank',         'Bank'
        CASH         = 'cash',         'Cash'
        MOBILE_MONEY = 'mobile_money', 'Mobile Money'

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan           = models.ForeignKey('Loan', on_delete=models.PROTECT, related_name='repayments')
    amount_paid    = models.DecimalField(max_digits=12, decimal_places=2)
    paid_date      = models.DateField(null=True, blank=True)
    date_precision = models.CharField(max_length=10, choices=[
        ('exact', 'Exact'), ('month', 'Month'), ('period', 'Period'), ('unknown', 'Unknown'),
    ], default='exact')
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    notes          = models.TextField(blank=True, default='')
    recorded_by    = models.ForeignKey('User', on_delete=models.PROTECT, null=True, blank=True, related_name='recorded_repayments')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-paid_date', '-created_at']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(date_precision='unknown', paid_date__isnull=True)
                    | models.Q(date_precision__in=['exact', 'month', 'period'], paid_date__isnull=False)
                ),
                name='repayment_date_matches_precision',
            ),
        ]

    def __str__(self):
        return f'Repayment {self.id} — Loan {self.loan_id} ({self.amount_paid})'
