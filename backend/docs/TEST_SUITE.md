# ContextHub Testing Guide

This document details the configuration, execution, and architecture of the backend test suite, outlining database roles, multi-tenancy RLS isolation, and a full catalog of all 36 tests.

## Running Tests

All tests run inside the `api` container from the `backend/` directory:

```bash
# Run all tests
docker compose exec api pytest

# Run by directories
docker compose exec api pytest tests/unit
docker compose exec api pytest tests/integration
docker compose exec api pytest tests/api
```

## Testing Database and Roles Architecture

To enforce Row-Level Security (RLS) in tests, the test environment separates the migration owner role from the application query connection:

* **Superuser / Owner (postgres)**: Alembic migrations run in a subprocess under this superuser role via the `DATABASE_OWNER_URL` environment override to create tables, pgvector vector columns, HNSW indexes, tsvector FTS indexes, and RLS policies on `contexthub_test`.
* **Application / Test Client (contexthub_app)**: The pytest engine executes test queries under this non-superuser role via `DATABASE_URL` to query `contexthub_test` with active RLS enforcement.

## Session and Transaction Isolation

We use SQLAlchemy connection pooling. To prevent connection states (like `app.bypass_rls = 'true'`) from leaking across pooled connections:

1. **Transaction-Local Configuration**: `db_session` fixture uses a session-level `after_begin` event listener to set `app.bypass_rls = 'true'` at the start of every transaction for test setup.
2. **Application Guard**: `UnitOfWork` (in `app/core/uow.py`) explicitly resets `app.bypass_rls` to `'false'` at the beginning of all non-admin transactions, ensuring RLS enforcement is always active on pooled connection checkouts.

## Pytest Fixtures

* `test_engine`: Runs Alembic migrations on `contexthub_test` as database owner, then yields the engine.
* `clean_database`: Autouse fixture that truncates all tables before each test by temporarily bypassing RLS.
* `db_session`: Session helper with RLS bypassed to set up test mock data.
* `uow`: Admin-mode Unit of Work to set up test fixtures.
* `async_client`: FastAPI HTTPX AsyncClient with overridden database session pointing to `contexthub_test`.

---

## Test Catalog (36 Tests Total)

### Unit Tests (`tests/unit/`)

* **test_security_context.py**
  * `test_bcrypt_password_hashing`: Verifies password hashing, matching verification, and failure cases.
  * `test_jwt_access_and_refresh_tokens`: Verifies JWT payload claims (claims, jti, type validation) for access and refresh tokens.
  * `test_jwt_decode_type_validation`: Verifies decode raises ValueError on token type mismatches.
  * `test_request_context_propagation`: Verifies RequestContext thread-local storage propagation using context managers.

* **test_parsers_chunkers.py**
  * `test_detect_mime_type`: Verifies automatic detection of MIME types from filename extensions and fallbacks.
  * `test_plaintext_parser`: Verifies line-by-line parsing of raw text files into structured prose blocks.
  * `test_markdown_parser`: Verifies header, prose, and fenced code block extraction with metadata.
  * `test_csv_parser_and_row_batching`: Verifies CSV row batching into table blocks with `row_range` metadata and header preservation (M5).
  * `test_document_assembler_and_offsets`: Verifies unified structural chunking and incremental character offset calculations (`char_start`, `char_end`) (M4).
  * `test_dlp_mask_and_unmask_roundtrip`: Verifies DLP PII pattern scanning, token masking (`[PII_EMAIL_hash]`), and token unmasking roundtrip (M6).

* **test_chat_module.py**
  * `test_query_classifier`: Verifies query complexity classification heuristics (SIMPLE vs MODERATE vs COMPLEX).
  * `test_reciprocal_rank_fusion`: Verifies Reciprocal Rank Fusion (RRF) score merging across dense and sparse ranks.
  * `test_relevance_grader_and_empty_fallback`: Verifies Corrective RAG (CRAG) relevance scoring, thresholding, and clean empty fallback with `is_low_confidence=True` (M3).
  * `test_citation_extraction`: Verifies strict inline citation extraction `[^1]`, `[^2]` and metadata attachment.
  * `test_prompt_building_and_history`: Verifies grounded synthesis prompt construction with recent conversation history block injection (L5).
  * `test_sse_event_framing_and_schemas`: Verifies SSEEvent framing JSON serialization and ChatRequest validation.
  * `test_semantic_cache_operations`: Verifies pgvector-backed `SemanticCache` get and set operations.

* **test_celery_tasks.py**
  * `test_celery_task_registration`: Verifies Celery background task registration and name mapping (`app.worker.tasks.process_document_ingestion`).
  * `test_process_ingestion_task_execution`: Verifies document ingestion Celery task execution workflow with UnitOfWork scope.


### Integration Tests (`tests/integration/`)

* **test_rls_isolation.py**
  * `test_rls_select_isolation`: Verifies that a tenant-scoped session cannot query or fetch rows belonging to other tenants.
  * `test_rls_insert_violation`: Verifies that trying to write another tenant's data raises a DBAPIError containing RLS violation messages.

* **test_services.py**
  * `test_user_service_cannot_demote_last_admin`: Verifies that UserService rejects demoting a tenant's last admin.
  * `test_user_service_cannot_deactivate_self`: Verifies that UserService rejects self-deactivation.
  * `test_invitation_service_flow`: Verifies invitation creation, retrieval, listing, and revocation.

* **test_document_services.py**
  * `test_workspace_service_lifecycle`: Verifies workspace creation, duplicate slug prevention (409), listing, and updates.
  * `test_document_service_lifecycle`: Verifies document file upload, SHA-256 content deduplication (409), listing, deletion, and 404 handling.

* **test_pdf_rag_pipeline.py**
  * `test_pdf_rag_pipeline_real_cv`: Integration test verifying real CV PDF parsing, structural chunking, hybrid retrieval, and grounded citation synthesis.

* **test_search_queries.py**
  * `test_dense_search_query`: Verifies pgvector dense HNSW cosine similarity search score ranking and workspace filtering.
  * `test_sparse_search_query`: Verifies tsvector full-text search indexing, search vector updates, and keyword matching.


### API Endpoint Tests (`tests/api/`)

* **test_auth.py**
  * `test_register_new_tenant_and_admin`: Tests new tenant/admin registration endpoint (`POST /api/v1/auth/register`).
  * `test_login_returns_jwt_tokens`: Tests authentication login endpoint (`POST /api/v1/auth/login`).

* **test_tenant_users.py**
  * `test_get_current_tenant_details`: Tests tenant retrieval endpoint (`GET /api/v1/tenant`).
  * `test_patch_tenant_admin_only`: Tests tenant settings update (`PATCH /api/v1/tenant`) is restricted to admins.
  * `test_role_update_rejected_for_members`: Tests that member role modification is rejected.
  * `test_api_tenant_isolation_list`: Tests that listing users returns only current tenant members.
  * `test_api_tenant_isolation_update`: Tests that updating a user from another tenant returns a 404 error due to RLS isolation.
