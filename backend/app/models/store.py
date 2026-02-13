from datetime import datetime
from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from app.models.base import Base
from app.models.enums import StoreEngine, StoreStatus


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engine: Mapped[StoreEngine] = mapped_column(
        Enum(StoreEngine, name="store_engine", values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        nullable=False,
    )
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    namespace: Mapped[str] = mapped_column(String(140), unique=True, nullable=False)
    release_name: Mapped[str] = mapped_column(String(140), unique=True, nullable=False)
    status: Mapped[StoreStatus] = mapped_column(Enum(StoreStatus, name="store_status"), nullable=False)
    url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
