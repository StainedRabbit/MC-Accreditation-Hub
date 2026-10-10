"""Add the one assignment needed by the isolated MIT 007 course demonstration."""
from django.core.management.base import BaseCommand, CommandError

from hub.models import Cycle, Requirement, RequirementAssignment, User


class Command(BaseCommand):
    help = 'Prepare fictional Faculty work in the dedicated mc_course_demo database only.'

    def handle(self, *args, **options):
        from django.db import connection

        if connection.settings_dict['NAME'] != 'mc_course_demo':
            raise CommandError('This command only accepts the dedicated mc_course_demo database.')
        cycle = Cycle.objects.get(is_demo=True, title='DEMO · Graduate School 2026')
        if Cycle.objects.exclude(pk=cycle.pk).exists():
            raise CommandError('Unexpected non-demo cycle; no course fixture changed.')
        requirement = Requirement.objects.get(area__cycle=cycle, area__code='A2', code='DEMO-02')
        coordinator = User.objects.get(username='demo.coordinator')
        custodian = User.objects.get(username='demo.custodian')
        assignment, created = RequirementAssignment.objects.get_or_create(
            requirement=requirement, user=custodian,
            defaults={'assigned_by': coordinator},
        )
        if not assignment.active:
            raise CommandError('Existing assignment is inactive; reset the disposable demo fixture.')
        self.stdout.write('Fictional Faculty assignment ready.' if created else 'Fictional Faculty assignment already ready.')
