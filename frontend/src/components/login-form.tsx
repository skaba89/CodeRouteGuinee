/**
 * LoginForm — Gère le login en 2 étapes avec 2FA optionnel
 * Étape 1 : email + mot de passe
 * Étape 2 (si requires_2fa=true) : code TOTP Google Authenticator
 */
import { useState } from 'react';
import { loginUser, verify2FA } from '../authClient';

interface LoginFormProps {
  onSuccess: () => void;
  onError?: (msg: string) => void;
}

export function LoginForm({ onSuccess, onError }: LoginFormProps) {
  const [email, setEmail]         = useState('');
  const [password, setPassword]   = useState('');
  const [tfaCode, setTfaCode]     = useState('');
  const [step, setStep]           = useState<'credentials' | '2fa'>('credentials');
  const [partialToken, setPartialToken] = useState('');
  const [userId, setUserId]       = useState('');
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');

  async function handleCredentials(e: React.FormEvent) {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const token = await loginUser(email, password);
      if (token.requires_2fa && token.user_id) {
        setPartialToken(token.access_token);
        setUserId(token.user_id);
        setStep('2fa');
      } else {
        onSuccess();
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Identifiants incorrects';
      setError(msg);
      onError?.(msg);
    } finally {
      setLoading(false);
    }
  }

  async function handleTfa(e: React.FormEvent) {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      await verify2FA(userId, partialToken, tfaCode.trim());
      onSuccess();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Code 2FA invalide';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  // Utilise les styles globaux input de styles.css
  const inputStyle: React.CSSProperties = { marginTop: 4, fontSize: 14 };

  if (step === '2fa') return (
    <form onSubmit={handleTfa} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ textAlign: 'center', marginBottom: 8 }}>
        <div style={{ fontSize: 36, marginBottom: 6 }}>🔐</div>
        <h3 style={{ margin: 0, color: 'var(--ink)' }}>Authentification à deux facteurs</h3>
        <p style={{ margin: '6px 0 0', fontSize: 13, color: 'var(--muted)' }}>
          Ouvrez Google Authenticator et entrez le code à 6 chiffres.
        </p>
      </div>
      {error && (
        <div style={{ padding: '8px 12px', background: 'var(--red-l, #fdecea)',
          borderRadius: 8, fontSize: 13, color: 'var(--red, #c00)' }}>⚠ {error}</div>
      )}
      <label>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink2)' }}>
          Code TOTP (6 chiffres)
        </span>
        <input
          type="text" inputMode="numeric" pattern="[0-9]{6}" maxLength={6}
          value={tfaCode} onChange={e => setTfaCode(e.target.value)}
          placeholder="123456" required autoFocus
          style={{ ...inputStyle, letterSpacing: '0.3em', fontSize: 20,
            textAlign: 'center', fontFamily: 'monospace' }}
        />
      </label>
      <button type="submit" disabled={loading || tfaCode.length !== 6}
        className="btn-success btn-block btn-lg">
        {loading ? 'Vérification…' : 'Valider le code'}
      </button>
      <button type="button" onClick={() => { setStep('credentials'); setTfaCode(''); }}
        style={{ background: 'none', border: 'none', color: 'var(--muted)',
          fontSize: 13, cursor: 'pointer', textDecoration: 'underline', minHeight: 'auto', padding: 0 }}>
        ← Retour à la connexion
      </button>
    </form>
  );

  return (
    <form onSubmit={handleCredentials} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {error && (
        <div style={{ padding: '8px 12px', background: 'var(--red-l, #fdecea)',
          borderRadius: 8, fontSize: 13, color: 'var(--red, #c00)' }}>⚠ {error}</div>
      )}
      <label>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink2)' }}>Email</span>
        <input type="email" value={email} onChange={e => setEmail(e.target.value)}
          required autoFocus placeholder="admin@coderoute.gov.gn" style={inputStyle} />
      </label>
      <label>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink2)' }}>Mot de passe</span>
        <input type="password" value={password} onChange={e => setPassword(e.target.value)}
          required placeholder="••••••••" style={inputStyle} />
      </label>
      <button type="submit" disabled={loading} className="btn-success btn-block btn-lg">
        {loading ? 'Connexion…' : 'Se connecter'}
      </button>
    </form>
  );
}
