# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies into a prefix directory
# We install into /install so we can copy only that folder into the final image
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Stage 2: Final (Distroless) ───────────────────────────────────────────────
# gcr.io/distroless/python3-debian12 has Python but no shell or package manager
FROM gcr.io/distroless/python3-debian12

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source code
COPY . .

# Collect static files (only works if SECRET_KEY is set at build time or you use --noinput with dummy key)
# Note: Static files should be served by S3/CloudFront in production — see Phase 8.
# This step is here for completeness.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

EXPOSE 8000

# Gunicorn is the entrypoint — no shell needed since distroless uses exec form
# Adjust 'config.wsgi:application' to match your actual wsgi module path
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]