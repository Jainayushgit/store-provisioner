# System Design and Tradeoffs

## Architecture
The platform is a control plane running in Kubernetes with four core components:
- React dashboard for operator workflows.
- FastAPI backend exposing store lifecycle APIs.
- Platform Postgres for metadata, jobs, events, and rate-limit counters.
- In-process worker loop (inside backend deployment) that executes provisioning jobs using Helm.

Each store is isolated in a deterministic namespace (`store-<uuid>`) and Helm release (`store-<uuid>`). The worker installs the Woo chart with `helm upgrade --install --wait`, then validates HTTP readiness before marking `READY`.

## Data model
- `stores`: lifecycle state, namespace, URL, and failure reason.
- `provisioning_jobs`: queue with retry metadata and lease fields for idempotent processing.
- `store_events`: human-readable activity/audit timeline.
- `rate_limit_buckets`: simple IP-based abuse control.

## Reliability and idempotency
- Queue durability is DB-backed, not in-memory.
- Worker leasing uses `FOR UPDATE SKIP LOCKED`.
- Startup reconciliation requeues stale `IN_PROGRESS` jobs.
- Actions are deterministic by naming convention; retries target the same namespace/release.

## Security and guardrails
- Dedicated ServiceAccount and restricted ClusterRole/ClusterRoleBinding.
- Namespace-per-store isolation.
- Per-store ResourceQuota and LimitRange.
- Baseline NetworkPolicy template in store chart.
- No secrets in source; values/secrets are injected at deploy time.

## Local to production
The same charts are used for local and VPS deployments; only values differ:
- domain and ingress hosts
- storage class and persistence sizing
- image tags
- concurrency and resource settings

## Upgrade and rollback approach
- Each tenant maps to deterministic Helm release `store-<uuid>`.
- Upgrades are executed with `helm upgrade --reuse-values --wait` to preserve existing tenant config.
- Rollbacks use Helm revision history (`helm history` + `helm rollback <revision>`).
- Control-plane upgrades follow the same pattern on the `platform` release.

## Tradeoffs
- API and worker are colocated for faster iteration; can split later for independent scaling.
- WooCommerce is fully implemented while Medusa remains stubbed for Round 1 scope control.
- Postgres-based rate limiting is simple and sufficient for assignment scale, but Redis could improve high-throughput behavior.
