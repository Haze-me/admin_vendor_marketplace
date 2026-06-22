"""
Django admin registration for Product and ProductImage models.
"""
from django.contrib import admin
from apps.products.models import Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    readonly_fields = ["id", "created_at"]
    fields = ["image_url", "is_primary", "display_order"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "sku", "vendor", "category", "price", "status", "created_at"]
    list_filter = ["status", "category", "vendor"]
    search_fields = ["name", "sku", "brand"]
    readonly_fields = ["id", "slug", "created_at", "updated_at"]
    ordering = ["-created_at"]
    inlines = [ProductImageInline]

    fieldsets = (
        (None, {"fields": ("id", "vendor", "category", "status")}),
        ("Product Info", {"fields": ("name", "description", "brand", "sku", "price", "slug")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ["product", "is_primary", "display_order", "created_at"]
    list_filter = ["is_primary"]
    search_fields = ["product__name"]
    readonly_fields = ["id", "created_at"]