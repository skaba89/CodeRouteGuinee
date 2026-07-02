/**
 * LiveDashboard — Widget de monitoring temps réel
 * Polle GET /api/v1/dashboard/live toutes les 15 secondes
 * Affiche les KPIs frais + un feed d'activité récente
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { getPrivateJson } from '../api';

const POLL_INTERVAL = 15_000; // 15 secondes

interface LiveKpis {
  total_candidates:   number;
  bookings_today:     number;
  bookings_week:      number;
  pending_payments:   number;
  paid_today:         number;
  active_sessions:    number;
  confirmed_bookings: number;
  open_incidents:     number;
  fraud_active:       number;
}

interface FeedItem {
  id:        string;
  type:      'booking' | 'payment' | 'exam' | 'user' | 'fraud';
  title:     string;
  status:    string;
  timestamp: string | null;
}

interface LiveData {
  timestamp: string;
  kpis:      LiveKpis;
  feed:      FeedItem[];
  poll_interval_seconds: number;
}

const TYPE_ICON: Record<string, string> = {
  booking: 'calendar', payment: 'credit-card', exam: 'clipboard', user: 'user', fraud: 'alert',
};

const STATUS_COLOR: Record<string, string> = {
  confirmed: '#155724', paid: '#004085', pending: '#856404',
  failed: '#721c24', open: '#721c24', refunded: '#5a5a5a',
};

// Icônes SVG pour le tableau de bord temps réel
const ICONS: Record<string, React.ReactElement> = {
  'users':     <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>,
  'calendar':  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>,
  'credit-card':<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>,
  'clipboard': <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/></svg>,
  'card':      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>,
  'building':  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="4" y="2" width="16" height="20" rx="1"/><line x1="9" y1="22" x2="9" y2="11"/><line x1="15" y1="22" x2="15" y2="11"/><path d="M8 7h.01M12 7h.01M16 7h.01M8 11h.01M16 11h.01"/></svg>,
  'check':     <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>,
  'alert':     <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>,
  '🗓':        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01"/></svg>,
  '⏳':        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M5 22h14M5 2h14M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"/></svg>,
  '🔴':        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>,
};

function KpiCard({ label, value, icon, alert = false }: {
  label: string; value: number; icon: string; alert?: boolean;
}) {
  return (
    <div style={{
      background: alert && value > 0 ? '#fff3cd' : '#f8faf9',
      border: `1px solid ${alert && value > 0 ? '#ffc107' : '#d4edda'}`,
      borderRadius: 10, padding: '12px 16px', minWidth: 120, flex: 1,
    }}>
      <div style={{ fontSize: 22, color: alert && value > 0 ? '#B45309' : 'var(--guinea-green)', display: 'flex', alignItems: 'center' }}>
        {ICONS[icon] ?? <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/></svg>}
      </div>
      <div style={{ fontSize: 26, fontWeight: 800, color: '#006B3F', lineHeight: 1.2 }}>
        {value.toLocaleString('fr-FR')}
      </div>
      <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{label}</div>
    </div>
  );
}

export function LiveDashboard() {
  const [data, setData]         = useState<LiveData | null>(null);
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [online, setOnline]     = useState(true);
  const timerRef                = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchLive = useCallback(async () => {
    try {
      const d = await getPrivateJson<LiveData>('/api/v1/dashboard/live');
      setData(d);
      setError('');
      setLastRefresh(new Date());
      setOnline(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur réseau');
      setOnline(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLive();
    timerRef.current = setInterval(fetchLive, POLL_INTERVAL);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [fetchLive]);

  const kpis = data?.kpis;

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif' }}>
      {/* En-tête */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <span style={{ fontSize: 15, fontWeight: 800, color: 'var(--ink)', letterSpacing: '-.02em' }}>
          Tableau de bord temps réel
        </span>
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 5,
          fontSize: 12, padding: '3px 10px', borderRadius: 20,
          background: online ? '#d4edda' : '#f8d7da',
          color:      online ? '#155724' : '#721c24',
        }}>
          <span style={{
            display: 'inline-block', width: 7, height: 7, borderRadius: '50%',
            background: online ? '#28a745' : '#dc3545',
          }} />
          {online ? 'En ligne' : 'Hors ligne'}
        </span>
        <button
          onClick={fetchLive}
          title="Rafraîchir maintenant"
          style={{ marginLeft: 'auto', background: 'none', border: 'none',
            cursor: 'pointer', fontSize: 16, opacity: 0.6 }}
        >🔄</button>
        {lastRefresh && (
          <span style={{ fontSize: 11, color: 'var(--muted)' }}>
            Mis à jour {lastRefresh.toLocaleTimeString('fr-FR')}
          </span>
        )}
      </div>

      {loading && <p style={{ color: 'var(--muted)', fontSize: 13 }}>Chargement…</p>}
      {error  && !loading && <p style={{ color: 'var(--red, #c00)', fontSize: 13 }}>{error}</p>}

      {kpis && (
        <>
          {/* KPIs grid */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 20 }}>
            <KpiCard label="Candidats total"    value={kpis.total_candidates}   icon="users" />
            <KpiCard label="Réservations auj."  value={kpis.bookings_today}     icon="calendar" />
            <KpiCard label="Réservées cette sem." value={kpis.bookings_week}    icon="🗓" />
            <KpiCard label="Paiements en attente" value={kpis.pending_payments} icon="⏳" alert />
            <KpiCard label="Paiements auj."     value={kpis.paid_today}         icon="card" />
            <KpiCard label="Sessions actives"   value={kpis.active_sessions}    icon="building" />
            <KpiCard label="Réservations conf." value={kpis.confirmed_bookings} icon="check" />
            <KpiCard label="Incidents ouverts"  value={kpis.open_incidents}     icon="alert" alert />
            <KpiCard label="Alertes fraude"     value={kpis.fraud_active}       icon="🔴" alert />
          </div>

          {/* Feed activité */}
          {data.feed.length > 0 && (
            <div>
              <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--ink2)', marginBottom: 8 }}>
                Activité récente (15 dernières minutes)
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {data.feed.map((item) => (
                  <div key={item.id} style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    background: 'var(--bg, #f8faf9)', borderRadius: 8, padding: '8px 12px',
                    fontSize: 13,
                  }}>
                    <span style={{ fontSize: 16 }}>{TYPE_ICON[item.type] ?? '📌'}</span>
                    <span style={{ flex: 1, color: 'var(--ink2)' }}>{item.title}</span>
                    <span style={{
                      fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 10,
                      background: 'var(--primary-light, #e8f5e9)',
                      color: STATUS_COLOR[item.status] ?? '#333',
                    }}>
                      {item.status}
                    </span>
                    <span style={{ fontSize: 11, color: 'var(--muted)', minWidth: 60, textAlign: 'right' }}>
                      {item.timestamp
                        ? new Date(item.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
                        : '—'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.feed.length === 0 && (
            <p style={{ fontSize: 13, color: 'var(--muted)', fontStyle: 'italic' }}>
              Aucune activité dans les 15 dernières minutes.
            </p>
          )}
        </>
      )}

      <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 12 }}>
        Rafraîchissement automatique toutes les {POLL_INTERVAL / 1000}s
      </div>
    </div>
  );
}
