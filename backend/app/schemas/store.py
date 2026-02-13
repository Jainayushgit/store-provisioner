from datetime import datetime
from pydantic import BaseModel, Field

from app.models.enums import StoreEngine, StoreStatus


class CreateStoreRequest(BaseModel):
    engine: StoreEngine = Field(default=StoreEngine.WOOCOMMERCE)
    display_name: str | None = Field(default=None, max_length=120)


class StoreResponse(BaseModel):
    id: str
    engine: StoreEngine
    display_name: str | None
    namespace: str
    release_name: str
    status: StoreStatus
    url: str | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class StoreEventResponse(BaseModel):
    id: int
    event_type: str
    message: str
    created_at: datetime


class StoreDetailResponse(StoreResponse):
    events: list[StoreEventResponse]


class EnqueueResponse(BaseModel):
    store_id: str
    status: StoreStatus
    namespace: str
    queued_job_id: str
