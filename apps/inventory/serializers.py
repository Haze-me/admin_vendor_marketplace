"""
Serializers for inventory app.
"""
from rest_framework import serializers
from apps.inventory.models import Inventory


class InventoryDetailSerializer(serializers.ModelSerializer):
    """Full inventory detail."""
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    total_stock = serializers.IntegerField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Inventory
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "available_quantity",
            "reserved_quantity",
            "sold_quantity",
            "total_stock",
            "in_stock",
            "version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class InventoryCreateSerializer(serializers.ModelSerializer):
    """
    Create an inventory record for a product.
    Called automatically when a product is created.
    Can also be called manually by vendor or admin.
    """
    class Meta:
        model = Inventory
        fields = ["product", "available_quantity"]

    def validate_product(self, value):
        if Inventory.objects.filter(product=value).exists():
            raise serializers.ValidationError(
                "An inventory record already exists for this product."
            )
        return value

    def validate_available_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Available quantity cannot be negative."
            )
        return value


class InventoryUpdateSerializer(serializers.Serializer):
    """
    Vendor or admin updates stock quantity.
    Only available_quantity is directly settable.
    reserved_quantity is managed by the order flow.
    """
    available_quantity = serializers.IntegerField(min_value=0)
    reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Reason for stock adjustment (stored in audit log).",
    )


class StockReservationRequestSerializer(serializers.Serializer):
    """
    Internal request body for reserving stock during Commerce Service checkout.
    Accepts a list of {product_id, quantity} pairs — the full cart contents.
    All-or-nothing: if ANY item has insufficient stock, the entire
    reservation fails and nothing is reserved.
    """
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text="List of {product_id: uuid, quantity: int}",
    )

    def validate_items(self, value):
        for item in value:
            if "product_id" not in item or "quantity" not in item:
                raise serializers.ValidationError(
                    "Each item must have 'product_id' and 'quantity'."
                )
            try:
                quantity = int(item["quantity"])
            except (ValueError, TypeError):
                raise serializers.ValidationError("'quantity' must be an integer.")
            if quantity < 1:
                raise serializers.ValidationError("'quantity' must be at least 1.")
        return value


class StockReservationResponseSerializer(serializers.Serializer):
    """Response shape for a successful stock reservation."""
    reservationId = serializers.CharField()
    reservedItems = serializers.ListField(child=serializers.DictField())


class StockReleaseRequestSerializer(serializers.Serializer):
    """
    Internal request body for releasing previously reserved stock
    when an order is cancelled or payment fails.
    """
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text="List of {product_id: uuid, quantity: int}",
    )