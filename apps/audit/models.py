"""
Audit log model.

Design decisions:
- Every significant action in the system is recorded here.
- Records are NEVER deleted or soft-deleted — audit logs are immutable.
- Uses BaseModelNoSoftDelete (UUID + timestamps, no soft delete).
- actor_id is stored as a plain string (not a ForeignKey) so that
  audit logs survive even if the user account is deleted.
- metadata JSONB stores before/after state for critical changes.
- entity_type + entity_id allows querying all actions on any record.
"""
from django.db import models
from common.models import BaseModelNoSoftDelete


class AuditAction(models.TextChoices):
    # Auth
    LOGIN = "LOGIN", "Login"
    LOGOUT = "LOGOUT", "Logout"
    PASSWORD_CHANGED = "PASSWORD_CHANGED", "Password Changed"

    # Vendor
    VENDOR_CREATED = "VENDOR_CREATED", "Vendor Created"
    VENDOR_UPDATED = "VENDOR_UPDATED", "Vendor Updated"
    VENDOR_APPROVED = "VENDOR_APPROVED", "Vendor Approved"
    VENDOR_SUSPENDED = "VENDOR_SUSPENDED", "Vendor Suspended"

    # Category
    CATEGORY_CREATED = "CATEGORY_CREATED", "Category Created"
    CATEGORY_UPDATED = "CATEGORY_UPDATED", "Category Updated"
    CATEGORY_DELETED = "CATEGORY_DELETED", "Category Deleted"

    # Product
    PRODUCT_CREATED = "PRODUCT_CREATED", "Product Created"
    PRODUCT_UPDATED = "PRODUCT_UPDATED", "Product Updated"
    PRODUCT_DELETED = "PRODUCT_DELETED", "Product Deleted"

    # Inventory
    INVENTORY_UPDATED = "INVENTORY_UPDATED", "Inventory Updated"

    # Image
    IMAGE_UPLOADED = "IMAGE_UPLOADED", "Image Uploaded"
    IMAGE_DELETED = "IMAGE_DELETED", "Image Deleted"


class AuditLog(BaseModelNoSoftDelete):
    """
    Immutable record of every significant action in the system.

    actor_id:    UUID of the user who performed the action (string, not FK).
    actor_email: Email at the time of action (denormalised for history).
    action:      What happened (from AuditAction choices).
    entity_type: Which model was affected (e.g. 'Product', 'Vendor').
    entity_id:   UUID of the affected record (string, not FK).
    ip_address:  Client IP address from the request.
    metadata:    JSON blob with extra context (before/after values, reasons).
    """
    actor_id = models.CharField(max_length=36, blank=True, db_index=True)
    actor_email = models.EmailField(blank=True)
    action = models.CharField(
        max_length=50,
        choices=AuditAction.choices,
        db_index=True,
    )
    entity_type = models.CharField(max_length=100, blank=True, db_index=True)
    entity_id = models.CharField(max_length=36, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "audit_logs"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor_id", "action"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self):
        return f"{self.action} by {self.actor_email} at {self.created_at}"