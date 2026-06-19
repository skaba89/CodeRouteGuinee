/**
 * ResultsPage — CodeRoute Guinée
 * Page des résultats d'examen : vérification de certificat + résultats détaillés.
 */
import { useState, useEffect, type FormEvent } from 'react';
import { useAuthSession, canUseProtectedActions } from '../authSession';
import {
  getExamSummary,
  getExamResults,
  verifyExamCertificate,
  downloadExamCertificatePdf,
  type ExamSummary,
  type ExamCertificateVerification,
  type ExamDetailedResult,
} from '../api';
import { buildDemoCertificateVerification, getActionErrorMessage } from './helpers';

const DEMO_ATTEMPT_KEY = 'coderoute-demo-attempt-id';

const fallbackSummary: ExamSummary = {
  total_attempts: 0,
  submitted_attempts: 0,
  passed_attempts: 0,
  failed_attempts: 0,
  average_score: 0,
};

export function ResultsPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const canUseApi = canUseProtectedActions(currentUser, isPresentationMode, ['candidate', 'center', 'admin', 'super_admin']);

  const [attemptId, setAttemptId] = useState(
    () => sessionStorage.getItem(DEMO_ATTEMPT_KEY) ?? localStorage.getItem(DEMO_ATTEMPT_KEY) ?? ''
  );
  const [summary, setSummary] = useState<ExamSummary>(fallbackSummary);
  const [cert, setCert] = useState<ExamCertificateVerification | null>(null);
  const [certError, setCertError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);

  const [detailedResult, setDetailedResult] = useState<ExamDetailedResult | null>(null);
  const [loadingResult, setLoadingResult] = useState(false);
  const [resultError, setResultError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'correct' | 'wrong'>('all');

  const [downloadingPdf, setDownloadingPdf] = useState(false);

  useEffect(() => {
    if (!canUseApi) return;
    getExamSummary().then(setSummary).catch(() => undefined);
  }, [canUseApi]);

  // Charger auto les résultats si un attemptId est stocké
  useEffect(() => {
    if (!attemptId || !canUseApi) return;
    handleLoadResults();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleVerifyCertificate(e: FormEvent) {
    e.preventDefault();
    if (!attemptId.trim()) return;
    setVerifying(true);
    setCert(null);
    setCertError(null);
    try {
      if (!canUseApi || attemptId.startsWith('DEMO-') || attemptId.startsWith('demo-')) {
        setCert(buildDemoCertificateVerification(attemptId));
        return;
      }
      const result = await verifyExamCertificate(attemptId);
      setCert(result);
    } catch (err) {
      setCertError(getActionErrorMessage(err, 'Vérification impossible.'));
    } finally {
      setVerifying(false);
    }
  }

  async function handleLoadResults() {
    if (!attemptId.trim() || !canUseApi) return;
    setLoadingResult(true);
    setResultError(null);
    try {
      const result = await getExamResults(attemptId);
      setDetailedResult(result);
    } catch {
      setResultError("Résultats non disponibles — l'examen n'est peut-être pas encore soumis.");
    } finally {
      setLoadingResult(false);
    }
  }

  async function handleDownloadPdf() {
    if (!attemptId.trim() || !canUseApi) return;
    setDownloadingPdf(true);
    try {
      await downloadExamCertificatePdf(attemptId);
    } catch {
      setCertError("Téléchargement impossible — vérifiez que l'examen est admis.");
    } finally {
      setDownloadingPdf(false);
    }
  }

  const filteredQuestions = detailedResult?.questions.filter(q =>
    filter === 'all' ? true : filter === 'correct' ? q.is_correct : !q.is_correct
  ) ?? [];

  return (
    <section className="screen results-screen">
      <div className="results-workspace">

        {/* ── En-tête ── */}
        <div className="results-header">
          <span className="eyebrow dark">Résultats officiels</span>
          <h2>Vérification & Résultats d'examen</h2>
          <p>Consultez les résultats d'un examen par son identifiant de tentative.</p>
        </div>

        {/* ── Statistiques nationales (admin) ── */}
        {canUseApi && (currentUser?.role === 'admin' || currentUser?.role === 'super_admin') && (
          <div className="results-stats-grid">
            <div className="stat-card">
              <span className="stat-label">Tentatives total</span>
              <strong className="stat-value">{summary.total_attempts}</strong>
            </div>
            <div className="stat-card">
              <span className="stat-label">Soumis</span>
              <strong className="stat-value">{summary.submitted_attempts}</strong>
            </div>
            <div className="stat-card stat-passed">
              <span className="stat-label">Admis</span>
              <strong className="stat-value">{summary.passed_attempts}</strong>
            </div>
            <div className="stat-card stat-failed">
              <span className="stat-label">Ajournés</span>
              <strong className="stat-value">{summary.failed_attempts}</strong>
            </div>
            <div className="stat-card">
              <span className="stat-label">Score moyen</span>
              <strong className="stat-value">{summary.average_score}<span style={{fontSize:14,fontWeight:700}}>/40</span></strong>
            </div>
          </div>
        )}

        {/* ── Formulaire de recherche ── */}
        <form className="results-search-form" onSubmit={handleVerifyCertificate}>
          <label>
            Identifiant de tentative
            <input
              value={attemptId}
              onChange={e => setAttemptId(e.target.value)}
              placeholder="ATT-... ou DEMO-..."
            />
          </label>
          <div className="results-search-actions">
            <button type="submit" disabled={verifying || !attemptId.trim()}>
              {verifying ? 'Vérification…' : '🔍 Vérifier le certificat'}
            </button>
            {canUseApi && (
              <button type="button" className="secondary-button"
                onClick={handleLoadResults} disabled={loadingResult || !attemptId.trim()}>
                {loadingResult ? 'Chargement…' : '📊 Résultats détaillés'}
              </button>
            )}
          </div>
        </form>

        {certError && <p className="form-error">{certError}</p>}

        {/* ── Certificat ── */}
        {cert && (
          <div className={`certificate-result ${cert.valid && cert.passed ? 'admitted' : cert.valid && cert.passed === false ? 'failed' : 'invalid'}`}>
            <div className="certificate-result-header">
              <span className="cert-icon">{cert.valid && cert.passed ? '🏆' : cert.valid && cert.passed === false ? '📋' : '❌'}</span>
              <div>
                <h3>{cert.valid && cert.passed ? 'Admis — Certificat authentique' : cert.valid && cert.passed === false ? 'Ajourné' : 'Certificat non valide'}</h3>
                {cert.candidate_name && <p className="cert-name">{cert.candidate_name}</p>}
              </div>
              {cert.valid && cert.passed && canUseApi && (
                <button className="btn-download-cert" onClick={handleDownloadPdf} disabled={downloadingPdf}>
                  {downloadingPdf ? '…' : '⬇ PDF'}
                </button>
              )}
            </div>
            {cert.valid && (
              <div className="certificate-fields">
                {cert.candidate_reference && (
                  <div className="certificate-field"><small>Référence</small><b>{cert.candidate_reference}</b></div>
                )}
                {cert.identity_number && (
                  <div className="certificate-field"><small>NINA</small><b>{cert.identity_number}</b></div>
                )}
                {cert.permit_category && (
                  <div className="certificate-field"><small>Catégorie</small><b>{cert.permit_category}</b></div>
                )}
                {cert.center_name && (
                  <div className="certificate-field"><small>Centre</small><b>{cert.center_name} — {cert.center_city}</b></div>
                )}
                {cert.score !== null && cert.score !== undefined && (
                  <div className="certificate-field"><small>Score</small><b>{cert.score}/40</b></div>
                )}
                {cert.submitted_at && (
                  <div className="certificate-field"><small>Date</small><b>{new Date(cert.submitted_at).toLocaleDateString('fr-FR')}</b></div>
                )}
              </div>
            )}
            {cert.reason && !cert.valid && <p className="cert-reason">{cert.reason}</p>}
          </div>
        )}

        {/* ── Résultats détaillés ── */}
        {detailedResult && (
          <div className="detailed-results">
            {/* Verdict */}
            <div className={`exam-verdict-banner ${detailedResult.passed ? 'passed' : 'failed'}`}>
              <span className="verdict-emoji">{detailedResult.passed ? '🏆' : '📋'}</span>
              <div className="verdict-body">
                <h3>{detailedResult.passed ? 'Admis !' : 'Ajourné'}</h3>
                <p>{detailedResult.candidate_name}</p>
              </div>
              <div className="verdict-score">
                <strong>{detailedResult.score} <span>/ {detailedResult.total}</span></strong>
                <small>{detailedResult.score_percent}%</small>
              </div>
            </div>

            {/* Filtres */}
            <div className="result-filter-bar">
              {(['all', 'correct', 'wrong'] as const).map(f => (
                <button key={f} type="button"
                  className={`result-filter-btn ${filter === f ? 'active' : ''}`}
                  onClick={() => setFilter(f)}>
                  {f === 'all' ? `Toutes (${detailedResult.questions.length})`
                    : f === 'correct' ? `✅ Correctes (${detailedResult.questions.filter(q => q.is_correct).length})`
                    : `❌ Incorrectes (${detailedResult.questions.filter(q => !q.is_correct).length})`}
                </button>
              ))}
            </div>

            {/* Liste de questions */}
            <div className="result-questions-list">
              {filteredQuestions.map(q => (
                <div key={q.question_id} className={`result-q-item ${q.is_correct ? 'correct' : 'wrong'}`}>
                  <div className="result-q-head">
                    <span className="result-q-num">Q{q.number}</span>
                    <span className="result-q-cat">{q.category}</span>
                    <span className="result-q-icon">{q.is_correct ? '✅' : '❌'}</span>
                  </div>
                  <p className="result-q-text">{q.text}</p>
                  {q.given_answer && !q.is_correct && (
                    <p className="result-q-given">Votre réponse : <strong>{q.given_answer}</strong></p>
                  )}
                  {!q.is_correct && (
                    <p className="result-q-correct">Bonne réponse : <strong>{q.correct_answer}</strong></p>
                  )}
                  {q.explanation && (
                    <p className="result-q-expl">💡 {q.explanation}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {resultError && <p className="form-error" style={{marginTop: 12}}>{resultError}</p>}
      </div>
    </section>
  );
}
