// TrainingPage — CodeRoute Guinée
import { type FormEvent, useEffect, useRef, useCallback, useState } from 'react';
import { AudioModeBanner, LocaleAudioSwitcher, PlayButton, AudioToggle } from '../components/AudioButton';
import {
  InstitutionalAuthsPanel,
  DeviceAlertsPanel,
  CenterManagementPanel,
  QuestionsAdminPanel,
  CandidateIdentityForm,
  CandidateRecourseForm,
  CertificatePdfButton,
  CsvExportsPanel,
  OfficialPaymentsImportPanel,
} from '../components/AdminExtras';
import { Pagination, SearchBar, PaginationBar, PageSizeSelector } from '../components/Pagination';
import {
  type CandidateFilters,
  type CenterFilters,
  type QuestionFilters,
  type UserFilters,
} from '../api';
import { isAudioLocale, speakFeedback, stop as stopAudio } from '../audio';
import { type Locale } from '../i18n';
import { type AuthUser } from '../authClient';
import { type UserRole } from '../auth';
import { useAuthSession, canUseProtectedActions } from '../authSession';
import {
  type Center, type Candidate, type DashboardData, type ExamSummary,
  type EntrySummary, type ExamAttempt, type EntryValidationResult,
  type PaymentResult, type PaymentFilters, type AuditLogEntry, type AuditLogFilters,
  type CenterIncident, type InstitutionalUser, type InstitutionalUserCreatePayload,
  type ExamCertificateVerification, type ExamDetailedResult, type ExamLiveStatus,
  type CandidateIdentityCheck, type CandidateSubmission,
  type ExamMonitoringSummary, type ExamMonitoringEvent, type ExamMonitoringFilters,
  type QuestionGovernanceItem,
  getDashboard, getCandidates, getCenters, getExamSummary, getEntrySummary,
  getAuditLogs, getAdminPaymentSummary, getPaymentReconciliationItems,
  getInstitutionalUsers, createInstitutionalUser,
  updateInstitutionalUserRole, updateInstitutionalUserStatus,
  resetInstitutionalUserPassword,
  validateEntry, reportCenterIncident, getCenterIncidents, resolveCenterIncident,
  createPayment, getConvocationPdfUrl, verifyExamCertificate,
  downloadExamCertificatePdf, getExamResults,
  startExamFromBooking, submitExamAttempt, getExamLiveStatus,
  getCandidateIdentityChecks, getCandidateSubmissions,
  getExamMonitoringSummaries, getExamMonitoringEvents,
  getQuestionGovernanceItems, decideQuestionGovernance,
  getPaymentAlerts, getInstitutionalReport, downloadInstitutionalReportPdf,
  downloadDashboardCsv, downloadAuditLogsCsv, downloadExamAttemptsCsv,
  downloadAdminPaymentsCsv, decideCandidateIdentity, handleCandidateSubmission,
  type OperationsSummary,
  type InstitutionalReadiness,
  type InstitutionalActionCenter,
  type InstitutionalActionItem,
  type CenterStation,
  getOperationsSummary,
  getInstitutionalReadiness,
  getInstitutionalActionCenter,
  downloadInstitutionalReportCsv,
  importOfficialCandidates,
  importOfficialCenters,
  importOfficialQuestions,
  getCenterStations,
  createCenterStation,
  getExamCertificatePdfUrl,
} from '../api';
import { DEMO_QUESTIONS } from '../pages/examQuestions';

// ── Helpers ───────────────────────────────────────────────────────
function fmt(n: number) { return n.toLocaleString('fr-FR'); }
function fmtGNF(n: number) { return `${fmt(n)} GNF`; }
function fmtDate(s: string) { return new Date(s).toLocaleDateString('fr-FR'); }
function errMsg(e: unknown, fallback = 'Erreur inattendue'): string {
  if (e instanceof Error) return e.message;
  if (typeof e === 'object' && e !== null && 'detail' in e) return String((e as { detail: unknown }).detail);
  return fallback;
}

// ══════════════════════════════════════════════════════════════════
// HOME PAGE — Accueil toutes rôles
// ══════════════════════════════════════════════════════════════════

export function TrainingPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const canUseApi = canUseProtectedActions(currentUser, isPresentationMode, ['candidate','admin','super_admin','driving_school']);

  type TrainingQ = {
    index: number; category: string; category_label: string;
    text: string; options: string[];
    correct_answer: string; explanation: string;
  };

  const CATS = [
    { id: '', label: 'Toutes les catégories', icon: '📚' },
    { id: 'signalisation',    label: 'Signalisation',          icon: '🚦' },
    { id: 'priorites',        label: 'Priorités',              icon: '⭐' },
    { id: 'vitesse',          label: 'Vitesse & Distances',    icon: '⏱️' },
    { id: 'depassement',      label: 'Dépassement',            icon: '↔️' },
    { id: 'securite_passive', label: 'Sécurité passive',       icon: '🛡️' },
    { id: 'urgence',          label: 'Situations d\'urgence',  icon: '🚨' },
    { id: 'alcool_drogues',   label: 'Alcool & Drogues',       icon: '🚫' },
    { id: 'premiers_secours', label: 'Premiers secours',       icon: '🩺' },
  ];

  const [mode, setMode] = useState<'menu'|'training'|'done'>('menu');
  const [cat, setCat] = useState('');
  const [questions, setQuestions] = useState<TrainingQ[]>([]);
  const [qi, setQi] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [stats, setStats] = useState<{ total: number; correct: number; bycat: Record<string,{ok:number;total:number}> }>({ total: 0, correct: 0, bycat: {} });

  // Charger les questions via l'API training
  async function startSession() {
    setLoading(true);
    try {
      const url = `/api/v1/training/questions?limit=20&shuffle=true${cat ? `&category=${cat}` : ''}`;
      let qs: TrainingQ[] = [];
      if (canUseApi) {
        const r = await fetch(url, { headers: { 'Authorization': `Bearer ${localStorage.getItem('cr-access-token') ?? ''}` } });
        if (r.ok) qs = await r.json();
      }
      if (qs.length === 0) {
        // Fallback local depuis les données DEMO_QUESTIONS
        qs = DEMO_QUESTIONS
          .filter(q => !cat || q.category === cat)
          .sort(() => Math.random() - .5).slice(0, 20)
          .map((q, i) => ({
            index: i, category: q.category, category_label: q.category,
            text: q.text, options: q.options,
            correct_answer: q.correct_answer, explanation: q.explanation ?? '',
          }));
      }
      setQuestions(qs); setQi(0); setAnswers({}); setRevealed(false);
      setMode('training');
    } finally { setLoading(false); }
  }

  function pickAnswer(opt: string) {
    if (revealed) return;
    setAnswers(a => ({ ...a, [qi]: opt }));
    setRevealed(true);
    // Feedback audio : correct ou incorrect (avec explication pour les mauvaises réponses)
    const isCorrect = opt === questions[qi]?.correct_answer;
    const expl = questions[qi]?.explanation ?? '';
    speakFeedback(isCorrect, expl);
  }

  function next() {
    setRevealed(false);
    if (qi < questions.length - 1) setQi(i => i + 1);
    else {
      // Calculer les stats
      const correct = questions.filter((q, i) => answers[i] === q.correct_answer).length;
      const bycat: Record<string,{ok:number;total:number}> = {};
      questions.forEach((q, i) => {
        if (!bycat[q.category]) bycat[q.category] = { ok: 0, total: 0 };
        bycat[q.category].total++;
        if (answers[i] === q.correct_answer) bycat[q.category].ok++;
      });
      setStats({ total: questions.length, correct, bycat });
      setMode('done');
    }
  }

  const q = questions[qi];

  // ── Menu ──────────────────────────────────────────────────────
  if (mode === 'menu') return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div className="page-header">
        <span className="eyebrow">Module Entraînement</span>
        <h1>Préparez-vous à l'examen</h1>
        <p>200 questions en banque. L'examen officiel en tire 40 aléatoirement — entraînez-vous sur toutes les catégories.</p>
      </div>

      <div style={{ maxWidth: 700 }}>
        <AudioModeBanner />
        {/* Sélecteur de catégorie */}
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header"><span className="card-title">🎯 Choisissez une catégorie</span></div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(180px,1fr))', gap: 8 }}>
            {CATS.map(c => (
              <button key={c.id} type="button"
                className={cat === c.id ? 'btn-primary btn-sm' : 'secondary-button btn-sm'}
                style={{ justifyContent: 'flex-start', gap: 8 }}
                onClick={() => setCat(c.id)}>
                <span>{c.icon}</span> <span>{c.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Options */}
        <div className="g2">
          <div className="card">
            <div className="card-header"><span className="card-title">📖 Mode entraînement libre</span></div>
            <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 14, display: 'grid', gap: 6 }}>
              <div>✅ Réponse correcte affichée immédiatement</div>
              <div>💡 Explication pédagogique après chaque question</div>
              <div>📊 Statistiques par catégorie en fin de session</div>
              <div>🔄 20 questions tirées aléatoirement</div>
            </div>
            <button className="btn-success btn-block btn-lg" onClick={startSession} disabled={loading}>
              {loading ? 'Chargement…' : '🚀 Démarrer l\'entraînement'}
            </button>
          </div>

          <div className="card">
            <div className="card-header"><span className="card-title">📊 Statistiques globales</span></div>
            <div style={{ display: 'grid', gap: 10 }}>
              {CATS.slice(1).map(c => (
                <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
                  <span style={{ width: 24 }}>{c.icon}</span>
                  <span style={{ flex: 1, color: 'var(--ink2)' }}>{c.label}</span>
                  <span className="badge bb">
                    {DEMO_QUESTIONS.filter(q => q.category === c.id).length} Q
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );

  // ── Résultats entraînement ────────────────────────────────────
  if (mode === 'done') {
    const pct = Math.round(stats.correct / stats.total * 100);
    const weak = Object.entries(stats.bycat)
      .filter(([, v]) => v.ok / v.total < .7)
      .sort(([, a], [, b]) => (a.ok/a.total) - (b.ok/b.total));
    return (
      <section className="screen" role="main" aria-label="Contenu principal">
        <div style={{ maxWidth: 640, margin: '0 auto', display: 'grid', gap: 16 }}>
          <div style={{ background: `linear-gradient(135deg,${pct>=70?'var(--green)':'var(--navy)'},${pct>=70?'#006b47':'var(--navy2)'})`, borderRadius: 20, padding: '24px 28px', color: '#fff', textAlign: 'center' }}>
            <div style={{ fontSize: 44 }}>{pct >= 80 ? '🏆' : pct >= 60 ? '📈' : '📚'}</div>
            <h2 style={{ color: '#fff', fontSize: 22, margin: '8px 0 4px' }}>
              {pct >= 80 ? 'Excellent !' : pct >= 60 ? 'En progrès' : 'Continuez à réviser'}
            </h2>
            <div style={{ fontSize: 38, fontWeight: 900 }}>{stats.correct}<span style={{ fontSize: 18, opacity: .7 }}>/{stats.total}</span></div>
            <div style={{ fontSize: 14, opacity: .8 }}>{pct} % de bonnes réponses</div>
          </div>

          {weak.length > 0 && (
            <div className="card">
              <div className="card-header"><span className="card-title">⚠️ Points à améliorer</span></div>
              {weak.map(([cat, v]) => (
                <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
                  <span style={{ flex: 1, fontSize: 13 }}>{CATS.find(c=>c.id===cat)?.icon} {CATS.find(c=>c.id===cat)?.label ?? cat}</span>
                  <span className="badge br">{v.ok}/{v.total}</span>
                </div>
              ))}
              <div style={{ marginTop: 14 }}>
                <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 10 }}>
                  Révisez les catégories faibles pour améliorer votre score.
                </p>
                <div className="actions">
                  {weak.slice(0,3).map(([c]) => (
                    <button key={c} type="button" className="secondary-button btn-sm"
                      onClick={() => { setCat(c); setMode('menu'); }}>
                      Retravailler {CATS.find(x=>x.id===c)?.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="actions">
            <button className="btn-success" onClick={() => { setMode('menu'); setQi(0); setAnswers({}); }}>🔄 Nouvelle session</button>
            <a href="#/exam"><button className="btn-primary">🎓 Passer l'examen officiel →</button></a>
          </div>
        </div>
      </section>
    );
  }

  // ── Question en cours ─────────────────────────────────────────
  const isCorrect = answers[qi] === q.correct_answer;
  return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div style={{ maxWidth: 680, margin: '0 auto' }}>
        {/* Progression */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12, fontSize: 13, color: 'var(--muted)' }}>
          <span>{CATS.find(c=>c.id===q.category)?.icon} {q.category_label}</span>
          <span style={{ fontWeight: 700, color: 'var(--ink)' }}>{qi+1} / {questions.length}</span>
        </div>
        <div style={{ height: 6, background: 'var(--border)', borderRadius: 99, marginBottom: 20, overflow: 'hidden' }}>
          <div style={{ height: '100%', background: `linear-gradient(90deg,var(--blue),var(--green))`, width: `${(qi+1)/questions.length*100}%`, borderRadius: 'inherit', transition: 'width .3s' }} />
        </div>

        {/* Question */}
        <div className="card" style={{ marginBottom: 14 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 18 }}>
            <p style={{ fontSize: 17, fontWeight: 700, color: 'var(--ink)', lineHeight: 1.5, flex: 1, margin: 0 }}>{q.text}</p>
            <PlayButton text={q.text} options={q.options} size={40} />
          </div>

          <div style={{ display: 'grid', gap: 9 }}>
            {q.options.map((opt, i) => {
              let bg = 'var(--bg)', border = 'var(--border)', clr = 'var(--ink2)';
              if (revealed) {
                if (opt === q.correct_answer) { bg = 'var(--green-l)'; border = '#86efac'; clr = '#166534'; }
                else if (answers[qi] === opt) { bg = 'var(--red-l)'; border = '#fca5a5'; clr = 'var(--red)'; }
              } else if (answers[qi] === opt) {
                bg = 'var(--blue-l)'; border = 'var(--blue)'; clr = 'var(--blue)';
              }
              return (
                <button key={i} type="button" onClick={() => pickAnswer(opt)}
                  style={{ display:'flex', alignItems:'center', gap:10, padding:'12px 14px', border:`2px solid ${border}`, borderRadius:'var(--r-lg)', background:bg, cursor:'pointer', textAlign:'left', width:'100%', color:clr, fontSize:13, fontWeight:500, minHeight:'unset', transition:'all .15s' }}>
                  <span style={{ width:26, height:26, borderRadius:7, background: revealed ? (opt===q.correct_answer ? 'var(--green)' : answers[qi]===opt ? 'var(--red)' : '#e2e8f0') : (answers[qi]===opt ? 'var(--blue)' : '#e2e8f0'), color: revealed || answers[qi]===opt ? '#fff' : 'var(--muted)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:12, fontWeight:900, flexShrink:0 }}>
                    {String.fromCharCode(65+i)}
                  </span>
                  {opt}
                  {revealed && opt === q.correct_answer && <span style={{ marginLeft:'auto', fontWeight:900 }}>✓</span>}
                  {revealed && opt !== q.correct_answer && answers[qi] === opt && <span style={{ marginLeft:'auto', fontWeight:900 }}>✗</span>}
                </button>
              );
            })}
          </div>

          {/* Explication immédiate */}
          {revealed && q.explanation && (
            <div style={{ marginTop:16, background: isCorrect ? 'var(--green-l)' : 'var(--blue-l)', border:`1px solid ${isCorrect ? '#86efac' : '#bfdbfe'}`, borderRadius:'var(--r)', padding:'12px 14px', fontSize:13 }}>
              <div style={{ fontWeight:700, marginBottom:4, color: isCorrect ? '#166534' : 'var(--blue)' }}>
                {isCorrect ? '✅ Bonne réponse !' : '💡 Explication'}
              </div>
              <div style={{ color: 'var(--ink2)', lineHeight:1.5 }}>{q.explanation}</div>
            </div>
          )}
        </div>

        {/* Navigation */}
        {revealed && (
          <button className="btn-success btn-block btn-lg" onClick={next}>
            {qi < questions.length - 1 ? 'Question suivante →' : '📊 Voir mes résultats'}
          </button>
        )}
        {!revealed && (
          <div style={{ textAlign:'center', fontSize:13, color:'var(--muted)' }}>
            Sélectionnez une réponse pour voir l'explication
          </div>
        )}
      </div>
    </section>
  );
}

// ══════════════════════════════════════════════════════════════════
// DRIVING SCHOOL PAGE — Portail auto-école (Mois 10–12)
// ══════════════════════════════════════════════════════════════════
