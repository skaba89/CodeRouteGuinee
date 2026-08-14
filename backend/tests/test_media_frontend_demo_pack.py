from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "frontend" / "public" / "media" / "exam" / "guinea"
PLAYER = ROOT / "frontend" / "src" / "components" / "ExamMediaPremium.tsx"
VITE_CONFIG = ROOT / "frontend" / "vite.config.ts"


def test_guinea_demo_media_pack_is_small_valid_and_explicitly_not_official():
    manifest_path = PACK / "manifest.json"
    assert manifest_path.exists(), "Guinea demo media manifest is missing"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    governance = manifest["governance"]
    assert governance["source_type"] == "generated"
    assert governance["quality_status"] == "DEMO_NOT_OFFICIAL"
    assert governance["regulatory_status"] == "NOT_REVIEWED"
    assert governance["official_exam_allowed"] is False

    assets = manifest["assets"]
    assert {item["question_keys"][0] for item in assets} >= {"stop", "give_way", "no_entry", "roundabout"}

    for item in assets:
        path = PACK / item["file"]
        assert path.exists(), f"Missing demo media asset: {item['file']}"
        assert path.stat().st_size > 0
        if item["kind"] == "image":
            raw = path.read_bytes()[:16]
            assert raw[:4] == b"RIFF" and raw[8:12] == b"WEBP", f"{path.name} is not WebP"
            assert path.stat().st_size < 500_000, f"{path.name} is too large for mobile demo delivery"
        elif item["kind"] == "video":
            raw = path.read_bytes()[:32]
            assert b"ftyp" in raw, f"{path.name} is not an ISO BMFF/MP4 asset"
            assert 6 <= int(item["duration_seconds"]) <= 20
            assert item.get("poster")
            assert item.get("fallback")
            assert path.stat().st_size < 2_000_000, f"{path.name} is too large for the first mobile demo pack"


def test_guinea_demo_media_injection_is_fail_closed_for_official_attempts():
    source = PLAYER.read_text(encoding="utf-8")
    assert "coderoute:official-exam:active-attempt" in source
    assert "window.sessionStorage.getItem(OFFICIAL_ATTEMPT_KEY)" in source
    assert "Fail closed" in source
    assert "return true;" in source
    assert "if (!media || isOfficialAttemptActive()) return null;" in source
    assert "stop-conakry.webp" in source
    assert "yield-roundabout-conakry.webp" in source
    assert "no-entry-conakry.webp" in source
    assert "roundabout-approach-demo.mp4" in source
    assert "fallbackUrl={demo.fallback}" in source


def test_guinea_demo_images_can_recover_from_stale_mobile_pwa_cache():
    player_source = PLAYER.read_text(encoding="utf-8")
    vite_source = VITE_CONFIG.read_text(encoding="utf-8")

    assert "GUINEA_MEDIA_VERSION = '20260814-1'" in player_source
    assert "withRetryCacheBypass" in player_source
    assert "retry=${retryKey}" in player_source
    assert "src={imageUrl}" in player_source

    assert "handler: 'NetworkFirst'" in vite_source
    assert "cacheName: 'guinea-exam-images-v3'" in vite_source
    assert "networkTimeoutSeconds: 5" in vite_source
    assert "cacheableResponse: { statuses: [200] }" in vite_source
