import { useLocale, SUPPORTED_LOCALES, type Locale } from '../i18n';

export function LocaleSwitcher() {
  const { locale, setLocale } = useLocale();
  return (
    <div className="locale-switcher">
      <select
        value={locale}
        onChange={e => setLocale(e.target.value as Locale)}
        className="locale-select"
        aria-label="Langue / Language"
        title="Changer la langue"
      >
        {SUPPORTED_LOCALES.map(l => (
          <option key={l.code} value={l.code}>
            {l.native}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Affichage complet avec région — pour les pages de paramètres */
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
            padding: '10px 14px', border: `2px solid ${locale === l.code ? 'var(--blue)' : 'var(--border)'}`,
            borderRadius: 'var(--r-lg)', background: locale === l.code ? 'var(--blue-l)' : 'var(--white)',
            cursor: 'pointer', minHeight: 'unset', color: 'var(--ink)', transition: 'all .15s',
          }}
        >
          <span style={{ fontWeight: 700, fontSize: 14, color: locale === l.code ? 'var(--blue)' : 'var(--ink)' }}>
            {l.native}
          </span>
          <span style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
            {l.label} · {l.region}
          </span>
        </button>
      ))}
    </div>
  );
}
