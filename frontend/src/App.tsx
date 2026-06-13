import { useEffect, useState } from 'react';

import { demoRoles, navigationItems, type UserRole } from './auth';
import { AdminPage, CandidatePage, CenterPage, ExamPage, HomePage, ResultsPage } from './pages';

type AppRoute = 'home' | 'candidate' | 'center' | 'admin' | 'exam' | 'results';

function getRouteFromHash(): AppRoute {
  const route = window.location.hash.replace('#/', '');
  if (route === 'candidate' || route === 'center' || route === 'admin' || route === 'exam' || route === 'results') {
    return route;
  }
  return 'home';
}

export default function App() {
  const [route, setRoute] = useState<AppRoute>(getRouteFromHash());
  const [role, setRole] = useState<UserRole>('super_admin');

  useEffect(() => {
    const onHashChange = () => setRoute(getRouteFromHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const visibleNavigation = navigationItems.filter((item) => item.roles.includes(role));

  const page = {
    home: <HomePage />,
    candidate: <CandidatePage />,
    center: <CenterPage />,
    admin: <AdminPage />,
    exam: <ExamPage />,
    results: <ResultsPage />,
  }[route];

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
