#!/usr/bin/env bash
# @package  EGI-STAT/deploy
# @author   Padmin D. Curtis (Supervisor-CTO, AI Partner OS3.0) for Fabio Cherici
# @version  1.0.0 (M-FUC-052)
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

# 1) rigenera l'aggregate dai registri (questo gia avveniva: era lo stats_refresh_cmd precedente)
( cd "$ROOT/backend" && python3 aggregate_to_sqlite.py >/dev/null 2>&1 ) || echo "[push-nexus] aggregate WARN" >&2

# 2) pubblica stats.db su S3 (laptop -> bucket; egi-hub-deploy/fabiocherici-deploy ha PutObject)
aws s3 cp "$ROOT/backend/data/stats.db" "s3://${BUCKET}/stats.db" --region "$REGION" --profile "$PROFILE" >/dev/null 2>&1 \
  || { echo "[push-nexus] s3 cp FALLITO (profilo $PROFILE)" >&2; exit 0; }

# 3) consegna al dev-server (EVENT-DRIVEN, no cron): l'EC2 tira giu via SSM (il suo ruolo ha GetObject)
aws ssm send-command --profile "$PROFILE" --region "$REGION" --instance-ids "$INSTANCE" \
  --document-name "AWS-RunShellScript" \
  --comment "nexus stats push (mission close)" \
  --parameters commands="[\"aws s3 cp s3://${BUCKET}/stats.db ${DEST}/backend/data/stats.db --region ${REGION}\"]" \
  --query 'Command.CommandId' --output text 2>/dev/null \
  || echo "[push-nexus] ssm send-command FALLITO (verifica perms ssm:SendCommand su $INSTANCE per $PROFILE)" >&2
# best-effort: mai bloccare il finalize (exit 0)
exit 0
