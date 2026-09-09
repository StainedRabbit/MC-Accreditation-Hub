import io
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from rest_framework.test import APIClient
from pypdf import PdfWriter
from .models import *


def pdf_file(name='evidence.pdf'):
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(output)
    return SimpleUploadedFile(name, output.getvalue(), content_type='application/pdf')


class WorkflowFixture:
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(PRIVATE_MEDIA_ROOT=Path(self.media.name))
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media.cleanup)
        self.cycle = Cycle.objects.create(title='Test cycle', status='active')
        self.area = Area.objects.create(cycle=self.cycle, code='A1', title='Faculty')
        self.other_area = Area.objects.create(cycle=self.cycle, code='A2', title='Research')
        self.coordinator = self.user('coordinator', None)
        self.custodian = self.user('custodian', self.area)
        self.reviewer = self.user('reviewer', self.area)
        self.outsider = self.user('custodian', self.other_area, 'outsider')
        self.viewer = self.user('viewer', None)
        self.administrator = self.user('administrator', None)
        self.administrator.is_staff = True
        self.administrator.is_superuser = True
        self.administrator.save()
        self.client = APIClient()
        self.client.force_authenticate(self.coordinator)
        response = self.client.post('/api/requirements/', {'area': self.area.id, 'code': 'R1', 'title': 'Faculty Plan',
            'responsible': 'Graduate School', 'active': True, 'items': [{'label': 'Plan'}]}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.requirement = Requirement.objects.get(pk=response.data['id'])
        self.item = self.requirement.items.get()

    def user(self, role, area, name=None):
        user = User.objects.create_user(username=name or role, email=f'{name or role}@test.invalid', password='Test-password-1234')
        RoleAssignment.objects.create(user=user, role=role, cycle=self.cycle, area=area)
        return user

    def upload(self, doc=None, user=None, valid_until=None):
        self.client.force_authenticate(user or self.custodian)
        data = {'file': pdf_file(), 'title': 'Faculty Development Plan', 'area': self.area.id}
        if valid_until:
            data['valid_until'] = str(valid_until)
        response = self.client.post(f'/api/documents/{doc}/versions/' if doc else '/api/documents/', data, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def submit(self, document, item=None, user=None, version=None):
        self.client.force_authenticate(user or self.custodian)
        mapping = self.client.post('/api/evidence-mappings/', {'item': (item or self.item).id, 'document': document['id']}, format='json')
        self.assertIn(mapping.status_code, [200, 201], mapping.data)
        sub = self.client.post('/api/submissions/', {'mapping': mapping.data['id'], 'version': version or document['versions'][0]['id']}, format='json')
        self.assertEqual(sub.status_code, 201, sub.data)
        return sub.data

    def decide(self, sub, outcome='approved', comment='', user=None):
        self.client.force_authenticate(user or self.reviewer)
        return self.client.post('/api/review-decisions/', {'submission': sub['id'], 'outcome': outcome, 'comment': comment}, format='json')

    def compliance(self):
        self.client.force_authenticate(self.coordinator)
        return self.client.get('/api/compliance/').data

    def certify(self, outcome='complete', rationale='Evidence satisfies the requirement.', user=None):
        self.client.force_authenticate(user or self.coordinator)
        return self.client.post(f'/api/requirements/{self.requirement.id}/certifications/',
                                {'outcome': outcome, 'rationale': rationale}, format='json')


class WorkflowTests(WorkflowFixture, TestCase):
    def test_approved_evidence_becomes_ready_then_coordinator_certifies_completion(self):
        self.assertEqual(self.compliance()['percentage'], 0)
        document = self.upload()
        sub = self.submit(document)
        self.assertEqual(self.compliance()['pending'], 1)
        self.assertEqual(self.decide(sub).status_code, 201)
        self.assertEqual(self.compliance()['percentage'], 0)
        self.assertEqual(self.compliance()['ready_for_completion_review'], 1)
        self.assertEqual(self.certify().status_code, 201)
        self.assertEqual(self.compliance()['percentage'], 100)
        self.assertTrue(AuditEvent.objects.filter(action='approved', detail__version=sub['version']).exists())
        self.assertTrue(AuditEvent.objects.filter(action='requirement_completed').exists())

    def test_revision_requires_new_version_preserves_history(self):
        document = self.upload()
        sub = self.submit(document)
        self.assertEqual(self.decide(sub, 'revision_requested', 'Include the signatures.').status_code, 201)
        self.assertEqual(self.compliance()['percentage'], 0)
        updated = self.upload(document['id'])
        new_sub = self.submit(updated)
        self.assertEqual(self.decide(new_sub).status_code, 201)
        self.assertEqual(self.compliance()['percentage'], 0)
        self.assertEqual(self.compliance()['ready_for_completion_review'], 1)
        self.assertEqual(DocumentVersion.objects.count(), 2)
        self.assertEqual(ReviewDecision.objects.get(submission_id=sub['id']).outcome, 'revision_requested')

    def test_new_draft_or_submission_does_not_reopen_completed_requirement(self):
        doc = self.upload()
        self.decide(self.submit(doc))
        self.certify()
        updated = self.upload(doc['id'])
        self.assertEqual(self.compliance()['percentage'], 100)
        self.submit(updated)
        self.assertEqual(self.compliance()['percentage'], 100)

    def test_anonymous_and_outside_scope(self):
        doc = self.upload()
        sub = self.submit(doc)
        version = doc['versions'][0]['id']
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/documents/').status_code, 403)
        self.assertEqual(self.client.get(f'/api/document-versions/{version}/download/').status_code, 403)
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get('/api/documents/').data, [])
        self.assertEqual(self.client.get('/api/requirements/').data, [])
        self.assertEqual(self.client.get('/api/submissions/').data, [])
        self.assertEqual(self.client.get(f'/api/documents/{doc["id"]}/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/document-versions/{version}/download/').status_code, 404)
        self.assertEqual(self.client.patch(f'/api/requirements/{self.requirement.id}/', {'title': 'Unauthorized'}, format='json').status_code, 404)
        self.assertEqual(self.decide(sub, user=self.outsider).status_code, 404)

    def test_scoped_search_compliance_report_csv_and_audit_filters(self):
        document = self.upload()
        submission = self.submit(document)
        self.assertEqual(self.decide(submission).status_code, 201)
        self.assertEqual(self.certify().status_code, 201)
        self.client.force_authenticate(self.coordinator)
        search = self.client.get('/api/search/', {'q': 'Faculty'})
        self.assertEqual(search.status_code, 200)
        self.assertEqual(search.data['requirements'][0]['id'], self.requirement.id)
        self.assertEqual(search.data['documents'][0]['title'], 'Faculty Development Plan')
        report = self.client.get('/api/reports/compliance/', {'cycle': self.cycle.id})
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.data['total'], 1)
        self.assertEqual(report.data['complete'], 1)
        self.assertEqual(report.data['percentage'], 100)
        csv_response = self.client.get('/api/reports/compliance/', {'cycle': self.cycle.id, 'download': 'csv'})
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn('text/csv', csv_response['Content-Type'])
        self.assertIn('Faculty Plan', csv_response.content.decode())
        audit = self.client.get('/api/audit/', {'search': 'Faculty Development'})
        self.assertEqual(audit.status_code, 200)
        self.assertTrue(any(event['action'] == 'version_uploaded' for event in audit.data))
        self.client.force_authenticate(self.outsider)
        hidden_search = self.client.get('/api/search/', {'q': 'Faculty'})
        self.assertEqual(hidden_search.status_code, 200)
        self.assertEqual(hidden_search.data, {'requirements': [], 'documents': []})
        self.assertEqual(self.client.get('/api/reports/compliance/', {'cycle': self.cycle.id}).data['total'], 0)

    def test_csv_neutralizes_spreadsheet_formula_values(self):
        self.requirement.title = '=HYPERLINK("https://invalid.example")'
        self.requirement.save()
        self.client.force_authenticate(self.coordinator)
        response = self.client.get('/api/reports/compliance/', {'cycle': self.cycle.id, 'download': 'csv'})
        self.assertEqual(response.status_code, 200)
        self.assertIn("'=HYPERLINK", response.content.decode())

    def test_admin_has_no_implicit_evidence_access_or_approval(self):
        doc = self.upload()
        sub = self.submit(doc)
        self.assertEqual(self.decide(sub, user=self.administrator).status_code, 404)
        self.assertEqual(self.client.get('/api/documents/').data, [])

    def test_self_review_and_submission_review_are_denied(self):
        RoleAssignment.objects.create(user=self.custodian, cycle=self.cycle, area=self.area, role='reviewer')
        doc = self.upload()
        sub = self.submit(doc)
        self.assertEqual(self.decide(sub, user=self.custodian).status_code, 403)

    def test_mappings_require_access_to_source_and_destination(self):
        doc = self.upload()
        self.client.force_authenticate(self.outsider)
        response = self.client.post('/api/evidence-mappings/', {'item': self.item.id, 'document': doc['id']}, format='json')
        self.assertEqual(response.status_code, 404)

    def test_shared_document_exposes_only_submitted_versions(self):
        doc = self.upload()
        req = Requirement.objects.create(area=self.other_area, code='R2', title='Shared', responsible='Office', active=True, created_by=self.coordinator)
        item = EvidenceItem.objects.create(requirement=req, label='Shared plan')
        self.submit(doc, item=item, user=self.coordinator)
        updated = self.upload(doc['id'])
        self.client.force_authenticate(self.outsider)
        visible = self.client.get(f'/api/documents/{doc["id"]}/').data
        self.assertEqual(len(visible['versions']), 1)
        self.assertEqual(visible['versions'][0]['number'], 1)
        self.assertEqual(self.client.get(f'/api/document-versions/{updated["versions"][0]["id"]}/download/').status_code, 404)

    def test_all_mandatory_evidence_is_required_before_completion_certification(self):
        doc = self.upload()
        second = EvidenceItem.objects.create(requirement=self.requirement, label='Second required item')
        first_sub = self.submit(doc)
        second_sub = self.submit(doc, item=second)
        self.decide(first_sub)
        self.assertEqual(self.compliance()['complete'], 0)
        self.assertEqual(self.certify().status_code, 400)
        self.decide(second_sub)
        self.assertEqual(self.compliance()['ready_for_completion_review'], 1)
        self.assertEqual(self.certify().status_code, 201)
        self.assertEqual(self.compliance()['complete'], 1)

    def test_only_coordinator_can_certify_or_reopen_with_required_rationale(self):
        self.decide(self.submit(self.upload()))
        self.assertEqual(self.certify(user=self.reviewer).status_code, 403)
        self.assertEqual(self.certify(rationale='').status_code, 400)
        completed = self.certify(rationale='Coordinator verified all required evidence.')
        self.assertEqual(completed.status_code, 201)
        self.assertEqual(completed.data['requirement']['status'], 'complete')
        self.assertEqual(self.certify(outcome='reopened', rationale='', user=self.coordinator).status_code, 400)
        reopened = self.certify(outcome='reopened', rationale='Updated policy requires a new certification.')
        self.assertEqual(reopened.status_code, 201)
        self.assertEqual(reopened.data['requirement']['status'], 'ready_for_completion_review')
        self.assertEqual(self.compliance()['complete'], 0)
        self.assertEqual(self.compliance()['ready_for_completion_review'], 1)
        history = self.client.get(f'/api/requirements/{self.requirement.id}/certifications/')
        self.assertEqual(history.status_code, 200)
        self.assertEqual([entry['outcome'] for entry in history.data], ['reopened', 'complete'])
        self.assertTrue(AuditEvent.objects.filter(action='requirement_reopened').exists())

    def test_certification_history_is_immutable_and_outside_scope_is_hidden(self):
        self.decide(self.submit(self.upload()))
        self.certify()
        certification = RequirementCertification.objects.get()
        certification.rationale = 'Overwritten'
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            certification.save()
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(f'/api/requirements/{self.requirement.id}/certifications/').status_code, 404)

    def test_duplicate_or_stale_review_rejected(self):
        doc = self.upload()
        sub = self.submit(doc)
        self.assertEqual(self.decide(sub).status_code, 201)
        self.assertEqual(self.decide(sub).status_code, 400)
        updated = self.upload(doc['id'])
        new_sub = self.submit(updated)
        updated_again = self.upload(doc['id'])
        self.submit(updated_again)
        self.assertEqual(self.decide(new_sub).status_code, 400)

    def test_non_approval_requires_reason(self):
        sub = self.submit(self.upload())
        self.assertEqual(self.decide(sub, 'revision_requested', '   ').status_code, 400)
        self.assertEqual(self.decide(sub, 'rejected', '').status_code, 400)
        self.assertEqual(self.decide(sub, 'rejected', 'Wrong evidence.').status_code, 201)

    def test_empty_and_excluded_denominators(self):
        self.client.force_authenticate(self.coordinator)
        response = self.client.patch(f'/api/requirements/{self.requirement.id}/', {'applicable': False}, format='json')
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(f'/api/requirements/{self.requirement.id}/', {'applicable': False, 'exclusion_reason': 'Outside program scope'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.compliance()['percentage'])
        self.assertEqual(self.compliance()['excluded'], 1)

    def test_activation_requires_mandatory_item(self):
        self.client.force_authenticate(self.coordinator)
        response = self.client.post('/api/requirements/', {'area': self.area.id, 'code': 'EMPTY', 'title': 'Empty', 'responsible': 'Office', 'active': True, 'items': []}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_expired_evidence_cannot_submit_or_count(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        doc = self.upload(valid_until=yesterday)
        self.client.force_authenticate(self.custodian)
        mapping = self.client.post('/api/evidence-mappings/', {'item': self.item.id, 'document': doc['id']}, format='json').data
        self.assertEqual(self.client.post('/api/submissions/', {'mapping': mapping['id'], 'version': doc['versions'][0]['id']}, format='json').status_code, 400)
        current = self.upload(doc['id'], valid_until=timezone.localdate())
        sub = self.submit(current)
        self.decide(sub)
        self.certify()
        from unittest.mock import patch
        with patch('hub.compliance.timezone.localdate', return_value=timezone.localdate() + timedelta(days=1)):
            self.assertEqual(self.compliance()['complete'], 1)

    def test_closed_cycle_is_read_only_but_downloadable(self):
        doc = self.upload()
        sub = self.submit(doc)
        self.cycle.status = 'closed'
        self.cycle.save()
        self.assertEqual(self.decide(sub).status_code, 400)
        self.client.force_authenticate(self.coordinator)
        self.assertEqual(self.client.patch(f'/api/requirements/{self.requirement.id}/', {'title': 'Changed'}, format='json').status_code, 400)
        self.assertEqual(self.certify().status_code, 400)
        self.assertEqual(self.client.post(f'/api/documents/{doc["id"]}/versions/', {'file': pdf_file()}, format='multipart').status_code, 400)
        response = self.client.get(f'/api/document-versions/{doc["versions"][0]["id"]}/download/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF-'))

    def test_invalid_uploads_and_file_limit(self):
        self.client.force_authenticate(self.custodian)
        for filename, content in [('bad.exe', b'MZ'), ('fake.pdf', b'not pdf'), ('fake.png', b'not image'), ('fake.docx', b'not zip'), ('empty.pdf', b'')]:
            response = self.client.post('/api/documents/', {'file': SimpleUploadedFile(filename, content), 'title': 'Invalid', 'area': self.area.id}, format='multipart')
            self.assertEqual(response.status_code, 400)
        from .files import validate_upload
        from rest_framework.exceptions import ValidationError
        upload = pdf_file()
        upload.size = 26 * 1024 * 1024
        with self.assertRaises(ValidationError):
            validate_upload(upload)
        self.assertEqual(Document.objects.count(), 0)

    def test_viewer_cannot_upload_or_modify(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.post('/api/documents/', {'file': pdf_file(), 'title': 'No', 'area': self.area.id}, format='multipart').status_code, 404)
        self.assertEqual(self.client.patch(f'/api/requirements/{self.requirement.id}/', {'title': 'No'}, format='json').status_code, 403)

    def test_login_csrf_and_session(self):
        client = APIClient(enforce_csrf_checks=True)
        credentials = {'username': self.custodian.email, 'password': 'Test-password-1234'}
        self.assertEqual(client.post('/api/auth/login/', credentials, format='json').status_code, 403)
        token = client.get('/api/auth/csrf/').data['csrfToken']
        self.assertEqual(client.post('/api/auth/login/', credentials, format='json', HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(client.get('/api/auth/me/').status_code, 200)
        self.assertEqual(client.post('/api/auth/logout/', {}, format='json').status_code, 403)
        token = client.get('/api/auth/csrf/').data['csrfToken']
        self.assertEqual(client.post('/api/auth/logout/', {}, format='json', HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(client.get('/api/auth/me/').status_code, 403)

    def test_password_change_requires_current_password_and_keeps_session(self):
        self.client.force_authenticate(self.custodian)
        bad = self.client.post('/api/auth/password-change/', {'current_password': 'wrong', 'new_password': 'Changed-password-1234'}, format='json')
        self.assertEqual(bad.status_code, 400)
        response = self.client.post('/api/auth/password-change/', {'current_password': 'Test-password-1234', 'new_password': 'Changed-password-1234'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 200)
        self.assertTrue(User.objects.get(pk=self.custodian.pk).check_password('Changed-password-1234'))
        self.assertTrue(AuditEvent.objects.filter(action='password_changed', actor=self.custodian).exists())

    def test_password_recovery_reports_when_delivery_is_not_configured(self):
        disabled = self.client.post('/api/auth/password-reset/', {'email': self.custodian.email}, format='json')
        self.assertEqual(disabled.status_code, 200)
        self.assertIn('not configured', disabled.data['detail'])

    @override_settings(PASSWORD_RESET_ENABLED=True, EMAIL_HOST='smtp.example.invalid', DEFAULT_FROM_EMAIL='noreply@example.invalid', EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_recovery_is_one_time_when_delivery_is_configured(self):
        # The endpoint remains non-enumerating once institutional delivery is enabled.
        response = self.client.post('/api/auth/password-reset/', {'email': self.custodian.email}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(mail.outbox), 1)
        uid = urlsafe_base64_encode(force_bytes(self.custodian.pk))
        token = default_token_generator.make_token(self.custodian)
        confirmed = self.client.post('/api/auth/password-reset-confirm/', {'uid': uid, 'token': token, 'new_password': 'Recovered-password-1234'}, format='json')
        self.assertEqual(confirmed.status_code, 200, confirmed.data)
        self.assertTrue(User.objects.get(pk=self.custodian.pk).check_password('Recovered-password-1234'))
        self.assertTrue(AuditEvent.objects.filter(action='password_reset', actor=self.custodian).exists())

    def test_cycle_close_reopen_is_scoped_logged_and_restores_authorized_writes(self):
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.post(f'/api/cycles/{self.cycle.id}/close/', {'rationale': 'Not authorized'}, format='json').status_code, 403)
        self.client.force_authenticate(self.coordinator)
        closed = self.client.post(f'/api/cycles/{self.cycle.id}/close/', {'rationale': 'Evidence review is complete.'}, format='json')
        self.assertEqual(closed.status_code, 200, closed.data)
        self.cycle.refresh_from_db()
        self.assertEqual(self.cycle.status, 'closed')
        self.assertTrue(AuditEvent.objects.filter(action='cycle_closed', detail__rationale='Evidence review is complete.').exists())
        self.assertEqual(self.client.patch(f'/api/requirements/{self.requirement.id}/', {'title': 'Blocked'}, format='json').status_code, 400)
        reopened = self.client.post(f'/api/cycles/{self.cycle.id}/reopen/', {'rationale': 'A correction is required.'}, format='json')
        self.assertEqual(reopened.status_code, 200, reopened.data)
        self.assertEqual(self.client.patch(f'/api/requirements/{self.requirement.id}/', {'title': 'Allowed'}, format='json').status_code, 200)
        self.assertTrue(AuditEvent.objects.filter(action='cycle_reopened', detail__rationale='A correction is required.').exists())

    def test_historical_records_cannot_be_overwritten(self):
        doc = self.upload()
        version = DocumentVersion.objects.get(pk=doc['versions'][0]['id'])
        version.original_name = 'overwritten.pdf'
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            version.save()

    def test_bad_queries_and_unsupported_methods_are_client_errors(self):
        self.client.force_authenticate(self.coordinator)
        for endpoint in ['areas', 'requirements', 'documents', 'submissions', 'compliance', 'audit']:
            self.assertEqual(self.client.get(f'/api/{endpoint}/?cycle=invalid').status_code, 400)
        self.assertEqual(self.client.post(f'/api/requirements/{self.requirement.id}/', {}, format='json').status_code, 405)
        self.assertEqual(self.client.patch('/api/requirements/', {}, format='json').status_code, 405)

    def test_cycle_closure_preserves_expiry_date_and_records_summary(self):
        from django.core.management import call_command
        from unittest.mock import patch
        doc = self.upload(valid_until=timezone.localdate())
        self.decide(self.submit(doc))
        self.certify()
        call_command('close_cycle', self.cycle.id, stdout=io.StringIO())
        with patch('hub.compliance.timezone.localdate', return_value=timezone.localdate() + timedelta(days=5)):
            self.assertEqual(self.compliance()['percentage'], 100)
        self.assertTrue(AuditEvent.objects.filter(action='cycle_closed').exists())


class ConcurrencyTests(WorkflowFixture, TransactionTestCase):
    def test_two_reviewers_cannot_record_conflicting_decisions(self):
        sub = self.submit(self.upload())
        def decide(user_id, outcome):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(User.objects.get(pk=user_id))
                return client.post('/api/review-decisions/', {'submission': sub['id'], 'outcome': outcome, 'comment': 'Concurrent review'}, format='json').status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(decide, self.reviewer.id, 'approved'), pool.submit(decide, self.coordinator.id, 'rejected')]
            self.assertEqual(sorted(f.result() for f in futures), [201, 400])
        self.assertEqual(ReviewDecision.objects.filter(submission_id=sub['id']).count(), 1)
