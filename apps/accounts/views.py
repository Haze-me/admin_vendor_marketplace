"""
Accounts views.

Endpoints:
  POST /api/v1/auth/admin/register    -> register admin (admin only)
  POST /api/v1/auth/vendor/register   -> register vendor (public)
  POST /api/v1/auth/login             -> login (returns JWT tokens)
  POST /api/v1/auth/token/refresh     -> refresh access token
  POST /api/v1/auth/logout            -> blacklist refresh token
  POST /api/v1/auth/change-password   -> change own password
  GET  /api/v1/auth/me                -> current user profile
"""
import logging
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.serializers import (
    AdminRegistrationSerializer,
    VendorRegistrationSerializer,
    LoginSerializer,
    LogoutSerializer,
    ChangePasswordSerializer,
    UserProfileSerializer,
    TokenRefreshSerializer,
)
from apps.accounts.permissions import IsAdminUser
from common.responses import success_response, created_response, error_response, no_content_response

logger = logging.getLogger(__name__)


def _build_token_response(user):
    """Generate JWT token pair and build the response payload."""
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "token_type": "Bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    }


class AdminRegisterView(APIView):
    """
    Register a new admin user.
    Only existing admins can create other admins.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = AdminRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info("Admin account created: %s by %s", user.email, request.user.email)
        return created_response(
            data={"id": str(user.id), "email": user.email, "role": user.role},
            message="Admin account created successfully.",
            request=request,
        )


class VendorRegisterView(APIView):
    """
    Register a new vendor user account.
    Public endpoint — no authentication required.
    The vendor profile is created separately after admin approval.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VendorRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info("Vendor account registered: %s", user.email)
        return created_response(
            data={"id": str(user.id), "email": user.email, "role": user.role},
            message="Vendor account registered. Await admin approval.",
            request=request,
        )


class LoginView(APIView):
    """
    Authenticate with email + password.
    Returns JWT access and refresh tokens.
    Works for both ADMIN and VENDOR roles.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token_data = _build_token_response(user)
        logger.info("User logged in: %s (%s)", user.email, user.role)
        return success_response(
            data=token_data,
            message="Login successful.",
            request=request,
        )


class TokenRefreshView(APIView):
    """
    Refresh an expired access token using a valid refresh token.
    Returns a new access token. The refresh token is rotated per SIMPLE_JWT settings.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refresh = RefreshToken(serializer.validated_data["refresh"])
            data = {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "token_type": "Bearer",
            }
            return success_response(data=data, message="Token refreshed.", request=request)
        except Exception:
            return error_response(
                message="Invalid or expired refresh token.",
                http_status=401,
                request=request,
            )


class LogoutView(APIView):
    """Logout by blacklisting the refresh token."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info("User logged out: %s", request.user.email)
        return no_content_response()


class ChangePasswordView(APIView):
    """Authenticated user changes their own password."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info("Password changed for user: %s", request.user.email)
        return success_response(message="Password changed successfully.", request=request)


class MeView(APIView):
    """Return the authenticated user's own profile."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return success_response(data=serializer.data, request=request)