import { FormEvent, useEffect, useState } from 'react';

import { canAccessRoute, demoRoles, navigationItems, type UserRole } from './auth';
import { getCurrentUser, loginUser, logoutUser } from './authClient';
import { AdminPage, CandidatePage, CenterPage, ExamPage, HomePage, ResultsPage } from './pages';
import './role.css';

type AppRoute = 'home' | 'candidate' | 'center' | 'admin' | 'exam' | 'results' | 'login';

const ROLE_STORAGE_KEY = 'coderoute-demo-role';

function getRouteFromHash(): AppRoute {
  const route = window.location.hash.replace('#/', '');
  if (route === 'candidate' || route === 'center' || route === 'admin' || route === 'exam' || route === 'results' || route === 'login') {
    return route;
  }
  return 'home';
}

function normalizeRole(role: string): UserRole {
  return demoRoles.some((item) => item.value === role) ? role as UserRole : 'candidate';
}

function getInitialRole(): UserRole {
  const savedRole = window.localStorage.getItem(ROLE_STORAGE_KEY);
  if (savedRole && demoRoles.some((item) => item.value === savedRole)) {
    return savedRole as UserRole;
  }
  return 'super_admin';
}

function AccessDenied({ role }: { role: UserRole }) {
  return (
    <section className="screen access-denied">
      <p className="eyebrow dark">Accès restreint</p>
      <h2>Page non autorisée pour ce rôle</h2>
      <p>Le rôle actif <strong>{role}</strong> ne dispose pas des permissions nécessaires pour consulter cette page.</p>
      <div className="actions result-actions">
        <a href="#/">Retour à l’accueil</a>
      </div>
    </section>
  );
}

function LoginPage({ role, onRoleChange, onLogin }: { role: UserRole; onRoleChange: (role: UserRole) => void; onLogin: (email: string, password: string) => Promise<void> }) {
  const [email, setEmail] = useState('admin@coderoute.gov.gn');
  const [password, setPassword] = useState('');
  const [status, setStatus] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus('Connexion en cours...');
    try {
      await onLogin(email, password);
      setStatus('Connexion réussie. Redirection...');
    } catch {
      setStatus('Connexion impossible avec ces identifiants. Vérifiez le compte ou utilisez le mode démo.');
    }
  }

  return (
    <section className="screen login-screen">
      <p className="eyebrow dark">Connexion sécurisée</p>
      <h2>Accéder à CodeRoute Guinée</h2>
      <p>Connexion réelle via JWT ou sélection d’un rôle de démonstration pendant la phase MVP.</p>
      <form className="login-form" onSubmit={handleSubmit}>
        <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" type="email" />
        <input value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Mot de passe" type="password" />
        <button type="submit">Se connecter</button>
      </form>
      {status && <p className="login-status">{status}</p>}
      <div className="login-role-grid">
        {demoRoles.map((item) => (
          <button key={item.value} className={role === item.value ? 'active-role' : ''} onClick={() => onRoleChange(item.value)}>
            {item.label}
          </button>
        ))}
      </div>
      <div className="actions result-actions">
        <a href="#/">Continuer avec ce rôle</a>
      </div>
    </section>
  );
}

export default function App() {
  const [route, setRoute] = useState<AppRoute>(getRouteFromHash());
  const [role, setRole] = useState<UserRole>(getInitialRole);

  useEffect(() => {
    const onHashChange = () => setRoute(getRouteFromHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  useEffect(() => {
    window.localStorage.setItem(ROLE_STORAGE_KEY, role);
  }, [role]);

  async function handleLogin(email: string, password: string) {
    await loginUser(email, password);
    const user = await getCurrentUser();
    setRole(normalizeRole(user.role));
    window.location.hash = '#/';
  }

  function handleLogout() {
    logoutUser();
    window.localStorage.removeItem(ROLE_STORAGE_KEY);
    setRole('super_admin');
    window.location.hash = '#/login';
  }

  const visibleNavigation = navigationItems.filter((item) => item.roles.includes(role));
  const currentHref = route === 'home' ? '#/' : `#/${route}`;
  const hasAccess = canAccessRoute(role, currentHref);
  const currentRoleLabel = demoRoles.find((item) => item.value === role)?.label ?? role;

  const page = route === 'login' ? <LoginPage role={role} onRoleChange={setRole} onLogin={handleLogin} /> : hasAccess ? {
    home: <HomePage />,
    candidate: <CandidatePage />,
    center: <CenterPage />,
    admin: <AdminPage />,
    exam: <ExamPage />,
    results: <ResultsPage />,
    login: <LoginPage role={role} onRoleChange={setRole} onLogin={handleLogin} />,
  }[route] : <AccessDenied role={role} />;

  return (
    <main className="app-shell">
      <nav className="top-nav" aria-label="Navigation principale">
        <a href="#/" className="brand-link" aria-label="Retour à l’accueil CodeRoute Guinée">
          <span className="brand-logo">CR</span>
          <span className="brand-text">
            <strong>CodeRoute Guinée</strong>
            <small>Plateforme nationale d’examen</small>
          </span>
        </a>

        <div className="nav-links">
          {visibleNavigation.map((item) => {
            const itemRoute = item.href.replace('#/', '') || 'home';
            return <a key={item.href} href={item.href} className={route === itemRoute ? 'active' : ''}>{item.label}</a>;
          })}
          <a href="#/login" className={route === 'login' ? 'active' : ''}>Connexion</a>
        </div>

        <div className="session-panel">
          <span>Session : {currentRoleLabel}</span>
          <button onClick={handleLogout}>Déconnexion</button>
        </div>

        <label className="role-switcher">
          Rôle
          <select value={role} onChange={(event) => setRole(event.target.value as UserRole)}>
            {demoRoles.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
        </label>
      </nav>
      {page}
    </main>
  );
}
