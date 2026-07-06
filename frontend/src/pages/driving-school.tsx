// DrivingSchoolPage — CodeRoute Guinée
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
  registerSchoolCandidate, getMySchoolCandidates, type SchoolCandidateItem,
} from '../api';
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

export function DrivingSchoolPage() {
  const { currentUser } = useAuthSession();
  const isSchool = currentUser?.role === 'driving_school';

  const MOCK_STUDENTS = [
    { id:'1', name:'Mamadou Diallo',    score:32, sessions:8,  status:'en_cours',  progress:80 },
    { id:'2', name:'Fatoumata Camara',  score:28, sessions:5,  status:'risque',    progress:55 },
    { id:'3', name:'Alpha Bah',         score:38, sessions:12, status:'pret',      progress:95 },
    { id:'4', name:'Mariam Soumah',     score:35, sessions:9,  status:'pret',      progress:88 },
    { id:'5', name:'Ibrahima Kouyaté',  score:22, sessions:3,  status:'debutant',  progress:30 },
    { id:'6', name:'Kadiatou Sylla',    score:30, sessions:6,  status:'en_cours',  progress:65 },
  ];

  const pret = MOCK_STUDENTS.filter(s=>s.status==='pret').length;
  const risque = MOCK_STUDENTS.filter(s=>s.status==='risque').length;

  return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div className="page-header">
        <span className="eyebrow">Portail Auto-École</span>
        <h1>Tableau de bord pédagogique</h1>
        <p>Suivez les progrès de vos élèves et identifiez ceux qui ont besoin d'aide.</p>
      </div>

      {!isSchool && (
        <div className="alert aw" style={{ marginBottom: 20 }}>
           Mode démonstration — Connectez-vous avec un compte auto-école pour voir vos élèves réels.
        </div>
      )}

      {isSchool && <SchoolCandidatesPanel />}

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card s-blue">
          <div className="stat-label">Élèves inscrits</div>
          <div className="stat-value">{MOCK_STUDENTS.length}</div>
        </div>
        <div className="stat-card s-green">
          <div className="stat-label">Prêts pour l'examen</div>
          <div className="stat-value">{pret}</div>
          <div className="stat-sub">score ≥ 35/40</div>
        </div>
        <div className="stat-card s-red">
          <div className="stat-label">Nécessitent de l'aide</div>
          <div className="stat-value">{risque}</div>
          <div className="stat-sub">score &lt; 28/40</div>
        </div>
        <div className="stat-card s-gold">
          <div className="stat-label">Score moyen</div>
          <div className="stat-value">{Math.round(MOCK_STUDENTS.reduce((s,e)=>s+e.score,0)/MOCK_STUDENTS.length)}</div>
          <div className="stat-sub">sur 40</div>
        </div>
      </div>

      {/* Tableau élèves */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">👥 Suivi individuel des élèves</span>
          <a href="#/training"><button className="secondary-button btn-sm">+ Affecter des exercices</button></a>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Élève</th>
                <th>Sessions</th>
                <th>Score moyen</th>
                <th>Progression</th>
                <th>Statut</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_STUDENTS.map(s => (
                <tr key={s.id}>
                  <td style={{ fontWeight: 600 }}>{s.name}</td>
                  <td>{s.sessions} séances</td>
                  <td>
                    <span style={{ fontWeight: 700, color: s.score >= 35 ? 'var(--green)' : s.score >= 30 ? 'var(--gold)' : 'var(--red)' }}>
                      {s.score}/40
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ flex: 1, height: 6, background: 'var(--border)', borderRadius: 99, overflow: 'hidden' }}>
                        <div style={{ height: '100%', background: s.progress >= 80 ? 'var(--green)' : s.progress >= 60 ? 'var(--gold)' : 'var(--red)', width: `${s.progress}%`, borderRadius: 'inherit' }} />
                      </div>
                      <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)', minWidth: 32 }}>{s.progress}%</span>
                    </div>
                  </td>
                  <td>
                    <span className={`badge ${s.status==='pret'?'bg':s.status==='risque'?'br':s.status==='en_cours'?'bb':'bgr'}`}>
                      {s.status==='pret' ? ' Prêt' : s.status==='risque' ? ' Risque' : s.status==='en_cours' ? ' En cours' : '🆕 Débutant'}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="secondary-button btn-sm" style={{ fontSize: 11 }}> Rapport</button>
                      {s.status === 'risque' && (
                        <button className="btn-sm btn-gold" style={{ fontSize: 11 }}>📞 Contacter</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recommandations */}
      {risque > 0 && (
        <div className="alert aw">
           <strong>{risque} élève(s) en difficulté</strong> — Leur score moyen est inférieur à 28/40.
          Planifiez des sessions supplémentaires sur les catégories Priorités et Signalisation.
        </div>
      )}

      <div className="g2">
        <div className="card">
          <div className="card-header"><span className="card-title">📅 Prochaines sessions</span></div>
          <div style={{ display: 'grid', gap: 10 }}>
            {[
              { date: '22/06/2026', time: '09h00', students: 4, center: 'CTR-KALOUM' },
              { date: '25/06/2026', time: '14h00', students: 3, center: 'CTR-MATAM' },
              { date: '28/06/2026', time: '09h00', students: 5, center: 'CTR-KALOUM' },
            ].map((s, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', background: 'var(--bg)', borderRadius: 'var(--r)', fontSize: 13 }}>
                <div style={{ textAlign: 'center', minWidth: 48 }}>
                  <div style={{ fontWeight: 800, color: 'var(--ink)' }}>{s.date.split('/')[0]}</div>
                  <div style={{ fontSize: 10, color: 'var(--muted)' }}>{s.date.split('/')[1]+'/'+s.date.split('/')[2]}</div>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600 }}>{s.time} — {s.center}</div>
                  <div style={{ color: 'var(--muted)', fontSize: 12 }}>{s.students} élèves inscrits</div>
                </div>
                <span className="badge bb">{s.students} candidats</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-header"><span className="card-title"> Actions rapides</span></div>
          <div style={{ display: 'grid', gap: 10 }}>
            <button className="secondary-button btn-block" style={{ justifyContent: 'flex-start', gap: 10 }}>
              ➕ Inscrire un nouvel élève
            </button>
            <button className="secondary-button btn-block" style={{ justifyContent: 'flex-start', gap: 10 }}>
               Importer liste (CSV)
            </button>
            <button className="secondary-button btn-block" style={{ justifyContent: 'flex-start', gap: 10 }}>
               Rapport mensuel PDF
            </button>
            <button className="secondary-button btn-block" style={{ justifyContent: 'flex-start', gap: 10 }}>
              📅 Réserver des sessions examen
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

// ══════════════════════════════════════════════════════════════════
// MINISTERIAL PAGE — Portail ministériel (Mois 13–18)
// Accessible depuis AdminPage onglet "Ministère"
// ══════════════════════════════════════════════════════════════════


// ── Inscription et suivi des candidats de l'auto-école ────────────────────
function SchoolCandidatesPanel() {
  const [items, setItems] = useState<SchoolCandidateItem[]>([]);
  const [total, setTotal] = useState(0);
  const [form, setForm] = useState({
    first_name: '', last_name: '', phone: '', identity_number: '',
    permit_category: 'B', email: '', password: '',
  });
  const [msg, setMsg] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  const load = () => {
    getMySchoolCandidates()
      .then(r => { setItems(r.items); setTotal(r.total); })
      .catch(() => undefined);
  };
  useEffect(load, []);

  const wantsLogin = form.email.trim().length > 0;
  const valid =
    form.first_name.trim().length >= 2 &&
    form.last_name.trim().length >= 2 &&
    form.phone.trim().length >= 8 &&
    form.identity_number.trim().length >= 3 &&
    (!wantsLogin || form.password.length >= 8);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!valid || saving) return;
    setSaving(true); setMsg(null);
    try {
      const r = await registerSchoolCandidate({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        phone: form.phone.trim(),
        identity_number: form.identity_number.trim(),
        permit_category: form.permit_category,
        email: wantsLogin ? form.email.trim() : undefined,
        password: wantsLogin ? form.password : undefined,
      });
      setMsg(`Candidat inscrit — référence : ${r.candidate_reference}`);
      setForm({ first_name: '', last_name: '', phone: '', identity_number: '', permit_category: 'B', email: '', password: '' });
      load();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : 'Inscription impossible.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="g2" style={{ marginBottom: 24, alignItems: 'start' }}>
      <div className="card">
        <div className="card-header"><span className="card-title">Inscrire un candidat</span></div>
        <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 12 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <label>Prénom<input value={form.first_name} onChange={set('first_name')} autoComplete="off" /></label>
            <label>Nom<input value={form.last_name} onChange={set('last_name')} autoComplete="off" /></label>
          </div>
          <label>Téléphone<input value={form.phone} onChange={set('phone')} autoComplete="off" placeholder="+224 6XX XX XX XX" /></label>
          <label>Numéro d'identité<input value={form.identity_number} onChange={set('identity_number')} autoComplete="off" /></label>
          <label>Catégorie
            <select value={form.permit_category} onChange={set('permit_category')}>
              <option value="A">A — Moto</option>
              <option value="B">B — Voiture</option>
              <option value="C">C — Poids lourd</option>
              <option value="D">D — Transport en commun</option>
              <option value="E">E — Remorque</option>
            </select>
          </label>
          <div style={{ borderTop: '1px solid var(--line)', paddingTop: 12 }}>
            <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>
              Optionnel : créer un accès de connexion pour l'élève
            </p>
            <label>Email (optionnel)<input type="email" value={form.email} onChange={set('email')} autoComplete="off" /></label>
            {wantsLogin && (
              <label style={{ marginTop: 8, display: 'block' }}>Mot de passe (8 car. min.)
                <input type="password" value={form.password} onChange={set('password')} autoComplete="new-password" />
              </label>
            )}
          </div>
          {msg && <p style={{ fontSize: 13 }}>{msg}</p>}
          <button type="submit" className="btn-primary" disabled={saving || !valid}>
            {saving ? 'Inscription…' : 'Inscrire le candidat'}
          </button>
        </form>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Mes candidats ({total})</span>
          <button className="btn-sm btn-outline" onClick={load}>Actualiser</button>
        </div>
        {items.length === 0 ? (
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>Aucun candidat inscrit pour le moment.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Candidat</th><th>Référence</th><th>Cat.</th><th>Statut</th><th>Résultat</th><th>Accès</th></tr></thead>
              <tbody>
                {items.map(i => (
                  <tr key={i.id}>
                    <td>{i.first_name} {i.last_name}<br/><span style={{ fontSize: 11, color: 'var(--muted)' }}>{i.phone}</span></td>
                    <td><code style={{ fontSize: 11 }}>{i.reference}</code></td>
                    <td>{i.permit_category}</td>
                    <td>{i.status}</td>
                    <td>
                      {i.last_result ? (
                        <span style={{ fontWeight: 700, color: i.last_result.passed ? 'var(--guinea-green)' : 'var(--red)' }}>
                          {i.last_result.passed ? 'ADMIS' : 'AJOURNÉ'} {i.last_result.score != null ? `(${i.last_result.score}/40)` : ''}
                        </span>
                      ) : <span style={{ color: 'var(--muted)' }}>—</span>}
                    </td>
                    <td>{i.has_login ? 'Oui' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
