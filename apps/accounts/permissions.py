"""
Role-based permission classes.

IsAdminUser     — only ADMIN role can access
IsVendorUser    — only VENDOR role can access
IsAdminOrVendor — either role
"""
from rest_framework.permissions import BasePermission
from apps.accounts.models import Role


class IsAdminUser(BasePermission):
    """Only authenticated users with ADMIN role."""
    message = "You must be an administrator to perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.ADMIN
        )


class IsVendorUser(BasePermission):
    """Only authenticated users with VENDOR role."""
    message = "You must be a vendor to perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.VENDOR
        )


class IsAdminOrVendor(BasePermission):
    """Authenticated users with either ADMIN or VENDOR role."""
    message = "Authentication required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in (Role.ADMIN, Role.VENDOR)
        )