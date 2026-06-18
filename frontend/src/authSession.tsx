import { createContext, useContext, type ReactNode } from 'react';

import type { AuthUser } from './authClient';
import type { UserRole } from './auth';

type AuthSessionContextValue = {
  currentUser: AuthUser | null;
  isPresentationMode: boolean;
  role: UserRole;
};

const AuthSessionContext = createContext<AuthSessionContextValue>({
  currentUser: null,
  isPresentationMode: true,
  role: 'candidate',
});

export function AuthSessionProvider({
  children,
  currentUser,
  isPresentationMode,
  role,
}: AuthSessionContextValue & { children: ReactNode }) {
  return (
    <AuthSessionContext.Provider value={{ currentUser, isPresentationMode, role }}>
      {children}
    </AuthSessionContext.Provider>
  );
}

export function useAuthSession(): AuthSessionContextValue {
  return useContext(AuthSessionContext);
}

export function canUseProtectedActions(currentUser: AuthUser | null, isPresentationMode: boolean, allowedRoles: UserRole[]): boolean {
  if (isPresentationMode || !currentUser) {
    return false;
  }
  return allowedRoles.includes(currentUser.role as UserRole);
}
