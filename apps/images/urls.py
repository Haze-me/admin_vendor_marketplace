"""
URL patterns for the images app.
All routes mounted under /api/v1/images/ in config/urls.py.
"""
from django.urls import path
from apps.images.views import PresignedUploadUrlView

urlpatterns = [
    path("presigned-url/", PresignedUploadUrlView.as_view(), name="presigned-upload-url"),
]