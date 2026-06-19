/**
 * Système i18n léger pour CodeRoute Guinée.
 * Supporte : Français (fr), Pular/Fula (ff), Malinké (man), Soussou (sus), Anglais (en)
 *
 * Usage :
 *   import { t, setLocale, useLocale } from './i18n';
 *   t('nav.login')          → "Connexion" (fr)
 *   setLocale('ff')         → passe en Pular
 */

export type Locale = 'fr' | 'ff' | 'man' | 'sus' | 'en';

export const SUPPORTED_LOCALES: { code: Locale; label: string; native: string }[] = [
  { code: 'fr',  label: 'Français',  native: 'Français' },
  { code: 'ff',  label: 'Pular',     native: 'Pulaar' },
  { code: 'man', label: 'Malinké',   native: 'Mandinkakan' },
  { code: 'sus', label: 'Soussou',   native: 'Sosoxui' },
  { code: 'en',  label: 'English',   native: 'English' },
];

// ── Dictionnaire principal ─────────────────────────────────────────────────

type TranslationMap = Record<string, string>;
type Translations = Record<Locale, TranslationMap>;

const translations: Translations = {
  fr: {
    // Navigation
    'nav.home':        'Accueil',
    'nav.candidate':   'Espace candidat',
    'nav.center':      'Espace centre',
    'nav.admin':       'Administration',
    'nav.exam':        'Examen',
    'nav.results':     'Résultats',
    'nav.dossier':     'Mon dossier',
    'nav.login':       'Connexion',
    'nav.account':     'Mon compte',
    'nav.logout':      'Déconnexion',

    // Auth
    'auth.email':      'Adresse e-mail',
    'auth.password':   'Mot de passe',
    'auth.login':      'Se connecter',
    'auth.logout':     'Se déconnecter',
    'auth.role':       'Rôle',
    'auth.welcome':    'Bienvenue sur CodeRoute Guinée',

    // Domaine
    'domain.candidate':    'Candidat',
    'domain.center':       'Centre agréé',
    'domain.session':      'Session d\'examen',
    'domain.booking':      'Réservation',
    'domain.exam':         'Examen',
    'domain.payment':      'Paiement',
    'domain.certificate':  'Certificat',
    'domain.question':     'Question',
    'domain.result':       'Résultat',
    'domain.score':        'Score',

    // Status
    'status.passed':   'Admis',
    'status.failed':   'Ajourné',
    'status.pending':  'En attente',
    'status.paid':     'Payé',
    'status.active':   'Actif',

    // Actions
    'action.save':     'Enregistrer',
    'action.cancel':   'Annuler',
    'action.confirm':  'Confirmer',
    'action.download': 'Télécharger',
    'action.search':   'Rechercher',
    'action.filter':   'Filtrer',
    'action.export':   'Exporter',
    'action.import':   'Importer',

    // Mobile Money
    'payment.orange':  'Orange Money',
    'payment.mtn':     'MTN Money',
    'payment.amount':  'Montant (GNF)',
    'payment.phone':   'Numéro de téléphone',

    // Erreurs
    'error.generic':   'Une erreur s\'est produite',
    'error.network':   'Erreur de connexion',
    'error.auth':      'Session expirée, veuillez vous reconnecter',
    'error.notfound':  'Ressource introuvable',
  },

  ff: {
    // Navigation — Pular/Fulfulde
    'nav.home':        'Suudu Mawdo',
    'nav.candidate':   'Jaŋtorde Calonke',
    'nav.center':      'Jaŋtorde Laamorde',
    'nav.admin':       'Binndi-Laamu',
    'nav.exam':        'Janngirde',
    'nav.results':     'Jaabawuuji',
    'nav.dossier':     'Dosiye Am',
    'nav.login':       'Naatde',
    'nav.account':     'Ñoɓirde Am',
    'nav.logout':      'Yaltude',

    // Auth
    'auth.email':      'Iimeel',
    'auth.password':   'Finaa-tawaa',
    'auth.login':      'Naatde',
    'auth.logout':     'Yaltude',
    'auth.role':       'Gonɗi',
    'auth.welcome':    'Bismillaa to CodeRoute Gine',

    // Domaine
    'domain.candidate':    'Calonke',
    'domain.center':       'Laamorɗe',
    'domain.session':      'Janngirde-Waktu',
    'domain.booking':      'Muuɗtaade',
    'domain.exam':         'Janngirde',
    'domain.payment':      'Liggorde',
    'domain.certificate':  'Takkaare',
    'domain.question':     'Faayidaare',
    'domain.result':       'Jaabawal',
    'domain.score':        'Limoore',

    // Status
    'status.passed':   'Laaɓi',
    'status.failed':   'Waylaaki',
    'status.pending':  'Ɗowtiiɗo',
    'status.paid':     'Liggaama',
    'status.active':   'Hollitiima',

    // Actions
    'action.save':     'Dannude',
    'action.cancel':   'Haɗde',
    'action.confirm':  'Siftorde',
    'action.download': 'Aawde',
    'action.search':   'Yiylude',
    'action.filter':   'Suɓude',
    'action.export':   'Yaltinde',
    'action.import':   'Naatinde',

    // Mobile Money
    'payment.orange':  'Orange Money',
    'payment.mtn':     'MTN Money',
    'payment.amount':  'Limoore (GNF)',
    'payment.phone':   'Nimero Telefoon',

    // Erreurs
    'error.generic':   'Juumre waɗii',
    'error.network':   'Juumre Reseŋ',
    'error.auth':      'Waktu yalti, naatid kadi',
    'error.notfound':  'Laaɓaani',
  },

  man: {
    // Navigation — Malinké/Mandinka
    'nav.home':        'So Kɔrɔ',
    'nav.candidate':   'Kuntigibaaɲɔgɔn',
    'nav.center':      'Senfɛlabaa',
    'nav.admin':       'Kuntigi',
    'nav.exam':        'Sɛgɛsɛgɛli',
    'nav.results':     'Lajɛlennw',
    'nav.dossier':     'N ka Dosiye',
    'nav.login':       'Dɔn',
    'nav.account':     'N ka Kɔnɔ',
    'nav.logout':      'Bɔ',

    // Auth
    'auth.email':      'Imɛli',
    'auth.password':   'Gundo',
    'auth.login':      'Dɔn',
    'auth.logout':     'Bɔ',
    'auth.role':       'Baara',
    'auth.welcome':    'Aw ni ce CodeRoute Gine',

    // Domaine
    'domain.candidate':    'Kuntigibaaw',
    'domain.center':       'Senfɛlabaa',
    'domain.session':      'Sɛgɛsɛgɛli Loon',
    'domain.booking':      'Sɛnbɔ',
    'domain.exam':         'Sɛgɛsɛgɛli',
    'domain.payment':      'Sara',
    'domain.certificate':  'Maratigɛ',
    'domain.question':     'Ɲininkali',
    'domain.result':       'Lajɛlen',
    'domain.score':        'Tɔgɔtɔgɔ',

    // Status
    'status.passed':   'Sɔrɔlen',
    'status.failed':   'Tɛ',
    'status.pending':  'Kɔnɔ',
    'status.paid':     'Saralen',
    'status.active':   'Kɛlen',

    // Actions
    'action.save':     'Mara',
    'action.cancel':   'Dabɔ',
    'action.confirm':  'Dafa',
    'action.download': 'Kɔrɔ',
    'action.search':   'Ɲini',
    'action.filter':   'Filɛ',
    'action.export':   'Bɔ',
    'action.import':   'Dɔn',

    // Mobile Money
    'payment.orange':  'Orange Money',
    'payment.mtn':     'MTN Money',
    'payment.amount':  'Hakɛ (GNF)',
    'payment.phone':   'Telefɔni Nimɔrɔ',

    // Erreurs
    'error.generic':   'Fili dɔ kɛra',
    'error.network':   'Rezo fili',
    'error.auth':      'Loon banna, dɔn kɔ',
    'error.notfound':  'Tɛ sɔrɔ',
  },

  sus: {
    // Navigation — Soussou
    'nav.home':        'Bande Fɔlɔ',
    'nav.candidate':   'Nakɛɛmakɛɛ',
    'nav.center':      'Santara',
    'nav.admin':       'Kuntigi',
    'nav.exam':        'Kɔntɔrɔli',
    'nav.results':     'Jɛtɛwali',
    'nav.dossier':     'N Dɔsiye',
    'nav.login':       'Siga',
    'nav.account':     'N Konto',
    'nav.logout':      'Bɔ',

    // Auth
    'auth.email':      'Imɛli',
    'auth.password':   'Sɛkɛrɛ',
    'auth.login':      'Siga',
    'auth.logout':     'Bɔ',
    'auth.role':       'Baarataa',
    'auth.welcome':    'I sɛrɛ bɔ CodeRoute Gine',

    // Domaine
    'domain.candidate':    'Nakɛɛmakɛɛ',
    'domain.center':       'Santara',
    'domain.session':      'Kɔntɔrɔli Lɔxɔ',
    'domain.booking':      'Tɔndi',
    'domain.exam':         'Kɔntɔrɔli',
    'domain.payment':      'Seli',
    'domain.certificate':  'Sɛrtifi',
    'domain.question':     'Ɲɛnɛ',
    'domain.result':       'Jɛtɛwal',
    'domain.score':        'Limoore',

    // Status
    'status.passed':   'Halaki',
    'status.failed':   'Mɔxɔ mɛ',
    'status.pending':  'Ɲaxali',
    'status.paid':     'Selima',
    'status.active':   'Tɛngɛma',

    // Actions
    'action.save':     'Mara',
    'action.cancel':   'Gafe',
    'action.confirm':  'Xɛrɛ',
    'action.download': 'Mɛ',
    'action.search':   'Xili',
    'action.filter':   'Tɛmɛya',
    'action.export':   'Bɔ',
    'action.import':   'Siga',

    // Mobile Money
    'payment.orange':  'Orange Money',
    'payment.mtn':     'MTN Money',
    'payment.amount':  'Hakɛ (GNF)',
    'payment.phone':   'Telefɔni Nimɛrɔ',

    // Erreurs
    'error.generic':   'Tɛ halaki',
    'error.network':   'Rezo tɛ',
    'error.auth':      'Lɔxɔ lɔxɔ, siga kɔ',
    'error.notfound':  'Mɛ mɔxɔ',
  },

  en: {
    // Navigation
    'nav.home':        'Home',
    'nav.candidate':   'Candidate Portal',
    'nav.center':      'Center Portal',
    'nav.admin':       'Administration',
    'nav.exam':        'Exam',
    'nav.results':     'Results',
    'nav.dossier':     'My File',
    'nav.login':       'Login',
    'nav.account':     'My Account',
    'nav.logout':      'Logout',

    // Auth
    'auth.email':      'Email address',
    'auth.password':   'Password',
    'auth.login':      'Sign in',
    'auth.logout':     'Sign out',
    'auth.role':       'Role',
    'auth.welcome':    'Welcome to CodeRoute Guinea',

    // Domaine
    'domain.candidate':    'Candidate',
    'domain.center':       'Accredited center',
    'domain.session':      'Exam session',
    'domain.booking':      'Booking',
    'domain.exam':         'Exam',
    'domain.payment':      'Payment',
    'domain.certificate':  'Certificate',
    'domain.question':     'Question',
    'domain.result':       'Result',
    'domain.score':        'Score',

    // Status
    'status.passed':   'Passed',
    'status.failed':   'Failed',
    'status.pending':  'Pending',
    'status.paid':     'Paid',
    'status.active':   'Active',

    // Actions
    'action.save':     'Save',
    'action.cancel':   'Cancel',
    'action.confirm':  'Confirm',
    'action.download': 'Download',
    'action.search':   'Search',
    'action.filter':   'Filter',
    'action.export':   'Export',
    'action.import':   'Import',

    // Mobile Money
    'payment.orange':  'Orange Money',
    'payment.mtn':     'MTN Money',
    'payment.amount':  'Amount (GNF)',
    'payment.phone':   'Phone number',

    // Erreurs
    'error.generic':   'An error occurred',
    'error.network':   'Connection error',
    'error.auth':      'Session expired, please log in again',
    'error.notfound':  'Resource not found',
  },
};

// ── État global de la locale ───────────────────────────────────────────────

const LOCALE_STORAGE_KEY = 'coderoute-locale';
const DEFAULT_LOCALE: Locale = 'fr';

function detectBrowserLocale(): Locale {
  const browser = (navigator.language || 'fr').toLowerCase().split('-')[0];
  const map: Record<string, Locale> = {
    fr: 'fr', en: 'en', ff: 'ff', ful: 'ff', man: 'man', sus: 'sus',
  };
  return map[browser] ?? DEFAULT_LOCALE;
}

let _currentLocale: Locale = (() => {
  try {
    const stored = localStorage.getItem(LOCALE_STORAGE_KEY) as Locale | null;
    if (stored && SUPPORTED_LOCALES.some((l) => l.code === stored)) return stored;
    return detectBrowserLocale();
  } catch {
    return DEFAULT_LOCALE;
  }
})();

const _listeners: Set<() => void> = new Set();

export function getLocale(): Locale {
  return _currentLocale;
}

export function setLocale(locale: Locale): void {
  _currentLocale = locale;
  try {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale);
  } catch {}
  _listeners.forEach((fn) => fn());
}

export function onLocaleChange(fn: () => void): () => void {
  _listeners.add(fn);
  return () => _listeners.delete(fn);
}

// ── Fonction de traduction principale ─────────────────────────────────────

export function t(key: string, fallback?: string): string {
  const dict = translations[_currentLocale] ?? translations[DEFAULT_LOCALE];
  if (dict[key]) return dict[key];
  // Fallback sur français si clé absente dans la locale cible
  if (_currentLocale !== DEFAULT_LOCALE && translations[DEFAULT_LOCALE][key]) {
    return translations[DEFAULT_LOCALE][key];
  }
  return fallback ?? key;
}

// ── Hook React ─────────────────────────────────────────────────────────────

export function useLocale(): { locale: Locale; setLocale: typeof setLocale; t: typeof t } {
  const [locale, setLocaleState] = useState<Locale>(_currentLocale);

  useEffect(() => {
    return onLocaleChange(() => setLocaleState(getLocale()));
  }, []);

  return {
    locale,
    setLocale(next: Locale) {
      setLocale(next);
      setLocaleState(next);
    },
    t,
  };
}

// Import React hooks pour le hook useLocale
import { useState, useEffect } from 'react';
