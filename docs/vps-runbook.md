# VPS Runbook (k3s, production-like)


## 1) What changes from local

Only values and infrastructure primitives change:

- `LOCAL_DOMAIN`: `localtest.me` -> `stores.example.com`
- ingress hosts: local -> public DNS (`controlplane.example.com`, `api.controlplane.example.com`)
- tenant store ingress class: `nginx` (with ingress-nginx cache zone for guest pages)
- backend replicas/concurrency: higher in prod overlay
- image tags: pinned immutable tags instead of local/dev tags

Core code and Helm charts remain the same.

## 2) Prerequisites

- One VPS (Hetzner/Vultr/DO/Linode)
- Domain with DNS control
- Wildcard DNS for tenant stores:
  - `*.stores.example.com` -> VPS public IP
- Dashboard/API DNS:
  - `controlplane.example.com` -> VPS public IP
  - `api.controlplane.example.com` -> VPS public IP
- Docker registry for images (Docker Hub/GHCR)

## 3) Provision host and install k3s

```bash
# On VPS
curl -sfL https://get.k3s.io | sh -
sudo kubectl get nodes
```

Install Helm locally on the VPS (or from your laptop with kubeconfig access):

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

Install ingress-nginx for tenant store traffic (Traefik remains for existing platform ingress):

```bash
./scripts/install-ingress-nginx.sh
kubectl get ingressclass
```

## 4) Build and push images

From repo root:

```bash
docker build -f backend/Dockerfile -t <registry>/store-platform-backend:<tag> .
docker build -f dashboard/Dockerfile \
  --build-arg VITE_API_BASE_URL=https://api.controlplane.example.com \
  -t <registry>/store-platform-dashboard:<tag> \
  ./dashboard

docker push <registry>/store-platform-backend:<tag>
docker push <registry>/store-platform-dashboard:<tag>
```

## 5) Configure production values

Edit `values/values-prod.yaml`:

- `backend.image`: `<registry>/store-platform-backend:<tag>`
- `dashboard.image`: `<registry>/store-platform-dashboard:<tag>`
- `ingress.dashboardHost`: `controlplane.example.com`
- `ingress.backendHost`: `api.controlplane.example.com`
- `backend.env.LOCAL_DOMAIN`: `stores.example.com`
- `backend.env.STORE_INGRESS_CLASS`: `nginx`
- `backend.env.STORE_GUEST_CACHE_ENABLED`: `"true"`
- `backend.env.STORE_GUEST_CACHE_TTL_SECONDS`: `"14400"`
- `backend.env.STORE_GUEST_CACHE_ZONE`: `store_cache`

## 6) Deploy platform chart

```bash
helm upgrade --install platform ./charts/platform \
  -n platform \
  --create-namespace \
  -f values/values-prod.yaml
```

Optional hardening: provide existing secrets instead of chart-managed ones:

```bash
kubectl -n platform create secret generic platform-postgres-secret \
  --from-literal=POSTGRES_DB=platform \
  --from-literal=POSTGRES_USER=postgres \
  --from-literal=POSTGRES_PASSWORD='<strong-password>'
```

Then set `postgres.existingSecret: platform-postgres-secret` and `backend.existingSecret: platform-backend-secret` in values (or create `platform-backend-secret` with `DATABASE_URL`).

## 7) Run DB migrations

```bash
kubectl -n platform exec deploy/platform-backend -- alembic upgrade head
```

## 8) Verify platform health

```bash
kubectl -n platform get pods
kubectl -n platform get ingress
curl -fsS https://api.controlplane.example.com/healthz
```

## 9) Verify end-to-end tenant flow

1. Open dashboard at `https://controlplane.example.com`.
2. Create a Woo store.
3. Wait for `READY`.
4. Open `http://store-<id>.stores.example.com`.
5. Add product -> checkout using COD/Cheque.
6. Open admin (`/wp-admin`) and verify order exists.
7. Delete store and confirm namespace removal.

## 10) Upgrade and rollback operations

Per-store Helm release name is deterministic: `store-<store-id>`.

```bash
./scripts/store-history.sh <store-id>
./scripts/store-upgrade.sh <store-id>
./scripts/store-rollback.sh <store-id> <revision>
```

Platform release rollback:

```bash
helm -n platform history platform
helm -n platform rollback platform <revision>
```

## 11) Optional TLS hardening

- Add `cert-manager`
- Issue certs for control-plane hosts and wildcard tenant hosts
- Enforce HTTPS redirects at ingress

## 12) Roll-forward / rollback rule of thumb

- Prefer `helm upgrade --install` with immutable image tags.
- If post-upgrade checks fail, rollback immediately to previous Helm revision.
- Keep DB migration strategy backward-compatible for one release whenever possible.
