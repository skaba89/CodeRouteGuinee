export type UserRole = 'candidate' | 'center' | 'admin' | 'super_admin' | 'driving_school';

export type NavigationItem = {
  label: string;
  href: string;
  roles: UserRole[];
};

export const demoRoles: Array<{ label: string; value: UserRole }> = [
  { label: 'Candidat',        value: 'candidate' },
  { label: 'Centre agréé',    value: 'center' },
  { label: 'Auto-école',      value: 'driving_school' },
  { label: 'Admin national',  value: 'admin' },
  { label: 'Super admin',     value: 'super_admin' },
];

export const navigationItems: NavigationItem[] = [
  { label: 'Accueil',         href: '#/',           roles: ['candidate','center','driving_school','admin','super_admin'] },
  { label: 'Entraînement',    href: '#/training',   roles: ['candidate','driving_school','admin','super_admin'] },
  { label: 'Examen',          href: '#/exam',       roles: ['candidate','center','admin','super_admin'] },
  { label: 'Résultats',       href: '#/results',    roles: ['candidate','admin','super_admin'] },
  { label: 'Espace candidat', href: '#/candidate',  roles: ['candidate','admin','super_admin'] },
  { label: 'Espace centre',   href: '#/center',     roles: ['center','admin','super_admin'] },
  { label: 'Auto-école',      href: '#/school',     roles: ['driving_school','admin','super_admin'] },
  { label: 'Administration',  href: '#/admin',      roles: ['admin','super_admin'] },
  { label: 'Dossier État',    href: '#/dossier',    roles: ['admin','super_admin'] },
];

export function canAccessRoute(role: UserRole, href: string): boolean {
  const item = navigationItems.find(n => n.href === href);
  return item ? item.roles.includes(role) : true;
}
