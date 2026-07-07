/**
 * Inscription candidat libre — création de compte publique.
 * Crée le compte User + la fiche Candidate, connecte immédiatement
 * et affiche la référence officielle GN-CODE-....
 */
import { type FormEvent, useState } from 'react';
import { registerFreeCandidate, registerSchool } from '../api';
import { setAccessToken, setRefreshToken } from '../authClient';

export function RegisterPage({ onRegistered }: { onRegistered: () => void }) {
  const [mode, setMode] = useState<'candidate' | 'school'>('candidate');
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', password: '', confirm: '',
    phone: '', identity_number: '', permit_category: 'B', city: '',
  });
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState<{ reference: string } | null>(null);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm(f => ({ ...f, [k]: e.target.value }));
  const [school, setSchool] = useState({
    school_name: '', manager_name: '', email: '', phone: '', city: '', password: '', confirm: '',
  });
  const [schoolDone, setSchoolDone] = useState<string | null>(null);
  const setS = (k: keyof typeof school) => (e: { target: { value: string } }) =>
    setSchool(s => ({ ...s, [k]: e.target.value }));

  const emailOk = (v: string) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v);

  const valid =
    form.first_name.trim().length >= 2 &&
    form.last_name.trim().length >= 2 &&
    emailOk(form.email) &&
    form.password.length >= 8 &&
    form.password === form.confirm &&
    form.phone.trim().length >= 8 &&
    form.identity_number.trim().length >= 3;

  const schoolValid =
    school.school_name.trim().length >= 3 &&
    school.manager_name.trim().length >= 3 &&
    emailOk(school.email) &&
    school.phone.trim().length >= 8 &&
    school.city.trim().length >= 2 &&
    school.password.length >= 8 &&
    school.password === school.confirm;

  async function handleSchoolSubmit(e: FormEvent) {
    e.preventDefault();
    if (!schoolValid || loading) return;
    setLoading(true); setStatus(null);
    try {
      const r = await registerSchool({
        school_name: school.school_name.trim(),
        manager_name: school.manager_name.trim(),
        email: school.email.trim(),
        phone: school.phone.trim(),
        city: school.city.trim(),
        password: school.password,
      });
      setSchoolDone(r.detail);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : 'Inscription impossible. Réessayez.');
    } finally {
      setLoading(false);
    }
  }

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

  if (schoolDone) {
    return (
      <div className="login-screen">
        <div className="login-form-panel" style={{ margin: '0 auto' }}>
          <div className="login-card" style={{ textAlign: 'center', maxWidth: 460 }}>
            <div style={{ color: 'var(--guinea-gold)', marginBottom: 12 }}>
              <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
              </svg>
            </div>
            <h2 style={{ fontSize: 20 }}>Demande enregistrée</h2>
            <p style={{ color: 'var(--muted)', fontSize: 13, margin: '12px 0 18px', lineHeight: 1.6 }}>
              {schoolDone}
            </p>
            <a href="#/login" className="btn-primary" style={{ width: '100%', display: 'block', textDecoration: 'none' }}>
              Retour à la connexion
            </a>
          </div>
        </div>
      </div>
    );
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
              <h2 style={{ fontSize: 20, letterSpacing: '-.02em' }}>
                {mode === 'candidate' ? 'Créer un compte candidat' : 'Inscrire mon auto-école'}
              </h2>
              <p className="login-sub">Plateforme nationale DNTT</p>
            </div>
          </div>

          {/* Toggle Candidat / Auto-école */}
          <div style={{ display: 'flex', gap: 6, background: 'var(--bg)', padding: 4, borderRadius: 12, marginBottom: 18 }}>
            <button type="button" onClick={() => { setMode('candidate'); setStatus(null); }}
              style={{
                flex: 1, padding: '9px 0', border: 'none', borderRadius: 9, cursor: 'pointer',
                fontSize: 13, fontWeight: 700, fontFamily: 'var(--font-ui)',
                background: mode === 'candidate' ? 'var(--guinea-green)' : 'transparent',
                color: mode === 'candidate' ? '#fff' : 'var(--ink2)',
              }}>
              Candidat
            </button>
            <button type="button" onClick={() => { setMode('school'); setStatus(null); }}
              style={{
                flex: 1, padding: '9px 0', border: 'none', borderRadius: 9, cursor: 'pointer',
                fontSize: 13, fontWeight: 700, fontFamily: 'var(--font-ui)',
                background: mode === 'school' ? 'var(--guinea-green)' : 'transparent',
                color: mode === 'school' ? '#fff' : 'var(--ink2)',
              }}>
              Auto-école
            </button>
          </div>

          {mode === 'school' ? (
            <form className="login-form" onSubmit={handleSchoolSubmit}>
              <label>Nom de l'auto-école
                <input value={school.school_name} onChange={setS('school_name')} required autoComplete="off" placeholder="Auto-École de la Corniche" />
              </label>
              <label>Nom du responsable
                <input value={school.manager_name} onChange={setS('manager_name')} required autoComplete="off" />
              </label>
              <label>Adresse email professionnelle
                <input type="email" value={school.email} onChange={setS('email')} required autoComplete="off" placeholder="contact@auto-ecole.gn" />
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <label>Téléphone
                  <input value={school.phone} onChange={setS('phone')} required autoComplete="off" placeholder="+224 6XX…" />
                </label>
                <label>Ville
                  <input value={school.city} onChange={setS('city')} required autoComplete="off" placeholder="Conakry" />
                </label>
              </div>
              <label>Mot de passe (8 caractères min.)
                <input type="password" value={school.password} onChange={setS('password')} required autoComplete="new-password" />
              </label>
              <label>Confirmer le mot de passe
                <input type="password" value={school.confirm} onChange={setS('confirm')} required autoComplete="new-password" />
                {school.confirm.length > 0 && school.confirm !== school.password && (
                  <span style={{ fontSize: 11, color: 'var(--red)', marginTop: 3, display: 'block' }}>
                    Les mots de passe ne correspondent pas
                  </span>
                )}
              </label>

              <div className="alert ai" style={{ fontSize: 12 }}>
                Votre compte sera activé après validation par la DNTT (sous 48h ouvrées).
                Vous recevrez la confirmation par email.
              </div>

              {status && <div className="login-error-box">{status}</div>}

              <button type="submit" className="btn-success"
                style={{ width: '100%', minHeight: 46, fontSize: 14, marginTop: 4 }}
                disabled={loading || !schoolValid}>
                {loading ? 'Envoi…' : "Envoyer ma demande →"}
              </button>
            </form>
          ) : (
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
          )}

          <p style={{ textAlign: 'center', fontSize: 13, marginTop: 14, color: 'var(--muted)' }}>
            Déjà inscrit ?{' '}
            <a href="#/login" style={{ color: 'var(--guinea-green)', fontWeight: 600 }}>Se connecter</a>
          </p>
        </div>
      </div>
    </div>
  );
}
