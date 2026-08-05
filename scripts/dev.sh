#!/usr/bin/env bash
set -euo pipefail

command -v docker >/dev/null || {
  echo "Docker is required for make dev. Use make demo for the zero-service UI demo." >&2
  exit 1
}

docker compose up -d --wait postgres clickhouse

export ANNEAL_ENV="${ANNEAL_ENV:-development}"
export ANNEAL_ORG_ID="${ANNEAL_ORG_ID:-org_demo}"
export ANNEAL_API_KEY="${ANNEAL_API_KEY:-dev_optional}"
export POSTGRES_URL="${POSTGRES_URL:-postgresql://anneal:anneal@localhost:${POSTGRES_PORT:-5432}/anneal}"
export CLICKHOUSE_URL="${CLICKHOUSE_URL:-http://localhost:${CLICKHOUSE_HTTP_PORT:-8123}/anneal}"
export CLICKHOUSE_DB="${CLICKHOUSE_DB:-anneal}"

(
  cd dashboard
  ANNEAL_DATA_SOURCE=api \
    ANNEAL_ENDPOINT="${ANNEAL_ENDPOINT:-http://localhost:8000}" \
    ANNEAL_ORG_ID="$ANNEAL_ORG_ID" \
    ANNEAL_API_KEY="$ANNEAL_API_KEY" \
    ANNEAL_DEMO_MODE=true \
    npm run dev
) &
dashboard_pid=$!

cleanup() {
  kill "$dashboard_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

uv run uvicorn core.main:app --reload --port 8000
