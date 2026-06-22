"""
URL patterns for the products app.
All routes mounted under /api/v1/products/ in config/urls.py.
"""
from django.urls import path
from apps.products.views import (
    ProductListCreateView,
    ProductDetailView,
    ProductImageView,
    ProductImageDeleteView,
    AdminProductListView,
    AdminProductDetailView,
)

urlpatterns = [
    # Vendor endpoints
    path("", ProductListCreateView.as_view(), name="product-list-create"),
    path("<uuid:product_id>/", ProductDetailView.as_view(), name="product-detail"),
    path("<uuid:product_id>/images/", ProductImageView.as_view(), name="product-image-add"),
    path("<uuid:product_id>/images/<uuid:image_id>/", ProductImageDeleteView.as_view(), name="product-image-delete"),

    # Admin endpoints
    path("admin/", AdminProductListView.as_view(), name="admin-product-list"),
    path("admin/<uuid:product_id>/", AdminProductDetailView.as_view(), name="admin-product-detail"),
]