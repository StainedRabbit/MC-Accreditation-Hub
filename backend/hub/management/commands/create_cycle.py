import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from hub.models import Cycle, Area


class Command(BaseCommand):
    help = 'Create an active cycle and its area structure from a JSON file. No existing records are changed.'

    def add_arguments(self, parser):
        parser.add_argument('file')

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            data = json.loads(Path(options['file']).read_text(encoding='utf-8'))
            if not data.get('title') or not data.get('program') or not data.get('instrument') or not data.get('areas'):
                raise ValueError('title, program, instrument and a nonempty areas list are required')
            cycle = Cycle(title=data['title'], program=data['program'], instrument=data['instrument'], status='active')
            cycle.full_clean()
            cycle.save()
            for i, entry in enumerate(data['areas']):
                area = Area(cycle=cycle, code=entry['code'], title=entry['title'], icon=entry.get('icon', '📁'), order=i)
                area.full_clean()
                area.save()
        except (ValueError, KeyError, OSError) as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f'Created cycle {cycle.pk}. Assign users through /api/admin/.'))
