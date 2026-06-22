"""
Inventory model.

Design decisions:
- One inventory record per product (OneToOne).
- available_quantity: stock ready to be sold.
- reserved_quantity: stock held for pending orders (not yet confirmed).
- sold_quantity: running total of units sold (for analytics).
- version field for optimistic locking — prevents overselling
  when two orders try to reserve the same stock simultaneously.
"""
from django.db import models
from common.models import BaseModelNoSoftDelete
from common.validators import validate_non_negative_quantity


class Inventory(BaseModelNoSoftDelete):
    """
    Stock record for a single product.
    This is the single source of truth for all stock quantities.

    Optimistic locking pattern:
    When updating, always include version in the WHERE clause:
        UPDATE inventory SET available_quantity=X, version=version+1
        WHERE id=Y AND version=Z
    If 0 rows updated -> another process changed it first -> retry.
    """
    product = models.OneToOneField(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="inventory",
    )
    available_quantity = models.PositiveIntegerField(
        default=0,
        validators=[validate_non_negative_quantity],
    )
    reserved_quantity = models.PositiveIntegerField(
        default=0,
        validators=[validate_non_negative_quantity],
    )
    sold_quantity = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "inventory"
        verbose_name = "Inventory"
        verbose_name_plural = "Inventories"

    def __str__(self):
        return (
            f"{self.product.name} | "
            f"available={self.available_quantity} "
            f"reserved={self.reserved_quantity}"
        )

    @property
    def total_stock(self) -> int:
        """Total physical stock = available + reserved."""
        return self.available_quantity + self.reserved_quantity

    @property
    def in_stock(self) -> bool:
        return self.available_quantity > 0