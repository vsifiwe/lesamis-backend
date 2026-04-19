from django.db import transaction
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ContributionReceipt, ContributionReceiptItem, FundAccount, Investment, InvestmentProfitEntry, Loan, LoanProduct, LoanRepayment, LedgerEntry, Member, MemberContributionObligation, MemberShareAccount, Penalty
from .permissions import IsAdminUser, IsAnyAuthenticatedUser
from .serializers import (
    AdjustSharesSerializer,
    ContributionReceiptSerializer,
    CreateContributionReceiptSerializer,
    CreateInvestmentSerializer,
    CreateInvestmentProfitEntrySerializer,
    CreateLoanSerializer,
    CreateMemberSerializer,
    InvestmentSerializer,
    InvestmentProfitEntrySerializer,
    LoanProductSerializer,
    LoanSerializer,
    MemberContributionObligationSerializer,
    MemberSerializer,
    MemberShareAccountSerializer,
    PenaltySerializer,
)


class MemberListCreateView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        members = Member.objects.select_related('share_account').all()
        serializer = MemberSerializer(members, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=CreateMemberSerializer,
        responses={201: MemberSerializer},
        operation_summary='Create a member',
        operation_description=(
            'Creates a new club member and automatically provisions a linked User account '
            'with the `viewer` role using the supplied `default_password`. '
            'A share account is also created for the member with 0 shares.'
        ),
    )
    def post(self, request):
        serializer = CreateMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = serializer.save()
        return Response(MemberSerializer(member).data, status=status.HTTP_201_CREATED)


class MemberDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        return Response(MemberSerializer(member).data)


class MemberDeactivateView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        if member.status == Member.Status.EXITED:
            return Response(
                {'detail': 'Member has already exited.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        member.status = Member.Status.EXITED
        member.exit_date = member.exit_date or timezone.now().date()
        member.save(update_fields=['status', 'exit_date', 'updated_at'])
        return Response(MemberSerializer(member).data)


class ShareAdjustView(APIView):
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        request_body=AdjustSharesSerializer,
        responses={200: MemberShareAccountSerializer},
        operation_summary='Adjust member share count',
        operation_description=(
            'Increases or decreases a member\'s share count by the given amount. '
            'A DECREASE that would push the share count below 0 is rejected.'
        ),
    )
    def post(self, request):
        serializer = AdjustSharesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member_id = serializer.validated_data['member_id']
        action    = serializer.validated_data['action']
        amount    = serializer.validated_data['amount']

        account = get_object_or_404(MemberShareAccount, member_id=member_id)

        if action == 'DECREASE':
            if account.share_count < amount:
                return Response(
                    {'detail': f'Cannot decrease by {amount}: current share count is only {account.share_count}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            with transaction.atomic():
                account.share_count -= amount
                account.save(update_fields=['share_count', 'updated_at'])
        else:
            payment_method = serializer.validated_data['payment_method']
            received_date  = serializer.validated_data.get('received_date') or timezone.now().date()
            amount_received = amount * account.share_unit_value

            with transaction.atomic():
                account.share_count += amount
                account.save(update_fields=['share_count', 'updated_at'])

                receipt = ContributionReceipt.objects.create(
                    amount_received=amount_received,
                    received_date=received_date,
                    payment_method=payment_method,
                    status=ContributionReceipt.Status.CONFIRMED,
                    confirmed_by=request.user,
                    confirmed_at=timezone.now(),
                    notes=(
                        f'Share purchase: {amount} share(s) for '
                        f'{account.member.first_name} {account.member.last_name} '
                        f'({account.member.member_number})'
                    ),
                    created_by=request.user,
                )

                from .ledger_service import record_share_purchase
                record_share_purchase(account, receipt, request.user)

        return Response(MemberShareAccountSerializer(account).data)


class ObligationListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        obligations = (
            MemberContributionObligation.objects
            .filter(status=MemberContributionObligation.Status.EXPECTED)
            .select_related('member', 'contribution_cycle')
        )
        serializer = MemberContributionObligationSerializer(obligations, many=True)
        return Response(serializer.data)


class ContributionReceiptListCreateView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        receipts = (
            ContributionReceipt.objects
            .select_related('confirmed_by', 'created_by')
            .prefetch_related('items__obligation__member')
        )
        serializer = ContributionReceiptSerializer(receipts, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=CreateContributionReceiptSerializer,
        responses={201: ContributionReceiptSerializer},
        operation_summary='Create a contribution receipt',
        operation_description=(
            'Records a payment received from one or more members. '
            'Each item in `items` links the receipt to a specific obligation '
            'and records how much is applied to it.'
        ),
    )
    def post(self, request):
        serializer = CreateContributionReceiptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        receipt = serializer.save(created_by=request.user)
        return Response(
            ContributionReceiptSerializer(
                ContributionReceipt.objects
                .select_related('confirmed_by', 'created_by')
                .prefetch_related('items__obligation__member')
                .get(pk=receipt.pk)
            ).data,
            status=status.HTTP_201_CREATED,
        )


class InvestmentListCreateView(APIView):
    permission_classes = [IsAdminUser]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAnyAuthenticatedUser()]
        return [IsAdminUser()]

    def get(self, request):
        investments = Investment.objects.select_related('created_by').annotate(
            total_profit=Coalesce(
                Sum('profit_entries__amount'),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
        return Response(InvestmentSerializer(investments, many=True).data)

    @swagger_auto_schema(
        request_body=CreateInvestmentSerializer,
        responses={201: InvestmentSerializer},
        operation_summary='Create an investment',
        operation_description=(
            'Creates a new investment record and immediately records the matching '
            'CAPITAL debit ledger entry for the purchase.'
        ),
    )
    def post(self, request):
        serializer = CreateInvestmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        investment = serializer.save(created_by=request.user)
        from .ledger_service import record_investment_purchase
        record_investment_purchase(investment, request.user)
        return Response(
            InvestmentSerializer(
                Investment.objects.select_related('created_by').annotate(
                    total_profit=Coalesce(
                        Sum('profit_entries__amount'),
                        Decimal('0.00'),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                ).get(pk=investment.pk)
            ).data,
            status=status.HTTP_201_CREATED,
        )


class InvestmentProfitEntryCreateView(APIView):
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        request_body=CreateInvestmentProfitEntrySerializer,
        responses={201: InvestmentProfitEntrySerializer},
        operation_summary='Create an investment profit entry',
        operation_description=(
            'Records profit earned from an existing investment and immediately records '
            'the matching CAPITAL credit ledger entry.'
        ),
    )
    def post(self, request, pk):
        investment = get_object_or_404(Investment, pk=pk)
        serializer = CreateInvestmentProfitEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profit_entry = serializer.save(investment=investment, recorded_by=request.user)
        from .ledger_service import record_investment_profit
        record_investment_profit(profit_entry, request.user)
        return Response(
            InvestmentProfitEntrySerializer(
                InvestmentProfitEntry.objects.select_related('recorded_by', 'investment').get(pk=profit_entry.pk)
            ).data,
            status=status.HTTP_201_CREATED,
        )


class LoanProductListCreateView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        products = LoanProduct.objects.all()
        return Response(LoanProductSerializer(products, many=True).data)

    @swagger_auto_schema(
        request_body=LoanProductSerializer,
        responses={201: LoanProductSerializer},
        operation_summary='Create a loan product',
    )
    def post(self, request):
        serializer = LoanProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LoanProductArchiveView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        product = get_object_or_404(LoanProduct, pk=pk)
        if not product.is_active:
            return Response({'detail': 'Loan product is already archived.'}, status=status.HTTP_400_BAD_REQUEST)
        product.is_active = False
        product.save(update_fields=['is_active', 'updated_at'])
        return Response(LoanProductSerializer(product).data)


class LoanListCreateView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        loans = (
            Loan.objects
            .select_related('member', 'loan_product', 'created_by')
            .all()
        )
        return Response(LoanSerializer(loans, many=True).data)

    @swagger_auto_schema(
        request_body=CreateLoanSerializer,
        responses={201: LoanSerializer},
        operation_summary='Issue a loan to a member',
        operation_description=(
            'Creates a loan for a member. '
            'Snapshots the product\'s interest rate and duration. '
            'Total repayment = principal × (1 + rate/100). '
            'Monthly installment = total / duration_months. '
            'Principal is capped at member share count × 10,000.'
        ),
    )
    def post(self, request):
        serializer = CreateLoanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        loan = serializer.save(created_by=request.user)
        from .ledger_service import record_loan_disbursement
        record_loan_disbursement(loan, request.user)
        return Response(
            LoanSerializer(
                Loan.objects.select_related('member', 'loan_product', 'created_by').get(pk=loan.pk)
            ).data,
            status=status.HTTP_201_CREATED,
        )


class PenaltyListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        penalties = (
            Penalty.objects
            .select_related(
                'contribution_obligation__member',
                'contribution_obligation__contribution_cycle',
                'waived_by',
            )
            .all()
        )
        return Response(PenaltySerializer(penalties, many=True).data)


class FundAccountBalanceView(APIView):
    permission_classes = [IsAnyAuthenticatedUser]

    def get(self, request):
        accounts = FundAccount.objects.annotate(
            total_credits=Coalesce(
                Sum('ledger_entries__amount', filter=Q(ledger_entries__direction=LedgerEntry.Direction.CREDIT)),
                0,
                output_field=DecimalField(),
            ),
            total_debits=Coalesce(
                Sum('ledger_entries__amount', filter=Q(ledger_entries__direction=LedgerEntry.Direction.DEBIT)),
                0,
                output_field=DecimalField(),
            ),
        )

        data = [
            {
                'id':            str(account.id),
                'code':          account.code,
                'name':          account.name,
                'total_credits': account.total_credits,
                'total_debits':  account.total_debits,
                'balance':       account.total_credits - account.total_debits,
            }
            for account in accounts
        ]
        return Response(data)


class DashboardSummaryView(APIView):
    permission_classes = [IsAnyAuthenticatedUser]

    def get(self, request):
        loan_totals = Loan.objects.aggregate(
            total_loans_disbursed=Coalesce(
                Sum('principal_amount'),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            expected_interest=Coalesce(
                Sum(F('total_repayment_amount') - F('principal_amount')),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            total_loan_interest_paid=Coalesce(
                Sum('repayments__amount_paid'),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )

        ledger_totals = LedgerEntry.objects.aggregate(
            total_credit=Coalesce(
                Sum('amount', filter=Q(direction=LedgerEntry.Direction.CREDIT)),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            total_debit=Coalesce(
                Sum('amount', filter=Q(direction=LedgerEntry.Direction.DEBIT)),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )

        fund_balances = FundAccount.objects.annotate(
            total_credits=Coalesce(
                Sum('ledger_entries__amount', filter=Q(ledger_entries__direction=LedgerEntry.Direction.CREDIT)),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            total_debits=Coalesce(
                Sum('ledger_entries__amount', filter=Q(ledger_entries__direction=LedgerEntry.Direction.DEBIT)),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )

        balance_by_code = {
            account.code: account.total_credits - account.total_debits
            for account in fund_balances
        }

        socials = (
            balance_by_code.get(FundAccount.Code.SOCIAL, Decimal('0.00')) +
            balance_by_code.get(FundAccount.Code.SOCIAL_PLUS, Decimal('0.00'))
        )

        current_available = ledger_totals['total_credit'] - ledger_totals['total_debit']
        available_for_investment = current_available - socials

        loan_projection_totals = Loan.objects.annotate(
            total_repaid=Coalesce(
                Sum('repayments__amount_paid'),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        ).aggregate(
            outstanding_loan_repayments=Coalesce(
                Sum(F('total_repayment_amount') - F('total_repaid')),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )

        unpaid_penalties_total = Penalty.objects.filter(
            receipt__isnull=True,
            waived=False,
        ).aggregate(
            total=Coalesce(
                Sum('amount'),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )['total']

        investment_projection_total = Decimal('0.00')
        realized_profits = Decimal('0.00')
        investments = Investment.objects.annotate(
            total_profit=Coalesce(
                Sum('profit_entries__amount'),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        ).exclude(expected_interest_rate_percent__isnull=True)

        for investment in investments:
            realized_profits += investment.total_profit
            expected_maturity_value = investment.amount_invested + (
                investment.amount_invested * investment.expected_interest_rate_percent / Decimal('100')
            )
            investment_projection_total += expected_maturity_value - investment.total_profit

        expected_total = (
            current_available +
            loan_projection_totals['outstanding_loan_repayments'] +
            unpaid_penalties_total +
            investment_projection_total
        )

        data = {
            'total_loans_disbursed': loan_totals['total_loans_disbursed'],
            'expected_interest': loan_totals['expected_interest'],
            'total_loan_interest_paid': loan_totals['total_loan_interest_paid'],
            'fund_summary': {
                'total_credit': ledger_totals['total_credit'],
                'total_debit': ledger_totals['total_debit'],
                'current_available': current_available,
                'realized_profits': realized_profits.quantize(Decimal('0.01')),
                'expected_total': expected_total.quantize(Decimal('0.01')),
                'available_for_investment': available_for_investment.quantize(Decimal('0.01')),
            },
        }
        return Response(data)


class MemberSummaryView(APIView):
    permission_classes = [IsAnyAuthenticatedUser]

    def get(self, request):
        member = getattr(request.user, 'member', None)
        if member is None:
            return Response(
                {'detail': 'No member account linked to this user.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        total_contributions = (
            ContributionReceiptItem.objects
            .filter(
                obligation__member=member,
                receipt__status=ContributionReceipt.Status.CONFIRMED,
            )
            .aggregate(total=Coalesce(
                Sum('amount_applied'),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ))['total']
        )

        active_loans_agg = Loan.objects.filter(
            member=member, status=Loan.Status.ACTIVE
        ).aggregate(
            count=Count('id'),
            total_amount=Coalesce(
                Sum('principal_amount'),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )

        total_penalties = (
            Penalty.objects
            .filter(contribution_obligation__member=member, waived=False)
            .aggregate(total=Coalesce(
                Sum('amount'),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ))['total']
        )

        return Response({
            'total_contributions': total_contributions,
            'active_loans': active_loans_agg['count'],
            'active_loan_amount': active_loans_agg['total_amount'],
            'total_penalties': total_penalties,
        })
