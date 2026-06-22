"""
Custom User model for Admin & Vendor Service.

Design decisions:
- Single User model with a role field (ADMIN, VENDOR).
- Email is the login identifier, not username.
- UUID primary key — never expose auto-increment IDs.
- Extends AbstractBaseUser for full control over auth fields.
- PermissionsMixin adds Django's group/permission system.
- vendor_profile reverse relation is added by the Vendor model (OneToOne).
"""
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    VENDOR = "VENDOR", "Vendor"


class UserManager(BaseUserManager):
    """Custom manager: email-based auth, no username."""

    def _create_user(self, email, password, role, **extra_fields):
        if not email:
            raise ValueError("Email address is required.")
        if not role:
            raise ValueError("Role is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, role=Role.VENDOR, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, role, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, Role.ADMIN, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Central user model for Admin & Vendor Service.
    One row per human actor — either an ADMIN or a VENDOR.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "role"]),
        ]

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_vendor(self) -> bool:
        return self.role == Role.VENDOR