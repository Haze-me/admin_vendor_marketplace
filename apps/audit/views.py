"""
Audit log views.

Endpoints:
  GET /api/v1/audit/          -> list audit logs (admin only)
  GET /api/v1/audit/<id>/     -> retrieve single audit log (admin only)

Filtering supported:
  ?actor_id=<uuid>
  ?action=PRODUCT_CREATED
  ?entity_type=Product
  ?entity_id=<uuid>
  ?date_from=2024-01-01
  ?date_to=2024-12-31
"""
import logging
from rest_framework.views import APIView
from django.utils.dateparse import parse_date
from django.utils import timezone
from datetime import datetime, time

from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.accounts.permissions import IsAdminUser
from common.responses import success_response
from common.exceptions import ResourceNotFound
from common.pagination import StandardResultsPagination

logger = logging.getLogger(__name__)


class AuditLogListView(APIView):
    """
    Admin lists audit logs with filtering.
    Audit logs are read-only — no create, update, or delete.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = AuditLog.objects.all()

        # Filter by actor
        actor_id = request.query_params.get("actor_id")
        if actor_id:
            queryset = queryset.filter(actor_id=actor_id)

        # Filter by action
        action = request.query_params.get("action")
        if action:
            queryset = queryset.filter(action=action.upper())

        # Filter by entity type
        entity_type = request.query_params.get("entity_type")
        if entity_type:
            queryset = queryset.filter(entity_type__iexact=entity_type)

        # Filter by entity id
        entity_id = request.query_params.get("entity_id")
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)

        # Filter by date range
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        if date_from:
            parsed = parse_date(date_from)
            if parsed:
                queryset = queryset.filter(
                    created_at__gte=datetime.combine(parsed, time.min).replace(
                        tzinfo=timezone.utc
                    )
                )

        if date_to:
            parsed = parse_date(date_to)
            if parsed:
                queryset = queryset.filter(
                    created_at__lte=datetime.combine(parsed, time.max).replace(
                        tzinfo=timezone.utc
                    )
                )

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AuditLogSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AuditLogDetailView(APIView):
    """Admin retrieves a single audit log entry."""
    permission_classes = [IsAdminUser]

    def get(self, request, log_id):
        try:
            log = AuditLog.objects.get(id=log_id)
        except AuditLog.DoesNotExist:
            raise ResourceNotFound("Audit log entry not found.")
        serializer = AuditLogSerializer(log)
        return success_response(data=serializer.data, request=request)