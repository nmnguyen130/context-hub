# ContextHub - Enterprise AI Knowledge Platform

**ContextHub** is an Enterprise Multi-Tenant AI Knowledge Platform built with a custom hybrid RAG (Retrieval-Augmented Generation) pipeline, strict logical multi-tenancy, and a modern Next.js 16.3.0 web interface.

---

## 🌟 Tech Stack & Architecture

- **Frontend:** Next.js 16.3.0 (App Router, Turbopack), React 19, TypeScript, Tailwind CSS v4, Zustand, TanStack Query.
- **Backend:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), Alembic.
- **Databases & Storage:** PostgreSQL 18 with `pgvector` and Row Level Security (RLS), Redis 8, MinIO S3 Object Storage.
- **Async Workers & Event Bus:** Celery background worker, Outbox Pattern event relay.
- **AI Orchestration:** Custom Python RAG pipeline (Dense + Sparse Hybrid Search, RRF Fusion, Cohere Reranking, Gemini LLM Synthesis).

---

## 🚀 Quick Start (Full-Stack Docker Compose)

Boot up the complete ContextHub stack (7 containers: Database, Redis, MinIO, Backend, Celery Worker, Outbox Relay, Frontend) with a single command:

### Step 1: Start All Services
From the project root directory (`context-hub/`), run:
```bash
docker compose up -d
```

### Step 2: Run Database Migrations
Run the initial Alembic schema and Row Level Security (RLS) migrations:
```bash
docker compose exec backend alembic upgrade head
```

### Step 3: Access Application & Services
- 🌐 **Web Interface:** [http://localhost:3000](http://localhost:3000)
- ⚙️ **Backend API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- 📦 **MinIO S3 Storage Console:** [http://localhost:9001](http://localhost:9001) *(Credentials: `minioadmin` / `minioadmin`)*

---

## 📁 Repository Layout

```text
context-hub/
├── backend/                  # FastAPI Application Monolith (Python 3.13)
│   ├── app/                  # API endpoints, core config, modules, worker tasks
│   ├── alembic/              # Database schema & RLS migrations
│   ├── Dockerfile            # Python uv multi-stage container
│   ├── docker-compose.yml    # Backend-isolated docker stack
│   └── README.md             # Backend detailed documentation
├── frontend/                 # Next.js Application (React 19, Tailwind v4)
│   ├── src/                  # App router, components, features, store, proxy.ts
│   ├── Dockerfile            # Next.js standalone container
│   └── README.md             # Frontend detailed documentation
├── docker-compose.yml        # Root full-stack orchestrator
├── .env                      # System environment configuration
└── TASKS.md                  # Development roadmap & checklists
```

---

## 🛡️ Multi-Tenancy & Security Guidelines

1. **Logical Tenant Partitioning**: Every database table is partitioned with `tenant_id` and enforced with PostgreSQL Row Level Security (RLS).
2. **HTTPOnly Secure Session Cookies**: Authentication tokens are stored strictly in HTTPOnly secure cookies via Edge Middleware (`proxy.ts`).
3. **Restricted DB Connection Pools**: FastAPI uses `POSTGRES_APP_USER` (`contexthub_app`) with restricted CRUD privileges for runtime operations, while Alembic uses `POSTGRES_OWNER_USER` (`postgres`) for DDL schema migrations.

---

## 📖 Submodule Documentation

- For backend setup, unit testing, and RAG evaluation: [backend/README.md](file:///d:/Coding/Project/context-hub/backend/README.md)
- For frontend component architecture and Zustand store slicing: [frontend/README.md](file:///d:/Coding/Project/context-hub/frontend/README.md)
