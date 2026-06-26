"""
Django admin registration for Vendor model.
"""
from django.contrib import admin
from django.contrib import messages
from apps.vendors.models import Vendor
from apps.vendors.services import VendorService
from common.exceptions import InvalidStatusTransition


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
    actions = ["approve_vendors", "suspend_vendors"]

    fieldsets = (
        (None, {"fields": ("id", "user", "status")}),
        ("Business Info", {"fields": ("business_name", "business_email", "phone", "address", "description", "slug")}),
        ("Timestamps", {"fields": ("approved_at", "suspended_at", "created_at", "updated_at")}),
    )

    @admin.action(description="Approve selected vendors")
    def approve_vendors(self, request, queryset):
        ok, skipped = 0, 0
        for vendor in queryset:
            try:
                VendorService.approve_vendor(vendor)
                ok += 1
            except InvalidStatusTransition:
                skipped += 1
        if ok:
            self.message_user(request, f"{ok} vendor(s) approved.", messages.SUCCESS)
        if skipped:
            self.message_user(request, f"{skipped} vendor(s) skipped (already approved).", messages.WARNING)

    @admin.action(description="Suspend selected vendors")
    def suspend_vendors(self, request, queryset):
        ok, skipped = 0, 0
        for vendor in queryset:
            try:
                VendorService.suspend_vendor(vendor)
                ok += 1
            except InvalidStatusTransition:
                skipped += 1
        if ok:
            self.message_user(request, f"{ok} vendor(s) suspended.", messages.SUCCESS)
        if skipped:
            self.message_user(request, f"{skipped} vendor(s) skipped (already suspended).", messages.WARNING)