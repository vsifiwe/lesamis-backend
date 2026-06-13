import uuid

from django.db import models


class SocialActivityRecord(models.Model):

    class Category(models.TextChoices):
        EVENT   = 'event',   'Event'
        SUPPORT = 'support', 'Support'
        VISIT   = 'visit',   'Visit'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund_account = models.ForeignKey('FundAccount', on_delete=models.PROTECT, related_name='social_activity_records')
    activity_date = models.DateField(null=True, blank=True)
    date_precision = models.CharField(max_length=10, choices=[
        ('exact', 'Exact'), ('month', 'Month'), ('period', 'Period'), ('unknown', 'Unknown'),
    ], default='exact')
    import_batch = models.ForeignKey('ImportBatch', on_delete=models.SET_NULL, null=True, blank=True, related_name='social_activity_records')
    category     = models.CharField(max_length=20, choices=Category.choices)
    name         = models.CharField(max_length=255)
    description  = models.TextField(blank=True, default='')
    amount       = models.DecimalField(max_digits=12, decimal_places=2)
    recorded_by  = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_social_activities')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-activity_date', '-created_at']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(date_precision='unknown', activity_date__isnull=True)
                    | models.Q(date_precision__in=['exact', 'month', 'period'], activity_date__isnull=False)
                ),
                name='social_activity_date_matches_precision',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_category_display()}) — {self.amount}'
