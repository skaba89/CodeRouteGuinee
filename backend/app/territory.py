"""Découpage administratif de la Guinée utilisé par la supervision territoriale.

La DNTT pilote par région administrative ; les centres agréés ne portent que
leur préfecture. Ce référentiel rattache chaque préfecture à sa région (8
régions : Conakry, zone spéciale, et les 7 régions administratives).
"""
from __future__ import annotations

import unicodedata

UNKNOWN_REGION = "Non renseignée"

# Ordre d'affichage : Conakry puis les régions de l'intérieur.
REGIONS: tuple[str, ...] = (
    "Conakry",
    "Boké",
    "Kindia",
    "Labé",
    "Mamou",
    "Faranah",
    "Kankan",
    "N'Zérékoré",
)

_PREFECTURES_BY_REGION: dict[str, tuple[str, ...]] = {
    "Conakry": ("Conakry",),
    "Boké": ("Boffa", "Boké", "Fria", "Gaoual", "Koundara"),
    "Kindia": ("Coyah", "Dubréka", "Forécariah", "Kindia", "Télimélé"),
    "Labé": ("Koubia", "Labé", "Lélouma", "Mali", "Tougué"),
    "Mamou": ("Dalaba", "Mamou", "Pita"),
    "Faranah": ("Dabola", "Dinguiraye", "Faranah", "Kissidougou"),
    "Kankan": ("Kankan", "Kérouané", "Kouroussa", "Mandiana", "Siguiri"),
    "N'Zérékoré": ("Beyla", "Guéckédou", "Lola", "Macenta", "N'Zérékoré", "Yomou"),
}


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_only = "".join(char for char in decomposed if not unicodedata.combining(char))
    return ascii_only.replace("’", "'").strip().lower()


_REGION_BY_PREFECTURE: dict[str, str] = {
    _normalize(prefecture): region
    for region, prefectures in _PREFECTURES_BY_REGION.items()
    for prefecture in prefectures
}


def region_for_prefecture(prefecture: str | None) -> str:
    """Région administrative d'une préfecture, insensible aux accents et à la casse."""
    if not prefecture:
        return UNKNOWN_REGION
    return _REGION_BY_PREFECTURE.get(_normalize(prefecture), UNKNOWN_REGION)
