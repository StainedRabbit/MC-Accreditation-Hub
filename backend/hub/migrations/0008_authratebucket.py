from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('hub', '0007_requirement_legacy_submission_mode_packageattempt_and_more')]

    operations = [
        migrations.CreateModel(
            name='AuthRateBucket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=64, unique=True)),
                ('window_start', models.DateTimeField()),
                ('count', models.PositiveIntegerField(default=0)),
            ],
        ),
    ]
