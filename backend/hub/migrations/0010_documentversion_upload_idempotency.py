from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hub', '0009_alter_auditevent_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='documentversion',
            name='idempotency_key',
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='documentversion',
            name='idempotency_fingerprint',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddConstraint(
            model_name='documentversion',
            constraint=models.UniqueConstraint(fields=('uploaded_by', 'idempotency_key'), name='version_upload_idempotency_user'),
        ),
    ]
