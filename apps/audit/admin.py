"""
Django admin registration for AuditLog model.
"""
from django.contrib import admin
from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "action",
        "actor_email",
        "entity_type",
        "entity_id",
        "ip_address",
        "created_at",
    ]
    list_filter = ["action", "entity_type"]
    search_fields = ["actor_email", "actor_id", "entity_id"]
    readonly_fields = [
        "id",
        "actor_id",
        "actor_email",
        "action",
        "entity_type",
        "entity_id",
        "ip_address",
        "user_agent",
        "metadata",
        "created_at",
    ]
    ordering = ["-created_at"]

    # Audit logs are immutable — disable all write operations
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False