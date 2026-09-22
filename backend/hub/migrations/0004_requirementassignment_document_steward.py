# Generated for F04 user-linked requirement assignments and stewardship.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hub', '0003_requirementcertification'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='steward',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name='stewarded_documents', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='RequirementAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assigned_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                   related_name='assignments_made', to=settings.AUTH_USER_MODEL)),
                ('requirement', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                  related_name='user_assignments', to='hub.requirement')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                           related_name='requirement_assignments', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='requirementassignment',
            constraint=models.UniqueConstraint(fields=('requirement', 'user'), name='unique_requirement_user_assignment'),
        ),
    ]
