#!/usr/bin/env bash
# @purpose Deploy ripetibile stat.florenceegi.com (M-266) — EGI-STAT su EC2.
# @author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
# @version 1.0.0 (EGI-STAT)
# Pattern: replica tmp-le-vespe (M-LEVESPE-002/020): build → S3 → EC2 pull via SSM → nginx.
# In più rispetto al pattern statico: backend Python (venv+gunicorn systemd) + stats.db shipped.
# Uso: deploy/deploy-stat.sh /percorso/file-password   (password basic auth dashboard, 1 riga)
set -euo pipefail

PROFILE="${AWS_DEPLOY_PROFILE:-fabiocherici-deploy}"
REGION="eu-north-1"
INSTANCE="i-0940cdb7b955d1632"
SUB="stat.florenceegi.com"
BUCKET="florenceegi-media"
S3_BASE="s3://${BUCKET}/_deploy/egi-stat"
DEST="/home/forge/${SUB}"
USER_AUTH="egistat"

PASSFILE="${1:?Uso: deploy-stat.sh /percorso/file-password}"
PASS=$(head -1 "$PASSFILE")
HTLINE="${USER_AUTH}:$(openssl passwd -apr1 -stdin <<< "$PASS")"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> 1/6 build frontend"
( cd "$ROOT/frontend" && npm install --silent && npm run build )

echo "==> 2/6 rigenera serving SQLite dai registry locali"
( cd "$ROOT/backend" && python3 aggregate_to_sqlite.py )

echo "==> 3/6 push su S3: frontend dist + backend + db + vhost + systemd unit"
aws s3 sync "$ROOT/frontend/dist/" "${S3_BASE}/frontend-dist/" --delete --region "$REGION" --profile "$PROFILE"
tar -C "$ROOT" -czf /tmp/egi-stat-backend.tgz --exclude='__pycache__' --exclude='.venv' --exclude='*.log' backend
aws s3 cp /tmp/egi-stat-backend.tgz "${S3_BASE}/backend.tgz" --region "$REGION" --profile "$PROFILE"
aws s3 cp "$ROOT/backend/data/stats.db" "${S3_BASE}/stats.db" --region "$REGION" --profile "$PROFILE"
aws s3 cp "$ROOT/deploy/nginx/${SUB}.conf" "${S3_BASE}/nginx.conf" --region "$REGION" --profile "$PROFILE"
aws s3 cp "$ROOT/deploy/systemd/egi-stat.service" "${S3_BASE}/egi-stat.service" --region "$REGION" --profile "$PROFILE"

echo "==> 4/6 SSM: install su EC2 (htpasswd solo hash, venv, systemd, vhost, reload)"
CMD=$(aws ssm send-command --profile "$PROFILE" --region "$REGION" --instance-ids "$INSTANCE" \
  --document-name "AWS-RunShellScript" \
  --comment "deploy ${SUB} (M-266)" \
  --parameters commands="[
    \"set -e\",
    \"mkdir -p ${DEST}\",
    \"aws s3 sync ${S3_BASE}/frontend-dist/ ${DEST}/frontend/dist/ --delete\",
    \"aws s3 cp ${S3_BASE}/backend.tgz /tmp/egi-stat-backend.tgz\",
    \"tar -C ${DEST} -xzf /tmp/egi-stat-backend.tgz\",
    \"aws s3 cp ${S3_BASE}/stats.db ${DEST}/backend/data/stats.db\",
    \"cd ${DEST}/backend && python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt gunicorn\",
    \"chown -R forge:forge ${DEST}\",
    \"printf '%s\\n' '$HTLINE' > /etc/nginx/.htpasswd-egistat\",
    \"chmod 640 /etc/nginx/.htpasswd-egistat && chown root:www-data /etc/nginx/.htpasswd-egistat\",
    \"aws s3 cp ${S3_BASE}/egi-stat.service /etc/systemd/system/egi-stat.service\",
    \"systemctl daemon-reload && systemctl enable --now egi-stat && systemctl restart egi-stat\",
    \"aws s3 cp ${S3_BASE}/nginx.conf /etc/nginx/sites-available/${SUB}\",
    \"ln -sf /etc/nginx/sites-available/${SUB} /etc/nginx/sites-enabled/${SUB}\",
    \"nginx -t\",
    \"systemctl reload nginx\",
    \"echo STAT_DEPLOY_OK\"
  ]" \
  --query 'Command.CommandId' --output text)
echo "    CommandId=$CMD"

echo "==> 5/6 attendo esito SSM"
aws ssm wait command-executed --profile "$PROFILE" --region "$REGION" --command-id "$CMD" --instance-id "$INSTANCE" || true
aws ssm get-command-invocation --profile "$PROFILE" --region "$REGION" --command-id "$CMD" --instance-id "$INSTANCE" \
  --query '[Status,StandardOutputContent,StandardErrorContent]' --output text

echo "==> 6/6 done. Test: CREDS=\"${USER_AUTH}:<password>\" tests/m-266/test_public_site_stats.sh"
echo "NOTA DNS: il sottodominio ${SUB} deve puntare all'ALB (vedi /new-subdomain) e l'ALB"
echo "deve avere la rule host-header per ${SUB} → target EC2 (come tmp-le-vespe)."
