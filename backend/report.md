# Comprehensive Review: `chat` & `documents` Modules — ContextHub

**Scope reviewed:** `backend/app/modules/chat/` (~1,567 LOC), `backend/app/modules/documents/` (~2,145 LOC), plus their interactions with `app/core`, `app/infrastructure`, `app/worker`, and Alembic migrations.

**Overall assessment:** The architecture is genuinely strong for a system at this stage — clean layered separation (router → service → queries/parsers/chunkers), proper multi-tenant RLS enforcement at the DB layer, an outbox pattern for reliable async processing, a sophisticated adaptive RAG pipeline (query classification → rewriting → HyDE → multi-query → CRAG), and well-engineered semantic chunking. This is not a toy codebase.

That said, I found **one critical production-breaking bug**, several **high-severity correctness/security issues**, and a meaningful set of optimization and feature opportunities. Findings are prioritized below.

---

## 📊 Module Scorecard

| Dimension | chat | documents | Notes |
|---|---|---|---|
| Architecture | A | A− | Excellent layering; both follow consistent patterns |
| Business logic | B+ | A− | RAG pipeline is sophisticated; CRAG retry has a bug |
| Security | B | B+ | RLS solid; missing authorization gaps & input limits |
| Performance | C+ | B | Several N+1 / serial-await / unindexed query issues |
| Scalability | C+ | B | Semantic cache can't scale; retrieval not parallelized |
| Code quality | A− | A | Readable, typed, consistent; minor dead code |
| Edge cases | C | C+ | Several unhandled failure modes in streaming |
| Test coverage | C+ | B− | Pure functions tested; integration gaps |

---

## 🔴 CRITICAL

### C1. Ingestion pipeline is **never executed** — uploaded documents stay in `PENDING` forever

`DocumentService.upload()` records an outbox event `"documents.process_ingestion"` (`document_service.py:160-166`), and `infrastructure/outbox.py` relays it to Celery via `celery_app.send_task(event_type, ...)`. **But no Celery task named `documents.process_ingestion` is registered anywhere in the codebase** — I verified with a full search: zero `@celery_app.task` / `@shared_task` decorators, no `autodiscover`, no `include=` in celery config. `IngestionService.process_document()` is defined but has no caller.

**Consequence:** Every upload succeeds at the HTTP layer and returns `201`, but no chunking, embedding, or `search_vector` update ever happens. RAG retrieval returns nothing because `document_chunks` is empty. This is a fully-broken core path.

**Fix (two parts):**
1. Register the task handler in `app/worker/tasks.py`:
```python
@celery_app.task(name="documents.process_ingestion", bind=True, base=ContextTask, ...)
def process_ingestion_task(self, payload: dict, context: dict | None = None):
    # rebuild RequestContext, open owner-scoped UoW, call IngestionService.process_document
```
   Note the current `ContextTask.__call__` pops `context` from kwargs, but `_dispatch_to_celery` sends it as a kwarg while `args=[payload]` — the wiring is correct, but you must also ensure the worker imports the task module (add to `celery_app.conf.imports` or use `autodiscover_tasks`).

2. Add an integration test that uploads → asserts `status` transitions `PENDING → PROCESSING → ACTIVE` and chunks exist.

---

### C2. `/chat/stream` never commits — **user/assistant messages and auto-title are silently discarded**

`stream_chat()` in `router.py:33-62` iterates `service.process_query(...)` and streams SSE, but **never calls `await service.uow.commit()`**. `process_query()` calls `_persist_messages()` which does `self.uow.flush()` (writes to the transaction) and mutates `session.message_count`, but the transaction is rolled back when `UnitOfWork.__aexit__` runs without an explicit commit (`uow.py:54-69` — it detects pending dirty state, logs a warning, and rolls back).

Compare with `create_session` / `update_session` / `delete_session`, all of which explicitly `await service.uow.commit()`.

**Consequence:** Every chat turn is lost on transaction close. History is never built. `running_summary` updates, `message_count`, `total_tokens` — all rolled back. The system appears to "work" only within a single streaming response.

**Why it's subtle:** `flush()` makes rows visible inside the open transaction, so the in-memory session state looks correct during the stream. The data dies on session close.

**Fix:** Wrap persistence in a commit. Because the response is a streaming generator and the LLM call happens *inside* the generator, the transaction must stay open for the whole stream. Recommended:
```python
async def event_generator():
    try:
        async for event in service.process_query(body, context):
            yield f"data: {event.model_dump_json()}\n\n"
            if await request.is_disconnected():
                break
        await service.uow.commit()   # <-- commit on success
    except Exception as exc:
        await service.uow.rollback()
        yield ...
```
Also handle the client-disconnect case explicitly: currently `break` drops you to `yield "data: [DONE]"` with an uncommitted transaction that then rolls back — arguably desirable (don't persist half a stream), but make it intentional and documented.

---

### C3. `RedisClient` and `CohereClient` are **never injected** into `ChatService` — semantic cache & reranking are dead

`ChatService.__init__` accepts `redis_client` and `cohere_client` with `or GeminiClient()` / `or CohereClient()` defaults. The router wires it via `get_service(ChatService)` which calls `ChatService(uow)` — **no Redis, no Cohere, no API keys**.

**Consequences:**
- `SemanticCache.redis_client is None` → `cache.get()`/`set()` short-circuit to `None`/no-op (`semantic_cache.py:39, 93`). The entire semantic-cache subsystem is silently disabled in production.
- `CohereClient.api_key` is `None` → `Reranker` falls back to plain RRF sort on every request (`reranker.py:24-28`). Not catastrophic, but you've built and configured a reranker that never runs.

**Fix:** Update the dependency factory to inject `request.app.state.redis` and a shared `CohereClient` singleton:
```python
async def get_chat_service(
    uow: UnitOfWork = Depends(get_uow),
    request: Request,
) -> ChatService:
    return ChatService(
        uow=uow,
        redis_client=request.app.state.redis,
        cohere_client=app.state.cohere,  # cache a singleton in lifespan
    )
```
Consider generalizing `get_service` to accept extra kwargs.

---

## 🟠 HIGH

### H1. `process_query()` mixes a streaming generator with side effects inside an open transaction — long-held DB connections

The entire RAG flow (embeddings → LLM calls → rerank → streaming synthesis, potentially 30–120s) runs inside the `UnitOfWork` transaction opened by `get_uow`. Two problems:

1. **Connection pool exhaustion under load.** The `app_engine` pool is `DATABASE_POOL_SIZE=10, max_overflow=20` (30 total). A handful of concurrent streaming chats pins one connection each for the whole stream duration. 30 simultaneous users → pool starvation → 503s.
2. **Idle-in-transaction.** Postgres holds snapshot locks; long transactions bloat and can cause `pg_stat_activity` "idle in transaction" warnings and replication lag.

**Fix:** Split the transaction into short scopes:
- Resolve session + fetch history → commit/close (read).
- Do retrieval + LLM streaming with **no** transaction open (use a fresh short-lived session for the dense/sparse search, or use `autocommit` reads).
- Open a new short transaction only for `_persist_messages` + summary/title update → commit.

This requires `ChatService` to manage its own session lifecycle rather than borrowing the request-scoped UoW. Given the architecture, the cleanest pattern is: **streaming endpoint uses a dedicated session factory**, not `get_uow`.

---

### H2. No authorization check that `request.workspace_id` belongs to `context.tenant_id`

In `ChatService.process_query`, `request.workspace_id` is taken directly from the untrusted request body and used in retrieval (`queries.py`) and cache scoping. RLS will still constrain *rows* by `tenant_id`, so a cross-tenant workspace leak is prevented at the DB level. **But** within the same tenant, any user can query any workspace they don't belong to, and there's no workspace-membership concept enforced. Worse, the session creation path (`_resolve_session` → `session_service.create`) *does* validate the workspace, but the streaming path that takes an existing `session_id` doesn't re-check that the session belongs to the calling user.

**Concretely:** User A can call `/chat/stream` with `{session_id: <user_B's_session>}` and read B's history (RLS permits it because they share a tenant_id). `ChatSessionService.get()` checks tenant but **not user ownership** for reads.

**Fix:**
- In `ChatSessionService.get`, when invoked from a user-scoped path, assert `session.user_id == ctx.user_id` (or introduce workspace membership/role checks).
- Validate that `request.workspace_id` exists and belongs to `context.tenant_id` before retrieval (cheap `SELECT 1`).
- Decide on a workspace-membership model (currently workspaces have no member list — only tenant scope).

---

### H3. SSE error handling leaks internal details and the `[DONE]` sentinel is always emitted — even on error

```python
except Exception as exc:
    err_event = SSEEvent(type="error", data={"message": str(exc)})
    yield f"data: {err_event.model_dump_json()}\n\n"
yield "data: [DONE]\n\n"
```

Two issues:
1. `str(exc)` can contain API keys (Gemini/Cohere URLs echo the key in query params on some errors), DB connection strings, or stack-trace fragments. This is sent to the client.
2. `[DONE]` is yielded after errors. Frontends often treat `[DONE]` as "stream complete successfully" — masking failures.

**Fix:**
- Map known exceptions to safe messages (`ChatGenerationError` → "The assistant is unavailable; please retry"); log the full detail server-side.
- Emit `[DONE]` only on full success; emit a distinct terminal event (e.g. `type: "fatal_error"`) on failure, or rely on closing the stream.

---

### H4. `dense_search` / `sparse_search` are issued **serially** in a loop — biggest latency contributor

```python
for query_text, embedding in zip(query_plan.queries, query_plan.embeddings):
    dense_res = await dense_search(...)   # blocks
    sparse_res = await sparse_search(...) # blocks
```

For a COMPLEX query (rewrite + 3 expansions + HyDE = 5 queries), this is **10 sequential DB round-trips** before reranking. Each pgvector HNSW scan + FTS is ~10–50ms, so 100–500ms of pure serialization that should be ~one round-trip with `asyncio.gather`.

**Fix:**
```python
tasks = []
for q, emb in zip(query_plan.queries, query_plan.embeddings):
    tasks.append(dense_search(..., embedding=emb, ...))
    tasks.append(sparse_search(..., query=q, ...))
results = await asyncio.gather(*tasks)
```
Even better: collapse multiple embeddings into a **single SQL `ORDER BY ... LIMIT` per anchor** using `UNION`-style candidate generation, or use batched pgvector queries (`embedding IN (...)` isn't supported, but you can issue one query per embedding in parallel).

**Expected win:** Cut p50 retrieval latency by 3–5× on complex queries.

---

### H5. Semantic cache `KEYS` scan — **O(n) over all workspace cache entries on every query**

```python
keys = await self.redis.keys(pattern)  # semcache:{workspace}:*
for key in keys:
    raw_data = await self.redis.get(key)
    ... cosine_similarity(...)
```

`KEYS` is explicitly documented as "do not use in production" — it blocks the Redis event loop. Then each value is fetched individually and cosine-similarity is computed **in Python over 768-dim vectors**. With even 1,000 cached entries per workspace, this is seconds of CPU per cache lookup, defeating the entire purpose of caching.

**Fix — two tiers:**
1. **Short term (correctness):** Use `SCAN` instead of `KEYS` to avoid blocking. Still slow but safe.
2. **Proper fix:** Move similarity search to a vector index. Options:
   - Use a **separate pgvector table** `chat_cache(workspace_id, query_embedding vector(768), response jsonb)` with an HNSW index — reuse the infra you already have. Lookup is then a single indexed ANN query, ~5ms.
   - Or use Redis Stack's `FT.SEARCH` with `VECTOR` HNSW (requires RedisAI/RediSearch modules).
   - Or maintain a per-workspace in-memory `numpy` matrix refreshed periodically.

This is the difference between a cache that *works* and one that *scales*.

---

### H6. Streaming tokens are **buffered in a Python list and never back-pressured**

`stream_synthesis` appends every token to `full_text_chunks` and yields it. If the client is slow (or the SSE write blocks), Gemini's stream keeps producing and `httpx`'s buffer grows. For long answers (4K+ tokens) with a slow consumer, memory grows unboundedly per request.

Additionally, `request.is_disconnected()` is checked *after* each `yield`, so a disconnect during `client.stream_generate` (which can produce many tokens before yielding back) isn't observed until the next iteration.

**Fix:**
- Add a timeout / max-buffer check; if the client hasn't drained, pause upstream reads (Starlette's `StreamingResponse` already does some of this, but verify).
- Wrap the inner `async for token` with a periodic disconnect check.

---

## 🟡 MEDIUM

### M1. CRAG retry mutates `query_plan` and **re-runs the entire multi-query retrieval**

On low confidence, the code appends `rewritten` to `query_plan.queries` and `retry_embedding` to `query_plan.embeddings`, then calls `retrieve_context` again — which re-executes dense+sparse for **all** prior queries *plus* the new one. Wasted work. Intended behavior is presumably a *fresh* retrieval using only the rewrite.

**Fix:** Construct a new `QueryPlan(queries=[rewritten], embeddings=[retry_embedding], ...)` for the retry, or design `retrieve_context` to accept a flag.

---

### M2. `token_count = len(content.split())` — inaccurate, and `total_cost_usd` is **never populated**

`_persist_messages` and `ChatSession` track `token_count` and `total_tokens` using whitespace word counts. `total_cost_usd` / `cost_usd` fields exist on both models but are never written (always 0.0). For an enterprise RAG product, accurate usage/cost tracking per tenant is usually a billing requirement.

**Fix:**
- Use Gemini's `usageMetadata` from the response (`promptTokenCount`, `candidatesTokenCount`) — already returned by the API, just not parsed in `clients.py`.
- Compute cost from a model→price table in config.
- Persist into the existing `cost_usd` fields and aggregate into `ChatSession.total_cost_usd`.

---

### M3. `grade_relevance` fallback is counterproductive

```python
if not accepted:
    accepted = [chunks[0]]   # always force-accept the top chunk
    ...
is_low = avg_conf < threshold or len(accepted) == 0
```

The `len(accepted) == 0` branch can never be true because of the fallback. And forcing acceptance of a below-threshold chunk undermines the CRAG signal: `needs_retry` is computed from `avg_conf`, but if the top chunk was force-accepted with score 0.02 (below 0.05 threshold), `avg_conf` becomes 0.02 → `is_low=True` → retry fires. That's correct *by accident*, but the logic is confusing. Decide: either reject cleanly (and surface "no context found" to the user) or accept top-k always. Don't do both silently.

---

### M4. Chunker overlap can **double-count content** and the `search_offset` heuristic is fragile

`DocumentAssembler.flush_buffer` computes `char_start = full_text.find(first_block_text, search_offset)`. `str.find` returns the first match; if a paragraph appears twice in the document (boilerplate headers, repeated clauses), offsets drift silently and all subsequent `char_start`/`char_end` are wrong. Also, `_compute_block_overlap` retains tail blocks but the next chunk starts with those same blocks — so a sentence can appear in two chunks, which is fine for retrieval but the `char_start` math double-counts.

**Fix:** Have parsers emit absolute character offsets in `ContentBlock` (e.g. `char_start`/`char_end` on each block) and compute chunk offsets by min/max. Drop the `find` heuristic.

---

### M5. CSV parser produces one block **per row**, each repeating the header — explodes chunk count and token usage

```python
for row_index, row in enumerate(reader, start=1):
    blocks.append(ContentBlock(text=f"{header}\n{separator}\n{row_text}", ...))
```

A 10K-row CSV → 10K blocks, each ~re-embedding the header. Embedding cost and `document_chunks` row count balloon. The chunker then splits large blocks but each "large block" here is already one row.

**Fix:** Group rows into batches that fit `max_chunk_size` (e.g. 50 rows/chunk), preserving the header once. Add a `row_range` metadata field for citation precision.

---

### M6. DLP vault is **discarded** — masked text is unrecoverable, citations become useless

`apply_dlp` returns `(masked_text, warnings, vault)` but `IngestionService` does `_vault = apply_dlp(...)` and throws the vault away. The masked text `[PII_EMAIL_a1b2]` is embedded and stored. At generation time, the LLM may quote `[PII_EMAIL_a1b2]` in its answer, and the user sees the token, not the original. There's no unmasking step in `stream_synthesis`.

**Fix options:**
- Persist the vault (encrypted, tenant-scoped, TTL'd) keyed by token, and unmask in `extract_citations` / before streaming the final answer to authorized users.
- Or, simpler and safer: mask only for embedding/indexing, but store the *unmasked* chunk content in a separate `content_raw` column accessible only to authorized roles. Decide on threat model.

Currently DLP gives the *appearance* of protection while breaking the user experience.

---

### M7. `ALLOWED_ORIGINS="*"` with `allow_credentials=True` is a browser-rejected / insecure combo

`main.py` warns but allows `*` + credentials in non-prod. Browsers reject credentialed requests to `*` origins, so this only works because something else is failing open. In prod it raises, but the validation runs only at import time. Move origin-parsing into `Settings.validate_settings`.

Minor, but it's a known CORS foot-gun.

---

### M8. No rate limiting on `/chat/stream` (or any chat/docs route)

`RateLimiter` is fully built (`infrastructure/rate_limiter.py`) with sliding-window Lua, plan-based policies, and proper headers — but it's **never wired** to any route. Chat streaming is the most expensive endpoint (LLM tokens, embeddings, rerank). A single abusive client can burn the Gemini quota and cost budget in minutes.

**Fix:** Add `dependencies=[Depends(chat_limiter)]` to `chat_router`, with a tighter policy than general API (e.g. free: 10/min, pro: 100/min). The infra is ready — this is a one-line-per-router change.

---

### M9. `expand_query` / `rewrite_query` / `auto_title` swallow JSON/LLM errors silently and return degraded results with no observability

`expand_query` catches `JSONDecodeError` and returns `[query]` — fine. But `auto_title` and `update_summary` have bare `except Exception: pass` / `return session.running_summary`. No metric, no log. When the LLM is rate-limited, titles silently fall back to `first_message[:50]` and summaries never update, with zero signal to operators.

**Fix:** At minimum `logger.warning(...)` with the exception; ideally emit a metric counter (`rag.llm.fallback`) for dashboards.

---

### M10. `prepare_queries` for COMPLEX runs `rewrite → expand → embed(all) → HyDE` **serially**

Each LLM/embedding call awaits the previous. The rewrite and expand are dependent (expand takes the rewrite), but HyDE depends only on the rewrite — it could run concurrently with `expand`. And `embed_texts(all_queries)` is one batched call (good), but it could be overlapped with HyDE generation.

**Fix:** `asyncio.gather(expand(rewritten), generate_hyde_embedding(rewritten))`, then embed everything.

---

## 🟢 LOW / Code Quality

- **L1.** `chat/exceptions.py` defines `ChatGenerationError`, `RetrievalInsufficientError`, `SemanticCacheError` — none are raised anywhere. Dead code; either wire them or remove.
- **L2.** `ScoredChunk.boost_score` is never set or read. Remove or implement.
- **L3.** `ChatRequest.model` field is accepted but never used (no model override in `stream_synthesis`/`clients`). Either honor it or drop it.
- **L4.** `EmbeddingProvider._embed_batch_with_retry(batch, batch_idx)` — `batch_idx` only used in logging; fine, but the `raise e` at line 51 can just be `raise`.
- **L5.** `format_history_for_prompt` returns `["user: ...", "assistant: ..."]` but `build_grounded_prompt` doesn't use history at all — history is only fed to `rewrite_query`. The actual generation prompt has no conversational context besides `running_summary`. For multi-turn coherence this is a real UX gap (see Missing Features).
- **L6.** `ChatSessionUpdate.update` skips `None` values (`if value is not None`), making it impossible to explicitly clear `title` to null. Use `exclude_unset=True` semantics instead.
- **L7.** `get_session` in `database.py` is defined but unused (UoW is the path). Remove.
- **L8.** `PaginationParams` is instantiated as a default arg in several service methods (`pagination: PaginationParams = PaginationParams()`) — mutable default. Pydantic models are somewhat safer than dataclasses here, but it's still a smell; use `None` + sentinel.
- **L9.** `_PARSER_MAP` includes `application/json → parse_plaintext`, which parses JSON as if it were prose. JSON should either be parsed structurally or rejected; treating it as text loses schema info and produces poor chunks.
- **L10.** `DocumentAssembler._split_large_block` re-creates `Chunk` objects with `chunk_index=len(sub_chunks)` which is then overwritten by the final re-index loop. Harmless but confusing.
- **L11.** `health_check` returns 200 even when `degraded`. Should return 503 when any component is unreachable, or at least differentiate `/health` (liveness) from `/ready`.
- **L12.** `ChatMessage.confidence_score` is on the model and schema but never populated. Wire it from `grading.avg_confidence`.
- **L13.** Hardcoded Cohere model `"rerank-english-v3.0"` in `clients.py` — should be config-driven, especially since multilingual workspaces exist.
- **L14.** The `[DONE]` SSE terminator and `data: ` prefix are hardcoded in two places (router error path + success path). Centralize in a small helper.

---

## 🧪 Test Coverage Gaps

Current tests cover pure functions (classifier, RRF, grader, citations, prompts, cosine) — good unit coverage. **Missing:**

| Gap | Priority |
|---|---|
| End-to-end ingestion (upload → chunks persisted) — would have caught **C1** | Critical |
| Streaming endpoint commit assertion — would have caught **C2** | Critical |
| Dependency injection of Redis/Cohere into ChatService — would have caught **C3** | Critical |
| Cross-user session access (H2) | High |
| Tenant-isolation integration for `chat_messages` / `chat_sessions` | High |
| SSE error-path contract (no `[DONE]` on error, no key leakage) | High |
| CRAG retry path & low-confidence branch | Medium |
| Chunker: overlapping content, large tables, repeated paragraphs (M4) | Medium |
| DLP vault round-trip (M6) | Medium |
| Concurrent retrieval (`asyncio.gather` regression test) | Medium |

---

## ✨ Missing Features / Strategic Upgrades

### F1. True multi-turn conversational context in generation
Currently the generation prompt includes only `running_summary` + retrieved chunks — **not the actual recent Q&A turns**. So "and what about the second point?" has no idea what "the second point" was, unless the rewriter resolved it (and the rewriter only sees the last 4 turns as plain strings). Feed the last N message pairs into `build_grounded_prompt` as a `## Conversation History` block.

### F2. Feedback loop & answer-rating
No way for users to thumbs-up/down an answer, flag bad citations, or retry. This data is gold for evaluating retrieval quality and fine-tuning prompts. Add `ChatMessage.feedback: enum('up','down',null)` + `feedback_note` and an endpoint.

### F3. Retrieval evaluation & observability dashboard
You have all the signals (`grading.avg_confidence`, `needs_retry`, cache hit ratio, rerank scores) but they're logged, not aggregated. Export to Prometheus/OpenTelemetry:
- `rag_retrieval_confidence` histogram
- `rag_crag_retry_total` counter
- `rag_cache_hit_total` / `rag_cache_miss_total`
- `rag_llm_tokens_total{model,kind}` + cost
- `rag_latency_seconds{stage="embed|retrieve|rerank|generate"}`

### F4. Query routing beyond RAG: small-talk / chitchat / out-of-domain
The grounded prompt says "If the context does not contain enough information, state: 'I cannot find the answer...'". There's no intent detection. A lightweight classifier (the existing `classify_query` could be extended) could route greetings/capabilities questions without invoking retrieval at all — saving cost and improving UX.

### F5. Streaming partial citations & source previews
Citations are emitted *after* the full text is generated. Inline citation markers `[^1]` stream live, but the mapping to source metadata arrives at the end. Consider emitting a `sources` event (already done) and resolving markers progressively so the UI can render live tooltip previews.

### F6. Document re-ingestion & versioning
`delete` + `upload` is the only way to update a document. No versioning, no diff, no "re-chunk with new settings." With the `content_hash` unique constraint, re-uploading the same content is rejected — good — but there's no path for "updated content." Add `Document.version` and a `POST /documents/{id}/reingest` that swaps chunks atomically.

### F7. Workspace-level & document-level filters in chat
Chat always searches the whole workspace. Let users scope a chat to specific documents, folders, or tags (the `topic_tags` enrichment already exists). Add `ChatRequest.document_ids: list[UUID] | None` plumbed into `dense_search`/`sparse_search`.

### F8. Structured outputs for analytical queries
For "list the top 5 risks" or "summarize revenue by quarter," a structured JSON answer (or a generated chart spec) is far more useful than prose. Gemini supports `responseMimeType: "application/json"` + `responseSchema`. Route aggregation-type queries (you already classify `has_aggregation`) to structured generation.

### F9. Async/parallel ingestion with progress
Ingestion is one big Celery task per document. For large PDFs, surface progress (`chunks_created`, `embeddings_done`) via a job-status endpoint or SSE on `/documents/{id}/status`. Useful UX and observability.

### F10. Multi-modal documents
PDF parser ignores images (`ignore_images=True`). For slide decks, scanned contracts, and diagrams, add OCR (Tesseract / a vision model) and image-caption chunks. This is a major retrieval-quality win for non-text-native PDFs.

---

## 🗺️ Roadmap (prioritized)

### Phase 0 — Stop the bleeding (this week)
1. **C1** Register `documents.process_ingestion` Celery task + worker import; add e2e ingestion test.
2. **C2** Add `commit()` to `/chat/stream` success path; add rollback on error.
3. **C3** Inject `redis_client` and `cohere_client` into `ChatService` via the dependency factory.
4. **H3** Sanitize SSE error messages; stop emitting `[DONE]` on error.

### Phase 1 — Correctness & security (weeks 2–3)
5. **H2** Add user-ownership check on chat sessions; validate `workspace_id` ↔ tenant.
6. **M1** Fix CRAG retry to use a fresh `QueryPlan`.
7. **M6** Decide DLP vault strategy and implement unmasking (or remove the vault return).
8. **M8** Wire `RateLimiter` to chat & documents routers.
9. **L-series** dead-code cleanup; remove unused exceptions/fields.

### Phase 2 — Performance & scalability (weeks 3–5)
10. **H1** Refactor streaming endpoint to use short-lived transactions; release the DB connection during LLM calls.
11. **H4** Parallelize dense/sparse retrieval with `asyncio.gather`.
12. **H5** Migrate semantic cache to pgvector (or Redis Stack VECTOR); eliminate `KEYS`.
13. **M10** Parallelize COMPLEX query-prep (expand ∥ HyDE).
14. **M5** Batch CSV rows into chunks.

### Phase 3 — Feature depth (weeks 5–8)
15. **F1** Inject conversation history into the generation prompt.
16. **F3** Prometheus metrics + Grafana dashboard for RAG signals.
17. **F2** Answer feedback model + endpoints.
18. **F6** Document versioning & re-ingest endpoint.
19. **F7** Chat scoping to document subsets.
20. **M2** Accurate token/cost accounting from `usageMetadata`.

### Phase 4 — Differentiation (weeks 8+)
21. **F8** Structured JSON outputs for aggregation queries.
22. **F10** Multi-modal / OCR for scanned PDFs and images.
23. **F4** Intent routing (chitchat / capabilities / RAG).
24. **F5** Progressive inline citations.
25. **F9** Streaming ingestion progress.

---

## Summary

The codebase demonstrates strong engineering taste — layered architecture, RLS-first multi-tenancy, an outbox for reliability, and a genuinely thoughtful RAG pipeline. The **three critical issues (C1–C3) are all wiring/integration bugs, not design flaws**, which is encouraging: the hard architectural decisions are already correct. Fixing Phase 0 alone will take the system from "looks like it works in dev" to "actually works in production." Phases 1–2 then deliver the latency, cost, and scalability characteristics expected of an enterprise RAG product, and Phases 3–4 unlock the features that differentiate it.

The single highest-leverage action is **adding integration tests for the upload→ingest→chat round-trip** — it would have caught all three critical bugs immediately and would guard every future refactor in these two modules.