/**
 * Moteur audio CodeRoute Guinée
 *
 * Architecture :
 *   - fr / en  → interface écrite normale (pas de TTS auto)
 *   - ff / man / sus / kss / gkp / lom → audio obligatoire pour :
 *       • questions d'examen
 *       • options de réponse
 *       • feedback (correct / incorrect)
 *       • navigation (suivante, précédente, soumettre)
 *
 * Implémentation :
 *   Niveau 1 — Web Speech API (SpeechSynthesis) : disponible sur 95% des mobiles Android.
 *              Utilise la voix "fr-FR" comme base (les langues nationales
 *              n'ont pas de voix dédiées dans les navigateurs actuels).
 *              Le texte lu est la VERSION FRANÇAISE — l'utilisateur entend le français
 *              prononcé, mais l'UI affiche l'identification dans sa langue nationale.
 *
 *   Niveau 2 — Fichiers audio pré-enregistrés (futur Phase 2) :
 *              Quand des locuteurs natifs enregistrent les questions,
 *              remplacer speak() par playAudioFile(questionId, locale).
 *              Structure prévue : /audio/{locale}/{question_id}.mp3
 *
 * Choix de conception :
 *   Les langues nationales de Guinée (Pular, Malinké, Soussou, Kissi, Kpelle, Toma)
 *   n'ont pas de standard d'écriture largement répandu. L'interface textuelle
 *   reste en français pour la clarté visuelle ; l'audio permet à l'utilisateur
 *   d'entendre la question dans un format accessible même sans alphabétisation.
 */

import { type Locale, getLocale } from './i18n';

// Locales qui nécessitent l'audio pour l'accès aux questions
export const AUDIO_LOCALES: Locale[] = ['ff', 'man', 'sus', 'kss', 'gkp', 'lom'];

// Locales avec interface écrite (fr et en gardent l'interface textuelle normale)
export const TEXT_LOCALES: Locale[] = ['fr', 'en'];

/** Retourne true si la locale active nécessite le mode audio */
export function isAudioLocale(locale?: Locale): boolean {
  return AUDIO_LOCALES.includes(locale ?? getLocale());
}

// ── TTS Engine ────────────────────────────────────────────────────

let _utterance: SpeechSynthesisUtterance | null = null;
let _enabled = true;

/** Vérifie si la synthèse vocale est disponible sur ce navigateur */
export function isTTSAvailable(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window;
}

/** Active ou désactive le TTS (bouton muet) */
export function setAudioEnabled(enabled: boolean): void {
  _enabled = enabled;
  if (!enabled) stop();
  try { localStorage.setItem('cr-audio-enabled', enabled ? '1' : '0'); } catch {}
}

/** Lit l'état audio depuis localStorage */
export function getAudioEnabled(): boolean {
  try { return localStorage.getItem('cr-audio-enabled') !== '0'; } catch { return true; }
}

/**
 * Lit un texte à voix haute.
 *
 * @param text      Texte à lire (toujours en français — base commune)
 * @param options   rate : vitesse (0.7 = lent, 1.0 = normal), priority : interrompt si true
 */
export function speak(
  text: string,
  options: { rate?: number; priority?: boolean; onEnd?: () => void } = {}
): void {
  if (!isTTSAvailable() || !_enabled) {
    options.onEnd?.();
    return;
  }

  const { rate = 0.85, priority = false, onEnd } = options;

  // Interrompre la lecture en cours si prioritaire
  if (priority || window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel();
  }

  // Petit délai pour laisser cancel() prendre effet
  setTimeout(() => {
    const utt = new SpeechSynthesisUtterance(text);

    // Utiliser une voix française disponible
    const voices = window.speechSynthesis.getVoices();
    const frVoice = voices.find(v => v.lang.startsWith('fr')) ??
                    voices.find(v => v.lang.startsWith('fr-FR')) ??
                    voices[0] ?? null;
    if (frVoice) utt.voice = frVoice;

    utt.lang  = 'fr-FR';
    utt.rate  = rate;
    utt.pitch = 1.0;
    utt.volume = 1.0;

    if (onEnd) utt.onend = onEnd;

    _utterance = utt;
    window.speechSynthesis.speak(utt);
  }, priority ? 150 : 0);
}

/** Arrête la lecture en cours */
export function stop(): void {
  if (isTTSAvailable()) window.speechSynthesis.cancel();
  _utterance = null;
}

/** Lit une question complète : texte + options (séquentiellement) */
export function speakQuestion(
  text: string,
  options: string[],
  opts: { rate?: number } = {}
): void {
  if (!isTTSAvailable() || !_enabled) return;

  stop();
  const letters = ['A', 'B', 'C', 'D'];
  const full = [
    text,
    ...options.map((opt, i) => `${letters[i]}. ${opt}`),
  ].join('. ');

  speak(full, { rate: opts.rate ?? 0.82, priority: true });
}

/** Lit le feedback après une réponse */
export function speakFeedback(
  correct: boolean,
  explanation?: string
): void {
  if (!isTTSAvailable() || !_enabled) return;
  const msg = correct
    ? 'Bonne réponse !'
    : `Mauvaise réponse. ${explanation ?? ''}`;
  speak(msg, { rate: 0.88, priority: true });
}

/** Lit une option individuelle au survol/focus */
export function speakOption(letter: string, text: string): void {
  if (!isTTSAvailable() || !_enabled) return;
  speak(`${letter}. ${text}`, { rate: 0.9, priority: true });
}

// ── Préchargement des voix ────────────────────────────────────────
// Les navigateurs chargent la liste des voix de façon asynchrone

let _voicesLoaded = false;

export function preloadVoices(): Promise<void> {
  if (_voicesLoaded || !isTTSAvailable()) return Promise.resolve();
  return new Promise(resolve => {
    const voices = window.speechSynthesis.getVoices();
    if (voices.length > 0) { _voicesLoaded = true; resolve(); return; }
    window.speechSynthesis.addEventListener('voiceschanged', () => {
      _voicesLoaded = true;
      resolve();
    }, { once: true });
    // Fallback si voiceschanged ne se déclenche pas
    setTimeout(resolve, 1500);
  });
}

// ── Audio pré-enregistré (Phase 2) ───────────────────────────────

/**
 * Joue l'enregistrement d'une question par un locuteur natif, avec repli
 * automatique sur la synthèse vocale.
 *
 * Deux sources possibles, dans l'ordre :
 *   1. audioUrl fourni par le backend (traduction : translations[locale].audio_url).
 *      Permet d'héberger les enregistrements n'importe où (Cloudinary, CDN…).
 *   2. Convention de chemin : /audio/{locale}/{questionId}.mp3
 *
 * Si aucun enregistrement n'est disponible ou lisible, on retombe sur la
 * synthèse vocale : aucune question n'est jamais muette.
 *
 * Entendre sa VRAIE langue (et non du français prononcé) est déterminant
 * pour les candidats qui parlent Pular, Malinké ou Soussou sans les lire.
 */
export async function playQuestionAudio(
  questionId: string,
  locale: Locale,
  fallbackText: string,
  fallbackOptions: string[],
  audioUrl?: string | null,
): Promise<void> {
  if (!_enabled) return;
  stop(); // couper une synthèse vocale en cours

  const candidates = [
    audioUrl || null,                          // 1. URL fournie par le backend
    `/audio/${locale}/${questionId}.mp3`,      // 2. convention de chemin
  ].filter(Boolean) as string[];

  for (const url of candidates) {
    try {
      const audio = new Audio(url);
      // play() rejette si le fichier est absent/illisible → on essaie le suivant
      await audio.play();
      return;
    } catch {
      // Source indisponible → candidat suivant
    }
  }

  // Repli final : synthèse vocale
  speakQuestion(fallbackText, fallbackOptions);
}

// ── Initialisation ────────────────────────────────────────────────
// Initialiser l'état audio depuis localStorage
if (typeof window !== 'undefined') {
  _enabled = getAudioEnabled();
  preloadVoices().catch(() => {});
}
