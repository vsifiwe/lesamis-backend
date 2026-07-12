import uuid

from django.db import models


class HistoricalContributionEntry(models.Model):
    class FundType(models.TextChoices):
        CAPITAL = 'capital', 'Capital'
        SOCIAL = 'social', 'Social'
        SOCIAL_PLUS = 'social_plus', 'Social Plus'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    import_batch = models.ForeignKey('ImportBatch', on_delete=models.CASCADE, related_name='historical_contributions')
    member = models.ForeignKey('Member', on_delete=models.PROTECT, related_name='historical_contributions')
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    fund_type = models.CharField(max_length=20, choices=FundType.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['year', 'month', 'member__member_number', 'fund_type']
        constraints = [
            models.UniqueConstraint(
                fields=['import_batch', 'member', 'year', 'month', 'fund_type'],
                name='unique_import_member_month_fund_contribution',
            ),
        ]

    def __str__(self):
        return f'{self.member} {self.year}-{self.month:02d} {self.fund_type}: {self.amount}'
