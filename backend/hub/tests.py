import io
import csv
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from django.db import DatabaseError, close_old_connections
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.auth.models import Permission
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from rest_framework.test import APIClient
from pypdf import PdfWriter
from .models import *
from .audit import write_audit


RECOVERY_TEST_SETTINGS = {
    'PASSWORD_RESET_ENABLED': True,
    'EMAIL_BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
    'EMAIL_HOST': 'smtp.school.edu',
    'EMAIL_PORT': 587,
    'EMAIL_HOST_USER': 'recovery-service',
    'EMAIL_HOST_PASSWORD': 'fixture-only-placeholder',
    'EMAIL_USE_TLS': True,
    'EMAIL_USE_SSL': False,
    'EMAIL_TIMEOUT': 10,
    'DEFAULT_FROM_EMAIL': 'recovery@school.edu',
    'PASSWORD_RESET_FRONTEND_URL': 'https://hub.school.edu/',
}


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
        # Existing tests exercise the preserved pre-F07 item-level history path.
        self.requirement.legacy_submission_mode = True
        self.requirement.save(update_fields=['legacy_submission_mode'])
        self.item = self.requirement.items.get()
        RequirementAssignment.objects.create(requirement=self.requirement, user=self.custodian, assigned_by=self.coordinator)

    def user(self, role, area, name=None):
        user = User.objects.create_user(username=name or role, email=f'{name or role}@test.invalid', password='Test-password-1234')
        RoleAssignment.objects.create(user=user, role=role, cycle=self.cycle, area=area)
        return user

    def upload(self, doc=None, user=None, valid_until=None, filename='evidence.pdf'):
        actor = user or self.custodian
        self.client.force_authenticate(actor)
        data = {'file': pdf_file(filename), 'title': 'Faculty Development Plan', 'area': self.area.id, 'requirement': self.requirement.id}
        if doc and actor == self.coordinator:
            data['override_reason'] = 'Focused test Coordinator replacement override.'
        if not doc and actor == self.coordinator:
            data['override_reason'] = 'Focused test Coordinator upload override.'
        if valid_until:
            data['valid_until'] = str(valid_until)
        response = self.client.post(f'/api/documents/{doc}/versions/' if doc else '/api/documents/', data, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def submit(self, document, item=None, user=None, version=None):
        actor = user or self.custodian
        self.client.force_authenticate(actor)
        override = {'override_reason': 'Focused test Coordinator mapping and submission override.'} if actor == self.coordinator else {}
        mapping = self.client.post('/api/evidence-mappings/', {'item': (item or self.item).id, 'document': document['id'], **override}, format='json')
        self.assertIn(mapping.status_code, [200, 201], mapping.data)
        sub = self.client.post('/api/submissions/', {'mapping': mapping.data['id'], 'version': version or document['versions'][0]['id'], **override}, format='json')
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
        selected = [mapping.submissions.first().id for item in self.requirement.items.all()
                    for mapping in item.mappings.all() if mapping.submissions.first() and
                    ReviewDecision.objects.filter(submission=mapping.submissions.first(), outcome='approved').exists()]
        return self.client.post(f'/api/requirements/{self.requirement.id}/certifications/',
                                {'outcome': outcome, 'rationale': rationale,
                                 **({'submissions': selected} if outcome == 'complete' else {})}, format='json')


class WorkflowTests(WorkflowFixture, TestCase):
    def test_certification_requires_deliberate_current_evidence_and_preserves_snapshot(self):
        doc = self.upload()
        sub = self.submit(doc)
        self.decide(sub)
        self.client.force_authenticate(self.coordinator)
        url = f'/api/requirements/{self.requirement.id}/certifications/'
        self.assertEqual(self.client.post(url, {'outcome': 'complete', 'rationale': 'Checked'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url, {'outcome': 'complete', 'rationale': 'Checked', 'submissions': [999999]}, format='json').status_code, 400)
        completed = self.certify()
        self.assertEqual(completed.status_code, 201, completed.data)
        record = RequirementCertification.objects.get(pk=completed.data['certification']['id'])
        self.assertEqual(record.criteria_snapshot['revision'], 1)
        self.assertEqual(record.criteria_snapshot['code'], 'R1')
        self.assertEqual(record.criteria_snapshot['items'][0]['label'], 'Plan')
        self.assertEqual(record.evidence.get().submission_id, sub['id'])
        self.assertEqual(record.evidence.get().snapshot['version'], sub['version'])
        self.assertEqual(record.evidence.get().snapshot['checksum'], doc['versions'][0]['checksum'])
        pinned = record.evidence.get()
        pinned.snapshot = {'version': -1}
        from django.core.exceptions import ValidationError as ModelValidationError
        with self.assertRaises(ModelValidationError):
            pinned.save()
        self.assertEqual(self.compliance()['complete'], 1)
        self.assertEqual(self.client.get('/api/reports/compliance/').data['complete'], 1)

    def test_legacy_completion_excluded_until_new_auditable_certification(self):
        self.decide(self.submit(self.upload()))
        old = RequirementCertification.objects.create(requirement=self.requirement, coordinator=self.coordinator,
            outcome='complete', rationale='Pre-F05 historical decision')
        self.assertEqual(self.compliance()['complete'], 0)
        self.assertEqual(self.compliance()['ready_for_completion_review'], 1)
        self.assertEqual(self.client.get('/api/reports/compliance/').data['complete'], 0)
        self.client.force_authenticate(self.coordinator)
        detail = self.client.get(f'/api/requirements/{self.requirement.id}/').data
        self.assertTrue(detail['legacy_certification'])
        self.assertTrue(detail['certifications'][0]['legacy'])
        self.assertIsNone(old.criteria_snapshot)
        self.assertEqual(self.certify().status_code, 201)
        self.assertEqual(self.compliance()['complete'], 1)
        old.refresh_from_db()
        self.assertIsNone(old.criteria_snapshot)
        self.assertEqual(RequirementCertification.objects.count(), 2)

    def test_reopen_precedes_substantive_change_and_applicability_history(self):
        doc = self.upload()
        self.decide(self.submit(doc))
        self.certify()
        self.client.force_authenticate(self.coordinator)
        url = f'/api/requirements/{self.requirement.id}/'
        self.assertEqual(self.client.patch(url, {'description': 'New standard', 'change_reason': 'Policy update'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'applicable': False, 'exclusion_reason': 'Out of scope', 'applicability_reason': 'Scope decision'}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/evidence-mappings/', {'item': self.item.id, 'document': doc['id']}, format='json').status_code, 400)
        self.assertEqual(self.certify(outcome='reopened', rationale='Update criteria').status_code, 201)
        self.assertEqual(self.client.patch(url, {'description': 'New standard', 'change_reason': 'Policy update'}, format='json').status_code, 200)
        self.assertEqual(self.requirement.certifications.get(outcome='complete').criteria_snapshot['description'], '')
        self.assertEqual(self.client.patch(url, {'applicable': False, 'exclusion_reason': 'Out of scope', 'applicability_reason': 'Scope decision'}, format='json').status_code, 200)
        self.assertEqual(self.compliance()['excluded'], 1)
        self.assertEqual(self.client.patch(url, {'exclusion_reason': 'Revised scope'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'exclusion_reason': 'Revised scope', 'applicability_reason': 'Clarified exclusion'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(url, {'applicable': True}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'applicable': True, 'applicability_reason': 'Returned to scope'}, format='json').status_code, 200)
        self.assertEqual(list(self.requirement.applicability_decisions.values_list('applicable', flat=True)), [True, False, False, True])
        decision = self.requirement.applicability_decisions.first()
        decision.reason = 'Overwritten'
        from django.core.exceptions import ValidationError as ModelValidationError
        with self.assertRaises(ModelValidationError):
            decision.save()
        self.assertEqual(self.compliance()['needs_revision'], 1)
        updated = self.upload(doc['id'])
        self.decide(self.submit(updated))
        self.assertEqual(self.certify().status_code, 201)
        self.assertEqual(self.requirement.certifications.first().criteria_snapshot['revision'], 2)

    def test_pending_submission_cannot_be_reviewed_after_criteria_revision(self):
        sub = self.submit(self.upload())
        self.client.force_authenticate(self.coordinator)
        self.assertEqual(self.client.patch(f'/api/requirements/{self.requirement.id}/',
            {'description': 'Revised criteria', 'change_reason': 'Updated standard'}, format='json').status_code, 200)
        self.assertEqual(self.decide(sub).status_code, 400)
        self.assertEqual(self.compliance()['needs_revision'], 1)

    def test_health_probe_is_public_and_checks_database(self):
        client = APIClient()
        response = client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'status': 'ok'})

    def test_approved_evidence_becomes_ready_then_coordinator_certifies_completion(self):
        self.assertEqual(self.compliance()['percentage'], 0)
        document = self.upload()
        sub = self.submit(document)
        self.assertEqual(self.compliance()['for_verification'], 1)
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

    def test_new_draft_allowed_but_submission_requires_reopen(self):
        doc = self.upload()
        self.decide(self.submit(doc))
        self.certify()
        updated = self.upload(doc['id'])
        self.assertEqual(self.compliance()['percentage'], 100)
        mapping = EvidenceMapping.objects.get(item=self.item, document_id=doc['id'])
        blocked = self.client.post('/api/submissions/', {'mapping': mapping.id, 'version': updated['versions'][0]['id']}, format='json')
        self.assertEqual(blocked.status_code, 400)
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
        self.assertTrue(any(event['action'] == 'version_uploaded' for event in audit.data['results']))
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

    def test_f04_assignments_stewardship_overrides_and_legacy_history(self):
        self.client.force_authenticate(self.coordinator)
        unassigned = self.client.post('/api/requirements/', {
            'area': self.area.id, 'code': 'UNASSIGNED', 'title': 'Unassigned requirement',
            'responsible': 'Graduate School', 'active': True, 'items': [{'label': 'Evidence'}],
        }, format='json').data
        self.client.force_authenticate(self.custodian)
        denied_upload = self.client.post('/api/documents/', {
            'file': pdf_file(), 'title': 'Blocked unassigned evidence', 'area': self.area.id,
            'requirement': unassigned['id'],
        }, format='multipart')
        self.assertEqual(denied_upload.status_code, 403)

        self.client.force_authenticate(self.coordinator)
        inactive = self.user('custodian', self.area, 'inactive')
        inactive.is_active = False
        inactive.save(update_fields=['is_active'])
        unrelated = self.user('custodian', self.other_area, 'unrelated')
        other_cycle = Cycle.objects.create(title='Other cycle', status='active')
        cross_cycle = User.objects.create_user(username='cross-cycle', email='cross-cycle@test.invalid', password='Test-password-1234')
        RoleAssignment.objects.create(user=cross_cycle, role='custodian', cycle=other_cycle,
                                      area=Area.objects.create(cycle=other_cycle, code='O1', title='Other'))
        for candidate in [inactive, unrelated, cross_cycle]:
            response = self.client.post(f'/api/requirements/{unassigned["id"]}/assignments/',
                                        {'user': candidate.id, 'reason': 'Must be rejected.'}, format='json')
            self.assertIn(response.status_code, [400, 404])
        assigned = self.client.post(f'/api/requirements/{unassigned["id"]}/assignments/', {
            'user': self.custodian.id, 'reason': 'Custodian owns this requirement.', 'replace': True,
        }, format='json')
        self.assertEqual(assigned.status_code, 201, assigned.data)
        self.assertTrue(AuditEvent.objects.filter(action='requirement_reassigned', detail__reason='Custodian owns this requirement.').exists())

        first = self.upload(user=self.custodian)
        colleague = self.user('custodian', self.area, 'colleague')
        RequirementAssignment.objects.create(requirement=self.requirement, user=colleague, assigned_by=self.coordinator)
        self.client.force_authenticate(colleague)
        self.assertEqual(self.client.post(f'/api/documents/{first["id"]}/versions/', {'file': pdf_file()}, format='multipart').status_code, 403)

        self.client.force_authenticate(self.coordinator)
        mapped = self.client.post('/api/evidence-mappings/', {
            'item': self.item.id, 'document': first['id'], 'override_reason': 'Coordinator covers an urgent handoff.',
        }, format='json')
        self.assertEqual(mapped.status_code, 201, mapped.data)
        submitted = self.client.post('/api/submissions/', {
            'mapping': mapped.data['id'], 'version': first['versions'][0]['id'],
            'override_reason': 'Coordinator covers an urgent handoff.',
        }, format='json')
        self.assertEqual(submitted.status_code, 201, submitted.data)
        self.assertTrue(AuditEvent.objects.filter(action='evidence_submitted', detail__override=True,
                                                   detail__override_reason='Coordinator covers an urgent handoff.').exists())

        legacy = Document.objects.create(title='Legacy history', category='Supporting Document', area=self.area, custodian=self.custodian)
        legacy_version = DocumentVersion.objects.create(document=legacy, number=1, original_name='legacy.pdf',
                                                        content_type='application/pdf', size=1, checksum='0' * 64,
                                                        uploaded_by=self.custodian)
        legacy_mapping = EvidenceMapping.objects.create(item=self.item, document=legacy, created_by=self.custodian)
        Submission.objects.create(mapping=legacy_mapping, version=legacy_version, submitted_by=self.custodian)
        self.assertIsNone(legacy.steward)
        self.client.force_authenticate(self.custodian)
        self.assertEqual(self.client.post(f'/api/documents/{legacy.id}/versions/', {'file': pdf_file()}, format='multipart').status_code, 400)
        self.client.force_authenticate(self.coordinator)
        self.assertEqual(self.client.get(f'/api/documents/{legacy.id}/').status_code, 200)
        self.assertEqual(self.client.get('/api/submissions/').status_code, 200)

    def test_legacy_cross_scope_history_preserves_only_approved_version_access(self):
        doc = self.upload()
        req = Requirement.objects.create(area=self.other_area, code='R2', title='Shared', responsible='Office', active=True, created_by=self.coordinator)
        item = EvidenceItem.objects.create(requirement=req, label='Shared plan')
        version = DocumentVersion.objects.get(pk=doc['versions'][0]['id'])
        mapping = EvidenceMapping.objects.create(item=item, document_id=doc['id'], created_by=self.coordinator)
        submission = Submission.objects.create(mapping=mapping, version=version, submitted_by=self.coordinator)
        ReviewDecision.objects.create(submission=submission, reviewer=self.reviewer, outcome='approved')
        updated = self.upload(doc['id'], filename='future-private-version.pdf')
        self.client.force_authenticate(self.outsider)
        visible = self.client.get(f'/api/documents/{doc["id"]}/').data
        self.assertEqual(len(visible['versions']), 1)
        self.assertEqual(visible['versions'][0]['number'], 1)
        self.assertEqual(self.client.get(f'/api/document-versions/{updated["versions"][0]["id"]}/download/').status_code, 404)
        self.assertEqual(self.client.get('/api/search/', {'q': 'future-private-version'}).data['documents'], [])

    def test_role_state_visibility_is_consistent_for_lists_history_search_and_downloads(self):
        document = self.upload(filename='draft-only.pdf')
        v1 = document['versions'][0]['id']

        for user in [self.reviewer, self.viewer]:
            with self.subTest(role=user.username, state='draft'):
                self.client.force_authenticate(user)
                self.assertEqual(self.client.get('/api/documents/').data, [])
                self.assertEqual(self.client.get(f'/api/documents/{document["id"]}/').status_code, 404)
                self.assertEqual(self.client.get(f'/api/document-versions/{v1}/download/').status_code, 404)
                self.assertEqual(self.client.get('/api/search/', {'q': 'draft-only'}).data['documents'], [])

        self.client.force_authenticate(self.custodian)
        self.assertEqual(self.client.get(f'/api/documents/{document["id"]}/').data['versions'][0]['id'], v1)
        self.client.force_authenticate(self.coordinator)
        self.assertEqual(self.client.get(f'/api/documents/{document["id"]}/').data['versions'][0]['id'], v1)

        submission = self.submit(document)
        self.client.force_authenticate(self.reviewer)
        reviewer_detail = self.client.get(f'/api/documents/{document["id"]}/').data
        self.assertEqual([version['id'] for version in reviewer_detail['versions']], [v1])
        self.assertEqual([record['id'] for record in self.client.get('/api/submissions/').data], [submission['id']])
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get('/api/documents/').data, [])
        self.assertEqual(self.client.get(f'/api/document-versions/{v1}/download/').status_code, 404)

        self.assertEqual(self.decide(submission).status_code, 201)
        updated = self.upload(document['id'], filename='hidden-newer-filename.pdf')
        v2 = updated['versions'][0]['id']
        for user in [self.reviewer, self.viewer]:
            with self.subTest(role=user.username, state='approved_v1_draft_v2'):
                self.client.force_authenticate(user)
                detail = self.client.get(f'/api/documents/{document["id"]}/').data
                self.assertEqual([version['id'] for version in detail['versions']], [v1])
                self.assertEqual(self.client.get(f'/api/document-versions/{v2}/download/').status_code, 404)
                self.assertEqual(self.client.get('/api/search/', {'q': 'hidden-newer-filename'}).data['documents'], [])

        self.client.force_authenticate(self.viewer)
        approved_download = self.client.get(f'/api/document-versions/{v1}/download/')
        self.assertEqual(approved_download.status_code, 200)
        b''.join(approved_download.streaming_content)
        self.assertEqual(self.client.get('/api/submissions/').data, [])
        self.assertEqual(self.client.get('/api/review-decisions/').data, [])
        self.assertEqual(self.client.get(f'/api/requirements/{self.requirement.id}/').data['items'][0]['mappings'], [])
        self.client.force_authenticate(self.coordinator)
        self.assertEqual({version['id'] for version in self.client.get(f'/api/documents/{document["id"]}/').data['versions']}, {v1, v2})
        coordinator_download = self.client.get(f'/api/document-versions/{v2}/download/')
        self.assertEqual(coordinator_download.status_code, 200)
        b''.join(coordinator_download.streaming_content)

    def test_new_cross_area_or_cross_cycle_mapping_and_submission_are_denied(self):
        document = self.upload()
        version = document['versions'][0]['id']
        self.client.force_authenticate(self.coordinator)
        same_cycle = self.client.post('/api/evidence-mappings/', {'item': EvidenceItem.objects.create(
            requirement=Requirement.objects.create(area=self.other_area, code='R2', title='Other area', responsible='Office', active=True, created_by=self.coordinator),
            label='Other area item').id, 'document': document['id']}, format='json')
        self.assertEqual(same_cycle.status_code, 400, same_cycle.data)

        other_cycle = Cycle.objects.create(title='Another cycle', status='active')
        other_area = Area.objects.create(cycle=other_cycle, code='B1', title='Other cycle')
        other_item = EvidenceItem.objects.create(requirement=Requirement.objects.create(
            area=other_area, code='R3', title='Other cycle', responsible='Office', active=True, created_by=self.coordinator), label='Other cycle item')
        RoleAssignment.objects.create(user=self.coordinator, cycle=other_cycle, role='coordinator')
        cross_cycle = self.client.post('/api/evidence-mappings/', {'item': other_item.id, 'document': document['id']}, format='json')
        self.assertEqual(cross_cycle.status_code, 400, cross_cycle.data)

        legacy = EvidenceMapping.objects.create(item=other_item, document_id=document['id'], created_by=self.coordinator)
        denied_submission = self.client.post('/api/submissions/', {'mapping': legacy.id, 'version': version}, format='json')
        self.assertEqual(denied_submission.status_code, 400, denied_submission.data)

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
        response = self.client.patch(f'/api/requirements/{self.requirement.id}/', {'applicable': False, 'exclusion_reason': 'Outside program scope', 'applicability_reason': 'Outside program scope'}, format='json')
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
        self.assertEqual(self.client.post('/api/documents/', {'file': pdf_file(), 'title': 'No', 'area': self.area.id,
                                                              'requirement': self.requirement.id}, format='multipart').status_code, 404)
        self.assertEqual(self.client.patch(f'/api/requirements/{self.requirement.id}/', {'title': 'No'}, format='json').status_code, 403)

    def test_upload_content_validation_follows_scope_and_steward_checks(self):
        from .files import validate_upload
        teammate = self.user('custodian', self.area, 'unassigned-teammate')

        def create_payload():
            return {'file': pdf_file(), 'title': 'Synthetic evidence', 'area': self.area.id,
                    'requirement': self.requirement.id}

        with patch('hub.views.validate_upload', wraps=validate_upload) as validate:
            self.client.force_authenticate(self.viewer)
            self.assertEqual(self.client.post('/api/documents/', create_payload(), format='multipart').status_code, 404)
            self.client.force_authenticate(self.outsider)
            self.assertEqual(self.client.post('/api/documents/', create_payload(), format='multipart').status_code, 404)
            self.client.force_authenticate(teammate)
            self.assertEqual(self.client.post('/api/documents/', create_payload(), format='multipart').status_code, 403)
            self.client.force_authenticate(self.coordinator)
            self.assertEqual(self.client.post('/api/documents/', create_payload(), format='multipart').status_code, 400)
            validate.assert_not_called()

        document = self.upload()
        version_url = f'/api/documents/{document["id"]}/versions/'
        with patch('hub.views.validate_upload', wraps=validate_upload) as validate:
            self.client.force_authenticate(self.outsider)
            self.assertEqual(self.client.post(version_url, {'file': pdf_file()}, format='multipart').status_code, 404)
            self.client.force_authenticate(teammate)
            self.assertEqual(self.client.post(version_url, {'file': pdf_file()}, format='multipart').status_code, 403)
            self.client.force_authenticate(self.coordinator)
            self.assertEqual(self.client.post(version_url, {'file': pdf_file()}, format='multipart').status_code, 400)
            self.cycle.status = 'closed'
            self.cycle.save(update_fields=['status'])
            self.client.force_authenticate(self.custodian)
            self.assertEqual(self.client.post(version_url, {'file': pdf_file()}, format='multipart').status_code, 400)
            validate.assert_not_called()

        self.cycle.status = 'active'
        self.cycle.save(update_fields=['status'])
        with patch('hub.views.validate_upload', wraps=validate_upload) as validate:
            self.client.force_authenticate(self.custodian)
            self.assertEqual(self.client.post(version_url, {'file': pdf_file()}, format='multipart').status_code, 201)
            validate.assert_called_once()

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
        client = APIClient(enforce_csrf_checks=True)
        token = client.get('/api/auth/csrf/').data['csrfToken']
        signed_in = client.post('/api/auth/login/', {'username': self.custodian.username,
            'password': 'Test-password-1234'}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(signed_in.status_code, 200)
        self.assertEqual(client.get('/api/auth/me/').data['id'], self.custodian.pk)
        token = client.get('/api/auth/csrf/').data['csrfToken']
        bad = client.post('/api/auth/password-change/', {'current_password': 'wrong',
            'new_password': 'Changed-password-1234'}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(bad.status_code, 400)
        response = client.post('/api/auth/password-change/', {'current_password': 'Test-password-1234',
            'new_password': 'Changed-password-1234'}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(client.get('/api/auth/me/').data['id'], self.custodian.pk)
        self.assertTrue(User.objects.get(pk=self.custodian.pk).check_password('Changed-password-1234'))
        self.assertTrue(AuditEvent.objects.filter(action='password_changed', actor=self.custodian).exists())
        other = APIClient(enforce_csrf_checks=True)
        other_token = other.get('/api/auth/csrf/').data['csrfToken']
        self.assertEqual(other.post('/api/auth/login/', {'username': self.custodian.username,
            'password': 'Test-password-1234'}, format='json', HTTP_X_CSRFTOKEN=other_token).status_code, 403)
        self.assertEqual(other.post('/api/auth/login/', {'username': self.custodian.username,
            'password': 'Changed-password-1234'}, format='json', HTTP_X_CSRFTOKEN=other_token).status_code, 200)

    def test_password_recovery_reports_when_delivery_is_not_configured(self):
        disabled = self.client.post('/api/auth/password-reset/', {'email': self.custodian.email}, format='json')
        self.assertEqual(disabled.status_code, 200)
        self.assertIn('not configured', disabled.data['detail'])
        self.assertNotIn('sent', disabled.data['detail'])

        uid = urlsafe_base64_encode(force_bytes(self.custodian.pk))
        token = default_token_generator.make_token(self.custodian)
        self.assertEqual(self.client.post('/api/auth/password-reset-confirm/', {
            'uid': uid, 'token': token, 'new_password': 'Recovered-password-1234'}, format='json').status_code, 400)

    def test_password_recovery_rejects_non_smtp_and_incomplete_configuration(self):
        for change in ({'EMAIL_BACKEND': 'django.core.mail.backends.console.EmailBackend'},
                       {'EMAIL_BACKEND': 'django.core.mail.backends.dummy.EmailBackend'},
                       {'EMAIL_HOST_PASSWORD': ''}, {'EMAIL_HOST': ''},
                       {'PASSWORD_RESET_FRONTEND_URL': 'http://hub.school.edu/'},
                       {'EMAIL_USE_TLS': False}):
            with self.subTest(change=list(change)):
                with override_settings(**(RECOVERY_TEST_SETTINGS | change)):
                    with patch('hub.views.EmailMessage.send') as send:
                        response = self.client.post('/api/auth/password-reset/', {'email': self.custodian.email}, format='json')
                    self.assertIn('not configured', response.data['detail'])
                    send.assert_not_called()

    @override_settings(**RECOVERY_TEST_SETTINGS)
    def test_password_recovery_generic_response_and_fragment_link(self):
        with patch('hub.views.EmailMessage.send', autospec=True, return_value=1) as send:
            found = self.client.post('/api/auth/password-reset/', {'email': self.custodian.email}, format='json')
            missing = self.client.post('/api/auth/password-reset/', {'email': 'unknown@school.edu'}, format='json')
        self.assertEqual(found.status_code, 200)
        self.assertEqual(found.data, missing.data)
        self.assertNotIn('sent', found.data['detail'])
        self.assertEqual(send.call_count, 1)
        body = send.call_args.args[0].body
        self.assertTrue('/#reset=1&uid=' in body)
        self.assertNotIn('?reset=', body)
        self.assertNotIn('token=', body.split('#', 1)[0])

    @override_settings(**RECOVERY_TEST_SETTINGS)
    def test_password_recovery_smtp_failure_is_non_enumerating(self):
        for result in (0, RuntimeError('Synthetic SMTP failure')):
            with self.subTest(result=type(result).__name__):
                with patch('hub.views.EmailMessage.send', autospec=True,
                           side_effect=result if isinstance(result, Exception) else None,
                           return_value=result if not isinstance(result, Exception) else None):
                    found = self.client.post('/api/auth/password-reset/', {'email': self.custodian.email}, format='json')
                    missing = self.client.post('/api/auth/password-reset/', {'email': 'unknown@school.edu'}, format='json')
                self.assertEqual(found.status_code, 200)
                self.assertEqual(found.data, missing.data)
                self.assertNotIn('sent', found.data['detail'])

    @override_settings(**RECOVERY_TEST_SETTINGS)
    def test_password_recovery_token_reuse_and_expiry(self):
        with patch('hub.views.EmailMessage.send', autospec=True, return_value=1):
            response = self.client.post('/api/auth/password-reset/', {'email': self.custodian.email}, format='json')
        self.assertEqual(response.status_code, 200)
        uid = urlsafe_base64_encode(force_bytes(self.custodian.pk))
        token = default_token_generator.make_token(self.custodian)
        confirmed = self.client.post('/api/auth/password-reset-confirm/', {'uid': uid, 'token': token, 'new_password': 'Recovered-password-1234'}, format='json')
        self.assertEqual(confirmed.status_code, 200, confirmed.data)
        self.assertEqual(self.client.post('/api/auth/password-reset-confirm/', {
            'uid': uid, 'token': token, 'new_password': 'Another-password-1234'}, format='json').status_code, 400)
        self.assertTrue(User.objects.get(pk=self.custodian.pk).check_password('Recovered-password-1234'))
        self.assertTrue(AuditEvent.objects.filter(action='password_reset', actor=self.custodian).exists())
        issued = datetime(2026, 1, 1)
        with override_settings(PASSWORD_RESET_TIMEOUT=1):
            with patch.object(default_token_generator, '_now', return_value=issued):
                expired_token = default_token_generator.make_token(User.objects.get(pk=self.custodian.pk))
            with patch.object(default_token_generator, '_now', return_value=issued + timedelta(seconds=2)):
                expired = self.client.post('/api/auth/password-reset-confirm/', {
                    'uid': uid, 'token': expired_token, 'new_password': 'Another-password-1234'}, format='json')
        self.assertEqual(expired.status_code, 400)

    def test_cycle_close_reopen_is_scoped_logged_and_restores_authorized_writes(self):
        area_coordinator = self.user('coordinator', self.area, 'area-coordinator')
        self.client.force_authenticate(area_coordinator)
        flags = self.client.get('/api/cycles/').data[0]
        self.assertFalse(flags['can_close'])
        self.assertFalse(flags['can_reopen'])
        self.assertEqual(self.client.post(f'/api/cycles/{self.cycle.id}/close/', {'rationale': 'Area grants cannot close a cycle.'}, format='json').status_code, 403)
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.post(f'/api/cycles/{self.cycle.id}/close/', {'rationale': 'Not authorized'}, format='json').status_code, 403)
        self.client.force_authenticate(self.coordinator)
        closed = self.client.post(f'/api/cycles/{self.cycle.id}/close/', {'rationale': 'Evidence review is complete.'}, format='json')
        self.assertEqual(closed.status_code, 200, closed.data)
        self.cycle.refresh_from_db()
        self.assertEqual(self.cycle.status, 'closed')
        self.assertTrue(AuditEvent.objects.filter(action='cycle_closed', detail__rationale='Evidence review is complete.').exists())
        self.assertEqual(self.client.patch(f'/api/requirements/{self.requirement.id}/', {'title': 'Blocked'}, format='json').status_code, 400)
        self.client.force_authenticate(area_coordinator)
        self.assertEqual(self.client.post(f'/api/cycles/{self.cycle.id}/reopen/', {'rationale': 'Area grants cannot reopen a cycle.'}, format='json').status_code, 403)
        self.client.force_authenticate(self.coordinator)
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
        with self.assertRaises(CommandError):
            call_command('close_cycle', self.cycle.id, actor_id=self.administrator.id,
                         reason='Fictional unauthorized close', stdout=io.StringIO())
        self.coordinator.is_staff = True
        self.coordinator.save(update_fields=['is_staff'])
        call_command('close_cycle', self.cycle.id, actor_id=self.coordinator.id,
                     reason='Fictional operator close', stdout=io.StringIO())
        with patch('hub.compliance.timezone.localdate', return_value=timezone.localdate() + timedelta(days=5)):
            self.assertEqual(self.compliance()['percentage'], 100)
        self.assertTrue(AuditEvent.objects.filter(action='cycle_closed', actor=self.coordinator,
                                                  detail__rationale='Fictional operator close').exists())


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


class PackageWorkflowTests(WorkflowFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.requirement.legacy_submission_mode = False
        self.requirement.save(update_fields=['legacy_submission_mode'])

    def mapped(self, item=None, document=None, user=None):
        doc = document or self.upload(user=user)
        self.client.force_authenticate(user or self.custodian)
        mapping = self.client.post('/api/evidence-mappings/', {
            'item': (item or self.item).id, 'document': doc['id'],
            **({'override_reason': 'Coordinator package mapping override'} if user == self.coordinator else {})}, format='json')
        self.assertIn(mapping.status_code, (200, 201), mapping.data)
        return doc, mapping.data['id']

    def draft(self, entries=None, user=None, notes='Package draft notes'):
        self.client.force_authenticate(user or self.custodian)
        response = self.client.post('/api/packages/', {'requirement': self.requirement.id, 'notes': notes,
            'items': entries or [], **({'override_reason': 'Coordinator package draft override'} if user == self.coordinator else {})}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_draft_edit_submit_review_and_certification_pin_package(self):
        doc, mapping = self.mapped()
        version = doc['versions'][0]['id']
        draft = self.draft()
        self.assertEqual(self.compliance()['in_progress'], 1)
        self.client.force_authenticate(self.custodian)
        edited = self.client.patch(f'/api/packages/{draft["id"]}/', {'notes': 'Updated notes',
            'items': [{'mapping': mapping, 'version': version, 'note': 'Exact faculty plan'}]}, format='json')
        self.assertEqual(edited.status_code, 200, edited.data)
        self.assertEqual(edited.data['items'][0]['version'], version)
        submitted = self.client.post(f'/api/packages/{draft["id"]}/submit/', {}, format='json')
        self.assertEqual(submitted.status_code, 200, submitted.data)
        self.assertEqual(self.compliance()['for_verification'], 1)
        self.assertEqual(self.client.patch(f'/api/packages/{draft["id"]}/', {'notes': 'Rewrite'}, format='json').status_code, 403)
        self.client.force_authenticate(self.reviewer)
        reviewed = self.client.post(f'/api/packages/{draft["id"]}/review/', {'outcome': 'approved', 'comment': 'Meets criteria'}, format='json')
        self.assertEqual(reviewed.status_code, 201, reviewed.data)
        self.assertEqual(self.compliance()['ready_for_completion_review'], 1)
        self.client.force_authenticate(self.coordinator)
        cert = self.client.post(f'/api/requirements/{self.requirement.id}/certifications/', {
            'outcome': 'complete', 'rationale': 'Selected approved package', 'packages': [draft['id']]}, format='json')
        self.assertEqual(cert.status_code, 201, cert.data)
        link = CertificationPackage.objects.get(certification_id=cert.data['certification']['id'])
        self.assertEqual(link.package_id, draft['id'])
        self.assertEqual(link.snapshot['items'][0]['version'], version)
        self.assertEqual(link.snapshot['items'][0]['checksum'], doc['versions'][0]['checksum'])
        self.assertEqual(self.compliance()['complete'], 1)
        self.assertEqual(self.client.get('/api/reports/compliance/').data['complete'], 1)
        package = PackageAttempt.objects.get(pk=draft['id'])
        package.notes = 'Attempted rewrite'
        from django.core.exceptions import ValidationError as ModelValidationError
        with self.assertRaises(ModelValidationError):
            package.save()

    def test_pending_missing_precedence_withdrawal_and_resubmission_history(self):
        second = EvidenceItem.objects.create(requirement=self.requirement, label='Second mandatory')
        doc, mapping = self.mapped()
        first = self.draft([{'mapping': mapping, 'version': doc['versions'][0]['id']}])
        self.client.force_authenticate(self.custodian)
        self.assertEqual(self.client.post(f'/api/packages/{first["id"]}/submit/', {}, format='json').status_code, 200)
        self.assertEqual(self.compliance()['for_verification'], 1)
        self.assertEqual(self.client.get('/api/reports/compliance/').data['for_verification'], 1)
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.client.post(f'/api/packages/{first["id"]}/review/', {'outcome': 'approved'}, format='json').status_code, 400)
        another = self.draft()
        self.client.force_authenticate(self.custodian)
        self.assertEqual(self.client.post(f'/api/packages/{another["id"]}/submit/', {}, format='json').status_code, 400)
        self.assertEqual(self.client.post(f'/api/packages/{first["id"]}/withdraw/', {}, format='json').status_code, 400)
        withdrawn = self.client.post(f'/api/packages/{first["id"]}/withdraw/', {'confirm': True, 'reason': 'Needs replacement'}, format='json')
        self.assertEqual(withdrawn.status_code, 200, withdrawn.data)
        self.assertEqual(PackageAttempt.objects.get(pk=first['id']).status, 'withdrawn')
        self.assertEqual(self.compliance()['in_progress'], 1)
        self.client.force_authenticate(self.custodian)
        resumed = self.client.post(f'/api/packages/{first["id"]}/resubmit/', {}, format='json')
        self.assertEqual(resumed.status_code, 201, resumed.data)
        self.assertEqual(resumed.data['number'], 3)
        self.assertEqual(resumed.data['source_attempt'], first['id'])
        self.assertEqual(resumed.data['items'][0]['version'], doc['versions'][0]['id'])
        self.assertEqual(PackageAttempt.objects.count(), 3)
        self.assertTrue(self.requirement.items.filter(pk=second.id).exists())

    def test_revision_resubmission_and_independent_review_guards(self):
        doc, mapping = self.mapped()
        first = self.draft([{'mapping': mapping, 'version': doc['versions'][0]['id']}])
        self.client.force_authenticate(self.custodian)
        self.client.post(f'/api/packages/{first["id"]}/submit/', {}, format='json')
        self.assertEqual(self.client.post(f'/api/packages/{first["id"]}/review/', {'outcome': 'approved'}, format='json').status_code, 404)
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.client.post(f'/api/packages/{first["id"]}/review/', {'outcome': 'revisions_requested'}, format='json').status_code, 400)
        revision = self.client.post(f'/api/packages/{first["id"]}/review/', {'outcome': 'revisions_requested', 'comment': 'Add signatures'}, format='json')
        self.assertEqual(revision.status_code, 201, revision.data)
        self.assertEqual(self.compliance()['needs_revision'], 1)
        self.assertEqual(self.client.post(f'/api/packages/{first["id"]}/review/', {'outcome': 'approved'}, format='json').status_code, 400)
        self.client.force_authenticate(self.custodian)
        second = self.client.post(f'/api/packages/{first["id"]}/resubmit/', {'copy_items': True}, format='json')
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(self.compliance()['in_progress'], 1)
        newer = self.upload(doc['id'])
        self.client.force_authenticate(self.custodian)
        self.assertEqual(self.client.patch(f'/api/packages/{second.data["id"]}/', {'items': [
            {'mapping': mapping, 'version': newer['versions'][0]['id'], 'note': 'Signed plan'}]}, format='json').status_code, 200)
        self.assertEqual(self.client.post(f'/api/packages/{second.data["id"]}/submit/', {}, format='json').status_code, 200)
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.client.post(f'/api/packages/{second.data["id"]}/review/', {'outcome': 'approved'}, format='json').status_code, 201)
        self.assertEqual(PackageDecision.objects.count(), 2)
        self.assertEqual(PackageAttempt.objects.get(pk=first['id']).status, 'revisions_requested')

    def test_scope_assignment_stewardship_and_legacy_history(self):
        doc, mapping = self.mapped()
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get('/api/packages/').data, [])
        self.assertEqual(self.client.post('/api/packages/', {'requirement': self.requirement.id}, format='json').status_code, 404)
        other = self.user('custodian', self.area, 'teammate')
        self.client.force_authenticate(other)
        self.assertEqual(self.client.post('/api/packages/', {'requirement': self.requirement.id,
            'items': [{'mapping': mapping, 'version': doc['versions'][0]['id']}]}, format='json').status_code, 403)
        self.client.force_authenticate(self.custodian)
        draft = self.draft([{'mapping': mapping, 'version': doc['versions'][0]['id']}])
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get('/api/packages/').data, [])
        self.assertEqual(self.client.get(f'/api/packages/{draft["id"]}/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/requirements/{self.requirement.id}/').data['items'][0]['status'], 'missing')
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.client.get(f'/api/requirements/{self.requirement.id}/').data['items'][0]['status'], 'missing')
        self.client.force_authenticate(self.custodian)
        self.assertEqual(self.client.get(f'/api/requirements/{self.requirement.id}/').data['items'][0]['status'], 'draft')
        self.assertEqual(self.client.post(f'/api/packages/{draft["id"]}/submit/', {}, format='json').status_code, 200)
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.client.get(f'/api/requirements/{self.requirement.id}/').data['items'][0]['status'], 'pending')
        self.assertEqual(self.client.post(f'/api/packages/{draft["id"]}/review/', {'outcome': 'approved'}, format='json').status_code, 201)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get(f'/api/requirements/{self.requirement.id}/').data['items'][0]['status'], 'approved')
        self.assertEqual(Submission.objects.count(), 0)
        self.assertEqual(ReviewDecision.objects.count(), 0)

    def test_starting_package_preserves_legacy_item_review_without_backfill(self):
        self.requirement.legacy_submission_mode = True
        self.requirement.save(update_fields=['legacy_submission_mode'])
        doc = self.upload()
        submission = self.submit(doc)
        self.assertEqual(self.decide(submission).status_code, 201)
        original_count = Submission.objects.count()
        decision_count = ReviewDecision.objects.count()
        self.client.force_authenticate(self.custodian)
        draft = self.client.post('/api/packages/', {'requirement': self.requirement.id, 'notes': 'New package work'}, format='json')
        self.assertEqual(draft.status_code, 201, draft.data)
        self.requirement.refresh_from_db()
        self.assertFalse(self.requirement.legacy_submission_mode)
        self.assertEqual(Submission.objects.count(), original_count)
        self.assertEqual(ReviewDecision.objects.count(), decision_count)
        self.assertEqual(PackageAttempt.objects.count(), 1)
        self.assertEqual(PackageItem.objects.count(), 0)
        self.assertEqual(self.client.post('/api/submissions/', {'mapping': submission['mapping'],
            'version': submission['version']}, format='json').status_code, 400)


class PackageConcurrencyTests(WorkflowFixture, TransactionTestCase):
    def test_competing_package_submissions_leave_one_pending(self):
        self.requirement.legacy_submission_mode = False
        self.requirement.save(update_fields=['legacy_submission_mode'])
        doc = self.upload()
        self.client.force_authenticate(self.custodian)
        mapping = self.client.post('/api/evidence-mappings/', {'item': self.item.id, 'document': doc['id']}, format='json').data
        drafts = [self.client.post('/api/packages/', {'requirement': self.requirement.id,
            'items': [{'mapping': mapping['id'], 'version': doc['versions'][0]['id']}]}, format='json').data['id']
            for _ in range(2)]
        def submit(package_id):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(User.objects.get(pk=self.custodian.id))
                return client.post(f'/api/packages/{package_id}/submit/', {}, format='json').status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(submit, drafts)), [200, 400])
        self.assertEqual(PackageAttempt.objects.filter(requirement=self.requirement, status='submitted').count(), 1)

    def test_competing_package_reviews_are_serialized(self):
        self.requirement.legacy_submission_mode = False
        self.requirement.save(update_fields=['legacy_submission_mode'])
        doc = self.upload()
        self.client.force_authenticate(self.custodian)
        mapping = self.client.post('/api/evidence-mappings/', {'item': self.item.id, 'document': doc['id']}, format='json').data
        draft = self.client.post('/api/packages/', {'requirement': self.requirement.id,
            'items': [{'mapping': mapping['id'], 'version': doc['versions'][0]['id']}]}, format='json').data
        self.client.post(f'/api/packages/{draft["id"]}/submit/', {}, format='json')
        def decide(user_id, outcome):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(User.objects.get(pk=user_id))
                return client.post(f'/api/packages/{draft["id"]}/review/', {'outcome': outcome,
                    'comment': 'Concurrent decision'}, format='json').status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(decide, self.reviewer.id, 'approved'),
                       pool.submit(decide, self.coordinator.id, 'revisions_requested')]
            self.assertEqual(sorted(f.result() for f in futures), [201, 400])
        self.assertEqual(PackageDecision.objects.filter(package_id=draft['id']).count(), 1)


@override_settings(RESTRICTED_TEST_MODE=True, TEST_TRUSTED_PROXY_NETWORKS='127.0.0.1/32',
                   TEST_ADMIN_NETWORKS='10.20.0.0/16', TEST_AUTH_LIMIT_PER_MINUTE=2)
class RestrictedTestBoundaryTests(TestCase):
    def client_from(self, address='10.20.1.5', **headers):
        return Client(**({'REMOTE_ADDR': '127.0.0.1', 'HTTP_X_FORWARDED_FOR': address,
                          'HTTP_X_FORWARDED_PROTO': 'https'} | headers))

    def test_spoofed_forwarding_and_untrusted_peer_are_denied(self):
        self.assertEqual(self.client_from('9.9.9.9, 10.20.1.5').get('/api/health/').status_code, 400)
        self.assertEqual(self.client_from('10.20.1.5', HTTP_X_FORWARDED_PROTO='https,http').get('/api/health/').status_code, 400)
        self.assertEqual(self.client_from('10.20.1.5', HTTP_FORWARDED='for=9.9.9.9').get('/api/health/').status_code, 200)
        self.assertEqual(Client(REMOTE_ADDR='10.20.1.5', HTTP_X_FORWARDED_FOR='10.20.1.5',
                                HTTP_X_FORWARDED_PROTO='https').get('/api/health/').status_code, 403)
        with override_settings(TEST_TRUSTED_PROXY_NETWORKS=''):
            self.assertEqual(self.client_from().get('/api/health/').status_code, 403)
        with override_settings(TEST_TRUSTED_PROXY_NETWORKS='0.0.0.0/0'):
            self.assertEqual(self.client_from().get('/api/health/').status_code, 403)

    def test_admin_allowlist_defaults_closed(self):
        self.assertEqual(self.client_from('10.20.1.5').get('/api/admin/login/').status_code, 200)
        self.assertEqual(self.client_from('10.21.1.5').get('/api/admin/login/').status_code, 404)
        with override_settings(TEST_ADMIN_NETWORKS=''):
            self.assertEqual(self.client_from().get('/api/admin/login/').status_code, 404)
        with override_settings(TEST_ADMIN_NETWORKS='0.0.0.0/0'):
            self.assertEqual(self.client_from().get('/api/admin/login/').status_code, 404)

    def test_database_limit_shared_across_clients_for_all_auth_routes(self):
        first = self.client_from()
        second = self.client_from()
        routes = [('/api/auth/login/', {'username': 'absent', 'password': 'incorrect'}),
                  ('/api/auth/password-reset/', {'email': 'absent@school.edu'}),
                  ('/api/admin/login/', {'username': 'absent', 'password': 'incorrect'})]
        for route, body in routes:
            with self.subTest(route=route):
                self.assertNotEqual(first.post(route, body).status_code, 429)
                self.assertNotEqual(second.post(route, body).status_code, 429)
                self.assertEqual(self.client_from().post(route, body).status_code, 429)
        self.assertEqual(AuthRateBucket.objects.count(), 3)
        self.assertNotEqual(self.client_from('10.20.1.6').post('/api/auth/login/',
                            {'username': 'absent', 'password': 'incorrect'}).status_code, 429)

    def test_recovery_confirmation_uses_shared_recovery_limit(self):
        client = self.client_from()
        self.assertNotEqual(client.post('/api/auth/password-reset/', {'email': 'absent@school.edu'}).status_code, 429)
        self.assertNotEqual(client.post('/api/auth/password-reset-confirm/',
                            {'uid': 'bad', 'token': 'bad', 'new_password': 'Synthetic-passphrase-1234'}).status_code, 429)
        self.assertEqual(self.client_from().post('/api/auth/password-reset/',
                         {'email': 'absent@school.edu'}).status_code, 429)

    def test_unavailable_shared_limit_storage_fails_closed(self):
        from django.db import DatabaseError
        with patch('hub.test_boundary.RestrictedTestBoundaryMiddleware._allowed', side_effect=DatabaseError):
            self.assertEqual(self.client_from().post('/api/auth/login/',
                             {'username': 'absent', 'password': 'incorrect'}).status_code, 503)


class StorageReconciliationTests(WorkflowFixture, TestCase):
    def report(self):
        return json.loads(call_command('reconcile_storage', stdout=io.StringIO()))

    def test_missing_mismatched_and_orphaned_files_are_only_reported(self):
        document = self.upload()
        version = DocumentVersion.objects.get(pk=document['versions'][0]['id'])
        path = Path(self.media.name) / str(version.storage_key)
        self.assertEqual(self.report()['counts'], {'missing': 0, 'mismatched': 0, 'orphaned': 0})
        path.write_bytes(b'fictional corrupt content')
        self.assertEqual(self.report()['mismatched'], [str(version.storage_key)])
        path.unlink()
        orphan = Path(self.media.name) / 'orphan-synthetic.txt'
        orphan.write_bytes(b'fictional orphan')
        result = self.report()
        self.assertEqual(result['missing'], [str(version.storage_key)])
        self.assertEqual(result['orphaned'], [orphan.name])
        self.assertTrue(orphan.exists())
        self.assertTrue(DocumentVersion.objects.filter(pk=version.pk).exists())


class AuditHistoryTests(WorkflowFixture, TestCase):
    def test_scoped_academic_access_revocation_and_pagination(self):
        for number in range(5):
            write_audit(self.coordinator, self.area, 'synthetic_review', f'record:{number}', reason='fixture')
        write_audit(self.coordinator, self.other_area, 'synthetic_review', 'other-area')
        scoped = self.user('coordinator', self.area, 'area-coordinator')
        self.client.force_authenticate(scoped)
        first = self.client.get('/api/audit/', {'limit': 2, 'action': 'synthetic_review'})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(len(first.data['results']), 2)
        self.assertIsNotNone(first.data['next_before'])
        second = self.client.get('/api/audit/', {'limit': 2, 'action': 'synthetic_review',
                                                 'before': first.data['next_before']})
        self.assertEqual(len(second.data['results']), 2)
        self.assertTrue(all(row['area_id'] == self.area.id for row in first.data['results'] + second.data['results']))
        self.assertTrue(all(row['detail']['reason'] == 'fixture' for row in first.data['results']))
        RoleAssignment.objects.filter(user=scoped, role='coordinator').delete()
        self.assertEqual(self.client.get('/api/audit/').data['results'], [])
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get('/api/audit/').data['results'], [])

    def test_security_capability_is_separate_from_product_admin_and_evidence(self):
        account = self.user('administrator', None, 'security-operator')
        account.user_permissions.add(Permission.objects.get(codename='view_security_audit'))
        account = User.objects.get(pk=account.pk)
        self.client.force_authenticate(account)
        security = self.client.get('/api/audit/', {'kind': 'security', 'action': 'grant_created'})
        self.assertEqual(security.status_code, 200)
        self.assertTrue(security.data['results'])
        self.assertTrue(all(row['area_id'] is None for row in security.data['results']))
        self.assertEqual(self.client.get('/api/audit/').data['results'], [])
        document = self.upload()
        self.client.force_authenticate(account)
        self.assertEqual(self.client.get(f'/api/documents/{document["id"]}/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/document-versions/{document["versions"][0]["id"]}/download/').status_code, 404)
        ordinary_admin = self.user('administrator', None, 'ordinary-admin')
        self.client.force_authenticate(ordinary_admin)
        self.assertEqual(self.client.get('/api/audit/', {'kind': 'security'}).status_code, 403)

    def test_account_grant_logout_and_secret_redaction(self):
        account = User.objects.create_user(username='audit-fixture', email='audit@test.invalid', password='synthetic-secret-1234')
        account.is_active = False
        account.save(update_fields=['is_active'])
        grant = RoleAssignment.objects.create(user=account, role='viewer', cycle=self.cycle)
        grant_id = grant.pk
        grant.delete()
        self.assertTrue(AuditEvent.objects.filter(action='account_created', record=f'user:{account.pk}').exists())
        self.assertTrue(AuditEvent.objects.filter(action='account_updated', record=f'user:{account.pk}').exists())
        self.assertTrue(AuditEvent.objects.filter(action='grant_revoked', record=f'grant:{grant_id}').exists())
        client = APIClient()
        token = client.get('/api/auth/csrf/').data['csrfToken']
        self.assertEqual(client.post('/api/auth/login/', {'username': self.custodian.username,
                         'password': 'Test-password-1234'}, format='json', HTTP_X_CSRFTOKEN=token).status_code, 200)
        token = client.get('/api/auth/csrf/').data['csrfToken']
        self.assertEqual(client.post('/api/auth/logout/', {}, format='json', HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertTrue(AuditEvent.objects.filter(action='login', actor=self.custodian).exists())
        self.assertTrue(AuditEvent.objects.filter(action='logout', actor=self.custodian).exists())
        serialized = json.dumps(list(AuditEvent.objects.values('record', 'detail')))
        self.assertNotIn('synthetic-secret-1234', serialized)
        self.assertNotIn('Test-password-1234', serialized)
        self.assertNotIn(token, serialized)

    def test_cycle_request_correlation_and_detail_redaction(self):
        write_audit(self.coordinator, self.area, 'synthetic_safe', 'record:1',
                    reason='fixture', reset_token='hidden-token', nested={'password': 'hidden-password'})
        safe = AuditEvent.objects.get(action='synthetic_safe')
        self.assertEqual(safe.detail['reset_token'], '[redacted]')
        self.assertEqual(safe.detail['nested']['password'], '[redacted]')
        self.client.force_authenticate(self.coordinator)
        response = self.client.post(f'/api/cycles/{self.cycle.pk}/close/',
                                    {'rationale': 'Fictional cycle review complete'}, format='json')
        self.assertEqual(response.status_code, 200)
        events = list(AuditEvent.objects.filter(action='cycle_closed', actor=self.coordinator))
        self.assertEqual(len(events), 2)
        self.assertEqual(len({event.request_id for event in events}), 1)
        self.assertTrue(all(event.detail['rationale'] == 'Fictional cycle review complete' for event in events))

    @override_settings(**RECOVERY_TEST_SETTINGS)
    def test_recovery_audit_omits_token_and_security_grant_can_be_revoked(self):
        with patch('hub.views.EmailMessage.send', return_value=1):
            response = self.client.post('/api/auth/password-reset/', {'email': self.custodian.email}, format='json')
        self.assertEqual(response.status_code, 200)
        event = AuditEvent.objects.get(action='recovery_email_accepted', actor=self.custodian)
        self.assertEqual(event.detail, {})
        self.assertNotIn(self.custodian.email, event.record)
        account = self.user('administrator', None, 'temporary-security')
        permission = Permission.objects.get(codename='view_security_audit')
        account.user_permissions.add(permission)
        account = User.objects.get(pk=account.pk)
        self.client.force_authenticate(account)
        self.assertEqual(self.client.get('/api/audit/', {'kind': 'security'}).status_code, 200)
        account.user_permissions.remove(permission)
        account = User.objects.get(pk=account.pk)
        self.client.force_authenticate(account)
        self.assertEqual(self.client.get('/api/audit/', {'kind': 'security'}).status_code, 403)
        self.assertTrue(AuditEvent.objects.filter(action='account_permission_remove', record=f'user:{account.pk}').exists())

    def test_legacy_shared_download_has_source_and_recipient_scope(self):
        document = self.upload()
        version = DocumentVersion.objects.get(pk=document['versions'][0]['id'])
        recipient = self.user('coordinator', self.other_area, 'recipient-coordinator')
        requirement = Requirement.objects.create(area=self.other_area, code='OLD', title='Fictional legacy',
                                                   responsible='School', active=True, created_by=self.coordinator)
        item = EvidenceItem.objects.create(requirement=requirement, label='Sample')
        mapping = EvidenceMapping.objects.create(item=item, document=version.document, created_by=self.coordinator)
        Submission.objects.create(mapping=mapping, version=version, submitted_by=self.custodian)
        self.client.force_authenticate(recipient)
        response = self.client.get(f'/api/document-versions/{version.pk}/download/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF-'))
        events = list(AuditEvent.objects.filter(action='version_downloaded', actor=recipient, record=f'version:{version.pk}'))
        self.assertEqual({event.area_id for event in events}, {self.area.pk, self.other_area.pk})
        self.assertEqual(len({event.request_id for event in events}), 1)
        recipient_page = self.client.get('/api/audit/', {'area': self.other_area.pk, 'action': 'version_downloaded'})
        self.assertEqual(len(recipient_page.data['results']), 1)
        self.assertEqual(recipient_page.data['results'][0]['detail']['source_area_id'], self.area.pk)


class ReportProvenanceTests(WorkflowFixture, TestCase):
    def test_status_filter_keeps_cycle_area_readiness_and_records_population(self):
        document = self.upload()
        self.assertEqual(self.decide(self.submit(document)).status_code, 201)
        self.assertEqual(self.certify().status_code, 201)
        Requirement.objects.create(area=self.other_area, code='MISSING', title='Fictional missing',
                                   responsible='School', active=True, created_by=self.coordinator)
        Requirement.objects.create(area=self.area, code='EXCLUDED', title='Fictional excluded',
                                   responsible='School', active=True, applicable=False,
                                   exclusion_reason='Synthetic scope decision', created_by=self.coordinator)
        self.client.force_authenticate(self.coordinator)
        dashboard = self.client.get('/api/compliance/', {'cycle': self.cycle.id}).data
        report = self.client.get('/api/reports/compliance/',
                                 {'cycle': self.cycle.id, 'status': 'complete'}).data
        for field in ('total', 'complete', 'excluded', 'percentage', 'formula', 'formula_version'):
            self.assertEqual(report[field], dashboard[field])
        self.assertEqual((report['numerator'], report['denominator'], report['filtered_row_count']), (1, 2, 1))
        self.assertEqual(report['selected_filters']['status'], 'complete')
        self.assertEqual(report['cycle']['instrument'], self.cycle.instrument)
        self.assertEqual(report['timezone'], 'Asia/Manila')
        self.assertIn('status filters change rows only', report['population_label'])
        self.assertEqual({a['id'] for a in report['authorized_areas']}, {self.area.id, self.other_area.id})
        self.assertEqual(len(report['rows']), 1)
        area_report = self.client.get('/api/reports/compliance/',
                                      {'cycle': self.cycle.id, 'area': self.other_area.id, 'status': 'complete'}).data
        self.assertEqual((area_report['numerator'], area_report['denominator'], area_report['filtered_row_count']), (0, 1, 0))
        self.assertEqual(area_report['selected_filters']['area'], self.other_area.title)

    def test_csv_has_provenance_and_neutralizes_metadata_and_rows(self):
        self.cycle.instrument = '=unsafe-instrument'
        self.cycle.save(update_fields=['instrument'])
        self.area.title = '+unsafe-area'
        self.area.save(update_fields=['title'])
        self.requirement.title = '=unsafe-title'
        self.requirement.save(update_fields=['title'])
        self.client.force_authenticate(self.coordinator)
        response = self.client.get('/api/reports/compliance/',
                                   {'cycle': self.cycle.id, 'area': self.area.id, 'status': 'missing', 'download': 'csv'})
        self.assertEqual(response.status_code, 200)
        csv_rows = list(csv.reader(io.StringIO(response.content.decode('utf-8'))))
        metadata = {row[0]: row[1] for row in csv_rows if len(row) == 2}
        for key in ('Cycle', 'Instrument', 'Authorized scope', 'Authorized areas', 'Area filter',
                    'Status filter', 'Readiness population', 'Numerator (complete)',
                    'Denominator (active applicable)', 'Excluded (active not applicable)',
                    'Filtered row count', 'Formula', 'Formula version', 'Calculated at', 'Timezone'):
            self.assertIn(key, metadata)
        self.assertEqual(metadata['Instrument'], "'=unsafe-instrument")
        self.assertEqual(metadata['Area filter'], "'+unsafe-area")
        self.assertEqual(metadata['Timezone'], 'Asia/Manila')
        self.assertTrue(any("'=unsafe-title" in row for row in csv_rows))

    def test_report_rejects_inaccessible_cycle_or_area(self):
        private_cycle = Cycle.objects.create(title='Fictional private cycle', status='active')
        self.client.force_authenticate(self.custodian)
        self.assertEqual(self.client.get('/api/reports/compliance/', {'cycle': private_cycle.id}).status_code, 404)
        self.assertEqual(self.client.get('/api/reports/compliance/',
                                         {'cycle': self.cycle.id, 'area': self.other_area.id}).status_code, 404)


class InputBoundaryTests(WorkflowFixture, TestCase):
    def test_invalid_identifiers_and_oversized_search_return_400(self):
        for value in ('²', '٢', '9' * 4301, '0', '-1'):
            with self.subTest(kind='identifier', length=len(value)):
                self.assertEqual(self.client.get('/api/requirements/', {'cycle': value}).status_code, 400)
                self.assertEqual(self.client.get('/api/reports/compliance/', {'area': value}).status_code, 400)
        for endpoint in ('/api/requirements/', '/api/documents/'):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.client.get(endpoint, {'search': 'x' * 121}).status_code, 400)

    def test_ambiguous_login_fails_closed(self):
        User.objects.create_user(username=self.custodian.email, email='second@test.invalid', password='Synthetic-password-1234')
        self.client.force_authenticate(user=None)
        login = self.client.post('/api/auth/login/', {'username': self.custodian.email,
                                                      'password': 'Test-password-1234'}, format='json')
        self.assertEqual(login.status_code, 403)
        self.assertEqual(login.data['detail'], 'Invalid username or password.')
        oversized = self.client.post('/api/auth/login/', {'username': self.custodian.username,
                                                            'password': 'x' * 4097}, format='json')
        self.assertEqual(oversized.status_code, 403)

    def test_large_requirement_fields_and_item_count_are_rejected(self):
        before = Requirement.objects.count()
        base = {'area': self.area.id, 'code': 'BOUND', 'title': 'Synthetic boundary',
                'responsible': 'School', 'active': True, 'items': [{'label': 'Required'}]}
        for change in ({'description': 'x' * 4001}, {'items': [{'label': 'Item'}] * 51},
                       {'items': [{'label': 'Required', 'criteria': 'x' * 4001}]}):
            with self.subTest(fields=list(change)):
                response = self.client.post('/api/requirements/', base | change, format='json')
                self.assertEqual(response.status_code, 400)
        self.assertEqual(Requirement.objects.count(), before)


class SessionAndHealthEvidenceTests(WorkflowFixture, TestCase):
    def session_client(self, user):
        client = APIClient(enforce_csrf_checks=True)
        token = client.get('/api/auth/csrf/').data['csrfToken']
        response = client.post('/api/auth/login/', {'username': user.username,
            'password': 'Test-password-1234'}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        return client

    def test_inactive_account_cannot_log_in_or_keep_a_session(self):
        client = self.session_client(self.custodian)
        self.assertEqual(client.get('/api/auth/me/').status_code, 200)
        self.custodian.is_active = False
        self.custodian.save(update_fields=['is_active'])
        self.assertEqual(client.get('/api/auth/me/').status_code, 403)
        another = APIClient(enforce_csrf_checks=True)
        token = another.get('/api/auth/csrf/').data['csrfToken']
        denied = another.post('/api/auth/login/', {'username': self.custodian.username,
            'password': 'Test-password-1234'}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.data['detail'], 'Invalid username or password.')

    def test_revoked_grant_removes_evidence_access_from_existing_session(self):
        document = self.upload()
        client = self.session_client(self.custodian)
        path = f"/api/documents/{document['id']}/"
        self.assertEqual(client.get(path).status_code, 200)
        RoleAssignment.objects.filter(user=self.custodian, role='custodian', area=self.area).delete()
        self.assertEqual(client.get('/api/auth/me/').status_code, 200)
        self.assertEqual(client.get(path).status_code, 404)
        self.assertEqual(client.get(f"/api/document-versions/{document['versions'][0]['id']}/download/").status_code, 404)

    def test_health_probe_fails_closed_when_database_is_unavailable(self):
        client = APIClient()
        with patch('hub.views.connection.cursor', side_effect=DatabaseError('synthetic unavailable')):
            response = client.get('/api/health/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data, {'status': 'unavailable'})
