/**
 * Système i18n CodeRoute Guinée — 8 langues
 *
 * Langues nationales selon la Constitution guinéenne (Article 6) :
 *   fr  — Français (officiel)
 *   ff  — Pular / Fulfulde (Fouta Djalon, ~40 % population)
 *   man — Malinké / Mandinka (Haute-Guinée, ~25 %)
 *   sus — Soussou (Basse-Guinée / Conakry, ~20 %)
 *   kss — Kissi (Guinée forestière — N'Zérékoré, Kissidougou)
 *   gkp — Kpelle / Guerzé (Guinée forestière — Nzérékoré)
 *   lom — Toma / Loma (Guinée forestière — Macenta, Beyla)
 *   en  — English (administration internationale)
 */

export type Locale = 'fr' | 'ff' | 'man' | 'sus' | 'kss' | 'gkp' | 'lom' | 'en';

export const SUPPORTED_LOCALES: { code: Locale; label: string; native: string; region: string }[] = [
  { code: 'fr',  label: 'Français',   native: 'Français',     region: 'Officiel' },
  { code: 'ff',  label: 'Pular',      native: 'Pulaar',       region: 'Fouta Djalon' },
  { code: 'man', label: 'Malinké',    native: 'Mandinkakan',  region: 'Haute-Guinée' },
  { code: 'sus', label: 'Soussou',    native: 'Sosoxui',      region: 'Basse-Guinée' },
  { code: 'kss', label: 'Kissi',      native: 'Kísîî',        region: 'Guinée forestière' },
  { code: 'gkp', label: 'Kpelle',     native: 'Kpɛlɛwoo',    region: 'N\'Zérékoré' },
  { code: 'lom', label: 'Toma',       native: 'Tɔmaa',        region: 'Macenta' },
  { code: 'en',  label: 'English',    native: 'English',      region: 'International' },
];

type TranslationMap = Record<string, string>;
type Translations = Record<Locale, TranslationMap>;

const translations: Translations = {

  // ══════════════════════════════════════════════════════════════════
  // FRANÇAIS — Langue officielle de référence
  // ══════════════════════════════════════════════════════════════════
  fr: {
    // Navigation
    'nav.home':           'Accueil',
    'nav.candidate':      'Espace candidat',
    'nav.center':         'Espace centre',
    'nav.admin':          'Administration',
    'nav.exam':           'Examen',
    'nav.results':        'Résultats',
    'nav.dossier':        'Mon dossier',
    'nav.training':       'Entraînement',
    'nav.login':          'Connexion',
    'nav.account':        'Mon compte',
    'nav.logout':         'Déconnexion',

    // Auth
    'auth.email':         'Adresse e-mail',
    'auth.password':      'Mot de passe',
    'auth.login':         'Se connecter',
    'auth.logout':        'Se déconnecter',
    'auth.welcome':       'Bienvenue sur CodeRoute Guinée',
    'auth.sign_in':       'Connexion à votre compte',

    // Examen
    'exam.title':         'Examen officiel',
    'exam.category':      'Catégorie B',
    'exam.questions':     'questions',
    'exam.duration':      '30 minutes',
    'exam.threshold':     'Seuil : 35/40',
    'exam.start':         'Démarrer l\'examen',
    'exam.submit':        'Soumettre',
    'exam.next':          'Suivante',
    'exam.prev':          'Précédente',
    'exam.skip':          'Passer',
    'exam.passed':        'Admis',
    'exam.failed':        'Ajourné',
    'exam.score':         'Score',
    'exam.time_left':     'Temps restant',
    'exam.time_warning':  'Moins de 5 minutes',
    'exam.time_critical': 'Temps presque écoulé !',

    // Entraînement
    'training.title':     'Entraînement',
    'training.free':      'Mode libre',
    'training.series':    'Série thématique',
    'training.mock':      'Examen blanc',
    'training.progress':  'Mes progrès',
    'training.weak':      'Points à améliorer',

    // Domaine
    'domain.candidate':   'Candidat',
    'domain.center':      'Centre agréé',
    'domain.session':     'Session d\'examen',
    'domain.booking':     'Réservation',
    'domain.payment':     'Paiement',
    'domain.certificate': 'Certificat',
    'domain.result':      'Résultat',
    'domain.score':       'Score',

    // Statuts
    'status.passed':      'Admis',
    'status.failed':      'Ajourné',
    'status.pending':     'En attente',
    'status.paid':        'Payé',
    'status.active':      'Actif',
    'status.verified':    'Vérifié',

    // Actions
    'action.save':        'Enregistrer',
    'action.cancel':      'Annuler',
    'action.confirm':     'Confirmer',
    'action.download':    'Télécharger',
    'action.search':      'Rechercher',
    'action.validate':    'Valider',
    'action.pay':         'Payer',
    'action.verify':      'Vérifier',

    // Paiement
    'payment.orange':     'Orange Money',
    'payment.mtn':        'MTN Money',
    'payment.wave':       'Wave',
    'payment.amount':     'Montant (GNF)',
    'payment.phone':      'Numéro de téléphone',
    'payment.success':    'Paiement confirmé',

    // Erreurs
    'error.generic':      'Une erreur s\'est produite',
    'error.network':      'Erreur de connexion',
    'error.auth':         'Session expirée, reconnectez-vous',
    'error.not_found':    'Ressource introuvable',

    // Infos
    'info.loading':       'Chargement…',
    'info.no_data':       'Aucune donnée disponible',
    'info.success':       'Opération réussie',
  },

  // ══════════════════════════════════════════════════════════════════
  // PULAR / FULFULDE — Fouta Djalon (~40 % de la population)
  // Dialecte guinéen (≠ Fulfulde du Sahel)
  // ══════════════════════════════════════════════════════════════════
  ff: {
    'nav.home':           'Suudu Mawdo',
    'nav.candidate':      'Jaŋtorde Calonke',
    'nav.center':         'Jaŋtorde Laamorde',
    'nav.admin':          'Binndi-Laamu',
    'nav.exam':           'Janngirde',
    'nav.results':        'Jaabawuuji',
    'nav.dossier':        'Dosiye Am',
    'nav.training':       'Haaɗtirde',
    'nav.login':          'Naatde',
    'nav.account':        'Ñoɓirde Am',
    'nav.logout':         'Yaltude',

    'auth.email':         'Iimeel',
    'auth.password':      'Finaa-tawaa',
    'auth.login':         'Naatde',
    'auth.logout':        'Yaltude',
    'auth.welcome':       'Bismillaa to CodeRoute Gine',
    'auth.sign_in':       'Naatde e ñoɓirde maa',

    'exam.title':         'Janngirde Laawol',
    'exam.category':      'Ɓeyɗi B',
    'exam.questions':     'faayidaaji',
    'exam.duration':      '30 hojomaaji',
    'exam.threshold':     'Cehol : 35/40',
    'exam.start':         'Fuɗɗude Janngirde',
    'exam.submit':        'Aawde',
    'exam.next':          'Yeeso',
    'exam.prev':          'Ɓaawo',
    'exam.skip':          'Ɗaɓɓude',
    'exam.passed':        'Laaɓi ✓',
    'exam.failed':        'Waylaaki ✗',
    'exam.score':         'Limoore',
    'exam.time_left':     'Waktu toowi',
    'exam.time_warning':  'Waktu ɓuri 5 hojomaaji',
    'exam.time_critical': '⚠️ Waktu ɓuri wuurde !',

    'training.title':     'Haaɗtirde',
    'training.free':      'Laawol Libre',
    'training.series':    'Seɗɗaaji Teeŋtinaaɗi',
    'training.mock':      'Janngirde Haala',
    'training.progress':  'Nanngu Am',
    'training.weak':      'Ko Foti Haaɗtirde',

    'domain.candidate':   'Calonke',
    'domain.center':      'Laamorɗe',
    'domain.session':     'Janngirde-Waktu',
    'domain.booking':     'Muuɗtaade',
    'domain.payment':     'Liggorde',
    'domain.certificate': 'Takkaare',
    'domain.result':      'Jaabawal',
    'domain.score':       'Limoore',

    'status.passed':      'Laaɓi',
    'status.failed':      'Waylaaki',
    'status.pending':     'Ɗowtiiɗo',
    'status.paid':        'Liggaama',
    'status.active':      'Hollitiima',
    'status.verified':    'Ɓettaama',

    'action.save':        'Dannude',
    'action.cancel':      'Haɗde',
    'action.confirm':     'Siftorde',
    'action.download':    'Aawde',
    'action.search':      'Yiylude',
    'action.validate':    'Humpitinde',
    'action.pay':         'Ligginde',
    'action.verify':      'Ɓettude',

    'payment.orange':     'Orange Money',
    'payment.mtn':        'MTN Money',
    'payment.wave':       'Wave',
    'payment.amount':     'Limoore (GNF)',
    'payment.phone':      'Nimero Telefoon',
    'payment.success':    'Liggirde Laaɓii',

    'error.generic':      'Juumre waɗii',
    'error.network':      'Juumre Reseŋ',
    'error.auth':         'Waktu yalti — naatid kadi',
    'error.not_found':    'Laaɓaani',

    'info.loading':       'Ɗowtude…',
    'info.no_data':       'Hay fuu alaa',
    'info.success':       'Laaɓii ✓',
  },

  // ══════════════════════════════════════════════════════════════════
  // MALINKÉ / MANDINKA — Haute-Guinée (~25 %)
  // Variante guinéenne du Mandé
  // ══════════════════════════════════════════════════════════════════
  man: {
    'nav.home':           'So Kɔrɔ',
    'nav.candidate':      'Kuntigibaaɲɔgɔn',
    'nav.center':         'Senfɛlabaa',
    'nav.admin':          'Kuntigi',
    'nav.exam':           'Sɛgɛsɛgɛli',
    'nav.results':        'Lajɛlennw',
    'nav.dossier':        'N ka Dosiye',
    'nav.training':       'Kalanni',
    'nav.login':          'Dɔn',
    'nav.account':        'N ka Kɔnɔ',
    'nav.logout':         'Bɔ',

    'auth.email':         'Imɛli',
    'auth.password':      'Gundo',
    'auth.login':         'Dɔn',
    'auth.logout':        'Bɔ',
    'auth.welcome':       'Aw ni ce — CodeRoute Gine',
    'auth.sign_in':       'Aw ka kɔnɔ dɔn',

    'exam.title':         'Laɲini Kɛcogo',
    'exam.category':      'Wolo B',
    'exam.questions':     'ɲininkaliw',
    'exam.duration':      'Miniti 30',
    'exam.threshold':     'Sehol : 35/40',
    'exam.start':         'Sɛgɛsɛgɛli Daminɛ',
    'exam.submit':        'Ci',
    'exam.next':          'Nɔ',
    'exam.prev':          'Kɔ',
    'exam.skip':          'Tɛmɛ',
    'exam.passed':        'Sɔrɔlen ✓',
    'exam.failed':        'Tɛ ✗',
    'exam.score':         'Tɔgɔtɔgɔ',
    'exam.time_left':     'Waati Toomi',
    'exam.time_warning':  'Miniti 5 kelen bɛ tɔ',
    'exam.time_critical': '⚠️ Waati banna !',

    'training.title':     'Kalanni',
    'training.free':      'Kalanni Yɛrɛma',
    'training.series':    'Ɲininkali Koorow',
    'training.mock':      'Sɛgɛsɛgɛli Haala',
    'training.progress':  'N ka Sɔrɔliw',
    'training.weak':      'Ko Baarikama',

    'domain.candidate':   'Kuntigibaaw',
    'domain.center':      'Senfɛlabaa',
    'domain.session':     'Sɛgɛsɛgɛli Loon',
    'domain.booking':     'Sɛnbɔ',
    'domain.payment':     'Sara',
    'domain.certificate': 'Maratigɛ',
    'domain.result':      'Lajɛlen',
    'domain.score':       'Tɔgɔtɔgɔ',

    'status.passed':      'Sɔrɔlen',
    'status.failed':      'Tɛ',
    'status.pending':     'Kɔnɔ',
    'status.paid':        'Saralen',
    'status.active':      'Kɛlen',
    'status.verified':    'Dafalen',

    'action.save':        'Mara',
    'action.cancel':      'Dabɔ',
    'action.confirm':     'Dafa',
    'action.download':    'Kɔrɔ',
    'action.search':      'Ɲini',
    'action.validate':    'Dafa',
    'action.pay':         'Sara',
    'action.verify':      'Lajɛ',

    'payment.orange':     'Orange Money',
    'payment.mtn':        'MTN Money',
    'payment.wave':       'Wave',
    'payment.amount':     'Hakɛ (GNF)',
    'payment.phone':      'Telefɔni Nimɔrɔ',
    'payment.success':    'Sara Kɛra ✓',

    'error.generic':      'Fili dɔ kɛra',
    'error.network':      'Rezo fili',
    'error.auth':         'Loon banna — dɔn kɔ',
    'error.not_found':    'Tɛ sɔrɔ',

    'info.loading':       'Ɲinini…',
    'info.no_data':       'Fɛn si tɛ',
    'info.success':       'Kɛra Caman ✓',
  },

  // ══════════════════════════════════════════════════════════════════
  // SOUSSOU — Basse-Guinée / Conakry (~20 %)
  // Langue bantoue / Mande-Fu
  // ══════════════════════════════════════════════════════════════════
  sus: {
    'nav.home':           'Bande Fɔlɔ',
    'nav.candidate':      'Nakɛɛmakɛɛ',
    'nav.center':         'Santara',
    'nav.admin':          'Kuntigi',
    'nav.exam':           'Kɔntɔrɔli',
    'nav.results':        'Jɛtɛwali',
    'nav.dossier':        'N Dɔsiye',
    'nav.training':       'Kalanɛ',
    'nav.login':          'Siga',
    'nav.account':        'N Konto',
    'nav.logout':         'Bɔ',

    'auth.email':         'Imɛli',
    'auth.password':      'Sɛkɛrɛ',
    'auth.login':         'Siga',
    'auth.logout':        'Bɔ',
    'auth.welcome':       'I sɛrɛ bɔ — CodeRoute Gine',
    'auth.sign_in':       'I konto siga',

    'exam.title':         'Kɔntɔrɔli Kɛcogo',
    'exam.category':      'Wolo B',
    'exam.questions':     'ɲɛnɛnw',
    'exam.duration':      'Miniti 30',
    'exam.threshold':     'Cehol : 35/40',
    'exam.start':         'Kɔntɔrɔli Daminɛ',
    'exam.submit':        'Mɛ ci',
    'exam.next':          'Tɛmɛ',
    'exam.prev':          'Kɔ',
    'exam.skip':          'Tɛmɛ fɔlɔ',
    'exam.passed':        'Halaki ✓',
    'exam.failed':        'Mɔxɔ mɛ ✗',
    'exam.score':         'Limoore',
    'exam.time_left':     'Lɔxɔ Toomi',
    'exam.time_warning':  'Miniti 5 ma tɔ',
    'exam.time_critical': '⚠️ Lɔxɔ banna !',

    'training.title':     'Kalanɛ',
    'training.free':      'Kalanɛ Yɛrɛma',
    'training.series':    'Ɲɛnɛ Korow',
    'training.mock':      'Kɔntɔrɔli Haala',
    'training.progress':  'N Sɔrɔliw',
    'training.weak':      'Ko Baarikama',

    'domain.candidate':   'Nakɛɛmakɛɛ',
    'domain.center':      'Santara',
    'domain.session':     'Kɔntɔrɔli Lɔxɔ',
    'domain.booking':     'Tɔndi',
    'domain.payment':     'Seli',
    'domain.certificate': 'Sɛrtifi',
    'domain.result':      'Jɛtɛwal',
    'domain.score':       'Limoore',

    'status.passed':      'Halaki',
    'status.failed':      'Mɔxɔ mɛ',
    'status.pending':     'Ɲaxali',
    'status.paid':        'Selima',
    'status.active':      'Tɛngɛma',
    'status.verified':    'Dafama',

    'action.save':        'Mara',
    'action.cancel':      'Gafe',
    'action.confirm':     'Xɛrɛ',
    'action.download':    'Mɛ',
    'action.search':      'Xili',
    'action.validate':    'Xɛrɛ',
    'action.pay':         'Seli',
    'action.verify':      'Lajɛ',

    'payment.orange':     'Orange Money',
    'payment.mtn':        'MTN Money',
    'payment.wave':       'Wave',
    'payment.amount':     'Hakɛ (GNF)',
    'payment.phone':      'Telefɔni Nimɛrɔ',
    'payment.success':    'Seli Halaki ✓',

    'error.generic':      'Tɛ halaki',
    'error.network':      'Rezo tɛ',
    'error.auth':         'Lɔxɔ banna — siga kɔ',
    'error.not_found':    'Mɛ mɔxɔ',

    'info.loading':       'Ɲinini…',
    'info.no_data':       'Fɛn si tɛ',
    'info.success':       'Halaki ✓',
  },

  // ══════════════════════════════════════════════════════════════════
  // KISSI — Guinée forestière (N'Zérékoré, Kissidougou, Guéckédou)
  // Famille Niger-Congo, branche Mel
  // ══════════════════════════════════════════════════════════════════
  kss: {
    'nav.home':           'Taa Nde',
    'nav.candidate':      'Ŋwandi',
    'nav.center':         'Sandɛ',
    'nav.admin':          'Kɔmɔ',
    'nav.exam':           'Kɔntɔrɔli',
    'nav.results':        'Jɛtɛ',
    'nav.dossier':        'M Dɔsiye',
    'nav.training':       'Kalan',
    'nav.login':          'Siga',
    'nav.account':        'M Konto',
    'nav.logout':         'Bɔ',

    'auth.email':         'Imɛli',
    'auth.password':      'Yele',
    'auth.login':         'Siga',
    'auth.logout':        'Bɔ',
    'auth.welcome':       'Ɛ sɛrɛ — CodeRoute Gine',
    'auth.sign_in':       'I konto siga',

    'exam.title':         'Laɲini',
    'exam.category':      'Wolo B',
    'exam.questions':     'kɔnɛ',
    'exam.duration':      'Miniti 30',
    'exam.threshold':     'Cehol : 35/40',
    'exam.start':         'Laɲini Daminɛ',
    'exam.submit':        'Ci',
    'exam.next':          'Nɔ',
    'exam.prev':          'Kɔ',
    'exam.skip':          'Tɛmɛ',
    'exam.passed':        'Laaɓi ✓',
    'exam.failed':        'Tɛ ✗',
    'exam.score':         'Tɔgɔ',
    'exam.time_left':     'Waati Tɔmi',
    'exam.time_warning':  'Miniti 5 bɛ tɔ',
    'exam.time_critical': '⚠️ Waati banna !',

    'training.title':     'Kalan',
    'training.free':      'Kalan Yɛrɛ',
    'training.series':    'Kɔnɛ Koro',
    'training.mock':      'Laɲini Haala',
    'training.progress':  'N Taamaaw',
    'training.weak':      'Ko Gɛlɛnw',

    'domain.candidate':   'Ŋwandi',
    'domain.center':      'Sandɛ',
    'domain.session':     'Laɲini Loon',
    'domain.booking':     'Tɔndi',
    'domain.payment':     'Sara',
    'domain.certificate': 'Sɛrtifi',
    'domain.result':      'Jɛtɛ',
    'domain.score':       'Tɔgɔ',

    'status.passed':      'Laaɓi',
    'status.failed':      'Tɛ',
    'status.pending':     'Ɲaxali',
    'status.paid':        'Saralen',
    'status.active':      'Tɛngɛma',
    'status.verified':    'Dafalen',

    'action.save':        'Mara',
    'action.cancel':      'Dabɔ',
    'action.confirm':     'Dafa',
    'action.download':    'Kɔrɔ',
    'action.search':      'Ɲini',
    'action.validate':    'Dafa',
    'action.pay':         'Sara',
    'action.verify':      'Lajɛ',

    'payment.orange':     'Orange Money',
    'payment.mtn':        'MTN Money',
    'payment.wave':       'Wave',
    'payment.amount':     'Hakɛ (GNF)',
    'payment.phone':      'Telefɔni',
    'payment.success':    'Sara Kɛra ✓',

    'error.generic':      'Fili kɛra',
    'error.network':      'Rezo fili',
    'error.auth':         'Waktu banna — siga kɔ',
    'error.not_found':    'Tɛ sɔrɔ',

    'info.loading':       'Ɲinini…',
    'info.no_data':       'Fɛn si tɛ',
    'info.success':       'Kɛra ✓',
  },

  // ══════════════════════════════════════════════════════════════════
  // KPELLE / GUERZÉ — Guinée forestière (N'Zérékoré)
  // Famille Mandé du Sud
  // ══════════════════════════════════════════════════════════════════
  gkp: {
    'nav.home':           'Pɔlɔ',
    'nav.candidate':      'Kɔntɔrɔla',
    'nav.center':         'Sandɛ',
    'nav.admin':          'Kama',
    'nav.exam':           'Kɔntɔrɔli',
    'nav.results':        'Jɛtɛ',
    'nav.dossier':        'Ma Dɔsiye',
    'nav.training':       'Kalɛ',
    'nav.login':          'Siga',
    'nav.account':        'Ma Konto',
    'nav.logout':         'Bɔ',

    'auth.email':         'Imɛli',
    'auth.password':      'Yele',
    'auth.login':         'Siga',
    'auth.logout':        'Bɔ',
    'auth.welcome':       'Pɔlɔ — CodeRoute Gine',
    'auth.sign_in':       'Konto siga',

    'exam.title':         'Kɔntɔrɔli',
    'exam.category':      'Wolo B',
    'exam.questions':     'kɔnɛ',
    'exam.duration':      'Miniti 30',
    'exam.threshold':     'Cehol : 35/40',
    'exam.start':         'Kɔntɔrɔli Daminɛ',
    'exam.submit':        'Ci',
    'exam.next':          'Tɛmɛ',
    'exam.prev':          'Kɔ',
    'exam.skip':          'Fɔlɔ',
    'exam.passed':        'Sɔrɔlen ✓',
    'exam.failed':        'Tɛ ✗',
    'exam.score':         'Tɔgɔ',
    'exam.time_left':     'Waktu Tɔmi',
    'exam.time_warning':  'Miniti 5 bɛ tɔ',
    'exam.time_critical': '⚠️ Waktu banna !',

    'training.title':     'Kalɛ',
    'training.free':      'Kalɛ Yɛrɛ',
    'training.series':    'Kɔnɛ Koro',
    'training.mock':      'Kɔntɔrɔli Haala',
    'training.progress':  'N Taama',
    'training.weak':      'Ko Gɛlɛnw',

    'domain.candidate':   'Kɔntɔrɔla',
    'domain.center':      'Sandɛ',
    'domain.session':     'Kɔntɔrɔli Loon',
    'domain.booking':     'Tɔndi',
    'domain.payment':     'Sara',
    'domain.certificate': 'Sɛrtifi',
    'domain.result':      'Jɛtɛ',
    'domain.score':       'Tɔgɔ',

    'status.passed':      'Sɔrɔlen',
    'status.failed':      'Tɛ',
    'status.pending':     'Ɲaxali',
    'status.paid':        'Saralen',
    'status.active':      'Kɛlen',
    'status.verified':    'Dafalen',

    'action.save':        'Mara',
    'action.cancel':      'Dabɔ',
    'action.confirm':     'Dafa',
    'action.download':    'Kɔrɔ',
    'action.search':      'Ɲini',
    'action.validate':    'Dafa',
    'action.pay':         'Sara',
    'action.verify':      'Lajɛ',

    'payment.orange':     'Orange Money',
    'payment.mtn':        'MTN Money',
    'payment.wave':       'Wave',
    'payment.amount':     'Hakɛ (GNF)',
    'payment.phone':      'Telefɔni',
    'payment.success':    'Sara Kɛra ✓',

    'error.generic':      'Fili kɛra',
    'error.network':      'Rezo fili',
    'error.auth':         'Waktu banna — siga kɔ',
    'error.not_found':    'Tɛ sɔrɔ',

    'info.loading':       'Ɲinini…',
    'info.no_data':       'Fɛn si tɛ',
    'info.success':       'Kɛra ✓',
  },

  // ══════════════════════════════════════════════════════════════════
  // TOMA / LOMA — Guinée forestière (Macenta, Beyla, Guéckédou)
  // Famille Mandé du Sud
  // ══════════════════════════════════════════════════════════════════
  lom: {
    'nav.home':           'Taa',
    'nav.candidate':      'Ŋwandi',
    'nav.center':         'Sandɛ',
    'nav.admin':          'Kama',
    'nav.exam':           'Laɲini',
    'nav.results':        'Sɔrɔliw',
    'nav.dossier':        'N Dɔsiye',
    'nav.training':       'Kalan',
    'nav.login':          'Siga',
    'nav.account':        'N Konto',
    'nav.logout':         'Bɔ',

    'auth.email':         'Imɛli',
    'auth.password':      'Yele',
    'auth.login':         'Siga',
    'auth.logout':        'Bɔ',
    'auth.welcome':       'I sɛrɛ — CodeRoute Gine',
    'auth.sign_in':       'Konto siga',

    'exam.title':         'Laɲini',
    'exam.category':      'Wolo B',
    'exam.questions':     'kɔnɛ',
    'exam.duration':      'Miniti 30',
    'exam.threshold':     'Cehol : 35/40',
    'exam.start':         'Laɲini Daminɛ',
    'exam.submit':        'Ci',
    'exam.next':          'Nɔ',
    'exam.prev':          'Kɔ',
    'exam.skip':          'Tɛmɛ',
    'exam.passed':        'Laaɓi ✓',
    'exam.failed':        'Tɛ ✗',
    'exam.score':         'Tɔgɔ',
    'exam.time_left':     'Waktu',
    'exam.time_warning':  'Miniti 5 bɛ tɔ',
    'exam.time_critical': '⚠️ Waktu banna !',

    'training.title':     'Kalan',
    'training.free':      'Kalan Yɛrɛ',
    'training.series':    'Kɔnɛ Sira',
    'training.mock':      'Laɲini Haala',
    'training.progress':  'N Taamaaw',
    'training.weak':      'Ko Gɛlɛnw',

    'domain.candidate':   'Ŋwandi',
    'domain.center':      'Sandɛ',
    'domain.session':     'Laɲini Loon',
    'domain.booking':     'Tɔndi',
    'domain.payment':     'Sara',
    'domain.certificate': 'Sɛrtifi',
    'domain.result':      'Sɔrɔli',
    'domain.score':       'Tɔgɔ',

    'status.passed':      'Laaɓi',
    'status.failed':      'Tɛ',
    'status.pending':     'Ɲaxali',
    'status.paid':        'Saralen',
    'status.active':      'Kɛlen',
    'status.verified':    'Dafalen',

    'action.save':        'Mara',
    'action.cancel':      'Dabɔ',
    'action.confirm':     'Dafa',
    'action.download':    'Kɔrɔ',
    'action.search':      'Ɲini',
    'action.validate':    'Dafa',
    'action.pay':         'Sara',
    'action.verify':      'Lajɛ',

    'payment.orange':     'Orange Money',
    'payment.mtn':        'MTN Money',
    'payment.wave':       'Wave',
    'payment.amount':     'Hakɛ (GNF)',
    'payment.phone':      'Telefɔni',
    'payment.success':    'Sara Kɛra ✓',

    'error.generic':      'Fili kɛra',
    'error.network':      'Rezo fili',
    'error.auth':         'Waktu banna — siga kɔ',
    'error.not_found':    'Tɛ sɔrɔ',

    'info.loading':       'Ɲinini…',
    'info.no_data':       'Fɛn si tɛ',
    'info.success':       'Kɛra ✓',
  },

  // ══════════════════════════════════════════════════════════════════
  // ENGLISH — Administration internationale
  // ══════════════════════════════════════════════════════════════════
  en: {
    'nav.home':           'Home',
    'nav.candidate':      'Candidate Portal',
    'nav.center':         'Exam Center',
    'nav.admin':          'Administration',
    'nav.exam':           'Exam',
    'nav.results':        'Results',
    'nav.dossier':        'My File',
    'nav.training':       'Training',
    'nav.login':          'Sign in',
    'nav.account':        'My Account',
    'nav.logout':         'Sign out',

    'auth.email':         'Email address',
    'auth.password':      'Password',
    'auth.login':         'Sign in',
    'auth.logout':        'Sign out',
    'auth.welcome':       'Welcome to CodeRoute Guinea',
    'auth.sign_in':       'Sign in to your account',

    'exam.title':         'Official Exam',
    'exam.category':      'Category B',
    'exam.questions':     'questions',
    'exam.duration':      '30 minutes',
    'exam.threshold':     'Pass: 35/40',
    'exam.start':         'Start Exam',
    'exam.submit':        'Submit',
    'exam.next':          'Next',
    'exam.prev':          'Previous',
    'exam.skip':          'Skip',
    'exam.passed':        'Passed ✓',
    'exam.failed':        'Failed ✗',
    'exam.score':         'Score',
    'exam.time_left':     'Time remaining',
    'exam.time_warning':  'Less than 5 minutes',
    'exam.time_critical': '⚠️ Time almost up!',

    'training.title':     'Training',
    'training.free':      'Free Mode',
    'training.series':    'Topic Series',
    'training.mock':      'Mock Exam',
    'training.progress':  'My Progress',
    'training.weak':      'Areas to Improve',

    'domain.candidate':   'Candidate',
    'domain.center':      'Accredited center',
    'domain.session':     'Exam session',
    'domain.booking':     'Booking',
    'domain.payment':     'Payment',
    'domain.certificate': 'Certificate',
    'domain.result':      'Result',
    'domain.score':       'Score',

    'status.passed':      'Passed',
    'status.failed':      'Failed',
    'status.pending':     'Pending',
    'status.paid':        'Paid',
    'status.active':      'Active',
    'status.verified':    'Verified',

    'action.save':        'Save',
    'action.cancel':      'Cancel',
    'action.confirm':     'Confirm',
    'action.download':    'Download',
    'action.search':      'Search',
    'action.validate':    'Validate',
    'action.pay':         'Pay',
    'action.verify':      'Verify',

    'payment.orange':     'Orange Money',
    'payment.mtn':        'MTN Money',
    'payment.wave':       'Wave',
    'payment.amount':     'Amount (GNF)',
    'payment.phone':      'Phone number',
    'payment.success':    'Payment confirmed ✓',

    'error.generic':      'An error occurred',
    'error.network':      'Connection error',
    'error.auth':         'Session expired — please sign in again',
    'error.not_found':    'Resource not found',

    'info.loading':       'Loading…',
    'info.no_data':       'No data available',
    'info.success':       'Success ✓',
  },
};

// ── État global ────────────────────────────────────────────────────────────

const KEY = 'cr-locale';
const DEFAULT: Locale = 'fr';

function detectLocale(): Locale {
  try {
    const stored = localStorage.getItem(KEY) as Locale | null;
    if (stored && SUPPORTED_LOCALES.some(l => l.code === stored)) return stored;
    const browser = navigator.language.toLowerCase().split('-')[0];
    const map: Record<string, Locale> = {
      fr: 'fr', en: 'en', ff: 'ff', ful: 'ff', man: 'man', sus: 'sus',
      kss: 'kss', gkp: 'gkp', lom: 'lom',
    };
    return map[browser] ?? DEFAULT;
  } catch { return DEFAULT; }
}

let _locale: Locale = detectLocale();
const _listeners = new Set<() => void>();

export function getLocale(): Locale { return _locale; }

export function setLocale(locale: Locale): void {
  _locale = locale;
  try { localStorage.setItem(KEY, locale); } catch {}
  _listeners.forEach(fn => fn());
}

export function onLocaleChange(fn: () => void): () => void {
  _listeners.add(fn);
  return () => _listeners.delete(fn);
}

// ── Traduction ─────────────────────────────────────────────────────────────

export function t(key: string, fallback?: string): string {
  const dict = translations[_locale] ?? translations[DEFAULT];
  if (dict[key]) return dict[key];
  if (_locale !== DEFAULT && translations[DEFAULT][key]) return translations[DEFAULT][key];
  return fallback ?? key;
}

// ── Hook React ─────────────────────────────────────────────────────────────

import { useState, useEffect } from 'react';

export function useLocale() {
  const [locale, setLocaleState] = useState<Locale>(_locale);
  useEffect(() => onLocaleChange(() => setLocaleState(getLocale())), []);
  return {
    locale,
    setLocale(next: Locale) { setLocale(next); setLocaleState(next); },
    t,
  };
}
