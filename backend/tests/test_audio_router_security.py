"""
Test — sécurité et fonctionnement du router audio.

Couvre notamment la protection contre la traversée de répertoire : sans
validation de question_id, un attaquant pourrait lire, écrire ou SUPPRIMER
des fichiers hors du dossier audio. C'est exactement ce qu'un audit de
sécurité externe rechercherait.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import init_db
from app.routers.audio import _audio_path, _validate
from tests.conftest import get_admin_headers, get_candidate_headers


# ── Sécurité : traversée de répertoire ──────────────────────────────────────

TRAVERSAL_ATTEMPTS = [
    "../../../etc/passwd",
    "..",
    "q1/../../secret",
    "q1;rm",
    "q1 q2",
    "q1\x00",
    "a/b",
    "a\\b",
]


@pytest.mark.parametrize("evil", TRAVERSAL_ATTEMPTS)
def test_path_traversal_bloquee(evil: str) -> None:
    with pytest.raises(HTTPException):
        _audio_path("ff", evil)


def test_identifiant_legitime_accepte() -> None:
    p = _audio_path("ff", "q001")
    assert p.name == "q001.mp3"
    assert "ff" in str(p)


def test_locale_invalide_refusee() -> None:
    with pytest.raises(HTTPException):
        _validate("xx", "q001")


# ── Fonctionnement des endpoints ────────────────────────────────────────────

def test_check_audio_inexistant() -> None:
    init_db()
    with TestClient(app) as client:
        r = client.get("/api/v1/audio/check/ff/q999inexistant")
        assert r.status_code == 200
        assert r.json()["exists"] is False


def test_check_audio_locale_invalide() -> None:
    init_db()
    with TestClient(app) as client:
        r = client.get("/api/v1/audio/check/xx/q1")
        assert r.status_code == 400


def test_check_audio_question_id_malveillant() -> None:
    init_db()
    with TestClient(app) as client:
        # L'API doit rejeter un id contenant des caractères de chemin
        r = client.get("/api/v1/audio/check/ff/..%2F..%2Fsecret")
        assert r.status_code in (400, 404)


def test_upload_refuse_non_admin() -> None:
    init_db()
    with TestClient(app) as client:
        r = client.post("/api/v1/audio/upload/ff/q1",
                        headers=get_candidate_headers(client),
                        files={"file": ("q1.mp3", b"ID3fakecontent", "audio/mpeg")})
        assert r.status_code == 403


def test_upload_refuse_fichier_non_mp3() -> None:
    init_db()
    with TestClient(app) as client:
        r = client.post("/api/v1/audio/upload/ff/q1",
                        headers=get_admin_headers(client),
                        files={"file": ("q1.txt", b"pas du mp3", "text/plain")})
        assert r.status_code == 400


def test_upload_refuse_signature_invalide() -> None:
    init_db()
    with TestClient(app) as client:
        r = client.post("/api/v1/audio/upload/ff/q1",
                        headers=get_admin_headers(client),
                        files={"file": ("q1.mp3", b"PASUNMP3REEL", "audio/mpeg")})
        assert r.status_code == 400


def test_upload_mp3_valide_puis_suppression() -> None:
    init_db()
    with TestClient(app) as client:
        admin = get_admin_headers(client)
        # Un vrai en-tête MP3 (ID3)
        content = b"ID3" + b"\x00" * 100
        r = client.post("/api/v1/audio/upload/ff/qtest123",
                        headers=admin,
                        files={"file": ("q.mp3", content, "audio/mpeg")})
        assert r.status_code == 201
        assert r.json()["uploaded"] is True

        # Le fichier existe maintenant
        r = client.get("/api/v1/audio/check/ff/qtest123")
        assert r.json()["exists"] is True

        # Suppression (super_admin = get_admin_headers)
        r = client.delete("/api/v1/audio/delete/ff/qtest123", headers=admin)
        assert r.status_code == 200
        assert r.json()["deleted"] is True
