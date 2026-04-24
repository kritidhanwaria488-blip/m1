# RAG Architecture: Mutual Fund FAQ Assistant

This document describes a retrieval-augmented generation (RAG) architecture for the facts-only mutual fund FAQ assistant defined in `problemStatement.md`. It prioritizes **accuracy, provenance, and compliance** over open-ended conversational ability.

---

## 1. Design Principles

| Principle | Implication for Architecture |
|-----------|------------------------------|
| **Facts-only** | Retrieval gates what the model may say; prompts and post-checks forbid advice and comparisons. |
| **Single canonical source per answer** | Retrieval returns chunks tagged with one citation URL; generation is constrained to cite that URL only. |
| **Curated corpus** | Ingestion is batch or scheduled from an allowlist of URLs; no arbitrary web crawling at query time. |
| **No PII** | No user document upload path; chat payloads exclude identifiers; logs redact or omit sensitive fields. |
| **Accuracy over "intelligence"** | Prefer abstention, refusal, or "see the indexed scheme page" over speculative answers. |

---

## 2. Components Overview

| Component | Purpose | Implementation Path |
|-----------|---------|---------------------|
| **Scheduler (GitHub Actions)** | Runs full ingest job daily at 09:15 IST | `.github/workflows/ingest.yml` |
| **Scraping Service** | Fetches allowlisted URLs, persists raw HTML | Phase 4.0 |
| **Ingestion Pipeline** | Normalizes, chunks, embeds, indexes documents | Phases 4.1 → 4.2 → 4.3 |
| **Vector Store** | ChromaDB with BAAI/bge-small-en-v1.5 embeddings (384-dim) | `data/chroma/` |
| **Thread Store** | Persists conversation history per thread | `runtime/phase_8_threads/` |
| **Query Router** | Classifies intent (factual vs advisory vs out-of-scope) | `runtime/phase_7_safety/` |
| **Retriever + Re-ranker** | Dense retrieval + metadata filtering | `runtime/phase_5_retrieval/` |
| **LLM Layer** | Generates short answers from retrieved context | `runtime/phase_6_generation/` |
| **Post-Guards** | Validates citation, sentence count, forbidden patterns | `runtime/phase_7_safety/` |
| **API Layer** | FastAPI endpoints for chat and threads | `runtime/phase_9_api/` |

---

## 3. Corpus & Data Model

### 3.1 Scope (Current Corpus)

**AMC:** HDFC Mutual Fund

**Allowlisted URLs (HTML only from Groww scheme pages):**

| Scheme | URL |
|--------|-----|
| HDFC Mid Cap Fund Direct Growth | `https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth` |
| HDFC Equity Fund Direct Growth | `https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth` |
| HDFC Focused Fund Direct Growth | `https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth` |
| HDFC ELSS Tax Saver Fund Direct Plan Growth | `https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth` |
| HDFC Large Cap Fund Direct Growth | `https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth` |

**Out of scope for now:** AMC PDFs (KIM, SID), standalone factsheet PDFs, AMFI/SEBI pages. The ingestion pipeline should be built so PDFs and extra allowlist entries can be added later without redesign.

### 3.2 Document Metadata (Per Chunk)

| Field | Purpose |
|-------|---------|
| `source_url` | Canonical URL for citation (exactly one per assistant message) |
| `source_type` | e.g., `groww_scheme_page` (current); later `factsheet`, `kim`, `sid`, `amfi`, `sebi` |
| `scheme_id` / `scheme_name` | Tie chunks to a scheme when applicable |
| `amc` | AMC identifier or name |
| `title` | Page or section title for debugging and UI tooltips |
| `fetched_at` | ISO date for "Last updated from sources" footer |
| `content_hash` | Detect content drift on re-crawl |

### 3.3 Chunking Strategy

**HTML (Groww scheme pages):**
- Split on headings and logical sections
- Preserve tables as single units where possible
- Target chunk size: 300–450 tokens (for BAAI/bge-small-en-v1.5, max 512 input tokens)
- Overlap: 10–15% to preserve boundary context
- De-duplication: Same URL + overlapping hash → keep one primary chunk

**For implementation-level details:** See `chunking-embedding-architecture.md`

### 3.4 Structured Fund Metrics

Hybrid approach for reliable numeric queries:

| Layer | Storage | Role |
|-------|---------|------|
| **Structured "facts" store** | One record per scheme per scrape (JSON/Postgres) | Exact answers, filters, regression tests |
| **Vector index (chunks)** | Full normalized text / tables | Narrative context, exit load, benchmark |

**Recommended schema (per scheme, per snapshot):**

| Field | Storage Notes |
|-------|---------------|
| `scheme_id`, `scheme_name`, `amc` | From URL registry; stable keys |
| `source_url` | Groww page URL (citation) |
| `fetched_at` | ISO timestamp of scrape |
| `raw_content_hash` | Hash of raw HTML used for extraction |
| `nav` | Number + currency + optional `as_of` date |
| `minimum_sip` | Number (INR) + frequency if stated |
| `fund_size` / `aum` | Number + unit |
| `expense_ratio` | Percentage as number (e.g., 0.52 for 0.52% p.a.) |
| `rating` | Raw label + `rating_kind` enum: `riskometer` \| `analyst` \| `unknown` |

Use `null` for missing fields; log parse warnings. Do not invent values.

**Extraction:** Parse server-rendered HTML (Groww often embeds data in `__NEXT_DATA__` / JSON blobs).

**Query-time use:** For column-mapped questions ("What is the minimum SIP?"), answer from structured row with `source_url` citation.

---

## 4. Ingestion Pipeline (Detailed)

### 4.0 Scheduler and Scraping Service

#### Scheduler — GitHub Actions

The scheduler triggers the full ingestion pipeline daily to ensure the assistant has access to the latest mutual fund data.

| Attribute | Value |
|-----------|-------|
| **Frequency** | Every day at 09:15 AM IST (Asia/Kolkata) |
| **Cron Expression** | `45 3 * * *` (03:45 UTC ≈ 09:15 IST; India has no DST) |
| **Workflow File** | `.github/workflows/ingest.yml` |
| **Purpose** | Get latest data from all configured URLs and refresh the vector index |

**Pipeline Execution Order:**
```
Scheduled Trigger (09:15 AM IST)
    ↓
1. Checkout repository
    ↓
2. Install Python dependencies
    ↓
3. SCRAPE → Fetch latest HTML from all URLs
    ↓
4. NORMALIZE → Clean and extract structured data
    ↓
5. CHUNK + EMBED → Split and generate vectors
    ↓
6. INDEX → Upsert to ChromaDB
    ↓
7. Upload artifacts (data/chroma/, logs)
```

**Configuration:**
- **Timeout:** 30–60 minutes (prevents quota burn on hung requests)
- **Idempotency:** Safe to re-run; uses `content_hash` to skip unchanged content
- **Manual Trigger:** `workflow_dispatch` enabled for hotfixes
- **Secrets:** `INGEST_USER_AGENT` (optional), no API keys needed for local embeddings

#### Scraping Service

The scraping service fetches data from all URLs listed in the URL registry (`config/urls.yaml`) during each scheduled run.

| Aspect | Specification |
|--------|---------------|
| **Input** | URL registry (`config/urls.yaml`) — 5 Groww HDFC scheme pages |
| **Method** | HTTP(S) GET requests |
| **Rate Limiting** | 2-second delay between requests |
| **Timeout** | 30 seconds per URL |
| **User-Agent** | Identifiable string (e.g., `MutualFundFAQ-Assistant/1.0`) |

**URLs Scraped (Daily at 09:15 AM):**

| # | Scheme | URL |
|---|--------|-----|
| 1 | HDFC Mid Cap Fund Direct Growth | `https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth` |
| 2 | HDFC Equity Fund Direct Growth | `https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth` |
| 3 | HDFC Focused Fund Direct Growth | `https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth` |
| 4 | HDFC ELSS Tax Saver Fund Direct Plan Growth | `https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth` |
| 5 | HDFC Large Cap Fund Direct Growth | `https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth` |

**Behavior:**
1. Read all URLs from `config/urls.yaml`
2. For each URL:
   - Send HTTP GET request
   - Respect `robots.txt`
   - Apply rate limiting (2s delay)
   - Store raw HTML to `data/raw/{run_id}/{scheme_id}.html`
   - Compute `content_hash` for change detection
3. On failure (non-2xx, timeout, empty body):
   - Log error with URL and timestamp
   - Mark URL as failed for this run
   - Continue with remaining URLs
4. Forward successfully fetched HTML to normalization stage

**Output:**
- Raw HTML files per URL per run
- Scrape manifest (URL → status, hash, timestamp)
- Logs for debugging failed fetches

### 4.1 Ingestion Stages

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ URL         │───▶│ Fetch       │───▶│ Normalize   │───▶│ Chunk +     │
│ Registry    │    │ (Scrape)    │    │ (Clean HTML)│    │ Enrich      │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                  │
                                                                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Chroma    │◀───│  Embed      │◀───│  Structured │
│   Local     │    │  (BGE)      │    │  Facts JSON │
│ (data/chroma)    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
```

**Stage Details:**

1. **URL Registry:** Versioned YAML/JSON of allowed URLs with tags (AMC, scheme, document type)
2. **Fetch:** Execute on each scheduled run; store raw HTML for audit/replay
3. **Normalize:** Strip boilerplate (nav, footers); keep main content; extract structured metrics
4. **Chunk + Enrich:** Apply chunking rules; attach metadata (`source_url`, `scheme_id`, `fetched_at`, etc.)
5. **Embed:** BAAI/bge-small-en-v1.5 via sentence-transformers (local, 384-dim)
6. **Index:** Upsert to local ChromaDB via `PersistentClient` (data/chroma/)

### 4.2 Failure Handling

| Scenario | Handling |
|----------|----------|
| Failed URL | Log, alert, exclude from index until fixed |
| Partial/empty HTML | Mark document quality flag; exclude low-confidence chunks |
| PDF extraction (future) | Apply same quality pattern |

### 4.3 Vector Index — Local ChromaDB (PersistentClient)

**Product choice:** Local ChromaDB — embedded vector database
- **Benefits:** No external dependencies, fast local queries, data stays on-premise
- **Storage:** Local filesystem (`data/chroma/`)

**Ingest-time steps:**

```python
client = chromadb.PersistentClient(
    path="data/chroma",
    settings=Settings(anonymized_telemetry=False)
)
collection = client.get_or_create_collection(
    name=INGEST_CHROMA_COLLECTION,  # e.g., "mf_faq_chunks"
    metadata={"hnsw:space": "cosine"}
)
# Dimension: 384 (must match BAAI/bge-small-en-v1.5)
```

**Record shape:**

| Field | Description |
|-------|-------------|
| `id` | `chunk_id` (deterministic hash for idempotent upserts) |
| `embedding` | Float vector length 384 |
| `document` | `chunk_text` (retrieval display + LLM context) |
| `metadata` | `source_url`, `scheme_id`, `scheme_name`, `amc`, `source_type`, `fetched_at`, `chunk_index`, `section_title` |

**Upsert strategy:**
- Daily ingest: upsert by `chunk_id` (add new, update changed)
- Optimization: Skip write if `chunk_text_hash` unchanged

**Deletion / stale data:**
- If scheme removed from registry: delete entries matching `scheme_id` or `source_url`
- Alternative: Replace collection on full reindex for small corpora

**Registry / operator manifest:**
```json
{
  "embedding_model_id": "BAAI/bge-small-en-v1.5",
  "run_id": "uuid",
  "collection_name": "mf_faq_chunks",
  "chroma_storage": "local",
  "chroma_persist_path": "data/chroma/",
  "chunk_count": 150,
  "indexed_at": "2024-01-15T09:15:00Z"
}
```

---

## 5. Retrieval Layer

**Implementation:** `runtime/phase_5_retrieval/`

**CLI:** `python -m runtime.phase_5_retrieval "query"`

### 5.1 Query Preprocessing

- Light normalization: lowercase for matching
- Keep scheme names and tickers as entities
- **Scheme resolution:** If user names a scheme, constrain metadata filter `scheme_id` when confidence is high

### 5.2 Retrieval Mechanics

1. **Dense retrieval:** Top-k (20–40) by cosine similarity in local ChromaDB
2. **Metadata filter:** Optional pre-filter by `scheme_id` or `amc`
3. **Re-ranking:** Cross-encoder or lightweight lexical re-rank for table/number-heavy FAQ hits
4. **Merging:** If multiple chunks from same `source_url` score highly, merge text while keeping one citation

### 5.3 Source Selection ("Exactly One Link")

- **Primary rule:** Choose single highest-confidence chunk's `source_url` as citation
- **Conflict rule:** If chunks disagree, prefer newer `fetched_at`, or respond conservatively with scheme URL only

### 5.4 Performance-Related Questions

Per constraints: do not compute or compare returns. Answer with link to indexed scheme page only.

---

## 6. Generation Layer

**Implementation:** `runtime/phase_6_generation/`

**CLI:** `python -m runtime.phase_6_generation "query"`

### 6.1 Prompting Strategy

**System prompt:**
```
You are a factual mutual fund assistant. You answer ONLY objective, 
verifiable questions about mutual fund schemes using the provided context.

RULES:
1. Answer in maximum 3 sentences
2. Include exactly one source citation link (from provided metadata)
3. Add footer: "Last updated from sources: <date>"
4. NEVER provide investment advice or recommendations
5. Use only the CONTEXT; if insufficient, say you cannot find it
6. For advisory questions, refuse politely

Developer instruction: "Use only the CONTEXT; if CONTEXT is insufficient, 
say you cannot find it in the indexed sources and suggest the relevant 
allowlisted scheme URL from metadata if available."
```

**Context Packaging:**
Pass retrieved chunk text with explicit `Source URL: ...` headers so the model does not invent links.

### 6.2 Output Schema (Contract)

| Field | Requirement |
|-------|-------------|
| **Body** | ≤ 3 sentences, factual, no "you should invest" |
| **Citation** | Exactly one URL, matching the selected `source_url` |
| **Footer** | `Last updated from sources: <date>` using corpus or cited document `fetched_at` |

### 6.3 Model Configuration

| Attribute | Value |
|-----------|-------|
| **Provider** | Groq API |
| **Model** | `llama-3.1-8b-instant` (or similar instruction-tuned) |
| **API Key** | `GROQ_API_KEY` env var |
| **Temperature** | Low (0.1–0.3) for determinism |
| **Max Tokens** | 200 |
| **Timeout** | 10 seconds |
| **Response Format** | JSON with `answer`, `citation_url`, `footer` |

**Note:** Embedding model (BAAI/bge-small-en-v1.5, local) and LLM (Groq API) are independent providers.

---

## 7. Refusal & Safety Layer

**Implementation:** `runtime/phase_7_safety/`

**CLI:**
- `python -m runtime.phase_7_safety "query"`
- `python -m runtime.phase_7_safety --route-only "query"`

### 7.1 Advisory / Comparative Queries (Router)

**Detection patterns:**
- "should I", "which is better", "best fund", "recommend"
- Implicit ranking, personal situation ("I am 45…")

**Action:**
- No retrieval for advisory queries
- Or retrieval only for static educational snippet from pre-approved AMFI/SEBI URLs
- Response: Polite refusal + one educational link

### 7.2 Post-Generation Validation

**Programmatic checks:**

| Check | Implementation |
|-------|----------------|
| Sentence count | ≤ 3 (split on `. ? !`) |
| URL validation | Exactly one HTTP(S) URL, on allowlist |
| Forbidden phrases | Regex/keyword lists: "invest in", "you should", "better than", "outperform", "guarantee" |

**On failure:**
- Regenerate once with stricter prompt
- Or fall back to templated safe response with scheme's allowlisted URL

### 7.3 Privacy

**Prohibited data (do not request or store):**
- PAN, Aadhaar
- Account numbers
- OTPs
- Email, phone numbers

**PII Detection (heuristic):**
- PAN: `[A-Z]{5}[0-9]{4}[A-Z]{1}`
- Aadhaar: `[0-9]{4}[ -]?[0-9]{4}[ -]?[0-9]{4}`
- Account: `\d{9,18}`

**Note:** If UI supports "paste your statement text" — out of scope per product spec.

---

## 8. Multi-Thread Chat Architecture

**Implementation:** `runtime/phase_8_threads/`

**CLI:**
- `python -m runtime.phase_8_threads new-thread`
- `python -m runtime.phase_8_threads say "message"`
- `python -m runtime.phase_8_threads history`
- `python -m runtime.phase_8_threads context`
- `python -m runtime.phase_8_threads list-threads`

### 8.1 Thread Model

| Field | Description |
|-------|-------------|
| `thread_id` | Opaque UUID per conversation |
| `session_key` | Anonymous or non-PII session identifier |
| `messages` | Array of `{ role, content, timestamp, retrieval_debug_id }` |

### 8.2 Context Window Policy

- **For factual FAQ:** Full thread history often unnecessary
- **Use last N turns:** 4–6 turns for follow-ups ("What about exit load?")
- **Retrieval query expansion:** Optionally rewrite latest user message using recent history (e.g., "same scheme as before") — without injecting PII

### 8.3 Storage

**Near-term:** SQLite for threads/messages (file-based)

**Production:** Postgres (row per scheme + `fetched_at`, or upsert "current" row per scheme)

### 8.4 Concurrency

- Stateless API servers
- Thread state in DB or durable KV
- Vector store read-only at query time; no cross-thread writes

---

## 9. Application & API Layer

**Implementation:** `runtime/phase_9_api/`

**Run:** `python -m runtime.phase_9_api` (see `PORT` / `API_HOST` in `.env.example`)

### 9.1 Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness check |
| `POST /threads` | Create thread |
| `GET /threads` | List threads |
| `GET /threads/{id}/messages` | List messages |
| `POST /threads/{id}/messages` | User message → pipeline → assistant message |
| `POST /admin/reindex` | Protected re-ingestion trigger (optional) |

### 9.2 Response Payload

```json
{
  "assistant_message": "...",
  "debug": {
    "retrieved_chunks": [...],
    "scores": [...],
    "latency_ms": 1234
  }
}
```

**Note:** Debug info disabled in production (`RUNTIME_API_DEBUG=0`)

### 9.3 Configuration

```bash
# .env
PORT=8000
API_HOST=0.0.0.0
GROQ_API_KEY=gsk_...
ADMIN_REINDEX_SECRET=secret_for_admin_endpoint
RUNTIME_API_DEBUG=1  # Set 0 in production
```

---

## 10. Observability & Quality

### 10.1 Logging

- Query latency
- Retrieval count
- Router decision (factual/advisory/blocked)
- Refusal vs answer rate

**Do not log:** Full message bodies (aggregate metrics only)

### 10.2 Evaluation (Offline)

- **Golden set:** 50–100 Q&A pairs from corpus
- **Metrics:**
  - Citation URL exact match rate
  - Grounding (answer supported by chunk)
  - Refusal precision/recall on advisory prompts

### 10.3 Drift Detection

- Re-crawl alerts when `content_hash` changes for critical allowlisted URLs
- Weekly comparison of structured fund metrics

---

## 11. Technology Stack

| Layer | Choice |
|-------|--------|
| **Scheduled Ingest** | GitHub Actions (schedule + `workflow_dispatch`) |
| **Vector DB** | Chroma — Phase 4.3 (`PersistentClient` on disk under `INGEST_CHROMA_DIR`) |
| **Embeddings** | BAAI/bge-small-en-v1.5 via sentence-transformers (local, 384-dim, 512 max tokens) |
| **LLM** | Groq API for Phase 6 (`GROQ_API_KEY`; model e.g., `llama-3.1-8b-instant`) |
| **Orchestration** | Custom pipeline (LangChain/LlamaIndex optional) |
| **UI** | Next.js (in `web/` directory) |
| **Thread Storage** | SQLite (dev) → Postgres (production) |
| **Raw Data Storage** | Disk / Object store for HTML artifacts |

**Important:** Keep embedding model, chunking parameters, and Chroma collection dimension (384) frozen across index and query for reproducibility.

---

## 12. Known Limitations (Architectural)

| Limitation | Mitigation |
|------------|------------|
| **Stale data** | Answers reflect last crawl; footer date indicates freshness |
| **HTML table variance** | Numeric FAQs sensitive to Groww rendering; PDF ingestion planned |
| **Narrow corpus** | Only indexed schemes answerable; broad questions get refusal + educational link |
| **Router mistakes** | Combine router + post-guards for defense in depth |
| **No real-time market data** | By design — only curated corpus |

---

## 13. Alignment with Deliverables

| Deliverable | Location in Architecture |
|-------------|--------------------------|
| README setup, AMC/schemes, architecture, limitations | This file + `chunking-embedding-architecture.md` + runtime phase implementations |
| Disclaimer snippet | UI + system prompt reinforcement |
| Multi-thread chat | Section 8 + thread API in Section 9 |
| Facts-only + one citation + footer | Sections 5–7 and 6.2 |

---

## 14. Summary

The architecture is a **closed-book RAG system**:

1. **Curated corpus:** 5 Groww HDFC scheme pages (HTML only)
2. **Scheduled refresh:** GitHub Actions at 09:15 IST → scrape → normalize → chunk → embed → local Chroma
3. **Query-time:** Router and retriever constrain what may be said; prompts + post-validation enforce how it is said
4. **Output:** Short, factual, one source link, with compliant refusal paths for advisory requests
5. **Multi-thread:** Durable per-thread history with conservative context use

The system prioritizes **accuracy, provenance, and compliance** over conversational flexibility — ensuring users receive only verified, source-backed financial information.
