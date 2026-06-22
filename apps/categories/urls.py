"""
URL patterns for the categories app.
All routes mounted under /api/v1/categories/ in config/urls.py.
"""
from django.urls import path
from apps.categories.views import (
    CategoryListCreateView,
    CategoryDetailView,
)

urlpatterns = [
    path("", CategoryListCreateView.as_view(), name="category-list-create"),
    path("<uuid:category_id>/", CategoryDetailView.as_view(), name="category-detail"),
]