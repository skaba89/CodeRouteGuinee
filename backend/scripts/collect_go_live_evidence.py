#!/usr/bin/env python3
"""Collect a privacy-safe CodeRoute go-live evidence snapshot.

The collector is intentionally read-only. It calls existing health, reliability,
security and national-governance endpoints, writes a machine-readable JSON
snapshot plus a Markdown summary, and generates SHA-256 checksums.

It never turns an operational or institutional requirement into a synthetic
"pass". Missing runtime evidence, SOC activation, PITR, WAF/SIEM or DNTT
approval remain explicit blockers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

DEFAULT_TIMEOUT_SECONDS = 15.0

_ENDPOINTS: tuple[tuple[str, str, bool], ...] = (
    ("health_live", "/health/live", False),
    ("health_readiness", "/health/readiness", False),
    ("reliability", "/api/v1/operations/reliability", True),
    ("security", "/api/v1/operations/security/status", True),
    ("governance_contract", "/api/v1/national-governance/technical-contract", True),
    ("governance_readiness", "/api/v1/national-governance/readiness", True),
    ("homologation_dossiers", "/api/v1/national-governance/homologation-dossiers", True),
)

_SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "api_key",
    "apikey",
    "credential",
    "private_key",
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+\-/]+=*\b")
_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")


def utc_now() -> datetime:
    return datetime.now(UTC)


def _safe_base_url(raw: str, *, allow_http: bool) -> str:
    value = (raw or "").strip().rstrip("/")
    if not value:
        raise ValueError("base URL absente")
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"}:
        raise ValueError("base URL doit utiliser https:// (http:// seulement en local avec --allow-http)")
    if parsed.scheme == "http" and not allow_http:
        host = (parsed.hostname or "").lower()
        if host not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("HTTP non chiffré refusé hors localhost ; utiliser HTTPS")
    if parsed.username or parsed.password:
        raise ValueError("base URL ne doit contenir aucun credential")
    if parsed.query or parsed.fragment:
        raise ValueError("base URL ne doit contenir ni query string ni fragment")
    if parsed.path not in {"", "/"}:
        raise ValueError("base URL doit pointer vers la racine du backend")
    if not parsed.hostname:
        raise ValueError("hostname manquant dans la base URL")
    return value


def _safe_origin(raw: str) -> str:
    parsed = urlparse(raw)
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    return urlunparse((parsed.scheme, f"{host}{port}", "", "", "", ""))


def _sanitize(value: Any, *, key: str = "") -> Any:
    lowered = key.lower()
    if any(part in lowered for part in _SENSITIVE_KEY_PARTS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): _sanitize(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(item, key=key) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item, key=key) for item in value]
    if isinstance(value, str):
        cleaned = _BEARER_RE.sub("Bearer [REDACTED]", value)
        cleaned = _EMAIL_RE.sub("[REDACTED_EMAIL]", cleaned)
        if "://" in cleaned:
            try:
                parsed = urlparse(cleaned)
                if parsed.scheme in {"http", "https"} and parsed.hostname:
                    host = parsed.hostname
                    port = f":{parsed.port}" if parsed.port else ""
                    cleaned = urlunparse((parsed.scheme, f"{host}{port}", parsed.path, "", "", ""))
            except ValueError:
                pass
        return cleaned
    return value


def _request_json(
    *,
    base_url: str,
    path: str,
    token: str,
    protected: bool,
    timeout_seconds: float,
) -> dict[str, Any]:
    if protected and not token:
        return {
            "ok": False,
            "skipped": True,
            "status_code": None,
            "error": "admin bearer token unavailable",
            "body": None,
        }

    url = urljoin(base_url + "/", path.lstrip("/"))
    headers = {
        "Accept": "application/json",
        "User-Agent": "CodeRoute-GoLive-Evidence/1.0",
    }
    if protected:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - URL is operator supplied and validated
            status_code = int(getattr(response, "status", response.getcode()))
            raw = response.read(2_000_000)
            content_type = str(response.headers.get("content-type", ""))
        if "json" not in content_type.lower():
            return {
                "ok": False,
                "skipped": False,
                "status_code": status_code,
                "error": "unexpected non-JSON response",
                "body": None,
            }
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {
                "ok": False,
                "skipped": False,
                "status_code": status_code,
                "error": "invalid JSON response",
                "body": None,
            }
        return {
            "ok": 200 <= status_code < 300,
            "skipped": False,
            "status_code": status_code,
            "error": None if 200 <= status_code < 300 else f"HTTP {status_code}",
            "body": _sanitize(decoded),
        }
    except HTTPError as exc:
        return {
            "ok": False,
            "skipped": False,
            "status_code": int(exc.code),
            "error": f"HTTP {int(exc.code)}",
            "body": None,
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "skipped": False,
            "status_code": None,
            "error": exc.__class__.__name__,
            "body": None,
        }


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _freshness_check(
    *,
    label: str,
    value: Any,
    now: datetime,
    max_age: timedelta,
) -> tuple[bool, str]:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return False, f"{label}: aucune preuve horodatée"
    age = now - parsed
    if age < timedelta(0):
        return False, f"{label}: preuve datée dans le futur"
    if age > max_age:
        return False, f"{label}: preuve trop ancienne ({age.total_seconds() / 3600:.1f} h)"
    return True, f"{label}: preuve fraîche ({age.total_seconds() / 3600:.1f} h)"


def _body(observations: dict[str, dict[str, Any]], key: str) -> dict[str, Any]:
    item = observations.get(key) or {}
    body = item.get("body")
    return body if isinstance(body, dict) else {}


def evaluate_snapshot(
    observations: dict[str, dict[str, Any]],
    *,
    now: datetime,
    expected_deployment_id: str | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []

    def add_check(code: str, passed: bool, detail: str) -> None:
        checks.append({"code": code, "passed": bool(passed), "detail": detail})
        if not passed:
            blockers.append(f"{code}: {detail}")

    live_obs = observations.get("health_live") or {}
    live = _body(observations, "health_live")
    add_check(
        "P10_LIVENESS",
        bool(live_obs.get("ok")) and live.get("status") == "ok",
        "liveness HTTP 2xx et status=ok" if live_obs.get("ok") and live.get("status") == "ok" else "liveness indisponible ou invalide",
    )

    readiness_obs = observations.get("health_readiness") or {}
    readiness = _body(observations, "health_readiness")
    add_check(
        "P10_READINESS",
        bool(readiness_obs.get("ok")) and readiness.get("status") == "ready",
        "readiness=ready" if readiness.get("status") == "ready" else f"readiness={readiness.get('status') or 'unknown'}",
    )

    if expected_deployment_id:
        deployment_id = ((live.get("runtime") or {}).get("deployment_id") if isinstance(live.get("runtime"), dict) else None)
        add_check(
            "DEPLOYMENT_ID_MATCH",
            deployment_id == expected_deployment_id,
            f"deployment_id={deployment_id!r}, attendu={expected_deployment_id!r}",
        )

    reliability_obs = observations.get("reliability") or {}
    reliability = _body(observations, "reliability")
    add_check(
        "P10_RELIABILITY_ENDPOINT",
        bool(reliability_obs.get("ok")),
        "statut PRA accessible" if reliability_obs.get("ok") else "statut PRA non collecté",
    )
    last_evidence = reliability.get("last_evidence") if isinstance(reliability.get("last_evidence"), dict) else {}
    if reliability_obs.get("ok"):
        ok, detail = _freshness_check(
            label="backup hors région",
            value=last_evidence.get("backup_uploaded"),
            now=now,
            max_age=timedelta(hours=26),
        )
        add_check("P10_BACKUP_FRESH", ok, detail)
        ok, detail = _freshness_check(
            label="restore drill",
            value=last_evidence.get("restore_drill_passed"),
            now=now,
            max_age=timedelta(days=35),
        )
        add_check("P10_RESTORE_DRILL_FRESH", ok, detail)
        ok, detail = _freshness_check(
            label="failover API",
            value=last_evidence.get("ha_failover_probe_passed"),
            now=now,
            max_age=timedelta(days=35),
        )
        add_check("P10_FAILOVER_FRESH", ok, detail)

    security_obs = observations.get("security") or {}
    security = _body(observations, "security")
    soc_policy = security.get("soc_policy") if isinstance(security.get("soc_policy"), dict) else {}
    audit_chain = security.get("audit_chain") if isinstance(security.get("audit_chain"), dict) else {}
    add_check(
        "P11_SECURITY_ENDPOINT",
        bool(security_obs.get("ok")),
        "statut SOC accessible" if security_obs.get("ok") else "statut SOC non collecté",
    )
    if security_obs.get("ok"):
        soc_enabled = bool(soc_policy.get("enabled"))
        audit_enabled = bool(soc_policy.get("audit_chain_enabled"))
        audit_valid = bool(audit_chain.get("valid"))
        add_check("P11_SOC_ENABLED", soc_enabled, "SOC actif" if soc_enabled else "SOC encore dormant")
        add_check("P11_AUDIT_HMAC_ENABLED", audit_enabled, "chaîne HMAC active" if audit_enabled else "chaîne HMAC non activée")
        add_check("P11_AUDIT_CHAIN_VALID", soc_enabled and audit_enabled and audit_valid, "chaîne audit valide" if audit_valid else "chaîne audit non validée en mode actif")
        add_check(
            "P11_NO_CRITICAL_SIGNAL",
            security.get("status") == "ok",
            f"security.status={security.get('status') or 'unknown'}",
        )

    governance_obs = observations.get("governance_readiness") or {}
    governance = _body(observations, "governance_readiness")
    add_check(
        "P12_READINESS_ENDPOINT",
        bool(governance_obs.get("ok")),
        "readiness nationale accessible" if governance_obs.get("ok") else "readiness nationale non collectée",
    )
    if governance_obs.get("ok"):
        go_live_allowed = governance.get("go_live_allowed") is True
        detail = "contrôles automatisés P12 satisfaits" if go_live_allowed else "go_live_allowed=false"
        automated_blockers = governance.get("blockers")
        if not go_live_allowed and isinstance(automated_blockers, list) and automated_blockers:
            safe_values = [str(item)[:180] for item in automated_blockers[:12]]
            detail += "; blockers=" + " | ".join(safe_values)
        add_check("P12_AUTOMATED_READINESS", go_live_allowed, detail)

    contract_obs = observations.get("governance_contract") or {}
    contract = _body(observations, "governance_contract")
    alignment = contract.get("alignment") if isinstance(contract.get("alignment"), dict) else {}
    add_check(
        "P12_POLICY_RUNTIME_ALIGNMENT",
        bool(contract_obs.get("ok")) and alignment.get("aligned") is True,
        "politique active alignée au runtime" if alignment.get("aligned") is True else "politique active absente ou non alignée",
    )

    dossiers_obs = observations.get("homologation_dossiers") or {}
    add_check(
        "P12_DOSSIERS_ENDPOINT",
        bool(dossiers_obs.get("ok")),
        "dossiers d'homologation accessibles" if dossiers_obs.get("ok") else "dossiers non collectés",
    )

    manual_evidence_required = [
        "P10.2: preuve fournisseur PITR, fenêtre de rétention et RPO/RTO réellement mesurés",
        "P10.2: preuve externe du bucket/objet backup hors région et restore drill archivé",
        "P11: preuve SIEM/OTLP, WAF/DDoS, astreinte, tests staging et sign-off sécurité",
        "P12: règles officielles DNTT, référence juridique, droits contenus/médias et cinq pièces institutionnelles",
        "P12: approbateurs nommés et décision finale de l'autorité habilitée",
    ]

    protected_skipped = [
        name
        for name, _path, protected in _ENDPOINTS
        if protected and bool((observations.get(name) or {}).get("skipped"))
    ]
    if protected_skipped:
        blockers.append("AUTHENTICATED_EVIDENCE_MISSING: fournir CODEROUTE_ADMIN_BEARER_TOKEN pour collecter " + ", ".join(protected_skipped))

    return {
        "automated_checks_passed": not blockers,
        "status": "automated_checks_passed" if not blockers else "blocked",
        "checks": checks,
        "blockers": blockers,
        "manual_evidence_required": manual_evidence_required,
        "institutional_homologation_claimed": False,
    }


def collect_snapshot(
    *,
    base_url: str,
    token: str,
    timeout_seconds: float,
    expected_deployment_id: str | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    generated_at = now or utc_now()
    observations: dict[str, dict[str, Any]] = {}
    for name, path, protected in _ENDPOINTS:
        observations[name] = _request_json(
            base_url=base_url,
            path=path,
            token=token,
            protected=protected,
            timeout_seconds=timeout_seconds,
        )

    snapshot = {
        "schema": "coderoute_go_live_evidence_pack_v1",
        "generated_at": generated_at.isoformat(),
        "target_origin": _safe_origin(base_url),
        "authenticated_endpoints_requested": bool(token),
        "observations": observations,
    }
    snapshot["assessment"] = evaluate_snapshot(
        observations,
        now=generated_at,
        expected_deployment_id=expected_deployment_id,
    )
    return _sanitize(snapshot)


def render_markdown(snapshot: dict[str, Any]) -> str:
    assessment = snapshot.get("assessment") if isinstance(snapshot.get("assessment"), dict) else {}
    checks = assessment.get("checks") if isinstance(assessment.get("checks"), list) else []
    blockers = assessment.get("blockers") if isinstance(assessment.get("blockers"), list) else []
    manual = assessment.get("manual_evidence_required") if isinstance(assessment.get("manual_evidence_required"), list) else []

    lines = [
        "# CodeRoute Guinée — Go-Live Evidence Pack",
        "",
        f"- Schéma: `{snapshot.get('schema')}`",
        f"- Généré: `{snapshot.get('generated_at')}`",
        f"- Cible: `{snapshot.get('target_origin')}`",
        f"- Statut des contrôles automatisables: **{assessment.get('status', 'unknown')}**",
        "- Homologation institutionnelle déclarée par cet outil: **NON**",
        "",
        "## Contrôles automatisés",
        "",
        "| Contrôle | Résultat | Détail |",
        "| --- | --- | --- |",
    ]
    for item in checks:
        if not isinstance(item, dict):
            continue
        result = "PASS" if item.get("passed") else "BLOCKED"
        detail = str(item.get("detail") or "").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{item.get('code')}` | **{result}** | {detail} |")

    lines.extend(["", "## Blockers automatiques", ""])
    if blockers:
        lines.extend(f"- {str(item)}" for item in blockers)
    else:
        lines.append("- Aucun blocker automatisable détecté dans cet instantané.")

    lines.extend(["", "## Preuves humaines / externes toujours requises", ""])
    lines.extend(f"- {str(item)}" for item in manual)
    lines.extend(
        [
            "",
            "## Interprétation",
            "",
            "Un pack vert signifie uniquement que les contrôles **automatisables** observés au moment de la collecte sont satisfaits. Il ne remplace ni une preuve fournisseur PITR/WAF/SIEM, ni un pentest, ni la validation juridique/DNTT, ni les signatures institutionnelles.",
            "",
        ]
    )
    return "\n".join(lines)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_pack(snapshot: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "evidence.json"
    markdown_path = output_dir / "evidence.md"
    checksums_path = output_dir / "SHA256SUMS"

    json_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(snapshot), encoding="utf-8")

    json_sha = _sha256(json_path)
    markdown_sha = _sha256(markdown_path)
    checksums_path.write_text(
        f"{json_sha}  {json_path.name}\n{markdown_sha}  {markdown_path.name}\n",
        encoding="utf-8",
    )
    return {
        "json": str(json_path),
        "markdown": str(markdown_path),
        "checksums": str(checksums_path),
        "json_sha256": json_sha,
        "markdown_sha256": markdown_sha,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect CodeRoute go-live evidence without mutating production")
    parser.add_argument(
        "--base-url",
        default=os.getenv("CODEROUTE_API_BASE_URL", ""),
        help="Backend root URL. Defaults to CODEROUTE_API_BASE_URL.",
    )
    parser.add_argument(
        "--output-dir",
        default="go-live-evidence/latest",
        help="Directory receiving evidence.json, evidence.md and SHA256SUMS.",
    )
    parser.add_argument(
        "--expected-deployment-id",
        default=os.getenv("CODEROUTE_EXPECTED_DEPLOYMENT_ID", ""),
        help="Optional expected runtime deployment_id.",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--allow-http",
        action="store_true",
        help="Allow plain HTTP for non-local test environments. Never use for production evidence.",
    )
    parser.add_argument(
        "--fail-on-blocker",
        action="store_true",
        help="Exit 2 when one or more automated checks are blocked.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.timeout <= 0 or args.timeout > 120:
        print("ERROR: --timeout doit être > 0 et <= 120 secondes", file=sys.stderr)
        return 2
    try:
        base_url = _safe_base_url(args.base_url, allow_http=bool(args.allow_http))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    # Token read from environment only: avoid exposing it in shell history/process arguments.
    token = os.getenv("CODEROUTE_ADMIN_BEARER_TOKEN", "").strip()
    snapshot = collect_snapshot(
        base_url=base_url,
        token=token,
        timeout_seconds=float(args.timeout),
        expected_deployment_id=(args.expected_deployment_id or "").strip() or None,
    )
    outputs = write_pack(snapshot, Path(args.output_dir))

    assessment = snapshot.get("assessment") if isinstance(snapshot.get("assessment"), dict) else {}
    print(json.dumps({"status": assessment.get("status"), "outputs": outputs}, ensure_ascii=False, indent=2))
    if args.fail_on_blocker and assessment.get("status") != "automated_checks_passed":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
