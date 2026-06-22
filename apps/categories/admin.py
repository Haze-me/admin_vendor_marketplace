"""
Django admin registration for Category model.
"""
from django.contrib import admin
from apps.categories.models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "is_active", "slug", "created_at"]
    list_filter = ["is_active", "parent"]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "slug", "created_at", "updated_at"]
    ordering = ["name"]

    fieldsets = (
        (None, {"fields": ("id", "name", "slug", "description")}),
        ("Hierarchy", {"fields": ("parent", "is_active")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )