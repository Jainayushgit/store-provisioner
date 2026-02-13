#!/usr/bin/env bash
set -euo pipefail

HELM_TIMEOUT_SECONDS="${HELM_TIMEOUT_SECONDS:-300}"

usage() {
  echo "Usage: $0 <store-id|store-namespace> <revision>"
  echo "Tip: run ./scripts/store-history.sh <store-id> first"
}

if [ $# -ne 2 ]; then
  usage
  exit 1
fi

raw="$1"
revision="$2"

if [[ "$raw" == store-* ]]; then
  namespace="$raw"
else
  namespace="store-$raw"
fi
release="$namespace"

echo "Rolling back release '$release' in namespace '$namespace' to revision '$revision'"
helm rollback "$release" "$revision" \
  -n "$namespace" \
  --wait \
  --timeout "${HELM_TIMEOUT_SECONDS}s"

echo "Rollback complete. Current history:"
helm -n "$namespace" history "$release"
