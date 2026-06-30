import React from 'react';
import { SIGN_ILLUSTRATION_MAP } from './illustrations_signs';
/**
 * CodeRoute Guinée — Illustrations style Ornikar
 * Vue first-person conducteur : route en perspective, ciel, végétation,
 * bâtiments, panneaux sur poteaux, tableau de bord en bas.
 * Chaque composant = SVG autonome 800×420px, responsive via viewBox.
 */

interface IllusProps { className?: string; style?: React.CSSProperties; }

// ── SKY + CLOUDS réutilisables ─────────────────────────────────────────────
const Clouds = ({ y = 70 }: { y?: number }) => <>
  <ellipse cx="160" cy={y}    rx="75" ry="28" fill="rgba(255,255,255,.87)"/>
  <ellipse cx="218" cy={y-12} rx="56" ry="22" fill="white"/>
  <ellipse cx="600" cy={y+8}  rx="82" ry="30" fill="rgba(255,255,255,.82)"/>
  <ellipse cx="658" cy={y-4}  rx="62" ry="24" fill="rgba(255,255,255,.88)"/>
</>;

const Trees = () => <>
  <rect x="42"  y="158" width="12" height="62" fill="#5d4037"/>
  <ellipse cx="48"  cy="150" rx="30" ry="34" fill="#2d6a1a"/>
  <rect x="108" y="167" width="10" height="53" fill="#5d4037"/>
  <ellipse cx="113" cy="161" rx="23" ry="27" fill="#3a7a22"/>
  <rect x="660" y="160" width="12" height="60" fill="#5d4037"/>
  <ellipse cx="666" cy="153" rx="28" ry="32" fill="#2d6a1a"/>
  <rect x="718" y="168" width="10" height="52" fill="#5d4037"/>
  <ellipse cx="723" cy="162" rx="22" ry="26" fill="#3a7a22"/>
</>;

const Dashboard = ({ dark = false }) => <>
  <rect x="0" y="370" width="800" height="50" fill={dark ? '#0a0f18' : '#1a1a1a'}/>
  <ellipse cx="400" cy="370" rx="420" ry="30" fill={dark ? '#0d1422' : '#222'}/>
  <circle cx="400" cy="398" r="35" fill="none" stroke={dark ? '#2a2a3a' : '#444'} strokeWidth="10"/>
  <line x1="400" y1="363" x2="400" y2="433" stroke={dark ? '#333' : '#555'} strokeWidth="5"/>
  <line x1="365" y1="398" x2="435" y2="398" stroke={dark ? '#333' : '#555'} strokeWidth="5"/>
  <circle cx="400" cy="398" r="8" fill={dark ? '#222' : '#333'}/>
</>;

const Road = () => <>
  {/* Chaussée */}
  <polygon points="258,218 542,218 800,420 0,420" fill="#3d3d3d"/>
  {/* Ligne centrale pointillée */}
  <polygon points="390,220 410,220 406,268 394,268" fill="#f1c40f" opacity=".88"/>
  <polygon points="395,286 405,286 403,322 397,322" fill="#f1c40f" opacity=".7"/>
  <polygon points="396,338 404,338 404,368 396,368" fill="#f1c40f" opacity=".52"/>
  {/* Bandes latérales blanches */}
  <polygon points="258,218 282,218 0,398 0,376" fill="white" opacity=".6"/>
  <polygon points="542,218 518,218 800,398 800,376" fill="white" opacity=".6"/>
</>;

const Grass = () => <>
  <polygon points="0,218 258,218 0,420"   fill="#4a8a2e"/>
  <polygon points="800,218 542,218 800,420" fill="#4a8a2e"/>
</>;

// ── Poteau avec panneau ────────────────────────────────────────────────────
const Pole = ({ x, yTop, h = 135 }: { x: number; yTop: number; h?: number }) =>
  <rect x={x} y={yTop} width="7" height={h} fill="#8a8a8a" rx="2"/>;

// ─────────────────────────────────────────────────────────────────────────
// 1. STOP — approche d'un carrefour
// ─────────────────────────────────────────────────────────────────────────
export function IllusStop({ className, style }: IllusProps) {
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" className={className} style={style}>
      <defs>
        <linearGradient id="i-sky1" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#82C4E8"/>
          <stop offset="100%" stopColor="#C4E4F4"/>
        </linearGradient>
      </defs>
      <rect width="800" height="420" fill="url(#i-sky1)"/>
      <Clouds y={72}/>
      <Grass/>
      {/* Fond herbe + lisière */}
      <rect x="0" y="215" width="800" height="5" fill="#3d6b25" opacity=".6"/>
      <Road/>
      <Trees/>
      {/* Bâtiment gauche fond */}
      <rect x="22" y="170" width="58" height="48" fill="#c0b0a0"/>
      <rect x="24" y="172" width="54" height="44" fill="#d4c4b4"/>
      <rect x="30" y="178" width="14" height="18" fill="#7a9db5"/>
      <rect x="50" y="178" width="14" height="18" fill="#7a9db5"/>
      <rect x="32" y="196" width="18" height="22" fill="#8b6914"/>
      {/* Ligne d'arrêt au sol */}
      <rect x="306" y="332" width="188" height="8" fill="white" opacity=".9" rx="2"/>
      {/* Poteau + panneau STOP */}
      <Pole x={574} yTop={196}/>
      <polygon points="614,168 648,184 658,218 642,248 606,248 590,218 600,184"
        fill="#C0392B" stroke="white" strokeWidth="5"/>
      <polygon points="614,177 645,191 653,219 639,245 609,245 595,219 603,191"
        fill="none" stroke="rgba(255,255,255,.25)" strokeWidth="2"/>
      <text x="624" y="218" textAnchor="middle" fill="white" fontSize="19"
        fontWeight="bold" fontFamily="Arial Black,sans-serif">STOP</text>
      <Dashboard/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// 2. CÉDEZ LE PASSAGE — vue conducteur carrefour
// ─────────────────────────────────────────────────────────────────────────
export function IllusGiveWay({ className, style }: IllusProps) {
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" className={className} style={style}>
      <defs>
        <linearGradient id="i-sky2" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#6ab4d8"/>
          <stop offset="100%" stopColor="#b8dcee"/>
        </linearGradient>
      </defs>
      <rect width="800" height="420" fill="url(#i-sky2)"/>
      <Clouds y={68}/>
      {/* Route principale traversante */}
      <rect x="0" y="218" width="800" height="202" fill="#444"/>
      {/* Herbe îlots */}
      <polygon points="0,218 258,218 0,310" fill="#4a8a2e"/>
      <polygon points="800,218 542,218 800,310" fill="#4a8a2e"/>
      {/* Route vers nous */}
      <polygon points="258,218 542,218 800,420 0,420" fill="#3d3d3d"/>
      {/* Marquages route principale */}
      <line x1="0"   y1="280" x2="248" y2="280" stroke="#f1c40f" strokeWidth="3" strokeDasharray="22,14" opacity=".8"/>
      <line x1="552" y1="280" x2="800" y2="280" stroke="#f1c40f" strokeWidth="3" strokeDasharray="22,14" opacity=".8"/>
      <line x1="0"   y1="222" x2="800" y2="222" stroke="white" strokeWidth="2.5" opacity=".55"/>
      <line x1="0"   y1="416" x2="800" y2="416" stroke="white" strokeWidth="2.5" opacity=".55"/>
      {/* Ligne centrale route secondaire */}
      <polygon points="391,220 409,220 405,268 395,268" fill="#f1c40f" opacity=".82"/>
      {/* Triangles cédez au sol */}
      {[320,358,396,434,472].map(x => (
        <polygon key={x} points={`${x},310 ${x+10},326 ${x-10},326`} fill="white" opacity=".85"/>
      ))}
      <rect x="298" y="304" width="204" height="6" fill="white" opacity=".85"/>
      {/* Voiture gauche route principale */}
      <rect x="55"  y="248" width="96" height="44" rx="8" fill="#e74c3c"/>
      <rect x="63"  y="252" width="32" height="26" rx="3" fill="rgba(200,230,255,.65)"/>
      <rect x="99"  y="252" width="32" height="26" rx="3" fill="rgba(200,230,255,.65)"/>
      <circle cx="69"  cy="292" r="10" fill="#111"/><circle cx="69"  cy="292" r="5" fill="#555"/>
      <circle cx="141" cy="292" r="10" fill="#111"/><circle cx="141" cy="292" r="5" fill="#555"/>
      {/* Voiture droite route principale */}
      <rect x="649" y="248" width="96" height="44" rx="8" fill="#27ae60"/>
      <rect x="657" y="252" width="32" height="26" rx="3" fill="rgba(200,230,255,.65)"/>
      <rect x="693" y="252" width="32" height="26" rx="3" fill="rgba(200,230,255,.65)"/>
      <circle cx="663" cy="292" r="10" fill="#111"/><circle cx="663" cy="292" r="5" fill="#555"/>
      <circle cx="735" cy="292" r="10" fill="#111"/><circle cx="735" cy="292" r="5" fill="#555"/>
      <Trees/>
      {/* Panneau cédez */}
      <Pole x={523} yTop={195}/>
      <polygon points="552,162 596,238 508,238" fill="white" stroke="#C0392B" strokeWidth="9"/>
      <polygon points="552,176 586,232 518,232" fill="white" stroke="#C0392B" strokeWidth="4.5"/>
      <Dashboard/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// 3. LIMITATION 50 — entrée agglomération
// ─────────────────────────────────────────────────────────────────────────
export function IllusSpeed50({ className, style, speed = '50' }: IllusProps & { speed?: string }) {
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" className={className} style={style}>
      <defs>
        <linearGradient id="i-sky3" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#91C8E4"/>
          <stop offset="100%" stopColor="#cce8f5"/>
        </linearGradient>
      </defs>
      <rect width="800" height="420" fill="url(#i-sky3)"/>
      <Clouds y={66}/>
      {/* Bâtiments fond — ambiance agglomération */}
      <rect x="0"   y="142" width="76"  height="78" fill="#b8a898"/>
      <rect x="2"   y="144" width="72"  height="74" fill="#cebea8"/>
      <rect x="8"   y="152" width="16"  height="20" fill="#7a9db5"/>
      <rect x="28"  y="152" width="16"  height="20" fill="#7a9db5"/>
      <rect x="48"  y="152" width="16"  height="20" fill="#7a9db5"/>
      <rect x="10"  y="174" width="20"  height="46" fill="#8b6914"/>
      <rect x="82"  y="155" width="68"  height="65" fill="#a09888"/>
      <rect x="84"  y="157" width="64"  height="61" fill="#b4a898"/>
      <rect x="88"  y="162" width="14"  height="18" fill="#7a9db5"/>
      <rect x="106" y="162" width="14"  height="18" fill="#7a9db5"/>
      <rect x="124" y="162" width="14"  height="18" fill="#7a9db5"/>
      <rect x="638" y="148" width="72"  height="72" fill="#c0b0a0"/>
      <rect x="640" y="150" width="68"  height="68" fill="#d0c0b0"/>
      <rect x="644" y="158" width="16"  height="18" fill="#7a9db5"/>
      <rect x="664" y="158" width="16"  height="18" fill="#7a9db5"/>
      <rect x="684" y="158" width="16"  height="18" fill="#7a9db5"/>
      <rect x="644" y="180" width="22"  height="38" fill="#8b6914"/>
      <rect x="716" y="154" width="84"  height="66" fill="#b0a090"/>
      {/* Trottoirs */}
      <polygon points="242,218 288,218 0,370 0,344" fill="#c8c0b0"/>
      <polygon points="558,218 512,218 800,370 800,344" fill="#c8c0b0"/>
      <Grass/>
      <Road/>
      {/* Lampadaires */}
      <rect x="246" y="172" width="6" height="48" fill="#888"/>
      <path d="M249,172 Q260,164 272,166" fill="none" stroke="#888" strokeWidth="5"/>
      <ellipse cx="273" cy="166" rx="7" ry="4" fill="#fffde0" opacity=".9"/>
      <rect x="552" y="172" width="6" height="48" fill="#888"/>
      <path d="M555,172 Q544,164 532,166" fill="none" stroke="#888" strokeWidth="5"/>
      <ellipse cx="531" cy="166" rx="7" ry="4" fill="#fffde0" opacity=".9"/>
      {/* Panneau 50 + plaque agglomération */}
      <Pole x={543} yTop={186}/>
      <circle cx="570" cy="164" r="36" fill="white" stroke="#C0392B" strokeWidth="10"/>
      <circle cx="570" cy="164" r="25" fill="white" stroke="#eee" strokeWidth="1"/>
      <text x="570" y="174" textAnchor="middle" fill="#111" fontSize={speed.length > 2 ? 20 : 26}
        fontWeight="bold" fontFamily="Arial Black,sans-serif">{speed}</text>
      <rect x="544" y="204" width="54" height="22" rx="3" fill="#1a2a5a" stroke="white" strokeWidth="1.5"/>
      <text x="571" y="219" textAnchor="middle" fill="white" fontSize="9" fontWeight="bold">CONAKRY</text>
      <Dashboard/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// 4. FEU ROUGE — arrêt obligatoire
// ─────────────────────────────────────────────────────────────────────────
export function IllusTrafficLightRed({ className, style }: IllusProps) {
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" className={className} style={style}>
      <defs>
        <linearGradient id="i-sky4" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#7ab8d0"/>
          <stop offset="100%" stopColor="#b0d8e8"/>
        </linearGradient>
        <filter id="i-gr"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <rect width="800" height="420" fill="url(#i-sky4)"/>
      <Clouds y={70}/>
      {/* Herbe + routes */}
      <rect x="0" y="218" width="800" height="202" fill="#444"/>
      <polygon points="0,218 258,218 0,420" fill="#4a8a2e"/>
      <polygon points="800,218 542,218 800,420" fill="#4a8a2e"/>
      <polygon points="258,218 542,218 800,420 0,420" fill="#3d3d3d"/>
      {/* Passage piéton */}
      {[296,330,364,398,432,466].map(x => (
        <rect key={x} x={x} y={296} width="28" height="52" fill="white" opacity=".88"/>
      ))}
      <rect x="295" y="288" width="208" height="7" fill="white" opacity=".92"/>
      {/* Ligne centrale */}
      <polygon points="392,220 408,220 404,278 396,278" fill="#f1c40f" opacity=".82"/>
      {/* Voiture en attente face à nous */}
      <rect x="330" y="242" width="140" height="50" rx="8" fill="#4a4a4a" opacity=".88"/>
      <rect x="340" y="246" width="46" height="30" rx="3" fill="#7ab8d4" opacity=".75"/>
      <rect x="394" y="246" width="46" height="30" rx="3" fill="#7ab8d4" opacity=".75"/>
      <circle cx="350" cy="293" r="12" fill="#111"/><circle cx="350" cy="293" r="6" fill="#444"/>
      <circle cx="450" cy="293" r="12" fill="#111"/><circle cx="450" cy="293" r="6" fill="#444"/>
      {/* Feux tricolores gauche */}
      <rect x="258" y="116" width="34" height="106" rx="8" fill="#111"/>
      <circle cx="275" cy="137" r="14" fill="#FF2D00" filter="url(#i-gr)"/>
      <circle cx="275" cy="137" r="7"  fill="rgba(255,160,120,.35)"/>
      <circle cx="275" cy="169" r="14" fill="#2a1800"/>
      <circle cx="275" cy="200" r="14" fill="#001800"/>
      <rect x="272" y="222" width="6" height="96" fill="#888"/>
      {/* Feux tricolores droite */}
      <rect x="508" y="116" width="34" height="106" rx="8" fill="#111"/>
      <circle cx="525" cy="137" r="14" fill="#FF2D00" filter="url(#i-gr)"/>
      <circle cx="525" cy="137" r="7"  fill="rgba(255,160,120,.35)"/>
      <circle cx="525" cy="169" r="14" fill="#2a1800"/>
      <circle cx="525" cy="200" r="14" fill="#001800"/>
      <rect x="522" y="222" width="6" height="96" fill="#888"/>
      <Trees/>
      <Dashboard/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// 5. FEU ORANGE — transition vers rouge
// ─────────────────────────────────────────────────────────────────────────
export function IllusTrafficLightOrange({ className, style }: IllusProps) {
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" className={className} style={style}>
      <defs>
        <linearGradient id="i-sky4o" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#7ab8d0"/>
          <stop offset="100%" stopColor="#b0d8e8"/>
        </linearGradient>
        <filter id="i-go"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <rect width="800" height="420" fill="url(#i-sky4o)"/>
      <Clouds y={70}/>
      <rect x="0" y="218" width="800" height="202" fill="#444"/>
      <polygon points="0,218 258,218 0,420" fill="#4a8a2e"/>
      <polygon points="800,218 542,218 800,420" fill="#4a8a2e"/>
      <polygon points="258,218 542,218 800,420 0,420" fill="#3d3d3d"/>
      {[296,330,364,398,432,466].map(x => (
        <rect key={x} x={x} y={296} width="28" height="52" fill="white" opacity=".88"/>
      ))}
      <rect x="295" y="288" width="208" height="7" fill="white" opacity=".92"/>
      <polygon points="392,220 408,220 404,278 396,278" fill="#f1c40f" opacity=".82"/>
      {/* Feux tricolores — orange allumé */}
      <rect x="258" y="116" width="34" height="106" rx="8" fill="#111"/>
      <circle cx="275" cy="137" r="14" fill="#2a0a00"/>
      <circle cx="275" cy="169" r="14" fill="#FF8C00" filter="url(#i-go)"/>
      <circle cx="275" cy="169" r="7"  fill="rgba(255,200,80,.4)"/>
      <circle cx="275" cy="200" r="14" fill="#001800"/>
      <rect x="272" y="222" width="6" height="96" fill="#888"/>
      <rect x="508" y="116" width="34" height="106" rx="8" fill="#111"/>
      <circle cx="525" cy="137" r="14" fill="#2a0a00"/>
      <circle cx="525" cy="169" r="14" fill="#FF8C00" filter="url(#i-go)"/>
      <circle cx="525" cy="169" r="7"  fill="rgba(255,200,80,.4)"/>
      <circle cx="525" cy="200" r="14" fill="#001800"/>
      <rect x="522" y="222" width="6" height="96" fill="#888"/>
      <Trees/>
      <Dashboard/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// 6. FEU ROUGE + ORANGE — préannonce du vert
// ─────────────────────────────────────────────────────────────────────────
export function IllusTrafficLightRedOrange({ className, style }: IllusProps) {
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" className={className} style={style}>
      <defs>
        <linearGradient id="i-sky4ro" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#7ab8d0"/>
          <stop offset="100%" stopColor="#b0d8e8"/>
        </linearGradient>
        <filter id="i-gro"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <rect width="800" height="420" fill="url(#i-sky4ro)"/>
      <Clouds y={70}/>
      <rect x="0" y="218" width="800" height="202" fill="#444"/>
      <polygon points="0,218 258,218 0,420" fill="#4a8a2e"/>
      <polygon points="800,218 542,218 800,420" fill="#4a8a2e"/>
      <polygon points="258,218 542,218 800,420 0,420" fill="#3d3d3d"/>
      {[296,330,364,398,432,466].map(x => (
        <rect key={x} x={x} y={296} width="28" height="52" fill="white" opacity=".88"/>
      ))}
      <rect x="295" y="288" width="208" height="7" fill="white" opacity=".92"/>
      <polygon points="392,220 408,220 404,278 396,278" fill="#f1c40f" opacity=".82"/>
      {/* Rouge + orange allumés */}
      <rect x="258" y="116" width="34" height="106" rx="8" fill="#111"/>
      <circle cx="275" cy="137" r="14" fill="#FF2D00" filter="url(#i-gro)"/>
      <circle cx="275" cy="137" r="7"  fill="rgba(255,160,120,.35)"/>
      <circle cx="275" cy="169" r="14" fill="#FF8C00" filter="url(#i-gro)"/>
      <circle cx="275" cy="169" r="7"  fill="rgba(255,200,80,.35)"/>
      <circle cx="275" cy="200" r="14" fill="#001800"/>
      <rect x="272" y="222" width="6" height="96" fill="#888"/>
      <rect x="508" y="116" width="34" height="106" rx="8" fill="#111"/>
      <circle cx="525" cy="137" r="14" fill="#FF2D00" filter="url(#i-gro)"/>
      <circle cx="525" cy="137" r="7"  fill="rgba(255,160,120,.35)"/>
      <circle cx="525" cy="169" r="14" fill="#FF8C00" filter="url(#i-gro)"/>
      <circle cx="525" cy="169" r="7"  fill="rgba(255,200,80,.35)"/>
      <circle cx="525" cy="200" r="14" fill="#001800"/>
      <rect x="522" y="222" width="6" height="96" fill="#888"/>
      <Trees/>
      <Dashboard/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// 7. PRIORITÉ À DROITE — vue semi-aérienne intersection
// ─────────────────────────────────────────────────────────────────────────
export function IllusPriorityRight({ className, style }: IllusProps) {
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" className={className} style={style}>
      <defs>
        <linearGradient id="i-sky5" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#85C1E9"/>
          <stop offset="100%" stopColor="#AED6F1"/>
        </linearGradient>
      </defs>
      <rect width="800" height="420" fill="url(#i-sky5)"/>
      <Clouds y={68}/>
      {/* Herbe de base */}
      <rect x="0" y="200" width="800" height="220" fill="#4a8a2e"/>
      {/* Route principale horizontale */}
      <rect x="0" y="238" width="800" height="76" fill="#4a4a4a"/>
      <line x1="0"   y1="276" x2="292" y2="276" stroke="#f1c40f" strokeWidth="3" strokeDasharray="22,14" opacity=".82"/>
      <line x1="508" y1="276" x2="800" y2="276" stroke="#f1c40f" strokeWidth="3" strokeDasharray="22,14" opacity=".82"/>
      <line x1="0"   y1="242" x2="800" y2="242" stroke="white" strokeWidth="2.5" opacity=".55"/>
      <line x1="0"   y1="310" x2="800" y2="310" stroke="white" strokeWidth="2.5" opacity=".55"/>
      {/* Route secondaire vers nous */}
      <rect x="328" y="200" width="144" height="120" fill="#4a4a4a"/>
      <line x1="400" y1="200" x2="400" y2="238" stroke="#f1c40f" strokeWidth="3" strokeDasharray="14,10" opacity=".82"/>
      <line x1="332" y1="200" x2="332" y2="238" stroke="white" strokeWidth="2.5" opacity=".55"/>
      <line x1="468" y1="200" x2="468" y2="238" stroke="white" strokeWidth="2.5" opacity=".55"/>
      {/* Zones herbe coins */}
      <rect x="0"   y="200" width="328" height="40" fill="#4a8a2e"/>
      <rect x="472" y="200" width="328" height="40" fill="#4a8a2e"/>
      {/* Voiture A — venant de gauche, bleu */}
      <rect x="82" y="248" width="114" height="50" rx="9" fill="#2980b9"/>
      <rect x="90" y="252" width="40" height="30" rx="3" fill="#85c1e9" opacity=".8"/>
      <rect x="134" y="252" width="40" height="30" rx="3" fill="#85c1e9" opacity=".8"/>
      <circle cx="96"  cy="299" r="12" fill="#111"/><circle cx="96"  cy="299" r="6" fill="#555"/>
      <circle cx="186" cy="299" r="12" fill="#111"/><circle cx="186" cy="299" r="6" fill="#555"/>
      {/* Badge A */}
      <circle cx="139" cy="266" r="14" fill="#1a6099" opacity=".92"/>
      <text x="139" y="271" textAnchor="middle" fill="white" fontSize="15" fontWeight="bold">A</text>
      {/* Flèche A */}
      <path d="M198 266 L226 266 M217 259 L226 266 L217 273"
        fill="none" stroke="#f1c40f" strokeWidth="3.5" strokeLinecap="round"/>
      {/* Voiture B — vient du bas (route secondaire), rouge */}
      <rect x="336" y="203" width="62" height="108" rx="9" fill="#e74c3c"/>
      <rect x="340" y="208" width="28" height="38" rx="3" fill="#f1948a" opacity=".75"/>
      <rect x="372" y="208" width="22" height="38" rx="3" fill="#f1948a" opacity=".75"/>
      <circle cx="344" cy="308" r="12" fill="#111"/><circle cx="344" cy="308" r="6" fill="#555"/>
      <circle cx="394" cy="308" r="12" fill="#111"/><circle cx="394" cy="308" r="6" fill="#555"/>
      {/* Badge B */}
      <circle cx="369" cy="248" r="14" fill="#c0392b" opacity=".92"/>
      <text x="369" y="253" textAnchor="middle" fill="white" fontSize="15" fontWeight="bold">B</text>
      {/* Flèche B */}
      <path d="M369 205 L369 180 M362 188 L369 180 L376 188"
        fill="none" stroke="#f1c40f" strokeWidth="3.5" strokeLinecap="round"/>
      {/* Bulle info */}
      <rect x="490" y="228" width="210" height="62" rx="12" fill="rgba(0,0,0,.72)"/>
      <polygon points="490,260 473,268 490,274" fill="rgba(0,0,0,.72)"/>
      <text x="595" y="248" textAnchor="middle" fill="#f1c40f" fontSize="12" fontWeight="bold">SANS SIGNALISATION</text>
      <text x="595" y="266" textAnchor="middle" fill="white" fontSize="11.5">B arrive par la droite de A</text>
      <text x="595" y="282" textAnchor="middle" fill="#7dcea0" fontSize="11.5" fontWeight="bold">→ B est prioritaire</text>
      <Trees/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// 8. CONDUITE DE NUIT
// ─────────────────────────────────────────────────────────────────────────
export function IllusNightDriving({ className, style }: IllusProps) {
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" className={className} style={style}>
      <defs>
        <linearGradient id="i-night" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#080c1e"/>
          <stop offset="100%" stopColor="#16223a"/>
        </linearGradient>
        <radialGradient id="i-hl" cx="50%" cy="100%" r="85%">
          <stop offset="0%"   stopColor="rgba(255,248,190,.20)"/>
          <stop offset="55%"  stopColor="rgba(255,248,190,.05)"/>
          <stop offset="100%" stopColor="transparent"/>
        </radialGradient>
        <filter id="i-gs"><feGaussianBlur stdDeviation="2.5" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <rect width="800" height="420" fill="url(#i-night)"/>
      {/* Étoiles */}
      {[[70,32],[148,18],[234,44],[318,16],[426,28],[518,12],[612,36],[696,20],[754,48],
        [38,58],[172,72],[560,52]].map(([x,y],i) => (
        <circle key={i} cx={x} cy={y} r={i%3===0?1.5:1} fill="white" opacity={.6+i*.03}/>
      ))}
      {/* Lune */}
      <circle cx="692" cy="54" r="24" fill="#e8ddb5" opacity=".92"/>
      <circle cx="703" cy="46" r="19" fill="#080c1e" opacity=".78"/>
      {/* Silhouettes arbres nocturnes */}
      <rect x="28"  y="172" width="14" height="68" fill="#060c14"/>
      <polygon points="35,138 8,218 62,218" fill="#0d1825"/>
      <rect x="96"  y="182" width="11" height="58" fill="#060c14"/>
      <polygon points="102,154 78,218 126,218" fill="#0d1825"/>
      <rect x="664" y="175" width="14" height="66" fill="#060c14"/>
      <polygon points="671,140 644,218 698,218" fill="#0d1825"/>
      <rect x="726" y="182" width="11" height="58" fill="#060c14"/>
      <polygon points="732,156 708,218 756,218" fill="#0d1825"/>
      {/* Herbe nocturne */}
      <polygon points="0,218 258,218 0,420"   fill="#0d1a08"/>
      <polygon points="800,218 542,218 800,420" fill="#0d1a08"/>
      {/* Route */}
      <polygon points="258,218 542,218 800,420 0,420" fill="#1e1e1e"/>
      {/* Cône de lumière phares */}
      <polygon points="340,370 460,370 562,218 238,218" fill="url(#i-hl)"/>
      {/* Lignes route */}
      <polygon points="392,220 408,220 404,264 396,264" fill="#f1c40f" opacity=".9"/>
      <polygon points="394,282 406,282 404,318 396,318" fill="#f1c40f" opacity=".72"/>
      <polygon points="395,334 405,334 404,362 396,362" fill="#f1c40f" opacity=".54"/>
      <polygon points="258,218 282,218 0,396 0,374" fill="white" opacity=".65"/>
      <polygon points="542,218 518,218 800,396 800,374" fill="white" opacity=".65"/>
      {/* Cataphotes */}
      <ellipse cx="400" cy="240" rx="4" ry="2" fill="#FFEAA0" opacity=".9"/>
      <ellipse cx="400" cy="272" rx="3" ry="1.5" fill="#FFEAA0" opacity=".72"/>
      <ellipse cx="400" cy="298" rx="3" ry="1.5" fill="#FFEAA0" opacity=".54"/>
      {/* Panneau 90 km/h éclairé */}
      <Pole x={529} yTop={186}/>
      <circle cx="556" cy="164" r="34" fill="white" stroke="#C0392B" strokeWidth="8" filter="url(#i-gs)"/>
      <circle cx="556" cy="164" r="23" fill="white" stroke="#eee" strokeWidth="1"/>
      <text x="556" y="173" textAnchor="middle" fill="#111" fontSize="21"
        fontWeight="bold" fontFamily="Arial Black,sans-serif">90</text>
      <Dashboard dark={true}/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// 9. PLUIE — conditions météo dégradées
// ─────────────────────────────────────────────────────────────────────────
export function IllusRainDriving({ className, style }: IllusProps) {
  // Pluie : tableau de coordonnées pré-calculé
  const drops = Array.from({length:62}, (_,i) => ({
    x: ((i * 13 + 5) % 820) - 10,
    y: ((i * 23 + 8) % 430) - 20,
  }));
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" className={className} style={style}>
      <defs>
        <linearGradient id="i-rain" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#485566"/>
          <stop offset="100%" stopColor="#6a7a8a"/>
        </linearGradient>
        <filter id="i-blur"><feGaussianBlur stdDeviation="1.8"/></filter>
      </defs>
      <rect width="800" height="420" fill="url(#i-rain)"/>
      {/* Nuages orageux */}
      <ellipse cx="200" cy="68" rx="165" ry="56" fill="#3a4a5a"/>
      <ellipse cx="345" cy="52" rx="148" ry="50" fill="#40505f"/>
      <ellipse cx="510" cy="72" rx="175" ry="60" fill="#374455"/>
      <ellipse cx="658" cy="60" rx="155" ry="54" fill="#3d4b5b"/>
      <ellipse cx="98"  cy="88" rx="125" ry="42" fill="#4a5867" opacity=".8"/>
      {/* Brume */}
      <rect x="0" y="110" width="800" height="250" fill="rgba(175,192,210,.07)"/>
      {/* Herbe */}
      <polygon points="0,220 258,220 0,420"   fill="#3a5a2a" opacity=".82"/>
      <polygon points="800,220 542,220 800,420" fill="#3a5a2a" opacity=".82"/>
      {/* Route */}
      <polygon points="258,220 542,220 800,420 0,420" fill="#353535"/>
      {/* Reflets humides */}
      <polygon points="342,278 458,278 524,370 276,370" fill="rgba(155,188,218,.11)"/>
      <polygon points="358,352 442,352 474,420 326,420" fill="rgba(155,188,218,.09)"/>
      {/* Ligne centrale */}
      <polygon points="390,222 410,222 406,270 394,270" fill="#f1c40f" opacity=".6"/>
      <polygon points="393,288 407,288 405,326 395,326" fill="#f1c40f" opacity=".46"/>
      {/* Bandes */}
      <polygon points="258,220 280,220 0,396 0,376" fill="white" opacity=".5"/>
      <polygon points="542,220 520,220 800,396 800,376" fill="white" opacity=".5"/>
      {/* Flaque */}
      <ellipse cx="356" cy="358" rx="84" ry="14" fill="rgba(136,178,208,.28)"/>
      <ellipse cx="478" cy="384" rx="64" ry="10" fill="rgba(136,178,208,.24)"/>
      {/* Voiture devant floue */}
      <rect x="328" y="244" width="144" height="52" rx="8" fill="#555" opacity=".68" filter="url(#i-blur)"/>
      <rect x="328" y="258" width="22" height="14" rx="3" fill="#ff2222" opacity=".8"/>
      <rect x="450" y="258" width="22" height="14" rx="3" fill="#ff2222" opacity=".8"/>
      {/* Pluie */}
      {drops.map((d,i) => (
        <line key={i} x1={d.x} y1={d.y} x2={d.x-5} y2={d.y+18}
          stroke="rgba(178,208,232,.52)" strokeWidth="1.2"/>
      ))}
      {/* Arbres */}
      <rect x="52"  y="165" width="12" height="56" fill="#2a3820" opacity=".62"/>
      <ellipse cx="58"  cy="158" rx="28" ry="32" fill="#2a3820" opacity=".62"/>
      <rect x="116" y="172" width="10" height="50" fill="#2a3820" opacity=".52"/>
      <ellipse cx="121" cy="166" rx="22" ry="26" fill="#2a3820" opacity=".52"/>
      <rect x="660" y="168" width="12" height="54" fill="#2a3820" opacity=".62"/>
      <ellipse cx="666" cy="162" rx="26" ry="30" fill="#2a3820" opacity=".62"/>
      {/* Panneau 80 */}
      <Pole x={526} yTop={190}/>
      <circle cx="552" cy="168" r="32" fill="white" stroke="#C0392B" strokeWidth="8" opacity=".92"/>
      <text x="552" y="177" textAnchor="middle" fill="#111" fontSize="22"
        fontWeight="bold" fontFamily="Arial Black,sans-serif">80</text>
      {/* Essuie-glaces */}
      <line x1="320" y1="370" x2="400" y2="348" stroke="rgba(255,255,255,.28)" strokeWidth="5" strokeLinecap="round"/>
      <line x1="480" y1="370" x2="400" y2="348" stroke="rgba(255,255,255,.28)" strokeWidth="5" strokeLinecap="round"/>
      <Dashboard/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// 10. AMBULANCE — véhicule prioritaire à croiser
// ─────────────────────────────────────────────────────────────────────────
export function IllusAmbulance({ className, style }: IllusProps) {
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" className={className} style={style}>
      <defs>
        <linearGradient id="i-sky8" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#7ab4cc"/>
          <stop offset="100%" stopColor="#b0d4e6"/>
        </linearGradient>
        <filter id="i-gl"><feGaussianBlur stdDeviation="6" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <rect width="800" height="420" fill="url(#i-sky8)"/>
      <Clouds y={70}/>
      <Grass/>
      <Road/>
      <Trees/>
      {/* AMBULANCE en sens inverse gauche */}
      {/* Carrosserie */}
      <rect x="76"  y="232" width="170" height="64" rx="7" fill="white"/>
      <rect x="76"  y="232" width="52"  height="48" rx="5" fill="#f0f0f0"/>
      {/* Pare-brise */}
      <rect x="78"  y="235" width="46"  height="30" rx="4" fill="#7ab8d4" opacity=".82"/>
      {/* Flanc */}
      <rect x="126" y="232" width="120" height="64" fill="white"/>
      {/* Bandes rouges */}
      <rect x="126" y="244" width="120" height="9" fill="#C0392B"/>
      <rect x="126" y="280" width="120" height="9" fill="#C0392B"/>
      {/* Croix rouge */}
      <rect x="196" y="247" width="30" height="30" rx="4" fill="#C0392B"/>
      <rect x="203" y="250" width="16" height="24" rx="1" fill="white"/>
      <rect x="197" y="256" width="28" height="12" rx="1" fill="white"/>
      {/* Gyrophares barre led */}
      <rect x="112" y="225" width="120" height="9" rx="3" fill="#0a0a0a"/>
      <ellipse cx="138" cy="225" rx="14" ry="5" fill="#0055ff" opacity=".88" filter="url(#i-gl)"/>
      <ellipse cx="172" cy="225" rx="12" ry="4" fill="#0044cc" opacity=".65"/>
      <ellipse cx="206" cy="225" rx="14" ry="5" fill="#ff4400" opacity=".88" filter="url(#i-gl)"/>
      <ellipse cx="232" cy="225" rx="12" ry="4" fill="#cc3300" opacity=".65"/>
      {/* Roues */}
      <circle cx="110" cy="297" r="16" fill="#111"/><circle cx="110" cy="297" r="7" fill="#444"/>
      <circle cx="232" cy="297" r="16" fill="#111"/><circle cx="232" cy="297" r="7" fill="#444"/>
      {/* Halo gyrophares sur route */}
      <ellipse cx="162" cy="342" rx="88" ry="12" fill="rgba(0,80,255,.07)"/>
      {/* Flèche déportez-vous */}
      <path d="M310,290 L408,290" stroke="#f1c40f" strokeWidth="5" fill="none"/>
      <path d="M395,280 L410,290 L395,300" fill="#f1c40f"/>
      <Dashboard/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// 11. DISTANCE DE SÉCURITÉ
// ─────────────────────────────────────────────────────────────────────────
export function IllusSafeDistance({ className, style }: IllusProps) {
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" className={className} style={style}>
      <defs>
        <linearGradient id="i-sky9" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#88C8E6"/>
          <stop offset="100%" stopColor="#C0E2F4"/>
        </linearGradient>
      </defs>
      <rect width="800" height="420" fill="url(#i-sky9)"/>
      <Clouds y={68}/>
      <Grass/>
      <Road/>
      <Trees/>
      {/* Voiture devant — rouge */}
      <rect x="314" y="234" width="172" height="56" rx="8" fill="#e74c3c"/>
      <rect x="324" y="238" width="60" height="36" rx="4" fill="#f1948a" opacity=".78"/>
      <rect x="392" y="238" width="60" height="36" rx="4" fill="#f1948a" opacity=".78"/>
      <circle cx="330" cy="291" r="13" fill="#111"/><circle cx="330" cy="291" r="6" fill="#444"/>
      <circle cx="476" cy="291" r="13" fill="#111"/><circle cx="476" cy="291" r="6" fill="#444"/>
      {/* Feux arrière rouges */}
      <rect x="312" y="248" width="22" height="14" rx="3" fill="#ff2222" opacity=".9"/>
      <rect x="466" y="248" width="22" height="14" rx="3" fill="#ff2222" opacity=".9"/>
      {/* Mesure distance */}
      <line x1="280" y1="340" x2="512" y2="340" stroke="#27ae60" strokeWidth="2.5"/>
      <line x1="280" y1="332" x2="280" y2="348" stroke="#27ae60" strokeWidth="2.5"/>
      <line x1="512" y1="332" x2="512" y2="348" stroke="#27ae60" strokeWidth="2.5"/>
      <rect x="312" y="326" width="176" height="28" rx="8" fill="rgba(39,174,96,.85)"/>
      <text x="400" y="345" textAnchor="middle" fill="white" fontSize="13" fontWeight="bold">≥ 2 secondes = 55 m à 100 km/h</text>
      <Dashboard/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// 12. GIRATOIRE — priorité aux véhicules engagés
// ─────────────────────────────────────────────────────────────────────────
export function IllusRoundabout({ className, style }: IllusProps) {
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" className={className} style={style}>
      <defs>
        <linearGradient id="i-sky10" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#8ECAE6"/>
          <stop offset="100%" stopColor="#B8DCF0"/>
        </linearGradient>
      </defs>
      <rect width="800" height="420" fill="url(#i-sky10)"/>
      <Clouds y={66}/>
      {/* Herbe large */}
      <rect x="0" y="200" width="800" height="220" fill="#4a8a2e"/>
      {/* Anneau du giratoire */}
      <circle cx="400" cy="310" r="180" fill="#4a4a4a"/>
      <circle cx="400" cy="310" r="80"  fill="#4a8a2e"/>
      <circle cx="400" cy="310" r="70"  fill="#4a8a2e"/>
      {/* Flèches de sens giratoire */}
      <path d="M380,244 Q350,250 340,276" fill="none" stroke="#f1c40f" strokeWidth="4" strokeLinecap="round"/>
      <polygon points="334,268 338,282 348,274" fill="#f1c40f"/>
      {/* Routes entrant/sortant */}
      <rect x="370" y="140" width="60" height="90"  fill="#4a4a4a"/>
      <rect x="370" y="380" width="60" height="40"  fill="#4a4a4a"/>
      <rect x="140" y="284" width="80" height="52"  fill="#4a4a4a"/>
      <rect x="580" y="284" width="80" height="52"  fill="#4a4a4a"/>
      {/* Lignes et marquages */}
      <line x1="374" y1="140" x2="374" y2="230" stroke="white" strokeWidth="2.5" opacity=".55"/>
      <line x1="426" y1="140" x2="426" y2="230" stroke="white" strokeWidth="2.5" opacity=".55"/>
      <line x1="400" y1="140" x2="400" y2="230" stroke="#f1c40f" strokeWidth="3" strokeDasharray="14,10" opacity=".8"/>
      {/* Voiture engagée dans le giratoire */}
      <rect x="440" y="236" width="90" height="40" rx="7" fill="#3498db"
        transform="rotate(-35,485,256)"/>
      <text x="485" y="230" textAnchor="middle" fill="white" fontSize="10" fontWeight="bold">PRIORITAIRE</text>
      {/* Voiture entrant */}
      <rect x="368" y="152" width="64" height="38" rx="7" fill="#e74c3c"/>
      <text x="400" y="148" textAnchor="middle" fill="#e74c3c" fontSize="10" fontWeight="bold">CÈDE LE PASSAGE</text>
      {/* Panneau giratoire */}
      <Pole x={546} yTop={200}/>
      <circle cx="572" cy="178" r="32" fill="#1A6FC4" stroke="white" strokeWidth="5"/>
      <circle cx="572" cy="178" r="20" fill="none" stroke="white" strokeWidth="4"/>
      <path d="M555,170 Q556,158 568,156" fill="none" stroke="white" strokeWidth="4" strokeLinecap="round"/>
      <polygon points="568,151 562,162 574,162" fill="white"/>
      {/* Arbres fond */}
      <rect x="44"  y="158" width="12" height="60" fill="#5d4037"/>
      <ellipse cx="50"  cy="151" rx="28" ry="32" fill="#2d6a1a"/>
      <rect x="720" y="160" width="12" height="58" fill="#5d4037"/>
      <ellipse cx="726" cy="153" rx="26" ry="30" fill="#3a7a22"/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// Registre — map media_url → composant
// ─────────────────────────────────────────────────────────────────────────
type IllusComponent = (props: IllusProps) => React.ReactElement;

export const ILLUSTRATION_MAP: Record<string, IllusComponent> = {
  // Panneaux — vitesse (prop speed pour réutiliser le même gabarit visuel)
  'stop':                    IllusStop,
  'give_way':                IllusGiveWay,
  'speed_50':                IllusSpeed50,
  'speed_70':                (p) => IllusSpeed50({ ...p, speed: '70' } as any),
  'roundabout':              IllusRoundabout,
  // Feux
  'traffic_light_red':       IllusTrafficLightRed,
  'traffic_light_orange':    IllusTrafficLightOrange,
  'traffic_light_red_orange':IllusTrafficLightRedOrange,
  // Scènes
  'intersection_priority_right': IllusPriorityRight,
  'intersection_roundabout':     IllusRoundabout,
  'night_driving':               IllusNightDriving,
  'rain_driving':                IllusRainDriving,
  'situation_safe_distance':     IllusSafeDistance,
  'situation_emergency_vehicle': IllusAmbulance,
  'alcohol_scene':               IllusAlcoholCheck,
  'first_aid':                   IllusFirstAid,
  // Panneaux complémentaires — illustrations_signs.tsx
  ...SIGN_ILLUSTRATION_MAP,
};

// ─────────────────────────────────────────────────────────────────────────
// CONTRÔLE ALCOOLÉMIE — agent + éthylotest, vue conducteur arrêté
// ─────────────────────────────────────────────────────────────────────────
export function IllusAlcoholCheck({ className, style }: IllusProps) {
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" className={className} style={style}
      role="img" aria-label="Contrôle d'alcoolémie par un agent — éthylotest">
      <defs>
        <linearGradient id="i-skyalc" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0a1428"/>
          <stop offset="55%" stopColor="#16243d"/>
          <stop offset="100%" stopColor="#242424"/>
        </linearGradient>
        <radialGradient id="i-gyro-b" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#0055ff" stopOpacity=".75"/>
          <stop offset="100%" stopColor="#0055ff" stopOpacity="0"/>
        </radialGradient>
        <radialGradient id="i-gyro-r" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#ff2200" stopOpacity=".75"/>
          <stop offset="100%" stopColor="#ff2200" stopOpacity="0"/>
        </radialGradient>
      </defs>
      <rect width="800" height="420" fill="url(#i-skyalc)"/>
      {/* Étoiles */}
      {[[70,30],[180,18],[300,40],[420,15],[540,32],[660,20],[740,42]].map(([x,y],i)=>(
        <circle key={i} cx={x} cy={y} r="1.4" fill="white" opacity={.5+i*0.05}/>
      ))}
      <Grass/>
      <Road/>
      <Trees/>
      {/* Gyrophares véhicule police gauche */}
      <rect x="40" y="248" width="120" height="50" rx="6" fill="#0d1d2e"/>
      <rect x="44" y="240" width="112" height="9" rx="3" fill="#0a0a0a"/>
      <ellipse cx="72" cy="240" rx="13" ry="5" fill="url(#i-gyro-b)"/>
      <ellipse cx="72" cy="240" rx="7" ry="3" fill="#3a7aff"/>
      <ellipse cx="128" cy="240" rx="13" ry="5" fill="url(#i-gyro-r)"/>
      <ellipse cx="128" cy="240" rx="7" ry="3" fill="#ff5533"/>
      <ellipse cx="100" cy="350" rx="100" ry="14" fill="rgba(0,90,255,.08)"/>
      <ellipse cx="100" cy="350" rx="60" ry="10" fill="rgba(255,40,0,.06)"/>
      {/* Agent silhouette */}
      <ellipse cx="430" cy="232" rx="16" ry="20" fill="#d8a878"/>
      <rect x="412" y="252" width="36" height="58" rx="6" fill="#0c3d22"/>
      <rect x="412" y="252" width="36" height="14" fill="#0a2e18"/>
      <rect x="402" y="262" width="14" height="38" rx="4" fill="#0c3d22"/>
      <rect x="446" y="262" width="14" height="38" rx="4" fill="#0c3d22"/>
      {/* Bras tenant éthylotest */}
      <rect x="450" y="268" width="32" height="9" rx="3" fill="#222" transform="rotate(-18 450 272)"/>
      <rect x="478" y="255" width="14" height="22" rx="3" fill="#e8e8e8" stroke="#999" strokeWidth="1"/>
      <rect x="481" y="258" width="8" height="8" fill="#0a8a4a"/>
      {/* Casquette */}
      <ellipse cx="430" cy="218" rx="17" ry="8" fill="#0a2e18"/>
      <rect x="418" y="206" width="24" height="14" rx="6" fill="#0a2e18"/>
      {/* Voiture arrêtée (vue conducteur) */}
      <rect x="312" y="252" width="168" height="58" fill="#2a2a2a" rx="7"/>
      <rect x="320" y="256" width="60" height="38" fill="#3a6070" rx="3" opacity=".84"/>
      <rect x="392" y="256" width="60" height="38" fill="#3a6070" rx="3" opacity=".84"/>
      <ellipse cx="336" cy="312" rx="17" ry="9" fill="#111"/>
      <ellipse cx="458" cy="312" rx="17" ry="9" fill="#111"/>
      {/* Panneau taux légal */}
      <rect x="600" y="190" width="160" height="92" rx="10" fill="rgba(255,255,255,.06)" stroke="#C0392B" strokeWidth="2"/>
      <text x="680" y="216" textAnchor="middle" fill="#f1c40f" fontSize="13" fontWeight="bold" fontFamily="Arial,sans-serif">TAUX LÉGAL</text>
      <text x="680" y="244" textAnchor="middle" fill="white" fontSize="20" fontWeight="bold" fontFamily="Arial Black,sans-serif">0,5 g/L</text>
      <text x="680" y="262" textAnchor="middle" fill="rgba(255,255,255,.55)" fontSize="10">Permis probatoire</text>
      <text x="680" y="276" textAnchor="middle" fill="#ff6b5b" fontSize="13" fontWeight="bold">0,2 g/L</text>
      <Dashboard dark/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// PREMIERS SECOURS — accident, triangle, croix rouge
// ─────────────────────────────────────────────────────────────────────────
export function IllusFirstAid({ className, style }: IllusProps) {
  return (
    <svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" className={className} style={style}
      role="img" aria-label="Accident de la route — premiers secours, triangle de signalisation">
      <defs>
        <linearGradient id="i-skyfa" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#6aa8cc"/>
          <stop offset="100%" stopColor="#aed4e8"/>
        </linearGradient>
      </defs>
      <rect width="800" height="420" fill="url(#i-skyfa)"/>
      <Clouds y={66}/>
      <Grass/>
      <Road/>
      <Trees/>
      {/* Véhicule accidenté légèrement de travers */}
      <g transform="rotate(-6 280 275)">
        <rect x="200" y="248" width="160" height="58" rx="7" fill="#C0392B"/>
        <rect x="208" y="252" width="56" height="36" fill="#8a2a2a" rx="3" opacity=".7"/>
        <rect x="276" y="252" width="56" height="36" fill="#8a2a2a" rx="3" opacity=".7"/>
        <ellipse cx="224" cy="306" rx="16" ry="9" fill="#111"/>
        <ellipse cx="340" cy="306" rx="16" ry="9" fill="#111"/>
      </g>
      {/* Triangle de signalisation au sol, en avant */}
      <polygon points="470,330 500,278 530,330" fill="#F5C518" stroke="#0A2540" strokeWidth="4"/>
      <polygon points="470,326 500,286 530,326" fill="none" stroke="#0A2540" strokeWidth="1.5" opacity=".4"/>
      {/* Personne au sol secourue (silhouette PLS schématique) */}
      <ellipse cx="395" cy="350" rx="46" ry="9" fill="rgba(0,0,0,.18)"/>
      <ellipse cx="368" cy="340" rx="9" ry="9" fill="#d8a878"/>
      <path d="M376,344 Q400,348 422,344 Q430,348 430,354 L370,356 Q364,350 376,344 Z" fill="#1A6FC4"/>
      {/* Secouriste agenouillé */}
      <ellipse cx="470" cy="300" rx="11" ry="13" fill="#d8a878"/>
      <path d="M462,312 Q470,340 486,348 L498,338 Q486,326 480,312 Z" fill="#C0392B"/>
      <rect x="478" y="330" width="12" height="22" rx="4" fill="#C0392B" transform="rotate(35 484 340)"/>
      {/* Trousse premiers secours */}
      <rect x="555" y="320" width="46" height="32" rx="4" fill="white" stroke="#C0392B" strokeWidth="2"/>
      <rect x="572" y="328" width="12" height="16" fill="#C0392B"/>
      <rect x="566" y="334" width="24" height="6" fill="#C0392B"/>
      {/* Panneau croix hôpital lointain */}
      <rect x="660" y="160" width="64" height="64" rx="8" fill="#C0392B"/>
      <rect x="678" y="174" width="28" height="12" fill="white"/>
      <rect x="686" y="166" width="12" height="28" fill="white"/>
      <text x="692" y="246" textAnchor="middle" fill="#0A2540" fontSize="10" fontWeight="bold">Hôpital — 5 km</text>
      <Dashboard/>
    </svg>
  );
}
