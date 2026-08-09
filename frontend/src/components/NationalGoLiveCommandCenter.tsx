import { useEffect, useMemo, useState } from 'react';
import { getGovernanceReadiness, type GovernanceReadiness } from '../nationalGovernanceClient';
import { getReliabilityStatus, type ReliabilityStatus } from '../reliabilityClient';
import { getSecurityOperationsStatus, type SecurityOperationsStatus } from '../securityOperationsClient';

type GateStatus = 'pass' | 'blocked' | 'unknown';

type GateItem = {
  code: string;
  label: string;
  status: GateStatus;
  detail: string;
};

const HOUR_MS = 60 * 60 * 1000;
const DAY_MS = 24 * HOUR_MS;

function ageGate(
  code: string,
  label: string,
  timestamp: string | null | undefined,
  maxAgeMs: number,
  nowMs: number,
): GateItem {
  if (!timestamp) return { code, label, status: 'blocked', detail: 'Aucune preuve horodatée' };
  const value = Date.parse(timestamp);
  if (!Number.isFinite(value)) return { code, label, status: 'blocked', detail: 'Horodatage invalide' };
  const ageMs = nowMs - value;
  if (ageMs < -5 * 60 * 1000) return { code, label, status: 'blocked', detail: 'Preuve datée dans le futur' };
  const hours = Math.max(0, ageMs) / HOUR_MS;
  if (ageMs > maxAgeMs) {
    return { code, label, status: 'blocked', detail: `Preuve trop ancienne · ${hours.toFixed(1)} h` };
  }
  return { code, label, status: 'pass', detail: `Preuve fraîche · ${hours.toFixed(1)} h` };
}

function GateBadge({ status }: { status: GateStatus }) {
  const cls = status === 'pass' ? 'bg' : status === 'blocked' ? 'br' : 'bgo';
  const label = status === 'pass' ? 'PASS' : status === 'blocked' ? 'BLOQUÉ' : 'INCONNU';
  return <span className={`badge ${cls}`}>{label}</span>;
}

function DomainCard({
  title,
  subtitle,
  status,
  items,
  testId,
}: {
  title: string;
  subtitle: string;
  status: GateStatus;
  items: GateItem[];
  testId: string;
}) {
  return (
    <div data-testid={testId} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 14, background: 'var(--surface)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontWeight: 850 }}>{title}</div>
          <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 3 }}>{subtitle}</div>
        </div>
        <GateBadge status={status} />
      </div>
      <div style={{ display: 'grid', gap: 7, marginTop: 12 }}>
        {items.map(item => (
          <div key={item.code} style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 8, alignItems: 'start' }}>
            <span aria-label={`${item.label}: ${item.status}`} style={{ fontWeight: 850, color: item.status === 'pass' ? 'var(--green)' : 'var(--red)' }}>
              {item.status === 'pass' ? '✓' : item.status === 'blocked' ? '×' : '·'}
            </span>
            <div>
              <div style={{ fontSize: 11.5, fontWeight: 750 }}>{item.label}</div>
              <div style={{ fontSize: 10.5, color: 'var(--muted)' }}>{item.detail}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function allPassed(items: GateItem[]): GateStatus {
  if (!items.length) return 'unknown';
  return items.every(item => item.status === 'pass') ? 'pass' : 'blocked';
}

export function NationalGoLiveCommandCenter() {
  const [reliability, setReliability] = useState<ReliabilityStatus | null>(null);
  const [security, setSecurity] = useState<SecurityOperationsStatus | null>(null);
  const [governance, setGovernance] = useState<GovernanceReadiness | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [nextReliability, nextSecurity, nextGovernance] = await Promise.all([
          getReliabilityStatus(),
          getSecurityOperationsStatus(),
          getGovernanceReadiness(),
        ]);
        if (!cancelled) {
          setReliability(nextReliability);
          setSecurity(nextSecurity);
          setGovernance(nextGovernance);
          setNowMs(Date.now());
          setError('');
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Command Center indisponible.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    const refresh = window.setInterval(() => { void load(); }, 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(refresh);
    };
  }, []);

  const p10 = useMemo<GateItem[]>(() => {
    if (!reliability) return [];
    const last = reliability.last_evidence ?? {};
    const dr = reliability.policy?.dr ?? {};
    return [
      {
        code: 'backup_configuration',
        label: 'Backup hors région configuré',
        status: dr.bucket_configured && dr.off_region_required && Boolean(dr.target_region) ? 'pass' : 'blocked',
        detail: dr.bucket_configured && dr.off_region_required && dr.target_region
          ? `Cible ${dr.target_region}`
          : 'Bucket/cible hors région non finalisés',
      },
      ageGate('backup_uploaded', 'Dernier backup hors région', last.backup_uploaded, 26 * HOUR_MS, nowMs),
      ageGate('restore_drill', 'Restore drill', last.restore_drill_passed, 35 * DAY_MS, nowMs),
      ageGate('pitr_drill', 'PITR fournisseur', last.pitr_drill_passed, 35 * DAY_MS, nowMs),
      ageGate('api_failover', 'Failover API', last.ha_failover_probe_passed, 35 * DAY_MS, nowMs),
    ];
  }, [reliability, nowMs]);

  const p11 = useMemo<GateItem[]>(() => {
    if (!security) return [];
    const controls = security.go_live?.controls ?? [];
    if (!controls.length) {
      return [{ code: 'p11_contract', label: 'Gate sécurité P11', status: 'blocked', detail: 'Contrat go_live absent du backend' }];
    }
    return controls.map(control => ({
      code: control.code,
      label: control.code
        .replace('soc_enabled', 'SOC activé')
        .replace('audit_hmac_enabled', 'Audit HMAC activé')
        .replace('audit_chain_valid', 'Chaîne audit valide')
        .replace('otel_enabled', 'OTLP activé')
        .replace('waf_enforced', 'WAF imposé')
        .replace('siem_enforced', 'SIEM imposé')
        .replace('no_active_security_alert', 'Aucun signal sécurité actif'),
      status: control.passed ? 'pass' : 'blocked',
      detail: control.detail,
    }));
  }, [security]);

  const p12 = useMemo<GateItem[]>(() => {
    if (!governance) return [];
    return governance.checks
      .filter(check => check.required)
      .map(check => ({
        code: check.code,
        label: check.code
          .replace('active_policy', 'Politique DNTT active')
          .replace('runtime_alignment', 'Politique alignée au runtime')
          .replace('official_question_bank', 'Banque officielle prête')
          .replace('accredited_centers', 'Centre accrédité disponible')
          .replace('backup_off_region', 'Backup hors région')
          .replace('restore_drill', 'Restore drill')
          .replace('pitr_provider', 'PITR fournisseur')
          .replace('api_failover', 'Failover API'),
        status: check.status === 'pass' ? 'pass' : 'blocked',
        detail: check.status === 'pass' ? 'Contrôle automatisé satisfait' : 'Bloque la readiness P12',
      }));
  }, [governance]);

  const p10Status = allPassed(p10);
  const p11Status = allPassed(p11);
  const p12Status = governance?.go_live_allowed === true && allPassed(p12) === 'pass' ? 'pass' : p12.length ? 'blocked' : 'unknown';
  const automatedReady = p10Status === 'pass' && p11Status === 'pass' && p12Status === 'pass';
  const blockerCount = [...p10, ...p11, ...p12].filter(item => item.status !== 'pass').length;

  return (
    <div className="card" data-testid="national-go-live-command-center">
      <div className="card-header" style={{ alignItems: 'flex-start', gap: 12 }}>
        <div>
          <span className="card-title">Command Center — Go-Live national</span>
          <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 4 }}>
            Vue consolidée P10.2 PRA/PITR · P11 SOC/WAF/SIEM · P12 gouvernance/homologation
          </div>
        </div>
        <span data-testid="national-automated-readiness" className={`badge ${automatedReady ? 'bg' : 'br'}`}>
          {automatedReady ? 'Gates automatisables prêts' : `${blockerCount} blocker(s)`}
        </span>
      </div>

      {loading && <p style={{ color: 'var(--muted)' }}>Calcul de la readiness nationale…</p>}
      {error && <div className="alert aw" style={{ marginBottom: 14 }}>{error}</div>}

      {!loading && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 10 }}>
            <DomainCard title="P10.2 — Continuité" subtitle="Backup, restore, PITR, failover" status={p10Status} items={p10} testId="go-live-p10" />
            <DomainCard title="P11 — Sécurité" subtitle="SOC, HMAC, OTLP, WAF, SIEM" status={p11Status} items={p11} testId="go-live-p11" />
            <DomainCard title="P12 — Homologation" subtitle="Politique, banque, centres, readiness" status={p12Status} items={p12} testId="go-live-p12" />
          </div>

          <div className="alert aw" style={{ marginTop: 14 }} data-testid="institutional-signoff-required">
            <strong>Décision institutionnelle toujours requise.</strong> Même lorsque tous les gates automatisables sont verts, le lancement national exige encore les pièces externes correspondantes, les recettes fournisseur/SOC, les droits contenus, les approbateurs habilités et la décision DNTT/autorité compétente.
          </div>
        </>
      )}
    </div>
  );
}
