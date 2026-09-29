from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Requirement, EvidenceItem, Area


class AreaInput(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ['cycle', 'code', 'title', 'icon', 'order']
        extra_kwargs = {'cycle': {'required': False}}

    def validate_code(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Enter an area code.')
        return value

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Enter an area title.')
        return value

    def validate_icon(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Enter an area icon.')
        return value

    def validate(self, attrs):
        instance = self.instance
        cycle = attrs.get('cycle', instance.cycle if instance else None)
        if instance and cycle.pk != instance.cycle_id:
            raise serializers.ValidationError({'cycle': 'An area cannot move to another cycle.'})
        code = attrs.get('code', instance.code if instance else None)
        if cycle and Area.objects.filter(cycle=cycle, code=code).exclude(pk=instance.pk if instance else None).exists():
            raise serializers.ValidationError({'code': 'This area code is already used in the cycle.'})
        return attrs


class ItemInput(serializers.Serializer):
    label = serializers.CharField(max_length=180)
    criteria = serializers.CharField(required=False, allow_blank=True, default='', max_length=4000)
    mandatory = serializers.BooleanField(default=True)


class RequirementInput(serializers.ModelSerializer):
    items = ItemInput(many=True, required=False)
    description = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    exclusion_reason = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    applicability_reason = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=4000)
    change_reason = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=4000)

    class Meta:
        model = Requirement
        fields = ['area', 'code', 'title', 'description', 'responsible', 'deadline', 'active', 'applicable', 'exclusion_reason', 'items', 'applicability_reason', 'change_reason']
        validators = []

    def validate(self, attrs):
        if len(attrs.get('items', [])) > 50:
            raise serializers.ValidationError({'items': 'Use 50 evidence items or fewer.'})
        instance = self.instance
        applicable = attrs.get('applicable', instance.applicable if instance else True)
        reason = attrs.get('exclusion_reason', instance.exclusion_reason if instance else '')
        if not applicable and not reason.strip():
            raise serializers.ValidationError('An exclusion reason is required.')
        if instance and 'area' in attrs and attrs['area'].id != instance.area_id:
            raise serializers.ValidationError('A requirement cannot move to another area.')
        if instance and 'items' in attrs:
            raise serializers.ValidationError('Existing evidence criteria are preserved; create a new requirement for structural changes.')
        if instance and (attrs.get('applicable', instance.applicable) != instance.applicable or
                         attrs.get('exclusion_reason', instance.exclusion_reason) != instance.exclusion_reason) and not attrs.get('applicability_reason', '').strip():
            raise serializers.ValidationError({'applicability_reason': 'A reason is required for an applicability decision.'})
        if instance and 'description' in attrs and attrs['description'] != instance.description and not attrs.get('change_reason', '').strip():
            raise serializers.ValidationError({'change_reason': 'A reason is required for a criteria change.'})
        active = attrs.get('active', instance.active if instance else False)
        has_required = instance.items.filter(mandatory=True).exists() if instance else any(i['mandatory'] for i in attrs.get('items', []))
        if active and not has_required:
            raise serializers.ValidationError('An active requirement needs at least one mandatory evidence item.')
        area = attrs.get('area', instance.area if instance else None)
        code = attrs.get('code', instance.code if instance else None)
        existing = Requirement.objects.filter(area=area, code=code)
        if instance:
            existing = existing.exclude(pk=instance.pk)
        if existing.exists():
            raise serializers.ValidationError('This requirement code is already used in the area.')
        return attrs

    def create(self, validated_data):
        items = validated_data.pop('items', [])
        validated_data.pop('applicability_reason', None)
        validated_data.pop('change_reason', None)
        requirement = Requirement.objects.create(**validated_data)
        for item in items:
            EvidenceItem.objects.create(requirement=requirement, **item)
        return requirement

    def update(self, instance, validated_data):
        validated_data.pop('applicability_reason', None)
        validated_data.pop('change_reason', None)
        return super().update(instance, validated_data)


class UploadInput(serializers.Serializer):
    file = serializers.FileField()
    valid_until = serializers.DateField(required=False, allow_null=True)
    title = serializers.CharField(max_length=180, required=False)
    category = serializers.CharField(max_length=100, required=False, default='Supporting Document')
    area = serializers.IntegerField(required=False)
    requirement = serializers.IntegerField(required=False)
    override_reason = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True, max_length=4000)


class MappingInput(serializers.Serializer):
    item = serializers.IntegerField()
    document = serializers.UUIDField()
    override_reason = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True, max_length=4000)


class SubmitInput(serializers.Serializer):
    mapping = serializers.IntegerField()
    version = serializers.IntegerField()
    override_reason = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True, max_length=4000)


class RequirementAssignmentInput(serializers.Serializer):
    user = serializers.IntegerField()
    reason = serializers.CharField(trim_whitespace=True, max_length=4000)
    replace = serializers.BooleanField(default=False)

    def validate_reason(self, value):
        if not value:
            raise serializers.ValidationError('A reason is required.')
        return value


class StewardshipInput(serializers.Serializer):
    steward = serializers.IntegerField()
    reason = serializers.CharField(trim_whitespace=True, max_length=4000)

    def validate_reason(self, value):
        if not value:
            raise serializers.ValidationError('A reason is required.')
        return value


class ReviewInput(serializers.Serializer):
    submission = serializers.IntegerField()
    outcome = serializers.ChoiceField(choices=['approved', 'revision_requested', 'rejected'])
    comment = serializers.CharField(required=False, allow_blank=True, default='', max_length=4000)

    def validate(self, attrs):
        if attrs['outcome'] != 'approved' and not attrs['comment'].strip():
            raise serializers.ValidationError('Explain the requested revision or rejection.')
        return attrs


class CertificationInput(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=['complete', 'reopened'])
    rationale = serializers.CharField(trim_whitespace=True, max_length=4000)
    submissions = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False)
    packages = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False)

    def validate_rationale(self, value):
        if not value:
            raise serializers.ValidationError('A rationale is required.')
        return value


class PackageItemInput(serializers.Serializer):
    mapping = serializers.IntegerField(min_value=1)
    version = serializers.IntegerField(min_value=1)
    note = serializers.CharField(required=False, allow_blank=True, max_length=4000)


class PackageDraftInput(serializers.Serializer):
    requirement = serializers.IntegerField(min_value=1, required=False)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    items = PackageItemInput(many=True, required=False)
    override_reason = serializers.CharField(required=False, allow_blank=True, max_length=4000)


class PackageActionInput(serializers.Serializer):
    override_reason = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    confirm = serializers.BooleanField(required=False, default=False)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    copy_items = serializers.BooleanField(required=False, default=True)


class PackageReviewInput(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=['approved', 'revisions_requested'])
    comment = serializers.CharField(required=False, allow_blank=True, max_length=4000)

    def validate(self, attrs):
        if attrs['outcome'] == 'revisions_requested' and not attrs.get('comment', '').strip():
            raise serializers.ValidationError({'comment': 'Explain the revisions needed.'})
        return attrs


class CycleTransitionInput(serializers.Serializer):
    rationale = serializers.CharField(trim_whitespace=True, max_length=4000)

    def validate_rationale(self, value):
        if not value:
            raise serializers.ValidationError('A reason is required.')
        return value


class PasswordChangeInput(serializers.Serializer):
    current_password = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(trim_whitespace=False)

    def validate_new_password(self, value):
        validate_password(value, self.context['request'].user)
        return value


class PasswordResetRequestInput(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmInput(serializers.Serializer):
    uid = serializers.CharField(max_length=128)
    token = serializers.CharField(max_length=256)
    new_password = serializers.CharField(trim_whitespace=False)

    def validate_new_password(self, value):
        validate_password(value)
        return value
