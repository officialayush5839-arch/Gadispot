# ==============================================================================
# Gadispot Backend Multi-Stage Production Dockerfile
# Base: python:3.12-slim | Non-root User: gadispot (UID 1000)
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Dependency Builder
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install build dependencies required for compiling C-extensions and wheels
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency specifications for layer caching
COPY pyproject.toml requirements.txt ./

# Install wheels into a local prefix /install for clean transfer
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# ------------------------------------------------------------------------------
# Stage 2: Final Production Runtime Image
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/app"

# Install curl for health probe checks and libpq5 for PostgreSQL client support
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Create dedicated non-root group and user (UID/GID 1000)
RUN groupadd -g 1000 gadispot && \
    useradd -u 1000 -g gadispot -s /bin/bash -m gadispot

# Copy pre-built Python dependencies from builder stage
COPY --from=builder /install /install

# Set working directory
WORKDIR /app

# Copy application source code, Alembic config, and migration versions
COPY --chown=gadispot:gadispot alembic.ini ./
COPY --chown=gadispot:gadispot alembic ./alembic
COPY --chown=gadispot:gadispot app ./app

# Enforce non-root execution
USER gadispot

# Expose standard API port
EXPOSE 8000

# Container healthcheck verifying readiness probe
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

# Production ASGI server launch command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
