#!/usr/bin/env bash
# ==============================================================================
# Tenderpreneur / BoQPro Production Deployment Script
# Usage: ./deploy.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$REPO_ROOT/.env.production"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"


echo "============================================================"
echo "            BOQPRO PRODUCTION DEPLOYMENT"
echo "============================================================"

# 1. Check for .env.production file
if [ ! -f "$ENV_FILE" ]; then
    echo "[-] Error: '$ENV_FILE' not found."
    echo "    Please copy '.env.production.example' to '$REPO_ROOT/.env.production' and configure secrets."
    exit 1
fi

echo "[+] Loading environment configuration from $ENV_FILE..."
set -a
source "$ENV_FILE"
set +a

# 2. Validate required production secrets and settings
JWT_SECRET_VAL="${BOQPRO_JWT_SECRET:-${TENDERPRENEUR_JWT_SECRET:-}}"
PASSWORD_SALT_VAL="${BOQPRO_PASSWORD_SALT:-${TENDERPRENEUR_PASSWORD_SALT:-}}"
if [[ -z "$JWT_SECRET_VAL" ]] || [[ "$JWT_SECRET_VAL" == *"replace_me"* ]] || [ ${#JWT_SECRET_VAL} -lt 32 ]; then
    echo "[-] Security Error: BOQPRO_JWT_SECRET is still missing, placeholder, or under 32 chars."
    echo "    Generate a strong secret with: openssl rand -hex 32"
    exit 1
fi
if [[ -z "$PASSWORD_SALT_VAL" ]] || [[ "$PASSWORD_SALT_VAL" == *"replace_me"* ]] || [ ${#PASSWORD_SALT_VAL} -lt 32 ]; then
    echo "[-] Security Error: BOQPRO_PASSWORD_SALT is still missing, placeholder, or under 32 chars."
    echo "    Generate a strong salt with: openssl rand -hex 32"
    exit 1
fi
if [[ "${BOQPRO_DATABASE_URL:-}" != postgresql* ]]; then
    echo "[-] Security Error: BOQPRO_DATABASE_URL must use PostgreSQL in production."
    exit 1
fi
if ! python - "$BOQPRO_CORS_ORIGINS" <<'PY'
import json
import sys

try:
    origins = json.loads(sys.argv[1])
except json.JSONDecodeError:
    sys.exit(1)

if not isinstance(origins, list) or not origins or not all(
    isinstance(origin, str) and origin.startswith("https://") for origin in origins
):
    sys.exit(1)
PY
then
    echo "[-] Security Error: BOQPRO_CORS_ORIGINS must contain HTTPS origins only."
    exit 1
fi

echo "[+] Building and starting Docker Compose services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

echo "[+] Waiting for PostgreSQL database to be healthy..."
until docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U "${POSTGRES_USER:-boqpro}" -d "${POSTGRES_DB:-boqpro}" > /dev/null 2>&1; do
    echo "    ... waiting for postgres"
    sleep 2
done
echo "[+] PostgreSQL is healthy."

echo "[+] Running database migrations (Alembic)..."
docker compose -f "$COMPOSE_FILE" exec -T api sh -lc 'cd /app && alembic upgrade head'
echo "[+] Migrations complete."

echo "[+] Verifying API health check..."
HEALTH_RESPONSE=$(docker compose -f "$COMPOSE_FILE" exec -T api curl -s http://localhost:8000/health)
echo "    Health status: $HEALTH_RESPONSE"

echo "============================================================"
echo "    [SUCCESS] BOQPRO DEPLOYED SUCCESSFULLY!"
echo "  Web & API live at: https://${DOMAIN_NAME:-localhost}"
echo "============================================================"
