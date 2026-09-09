import os
from datetime import date
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from hub.models import User, Cycle, Area, RoleAssignment, Requirement, EvidenceItem


class Command(BaseCommand):
    help = 'Create fictional sample data. Requires MC_DEMO_PASSWORD; never overwrites existing accounts.'

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.getenv('MC_DEMO_PASSWORD', '')
        if len(password) < 12:
            raise CommandError('Set MC_DEMO_PASSWORD to a unique demo-only password of at least 12 characters.')
        if Cycle.objects.filter(title='DEMO · Graduate School 2026').exists():
            self.stdout.write('Demo cycle already exists. No records changed.')
            return
        names = {'coordinator': ('Maria', 'Santos'), 'reviewer': ('Elena', 'Garcia'), 'custodian': ('Juan', 'Dela Cruz'),
                 'viewer': ('Demo', 'Dean'), 'administrator': ('Demo', 'Administrator')}
        if User.objects.filter(username__in=[f'demo.{r}' for r in names]).exists():
            raise CommandError('A demo username already exists; refusing to modify existing accounts.')
        users = {r: User.objects.create_user(username=f'demo.{r}', email=f'{r}@demo.invalid', password=password,
                    first_name=n[0], last_name=n[1], department='Graduate School', is_staff=r == 'administrator',
                    is_superuser=r == 'administrator') for r, n in names.items()}
        cycle = Cycle.objects.create(title='DEMO · Graduate School 2026', status='active', is_demo=True)
        for role in ['coordinator', 'viewer', 'administrator']:
            RoleAssignment.objects.create(user=users[role], cycle=cycle, role=role)
        categories = [('Vision, Mission & Goals', '🎯'), ('Faculty', '👩‍🏫'), ('Curriculum & Instruction', '📚'),
                      ('Students', '🎓'), ('Research', '🔬'), ('Extension & Community', '🤝'),
                      ('Library & Learning Resources', '📖'), ('Physical Facilities', '🏛️')]
        for i, (title, icon) in enumerate(categories, 1):
            area = Area.objects.create(cycle=cycle, code=f'A{i}', title=title, icon=icon, order=i)
            for role in ['reviewer', 'custodian']:
                RoleAssignment.objects.create(user=users[role], cycle=cycle, area=area, role=role)
            req = Requirement.objects.create(area=area, code=f'DEMO-{i:02}', title=f'{title} Documentation',
                description='Fictional practice requirement. Replace with the official approved instrument before institutional use.',
                responsible='Graduate School', deadline=date(2026, 12, 15), active=True, created_by=users['coordinator'])
            EvidenceItem.objects.create(requirement=req, label='Approved plan or policy', criteria='A complete, readable sample plan with a date and responsible office.')
            EvidenceItem.objects.create(requirement=req, label='Implementation report', criteria='A sample report describing activities and outcomes.')
        self.stdout.write(self.style.SUCCESS('Created demo cycle, eight areas, eight requirements, and five accounts.'))
        self.stdout.write('Usernames: ' + ', '.join(f'demo.{r}' for r in names))
