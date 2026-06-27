"""
Images views.

Endpoints:
  POST /api/v1/images/presigned-url/  -> generate S3 presigned upload URL (vendor only)

Upload flow:
  1. Vendor calls POST /api/v1/images/presigned-url/ with content_type and product_id.
  2. Server validates the product belongs to the vendor.
  3. Server returns { upload_url, image_url, object_key, expires_in }.
  4. Vendor PUTs the image binary directly to upload_url.
  5. Vendor calls POST /api/v1/products/<id>/images/ with { image_url, is_primary }.
  6. Server saves the image URL in the database.
"""
import logging
from rest_framework.views import APIView

from apps.images.serializers import (
    PresignedUrlRequestSerializer,
    PresignedUrlResponseSerializer,
)
from apps.images.services import S3PresignedUrlService
from apps.products.models import Product
from apps.accounts.permissions import IsVendorUser
from common.responses import success_response
from common.exceptions import ResourceNotFound, BusinessRuleViolation

logger = logging.getLogger(__name__)


class PresignedUploadUrlView(APIView):
    """
    Generate a presigned S3 URL for a vendor to upload a product image.
    The product must belong to the authenticated vendor.
    """
    permission_classes = [IsVendorUser]

    def post(self, request):
        serializer = PresignedUrlRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = str(serializer.validated_data["product_id"])
        content_type = serializer.validated_data["content_type"]
        vendor = request.user.vendor_profile

        # Verify the product belongs to this vendor
        try:
            product = Product.objects.get(id=product_id, vendor=vendor)
        except Product.DoesNotExist:
            raise ResourceNotFound(
                "Product not found or does not belong to your store."
            )

        # Vendor must be approved to upload images
        if not vendor.is_approved:
            raise BusinessRuleViolation(
                "Your vendor account must be approved before uploading images."
            )

        try:
            result = S3PresignedUrlService.generate_presigned_upload_url(
                content_type=content_type,
                product_id=product_id,
                vendor_id=str(vendor.id),
            )
        except ValueError as e:
            logger.warning(
                "Presigned URL validation error vendor=%s product=%s: %s",
                vendor.id, product_id, e,
            )
            raise BusinessRuleViolation(str(e))
        except RuntimeError as e:
            logger.error(
                "Presigned URL generation failed vendor=%s product=%s: %s",
                vendor.id, product_id, e, exc_info=True,
            )
            raise BusinessRuleViolation(str(e))

        logger.info(
            "Presigned URL issued for vendor=%s product=%s",
            vendor.id, product_id,
        )

        response_serializer = PresignedUrlResponseSerializer(result)
        return success_response(
            data=response_serializer.data,
            message=(
                "Presigned URL generated. PUT your image to upload_url, "
                "then save image_url via POST /api/v1/products/<id>/images/."
            ),
            request=request,
        )