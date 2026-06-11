#!/usr/bin/env bash
# @purpose Push veloce del solo stats.db verso l'EC2 (dati cantiere "live") — M-266.
# @author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
# @version 1.0.0 (EGI-STAT)
# Da lanciare dopo le sessioni di lavoro (o in cron locale, es. ogni ora):
# rigenera lo SQLite dai registry locali e lo spedisce all'EC2 via S3+SSM.
set -euo pipefail

PROFILE="${AWS_DEPLOY_PROFILE:-fabiocherici-deploy}"
REGION="eu-north-1"
INSTANCE="i-0940cdb7b955d1632"
BUCKET="florenceegi-media"
S3_BASE="s3://${BUCKET}/_deploy/egi-stat"
DEST="/home/forge/stat.florenceegi.com"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

( cd "$ROOT/backend" && python3 aggregate_to_sqlite.py )
aws s3 cp "$ROOT/backend/data/stats.db" "${S3_BASE}/stats.db" --region "$REGION" --profile "$PROFILE"

CMD=$(aws ssm send-command --profile "$PROFILE" --region "$REGION" --instance-ids "$INSTANCE" \
  --document-name "AWS-RunShellScript" \
  --comment "push stats.db stat.florenceegi.com" \
  --parameters commands="[
    \"set -e\",
    \"aws s3 cp ${S3_BASE}/stats.db ${DEST}/backend/data/stats.db\",
    \"chown forge:forge ${DEST}/backend/data/stats.db\",
    \"echo STATS_PUSH_OK\"
  ]" \
  --query 'Command.CommandId' --output text)
aws ssm wait command-executed --profile "$PROFILE" --region "$REGION" --command-id "$CMD" --instance-id "$INSTANCE" || true
aws ssm get-command-invocation --profile "$PROFILE" --region "$REGION" --command-id "$CMD" --instance-id "$INSTANCE" \
  --query '[Status,StandardOutputContent]' --output text
