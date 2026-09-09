from django.contrib import admin
from django.urls import path
from hub import views as v

urlpatterns = [
    path('api/admin/', admin.site.urls),
    path('api/auth/csrf/', v.CsrfView.as_view()), path('api/auth/login/', v.LoginView.as_view()),
    path('api/auth/logout/', v.LogoutView.as_view()), path('api/auth/me/', v.MeView.as_view()),
    path('api/cycles/', v.CyclesView.as_view()), path('api/areas/', v.AreasView.as_view()),
    path('api/requirements/', v.RequirementsView.as_view()), path('api/requirements/<int:pk>/', v.RequirementsView.as_view()),
    path('api/requirements/<int:pk>/certifications/', v.RequirementCertificationsView.as_view()),
    path('api/evidence-items/', v.ItemsView.as_view()), path('api/documents/', v.DocumentsView.as_view()),
    path('api/documents/<uuid:pk>/', v.DocumentsView.as_view()), path('api/documents/<uuid:pk>/versions/', v.VersionsView.as_view()),
    path('api/document-versions/<int:pk>/download/', v.DownloadView.as_view()),
    path('api/evidence-mappings/', v.MappingsView.as_view()), path('api/submissions/', v.SubmissionsView.as_view()),
    path('api/review-decisions/', v.ReviewsView.as_view()), path('api/compliance/', v.ComplianceView.as_view()),
    path('api/audit/', v.AuditView.as_view()), path('api/search/', v.SearchView.as_view()),
    path('api/reports/compliance/', v.ComplianceReportView.as_view()),
]
