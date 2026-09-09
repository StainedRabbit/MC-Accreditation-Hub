from rest_framework import serializers
from .models import Requirement, EvidenceItem


class ItemInput(serializers.Serializer):
    label = serializers.CharField(max_length=180)
    criteria = serializers.CharField(required=False, allow_blank=True, default='')
    mandatory = serializers.BooleanField(default=True)


class RequirementInput(serializers.ModelSerializer):
    items = ItemInput(many=True, required=False)

    class Meta:
        model = Requirement
        fields = ['area', 'code', 'title', 'description', 'responsible', 'deadline', 'active', 'applicable', 'exclusion_reason', 'items']
        validators = []

    def validate(self, attrs):
        instance = self.instance
        applicable = attrs.get('applicable', instance.applicable if instance else True)
        reason = attrs.get('exclusion_reason', instance.exclusion_reason if instance else '')
        if not applicable and not reason.strip():
            raise serializers.ValidationError('An exclusion reason is required.')
        if instance and 'area' in attrs and attrs['area'].id != instance.area_id:
            raise serializers.ValidationError('A requirement cannot move to another area.')
        if instance and 'items' in attrs:
            raise serializers.ValidationError('Existing evidence criteria are preserved; create a new requirement for structural changes.')
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
        requirement = Requirement.objects.create(**validated_data)
        for item in items:
            EvidenceItem.objects.create(requirement=requirement, **item)
        return requirement


class UploadInput(serializers.Serializer):
    file = serializers.FileField()
    valid_until = serializers.DateField(required=False, allow_null=True)
    title = serializers.CharField(max_length=180, required=False)
    category = serializers.CharField(max_length=100, required=False, default='Supporting Document')
    area = serializers.IntegerField(required=False)


class MappingInput(serializers.Serializer):
    item = serializers.IntegerField()
    document = serializers.UUIDField()


class SubmitInput(serializers.Serializer):
    mapping = serializers.IntegerField()
    version = serializers.IntegerField()


class ReviewInput(serializers.Serializer):
    submission = serializers.IntegerField()
    outcome = serializers.ChoiceField(choices=['approved', 'revision_requested', 'rejected'])
    comment = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        if attrs['outcome'] != 'approved' and not attrs['comment'].strip():
            raise serializers.ValidationError('Explain the requested revision or rejection.')
        return attrs


class CertificationInput(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=['complete', 'reopened'])
    rationale = serializers.CharField(trim_whitespace=True, max_length=4000)

    def validate_rationale(self, value):
        if not value:
            raise serializers.ValidationError('A rationale is required.')
        return value
