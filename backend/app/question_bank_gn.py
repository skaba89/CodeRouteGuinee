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

# ── EXTENSION 2 : 116 questions supplémentaires pour atteindre 200 total ──

QUESTIONS_TRAINING_2: list[dict] = [
  # SIGNALISATION (20)
  {"category":"signalisation","text":"Un panneau triangulaire rouge avec une locomotive signifie :","options":["Voie de chemin de fer à niveau","Passage de train interdit","Zone industrielle","Passage souterrain"],"correct_answer":"Voie de chemin de fer à niveau","explanation":"Ce panneau avertit d'un passage à niveau à proximité. Réduisez votre vitesse et soyez prêt à vous arrêter."},
  {"category":"signalisation","text":"Un panonceau 'Rappel' sous un panneau de vitesse signifie :","options":["La limite est confirmée","La limite se répète","Vitesse réduite de moitié","Zone de double limite"],"correct_answer":"La limite est confirmée","explanation":"Le panonceau 'Rappel' indique que la limitation déjà signalée plus tôt est toujours en vigueur."},
  {"category":"signalisation","text":"Un panneau bleu rectangulaire avec une flèche indique :","options":["Sens obligatoire","Route nationale","Direction conseillée","Voie réservée aux bus"],"correct_answer":"Sens obligatoire","explanation":"Les panneaux rectangulaires bleus à flèche indiquent une direction obligatoire pour tous les véhicules."},
  {"category":"signalisation","text":"La signification d'un panneau circulaire bleu avec des skis est :","options":["Piste de ski interdite","Voie réservée aux véhicules de montagne","Début d'une piste de ski","Station de ski à proximité"],"correct_answer":"Début d'une piste de ski","explanation":"Ce panneau bleu indique le début d'une piste de ski balisée. Interdit aux véhicules non équipés en montagne."},
  {"category":"signalisation","text":"Un panneau triangulaire avec des vagues signifie :","options":["Zone d'inondation possible","Traversée d'une rivière","Pont sur eau","Route glissante par temps de pluie"],"correct_answer":"Zone d'inondation possible","explanation":"Ce panneau avertit d'un risque d'inondation ou de submersion de la chaussée. Ralentissez et restez vigilant."},
  {"category":"signalisation","text":"Que signifie une ligne jaune continue le long du trottoir ?","options":["Stationnement gênant interdit","Zone de livraison","Arrêt de bus","Voie cyclable"],"correct_answer":"Stationnement gênant interdit","explanation":"La ligne jaune au sol indique une interdiction de stationnement (arrêt bref autorisé selon le contexte)."},
  {"category":"signalisation","text":"Un panneau 'Zone 30' indique :","options":["Vitesse maximale 30 km/h dans toute la zone","Vitesse conseillée 30 km/h","Limite valable 30 mètres","Rue à 30 m de longueur"],"correct_answer":"Vitesse maximale 30 km/h dans toute la zone","explanation":"En zone 30, la limitation s'applique à toutes les rues jusqu'au panneau de fin de zone."},
  {"category":"signalisation","text":"Les marquages au sol en chevrons (hachures) signifient :","options":["Voie réservée aux urgences","Zone où il est interdit de s'arrêter sauf urgence","Ralentisseurs peints","Voie de covoiturage"],"correct_answer":"Zone où il est interdit de s'arrêter sauf urgence","explanation":"Les chevrons au sol délimitent une zone que les véhicules ne doivent pas occuper, pour permettre les manœuvres d'urgence."},
  {"category":"signalisation","text":"Un panneau 'Impasse' signifie :","options":["Route à voie unique","La route n'a pas d'issue — faire demi-tour","Voie privée","Route en travaux fermée"],"correct_answer":"La route n'a pas d'issue — faire demi-tour","explanation":"L'impasse est une voie sans issue. N'y engagez-vous que si votre destination s'y trouve."},
  {"category":"signalisation","text":"Les clous ou pastilles réfléchissants au centre de la chaussée servent à :","options":["Délimiter les bandes de circulation la nuit","Mesurer la distance entre les voitures","Alerter les conducteurs somnolents","Décorer la route"],"correct_answer":"Délimiter les bandes de circulation la nuit","explanation":"Les pastilles rétro-réfléchissantes (catadioptres) restituent la lumière des phares pour guider les conducteurs de nuit."},
  {"category":"signalisation","text":"Un panneau rond avec un 'P' barré signifie :","options":["Stationnement interdit","Fin de stationnement payant","Parking complet","Parking réservé"],"correct_answer":"Stationnement interdit","explanation":"Le panneau P barré interdit tout stationnement à partir de cet emplacement. Différent de l'arrêt interdit (croix rouge)."},
  {"category":"signalisation","text":"Que signifie un feu orange fixe à un carrefour ?","options":["Dégagez l'intersection","Ralentissez, le feu va passer au rouge","Passez rapidement","Le feu est hors service"],"correct_answer":"Ralentissez, le feu va passer au rouge","explanation":"Le feu orange annonce le passage imminent au rouge. Vous devez vous préparer à vous arrêter, sauf si vous êtes trop proche pour freiner sans danger."},
  {"category":"signalisation","text":"Un panneau triangulaire avec un animal signifie :","options":["Zone d'élevage","Traversée d'animaux sauvages probable","Circulation d'animaux domestiques","Zone de chasse"],"correct_answer":"Traversée d'animaux sauvages probable","explanation":"Ce panneau signale une zone où des animaux sauvages (chèvres, vaches, singes) peuvent traverser la route. Réduisez votre vitesse."},
  {"category":"signalisation","text":"La signification de deux flèches opposées sur un panneau rond blanc est :","options":["Voie à double sens","Voie en impasse","Circulation alternée","Route nationale bidirectionnelle"],"correct_answer":"Circulation alternée","explanation":"Ce panneau indique une section où la circulation est alternée (route étroite, travaux), généralement gérée par des feux ou un agent."},
  {"category":"signalisation","text":"Un panneau 'Fin de chaussée revêtue' annonce :","options":["La route devient une piste","Fin de la route nationale","Zone de travaux imminents","Fin de l'autoroute"],"correct_answer":"La route devient une piste","explanation":"Ce panneau avertit que le revêtement bitumé se termine. Adaptez votre vitesse à la qualité de la piste."},
  {"category":"signalisation","text":"Un panneau triangulaire avec des zigzags représente :","options":["Route sinueuse dangereuse","Vitesse réduite obligatoire","Zone de brouillard","Piste de ski"],"correct_answer":"Route sinueuse dangereuse","explanation":"Les zigzags signalent une succession de virages dangereux. Réduisez votre vitesse et restez vigilant."},
  {"category":"signalisation","text":"La signification d'un panneau carré bleu avec un téléphone est :","options":["Poste d'appel d'urgence à proximité","Zone de couverture téléphonique","Téléphone interdit pendant la conduite","Poste de police"],"correct_answer":"Poste d'appel d'urgence à proximité","explanation":"Ce panneau indique la présence d'un poste téléphonique de secours pour appeler les services d'urgence en cas d'accident."},
  {"category":"signalisation","text":"Que signifie 'Rappel' sous un panneau de limitation de vitesse à 50 km/h ?","options":["Vous pouvez rouler à 100 km/h","La limite de 50 km/h s'applique toujours","Fin de la zone 50","Recommandation de vitesse"],"correct_answer":"La limite de 50 km/h s'applique toujours","explanation":"Le panonceau Rappel confirme que la limitation déjà indiquée est encore en vigueur, souvent après une intersection."},
  {"category":"signalisation","text":"Un panneau 'Passage protégé' (panneaux piétons verts) impose :","options":["De ralentir à 30 km/h","De s'arrêter absolument si des piétons traversent","De klaxonner pour prévenir","De changer de voie"],"correct_answer":"De s'arrêter absolument si des piétons traversent","explanation":"Les piétons engagés sur un passage protégé ont la priorité absolue. Vous devez vous arrêter même si votre feu est vert."},
  {"category":"signalisation","text":"Un panneau triangulaire avec un homme travaillant signifie :","options":["Zone d'emploi","Travaux sur la route","Aire de service","Zone industrielle"],"correct_answer":"Travaux sur la route","explanation":"Ce panneau avertit de la présence de travaux. Ralentissez, restez vigilant et respectez la signalisation temporaire orange."},

  # PRIORITÉS (15)
  {"category":"priorites","text":"Un convoi militaire en marche est-il prioritaire ?","options":["Non — aucune priorité spéciale","Oui — il ne faut jamais le couper","Seulement sur route nationale","Seulement si escorté par la police"],"correct_answer":"Oui — il ne faut jamais le couper","explanation":"Les convois militaires en formation doivent être respectés. Les couper peut être dangereux et constitue une infraction."},
  {"category":"priorites","text":"Sur une route à deux voies de sens opposés, que font deux véhicules larges se croisant ?","options":["Le plus rapide passe en premier","Celui qui monte sur la voie","Ils négocient en réduisant leur vitesse au maximum","Le plus léger se gare"],"correct_answer":"Ils négocient en réduisant leur vitesse au maximum","explanation":"Sur route étroite, quand deux véhicules larges se croisent, chacun réduit sa vitesse au minimum et passe en serrant à droite."},
  {"category":"priorites","text":"Un piéton aveugle avec une canne blanche traverse. Vous devez :","options":["Klaxonner pour l'alerter","Vous arrêter absolument et ne repartir que quand il est en sécurité","Ralentir et passer doucement","L'aider à traverser en sortant de votre véhicule"],"correct_answer":"Vous arrêter absolument et ne repartir que quand il est en sécurité","explanation":"Les piétons aveugles ont une priorité absolue. Arrêtez-vous complètement et attendez qu'ils aient traversé."},
  {"category":"priorites","text":"Vous êtes sur une route principale signalée. Un véhicule venant d'une voie secondaire tourne à gauche devant vous. Il doit :","options":["Passer rapidement","Attendre que vous soyez passé","Allumer ses clignotants d'abord","Klaxonner"],"correct_answer":"Attendre que vous soyez passé","explanation":"La route principale a toujours la priorité sur les voies secondaires. Le conducteur secondaire doit attendre que vous soyez passé."},
  {"category":"priorites","text":"Sur un rond-point, un piéton veut traverser l'entrée. Qui a la priorité ?","options":["Le conducteur qui entre","Le piéton s'il est engagé sur le passage","Le conducteur qui sort du rond-point","Dépend du pays"],"correct_answer":"Le piéton s'il est engagé sur le passage","explanation":"Un piéton engagé sur un passage protégé à l'entrée d'un giratoire a la priorité sur les véhicules entrant ou sortant."},
  {"category":"priorites","text":"Une voiture vient de votre gauche à une vitesse très élevée sur une route sans signalisation. Vous devez :","options":["Passer en premier car elle est à votre gauche","Freiner — même si vous avez la priorité, évitez l'accident","Klaxonner fort","Accélérer pour passer devant"],"correct_answer":"Freiner — même si vous avez la priorité, évitez l'accident","explanation":"La priorité légale ne protège pas en cas d'accident. La prudence prime toujours — mieux vaut céder que d'avoir un accident."},
  {"category":"priorites","text":"Un deux-roues motorisé vient de votre droite à une intersection sans signalisation. Vous devez :","options":["Passer en premier car vous êtes motorisé","Lui céder la priorité comme à tout véhicule venant de droite","Klaxonner","Accélérer"],"correct_answer":"Lui céder la priorité comme à tout véhicule venant de droite","explanation":"Un deux-roues est un véhicule à part entière. La règle de priorité à droite s'applique sans exception de puissance."},
  {"category":"priorites","text":"Qui a la priorité entre deux conducteurs arrivant simultanément à un croisement en T ?","options":["Celui sur la route principale","Le premier arrivé","Celui venant de la droite par rapport à l'autre","Aucune règle précise"],"correct_answer":"Celui sur la route principale","explanation":"Au croisement en T, la voie principale a la priorité sur la voie secondaire qui la rejoint."},
  {"category":"priorites","text":"En cas d'urgence médicale à bord, le conducteur peut-il s'affranchir des règles de priorité ?","options":["Oui, en klaxonnant continuellement","Non — aucune exception pour les particuliers","Oui si des témoins valident l'urgence","Oui avec les feux de détresse"],"correct_answer":"Non — aucune exception pour les particuliers","explanation":"Seuls les véhicules d'urgence officiels (ambulance, police) peuvent déroger aux règles de priorité. Appelez le 15 ou le 18."},
  {"category":"priorites","text":"Un enfant court soudainement sur la route. Vous devez :","options":["Klaxonner fort","Freiner en urgence même si cela cause un accident arrière","Virer brusquement","Accélérer pour passer avant lui"],"correct_answer":"Freiner en urgence même si cela cause un accident arrière","explanation":"La vie d'un piéton prime toujours. Freinez d'urgence — l'accident arrière sera moins grave qu'un enfant renversé."},
  {"category":"priorites","text":"Un troupeau de bœufs traverse la route (réalité courante en Guinée). Vous devez :","options":["Klaxonner pour les disperser","Vous arrêter et attendre qu'ils passent","Rouler lentement entre les animaux","Contourner par le bas-côté"],"correct_answer":"Vous arrêter et attendre qu'ils passent","explanation":"Les animaux sur la route représentent un danger grave. Arrêtez-vous, coupez vos phares si nécessaire, et attendez patiemment."},
  {"category":"priorites","text":"À un passage à niveau, les barrières commencent à se fermer. Vous devez :","options":["Accélérer pour passer avant","Vous arrêter immédiatement avant les barrières","Klaxonner et passer vite","Attendre que les barrières s'arrêtent"],"correct_answer":"Vous arrêter immédiatement avant les barrières","explanation":"Les barrières de passage à niveau sont un signal d'arrêt absolu. S'engager sous des barrières qui se ferment est mortel."},
  {"category":"priorites","text":"Un véhicule en stationnement ouvre sa portière devant vous. Qui est responsable ?","options":["Vous car vous roulez","Le conducteur garé qui doit vérifier avant d'ouvrir","Responsabilité partagée","Dépend de la vitesse"],"correct_answer":"Le conducteur garé qui doit vérifier avant d'ouvrir","explanation":"L'ouverture de portière sans vérification est une infraction. Le conducteur garé est responsable sauf si vous rouliez à vitesse excessive."},
  {"category":"priorites","text":"Sur un axe à 4 voies, les conducteurs dans la voie rapide ont-ils la priorité sur ceux dans la voie lente ?","options":["Oui toujours","Non — les règles de priorité s'appliquent normalement","Seulement pour les dépassements","Seulement sur autoroute"],"correct_answer":"Non — les règles de priorité s'appliquent normalement","explanation":"Le nombre de voies ne crée pas de priorité supplémentaire. Les règles normales (signalisation, droite) s'appliquent."},
  {"category":"priorites","text":"Un conducteur fait clignoter ses phares pour vous céder le passage. Devez-vous passer ?","options":["Oui, c'est un signal officiel de priorité","Non — ce n'est pas un signal officiel, vérifiez par vous-même","Oui si personne d'autre ne vient","Seulement si vous êtes à droite"],"correct_answer":"Non — ce n'est pas un signal officiel, vérifiez par vous-même","explanation":"Le clignotement de phares n'est pas réglementaire. Vérifiez vous-même que la voie est libre avant de vous engager."},

  # VITESSE (12)
  {"category":"vitesse","text":"La limitation de vitesse de nuit sur route nationale en Guinée est :","options":["Identique au jour : 90 km/h","Réduite à 70 km/h","Réduite à 80 km/h","Il n'y a pas de limitation spécifique de nuit"],"correct_answer":"Réduite à 80 km/h","explanation":"De nuit ou par visibilité réduite, il est recommandé de réduire sa vitesse même si la limite légale reste la même."},
  {"category":"vitesse","text":"En cas de brouillard dense (visibilité < 50 m), la vitesse est limitée à :","options":["50 km/h","30 km/h","La moitié de la limite normale","Aucune limite spécifique"],"correct_answer":"50 km/h","explanation":"Par brouillard dense, la limitation est de 50 km/h sur toutes les routes, quelle que soit la limitation habituelle."},
  {"category":"vitesse","text":"Un véhicule qui double la masse d'un autre a une énergie cinétique :","options":["Identique à vitesse égale","Double","Quadruple","La moitié"],"correct_answer":"Double","explanation":"L'énergie cinétique est proportionnelle à la masse (E = ½mv²). Doubler la masse double l'énergie à absorber lors d'un choc."},
  {"category":"vitesse","text":"Sur route mouillée, la vitesse conseillée est réduite de combien par rapport à la route sèche ?","options":["10 %","20 %","30 %","La même — seule la distance augmente"],"correct_answer":"20 %","explanation":"Sur chaussée mouillée, il est recommandé de réduire sa vitesse d'environ 20 % pour compenser la perte d'adhérence."},
  {"category":"vitesse","text":"Un conducteur roule à 50 km/h dans une zone 30. Il est en infraction de :","options":["10 km/h","20 km/h","30 km/h","Il n'est pas en infraction"],"correct_answer":"20 km/h","explanation":"La limite est 30 km/h. Le conducteur roule à 50 km/h, soit 20 km/h au-dessus de la limite — infraction caractérisée."},
  {"category":"vitesse","text":"La vitesse maximale en agglomération peut être abaissée à :","options":["20 km/h dans les zones à trafic partagé","Jamais en dessous de 30 km/h","40 km/h minimum","Seulement en cas de travaux"],"correct_answer":"20 km/h dans les zones à trafic partagé","explanation":"En aire piétonne ou zone de rencontre, la vitesse peut être réduite à 20 km/h ou moins pour la sécurité des piétons."},
  {"category":"vitesse","text":"Un poids lourd chargé a une distance de freinage :","options":["Identique à une voiture","Plus courte grâce à ses grands freins","Beaucoup plus longue","Légèrement plus longue"],"correct_answer":"Beaucoup plus longue","explanation":"L'énergie cinétique d'un camion chargé est considérablement plus grande. Sa distance de freinage peut être 2 à 3 fois celle d'une voiture."},
  {"category":"vitesse","text":"La vitesse tue principalement parce qu'elle :","options":["Réduit la visibilité","Augmente les distances de freinage et la violence des chocs","Provoque plus de pannes","Augmente la consommation"],"correct_answer":"Augmente les distances de freinage et la violence des chocs","explanation":"À vitesse double, la distance de freinage est × 4 et l'énergie d'impact × 4. Un choc à 70 km/h est 4 fois plus violent qu'à 35 km/h."},
  {"category":"vitesse","text":"En montagne sur route sinueuse, quelle vitesse adoptez-vous ?","options":["La vitesse limite du panneau sans tenir compte du virage","Une vitesse adaptée pour pouvoir s'arrêter dans votre champ de vision","La même qu'en plaine","50 km/h maximum toujours"],"correct_answer":"Une vitesse adaptée pour pouvoir s'arrêter dans votre champ de vision","explanation":"En montagne, les virages masquent la visibilité. Roulez à une vitesse permettant de vous arrêter dans la distance que vous voyez."},
  {"category":"vitesse","text":"Le radar mobile peut vous flasher quel que soit :","options":["L'heure et le jour","La direction et le sens","La météo","Toutes ces réponses"],"correct_answer":"Toutes ces réponses","explanation":"Les radars modernes fonctionnent dans tous les sens, de jour comme de nuit, par tous temps et toutes conditions."},
  {"category":"vitesse","text":"La vitesse excessive est impliquée dans combien d'accidents mortels ?","options":["10 %","25 %","35 %","50 %"],"correct_answer":"35 %","explanation":"La vitesse excessive ou inadaptée est impliquée dans environ 35 % des accidents mortels en Afrique subsaharienne."},
  {"category":"vitesse","text":"Quelle est la vitesse maximale autorisée pour un tracteur sur route nationale ?","options":["30 km/h","40 km/h","50 km/h","90 km/h"],"correct_answer":"40 km/h","explanation":"Les véhicules agricoles (tracteurs) ont une vitesse maximale de 40 km/h sur route nationale, représentant un danger pour les conducteurs qui ne les voient pas ralentir."},

  # DÉPASSEMENT (8)
  {"category":"depassement","text":"Vous dépassez et un véhicule vient en sens inverse. Que faites-vous ?","options":["Continuez à la même vitesse — l'autre s'adaptera","Accélérez pour terminer le dépassement le plus vite possible","Si vous ne pouvez terminer, serrez à droite progressivement derrière le véhicule dépassé","Freinez brusquement et revenez en file"],"correct_answer":"Accélérez pour terminer le dépassement le plus vite possible","explanation":"Si vous êtes déjà engagé dans un dépassement et qu'un véhicule arrive, il faut accélérer pour terminer le dépassement rapidement et libérer la voie."},
  {"category":"depassement","text":"Peut-on dépasser un car scolaire arrêté avec feux clignotants orange ?","options":["Oui si personne ne traverse","Non — arrêt obligatoire","Oui à vitesse réduite","Oui côté gauche"],"correct_answer":"Non — arrêt obligatoire","explanation":"Un car scolaire arrêté avec ses feux orange signifie que des enfants montent ou descendent. Arrêt absolu dans les deux sens."},
  {"category":"depassement","text":"Le dépassement à gauche d'un tramway est :","options":["Interdit","Autorisé si la voie est large","Obligatoire","Autorisé la nuit"],"correct_answer":"Autorisé si la voie est large","explanation":"On peut dépasser un tramway par la gauche si la chaussée est suffisamment large et si la visibilité le permet."},
  {"category":"depassement","text":"Après avoir doublé, vous devez vous rabattre quand :","options":["Après 50 mètres","Quand vous voyez les phares du véhicule doublé dans votre rétroviseur","Quand vous estimez avoir assez d'espace","Après le prochain virage"],"correct_answer":"Quand vous voyez les phares du véhicule doublé dans votre rétroviseur","explanation":"Vous pouvez vous rabattre en sécurité quand vous voyez entièrement le véhicule dépassé dans votre rétroviseur intérieur."},
  {"category":"depassement","text":"Peut-on dépasser un véhicule arrêté pour laisser traverser des piétons ?","options":["Oui si on klaxonne","Non — vous risquez de renverser les piétons","Oui si la voie opposée est libre","Oui à vitesse très lente"],"correct_answer":"Non — vous risquez de renverser les piétons","explanation":"Doubler un véhicule arrêté à un passage piéton est extrêmement dangereux. Les piétons continuent de traverser et ne vous voient pas arriver."},
  {"category":"depassement","text":"Un deux-roues peut-il dépasser entre les files de voitures ?","options":["Oui toujours","Non jamais","Oui si le trafic est à l'arrêt et à vitesse très réduite","Oui uniquement les motos de police"],"correct_answer":"Non jamais","explanation":"Le dépassement entre les files (remontée de files) est interdit en Guinée. C'est une manœuvre dangereuse pour les deux-roues et les conducteurs qui ouvrent leur portière."},
  {"category":"depassement","text":"À quelle distance d'un dos d'âne (ralentisseur) le dépassement est-il interdit ?","options":["5 mètres","50 mètres","100 mètres","Le dépassement y est toujours autorisé"],"correct_answer":"50 mètres","explanation":"Les ralentisseurs imposent un ralentissement qui rend le dépassement dangereux. On ne dépasse pas à moins de 50 mètres d'un dos d'âne."},
  {"category":"depassement","text":"Peut-on dépasser à l'approche d'un virage ?","options":["Oui si on voit bien","Non — la visibilité est insuffisante","Oui si la route est large","Oui avec les phares de route allumés"],"correct_answer":"Non — la visibilité est insuffisante","explanation":"À l'approche d'un virage, on ne peut pas évaluer la distance et la vitesse des véhicules en sens inverse. Le dépassement y est interdit."},

  # SÉCURITÉ PASSIVE (10)
  {"category":"securite_passive","text":"Le système ESP (contrôle de la trajectoire) intervient quand :","options":["Vous freinez trop fort","Le véhicule commence à déraper ou perdre sa trajectoire","Vous tournez à haute vitesse","Lors d'un choc frontal"],"correct_answer":"Le véhicule commence à déraper ou perdre sa trajectoire","explanation":"L'ESP agit automatiquement sur les freins de chaque roue individuellement pour maintenir la trajectoire souhaitée lors d'un dérapage."},
  {"category":"securite_passive","text":"La limite de charge d'un véhicule (PTAC) doit être respectée car :","options":["C'est une obligation légale uniquement","Une surcharge augmente les distances de freinage et dégrade la tenue de route","Elle protège les routes","Elle réduit la consommation"],"correct_answer":"Une surcharge augmente les distances de freinage et dégrade la tenue de route","explanation":"Dépasser le PTAC est dangereux (freinage, direction, tenue de route) et illégal. Les pneumatiques peuvent aussi éclater sous surcharge."},
  {"category":"securite_passive","text":"En cas de collision, quelle partie du véhicule absorbe l'énergie du choc ?","options":["Le toit","Les zones d'absorption (chocs avant et arrière conçus pour se déformer)","Le châssis rigide","Les portes"],"correct_answer":"Les zones d'absorption (chocs avant et arrière conçus pour se déformer)","explanation":"Les véhicules modernes ont des zones déformables à l'avant et à l'arrière qui absorbent l'énergie pour protéger l'habitacle rigide."},
  {"category":"securite_passive","text":"Un appuie-tête correctement réglé doit être :", "options":["À hauteur des épaules","À hauteur du bas du crâne","À hauteur du milieu de la tête ou plus haut","Incliné vers l'arrière"],"correct_answer":"À hauteur du milieu de la tête ou plus haut","explanation":"Un appuie-tête bien réglé protège contre le coup du lapin (whiplash). Trop bas, il aggrave la blessure cervicale en cas de choc arrière."},
  {"category":"securite_passive","text":"Les rétroviseurs doivent être réglés pour :","options":["Voir toute la carrosserie de votre voiture","Minimiser les angles morts et voir le plus loin possible derrière","Voir le sol derrière","Voir uniquement la voie sur laquelle vous roulez"],"correct_answer":"Minimiser les angles morts et voir le plus loin possible derrière","explanation":"Les rétroviseurs doivent montrer un minimum de votre propre véhicule. Plus vous voyez derrière, moins vous avez d'angle mort."},
  {"category":"securite_passive","text":"Un dispositif de retenue enfant (siège auto) doit être :","options":["Homologué et adapté au poids de l'enfant","Acheté récemment","De couleur voyante","Fixé avec la ceinture de sécurité uniquement"],"correct_answer":"Homologué et adapté au poids de l'enfant","explanation":"Un siège trop grand ou trop petit pour l'enfant ne le protège pas correctement. La certification homologuée garantit les tests de sécurité."},
  {"category":"securite_passive","text":"Les phares antibrouillard arrière s'utilisent :","options":["Dès la nuit tombée","Uniquement par brouillard dense ou fortes chutes de neige","Toujours avec les phares de route","Par pluie normale"],"correct_answer":"Uniquement par brouillard dense ou fortes chutes de neige","explanation":"Les antibrouillard arrière éblouissent les autres conducteurs. Leur usage est réservé aux visibilités inférieures à 50 mètres."},
  {"category":"securite_passive","text":"Le témoin de pression des pneus s'allume. Vous devez :","options":["Rouler lentement jusqu'au garage","Vérifier la pression à la prochaine occasion","Gonfler immédiatement ou faire vérifier les pneus","Ignorer si le volant ne vibre pas"],"correct_answer":"Gonfler immédiatement ou faire vérifier les pneus","explanation":"Un pneu dégonflé affecte la tenue de route, augmente la consommation et peut provoquer un éclatement. Agissez dès que possible."},
  {"category":"securite_passive","text":"La ceinture de sécurité doit passer :","options":["Sur l'épaule et en travers du ventre","Sur la clavicule (pas sur le cou) et sur le bas-ventre/bassin","Sous l'aisselle pour plus de confort","Sur le ventre uniquement pour les femmes enceintes"],"correct_answer":"Sur la clavicule (pas sur le cou) et sur le bas-ventre/bassin","explanation":"La ceinture passe sur l'os de la clavicule (partie haute) et sur le bassin (partie basse). La passer sous le bras la rend inefficace et dangereuse."},
  {"category":"securite_passive","text":"Avant de démarrer, vous devez vérifier :","options":["Uniquement le niveau d'essence","Que les rétroviseurs sont réglés et que la voie est dégagée","Le niveau d'huile chaque matin","Seulement la pression des pneus chaque semaine"],"correct_answer":"Que les rétroviseurs sont réglés et que la voie est dégagée","explanation":"Avant tout départ, ajustez siège et rétroviseurs, bouclez la ceinture, et assurez-vous que la voie est libre avant d'engager la marche arrière."},

  # ALCOOL & DROGUES (5)
  {"category":"alcool_drogues","text":"La conduite après usage de médicaments somnifères est :","options":["Autorisée en dessous de 0,5 g/L d'alcool","Interdite si le médicament altère les facultés","Autorisée le matin car l'effet diminue","Sans danger si on conduit depuis 2 ans ou plus"],"correct_answer":"Interdite si le médicament altère les facultés","explanation":"De nombreux médicaments (antihistaminiques, somnifères, anxiolytiques) altèrent la conduite. Le symbole voiture sur la boîte avertit des risques."},
  {"category":"alcool_drogues","text":"Un jeune conducteur (moins de 2 ans de permis) a un taux légal d'alcoolémie de :","options":["0,5 g/L comme tout le monde","0,3 g/L","0,2 g/L","0,0 g/L — tolérance zéro"],"correct_answer":"0,2 g/L","explanation":"Les jeunes conducteurs (moins de 2 ans de permis) ont un taux légal abaissé à 0,2 g/L dans de nombreux pays, car leur expérience est moindre."},
  {"category":"alcool_drogues","text":"La drogue la plus souvent impliquée dans les accidents en Afrique de l'Ouest est :","options":["La cocaïne","Le cannabis","L'héroïne","Les amphétamines"],"correct_answer":"Le cannabis","explanation":"Le cannabis est la drogue illicite la plus consommée et la plus impliquée dans les accidents en Afrique. Il réduit les réflexes et déforme la perception du temps."},
  {"category":"alcool_drogues","text":"Peut-on conduire après une nuit de fête sans avoir bu d'alcool mais sans dormi ?","options":["Oui si on est sobre","Non — le manque de sommeil altère les réflexes autant que l'alcool","Oui si on prend un café","Non uniquement si on a moins de 20 ans"],"correct_answer":"Non — le manque de sommeil altère les réflexes autant que l'alcool","explanation":"24 heures sans sommeil produisent une altération des réflexes équivalente à 1 g/L d'alcool dans le sang."},
  {"category":"alcool_drogues","text":"Un conducteur pris en état d'ivresse en Guinée risque :","options":["Une simple amende","Suspension du permis, amende, et emprisonnement possible","Uniquement l'immobilisation du véhicule","Un avertissement pour la première fois"],"correct_answer":"Suspension du permis, amende, et emprisonnement possible","explanation":"La conduite en état d'ivresse est un délit pénal en Guinée passible de suspension de permis, d'amende et pouvant conduire à l'emprisonnement."},

  # URGENCE (8)
  {"category":"urgence","text":"Votre accélérateur reste bloqué. Vous devez :","options":["Couper le contact immédiatement","Freiner progressivement, passer au point mort, chercher un espace dégagé pour vous arrêter","Klaxonner et allumer les feux de détresse","Appuyer fort sur les freins tout de suite"],"correct_answer":"Freiner progressivement, passer au point mort, chercher un espace dégagé pour vous arrêter","explanation":"Accélérateur coincé : freinage progressif, passage au neutre, puis arrêt dans un espace sûr. Couper le contact peut bloquer la direction assistée."},
  {"category":"urgence","text":"Vos phares tombent en panne de nuit sur route isolée. Vous devez :","options":["Continuer lentement avec les feux de détresse","Vous arrêter immédiatement en dehors de la chaussée et baliser","Allumer les feux antibrouillard à la place","Klaxonner continuellement"],"correct_answer":"Vous arrêter immédiatement en dehors de la chaussée et baliser","explanation":"Sans phares de nuit, poursuivre la route est extrêmement dangereux. Arrêtez-vous en sécurité, balisez, et attendez les secours ou le jour."},
  {"category":"urgence","text":"Un enfant court sur la route pour récupérer un ballon. Vous devez :","options":["Klaxonner fort pour l'effrayer et le faire reculer","Freiner d'urgence quelle que soit la vitesse","Virer sur la droite sans freiner","Accélérer pour passer avant lui"],"correct_answer":"Freiner d'urgence quelle que soit la vitesse","explanation":"Devant un enfant sur la chaussée, le freinage d'urgence maximum est la seule réponse. Les risques de collision arrière sont secondaires."},
  {"category":"urgence","text":"Un chien surgit devant vous sur route nationale. Vous devez :","options":["Freiner d'urgence et braquer","Freiner progressivement sans virer brusquement","Écraser l'animal pour éviter de mettre des vies humaines en danger","Klaxonner et accélérer"],"correct_answer":"Freiner progressivement sans virer brusquement","explanation":"Écraser un animal est préférable à un accident grave. Un écart brusque peut provoquer un tonneau ou une collision frontale."},
  {"category":"urgence","text":"Votre voiture prend de l'eau sur une route inondée. Quand devez-vous sortir ?","options":["Immédiatement dès que l'eau arrive dans l'habitacle","Quand l'eau dépasse les fenêtres","Jamais — restez dans le véhicule","Quand le moteur cale"],"correct_answer":"Immédiatement dès que l'eau arrive dans l'habitacle","explanation":"Sortez dès que possible pendant que les portes s'ouvrent encore. Quand la pression de l'eau est trop forte, les portes ne s'ouvrent plus."},
  {"category":"urgence","text":"Vous traversez une route inondée. Si le moteur cale au milieu, vous devez :","options":["Essayer de redémarrer","Sortir immédiatement par les fenêtres si les portes ne s'ouvrent plus","Rester dans le véhicule et appeler les secours","Pousser le véhicule"],"correct_answer":"Sortir immédiatement par les fenêtres si les portes ne s'ouvrent plus","explanation":"En cas de cale dans une inondation, sortez immédiatement. Si les portes sont bloquées par la pression, brisez une vitre ou sortez par une fenêtre ouverte."},
  {"category":"urgence","text":"Un feu de voiture se déclare. Vous avez un extincteur. Où l'utilisez-vous ?","options":["Sur les flammes visibles en ouvrant grand le capot","À la base des flammes, en maintenant le capot légèrement entrouvert","Sur tout le moteur depuis l'habitacle","Uniquement sur les flammes des roues"],"correct_answer":"À la base des flammes, en maintenant le capot légèrement entrouvert","explanation":"Ouvrir grand le capot attise les flammes. Dirigez l'extincteur à la base du feu par l'espace du capot entrouvert — c'est là que le feu prend."},
  {"category":"urgence","text":"Votre direction bloque soudainement à haute vitesse. Votre première action est :","options":["Couper le moteur","Ne pas paniquer, freiner progressivement tout en essayant de maintenir la trajectoire","Braquer fortement dans le sens souhaité","Tirer le frein à main"],"correct_answer":"Ne pas paniquer, freiner progressivement tout en essayant de maintenir la trajectoire","explanation":"Une direction bloquée ne signifie pas perte totale de contrôle. Freinez progressivement pour ralentir et maîtrisez l'arrêt sans mouvements brusques."},

  # PREMIERS SECOURS (6)
  {"category":"premiers_secours","text":"Un blessé est coincé dans un véhicule en feu. Vous devez :","options":["Attendre les secours sans intervenir","Le dégager immédiatement malgré le risque de lésions rachidiennes","Éteindre d'abord le feu avec l'extincteur","Appeler les secours uniquement"],"correct_answer":"Le dégager immédiatement malgré le risque de lésions rachidiennes","explanation":"Le feu représente un danger immédiat de mort. Dans ce cas extrême, dégager la victime prime sur le risque de lésions rachidiennes."},
  {"category":"premiers_secours","text":"Une personne est choquée après un accident mais consciente. Vous devez :","options":["Lui donner de l'eau sucrée","La garder au chaud, la rassurer, et appeler les secours","La faire marcher pour la réveiller","Lui donner un médicament analgésique"],"correct_answer":"La garder au chaud, la rassurer, et appeler les secours","explanation":"Le choc traumatique peut aggraver l'état d'une victime. Gardez-la allongée, au chaud, réconfortée, et attendez les secours."},
  {"category":"premiers_secours","text":"Un enfant avale un objet et s'étouffe. Vous devez :","options":["Lui donner à boire","Pencher sa tête en avant et frapper fort dans le dos (manœuvre de Heimlich adaptée enfant)","Le mettre la tête en bas","Appeler les secours uniquement et attendre"],"correct_answer":"Pencher sa tête en avant et frapper fort dans le dos (manœuvre de Heimlich adaptée enfant)","explanation":"Pour un enfant qui s'étouffe : 5 frappes dans le dos avec la tête penchée en avant. Si ça ne suffit pas, la manœuvre de Heimlich abdominale pour enfants de plus de 1 an."},
  {"category":"premiers_secours","text":"Combien de compressions cardiaques faites-vous avant 2 insufflations ?","options":["10","15","30","50"],"correct_answer":"30","explanation":"Le protocole RCP actuel est 30 compressions pour 2 insufflations (30:2), à un rythme de 100 à 120 compressions par minute."},
  {"category":"premiers_secours","text":"Une victime a une fracture apparente du membre. Vous devez :","options":["Remettre l'os en place","Immobiliser le membre sans le déplacer et appeler les secours","Appliquer de la glace directement","Faire marcher la victime pour évaluer la gravité"],"correct_answer":"Immobiliser le membre sans le déplacer et appeler les secours","explanation":"Ne jamais tenter de remettre un os en place. Immobilisez le membre dans la position trouvée, protégez-le et attendez les secours."},
  {"category":"premiers_secours","text":"En Guinée, le numéro d'urgence pour appeler le SAMU ou la police est :","options":["15","17 ou 18","117 ou 122 selon les villes","101"],"correct_answer":"117 ou 122 selon les villes","explanation":"En Guinée, les numéros d'urgence varient. Le 117 est la gendarmerie nationale, le 122 est la protection civile. Apprenez les numéros de votre préfecture."},

  # RÉGLEMENTATION SPÉCIFIQUE GUINÉE (12)
  {"category":"signalisation","text":"En Guinée, la visite technique du véhicule est obligatoire :","options":["Tous les 5 ans","Tous les 2 ans pour les véhicules de moins de 5 ans, tous les ans au-delà","Tous les ans pour tous les véhicules","Uniquement pour les poids lourds"],"correct_answer":"Tous les 2 ans pour les véhicules de moins de 5 ans, tous les ans au-delà","explanation":"La visite technique est obligatoire et doit être affichée sur le pare-brise. Un véhicule sans visite technique valide est en infraction."},
  {"category":"signalisation","text":"Le port du casque est obligatoire pour les conducteurs et passagers de :","options":["Motos uniquement","Motos et cyclomoteurs","Tous les deux-roues y compris vélos","Motos de plus de 125 cc"],"correct_answer":"Motos et cyclomoteurs","explanation":"En Guinée comme dans la plupart des pays CEDEAO, le casque est obligatoire pour tous les conducteurs et passagers de motos et cyclomoteurs."},
  {"category":"vitesse","text":"La limitation de vitesse dans les agglomérations de Guinée est :","options":["40 km/h","50 km/h","60 km/h","Variable selon les panneaux uniquement"],"correct_answer":"50 km/h","explanation":"La limitation légale en agglomération est 50 km/h en Guinée, conforme aux normes CEDEAO."},
  {"category":"vitesse","text":"Hors agglomération sur route nationale, la limitation est :","options":["80 km/h","90 km/h","100 km/h","120 km/h"],"correct_answer":"90 km/h","explanation":"La limitation hors agglomération sur route nationale est de 90 km/h en Guinée."},
  {"category":"signalisation","text":"L'assurance responsabilité civile est :","options":["Facultative","Obligatoire pour tous les véhicules motorisés","Obligatoire seulement pour les véhicules de plus de 5 ans","Obligatoire uniquement pour les taxis"],"correct_answer":"Obligatoire pour tous les véhicules motorisés","explanation":"L'assurance RC est obligatoire pour tout véhicule motorisé circulant sur la voie publique en Guinée. Circuler sans assurance est un délit."},
  {"category":"securite_passive","text":"En Guinée, les conducteurs de moto-taxis doivent :","options":["Être immatriculés et assurés uniquement","Avoir un permis A, être immatriculés, assurés et fournir un casque au passager","Avoir uniquement la vignette","Avoir le permis B suffit"],"correct_answer":"Avoir un permis A, être immatriculés, assurés et fournir un casque au passager","explanation":"Les moto-taxis (Gbaka) sont réglementés. Le conducteur doit avoir un permis A, une immatriculation, une assurance, et un casque pour le passager."},
  {"category":"alcool_drogues","text":"Le contrôle d'alcoolémie par la gendarmerie guinéenne peut se faire :","options":["Uniquement après un accident","À tout moment sur la voie publique","Uniquement la nuit","Uniquement sur autoroute"],"correct_answer":"À tout moment sur la voie publique","explanation":"Les forces de l'ordre peuvent contrôler l'alcoolémie à tout moment, en particulier lors de contrôles routiers ou après un accident."},
  {"category":"signalisation","text":"La vignette fiscale (taxe de circulation) doit être :","options":["Conservée chez vous","Apposée visiblement sur le pare-brise","Dans la boîte à gants","Présentée uniquement sur demande"],"correct_answer":"Apposée visiblement sur le pare-brise","explanation":"La vignette de taxe de circulation doit être visible sur le pare-brise du véhicule. L'absence expose à une amende."},
  {"category":"priorites","text":"En Guinée, les gendarmes et policiers réglant la circulation ont :","options":["Autorité égale à la signalisation","Autorité supérieure à la signalisation — leurs gestes priment","Autorité inférieure aux feux de signalisation","Autorité uniquement hors agglomération"],"correct_answer":"Autorité supérieure à la signalisation — leurs gestes priment","explanation":"Un agent de la force publique réglant la circulation est prioritaire sur toute signalisation, y compris les feux. Obéissez toujours à leurs gestes."},
  {"category":"securite_passive","text":"Transporter des passagers dans la benne d'un pick-up est :","options":["Autorisé sans restriction","Autorisé uniquement pour les trajets courts","Interdit — les passagers doivent être dans l'habitacle fermé","Autorisé uniquement pour les adultes"],"correct_answer":"Interdit — les passagers doivent être dans l'habitacle fermé","explanation":"Transporter des personnes dans la benne d'un pick-up est interdit et extrêmement dangereux en cas de freinage ou d'accident."},
  {"category":"urgence","text":"En Guinée, que faire après un accident matériel sans blessés ?","options":["Partir sans vous arrêter","Remplir un constat amiable avec l'autre conducteur","Appeler la police obligatoirement","Appeler votre assurance et partir"],"correct_answer":"Remplir un constat amiable avec l'autre conducteur","explanation":"En cas d'accident matériel, les conducteurs doivent remplir un constat amiable. La police n'est obligatoire qu'en cas de désaccord ou de blessés."},
  {"category":"signalisation","text":"Le numéro de la plaque d'immatriculation en Guinée comprend :","options":["Des lettres et chiffres sans région","Le code de la préfecture + numéro séquentiel","Uniquement des chiffres","Le code CEDEAO du pays uniquement"],"correct_answer":"Le code de la préfecture + numéro séquentiel","explanation":"Les plaques guinéennes comprennent les initiales de la préfecture d'immatriculation suivies d'un numéro séquentiel."},
]

# Banque étendue complète
QUESTIONS_TRAINING_FULL = QUESTIONS_TRAINING + QUESTIONS_TRAINING_2

# Total : 40 officielles + 44 + 116 = 200 questions
QUESTIONS_200 = QUESTIONS_GN + QUESTIONS_TRAINING_FULL

# ── COMPLÉMENT POUR 200 QUESTIONS ──
QUESTIONS_TRAINING_3: list[dict] = [
  {"category":"signalisation","text":"Un triangle rouge avec un camion penché signifie :","options":["Camions interdits","Route glissante pour les camions","Risque de chute de pierres","Déclivité dangereuse"],"correct_answer":"Déclivité dangereuse","explanation":"Ce panneau avertit d'une pente raide qui peut provoquer des problèmes de freinage, surtout pour les camions chargés."},
  {"category":"signalisation","text":"Un panneau 'Fin de voie réservée aux bus' signifie :","options":["Les bus doivent s'arrêter","Tous les véhicules peuvent à nouveau utiliser cette voie","Début d'une zone piétonne","Voie rapide commence"],"correct_answer":"Tous les véhicules peuvent à nouveau utiliser cette voie","explanation":"La fin de la voie réservée aux transports en commun signifie que la voie redevient accessible à tous les véhicules."},
  {"category":"vitesse","text":"Sur une route à chaussées séparées (type 2×2 voies) en Guinée, la vitesse maximum est :","options":["90 km/h","100 km/h","110 km/h","120 km/h"],"correct_answer":"100 km/h","explanation":"Sur les routes à chaussées séparées par un terre-plein central, la limitation est généralement portée à 100 km/h en Guinée."},
  {"category":"priorites","text":"Un agent de la croix rouge dirige la circulation sur un accident. Ses gestes :","options":["Ont force de loi","N'ont aucune valeur légale — suivez la signalisation","Valent seulement comme conseil","Sont obligatoires uniquement pour les véhicules impliqués"],"correct_answer":"N'ont aucune valeur légale — suivez la signalisation","explanation":"Seuls les agents des forces de l'ordre (police, gendarmerie) ont autorité pour diriger la circulation. Les bénévoles et premiers arrivants n'ont pas ce pouvoir légal."},
  {"category":"securite_passive","text":"La durée de vie d'un siège enfant après un accident, même léger, est :","options":["Illimitée si aucun dommage visible","Il doit être remplacé même après un accident mineur","5 ans supplémentaires","Jusqu'à la prochaine inspection"],"correct_answer":"Il doit être remplacé même après un accident mineur","explanation":"Un siège auto peut subir des déformations invisibles lors d'un choc. Par sécurité, il doit être remplacé après tout accident."},
  {"category":"urgence","text":"La règle d'or après un choc arrière est :","options":["Rester dans son véhicule et appeler la police","Sortir immédiatement — un deuxième choc peut survenir","Évaluer les dégâts avant d'appeler","Partir si pas de blessés"],"correct_answer":"Sortir immédiatement — un deuxième choc peut survenir","explanation":"Après un choc sur autoroute ou route rapide, quittez rapidement le véhicule et mettez-vous en sécurité. Un second choc est fréquent."},
  {"category":"premiers_secours","text":"Combien de minutes sans oxygène avant des lésions cérébrales irréversibles ?","options":["2 minutes","4–6 minutes","10 minutes","15 minutes"],"correct_answer":"4–6 minutes","explanation":"Le cerveau commence à souffrir après 4 à 6 minutes sans oxygène. C'est pourquoi la RCP doit commencer immédiatement en cas d'arrêt cardiaque."},
  {"category":"alcool_drogues","text":"Le tabac au volant est :","options":["Interdit","Autorisé mais déconseillé","Interdit si des enfants sont dans le véhicule en Guinée","Sans réglementation spécifique"],"correct_answer":"Autorisé mais déconseillé","explanation":"Le tabac n'est pas interdit au volant, mais fumer distrait le conducteur (allumer la cigarette, cendres, fumée dans les yeux)."},
  {"category":"depassement","text":"Le dépassement d'une ambulance arrêtée avec feux allumés est :","options":["Interdit si des soins sont prodigués","Toujours autorisé","Interdit uniquement si une voie est occupée","Autorisé à vitesse réduite"],"correct_answer":"Interdit si des soins sont prodigués","explanation":"Si une ambulance est arrêtée et que des soins sont en cours, il ne faut pas perturber l'intervention. Ralentissez et contournez prudemment."},
  {"category":"priorites","text":"À un croisement sans signalisation entre une route en terre et une route bitumée, qui est prioritaire ?","options":["La route bitumée systématiquement","La règle de priorité à droite s'applique, sans distinction","Le véhicule le plus lourd","Le plus rapide"],"correct_answer":"La règle de priorité à droite s'applique, sans distinction","explanation":"La priorité à droite s'applique quelle que soit la qualité du revêtement. Seule la signalisation peut créer une différence de priorité."},
  {"category":"signalisation","text":"En Guinée, les dos d'âne (ralentisseurs) doivent être signalés par :","options":["Un panneau triangulaire avec bosses et une bande jaune au sol","Uniquement peints en jaune","Pas de signalisation obligatoire","Seulement par des panneaux"],"correct_answer":"Un panneau triangulaire avec bosses et une bande jaune au sol","explanation":"Les ralentisseurs réglementaires doivent être précédés d'un panneau d'avertissement et marqués au sol en jaune."},
  {"category":"vitesse","text":"La signification de '30' sur une route guinéenne sans panneau rond rouge autour est :","options":["Vitesse conseillée","Numéro de la route","Vitesse maximale obligatoire","Distance en mètres"],"correct_answer":"Vitesse conseillée","explanation":"Un chiffre seul sur la chaussée sans panneau circulaire rouge est une vitesse conseillée, pas une limitation légale."},
  {"category":"urgence","text":"Votre volant vibre fortement à haute vitesse. Cela signifie probablement :","options":["Moteur en surchauffe","Pneu déséquilibré ou roue voilée — ralentissez et consultez un garage","Direction assistée défaillante","Freins usés"],"correct_answer":"Pneu déséquilibré ou roue voilée — ralentissez et consultez un garage","explanation":"Les vibrations du volant à grande vitesse indiquent souvent un déséquilibrage de roue ou une déformation du pneu. Dangereuses à haute vitesse."},
  {"category":"premiers_secours","text":"Une victime a une brûlure grave. Vous devez :","options":["Appliquer du beurre ou de l'huile","Percer les cloques","Refroidir avec de l'eau froide courante pendant 10–15 min puis couvrir proprement","Appliquer de la glace directement"],"correct_answer":"Refroidir avec de l'eau froide courante pendant 10–15 min puis couvrir proprement","explanation":"L'eau froide courante stoppe la progression de la brûlure. Jamais de glace (aggrave), ni de corps gras (infesté de microbes)."},
  {"category":"priorites","text":"Une file de véhicules s'est formée pour permettre le passage d'un convoi présidentiel. Vous devez :","options":["Continuer votre route","Vous arrêter et attendre que le convoi soit passé","Vous insérer dans le convoi","Faire demi-tour"],"correct_answer":"Vous arrêter et attendre que le convoi soit passé","explanation":"Les convois officiels avec escorte de sécurité sont prioritaires. Restez à l'arrêt jusqu'à ce qu'ils soient entièrement passés."},
  {"category":"securite_passive","text":"En Guinée, les conducteurs de taxi moto doivent disposer :","options":["Uniquement d'un vêtement fluorescent","D'un casque homologué pour eux et pour le passager","D'un brassard de couleur uniquement","D'une carte professionnelle"],"correct_answer":"D'un casque homologué pour eux et pour le passager","explanation":"Les conducteurs de moto-taxi (Jakarta) doivent impérativement disposer d'un casque homologué pour eux et pour chaque passager transporté."},
  {"category":"signalisation","text":"Un panneau blanc rectangulaire avec le nom d'une ville en noir indique :","options":["Le début de l'agglomération","La fin de l'agglomération","Un point de repos","Un péage"],"correct_answer":"Le début de l'agglomération","explanation":"Le panneau blanc avec le nom de la localité en noir marque l'entrée dans l'agglomération. La limitation de 50 km/h s'applique dès ce point."},
  {"category":"signalisation","text":"Un panneau identique mais barré d'un trait oblique indique :","options":["Début de la localité","Fin de l'agglomération","Zone interdite","Bifurcation"],"correct_answer":"Fin de l'agglomération","explanation":"Le même panneau avec une barre oblique marque la sortie de l'agglomération. La limitation repasse à 90 km/h hors agglomération."},
  {"category":"vitesse","text":"La distance de sécurité en mètres à 90 km/h est d'au moins :","options":["25 mètres","50 mètres","75 mètres","100 mètres"],"correct_answer":"50 mètres","explanation":"À 90 km/h, la règle des 2 secondes correspond à environ 50 mètres. Cette distance est le minimum — davantage par mauvais temps."},
  {"category":"alcool_drogues","text":"L'alcool est éliminé par le corps humain à raison de :","options":["0,05 g/L par heure","0,10–0,15 g/L par heure","0,20 g/L par heure","0,30 g/L par heure"],"correct_answer":"0,10–0,15 g/L par heure","explanation":"Le foie élimine l'alcool à un rythme fixe d'environ 0,10 à 0,15 gramme par litre de sang par heure, selon les individus."},
]

# Mise à jour de la banque complète 200Q
QUESTIONS_TRAINING_FULL = QUESTIONS_TRAINING + QUESTIONS_TRAINING_2 + QUESTIONS_TRAINING_3
QUESTIONS_200 = QUESTIONS_GN + QUESTIONS_TRAINING_FULL
