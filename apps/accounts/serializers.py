"""
Serializers for accounts app.

Covers:
- Admin registration
- Vendor registration
- Login (email + password -> tokens)
- Token refresh
- Logout (blacklist refresh token)
- Change password
- User profile (read)
"""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from apps.accounts.models import User, Role


class AdminRegistrationSerializer(serializers.ModelSerializer):
    """Register a new ADMIN user. Only callable by an existing admin."""
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "password", "confirm_password"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        validate_password(attrs["password"])
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            role=Role.ADMIN,
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            is_staff=True,
        )


class VendorRegistrationSerializer(serializers.ModelSerializer):
    """
    Register a new VENDOR user account.
    This only creates the auth user — the vendor profile is created
    separately in apps.vendors once the account is approved.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "password", "confirm_password"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        validate_password(attrs["password"])
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            role=Role.VENDOR,
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )


class LoginSerializer(serializers.Serializer):
    """Authenticate with email + password. Returns JWT access + refresh tokens."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email", "").lower()
        password = attrs.get("password")

        user = authenticate(request=self.context.get("request"), email=email, password=password)

        if not user:
            raise serializers.ValidationError(
                {"non_field_errors": "Invalid email or password."}
            )
        if not user.is_active:
            raise serializers.ValidationError(
                {"non_field_errors": "This account has been deactivated."}
            )

        attrs["user"] = user
        return attrs


class TokenRefreshSerializer(serializers.Serializer):
    """Accepts a refresh token and returns a new access token."""
    refresh = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    """Blacklists the provided refresh token on logout."""
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs["refresh"]
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except TokenError as exc:
            raise serializers.ValidationError({"refresh": str(exc)})


class ChangePasswordSerializer(serializers.Serializer):
    """Authenticated user changes their own password."""
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise serializers.ValidationError(
                {"confirm_new_password": "New passwords do not match."}
            )
        validate_password(attrs["new_password"])
        return attrs

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Read-only profile of the authenticated user."""
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name", "role", "created_at"]
        read_only_fields = fields