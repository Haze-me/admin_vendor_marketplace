"""
Production settings.
All sensitive values must come from environment variables — never hard-coded.
"""
from .base import *  # noqa: F401, F403
from decouple import config

DEBUG = False

# Security hardening
SECURE_HSTS_SECONDS = 31536000          # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True              # Force all HTTP -> HTTPS
SESSION_COOKIE_SECURE = True            # Cookie only sent over HTTPS
CSRF_COOKIE_SECURE = True               # CSRF cookie only over HTTPS
SECURE_BROWSER_XSS_FILTER = True        # XSS protection header
SECURE_CONTENT_TYPE_NOSNIFF = True      # Prevent MIME sniffing
X_FRAME_OPTIONS = "DENY"               # Prevent clickjacking

# Static files
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"