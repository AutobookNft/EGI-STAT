#!/usr/bin/env bash
# @purpose Pull SOLO del frontend dist da S3 sull'EC2 (stat.florenceegi.com) — M-267.
# @author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
# @version 1.0.0 (EGI-STAT)
# Per quando il bundle è già su S3 e serve solo aggiornare l'EC2 (no rebuild, no backend).
set -euo pipefail

PROFILE="${AWS_DEPLOY_PROFILE:-fabiocherici-deploy}"
REGION="eu-north-1"
INSTANCE="i-0940cdb7b955d1632"
S3_BASE="s3://florenceegi-media/_deploy/egi-stat"
DEST="/home/forge/stat.florenceegi.com"

CMD=$(aws ssm send-command --profile "$PROFILE" --region "$REGION" --instance-ids "$INSTANCE" \
  --document-name "AWS-RunShellScript" \
  --comment "pull frontend stat.florenceegi.com (M-267)" \
  --parameters commands="[
    \"set -e\",
    \"aws s3 sync ${S3_BASE}/frontend-dist/ ${DEST}/frontend/dist/ --delete --exact-timestamps\",
    \"chown -R forge:forge ${DEST}/frontend\",
    \"echo PULL_OK\"
  ]" \
  --query 'Command.CommandId' --output text)
echo "CommandId=$CMD"
aws ssm wait command-executed --profile "$PROFILE" --region "$REGION" --command-id "$CMD" --instance-id "$INSTANCE" || true
aws ssm get-command-invocation --profile "$PROFILE" --region "$REGION" --command-id "$CMD" --instance-id "$INSTANCE" \
  --query '[Status,StandardOutputContent,StandardErrorContent]' --output text
