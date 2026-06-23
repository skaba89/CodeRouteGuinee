import React from 'react';
import { InstallPWA } from './components/pwa-install-prompt';
import ReactDOM from 'react-dom/client';
import App from './App';
import { ErrorBoundary } from './ErrorBoundary';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary><App /></ErrorBoundary>
    <InstallPWA />
  </React.StrictMode>,
);
