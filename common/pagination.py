"""
Standard pagination class used by all list endpoints.
Returns a consistent envelope with page metadata.
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from datetime import datetime, timezone


class StandardResultsPagination(PageNumberPagination):
    """
    Default pagination: 20 items per page, max 100.
    Response shape:
    {
        "success": true,
        "message": "Success",
        "data": {
            "content": [...],
            "page": 1,
            "size": 20,
            "totalElements": 150,
            "totalPages": 8,
            "hasNext": true,
            "hasPrevious": false
        },
        "errors": null,
        "timestamp": "...",
        "path": "..."
    }
    """
    page_size = 20
    page_size_query_param = "size"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data):
        return Response({
            "success": True,
            "message": "Success",
            "data": {
                "content": data,
                "page": self.page.number,
                "size": self.get_page_size(self.request),
                "totalElements": self.page.paginator.count,
                "totalPages": self.page.paginator.num_pages,
                "hasNext": self.page.has_next(),
                "hasPrevious": self.page.has_previous(),
            },
            "errors": None,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "path": self.request.path,
        })

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message": {"type": "string"},
                "data": {
                    "type": "object",
                    "properties": {
                        "content": schema,
                        "page": {"type": "integer"},
                        "size": {"type": "integer"},
                        "totalElements": {"type": "integer"},
                        "totalPages": {"type": "integer"},
                        "hasNext": {"type": "boolean"},
                        "hasPrevious": {"type": "boolean"},
                    },
                },
                "errors": {"type": "null"},
                "timestamp": {"type": "string", "format": "date-time"},
                "path": {"type": "string"},
            },
        }