from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import get_admin_headers


def test_national_readiness_v2_contract_is_explainable_and_bounded() -> None:
    with TestClient(app) as client:
        headers = get_admin_headers(client)
        response = client.get('/api/v1/dashboard/national-readiness', headers=headers)

    assert response.status_code == 200
    payload = response.json()

    assert payload['version'] == 'national-readiness-v2'
    assert isinstance(payload['score'], int)
    assert 0 <= payload['score'] <= 100
    assert payload['status'] in {
        'national_ready', 'pilot_ready', 'remediation_required', 'not_ready'
    }
    assert isinstance(payload['national_rollout_allowed'], bool)
    assert isinstance(payload['blockers'], list)

    pillars = payload['pillars']
    assert sum(item['weight'] for item in pillars.values()) == 100
    assert sum(item['score'] for item in pillars.values()) == payload['score']
    assert all(0 <= item['score'] <= item['weight'] for item in pillars.values())

    bank = payload['official_bank']
    assert bank['required'] == 40
    assert set(bank['category_coverage']) == {
        'signalisation', 'priorites', 'vitesse', 'depassement',
        'securite_passive', 'urgence', 'alcool_drogues', 'premiers_secours',
    }

    centers = payload['centers']
    assert 0 <= centers['station_coverage_percent'] <= 100
    assert 0 <= centers['session_coverage_percent'] <= 100
    assert isinstance(centers['matrix'], list)
    for center in centers['matrix']:
        assert 0 <= center['readiness_score'] <= 100
        assert isinstance(center['blockers'], list)
        assert isinstance(center['ready'], bool)

    integrity = payload['exam_integrity']
    assert 0 <= integrity['trace_coverage_percent'] <= 100
    assert payload['methodology']['score_max'] == 100
    assert payload['methodology']['national_ready_threshold'] == 90
