from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ContributionReceipt, Member, MemberContributionObligation, MemberShareAccount
from .permissions import IsAdminUser
from .serializers import (
    AdjustSharesSerializer,
    ContributionReceiptSerializer,
    CreateContributionReceiptSerializer,
    CreateMemberSerializer,
    MemberContributionObligationSerializer,
    MemberSerializer,
    MemberShareAccountSerializer,
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
            account.share_count -= amount
        else:
            account.share_count += amount

        account.save(update_fields=['share_count', 'updated_at'])
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
