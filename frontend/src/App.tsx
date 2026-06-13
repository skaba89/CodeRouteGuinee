const metrics = [
  { label: 'Candidats inscrits', value: '1 250' },
  { label: 'Centres agrees', value: '18' },
  { label: 'Sessions organisees', value: '96' },
  { label: 'Alertes entree', value: '19' },
];

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

const centerRows = [
  ['CTR-KALOUM', '122', '3', 'Normal'],
  ['CTR-MATOTO', '98', '12', 'A verifier'],
  ['CTR-KANKAN', '66', '4', 'Audit'],
];

export default function App() {
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
          <span>Logs supervision</span><strong>Actif</strong>
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
        <div className="scanner-card">
          <h2>Controle entree centre</h2>
          <p>Scan QR, verification du code et passage automatique du statut en checked_in.</p>
          <div className="form-line">Reference convocation</div>
          <div className="form-line">Code verification</div>
          <button>Valider entree</button>
        </div>
        <div>
          <p className="eyebrow dark">Centre agree</p>
          <h2>Validation en temps reel</h2>
          <table>
            <tbody>
              <tr><th>Statut</th><td><span className="badge ok">checked_in</span></td></tr>
              <tr><th>Candidat</th><td>Mariama Barry</td></tr>
              <tr><th>Centre</th><td>CTR-KALOUM</td></tr>
              <tr><th>Heure</th><td>08:42</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section id="admin" className="panel admin-panel">
        <p className="eyebrow dark">Administration nationale</p>
        <h2>Supervision centres et entrees</h2>
        <div className="metrics compact">
          <article><strong>402</strong><span>Entrees validees</span></article>
          <article><strong>19</strong><span>Entrees refusees</span></article>
          <article><strong>58.5M</strong><span>GNF encaisses</span></article>
          <article><strong>3</strong><span>Alertes centre</span></article>
        </div>
        <table>
          <thead><tr><th>Centre</th><th>Validees</th><th>Refusees</th><th>Risque</th></tr></thead>
          <tbody>
            {centerRows.map((row) => (
              <tr key={row[0]}>
                {row.map((cell, index) => <td key={cell}>{index === 3 ? <span className="badge">{cell}</span> : cell}</td>)}
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
