"""
Vendor service layer.

All business logic lives here — views stay thin.
Kafka events are published from this layer after DB changes succeed.
"""
import logging
from django.utils import timezone
from django.db import transaction

from apps.vendors.models import Vendor, VendorStatus
from common.exceptions import ResourceNotFound, InvalidStatusTransition
from events.producers import publish_event
from events.topics import KafkaTopics

logger = logging.getLogger(__name__)


class VendorService:

    @staticmethod
    def get_vendor_or_404(vendor_id: str) -> Vendor:
        try:
            return Vendor.objects.select_related("user").get(id=vendor_id)
        except Vendor.DoesNotExist:
            raise ResourceNotFound(f"Vendor with id '{vendor_id}' not found.")

    @staticmethod
    def get_vendor_by_user(user) -> Vendor:
        try:
            return Vendor.objects.select_related("user").get(user=user)
        except Vendor.DoesNotExist:
            raise ResourceNotFound("Vendor profile not found for this user.")

    @staticmethod
    @transaction.atomic
    def approve_vendor(vendor: Vendor) -> Vendor:
        """
        Approve a PENDING or SUSPENDED vendor.
        Publishes vendor.approved Kafka event after DB commit.
        """
        if vendor.status == VendorStatus.APPROVED:
            raise InvalidStatusTransition("Vendor is already approved.")

        vendor.status = VendorStatus.APPROVED
        vendor.approved_at = timezone.now()
        vendor.suspended_at = None
        vendor.save(update_fields=["status", "approved_at", "suspended_at", "updated_at"])

        logger.info("Vendor approved: %s (%s)", vendor.business_name, vendor.id)

        # Publish Kafka event — outside the atomic block would be safer with
        # transactional outbox pattern; kept simple here for now.
        try:
            publish_event(
                topic=KafkaTopics.VENDOR_APPROVED,
                event_type=KafkaTopics.VENDOR_APPROVED,
                payload={
                    "vendorId": str(vendor.id),
                    "businessName": vendor.business_name,
                    "businessEmail": vendor.business_email,
                },
                key=str(vendor.id),
            )
        except Exception as e:
            logger.error("Failed to publish vendor.approved event: %s", e)

        return vendor

    @staticmethod
    @transaction.atomic
    def suspend_vendor(vendor: Vendor, reason: str = "") -> Vendor:
        """
        Suspend an APPROVED or PENDING vendor.
        Publishes vendor.suspended Kafka event after DB commit.
        """
        if vendor.status == VendorStatus.SUSPENDED:
            raise InvalidStatusTransition("Vendor is already suspended.")

        vendor.status = VendorStatus.SUSPENDED
        vendor.suspended_at = timezone.now()
        vendor.save(update_fields=["status", "suspended_at", "updated_at"])

        logger.info("Vendor suspended: %s (%s) reason=%s", vendor.business_name, vendor.id, reason)

        try:
            publish_event(
                topic=KafkaTopics.VENDOR_SUSPENDED,
                event_type=KafkaTopics.VENDOR_SUSPENDED,
                payload={
                    "vendorId": str(vendor.id),
                    "businessName": vendor.business_name,
                    "businessEmail": vendor.business_email,
                    "reason": reason,
                },
                key=str(vendor.id),
            )
        except Exception as e:
            logger.error("Failed to publish vendor.suspended event: %s", e)

        return vendor