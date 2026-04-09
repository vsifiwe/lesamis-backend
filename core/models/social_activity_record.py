import uuid

from django.db import models


class SocialActivityRecord(models.Model):

    class Category(models.TextChoices):
        EVENT   = 'event',   'Event'
        SUPPORT = 'support', 'Support'
        VISIT   = 'visit',   'Visit'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund_account = models.ForeignKey('FundAccount', on_delete=models.PROTECT, related_name='social_activity_records')
    activity_date = models.DateField()
    category     = models.CharField(max_length=20, choices=Category.choices)
    name         = models.CharField(max_length=255)
    description  = models.TextField(blank=True, default='')
    amount       = models.DecimalField(max_digits=12, decimal_places=2)
    recorded_by  = models.ForeignKey('User', on_delete=models.PROTECT, related_name='recorded_social_activities')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-activity_date', '-created_at']

    def __str__(self):
        return f'{self.name} ({self.get_category_display()}) — {self.amount}'
