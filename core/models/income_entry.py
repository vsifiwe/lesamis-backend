import uuid

from django.db import models


class IncomeEntry(models.Model):
    class IncomeType(models.TextChoices):
        BANK_INTEREST = 'bank_interest', 'Bank Interest'
        JOINING_FEE = 'joining_fee', 'Joining Fee'
        CONTRIBUTION_PENALTY = 'contribution_penalty', 'Collected Contribution Penalty'
        LOAN_EXIT_PENALTY = 'loan_exit_penalty', 'Collected Loan/Exit Penalty'
        CORRECTION = 'correction', 'Correction'

    class DatePrecision(models.TextChoices):
        EXACT = 'exact', 'Exact'
        MONTH = 'month', 'Month'
        PERIOD = 'period', 'Period'
        UNKNOWN = 'unknown', 'Unknown'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    income_type = models.CharField(max_length=30, choices=IncomeType.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    income_date = models.DateField(null=True, blank=True)
    date_precision = models.CharField(max_length=10, choices=DatePrecision.choices, default=DatePrecision.EXACT)
    description = models.TextField(blank=True, default='')
    import_batch = models.ForeignKey('ImportBatch', on_delete=models.SET_NULL, null=True, blank=True, related_name='income_entries')
    recorded_by = models.ForeignKey('User', on_delete=models.PROTECT, null=True, blank=True, related_name='recorded_income_entries')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-income_date', '-created_at']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(date_precision='unknown', income_date__isnull=True)
                    | models.Q(date_precision__in=['exact', 'month', 'period'], income_date__isnull=False)
                ),
                name='income_date_matches_precision',
            ),
        ]

    def __str__(self):
        return f'{self.get_income_type_display()} {self.amount}'
