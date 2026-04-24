# Render Deployment Helper Script
# This script prepares and validates your deployment to Render

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  MF FAQ Assistant - Render Deploy Tool" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if GROQ_API_KEY is set
$groqKey = $env:GROQ_API_KEY
if (-not $groqKey) {
    Write-Host "⚠️  Warning: GROQ_API_KEY environment variable not set" -ForegroundColor Yellow
    Write-Host "   You'll need to add it in Render Dashboard after deployment" -ForegroundColor Yellow
} else {
    Write-Host "✅ GROQ_API_KEY found in environment" -ForegroundColor Green
}

Write-Host ""
Write-Host "📋 Pre-Deployment Checklist:" -ForegroundColor Cyan
Write-Host ""

# Check files exist
$checks = @(
    @{File="render.yaml"; Desc="Render Blueprint"},
    @{File="requirements.txt"; Desc="Python Dependencies"},
    @{File="runtime/phase_9_api/__main__.py"; Desc="FastAPI Backend"},
    @{File="scripts/local_scheduler.py"; Desc="Scheduler Script"}
)

$allGood = $true
foreach ($check in $checks) {
    if (Test-Path $check.File) {
        Write-Host "  ✅ $($check.Desc): $($check.File)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $($check.Desc): $($check.File) NOT FOUND" -ForegroundColor Red
        $allGood = $false
    }
}

Write-Host ""

if (-not $allGood) {
    Write-Host "❌ Some required files are missing. Please fix before deploying." -ForegroundColor Red
    exit 1
}

Write-Host "✅ All required files present!" -ForegroundColor Green
Write-Host ""

# Git status check
Write-Host "📦 Git Status Check:" -ForegroundColor Cyan
$gitStatus = git status --short 2>$null
if ($gitStatus) {
    Write-Host "  ⚠️  Uncommitted changes detected:" -ForegroundColor Yellow
    $gitStatus | ForEach-Object { Write-Host "     $_" -ForegroundColor Yellow }
    Write-Host ""
    $commit = Read-Host "Commit changes before deploying? (y/n)"
    if ($commit -eq 'y' -or $commit -eq 'Y') {
        $msg = Read-Host "Enter commit message (or press Enter for default)"
        if (-not $msg) {
            $msg = "Prepare for Render deployment"
        }
        git add .
        git commit -m "$msg"
        git push origin master
        Write-Host "✅ Changes committed and pushed" -ForegroundColor Green
    }
} else {
    Write-Host "  ✅ Working directory clean" -ForegroundColor Green
}

Write-Host ""
Write-Host "🚀 Ready to Deploy!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "  1. Go to https://dashboard.render.com" -ForegroundColor White
Write-Host "  2. Click 'New +' → 'Blueprint'" -ForegroundColor White
Write-Host "  3. Connect your GitHub repo: kritidhanwaria488-blip/m1" -ForegroundColor White
Write-Host "  4. Render will detect render.yaml and create services" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  IMPORTANT: After deployment:" -ForegroundColor Yellow
Write-Host "  1. Upgrade to Starter Plan ($7/month) for cron jobs" -ForegroundColor Yellow
Write-Host "  2. Add GROQ_API_KEY to BOTH services in Dashboard" -ForegroundColor Yellow
Write-Host "  3. Copy ADMIN_REINDEX_SECRET from web service to cron job" -ForegroundColor Yellow
Write-Host "  4. Manually trigger first ingestion run" -ForegroundColor Yellow
Write-Host ""

$openBrowser = Read-Host "Open Render Dashboard now? (y/n)"
if ($openBrowser -eq 'y' -or $openBrowser -eq 'Y') {
    Start-Process "https://dashboard.render.com"
}

Write-Host ""
Write-Host "📖 Full deployment guide: DEPLOYMENT.md" -ForegroundColor Cyan
Write-Host "📖 Detailed architecture: docs/deployment-plan.md" -ForegroundColor Cyan
