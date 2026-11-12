from unittest import skipUnless
from unittest.mock import patch

from django.db import connection
from django.urls import reverse
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from .models import Member, MemberNationalID, MemberShareAccount, User
from .serializers import CreateMemberSerializer


class MemberNationalIDTests(APITestCase):
    nid = '0123456789012345'
    other_nid = '9876543210987654'

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(email='admin-nid@example.com', full_name='Admin')
        cls.member = Member.objects.create(first_name='Existing', last_name='Member')

    def setUp(self):
        self.client.force_authenticate(self.admin)
        self.members_url = reverse('member_list_create')
        self.detail_url = reverse('member_detail', args=[self.member.pk])
        self.payload = {
            'first_name': 'New',
            'last_name': 'Member',
            'email': 'new-nid@example.com',
            'default_password': 'TestPassword-2!',
        }

    def test_create_with_nid_preserves_leading_zero(self):
        response = self.client.post(self.members_url, {**self.payload, 'nid': self.nid}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn('nid', response.data)
        member = Member.objects.get(pk=response.data['id'])
        self.assertEqual(member.national_id.nid, self.nid)
        self.assertEqual(member.user.role, User.Role.VIEWER)
        self.assertEqual(member.share_account.share_count, 0)

        detail = self.client.get(reverse('member_detail', args=[member.pk]))
        self.assertEqual(detail.data['nid'], self.nid)
        self.assertIn('no-store', detail['Cache-Control'])

    def test_create_without_nid_and_read_existing_member(self):
        response = self.client.post(self.members_url, self.payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(MemberNationalID.objects.filter(member_id=response.data['id']).exists())
        self.assertIsNone(self.client.get(self.detail_url).data['nid'])

    def test_invalid_nid_returns_field_error(self):
        for nid in ('', '123456789012345', self.nid + '0', self.nid + '\n', '٠' * 16, 1234567890123456):
            with self.subTest(nid=nid):
                created = self.client.post(self.members_url, {**self.payload, 'nid': nid}, format='json')
                self.assertEqual(created.status_code, 400)
                self.assertIn('nid', created.data)
                updated = self.client.patch(self.detail_url, {'nid': nid}, format='json')
                self.assertEqual(updated.status_code, 400)
                self.assertIn('nid', updated.data)
        self.assertFalse(Member.objects.filter(email=self.payload['email']).exists())
        self.assertIsNone(self.client.get(self.detail_url).data['nid'])

    def test_set_correct_and_clear_nid(self):
        for nid in (self.nid, self.nid, self.other_nid, None):
            response = self.client.patch(self.detail_url, {'nid': nid}, format='json')
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['nid'], nid)
            self.assertIn('no-store', response['Cache-Control'])
            self.assertEqual(self.client.get(self.detail_url).data['nid'], nid)
        self.assertFalse(MemberNationalID.objects.filter(member=self.member).exists())

    def test_duplicate_nid_is_rejected_on_create_and_patch(self):
        MemberNationalID.objects.create(member=self.member, nid=self.nid)
        other_member = Member.objects.create(first_name='Other', last_name='Member')
        MemberNationalID.objects.create(member=other_member, nid=self.other_nid)
        create = self.client.post(self.members_url, {**self.payload, 'nid': self.nid}, format='json')
        update = self.client.patch(self.detail_url, {'nid': self.other_nid}, format='json')
        for response in (create, update):
            self.assertEqual(response.status_code, 400)
            self.assertIn('nid', response.data)
        self.assertEqual(self.client.get(self.detail_url).data['nid'], self.nid)

    def test_provisioning_failure_rolls_back_new_member_and_user(self):
        with patch.object(MemberShareAccount.objects, 'create', side_effect=RuntimeError('Share setup failed')):
            with self.assertRaisesMessage(RuntimeError, 'Share setup failed'):
                self.client.post(self.members_url, {**self.payload, 'nid': self.nid}, format='json')
        self.assertFalse(Member.objects.filter(email=self.payload['email']).exists())
        self.assertFalse(User.objects.filter(email=self.payload['email']).exists())
        self.assertFalse(MemberNationalID.objects.filter(nid=self.nid).exists())

    @skipUnless(connection.vendor == 'postgresql', 'Checks PostgreSQL constraint diagnostics.')
    def test_nid_taken_after_validation_returns_field_error_and_rolls_back(self):
        serializer = CreateMemberSerializer(data={**self.payload, 'nid': self.nid})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        MemberNationalID.objects.create(member=self.member, nid=self.nid)
        with self.assertRaises(ValidationError) as error:
            serializer.save()
        self.assertIn('nid', error.exception.detail)
        self.assertFalse(Member.objects.filter(email=self.payload['email']).exists())
        self.assertFalse(User.objects.filter(email=self.payload['email']).exists())

    @skipUnless(connection.vendor == 'postgresql', 'Checks PostgreSQL table permissions.')
    def test_nid_table_is_private(self):
        table = MemberNationalID._meta.db_table
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT relrowsecurity, EXISTS (
                    SELECT 1 FROM aclexplode(relacl) WHERE grantee = 0
                )
                FROM pg_class WHERE oid = %s::regclass
                """,
                [table],
            )
            self.assertEqual(cursor.fetchone(), (True, False))
            cursor.execute(
                """
                SELECT rolname FROM pg_roles
                WHERE rolname IN ('anon', 'authenticated', 'service_role')
                  AND has_table_privilege(oid, %s, 'SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER')
                """,
                [table],
            )
            self.assertEqual(cursor.fetchall(), [])

    def test_nid_is_omitted_from_other_responses_and_admin_access_is_required(self):
        MemberNationalID.objects.create(member=self.member, nid=self.nid)
        members = self.client.get(self.members_url).data
        self.assertTrue(all('nid' not in member for member in members))
        contributions = self.client.get(reverse('member_contributions', args=[self.member.pk]))
        self.assertNotIn('nid', contributions.data['member'])

        viewer = User.objects.create_user(email='viewer-nid@example.com', role=User.Role.VIEWER, member=self.member)
        operator = User.objects.create_user(email='operator-nid@example.com', role=User.Role.OPERATOR)
        for user, expected_status in ((None, 401), (viewer, 403), (operator, 403)):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get(self.detail_url).status_code, expected_status)
            self.assertEqual(self.client.patch(self.detail_url, {'nid': None}, format='json').status_code, expected_status)
            self.assertEqual(self.client.post(self.members_url, self.payload, format='json').status_code, expected_status)

        self.client.force_authenticate(viewer)
        for endpoint in ('me', 'member_me_summary', 'member_me_contributions', 'member_me_loans', 'member_me_penalties'):
            response = self.client.get(reverse(endpoint))
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, self.nid)

    def test_django_admin_can_add_correct_and_delete_nid(self):
        self.client.force_login(self.admin)
        url = reverse('admin:core_member_change', args=[self.member.pk])
        form = {
            'first_name': self.member.first_name,
            'last_name': self.member.last_name,
            'status': self.member.status,
            'join_date': self.member.join_date.strftime('%Y-%m-%d'),
            'national_id-TOTAL_FORMS': '1',
            'national_id-INITIAL_FORMS': '0',
            'national_id-0-nid': self.nid,
        }
        self.assertEqual(self.client.post(url, form).status_code, 302)
        self.assertContains(self.client.get(url), self.nid)

        form.update({
            'national_id-INITIAL_FORMS': '1',
            'national_id-0-member': str(self.member.pk),
            'national_id-0-nid': self.other_nid,
        })
        self.assertEqual(self.client.post(url, form).status_code, 302)
        self.assertContains(self.client.get(url), self.other_nid)

        form['national_id-0-DELETE'] = 'on'
        self.assertEqual(self.client.post(url, form).status_code, 302)
        self.assertFalse(MemberNationalID.objects.filter(member=self.member).exists())
