import pytest

from scripts.publish_reliability_evidence import _payload


def test_backup_receipt_requires_verified_off_region_storage() -> None:
    receipt = {
        "kind": "coderoute_offsite_backup_receipt_v2",
        "uploaded_at": "2026-08-09T10:00:00+00:00",
        "bundle_sha256": "a" * 64,
        "target_region": "paris",
        "object_key": "coderoute/production/backup.crgbak",
        "off_region_verified": False,
    }
    with pytest.raises(SystemExit, match="hors région"):
        _payload(receipt)


def test_restore_receipt_must_be_successful() -> None:
    receipt = {
        "kind": "coderoute_restore_drill_receipt_v1",
        "verified_at": "2026-08-09T10:00:00+00:00",
        "dump_sha256": "b" * 64,
        "ok": False,
    }
    with pytest.raises(SystemExit, match="non réussi"):
        _payload(receipt)


def test_failover_receipt_must_have_passed_thresholds() -> None:
    failed = {
        "kind": "coderoute_ha_failover_probe_receipt_v1",
        "finished_at": "2026-08-09T10:00:00+00:00",
        "availability_percent": 98.0,
        "duration_seconds": 120,
        "passed": False,
    }
    with pytest.raises(SystemExit, match="seuils"):
        _payload(failed)


def test_pitr_receipt_requires_success_and_archived_report_metadata() -> None:
    with pytest.raises(SystemExit, match="non réussi"):
        _payload({
            "kind": "coderoute_pitr_drill_receipt_v1",
            "passed": False,
        })

    with pytest.raises(SystemExit, match="incomplet"):
        _payload({
            "kind": "coderoute_pitr_drill_receipt_v1",
            "passed": True,
            "finished_at": "2026-08-09T10:30:00+00:00",
        })


def test_successful_receipts_map_to_machine_evidence() -> None:
    backup = _payload({
        "kind": "coderoute_offsite_backup_receipt_v2",
        "uploaded_at": "2026-08-09T10:00:00+00:00",
        "bundle_sha256": "c" * 64,
        "target_region": "paris",
        "object_key": "coderoute/production/backup.crgbak",
        "off_region_verified": True,
    })
    restore = _payload({
        "kind": "coderoute_restore_drill_receipt_v1",
        "verified_at": "2026-08-09T10:10:00+00:00",
        "dump_sha256": "d" * 64,
        "ok": True,
    })
    failover = _payload({
        "kind": "coderoute_ha_failover_probe_receipt_v1",
        "finished_at": "2026-08-09T10:20:00+00:00",
        "availability_percent": 100.0,
        "duration_seconds": 120,
        "passed": True,
    })
    pitr = _payload({
        "kind": "coderoute_pitr_drill_receipt_v1",
        "finished_at": "2026-08-09T10:30:00+00:00",
        "evidence_sha256": "e" * 64,
        "reference": "PITR-DRILL-2026-08-09",
        "observed_rpo_minutes": 3.2,
        "observed_rto_minutes": 17.0,
        "passed": True,
    })
    assert backup["kind"] == "backup_uploaded"
    assert restore["kind"] == "restore_drill_passed"
    assert failover["kind"] == "ha_failover_probe_passed"
    assert pitr == {
        "kind": "pitr_drill_passed",
        "occurred_at": "2026-08-09T10:30:00+00:00",
        "artifact_sha256": "e" * 64,
        "reference": "PITR-DRILL-2026-08-09",
        "observed_rpo_minutes": 3.2,
        "observed_rto_minutes": 17.0,
    }
