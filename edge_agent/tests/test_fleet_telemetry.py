from __future__ import annotations

from coderoute_edge.service import EdgeAgentService


class _CaptureCentral:
    def __init__(self) -> None:
        self.telemetry = None

    def heartbeat(self, telemetry=None):
        self.telemetry = telemetry
        return {"accepted": True}


class _Unused:
    pass


def test_service_heartbeat_publishes_only_operational_fleet_telemetry() -> None:
    central = _CaptureCentral()
    service = EdgeAgentService(_Unused(), central, _Unused())
    service.operator_status = lambda: {
        "lease_counts": {"active": 3, "finalized": 2, "synced": 41},
        "sync_pending": 2,
        "revalidation_required": 1,
        "corrupt_leases": 0,
        "media_cache": {"files": 18, "bytes": 2_500_000},
        # Ces détails locaux existent dans la vue opérateur mais ne doivent
        # jamais être envoyés dans le heartbeat national.
        "leases": [{
            "attempt_id": "attempt-secret",
            "station": {"device_key": "POSTE-SECRET"},
            "event_count": 12,
        }],
    }

    result = service.heartbeat()

    assert result == {"accepted": True}
    assert central.telemetry == {
        "active_leases": 3,
        "finalized_leases": 2,
        "synced_leases": 41,
        "sync_pending": 2,
        "revalidation_required": 1,
        "corrupt_leases": 0,
        "media_files": 18,
        "media_bytes": 2_500_000,
    }
    serialized = str(central.telemetry)
    assert "attempt-secret" not in serialized
    assert "POSTE-SECRET" not in serialized
    assert "event_count" not in serialized
