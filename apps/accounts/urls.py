"""
URL patterns for the accounts app.
All routes are mounted under /api/v1/auth/ in config/urls.py.
"""
from django.urls import path
from apps.accounts.views import (
    AdminRegisterView,
    VendorRegisterView,
    LoginView,
    TokenRefreshView,
    LogoutView,
    ChangePasswordView,
    MeView,
)

urlpatterns = [
    path("admin/register/", AdminRegisterView.as_view(), name="admin-register"),
    path("vendor/register/", VendorRegisterView.as_view(), name="vendor-register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("me/", MeView.as_view(), name="me"),
]