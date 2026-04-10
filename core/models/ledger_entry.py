import uuid

from django.db import models


class LedgerEntry(models.Model):

    class EntryType(models.TextChoices):
        CONTRIBUTION_CAPITAL     = 'contribution_capital',     'Contribution — Capital'
        CONTRIBUTION_SOCIAL      = 'contribution_social',      'Contribution — Social'
        CONTRIBUTION_SOCIAL_PLUS = 'contribution_social_plus', 'Contribution — Social+'
        LATE_PENALTY             = 'late_penalty',             'Late Penalty'
        OTHER_CHARGE             = 'other_charge',             'Other Charge'
        LOAN_DISBURSEMENT        = 'loan_disbursement',        'Loan Disbursement'
        LOAN_REPAYMENT           = 'loan_repayment',           'Loan Repayment'
        INVESTMENT_PURCHASE      = 'investment_purchase',      'Investment Purchase'
        INVESTMENT_PROFIT        = 'investment_profit',        'Investment Profit'
        SOCIAL_EXPENSE           = 'social_expense',           'Social Expense'
        SOCIAL_PLUS_EXPENSE      = 'social_plus_expense',      'Social+ Expense'
        SHARE_PURCHASE           = 'share_purchase',           'Share Purchase'

    class Direction(models.TextChoices):
        DEBIT  = 'debit',  'Debit'
        CREDIT = 'credit', 'Credit'

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund_account   = models.ForeignKey('FundAccount', on_delete=models.PROTECT, related_name='ledger_entries')
    member         = models.ForeignKey('Member', on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    entry_date     = models.DateField()
    entry_type     = models.CharField(max_length=30, choices=EntryType.choices)
    amount         = models.DecimalField(max_digits=14, decimal_places=2)
    direction      = models.CharField(max_length=10, choices=Direction.choices)
    reference_id   = models.UUIDField(null=True, blank=True)
    reference_type = models.CharField(max_length=50, blank=True, default='')
    notes          = models.TextField(blank=True, default='')
    recorded_by    = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-entry_date', '-created_at']

    def __str__(self):
        return f'{self.get_entry_type_display()} {self.direction} {self.amount} ({self.entry_date})'
