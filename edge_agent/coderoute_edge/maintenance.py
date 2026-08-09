from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_WINDOW_RE = re.compile(r"^(mon|tue|wed|thu|fri|sat|sun|daily)@(\d{2}:\d{2})-(\d{2}:\d{2})$")
_WEEKDAY = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


@dataclass(frozen=True)
class MaintenanceWindow:
    weekday: int | None
    start: time
    end: time


@dataclass(frozen=True)
class LocalExamState:
    active: int
    finalized_unsynced: int
    synced: int
    other: int

    @property
    def quiescent(self) -> bool:
        return self.active == 0 and self.finalized_unsynced == 0 and self.other == 0


def _clock(value: str) -> time:
    hour, minute = (int(part) for part in value.split(":", 1))
    if hour > 23 or minute > 59:
        raise ValueError(f"Heure de maintenance invalide : {value}")
    return time(hour=hour, minute=minute)


def parse_maintenance_windows(raw: str) -> tuple[MaintenanceWindow, ...]:
    windows: list[MaintenanceWindow] = []
    for item in (part.strip().lower() for part in raw.split(";") if part.strip()):
        match = _WINDOW_RE.fullmatch(item)
        if not match:
            raise ValueError(f"Fenêtre de maintenance invalide : {item}")
        day, start_raw, end_raw = match.groups()
        start = _clock(start_raw)
        end = _clock(end_raw)
        if start == end:
            raise ValueError("Une fenêtre de maintenance ne peut pas durer 24h")
        windows.append(MaintenanceWindow(None if day == "daily" else _WEEKDAY[day], start, end))
    if not windows:
        raise ValueError("Au moins une fenêtre de maintenance est obligatoire")
    return tuple(windows)


def _inside_clock_window(current: time, start: time, end: time) -> bool:
    if start < end:
        return start <= current < end
    # Fenêtre traversant minuit, ex. 23:00-02:00.
    return current >= start or current < end


def maintenance_window_open(
    raw_windows: str,
    timezone_name: str,
    *,
    now: datetime | None = None,
) -> bool:
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Fuseau de maintenance inconnu : {timezone_name}") from exc
    reference = now or datetime.now(zone)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=zone)
    else:
        reference = reference.astimezone(zone)
    current_time = reference.time().replace(tzinfo=None)
    weekday = reference.weekday()
    previous_weekday = (weekday - 1) % 7

    for window in parse_maintenance_windows(raw_windows):
        crosses_midnight = window.start > window.end
        if window.weekday is None:
            if _inside_clock_window(current_time, window.start, window.end):
                return True
            continue
        if not crosses_midnight:
            if window.weekday == weekday and _inside_clock_window(current_time, window.start, window.end):
                return True
        else:
            if window.weekday == weekday and current_time >= window.start:
                return True
            if window.weekday == previous_weekday and current_time < window.end:
                return True
    return False


def local_exam_state(database_path: Path) -> LocalExamState:
    if not database_path.is_file():
        raise RuntimeError(f"Base Edge introuvable : {database_path}")
    uri = f"file:{database_path.resolve().as_posix()}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True, timeout=5) as conn:
            rows = conn.execute("SELECT status,COUNT(*) FROM leases GROUP BY status").fetchall()
    except sqlite3.Error as exc:
        raise RuntimeError("Impossible de vérifier l'état des examens locaux avant maintenance") from exc
    counts = {str(status): int(count) for status, count in rows}
    known = {"active", "finalized", "synced"}
    return LocalExamState(
        active=counts.get("active", 0),
        finalized_unsynced=counts.get("finalized", 0),
        synced=counts.get("synced", 0),
        other=sum(count for status, count in counts.items() if status not in known),
    )


def assert_safe_maintenance(
    database_path: Path,
    raw_windows: str,
    timezone_name: str,
    *,
    now: datetime | None = None,
    bypass_window: bool = False,
) -> LocalExamState:
    if not bypass_window and not maintenance_window_open(raw_windows, timezone_name, now=now):
        raise RuntimeError("Mise à jour Edge hors fenêtre de maintenance autorisée")
    state = local_exam_state(database_path)
    if not state.quiescent:
        raise RuntimeError(
            "Mise à jour Edge bloquée : "
            f"{state.active} examen(s) actif(s), {state.finalized_unsynced} journal(aux) finalisé(s) non synchronisé(s), "
            f"{state.other} état(s) local(aux) inconnu(s)."
        )
    return state
