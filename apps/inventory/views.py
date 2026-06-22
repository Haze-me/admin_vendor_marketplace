"""
Inventory views.

Vendor endpoints:
  GET   /api/v1/inventory/<product_id>/         -> view stock for own product
  PATCH /api/v1/inventory/<product_id>/         -> update stock for own product

Admin endpoints:
  GET   /api/v1/inventory/admin/                -> list all inventory records
  GET   /api/v1/inventory/admin/<product_id>/   -> view any product's stock
  PATCH /api/v1/inventory/admin/<product_id>/   -> update any product's stock

Internal endpoints (called by Commerce Service during checkout):
  POST  /api/v1/inventory/internal/reserve/     -> reserve stock for an order
  POST  /api/v1/inventory/internal/release/     -> release reserved stock (order cancelled)
  POST  /api/v1/inventory/internal/confirm/     -> confirm sale (order completed)
"""
import logging
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from apps.inventory.models import Inventory
from apps.inventory.serializers import (
    InventoryDetailSerializer,
    InventoryUpdateSerializer,
    StockReservationRequestSerializer,
    StockReleaseRequestSerializer,
)
from apps.inventory.services import InventoryService
from apps.accounts.permissions import IsAdminUser, IsVendorUser
from apps.audit.services import AuditService
from common.responses import success_response, error_response
from common.exceptions import ResourceNotFound, InsufficientStock, BusinessRuleViolation
from common.pagination import StandardResultsPagination

logger = logging.getLogger(__name__)


class VendorInventoryView(APIView):
    """
    Vendor views or updates stock for one of their own products.
    Vendor cannot access another vendor's inventory.
    """
    permission_classes = [IsVendorUser]

    def get(self, request, product_id):
        vendor = request.user.vendor_profile
        try:
            inventory = Inventory.objects.select_related("product__vendor").get(
                product_id=product_id,
                product__vendor=vendor,
            )
        except Inventory.DoesNotExist:
            raise ResourceNotFound(
                "Inventory record not found for this product."
            )
        serializer = InventoryDetailSerializer(inventory)
        return success_response(data=serializer.data, request=request)

    def patch(self, request, product_id):
        vendor = request.user.vendor_profile
        try:
            existing = Inventory.objects.get(
                product_id=product_id,
                product__vendor=vendor,
            )
        except Inventory.DoesNotExist:
            raise ResourceNotFound(
                "Inventory record not found for this product."
            )

        old_quantity = existing.available_quantity

        serializer = InventoryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        inventory = InventoryService.update_stock(
            product_id=str(product_id),
            new_quantity=serializer.validated_data["available_quantity"],
        )

        AuditService.log_inventory_update(
            request=request,
            inventory=inventory,
            old_quantity=old_quantity,
        )

        logger.info(
            "Vendor %s updated stock for product %s",
            vendor.id, product_id,
        )
        return success_response(
            data=InventoryDetailSerializer(inventory).data,
            message="Stock updated successfully.",
            request=request,
        )


class AdminInventoryListView(APIView):
    """Admin lists inventory records across all products."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = Inventory.objects.select_related(
            "product", "product__vendor"
        ).order_by("-updated_at")

        vendor_id = request.query_params.get("vendor_id")
        if vendor_id:
            queryset = queryset.filter(product__vendor_id=vendor_id)

        in_stock = request.query_params.get("in_stock")
        if in_stock and in_stock.lower() == "true":
            queryset = queryset.filter(available_quantity__gt=0)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = InventoryDetailSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminInventoryDetailView(APIView):
    """Admin views or updates stock for any product."""
    permission_classes = [IsAdminUser]

    def get(self, request, product_id):
        inventory = InventoryService.get_inventory_or_404(str(product_id))
        return success_response(
            data=InventoryDetailSerializer(inventory).data,
            request=request,
        )

    def patch(self, request, product_id):
        serializer = InventoryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        inventory = InventoryService.update_stock(
            product_id=str(product_id),
            new_quantity=serializer.validated_data["available_quantity"],
        )
        logger.info(
            "Admin %s updated stock for product %s",
            request.user.email, product_id,
        )
        return success_response(
            data=InventoryDetailSerializer(inventory).data,
            message="Stock updated successfully.",
            request=request,
        )


class InternalStockReserveView(APIView):
    """
    INTERNAL endpoint — called synchronously by Commerce Service during
    checkout to reserve stock for every item in an order.

    All-or-nothing: if any single item has insufficient stock, the entire
    request fails with 409 and NOTHING is reserved (full rollback).

    SECURITY NOTE: this endpoint has no authentication in this iteration.
    In production this MUST be restricted to internal network access only
    (e.g. via the API Gateway blocking external access to /internal/* routes,
    or a shared internal service-to-service API key). Flagged here as a
    known gap to close in Phase 4 (API Gateway) or via network-level rules
    in Phase 6 (Docker Compose internal networking).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StockReservationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data["items"]

        try:
            reserved = InventoryService.reserve_stock_bulk(items)
        except InsufficientStock as e:
            return error_response(
                message=str(e),
                http_status=409,
                request=request,
            )
        except ResourceNotFound as e:
            return error_response(
                message=str(e),
                http_status=404,
                request=request,
            )
        except BusinessRuleViolation as e:
            return error_response(
                message=str(e),
                http_status=422,
                request=request,
            )

        logger.info("Stock reserved for %s items via internal API", len(items))
        return success_response(
            data={"reservedItems": reserved},
            message="Stock reserved successfully.",
            request=request,
        )


class InternalStockReleaseView(APIView):
    """
    INTERNAL endpoint — called by Commerce Service when an order is
    cancelled or payment fails, releasing previously reserved stock
    back to available.

    Same security note as InternalStockReserveView applies.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StockReleaseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data["items"]

        try:
            InventoryService.release_stock_bulk(items)
        except ResourceNotFound as e:
            return error_response(message=str(e), http_status=404, request=request)
        except BusinessRuleViolation as e:
            return error_response(message=str(e), http_status=422, request=request)

        logger.info("Stock released for %s items via internal API", len(items))
        return success_response(message="Stock released successfully.", request=request)


class InternalStockConfirmView(APIView):
    """
    INTERNAL endpoint — called by Commerce Service when an order payment
    is confirmed, moving stock from reserved -> sold permanently.

    Same security note as InternalStockReserveView applies.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StockReleaseRequestSerializer(data=request.data)  # same shape
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data["items"]

        try:
            InventoryService.confirm_sale_bulk(items)
        except ResourceNotFound as e:
            return error_response(message=str(e), http_status=404, request=request)
        except BusinessRuleViolation as e:
            return error_response(message=str(e), http_status=422, request=request)

        logger.info("Sale confirmed for %s items via internal API", len(items))
        return success_response(message="Sale confirmed successfully.", request=request)