"""
Kafka topic constants.
Single source of truth for all topic names across this service.
Never hard-code topic strings in producers or consumers.
"""


class KafkaTopics:
    # Product lifecycle
    PRODUCT_CREATED = "product.created"
    PRODUCT_UPDATED = "product.updated"
    PRODUCT_DELETED = "product.deleted"

    # Inventory
    INVENTORY_UPDATED = "inventory.updated"

    # Vendor lifecycle
    VENDOR_APPROVED = "vendor.approved"
    VENDOR_SUSPENDED = "vendor.suspended"

    # Order lifecycle (produced by Commerce Service — listed here for reference)
    ORDER_CREATED = "order.created"
    ORDER_COMPLETED = "order.completed"
    ORDER_CANCELLED = "order.cancelled"

    # Review lifecycle (produced by Commerce Service — listed here for reference)
    REVIEW_CREATED = "review.created"
    REVIEW_UPDATED = "review.updated"
    REVIEW_DELETED = "review.deleted"

    # Dead-letter topics — failed messages land here for manual inspection
    PRODUCT_CREATED_DLT = "product.created.DLT"
    PRODUCT_UPDATED_DLT = "product.updated.DLT"
    PRODUCT_DELETED_DLT = "product.deleted.DLT"
    INVENTORY_UPDATED_DLT = "inventory.updated.DLT"
    VENDOR_APPROVED_DLT = "vendor.approved.DLT"
    VENDOR_SUSPENDED_DLT = "vendor.suspended.DLT"
    
    CATEGORY_CREATED = "category.created"
    CATEGORY_UPDATED = "category.updated"