"""One authoritative evidence visibility policy for the scoped API.

Role grants are additive: a person with several grants receives the union of
their permitted records. This module deliberately has no Administrator bypass;
academic/evidence access still requires an explicit academic grant.
"""

from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Area, Cycle, Document, DocumentVersion, EvidenceMapping, Submission


READ_ROLES = ['coordinator', 'reviewer', 'custodian', 'viewer']
WRITE_ROLES = ['coordinator', 'custodian']
REVIEW_ROLES = ['coordinator', 'reviewer']


def areas_for(user, roles=None):
    assignments = user.assignments.filter(role__in=roles or READ_ROLES)
    return Area.objects.filter(
        Q(id__in=assignments.filter(area__isnull=False).values('area_id')) |
        Q(cycle_id__in=assignments.filter(area__isnull=True).values('cycle_id'))
    ).distinct()


def has_cyclewide_coordinator(user, cycle):
    """Only an explicit area-less Coordinator grant controls a whole cycle."""
    return user.assignments.filter(role='coordinator', cycle=cycle, area__isnull=True).exists()


def require_area(user, area, roles=None):
    if not areas_for(user, roles).filter(pk=area.pk).exists():
        raise PermissionDenied('You do not have permission in this accreditation area.')


def visible_versions_for(user, queryset=None):
    """Return the exact document versions a requester may see or download.

    Matrix, within an explicit role grant's area/cycle scope:
    * Coordinators: all versions and submission history in scope.
    * Reviewers: versions that have been submitted in scope and their history.
    * Custodians (the current Contributor implementation): their document/
      uploaded/submitted work, plus approved shared evidence. Approved shared
      evidence grants file/version access, not another person's review history.
    * Viewers: approved evidence only, without submission/review history.

    Existing legacy cross-area/cross-cycle mappings are never changed. Their
    already submitted/approved versions remain visible through the recipient
    area's matching rule above; new mappings and submissions are blocked in
    the views layer.
    """
    qs = queryset if queryset is not None else DocumentVersion.objects.all()
    coordinator_areas = areas_for(user, ['coordinator'])
    reviewer_areas = areas_for(user, ['reviewer'])
    custodian_areas = areas_for(user, ['custodian'])
    viewer_areas = areas_for(user, ['viewer'])

    coordinator_scope = (
        Q(document__area__in=coordinator_areas) |
        Q(submissions__mapping__item__requirement__area__in=coordinator_areas)
    )
    reviewer_scope = Q(submissions__mapping__item__requirement__area__in=reviewer_areas)
    custodian_own_source = Q(document__area__in=custodian_areas) & (
        Q(document__custodian=user) | Q(uploaded_by=user)
    )
    custodian_own_submission = Q(
        submissions__submitted_by=user,
        submissions__mapping__item__requirement__area__in=custodian_areas,
    )
    custodian_approved_shared = Q(
        submissions__decision__outcome='approved',
        submissions__mapping__item__requirement__area__in=custodian_areas,
    )
    viewer_approved = Q(
        submissions__decision__outcome='approved',
        submissions__mapping__item__requirement__area__in=viewer_areas,
    )
    return qs.filter(
        coordinator_scope | reviewer_scope | custodian_own_source |
        custodian_own_submission | custodian_approved_shared | viewer_approved
    ).distinct()


def documents_for(user):
    return Document.objects.filter(versions__in=visible_versions_for(user)).distinct()


def can_version(user, version):
    return visible_versions_for(user).filter(pk=version.pk).exists()


def visible_submissions_for(user, queryset=None):
    """Return submission/review history, which is narrower than file access."""
    qs = queryset if queryset is not None else Submission.objects.all()
    if not user.assignments.filter(role__in=['coordinator', 'reviewer', 'custodian']).exists():
        return qs.none()
    coordinator_areas = areas_for(user, ['coordinator'])
    reviewer_areas = areas_for(user, ['reviewer'])
    custodian_areas = areas_for(user, ['custodian'])
    return qs.filter(
        Q(mapping__item__requirement__area__in=coordinator_areas) |
        Q(mapping__item__requirement__area__in=reviewer_areas) |
        (Q(mapping__document__area__in=custodian_areas) &
         (Q(mapping__document__custodian=user) | Q(submitted_by=user)))
    ).filter(version__in=visible_versions_for(user)).distinct()


def visible_mappings_for(user, queryset=None):
    """Mappings accompany coordinators/reviewers and a custodian's own work."""
    qs = queryset if queryset is not None else EvidenceMapping.objects.all()
    if not user.assignments.filter(role__in=['coordinator', 'reviewer', 'custodian']).exists():
        return qs.none()
    coordinator_areas = areas_for(user, ['coordinator'])
    reviewer_areas = areas_for(user, ['reviewer'])
    custodian_areas = areas_for(user, ['custodian'])
    return qs.filter(
        Q(item__requirement__area__in=coordinator_areas) |
        (Q(item__requirement__area__in=reviewer_areas) & Q(submissions__isnull=False)) |
        (Q(document__area__in=custodian_areas) &
         (Q(document__custodian=user) | Q(created_by=user) | Q(submissions__submitted_by=user)))
    ).distinct()


def lock_active_cycles(*cycle_ids):
    # All mutations acquire cycle locks in a stable order before record locks.
    cycles = list(Cycle.objects.select_for_update().filter(id__in=set(cycle_ids)).order_by('id'))
    if len(cycles) != len(set(cycle_ids)) or any(c.status != 'active' for c in cycles):
        raise ValidationError('This cycle is not active. Closed and draft cycles are read-only.')
