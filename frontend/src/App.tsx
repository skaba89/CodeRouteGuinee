import { useEffect, useState } from 'react';

import { canAccessRoute, demoRoles, navigationItems, type UserRole } from './auth';
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

function getInitialRole(): UserRole {
  const savedRole = window.localStorage.getItem(ROLE_STORAGE_KEY) as UserRole | null;
  return demoRoles.some((item) => item.value === savedRole) ? savedRole : 'super_admin';
}

function AccessDenied({ role }: { role: UserRole }) {
  return (
    <section className="screen access-denied">
      <p className="eyebrow dark">Acces restreint</p>
      <h2>Page non autorisee pour ce role</h2>
      <p>Le role actif <strong>{role}</strong> ne dispose pas des permissions necessaires pour consulter cette page.</p>
      <div className="actions result-actions">
        <a href="#/">Retour accueil</a>
      </div>
    </section>
  );
}

function LoginPage({ role, onRoleChange }: { role: UserRole; onRoleChange: (role: UserRole) => void }) {
  return (
    <section className="screen login-screen">
      <p className="eyebrow dark">Connexion de demonstration</p>
      <h2>Choisir un espace utilisateur</h2>
      <p>Cette page prepare le futur branchement avec l'authentification reelle et les jetons JWT.</p>
      <div className="login-role-grid">
        {demoRoles.map((item) => (
          <button key={item.value} className={role === item.value ? 'active-role' : ''} onClick={() => onRoleChange(item.value)}>
            {item.label}
          </button>
        ))}
      </div>
      <div className="actions result-actions">
        <a href="#/">Continuer avec ce role</a>
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

  const visibleNavigation = navigationItems.filter((item) => item.roles.includes(role));
  const currentHref = route === 'home' ? '#/' : `#/${route}`;
  const hasAccess = canAccessRoute(role, currentHref);

  const page = route === 'login' ? <LoginPage role={role} onRoleChange={setRole} /> : hasAccess ? {
    home: <HomePage />,
    candidate: <CandidatePage />,
    center: <CenterPage />,
    admin: <AdminPage />,
    exam: <ExamPage />,
    results: <ResultsPage />,
    login: <LoginPage role={role} onRoleChange={setRole} />,
  }[route] : <AccessDenied role={role} />;

  return (
    <main className="app-shell">
      <nav className="top-nav">
        <strong><a href="#/" className="brand-link">CodeRoute Guinee</a></strong>
        <div>
          {visibleNavigation.map((item) => {
            const itemRoute = item.href.replace('#/', '') || 'home';
            return <a key={item.href} href={item.href} className={route === itemRoute ? 'active' : ''}>{item.label}</a>;
          })}
          <a href="#/login" className={route === 'login' ? 'active' : ''}>Connexion</a>
        </div>
        <label className="role-switcher">
          Role
          <select value={role} onChange={(event) => setRole(event.target.value as UserRole)}>
            {demoRoles.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
        </label>
      </nav>
      {page}
    </main>
  );
}
