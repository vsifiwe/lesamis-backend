import uuid

from django.db import models


class ContributionCycle(models.Model):

    class Status(models.TextChoices):
        OPEN   = 'open',   'Open'
        CLOSED = 'closed', 'Closed'

    id                       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    year                     = models.PositiveSmallIntegerField()
    month                    = models.PositiveSmallIntegerField()
    due_date                 = models.DateField()
    late_penalty_start_date  = models.DateField()
    extra_penalty_start_date = models.DateField()
    status                   = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    share_unit_value         = models.PositiveIntegerField(null=True, blank=True)
    created_at               = models.DateTimeField(auto_now_add=True)
    updated_at               = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Contribution Cycle'
        verbose_name_plural = 'Contribution Cycles'
        ordering            = ['-year', '-month']
        constraints         = [
            models.UniqueConstraint(fields=['year', 'month'], name='unique_cycle_year_month'),
        ]

    def __str__(self):
        return f'{self.year}-{self.month:02d} ({self.status})'
