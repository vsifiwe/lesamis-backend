import calendar
import datetime
from decimal import Decimal, ROUND_HALF_UP

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

# ------------------------------------------------------------------
# Loan seed data from:
# Situation les Amis Sept 2023 Version.xlsx / Details de credits
# ------------------------------------------------------------------
# Total principal       : Details de credits!D52 = 134,981,900.00
# Total paid            : Details de credits!F52 = 120,359,346.00
# Active principal      : Details de credits!G52 =  31,370,000.00
# Active paid           : Details de credits!K52 =  10,959,233.89
# Active outstanding    : Details de credits!L52 =  22,790,466.11
# ------------------------------------------------------------------

SOURCE_WORKBOOK = 'Situation les Amis Sept 2023 Version.xlsx'
SUMMARY_DATE = datetime.date(2026, 3, 5)

EXPECTED_TOTALS = {
    'principal': Decimal('134981900.00'),
    'paid': Decimal('120359346.00'),
    'active_principal': Decimal('31370000.00'),
    'active_paid': Decimal('10959233.89'),
    'active_outstanding': Decimal('22790466.11'),
}

MEMBER_NUMBERS = {
    'Didier': 'MBR-0001',
    'Claudine': 'MBR-0002',
    'Eric': 'MBR-0003',
    'Delphine': 'MBR-0004',
    'Clement': 'MBR-0005',
    'Sandrine': 'MBR-0006',
    'Semanzi': 'MBR-0007',
    'Vanessa': 'MBR-0008',
    'Musonera': 'MBR-0009',
    'Yvonne': 'MBR-0010',
    'Fidele': 'MBR-0011',
    'Thadee': 'MBR-0012',
    'Thadée': 'MBR-0012',
    'Diane': 'MBR-0013',
    'Kamana': 'MBR-0014',
    'Gerardine': 'MBR-0015',
    'Tuyizere': 'MBR-0016',
    'Venuste': 'MBR-0017',
    'Dalyda': 'MBR-0018',
    'Chantal': 'MBR-0019',
    'Edissa': 'MBR-0020',
    'Vital': 'MBR-0021',
    'Obadiah': 'MBR-0022',
    'Obadias': 'MBR-0022',
    'Arnauld': 'MBR-0023',
    'Joelle': 'MBR-0024',
    'Florent': 'MBR-0025',
    'Arsene': 'MBR-0027',
    'Emmanuel': 'MBR-0028',
    'Gedeon': 'MBR-0032',
    'Phoebe': 'MBR-0033',
    'Edmond': 'MBR-0035',
    'Belyse': 'MBR-0036',
    'Elie': 'MBR-0038',
    'Seraphina': 'MBR-0039',
    'Epimaque': 'MBR-0041',
    'Manzi': 'MBR-0043',
    'Christian': 'MBR-0046',
    'Chrisitan': 'MBR-0046',
}

LOAN_PRODUCTS = [
    ('Seed loan - 3 months @ 3%', 3, '3.00', 'Workbook seed product for 3-month loans.'),
    ('Seed loan - 6 months @ 4%', 6, '4.00', 'Workbook seed product for 6-month loans.'),
    ('Seed loan - 12 months @ 7%', 12, '7.00', 'Workbook seed product for 12-month loans.'),
    ('Seed loan - 18 months @ 10%', 18, '10.00', 'Workbook seed product for 18-month loans.'),
    ('Historical aggregate loan', 1, '0.00', 'Workbook aggregate for historical loans where exact original product/date detail is unavailable.'),
]

# (member_name, principal, duration_months, rate_percent, monthly_installment, paid, outstanding, issued_date, maturity_date)
ACTIVE_LOANS = [
    ('Didier', '7900000.00', 18, '10.00', '482777.78', '3862222.89', '4827777.11', datetime.date(2025, 12, 30), datetime.date(2027, 6, 30)),
    ('Claudine', '1400000.00', 18, '10.00', '85555.56', '681422.00', '858578.00', datetime.date(2025, 5, 15), datetime.date(2026, 11, 15)),
    ('Sandrine', '1000000.00', 3, '3.00', '343333.33', '0.00', '1030000.00', datetime.date(2026, 2, 25), datetime.date(2026, 5, 25)),
    ('Semanzi', '760000.00', 12, '7.00', '67766.67', '0.00', '813200.00', datetime.date(2025, 10, 13), datetime.date(2026, 10, 13)),
    ('Vanessa', '4500000.00', 3, '3.00', '1545000.00', '4635000.00', '0.00', datetime.date(2026, 3, 7), datetime.date(2026, 6, 7)),
    ('Fidele', '1000000.00', 18, '10.00', '61111.11', '183333.00', '916667.00', datetime.date(2025, 11, 8), datetime.date(2027, 5, 8)),
    ('Gerardine', '720000.00', 18, '10.00', '44000.00', '132000.00', '660000.00', datetime.date(2026, 1, 14), datetime.date(2027, 6, 14)),
    ('Tuyizere', '1800000.00', 12, '7.00', '160500.00', '0.00', '1926000.00', datetime.date(2025, 10, 13), datetime.date(2026, 10, 13)),
    ('Dalyda', '500000.00', 18, '10.00', '30555.56', '0.00', '550000.00', datetime.date(2025, 8, 16), datetime.date(2027, 2, 16)),
    ('Chantal', '330000.00', 3, '3.00', '113300.00', '113300.00', '226600.00', datetime.date(2026, 3, 23), datetime.date(2026, 7, 23)),
    ('Edissa', '800000.00', 12, '7.00', '71333.33', '0.00', '856000.00', datetime.date(2026, 4, 27), datetime.date(2027, 4, 27)),
    ('Vital', '1300000.00', 12, '7.00', '115916.67', '695512.00', '695488.00', datetime.date(2025, 10, 27), datetime.date(2026, 10, 27)),
    ('Obadiah', '840000.00', 12, '7.00', '74900.00', '0.00', '898800.00', datetime.date(2026, 5, 6), datetime.date(2027, 5, 6)),
    ('Joelle', '2000000.00', 18, '10.00', '122222.22', '122222.00', '2077778.00', datetime.date(2026, 4, 13), datetime.date(2027, 10, 13)),
    ('Florent', '820000.00', 6, '4.00', '142133.33', '0.00', '852800.00', datetime.date(2026, 4, 9), datetime.date(2026, 10, 9)),
    ('Gedeon', '1500000.00', 12, '7.00', '133750.00', '0.00', '1605000.00', datetime.date(2025, 10, 3), datetime.date(2026, 10, 3)),
    ('Phoebe', '800000.00', 12, '7.00', '71333.33', '0.00', '856000.00', datetime.date(2026, 1, 6), datetime.date(2027, 1, 6)),
    ('Edmond', '2000000.00', 18, '10.00', '122222.22', '122222.00', '2077778.00', datetime.date(2026, 2, 18), datetime.date(2027, 8, 18)),
    ('Elie', '800000.00', 12, '7.00', '71333.33', '0.00', '856000.00', datetime.date(2026, 5, 4), datetime.date(2027, 5, 4)),
    ('Epimaque', '600000.00', 3, '3.00', '206000.00', '412000.00', '206000.00', datetime.date(2026, 2, 9), datetime.date(2026, 5, 9)),
]

# (member_name, principal, interest, paid)
HISTORICAL_LOANS = [
    ('Didier', '20520000.00', '1281000.00', '21391607.11'),
    ('Claudine', '5300000.00', '334000.00', '5634000.00'),
    ('Eric', '4800000.00', '219000.00', '5019000.00'),
    ('Delphine', '2200000.00', '140000.00', '2340000.00'),
    ('Clement', '1000000.00', '50000.00', '1050000.00'),
    ('Sandrine', '3700000.00', '215000.00', '3919836.00'),
    ('Semanzi', '2620000.00', '169400.00', '2789400.00'),
    ('Vanessa', '9050000.00', '726900.00', '9801455.00'),
    ('Musonera', '1300000.00', '65000.00', '1365000.00'),
    ('Yvonne', '1170000.00', '58500.00', '1228500.00'),
    ('Fidele', '1000000.00', '70000.00', '1070001.00'),
    ('Thadée', '4320000.00', '216000.00', '4536000.00'),
    ('Diane', '1560000.00', '78000.00', '1628000.00'),
    ('Kamana', '1340000.00', '67000.00', '1407000.00'),
    ('Gerardine', '2060000.00', '110000.00', '2170000.00'),
    ('Tuyizere', '7950000.00', '457500.00', '8407500.00'),
    ('Venuste', '960000.00', '48000.00', '1008000.00'),
    ('Dalyda', '3640000.00', '217000.00', '2947500.00'),
    ('Chantal', '2911900.00', '136357.00', '3769257.00'),
    ('Edissa', '2000000.00', '120000.00', '2120000.00'),
    ('Vital', '1730000.00', '109500.00', '1839500.00'),
    ('Obadiah', '1230000.00', '86100.00', '1414683.00'),
    ('Arnauld', '3290000.00', '141900.00', '3431900.00'),
    ('Joelle', '3410000.00', '191700.00', '3601987.00'),
    ('Florent', '2070000.00', '108500.00', '2178510.00'),
    ('Arsene', '1250000.00', '0.00', '630000.00'),
    ('Emmanuel', '1280000.00', '77000.00', '1357000.00'),
    ('Gedeon', '2700000.00', '172000.00', '2872500.00'),
    ('Phoebe', '2180000.00', '128600.00', '2308573.00'),
    ('Edmond', '1850000.00', '74000.00', '1925000.00'),
    ('Belyse', '1420000.00', '72400.00', '1492400.00'),
    ('Elie', '400000.00', '13000.00', '1269000.00'),
    ('Seraphina', '700000.00', '49000.00', '749000.00'),
    ('Manzi', '700000.00', '28000.00', '728003.00'),
]


def _d(value):
    return Decimal(value)


def _add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def _historical_rate(principal, interest):
    if principal == 0:
        return Decimal('0.00')
    return (interest / principal * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _active_product_name(duration, rate):
    rate_label = str(rate.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return f'Seed loan - {duration} months @ {rate_label}%'


def _status_from_paid(total, paid):
    if paid + Decimal('1.00') >= total:
        return 'closed'
    return 'defaulted'


def _validate_totals():
    active_principal = sum(_d(row[1]) for row in ACTIVE_LOANS)
    active_paid = sum(_d(row[5]) for row in ACTIVE_LOANS)
    active_outstanding = sum(_d(row[6]) for row in ACTIVE_LOANS)
    historical_principal = sum(_d(row[1]) for row in HISTORICAL_LOANS)
    historical_paid = sum(_d(row[3]) for row in HISTORICAL_LOANS)

    actual = {
        'principal': active_principal + historical_principal,
        'paid': active_paid + historical_paid,
        'active_principal': active_principal,
        'active_paid': active_paid,
        'active_outstanding': active_outstanding,
    }
    if actual != EXPECTED_TOTALS:
        raise ValueError(f'Loan seed totals do not match workbook totals: {actual}')


def seed(apps, schema_editor):
    Member = apps.get_model('core', 'Member')
    LoanProduct = apps.get_model('core', 'LoanProduct')
    Loan = apps.get_model('core', 'Loan')
    LoanRepayment = apps.get_model('core', 'LoanRepayment')
    LedgerEntry = apps.get_model('core', 'LedgerEntry')
    FundAccount = apps.get_model('core', 'FundAccount')

    _validate_totals()

    products = {}
    for name, duration, rate, notes in LOAN_PRODUCTS:
        product, _ = LoanProduct.objects.get_or_create(
            name=name,
            defaults={
                'duration_months': duration,
                'interest_rate_percent': _d(rate),
                'is_active': True,
                'notes': notes,
            },
        )
        products[name] = product

    capital = FundAccount.objects.get(code='CAPITAL')
    ledger_entries = []

    def create_loan(member_name, product, principal, rate, duration, total, monthly, issued, first_due, status, notes):
        member = Member.objects.get(member_number=MEMBER_NUMBERS[member_name])
        loan = Loan.objects.create(
            member=member,
            loan_product=product,
            principal_amount=principal,
            interest_rate_percent_snapshot=rate,
            duration_months_snapshot=duration,
            total_repayment_amount=total,
            monthly_installment_amount=monthly,
            issued_date=issued,
            first_due_date=first_due,
            status=status,
            notes=notes,
            created_by=None,
        )
        ledger_entries.append(LedgerEntry(
            fund_account=capital,
            member=member,
            entry_date=issued,
            entry_type='loan_disbursement',
            amount=principal,
            direction='debit',
            reference_id=loan.id,
            reference_type='loan',
            notes=f'Seeded from {SOURCE_WORKBOOK}.',
            recorded_by=None,
        ))
        return loan, member

    def create_repayment(loan, member, amount, paid_date, notes):
        if amount <= 0:
            return
        repayment = LoanRepayment.objects.create(
            loan=loan,
            amount_paid=amount,
            paid_date=paid_date,
            payment_method='bank',
            notes=notes,
            recorded_by=None,
        )
        ledger_entries.append(LedgerEntry(
            fund_account=capital,
            member=member,
            entry_date=paid_date,
            entry_type='loan_repayment',
            amount=amount,
            direction='credit',
            reference_id=repayment.id,
            reference_type='loan_repayment',
            notes=f'Seeded from {SOURCE_WORKBOOK}.',
            recorded_by=None,
        ))

    for member_name, principal_s, duration, rate_s, monthly_s, paid_s, outstanding_s, issued, _maturity in ACTIVE_LOANS:
        principal = _d(principal_s)
        rate = _d(rate_s)
        monthly = _d(monthly_s)
        paid = _d(paid_s)
        outstanding = _d(outstanding_s)
        total = (principal * (Decimal('1') + rate / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        product = products[_active_product_name(duration, rate)]
        status = 'closed' if outstanding == 0 else 'active'
        loan, member = create_loan(
            member_name,
            product,
            principal,
            rate,
            duration,
            total,
            monthly,
            issued,
            _add_months(issued, 1),
            status,
            'Current loan reconstructed from Details de credits columns G:N.',
        )
        create_repayment(
            loan,
            member,
            paid,
            SUMMARY_DATE,
            'Aggregate current-loan repayment reconstructed from Details de credits column K.',
        )

    historical_product = products['Historical aggregate loan']
    for member_name, principal_s, interest_s, paid_s in HISTORICAL_LOANS:
        principal = _d(principal_s)
        interest = _d(interest_s)
        paid = _d(paid_s)
        total = principal + interest
        rate = _historical_rate(principal, interest)
        loan, member = create_loan(
            member_name,
            historical_product,
            principal,
            rate,
            1,
            total,
            total,
            SUMMARY_DATE,
            SUMMARY_DATE,
            _status_from_paid(total, paid),
            'Historical aggregate loan reconstructed from Details de credits columns D:F after subtracting current-loan columns G:K.',
        )
        create_repayment(
            loan,
            member,
            paid,
            SUMMARY_DATE,
            'Aggregate historical repayment reconstructed from Details de credits column F after subtracting column K.',
        )

    LedgerEntry.objects.bulk_create(ledger_entries)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0126_seed_social_expense_records'),
    ]

    operations = [
        migrations.AlterField(
            model_name='loan',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='created_loans',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='loanrepayment',
            name='recorded_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='recorded_repayments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(seed, reverse_code=migrations.RunPython.noop),
    ]
