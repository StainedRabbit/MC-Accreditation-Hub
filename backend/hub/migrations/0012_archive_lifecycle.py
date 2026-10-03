from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('hub', '0011_documentscan'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.AddField(model_name='cycle', name='archived_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='cycle', name='archived_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='archived_cycles', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='cycle', name='archive_reason', field=models.TextField(blank=True)),
        migrations.AddField(model_name='requirement', name='archived_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='requirement', name='archived_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='archived_requirements', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='requirement', name='archive_reason', field=models.TextField(blank=True)),
    ]
