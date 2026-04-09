import uuid

from django.db import models


class Loan(models.Model):

    class Status(models.TextChoices):
        ACTIVE    = 'active',    'Active'
        CLOSED    = 'closed',    'Closed'
        DEFAULTED = 'defaulted', 'Defaulted'
        CANCELLED = 'cancelled', 'Cancelled'

    id                              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member                          = models.ForeignKey('Member', on_delete=models.PROTECT, related_name='loans')
    loan_product                    = models.ForeignKey('LoanProduct', on_delete=models.PROTECT, related_name='loans')
    principal_amount                = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate_percent_snapshot  = models.DecimalField(max_digits=5, decimal_places=2)
    duration_months_snapshot        = models.PositiveSmallIntegerField()
    total_repayment_amount          = models.DecimalField(max_digits=12, decimal_places=2)
    monthly_installment_amount      = models.DecimalField(max_digits=12, decimal_places=2)
    issued_date                     = models.DateField()
    first_due_date                  = models.DateField()
    status                          = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    notes                           = models.TextField(blank=True, default='')
    created_by                      = models.ForeignKey('User', on_delete=models.PROTECT, related_name='created_loans')
    created_at                      = models.DateTimeField(auto_now_add=True)
    updated_at                      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Loan {self.id} — {self.member} ({self.status})'
