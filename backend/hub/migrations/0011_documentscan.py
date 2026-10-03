from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('hub', '0010_documentversion_upload_idempotency')]

    operations = [
        migrations.CreateModel(
            name='DocumentScan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('result', models.CharField(choices=[('clean', 'Clean'), ('infected', 'Infected'), ('error', 'Error')], max_length=12)),
                ('checksum', models.CharField(max_length=64)),
                ('scanner_id', models.CharField(max_length=120)),
                ('scanned_at', models.DateTimeField(auto_now_add=True)),
                ('version', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='scans', to='hub.documentversion')),
            ],
            options={'ordering': ['-id']},
        ),
    ]
