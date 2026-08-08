from __future__ import annotations

import base64
import hmac
import json
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .central import CentralClient
from .config import EdgeAgentConfig
from .crypto import load_or_create_storage_key, load_private_key
from .media import MediaCache
from .service import EdgeAgentService
from .store import EdgeStore
from .tickets import verify_media_ticket


class ActivateRequest(BaseModel):
    attempt_id: str
    station_device_key: str = Field(min_length=4, max_length=160)
    lang: str = Field(default="fr", min_length=2, max_length=10)


class ClaimRequest(BaseModel):
    attempt_id: str
    claim_token: str = Field(min_length=32, max_length=160)
    station_device_key: str = Field(min_length=4, max_length=160)


class AnswerRequest(BaseModel):
    question_id: str
    answer: str = Field(min_length=1, max_length=255)


def _b64url_json(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def build_service(config: EdgeAgentConfig) -> EdgeAgentService:
    storage_key = load_or_create_storage_key(config.storage_key_path)
    store = EdgeStore(config.database_path, storage_key)
    private_key = load_private_key(config.private_key_path)
    central = CentralClient(config, store, private_key)
    media = MediaCache(
        config.media_cache_dir,
        central_url=config.central_url,
        public_url=config.public_url,
        max_media_bytes=config.max_media_bytes,
    )
    return EdgeAgentService(store, central, media)


def create_app(
    config: EdgeAgentConfig | None = None,
    service: EdgeAgentService | None = None,
) -> FastAPI:
    config = config or EdgeAgentConfig.from_env()
    service = service or build_service(config)
    app = FastAPI(
        title="CodeRoute Center Edge Agent",
        version=config.software_version,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "X-Edge-Operator-Token",
            "X-Edge-Access-Token",
            "X-CodeRoute-Station-Key",
        ],
    )

    def require_operator(
        x_edge_operator_token: Annotated[str | None, Header()] = None,
    ) -> None:
        if not x_edge_operator_token or not hmac.compare_digest(x_edge_operator_token, config.operator_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Operator token invalid")

    def candidate_headers(
        x_edge_access_token: Annotated[str | None, Header()] = None,
        x_coderoute_station_key: Annotated[str | None, Header()] = None,
    ) -> tuple[str, str]:
        if not x_edge_access_token or not x_coderoute_station_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Edge candidate credentials required")
        return x_edge_access_token, x_coderoute_station_key

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "node_id": config.node_id,
            "center_id": config.center_id,
            "software_version": config.software_version,
            **service.status(),
        }

    @app.post("/operator/heartbeat", dependencies=[Depends(require_operator)])
    def operator_heartbeat() -> dict:
        try:
            return service.heartbeat()
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Central heartbeat failed: {exc}") from exc

    @app.post("/operator/leases", dependencies=[Depends(require_operator)])
    def operator_activate(payload: ActivateRequest) -> dict:
        try:
            result = service.activate_attempt(payload.attempt_id, payload.station_device_key, payload.lang)
            bootstrap = {
                "edge_url": config.public_url,
                "attempt_id": result["attempt_id"],
                "claim_token": result["claim_token"],
                "claim_expires_at": result["claim_expires_at"],
            }
            encoded = _b64url_json(bootstrap)
            frontend_origin = config.allowed_origins[0].rstrip("/")
            return {
                **result,
                "claim_fragment": f"edge={encoded}",
                "candidate_url": f"{frontend_origin}/#/exam?edge={encoded}",
            }
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Edge activation failed: {exc}") from exc

    @app.post("/v1/claim")
    def candidate_claim(payload: ClaimRequest) -> dict:
        try:
            result = service.claim_candidate_session(
                payload.attempt_id,
                payload.claim_token,
                payload.station_device_key,
            )
            return {
                **result,
                "edge_url": config.public_url,
                "node_id": config.node_id,
                "center_id": config.center_id,
            }
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @app.post("/operator/sync/{attempt_id}", dependencies=[Depends(require_operator)])
    def operator_sync(attempt_id: str) -> dict:
        try:
            return service.sync_attempt(attempt_id)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Edge sync failed: {exc}") from exc

    @app.get("/operator/status", dependencies=[Depends(require_operator)])
    def operator_status() -> dict:
        return {
            "node_id": config.node_id,
            "center_id": config.center_id,
            **service.status(),
        }

    @app.get("/v1/exams/{attempt_id}")
    def candidate_exam(
        attempt_id: str,
        credentials: tuple[str, str] = Depends(candidate_headers),
    ) -> dict:
        try:
            return service.candidate_exam(attempt_id, credentials[0], credentials[1])
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except RuntimeError as exc:
            code = "EDGE_REVALIDATION_REQUIRED" if "EDGE_REVALIDATION_REQUIRED" in str(exc) else "EDGE_RUNTIME_ERROR"
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": code, "message": str(exc)}) from exc

    @app.post("/v1/exams/{attempt_id}/answers")
    def candidate_answer(
        attempt_id: str,
        payload: AnswerRequest,
        credentials: tuple[str, str] = Depends(candidate_headers),
    ) -> dict:
        try:
            return service.answer(attempt_id, credentials[0], credentials[1], payload.question_id, payload.answer)
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @app.post("/v1/exams/{attempt_id}/finalize")
    def candidate_finalize(
        attempt_id: str,
        credentials: tuple[str, str] = Depends(candidate_headers),
    ) -> dict:
        try:
            return service.finalize(attempt_id, credentials[0], credentials[1])
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except (KeyError, RuntimeError) as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @app.get("/v1/exams/{attempt_id}/media/{digest}")
    def local_media(
        attempt_id: str,
        digest: str,
        expires: int = Query(gt=0),
        ticket: str = Query(min_length=64, max_length=64),
    ):
        if not verify_media_ticket(service.store.storage_key, attempt_id, digest, expires, ticket):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Media ticket invalid or expired")
        try:
            path, content_type = service.media.resolve(digest)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return FileResponse(path, media_type=content_type, headers={"Cache-Control": "private, max-age=3600, immutable"})

    return app
