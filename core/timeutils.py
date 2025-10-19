"""Time utility helpers with five-second precision."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Iterator

FIVE_SECONDS = timedelta(seconds=5)


def to_utc(ts: datetime) -> datetime:
    """Ensure a datetime is timezone-aware UTC."""
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def floor_to_bucket(ts: datetime, bucket: timedelta = FIVE_SECONDS) -> datetime:
    """Floor the timestamp to the start of a bucket."""
    ts_utc = to_utc(ts)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = ts_utc - epoch
    total_seconds = int(delta.total_seconds())
    bucket_seconds = int(bucket.total_seconds())
    floored = (total_seconds // bucket_seconds) * bucket_seconds
    return epoch + timedelta(seconds=floored)


def iterate_buckets(start: datetime, end: datetime, bucket: timedelta = FIVE_SECONDS) -> Iterator[datetime]:
    """Yield bucket-aligned timestamps inclusive of start and exclusive of end."""
    current = floor_to_bucket(start, bucket)
    end_utc = to_utc(end)
    while current < end_utc:
        yield current
        current += bucket


def fill_missing_buckets(existing: Iterable[datetime], start: datetime, end: datetime) -> list[datetime]:
    """Return all expected buckets between start/end, marking missing windows."""
    target = list(iterate_buckets(start, end))
    existing_set = {floor_to_bucket(ts) for ts in existing}
    return [ts for ts in target if ts not in existing_set]
