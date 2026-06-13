import { useEffect, useState } from 'react';

import { AdminPage, CandidatePage, CenterPage, ExamPage, HomePage } from './pages';

type AppRoute = 'home' | 'candidate' | 'center' | 'admin' | 'exam';

function getRouteFromHash(): AppRoute {
  const route = window.location.hash.replace('#/', '');
  if (route === 'candidate' || route === 'center' || route === 'admin' || route === 'exam') {
    return route;
  }
  return 'home';
}

export default function App() {
  const [route, setRoute] = useState<AppRoute>(getRouteFromHash());

  useEffect(() => {
    const onHashChange = () => setRoute(getRouteFromHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const page = {
    home: <HomePage />,
    candidate: <CandidatePage />,
    center: <CenterPage />,
    admin: <AdminPage />,
    exam: <ExamPage />,
  }[route];

  return (
    <main className="app-shell">
      <nav className="top-nav">
        <strong><a href="#/" className="brand-link">CodeRoute Guinee</a></strong>
        <div>
          <a href="#/candidate" className={route === 'candidate' ? 'active' : ''}>Candidat</a>
          <a href="#/center" className={route === 'center' ? 'active' : ''}>Centre</a>
          <a href="#/admin" className={route === 'admin' ? 'active' : ''}>Admin</a>
          <a href="#/exam" className={route === 'exam' ? 'active' : ''}>Examen</a>
        </div>
      </nav>
      {page}
    </main>
  );
}
