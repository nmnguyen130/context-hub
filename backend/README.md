# ContextHub Backend Foundation

This is the FastAPI backend monolith for **ContextHub** - an Enterprise AI Knowledge Platform.

It is built with **Python 3.13**, **FastAPI**, **SQLAlchemy 2.0 (Async)**, and **Alembic**. It uses PostgreSQL 18 with `pgvector` for relational and vector metadata storage, and Redis for caching and Celery queues.

---

## 1. Quick Start Guide (Using Docker)

If you have Docker installed, you can boot up the entire backend stack (Database, Redis, API, and Celery Worker) with a single command.

### Step 1: Install Docker
- **Windows:** Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/). Make sure **WSL 2** is enabled during installation.
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
- **FastAPI API Gateway** at `http://localhost:8000` (Docs at `http://localhost:8000/api/v1/docs`)
- **Celery Worker** (running in the background)

### Step 3: Run Database Migrations
Once the containers are healthy, run the database migrations inside the API container:
```bash
docker compose exec api alembic upgrade head
```

### Step 4: Run Integration Tests
To run the test suite and verify multi-tenant isolation within the Docker environment:
```bash
docker compose exec api pytest -p no:cacheprovider
```

---

## 2. Local Development Guide (Without Docker for Python)

If you want to run the Python server locally on your host machine while using Docker only for backing services (Database and Redis), follow this process.

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
You only need PostgreSQL and Redis containers. Run:
```bash
docker compose up -d db redis
```

### Step 3: Set Up Local Environment Variables
Make sure your `.env` matches your host configuration. Since PostgreSQL and Redis are bound to `localhost` on ports `5432` and `6379`, your `.env` should look like:
```env
ENVIRONMENT=development

# Secrets & Authentication
JWT_SECRET=your-super-secure-jwt-secret-key-placeholder-32-bytes-min

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure-db-password-placeholder
POSTGRES_DB=contexthub

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Step 4: Run database migrations
To generate and execute Alembic migrations on your local system:
```bash
# 1. Generate the initial migration revision
uv run alembic revision --autogenerate -m "initial_schema"

# 2. Run the migration to apply changes to database
uv run alembic upgrade head
```

### Step 5: Start FastAPI Server
Start the Uvicorn live-reload server:
```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Visit the interactive Swagger UI documentation at: `http://127.0.0.1:8000/api/v1/docs`.

---

## 3. Project Architecture & Standards

- **Logical Multi-Tenancy**: Built with logical tenant isolation at the database level.
  - Read/Write/Delete operations are filtered automatically based on the active tenant context.
  - Insert operations automatically populate tenant relations.
- **Async Execution**: Powered by `asyncio` using async database drivers (`asyncpg` for PostgreSQL) and async Redis clients.
- **Domain-Driven Directory Structure**: Business domains are separated into self-contained modules under `app/modules/` (e.g., `auth`, `tenant`, `documents`).
- **Timezone Standardization**: All timestamps are standardized to UTC and configured as timezone-aware (`TIMESTAMPTZ`) to ensure consistency across systems.

---

## 4. PEP 8 Linting & Formatting

We use **Ruff** for extremely fast PEP 8 code linting and formatting.

### 4.1 Running inside Docker (Recommended)
Since Ruff is installed in the container's virtual environment, you can run it directly:

```bash
# 1. Format code layout and spacing (PEP 8)
docker compose exec api ruff format --no-cache app tests

# 2. Sort imports and fix basic lint issues
docker compose exec api ruff check --select I --fix --no-cache app tests
```

### 4.2 Running locally (Without Docker)
If you are developing locally with `uv`:

```bash
# 1. Format code layout
uv run ruff format app tests

# 2. Sort imports and lint
uv run ruff check --select I --fix app tests
```

