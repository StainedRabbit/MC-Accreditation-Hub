from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.decorators import method_decorator

from .audit import suppress_model_audit, write_audit
from .models import User, RoleAssignment, RequirementAssignment, Cycle, Area, Requirement, EvidenceItem, Document, DocumentVersion, EvidenceMapping, Submission, ReviewDecision, PackageAttempt, PackageItem, PackageDecision, RequirementCertification, CertificationEvidence, CertificationPackage, ApplicabilityDecision, AuditEvent


class ReasonForm(forms.ModelForm):
    reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), help_text='Required for the security audit.')

    def clean_reason(self):
        reason = self.cleaned_data['reason'].strip()
        if not reason:
            raise forms.ValidationError('A reason is required.')
        return reason

    def clean(self):
        values = super().clean()
        others = User.objects.exclude(pk=self.instance.pk)
        username, email = values.get('username'), values.get('email')
        if username and others.filter(email__iexact=username).exists():
            self.add_error('username', 'Username conflicts with another account email.')
        if email and others.filter(username__iexact=email).exists():
            self.add_error('email', 'Email conflicts with another account username.')
        return values


class AccountForm(ReasonForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'department', 'is_active')


class BreakGlassForm(ReasonForm):
    class Meta:
        model = User
        fields = AccountForm.Meta.fields + ('is_staff', 'is_superuser', 'groups', 'user_permissions')


class ReasonedPasswordForm(SetPasswordForm):
    reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))

    def clean_reason(self):
        reason = self.cleaned_data['reason'].strip()
        if not reason:
            raise forms.ValidationError('A reason is required.')
        return reason


@admin.register(User)
class HubUserAdmin(UserAdmin):
    # Product grants are changed only by the audited named-operator command.
    inlines = []
    add_form = AccountForm
    form = AccountForm
    filter_horizontal = ()
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff')

    def get_form(self, request, obj=None, **kwargs):
        kwargs['form'] = BreakGlassForm if request.user.is_superuser else AccountForm
        return admin.ModelAdmin.get_form(self, request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        fields = ['username', 'email', 'first_name', 'last_name', 'department', 'is_active']
        if request.user.is_superuser:
            fields += ['is_staff', 'is_superuser', 'groups', 'user_permissions']
        fields += ['reason']
        if obj and request.user.has_perm('hub.reset_user_password'):
            fields += ['password_reset_link']
        return ((None, {'fields': fields}),)

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and request.user.has_perm('hub.reset_user_password'):
            fields.append('password_reset_link')
        if obj and not self.has_change_permission(request, obj):
            fields += ['username', 'email', 'first_name', 'last_name', 'department', 'is_active']
            if request.user.is_superuser:
                fields += ['is_staff', 'is_superuser', 'groups', 'user_permissions']
            fields += ['reason']
        return fields

    @admin.display(description='Credential recovery')
    def password_reset_link(self, obj):
        url = reverse('admin:hub_user_password_change', args=(obj.pk,))
        return format_html('<a href="{}">Set a new password with a reason</a>', url)

    def has_add_permission(self, request):
        return request.user.is_active and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if not request.user.is_active or not super().has_change_permission(request, obj):
            return False
        if request.user.is_superuser or obj is None:
            return True
        return obj.pk != request.user.pk and not obj.is_staff and not obj.is_superuser and not obj.assignments.filter(role='administrator').exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if change:
            current = User.objects.select_for_update().get(pk=obj.pk)
            if not self.has_change_permission(request, current):
                raise PermissionDenied
            if not request.user.is_superuser:
                # Never overwrite a concurrent credential or privilege change.
                obj.password = current.password
                obj.is_staff = current.is_staff
                obj.is_superuser = current.is_superuser
        elif not self.has_add_permission(request):
            raise PermissionDenied
        if not change:
            obj.set_unusable_password()
            if not request.user.is_superuser:
                obj.is_staff = False
                obj.is_superuser = False
        changed = sorted(set(form.changed_data) & {'username', 'email', 'first_name', 'last_name', 'department', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'})
        with suppress_model_audit():
            super().save_model(request, obj, form, change)
        request._hub_account_audit = (obj.pk, change, form.cleaned_data['reason'], changed)

    def save_related(self, request, form, formsets, change):
        with suppress_model_audit():
            super().save_related(request, form, formsets, change)
        user_id, changed_account, reason, fields = request._hub_account_audit
        write_audit(request.user, None, 'account_updated' if changed_account else 'account_created',
                    f'user:{user_id}', reason=reason, changed_fields=fields)

    def get_urls(self):
        return [path('<path:object_id>/password/', self.admin_site.admin_view(self.user_change_password),
                     name='hub_user_password_change')] + admin.ModelAdmin.get_urls(self)

    @method_decorator(sensitive_post_parameters('new_password1', 'new_password2'))
    def user_change_password(self, request, object_id, form_url=''):
        if not request.user.is_active or not request.user.has_perm('hub.reset_user_password'):
            raise PermissionDenied
        target = User.objects.filter(pk=object_id).first()
        if target is None:
            raise Http404
        if not request.user.is_superuser and (target.is_staff or target.is_superuser or target.assignments.filter(role='administrator').exists()):
            raise PermissionDenied
        form = ReasonedPasswordForm(target, request.POST or None)
        if request.method == 'POST' and form.is_valid():
            with transaction.atomic():
                current = User.objects.select_for_update().get(pk=target.pk)
                if not request.user.is_superuser and (current.is_staff or current.is_superuser or current.assignments.filter(role='administrator').exists()):
                    raise PermissionDenied
                current.set_password(form.cleaned_data['new_password1'])
                with suppress_model_audit():
                    current.save(update_fields=['password'])
                write_audit(request.user, None, 'account_password_set', f'user:{current.pk}',
                            reason=form.cleaned_data['reason'])
            messages.success(request, 'Password changed. Follow the approved identity-verification and secure-delivery procedure.')
            return HttpResponseRedirect(reverse('admin:hub_user_change', args=(target.pk,)))
        context = {**self.admin_site.each_context(request), 'title': f'Set password: {target.username}',
                   'opts': self.opts, 'original': target, 'form': form, 'form_url': form_url}
        return TemplateResponse(request, 'admin/hub/user/password.html', context)


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Workflow records cannot bypass API invariants through Django administration.
for model in [Cycle, Area, Requirement, RoleAssignment, RequirementAssignment, EvidenceItem, Document, DocumentVersion, EvidenceMapping, Submission, ReviewDecision, PackageAttempt, PackageItem, PackageDecision, RequirementCertification, CertificationEvidence, CertificationPackage, ApplicabilityDecision, AuditEvent]:
    admin.site.register(model, ReadOnlyAdmin)
admin.site.site_header = 'MC Accreditation Hub Administration'
