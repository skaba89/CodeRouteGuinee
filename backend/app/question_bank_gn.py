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
