# Deployment Plan

Complete deployment strategy for the Mutual Fund FAQ Assistant with automated scheduling, hosted backend, and modern frontend.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────────────┘

                             ┌─────────────────┐
                             │    Vercel       │
                             │   (Frontend)    │
                             │   Next.js       │
                             └────────┬────────┘
                                      │ API Queries
                                      │ (Real-time)
                                      ▼
┌──────────────────────────────────────────────────────────────────────┐
│                            RENDER                                   │
│  ┌─────────────────────┐         ┌─────────────────────────────────┐  │
│  │   Web Service       │         │   Cron Job (Scheduler)          │  │
│  │   FastAPI Server    │◀───────▶│   Daily Ingestion               │  │
│  │   - API endpoints   │ Shared  │   - Runs 09:15 AM IST           │  │
│  │   - Thread queries  │  Disk   │   - Updates ChromaDB            │  │
│  │   - Safety checks   │         │   - Logs to same disk           │  │
│  └─────────────────────┘         └─────────────────────────────────┘  │
│           │                                    │                      │
│           └────────────┬───────────────────────┘                      │
│                        │                                              │
│                        ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │   Shared Persistent Disk                                        │  │
│  │   ├── data/chroma/      (ChromaDB - 251 chunks indexed)       │  │
│  │   ├── data/threads.db   (SQLite - conversation storage)         │  │
│  │   └── logs/             (Scheduler logs)                       │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│              Zapier (Optional)                 │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│    │ Failure  │  │  Daily   │  │  Slack   │  │
│    │  Alerts  │  │ Summary  │  │  Notify  │  │
│    └──────────┘  └──────────┘  └──────────┘  │
└──────────────────────────────────────────────┘
```

---

## 1. Render Cron Job (Scheduler)

**Purpose**: Daily automated ingestion pipeline  
**Schedule**: 09:15 AM IST (03:45 UTC) daily  
**Product**: Render Cron Job (Requires Starter plan: $7/month)

### Why Render for Scheduler?

**The Problem with GitHub Actions:**
- ❌ ChromaDB created in GitHub runner isn't accessible by backend
- ❌ Artifacts are temporary and hard to sync
- ❌ Data transfer complexity

**The Render Solution:**
- ✅ Scheduler runs on SAME server as backend
- ✅ Shared persistent disk (ChromaDB immediately available)
- ✅ No data transfer needed
- ✅ Logs accessible in one place

### Configuration

Configured in `render.yaml`:

```yaml
services:
  # Web Service (API)
  - type: web
    name: mf-faq-assistant
    # ... API configuration ...
    disk:
      name: mf-data
      mountPath: /opt/render/project/src/data
      sizeGB: 1
  
  # Cron Job (Scheduler)
  - type: cron
    name: mf-faq-scheduler
    schedule: "45 3 * * *"  # 09:15 AM IST
    startCommand: python scripts/local_scheduler.py
    disk:
      name: mf-data  # SAME disk as web service!
      mountPath: /opt/render/project/src/data
```

### How It Works

```
09:15 AM IST
    │
    ▼
┌─────────────────────────────────────┐
│  Render Cron Job Starts             │
│  mf-faq-scheduler                   │
└─────────────┬───────────────────────┘
              │
              ▼
    ┌─────────────────────┐
    │  Phase 4.0: Scrape │──► data/raw/
    └─────────────────────┘
              │
              ▼
    ┌─────────────────────┐
    │  Phase 4.1: Normalize│──► data/structured/
    └─────────────────────┘
              │
              ▼
    ┌─────────────────────┐
    │  Phase 4.2: Chunk   │──► data/structured/*/chunked/
    └─────────────────────┘
              │
              ▼
    ┌─────────────────────┐
    │  Phase 4.3: Index  │──► data/chroma/ (ChromaDB)
    └─────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Web Service (FastAPI)              │
│  Immediately sees updated ChromaDB  │
│  Same disk, no sync needed!         │
└─────────────────────────────────────┘
```

### Logs

Scheduler logs saved to:
```
/opt/render/project/src/data/logs/scheduler_YYYYMMDD-HHMMSS.log
```

View in Render Dashboard:
1. Go to Cron Job → Logs
2. Or SSH into disk: `cd data/logs/`

---

## 2. Render (Backend + Scheduler)

**Purpose**: Host FastAPI application AND run daily ingestion
**Product**: Render Web Service + Cron Job
**URL**: `https://mf-faq-assistant.onrender.com`

### Why Render?
- ✅ Native Python support
- ✅ Cron jobs for scheduling (paid plan)
- ✅ Persistent disks shared between services
- ✅ Same server = no data sync issues
- ✅ Automatic deployments from Git

### Architecture: Shared Disk Pattern

```
┌─────────────────────────────────────────┐
│           RENDER DASHBOARD              │
│                                         │
│  ┌──────────────┐    ┌──────────────┐   │
│  │  Web Service │    │  Cron Job    │   │
│  │  (FastAPI)   │    │  (Scheduler) │   │
│  │  ─────────── │    │  ─────────── │   │
│  │  Queries API  │    │  09:15 AM IST│   │
│  │  Real-time   │    │  Ingestion   │   │
│  └──────┬───────┘    └──────┬───────┘   │
│         │                     │           │
│         └──────────┬──────────┘           │
│                    │                      │
│         ┌──────────▼──────────┐          │
│         │   SHARED DISK       │          │
│         │   mf-data (1GB)      │          │
│         │   ─────────────     │          │
│         │   data/chroma/       │          │
│         │   data/threads.db    │          │
│         │   data/logs/         │          │
│         └─────────────────────┘          │
└─────────────────────────────────────────┘
```

### Deployment Steps

#### 2.1 Create Render Account
1. Sign up at https://render.com (GitHub login)
2. Click "New +" → "Blueprint"
3. Connect GitHub repository

#### 2.2 Deploy with render.yaml

Your repo already has `render.yaml`:

```yaml
services:
  # Web Service
  - type: web
    name: mf-faq-assistant
    plan: free
    # ... (see file for full config)
  
  # Cron Job (Scheduler)
  - type: cron
    name: mf-faq-scheduler
    plan: starter  # $7/month
    schedule: "45 3 * * *"  # 09:15 AM IST
    # ... (see file for full config)
    disk:
      name: mf-data  # SHARED with web service!
      mountPath: /opt/render/project/src/data
```

#### 2.3 Set Environment Variables

Both services share these:
```
GROQ_API_KEY=gsk_your_key_here
THREAD_DB_PATH=/opt/render/project/src/data/threads.db
CHROMA_PERSIST_DIR=/opt/render/project/src/data/chroma
ADMIN_REINDEX_SECRET=your_secure_random_string
RUNTIME_API_DEBUG=0
```

**Important**: Use the SAME secret for both web service and cron job so admin endpoints work.

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

### Phase 1: Render (Backend + Scheduler)
- [ ] Create Render account (https://render.com)
- [ ] Click "New +" → "Blueprint"
- [ ] Connect GitHub repo (`kritidhanwaria488-blip/m1`)
- [ ] Upgrade to Starter plan ($7/month) for cron jobs
- [ ] Configure environment variables (both web service and cron job):
  - `GROQ_API_KEY`
  - `ADMIN_REINDEX_SECRET` (same for both!)
  - `THREAD_DB_PATH=/opt/render/project/src/data/threads.db`
  - `CHROMA_PERSIST_DIR=/opt/render/project/src/data/chroma`
- [ ] Deploy and verify health endpoint
- [ ] Test API endpoints with curl/Postman
- [ ] **Trigger first ingestion**: Go to Cron Job → Run Job
- [ ] Verify ChromaDB populated with 251 chunks
- [ ] Verify logs in `data/logs/`

### Phase 2: Frontend (Vercel)
- [ ] Create Vercel account
- [ ] Import GitHub repo
- [ ] Set `NEXT_PUBLIC_API_URL=https://[your-render-service].onrender.com`
- [ ] Deploy and test UI
- [ ] Verify chat functionality
- [ ] Test thread management

### Phase 3: Zapier Automations (Optional)
- [ ] Create Zapier account
- [ ] Set up failure alert (Render → Email/Slack)
- [ ] Set up daily summary (Schedule → API → Email)

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

### Why Render Cron Job Requires Paid Plan

Cron jobs on Render require at least the **Starter plan** ($7/month):
- Free tier: Web services only
- Starter ($7/mo): Web + Cron jobs + 1GB disk

### Cost Breakdown

| Service | Plan | Cost | Purpose |
|---------|------|------|---------|
| **Render Web** | Free | $0 | FastAPI backend (512 MB RAM) |
| **Render Cron** | Starter | $7/mo | Daily ingestion scheduler |
| **Render Disk** | Included | $0 | 1GB shared persistent disk |
| **Vercel** | Hobby | $0 | Next.js frontend |
| **Zapier** | Free | $0 | 100 tasks/month (alerts) |

**Total Estimated Cost: $7/month** (Render Starter plan)

### Can I Reduce Cost?

**Option: Run Scheduler Manually**
- Disable Render cron job
- Run local scheduler manually when needed:
  ```bash
  python scripts/local_scheduler.py
  ```
- Cost: **$0/month** (but no automatic daily updates)

**Option: Use GitHub Actions + Manual Deploy**
- Keep GitHub Actions for ingestion
- Commit ChromaDB to repo (not recommended for production)
- Auto-deploy on Render when repo updates
- Cost: **$0/month** but messy git history

**Recommendation**: Pay $7/month for the clean, reliable architecture.

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
