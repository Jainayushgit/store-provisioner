from sqlalchemy.orm import Session

from app.models.store_event import StoreEvent


def log_event(db: Session, store_id, event_type: str, message: str) -> None:
    db.add(StoreEvent(store_id=store_id, event_type=event_type, message=message))
