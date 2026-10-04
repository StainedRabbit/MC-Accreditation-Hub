import json
import os
from pathlib import Path

from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from hub.models import User


class Command(BaseCommand):
    help = 'Create fictional account-administration users only in the disposable isolated browser database.'

    @transaction.atomic
    def handle(self, *args, **options):
        scratch = Path(os.environ['E2E_SCRATCH'])
        if not scratch.name.startswith('isolated-browser-') or not os.environ.get('E2E_ISOLATED_DB_NAME', '').startswith('mc_browser_'):
            raise RuntimeError('Refusing to seed outside the isolated browser runner.')
        password = os.environ['E2E_SYNTHETIC_PASSWORD']
        users = {}
        for name, permissions in {
            'e2e.account.admin': ('add_user', 'change_user', 'view_user'),
            'e2e.credential.operator': ('view_user', 'reset_user_password'),
        }.items():
            user = User.objects.create_user(username=name, email=f'{name}@test.invalid', password=password, is_staff=True)
            user.user_permissions.add(*Permission.objects.filter(content_type__app_label='hub', codename__in=permissions))
            users[name] = user.pk
        target = User.objects.create_user(username='e2e.ordinary', email='e2e.ordinary@test.invalid', password=password)
        users['e2e.ordinary'] = target.pk
        (scratch / 'admin-fixture.json').write_text(json.dumps(users), encoding='utf-8')
        self.stdout.write('Created fictional admin browser fixture.')
