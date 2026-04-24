# Zapier Integration Guide

Automate workflows and notifications for the Mutual Fund FAQ Assistant.

---

## What is Zapier?

Zapier connects your apps and automates workflows without code. Think of it as "if this, then that" for your entire tech stack.

**Free Tier**: 100 tasks/month (sufficient for basic alerting)
**Website**: https://zapier.com

---

## Recommended Zaps

### 1. 🚨 Failure Alerts (ESSENTIAL)

**Purpose**: Get notified immediately when ingestion fails

**Trigger**: GitHub Actions → Workflow Run (failure)
**Filter**: Workflow name = "Daily Ingestion Pipeline"
**Actions**:
- 📧 Send email to admin
- 💬 Post to Slack #alerts channel
- 📱 Send SMS (optional)

**Setup**:
1. Create new Zap
2. Choose trigger: GitHub → "New Workflow Run"
3. Add filter: `workflow_name` contains "Daily Ingestion Pipeline" AND `conclusion` = "failure"
4. Add action: Email by Zapier → Send email
   - To: admin@yourcompany.com
   - Subject: "🚨 MF FAQ Assistant: Ingestion Failed"
   - Body: Run details + log URL

**Why**: Catch data pipeline issues before users notice

---

### 2. ✅ Daily Success Summary (RECOMMENDED)

**Purpose**: Daily digest of system health

**Trigger**: Schedule by Zapier → Every day at 10:00 AM IST
**Actions**:
- 🔗 GET https://your-api.com/health
- 📊 Format response
- 📧 Email summary

**Setup**:
1. Trigger: Schedule → Daily → 10:00 AM IST
2. Action: Webhooks by Zapier → Custom Request
   - Method: GET
   - URL: `https://your-render-service.onrender.com/health`
3. Action: Formatter → Text → Extract status fields
4. Action: Email → Send formatted summary

**Email Template**:
```
Daily MF FAQ Assistant Report
Date: {{zap_meta_human_now}}

Status: ✅ All systems operational
Collection: {{total_chunks}} documents
API: Online ({{api_latency}}ms)
Last Ingestion: {{last_run_date}}

View Dashboard: https://your-render-service.onrender.com/health
```

**Why**: Peace of mind + proactive monitoring

---

### 3. 💬 Slack Notifications (OPTIONAL)

**Purpose**: Team visibility on system events

**Trigger**: Multiple (GitHub Actions, Render deploys)
**Action**: Slack → Send channel message

**Events to notify**:
- ✅ Ingestion completed (with stats)
- ❌ Ingestion failed
- 🚀 New deployment
- ⚠️ API health issues

**Setup**:
1. Connect Slack workspace to Zapier
2. Choose channel: #mf-faq-alerts
3. Customize message format with emojis

**Example Message**:
```
✅ *Daily Ingestion Complete*

251 chunks indexed from 5 schemes
Duration: 68 seconds
Updated: {{timestamp}}
```

---

### 4. 📊 Usage Analytics (ADVANCED)

**Purpose**: Track API usage and popular queries

**Trigger**: Webhook catch (from your API)
**Actions**:
- 📝 Google Sheets → Append row
- 📈 Analytics dashboard

**Implementation**:
1. In `runtime/phase_9_api/app.py`, add webhook call:
```python
import requests

# After each API response
requests.post(
    "https://hooks.zapier.com/hooks/catch/[your-hook-id]/",
    json={
        "event": "query",
        "thread_id": thread_id,
        "query_length": len(content),
        "has_response": bool(assistant_message),
        "timestamp": datetime.now().isoformat()
    },
    timeout=5
)
```

2. Zapier: Webhooks by Zapier → Catch Hook
3. Zapier: Google Sheets → Create Spreadsheet Row

**Sheet Columns**:
- Timestamp
- Thread ID
- Query (first 50 chars)
- Response status
- Response time

**Why**: Understand user behavior, improve FAQ coverage

---

### 5. 🔗 Data Sync to CRM/Database (ADVANCED)

**Purpose**: Sync conversation data to external systems

**Trigger**: Webhook catch (new thread created)
**Actions**:
- 🗄️ Airtable → Create record
- 🗃️ Notion → Add page
- 📧 Salesforce/HubSpot → Log activity

**Use Cases**:
- Track user engagement
- Build knowledge base
- Identify gaps in documentation

---

### 6. 📱 SMS Alerts for Critical Issues (OPTIONAL)

**Purpose**: Immediate notification for urgent issues

**Trigger**: API health check fails 3 times in 10 min
**Action**: Twilio → Send SMS

**Setup**:
1. Schedule: Every 5 minutes
2. Webhook: GET /health
3. Filter: Status != "healthy"
4. Delay: 10 min
5. Filter: Check again (still failing)
6. Action: Twilio → Send SMS

**SMS Content**:
```
🚨 MF FAQ Assistant DOWN
API not responding
Check: https://status.yoursite.com
```

**Why**: 24/7 monitoring without expensive tools

---

### 7. 📅 Content Update Calendar (OPTIONAL)

**Purpose**: Track when data was last updated

**Trigger**: GitHub Actions workflow success
**Action**: Google Calendar → Create event

**Setup**:
1. Trigger: GitHub → Workflow success
2. Filter: Workflow = "Daily Ingestion Pipeline"
3. Action: Google Calendar → Quick Add Event
4. Event title: "✅ MF Data Updated - {{chunks_count}} chunks"

**Why**: Audit trail, stakeholder visibility

---

## Setup Instructions

### Step 1: Create Zapier Account
1. Go to https://zapier.com
2. Sign up (free tier)
3. Complete onboarding

### Step 2: Connect Apps
Connect these apps to Zapier:
- ✅ GitHub (for Actions monitoring)
- ✅ Email/Gmail (for notifications)
- ✅ Slack (for team alerts) - optional
- ✅ Webhooks (for custom integrations)

### Step 3: Create First Zap (Failure Alert)

**Trigger Configuration**:
```
App: GitHub
Event: New Workflow Run
Repository: your-org/m1
```

**Filter Configuration**:
```
Only continue if...
Workflow name contains "Daily Ingestion Pipeline"
AND
Conclusion equals "failure"
```

**Action Configuration**:
```
App: Email by Zapier
To: your-email@example.com
Subject: MF FAQ Assistant: Pipeline Failed 🚨
Body:
  Run ID: {{workflow_run_id}}
  Failed at: {{created_at}}
  Logs: {{html_url}}
```

### Step 4: Test
1. Go to GitHub Actions
2. Trigger workflow manually
3. Force it to fail (temporarily break config)
4. Verify you receive email

### Step 5: Enable
Turn on the Zap! 🎉

---

## Cost Analysis

### Free Tier (100 tasks/month)
- Failure alerts: ~5 tasks/month (rare failures)
- Daily summary: ~30 tasks/month
- **Total**: ~35 tasks/month ✅

### When to Upgrade?
- More than 100 tasks/month
- Need multi-step Zaps
- Need premium apps (Salesforce, etc.)

**Paid Plans**:
- Starter: $19.99/month (750 tasks)
- Professional: $49/month (2,000 tasks)

---

## Alternatives to Zapier

### Native GitHub Notifications
- GitHub → Settings → Notifications
- Enable Actions notifications
- Free, but less customizable

### Render + Uptime Robot
- Uptime Robot → Monitor /health endpoint
- Free tier: 50 monitors
- SMS/email alerts included

### Custom Webhook Server
- Build simple Flask app
- Receive webhooks from GitHub/Render
- Send notifications via AWS SES
- More work, full control

---

## Best Practices

### 1. Keep it Simple
Start with 1-2 critical Zaps (failure alert + daily summary)

### 2. Rate Limiting
Don't create Zaps that fire too frequently
- GitHub Actions: Max 1 per day
- Health checks: Every 5-15 minutes

### 3. Error Handling
Add "Filter" steps to prevent false positives

### 4. Security
- Don't log sensitive data (API keys, PII)
- Use webhook secrets for verification
- Limit Zapier access to necessary repos

### 5. Monitoring
Periodically review Zapier Task History to ensure Zaps are running

---

## Troubleshooting

### Zap not firing?
- Check if trigger app is connected
- Verify filter conditions
- Check Zapier Task History for errors

### Too many notifications?
- Add stricter filters
- Reduce check frequency
- Use "Only continue if..." logic

### Webhook not received?
- Verify webhook URL is correct
- Check payload format matches expected schema
- Test webhook with curl:
```bash
curl -X POST https://hooks.zapier.com/hooks/catch/xxx/ \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

---

## Quick Reference

| Zap | Priority | Tasks/Month | Setup Time |
|-----|----------|-------------|------------|
| Failure Alert | ⭐⭐⭐ Critical | ~5 | 5 min |
| Daily Summary | ⭐⭐ Recommended | ~30 | 10 min |
| Slack Notifications | ⭐⭐ Optional | ~35 | 10 min |
| Usage Analytics | ⭐ Advanced | ~100+ | 30 min |
| SMS Alerts | ⭐ Optional | ~10 | 15 min |

---

## Summary

**Zapier adds**: Automated monitoring, alerting, and reporting
**Effort**: 30 minutes setup
**Cost**: Free tier sufficient
**Value**: Peace of mind, proactive issue detection

**Start with**: Failure alert + Daily summary
**Add later**: Slack integration, usage analytics

---

*Document Version: 1.0*
*Last Updated: 2026-04-24*
