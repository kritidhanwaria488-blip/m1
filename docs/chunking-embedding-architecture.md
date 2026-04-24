# Chunking & Embedding Architecture

This document describes the chunking and embedding pipeline (Phase 4.2) for the Mutual Fund FAQ Assistant. It details how HTML content is split into chunks and converted to vector embeddings using the BAAI/bge-small-en-v1.5 model.

---

## 1. Overview

The chunking and embedding phase transforms cleaned HTML content into searchable vector representations. This phase runs as part of the daily scheduled ingestion pipeline (triggered at 09:15 AM IST via GitHub Actions).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CHUNKING & EMBEDDING PIPELINE (Phase 4.2)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                 │
│  │   Normalized │────▶│   HTML       │────▶│   Semantic   │                 │
│  │   HTML       │     │   Chunker    │     │   Chunks     │                 │
│  │   (Input)    │     │              │     │   (300-450   │                 │
│  └──────────────┘     └──────────────┘     │   tokens)    │                 │
│                                             └──────┬───────┘                 │
│                                                    │                         │
│                          ┌─────────────────────────┘                         │
│                          ▼                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                 │
│  │   Chunked    │◀────│   BGE        │◀────│   BAAI/      │                 │
│  │   Output     │     │   Embedder   │     │   bge-small- │                 │
│  │   (JSONL)    │     │   (384-dim)  │     │   en-v1.5    │                 │
│  └──────────────┘     └──────────────┘     └──────────────┘                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Input Specification

### 2.1 Source Data

| Attribute | Value |
|-----------|-------|
| **Source** | Normalized HTML from Phase 4.1 |
| **Location** | `data/structured/{run_id}/normalized/` |
| **Format** | Cleaned HTML (boilerplate removed) |
| **Content** | Scheme pages from Groww (5 URLs) |

### 2.2 Input Schema

```json
{
  "scheme_id": "hdfc_mid_cap_direct_growth",
  "scheme_name": "HDFC Mid Cap Fund Direct Growth",
  "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
  "amc": "hdfc_mutual_fund",
  "source_type": "groww_scheme_page",
  "fetched_at": "2024-01-15T09:15:00+05:30",
  "content_hash": "sha256_hash",
  "html_content": "<html>...</html>",
  "structured_data": {
    "nav": 125.67,
    "expense_ratio": 0.52,
    "minimum_sip": 500,
    "fund_size": 28500
  }
}
```

---

## 3. Chunking Strategy

### 3.1 HTML-Aware Chunking

Since the corpus consists of Groww scheme pages (HTML tables, sections, headings), we use semantic chunking that respects document structure.

#### Chunk Boundaries

| Boundary Type | Rule |
|---------------|------|
| **Heading splits** | Split on `<h1>`, `<h2>`, `<h3>` tags |
| **Section breaks** | Split on `<section>`, `<div class="...">` with semantic classes |
| **Table preservation** | Keep entire tables as single chunks where possible |
| **Paragraph breaks** | Split on `<p>` when content exceeds target size |

#### Special Handling for Tables

Tables contain critical numeric data (expense ratios, NAV, SIP amounts):

```python
# Table chunking rules
TABLE_CHUNK_RULES = {
    "preserve_whole": True,      # Keep small tables intact
    "max_rows_per_chunk": 50,    # Split large tables by row groups
    "include_headers": True,      # Always include column headers
    "metadata_tags": ["expense", "performance", "holding"]
}
```

### 3.2 Token-Based Sizing

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Target chunk size** | 300-450 tokens | Balances granularity with context |
| **Maximum tokens** | 512 | Hard limit for BGE model |
| **Overlap** | 10-15% (~40-60 tokens) | Preserve context at boundaries |
| **Minimum chunk size** | 100 tokens | Discard very small fragments |

### 3.3 Chunk Types

| Type | Description | Example Content |
|------|-------------|-----------------|
| **Overview** | Fund description, objective | "This fund invests predominantly in mid-cap stocks..." |
| **Metrics Table** | Numeric data in tabular form | Expense ratio, NAV, AUM table |
| **Performance** | Returns, benchmarks | "1-year return: 15.2%, benchmark: Nifty Midcap 100" |
| **Details** | Exit load, SIP minimums | "Exit load: 1% for redemption within 1 year" |
| **Risk** | Riskometer, disclaimer | "Very High risk, suitable for long-term investors" |

### 3.4 Metadata Attachment

Each chunk inherits and extends metadata from the source:

```json
{
  "chunk_id": "hdfc_mid_cap_direct_growth_003_expense",
  "scheme_id": "hdfc_mid_cap_direct_growth",
  "scheme_name": "HDFC Mid Cap Fund Direct Growth",
  "amc": "hdfc_mutual_fund",
  "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
  "source_type": "groww_scheme_page",
  "fetched_at": "2024-01-15T09:15:00+05:30",
  "content_hash": "sha256_of_parent_html",
  "chunk_index": 3,
  "section_title": "Expense Ratio & Fees",
  "chunk_type": "metrics_table",
  "token_count": 412,
  "text": "The expense ratio for HDFC Mid Cap Fund Direct Growth is 0.52% per annum..."
}
```

---

## 4. Embedding Model

### 4.1 Model Specification

| Attribute | Value |
|-----------|-------|
| **Model** | `BAAI/bge-small-en-v1.5` |
| **Provider** | Hugging Face (local inference) |
| **Dimensions** | 384 |
| **Max sequence length** | 512 tokens |
| **Architecture** | BERT-based transformer |

### 4.2 Why BGE-small-en-v1.5?

| Factor | Rationale |
|--------|-----------|
| **Size** | Small (~50MB) enables fast local inference |
| **Quality** | Strong performance on semantic similarity tasks |
| **Cost** | Zero API cost (runs on GitHub Actions runner) |
| **Reproducibility** | Fixed model version ensures consistent embeddings |
| **Context** | 512 tokens sufficient for our chunk sizes |

### 4.3 Query vs Document Embeddings

BGE models benefit from query prefixes for asymmetric retrieval:

```python
# Document chunk (index time)
doc_embedding = model.encode(chunk_text)  # No prefix

# Query (search time)
query_embedding = model.encode(
    "Represent this sentence for searching relevant passages: " + query_text
)
```

**Note:** Both use the same model; only the query gets the instruction prefix.

---

## 5. Implementation Details

### 5.1 Pipeline Flow

```python
# Phase 4.2 execution flow
def chunk_and_embed(run_id: str):
    # 1. Load normalized HTML from Phase 4.1
    normalized_files = load_normalized(run_id)
    
    # 2. Initialize BGE model (cached)
    model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    
    # 3. Process each scheme
    for file in normalized_files:
        html_content = file["html_content"]
        metadata = file["metadata"]
        
        # 4. Parse and chunk HTML
        chunks = chunk_html(html_content, metadata)
        
        # 5. Embed chunks
        for chunk in chunks:
            chunk["embedding"] = model.encode(chunk["text"]).tolist()
        
        # 6. Write to JSONL
        write_chunked_jsonl(chunks, run_id)
```

### 5.2 Directory Structure

```
data/
├── raw/{run_id}/              # Phase 4.0 output
├── structured/{run_id}/
│   ├── normalized/            # Phase 4.1 output (clean HTML)
│   └── chunked/               # Phase 4.2 output (this phase)
│       ├── hdfc_mid_cap_direct_growth.jsonl
│       ├── hdfc_equity_direct_growth.jsonl
│       ├── hdfc_focused_direct_growth.jsonl
│       ├── hdfc_elss_tax_saver_direct_growth.jsonl
│       ├── hdfc_large_cap_direct_growth.jsonl
│       └── manifest.json      # Run metadata
└── chroma/                    # Phase 4.3 output (vector DB)
```

### 5.3 Output Format (JSONL)

Each line is a JSON object representing one chunk:

```json
{
  "chunk_id": "hdfc_mid_cap_direct_growth_003_expense",
  "scheme_id": "hdfc_mid_cap_direct_growth",
  "scheme_name": "HDFC Mid Cap Fund Direct Growth",
  "amc": "hdfc_mutual_fund",
  "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
  "source_type": "groww_scheme_page",
  "fetched_at": "2024-01-15T09:15:00+05:30",
  "content_hash": "abc123...",
  "chunk_index": 3,
  "section_title": "Expense Ratio & Fees",
  "chunk_type": "metrics_table",
  "token_count": 412,
  "text": "The expense ratio for HDFC Mid Cap Fund Direct Growth is 0.52% per annum as of January 2024...",
  "embedding": [0.0234, -0.0156, 0.0891, ...]  // 384 dimensions
}
```

### 5.4 Manifest File

```json
{
  "run_id": "2024-01-15-091500",
  "phase": "4.2",
  "embedding_model": "BAAI/bge-small-en-v1.5",
  "embedding_dim": 384,
  "chunking_strategy": "html_semantic",
  "target_chunk_tokens": 375,
  "overlap_percent": 12,
  "files": [
    {
      "scheme_id": "hdfc_mid_cap_direct_growth",
      "chunks": 12,
      "file": "hdfc_mid_cap_direct_growth.jsonl"
    },
    ...
  ],
  "total_chunks": 58,
  "processed_at": "2024-01-15T09:18:23+05:30"
}
```

---

## 6. Idempotency & Change Detection

### 6.1 Content Hashing

Each chunk's `content_hash` enables idempotent operations:

```python
import hashlib

# Generate deterministic chunk ID
chunk_id = f"{scheme_id}_{index:03d}_{section_type}"

# Detect if chunk content changed
chunk_hash = hashlib.sha256(chunk_text.encode()).hexdigest()[:16]
```

### 6.2 Incremental Processing

On re-runs (scheduled or manual), the pipeline:

1. Compares `content_hash` of input HTML
2. If unchanged → skip re-chunking, use existing output
3. If changed → re-chunk and re-embed only that scheme
4. Updates manifest with new/updated chunk records

---

## 7. Performance Characteristics

| Metric | Target | Notes |
|--------|--------|-------|
| **Chunking speed** | 10-20 schemes/second | CPU-bound, single-threaded |
| **Embedding speed** | ~100 chunks/second | On GitHub Actions runner (2-core) |
| **Total time (5 schemes)** | < 2 minutes | Including I/O |
| **Memory usage** | < 2 GB | Model + batch processing |
| **Output size** | ~50-100 KB per scheme | JSONL with embeddings |

---

## 8. CLI Interface

### 8.1 Command

```bash
python -m runtime.phase_4_chunk_embed [OPTIONS]
```

### 8.2 Options

| Option | Default | Description |
|--------|---------|-------------|
| `--run-id` | Auto-generated | Identifier for this run (YYYY-MM-DD-HHMMSS) |
| `--input-dir` | `data/structured/{run_id}/normalized/` | Source normalized HTML |
| `--output-dir` | `data/structured/{run_id}/chunked/` | Destination for JSONL |
| `--model` | `BAAI/bge-small-en-v1.5` | Embedding model (frozen) |
| `--chunk-size` | 375 | Target tokens per chunk |
| `--overlap` | 0.12 | Overlap percentage (0-1) |
| `--batch-size` | 32 | Embedding batch size |

### 8.3 Example

```bash
# Standard run (part of scheduled pipeline)
python -m runtime.phase_4_chunk_embed --run-id 2024-01-15-091500

# Custom chunk size for testing
python -m runtime.phase_4_chunk_embed --chunk-size 300 --overlap 0.15
```

---

## 9. Error Handling

| Scenario | Handling |
|----------|----------|
| **Empty HTML input** | Log warning, skip scheme, continue |
| **Chunk exceeds 512 tokens** | Truncate with ellipsis, log warning |
| **Embedding failure** | Retry once, then mark chunk as failed |
| **Out of memory** | Reduce batch size, retry |
| **Model download failure** | Exit with error code (blocks pipeline) |

---

## 10. Integration with GitHub Actions

The chunking/embedding phase runs automatically as part of the scheduled workflow:

```yaml
# .github/workflows/ingest.yml (excerpt)
jobs:
  ingest:
    runs-on: ubuntu-latest
    steps:
      # ... previous phases ...
      
      - name: Phase 4.2 - Chunk and Embed
        run: python -m runtime.phase_4_chunk_embed --run-id ${{ github.run_id }}
        
      - name: Upload chunked artifacts
        uses: actions/upload-artifact@v4
        with:
          name: chunked-data
          path: data/structured/*/chunked/
```

---

## 11. Alignment with RAG Architecture

This chunking/embedding architecture implements **Phase 4.2** of the main RAG architecture:

| RAG Phase | This Document |
|-----------|---------------|
| Phase 4.2 (Chunk + Embed) | Sections 3-5 (Chunking, Embedding, Implementation) |
| Phase 4.3 (Index) | Output feeds into ChromaDB indexing |
| Phase 5 (Retrieval) | Uses embeddings generated here |

The 384-dimensional embeddings produced here are query-compatible with the same BGE model configuration used at retrieval time.

---

## Summary

The chunking and embedding pipeline transforms normalized HTML into searchable vector chunks using:

- **Semantic HTML chunking** that preserves tables and sections
- **BAAI/bge-small-en-v1.5** for local, cost-free 384-dimensional embeddings
- **Token-based sizing** (300-450 tokens) with 10-15% overlap
- **Rich metadata** linking chunks to source URLs for citation
- **Idempotent processing** via content hashing
- **GitHub Actions integration** as part of daily 09:15 AM IST scheduled runs

This ensures the RAG system has fresh, accurately chunked, and consistently embedded content for factual mutual fund queries.
