from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.exam_center_gate import (
    assert_center_actor_scope,
    assert_checkin_window,
    assert_exam_start_window,
    assert_station_allowed,
)


class _ScalarSequenceDb:
    def __init__(self, *values):
        self.values = list(values)
        self.statements = []

    def scalar(self, statement):
        self.statements.append(statement)
        return self.values.pop(0) if self.values else None


def _session(starts_at: datetime, center_id: str = "center-1"):
    return SimpleNamespace(id="session-1", starts_at=starts_at, center_id=center_id)


def test_checkin_window_accepts_candidate_one_hour_before_session():
    starts = datetime(2026, 8, 8, 10, 0)
    window = assert_checkin_window(_session(starts), now=starts - timedelta(minutes=45))
    assert window.allowed is True


def test_checkin_window_rejects_candidate_too_early():
    starts = datetime(2026, 8, 8, 10, 0)
    with pytest.raises(HTTPException) as exc_info:
        assert_checkin_window(_session(starts), now=starts - timedelta(minutes=61))
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "CHECKIN_OUTSIDE_SESSION_WINDOW"


def test_exam_start_window_accepts_ten_minutes_before_session():
    starts = datetime(2026, 8, 8, 10, 0)
    window = assert_exam_start_window(_session(starts), now=starts - timedelta(minutes=9))
    assert window.allowed is True


def test_exam_start_window_rejects_after_operational_close():
    starts = datetime(2026, 8, 8, 10, 0)
    with pytest.raises(HTTPException) as exc_info:
        assert_exam_start_window(_session(starts), now=starts + timedelta(minutes=46))
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "EXAM_START_OUTSIDE_SESSION_WINDOW"


def test_center_actor_is_scoped_to_assigned_center():
    user = SimpleNamespace(role="center", center_id="center-a")
    with pytest.raises(HTTPException) as exc_info:
        assert_center_actor_scope(user, _session(datetime.now(UTC).replace(tzinfo=None), "center-b"))
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "CENTER_SCOPE_MISMATCH"


def test_station_gate_is_soft_until_center_has_a_registry():
    db = _ScalarSequenceDb(None)
    result = assert_station_allowed(db, _session(datetime.now(UTC).replace(tzinfo=None)), None)
    assert result["enforced"] is False
    assert result["reason"] == "station_registry_not_configured"


def test_station_gate_requires_device_key_after_registry_activation():
    db = _ScalarSequenceDb("station-any")
    with pytest.raises(HTTPException) as exc_info:
        assert_station_allowed(db, _session(datetime.now(UTC).replace(tzinfo=None)), None)
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "EXAM_STATION_REQUIRED"


def test_station_gate_rejects_unregistered_device():
    db = _ScalarSequenceDb("station-any", None)
    with pytest.raises(HTTPException) as exc_info:
        assert_station_allowed(db, _session(datetime.now(UTC).replace(tzinfo=None)), "CRG-STATION-UNKNOWN")
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "UNREGISTERED_EXAM_STATION"


def test_station_gate_accepts_registered_active_device():
    station = SimpleNamespace(id="station-1", status="active")
    db = _ScalarSequenceDb("station-any", station)
    result = assert_station_allowed(
        db,
        _session(datetime.now(UTC).replace(tzinfo=None)),
        "CRG-STATION-001",
    )
    assert result == {
        "enforced": True,
        "registered": True,
        "station_id": "station-1",
        "reason": None,
    }
