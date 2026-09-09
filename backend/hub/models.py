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


class Cycle(models.Model):
    title = models.CharField(max_length=180)
    program = models.CharField(max_length=180, default='Graduate School')
    instrument = models.CharField(max_length=180, default='Sample instrument — not official PACUCOA criteria')
    status = models.CharField(max_length=10, choices=[('draft', 'Draft'), ('active', 'Active'), ('closed', 'Closed')], default='draft')
    is_demo = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
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
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code', 'id']
        constraints = [models.UniqueConstraint(fields=['area', 'code'], name='requirement_code_area'),
                       models.CheckConstraint(condition=models.Q(applicable=True) | ~models.Q(exclusion_reason=''), name='exclusion_reason_required')]


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
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    size = models.PositiveIntegerField()
    checksum = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-number']
        constraints = [models.UniqueConstraint(fields=['document', 'number'], name='document_version_number')]


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


class RequirementCertification(ImmutableRecord):
    """Append-only coordinator decisions that determine requirement completion."""
    requirement = models.ForeignKey(Requirement, on_delete=models.PROTECT, related_name='certifications')
    coordinator = models.ForeignKey(User, on_delete=models.PROTECT)
    outcome = models.CharField(max_length=10, choices=[('complete', 'Complete'), ('reopened', 'Reopened')])
    rationale = models.TextField()
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
