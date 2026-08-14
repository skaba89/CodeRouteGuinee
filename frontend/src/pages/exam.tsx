// ExamPage — CodeRoute Guinée v5
// Examen officiel durci : temps serveur, reprise après refresh, autosauvegarde
// des réponses et séparation stricte avec l'examen blanc.
import { type FormEvent, useEffect, useRef, useState } from 'react';
import {
  getExamLiveStatus,
  getExamQuestions,
  getExamResults,
  getPrivateJson,
  postPrivateJson,
  startExamFromBooking,
  submitExamAttempt,
} from '../api';
import type { ExamQuestion } from '../api';
import { useIsMobile } from '../hooks/useIsMobile';
import { isAudioLocale, speakFeedback, stop as stopAudio, playQuestionAudio, announceResult, announceInstructions } from '../audio';
import { AudioModeBanner, LocaleAudioSwitcher, PlayButton } from '../components/AudioButton';
import { type AuthUser } from '../authClient';
import { type Locale } from '../i18n';
import { useAuthSession, canUseProtectedActions } from '../authSession';
import { IconArrowLeft, IconArrowRight, IconCheck, IconClock, IconTarget, IconFileCheck, IconClipboard, IconAlertTriangle } from '../icons';
import { DEMO_QUESTIONS, type ExamQuestionData } from './examQuestions';
import { MediaBlock } from './shared-exam-components';
import type { QData } from './shared-exam-components';

interface Props { user?: AuthUser | null; locale?: Locale; onLocaleChange?: (l: Locale) => void; }

type DisplayResultQuestion = {
  question_id: string;
  question_text: string;
  candidate_answer: string;
  correct_answer?: string;
  is_correct: boolean;
  category?: string;
  options?: string[];
  explanation?: string | null;
};

type DisplayResult = {
  score: number;
  threshold: number;
  passed: boolean;
  questions: DisplayResultQuestion[];
};

type SaveState = 'idle' | 'saving' | 'saved' | 'offline';

type ExamQuestionWithMediaRuntime = ExamQuestion & {
  media_poster_url?: string | null;
  media_fallback_url?: string | null;
};

type ExamDisplayQuestion = QData & {
  mediaPoster?: string;
  mediaFallback?: string;
};

const ACTIVE_ATTEMPT_KEY = 'coderoute:official-exam:active-attempt';
const answerStorageKey = (attemptId: string) => `coderoute:official-exam:answers:${attemptId}`;

function errMsg(e: unknown, fallback: string): string {
  if (e instanceof Error) return e.message;
  if (typeof e === 'string') return e;
  return fallback;
}

function readStoredAnswers(attemptId: string): Record<number, string> {
  try {
    const raw = window.sessionStorage.getItem(answerStorageKey(attemptId));
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    return Object.fromEntries(
      Object.entries(parsed)
        .filter(([, value]) => typeof value === 'string')
        .map(([key, value]) => [Number(key), value as string]),
    );
  } catch {
    return {};
  }
}

function persistStoredAnswers(attemptId: string, answers: Record<number, string>) {
  try {
    window.sessionStorage.setItem(answerStorageKey(attemptId), JSON.stringify(answers));
  } catch {
    // Le stockage navigateur ne doit jamais bloquer l'examen.
  }
}

function clearStoredAttempt(attemptId?: string | null) {
  try {
    window.sessionStorage.removeItem(ACTIVE_ATTEMPT_KEY);
    if (attemptId) window.sessionStorage.removeItem(answerStorageKey(attemptId));
  } catch {
    // Best effort.
  }
}

function mapResult(serverResult: Awaited<ReturnType<typeof getExamResults>>): DisplayResult {
  return {
    score: serverResult.score,
    threshold: serverResult.threshold,
    passed: serverResult.passed,
    questions: serverResult.questions.map(item => ({
      question_id: item.question_id,
      question_text: item.text,
      candidate_answer: item.given_answer ?? '—',
      correct_answer: item.correct_answer,
      is_correct: item.is_correct,
      category: item.category,
      options: item.options,
      explanation: item.explanation,
    })),
  };
}

function toApiAnswers(answers: Record<number, string>, questions: QData[]): Record<string, string> {
  const payload: Record<string, string> = {};
  Object.entries(answers).forEach(([index, answer]) => {
    const question = questions[Number(index)];
    if (question) payload[question.id] = answer;
  });
  return payload;
}

function fromApiAnswers(apiAnswers: Record<string, string>, questions: QData[]): Record<number, string> {
  const indexById = new Map(questions.map((question, index) => [question.id, index]));
  const restored: Record<number, string> = {};
  Object.entries(apiAnswers).forEach(([questionId, answer]) => {
    const index = indexById.get(questionId);
    if (index !== undefined && typeof answer === 'string') restored[index] = answer;
  });
  return restored;
}

function firstUnansweredIndex(answers: Record<number, string>, questionCount: number): number {
  for (let index = 0; index < questionCount; index += 1) {
    if (answers[index] === undefined) return index;
  }
  return -1;
}

function toDisplayQuestion(question: ExamQuestion, index: number): ExamDisplayQuestion {
  const runtimeQuestion = question as ExamQuestionWithMediaRuntime;
  return {
    id: question.id,
    text: question.text,
    options: question.options,
    number: index + 1,
    category: question.category,
    media: question.media_url ?? undefined,
    mediaType: (question.media_type ?? undefined) as 'sign' | 'scene' | 'image' | 'video' | undefined,
    mediaAlt: question.media_alt ?? undefined,
    mediaPoster: runtimeQuestion.media_poster_url ?? undefined,
    mediaFallback: runtimeQuestion.media_fallback_url ?? undefined,
    audioUrl: question.audio_url ?? undefined,
  };
}

async function getServerAnswerSnapshot(attemptId: string): Promise<Record<string, string>> {
  try {
    const payload = await getPrivateJson<{ answers: Record<string, string> }>(
      `/api/v1/exams/${encodeURIComponent(attemptId)}/answers`,
    );
    return payload.answers ?? {};
  } catch {
    return {};
  }
}

function formatRemaining(seconds: number) {
  const safe = Math.max(0, seconds);
  const minutes = Math.floor(safe / 60);
  const secs = safe % 60;
  return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

const CATEGORY_COLOR: Record<string, string> = {
  'Signalisation': '#1A6FC4', 'Priorités': '#7C3AED', 'Vitesse': '#D4A017',
  'Dépassement': '#C0392B', 'Sécurité': '#006B3F', 'Conduite de nuit': '#0E7490',
  'Conditions météo': '#0E7490', 'Alcool & Drogues': '#C0392B',
  'Premiers secours': '#BE185D', 'Feux tricolores': '#D97706',
};
const CATEGORY_BG: Record<string, string> = {
  'Signalisation': '#EBF3FC', 'Priorités': '#EDE9FE', 'Vitesse': '#FDF6E0',
  'Dépassement': '#FDECEA', 'Sécurité': '#E6F3EC', 'Conduite de nuit': '#E0F7FA',
  'Conditions météo': '#E0F7FA', 'Alcool & Drogues': '#FDECEA',
  'Premiers secours': '#FCE7F3', 'Feux tricolores': '#FEF3C7',
};

export function ExamPage({ locale }: Props) {
  const { currentUser } = useAuthSession();
  const isAuth = Boolean(currentUser);
  const canUseApi = canUseProtectedActions(currentUser, false, ['candidate','center','admin','super_admin']);
  const isMobile = useIsMobile();

  const [liveQuestions, setLiveQuestions] = useState<ExamQuestion[] | null>(null);
  const questions: ExamDisplayQuestion[] = (liveQuestions ?? []).length > 0
    ? liveQuestions!.map(toDisplayQuestion)
    : DEMO_QUESTIONS.map((question: ExamQuestionData) => ({
        id: question.id,
        text: question.text,
        options: question.options,
        correct_answer: question.correct_answer,
        number: question.number,
        category: question.category,
        media: question.media_url ?? undefined,
        mediaType: question.media_url
          ? (question.media_url.startsWith('intersection') || question.media_url.startsWith('situation')
              || question.media_url.endsWith('_driving') || question.media_url.endsWith('_scene')
              || question.media_url.endsWith('_priority_right') ? 'scene' : 'sign')
          : undefined,
        mediaAlt: question.media_alt ?? undefined,
        expl: question.explanation,
      }));

  const [phase, setPhase] = useState<'setup' | 'running' | 'done'>('setup');
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [reveal, setReveal] = useState(false);
  const [bookRef, setBookRef] = useState('');
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [result, setResult] = useState<DisplayResult | null>(null);
  const [startLoading, setStartLoading] = useState(false);
  const [startErr, setStartErr] = useState('');
  const [submissionErr, setSubmissionErr] = useState('');
  const [filter, setFilter] = useState<'all' | 'ok' | 'ko'>('all');
  const [remainingSeconds, setRemainingSeconds] = useState(30 * 60);
  const [totalSeconds, setTotalSeconds] = useState(30 * 60);
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [timerSyncedAt, setTimerSyncedAt] = useState<Date | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const timeoutSubmitFired = useRef(false);
  const submissionInFlight = useRef(false);
  const autosaveQueue = useRef<Promise<void>>(Promise.resolve());
  const latestAutosaveSnapshot = useRef<Record<number, string>>({});

  const q = questions[idx];
  const answered = Object.keys(answers).length;
  const currentAnswered = answers[idx] !== undefined;
  const audioEnabled = isAudioLocale(locale as Locale);
  const isOfficialExam = attemptId !== null;

  async function loadServerResult(id: string) {
    const serverResult = await getExamResults(id);
    setResult(mapResult(serverResult));
    clearStoredAttempt(id);
    setSaveState('saved');
    setPhase('done');
  }

  async function finalizeTimedOutExam(id: string) {
    setSubmissionErr('Temps écoulé — finalisation sécurisée à partir de la dernière sauvegarde serveur…');
    try {
      await postPrivateJson(`/api/v1/exams/${encodeURIComponent(id)}/timeout-submit`, {});
      await loadServerResult(id);
    } catch (err: unknown) {
      setSubmissionErr(errMsg(err, 'Finalisation automatique momentanément indisponible. La dernière sauvegarde serveur est conservée.'));
      timeoutSubmitFired.current = false;
    }
  }

  // Reprise automatique d'une tentative officielle après refresh/retour écran.
  useEffect(() => {
    if (!canUseApi || phase !== 'setup') return;
    let cancelled = false;
    const storedAttemptId = window.sessionStorage.getItem(ACTIVE_ATTEMPT_KEY);
    if (!storedAttemptId) return;

    void (async () => {
      setStartLoading(true);
      try {
        const status = await getExamLiveStatus(storedAttemptId);
        if (cancelled) return;

        if (status.status === 'submitted') {
          setAttemptId(storedAttemptId);
          await loadServerResult(storedAttemptId);
          return;
        }

        if (!['started', 'expired'].includes(status.status)) {
          clearStoredAttempt(storedAttemptId);
          return;
        }

        const [response, serverSnapshot] = await Promise.all([
          getExamQuestions(storedAttemptId, locale),
          getServerAnswerSnapshot(storedAttemptId),
        ]);
        if (cancelled) return;
        setAttemptId(storedAttemptId);
        setLiveQuestions(response.questions);
        const questionView: ExamDisplayQuestion[] = response.questions.map(toDisplayQuestion);
        const restoredAnswers = {
          ...fromApiAnswers(serverSnapshot, questionView),
          ...readStoredAnswers(storedAttemptId),
        };
        setAnswers(restoredAnswers);
        const resumeIndex = firstUnansweredIndex(restoredAnswers, questionView.length);
        setIdx(resumeIndex === -1 ? Math.max(0, questionView.length - 1) : resumeIndex);
        persistStoredAnswers(storedAttemptId, restoredAnswers);
        latestAutosaveSnapshot.current = restoredAnswers;
        autosaveQueue.current = Promise.resolve();
        setRemainingSeconds(status.remaining_seconds);
        setTotalSeconds(status.total_seconds || response.duration_seconds || 30 * 60);
        setTimerSyncedAt(new Date());
        timeoutSubmitFired.current = false;
        setPhase('running');
      } catch {
        // Une tentative inaccessible/ancienne ne doit pas bloquer le candidat.
        clearStoredAttempt(storedAttemptId);
      } finally {
        if (!cancelled) setStartLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [canUseApi, locale, phase]);

  // Le backend est l'horloge de référence. Resynchronisation toutes les 10 s.
  useEffect(() => {
    if (!attemptId || phase !== 'running') return;
    let cancelled = false;

    const syncServerClock = async () => {
      try {
        const status = await getExamLiveStatus(attemptId);
        if (cancelled) return;
        setRemainingSeconds(status.remaining_seconds);
        setTotalSeconds(status.total_seconds || 30 * 60);
        setTimerSyncedAt(new Date());
        if (status.status === 'submitted') {
          await loadServerResult(attemptId);
        }
      } catch {
        // Le compteur local continue visuellement, mais aucune décision de score
        // n'est prise côté navigateur. La prochaine synchro recale l'horloge.
      }
    };

    void syncServerClock();
    const poll = window.setInterval(() => { void syncServerClock(); }, 10_000);
    return () => {
      cancelled = true;
      window.clearInterval(poll);
    };
  }, [attemptId, phase]);

  // Tick d'affichage entre deux synchronisations serveur.
  useEffect(() => {
    if (phase !== 'running') return;
    const tick = window.setInterval(() => {
      setRemainingSeconds(current => Math.max(0, current - 1));
    }, 1000);
    return () => window.clearInterval(tick);
  }, [phase]);

  // À 00:00 : finalisation automatique avec la dernière copie serveur.
  useEffect(() => {
    if (!attemptId || phase !== 'running' || remainingSeconds > 0 || timeoutSubmitFired.current) return;
    timeoutSubmitFired.current = true;
    void finalizeTimedOutExam(attemptId);
  }, [attemptId, phase, remainingSeconds]);

  useEffect(() => {
    if (phase === 'running' && audioEnabled && q) {
      void playQuestionAudio(q.id, locale as Locale, q.text, q.options, q.audioUrl);
    }
    return () => { if (audioEnabled) stopAudio(); };
  }, [idx, phase, audioEnabled, locale, q]);

  useEffect(() => {
    if (phase === 'done' && result && audioEnabled) {
      void announceResult(Boolean(result.passed), Number(result.score ?? 0), Number(result.questions?.length ?? questions.length));
    }
  }, [phase, result, audioEnabled, questions.length]);

  useEffect(() => {
    if (phase !== 'running') return;
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'ArrowRight') {
        if (answers[idx] === undefined) {
          setSubmissionErr(`Répondez à la question ${idx + 1} avant de continuer.`);
          return;
        }
        setSubmissionErr('');
        setReveal(false);
        setIdx(index => Math.min(questions.length - 1, index + 1));
      }
      if (event.key === 'ArrowLeft') {
        setSubmissionErr('');
        setReveal(false);
        setIdx(index => Math.max(0, index - 1));
      }
      if (['1','2','3','4'].includes(event.key)) {
        const optionIndex = parseInt(event.key) - 1;
        if (q?.options[optionIndex]) pick(q.options[optionIndex]);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [phase, idx, q, answers, isOfficialExam, questions.length]);

  function autosaveOfficialAnswers(nextAnswers: Record<number, string>): Promise<void> {
    if (!attemptId) return Promise.resolve();
    const id = attemptId;
    const snapshot = nextAnswers;
    const apiAnswers = toApiAnswers(snapshot, questions);
    persistStoredAnswers(id, snapshot);
    latestAutosaveSnapshot.current = snapshot;
    setSaveState('saving');

    const saveSnapshot = async () => {
      try {
        await postPrivateJson(`/api/v1/exams/${encodeURIComponent(id)}/answers`, { answers: apiAnswers });
        if (latestAutosaveSnapshot.current === snapshot) setSaveState('saved');
      } catch {
        // Une copie locale plus récente reste prioritaire. La file FIFO évite
        // qu'un vieux snapshot arrivé tardivement écrase une réponse récente.
        if (latestAutosaveSnapshot.current === snapshot) setSaveState('offline');
      }
    };

    autosaveQueue.current = autosaveQueue.current.catch(() => undefined).then(saveSnapshot);
    return autosaveQueue.current;
  }

  function pick(opt: string) {
    if (!q) return;

    setSubmissionErr('');
    if (isOfficialExam) {
      const nextAnswers = { ...answers, [idx]: opt };
      setAnswers(nextAnswers);
      setReveal(false);
      void autosaveOfficialAnswers(nextAnswers);
      return;
    }

    if (answers[idx] !== undefined) return;
    const isCorrect = opt === q.correct_answer;
    if (audioEnabled) speakFeedback(isCorrect, q.explanation ?? q.expl);
    setAnswers(current => ({ ...current, [idx]: opt }));
    setReveal(true);
  }

  function goToPreviousQuestion() {
    setSubmissionErr('');
    setReveal(false);
    setIdx(index => Math.max(0, index - 1));
  }

  function goToNextQuestion() {
    if (answers[idx] === undefined) {
      setSubmissionErr(`Répondez à la question ${idx + 1} avant de continuer.`);
      return;
    }
    setSubmissionErr('');
    setReveal(false);
    setIdx(index => Math.min(questions.length - 1, index + 1));
  }

  function resetExamState() {
    clearStoredAttempt(attemptId);
    setPhase('setup');
    setAnswers({});
    setIdx(0);
    setResult(null);
    setLiveQuestions(null);
    setAttemptId(null);
    setReveal(false);
    setSubmissionErr('');
    setStartErr('');
    setFilter('all');
    setRemainingSeconds(30 * 60);
    setTotalSeconds(30 * 60);
    setSaveState('idle');
    setTimerSyncedAt(null);
    setSubmitting(false);
    submissionInFlight.current = false;
    autosaveQueue.current = Promise.resolve();
    latestAutosaveSnapshot.current = {};
    timeoutSubmitFired.current = false;
  }

  function startDemoExam() {
    clearStoredAttempt(attemptId);
    setStartErr('');
    setSubmissionErr('');
    setAttemptId(null);
    setLiveQuestions(null);
    setAnswers({});
    setIdx(0);
    setReveal(false);
    setResult(null);
    setFilter('all');
    setRemainingSeconds(30 * 60);
    setTotalSeconds(30 * 60);
    setSaveState('idle');
    setPhase('running');
  }

  async function handleStartExam(event?: FormEvent) {
    event?.preventDefault();
    setStartErr('');
    setSubmissionErr('');

    if (!canUseApi || !bookRef.trim()) {
      setStartErr("Connectez-vous et saisissez une référence de réservation valide pour démarrer l'examen officiel.");
      return;
    }

    setStartLoading(true);
    try {
      const attempt = await startExamFromBooking(bookRef.trim());
      const [questionsResponse, status, serverSnapshot] = await Promise.all([
        getExamQuestions(attempt.id, locale),
        getExamLiveStatus(attempt.id),
        getServerAnswerSnapshot(attempt.id),
      ]);
      if (!questionsResponse.questions.length) {
        throw new Error("La session officielle ne contient aucune question. Contactez le responsable du centre.");
      }

      window.sessionStorage.setItem(ACTIVE_ATTEMPT_KEY, attempt.id);
      setAttemptId(attempt.id);
      setLiveQuestions(questionsResponse.questions);
      const questionView: ExamDisplayQuestion[] = questionsResponse.questions.map(toDisplayQuestion);
      const restoredAnswers = fromApiAnswers(serverSnapshot, questionView);
      setAnswers(restoredAnswers);
      persistStoredAnswers(attempt.id, restoredAnswers);
      latestAutosaveSnapshot.current = restoredAnswers;
      autosaveQueue.current = Promise.resolve();
      const resumeIndex = firstUnansweredIndex(restoredAnswers, questionView.length);
      setIdx(resumeIndex === -1 ? Math.max(0, questionView.length - 1) : resumeIndex);
      setReveal(false);
      setResult(null);
      setFilter('all');
      setRemainingSeconds(status.remaining_seconds);
      setTotalSeconds(status.total_seconds || questionsResponse.duration_seconds || 30 * 60);
      setTimerSyncedAt(new Date());
      setSaveState('saved');
      timeoutSubmitFired.current = false;
      setPhase('running');
    } catch (err: unknown) {
      setAttemptId(null);
      setLiveQuestions(null);
      setStartErr(errMsg(err, "Impossible de démarrer l'examen officiel"));
    } finally {
      setStartLoading(false);
    }
  }

  async function submitExam() {
    const firstMissing = firstUnansweredIndex(answers, questions.length);
    if (firstMissing !== -1) {
      setSubmissionErr(`Répondez à toutes les questions avant de soumettre. La question ${firstMissing + 1} est encore sans réponse.`);
      setReveal(false);
      setIdx(firstMissing);
      return;
    }

    if (submissionInFlight.current) return;
    submissionInFlight.current = true;
    setSubmitting(true);
    setSubmissionErr('');

    try {
      if (attemptId) {
        try {
          // Attendre la file d'autosauvegarde évite que la soumission finale
          // dépasse encore un snapshot local en transit.
          await autosaveQueue.current.catch(() => undefined);
          try {
            await submitExamAttempt(attemptId, toApiAnswers(answers, questions));
          } catch {
            // Un retry réseau ou une soumission déjà finalisée est idempotent :
            // on relit toujours le résultat persistant comme source de vérité.
          }
          await loadServerResult(attemptId);
        } catch (err: unknown) {
          setSubmissionErr(errMsg(err, "Impossible d'enregistrer ou de récupérer le résultat officiel."));
          timeoutSubmitFired.current = false;
        }
        return;
      }

      const score = questions.filter((_, index) => answers[index] === questions[index].correct_answer).length;
      setResult({
        score,
        threshold: 35,
        passed: score >= 35,
        questions: questions.map((question, index) => ({
          question_id: question.id,
          question_text: question.text,
          candidate_answer: answers[index] ?? '—',
          correct_answer: question.correct_answer,
          is_correct: answers[index] === question.correct_answer,
          category: question.category,
          options: question.options,
          explanation: question.expl,
        })),
      });
      setPhase('done');
    } finally {
      submissionInFlight.current = false;
      setSubmitting(false);
    }
  }

  if (phase === 'setup') {
    const stats = [
      { icon: <IconClipboard size={18}/>, label: '40 questions', desc: 'illustrées' },
      { icon: <IconClock size={18}/>, label: '30 minutes', desc: 'temps serveur' },
      { icon: <IconTarget size={18}/>, label: '35 / 40', desc: 'pour réussir' },
      { icon: <IconFileCheck size={18}/>, label: 'Reprise sûre', desc: 'après coupure' },
    ];
    return (
      <section className="screen" role="main">
        <div style={{ maxWidth: 560, margin: '0 auto' }}>
          <AudioModeBanner />
          <div style={{ background: 'linear-gradient(135deg, #0D2137 0%, #1B3254 55%, #0F4A2A 100%)', borderRadius: 20, padding: '32px 28px', color: '#fff', marginBottom: 20, textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
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
              <h2 style={{ color: '#fff', fontSize: 22, fontWeight: 800, letterSpacing: '-.03em', marginBottom: 6 }}>Code de la Route — Catégorie B</h2>
              <p style={{ color: 'rgba(255,255,255,.65)', fontSize: 13 }}>République de Guinée · Direction Nationale des Transports Terrestres</p>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
            {stats.map(({ icon, label, desc }) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, boxShadow: 'var(--sh-xs)' }}>
                <div style={{ color: 'var(--guinea-green)', flexShrink: 0 }}>{icon}</div>
                <div><div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink)' }}>{label}</div><div style={{ fontSize: 11, color: 'var(--muted)' }}>{desc}</div></div>
              </div>
            ))}
          </div>

          <div className="card">
            <LocaleAudioSwitcher />
            {audioEnabled && (
              <button type="button" className="btn-outline" onClick={() => { void announceInstructions(40, 30, 35); }} style={{ width: '100%', marginTop: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M11 5 6 9H2v6h4l5 4V5zM15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14" /></svg>
                Écouter les consignes
              </button>
            )}

            {isAuth && (
              <label style={{ marginBottom: 14, marginTop: 14 }}>
                Référence de réservation <span style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 400 }}>(obligatoire pour l'examen officiel)</span>
                <input value={bookRef} onChange={event => setBookRef(event.target.value)} placeholder="GN-CONV-2026-000001" style={{ marginTop: 6 }}/>
              </label>
            )}
            {startErr && (
              <div style={{ display: 'flex', gap: 8, padding: '10px 14px', background: 'var(--gold-l)', border: '1px solid var(--gold)', borderRadius: 8, fontSize: 13, color: 'var(--ink2)', marginBottom: 12, alignItems: 'flex-start' }}>
                <IconAlertTriangle size={16} style={{ color: 'var(--gold)', flexShrink: 0, marginTop: 1 }}/><span>{startErr}</span>
              </div>
            )}

            {isAuth && (
              <button className="btn-success btn-block" style={{ minHeight: 48, fontSize: 14, fontWeight: 700 }} onClick={handleStartExam} disabled={startLoading || !canUseApi || !bookRef.trim()}>
                {startLoading ? 'Vérification de la session…' : "Démarrer l'examen officiel"}
              </button>
            )}
            <button className="secondary-button btn-block" style={{ minHeight: 44, marginTop: 10, fontSize: 13, fontWeight: 700 }} onClick={startDemoExam} disabled={startLoading}>Commencer un examen blanc</button>
            <p style={{ fontSize: 12, color: 'var(--muted)', textAlign: 'center', marginTop: 12 }}>Examen officiel : réservation requise · Examen blanc : entraînement sans valeur administrative</p>
          </div>
        </div>
      </section>
    );
  }

  if (phase === 'done' && result) {
    const filtered = result.questions.filter(question => filter === 'all' ? true : filter === 'ok' ? question.is_correct : !question.is_correct);
    const scoreColor = result.passed ? 'var(--guinea-green)' : 'var(--red)';
    return (
      <section className="screen" role="main">
        <div style={{ maxWidth: 780, margin: '0 auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'auto 1fr', gap: isMobile ? 14 : 24, padding: isMobile ? 20 : 28, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, marginBottom: 20, boxShadow: 'var(--sh)', alignItems: 'center', justifyItems: isMobile ? 'center' : 'stretch', textAlign: isMobile ? 'center' : 'left' }}>
            <div style={{ width: 120, height: 120, borderRadius: '50%', background: `conic-gradient(${scoreColor} ${(result.score / Math.max(1, result.questions.length) * 100).toFixed(1)}%, var(--border) 0)`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ width: 96, height: 96, borderRadius: '50%', background: 'var(--surface)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                <span style={{ fontSize: 28, fontWeight: 800, color: scoreColor }}>{result.score}</span><span style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 600 }}>/ {result.questions.length}</span>
              </div>
            </div>
            <div>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 12px', borderRadius: 20, background: result.passed ? '#E6F3EC' : '#FDECEA', color: scoreColor, fontSize: 12, fontWeight: 700, marginBottom: 10 }}>
                {result.passed ? <IconCheck size={14}/> : <IconAlertTriangle size={14}/>} {result.passed ? 'ADMIS' : 'NON ADMIS'}
              </div>
              <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>{result.score} réponses correctes sur {result.questions.length}</h2>
              <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 14 }}>Seuil d'admission : {result.threshold} / {result.questions.length}</p>
              <button className="btn-success btn-sm" onClick={resetExamState}>Nouvel examen</button>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            {([['all', `Toutes (${result.questions.length})`], ['ok', `Correctes (${result.questions.filter(item => item.is_correct).length})`], ['ko', `Erreurs (${result.questions.filter(item => !item.is_correct).length})`]] as [string,string][]).map(([value, label]) => (
              <button key={value} className={filter === value ? 'btn-success btn-sm' : 'secondary-button btn-sm'} onClick={() => setFilter(value as 'all' | 'ok' | 'ko')}>{label}</button>
            ))}
          </div>

          <div style={{ display: 'grid', gap: 10 }}>
            {filtered.map((item, index) => (
              <div key={index} style={{ background: 'var(--surface)', border: `1.5px solid ${item.is_correct ? '#86efac' : '#fca5a5'}`, borderRadius: 12, padding: '14px 18px', display: 'grid', gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><p style={{ fontSize: 13.5, fontWeight: 600, flex: 1 }}>{item.question_text}</p>{item.is_correct ? <IconCheck size={18}/> : <IconAlertTriangle size={18}/>}</div>
                {!item.is_correct && <>
                  <div style={{ fontSize: 12, color: 'var(--red)', background: '#FDECEA', padding: '4px 10px', borderRadius: 6 }}>Votre réponse : {item.candidate_answer}</div>
                  <div style={{ fontSize: 12, color: 'var(--guinea-green)', background: '#E6F3EC', padding: '4px 10px', borderRadius: 6 }}>Bonne réponse : {item.correct_answer}</div>
                  {item.explanation && <div style={{ fontSize: 12, padding: '6px 10px', background: 'var(--bg)', borderRadius: 6 }}>{item.explanation}</div>}
                </>}
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  const catColor = CATEGORY_COLOR[q?.category ?? ''] ?? '#006B3F';
  const catBg = CATEGORY_BG[q?.category ?? ''] ?? '#E6F3EC';
  const hasMedia = Boolean(q?.media);
  const canRevealAnswer = !isOfficialExam;
  const timerUrgent = remainingSeconds <= 300;
  const timerCritical = remainingSeconds <= 60;
  const timerColor = timerCritical ? '#C0392B' : timerUrgent ? '#D4A017' : '#006B3F';

  return (
    <section className="screen" role="main" aria-label={isOfficialExam ? 'Examen officiel en cours' : 'Examen blanc en cours'} style={{ padding: '20px 16px' }}>
      <div style={{ maxWidth: 1060, margin: '0 auto' }}>
        {isOfficialExam && (
          <div style={{ marginBottom: 12, padding: '10px 12px', borderRadius: 9, background: '#E6F3EC', border: '1px solid #86efac', color: '#006B3F', fontSize: 12.5, fontWeight: 700, display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
            <span>Examen officiel · correction et score exclusivement côté serveur</span>
            <span style={{ fontWeight: 600, color: saveState === 'offline' ? '#C0392B' : '#166534' }}>
              {saveState === 'saving' ? '● Sauvegarde…' : saveState === 'offline' ? '● Réseau instable — copie locale conservée' : '● Réponses sauvegardées'}
            </span>
          </div>
        )}

        {submissionErr && (
          <div style={{ display: 'flex', gap: 8, padding: '10px 14px', background: '#FDECEA', border: '1px solid #fca5a5', borderRadius: 8, fontSize: 13, color: '#991B1B', marginBottom: 12 }}>
            <IconAlertTriangle size={16}/><span>{submissionErr}</span>
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <div aria-label={`Question ${idx + 1} sur ${questions.length}`} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 600 }}><span style={{ color: 'var(--guinea-green)', fontWeight: 800, fontSize: 16 }}>{idx + 1}</span><span style={{ color: 'var(--muted)' }}>/ {questions.length}</span></div>
          <div style={{ flex: 1, height: 6, background: 'var(--border)', borderRadius: 8, overflow: 'hidden', minWidth: 100 }}><div style={{ height: '100%', background: 'linear-gradient(90deg, var(--guinea-green), #009460)', width: `${(idx + 1) / Math.max(1, questions.length) * 100}%` }}/></div>
          <div style={{ padding: '4px 12px', borderRadius: 20, background: catBg, color: catColor, fontSize: 11.5, fontWeight: 700 }}>{q?.category}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 11px', borderRadius: 10, border: `1px solid ${timerColor}33`, background: timerCritical ? '#FDECEA' : timerUrgent ? '#FDF6E0' : '#E6F3EC', flexShrink: 0 }}>
            <IconClock size={15} style={{ color: timerColor }}/>
            <div style={{ display: 'grid', lineHeight: 1.05 }}>
              <strong style={{ color: timerColor, fontVariantNumeric: 'tabular-nums', fontSize: 15 }}>{formatRemaining(remainingSeconds)}</strong>
              <span style={{ fontSize: 9.5, color: 'var(--muted)', marginTop: 3 }}>{isOfficialExam ? `Serveur${timerSyncedAt ? ' · synchronisé' : ''}` : 'Examen blanc'}</span>
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: hasMedia && !isMobile ? '1fr 400px' : '1fr', gap: 16, alignItems: 'start' }}>
          {hasMedia && (
            <div style={{ position: isMobile ? 'static' : 'sticky', top: 76 }}>
              <div key={idx} className="exam-media-fade" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, overflow: 'hidden', boxShadow: 'var(--sh)' }}>
                <div style={{ padding: '10px 16px', background: 'var(--bg)', borderBottom: '1px solid var(--border)', display: 'flex', gap: 6 }}>
                  <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.07em' }}>{q.mediaType === 'sign' ? 'Panneau de signalisation' : q.mediaType === 'video' ? 'Vidéo pédagogique' : q.mediaType === 'image' ? 'Photo réelle' : 'Situation de conduite'}</span>
                  <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--muted)' }}>Question {idx + 1}</span>
                </div>
                <div style={{ padding: q.mediaType === 'scene' ? 0 : '20px 16px 16px' }}><MediaBlock mediaType={q.mediaType} media={q.media} alt={q.mediaAlt} poster={q.mediaPoster} fallback={q.mediaFallback}/></div>
              </div>
            </div>
          )}

          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.09em', marginBottom: 10 }}>Question {idx + 1}</div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 18 }}><p style={{ fontSize: 17, fontWeight: 600, color: 'var(--ink)', lineHeight: 1.6, flex: 1 }}>{q?.text}</p><PlayButton text={q?.text ?? ''} options={q?.options ?? []} size={36}/></div>

            <div style={{ display: 'grid', gap: 9 }}>
              {q?.options.map((opt, optionIndex) => {
                const selected = answers[idx] === opt;
                const correct = canRevealAnswer && opt === q.correct_answer;
                const showResult = canRevealAnswer && reveal && selected;
                const showCorrect = canRevealAnswer && reveal && correct && !selected;
                let borderColor = 'var(--border)', bgColor = 'var(--surface)', textColor = 'var(--ink2)', letterBg = 'var(--bg)', letterColor = 'var(--muted)';
                if (selected && (!reveal || isOfficialExam)) { borderColor = '#006B3F'; bgColor = '#E6F3EC'; textColor = '#006B3F'; letterBg = '#006B3F'; letterColor = '#fff'; }
                if (showResult && correct) { borderColor = '#006B3F'; bgColor = '#E6F3EC'; textColor = '#006B3F'; letterBg = '#006B3F'; letterColor = '#fff'; }
                if (showResult && !correct) { borderColor = '#C0392B'; bgColor = '#FDECEA'; textColor = '#C0392B'; letterBg = '#C0392B'; letterColor = '#fff'; }
                if (showCorrect) { borderColor = '#006B3F'; bgColor = '#E6F3EC'; textColor = '#006B3F'; }
                return (
                  <button key={optionIndex} type="button" onClick={() => pick(opt)} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 16px', border: `2px solid ${borderColor}`, borderRadius: 10, background: bgColor, cursor: isOfficialExam || answers[idx] === undefined ? 'pointer' : 'default', textAlign: 'left', width: '100%', color: textColor, fontSize: 14, fontWeight: 500, minHeight: 'unset' }}>
                    <span style={{ width: 30, height: 30, borderRadius: 8, background: letterBg, color: letterColor, border: `2px solid ${borderColor}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 800, flexShrink: 0 }}>{String.fromCharCode(65 + optionIndex)}</span>
                    <span style={{ flex: 1 }}>{opt}</span>
                    {showResult && correct && <IconCheck size={18}/>} {showResult && !correct && <IconAlertTriangle size={18}/>} {showCorrect && <IconCheck size={18}/>} 
                  </button>
                );
              })}
            </div>

            {canRevealAnswer && reveal && q?.expl && <div style={{ marginTop: 14, padding: '12px 16px', background: '#E6F3EC', borderLeft: '3px solid var(--guinea-green)', borderRadius: '0 8px 8px 0', fontSize: 13, color: '#006B3F' }}><strong>Explication : </strong>{q.expl}</div>}

            {!currentAnswered && (
              <div role="status" style={{ marginTop: 14, fontSize: 12.5, color: 'var(--muted)', textAlign: 'center' }}>
                Sélectionnez une réponse pour continuer vers la question suivante.
              </div>
            )}

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
              <button className="secondary-button btn-sm" disabled={idx === 0} onClick={goToPreviousQuestion} style={{ display: 'flex', alignItems: 'center', gap: 5 }}><IconArrowLeft size={15}/> Précédente</button>
              <span style={{ fontSize: 12, color: 'var(--muted)' }}>{answered} / {questions.length} répondues</span>
              {idx < questions.length - 1
                ? <button className="secondary-button btn-sm" disabled={!currentAnswered} aria-disabled={!currentAnswered} onClick={goToNextQuestion} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>Suivante <IconArrowRight size={15}/></button>
                : <button className="btn-success btn-sm" disabled={submitting || !currentAnswered} onClick={() => { void submitExam(); }} style={{ display: 'flex', alignItems: 'center', gap: 5 }}><IconCheck size={15}/> {submitting ? 'Soumission…' : "Soumettre l'examen"}</button>}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
