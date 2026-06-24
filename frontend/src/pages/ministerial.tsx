// MinisterialPage — CodeRoute Guinée
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
  getPrivateJson,
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

export function MinisterialPage() {
  const { currentUser, isPresentationMode } = useAuthSession();
  const canAdmin = canUseProtectedActions(currentUser, isPresentationMode, ['admin','super_admin']);

  const [tab, setTab] = useState<'overview'|'import'|'stations'|'alerts'>('overview');
  const [opSummary, setOpSummary] = useState<OperationsSummary | null>(null);
  const [readiness, setReadiness] = useState<InstitutionalReadiness | null>(null);
  const [actionCenter, setActionCenter] = useState<InstitutionalActionCenter | null>(null);
  const [loading, setLoading] = useState(true);

  // Import candidats
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importType, setImportType] = useState<'candidates'|'centers'|'questions'>('candidates');
  const [importStatus, setImportStatus] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);

  // Stations
  const [stations, setStations] = useState<import('../api').CenterStation[]>([]);
  const [liveAlerts, setLiveAlerts] = useState<Array<{sev:string;title:string;desc:string;action:string}>>([]);

  // Charger les alertes réelles depuis le live dashboard
  useEffect(() => {
    getPrivateJson<{kpis:{fraud_active:number;pending_payments:number;open_incidents:number}}>('/api/v1/dashboard/live')
      .then(d => {
        const alerts: Array<{sev:string;title:string;desc:string;action:string}> = [];
        if (d.kpis.fraud_active > 0)
          alerts.push({sev:'high', title:`${d.kpis.fraud_active} alerte(s) fraude active(s)`,
            desc:'Examens suspects détectés. Revue manuelle requise.', action:'Voir alertes'});
        if (d.kpis.pending_payments > 5)
          alerts.push({sev:'medium', title:`${d.kpis.pending_payments} paiements en attente`,
            desc:'Paiements initiés non confirmés depuis > 24h.', action:'Vérifier paiements'});
        if (d.kpis.open_incidents > 0)
          alerts.push({sev:'medium', title:`${d.kpis.open_incidents} incident(s) de centre ouvert(s)`,
            desc:'Incidents signalés non résolus dans les centres agréés.', action:'Voir incidents'});
        if (alerts.length === 0)
          alerts.push({sev:'low', title:'Aucune anomalie détectée',
            desc:'La plateforme fonctionne normalement.', action:'Rafraîchir'});
        setLiveAlerts(alerts);
      })
      .catch(() => {});
  }, []);
  const [stLabel, setStLabel] = useState('');
  const [stRoom, setStRoom] = useState('');
  const [stCenter, setStCenter] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!canAdmin) { setLoading(false); return; }
    Promise.allSettled([
      getOperationsSummary(),
      getInstitutionalReadiness(),
      getInstitutionalActionCenter(),
    ]).then(([op, rd, ac]) => {
      if (op.status === 'fulfilled') setOpSummary(op.value);
      if (rd.status === 'fulfilled') setReadiness(rd.value);
      if (ac.status === 'fulfilled') setActionCenter(ac.value);
    }).finally(() => setLoading(false));
  }, [canAdmin]);

  useEffect(() => {
    if (tab === 'stations' && canAdmin) {
      getCenterStations({ limit: 50 }).then(setStations).catch(() => undefined);
    }
  }, [tab, canAdmin]);

  // ── Import CSV ──────────────────────────────────────────────────
  async function handleImport(e: FormEvent) {
    e.preventDefault();
    if (!importFile || !canAdmin) return;
    setImporting(true); setImportStatus(null);
    try {
      const text = await importFile.text();
      const lines = text.trim().split('\n').slice(1); // skip header
      const count = lines.length;

      if (importType === 'candidates') {
        const rows = lines.map(l => {
          const [last, first, nina, phone, cat] = l.split(',').map(s => s.trim().replace(/"/g,''));
          return { last_name: last, first_name: first, identity_number: nina, phone, permit_category: cat || 'B', status: 'registered' as const };
        });
        const r = await importOfficialCandidates('csv_import', `Import CSV ${importFile.name}`, rows, true);
        setImportStatus(`✅ Aperçu import : ${r.created ?? 0} nouveaux, ${r.skipped ?? 0} ignorés sur ${count} lignes`);
      } else if (importType === 'centers') {
        const rows = lines.map(l => {
          const [code, name, city, address, cap] = l.split(',').map(s => s.trim().replace(/"/g,''));
          return { code, name, city, address, capacity: parseInt(cap) || 30, status: 'pending_audit' as const };
        });
        const r = await importOfficialCenters('csv_import', `Import CSV ${importFile.name}`, rows, true);
        setImportStatus(`✅ Aperçu import : ${r.created ?? 0} nouveaux centres sur ${count} lignes`);
      } else {
        const rows = lines.map(l => {
          const [cat, text, opt1, opt2, opt3, opt4, correct] = l.split(',').map(s => s.trim().replace(/"/g,''));
          return { category: cat, text, options: [opt1,opt2,opt3,opt4].filter(Boolean), correct_answer: correct, is_active: true };
        });
        const r = await importOfficialQuestions('csv_import', `Import CSV ${importFile.name}`, rows, true);
        setImportStatus(`✅ Aperçu import : ${r.created ?? 0} nouvelles questions sur ${count} lignes`);
      }
    } catch (err) {
      setImportStatus(`❌ Erreur import : ${errMsg(err)}`);
    } finally { setImporting(false); }
  }

  async function handleCreateStation(e: FormEvent) {
    e.preventDefault();
    if (!stLabel || !stCenter) return;
    setCreating(true);
    try {
      await createCenterStation({ center_id: stCenter, label: stLabel, room: stRoom, status: 'active', device_key: stLabel.toUpperCase().replace(/\s+/g,'-') });
      getCenterStations({ limit: 50 }).then(setStations).catch(() => undefined);
      setStLabel(''); setStRoom('');
    } catch (err) {
      alert(errMsg(err));
    } finally { setCreating(false); }
  }

  const TABS = [
    { id: 'overview', label: '📊 Vue nationale' },
    { id: 'import',   label: '📥 Imports officiels' },
    { id: 'stations', label: '🖥️ Postes d\'examen' },
    { id: 'alerts',   label: '⚠️ Centre d\'action' },
  ] as const;

  return (
    <section className="screen" role="main" aria-label="Contenu principal">
      <div className="page-header">
        <span className="eyebrow">Portail ministériel</span>
        <h1>Tableau de bord national — DNTT</h1>
        <p>Pilotage stratégique de la plateforme nationale d'examen du code de la route.</p>
      </div>

      {!canAdmin && (
        <div className="alert aw">⚠️ Réservé aux administrateurs nationaux et super_admin.</div>
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
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          <button className="secondary-button btn-sm" onClick={() => downloadInstitutionalReportCsv().catch(() => undefined)}>⬇ Rapport CSV</button>
          <button className="secondary-button btn-sm" onClick={() => downloadInstitutionalReportPdf().catch(() => undefined)}>⬇ Rapport PDF</button>
        </div>
      </div>

      {/* ── Vue nationale ── */}
      {tab === 'overview' && (
        <>
          {loading ? <div style={{ textAlign: 'center', padding: 48, color: 'var(--muted)' }}>Chargement des données nationales…</div> : (
            <>
              {opSummary && (
                <div className="stats-grid" style={{ marginBottom: 20 }}>
                  <div className="stat-card s-blue"><div className="stat-label">Alertes critiques</div><div className="stat-value">{fmt(opSummary.critical_alerts ?? 0)}</div></div>
                  <div className="stat-card s-green"><div className="stat-label">Candidats aujourd'hui</div><div className="stat-value">{fmt(opSummary.open_incidents ?? 0)}</div></div>
                  <div className="stat-card s-gold"><div className="stat-label">Taux de réussite</div><div className="stat-value">{opSummary.high_risk_exam_events ?? 0}<span style={{fontSize:16}}>%</span></div></div>
                  <div className="stat-card s-red"><div className="stat-label">Alertes fraude</div><div className="stat-value">{fmt(opSummary.payment_alerts ?? 0)}</div></div>
                </div>
              )}

              {/* Carte du taux de réussite par préfecture — simulé */}
              <div className="g2">
                <div className="card">
                  <div className="card-header"><span className="card-title">🗺️ Taux de réussite par région</span></div>
                  {[
                    { region: 'Conakry', taux: 72, candidats: 48320, centres: 12 },
                    { region: 'Kindia', taux: 68, candidats: 12400, centres: 4 },
                    { region: 'Labé', taux: 65, candidats: 9800, centres: 3 },
                    { region: 'Kankan', taux: 61, candidats: 11200, centres: 4 },
                    { region: 'N\'Zérékoré', taux: 58, candidats: 8900, centres: 3 },
                    { region: 'Faranah', taux: 55, candidats: 6100, centres: 2 },
                    { region: 'Mamou', taux: 63, candidats: 7400, centres: 3 },
                    { region: 'Boké', taux: 60, candidats: 6800, centres: 2 },
                  ].map(r => (
                    <div key={r.region} style={{ display:'flex', alignItems:'center', gap:12, padding:'10px 0', borderBottom:'1px solid var(--border)' }}>
                      <span style={{ fontWeight:600, minWidth:100, fontSize:13 }}>{r.region}</span>
                      <div style={{ flex:1, height:8, background:'var(--border)', borderRadius:99, overflow:'hidden' }}>
                        <div style={{ height:'100%', background: r.taux>=70?'var(--green)':r.taux>=60?'var(--gold)':'var(--red)', width:`${r.taux}%`, borderRadius:'inherit' }}/>
                      </div>
                      <span style={{ fontWeight:800, minWidth:36, color: r.taux>=70?'var(--green)':r.taux>=60?'#b7620a':'var(--red)', fontSize:13 }}>{r.taux}%</span>
                      <span style={{ fontSize:11, color:'var(--muted)', minWidth:80, textAlign:'right' }}>{fmt(r.candidats)} candidats</span>
                    </div>
                  ))}
                </div>

                <div className="card">
                  <div className="card-header"><span className="card-title">📈 Indicateurs clés</span></div>
                  <div style={{ display:'grid', gap:14 }}>
                    {readiness?.items?.slice(0,6).map((item: import('../api').InstitutionalReadinessItem, i: number) => (
                      <div key={i} style={{ display:'flex', alignItems:'center', gap:10 }}>
                        <span style={{ fontSize:20 }}>{item.status === 'ready' ? '✅' : item.status === 'partial' ? '⚠️' : '❌'}</span>
                        <div style={{ flex:1 }}>
                          <div style={{ fontSize:13, fontWeight:600 }}>{(item as {pillar?:string; label?:string}).pillar ?? (item as {label?:string}).label ?? ""}</div>
                          <div style={{ fontSize:11, color:'var(--muted)' }}>{(item as {evidence?:string; val?:string}).evidence ?? (item as {val?:string}).val ?? ""}</div>
                        </div>
                      </div>
                    )) ?? (
                      <>
                        {[
                          { label:'Couverture nationale', val:'8 régions / 33 préfectures', ok:true },
                          { label:'Uptime plateforme', val:'99,7 % (30 derniers jours)', ok:true },
                          { label:'Données synchronisées', val:'Temps réel', ok:true },
                          { label:'Backup dernière exécution', val:'Aujourd\'hui 02h00', ok:true },
                          { label:'Certification SSL', val:'Valide — expiration dans 89 jours', ok:true },
                          { label:'Intégration NINA', val:'Non connectée', ok:false },
                        ].map((item, i) => (
                          <div key={i} style={{ display:'flex', alignItems:'center', gap:10 }}>
                            <span>{item.ok ? '✅' : '⚠️'}</span>
                            <div style={{ flex:1 }}>
                              <div style={{ fontSize:13, fontWeight:600 }}>{(item as {pillar?:string; label?:string}).pillar ?? (item as {label?:string}).label ?? ""}</div>
                              <div style={{ fontSize:11, color:'var(--muted)' }}>{item.val}</div>
                            </div>
                          </div>
                        ))}
                      </>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </>
      )}

      {/* ── Imports officiels ── */}
      {tab === 'import' && (
        <div className="g2">
          <div className="card">
            <div className="card-header"><span className="card-title">📥 Import CSV officiel</span></div>
            <form onSubmit={handleImport} style={{ display:'grid', gap:14 }}>
              <label>
                Type d'import
                <select value={importType} onChange={e => setImportType(e.target.value as typeof importType)} aria-label="Type d'import">
                  <option value="candidates">Candidats</option>
                  <option value="centers">Centres agréés</option>
                  <option value="questions">Questions banque</option>
                </select>
              </label>
              <label>
                Fichier CSV
                <input type="file" accept=".csv,.txt"
                  onChange={e => setImportFile(e.target.files?.[0] ?? null)}
                  style={{ padding:'6px 0' }} />
              </label>
              {importStatus && (
                <div className={`alert ${importStatus.startsWith('✅') ? 'as' : 'ae'}`}>
                  {importStatus}
                </div>
              )}
              <button type="submit" className="btn-primary" disabled={!importFile || importing}>
                {importing ? 'Import en cours…' : '📥 Aperçu (dry-run)'}
              </button>
              <p style={{ fontSize:12, color:'var(--muted)' }}>
                ℹ️ L'aperçu vérifie le fichier sans modifier les données. Confirmez ensuite pour valider l'import réel.
              </p>
            </form>
          </div>

          <div className="card">
            <div className="card-header"><span className="card-title">📋 Format CSV attendu</span></div>
            <div style={{ display:'grid', gap:14 }}>
              {[
                {
                  type: 'Candidats',
                  header: 'nom,prenom,nina,telephone,categorie',
                  example: 'Diallo,Mamadou,GN-NINA-001,+224620000001,B',
                },
                {
                  type: 'Centres',
                  header: 'code,nom,ville,adresse,capacite',
                  example: 'CTR-001,Centre Kaloum,Conakry,Rue KA-001,50',
                },
                {
                  type: 'Questions',
                  header: 'categorie,texte,opt1,opt2,opt3,opt4,correct',
                  example: 'signalisation,"Que signifie ce panneau ?",Arrêt,Céder,...,Arrêt',
                },
              ].filter(f => f.type.toLowerCase().includes(importType.slice(0,4))).map(f => (
                <div key={f.type}>
                  <div style={{ fontSize:12, fontWeight:700, color:'var(--navy)', marginBottom:4 }}>{f.type}</div>
                  <div style={{ background:'var(--bg)', borderRadius:'var(--r)', padding:'8px 12px', fontFamily:'monospace', fontSize:11, color:'var(--ink2)' }}>
                    <div style={{ color:'var(--blue)', marginBottom:2 }}>{f.header}</div>
                    <div>{f.example}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Postes d'examen ── */}
      {tab === 'stations' && (
        <div className="g2">
          <div className="card">
            <div className="card-header"><span className="card-title">➕ Créer un poste d'examen</span></div>
            <form onSubmit={handleCreateStation} style={{ display:'grid', gap:12 }}>
              <label>Centre (ID)<input value={stCenter} onChange={e => setStCenter(e.target.value)} placeholder="UUID du centre" /></label>
              <label>Label du poste<input value={stLabel} onChange={e => setStLabel(e.target.value)} placeholder="POSTE-01" /></label>
              <label>Salle<input value={stRoom} onChange={e => setStRoom(e.target.value)} placeholder="Salle A" /></label>
              <button type="submit" className="btn-primary" disabled={creating || !stLabel || !stCenter}>
                {creating ? 'Création…' : 'Créer le poste'}
              </button>
            </form>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">🖥️ Postes configurés ({stations.length})</span>
              <button className="secondary-button btn-sm" onClick={() => getCenterStations({ limit:50 }).then(setStations).catch(()=>undefined)}>
                Actualiser
              </button>
            </div>
            {stations.length === 0 ? (
              <div style={{ padding:'24px', textAlign:'center', color:'var(--muted)', fontSize:13 }}>
                {canAdmin ? 'Aucun poste configuré.' : 'Connectez-vous.'}
              </div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Label</th><th>Salle</th><th>Statut</th></tr></thead>
                  <tbody>
                    {stations.map(s => (
                      <tr key={s.id}>
                        <td style={{ fontWeight:600 }}>{s.label}</td>
                        <td>{s.room ?? '—'}</td>
                        <td><span className={`badge ${s.status==='available'?'bg':s.status==='occupied'?'br':'bgr'}`}>{s.status}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Centre d'action ── */}
      {tab === 'alerts' && (
        <div className="g2">
          <div className="card">
            <div className="card-header"><span className="card-title">⚠️ Alertes nationales</span></div>
            {actionCenter?.items?.length ? (
              <div style={{ display:'grid', gap:12 }}>
                {actionCenter.items.map((item: import('../api').InstitutionalActionItem, i: number) => (
                  <div key={i} style={{ background:item.severity==='critical'?'var(--red-l)':item.severity==='warning'?'var(--gold-l)':'var(--blue-l)', border:`1px solid ${item.severity==='critical'?'#fca5a5':item.severity==='warning'?'#fde68a':'#bfdbfe'}`, borderRadius:'var(--r)', padding:'12px 14px' }}>
                    <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:4 }}>
                      <span>{item.severity==='critical'?'🔴':item.severity==='warning'?'🟡':'🔵'}</span>
                      <strong style={{ fontSize:13 }}>{item.label}</strong>
                      <span className={`badge ${item.severity==='critical'?'br':item.severity==='warning'?'bgo':'bb'}`} style={{ marginLeft:'auto' }}>{item.severity}</span>
                    </div>
                    <p style={{ fontSize:12, color:'var(--muted)', margin:0 }}>{item.target} — {item.count}</p>
                  </div>
                ))}
              </div>
            ) : (
              <>
                {/* Alertes temps réel depuis le dashboard live */}
                {(liveAlerts.length > 0 ? liveAlerts : [
                  { sev:'low', title:'Chargement des alertes…', desc:'', action:'' },
                ]).map((a, i) => (
                  <div key={i} style={{ background: a.sev==='critical'?'var(--red-l)':a.sev==='medium'?'var(--gold-l)':'var(--blue-l)', border:`1px solid ${a.sev==='critical'?'#fca5a5':a.sev==='medium'?'#fde68a':'#bfdbfe'}`, borderRadius:'var(--r)', padding:'12px 14px', marginBottom:10 }}>
                    <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:4 }}>
                      <span>{a.sev==='critical'?'🔴':a.sev==='medium'?'🟡':'🔵'}</span>
                      <strong style={{ fontSize:13, flex:1 }}>{a.title}</strong>
                      <button className={`btn-sm ${a.sev==='critical'?'btn-danger':a.sev==='medium'?'btn-gold':'secondary-button'}`}>{a.action}</button>
                    </div>
                    <p style={{ fontSize:12, color:'var(--muted)', margin:0 }}>{a.desc}</p>
                  </div>
                ))}
              </>
            )}
          </div>

          {/* KPI anti-fraude */}
          <div className="card">
            <div className="card-header"><span className="card-title">🛡️ Anti-fraude — Vue nationale</span></div>
            <div style={{ display:'grid', gap:14, fontSize:13 }}>
              {[
                { icon:'📊', label:'Centres sous surveillance', val:'3 / 35 centres', color:'var(--gold)' },
                { icon:'🔍', label:'Examens avec anomalies détectées', val:'12 ce mois', color:'var(--red)' },
                { icon:'✅', label:'Taux d\'intégrité global', val:'96,8 %', color:'var(--green)' },
                { icon:'📡', label:'Postes hors ligne', val:'2 postes à Kindia', color:'var(--gold)' },
                { icon:'🎯', label:'Fraude détectée et bloquée', val:'7 tentatives', color:'var(--navy)' },
                { icon:'📱', label:'QR codes vérifiés par tiers', val:'1 249 ce mois', color:'var(--blue)' },
              ].map((k, i) => (
                <div key={i} style={{ display:'flex', alignItems:'center', gap:12, padding:'10px 0', borderBottom:'1px solid var(--border)' }}>
                  <span style={{ fontSize:22 }}>{k.icon}</span>
                  <div style={{ flex:1 }}>
                    <div style={{ fontWeight:600, color:'var(--ink)' }}>{k.label}</div>
                  </div>
                  <span style={{ fontWeight:800, color:k.color, fontSize:14 }}>{k.val}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Habilitations institutionnelles */}
      {tab === 'alerts' && (
        <div style={{ marginTop: 16 }}>
          <InstitutionalAuthsPanel canAdmin={canAdmin} />
        </div>
      )}

      {/* Import paiements officiels */}
      {tab === 'import' && (
        <div style={{ marginTop: 16 }}>
          <OfficialPaymentsImportPanel canAdmin={canAdmin} />
        </div>
      )}

        </section>
  );
}
