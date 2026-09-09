from pathlib import Path
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
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


def user_data(user):
    return {'id': user.id, 'name': user.get_full_name() or user.username, 'username': user.username,
            'is_staff': user.is_staff, 'assignments': list(user.assignments.values('role', 'cycle_id', 'area_id'))}


class CsrfView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'csrfToken': get_token(request)})


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
        'can_manage': can_certify,
        'can_upload': req.area.cycle.status == 'active' and areas_for(user, WRITE_ROLES).filter(pk=req.area_id).exists()}
    if detail:
        result['items'] = [{'id': i.id, 'label': i.label, 'criteria': i.criteria, 'mandatory': i.mandatory,
                            'status': item_state(i), 'mappings': [mapping_data(m, user) for m in i.mappings.all()]} for i in req.items.all()]
        result['certifications'] = [certification_data(c) for c in req.certifications.all()]
        result['can_complete'] = can_certify and result['status'] == 'ready_for_completion_review'
        result['can_reopen'] = can_certify and result['status'] == 'complete'
    return result


def certification_data(certification):
    return {'id': certification.id, 'outcome': certification.outcome, 'rationale': certification.rationale,
            'coordinator': certification.coordinator.get_full_name() or certification.coordinator.username,
            'created_at': certification.created_at}


def submission_data(sub, user):
    decision = getattr(sub, 'decision', None)
    current = sub.mapping.submissions.order_by('-id').first().id == sub.id
    return {'id': sub.id, 'mapping': sub.mapping_id, 'version': sub.version_id, 'version_number': sub.version.number,
        'document_title': sub.mapping.document.title, 'document': str(sub.mapping.document_id),
        'item_label': sub.mapping.item.label, 'requirement': sub.mapping.item.requirement_id,
        'requirement_title': sub.mapping.item.requirement.title, 'submitted_at': sub.submitted_at,
        'submitted_by': sub.submitted_by.get_full_name() or sub.submitted_by.username,
        'status': submission_state(sub), 'current': current,
        'can_review': current and not decision and sub.version.uploaded_by_id != user.id and sub.submitted_by_id != user.id
            and sub.mapping.item.requirement.area.cycle.status == 'active'
            and areas_for(user, REVIEW_ROLES).filter(pk=sub.mapping.item.requirement.area_id).exists(),
        'decision': {'outcome': decision.outcome, 'comment': decision.comment,
                     'reviewer': decision.reviewer.get_full_name() or decision.reviewer.username,
                     'created_at': decision.created_at} if decision else None}


def mapping_data(mapping, user):
    return {'id': mapping.id, 'document': str(mapping.document_id), 'document_title': mapping.document.title,
            'item': mapping.item_id, 'submissions': [submission_data(s, user) for s in mapping.submissions.all()]}


def version_data(version):
    return {'id': version.id, 'number': version.number, 'original_name': version.original_name,
            'content_type': version.content_type, 'size': version.size, 'checksum': version.checksum,
            'uploaded_by': version.uploaded_by.get_full_name() or version.uploaded_by.username,
            'uploaded_at': version.uploaded_at, 'valid_until': version.valid_until,
            'download_url': f'/api/document-versions/{version.id}/download/'}


def doc_data(doc, user):
    versions = [version_data(v) for v in doc.versions.all() if can_version(user, v)]
    mappings = doc.mappings.filter(item__requirement__area__in=areas_for(user))
    return {'id': str(doc.id), 'title': doc.title, 'category': doc.category, 'area': doc.area_id,
        'area_title': doc.area.title, 'cycle': doc.area.cycle_id, 'versions': versions,
        'custodian': doc.custodian.get_full_name() or doc.custodian.username,
        'can_upload': doc.area.cycle.status == 'active' and areas_for(user, WRITE_ROLES).filter(pk=doc.area_id).exists(),
        'mappings': [mapping_data(m, user) for m in mappings]}


class CyclesView(APIView):
    def get(self, request):
        return Response(list(Cycle.objects.filter(areas__in=areas_for(request.user)).distinct().order_by('-id').values()))


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
        before = {k: str(getattr(req, k)) for k in serializer.validated_data}
        serializer.save()
        audit(request.user, req.area, 'requirement_updated', req.title, before=before,
              after={k: str(getattr(req, k)) for k in serializer.validated_data})
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
            qs = qs.filter(Q(area__cycle_id=cycle_id) | Q(mappings__item__requirement__area__cycle_id=cycle_id,
                mappings__item__requirement__area__in=areas_for(request.user))).distinct()
        q = request.query_params.get('search', '')
        # Search only source metadata and mappings visible to the requester.
        qs = qs.filter(Q(title__icontains=q) | Q(category__icontains=q) | Q(custodian__first_name__icontains=q) |
                       Q(custodian__last_name__icontains=q) | Q(mappings__item__requirement__title__icontains=q,
                       mappings__item__requirement__area__in=areas_for(request.user))).distinct()
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
                doc = get_object_or_404(documents_for(request.user), pk=document_id)
                require_area(request.user, doc.area, WRITE_ROLES)
                lock_active_cycles(doc.area.cycle_id)
                doc = Document.objects.select_for_update().get(pk=doc.pk)
            else:
                if not data.get('title') or not data.get('area'):
                    raise ValidationError('A document title and owning area are required.')
                area = get_object_or_404(areas_for(request.user, WRITE_ROLES), pk=data['area'])
                lock_active_cycles(area.cycle_id)
                doc = Document.objects.create(title=data['title'], category=data['category'], area=area, custodian=request.user)
            last = doc.versions.order_by('-number').first()
            version = DocumentVersion.objects.create(document=doc, number=last.number + 1 if last else 1,
                original_name=name, content_type=content_type, size=len(contents), checksum=checksum,
                uploaded_by=request.user, valid_until=data.get('valid_until'))
            settings.PRIVATE_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
            storage_path = settings.PRIVATE_MEDIA_ROOT / str(version.storage_key)
            with storage_path.open('xb') as output:
                output.write(contents)
            audit(request.user, doc.area, 'version_uploaded', doc.title, version=version.id, number=version.number)
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


class MappingsView(APIView):
    def get(self, request):
        qs = EvidenceMapping.objects.filter(item__requirement__area__in=areas_for(request.user))
        return Response([mapping_data(m, request.user) for m in qs])

    @transaction.atomic
    def post(self, request):
        data = payload(MappingInput, request).validated_data
        item = get_object_or_404(EvidenceItem.objects.filter(requirement__area__in=areas_for(request.user, WRITE_ROLES)), pk=data['item'])
        doc = get_object_or_404(documents_for(request.user), pk=data['document'])
        require_area(request.user, doc.area, WRITE_ROLES)
        lock_active_cycles(item.requirement.area.cycle_id)
        mapping, created = EvidenceMapping.objects.get_or_create(item=item, document=doc, defaults={'created_by': request.user})
        if created:
            audit(request.user, item.requirement.area, 'evidence_mapped', doc.title, mapping=mapping.id, item=item.id)
        return Response(mapping_data(mapping, request.user), status=201 if created else 200)


class SubmissionsView(APIView):
    def get(self, request):
        qs = Submission.objects.filter(mapping__item__requirement__area__in=areas_for(request.user)).select_related(
            'mapping__item__requirement__area__cycle', 'mapping__document', 'version', 'submitted_by', 'decision__reviewer')
        if query_id(request, 'cycle'):
            qs = qs.filter(mapping__item__requirement__area__cycle_id=request.query_params['cycle'])
        return Response([submission_data(s, request.user) for s in qs])

    @transaction.atomic
    def post(self, request):
        data = payload(SubmitInput, request).validated_data
        mapping = get_object_or_404(EvidenceMapping.objects.filter(item__requirement__area__in=areas_for(request.user, WRITE_ROLES)), pk=data['mapping'])
        require_area(request.user, mapping.document.area, WRITE_ROLES)
        lock_active_cycles(mapping.item.requirement.area.cycle_id)
        mapping = EvidenceMapping.objects.select_for_update().get(pk=mapping.pk)
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
        sub = Submission.objects.create(mapping=mapping, version=version, submitted_by=request.user)
        audit(request.user, mapping.item.requirement.area, 'evidence_submitted', mapping.document.title, submission=sub.id, version=version.id)
        return Response(submission_data(sub, request.user), status=201)


class ReviewsView(APIView):
    def get(self, request):
        qs = ReviewDecision.objects.filter(submission__mapping__item__requirement__area__in=areas_for(request.user))
        return Response(list(qs.values('id', 'submission_id', 'outcome', 'comment', 'created_at')))

    @transaction.atomic
    def post(self, request):
        data = payload(ReviewInput, request).validated_data
        sub = get_object_or_404(Submission.objects.filter(mapping__item__requirement__area__in=areas_for(request.user, REVIEW_ROLES)), pk=data['submission'])
        area = sub.mapping.item.requirement.area
        lock_active_cycles(area.cycle_id)
        EvidenceMapping.objects.select_for_update().get(pk=sub.mapping_id)
        sub = Submission.objects.select_for_update().select_related('version').get(pk=sub.pk)
        if sub.version.uploaded_by_id == request.user.id or sub.submitted_by_id == request.user.id:
            raise PermissionDenied('You cannot review your own upload or submission.')
        if sub.mapping.submissions.first().id != sub.id or ReviewDecision.objects.filter(submission=sub).exists():
            raise ValidationError('This submission has already been reviewed or superseded. Refresh the page.')
        if data['outcome'] == 'approved' and sub.version.valid_until and sub.version.valid_until < timezone.localdate():
            raise ValidationError('Expired evidence cannot be approved.')
        ReviewDecision.objects.create(submission=sub, reviewer=request.user, outcome=data['outcome'], comment=data['comment'])
        audit(request.user, area, data['outcome'], sub.mapping.document.title, submission=sub.id, version=sub.version_id, comment=data['comment'])
        return Response(submission_data(Submission.objects.get(pk=sub.pk), request.user), status=201)


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
            action = 'requirement_completed'
        else:
            if result['status'] != 'complete' or not latest or latest.outcome != 'complete':
                raise ValidationError('Only a completed requirement can be reopened.')
            action = 'requirement_reopened'
        certification = RequirementCertification.objects.create(
            requirement=requirement, coordinator=request.user, outcome=data['outcome'], rationale=data['rationale'])
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


class AuditView(APIView):
    def get(self, request):
        qs = AuditEvent.objects.filter(area__in=areas_for(request.user, ['coordinator', 'viewer'])).select_related('actor')
        if query_id(request, 'cycle'):
            qs = qs.filter(area__cycle_id=request.query_params['cycle'])
        return Response([{'id': e.id, 'actor': e.actor.get_full_name() or e.actor.username if e.actor else 'System',
            'action': e.action, 'record': e.record, 'detail': e.detail, 'created_at': e.created_at} for e in qs[:200]])
