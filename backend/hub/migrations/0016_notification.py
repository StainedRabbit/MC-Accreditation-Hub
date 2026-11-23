from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('hub', '0015_areacomment'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(max_length=40)),
                ('event_key', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('package', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='hub.packageattempt')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
                ('requirement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='hub.requirement')),
                ('submission', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='hub.submission')),
            ],
            options={'ordering': ['-created_at', '-id'],
                     'indexes': [models.Index(fields=['recipient', 'read_at', '-created_at'], name='notification_inbox_idx')],
                     'constraints': [models.UniqueConstraint(fields=('recipient', 'event_key'), name='unique_recipient_notification_event')]},
        ),
    ]
