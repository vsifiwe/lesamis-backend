import uuid

from django.db import models


class LoanProduct(models.Model):
    id                    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name                  = models.CharField(max_length=255, unique=True)
    duration_months       = models.PositiveSmallIntegerField()
    interest_rate_percent = models.DecimalField(max_digits=5, decimal_places=2)
    is_active             = models.BooleanField(default=True)
    notes                 = models.TextField(blank=True, default='')
    created_at            = models.DateTimeField(auto_now_add=True)
    updated_at            = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.duration_months}m @ {self.interest_rate_percent}%)'
