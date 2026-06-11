#!/usr/bin/env bash
# @package EGI-STAT — M-267 acceptance test
# @author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
# @version 1.0.0
# @date 2026-06-11
# @purpose Dashboard funzionante: env produzione punta a stat.florenceegi.com,
#          il bundle buildato NON contiene host sslip morto, e (live, con CREDS)
#          /api/v2/stats/hours risponde con dati attraverso il dominio nuovo.
set -u
ROOT=/home/fabio/EGI-STAT

grep -q "VITE_API_BASE_URL=https://stat.florenceegi.com" "$ROOT/frontend/.env.production" \
  || { echo "RED: .env.production non punta a stat.florenceegi.com"; exit 1; }

DIST="$ROOT/frontend/dist"
[[ -d "$DIST" ]] || { echo "RED: dist/ assente — build mancante"; exit 1; }
if grep -rq "sslip.io" "$DIST"; then
  echo "RED: bundle buildato contiene ancora host sslip morto"; exit 1
fi
grep -rq "stat.florenceegi.com" "$DIST/assets" \
  || { echo "RED: bundle non contiene stat.florenceegi.com"; exit 1; }

if [[ -n "${CREDS:-}" ]]; then
  N=$(curl -s --max-time 10 -u "$CREDS" "https://stat.florenceegi.com/api/v2/stats/hours" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null)
  [[ "${N:-0}" -gt 0 ]] || { echo "RED live: /api/v2/stats/hours vuoto o irraggiungibile"; exit 1; }
  echo "GREEN: env ok, bundle pulito, API hours live con $N progetti"
else
  echo "GREEN (parziale): env ok, bundle pulito — CREDS non fornite, live non verificato"
fi
exit 0
