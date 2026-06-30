import { createContext, useContext, type ReactNode } from 'react';
import type { AuthUser } from './authClient';
import type { UserRole } from './auth';

type AuthSessionContextValue = {
  currentUser: AuthUser | null;
  isPresentationMode: boolean; // toujours false — conservé pour compatibilité pages
  role: UserRole;
};

const AuthSessionContext = createContext<AuthSessionContextValue>({
  currentUser: null,
  isPresentationMode: false,
  role: 'candidate',
});

export function AuthSessionProvider({
  children, currentUser, role,
}: { children: ReactNode; currentUser: AuthUser | null; isPresentationMode: boolean; role: UserRole }) {
  return (
    <AuthSessionContext.Provider value={{ currentUser, isPresentationMode: false, role }}>
      {children}
    </AuthSessionContext.Provider>
  );
}

export function useAuthSession(): AuthSessionContextValue {
  return useContext(AuthSessionContext);
}

/** Vérifie que l'utilisateur est connecté et possède un des rôles autorisés. */
export function canUseProtectedActions(
  currentUser: AuthUser | null,
  _isPresentationMode: boolean, // ignoré — conservé pour compatibilité
  allowedRoles: UserRole[],
): boolean {
  if (!currentUser) return false;
  return allowedRoles.includes(currentUser.role as UserRole);
}
