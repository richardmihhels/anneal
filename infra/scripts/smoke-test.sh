#!/usr/bin/env bash
# Post-deploy smoke test: hit /health on core and dashboard.
# Exits non-zero if any service is unhealthy.
#
# Usage: CORE_URL=https://... DASHBOARD_URL=https://... ./infra/scripts/smoke-test.sh
# URLs are printed by `terraform output` after apply.

set -euo pipefail

CORE_URL="${CORE_URL:?Set CORE_URL}"
DASHBOARD_URL="${DASHBOARD_URL:?Set DASHBOARD_URL}"

MAX_RETRIES=12
RETRY_DELAY=10

check() {
  local name="$1"
  local url="$2"
  local attempt=0

  echo "==> Checking $name at $url/health"
  until curl -fsS --max-time 10 "$url/health" > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge "$MAX_RETRIES" ]; then
      echo "FAIL: $name did not become healthy after $((MAX_RETRIES * RETRY_DELAY))s"
      return 1
    fi
    echo "    attempt $attempt/$MAX_RETRIES — retrying in ${RETRY_DELAY}s"
    sleep "$RETRY_DELAY"
  done

  echo "    OK: $name is healthy"
}

check "core"      "$CORE_URL"
check "dashboard" "$DASHBOARD_URL"

echo "==> All services healthy."
