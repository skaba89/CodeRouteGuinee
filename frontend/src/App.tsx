import { type FormEvent, useEffect, useState } from 'react';

import {
  type DashboardData,
  type EntrySummary,
  type EntryValidationResult,
  getDashboard,
  getEntrySummary,
  validateEntry,
} from './api';

const fallbackDashboard: DashboardData = {
  candidates: 1250,
  accredited_centers: 18,
  exam_sessions: 96,
  questions: 0,
  fraud_alerts: 19,
};

const fallbackEntrySummary: EntrySummary = {
  total: 421,
  by_result: { allowed: 402, denied: 19 },
  by_center: {
    'CTR-KALOUM': { allowed: 122, denied: 3 },
    'CTR-MATOTO': { allowed: 98, denied: 12 },
    'CTR-KANKAN': { allowed: 66, denied: 4 },
  },
};

const modules = [
  'Inscription candidat',
  'Reservation examen',
  'Paiement Mobile Money',
  'Convocation QR et PDF',
  'Controle entree centre',
  'Examen et correction',
  'Logs et supervision',
  'Dashboard national',
];

function formatNumber(value: number): string {
  return new Intl.NumberFormat('fr-FR').format(value);
}

function buildRiskLabel(denied: number): string {
  if (denied >= 10) return 'A verifier';
  if (denied >= 4) return 'Audit';
  return 'Normal';
}

export default function App() {
  const [dashboard, setDashboard] = useState<DashboardData>(fallbackDashboard);
  const [entrySummary, setEntrySummary] = useState<EntrySummary>(fallbackEntrySummary);
  const [apiStatus, setApiStatus] = useState<'connected' | 'offline'>('offline');
  const [entryReference, setEntryReference] = useState('GN-CONV-2026-000001');
  const [verificationCode, setVerificationCode] = useState('');
  const [centerCode, setCenterCode] = useState('CTR-KALOUM');
  const [entryResult, setEntryResult] = useState<EntryValidationResult | null>(null);
  const [entryError, setEntryError] = useState<string | null>(null);
  const [isSubmittingEntry, setIsSubmittingEntry] = useState(false);

  useEffect(() => {
    let isMounted = true;
    Promise.allSettled([getDashboard(), getEntrySummary()]).then(([dashboardResult, entryResult]) => {
      if (!isMounted) return;
      if (dashboardResult.status === 'fulfilled') {
        setDashboard(dashboardResult.value);
      }
      if (entryResult.status === 'fulfilled') {
        setEntrySummary(entryResult.value);
      }
      if (dashboardResult.status === 'fulfilled' || entryResult.status === 'fulfilled') {
        setApiStatus('connected');
      }
    });
    return () => {
      isMounted = false;
    };
  }, []);

  async function handleEntrySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmittingEntry(true);
    setEntryError(null);
    setEntryResult(null);
    try {
      const result = await validateEntry({
        reference: entryReference,
        verification_code: verificationCode,
        center_code: centerCode,
      });
      setEntryResult(result);
      const latestSummary = await getEntrySummary();
      setEntrySummary(latestSummary);
      setApiStatus('connected');
    } catch (error) {
      setEntryError("Impossible de valider l'entree. Verifiez que l'API est demarree.");
    } finally {
      setIsSubmittingEntry(false);
    }
  }

  const metrics = [
    { label: 'Candidats inscrits', value: formatNumber(dashboard.candidates) },
    { label: 'Centres agrees', value: formatNumber(dashboard.accredited_centers) },
    { label: 'Sessions organisees', value: formatNumber(dashboard.exam_sessions) },
    { label: 'Alertes entree', value: formatNumber(dashboard.fraud_alerts) },
  ];

  const allowedEntries = entrySummary.by_result.allowed ?? 0;
  const deniedEntries = entrySummary.by_result.denied ?? 0;
  const centerRows = Object.entries(entrySummary.by_center).map(([center, values]) => [
    center,
    String(values.allowed ?? 0),
    String(values.denied ?? 0),
    buildRiskLabel(values.denied ?? 0),
  ]);

  return (
    <main className="app-shell">
      <nav className="top-nav">
        <strong>CodeRoute Guinee</strong>
        <div>
          <a href="#candidat">Candidat</a>
          <a href="#centre">Centre</a>
          <a href="#admin">Admin</a>
          <a href="#examen">Examen</a>
        </div>
      </nav>

      <section className="hero">
        <div>
          <p className="eyebrow">Produit national pour la Guinee</p>
          <h1>CodeRoute Guinee</h1>
          <p>
            Plateforme nationale de digitalisation, securisation et tracabilite des examens du code de la route.
          </p>
          <div className="actions">
            <a href="http://localhost:8000/docs" target="_blank">Voir l'API</a>
            <a href="#modules" className="secondary">Modules MVP</a>
          </div>
        </div>
        <div className="hero-status">
          <span>Convocation QR</span><strong>Actif</strong>
          <span>Paiement Mobile Money</span><strong>Sandbox</strong>
          <span>Controle entree</span><strong>Actif</strong>
          <span>API frontend</span><strong>{apiStatus === 'connected' ? 'Connectee' : 'Fallback'}</strong>
        </div>
      </section>

      <section className="metrics">
        {metrics.map((metric) => (
          <article key={metric.label}>
            <strong>{metric.value}</strong>
            <span>{metric.label}</span>
          </article>
        ))}
      </section>

      <section id="modules" className="panel">
        <h2>Socle fonctionnel national</h2>
        <div className="grid modules-grid">
          {modules.map((module) => (
            <div className="card" key={module}>{module}</div>
          ))}
        </div>
      </section>

      <section id="candidat" className="screen two-columns">
        <div>
          <p className="eyebrow dark">Espace candidat</p>
          <h2>Dossier, reservation et convocation</h2>
          <p>Le candidat suit son dossier, reserve une session, paie et telecharge sa convocation PDF avec QR code.</p>
          <div className="mini-card">Reference candidat : <strong>GN-CODE-2026-000001</strong></div>
          <div className="mini-card">Session : <strong>Centre Kaloum - 20/06/2026</strong></div>
          <div className="mini-card">Paiement : <strong>Orange Money - paye</strong></div>
        </div>
        <div className="qr-card">
          <div className="qr-box" />
          <strong>Convocation verifiable</strong>
          <span>GN-CONV-2026-000001</span>
        </div>
      </section>

      <section id="centre" className="screen two-columns inverted">
        <form className="scanner-card" onSubmit={handleEntrySubmit}>
          <h2>Controle entree centre</h2>
          <p>Scan QR, verification du code et passage automatique du statut en checked_in.</p>
          <label>
            Reference convocation
            <input value={entryReference} onChange={(event) => setEntryReference(event.target.value)} />
          </label>
          <label>
            Code verification
            <input value={verificationCode} onChange={(event) => setVerificationCode(event.target.value)} placeholder="Code de la convocation" />
          </label>
          <label>
            Code centre
            <input value={centerCode} onChange={(event) => setCenterCode(event.target.value)} />
          </label>
          <button disabled={isSubmittingEntry || !entryReference || !verificationCode}>
            {isSubmittingEntry ? 'Validation...' : 'Valider entree'}
          </button>
        </form>
        <div>
          <p className="eyebrow dark">Centre agree</p>
          <h2>Validation en temps reel</h2>
          <table>
            <tbody>
              <tr><th>Statut</th><td><span className={entryResult?.allowed ? 'badge ok' : 'badge'}>{entryResult?.status ?? 'En attente'}</span></td></tr>
              <tr><th>Reference</th><td>{entryResult?.reference ?? entryReference}</td></tr>
              <tr><th>Centre</th><td>{entryResult?.center_code ?? centerCode}</td></tr>
              <tr><th>Message</th><td>{entryResult?.message ?? entryResult?.reason ?? entryError ?? 'Aucune validation lancee'}</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section id="admin" className="panel admin-panel">
        <p className="eyebrow dark">Administration nationale</p>
        <h2>Supervision centres et entrees</h2>
        <div className="metrics compact">
          <article><strong>{formatNumber(allowedEntries)}</strong><span>Entrees validees</span></article>
          <article><strong>{formatNumber(deniedEntries)}</strong><span>Entrees refusees</span></article>
          <article><strong>58.5M</strong><span>GNF encaisses</span></article>
          <article><strong>{formatNumber(dashboard.fraud_alerts)}</strong><span>Alertes centre</span></article>
        </div>
        <table>
          <thead><tr><th>Centre</th><th>Validees</th><th>Refusees</th><th>Risque</th></tr></thead>
          <tbody>
            {centerRows.map((row) => (
              <tr key={row[0]}>
                {row.map((cell, index) => <td key={`${row[0]}-${index}`}>{index === 3 ? <span className="badge">{cell}</span> : cell}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section id="examen" className="screen exam-screen">
        <div>
          <p className="eyebrow dark">Interface examen</p>
          <h2>Question 12 / 40</h2>
          <p className="question">Que devez-vous faire face a un feu rouge fixe ?</p>
          <div className="answer selected">A. Marquer l'arret obligatoire</div>
          <div className="answer">B. Passer si la voie est libre</div>
          <div className="answer">C. Klaxonner puis avancer</div>
        </div>
        <aside className="timer-card">
          <span>Temps restant</span>
          <strong>18:24</strong>
          <p>Score requis : 35 / 40</p>
        </aside>
      </section>
    </main>
  );
}
