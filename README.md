# Mutual Fund FAQ Assistant

A facts-only RAG-based assistant for mutual fund scheme information. Answers factual queries using a curated corpus of official sources while strictly avoiding investment advice.

## Architecture

- **RAG Architecture:** See `docs/ragArchitecture.md`
- **Phase-wise Implementation:** See `docs/phase-wise-architecture.md`

## Current Scope

**AMC:** HDFC Mutual Fund  
**Sources:** 5 Groww scheme pages (HTML only, no PDFs)

| Scheme | Category |
|--------|----------|
| HDFC Mid Cap Fund Direct Growth | Mid Cap |
| HDFC Equity Fund Direct Growth | Equity |
| HDFC Focused Fund Direct Growth | Focused |
| HDFC ELSS Tax Saver Fund Direct Plan Growth | ELSS |
| HDFC Large Cap Fund Direct Growth | Large Cap |

## Quick Start

### 1. Setup Environment

```bash
# Clone and navigate to project
cd m1

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your GROQ_API_KEY and other settings
```

### 2. Configure URLs

Edit `config/urls.yaml` to add/remove schemes. Default includes 5 HDFC schemes from Groww.

### 3. Run Ingestion Pipeline (Full)

```bash
# Phase 4.0: Scrape
python -m runtime.phase_4_scrape

# Phase 4.1: Normalize
python -m runtime.phase_4_normalize

# Phase 4.2: Chunk & Embed
python -m runtime.phase_4_chunk_embed

# Phase 4.3: Index to Chroma
python -m runtime.phase_4_index
```

### 4. Test Query

```bash
# Phase 5-7: Retrieval + Generation + Safety
python -m runtime.phase_7_safety "What is the expense ratio of HDFC Mid Cap Fund?"
```

### 5. Start API Server

```bash
# Phase 9: FastAPI server
python -m runtime.phase_9_api

# Server runs at http://localhost:8000
# Health check: curl http://localhost:8000/health
```

### 6. Start UI (Optional)

```bash
cd web
npm install
npm run dev

# UI runs at http://localhost:3000
```

## Deployment

See detailed deployment guides:
- **Quick Start**: `DEPLOYMENT.md` (30-minute setup)
- **Full Plan**: `docs/deployment-plan.md` (architecture & troubleshooting)

### Deployment Architecture
- **Scheduler**: GitHub Actions (daily ingestion)
- **Backend**: Render (FastAPI + SQLite/ChromaDB)
- **Frontend**: Vercel (Next.js)
- **Automations**: Zapier (optional alerts)

Quick deploy:
```bash
# 1. Deploy backend to Render
# 2. Deploy frontend to Vercel
# 3. Configure GitHub Actions secrets
# See DEPLOYMENT.md for details
```

## Project Structure

```
m1/
├── config/
│   └── urls.yaml              # Curated URL registry (Phase 1)
├── data/
│   ├── raw/                   # Scraped HTML (Phase 4.0)
│   ├── structured/            # Extracted metrics (Phase 4.1)
│   └── chroma/                # Vector store (Phase 4.3)
├── docs/
│   ├── problemStatement.md     # Product requirements
│   ├── ragArchitecture.md        # System architecture
│   ├── phase-wise-architecture.md  # Implementation phases
│   ├── edge-cases.md           # Test scenarios
│   └── deployment-plan.md      # Deployment architecture
├── DEPLOYMENT.md               # Quick deployment guide
├── runtime/                   # All phase implementations
│   ├── phase_4_scrape/       # Phase 4.0: Scraping
│   ├── phase_4_normalize/    # Phase 4.1: Normalization
│   ├── phase_4_chunk_embed/  # Phase 4.2: Chunking & Embedding
│   ├── phase_4_index/        # Phase 4.3: Vector Index
│   ├── phase_5_retrieval/    # Phase 5: Retrieval
│   ├── phase_6_generation/   # Phase 6: LLM Generation
│   ├── phase_7_safety/       # Phase 7: Safety & Routing
│   ├── phase_8_threads/      # Phase 8: Thread Management
│   └── phase_9_api/          # Phase 9: API Layer
├── web/                       # Phase 11: Next.js UI
├── .env.example              # Environment template (Phase 1)
├── .gitignore                # Git ignore rules (Phase 1)
├── requirements.txt          # Python deps (Phase 1)
└── README.md                 # This file (Phase 1)
```

## Environment Variables

### Required for Ingestion (Phases 4.0-4.3)

| Variable | Required | Description |
|----------|----------|-------------|
| `CHROMA_PERSIST_DIR` | No | Local ChromaDB storage path (default: data/chroma) |

### Required for Runtime (Phases 5-9)

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key for LLM generation |
| `ADMIN_REINDEX_SECRET` | Yes | Secret for admin reindex endpoint |
| `PORT` | No | API server port (default: 8000) |
| `RUNTIME_API_DEBUG` | No | Debug mode (default: 1) |

See `.env.example` for complete list.

## ChromaDB Setup (Local)

ChromaDB runs locally - no cloud signup required. Data is stored in `data/chroma/`.

### Local Development
```bash
# Add to .env file (optional - defaults work)
CHROMA_PERSIST_DIR=data/chroma
```

### 3. GitHub Actions (Automated Daily Ingestion)
The scheduler runs daily at **09:15 AM IST** (03:45 UTC) via GitHub Actions.

No cloud secrets required - ChromaDB is local!

## Development Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Complete | Project setup & URL registry |
| 4.0 | ✅ Complete | Scraping service - Daily HTML fetch |
| 4.1 | ✅ Complete | Normalization - Structured extraction |
| 4.2 | ✅ Complete | Chunking & Embedding (BGE-small) |
| 4.3 | ✅ Complete | **Vector Index - Local ChromaDB** |
| 12 | ✅ Complete | GitHub Actions Scheduler (09:15 AM IST) |
| 5 | ⏸️ Pending | Retrieval Layer |
| 6 | ⏸️ Pending | LLM Generation |
| 7 | ⏸️ Pending | Safety & Routing |
| 8 | ⏸️ Pending | Thread Management |
| 9 | ⏸️ Pending | API Layer |
| 11 | ⏸️ Pending | Next.js UI |

## Constraints

- **Facts-only:** No investment advice, recommendations, or comparisons
- **One citation per answer:** Single source URL with "Last updated from sources" footer
- **Max 3 sentences per response**
- **No PII:** PAN, Aadhaar, account numbers blocked
- **No real-time data:** Reflects last crawl date

## License

MIT
