"""
Standardised API response envelope.

Every endpoint in this service returns:
{
    "success": true | false,
    "message": "Human-readable message",
    "data": { ... } | null,
    "errors": null | [ { "field": "...", "message": "..." } ],
    "timestamp": "ISO-8601",
    "path": "/api/v1/..."
}
"""
from datetime import datetime, timezone
from typing import Any, Optional
from rest_framework.response import Response
from rest_framework import status


def _build_envelope(
    success: bool,
    message: str,
    data: Any = None,
    errors: Optional[list] = None,
    http_status: int = status.HTTP_200_OK,
    request=None,
) -> Response:
    path = request.path if request else None
    body = {
        "success": success,
        "message": message,
        "data": data,
        "errors": errors,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "path": path,
    }
    return Response(body, status=http_status)


def success_response(
    data: Any = None,
    message: str = "Success",
    http_status: int = status.HTTP_200_OK,
    request=None,
) -> Response:
    return _build_envelope(
        success=True,
        message=message,
        data=data,
        errors=None,
        http_status=http_status,
        request=request,
    )


def created_response(
    data: Any = None,
    message: str = "Created successfully",
    request=None,
) -> Response:
    return _build_envelope(
        success=True,
        message=message,
        data=data,
        errors=None,
        http_status=status.HTTP_201_CREATED,
        request=request,
    )


def error_response(
    message: str = "An error occurred",
    errors: Optional[list] = None,
    http_status: int = status.HTTP_400_BAD_REQUEST,
    request=None,
) -> Response:
    return _build_envelope(
        success=False,
        message=message,
        data=None,
        errors=errors,
        http_status=http_status,
        request=request,
    )


def no_content_response() -> Response:
    """204 No Content — used for DELETE operations."""
    return Response(status=status.HTTP_204_NO_CONTENT)