from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hub.models import Area, Cycle, EvidenceItem, Requirement, RequirementAssignment, User


class Command(BaseCommand):
    help = 'Seed a legacy item-review fixture in the disposable browser database.'

    @transaction.atomic
    def handle(self, *args, **options):
        database_name = str(settings.DATABASES['default']['NAME'])
        if not database_name.startswith('mc_browser_'):
            raise CommandError('This fixture is limited to the disposable browser database.')
        cycle = Cycle.objects.get(title='DEMO · Graduate School 2026', is_demo=True)
        area = Area.objects.get(cycle=cycle, code='A2')
        coordinator = User.objects.get(username='demo.coordinator')
        custodian = User.objects.get(username='demo.custodian')
        requirement, _ = Requirement.objects.get_or_create(
            area=area,
            code='E2E-LEGACY-REVIEW',
            defaults={
                'title': 'Legacy review context fixture',
                'description': 'Current criteria for the legacy review context test.',
                'responsible': 'Graduate School',
                'active': True,
                'legacy_submission_mode': True,
                'created_by': coordinator,
            },
        )
        if not requirement.legacy_submission_mode:
            requirement.legacy_submission_mode = True
            requirement.save(update_fields=['legacy_submission_mode'])
        EvidenceItem.objects.get_or_create(
            requirement=requirement,
            label='Legacy review evidence',
            defaults={'criteria': 'A dated file with a clear responsible office.'},
        )
        RequirementAssignment.objects.get_or_create(
            requirement=requirement,
            user=custodian,
            defaults={'assigned_by': coordinator},
        )
        self.stdout.write(self.style.SUCCESS('Created the synthetic legacy review browser fixture.'))
