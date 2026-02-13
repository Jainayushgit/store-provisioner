#!/usr/bin/env bash
set -euo pipefail

CHART_PATH="${CHART_PATH:-./charts/woocommerce}"
HELM_TIMEOUT_SECONDS="${HELM_TIMEOUT_SECONDS:-300}"

usage() {
  echo "Usage: $0 <store-id|store-namespace> [extra helm args]"
  echo "Example: $0 aaef12b7-a47f-4387-9552-3899429cba0f --set wordpress.wordpressBlogName='Round 1 Store v2'"
}

if [ $# -lt 1 ]; then
  usage
  exit 1
fi

raw="$1"
shift

if [[ "$raw" == store-* ]]; then
  namespace="$raw"
else
  namespace="store-$raw"
fi
release="$namespace"

echo "Upgrading release '$release' in namespace '$namespace'"
helm upgrade "$release" "$CHART_PATH" \
  -n "$namespace" \
  --reuse-values \
  --wait \
  --timeout "${HELM_TIMEOUT_SECONDS}s" \
  "$@"

echo "Upgrade complete. Current history:"
helm -n "$namespace" history "$release"
