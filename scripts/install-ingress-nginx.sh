#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${INGRESS_NGINX_NAMESPACE:-ingress-nginx}"
RELEASE_NAME="${INGRESS_NGINX_RELEASE:-ingress-nginx}"
INGRESS_CLASS="${INGRESS_NGINX_CLASS:-nginx}"
CHART_VERSION="${INGRESS_NGINX_CHART_VERSION:-4.12.0}"

CACHE_ZONE="${STORE_CACHE_ZONE:-store_cache}"
CACHE_KEYS_ZONE_SIZE="${STORE_CACHE_KEYS_ZONE_SIZE:-100m}"
CACHE_MAX_SIZE="${STORE_CACHE_MAX_SIZE:-1g}"
CACHE_INACTIVE="${STORE_CACHE_INACTIVE:-4h}"
CACHE_PATH="${STORE_CACHE_PATH:-/tmp/nginx-cache}"

if ! command -v helm >/dev/null 2>&1; then
  echo "helm is required"
  exit 1
fi
if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required"
  exit 1
fi

echo "Adding/updating ingress-nginx Helm repo"
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx >/dev/null 2>&1 || true
helm repo update ingress-nginx

HTTP_SNIPPET="proxy_cache_path ${CACHE_PATH} levels=1:2 keys_zone=${CACHE_ZONE}:${CACHE_KEYS_ZONE_SIZE} max_size=${CACHE_MAX_SIZE} inactive=${CACHE_INACTIVE} use_temp_path=off;"

echo "Installing ingress-nginx release '${RELEASE_NAME}' in namespace '${NAMESPACE}' with ingress class '${INGRESS_CLASS}'"
helm upgrade --install "${RELEASE_NAME}" ingress-nginx/ingress-nginx \
  --namespace "${NAMESPACE}" \
  --create-namespace \
  --version "${CHART_VERSION}" \
  -f - <<YAML
controller:
  ingressClass: ${INGRESS_CLASS}
  ingressClassResource:
    name: ${INGRESS_CLASS}
    enabled: true
    default: false
  allowSnippetAnnotations: true
  config:
    allow-snippet-annotations: "true"
    annotations-risk-level: Critical
    http-snippet: |
      ${HTTP_SNIPPET}
YAML

echo "Waiting for ingress-nginx controller rollout"
kubectl -n "${NAMESPACE}" rollout status deploy/"${RELEASE_NAME}"-controller --timeout=180s

echo "Ingress classes:"
kubectl get ingressclass

echo "Done. ingress-nginx is ready for tenant-store caching."
