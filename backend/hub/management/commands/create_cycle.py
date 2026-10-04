import json
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from hub.audit import suppress_model_audit, write_audit
from hub.models import Cycle, Area, User


class Command(BaseCommand):
    help = 'Create an active cycle and its areas from JSON as a named permitted operator.'

    def add_arguments(self, parser):
        parser.add_argument('file')
        parser.add_argument('--actor-id', required=True, type=int)
        parser.add_argument('--reason', required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        reason = options['reason'].strip()
        if not reason:
            raise CommandError('A non-empty reason is required.')
        actor = User.objects.filter(pk=options['actor_id'], is_active=True, is_staff=True).first()
        if actor is None or not actor.has_perm('hub.provision_cycle'):
            raise CommandError('An active staff operator with cycle-provisioning permission is required.')
        try:
            data = json.loads(Path(options['file']).read_text(encoding='utf-8'))
            if not isinstance(data, dict) or not all(isinstance(data.get(key), str) and data[key].strip()
                                                     for key in ('title', 'program', 'instrument')):
                raise ValueError('title, program and instrument must be non-empty strings')
            entries = data.get('areas')
            if not isinstance(entries, list) or not entries:
                raise ValueError('areas must be a nonempty list')
            with suppress_model_audit():
                cycle = Cycle(title=data['title'].strip(), program=data['program'].strip(),
                              instrument=data['instrument'].strip(), status='active')
                cycle.full_clean()
                cycle.save()
                codes = set()
                for i, entry in enumerate(entries):
                    if not isinstance(entry, dict) or not isinstance(entry.get('code'), str) or not isinstance(entry.get('title'), str):
                        raise ValueError('each area needs a code and title')
                    code = entry['code'].strip()
                    title = entry['title'].strip()
                    if not code or not title or code in codes:
                        raise ValueError('area codes and titles must be non-empty; codes must be unique')
                    codes.add(code)
                    area = Area(cycle=cycle, code=code, title=title, icon=entry.get('icon', '📁'), order=i)
                    area.full_clean()
                    area.save()
            write_audit(actor, None, 'cycle_provisioned', f'cycle:{cycle.pk}', reason=reason,
                        program=cycle.program, instrument=cycle.instrument,
                        areas=[{'id': area.pk, 'code': area.code} for area in cycle.areas.all()])
        except (ValueError, KeyError, TypeError, OSError, ValidationError, IntegrityError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f'Created cycle {cycle.pk} with {len(entries)} areas.'))
