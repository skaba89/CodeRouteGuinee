/**
 * CodeRoute Guinée — Bibliothèque d'icônes SVG
 * Ligne fine (stroke 1.5–2), design institutionnel, compatible dark mode.
 * Chaque icône accepte className et size (défaut: 18).
 */

import type { SVGProps } from 'react';

interface IconProps extends SVGProps<SVGSVGElement> {
  size?: number;
  className?: string;
}

const base = (size: number, props: IconProps) => ({
  width: size,
  height: size,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.75,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  ...props,
});

// ── Navigation ────────────────────────────────────────────────────
export function IconHome({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M3 12L12 3l9 9"/><path d="M9 21V12h6v9"/><path d="M5 10v11h14V10"/></svg>;
}
export function IconDashboard({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>;
}
export function IconClipboard({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><rect x="8" y="2" width="8" height="4" rx="1"/><path d="M8 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V4a2 2 0 00-2-2h-2"/><path d="M9 12h6M9 16h4"/></svg>;
}
export function IconBook({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>;
}
export function IconGraduate({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M22 10v6M2 10l10-5 10 5-10 5-10-5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>;
}
export function IconBuilding({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><rect x="2" y="7" width="20" height="14" rx="1"/><path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2"/><path d="M9 14h.01M12 14h.01M15 14h.01M9 18h.01M12 18h.01M15 18h.01"/></svg>;
}
export function IconLandmark({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><line x1="3" y1="22" x2="21" y2="22"/><line x1="6" y1="18" x2="6" y2="11"/><line x1="10" y1="18" x2="10" y2="11"/><line x1="14" y1="18" x2="14" y2="11"/><line x1="18" y1="18" x2="18" y2="11"/><polygon points="12 2 20 7 4 7"/></svg>;
}
export function IconMap({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>;
}

// ── Utilisateurs ──────────────────────────────────────────────────
export function IconUser({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>;
}
export function IconUsers({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="9" cy="7" r="3"/><path d="M3 20c0-3 2.7-5.5 6-5.5"/><circle cx="17" cy="9" r="3"/><path d="M21 20c0-3.5-3-6-7-6s-7 2.5-7 6"/></svg>;
}
export function IconUserPlus({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="10" cy="8" r="4"/><path d="M2 20c0-4 3.6-7 8-7"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="16" y1="11" x2="22" y2="11"/></svg>;
}
export function IconUserCheck({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="9" cy="7" r="4"/><path d="M3 20c0-4 2.7-7 6-7"/><polyline points="16 11 18 13 22 9"/></svg>;
}
export function IconShield({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>;
}
export function IconKey({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="7.5" cy="7.5" r="4.5"/><path d="M10.9 10.9L21 21"/><line x1="16" y1="16" x2="19" y2="13"/></svg>;
}
export function IconLock({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>;
}
export function IconId({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><rect x="2" y="7" width="20" height="14" rx="2"/><circle cx="8" cy="13" r="2"/><path d="M13 11h4M13 15h4"/></svg>;
}

// ── Documents & Données ───────────────────────────────────────────
export function IconFile({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>;
}
export function IconFileText({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="12" y2="17"/></svg>;
}
export function IconFileCheck({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><polyline points="9 15 11 17 15 13"/></svg>;
}
export function IconClipboardCheck({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><rect x="8" y="2" width="8" height="4" rx="1"/><path d="M8 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V4a2 2 0 00-2-2h-2"/><polyline points="9 12 11 14 15 10"/></svg>;
}
export function IconDownload({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>;
}
export function IconUpload({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>;
}
export function IconPrinter({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>;
}

// ── Calendrier & Temps ────────────────────────────────────────────
export function IconCalendar({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>;
}
export function IconClock({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>;
}
export function IconBell({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>;
}

// ── Paiements & Finance ───────────────────────────────────────────
export function IconCreditCard({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/><line x1="6" y1="16" x2="10" y2="16"/></svg>;
}
export function IconWallet({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M2 7h20v14H2z"/><path d="M16 13a1 1 0 000 2h2a1 1 0 000-2h-2z"/><path d="M2 7V5a2 2 0 012-2h16a2 2 0 012 2v2"/></svg>;
}
export function IconBanknote({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/></svg>;
}
export function IconTrendingUp({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>;
}
export function IconBarChart({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/></svg>;
}

// ── Statuts & Actions ─────────────────────────────────────────────
export function IconCheck({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><polyline points="20 6 9 17 4 12"/></svg>;
}
export function IconCheckCircle({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="12" cy="12" r="10"/><polyline points="9 12 11 14 15 10"/></svg>;
}
export function IconX({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>;
}
export function IconXCircle({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>;
}
export function IconAlertTriangle({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>;
}
export function IconAlertCircle({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>;
}
export function IconInfo({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>;
}
export function IconShieldAlert({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>;
}
export function IconFlag({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>;
}

// ── Navigation & UI ───────────────────────────────────────────────
export function IconArrowLeft({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>;
}
export function IconArrowRight({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>;
}
export function IconChevronRight({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><polyline points="9 18 15 12 9 6"/></svg>;
}
export function IconChevronDown({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><polyline points="6 9 12 15 18 9"/></svg>;
}
export function IconRefresh({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>;
}
export function IconSearch({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>;
}
export function IconFilter({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>;
}
export function IconSettings({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>;
}
export function IconLogOut({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>;
}
export function IconMoon({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>;
}
export function IconSun({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>;
}
export function IconPlus({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>;
}
export function IconEdit({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>;
}
export function IconTrash({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>;
}
export function IconEye({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>;
}
export function IconExternalLink({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>;
}
export function IconMoreVertical({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>;
}
export function IconTarget({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>;
}
export function IconAward({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89L17 22l-5-3-5 3 1.523-9.11"/></svg>;
}
export function IconZap({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>;
}
export function IconActivity({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>;
}
export function IconGlobe({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg>;
}
export function IconPhone({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.81 19.79 19.79 0 01.1 1.18 2 2 0 012.1 0h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>;
}
export function IconMail({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22 6 12 13 2 6"/></svg>;
}
export function IconMapPin({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>;
}
export function IconVolume({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 010 7.07"/><path d="M19.07 4.93a10 10 0 010 14.14"/></svg>;
}
export function IconVolumeX({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>;
}
export function IconList({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>;
}
export function IconGrid({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>;
}
export function IconImage({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>;
}
export function IconTag({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>;
}

// ── Transport / Code de la route ──────────────────────────────────
export function IconCar({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><rect x="1" y="9" width="22" height="11" rx="2"/><path d="M5 9V5a1 1 0 011-1h12a1 1 0 011 1v4"/><circle cx="7" cy="20" r="1"/><circle cx="17" cy="20" r="1"/></svg>;
}
export function IconTruck({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><rect x="1" y="3" width="15" height="13" rx="1"/><path d="M16 8h4l3 5v3h-7V8z"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>;
}
export function IconNavigation({ size = 18, ...p }: IconProps) {
  return <svg {...base(size, p)}><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>;
}

// ── Drapeau Guinée SVG (sans emoji) ──────────────────────────────
export function FlagGuinea({ size = 40, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size * 0.67}
      viewBox="0 0 60 40"
      className={className}
      style={{ borderRadius: 2, boxShadow: '0 2px 8px rgba(0,0,0,.25)' }}
    >
      <rect width="20" height="40" fill="#CE1126"/>
      <rect x="20" width="20" height="40" fill="#FCD116"/>
      <rect x="40" width="20" height="40" fill="#006B3F"/>
    </svg>
  );
}

// ── Badge statut composant ────────────────────────────────────────
export function StatusIcon({ status }: { status: string }) {
  if (status === 'ok' || status === 'passed' || status === 'active' || status === 'confirmed' || status === 'paid')
    return <IconCheckCircle size={16} style={{ color: 'var(--guinea-green)' }}/>;
  if (status === 'error' || status === 'failed' || status === 'rejected')
    return <IconXCircle size={16} style={{ color: 'var(--red)' }}/>;
  if (status === 'warning' || status === 'pending')
    return <IconAlertTriangle size={16} style={{ color: 'var(--gold)' }}/>;
  return <IconInfo size={16} style={{ color: 'var(--blue)' }}/>;
}
