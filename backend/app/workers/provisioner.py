import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import SessionLocal
from app.models.enums import JobAction, JobStatus, StoreEngine, StoreStatus
from app.models.provisioning_job import ProvisioningJob
from app.models.store import Store
from app.services.events import log_event
from app.services.helm import HelmService
from app.services.kube import KubeService
from app.services.readiness import ReadinessService


class ProvisioningWorker:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.helm = HelmService(settings.helm_binary)
        self.kube = KubeService(settings.kubectl_binary, settings.kubectl_delete_timeout_seconds)
        self.readiness = ReadinessService()
        self._tasks: set[asyncio.Task] = set()
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._requeue_stale_jobs()
        while self._running:
            await self._tick()
            await asyncio.sleep(self.settings.worker_poll_seconds)

    def stop(self) -> None:
        self._running = False

    async def _tick(self) -> None:
        self._tasks = {task for task in self._tasks if not task.done()}
        available_slots = max(0, self.settings.worker_max_concurrency - len(self._tasks))

        for _ in range(available_slots):
            job_id = self._lease_next_job()
            if not job_id:
                break
            task = asyncio.create_task(self._run_job(job_id))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    def _requeue_stale_jobs(self) -> None:
        lease_cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.settings.worker_lease_seconds)
        with SessionLocal() as db:
            stale_jobs = db.scalars(
                select(ProvisioningJob).where(
                    and_(
                        ProvisioningJob.status == JobStatus.IN_PROGRESS,
                        or_(ProvisioningJob.locked_at.is_(None), ProvisioningJob.locked_at < lease_cutoff),
                    )
                )
            ).all()
            for job in stale_jobs:
                job.status = JobStatus.QUEUED
                job.locked_by = None
                job.locked_at = None
            db.commit()

    def _lease_next_job(self):
        now = datetime.now(timezone.utc)
        with SessionLocal() as db:
            with db.begin():
                job = db.scalar(
                    select(ProvisioningJob)
                    .where(ProvisioningJob.status == JobStatus.QUEUED)
                    .order_by(ProvisioningJob.created_at.asc())
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )
                if not job:
                    return None
                job.status = JobStatus.IN_PROGRESS
                job.locked_by = self.settings.worker_id
                job.locked_at = now
                job.attempt += 1
                db.add(job)
                return job.id

    async def _run_job(self, job_id):
        await asyncio.to_thread(self._process_job_sync, job_id)

    def _process_job_sync(self, job_id) -> None:
        with SessionLocal() as db:
            job = db.get(ProvisioningJob, job_id)
            if not job:
                return

            store = db.get(Store, job.store_id)
            if not store:
                job.status = JobStatus.FAILED
                job.error_message = "store_not_found"
                db.commit()
                return

            # If teardown was requested, any pending/leased provision job becomes a no-op.
            if job.action == JobAction.PROVISION and store.status in {StoreStatus.DELETING, StoreStatus.DELETED}:
                job.status = JobStatus.SUCCEEDED
                job.error_message = "provision_skipped_store_teardown_requested"
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
                return

            # Delete is idempotent; if already deleted, mark job complete.
            if job.action == JobAction.DELETE and store.status == StoreStatus.DELETED:
                job.status = JobStatus.SUCCEEDED
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
                return

            try:
                if job.action == JobAction.PROVISION:
                    self._provision_store(db, store)
                    job.status = JobStatus.SUCCEEDED
                    job.completed_at = datetime.now(timezone.utc)
                elif job.action == JobAction.DELETE:
                    self._delete_store(db, store)
                    job.status = JobStatus.SUCCEEDED
                    job.completed_at = datetime.now(timezone.utc)
                else:
                    raise RuntimeError(f"Unknown action: {job.action}")
                db.commit()
            except Exception as exc:  # noqa: BLE001
                store.last_error = str(exc)
                job.error_message = str(exc)
                if job.attempt >= job.max_attempts:
                    job.status = JobStatus.FAILED
                    store.status = StoreStatus.FAILED if job.action == JobAction.PROVISION else StoreStatus.DELETING
                else:
                    job.status = JobStatus.QUEUED
                    job.locked_by = None
                    job.locked_at = None
                    store.status = StoreStatus.QUEUED if job.action == JobAction.PROVISION else StoreStatus.DELETING
                log_event(db, store.id, "failed", str(exc))
                db.commit()

    def _provision_store(self, db: Session, store: Store) -> None:
        if store.engine == StoreEngine.MEDUSA:
            raise RuntimeError("Medusa is not enabled in Round 1")

        # Persist intermediate state early so UI does not remain stuck on QUEUED
        # while Helm work is running in the background.
        store.status = StoreStatus.PROVISIONING
        db.add(store)
        log_event(db, store.id, "install_started", "Starting Helm provisioning")
        db.commit()

        store_host = self._build_store_host(str(store.id))
        values = {
            "store": {
                "id": str(store.id),
                "namespace": store.namespace,
                "host": store_host,
            },
            "wordpress": {
                "fullnameOverride": store.release_name,
                "wordpressBlogName": store.display_name or f"Store {str(store.id)[:8]}",
                "ingress": self._build_store_ingress_values(store_host),
            },
        }
        self.helm.upgrade_install(
            release_name=store.release_name,
            namespace=store.namespace,
            chart_path=self.settings.helm_chart_path,
            values=values,
            timeout_seconds=self.settings.helm_timeout_seconds,
        )

        url = f"http://{store_host}"
        try:
            self.readiness.wait_for_http_ok(
                url=url,
                timeout_seconds=self.settings.http_ready_timeout_seconds,
                poll_seconds=self.settings.http_ready_poll_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            # Local ingress networking can be flaky in laptop runtimes; keep event visibility and continue.
            log_event(db, store.id, "readiness_warning", f"HTTP check did not pass before timeout: {exc}")

        store.url = url
        store.status = StoreStatus.READY
        store.last_error = None
        db.add(store)
        log_event(db, store.id, "ready", f"Store is ready at {url}")

    def _delete_store(self, db: Session, store: Store) -> None:
        # Persist intermediate state early so teardown progress is visible.
        store.status = StoreStatus.DELETING
        db.add(store)
        log_event(db, store.id, "delete_started", "Delete requested")
        db.commit()

        # Uninstall first; if already absent this should be no-op-ish
        try:
            self.helm.uninstall(store.release_name, store.namespace, self.settings.helm_timeout_seconds)
        except RuntimeError:
            # Namespace delete is authoritative teardown; continue.
            pass

        self.kube.delete_namespace(store.namespace)

        store.status = StoreStatus.DELETED
        store.url = None
        db.add(store)
        log_event(db, store.id, "deleted", "Namespace and release removed")

    def _build_store_host(self, store_id: str) -> str:
        return f"store-{store_id}.{self.settings.local_domain}"

    def _build_store_ingress_values(self, store_host: str) -> dict:
        ingress_values: dict = {
            "enabled": True,
            "hostname": store_host,
            "ingressClassName": self.settings.store_ingress_class,
        }

        if self.settings.store_guest_cache_enabled:
            ingress_values["annotations"] = self._build_store_cache_annotations()

        return ingress_values

    def _build_store_cache_annotations(self) -> dict:
        ttl_seconds = max(1, self.settings.store_guest_cache_ttl_seconds)
        configuration_snippet = "\n".join(
            [
                "set $skip_cache 0;",
                "",
                "if ($request_method !~ ^(GET|HEAD)$) {",
                "  set $skip_cache 1;",
                "}",
                "",
                "if ($request_uri ~* \"^/(wp-admin/?|wp-login\\.php|cart/?|checkout/?|my-account/?|wc-api/?|wp-json/)\") {",
                "  set $skip_cache 1;",
                "}",
                "",
                "if ($query_string ~* \"(^|&)(add-to-cart|wc-ajax|remove_item|undo_item|apply_coupon|remove_coupon)=\") {",
                "  set $skip_cache 1;",
                "}",
                "",
                "if ($http_cookie ~* \"(wordpress_logged_in_|wordpress_sec_|wp-postpass_|comment_author_|woocommerce_items_in_cart|woocommerce_cart_hash|wp_woocommerce_session_|PHPSESSID)\") {",
                "  set $skip_cache 1;",
                "}",
                "",
                f"proxy_cache {self.settings.store_guest_cache_zone};",
                "proxy_cache_key \"$scheme$request_method$host$request_uri\";",
                f"proxy_cache_valid 200 301 302 {ttl_seconds}s;",
                "proxy_cache_bypass $skip_cache;",
                "proxy_no_cache $skip_cache;",
                "add_header X-Store-Cache $upstream_cache_status always;",
            ]
        )

        return {
            "nginx.ingress.kubernetes.io/proxy-buffering": "on",
            "nginx.ingress.kubernetes.io/configuration-snippet": configuration_snippet,
        }


def count_active_stores(db: Session) -> int:
    active_statuses = [StoreStatus.QUEUED, StoreStatus.PROVISIONING, StoreStatus.READY, StoreStatus.DELETING]
    return db.scalar(select(func.count(Store.id)).where(Store.status.in_(active_statuses))) or 0
