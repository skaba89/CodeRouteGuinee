import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.csrf import check_csrf


def _request(path: str) -> Request:
    return Request({
        "type": "http",
        "method": "POST",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "scheme": "https",
        "server": ("api.coderoute.test", 443),
        "client": ("127.0.0.1", 12345),
    })


def test_exact_machine_evidence_path_is_csrf_exempt() -> None:
    check_csrf(_request("/api/v1/operations/reliability/evidence"))


def test_neighboring_reliability_path_still_requires_csrf() -> None:
    with pytest.raises(HTTPException) as exc:
        check_csrf(_request("/api/v1/operations/reliability/evidence/admin"))
    assert exc.value.status_code == 403


def test_metrics_is_read_only_and_not_part_of_csrf_exemptions() -> None:
    # Un POST accidentel vers metrics n'est pas exempté.
    with pytest.raises(HTTPException) as exc:
        check_csrf(_request("/internal/metrics"))
    assert exc.value.status_code == 403
