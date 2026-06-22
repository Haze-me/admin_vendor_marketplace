"""
Centralised exception handling.

custom_exception_handler is registered in REST_FRAMEWORK settings
and converts all exceptions to the standard response envelope.
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    APIException,
    ValidationError,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
    MethodNotAllowed,
    Throttled,
)
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom Domain Exceptions
# ---------------------------------------------------------------------------

class BusinessRuleViolation(APIException):
    """Raised when a business rule is violated (e.g. approving already-approved vendor)."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Business rule violation."
    default_code = "business_rule_violation"


class ResourceNotFound(APIException):
    """Raised when a requested resource does not exist (or is soft-deleted)."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Resource not found."
    default_code = "not_found"


class DuplicateResource(APIException):
    """Raised when attempting to create a resource that already exists."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Resource already exists."
    default_code = "duplicate_resource"


class InsufficientStock(APIException):
    """Raised when stock is insufficient for a requested operation."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Insufficient stock."
    default_code = "insufficient_stock"


class VendorNotApproved(APIException):
    """Raised when a vendor attempts an action that requires approval."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Vendor account is not approved."
    default_code = "vendor_not_approved"


class InvalidStatusTransition(APIException):
    """Raised when an invalid status transition is attempted."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Invalid status transition."
    default_code = "invalid_status_transition"


# ---------------------------------------------------------------------------
# Exception Handler
# ---------------------------------------------------------------------------

def _format_validation_errors(detail) -> list:
    """
    Recursively format DRF ValidationError detail into a flat list of
    {"field": "...", "message": "..."} dicts.
    """
    errors = []
    if isinstance(detail, dict):
        for field, messages in detail.items():
            if isinstance(messages, list):
                for msg in messages:
                    errors.append({"field": field, "message": str(msg)})
            elif isinstance(messages, dict):
                errors.extend(_format_validation_errors(messages))
            else:
                errors.append({"field": field, "message": str(messages)})
    elif isinstance(detail, list):
        for item in detail:
            if isinstance(item, dict):
                errors.extend(_format_validation_errors(item))
            else:
                errors.append({"field": "non_field_errors", "message": str(item)})
    else:
        errors.append({"field": "non_field_errors", "message": str(detail)})
    return errors


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler.
    Converts all exceptions to the standard response envelope format.
    Registered via REST_FRAMEWORK['EXCEPTION_HANDLER'] in settings.
    """
    from datetime import datetime, timezone
    from rest_framework.response import Response

    # Convert Django exceptions to DRF equivalents
    if isinstance(exc, Http404):
        exc = NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = PermissionDenied()

    # Let DRF handle the response construction first
    response = exception_handler(exc, context)

    request = context.get("request")
    path = request.path if request else None
    timestamp = datetime.now(tz=timezone.utc).isoformat()

    if response is not None:
        errors = None
        message = "An error occurred"

        if isinstance(exc, ValidationError):
            message = "Validation failed"
            errors = _format_validation_errors(exc.detail)
        elif isinstance(exc, AuthenticationFailed):
            message = str(exc.detail) if hasattr(exc, "detail") else "Authentication failed"
        elif isinstance(exc, NotAuthenticated):
            message = "Authentication credentials were not provided"
        elif isinstance(exc, PermissionDenied):
            message = "You do not have permission to perform this action"
        elif isinstance(exc, NotFound):
            message = "Resource not found"
        elif isinstance(exc, MethodNotAllowed):
            message = f"Method '{exc.args[0] if exc.args else ''}' not allowed"
        elif isinstance(exc, Throttled):
            message = "Request was throttled. Try again later."
        elif isinstance(exc, APIException):
            message = str(exc.detail) if hasattr(exc, "detail") else str(exc)
        else:
            message = "An unexpected error occurred"

        response.data = {
            "success": False,
            "message": message,
            "data": None,
            "errors": errors,
            "timestamp": timestamp,
            "path": path,
        }
        return response

    # Unhandled exception — log it and return 500
    logger.exception("Unhandled exception", exc_info=exc)
    return Response(
        {
            "success": False,
            "message": "Internal server error",
            "data": None,
            "errors": None,
            "timestamp": timestamp,
            "path": path,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )