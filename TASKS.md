# ContextHub Incremental Development Roadmap (TASKS.md)

This document maps out the engineering steps to build **ContextHub** from the ground up, organized in logical, incremental development phases. Each phase builds upon the previous, ensuring a fully operational, testable platform at the end of each stage.

---

## Phase 1: Foundation & Core Ingestion Pipeline

### [x] Task 1.1: Project Initialization & Dev Environment
- [x] Initialize Python backend environment with uv (FastAPI, SQLAlchemy, Alembic).
- [x] Initialize frontend project with Next.js 16.3.0 (App Router, TypeScript, Tailwind CSS v4).
- [x] Create `docker-compose.yml` for local services: PostgreSQL with `pgvector`, Redis, MinIO, Backend, Celery, and Frontend.
- [x] Set up basic CI linting and TypeScript verification.

### [x] Task 1.2: Multi-Tenant Relational Database Setup
- [x] Create PostgreSQL schema migrations for Core Models:
  - [x] `tenants` (ID, Name, Tier, Metadata)
  - [x] `users` (ID, Email, PasswordHash, Role, TenantID)
  - [x] `workspaces` (ID, Name, IsPrivate, TenantID)
  - [x] `documents` (ID, Name, ObjectStoreKey, Status, TenantID, WorkspaceID)
- [x] Configure Async SQLAlchemy engine with thread-safe `tenant_id` context propagation.
- [x] Write integration test ensuring two users from different tenants cannot read/write each other's data.

### [x] Task 1.3: Authentication & Logical Scope Middleware
- [x] Implement JWT-based registration and login flows inside FastAPI (with `tenant_id` claims).
- [x] Write Next.js Edge proxy checking session cookies, handling route protection (`/app/*`), and managing session state.
- [x] Implement FastAPI dependency injection helpers: `get_current_user`, `get_current_tenant`.

### [x] Task 1.4: Base Ingestion & Object Storage
- [x] Set up file upload API in FastAPI. Store raw payloads in S3/MinIO using structured paths: `s3://contexthub/<tenant_id>/<workspace_id>/<doc_id>/raw.<ext>`.
- [x] Setup Celery worker system with Redis as the message broker.
- [x] Implement a basic document parser worker that extracts plain text from `.txt`, `.md`, and `.pdf` files.
- [x] Implement database status updates (`PENDING` -> `PARSING` -> `ACTIVE` or `ERROR`).

---

## Phase 2: Custom Hybrid RAG & Grounded Chat Engine

### [x] Task 2.1: Semantic Text Chunking & Vector Creation
- [x] Build a custom Python chunking library supporting Markdown/Plain-Text formatting (splitting on header blocks, paragraphs, lists) with token counting.
- [x] Connect the parsing Celery worker to the Gemini Embedding API (`gemini-embedding-001`).
- [x] Create `document_chunks` table in Postgres supporting `vector` (768 dimensions) and `tsvector` columns.
- [x] Add GIST/GIN full-text indices and HNSW vector indices on `document_chunks`.

### [x] Task 2.2: Hybrid Retrieval & Reciprocal Rank Fusion (RRF)
- [x] Implement raw SQL or SQLAlchemy raw expressions performing dense search:
  ```sql
  SELECT id, content, (embedding <=> :query_vector) AS cosine_distance 
  FROM document_chunks WHERE tenant_id = :tenant_id
  ```
- [x] Implement sparse search:
  ```sql
  SELECT id, content, ts_rank_cd(search_vector, to_tsquery(:query_text)) AS text_rank 
  FROM document_chunks WHERE tenant_id = :tenant_id
  ```
- [x] Build a Python module implementing Reciprocal Rank Fusion (RRF) combining dense search rank and sparse search rank.
- [x] Set up Cohere Rerank API integration (and zero-cost ContextBoostReranker) to refine candidate chunks.

### [x] Task 2.3: Grounded Conversational AI Stream (Complete)
- [x] Implement streaming API router `/api/v1/chat/stream` in FastAPI.
- [x] Draft system prompt instructing Gemini to rely exclusively on context and output citations.
- [x] Write Python parser extracting chunk citations from LLM responses, retrieving referenced chunk metadata, and building a structured JSON response payload alongside the text stream.
- [x] Build a streaming chat UI in Next.js displaying citations with hoverable tooltip metadata (Document Name, Excerpt).

---

## Phase 3: Knowledge Organization & Row-Level Authorization

### [/] Task 3.1: Spaces & Collections Dashboard
- [x] Design the workspaces dashboard UI using Tailwind CSS v4 and Radix UI elements.
- [x] Implement API endpoints to Create, Update, and Delete Workspaces.

- [ ] Implement API endpoints to Create, Update, and Delete Workspaces.
- [ ] Implement Workspace Collections (logical folders inside Workspaces).
- [ ] Add document transfer logic (moving documents between Workspaces).

### [ ] Task 3.2: Granular RBAC Permissions
- [ ] Add RBAC validation layers: checks for `WorkspaceMember` vs. `WorkspaceAdmin` vs. `WorkspaceViewer`.
- [ ] Extend DB queries in the retrieval pipeline to filter chunks by workspaces the user explicitly has access to.
- [ ] Write validation testing cases validating access limitations across workspaces.

### [ ] Task 3.3: Collaborative Workspace Interactions
- [ ] Implement workspace activity feeds (log actions: doc uploaded, workspace settings changed).
- [ ] Build a comment threading UI allowing users to post notes on specific documents or chunks.
- [ ] Set up WebSockets using FastAPI and Redis Pub/Sub to broadcast active viewers in a Workspace.

---

## Phase 4: AI Agents & Automated Workflows

### [ ] Task 4.1: Agent Loop & Custom Tool Registry
- [ ] Implement a ReAct agent runner loop in Python that executes LLM tool calls.
- [ ] Create a local registry for agent tools (e.g., `web_search`, `document_lookup`, `database_query`).
- [ ] Build a sandboxed Python execution context (or microservice) to run custom Javascript or Python utility scripts securely.

### [ ] Task 4.2: Workflow Automation Engine
- [ ] Implement event triggers (e.g., `DOCUMENT_INGESTED`, `CHUNKING_COMPLETE`, `DAILY_CRON`).
- [ ] Create a flow builder UI in Next.js to link triggers to actions (e.g., "When document is uploaded to Space A -> Classify topics -> Generate summary report").
- [ ] Set up Celery beat for handling scheduled periodic workflows.

---

## Phase 5: Enterprise Security, Admin & Compliance

### [ ] Task 5.1: SAML 2.0 & OIDC SSO Integration
- [ ] Integrate SAML authentication handlers allowing connection to OKTA or Azure Active Directory.
- [ ] Build tenant admin screens to configure Custom SAML parameters (metadata URLs, certificate uploads).

### [ ] Task 5.2: Data Loss Prevention (DLP) Regex Scanner
- [ ] Implement a pre-ingest PII detection processor parsing chunks for credit cards, SSNs, and common credentials.
- [ ] Add workspace DLP settings letting tenant admins toggle masking (redacting sensitive content) or rejection (refusing to ingest the document).

### [ ] Task 5.3: Immutable Audit Trails
- [ ] Build a global service logging mutating database operations to the `audit_logs` table.
- [ ] Create a read-only admin log explorer UI in Next.js.
- [ ] Add CSV export for compliance audits.

---

## Phase 6: Observability, Hardening & Scaling

### [ ] Task 6.1: Cost & Usage Analytics
- [ ] Log token counts (input/output) and embedding count metrics in PostgreSQL.
- [ ] Create usage dashboards visualizing LLM costs, vector counts, and storage size by tenant.
- [ ] Implement soft limits and hard quotas preventing tenants from exceeding their plan thresholds.

### [ ] Task 6.2: Semantic Caching & Rate Limiting
- [ ] Set up semantic caching in Redis (checking if similar questions were answered recently to bypass LLM calls).
- [ ] Implement API rate limiting using Redis token buckets partitioned by user ID and API key.

### [ ] Task 6.3: Kubernetes & Helm Manifests
- [ ] Containerize services using optimized multi-stage Dockerfiles.
- [ ] Write Helm charts for kubernetes deployments (defining API deployments, worker stateful sets, horizontal pod autoscalers).
