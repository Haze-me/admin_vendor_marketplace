"""
Reusable validators shared across apps.
"""
import re
from django.core.exceptions import ValidationError


def validate_phone_number(value: str) -> None:
    """
    Validate international phone numbers.
    Accepts formats: +2348012345678, +1-234-567-8901, etc.
    """
    pattern = re.compile(r"^\+?[1-9]\d{7,14}$")
    cleaned = re.sub(r"[\s\-\(\)]", "", value)
    if not pattern.match(cleaned):
        raise ValidationError(
            "Enter a valid phone number (e.g. +2348012345678).",
            code="invalid_phone",
        )


def validate_business_name(value: str) -> None:
    """Business name must be at least 2 characters and not purely numeric."""
    if len(value.strip()) < 2:
        raise ValidationError(
            "Business name must be at least 2 characters.",
            code="invalid_business_name",
        )
    if value.strip().isdigit():
        raise ValidationError(
            "Business name cannot be purely numeric.",
            code="invalid_business_name",
        )


def validate_sku(value: str) -> None:
    """
    SKU must be alphanumeric with optional hyphens/underscores.
    Example valid: IPHONE-15-PRO-256, SKU_001
    """
    pattern = re.compile(r"^[A-Za-z0-9\-_]+$")
    if not pattern.match(value):
        raise ValidationError(
            "SKU must contain only letters, numbers, hyphens, or underscores.",
            code="invalid_sku",
        )


def validate_positive_price(value) -> None:
    """Price must be greater than zero."""
    if value <= 0:
        raise ValidationError(
            "Price must be greater than zero.",
            code="invalid_price",
        )


def validate_non_negative_quantity(value: int) -> None:
    """Quantity must be zero or greater."""
    if value < 0:
        raise ValidationError(
            "Quantity cannot be negative.",
            code="invalid_quantity",
        )