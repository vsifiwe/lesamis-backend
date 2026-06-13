import uuid

from django.db import models


class BankReconciliationSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    import_batch = models.OneToOneField('ImportBatch', on_delete=models.CASCADE, related_name='bank_reconciliation')
    as_of_date = models.DateField()
    calculated_cash_balance = models.DecimalField(max_digits=14, decimal_places=2)
    stated_bank_balance = models.DecimalField(max_digits=14, decimal_places=2)
    variance = models.DecimalField(max_digits=14, decimal_places=2)
    expected_total_assets = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-as_of_date']

    def __str__(self):
        return f'Bank reconciliation {self.as_of_date}: variance {self.variance}'
