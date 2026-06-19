// AdminPage — CodeRoute Guinée
// Extrait de src/pages.tsx L1218-L3113
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

export function AdminPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const canAdminAct = canUseProtectedActions(currentUser, isPresentationMode, ['admin', 'super_admin']);
  const canSuperAdminAct = canUseProtectedActions(currentUser, isPresentationMode, ['super_admin']);
  const [dashboard, setDashboard] = useState<DashboardData>(fallbackDashboard);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [candidateImportSource, setCandidateImportSource] = useState('Registre national pilote');
  const [candidateImportReason, setCandidateImportReason] = useState('Chargement officiel des candidats pilotes');
  const [candidateImportCsv, setCandidateImportCsv] = useState('Mamadou;Diallo;GN-ID-2026-0001;+224620000001;B;registered');
  const [candidateImportDryRun, setCandidateImportDryRun] = useState(true);
  const [candidateImportStatus, setCandidateImportStatus] = useState<string | null>(null);
  const [centers, setCenters] = useState<Center[]>([]);
  const [centerStatus, setCenterStatus] = useState<string | null>(null);
  const [centerImportSource, setCenterImportSource] = useState('Liste officielle DNTT');
  const [centerImportReason, setCenterImportReason] = useState('Chargement officiel des centres pilotes');
  const [centerImportCsv, setCenterImportCsv] = useState('CRG-CONAKRY-002;Centre officiel Conakry 2;Conakry;Matoto;30;pending_audit');
  const [centerImportDryRun, setCenterImportDryRun] = useState(true);
  const [centerStations, setCenterStations] = useState<CenterStation[]>([]);
  const [centerStationStatus, setCenterStationStatus] = useState<string | null>(null);
  const [centerStationForm, setCenterStationForm] = useState<CenterStationPayload>({
    center_id: '',
    device_key: 'CTR-KALOUM-POSTE-12',
    label: 'Poste examen 12',
    room: 'Salle A',
    status: 'active',
  });
  const [entrySummary, setEntrySummary] = useState<EntrySummary>(fallbackEntrySummary);
  const [examSummary, setExamSummary] = useState<ExamSummary>(fallbackExamSummary);
  const [paymentSummary, setPaymentSummary] = useState<PaymentSummary>(fallbackPaymentSummary);
  const [paymentItems, setPaymentItems] = useState<PaymentReconciliationItem[]>(fallbackPaymentItems);
  const [paymentAlerts, setPaymentAlerts] = useState<PaymentAlert[]>(fallbackPaymentAlerts);
  const [centerIncidents, setCenterIncidents] = useState<CenterIncident[]>(fallbackCenterIncidents);
  const [incidentResolutionNotes, setIncidentResolutionNotes] = useState('Incident analyse par la supervision nationale. Reprise autorisee si necessaire.');
  const [allowIncidentRetake, setAllowIncidentRetake] = useState(true);
  const [incidentAdminStatus, setIncidentAdminStatus] = useState<string | null>(null);
  const [identityChecks, setIdentityChecks] = useState<CandidateIdentityCheck[]>(fallbackIdentityChecks);
  const [identityStatus, setIdentityStatus] = useState<string | null>(null);
  const [identityFilters, setIdentityFilters] = useState<CandidateIdentityFilters>({ status_filter: 'pending', limit: 25 });
  const [activeIdentityFilters, setActiveIdentityFilters] = useState<CandidateIdentityFilters>({ status_filter: 'pending', limit: 25 });
  const [candidateSubmissions, setCandidateSubmissions] = useState<CandidateSubmission[]>(fallbackCandidateSubmissions);
  const [submissionFilters, setSubmissionFilters] = useState<CandidateSubmissionFilters>({ status_filter: 'submitted', limit: 25 });
  const [activeSubmissionFilters, setActiveSubmissionFilters] = useState<CandidateSubmissionFilters>({ status_filter: 'submitted', limit: 25 });
  const [submissionAdminResponse, setSubmissionAdminResponse] = useState('Votre demande est prise en charge par la supervision nationale.');
  const [submissionAdminStatus, setSubmissionAdminStatus] = useState<string | null>(null);
  const [questionGovernance, setQuestionGovernance] = useState<QuestionGovernanceItem[]>(fallbackQuestionGovernance);
  const [questionGovernanceStatus, setQuestionGovernanceStatus] = useState<string | null>(null);
  const [questionImportSource, setQuestionImportSource] = useState('Commission nationale du code');
  const [questionImportReason, setQuestionImportReason] = useState('Chargement officiel de la banque pilote');
  const [questionImportCsv, setQuestionImportCsv] = useState('signalisation;Que signifie un feu rouge fixe ?;S arreter|Passer avec prudence|Accelerer;S arreter;Le feu rouge impose l arret.;true;image;https://cdn.coderoute.gov.gn/exam/images/feu-rouge.jpg;Illustration feu rouge');
  const [questionImportDryRun, setQuestionImportDryRun] = useState(true);
  const [institutionalAuthorizations, setInstitutionalAuthorizations] = useState<InstitutionalAuthorization[]>(fallbackInstitutionalAuthorizations);
  const [authorizationStatus, setAuthorizationStatus] = useState<string | null>(null);
  const [authorizationForm, setAuthorizationForm] = useState<InstitutionalAuthorizationPayload>({
    authority: 'Ministere des Transports',
    reference: 'MT-CODE-2026-001',
    title: 'Convention pilote CodeRoute Guinee',
    scope: 'Autorisation pilote pour la digitalisation des examens du code de la route.',
  });
  const [institutionalReadiness, setInstitutionalReadiness] = useState<InstitutionalReadiness>(fallbackInstitutionalReadiness);
  const [institutionalUsers, setInstitutionalUsers] = useState<InstitutionalUser[]>(fallbackInstitutionalUsers);
  const [userGovernanceStatus, setUserGovernanceStatus] = useState<string | null>(null);
  const [userForm, setUserForm] = useState<InstitutionalUserCreatePayload>({
    email: 'agent.centre@coderoute.gov.gn',
    full_name: 'Agent Centre Agree',
    initial_password: 'TemporaryPass123',
    role: 'center',
    reason: 'Creation officielle du compte institutionnel',
  });
  const [passwordResetValue, setPasswordResetValue] = useState('ResetStrongPass123');
  const [institutionalActionCenter, setInstitutionalActionCenter] = useState<InstitutionalActionCenter>(fallbackInstitutionalActionCenter);
  const [actionCenterStatus, setActionCenterStatus] = useState<string | null>(null);
  const [operationsSummary, setOperationsSummary] = useState<OperationsSummary>(fallbackOperationsSummary);
  const [operationsStatus, setOperationsStatus] = useState<string | null>(null);
  const [institutionalReport, setInstitutionalReport] = useState<InstitutionalReport>(fallbackInstitutionalReport);
  const [institutionalReportStatus, setInstitutionalReportStatus] = useState<string | null>(null);
  const [readinessStatus, setReadinessStatus] = useState<string | null>(null);
  const [paymentFilters, setPaymentFilters] = useState<PaymentFilters>({});
  const [activePaymentFilters, setActivePaymentFilters] = useState<PaymentFilters>({});
  const [paymentImportSource, setPaymentImportSource] = useState('Orange Money');
  const [paymentImportReason, setPaymentImportReason] = useState('Rapprochement officiel quotidien');
  const [paymentImportCsv, setPaymentImportCsv] = useState('GN-BOOK-2026-000001;250000;orange_money;+224620000001;paid;OM-RECU-000001');
  const [paymentImportDryRun, setPaymentImportDryRun] = useState(true);
  const [paymentImportStatus, setPaymentImportStatus] = useState<string | null>(null);
  const [auditFilters, setAuditFilters] = useState<AuditLogFilters>({});
  const [activeAuditFilters, setActiveAuditFilters] = useState<AuditLogFilters>({});
  const [monitoringFilters, setMonitoringFilters] = useState<ExamMonitoringFilters>({ min_risk_score: 1, limit: 25 });
  const [activeMonitoringFilters, setActiveMonitoringFilters] = useState<ExamMonitoringFilters>({ min_risk_score: 1, limit: 25 });
  const [monitoringSummaries, setMonitoringSummaries] = useState<ExamMonitoringSummary[]>(fallbackMonitoringSummaries);
  const [monitoringEvents, setMonitoringEvents] = useState<ExamMonitoringEvent[]>(fallbackMonitoringEvents);
  const [deviceSessionAlerts, setDeviceSessionAlerts] = useState<DeviceSession[]>(fallbackDeviceSessionAlerts);
  const [monitoringStatus, setMonitoringStatus] = useState<string | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>(fallbackAuditLogs);
  const [auditStatus, setAuditStatus] = useState<string | null>(null);
  const [financeStatus, setFinanceStatus] = useState<string | null>(null);
  const [csvExportStatus, setCsvExportStatus] = useState<string | null>(null);
  const [examCsvExportStatus, setExamCsvExportStatus] = useState<string | null>(null);
  const [paymentCsvExportStatus, setPaymentCsvExportStatus] = useState<string | null>(null);
  const [auditCsvExportStatus, setAuditCsvExportStatus] = useState<string | null>(null);
  const [isExportingInstitutionalReport, setIsExportingInstitutionalReport] = useState(false);
  const [isExportingInstitutionalReportPdf, setIsExportingInstitutionalReportPdf] = useState(false);
  const [isExportingCsv, setIsExportingCsv] = useState(false);
  const [isExportingExamCsv, setIsExportingExamCsv] = useState(false);
  const [isExportingPaymentCsv, setIsExportingPaymentCsv] = useState(false);
  const [isExportingAuditCsv, setIsExportingAuditCsv] = useState(false);

  function blockProtectedAction(setStatus: (value: string) => void, superAdminOnly = false): boolean {
    if (superAdminOnly ? canSuperAdminAct : canAdminAct) {
      return false;
    }
    setStatus(superAdminOnly
      ? 'Action protegee : connectez-vous avec un compte super admin reel.'
      : 'Action protegee : connectez-vous avec un compte admin ou super admin reel.');
    return true;
  }

  async function refreshCenterIncidents() {
    if (!canAdminAct) {
      setCenterIncidents(fallbackCenterIncidents);
      setIncidentAdminStatus('Apercu presentation charge : incidents ouverts simulés, sans action officielle.');
      return;
    }
    try {
      const incidents = await getCenterIncidents('open', 25);
      setCenterIncidents(incidents);
      setIncidentAdminStatus(null);
    } catch {
      setIncidentAdminStatus('Incidents indisponibles : connectez-vous avec un role admin ou super admin.');
    }
  }

  async function loadPaymentSummary(filters: PaymentFilters) {
    try {
      const cleanFilters = sanitizePaymentFilters(filters);
      if (!canAdminAct) {
        const demo = filterDemoPayments(cleanFilters);
        setPaymentSummary(demo.summary);
        setPaymentItems(demo.items);
        setPaymentAlerts(demo.alerts);
        setActivePaymentFilters(cleanFilters);
        setFinanceStatus('Apercu presentation : filtres financiers appliques sur donnees simulees.');
        return;
      }
      const summary = await getAdminPaymentSummary(cleanFilters);
      const items = await getPaymentReconciliationItems({ ...cleanFilters, limit: 25 });
      const alerts = await getPaymentAlerts({ ...cleanFilters, limit: 25 });
      setPaymentSummary(summary);
      setPaymentItems(items);
      setPaymentAlerts(alerts);
      setActivePaymentFilters(cleanFilters);
      setFinanceStatus(null);
    } catch {
      const demo = filterDemoPayments(sanitizePaymentFilters(filters));
      setPaymentSummary(demo.summary);
      setPaymentItems(demo.items);
      setPaymentAlerts(demo.alerts);
      setActivePaymentFilters(sanitizePaymentFilters(filters));
      setFinanceStatus('Finance API indisponible : apercu presentation charge.');
    }
  }

  async function refreshIdentityChecks(filters: CandidateIdentityFilters = activeIdentityFilters) {
    if (!canAdminAct) {
      const cleanFilters = {
        status_filter: filters.status_filter || undefined,
        candidate_id: filters.candidate_id || undefined,
        limit: filters.limit ?? 25,
      };
      setIdentityChecks(filterDemoIdentityChecks(cleanFilters));
      setActiveIdentityFilters(cleanFilters);
      setIdentityStatus('Apercu presentation : filtres appliques aux pieces simulees.');
      return;
    }
    try {
      const cleanFilters = {
        status_filter: filters.status_filter || undefined,
        candidate_id: filters.candidate_id || undefined,
        limit: filters.limit ?? 25,
      };
      const checks = await getCandidateIdentityChecks(cleanFilters);
      setIdentityChecks(checks);
      setActiveIdentityFilters(cleanFilters);
      setIdentityStatus(null);
    } catch {
      setIdentityStatus('Pieces indisponibles : connectez-vous avec un role admin ou super admin.');
    }
  }

  async function refreshCandidateSubmissions(filters: CandidateSubmissionFilters = activeSubmissionFilters) {
    if (!canAdminAct) {
      const cleanFilters = {
        candidate_id: filters.candidate_id || undefined,
        attempt_id: filters.attempt_id || undefined,
        status_filter: filters.status_filter || undefined,
        limit: filters.limit ?? 25,
      };
      setCandidateSubmissions(filterDemoSubmissions(cleanFilters));
      setActiveSubmissionFilters(cleanFilters);
      setSubmissionAdminStatus('Apercu presentation : filtres appliques aux recours simules.');
      return;
    }
    try {
      const cleanFilters = {
        candidate_id: filters.candidate_id || undefined,
        attempt_id: filters.attempt_id || undefined,
        status_filter: filters.status_filter || undefined,
        limit: filters.limit ?? 25,
      };
      const items = await getCandidateSubmissions(cleanFilters);
      setCandidateSubmissions(items);
      setActiveSubmissionFilters(cleanFilters);
      setSubmissionAdminStatus(null);
    } catch {
      setSubmissionAdminStatus('Recours indisponibles : connectez-vous avec un role admin ou super admin.');
    }
  }

  async function refreshExamMonitoring(filters: ExamMonitoringFilters = activeMonitoringFilters) {
    if (!canAdminAct) {
      const cleanFilters = {
        attempt_id: filters.attempt_id || undefined,
        session_id: filters.session_id || undefined,
        severity: filters.severity || undefined,
        min_risk_score: filters.min_risk_score ?? 1,
        limit: filters.limit ?? 25,
      };
      const demo = filterDemoMonitoring(cleanFilters);
      setMonitoringSummaries(demo.summaries);
      setMonitoringEvents(demo.events);
      setDeviceSessionAlerts(demo.deviceAlerts);
      setActiveMonitoringFilters(cleanFilters);
      setMonitoringStatus('Apercu presentation : monitoring simule charge selon les filtres.');
      return;
    }
    try {
      const cleanFilters = {
        attempt_id: filters.attempt_id || undefined,
        session_id: filters.session_id || undefined,
        severity: filters.severity || undefined,
        min_risk_score: filters.min_risk_score ?? 1,
        limit: filters.limit ?? 25,
      };
      const summaries = await getExamMonitoringSummaries(cleanFilters);
      const events = await getExamMonitoringEvents(cleanFilters);
      const deviceAlerts = await getDeviceSessionAlerts({ session_id: cleanFilters.session_id, limit: 25 });
      setMonitoringSummaries(summaries);
      setMonitoringEvents(events);
      setDeviceSessionAlerts(deviceAlerts);
      setActiveMonitoringFilters(cleanFilters);
      setMonitoringStatus(null);
    } catch {
      setMonitoringStatus('Monitoring examen indisponible : connectez-vous avec un role admin ou super admin.');
    }
  }

  useEffect(() => {
    getDashboard().then(setDashboard).catch(() => undefined);
    getCandidates().then(setCandidates).catch(() => undefined);
    getCenters().then(setCenters).catch(() => undefined);
    getCenterStations({ limit: 25 }).then(setCenterStations).catch(() => undefined);
    getEntrySummary().then(setEntrySummary).catch(() => undefined);
    getExamSummary().then(setExamSummary).catch(() => undefined);
    loadPaymentSummary({});
    refreshCenterIncidents();
    getInstitutionalReadiness()
      .then((readiness) => {
        setInstitutionalReadiness(readiness);
        setReadinessStatus(null);
      })
      .catch(() => setReadinessStatus('Mode demo : connectez-vous avec un token admin pour charger le score institutionnel API.'));
    getInstitutionalReport()
      .then((report) => {
        setInstitutionalReport(report);
        setInstitutionalReportStatus(null);
      })
      .catch(() => setInstitutionalReportStatus('Mode demo : connectez-vous avec un token admin pour charger le rapport institutionnel API.'));
    getInstitutionalActionCenter()
      .then((actionCenter) => {
        setInstitutionalActionCenter(actionCenter.items.length > 0 ? actionCenter : fallbackInstitutionalActionCenter);
        setActionCenterStatus(null);
      })
      .catch(() => setActionCenterStatus('Mode demo : connectez-vous avec un role admin pour charger le centre d action API.'));
    getOperationsSummary()
      .then((summary) => {
        setOperationsSummary(summary);
        setOperationsStatus(null);
      })
      .catch(() => setOperationsStatus('Mode demo : connectez-vous avec un role admin pour charger le resume exploitation API.'));
    getCandidateIdentityChecks({ status_filter: 'pending', limit: 25 })
      .then((checks) => {
        setIdentityChecks(checks.length > 0 ? checks : fallbackIdentityChecks);
        setIdentityStatus(null);
      })
      .catch(() => setIdentityStatus('Mode demo : connectez-vous avec un role admin pour traiter les identites API.'));
    getCandidateSubmissions({ status_filter: 'submitted', limit: 25 })
      .then((items) => {
        setCandidateSubmissions(items);
        setSubmissionAdminStatus(null);
      })
      .catch(() => setSubmissionAdminStatus('Mode demo : connectez-vous avec un role admin pour traiter les recours API.'));
    getExamMonitoringSummaries({ min_risk_score: 1, limit: 25 })
      .then(setMonitoringSummaries)
      .catch(() => setMonitoringStatus('Mode demo : connectez-vous avec un role admin pour charger le monitoring examen API.'));
    getExamMonitoringEvents({ limit: 25 })
      .then(setMonitoringEvents)
      .catch(() => undefined);
    getDeviceSessionAlerts({ limit: 25 })
      .then(setDeviceSessionAlerts)
      .catch(() => undefined);
    getQuestionGovernanceItems()
      .then((items) => {
        setQuestionGovernance(items.length > 0 ? items : fallbackQuestionGovernance);
        setQuestionGovernanceStatus(null);
      })
      .catch(() => setQuestionGovernanceStatus('Mode demo : connectez-vous avec un role admin pour gouverner la banque de questions API.'));
    getInstitutionalAuthorizations()
      .then((items) => {
        setInstitutionalAuthorizations(items.length > 0 ? items : fallbackInstitutionalAuthorizations);
        setAuthorizationStatus(null);
      })
      .catch(() => setAuthorizationStatus('Mode demo : connectez-vous avec un role admin pour charger les habilitations API.'));
    getInstitutionalUsers()
      .then((users) => {
        setInstitutionalUsers(users.length > 0 ? users : fallbackInstitutionalUsers);
        setUserGovernanceStatus(null);
      })
      .catch(() => setUserGovernanceStatus('Mode demo : connectez-vous avec un role admin pour charger les comptes API.'));
    getAuditLogs()
      .then((logs) => {
        setAuditLogs(logs);
        setAuditStatus(null);
      })
      .catch(() => setAuditStatus('Logs indisponibles : connectez-vous avec un role admin ou super admin.'));
  }, []);

  async function handleResolveIncident(incidentId: string) {
    setIncidentAdminStatus(null);
    if (blockProtectedAction(setIncidentAdminStatus)) return;
    try {
      const resolved = await resolveCenterIncident(incidentId, incidentResolutionNotes, allowIncidentRetake);
      setCenterIncidents((current) => current.filter((incident) => incident.id !== resolved.id));
      setIncidentAdminStatus(`Incident ${resolved.id} resolu${resolved.new_attempt_id ? `, nouvelle tentative ${resolved.new_attempt_id}` : ''}.`);
      await refreshAuditLogs();
    } catch (error) {
      setIncidentAdminStatus(getActionErrorMessage(error, 'Resolution incident impossible.'));
    }
  }

  async function refreshAuditLogs(filters: AuditLogFilters = activeAuditFilters) {
    if (!canAdminAct) {
      const cleanFilters = {
        action: filters.action || undefined,
        entity: filters.entity || undefined,
        limit: filters.limit ?? 25,
      };
      setAuditLogs(filterDemoAuditLogs(cleanFilters));
      setActiveAuditFilters(cleanFilters);
      setAuditStatus('Apercu presentation : logs simules filtres localement.');
      return;
    }
    try {
      const cleanFilters = {
        action: filters.action || undefined,
        entity: filters.entity || undefined,
        limit: filters.limit ?? 25,
      };
      setAuditLogs(await getAuditLogs(cleanFilters));
      setActiveAuditFilters(cleanFilters);
      setAuditStatus(null);
    } catch {
      setAuditStatus('Logs indisponibles : connectez-vous avec un role admin ou super admin.');
    }
  }

  async function handleCenterStatus(centerId: string, status: string, reason: string) {
    setCenterStatus(null);
    if (blockProtectedAction(setCenterStatus)) return;
    try {
      const updatedCenter = await updateCenterStatus(centerId, status, reason);
      setCenters((current) => current.map((center) => (center.id === centerId ? updatedCenter : center)));
      setCenterStatus(`Statut du centre ${updatedCenter.code} mis a jour : ${updatedCenter.status}.`);
      await refreshAuditLogs();
      getDashboard().then(setDashboard).catch(() => undefined);
    } catch {
      setCenterStatus('Mise a jour du centre impossible : connectez-vous avec un role admin ou super admin.');
    }
  }

  async function handleOfficialCenterImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canAdminAct && centerImportDryRun) {
      try {
        const rows = parseCenterImportCsv(centerImportCsv);
        setCenterStatus(buildDemoImportStatus('centres officiels', rows.length));
      } catch (error) {
        setCenterStatus(error instanceof Error ? `Simulation centres impossible : ${error.message}` : 'Simulation centres impossible.');
      }
      return;
    }
    if (blockProtectedAction(setCenterStatus)) return;
    try {
      const rows = parseCenterImportCsv(centerImportCsv);
      const result = await importOfficialCenters(centerImportSource, centerImportReason, rows, centerImportDryRun);
      setCenterStatus(`${result.dry_run ? 'Simulation officielle terminee' : 'Import officiel termine'} : ${result.imported} centre(s), ${result.created} cree(s), ${result.updated} mis a jour.`);
      if (!result.dry_run) {
        const refreshedCenters = await getCenters();
        setCenters(refreshedCenters);
        await refreshAuditLogs();
      }
    } catch (error) {
      setCenterStatus(error instanceof Error ? `Import impossible : ${error.message}` : 'Import officiel impossible.');
    }
  }

  async function handleCenterStationSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCenterStationStatus(null);
    if (blockProtectedAction(setCenterStationStatus)) return;
    try {
      const created = await createCenterStation(centerStationForm);
      setCenterStations((current) => [created, ...current]);
      setCenterStationStatus(`Poste ${created.label} enregistre (${created.status}).`);
      await refreshAuditLogs();
    } catch {
      setCenterStationStatus('Creation poste impossible : verifiez le centre, la cle appareil et le role admin.');
    }
  }

  async function handleCenterStationStatus(stationId: string, status: 'active' | 'disabled' | 'maintenance') {
    setCenterStationStatus(null);
    if (blockProtectedAction(setCenterStationStatus)) return;
    try {
      const updated = await updateCenterStation(stationId, { status });
      setCenterStations((current) => current.map((station) => (station.id === stationId ? updated : station)));
      setCenterStationStatus(`Poste ${updated.label} : ${updated.status}.`);
      await refreshAuditLogs();
    } catch {
      setCenterStationStatus('Mise a jour poste impossible : connectez-vous avec un role admin ou super admin.');
    }
  }

  async function handleOfficialCandidateImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCandidateImportStatus(null);
    if (!canAdminAct && candidateImportDryRun) {
      try {
        const rows = parseCandidateImportCsv(candidateImportCsv);
        setCandidateImportStatus(buildDemoImportStatus('candidats officiels', rows.length));
      } catch (error) {
        setCandidateImportStatus(error instanceof Error ? `Simulation candidats impossible : ${error.message}` : 'Simulation candidats impossible.');
      }
      return;
    }
    if (blockProtectedAction(setCandidateImportStatus)) return;
    try {
      const rows = parseCandidateImportCsv(candidateImportCsv);
      const result = await importOfficialCandidates(candidateImportSource, candidateImportReason, rows, candidateImportDryRun);
      setCandidateImportStatus(`${result.dry_run ? 'Simulation candidats terminee' : 'Import candidats termine'} : ${result.imported} dossier(s), ${result.created} cree(s), ${result.updated} mis a jour.`);
      if (!result.dry_run) {
        const refreshedCandidates = await getCandidates();
        setCandidates(refreshedCandidates);
        await refreshAuditLogs();
        getDashboard().then(setDashboard).catch(() => undefined);
      }
    } catch (error) {
      setCandidateImportStatus(error instanceof Error ? `Import candidats impossible : ${error.message}` : 'Import candidats impossible.');
    }
  }

  async function handleIdentityDecision(checkId: string, status: string, reason: string) {
    setIdentityStatus(null);
    if (blockProtectedAction(setIdentityStatus)) return;
    try {
      const updatedCheck = await decideCandidateIdentity(checkId, status, reason);
      setIdentityChecks((current) => current.map((check) => (check.id === checkId ? updatedCheck : check)));
      setIdentityStatus(`Verification identite ${updatedCheck.document_reference} : ${updatedCheck.status}.`);
      await refreshIdentityChecks();
      await refreshAuditLogs();
    } catch {
      setIdentityStatus('Decision identite impossible : connectez-vous avec un role admin ou super admin.');
    }
  }

  async function handleSubmissionDecision(submissionId: string, status: string) {
    setSubmissionAdminStatus(null);
    if (blockProtectedAction(setSubmissionAdminStatus)) return;
    try {
      const updated = await handleCandidateSubmission(submissionId, status, submissionAdminResponse);
      setCandidateSubmissions((current) => current.map((item) => (item.id === submissionId ? updated : item)));
      setSubmissionAdminStatus(`Recours ${updated.id} : ${updated.status}.`);
      await refreshCandidateSubmissions();
      await refreshAuditLogs();
    } catch {
      setSubmissionAdminStatus('Decision recours impossible : verifiez la reponse admin et le role.');
    }
  }

  async function handleQuestionDecision(questionId: string, status: string, reason: string) {
    setQuestionGovernanceStatus(null);
    if (blockProtectedAction(setQuestionGovernanceStatus)) return;
    try {
      const updatedItem = await decideQuestionGovernance(questionId, status, reason);
      setQuestionGovernance((current) => current.map((item) => (item.question_id === questionId ? updatedItem : item)));
      setQuestionGovernanceStatus(`Question ${updatedItem.category} : ${updatedItem.latest_status}.`);
      await refreshAuditLogs();
      getDashboard().then(setDashboard).catch(() => undefined);
    } catch {
      setQuestionGovernanceStatus('Decision question impossible : connectez-vous avec un role admin ou super admin.');
    }
  }

  async function handleOfficialQuestionImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setQuestionGovernanceStatus(null);
    if (!canAdminAct && questionImportDryRun) {
      try {
        const rows = parseQuestionImportCsv(questionImportCsv);
        setQuestionGovernanceStatus(buildDemoImportStatus('questions officielles', rows.length));
      } catch (error) {
        setQuestionGovernanceStatus(error instanceof Error ? `Simulation questions impossible : ${error.message}` : 'Simulation questions impossible.');
      }
      return;
    }
    if (blockProtectedAction(setQuestionGovernanceStatus)) return;
    try {
      const rows = parseQuestionImportCsv(questionImportCsv);
      const result = await importOfficialQuestions(questionImportSource, questionImportReason, rows, questionImportDryRun);
      setQuestionGovernanceStatus(`${result.dry_run ? 'Simulation questions terminee' : 'Import questions termine'} : ${result.imported} question(s), ${result.created} creee(s), ${result.updated} mise(s) a jour.`);
      if (!result.dry_run) {
        const refreshedQuestions = await getQuestionGovernanceItems();
        setQuestionGovernance(refreshedQuestions);
        await refreshAuditLogs();
        getDashboard().then(setDashboard).catch(() => undefined);
      }
    } catch (error) {
      setQuestionGovernanceStatus(error instanceof Error ? `Import questions impossible : ${error.message}` : 'Import questions impossible.');
    }
  }

  async function handleAuthorizationSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthorizationStatus(null);
    if (blockProtectedAction(setAuthorizationStatus)) return;
    try {
      const created = await createInstitutionalAuthorization(authorizationForm);
      setInstitutionalAuthorizations((current) => [created, ...current]);
      setAuthorizationStatus(`Habilitation ${created.reference} creee en statut ${created.status}.`);
      await refreshAuditLogs();
    } catch {
      setAuthorizationStatus('Creation habilitation impossible : verifiez la reference et le role admin.');
    }
  }

  async function handleAuthorizationStatus(authorizationId: string, status: string, reason: string) {
    setAuthorizationStatus(null);
    if (blockProtectedAction(setAuthorizationStatus)) return;
    try {
      const updated = await updateInstitutionalAuthorizationStatus(authorizationId, status, reason);
      setInstitutionalAuthorizations((current) => current.map((item) => (item.id === authorizationId ? updated : item)));
      setAuthorizationStatus(`Habilitation ${updated.reference} : ${updated.status}.`);
      await refreshAuditLogs();
    } catch {
      setAuthorizationStatus('Decision habilitation impossible : connectez-vous avec un role admin ou super admin.');
    }
  }

  async function handleUserRole(userId: string, role: string, reason: string) {
    setUserGovernanceStatus(null);
    if (blockProtectedAction(setUserGovernanceStatus, true)) return;
    try {
      const updated = await updateInstitutionalUserRole(userId, role, reason);
      setInstitutionalUsers((current) => current.map((user) => (user.id === userId ? updated : user)));
      setUserGovernanceStatus(`Compte ${updated.email} : role ${updated.role}.`);
      await refreshAuditLogs();
    } catch {
      setUserGovernanceStatus('Decision role impossible : seul un super admin peut modifier les habilitations.');
    }
  }

  async function handleUserSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUserGovernanceStatus(null);
    if (blockProtectedAction(setUserGovernanceStatus, true)) return;
    try {
      const created = await createInstitutionalUser(userForm);
      setInstitutionalUsers((current) => [created, ...current]);
      setUserGovernanceStatus(`Compte ${created.email} cree avec le role ${created.role}.`);
      await refreshAuditLogs();
    } catch {
      setUserGovernanceStatus('Creation compte impossible : email deja utilise, mot de passe trop court ou role super admin requis.');
    }
  }

  async function handleUserStatus(userId: string, isActive: boolean, reason: string) {
    setUserGovernanceStatus(null);
    if (blockProtectedAction(setUserGovernanceStatus, true)) return;
    try {
      const updated = await updateInstitutionalUserStatus(userId, isActive, reason);
      setInstitutionalUsers((current) => current.map((user) => (user.id === userId ? updated : user)));
      setUserGovernanceStatus(`Compte ${updated.email} : ${updated.is_active ? 'actif' : 'suspendu'}.`);
      await refreshAuditLogs();
    } catch {
      setUserGovernanceStatus('Decision statut impossible : seul un super admin peut activer ou suspendre un compte.');
    }
  }

  async function handleUserPasswordReset(userId: string) {
    setUserGovernanceStatus(null);
    if (blockProtectedAction(setUserGovernanceStatus, true)) return;
    try {
      const updated = await resetInstitutionalUserPassword(userId, passwordResetValue, 'Reinitialisation administrative controlee');
      setInstitutionalUsers((current) => current.map((user) => (user.id === userId ? updated : user)));
      setUserGovernanceStatus(`Mot de passe du compte ${updated.email} reinitialise.`);
      await refreshAuditLogs();
    } catch {
      setUserGovernanceStatus('Reinitialisation impossible : mot de passe trop court ou role super admin requis.');
    }
  }

  async function handleDashboardCsvExport() {
    if (!canAdminAct) {
      downloadLocalFile('coderoute-dashboard-demo.csv', `indicateur,valeur\ncandidats,${dashboard.candidates}\ncentres_agrees,${dashboard.accredited_centers}\nsessions,${dashboard.exam_sessions}\nalertes,${dashboard.fraud_alerts}\n`);
      setCsvExportStatus('Export demo genere localement : connectez-vous pour exporter les donnees officielles.');
      return;
    }
    if (blockProtectedAction(setCsvExportStatus)) return;
    setIsExportingCsv(true);
    setCsvExportStatus(null);
    try {
      await downloadDashboardCsv();
      setCsvExportStatus('Export dashboard CSV telecharge avec succes.');
      await refreshAuditLogs();
    } catch {
      setCsvExportStatus('Export dashboard impossible : connectez-vous avec un role admin ou super admin.');
    } finally {
      setIsExportingCsv(false);
    }
  }

  async function handleExamAttemptsCsvExport() {
    if (!canAdminAct) {
      downloadLocalFile('coderoute-examens-demo.csv', `indicateur,valeur\ntentatives,${examSummary.total_attempts}\nsoumises,${examSummary.submitted_attempts}\nadmis,${examSummary.passed_attempts}\nechecs,${examSummary.failed_attempts}\nscore_moyen,${examSummary.average_score}\n`);
      setExamCsvExportStatus('Export examens demo genere localement.');
      return;
    }
    if (blockProtectedAction(setExamCsvExportStatus)) return;
    setIsExportingExamCsv(true);
    setExamCsvExportStatus(null);
    try {
      await downloadExamAttemptsCsv();
      setExamCsvExportStatus('Export examens CSV telecharge avec succes.');
      await refreshAuditLogs();
    } catch {
      setExamCsvExportStatus('Export examens impossible : connectez-vous avec un role admin ou super admin.');
    } finally {
      setIsExportingExamCsv(false);
    }
  }

  async function handlePaymentCsvExport() {
    if (!canAdminAct) {
      const rows = ['reference,reservation,operateur,statut,montant,recu', ...paymentItems.map((item) => `${item.reference},${item.booking_reference},${item.provider},${item.status},${item.amount_gnf},${item.receipt_number}`)];
      downloadLocalFile('coderoute-paiements-demo.csv', `${rows.join('\n')}\n`);
      setPaymentCsvExportStatus('Export paiements demo genere localement.');
      return;
    }
    if (blockProtectedAction(setPaymentCsvExportStatus)) return;
    setIsExportingPaymentCsv(true);
    setPaymentCsvExportStatus(null);
    try {
      await downloadAdminPaymentsCsv(activePaymentFilters);
      setPaymentCsvExportStatus('Export paiements CSV telecharge avec succes.');
      await refreshAuditLogs();
    } catch {
      setPaymentCsvExportStatus('Export paiements impossible : connectez-vous avec un role admin ou super admin.');
    } finally {
      setIsExportingPaymentCsv(false);
    }
  }

  async function handleAuditCsvExport() {
    if (!canAdminAct) {
      const rows = ['date,action,entite', ...auditLogs.map((log) => `${log.created_at},${log.action},${log.entity}`)];
      downloadLocalFile('coderoute-audit-demo.csv', `${rows.join('\n')}\n`);
      setAuditCsvExportStatus('Export audit demo genere localement.');
      return;
    }
    if (blockProtectedAction(setAuditCsvExportStatus)) return;
    setIsExportingAuditCsv(true);
    setAuditCsvExportStatus(null);
    try {
      await downloadAuditLogsCsv(activeAuditFilters);
      setAuditCsvExportStatus('Export audit CSV telecharge avec succes.');
      await refreshAuditLogs();
    } catch {
      setAuditCsvExportStatus('Export audit impossible : connectez-vous avec un role admin ou super admin.');
    } finally {
      setIsExportingAuditCsv(false);
    }
  }

  async function handleInstitutionalReportCsvExport() {
    if (!canAdminAct) {
      downloadLocalFile('coderoute-rapport-institutionnel-demo.csv', `champ,valeur\nscore,${institutionalReport.readiness_score}\nlabel,${institutionalReport.readiness_label}\ncandidats,${institutionalReport.candidates}\naudit,${institutionalReport.audit_events}\n`);
      setInstitutionalReportStatus('Rapport institutionnel demo CSV genere localement.');
      return;
    }
    if (blockProtectedAction(setInstitutionalReportStatus)) return;
    setIsExportingInstitutionalReport(true);
    setInstitutionalReportStatus(null);
    try {
      await downloadInstitutionalReportCsv();
      setInstitutionalReportStatus('Rapport institutionnel CSV telecharge avec succes.');
      await refreshAuditLogs();
    } catch {
      setInstitutionalReportStatus('Export rapport institutionnel impossible : connectez-vous avec un role admin ou super admin.');
    } finally {
      setIsExportingInstitutionalReport(false);
    }
  }

  async function handleInstitutionalReportPdfExport() {
    if (!canAdminAct) {
      downloadLocalFile('coderoute-dossier-etat-demo.txt', `CodeRoute Guinee - Dossier Etat\nScore: ${institutionalReport.readiness_score}%\n${institutionalReport.readiness_label}\n\nRecommendations:\n${institutionalReport.recommendations.join('\n')}\n`, 'text/plain;charset=utf-8');
      setInstitutionalReportStatus('Apercu dossier Etat genere localement en texte. Connectez-vous pour le PDF officiel.');
      return;
    }
    if (blockProtectedAction(setInstitutionalReportStatus)) return;
    setIsExportingInstitutionalReportPdf(true);
    setInstitutionalReportStatus(null);
    try {
      await downloadInstitutionalReportPdf();
      setInstitutionalReportStatus('Rapport institutionnel PDF telecharge avec succes.');
      await refreshAuditLogs();
    } catch {
      setInstitutionalReportStatus('Export PDF institutionnel impossible : connectez-vous avec un role admin ou super admin.');
    } finally {
      setIsExportingInstitutionalReportPdf(false);
    }
  }

  async function handlePaymentFiltersSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await loadPaymentSummary(paymentFilters);
    await refreshAuditLogs();
  }

  async function handleOfficialPaymentImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPaymentImportStatus(null);
    if (!canAdminAct && paymentImportDryRun) {
      try {
        const rows = parsePaymentImportCsv(paymentImportCsv);
        setPaymentImportStatus(buildDemoImportStatus('paiements operateur', rows.length));
      } catch (error) {
        setPaymentImportStatus(error instanceof Error ? `Simulation paiements impossible : ${error.message}` : 'Simulation paiements impossible.');
      }
      return;
    }
    if (blockProtectedAction(setPaymentImportStatus)) return;
    try {
      const rows = parsePaymentImportCsv(paymentImportCsv);
      const result = await importOfficialPayments(paymentImportSource, paymentImportReason, rows, paymentImportDryRun);
      setPaymentImportStatus(`${result.dry_run ? 'Simulation paiements terminee' : 'Import paiements termine'} : ${result.imported} paiement(s), ${result.created} cree(s), ${result.updated} mis a jour.`);
      if (!result.dry_run) {
        await loadPaymentSummary(activePaymentFilters);
        await refreshAuditLogs();
      }
    } catch (error) {
      setPaymentImportStatus(error instanceof Error ? `Import paiements impossible : ${error.message}` : 'Import paiements impossible.');
    }
  }

  async function handleIdentityFiltersSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await refreshIdentityChecks(identityFilters);
  }

  async function resetIdentityFilters() {
    const defaults = { status_filter: 'pending', limit: 25 };
    setIdentityFilters(defaults);
    await refreshIdentityChecks(defaults);
  }

  async function handleSubmissionFiltersSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await refreshCandidateSubmissions(submissionFilters);
  }

  async function resetSubmissionFilters() {
    const defaults = { status_filter: 'submitted', limit: 25 };
    setSubmissionFilters(defaults);
    await refreshCandidateSubmissions(defaults);
  }

  async function handleAuditFiltersSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await refreshAuditLogs(auditFilters);
  }

  async function handleMonitoringFiltersSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await refreshExamMonitoring(monitoringFilters);
  }

  async function resetMonitoringFilters() {
    const defaults = { min_risk_score: 1, limit: 25 };
    setMonitoringFilters(defaults);
    await refreshExamMonitoring(defaults);
  }

  async function resetAuditFilters() {
    setAuditFilters({});
    await refreshAuditLogs({});
  }

  async function resetPaymentFilters() {
    setPaymentFilters({});
    await loadPaymentSummary({});
    await refreshAuditLogs();
  }

  const allowedEntries = entrySummary.by_result.allowed ?? 0;
  const deniedEntries = entrySummary.by_result.denied ?? 0;
  const centerRows = Object.entries(entrySummary.by_center).map(([center, values]) => [
    center,
    String(values.allowed ?? 0),
    String(values.denied ?? 0),
    buildRiskLabel(values.denied ?? 0),
  ]);
  const paymentProviderRows = Object.entries(paymentSummary.by_provider).map(([provider, values]) => [
    provider,
    String(values.count),
    formatCurrency(values.amount_gnf),
  ]);
  const paymentStatusRows = Object.entries(paymentSummary.by_status).map(([status, values]) => [
    status,
    String(values.count),
    formatCurrency(values.amount_gnf),
  ]);
  const reportRows = [
    ['Centres', Object.values(institutionalReport.centers_by_status).reduce((sum, value) => sum + value, 0)],
    ['Questions', Object.values(institutionalReport.questions_by_status).reduce((sum, value) => sum + value, 0)],
    ['Identites', Object.values(institutionalReport.identity_checks_by_status).reduce((sum, value) => sum + value, 0)],
    ['Habilitations', Object.values(institutionalReport.authorizations_by_status).reduce((sum, value) => sum + value, 0)],
  ];
  const adminSections = [
    { href: '#comptes', label: 'Comptes' },
    { href: '#candidats', label: 'Candidats' },
    { href: '#centres', label: 'Centres' },
    { href: '#incidents', label: 'Incidents' },
    { href: '#identites', label: 'Identites' },
    { href: '#recours', label: 'Recours' },
    { href: '#questions', label: 'Questions' },
    { href: '#habilitations', label: 'Habilitations' },
    { href: '#dossier-etat', label: 'Dossier Etat' },
    { href: '#securite', label: 'Securite' },
    { href: '#exploitation', label: 'Exploitation' },
    { href: '#production', label: 'Production' },
    { href: '#roadmap', label: 'Roadmap' },
    { href: '#rapport', label: 'Rapport' },
    { href: '#finance', label: 'Finance' },
    { href: '#monitoring-examen', label: 'Monitoring' },
    { href: '#audit', label: 'Audit' },
  ];
  const passRate = examSummary.submitted_attempts
    ? Math.round((examSummary.passed_attempts / examSummary.submitted_attempts) * 100)
    : 0;
  const entryApprovalRate = allowedEntries + deniedEntries
    ? Math.round((allowedEntries / (allowedEntries + deniedEntries)) * 100)
    : 0;
  const accreditedCenters = centers.filter((center) => center.status === 'accredited').length
    || (institutionalReport.centers_by_status.accredited ?? 0);
  const pendingCenters = centers.filter((center) => center.status !== 'accredited').length
    || Object.entries(institutionalReport.centers_by_status)
      .filter(([status]) => status !== 'accredited')
      .reduce((sum, [, value]) => sum + value, 0);
  const paidPayments = paymentSummary.by_status.paid?.count ?? 0;
  const pendingPayments = Object.entries(paymentSummary.by_status)
    .filter(([status]) => status !== 'paid')
    .reduce((sum, [, values]) => sum + values.count, 0);
  const nationalPriorities = [
    {
      label: 'Maturite dossier Etat',
      value: `${institutionalReport.readiness_score}%`,
      status: institutionalReport.readiness_score >= 80 ? 'Pret' : 'A consolider',
      tone: institutionalReport.readiness_score >= 80 ? 'ready' : 'watch',
    },
    {
      label: 'Centres accredites',
      value: formatNumber(accreditedCenters),
      status: pendingCenters > 0 ? `${formatNumber(pendingCenters)} a verifier` : 'Couverture stable',
      tone: pendingCenters > 0 ? 'watch' : 'ready',
    },
    {
      label: 'Reussite examen',
      value: `${passRate}%`,
      status: `${formatNumber(examSummary.passed_attempts)} admis`,
      tone: passRate >= 70 ? 'ready' : 'watch',
    },
    {
      label: 'Entrees centre',
      value: `${entryApprovalRate}%`,
      status: `${formatNumber(deniedEntries)} refus`,
      tone: deniedEntries > 10 ? 'risk' : 'ready',
    },
  ];
  const operationalFlows = [
    ['Dossiers candidats', formatNumber(dashboard.candidates), 'Inscription et convocation'],
    ['Paiements confirmes', formatNumber(paidPayments), `${formatNumber(pendingPayments)} a rapprocher`],
    ['Audit disponible', formatNumber(institutionalReport.audit_events), 'Tracabilite administrative'],
    ['Actions ouvertes', formatNumber(institutionalActionCenter.total_actions), `${formatNumber(institutionalActionCenter.critical_actions)} critique(s)`],
  ];
  const institutionalRoadmap = [
    {
      phase: 'Lot 1',
      title: 'Socle officiel et homologation',
      priority: 'Priorite haute',
      status: institutionalReport.readiness_score >= 80 ? 'Pret' : 'En cours',
      items: ['Validation ministerielle', 'Nomenclature centres agrees', 'Politique de conservation des preuves'],
    },
    {
      phase: 'Lot 2',
      title: 'Donnees nationales connectees',
      priority: 'Priorite haute',
      status: 'A brancher',
      items: ['Registre candidats', 'Pieces identite', 'Banque officielle de questions'],
    },
    {
      phase: 'Lot 3',
      title: 'Securite examen et antifraude',
      priority: 'Priorite haute',
      status: 'A renforcer',
      items: ['Photo candidat', 'Surveillance centre', 'Journal antifraude horodate'],
    },
    {
      phase: 'Lot 4',
      title: 'Deploiement national',
      priority: 'Priorite moyenne',
      status: 'Planifie',
      items: ['Formation agents', 'Tableaux de bord regionaux', 'Support et exploitation'],
    },
  ];
  const statePresentationPillars = [
    ['Objectif public', 'Digitaliser le parcours code de la route avec un controle national, mesurable et auditable.'],
    ['Impact attendu', 'Reduire les files, limiter les fraudes, harmoniser les centres et fiabiliser les resultats.'],
    ['Preuves disponibles', 'Exports CSV, journaux d audit, certificats, controles centre, suivi paiements et readiness.'],
    ['Cadre de pilotage', 'Roles institutionnels, habilitations, decisions tracees et tableau de bord national.'],
  ];
  const pilotCalendar = [
    ['Semaine 1-2', 'Validation ministerielle du perimetre pilote et des centres retenus.'],
    ['Semaine 3-4', 'Import des donnees officielles, formation agents et tests en centre.'],
    ['Mois 2', 'Pilote controle avec candidats reels, supervision nationale et rapport hebdomadaire.'],
    ['Mois 3', 'Bilan, corrections, extension progressive vers les regions prioritaires.'],
  ];
  const securityMatrix = [
    {
      domain: 'Acces et roles',
      status: 'Operationnel',
      evidence: 'Roles admin, centre et candidat avec navigation restreinte et actions sensibles tracees.',
      next: 'Ajouter politiques de mot de passe et expiration de session en production.',
    },
    {
      domain: 'Tracabilite',
      status: 'Operationnel',
      evidence: 'Journaux d audit consultables et exportables pour les decisions administratives.',
      next: 'Signer les exports critiques et definir la duree de conservation officielle.',
    },
    {
      domain: 'Antifraude examen',
      status: 'A renforcer',
      evidence: 'Controle entree, session securisee, surveillance et certificat numerique.',
      next: 'Brancher photo candidat, camera centre et detection d anomalies.',
    },
    {
      domain: 'Donnees personnelles',
      status: 'A cadrer',
      evidence: 'Parcours identite modelise et verification administrative presente.',
      next: 'Formaliser consentement, minimisation, retention et acces aux donnees sensibles.',
    },
  ];
  const productionChecklist = [
    {
      domain: 'Environnements',
      status: 'A preparer',
      evidence: 'Staging et production doivent utiliser des bases separees, variables dediees et domaines officiels.',
      action: 'Creer staging/prod, isoler secrets et URL API.',
    },
    {
      domain: 'Secrets',
      status: 'Critique',
      evidence: 'SECRET_KEY, ADMIN_REGISTRATION_TOKEN, POSTGRES_PASSWORD et compte bootstrap doivent etre generes hors depot.',
      action: 'Stocker dans un coffre de secrets ou les variables securisees de la plateforme.',
    },
    {
      domain: 'Base de donnees',
      status: 'A valider',
      evidence: 'PostgreSQL via migrations Alembic, AUTO_CREATE_TABLES=false et sauvegardes planifiees.',
      action: 'Executer un test de restauration sur environnement de recette.',
    },
    {
      domain: 'Securite HTTP',
      status: 'En place',
      evidence: 'Headers securite, CORS restreint, rate limit login et audit auth disponibles.',
      action: 'Ajouter HTTPS, rotation certificats et revue OWASP avant ouverture publique.',
    },
    {
      domain: 'Observabilite',
      status: 'A renforcer',
      evidence: 'Health/readiness, audit logs, monitoring examen et exports existent.',
      action: 'Brancher logs centralises, alertes et metriques infrastructure.',
    },
    {
      domain: 'CI/CD',
      status: 'Partiel',
      evidence: 'Workflow CI present pour tests backend critiques.',
      action: 'Ajouter build frontend, tests E2E et deploiement staging automatise.',
    },
  ];
  const operationsMetrics = [
    ['Incidents ouverts', operationsSummary.open_incidents],
    ['Incidents critiques', operationsSummary.critical_incidents],
    ['Evenements examen high', operationsSummary.high_risk_exam_events],
    ['Evenements examen critical', operationsSummary.critical_exam_events],
    ['Appareils suspects', operationsSummary.suspicious_devices],
    ['Alertes finance', operationsSummary.payment_alerts],
    ['Audit 24h', operationsSummary.audit_events_24h],
  ];

  return (
    <section className="panel admin-panel">
      <div className="admin-hero">
        <div>
          <p className="eyebrow dark">Administration nationale</p>
          <strong className="admin-kicker">Console institutionnelle CodeRoute Guinee</strong>
          <h2>Supervision centres, entrees, examens et finances</h2>
          <p>Vue de pilotage pour suivre les centres, les candidats, les questions officielles, les habilitations, les finances et les preuves d'audit.</p>
        </div>
        <div className="admin-score-card">
          <span>Maturite institutionnelle</span>
          <strong>{institutionalReport.readiness_score}%</strong>
          <small>{institutionalReport.readiness_label}</small>
        </div>
      </div>
      <div className="admin-section-nav" aria-label="Sections administration">
        {adminSections.map((section) => <a key={section.href} href={section.href}>{section.label}</a>)}
      </div>
      <div className="actions result-actions admin-actions">
        <button onClick={handleDashboardCsvExport} disabled={isExportingCsv}>{isExportingCsv ? 'Export...' : 'Exporter le dashboard CSV'}</button>
        <button onClick={handleInstitutionalReportCsvExport} disabled={isExportingInstitutionalReport}>{isExportingInstitutionalReport ? 'Export...' : 'Exporter le rapport institutionnel'}</button>
        <button onClick={handleInstitutionalReportPdfExport} disabled={isExportingInstitutionalReportPdf}>{isExportingInstitutionalReportPdf ? 'PDF...' : 'Exporter dossier Etat PDF'}</button>
        <button onClick={handleExamAttemptsCsvExport} disabled={isExportingExamCsv}>{isExportingExamCsv ? 'Export...' : 'Exporter les examens CSV'}</button>
        <button onClick={handlePaymentCsvExport} disabled={isExportingPaymentCsv}>{isExportingPaymentCsv ? 'Export...' : 'Exporter les paiements CSV'}</button>
        <button onClick={handleAuditCsvExport} disabled={isExportingAuditCsv}>{isExportingAuditCsv ? 'Export...' : 'Exporter audit CSV'}</button>
      </div>
      {!canAdminAct && <p className="protected-action-note">Mode presentation : les exports et simulations sont actifs localement ; les ecritures officielles restent reservees a un compte admin reel.</p>}
      {csvExportStatus && <p className="login-status">{csvExportStatus}</p>}
      {examCsvExportStatus && <p className="login-status">{examCsvExportStatus}</p>}
      {paymentCsvExportStatus && <p className="login-status">{paymentCsvExportStatus}</p>}
      {auditCsvExportStatus && <p className="login-status">{auditCsvExportStatus}</p>}
      {institutionalReportStatus && <p className={institutionalReportStatus.includes('impossible') || institutionalReportStatus.includes('Mode demo') ? 'form-error' : 'login-status'}>{institutionalReportStatus}</p>}
      {financeStatus && <p className="form-error">{financeStatus}</p>}
      <div className="executive-overview">
        <div className="executive-summary-card">
          <span>Decision de pilotage</span>
          <strong>{institutionalReport.readiness_score >= 80 ? 'Pret pour extension pilote' : 'Pilote a consolider'}</strong>
          <p>{institutionalReport.readiness_label}</p>
        </div>
        <div className="priority-grid">
          {nationalPriorities.map((priority) => (
            <article className={`priority-card tone-${priority.tone}`} key={priority.label}>
              <span>{priority.label}</span>
              <strong>{priority.value}</strong>
              <small>{priority.status}</small>
            </article>
          ))}
        </div>
      </div>
      <div className="operational-flow-grid">
        {operationalFlows.map(([label, value, detail]) => (
          <article key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{detail}</small>
          </article>
        ))}
      </div>
      <div className="action-center-panel">
        <div>
          <h3>Centre d'action institutionnel</h3>
          <p>{formatNumber(institutionalActionCenter.total_actions)} action(s) prioritaire(s), dont {formatNumber(institutionalActionCenter.critical_actions)} critique(s).</p>
        </div>
        {actionCenterStatus && <p className="form-error">{actionCenterStatus}</p>}
        <div className="action-center-grid">
          {institutionalActionCenter.items.map((item) => (
            <a href={item.target} className={`action-item severity-${item.severity}`} key={item.code}>
              <span>{item.severity}</span>
              <strong>{formatNumber(item.count)}</strong>
              <small>{item.label}</small>
            </a>
          ))}
        </div>
      </div>
      <div className="metrics compact">
        <article><strong>{formatNumber(allowedEntries)}</strong><span>Entrees validees</span></article>
        <article><strong>{formatNumber(deniedEntries)}</strong><span>Entrees refusees</span></article>
        <article><strong>{formatNumber(examSummary.submitted_attempts)}</strong><span>Examens soumis</span></article>
        <article><strong>{formatNumber(examSummary.passed_attempts)}</strong><span>Reussites examen</span></article>
      </div>
      <div className="metrics compact">
        <article><strong>{formatNumber(examSummary.failed_attempts)}</strong><span>Echecs examen</span></article>
        <article><strong>{examSummary.average_score}</strong><span>Score moyen</span></article>
        <article><strong>{formatCurrency(paymentSummary.total_amount_gnf)}</strong><span>GNF encaisses</span></article>
        <article><strong>{formatNumber(paymentSummary.total_count)}</strong><span>Paiements</span></article>
      </div>
      <div id="comptes" className="user-governance-panel admin-section">
        <h3>Comptes et roles institutionnels</h3>
        <p>Gouvernance des acces administratifs, agents de centre et comptes candidats rattaches au dispositif.</p>
        {userGovernanceStatus && <p className={userGovernanceStatus.includes('impossible') || userGovernanceStatus.includes('Mode demo') ? 'form-error' : 'login-status'}>{userGovernanceStatus}</p>}
        <form className="authorization-form" onSubmit={handleUserSubmit}>
          <label>Email<input value={userForm.email} onChange={(event) => setUserForm((current) => ({ ...current, email: event.target.value }))} /></label>
          <label>Nom complet<input value={userForm.full_name} onChange={(event) => setUserForm((current) => ({ ...current, full_name: event.target.value }))} /></label>
          <label>Role
            <select value={userForm.role} onChange={(event) => setUserForm((current) => ({ ...current, role: event.target.value }))}>
              <option value="admin">Admin national</option>
              <option value="center">Agent centre</option>
              <option value="candidate">Candidat</option>
            </select>
          </label>
          <label>Mot de passe initial<input type="password" value={userForm.initial_password} onChange={(event) => setUserForm((current) => ({ ...current, initial_password: event.target.value }))} /></label>
          <label>Motif administratif<input value={userForm.reason} onChange={(event) => setUserForm((current) => ({ ...current, reason: event.target.value }))} /></label>
          <button type="submit" disabled={!canSuperAdminAct}>Creer le compte</button>
        </form>
        <div className="reset-password-strip">
          <label>Mot de passe de reset<input type="password" value={passwordResetValue} onChange={(event) => setPasswordResetValue(event.target.value)} /></label>
        </div>
        <div className="table-shell">
          <table>
            <thead><tr><th>Compte</th><th>Nom</th><th>Role</th><th>Statut</th><th>Creation</th><th>Decision</th></tr></thead>
            <tbody>
              {institutionalUsers.slice(0, 10).map((user) => (
                <tr key={user.id}>
                  <td>{user.email}</td>
                  <td>{user.full_name}</td>
                  <td><span className={user.role === 'super_admin' ? 'badge ok' : 'badge'}>{user.role}</span></td>
                  <td><span className={user.is_active ? 'badge ok' : 'badge'}>{user.is_active ? 'Actif' : 'Suspendu'}</span></td>
                  <td>{new Date(user.created_at).toLocaleDateString('fr-FR')}</td>
                  <td>
                    <div className="table-actions">
                      <button disabled={!canSuperAdminAct} onClick={() => handleUserRole(user.id, 'admin', 'Affectation officielle a la supervision nationale')}>Admin</button>
                      <button disabled={!canSuperAdminAct} onClick={() => handleUserRole(user.id, 'center', 'Affectation officielle a un centre agree')}>Centre</button>
                      <button disabled={!canSuperAdminAct} onClick={() => handleUserStatus(user.id, !user.is_active, user.is_active ? 'Suspension administrative temporaire' : 'Reactivation administrative du compte')}>
                        {user.is_active ? 'Suspendre' : 'Reactiver'}
                      </button>
                      <button disabled={!canSuperAdminAct} onClick={() => handleUserPasswordReset(user.id)}>Reset MDP</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div id="candidats" className="candidate-official-panel admin-section">
        <h3>Import candidats officiels</h3>
        <p>Chargement controle des dossiers candidats transmis par une source institutionnelle avant reservation, paiement et convocation.</p>
        {candidateImportStatus && <p className={candidateImportStatus.includes('impossible') ? 'form-error' : 'login-status'}>{candidateImportStatus}</p>}
        <form className="official-import-form" onSubmit={handleOfficialCandidateImport}>
          <label>Source officielle<input value={candidateImportSource} onChange={(event) => setCandidateImportSource(event.target.value)} /></label>
          <label>Motif<input value={candidateImportReason} onChange={(event) => setCandidateImportReason(event.target.value)} /></label>
          <label>Candidats a importer
            <textarea value={candidateImportCsv} onChange={(event) => setCandidateImportCsv(event.target.value)} />
          </label>
          <label className="checkbox-line">
            <input type="checkbox" checked={candidateImportDryRun} onChange={(event) => setCandidateImportDryRun(event.target.checked)} />
            Simulation sans ecriture
          </label>
          <small>Format : prenom;nom;numero_identite;telephone;categorie_permis;statut. Statuts : registered, verified, suspended.</small>
          <button type="submit" disabled={!canAdminAct && !candidateImportDryRun}>Importer candidats officiels</button>
        </form>
        <div className="table-shell">
          <table>
            <thead><tr><th>Reference</th><th>Candidat</th><th>Identite</th><th>Telephone</th><th>Permis</th><th>Statut</th></tr></thead>
            <tbody>
              {candidates.slice(0, 8).map((candidate) => (
                <tr key={candidate.id}>
                  <td>{candidate.reference}</td>
                  <td>{candidate.first_name} {candidate.last_name}</td>
                  <td>{candidate.identity_number}</td>
                  <td>{candidate.phone}</td>
                  <td>{candidate.permit_category}</td>
                  <td><span className={candidate.status === 'verified' ? 'badge ok' : 'badge'}>{candidate.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div id="centres" className="center-governance-panel admin-section">
        <h3>Gouvernance des centres agrees</h3>
        <p>Suivi administratif des centres : audit initial, activation, accreditation et suspension.</p>
        {centerStatus && <p className={centerStatus.includes('impossible') ? 'form-error' : 'login-status'}>{centerStatus}</p>}
        <form className="official-import-form" onSubmit={handleOfficialCenterImport}>
          <label>Source officielle<input value={centerImportSource} onChange={(event) => setCenterImportSource(event.target.value)} /></label>
          <label>Motif<input value={centerImportReason} onChange={(event) => setCenterImportReason(event.target.value)} /></label>
          <label>Centres a importer
            <textarea value={centerImportCsv} onChange={(event) => setCenterImportCsv(event.target.value)} />
          </label>
          <label className="checkbox-line">
            <input type="checkbox" checked={centerImportDryRun} onChange={(event) => setCenterImportDryRun(event.target.checked)} />
            Simulation sans ecriture
          </label>
          <small>Format : code;nom;ville;adresse;capacite;statut. Statuts : pending_audit, active, accredited, suspended.</small>
          <button type="submit" disabled={!canAdminAct && !centerImportDryRun}>Importer centres officiels</button>
        </form>
        <div className="station-registry-panel">
          <div>
            <h4>Registre des postes d'examen</h4>
            <p>Autoriser les appareils connus du centre et identifier les postes inconnus dans le monitoring.</p>
          </div>
          {centerStationStatus && <p className={centerStationStatus.includes('impossible') ? 'form-error' : 'login-status'}>{centerStationStatus}</p>}
          <form className="official-import-form" onSubmit={handleCenterStationSubmit}>
            <label>Centre
              <select value={centerStationForm.center_id} onChange={(event) => setCenterStationForm((current) => ({ ...current, center_id: event.target.value }))}>
                <option value="">Choisir un centre</option>
                {centers.slice(0, 30).map((center) => <option key={center.id} value={center.id}>{center.code} - {center.name}</option>)}
              </select>
            </label>
            <label>Cle appareil<input value={centerStationForm.device_key} onChange={(event) => setCenterStationForm((current) => ({ ...current, device_key: event.target.value }))} /></label>
            <label>Libelle<input value={centerStationForm.label} onChange={(event) => setCenterStationForm((current) => ({ ...current, label: event.target.value }))} /></label>
            <label>Salle<input value={centerStationForm.room ?? ''} onChange={(event) => setCenterStationForm((current) => ({ ...current, room: event.target.value }))} /></label>
            <label>Statut
              <select value={centerStationForm.status} onChange={(event) => setCenterStationForm((current) => ({ ...current, status: event.target.value as CenterStationPayload['status'] }))}>
                <option value="active">Actif</option>
                <option value="maintenance">Maintenance</option>
                <option value="disabled">Desactive</option>
              </select>
            </label>
            <button type="submit" disabled={!canAdminAct || !centerStationForm.center_id}>Enregistrer poste</button>
          </form>
          <div className="table-shell compact-table">
            <table>
              <thead><tr><th>Poste</th><th>Cle appareil</th><th>Centre</th><th>Salle</th><th>Statut</th><th>Decision</th></tr></thead>
              <tbody>
                {centerStations.length === 0 ? (
                  <tr><td colSpan={6}>Aucun poste enregistre.</td></tr>
                ) : centerStations.slice(0, 8).map((station) => (
                  <tr key={station.id}>
                    <td>{station.label}</td>
                    <td>{station.device_key}</td>
                    <td>{centers.find((center) => center.id === station.center_id)?.code ?? station.center_id}</td>
                    <td>{station.room ?? '-'}</td>
                    <td><span className={station.status === 'active' ? 'badge ok' : 'badge'}>{station.status}</span></td>
                    <td>
                      <div className="table-actions">
                        <button disabled={!canAdminAct} onClick={() => handleCenterStationStatus(station.id, 'active')}>Actif</button>
                        <button disabled={!canAdminAct} onClick={() => handleCenterStationStatus(station.id, 'maintenance')}>Maintenance</button>
                        <button disabled={!canAdminAct} onClick={() => handleCenterStationStatus(station.id, 'disabled')}>Desactiver</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="table-shell">
          <table>
            <thead><tr><th>Code</th><th>Centre</th><th>Ville</th><th>Capacite</th><th>Statut</th><th>Decision</th></tr></thead>
            <tbody>
              {centers.slice(0, 8).map((center) => (
                <tr key={center.id}>
                  <td>{center.code}</td>
                  <td>{center.name}</td>
                  <td>{center.city}</td>
                  <td>{center.capacity}</td>
                  <td><span className="badge">{center.status}</span></td>
                  <td>
                    <div className="table-actions">
                      <button disabled={!canAdminAct} onClick={() => handleCenterStatus(center.id, 'accredited', 'Accreditation institutionnelle validee')}>Accrediter</button>
                      <button disabled={!canAdminAct} onClick={() => handleCenterStatus(center.id, 'suspended', 'Suspension administrative pour controle')}>Suspendre</button>
                      <button disabled={!canAdminAct} onClick={() => handleCenterStatus(center.id, 'pending_audit', 'Retour en audit administratif')}>Audit</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div id="incidents" className="center-incident-panel admin-section">
        <div className="incident-admin-header">
          <div>
            <h3>Incidents centres et reprises</h3>
            <p>Suivi des incidents declares par les centres, decision de resolution et creation eventuelle d une nouvelle tentative.</p>
          </div>
          <button className="secondary-button" onClick={refreshCenterIncidents}>Actualiser</button>
        </div>
        {incidentAdminStatus && <p className={incidentAdminStatus.includes('impossible') || incidentAdminStatus.includes('indisponibles') ? 'form-error' : 'login-status'}>{incidentAdminStatus}</p>}
        <div className="incident-resolution-controls">
          <label>Note de resolution<textarea value={incidentResolutionNotes} onChange={(event) => setIncidentResolutionNotes(event.target.value)} /></label>
          <label className="checkbox-line"><input type="checkbox" checked={allowIncidentRetake} onChange={(event) => setAllowIncidentRetake(event.target.checked)} /> Autoriser une nouvelle tentative</label>
        </div>
        <div className="table-shell">
          <table>
            <thead><tr><th>Incident</th><th>Centre</th><th>Session</th><th>Tentative</th><th>Type</th><th>Gravite</th><th>Description</th><th>Decision</th></tr></thead>
            <tbody>
              {centerIncidents.length === 0 ? (
                <tr><td colSpan={8}>Aucun incident ouvert charge.</td></tr>
              ) : centerIncidents.map((incident) => (
                <tr key={incident.id}>
                  <td>{incident.id}</td>
                  <td>{incident.center_id}</td>
                  <td>{incident.session_id ?? '-'}</td>
                  <td>{incident.attempt_id ?? '-'}</td>
                  <td>{incident.incident_type}</td>
                  <td><span className="badge">{incident.severity}</span></td>
                  <td>{incident.description}</td>
                  <td><button onClick={() => handleResolveIncident(incident.id)} disabled={!canAdminAct || incidentResolutionNotes.length < 5}>Resoudre</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div id="identites" className="identity-panel admin-section">
        <h3>Verification identite candidat</h3>
        <p>Controle administratif des pieces avant convocation, entree en centre et emission des attestations.</p>
        {identityStatus && <p className={identityStatus.includes('impossible') || identityStatus.includes('Mode demo') ? 'form-error' : 'login-status'}>{identityStatus}</p>}
        <form className="identity-filters" onSubmit={handleIdentityFiltersSubmit}>
          <label>Statut
            <select value={identityFilters.status_filter ?? ''} onChange={(event) => setIdentityFilters((current) => ({ ...current, status_filter: event.target.value || undefined }))}>
              <option value="">Tous</option>
              <option value="pending">En attente</option>
              <option value="verified">Valide</option>
              <option value="needs_review">A revoir</option>
              <option value="rejected">Rejete</option>
            </select>
          </label>
          <label>ID candidat<input value={identityFilters.candidate_id ?? ''} onChange={(event) => setIdentityFilters((current) => ({ ...current, candidate_id: event.target.value || undefined }))} placeholder="Filtrer par candidat" /></label>
          <label>Limite<input type="number" value={identityFilters.limit ?? 25} onChange={(event) => setIdentityFilters((current) => ({ ...current, limit: Number(event.target.value) || 25 }))} /></label>
          <button type="submit">Filtrer les pieces</button>
          <button type="button" className="secondary-button" onClick={resetIdentityFilters}>Reinitialiser</button>
        </form>
        <p className="identity-filter-summary">Filtre actif : {activeIdentityFilters.status_filter ?? 'tous'} - {identityChecks.length} piece(s) affichee(s).</p>
        <div className="table-shell">
        <table>
          <thead><tr><th>Candidat</th><th>Document</th><th>Reference</th><th>Statut</th><th>Date</th><th>Decision</th></tr></thead>
          <tbody>
            {identityChecks.slice(0, 8).map((check) => (
              <tr key={check.id}>
                <td>{check.candidate_id}</td>
                <td>{check.document_type}</td>
                <td>{check.document_reference}</td>
                <td><span className={check.status === 'verified' ? 'badge ok' : 'badge'}>{check.status}</span></td>
                <td>{new Date(check.created_at).toLocaleString('fr-FR')}</td>
                <td>
                  <div className="table-actions">
                    <button disabled={!canAdminAct} onClick={() => handleIdentityDecision(check.id, 'verified', 'Piece conforme au controle administratif')}>Valider</button>
                    <button disabled={!canAdminAct} onClick={() => handleIdentityDecision(check.id, 'needs_review', 'Controle manuel complementaire requis')}>Revue</button>
                    <button disabled={!canAdminAct} onClick={() => handleIdentityDecision(check.id, 'rejected', 'Piece non conforme ou illisible')}>Rejeter</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </div>
      <div id="recours" className="candidate-submissions-panel admin-section">
        <h3>Recours et reclamations candidats</h3>
        <p>Traitement des demandes de revue, contestations de resultat et suites administratives apres incident.</p>
        {submissionAdminStatus && <p className={submissionAdminStatus.includes('impossible') || submissionAdminStatus.includes('Mode demo') || submissionAdminStatus.includes('indisponibles') ? 'form-error' : 'login-status'}>{submissionAdminStatus}</p>}
        <form className="identity-filters" onSubmit={handleSubmissionFiltersSubmit}>
          <label>Statut
            <select value={submissionFilters.status_filter ?? ''} onChange={(event) => setSubmissionFilters((current) => ({ ...current, status_filter: event.target.value || undefined }))}>
              <option value="">Tous</option>
              <option value="submitted">Depose</option>
              <option value="under_review">En revue</option>
              <option value="accepted">Accepte</option>
              <option value="rejected">Rejete</option>
              <option value="retake_planned">Reprise prevue</option>
            </select>
          </label>
          <label>ID candidat<input value={submissionFilters.candidate_id ?? ''} onChange={(event) => setSubmissionFilters((current) => ({ ...current, candidate_id: event.target.value || undefined }))} placeholder="Candidat" /></label>
          <label>ID tentative<input value={submissionFilters.attempt_id ?? ''} onChange={(event) => setSubmissionFilters((current) => ({ ...current, attempt_id: event.target.value || undefined }))} placeholder="Tentative" /></label>
          <button type="submit">Filtrer</button>
          <button type="button" className="secondary-button" onClick={resetSubmissionFilters}>Reinitialiser</button>
        </form>
        <label className="submission-response-field">Reponse officielle<textarea value={submissionAdminResponse} onChange={(event) => setSubmissionAdminResponse(event.target.value)} /></label>
        <p className="identity-filter-summary">Filtre actif : {activeSubmissionFilters.status_filter ?? 'tous'} - {candidateSubmissions.length} recours affiche(s).</p>
        <div className="table-shell">
          <table>
            <thead><tr><th>Recours</th><th>Candidat</th><th>Tentative</th><th>Categorie</th><th>Statut</th><th>Message</th><th>Decision</th></tr></thead>
            <tbody>
              {candidateSubmissions.length === 0 ? (
                <tr><td colSpan={7}>Aucun recours charge.</td></tr>
              ) : candidateSubmissions.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{item.candidate_id}</td>
                  <td>{item.attempt_id}</td>
                  <td>{item.category}</td>
                  <td><span className={item.status === 'accepted' ? 'badge ok' : 'badge'}>{item.status}</span></td>
                  <td>{item.admin_response ? `${item.message} / Reponse: ${item.admin_response}` : item.message}</td>
                  <td>
                    <div className="table-actions">
                      <button disabled={!canAdminAct || submissionAdminResponse.length < 5} onClick={() => handleSubmissionDecision(item.id, 'under_review')}>Revue</button>
                      <button disabled={!canAdminAct || submissionAdminResponse.length < 5} onClick={() => handleSubmissionDecision(item.id, 'accepted')}>Accepter</button>
                      <button disabled={!canAdminAct || submissionAdminResponse.length < 5} onClick={() => handleSubmissionDecision(item.id, 'retake_planned')}>Reprise</button>
                      <button disabled={!canAdminAct || submissionAdminResponse.length < 5} onClick={() => handleSubmissionDecision(item.id, 'rejected')}>Rejeter</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div id="questions" className="question-governance-panel admin-section">
        <h3>Banque nationale de questions</h3>
        <p>Publication, suspension et relecture officielle des questions utilisees dans les examens.</p>
        {questionGovernanceStatus && <p className={questionGovernanceStatus.includes('impossible') || questionGovernanceStatus.includes('Mode demo') ? 'form-error' : 'login-status'}>{questionGovernanceStatus}</p>}
        <form className="official-import-form" onSubmit={handleOfficialQuestionImport}>
          <label>Source officielle<input value={questionImportSource} onChange={(event) => setQuestionImportSource(event.target.value)} /></label>
          <label>Motif<input value={questionImportReason} onChange={(event) => setQuestionImportReason(event.target.value)} /></label>
          <label>Questions a importer
            <textarea value={questionImportCsv} onChange={(event) => setQuestionImportCsv(event.target.value)} />
          </label>
          <label className="checkbox-line">
            <input type="checkbox" checked={questionImportDryRun} onChange={(event) => setQuestionImportDryRun(event.target.checked)} />
            Simulation sans ecriture
          </label>
          <small>Format : categorie;question;option1|option2|option3;bonne_reponse;explication;active;media_type;media_url;media_alt. Media type : image ou video.</small>
          <button type="submit" disabled={!canAdminAct && !questionImportDryRun}>Importer questions officielles</button>
        </form>
        <div className="table-shell">
        <table>
          <thead><tr><th>Categorie</th><th>Question</th><th>Statut</th><th>Active</th><th>Decision</th></tr></thead>
          <tbody>
            {questionGovernance.slice(0, 8).map((item) => (
              <tr key={item.question_id}>
                <td>{item.category}</td>
                <td>{item.text}</td>
                <td><span className={item.latest_status === 'published' ? 'badge ok' : 'badge'}>{item.latest_status}</span></td>
                <td>{item.is_active ? 'Oui' : 'Non'}</td>
                <td>
                  <div className="table-actions">
                    <button disabled={!canAdminAct} onClick={() => handleQuestionDecision(item.question_id, 'published', 'Question validee pour publication officielle')}>Publier</button>
                    <button disabled={!canAdminAct} onClick={() => handleQuestionDecision(item.question_id, 'needs_revision', 'Relecture pedagogique ou juridique requise')}>Relecture</button>
                    <button disabled={!canAdminAct} onClick={() => handleQuestionDecision(item.question_id, 'suspended', 'Question suspendue par decision administrative')}>Suspendre</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </div>
      <div id="habilitations" className="authorization-panel admin-section">
        <h3>Habilitations institutionnelles</h3>
        <p>Registre des conventions, autorisations ministerielles et cadres de validite du dispositif.</p>
        {authorizationStatus && <p className={authorizationStatus.includes('impossible') || authorizationStatus.includes('Mode demo') ? 'form-error' : 'login-status'}>{authorizationStatus}</p>}
        <form className="authorization-form" onSubmit={handleAuthorizationSubmit}>
          <label>Autorite<input value={authorizationForm.authority} onChange={(event) => setAuthorizationForm((current) => ({ ...current, authority: event.target.value }))} /></label>
          <label>Reference<input value={authorizationForm.reference} onChange={(event) => setAuthorizationForm((current) => ({ ...current, reference: event.target.value }))} /></label>
          <label>Titre<input value={authorizationForm.title} onChange={(event) => setAuthorizationForm((current) => ({ ...current, title: event.target.value }))} /></label>
          <label>Perimetre<input value={authorizationForm.scope} onChange={(event) => setAuthorizationForm((current) => ({ ...current, scope: event.target.value }))} /></label>
          <button type="submit" disabled={!canAdminAct}>Enregistrer habilitation</button>
        </form>
        <div className="table-shell">
        <table>
          <thead><tr><th>Reference</th><th>Autorite</th><th>Titre</th><th>Statut</th><th>Validite</th><th>Decision</th></tr></thead>
          <tbody>
            {institutionalAuthorizations.slice(0, 8).map((item) => (
              <tr key={item.id}>
                <td>{item.reference}</td>
                <td>{item.authority}</td>
                <td>{item.title}</td>
                <td><span className={item.status === 'approved' ? 'badge ok' : 'badge'}>{item.status}</span></td>
                <td>{item.valid_until ? new Date(item.valid_until).toLocaleDateString('fr-FR') : 'A definir'}</td>
                <td>
                  <div className="table-actions">
                    <button disabled={!canAdminAct} onClick={() => handleAuthorizationStatus(item.id, 'approved', 'Habilitation approuvee par l autorite competente')}>Approuver</button>
                    <button disabled={!canAdminAct} onClick={() => handleAuthorizationStatus(item.id, 'pending_signature', 'Signature institutionnelle en attente')}>Signature</button>
                    <button disabled={!canAdminAct} onClick={() => handleAuthorizationStatus(item.id, 'revoked', 'Habilitation revoquee par decision administrative')}>Revoquer</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </div>
      <div className="institutional-panel admin-section">
        <div className="institutional-header">
          <div>
            <h3>Dossier institutionnel Etat guineen</h3>
            <p>{institutionalReadiness.summary}</p>
          </div>
          <strong>{institutionalReadiness.score}%</strong>
        </div>
        <span className="badge ok">{institutionalReadiness.label}</span>
        {readinessStatus && <p className="form-error">{readinessStatus}</p>}
        <div className="readiness-grid">
          {institutionalReadiness.items.map((item) => (
            <article key={item.pillar} className={`readiness-item status-${item.status}`}>
              <span>{item.status}</span>
              <strong>{item.pillar}</strong>
              <p>{item.evidence}</p>
              <small>{item.next_step}</small>
            </article>
          ))}
        </div>
      </div>
      <div id="dossier-etat" className="state-dossier-panel admin-section">
        <div className="state-dossier-intro">
          <div>
            <h3>Dossier de presentation Etat</h3>
            <p>Synthese executive pour presenter CodeRoute Guinee comme solution institutionnelle pilote.</p>
          </div>
          <strong>{institutionalReport.readiness_score}%</strong>
        </div>
        <div className="state-dossier-grid">
          {statePresentationPillars.map(([label, detail]) => (
            <article key={label}>
              <span>{label}</span>
              <p>{detail}</p>
            </article>
          ))}
        </div>
        <div className="pilot-calendar">
          <strong>Calendrier pilote propose</strong>
          {pilotCalendar.map(([period, detail]) => (
            <div key={period}>
              <span>{period}</span>
              <p>{detail}</p>
            </div>
          ))}
        </div>
        <div className="actions result-actions">
          <a href="#/dossier">Ouvrir le dossier complet</a>
        </div>
      </div>
      <div id="securite" className="security-matrix-panel admin-section">
        <div className="security-matrix-header">
          <div>
            <h3>Securite et conformite</h3>
            <p>Matrice de controle pour cadrer les exigences avant homologation et passage en production.</p>
          </div>
          <span>{securityMatrix.filter((item) => item.status === 'Operationnel').length} / {securityMatrix.length} couverts</span>
        </div>
        <div className="security-matrix-grid">
          {securityMatrix.map((item) => (
            <article key={item.domain}>
              <div>
                <strong>{item.domain}</strong>
                <span>{item.status}</span>
              </div>
              <p>{item.evidence}</p>
              <small>{item.next}</small>
            </article>
          ))}
        </div>
      </div>
      <div id="exploitation" className="operations-summary-panel admin-section">
        <div className="operations-summary-header">
          <div>
            <h3>Exploitation nationale</h3>
            <p>Vue de supervision pour la DSI et les responsables metier : incidents, risques examen, appareils, paiements et audit recent.</p>
          </div>
          <span className={`operations-status status-${operationsSummary.status}`}>{operationsSummary.status}</span>
        </div>
        {operationsStatus && <p className="form-error">{operationsStatus}</p>}
        <div className="operations-summary-grid">
          {operationsMetrics.map(([label, value]) => (
            <article key={label}>
              <strong>{formatNumber(Number(value))}</strong>
              <span>{label}</span>
            </article>
          ))}
        </div>
        <div className="operations-alert-list">
          <strong>Alertes a traiter</strong>
          {operationsSummary.alerts.length === 0 ? (
            <p>Aucune alerte operationnelle critique ou warning.</p>
          ) : operationsSummary.alerts.map((alert) => (
            <button key={alert.code} type="button" className={`operations-alert severity-${alert.severity}`} onClick={() => { window.location.hash = alert.target; }} aria-label={`Ouvrir alerte exploitation ${alert.code}`}>
              <span>{alert.severity}</span>
              <strong>{alert.label}</strong>
              <small>{formatNumber(alert.count)} element(s)</small>
            </button>
          ))}
        </div>
        <p className="operations-timestamp">Dernier audit : {operationsSummary.last_audit_at ? new Date(operationsSummary.last_audit_at).toLocaleString('fr-FR') : 'aucun'} - generation : {new Date(operationsSummary.generated_at).toLocaleString('fr-FR')}</p>
      </div>
      <div id="production" className="production-readiness-panel admin-section">
        <div className="production-readiness-header">
          <div>
            <h3>Preparation production</h3>
            <p>Runbook de mise en ligne : environnements, secrets, base, sauvegardes, monitoring et exploitation.</p>
          </div>
          <span>{productionChecklist.filter((item) => item.status === 'En place').length} / {productionChecklist.length} prets</span>
        </div>
        <div className="production-readiness-grid">
          {productionChecklist.map((item) => (
            <article key={item.domain}>
              <div>
                <strong>{item.domain}</strong>
                <span>{item.status}</span>
              </div>
              <p>{item.evidence}</p>
              <small>{item.action}</small>
            </article>
          ))}
        </div>
        <div className="production-command-strip">
          <strong>Commandes de mise en recette</strong>
          <code>docker compose up -d postgres</code>
          <code>docker compose run --rm backend alembic upgrade head</code>
          <code>docker compose run --rm backend python -m app.bootstrap_admin</code>
          <code>python scripts/smoke_local.py</code>
        </div>
      </div>
      <div id="roadmap" className="roadmap-panel admin-section">
        <div className="roadmap-header">
          <div>
            <h3>Feuille de route institutionnelle</h3>
            <p>Lots restants pour passer du pilote presentable a une plateforme nationale exploitable.</p>
          </div>
          <span>{institutionalRoadmap.length} lots</span>
        </div>
        <div className="roadmap-grid">
          {institutionalRoadmap.map((item) => (
            <article key={item.phase}>
              <div className="roadmap-card-header">
                <span>{item.phase}</span>
                <small>{item.priority}</small>
              </div>
              <strong>{item.title}</strong>
              <em>{item.status}</em>
              <ul>
                {item.items.map((detail) => <li key={detail}>{detail}</li>)}
              </ul>
            </article>
          ))}
        </div>
      </div>
      <div id="rapport" className="institutional-report-panel admin-section">
        <h3>Rapport institutionnel exportable</h3>
        <p>{institutionalReport.generated_for}</p>
        <div className="metrics compact">
          <article><strong>{institutionalReport.readiness_score}%</strong><span>{institutionalReport.readiness_label}</span></article>
          <article><strong>{formatNumber(institutionalReport.candidates)}</strong><span>Candidats references</span></article>
          <article><strong>{formatNumber(institutionalReport.audit_events)}</strong><span>Evenements d audit</span></article>
          <article><strong>{formatNumber(institutionalReport.recommendations.length)}</strong><span>Actions recommandees</span></article>
        </div>
        <div className="table-shell compact-table">
        <table>
          <tbody>
            {reportRows.map(([label, value]) => (
              <tr key={label}><th>{label}</th><td>{formatNumber(Number(value))}</td></tr>
            ))}
          </tbody>
        </table>
        </div>
        <div className="recommendation-list">
          {institutionalReport.recommendations.slice(0, 3).map((recommendation) => (
            <p key={recommendation}>{recommendation}</p>
          ))}
        </div>
      </div>
      <div id="finance" className="finance-panel admin-section">
        <h3>Supervision financiere</h3>
        {paymentImportStatus && <p className={paymentImportStatus.includes('impossible') ? 'form-error' : 'login-status'}>{paymentImportStatus}</p>}
        <form className="official-import-form" onSubmit={handleOfficialPaymentImport}>
          <label>Source operateur<input value={paymentImportSource} onChange={(event) => setPaymentImportSource(event.target.value)} /></label>
          <label>Motif<input value={paymentImportReason} onChange={(event) => setPaymentImportReason(event.target.value)} /></label>
          <label>Paiements a rapprocher
            <textarea value={paymentImportCsv} onChange={(event) => setPaymentImportCsv(event.target.value)} />
          </label>
          <label className="checkbox-line">
            <input type="checkbox" checked={paymentImportDryRun} onChange={(event) => setPaymentImportDryRun(event.target.checked)} />
            Simulation sans ecriture
          </label>
          <small>Format : reference_reservation;montant;operateur;telephone;statut;numero_recu;date_iso_optionnelle.</small>
          <button type="submit" disabled={!canAdminAct && !paymentImportDryRun}>Importer paiements operateur</button>
        </form>
        <form className="finance-filters" onSubmit={handlePaymentFiltersSubmit}>
          <label>Operateur
            <select value={paymentFilters.provider ?? ''} onChange={(event) => setPaymentFilters((current) => ({ ...current, provider: event.target.value || undefined }))}>
              <option value="">Tous</option>
              <option value="orange_money">Orange Money</option>
              <option value="mtn_money">MTN Money</option>
              <option value="sandbox">Sandbox</option>
            </select>
          </label>
          <label>Statut
            <select value={paymentFilters.status ?? ''} onChange={(event) => setPaymentFilters((current) => ({ ...current, status: event.target.value || undefined }))}>
              <option value="">Tous</option>
              <option value="paid">Paid</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
            </select>
          </label>
          <label>Date debut<input type="datetime-local" value={paymentFilters.date_from ?? ''} onChange={(event) => setPaymentFilters((current) => ({ ...current, date_from: event.target.value || undefined }))} /></label>
          <label>Date fin<input type="datetime-local" value={paymentFilters.date_to ?? ''} onChange={(event) => setPaymentFilters((current) => ({ ...current, date_to: event.target.value || undefined }))} /></label>
          <button type="submit">Appliquer les filtres</button>
          <button type="button" className="secondary-button" onClick={resetPaymentFilters}>Reinitialiser</button>
        </form>
        <div className="finance-alerts-panel">
          <strong>Alertes financieres</strong>
          {paymentAlerts.length === 0 ? <p>Aucune alerte financiere sur le perimetre filtre.</p> : (
            <div className="alert-list">
              {paymentAlerts.slice(0, 8).map((alert) => (
                <article className={`finance-alert severity-${alert.severity}`} key={`${alert.type}-${alert.reference}-${alert.receipt_number}`}>
                  <span>{alert.severity}</span>
                  <strong>{alert.message}</strong>
                  <small>{alert.reference} - {alert.provider} - {formatCurrency(alert.amount_gnf)}</small>
                </article>
              ))}
            </div>
          )}
        </div>
        <div className="grid modules-grid">
          <div>
            <strong>Par operateur</strong>
            <table>
              <thead><tr><th>Operateur</th><th>Transactions</th><th>Montant</th></tr></thead>
              <tbody>{paymentProviderRows.map((row) => <tr key={row[0]}>{row.map((cell) => <td key={cell}>{cell}</td>)}</tr>)}</tbody>
            </table>
          </div>
          <div>
            <strong>Par statut</strong>
            <table>
              <thead><tr><th>Statut</th><th>Transactions</th><th>Montant</th></tr></thead>
              <tbody>{paymentStatusRows.map((row) => <tr key={row[0]}>{row.map((cell) => <td key={cell}>{cell}</td>)}</tr>)}</tbody>
            </table>
          </div>
        </div>
        <div className="payment-items-panel">
          <strong>Paiements recents filtres</strong>
          <table>
            <thead><tr><th>Reference</th><th>Reservation</th><th>Operateur</th><th>Statut</th><th>Montant</th><th>Recu</th><th>Date</th></tr></thead>
            <tbody>
              {paymentItems.map((payment) => (
                <tr key={payment.reference}>
                  <td>{payment.reference}</td>
                  <td>{payment.booking_reference}</td>
                  <td>{payment.provider}</td>
                  <td><span className="badge">{payment.status}</span></td>
                  <td>{formatCurrency(payment.amount_gnf)}</td>
                  <td>{payment.receipt_number}</td>
                  <td>{payment.created_at ? new Date(payment.created_at).toLocaleString('fr-FR') : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="risk-table-panel admin-section">
        <h3>Controle entree par centre</h3>
        <p>Lecture rapide des validations et refus pour orienter les controles terrain.</p>
        <div className="table-shell compact-table">
          <table>
            <thead><tr><th>Centre</th><th>Validees</th><th>Refusees</th><th>Risque</th></tr></thead>
            <tbody>
              {centerRows.map((row) => (
                <tr key={row[0]}>{row.map((cell, index) => <td key={`${row[0]}-${index}`}>{index === 3 ? <span className="badge">{cell}</span> : cell}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div id="monitoring-examen" className="exam-monitoring-panel admin-section">
        <h3>Monitoring examen et alertes fraude</h3>
        <p>Suivi des evenements de surveillance, scores de risque et tentatives devant passer en revue.</p>
        {monitoringStatus && <p className={monitoringStatus.includes('indisponible') || monitoringStatus.includes('Mode demo') ? 'form-error' : 'login-status'}>{monitoringStatus}</p>}
        <form className="finance-filters" onSubmit={handleMonitoringFiltersSubmit}>
          <label>Tentative
            <input value={monitoringFilters.attempt_id ?? ''} onChange={(event) => setMonitoringFilters((current) => ({ ...current, attempt_id: event.target.value || undefined }))} placeholder="attempt_id" />
          </label>
          <label>Session
            <input value={monitoringFilters.session_id ?? ''} onChange={(event) => setMonitoringFilters((current) => ({ ...current, session_id: event.target.value || undefined }))} placeholder="session_id" />
          </label>
          <label>Gravite
            <select value={monitoringFilters.severity ?? ''} onChange={(event) => setMonitoringFilters((current) => ({ ...current, severity: event.target.value || undefined }))}>
              <option value="">Toutes</option>
              <option value="low">Faible</option>
              <option value="medium">Moyenne</option>
              <option value="high">Haute</option>
              <option value="critical">Critique</option>
            </select>
          </label>
          <label>Risque min<input type="number" value={monitoringFilters.min_risk_score ?? 1} onChange={(event) => setMonitoringFilters((current) => ({ ...current, min_risk_score: Number(event.target.value) || 0 }))} /></label>
          <button type="submit">Charger monitoring</button>
          <button type="button" className="secondary-button" onClick={resetMonitoringFilters}>Reinitialiser</button>
        </form>
        <div className="monitoring-summary-grid">
          <article><strong>{formatNumber(monitoringSummaries.length)}</strong><span>Tentatives a risque</span></article>
          <article><strong>{formatNumber(monitoringEvents.length)}</strong><span>Evenements charges</span></article>
          <article><strong>{formatNumber(deviceSessionAlerts.length)}</strong><span>Alertes appareil</span></article>
          <article><strong>{formatNumber(monitoringSummaries.reduce((sum, item) => sum + item.total_risk_score, 0))}</strong><span>Score risque cumule</span></article>
        </div>
        <div className="grid modules-grid">
          <div className="table-shell">
            <table>
              <thead><tr><th>Tentative</th><th>Evenements</th><th>Risque</th><th>Max</th><th>Statut</th></tr></thead>
              <tbody>
                {monitoringSummaries.length === 0 ? (
                  <tr><td colSpan={5}>Aucune tentative a risque chargee.</td></tr>
                ) : monitoringSummaries.map((summary) => (
                  <tr key={summary.attempt_id}>
                    <td>{summary.attempt_id}</td>
                    <td>{summary.total_events}</td>
                    <td>{summary.total_risk_score}</td>
                    <td><span className="badge">{summary.max_severity}</span></td>
                    <td><span className={summary.status === 'normal' ? 'badge ok' : 'badge'}>{summary.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="table-shell">
            <table>
              <thead><tr><th>Heure</th><th>Tentative</th><th>Type</th><th>Gravite</th><th>Risque</th></tr></thead>
              <tbody>
                {monitoringEvents.length === 0 ? (
                  <tr><td colSpan={5}>Aucun evenement charge.</td></tr>
                ) : monitoringEvents.slice(0, 10).map((event) => (
                  <tr key={event.id}>
                    <td>{new Date(event.occurred_at).toLocaleString('fr-FR')}</td>
                    <td>{event.attempt_id}</td>
                    <td>{event.event_type}</td>
                    <td><span className="badge">{event.severity}</span></td>
                    <td>{event.risk_score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="table-shell device-alert-table">
          <strong>Alertes appareil et postes examen</strong>
          <table>
            <thead><tr><th>Derniere trace</th><th>Poste</th><th>Tentative</th><th>Session</th><th>Risque</th></tr></thead>
            <tbody>
              {deviceSessionAlerts.length === 0 ? (
                <tr><td colSpan={5}>Aucune alerte appareil chargee.</td></tr>
              ) : deviceSessionAlerts.slice(0, 8).map((alert) => (
                <tr key={alert.id}>
                  <td>{new Date(alert.last_seen_at).toLocaleString('fr-FR')}</td>
                  <td>{alert.device_label ?? alert.device_key}</td>
                  <td>{alert.attempt_id ?? '-'}</td>
                  <td>{alert.session_id}</td>
                  <td><span className="badge">{alert.risk_reason ?? alert.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="identity-filter-summary">Filtre actif : risque min {activeMonitoringFilters.min_risk_score ?? 1} - {activeMonitoringFilters.severity ?? 'toutes gravites'}.</p>
      </div>
      <div id="audit" className="audit-panel admin-section">
        <h3>Journal d'audit national</h3>
        {auditStatus && <p className="form-error">{auditStatus}</p>}
        <form className="finance-filters" onSubmit={handleAuditFiltersSubmit}>
          <label>Action
            <input value={auditFilters.action ?? ''} onChange={(event) => setAuditFilters((current) => ({ ...current, action: event.target.value || undefined }))} placeholder="user.created" />
          </label>
          <label>Entite
            <input value={auditFilters.entity ?? ''} onChange={(event) => setAuditFilters((current) => ({ ...current, entity: event.target.value || undefined }))} placeholder="user" />
          </label>
          <label>Limite
            <input type="number" min="1" max="200" value={auditFilters.limit ?? 25} onChange={(event) => setAuditFilters((current) => ({ ...current, limit: Number(event.target.value) || undefined }))} />
          </label>
          <button type="submit">Filtrer</button>
          <button type="button" className="secondary-button" onClick={resetAuditFilters}>Reinitialiser</button>
        </form>
        <table>
          <thead><tr><th>Date</th><th>Action</th><th>Entite</th><th>Details</th></tr></thead>
          <tbody>
            {auditLogs.slice(0, 8).map((log) => (
              <tr key={log.id}>
                <td>{new Date(log.created_at).toLocaleString('fr-FR')}</td>
                <td><span className="badge">{log.action}</span></td>
                <td>{log.entity}</td>
                <td>{formatAuditDetails(log.details)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
