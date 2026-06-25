/**
 * Questions de démonstration — CodeRoute Guinée Catégorie B
 *
 * Ces 40 questions illustrées servent à la démonstration frontend (mode présentation).
 *
 * En conditions réelles :
 *   - La banque officielle contient 200 questions stockées en PostgreSQL
 *   - L'exam_engine tire 40 questions selon la répartition officielle DNTT :
 *       signalisation: 10, priorités: 6, vitesse: 5, dépassement: 5,
 *       sécurité_passive: 4, urgence: 4, alcool_drogues: 3, premiers_secours: 3
 *   - Chaque examen est unique grâce au pool de 200 (5e combinaisons possibles)
 *   - Les questions sélectionnées sont tracées par hash SHA-256 pour l'audit
 */

export interface ExamQuestionData {
  id: string;
  number: number;
  category: string;
  text: string;
  options: string[];
  correct_answer: string;
  media_type?: 'image' | 'video' | 'svg' | null;
  media_url?: string | null;
  media_alt?: string | null;
  explanation?: string;
}

export const DEMO_QUESTIONS: ExamQuestionData[] = [
  {
    id: 'q01', number: 1, category: 'Signalisation',
    text: 'Quel est ce panneau et que vous impose-t-il ?',
    options: ['Ralentir et passer prudemment', "S'arrêter complètement, céder le passage", 'Klaxonner pour signaler votre présence', 'Accélérer pour dégager l\'intersection'],
    correct_answer: "S'arrêter complètement, céder le passage",
    media_type: 'svg', media_url: 'stop', media_alt: 'Panneau STOP rouge octogonal',
    explanation: 'Le STOP impose un arrêt complet (roues immobiles) puis une cession de priorité.',
  },
  {
    id: 'q02', number: 2, category: 'Signalisation',
    text: 'Ce panneau est installé avant votre voie. Que signifie-t-il ?',
    options: ['Vous avez la priorité', 'Vous devez céder le passage aux véhicules sur la route principale', 'Danger de virage à droite', 'Fin de zone de travaux'],
    correct_answer: 'Vous devez céder le passage aux véhicules sur la route principale',
    media_type: 'svg', media_url: 'give_way', media_alt: 'Panneau cédez le passage — triangle inversé rouge et blanc',
    explanation: 'Le triangle inversé signifie cédez le passage. Laissez passer les véhicules de la voie principale.',
  },
  {
    id: 'q03', number: 3, category: 'Signalisation',
    text: 'Quelle est la vitesse maximale que vous pouvez atteindre ici ?',
    options: ['30 km/h', '50 km/h', '60 km/h', '70 km/h'],
    correct_answer: '50 km/h',
    media_type: 'svg', media_url: 'speed_50', media_alt: 'Panneau de limitation de vitesse à 50 km/h',
    explanation: 'Le panneau circulaire rouge avec 50 impose une vitesse maximale de 50 km/h à partir de ce point.',
  },
  {
    id: 'q04', number: 4, category: 'Signalisation',
    text: 'Vous approchez de ce panneau. Que devez-vous faire impérativement ?',
    options: ['Ralentir et klaxonner', 'Vous arrêter — accès totalement interdit', 'Passer si votre véhicule est petit', 'Céder le passage à droite'],
    correct_answer: 'Vous arrêter — accès totalement interdit',
    media_type: 'svg', media_url: 'no_entry', media_alt: 'Panneau sens interdit — rond rouge avec barre blanche',
    explanation: 'Le panneau sens interdit interdit tout accès. Vous ne pouvez pas vous engager dans cette voie.',
  },
  {
    id: 'q05', number: 5, category: 'Signalisation',
    text: "Vous entrez dans un giratoire. Ce panneau est à l'entrée. Que signifie-t-il ?",
    options: ['Vous avez la priorité sur les voitures dans le rond-point', 'Vous devez céder le passage aux véhicules circulant dans le giratoire', 'Sens obligatoire pour les camions', 'Vitesse maximale de 20 km/h dans le giratoire'],
    correct_answer: 'Vous devez céder le passage aux véhicules circulant dans le giratoire',
    media_type: 'svg', media_url: 'roundabout', media_alt: 'Panneau giratoire — rond bleu avec flèche circulaire',
    explanation: "À l'entrée d'un giratoire, vous devez toujours céder le passage aux véhicules déjà engagés.",
  },
  {
    id: 'q06', number: 6, category: 'Priorités',
    text: 'Dans cette situation, quelle voiture est prioritaire ?',
    options: ['La voiture A (venant de gauche)', 'La voiture B (venant du bas, à droite de A)', 'Les deux arrivent ensemble — ni l\'une ni l\'autre', 'La voiture la plus rapide'],
    correct_answer: 'La voiture B (venant du bas, à droite de A)',
    media_type: 'svg', media_url: 'intersection_priority_right', media_alt: 'Intersection sans signalisation — voiture A vient de gauche, voiture B vient du bas',
    explanation: 'Sans signalisation, la priorité à droite s\'applique. B arrive par la droite de A → B est prioritaire.',
  },
  {
    id: 'q07', number: 7, category: 'Priorités',
    text: 'Qui a la priorité dans cette scène de giratoire ?',
    options: ['La voiture qui entre (rouge)', 'La voiture déjà dans le giratoire (bleue)', 'Le véhicule le plus grand', 'Celui qui a le clignotant activé'],
    correct_answer: 'La voiture déjà dans le giratoire (bleue)',
    media_type: 'svg', media_url: 'intersection_roundabout', media_alt: "Giratoire — voiture entrant vs voiture circulant à l'intérieur",
    explanation: 'Les véhicules circulant dans le giratoire ont toujours la priorité sur ceux qui entrent.',
  },
  {
    id: 'q08', number: 8, category: 'Priorités',
    text: 'Un SAMU avec gyrophare et sirène approche dans votre dos. Que faites-vous ?',
    options: ['Maintenez votre vitesse pour ne pas le gêner', 'Serrez à droite dès que possible, ralentissez, laissez-le passer', 'Klaxonnez pour avertir les autres conducteurs', 'Ignorez-le sur les routes secondaires'],
    correct_answer: 'Serrez à droite dès que possible, ralentissez, laissez-le passer',
    media_type: 'svg', media_url: 'situation_emergency_vehicle', media_alt: 'Ambulance avec gyrophare dépassant des voitures qui se dégagent',
    explanation: "Les véhicules d'urgence en intervention ont priorité absolue. Dégagez-vous immédiatement.",
  },
  {
    id: 'q09', number: 9, category: 'Priorités',
    text: 'À un passage à niveau non gardé sans barrières, vous devez :',
    options: ['Traverser rapidement sans vous arrêter', "Marquer l'arrêt obligatoire, regarder des deux côtés, traverser vite", 'Klaxonner et traverser en accélérant', 'Céder uniquement si vous entendez le train'],
    correct_answer: "Marquer l'arrêt obligatoire, regarder des deux côtés, traverser vite",
    explanation: "L'arrêt est obligatoire aux passages à niveau non gardés. Vérifiez de chaque côté avant de traverser.",
  },
  {
    id: 'q10', number: 10, category: 'Vitesse',
    text: 'Quelle distance de sécurité devez-vous respecter avec le véhicule devant vous ?',
    options: ['Une distance fixe de 10 mètres', 'La distance parcourue en 2 secondes minimum', 'La longueur de votre voiture', '5 mètres en ville, 10 mètres sur route'],
    correct_answer: 'La distance parcourue en 2 secondes minimum',
    media_type: 'svg', media_url: 'situation_safe_distance', media_alt: 'Deux voitures sur route avec indication de la distance de sécurité de 2 secondes',
    explanation: 'La règle des 2 secondes s\'adapte à la vitesse : à 90 km/h, cela correspond à environ 50 mètres.',
  },
  {
    id: 'q11', number: 11, category: 'Vitesse',
    text: 'Quelle est la vitesse maximale autorisée en agglomération en Guinée (sauf panneau contraire) ?',
    options: ['40 km/h', '50 km/h', '60 km/h', '70 km/h'],
    correct_answer: '50 km/h',
    explanation: 'La limite légale en agglomération est de 50 km/h conformément à la réglementation guinéenne.',
  },
  {
    id: 'q12', number: 12, category: 'Vitesse',
    text: 'Sur route nationale hors agglomération, la vitesse maximale est :',
    options: ['80 km/h', '90 km/h', '100 km/h', '110 km/h'],
    correct_answer: '90 km/h',
    explanation: 'La limite hors agglomération sur route nationale est de 90 km/h en Guinée.',
  },
  {
    id: 'q13', number: 13, category: 'Vitesse',
    text: 'Par pluie battante réduisant la visibilité, vous devez :',
    options: ['Maintenir votre vitesse habituelle', 'Réduire votre vitesse et augmenter vos distances de sécurité', 'Allumer les feux de route et maintenir la vitesse', 'Doubler la distance de freinage et rien d\'autre'],
    correct_answer: 'Réduire votre vitesse et augmenter vos distances de sécurité',
    explanation: "La pluie réduit l'adhérence et la visibilité. Réduire la vitesse et augmenter les distances est impératif.",
  },
  {
    id: 'q14', number: 14, category: 'Vitesse',
    text: 'La distance d\'arrêt à 90 km/h sur route sèche est d\'environ :',
    options: ['30 mètres', '50 mètres', '75 mètres', '120 mètres'],
    correct_answer: '75 mètres',
    explanation: 'À 90 km/h : environ 25 m de réaction (1 s) + 50 m de freinage = 75 m sur route sèche.',
  },
  {
    id: 'q15', number: 15, category: 'Dépassement',
    text: 'Dans cette scène, devez-vous dépasser le camion ?',
    options: ['Oui, la voie en face semble libre', 'Non — ligne continue et virage = dépassement interdit', 'Oui si vous klaxonnez d\'abord', 'Oui si vous roulez vite'],
    correct_answer: 'Non — ligne continue et virage = dépassement interdit',
    media_type: 'svg', media_url: 'situation_overtake_forbidden', media_alt: 'Route avec virage, ligne blanche continue et camion devant',
    explanation: 'La ligne continue + le virage interdisent formellement tout dépassement dans cette zone.',
  },
  {
    id: 'q16', number: 16, category: 'Dépassement',
    text: 'Avant de dépasser, vous devez vérifier (choisissez la réponse complète) :',
    options: ['Que votre klaxon fonctionne', 'Que la voie opposée est libre, que le dépassement est autorisé, que vous pouvez finir avant un obstacle', 'Que le conducteur devant vous vous a vu', 'Que vous avez assez de carburant'],
    correct_answer: 'Que la voie opposée est libre, que le dépassement est autorisé, que vous pouvez finir avant un obstacle',
    explanation: 'Un dépassement mal préparé est la cause de nombreux accidents graves. Les trois vérifications sont indispensables.',
  },
  {
    id: 'q17', number: 17, category: 'Dépassement',
    text: 'Vous souhaitez tourner à gauche. Quelle est la séquence correcte ?',
    options: ['Tourner directement sans signal', 'Signaler, se placer à gauche, ralentir, vérifier les rétroviseurs puis tourner', 'Klaxonner et tourner rapidement', 'Attendre que tous les véhicules s\'arrêtent'],
    correct_answer: 'Signaler, se placer à gauche, ralentir, vérifier les rétroviseurs puis tourner',
    explanation: 'Toute manœuvre exige : signal suffisamment tôt, positionnement correct, réduction de vitesse, vérification.',
  },
  {
    id: 'q18', number: 18, category: 'Signalisation',
    text: 'Une ligne blanche continue au sol signifie :',
    options: ['On peut la franchir si la voie est libre', 'Il est interdit de la franchir ou de la chevaucher', 'Zone de stationnement autorisé', 'Fin de voie prioritaire'],
    correct_answer: 'Il est interdit de la franchir ou de la chevaucher',
    explanation: 'La ligne continue est absolument infranchissable — aucun dépassement ni changement de file n\'est permis.',
  },
  {
    id: 'q19', number: 19, category: 'Signalisation',
    text: 'Un feu orange clignotant à une intersection vous indique :',
    options: ['Arrêt obligatoire', 'Passage libre sans précaution', 'Ralentir et traverser prudemment', 'Priorité à droite'],
    correct_answer: 'Ralentir et traverser prudemment',
    explanation: 'Le feu orange clignotant signale un carrefour dangereux : traversez lentement en vous assurant que la voie est dégagée.',
  },
  {
    id: 'q20', number: 20, category: 'Signalisation',
    text: 'Ce panneau vous oblige à :',
    options: ['Céder le passage', 'Tourner à droite uniquement', 'Aller tout droit — direction obligatoire', 'Maintenir votre vitesse'],
    correct_answer: 'Aller tout droit — direction obligatoire',
    media_type: 'svg', media_url: 'mandatory', media_alt: 'Panneau rond bleu avec flèche blanche indiquant direction obligatoire tout droit',
    explanation: 'Le panneau circulaire bleu à flèche impose la direction indiquée. Vous devez aller tout droit.',
  },
  {
    id: 'q21', number: 21, category: 'Signalisation',
    text: 'Ce panneau triangulaire rouge avec point d\'exclamation signifie :',
    options: ['Travaux sur chaussée', 'Danger non spécifié — vigilance requise', 'Priorité à droite', 'Zone scolaire'],
    correct_answer: 'Danger non spécifié — vigilance requise',
    media_type: 'svg', media_url: 'priority', media_alt: "Panneau triangulaire rouge avec point d'exclamation",
    explanation: "Ce triangle avertit d'un danger dont la nature n'est pas précisée. Adaptez votre vitesse.",
  },
  {
    id: 'q22', number: 22, category: 'Signalisation',
    text: 'Un panneau octogonal rouge avec STOP m\'impose :',
    options: ['Ralentir fortement', 'Céder le passage uniquement si un véhicule arrive', 'Arrêt complet obligatoire puis priorité aux véhicules sur la voie principale', 'Klaxonner avant de passer'],
    correct_answer: 'Arrêt complet obligatoire puis priorité aux véhicules sur la voie principale',
    media_type: 'svg', media_url: 'stop', media_alt: 'Panneau STOP',
    explanation: 'Le STOP impose un arrêt complet (roues immobiles) avant la ligne. Ensuite, céder le passage.',
  },
  {
    id: 'q23', number: 23, category: 'Sécurité',
    text: 'Le port de la ceinture de sécurité est :',
    options: ['Obligatoire uniquement sur les routes nationales', 'Obligatoire pour tous les occupants en toutes circonstances', 'Conseillé mais pas obligatoire en ville', 'Obligatoire seulement pour le conducteur'],
    correct_answer: 'Obligatoire pour tous les occupants en toutes circonstances',
    explanation: 'La ceinture est obligatoire pour TOUS les occupants (avant et arrière) dès que le véhicule est en mouvement.',
  },
  {
    id: 'q24', number: 24, category: 'Sécurité',
    text: 'À quelle distance devez-vous placer votre triangle de signalisation ?',
    options: ['5 mètres', 'Juste derrière le véhicule', '30 mètres minimum, davantage sur route rapide', '100 mètres exactement'],
    correct_answer: '30 mètres minimum, davantage sur route rapide',
    explanation: 'Le triangle se place à 30 m minimum. Sur route rapide ou à mauvaise visibilité, plus loin pour avertir à temps.',
  },
  {
    id: 'q25', number: 25, category: 'Sécurité',
    text: "L'usage du téléphone tenu en main en conduisant est :",
    options: ['Autorisé à l\'arrêt au feu rouge', 'Autorisé si vous roulez sous 30 km/h', 'Interdit — seul le kit mains-libres est toléré', 'Autorisé sur les routes peu fréquentées'],
    correct_answer: 'Interdit — seul le kit mains-libres est toléré',
    explanation: "Le téléphone tenu en main est interdit en conduisant. L'attention requise pour conduire ne supporte pas de distraction.",
  },
  {
    id: 'q26', number: 26, category: 'Sécurité',
    text: 'Un siège enfant homologué est obligatoire pour :',
    options: ['Les enfants de moins de 5 ans', 'Les enfants de moins de 10 ans ou mesurant moins de 1,35 m', 'Les enfants de moins de 3 ans uniquement', 'Les enfants de moins de 6 ans et moins de 15 kg'],
    correct_answer: 'Les enfants de moins de 10 ans ou mesurant moins de 1,35 m',
    explanation: 'Tout enfant de moins de 10 ans ou mesurant moins de 1,35 m doit être dans un dispositif de retenue homologué.',
  },
  {
    id: 'q27', number: 27, category: 'Urgence',
    text: 'Vos freins semblent défaillants en descente. La bonne réaction est :',
    options: ['Couper le moteur immédiatement', 'Rétrograder, utiliser le frein à main progressivement, chercher un obstacle naturel', 'Accélérer pour passer le danger plus vite', 'Ouvrir la portière pour ralentir par friction'],
    correct_answer: 'Rétrograder, utiliser le frein à main progressivement, chercher un obstacle naturel',
    explanation: 'Freinage moteur + frein à main progressif (sans bloquer) + sortie contrôlée sont les bons réflexes face à une défaillance de freins.',
  },
  {
    id: 'q28', number: 28, category: 'Urgence',
    text: 'Votre voiture prend feu. La séquence correcte est :',
    options: ['Appeler les pompiers depuis le véhicule puis sortir', "S'arrêter, couper le moteur, sortir, s'éloigner, appeler les secours", "Tenter d'éteindre avec l'eau du radiateur", 'Continuer à rouler vers un poste de secours'],
    correct_answer: "S'arrêter, couper le moteur, sortir, s'éloigner, appeler les secours",
    explanation: "Le risque d'explosion impose une évacuation immédiate. Éloignez-vous d'au moins 50 mètres avant d'appeler.",
  },
  {
    id: 'q29', number: 29, category: 'Urgence',
    text: 'En cas d\'aquaplaning, vous devez :',
    options: ['Freiner fort pour regagner l\'adhérence', 'Tourner le volant en sens opposé au glissement', 'Lâcher l\'accélérateur doucement et tenir le volant sans brusquerie', 'Changer de voie rapidement'],
    correct_answer: "Lâcher l'accélérateur doucement et tenir le volant sans brusquerie",
    explanation: 'Tout geste brusque aggraverait la perte de contrôle. Relâchez doucement l\'accélérateur et laissez les pneus reprendre contact.',
  },
  {
    id: 'q30', number: 30, category: 'Urgence',
    text: 'Sur une chaussée verglacée, la distance de freinage est :',
    options: ['Identique à la route sèche', '1,5 fois plus longue', '5 à 10 fois plus longue', '2 fois plus longue exactement'],
    correct_answer: '5 à 10 fois plus longue',
    explanation: 'Sur verglas, la distance de freinage peut être multipliée par 5 à 10. Adaptez impérativement votre vitesse et vos distances.',
  },
  {
    id: 'q31', number: 31, category: 'Alcool / Drogues',
    text: 'Le taux d\'alcoolémie maximal légal pour conduire en Guinée est :',
    options: ['0,0 g/L', '0,3 g/L de sang', '0,5 g/L de sang', '0,8 g/L de sang'],
    correct_answer: '0,5 g/L de sang',
    explanation: 'La limite légale guinéenne est de 0,5 g/L de sang (0,25 mg/L d\'air expiré), conforme aux normes CEDEAO.',
  },
  {
    id: 'q32', number: 32, category: 'Alcool / Drogues',
    text: 'La consommation de cannabis avant de conduire :',
    options: ["N'a aucun effet sur la conduite", 'Perturbe réflexes, coordination et perception du temps — elle est interdite', 'Améliore la concentration', 'Est tolérée plusieurs heures après la consommation'],
    correct_answer: 'Perturbe réflexes, coordination et perception du temps — elle est interdite',
    explanation: 'Le cannabis altère significativement les capacités de conduite et reste détectable plusieurs heures après consommation.',
  },
  {
    id: 'q33', number: 33, category: 'Alcool / Drogues',
    text: 'Les médicaments peuvent-ils affecter la conduite ?',
    options: ['Non, ils sont inoffensifs en doses normales', 'Oui — somnolence, réflexes diminués, troubles de vision ; lisez la notice', 'Seulement les médicaments à base de codéine', 'Seulement à forte dose'],
    correct_answer: 'Oui — somnolence, réflexes diminués, troubles de vision ; lisez la notice',
    explanation: 'Antihistaminiques, anxiolytiques, antidouleurs… nombreux médicaments altèrent la vigilance. Vérifiez toujours la notice.',
  },
  {
    id: 'q34', number: 34, category: 'Premiers secours',
    text: 'Vous arrivez sur un accident. Votre première action est :',
    options: ['Prendre des photos de la scène', 'Protéger, Alerter, Secourir (PAS) — sécuriser la zone, appeler, aider', 'Déplacer immédiatement tous les blessés', 'Chercher les responsables'],
    correct_answer: 'Protéger, Alerter, Secourir (PAS) — sécuriser la zone, appeler, aider',
    explanation: "La règle PAS : 1) Protéger (éviter sur-accident) 2) Alerter (secours) 3) Secourir (sans aggraver les blessures).",
  },
  {
    id: 'q35', number: 35, category: 'Premiers secours',
    text: 'Une victime est inconsciente mais respire. Que faites-vous ?',
    options: ['La laisser sur le dos', 'La mettre en Position Latérale de Sécurité (PLS)', "Lui donner de l'eau", 'La faire marcher pour la réveiller'],
    correct_answer: 'La mettre en Position Latérale de Sécurité (PLS)',
    explanation: 'La PLS maintient les voies respiratoires libres et prévient l\'étouffement chez une victime inconsciente qui respire.',
  },
  {
    id: 'q36', number: 36, category: 'Premiers secours',
    text: 'Pour réduire la pollution, le conducteur doit :',
    options: ['Garder le moteur au ralenti lors des arrêts', 'Couper le moteur pour les arrêts > 30 secondes et entretenir régulièrement son véhicule', 'Utiliser du carburant non filtré', 'Rouler vite pour consommer moins'],
    correct_answer: 'Couper le moteur pour les arrêts > 30 secondes et entretenir régulièrement son véhicule',
    explanation: 'Couper le moteur à l\'arrêt réduit les émissions et la consommation. Un véhicule bien entretenu pollue moins.',
  },
  {
    id: 'q37', number: 37, category: 'Signalisation',
    text: 'Un feu vert pour les piétons signifie pour le conducteur :',
    options: ['Il peut passer si aucun piéton n\'est visible', 'Priorité absolue aux piétons — le conducteur doit s\'arrêter', 'Il peut klaxonner et passer', 'Ce feu ne le concerne pas'],
    correct_answer: 'Priorité absolue aux piétons — le conducteur doit s\'arrêter',
    explanation: 'Feu vert piéton = le conducteur DOIT s\'arrêter et laisser traverser les piétons.',
  },
  {
    id: 'q38', number: 38, category: 'Sécurité',
    text: 'Vous êtes somnolent sur la route. Que faites-vous ?',
    options: ['Ouvrez la fenêtre et maintenez votre vitesse', 'Boire un café et conduire encore 2h', 'Vous arrêter dès que possible et vous reposer', 'Mettre de la musique forte'],
    correct_answer: 'Vous arrêter dès que possible et vous reposer',
    explanation: 'La somnolence est aussi dangereuse que l\'alcool. Seul le repos élimine le risque — aucune astuce ne compense.',
  },
  {
    id: 'q39', number: 39, category: 'Priorités',
    text: 'Vous tournez à gauche à un carrefour. Un piéton traverse en face. Vous devez :',
    options: ['Passer rapidement avant le piéton', 'Céder le passage au piéton', 'Klaxonner pour qu\'il accélère', 'Continuer si votre feu est vert'],
    correct_answer: 'Céder le passage au piéton',
    explanation: 'Tout véhicule tournant doit céder le passage aux piétons qui traversent la voie dans laquelle il s\'engage.',
  },
  {
    id: 'q40', number: 40, category: 'Dépassement',
    text: 'Le dépassement par la droite est :',
    options: ['Toujours interdit', 'Autorisé sur les routes à 3 voies', 'Interdit sauf en cas de file de gauche ralentissant ou lorsqu\'un conducteur tourne à gauche', 'Autorisé si vous roulez vite'],
    correct_answer: "Interdit sauf en cas de file de gauche ralentissant ou lorsqu'un conducteur tourne à gauche",
    explanation: 'Le dépassement par la droite est généralement interdit. Les exceptions sont strictement encadrées.',
  },
  // ── Questions additionnelles avec médias enrichis ──────────────────────────
  {
    id: 'q41_tl', number: 41, category: 'Signalisation',
    text: "Ce feu passe à l'orange. Que devez-vous faire si vous pouvez vous arrêter en sécurité ?",
    options: ['Accélérer pour passer avant le rouge', "Ralentir et s'arrêter avant la ligne", 'Continuer si moins de 10 m du feu', 'Klaxonner et passer'],
    correct_answer: "Ralentir et s'arrêter avant la ligne",
    media_type: 'svg', media_url: 'traffic_light_orange', media_alt: 'Feu tricolore — phase orange (transition vers rouge)',
    explanation: "L'orange signale l'imminence du rouge. Arrêtez-vous si c'est possible sans freinage brusque dangereux.",
  },
  {
    id: 'q42_tl', number: 42, category: 'Signalisation',
    text: 'Ce feu est rouge et orange simultanément. Que signifie cette phase ?',
    options: ['Vous pouvez passer prudemment', 'Le feu va passer au vert — préparez-vous', 'Feu défaillant — passez avec prudence', 'Demi-tour autorisé'],
    correct_answer: 'Le feu va passer au vert — préparez-vous',
    media_type: 'svg', media_url: 'traffic_light_red_orange', media_alt: 'Feu tricolore — rouge et orange simultanés (transition vers vert)',
    explanation: 'Rouge + orange simultanément annonce le vert imminent. Passez en 1re vitesse et soyez prêt à démarrer.',
  },
  {
    id: 'q43_nuit', number: 43, category: 'Sécurité',
    text: "Vous conduisez de nuit à 90 km/h. Vos feux éclairent à 40 m. La distance d'arrêt est 70 m. Est-ce sûr ?",
    options: ['Oui — vous êtes dans la zone sûre', "Non — 70 m > 40 m : ralentissez à 60 km/h", 'Oui — 40 m suffit à cette vitesse', 'Acceptable de nuit uniquement'],
    correct_answer: "Non — 70 m > 40 m : ralentissez à 60 km/h",
    media_type: 'svg', media_url: 'night_driving', media_alt: 'Conduite de nuit — portée des feux de croisement limitée à 40 m',
    explanation: "À 90 km/h, la distance d'arrêt est ~70 m mais les feux n'éclairent qu'à 40 m : danger. Réduire à 60 km/h.",
  },
  {
    id: 'q44_pluie', number: 44, category: 'Sécurité',
    text: 'Pluie forte, visibilité < 50 m. Quelle vitesse maximale est autorisée toutes routes confondues ?',
    options: ['110 km/h', '90 km/h', '80 km/h (règle visibilité < 50 m)', '50 km/h'],
    correct_answer: '80 km/h (règle visibilité < 50 m)',
    media_type: 'svg', media_url: 'rain_driving', media_alt: 'Conduite sous pluie forte — visibilité réduite, route glissante',
    explanation: 'Visibilité < 50 m = 80 km/h maximum, quelle que soit la route. Doublez les distances de sécurité.',
  },
  {
    id: 'q45_alcool', number: 45, category: 'Alcool & Drogues',
    text: 'Taux maximal autorisé pour un conducteur expérimenté en Guinée (permis > 2 ans) ?',
    options: ['0,0 g/L', '0,5 g/L de sang', '0,8 g/L', '1,0 g/L'],
    correct_answer: '0,5 g/L de sang',
    media_type: 'svg', media_url: 'alcohol_scene', media_alt: "Contrôle éthylomètre par les forces de l'ordre",
    explanation: "Taux légal : 0,5 g/L de sang. Nouveaux conducteurs (< 2 ans) : 0,2 g/L. Dépassement = suspension + amende + prison.",
  },
  {
    id: 'q46_urgence', number: 46, category: 'Premiers secours',
    text: 'Accident avec victimes : quelle est la bonne séquence ?',
    options: ['Secourir → Alerter → Protéger', 'Protéger → Alerter → Secourir', 'Alerter → Protéger → Secourir', 'Protéger → Secourir → Alerter'],
    correct_answer: 'Protéger → Alerter → Secourir',
    media_type: 'svg', media_url: 'first_aid', media_alt: "Premiers secours — triangle de signalisation, appel d'urgence",
    explanation: 'PAS : Protéger (baliser, couper contact), Alerter (115 SAMU ou 17 Gendarmerie), Secourir (PLS, MCE si formé). Ne jamais déplacer sans raison.',
  },
];
