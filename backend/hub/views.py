from pathlib import Path
import csv
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.db import transaction, connection, DatabaseError
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import PermissionDenied, ValidationError, MethodNotAllowed
from rest_framework.throttling import AnonRateThrottle
from .models import *
from .access import *
from .compliance import *
from .serializers import *
from .files import validate_upload
from .recovery import recovery_configured


def audit(user, area, action, record, **detail):
    AuditEvent.objects.create(actor=user, area=area, action=action, record=str(record), detail=detail)


def payload(serializer_class, request, **kwargs):
    serializer = serializer_class(data=request.data, **kwargs)
    serializer.is_valid(raise_exception=True)
    return serializer


def query_id(request, name):
    value = request.query_params.get(name)
    if value is not None and (not value.isdigit() or int(value) < 1 or len(value) > 12):
        raise ValidationError({name: 'Use a positive numeric identifier.'})
    return value


def query_text(request, name='q'):
    value = request.query_params.get(name, '').strip()
    if len(value) > 120:
        raise ValidationError({name: 'Use 120 characters or fewer.'})
    return value


def user_data(user):
    return {'id': user.id, 'name': user.get_full_name() or user.username, 'username': user.username,
            'is_staff': user.is_staff, 'assignments': list(user.assignments.values('role', 'cycle_id', 'area_id'))}


class CsrfView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'csrfToken': get_token(request)})


class HealthView(APIView):
    """Minimal unauthenticated readiness probe; it discloses no application data."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
        except DatabaseError:
            return Response({'status': 'unavailable'}, status=503)
        return Response({'status': 'ok'})


class LoginThrottle(AnonRateThrottle):
    scope = 'login'


@method_decorator(csrf_protect, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        identifier = request.data.get('username', '')
        password = request.data.get('password', '')
        if not isinstance(identifier, str) or not isinstance(password, str):
            raise ValidationError('Enter a username and password.')
        account = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier)).first()
        user = authenticate(request, username=account.username if account else identifier, password=password)
        if user is None:
            raise PermissionDenied('Invalid username or password.')
        login(request, user)
        request.session.set_expiry(8 * 60 * 60 if request.data.get('remember') is True else 0)
        audit(user, None, 'login', user.username)
        return Response(user_data(user))


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'detail': 'Signed out.'})


class PasswordChangeView(APIView):
    def post(self, request):
        data = payload(PasswordChangeInput, request, context={'request': request}).validated_data
        if not request.user.check_password(data['current_password']):
            raise ValidationError({'current_password': 'Your current password is incorrect.'})
        request.user.set_password(data['new_password'])
        request.user.save(update_fields=['password'])
        update_session_auth_hash(request, request.user)
        audit(request.user, None, 'password_changed', request.user.username)
        return Response({'detail': 'Password changed.'})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = payload(PasswordResetRequestInput, request).validated_data
        if not recovery_configured():
            return Response({'detail': 'Password recovery email is not configured. Contact an administrator for recovery.'})
        user = User.objects.filter(email__iexact=data['email'], is_active=True).first()
        if user and user.has_usable_password():
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            # Fragments are not sent in HTTP requests or included in standard proxy access logs.
            reset_url = settings.PASSWORD_RESET_FRONTEND_URL.rstrip('/') + '/#reset=1&uid=' + uid + '&token=' + token
            message = EmailMessage(
                render_to_string('hub/password_reset_subject.txt').strip(),
                render_to_string('hub/password_reset_email.txt', {'reset_url': reset_url}),
                settings.DEFAULT_FROM_EMAIL, [user.email],
            )
            try:
                message.send(fail_silently=False)
            except Exception:
                # Do not log the exception: mail transports can include message data.
                pass
        return Response({'detail': 'If an active account matches, follow the recovery instructions if they arrive. Otherwise contact an administrator.'})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not recovery_configured():
            raise ValidationError('Password recovery email is not configured. Contact an administrator for recovery.')
        data = payload(PasswordResetConfirmInput, request).validated_data
        try:
            user_id = int(force_str(urlsafe_base64_decode(data['uid'])))
            if user_id < 1:
                raise ValueError('Invalid user ID')
        except (ValueError, TypeError, OverflowError):
            raise ValidationError('This password recovery link is invalid or has expired.')
        with transaction.atomic():
            user = User.objects.select_for_update().filter(pk=user_id, is_active=True).first()
            if not user or not default_token_generator.check_token(user, data['token']):
                raise ValidationError('This password recovery link is invalid or has expired.')
            validate_password(data['new_password'], user)
            user.set_password(data['new_password'])
            user.save(update_fields=['password'])
            audit(user, None, 'password_reset', user.username)
        return Response({'detail': 'Password reset. You can now sign in.'})


class MeView(APIView):
    def get(self, request):
        return Response(user_data(request.user))


def scoped_requirements(user):
    return with_evidence(Requirement.objects.filter(area__in=areas_for(user)))


def req_data(req, user, detail=False):
    result_data = requirement_result(req)
    certification = result_data.pop('latest_certification')
    can_certify = req.area.cycle.status == 'active' and areas_for(user, ['coordinator']).filter(pk=req.area_id).exists()
    result = {'id': req.id, 'code': req.code, 'title': req.title, 'description': req.description,
        'area': req.area_id, 'area_title': req.area.title, 'icon': req.area.icon, 'cycle': req.area.cycle_id,
        'responsible': req.responsible, 'deadline': req.deadline, 'active': req.active,
        'applicable': req.applicable, 'exclusion_reason': req.exclusion_reason, **result_data,
        'criteria_revision': req.criteria_revision,
        'legacy_submission_mode': req.legacy_submission_mode,
        'can_manage': can_certify,
        'can_assign': can_certify,
        'can_upload': req.area.cycle.status == 'active' and (is_active_assignee(user, req) or can_certify)}
    if detail:
        result['assignments'] = [assignment_data(a) for a in req.user_assignments.filter(active=True).select_related('user')]
        result['items'] = [{'id': i.id, 'label': i.label, 'criteria': i.criteria, 'mandatory': i.mandatory,
                            'status': package_item_state(req, i, user) if req.packages.exists() else item_state(i),
                            'mappings': [mapping_data(m, user) for m in visible_mappings_for(user, i.mappings.all())]}
                           for i in req.items.all()]
        result['certifications'] = [certification_data(c) for c in req.certifications.all()]
        result['packages'] = [package_data(p, user) for p in visible_packages_for(user, req.packages.all())]
        result['package_choices'] = [
            {'mapping': mapping.id, 'item': mapping.item_id, 'item_label': mapping.item.label,
             'document_title': mapping.document.title, 'version': version.id,
             'version_number': version.number, 'original_name': version.original_name,
             'checksum': version.checksum, 'valid_until': version.valid_until}
            for item in req.items.all() for mapping in visible_mappings_for(user, item.mappings.all())
            if mapping.document.area_id == req.area_id
            for version in mapping.document.versions.all() if can_version(user, version)
        ] if result['can_upload'] else []
        result['applicability_history'] = [applicability_data(d) for d in req.applicability_decisions.all()]
        result['certification_candidates'] = [certification_candidate(s) for item in req.items.all()
            for mapping in item.mappings.all() for s in mapping.submissions.all()
            if s.id == next(iter(mapping.submissions.all()), s).id and submission_state(s) == 'approved']
        result['package_certification_candidates'] = [package_data(p, user) for p in req.packages.all()
            if can_certify and package_is_ready(p, req)]
        result['can_complete'] = can_certify and result['status'] == 'ready_for_completion_review'
        result['can_reopen'] = can_certify and certification_is_open(req)
    return result


def package_item_state(requirement, item, user):
    visible_attempts = list(visible_packages_for(user, requirement.packages.all()))
    for status, display in [('submitted', 'pending'), ('revisions_requested', 'revision_requested'),
                            ('approved', 'approved'), ('draft', 'draft')]:
        if any(package.status == status and (status != 'approved' or package_is_ready(package, requirement)) and
               any(entry.mapping.item_id == item.id for entry in package.items.all())
               for package in visible_attempts):
            return display
    if any(package.status == 'approved' and package_is_ready(package, requirement) and
           any(entry.mapping.item_id == item.id and can_version(user, entry.version) for entry in package.items.all())
           for package in requirement.packages.all()):
        return 'approved'
    return 'missing'


def assignment_data(assignment):
    return {'id': assignment.id, 'user': assignment.user_id,
            'name': assignment.user.get_full_name() or assignment.user.username,
            'username': assignment.user.username, 'active': assignment.active,
            'assigned_by': assignment.assigned_by.get_full_name() or assignment.assigned_by.username,
            'created_at': assignment.created_at}


def assignment_candidates(requirement):
    """Only active Custodians with an exact area grant may be assigned/steward."""
    users = User.objects.filter(is_active=True, assignments__role='custodian',
                                assignments__cycle=requirement.area.cycle,
                                assignments__area=requirement.area).distinct().order_by('username')
    return [{'id': user.id, 'name': user.get_full_name() or user.username, 'username': user.username} for user in users]


def certification_data(certification):
    return {'id': certification.id, 'outcome': certification.outcome, 'rationale': certification.rationale,
            'coordinator': certification.coordinator.get_full_name() or certification.coordinator.username,
            'created_at': certification.created_at, 'legacy': certification.outcome == 'complete' and not certification_has_support(certification),
            'criteria_snapshot': certification.criteria_snapshot,
            'evidence': [link.snapshot for link in certification.evidence.all()],
            'packages': [link.snapshot for link in certification.packages.all()]}


def package_item_snapshot(entry):
    version = entry.version
    return {'mapping': entry.mapping_id, 'item': entry.mapping.item_id,
            'item_label': entry.mapping.item.label, 'document': str(entry.mapping.document_id),
            'document_title': entry.mapping.document.title, 'version': version.id,
            'version_number': version.number, 'original_name': version.original_name,
            'checksum': version.checksum, 'valid_until': version.valid_until.isoformat() if version.valid_until else None,
            'note': entry.note}


def package_data(package, user):
    requirement = package.requirement
    editable = package.status == 'draft' and package.owner_id == user.id and requirement.area.cycle.status == 'active'
    reviewable = package.status == 'submitted' and requirement.area.cycle.status == 'active' and not certification_is_open(requirement) and (
        areas_for(user, REVIEW_ROLES).filter(pk=requirement.area_id).exists()) and user.id != package.owner_id and not any(
            entry.version.uploaded_by_id == user.id for entry in package.items.all())
    return {'id': package.id, 'requirement': requirement.id, 'requirement_title': requirement.title,
            'number': package.number, 'owner': package.owner.get_full_name() or package.owner.username,
            'owner_id': package.owner_id, 'source_attempt': package.source_attempt_id,
            'source_attempt_number': package.source_attempt.number if package.source_attempt_id else None,
            'status': package.status, 'notes': package.notes, 'criteria_revision': package.criteria_revision,
            'criteria_snapshot': package.criteria_snapshot, 'withdrawal_reason': package.withdrawal_reason,
            'created_at': package.created_at, 'submitted_at': package.submitted_at, 'resolved_at': package.resolved_at,
            'items': [entry.snapshot or package_item_snapshot(entry) for entry in package.items.all()],
            'decision': {'outcome': package.decision.outcome, 'comment': package.decision.comment,
                         'reviewer': package.decision.reviewer.get_full_name() or package.decision.reviewer.username,
                         'created_at': package.decision.created_at} if hasattr(package, 'decision') else None,
            'can_edit': editable, 'can_submit': editable, 'can_withdraw': package.status == 'submitted' and package.owner_id == user.id and requirement.area.cycle.status == 'active',
            'can_review': reviewable,
            'can_resubmit': package.status in ('approved', 'revisions_requested', 'withdrawn') and requirement.area.cycle.status == 'active' and (is_active_assignee(user, requirement) or is_scoped_coordinator(user, requirement.area)),
            'requires_override': is_scoped_coordinator(user, requirement.area) and not is_active_assignee(user, requirement)}


def applicability_data(decision):
    return {'id': decision.id, 'applicable': decision.applicable, 'reason': decision.reason,
            'coordinator': decision.coordinator.get_full_name() or decision.coordinator.username,
            'created_at': decision.created_at}


def certification_is_open(requirement):
    latest = next(iter(requirement.certifications.all()), None)
    return bool(latest and latest.outcome == 'complete')


def criteria_snapshot(requirement):
    return {'revision': requirement.criteria_revision, 'code': requirement.code, 'title': requirement.title,
            'cycle': requirement.area.cycle_id, 'area': requirement.area_id,
            'instrument': requirement.area.cycle.instrument, 'description': requirement.description,
            'items': [{'id': item.id, 'label': item.label, 'criteria': item.criteria, 'mandatory': item.mandatory}
                      for item in requirement.items.all()]}


def certification_candidate(sub):
    version = sub.version
    return {'submission': sub.id, 'item': sub.mapping.item_id, 'item_label': sub.mapping.item.label,
            'submission_criteria_revision': sub.criteria_revision,
            'document': str(sub.mapping.document_id), 'document_title': sub.mapping.document.title,
            'version': version.id, 'version_number': version.number, 'original_name': version.original_name,
            'checksum': version.checksum, 'valid_until': version.valid_until.isoformat() if version.valid_until else None,
            'review_decision': sub.decision.id}


def submission_data(sub, user):
    decision = getattr(sub, 'decision', None)
    current = sub.mapping.submissions.order_by('-id').first().id == sub.id
    return {'id': sub.id, 'mapping': sub.mapping_id, 'version': sub.version_id, 'version_number': sub.version.number,
        'criteria_revision': sub.criteria_revision,
        'document_title': sub.mapping.document.title, 'document': str(sub.mapping.document_id),
        'item_label': sub.mapping.item.label, 'requirement': sub.mapping.item.requirement_id,
        'requirement_title': sub.mapping.item.requirement.title, 'submitted_at': sub.submitted_at,
        'submitted_by': sub.submitted_by.get_full_name() or sub.submitted_by.username,
        'status': submission_state(sub), 'current': current,
        'can_review': current and not decision and submission_state(sub) != 'outdated'
            and not certification_is_open(sub.mapping.item.requirement)
            and sub.version.uploaded_by_id != user.id and sub.submitted_by_id != user.id
            and sub.mapping.item.requirement.area.cycle.status == 'active'
            and areas_for(user, REVIEW_ROLES).filter(pk=sub.mapping.item.requirement.area_id).exists(),
        'decision': {'outcome': decision.outcome, 'comment': decision.comment,
                     'reviewer': decision.reviewer.get_full_name() or decision.reviewer.username,
                     'created_at': decision.created_at} if decision else None}


def mapping_data(mapping, user):
    return {'id': mapping.id, 'document': str(mapping.document_id), 'document_title': mapping.document.title,
            'item': mapping.item_id,
            'submissions': [submission_data(s, user) for s in visible_submissions_for(user, mapping.submissions.all())]}


def version_data(version):
    return {'id': version.id, 'number': version.number, 'original_name': version.original_name,
            'content_type': version.content_type, 'size': version.size, 'checksum': version.checksum,
            'uploaded_by': version.uploaded_by.get_full_name() or version.uploaded_by.username,
            'uploaded_at': version.uploaded_at, 'valid_until': version.valid_until,
            'download_url': f'/api/document-versions/{version.id}/download/'}


def doc_data(doc, user):
    versions = [version_data(v) for v in doc.versions.all() if can_version(user, v)]
    mappings = visible_mappings_for(user, doc.mappings.all())
    return {'id': str(doc.id), 'title': doc.title, 'category': doc.category, 'area': doc.area_id,
        'area_title': doc.area.title, 'cycle': doc.area.cycle_id, 'versions': versions,
        'custodian': doc.custodian.get_full_name() or doc.custodian.username,
        'steward': (doc.steward.get_full_name() or doc.steward.username) if doc.steward else None,
        'steward_id': doc.steward_id,
        'can_upload': doc.area.cycle.status == 'active' and (doc.steward_id == user.id or is_scoped_coordinator(user, doc.area)),
        'can_delegate_stewardship': doc.area.cycle.status == 'active' and is_scoped_coordinator(user, doc.area),
        'mappings': [mapping_data(m, user) for m in mappings]}


class CyclesView(APIView):
    def get(self, request):
        records = Cycle.objects.filter(areas__in=areas_for(request.user)).distinct().order_by('-id')
        return Response([{**{'id': cycle.id, 'title': cycle.title, 'program': cycle.program,
                            'instrument': cycle.instrument, 'status': cycle.status, 'is_demo': cycle.is_demo,
                            'closed_at': cycle.closed_at},
                          'can_close': cycle.status == 'active' and has_cyclewide_coordinator(request.user, cycle),
                          'can_reopen': cycle.status == 'closed' and has_cyclewide_coordinator(request.user, cycle)}
                         for cycle in records])


class CycleTransitionView(APIView):
    action = ''

    @transaction.atomic
    def post(self, request, pk):
        cycle = get_object_or_404(Cycle.objects.select_for_update(), pk=pk)
        if not has_cyclewide_coordinator(request.user, cycle):
            raise PermissionDenied('You do not have permission to manage this accreditation cycle.')
        data = payload(CycleTransitionInput, request).validated_data
        if self.action == 'close':
            if cycle.status != 'active':
                raise ValidationError('Only an active cycle can be closed.')
            cycle.status, cycle.closed_at = 'closed', timezone.now()
            action, detail = 'cycle_closed', 'Cycle closed. Records are now read-only.'
        else:
            if cycle.status != 'closed':
                raise ValidationError('Only a closed cycle can be reopened.')
            cycle.status, cycle.closed_at = 'active', None
            action, detail = 'cycle_reopened', 'Cycle reopened. Authorized work can resume.'
        cycle.save(update_fields=['status', 'closed_at'])
        for area in cycle.areas.all():
            audit(request.user, area, action, cycle.title, rationale=data['rationale'])
        return Response({'detail': detail, 'cycle': {'id': cycle.id, 'status': cycle.status, 'closed_at': cycle.closed_at}})


class CloseCycleView(CycleTransitionView):
    action = 'close'


class ReopenCycleView(CycleTransitionView):
    action = 'reopen'


class AreasView(APIView):
    def get(self, request):
        qs = areas_for(request.user)
        if query_id(request, 'cycle'):
            qs = qs.filter(cycle_id=request.query_params['cycle'])
        return Response([{'id': a.id, 'cycle': a.cycle_id, 'title': a.title, 'code': a.code, 'icon': a.icon,
                          'can_manage': a.cycle.status == 'active' and areas_for(request.user, ['coordinator']).filter(pk=a.id).exists(),
                          'can_upload': a.cycle.status == 'active' and areas_for(request.user, WRITE_ROLES).filter(pk=a.id).exists(),
                          **summary(with_evidence(a.requirements.all()))} for a in qs])


class RequirementsView(APIView):
    def get(self, request, pk=None):
        qs = scoped_requirements(request.user)
        if pk is not None:
            return Response(req_data(get_object_or_404(qs, pk=pk), request.user, True))
        if query_id(request, 'cycle'):
            qs = qs.filter(area__cycle_id=request.query_params['cycle'])
        if query_id(request, 'area'):
            qs = qs.filter(area_id=request.query_params['area'])
        q = request.query_params.get('search', '')
        qs = qs.filter(Q(title__icontains=q) | Q(code__icontains=q) | Q(description__icontains=q) | Q(responsible__icontains=q))
        records = [req_data(r, request.user) for r in qs]
        status = request.query_params.get('status')
        return Response([r for r in records if not status or r['status'] == status])

    @transaction.atomic
    def post(self, request, pk=None):
        if pk is not None:
            raise MethodNotAllowed('POST')
        serializer = payload(RequirementInput, request)
        area = serializer.validated_data['area']
        require_area(request.user, area, ['coordinator'])
        lock_active_cycles(area.cycle_id)
        # Revalidate uniqueness after the cycle lock.
        serializer = payload(RequirementInput, request)
        req = serializer.save(created_by=request.user)
        ApplicabilityDecision.objects.create(requirement=req, coordinator=request.user, applicable=req.applicable,
            reason=serializer.validated_data.get('applicability_reason') or req.exclusion_reason or 'Initial applicable requirement.')
        audit(request.user, area, 'requirement_created', req.title, requirement=req.id)
        return Response(req_data(req, request.user, True), status=201)

    @transaction.atomic
    def patch(self, request, pk=None):
        if pk is None:
            raise MethodNotAllowed('PATCH')
        req = get_object_or_404(scoped_requirements(request.user), pk=pk)
        require_area(request.user, req.area, ['coordinator'])
        lock_active_cycles(req.area.cycle_id)
        req = Requirement.objects.select_for_update().get(pk=pk)
        serializer = payload(RequirementInput, request, instance=req, partial=True)
        data = serializer.validated_data
        substantive = ('description' in data and data['description'] != req.description) or (
            'active' in data and data['active'] != req.active) or (
            'applicable' in data and data['applicable'] != req.applicable) or (
            'exclusion_reason' in data and data['exclusion_reason'] != req.exclusion_reason)
        if substantive and req.certifications.first() and req.certifications.first().outcome == 'complete':
            raise ValidationError('Reopen the requirement with a documented reason before changing criteria, activation, or applicability.')
        before = {k: str(getattr(req, k)) for k in data if hasattr(req, k)}
        prior_description = req.description
        prior_applicable = req.applicable
        prior_exclusion_reason = req.exclusion_reason
        serializer.save()
        if req.description != prior_description:
            req.criteria_revision += 1
            req.save(update_fields=['criteria_revision'])
            audit(request.user, req.area, 'criteria_revised', req.title, requirement=req.id,
                  revision=req.criteria_revision, before=prior_description, after=req.description,
                  reason=data['change_reason'])
        if req.applicable != prior_applicable or req.exclusion_reason != prior_exclusion_reason:
            decision = ApplicabilityDecision.objects.create(requirement=req, coordinator=request.user,
                applicable=req.applicable, reason=data['applicability_reason'])
            audit(request.user, req.area, 'applicability_decided', req.title,
                  decision=decision.id, applicable=req.applicable, reason=decision.reason)
        audit(request.user, req.area, 'requirement_updated', req.title, before=before,
              after={k: str(getattr(req, k)) for k in data if hasattr(req, k)})
        return Response(req_data(req, request.user, True))


class ItemsView(APIView):
    def get(self, request):
        qs = EvidenceItem.objects.filter(requirement__area__in=areas_for(request.user))
        if query_id(request, 'requirement'):
            qs = qs.filter(requirement_id=request.query_params['requirement'])
        return Response(list(qs.values('id', 'requirement_id', 'label', 'criteria', 'mandatory')))


class DocumentsView(APIView):
    def get(self, request, pk=None):
        qs = documents_for(request.user).select_related('area__cycle', 'custodian').prefetch_related('versions__uploaded_by')
        if pk:
            return Response(doc_data(get_object_or_404(qs, pk=pk), request.user))
        if query_id(request, 'cycle'):
            cycle_id = request.query_params['cycle']
            qs = qs.filter(
                Q(area__cycle_id=cycle_id) |
                Q(versions__in=visible_versions_for(request.user).filter(
                    submissions__mapping__item__requirement__area__cycle_id=cycle_id))
            ).distinct()
        q = request.query_params.get('search', '')
        visible_mapping_matches = visible_mappings_for(request.user).filter(
            item__requirement__title__icontains=q
        )
        # Search only document metadata and mappings visible to the requester.
        qs = qs.filter(Q(title__icontains=q) | Q(category__icontains=q) | Q(custodian__first_name__icontains=q) |
                       Q(custodian__last_name__icontains=q) | Q(mappings__in=visible_mapping_matches)).distinct()
        return Response([doc_data(d, request.user) for d in qs.order_by('-created_at')])

    def post(self, request, pk=None):
        if pk is not None:
            raise MethodNotAllowed('POST')
        return upload_document(request)


def upload_document(request, document_id=None):
    data = payload(UploadInput, request).validated_data
    name, content_type, contents, checksum = validate_upload(data['file'])
    storage_path = None
    try:
        with transaction.atomic():
            if document_id:
                doc = get_object_or_404(Document.objects.filter(area__in=areas_for(request.user, WRITE_ROLES)), pk=document_id)
                require_area(request.user, doc.area, WRITE_ROLES)
                lock_active_cycles(doc.area.cycle_id)
                doc = Document.objects.select_for_update().get(pk=doc.pk)
                overridden = require_document_steward_or_coordinator_override(
                    request.user, doc, data.get('override_reason'), 'version replacement')
            else:
                if not data.get('title') or not data.get('area') or not data.get('requirement'):
                    raise ValidationError('A document title, owning area, and requirement are required.')
                area = get_object_or_404(areas_for(request.user, WRITE_ROLES), pk=data['area'])
                requirement = get_object_or_404(Requirement.objects.filter(area=area), pk=data['requirement'])
                lock_active_cycles(area.cycle_id)
                overridden = require_assignee_or_coordinator_override(
                    request.user, requirement, data.get('override_reason'), 'upload')
                doc = Document.objects.create(title=data['title'], category=data['category'], area=area,
                                              custodian=request.user, steward=request.user)
            last = doc.versions.order_by('-number').first()
            version = DocumentVersion.objects.create(document=doc, number=last.number + 1 if last else 1,
                original_name=name, content_type=content_type, size=len(contents), checksum=checksum,
                uploaded_by=request.user, valid_until=data.get('valid_until'))
            settings.PRIVATE_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
            storage_path = settings.PRIVATE_MEDIA_ROOT / str(version.storage_key)
            with storage_path.open('xb') as output:
                output.write(contents)
            audit(request.user, doc.area, 'version_uploaded', doc.title, version=version.id, number=version.number,
                  steward=doc.steward_id, override=overridden,
                  override_reason=data.get('override_reason', '') if overridden else '')
            result = doc_data(doc, request.user)
        return Response(result, status=201)
    except Exception:
        if storage_path and storage_path.exists():
            storage_path.unlink()
        raise


class VersionsView(APIView):
    def get(self, request, pk):
        doc = get_object_or_404(documents_for(request.user), pk=pk)
        return Response([version_data(v) for v in doc.versions.all() if can_version(request.user, v)])

    def post(self, request, pk):
        return upload_document(request, pk)


class DownloadView(APIView):
    def get(self, request, pk):
        version = get_object_or_404(DocumentVersion.objects.select_related('document__area'), pk=pk)
        if not can_version(request.user, version):
            raise Http404
        path = settings.PRIVATE_MEDIA_ROOT / str(version.storage_key)
        if not path.is_file():
            raise Http404('Stored file unavailable.')
        audit(request.user, version.document.area, 'version_downloaded', version.document.title, version=pk)
        response = FileResponse(path.open('rb'), as_attachment=True, filename=version.original_name, content_type=version.content_type)
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class RequirementAssignmentsView(APIView):
    def get(self, request, pk):
        requirement = get_object_or_404(scoped_requirements(request.user), pk=pk)
        if not is_scoped_coordinator(request.user, requirement.area):
            raise PermissionDenied('Only a scoped Coordinator may manage assignments.')
        return Response({'assignments': [assignment_data(a) for a in requirement.user_assignments.filter(active=True).select_related('user')],
                         'candidates': assignment_candidates(requirement)})

    @transaction.atomic
    def post(self, request, pk):
        requirement = get_object_or_404(scoped_requirements(request.user), pk=pk)
        require_area(request.user, requirement.area, ['coordinator'])
        lock_active_cycles(requirement.area.cycle_id)
        requirement = Requirement.objects.select_for_update().get(pk=requirement.pk)
        data = payload(RequirementAssignmentInput, request).validated_data
        candidate = get_object_or_404(User.objects.filter(is_active=True), pk=data['user'])
        if candidate.id not in [entry['id'] for entry in assignment_candidates(requirement)]:
            raise ValidationError({'user': 'The assignee must be active and have a Custodian grant in this requirement area and cycle.'})
        if data['replace']:
            removed = list(requirement.user_assignments.select_for_update().filter(active=True).exclude(user=candidate))
            for assignment in removed:
                assignment.active = False
                assignment.save(update_fields=['active', 'updated_at'])
                audit(request.user, requirement.area, 'requirement_assignment_deactivated', requirement.title,
                      assignment=assignment.id, assignee=assignment.user_id, reason=data['reason'])
        assignment, created = RequirementAssignment.objects.select_for_update().get_or_create(
            requirement=requirement, user=candidate,
            defaults={'active': True, 'assigned_by': request.user},
        )
        if not created and assignment.active:
            raise ValidationError({'user': 'This user is already an active assignee.'})
        if not created:
            assignment.active = True
            assignment.assigned_by = request.user
            assignment.save(update_fields=['active', 'assigned_by', 'updated_at'])
        audit(request.user, requirement.area,
              'requirement_reassigned' if data['replace'] else 'requirement_assigned', requirement.title,
              assignment=assignment.id, assignee=candidate.id, replace=data['replace'], reason=data['reason'])
        return Response(assignment_data(assignment), status=201 if created else 200)


class DocumentStewardshipView(APIView):
    def get(self, request, pk):
        document = get_object_or_404(documents_for(request.user).select_related('area__cycle'), pk=pk)
        if not is_scoped_coordinator(request.user, document.area):
            raise PermissionDenied('Only a scoped Coordinator may delegate document stewardship.')
        candidates = User.objects.filter(is_active=True, assignments__role='custodian',
                                         assignments__cycle=document.area.cycle,
                                         assignments__area=document.area).distinct().order_by('username')
        return Response({'steward_id': document.steward_id,
                         'candidates': [{'id': u.id, 'name': u.get_full_name() or u.username, 'username': u.username} for u in candidates]})

    @transaction.atomic
    def post(self, request, pk):
        document = get_object_or_404(Document.objects.select_for_update().select_related('area__cycle'), pk=pk)
        require_area(request.user, document.area, ['coordinator'])
        lock_active_cycles(document.area.cycle_id)
        data = payload(StewardshipInput, request).validated_data
        candidate = get_object_or_404(User.objects.filter(is_active=True), pk=data['steward'])
        eligible = RoleAssignment.objects.filter(user=candidate, role='custodian', cycle=document.area.cycle,
                                                  area=document.area).exists()
        if not eligible:
            raise ValidationError({'steward': 'The steward must be active and have a Custodian grant in this document area and cycle.'})
        previous = document.steward_id
        document.steward = candidate
        document.save(update_fields=['steward'])
        audit(request.user, document.area, 'document_stewardship_delegated', document.title,
              document=str(document.id), previous_steward=previous, steward=candidate.id, reason=data['reason'])
        return Response(doc_data(document, request.user))


class MappingsView(APIView):
    def get(self, request):
        qs = visible_mappings_for(request.user)
        return Response([mapping_data(m, request.user) for m in qs])

    @transaction.atomic
    def post(self, request):
        data = payload(MappingInput, request).validated_data
        item = get_object_or_404(EvidenceItem.objects.filter(requirement__area__in=areas_for(request.user, WRITE_ROLES)), pk=data['item'])
        doc = get_object_or_404(documents_for(request.user), pk=data['document'])
        require_area(request.user, doc.area, WRITE_ROLES)
        if doc.area_id != item.requirement.area_id or doc.area.cycle_id != item.requirement.area.cycle_id:
            raise ValidationError('Evidence can be mapped only within its owning area and cycle.')
        lock_active_cycles(item.requirement.area.cycle_id)
        if certification_is_open(item.requirement):
            raise ValidationError('Reopen the requirement before changing supporting evidence.')
        requirement_override = require_assignee_or_coordinator_override(
            request.user, item.requirement, data.get('override_reason'), 'mapping')
        stewardship_override = require_document_steward_or_coordinator_override(
            request.user, doc, data.get('override_reason'), 'mapping')
        mapping, created = EvidenceMapping.objects.get_or_create(item=item, document=doc, defaults={'created_by': request.user})
        if created:
            audit(request.user, item.requirement.area, 'evidence_mapped', doc.title, mapping=mapping.id, item=item.id,
                  override=requirement_override or stewardship_override,
                  override_reason=data.get('override_reason', '') if requirement_override or stewardship_override else '')
        return Response(mapping_data(mapping, request.user), status=201 if created else 200)


class SubmissionsView(APIView):
    def get(self, request):
        qs = visible_submissions_for(request.user).select_related(
            'mapping__item__requirement__area__cycle', 'mapping__document', 'version', 'submitted_by', 'decision__reviewer')
        if query_id(request, 'cycle'):
            qs = qs.filter(mapping__item__requirement__area__cycle_id=request.query_params['cycle'])
        return Response([submission_data(s, request.user) for s in qs])

    @transaction.atomic
    def post(self, request):
        data = payload(SubmitInput, request).validated_data
        mapping = get_object_or_404(EvidenceMapping.objects.filter(item__requirement__area__in=areas_for(request.user, WRITE_ROLES)), pk=data['mapping'])
        require_area(request.user, mapping.document.area, WRITE_ROLES)
        if mapping.document.area_id != mapping.item.requirement.area_id or mapping.document.area.cycle_id != mapping.item.requirement.area.cycle_id:
            raise ValidationError('Evidence can be submitted only within its owning area and cycle.')
        lock_active_cycles(mapping.item.requirement.area.cycle_id)
        if not mapping.item.requirement.legacy_submission_mode:
            raise ValidationError('New evidence work uses requirement-level package attempts.')
        if certification_is_open(mapping.item.requirement):
            raise ValidationError('Reopen the requirement before replacing supporting evidence.')
        mapping = EvidenceMapping.objects.select_for_update().get(pk=mapping.pk)
        requirement_override = require_assignee_or_coordinator_override(
            request.user, mapping.item.requirement, data.get('override_reason'), 'submission')
        stewardship_override = require_document_steward_or_coordinator_override(
            request.user, mapping.document, data.get('override_reason'), 'submission')
        version = get_object_or_404(DocumentVersion, pk=data['version'], document=mapping.document)
        if not can_version(request.user, version):
            raise PermissionDenied()
        if mapping.submissions.filter(version=version).exists():
            raise ValidationError('This version has already been submitted. Upload a new version for resubmission.')
        latest = mapping.submissions.first()
        if latest and latest.version.number >= version.number:
            raise ValidationError('A replacement must be a newer version.')
        if version.valid_until and version.valid_until < timezone.localdate():
            raise ValidationError('Expired evidence cannot be submitted.')
        sub = Submission.objects.create(mapping=mapping, version=version, submitted_by=request.user,
            criteria_revision=mapping.item.requirement.criteria_revision)
        audit(request.user, mapping.item.requirement.area, 'evidence_submitted', mapping.document.title, submission=sub.id,
              version=version.id, override=requirement_override or stewardship_override,
              override_reason=data.get('override_reason', '') if requirement_override or stewardship_override else '')
        return Response(submission_data(sub, request.user), status=201)


class ReviewsView(APIView):
    def get(self, request):
        qs = ReviewDecision.objects.filter(submission__in=visible_submissions_for(request.user))
        return Response(list(qs.values('id', 'submission_id', 'outcome', 'comment', 'created_at')))

    @transaction.atomic
    def post(self, request):
        data = payload(ReviewInput, request).validated_data
        sub = get_object_or_404(Submission.objects.filter(mapping__item__requirement__area__in=areas_for(request.user, REVIEW_ROLES)), pk=data['submission'])
        area = sub.mapping.item.requirement.area
        lock_active_cycles(area.cycle_id)
        if certification_is_open(sub.mapping.item.requirement):
            raise ValidationError('Reopen the requirement before reviewing changed supporting evidence.')
        EvidenceMapping.objects.select_for_update().get(pk=sub.mapping_id)
        sub = Submission.objects.select_for_update().select_related('version').get(pk=sub.pk)
        if submission_state(sub) == 'outdated':
            raise ValidationError('This submission uses outdated criteria. Submit a new version after the criteria revision.')
        if sub.version.uploaded_by_id == request.user.id or sub.submitted_by_id == request.user.id:
            raise PermissionDenied('You cannot review your own upload or submission.')
        if sub.mapping.submissions.first().id != sub.id or ReviewDecision.objects.filter(submission=sub).exists():
            raise ValidationError('This submission has already been reviewed or superseded. Refresh the page.')
        if data['outcome'] == 'approved' and sub.version.valid_until and sub.version.valid_until < timezone.localdate():
            raise ValidationError('Expired evidence cannot be approved.')
        ReviewDecision.objects.create(submission=sub, reviewer=request.user, outcome=data['outcome'], comment=data['comment'])
        audit(request.user, area, data['outcome'], sub.mapping.document.title, submission=sub.id, version=sub.version_id, comment=data['comment'])
        return Response(submission_data(Submission.objects.get(pk=sub.pk), request.user), status=201)


def validated_package_items(user, requirement, entries, override_reason):
    if len(entries) != len({entry['mapping'] for entry in entries}) or len(entries) != len({entry['version'] for entry in entries}):
        raise ValidationError({'items': 'Choose each mapping and version at most once.'})
    result = []
    for entry in entries:
        mapping = get_object_or_404(EvidenceMapping.objects.select_related('item', 'document'),
                                    pk=entry['mapping'], item__requirement=requirement)
        if mapping.document.area_id != requirement.area_id:
            raise ValidationError({'items': 'Package evidence must belong to the requirement area and cycle.'})
        version = get_object_or_404(DocumentVersion, pk=entry['version'], document=mapping.document)
        if not can_version(user, version):
            raise PermissionDenied('The selected version is not visible in your scope.')
        require_document_steward_or_coordinator_override(user, mapping.document, override_reason, 'package evidence selection')
        if version.valid_until and version.valid_until < timezone.localdate():
            raise ValidationError({'items': 'Expired versions cannot be submitted in a package.'})
        result.append((mapping, version, entry.get('note', '')))
    return result


class PackagesView(APIView):
    def get(self, request, pk=None):
        qs = visible_packages_for(request.user).select_related('requirement__area__cycle', 'owner', 'decision__reviewer').prefetch_related(
            'items__mapping__item', 'items__mapping__document', 'items__version')
        if pk is not None:
            return Response(package_data(get_object_or_404(qs, pk=pk), request.user))
        if query_id(request, 'requirement'):
            qs = qs.filter(requirement_id=request.query_params['requirement'])
        if query_id(request, 'cycle'):
            qs = qs.filter(requirement__area__cycle_id=request.query_params['cycle'])
        return Response([package_data(package, request.user) for package in qs.order_by('-id')])

    @transaction.atomic
    def post(self, request, pk=None):
        if pk is not None:
            raise MethodNotAllowed('POST')
        data = payload(PackageDraftInput, request).validated_data
        if 'requirement' not in data:
            raise ValidationError({'requirement': 'Select a requirement.'})
        requirement = get_object_or_404(Requirement.objects.select_related('area__cycle').filter(
            area__in=areas_for(request.user, WRITE_ROLES)), pk=data['requirement'])
        lock_active_cycles(requirement.area.cycle_id)
        requirement = Requirement.objects.select_for_update().get(pk=requirement.pk)
        override = require_assignee_or_coordinator_override(request.user, requirement, data.get('override_reason'), 'package draft')
        selections = validated_package_items(request.user, requirement, data.get('items', []), data.get('override_reason'))
        number = (requirement.packages.order_by('-number').first().number + 1) if requirement.packages.exists() else 1
        package = PackageAttempt.objects.create(requirement=requirement, number=number, owner=request.user,
                                                notes=data.get('notes', ''))
        for mapping, version, note in selections:
            PackageItem.objects.create(package=package, mapping=mapping, version=version, note=note)
        if requirement.legacy_submission_mode:
            requirement.legacy_submission_mode = False
            requirement.save(update_fields=['legacy_submission_mode'])
        audit(request.user, requirement.area, 'package_draft_created', requirement.title,
              package=package.id, attempt=number, override=override, override_reason=data.get('override_reason', '') if override else '')
        return Response(package_data(package, request.user), status=201)

    @transaction.atomic
    def patch(self, request, pk=None):
        if pk is None:
            raise MethodNotAllowed('PATCH')
        package = get_object_or_404(visible_packages_for(request.user), pk=pk)
        lock_active_cycles(package.requirement.area.cycle_id)
        package = PackageAttempt.objects.select_for_update().select_related('requirement__area').get(pk=pk)
        if package.status != 'draft' or package.owner_id != request.user.id:
            raise PermissionDenied('Only the draft owner may edit it.')
        data = payload(PackageDraftInput, request).validated_data
        if 'requirement' in data and data['requirement'] != package.requirement_id:
            raise ValidationError('A package cannot move to another requirement.')
        require_assignee_or_coordinator_override(request.user, package.requirement, data.get('override_reason'), 'package edit')
        if 'items' in data:
            selections = validated_package_items(request.user, package.requirement, data['items'], data.get('override_reason'))
            for entry in package.items.all():
                entry.delete()
            for mapping, version, note in selections:
                PackageItem.objects.create(package=package, mapping=mapping, version=version, note=note)
        if 'notes' in data:
            package.notes = data['notes']
            package.save(update_fields=['notes'])
        audit(request.user, package.requirement.area, 'package_draft_edited', package.requirement.title, package=package.id)
        return Response(package_data(package, request.user))

    @transaction.atomic
    def delete(self, request, pk=None):
        if pk is None:
            raise MethodNotAllowed('DELETE')
        package = get_object_or_404(visible_packages_for(request.user), pk=pk)
        lock_active_cycles(package.requirement.area.cycle_id)
        package = PackageAttempt.objects.select_for_update().get(pk=pk)
        if package.status != 'draft' or package.owner_id != request.user.id:
            raise PermissionDenied('Only the owner may delete an unsubmitted draft.')
        for entry in package.items.all():
            entry.delete()
        requirement = package.requirement
        number = package.number
        package.delete()
        audit(request.user, requirement.area, 'package_draft_deleted', requirement.title, attempt=number)
        return Response(status=204)


class PackageSubmitView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        package = get_object_or_404(visible_packages_for(request.user), pk=pk)
        lock_active_cycles(package.requirement.area.cycle_id)
        package = PackageAttempt.objects.select_for_update().select_related('requirement__area__cycle').get(pk=pk)
        if package.status != 'draft' or package.owner_id != request.user.id:
            raise PermissionDenied('Only the draft owner may submit it.')
        data = payload(PackageActionInput, request).validated_data
        requirement = package.requirement
        require_assignee_or_coordinator_override(request.user, requirement, data.get('override_reason'), 'package submission')
        if certification_is_open(requirement):
            raise ValidationError('Reopen the requirement before submitting changed supporting evidence.')
        if requirement.packages.filter(status='submitted').exclude(pk=package.pk).exists():
            raise ValidationError('Another package is awaiting review for this requirement.')
        if any(not hasattr(submission, 'decision') for mapping in EvidenceMapping.objects.filter(item__requirement=requirement)
               for submission in mapping.submissions.all()[:1]):
            raise ValidationError('Resolve the legacy item-level pending review before submitting a package.')
        entries = list(package.items.select_related('mapping__item', 'mapping__document', 'version'))
        if not entries:
            raise ValidationError({'items': 'A package needs at least one pinned evidence version.'})
        validated_package_items(request.user, requirement,
            [{'mapping': entry.mapping_id, 'version': entry.version_id, 'note': entry.note} for entry in entries], data.get('override_reason'))
        for entry in entries:
            entry.snapshot = package_item_snapshot(entry)
            entry.save(update_fields=['snapshot'])
        package.criteria_revision = requirement.criteria_revision
        package.criteria_snapshot = criteria_snapshot(requirement)
        package.submitted_at = timezone.now()
        package.status = 'submitted'
        package.save(update_fields=['criteria_revision', 'criteria_snapshot', 'submitted_at', 'status'])
        audit(request.user, requirement.area, 'package_submitted', requirement.title, package=package.id, attempt=package.number)
        return Response(package_data(package, request.user))


class PackageWithdrawView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        package = get_object_or_404(visible_packages_for(request.user), pk=pk)
        lock_active_cycles(package.requirement.area.cycle_id)
        package = PackageAttempt.objects.select_for_update().get(pk=pk)
        data = payload(PackageActionInput, request).validated_data
        if package.status != 'submitted' or package.owner_id != request.user.id:
            raise PermissionDenied('Only the submitter may withdraw a package before review.')
        if not data['confirm']:
            raise ValidationError({'confirm': 'Confirm withdrawal of this submitted attempt.'})
        package.status = 'withdrawn'
        package.withdrawal_reason = data.get('reason', '')
        package.resolved_at = timezone.now()
        package.save(update_fields=['status', 'withdrawal_reason', 'resolved_at'])
        audit(request.user, package.requirement.area, 'package_withdrawn', package.requirement.title,
              package=package.id, reason=package.withdrawal_reason)
        return Response(package_data(package, request.user))


class PackageReviewView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        package = get_object_or_404(PackageAttempt.objects.filter(requirement__area__in=areas_for(request.user, REVIEW_ROLES)), pk=pk)
        lock_active_cycles(package.requirement.area.cycle_id)
        package = PackageAttempt.objects.select_for_update().select_related('requirement__area__cycle').get(pk=pk)
        data = payload(PackageReviewInput, request).validated_data
        if package.status != 'submitted':
            raise ValidationError('This package is no longer awaiting review. Refresh the page.')
        if certification_is_open(package.requirement):
            raise ValidationError('Reopen the requirement before reviewing changed supporting evidence.')
        entries = list(package.items.select_related('version', 'mapping__item', 'mapping__document'))
        if package.owner_id == request.user.id or any(entry.version.uploaded_by_id == request.user.id for entry in entries):
            raise PermissionDenied('You cannot review your own package or an upload in it.')
        if data['outcome'] == 'approved':
            if package.criteria_revision != package.requirement.criteria_revision:
                raise ValidationError('Outdated criteria require a revision request and a new attempt.')
            required = set(package.requirement.items.filter(mandatory=True).values_list('id', flat=True))
            if not required.issubset({entry.mapping.item_id for entry in entries}):
                raise ValidationError('Missing mandatory evidence requires a revision request.')
            if any(entry.version.valid_until and entry.version.valid_until < timezone.localdate() for entry in entries):
                raise ValidationError('Expired evidence cannot be approved.')
        package.status = data['outcome']
        package.resolved_at = timezone.now()
        package.save(update_fields=['status', 'resolved_at'])
        PackageDecision.objects.create(package=package, reviewer=request.user,
                                       outcome=data['outcome'], comment=data.get('comment', ''))
        audit(request.user, package.requirement.area, 'package_' + data['outcome'], package.requirement.title,
              package=package.id, comment=data.get('comment', ''))
        return Response(package_data(package, request.user), status=201)


class PackageResubmitView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        source = get_object_or_404(visible_packages_for(request.user), pk=pk)
        lock_active_cycles(source.requirement.area.cycle_id)
        requirement = Requirement.objects.select_for_update().get(pk=source.requirement_id)
        data = payload(PackageActionInput, request).validated_data
        if source.status not in ('approved', 'revisions_requested', 'withdrawn'):
            raise ValidationError('Only a terminal attempt can seed a new draft.')
        require_assignee_or_coordinator_override(request.user, requirement, data.get('override_reason'), 'package resubmission')
        number = requirement.packages.order_by('-number').first().number + 1
        package = PackageAttempt.objects.create(requirement=requirement, number=number, owner=request.user,
                                                source_attempt=source, notes=source.notes)
        if data['copy_items']:
            validated_package_items(request.user, requirement,
                [{'mapping': entry.mapping_id, 'version': entry.version_id, 'note': entry.note}
                 for entry in source.items.all()], data.get('override_reason'))
            for entry in source.items.all():
                PackageItem.objects.create(package=package, mapping=entry.mapping, version=entry.version, note=entry.note)
        audit(request.user, requirement.area, 'package_resubmission_draft_created', requirement.title,
              package=package.id, source_attempt=source.id)
        return Response(package_data(package, request.user), status=201)


class RequirementCertificationsView(APIView):
    def get(self, request, pk):
        requirement = get_object_or_404(scoped_requirements(request.user), pk=pk)
        return Response([certification_data(certification) for certification in requirement.certifications.all()])

    @transaction.atomic
    def post(self, request, pk):
        requirement = get_object_or_404(scoped_requirements(request.user), pk=pk)
        require_area(request.user, requirement.area, ['coordinator'])
        lock_active_cycles(requirement.area.cycle_id)
        requirement = with_evidence(Requirement.objects.select_for_update()).get(pk=requirement.pk)
        data = payload(CertificationInput, request).validated_data
        result = requirement_result(requirement)
        latest = result['latest_certification']
        if data['outcome'] == 'complete':
            if result['status'] != 'ready_for_completion_review':
                raise ValidationError('Only a requirement with all mandatory evidence approved can be completed.')
            if requirement.packages.exists():
                selected_ids = data.get('packages')
                if data.get('submissions') or not selected_ids or len(selected_ids) != len(set(selected_ids)):
                    raise ValidationError({'packages': 'Select distinct approved package attempts deliberately.'})
                candidates = {p.id: p for p in requirement.packages.all() if package_is_ready(p, requirement)}
                if any(pid not in candidates for pid in selected_ids):
                    raise ValidationError({'packages': 'Every selection must be an approved, current package for this requirement.'})
                mandatory = {i.id for i in requirement.items.all() if i.mandatory}
                selected_items = {entry.mapping.item_id for pid in selected_ids for entry in candidates[pid].items.all()}
                if not mandatory.issubset(selected_items):
                    raise ValidationError({'packages': 'Selected packages must cover every mandatory item.'})
            else:
                selected_ids = data.get('submissions')
                if data.get('packages') or not selected_ids or len(selected_ids) != len(set(selected_ids)):
                    raise ValidationError({'submissions': 'Select distinct approved submissions deliberately.'})
                candidates = {s['submission']: s for s in req_data(requirement, request.user, True)['certification_candidates']}
                if any(sid not in candidates for sid in selected_ids):
                    raise ValidationError({'submissions': 'Every selection must be a current, approved, unexpired submission for this requirement.'})
                mandatory = {i.id for i in requirement.items.all() if i.mandatory}
                if not mandatory.issubset({candidates[sid]['item'] for sid in selected_ids}):
                    raise ValidationError({'submissions': 'Select approved evidence for every mandatory item.'})
            action = 'requirement_completed'
        else:
            if not latest or latest.outcome != 'complete':
                raise ValidationError('Only a completed requirement can be reopened.')
            if data.get('submissions') or data.get('packages'):
                raise ValidationError('Reopening does not select evidence.')
            action = 'requirement_reopened'
        certification = RequirementCertification.objects.create(
            requirement=requirement, coordinator=request.user, outcome=data['outcome'], rationale=data['rationale'],
            criteria_snapshot=criteria_snapshot(requirement) if data['outcome'] == 'complete' else None)
        if data['outcome'] == 'complete':
            if requirement.packages.exists():
                for pid in selected_ids:
                    package = candidates[pid]
                    CertificationPackage.objects.create(certification=certification, package=package,
                        snapshot={'package': package.id, 'attempt': package.number, 'owner': package.owner_id,
                                  'criteria_revision': package.criteria_revision,
                                  'items': [entry.snapshot for entry in package.items.all()]})
            else:
                for sid in selected_ids:
                    CertificationEvidence.objects.create(certification=certification, submission_id=sid,
                        snapshot=candidates[sid])
        audit(request.user, requirement.area, action, requirement.title,
              certification=certification.id, rationale=certification.rationale)
        requirement = with_evidence(Requirement.objects).get(pk=requirement.pk)
        return Response({'certification': certification_data(certification), 'requirement': req_data(requirement, request.user, True)}, status=201)


class ComplianceView(APIView):
    def get(self, request):
        qs = scoped_requirements(request.user)
        if query_id(request, 'cycle'):
            qs = qs.filter(area__cycle_id=request.query_params['cycle'])
        return Response({**summary(qs), 'calculated_at': timezone.now(), 'scope': 'Your authorized areas'})


REPORT_STATUSES = {'complete', 'for_verification', 'needs_revision', 'ready_for_completion_review', 'in_progress', 'missing', 'draft', 'excluded'}


def report_rows(request):
    qs = scoped_requirements(request.user)
    cycle_id = query_id(request, 'cycle')
    if cycle_id:
        qs = qs.filter(area__cycle_id=cycle_id)
    area_id = query_id(request, 'area')
    if area_id:
        qs = qs.filter(area_id=area_id)
    requested_status = request.query_params.get('status', '')
    if requested_status and requested_status not in REPORT_STATUSES:
        raise ValidationError({'status': 'Choose a valid requirement status.'})
    rows = []
    for requirement in qs.order_by('area__title', 'code'):
        result = requirement_result(requirement)
        if requested_status and result['status'] != requested_status:
            continue
        rows.append((requirement, result))
    return rows


def report_data(request):
    rows = report_rows(request)
    requirements = [requirement for requirement, _ in rows]
    return {
        **summary(requirements),
        'calculated_at': timezone.now(),
        'scope': 'Your authorized areas',
        'rows': [{'id': requirement.id, 'code': requirement.code, 'title': requirement.title,
                  'area': requirement.area.title, 'responsible': requirement.responsible,
                  'deadline': requirement.deadline, 'status': result['status'],
                  'approved_items': result['approved_items'], 'required_items': result['required_items']}
                 for requirement, result in rows],
    }


def csv_cell(value):
    value = '' if value is None else str(value)
    return "'" + value if value.startswith(('=', '+', '-', '@', '\t', '\r')) else value


class ComplianceReportView(APIView):
    def get(self, request):
        data = report_data(request)
        if request.query_params.get('download') != 'csv':
            return Response(data)
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="mc-accreditation-compliance.csv"'
        writer = csv.writer(response)
        writer.writerow(['MC Accreditation Hub compliance report'])
        writer.writerow(['Scope', data['scope']])
        writer.writerow(['Compliance percentage', '' if data['percentage'] is None else data['percentage']])
        writer.writerow(['Completed requirements', data['complete']])
        writer.writerow([])
        writer.writerow(['Area', 'Code', 'Requirement', 'Responsible', 'Deadline', 'Approved evidence', 'Status'])
        for row in data['rows']:
            writer.writerow([csv_cell(row['area']), csv_cell(row['code']), csv_cell(row['title']),
                             csv_cell(row['responsible']), row['deadline'] or '',
                             f"{row['approved_items']}/{row['required_items']}", row['status']])
        return response


class SearchView(APIView):
    def get(self, request):
        term = query_text(request)
        if not term:
            raise ValidationError({'q': 'Enter a search term.'})
        cycle_id = query_id(request, 'cycle')
        requirement_qs = scoped_requirements(request.user)
        document_qs = documents_for(request.user).select_related('area', 'area__cycle').prefetch_related('versions')
        if cycle_id:
            requirement_qs = requirement_qs.filter(area__cycle_id=cycle_id)
            document_qs = document_qs.filter(
                Q(area__cycle_id=cycle_id) |
                Q(versions__in=visible_versions_for(request.user).filter(
                    submissions__mapping__item__requirement__area__cycle_id=cycle_id))
            ).distinct()
        requirement_qs = requirement_qs.filter(
            Q(code__icontains=term) | Q(title__icontains=term) | Q(description__icontains=term) |
            Q(responsible__icontains=term) | Q(area__title__icontains=term)).order_by('area__title', 'code')[:50]
        visible_filename_versions = visible_versions_for(request.user).filter(original_name__icontains=term)
        document_qs = document_qs.filter(
            Q(title__icontains=term) | Q(category__icontains=term) | Q(area__title__icontains=term) |
            Q(custodian__first_name__icontains=term) | Q(custodian__last_name__icontains=term) |
            Q(versions__in=visible_filename_versions)).distinct().order_by('title')[:50]
        return Response({
            'requirements': [{'id': req.id, 'code': req.code, 'title': req.title, 'area': req.area.title,
                              'status': requirement_result(req)['status']} for req in requirement_qs],
            'documents': [{'id': str(doc.id), 'title': doc.title, 'category': doc.category,
                           'area': doc.area.title} for doc in document_qs],
        })


class AuditView(APIView):
    def get(self, request):
        qs = AuditEvent.objects.filter(area__in=areas_for(request.user, ['coordinator', 'viewer'])).select_related('actor')
        if query_id(request, 'cycle'):
            qs = qs.filter(area__cycle_id=request.query_params['cycle'])
        term = query_text(request, 'search')
        if term:
            qs = qs.filter(Q(record__icontains=term) | Q(action__icontains=term) |
                           Q(actor__first_name__icontains=term) | Q(actor__last_name__icontains=term) |
                           Q(actor__username__icontains=term))
        action = request.query_params.get('action', '')
        if action:
            if len(action) > 80:
                raise ValidationError({'action': 'Use 80 characters or fewer.'})
            qs = qs.filter(action=action)
        return Response([{'id': e.id, 'actor': e.actor.get_full_name() or e.actor.username if e.actor else 'System',
            'action': e.action, 'record': e.record, 'detail': e.detail, 'created_at': e.created_at} for e in qs[:200]])
