/**
 * AdminExtras.tsx — Composants branchant les 16 fonctions API restantes.
 *
 * Groupement par domaine :
 *   InstitutionalAuthsPanel   → getInstitutionalAuthorizations, createInstitutionalAuthorization,
 *                                updateInstitutionalAuthorizationStatus, getOperationalReadiness
 *   DeviceAlertsPanel         → getDeviceSessionAlerts
 *   CenterManagementPanel     → updateCenterStatus, updateCenterStation, getCenterStations
 *   QuestionsPanel            → getQuestions
 *   CandidateFormsPanel       → submitCandidateIdentity, submitCandidateSubmission,
 *                                getExamCertificatePdfUrl
 *   CsvExportsPanel           → getAdminPaymentsCsvUrl, getAuditLogsCsvUrl,
 *                                getDashboardCsvUrl, getExamAttemptsCsvUrl
 *   OfficialPaymentsPanel     → importOfficialPayments
 */
import { type FormEvent, useEffect, useState } from 'react';
import {
  type Center,
  type CenterStation,
  type DeviceSession,
  type ExamQuestion,
  type InstitutionalAuthorization,
  type InstitutionalAuthorizationPayload,
  type OperationalReadiness,
  type PaymentFilters,
  type AuditLogFilters,
  type PaymentOfficialImportRow,
  createInstitutionalAuthorization,
  getAdminPaymentsCsvUrl,
  getAuditLogsCsvUrl,
  getCenterStations,
  getDashboardCsvUrl,
  getDeviceSessionAlerts,
  getExamAttemptsCsvUrl,
  getExamCertificatePdfUrl,
  getInstitutionalAuthorizations,
  getOperationalReadiness,
  getQuestions,
  updateQuestionMedia,
  importOfficialPayments,
  submitCandidateIdentity,
  submitCandidateSubmission,
  updateCenterStation,
  updateCenterStatus,
  updateInstitutionalAuthorizationStatus,
} from '../api';

// ── Helpers locaux ────────────────────────────────────────────────

function fmtDate(s: string) {
  return new Date(s).toLocaleDateString('fr-FR');
}
function errMsg(e: unknown): string {
  if (e instanceof Error) return e.message;
  if (typeof e === 'object' && e !== null && 'detail' in e)
    return String((e as { detail: unknown }).detail);
  return 'Erreur inattendue';
}

// ══════════════════════════════════════════════════════════════════
// 1. Habilitations institutionnelles
//    Fonctions : getInstitutionalAuthorizations, createInstitutionalAuthorization,
//                updateInstitutionalAuthorizationStatus, getOperationalReadiness
// ══════════════════════════════════════════════════════════════════

export function InstitutionalAuthsPanel({ canAdmin }: { canAdmin: boolean }) {
  const [auths, setAuths] = useState<InstitutionalAuthorization[]>([]);
  const [readiness, setReadiness] = useState<OperationalReadiness | null>(null);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [newAuth, setNewAuth] = useState<InstitutionalAuthorizationPayload>({
    authority: '', reference: '', title: '', scope: 'national',
  });

  useEffect(() => {
    if (!canAdmin) { setLoading(false); return; }
    Promise.allSettled([
      getInstitutionalAuthorizations(),
      getOperationalReadiness(),
    ]).then(([a, r]) => {
      if (a.status === 'fulfilled') setAuths(a.value.items);
      if (r.status === 'fulfilled') setReadiness(r.value);
    }).finally(() => setLoading(false));
  }, [canAdmin]);

  function reload() {
    getInstitutionalAuthorizations().then(r => setAuths(r.items)).catch(() => undefined);
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!newAuth.authority || !newAuth.title) return;
    setCreating(true);
    try {
      await createInstitutionalAuthorization(newAuth);
      reload();
      setNewAuth({ authority: '', reference: '', title: '', scope: 'national' });
    } catch { /* silencieux */ }
    finally { setCreating(false); }
  }

  async function handleDecision(id: string, status: 'approved' | 'rejected') {
    setUpdatingId(id);
    try {
      await updateInstitutionalAuthorizationStatus(
        id, status, status === 'approved' ? 'Validée par admin' : 'Rejetée par admin'
      );
      reload();
    } catch { /* silencieux */ }
    finally { setUpdatingId(null); }
  }

  if (!canAdmin) {
    return <div className="alert aw">️ Réservé aux administrateurs.</div>;
  }

  return (
    <div style={{ display: 'grid', gap: 14 }}>

      {/* Statut opérationnel */}
      {readiness && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">📡 Statut opérationnel</span>
            <span className={`badge ${readiness.status === 'ready' ? 'bg' : 'bgo'}`}>
              {readiness.status}
            </span>
          </div>
          <div style={{ display: 'grid', gap: 8 }}>
            {Object.entries(readiness.checks ?? {}).map(([key, val]) => (
              <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
                <span>{val.status === 'ok' ? '' : '️'}</span>
                <span style={{ flex: 1, color: 'var(--ink2)' }}>{key}</span>
                {val.detail && (
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>{val.detail}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Liste habilitations */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">🏛️ Habilitations institutionnelles ({auths.length})</span>
          <button className="secondary-button btn-sm" onClick={reload}>Actualiser</button>
        </div>

        {/* Formulaire création */}
        <form onSubmit={handleCreate} style={{ display: 'grid', gap: 8, marginBottom: 14 }}>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <input
              value={newAuth.authority}
              onChange={e => setNewAuth(p => ({ ...p, authority: e.target.value }))}
              placeholder="Autorité (ex: Ministère des Transports)"
              aria-label="Autorité émettrice"
              style={{ flex: 2, minWidth: 200 }}
            />
            <input
              value={newAuth.reference}
              onChange={e => setNewAuth(p => ({ ...p, reference: e.target.value }))}
              placeholder="Référence (ex: MT/2026/001)"
              aria-label="Référence officielle"
              style={{ flex: 1, minWidth: 140 }}
            />
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <input
              value={newAuth.title}
              onChange={e => setNewAuth(p => ({ ...p, title: e.target.value }))}
              placeholder="Titre de l'habilitation"
              aria-label="Titre"
              style={{ flex: 3, minWidth: 200 }}
            />
            <select
              value={newAuth.scope}
              onChange={e => setNewAuth(p => ({ ...p, scope: e.target.value }))}
              aria-label="Portée"
              style={{ flex: 1, minWidth: 130 }}
            >
              <option value="national">Nationale</option>
              <option value="regional">Régionale</option>
              <option value="prefectural">Préfectorale</option>
            </select>
            <button
              type="submit"
              className="btn-primary btn-sm"
              disabled={creating || !newAuth.authority || !newAuth.title}
            >
              {creating ? '…' : '+ Habiliter'}
            </button>
          </div>
        </form>

        {loading ? (
          <p className="text-muted" style={{ padding: 12 }}>Chargement…</p>
        ) : auths.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--muted)', fontSize: 13, padding: '16px 0' }}>
            Aucune habilitation enregistrée.
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Autorité</th>
                  <th>Titre</th>
                  <th>Portée</th>
                  <th>Statut</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {auths.map(a => (
                  <tr key={a.id}>
                    <td style={{ fontSize: 12 }}>{a.authority}</td>
                    <td style={{ fontSize: 12 }}>{a.title}</td>
                    <td><span className="badge bb">{a.scope}</span></td>
                    <td>
                      <span className={`badge ${
                        a.status === 'approved' ? 'bg'
                        : a.status === 'rejected' ? 'br'
                        : 'bgo'
                      }`}>
                        {a.status ?? 'pending'}
                      </span>
                    </td>
                    <td>
                      {(!a.status || a.status === 'pending') && (
                        <div style={{ display: 'flex', gap: 4 }}>
                          <button
                            className="btn-sm btn-success"
                            disabled={updatingId === a.id}
                            onClick={() => handleDecision(a.id, 'approved')}
                            aria-label={`Approuver ${a.title}`}
                          ></button>
                          <button
                            className="btn-sm btn-danger"
                            disabled={updatingId === a.id}
                            onClick={() => handleDecision(a.id, 'rejected')}
                            aria-label={`Rejeter ${a.title}`}
                          ></button>
                        </div>
                      )}
                    </td>
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

// ══════════════════════════════════════════════════════════════════
// 2. Alertes postes d'examen
//    Fonctions : getDeviceSessionAlerts
// ══════════════════════════════════════════════════════════════════

export function DeviceAlertsPanel({
  centerId,
  sessionId,
}: {
  centerId?: string;
  sessionId?: string;
}) {
  const [alerts, setAlerts] = useState<DeviceSession[]>([]);
  const [loading, setLoading] = useState(true);

  function reload() {
    setLoading(true);
    getDeviceSessionAlerts({ center_id: centerId, session_id: sessionId, limit: 20 })
      .then(setAlerts)
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }

  useEffect(() => { reload(); }, [centerId, sessionId]);

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">⚡ Alertes postes ({alerts.length})</span>
        <button className="secondary-button btn-sm" onClick={reload}>Actualiser</button>
      </div>
      {loading ? (
        <p className="text-muted" style={{ padding: 12 }}>Chargement…</p>
      ) : alerts.length === 0 ? (
        <div style={{ textAlign: 'center', color: 'var(--muted)', fontSize: 13, padding: '16px 0' }}>
          Aucune alerte 
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Poste</th><th>Session</th><th>Statut</th><th>Date</th></tr>
            </thead>
            <tbody>
              {alerts.map(a => (
                <tr key={a.id}>
                  <td style={{ fontSize: 12, fontFamily: 'monospace' }}>
                    {a.device_key.slice(0, 12)}…
                  </td>
                  <td style={{ fontSize: 11, color: 'var(--muted)' }}>
                    {a.session_id?.slice(0, 8) ?? '—'}
                  </td>
                  <td>
                    <span className={`badge ${a.status === 'active' ? 'bg' : 'br'}`}>
                      {a.status}
                    </span>
                  </td>
                  <td style={{ fontSize: 11, color: 'var(--muted)' }}>
                    {a.created_at ? fmtDate(a.created_at) : '—'}
                  </td>
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
// 3. Gestion du centre (statut + postes)
//    Fonctions : updateCenterStatus, updateCenterStation, getCenterStations
// ══════════════════════════════════════════════════════════════════

export function CenterManagementPanel({ center }: { center: Center | null }) {
  const [stations, setStations] = useState<CenterStation[]>([]);
  const [updating, setUpdating] = useState(false);
  const [stationUpdating, setStationUpdating] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!center?.id) return;
    getCenterStations({ center_id: center.id, limit: 30 })
      .then(setStations)
      .catch(() => undefined);
  }, [center?.id]);

  async function toggleCenterStatus() {
    if (!center) return;
    const next = center.status === 'accredited' ? 'suspended' : 'accredited';
    const reason = next === 'suspended'
      ? 'Suspension administrative'
      : 'Réactivation du centre';
    setUpdating(true);
    setStatusMsg(null);
    try {
      await updateCenterStatus(center.id, next, reason);
      setStatusMsg(` Statut mis à jour : ${next}`);
    } catch (e) {
      setStatusMsg(` ${errMsg(e)}`);
    } finally {
      setUpdating(false);
    }
  }

  async function toggleStationStatus(station: CenterStation) {
    const next = station.status === 'active' ? 'maintenance' : 'active';
    setStationUpdating(station.id);
    try {
      await updateCenterStation(station.id, { status: next });
      setStations(prev =>
        prev.map(s => s.id === station.id ? { ...s, status: next } : s)
      );
    } catch { /* silencieux */ }
    finally { setStationUpdating(null); }
  }

  if (!center) return null;

  return (
    <div style={{ display: 'grid', gap: 14 }}>
      {/* Statut centre */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">🏢 Statut du centre</span>
          <span className={`badge ${center.status === 'accredited' ? 'bg' : 'br'}`}>
            {center.status}
          </span>
        </div>
        <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 12 }}>
          {center.name} — {center.city}
        </p>
        {statusMsg && (
          <div className={`alert ${statusMsg.startsWith('') ? 'as' : 'ae'}`}
            style={{ marginBottom: 10 }}>
            {statusMsg}
          </div>
        )}
        <button
          className={center.status === 'accredited' ? 'btn-sm btn-danger' : 'btn-sm btn-success'}
          onClick={toggleCenterStatus}
          disabled={updating}
        >
          {updating
            ? 'Mise à jour…'
            : center.status === 'accredited'
            ? '⏸ Suspendre le centre'
            : '▶ Réactiver le centre'}
        </button>
      </div>

      {/* Postes */}
      {stations.length > 0 && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">🖥️ Postes d'examen ({stations.length})</span>
          </div>
          <div style={{ display: 'grid', gap: 8 }}>
            {stations.map(s => (
              <div
                key={s.id}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '8px 10px', background: 'var(--bg)',
                  borderRadius: 'var(--r)', fontSize: 13,
                }}
              >
                <span style={{ flex: 1, fontWeight: 600 }}>{s.label}</span>
                {s.room && (
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>{s.room}</span>
                )}
                <span className={`badge ${
                  s.status === 'available' ? 'bg'
                  : s.status === 'occupied' ? 'bb'
                  : 'bgo'
                }`}>
                  {s.status}
                </span>
                <button
                  className="secondary-button btn-sm"
                  style={{ fontSize: 11 }}
                  disabled={stationUpdating === s.id}
                  onClick={() => toggleStationStatus(s)}
                  aria-label={`Basculer statut du poste ${s.label}`}
                >
                  {stationUpdating === s.id
                    ? '…'
                    : s.status === 'active'
                    ? '🔧 Maintenance'
                    : ' Actif'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// 4. Banque de questions (vue admin)
//    Fonctions : getQuestions
// ══════════════════════════════════════════════════════════════════

export function QuestionsAdminPanel({ canAdmin }: { canAdmin: boolean }) {
  const [questions, setQuestions] = useState<ExamQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [editing, setEditing] = useState<ExamQuestion | null>(null);

  const reload = () => {
    getQuestions()
      .then(r => setQuestions(r.items))
      .catch(() => undefined)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (!canAdmin) { setLoading(false); return; }
    reload();
  }, [canAdmin]);

  const filtered = filter
    ? questions.filter(q =>
        q.category.toLowerCase().includes(filter.toLowerCase()) ||
        q.text.toLowerCase().includes(filter.toLowerCase())
      )
    : questions;

  const byCategory = filtered.reduce<Record<string, number>>((acc, q) => {
    acc[q.category] = (acc[q.category] ?? 0) + 1;
    return acc;
  }, {});

  if (!canAdmin) {
    return <div className="alert aw">️ Réservé aux administrateurs.</div>;
  }

  return (
    <div style={{ display: 'grid', gap: 14 }}>
      {/* Stats par catégorie */}
      <div className="card">
        <div className="card-header">
          <span className="card-title"> Répartition ({questions.length} questions)</span>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {Object.entries(byCategory).map(([cat, n]) => (
            <button
              key={cat}
              type="button"
              className={filter === cat ? 'btn-primary btn-sm' : 'secondary-button btn-sm'}
              onClick={() => setFilter(filter === cat ? '' : cat)}
            >
              {cat} ({n})
            </button>
          ))}
          {filter && (
            <button
              type="button"
              className="btn-sm btn-danger"
              onClick={() => setFilter('')}
            >
              ✕ Effacer
            </button>
          )}
        </div>
      </div>

      {/* Table questions */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">
            {filter ? `${filter} — ` : ''}
            {filtered.length} question{filtered.length > 1 ? 's' : ''}
          </span>
        </div>
        {loading ? (
          <p className="text-muted" style={{ padding: 12 }}>Chargement…</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 130 }}>Catégorie</th>
                  <th>Question</th>
                  <th style={{ width: 60 }}>Active</th>
                  <th style={{ width: 120 }}>Média</th>
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, 100).map((q, i) => (
                  <tr key={q.id ?? i}>
                    <td>
                      <span className="badge bb" style={{ fontSize: 10 }}>
                        {q.category}
                      </span>
                    </td>
                    <td style={{
                      fontSize: 12,
                      maxWidth: 400,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {q.text}
                    </td>
                    <td>
                      <span className={`badge ${q.is_active ? 'bg' : 'bgr'}`}>
                        {q.is_active ? 'Oui' : 'Non'}
                      </span>
                    </td>
                    <td>
                      {q.media_type === 'image' || q.media_type === 'video' ? (
                        <span className="badge bg" style={{ fontSize: 10 }}>
                          {q.media_type === 'video' ? 'Vidéo' : 'Photo'}
                        </span>
                      ) : (
                        <span style={{ fontSize: 11, color: 'var(--muted)' }}>SVG auto</span>
                      )}
                      {q.id && (
                        <button className="btn-sm btn-outline" style={{ marginLeft: 6, padding: '2px 8px', fontSize: 11 }}
                          onClick={() => setEditing(q)}>
                          Média
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length > 100 && (
              <p style={{ fontSize: 12, color: 'var(--muted)', padding: '8px 0', textAlign: 'center' }}>
                100 / {filtered.length} affichées
              </p>
            )}
          </div>
        )}
      </div>

      {editing && (
        <QuestionMediaModal
          question={editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); reload(); }}
        />
      )}
    </div>
  );
}

// ── Modal : associer une image/vidéo réelle à une question ─────────────────
function QuestionMediaModal({ question, onClose, onSaved }: {
  question: ExamQuestion; onClose: () => void; onSaved: () => void;
}) {
  const isRealMedia = question.media_type === 'image' || question.media_type === 'video';
  const [mediaType, setMediaType] = useState<'image' | 'video'>(
    question.media_type === 'video' ? 'video' : 'image');
  const [url, setUrl] = useState(isRealMedia ? (question.media_url ?? '') : '');
  const [alt, setAlt] = useState(isRealMedia ? (question.media_alt ?? '') : '');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const urlOk = url.trim() === '' || /^https?:\/\//.test(url.trim());

  async function save(clear: boolean) {
    if (saving) return;
    setSaving(true); setErr(null);
    try {
      await updateQuestionMedia(question.id!, clear
        ? { media_url: null }
        : { media_type: mediaType, media_url: url.trim(), media_alt: alt.trim() || null });
      onSaved();
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Enregistrement impossible.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(13,33,55,.55)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
    }} onClick={onClose}>
      <div className="card" style={{ maxWidth: 520, width: '100%', maxHeight: '90vh', overflow: 'auto' }}
        onClick={e => e.stopPropagation()}>
        <div className="card-header">
          <span className="card-title">Média de la question</span>
          <button className="btn-sm btn-outline" onClick={onClose}>Fermer</button>
        </div>

        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 14, lineHeight: 1.5 }}>
          {question.text}
        </p>

        <div style={{ display: 'grid', gap: 12 }}>
          <label>Type de média
            <select value={mediaType} onChange={e => setMediaType(e.target.value as 'image' | 'video')}>
              <option value="image">Photo (image)</option>
              <option value="video">Vidéo</option>
            </select>
          </label>

          <label>URL du média (https://…)
            <input value={url} onChange={e => setUrl(e.target.value)} autoComplete="off"
              placeholder="https://images.unsplash.com/…  ou  https://upload.wikimedia.org/…" />
            {!urlOk && (
              <span style={{ fontSize: 11, color: 'var(--red)', marginTop: 3, display: 'block' }}>
                L'URL doit commencer par https://
              </span>
            )}
          </label>

          <label>Description (texte alternatif)
            <input value={alt} onChange={e => setAlt(e.target.value)} autoComplete="off"
              placeholder="Ex. Panneau STOP à une intersection" />
          </label>

          {/* Aperçu */}
          {url.trim() && urlOk && (
            <div style={{ borderRadius: 10, overflow: 'hidden', background: '#f8fafc', padding: 12, textAlign: 'center' }}>
              <p style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 8 }}>Aperçu</p>
              {mediaType === 'video' ? (
                <video src={url.trim()} controls style={{ maxWidth: '100%', maxHeight: 200, borderRadius: 6 }} />
              ) : (
                <img src={url.trim()} alt={alt || 'Aperçu'} style={{ maxWidth: '100%', maxHeight: 200, borderRadius: 6, objectFit: 'contain' }} />
              )}
            </div>
          )}

          <div className="alert ai" style={{ fontSize: 11.5 }}>
            Utilisez uniquement des images libres de droits (Unsplash, Pexels, Wikimedia Commons)
            ou vos propres visuels. Sans média, la question garde son illustration SVG automatique.
          </div>

          {err && <div className="alert ae">{err}</div>}

          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn-primary" style={{ flex: 1 }}
              disabled={saving || !url.trim() || !urlOk} onClick={() => save(false)}>
              {saving ? 'Enregistrement…' : 'Associer ce média'}
            </button>
            {isRealMedia && (
              <button className="btn-outline" disabled={saving} onClick={() => save(true)}>
                Revenir au SVG
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// 5. Formulaires candidat
//    Fonctions : submitCandidateIdentity, submitCandidateSubmission,
//                getExamCertificatePdfUrl
// ══════════════════════════════════════════════════════════════════

export function CandidateIdentityForm({ candidateId }: { candidateId?: string }) {
  const [docType, setDocType] = useState<'national_id' | 'passport' | 'driver_file'>('national_id');
  const [docRef, setDocRef] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!candidateId || !docRef.trim()) return;
    setSubmitting(true);
    setResult(null);
    try {
      await submitCandidateIdentity({
        candidate_id: candidateId,
        document_type: docType,
        document_reference: docRef.trim(),
      });
      setResult({ ok: true, msg: 'Pièce soumise — en attente de vérification DNTT.' });
      setDocRef('');
    } catch (e) {
      setResult({ ok: false, msg: errMsg(e) });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">🪪 Soumettre une pièce d'identité</span>
      </div>
      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 12 }}>
        <label>
          Type de document
          <select
            value={docType}
            onChange={e => setDocType(e.target.value as typeof docType)}
            aria-label="Type de document d'identité"
          >
            <option value="national_id">Carte Nationale d'Identité</option>
            <option value="passport">Passeport</option>
            <option value="driver_file">Dossier conducteur</option>
          </select>
        </label>
        <label>
          Numéro de référence
          <input
            value={docRef}
            onChange={e => setDocRef(e.target.value)}
            placeholder="Numéro NINA, passeport ou référence dossier"
            aria-label="Numéro de référence du document"
          />
        </label>
        {result && (
          <div className={`alert ${result.ok ? 'as' : 'ae'}`}>{result.msg}</div>
        )}
        <button type="submit" className="btn-primary" disabled={submitting || !docRef.trim()}>
          {submitting ? 'Envoi en cours…' : '📤 Soumettre la pièce'}
        </button>
      </form>
    </div>
  );
}

export function CandidateRecourseForm({
  candidateId,
  attemptId,
}: {
  candidateId?: string;
  attemptId?: string;
}) {
  const [category, setCategory] = useState('exam_result');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!candidateId || !message.trim()) return;
    setSubmitting(true);
    setResult(null);
    try {
      await submitCandidateSubmission({
        candidate_id: candidateId,
        attempt_id: attemptId ?? '',
        category,
        message: message.trim(),
      });
      setResult({ ok: true, msg: 'Recours soumis. Vous serez contacté dans les 72h.' });
      setMessage('');
    } catch (e) {
      setResult({ ok: false, msg: errMsg(e) });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">📩 Déposer un recours</span>
      </div>
      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 12 }}>
        <label>
          Catégorie
          <select
            value={category}
            onChange={e => setCategory(e.target.value)}
            aria-label="Catégorie du recours"
          >
            <option value="exam_result">Résultat d'examen</option>
            <option value="payment">Paiement</option>
            <option value="booking">Réservation</option>
            <option value="center_incident">Incident centre</option>
            <option value="other">Autre</option>
          </select>
        </label>
        <label>
          Message
          <textarea
            value={message}
            onChange={e => setMessage(e.target.value)}
            rows={4}
            placeholder="Décrivez votre recours en détail…"
            aria-label="Message du recours"
            style={{
              width: '100%', fontFamily: 'inherit', fontSize: 13,
              padding: '8px 12px', border: '1.5px solid var(--border)',
              borderRadius: 'var(--r)', resize: 'vertical', background: 'var(--bg)',
              color: 'var(--ink)',
            }}
          />
        </label>
        {result && (
          <div className={`alert ${result.ok ? 'as' : 'ae'}`}>{result.msg}</div>
        )}
        <button type="submit" className="btn-primary" disabled={submitting || !message.trim()}>
          {submitting ? 'Envoi en cours…' : '📤 Soumettre le recours'}
        </button>
      </form>
    </div>
  );
}

export function CertificatePdfButton({
  attemptId,
  label = '⬇ Certificat PDF',
}: {
  attemptId: string;
  label?: string;
}) {
  function handleClick() {
    const url = getExamCertificatePdfUrl(attemptId);
    window.open(url, '_blank', 'noopener');
  }

  return (
    <button
      type="button"
      className="btn-success btn-sm"
      onClick={handleClick}
      aria-label="Télécharger le certificat PDF"
    >
      {label}
    </button>
  );
}

// ══════════════════════════════════════════════════════════════════
// 6. Exports CSV directs (URLs signées)
//    Fonctions : getAdminPaymentsCsvUrl, getAuditLogsCsvUrl,
//                getDashboardCsvUrl, getExamAttemptsCsvUrl
// ══════════════════════════════════════════════════════════════════

export function CsvExportsPanel({
  paymentFilters = {},
  auditFilters = {},
}: {
  paymentFilters?: PaymentFilters;
  auditFilters?: AuditLogFilters;
}) {
  function download(url: string, name: string) {
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    a.rel = 'noopener';
    a.click();
  }

  const exports = [
    {
      label: ' Dashboard',
      url: getDashboardCsvUrl(),
      file: 'dashboard.csv',
    },
    {
      label: ' Paiements',
      url: getAdminPaymentsCsvUrl(paymentFilters),
      file: 'paiements.csv',
    },
    {
      label: ' Audit logs',
      url: getAuditLogsCsvUrl(auditFilters),
      file: 'audit.csv',
    },
    {
      label: '🎓 Examens',
      url: getExamAttemptsCsvUrl(),
      file: 'examens.csv',
    },
  ];

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">⬇ Exports CSV</span>
      </div>
      <div style={{ display: 'grid', gap: 8 }}>
        {exports.map(e => (
          <button
            key={e.file}
            type="button"
            className="secondary-button btn-block"
            style={{ justifyContent: 'flex-start', gap: 10 }}
            onClick={() => download(e.url, e.file)}
          >
            {e.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// 7. Import paiements officiels
//    Fonctions : importOfficialPayments
// ══════════════════════════════════════════════════════════════════

export function OfficialPaymentsImportPanel({ canAdmin }: { canAdmin: boolean }) {
  const [file, setFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);

  async function handleImport(e: FormEvent) {
    e.preventDefault();
    if (!file || !canAdmin) return;
    setImporting(true);
    setStatus(null);
    try {
      const text = await file.text();
      const lines = text.trim().split('\n').slice(1); // skip header
      const rows: PaymentOfficialImportRow[] = lines
        .filter(l => l.trim())
        .map(l => {
          const [ref, amount, provider, phone, st, receipt] =
            l.split(',').map(s => s.trim().replace(/"/g, ''));
          return {
            booking_reference: ref ?? '',
            amount_gnf: parseInt(amount, 10) || 0,
            provider: provider ?? 'orange_money',
            phone: phone ?? '',
            status: st ?? 'paid',
            receipt_number: receipt ?? ref ?? '',
          };
        });

      const result = await importOfficialPayments(
        'csv_upload',
        `Import CSV ${file.name}`,
        rows,
        !confirmed,           // dry_run si pas encore confirmé
      );

      if (!confirmed) {
        setStatus(` Aperçu : ${result.created ?? 0} nouveaux, ${result.skipped ?? 0} ignorés sur ${rows.length} lignes. Cochez "Confirmer" puis soumettez à nouveau.`);
      } else {
        setStatus(` Import validé : ${result.created ?? 0} paiements enregistrés.`);
        setFile(null);
        setConfirmed(false);
      }
    } catch (err) {
      setStatus(` ${errMsg(err)}`);
    } finally {
      setImporting(false);
    }
  }

  if (!canAdmin) {
    return <div className="alert aw">️ Réservé aux administrateurs.</div>;
  }

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title"> Import paiements officiels</span>
      </div>
      <form onSubmit={handleImport} style={{ display: 'grid', gap: 12 }}>
        <label>
          Fichier CSV
          <input
            type="file"
            accept=".csv,.txt"
            onChange={e => { setFile(e.target.files?.[0] ?? null); setStatus(null); setConfirmed(false); }}
            aria-label="Fichier CSV paiements officiels"
          />
        </label>
        <div style={{ fontSize: 12, color: 'var(--muted)', background: 'var(--bg)', padding: '8px 10px', borderRadius: 'var(--r)' }}>
          <strong>Format attendu :</strong><br />
          <code>booking_reference,montant_gnf,operateur,telephone,statut,recu</code><br />
          <code>BK-001,150000,orange_money,+224620001234,paid,REC-001</code>
        </div>
        {status && (
          <div className={`alert ${status.startsWith('') ? 'as' : 'ae'}`}>{status}</div>
        )}
        {status?.includes('Cochez') && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
            <input
              type="checkbox"
              checked={confirmed}
              onChange={e => setConfirmed(e.target.checked)}
            />
            Confirmer l'import réel (irréversible)
          </label>
        )}
        <button type="submit" className="btn-primary" disabled={importing || !file}>
          {importing ? 'Import…' : confirmed ? ' Valider l\'import' : '🔍 Aperçu (dry-run)'}
        </button>
      </form>
    </div>
  );
}
