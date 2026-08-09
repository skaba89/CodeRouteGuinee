import { useEffect, useState } from 'react';
import {
  getSecurityOperationsStatus,
  type SecurityOperationsStatus,
} from '../securityOperationsClient';

function statusBadge(status: string): { label: string; cls: string } {
  if (status === 'ok') return { label: 'Opérationnel', cls: 'bg' };
  if (status === 'warning') return { label: 'À surveiller', cls: 'bgo' };
  if (status === 'critical') return { label: 'Critique', cls: 'br' };
  return { label: 'Non activé', cls: 'bgo' };
}

function Metric({ label, value, detail, critical = false }: {
  label: string;
  value: string | number;
  detail: string;
  critical?: boolean;
}) {
  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 14, background: 'var(--surface)' }}>
      <div style={{ fontSize: 10.5, color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 750 }}>{label}</div>
      <div style={{ fontSize: 23, fontWeight: 850, color: critical ? 'var(--red)' : 'var(--ink)', marginTop: 4 }}>{value}</div>
      <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 3 }}>{detail}</div>
    </div>
  );
}

export function NationalSecurityOperationsPanel() {
  const [status, setStatus] = useState<SecurityOperationsStatus | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const next = await getSecurityOperationsStatus();
        if (!cancelled) {
          setStatus(next);
          setError('');
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Supervision sécurité indisponible.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    const timer = window.setInterval(() => { void load(); }, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const badge = statusBadge(status?.status ?? 'disabled');
  const auditValid = Boolean(status?.audit_chain.valid);
  const socEnabled = Boolean(status?.soc_policy.enabled);
  const goLive = status?.go_live;
  const failedGoLiveControls = goLive?.controls.filter(control => !control.passed) ?? [];

  return (
    <div className="card" data-testid="national-security-operations">
      <div className="card-header" style={{ alignItems: 'flex-start', gap: 12 }}>
        <div>
          <span className="card-title">SOC national — Security Operations</span>
          <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 4 }}>
            Intégrité audit · authentification · postes suspects · OTLP/WAF/SIEM — aucune identité citoyenne exposée
          </div>
        </div>
        <span className={`badge ${badge.cls}`}>{badge.label}</span>
      </div>

      {loading && <p style={{ padding: 12, color: 'var(--muted)' }}>Chargement de la sécurité nationale…</p>}
      {error && <div className="alert aw" style={{ marginBottom: 14 }}>{error}</div>}

      {status && (
        <>
          {!socEnabled && (
            <div className="alert aw" style={{ marginBottom: 14 }}>
              P11 est livré mais volontairement dormant. Provisionner les clés SOC/audit puis activer selon le runbook.
            </div>
          )}

          {goLive && (
            <div
              data-testid="security-go-live-gate"
              style={{
                border: `1px solid ${goLive.ready ? '#86efac' : '#fcd34d'}`,
                borderRadius: 12,
                padding: 14,
                marginBottom: 14,
                background: 'var(--surface)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontWeight: 850 }}>Go-live sécurité nationale</div>
                  <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 3 }}>
                    Gate runtime P11 : SOC + HMAC + OTLP + WAF + SIEM + absence de signal actif
                  </div>
                </div>
                <span className={`badge ${goLive.ready ? 'bg' : 'bgo'}`}>
                  {goLive.ready ? 'Gate runtime prêt' : 'Go-live bloqué'}
                </span>
              </div>

              {failedGoLiveControls.length > 0 && (
                <div style={{ display: 'grid', gap: 5, marginTop: 10 }}>
                  {failedGoLiveControls.slice(0, 7).map(control => (
                    <div key={control.code} style={{ fontSize: 11.5, color: 'var(--muted)' }}>
                      <strong>{control.code}</strong> · {control.detail}
                    </div>
                  ))}
                </div>
              )}

              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 10 }}>
                {goLive.external_evidence_still_required.length} preuve(s) externe(s) restent à archiver : ce gate ne remplace ni le WAF/SIEM/OTLP réellement observé, ni les tests staging, ni les sign-offs.
              </div>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(155px,1fr))', gap: 10 }}>
            <Metric
              label="Chaîne audit"
              value={!status.soc_policy.audit_chain_enabled ? 'OFF' : auditValid ? 'VALIDE' : 'INVALIDE'}
              detail={status.audit_chain.head_seq ? `Head #${status.audit_chain.head_seq}` : status.audit_chain.reason || 'Non initialisée'}
              critical={status.soc_policy.audit_chain_enabled && !auditValid}
            />
            <Metric label="Login refusés 15 min" value={status.signals.login_failed_15m} detail={`${status.signals.login_failed_24h} sur 24 h`} critical={status.signals.login_failed_15m >= 10} />
            <Metric label="Blocages 15 min" value={status.signals.login_blocked_15m} detail="Protection brute-force" critical={status.signals.login_blocked_15m > 0} />
            <Metric label="Postes suspects" value={status.signals.suspicious_devices} detail="Device sessions" critical={status.signals.suspicious_devices > 0} />
            <Metric label="Incidents critiques" value={status.signals.critical_center_incidents} detail="Centres d’examen" critical={status.signals.critical_center_incidents > 0} />
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 14 }}>
            <span className={`badge ${status.soc_policy.otel.traces_enabled ? 'bg' : 'bgo'}`}>OTLP {status.soc_policy.otel.traces_enabled ? 'actif' : 'inactif'}</span>
            <span className={`badge ${status.soc_policy.waf.required ? 'bg' : 'bgo'}`}>WAF {status.soc_policy.waf.required ? status.soc_policy.waf.provider || 'requis' : 'non validé'}</span>
            <span className={`badge ${status.soc_policy.siem.required ? 'bg' : 'bgo'}`}>SIEM {status.soc_policy.siem.required ? 'requis' : 'non validé'}</span>
          </div>

          {status.alerts.length > 0 && (
            <div style={{ display: 'grid', gap: 6, marginTop: 14 }}>
              {status.alerts.map(alert => (
                <div key={alert.code} className={alert.severity === 'critical' ? 'alert ae' : 'alert aw'}>
                  <strong>{alert.code}</strong> · {alert.severity === 'critical' ? 'Action SOC immédiate' : 'Surveillance requise'}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
