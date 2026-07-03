// ExamPage — CodeRoute Guinée v4
// Interface niveau professionnel : layout 2 colonnes, média full-width,
// timer circulaire, barre de progression, grille de navigation.
import { type FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { getExamQuestions, startExamFromBooking, submitExamAttempt } from '../api';
import type { ExamQuestion } from '../api';
import { isAudioLocale, speakFeedback, stop as stopAudio } from '../audio';
import { AudioModeBanner, AudioToggle, LocaleAudioSwitcher, PlayButton } from '../components/AudioButton';
import { type AuthUser } from '../authClient';
import { type Locale } from '../i18n';
import { useAuthSession, canUseProtectedActions } from '../authSession';
import { IconArrowLeft, IconArrowRight, IconCheck, IconClock, IconTarget, IconFileCheck, IconClipboard, IconAlertTriangle } from '../icons';
import { DEMO_QUESTIONS, type ExamQuestionData } from './examQuestions';
import { MediaBlock, Timer, QGrid } from './shared-exam-components';
import type { QData } from './shared-exam-components';

interface Props { user?: AuthUser | null; locale?: Locale; onLocaleChange?: (l: Locale) => void; }

// ── Helpers ──────────────────────────────────────────────────────────────────
function errMsg(e: unknown, fallback: string): string {
  if (e instanceof Error) return e.message;
  if (typeof e === 'string') return e;
  return fallback;
}

const CATEGORY_COLOR: Record<string, string> = {
  'Signalisation':    '#1A6FC4',
  'Priorités':        '#7C3AED',
  'Vitesse':          '#D4A017',
  'Dépassement':      '#C0392B',
  'Sécurité':         '#006B3F',
  'Conduite de nuit': '#0E7490',
  'Conditions météo': '#0E7490',
  'Alcool & Drogues': '#C0392B',
  'Premiers secours': '#BE185D',
  'Feux tricolores':  '#D97706',
};
const CATEGORY_BG: Record<string, string> = {
  'Signalisation':    '#EBF3FC',
  'Priorités':        '#EDE9FE',
  'Vitesse':          '#FDF6E0',
  'Dépassement':      '#FDECEA',
  'Sécurité':         '#E6F3EC',
  'Conduite de nuit': '#E0F7FA',
  'Conditions météo': '#E0F7FA',
  'Alcool & Drogues': '#FDECEA',
  'Premiers secours': '#FCE7F3',
  'Feux tricolores':  '#FEF3C7',
};

// ── Composant principal ───────────────────────────────────────────────────────
export function ExamPage({ locale, onLocaleChange }: Props) {
  const { currentUser } = useAuthSession();
  const isAuth = Boolean(currentUser);
  const canUseApi = canUseProtectedActions(currentUser, false, ['candidate','center','admin','super_admin']);

  // Questions
  const [liveQuestions, setLiveQuestions] = useState<ExamQuestion[] | null>(null);
  const questions: QData[] = (liveQuestions ?? []).length > 0
    ? liveQuestions!.map((q, i) => ({
        id: q.id, text: q.text, options: q.options,
        correct_answer: q.correct_answer, number: i + 1,
        category: q.category,
        media: q.media_url ?? undefined,
        mediaType: q.media_type as 'sign' | 'scene' | undefined,
        mediaAlt: q.media_alt ?? undefined,
      }))
    : DEMO_QUESTIONS.map((q: ExamQuestionData) => ({
        id: q.id, text: q.text, options: q.options,
        correct_answer: q.correct_answer, number: q.number,
        category: q.category,
        media: q.media_url ?? undefined,
        mediaType: q.media_url
          ? (q.media_url.startsWith('intersection') || q.media_url.startsWith('situation')
              || q.media_url.endsWith('_driving') || q.media_url.endsWith('_scene')
              || q.media_url.endsWith('_priority_right') ? 'scene' : 'sign')
          : undefined,
        mediaAlt: q.media_alt ?? undefined,
        expl: q.explanation,
      }));

  // State
  const [phase, setPhase]         = useState<'setup' | 'running' | 'review' | 'done'>('setup');
  const [idx, setIdx]             = useState(0);
  const [answers, setAnswers]     = useState<Record<number, string>>({});
  const [reveal, setReveal]       = useState(false);
  const [bookRef, setBookRef]     = useState('');
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [result, setResult]       = useState<any>(null);
  const [startLoading, setStartLoading] = useState(false);
  const [startErr, setStartErr]   = useState('');
  const [filter, setFilter]       = useState<'all' | 'ok' | 'ko'>('all');

  const q = questions[idx];
  const answered = Object.keys(answers).length;
  const audioEnabled = isAudioLocale(locale as Locale);

  // Lire question à voix haute si audio activé
  useEffect(() => {
    if (phase === 'running' && audioEnabled && q) {
      // Audio: utiliser PlayButton pour lire la question
    }
    return () => { if (audioEnabled) stopAudio(); };
  }, [idx, phase, audioEnabled, locale, q]);

  // Navigation clavier
  useEffect(() => {
    if (phase !== 'running') return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') setIdx(i => Math.min(questions.length - 1, i + 1));
      if (e.key === 'ArrowLeft')  setIdx(i => Math.max(0, i - 1));
      if (['1','2','3','4'].includes(e.key)) {
        const i = parseInt(e.key) - 1;
        if (q?.options[i]) pick(q.options[i]);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [phase, idx, q, answers]);

  // Timer expiration
  const onTimerExpire = useCallback(() => {
    if (phase === 'running') { setPhase('review'); }
  }, [phase]);

  // ── Sélection réponse ───────────────────────────────────────────────────────
  function pick(opt: string) {
    if (answers[idx] !== undefined) return;
    const isCorrect = opt === q.correct_answer;
    if (audioEnabled) speakFeedback(isCorrect);
    setAnswers(a => ({ ...a, [idx]: opt }));
    setReveal(true);
  }

  // ── Démarrer l'examen ────────────────────────────────────────────────────────
  async function handleStartExam(e?: FormEvent) {
    e?.preventDefault();
    setStartLoading(true);
    setStartErr('');
    try {
      if (canUseApi && bookRef.trim()) {
        const attempt = await startExamFromBooking(bookRef.trim());
        setAttemptId(attempt.id);
        const qsResp = await getExamQuestions(attempt.id);
        setLiveQuestions(qsResp.questions);
      }
      setPhase('running');
    } catch (err: unknown) {
      const msg = errMsg(err, "Impossible de démarrer l'examen");
      if (msg.includes('404') || msg.includes('401') || msg.includes('not found')) {
        setStartErr('Référence introuvable — passage en mode démonstration');
        setTimeout(() => { setStartErr(''); setPhase('running'); }, 1800);
      } else {
        setStartErr(msg);
      }
    } finally {
      setStartLoading(false);
    }
  }

  // ── Soumettre l'examen ───────────────────────────────────────────────────────
  async function submitExam() {
    setPhase('done');
    if (attemptId) {
      try {
        const payload: Record<string, string> = {};
        Object.entries(answers).forEach(([i, ans]) => { payload[questions[parseInt(i)].id] = ans; });
        const r = await submitExamAttempt(attemptId, payload);
        setResult(r);
      } catch { /* afficher résultats locaux */ }
    }
    if (!result) {
      const score = questions.filter((_, i) => answers[i] === questions[i].correct_answer).length;
      setResult({
        score, threshold: 35, passed: score >= 35,
        questions: questions.map((q2, i) => ({
          question_id: q2.id, question_text: q2.text,
          candidate_answer: answers[i] ?? '—',
          correct_answer: q2.correct_answer,
          is_correct: answers[i] === q2.correct_answer,
          category: q2.category, options: q2.options,
          explanation: q2.expl,
        })),
      });
    }
  }

  // ── PHASE SETUP ─────────────────────────────────────────────────────────────
  if (phase === 'setup') {
    const stats = [
      { icon: <IconClipboard size={18}/>,  label: '40 questions', desc: 'illustrées' },
      { icon: <IconClock size={18}/>,      label: '30 minutes',   desc: 'minuterie' },
      { icon: <IconTarget size={18}/>,     label: '35 / 40',      desc: 'pour réussir' },
      { icon: <IconFileCheck size={18}/>,  label: 'Résultats',    desc: 'détaillés' },
    ];
    return (
      <section className="screen" role="main">
        <div style={{ maxWidth: 560, margin: '0 auto' }}>
          <AudioModeBanner />

          {/* Hero */}
          <div style={{
            background: 'linear-gradient(135deg, #0D2137 0%, #1B3254 55%, #0F4A2A 100%)',
            borderRadius: 20, padding: '32px 28px', color: '#fff', marginBottom: 20,
            textAlign: 'center', position: 'relative', overflow: 'hidden',
          }}>
            <div style={{ position: 'absolute', top: -40, right: -40, width: 180, height: 180, borderRadius: '50%', background: 'rgba(255,255,255,.04)' }}/>
            <div style={{ position: 'absolute', bottom: -50, left: 30, width: 140, height: 140, borderRadius: '50%', background: 'rgba(0,107,63,.18)' }}/>
            <div style={{ position: 'relative', zIndex: 1 }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 64, height: 64, borderRadius: 16, background: 'rgba(255,255,255,.12)', backdropFilter: 'blur(4px)', marginBottom: 14 }}>
                <svg viewBox="0 0 40 40" width="38" height="38">
                  <rect x="4" y="12" width="32" height="22" rx="4" fill="none" stroke="#fff" strokeWidth="2"/>
                  <path d="M13 12V9a3 3 0 016 0v3M21 12V9a3 3 0 016 0v3" stroke="#fff" strokeWidth="2"/>
                  <path d="M12 21h3l2 4 3-7 2 4h4" stroke="#fff" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <h2 style={{ color: '#fff', fontSize: 22, fontWeight: 800, letterSpacing: '-.03em', marginBottom: 6 }}>
                Code de la Route — Catégorie B
              </h2>
              <p style={{ color: 'rgba(255,255,255,.65)', fontSize: 13 }}>
                République de Guinée · Direction Nationale des Transports Terrestres
              </p>
            </div>
          </div>

          {/* Stats */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
            {stats.map(({ icon, label, desc }) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, boxShadow: 'var(--sh-xs)' }}>
                <div style={{ color: 'var(--guinea-green)', flexShrink: 0 }}>{icon}</div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink)', letterSpacing: '-.01em' }}>{label}</div>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>{desc}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Form */}
          <div className="card">
            <LocaleAudioSwitcher />
            {isAuth && (
              <label style={{ marginBottom: 14, marginTop: 14 }}>
                Référence de réservation <span style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 400 }}>(optionnel)</span>
                <input value={bookRef} onChange={e => setBookRef(e.target.value)} placeholder="GN-CONV-2026-000001" style={{ marginTop: 6 }}/>
              </label>
            )}
            {startErr && (
              <div style={{ display: 'flex', gap: 8, padding: '10px 14px', background: 'var(--gold-l)', border: '1px solid var(--gold)', borderRadius: 8, fontSize: 13, color: 'var(--ink2)', marginBottom: 12, alignItems: 'flex-start' }}>
                <IconAlertTriangle size={16} style={{ color: 'var(--gold)', flexShrink: 0, marginTop: 1 }}/>
                <span>{startErr}</span>
              </div>
            )}
            <button
              className="btn-success btn-block"
              style={{ minHeight: 48, fontSize: 14, fontWeight: 700, letterSpacing: '.02em' }}
              onClick={handleStartExam}
              disabled={startLoading}
            >
              {startLoading ? 'Chargement des questions…' : isAuth && bookRef.trim() ? 'Démarrer l\'examen officiel' : 'Commencer la démonstration'}
            </button>
            <p style={{ fontSize: 12, color: 'var(--muted)', textAlign: 'center', marginTop: 12 }}>
              Touches clavier : ← → pour naviguer · 1 2 3 4 pour répondre
            </p>
          </div>
        </div>
      </section>
    );
  }

  // ── PHASE DONE / RÉSULTATS ───────────────────────────────────────────────────
  if (phase === 'done' && result) {
    const filtered = result.questions.filter((q2: any) =>
      filter === 'all' ? true : filter === 'ok' ? q2.is_correct : !q2.is_correct
    );
    const scoreColor = result.passed ? 'var(--guinea-green)' : 'var(--red)';
    return (
      <section className="screen" role="main">
        <div style={{ maxWidth: 780, margin: '0 auto' }}>

          {/* Score card */}
          <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 24, padding: 28, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, marginBottom: 20, boxShadow: 'var(--sh)', alignItems: 'center' }}>
            {/* Cercle score */}
            <div style={{ width: 120, height: 120, borderRadius: '50%', background: `conic-gradient(${scoreColor} ${(result.score / result.questions.length * 100).toFixed(1)}%, var(--border) 0)`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <div style={{ width: 96, height: 96, borderRadius: '50%', background: 'var(--surface)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2 }}>
                <span style={{ fontSize: 28, fontWeight: 800, color: scoreColor, lineHeight: 1, letterSpacing: '-.03em' }}>{result.score}</span>
                <span style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 600 }}>/ {result.questions.length}</span>
              </div>
            </div>
            {/* Détails */}
            <div>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 12px', borderRadius: 20, background: result.passed ? '#E6F3EC' : '#FDECEA', color: scoreColor, fontSize: 12, fontWeight: 700, marginBottom: 10 }}>
                {result.passed ? <IconCheck size={14}/> : <IconAlertTriangle size={14}/>}
                {result.passed ? 'ADMIS' : 'NON ADMIS'}
              </div>
              <h2 style={{ fontSize: 20, fontWeight: 800, letterSpacing: '-.03em', marginBottom: 4 }}>
                {result.score} réponses correctes sur {result.questions.length}
              </h2>
              <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 14 }}>
                Seuil d'admission : {result.threshold} / {result.questions.length} — {Math.round(result.score / result.questions.length * 100)}%
              </p>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn-success btn-sm" onClick={() => { setPhase('setup'); setAnswers({}); setIdx(0); setResult(null); setLiveQuestions(null); }}>
                  Recommencer
                </button>
              </div>
            </div>
          </div>

          {/* Filtres */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            {([['all', `Toutes (${result.questions.length})`], ['ok', `Correctes (${result.questions.filter((q:any)=>q.is_correct).length})`], ['ko', `Erreurs (${result.questions.filter((q:any)=>!q.is_correct).length})`]] as [string,string][]).map(([f, label]) => (
              <button key={f} className={filter === f ? 'btn-success btn-sm' : 'secondary-button btn-sm'} onClick={() => setFilter(f as any)}>
                {label}
              </button>
            ))}
          </div>

          {/* Liste des questions */}
          <div style={{ display: 'grid', gap: 10 }}>
            {filtered.map((q2: any, i: number) => (
              <div key={i} style={{ background: 'var(--surface)', border: `1.5px solid ${q2.is_correct ? '#86efac' : '#fca5a5'}`, borderRadius: 12, padding: '14px 18px', display: 'grid', gap: 8 }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                  <p style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink)', flex: 1, lineHeight: 1.5 }}>{q2.question_text}</p>
                  <div style={{ flexShrink: 0, color: q2.is_correct ? 'var(--guinea-green)' : 'var(--red)' }}>
                    {q2.is_correct ? <IconCheck size={18}/> : <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>}
                  </div>
                </div>
                {!q2.is_correct && (
                  <div style={{ display: 'grid', gap: 4 }}>
                    <div style={{ fontSize: 12, color: 'var(--red)', background: '#FDECEA', padding: '4px 10px', borderRadius: 6 }}>
                      Votre réponse : {q2.candidate_answer}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--guinea-green)', background: '#E6F3EC', padding: '4px 10px', borderRadius: 6 }}>
                      Bonne réponse : {q2.correct_answer}
                    </div>
                    {q2.explanation && (
                      <div style={{ fontSize: 12, color: 'var(--ink2)', padding: '6px 10px', background: 'var(--bg)', borderRadius: 6, lineHeight: 1.6 }}>
                        {q2.explanation}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  // ── PHASE RUNNING ────────────────────────────────────────────────────────────
  const catColor = CATEGORY_COLOR[q?.category ?? ''] ?? '#006B3F';
  const catBg    = CATEGORY_BG[q?.category ?? '']    ?? '#E6F3EC';
  const hasMedia = Boolean(q?.media);

  return (
    <section className="screen" role="main" aria-label="Examen en cours" style={{ padding: '20px 16px' }}>
      <div style={{ maxWidth: 1060, margin: '0 auto' }}>

        {/* ── Barre supérieure ─────────────────────────────────────────── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          {/* Progression textuelle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>
            <span style={{ color: 'var(--guinea-green)', fontWeight: 800, fontSize: 16 }}>{idx + 1}</span>
            <span style={{ color: 'var(--muted)' }}>/ {questions.length}</span>
          </div>
          {/* Barre progression */}
          <div style={{ flex: 1, height: 6, background: 'var(--border)', borderRadius: 8, overflow: 'hidden', minWidth: 100 }}>
            <div style={{ height: '100%', background: 'linear-gradient(90deg, var(--guinea-green), #009460)', borderRadius: 'inherit', width: `${(idx + 1) / questions.length * 100}%`, transition: 'width .35s ease' }} />
          </div>
          {/* Badge catégorie */}
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '4px 12px', borderRadius: 20, background: catBg, color: catColor, fontSize: 11.5, fontWeight: 700 }}>
            {q?.category}
          </div>
          {/* Timer */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '5px 12px', borderRadius: 20, border: '1px solid var(--border)', fontSize: 12.5, fontWeight: 600, color: 'var(--muted)', background: 'var(--surface)', flexShrink: 0 }}>
            <IconClock size={14} style={{ color: 'var(--muted)' }}/>
            <Timer secs={30 * 60} total={30 * 60} onExpire={onTimerExpire} />
          </div>
        </div>

        {/* ── Layout principal ──────────────────────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: hasMedia ? '1fr 400px' : '1fr', gap: 16, alignItems: 'start' }}>

          {/* ── Colonne média (si présent) ──────────────────────────────── */}
          {hasMedia && (
            <div style={{ position: 'sticky', top: 76 }}>
              <div key={idx} className="exam-media-fade" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, overflow: 'hidden', boxShadow: 'var(--sh)' }}>
                {/* Entête zone média */}
                <div style={{ padding: '10px 16px', background: 'var(--bg)', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                  <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.07em' }}>
                    {q.mediaType === 'sign' ? 'Panneau de signalisation' : q.mediaType === 'video' ? 'Vidéo pédagogique' : q.mediaType === 'image' ? 'Photo réelle' : 'Situation de conduite'}
                  </span>
                  <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--muted)', opacity: .6 }}>
                    Question {idx + 1}
                  </span>
                </div>
                {/* Média */}
                <div style={{ padding: q.mediaType === 'scene' ? 0 : '20px 16px 16px' }}>
                  <MediaBlock mediaType={q.mediaType} media={q.media} alt={q.mediaAlt} />
                </div>
              </div>
            </div>
          )}

          {/* ── Colonne question + réponses ─────────────────────────────── */}
          <div>
            {/* Numéro question */}
            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.09em', marginBottom: 10 }}>
              Question {idx + 1}
            </div>

            {/* Texte question */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 18 }}>
              <p style={{ fontSize: 17, fontWeight: 600, color: 'var(--ink)', lineHeight: 1.6, flex: 1 }}>
                {q?.text}
              </p>
              <PlayButton text={q?.text ?? ''} options={q?.options ?? []} size={36} />
            </div>

            {/* Options */}
            <div style={{ display: 'grid', gap: 9 }}>
              {q?.options.map((opt, i) => {
                const isSelected = answers[idx] === opt;
                const isCorrect  = opt === q.correct_answer;
                const showResult = reveal && isSelected;
                const showCorrect= reveal && isCorrect && !isSelected;

                let borderColor = 'var(--border)';
                let bgColor     = 'var(--surface)';
                let textColor   = 'var(--ink2)';
                let letterBg    = 'var(--bg)';
                let letterColor = 'var(--muted)';

                if (isSelected && !reveal) { borderColor = 'var(--guinea-green)'; bgColor = '#E6F3EC'; textColor = '#006B3F'; letterBg = '#006B3F'; letterColor = '#fff'; }
                if (showResult && isCorrect) { borderColor = '#006B3F'; bgColor = '#E6F3EC'; textColor = '#006B3F'; letterBg = '#006B3F'; letterColor = '#fff'; }
                if (showResult && !isCorrect){ borderColor = '#C0392B'; bgColor = '#FDECEA'; textColor = '#C0392B'; letterBg = '#C0392B'; letterColor = '#fff'; }
                if (showCorrect)             { borderColor = '#006B3F'; bgColor = '#E6F3EC'; textColor = '#006B3F'; letterBg = '#E6F3EC'; letterColor = '#006B3F'; }

                return (
                  <button key={i} type="button" onClick={() => pick(opt)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 12,
                      padding: '13px 16px',
                      border: `2px solid ${borderColor}`,
                      borderRadius: 10,
                      background: bgColor,
                      cursor: answers[idx] !== undefined ? 'default' : 'pointer',
                      textAlign: 'left', width: '100%',
                      color: textColor, fontSize: 14, fontWeight: 500,
                      minHeight: 'unset', transition: 'all .12s ease',
                      lineHeight: 1.5,
                    }}>
                    {/* Lettre */}
                    <span style={{ width: 30, height: 30, borderRadius: 8, background: letterBg, color: letterColor, border: `2px solid ${borderColor}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 800, flexShrink: 0, transition: 'all .12s' }}>
                      {String.fromCharCode(65 + i)}
                    </span>
                    {/* Texte */}
                    <span style={{ flex: 1 }}>{opt}</span>
                    {/* Icône résultat */}
                    {showResult && isCorrect  && <IconCheck size={18} style={{ color: '#006B3F', flexShrink: 0 }}/>}
                    {showResult && !isCorrect && <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#C0392B" strokeWidth="2.5" style={{ flexShrink: 0 }}><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>}
                    {showCorrect && <IconCheck size={18} style={{ color: '#006B3F', flexShrink: 0 }}/>}
                  </button>
                );
              })}
            </div>

            {/* Explication */}
            {reveal && q?.expl && (
              <div style={{ marginTop: 14, padding: '12px 16px', background: '#E6F3EC', borderLeft: '3px solid var(--guinea-green)', borderRadius: '0 8px 8px 0', fontSize: 13, color: '#006B3F', lineHeight: 1.65 }}>
                <strong>Explication : </strong>{q.expl}
              </div>
            )}

            {/* Navigation */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
              <button className="secondary-button btn-sm" disabled={idx === 0}
                onClick={() => { setReveal(false); setIdx(i => Math.max(0, i - 1)); }}
                style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <IconArrowLeft size={15}/> Précédente
              </button>
              <span style={{ fontSize: 12, color: 'var(--muted)' }}>{answered} répondue{answered > 1 ? 's' : ''}</span>
              {idx < questions.length - 1
                ? <button className="secondary-button btn-sm"
                    onClick={() => { setReveal(false); setIdx(i => Math.min(questions.length - 1, i + 1)); }}
                    style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    Suivante <IconArrowRight size={15}/>
                  </button>
                : <button className="btn-success btn-sm" onClick={submitExam}
                    style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <IconCheck size={15}/> Soumettre
                  </button>
              }
            </div>
          </div>
        </div>

        {/* ── Grille navigation questions ───────────────────────────────── */}
        <div style={{ marginTop: 20, padding: 16, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, boxShadow: 'var(--sh-xs)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <span style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.07em' }}>
              Navigation — {answered} / {questions.length} répondues
            </span>
            <div style={{ display: 'flex', gap: 12, fontSize: 11, color: 'var(--muted)' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 10, height: 10, borderRadius: 3, background: '#dcfce7', border: '1.5px solid #86efac', display: 'inline-block' }}/>
                Répondue
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 10, height: 10, borderRadius: 3, background: '#0D2137', display: 'inline-block' }}/>
                Actuelle
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 10, height: 10, borderRadius: 3, background: 'var(--bg)', border: '1.5px solid var(--border)', display: 'inline-block' }}/>
                Non répondue
              </span>
            </div>
          </div>
          <QGrid total={questions.length} cur={idx} ans={answers} onSelect={i => { setReveal(false); setIdx(i); }} />
          <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end' }}>
            <button className="btn-success btn-sm"
              onClick={() => answered < questions.length ? setPhase('review') : submitExam()}
              style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <IconCheck size={14}/>
              {answered < questions.length ? `Soumettre (${questions.length - answered} sans réponse)` : 'Soumettre l\'examen'}
            </button>
          </div>
        </div>

      </div>
    </section>
  );
}
