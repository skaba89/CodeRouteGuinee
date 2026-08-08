import { useEffect, useMemo, useState } from 'react';
import { getDashboardByCenter, type NationalDashboard, type CenterDashboardRow } from '../api';
import {
  getNationalEdgeFleet,
  type EdgeFleet,
  type EdgeFleetCenter,
  type EdgeFleetNode,
} from '../edgeFleetClient';

function fmtNumber(value: number): string {
  return value.toLocaleString('fr-FR');
}

function fmtDateTime(value?: string | null): string {
  if (!value) return 'Jamais';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? 'Inconnu' : parsed.toLocaleString('fr-FR');
}

function healthBadge(status: string) {
  if (status === 'healthy') return { label: 'Sain', cls: 'bg' };
  if (status === 'degraded') return { label: 'Dégradé', cls: 'bgo' };
  return { label: 'Critique', cls: 'br' };
}

function FleetMetric({ label, value, detail, critical = false, warning = false }: {
  label: string;
  value: string | number;
  detail: string;
  critical?: boolean;
  warning?: boolean;
}) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: `1px solid ${critical ? '#fca5a5' : warning ? '#fcd34d' : 'var(--border)'}`,
      borderRadius: 12,
      padding: '14px 16px',
    }}>
      <div style={{ fontSize: 10.5, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.06em', fontWeight: 750 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 850, color: critical ? 'var(--red)' : 'var(--ink)', marginTop: 3 }}>{value}</div>
      <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 3 }}>{detail}</div>
    </div>
  );
}

function EdgeFleetCenterRow({ center }: { center: EdgeFleetCenter }) {
  const health = healthBadge(center.health_status);
  return (
    <tr>
      <td>
        <strong>{center.name}</strong><br />
        <span style={{ fontSize: 11, color: 'var(--muted)' }}>{center.code} · {center.city}</span>
      </td>
      <td><span className={`badge ${health.cls}`}>{health.label}</span></td>
      <td style={{ fontWeight: 800 }}>{center.health_score}/100</td>
      <td>{center.online_nodes}/{center.node_count}</td>
      <td>{center.sync_pending > 0 ? <span className="badge bgo">{center.sync_pending}</span> : '0'}</td>
      <td>{center.revalidation_required > 0 ? <span className="badge br">{center.revalidation_required}</span> : '0'}</td>
      <td>{center.corrupt_leases > 0 ? <span className="badge br">{center.corrupt_leases}</span> : '0'}</td>
      <td>{center.version_drift_nodes > 0 ? <span className="badge bgo">{center.version_drift_nodes}</span> : '0'}</td>
      <td style={{ minWidth: 220 }}>
        {center.alerts.length > 0
          ? center.alerts.slice(0, 2).map(alert => <div key={alert} style={{ fontSize: 11.5, color: 'var(--muted)', marginBottom: 3 }}>• {alert}</div>)
          : <span style={{ fontSize: 12, color: 'var(--guinea-green)' }}>Aucune anomalie critique</span>}
      </td>
    </tr>
  );
}

function EdgeNodeCard({ node, targetVersion }: { node: EdgeFleetNode; targetVersion: string }) {
  const health = healthBadge(node.health_status);
  const telemetry = node.telemetry;
  return (
    <div className="card" style={{ padding: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontWeight: 800 }}>{node.label || node.reference}</div>
          <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{node.center_code || 'Centre inconnu'} · {node.reference}</div>
        </div>
        <span className={`badge ${health.cls}`}>{health.label}</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,minmax(0,1fr))', gap: 8, marginTop: 12, fontSize: 12 }}>
        <div><span style={{ color: 'var(--muted)' }}>Présence</span><br /><strong>{node.online ? 'En ligne' : 'Hors ligne'}</strong></div>
        <div><span style={{ color: 'var(--muted)' }}>Santé</span><br /><strong>{node.health_score}/100</strong></div>
        <div><span style={{ color: 'var(--muted)' }}>Version</span><br /><strong>{node.software_version || 'Inconnue'}</strong></div>
        <div><span style={{ color: 'var(--muted)' }}>Cible</span><br /><strong>{targetVersion}</strong></div>
        <div><span style={{ color: 'var(--muted)' }}>Sync attente</span><br /><strong>{telemetry?.sync_pending ?? '—'}</strong></div>
        <div><span style={{ color: 'var(--muted)' }}>Revalidation</span><br /><strong>{telemetry?.revalidation_required ?? '—'}</strong></div>
      </div>
      <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 10 }}>Dernier heartbeat : {fmtDateTime(node.last_seen_at)}</div>
      {node.alerts.length > 0 && (
        <div style={{ marginTop: 10, display: 'grid', gap: 5 }}>
          {node.alerts.slice(0, 3).map(alert => (
            <div key={`${alert.code}-${alert.message}`} style={{ fontSize: 11.5, color: alert.severity === 'critical' ? 'var(--red)' : '#9a6700' }}>
              {alert.severity === 'critical' ? '●' : '▲'} {alert.message}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Tableau de bord de supervision nationale (DNTT).
 * P7 combine l'activité métier des centres et la santé de la flotte Edge.
 */
export function NationalDashboard() {
  const [data, setData] = useState<NationalDashboard | null>(null);
  const [fleet, setFleet] = useState<EdgeFleet | null>(null);
  const [loading, setLoading] = useState(true);
  const [fleetLoading, setFleetLoading] = useState(true);
  const [fleetError, setFleetError] = useState('');
  const [sortKey, setSortKey] = useState<keyof CenterDashboardRow>('exams_total');
  const [fleetFilter, setFleetFilter] = useState<'all' | 'critical' | 'degraded' | 'healthy'>('all');
  const [showNodes, setShowNodes] = useState(false);

  useEffect(() => {
    getDashboardByCenter()
      .then(setData)
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    let cancelled = false;
    const load = async (first = false) => {
      if (first) setFleetLoading(true);
      try {
        const next = await getNationalEdgeFleet();
        if (!cancelled) {
          setFleet(next);
          setFleetError('');
        }
      } catch (error) {
        if (!cancelled) setFleetError(error instanceof Error ? error.message : 'Supervision Edge indisponible.');
      } finally {
        if (!cancelled && first) setFleetLoading(false);
      }
    };
    void load(true);
    const timer = window.setInterval(() => { void load(false); }, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const filteredFleetCenters = useMemo(() => {
    const centers = fleet?.centers ?? [];
    if (fleetFilter === 'all') return centers;
    return centers.filter(center => center.health_status === fleetFilter);
  }, [fleet, fleetFilter]);

  if (loading) return <div className="card"><p className="text-muted" style={{ padding: 16 }}>Chargement de la supervision nationale…</p></div>;
  if (!data) return <div className="card"><div className="alert aw">Supervision indisponible.</div></div>;

  const n = data.national;
  const sorted = [...data.centers].sort((a, b) => {
    const av = a[sortKey] ?? 0, bv = b[sortKey] ?? 0;
    return typeof av === 'number' && typeof bv === 'number' ? bv - av : String(av).localeCompare(String(bv));
  });

  const kpi = (label: string, value: string | number, accent?: string) => (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '14px 16px' }}>
      <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: .4 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 800, color: accent ?? 'var(--ink)', marginTop: 4 }}>{value}</div>
    </div>
  );

  return (
    <div style={{ display: 'grid', gap: 20 }}>
      <div className="card">
        <div className="card-header"><span className="card-title">Supervision nationale — activité par centre</span></div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12, padding: '4px 0 16px' }}>
          {kpi('Centres', `${n.centers_active}/${n.centers_total}`, 'var(--guinea-green)')}
          {kpi('Sessions', n.sessions_total)}
          {kpi('Réservations', n.bookings_total)}
          {kpi('Examens', n.exams_total)}
          {kpi('Incidents ouverts', n.open_incidents_total, n.open_incidents_total > 0 ? 'var(--red)' : undefined)}
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Centre</th><th>Ville</th><th>Statut</th><th onClick={() => setSortKey('sessions')} style={{ cursor: 'pointer' }}>Sessions</th><th onClick={() => setSortKey('bookings')} style={{ cursor: 'pointer' }}>Réserv.</th><th onClick={() => setSortKey('exams_total')} style={{ cursor: 'pointer' }}>Examens</th><th>Réussite</th><th>Incidents</th></tr></thead>
            <tbody>
              {sorted.map(c => (
                <tr key={c.center_id}>
                  <td style={{ fontWeight: 600 }}>{c.name}<br /><span style={{ fontSize: 11, color: 'var(--muted)' }}>{c.code}</span></td>
                  <td>{c.city}</td>
                  <td><span className={`badge ${c.status === 'active' || c.status === 'accredited' ? 'bg' : 'bgo'}`}>{c.status}</span></td>
                  <td>{c.sessions}</td><td>{c.bookings}</td><td>{c.exams_total}</td>
                  <td>{c.pass_rate_pct === null ? <span style={{ color: 'var(--muted)' }}>—</span> : <span style={{ fontWeight: 700, color: c.pass_rate_pct >= 70 ? 'var(--guinea-green)' : c.pass_rate_pct >= 50 ? '#B8860B' : 'var(--red)' }}>{c.pass_rate_pct}%</span>}</td>
                  <td>{c.open_incidents > 0 ? <span className="badge br">{c.open_incidents}</span> : <span style={{ color: 'var(--muted)' }}>0</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {sorted.length === 0 && <div style={{ padding: 24, textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>Aucun centre enregistré.</div>}
      </div>

      <div className="card" data-testid="national-edge-fleet">
        <div className="card-header" style={{ alignItems: 'flex-start', gap: 14 }}>
          <div>
            <span className="card-title">Flotte Center Edge — continuité nationale</span>
            <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 4 }}>
              Heartbeats Ed25519 · inventaire, backlog, dérive version et capacité hors ligne par centre
            </div>
          </div>
          {fleet && <span className={`badge ${healthBadge(fleet.status).cls}`}>{healthBadge(fleet.status).label}</span>}
        </div>

        {fleetLoading && <p style={{ padding: 12, color: 'var(--muted)' }}>Chargement de la flotte Edge…</p>}
        {fleetError && <div className="alert aw" style={{ marginBottom: 14 }}>{fleetError}</div>}

        {fleet && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))', gap: 10, marginBottom: 16 }}>
              <FleetMetric label="Centres sains" value={`${fleet.summary.centers_healthy}/${fleet.summary.centers_total}`} detail={`${fleet.summary.centers_without_gateway} sans gateway`} critical={fleet.summary.centers_without_gateway > 0} />
              <FleetMetric label="Gateways en ligne" value={`${fleet.summary.nodes_online}/${fleet.summary.nodes_active}`} detail={`${fleet.summary.nodes_total} nœuds enregistrés`} critical={fleet.summary.nodes_active > fleet.summary.nodes_online} />
              <FleetMetric label="Sync en attente" value={fmtNumber(fleet.summary.sync_pending)} detail="Journaux finalisés" warning={fleet.summary.sync_pending > 0} critical={fleet.summary.sync_pending >= 10} />
              <FleetMetric label="Revalidation" value={fmtNumber(fleet.summary.revalidation_required)} detail="Après reboot Edge" critical={fleet.summary.revalidation_required > 0} />
              <FleetMetric label="Corruption locale" value={fmtNumber(fleet.summary.corrupt_leases)} detail="Leases isolés" critical={fleet.summary.corrupt_leases > 0} />
              <FleetMetric label="Mise à niveau" value={fmtNumber(fleet.rollout.upgrade_required_nodes)} detail={`Cible ${fleet.target_software_version}`} warning={fleet.rollout.upgrade_required_nodes > 0} />
            </div>

            <div style={{ padding: 14, border: '1px solid var(--border)', borderRadius: 12, marginBottom: 16, background: 'var(--surface)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 14, flexWrap: 'wrap', alignItems: 'center' }}>
                <div>
                  <strong>Rollout national Edge {fleet.target_software_version}</strong>
                  <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 3 }}>
                    {fleet.rollout.compliant_nodes} conforme(s) · {fleet.rollout.upgrade_required_nodes} à mettre à niveau · {fleet.rollout.blocked_nodes} bloqué(s)
                  </div>
                </div>
                <div style={{ minWidth: 220, flex: '0 1 340px' }}>
                  <div style={{ height: 9, borderRadius: 999, background: 'var(--line)', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${fleet.summary.nodes_active > 0 ? Math.round((fleet.rollout.compliant_nodes / fleet.summary.nodes_active) * 100) : 0}%`,
                      background: 'var(--guinea-green)',
                    }} />
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
              {(['all', 'critical', 'degraded', 'healthy'] as const).map(value => (
                <button key={value} type="button" className={fleetFilter === value ? 'btn-primary btn-sm' : 'secondary-button btn-sm'} onClick={() => setFleetFilter(value)}>
                  {value === 'all' ? 'Tous les centres' : value === 'critical' ? 'Critiques' : value === 'degraded' ? 'Dégradés' : 'Sains'}
                </button>
              ))}
              <button type="button" className="secondary-button btn-sm" onClick={() => setShowNodes(value => !value)} style={{ marginLeft: 'auto' }}>
                {showNodes ? 'Masquer les gateways' : 'Voir les gateways'}
              </button>
            </div>

            <div className="table-wrap">
              <table>
                <thead><tr><th>Centre</th><th>État</th><th>Score</th><th>Gateways</th><th>Sync</th><th>Revalidation</th><th>Corruption</th><th>Version</th><th>Alertes</th></tr></thead>
                <tbody>{filteredFleetCenters.map(center => <EdgeFleetCenterRow key={center.center_id} center={center} />)}</tbody>
              </table>
            </div>
            {filteredFleetCenters.length === 0 && <div style={{ padding: 20, textAlign: 'center', color: 'var(--muted)' }}>Aucun centre dans ce filtre.</div>}

            {showNodes && (
              <div style={{ marginTop: 18 }}>
                <div style={{ fontWeight: 800, marginBottom: 10 }}>Gateways enregistrés ({fleet.nodes.length})</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(270px,1fr))', gap: 10 }}>
                  {fleet.nodes.map(node => <EdgeNodeCard key={node.node_id} node={node} targetVersion={fleet.target_software_version} />)}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
