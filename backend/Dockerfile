# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.13-slim-trixie AS builder

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /bin/

# Environment variables for uv build optimization
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/workspace/.venv

WORKDIR /workspace

# Copy package definitions and lock files
COPY pyproject.toml uv.lock* ./

# Install dependencies using cache mount for speed (wheels are used, no build-essential needed)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project

# ==========================================
# Stage 2: Runtime
# ==========================================
FROM python:3.13-slim-trixie AS runtime

WORKDIR /workspace

# Python performance and runtime environment configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/workspace/.venv/bin:$PATH"

# Install runtime dependencies and create non-privileged user
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 10001 contexthub \
    && useradd -u 10001 -g contexthub -m -s /bin/bash contexthub

# Copy virtual environment from builder stage
COPY --from=builder /workspace/.venv /workspace/.venv

# Copy project code and database migration resources
COPY --chown=contexthub:contexthub app ./app
COPY --chown=contexthub:contexthub alembic ./alembic
COPY --chown=contexthub:contexthub alembic.ini ./alembic.ini

# Set non-root execution permissions
USER contexthub

# Expose port and run server
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
