"""
URL patterns for the inventory app.
All routes mounted under /api/v1/inventory/ in config/urls.py.
"""
from django.urls import path
from apps.inventory.views import (
    VendorInventoryView,
    AdminInventoryListView,
    AdminInventoryDetailView,
    InternalStockReserveView,
    InternalStockReleaseView,
    InternalStockConfirmView,
)

urlpatterns = [
    # Vendor endpoints
    path("<uuid:product_id>/", VendorInventoryView.as_view(), name="vendor-inventory"),

    # Admin endpoints
    path("admin/", AdminInventoryListView.as_view(), name="admin-inventory-list"),
    path("admin/<uuid:product_id>/", AdminInventoryDetailView.as_view(), name="admin-inventory-detail"),

    # Internal endpoints (called by Commerce Service)
    path("internal/reserve/", InternalStockReserveView.as_view(), name="internal-stock-reserve"),
    path("internal/release/", InternalStockReleaseView.as_view(), name="internal-stock-release"),
    path("internal/confirm/", InternalStockConfirmView.as_view(), name="internal-stock-confirm"),
]