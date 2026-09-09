from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, RoleAssignment, Cycle, Area, Requirement, EvidenceItem, Document, DocumentVersion, EvidenceMapping, Submission, ReviewDecision, RequirementCertification, AuditEvent


class AssignmentInline(admin.TabularInline):
    model = RoleAssignment
    extra = 0


@admin.register(User)
class HubUserAdmin(UserAdmin):
    inlines = [AssignmentInline]
    fieldsets = UserAdmin.fieldsets + (('School', {'fields': ('department',)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('School', {'fields': ('email', 'first_name', 'last_name', 'department')}),)

    def has_delete_permission(self, request, obj=None):
        return False


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Workflow records cannot bypass API invariants through Django administration.
for model in [Cycle, Area, Requirement, EvidenceItem, Document, DocumentVersion, EvidenceMapping, Submission, ReviewDecision, RequirementCertification, AuditEvent]:
    admin.site.register(model, ReadOnlyAdmin)
admin.site.site_header = 'MC Accreditation Hub Administration'
