import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('hub', '0004_requirementassignment_document_steward')]

    operations = [
        migrations.AddField(model_name='requirement', name='criteria_revision', field=models.PositiveIntegerField(default=1)),
        migrations.AddField(model_name='submission', name='criteria_revision', field=models.PositiveIntegerField(default=1)),
        migrations.AddField(model_name='requirementcertification', name='criteria_snapshot', field=models.JSONField(blank=True, null=True)),
        migrations.CreateModel(name='CertificationEvidence', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('snapshot', models.JSONField()),
            ('certification', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='evidence', to='hub.requirementcertification')),
            ('submission', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='hub.submission')),
        ]),
        migrations.AddConstraint(model_name='certificationevidence', constraint=models.UniqueConstraint(fields=('certification', 'submission'), name='unique_certification_submission')),
        migrations.CreateModel(name='ApplicabilityDecision', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('applicable', models.BooleanField()),
            ('reason', models.TextField()),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('coordinator', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ('requirement', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='applicability_decisions', to='hub.requirement')),
        ], options={'ordering': ['-id']}),
    ]
