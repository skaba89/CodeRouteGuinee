// ExamPage — CodeRoute Guinée
// Extrait de src/pages.tsx L3114-L3345
// Pour modifier, éditer ce fichier directement.

import { type AuthUser } from '../authClient';
import { type UserRole } from '../auth';
import { useAuthSession, canUseProtectedActions } from '../authSession';
import * as api from '../api';
import {
  buildDemoExamAttempt,
  buildDemoCertificateVerification,
  buildDemoQuestionImage,
  filterDemoIdentityChecks,
  filterDemoSubmissions,
  filterDemoAuditLogs,
  filterDemoMonitoring,
  filterDemoPayments,
  buildDemoImportStatus,
  buildRiskLabel,
  formatNumber,
  formatCurrency,
  formatAuditDetails,
  getActionErrorMessage,
  sanitizePaymentFilters,
  downloadLocalFile,
  type AuditLogEntry,
  type AuditLogFilters,
  type CandidateIdentityCheck,
  type CandidateIdentityFilters,
  type CandidateSubmission,
  type CandidateSubmissionFilters,
  type ExamAttempt,
  type ExamCertificateVerification,
  type ExamMonitoringFilters,
  type PaymentFilters,
} from './helpers';

export function ExamPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const canUseExamApi = canUseProtectedActions(currentUser, isPresentationMode, ['candidate', 'center', 'admin', 'super_admin']);
  const fallbackExamQuestions: ExamQuestion[] = [
    {
      id: 'demo-question-red-light',
      category: 'Signalisation lumineuse',
      text: 'Que devez-vous faire face a un feu rouge fixe ?',
      options: ['Marquer l arret obligatoire', 'Passer si la voie est libre', 'Klaxonner puis avancer', 'Continuer a vitesse reduite'],
      correct_answer: 'Marquer l arret obligatoire',
      media_type: 'image',
      media_url: buildDemoQuestionImage('Feu rouge fixe', '#c0392b'),
      media_alt: 'Illustration d un feu rouge avec arret obligatoire.',
      is_active: true,
      created_at: new Date().toISOString(),
    },
    {
      id: 'demo-question-priority',
      category: 'Priorite',
      text: 'A une intersection sans panneau, quelle regle appliquez-vous ?',
      options: ['La priorite a droite', 'Le vehicule le plus rapide passe', 'La priorite au vehicule le plus gros', 'Le premier qui klaxonne passe'],
      correct_answer: 'La priorite a droite',
      media_type: 'video',
      media_url: 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4',
      media_alt: 'Sequence video de demonstration pour illustrer une situation dynamique.',
      is_active: true,
      created_at: new Date().toISOString(),
    },
    {
      id: 'demo-question-seatbelt',
      category: 'Securite routiere',
      text: 'Quand devez-vous attacher votre ceinture ?',
      options: ['Avant tout demarrage', 'Uniquement sur autoroute', 'Seulement la nuit', 'Apres avoir atteint 50 km/h'],
      correct_answer: 'Avant tout demarrage',
      media_type: 'image',
      media_url: buildDemoQuestionImage('Ceinture attachee', '#2471a3'),
      media_alt: 'Illustration de securite avant demarrage.',
      is_active: true,
      created_at: new Date().toISOString(),
    },
  ];
  const [examQuestions, setExamQuestions] = useState<ExamQuestion[]>(fallbackExamQuestions);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, number>>({ 0: 0 });
  const [examBookingReference, setExamBookingReference] = useState('CRG-BOOK-DEMO-001');
  const [examStationCode, setExamStationCode] = useState('CTR-KALOUM-POSTE-12');
  const [deviceFingerprint] = useState(() => {
    const userAgent = window.navigator.userAgent.slice(0, 28);
    const language = window.navigator.language || 'fr-GN';
    return `${language}-${userAgent.length}-${window.screen.width}x${window.screen.height}`;
  });
  const [examAttempt, setExamAttempt] = useState<ExamAttempt | null>(null);
  const [examStatus, setExamStatus] = useState<string | null>(null);
  const [isStartingExam, setIsStartingExam] = useState(false);
  const [isSubmittingExam, setIsSubmittingExam] = useState(false);
  const currentQuestion = examQuestions[currentQuestionIndex];
  const displayQuestionNumber = currentQuestionIndex + 12;
  const answeredCount = Object.keys(selectedAnswers).length;
  const progress = Math.round((displayQuestionNumber / 40) * 100);

  useEffect(() => {
    getQuestions()
      .then((questions) => {
        const activeQuestions = questions.filter((question) => question.is_active);
        if (activeQuestions.length > 0) {
          setExamQuestions(activeQuestions.map((question, index) => question.media_url ? question : {
            ...question,
            media_type: index % 2 === 0 ? 'image' : 'video',
            media_url: index % 2 === 0
              ? buildDemoQuestionImage(`Scenario ${index + 1}`, index % 4 === 0 ? '#c0392b' : '#1f7a4d')
              : 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4',
            media_alt: 'Illustration pedagogique ajoutee pour la presentation.',
          }));
          setCurrentQuestionIndex(0);
          setSelectedAnswers({});
        }
      })
      .catch(() => setExamStatus('Mode demo : banque de questions API indisponible.'));
  }, []);

  async function handleStartExam() {
    if (!canUseExamApi) {
      const demoAttempt = buildDemoExamAttempt('started');
      setExamAttempt(demoAttempt);
      window.localStorage.setItem(DEMO_EXAM_ATTEMPT_STORAGE_KEY, demoAttempt.id);
      setExamStatus(`Tentative demo demarree : ${demoAttempt.id}. Trace appareil simulee.`);
      return;
    }
    setIsStartingExam(true);
    setExamStatus(null);
    try {
      const attempt = await startExamFromBooking(examBookingReference, deviceFingerprint, examStationCode);
      setExamAttempt(attempt);
      window.localStorage.setItem(DEMO_EXAM_ATTEMPT_STORAGE_KEY, attempt.id);
      setExamStatus(`Tentative API demarree : ${attempt.id}. Trace appareil enregistree.`);
    } catch (error) {
      setExamStatus(getActionErrorMessage(error, 'Demarrage API impossible. Mode demo maintenu.'));
    } finally {
      setIsStartingExam(false);
    }
  }

  async function handleSubmitExam() {
    if (!canUseExamApi) {
      if (!examAttempt) {
        setExamStatus('Demarrez une tentative demo avant de soumettre.');
        return;
      }
      const submittedAttempt = buildDemoExamAttempt('submitted');
      setExamAttempt(submittedAttempt);
      window.localStorage.setItem(DEMO_EXAM_ATTEMPT_STORAGE_KEY, submittedAttempt.id);
      setExamStatus(`Tentative demo soumise : score ${submittedAttempt.score}/40, certificat pret dans Resultats.`);
      return;
    }
    if (!examAttempt) {
      setExamStatus('Demarrez une tentative API avant de soumettre.');
      return;
    }
    setIsSubmittingExam(true);
    setExamStatus(null);
    const answers = Object.fromEntries(
      Object.entries(selectedAnswers)
        .map(([questionIndex, answerIndex]) => {
          const question = examQuestions[Number(questionIndex)];
          return question ? [question.id, question.options[answerIndex]] : null;
        })
        .filter((entry): entry is [string, string] => Boolean(entry)),
    );
    try {
      const submittedAttempt = await submitExamAttempt(examAttempt.id, answers);
      setExamAttempt(submittedAttempt);
      window.localStorage.setItem(DEMO_EXAM_ATTEMPT_STORAGE_KEY, submittedAttempt.id);
      setExamStatus(`Tentative soumise : score ${submittedAttempt.score ?? 0}, statut ${submittedAttempt.status}.`);
    } catch (error) {
      setExamStatus(getActionErrorMessage(error, 'Soumission impossible. Verifiez la tentative API.'));
    } finally {
      setIsSubmittingExam(false);
    }
  }
  const examChecks = [
    ['Identite', currentUser?.full_name ?? 'Presentation'],
    ['Poste', examStationCode],
    ['Reservation', examBookingReference],
    ['Trace appareil', deviceFingerprint],
  ];
  const monitoringEvents = [
    ['08:42', 'Connexion poste autorisee', 'ok'],
    ['08:51', 'Questionnaire charge et scelle', 'ok'],
    ['09:03', 'Aucune alerte de comportement', 'ok'],
  ];

  return (
    <section className="screen exam-screen">
      <div className="exam-workspace">
        <p className="eyebrow dark">Examen securise</p>
        <div className="exam-header">
          <div>
            <h2>Question {displayQuestionNumber} / 40</h2>
            <p>Mode centre agree avec surveillance, minuterie et trace d'audit de la tentative.</p>
          </div>
          <span className={canUseExamApi ? 'badge ok' : 'badge'}>{canUseExamApi ? 'Session API autorisee' : 'Mode presentation'}</span>
        </div>
        {!canUseExamApi && <p className="protected-action-note">Mode presentation : demarrage et soumission demo actifs localement ; la tentative API officielle reste reservee aux sessions reelles.</p>}
        <div className="exam-trace-controls">
          <label>Reference reservation<input value={examBookingReference} onChange={(event) => setExamBookingReference(event.target.value)} /></label>
          <label>Poste centre<input value={examStationCode} onChange={(event) => setExamStationCode(event.target.value)} /></label>
          <label>Trace appareil<input value={deviceFingerprint} readOnly /></label>
        </div>
        <div className="exam-progress" aria-label="Progression examen"><span style={{ width: `${progress}%` }} /></div>
        <article className="question-card">
          <span className="question-category">{currentQuestion.category}</span>
          <p className="question">{currentQuestion.text}</p>
          {currentQuestion.media_url && currentQuestion.media_type === 'image' && (
            <figure className="question-media">
              <img src={currentQuestion.media_url} alt={currentQuestion.media_alt ?? 'Illustration de la question'} />
              {currentQuestion.media_alt && <figcaption>{currentQuestion.media_alt}</figcaption>}
            </figure>
          )}
          {currentQuestion.media_url && currentQuestion.media_type === 'video' && (
            <figure className="question-media">
              <video src={currentQuestion.media_url} controls preload="metadata" aria-label={currentQuestion.media_alt ?? 'Video de la question'} />
              {currentQuestion.media_alt && <figcaption>{currentQuestion.media_alt}</figcaption>}
            </figure>
          )}
          {currentQuestion.options.map((answer, index) => (
            <button
              type="button"
              className={selectedAnswers[currentQuestionIndex] === index ? 'answer selected' : 'answer'}
              key={answer}
              onClick={() => setSelectedAnswers((current) => ({ ...current, [currentQuestionIndex]: index }))}
            >
              <strong>{String.fromCharCode(65 + index)}.</strong> {answer}
            </button>
          ))}
        </article>
        <div className="exam-navigation">
          <button className="secondary-button" disabled={currentQuestionIndex === 0} onClick={() => setCurrentQuestionIndex((index) => Math.max(0, index - 1))}>Question precedente</button>
          <span>{answeredCount} reponse(s) saisie(s)</span>
          <button disabled={currentQuestionIndex === examQuestions.length - 1} onClick={() => setCurrentQuestionIndex((index) => Math.min(examQuestions.length - 1, index + 1))}>Question suivante</button>
        </div>
        <div className="exam-api-actions">
          <button onClick={handleStartExam} disabled={isStartingExam || !examBookingReference || examAttempt?.status === 'started'}>{isStartingExam ? 'Demarrage...' : canUseExamApi ? 'Demarrer tentative API' : 'Demarrer tentative demo'}</button>
          <button className="secondary-button" onClick={handleSubmitExam} disabled={isSubmittingExam || !examAttempt || examAttempt.status !== 'started'}>
            {isSubmittingExam ? 'Soumission...' : 'Soumettre les reponses'}
          </button>
        </div>
        {examStatus && <p className={examStatus.includes('impossible') || examStatus.includes('indisponible') ? 'form-error' : 'login-status'}>{examStatus}</p>}
      </div>
      <aside className="timer-card exam-control-card">
        <span>Temps restant</span>
        <strong>18:24</strong>
        <p>Score requis : 35 / 40</p>
        <div className="exam-check-grid">
          {examChecks.map(([label, value]) => (
            <div key={label}><small>{label}</small><b>{value}</b></div>
          ))}
        </div>
        <div className="monitoring-feed">
          <strong>Surveillance</strong>
          {monitoringEvents.map(([time, label, status]) => (
            <div className="monitoring-event" key={`${time}-${label}`}>
              <span>{time}</span>
              <p>{label}</p>
              <i className={`status-dot ${status}`} />
            </div>
          ))}
        </div>
      </aside>
    </section>
  );
}
