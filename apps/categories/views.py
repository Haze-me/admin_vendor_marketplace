"""
Category views.

Endpoints:
  GET    /api/v1/categories/           -> list all categories (admin + vendor)
  POST   /api/v1/categories/           -> create category (admin only)
  GET    /api/v1/categories/<id>/      -> retrieve category (admin + vendor)
  PUT    /api/v1/categories/<id>/      -> update category (admin only)
  DELETE /api/v1/categories/<id>/      -> soft delete category (admin only)
"""
import logging
from rest_framework.views import APIView

from apps.categories.models import Category
from apps.categories.serializers import (
    CategoryCreateSerializer,
    CategoryUpdateSerializer,
    CategoryDetailSerializer,
    CategoryListSerializer,
)
from apps.accounts.permissions import IsAdminUser, IsAdminOrVendor
from common.responses import success_response, created_response, no_content_response
from common.exceptions import ResourceNotFound
from common.pagination import StandardResultsPagination
from events.producers import publish_event
from events.topics import KafkaTopics


logger = logging.getLogger(__name__)


def get_category_or_404(category_id: str) -> Category:
    try:
        return Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        raise ResourceNotFound(f"Category with id '{category_id}' not found.")


class CategoryListCreateView(APIView):
    """
    GET  -> list categories (admin and vendor can view)
    POST -> create category (admin only)
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAdminOrVendor()]
        return [IsAdminUser()]

    def get(self, request):
        queryset = Category.objects.select_related("parent").prefetch_related("children")

        # Filter by active status
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # Filter parent-only categories
        parents_only = request.query_params.get("parents_only")
        if parents_only and parents_only.lower() == "true":
            queryset = queryset.filter(parent__isnull=True)

        # Search by name
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = CategoryListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = CategoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        logger.info("Category created: %s by %s", category.name, request.user.email)

        try:
            publish_event(
                topic=KafkaTopics.CATEGORY_CREATED,
                event_type=KafkaTopics.CATEGORY_CREATED,
                payload={
                    "categoryId": str(category.id),
                    "name": category.name,
                    "description": category.description,
                    "slug": category.slug,
                    "parentId": str(category.parent.id) if category.parent else None,
                    "isActive": category.is_active,
                },
                key=str(category.id),
            )
        except Exception as e:
            logger.error("Failed to publish category.created event: %s", e)

        return created_response(
            data=CategoryDetailSerializer(category).data,
            message="Category created successfully.",
            request=request,
        )


class CategoryDetailView(APIView):
    """
    GET    -> retrieve single category (admin and vendor)
    PUT    -> update category (admin only)
    DELETE -> soft delete category (admin only)
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAdminOrVendor()]
        return [IsAdminUser()]

    def get(self, request, category_id):
        category = get_category_or_404(category_id)
        serializer = CategoryDetailSerializer(category)
        return success_response(data=serializer.data, request=request)

    def put(self, request, category_id):
        category = get_category_or_404(category_id)
        serializer = CategoryUpdateSerializer(category, data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        logger.info("Category updated: %s by %s", category.name, request.user.email)

        try:
            publish_event(
                topic=KafkaTopics.CATEGORY_UPDATED,
                event_type=KafkaTopics.CATEGORY_UPDATED,
                payload={
                    "categoryId": str(category.id),
                    "name": category.name,
                    "description": category.description,
                    "slug": category.slug,
                    "parentId": str(category.parent.id) if category.parent else None,
                    "isActive": category.is_active,
                },
                key=str(category.id),
            )
        except Exception as e:
            logger.error("Failed to publish category.updated event: %s", e)

        return success_response(
            data=CategoryDetailSerializer(category).data,
            message="Category updated successfully.",
            request=request,
        )

    def delete(self, request, category_id):
        category = get_category_or_404(category_id)
        category_name = category.name
        category.delete()  # soft delete via BaseModel
        logger.info("Category soft-deleted: %s by %s", category_name, request.user.email)
        return no_content_response()