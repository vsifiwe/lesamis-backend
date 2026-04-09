import uuid

from django.db import models


class InvestmentProfitEntry(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investment  = models.ForeignKey('Investment', on_delete=models.PROTECT, related_name='profit_entries')
    profit_date = models.DateField()
    amount      = models.DecimalField(max_digits=14, decimal_places=2)
    description = models.TextField(blank=True, default='')
    recorded_by = models.ForeignKey('User', on_delete=models.PROTECT, related_name='recorded_profit_entries')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-profit_date', '-created_at']

    def __str__(self):
        return f'Profit {self.amount} from {self.investment} on {self.profit_date}'
