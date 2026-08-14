#!/usr/bin/env python3
"""Vendor rights-cleared Guinea road photos into the static training pack.

This script is intentionally NOT part of the normal frontend build. It is a
curation tool: exact sources are declared in realistic-sources.json, downloaded
from Wikimedia's upload host, transformed to a deterministic mobile-friendly
1280x720 WebP derivative, and accompanied by attribution metadata.

Generated derivatives remain training-only and must never be interpreted as
DNTT regulatory approval or as official exam media.
"""
from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "frontend/public/media/exam/guinea/realistic-sources.json"
MAX_SOURCE_BYTES = 10 * 1024 * 1024
ALLOWED_DOWNLOAD_HOSTS = {"upload.wikimedia.org"}
USER_AGENT = "CodeRouteGuinee-MediaVendor/1.0 (+https://github.com/skaba89/CodeRouteGuinee)"


def _download(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS:
        raise RuntimeError(f"Refusing untrusted media source: {url}")

    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "image/jpeg" not in content_type and "image/jpg" not in content_type:
            raise RuntimeError(f"Unexpected content type for {url}: {content_type}")
        declared_length = response.headers.get("Content-Length")
        if declared_length and int(declared_length) > MAX_SOURCE_BYTES:
            raise RuntimeError(f"Source too large: {url}")
        payload = response.read(MAX_SOURCE_BYTES + 1)

    if len(payload) > MAX_SOURCE_BYTES:
        raise RuntimeError(f"Source exceeded {MAX_SOURCE_BYTES} bytes: {url}")
    if len(payload) < 1024 or payload[:2] != b"\xff\xd8":
        raise RuntimeError(f"Source is not a valid JPEG payload: {url}")
    return payload


def _render_webp(payload: bytes, width: int, height: int, quality: int) -> bytes:
    with Image.open(BytesIO(payload)) as image:
        image.load()
        image = ImageOps.exif_transpose(image).convert("RGB")
        if image.width < 800 or image.height < 600:
            raise RuntimeError(f"Source resolution too small: {image.width}x{image.height}")
        fitted = ImageOps.fit(
            image,
            (width, height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        output = BytesIO()
        fitted.save(output, format="WEBP", quality=quality, method=6)
        return output.getvalue()


def _write_attribution(output_dir: Path, sources: list[dict]) -> None:
    lines = [
        "# Attribution — realistic Guinea training media",
        "",
        "These derivatives are bundled locally for CodeRoute Guinée training/demo use.",
        "They are **not DNTT-approved official exam media** and must not be presented as such.",
        "",
        "Each derivative was EXIF-normalized, center-cropped to 16:9, resized to 1280×720,",
        "and encoded as WebP. Source authors do not endorse CodeRoute Guinée.",
        "",
    ]
    for source in sources:
        lines.extend(
            [
                f"## {source['output_file']}",
                "",
                f"- Source: {source['title']}",
                f"- Author: {source['author']}",
                f"- Source page: {source['source_page']}",
                f"- License: {source['license']} ({source['license_url']})",
                "- Modifications: EXIF orientation normalization, 16:9 crop, resize and WebP encoding.",
                "- Usage in CodeRoute: training/demo only; official_exam_allowed=false.",
                "",
            ]
        )
    (output_dir / "ATTRIBUTION.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    output_cfg = manifest["output"]
    output_dir = ROOT / output_cfg["directory"]
    output_dir.mkdir(parents=True, exist_ok=True)

    generated: list[dict] = []
    for source in manifest["sources"]:
        if source.get("usage") != "training_only" or source.get("official_exam_allowed") is not False:
            raise RuntimeError(f"Unsafe governance flags for source {source.get('id')}")

        payload = _download(source["download_url"])
        source_sha1 = hashlib.sha1(payload).hexdigest()
        expected_sha1 = source.get("source_sha1")
        if expected_sha1 and source_sha1 != expected_sha1:
            raise RuntimeError(
                f"SHA-1 mismatch for {source['id']}: expected {expected_sha1}, got {source_sha1}"
            )

        webp = _render_webp(
            payload,
            int(output_cfg["width"]),
            int(output_cfg["height"]),
            int(output_cfg["quality"]),
        )
        target = output_dir / source["output_file"]
        target.write_bytes(webp)

        generated.append(
            {
                "id": source["id"],
                "file": source["output_file"],
                "kind": "image",
                "width": int(output_cfg["width"]),
                "height": int(output_cfg["height"]),
                "bytes": len(webp),
                "sha256": hashlib.sha256(webp).hexdigest(),
                "source_sha1": source_sha1,
                "author": source["author"],
                "source_page": source["source_page"],
                "license": source["license"],
                "license_url": source["license_url"],
                "usage": "training_only",
                "official_exam_allowed": False,
            }
        )
        print(f"generated {target.relative_to(ROOT)} ({len(webp)} bytes)")

    runtime_manifest = {
        "schema_version": 1,
        "collection": "guinea-realistic-training-media",
        "governance": {
            "source_type": "rights_cleared_photography",
            "quality_status": "TRAINING_CURATED",
            "regulatory_status": "NOT_REVIEWED",
            "official_exam_allowed": False,
            "note": "Real Guinea road photography for training/demo only; not DNTT homologation.",
        },
        "assets": generated,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(runtime_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_attribution(output_dir, manifest["sources"])


if __name__ == "__main__":
    main()
