#!/usr/bin/env bash
# @package EGI-STAT — M-266 acceptance test
# @author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
# @version 1.0.0
# @date 2026-06-11
# @purpose Gate stat.florenceegi.com: dashboard+API interne 401, /api/public/site-stats 200
#          con shape atteso + CORS fabiocherici.com. Parte locale: modulo public_stats.
set -u
ROOT=/home/fabio/EGI-STAT

# ---- 1. LOCALE: modulo public_stats produce lo shape atteso dallo SQLite reale
python3 - <<'EOF' || exit 1
import sys
sys.path.insert(0, '/home/fabio/EGI-STAT/backend')
try:
    from public_stats import site_stats
except ImportError:
    print("RED: backend/public_stats.py mancante"); sys.exit(1)
s = site_stats()
required = ["hours_total", "hours_last_7_days", "projects_total",
            "projects_active_30d", "last_activity", "lines_net_total", "generated_at"]
missing = [k for k in required if k not in s]
if missing:
    print(f"RED: chiavi mancanti in site_stats(): {missing}"); sys.exit(1)
if not isinstance(s["hours_total"], (int, float)) or s["hours_total"] <= 0:
    print(f"RED: hours_total non plausibile: {s['hours_total']}"); sys.exit(1)
# privacy: l'aggregato NON deve esporre nomi progetto
flat = str(s)
if "project_names" in s or "projects" in s and isinstance(s.get("projects"), list):
    print("RED: endpoint pubblico espone lista progetti (solo aggregati ammessi)"); sys.exit(1)
print("OK local: shape valido, hours_total =", s["hours_total"])
EOF

# ---- 2. LIVE (skip se DNS non ancora propagato: fallisce esplicito, no silent skip)
URL="https://stat.florenceegi.com"
DASH=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$URL/" 2>/dev/null)
[[ "$DASH" == "401" ]] || { echo "RED live: dashboard senza credenziali atteso 401, ricevuto '$DASH'"; exit 1; }

INTERNAL=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$URL/api/v2/stats/summary" 2>/dev/null)
[[ "$INTERNAL" == "401" ]] || { echo "RED live: API interna atteso 401, ricevuto '$INTERNAL'"; exit 1; }

PUB=$(curl -s -o /tmp/m266-pub.json -w "%{http_code}" --max-time 10 "$URL/api/public/site-stats" 2>/dev/null)
[[ "$PUB" == "200" ]] || { echo "RED live: /api/public/site-stats atteso 200, ricevuto '$PUB'"; exit 1; }
python3 -c "import json; d=json.load(open('/tmp/m266-pub.json')); assert 'hours_total' in d" \
  || { echo "RED live: JSON pubblico senza hours_total"; exit 1; }

CORS=$(curl -s -I --max-time 10 -H "Origin: https://fabiocherici.com" "$URL/api/public/site-stats" | grep -i "access-control-allow-origin" | tr -d '\r')
echo "$CORS" | grep -q "fabiocherici.com" || { echo "RED live: CORS per fabiocherici.com assente"; exit 1; }

echo "GREEN: locale + live (401 protetti, 200 pubblico, CORS ok)"
exit 0
