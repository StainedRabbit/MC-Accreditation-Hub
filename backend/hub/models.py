import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=160, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(Lower('email'), name='user_email_ci')]


class AuthRateBucket(models.Model):
    """PostgreSQL-backed test throttling shared by every application worker."""
    key = models.CharField(max_length=64, unique=True)
    window_start = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)


class Cycle(models.Model):
    title = models.CharField(max_length=180)
    program = models.CharField(max_length=180, default='Graduate School')
    instrument = models.CharField(max_length=180, default='Sample instrument — not official PACUCOA criteria')
    status = models.CharField(max_length=10, choices=[('draft', 'Draft'), ('active', 'Active'), ('closed', 'Closed')], default='draft')
    is_demo = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name="archived_cycles")
    archive_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Area(models.Model):
    cycle = models.ForeignKey(Cycle, on_delete=models.PROTECT, related_name='areas')
    code = models.CharField(max_length=20)
    title = models.CharField(max_length=180)
    icon = models.CharField(max_length=10, default='📁')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        constraints = [models.UniqueConstraint(fields=['cycle', 'code'], name='area_code_cycle')]

    def __str__(self):
        return f'{self.cycle}: {self.title}'


class RoleAssignment(models.Model):
    ROLES = [('administrator', 'Administrator'), ('coordinator', 'Coordinator'), ('reviewer', 'Reviewer'), ('custodian', 'Custodian'), ('viewer', 'Viewer')]
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='assignments')
    cycle = models.ForeignKey(Cycle, on_delete=models.PROTECT)
    area = models.ForeignKey(Area, null=True, blank=True, on_delete=models.PROTECT)
    role = models.CharField(max_length=20, choices=ROLES)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'cycle', 'area', 'role'], name='unique_assignment', nulls_distinct=False),
                       models.CheckConstraint(condition=~models.Q(role__in=['custodian', 'reviewer']) | models.Q(area__isnull=False), name='area_required_for_staff')]

    def clean(self):
        if self.area_id and self.area.cycle_id != self.cycle_id:
            raise ValidationError('Area must belong to the selected cycle.')
        if self.role in ('custodian', 'reviewer') and not self.area_id:
            raise ValidationError('Custodians and reviewers need an area assignment.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Requirement(models.Model):
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name='requirements')
    code = models.CharField(max_length=40)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    responsible = models.CharField(max_length=180)
    deadline = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=False)
    applicable = models.BooleanField(default=True)
    exclusion_reason = models.TextField(blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name="archived_requirements")
    archive_reason = models.TextField(blank=True)
    criteria_revision = models.PositiveIntegerField(default=1)
    # Pre-F07 requirements retain their item-level write path until their first
    # package draft. New requirements use packages from the start.
    legacy_submission_mode = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code', 'id']
        constraints = [models.UniqueConstraint(fields=['area', 'code'], name='requirement_code_area'),
                       models.CheckConstraint(condition=models.Q(applicable=True) | ~models.Q(exclusion_reason=''), name='exclusion_reason_required')]


class RequirementAssignment(models.Model):
    """The active people accountable for new evidence on a requirement.

    Deactivation preserves the original assignment rather than rewriting
    assignment history.  AuditEvent records the reason for every transition.
    """
    requirement = models.ForeignKey(Requirement, on_delete=models.PROTECT, related_name='user_assignments')
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='requirement_assignments')
    active = models.BooleanField(default=True)
    assigned_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='assignments_made')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['requirement', 'user'], name='unique_requirement_user_assignment')]

    def clean(self):
        if not self.user.is_active:
            raise ValidationError('Requirement assignees must have an active account.')
        has_scope = RoleAssignment.objects.filter(
            user=self.user, role='custodian', cycle=self.requirement.area.cycle,
            area=self.requirement.area,
        ).exists()
        if not has_scope:
            raise ValidationError('Requirement assignees need an active Custodian grant in this area and cycle.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class EvidenceItem(models.Model):
    requirement = models.ForeignKey(Requirement, on_delete=models.PROTECT, related_name='items')
    label = models.CharField(max_length=180)
    criteria = models.TextField(blank=True)
    mandatory = models.BooleanField(default=True)


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name='documents')
    title = models.CharField(max_length=180)
    category = models.CharField(max_length=100, default='Supporting Document')
    custodian = models.ForeignKey(User, on_delete=models.PROTECT)
    # Nullable only for pre-F04 records.  The migration deliberately does not
    # infer stewardship from the older custodian field.
    steward = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT,
                                related_name='stewarded_documents')
    created_at = models.DateTimeField(auto_now_add=True)


class ImmutableRecord(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('Historical records cannot be overwritten.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Historical records cannot be deleted.')


class DocumentVersion(ImmutableRecord):
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name='versions')
    number = models.PositiveIntegerField()
    storage_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    idempotency_key = models.UUIDField(null=True, blank=True)
    idempotency_fingerprint = models.CharField(max_length=64, blank=True, default='')
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    size = models.PositiveIntegerField()
    checksum = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-number']
        constraints = [
            models.UniqueConstraint(fields=['document', 'number'], name='document_version_number'),
            models.UniqueConstraint(fields=['uploaded_by', 'idempotency_key'], name='version_upload_idempotency_user'),
        ]


class DocumentScan(ImmutableRecord):
    """Append-only scanner verdict for exact stored bytes; the latest verdict governs release."""
    version = models.ForeignKey(DocumentVersion, on_delete=models.PROTECT, related_name='scans')
    result = models.CharField(max_length=12, choices=[('clean', 'Clean'), ('infected', 'Infected'), ('error', 'Error')])
    checksum = models.CharField(max_length=64)
    scanner_id = models.CharField(max_length=120)
    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']


class EvidenceMapping(models.Model):
    item = models.ForeignKey(EvidenceItem, on_delete=models.PROTECT, related_name='mappings')
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name='mappings')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['item', 'document'], name='item_document_mapping')]


class Submission(ImmutableRecord):
    mapping = models.ForeignKey(EvidenceMapping, on_delete=models.PROTECT, related_name='submissions')
    version = models.ForeignKey(DocumentVersion, on_delete=models.PROTECT, related_name='submissions')
    submitted_by = models.ForeignKey(User, on_delete=models.PROTECT)
    submitted_at = models.DateTimeField(auto_now_add=True)
    # Null is honest for submissions created before criteria revision tracking.
    criteria_revision = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-id']
        constraints = [models.UniqueConstraint(fields=['mapping', 'version'], name='version_submitted_once_per_mapping')]


class ReviewDecision(ImmutableRecord):
    submission = models.OneToOneField(Submission, on_delete=models.PROTECT, related_name='decision')
    reviewer = models.ForeignKey(User, on_delete=models.PROTECT)
    outcome = models.CharField(max_length=25, choices=[('approved', 'Approved'), ('revision_requested', 'Revision requested'), ('rejected', 'Rejected')])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(outcome='approved') | ~models.Q(comment=''), name='review_reason_required')]


class PackageAttempt(models.Model):
    STATES = [('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'),
              ('revisions_requested', 'Revisions requested'), ('withdrawn', 'Withdrawn')]
    requirement = models.ForeignKey(Requirement, on_delete=models.PROTECT, related_name='packages')
    number = models.PositiveIntegerField()
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='package_attempts')
    source_attempt = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT)
    status = models.CharField(max_length=22, choices=STATES, default='draft')
    notes = models.TextField(blank=True)
    criteria_revision = models.PositiveIntegerField(null=True, blank=True)
    criteria_snapshot = models.JSONField(null=True, blank=True)
    withdrawal_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-number']
        constraints = [
            models.UniqueConstraint(fields=['requirement', 'number'], name='package_attempt_number'),
            models.UniqueConstraint(fields=['requirement'], condition=models.Q(status='submitted'), name='one_submitted_package_per_requirement'),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            before = type(self).objects.get(pk=self.pk)
            if before.status in ('approved', 'revisions_requested', 'withdrawn'):
                raise ValidationError('Terminal package attempts cannot be changed.')
            if before.status == 'submitted' and (self.status not in ('approved', 'revisions_requested', 'withdrawn') or
                    any(getattr(self, field) != getattr(before, field) for field in
                        ('requirement_id', 'number', 'owner_id', 'source_attempt_id', 'notes',
                         'criteria_revision', 'criteria_snapshot', 'created_at', 'submitted_at'))):
                raise ValidationError('Submitted package contents cannot be changed.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status != 'draft':
            raise ValidationError('Submitted and terminal package attempts cannot be deleted.')
        super().delete(*args, **kwargs)


class PackageItem(models.Model):
    package = models.ForeignKey(PackageAttempt, on_delete=models.PROTECT, related_name='items')
    mapping = models.ForeignKey(EvidenceMapping, on_delete=models.PROTECT)
    version = models.ForeignKey(DocumentVersion, on_delete=models.PROTECT, related_name='package_items')
    note = models.TextField(blank=True)
    snapshot = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['package', 'mapping'], name='package_mapping_once'),
                       models.UniqueConstraint(fields=['package', 'version'], name='package_version_once')]

    def save(self, *args, **kwargs):
        if self.package.status != 'draft':
            raise ValidationError('Submitted package items cannot be changed.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.package.status != 'draft':
            raise ValidationError('Submitted package items cannot be deleted.')
        super().delete(*args, **kwargs)


class PackageDecision(ImmutableRecord):
    package = models.OneToOneField(PackageAttempt, on_delete=models.PROTECT, related_name='decision')
    reviewer = models.ForeignKey(User, on_delete=models.PROTECT)
    outcome = models.CharField(max_length=22, choices=[('approved', 'Approved'), ('revisions_requested', 'Revisions requested')])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class RequirementCertification(ImmutableRecord):
    """Append-only coordinator decisions that determine requirement completion."""
    requirement = models.ForeignKey(Requirement, on_delete=models.PROTECT, related_name='certifications')
    coordinator = models.ForeignKey(User, on_delete=models.PROTECT)
    outcome = models.CharField(max_length=10, choices=[('complete', 'Complete'), ('reopened', 'Reopened')])
    rationale = models.TextField()
    # Null identifies pre-F05 completions. No historical evidence is inferred.
    criteria_snapshot = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']


class CertificationEvidence(ImmutableRecord):
    certification = models.ForeignKey(RequirementCertification, on_delete=models.PROTECT, related_name='evidence')
    submission = models.ForeignKey(Submission, on_delete=models.PROTECT)
    # Preserve displayed details even if editable document metadata changes.
    snapshot = models.JSONField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['certification', 'submission'], name='unique_certification_submission')]


class CertificationPackage(ImmutableRecord):
    certification = models.ForeignKey(RequirementCertification, on_delete=models.PROTECT, related_name='packages')
    package = models.ForeignKey(PackageAttempt, on_delete=models.PROTECT)
    snapshot = models.JSONField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['certification', 'package'], name='unique_certification_package')]


class ApplicabilityDecision(ImmutableRecord):
    requirement = models.ForeignKey(Requirement, on_delete=models.PROTECT, related_name='applicability_decisions')
    coordinator = models.ForeignKey(User, on_delete=models.PROTECT)
    applicable = models.BooleanField()
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']


class AuditEvent(ImmutableRecord):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    area = models.ForeignKey(Area, null=True, on_delete=models.PROTECT)
    action = models.CharField(max_length=60)
    record = models.CharField(max_length=200)
    detail = models.JSONField(default=dict)
    request_id = models.UUIDField(default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
        permissions = [('view_security_audit', 'Can view institution security audit events')]
