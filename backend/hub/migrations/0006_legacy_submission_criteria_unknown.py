from django.db import migrations, models


def mark_legacy_revision_unknown(apps, schema_editor):
    # This field did not exist before F05. Existing approval history contains
    # no reliable record of which criteria text a submission was reviewed under.
    apps.get_model('hub', 'Submission').objects.all().update(criteria_revision=None)


class Migration(migrations.Migration):
    dependencies = [('hub', '0005_certification_support_applicability')]

    operations = [
        migrations.AlterField(model_name='submission', name='criteria_revision',
                              field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.RunPython(mark_legacy_revision_unknown),
    ]
