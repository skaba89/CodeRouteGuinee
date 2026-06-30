import React from 'react';
import { ThemeToggle } from './components/theme-toggle';
import { ELearningPage } from './pages/elearning';
import { FormEvent, useEffect, useState } from 'react';
import { canAccessRoute, navigationItems, type UserRole } from './auth';
import {
  IconHome, IconBook, IconGraduate, IconUser, IconBuilding,
  IconLandmark, IconDashboard, IconClipboard, IconTarget,
  IconBarChart, IconSettings,
} from './icons';
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
  AdminPage, CandidatePage, CenterPage, DrivingSchoolPage,
  ExamPage, HomePage, InstitutionalDossierPage, MinisterialPage,
  ResultsPage, TrainingPage,
} from './pages';

type AppRoute =
  | 'home' | 'candidate' | 'center' | 'admin'
  | 'exam' | 'results' | 'dossier' | 'training' | 'school' | 'ministerial'
  | 'login' | 'account';

function getRouteFromHash(): AppRoute {
  const r = window.location.hash.replace('#/', '') as AppRoute;
  const valid: AppRoute[] = ['candidate','center','admin','exam','results','dossier','training','school','ministerial','login','account'];
  return valid.includes(r) ? r : 'home';
}

function normalizeRole(role: string): UserRole {
  const valid: UserRole[] = ['super_admin','admin','center','driving_school','candidate'];
  return valid.includes(role as UserRole) ? role as UserRole : 'candidate';
}

// ── Loading ───────────────────────────────────────────────────────
function Loading() {
  return (
    <div className="login-screen">
      <div style={{ textAlign: 'center', color: 'var(--muted)' }}>
        <div className="spinner" style={{ width: 32, height: 32, margin: '0 auto 16px' }} />
        <p>Vérification de la session…</p>
      </div>
    </div>
  );
}

// ── Accès refusé ──────────────────────────────────────────────────
function AccessDenied({ role }: { role: UserRole }) {
  return (
    <section className="screen access-denied">
      <div style={{ color: 'var(--muted)', marginBottom: 12 }}>
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
          <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
      </div>
      <h2>Accès non autorisé</h2>
      <p>Le rôle <strong>{role}</strong> ne peut pas accéder à cette page.</p>
      <div className="actions" style={{ justifyContent: 'center', marginTop: 20 }}>
        <a href="#/" style={{ color: 'var(--blue)', fontSize: 13 }}>← Retour à l'accueil</a>
      </div>
    </section>
  );
}

// ── Mon compte ────────────────────────────────────────────────────
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
      setMsg('Mot de passe mis à jour avec succès.');
    } catch {
      setMsg('Mot de passe actuel incorrect.');
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
          <strong>Agent</strong>
          <span>{currentUser?.full_name ?? '—'}</span>
          <small style={{ color: 'var(--muted)', fontSize: 12 }}>{currentUser?.email ?? '—'}</small>
        </div>
        <div className="acct-card">
          <strong>Rôle</strong>
          <span style={{ textTransform: 'capitalize' }}>{currentUser?.role ?? '—'}</span>
          <small style={{ color: 'var(--muted)', fontSize: 12 }}>
            {currentUser?.is_active ? 'Compte actif' : 'Compte inactif'}
          </small>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">
          <span className="card-title">Langue de l'interface</span>
          <AudioToggle />
        </div>
        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12 }}>
          Les langues nationales guinéennes utilisent l'audio pour les questions d'examen.
        </p>
        <LocaleAudioSwitcher />
      </div>

      <div className="card">
        <div className="card-header"><span className="card-title">Changer le mot de passe</span></div>
        <form className="login-form" onSubmit={handleSubmit}>
          <label>Mot de passe actuel<input type="password" value={cur} onChange={e => setCur(e.target.value)} autoComplete="current-password" /></label>
          <label>Nouveau mot de passe (12 car. min.)<input type="password" value={nw} onChange={e => setNw(e.target.value)} autoComplete="new-password" /></label>
          <label>Confirmer<input type="password" value={conf} onChange={e => setConf(e.target.value)} autoComplete="new-password" /></label>
          <button type="submit" className="btn-primary" disabled={!cur || nw.length < 12 || !conf}>
            Changer le mot de passe
          </button>
          {msg && (
            <p className={msg.includes('succès') ? 'login-status' : 'form-error'}>{msg}</p>
          )}
        </form>
      </div>
    </section>
  );
}

// ── Page de connexion ─────────────────────────────────────────────
function LoginPage({ onLogin }: { onLogin: (email: string, pass: string) => Promise<void> }) {
  const [email, setEmail] = useState('');
  const [pass, setPass] = useState('');
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email || !pass) return;
    setLoading(true);
    setStatus(null);
    try {
      await onLogin(email, pass);
    } catch {
      setStatus('Identifiants incorrects. Vérifiez votre email et mot de passe.');
      setLoading(false);
    }
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-brand">
          <div className="login-logo">CR</div>
          <div>
            <h2>CodeRoute Guinée</h2>
            <p className="login-sub">Plateforme nationale DNTT</p>
          </div>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            Adresse email
            <input
              type="email" value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="votre@email.com"
              autoComplete="email" required
            />
          </label>
          <label>
            Mot de passe
            <input
              type="password" value={pass}
              onChange={e => setPass(e.target.value)}
              placeholder="••••••••••••"
              autoComplete="current-password" required
            />
          </label>
          <button type="submit" className="btn-success" style={{ width: '100%', minHeight: 44 }} disabled={loading}>
            {loading ? 'Connexion…' : 'Se connecter'}
          </button>
          {status && <p className="form-error">{status}</p>}
        </form>

        <div style={{ marginTop: 20, textAlign: 'center', fontSize: 12, color: 'var(--muted)' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ verticalAlign: 'middle', marginRight: 4 }}>
            <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          Connexion sécurisée — Plateforme officielle DNTT
        </div>
      </div>
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────
export default function App() {
  const [route, setRoute] = useState<AppRoute>(getRouteFromHash());
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [role, setRole] = useState<UserRole>('candidate');
  const [loading, setLoading] = useState(true);

  // Écouter les changements de hash
  useEffect(() => {
    const onHash = () => setRoute(getRouteFromHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  // Restaurer la session au démarrage
  useEffect(() => {
    if (!getAccessToken() && !getRefreshToken()) {
      setLoading(false);
      if (getRouteFromHash() !== 'login') window.location.hash = '#/login';
      return;
    }
    getCurrentUser()
      .then(u => {
        setCurrentUser(u);
        setRole(normalizeRole(u.role));
      })
      .catch(() => {
        logoutUser();
        window.location.hash = '#/login';
      })
      .finally(() => setLoading(false));
  }, []);

  // Session expirée
  useEffect(() => {
    function onExpired() {
      setCurrentUser(null); setRole('candidate');
      window.location.hash = '#/login';
    }
    window.addEventListener('coderoute:session-expired', onExpired);
    return () => window.removeEventListener('coderoute:session-expired', onExpired);
  }, []);

  async function handleLogin(email: string, pass: string) {
    await loginUser(email, pass);
    const u = await getCurrentUser();
    setCurrentUser(u);
    setRole(normalizeRole(u.role));
    window.location.hash = '#/';
  }

  function handleLogout() {
    clearCsrfToken(); logoutUser();
    setCurrentUser(null); setRole('candidate');
    window.location.hash = '#/login';
  }

  // Navigation filtrée par rôle réel
  const visibleNav = navigationItems.filter(n => n.roles.includes(role));
  const curHref = route === 'home' ? '#/' : `#/${route}`;
  const hasAccess = canAccessRoute(role, curHref);
  const isLoggedIn = Boolean(currentUser);

  // Page courante
  let page: React.ReactElement;
  if (loading) {
    page = <Loading />;
  } else if (route === 'login' || !isLoggedIn) {
    page = <LoginPage onLogin={handleLogin} />;
  } else if (!hasAccess) {
    page = <AccessDenied role={role} />;
  } else {
    const pageMap: Record<AppRoute, React.ReactElement> = {
      home:        <HomePage />,
      training:    <TrainingPage />,
      candidate:   <CandidatePage />,
      center:      <CenterPage />,
      school:      <DrivingSchoolPage />,
      ministerial: <MinisterialPage />,
      admin:       <AdminPage />,
      dossier:     <InstitutionalDossierPage />,
      exam:        <ExamPage />,
      results:     <ResultsPage />,
      account:     <AccountPage currentUser={currentUser} />,
      login:       <LoginPage onLogin={handleLogin} />,
    };
    page = pageMap[route];
  }

  // Topbar — uniquement si connecté
  const showTopbar = isLoggedIn && route !== 'login' && !loading;

  return (
    <main className="app-shell">
      {showTopbar && (
        <header className="topbar">
          <a href="#/" className="brand">
            <div className="brand-logo">CR</div>
            <div className="brand-text">
              <strong>CodeRoute Guinée</strong>
              <small>Plateforme nationale DNTT</small>
            </div>
          </a>

          <nav className="nav-links" role="navigation" aria-label="Navigation principale">
            {visibleNav.map(item => {
              const r = item.href.replace('#/', '') || 'home';
              const label = t(`nav.${r}`) !== `nav.${r}` ? t(`nav.${r}`) : item.label;
              const NAV_ICONS: Record<string, React.ReactElement> = {
                home:        <IconHome size={15} />,
                training:    <IconTarget size={15} />,
                elearning:   <IconBook size={15} />,
                candidate:   <IconUser size={15} />,
                center:      <IconBuilding size={15} />,
                school:      <IconGraduate size={15} />,
                ministerial: <IconLandmark size={15} />,
                admin:       <IconDashboard size={15} />,
                dossier:     <IconClipboard size={15} />,
                results:     <IconBarChart size={15} />,
                exam:        <IconTarget size={15} />,
              };
              return (
                <a key={item.href} href={item.href} className={route === r ? 'active' : ''}>
                  {NAV_ICONS[r] && <span className="nav-icon" aria-hidden="true">{NAV_ICONS[r]}</span>}
                  <span>{label}</span>
                </a>
              );
            })}
            <a href="#/account" className={route === 'account' ? 'active' : ''}>
              <span className="nav-icon" aria-hidden="true"><IconSettings size={15} /></span>
              <span>Mon compte</span>
            </a>
          </nav>

          <div className="session-panel">
            <LocaleSwitcher />
            <span title={`${currentUser?.full_name} · ${role}`}>
              {currentUser?.full_name?.split(' ')[0] ?? 'Agent'}
            </span>
            <ThemeToggle compact />
            <button type="button" onClick={handleLogout}>Déconnexion</button>
          </div>
        </header>
      )}

      <AuthSessionProvider currentUser={currentUser} isPresentationMode={false} role={role}>
        {page}
      </AuthSessionProvider>
    </main>
  );
}
