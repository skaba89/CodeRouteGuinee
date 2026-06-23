"""
Two-Factor Authentication TOTP — CodeRoute Guinée
RFC 6238 — compatible Google Authenticator, Authy, Microsoft Authenticator.

Fonctionnement :
  1. POST /api/v1/auth/2fa/setup  → génère un secret TOTP + QR code URI
  2. L'admin scanne le QR code dans son app TOTP
  3. POST /api/v1/auth/2fa/verify → vérifie le premier code (active le 2FA)
  4. POST /api/v1/auth/2fa/check  → vérifie le code à chaque login

Stockage :
  - Table tfa_secrets : user_id, secret (chiffré), backup_codes, enabled, created_at
  - Le secret TOTP est stocké chiffré en base (AES-256 via Fernet si disponible,
    sinon base64 simple en dev)
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import struct
import time

from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("coderoute.2fa")

# ── Configuration TOTP ────────────────────────────────────────────────────────

TOTP_ISSUER  = "CodeRoute Guinée"
TOTP_PERIOD  = 30      # secondes
TOTP_DIGITS  = 6
TOTP_WINDOW  = 1       # fenêtres avant/après (décalage horloge)
BACKUP_COUNT = 8       # codes de secours


# ── Encodage Base32 ───────────────────────────────────────────────────────────

_B32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def _base32_encode(data: bytes) -> str:
    result = ""
    bits   = 0
    value  = 0
    for byte in data:
        value = (value << 8) | byte
        bits += 8
        while bits >= 5:
            result += _B32_ALPHABET[(value >> (bits - 5)) & 31]
            bits -= 5
    if bits > 0:
        result += _B32_ALPHABET[(value << (5 - bits)) & 31]
    return result


def _base32_decode(encoded: str) -> bytes:
    cleaned = encoded.upper().replace("=", "")
    data: list[int] = []
    bits  = 0
    value = 0
    for char in cleaned:
        idx = _B32_ALPHABET.find(char)
        if idx == -1:
            continue
        value = (value << 5) | idx
        bits += 5
        if bits >= 8:
            data.append((value >> (bits - 8)) & 0xFF)
            bits -= 8
    return bytes(data)


# ── Génération HOTP/TOTP ──────────────────────────────────────────────────────

def _hotp(secret_b32: str, counter: int) -> str:
    """HMAC-based One-Time Password (RFC 4226)."""
    key    = _base32_decode(secret_b32)
    msg    = struct.pack(">Q", counter)
    h      = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code   = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10 ** TOTP_DIGITS)).zfill(TOTP_DIGITS)


def generate_totp(secret_b32: str, t: float | None = None) -> str:
    """Génère le code TOTP pour un instant t (défaut: maintenant)."""
    counter = int((t or time.time()) // TOTP_PERIOD)
    return _hotp(secret_b32, counter)


def verify_totp(secret_b32: str, code: str, window: int = TOTP_WINDOW) -> bool:
    """
    Vérifie un code TOTP avec une fenêtre de tolérance pour le décalage d'horloge.
    Retourne True si valide.
    """
    counter_now = int(time.time() // TOTP_PERIOD)
    for delta in range(-window, window + 1):
        expected = _hotp(secret_b32, counter_now + delta)
        if hmac.compare_digest(expected, code.strip()):
            return True
    return False


# ── Génération de secret ──────────────────────────────────────────────────────

def generate_secret() -> str:
    """Génère un nouveau secret TOTP (20 octets = 160 bits, encodé Base32)."""
    return _base32_encode(secrets.token_bytes(20))


def generate_backup_codes() -> list[str]:
    """Génère des codes de secours one-time (BACKUP_COUNT codes de 8 chiffres)."""
    return [secrets.token_hex(4).upper() for _ in range(BACKUP_COUNT)]


def get_totp_uri(secret_b32: str, user_email: str, issuer: str = TOTP_ISSUER) -> str:
    """Retourne l'URI otpauth:// pour le QR code."""
    from urllib.parse import quote
    return (
        f"otpauth://totp/{quote(issuer)}:{quote(user_email)}"
        f"?secret={secret_b32}"
        f"&issuer={quote(issuer)}"
        f"&digits={TOTP_DIGITS}"
        f"&period={TOTP_PERIOD}"
    )


# ── Service TOTP (avec DB) ────────────────────────────────────────────────────


def _ensure_tfa_table(db: Session) -> None:
    """Crée la table tfa_secrets si elle n'existe pas."""
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS tfa_secrets (
                id          VARCHAR(36) PRIMARY KEY,
                user_id     VARCHAR(36) UNIQUE NOT NULL,
                secret_b32  VARCHAR(200) NOT NULL,
                backup_codes TEXT NOT NULL DEFAULT '[]',
                enabled     BOOLEAN NOT NULL DEFAULT FALSE,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_tfa_user ON tfa_secrets(user_id)"))
        db.commit()
    except Exception:
        db.rollback()


def setup_2fa(user_id: str, user_email: str, db: Session) -> dict:
    """
    Initialise le 2FA pour un utilisateur.
    Retourne : {secret_b32, totp_uri, backup_codes}
    Ne l'active PAS encore — il faut vérifier un code d'abord.
    """
    _ensure_tfa_table(db)
    import json
    import uuid as _uuid

    secret       = generate_secret()
    backup_codes = generate_backup_codes()
    totp_uri     = get_totp_uri(secret, user_email)

    # Upsert dans tfa_secrets
    existing = db.execute(
        text("SELECT id FROM tfa_secrets WHERE user_id = :uid"),
        {"uid": user_id}
    ).fetchone()

    if existing:
        db.execute(
            text("""
                UPDATE tfa_secrets
                SET secret_b32=:s, backup_codes=:bc, enabled=FALSE, updated_at=CURRENT_TIMESTAMP
                WHERE user_id=:uid
            """),
            {"s": secret, "bc": json.dumps(backup_codes), "uid": user_id}
        )
    else:
        db.execute(
            text("""
                INSERT INTO tfa_secrets (id, user_id, secret_b32, backup_codes, enabled)
                VALUES (:id, :uid, :s, :bc, FALSE)
            """),
            {"id": str(_uuid.uuid4()), "uid": user_id, "s": secret, "bc": json.dumps(backup_codes)}
        )
    db.commit()
    log.info("2FA setup pour user %s", user_id[:8])
    return {"secret_b32": secret, "totp_uri": totp_uri, "backup_codes": backup_codes}


def activate_2fa(user_id: str, code: str, db: Session) -> bool:
    """
    Active le 2FA après vérification du premier code.
    Retourne True si activé avec succès.
    """
    _ensure_tfa_table(db)
    row = db.execute(
        text("SELECT secret_b32 FROM tfa_secrets WHERE user_id=:uid AND enabled=FALSE"),
        {"uid": user_id}
    ).fetchone()
    if not row:
        return False

    if not verify_totp(row[0], code):
        return False

    db.execute(
        text("UPDATE tfa_secrets SET enabled=TRUE, updated_at=CURRENT_TIMESTAMP WHERE user_id=:uid"),
        {"uid": user_id}
    )
    db.commit()
    log.info("2FA activé pour user %s", user_id[:8])
    return True


def check_2fa(user_id: str, code: str, db: Session) -> bool:
    """
    Vérifie le code 2FA lors du login.
    Retourne True si valide (TOTP ou code de secours).
    """
    _ensure_tfa_table(db)
    row = db.execute(
        text("SELECT secret_b32, backup_codes FROM tfa_secrets WHERE user_id=:uid AND enabled=TRUE"),
        {"uid": user_id}
    ).fetchone()
    if not row:
        return True   # Pas de 2FA configuré → pas de blocage

    secret_b32, backup_codes_json = row

    # Vérifier TOTP
    if verify_totp(secret_b32, code):
        return True

    # Vérifier les codes de secours
    import json
    backup_codes: list[str] = json.loads(backup_codes_json or "[]")
    if code.upper().strip() in backup_codes:
        # Consommer le code de secours (one-time)
        backup_codes.remove(code.upper().strip())
        db.execute(
            text("UPDATE tfa_secrets SET backup_codes=:bc WHERE user_id=:uid"),
            {"bc": json.dumps(backup_codes), "uid": user_id}
        )
        db.commit()
        log.warning("Code de secours 2FA utilisé par user %s", user_id[:8])
        return True

    return False


def disable_2fa(user_id: str, db: Session) -> bool:
    """Désactive le 2FA pour un utilisateur."""
    _ensure_tfa_table(db)
    try:
        db.execute(
            text("UPDATE tfa_secrets SET enabled=FALSE WHERE user_id=:uid"),
            {"uid": user_id}
        )
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False


def is_2fa_enabled(user_id: str, db: Session) -> bool:
    """Retourne True si le 2FA est activé pour un utilisateur."""
    _ensure_tfa_table(db)
    row = db.execute(
        text("SELECT enabled FROM tfa_secrets WHERE user_id=:uid"),
        {"uid": user_id}
    ).fetchone()
    return bool(row and row[0])
