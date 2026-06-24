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
  expl?: string;
  explanation?: string;
};

export function SignSvg({ type }: { type: string }) {
  if (type === 'stop') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <polygon points="60,5 105,28 115,75 90,112 30,112 5,75 15,28" fill="#c0392b" stroke="#fff" strokeWidth="4"/>
      <text x="60" y="68" textAnchor="middle" fill="#fff" fontSize="20" fontWeight="bold">STOP</text>
    </svg>
  );
  if (type === 'give_way') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <polygon points="60,115 5,15 115,15" fill="#fff" stroke="#c0392b" strokeWidth="6"/>
      <polygon points="60,100 18,28 102,28" fill="#fff" stroke="#c0392b" strokeWidth="4"/>
    </svg>
  );
  if (type === 'speed_50') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <circle cx="60" cy="60" r="55" fill="#fff" stroke="#c0392b" strokeWidth="8"/>
      <text x="60" y="74" textAnchor="middle" fill="#0A2540" fontSize="32" fontWeight="bold">50</text>
    </svg>
  );
  if (type === 'no_entry') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <circle cx="60" cy="60" r="55" fill="#c0392b" stroke="#fff" strokeWidth="4"/>
      <rect x="20" y="50" width="80" height="20" rx="4" fill="#fff"/>
    </svg>
  );
  if (type === 'roundabout') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <circle cx="60" cy="60" r="55" fill="#2980b9" stroke="#fff" strokeWidth="4"/>
      <circle cx="60" cy="60" r="22" fill="none" stroke="#fff" strokeWidth="5"/>
      <path d="M38 60 Q38 38 60 38" fill="none" stroke="#fff" strokeWidth="5"/>
      <polygon points="60,35 55,45 65,45" fill="#fff"/>
    </svg>
  );
  if (type === 'mandatory') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <circle cx="60" cy="60" r="55" fill="#2980b9" stroke="#fff" strokeWidth="4"/>
      <path d="M30 60 L90 60 M75 45 L90 60 L75 75" stroke="#fff" strokeWidth="8" fill="none" strokeLinecap="round"/>
    </svg>
  );
  if (type === 'speed_30') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <circle cx="60" cy="60" r="55" fill="#fff" stroke="#c0392b" strokeWidth="8"/>
      <text x="60" y="74" textAnchor="middle" fill="#0A2540" fontSize="32" fontWeight="bold">30</text>
    </svg>
  );
  if (type === 'speed_70') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <circle cx="60" cy="60" r="55" fill="#fff" stroke="#c0392b" strokeWidth="8"/>
      <text x="60" y="74" textAnchor="middle" fill="#0A2540" fontSize="32" fontWeight="bold">70</text>
    </svg>
  );
  if (type === 'speed_90') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <circle cx="60" cy="60" r="55" fill="#fff" stroke="#c0392b" strokeWidth="8"/>
      <text x="60" y="74" textAnchor="middle" fill="#0A2540" fontSize="32" fontWeight="bold">90</text>
    </svg>
  );
  if (type === 'priority') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <rect x="35" y="10" width="50" height="50" fill="#f1c40f" stroke="#0A2540" strokeWidth="3" transform="rotate(45 60 35)"/>
      <text x="60" y="70" textAnchor="middle" fill="#0A2540" fontSize="10">PRIORITÉ</text>
    </svg>
  );
  if (type === 'no_overtaking') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <circle cx="60" cy="60" r="55" fill="#fff" stroke="#c0392b" strokeWidth="8"/>
      <ellipse cx="45" cy="65" rx="12" ry="18" fill="#0A2540"/>
      <ellipse cx="75" cy="65" rx="12" ry="18" fill="#c0392b"/>
      <line x1="15" y1="15" x2="105" y2="105" stroke="#c0392b" strokeWidth="8"/>
    </svg>
  );
  if (type === 'pedestrian_crossing') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <rect x="5" y="5" width="110" height="110" rx="6" fill="#2980b9"/>
      <circle cx="60" cy="28" r="10" fill="#fff"/>
      <line x1="60" y1="38" x2="60" y2="75" stroke="#fff" strokeWidth="7" strokeLinecap="round"/>
      <line x1="60" y1="55" x2="40" y2="45" stroke="#fff" strokeWidth="6" strokeLinecap="round"/>
      <line x1="60" y1="55" x2="80" y2="45" stroke="#fff" strokeWidth="6" strokeLinecap="round"/>
      <line x1="60" y1="75" x2="42" y2="95" stroke="#fff" strokeWidth="6" strokeLinecap="round"/>
      <line x1="60" y1="75" x2="78" y2="95" stroke="#fff" strokeWidth="6" strokeLinecap="round"/>
    </svg>
  );
  if (type === 'school_zone') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <polygon points="60,8 112,112 8,112" fill="#f1c40f" stroke="#0A2540" strokeWidth="4"/>
      <text x="60" y="72" textAnchor="middle" fill="#0A2540" fontSize="10" fontWeight="bold">ÉCOLE</text>
      <text x="60" y="90" textAnchor="middle" fill="#0A2540" fontSize="9">30 km/h</text>
    </svg>
  );
  if (type === 'parking') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <rect x="5" y="5" width="110" height="110" rx="6" fill="#2980b9"/>
      <text x="60" y="80" textAnchor="middle" fill="#fff" fontSize="72" fontWeight="bold">P</text>
    </svg>
  );
  if (type === 'no_parking') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <circle cx="60" cy="60" r="55" fill="#fff" stroke="#c0392b" strokeWidth="8"/>
      <text x="60" y="80" textAnchor="middle" fill="#c0392b" fontSize="52" fontWeight="bold">P</text>
      <line x1="15" y1="15" x2="105" y2="105" stroke="#c0392b" strokeWidth="8"/>
    </svg>
  );
  if (type === 'danger') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <polygon points="60,8 112,112 8,112" fill="#fff" stroke="#c0392b" strokeWidth="6"/>
      <text x="60" y="98" textAnchor="middle" fill="#c0392b" fontSize="60" fontWeight="bold">!</text>
    </svg>
  );
  if (type === 'end_restriction') return (
    <svg viewBox="0 0 120 120" width="110" height="110">
      <circle cx="60" cy="60" r="55" fill="#fff" stroke="#888" strokeWidth="6"/>
      <line x1="20" y1="40" x2="100" y2="80" stroke="#888" strokeWidth="6"/>
      <line x1="20" y1="60" x2="100" y2="100" stroke="#888" strokeWidth="6"/>
      <line x1="20" y1="80" x2="100" y2="55" stroke="#888" strokeWidth="6"/>
    </svg>
  );
  return <svg viewBox="0 0 120 120" width="110" height="110"><circle cx="60" cy="60" r="55" fill="#e2e8f0"/><text x="60" y="68" textAnchor="middle" fontSize="12" fill="#667085">Illustration</text></svg>;
}

export function SceneSvg({ type }: { type: string }) {
  if (type === 'intersection') return (
    <svg viewBox="0 0 200 200" width="100%" style={{ maxWidth: 300, display: 'block', margin: '0 auto' }}>
      <rect x="0" y="85" width="200" height="30" fill="#555"/>
      <rect x="85" y="0" width="30" height="200" fill="#555"/>
      <line x1="0" y1="100" x2="80" y2="100" stroke="#f1c40f" strokeWidth="2" strokeDasharray="8,6"/>
      <line x1="120" y1="100" x2="200" y2="100" stroke="#f1c40f" strokeWidth="2" strokeDasharray="8,6"/>
      <line x1="100" y1="0" x2="100" y2="80" stroke="#f1c40f" strokeWidth="2" strokeDasharray="8,6"/>
      <line x1="100" y1="120" x2="100" y2="200" stroke="#f1c40f" strokeWidth="2" strokeDasharray="8,6"/>
      <rect x="18" y="90" width="36" height="18" rx="4" fill="#3498db"/>
      <text x="36" y="103" textAnchor="middle" fill="#fff" fontSize="11" fontWeight="bold">A →</text>
      <rect x="90" y="148" width="20" height="34" rx="4" fill="#e74c3c"/>
      <text x="100" y="168" textAnchor="middle" fill="#fff" fontSize="11" fontWeight="bold">B ↑</text>
      <text x="100" y="193" textAnchor="middle" fill="#f1c40f" fontSize="9" fontWeight="bold">B est prioritaire</text>
    </svg>
  );
  if (type === 'safe_distance') return (
    <svg viewBox="0 0 300 120" width="100%" style={{ maxWidth: 380, display: 'block', margin: '0 auto' }}>
      <rect width="300" height="120" fill="#1a2e1a"/>
      <rect x="0" y="50" width="300" height="50" fill="#3d3d3d"/>
      <line x1="0" y1="75" x2="300" y2="75" stroke="#f1c40f" strokeWidth="2" strokeDasharray="10,8"/>
      <rect x="10" y="55" width="56" height="28" rx="5" fill="#3498db"/>
      <text x="38" y="73" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">VOUS</text>
      <rect x="180" y="55" width="56" height="28" rx="5" fill="#e74c3c"/>
      <text x="208" y="73" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">DEVANT</text>
      <line x1="68" y1="80" x2="178" y2="80" stroke="#27ae60" strokeWidth="2"/>
      <text x="123" y="100" textAnchor="middle" fill="#27ae60" fontSize="11" fontWeight="bold">≥ 2 secondes</text>
    </svg>
  );
  if (type === 'emergency') return (
    <svg viewBox="0 0 280 130" width="100%" style={{ maxWidth: 380, display: 'block', margin: '0 auto' }}>
      <rect width="280" height="130" fill="#0d1117"/>
      <rect x="0" y="55" width="280" height="50" fill="#3d3d3d"/>
      <line x1="0" y1="80" x2="280" y2="80" stroke="#f1c40f" strokeWidth="2" strokeDasharray="10,8"/>
      <rect x="20" y="84" width="44" height="18" rx="4" fill="#3498db" opacity="0.7"/>
      <rect x="210" y="84" width="44" height="18" rx="4" fill="#2ecc71" opacity="0.7"/>
      <rect x="108" y="60" width="64" height="28" rx="5" fill="#fff"/>
      <text x="140" y="78" textAnchor="middle" fill="#c0392b" fontSize="11" fontWeight="bold">🚑 SAMU</text>
      <circle cx="140" cy="58" r="6" fill="#c0392b"/>
      <text x="140" y="120" textAnchor="middle" fill="#f1c40f" fontSize="10" fontWeight="bold">Dégagez la voie — priorité absolue</text>
    </svg>
  );
  if (type === 'overtake') return (
    <svg viewBox="0 0 280 150" width="100%" style={{ maxWidth: 380, display: 'block', margin: '0 auto' }}>
      <rect width="280" height="150" fill="#1a2e1a"/>
      <rect x="0" y="65" width="280" height="55" fill="#3d3d3d"/>
      <rect x="0" y="93" width="280" height="3" fill="#fff"/>
      <path d="M0 125 Q140 35 280 125" stroke="#3d3d3d" strokeWidth="55" fill="none"/>
      <rect x="36" y="70" width="46" height="21" rx="5" fill="#3498db"/>
      <rect x="100" y="70" width="46" height="21" rx="5" fill="#e74c3c"/>
      <text x="59" y="85" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">VOUS</text>
      <text x="123" y="85" textAnchor="middle" fill="#fff" fontSize="9" fontWeight="bold">CAMION</text>
      <circle cx="200" cy="36" r="18" fill="rgba(192,57,43,0.9)"/>
      <text x="200" y="41" textAnchor="middle" fill="#fff" fontSize="14" fontWeight="bold">✗</text>
    </svg>
  );
  return <div style={{ height: 120, background: 'var(--bg, #f1f5f9)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', fontSize: 13 }}>Illustration</div>;
}

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
  const color = crit ? 'var(--red, #D32F2F)' : urgent ? 'var(--gold, #F5A623)' : 'var(--green, #00875A)';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 90, height: 90, borderRadius: '50%', background: `conic-gradient(${color} ${pct}, #E4E7EC 0)`, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
        <div style={{ width: 72, height: 72, borderRadius: '50%', background: 'var(--surface, #fff)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: 20, fontWeight: 900, fontVariantNumeric: 'tabular-nums', color: 'var(--ink)' }}>
            {String(m).padStart(2,'0')}:{String(s).padStart(2,'0')}
          </span>
        </div>
      </div>
      <p style={{ fontSize: 11, color: crit ? 'var(--red, #D32F2F)' : 'var(--muted)', fontWeight: crit ? 700 : 500 }}>
        {crit ? '⚠️ Temps critique !' : urgent ? '⏳ < 5 min' : 'Temps restant'}
      </p>
    </div>
  );
}

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

