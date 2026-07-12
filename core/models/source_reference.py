import uuid

from django.db import models


class SourceReference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    import_batch = models.ForeignKey('ImportBatch', on_delete=models.CASCADE, related_name='source_references')
    entity_type = models.CharField(max_length=80)
    entity_id = models.UUIDField()
    sheet_name = models.CharField(max_length=255)
    cell_reference = models.CharField(max_length=100)
    source_formula = models.TextField(blank=True, default='')
    source_value = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['entity_type', 'sheet_name', 'cell_reference']
        constraints = [
            models.UniqueConstraint(
                fields=['import_batch', 'entity_type', 'entity_id', 'sheet_name', 'cell_reference'],
                name='unique_import_entity_source_reference',
            ),
        ]

    def __str__(self):
        return f'{self.entity_type}:{self.entity_id} from {self.sheet_name}!{self.cell_reference}'
