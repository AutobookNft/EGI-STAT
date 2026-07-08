#!/usr/bin/env bash
# @package  EGI-STAT/deploy
# @author   Padmin D. Curtis (Supervisor-CTO, AI Partner OS3.0) for Fabio Cherici
# @version  1.1.0 (M-OS3-141 — aggiunto ship-with-push del livello documentazione: docs.serving.db + doc-coverage.json)
# @date     2026-06-16
# @purpose  Refresh + PUSH delle statistiche Nexus ALLA FINE DI OGNI MISSION (event-driven, NON cron).
#           Invocato dal motore via `stats_refresh_cmd` del descrittore a OGNI chiusura/finalize.
#           Rigenera stats.db dai registri (verita = registri+git) e lo consegna al dev-server
#           (nexus.florenceegi.com / i-079...) via S3 + SSM. Riuso pattern push-stats.sh.
set -uo pipefail
PROFILE="${AWS_DEPLOY_PROFILE:-fabiocherici-deploy}"
REGION="eu-south-1"
INSTANCE="i-079808547853ab7f6"
BUCKET="oracode-dev-exo-504606041369"
DEST="/home/ssm-user/nexus.florenceegi.com"
ROOT="/home/fabio/EGI-STAT"
# M-OS3-141: il livello documentazione del cockpit vive in os3-matrix (i suoi tool producono il
# serving-doc + doc-coverage sul laptop, come coverage_scan.py fa per le stat). Stessa catena a 3 strati.
OS3M="/home/fabio/os3-matrix"
DOCS_SERVING="$OS3M/.oracode/serving"

# 1) rigenera l'aggregate dai registri (questo gia avveniva: era lo stats_refresh_cmd precedente)
( cd "$ROOT/backend" && python3 aggregate_to_sqlite.py >/dev/null 2>&1 ) || echo "[push-nexus] aggregate WARN" >&2

# 1b) COPERTURA (M-FUC-057, ship-with-push): scansiona i repo SUL LAPTOP (dove vivono) e
# produce coverage.json — la scansione lato server sarebbe falsa (repo laptop-only assenti).
( cd "$ROOT/backend" && python3 coverage_scan.py >/dev/null 2>&1 ) || echo "[push-nexus] coverage WARN" >&2

# 1c) DRIFT SSOT (M-STAT-002, ship-with-push): esegue ssot-index-check SUL LAPTOP (indice +
# registry_path coi path reali /home/fabio/...) e produce drift.json. Un check live sul box
# sarebbe falso (là manca projects.json e i path sono del laptop) — vedi gemello M-NEXUS-009.
( cd "$ROOT/backend" && python3 produce_drift.py >/dev/null 2>&1 ) || echo "[push-nexus] drift WARN" >&2

# 1d) SERVING-DOC (M-OS3-141): rigenera docs.serving.db dai registri SSOT di tutti gli LSO (gemello
# di aggregate_to_sqlite.py per la documentazione). Scansione sul laptop: i .md vivono qui.
"$OS3M/bin/oracode-docs-aggregate" --db "$DOCS_SERVING/docs.serving.db" >/dev/null 2>&1 || echo "[push-nexus] docs-aggregate WARN" >&2

# 1e) DOC-COVERAGE (M-OS3-141, segnale 3): codice che nessun SSOT sorveglia -> doc-coverage.json
# (gemello di coverage_scan.py). Scansione sul laptop (i repo vivono qui).
"$OS3M/bin/oracode-doc-coverage" --out "$DOCS_SERVING/doc-coverage.json" >/dev/null 2>&1 || echo "[push-nexus] doc-coverage WARN" >&2

# 2) pubblica stats.db su S3 (laptop -> bucket; egi-hub-deploy/fabiocherici-deploy ha PutObject)
aws s3 cp "$ROOT/backend/data/stats.db" "s3://${BUCKET}/stats.db" --region "$REGION" --profile "$PROFILE" >/dev/null 2>&1 \
  || { echo "[push-nexus] s3 cp FALLITO (profilo $PROFILE)" >&2; exit 0; }

# 2b) pubblica coverage.json su S3 (best-effort: la copertura non blocca lo stat)
[ -f "$ROOT/backend/data/coverage.json" ] && aws s3 cp "$ROOT/backend/data/coverage.json" "s3://${BUCKET}/coverage.json" --region "$REGION" --profile "$PROFILE" >/dev/null 2>&1 \
  || echo "[push-nexus] coverage s3 cp WARN" >&2

# 2c) pubblica drift.json su S3 (best-effort: il drift non blocca lo stat)
[ -f "$ROOT/backend/data/drift.json" ] && aws s3 cp "$ROOT/backend/data/drift.json" "s3://${BUCKET}/drift.json" --region "$REGION" --profile "$PROFILE" >/dev/null 2>&1 \
  || echo "[push-nexus] drift s3 cp WARN" >&2

# 2d) pubblica docs.serving.db su S3 (M-OS3-141, best-effort: la doc non blocca lo stat)
[ -f "$DOCS_SERVING/docs.serving.db" ] && aws s3 cp "$DOCS_SERVING/docs.serving.db" "s3://${BUCKET}/docs.serving.db" --region "$REGION" --profile "$PROFILE" >/dev/null 2>&1 \
  || echo "[push-nexus] docs.serving.db s3 cp WARN" >&2

# 2e) pubblica doc-coverage.json su S3 (M-OS3-141, best-effort)
[ -f "$DOCS_SERVING/doc-coverage.json" ] && aws s3 cp "$DOCS_SERVING/doc-coverage.json" "s3://${BUCKET}/doc-coverage.json" --region "$REGION" --profile "$PROFILE" >/dev/null 2>&1 \
  || echo "[push-nexus] doc-coverage s3 cp WARN" >&2

# 3) consegna al dev-server (EVENT-DRIVEN, no cron): l'EC2 tira giu via SSM (il suo ruolo ha GetObject)
aws ssm send-command --profile "$PROFILE" --region "$REGION" --instance-ids "$INSTANCE" \
  --document-name "AWS-RunShellScript" \
  --comment "nexus stats push (mission close)" \
  --parameters commands="[\"aws s3 cp s3://${BUCKET}/stats.db ${DEST}/backend/data/stats.db --region ${REGION}\",\"aws s3 cp s3://${BUCKET}/coverage.json ${DEST}/backend/data/coverage.json --region ${REGION} || true\",\"aws s3 cp s3://${BUCKET}/drift.json ${DEST}/backend/data/drift.json --region ${REGION} || true\",\"aws s3 cp s3://${BUCKET}/docs.serving.db ${DEST}/backend/data/docs.serving.db --region ${REGION} || true\",\"aws s3 cp s3://${BUCKET}/doc-coverage.json ${DEST}/backend/data/doc-coverage.json --region ${REGION} || true\"]" \
  --query 'Command.CommandId' --output text 2>/dev/null \
  || echo "[push-nexus] ssm send-command FALLITO (verifica perms ssm:SendCommand su $INSTANCE per $PROFILE)" >&2
# 4) ATTUATORE vault Obsidian (M-OS3-109): auto-sync del "secondo cervello" a ogni ciclo mission.
#    Best-effort: il fallimento NON blocca stat né mission. Instance-specific (vault del CEO via /mnt/c).
#    Rigenera l'export arricchito + rsync additivo nel vault (esclude .obsidian).
bash /home/fabio/os3-matrix/bin/export-ssot-to-vault >/dev/null 2>&1 \
  || echo "[push-nexus] obsidian vault sync best-effort fallito (vault non montato?)" >&2

# best-effort: mai bloccare il finalize (exit 0)
exit 0
