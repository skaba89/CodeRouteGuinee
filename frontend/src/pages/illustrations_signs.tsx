import React from 'react';
/**
 * CodeRoute Guinée — Illustrations panneaux manquants, style Ornikar
 * Complète illustrations.tsx : vue conducteur, route en perspective,
 * panneau sur poteau à droite, dashboard en bas.
 * Réutilise le même gabarit 800×420 pour cohérence visuelle parfaite.
 */

interface IllusProps { className?: string; style?: React.CSSProperties; }

// ── Helpers communs (mêmes proportions que illustrations.tsx) ──────────────
const SignClouds = ({ y = 70 }: { y?: number }) => <>
  <ellipse cx="160" cy={y}    rx="75" ry="28" fill="rgba(255,255,255,.87)"/>
  <ellipse cx="218" cy={y-12} rx="56" ry="22" fill="white"/>
  <ellipse cx="600" cy={y+8}  rx="82" ry="30" fill="rgba(255,255,255,.82)"/>
  <ellipse cx="658" cy={y-4}  rx="62" ry="24" fill="rgba(255,255,255,.88)"/>
</>;

const SignTrees = () => <>
  <rect x="42"  y="158" width="12" height="62" fill="#5d4037"/>
  <ellipse cx="48"  cy="150" rx="30" ry="34" fill="#2d6a1a"/>
  <rect x="108" y="167" width="10" height="53" fill="#5d4037"/>
  <ellipse cx="113" cy="161" rx="23" ry="27" fill="#3a7a22"/>
  <rect x="700" y="160" width="12" height="60" fill="#5d4037"/>
  <ellipse cx="706" cy="153" rx="28" ry="32" fill="#2d6a1a"/>
</>;

const SignDashboard = () => <>
  <rect x="0" y="370" width="800" height="50" fill="#1a1a1a"/>
  <ellipse cx="400" cy="370" rx="420" ry="30" fill="#222"/>
  <circle cx="400" cy="398" r="35" fill="none" stroke="#444" strokeWidth="10"/>
  <line x1="400" y1="363" x2="400" y2="433" stroke="#555" strokeWidth="5"/>
  <line x1="365" y1="398" x2="435" y2="398" stroke="#555" strokeWidth="5"/>
  <circle cx="400" cy="398" r="8" fill="#333"/>
</>;

const SignRoad = () => <>
  <polygon points="258,218 542,218 800,420 0,420" fill="#3d3d3d"/>
  <polygon points="390,220 410,220 406,268 394,268" fill="#f1c40f" opacity=".88"/>
  <polygon points="395,286 405,286 403,322 397,322" fill="#f1c40f" opacity=".7"/>
  <polygon points="396,338 404,338 404,368 396,368" fill="#f1c40f" opacity=".52"/>
  <polygon points="258,218 282,218 0,398 0,376" fill="white" opacity=".6"/>
  <polygon points="542,218 518,218 800,398 800,376" fill="white" opacity=".6"/>
</>;

const SignGrass = () => <>
  <polygon points="0,218 258,218 0,420"   fill="#4a8a2e"/>
  <polygon points="800,218 542,218 800,420" fill="#4a8a2e"/>
</>;

const SignPole = ({ x = 612, yTop = 150, h = 175 }: { x?: number; yTop?: number; h?: number }) =>
  <rect x={x} y={yTop} width="7" height={h} fill="#8a8a8a" rx="2"/>;

const SignBuilding = () => <>
  <rect x="20" y="168" width="60" height="50" fill="#c0b0a0"/>
  <rect x="22" y="170" width="56" height="46" fill="#d4c4b4"/>
  <rect x="30" y="178" width="14" height="18" fill="#7a9db5"/>
  <rect x="52" y="178" width="14" height="18" fill="#7a9db5"/>
  <rect x="32" y="198" width="18" height="20" fill="#8b6914"/>
</>;

/** Scène de base réutilisable : ciel + route + panneau rond rouge sur poteau */
function SignScene({
  panelContent, ariaLabel, skyId = 'sg', skyC1 = '#82C4E8', skyC2 = '#C4E4F4',
}: {
  panelContent: React.ReactNode;
  ariaLabel: string;
  skyId?: string;
  skyC1?: string;
  skyC2?: string;
}) {
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label={ariaLabel}>
      <defs>
        <linearGradient id={`i-${skyId}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={skyC1}/>
          <stop offset="100%" stopColor={skyC2}/>
        </linearGradient>
      </defs>
      <rect width="800" height="420" fill={`url(#i-${skyId})`}/>
      <SignClouds y={72}/>
      <SignGrass/>
      <rect x="0" y="215" width="800" height="5" fill="#3d6b25" opacity=".6"/>
      <SignRoad/>
      <SignTrees/>
      <SignBuilding/>
      <SignPole/>
      {panelContent}
      <SignDashboard/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// PANNEAUX DE VITESSE (30 / 90 / 100) — speed_50 existe déjà ailleurs
// ─────────────────────────────────────────────────────────────────────────
function SpeedPanel({ speed }: { speed: string }) {
  const fs = speed.length > 2 ? 46 : 56;
  return <>
    <circle cx="640" cy="220" r="64" fill="white" stroke="#C0392B" strokeWidth="13"/>
    <circle cx="640" cy="220" r="50" fill="white" stroke="#C0392B" strokeWidth="1"/>
    <text x="640" y="240" textAnchor="middle" fill="#0A2540" fontSize={fs}
      fontWeight="bold" fontFamily="Arial Black,sans-serif">{speed}</text>
  </>;
}
export function IllusSpeed30({ className, style }: IllusProps) {
  return <span className={className} style={style}>{SignScene({
    panelContent: <SpeedPanel speed="30"/>, ariaLabel: 'Limitation de vitesse 30 km/h — zone résidentielle', skyId: 'sp30',
  })}</span>;
}
export function IllusSpeed90({ className, style }: IllusProps) {
  return <span className={className} style={style}>{SignScene({
    panelContent: <SpeedPanel speed="90"/>, ariaLabel: 'Limitation de vitesse 90 km/h — route nationale', skyId: 'sp90',
    skyC1: '#6ab4d8', skyC2: '#b8dcee',
  })}</span>;
}
export function IllusSpeed100({ className, style }: IllusProps) {
  return <span className={className} style={style}>{SignScene({
    panelContent: <SpeedPanel speed="100"/>, ariaLabel: 'Limitation de vitesse 100 km/h — chaussées séparées', skyId: 'sp100',
    skyC1: '#5aa8d0', skyC2: '#aed4ea',
  })}</span>;
}

// ─────────────────────────────────────────────────────────────────────────
// SENS INTERDIT
// ─────────────────────────────────────────────────────────────────────────
export function IllusNoEntry({ className, style }: IllusProps) {
  return <span className={className} style={style}>{SignScene({
    ariaLabel: 'Panneau sens interdit — accès totalement interdit',
    skyId: 'sni',
    panelContent: <>
      <circle cx="640" cy="220" r="64" fill="#C0392B" stroke="white" strokeWidth="7"/>
      <rect x="600" y="208" width="80" height="24" rx="4" fill="white"/>
    </>,
  })}</span>;
}

// ─────────────────────────────────────────────────────────────────────────
// ROUTE PRIORITAIRE (losange jaune)
// ─────────────────────────────────────────────────────────────────────────
export function IllusPriority({ className, style }: IllusProps) {
  return <span className={className} style={style}>{SignScene({
    ariaLabel: 'Panneau route prioritaire — losange jaune',
    skyId: 'spr',
    panelContent: <>
      <rect x="600" y="178" width="80" height="80" fill="#F5C518" stroke="#0A2540" strokeWidth="5" transform="rotate(45 640 218)"/>
      <rect x="612" y="190" width="56" height="56" fill="white" transform="rotate(45 640 218)"/>
    </>,
  })}</span>;
}

// ─────────────────────────────────────────────────────────────────────────
// DÉPASSEMENT INTERDIT (deux voitures rouge/noir barrées)
// ─────────────────────────────────────────────────────────────────────────
export function IllusNoOvertaking({ className, style }: IllusProps) {
  return <span className={className} style={style}>{SignScene({
    ariaLabel: 'Panneau dépassement interdit',
    skyId: 'sno',
    panelContent: <>
      <circle cx="640" cy="220" r="64" fill="white" stroke="#C0392B" strokeWidth="9"/>
      <circle cx="620" cy="220" r="17" fill="#C0392B"/>
      <circle cx="660" cy="220" r="17" fill="#333"/>
      <line x1="600" y1="180" x2="680" y2="260" stroke="#C0392B" strokeWidth="9"/>
    </>,
  })}</span>;
}

// ─────────────────────────────────────────────────────────────────────────
// PASSAGE PIÉTON (triangle blanc, silhouette piéton)
// ─────────────────────────────────────────────────────────────────────────
export function IllusPedestrianCrossing({ className, style }: IllusProps) {
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Panneau passage piéton — zone de traversée">
      <defs>
        <linearGradient id="i-sped" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#7cbcdc"/><stop offset="100%" stopColor="#c0e0ee"/>
        </linearGradient>
      </defs>
      <rect width="800" height="420" fill="url(#i-sped)"/>
      <SignClouds y={68}/>
      <SignGrass/>
      <rect x="0" y="215" width="800" height="5" fill="#3d6b25" opacity=".6"/>
      <SignRoad/>
      {/* Bandes zébrées passage piéton au sol */}
      {[300,332,364,396,428,460].map(x => (
        <polygon key={x} points={`${x},300 ${x+18},300 ${x+12},340 ${x-6},340`} fill="white" opacity=".88"/>
      ))}
      <SignTrees/>
      <SignBuilding/>
      <SignPole/>
      {/* Panneau triangulaire piéton */}
      <polygon points="640,150 690,250 590,250" fill="white" stroke="#C0392B" strokeWidth="7"/>
      <circle cx="640" cy="190" r="9" fill="#0A2540"/>
      <path d="M640 202 L632 228 L622 244 M632 228 L648 244 M615 214 L665 214"
        stroke="#0A2540" strokeWidth="5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
      <SignDashboard/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// ZONE SCOLAIRE
// ─────────────────────────────────────────────────────────────────────────
export function IllusSchoolZone({ className, style }: IllusProps) {
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Panneau zone scolaire — ralentir, enfants">
      <defs>
        <linearGradient id="i-schz" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#8ac4e0"/><stop offset="100%" stopColor="#cce8f2"/>
        </linearGradient>
      </defs>
      <rect width="800" height="420" fill="url(#i-schz)"/>
      <SignClouds y={70}/>
      <SignGrass/>
      <rect x="0" y="215" width="800" height="5" fill="#3d6b25" opacity=".6"/>
      <SignRoad/>
      <SignTrees/>
      {/* École en fond */}
      <rect x="20" y="155" width="92" height="62" fill="#d9b58c"/>
      <rect x="24" y="159" width="84" height="54" fill="#e8caa4"/>
      <polygon points="20,155 66,128 112,155" fill="#8b4a2e"/>
      <rect x="48" y="186" width="20" height="28" fill="#5a3a1e"/>
      <rect x="76" y="172" width="14" height="14" fill="#7a9db5"/>
      <SignPole/>
      <polygon points="640,150 690,250 590,250" fill="#F5C518" stroke="#0A2540" strokeWidth="5"/>
      {/* Silhouettes enfants */}
      <circle cx="622" cy="208" r="7" fill="#0A2540"/>
      <rect x="615" y="217" width="14" height="20" rx="2" fill="#0A2540"/>
      <circle cx="652" cy="216" r="6" fill="#0A2540"/>
      <rect x="646" y="223" width="12" height="16" rx="2" fill="#0A2540"/>
      <SignDashboard/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// PANNEAU DANGER (triangle point d'exclamation)
// ─────────────────────────────────────────────────────────────────────────
export function IllusDanger({ className, style }: IllusProps) {
  return <span className={className} style={style}>{SignScene({
    ariaLabel: 'Panneau danger — prudence',
    skyId: 'sdg',
    panelContent: <>
      <polygon points="640,150 695,255 585,255" fill="white" stroke="#C0392B" strokeWidth="8"/>
      <text x="640" y="238" textAnchor="middle" fill="#C0392B" fontSize="64" fontWeight="bold" fontFamily="Arial Black">!</text>
    </>,
  })}</span>;
}

// ─────────────────────────────────────────────────────────────────────────
// STATIONNEMENT (P bleu)
// ─────────────────────────────────────────────────────────────────────────
export function IllusParking({ className, style }: IllusProps) {
  return <span className={className} style={style}>{SignScene({
    ariaLabel: 'Panneau stationnement autorisé',
    skyId: 'spk',
    panelContent: <>
      <rect x="596" y="174" width="88" height="88" rx="12" fill="#1A6FC4"/>
      <text x="640" y="240" textAnchor="middle" fill="white" fontSize="58" fontWeight="bold" fontFamily="Arial Black">P</text>
    </>,
  })}</span>;
}

// ─────────────────────────────────────────────────────────────────────────
// FIN DE LIMITATION (bandes diagonales grises)
// ─────────────────────────────────────────────────────────────────────────
export function IllusEndRestriction({ className, style }: IllusProps) {
  return <span className={className} style={style}>{SignScene({
    ariaLabel: 'Fin de limitation de vitesse',
    skyId: 'send',
    panelContent: <>
      <circle cx="640" cy="220" r="64" fill="white" stroke="#888" strokeWidth="6"/>
      {Array.from({ length: 6 }, (_, i) => (
        <line key={i} x1={604 + i * 13} y1="252" x2={616 + i * 13} y2="188" stroke="#888" strokeWidth="4"/>
      ))}
    </>,
  })}</span>;
}

// ─────────────────────────────────────────────────────────────────────────
// DIRECTION OBLIGATOIRE (flèche bleue)
// ─────────────────────────────────────────────────────────────────────────
export function IllusMandatory({ className, style }: IllusProps) {
  return <span className={className} style={style}>{SignScene({
    ariaLabel: 'Panneau direction obligatoire à droite',
    skyId: 'smd',
    panelContent: <>
      <circle cx="640" cy="220" r="64" fill="#1A6FC4" stroke="white" strokeWidth="6"/>
      <path d="M604 220 L668 220 M650 200 L674 220 L650 240" stroke="white" strokeWidth="11"
        fill="none" strokeLinecap="round" strokeLinejoin="round"/>
    </>,
  })}</span>;
}

// ── Export map dédié, à fusionner dans ILLUSTRATION_MAP ────────────────────
export const SIGN_ILLUSTRATION_MAP: Record<string, React.ComponentType<IllusProps>> = {
  'speed_30':           IllusSpeed30,
  'speed_90':           IllusSpeed90,
  'speed_100':          IllusSpeed100,
  'no_entry':           IllusNoEntry,
  'priority':           IllusPriority,
  'no_overtaking':      IllusNoOvertaking,
  'pedestrian_crossing':IllusPedestrianCrossing,
  'school_zone':        IllusSchoolZone,
  'danger':             IllusDanger,
  'parking':            IllusParking,
  'end_restriction':    IllusEndRestriction,
  'mandatory':          IllusMandatory,
  'mandatory_straight': IllusMandatory,
};
