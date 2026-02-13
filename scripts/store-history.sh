#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <store-id|store-namespace>"
  echo "Example: $0 aaef12b7-a47f-4387-9552-3899429cba0f"
  echo "Example: $0 store-aaef12b7-a47f-4387-9552-3899429cba0f"
}

if [ $# -ne 1 ]; then
  usage
  exit 1
fi

raw="$1"
if [[ "$raw" == store-* ]]; then
  namespace="$raw"
else
  namespace="store-$raw"
fi
release="$namespace"

helm -n "$namespace" history "$release"
