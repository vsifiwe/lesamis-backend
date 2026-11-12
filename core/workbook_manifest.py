import json
import os
import tempfile
from collections import Counter
from decimal import Decimal
from pathlib import Path

from rest_framework import serializers


FIXTURE_VERSION = 2
CONTRIBUTION_FUNDS = ('capital', 'social', 'social_plus')
EXPENSE_FUNDS = ('SOCIAL', 'SOCIAL_PLUS')
INCOME_TYPES = ('bank_interest', 'joining_fee', 'contribution_penalty', 'loan_exit_penalty')


def write_private_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n'
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            output.write(payload)
            output.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


class AmountField(serializers.DecimalField):
    def __init__(self, max_digits=14, **kwargs):
        super().__init__(max_digits=max_digits, decimal_places=2, **kwargs)


class SourceSerializer(serializers.Serializer):
    sheet = serializers.CharField(max_length=255)
    cell = serializers.CharField(max_length=100)
    formula = serializers.CharField(allow_blank=True, trim_whitespace=False)
    value = serializers.CharField(allow_blank=True, trim_whitespace=False)
    notes = serializers.CharField(allow_blank=True)


class SourcedRow(serializers.Serializer):
    source = SourceSerializer()


class MemberRow(SourcedRow):
    member_number = serializers.CharField(max_length=20)
    source_name = serializers.CharField(max_length=150)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, allow_blank=True)
    aliases = serializers.ListField(child=serializers.CharField(max_length=150))
    join_date = serializers.DateField()
    share_count = serializers.IntegerField(min_value=0, max_value=2147483647)


class ContributionRow(SourcedRow):
    member_number = serializers.CharField(max_length=20)
    year = serializers.IntegerField(min_value=1, max_value=9999)
    month = serializers.IntegerField(min_value=1, max_value=12)
    fund = serializers.ChoiceField(CONTRIBUTION_FUNDS)
    amount = AmountField()


class HistoricalLoanRow(SourcedRow):
    member_name = serializers.CharField(max_length=150)
    principal = AmountField(max_digits=12, min_value=0)
    interest = AmountField(max_digits=12)
    paid = AmountField()


class ActiveLoanRow(HistoricalLoanRow):
    principal = AmountField(max_digits=12, min_value=Decimal('0.01'))
    paid = AmountField(min_value=0)
    outstanding = AmountField()
    duration_months = serializers.IntegerField(min_value=1, max_value=32767)
    rate_percent = AmountField(max_digits=5, min_value=0)
    date = serializers.DateField()
    maturity_date = serializers.DateField(allow_null=True)

    def validate(self, row):
        if row['principal'] + row['interest'] - row['paid'] != row['outstanding']:
            raise serializers.ValidationError('Principal plus interest less paid must equal outstanding.')
        return row


class LoanRows(serializers.Serializer):
    active = ActiveLoanRow(many=True)
    historical = HistoricalLoanRow(many=True)


class ExpenseRow(SourcedRow):
    fund = serializers.ChoiceField(EXPENSE_FUNDS)
    date = serializers.DateField(allow_null=True)
    date_precision = serializers.ChoiceField(('exact', 'unknown'))
    category = serializers.ChoiceField(('support', 'event'))
    name = serializers.CharField(max_length=255)
    amount = AmountField()

    def validate(self, row):
        if (row['date'] is None) != (row['date_precision'] == 'unknown'):
            raise serializers.ValidationError('Date must match its precision.')
        return row


class IncomeRow(SourcedRow):
    type = serializers.ChoiceField(INCOME_TYPES)
    amount = AmountField()


class ChargeRow(SourcedRow):
    description = serializers.CharField()
    amount = AmountField()


class ProfitRow(SourcedRow):
    date = serializers.DateField(allow_null=True)
    amount = AmountField()


class InvestmentRow(SourcedRow):
    name = serializers.CharField(max_length=255)
    type = serializers.ChoiceField(('bond',))
    date = serializers.DateField()
    rate = AmountField(max_digits=5, min_value=0)
    vesting_months = serializers.IntegerField(min_value=1, max_value=2147483647)
    amount = AmountField(min_value=0)
    profits = ProfitRow(many=True)


class ReconciliationRow(SourcedRow):
    as_of_date = serializers.DateField(allow_null=True)
    calculated_cash_balance = AmountField()
    stated_bank_balance = AmountField()
    variance = AmountField()
    expected_total_assets = AmountField()


TOTAL_FIELDS = (
    'contribution_capital', 'contribution_social', 'contribution_social_plus',
    'social_expenses', 'social_plus_expenses', 'bank_interest', 'joining_fees', 'collected_penalties',
    'bank_charges', 'loan_principal', 'loan_interest', 'loan_repayments', 'active_loan_principal',
    'active_loan_outstanding', 'investments', 'investment_profits', 'calculated_cash_balance',
    'expected_total_assets', 'shares',
)


class ManifestSerializer(serializers.Serializer):
    fixture_version = serializers.ChoiceField((FIXTURE_VERSION,))
    source_name = serializers.CharField(max_length=255)
    source_sha256 = serializers.RegexField(r'^[0-9a-f]{64}\Z')
    declared_summary_date = serializers.DateField()
    latest_transaction_date = serializers.DateField(allow_null=True)
    members = MemberRow(many=True, allow_empty=False)
    contributions = ContributionRow(many=True, allow_empty=False)
    loans = LoanRows()
    social_expenses = ExpenseRow(many=True)
    income = IncomeRow(many=True)
    bank_charges = ChargeRow(many=True)
    investments = InvestmentRow(many=True)
    reconciliation = ReconciliationRow()
    targets = serializers.DictField(child=AmountField())

    def validate(self, data):
        if data['targets'].keys() != set(TOTAL_FIELDS):
            raise serializers.ValidationError({'targets': 'Expected all workbook reconciliation totals.'})

        numbers = set()
        names = {}
        for member in data['members']:
            number = member['member_number']
            if number in numbers:
                raise serializers.ValidationError({'members': 'Duplicate member number.'})
            numbers.add(number)
            for name in {member['first_name'], *member['aliases']}:
                if name in names:
                    raise serializers.ValidationError({'members': 'Ambiguous member name or alias.'})
                names[name] = number

        contribution_keys = set()
        for row in data['contributions']:
            key = (row['member_number'], row['year'], row['month'], row['fund'])
            if row['member_number'] not in numbers or key in contribution_keys:
                raise serializers.ValidationError({'contributions': 'Unknown member or duplicate member/month/fund.'})
            contribution_keys.add(key)

        for rows in data['loans'].values():
            loan_members = set()
            for row in rows:
                member = names.get(row['member_name'])
                if member is None or member in loan_members:
                    raise serializers.ValidationError({'loans': 'Unknown member or duplicate loan aggregate.'})
                loan_members.add(member)
        return data


def expected_counts(data):
    active = data['loans']['active']
    historical = data['loans']['historical']
    counts = {
        'members': len(data['members']),
        'share_accounts': len(data['members']),
        'contributions': len(data['contributions']),
        'active_loans': len(active),
        'historical_loans': len(historical),
        'loan_repayments': sum(bool(row['paid']) for row in active + historical),
        'loan_installments': sum(row['duration_months'] for row in active),
        'social_expenses': len(data['social_expenses']),
        'income': len(data['income']),
        'bank_charges': len(data['bank_charges']),
        'investments': len(data['investments']),
        'investment_profits': sum(len(row['profits']) for row in data['investments']),
        'bank_snapshots': 1,
    }

    counts['ledger_entries'] = sum(counts[key] for key in (
        'contributions', 'active_loans', 'historical_loans', 'loan_repayments',
        'social_expenses', 'income', 'bank_charges', 'investments', 'investment_profits',
    ))
    counts['source_references'] = counts['ledger_entries'] + counts['members'] + counts['bank_snapshots']
    return counts


def expected_assets(totals):
    return (
        totals['contribution_capital'] + totals['bank_interest'] + totals['joining_fees']
        + totals['collected_penalties'] - totals['bank_charges']
        + totals['loan_interest'] + totals['investment_profits']
    )


def manifest_totals(data):
    totals = Counter()
    for row in data['contributions']:
        totals[f"contribution_{row['fund']}"] += row['amount']
    for row in data['social_expenses']:
        totals['social_expenses' if row['fund'] == 'SOCIAL' else 'social_plus_expenses'] += row['amount']
    for row in data['income']:
        key = row['type'] if row['type'] in ('bank_interest', 'joining_fee') else 'collected_penalties'
        totals[key] += row['amount']

    totals['bank_charges'] = sum(row['amount'] for row in data['bank_charges'])
    active = data['loans']['active']
    loans = active + data['loans']['historical']
    totals['active_loan_principal'] = sum(row['principal'] for row in active)
    totals['active_loan_outstanding'] = sum(row['outstanding'] for row in active)
    totals['loan_principal'] = sum(row['principal'] for row in loans)
    totals['loan_interest'] = sum(row['interest'] for row in loans)
    totals['loan_repayments'] = sum(row['paid'] for row in loans)
    totals['investments'] = sum(row['amount'] for row in data['investments'])
    totals['investment_profits'] = sum(p['amount'] for row in data['investments'] for p in row['profits'])
    totals['shares'] = sum(row['share_count'] for row in data['members'])
    totals['calculated_cash_balance'] = (
        sum(totals[f'contribution_{fund}'] for fund in CONTRIBUTION_FUNDS)
        + totals['bank_interest'] + totals['joining_fees'] + totals['collected_penalties']
        + totals['loan_repayments'] + totals['investment_profits']
        - totals['social_expenses'] - totals['social_plus_expenses']
        - totals['bank_charges'] - totals['loan_principal'] - totals['investments']
    )
    totals['expected_total_assets'] = expected_assets(totals)
    return {key: totals[key] for key in TOTAL_FIELDS}


def compare_totals(expected, calculated):
    return {
        key: {'expected': format(value, '.2f'), 'calculated': format(calculated[key], '.2f')}
        for key, value in expected.items() if value != calculated[key]
    }


def financial_report(data, calculated):
    expected = data['targets']
    snapshot = data['reconciliation']
    discrepancies = compare_totals(expected, calculated)
    snapshot_totals = {key: snapshot[key] for key in ('calculated_cash_balance', 'expected_total_assets')}
    discrepancies.update(compare_totals(snapshot_totals, calculated))
    discrepancies.update(compare_totals(
        {'bank_variance': snapshot['variance']},
        {'bank_variance': snapshot['stated_bank_balance'] - calculated['calculated_cash_balance']},
    ))
    return {
        'expected_totals': {key: format(value, '.2f') for key, value in expected.items()},
        'calculated_totals': {key: format(value, '.2f') for key, value in calculated.items()},
        'stated_bank_balance': format(snapshot['stated_bank_balance'], '.2f'),
        'reported_bank_variance': format(snapshot['variance'], '.2f'),
        'bank_balance_as_of': snapshot['as_of_date'].isoformat() if snapshot['as_of_date'] else None,
        'discrepancies': discrepancies,
    }
