import uuid

from django.db import models
from django.utils import timezone


class Member(models.Model):

    class Status(models.TextChoices):
        ACTIVE   = 'active',   'Active'
        INACTIVE = 'inactive', 'Inactive'
        EXITED   = 'exited',   'Exited'

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member_number = models.CharField(max_length=20, unique=True, blank=True)
    first_name    = models.CharField(max_length=150)
    last_name     = models.CharField(max_length=150)
    phone         = models.CharField(max_length=30, blank=True)
    email         = models.EmailField(blank=True)
    status        = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    join_date     = models.DateField(default=timezone.now)
    exit_date     = models.DateField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Member'
        verbose_name_plural = 'Members'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.member_number} — {self.first_name} {self.last_name}'

    def save(self, *args, **kwargs):
        if not self.member_number:
            n = Member.objects.count() + 1
            self.member_number = f'MBR-{n:04d}'
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()
