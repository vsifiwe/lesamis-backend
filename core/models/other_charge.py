import uuid

from django.db import models


class OtherCharge(models.Model):

    class ChargeType(models.TextChoices):
        BANK_CHARGE = 'bank_charge',  'Bank Charge'
        ADJUSTMENT  = 'adjustment',   'Adjustment'
        CORRECTION  = 'correction',   'Correction'

    class Direction(models.TextChoices):
        DEBIT  = 'debit',  'Debit'
        CREDIT = 'credit', 'Credit'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    charge_type = models.CharField(max_length=20, choices=ChargeType.choices)
    amount      = models.DecimalField(max_digits=12, decimal_places=2)
    direction   = models.CharField(max_length=10, choices=Direction.choices)
    fund_account = models.ForeignKey('FundAccount', on_delete=models.PROTECT, related_name='other_charges')
    charge_date  = models.DateField(null=True, blank=True)
    date_precision = models.CharField(max_length=10, choices=[
        ('exact', 'Exact'), ('month', 'Month'), ('period', 'Period'), ('unknown', 'Unknown'),
    ], default='exact')
    import_batch = models.ForeignKey('ImportBatch', on_delete=models.SET_NULL, null=True, blank=True, related_name='other_charges')
    description  = models.TextField()
    recorded_by  = models.ForeignKey('User', on_delete=models.PROTECT, null=True, blank=True, related_name='recorded_charges')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-charge_date', '-created_at']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(date_precision='unknown', charge_date__isnull=True)
                    | models.Q(date_precision__in=['exact', 'month', 'period'], charge_date__isnull=False)
                ),
                name='other_charge_date_matches_precision',
            ),
        ]

    def __str__(self):
        return f'{self.get_charge_type_display()} — {self.direction} {self.amount} ({self.charge_date})'
