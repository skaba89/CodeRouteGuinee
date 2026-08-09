from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from coderoute_edge.maintenance import (
    assert_safe_maintenance,
    local_exam_state,
    maintenance_window_open,
    parse_maintenance_windows,
)


def _db(path: Path, statuses: list[str]) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE leases(attempt_id TEXT PRIMARY KEY,status TEXT NOT NULL)")
        for index, status in enumerate(statuses):
            conn.execute("INSERT INTO leases(attempt_id,status) VALUES(?,?)", (f"attempt-{index}", status))
        conn.commit()


def test_maintenance_windows_support_weekday_daily_and_midnight_crossing() -> None:
    windows = parse_maintenance_windows("sun@01:00-04:00;daily@23:00-00:30")
    assert len(windows) == 2
    zone = ZoneInfo("Africa/Conakry")
    sunday = datetime(2026, 8, 9, 2, 0, tzinfo=zone)
    sunday_late = datetime(2026, 8, 9, 23, 30, tzinfo=zone)
    monday_after_midnight = datetime(2026, 8, 10, 0, 15, tzinfo=zone)
    monday_day = datetime(2026, 8, 10, 10, 0, tzinfo=zone)
    assert maintenance_window_open("sun@01:00-04:00", "Africa/Conakry", now=sunday) is True
    assert maintenance_window_open("daily@23:00-00:30", "Africa/Conakry", now=sunday_late) is True
    assert maintenance_window_open("daily@23:00-00:30", "Africa/Conakry", now=monday_after_midnight) is True
    assert maintenance_window_open("daily@23:00-00:30", "Africa/Conakry", now=monday_day) is False


def test_local_exam_state_only_allows_synced_leases(tmp_path: Path) -> None:
    database = tmp_path / "edge.db"
    _db(database, ["synced", "synced"])
    state = local_exam_state(database)
    assert state.active == 0
    assert state.finalized_unsynced == 0
    assert state.synced == 2
    assert state.quiescent is True


def test_active_or_finalized_unsynced_exam_blocks_update_even_with_emergency_bypass(tmp_path: Path) -> None:
    database = tmp_path / "edge.db"
    _db(database, ["active", "finalized", "synced"])
    with pytest.raises(RuntimeError, match="1 examen.*1 journal"):
        assert_safe_maintenance(
            database,
            "sun@01:00-04:00",
            "Africa/Conakry",
            now=datetime(2026, 8, 9, 12, 0, tzinfo=ZoneInfo("Africa/Conakry")),
            bypass_window=True,
        )


def test_outside_window_blocks_quiescent_gateway(tmp_path: Path) -> None:
    database = tmp_path / "edge.db"
    _db(database, ["synced"])
    with pytest.raises(RuntimeError, match="hors fenêtre"):
        assert_safe_maintenance(
            database,
            "sun@01:00-04:00",
            "Africa/Conakry",
            now=datetime(2026, 8, 9, 12, 0, tzinfo=ZoneInfo("Africa/Conakry")),
        )
