# Urumi SDE Internship (Round 1): Store Provisioning Platform

This repository contains my Round 1 system design + implementation submission.

I built a Kubernetes-native control plane where a user can create and delete ecommerce stores from a dashboard.  
For this round, I fully implemented **WooCommerce provisioning** and kept the architecture extensible for **Medusa** later.

## 1) What I Built

- React dashboard for store operations and status visibility
- FastAPI backend for APIs + orchestration
- Postgres metadata store for jobs, stores, and events
- Helm-based provisioning into **namespace-per-store** isolation
- Local-to-prod setup using the **same charts**, with environment differences handled through values files

## 2) Requirement Coverage (Round 1)

The platform supports:

- Create store from dashboard
- List stores with status (`PROVISIONING`, `READY`, `FAILED`)
- Store URLs and timestamps in the UI
- Concurrent multi-store provisioning
- Delete store with namespace/release cleanup
- HTTP exposure through ingress with stable host pattern

Scope decision:

- **Implemented:** WooCommerce end-to-end
- **Stubbed by design:** Medusa provisioning path (explicitly out of Round 1 implementation scope)

### Requirement -> Proof Map

| Requirement | Where to verify | How to verify quickly | Expected result |
| --- | --- | --- | --- |
| Local Kubernetes + Helm | `scripts/create-cluster.sh`, `charts/platform/Chart.yaml` | Run `./scripts/create-cluster.sh` then `helm upgrade --install platform ./charts/platform -n platform --create-namespace -f values/values-local.yaml` | Platform pods and ingress resources are created |
| Same charts for local and VPS/k3s | `values/values-local.yaml`, `values/values-prod.yaml`, `docs/vps-runbook.md` | Compare values files, then run local/prod Helm commands from sections 10 and `docs/vps-runbook.md` | Only values change between environments |
| Create/list/delete store | `backend/app/api/stores.py`, section 6 API list | Use dashboard or call `POST /stores`, `GET /stores`, `DELETE /stores/{id}` | Store lifecycle transitions from `PROVISIONING` to `READY`, then cleanup on delete |
| Provisioning/orchestration flow | `backend/app/workers/provisioner.py`, `backend/app/services/helm.py` | Run `./scripts/demo-flow.sh` | Deterministic namespace/release provisioning via Helm |
| End-to-end order flow (Woo) | section 7, `scripts/demo-flow.sh` | Open store URL, add to cart, checkout, verify in `/wp-admin` | Order appears in Woo admin |
| Isolation and guardrails | `charts/woocommerce/templates/resourcequota.yaml`, `charts/woocommerce/templates/limitrange.yaml`, `charts/woocommerce/templates/networkpolicy.yaml` | Provision a store, then inspect namespace resources with `kubectl -n store-<id> get resourcequota,limitrange,networkpolicy` | Per-store quota/limits/network policy exist |
| Reliability and idempotency | section 8, `docs/system-design.md`, `backend/app/workers/provisioner.py` | Create store and observe events/status; rerun operations via scripts | Retry-safe, lease-based job processing with clear status events |
| Upgrade/rollback story | `scripts/store-history.sh`, `scripts/store-upgrade.sh`, `scripts/store-rollback.sh` | Run history/upgrade/rollback scripts for a store | Helm revision history and rollback are functional |
| Security + secrets handling | section 8 and 10, `charts/platform/templates/backend.yaml`, `values/values-prod.yaml` | Inspect manifests/values for secret refs | Secrets consumed via Kubernetes Secrets, not hardcoded in code |

## 3) High-Level Architecture

```text
Dashboard (React)
   -> Backend API (FastAPI)
      -> Job table in Postgres
      -> Worker loop (lease + retry)
         -> Helm install/upgrade/uninstall
            -> Namespace-per-store Kubernetes resources
               -> WordPress + WooCommerce store
```

Key design choices:

- Deterministic naming (`store-<id>`) for namespace and release
- Async job orchestration instead of blocking API requests
- Event logging for traceability and failure visibility
- Helm as the deployment primitive for both local and VPS/k3s

## 4) Repo Layout

```text
backend/                 FastAPI app, worker, DB models, migrations, tests
dashboard/               Vite + React + TypeScript UI
charts/platform/         Helm chart for control-plane services
charts/woocommerce/      Helm chart used by provisioner for tenant stores
values/                  Local and production value overlays
docs/system-design.md    Detailed architecture and tradeoffs
docs/vps-runbook.md      Production-like k3s runbook
scripts/                 Setup, verification, demo, upgrade, rollback scripts
images/wordpress-woo/    Woo-enabled WordPress image build context
```

## 5) Local Setup (Interview Demo Path)

### Prerequisites

- Docker Desktop
- `kubectl`, `helm`, `k3d`
- Python 3.12+
- Node 22+

Optional helper (macOS):

```bash
./scripts/install-tools-macos.sh
```

### Step A: Create local cluster

```bash
./scripts/create-cluster.sh
kubectl get nodes
```

### Step B: Build images

Woo-enabled WordPress image:

```bash
docker build -t <your-registry>/wordpress-woo:latest ./images/wordpress-woo
```

Platform images:

```bash
docker build -f backend/Dockerfile -t <your-registry>/store-platform-backend:latest .
docker build -f dashboard/Dockerfile \
  --build-arg VITE_API_BASE_URL=http://localhost:8000 \
  -t <your-registry>/store-platform-dashboard:latest \
  ./dashboard
```

Update image references in:

- `charts/woocommerce/values.yaml`
- `values/values-local.yaml`

### Step C: Start backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export LOCAL_DB_PASSWORD="$(openssl rand -hex 12)"
docker run -d --name platform-postgres \
  -e POSTGRES_PASSWORD="$LOCAL_DB_PASSWORD" \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_DB=platform \
  -p 5432:5432 postgres:17-alpine
export DATABASE_URL="postgresql+psycopg://postgres:$LOCAL_DB_PASSWORD@localhost:5432/platform"
alembic upgrade head
export HELM_CHART_PATH=../charts/woocommerce
uvicorn app.main:app --reload
```

Backend URL: `http://localhost:8000`

### Step D: Start dashboard

```bash
cd dashboard
npm install
npm run dev
```

Dashboard URL: `http://localhost:5173`

## 6) API Endpoints

- `POST /stores` create store job (Woo allowed, Medusa currently rejected for Round 1)
- `GET /stores` list stores
- `GET /stores/{id}` store details + event log
- `DELETE /stores/{id}` delete store job
- `GET /healthz` health check
- `GET /metrics` Prometheus-style metrics

## 7) Definition of Done Validation (WooCommerce)

1. Create a store from the dashboard.
2. Wait until status is `READY`.
3. Open store URL (`store-<id>.localtest.me`).
4. Add product to cart and checkout (COD/dummy).
5. Confirm order in Woo admin.
6. Delete the store and verify namespace removal.

Quick demo helper:

```bash
./scripts/demo-flow.sh
```

## 8) Reliability, Isolation, and Security

Reliability:

- Job table with retry metadata
- Lease-based worker behavior using DB locking (`FOR UPDATE SKIP LOCKED`)
- Requeue behavior for stale in-progress jobs on startup
- `helm --wait` plus readiness verification events

Isolation and guardrails:

- Namespace-per-store isolation
- Per-store `ResourceQuota` and `LimitRange`
- Baseline `NetworkPolicy` template

Security posture:

- Dedicated service account + restricted RBAC for platform components
- Platform DB credentials are injected via Kubernetes Secrets (not plain env literals in manifests)
- Chart defaults avoid committing real credentials; local/dev values are placeholders or generated at deploy time
- Non-root execution context in platform deployment

## 9) Upgrade / Rollback Story

Each store is managed as its own Helm release, which provides revision history.

```bash
./scripts/store-history.sh <store-id>
./scripts/store-upgrade.sh <store-id>
./scripts/store-rollback.sh <store-id> <revision>
```

## 10) Local-to-Production (k3s/VPS)

The same chart is reused across environments; differences are configured through values files.

Local example:

```bash
helm upgrade --install platform ./charts/platform \
  -n platform --create-namespace \
  -f values/values-local.yaml
```

Production-like example:

```bash
helm upgrade --install platform ./charts/platform \
  -n platform --create-namespace \
  -f values/values-prod.yaml
```

Detailed runbook: `docs/vps-runbook.md`

Secret handling in the platform chart:

- Postgres credentials are sourced from a Kubernetes Secret (`platform-postgres-secret` by default).
- Backend reads `DATABASE_URL` from a Kubernetes Secret (`platform-backend-secret` by default).
- You can wire externally managed secrets via `postgres.existingSecret` and `backend.existingSecret`.

## 11) Tradeoffs and What I Would Do Next

What I optimized for in Round 1:

- Clear and demonstrable end-to-end Woo flow
- Safe tenant isolation and cleanup
- Operational simplicity (Helm + deterministic naming + scriptable ops)

Known limitations:

- Medusa path is intentionally not implemented yet
- Some production hardening (full secret manager integration, stronger policy controls, autoscaling stress tests) is future work

If this were extended, I would prioritize:

1. Medusa provisioning implementation using the same orchestration contract
2. Dedicated async worker deployment with queue back-pressure controls
3. Stronger policy enforcement and observability dashboards

## 12) Stand Out Coverage

| Stand out item from brief | Status | Evidence |
| --- | --- | --- |
| Production-like VPS deployment on k3s with same Helm charts | Implemented | `docs/vps-runbook.md`, section 10, `values/values-prod.yaml` |
| Documented local vs prod differences via Helm values | Implemented | section 10, `values/values-local.yaml`, `values/values-prod.yaml` |
| Optional TLS notes | Implemented (notes) | `docs/vps-runbook.md` section 11 |
| Stronger multi-tenant guardrails (`ResourceQuota`, `LimitRange`) | Implemented | `charts/woocommerce/templates/resourcequota.yaml`, `charts/woocommerce/templates/limitrange.yaml` |
| Idempotency and recovery behavior | Implemented | section 8, `docs/system-design.md`, `backend/app/workers/provisioner.py` |
| Abuse prevention beyond simple rate limiting | Partial | `backend/app/services/rate_limit.py`, `backend/app/models/rate_limit_bucket.py`; per-user quota is planned |
| Observability/activity log surfaced to operator | Implemented | `backend/app/services/events.py`, `backend/app/models/store_event.py`, `dashboard/src/components/store-events-panel.tsx` |
| Optional custom-domain linking from dashboard | Planned | Not implemented in Round 1 scope |
