# Quick Deployment Guide

Get the MF FAQ Assistant deployed in 30 minutes.

## Overview

| Component | Platform | URL Pattern | Status |
|-----------|----------|-------------|--------|
| Backend API | Render | `*.onrender.com` | 🚀 Deploy |
| Scheduler | Render (Cron) | N/A | 🚀 Deploy |
| Frontend | Vercel | `*.vercel.app` | 🚀 Deploy |
| Automations | Zapier | N/A | ⏳ Optional |

### Architecture
Both backend AND scheduler run on **Render** sharing the same disk:
- Web Service: FastAPI API endpoints
- Cron Job: Daily ingestion at 09:15 AM IST
- Shared Disk: ChromaDB + SQLite (immediately accessible)

---

## Step 1: Deploy Backend + Scheduler (Render) - 15 min

### 1.1 Create Account
- Go to https://dashboard.render.com
- Sign up with GitHub

### 1.2 Deploy with Blueprint (Recommended)
Your repo has `render.yaml` that deploys BOTH services:

1. Click "New +" → "Blueprint"
2. Connect your GitHub repository (`kritidhanwaria488-blip/m1`)
3. Render will detect `render.yaml` and create TWO services:
   - **Web Service**: FastAPI backend
   - **Cron Job**: Daily ingestion scheduler

### 1.3 Upgrade to Starter Plan
Cron jobs require paid plan:
1. Go to Dashboard → Settings
2. Change plan to "Starter" ($7/month)
3. This enables both web service AND cron job

### 1.4 Configure Environment Variables
Add to BOTH services (same values):
```
GROQ_API_KEY=gsk_your_key_here
ADMIN_REINDEX_SECRET=your_secure_random_string
THREAD_DB_PATH=/opt/render/project/src/data/threads.db
CHROMA_PERSIST_DIR=/opt/render/project/src/data/chroma
RUNTIME_API_DEBUG=0
```

**Important**: Use the SAME `ADMIN_REINDEX_SECRET` for both!

### 1.5 Verify Deployment

**Web Service**: Visit `https://[service].onrender.com/health`

**Cron Job**: 
1. Go to Cron Job in Dashboard
2. Click "Run Job" (manual trigger)
3. Wait for completion (~2 minutes)
4. Check logs: should show "251 chunks indexed"

### 1.6 Verify Shared Disk
Both services share disk at `/opt/render/project/src/data/`:
- `data/chroma/` - ChromaDB (251 documents)
- `data/threads.db` - SQLite
- `data/logs/` - Scheduler logs

**Architecture**:
```
Render Dashboard
├── mf-faq-assistant (Web Service) ◀── API queries
│                                    │
├── mf-faq-scheduler (Cron Job)      │
│   Runs daily at 09:15 AM IST       │
│                                    │
└── Shared Disk: mf-data (1GB) ──────┘
    ├── data/chroma/ (ChromaDB)
    └── data/threads.db (SQLite)
```

---

## Step 2: Deploy Frontend (Vercel) - 10 min

### 2.1 Prepare
```bash
cd web
npm install
npm run build  # Verify builds locally
```

### 2.2 Update API URL
Edit `web/lib/api.ts`:
```typescript
const API_BASE_URL = 'https://[your-render-service].onrender.com';
```

### 2.3 Deploy
```bash
npm i -g vercel
vercel --prod
```

Or use GitHub integration:
1. Push `web/` folder to GitHub
2. Import at https://vercel.com/new
3. Framework: Next.js
4. Root Directory: `web`

### 2.4 Set Environment Variable
In Vercel Dashboard:
```
NEXT_PUBLIC_API_URL=https://[your-render-service].onrender.com
```

**Verify**: Visit your Vercel URL

---

## Step 3: Verify Scheduler is Working - 2 min

The scheduler is already configured in `render.yaml`!

### 3.1 Check Cron Job Schedule
- Go to Render Dashboard → mf-faq-scheduler
- Verify schedule: `45 3 * * *` (09:15 AM IST)

### 3.2 View Logs
After first run, check:
```
Render Dashboard → mf-faq-scheduler → Logs
```

You should see:
```
[PASS] | 4.0_scrape           |  10.23s
[PASS] | 4.1_normalize        |   5.12s
[PASS] | 4.2_chunk_embed      |  52.45s
[PASS] | 4.3_index            |   2.89s
Total Duration: 70.69s
Overall Status: [SUCCESS]
```

### 3.3 Verify Data in API
```bash
curl https://[your-service].onrender.com/health
```
Response should show retriever as "ready" with ChromaDB accessible.

---

## Step 4: Optional - Zapier Automations - 5 min

### 4.1 Failure Alert
**Zap**: GitHub Actions Failure → Email/Slack
```
Trigger: GitHub → Workflow Run (failed)
Filter: workflow = "Daily Ingestion Pipeline"
Action: Email/Slack notification
```

### 4.2 Daily Summary
**Zap**: Schedule → API Stats → Email
```
Trigger: Schedule (daily 10 AM IST)
Action: Webhook → GET /health
Action: Email with stats
```

---

## URLs After Deployment

| Component | URL | What to Check |
|-----------|-----|---------------|
| Backend Health | `https://[service].onrender.com/health` | All components "ready" |
| API Docs | `https://[service].onrender.com/docs` | OpenAPI schema |
| Frontend | `https://[project].vercel.app` | Chat interface works |

---

## Quick Tests

### Test Backend
```bash
curl https://[service].onrender.com/health
```

### Test Frontend
1. Open Vercel URL
2. Create new thread
3. Send test message: "What is HDFC ELSS expense ratio?"
4. Verify response with citation

### Test Scheduler
1. Go to GitHub → Actions
2. Trigger workflow manually
3. Wait for completion
4. Verify ChromaDB count updated

---

## Troubleshooting

### Backend won't start
- Check Render logs
- Verify `requirements.txt` has all dependencies
- Ensure `PORT` env var is set

### Frontend API errors
- Check `NEXT_PUBLIC_API_URL` is correct
- Verify backend is running
- Check CORS in browser console

### Scheduler fails
- Check GitHub Actions logs
- Verify secrets are set
- Test phases locally first

---

## Next Steps

1. ⭐ Star the repository
2. 🔧 Customize `config/urls.yaml` for your schemes
3. 📊 Monitor usage in Render/Vercel dashboards
4. 🔔 Set up Zapier alerts for failures

---

## Support

- Render docs: https://render.com/docs
- Vercel docs: https://vercel.com/docs
- Zapier docs: https://zapier.com/platform
- Project docs: See `docs/deployment-plan.md`

---

**Deploy in this order: Render → Vercel → GitHub Actions → Zapier**

**Total time: ~30 minutes**
