// AdminPage — CodeRoute Guinée
import { LiveDashboard } from '../components/live-dashboard';
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

export function AdminPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const canAdmin = canUseProtectedActions(currentUser, isPresentationMode, ['admin','super_admin']);
  const canSA = canUseProtectedActions(currentUser, isPresentationMode, ['super_admin']);

  const [tab, setTab] = useState<'dashboard'|'candidates'|'payments'|'monitoring'|'questions'|'audit'|'users'>('dashboard');
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [examSum, setExamSum] = useState<ExamSummary | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [candidatesTotal, setCandidatesTotal] = useState(0);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  const [candPage, setCandPage] = useState(0);
  const [candLimit, setCandLimit] = useState(20);
  const [candSearch, setCandSearch] = useState('');
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditPage, setAuditPage] = useState(0);
  const [auditSearch, setAuditSearch] = useState('');
  const [users, setUsers] = useState<InstitutionalUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  // Création utilisateur
  const [newEmail, setNewEmail] = useState('');
  const [newName, setNewName] = useState('');
  const [newRole, setNewRole] = useState('admin');
  const [newPass, setNewPass] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    getDashboard().then(setDashboard).catch(() => undefined);
    getExamSummary().then(setExamSum).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (tab === 'candidates') {
      setCandidatesLoading(true);
      getCandidates({ limit: candLimit, offset: candPage * candLimit, search: candSearch })
        .then(data => { setCandidates(data.items); setCandidatesTotal(data.total); })
        .catch(() => undefined)
        .finally(() => setCandidatesLoading(false));
    }
    if (tab === 'audit') {
      setAuditLoading(true);
      getAuditLogs({ limit: 100, action: undefined, entity: undefined })
        .then(data => { setAuditLogs(data); setAuditTotal(data.length); })
        .catch(() => undefined)
        .finally(() => setAuditLoading(false));
    }
    if (tab === 'users') getInstitutionalUsers().then(setUsers).catch(() => undefined);
  }, [tab, candPage, candLimit, candSearch]);

  async function handleCreateUser(e: FormEvent) {
    e.preventDefault();
    setCreating(true); setMsg(null);
    try {
      await createInstitutionalUser({ email: newEmail, full_name: newName, role: newRole, initial_password: newPass, reason: 'Création par super_admin' });
      setMsg(' Utilisateur créé.');
      setNewEmail(''); setNewName(''); setNewPass('');
      getInstitutionalUsers().then(setUsers).catch(() => undefined);
    } catch (err) {
      setMsg(' ' + errMsg(err, 'Création échouée.'));
    } finally { setCreating(false); }
  }

  const TABS = [
    { id: 'dashboard',  label: ' Dashboard' },
    { id: 'candidates', label: 'Candidats' },
    { id: 'payments',   label: ' Paiements' },
    { id: 'monitoring', label: 'Monitoring' },
    { id: 'questions',  label: 'Questions' },
    { id: 'audit',      label: ' Audit' },
    { id: 'users',      label: ' Utilisateurs' },
  ] as const;

  return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div className="page-header">
        <span className="eyebrow">Administration</span>
        <h1>Tableau de bord national</h1>
        <p>Vue d'ensemble et gestion de la plateforme CodeRoute Guinée.</p>
      </div>

      {/* Live Dashboard — données temps réel, polling 15s */}
      <div className="card" style={{ marginBottom: 20 }}>
        <LiveDashboard />
      </div>

      {!canAdmin && (
        <div className="alert aw">Connectez-vous avec un compte admin ou super_admin pour accéder aux données réelles.</div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, flexWrap: 'wrap' }}>
        {TABS.map(t => (
          <button key={t.id} type="button"
            className={tab === t.id ? 'btn-primary btn-sm' : 'secondary-button btn-sm'}
            onClick={() => setTab(t.id as typeof tab)}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Dashboard tab */}
      {tab === 'dashboard' && (
        <>
          {dashboard && (
            <div className="stats-grid">
              <div className="stat-card s-blue"><div className="stat-label">Candidats</div><div className="stat-value">{fmt(dashboard.candidates)}</div></div>
              <div className="stat-card s-green"><div className="stat-label">Centres agréés</div><div className="stat-value">{fmt(dashboard.accredited_centers)}</div></div>
              <div className="stat-card s-gold"><div className="stat-label">Sessions</div><div className="stat-value">{fmt(dashboard.exam_sessions)}</div></div>
              <div className="stat-card s-red"><div className="stat-label">Alertes fraude</div><div className="stat-value">{fmt(dashboard.fraud_alerts)}</div></div>
            </div>
          )}
          {examSum && (
            <div className="g2">
              <div className="card">
                <div className="card-header"><span className="card-title">Examens</span></div>
                <div className="stats-grid" style={{ marginBottom: 0 }}>
                  <div><div className="stat-label">Total</div><div className="stat-value">{fmt(examSum.total_attempts)}</div></div>
                  <div><div className="stat-label">Admis</div><div className="stat-value" style={{ color: 'var(--green)' }}>{fmt(examSum.passed_attempts)}</div></div>
                  <div><div className="stat-label">Ajournés</div><div className="stat-value" style={{ color: 'var(--red)' }}>{fmt(examSum.failed_attempts)}</div></div>
                  <div><div className="stat-label">Score moy.</div><div className="stat-value">{examSum.average_score}<span style={{ fontSize: 14, fontWeight: 500 }}>/40</span></div></div>
                </div>
              </div>
              <div className="card">
                <div className="card-header"><span className="card-title">Exports</span></div>
                <div className="actions">
                  <button className="secondary-button btn-sm" onClick={() => downloadDashboardCsv().catch(() => undefined)}>⬇ Dashboard CSV</button>
                  <button className="secondary-button btn-sm" onClick={() => downloadAuditLogsCsv().catch(() => undefined)}>⬇ Audit CSV</button>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Candidats tab */}
      {tab === 'candidates' && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">Candidats</span>
            <SearchBar
              value={candSearch}
              onChange={s => { setCandSearch(s); }}
              placeholder="Rechercher un candidat…"
            />
            <button className="secondary-button btn-sm" onClick={() => getCandidates({ limit: candLimit, offset: candPage * candLimit, search: candSearch }).then(r => { setCandidates(r.items); setCandidatesTotal(r.total); }).catch(() => undefined)}>Actualiser</button>
          </div>
          {candidates.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px', color: 'var(--muted)' }}>
              {canAdmin ? 'Chargement…' : 'Connectez-vous pour voir les candidats.'}
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Référence</th><th>Nom</th><th>Prénom</th><th>Téléphone</th><th>Catégorie</th><th>Statut</th></tr></thead>
                <tbody>
                  {candidates.map(c => (
                    <tr key={c.id}>
                      <td><code style={{ fontSize: 11 }}>{c.reference}</code></td>
                      <td>{c.last_name}</td>
                      <td>{c.first_name}</td>
                      <td>{c.phone}</td>
                      <td><span className="badge bb">Cat. {c.permit_category}</span></td>
                      <td><span className={`badge ${c.status === 'active' ? 'bg' : 'bgr'}`}>{c.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <PaginationBar
            total={candidatesTotal || candidates.length}
            limit={candLimit}
            offset={candPage * candLimit}
            search={candSearch}
            onPage={(off) => setCandPage(Math.floor(off / candLimit))}
            onSearch={(s) => { setCandSearch(s); setCandPage(0); }}
            onLimit={(l) => { setCandLimit(l); setCandPage(0); }}
            loading={candidatesLoading}
            searchPlaceholder="Rechercher un candidat…"
          />
        </div>
      )}

      {/* Paiements tab */}
      {tab === 'payments' && <PaymentsPanel canAdmin={canAdmin} />}

      {/* Audit logs tab */}
      {tab === 'audit' && (
        <div className="card">
          <div className="card-header">
            <span className="card-title"> Audit logs</span>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <SearchBar
                value={auditSearch}
                onChange={s => setAuditSearch(s)}
                placeholder="Filtrer les logs…"
              />
              <button className="secondary-button btn-sm" onClick={() => downloadAuditLogsCsv().catch(() => undefined)}>⬇ CSV</button>
            </div>
          </div>
          {auditLogs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 32, color: 'var(--muted)' }}>
              {canAdmin ? 'Aucun log trouvé.' : 'Connectez-vous pour voir les logs.'}
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Date</th><th>Action</th><th>Entité</th><th>Détails</th></tr></thead>
                <tbody>
                  {auditLogs.slice(auditPage * 25, auditPage * 25 + 25).map((log, i) => (
                    <tr key={i}>
                      <td style={{ whiteSpace: 'nowrap' }}>{fmtDate(log.created_at)}</td>
                      <td><code style={{ fontSize: 11 }}>{log.action}</code></td>
                      <td>{log.entity}</td>
                      <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 11 }}>
                        {JSON.stringify(log.details).slice(0, 80)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <Pagination
                total={auditLogs.length}
                limit={25}
                offset={auditPage * 25}
                onPage={(off) => setAuditPage(Math.floor(off / 25))}
                loading={auditLoading}
              />
            </div>
          )}
        </div>
      )}

      {/* Monitoring tab */}
      {tab === 'monitoring' && <MonitoringPanel canAdmin={canAdmin} />}

      {/* Questions tab */}
      {tab === 'questions' && (
        <div style={{ display: 'grid', gap: 16 }}>
          <QuestionsPanel canAdmin={canAdmin} />
          <QuestionsAdminPanel canAdmin={canAdmin} />
        </div>
      )}

      {/* Users tab */}
      {tab === 'users' && (
        <div className="g2">
          {canSA && (
            <div className="card">
              <div className="card-header"><span className="card-title">Créer un utilisateur</span></div>
              <form onSubmit={handleCreateUser} style={{ display: 'grid', gap: 12 }}>
                <label>Nom complet<input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Prénom Nom" /></label>
                <label>Email<input type="email" value={newEmail} onChange={e => setNewEmail(e.target.value)} placeholder="agent@coderoute.gov.gn" /></label>
                <label>
                  Rôle
                  <select value={newRole} onChange={e => setNewRole(e.target.value)}>
                    <option value="admin">Admin national</option>
                    <option value="center">Chef de centre</option>
                  </select>
                </label>
                <label>Mot de passe temporaire<input type="password" value={newPass} onChange={e => setNewPass(e.target.value)} placeholder="12 caractères minimum" /></label>
                {msg && <p className={msg.startsWith('') ? 'login-status' : 'form-error'}>{msg}</p>}
                <button type="submit" className="btn-primary" disabled={creating || !newEmail || !newName || newPass.length < 12}>
                  {creating ? 'Création…' : 'Créer l\'utilisateur'}
                </button>
              </form>
            </div>
          )}
          <div className="card">
            <div className="card-header">
              <span className="card-title"> Comptes ({users.length})</span>
              <button className="secondary-button btn-sm" onClick={() => getInstitutionalUsers().then(setUsers).catch(() => undefined)}>Actualiser</button>
            </div>
            {users.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 32, color: 'var(--muted)' }}>
                {canAdmin ? 'Aucun utilisateur.' : 'Connectez-vous.'}
              </div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Nom</th><th>Email</th><th>Rôle</th><th>Statut</th></tr></thead>
                  <tbody>
                    {users.map(u => (
                      <tr key={u.id}>
                        <td>{u.full_name}</td>
                        <td style={{ fontSize: 12 }}>{u.email}</td>
                        <td><span className="badge bb">{u.role}</span></td>
                        <td><span className={`badge ${u.is_active ? 'bg' : 'bgr'}`}>{u.is_active ? 'Actif' : 'Inactif'}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

// ── Monitoring sub-panel ───────────────────────────────────────────
function MonitoringPanel({ canAdmin }: { canAdmin: boolean }) {
  const [summaries, setSummaries] = useState<ExamMonitoringSummary[]>([]);
  const [events, setEvents] = useState<ExamMonitoringEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!canAdmin) { setLoading(false); return; }
    Promise.allSettled([
      getExamMonitoringSummaries({ limit: 20 }),
      getExamMonitoringEvents({ limit: 30 }),
    ]).then(([s, e]) => {
      if (s.status === 'fulfilled') setSummaries(s.value);
      if (e.status === 'fulfilled') setEvents(e.value);
    }).finally(() => setLoading(false));
  }, [canAdmin]);

  if (!canAdmin) return <div className="alert aw">Accès réservé aux administrateurs.</div>;

  return (
    <div className="g2">
      <div className="card">
        <div className="card-header">
          <span className="card-title">Résumés de monitoring ({summaries.length})</span>
          <button className="secondary-button btn-sm" aria-label="Actualiser le monitoring" onClick={() => getExamMonitoringSummaries({ limit: 20 }).then(setSummaries).catch(() => undefined)}>Actualiser</button>
        </div>
        {loading ? <p className="text-muted" style={{ padding: 16 }}>Chargement…</p> :
          summaries.length === 0 ? <div style={{ padding: '24px', textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>Aucune anomalie détectée </div> :
          <div className="table-wrap">
            <table>
              <thead><tr><th>Tentative</th><th>Risque</th><th>Anomalies</th><th>Statut</th></tr></thead>
              <tbody>
                {summaries.map((s, i) => (
                  <tr key={i}>
                    <td><code style={{ fontSize: 11 }}>{s.attempt_id?.slice(0,16)}…</code></td>
                    <td>
                      <span className={`badge ${((s as Record<string,unknown>)["max_risk_score"] as number ?? 0) > 70 ? 'br' : ((s as Record<string,unknown>)["max_risk_score"] as number ?? 0) > 40 ? 'bgo' : 'bg'}`}>
                        {((s as Record<string,unknown>)["max_risk_score"] as number) ?? 0}
                      </span>
                    </td>
                    <td>{((s as Record<string,unknown>)["anomaly_count"] as number) ?? 0}</td>
                    <td><span className="badge bgr">{((s as Record<string,unknown>)['review_status'] as string) ?? 'pending'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        }
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Événements récents ({events.length})</span>
          <button className="secondary-button btn-sm" aria-label="Télécharger export CSV" onClick={() => downloadExamAttemptsCsv().catch(() => undefined)}>⬇ Export</button>
        </div>
        {loading ? <p className="text-muted" style={{ padding: 16 }}>Chargement…</p> :
          events.length === 0 ? <div style={{ padding: '24px', textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>Aucun événement récent</div> :
          <div className="table-wrap">
            <table>
              <thead><tr><th>Événement</th><th>Score</th><th>Date</th></tr></thead>
              <tbody>
                {events.slice(0, 20).map((e, i) => (
                  <tr key={i}>
                    <td style={{ fontSize: 12 }}>{e.event_type}</td>
                    <td>
                      <span className={`badge ${(e.risk_score ?? 0) > 70 ? 'br' : (e.risk_score ?? 0) > 40 ? 'bgo' : 'bgr'}`}>
                        {e.risk_score ?? 0}
                      </span>
                    </td>
                    <td style={{ fontSize: 11, color: 'var(--muted)' }}>
                      {e.created_at ? fmtDate(e.created_at) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        }
      </div>
    </div>
  );
}

// ── Questions sub-panel ─────────────────────────────────────────────
function QuestionsPanel({ canAdmin }: { canAdmin: boolean }) {
  const [items, setItems] = useState<QuestionGovernanceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [deciding, setDeciding] = useState<string | null>(null);

  useEffect(() => {
    if (!canAdmin) { setLoading(false); return; }
    getQuestionGovernanceItems().then(setItems).catch(() => undefined).finally(() => setLoading(false));
  }, [canAdmin]);

  async function handleDecide(questionId: string, status: 'approved' | 'rejected', reason: string) {
    setDeciding(questionId);
    try {
      await decideQuestionGovernance(questionId, status, reason);
      getQuestionGovernanceItems().then(setItems).catch(() => undefined);
    } catch { /* silencieux */ }
    finally { setDeciding(null); }
  }

  if (!canAdmin) return <div className="alert aw">Accès réservé aux administrateurs.</div>;

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">Gouvernance des questions ({items.length})</span>
        <button className="secondary-button btn-sm" onClick={() => getQuestionGovernanceItems().then(setItems).catch(() => undefined)}>Actualiser</button>
      </div>
      {loading ? <p className="text-muted" style={{ padding: 16 }}>Chargement…</p> :
        items.length === 0 ? <div style={{ padding: '24px', textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>Toutes les questions sont validées </div> :
        <div className="table-wrap">
          <table>
            <thead><tr><th>Catégorie</th><th>Question</th><th>Statut</th><th>Actions</th></tr></thead>
            <tbody>
              {items.map(item => (
                <tr key={item.question_id}>
                  <td><span className="badge bb">{item.category}</span></td>
                  <td style={{ maxWidth: 300, fontSize: 13 }}>
                    {(item.text ?? '').slice(0, 80)}{(item.text ?? '').length > 80 ? '…' : ''}
                  </td>
                  <td>
                    <span className={`badge ${item.latest_status === 'approved' ? 'bg' : item.latest_status === 'rejected' ? 'br' : 'bgo'}`}>
                      {item.latest_status ?? 'pending'}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button className="btn-sm btn-success"
                        disabled={deciding === item.question_id || item.latest_status === 'approved'}
                        onClick={() => handleDecide(item.question_id, 'approved', 'Validée par admin')}>
                        
                      </button>
                      <button className="btn-sm btn-danger"
                        disabled={deciding === item.question_id || item.latest_status === 'rejected'}
                        onClick={() => handleDecide(item.question_id, 'rejected', 'Rejetée par admin')}>
                        
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      }
    </div>
  );
}

// ── Payments sub-panel ────────────────────────────────────────────
function PaymentsPanel({ canAdmin }: { canAdmin: boolean }) {
  const [items, setItems] = useState<import('../api').PaymentReconciliationItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPaymentReconciliationItems({}).then(setItems).catch(() => undefined).finally(() => setLoading(false));
  }, []);

  return (
    <div className="card">
      <div className="card-header"><span className="card-title"> Paiements</span></div>
      {loading ? (
        <div style={{ textAlign: 'center', padding: 32, color: 'var(--muted)' }}>Chargement…</div>
      ) : items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 32, color: 'var(--muted)' }}>
          {canAdmin ? 'Aucun paiement trouvé.' : 'Connectez-vous pour voir les paiements.'}
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Référence</th><th>Réservation</th><th>Montant</th><th>Provider</th><th>Statut</th></tr></thead>
            <tbody>
              {items.slice(0, 50).map(p => (
                <tr key={p.reference}>
                  <td><code style={{ fontSize: 11 }}>{p.reference}</code></td>
                  <td style={{ fontSize: 12 }}>{p.booking_reference}</td>
                  <td>{fmtGNF(p.amount_gnf)}</td>
                  <td>{p.provider}</td>
                  <td><span className={`badge ${p.status === 'paid' ? 'bg' : p.status === 'pending' ? 'bgo' : 'br'}`}>{p.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// INSTITUTIONAL DOSSIER PAGE
// ══════════════════════════════════════════════════════════════════
