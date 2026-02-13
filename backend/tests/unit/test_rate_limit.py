from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.rate_limit_bucket import RateLimitBucket
from app.services.rate_limit import RateLimiter


def test_rate_limit_allows_then_blocks_within_window():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    RateLimitBucket.__table__.create(engine)

    limiter = RateLimiter(max_requests=2, window_seconds=60)

    with Session(engine) as db:
        ok_1, remaining_1 = limiter.allow(db, "create:127.0.0.1")
        ok_2, remaining_2 = limiter.allow(db, "create:127.0.0.1")
        ok_3, remaining_3 = limiter.allow(db, "create:127.0.0.1")

    assert ok_1 is True and remaining_1 == 1
    assert ok_2 is True and remaining_2 == 0
    assert ok_3 is False and remaining_3 == 0
