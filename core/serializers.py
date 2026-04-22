from decimal import Decimal

from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from .models import ContributionCycle, ContributionReceipt, ContributionReceiptItem, Investment, InvestmentProfitEntry, Loan, LoanProduct, Member, MemberContributionObligation, MemberShareAccount, OtherCharge, Penalty, User


def _get_current_share_price() -> int:
    cycle = ContributionCycle.objects.filter(share_unit_value__isnull=False).order_by('-year', '-month').first()
    return cycle.share_unit_value if cycle else 10_000


class UserSerializer(serializers.ModelSerializer):
    last_login_at = serializers.DateTimeField(source='last_login', read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'email', 'full_name', 'role', 'is_active',
            'last_login_at', 'member', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'last_login_at', 'created_at', 'updated_at']


class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model  = User
        fields = ['email', 'full_name', 'password', 'role', 'member']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class MemberSerializer(serializers.ModelSerializer):
    share_count = serializers.SerializerMethodField()

    class Meta:
        model  = Member
        fields = [
            'id', 'member_number', 'first_name', 'last_name',
            'phone', 'email', 'status', 'join_date', 'exit_date',
            'share_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'member_number', 'created_at', 'updated_at']

    def get_share_count(self, obj):
        try:
            return obj.share_account.share_count
        except Member.share_account.RelatedObjectDoesNotExist:
            return None


class CreateMemberSerializer(serializers.ModelSerializer):
    default_password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model  = Member
        fields = ['first_name', 'last_name', 'phone', 'email', 'join_date', 'default_password']
        extra_kwargs = {
            'email': {'required': True, 'allow_blank': False},
        }

    def create(self, validated_data):
        password = validated_data.pop('default_password')
        member = Member.objects.create(**validated_data)
        User.objects.create_user(
            email=member.email,
            password=password,
            full_name=member.get_full_name(),
            role=User.Role.VIEWER,
            member=member,
        )
        MemberShareAccount.objects.create(member=member)
        return member


class MemberShareAccountSerializer(serializers.ModelSerializer):
    total_value = serializers.IntegerField(read_only=True)

    class Meta:
        model  = MemberShareAccount
        fields = [
            'id', 'member', 'share_count', 'share_unit_value',
            'total_value', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'total_value', 'created_at', 'updated_at']


class AdjustSharesSerializer(serializers.Serializer):
    action         = serializers.ChoiceField(choices=['INCREASE', 'DECREASE'])
    member_id      = serializers.UUIDField()
    amount         = serializers.IntegerField(min_value=1)
    payment_method = serializers.ChoiceField(
        choices=['cash', 'bank', 'mobile_money'],
        required=False,
    )
    received_date  = serializers.DateField(required=False)

    def validate(self, data):
        if data.get('action') == 'INCREASE' and not data.get('payment_method'):
            raise serializers.ValidationError(
                {'payment_method': 'This field is required when action is INCREASE.'}
            )
        return data


# ---------------------------------------------------------------------------
# Other Charges
# ---------------------------------------------------------------------------

class OtherChargeSerializer(serializers.ModelSerializer):
    recorded_by_email = serializers.EmailField(source='recorded_by.email', read_only=True)
    fund_account_name = serializers.CharField(source='fund_account.name', read_only=True)

    class Meta:
        model  = OtherCharge
        fields = [
            'id', 'charge_type', 'amount', 'direction',
            'fund_account', 'fund_account_name',
            'charge_date', 'description',
            'recorded_by', 'recorded_by_email', 'created_at',
        ]


class CreateOtherChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OtherCharge
        fields = ['charge_type', 'amount', 'direction', 'fund_account', 'charge_date', 'description']

    def validate(self, data):
        if data.get('charge_type') == 'adjustment':
            desc = (data.get('description') or '').strip()
            if len(desc) < 50:
                raise serializers.ValidationError(
                    {'description': 'A description of at least 50 characters is required for adjustments.'}
                )
        return data


# ---------------------------------------------------------------------------
# Obligations
# ---------------------------------------------------------------------------

class MemberContributionObligationSerializer(serializers.ModelSerializer):
    member_number = serializers.CharField(source='member.member_number', read_only=True)
    member_name   = serializers.SerializerMethodField()
    cycle         = serializers.StringRelatedField(source='contribution_cycle')

    class Meta:
        model  = MemberContributionObligation
        fields = [
            'id', 'member', 'member_number', 'member_name',
            'contribution_cycle', 'cycle',
            'share_count_snapshot', 'share_unit_value_snapshot',
            'capital_amount_expected', 'social_amount_expected',
            'social_plus_amount_expected', 'total_amount_expected',
            'status', 'created_at', 'updated_at',
        ]

    def get_member_name(self, obj):
        return obj.member.get_full_name()


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------

class ContributionReceiptItemSerializer(serializers.ModelSerializer):
    member_number = serializers.CharField(source='obligation.member.member_number', read_only=True)
    member_name   = serializers.SerializerMethodField()

    class Meta:
        model  = ContributionReceiptItem
        fields = ['id', 'obligation', 'member_number', 'member_name', 'amount_applied', 'created_at']

    def get_member_name(self, obj):
        return obj.obligation.member.get_full_name()


class ContributionReceiptSerializer(serializers.ModelSerializer):
    items             = ContributionReceiptItemSerializer(many=True, read_only=True)
    confirmed_by_email = serializers.EmailField(source='confirmed_by.email', read_only=True, default=None)
    created_by_email  = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model  = ContributionReceipt
        fields = [
            'id', 'amount_received', 'received_date', 'payment_method',
            'status', 'confirmed_by', 'confirmed_by_email', 'confirmed_at',
            'rejection_reason', 'notes',
            'created_by', 'created_by_email',
            'created_at', 'updated_at',
            'items',
        ]


class _ReceiptItemWriteSerializer(serializers.Serializer):
    obligation_id  = serializers.UUIDField()
    amount_applied = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))


class CreateContributionReceiptSerializer(serializers.Serializer):
    amount_received = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    received_date   = serializers.DateField()
    payment_method  = serializers.ChoiceField(choices=ContributionReceipt.PaymentMethod.choices)
    notes           = serializers.CharField(required=False, allow_blank=True, default='')
    items           = _ReceiptItemWriteSerializer(many=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError('At least one item is required.')
        obligation_ids = [item['obligation_id'] for item in items]
        if len(obligation_ids) != len(set(str(i) for i in obligation_ids)):
            raise serializers.ValidationError('Duplicate obligation ids are not allowed.')
        already_paid = ContributionReceiptItem.objects.filter(
            obligation_id__in=obligation_ids
        ).values_list('obligation_id', flat=True)
        if already_paid:
            raise serializers.ValidationError(
                f'The following obligations already have a receipt: {[str(i) for i in already_paid]}'
            )
        obligations = {
            str(o.id): o
            for o in MemberContributionObligation.objects.filter(id__in=obligation_ids)
        }
        errors = []
        for item in items:
            obligation = obligations.get(str(item['obligation_id']))
            if obligation is None:
                errors.append(f'Obligation {item["obligation_id"]} does not exist.')
                continue
            if item['amount_applied'] != obligation.total_amount_expected:
                errors.append(
                    f'Obligation {item["obligation_id"]}: amount_applied ({item["amount_applied"]}) '
                    f'must equal total_amount_expected ({obligation.total_amount_expected}).'
                )
        if errors:
            raise serializers.ValidationError(errors)
        return items

    def validate(self, data):
        items = data.get('items', [])
        total_applied = sum(item['amount_applied'] for item in items)
        if total_applied > data['amount_received']:
            raise serializers.ValidationError(
                f'Total items amount ({total_applied}) exceeds amount received ({data["amount_received"]}).'
            )
        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        now = timezone.now()
        receipt = ContributionReceipt.objects.create(
            **validated_data,
            status=ContributionReceipt.Status.CONFIRMED,
            confirmed_by=validated_data.get('created_by'),
            confirmed_at=now,
        )
        obligation_ids = [item['obligation_id'] for item in items_data]
        ContributionReceiptItem.objects.bulk_create([
            ContributionReceiptItem(
                receipt=receipt,
                obligation_id=item['obligation_id'],
                amount_applied=item['amount_applied'],
            )
            for item in items_data
        ])
        MemberContributionObligation.objects.filter(id__in=obligation_ids).update(
            status=MemberContributionObligation.Status.CONFIRMED,
        )
        Penalty.objects.filter(
            contribution_obligation_id__in=obligation_ids,
            waived=False,
            receipt__isnull=True,
        ).update(receipt=receipt)
        from .ledger_service import record_contribution_receipt
        record_contribution_receipt(receipt, validated_data['created_by'])
        return receipt


# ---------------------------------------------------------------------------
# Penalties
# ---------------------------------------------------------------------------

class PenaltySerializer(serializers.ModelSerializer):
    member_number = serializers.CharField(source='contribution_obligation.member.member_number', read_only=True)
    member_name   = serializers.SerializerMethodField()
    cycle         = serializers.StringRelatedField(source='contribution_obligation.contribution_cycle')
    waived_by_email = serializers.EmailField(source='waived_by.email', read_only=True, default=None)

    class Meta:
        model  = Penalty
        fields = [
            'id', 'contribution_obligation', 'receipt',
            'member_number', 'member_name', 'cycle',
            'penalty_type', 'amount', 'reason', 'auto_generated',
            'waived', 'waived_by', 'waived_by_email', 'waived_at',
            'created_at', 'updated_at',
        ]

    def get_member_name(self, obj):
        return obj.contribution_obligation.member.get_full_name()


# ---------------------------------------------------------------------------
# Investments
# ---------------------------------------------------------------------------

class InvestmentSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    total_profit     = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model  = Investment
        fields = [
            'id', 'name', 'investment_type', 'investment_date',
            'amount_invested', 'expected_interest_rate_percent', 'vesting_period_months',
            'status', 'description',
            'total_profit',
            'created_by', 'created_by_email',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class CreateInvestmentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Investment
        fields = [
            'name', 'investment_type', 'investment_date',
            'amount_invested', 'expected_interest_rate_percent', 'vesting_period_months',
            'status', 'description',
        ]
        extra_kwargs = {
            'expected_interest_rate_percent': {'required': False, 'allow_null': True},
            'vesting_period_months': {'required': False, 'allow_null': True},
            'status': {'required': False},
            'description': {'required': False, 'allow_blank': True},
        }


class InvestmentProfitEntrySerializer(serializers.ModelSerializer):
    recorded_by_email = serializers.EmailField(source='recorded_by.email', read_only=True)

    class Meta:
        model  = InvestmentProfitEntry
        fields = [
            'id', 'investment', 'profit_date', 'amount', 'description',
            'recorded_by', 'recorded_by_email',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'investment', 'recorded_by', 'created_at', 'updated_at']


class CreateInvestmentProfitEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model  = InvestmentProfitEntry
        fields = ['profit_date', 'amount', 'description']
        extra_kwargs = {
            'description': {'required': False, 'allow_blank': True},
        }


# ---------------------------------------------------------------------------
# Loan Products
# ---------------------------------------------------------------------------

class LoanProductSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LoanProduct
        fields = [
            'id', 'name', 'duration_months', 'interest_rate_percent',
            'is_active', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ---------------------------------------------------------------------------
# Loans
# ---------------------------------------------------------------------------

class LoanSerializer(serializers.ModelSerializer):
    member_name        = serializers.SerializerMethodField()
    member_number      = serializers.CharField(source='member.member_number', read_only=True)
    loan_product_name  = serializers.CharField(source='loan_product.name', read_only=True)
    created_by_email   = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model  = Loan
        fields = [
            'id', 'member', 'member_number', 'member_name',
            'loan_product', 'loan_product_name',
            'principal_amount', 'interest_rate_percent_snapshot',
            'duration_months_snapshot', 'total_repayment_amount',
            'monthly_installment_amount', 'issued_date', 'first_due_date',
            'status', 'notes', 'created_by', 'created_by_email',
            'created_at', 'updated_at',
        ]

    def get_member_name(self, obj):
        return obj.member.get_full_name()


class CreateLoanSerializer(serializers.Serializer):
    member_id      = serializers.UUIDField()
    loan_product_id = serializers.UUIDField()
    principal_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    issued_date    = serializers.DateField()
    first_due_date = serializers.DateField()
    notes          = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, data):
        # Resolve member
        try:
            member = Member.objects.select_related('share_account').get(pk=data['member_id'])
        except Member.DoesNotExist:
            raise serializers.ValidationError({'member_id': 'Member does not exist.'})
        if member.status != Member.Status.ACTIVE:
            raise serializers.ValidationError({'member_id': 'Member is not active.'})
        try:
            share_account = member.share_account
        except Member.share_account.RelatedObjectDoesNotExist:
            raise serializers.ValidationError({'member_id': 'Member has no share account.'})

        from django.db.models import Sum
        share_price = _get_current_share_price()
        max_principal = share_account.share_count * share_price
        existing_principal = (
            Loan.objects
            .filter(member=member, status=Loan.Status.ACTIVE)
            .aggregate(total=Sum('principal_amount'))['total']
        ) or Decimal('0')
        available = max_principal - existing_principal
        if data['principal_amount'] > available:
            raise serializers.ValidationError(
                {
                    'principal_amount': (
                        f'Principal exceeds available borrowing capacity. '
                        f'Share cap: {max_principal}, existing active loans: {existing_principal}, '
                        f'available: {available}.'
                    )
                }
            )

        # Resolve loan product
        try:
            loan_product = LoanProduct.objects.get(pk=data['loan_product_id'])
        except LoanProduct.DoesNotExist:
            raise serializers.ValidationError({'loan_product_id': 'Loan product does not exist.'})
        if not loan_product.is_active:
            raise serializers.ValidationError({'loan_product_id': 'Loan product is not active.'})

        data['_member'] = member
        data['_loan_product'] = loan_product
        return data

    def create(self, validated_data):
        member       = validated_data['_member']
        loan_product = validated_data['_loan_product']
        principal    = validated_data['principal_amount']
        rate         = loan_product.interest_rate_percent
        duration     = loan_product.duration_months

        total   = (principal * (1 + rate / 100)).quantize(Decimal('0.01'))
        monthly = (total / duration).quantize(Decimal('0.01'))

        return Loan.objects.create(
            member=member,
            loan_product=loan_product,
            principal_amount=principal,
            interest_rate_percent_snapshot=rate,
            duration_months_snapshot=duration,
            total_repayment_amount=total,
            monthly_installment_amount=monthly,
            issued_date=validated_data['issued_date'],
            first_due_date=validated_data['first_due_date'],
            notes=validated_data['notes'],
            created_by=validated_data['created_by'],
        )


class MemberContributionReceivedSerializer(serializers.ModelSerializer):
    cycle_year     = serializers.IntegerField(source='obligation.contribution_cycle.year',    read_only=True)
    cycle_month    = serializers.IntegerField(source='obligation.contribution_cycle.month',   read_only=True)
    received_date  = serializers.DateField(source='receipt.received_date',                   read_only=True)
    payment_method = serializers.CharField(source='receipt.payment_method',                  read_only=True)

    class Meta:
        model  = ContributionReceiptItem
        fields = ['id', 'cycle_year', 'cycle_month', 'amount_applied', 'received_date', 'payment_method']


class MemberContributionPendingSerializer(serializers.ModelSerializer):
    cycle_year  = serializers.IntegerField(source='contribution_cycle.year',     read_only=True)
    cycle_month = serializers.IntegerField(source='contribution_cycle.month',    read_only=True)
    due_date    = serializers.DateField(source='contribution_cycle.due_date',    read_only=True)

    class Meta:
        model  = MemberContributionObligation
        fields = [
            'id', 'cycle_year', 'cycle_month', 'due_date',
            'capital_amount_expected', 'social_amount_expected',
            'social_plus_amount_expected', 'total_amount_expected', 'status',
        ]


class MemberPenaltySerializer(serializers.ModelSerializer):
    cycle_year  = serializers.IntegerField(source='contribution_obligation.contribution_cycle.year',  read_only=True)
    cycle_month = serializers.IntegerField(source='contribution_obligation.contribution_cycle.month', read_only=True)

    class Meta:
        model  = Penalty
        fields = [
            'id', 'cycle_year', 'cycle_month',
            'penalty_type', 'amount', 'reason',
            'waived', 'waived_at', 'created_at',
        ]


class MemberLoanSerializer(serializers.ModelSerializer):
    loan_product_name  = serializers.CharField(source='loan_product.name', read_only=True)
    total_paid         = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    outstanding_amount = serializers.SerializerMethodField()

    def get_outstanding_amount(self, obj):
        return (obj.total_repayment_amount - obj.total_paid).quantize(Decimal('0.01'))

    class Meta:
        model  = Loan
        fields = [
            'id', 'loan_product_name',
            'principal_amount', 'interest_rate_percent_snapshot', 'duration_months_snapshot',
            'total_repayment_amount', 'monthly_installment_amount',
            'outstanding_amount', 'total_paid',
            'issued_date', 'first_due_date', 'status',
        ]

