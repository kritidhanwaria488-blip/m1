# Local Ingestion Pipeline Scheduler

Simulates the GitHub Actions daily ingestion pipeline locally. Runs all phases in sequence with comprehensive logging.

## Quick Start

### Windows (PowerShell/CMD)
```powershell
# Run with auto-generated run ID
scripts\run_scheduler.bat

# Run with verbose logging
scripts\run_scheduler.bat --verbose

# Run with custom run ID
scripts\run_scheduler.bat --run-id 20240424-180000
```

### Linux/macOS (Bash)
```bash
# Make executable (first time only)
chmod +x scripts/run_scheduler.sh

# Run with auto-generated run ID
./scripts/run_scheduler.sh

# Run with verbose logging
./scripts/run_scheduler.sh --verbose

# Run with custom run ID
./scripts/run_scheduler.sh --run-id 20240424-180000
```

### Python (Cross-platform)
```bash
# Run the Python script directly
python scripts/local_scheduler.py

# With options
python scripts/local_scheduler.py --verbose
python scripts/local_scheduler.py --run-id 20240424-180000 --verbose
```

## What It Does

The scheduler runs all ingestion phases in sequence:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Phase     │───▶│   Phase     │───▶│   Phase     │───▶│   Phase     │
│   4.0       │    │   4.1       │    │   4.2       │    │   4.3       │
│   Scrape    │    │  Normalize  │    │Chunk & Embed│    │    Index    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                   │                  │                  │
      ▼                   ▼                  ▼                  ▼
data/raw/         data/structured/    data/structured/       data/chroma/
  {run_id}/          {run_id}/           {run_id}/         (Local DB)
                   /normalized         /chunked
```

## Pipeline Phases

### Phase 4.0: Scrape
- **Input**: `config/urls.yaml` (URL registry)
- **Output**: `data/raw/{run_id}/`
- **Actions**:
  - Fetches HTML from all URLs
  - Computes content hashes
  - Creates scrape manifest

### Phase 4.1: Normalize
- **Input**: `data/raw/{run_id}/`
- **Output**: `data/structured/{run_id}/normalized/`
- **Actions**:
  - Extracts structured data from HTML
  - Normalizes metrics (expense ratio, NAV, etc.)
  - Creates normalized JSON files

### Phase 4.2: Chunk & Embed
- **Input**: `data/structured/{run_id}/normalized/`
- **Output**: `data/structured/{run_id}/chunked/`
- **Actions**:
  - Splits HTML into semantic chunks
  - Generates BGE embeddings (384-dim)
  - Creates chunked manifest

### Phase 4.3: Index
- **Input**: `data/structured/{run_id}/chunked/`
- **Output**: `data/chroma/` (Local ChromaDB)
- **Actions**:
  - Upserts chunks to local ChromaDB
  - Updates collection metadata
  - Creates index manifest

## Log Files

### Location
All logs are saved to `logs/` directory:

```
logs/
├── scheduler_YYYYMMDD-HHMMSS.log     # Detailed execution log
├── results_YYYYMMDD-HHMMSS.json    # Structured results
└── ...
```

### Log Format
```
2024-04-24 18:15:32 | INFO     | ============================================
2024-04-24 18:15:32 | INFO     |   PHASE 4.0: SCRAPE URLS
2024-04-24 18:15:32 | INFO     | ============================================
2024-04-24 18:15:32 | INFO     | --- Running Phase 4.0 (Scrape) ---
2024-04-24 18:15:32 | INFO     | Command: python -m runtime.phase_4_scrape ...
2024-04-24 18:15:45 | INFO     | STDOUT:
2024-04-24 18:15:45 | INFO     | Starting scrape...
2024-04-24 18:15:45 | INFO     | Fetched: https://groww.in/...
2024-04-24 18:15:52 | INFO     | ✅ Phase 4.0 (Scrape) completed in 17.34s
```

### Log Levels
- **INFO**: General progress, phase start/end
- **WARNING**: Non-critical issues (stderr output, missing optional data)
- **ERROR**: Phase failures, critical issues
- **DEBUG**: Detailed output (with `--verbose` flag)

## Results JSON

After each run, a JSON file is created with structured results:

```json
{
  "run_id": "20240424-181532",
  "timestamp": "2024-04-24T18:15:32+00:00",
  "phases": {
    "4.0_scrape": {
      "success": true,
      "duration": 17.34,
      "output_preview": "Starting scrape..."
    },
    "4.1_normalize": {
      "success": true,
      "duration": 3.21,
      "output_preview": "Normalized 5 schemes..."
    },
    "4.2_chunk_embed": {
      "success": true,
      "duration": 45.67,
      "output_preview": "Created 251 chunks..."
    },
    "4.3_index": {
      "success": true,
      "duration": 8.92,
      "output_preview": "Indexed 251 chunks..."
    }
  },
  "success": true,
  "total_duration": 75.14,
  "final_collection_count": 251
}
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Pipeline completed successfully |
| 1 | One or more phases failed |
| 130 | Interrupted by user (Ctrl+C) |

## Common Issues

### Phase 4.0 Fails: Network Error
```
❌ Phase 4.0 (Scrape) failed with code 1
Error: Connection timeout
```
**Solution**: Check internet connection, retry later

### Phase 4.2 Fails: Model Download
```
❌ Phase 4.2 (Chunk & Embed) failed
Error: Failed to download BGE model
```
**Solution**: Check HuggingFace connectivity, verify disk space

### Phase 4.3 Fails: Collection Exists
```
❌ Phase 4.3 (Index) failed
Error: Collection dimension mismatch
```
**Solution**: Clear existing ChromaDB or use different collection name

## Verification

After successful run, verify data:

```python
import chromadb

client = chromadb.PersistentClient(path="data/chroma")
collection = client.get_collection("mf_faq_chunks")
print(f"Collection has {collection.count()} documents")
# Expected: Collection has 251 documents
```

Or check the summary at end of log:
```
✅ PASS | 4.0_scrape           |  17.34s
✅ PASS | 4.1_normalize        |   3.21s
✅ PASS | 4.2_chunk_embed      |  45.67s
✅ PASS | 4.3_index            |   8.92s

Total Duration: 75.14s
Overall Status: ✅ SUCCESS
```

## Troubleshooting

### View Live Logs
```bash
# Windows PowerShell
tail -f logs/scheduler_20240424-*.log

# Linux/macOS
tail -f logs/scheduler_20240424-*.log
```

### Check Phase Output
```bash
# Check raw data
ls -la data/raw/20240424-*/

# Check structured data
ls -la data/structured/20240424-*/normalized/

# Check chunks
ls -la data/structured/20240424-*/chunked/

# Check ChromaDB
ls -la data/chroma/
```

### Re-run Single Phase
```bash
# Example: Re-run only indexing
python -m runtime.phase_4_index \
  --run-id 20240424-181532 \
  --input-dir data/structured \
  --collection mf_faq_chunks \
  --persist-dir data/chroma \
  --verbose
```

## Schedule Daily Runs

### Windows Task Scheduler
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily at 09:15 AM
4. Action: Start Program
5. Program: `scripts\run_scheduler.bat`
6. Working directory: `c:\Users\Kriti\CascadeProjects\m1`

### Linux Cron
```bash
# Edit crontab
crontab -e

# Add line (runs at 9:15 AM daily)
15 9 * * * cd /path/to/m1 && ./scripts/run_scheduler.sh >> logs/cron.log 2>&1
```

### macOS LaunchAgent
Create `~/Library/LaunchAgents/com.mfassistant.scheduler.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" 
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mfassistant.scheduler</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/m1/scripts/run_scheduler.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>15</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>/path/to/m1</string>
</dict>
</plist>
```

Load: `launchctl load ~/Library/LaunchAgents/com.mfassistant.scheduler.plist`

## GitHub Actions Comparison

| Feature | GitHub Actions | Local Scheduler |
|---------|---------------|-----------------|
| Schedule | Cron: `45 3 * * *` | Manual or local cron |
| Logs | GitHub UI | Local files in `logs/` |
| Artifacts | GitHub Artifacts | Local files |
| Secrets | GitHub Secrets | `.env` file |
| Notifications | GitHub/Email | Console output |
| Parallel Jobs | Yes | Sequential |

The local scheduler is perfect for:
- Testing pipeline changes
- Debugging phase failures
- Initial data population
- Offline development

GitHub Actions is for:
- Production daily runs
- Team collaboration
- Automated scheduling
- Audit trail
