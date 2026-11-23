from django.test import TestCase
from rest_framework.test import APIClient
from .models import Area, AreaComment, Cycle, RoleAssignment, User


class AreaCollaborationTests(TestCase):
    def setUp(self):
        self.cycle = Cycle.objects.create(title='Cycle', status='active')
        self.area = Area.objects.create(cycle=self.cycle, code='A', title='Area')
        self.coordinator = User.objects.create_user(username='coord', email='coord@example.test')
        self.viewer = User.objects.create_user(username='viewer', email='viewer@example.test')
        self.other = User.objects.create_user(username='other', email='other@example.test')
        RoleAssignment.objects.create(user=self.coordinator, cycle=self.cycle, role='coordinator')
        self.client = APIClient()
        self.client.force_authenticate(self.coordinator)

    def test_assignment_visibility_and_access_boundaries(self):
        url = f'/api/areas/{self.area.pk}/access/'
        grant = {'user': self.viewer.pk, 'role': 'viewer', 'action': 'add', 'reason': 'Area access'}
        self.assertEqual(self.client.post(url, grant, format='json').status_code, 200)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(len(self.client.get('/api/areas/').data), 1)
        self.assertEqual(self.client.post(url, grant, format='json').status_code, 403)
        self.client.force_authenticate(self.coordinator)
        self.assertEqual(self.client.post(url, {**grant, 'user': self.coordinator.pk}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url, {**grant, 'role': 'coordinator'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url, {**grant, 'action': 'remove'}, format='json').status_code, 200)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(len(self.client.get('/api/areas/').data), 0)

    def test_comments_are_viewer_written_and_area_scoped(self):
        RoleAssignment.objects.create(user=self.viewer, cycle=self.cycle, area=self.area, role='viewer')
        url = f'/api/areas/{self.area.pk}/comments/'
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.post(url, {'text': 'Please review'}, format='json').status_code, 201)
        self.client.force_authenticate(self.coordinator)
        self.assertEqual(self.client.get(url).data[0]['text'], 'Please review')
        self.assertEqual(self.client.post(url, {'text': 'Not a viewer'}, format='json').status_code, 404)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(AreaComment.objects.count(), 1)
