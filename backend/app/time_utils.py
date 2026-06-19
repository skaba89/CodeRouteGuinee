from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return a naive UTC datetime compatible with existing database columns."""
    return datetime.now(UTC).replace(tzinfo=None)
