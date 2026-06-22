"""
Development settings.
Never use in production.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ["*"]

# Disable HTTPS-only cookie flag in development
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Show SQL queries in development
LOGGING["loggers"]["django.db.backends"] = {  # noqa: F405
    "handlers": ["console"],
    "level": "WARNING",
    "propagate": False,
}

# CORS: allow all in dev
CORS_ALLOW_ALL_ORIGINS = True