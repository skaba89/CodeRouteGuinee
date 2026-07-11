import { useEffect, useState } from 'react';
import { getDashboardByCenter, type NationalDashboard, type CenterDashboardRow } from '../api';

/**
 * Tableau de bord de supervision nationale (DNTT) — activité par centre.
 * Vue territoriale : chaque centre agréé avec ses sessions, réservations,
 * examens, taux de réussite et incidents. Permet à l'État de piloter les
 * 135 centres d'un coup d'œil.
 */
export function NationalDashboard() {
  const [data, setData] = useState<NationalDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<keyof CenterDashboardRow>('exams_total');

  useEffect(() => {
    getDashboardByCenter()
      .then(setData)
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

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
    <div className="card">
      <div className="card-header">
        <span className="card-title">Supervision nationale — activité par centre</span>
      </div>

      {/* Synthèse nationale */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12, padding: '4px 0 16px' }}>
        {kpi('Centres', `${n.centers_active}/${n.centers_total}`, 'var(--guinea-green)')}
        {kpi('Sessions', n.sessions_total)}
        {kpi('Réservations', n.bookings_total)}
        {kpi('Examens', n.exams_total)}
        {kpi('Incidents ouverts', n.open_incidents_total, n.open_incidents_total > 0 ? 'var(--red)' : undefined)}
      </div>

      {/* Tableau par centre */}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Centre</th>
              <th>Ville</th>
              <th>Statut</th>
              <th onClick={() => setSortKey('sessions')} style={{ cursor: 'pointer' }}>Sessions</th>
              <th onClick={() => setSortKey('bookings')} style={{ cursor: 'pointer' }}>Réserv.</th>
              <th onClick={() => setSortKey('exams_total')} style={{ cursor: 'pointer' }}>Examens</th>
              <th>Réussite</th>
              <th>Incidents</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(c => (
              <tr key={c.center_id}>
                <td style={{ fontWeight: 600 }}>{c.name}<br /><span style={{ fontSize: 11, color: 'var(--muted)' }}>{c.code}</span></td>
                <td>{c.city}</td>
                <td><span className={`badge ${c.status === 'active' || c.status === 'accredited' ? 'bg' : 'bgo'}`}>{c.status}</span></td>
                <td>{c.sessions}</td>
                <td>{c.bookings}</td>
                <td>{c.exams_total}</td>
                <td>
                  {c.pass_rate_pct === null ? <span style={{ color: 'var(--muted)' }}>—</span> :
                    <span style={{ fontWeight: 700, color: c.pass_rate_pct >= 70 ? 'var(--guinea-green)' : c.pass_rate_pct >= 50 ? '#B8860B' : 'var(--red)' }}>
                      {c.pass_rate_pct}%
                    </span>}
                </td>
                <td>{c.open_incidents > 0 ? <span className="badge br">{c.open_incidents}</span> : <span style={{ color: 'var(--muted)' }}>0</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {sorted.length === 0 && <div style={{ padding: 24, textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>Aucun centre enregistré.</div>}
    </div>
  );
}
