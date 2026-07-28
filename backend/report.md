# Comprehensive Review: `chat` & `documents` Modules — ContextHub

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
