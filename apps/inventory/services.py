"""
Inventory service layer.

Key responsibility:
- All stock mutations go through this service.
- Optimistic locking on every update prevents overselling.
- Kafka inventory.updated event published after every change.
"""
import logging
from django.db import transaction
from django.utils import timezone

from apps.inventory.models import Inventory
from apps.products.models import Product
from common.exceptions import ResourceNotFound, InsufficientStock, BusinessRuleViolation
from events.producers import publish_event
from events.topics import KafkaTopics

logger = logging.getLogger(__name__)

MAX_LOCK_RETRIES = 3


def _publish_inventory_event(inventory: Inventory) -> None:
    """Publish inventory.updated Kafka event."""
    try:
        publish_event(
            topic=KafkaTopics.INVENTORY_UPDATED,
            event_type=KafkaTopics.INVENTORY_UPDATED,
            payload={
                "productId": str(inventory.product.id),
                "availableQuantity": inventory.available_quantity,
                "reservedQuantity": inventory.reserved_quantity,
                "inStock": inventory.in_stock,
            },
            key=str(inventory.product.id),
        )
    except Exception as e:
        logger.error("Failed to publish inventory.updated event: %s", e)


class InventoryService:

    @staticmethod
    def get_inventory_or_404(product_id: str) -> Inventory:
        try:
            return Inventory.objects.select_related("product").get(
                product_id=product_id
            )
        except Inventory.DoesNotExist:
            raise ResourceNotFound(
                f"Inventory record not found for product '{product_id}'."
            )

    @staticmethod
    @transaction.atomic
    def create_inventory(product: Product, available_quantity: int = 0) -> Inventory:
        if Inventory.objects.filter(product=product).exists():
            raise BusinessRuleViolation(
                "An inventory record already exists for this product."
            )
        inventory = Inventory.objects.create(
            product=product,
            available_quantity=available_quantity,
        )
        logger.info(
            "Inventory created for product %s with qty=%s",
            product.id, available_quantity,
        )
        _publish_inventory_event(inventory)
        return inventory

    @staticmethod
    @transaction.atomic
    def update_stock(product_id: str, new_quantity: int) -> Inventory:
        for attempt in range(MAX_LOCK_RETRIES):
            try:
                inventory = Inventory.objects.select_related("product").get(
                    product_id=product_id
                )
                current_version = inventory.version

                updated = Inventory.objects.filter(
                    product_id=product_id,
                    version=current_version,
                ).update(
                    available_quantity=new_quantity,
                    version=current_version + 1,
                    updated_at=timezone.now(),
                )

                if updated == 0:
                    logger.warning(
                        "Optimistic lock conflict on inventory update "
                        "for product %s (attempt %s/%s)",
                        product_id, attempt + 1, MAX_LOCK_RETRIES,
                    )
                    continue

                inventory.refresh_from_db()
                logger.info(
                    "Stock updated for product %s: new_qty=%s",
                    product_id, new_quantity,
                )
                _publish_inventory_event(inventory)
                return inventory

            except Inventory.DoesNotExist:
                raise ResourceNotFound(
                    f"Inventory record not found for product '{product_id}'."
                )

        raise BusinessRuleViolation(
            "Failed to update stock after multiple retries due to concurrent modifications. "
            "Please try again."
        )

    @staticmethod
    @transaction.atomic
    def reserve_stock(product_id: str, quantity: int) -> Inventory:
        for attempt in range(MAX_LOCK_RETRIES):
            try:
                inventory = Inventory.objects.select_related("product").get(
                    product_id=product_id
                )

                if inventory.available_quantity < quantity:
                    raise InsufficientStock(
                        f"Insufficient stock for product '{product_id}'. "
                        f"Available: {inventory.available_quantity}, Requested: {quantity}."
                    )

                current_version = inventory.version
                updated = Inventory.objects.filter(
                    product_id=product_id,
                    version=current_version,
                    available_quantity__gte=quantity,
                ).update(
                    available_quantity=inventory.available_quantity - quantity,
                    reserved_quantity=inventory.reserved_quantity + quantity,
                    version=current_version + 1,
                    updated_at=timezone.now(),
                )

                if updated == 0:
                    logger.warning(
                        "Optimistic lock conflict on stock reserve "
                        "for product %s (attempt %s/%s)",
                        product_id, attempt + 1, MAX_LOCK_RETRIES,
                    )
                    continue

                inventory.refresh_from_db()
                logger.info(
                    "Stock reserved for product %s: qty=%s",
                    product_id, quantity,
                )
                _publish_inventory_event(inventory)
                return inventory

            except Inventory.DoesNotExist:
                raise ResourceNotFound(
                    f"Inventory record not found for product '{product_id}'."
                )

        raise BusinessRuleViolation(
            "Failed to reserve stock after multiple retries. Please try again."
        )

    @staticmethod
    @transaction.atomic
    def reserve_stock_bulk(items: list) -> list:
        """
        Reserve stock for multiple products atomically — all or nothing.
        Used by the internal checkout endpoint. If any item fails,
        the entire transaction rolls back via Django's @transaction.atomic,
        so no partial reservation is ever left behind.

        Args:
            items: [{"product_id": "uuid", "quantity": 2}, ...]

        Returns:
            List of {"productId": ..., "reservedQuantity": ...} for confirmation.
        """
        reserved_items = []
        for item in items:
            inventory = InventoryService.reserve_stock(
                product_id=str(item["product_id"]),
                quantity=int(item["quantity"]),
            )
            reserved_items.append({
                "productId": str(inventory.product.id),
                "reservedQuantity": int(item["quantity"]),
            })
        return reserved_items

    @staticmethod
    @transaction.atomic
    def release_stock(product_id: str, quantity: int) -> Inventory:
        for attempt in range(MAX_LOCK_RETRIES):
            try:
                inventory = Inventory.objects.select_related("product").get(
                    product_id=product_id
                )

                if inventory.reserved_quantity < quantity:
                    raise BusinessRuleViolation(
                        f"Cannot release {quantity} units for product '{product_id}' — "
                        f"only {inventory.reserved_quantity} are reserved."
                    )

                current_version = inventory.version
                updated = Inventory.objects.filter(
                    product_id=product_id,
                    version=current_version,
                ).update(
                    available_quantity=inventory.available_quantity + quantity,
                    reserved_quantity=inventory.reserved_quantity - quantity,
                    version=current_version + 1,
                    updated_at=timezone.now(),
                )

                if updated == 0:
                    continue

                inventory.refresh_from_db()
                logger.info(
                    "Stock released for product %s: qty=%s",
                    product_id, quantity,
                )
                _publish_inventory_event(inventory)
                return inventory

            except Inventory.DoesNotExist:
                raise ResourceNotFound(
                    f"Inventory record not found for product '{product_id}'."
                )

        raise BusinessRuleViolation(
            "Failed to release stock after multiple retries. Please try again."
        )

    @staticmethod
    @transaction.atomic
    def release_stock_bulk(items: list) -> None:
        """Release stock for multiple products — used when an order is cancelled."""
        for item in items:
            InventoryService.release_stock(
                product_id=str(item["product_id"]),
                quantity=int(item["quantity"]),
            )

    @staticmethod
    @transaction.atomic
    def confirm_sale(product_id: str, quantity: int) -> Inventory:
        for attempt in range(MAX_LOCK_RETRIES):
            try:
                inventory = Inventory.objects.select_related("product").get(
                    product_id=product_id
                )

                if inventory.reserved_quantity < quantity:
                    raise BusinessRuleViolation(
                        f"Cannot confirm sale of {quantity} units for product '{product_id}' — "
                        f"only {inventory.reserved_quantity} are reserved."
                    )

                current_version = inventory.version
                updated = Inventory.objects.filter(
                    product_id=product_id,
                    version=current_version,
                ).update(
                    reserved_quantity=inventory.reserved_quantity - quantity,
                    sold_quantity=inventory.sold_quantity + quantity,
                    version=current_version + 1,
                    updated_at=timezone.now(),
                )

                if updated == 0:
                    continue

                inventory.refresh_from_db()
                logger.info(
                    "Sale confirmed for product %s: qty=%s",
                    product_id, quantity,
                )
                _publish_inventory_event(inventory)
                return inventory

            except Inventory.DoesNotExist:
                raise ResourceNotFound(
                    f"Inventory record not found for product '{product_id}'."
                )

        raise BusinessRuleViolation(
            "Failed to confirm sale after multiple retries. Please try again."
        )

    @staticmethod
    @transaction.atomic
    def confirm_sale_bulk(items: list) -> None:
        """Confirm sale for multiple products — used when payment succeeds."""
        for item in items:
            InventoryService.confirm_sale(
                product_id=str(item["product_id"]),
                quantity=int(item["quantity"]),
            )