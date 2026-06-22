"""
Audit service layer.

Usage from any view or service:
    from apps.audit.services import AuditService
    from apps.audit.models import AuditAction

    AuditService.log(
        request=request,
        action=AuditAction.PRODUCT_CREATED,
        entity_type="Product",
        entity_id=str(product.id),
        metadata={"name": product.name, "sku": product.sku},
    )

Design decisions:
- log() never raises exceptions — audit failures must not break
  the main request. Errors are logged to the application logger only.
- actor_id and actor_email are extracted from the request user.
- ip_address is extracted from the request (set by AuditMiddleware).
- This is synchronous now — Celery-ready by simply moving the
  AuditLog.objects.create() call into a task.
"""
import logging
from apps.audit.models import AuditLog, AuditAction

logger = logging.getLogger(__name__)


class AuditService:

    @staticmethod
    def log(
        request,
        action: str,
        entity_type: str = "",
        entity_id: str = "",
        metadata: dict = None,
    ) -> None:
        """
        Write an audit log entry.
        Never raises — failures are swallowed and logged.

        Args:
            request:     The DRF/Django request object.
            action:      AuditAction choice string.
            entity_type: Model name affected (e.g. 'Product').
            entity_id:   UUID of the affected record.
            metadata:    Dict of extra context (before/after, reasons, etc.).
        """
        try:
            user = getattr(request, "user", None)
            actor_id = ""
            actor_email = ""

            if user and user.is_authenticated:
                actor_id = str(user.id)
                actor_email = user.email

            ip_address = getattr(request, "audit_ip_address", None)
            user_agent = getattr(request, "audit_user_agent", "")

            AuditLog.objects.create(
                actor_id=actor_id,
                actor_email=actor_email,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                ip_address=ip_address or None,
                user_agent=user_agent,
                metadata=metadata or {},
            )
        except Exception as exc:
            # Audit failures must never break the main request flow
            logger.error(
                "Failed to write audit log | action=%s entity=%s/%s error=%s",
                action, entity_type, entity_id, exc,
            )

    @staticmethod
    def log_login(request, user) -> None:
        """Convenience method for login events."""
        AuditService.log(
            request=request,
            action=AuditAction.LOGIN,
            entity_type="User",
            entity_id=str(user.id),
            metadata={"email": user.email, "role": user.role},
        )

    @staticmethod
    def log_logout(request, user) -> None:
        """Convenience method for logout events."""
        AuditService.log(
            request=request,
            action=AuditAction.LOGOUT,
            entity_type="User",
            entity_id=str(user.id),
            metadata={"email": user.email},
        )

    @staticmethod
    def log_vendor_status_change(request, vendor, new_status: str, reason: str = "") -> None:
        """Convenience method for vendor approval/suspension."""
        action = (
            AuditAction.VENDOR_APPROVED
            if new_status == "APPROVED"
            else AuditAction.VENDOR_SUSPENDED
        )
        AuditService.log(
            request=request,
            action=action,
            entity_type="Vendor",
            entity_id=str(vendor.id),
            metadata={
                "business_name": vendor.business_name,
                "new_status": new_status,
                "reason": reason,
            },
        )

    @staticmethod
    def log_product_action(request, product, action: str) -> None:
        """Convenience method for product create/update/delete."""
        AuditService.log(
            request=request,
            action=action,
            entity_type="Product",
            entity_id=str(product.id),
            metadata={
                "name": product.name,
                "sku": product.sku,
                "status": product.status,
                "price": str(product.price),
            },
        )

    @staticmethod
    def log_inventory_update(request, inventory, old_quantity: int) -> None:
        """Convenience method for inventory updates."""
        AuditService.log(
            request=request,
            action=AuditAction.INVENTORY_UPDATED,
            entity_type="Inventory",
            entity_id=str(inventory.id),
            metadata={
                "product_id": str(inventory.product.id),
                "old_quantity": old_quantity,
                "new_quantity": inventory.available_quantity,
            },
        )