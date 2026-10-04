import io
import json
import tempfile
from pathlib import Path

from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings

from .access import areas_for
from .models import Area, AuditEvent, Cycle, RoleAssignment, User


class AdminHardeningTests(TestCase):
    def setUp(self):
        self.account_admin = User.objects.create_user('account.admin', 'account.admin@test.invalid', 'Synthetic-test-123', is_staff=True)
        self.grant_operator = User.objects.create_user('grant.operator', 'grant.operator@test.invalid', 'Synthetic-test-123', is_staff=True)
        self.cycle_operator = User.objects.create_user('cycle.operator', 'cycle.operator@test.invalid', 'Synthetic-test-123', is_staff=True)
        self.credential_operator = User.objects.create_user('credential.operator', 'credential.operator@test.invalid', 'Synthetic-test-123', is_staff=True)
        self.target = User.objects.create_user('ordinary', 'ordinary@test.invalid', 'Synthetic-test-123')
        self.cycle = Cycle.objects.create(title='Synthetic cycle', status='active')
        self.area = Area.objects.create(cycle=self.cycle, code='A1', title='Synthetic area')
        self.other_cycle = Cycle.objects.create(title='Other synthetic cycle', status='active')
        self.other_area = Area.objects.create(cycle=self.other_cycle, code='B1', title='Other synthetic area')
        for codename in ('add_user', 'change_user', 'view_user'):
            self.account_admin.user_permissions.add(Permission.objects.get(content_type__app_label='hub', codename=codename))
        self.grant_operator.user_permissions.add(Permission.objects.get(content_type__app_label='hub', codename='manage_role_grants'))
        self.cycle_operator.user_permissions.add(Permission.objects.get(content_type__app_label='hub', codename='provision_cycle'))
        for codename in ('view_user', 'reset_user_password'):
            self.credential_operator.user_permissions.add(Permission.objects.get(content_type__app_label='hub', codename=codename))
        self.client = Client()
        self.client.force_login(self.account_admin)
        AuditEvent.objects.all().delete()

    def account_url(self, user):
        return f'/api/admin/hub/user/{user.pk}/change/'

    def test_routine_add_forgery_creates_unusable_ordinary_account_with_one_reasoned_event(self):
        response = self.client.post('/api/admin/hub/user/add/', {
            'username': 'new.user', 'email': 'new.user@test.invalid', 'first_name': 'New',
            'last_name': 'User', 'department': 'Synthetic', 'is_active': 'on',
            'is_staff': 'on', 'is_superuser': 'on', 'password': 'Forged-password-123',
            'groups': '1', 'user_permissions': '1', 'reason': 'Synthetic intake', '_save': 'Save',
        })
        self.assertEqual(response.status_code, 302, response.context)
        created = User.objects.get(username='new.user')
        self.assertFalse(created.has_usable_password())
        self.assertFalse(created.is_staff)
        self.assertFalse(created.is_superuser)
        self.assertFalse(created.groups.exists())
        self.assertFalse(created.user_permissions.exists())
        event = AuditEvent.objects.get(action='account_created', record=f'user:{created.pk}')
        self.assertEqual(event.actor, self.account_admin)
        self.assertEqual(event.detail['reason'], 'Synthetic intake')
        self.assertNotIn('password', str(event.detail).lower())
        self.assertEqual(AuditEvent.objects.count(), 1)

    def test_account_change_deactivation_self_and_privileged_targets(self):
        data = {'username': self.target.username, 'email': self.target.email,
                'first_name': 'Updated', 'last_name': '', 'department': '',
                'is_staff': 'on', 'is_superuser': 'on', 'password': 'Forged',
                'reason': 'Synthetic deactivation', '_save': 'Save'}
        response = self.client.post(self.account_url(self.target), data)
        self.assertEqual(response.status_code, 302)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)
        self.assertFalse(self.target.is_staff)
        self.assertEqual(self.target.first_name, 'Updated')
        self.assertEqual(AuditEvent.objects.filter(action='account_updated').count(), 1)
        self.assertEqual(self.client.post(self.account_url(self.account_admin), data).status_code, 403)
        self.assertEqual(self.client.post(self.account_url(self.grant_operator), data).status_code, 403)
        RoleAssignment.objects.create(user=self.target, cycle=self.cycle, role='administrator')
        self.target.is_active = True
        self.target.save(update_fields=['is_active'])
        AuditEvent.objects.all().delete()
        self.assertEqual(self.client.post(self.account_url(self.target), data).status_code, 403)
        self.assertEqual(AuditEvent.objects.count(), 0)
        self.assertEqual(self.client.post(f'/api/admin/hub/roleassignment/{self.target.assignments.get().pk}/change/', {'role': 'coordinator'}).status_code, 403)

    def test_reason_required_and_password_route_separately_permitted(self):
        data = {'username': self.target.username, 'email': self.target.email, 'is_active': 'on', 'reason': '   '}
        self.assertEqual(self.client.post(self.account_url(self.target), data).status_code, 200)
        self.assertEqual(AuditEvent.objects.count(), 0)
        password_url = f'/api/admin/hub/user/{self.target.pk}/password/'
        self.assertEqual(self.client.get(password_url).status_code, 403)
        self.client.force_login(self.credential_operator)
        self.assertEqual(self.client.get(password_url).status_code, 200)
        self.assertEqual(self.client.post(password_url, {'new_password1': 'Another-synthetic-123', 'new_password2': 'Another-synthetic-123', 'reason': '  '}).status_code, 200)
        self.assertEqual(AuditEvent.objects.count(), 0)
        self.assertEqual(self.client.post(password_url, {'new_password1': 'Another-synthetic-123', 'new_password2': 'Another-synthetic-123', 'reason': 'Verified synthetic case'}).status_code, 302)
        self.target.refresh_from_db()
        self.assertTrue(self.target.check_password('Another-synthetic-123'))
        event = AuditEvent.objects.get()
        self.assertEqual(event.action, 'account_password_set')
        self.assertEqual(event.detail, {'reason': 'Verified synthetic case'})
        self.assertEqual(self.client.get(self.account_url(self.target)).status_code, 200)
        self.assertEqual(self.client.post(self.account_url(self.target), data).status_code, 403)
        self.assertEqual(self.client.get(f'/api/admin/hub/user/{self.grant_operator.pk}/password/').status_code, 403)

    def test_break_glass_permission_edit_has_one_reasoned_event(self):
        superuser = User.objects.create_superuser('synthetic.breakglass', 'synthetic.breakglass@test.invalid', 'Synthetic-test-123')
        AuditEvent.objects.all().delete()
        self.client.force_login(superuser)
        permission = Permission.objects.get(content_type__app_label='hub', codename='view_security_audit')
        response = self.client.post(self.account_url(self.target), {
            'username': self.target.username, 'email': self.target.email,
            'is_active': 'on', 'user_permissions': [str(permission.pk)],
            'reason': 'Synthetic break-glass ticket', '_save': 'Save',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.target.user_permissions.filter(pk=permission.pk).exists())
        self.assertEqual(AuditEvent.objects.count(), 1)
        self.assertEqual(AuditEvent.objects.get().detail['reason'], 'Synthetic break-glass ticket')

    def test_account_identifier_collision_is_rejected(self):
        response = self.client.post('/api/admin/hub/user/add/', {
            'username': self.target.email, 'email': 'collision@test.invalid',
            'is_active': 'on', 'reason': 'Synthetic collision check', '_save': 'Save',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='collision@test.invalid').exists())
        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_grant_add_revoke_scope_permissions_and_access_loss(self):
        args = dict(actor_id=self.grant_operator.pk, target_id=self.target.pk,
                    cycle_id=self.cycle.pk, role='reviewer', area_id=self.area.pk,
                    reason='Synthetic scope approval')
        with self.assertRaises(CommandError):
            call_command('manage_grant', action='add', **{**args, 'actor_id': self.account_admin.pk}, stdout=io.StringIO())
        with self.assertRaises(CommandError):
            call_command('manage_grant', action='add', **{**args, 'reason': ' '}, stdout=io.StringIO())
        with self.assertRaises(CommandError):
            call_command('manage_grant', action='add', **{**args, 'target_id': self.grant_operator.pk}, stdout=io.StringIO())
        with self.assertRaises(CommandError):
            call_command('manage_grant', action='add', **{**args, 'role': 'administrator'}, stdout=io.StringIO())
        with self.assertRaises(CommandError):
            call_command('manage_grant', action='add', **{**args, 'area_id': None}, stdout=io.StringIO())
        with self.assertRaises(CommandError):
            call_command('manage_grant', action='add', **{**args, 'area_id': self.other_area.pk}, stdout=io.StringIO())
        self.assertEqual(AuditEvent.objects.count(), 0)
        call_command('manage_grant', action='add', **args, stdout=io.StringIO())
        self.assertEqual(RoleAssignment.objects.count(), 1)
        self.assertTrue(areas_for(self.target).filter(pk=self.area.pk).exists())
        signed_in = Client()
        signed_in.force_login(self.target)
        self.assertEqual([row['id'] for row in signed_in.get('/api/areas/').json()], [self.area.pk])
        self.assertEqual(AuditEvent.objects.count(), 1)
        with self.assertRaises(CommandError):
            call_command('manage_grant', action='add', **args, stdout=io.StringIO())
        self.assertEqual(AuditEvent.objects.count(), 1)
        call_command('manage_grant', action='revoke', **args, stdout=io.StringIO())
        self.assertFalse(areas_for(self.target).exists())
        self.assertEqual(signed_in.get('/api/areas/').json(), [])
        self.assertEqual(RoleAssignment.objects.count(), 0)
        self.assertEqual(AuditEvent.objects.count(), 2)
        with self.assertRaises(CommandError):
            call_command('manage_grant', action='revoke', **args, stdout=io.StringIO())
        self.assertEqual(AuditEvent.objects.count(), 2)

    def test_cycle_provisioning_atomic_and_permissioned(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = Path(directory) / 'cycle.json'
            payload.write_text(json.dumps({'title': 'New synthetic cycle', 'program': 'Graduate School',
                'instrument': 'Synthetic instrument', 'areas': [{'code': 'A1', 'title': 'One'}, {'code': 'A1', 'title': 'Two'}]}))
            with self.assertRaises(CommandError):
                call_command('create_cycle', str(payload), actor_id=self.cycle_operator.pk, reason='Synthetic launch', stdout=io.StringIO())
            self.assertFalse(Cycle.objects.filter(title='New synthetic cycle').exists())
            self.assertEqual(AuditEvent.objects.count(), 0)
            payload.write_text(json.dumps({'title': 'New synthetic cycle', 'program': 'Graduate School',
                'instrument': 'Synthetic instrument', 'areas': [{'code': 'A1', 'title': 'One'}]}))
            with self.assertRaises(CommandError):
                call_command('create_cycle', str(payload), actor_id=self.grant_operator.pk, reason='Synthetic launch', stdout=io.StringIO())
            with self.assertRaises(CommandError):
                call_command('create_cycle', str(payload), actor_id=self.cycle_operator.pk, reason=' ', stdout=io.StringIO())
            call_command('create_cycle', str(payload), actor_id=self.cycle_operator.pk, reason='Synthetic launch', stdout=io.StringIO())
            self.assertEqual(Cycle.objects.get(title='New synthetic cycle').areas.count(), 1)
            event = AuditEvent.objects.get()
            self.assertEqual(event.action, 'cycle_provisioned')
            self.assertEqual(event.detail['reason'], 'Synthetic launch')
            self.assertEqual(len(event.detail['areas']), 1)

    @override_settings(RESTRICTED_TEST_MODE=True, TEST_TRUSTED_PROXY_NETWORKS='127.0.0.1/32', TEST_ADMIN_NETWORKS='10.20.0.0/16')
    def test_admin_network_boundary_and_role_separation(self):
        outside = Client(REMOTE_ADDR='127.0.0.1', HTTP_X_FORWARDED_FOR='10.21.1.5', HTTP_X_FORWARDED_PROTO='https')
        inside = Client(REMOTE_ADDR='127.0.0.1', HTTP_X_FORWARDED_FOR='10.20.1.5', HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(outside.get('/api/admin/login/').status_code, 404)
        self.assertEqual(inside.get('/api/admin/login/').status_code, 200)
        self.assertFalse(areas_for(self.account_admin).exists())
        self.assertFalse(areas_for(self.grant_operator).exists())
