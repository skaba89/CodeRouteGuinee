import { ILLUSTRATION_MAP } from './illustrations';
// Composants partagés — ExamPage et InstitutionalDossierPage
import { useEffect, useRef, useState } from 'react';

export type QData = {
  id: string;
  text: string;
  options: string[];
  correct_answer?: string;
  correct?: string;
  number?: number;
  category?: string;
  mediaType?: string;
  media?: string;
  mediaAlt?: string;
  audioUrl?: string | null;
  expl?: string;
  explanation?: string;
};

// ── Panneaux de signalisation SVG ─────────────────────────────────────────────

export function SignSvg({ type, alt }: { type: string; alt?: string }) {
  const S = { display: 'block', margin: '0 auto' };

  if (type === 'stop') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Panneau STOP'}>
      <polygon points="60,5 105,28 115,75 90,112 30,112 5,75 15,28" fill="#C0392B" stroke="#fff" strokeWidth="5"/>
      <polygon points="60,14 98,32 107,72 86,104 34,104 13,72 22,32" fill="none" stroke="rgba(255,255,255,.3)" strokeWidth="2"/>
      <text x="60" y="70" textAnchor="middle" fill="#fff" fontSize="22" fontWeight="bold" fontFamily="Arial Black,sans-serif">STOP</text>
    </svg>
  );

  if (type === 'give_way') return (
    <svg viewBox="0 0 120 130" width="105" height="115" style={S} role="img" aria-label={alt ?? 'Cédez le passage'}>
      <polygon points="60,120 5,20 115,20" fill="#fff" stroke="#C0392B" strokeWidth="8"/>
      <polygon points="60,105 18,32 102,32" fill="#fff" stroke="#C0392B" strokeWidth="5"/>
    </svg>
  );

  if (type === 'speed_30') return <SpeedSign speed="30" alt={alt}/>;
  if (type === 'speed_50') return <SpeedSign speed="50" alt={alt}/>;
  if (type === 'speed_70') return <SpeedSign speed="70" alt={alt}/>;
  if (type === 'speed_90') return <SpeedSign speed="90" alt={alt}/>;
  if (type === 'speed_100') return <SpeedSign speed="100" alt={alt}/>;
  if (type === 'speed_end') return <SpeedEndSign alt={alt}/>;

  if (type === 'no_entry') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Sens interdit'}>
      <circle cx="60" cy="60" r="55" fill="#C0392B" stroke="#fff" strokeWidth="5"/>
      <rect x="18" y="48" width="84" height="24" rx="5" fill="#fff"/>
    </svg>
  );

  if (type === 'roundabout') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Giratoire'}>
      <circle cx="60" cy="60" r="55" fill="#1A6FC4" stroke="#fff" strokeWidth="5"/>
      <circle cx="60" cy="60" r="22" fill="none" stroke="#fff" strokeWidth="5"/>
      <path d="M38 60 Q38 36 60 36" fill="none" stroke="#fff" strokeWidth="5" strokeLinecap="round"/>
      <polygon points="60,32 54,44 66,44" fill="#fff"/>
      <path d="M60 82 Q82 82 82 60" fill="none" stroke="#fff" strokeWidth="5" strokeLinecap="round"/>
      <polygon points="86,60 74,54 74,66" fill="#fff"/>
    </svg>
  );

  if (type === 'mandatory_straight') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Tout droit obligatoire'}>
      <circle cx="60" cy="60" r="55" fill="#1A6FC4" stroke="#fff" strokeWidth="5"/>
      <path d="M60 95 L60 30" stroke="#fff" strokeWidth="10" strokeLinecap="round"/>
      <polygon points="60,22 48,42 72,42" fill="#fff"/>
    </svg>
  );

  if (type === 'mandatory') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Direction obligatoire'}>
      <circle cx="60" cy="60" r="55" fill="#1A6FC4" stroke="#fff" strokeWidth="5"/>
      <path d="M28 60 L92 60 M76 44 L92 60 L76 76" stroke="#fff" strokeWidth="9" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );

  if (type === 'priority') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Route prioritaire'}>
      <rect x="35" y="10" width="50" height="50" fill="#F5C518" stroke="#0A2540" strokeWidth="4" transform="rotate(45 60 35)"/>
      <rect x="42" y="17" width="36" height="36" fill="#fff" transform="rotate(45 60 35)"/>
    </svg>
  );

  if (type === 'no_overtaking') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Dépassement interdit'}>
      <circle cx="60" cy="60" r="55" fill="#fff" stroke="#C0392B" strokeWidth="8"/>
      <circle cx="44" cy="60" r="15" fill="#C0392B"/>
      <circle cx="76" cy="60" r="15" fill="#333"/>
      <line x1="22" y1="22" x2="98" y2="98" stroke="#C0392B" strokeWidth="8"/>
    </svg>
  );

  if (type === 'pedestrian_crossing') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Passage piéton'}>
      <polygon points="60,5 115,115 5,115" fill="#fff" stroke="#C0392B" strokeWidth="7"/>
      <circle cx="70" cy="55" r="7" fill="#333"/>
      <path d="M70 62 L65 85 M65 85 L55 105 M65 85 L75 105 M55 70 L80 70" stroke="#333" strokeWidth="4" fill="none" strokeLinecap="round"/>
    </svg>
  );

  if (type === 'school_zone') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Zone scolaire'}>
      <polygon points="60,5 115,115 5,115" fill="#F5C518" stroke="#0A2540" strokeWidth="5"/>
      <text x="60" y="95" textAnchor="middle" fill="#0A2540" fontSize="9" fontWeight="bold">ÉCOLE</text>
      <rect x="42" y="55" width="36" height="28" rx="2" fill="#0A2540"/>
      <polygon points="42,55 60,38 78,55" fill="#0A2540"/>
    </svg>
  );

  if (type === 'danger') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Danger'}>
      <polygon points="60,8 112,108 8,108" fill="#fff" stroke="#C0392B" strokeWidth="7"/>
      <text x="60" y="95" textAnchor="middle" fill="#C0392B" fontSize="46" fontWeight="bold">!</text>
    </svg>
  );

  if (type === 'parking') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Parking autorisé'}>
      <rect x="5" y="5" width="110" height="110" rx="12" fill="#1A6FC4"/>
      <text x="60" y="82" textAnchor="middle" fill="#fff" fontSize="68" fontWeight="bold" fontFamily="Arial Black">P</text>
    </svg>
  );

  if (type === 'no_parking') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Stationnement interdit'}>
      <circle cx="60" cy="60" r="55" fill="#fff" stroke="#1A6FC4" strokeWidth="8"/>
      <line x1="20" y1="60" x2="100" y2="60" stroke="#1A6FC4" strokeWidth="8"/>
      <line x1="20" y1="20" x2="100" y2="100" stroke="#C0392B" strokeWidth="8"/>
    </svg>
  );

  if (type === 'end_restriction') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Fin de restriction'}>
      <circle cx="60" cy="60" r="55" fill="#fff" stroke="#888" strokeWidth="5"/>
      {Array.from({length:6},(_,i)=>(
        <line key={i} x1={24+i*14} y1="90" x2={34+i*14} y2="30" stroke="#888" strokeWidth="4"/>
      ))}
    </svg>
  );

  if (type === 'traffic_light_red') return <TrafficLight state="red" alt={alt}/>;
  if (type === 'traffic_light_orange') return <TrafficLight state="orange" alt={alt}/>;
  if (type === 'traffic_light_green') return <TrafficLight state="green" alt={alt}/>;
  if (type === 'traffic_light_red_orange') return <TrafficLight state="red_orange" alt={alt}/>;

  // ── Panneaux de danger (triangle rouge) ──────────────────────────────
  if (type === 'danger_children') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Passage d\'enfants'}>
      <polygon points="60,8 112,108 8,108" fill="#fff" stroke="#C0392B" strokeWidth="7" strokeLinejoin="round"/>
      {/* Adulte + enfant stylisés (norme A13) */}
      <circle cx="52" cy="55" r="6" fill="#1a1a1a"/>
      <path d="M52 61 L50 82 M50 82 L44 98 M50 82 L56 98 M44 66 L60 72" stroke="#1a1a1a" strokeWidth="3.5" fill="none" strokeLinecap="round"/>
      <circle cx="74" cy="62" r="5" fill="#1a1a1a"/>
      <path d="M74 67 L73 84 M73 84 L68 97 M73 84 L79 97 M66 72 L80 76" stroke="#1a1a1a" strokeWidth="3" fill="none" strokeLinecap="round"/>
    </svg>
  );

  if (type === 'danger_slippery') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Chaussée glissante'}>
      <polygon points="60,8 112,108 8,108" fill="#fff" stroke="#C0392B" strokeWidth="7" strokeLinejoin="round"/>
      <rect x="44" y="58" width="32" height="16" rx="3" fill="#1a1a1a"/>
      <circle cx="50" cy="76" r="5" fill="#1a1a1a"/><circle cx="70" cy="76" r="5" fill="#1a1a1a"/>
      <path d="M40 92 q6 -8 12 0 q6 8 12 0 q6 -8 12 0" stroke="#1a1a1a" strokeWidth="3" fill="none"/>
      <path d="M78 62 q6 4 0 10 M84 58 q8 6 0 16" stroke="#1a1a1a" strokeWidth="2.5" fill="none"/>
    </svg>
  );

  if (type === 'danger_bend') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Virage dangereux'}>
      <polygon points="60,8 112,108 8,108" fill="#fff" stroke="#C0392B" strokeWidth="7" strokeLinejoin="round"/>
      <path d="M60 96 L60 70 Q60 54 74 54 Q88 54 88 66" stroke="#1a1a1a" strokeWidth="8" fill="none" strokeLinecap="round"/>
      <polygon points="60,54 50,72 70,72" fill="#1a1a1a"/>
    </svg>
  );

  if (type === 'danger_roundabout') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Carrefour à sens giratoire'}>
      <polygon points="60,8 112,108 8,108" fill="#fff" stroke="#C0392B" strokeWidth="7" strokeLinejoin="round"/>
      <g transform="translate(0,6)">
        <path d="M48 66 A16 16 0 1 1 60 78" fill="none" stroke="#1a1a1a" strokeWidth="6" strokeLinecap="round"/>
        <polygon points="44,60 52,52 58,64" fill="#1a1a1a"/>
        <path d="M72 78 A16 16 0 0 1 60 78" fill="none" stroke="#1a1a1a" strokeWidth="6" strokeLinecap="round"/>
        <path d="M62 92 A16 16 0 0 1 48 82" fill="none" stroke="#1a1a1a" strokeWidth="6" strokeLinecap="round"/>
      </g>
    </svg>
  );

  if (type === 'danger_generic') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Autres dangers'}>
      <polygon points="60,8 112,108 8,108" fill="#fff" stroke="#C0392B" strokeWidth="7" strokeLinejoin="round"/>
      <text x="60" y="96" textAnchor="middle" fill="#1a1a1a" fontSize="52" fontWeight="bold" fontFamily="Arial Black">!</text>
    </svg>
  );

  // ── Panneaux d'obligation (rond bleu) ────────────────────────────────
  if (type === 'mandatory_right') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Obligation de tourner à droite'}>
      <circle cx="60" cy="60" r="55" fill="#1A6FC4" stroke="#fff" strokeWidth="5"/>
      <path d="M40 78 Q40 48 66 48 M52 36 L70 48 L52 60" stroke="#fff" strokeWidth="9" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );

  if (type === 'no_left_turn') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Interdiction de tourner à gauche'}>
      <circle cx="60" cy="60" r="55" fill="#fff" stroke="#C0392B" strokeWidth="8"/>
      <path d="M78 82 Q78 52 52 52 M64 40 L46 52 L64 64" stroke="#1a1a1a" strokeWidth="8" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
      <line x1="22" y1="22" x2="98" y2="98" stroke="#C0392B" strokeWidth="8"/>
    </svg>
  );

  if (type === 'no_stopping') return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={S} role="img" aria-label={alt ?? 'Arrêt et stationnement interdits'}>
      <circle cx="60" cy="60" r="55" fill="#1A6FC4" stroke="#C0392B" strokeWidth="6"/>
      <line x1="22" y1="22" x2="98" y2="98" stroke="#C0392B" strokeWidth="7"/>
      <line x1="98" y1="22" x2="22" y2="98" stroke="#C0392B" strokeWidth="7"/>
    </svg>
  );

  if (type === 'speed_70') return <SpeedSign speed="70" alt={alt}/>;
  if (type === 'speed_110') return <SpeedSign speed="110" alt={alt}/>;
  if (type === 'speed_130') return <SpeedSign speed="130" alt={alt}/>;

  return (
    <div style={{ height: 110, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', fontSize: 13, background: 'var(--bg)', borderRadius: 8 }}>
      Panneau non disponible
    </div>
  );
}

function SpeedSign({ speed, alt }: { speed: string; alt?: string }) {
  return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={{ display: 'block', margin: '0 auto' }} role="img" aria-label={alt ?? `Limitation ${speed} km/h`}>
      <circle cx="60" cy="60" r="55" fill="#fff" stroke="#C0392B" strokeWidth="10"/>
      <circle cx="60" cy="60" r="44" fill="#fff" stroke="#C0392B" strokeWidth="1"/>
      <text x="60" y="75" textAnchor="middle" fill="#0A2540" fontSize={speed.length > 2 ? 28 : 34} fontWeight="bold" fontFamily="Arial Black,sans-serif">{speed}</text>
    </svg>
  );
}

function SpeedEndSign({ alt }: { alt?: string }) {
  return (
    <svg viewBox="0 0 120 120" width="110" height="110" style={{ display: 'block', margin: '0 auto' }} role="img" aria-label={alt ?? 'Fin de limitation de vitesse'}>
      <circle cx="60" cy="60" r="55" fill="#fff" stroke="#888" strokeWidth="5"/>
      {Array.from({length:5},(_,i)=>(
        <line key={i} x1={26+i*16} y1="88" x2={38+i*16} y2="32" stroke="#888" strokeWidth="4"/>
      ))}
      <text x="60" y="74" textAnchor="middle" fill="#0A2540" fontSize="28" fontWeight="bold" fontFamily="Arial Black">50</text>
    </svg>
  );
}

function TrafficLight({ state, alt }: { state: string; alt?: string }) {
  const red    = state === 'red' || state === 'red_orange';
  const orange = state === 'orange' || state === 'red_orange';
  const green  = state === 'green';
  return (
    <svg viewBox="0 0 60 160" width="55" height="145" style={{ display: 'block', margin: '0 auto' }} role="img" aria-label={alt ?? 'Feu tricolore'}>
      <rect x="8" y="5" width="44" height="150" rx="8" fill="#1a1a1a" stroke="#333" strokeWidth="2"/>
      <circle cx="30" cy="35"  r="16" fill={red    ? '#FF2D00' : '#3a0000'} filter={red    ? 'url(#glow-r)' : undefined}/>
      <circle cx="30" cy="80"  r="16" fill={orange ? '#FF9500' : '#3a2a00'} filter={orange ? 'url(#glow-o)' : undefined}/>
      <circle cx="30" cy="125" r="16" fill={green  ? '#00C830' : '#003a10'} filter={green  ? 'url(#glow-g)' : undefined}/>
      <defs>
        <filter id="glow-r"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        <filter id="glow-o"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        <filter id="glow-g"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
    </svg>
  );
}

// ── Scènes de circulation SVG ─────────────────────────────────────────────────

export function SceneSvg({ type, alt }: { type: string; alt?: string }) {
  if (type === 'intersection') return (
    <svg viewBox="0 0 280 200" width="100%" style={{ maxWidth: 340, display: 'block', margin: '0 auto' }} role="img" aria-label={alt ?? 'Intersection'}>
      {/* Fond herbe */}
      <rect width="280" height="200" fill="#2d5a1b"/>
      {/* Routes */}
      <rect x="0" y="78" width="280" height="44" fill="#555"/>
      <rect x="112" y="0" width="56" height="200" fill="#555"/>
      {/* Marquages */}
      <line x1="0" y1="100" x2="104" y2="100" stroke="#f1c40f" strokeWidth="2" strokeDasharray="10,8"/>
      <line x1="176" y1="100" x2="280" y2="100" stroke="#f1c40f" strokeWidth="2" strokeDasharray="10,8"/>
      <line x1="140" y1="0" x2="140" y2="70" stroke="#f1c40f" strokeWidth="2" strokeDasharray="10,8"/>
      <line x1="140" y1="130" x2="140" y2="200" stroke="#f1c40f" strokeWidth="2" strokeDasharray="10,8"/>
      {/* Véhicule A — vient de gauche */}
      <rect x="30" y="84" width="50" height="22" rx="5" fill="#3498db"/>
      <rect x="36" y="87" width="18" height="12" rx="2" fill="rgba(200,230,255,.5)"/>
      <rect x="56" y="87" width="18" height="12" rx="2" fill="rgba(200,230,255,.5)"/>
      <text x="55" y="99" textAnchor="middle" fill="#fff" fontSize="11" fontWeight="bold">A →</text>
      {/* Véhicule B — vient du bas */}
      <rect x="120" y="145" width="40" height="22" rx="5" fill="#e74c3c" transform="rotate(270,140,156)"/>
      <rect x="126" y="148" width="28" height="12" rx="2" fill="rgba(255,200,200,.4)" transform="rotate(270,140,156)"/>
      <text x="140" y="162" textAnchor="middle" fill="#fff" fontSize="11" fontWeight="bold">B ↑</text>
      {/* Label */}
      <text x="140" y="192" textAnchor="middle" fill="#f1c40f" fontSize="9" fontWeight="bold">Sans signalisation — Priorité à droite</text>
    </svg>
  );

  if (type === 'intersection_roundabout') return (
    <svg viewBox="0 0 280 200" width="100%" style={{ maxWidth: 340, display: 'block', margin: '0 auto' }} role="img" aria-label={alt ?? 'Giratoire'}>
      <rect width="280" height="200" fill="#2d5a1b"/>
      <circle cx="140" cy="100" r="70" fill="#555"/>
      <circle cx="140" cy="100" r="35" fill="#2d5a1b"/>
      <circle cx="140" cy="100" r="28" fill="#2d5a1b" stroke="#fff" strokeWidth="2"/>
      <line x1="0" y1="100" x2="70" y2="100" stroke="#555" strokeWidth="28"/>
      <line x1="210" y1="100" x2="280" y2="100" stroke="#555" strokeWidth="28"/>
      <line x1="140" y1="0" x2="140" y2="70" stroke="#555" strokeWidth="28"/>
      <line x1="140" y1="130" x2="140" y2="200" stroke="#555" strokeWidth="28"/>
      {/* Véhicule dans le giratoire */}
      <rect x="158" y="68" width="36" height="16" rx="4" fill="#3498db" transform="rotate(-30,176,76)"/>
      {/* Véhicule entrant */}
      <rect x="98" y="92" width="36" height="16" rx="4" fill="#e74c3c"/>
      <text x="116" y="86" textAnchor="middle" fill="#e74c3c" fontSize="9" fontWeight="bold">CÈDE</text>
      <text x="116" y="120" textAnchor="middle" fill="#3498db" fontSize="9" fontWeight="bold">PRIORITAIRE</text>
    </svg>
  );

  if (type === 'safe_distance') return (
    <svg viewBox="0 0 360 140" width="100%" style={{ maxWidth: 420, display: 'block', margin: '0 auto' }} role="img" aria-label={alt ?? 'Distance de sécurité'}>
      <rect width="360" height="140" fill="#1a2e1a"/>
      <rect x="0" y="60" width="360" height="60" fill="#444"/>
      <line x1="0" y1="90" x2="360" y2="90" stroke="#f1c40f" strokeWidth="2" strokeDasharray="14,10"/>
      {/* Voiture avant */}
      <rect x="230" y="67" width="68" height="30" rx="6" fill="#e74c3c"/>
      <rect x="236" y="70" width="24" height="18" rx="2" fill="rgba(255,200,200,.4)"/>
      <rect x="264" y="70" width="24" height="18" rx="2" fill="rgba(255,200,200,.4)"/>
      <text x="264" y="88" textAnchor="middle" fill="#fff" fontSize="9" fontWeight="bold">DEVANT</text>
      {/* Votre voiture */}
      <rect x="36" y="67" width="68" height="30" rx="6" fill="#3498db"/>
      <rect x="42" y="70" width="24" height="18" rx="2" fill="rgba(200,230,255,.4)"/>
      <rect x="70" y="70" width="24" height="18" rx="2" fill="rgba(200,230,255,.4)"/>
      <text x="70" y="88" textAnchor="middle" fill="#fff" fontSize="9" fontWeight="bold">VOUS</text>
      {/* Flèche distance */}
      <line x1="106" y1="110" x2="228" y2="110" stroke="#27ae60" strokeWidth="2"/>
      <polygon points="228,106 236,110 228,114" fill="#27ae60"/>
      <polygon points="106,106 98,110 106,114" fill="#27ae60"/>
      <text x="167" y="126" textAnchor="middle" fill="#27ae60" fontSize="11" fontWeight="bold">≥ 2 secondes (≈ 56 m à 100 km/h)</text>
    </svg>
  );

  if (type === 'night_driving') return (
    <svg viewBox="0 0 360 160" width="100%" style={{ maxWidth: 420, display: 'block', margin: '0 auto' }} role="img" aria-label={alt ?? 'Conduite de nuit'}>
      <rect width="360" height="160" fill="#0a0e1a"/>
      <rect x="0" y="80" width="360" height="60" fill="#2a2a2a"/>
      <line x1="0" y1="110" x2="360" y2="110" stroke="#f1c40f" strokeWidth="2" strokeDasharray="14,10"/>
      {/* Phares voiture */}
      <rect x="28" y="87" width="68" height="30" rx="6" fill="#333"/>
      <ellipse cx="32" cy="93" rx="12" ry="8" fill="#FFEAA0" opacity="0.9"/>
      <ellipse cx="32" cy="113" rx="12" ry="8" fill="#FFEAA0" opacity="0.9"/>
      {/* Cônes de lumière */}
      <polygon points="44,93 44,113 260,130 260,76" fill="rgba(255,234,160,.08)"/>
      {/* Panneau éclairé */}
      <circle cx="310" cy="60" r="26" fill="#fff" stroke="#C0392B" strokeWidth="6"/>
      <text x="310" y="68" textAnchor="middle" fill="#0A2540" fontSize="18" fontWeight="bold">50</text>
      {/* Étoiles */}
      {[[50,20],[120,35],[200,15],[280,28],[340,18]].map(([x,y],i)=>(
        <circle key={i} cx={x} cy={y} r="1.5" fill="#fff" opacity="0.7"/>
      ))}
      <text x="180" y="150" textAnchor="middle" fill="#aaa" fontSize="10">Feux de croisement obligatoires — portée 30–40 m</text>
    </svg>
  );

  if (type === 'rain_driving') return (
    <svg viewBox="0 0 360 180" width="100%" style={{ maxWidth: 420, display: 'block', margin: '0 auto' }} role="img" aria-label={alt ?? 'Conduite sous la pluie'}>
      <rect width="360" height="180" fill="#1a2535"/>
      <rect x="0" y="110" width="360" height="60" fill="#3d3d3d"/>
      <line x1="0" y1="140" x2="360" y2="140" stroke="#f1c40f" strokeWidth="2" strokeDasharray="14,10"/>
      {/* Voiture */}
      <rect x="40" y="117" width="68" height="30" rx="6" fill="#3498db"/>
      {/* Essuie-glaces */}
      <path d="M48 120 Q68 108 88 120" fill="none" stroke="#aaa" strokeWidth="2"/>
      {/* Gouttes pluie */}
      {Array.from({length:18},(_,i)=>{
        const x = 20 + (i%9) * 36 + (Math.floor(i/9)*18);
        const y = 20 + (i%5) * 22;
        return <line key={i} x1={x} y1={y} x2={x-4} y2={y+12} stroke="#80b8d8" strokeWidth="1.5" opacity="0.7"/>;
      })}
      {/* Flaque */}
      <ellipse cx="165" cy="148" rx="60" ry="8" fill="rgba(80,130,180,.3)"/>
      <text x="180" y="170" textAnchor="middle" fill="#aaa" fontSize="10">Distances doublées — vitesse réduite obligatoire</text>
    </svg>
  );

  if (type === 'overtake') return (
    <svg viewBox="0 0 360 180" width="100%" style={{ maxWidth: 420, display: 'block', margin: '0 auto' }} role="img" aria-label={alt ?? 'Dépassement'}>
      <rect width="360" height="180" fill="#1a2e1a"/>
      <rect x="0" y="90" width="360" height="70" fill="#444"/>
      <rect x="0" y="140" width="360" height="3" fill="#fff"/>
      {/* Axe */}
      <line x1="0" y1="125" x2="360" y2="125" stroke="#fff" strokeWidth="1.5" strokeDasharray="12,8"/>
      {/* Camion */}
      <rect x="130" y="97" width="72" height="32" rx="4" fill="#7f8c8d"/>
      <rect x="130" y="97" width="28" height="20" rx="3" fill="#6c7a89"/>
      <text x="175" y="117" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">CAMION</text>
      {/* Voiture dépassant */}
      <rect x="60" y="100" width="55" height="26" rx="5" fill="#3498db"/>
      <text x="87" y="86" textAnchor="middle" fill="#3498db" fontSize="9" fontWeight="bold">VOUS →</text>
      {/* Interdit */}
      <circle cx="290" cy="60" r="26" fill="#fff" stroke="#C0392B" strokeWidth="6"/>
      <line x1="270" y1="40" x2="310" y2="80" stroke="#C0392B" strokeWidth="6"/>
      <circle cx="275" cy="48" r="10" fill="#C0392B"/>
      <circle cx="305" cy="48" r="10" fill="#555"/>
      <text x="290" y="102" textAnchor="middle" fill="#C0392B" fontSize="9" fontWeight="bold">INTERDIT ICI</text>
    </svg>
  );

  if (type === 'emergency') return (
    <svg viewBox="0 0 360 160" width="100%" style={{ maxWidth: 420, display: 'block', margin: '0 auto' }} role="img" aria-label={alt ?? 'Véhicule d\'urgence'}>
      <rect width="360" height="160" fill="#0d1117"/>
      <rect x="0" y="70" width="360" height="65" fill="#3d3d3d"/>
      <line x1="0" y1="102" x2="360" y2="102" stroke="#f1c40f" strokeWidth="2" strokeDasharray="12,8"/>
      {/* Véhicule à gauche */}
      <rect x="18" y="106" width="50" height="22" rx="4" fill="#3498db" opacity="0.6"/>
      {/* Ambulance */}
      <rect x="125" y="76" width="80" height="35" rx="6" fill="#fff"/>
      <rect x="125" y="76" width="30" height="20" rx="4" fill="#d0d8e0"/>
      <text x="175" y="97" textAnchor="middle" fill="#C0392B" fontSize="11" fontWeight="bold">SAMU</text>
      <line x1="155" y1="82" x2="165" y2="92" stroke="#C0392B" strokeWidth="3"/>
      <line x1="160" y1="82" x2="160" y2="92" stroke="#C0392B" strokeWidth="3"/>
      {/* Gyrophares */}
      <circle cx="140" cy="74" r="5" fill="#ff4400" opacity="0.9"/>
      <circle cx="155" cy="72" r="5" fill="#0044ff" opacity="0.9"/>
      <circle cx="170" cy="72" r="5" fill="#ff4400" opacity="0.9"/>
      {/* Véhicule dégageant */}
      <rect x="270" y="106" width="50" height="22" rx="4" fill="#3498db" opacity="0.6"/>
      <text x="180" y="148" textAnchor="middle" fill="#f1c40f" fontSize="10" fontWeight="bold">Dégagez immédiatement — priorité absolue aux urgences</text>
    </svg>
  );

  if (type === 'parking_scene') return (
    <svg viewBox="0 0 320 200" width="100%" style={{ maxWidth: 380, display: 'block', margin: '0 auto' }} role="img" aria-label={alt ?? 'Stationnement'}>
      <rect width="320" height="200" fill="#c8d0c8"/>
      {/* Trottoir */}
      <rect x="0" y="0" width="320" height="50" fill="#bbb"/>
      <rect x="0" y="50" width="320" height="8" fill="#999"/>
      {/* Chaussée */}
      <rect x="0" y="58" width="320" height="142" fill="#555"/>
      {/* Places de parking délimitées */}
      {[20,80,140,200,260].map((x,i)=>(
        <g key={i}>
          <rect x={x} y={10} width="52" height="38" rx="2" fill="none" stroke="#fff" strokeWidth="1.5"/>
          {i===1 && <rect x={x} y={10} width="52" height="38" rx="2" fill="rgba(52,152,219,.3)"/>}
        </g>
      ))}
      {/* Voiture garée */}
      <rect x="82" y="14" width="48" height="30" rx="5" fill="#3498db"/>
      {/* Panneau */}
      <rect x="290" y="5" width="24" height="38" rx="4" fill="#1A6FC4"/>
      <text x="302" y="28" textAnchor="middle" fill="#fff" fontSize="14" fontWeight="bold">P</text>
      <text x="160" y="185" textAnchor="middle" fill="#f1c40f" fontSize="10" fontWeight="bold">Stationnement autorisé — places délimitées</text>
    </svg>
  );

  if (type === 'alcohol_scene') return (
    <svg viewBox="0 0 320 180" width="100%" style={{ maxWidth: 380, display: 'block', margin: '0 auto' }} role="img" aria-label={alt ?? 'Contrôle alcoolémie'}>
      <rect width="320" height="180" fill="#1a2535"/>
      <rect x="0" y="100" width="320" height="60" fill="#333"/>
      <line x1="0" y1="130" x2="320" y2="130" stroke="#f1c40f" strokeWidth="2" strokeDasharray="12,8"/>
      {/* Voiture contrôlée */}
      <rect x="40" y="107" width="70" height="30" rx="6" fill="#3498db"/>
      {/* Agent */}
      <ellipse cx="165" cy="95" rx="10" ry="12" fill="#ffcc99"/>
      <rect x="157" y="105" width="16" height="22" rx="2" fill="#006B3F"/>
      <rect x="170" y="108" width="20" height="8" rx="3" fill="#aaa"/>
      <text x="160" y="150" textAnchor="middle" fill="#fff" fontSize="9">Éthylotest</text>
      {/* Taux légal */}
      <rect x="220" y="60" width="86" height="50" rx="6" fill="rgba(255,255,255,.08)" stroke="#C0392B" strokeWidth="1"/>
      <text x="263" y="80" textAnchor="middle" fill="#f1c40f" fontSize="9" fontWeight="bold">TAUX LÉGAL</text>
      <text x="263" y="98" textAnchor="middle" fill="#fff" fontSize="11" fontWeight="bold">≤ 0,5 g/L</text>
      <text x="263" y="110" textAnchor="middle" fill="#aaa" fontSize="8">Nouveaux conducteurs</text>
      <text x="263" y="120" textAnchor="middle" fill="#C0392B" fontSize="8" fontWeight="bold">≤ 0,2 g/L</text>
    </svg>
  );

  if (type === 'first_aid') return (
    <svg viewBox="0 0 320 180" width="100%" style={{ maxWidth: 380, display: 'block', margin: '0 auto' }} role="img" aria-label={alt ?? 'Premiers secours'}>
      <rect width="320" height="180" fill="#1a2535"/>
      <rect x="0" y="100" width="320" height="60" fill="#333"/>
      {/* Croix rouge */}
      <rect x="40" y="30" width="80" height="80" rx="8" fill="#C0392B"/>
      <rect x="56" y="50" width="48" height="16" rx="3" fill="#fff"/>
      <rect x="72" y="34" width="16" height="48" rx="3" fill="#fff"/>
      {/* Accident schématique */}
      <rect x="165" y="107" width="60" height="28" rx="5" fill="#e74c3c"/>
      <ellipse cx="175" cy="137" rx="8" ry="4" fill="#444"/>
      <ellipse cx="217" cy="137" rx="8" ry="4" fill="#444"/>
      {/* Triangle */}
      <polygon points="220,65 235,40 250,65" fill="#f1c40f" stroke="#0A2540" strokeWidth="2"/>
      <text x="235" y="60" textAnchor="middle" fill="#0A2540" fontSize="9" fontWeight="bold">!</text>
      <text x="160" y="165" textAnchor="middle" fill="#fff" fontSize="9">Triangle · Protéger · Alerter · Secourir</text>
    </svg>
  );

  return (
    <div style={{ height: 140, background: 'var(--bg,#f1f5f9)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', fontSize: 13 }}>
      Illustration indisponible
    </div>
  );
}

// ── Lecteur vidéo HTML5 ───────────────────────────────────────────────────────

export function VideoPlayer({ url, poster, alt }: { url: string; poster?: string; alt?: string }) {
  return (
    <div style={{ borderRadius: 10, overflow: 'hidden', background: '#000', position: 'relative' }}>
      <video
        src={url}
        poster={poster}
        controls
        preload="metadata"
        style={{ width: '100%', maxHeight: 280, display: 'block' }}
        aria-label={alt ?? 'Vidéo pédagogique'}
      >
        <p>Votre navigateur ne supporte pas la lecture vidéo HTML5.</p>
      </video>
      {alt && (
        <div style={{ background: 'rgba(0,0,0,.6)', color: '#fff', fontSize: 11, padding: '4px 10px', textAlign: 'center' }}>
          {alt}
        </div>
      )}
    </div>
  );
}

// ── Bloc média unifié — style Ornikar ─────────────────────────────────────────

export function MediaBlock({ mediaType, media, alt }: { mediaType?: string; media?: string; alt?: string }) {
  const [imgFailed, setImgFailed] = useState(false);
  if (!media) return null;

  // Vidéo réelle
  if (mediaType === 'video') {
    return (
      <div style={{ background: '#000', borderRadius: 14, overflow: 'hidden', marginBottom: 0, boxShadow: '0 4px 20px rgba(0,0,0,.3)' }}>
        <VideoPlayer url={media} alt={alt} />
      </div>
    );
  }

  // Image réelle (URL http/https). Si le chargement échoue, on bascule sur
  // l'illustration SVG au lieu d'afficher l'icône « image cassée ».
  if (mediaType === 'image' && /^https?:\/\//.test(media) && !imgFailed) {
    return (
      <div style={{ borderRadius: 14, overflow: 'hidden', marginBottom: 0, background: '#f8fafc', textAlign: 'center', padding: 20 }}>
        <img
          src={media}
          alt={alt ?? 'Illustration de la question'}
          onError={() => setImgFailed(true)}
          style={{ maxWidth: '100%', maxHeight: 300, borderRadius: 8, objectFit: 'contain' }}
        />
        {alt && <p style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 10, lineHeight: 1.5 }}>{alt}</p>}
      </div>
    );
  }

  // Illustration style Ornikar — first-person, route perspective
  const IllusComp = ILLUSTRATION_MAP[media];
  if (IllusComp) {
    return (
      <div style={{ borderRadius: 0, overflow: 'hidden', lineHeight: 0 }}>
        <IllusComp style={{ width: '100%', height: 'auto', display: 'block' }} />
        {alt && (
          <div style={{
            background: 'rgba(13,33,55,.82)',
            color: '#fff',
            fontSize: 11.5,
            padding: '7px 16px',
            lineHeight: 1.55,
            textAlign: 'center',
          }}>
            {alt}
          </div>
        )}
      </div>
    );
  }

  // Fallback : SVG schématique. Les panneaux (type 'sign') passent par SignSvg,
  // le reste (scènes non migrées) par SceneSvg.
  if (mediaType === 'sign') {
    return (
      <div style={{
        background: 'linear-gradient(135deg, #f8fafc, #f0f4f8)',
        border: '1px solid var(--border)',
        padding: '24px 20px 18px',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
      }}>
        <SignSvg type={media} alt={alt} />
        {alt && <p style={{ fontSize: 11.5, color: 'var(--muted)', textAlign: 'center', maxWidth: 280, lineHeight: 1.5 }}>{alt}</p>}
      </div>
    );
  }

  if (media.match(/^(no_entry|mandatory|priority|no_overtaking|pedestrian|school|danger|parking|end_restriction|speed_|give_way|stop|roundabout|no_)/)) {
    return (
      <div style={{
        background: 'linear-gradient(135deg, #f8fafc, #f0f4f8)',
        border: '1px solid var(--border)',
        padding: '24px 20px 18px',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
      }}>
        <SignSvg type={media} alt={alt} />
        {alt && <p style={{ fontSize: 11.5, color: 'var(--muted)', textAlign: 'center', maxWidth: 280, lineHeight: 1.5 }}>{alt}</p>}
      </div>
    );
  }

  return (
    <div style={{ overflow: 'hidden', lineHeight: 0 }}>
      <SceneSvg type={media.replace('situation_', '').replace('intersection_', '')} alt={alt} />
      {alt && (
        <div style={{ background: 'rgba(0,0,0,.65)', color: '#fff', fontSize: 11, padding: '6px 14px', textAlign: 'center' }}>
          {alt}
        </div>
      )}
    </div>
  );
}

// ── Timer circulaire ──────────────────────────────────────────────────────────

export function Timer({ secs, total, onExpire }: { secs: number; total: number; onExpire: () => void }) {
  const [rem, setRem] = useState(secs);
  const fired = useRef(false);
  useEffect(() => {
    if (rem <= 0 && !fired.current) { fired.current = true; onExpire(); return; }
    const t = setTimeout(() => setRem(r => Math.max(0, r - 1)), 1000);
    return () => clearTimeout(t);
  }, [rem, onExpire]);
  const m = Math.floor(rem / 60), s = rem % 60;
  const pct = (rem / total * 100).toFixed(1) + '%';
  const urgent = rem <= 300, crit = rem <= 60;
  const color = crit ? 'var(--red, #C0392B)' : urgent ? 'var(--gold, #D4A017)' : 'var(--guinea-green, #006B3F)';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <div style={{ width: 88, height: 88, borderRadius: '50%', background: `conic-gradient(${color} ${pct}, var(--border,#DDE3EC) 0)`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: 70, height: 70, borderRadius: '50%', background: 'var(--surface,#fff)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: 18, fontWeight: 800, fontVariantNumeric: 'tabular-nums', color: 'var(--ink)', letterSpacing: '-.03em' }}>
            {String(m).padStart(2,'0')}:{String(s).padStart(2,'0')}
          </span>
        </div>
      </div>
      <p style={{ fontSize: 10.5, color: crit ? 'var(--red)' : 'var(--muted)', fontWeight: crit ? 700 : 500, margin: 0 }}>
        {crit ? 'Temps critique' : urgent ? '< 5 minutes' : 'Temps restant'}
      </p>
    </div>
  );
}

// ── Grille de navigation questions ───────────────────────────────────────────

export function QGrid({ total, cur, ans, onSelect }: { total: number; cur: number; ans: Record<number,string>; onSelect: (i: number) => void }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8,1fr)', gap: 3 }}>
      {Array.from({ length: total }, (_, i) => (
        <button key={i} type="button" onClick={() => onSelect(i)}
          style={{
            aspectRatio: '1', borderRadius: 5, border: '1.5px solid',
            borderColor: i === cur ? 'var(--navy)' : ans[i] ? '#86efac' : 'var(--border)',
            background: i === cur ? 'var(--navy)' : ans[i] ? '#dcfce7' : 'var(--bg)',
            color: i === cur ? '#fff' : ans[i] ? '#166534' : 'var(--muted)',
            fontSize: 10, fontWeight: 700, cursor: 'pointer', padding: 0, minHeight: 'unset',
          }}>
          {i + 1}
        </button>
      ))}
    </div>
  );
}
