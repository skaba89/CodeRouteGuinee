"""
Seed e-learning — 5 cours de démonstration CodeRoute Guinée
Idempotent : ne recrée pas si déjà existant.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models_elearning import Course, Lesson


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


COURSES_DATA = [
    {
        "title":       "Signalisation routière guinéenne",
        "description": "Apprenez tous les panneaux de signalisation en vigueur en République de Guinée : interdiction, obligation, danger et information.",
        "category":    "signalisation",
        "order":       1,
        "lessons": [
            {
                "title":            "Panneaux d'interdiction",
                "content":          "Les panneaux d'interdiction sont ronds avec un liseré rouge sur fond blanc. Ils interdisent une action aux conducteurs.\n\n**STOP** — Arrêt obligatoire à l'intersection. Vous devez marquer un arrêt complet et céder le passage.\n\n**Sens interdit** — Cercle rouge avec bande blanche horizontale. Accès interdit dans ce sens.\n\n**Vitesse limitée** — Chiffre en rouge sur fond blanc (30, 50, 70, 90 km/h). Respectez cette limite en Guinée.",
                "order":            1,
                "duration_minutes": 8,
            },
            {
                "title":            "Panneaux de danger",
                "content":          "Les panneaux de danger sont triangulaires, fond jaune ou blanc avec un liseré rouge.\n\n**Danger général** — Point d'exclamation rouge. Soyez vigilant.\n\n**Zone scolaire** — Enfants qui traversent. Réduisez à 30 km/h obligatoirement.\n\n**Dos-d'âne** — Fréquent en Guinée sur les voies urbaines. Ralentissez avant de passer.",
                "order":            2,
                "duration_minutes": 6,
            },
            {
                "title":            "Panneaux d'obligation",
                "content":          "Les panneaux d'obligation sont ronds à fond bleu.\n\n**Direction obligatoire** — Flèche blanche indiquant le seul sens autorisé.\n\n**Passage piéton** — À Conakry, 47 passages piétons officiels sont balisés. Cédez toujours le passage.\n\n**Voie réservée** — Certaines voies du centre de Conakry sont réservées aux transports en commun.",
                "order":            3,
                "duration_minutes": 5,
            },
        ],
    },
    {
        "title":       "Priorités de passage",
        "description": "Maîtrisez les règles de priorité aux intersections, ronds-points et passages piétons, adaptées aux particularités du réseau routier guinéen.",
        "category":    "priorites",
        "order":       2,
        "lessons": [
            {
                "title":            "Règle de priorité à droite",
                "content":          "En l'absence de signalisation, vous devez céder le passage à tout véhicule venant de votre droite.\n\n**Exception** : Les voies principales signalisées par le panneau 'Vous êtes sur une route prioritaire' (losange jaune) vous donnent la priorité.\n\n**À Conakry** : Beaucoup d'intersections sans signalisation — appliquez systématiquement la priorité à droite.",
                "order":            1,
                "duration_minutes": 10,
            },
            {
                "title":            "Ronds-points et giratoires",
                "content":          "Dans un giratoire (sens giratoire imposé), les véhicules déjà engagés dans le rond-point sont prioritaires sur ceux qui entrent.\n\n**Règle Guinée** : Cédez le passage à gauche (aux véhicules déjà sur le giratoire) avant d'entrer.\n\n**Exemples** : Rond-point de la Gare, rond-point du 8 novembre à Conakry.",
                "order":            2,
                "duration_minutes": 8,
            },
        ],
    },
    {
        "title":       "Conduite en ville à Conakry",
        "description": "Situations spécifiques à la conduite urbaine à Conakry : embouteillages, motos, piétons, et règles pratiques.",
        "category":    "conduite_urbaine",
        "order":       3,
        "lessons": [
            {
                "title":            "Partage de la route avec les motos",
                "content":          "Les motos sont très nombreuses à Conakry. Règles essentielles :\n\n- Ne jamais ouvrir une portière sans vérifier les 2 rétroviseurs\n- Laisser 1 mètre minimum lors du dépassement\n- Anticiper les changements de file brusques\n- Les motos ont le droit de circuler entre les files à l'arrêt (interfile) à moins de 50 km/h",
                "order":            1,
                "duration_minutes": 7,
            },
            {
                "title":            "Distances de sécurité",
                "content":          "La règle des 2 secondes : choisissez un point fixe sur la route, le véhicule devant vous le dépasse, comptez 2 secondes minimum avant de le dépasser à votre tour.\n\n**En ville à Conakry** : La visibilité réduite et les sols parfois dégradés imposent :\n- Distance minimale de 3 secondes par temps de pluie\n- 4 secondes la nuit ou sur chaussée déformée",
                "order":            2,
                "duration_minutes": 6,
            },
        ],
    },
    {
        "title":       "Alcool, drogues et conduite",
        "description": "Législation guinéenne sur l'alcool au volant, tests et sanctions prévus par le Code de la route de Guinée.",
        "category":    "securite",
        "order":       4,
        "lessons": [
            {
                "title":            "Taux légal et sanctions",
                "content":          "**Taux légal en Guinée** : 0,5 g/L de sang (identique au droit français de référence).\n\n**Taux zéro tolérance** pour :\n- Les nouveaux conducteurs (permis < 3 ans)\n- Les conducteurs de transport en commun\n- Les chauffeurs de véhicules de plus de 3,5 tonnes\n\n**Sanctions** : Suspension du permis, amende de 500 000 à 2 000 000 GNF, retenue du véhicule.",
                "order":            1,
                "duration_minutes": 9,
            },
        ],
    },
    {
        "title":       "Premiers secours et accidents",
        "description": "Que faire en cas d'accident en Guinée ? Procédures d'urgence, contacts SAMU, et gestes de premiers secours.",
        "category":    "securite",
        "order":       5,
        "lessons": [
            {
                "title":            "Les 3 premières actions (PAS)",
                "content":          "**P — Protéger** : Balisez la zone (triangle de présignalisation à 150 m minimum). Ne fumez pas, coupez le contact.\n\n**A — Alerter** : Appelez immédiatement le **18 (Pompiers)** ou le **15 (SAMU)** ou le **17 (Gendarmerie)**.\n\n**S — Secourir** : N'intervenez que si vous êtes formé. Ne déplacez pas les blessés sauf danger immédiat (feu).",
                "order":            1,
                "duration_minutes": 10,
            },
            {
                "title":            "Position latérale de sécurité (PLS)",
                "content":          "La PLS maintient les voies aériennes libres pour une personne inconsciente qui respire.\n\n1. Agenouillez-vous côté victime\n2. Mettez le bras proche de vous à angle droit, coude plié\n3. Amenez l'autre bras sur la joue\n4. Pliez le genou éloigné et retournez doucement\n5. Stabilisez en ajustant la tête en arrière\n\nVérifiez la respiration toutes les 30 secondes jusqu'à l'arrivée des secours.",
                "order":            2,
                "duration_minutes": 12,
            },
        ],
    },
]


def seed_elearning(db: Session) -> dict:
    """Insère les cours demo si absents. Retourne un rapport."""
    created_courses = 0
    created_lessons = 0

    for course_data in COURSES_DATA:
        # Vérifier si le cours existe déjà
        existing = db.scalar(
            select(Course).where(Course.title == course_data["title"])
        )
        if existing:
            continue

        course = Course(
            id          = str(uuid.uuid4()),
            title       = course_data["title"],
            description = course_data["description"],
            category    = course_data["category"],
            order       = course_data["order"],
            is_active   = True,
            created_at  = _now(),
            updated_at  = _now(),
        )
        db.add(course)
        db.flush()
        created_courses += 1

        for lesson_data in course_data["lessons"]:
            lesson = Lesson(
                id               = str(uuid.uuid4()),
                course_id        = course.id,
                title            = lesson_data["title"],
                content          = lesson_data["content"],
                order            = lesson_data["order"],
                duration_minutes = lesson_data["duration_minutes"],
                is_active        = True,
                created_at       = _now(),
                updated_at       = _now(),
            )
            db.add(lesson)
            created_lessons += 1

    db.commit()
    return {
        "courses_created": created_courses,
        "lessons_created": created_lessons,
        "total_courses":   len(COURSES_DATA),
    }


if __name__ == "__main__":
    import json
    db = SessionLocal()
    try:
        result = seed_elearning(db)
        print(json.dumps(result, indent=2))
    finally:
        db.close()
