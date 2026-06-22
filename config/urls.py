"""
Root URL configuration for Admin & Vendor Service.
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # Django admin
    path("django/admin/", admin.site.urls),

    # OpenAPI schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # API v1
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/vendors/", include("apps.vendors.urls")),
    path("api/v1/categories/", include("apps.categories.urls")),
    path("api/v1/products/", include("apps.products.urls")),
    path("api/v1/inventory/", include("apps.inventory.urls")),
    path("api/v1/images/", include("apps.images.urls")),
    path("api/v1/audit/", include("apps.audit.urls")),
]