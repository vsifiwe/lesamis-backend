import uuid

from django.db import models


class LoanRepaymentSchedule(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        WAIVED = 'waived', 'Waived'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan = models.ForeignKey('Loan', on_delete=models.CASCADE, related_name='repayment_schedule')
    installment_number = models.PositiveSmallIntegerField()
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['loan', 'installment_number']
        constraints = [
            models.UniqueConstraint(
                fields=['loan', 'installment_number'],
                name='unique_loan_installment_number',
            ),
        ]

    def __str__(self):
        return f'{self.loan_id} installment {self.installment_number}'
