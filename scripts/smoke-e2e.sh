#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"

echo "Checking health"
curl -fsS "$API_BASE/healthz" >/dev/null

echo "Creating store"
RESP=$(curl -sS -X POST "$API_BASE/stores" -H 'Content-Type: application/json' -d '{"engine":"woocommerce"}')
STORE_ID=$(echo "$RESP" | sed -n 's/.*"store_id":"\([^"]*\)".*/\1/p')
[ -n "$STORE_ID" ]

echo "Polling readiness"
READY=0
for _ in $(seq 1 120); do
  STATUS=$(curl -sS "$API_BASE/stores/$STORE_ID" | sed -n 's/.*"status":"\([^"]*\)".*/\1/p')
  if [ "$STATUS" = "READY" ]; then
    READY=1
    break
  fi
  sleep 5
done

if [ "$READY" -ne 1 ]; then
  echo "Store not ready in time"
  exit 1
fi

echo "Deleting store"
curl -sS -X DELETE "$API_BASE/stores/$STORE_ID" >/dev/null

echo "Smoke e2e passed through queueing stages"
