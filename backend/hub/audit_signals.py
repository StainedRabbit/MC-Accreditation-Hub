"""Account and grant writes, including Django admin inline changes."""
from django.db.models.signals import pre_save, post_save, post_delete, m2m_changed
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .audit import current_actor, write_audit
from .models import User, RoleAssignment, Cycle, Area


@receiver(pre_save, sender=User)
def remember_account_state(sender, instance, **kwargs):
    instance._audit_old = User.objects.filter(pk=instance.pk).values(
        'username', 'is_active', 'is_staff', 'is_superuser', 'password').first() if instance.pk else None


@receiver(post_save, sender=User)
def account_changed(sender, instance, created, **kwargs):
    if created:
        write_audit(current_actor(), None, 'account_created', f'user:{instance.pk}')
        return
    old = getattr(instance, '_audit_old', None)
    if old is None:
        return
    changes = {field: {'before': old[field], 'after': getattr(instance, field)}
               for field in ('username', 'is_active', 'is_staff', 'is_superuser')
               if old[field] != getattr(instance, field)}
    if changes:
        write_audit(current_actor(), None, 'account_updated', f'user:{instance.pk}', changes=changes)
    if old['password'] != instance.password:
        write_audit(current_actor(), None, 'account_password_set', f'user:{instance.pk}')


@receiver(pre_save, sender=RoleAssignment)
def remember_grant_state(sender, instance, **kwargs):
    instance._audit_old = RoleAssignment.objects.filter(pk=instance.pk).values(
        'user_id', 'role', 'cycle_id', 'area_id').first() if instance.pk else None


@receiver(post_save, sender=RoleAssignment)
def grant_saved(sender, instance, created, **kwargs):
    if created:
        write_audit(current_actor(), None, 'grant_created', f'grant:{instance.pk}',
                    user_id=instance.user_id, role=instance.role,
                    cycle_id=instance.cycle_id, area_id=instance.area_id)
    else:
        old = getattr(instance, '_audit_old', None)
        if old:
            after = {field: getattr(instance, field) for field in ('user_id', 'role', 'cycle_id', 'area_id')}
            if old != after:
                write_audit(current_actor(), None, 'grant_updated', f'grant:{instance.pk}',
                            before=old, after=after)


@receiver(post_delete, sender=RoleAssignment)
def grant_removed(sender, instance, **kwargs):
    write_audit(current_actor(), None, 'grant_revoked', f'grant:{instance.pk}',
                user_id=instance.user_id, role=instance.role,
                cycle_id=instance.cycle_id, area_id=instance.area_id)


@receiver(user_logged_in)
def admin_login(sender, request, user, **kwargs):
    if request.path.startswith('/api/admin/'):
        write_audit(user, None, 'admin_login', f'user:{user.pk}')


@receiver(user_logged_out)
def admin_logout(sender, request, user, **kwargs):
    if user and request and request.path.startswith('/api/admin/'):
        write_audit(user, None, 'admin_logout', f'user:{user.pk}')


@receiver(user_login_failed)
def admin_login_failed(sender, request, **kwargs):
    if request and request.path.startswith('/api/admin/'):
        write_audit(None, None, 'admin_login_failed', 'authentication')


@receiver(post_save, sender=Cycle)
def cycle_created(sender, instance, created, **kwargs):
    if created:
        write_audit(current_actor(), None, 'cycle_created', f'cycle:{instance.pk}')


@receiver(post_save, sender=Area)
def area_created(sender, instance, created, **kwargs):
    if created:
        # Keep the event addressable by cycle and area while allowing an empty area to be deleted.
        write_audit(current_actor(), None, 'area_created', f'area:{instance.pk}',
                    cycle_id=instance.cycle_id, area_id=instance.pk,
                    area_code=instance.code, area_title=instance.title)


@receiver(m2m_changed, sender=User.user_permissions.through)
def user_permission_changed(sender, instance, action, pk_set, reverse, **kwargs):
    if action in ('post_add', 'post_remove', 'post_clear'):
        write_audit(current_actor(), None, 'account_permission_' + action[5:],
                    f'user:{instance.pk}' if not reverse else f'permission:{instance.pk}',
                    permission_ids=sorted(pk_set or []))


@receiver(m2m_changed, sender=User.groups.through)
def user_group_changed(sender, instance, action, pk_set, reverse, **kwargs):
    if action in ('post_add', 'post_remove', 'post_clear'):
        write_audit(current_actor(), None, 'account_group_' + action[5:],
                    f'user:{instance.pk}' if not reverse else f'group:{instance.pk}',
                    group_ids=sorted(pk_set or []))
