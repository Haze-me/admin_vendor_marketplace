"""
Product service layer.

All business logic lives here.
Kafka events published after successful DB operations.
"""
import logging
from django.db import transaction

from apps.products.models import Product, ProductImage, ProductStatus
from common.exceptions import ResourceNotFound, BusinessRuleViolation
from events.producers import publish_event
from events.topics import KafkaTopics

logger = logging.getLogger(__name__)


def _build_product_payload(product: Product) -> dict:
    """Build the Kafka event payload for a product."""
    primary_image = product.primary_image
    return {
        "productId": str(product.id),
        "vendorId": str(product.vendor.id),
        "categoryId": str(product.category.id),
        "name": product.name,
        "description": product.description,
        "brand": product.brand,
        "sku": product.sku,
        "price": str(product.price),
        "status": product.status,
        "slug": product.slug,
        "primaryImageUrl": primary_image.image_url if primary_image else None,
    }


class ProductService:

    @staticmethod
    def get_product_or_404(product_id: str) -> Product:
        try:
            return Product.objects.select_related(
                "vendor", "category"
            ).prefetch_related("product_images").get(id=product_id)
        except Product.DoesNotExist:
            raise ResourceNotFound(f"Product with id '{product_id}' not found.")

    @staticmethod
    def get_vendor_product_or_404(product_id: str, vendor) -> Product:
        """Get a product that belongs to the given vendor."""
        try:
            return Product.objects.select_related(
                "vendor", "category"
            ).prefetch_related("product_images").get(id=product_id, vendor=vendor)
        except Product.DoesNotExist:
            raise ResourceNotFound(
                f"Product with id '{product_id}' not found in your store."
            )

    @staticmethod
    @transaction.atomic
    def create_product(validated_data: dict, vendor) -> Product:
        from apps.inventory.models import Inventory

        product = Product.objects.create(vendor=vendor, **validated_data)
        logger.info("Product created: %s (%s) by vendor %s", product.name, product.id, vendor.id)

        # Automatically create an inventory record with zero stock.
        # Vendor must update stock separately via PATCH /api/v1/inventory/<product_id>/
        Inventory.objects.create(product=product, available_quantity=0)
        logger.info("Inventory record auto-created for product %s with qty=0", product.id)

        try:
            publish_event(
                topic=KafkaTopics.PRODUCT_CREATED,
                event_type=KafkaTopics.PRODUCT_CREATED,
                payload=_build_product_payload(product),
                key=str(product.id),
            )
        except Exception as e:
            logger.error("Failed to publish product.created event: %s", e)

        return product

    @staticmethod
    @transaction.atomic
    def update_product(product: Product, validated_data: dict) -> Product:
        for attr, value in validated_data.items():
            setattr(product, attr, value)
        product.save()
        logger.info("Product updated: %s (%s)", product.name, product.id)

        try:
            publish_event(
                topic=KafkaTopics.PRODUCT_UPDATED,
                event_type=KafkaTopics.PRODUCT_UPDATED,
                payload=_build_product_payload(product),
                key=str(product.id),
            )
        except Exception as e:
            logger.error("Failed to publish product.updated event: %s", e)

        return product

    @staticmethod
    @transaction.atomic
    def delete_product(product: Product) -> None:
        product_id = str(product.id)
        product_name = product.name
        product.delete()  # soft delete
        logger.info("Product soft-deleted: %s (%s)", product_name, product_id)

        try:
            publish_event(
                topic=KafkaTopics.PRODUCT_DELETED,
                event_type=KafkaTopics.PRODUCT_DELETED,
                payload={"productId": product_id},
                key=product_id,
            )
        except Exception as e:
            logger.error("Failed to publish product.deleted event: %s", e)

    @staticmethod
    def add_product_image(
        product: Product,
        image_url: str,
        is_primary: bool,
        display_order: int,
        object_key: str = "",
    ) -> ProductImage:
        image = ProductImage.objects.create(
            product=product,
            image_url=image_url,
            object_key=object_key,
            is_primary=is_primary,
            display_order=display_order,
        )
        logger.info("Image added to product %s: %s", product.id, image_url)

        # Publish updated product event so catalog picks up new image
        try:
            publish_event(
                topic=KafkaTopics.PRODUCT_UPDATED,
                event_type=KafkaTopics.PRODUCT_UPDATED,
                payload=_build_product_payload(product),
                key=str(product.id),
            )
        except Exception as e:
            logger.error("Failed to publish product.updated event after image add: %s", e)

        return image

    @staticmethod
    def delete_product_image(image: ProductImage) -> None:
        from apps.images.services import S3PresignedUrlService
        product = image.product
        object_key = image.object_key
        image.delete()
        if object_key:
            S3PresignedUrlService.delete_object(object_key)
        logger.info("Image deleted from product %s", product.id)