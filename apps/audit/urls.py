"""
URL patterns for the audit app.
All routes mounted under /api/v1/audit/ in config/urls.py.
"""
from django.urls import path
from apps.audit.views import AuditLogListView, AuditLogDetailView

urlpatterns = [
    path("", AuditLogListView.as_view(), name="audit-log-list"),
    path("<uuid:log_id>/", AuditLogDetailView.as_view(), name="audit-log-detail"),
]