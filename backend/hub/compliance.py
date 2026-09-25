from django.utils import timezone


def submission_criteria_current(submission):
    revision = submission.mapping.item.requirement.criteria_revision
    return submission.criteria_revision == revision or (submission.criteria_revision is None and revision == 1)


def submission_state(submission):
    if not submission:
        return 'missing'
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
    for state in ['approved', 'revision_requested', 'rejected', 'expired', 'outdated', 'pending']:
        if state in states:
            return state
    return 'missing'


def certification_has_support(certification):
    return bool(certification and certification.outcome == 'complete' and
                certification.criteria_snapshot is not None and certification.evidence.exists())


def requirement_result(requirement):
    items = list(requirement.items.all())
    required = [i for i in items if i.mandatory]
    states = [item_state(i) for i in required]
    approved = states.count('approved')
    latest_certification = next(iter(requirement.certifications.all()), None)
    evidence_ready = bool(required) and approved == len(required)
    if not requirement.active:
        status = 'draft'
    elif not requirement.applicable:
        status = 'excluded'
    elif certification_has_support(latest_certification):
        status = 'complete'
    elif evidence_ready:
        status = 'ready_for_completion_review'
    elif states and all(s == 'missing' for s in states):
        status = 'missing'
    elif any(s in ['revision_requested', 'rejected', 'expired', 'outdated', 'missing'] for s in states):
        status = 'for_compliance'
    else:
        status = 'pending'
    return {'status': status, 'approved_items': approved, 'required_items': len(required),
            'ready_for_completion_review': evidence_ready and status != 'complete',
            'legacy_certification': bool(latest_certification and latest_certification.outcome == 'complete' and not certification_has_support(latest_certification)),
            'latest_certification': latest_certification}


def summary(requirements):
    requirements = list(requirements)
    results = [requirement_result(r) for r in requirements if r.active and r.applicable]
    total = len(results)
    counts = {s: sum(r['status'] == s for r in results) for s in ['complete', 'ready_for_completion_review', 'pending', 'for_compliance', 'missing']}
    return {**counts, 'total': total, 'percentage': round(100 * counts['complete'] / total, 2) if total else None,
            'excluded': sum(r.active and not r.applicable for r in requirements),
            'formula': '100 × complete applicable requirements / total applicable requirements', 'formula_version': 2}


def with_evidence(queryset):
    return queryset.select_related('area', 'area__cycle').prefetch_related(
        'items__mappings__submissions__version', 'items__mappings__submissions__decision',
        'certifications__coordinator', 'certifications__evidence__submission',
        'applicability_decisions__coordinator')
