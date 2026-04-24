# Quick Deployment Guide

Get the MF FAQ Assistant deployed in 30 minutes.

## Overview

| Component | Platform | URL Pattern | Status |
|-----------|----------|-------------|--------|
| Scheduler | GitHub Actions | N/A | ✅ Ready |
| Backend API | Render | `*.onrender.com` | 🚀 Deploy |
| Frontend | Vercel | `*.vercel.app` | 🚀 Deploy |
| Automations | Zapier | N/A | ⏳ Optional |

---

## Step 1: Deploy Backend (Render) - 10 min

### 1.1 Create Account
- Go to https://dashboard.render.com
- Sign up with GitHub

### 1.2 Deploy from GitHub
1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Select `main` branch

### 1.3 Configure Service
```
Name: mf-faq-assistant
Region: Singapore
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: python -m runtime.phase_9_api
Plan: Free
```

### 1.4 Add Environment Variables
In Render Dashboard → Environment:
```
GROQ_API_KEY=gsk_your_key_here
THREAD_DB_PATH=/opt/render/project/src/data/threads.db
CHROMA_PERSIST_DIR=/opt/render/project/src/data/chroma
ADMIN_REINDEX_SECRET=random_secure_string
RUNTIME_API_DEBUG=0
```

### 1.5 Create Persistent Disk
```
Disk Name: mf-data
Mount Path: /opt/render/project/src/data
Size: 1 GB
```

### 1.6 Deploy
Click "Create Web Service"

**Verify**: Visit `https://[your-service].onrender.com/health`

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

## Step 3: Configure Scheduler (GitHub Actions) - 5 min

### 3.1 Add Secrets
Go to GitHub → Settings → Secrets → Actions:

| Name | Value |
|------|-------|
| `GROQ_API_KEY` | Your Groq API key |
| `ADMIN_REINDEX_SECRET` | Random secure string |

### 3.2 Verify Workflow
Check `.github/workflows/ingest.yml` exists

### 3.3 Test Manually
Go to Actions tab → "Daily Ingestion Pipeline" → "Run workflow"

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
