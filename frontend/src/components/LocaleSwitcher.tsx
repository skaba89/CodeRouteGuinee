/**
 * Sélecteur de langue — barre de navigation CodeRoute Guinée.
 * Affiche les 5 langues supportées avec leur nom natif.
 */
import { useLocale, SUPPORTED_LOCALES, type Locale } from '../i18n';

export function LocaleSwitcher() {
  const { locale, setLocale } = useLocale();

  return (
    <div className="locale-switcher" aria-label="Changer la langue">
      <select
        value={locale}
        onChange={(e) => setLocale(e.target.value as Locale)}
        className="locale-select"
        aria-label="Sélectionner la langue"
      >
        {SUPPORTED_LOCALES.map((l) => (
          <option key={l.code} value={l.code}>
            {l.native}
          </option>
        ))}
      </select>
    </div>
  );
}
