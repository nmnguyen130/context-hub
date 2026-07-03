# ContextHub Custom Hybrid RAG Architecture

This document details the complete design, file structure, and logical workflows of the Custom Hybrid RAG (Retrieval-Augmented Generation) & Grounded Chat Engine implemented in ContextHub.

---

## 1. File Structure & Component Manifest

Below is the directory map showing where each part of the RAG system resides and its specific responsibility:

```text
context-hub/backend/app/
├── core/
│   ├── config.py             # Global configurations, credentials, RAG limits & thresholds
│   └── clients.py            # Async HTTP API clients (Gemini Embeddings, Gemini Chat, Cohere Rerank)
├── worker/
│   └── tasks.py              # Celery worker configuration (thin routing wrapper)
└── modules/
    └── documents/
        ├── models.py         # SQLAlchemy tables (Workspace, Document, DocumentChunk)
        ├── chunkers.py       # MarkdownStructureChunker (heading sectioning, paragraph overlaps)
        ├── semantic_cache.py # Redis 8 KNN Vector Semantic Cache VSS index manager
        ├── rerankers.py      # ContextBoostReranker (0ms CPU Matcher) & CohereReranker
        ├── retrieval.py      # Hybrid Search engine (Dense pgvector + Sparse FTS + RRF)
        ├── services.py       # Decoupled ingestion logic (process_document_ingestion)
        └── chat_router.py    # POST /api/v1/chat/stream SSE streaming chat gateway
```

---

## 2. Ingestion Pipeline Flow

The ingestion pipeline converts raw user document uploads into structured, searchable vector embeddings:

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1e1b4b',
    'primaryTextColor': '#e0e7ff',
    'primaryBorderColor': '#4338ca',
    'lineColor': '#6366f1',
    'secondaryColor': '#0f172a',
    'tertiaryColor': '#1e293b',
    'edgeLabelBackground':'#312e81'
  }
}}%%
graph LR
    subgraph PHASE_1 ["Phase 1: Document Extraction"]
        direction TB
        A["User Upload (PDF / MD / TXT)"] --> B["Upload raw file to S3"]
        B --> C["Trigger Celery task"]
        C --> D["PDFParser (PyMuPDF4LLM)<br/>& NFC Normalization"]
    end

    subgraph PHASE_2 ["Phase 2: Semantic Chunking & DLP"]
        direction TB
        E["Group paragraphs into<br/>Atomic Heading Sections"] --> F["Pack sections into<br/>chunks <= 2000 chars"]
        F --> G["Apply Paragraph-Aligned<br/>Sliding Window Overlap"]
        G --> H["Scrub sensitive PII<br/>(DLP Masking Hook)"]
    end

    subgraph PHASE_3 ["Phase 3: Vectorization & Storage"]
        direction TB
        I["Generate Embeddings<br/>(gemini-embedding-001)"] --> J["Bulk Save DocumentChunks<br/>(768-dim Vector)"]
        J --> K["Generate Postgres<br/>simple FTS search_vector"]
        K --> L["Upload parsed<br/>extracted.txt to S3"]
        L --> M["Update status to ACTIVE"]
    end

    D --> E
    H --> I

    style PHASE_1 fill:#0f172a,stroke:#312e81,stroke-width:2px;
    style PHASE_2 fill:#1e1b4b,stroke:#4338ca,stroke-width:2px;
    style PHASE_3 fill:#090d16,stroke:#1e1b4b,stroke-width:2px;
```

---

## 3. Retrieval & Chat Synthesis Flow

This workflow handles incoming user chat queries, executing low-cost semantic cache checks, multi-stage hybrid search, CPU-efficient reranking, and SSE streaming with inline footnote citations.

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1e1b4b',
    'primaryTextColor': '#e0e7ff',
    'primaryBorderColor': '#4338ca',
    'lineColor': '#6366f1',
    'actorColor': '#1e293b',
    'actorBorder': '#4338ca',
    'actorTextColor': '#e2e8f0',
    'signalColor': '#818cf8',
    'signalTextColor': '#c7d2fe',
    'labelBoxBorderColor': '#4338ca',
    'labelBoxBkgColor': '#0f172a'
  }
}}%%
sequenceDiagram
    autonumber
    actor User as User Agent (Frontend)
    participant API as API Gateway (chat_router)
    participant DB as DB (PostgreSQL)
    participant Cache as Semantic Cache (Redis 8)
    participant Gemini as Gemini Chat API

    User->>API: POST /api/v1/chat/stream { query, workspace_id }
    Note over API: 1. Validate multi-tenancy<br/>2. Normalize query to NFC<br/>3. Generate query vector (768-dim)
    
    API->>Cache: FT.SEARCH (KNN Cosine distance check)
    
    alt Semantic Cache HIT (Similarity >= 95%)
        Cache-->>API: Return cached answer string
        API-->>User: data: {"type": "text", "content": cached_answer}
        API-->>User: data: {"type": "done"}
    else Semantic Cache MISS
        Cache-->>API: Return None (cache miss)
        
        par Dense Retrieval
            API->>DB: Cosine similarity check (<=> operator)
        and Sparse Retrieval
            API->>DB: Simple full-text search (@@ operator)
        end
        DB-->>API: Return dense + sparse matching chunks (up to 50 each)
        
        Note over API: 1. Merge lists using RRF (k=60)<br/>2. Apply ContextBoostReranker (Metadata + Jaccard)<br/>3. Filter by Corrective Relevance Gate (> 0.05)
        
        API->>Gemini: stream_chat() (Grounded prompt + Source contexts + Query)
        
        loop Stream Token Chunks
            Gemini-->>API: Yield text token chunk
            API-->>User: data: {"type": "text", "content": token_chunk}
        end
        
        Note over API: Parse full answer using regex<br/>Extract citations and map to metadata
        
        API-->>User: data: {"type": "citations", "data": [mapped_citations_metadata]}
        API->>Cache: HSET cache entry (query_vector, full_answer)
        API-->>User: data: {"type": "done"}
    end
```

---

## 4. Key Architectural Highlights

### 1. Startup Dimension Validation (FastAPI Lifespan)
- Upon application boot, a lifespan handler runs a test embedding request with the keyword `"startup_validation"`.
- It dynamically inspects the database column configuration `DocumentChunk.embedding.type.dim` (defaulting to 768) and compares it with the length of the vector returned by the active `gemini-embedding-001` model.
- If a mismatch is detected, the server aborts startup immediately to prevent corrupt indices.

### 2. Zero-Cost Reranking (`ContextBoostReranker`)
- Avoids the expensive API charges of Cohere Rerank or the local GPU/RAM overhead of running heavy transformer models.
- Operates mathematically on CPU using lexical intersections (Jaccard overlaps) on text combined with strict matching of keywords in headings (`section_title`) and filenames.
- Outperforms standard Reciprocal Rank Fusion by ensuring that chunks matching the high-signal headers of a document are prioritized.

### 3. Decoupled Celery Worker
- Celery `tasks.py` remains a lightweight infrastructure routing wrapper.
- All core business operations (S3 uploads, text extraction, structural chunking, embedding) are located in the business logic service `services.py`, facilitating decoupled testing and clean separation of concerns.
