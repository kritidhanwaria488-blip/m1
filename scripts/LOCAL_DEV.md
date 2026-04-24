# Local Development Guide

Quickly start both backend and frontend for local testing.

---

## Quick Start

### Option 1: Windows (Batch Script)

```powershell
# From project root
scripts\start-local.bat
```

What it does:
1. Checks prerequisites
2. Starts backend (http://localhost:8000)
3. Waits 5 seconds
4. Starts frontend (http://localhost:3000)
5. Opens browser automatically
6. Press any key to stop all services

---

### Option 2: Cross-Platform (Python Script)

```bash
# Windows
python scripts\start_local.py

# Linux/macOS
python3 scripts/start_local.py
```

What it does:
1. Checks Python/Node dependencies
2. Installs frontend deps if needed
3. Starts backend and waits for health check
4. Starts frontend
5. Opens browser after 3 seconds
6. Press Ctrl+C to stop gracefully

---

## Manual Start (If Scripts Don't Work)

### Terminal 1: Backend
```bash
cd c:\Users\Kriti\CascadeProjects\m1
python -m runtime.phase_9_api

# Server runs at: http://localhost:8000
```

### Terminal 2: Frontend
```bash
cd c:\Users\Kriti\CascadeProjects\m1\web
npm install  # First time only
npm run dev

# Frontend runs at: http://localhost:3000
```

### Browser
Open: http://localhost:3000

---

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend UI | http://localhost:3000 | Next.js chat interface |
| Backend API | http://localhost:8000 | FastAPI server |
| API Docs | http://localhost:8000/docs | Swagger UI (interactive) |
| Health Check | http://localhost:8000/health | System status |

---

## Testing the API

### Using curl
```bash
# Health check
curl http://localhost:8000/health

# Create a thread
curl -X POST http://localhost:8000/threads \
  -H "Content-Type: application/json" \
  -d '{"session_key": "test_user"}'

# Send a message (replace {thread_id})
curl -X POST http://localhost:8000/threads/{thread_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "What is HDFC ELSS expense ratio?"}'
```

### Using Browser
1. Open: http://localhost:8000/docs
2. Click "Try it out"
3. Test endpoints interactively

---

## Prerequisites Check

### Python
```bash
# Check Python version
python --version  # Should be 3.8+

# Check dependencies installed
python -c "import fastapi, chromadb, sentence_transformers; print('✅ All installed')"
```

### Node.js
```bash
# Check Node version
node --version  # Should be 18+

# Check npm
npm --version
```

### Environment Variables
```bash
# Check .env exists
ls .env  # Linux/macOS
dir .env  # Windows

# Required variables:
# GROQ_API_KEY=your_key_here (optional for local testing)
```

---

## Common Issues

### Port Already in Use

**Error**: `Address already in use`

**Solution**:
```bash
# Find and kill process on port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS:
lsof -ti:8000 | xargs kill -9
```

### Backend Won't Start

**Check**:
1. `.env` file exists
2. `pip install -r requirements.txt` completed
3. ChromaDB directory exists: `data/chroma/`

### Frontend Won't Start

**Check**:
1. `cd web && npm install` completed
2. No errors in `npm run build`
3. Backend is running on port 8000

### API Connection Errors

**Check**:
1. Backend URL in `web/lib/api.ts`:
   ```typescript
   const API_BASE_URL = 'http://localhost:8000';
   ```
2. `next.config.js` has correct rewrites
3. No firewall blocking localhost

---

## Troubleshooting Commands

```bash
# Check what's running on ports
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # macOS
ss -tlnp | grep 8000          # Linux

# Test backend health
curl http://localhost:8000/health

# Test ChromaDB
cd c:\Users\Kriti\CascadeProjects\m1
python -c "import chromadb; c = chromadb.PersistentClient('data/chroma'); print(f'{c.get_collection(\"mf_faq_chunks\").count()} docs')"

# View backend logs (if running manually)
# Just look at the terminal where you started it
```

---

## Stopping Services

### If Using Scripts
- **Batch script**: Press any key in the terminal
- **Python script**: Press Ctrl+C

### If Running Manually
- **Terminal 1** (backend): Press Ctrl+C
- **Terminal 2** (frontend): Press Ctrl+C

### If Stuck
```bash
# Kill all Node processes
killall node  # Linux/macOS
taskkill /F /IM node.exe  # Windows

# Kill Python processes
killall python  # Linux/macOS
taskkill /F /IM python.exe  # Windows
```

---

## Development Workflow

1. **Start services**: `python scripts/start_local.py`
2. **Make changes** to code
3. **Frontend hot-reload**: Changes appear immediately
4. **Backend changes**: Need to restart (Ctrl+C, then restart)
5. **Test**: http://localhost:3000
6. **Stop**: Ctrl+C

---

## One-Liner Test

```bash
# Full stack test (run from project root)
python scripts/start_local.py &
sleep 10
curl -s http://localhost:8000/health | grep -q "healthy" && echo "✅ Backend OK"
curl -s http://localhost:3000 | grep -q "MF FAQ" && echo "✅ Frontend OK"
```

---

## Next Steps

After local testing works:
1. See `DEPLOYMENT.md` for production deployment
2. Or check `docs/deployment-plan.md` for full architecture

---

*Happy developing! 🚀*
