from django.db import models


class SystemConfig(models.Model):

    id                        = models.IntegerField(primary_key=True, default=1, editable=False)
    cycle_due_day             = models.PositiveSmallIntegerField()
    late_penalty_start_day    = models.PositiveSmallIntegerField()
    extra_penalty_start_day   = models.PositiveSmallIntegerField()
    social_amount             = models.PositiveIntegerField(default=2000)
    social_plus_amount        = models.PositiveIntegerField(default=3000)
    created_at                = models.DateTimeField(auto_now_add=True)
    updated_at                = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'System Config'
        verbose_name_plural = 'System Config'

    def __str__(self):
        return 'System Configuration'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
