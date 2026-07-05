/**
 * Inscription candidat libre — création de compte publique.
 * Crée le compte User + la fiche Candidate, connecte immédiatement
 * et affiche la référence officielle GN-CODE-....
 */
import { type FormEvent, useState } from 'react';
import { registerFreeCandidate } from '../api';
import { setAccessToken, setRefreshToken } from '../authClient';

export function RegisterPage({ onRegistered }: { onRegistered: () => void }) {
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', password: '', confirm: '',
    phone: '', identity_number: '', permit_category: 'B', city: '',
  });
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState<{ reference: string } | null>(null);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  const valid =
    form.first_name.trim().length >= 2 &&
    form.last_name.trim().length >= 2 &&
    /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email) &&
    form.password.length >= 8 &&
    form.password === form.confirm &&
    form.phone.trim().length >= 8 &&
    form.identity_number.trim().length >= 3;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!valid || loading) return;
    setLoading(true); setStatus(null);
    try {
      const r = await registerFreeCandidate({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        email: form.email.trim(),
        password: form.password,
        phone: form.phone.trim(),
        identity_number: form.identity_number.trim(),
        permit_category: form.permit_category,
        city: form.city.trim() || undefined,
      });
      setAccessToken(r.access_token);
      if (r.refresh_token) setRefreshToken(r.refresh_token);
      setDone({ reference: r.candidate_reference });
    } catch (err) {
      setStatus(err instanceof Error ? err.message : 'Inscription impossible. Réessayez.');
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <div className="login-screen">
        <div className="login-form-panel" style={{ margin: '0 auto' }}>
          <div className="login-card" style={{ textAlign: 'center' }}>
            <div style={{ color: 'var(--guinea-green)', marginBottom: 12 }}>
              <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            </div>
            <h2 style={{ fontSize: 20 }}>Compte créé</h2>
            <p style={{ color: 'var(--muted)', fontSize: 13, margin: '10px 0 4px' }}>
              Votre référence candidat officielle :
            </p>
            <p style={{ fontFamily: 'monospace', fontSize: 17, fontWeight: 700, letterSpacing: '.04em', margin: '2px 0 16px' }}>
              {done.reference}
            </p>
            <p style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 18 }}>
              Notez-la : elle sera demandée pour la réservation et le jour de l'examen.
            </p>
            <button className="btn-primary" style={{ width: '100%' }} onClick={onRegistered}>
              Accéder à mon espace →
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="login-screen">
      <div className="login-form-panel" style={{ margin: '0 auto' }}>
        <div className="login-card" style={{ maxWidth: 460 }}>
          <div className="login-brand">
            <div className="login-logo">CR</div>
            <div>
              <h2 style={{ fontSize: 20, letterSpacing: '-.02em' }}>Créer un compte candidat</h2>
              <p className="login-sub">Candidat libre — Plateforme nationale DNTT</p>
            </div>
          </div>

          <form className="login-form" onSubmit={handleSubmit}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <label>Prénom
                <input value={form.first_name} onChange={set('first_name')} required autoComplete="off" />
              </label>
              <label>Nom
                <input value={form.last_name} onChange={set('last_name')} required autoComplete="off" />
              </label>
            </div>
            <label>Adresse email
              <input type="email" value={form.email} onChange={set('email')} required autoComplete="off" placeholder="votre@email.com" />
            </label>
            <label>Téléphone
              <input value={form.phone} onChange={set('phone')} required autoComplete="off" placeholder="+224 6XX XX XX XX" />
            </label>
            <label>Numéro d'identité (NNI / passeport)
              <input value={form.identity_number} onChange={set('identity_number')} required autoComplete="off" />
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <label>Catégorie
                <select value={form.permit_category} onChange={set('permit_category')}>
                  <option value="A">A — Moto</option>
                  <option value="B">B — Voiture</option>
                  <option value="C">C — Poids lourd</option>
                  <option value="D">D — Transport en commun</option>
                  <option value="E">E — Remorque</option>
                </select>
              </label>
              <label>Ville
                <input value={form.city} onChange={set('city')} autoComplete="off" placeholder="Conakry" />
              </label>
            </div>
            <label>Mot de passe (8 caractères min.)
              <input type="password" value={form.password} onChange={set('password')} required autoComplete="new-password" />
            </label>
            <label>Confirmer le mot de passe
              <input type="password" value={form.confirm} onChange={set('confirm')} required autoComplete="new-password" />
              {form.confirm.length > 0 && form.confirm !== form.password && (
                <span style={{ fontSize: 11, color: 'var(--red)', marginTop: 3, display: 'block' }}>
                  Les mots de passe ne correspondent pas
                </span>
              )}
            </label>

            {status && <div className="login-error-box">{status}</div>}

            <button type="submit" className="btn-success"
              style={{ width: '100%', minHeight: 46, fontSize: 14, marginTop: 4 }}
              disabled={loading || !valid}>
              {loading ? 'Création…' : "Créer mon compte →"}
            </button>
          </form>

          <p style={{ textAlign: 'center', fontSize: 13, marginTop: 14, color: 'var(--muted)' }}>
            Déjà inscrit ?{' '}
            <a href="#/login" style={{ color: 'var(--guinea-green)', fontWeight: 600 }}>Se connecter</a>
          </p>
        </div>
      </div>
    </div>
  );
}
