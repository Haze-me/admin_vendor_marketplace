"""
Vendor model.

Design decisions:
- OneToOne link to User (the auth account).
- Status flow: PENDING -> APPROVED -> SUSPENDED (and back to APPROVED).
- Soft delete inherited from BaseModel — vendor records are never hard-deleted.
- slug field for clean URLs and SEO.
"""
from django.db import models
from django.utils.text import slugify
from common.models import BaseModel
from common.validators import validate_phone_number, validate_business_name


class VendorStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    SUSPENDED = "SUSPENDED", "Suspended"


class Vendor(BaseModel):
    """
    Vendor profile linked to a User account.
    Created by the vendor themselves after registering.
    Activated only after admin approval.
    """
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="vendor_profile",
    )
    business_name = models.CharField(
        max_length=255,
        validators=[validate_business_name],
    )
    business_email = models.EmailField(unique=True)
    phone = models.CharField(
        max_length=20,
        validators=[validate_phone_number],
    )
    address = models.TextField(blank=True)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=VendorStatus.choices,
        default=VendorStatus.PENDING,
        db_index=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vendors"
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["business_email"]),
        ]

    def __str__(self):
        return f"{self.business_name} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.business_name)
        super().save(*args, **kwargs)

    @property
    def is_approved(self) -> bool:
        return self.status == VendorStatus.APPROVED

    @property
    def is_pending(self) -> bool:
        return self.status == VendorStatus.PENDING

    @property
    def is_suspended(self) -> bool:
        return self.status == VendorStatus.SUSPENDED