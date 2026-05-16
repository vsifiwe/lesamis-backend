from datetime import date
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    ContributionCycle,
    ContributionReceipt,
    ContributionReceiptItem,
    Loan,
    LoanProduct,
    LoanRepayment,
    Member,
    MemberContributionObligation,
    MemberShareAccount,
    Penalty,
    User,
)


class MemberDashboardEndpointTests(APITestCase):
    def setUp(self):
        self.member = Member.objects.create(
            first_name='Alice',
            last_name='Member',
            email='alice@example.com',
            join_date=date(2024, 1, 1),
        )
        MemberShareAccount.objects.create(member=self.member, share_count=4)
        self.user = User.objects.create_user(
            email='alice@example.com',
            password='test-password',
            full_name='Alice Member',
            role=User.Role.VIEWER,
            member=self.member,
        )

        self.other_member = Member.objects.create(
            first_name='Bob',
            last_name='Member',
            email='bob@example.com',
            join_date=date(2024, 1, 1),
        )
        MemberShareAccount.objects.create(member=self.other_member, share_count=2)
        self.other_user = User.objects.create_user(
            email='bob@example.com',
            password='test-password',
            full_name='Bob Member',
            role=User.Role.VIEWER,
            member=self.other_member,
        )

        self.admin_without_member = User.objects.create_user(
            email='admin@example.com',
            password='test-password',
            full_name='Admin User',
            role=User.Role.ADMIN,
        )

        self.cycle, _ = ContributionCycle.objects.get_or_create(
            year=2024,
            month=1,
            defaults={
                'due_date': date(2024, 1, 10),
                'late_penalty_start_date': date(2024, 1, 11),
                'extra_penalty_start_date': date(2024, 1, 21),
                'share_unit_value': 10000,
            },
        )
        self.other_cycle, _ = ContributionCycle.objects.get_or_create(
            year=2024,
            month=2,
            defaults={
                'due_date': date(2024, 2, 10),
                'late_penalty_start_date': date(2024, 2, 11),
                'extra_penalty_start_date': date(2024, 2, 21),
                'share_unit_value': 10000,
            },
        )

        self.obligation = self._create_obligation(self.member, self.cycle, 45000)
        self.other_obligation = self._create_obligation(self.other_member, self.other_cycle, 70000)

        self.receipt = ContributionReceipt.objects.create(
            amount_received=Decimal('45000.00'),
            received_date=date(2024, 1, 9),
            payment_method=ContributionReceipt.PaymentMethod.BANK,
            status=ContributionReceipt.Status.CONFIRMED,
            confirmed_by=self.user,
            created_by=self.user,
        )
        ContributionReceiptItem.objects.create(
            receipt=self.receipt,
            obligation=self.obligation,
            amount_applied=Decimal('45000.00'),
        )
        self.obligation.status = MemberContributionObligation.Status.CONFIRMED
        self.obligation.save(update_fields=['status'])

        other_receipt = ContributionReceipt.objects.create(
            amount_received=Decimal('70000.00'),
            received_date=date(2024, 2, 9),
            payment_method=ContributionReceipt.PaymentMethod.CASH,
            status=ContributionReceipt.Status.CONFIRMED,
            confirmed_by=self.other_user,
            created_by=self.other_user,
        )
        ContributionReceiptItem.objects.create(
            receipt=other_receipt,
            obligation=self.other_obligation,
            amount_applied=Decimal('70000.00'),
        )
        self.other_obligation.status = MemberContributionObligation.Status.CONFIRMED
        self.other_obligation.save(update_fields=['status'])

        loan_product = LoanProduct.objects.create(
            name='Standard',
            duration_months=10,
            interest_rate_percent=Decimal('10.00'),
        )
        self.loan = Loan.objects.create(
            member=self.member,
            loan_product=loan_product,
            principal_amount=Decimal('100000.00'),
            interest_rate_percent_snapshot=Decimal('10.00'),
            duration_months_snapshot=10,
            total_repayment_amount=Decimal('110000.00'),
            monthly_installment_amount=Decimal('11000.00'),
            issued_date=date(2024, 1, 15),
            first_due_date=date(2024, 2, 15),
            created_by=self.user,
        )
        LoanRepayment.objects.create(
            loan=self.loan,
            amount_paid=Decimal('25000.00'),
            paid_date=date(2024, 2, 15),
            payment_method=LoanRepayment.PaymentMethod.BANK,
            recorded_by=self.user,
        )
        Loan.objects.create(
            member=self.other_member,
            loan_product=loan_product,
            principal_amount=Decimal('300000.00'),
            interest_rate_percent_snapshot=Decimal('10.00'),
            duration_months_snapshot=10,
            total_repayment_amount=Decimal('330000.00'),
            monthly_installment_amount=Decimal('33000.00'),
            issued_date=date(2024, 1, 20),
            first_due_date=date(2024, 2, 20),
            created_by=self.other_user,
        )

        Penalty.objects.create(
            contribution_obligation=self.obligation,
            penalty_type=Penalty.PenaltyType.LATE_PENALTY,
            amount=Decimal('5000.00'),
            reason='Late payment',
        )
        Penalty.objects.create(
            contribution_obligation=self.other_obligation,
            penalty_type=Penalty.PenaltyType.MANUAL,
            amount=Decimal('9000.00'),
            reason='Other member penalty',
        )

    def _create_obligation(self, member, cycle, total_amount):
        return MemberContributionObligation.objects.create(
            member=member,
            contribution_cycle=cycle,
            obligation_type=MemberContributionObligation.ObligationType.CONTRIBUTION,
            share_count_snapshot=1,
            share_unit_value_snapshot=10000,
            capital_amount_expected=total_amount - 5000,
            social_amount_expected=2000,
            social_plus_amount_expected=3000,
            total_amount_expected=total_amount,
            status=MemberContributionObligation.Status.EXPECTED,
        )

    def authenticate_as(self, user):
        self.client.force_authenticate(user=user)

    def test_me_includes_linked_member_metadata(self):
        self.authenticate_as(self.user)

        response = self.client.get('/api/v1/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['full_name'], 'Alice Member')
        self.assertEqual(response.data['role'], 'Member')
        self.assertEqual(response.data['member_id'], str(self.member.id))
        self.assertEqual(response.data['member_number'], self.member.member_number)
        self.assertTrue(response.data['has_member_profile'])

    def test_unlinked_admin_gets_explicit_profile_state_and_forbidden_dashboard_data(self):
        self.authenticate_as(self.admin_without_member)

        me_response = self.client.get('/api/v1/me/')
        summary_response = self.client.get('/api/v1/me/summary/')

        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data['role'], 'Admin')
        self.assertIsNone(me_response.data['member_id'])
        self.assertIsNone(me_response.data['member_number'])
        self.assertFalse(me_response.data['has_member_profile'])
        self.assertEqual(summary_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            summary_response.data['detail'],
            'No member account linked to this user.',
        )

    def test_member_summary_is_self_scoped(self):
        self.authenticate_as(self.user)

        response = self.client.get('/api/v1/me/summary/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_contributions'], Decimal('45000.00'))
        self.assertEqual(response.data['active_loans'], 1)
        self.assertEqual(response.data['active_loan_amount'], Decimal('100000.00'))
        self.assertEqual(response.data['total_penalties'], Decimal('5000.00'))

    def test_member_contributions_are_self_scoped(self):
        self.authenticate_as(self.user)

        response = self.client.get('/api/v1/me/contributions/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['received']), 1)
        self.assertEqual(response.data['received'][0]['amount_applied'], '45000.00')
        self.assertEqual(response.data['pending'], [])
        self.assertEqual(response.data['purchases'], [])

    def test_member_loans_are_self_scoped_with_payment_totals(self):
        self.authenticate_as(self.user)

        response = self.client.get('/api/v1/me/loans/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['principal_amount'], '100000.00')
        self.assertEqual(response.data[0]['total_paid'], '25000.00')
        self.assertEqual(response.data[0]['outstanding_amount'], Decimal('85000.00'))

    def test_member_penalties_are_self_scoped(self):
        self.authenticate_as(self.user)

        response = self.client.get('/api/v1/me/penalties/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['amount'], '5000.00')
        self.assertEqual(response.data[0]['cycle_year'], 2024)
        self.assertEqual(response.data[0]['cycle_month'], 1)


class ReceiptPaginationEndpointTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='receipt-admin@example.com',
            password='test-password',
            full_name='Receipt Admin',
            role=User.Role.ADMIN,
        )
        for index in range(3):
            ContributionReceipt.objects.create(
                amount_received=Decimal('1000.00') + index,
                received_date=date(2099, 1, index + 1),
                payment_method=ContributionReceipt.PaymentMethod.BANK,
                status=ContributionReceipt.Status.CONFIRMED,
                confirmed_by=self.admin,
                created_by=self.admin,
            )

    def test_receipts_are_cursor_paginated(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get('/api/v1/receipts/?page_size=2')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 2)
        self.assertIsNone(response.data['previous'])
        self.assertIsNotNone(response.data['next'])
