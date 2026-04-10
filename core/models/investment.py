import uuid

from django.db import models


class Investment(models.Model):

    class InvestmentType(models.TextChoices):
        SHARES  = 'shares',  'Shares'
        LAND    = 'land',    'Land'
        BOND    = 'bond',    'Bond'
        OTHER   = 'other',   'Other'

    class Status(models.TextChoices):
        ACTIVE        = 'active',        'Active'
        EXITED        = 'exited',        'Exited'
        PARTIAL_EXIT  = 'partial_exit',  'Partial Exit'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name            = models.CharField(max_length=255)
    investment_type = models.CharField(max_length=20, choices=InvestmentType.choices)
    investment_date = models.DateField()
    amount_invested = models.DecimalField(max_digits=14, decimal_places=2)
    expected_interest_rate_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    vesting_period_months = models.PositiveIntegerField(null=True, blank=True)
    status          = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    description     = models.TextField(blank=True, default='')
    created_by      = models.ForeignKey('User', on_delete=models.PROTECT, related_name='created_investments')
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-investment_date', '-created_at']

    def __str__(self):
        return f'{self.name} ({self.get_investment_type_display()}) — {self.status}'
