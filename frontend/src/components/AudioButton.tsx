/**
 * Composants audio réutilisables — CodeRoute Guinée
 */
import { useEffect, useRef, useState } from 'react';
import {
  getAudioEnabled, isAudioLocale, isTTSAvailable,
  playQuestionAudio, preloadVoices, setAudioEnabled, speak, speakQuestion, stop,
} from '../audio';
import { useLocale, SUPPORTED_LOCALES, type Locale } from '../i18n';

// ── Bouton lecture question ────────────────────────────────────────

interface PlayButtonProps {
  text: string;
  options?: string[];
  size?: number;
  rate?: number;
  /** ID de la question pour chercher un MP3 pré-enregistré */
  questionId?: string;
  /** Locale pour le fichier MP3 (/audio/{locale}/{questionId}.mp3) */
  locale?: string;
}

export function PlayButton({ text, options = [], size = 36, rate, questionId, locale }: PlayButtonProps) {
  const [playing, setPlaying] = useState(false);

  function handleClick() {
    if (playing) {
      stop();
      setPlaying(false);
      return;
    }
    setPlaying(true);
    const ms = Math.max(4000, (text.length + options.join('').length) * 75);
    setTimeout(() => setPlaying(false), ms);

    // Priorité 1 : MP3 pré-enregistré si questionId + locale fournis
    if (questionId && locale) {
      playQuestionAudio(questionId, locale as import('../i18n').Locale, text, options)
        .catch(() => {});
      return;
    }
    // Priorité 2 : TTS (fallback universel)
    if (options.length > 0) {
      speakQuestion(text, options, { rate });
    } else {
      speak(text, { rate: rate ?? 0.88, priority: true, onEnd: () => setPlaying(false) });
    }
  }

  if (!isTTSAvailable()) return null;

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-label={playing ? 'Arrêter la lecture' : 'Écouter la question'}
      title={playing ? 'Arrêter' : 'Écouter'}
      style={{
        width: size, height: size,
        borderRadius: '50%',
        border: `1.5px solid ${playing ? 'var(--blue)' : 'var(--border)'}`,
        background: playing ? 'var(--blue-l)' : 'transparent',
        color: playing ? 'var(--blue)' : 'var(--muted)',
        cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: size * 0.44,
        flexShrink: 0,
        transition: 'all .15s',
      }}
    >
      {playing ? '⏹' : '🔊'}
    </button>
  );
}

// ── Bouton muet global ────────────────────────────────────────────

export function AudioToggle() {
  const [enabled, setEnabled] = useState(getAudioEnabled);

  function toggle() {
    const next = !enabled;
    setAudioEnabled(next);
    setEnabled(next);
  }

  if (!isTTSAvailable()) return null;

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={enabled ? 'Désactiver le son' : 'Activer le son'}
      title={enabled ? 'Muet' : 'Activer le son'}
      style={{
        padding: '4px 10px',
        borderRadius: 20,
        border: '1px solid var(--border)',
        background: 'transparent',
        color: enabled ? 'var(--ink2)' : 'var(--muted)',
        cursor: 'pointer',
        fontSize: 13,
        display: 'flex', alignItems: 'center', gap: 5,
        minHeight: 'unset',
      }}
    >
      {enabled ? '🔊' : '🔇'}
      <span style={{ fontSize: 11 }}>{enabled ? 'Son ON' : 'Son OFF'}</span>
    </button>
  );
}

// ── Banner mode audio (affiché quand locale = langue nationale) ───

export function AudioModeBanner() {
  const { locale } = useLocale();
  const [visible, setVisible] = useState(false);
  const [ttsOk, setTtsOk] = useState(false);

  useEffect(() => {
    if (!isAudioLocale(locale as Locale)) { setVisible(false); return; }
    setVisible(true);
    preloadVoices().then(() => setTtsOk(isTTSAvailable()));
  }, [locale]);

  if (!visible) return null;

  const localeName = SUPPORTED_LOCALES.find(l => l.code === locale)?.native ?? locale;

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        background: 'var(--blue-l)',
        border: '1px solid #bfdbfe',
        borderRadius: 'var(--r-lg)',
        padding: '10px 14px',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        fontSize: 13,
        marginBottom: 12,
      }}
    >
      <span style={{ fontSize: 20 }}>🔊</span>
      <div style={{ flex: 1 }}>
        <strong style={{ color: 'var(--blue)', display: 'block', marginBottom: 2 }}>
          Mode audio — {localeName}
        </strong>
        <span style={{ color: 'var(--ink2)', fontSize: 12 }}>
          {ttsOk
            ? 'Appuyez sur 🔊 pour écouter chaque question et ses réponses à voix haute.'
            : 'Audio non disponible sur ce navigateur. Questions affichées en français.'}
        </span>
      </div>
      {ttsOk && <AudioToggle />}
    </div>
  );
}

// ── Sélecteur de langue avec badge audio ─────────────────────────

export function LocaleAudioSwitcher() {
  const { locale, setLocale } = useLocale();

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
        gap: 8,
      }}
    >
      {SUPPORTED_LOCALES.map(l => {
        const isNative = isAudioLocale(l.code as Locale);
        const selected = locale === l.code;
        return (
          <button
            key={l.code}
            type="button"
            onClick={() => setLocale(l.code as Locale)}
            aria-pressed={selected}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-start',
              padding: '10px 13px',
              border: `2px solid ${selected ? 'var(--blue)' : 'var(--border)'}`,
              borderRadius: 'var(--r-lg)',
              background: selected ? 'var(--blue-l)' : 'var(--bg)',
              cursor: 'pointer',
              minHeight: 'unset',
              color: 'var(--ink)',
              transition: 'all .15s',
              textAlign: 'left',
            }}
          >
            {/* Badge audio ou texte */}
            <div
              style={{
                fontSize: 10,
                fontWeight: 700,
                padding: '2px 6px',
                borderRadius: 10,
                marginBottom: 5,
                background: isNative ? '#fef9c3' : 'var(--bg)',
                color: isNative ? '#854d0e' : 'var(--muted)',
                border: isNative ? '1px solid #fde68a' : '1px solid var(--border)',
              }}
            >
              {isNative ? '🔊 Audio' : '📝 Texte'}
            </div>
            <span style={{ fontWeight: 700, fontSize: 14, color: selected ? 'var(--blue)' : 'var(--ink)' }}>
              {l.native}
            </span>
            <span style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
              {l.label} · {l.region}
            </span>
          </button>
        );
      })}
    </div>
  );
}
