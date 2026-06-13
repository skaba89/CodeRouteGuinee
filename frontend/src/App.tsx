import { useEffect, useState } from 'react';

import { canAccessRoute, demoRoles, navigationItems, type UserRole } from './auth';
import { AdminPage, CandidatePage, CenterPage, ExamPage, HomePage, ResultsPage } from './pages';
import './role.css';

type AppRoute = 'home' | 'candidate' | 'center' | 'admin' | 'exam' | 'results';

const ROLE_STORAGE_KEY = 'coderoute-demo-role';

function getRouteFromHash(): AppRoute {
  const route = window.location.hash.replace('#/', '');
  if (route === 'candidate' || route === 'center' || route === 'admin' || route === 'exam' || route === 'results') {
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

  const page = hasAccess ? {
    home: <HomePage />,
    candidate: <CandidatePage />,
    center: <CenterPage />,
    admin: <AdminPage />,
    exam: <ExamPage />,
    results: <ResultsPage />,
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
