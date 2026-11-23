from django.db import transaction
from django.test import TestCase
from .models import Notification, RequirementAssignment, RoleAssignment
from .notifications import notify, notify_reviewers
from .tests import WorkflowFixture


class NotificationTests(WorkflowFixture, TestCase):
    def test_assignment_inbox_and_revocation(self):
        colleague = self.user('custodian', self.area, 'colleague')
        self.client.force_authenticate(self.coordinator)
        response = self.client.post(f'/api/requirements/{self.requirement.pk}/assignments/',
                                    {'user': colleague.pk, 'reason': 'New responsibility'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.client.force_authenticate(colleague)
        inbox = self.client.get('/api/notifications/').data
        self.assertEqual(inbox['unread_count'], 1)
        notification_id = inbox['results'][0]['id']
        self.assertEqual(self.client.post(f'/api/notifications/{notification_id}/read/').status_code, 204)
        self.assertEqual(self.client.get('/api/notifications/').data['unread_count'], 0)
        RoleAssignment.objects.filter(user=colleague, role='custodian').delete()
        RoleAssignment.objects.create(user=colleague, cycle=self.cycle, area=self.area, role='viewer')
        self.assertEqual(self.client.get('/api/notifications/').data['results'], [])
        self.assertEqual(self.client.post(f'/api/notifications/{notification_id}/read/').status_code, 404)

    def test_legacy_review_and_completion_notifications(self):
        document = self.upload()
        submission = self.submit(document)
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.client.get('/api/notifications/').data['results'][0]['kind'], 'review_requested')
        self.assertEqual(self.decide(submission).status_code, 201)
        self.client.force_authenticate(self.custodian)
        self.assertEqual(self.client.get('/api/notifications/').data['results'][0]['kind'], 'review_decided')
        self.client.force_authenticate(self.coordinator)
        self.assertIn('ready_for_completion', [n['kind'] for n in self.client.get('/api/notifications/').data['results']])
        self.assertEqual(self.certify().status_code, 201)
        self.client.force_authenticate(self.custodian)
        self.assertEqual(self.client.get('/api/notifications/').data['results'][0]['kind'], 'requirement_completed')
        self.assertEqual(self.client.post('/api/notifications/read-all/').status_code, 204)
        self.assertEqual(self.client.get('/api/notifications/').data['unread_count'], 0)

    def test_scope_deduplication_self_exclusion_and_rollback(self):
        notify(self.requirement, [self.custodian, self.custodian, self.coordinator], self.coordinator, 'assigned', 'test:1')
        self.assertEqual(Notification.objects.filter(event_key='test:1').count(), 1)
        notify_reviewers(self.requirement, self.reviewer, 'test:review')
        self.assertFalse(Notification.objects.filter(event_key='test:review', recipient=self.reviewer).exists())
        self.assertFalse(Notification.objects.filter(event_key='test:review', recipient=self.outsider).exists())
        try:
            with transaction.atomic():
                notify(self.requirement, [self.custodian], self.coordinator, 'assigned', 'test:rollback')
                raise ValueError()
        except ValueError:
            pass
        self.assertFalse(Notification.objects.filter(event_key='test:rollback').exists())

    def test_package_review_notifications_and_self_review_exclusion(self):
        self.requirement.legacy_submission_mode = False
        self.requirement.save(update_fields=['legacy_submission_mode'])
        document = self.upload()
        mapping = self.client.post('/api/evidence-mappings/', {'item': self.item.pk, 'document': document['id']}, format='json')
        self.assertEqual(mapping.status_code, 201)
        draft = self.client.post('/api/packages/', {'requirement': self.requirement.pk,
            'items': [{'mapping': mapping.data['id'], 'version': document['versions'][0]['id']}]}, format='json')
        self.assertEqual(draft.status_code, 201)
        RoleAssignment.objects.create(user=self.custodian, cycle=self.cycle, area=self.area, role='reviewer')
        self.assertEqual(self.client.post(f'/api/packages/{draft.data["id"]}/submit/', {}, format='json').status_code, 200)
        self.assertFalse(Notification.objects.filter(recipient=self.custodian, kind='review_requested').exists())
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.client.get('/api/notifications/').data['results'][0]['kind'], 'review_requested')
        response = self.client.post(f'/api/packages/{draft.data["id"]}/review/', {'outcome': 'revisions_requested', 'comment': 'Please revise'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.client.force_authenticate(self.custodian)
        self.assertEqual(self.client.get('/api/notifications/').data['results'][0]['kind'], 'review_decided')
