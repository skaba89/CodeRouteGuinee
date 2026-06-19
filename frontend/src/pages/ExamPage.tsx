/**
 * ExamPage — Interface d'examen CodeRoute Guinée
 * Niveau iCode / En Voiture Simone — timer bloquant, grille de navigation,
 * media illustratif, correction détaillée.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { DEMO_QUESTIONS } from './examQuestions';
import { fetchWithAuth } from '../authClient';
import { useAuthSession } from '../authSession';

const API = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/api\/v1\/?$/, '');

// ── Types ────────────────────────────────────────────────────────────────

interface ExamQuestion {
  id: string;
  number: number;
  category: string;
  text: string;
  options: string[];
  media_type?: 'image' | 'video' | 'svg' | null;
  media_url?: string | null;
  media_alt?: string | null;
  // Disponibles seulement après soumission (dans /results)
  given_answer?: string;
  correct_answer?: string;
  is_correct?: boolean;
  explanation?: string;
}

interface ExamStatus {
  attempt_id: string;
  status: string;
  remaining_seconds: number;
  elapsed_seconds: number;
  total_seconds: number;
  question_count: number;
  score?: number;
  passed?: boolean;
  expired: boolean;
}

interface ExamResult {
  attempt_id: string;
  candidate_name: string;
  score: number;
  total: number;
  score_percent: number;
  passed: boolean;
  threshold: number;
  submitted_at: string;
  questions: ExamQuestion[];
}

// ── SVG illustrations pour les questions démo ─────────────────────────────

function SignSvg({ type }: { type: string }) {
  const signs: Record<string, JSX.Element> = {
    stop: (
      <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <polygon points="60,5 105,30 115,75 90,112 30,112 5,75 15,30" fill="#c0392b" stroke="#fff" strokeWidth="4"/>
        <text x="60" y="68" textAnchor="middle" fill="#fff" fontSize="20" fontWeight="bold" fontFamily="Arial">STOP</text>
      </svg>
    ),
    priority: (
      <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <polygon points="60,5 115,115 5,115" fill="#fff" stroke="#e67e22" strokeWidth="6"/>
        <polygon points="60,22 100,100 20,100" fill="#e67e22"/>
        <circle cx="60" cy="82" r="6" fill="#fff"/>
        <rect x="56" y="42" width="8" height="28" rx="4" fill="#fff"/>
      </svg>
    ),
    no_entry: (
      <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <circle cx="60" cy="60" r="55" fill="#c0392b" stroke="#fff" strokeWidth="4"/>
        <rect x="20" y="50" width="80" height="20" rx="4" fill="#fff"/>
      </svg>
    ),
    speed_50: (
      <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <circle cx="60" cy="60" r="55" fill="#fff" stroke="#c0392b" strokeWidth="8"/>
        <text x="60" y="72" textAnchor="middle" fill="#1a1a2e" fontSize="32" fontWeight="bold" fontFamily="Arial">50</text>
      </svg>
    ),
    roundabout: (
      <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <circle cx="60" cy="60" r="55" fill="#2980b9" stroke="#fff" strokeWidth="4"/>
        <circle cx="60" cy="60" r="22" fill="none" stroke="#fff" strokeWidth="5"/>
        <path d="M38 60 Q38 38 60 38" fill="none" stroke="#fff" strokeWidth="5" markerEnd="url(#arr)"/>
        <defs><marker id="arr" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#fff"/></marker></defs>
      </svg>
    ),
    pedestrian: (
      <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <polygon points="60,5 115,115 5,115" fill="#fff" stroke="#c0392b" strokeWidth="6"/>
        <circle cx="60" cy="48" r="8" fill="#1a1a2e"/>
        <path d="M60 56 L52 80 M60 56 L68 80 M52 80 L48 96 M52 80 L60 96" stroke="#1a1a2e" strokeWidth="3" fill="none"/>
      </svg>
    ),
    give_way: (
      <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <polygon points="60,115 5,15 115,15" fill="#fff" stroke="#c0392b" strokeWidth="6"/>
        <polygon points="60,100 18,28 102,28" fill="#fff" stroke="#c0392b" strokeWidth="4"/>
      </svg>
    ),
    mandatory: (
      <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <circle cx="60" cy="60" r="55" fill="#2980b9" stroke="#fff" strokeWidth="4"/>
        <path d="M30 60 L90 60 M75 45 L90 60 L75 75" stroke="#fff" strokeWidth="8" fill="none" strokeLinecap="round"/>
      </svg>
    ),
  };
  return (
    <div style={{ width: 120, height: 120, margin: '0 auto' }}>
      {signs[type] ?? signs.priority}
    </div>
  );
}

function IntersectionSvg({ type }: { type: string }) {
  if (type === 'priority_right') {
    return (
      <svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" style={{ width: '100%', maxWidth: 320, display: 'block', margin: '0 auto' }}>
        {/* Route principale */}
        <rect x="0" y="85" width="200" height="30" fill="#555"/>
        <rect x="85" y="0" width="30" height="200" fill="#555"/>
        {/* Lignes centrales */}
        <line x1="0" y1="100" x2="80" y2="100" stroke="#f1c40f" strokeWidth="2" strokeDasharray="8,6"/>
        <line x1="120" y1="100" x2="200" y2="100" stroke="#f1c40f" strokeWidth="2" strokeDasharray="8,6"/>
        <line x1="100" y1="0" x2="100" y2="80" stroke="#f1c40f" strokeWidth="2" strokeDasharray="8,6"/>
        <line x1="100" y1="120" x2="100" y2="200" stroke="#f1c40f" strokeWidth="2" strokeDasharray="8,6"/>
        {/* Voiture A — vient de gauche */}
        <rect x="18" y="90" width="36" height="20" rx="4" fill="#3498db"/>
        <text x="36" y="104" textAnchor="middle" fill="#fff" fontSize="11" fontWeight="bold">A</text>
        {/* Flèche A → droite */}
        <path d="M56 100 L72 100" stroke="#3498db" strokeWidth="2" markerEnd="url(#arrowB)"/>
        {/* Voiture B — vient du bas (droite de A) */}
        <rect x="90" y="148" width="20" height="36" rx="4" fill="#e74c3c"/>
        <text x="100" y="170" textAnchor="middle" fill="#fff" fontSize="11" fontWeight="bold">B</text>
        {/* Flèche B → haut */}
        <path d="M100 146 L100 126" stroke="#e74c3c" strokeWidth="2" markerEnd="url(#arrowR)"/>
        <defs>
          <marker id="arrowB" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#3498db"/></marker>
          <marker id="arrowR" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#e74c3c"/></marker>
        </defs>
        <text x="100" y="192" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">B est à droite de A → B prioritaire</text>
      </svg>
    );
  }
  if (type === 'roundabout') {
    return (
      <svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" style={{ width: '100%', maxWidth: 320, display: 'block', margin: '0 auto' }}>
        <rect width="200" height="200" fill="#222"/>
        <rect x="0" y="85" width="58" height="30" fill="#555"/>
        <rect x="142" y="85" width="58" height="30" fill="#555"/>
        <rect x="85" y="0" width="30" height="58" fill="#555"/>
        <rect x="85" y="142" width="30" height="58" fill="#555"/>
        <circle cx="100" cy="100" r="46" fill="#555"/>
        <circle cx="100" cy="100" r="32" fill="#2c3e50"/>
        <circle cx="100" cy="100" r="24" fill="#27ae60"/>
        <path d="M100 54 A46 46 0 1 1 54 100" fill="none" stroke="#f1c40f" strokeWidth="3" strokeDasharray="8,5" markerEnd="url(#rArr)"/>
        <rect x="12" y="90" width="30" height="20" rx="4" fill="#e74c3c"/>
        <text x="27" y="104" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">Entre</text>
        <rect x="92" y="150" width="16" height="28" rx="3" fill="#3498db"/>
        <text x="100" y="168" textAnchor="middle" fill="#fff" fontSize="9" fontWeight="bold">GIR</text>
        <defs><marker id="rArr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#f1c40f"/></marker></defs>
      </svg>
    );
  }
  return null;
}

function SituationSvg({ type }: { type: string }) {
  if (type === 'overtake_forbidden') {
    return (
      <svg viewBox="0 0 280 160" xmlns="http://www.w3.org/2000/svg" style={{ width: '100%', maxWidth: 400, display: 'block', margin: '0 auto' }}>
        <rect width="280" height="160" fill="#1a2e1a"/>
        <rect x="0" y="70" width="280" height="60" fill="#3d3d3d"/>
        <rect x="0" y="98" width="280" height="4" fill="#fff"/>
        <rect x="0" y="68" width="280" height="4" fill="#fff"/>
        {/* Ligne continue = dépassement interdit */}
        <rect x="0" y="97" width="280" height="3" fill="#fff"/>
        {/* Virage = danger */}
        <path d="M0 130 Q140 40 280 130" stroke="#333" strokeWidth="60" fill="none"/>
        <path d="M0 130 Q140 40 280 130" stroke="#3d3d3d" strokeWidth="52" fill="none"/>
        {/* Voitures */}
        <rect x="40" y="75" width="48" height="22" rx="5" fill="#3498db"/>
        <rect x="44" y="79" width="18" height="10" rx="2" fill="#85c1e9"/>
        <rect x="104" y="75" width="48" height="22" rx="5" fill="#e74c3c"/>
        <text x="64" y="90" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">VOUS</text>
        <text x="128" y="90" textAnchor="middle" fill="#fff" fontSize="9" fontWeight="bold">CAMION</text>
        {/* Croix interdiction */}
        <circle cx="200" cy="40" r="20" fill="rgba(192,57,43,0.9)"/>
        <path d="M190 30 L210 50 M210 30 L190 50" stroke="#fff" strokeWidth="4" strokeLinecap="round"/>
        <text x="200" y="70" textAnchor="middle" fill="#fff" fontSize="11" fontWeight="bold">Interdit</text>
      </svg>
    );
  }
  if (type === 'safe_distance') {
    return (
      <svg viewBox="0 0 300 120" xmlns="http://www.w3.org/2000/svg" style={{ width: '100%', maxWidth: 420, display: 'block', margin: '0 auto' }}>
        <rect width="300" height="120" fill="#1a2e1a"/>
        <rect x="0" y="50" width="300" height="50" fill="#3d3d3d"/>
        <line x1="0" y1="75" x2="300" y2="75" stroke="#f1c40f" strokeWidth="2" strokeDasharray="10,8"/>
        <rect x="10" y="55" width="56" height="28" rx="5" fill="#3498db"/>
        <text x="38" y="73" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">VOUS</text>
        <rect x="180" y="55" width="56" height="28" rx="5" fill="#e74c3c"/>
        <text x="208" y="73" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold">DEVANT</text>
        {/* Distance */}
        <line x1="68" y1="80" x2="178" y2="80" stroke="#27ae60" strokeWidth="2"/>
        <line x1="68" y1="74" x2="68" y2="86" stroke="#27ae60" strokeWidth="2"/>
        <line x1="178" y1="74" x2="178" y2="86" stroke="#27ae60" strokeWidth="2"/>
        <text x="123" y="100" textAnchor="middle" fill="#27ae60" fontSize="11" fontWeight="bold">≥ 2 secondes</text>
        <text x="123" y="112" textAnchor="middle" fill="#aaa" fontSize="9">≈ 50 m à 90 km/h</text>
      </svg>
    );
  }
  if (type === 'emergency_vehicle') {
    return (
      <svg viewBox="0 0 280 140" xmlns="http://www.w3.org/2000/svg" style={{ width: '100%', maxWidth: 400, display: 'block', margin: '0 auto' }}>
        <rect width="280" height="140" fill="#0d1117"/>
        <rect x="0" y="60" width="280" height="50" fill="#3d3d3d"/>
        <rect x="0" y="110" width="280" height="4" fill="#fff"/>
        <rect x="0" y="58" width="280" height="4" fill="#fff"/>
        <line x1="0" y1="84" x2="280" y2="84" stroke="#f1c40f" strokeWidth="2" strokeDasharray="10,8"/>
        {/* Voitures qui se rangent */}
        <rect x="20" y="88" width="48" height="20" rx="4" fill="#3498db" opacity="0.7"/>
        <rect x="210" y="88" width="48" height="20" rx="4" fill="#2ecc71" opacity="0.7"/>
        {/* Ambulance */}
        <rect x="110" y="65" width="60" height="28" rx="5" fill="#fff"/>
        <rect x="113" y="68" width="22" height="12" rx="2" fill="#85c1e9"/>
        <text x="140" y="82" textAnchor="middle" fill="#c0392b" fontSize="11" fontWeight="bold">🚑 SAMU</text>
        {/* Gyrophare */}
        <circle cx="140" cy="63" r="5" fill="#c0392b" opacity="0.9"/>
        <circle cx="140" cy="63" r="10" fill="rgba(192,57,43,0.3)"/>
        {/* Flèches se ranger */}
        <path d="M44 84 L24 84" stroke="#3498db" strokeWidth="2" markerEnd="url(#aL)"/>
        <path d="M236 84 L256 84" stroke="#2ecc71" strokeWidth="2" markerEnd="url(#aR)"/>
        <defs>
          <marker id="aL" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#3498db"/></marker>
          <marker id="aR" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#2ecc71"/></marker>
        </defs>
        <text x="140" y="130" textAnchor="middle" fill="#f1c40f" fontSize="10" fontWeight="bold">Se dégager immédiatement → priorité absolue</text>
      </svg>
    );
  }
  return null;
}

// ── Banque de questions (données dans examQuestions.ts) ──────────────────────

function buildDemoQuestions(): ExamQuestion[] {
  return DEMO_QUESTIONS;
}

// ── Timer ────────────────────────────────────────────────────────────────

function Timer({ remainingSeconds, onExpire }: { remainingSeconds: number; onExpire: () => void }) {
  const [secs, setSecs] = useState(remainingSeconds);
  const expired = useRef(false);

  useEffect(() => {
    setSecs(remainingSeconds);
  }, [remainingSeconds]);

  useEffect(() => {
    if (secs <= 0 && !expired.current) {
      expired.current = true;
      onExpire();
      return;
    }
    const t = setTimeout(() => setSecs((s) => Math.max(0, s - 1)), 1000);
    return () => clearTimeout(t);
  }, [secs, onExpire]);

  const mins = Math.floor(secs / 60);
  const sec = secs % 60;
  const pct = remainingSeconds > 0 ? (secs / remainingSeconds) * 100 : 0;
  const urgent = secs <= 300; // < 5 min
  const critical = secs <= 60; // < 1 min

  return (
    <div className={`exam-timer ${urgent ? 'urgent' : ''} ${critical ? 'critical' : ''}`}>
      <div className="exam-timer-ring" style={{ '--pct': `${pct}%` } as React.CSSProperties}>
        <span className="exam-timer-value">
          {String(mins).padStart(2, '0')}:{String(sec).padStart(2, '0')}
        </span>
      </div>
      <p className="exam-timer-label">{critical ? '⚠️ Temps presque écoulé !' : urgent ? '⏳ Moins de 5 minutes' : 'Temps restant'}</p>
    </div>
  );
}

// ── Grille de navigation ──────────────────────────────────────────────────

function QuestionGrid({
  total,
  current,
  answers,
  onSelect,
}: {
  total: number;
  current: number;
  answers: Record<number, string>;
  onSelect: (i: number) => void;
}) {
  return (
    <div className="exam-question-grid">
      {Array.from({ length: total }, (_, i) => (
        <button
          key={i}
          type="button"
          className={[
            'exam-grid-cell',
            i === current ? 'active' : '',
            answers[i] !== undefined ? 'answered' : '',
          ].filter(Boolean).join(' ')}
          onClick={() => onSelect(i)}
          aria-label={`Question ${i + 1}${answers[i] !== undefined ? ' — répondue' : ''}`}
        >
          {i + 1}
        </button>
      ))}
    </div>
  );
}

// ── Rendu media ───────────────────────────────────────────────────────────

function QuestionMedia({ q }: { q: ExamQuestion }) {
  if (!q.media_url) return null;

  if (q.media_type === 'svg') {
    // Panneaux
    if (['stop','give_way','speed_50','no_entry','roundabout','mandatory','priority'].includes(q.media_url)) {
      return (
        <figure className="question-media-figure">
          <div className="question-media-sign">
            <SignSvg type={q.media_url} />
          </div>
          {q.media_alt && <figcaption>{q.media_alt}</figcaption>}
        </figure>
      );
    }
    // Intersections
    if (q.media_url.startsWith('intersection_')) {
      return (
        <figure className="question-media-figure">
          <div className="question-media-scene">
            <IntersectionSvg type={q.media_url.replace('intersection_', '')} />
          </div>
          {q.media_alt && <figcaption>{q.media_alt}</figcaption>}
        </figure>
      );
    }
    // Situations
    if (q.media_url.startsWith('situation_')) {
      return (
        <figure className="question-media-figure">
          <div className="question-media-scene">
            <SituationSvg type={q.media_url.replace('situation_', '')} />
          </div>
          {q.media_alt && <figcaption>{q.media_alt}</figcaption>}
        </figure>
      );
    }
  }

  if (q.media_type === 'image' && q.media_url) {
    return (
      <figure className="question-media-figure">
        <img src={q.media_url} alt={q.media_alt ?? ''} className="question-media-img" />
        {q.media_alt && <figcaption>{q.media_alt}</figcaption>}
      </figure>
    );
  }

  if (q.media_type === 'video' && q.media_url) {
    return (
      <figure className="question-media-figure">
        <video src={q.media_url} controls preload="metadata" className="question-media-video"
          aria-label={q.media_alt ?? 'Vidéo illustrative'} />
        {q.media_alt && <figcaption>{q.media_alt}</figcaption>}
      </figure>
    );
  }

  return null;
}

// ── Page de résultats ─────────────────────────────────────────────────────

function ResultsView({ result }: { result: ExamResult }) {
  const [filter, setFilter] = useState<'all' | 'wrong' | 'correct'>('all');
  const filtered = result.questions.filter((q) =>
    filter === 'all' ? true : filter === 'correct' ? q.is_correct : !q.is_correct
  );

  return (
    <div className="exam-results">
      <div className={`exam-verdict ${result.passed ? 'passed' : 'failed'}`}>
        <div className="exam-verdict-icon">{result.passed ? '🏆' : '📋'}</div>
        <h2>{result.passed ? 'Félicitations — Admis !' : 'Ajourné'}</h2>
        <p className="exam-verdict-score">{result.score} / {result.total}</p>
        <p className="exam-verdict-pct">{result.score_percent}% — Seuil : {result.threshold}/{result.total} (87,5 %)</p>
        <p className="exam-verdict-name">{result.candidate_name}</p>
      </div>

      <div className="exam-results-filters">
        {(['all','correct','wrong'] as const).map((f) => (
          <button key={f} type="button"
            className={`exam-filter-btn ${filter === f ? 'active' : ''}`}
            onClick={() => setFilter(f)}>
            {f === 'all' ? `Toutes (${result.questions.length})` :
             f === 'correct' ? `✅ Correctes (${result.questions.filter((q) => q.is_correct).length})` :
             `❌ Incorrectes (${result.questions.filter((q) => !q.is_correct).length})`}
          </button>
        ))}
      </div>

      <div className="exam-results-list">
        {filtered.map((q) => (
          <div key={q.question_id ?? q.id} className={`result-item ${q.is_correct ? 'correct' : 'wrong'}`}>
            <div className="result-item-header">
              <span className="result-num">Q{q.number}</span>
              <span className="result-cat">{q.category}</span>
              <span className="result-badge">{q.is_correct ? '✅' : '❌'}</span>
            </div>
            <p className="result-question">{q.text}</p>
            {q.given_answer && (
              <p className="result-given">Votre réponse : <strong>{q.given_answer}</strong></p>
            )}
            {!q.is_correct && q.correct_answer && (
              <p className="result-correct">Bonne réponse : <strong>{q.correct_answer}</strong></p>
            )}
            {q.explanation && (
              <p className="result-explanation">💡 {q.explanation}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Composant principal ───────────────────────────────────────────────────

const DEMO_ATTEMPT_KEY = 'coderoute-demo-attempt-id';
const EXAM_DURATION = 30 * 60; // 30 min en secondes

export function ExamPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const isAuthenticated = !isPresentationMode && currentUser !== null;

  const [phase, setPhase] = useState<'setup' | 'running' | 'expired' | 'reviewing' | 'results'>('setup');
  const [questions, setQuestions] = useState<ExamQuestion[]>(buildDemoQuestions());
  const [currentIdx, setCurrentIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState(EXAM_DURATION);
  const [bookingRef, setBookingRef] = useState('');
  const [stationCode, setStationCode] = useState('POSTE-01');
  const [statusMsg, setStatusMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ExamResult | null>(null);

  const currentQ = questions[currentIdx];
  const answeredCount = Object.keys(answers).length;

  // Charger les questions de l'API si disponibles
  useEffect(() => {
    if (!isAuthenticated || !attemptId) return;
    fetchWithAuth(`${API}/api/v1/exams/${attemptId}/questions`)
      .then((r) => r.json())
      .then((qs: ExamQuestion[]) => {
        if (Array.isArray(qs) && qs.length > 0) {
          // Enrichir les questions sans media avec une illustration par défaut
          const enriched = qs.map((q) => enrichWithMedia(q));
          setQuestions(enriched);
        }
      })
      .catch(() => {/* Garder les questions démo */});
  }, [attemptId, isAuthenticated]);

  // Polling du statut timer
  useEffect(() => {
    if (phase !== 'running' || !attemptId || !isAuthenticated) return;
    const interval = setInterval(() => {
      fetchWithAuth(`${API}/api/v1/exams/${attemptId}/status`)
        .then((r) => r.json())
        .then((s: ExamStatus) => {
          setRemainingSeconds(s.remaining_seconds);
          if (s.expired || s.status === 'expired') {
            setPhase('expired');
          }
        })
        .catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [phase, attemptId, isAuthenticated]);

  const handleTimerExpire = useCallback(() => {
    if (phase === 'running') setPhase('expired');
  }, [phase]);

  async function handleStart() {
    if (!isAuthenticated) {
      // Mode démo
      setAttemptId(`DEMO-${Date.now()}`);
      setPhase('running');
      setRemainingSeconds(EXAM_DURATION);
      setStatusMsg('Mode démonstration — examen simulé (30 min)');
      return;
    }
    if (!bookingRef.trim()) {
      setStatusMsg('Veuillez saisir une référence de réservation.');
      return;
    }
    setLoading(true);
    setStatusMsg('');
    try {
      const r = await fetchWithAuth(`${API}/api/v1/exams/start-from-booking`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          booking_reference: bookingRef.trim(),
          device_key: stationCode.trim(),
          device_label: stationCode.trim(),
        }),
      });
      if (!r.ok) {
        const err = await r.json();
        setStatusMsg(err.detail ?? 'Impossible de démarrer l\'examen.');
        return;
      }
      const attempt = await r.json();
      setAttemptId(attempt.id);
      sessionStorage.setItem(DEMO_ATTEMPT_KEY, attempt.id);
      const statusR = await fetchWithAuth(`${API}/api/v1/exams/${attempt.id}/status`);
      const status: ExamStatus = await statusR.json();
      setRemainingSeconds(status.remaining_seconds);
      setPhase('running');
      setStatusMsg('');
    } catch {
      setStatusMsg('Erreur de connexion au serveur.');
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit() {
    if (phase === 'running' && answeredCount < questions.length) {
      setPhase('reviewing');
      return;
    }
    await doSubmit();
  }

  async function doSubmit() {
    const payload: Record<string, string> = {};
    questions.forEach((q, i) => {
      if (answers[i] !== undefined) payload[q.id] = answers[i];
    });

    if (!isAuthenticated || !attemptId || attemptId.startsWith('DEMO-')) {
      // Résultats démo
      const score = Object.values(payload).filter((_, i) => payload[questions[i]?.id] === questions[i]?.correct_answer).length;
      const demoResult: ExamResult = {
        attempt_id: attemptId ?? 'DEMO',
        candidate_name: currentUser?.full_name ?? 'Candidat',
        score,
        total: questions.length,
        score_percent: Math.round((score / questions.length) * 100 * 10) / 10,
        passed: score >= 35,
        threshold: 35,
        submitted_at: new Date().toISOString(),
        questions: questions.map((q, i) => ({
          ...q,
          given_answer: answers[i],
          is_correct: answers[i] === q.correct_answer,
        })),
      };
      setResult(demoResult);
      setPhase('results');
      return;
    }

    setLoading(true);
    try {
      const r = await fetchWithAuth(`${API}/api/v1/exams/${attemptId}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers: payload }),
      });
      if (!r.ok) {
        const err = await r.json();
        setStatusMsg(err.detail ?? 'Erreur lors de la soumission.');
        return;
      }
      // Charger les résultats détaillés
      const resR = await fetchWithAuth(`${API}/api/v1/exams/${attemptId}/results`);
      const res: ExamResult = await resR.json();
      setResult(res);
      setPhase('results');
    } catch {
      setStatusMsg('Erreur lors de la soumission.');
    } finally {
      setLoading(false);
    }
  }

  function selectAnswer(option: string) {
    setAnswers((prev) => ({ ...prev, [currentIdx]: option }));
  }

  // ── Rendu phase setup ────────────────────────────────────────────────

  if (phase === 'setup') {
    return (
      <section className="screen exam-screen">
        <div className="exam-setup-card">
          <div className="exam-setup-header">
            <span className="eyebrow">Examen officiel</span>
            <h2>Code de la route — Catégorie B</h2>
            <p>40 questions · 30 minutes · Seuil d'admission : 35/40 (87,5 %)</p>
          </div>
          <div className="exam-setup-rules">
            <div className="rule-item"><span>📋</span><span>40 questions illustrées</span></div>
            <div className="rule-item"><span>⏱️</span><span>30 minutes chronométrées</span></div>
            <div className="rule-item"><span>✅</span><span>35 bonnes réponses requises</span></div>
            <div className="rule-item"><span>🔒</span><span>Navigation libre entre questions</span></div>
            <div className="rule-item"><span>🎯</span><span>Résultats détaillés à la fin</span></div>
          </div>

          {isAuthenticated ? (
            <div className="exam-setup-fields">
              <label>
                Référence de réservation
                <input value={bookingRef} onChange={(e) => setBookingRef(e.target.value)}
                  placeholder="GN-BOOK-..." />
              </label>
              <label>
                Code du poste
                <input value={stationCode} onChange={(e) => setStationCode(e.target.value)}
                  placeholder="POSTE-01" />
              </label>
            </div>
          ) : (
            <p className="exam-demo-notice">
              🎓 Mode démonstration — 40 questions illustrées disponibles sans connexion
            </p>
          )}

          {statusMsg && <p className="form-error">{statusMsg}</p>}

          <button className="exam-start-btn" onClick={handleStart} disabled={loading}>
            {loading ? 'Démarrage...' : isAuthenticated ? '🚀 Démarrer l\'examen officiel' : '🎓 Commencer la démonstration'}
          </button>
        </div>
      </section>
    );
  }

  // ── Rendu phase reviewing (avant soumission) ──────────────────────────

  if (phase === 'reviewing') {
    const unanswered = questions.filter((_, i) => answers[i] === undefined);
    return (
      <section className="screen exam-screen">
        <div className="exam-review-card">
          <h2>Vérification avant soumission</h2>
          <p>Vous avez répondu à <strong>{answeredCount}</strong> question(s) sur {questions.length}.</p>
          {unanswered.length > 0 && (
            <div className="exam-unanswered-list">
              <p className="warning-text">⚠️ Questions sans réponse :</p>
              {unanswered.map((q) => (
                <button key={q.id} type="button" className="unanswered-btn"
                  onClick={() => { setCurrentIdx(q.number - 1); setPhase('running'); }}>
                  Question {q.number} — {q.category}
                </button>
              ))}
            </div>
          )}
          <div className="review-actions">
            <button className="secondary-button" onClick={() => setPhase('running')}>↩ Revenir à l'examen</button>
            <button className="exam-submit-final" onClick={doSubmit} disabled={loading}>
              {loading ? 'Soumission...' : '✅ Soumettre définitivement'}
            </button>
          </div>
        </div>
      </section>
    );
  }

  // ── Rendu phase expired ───────────────────────────────────────────────

  if (phase === 'expired') {
    return (
      <section className="screen exam-screen">
        <div className="exam-expired-card">
          <p className="exam-expired-icon">⏰</p>
          <h2>Temps écoulé</h2>
          <p>Le temps de 30 minutes est écoulé. Vos réponses vont être soumises automatiquement.</p>
          <button onClick={doSubmit} disabled={loading}>
            {loading ? 'Soumission...' : 'Voir mes résultats'}
          </button>
        </div>
      </section>
    );
  }

  // ── Rendu phase results ───────────────────────────────────────────────

  if (phase === 'results' && result) {
    return (
      <section className="screen exam-screen">
        <ResultsView result={result} />
      </section>
    );
  }

  // ── Rendu phase running ───────────────────────────────────────────────

  if (!currentQ) return null;

  return (
    <section className="screen exam-screen exam-screen--running">
      {/* Sidebar gauche : timer + grille */}
      <aside className="exam-sidebar">
        <Timer remainingSeconds={remainingSeconds} onExpire={handleTimerExpire} />

        <div className="exam-sidebar-info">
          <p><strong>{answeredCount}</strong> / {questions.length} répondues</p>
          <p>Seuil : 35/40</p>
        </div>

        <QuestionGrid
          total={questions.length}
          current={currentIdx}
          answers={answers}
          onSelect={setCurrentIdx}
        />

        <button className="exam-submit-btn" onClick={handleSubmit} disabled={loading}>
          {loading ? 'En cours...' : answeredCount < questions.length
            ? `Vérifier (${questions.length - answeredCount} sans réponse)`
            : '✅ Soumettre l\'examen'}
        </button>

        {statusMsg && <p className="form-error" style={{ fontSize: 12 }}>{statusMsg}</p>}
      </aside>

      {/* Zone principale : question */}
      <main className="exam-main">
        <div className="exam-main-header">
          <span className="exam-q-cat">{currentQ.category}</span>
          <span className="exam-q-num">Question {currentIdx + 1} / {questions.length}</span>
        </div>

        {/* Barre de progression */}
        <div className="exam-progress-bar">
          <div className="exam-progress-fill" style={{ width: `${((currentIdx + 1) / questions.length) * 100}%` }} />
        </div>

        {/* Media illustratif */}
        <QuestionMedia q={currentQ} />

        {/* Texte de la question */}
        <p className="exam-question-text">{currentQ.text}</p>

        {/* Options */}
        <div className="exam-options">
          {currentQ.options.map((opt, oi) => (
            <button
              key={oi}
              type="button"
              className={`exam-option ${answers[currentIdx] === opt ? 'selected' : ''}`}
              onClick={() => selectAnswer(opt)}
            >
              <span className="exam-option-letter">{String.fromCharCode(65 + oi)}</span>
              <span className="exam-option-text">{opt}</span>
              {answers[currentIdx] === opt && <span className="exam-option-check">✓</span>}
            </button>
          ))}
        </div>

        {/* Navigation */}
        <div className="exam-nav">
          <button
            className="secondary-button"
            disabled={currentIdx === 0}
            onClick={() => setCurrentIdx((i) => Math.max(0, i - 1))}
          >
            ← Précédente
          </button>
          <span className="exam-nav-skip">
            {answers[currentIdx] === undefined ? (
              <button className="exam-skip-btn"
                onClick={() => setCurrentIdx((i) => Math.min(questions.length - 1, i + 1))}>
                Passer →
              </button>
            ) : null}
          </span>
          <button
            disabled={currentIdx === questions.length - 1}
            onClick={() => setCurrentIdx((i) => Math.min(questions.length - 1, i + 1))}
          >
            Suivante →
          </button>
        </div>
      </main>
    </section>
  );
}

// ── Enrichissement automatique des questions API sans media ────────────────

function enrichWithMedia(q: ExamQuestion): ExamQuestion {
  if (q.media_url) return q;
  const cat = q.category.toLowerCase();
  if (cat.includes('signal')) return { ...q, media_type: 'svg', media_url: 'priority', media_alt: 'Illustration signalisation' };
  if (cat.includes('priorit')) return { ...q, media_type: 'svg', media_url: 'intersection_priority_right', media_alt: 'Situation de priorité' };
  if (cat.includes('girat') || cat.includes('rondpoint')) return { ...q, media_type: 'svg', media_url: 'intersection_roundabout', media_alt: 'Giratoire' };
  if (cat.includes('vitesse') || cat.includes('distance')) return { ...q, media_type: 'svg', media_url: 'situation_safe_distance', media_alt: 'Distance de sécurité' };
  if (cat.includes('dépasse') || cat.includes('manoeuv')) return { ...q, media_type: 'svg', media_url: 'situation_overtake_forbidden', media_alt: 'Situation de dépassement' };
  if (cat.includes('urgence') || cat.includes('secours')) return { ...q, media_type: 'svg', media_url: 'situation_emergency_vehicle', media_alt: 'Véhicule d\'urgence' };
  return q;
}
