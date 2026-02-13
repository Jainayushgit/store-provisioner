from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.rate_limit_bucket import RateLimitBucket


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def allow(self, db: Session, key: str) -> tuple[bool, int]:
        now = datetime.now(timezone.utc)
        bucket = db.get(RateLimitBucket, key)
        if bucket is None:
            db.add(RateLimitBucket(key=key, count=1, window_started_at=now))
            db.commit()
            return True, self.max_requests - 1

        elapsed = now - bucket.window_started_at
        if elapsed > timedelta(seconds=self.window_seconds):
            bucket.count = 1
            bucket.window_started_at = now
            db.commit()
            return True, self.max_requests - 1

        if bucket.count >= self.max_requests:
            return False, 0

        bucket.count += 1
        db.commit()
        return True, self.max_requests - bucket.count
