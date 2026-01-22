#!/bin/bash
# EGI-STAT Daily Ingestion Script
# Runs at 23:50 via Cron

# Navigate to backend directory
cd /home/fabio/EGI-STAT/backend

# Log start
echo "------------------------------------------------" >> cron_ingest.log
echo "⏰ Starting Daily Ingestion: $(date)" >> cron_ingest.log

# Run python script (using system python3 as dependencies are installed user-wide or venv needed?)
# Checking previously used command: "pip install" was run in /home/fabio/EGI-STAT/backend without venv activation visible in history, 
# but output showed ./.venv/lib/python3.10/site-packages.
# So we must use the venv python.

VENV_PYTHON="./.venv/bin/python"

if [ -f "$VENV_PYTHON" ]; then
    $VENV_PYTHON ingest_to_remotedb.py --days 1 >> cron_ingest.log 2>&1
else
    # Fallback if venv not found (though it should be there based on logs)
    echo "⚠️  Virtualenv not found, trying system python..." >> cron_ingest.log
    python3 ingest_to_remotedb.py --days 1 >> cron_ingest.log 2>&1
fi

echo "✅ Finished: $(date)" >> cron_ingest.log
echo "------------------------------------------------" >> cron_ingest.log
