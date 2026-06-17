import { FormEvent, useEffect, useState } from 'react';

import { canAccessRoute, demoRoles, navigationItems, type UserRole } from './auth';
import { type AuthUser, changePassword, getAccessToken, getCurrentUser, loginUser, logoutUser } from './authClient';
import { AdminPage, CandidatePage, CenterPage, ExamPage, HomePage, InstitutionalDossierPage, ResultsPage } from './pages';
import './role.css';

type AppRoute = 'home' | 'candidate' | 'center' | 'admin' | 'exam' | 'results' | 'dossier' | 'login' | 'account';

const ROLE_STORAGE_KEY = 'coderoute-demo-role';
const PRESENTATION_MODE_STORAGE_KEY = 'coderoute-presentation-mode';

function getRouteFromHash(): AppRoute {
  const route = window.location.hash.replace('#/', '');
  if (route === 'candidate' || route === 'center' || route === 'admin' || route === 'exam' || route === 'results' || route === 'dossier' || route === 'login' || route === 'account') {
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

function getInitialPresentationMode(): boolean {
  if (!getAccessToken()) {
    return true;
  }
  return window.localStorage.getItem(PRESENTATION_MODE_STORAGE_KEY) !== 'false';
}

function AccessDenied({ role, isPresentationMode }: { role: UserRole; isPresentationMode: boolean }) {
  return (
    <section className="screen access-denied">
      <p className="eyebrow dark">Acces restreint</p>
      <h2>Page non autorisee pour ce role</h2>
      <p>Le role actif <strong>{role}</strong> ne dispose pas des permissions necessaires pour consulter cette page.</p>
      {!isPresentationMode && <p>Connectez-vous avec un compte habilite ou demandez une elevation de role au super administrateur.</p>}
      <div className="actions result-actions">
        <a href="#/">Retour a l'accueil</a>
      </div>
    </section>
  );
}

function LoadingSession() {
  return (
    <section className="screen login-screen">
      <p className="eyebrow dark">Session securisee</p>
      <h2>Verification de la session</h2>
      <p>Controle du token et recuperation du profil utilisateur en cours.</p>
    </section>
  );
}

function AccountPage({ currentUser }: { currentUser: AuthUser | null }) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [status, setStatus] = useState<string | null>(null);

  async function handlePasswordChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus(null);

    if (newPassword.length < 12) {
      setStatus('Le nouveau mot de passe doit contenir au moins 12 caracteres.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setStatus('La confirmation ne correspond pas au nouveau mot de passe.');
      return;
    }

    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setStatus('Mot de passe mis a jour. La modification est journalisee dans l audit.');
    } catch {
      setStatus('Changement impossible : verifiez le mot de passe actuel et la session.');
    }
  }

  return (
    <section className="screen account-screen">
      <p className="eyebrow dark">Compte institutionnel</p>
      <h2>Mon compte</h2>
      <p>Gestion du profil connecte et rotation du mot de passe pour les agents habilites.</p>
      <div className="account-profile-grid">
        <article>
          <span>Agent</span>
          <strong>{currentUser?.full_name ?? 'Utilisateur connecte'}</strong>
          <small>{currentUser?.email ?? 'Email indisponible'}</small>
        </article>
        <article>
          <span>Role</span>
          <strong>{currentUser?.role ?? 'session'}</strong>
          <small>{currentUser?.is_active === false ? 'Compte inactif' : 'Compte actif'}</small>
        </article>
      </div>
      <form className="account-password-form" onSubmit={handlePasswordChange}>
        <label>Mot de passe actuel<input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /></label>
        <label>Nouveau mot de passe<input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label>
        <label>Confirmer<input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} /></label>
        <button type="submit" disabled={currentPassword.length < 8 || newPassword.length < 12 || confirmPassword.length < 12}>Changer le mot de passe</button>
      </form>
      {status && <p className={status.includes('impossible') || status.includes('doit') || status.includes('confirmation') ? 'form-error' : 'login-status'}>{status}</p>}
    </section>
  );
}

function LoginPage({
  currentUser,
  isPresentationMode,
  role,
  onRoleChange,
  onLogin,
}: {
  currentUser: AuthUser | null;
  isPresentationMode: boolean;
  role: UserRole;
  onRoleChange: (role: UserRole) => void;
  onLogin: (email: string, password: string) => Promise<void>;
}) {
  const [email, setEmail] = useState('admin@coderoute.gov.gn');
  const [password, setPassword] = useState('');
  const [status, setStatus] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus('Connexion en cours...');
    try {
      await onLogin(email, password);
      setStatus('Connexion reussie. Redirection...');
    } catch {
      setStatus('Connexion impossible avec ces identifiants. Verifiez le compte ou utilisez le mode presentation.');
    }
  }

  return (
    <section className="screen login-screen">
      <p className="eyebrow dark">Connexion securisee</p>
      <h2>Acceder a CodeRoute Guinee</h2>
      <p>Connexion reelle via JWT pour les agents habilites. Le mode presentation reste disponible pour les demonstrations controlees.</p>
      <div className={isPresentationMode ? 'auth-session-card presentation' : 'auth-session-card'}>
        <strong>{isPresentationMode ? 'Mode presentation actif' : `Session reelle : ${currentUser?.full_name ?? 'utilisateur connecte'}`}</strong>
        <span>{isPresentationMode ? 'Les roles ci-dessous servent uniquement a presenter les parcours.' : `${currentUser?.email ?? ''} - role ${currentUser?.role ?? role}`}</span>
      </div>
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
        <a href="#/">Continuer avec ce role</a>
      </div>
    </section>
  );
}

export default function App() {
  const [route, setRoute] = useState<AppRoute>(getRouteFromHash());
  const [role, setRole] = useState<UserRole>(getInitialRole);
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [isPresentationMode, setIsPresentationMode] = useState(getInitialPresentationMode);
  const [isSessionLoading, setIsSessionLoading] = useState(Boolean(getAccessToken()));

  useEffect(() => {
    const onHashChange = () => setRoute(getRouteFromHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  useEffect(() => {
    if (!getAccessToken()) {
      setIsPresentationMode(true);
      setIsSessionLoading(false);
      return;
    }

    getCurrentUser()
      .then((user) => {
        setCurrentUser(user);
        setRole(normalizeRole(user.role));
        setIsPresentationMode(false);
      })
      .catch(() => {
        logoutUser();
        setCurrentUser(null);
        setIsPresentationMode(true);
      })
      .finally(() => setIsSessionLoading(false));
  }, []);

  useEffect(() => {
    window.localStorage.setItem(ROLE_STORAGE_KEY, role);
  }, [role]);

  useEffect(() => {
    window.localStorage.setItem(PRESENTATION_MODE_STORAGE_KEY, String(isPresentationMode));
  }, [isPresentationMode]);

  function handleRoleChange(nextRole: UserRole) {
    logoutUser();
    setCurrentUser(null);
    setIsPresentationMode(true);
    setRole(nextRole);
  }

  async function handleLogin(email: string, password: string) {
    await loginUser(email, password);
    const user = await getCurrentUser();
    setCurrentUser(user);
    setRole(normalizeRole(user.role));
    setIsPresentationMode(false);
    window.location.hash = '#/';
  }

  function handleLogout() {
    logoutUser();
    setCurrentUser(null);
    setIsPresentationMode(true);
    setRole('candidate');
    window.location.hash = '#/login';
  }

  const visibleNavigation = navigationItems.filter((item) => item.roles.includes(role));
  const currentHref = route === 'home' ? '#/' : `#/${route}`;
  const hasAccess = canAccessRoute(role, currentHref);
  const currentRoleLabel = demoRoles.find((item) => item.value === role)?.label ?? role;
  const sessionLabel = isPresentationMode ? `Presentation : ${currentRoleLabel}` : `${currentUser?.full_name ?? 'Session reelle'} : ${currentRoleLabel}`;

  const loginPage = <LoginPage currentUser={currentUser} isPresentationMode={isPresentationMode} role={role} onRoleChange={handleRoleChange} onLogin={handleLogin} />;
  const page = isSessionLoading ? <LoadingSession /> : route === 'login' ? loginPage : hasAccess ? {
    home: <HomePage />,
    candidate: <CandidatePage />,
    center: <CenterPage />,
    admin: <AdminPage />,
    exam: <ExamPage />,
    results: <ResultsPage />,
    dossier: <InstitutionalDossierPage />,
    account: isPresentationMode ? <AccessDenied role={role} isPresentationMode={isPresentationMode} /> : <AccountPage currentUser={currentUser} />,
    login: loginPage,
  }[route] : <AccessDenied role={role} isPresentationMode={isPresentationMode} />;

  return (
    <main className="app-shell">
      <nav className="top-nav" aria-label="Navigation principale">
        <a href="#/" className="brand-link" aria-label="Retour a l'accueil CodeRoute Guinee">
          <span className="brand-logo">CR</span>
          <span className="brand-text">
            <strong>CodeRoute Guinee</strong>
            <small>Plateforme nationale d'examen</small>
          </span>
        </a>

        <div className="nav-links">
          {visibleNavigation.map((item) => {
            const itemRoute = item.href.replace('#/', '') || 'home';
            return <a key={item.href} href={item.href} className={route === itemRoute ? 'active' : ''}>{item.label}</a>;
          })}
          {!isPresentationMode && <a href="#/account" className={route === 'account' ? 'active' : ''}>Mon compte</a>}
          <a href="#/login" className={route === 'login' ? 'active' : ''}>Connexion</a>
        </div>

        <div className="session-panel">
          <span>{sessionLabel}</span>
          <button onClick={handleLogout}>{isPresentationMode ? 'Quitter' : 'Deconnexion'}</button>
        </div>

        {isPresentationMode && (
          <label className="role-switcher">
            Role presentation
            <select value={role} onChange={(event) => handleRoleChange(event.target.value as UserRole)}>
              {demoRoles.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
        )}
      </nav>
      {page}
    </main>
  );
}
