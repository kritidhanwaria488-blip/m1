# Deployment Plan

Complete deployment strategy for the Mutual Fund FAQ Assistant with automated scheduling, hosted backend, and modern frontend.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   GitHub        │     │    Render       │     │    Vercel       │
│   Actions       │────▶│   (Backend)     │◀────│   (Frontend)    │
│  (Scheduler)    │     │  FastAPI + DB   │     │   Next.js       │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
         │                         │
         │    Daily Ingestion      │   API Queries
         │    (09:15 AM IST)       │   (Real-time)
         │                         │
         ▼                         ▼
┌──────────────────────────────────────────────┐
│              Local ChromaDB                    │
│         (PersistentClient)                   │
│              data/chroma/                      │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│              SQLite Database                   │
│         (Thread Storage)                       │
│           data/threads.db                      │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│              Zapier (Optional)                 │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│    │ Failure  │  │  Daily   │  │  Slack   │  │
│    │  Alerts  │  │ Summary  │  │  Notify  │  │
│    └──────────┘  └──────────┘  └──────────┘  │
└──────────────────────────────────────────────┘
```

---

## 1. GitHub Actions (Scheduler)

**Purpose**: Daily automated ingestion pipeline
**Schedule**: 09:15 AM IST (03:45 UTC) daily
**Product**: GitHub Actions (Free tier: 2,000 minutes/month)

### Configuration

Already configured in `.github/workflows/ingest.yml`:

```yaml
name: Daily Ingestion Pipeline
on:
  schedule:
    - cron: '45 3 * * *'  # 03:45 UTC = 09:15 IST
  workflow_dispatch:       # Manual trigger
```

### Required Secrets

Add these to GitHub repository (Settings → Secrets → Actions):

| Secret | Value | Purpose |
|--------|-------|---------|
| `GROQ_API_KEY` | `gsk_...` | LLM generation (optional for ingestion) |
| `ADMIN_REINDEX_SECRET` | random string | Admin endpoint protection |
| `THREAD_DB_PATH` | `data/threads.db` | SQLite storage path |

**Note**: No Chroma Cloud secrets needed (using Local ChromaDB now!)

### Artifacts

GitHub Actions uploads these after each run:
- `manifest.json` (raw)
- `manifest.json` (structured)
- `manifest.json` (chunked)

Retention: 7 days

---

## 2. Render (Backend API)

**Purpose**: Host FastAPI application
**Product**: Render Web Service (Free tier available)
**URL**: `https://mf-faq-assistant.onrender.com`

### Why Render?
- ✅ Native Python support
- ✅ Free tier with 512 MB RAM
- ✅ Automatic deployments from Git
- ✅ Persistent disks (for SQLite/ChromaDB)
- ✅ Custom domains

### Deployment Steps

#### 2.1 Create Render Account
1. Sign up at https://render.com (GitHub login)
2. Create new Web Service
3. Connect GitHub repository

#### 2.2 Configure Service

**Settings:**
```yaml
Name: mf-faq-assistant
Region: Singapore (closest to India)
Branch: main
Build Command: pip install -r requirements.txt
Start Command: python -m runtime.phase_9_api
Plan: Starter ($7/month) or Free
```

**Environment Variables:**
```
GROQ_API_KEY=gsk_your_key_here
THREAD_DB_PATH=/opt/render/project/src/data/threads.db
CHROMA_PERSIST_DIR=/opt/render/project/src/data/chroma
ADMIN_REINDEX_SECRET=your_secure_random_string
RUNTIME_API_DEBUG=0
```

#### 2.3 Persistent Disk (Important!)

For SQLite and ChromaDB to persist across deploys:

```yaml
# render.yaml (add to repo root)
services:
  - type: web
    name: mf-faq-assistant
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python -m runtime.phase_9_api
    disk:
      name: mf-data
      mountPath: /opt/render/project/src/data
      sizeGB: 1
```

### Health Check Endpoint

Render will ping:
```
GET https://mf-faq-assistant.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "components": {
    "retriever": "ready",
    "generator": "ready",
    "safety": "ready",
    "threads": "ready"
  }
}
```

---

## 3. Vercel (Frontend)

**Purpose**: Host Next.js application
**Product**: Vercel (Hobby tier - free)
**URL**: `https://mf-faq-assistant.vercel.app`

### Why Vercel?
- ✅ Next.js native support (creators of Next.js)
- ✅ Automatic deployments from Git
- ✅ Global CDN
- ✅ Preview deployments for PRs
- ✅ Free SSL & custom domains

### Deployment Steps

#### 3.1 Prepare Frontend

Ensure `web/` folder is ready:
```bash
cd web
npm install
npm run build
```

#### 3.2 Configure API URL

Edit `web/lib/api.ts`:
```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://mf-faq-assistant.onrender.com';
```

#### 3.3 Deploy to Vercel

**Option A: Vercel CLI**
```bash
cd web
npm i -g vercel
vercel --prod
```

**Option B: Git Integration**
1. Push `web/` folder to GitHub
2. Import project at https://vercel.com/new
3. Select framework preset: Next.js
4. Set root directory: `web`

#### 3.4 Environment Variables

In Vercel Dashboard → Project Settings → Environment Variables:
```
NEXT_PUBLIC_API_URL=https://mf-faq-assistant.onrender.com
```

#### 3.5 Custom Domain (Optional)

1. Buy domain (e.g., mffaq.in)
2. Add to Vercel: Settings → Domains
3. Update DNS records as instructed

---

## 4. Zapier Integration

**Purpose**: Automate workflows and notifications
**Product**: Zapier (Free tier: 100 tasks/month)

### What Zapier Can Do

#### 4.1 Failure Alerts (Critical)

**Trigger**: GitHub Actions workflow failure
**Action**: Send email/Slack notification

```
GitHub → New Workflow Run (failed)
    ↓
Filter: Workflow name = "Daily Ingestion Pipeline"
    ↓
Email by Zapier → Send alert to admin
Slack → Post to #alerts channel
```

Setup:
1. GitHub trigger: "New Workflow Run"
2. Filter: `workflow_name` = "Daily Ingestion Pipeline" AND `conclusion` = "failure"
3. Action: Email/Slack with run details and log link

#### 4.2 Daily Summary Report

**Trigger**: Scheduled (10 AM IST daily)
**Action**: Send stats email

```
Schedule by Zapier → Every day at 10:00 AM IST
    ↓
Webhooks by Zapier → GET https://api.render.com/v1/services/{service_id}/deploys
    ↓
Formatter → Format stats
    ↓
Email by Zapier → Send daily digest
```

#### 4.3 API Health Monitoring

**Trigger**: Every 5 minutes
**Action**: Check API health, alert if down

```
Schedule by Zapier → Every 5 minutes
    ↓
Webhooks → GET https://mf-faq-assistant.onrender.com/health
    ↓
Filter: Status code != 200
    ↓
Slack/Email → Alert: API is down!
```

#### 4.4 New Thread Notifications (Optional)

**Trigger**: New thread created via API
**Action**: Log to Google Sheets/Airtable

```
Webhooks by Zapier → Catch hook from backend
    ↓
Google Sheets → Append row with thread_id, timestamp
    ↓
(For analytics/monitoring)
```

To implement:
1. Add webhook call in `runtime/phase_9_api/app.py`:
```python
# After thread creation
import requests
requests.post("https://hooks.zapier.com/hooks/catch/.../", json={
    "event": "thread_created",
    "thread_id": thread.thread_id,
    "timestamp": thread.created_at
})
```

#### 4.5 Content Update Notifications

**Trigger**: After successful GitHub Actions ingestion
**Action**: Notify team that data is fresh

```
GitHub → Workflow completed successfully
    ↓
Delay: 1 minute
    ↓
Slack → "✅ Daily ingestion complete! 251 chunks indexed."
```

---

## Deployment Checklist

### Phase 1: Backend (Render)
- [ ] Create Render account
- [ ] Connect GitHub repo
- [ ] Configure environment variables
- [ ] Set up persistent disk
- [ ] Deploy and verify health endpoint
- [ ] Test API endpoints with curl/Postman

### Phase 2: Frontend (Vercel)
- [ ] Create Vercel account
- [ ] Import GitHub repo
- [ ] Set `NEXT_PUBLIC_API_URL`
- [ ] Deploy and test UI
- [ ] Verify chat functionality
- [ ] Test thread management

### Phase 3: Scheduler (GitHub Actions)
- [ ] Verify workflow file exists
- [ ] Add required secrets
- [ ] Test manual trigger
- [ ] Wait for first scheduled run
- [ ] Verify logs and artifacts

### Phase 4: Zapier (Optional)
- [ ] Create Zapier account
- [ ] Set up failure alert Zap
- [ ] Set up daily summary Zap
- [ ] Test webhooks
- [ ] Verify notifications work

---

## Environment Variables Summary

### GitHub Actions Secrets
```
GROQ_API_KEY=gsk_...
ADMIN_REINDEX_SECRET=...
THREAD_DB_PATH=data/threads.db
```

### Render Environment Variables
```
GROQ_API_KEY=gsk_...
THREAD_DB_PATH=/opt/render/project/src/data/threads.db
CHROMA_PERSIST_DIR=/opt/render/project/src/data/chroma
ADMIN_REINDEX_SECRET=...
RUNTIME_API_DEBUG=0
PORT=8000
API_HOST=0.0.0.0
```

### Vercel Environment Variables
```
NEXT_PUBLIC_API_URL=https://mf-faq-assistant.onrender.com
```

---

## Cost Estimation

### Free Tier Limits

| Service | Free Tier | Usage |
|---------|-----------|-------|
| **GitHub Actions** | 2,000 min/month | ~60 min/month (1 run/day) |
| **Render** | 512 MB RAM, 0.1 CPU | Sufficient for low traffic |
| **Vercel** | 100 GB bandwidth | Sufficient for demo |
| **Zapier** | 100 tasks/month | ~30 tasks/month |

### Paid Tier (If Needed)

| Service | Plan | Cost | When Needed |
|---------|------|------|-------------|
| Render | Starter | $7/month | Higher traffic |
| Zapier | Starter | $19.99/month | More automations |

**Total Estimated Cost: $0-27/month**

---

## Monitoring & Maintenance

### Daily Checks
- [ ] Check Render dashboard for errors
- [ ] Review Zapier alerts (if any)
- [ ] Verify ingestion completed (GitHub Actions)

### Weekly Tasks
- [ ] Review Vercel analytics
- [ ] Check SQLite DB size
- [ ] Clean old ChromaDB versions

### Monthly Tasks
- [ ] Review GitHub Actions minutes usage
- [ ] Check Render disk usage
- [ ] Update dependencies

### Rollback Strategy

**If deployment fails:**
1. Revert Git commit
2. Push to trigger re-deploy
3. If database issue: restore from backup

**Backup commands:**
```bash
# Backup SQLite
cp data/threads.db data/threads.db.backup.$(date +%Y%m%d)

# Backup ChromaDB
tar -czf chroma-backup-$(date +%Y%m%d).tar.gz data/chroma/
```

---

## Troubleshooting

### Render: App Won't Start
- Check `requirements.txt` includes all deps
- Verify `PORT` env var set correctly
- Check Render logs for import errors

### Vercel: Build Fails
- Ensure `next.config.js` is valid
- Check for TypeScript errors: `npm run build` locally
- Verify Node.js version compatibility

### GitHub Actions: Workflow Fails
- Check secrets are set correctly
- Verify `config/urls.yaml` is valid
- Review detailed logs in GitHub UI

### Zapier: Webhook Not Firing
- Verify webhook URL is correct
- Check Zap history for errors
- Test webhook manually with curl

---

## Security Considerations

### API Keys
- ✅ Never commit to Git
- ✅ Store in environment variables
- ✅ Rotate periodically
- ✅ Use different keys for dev/prod

### Database
- ✅ SQLite only accessible via API
- ✅ No direct database exposure
- ✅ ChromaDB local to server

### CORS
- ✅ Configure allowed origins in FastAPI
- ✅ Frontend URL must be in allowlist

### Admin Endpoint
- ✅ Protected by secret token
- ✅ Not exposed in frontend
- ✅ Log all admin actions

---

## Next Steps

1. **Start with Render** (backend takes longest to deploy)
2. **Then Vercel** (frontend depends on backend)
3. **Configure GitHub Actions** (scheduler can run independently)
4. **Optional: Zapier** (nice-to-have automations)

**Estimated Total Setup Time: 2-3 hours**

---

*Document Version: 1.0*
*Last Updated: 2026-04-24*
