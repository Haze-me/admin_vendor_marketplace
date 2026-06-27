"""
Product views.

Vendor endpoints:
  GET    /api/v1/products/                        -> vendor lists own products
  POST   /api/v1/products/                        -> vendor creates product
  GET    /api/v1/products/<id>/                   -> vendor views own product
  PUT    /api/v1/products/<id>/                   -> vendor updates own product
  DELETE /api/v1/products/<id>/                   -> vendor soft-deletes own product
  POST   /api/v1/products/<id>/images/            -> vendor adds image to product
  DELETE /api/v1/products/<id>/images/<image_id>/ -> vendor removes image

Admin endpoints:
  GET    /api/v1/products/admin/                  -> admin lists all products
  GET    /api/v1/products/admin/<id>/             -> admin views any product
  PUT    /api/v1/products/admin/<id>/             -> admin updates any product
  DELETE /api/v1/products/admin/<id>/             -> admin soft-deletes any product
"""
import logging
from rest_framework.views import APIView

from apps.products.models import Product, ProductImage
from apps.products.serializers import (
    ProductCreateSerializer,
    ProductUpdateSerializer,
    ProductAdminUpdateSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductImageAddSerializer,
)
from apps.products.services import ProductService
from apps.accounts.permissions import IsAdminUser, IsVendorUser
from common.responses import success_response, created_response, no_content_response
from common.exceptions import ResourceNotFound
from common.pagination import StandardResultsPagination
from apps.audit.services import AuditService
from apps.audit.models import AuditAction


logger = logging.getLogger(__name__)


class ProductListCreateView(APIView):
    """Vendor lists their own products or creates a new one."""
    permission_classes = [IsVendorUser]

    def get(self, request):
        vendor = request.user.vendor_profile
        queryset = Product.objects.select_related(
            "category", "vendor"
        ).prefetch_related("product_images").filter(vendor=vendor)

        # Filter by status
        status = request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status.upper())

        # Search by name or SKU
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search) | \
                       queryset.filter(sku__icontains=search)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ProductListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ProductCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        vendor = request.user.vendor_profile
        product = ProductService.create_product(serializer.validated_data, vendor)

        AuditService.log_product_action(
            request=request,
            product=product,
            action=AuditAction.PRODUCT_CREATED,
        )

        return created_response(
            data=ProductDetailSerializer(product).data,
            message="Product created successfully.",
            request=request,
        )


class ProductDetailView(APIView):
    """Vendor views, updates, or deletes their own product."""
    permission_classes = [IsVendorUser]

    def get(self, request, product_id):
        vendor = request.user.vendor_profile
        product = ProductService.get_vendor_product_or_404(product_id, vendor)
        return success_response(
            data=ProductDetailSerializer(product).data,
            request=request,
        )

    def put(self, request, product_id):
        vendor = request.user.vendor_profile
        product = ProductService.get_vendor_product_or_404(product_id, vendor)
        serializer = ProductUpdateSerializer(product, data=request.data)
        serializer.is_valid(raise_exception=True)
        product = ProductService.update_product(product, serializer.validated_data)

        AuditService.log_product_action(
            request=request,
            product=product,
            action=AuditAction.PRODUCT_UPDATED,
        )

        return success_response(
            data=ProductDetailSerializer(product).data,
            message="Product updated successfully.",
            request=request,
        )

    def delete(self, request, product_id):
        vendor = request.user.vendor_profile
        product = ProductService.get_vendor_product_or_404(product_id, vendor)

        AuditService.log(
            request=request,
            action=AuditAction.PRODUCT_DELETED,
            entity_type="Product",
            entity_id=str(product.id),
            metadata={"name": product.name, "sku": product.sku},
        )

        ProductService.delete_product(product)
        return no_content_response()


class ProductImageView(APIView):
    """Vendor adds an image URL to their product after uploading to S3."""
    permission_classes = [IsVendorUser]

    def post(self, request, product_id):
        vendor = request.user.vendor_profile
        product = ProductService.get_vendor_product_or_404(product_id, vendor)
        serializer = ProductImageAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = ProductService.add_product_image(
            product=product,
            image_url=serializer.validated_data["image_url"],
            object_key=serializer.validated_data.get("object_key", ""),
            is_primary=serializer.validated_data.get("is_primary", False),
            display_order=serializer.validated_data.get("display_order", 0),
        )
        return created_response(
            data=ProductImageAddSerializer(image).data,
            message="Image added to product.",
            request=request,
        )


class ProductImageDeleteView(APIView):
    """Vendor removes an image from their product."""
    permission_classes = [IsVendorUser]

    def delete(self, request, product_id, image_id):
        vendor = request.user.vendor_profile
        product = ProductService.get_vendor_product_or_404(product_id, vendor)
        try:
            image = ProductImage.objects.get(id=image_id, product=product)
        except ProductImage.DoesNotExist:
            raise ResourceNotFound("Image not found.")
        ProductService.delete_product_image(image)
        return no_content_response()


class AdminProductListView(APIView):
    """Admin lists all products across all vendors."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = Product.objects.select_related(
            "vendor", "category"
        ).prefetch_related("product_images")

        # Filter by vendor
        vendor_id = request.query_params.get("vendor_id")
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)

        # Filter by status
        status = request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status.upper())

        # Filter by category
        category_id = request.query_params.get("category_id")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Search
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search) | \
                       queryset.filter(sku__icontains=search)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ProductListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminProductDetailView(APIView):
    """Admin views, updates, or soft-deletes any product."""
    permission_classes = [IsAdminUser]

    def get(self, request, product_id):
        product = ProductService.get_product_or_404(product_id)
        return success_response(
            data=ProductDetailSerializer(product).data,
            request=request,
        )

    def put(self, request, product_id):
        vendor = request.user.vendor_profile
        product = ProductService.get_vendor_product_or_404(product_id, vendor)
        serializer = ProductUpdateSerializer(product, data=request.data)
        serializer.is_valid(raise_exception=True)
        product = ProductService.update_product(product, serializer.validated_data)

        AuditService.log_product_action(
            request=request,
            product=product,
            action=AuditAction.PRODUCT_UPDATED,
        )

        return success_response(
            data=ProductDetailSerializer(product).data,
            message="Product updated successfully.",
            request=request,
        )

    def delete(self, request, product_id):
        vendor = request.user.vendor_profile
        product = ProductService.get_vendor_product_or_404(product_id, vendor)

        AuditService.log(
            request=request,
            action=AuditAction.PRODUCT_DELETED,
            entity_type="Product",
            entity_id=str(product.id),
            metadata={"name": product.name, "sku": product.sku},
        )

        ProductService.delete_product(product)
        return no_content_response()
    