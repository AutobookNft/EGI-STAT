#!/bin/bash
# Deploy EGI-STAT on Laravel Forge
# Formato corretto per Deploy Script di Forge

$CREATE_RELEASE()

cd $FORGE_RELEASE_DIRECTORY

# --- 1. FRONTEND BUILD ---
echo "📦 Building Frontend..."
cd frontend
npm install
npm run build
cd ..
echo "✅ Frontend built to dist/"

# --- 2. BACKEND SETUP ---
echo "🐍 Setting up Backend..."
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..

# --- 3. SETUP CRON JOB FOR DAILY INGESTION ---
echo "⏰ Configuring daily ingestion cron..."
CRON_JOB="0 6 * * * cd /home/forge/egi-stat.13.53.205.215.sslip.io/current/backend && source .venv/bin/activate && python ingest_to_remotedb.py --days 7 >> /tmp/egi-ingest.log 2>&1"
# Remove old cron if exists, then add new one
(crontab -l 2>/dev/null | grep -v "ingest_to_remotedb.py" || true; echo "$CRON_JOB") | crontab -

$ACTIVATE_RELEASE()

echo "✅ Deployment complete!"
echo ""
echo "⚠️  MANUAL STEP REQUIRED:"
echo "1. Go to Forge Dashboard → Daemons"
echo "2. Add new Daemon:"
echo "   Command: /home/forge/egi-stat.13.53.205.215.sslip.io/current/backend/.venv/bin/python /home/forge/egi-stat.13.53.205.215.sslip.io/current/backend/api.py"
echo "3. Save → It will start and stay running"
echo ""
echo "Verify:"
echo "   curl http://13.53.205.215:5000/api/stats/weekly"



