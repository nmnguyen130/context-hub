# Implementation Plan: Fix All Critical/High/Medium/Low Issues + Top Features

## Architectural decisions (confirmed with user)
- **Semantic cache → pgvector table** (new `chat_cache` table + HNSW index, migration)
- **ChatService → multi-scope sessions** (short tx for resolve/history, no connection during LLM streaming, short tx for persistence)
- **DLP vault → unmask in answers** (persist encrypted vault, unmask authorized responses)
- **Scope: all fixes + top features (F1 history, M2 token/cost accounting)**

---

## Phase 1: Critical Fixes (C1–C3)

### C1 — Register the `documents.process_ingestion` Celery task
- **`app/worker/tasks.py`**: Add `@celery_app.task(name="documents.process_ingestion", bind=True, base=ContextTask)` that reconstructs `RequestContext` from the `context` kwarg, opens an **owner-scoped** UoW (`is_admin=True`, owner_session), instantiates `IngestionService`, and calls `process_document(document_id)`. Configure `celery_app.conf.imports = ("app.worker.tasks",)` so workers discover it.
- **`app/core/database.py`**: Expose `owner_session` (already exists).
- Refine `ContextTask.__call__` to handle the `context` kwarg consistently with how `outbox._dispatch_to_celery` sends it (args=[payload], kwargs={context}).

### C2 — Commit on `/chat/stream` success; rollback on error; no `[DONE]` on error
- **`app/modules/chat/router.py`**: Add an SSE helper module for the `data: {...}\n\n` framing and `[DONE]` sentinel (removes duplication, L14). In `event_generator`: `commit()` after successful iteration; `rollback()` on exception; emit `[DONE]` **only** on success; emit a terminal `error` event (no `[DONE]`) on failure.

### C3 — Inject Redis + Cohere into ChatService
- **`app/api/dependencies.py`**: Add `get_chat_service` factory that pulls `request.app.state.redis` and a shared `CohereClient` from app state, passing them to `ChatService(uow, redis_client=..., cohere_client=...)`.
- **`app/main.py`**: In `lifespan`, create `app.state.cohere = CohereClient()` (singleton) and dispose in teardown. Update `chat/router.py` to use `Depends(get_chat_service)`.

---

## Phase 2: High Fixes (H1–H6)

### H1 — Multi-scope session lifecycle in ChatService
- **`app/modules/chat/services/chat_service.py`**: `ChatService` switches from borrowing one request-scoped UoW to owning a `session_factory`. `process_query` opens short transactions:
  1. **Resolve session + fetch history** (short tx, commit/close) → return session snapshot + history.
  2. **Cache check** (no DB), **query prep**, **retrieval** (open a short tx only for the dense/sparse SQL), **LLM streaming** (NO open connection).
  3. **Persist messages + title/summary update + cache write** (short tx, commit).
- Constructor: `ChatService(session_factory, context, redis_client, cohere_client)`.
- **`dependencies.py`**: `get_chat_service` builds it from `app_session`, the request context, and injected clients.

### H2 — Authorization: session user ownership + workspace↔tenant validation
- **`app/modules/chat/memory/session_service.py`**: `get()` gains a `require_owner` flag; when set, raise 404 if `session.user_id != ctx.user_id`. `list_messages` enforces owner. `list_by_workspace` already filters by user — keep.
- **`app/modules/chat/services/chat_service.py`**: `_resolve_session` validates that the resolved session belongs to `context.user_id`; also validate `request.workspace_id` belongs to `context.tenant_id` (cheap existence check) before retrieval.

### H3 — SSE error sanitization
- **`app/core/exceptions.py`** (or a new `app/modules/chat/errors.py`): map exceptions to safe messages. `ServiceError` keeps its `detail` (user-facing by design); generic `Exception` → "The assistant encountered an unexpected error." Never `str(exc)` to client. Log full detail server-side.

### H4 — Parallelize dense/sparse retrieval
- **`app/modules/chat/retrieval/__init__.py`**: Replace the serial `for` loop with `asyncio.gather` over all (dense, sparse) tasks per query/embedding pair. Each task shares the same short-lived session within one transaction.

### H5 — Semantic cache on pgvector
- **New model `app/modules/chat/models.py` → `ChatCacheEntry`** (tenant_id, workspace_id, query_embedding `Vector(768)`, query_text, response_text, citations JSONB, created_at, expires_at). Add to `models_registry.py`.
- **New migration** adding `chat_cache` table + HNSW index + RLS policy.
- **`app/modules/chat/cache/semantic_cache.py`**: Rewrite to query pgvector via a new `queries.py`-style function: `SELECT ... ORDER BY query_embedding <=> :emb LIMIT 1` with `expires_at` filter. Keep `cosine_similarity` (still used in unit tests). Drop Redis-based get/set; remove Redis dependency from cache (cache becomes DB-backed). `ChatService` no longer needs `redis_client` for the cache (Redis still used by rate limiter / app.state.redis).

### H6 — Backpressure / disconnect handling during streaming
- **`app/modules/chat/generation/synthesizer.py`**: Periodic disconnect check inside the token loop (pass a `is_disconnected` callable); cap `full_text_chunks` growth. On upstream error, emit terminal `error` event and stop.

---

## Phase 3: Medium Fixes (M1–M10)

- **M1** `retrieval/__init__.py` / `chat_service.py`: CRAG retry builds a **fresh** `QueryPlan(queries=[rewritten], embeddings=[retry_emb])` instead of mutating/appending.
- **M2** `clients.py`: Parse `usageMetadata` from Gemini responses; thread `UsageInfo` through `stream_synthesis` → `ChatService` → persist real `token_count`/`cost_usd` (model→price table in config) into `ChatMessage` + aggregate into `ChatSession.total_cost_usd`.
- **M3** `retrieval/grader.py`: Remove the confusing force-accept-top-1 fallback; return empty `accepted` + `is_low_confidence=True` cleanly (surface "no context" upstream).
- **M4** `chunkers/types.py` + `parsers/types.py`: Add `char_start`/`char_end` to `ContentBlock`; parsers populate them; assembler computes chunk offsets via min/max of block offsets (drop the fragile `str.find` heuristic).
- **M5** `parsers/__init__.py`: CSV parser groups rows into batches fitting a target size with header once + `row_range` metadata.
- **M6** `documents/security.py` + `documents/services/ingestion_service.py` + new vault persistence: persist vault encrypted (tenant-scoped) keyed by token; **`chat/generation/synthesizer.py`** unmask tokens in the final answer before emitting `done`. Add a `SecretsProvider`/Fernet wrapper in `app/utils/crypto.py` keyed by `JWT_SECRET`-derived key.
- **M7** `main.py` + `config.py`: Move origin parsing/validation into `Settings.validate_settings` (production: reject `*`).
- **M8** *Refined*: Rate limiter IS globally wired (I confirmed `api_router` depends on it). Add a **stricter policy for `/chat/stream`** via a dedicated dependency (e.g. free: 10/min). Add tests.
- **M9** `session_service.py` / `query/*`: Replace bare `except: pass` with `logger.warning(...)` on LLM fallbacks.
- **M10** `query/__init__.py`: Run `expand_query` ∥ `generate_hyde_embedding` via `asyncio.gather` after rewrite; then embed all.

---

## Phase 4: Low Fixes (L1–L14)

- **L1** Remove unused exceptions (`ChatGenerationError`, `RetrievalInsufficientError`, `SemanticCacheError`) — or wire `RetrievalInsufficientError` when accepted is empty (M3). Keep `ChatSessionNotFoundError`. Update `__init__.py`.
- **L2** Remove `ScoredChunk.boost_score` (unused) — update tests.
- **L3** Honor `ChatRequest.model` by threading it into `stream_synthesis`/`clients` (or remove the field). → **Thread it through** (small, useful).
- **L4** `embeddings.py`: `raise` without rebinding `e`.
- **L5** `build_grounded_prompt`: accept `history` and inject a `## Conversation History` block (this is also **F1**).
- **L6** `session_service.update`: use `exclude_unset=True` semantics so `title=None` can clear it.
- **L7** Remove unused `get_session` from `database.py`.
- **L8** Replace mutable `PaginationParams()` defaults with `None`+sentinel across services.
- **L9** `parsers/__init__.py`: Add a real `parse_json` (structural → table/paragraph blocks) instead of treating JSON as plaintext.
- **L10** `chunkers/assembler.py`: drop redundant `chunk_index=len(sub_chunks)` (re-indexed anyway); minor cleanup.
- **L11** `main.py`: `/health` returns 503 when degraded (keep liveness simple).
- **L12** `ChatService._persist_messages`: populate `ChatMessage.confidence_score` from `grading.avg_confidence`.
- **L13** `clients.py`: move Cohere model name to `settings.COHERE_RERANK_MODEL`.
- **L14** Centralize SSE framing in helper module (done in C2).

---

## Phase 5: Tests (new + updated)

Update **`tests/unit/test_chat_module.py`** for grader change (M3 — empty accepted), removed `boost_score` (L2), parallel retrieval, fresh QueryPlan retry (M1), prompt with history (L5/F1), DLP unmasking, usage parsing.

New files:
- **`tests/unit/test_celery_tasks.py`** — verifies task name registered + dispatches to IngestionService (mock).
- **`tests/unit/test_sse_framing.py`** — framing helper, no `[DONE]` on error.
- **`tests/unit/test_dlp_unmask.py`** — vault round-trip + unmask in answer.
- **`tests/unit/test_csv_batching.py`** — CSV row batching + header dedup (M5).
- **`tests/unit/test_chunker_offsets.py`** — block-offset-based char_start/char_end (M4).
- **`tests/integration/test_ingestion_pipeline.py`** — **end-to-end**: upload → call `IngestionService.process_document` directly → assert `document_chunks` rows + `search_vector` populated + status `ACTIVE`. (Would have caught C1.)
- **`tests/integration/test_chat_streaming.py`** — full `process_query` with mocked Gemini/Cohere: asserts messages **committed** (would have caught C2), session ownership enforced (H2), confidence persisted (L12).
- **`tests/integration/test_semantic_cache_pgvector.py`** — set/get via pgvector table, expiry, workspace isolation (H5).
- **Extend `tests/integration/test_document_services.py`** — duplicate-hash rejection still passes; DLP reject action.

All tests run against the existing test DB harness (`conftest.py`); unit tests use mocks for Gemini/Cohere (no network).

---

## Phase 6: Verification
- `ruff check backend/app backend/tests`
- `ruff format --check`
- `pytest backend/tests -m unit` (no DB needed — fast)
- `pytest backend/tests -m integration` (needs Postgres; the conftest auto-creates `_test` DB and runs migrations — the new migration must apply cleanly)

---

## Files touched (summary)

**New:** `app/modules/chat/models.py` (ChatCacheEntry), `alembic/versions/<new>_chat_cache_dlp_vault.py`, `app/utils/crypto.py`, `app/modules/chat/sse.py` (framing helper), `app/modules/chat/cache/queries.py` (pgvector cache query), 4 new test files.

**Modified (~25):** `worker/tasks.py`, `api/dependencies.py`, `main.py`, `core/config.py`, `core/database.py`, `core/exceptions.py`, `chat/router.py`, `chat/services/chat_service.py`, `chat/memory/session_service.py`, `chat/retrieval/__init__.py`, `chat/retrieval/grader.py`, `chat/generation/synthesizer.py`, `chat/generation/citations.py`, `chat/generation/prompts.py`, `chat/cache/semantic_cache.py`, `chat/query/__init__.py`, `chat/schemas.py`, `chat/exceptions.py`, `chat/__init__.py`, `core/clients.py`, `documents/security.py`, `documents/services/ingestion_service.py`, `documents/parsers/__init__.py`, `documents/parsers/types.py`, `documents/chunkers/assembler.py`, `documents/chunkers/types.py`, `models_registry.py`, `tests/unit/test_chat_module.py`.

## Risk notes
- The ChatService multi-scope refactor (H1) is the largest change; I'll keep the public method signature (`process_query`) identical so the router stays stable.
- The new Alembic migration must run cleanly under the existing `conftest.py` harness; I'll verify table drops in downgrade.
- All Gemini/Cohere calls in tests are mocked — no API keys or network needed.
- I will **not** reformat code outside the lines I touch, to keep the diff reviewable.