import React from 'react';
import { ThemeToggle } from './components/theme-toggle';
import { ELearningPage } from './pages/elearning';
import { FormEvent, useEffect, useState } from 'react';
import { canAccessRoute, demoRoles, navigationItems, type UserRole } from './auth';
import {
  type AuthUser,
  changePassword,
  getAccessToken,
  getRefreshToken,
  getCurrentUser,
  loginUser,
  logoutUser,
} from './authClient';
import { clearCsrfToken } from './api';
import { LocaleSwitcher } from './components/LocaleSwitcher';
import { AudioToggle, LocaleAudioSwitcher } from './components/AudioButton';
import { t } from './i18n';
import { AuthSessionProvider } from './authSession';
import {
  AdminPage,
  CandidatePage,
  CenterPage,
  DrivingSchoolPage,
  ExamPage,
  HomePage,
  InstitutionalDossierPage,
  MinisterialPage,
  ResultsPage,
  TrainingPage,
} from './pages';

type AppRoute =
  | 'home' | 'candidate' | 'center' | 'admin'
  | 'exam' | 'results' | 'dossier' | 'training' | 'school' | 'ministerial'
  | 'login' | 'account';

const ROLE_KEY = 'cr-role';
const PRES_KEY = 'cr-pres';

function getRouteFromHash(): AppRoute {
  const r = window.location.hash.replace('#/', '') as AppRoute;
  const valid: AppRoute[] = ['candidate','center','admin','exam','results','dossier','training','school','ministerial','login','account'];
  return valid.includes(r) ? r : 'home';
}

function normalizeRole(role: string): UserRole {
  return demoRoles.some(d => d.value === role) ? role as UserRole : 'candidate';
}

// ── Loading ───────────────────────────────────────────────────────
function Loading() {
  return (
    <div className="login-screen">
      <div style={{ textAlign: 'center', color: 'var(--muted)' }}>
        <div style={{ fontSize: 32, marginBottom: 12 }}>⏳</div>
        <p>Vérification de la session…</p>
      </div>
    </div>
  );
}

// ── Access Denied ─────────────────────────────────────────────────
function AccessDenied({ role }: { role: UserRole }) {
  return (
    <section className="screen access-denied">
      <div style={{ fontSize: 48, marginBottom: 12 }}>🔒</div>
      <h2>Accès non autorisé</h2>
      <p>Le rôle <strong>{role}</strong> ne peut pas accéder à cette page.</p>
      <div className="actions" style={{ justifyContent: 'center', marginTop: 20 }}>
        <a href="#/" style={{ color: 'var(--blue)', fontSize: 13 }}>← Retour à l'accueil</a>
      </div>
    </section>
  );
}

// ── Account Page ─────────────────────────────────────────────────
function AccountPage({ currentUser }: { currentUser: AuthUser | null }) {
  const [cur, setCur] = useState('');
  const [nw, setNw] = useState('');
  const [conf, setConf] = useState('');
  const [msg, setMsg] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    if (nw.length < 12) { setMsg('Le nouveau mot de passe doit contenir au moins 12 caractères.'); return; }
    if (nw !== conf) { setMsg('La confirmation ne correspond pas.'); return; }
    try {
      await changePassword(cur, nw);
      setCur(''); setNw(''); setConf('');
      setMsg('✅ Mot de passe mis à jour.');
    } catch {
      setMsg('❌ Mot de passe actuel incorrect.');
    }
  }

  return (
    <section className="screen" style={{ maxWidth: 600 }}>
      <div className="page-header">
        <span className="eyebrow dark">Compte</span>
        <h1>Mon compte</h1>
        <p>Gérez votre profil et sécurisez votre accès.</p>
      </div>
      <div className="acct-grid" style={{ marginBottom: 20 }}>
        <div className="acct-card">
          <span>Agent</span>
          <strong>{currentUser?.full_name ?? '—'}</strong>
          <small>{currentUser?.email ?? '—'}</small>
        </div>
        <div className="acct-card">
          <span>Rôle</span>
          <strong style={{ textTransform: 'capitalize' }}>{currentUser?.role ?? '—'}</strong>
          <small>{currentUser?.is_active ? '✅ Compte actif' : '⚠️ Compte inactif'}</small>
        </div>
      </div>
      {/* Sélecteur de langue avec badge audio */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">
          <span className="card-title">🌍 Langue / Langue</span>
          <AudioToggle />
        </div>
        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12 }}>
          Les langues nationales guinéennes utilisent l'audio pour les questions d'examen.
          Sélectionnez votre langue — un bouton 🔊 apparaîtra sur chaque question.
        </p>
        <LocaleAudioSwitcher />
      </div>

      <div className="card">
        <div className="card-header"><span className="card-title">Changer le mot de passe</span></div>
        <form className="pwd-form" onSubmit={handleSubmit}>
          <label>Mot de passe actuel<input type="password" value={cur} onChange={e => setCur(e.target.value)} /></label>
          <label>Nouveau mot de passe (12 car. min.)<input type="password" value={nw} onChange={e => setNw(e.target.value)} /></label>
          <label>Confirmer<input type="password" value={conf} onChange={e => setConf(e.target.value)} /></label>
          <button type="submit" className="btn-primary" disabled={!cur || nw.length < 12 || !conf}>Changer le mot de passe</button>
          {msg && <p className={msg.startsWith('✅') ? 'login-status' : 'form-error'}>{msg}</p>}
        </form>
      </div>
    </section>
  );
}

// ── Login Page ────────────────────────────────────────────────────
function LoginPage({
  currentUser, isPres, role, onRoleChange, onLogin,
}: {
  currentUser: AuthUser | null;
  isPres: boolean;
  role: UserRole;
  onRoleChange: (r: UserRole) => void;
  onLogin: (email: string, pass: string) => Promise<void>;
}) {
  const [email, setEmail] = useState('');
  const [pass, setPass] = useState('');
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const DEMO_ACCOUNTS = [
    { role: 'super_admin' as UserRole, label: 'Super Admin', email: 'super_admin@coderoute.gov.gn' },
    { role: 'admin' as UserRole, label: 'Admin national', email: 'admin.national@coderoute.gov.gn' },
    { role: 'center' as UserRole, label: 'Chef de centre', email: 'chef.conakry@coderoute.gov.gn' },
    { role: 'candidate' as UserRole, label: 'Candidat (démo)', email: '' },
  ];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email || !pass) return;
    setLoading(true);
    setStatus('Connexion en cours…');
    try {
      await onLogin(email, pass);
    } catch {
      setStatus('❌ Identifiants incorrects. Vérifiez votre email et mot de passe.');
      setLoading(false);
    }
  }

  function fillDemo(acc: typeof DEMO_ACCOUNTS[0]) {
    if (acc.email) { setEmail(acc.email); setPass('CodeRoute2026!'); }
    onRoleChange(acc.role);
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <span className="eyebrow">Accès sécurisé</span>
        <h2>CodeRoute Guinée</h2>
        <p>Connectez-vous à la plateforme nationale d'examen du code de la route.</p>

        {!isPres && currentUser && (
          <div className="auth-session-card">
            <strong>✅ Connecté : {currentUser.full_name}</strong>
            <span>{currentUser.email} · {currentUser.role}</span>
          </div>
        )}

        <form className="login-form" onSubmit={handleSubmit}>
          <label>Adresse e-mail<input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="agent@coderoute.gov.gn" autoComplete="username" /></label>
          <label>Mot de passe<input type="password" value={pass} onChange={e => setPass(e.target.value)} placeholder="••••••••••••" autoComplete="current-password" /></label>
          <button type="submit" className="btn-login" disabled={loading || !email || !pass}>
            {loading ? 'Connexion…' : 'Se connecter'}
          </button>
          {status && <p className={status.startsWith('❌') ? 'form-error' : 'login-status'}>{status}</p>}
        </form>

        <div className="login-sep">Comptes de test disponibles</div>
        <div className="demo-grid">
          {DEMO_ACCOUNTS.map(acc => (
            <button key={acc.role} type="button"
              className={`demo-btn${role === acc.role && !acc.email ? ' active' : ''}`}
              onClick={() => fillDemo(acc)}>
              <b>{acc.label}</b>
              <small>{acc.email || 'Mode présentation'}</small>
            </button>
          ))}
        </div>
        {isPres && (
          <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 12, textAlign: 'center' }}>
            Mode présentation actif — Rôle : <strong>{role}</strong>.{' '}
            <a href="#/" style={{ color: 'var(--blue)' }}>Continuer →</a>
          </p>
        )}
      </div>
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────
export default function App() {
  const [route, setRoute] = useState<AppRoute>(getRouteFromHash());
  const [role, setRole] = useState<UserRole>(
    () => (localStorage.getItem(ROLE_KEY) as UserRole) ?? 'super_admin'
  );
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [isPres, setIsPres] = useState(() => !getAccessToken() && !getRefreshToken());
  const [loading, setLoading] = useState(() => Boolean(getAccessToken() || getRefreshToken()));

  useEffect(() => {
    const onHash = () => setRoute(getRouteFromHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  useEffect(() => {
    if (!getAccessToken() && !getRefreshToken()) { setIsPres(true); setLoading(false); return; }
    getCurrentUser()
      .then(u => { setCurrentUser(u); setRole(normalizeRole(u.role)); setIsPres(false); })
      .catch(() => { logoutUser(); setIsPres(true); })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    function onExpired() {
      setCurrentUser(null); setIsPres(true); setRole('candidate');
      window.location.hash = '#/login';
    }
    window.addEventListener('coderoute:session-expired', onExpired);
    return () => window.removeEventListener('coderoute:session-expired', onExpired);
  }, []);

  useEffect(() => { localStorage.setItem(ROLE_KEY, role); }, [role]);
  useEffect(() => { localStorage.setItem(PRES_KEY, String(isPres)); }, [isPres]);

  async function handleLogin(email: string, pass: string) {
    await loginUser(email, pass);
    const u = await getCurrentUser();
    setCurrentUser(u); setRole(normalizeRole(u.role)); setIsPres(false);
    window.location.hash = '#/';
  }

  function handleLogout() {
    clearCsrfToken(); logoutUser(); setCurrentUser(null); setIsPres(true); setRole('candidate');
    window.location.hash = '#/login';
  }

  function handleRoleChange(r: UserRole) {
    clearCsrfToken(); logoutUser(); setCurrentUser(null); setIsPres(true); setRole(r);
  }

  const visibleNav = navigationItems.filter(n => n.roles.includes(role));
  const curHref = route === 'home' ? '#/' : `#/${route}`;
  const hasAccess = canAccessRoute(role, curHref);
  const roleLabel = demoRoles.find(d => d.value === role)?.label ?? role;
  const sessionLabel = isPres
    ? `Présentation · ${roleLabel}`
    : `${currentUser?.full_name ?? 'Agent'} · ${roleLabel}`;

  const loginPage = (
    <LoginPage
      currentUser={currentUser} isPres={isPres} role={role}
      onRoleChange={handleRoleChange} onLogin={handleLogin}
    />
  );

  let page: React.ReactElement;
  if (loading) page = <Loading />;
  else if (route === 'login') page = loginPage;
  else if (!hasAccess) page = <AccessDenied role={role} />;
  else {
    const pageMap: Record<AppRoute, React.ReactElement> = {
      home:      <HomePage />,
      training:  <TrainingPage />,
      candidate: <CandidatePage />,
      center:    <CenterPage />,
      school:    <DrivingSchoolPage />,
      ministerial: <MinisterialPage />,
      admin:     <AdminPage />,
      dossier:   <InstitutionalDossierPage />,
      exam:      <ExamPage />,
      results:   <ResultsPage />,
      account:   isPres ? <AccessDenied role={role} /> : <AccountPage currentUser={currentUser} />,
      login:     loginPage,
    };
    page = pageMap[route];
  }

  return (
    <main className="app-shell">
      <nav className="top-nav" role="navigation" aria-label="Navigation principale">
        <a href="#/" className="brand-link">
          <div className="brand-logo">CR</div>
          <div className="brand-text">
            <strong>CodeRoute Guinée</strong>
            <small>Examen code de la route</small>
          </div>
        </a>

        <div className="nav-links">
          {visibleNav.map(item => {
            const r = item.href.replace('#/', '') || 'home';
            return (
              <a key={item.href} href={item.href} className={route === r ? 'active' : ''}>
                {t(`nav.${r}`) !== `nav.${r}` ? t(`nav.${r}`) : item.label}
              </a>
            );
          })}
          {!isPres && (
            <a href="#/account" className={route === 'account' ? 'active' : ''}>Mon compte</a>
          )}
          <a href="#/login" className={route === 'login' ? 'active' : ''}>Connexion</a>
        </div>

        <div className="session-panel">
          <LocaleSwitcher />
          <span title={sessionLabel}>{sessionLabel}</span>
          <ThemeToggle compact />
          <button onClick={handleLogout}>{isPres ? 'Quitter' : 'Déconnexion'}</button>
        </div>

        {isPres && (
          <label className="role-switcher">
            Rôle
            <select value={role} onChange={e => handleRoleChange(e.target.value as UserRole)}>
              {demoRoles.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
            </select>
          </label>
        )}
      </nav>

      <AuthSessionProvider currentUser={currentUser} isPresentationMode={isPres} role={role}>
        {page}
      </AuthSessionProvider>
    </main>
  );
}
