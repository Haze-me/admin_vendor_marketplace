"""
URL patterns for the vendors app.
All routes mounted under /api/v1/vendors/ in config/urls.py.
"""
from django.urls import path
from apps.vendors.views import (
    VendorProfileView,
    AdminVendorListView,
    AdminVendorDetailView,
    AdminVendorStatusView,
)

urlpatterns = [
    # Vendor manages own profile
    path("profile/", VendorProfileView.as_view(), name="vendor-profile"),

    # Admin endpoints
    path("", AdminVendorListView.as_view(), name="admin-vendor-list"),
    path("<uuid:vendor_id>/", AdminVendorDetailView.as_view(), name="admin-vendor-detail"),
    path("<uuid:vendor_id>/status/", AdminVendorStatusView.as_view(), name="admin-vendor-status"),
]