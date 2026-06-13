export type UserRole = 'candidate' | 'center' | 'admin' | 'super_admin';

export type NavigationItem = {
  label: string;
  href: string;
  roles: UserRole[];
};

export const demoRoles: Array<{ label: string; value: UserRole }> = [
  { label: 'Candidat', value: 'candidate' },
  { label: 'Centre agree', value: 'center' },
  { label: 'Admin national', value: 'admin' },
  { label: 'Super admin', value: 'super_admin' },
];

export const navigationItems: NavigationItem[] = [
  { label: 'Candidat', href: '#/candidate', roles: ['candidate', 'admin', 'super_admin'] },
  { label: 'Centre', href: '#/center', roles: ['center', 'admin', 'super_admin'] },
  { label: 'Admin', href: '#/admin', roles: ['admin', 'super_admin'] },
  { label: 'Examen', href: '#/exam', roles: ['candidate', 'center', 'admin', 'super_admin'] },
  { label: 'Resultats', href: '#/results', roles: ['candidate', 'admin', 'super_admin'] },
];

export function canAccessRoute(role: UserRole, href: string): boolean {
  const item = navigationItems.find((navItem) => navItem.href === href);
  return item ? item.roles.includes(role) : true;
}
