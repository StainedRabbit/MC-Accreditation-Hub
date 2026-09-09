from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from hub.models import Cycle, AuditEvent
from hub.compliance import with_evidence, summary


class Command(BaseCommand):
    help = 'Close an active cycle, preserve the calculation date and log final area summaries. This cannot be reversed through the application.'

    def add_arguments(self, parser):
        parser.add_argument('cycle_id', type=int)

    @transaction.atomic
    def handle(self, *args, **options):
        cycle = Cycle.objects.select_for_update().filter(pk=options['cycle_id']).first()
        if not cycle or cycle.status != 'active':
            raise CommandError('Select an existing active cycle.')
        cycle.closed_at = timezone.now()
        cycle.status = 'closed'
        cycle.save(update_fields=['closed_at', 'status'])
        for area in cycle.areas.all():
            AuditEvent.objects.create(area=area, action='cycle_closed', record=cycle.title,
                detail={'closed_at': cycle.closed_at.isoformat(), 'compliance': summary(with_evidence(area.requirements.all()))})
        self.stdout.write(self.style.SUCCESS(f'Cycle {cycle.pk} closed. Requirements, mappings, and decisions are read-only.'))
