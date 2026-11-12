import calendar
import datetime
from decimal import Decimal

from .models import (
    BankReconciliationSnapshot,
    FundAccount,
    HistoricalContributionEntry,
    IncomeEntry,
    Investment,
    InvestmentProfitEntry,
    LedgerEntry,
    Loan,
    LoanProduct,
    LoanRepayment,
    LoanRepaymentSchedule,
    Member,
    MemberShareAccount,
    OtherCharge,
    SocialActivityRecord,
    SourceReference,
    SystemConfig,
)


def _add_month(value):
    year, month = (value.year + 1, 1) if value.month == 12 else (value.year, value.month + 1)
    return datetime.date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def write_workbook(data, batch):
    SystemConfig.objects.get_or_create(
        pk=1,
        defaults={
            'cycle_due_day': 20,
            'late_penalty_start_day': 25,
            'extra_penalty_start_day': 5,
            'social_amount': 2000,
            'social_plus_amount': 3000,
            'late_penalty_amount': 0,
            'extra_penalty_amount': 0,
        },
    )
    funds = {}
    for code, name, allow_negative in [('CAPITAL', 'Capital', False), ('SOCIAL', 'Social', True), ('SOCIAL_PLUS', 'Social Plus', True)]:
        funds[code], _ = FundAccount.objects.get_or_create(
            code=code, defaults={'name': name, 'allow_negative': allow_negative, 'is_active': True}
        )

    source_references = []

    def source(entity, entity_type, ref, notes=''):
        source_references.append(SourceReference(
            import_batch=batch,
            entity_type=entity_type,
            entity_id=entity.id,
            sheet_name=ref['sheet'],
            cell_reference=ref['cell'],
            source_formula=ref.get('formula', ''),
            source_value=ref.get('value', ''),
            notes=' '.join(part for part in (ref['notes'], notes) if part),
        ))

    members = {}
    members_by_number = {}
    for row in data['members']:
        member = Member.objects.create(
            member_number=row['member_number'],
            first_name=row['first_name'],
            last_name=row['last_name'],
            status='active',
            join_date=row['join_date'],
        )
        MemberShareAccount.objects.create(member=member, share_count=row['share_count'], share_unit_value=10000)
        members_by_number[row['member_number']] = member
        members[row['first_name']] = member
        for alias in row['aliases']:
            members[alias] = member
        source(member, 'member', row['source'], f"Source name: {row['source_name']}; aliases: {', '.join(row['aliases']) or 'none'}.")

    fund_map = {'capital': ('CAPITAL', 'contribution_capital'), 'social': ('SOCIAL', 'contribution_social'), 'social_plus': ('SOCIAL_PLUS', 'contribution_social_plus')}
    contribution_entries = []
    contribution_ledgers = []
    for row in data['contributions']:
        member = members_by_number[row['member_number']]
        entry = HistoricalContributionEntry(
            import_batch=batch, member=member, year=row['year'], month=row['month'],
            fund_type=row['fund'], amount=row['amount'],
        )
        fund_code, entry_type = fund_map[row['fund']]
        contribution_ledgers.append(LedgerEntry(
            fund_account=funds[fund_code], member=member,
            entry_date=datetime.date(row['year'], row['month'], 1), date_precision='month',
            entry_type=entry_type, amount=row['amount'], direction='credit',
            reference_id=entry.id, reference_type='historical_contribution_entry',
            notes=f'Imported monthly workbook contribution from {data["source_name"]}.',
        ))
        contribution_entries.append(entry)
        source(entry, 'historical_contribution_entry', row['source'])
    HistoricalContributionEntry.objects.bulk_create(contribution_entries)
    LedgerEntry.objects.bulk_create(contribution_ledgers)

    products = {}
    active_products = sorted({
        (row['duration_months'], row['rate_percent'])
        for row in data['loans']['active']
    })
    for duration, rate in active_products:
        name = f'Workbook loan - {duration} months @ {rate}%'
        products[(duration, rate)], _ = LoanProduct.objects.get_or_create(
            name=name,
            defaults={'duration_months': duration, 'interest_rate_percent': rate, 'is_active': True, 'notes': 'Imported workbook loan product.'},
        )
    historical_product, _ = LoanProduct.objects.get_or_create(
        name='Historical opening balance',
        defaults={'duration_months': 1, 'interest_rate_percent': Decimal('0.00'), 'is_active': False, 'notes': 'Undated aggregate historical loan balances.'},
    )

    loan_ledgers = []
    repayment_schedules = []
    for row in data['loans']['active']:
        member = members[row['member_name']]
        issued = row['date']
        principal = row['principal']
        interest = row['interest']
        paid = row['paid']
        rate = row['rate_percent']
        product = products[(row['duration_months'], row['rate_percent'])]
        loan = Loan.objects.create(
            member=member, loan_product=product, principal_amount=principal,
            interest_rate_percent_snapshot=rate, duration_months_snapshot=row['duration_months'],
            total_repayment_amount=principal + interest,
            monthly_installment_amount=((principal + interest) / row['duration_months']).quantize(Decimal('0.01')),
            issued_date=issued, first_due_date=_add_month(issued), status='active',
            source_outstanding_amount=row['outstanding'], import_batch=batch,
            notes=f'Active loan imported from {data["source_name"]}.', created_by=None,
        )
        source(loan, 'loan', row['source'])
        due_date = _add_month(issued)
        for installment_number in range(1, row['duration_months'] + 1):
            amount_due = (
                loan.total_repayment_amount - loan.monthly_installment_amount * (row['duration_months'] - 1)
                if installment_number == row['duration_months']
                else loan.monthly_installment_amount
            )
            repayment_schedules.append(LoanRepaymentSchedule(
                loan=loan, installment_number=installment_number, due_date=due_date,
                amount_due=amount_due, status='pending',
            ))
            due_date = _add_month(due_date)
        loan_ledgers.append(LedgerEntry(
            fund_account=funds['CAPITAL'], member=member, entry_date=issued, date_precision='exact',
            entry_type='loan_disbursement', amount=principal, direction='debit',
            reference_id=loan.id, reference_type='loan', notes='Imported active loan.',
        ))
        if paid:
            repayment = LoanRepayment.objects.create(
                loan=loan, amount_paid=paid, paid_date=None, date_precision='unknown',
                payment_method='bank', notes='Undated aggregate repayment from workbook.', recorded_by=None,
            )
            source(repayment, 'loan_repayment', row['source'], 'Workbook provides an aggregate paid amount, not exact repayment dates.')
            loan_ledgers.append(LedgerEntry(
                fund_account=funds['CAPITAL'], member=member, entry_date=None, date_precision='unknown',
                entry_type='loan_repayment', amount=paid, direction='credit',
                reference_id=repayment.id, reference_type='loan_repayment', notes='Imported undated active-loan repayment aggregate.',
            ))

    for row in data['loans']['historical']:
        member = members[row['member_name']]
        principal, interest, paid = row['principal'], row['interest'], row['paid']
        total = principal + interest
        rate = (interest / principal * 100).quantize(Decimal('0.01')) if principal else Decimal('0.00')
        loan = Loan.objects.create(
            member=member, loan_product=historical_product, principal_amount=principal,
            interest_rate_percent_snapshot=rate, duration_months_snapshot=1,
            total_repayment_amount=total, monthly_installment_amount=total,
            issued_date=None, first_due_date=None, status='closed', is_opening_balance=True,
            opening_principal_amount=principal, opening_interest_amount=interest,
            opening_paid_amount=paid, import_batch=batch,
            notes='Historical opening-balance loan; exact issue and repayment dates are unknown.', created_by=None,
        )
        source(loan, 'loan', row['source'], 'Historical aggregate retained without fabricated issue date.')
        loan_ledgers.append(LedgerEntry(
            fund_account=funds['CAPITAL'], member=member, entry_date=None, date_precision='unknown',
            entry_type='loan_disbursement', amount=principal, direction='debit',
            reference_id=loan.id, reference_type='loan', notes='Historical opening loan principal.',
        ))
        if paid:
            repayment = LoanRepayment.objects.create(
                loan=loan, amount_paid=paid, paid_date=None, date_precision='unknown',
                payment_method='bank', notes='Historical aggregate repayment; exact dates unknown.', recorded_by=None,
            )
            source(repayment, 'loan_repayment', row['source'])
            loan_ledgers.append(LedgerEntry(
                fund_account=funds['CAPITAL'], member=member, entry_date=None, date_precision='unknown',
                entry_type='loan_repayment', amount=paid, direction='credit',
                reference_id=repayment.id, reference_type='loan_repayment', notes='Historical opening repayment aggregate.',
            ))
    LoanRepaymentSchedule.objects.bulk_create(repayment_schedules)
    LedgerEntry.objects.bulk_create(loan_ledgers)

    expense_ledgers = []
    for row in data['social_expenses']:
        record = SocialActivityRecord.objects.create(
            fund_account=funds[row['fund']], activity_date=row['date'], date_precision=row['date_precision'],
            category=row['category'], name=row['name'], description='Imported workbook expense.',
            amount=row['amount'], import_batch=batch, recorded_by=None,
        )
        source(record, 'social_activity_record', row['source'])
        expense_ledgers.append(LedgerEntry(
            fund_account=funds[row['fund']], member=None, entry_date=row['date'], date_precision=row['date_precision'],
            entry_type='social_expense' if row['fund'] == 'SOCIAL' else 'social_plus_expense',
            amount=row['amount'], direction='debit', reference_id=record.id,
            reference_type='social_activity_record', notes='Imported workbook expense.',
        ))
    LedgerEntry.objects.bulk_create(expense_ledgers)

    income_ledgers = []
    for row in data['income']:
        entry = IncomeEntry.objects.create(
            income_type=row['type'], amount=row['amount'], income_date=None, date_precision='unknown',
            description='Imported aggregate workbook income.', import_batch=batch, recorded_by=None,
        )
        source(entry, 'income_entry', row['source'])
        income_ledgers.append(LedgerEntry(
            fund_account=funds['CAPITAL'], member=None, entry_date=None, date_precision='unknown',
            entry_type=row['type'], amount=row['amount'], direction='credit',
            reference_id=entry.id, reference_type='income_entry', notes='Imported aggregate workbook income.',
        ))
    LedgerEntry.objects.bulk_create(income_ledgers)

    charge_ledgers = []
    for row in data['bank_charges']:
        charge = OtherCharge.objects.create(
            charge_type='bank_charge', amount=row['amount'], direction='debit',
            fund_account=funds['CAPITAL'], charge_date=None, date_precision='unknown',
            description=row['description'], import_batch=batch, recorded_by=None,
        )
        source(charge, 'other_charge', row['source'])
        charge_ledgers.append(LedgerEntry(
            fund_account=funds['CAPITAL'], member=None, entry_date=None, date_precision='unknown',
            entry_type='other_charge', amount=row['amount'], direction='debit',
            reference_id=charge.id, reference_type='other_charge', notes=row['description'],
        ))
    LedgerEntry.objects.bulk_create(charge_ledgers)

    investment_ledgers = []
    for row in data['investments']:
        investment = Investment.objects.create(
            name=row['name'], investment_type=row['type'], investment_date=row['date'],
            amount_invested=row['amount'], expected_interest_rate_percent=row['rate'],
            vesting_period_months=row['vesting_months'], status='active',
            description='Imported workbook investment.', import_batch=batch, created_by=None,
        )
        source(investment, 'investment', row['source'])
        investment_ledgers.append(LedgerEntry(
            fund_account=funds['CAPITAL'], member=None, entry_date=row['date'], date_precision='month',
            entry_type='investment_purchase', amount=row['amount'], direction='debit',
            reference_id=investment.id, reference_type='investment', notes='Imported workbook investment.',
        ))
        for profit_row in row['profits']:
            profit = InvestmentProfitEntry.objects.create(
                investment=investment, profit_date=profit_row['date'], amount=profit_row['amount'],
                is_net_coupon_income=True, description='Imported net coupon income.', recorded_by=None,
            )
            source(profit, 'investment_profit_entry', profit_row['source'])
            investment_ledgers.append(LedgerEntry(
                fund_account=funds['CAPITAL'], member=None, entry_date=profit_row['date'],
                date_precision='exact' if profit_row['date'] else 'unknown',
                entry_type='investment_profit', amount=profit_row['amount'], direction='credit',
                reference_id=profit.id, reference_type='investment_profit_entry', notes='Imported net coupon income.',
            ))
    LedgerEntry.objects.bulk_create(investment_ledgers)

    reconciliation = data['reconciliation']
    snapshot = BankReconciliationSnapshot.objects.create(
        import_batch=batch, as_of_date=reconciliation['as_of_date'],
        calculated_cash_balance=reconciliation['calculated_cash_balance'],
        stated_bank_balance=reconciliation['stated_bank_balance'],
        variance=reconciliation['variance'],
        expected_total_assets=reconciliation['expected_total_assets'],
        notes='Bank balance date unverified. Variance retained as reported.',
    )
    source(snapshot, 'bank_reconciliation_snapshot', reconciliation['source'])
    SourceReference.objects.bulk_create(source_references)
