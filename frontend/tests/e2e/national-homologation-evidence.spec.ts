import { expect, test, type Page, type Route } from '@playwright/test';

function fakeJwt(): string {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url');
  return `${header}.${payload}.test`;
}

const runtime = {
  question_count: 40,
  pass_threshold: 35,
  duration_minutes: 30,
  category_distribution: {
    signalisation: 10, priorites: 6, vitesse: 5, depassement: 5,
    securite_passive: 4, urgence: 4, alcool_drogues: 3, premiers_secours: 3,
  },
  one_attempt_per_session: true,
  retake_cooldown_hours: 0,
};

const activePolicy = {
  id: 'policy-id', reference: 'DNTT-POLICY-OFFICIAL_EXAM_CATEGORY_B-2026.1', authority: 'DNTT',
  title: 'Règles officielles Catégorie B', status: 'active', valid_from: new Date().toISOString(), created_at: new Date().toISOString(), updated_at: null,
  document: {
    kind: 'coderoute_national_exam_policy_v1', schema_version: 1, code: 'OFFICIAL_EXAM_CATEGORY_B', version: '2026.1', parameters: runtime,
    legal_references: [{ reference: 'DNTT-DECISION-2026', title: 'Décision DNTT' }], rationale: 'Validation DNTT', approvals: [
      { actor_id: 'a1', role: 'admin', approved_at: new Date().toISOString(), note: 'ok' },
      { actor_id: 'a2', role: 'super_admin', approved_at: new Date().toISOString(), note: 'ok' },
    ], document_sha256: 'a'.repeat(64), activated_at: new Date().toISOString(), supersedes_reference: null,
  },
};

const evidenceCodes = [
  'dntt_exam_rules',
  'legal_review',
  'security_assessment',
  'operations_readiness',
  'content_signoff',
] as const;

type EvidenceCode = typeof evidenceCodes[number];

type EvidenceEntry = {
  reference: string;
  artifact_sha256: string;
  issued_at: string;
  note: string;
  attached_by: string;
  attached_at: string;
};

function evidence(code: EvidenceCode, char = 'b'): EvidenceEntry {
  return {
    reference: `GED-DNTT-${code.toUpperCase()}-2026-001`,
    artifact_sha256: char.repeat(64),
    issued_at: new Date().toISOString(),
    note: 'Pièce institutionnelle vérifiée.',
    attached_by: 'admin-dntt-1',
    attached_at: new Date().toISOString(),
  };
}

function dossier(status: string, entries: Partial<Record<EvidenceCode, EvidenceEntry>>, roleApprovals = 0) {
  return {
    id: 'dossier-id',
    reference: 'DNTT-HOMO-20260809190000-ADMIN1',
    authority: 'DNTT',
    title: 'Dossier homologation nationale',
    status,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    document: {
      kind: 'coderoute_national_homologation_dossier_v1',
      schema_version: 1,
      policy_reference: activePolicy.reference,
      policy_sha256: activePolicy.document.document_sha256,
      target_scope: 'national',
      evidence: entries,
      evidence_history: [],
      approvals: Array.from({ length: roleApprovals }, (_, index) => ({
        actor_id: `approver-${index + 1}`,
        role: index === 1 ? 'super_admin' : 'admin',
        approved_at: new Date().toISOString(),
        note: 'Validation institutionnelle.',
      })),
      decision: null,
      document_sha256: 'c'.repeat(64),
    },
  };
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function bootstrap(page: Page, role: 'admin' | 'super_admin') {
  await page.addInitScript(token => localStorage.setItem('coderoute-auth-token', token), fakeJwt());
  await page.route('**/api/v1/auth/me', route => fulfillJson(route, {
    id: role === 'super_admin' ? 'super-admin-dntt-1' : 'admin-dntt-1',
    email: `${role}@dntt.gov.gn`,
    full_name: role === 'super_admin' ? 'Super Admin DNTT' : 'Admin DNTT',
    role,
    is_active: true,
  }));
  await page.route('**/api/v1/auth/csrf-token', route => fulfillJson(route, { csrf_token: 'csrf-test-token' }));
  await page.route('**/api/v1/dashboard/by-center', route => fulfillJson(route, {
    national: { centers_total: 1, centers_active: 1, sessions_total: 1, bookings_total: 1, exams_total: 1, open_incidents_total: 0 },
    centers: [{ center_id: 'c1', code: 'CRG-001', name: 'Centre DNTT', city: 'Conakry', status: 'accredited', sessions: 1, bookings: 1, exams_total: 1, exams_submitted: 1, exams_passed: 1, pass_rate_pct: 100, open_incidents: 0 }],
  }));
  await page.route('**/api/v1/center-edge/fleet', route => fulfillJson(route, {
    generated_at: new Date().toISOString(), status: 'healthy', target_software_version: 'edge-agent-0.4.0', required_capabilities: [],
    summary: { centers_total: 1, centers_healthy: 1, centers_degraded: 0, centers_critical: 0, centers_without_gateway: 0, nodes_total: 1, nodes_active: 1, nodes_online: 1, sync_pending: 0, revalidation_required: 0, corrupt_leases: 0, version_drift_nodes: 0, capability_drift_nodes: 0 },
    rollout: { target_version: 'edge-agent-0.4.0', compliant_nodes: 1, upgrade_required_nodes: 0, blocked_nodes: 0 },
    centers: [], nodes: [],
  }));
  await page.route('**/api/v1/center-edge/releases**', route => fulfillJson(route, []));
  await page.route('**/api/v1/national-governance/readiness', route => fulfillJson(route, {
    generated_at: new Date().toISOString(), go_live_allowed: true, active_policy: activePolicy, blockers: [],
    checks: [
      'active_policy', 'runtime_alignment', 'official_question_bank', 'accredited_centers',
      'backup_off_region', 'restore_drill', 'pitr_provider', 'api_failover',
    ].map(code => ({ code, required: true, status: 'pass', evidence: {} })),
  }));
  await page.route('**/api/v1/national-governance/technical-contract', route => fulfillJson(route, {
    runtime, active_policy: activePolicy, alignment: { aligned: true, runtime, drift: [] },
  }));
  await page.route('**/api/v1/national-governance/policies', route => fulfillJson(route, [activePolicy]));
}

test('admin attaches fifth hashed evidence then submits the dossier', async ({ page }) => {
  await bootstrap(page, 'admin');
  const initialEvidence: Partial<Record<EvidenceCode, EvidenceEntry>> = {
    dntt_exam_rules: evidence('dntt_exam_rules', '1'),
    legal_review: evidence('legal_review', '2'),
    security_assessment: evidence('security_assessment', '3'),
    operations_readiness: evidence('operations_readiness', '4'),
  };
  let current = dossier('evidence_review', initialEvidence);

  await page.route('**/api/v1/national-governance/homologation-dossiers', route => fulfillJson(route, [current]));
  await page.route('**/api/v1/national-governance/homologation-dossiers/*/evidence', async route => {
    const body = route.request().postDataJSON() as {
      code: EvidenceCode; reference: string; artifact_sha256: string; issued_at: string; note: string;
    };
    expect(body.code).toBe('content_signoff');
    expect(body.reference).toBe('GED-DNTT-CONTENT-2026-009');
    expect(body.artifact_sha256).toBe('f'.repeat(64));
    expect(body.issued_at).toBeTruthy();
    current = dossier('evidence_review', { ...current.document.evidence, content_signoff: {
      reference: body.reference,
      artifact_sha256: body.artifact_sha256,
      issued_at: body.issued_at,
      note: body.note,
      attached_by: 'admin-dntt-1',
      attached_at: new Date().toISOString(),
    } });
    await fulfillJson(route, current);
  });
  await page.route('**/api/v1/national-governance/homologation-dossiers/*/submit', async route => {
    expect(route.request().method()).toBe('POST');
    current = dossier('pending_approval', current.document.evidence);
    await fulfillJson(route, current);
  });

  await page.goto('/#/admin');
  const panel = page.getByTestId('homologation-evidence-workflow');
  await expect(panel).toBeVisible();
  await expect(panel.getByText('4/5', { exact: false })).toBeVisible();
  await expect(panel.getByText('Validation contenus')).toBeVisible();
  await expect(panel.getByText('Manquante', { exact: true })).toHaveCount(1);

  await panel.getByLabel('Type de preuve').selectOption('content_signoff');
  await panel.getByLabel('Référence GED interne').fill('GED-DNTT-CONTENT-2026-009');
  await panel.getByLabel('SHA-256 du document').fill('f'.repeat(64));
  await panel.getByRole('button', { name: 'Enregistrer la preuve hashée' }).click();

  await expect(panel.getByText('Validation contenus').locator('..')).toContainText('Hashée');
  await expect(panel.getByRole('button', { name: 'Soumettre les 5 preuves' })).toBeEnabled();
  await panel.getByRole('button', { name: 'Soumettre les 5 preuves' }).click();
  await expect(panel.getByText('pending_approval', { exact: true })).toBeVisible();
});

test('super admin homologates only a ready-for-decision dossier with five hashes', async ({ page }) => {
  await bootstrap(page, 'super_admin');
  const allEvidence = Object.fromEntries(
    evidenceCodes.map((code, index) => [code, evidence(code, String((index + 1) % 10))]),
  ) as Record<EvidenceCode, EvidenceEntry>;
  let current = dossier('ready_for_decision', allEvidence, 2);

  await page.route('**/api/v1/national-governance/homologation-dossiers', route => fulfillJson(route, [current]));
  await page.route('**/api/v1/national-governance/homologation-dossiers/*/decision?approve=true', async route => {
    const body = route.request().postDataJSON() as { note: string };
    expect(body.note.length).toBeGreaterThan(3);
    current = dossier('homologated', allEvidence, 2);
    current.document.decision = {
      status: 'homologated', decided_by: 'super-admin-dntt-1', decided_at: new Date().toISOString(), note: body.note,
    };
    await fulfillJson(route, current);
  });

  await page.goto('/#/admin');
  const panel = page.getByTestId('homologation-evidence-workflow');
  await expect(panel).toBeVisible();
  await expect(panel.getByText('Hashée', { exact: true })).toHaveCount(5);
  await expect(panel.getByText('ready_for_decision', { exact: true })).toBeVisible();
  await panel.getByRole('button', { name: 'Homologuer' }).click();
  await expect(panel.getByText('homologated', { exact: true })).toBeVisible();
  await expect(panel.getByRole('button', { name: 'Homologuer' })).toHaveCount(0);
});
