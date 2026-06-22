"""
Base model classes used across all apps.

Rules:
- All models use UUID primary keys (never expose auto-increment IDs externally).
- All models have created_at / updated_at timestamps.
- Entities that can be referenced by other services use soft delete.
"""
import uuid
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base providing created_at and updated_at fields.
    All models in this project inherit from this.
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """
    Abstract base providing a UUID primary key.
    Prevents sequential ID enumeration attacks.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    class Meta:
        abstract = True


class SoftDeleteManager(models.Manager):
    """
    Default manager that filters out soft-deleted records.
    Use Model.all_objects to access deleted records.
    """
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllObjectsManager(models.Manager):
    """Manager that returns ALL records including soft-deleted ones."""
    def get_queryset(self):
        return super().get_queryset()


class SoftDeleteModel(models.Model):
    """
    Abstract base providing soft delete capability.
    Records are never hard-deleted; deleted_at is set instead.
    Required for entities referenced by other services (products, vendors, categories).
    """
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def delete(self, using=None, keep_parents=False):
        """Soft delete: set deleted_at instead of removing the row."""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        """Hard delete: permanently remove the row. Use with extreme caution."""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Restore a soft-deleted record."""
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])


class BaseModel(UUIDModel, TimeStampedModel, SoftDeleteModel):
    """
    Full base model: UUID pk + timestamps + soft delete.
    Use this for all domain entities.
    """
    class Meta:
        abstract = True


class BaseModelNoSoftDelete(UUIDModel, TimeStampedModel):
    """
    Base model without soft delete.
    Use for entities that are safe to hard-delete (e.g. audit logs — never deleted).
    """
    class Meta:
        abstract = True