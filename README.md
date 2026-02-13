# Urumi SDE Internship (Round 1): Store Provisioning Platform

This repository contains my Round 1 system design + implementation submission.

I built a Kubernetes-native control plane where a user can create and delete ecommerce stores from a dashboard.  
For this round, I fully implemented **WooCommerce provisioning** and kept the architecture extensible for **Medusa** later.

Demo video (5-8 min): [Loom walkthrough](https://www.loom.com/share/314882afc19b49b99fc26b83878ac09c)

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
| Local Kubernetes + Helm | `scripts/create-cluster.sh`, `charts/platform/Chart.yaml` | Run cluster script, then `helm upgrade --install ... -f values/values-local.yaml` | Platform comes up with pods + ingress |
| Same charts for local and VPS/k3s | `values/values-local.yaml`, `values/values-prod.yaml`, `docs/vps-runbook.md` | Verify chart + values split and follow runbook steps | Same chart model; VPS path is documented |
| Create/list/delete store | `backend/app/api/stores.py`, section 6 | Call `POST /stores`, `GET /stores`, `DELETE /stores/{id}` | `PROVISIONING -> READY`, then cleanup |
| Provisioning/orchestration | `backend/app/workers/provisioner.py`, `backend/app/services/helm.py` | Run `./scripts/demo-flow.sh` | Deterministic Helm install/uninstall per store |
| End-to-end order flow (Woo) | section 7, `scripts/demo-flow.sh` | Open storefront, checkout, verify in `/wp-admin` | Order is visible in Woo admin |
| Isolation and guardrails | `charts/woocommerce/templates/resourcequota.yaml`, `charts/woocommerce/templates/limitrange.yaml`, `charts/woocommerce/templates/networkpolicy.yaml` | `kubectl -n store-<id> get resourcequota,limitrange,networkpolicy` | Per-store guardrails are present |
| Reliability and idempotency | section 8, `docs/system-design.md`, `backend/app/workers/provisioner.py` | Observe retries/events and re-run flows | Lease-based retry-safe processing |
| Upgrade/rollback | `scripts/store-history.sh`, `scripts/store-upgrade.sh`, `scripts/store-rollback.sh` | Run history, upgrade, rollback scripts | Helm revisions and rollback work |
| Security and secrets | sections 8 and 10, `charts/platform/templates/backend.yaml`, `values/values-prod.yaml` | Check secret references in chart/values | Secrets are sourced via Kubernetes Secrets |

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

```mermaid
flowchart LR
  D["Dashboard (React)"] --> A["Backend API (FastAPI)"]
  A --> P["Postgres (stores, jobs, events, rate limits)"]
  A --> W["Worker Loop (lease + retry)"]
  W --> H["Helm upgrade/install/uninstall"]
  H --> N["Namespace per store: store-<id>"]
  N --> S["WordPress + WooCommerce Store"]
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

If you use Colima instead of Docker Desktop, use at least:

```bash
colima start --cpu 4 --memory 6 --disk 100
```

Optional helper (macOS):

```bash
./scripts/install-tools-macos.sh
```

### Step A: Create local cluster

```bash
./scripts/create-cluster.sh
kubectl get nodes
```

The script defaults to a stable local topology (`1 server + 1 agent`).
You can override with env vars:

```bash
K3D_SERVERS=1 K3D_AGENTS=2 ./scripts/create-cluster.sh
```

### Step B: Build images

Woo provisioning works with the chart defaults (`wordpressPlugins: woocommerce`).
If you want a pre-baked Woo image, an optional Dockerfile is available at `images/wordpress-woo/Dockerfile`.

Platform images:

```bash
docker build -f backend/Dockerfile -t <your-registry>/store-platform-backend:latest .
docker build -f dashboard/Dockerfile \
  --build-arg VITE_API_BASE_URL=http://localhost:8000 \
  -t <your-registry>/store-platform-dashboard:latest \
  ./dashboard
```

Update image references in:

- `charts/platform/values.yaml`
- `values/values-local.yaml` (or your chosen environment file)

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
- `GET /stores/{id}/admin-credentials` admin username/password + admin URL (local/dev only)
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
| 1) Production-like VPS deployment | Documented (not executed) | `docs/vps-runbook.md`, section 10, `values/values-prod.yaml` (VPS deployment path + Helm values split; TLS cert-manager notes included; custom domain linking out of Round 1 scope) |
| 2) Stronger multi-tenant isolation and guardrails | Implemented | `charts/woocommerce/templates/resourcequota.yaml`, `charts/woocommerce/templates/limitrange.yaml` (namespace-level ResourceQuota + LimitRange per store with PVC size limits and pod defaults) |
| 3) Idempotency and recovery | Implemented | section 8, `docs/system-design.md`, `backend/app/workers/provisioner.py` (lease-based retry-safe processing; clean reconcile on component restart; requeue for stale jobs) |
| 4) Abuse prevention beyond rate limiting | Implemented (core) | `backend/app/services/rate_limit.py`, `backend/app/models/rate_limit_bucket.py`, `backend/app/api/stores.py` (IP-based rate limiting + max active stores + provisioning timeouts + audit trail via event log) |
| 5) Observability | Implemented | `backend/app/services/events.py`, `backend/app/models/store_event.py`, `dashboard/src/components/store-events-panel.tsx` (store-level event log in dashboard; basic metrics at `/metrics`; failure visibility with reason reporting) |
| 6) Network and security hardening | Implemented | `charts/platform/templates/serviceaccount.yaml`, `charts/platform/templates/role.yaml`, `charts/woocommerce/templates/networkpolicy.yaml` (RBAC with least privilege; NetworkPolicy per namespace; non-root execution context) |
| 7) Scaling plan (implemented) | Implemented | section 11 (API/dashboard horizontal scaling; async worker with lease-based concurrency; stateful concerns documented) |
| 8) Upgrades and rollback story | Implemented | section 9, `scripts/store-history.sh`, `scripts/store-upgrade.sh`, `scripts/store-rollback.sh` (Helm revision tracking; upgrade/rollback scripts with demo) |

*Note*
I used codex in my workflow to implement the project