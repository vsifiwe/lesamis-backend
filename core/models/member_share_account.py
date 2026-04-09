import uuid

from django.db import models

from .member import Member


class MemberShareAccount(models.Model):

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member           = models.OneToOneField(Member, on_delete=models.CASCADE, related_name='share_account')
    share_count      = models.PositiveIntegerField(default=0)
    share_unit_value = models.PositiveIntegerField(default=10000)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Member Share Account'
        verbose_name_plural = 'Member Share Accounts'

    def __str__(self):
        return f'{self.member} — {self.share_count} shares'

    @property
    def total_value(self):
        return self.share_count * self.share_unit_value
