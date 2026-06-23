// ExamPage — CodeRoute Guinée
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
  startExamFromBooking, submitExamAttempt, getExamLiveStatus, getExamQuestions,
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
import { DEMO_QUESTIONS } from './examQuestions';

// ── Helpers ───────────────────────────────────────────────────────
function fmt(n: number) { return n.toLocaleString('fr-FR'); }
function fmtGNF(n: number) { return `${fmt(n)} GNF`; }
function fmtDate(s: string) { return new Date(s).toLocaleDateString('fr-FR'); }
function errMsg(e: unknown, fallback = 'Erreur inattendue'): string {
  if (e instanceof Error) return e.message;
  if (typeof e === 'object' && e !== null && 'detail' in e) return String((e as { detail: unknown }).detail);
  return fallback;
}
import { ExamQuestion } from '../api';
import { QData, Timer, QGrid, SignSvg, SceneSvg } from './shared-exam-components';

// ══════════════════════════════════════════════════════════════════
// HOME PAGE — Accueil toutes rôles
// ══════════════════════════════════════════════════════════════════

export function ExamPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const isAuth = !isPresentationMode && currentUser !== null;
  const SECS = 30 * 60;

  const [phase, setPhase] = useState<'setup'|'running'|'review'|'done'>('setup');
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<number,string>>({});
  const [bookRef, setBookRef] = useState('');
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [liveQuestions, setLiveQuestions] = useState<ExamQuestion[] | null>(null);
  const [result, setResult] = useState<ExamDetailedResult | null>(null);
  const [filter, setFilter] = useState<'all'|'ok'|'ko'>('all');
  const [reveal, setReveal] = useState(false);
  const [startErr, setStartErr] = useState('');

  // eslint-disable-next-line @typescript-eslint/no-use-before-define
  // Utiliser les questions du backend si disponibles, sinon fallback local
  const questions: QData[] = (liveQuestions ?? []).length > 0
    ? (liveQuestions!).map((q, i) => ({
        id: q.id, number: q.number, category: q.category, text: q.text,
        options: q.options, correct: undefined,  // réponse correcte masquée
        media: q.media_url ?? undefined,
        mediaType: q.media_type as 'sign' | 'scene' | undefined,
        expl: '',
      }))
    : DEMO_QUESTIONS.map((q: import('./examQuestions').ExamQuestionData) => ({
        id: q.id, number: q.number, category: q.category, text: q.text,
        options: q.options, correct: q.correct_answer,
        media: q.media_url ?? undefined,
        mediaType: q.media_url ? (q.media_url.startsWith('intersection') || q.media_url.startsWith('situation') ? 'scene' : 'sign') : undefined,
        expl: q.explanation ?? '',
      }));


  const q = questions[idx];
  const answered = Object.keys(answers).length;
  const handleExpire = useCallback(() => setPhase('done'), []);

  function pick(opt: string) {
    setAnswers(a => ({ ...a, [idx]: opt }));
    if (!reveal) { setReveal(true); setTimeout(() => { setReveal(false); if (idx < questions.length - 1) setIdx(i => i + 1); }, 1200); }
  }

  async function submitExam() {
    // Si examen réel (avec attemptId), soumettre au backend
    if (attemptId && isAuth && liveQuestions) {
      try {
        const answersById: Record<string, string> = {};
        questions.forEach((q, i) => { if (answers[i]) answersById[q.id] = answers[i]; });
        const attempt = await submitExamAttempt(attemptId, answersById);
        setResult({
          attempt_id: attempt.id,
          candidate_name: currentUser?.full_name ?? 'Candidat',
          score: attempt.score ?? 0,
          total: questions.length,
          score_percent: attempt.score ? Math.round(attempt.score / questions.length * 1000) / 10 : 0,
          passed: attempt.passed ?? false,
          threshold: 35,
          submitted_at: attempt.submitted_at ?? new Date().toISOString(),
          questions: [],
        });
        setPhase('done');
        return;
      } catch { /* fallback au calcul local */ }
    }
    // Calcul local pour la démo
    const score = questions.filter((q2, i) => answers[i] === q2.correct).length;
    const passed = score >= 35;
    const fakeResult: ExamDetailedResult = {
      attempt_id: 'DEMO',
      candidate_name: currentUser?.full_name ?? 'Candidat',
      score, total: questions.length,
      score_percent: Math.round(score / questions.length * 1000) / 10,
      passed, threshold: 35,
      submitted_at: new Date().toISOString(),
      questions: questions.map((q2, i) => ({
        number: q2.number ?? 0,
        question_id: q2.id,
        category: q2.category ?? '',
        text: q2.text,
        options: q2.options,
        given_answer: answers[i] ?? null,
        correct_answer: q2.correct ?? q2.correct_answer ?? '',
        is_correct: answers[i] === (q2.correct ?? q2.correct_answer),
        explanation: q2.expl ?? q2.explanation ?? '',
      })),
    };
    setResult(fakeResult);
    setPhase('done');
  }

  // ── Setup ──────────────────────────────────────────────────────
  if (phase === 'setup') return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div style={{ maxWidth: 520, margin: '0 auto' }}>
        <AudioModeBanner />
        <div style={{ background: 'linear-gradient(135deg,var(--navy),var(--navy2))', borderRadius: 20, padding: 28, color: '#fff', marginBottom: 20, textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 8 }}>🇬🇳</div>
          <h2 style={{ color: '#fff', fontSize: 22 }}>Code de la route — Catégorie B</h2>
          <p style={{ color: 'rgba(255,255,255,.7)', marginTop: 6, fontSize: 13 }}>40 questions • 30 minutes • Seuil 35/40</p>
        </div>
        <div className="card">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 18 }}>
            {[['📋','40 questions illustrées'],['⏱','30 minutes'],['✅','Seuil : 35/40'],['🎯','Résultats détaillés']].map(([icon,label]) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', background: 'var(--bg)', borderRadius: 'var(--r)', fontSize: 13, fontWeight: 500 }}>
                <span>{icon}</span><span>{label}</span>
              </div>
            ))}
          </div>
          {isAuth && (
            <label style={{ marginBottom: 14 }}>
              Référence de réservation (optionnel)
              <input value={bookRef} onChange={e => setBookRef(e.target.value)} placeholder="GN-CONV-2026-000001" />
            </label>
          )}
          <button className="btn-success btn-block btn-lg" onClick={() => setPhase('running')}>
            🚀 {isAuth ? 'Démarrer l\'examen officiel' : 'Commencer la démonstration'}
          </button>
        </div>
      </div>
    </section>
  );

  // ── Done / Results ─────────────────────────────────────────────
  if (phase === 'done' && result) {
    const filtered = result.questions.filter(q2 =>
      filter === 'all' ? true : filter === 'ok' ? q2.is_correct : !q2.is_correct
    );
    return (
      <section className="screen" role="main" aria-label="Contenu principal">
        <div style={{ maxWidth: 720, margin: '0 auto', display: 'grid', gap: 18 }}>
          <div style={{ background: `linear-gradient(135deg,${result.passed ? 'var(--green)' : 'var(--navy)'},${result.passed ? '#006b47' : 'var(--navy2)'})`, borderRadius: 20, padding: 28, color: '#fff', textAlign: 'center' }}>
            <div style={{ fontSize: 48 }}>{result.passed ? '🏆' : '📋'}</div>
            <h2 style={{ color: '#fff', fontSize: 24, margin: '8px 0 4px' }}>{result.passed ? 'Félicitations — Admis !' : 'Ajourné'}</h2>
            <div style={{ fontSize: 40, fontWeight: 900 }}>{result.score} <span style={{ fontSize: 20, fontWeight: 500, opacity: .8 }}>/ {result.total}</span></div>
            <div style={{ fontSize: 14, opacity: .8 }}>{result.score_percent}% — Seuil : {result.threshold}/{result.total}</div>
            <div style={{ fontSize: 13, opacity: .65, marginTop: 4 }}>{result.candidate_name}</div>
          </div>

          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {(['all','ok','ko'] as const).map(f => (
              <button key={f} type="button"
                className={filter === f ? 'btn-primary btn-sm' : 'secondary-button btn-sm'}
                onClick={() => setFilter(f)}>
                {f === 'all' ? `Toutes (${result.questions.length})`
                  : f === 'ok' ? `✅ Correctes (${result.questions.filter(q2 => q2.is_correct).length})`
                  : `❌ Incorrectes (${result.questions.filter(q2 => !q2.is_correct).length})`}
              </button>
            ))}
            <button className="secondary-button btn-sm" onClick={() => { setAnswers({}); setIdx(0); setPhase('setup'); setResult(null); }}>
              🔄 Recommencer
            </button>
          </div>

          {filtered.map(q2 => (
            <div key={q2.question_id} style={{ background: '#fff', border: `1.5px solid ${q2.is_correct ? '#86efac' : '#fca5a5'}`, borderRadius: 'var(--r-lg)', padding: '14px 18px', display: 'grid', gap: 7 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ background: 'var(--bg)', padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700 }}>Q{q2.number}</span>
                <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--muted)', flex: 1 }}>{q2.category}</span>
                <span>{q2.is_correct ? '✅' : '❌'}</span>
              </div>
              <p style={{ fontWeight: 600, fontSize: 13, color: 'var(--ink)', margin: 0 }}>{q2.text}</p>
              {!q2.is_correct && q2.given_answer && <p style={{ fontSize: 12, color: '#D32F2F', margin: 0 }}>Votre réponse : <strong>{q2.given_answer}</strong></p>}
              {!q2.is_correct && <p style={{ fontSize: 12, color: 'var(--green)', margin: 0 }}>Bonne réponse : <strong>{q2.correct_answer}</strong></p>}
              {q2.explanation && <p style={{ fontSize: 12, color: 'var(--muted)', background: 'var(--bg)', padding: '6px 10px', borderRadius: 8, margin: 0 }}>💡 {q2.explanation}</p>}
            </div>
          ))}
        </div>
      </section>
    );
  }

  // ── Running ────────────────────────────────────────────────────
  if (phase === 'review') {
    const unanswered = questions.filter((_, i) => answers[i] === undefined);
    return (
      <section className="screen" role="main" aria-label="Contenu principal">
        <div style={{ maxWidth: 520, margin: '0 auto' }} className="card">
          <h2 style={{ marginBottom: 12 }}>Vérification avant soumission</h2>
          <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 16 }}>
            {answered}/{questions.length} questions répondues.
          </p>
          {unanswered.length > 0 && (
            <div style={{ display: 'grid', gap: 6, marginBottom: 16 }}>
              <p style={{ fontSize: 12, fontWeight: 700, color: 'var(--gold)' }}>Questions sans réponse :</p>
              {unanswered.map(q2 => (
                <button key={q2.id} type="button" className="secondary-button btn-sm" style={{ justifyContent: 'flex-start' }}
                  onClick={() => { setIdx((q2.number ?? 0) - 1); setPhase('running'); }}>
                  Q{q2.number} — {q2.category}
                </button>
              ))}
            </div>
          )}
          <div className="actions">
            <button className="secondary-button" onClick={() => setPhase('running')}>↩ Revenir</button>
            <button className="btn-success" onClick={submitExam}>✅ Soumettre définitivement</button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="screen" style={{ padding: '16px 12px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 14, alignItems: 'start', maxWidth: 1100, margin: '0 auto' }}>
        {/* Sidebar */}
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: 16, display: 'grid', gap: 14, position: 'sticky', top: 76 }}>
          <Timer secs={SECS} total={SECS} onExpire={handleExpire} />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, fontWeight: 700, color: 'var(--muted)' }}>
            <span><strong style={{ color: 'var(--ink)' }}>{answered}</strong> / {questions.length}</span>
            <span>Seuil : 35</span>
          </div>
          <QGrid total={questions.length} cur={idx} ans={answers} onSelect={i => { setReveal(false); setIdx(i); }} />
          <button className="btn-success btn-block btn-sm" onClick={() => answered < questions.length ? setPhase('review') : submitExam()}>
            {answered < questions.length ? `Vérifier (${questions.length - answered} sans réponse)` : '✅ Soumettre'}
          </button>
        </div>

        {/* Main */}
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '20px 22px', display: 'grid', gap: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ background: 'var(--green-l)', color: 'var(--green)', padding: '3px 10px', borderRadius: 999, fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em' }}>{q.category}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <AudioToggle />
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--muted)' }}>Q {idx + 1} / {questions.length}</span>
            </div>
          </div>

          <div style={{ height: 5, background: 'var(--bg)', borderRadius: 999, overflow: 'hidden' }}>
            <div style={{ height: '100%', background: `linear-gradient(90deg,var(--blue),var(--green))`, borderRadius: 'inherit', width: `${(idx + 1) / questions.length * 100}%`, transition: 'width .3s' }} />
          </div>

          {/* Media */}
          {q.media && (
            <div style={{ background: q.mediaType === 'scene' ? '#1a2e1a' : '#f8fafc', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: 20, display: 'flex', justifyContent: 'center', minHeight: 140 }}>
              {q.mediaType === 'sign' ? <SignSvg type={q.media} /> : <SceneSvg type={q.media.replace('situation_','').replace('intersection_','')} />}
            </div>
          )}

          {/* Bouton écouter (visible pour toutes les locales, obligatoire pour les langues nationales) */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <p style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)', lineHeight: 1.5, flex: 1 }}>{q.text}</p>
            <PlayButton text={q.text} options={q.options} size={38} />
          </div>

          <div style={{ display: 'grid', gap: 8 }}>
            {q.options.map((opt, i) => {
              let bg = 'var(--bg)', border = 'var(--border)', color = 'var(--ink2)';
              if (answers[idx] === opt) { bg = '#dcfce7'; border = '#86efac'; color = '#166534'; }
              if (reveal && answers[idx] === opt && answers[idx] !== q.correct) { bg = '#fdecea'; border = '#fca5a5'; color = '#D32F2F'; }
              return (
                <button key={i} type="button" onClick={() => pick(opt)}
                  style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', border: `2px solid ${border}`, borderRadius: 'var(--r-lg)', background: bg, cursor: 'pointer', textAlign: 'left', width: '100%', color, fontSize: 13, fontWeight: 500, minHeight: 'unset', transition: 'all .15s' }}>
                  <span style={{ width: 26, height: 26, borderRadius: 7, background: answers[idx] === opt ? (answers[idx] === q.correct || !reveal ? 'var(--green)' : '#D32F2F') : '#e2e8f0', color: answers[idx] === opt ? '#fff' : 'var(--muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 900, flexShrink: 0 }}>
                    {String.fromCharCode(65 + i)}
                  </span>
                  <span style={{ flex: 1 }}>{opt}</span>
                  {answers[idx] === opt && <span>{answers[idx] === q.correct ? '✓' : '✗'}</span>}
                </button>
              );
            })}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: 8, borderTop: '1px solid var(--border)' }}>
            <button className="secondary-button btn-sm" disabled={idx === 0} onClick={() => { setReveal(false); setIdx(i => Math.max(0, i - 1)); }}>← Précédente</button>
            <button className="secondary-button btn-sm" onClick={() => { setReveal(false); setIdx(i => Math.min(questions.length - 1, i + 1)); }}>Suivante →</button>
          </div>
        </div>
      </div>
    </section>
  );
}

// ══════════════════════════════════════════════════════════════════
// RESULTS PAGE
// ══════════════════════════════════════════════════════════════════
