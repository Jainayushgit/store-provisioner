#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="storeplane"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required"
  exit 1
fi
if ! command -v k3d >/dev/null 2>&1; then
  echo "k3d is required"
  exit 1
fi
if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required"
  exit 1
fi

k3d cluster create "$CLUSTER_NAME" \
  --servers 1 \
  --agents 2 \
  --port "80:80@loadbalancer" \
  --port "443:443@loadbalancer"

kubectl wait --for=condition=Ready nodes --all --timeout=180s

echo "Cluster $CLUSTER_NAME is ready"
echo "Try: kubectl get nodes"
