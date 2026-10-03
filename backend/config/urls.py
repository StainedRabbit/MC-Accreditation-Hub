from django.contrib import admin
from django.urls import path
from hub import views as v

urlpatterns = [
    path('api/admin/', admin.site.urls),
    path('api/health/', v.HealthView.as_view()), path('api/auth/csrf/', v.CsrfView.as_view()), path('api/auth/login/', v.LoginView.as_view()),
    path('api/auth/logout/', v.LogoutView.as_view()), path('api/auth/me/', v.MeView.as_view()),
    path('api/auth/password-change/', v.PasswordChangeView.as_view()), path('api/auth/password-reset/', v.PasswordResetRequestView.as_view()), path('api/auth/password-reset-confirm/', v.PasswordResetConfirmView.as_view()),
    path('api/cycles/', v.CyclesView.as_view()), path('api/cycles/<int:pk>/close/', v.CloseCycleView.as_view()), path('api/cycles/<int:pk>/reopen/', v.ReopenCycleView.as_view()), path('api/cycles/<int:pk>/archive/', v.CycleArchiveView.as_view()), path('api/cycles/<int:pk>/restore/', v.CycleRestoreView.as_view()), path('api/areas/', v.AreasView.as_view()), path('api/areas/<int:pk>/', v.AreaDetailView.as_view()),
    path('api/requirements/', v.RequirementsView.as_view()), path('api/requirements/<int:pk>/', v.RequirementsView.as_view()), path('api/requirements/<int:pk>/archive/', v.RequirementArchiveView.as_view()), path('api/requirements/<int:pk>/restore/', v.RequirementRestoreView.as_view()),
    path('api/requirements/<int:pk>/assignments/', v.RequirementAssignmentsView.as_view()),
    path('api/requirements/<int:pk>/certifications/', v.RequirementCertificationsView.as_view()),
    path('api/evidence-items/', v.ItemsView.as_view()), path('api/documents/', v.DocumentsView.as_view()),
    path('api/documents/<uuid:pk>/', v.DocumentsView.as_view()), path('api/documents/<uuid:pk>/versions/', v.VersionsView.as_view()),
    path('api/documents/<uuid:pk>/stewardship/', v.DocumentStewardshipView.as_view()),
    path('api/document-versions/<int:pk>/download/', v.DownloadView.as_view()),
    path('api/document-versions/<int:pk>/preview/', v.PreviewView.as_view()),
    path('api/evidence-mappings/', v.MappingsView.as_view()), path('api/submissions/', v.SubmissionsView.as_view()),
    path('api/review-decisions/', v.ReviewsView.as_view()), path('api/compliance/', v.ComplianceView.as_view()),
    path('api/packages/', v.PackagesView.as_view()), path('api/packages/<int:pk>/', v.PackagesView.as_view()),
    path('api/packages/<int:pk>/submit/', v.PackageSubmitView.as_view()),
    path('api/packages/<int:pk>/withdraw/', v.PackageWithdrawView.as_view()),
    path('api/packages/<int:pk>/review/', v.PackageReviewView.as_view()),
    path('api/packages/<int:pk>/resubmit/', v.PackageResubmitView.as_view()),
    path('api/audit/', v.AuditView.as_view()), path('api/search/', v.SearchView.as_view()),
    path('api/reports/compliance/', v.ComplianceReportView.as_view()),
]
