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
  booking: '📅', payment: '💳', exam: '📝', user: '👤', fraud: '🚨',
};

const STATUS_COLOR: Record<string, string> = {
  confirmed: '#155724', paid: '#004085', pending: '#856404',
  failed: '#721c24', open: '#721c24', refunded: '#5a5a5a',
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
      <div style={{ fontSize: 22 }}>{icon}</div>
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
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <span style={{ fontSize: 18, fontWeight: 700 }}>📊 Tableau de bord live</span>
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
      {error  && !loading && <p style={{ color: 'var(--red, #c00)', fontSize: 13 }}>⚠ {error}</p>}

      {kpis && (
        <>
          {/* KPIs grid */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 20 }}>
            <KpiCard label="Candidats total"    value={kpis.total_candidates}   icon="👥" />
            <KpiCard label="Réservations auj."  value={kpis.bookings_today}     icon="📅" />
            <KpiCard label="Réservées cette sem." value={kpis.bookings_week}    icon="🗓" />
            <KpiCard label="Paiements en attente" value={kpis.pending_payments} icon="⏳" alert />
            <KpiCard label="Paiements auj."     value={kpis.paid_today}         icon="💳" />
            <KpiCard label="Sessions actives"   value={kpis.active_sessions}    icon="🏫" />
            <KpiCard label="Réservations conf." value={kpis.confirmed_bookings} icon="✅" />
            <KpiCard label="Incidents ouverts"  value={kpis.open_incidents}     icon="🚨" alert />
            <KpiCard label="Alertes fraude"     value={kpis.fraud_active}       icon="🔴" alert />
          </div>

          {/* Feed activité */}
          {data.feed.length > 0 && (
            <div>
              <div style={{ fontWeight: 600, fontSize: 13, color: '#444', marginBottom: 8 }}>
                ⚡ Activité récente (15 dernières minutes)
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

      <div style={{ fontSize: 11, color: '#aaa', marginTop: 12 }}>
        Rafraîchissement automatique toutes les {POLL_INTERVAL / 1000}s
      </div>
    </div>
  );
}
