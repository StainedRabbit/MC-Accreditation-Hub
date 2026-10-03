from django.utils import timezone
from zoneinfo import ZoneInfo

MANILA = ZoneInfo('Asia/Manila')
from .scanning import scan_status


def submission_criteria_current(submission):
    revision = submission.mapping.item.requirement.criteria_revision
    return submission.criteria_revision == revision or (submission.criteria_revision is None and revision == 1)


def submission_state(submission):
    if not submission:
        return 'missing'
    if scan_status(submission.version) != 'clean':
        return 'quarantined'
    if not submission_criteria_current(submission):
        return 'outdated'
    decision = getattr(submission, 'decision', None)
    if not decision:
        return 'pending'
    cycle = submission.mapping.item.requirement.area.cycle
    as_of = timezone.localtime(cycle.closed_at).date() if cycle.status == 'closed' and cycle.closed_at else timezone.localdate()
    if decision.outcome == 'approved' and submission.version.valid_until and submission.version.valid_until < as_of:
        return 'expired'
    return decision.outcome


def item_state(item):
    states = [submission_state(next(iter(mapping.submissions.all()), None)) for mapping in item.mappings.all()]
    for state in ['approved', 'revision_requested', 'rejected', 'expired', 'outdated', 'quarantined', 'pending']:
        if state in states:
            return state
    return 'missing'


def certification_has_support(certification):
    if not (certification and certification.outcome == 'complete' and
            certification.criteria_snapshot is not None and
            (certification.evidence.exists() or certification.packages.exists())):
        return False
    return (all(scan_status(entry.submission.version) == 'clean' for entry in certification.evidence.all()) and
            all(scan_status(item.version) == 'clean' for entry in certification.packages.all()
                for item in entry.package.items.all()))


def package_is_ready(package, requirement):
    if package.status != 'approved' or package.criteria_revision != requirement.criteria_revision:
        return False
    items = list(package.items.all())
    required = {item.id for item in requirement.items.all() if item.mandatory}
    if not required.issubset({entry.mapping.item_id for entry in items}):
        return False
    as_of = timezone.localtime(requirement.area.cycle.closed_at).date() if requirement.area.cycle.status == 'closed' and requirement.area.cycle.closed_at else timezone.localdate()
    return all(scan_status(entry.version) == 'clean' and
               (not entry.version.valid_until or entry.version.valid_until >= as_of) for entry in items)


def requirement_overdue(requirement, status):
    """Deadline monitoring is independent of readiness status."""
    cycle = requirement.area.cycle
    if (not requirement.active or not requirement.applicable or not requirement.deadline or
            status == 'complete' or cycle.status not in ('active', 'closed')):
        return False
    if cycle.status == 'closed':
        if not cycle.closed_at:
            return False
        as_of = timezone.localtime(cycle.closed_at, MANILA).date()
    else:
        as_of = timezone.localdate(timezone=MANILA)
    return requirement.deadline < as_of


def requirement_result(requirement):
    items = list(requirement.items.all())
    required = [i for i in items if i.mandatory]
    states = [item_state(i) for i in required]
    approved = states.count('approved')
    latest_certification = next(iter(requirement.certifications.all()), None)
    evidence_ready = bool(required) and approved == len(required)
    packages = list(requirement.packages.all())
    latest_nonwithdrawn = next((package for package in packages if package.status != 'withdrawn'), None)
    package_ready = any(package_is_ready(package, requirement) for package in packages)
    if package_ready:
        approved = len(required)
    if not requirement.active:
        status = 'draft'
    elif not requirement.applicable:
        status = 'excluded'
    elif certification_has_support(latest_certification):
        status = 'complete'
    elif any(package.status == 'submitted' for package in packages) or (not packages and 'pending' in states):
        status = 'for_verification'
    elif latest_nonwithdrawn and latest_nonwithdrawn.status == 'revisions_requested':
        status = 'needs_revision'
    elif not packages and any(state in ('revision_requested', 'rejected', 'outdated', 'expired') for state in states):
        status = 'needs_revision'
    elif package_ready or (not packages and evidence_ready):
        status = 'ready_for_completion_review'
    elif any(package.status == 'draft' for package in packages) or (not packages and any(item.mappings.all() for item in items)) or (latest_certification and latest_certification.outcome == 'reopened'):
        status = 'in_progress'
    else:
        status = 'missing'
    return {'status': status, 'overdue': requirement_overdue(requirement, status),
            'approved_items': approved, 'required_items': len(required),
            'ready_for_completion_review': status == 'ready_for_completion_review',
            'legacy_certification': bool(latest_certification and latest_certification.outcome == 'complete' and not certification_has_support(latest_certification)),
            'latest_certification': latest_certification}


def summary(requirements):
    requirements = list(requirements)
    results = [requirement_result(r) for r in requirements if r.active and r.applicable]
    total = len(results)
    counts = {s: sum(r['status'] == s for r in results) for s in ['complete', 'for_verification', 'needs_revision', 'ready_for_completion_review', 'in_progress', 'missing']}
    return {**counts, 'total': total, 'overdue_count': sum(r['overdue'] for r in results), 'percentage': round(100 * counts['complete'] / total, 2) if total else None,
            'excluded': sum(r.active and not r.applicable for r in requirements),
            'formula': '100 × complete applicable requirements / total applicable requirements', 'formula_version': 3}


def with_evidence(queryset):
    return queryset.select_related('area', 'area__cycle').prefetch_related(
        'items__mappings__submissions__version', 'items__mappings__submissions__decision',
        'certifications__coordinator', 'certifications__evidence__submission',
        'certifications__packages__package', 'applicability_decisions__coordinator',
        'packages__owner', 'packages__decision__reviewer',
        'packages__items__mapping__item', 'packages__items__mapping__document', 'packages__items__version')
