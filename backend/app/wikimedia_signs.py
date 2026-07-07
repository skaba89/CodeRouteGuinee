"""
Catalogue des panneaux de signalisation français — Wikimedia Commons.

Les panneaux routiers français sont des œuvres officielles publiées par
l'État : les fichiers SVG correspondants sur Wikimedia Commons sont en
domaine public (PD-FRGov / PD-self des contributeurs). Ils sont donc
librement réutilisables, y compris pour un usage commercial ou officiel.

Chaque entrée mappe un `sign_type` (utilisé par _get_media_for_question)
vers l'URL directe du fichier SVG sur upload.wikimedia.org.

NB : ces URLs pointent vers le CDN Wikimedia. En production, il est
recommandé de les re-héberger (Cloudinary/Supabase) pour la pérennité,
mais elles fonctionnent directement.
"""
from __future__ import annotations

# sign_type → (url_svg_wikimedia, description)
WIKIMEDIA_SIGNS: dict[str, tuple[str, str]] = {
    # ── Interdiction (rond rouge) ────────────────────────────────────────
    "no_entry": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_B1.svg",
        "Sens interdit à tout véhicule",
    ),
    "no_overtaking": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_B3.svg",
        "Interdiction de dépasser",
    ),
    "no_parking": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_B6a1.svg",
        "Stationnement interdit",
    ),

    # ── Vitesses (rond rouge, chiffre) ───────────────────────────────────
    "speed_30": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_B14_%2830%29.svg",
        "Limitation de vitesse à 30 km/h",
    ),
    "speed_50": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_B14_%2850%29.svg",
        "Limitation de vitesse à 50 km/h",
    ),
    "speed_70": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_B14_%2870%29.svg",
        "Limitation de vitesse à 70 km/h",
    ),
    "speed_90": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_B14_%2890%29.svg",
        "Limitation de vitesse à 90 km/h",
    ),
    "speed_110": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_B14_%28110%29.svg",
        "Limitation de vitesse à 110 km/h",
    ),
    "speed_130": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_B14_%28130%29.svg",
        "Limitation de vitesse à 130 km/h",
    ),

    # ── Priorité ─────────────────────────────────────────────────────────
    "stop": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_AB4.svg",
        "Arrêt à l'intersection (STOP)",
    ),
    "give_way": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_AB3a.svg",
        "Cédez le passage",
    ),
    "priority": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_AB6.svg",
        "Caractère prioritaire d'une route",
    ),

    # ── Obligation (rond bleu) ───────────────────────────────────────────
    "roundabout": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_B21-1.svg",
        "Contournement obligatoire par la droite (giratoire)",
    ),
    "mandatory_straight": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_B21-1.svg",
        "Direction obligatoire tout droit",
    ),

    # ── Danger (triangle rouge) ──────────────────────────────────────────
    "danger_generic": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_A14.svg",
        "Autres dangers",
    ),
    "danger_children": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_A13a.svg",
        "Endroit fréquenté par des enfants",
    ),
    "danger_slippery": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_A4.svg",
        "Chaussée glissante",
    ),
    "danger_bend": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_A1a.svg",
        "Virage à droite",
    ),
    "pedestrian_crossing": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_A13b.svg",
        "Passage pour piétons",
    ),

    # ── Indication ───────────────────────────────────────────────────────
    "parking": (
        "https://commons.wikimedia.org/wiki/Special:FilePath/France_road_sign_C1a.svg",
        "Stationnement autorisé",
    ),
}
