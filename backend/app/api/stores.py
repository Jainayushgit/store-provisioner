import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from prometheus_client import Counter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.enums import JobAction, JobStatus, StoreEngine, StoreStatus
from app.models.provisioning_job import ProvisioningJob
from app.models.store import Store
from app.models.store_event import StoreEvent
from app.schemas.store import (
    CreateStoreRequest,
    EnqueueResponse,
    StoreDetailResponse,
    StoreEventResponse,
    StoreResponse,
)
from app.services.events import log_event
from app.services.rate_limit import RateLimiter
from app.workers.provisioner import count_active_stores

router = APIRouter(prefix="/stores", tags=["stores"])
settings = get_settings()
rate_limiter = RateLimiter(settings.rate_limit_create_delete_per_window, settings.rate_limit_window_seconds)
stores_created_total = Counter("stores_created_total", "Total stores queued for creation")
stores_deleted_total = Counter("stores_deleted_total", "Total stores queued for deletion")
api_rate_limited_total = Counter("api_rate_limited_total", "Total API requests rejected by rate limiting")


def _request_identity(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _to_store_response(store: Store) -> StoreResponse:
    return StoreResponse(
        id=str(store.id),
        engine=store.engine,
        display_name=store.display_name,
        namespace=store.namespace,
        release_name=store.release_name,
        status=store.status,
        url=store.url,
        last_error=store.last_error,
        created_at=store.created_at,
        updated_at=store.updated_at,
    )


@router.post("", response_model=EnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
def create_store(payload: CreateStoreRequest, request: Request, db: Session = Depends(get_db)) -> EnqueueResponse:
    allow, remaining = rate_limiter.allow(db, f"create:{_request_identity(request)}")
    if not allow:
        api_rate_limited_total.inc()
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    if payload.engine == StoreEngine.MEDUSA:
        raise HTTPException(
            status_code=422,
            detail="Medusa is intentionally disabled for Round 1. Please choose WooCommerce.",
        )

    if count_active_stores(db) >= settings.max_active_stores:
        raise HTTPException(status_code=409, detail="Maximum active store limit reached.")

    store_id = uuid.uuid4()
    namespace = f"store-{store_id}"
    release_name = namespace

    store = Store(
        id=store_id,
        engine=payload.engine,
        display_name=payload.display_name,
        namespace=namespace,
        release_name=release_name,
        status=StoreStatus.QUEUED,
    )
    db.add(store)
    db.flush()

    job = ProvisioningJob(
        store_id=store.id,
        action=JobAction.PROVISION,
        status=JobStatus.QUEUED,
        max_attempts=settings.worker_max_attempts,
    )
    db.add(job)
    log_event(db, store.id, "queued", f"Provisioning queued. Rate remaining: {remaining}")
    db.commit()
    stores_created_total.inc()

    return EnqueueResponse(
        store_id=str(store.id),
        status=store.status,
        namespace=store.namespace,
        queued_job_id=str(job.id),
    )


@router.get("", response_model=list[StoreResponse])
def list_stores(db: Session = Depends(get_db)) -> list[StoreResponse]:
    stores = db.scalars(select(Store).order_by(Store.created_at.desc())).all()
    return [_to_store_response(s) for s in stores]


@router.get("/{store_id}", response_model=StoreDetailResponse)
def get_store(store_id: str, db: Session = Depends(get_db)) -> StoreDetailResponse:
    try:
        parsed_id = uuid.UUID(store_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid store id") from exc

    store = db.get(Store, parsed_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    events = db.scalars(
        select(StoreEvent).where(StoreEvent.store_id == store.id).order_by(StoreEvent.created_at.desc()).limit(50)
    ).all()

    base = _to_store_response(store)
    return StoreDetailResponse(
        **base.model_dump(),
        events=[StoreEventResponse(id=e.id, event_type=e.event_type, message=e.message, created_at=e.created_at) for e in events],
    )


@router.delete("/{store_id}", response_model=EnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
def delete_store(store_id: str, request: Request, db: Session = Depends(get_db)) -> EnqueueResponse:
    allow, _ = rate_limiter.allow(db, f"delete:{_request_identity(request)}")
    if not allow:
        api_rate_limited_total.inc()
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    try:
        parsed_id = uuid.UUID(store_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid store id") from exc

    store = db.get(Store, parsed_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    if store.status in {StoreStatus.DELETING, StoreStatus.DELETED}:
        existing = db.scalar(
            select(ProvisioningJob)
            .where(ProvisioningJob.store_id == store.id, ProvisioningJob.action == JobAction.DELETE)
            .order_by(ProvisioningJob.created_at.desc())
            .limit(1)
        )
        if existing:
            return EnqueueResponse(
                store_id=str(store.id),
                status=StoreStatus.DELETING,
                namespace=store.namespace,
                queued_job_id=str(existing.id),
            )

    store.status = StoreStatus.DELETING
    db.add(store)

    # Cancel queued provision retries once teardown is requested to avoid stale queue work.
    queued_provisions = db.scalars(
        select(ProvisioningJob).where(
            ProvisioningJob.store_id == store.id,
            ProvisioningJob.action == JobAction.PROVISION,
            ProvisioningJob.status == JobStatus.QUEUED,
        )
    ).all()
    for queued in queued_provisions:
        queued.status = JobStatus.FAILED
        queued.error_message = "provision_cancelled_delete_requested"
        queued.completed_at = queued.completed_at or datetime.now(timezone.utc)

    job = ProvisioningJob(
        store_id=store.id,
        action=JobAction.DELETE,
        status=JobStatus.QUEUED,
        max_attempts=settings.worker_max_attempts,
    )
    db.add(job)
    log_event(db, store.id, "delete_queued", "Teardown queued")
    db.commit()
    stores_deleted_total.inc()

    return EnqueueResponse(
        store_id=str(store.id),
        status=StoreStatus.DELETING,
        namespace=store.namespace,
        queued_job_id=str(job.id),
    )
