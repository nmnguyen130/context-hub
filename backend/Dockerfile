# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.13-slim-trixie AS builder

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Sync dependencies using bind mounts instead of copying them into the builder filesystem.
# This maximizes Docker build cache efficiency.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# ==========================================
# Stage 2: Runtime
# ==========================================
FROM python:3.13-slim-trixie AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Copy the synced production virtual environment containing only dependencies
COPY --from=builder /app/.venv /app/.venv

# Copy project codebase
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
