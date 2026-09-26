from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from hub.models import Cycle, User
from hub.audit import write_audit
from hub.access import has_cyclewide_coordinator
from hub.compliance import with_evidence, summary


class Command(BaseCommand):
    help = 'Close an active cycle with an operator reason; a scoped Coordinator can later reopen it in the application.'

    def add_arguments(self, parser):
        parser.add_argument('cycle_id', type=int)
        parser.add_argument('--actor-id', required=True, type=int, help='Active staff account of the named operator.')
        parser.add_argument('--reason', required=True, help='Operator reason recorded in the audit history.')

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['reason'].strip():
            raise CommandError('A non-empty reason is required.')
        actor = User.objects.filter(pk=options['actor_id'], is_active=True, is_staff=True).first()
        if actor is None:
            raise CommandError('Select an active staff operator account.')
        cycle = Cycle.objects.select_for_update().filter(pk=options['cycle_id']).first()
        if not cycle or cycle.status != 'active':
            raise CommandError('Select an existing active cycle.')
        if not has_cyclewide_coordinator(actor, cycle):
            raise CommandError('The operator needs an explicit cycle-wide Coordinator grant.')
        cycle.closed_at = timezone.now()
        cycle.status = 'closed'
        cycle.save(update_fields=['closed_at', 'status'])
        for area in cycle.areas.all():
            write_audit(actor, area, 'cycle_closed', f'cycle:{cycle.pk}',
                rationale=options['reason'].strip(), closed_at=cycle.closed_at.isoformat(),
                compliance=summary(with_evidence(area.requirements.all())))
        self.stdout.write(self.style.SUCCESS(f'Cycle {cycle.pk} closed. Requirements, mappings, and decisions are read-only.'))
