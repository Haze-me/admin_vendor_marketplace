"""
Django admin registration for Vendor model.
"""
from django.contrib import admin
from apps.vendors.models import Vendor


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = [
        "business_name",
        "business_email",
        "status",
        "user",
        "created_at",
    ]
    list_filter = ["status"]
    search_fields = ["business_name", "business_email", "user__email"]
    readonly_fields = ["id", "slug", "approved_at", "suspended_at", "created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("id", "user", "status")}),
        ("Business Info", {"fields": ("business_name", "business_email", "phone", "address", "description", "slug")}),
        ("Timestamps", {"fields": ("approved_at", "suspended_at", "created_at", "updated_at")}),
    )