import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('hub', '0013_alter_cycle_options_alter_roleassignment_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UploadIntent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('storage_key', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('title', models.CharField(blank=True, max_length=180)),
                ('category', models.CharField(default='Supporting Document', max_length=100)),
                ('original_name', models.CharField(max_length=255)),
                ('content_type', models.CharField(max_length=120)),
                ('size', models.PositiveIntegerField()),
                ('checksum', models.CharField(max_length=64)),
                ('valid_until', models.DateField(blank=True, null=True)),
                ('override_reason', models.TextField(blank=True)),
                ('idempotency_key', models.UUIDField(blank=True, null=True)),
                ('request_fingerprint', models.CharField(max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('area', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='upload_intents', to='hub.area')),
                ('completed_version', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='upload_intent', to='hub.documentversion')),
                ('document', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='upload_intents', to='hub.document')),
                ('requirement', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='upload_intents', to='hub.requirement')),
                ('uploader', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='upload_intents', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='uploadintent',
            constraint=models.UniqueConstraint(fields=('uploader', 'idempotency_key'), name='upload_intent_idempotency_user'),
        ),
    ]
