"""
Router audio — CodeRoute Guinée

Endpoints :
  GET /api/v1/audio/{locale}/{question_id}  — vérifier si un MP3 existe
  GET /api/v1/audio/inventory               — inventaire des fichiers disponibles
  POST /api/v1/audio/upload                 — uploader un MP3 (admin seulement)

Les fichiers audio sont servis par FastAPI StaticFiles sur /static/audio/{locale}/{question_id}.mp3
Ce router gère uniquement les métadonnées et l'upload admin.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.deps import require_roles
from app.models_user import User

router = APIRouter(prefix="/audio", tags=["audio"])

_STATIC_DIR = Path(__file__).parent.parent.parent / "static" / "audio"
_VALID_LOCALES = {"ff", "man", "sus", "kss", "gkp", "lom", "fr", "en"}
_MAX_MP3_SIZE  = 10 * 1024 * 1024  # 10 Mo


def _audio_path(locale: str, question_id: str) -> Path:
    return _STATIC_DIR / locale / f"{question_id}.mp3"


@router.get("/check/{locale}/{question_id}")
def check_audio_exists(locale: str, question_id: str) -> dict:
    """Vérifie si un fichier audio existe pour une question et une locale."""
    if locale not in _VALID_LOCALES:
        raise HTTPException(status_code=400, detail=f"Locale invalide. Valeurs : {sorted(_VALID_LOCALES)}")

    path = _audio_path(locale, question_id)
    if path.exists():
        size_kb = path.stat().st_size // 1024
        return {"exists": True, "locale": locale, "question_id": question_id,
                "size_kb": size_kb, "url": f"/static/audio/{locale}/{question_id}.mp3"}
    return {"exists": False, "locale": locale, "question_id": question_id}


@router.get("/inventory")
def get_audio_inventory(
    locale: str | None = None,
) -> dict:
    """
    Retourne l'inventaire des fichiers audio disponibles.
    Si locale est fourni, filtre par langue.
    """
    inventory: dict[str, list[str]] = {}
    total = 0

    for loc in _VALID_LOCALES:
        if locale and loc != locale:
            continue
        loc_dir = _STATIC_DIR / loc
        if not loc_dir.exists():
            inventory[loc] = []
            continue
        files = sorted(f.stem for f in loc_dir.glob("*.mp3"))
        inventory[loc] = files
        total += len(files)

    return {
        "total_files": total,
        "by_locale": inventory,
        "coverage_pct": {
            loc: round(len(files) / 200 * 100, 1)  # 200 questions par langue
            for loc, files in inventory.items()
        },
    }


@router.post("/upload/{locale}/{question_id}", status_code=status.HTTP_201_CREATED)
async def upload_audio(
    locale: str,
    question_id: str,
    file: UploadFile,
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    """
    Upload un fichier MP3 pour une question et une locale.
    Réservé aux admins.
    """
    if locale not in _VALID_LOCALES:
        raise HTTPException(status_code=400, detail=f"Locale invalide : {locale}")

    if not file.filename or not file.filename.lower().endswith(".mp3"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers .mp3 sont acceptés")

    content = await file.read()
    if len(content) > _MAX_MP3_SIZE:
        raise HTTPException(status_code=413, detail=f"Fichier trop volumineux ({len(content)//1024} Ko). Max : 10 Mo")

    # Vérifier la signature MP3 (bytes magiques)
    if content[:3] not in (b'ID3', b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'):
        raise HTTPException(status_code=400, detail="Fichier MP3 invalide (signature incorrecte)")

    dest = _audio_path(locale, question_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)

    return {
        "uploaded": True,
        "locale": locale,
        "question_id": question_id,
        "size_kb": len(content) // 1024,
        "url": f"/static/audio/{locale}/{question_id}.mp3",
    }


@router.delete("/delete/{locale}/{question_id}")
def delete_audio(
    locale: str,
    question_id: str,
    current_user: User = Depends(require_roles("super_admin")),
) -> dict:
    """Supprime un fichier audio (super_admin seulement)."""
    path = _audio_path(locale, question_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Fichier audio non trouvé")
    path.unlink()
    return {"deleted": True, "locale": locale, "question_id": question_id}
