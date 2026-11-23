"""Transactional, scoped notifications for accreditation work."""
from django.db.models import Q
from .access import areas_for, visible_packages_for, visible_submissions_for
from .models import Notification, RequirementAssignment, User


def scoped_users(requirement, roles):
    return User.objects.filter(Q(assignments__area_id=requirement.area_id) | Q(assignments__area__isnull=True),
        is_active=True, assignments__role__in=roles,
        assignments__cycle_id=requirement.area.cycle_id).distinct()


def notify(requirement, users, actor, kind, event_key, package=None, submission=None):
    for user in users:
        if user.is_active and user.pk != actor.pk:
            Notification.objects.get_or_create(recipient=user, event_key=event_key, defaults={
                'requirement': requirement, 'kind': kind, 'package': package, 'submission': submission})


def notify_reviewers(requirement, actor, event_key, package=None, submission=None):
    excluded = {actor.pk}
    if package:
        excluded.add(package.owner_id)
        excluded.update(package.items.values_list('version__uploaded_by_id', flat=True))
    if submission:
        excluded.update([submission.submitted_by_id, submission.version.uploaded_by_id])
    users = scoped_users(requirement, ['coordinator', 'reviewer']).exclude(pk__in=excluded)
    notify(requirement, users, actor, 'review_requested', event_key, package, submission)


def visible_notifications(user):
    """Recheck current grants, assignment and record visibility on every request."""
    rows = list(Notification.objects.filter(recipient=user, requirement__area__in=areas_for(user)).select_related(
        'requirement__area__cycle'))
    result = []
    review_areas = set(areas_for(user, ['coordinator', 'reviewer']).values_list('id', flat=True))
    coordinator_areas = set(areas_for(user, ['coordinator']).values_list('id', flat=True))
    custodian_areas = set(areas_for(user, ['custodian']).values_list('id', flat=True))
    assignments = set(RequirementAssignment.objects.filter(user=user, active=True).values_list('requirement_id', flat=True))
    package_ids = {row.package_id for row in rows if row.package_id}
    submission_ids = {row.submission_id for row in rows if row.submission_id}
    visible_packages = set(visible_packages_for(user).filter(pk__in=package_ids).values_list('pk', flat=True))
    visible_submissions = set(visible_submissions_for(user).filter(pk__in=submission_ids).values_list('pk', flat=True))
    for row in rows:
        if row.kind == 'review_requested' and row.requirement.area_id not in review_areas:
            continue
        if row.kind == 'ready_for_completion' and row.requirement.area_id not in coordinator_areas:
            continue
        if row.kind in ('assigned', 'requirement_completed', 'requirement_reopened') and (
                row.requirement.area_id not in custodian_areas or row.requirement_id not in assignments):
            continue
        if row.package_id and row.package_id not in visible_packages:
            continue
        if row.submission_id and row.submission_id not in visible_submissions:
            continue
        result.append(row)
    return result
