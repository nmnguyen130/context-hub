# ContextHub Backend Foundation

This is the FastAPI backend monolith for **ContextHub** - an Enterprise AI Knowledge Platform.

It is built with **Python 3.13**, **FastAPI**, **SQLAlchemy 2.0 (Async)**, and **Alembic**. It uses PostgreSQL 18 with `pgvector` for relational and vector metadata storage, Redis for caching, MinIO for S3 storage, and Celery + Outbox Relay for background task processing.

---

## 1. Quick Start Guide (Using Docker)

You can boot up the entire backend stack (Database, Redis, MinIO, API, Worker, and Relay) with a single command.

### Step 1: Install Docker
- **Windows:** Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/). Make sure **WSL 2** is enabled.
- **Mac:** Download and install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/).
- **Linux:** Run `curl -fsSL https://get.docker.com | sh` and ensure the docker daemon is active.

### Step 2: Build & Start Services
From the `backend/` directory, run:
```bash
# Copy settings template
cp .env.example .env

# Build and start all services in detached mode
docker compose up -d --build
```
This starts:
- **Database** at `localhost:5432` (PostgreSQL 18 with pgvector)
- **Redis** at `localhost:6379`
- **MinIO S3 Storage** at `localhost:9000` (Console at `http://localhost:9001`)
- **FastAPI API Gateway** at `http://localhost:8000` (Docs at `http://localhost:8000/docs`)
- **Celery Worker & Outbox Relay** (running in the background)

### Step 3: Run Database Migrations
Once the containers are healthy, run the database migrations inside the API container:
```bash
docker compose exec backend alembic upgrade head
```

### Step 4: Run Integration Tests
To run the test suite and verify multi-tenant isolation within the Docker environment:
```bash
docker compose exec backend pytest -p no:cacheprovider
```

---

## 2. Local Development Guide (Without Docker for Python)

If you want to run the Python server locally on your host machine while using Docker only for backing services (Database, Redis, MinIO), follow this process.

### Step 1: Install Dependencies
We use **uv** for fast package and workspace dependency management.
1. Install `uv` (if not already installed):
   - **Windows:** `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - **Mac/Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. Install project dependencies:
   ```bash
   uv sync
   ```

### Step 2: Spin Up Backing Services Only
You only need PostgreSQL, Redis, and MinIO containers. Run:
```bash
docker compose up -d db redis minio
```

### Step 3: Run Database Migrations
To execute Alembic migrations on your local system:
```bash
docker compose exec backend alembic upgrade head
```

### Step 4: Start FastAPI Server
Start the Uvicorn live-reload server:
```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Visit the interactive Swagger UI documentation at: `http://127.0.0.1:8000/docs`.

---

## 3. Project Architecture & Standards

- **Logical Multi-Tenancy**: Built with logical tenant isolation at the database level using `tenant_id` partitioning and PostgreSQL Row Level Security (RLS) policies.
- **Async Execution**: Powered by `asyncio` using async database drivers (`asyncpg` for PostgreSQL) and async Redis clients.
- **Domain-Driven Directory Structure**: Business domains are separated into self-contained modules under `app/modules/` (e.g., `auth`, `tenant`, `documents`, `audit`).
- **Custom Hybrid RAG**: Custom hybrid search pipeline incorporating dense vector search (`pgvector`), sparse full-text search (`tsvector`), Reciprocal Rank Fusion (RRF), and Cohere reranking.
- **Timezone Standardization**: All timestamps are standardized to UTC and configured as timezone-aware (`TIMESTAMPTZ`).

---

## 4. PEP 8 Linting & Formatting

We use **Ruff** for extremely fast PEP 8 code linting and formatting.

```bash
# Format code layout and spacing
docker compose exec backend ruff format --no-cache app tests

# Sort imports and fix basic lint issues
docker compose exec backend ruff check --select I --fix --no-cache app tests
```
