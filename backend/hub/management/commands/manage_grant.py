from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from hub.audit import suppress_model_audit, write_audit
from hub.models import Area, Cycle, RoleAssignment, User


class Command(BaseCommand):
    help = 'Add or revoke one academic scope grant as a separately permitted named operator.'

    def add_arguments(self, parser):
        parser.add_argument('--actor-id', required=True, type=int)
        parser.add_argument('--target-id', required=True, type=int)
        parser.add_argument('--role', required=True)
        parser.add_argument('--cycle-id', required=True, type=int)
        parser.add_argument('--area-id', type=int)
        parser.add_argument('--action', required=True, choices=('add', 'revoke'))
        parser.add_argument('--reason', required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        reason = options['reason'].strip()
        if not reason:
            raise CommandError('A non-empty reason is required.')
        actor = User.objects.filter(pk=options['actor_id'], is_active=True, is_staff=True).first()
        if actor is None or not actor.has_perm('hub.manage_role_grants'):
            raise CommandError('An active staff operator with the grant permission is required.')
        target = User.objects.filter(pk=options['target_id']).first()
        if target is None or target.pk == actor.pk:
            raise CommandError('Select another existing target user.')
        role = options['role']
        if role not in ('coordinator', 'reviewer', 'custodian', 'viewer'):
            raise CommandError('Select a permitted academic role; new administrator grants are disabled.')
        cycle = Cycle.objects.filter(pk=options['cycle_id']).first()
        if cycle is None:
            raise CommandError('Select an existing cycle.')
        area_id = options['area_id']
        if role in ('reviewer', 'custodian') and area_id is None:
            raise CommandError('Reviewer and Custodian grants require an area.')
        if area_id is not None and not Area.objects.filter(pk=area_id, cycle=cycle).exists():
            raise CommandError('Area must belong to the selected cycle.')
        scope = dict(user=target, cycle=cycle, area_id=area_id, role=role)
        try:
            if options['action'] == 'add':
                if not target.is_active:
                    raise CommandError('Activate the target account before granting access.')
                if RoleAssignment.objects.filter(**scope).exists():
                    raise CommandError('This grant already exists.')
                with suppress_model_audit():
                    grant = RoleAssignment.objects.create(**scope)
                audit_action = 'grant_created'
            else:
                grant = RoleAssignment.objects.select_for_update().filter(**scope).first()
                if grant is None:
                    raise CommandError('This grant does not exist.')
                grant_id = grant.pk
                with suppress_model_audit():
                    grant.delete()
                grant.pk = grant_id
                audit_action = 'grant_revoked'
        except (IntegrityError, ValidationError) as exc:
            raise CommandError(f'Invalid or duplicate grant: {exc}') from exc
        write_audit(actor, None, audit_action, f'grant:{grant.pk}',
                    target_user_id=target.pk, target_cycle_id=cycle.pk,
                    target_area_id=area_id, role=role, reason=reason)
        self.stdout.write(self.style.SUCCESS(f'{options["action"].capitalize()}ed grant {grant.pk}.'))
