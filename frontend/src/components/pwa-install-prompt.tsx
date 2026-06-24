/**
 * InstallPWA — Banner d'installation de l'app
 * Apparaît quand le navigateur est prêt à installer (beforeinstallprompt)
 * Disparaît pendant 7 jours après un refus
 */
'use client';
import { useState, useEffect } from 'react';

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

const DISMISS_KEY   = 'pwa-install-dismissed-at';
const DISMISS_TTL   = 1000 * 60 * 60 * 24 * 7; // 7 jours

export function InstallPWA() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible]               = useState(false);

  useEffect(() => {
    // Déjà installé (mode standalone)
    if (window.matchMedia('(display-mode: standalone)').matches) return;
    if ((navigator as unknown as { standalone?: boolean }).standalone === true) return;

    // Refus récent
    const dismissed = Number(localStorage.getItem(DISMISS_KEY) || 0);
    if (dismissed && Date.now() - dismissed < DISMISS_TTL) return;

    const onPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setVisible(true);
    };

    window.addEventListener('beforeinstallprompt', onPrompt);
    return () => window.removeEventListener('beforeinstallprompt', onPrompt);
  }, []);

  if (!visible || !deferredPrompt) return null;

  async function handleInstall() {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const choice = await deferredPrompt.userChoice;
    if (choice.outcome === 'dismissed') {
      localStorage.setItem(DISMISS_KEY, String(Date.now()));
    }
    setDeferredPrompt(null);
    setVisible(false);
  }

  function handleDismiss() {
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
    setVisible(false);
  }

  return (
    <div style={{
      position: 'fixed', bottom: 16, left: 16, right: 16, zIndex: 9999,
      background: '#006B3F', color: '#fff',
      borderRadius: 12, padding: '14px 16px',
      display: 'flex', alignItems: 'center', gap: 12,
      boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
      maxWidth: 420, margin: '0 auto',
    }}>
      {/* Drapeau Guinée */}
      <div style={{ display: 'flex', borderRadius: 4, overflow: 'hidden', flexShrink: 0 }}>
        <div style={{ width: 8, height: 32, background: '#CE1126' }} />
        <div style={{ width: 8, height: 32, background: '#FCD116' }} />
        <div style={{ width: 8, height: 32, background: '#009460' }} />
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 700, fontSize: 14 }}>Installer CodeRoute</div>
        <div style={{ fontSize: 12, opacity: 0.85 }}>
          Accédez à l'application sans connexion
        </div>
      </div>

      <button
        onClick={handleInstall}
        style={{
          background: 'var(--gold, #FCD116)', color: 'var(--ink, #000)', border: 'none',
          borderRadius: 8, padding: '8px 14px', fontWeight: 700,
          fontSize: 13, cursor: 'pointer', flexShrink: 0,
        }}
      >
        Installer
      </button>
      <button
        onClick={handleDismiss}
        style={{
          background: 'none', border: 'none', color: '#fff',
          fontSize: 20, cursor: 'pointer', lineHeight: 1, padding: 4,
          flexShrink: 0,
        }}
        aria-label="Fermer"
      >
        ×
      </button>
    </div>
  );
}
