# Urumi Round 1 - Kubernetes Store Provisioning Control Plane

A Woo-first multi-tenant store provisioning platform with:
- React dashboard (`shadcn`-style component architecture, minimalist warm-neutral theme)
- FastAPI backend + in-process worker
- Platform Postgres metadata store
- Helm-based Kubernetes provisioning into namespace-per-store isolation

Round 1 scope fully implements WooCommerce provisioning. Medusa is intentionally stubbed for future extension.

## Repo Structure

```text
backend/                 FastAPI, worker, models, migrations, tests
dashboard/               Vite + React + TypeScript dashboard
charts/platform/         Helm chart for control-plane components
charts/woocommerce/      Helm wrapper chart for store provisioning
docs/system-design.md    Architecture + tradeoffs
values/                  local and prod value overlays
scripts/                 setup + demo helper scripts
images/wordpress-woo/    Dockerfile with Woo plugin pre-bundled
```

## Prerequisites

- macOS + Homebrew (or equivalent Linux tooling)
- Docker Desktop running
- `kubectl`, `helm`, `k3d`
- Python 3.12+
- Node 22+

Install tooling on macOS:

```bash
./scripts/install-tools-macos.sh
```

## Local Setup

### 1) Create Kubernetes cluster

```bash
./scripts/create-cluster.sh
kubectl get nodes
```

### 2) Build and push Woo-enabled WordPress image

```bash
docker build -t <your-registry>/wordpress-woo:latest ./images/wordpress-woo
# push image to a registry accessible by your cluster
```

Build backend/dashboard images (from repo root so backend image includes store chart):

```bash
docker build -f backend/Dockerfile -t <your-registry>/store-platform-backend:latest .
docker build -f dashboard/Dockerfile \
  --build-arg VITE_API_BASE_URL=http://localhost:8000 \
  -t <your-registry>/store-platform-dashboard:latest \
  ./dashboard
```

Update chart values with your image:
- `charts/woocommerce/values.yaml`
- `values/values-local.yaml`

### 3) Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker run -d --name platform-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=platform -p 5432:5432 postgres:17-alpine
alembic upgrade head
export HELM_CHART_PATH=../charts/woocommerce
uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`.

### 4) Dashboard setup

```bash
cd dashboard
npm install
npm run dev
```

Dashboard runs on `http://localhost:5173`.

Set API base if needed:

```bash
export VITE_API_BASE_URL=http://localhost:8000
```

## API Contract

- `POST /stores` -> queue store creation (Woo enabled, Medusa rejected for Round 1)
- `GET /stores` -> list stores
- `GET /stores/{id}` -> store details + events
- `DELETE /stores/{id}` -> queue teardown
- `GET /healthz` -> health
- `GET /metrics` -> Prometheus metrics endpoint

## Definition of Done Verification (WooCommerce)

1. Create store in dashboard.
2. Wait for `READY` status.
3. Open store URL (`store-<id>.localtest.me`).
4. Add product to cart and checkout using COD/dummy gateway.
5. Confirm order appears in Woo admin.
6. Delete store from dashboard and verify namespace cleanup.

## Demo Flow (5-8 mins)

1. Show architecture and queue model.
2. Create store from dashboard.
3. Show namespace and resources:
   ```bash
   kubectl get ns
   kubectl get all -n store-<id>
   ```
4. Place order + verify admin order.
5. Show activity log/failure visibility.
6. Delete store and show namespace removed.

Helper script:

```bash
./scripts/demo-flow.sh
```

## Upgrade and Rollback Story (Helm Revisions)

Each store is a deterministic Helm release: `release = namespace = store-<store-id>`.
This gives a concrete per-tenant upgrade and rollback path with built-in Helm revision history.

Inspect release history:

```bash
./scripts/store-history.sh <store-id>
```

Upgrade a store safely (reuses current values):

```bash
./scripts/store-upgrade.sh <store-id>
```

Upgrade with an explicit override (example):

```bash
./scripts/store-upgrade.sh <store-id> --set wordpress.wordpressBlogName="Round 1 Store v2"
```

Rollback to a previous revision:

```bash
./scripts/store-rollback.sh <store-id> <revision>
```

These scripts use `--wait` and timeout guardrails so failures are visible and bounded.

## Security and Guardrails Implemented

- Dedicated ServiceAccount + restricted ClusterRole/Binding (`charts/platform/templates`)
- Namespace-per-store isolation
- Per-store `ResourceQuota` and `LimitRange`
- Baseline `NetworkPolicy` template
- Non-root execution context in platform chart
- No secrets hardcoded in app source

## Reliability and Recovery

- `provisioning_jobs` table with retries and lease metadata
- `FOR UPDATE SKIP LOCKED` job leasing
- startup stale-job requeue logic
- deterministic namespace/release naming (`store-<uuid>`)
- `helm --wait` with HTTP readiness check events (best-effort for local ingress quirks)

## Tests

Backend tests:

```bash
cd backend
source .venv/bin/activate
pytest
```

Current tests cover rate-limiting behavior and request identity parsing.

## Platform Helm Deployment

Deploy control plane chart:

```bash
helm upgrade --install platform ./charts/platform -n platform --create-namespace -f values/values-local.yaml
```

Optional production-like (k3s/VPS) values overlay:

```bash
helm upgrade --install platform ./charts/platform -n platform --create-namespace -f values/values-prod.yaml
```

Backend API ingress host is configurable through:
- `ingress.backendHost` in `values/values-local.yaml`
- `ingress.backendHost` in `values/values-prod.yaml`

## VPS/Production Runbook

A full production-like runbook is included here:

- `docs/vps-runbook.md`

You can submit with this runbook even if you do not perform a live VPS deployment in Round 1.
It documents exact value differences, rollout/rollback commands, and a safe promotion path.

## Notes for Interview

A local decision log is maintained in `notepad.md` (gitignored) with:
- what was implemented
- why the decision was made
- alternatives rejected
- accepted tradeoffs
