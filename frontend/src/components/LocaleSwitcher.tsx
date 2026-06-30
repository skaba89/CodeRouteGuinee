import { useLocale, SUPPORTED_LOCALES, type Locale } from '../i18n';

/** Version compacte pour la topbar — affiche le code langue en 2-3 lettres */
export function LocaleSwitcher() {
  const { locale, setLocale } = useLocale();
  const current = SUPPORTED_LOCALES.find(l => l.code === locale);
  const shortLabel = current?.code === 'fr' ? 'FR'
    : current?.code === 'en' ? 'EN'
    : current?.code.slice(0, 3).toUpperCase() ?? 'FR';

  return (
    <div className="locale-switcher" title="Changer la langue">
      <select
        value={locale}
        onChange={e => setLocale(e.target.value as Locale)}
        className="locale-select"
        aria-label="Langue"
      >
        {SUPPORTED_LOCALES.map(l => (
          <option key={l.code} value={l.code}>{l.native}</option>
        ))}
      </select>
      <span className="locale-label">{shortLabel}</span>
    </div>
  );
}

/** Affichage complet pour les pages de paramètres */
export function LocaleSwitcherFull() {
  const { locale, setLocale } = useLocale();
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(180px,1fr))', gap: 8 }}>
      {SUPPORTED_LOCALES.map(l => (
        <button
          key={l.code}
          type="button"
          onClick={() => setLocale(l.code)}
          style={{
            display: 'flex', flexDirection: 'column', alignItems: 'flex-start',
            padding: '10px 14px',
            border: `2px solid ${locale === l.code ? 'var(--blue)' : 'var(--border)'}`,
            borderRadius: 'var(--r-lg)',
            background: locale === l.code ? 'var(--blue-l)' : 'var(--surface)',
            cursor: 'pointer', minHeight: 'unset', color: 'var(--ink)',
            transition: 'all .15s', boxShadow: 'none',
          }}
        >
          <strong style={{ fontSize: 13 }}>{l.native}</strong>
          <small style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{l.region}</small>
        </button>
      ))}
    </div>
  );
}
