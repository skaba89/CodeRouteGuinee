/**
 * ThemeToggle — Bouton bascule Clair/Sombre
 * Persiste la préférence dans localStorage
 * Applique la classe "dark" sur <html>
 */
import { useState, useEffect } from 'react';

const STORAGE_KEY = 'coderoute-theme';

function getInitialTheme(): 'light' | 'dark' {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'dark' || stored === 'light') return stored;
    // Respecter la préférence système
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
  } catch { /* SSR ou cookies bloqués */ }
  return 'light';
}

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const initial = getInitialTheme();
    setTheme(initial);
    applyTheme(initial);
    setMounted(true);
  }, []);

  function applyTheme(t: 'light' | 'dark') {
    const root = document.documentElement;
    if (t === 'dark') {
      root.classList.add('dark');
      root.setAttribute('data-theme', 'dark');
    } else {
      root.classList.remove('dark');
      root.setAttribute('data-theme', 'light');
    }
    try { localStorage.setItem(STORAGE_KEY, t); } catch { /* silencieux */ }
  }

  function toggle() {
    const next = theme === 'light' ? 'dark' : 'light';
    setTheme(next);
    applyTheme(next);
  }

  // Éviter le flash de contenu non stylé
  if (!mounted) return null;

  const isDark = theme === 'dark';

  if (compact) {
    return (
      <button
        onClick={toggle}
        title={isDark ? 'Passer en mode clair' : 'Passer en mode sombre'}
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          fontSize: 18, lineHeight: 1, padding: '4px 6px',
          borderRadius: 6,
          color: 'inherit',
        }}
        aria-label={isDark ? 'Mode clair' : 'Mode sombre'}
      >
        {isDark ? '☀️' : '🌙'}
      </button>
    );
  }

  return (
    <button
      onClick={toggle}
      style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '6px 14px', borderRadius: 20, cursor: 'pointer', fontSize: 13,
        fontWeight: 600, border: '1px solid var(--border)',
        background: isDark ? '#334155' : '#f1f5f9',
        color: isDark ? '#F1F5F9' : '#0A2540',
        transition: 'all 0.2s',
      }}
    >
      <span>{isDark ? '☀️' : '🌙'}</span>
      <span>{isDark ? 'Mode clair' : 'Mode sombre'}</span>
    </button>
  );
}

/**
 * Hook pour lire le thème courant dans n'importe quel composant
 */
export function useTheme() {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    setTheme(getInitialTheme());
    const observer = new MutationObserver(() => {
      const isDark = document.documentElement.classList.contains('dark');
      setTheme(isDark ? 'dark' : 'light');
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'data-theme'] });
    return () => observer.disconnect();
  }, []);

  return { theme, isDark: theme === 'dark' };
}
