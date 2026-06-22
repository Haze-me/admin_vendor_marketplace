"""
AuditMiddleware — attaches request metadata to each request so that
audit log writers downstream can access the acting user and IP without
re-querying the database.

This is Celery-ready: the data is attached to the request object,
not written here. Actual DB writes happen in apps.audit.services.
"""
import logging

logger = logging.getLogger(__name__)


class AuditMiddleware:
    """
    Attaches audit context to every request:
    - request.audit_actor_id   -> UUID of authenticated user (or None)
    - request.audit_ip_address -> Client IP address
    - request.audit_user_agent -> User-Agent string

    These values are then read by AuditService.log() when writing
    audit log entries — no need to pass them manually from every view.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set defaults before the view runs
        request.audit_actor_id = None
        request.audit_ip_address = self._get_client_ip(request)
        request.audit_user_agent = request.META.get("HTTP_USER_AGENT", "")

        # Process the request through the view
        response = self.get_response(request)

        # After the view runs, the user is now authenticated
        # so we can capture their ID for audit purposes
        if hasattr(request, "user") and request.user and request.user.is_authenticated:
            request.audit_actor_id = str(request.user.id)

        return response

    @staticmethod
    def _get_client_ip(request) -> str:
        """
        Extract the real client IP address.

        When running behind the Spring Cloud Gateway or any reverse proxy,
        the real client IP is in the X-Forwarded-For header.
        We take the first IP in the chain — that is the original client.

        Example X-Forwarded-For: 41.58.123.45, 10.0.0.1
        We return:               41.58.123.45
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # First IP in the chain is the original client
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")