#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"

echo "[1/5] Creating Woo store"
CREATE_RESPONSE=$(curl -sS -X POST "$API_BASE/stores" -H 'Content-Type: application/json' -d '{"engine":"woocommerce"}')
STORE_ID=$(echo "$CREATE_RESPONSE" | sed -n 's/.*"store_id":"\([^"]*\)".*/\1/p')

if [ -z "$STORE_ID" ]; then
  echo "Failed to parse store_id"
  echo "$CREATE_RESPONSE"
  exit 1
fi

echo "Store ID: $STORE_ID"

echo "[2/5] Polling status"
for _ in $(seq 1 120); do
  DETAIL=$(curl -sS "$API_BASE/stores/$STORE_ID")
  STATUS=$(echo "$DETAIL" | sed -n 's/.*"status":"\([^"]*\)".*/\1/p')
  URL=$(echo "$DETAIL" | sed -n 's/.*"url":"\([^"]*\)".*/\1/p')
  echo "status=$STATUS"
  if [ "$STATUS" = "READY" ]; then
    echo "Store URL: $URL"
    break
  fi
  sleep 5
done

echo "[3/6] Optional: show release history + upgrade/rollback story"
echo "  ./scripts/store-history.sh $STORE_ID"
echo "  ./scripts/store-upgrade.sh $STORE_ID"
echo "  ./scripts/store-rollback.sh $STORE_ID <revision>"

echo "[4/6] Manual step: place test order on storefront"

echo "[5/6] Manual step: verify order in Woo admin"

echo "[6/6] Queue teardown"
curl -sS -X DELETE "$API_BASE/stores/$STORE_ID" >/dev/null

echo "Teardown queued"
