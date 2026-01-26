#!/bin/bash
echo "🚀 Deploy GitHub Actions Workflows"

echo "📁 Files creati:"
ls -la .github/workflows/

echo "💾 Commit & Push automatico..."
git add .github/
git add deploy-gh-actions.sh
git commit -m "🤖 Add GitHub Actions: daily+weekly auto-ingest EGI-STAT"

echo "🔗 Push to origin..."
git push origin main

echo "✅ Workflows deployati! Vai su GitHub Actions tab."
echo "Prossimo step: Aggiungi 6 secrets dal tuo .env"
