"""One authoritative evidence visibility policy for the scoped API.

Role grants are additive: a person with several grants receives the union of
their permitted records. This module deliberately has no Administrator bypass;
academic/evidence access still requires an explicit academic grant.
"""

from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Area, Cycle, Document, DocumentVersion, EvidenceMapping, Submission, Requirement, RequirementAssignment, PackageAttempt


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


def is_active_assignee(user, requirement):
    return user.is_active and RequirementAssignment.objects.filter(
        requirement=requirement, user=user, active=True,
    ).exists()


def is_scoped_coordinator(user, area):
    return areas_for(user, ['coordinator']).filter(pk=area.pk).exists()


def require_assignee_or_coordinator_override(user, requirement, override_reason, operation):
    """Return True for an explicit Coordinator exception, otherwise require an assignee."""
    require_unarchived_requirement(requirement)
    if is_active_assignee(user, requirement):
        return False
    if is_scoped_coordinator(user, requirement.area):
        if not (override_reason or '').strip():
            raise ValidationError({'override_reason': f'A reason is required for a Coordinator {operation} override.'})
        return True
    raise PermissionDenied('Only an active assignee may work on this requirement.')


def require_document_steward_or_coordinator_override(user, document, override_reason, operation):
    if document.steward_id == user.id:
        return False
    if document.steward_id is None:
        raise ValidationError('This legacy document has no steward. A scoped Coordinator must explicitly delegate stewardship first.')
    if is_scoped_coordinator(user, document.area):
        if not (override_reason or '').strip():
            raise ValidationError({'override_reason': f'A reason is required for a Coordinator {operation} override.'})
        return True
    raise PermissionDenied('Only the document steward may replace or submit this evidence.')


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
        Q(submissions__mapping__item__requirement__area__in=coordinator_areas) |
        Q(package_items__package__requirement__area__in=coordinator_areas)
    )
    reviewer_scope = (Q(submissions__mapping__item__requirement__area__in=reviewer_areas) |
                      Q(package_items__package__requirement__area__in=reviewer_areas,
                        package_items__package__status__in=['submitted', 'approved', 'revisions_requested', 'withdrawn']))
    custodian_own_source = Q(document__area__in=custodian_areas) & (
        Q(document__custodian=user) | Q(uploaded_by=user)
    )
    custodian_own_submission = Q(
        submissions__submitted_by=user,
        submissions__mapping__item__requirement__area__in=custodian_areas,
    ) | Q(package_items__package__owner=user,
          package_items__package__requirement__area__in=custodian_areas)
    custodian_approved_shared = Q(
        submissions__decision__outcome='approved',
        submissions__mapping__item__requirement__area__in=custodian_areas,
    ) | Q(package_items__package__status='approved',
          package_items__package__requirement__area__in=custodian_areas)
    viewer_approved = Q(
        submissions__decision__outcome='approved',
        submissions__mapping__item__requirement__area__in=viewer_areas,
    ) | Q(package_items__package__status='approved',
          package_items__package__requirement__area__in=viewer_areas)
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


def visible_packages_for(user, queryset=None):
    qs = queryset if queryset is not None else PackageAttempt.objects.all()
    if not user.assignments.filter(role__in=['coordinator', 'reviewer', 'custodian']).exists():
        return qs.none()
    return qs.filter(
        Q(requirement__area__in=areas_for(user, ['coordinator'])) |
        Q(requirement__area__in=areas_for(user, ['reviewer']),
          status__in=['submitted', 'approved', 'revisions_requested', 'withdrawn']) |
        Q(requirement__area__in=areas_for(user, ['custodian']), owner=user)
    ).distinct()


def lock_active_cycles(*cycle_ids):
    # All mutations acquire cycle locks in a stable order before record locks.
    cycles = list(Cycle.objects.select_for_update().filter(id__in=set(cycle_ids)).order_by('id'))
    if len(cycles) != len(set(cycle_ids)) or any(c.status != 'active' or c.archived_at for c in cycles):
        raise ValidationError('This cycle is not active. Closed and draft cycles are read-only.')


def require_unarchived_requirement(requirement):
    if not Requirement.objects.filter(pk=requirement.pk, archived_at__isnull=True, area__cycle__archived_at__isnull=True).exists():
        raise ValidationError('Archived records are read-only. Restore the record before changing it.')
