#!/usr/bin/env bash
# ==============================================================================
# Tenderpreneur / BoQPro Production Deployment Script
# Usage: ./deploy.sh
# ==============================================================================
set -euo pipefail

ENV_FILE=".env.production"

echo "============================================================"
echo "            BOQPRO PRODUCTION DEPLOYMENT"
echo "============================================================"

# 1. Check for .env.production file
if [ ! -f "$ENV_FILE" ]; then
    echo "[-] Error: '$ENV_FILE' not found."
    echo "    Please copy '.env.production.example' to '$ENV_FILE' and configure secrets."
    exit 1
fi

echo "[+] Loading environment configuration from $ENV_FILE..."
export $(grep -v '^#' "$ENV_FILE" | xargs)

# 2. Check that JWT secret is not the default
JWT_SECRET_VAL="${BOQPRO_JWT_SECRET:-${TENDERPRENEUR_JWT_SECRET:-}}"
if [[ "$JWT_SECRET_VAL" == *"replace_me"* ]] || [ ${#JWT_SECRET_VAL} -lt 32 ]; then
    echo "[-] Security Error: BOQPRO_JWT_SECRET is still set to placeholder or under 32 chars."
    echo "    Generate a strong secret with: openssl rand -hex 32"
    exit 1
fi

echo "[+] Building and starting Docker Compose services..."
docker compose -f docker-compose.yml --env-file "$ENV_FILE" build
docker compose -f docker-compose.yml --env-file "$ENV_FILE" up -d

echo "[+] Waiting for PostgreSQL database to be healthy..."
until docker compose -f docker-compose.yml exec -T postgres pg_isready -U "${POSTGRES_USER:-boqpro}" -d "${POSTGRES_DB:-boqpro}" > /dev/null 2>&1; do
    echo "    ... waiting for postgres"
    sleep 2
done
echo "[+] PostgreSQL is healthy."

echo "[+] Running database migrations (Alembic)..."
docker compose -f docker-compose.yml exec -T api alembic upgrade head
echo "[+] Migrations complete."

echo "[+] Verifying API health check..."
HEALTH_RESPONSE=$(docker compose -f docker-compose.yml exec -T api curl -s http://localhost:8000/health)
echo "    Health status: $HEALTH_RESPONSE"

echo "============================================================"
echo "    [SUCCESS] BOQPRO DEPLOYED SUCCESSFULLY!"
echo "  Web & API live at: https://${DOMAIN_NAME:-localhost}"
echo "============================================================"
