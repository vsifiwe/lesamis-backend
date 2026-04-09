import uuid

from django.db import models


class FundAccount(models.Model):

    class Code(models.TextChoices):
        CAPITAL     = 'CAPITAL',     'Capital'
        SOCIAL      = 'SOCIAL',      'Social'
        SOCIAL_PLUS = 'SOCIAL_PLUS', 'Social Plus'

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code           = models.CharField(max_length=20, choices=Code.choices, unique=True)
    name           = models.CharField(max_length=100)
    allow_negative = models.BooleanField(default=True)
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Fund Account'
        verbose_name_plural = 'Fund Accounts'
        ordering            = ['code']

    def __str__(self):
        return f'{self.name} ({self.code})'
