import './edgeExamBootstrap';
import React, { useEffect, useState } from 'react';
import { InstallPWA } from './components/pwa-install-prompt';
import ReactDOM from 'react-dom/client';
import App from './App';
import { ErrorBoundary } from './ErrorBoundary';
import EdgeExamEntry from './pages/EdgeExamEntry';
import EdgePendingPage from './pages/EdgePendingPage';
import { hasPendingEdgeBootstrap } from './edgeExamSession';
import './examDeviceFetchBridge';
import './edgeExamFetchBridge';
import './styles.css';

function RootSurface() {
  const [hash, setHash] = useState(() => window.location.hash || '#/');

  useEffect(() => {
    const onHashChange = () => setHash(window.location.hash || '#/');
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  if (hash.startsWith('#/edge-pending')) return <EdgePendingPage />;
  if (hash === '#/exam' && hasPendingEdgeBootstrap()) return <EdgeExamEntry />;
  return <App />;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary><RootSurface /></ErrorBoundary>
    <InstallPWA />
  </React.StrictMode>,
);
