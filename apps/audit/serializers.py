"""
Serializers for audit app.
"""
from rest_framework import serializers
from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Read-only audit log representation."""

    class Meta:
        model = AuditLog
        fields = [
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
        read_only_fields = fields