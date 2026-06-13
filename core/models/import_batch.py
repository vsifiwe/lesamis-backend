import uuid

from django.db import models


class ImportBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_name = models.CharField(max_length=255)
    source_sha256 = models.CharField(max_length=64, unique=True)
    fixture_version = models.PositiveIntegerField()
    declared_summary_date = models.DateField(null=True, blank=True)
    latest_transaction_date = models.DateField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-imported_at']

    def __str__(self):
        return f'{self.source_name} v{self.fixture_version}'
