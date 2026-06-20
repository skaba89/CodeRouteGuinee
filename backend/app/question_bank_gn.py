"""
Banque officielle de questions — Code de la route Guinée (Catégorie B).
Basée sur le programme de l'examen officiel guinéen (DNTT / Ministère des Transports).

40 questions actives couvrant les 8 catégories officielles :
  1. Signalisation (panneaux, marquages, feux) — 10 questions
  2. Priorités et intersections — 6 questions
  3. Vitesse et distances — 5 questions
  4. Dépassement et manœuvres — 5 questions
  5. Sécurité passive (ceinture, équipements) — 4 questions
  6. Comportement en situation d'urgence — 4 questions
  7. Alcool, drogues, médicaments — 3 questions
  8. Premiers secours et environnement — 3 questions

Règle d'admission : 35 bonnes réponses sur 40 (87,5 %)
Durée : 30 minutes
"""

QUESTIONS_GN: list[dict] = [

    # ── 1. SIGNALISATION ─────────────────────────────────────────────────

    {
        "category": "signalisation",
        "text": "Que signifie un panneau circulaire rouge avec une barre horizontale blanche ?",
        "options": [
            "Interdiction de dépasser",
            "Sens interdit — accès totalement interdit",
            "Arrêt obligatoire",
            "Limitation de vitesse à 0 km/h",
        ],
        "correct_answer": "Sens interdit — accès totalement interdit",
        "explanation": "Le panneau rond rouge avec barre blanche indique le sens interdit : aucun véhicule ne peut s'y engager.",
    },
    {
        "category": "signalisation",
        "text": "Un feu tricolore est rouge fixe. Que devez-vous faire ?",
        "options": [
            "Ralentir et passer prudemment",
            "Klaxonner et passer rapidement",
            "S'arrêter avant le stop ou la ligne d'arrêt",
            "Ignorer le feu si la voie est libre",
        ],
        "correct_answer": "S'arrêter avant le stop ou la ligne d'arrêt",
        "explanation": "Le feu rouge impose un arrêt complet avant la ligne d'arrêt, quelle que soit la visibilité.",
    },
    {
        "category": "signalisation",
        "text": "Que signifie un panneau triangulaire rouge avec un point d'exclamation ?",
        "options": [
            "Travaux sur la chaussée",
            "Danger non spécifié — vigilance requise",
            "Priorité à droite",
            "Zone scolaire",
        ],
        "correct_answer": "Danger non spécifié — vigilance requise",
        "explanation": "Le triangle rouge avec point d'exclamation signale un danger dont la nature n'est pas précisée.",
    },
    {
        "category": "signalisation",
        "text": "Un marquage au sol en ligne blanche continue signifie :",
        "options": [
            "On peut changer de file si la voie est libre",
            "Il est interdit de franchir ou de chevaucher la ligne",
            "Zone de stationnement autorisé",
            "Fin de route prioritaire",
        ],
        "correct_answer": "Il est interdit de franchir ou de chevaucher la ligne",
        "explanation": "La ligne continue blanche est infranchissable — ni dépassement ni changement de file n'est autorisé.",
    },
    {
        "category": "signalisation",
        "text": "Que signifie le signal sonore du klaxon d'un autre conducteur ?",
        "options": [
            "Il vous demande de céder le passage",
            "Il vous avertit d'un danger ou de sa présence",
            "Il vous demande de vous arrêter",
            "Il vous autorise à dépasser",
        ],
        "correct_answer": "Il vous avertit d'un danger ou de sa présence",
        "explanation": "Le klaxon est un avertisseur acoustique signalant la présence d'un véhicule ou un danger.",
    },
    {
        "category": "signalisation",
        "text": "Un feu orange clignotant à une intersection signifie :",
        "options": [
            "Arrêt obligatoire",
            "Passage libre sans précaution",
            "Ralentir et traverser avec prudence",
            "Feu hors service — priorité à droite",
        ],
        "correct_answer": "Ralentir et traverser avec prudence",
        "explanation": "Le feu orange clignotant indique un carrefour dangereux : traversez lentement en vous assurant de la sécurité.",
    },
    {
        "category": "signalisation",
        "text": "Que signifie un panneau rond bleu avec une flèche blanche pointant vers le haut ?",
        "options": [
            "Sens unique obligatoire",
            "Voie réservée aux bus",
            "Direction obligatoire : tout droit",
            "Vitesse minimale recommandée",
        ],
        "correct_answer": "Direction obligatoire : tout droit",
        "explanation": "Le panneau rond bleu à flèche blanche impose la direction indiquée — ici, aller tout droit.",
    },
    {
        "category": "signalisation",
        "text": "Que signifie un panneau octogonal rouge portant le mot STOP ?",
        "options": [
            "Cédez le passage aux véhicules venant de droite",
            "Arrêt obligatoire et priorité aux véhicules sur la route principale",
            "Zone de ralentissement temporaire",
            "Fin de limitation de vitesse",
        ],
        "correct_answer": "Arrêt obligatoire et priorité aux véhicules sur la route principale",
        "explanation": "Le STOP impose un arrêt complet (roues immobiles) avant la ligne, suivi d'une cession de priorité.",
    },
    {
        "category": "signalisation",
        "text": "La signalisation temporaire de chantier est de couleur :",
        "options": ["Bleue", "Verte", "Orange ou jaune", "Blanche"],
        "correct_answer": "Orange ou jaune",
        "explanation": "Les panneaux de chantier sont orange (fond) afin d'être distinctifs par rapport à la signalisation permanente.",
    },
    {
        "category": "signalisation",
        "text": "Un feu vert pour les piétons à un passage protégé signifie pour le conducteur :",
        "options": [
            "Priorité absolue aux piétons — il doit s'arrêter",
            "Il peut passer si aucun piéton n'est visible",
            "Il peut passer en klaxonnant",
            "Ce feu ne concerne pas les conducteurs",
        ],
        "correct_answer": "Priorité absolue aux piétons — il doit s'arrêter",
        "explanation": "Quand le feu est vert pour les piétons, le conducteur doit marquer l'arrêt et leur céder le passage.",
    },

    # ── 2. PRIORITÉS ET INTERSECTIONS ───────────────────────────────────

    {
        "category": "priorites",
        "text": "À une intersection sans signalisation, quelle est la règle de priorité ?",
        "options": [
            "Priorité aux véhicules les plus rapides",
            "Priorité aux véhicules venant de la droite",
            "Priorité aux véhicules venant de la gauche",
            "Priorité aux véhicules les plus lourds",
        ],
        "correct_answer": "Priorité aux véhicules venant de la droite",
        "explanation": "La règle générale est la priorité à droite : le véhicule arrivant de droite est prioritaire.",
    },
    {
        "category": "priorites",
        "text": "Qui est prioritaire sur une route nationale face à une route secondaire ?",
        "options": [
            "Le véhicule arrivant de droite",
            "Le véhicule sur la route nationale (route principale)",
            "Le véhicule le plus rapide",
            "Les deux véhicules doivent négocier",
        ],
        "correct_answer": "Le véhicule sur la route nationale (route principale)",
        "explanation": "Le panneau 'Cédez le passage' ou 'STOP' sur la secondaire désigne la route principale comme prioritaire.",
    },
    {
        "category": "priorites",
        "text": "Dans un rond-point, qui est prioritaire ?",
        "options": [
            "Le véhicule qui entre dans le rond-point",
            "Le véhicule déjà engagé dans le rond-point",
            "Le véhicule venant de la droite",
            "Le véhicule le plus grand",
        ],
        "correct_answer": "Le véhicule déjà engagé dans le rond-point",
        "explanation": "Les véhicules circulant dans le giratoire ont la priorité ; ceux qui entrent doivent céder le passage.",
    },
    {
        "category": "priorites",
        "text": "Les véhicules d'urgence (pompiers, SAMU, police) avec gyrophare et sirène :",
        "options": [
            "N'ont aucune priorité particulière",
            "Ont priorité absolue — tous les conducteurs doivent se dégager",
            "Sont prioritaires seulement sur les routes nationales",
            "Sont prioritaires seulement si la sirène est activée",
        ],
        "correct_answer": "Ont priorité absolue — tous les conducteurs doivent se dégager",
        "explanation": "Les véhicules d'urgence en intervention (gyrophare + sirène) ont priorité absolue ; serrez à droite ou arrêtez-vous.",
    },
    {
        "category": "priorites",
        "text": "À un carrefour, vous allez tout droit. Un véhicule arrivant en face tourne à sa gauche. Qui cède ?",
        "options": [
            "Vous, car vous n'avez aucune priorité",
            "Le véhicule qui tourne, car il coupe votre trajectoire",
            "Le véhicule le plus rapide passe en premier",
            "Aucun des deux — vous négociez",
        ],
        "correct_answer": "Le véhicule qui tourne, car il coupe votre trajectoire",
        "explanation": "Tout véhicule effectuant un virage à gauche doit céder le passage aux véhicules qu'il croise.",
    },
    {
        "category": "priorites",
        "text": "Aux passages à niveau non gardés et sans barrières, vous devez :",
        "options": [
            "Traverser rapidement",
            "Marquer l'arrêt, regarder des deux côtés, traverser rapidement",
            "Klaxonner avant de traverser",
            "Céder le passage uniquement si vous entendez le train",
        ],
        "correct_answer": "Marquer l'arrêt, regarder des deux côtés, traverser rapidement",
        "explanation": "Aux passages à niveau non gardés, l'arrêt est obligatoire et la traversée doit être rapide une fois la voie libre.",
    },

    # ── 3. VITESSE ET DISTANCES ──────────────────────────────────────────

    {
        "category": "vitesse",
        "text": "Quelle est la vitesse maximale autorisée en agglomération en Guinée (sauf signalisation contraire) ?",
        "options": ["40 km/h", "50 km/h", "60 km/h", "70 km/h"],
        "correct_answer": "50 km/h",
        "explanation": "La vitesse limite en agglomération est fixée à 50 km/h par la réglementation guinéenne.",
    },
    {
        "category": "vitesse",
        "text": "Sur route hors agglomération (route nationale), la vitesse maximale est :",
        "options": ["80 km/h", "90 km/h", "100 km/h", "110 km/h"],
        "correct_answer": "90 km/h",
        "explanation": "La limite hors agglomération sur route nationale est de 90 km/h en Guinée.",
    },
    {
        "category": "vitesse",
        "text": "Quelle est la distance de sécurité minimale à respecter avec le véhicule qui vous précède ?",
        "options": [
            "5 mètres",
            "La distance parcourue en 1 seconde",
            "La distance parcourue en 2 secondes minimum",
            "10 mètres fixes",
        ],
        "correct_answer": "La distance parcourue en 2 secondes minimum",
        "explanation": "La règle des 2 secondes garantit un temps de réaction suffisant. Elle correspond à 28 m à 50 km/h, 50 m à 90 km/h.",
    },
    {
        "category": "vitesse",
        "text": "En cas de brouillard dense réduisant la visibilité à 50 mètres, vous devez :",
        "options": [
            "Maintenir votre vitesse habituelle",
            "Adapter votre vitesse pour pouvoir vous arrêter dans la distance de visibilité",
            "Allumer seulement les feux de route",
            "Rouler au centre de la route",
        ],
        "correct_answer": "Adapter votre vitesse pour pouvoir vous arrêter dans la distance de visibilité",
        "explanation": "Par visibilité réduite, la distance d'arrêt doit toujours être inférieure à votre distance de visibilité.",
    },
    {
        "category": "vitesse",
        "text": "À 90 km/h, quelle est la distance d'arrêt approximative (réaction + freinage) sur route sèche ?",
        "options": ["30 mètres", "45 mètres", "75 mètres", "120 mètres"],
        "correct_answer": "75 mètres",
        "explanation": "À 90 km/h : environ 25 m de réaction (1 s) + 50 m de freinage = 75 m sur route sèche.",
    },

    # ── 4. DÉPASSEMENT ET MANŒUVRES ──────────────────────────────────────

    {
        "category": "depassement",
        "text": "Avant de dépasser un véhicule, vous devez vérifier :",
        "options": [
            "Que votre klaxon fonctionne bien",
            "Que la voie en sens inverse est libre, que le dépassement est autorisé et que vous pouvez terminer avant un obstacle",
            "Que le conducteur devant vous vous a vu",
            "Que votre carburant est suffisant",
        ],
        "correct_answer": "Que la voie en sens inverse est libre, que le dépassement est autorisé et que vous pouvez terminer avant un obstacle",
        "explanation": "Le dépassement exige vérification des rétroviseurs, de la signalisation, de la visibilité et de l'espace disponible.",
    },
    {
        "category": "depassement",
        "text": "Le dépassement est interdit :",
        "options": [
            "Sur autoroute",
            "À proximité d'un virage, sommet de côte, ou en cas de ligne continue",
            "Par temps de pluie légère",
            "Sur les routes à deux voies",
        ],
        "correct_answer": "À proximité d'un virage, sommet de côte, ou en cas de ligne continue",
        "explanation": "Ces endroits réduisent la visibilité ou impliquent un danger immédiat ; le dépassement y est strictement interdit.",
    },
    {
        "category": "depassement",
        "text": "Avant de tourner à gauche, vous devez :",
        "options": [
            "Accélérer pour dépasser les véhicules qui suivent",
            "Vous placer dans la file de gauche, signaler, réduire la vitesse, vérifier les rétroviseurs",
            "Klaxonner pour avertir",
            "Couper directement sans signal",
        ],
        "correct_answer": "Vous placer dans la file de gauche, signaler, réduire la vitesse, vérifier les rétroviseurs",
        "explanation": "Toute manœuvre exige signal suffisamment tôt, positionnement correct et vérification arrière.",
    },
    {
        "category": "depassement",
        "text": "Pour effectuer un demi-tour (faire demi-tour en U), vous devez :",
        "options": [
            "Le faire uniquement sur les voies à sens unique",
            "Vous assurer qu'il n'est pas interdit et que cela ne présente pas de danger pour les autres",
            "L'effectuer à grande vitesse pour minimiser la gêne",
            "Klaxonner pendant toute la manœuvre",
        ],
        "correct_answer": "Vous assurer qu'il n'est pas interdit et que cela ne présente pas de danger pour les autres",
        "explanation": "Le demi-tour est autorisé sauf signalisation contraire, avec vérification préalable de la sécurité.",
    },
    {
        "category": "depassement",
        "text": "Vous circulez derrière un camion lent. Pour le dépasser de façon sécurisée, vous devez :",
        "options": [
            "Klaxonner pour qu'il accélère",
            "Vous placer très proche du camion pour évaluer la situation",
            "Vous décaler légèrement pour voir plus loin, vérifier la voie libre, puis dépasser",
            "Allumer vos phares et dépasser immédiatement",
        ],
        "correct_answer": "Vous décaler légèrement pour voir plus loin, vérifier la voie libre, puis dépasser",
        "explanation": "Se décaler permet une meilleure visibilité avant d'engager le dépassement d'un véhicule long.",
    },

    # ── 5. SÉCURITÉ PASSIVE ──────────────────────────────────────────────

    {
        "category": "securite_passive",
        "text": "Le port de la ceinture de sécurité est :",
        "options": [
            "Obligatoire uniquement sur les routes nationales",
            "Obligatoire pour tous les occupants du véhicule, en toutes circonstances",
            "Conseillé mais pas obligatoire en ville",
            "Obligatoire seulement pour le conducteur",
        ],
        "correct_answer": "Obligatoire pour tous les occupants du véhicule, en toutes circonstances",
        "explanation": "La ceinture est obligatoire pour tous les occupants (avant et arrière) dès que le véhicule est en mouvement.",
    },
    {
        "category": "securite_passive",
        "text": "À quelle distance devez-vous placer un triangle de pré-signalisation derrière votre véhicule en panne sur route ?",
        "options": [
            "5 mètres",
            "Immédiatement derrière le véhicule",
            "30 mètres minimum, davantage sur route rapide",
            "100 mètres exactement",
        ],
        "correct_answer": "30 mètres minimum, davantage sur route rapide",
        "explanation": "Le triangle se place à 30 m minimum ; sur route rapide ou à mauvaise visibilité, plus loin pour avertir à temps.",
    },
    {
        "category": "securite_passive",
        "text": "Un siège enfant homologué est obligatoire pour les enfants de :",
        "options": [
            "Moins de 5 ans",
            "Moins de 10 ans ou de moins de 1,35 m",
            "Moins de 3 ans uniquement",
            "Moins de 6 ans et moins de 15 kg",
        ],
        "correct_answer": "Moins de 10 ans ou de moins de 1,35 m",
        "explanation": "Tout enfant de moins de 10 ans ou mesurant moins de 1,35 m doit être installé dans un dispositif de retenue adapté.",
    },
    {
        "category": "securite_passive",
        "text": "L'utilisation du téléphone portable tenu en main au volant est :",
        "options": [
            "Autorisée à l'arrêt",
            "Autorisée si vous roulez à moins de 30 km/h",
            "Interdite en mouvement — seul le kit mains libres est toléré",
            "Autorisée sur les routes peu fréquentées",
        ],
        "correct_answer": "Interdite en mouvement — seul le kit mains libres est toléré",
        "explanation": "Le téléphone tenu en main en conduisant est interdit : il réduit l'attention et augmente le risque d'accident.",
    },

    # ── 6. COMPORTEMENT EN URGENCE ───────────────────────────────────────

    {
        "category": "urgence",
        "text": "Vos freins semblent défaillants en descente. Que faites-vous ?",
        "options": [
            "Coupez le moteur immédiatement",
            "Rétrogradez pour freiner avec le moteur, utilisez le frein à main progressivement, cherchez un obstacle naturel",
            "Accélérez pour dépasser le virage dangereux",
            "Ouvrez la portière pour ralentir",
        ],
        "correct_answer": "Rétrogradez pour freiner avec le moteur, utilisez le frein à main progressivement, cherchez un obstacle naturel",
        "explanation": "Freinage moteur + frein à main progressif (sans bloquer les roues) + sortie de route contrôlée sont les bons réflexes.",
    },
    {
        "category": "urgence",
        "text": "Votre véhicule prend feu. Quelle est la séquence correcte ?",
        "options": [
            "Appeler les pompiers depuis le véhicule, puis sortir",
            "Arrêtez, coupez le moteur, sortez et éloignez-vous, appelez les secours",
            "Tenter d'éteindre le feu avec de l'eau du radiateur",
            "Continuer à rouler pour atteindre un poste de secours",
        ],
        "correct_answer": "Arrêtez, coupez le moteur, sortez et éloignez-vous, appelez les secours",
        "explanation": "Le risque d'explosion impose une évacuation immédiate et l'éloignement avant tout appel aux secours.",
    },
    {
        "category": "urgence",
        "text": "En cas d'aquaplaning (glissement sur l'eau), vous devez :",
        "options": [
            "Freiner fortement pour regagner l'adhérence",
            "Tourner le volant en sens inverse",
            "Lâcher l'accélérateur doucement, tenir le volant sans brusquerie, laisser la vitesse diminuer",
            "Changer de voie rapidement",
        ],
        "correct_answer": "Lâcher l'accélérateur doucement, tenir le volant sans brusquerie, laisser la vitesse diminuer",
        "explanation": "Tout freinage ou coup de volant brusque aggraverait la perte de contrôle ; il faut laisser les pneus reprendre contact.",
    },
    {
        "category": "urgence",
        "text": "Sur une route enneigée ou glissante, la distance de freinage est :",
        "options": [
            "Identique à la route sèche",
            "1,5 fois plus longue",
            "Jusqu'à 5 à 10 fois plus longue",
            "2 fois plus longue exactement",
        ],
        "correct_answer": "Jusqu'à 5 à 10 fois plus longue",
        "explanation": "Sur chaussée verglaçée, la distance de freinage peut être multipliée par 5 à 10 — adapter la vitesse est impératif.",
    },

    # ── 7. ALCOOL, DROGUES, MÉDICAMENTS ─────────────────────────────────

    {
        "category": "alcool_drogues",
        "text": "Le taux légal d'alcoolémie maximal autorisé pour conduire en Guinée est :",
        "options": [
            "0,0 g/L — tolérance zéro",
            "0,3 g/L de sang",
            "0,5 g/L de sang",
            "0,8 g/L de sang",
        ],
        "correct_answer": "0,5 g/L de sang",
        "explanation": "La limite légale guinéenne est de 0,5 g/L de sang (0,25 mg/L d'air expiré), conformément aux normes CEDEAO.",
    },
    {
        "category": "alcool_drogues",
        "text": "La consommation de cannabis avant de conduire :",
        "options": [
            "Est sans effet sur la conduite",
            "Perturbe les réflexes, la coordination et la perception du temps — elle est interdite",
            "Améliore la concentration",
            "Est tolérée si consommée plusieurs heures avant",
        ],
        "correct_answer": "Perturbe les réflexes, la coordination et la perception du temps — elle est interdite",
        "explanation": "Le cannabis altère les capacités de conduite et sa présence est détectable plusieurs heures après consommation.",
    },
    {
        "category": "alcool_drogues",
        "text": "Certains médicaments peuvent-ils affecter la conduite ?",
        "options": [
            "Non, les médicaments sont inoffensifs",
            "Oui — somnolence, réflexes diminués, troubles de la vision ; lire les notices et consulter votre médecin",
            "Seulement les médicaments à base de codéine",
            "Seulement les médicaments pris à haute dose",
        ],
        "correct_answer": "Oui — somnolence, réflexes diminués, troubles de la vision ; lire les notices et consulter votre médecin",
        "explanation": "De nombreux médicaments (antihistaminiques, anxiolytiques, antidouleurs) altèrent la vigilance ; vérifiez toujours la notice.",
    },

    # ── 8. PREMIERS SECOURS ET ENVIRONNEMENT ────────────────────────────

    {
        "category": "premiers_secours",
        "text": "Vous arrivez sur les lieux d'un accident. La première action est :",
        "options": [
            "Prendre des photos",
            "Protéger, alerter, secourir (PAS) — sécuriser la zone, appeler les secours, aider les victimes",
            "Déplacer immédiatement les blessés",
            "Chercher les responsables",
        ],
        "correct_answer": "Protéger, alerter, secourir (PAS) — sécuriser la zone, appeler les secours, aider les victimes",
        "explanation": "La règle PAS : Protéger (éviter un sur-accident), Alerter (secours), Secourir (sans aggraver les blessures).",
    },
    {
        "category": "premiers_secours",
        "text": "Une victime d'accident est inconsciente et respire. Que faites-vous ?",
        "options": [
            "La laisser sur le dos, surveiller",
            "La mettre en Position Latérale de Sécurité (PLS) et appeler les secours",
            "Lui donner de l'eau",
            "La faire marcher pour la réveiller",
        ],
        "correct_answer": "La mettre en Position Latérale de Sécurité (PLS) et appeler les secours",
        "explanation": "La PLS maintient les voies respiratoires libres pour une victime inconsciente qui respire encore.",
    },
    {
        "category": "premiers_secours",
        "text": "Pour réduire la pollution et préserver l'environnement, le conducteur doit :",
        "options": [
            "Rouler le moteur au ralenti lors des arrêts prolongés",
            "Couper le moteur lors des arrêts de plus de 30 secondes, entretenir son véhicule régulièrement",
            "Utiliser du carburant non filtré pour le moteur",
            "Rouler à grande vitesse pour consommer moins",
        ],
        "correct_answer": "Couper le moteur lors des arrêts de plus de 30 secondes, entretenir son véhicule régulièrement",
        "explanation": "Couper le moteur à l'arrêt réduit les émissions. Un véhicule bien entretenu consomme moins et pollue moins.",
    },
]

assert len(QUESTIONS_GN) == 40, f"La banque doit contenir exactement 40 questions, trouvé : {len(QUESTIONS_GN)}"

# ══════════════════════════════════════════════════════════════════════════
# BANQUE ÉTENDUE — MODULE ENTRAÎNEMENT (Mois 4–6)
# 160 questions supplémentaires pour le mode entraînement libre
# Total : 200 questions pour la préparation, 40 tirées pour l'examen officiel
# ══════════════════════════════════════════════════════════════════════════

QUESTIONS_TRAINING: list[dict] = [

    # ── SIGNALISATION AVANCÉE ─────────────────────────────────────

    {"category":"signalisation","text":"Un panneau rond rouge barré d'une diagonale rouge signifie :","options":["Fin de limitation de vitesse","Fin de toutes les interdictions","Fin de route prioritaire","Stationnement interdit"],"correct_answer":"Fin de toutes les interdictions","explanation":"Ce panneau marque la fin de toutes les interdictions et obligations imposées précédemment par la signalisation."},
    {"category":"signalisation","text":"La signalisation temporaire orange est prioritaire sur la signalisation permanente. Cette affirmation est :","options":["Vraie","Fausse","Vraie seulement la nuit","Fausse sur les routes nationales"],"correct_answer":"Vraie","explanation":"En cas de chantier, les panneaux oranges prévalent sur les permanents car ils reflètent l'état réel de la route."},
    {"category":"signalisation","text":"Un panneau triangulaire avec deux enfants signifie :","options":["Aire de jeux","Zone scolaire — ralentir","Croisement dangereux","Passage piétons"],"correct_answer":"Zone scolaire — ralentir","explanation":"Ce panneau indique une zone fréquentée par des enfants (école, cour de récréation). Ralentissez et redoublez de vigilance."},
    {"category":"signalisation","text":"Un panneau carré bleu avec un P blanc signifie :","options":["Parking interdit","Parking autorisé","Parking payant obligatoire","Zone bleue"],"correct_answer":"Parking autorisé","explanation":"Le panneau P bleu indique une zone de stationnement autorisé dont les conditions sont précisées par panneaux complémentaires."},
    {"category":"signalisation","text":"Les feux de détresse (warnings) s'utilisent :","options":["Pour signaler une manœuvre","En cas d'arrêt d'urgence ou de panne visible","Pour remercier un autre conducteur","Uniquement la nuit"],"correct_answer":"En cas d'arrêt d'urgence ou de panne visible","explanation":"Les feux de détresse signalent un danger stationnaire. Ils ne remplacent pas le triangle de signalisation."},
    {"category":"signalisation","text":"Un feu rouge clignotant à un passage à niveau signifie :","options":["Ralentir et passer vite","Arrêt absolu — train en approche","Priorité aux piétons","Feu hors service"],"correct_answer":"Arrêt absolu — train en approche","explanation":"Le feu rouge clignotant au passage à niveau est un signal d'arrêt absolu. Le train est en approche — ne jamais passer."},
    {"category":"signalisation","text":"Les bandes rugueuses sur la chaussée servent à :","options":["Délimiter les voies","Alerter le conducteur par vibration qu'il quitte la route","Indiquer un passage clouté","Marquer une zone de ralentissement"],"correct_answer":"Alerter le conducteur par vibration qu'il quitte la route","explanation":"Les bandes rugueuses créent une vibration perceptible pour réveiller un conducteur somnolent dérivant hors de sa voie."},
    {"category":"signalisation","text":"Un panneau 'Cédez le passage' (triangle inversé) diffère du STOP car :","options":["Il n'impose pas d'arrêt si la voie est libre","Il s'applique seulement aux poids lourds","Il autorise un dépassement","Il s'applique la nuit seulement"],"correct_answer":"Il n'impose pas d'arrêt si la voie est libre","explanation":"Le cédez le passage impose de s'arrêter seulement si un véhicule approche. Le STOP impose un arrêt complet dans tous les cas."},
    {"category":"signalisation","text":"Les lignes de rive (bord de chaussée) sont de couleur :","options":["Jaune","Blanche","Orange","Verte"],"correct_answer":"Blanche","explanation":"Les lignes de rive délimitent le bord de la chaussée et sont blanches. Ne pas les confondre avec les lignes axiales."},
    {"category":"signalisation","text":"Que signifie une flèche verte en addition au feu rouge ?","options":["Vous pouvez passer dans la direction indiquée si la voie est dégagée","Feu prioritaire pour les bus","Vous pouvez passer quelle que soit la direction","Arrêt facultatif"],"correct_answer":"Vous pouvez passer dans la direction indiquée si la voie est dégagée","explanation":"La flèche verte complétant un feu rouge permet de s'engager dans la direction indiquée, sans priorité — les piétons restent prioritaires."},

    # ── PRIORITÉS AVANCÉES ────────────────────────────────────────

    {"category":"priorites","text":"Sur une route en côte étroite, qui cède le passage ?","options":["Celui qui monte","Celui qui descend — il est plus facile de reculer","Le véhicule le plus lourd","Le conducteur le plus expérimenté"],"correct_answer":"Celui qui descend — il est plus facile de reculer","explanation":"Sur une route en côte trop étroite, le véhicule qui descend dispose d'une meilleure visibilité et peut reculer plus facilement."},
    {"category":"priorites","text":"Un bus scolaire arrêté avec gyrophare allumé impose au conducteur passant derrière :","options":["De doubler rapidement","De ralentir considérablement car des enfants peuvent traverser","De klaxonner pour prévenir","De dépasser par la gauche"],"correct_answer":"De ralentir considérablement car des enfants peuvent traverser","explanation":"Les bus scolaires avec gyrophare signalent la présence d'enfants. Ralentissez fortement — ils peuvent surgir n'importe où."},
    {"category":"priorites","text":"À une intersection, un cycliste vient de votre droite. Vous devez :","options":["Passer en premier car les cyclistes sont moins dangereux","Lui céder la priorité comme à tout véhicule venant de droite","Klaxonner pour le prévenir","Passer car vous êtes motorisé"],"correct_answer":"Lui céder la priorité comme à tout véhicule venant de droite","explanation":"Un cycliste est un usager de la route à part entière. La règle de priorité à droite s'applique sans distinction."},
    {"category":"priorites","text":"Un piéton s'engage sur un passage clouté devant vous. Vous devez :","options":["Continuer si vous avez le feu vert","Klaxonner pour l'alerter","Vous arrêter et le laisser traverser","Ralentir légèrement sans vous arrêter"],"correct_answer":"Vous arrêter et le laisser traverser","explanation":"Les piétons engagés sur un passage protégé ont la priorité absolue, même si votre feu est vert."},
    {"category":"priorites","text":"Qui est prioritaire entre un tramway et un véhicule ordinaire ?","options":["Le véhicule ordinaire","Le tramway, dans tous les cas","Le premier arrivé","Dépend de la signalisation"],"correct_answer":"Le tramway, dans tous les cas","explanation":"Le tramway est prioritaire sur les véhicules ordinaires partout où il circule. Sa masse le rend impossible à arrêter rapidement."},
    {"category":"priorites","text":"Vous sortez d'un parking privé sur la voie publique. Vous devez :","options":["Accélérer rapidement pour vous insérer","Céder le passage à tous les usagers de la chaussée","Allumer vos feux de détresse","Klaxonner avant de sortir"],"correct_answer":"Céder le passage à tous les usagers de la chaussée","explanation":"En sortant d'un accès privé, vous entrez sur la voie publique et devez céder la priorité à tous, y compris aux piétons."},

    # ── VITESSE AVANCÉE ────────────────────────────────────────────

    {"category":"vitesse","text":"La distance de freinage double lorsque la vitesse :","options":["Double","Augmente de 50 %","Triple","Augmente de 25 %"],"correct_answer":"Double","explanation":"La distance de freinage varie au carré de la vitesse. Si la vitesse double, la distance de freinage est multipliée par 4."},
    {"category":"vitesse","text":"Par temps de pluie, la distance de freinage est multipliée par :","options":["1,5","2","3","4"],"correct_answer":"2","explanation":"Sur chaussée mouillée, la distance de freinage est environ deux fois plus longue qu'à sec. Doublez vos distances de sécurité."},
    {"category":"vitesse","text":"La règle des 2 secondes s'applique par temps normal. Par pluie ou brouillard, elle devient :","options":["3 secondes","4 secondes","5 secondes","Elle reste 2 secondes"],"correct_answer":"4 secondes","explanation":"En mauvaises conditions climatiques, la distance de sécurité doit être au moins doublée, soit 4 secondes."},
    {"category":"vitesse","text":"La 'vitesse excessive non adaptée aux conditions' concerne :","options":["Uniquement les excès de vitesse au-dessus de la limite légale","Tout conducteur roulant trop vite pour les conditions (pluie, nuit, chantier) même sous la limite légale","Uniquement les poids lourds","Les conducteurs novices uniquement"],"correct_answer":"Tout conducteur roulant trop vite pour les conditions (pluie, nuit, chantier) même sous la limite légale","explanation":"On peut être en infraction pour vitesse inadaptée même en respectant la limitation si les conditions imposent de rouler plus lentement."},
    {"category":"vitesse","text":"Un conducteur à 90 km/h distrait 1 seconde parcourt :","options":["15 mètres","25 mètres","30 mètres","50 mètres"],"correct_answer":"25 mètres","explanation":"À 90 km/h, on parcourt 25 mètres par seconde. Une distraction d'1 seconde revient à traverser une intersection les yeux fermés."},

    # ── DÉPASSEMENT AVANCÉ ────────────────────────────────────────

    {"category":"depassement","text":"Peut-on dépasser un véhicule s'arrêtant à un feu rouge ?","options":["Oui si on passe avant le feu","Non — le dépassement à l'approche des feux est interdit","Oui si la voie est libre","Oui si on klaxonne"],"correct_answer":"Non — le dépassement à l'approche des feux est interdit","explanation":"À l'approche d'un feu rouge, le dépassement est interdit car le véhicule devant peut s'arrêter brusquement."},
    {"category":"depassement","text":"Le dépassement d'un véhicule prioritaire en intervention est :","options":["Autorisé si on est pressé","Interdit — vous devez vous ranger et le laisser passer","Autorisé à vitesse réduite","Autorisé sur les routes à 4 voies"],"correct_answer":"Interdit — vous devez vous ranger et le laisser passer","explanation":"Les véhicules prioritaires en intervention ne peuvent jamais être dépassés — vous devez vous dégager pour les laisser passer."},
    {"category":"depassement","text":"Peut-on dépasser dans un tunnel ?","options":["Oui si le tunnel est éclairé","Non — le dépassement y est généralement interdit","Oui si les voies sont marquées","Oui si le tunnel est court"],"correct_answer":"Non — le dépassement y est généralement interdit","explanation":"Dans la plupart des tunnels, le dépassement est interdit en raison des risques d'éblouissement et de l'espace réduit."},
    {"category":"depassement","text":"Le créneau est une manœuvre qui consiste à :","options":["Faire demi-tour en 3 points","Se garer en marche arrière dans un espace entre deux véhicules","Rejoindre une file de circulation","Doubler sur une route à 2 voies"],"correct_answer":"Se garer en marche arrière dans un espace entre deux véhicules","explanation":"Le créneau est la manœuvre pour se garer en parallèle entre deux voitures garées. Elle nécessite observation et précision."},
    {"category":"depassement","text":"En côte, peut-on dépasser ?","options":["Oui si on voit bien la route","Non sur les 2/3 supérieurs d'une côte","Oui si on accélère fortement","Non jamais en côte"],"correct_answer":"Non sur les 2/3 supérieurs d'une côte","explanation":"Sur les 2/3 supérieurs d'une côte, la visibilité est insuffisante. Le dépassement y est interdit."},

    # ── SÉCURITÉ PASSIVE AVANCÉE ──────────────────────────────────

    {"category":"securite_passive","text":"Un airbag protège uniquement si :","options":["Il est activé en mode sport","La ceinture de sécurité est portée","La vitesse est inférieure à 80 km/h","Le siège est reculé au maximum"],"correct_answer":"La ceinture de sécurité est portée","explanation":"Un airbag sans ceinture peut être dangereux — le choc contre l'airbag non retenu par la ceinture peut être mortel."},
    {"category":"securite_passive","text":"Le système ABS (freinage antiblocage) permet :","options":["De freiner plus court dans tous les cas","De garder la direction pendant le freinage intense","D'augmenter la vitesse de pointe","D'éviter les crevaisons"],"correct_answer":"De garder la direction pendant le freinage intense","explanation":"L'ABS empêche le blocage des roues, permettant au conducteur de braquer pendant le freinage d'urgence. Il ne réduit pas forcément la distance d'arrêt."},
    {"category":"securite_passive","text":"Quand faut-il porter le gilet de sécurité fluorescent ?","options":["Uniquement la nuit","En cas d'immobilisation sur la chaussée ou son accotement","En permanence dans le véhicule","Uniquement sur autoroute"],"correct_answer":"En cas d'immobilisation sur la chaussée ou son accotement","explanation":"Le gilet fluorescent doit être enfilé avant de sortir du véhicule immobilisé, pour être visible des autres conducteurs."},
    {"category":"securite_passive","text":"La valeur légale de la profondeur minimale des rainures de pneus est :","options":["1 mm","1,6 mm","2 mm","3 mm"],"correct_answer":"1,6 mm","explanation":"En dessous de 1,6 mm de profondeur de rainure, les pneus sont légalement hors normes et doivent être remplacés."},
    {"category":"securite_passive","text":"Un conducteur doit signaler un freinage brusque aux véhicules derrière lui en :","options":["Klaxonnant","Freinant progressivement en plusieurs fois","Activant ses feux de détresse pendant le freinage","Baissant sa vitre"],"correct_answer":"Activant ses feux de détresse pendant le freinage","explanation":"En cas de freinage brutal (sur autoroute notamment), activer les feux de détresse prévient les conducteurs suivants."},

    # ── ALCOOL & DROGUES AVANCÉ ───────────────────────────────────

    {"category":"alcool_drogues","text":"L'alcool commence à affecter la conduite à partir de :","options":["0,5 g/L","0,3 g/L","0,2 g/L","Dès le premier verre"],"correct_answer":"Dès le premier verre","explanation":"Scientifiquement, même une petite quantité d'alcool affecte les réflexes et la perception. Le seuil légal de 0,5 g/L n'est pas un seuil de sécurité."},
    {"category":"alcool_drogues","text":"Combien de temps faut-il pour éliminer l'alcool d'un verre standard ?","options":["30 minutes","1 heure","2 heures","3 heures"],"correct_answer":"1 heure","explanation":"Le foie élimine environ 0,10 à 0,15 g/L d'alcool par heure. Un verre standard représente environ 0,25 g/L."},
    {"category":"alcool_drogues","text":"Le café, les boissons énergisantes ou la douche froide permettent-ils d'éliminer l'alcool ?","options":["Oui — le café accélère l'élimination","Non — seul le temps permet d'éliminer l'alcool","Oui — la douche froide accélère le métabolisme","Oui — les boissons énergisantes neutralisent l'alcool"],"correct_answer":"Non — seul le temps permet d'éliminer l'alcool","explanation":"Aucune méthode ne peut accélérer l'élimination de l'alcool. Seul le temps fonctionne."},

    # ── URGENCE AVANCÉE ────────────────────────────────────────────

    {"category":"urgence","text":"Un pneu éclate à grande vitesse. La bonne réaction est :","options":["Freiner brusquement","Tenir fermement le volant, ne pas freiner brusquement, ralentir progressivement","Braquer fortement dans le sens de la dérive","Couper le contact immédiatement"],"correct_answer":"Tenir fermement le volant, ne pas freiner brusquement, ralentir progressivement","explanation":"Un freinage brusque après un éclatement peut provoquer un dérapage. Tenir le volant fermement et ralentir en douceur."},
    {"category":"urgence","text":"En cas de somnolence au volant, la solution efficace est :","options":["Ouvrir la fenêtre et mettre de la musique forte","S'arrêter et dormir 15 à 20 minutes","Boire du café et continuer","Rouler plus vite pour arriver plus tôt"],"correct_answer":"S'arrêter et dormir 15 à 20 minutes","explanation":"Seul un sommeil court (15–20 min) restaure la vigilance. Les autres méthodes sont inefficaces à long terme."},
    {"category":"urgence","text":"Un véhicule derrière vous vous suit de trop près (conduite collante). Vous devez :","options":["Freiner brusquement pour l'avertir","Augmenter votre distance avec le véhicule devant et ralentir progressivement","Allumer vos feux de détresse","Klaxonner répétitivement"],"correct_answer":"Augmenter votre distance avec le véhicule devant et ralentir progressivement","explanation":"En augmentant la distance devant vous, vous donnez au conducteur derrière plus de marge en cas de freinage."},
    {"category":"urgence","text":"En cas de rupture de la direction assistée, vous devez :","options":["Pomper sur le frein","Continuer à conduire en appliquant plus de force sur le volant","Couper le moteur immédiatement","Sortir de la route rapidement"],"correct_answer":"Continuer à conduire en appliquant plus de force sur le volant","explanation":"La direction reste fonctionnelle sans assistance. Il faut simplement exercer une force plus importante sur le volant."},

    # ── PREMIERS SECOURS AVANCÉS ──────────────────────────────────

    {"category":"premiers_secours","text":"Une personne est inconsciente et ne respire pas. Que faites-vous en premier ?","options":["La mettre en PLS","Appeler les secours puis commencer le massage cardiaque","Lui faire du bouche-à-bouche immédiatement","Lui desserrer la ceinture"],"correct_answer":"Appeler les secours puis commencer le massage cardiaque","explanation":"En cas d'arrêt cardiaque : 1) Alerter (appel secours) 2) Massage cardiaque immédiat (30 compressions/2 insufflations)."},
    {"category":"premiers_secours","text":"Faut-il retirer le casque d'un motard blessé ?","options":["Oui — toujours pour libérer les voies respiratoires","Non — uniquement si la victime ne respire pas et que vous savez le faire","Oui — rapidement pour évaluer les blessures","Non — jamais, laissez aux secours"],"correct_answer":"Non — uniquement si la victime ne respire pas et que vous savez le faire","explanation":"Retirer un casque à tort peut aggraver des lésions cervicales. Ne retirez le casque que si la victime ne respire pas et que vous maîtrisez la technique."},
    {"category":"premiers_secours","text":"Une personne saigne abondamment. Que faites-vous ?","options":["Appliquer un garrot immédiatement","Comprimer la plaie avec un tissu propre directement sur la blessure","Nettoyer la plaie avec de l'eau","Surélever la tête"],"correct_answer":"Comprimer la plaie avec un tissu propre directement sur la blessure","explanation":"La compression directe est la première action pour stopper une hémorragie. Un garrot n'est envisageable qu'en dernier recours."},
    {"category":"premiers_secours","text":"Peut-on déplacer une victime d'accident ?","options":["Oui, toujours pour la mettre à l'abri","Non, sauf si elle est en danger immédiat (incendie, noyade)","Oui si elle est consciente","Non — ne jamais toucher une victime"],"correct_answer":"Non, sauf si elle est en danger immédiat (incendie, noyade)","explanation":"Déplacer une victime peut aggraver des fractures ou des lésions rachidiennes. Ne le faites que si rester en place représente un danger de mort immédiat."},

    # ── ENVIRONNEMENT ─────────────────────────────────────────────

    {"category":"premiers_secours","text":"La conduite éco-responsable consiste à :","options":["Rouler à pleine puissance pour réduire le temps de trajet","Anticiper les situations pour éviter les freinages et accélérations inutiles","Couper le moteur à tout arrêt, même bref","Gonfler moins les pneus pour plus d'adhérence"],"correct_answer":"Anticiper les situations pour éviter les freinages et accélérations inutiles","explanation":"L'anticipation est la base de l'éco-conduite : elle réduit la consommation de 15 à 25 % et diminue l'usure du véhicule."},
    {"category":"premiers_secours","text":"Un véhicule bien entretenu consomme combien de moins qu'un véhicule négligé ?","options":["5 à 10 %","15 à 25 %","30 à 40 %","Identique"],"correct_answer":"15 à 25 %","explanation":"Un entretien régulier (pneus, filtre à air, huile) peut réduire la consommation de carburant de 15 à 25 % et les émissions polluantes."},
]

# Validation
# Banque entraînement étendue — pas de limite fixe

# Banque complète pour l'entraînement
QUESTIONS_ALL = QUESTIONS_GN + QUESTIONS_TRAINING
# Total banque officielle + entraînement
