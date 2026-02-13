#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="storeplane"
SERVERS="${K3D_SERVERS:-1}"
AGENTS="${K3D_AGENTS:-1}"

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
  --servers "$SERVERS" \
  --agents "$AGENTS" \
  --port "80:80@loadbalancer" \
  --port "443:443@loadbalancer"

kubectl wait --for=condition=Ready nodes --all --timeout=180s

echo "Cluster $CLUSTER_NAME is ready (servers=$SERVERS agents=$AGENTS)"
echo "Try: kubectl get nodes"
