from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

_ALLOWED_PREFIXES = ("image/", "video/", "audio/")


class MediaCache:
    def __init__(self, root: Path, *, central_url: str, public_url: str, max_media_bytes: int):
        self.root = root
        self.central_url = central_url.rstrip("/") + "/"
        self.public_url = public_url.rstrip("/")
        self.max_media_bytes = max_media_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve_url(self, value: str) -> str:
        if value.startswith("/"):
            return urljoin(self.central_url, value.lstrip("/"))
        parsed = urlparse(value)
        if parsed.scheme != "https":
            raise RuntimeError("Un média Edge distant doit utiliser HTTPS")
        return value

    def prefetch_bundle(self, bundle: dict, client: httpx.Client | None = None) -> dict:
        """Précharge les médias sans modifier le lease signé par le central."""
        owned = client is None
        http = client or httpx.Client(timeout=30.0, follow_redirects=True)
        try:
            cloned = json.loads(json.dumps(bundle))
            lease = cloned["lease"]
            attempt_id = str(lease["attempt_id"])
            local_questions = json.loads(json.dumps(lease.get("questions", [])))
            for question in local_questions:
                for field in ("media_url", "audio_url"):
                    value = question.get(field)
                    if not value:
                        continue
                    digest = self._fetch_one(http, str(value))
                    question[field] = f"{self.public_url}/v1/exams/{attempt_id}/media/{digest}"
            # La signature couvre `lease`; cette projection LAN est locale et
            # volontairement située hors du paquet signé.
            cloned["local_questions"] = local_questions
            return cloned
        finally:
            if owned:
                http.close()

    def _fetch_one(self, http: httpx.Client, value: str) -> str:
        url = self._resolve_url(value)
        temp = self.root / f".download-{os.urandom(8).hex()}.tmp"
        hasher = hashlib.sha256()
        total = 0
        content_type = ""
        try:
            with http.stream("GET", url) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if not content_type.startswith(_ALLOWED_PREFIXES):
                    raise RuntimeError(f"Type MIME média interdit pour le cache Edge : {content_type or 'inconnu'}")
                advertised = int(response.headers.get("content-length", "0") or 0)
                if advertised and advertised > self.max_media_bytes:
                    raise RuntimeError("Média trop volumineux pour le cache Edge")
                with temp.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > self.max_media_bytes:
                            raise RuntimeError("Média trop volumineux pour le cache Edge")
                        hasher.update(chunk)
                        handle.write(chunk)
                    handle.flush()
                    os.fsync(handle.fileno())

            digest = hasher.hexdigest()
            path = self.root / digest
            if path.exists():
                temp.unlink(missing_ok=True)
            else:
                temp.replace(path)
            metadata = self.root / f"{digest}.json"
            metadata.write_text(
                json.dumps({"sha256": digest, "content_type": content_type, "size": total}, sort_keys=True),
                encoding="utf-8",
            )
            return digest
        except Exception:
            temp.unlink(missing_ok=True)
            raise

    def resolve(self, digest: str) -> tuple[Path, str]:
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise FileNotFoundError("Digest média invalide")
        path = self.root / digest
        metadata = self.root / f"{digest}.json"
        if not path.is_file() or not metadata.is_file():
            raise FileNotFoundError("Média Edge introuvable")
        info = json.loads(metadata.read_text(encoding="utf-8"))
        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        if hasher.hexdigest() != digest:
            raise RuntimeError("Intégrité du média Edge invalide")
        return path, str(info.get("content_type") or "application/octet-stream")
