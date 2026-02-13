import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.stores import router as stores_router
from app.core.config import get_settings
from app.schemas.health import HealthResponse
from app.workers.provisioner import ProvisioningWorker

settings = get_settings()
app = FastAPI(title="Store Provisioning Control Plane", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stores_router)

worker: ProvisioningWorker | None = None
worker_task: asyncio.Task | None = None


@app.on_event("startup")
async def startup_event() -> None:
    global worker, worker_task
    worker = ProvisioningWorker(settings)
    worker_task = asyncio.create_task(worker.start())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    if worker:
        worker.stop()
    if worker_task:
        worker_task.cancel()


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
