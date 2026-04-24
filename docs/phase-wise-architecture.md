# Phase-wise Implementation Architecture

This document breaks down the RAG system implementation into manageable phases with specific deliverables for each phase.

## Phase 1: Project Setup & URL Registry
**Goal:** Establish project structure, dependencies, and curated URL list

### Deliverables:
- [ ] Project directory structure
- [ ] `requirements.txt` / `pyproject.toml` with core dependencies
- [ ] URL registry file (`config/urls.yaml`) with 5 Groww HDFC scheme URLs
- [ ] `.env.example` with environment variable templates
- [ ] `.gitignore` for Python/Node projects
- [ ] Basic README with setup instructions

### Files Created:
```
m1/
├── config/
│   └── urls.yaml
├── data/
│   └── raw/          # Raw HTML storage
├── runtime/
│   └── __init__.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Phase 2: Scraping Service (Phase 4.0)
**Goal:** Fetch and persist raw HTML from allowlisted URLs

### Deliverables:
- [x] `runtime/phase_4_scrape/` module
- [x] HTTP fetcher with rate limiting
- [x] Raw HTML storage to `data/raw/{run_id}/`
- [x] CLI: `python -m runtime.phase_4_scrape`
- [x] Error handling for failed URLs
- [x] Content hash generation

### Files Created:
```
runtime/phase_4_scrape/
├── __init__.py
├── fetcher.py
├── storage.py
└── __main__.py
```

---

## Phase 3: Normalization & Structured Extraction (Phase 4.1)
**Goal:** Clean HTML and extract structured fund metrics

### Deliverables:
- [x] `runtime/phase_4_normalize/` module
- [x] HTML boilerplate stripping (nav, footer, scripts)
- [x] Structured extraction (NAV, expense ratio, minimum SIP, rating, AUM)
- [x] Output: `data/structured/{run_id}/metrics/{scheme_id}.json`
- [x] CLI: `python -m runtime.phase_4_normalize`

### Files Created:
```
runtime/phase_4_normalize/
├── __init__.py
├── parser.py              # GrowwSchemeParser, FundMetrics dataclass
├── storage.py             # StructuredStorage for metrics
└── __main__.py            # CLI entry point
```

---

## Phase 4: Chunking & Embedding (Phase 4.2)
**Goal:** Split content into chunks and generate embeddings

### Deliverables:
- [x] `runtime/phase_4_chunk_embed/` module
- [x] HTML-aware chunking (preserve tables, 300-450 tokens, 10-15% overlap)
- [x] BAAI/bge-small-en-v1.5 embedding (local, 384-dim)
- [x] Output: Chunked JSONL with embeddings
- [x] CLI: `python -m runtime.phase_4_chunk_embed`

### Files Created:
```
runtime/phase_4_chunk_embed/
├── __init__.py
├── chunker.py             # HTMLChunker with semantic splitting
├── embedder.py            # BGEEmbedder (BAAI/bge-small-en-v1.5)
├── storage.py             # ChunkedStorage for JSONL output
└── __main__.py            # CLI entry point
```

---

## Phase 5: Vector Index (Phase 4.3)
**Goal:** Upsert embeddings into local ChromaDB (data/chroma/)

### Deliverables:
- [x] `runtime/phase_4_index/` module
- [x] Local ChromaDB PersistentClient integration
- [x] Local filesystem storage (data/chroma/)
- [x] Upsert with metadata (source_url, scheme_id, fetched_at, etc.)
- [x] Collection: `mf_faq_chunks` (384-dim, cosine similarity)
- [x] CLI: `python -m runtime.phase_4_index`

### Files Created:
```
runtime/phase_4_index/
├── __init__.py
├── chroma_client.py       # ChromaIndex with Local PersistentClient
└── __main__.py            # CLI entry point
```

### Configuration:
```bash
# .env
CHROMA_PERSIST_DIR=data/chroma
INGEST_CHROMA_COLLECTION=mf_faq_chunks
```

---

## Phase 6: Retrieval Layer (Phase 5)
**Goal:** Query the vector store and retrieve relevant chunks

### Deliverables:
- [ ] `runtime/phase_5_retrieval/` module
- [ ] Query embedding with same BGE model
- [ ] Chroma similarity search
- [ ] Metadata filtering (scheme_id, amc)
- [ ] Source selection (single citation URL)
- [ ] CLI: `python -m runtime.phase_5_retrieval "query"`

---

## Phase 7: Generation Layer (Phase 6)
**Goal:** Generate factual answers using Groq API

### Deliverables:
- [ ] `runtime/phase_6_generation/` module
- [ ] Prompt template with context packaging
- [ ] Groq API integration (llama-3.1-8b-instant)
- [ ] Output validation (≤3 sentences, one URL)
- [ ] CLI: `python -m runtime.phase_6_generation "query"`

---

## Phase 8: Safety & Routing (Phase 7)
**Goal:** Advisory detection and refusal handling

### Deliverables:
- [ ] `runtime/phase_7_safety/` module
- [ ] Intent classifier (factual vs advisory)
- [ ] PII detection heuristics
- [ ] Post-generation validation
- [ ] CLI: `python -m runtime.phase_7_safety "query"`

---

## Phase 9: Thread Management (Phase 8)
**Goal:** Multi-thread chat support

### Deliverables:
- [ ] `runtime/phase_8_threads/` module
- [ ] SQLite storage for threads/messages
- [ ] Context window policy (last N turns)
- [ ] CLI commands: new-thread, say, history, list-threads

---

## Phase 10: API Layer (Phase 9)
**Goal:** FastAPI endpoints for production

### Deliverables:
- [ ] `runtime/phase_9_api/` module
- [ ] FastAPI application
- [ ] Endpoints: /health, /threads, /threads/{id}/messages
- [ ] Admin reindex endpoint (protected)
- [ ] CORS, error handling

---

## Phase 11: UI Integration
**Goal:** Next.js frontend

### Deliverables:
- [ ] `web/` Next.js application
- [ ] Chat interface with thread support
- [ ] Disclaimer banner
- [ ] Source link display
- [ ] Environment: `NEXT_PUBLIC_API_URL`

---

## Phase 12: GitHub Actions Scheduler
**Goal:** Automated daily ingestion

### Deliverables:
- [x] `.github/workflows/ingest.yml`
- [x] Cron: `45 3 * * *` (09:15 IST)
- [x] Workflow dispatch for manual runs
- [x] Artifact upload (data/chroma/, logs)
- [x] Secrets configuration documented

---

## Current Status

**Phase 1:** ✅ COMPLETE (Project Setup)  
**Ingestion Pipeline (Phases 4.0-4.3):** ✅ **ALL COMPLETE**
- Phase 4.0: ✅ Scraping Service
- Phase 4.1: ✅ Normalization + Structured Extraction  
- Phase 4.2: ✅ Chunking & Embedding
- Phase 4.3: ✅ Vector Indexing (ChromaDB)

**Query/Runtime Pipeline (Phases 5-12):** ⏸️ PENDING
- Phase 5: Retrieval
- Phase 6: Generation
- Phase 7: Safety
- Phase 8: Threads
- Phase 9: API
- Phase 10-12: UI, GitHub Actions

## In Scope URLs (Phase 1 Definition)

```yaml
# config/urls.yaml
amc: hdfc_mutual_fund
base_url: https://groww.in
schemes:
  - id: hdfc_mid_cap_direct_growth
    name: "HDFC Mid Cap Fund Direct Growth"
    url: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
    category: mid_cap
    
  - id: hdfc_equity_direct_growth
    name: "HDFC Equity Fund Direct Growth"
    url: https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
    category: equity
    
  - id: hdfc_focused_direct_growth
    name: "HDFC Focused Fund Direct Growth"
    url: https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth
    category: focused
    
  - id: hdfc_elss_tax_saver_direct_growth
    name: "HDFC ELSS Tax Saver Fund Direct Plan Growth"
    url: https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
    category: elss
    
  - id: hdfc_large_cap_direct_growth
    name: "HDFC Large Cap Fund Direct Growth"
    url: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
    category: large_cap
```

**Note:** No PDFs in current scope (KIM, SID, factsheets to be added in future corpus expansion).
