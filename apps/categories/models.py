"""
Category model.

Design decisions:
- Supports parent/child categories (one level of nesting is enough for electronics:
  e.g. parent=Phones, child=Smartphones).
- Soft delete via BaseModel — deleting a category never breaks existing products.
- slug for clean URLs.
"""
from django.db import models
from django.utils.text import slugify
from common.models import BaseModel


class Category(BaseModel):
    """
    Product category.
    A category can optionally have a parent (one level deep).
    Example: parent=Electronics, child=Smartphones
    """
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "categories"
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def is_parent(self) -> bool:
        return self.parent is None

    @property
    def full_path(self) -> str:
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name