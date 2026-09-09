from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import Area, Document, Cycle

READ_ROLES = ['coordinator', 'reviewer', 'custodian', 'viewer']
WRITE_ROLES = ['coordinator', 'custodian']
REVIEW_ROLES = ['coordinator', 'reviewer']


def areas_for(user, roles=None):
    assignments = user.assignments.filter(role__in=roles or READ_ROLES)
    return Area.objects.filter(Q(id__in=assignments.filter(area__isnull=False).values('area_id')) |
                               Q(cycle_id__in=assignments.filter(area__isnull=True).values('cycle_id'))).distinct()


def require_area(user, area, roles=None):
    if not areas_for(user, roles).filter(pk=area.pk).exists():
        raise PermissionDenied('You do not have permission in this accreditation area.')


def documents_for(user):
    # A shared mapping grants access only to versions explicitly submitted there,
    # never to every draft or future version of the source document.
    return Document.objects.filter(Q(area__in=areas_for(user)) |
        Q(mappings__item__requirement__area__in=areas_for(user), mappings__submissions__isnull=False)).distinct()


def can_version(user, version):
    return areas_for(user).filter(pk=version.document.area_id).exists() or version.submissions.filter(
        mapping__item__requirement__area__in=areas_for(user)).exists()


def lock_active_cycles(*cycle_ids):
    # All mutations acquire cycle locks in a stable order before record locks.
    cycles = list(Cycle.objects.select_for_update().filter(id__in=set(cycle_ids)).order_by('id'))
    if len(cycles) != len(set(cycle_ids)) or any(c.status != 'active' for c in cycles):
        raise ValidationError('This cycle is not active. Closed and draft cycles are read-only.')
