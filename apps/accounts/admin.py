"""
Django admin registration for the User model.
Accessible at /django-admin/ — internal use only.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "full_name", "role", "is_active", "is_staff", "created_at"]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Role & status", {"fields": ("role", "is_active", "is_staff", "is_superuser")}),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "role", "first_name", "last_name", "password1", "password2"),
        }),
    )